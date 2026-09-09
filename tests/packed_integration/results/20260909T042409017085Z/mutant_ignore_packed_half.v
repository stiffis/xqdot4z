module datapath #(parameter ENABLE_XQDOT4Z = 0, parameter ENABLE_MUL = 0,
                  parameter ENABLE_XQDOT4 = 0)(input  clk, reset,
                 input  [1:0] ResultSrcW,
                 input  [1:0] ResultSrcM,
                 input  PCSrcE, ALUSrcE, JalrE,
                 input  RegWriteW,
                 input  StallF, StallD, FlushD, FlushE,
                 input  [1:0] ForwardAE, ForwardBE,
                 input  [1:0] ImmSrcD,
                 input  [3:0] ALUControlE,
                 output ZeroE,
                 output CondBitE,
                 output [6:0] opD,
                 output [2:0] funct3D,
                 output funct7b5D,
                 output SupportedD, UsesRs1D, UsesRs2D,
                 input FetchFaultF,
                 output FaultValidE,
                 output [1:0] FaultCauseE,
                 output [31:0] FaultPCE,
                 output reg ValidM, ValidW,
                 output reg [31:0] PCW,
                 output [4:0] Rs1D, Rs2D,
                 output [4:0] Rs1E, Rs2E,
                 output [4:0] RdE, RdM, RdW,
                 output [31:0] PCF,
                 input  [31:0] InstrF,
                 output [31:0] ALUResultM, WriteDataM,
                 input  [31:0] ReadDataM);
  
  localparam WIDTH = 32;

  wire [31:0] PCNextF, PCPlusIncF;
  wire [31:0] InstrDecF;
  wire        compressedF;
  wire illegalF;
  reg illegalD, fetchFaultD, invalidE, breakpointE, fetchFaultE;
  reg ValidD, ValidE;
  reg [31:0] PCM;
  wire baseSupportedD, breakpointD, rawUsesRs1D, rawUsesRs2D;
  wire [31:0] InstrD, PCD, PCPlusIncD;
  wire [31:0] RD1D, RD2D, ImmExtD;
  wire [31:0] RD1E, RD2E, PCE, ImmExtE, PCPlusIncE;
  wire [31:0] SrcAE, WriteDataE, SrcBE, ALUResultE;
  wire [31:0] QDotResultE, ExecuteResultE;
  wire [31:0] MulResultE;
  wire [31:0] PackedResultE;
  wire PackedD, PackedE, PackedHalfE;
  wire MulD, MulE;
  wire QDotD, QDotE, QDotHalfE;
  wire [3:0] QDotZeroE;
  wire [31:0] PCTargetE, PCBranchTargetE, PCJalrTargetE;
  wire [31:0] ResultM;
  wire [31:0] ALUResultW, ReadDataW, PCPlusIncM, PCPlusIncW;
  wire [31:0] ResultW;
  wire [4:0]  RdD;

  // Fetch stage
  flopenr #(WIDTH) pcreg(
    .clk(clk),
    .reset(reset),
    .en(~StallF),
    .d(PCNextF),
    .q(PCF)
  );

  decompressor dec(
    .instrraw(InstrF),
    .instr(InstrDecF),
    .compressed(compressedF),
    .illegal(illegalF)
  );

  // Validity is independent of RegWrite: stores, branches and NOPs retire too.
  // Faults are acted upon in E, so a wrong-path instruction flushed in D
  // cannot stop execution. No architectural trap/CSR handler is implemented.
  always @(posedge clk or posedge reset) begin
    if (reset) begin
      ValidD <= 0; ValidE <= 0; ValidM <= 0; ValidW <= 0;
      illegalD <= 0; fetchFaultD <= 0;
      invalidE <= 0; breakpointE <= 0; fetchFaultE <= 0;
      PCM <= 0; PCW <= 0;
    end else begin
      if (FlushD) begin
        ValidD <= 0; illegalD <= 0; fetchFaultD <= 0;
      end else if (!StallD) begin
        ValidD <= 1; illegalD <= illegalF; fetchFaultD <= FetchFaultF;
      end
      ValidE <= FlushE ? 1'b0 : ValidD;
      invalidE <= !FlushE && (illegalD || (!baseSupportedD && !breakpointD));
      breakpointE <= !FlushE && breakpointD && !illegalD;
      fetchFaultE <= !FlushE && fetchFaultD;
      ValidM <= ValidE && !FaultValidE;
      ValidW <= ValidM;
      PCM <= PCE; PCW <= PCM;
    end
  end

  instruction_policy #(.ENABLE_XQDOT4Z(ENABLE_XQDOT4Z), .ENABLE_MUL(ENABLE_MUL),
                       .ENABLE_XQDOT4(ENABLE_XQDOT4)) policy(
    .instr(InstrD), .supported(baseSupportedD), .breakpoint(breakpointD),
    .uses_rs1(rawUsesRs1D), .uses_rs2(rawUsesRs2D));
  assign SupportedD = ValidD && baseSupportedD && !illegalD && !fetchFaultD;
  assign UsesRs1D = SupportedD && rawUsesRs1D;
  assign UsesRs2D = SupportedD && rawUsesRs2D;
  assign QDotD = SupportedD && (opD == 7'b0001011);
  assign PackedD = SupportedD && (opD == 7'b0101011);
  assign MulD = SupportedD && (opD == 7'b0110011) &&
                (InstrD[31:25] == 7'b0000001) && (funct3D == 0);
  assign FaultValidE = ValidE && (invalidE || breakpointE || fetchFaultE);
  assign FaultCauseE = fetchFaultE ? 2'd1 : (breakpointE ? 2'd3 : 2'd2);
  assign FaultPCE = PCE;

  assign PCPlusIncF = PCF + (compressedF ? 32'd2 : 32'd4);

  mux2 #(WIDTH) pcmux(
    .d0(PCPlusIncF),
    .d1(PCTargetE),
    .s(PCSrcE),
    .y(PCNextF)
  );

  // IF/ID pipeline register
  flopenrc #(WIDTH) ifid_instrreg(
    .clk(clk),
    .reset(reset),
    .en(~StallD),
    .clear(FlushD),
    .d(InstrDecF),
    .q(InstrD)
  );

  flopenrc #(WIDTH) ifid_pcreg(
    .clk(clk),
    .reset(reset),
    .en(~StallD),
    .clear(FlushD),
    .d(PCF),
    .q(PCD)
  );

  flopenrc #(WIDTH) ifid_pcplusincreg(
    .clk(clk),
    .reset(reset),
    .en(~StallD),
    .clear(FlushD),
    .d(PCPlusIncF),
    .q(PCPlusIncD)
  );

  // Decode stage
  assign opD = InstrD[6:0];
  assign funct3D = InstrD[14:12];
  assign funct7b5D = InstrD[30];
  assign Rs1D = InstrD[19:15];
  assign Rs2D = InstrD[24:20];
  assign RdD = InstrD[11:7];

  regfile rf(
    .clk(clk),
    .we3(RegWriteW),
    .a1(Rs1D),
    .a2(Rs2D),
    .a3(RdW),
    .wd3(ResultW),
    .rd1(RD1D),
    .rd2(RD2D)
  );

  extend ext(
    .instr(InstrD[31:7]),
    .immsrc(ImmSrcD),
    .op(InstrD[6:0]),
    .immext(ImmExtD)
  );

  // ID/EX pipeline register
  flopenrc #(WIDTH) idex_rd1reg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(RD1D),
    .q(RD1E)
  );

  flopenrc #(WIDTH) idex_rd2reg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(RD2D),
    .q(RD2E)
  );

  flopenrc #(WIDTH) idex_pcreg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(PCD),
    .q(PCE)
  );

  flopenrc #(WIDTH) idex_immreg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(ImmExtD),
    .q(ImmExtE)
  );

  flopenrc #(5) idex_rs1reg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(Rs1D),
    .q(Rs1E)
  );

  flopenrc #(5) idex_rs2reg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(Rs2D),
    .q(Rs2E)
  );

  flopenrc #(5) idex_rdreg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(RdD),
    .q(RdE)
  );

  flopenrc #(WIDTH) idex_pcplusincreg(
    .clk(clk),
    .reset(reset),
    .en(1'b1),
    .clear(FlushE),
    .d(PCPlusIncD),
    .q(PCPlusIncE)
  );

  // Execute stage
  // Metadata travels with its instruction and is cleared on bubbles/redirects.
  // No architectural zero-point register and no extra register-file read port.
  flopenrc #(6) idex_qdotreg(
    .clk(clk), .reset(reset), .en(1'b1), .clear(FlushE),
    .d({QDotD, InstrD[31:28], InstrD[27]}),
    .q({QDotE, QDotZeroE, QDotHalfE})
  );
  generate if (ENABLE_XQDOT4Z != 0) begin : qdot_enabled
    // Reuse the exact M2 unit, supplied as ../rtl/xqdot4z.v by the build.
    xqdot4z qdot(
      .weights_word(SrcAE), .activations_word(WriteDataE),
      .zero_point(QDotZeroE), .half(QDotHalfE), .result(QDotResultE)
    );
  end else begin : qdot_disabled
    assign QDotResultE = 32'b0;
  end endgenerate
  // MUL is optional and independent of XQDot4Zi. No extra E-stage wait.
  flopenrc #(1) idex_mulreg(
    .clk(clk), .reset(reset), .en(1'b1), .clear(FlushE),
    .d(MulD), .q(MulE)
  );
  generate if (ENABLE_MUL != 0) begin : mul_enabled
    scalar_mul mul(.lhs(SrcAE), .rhs(WriteDataE), .result(MulResultE));
  end else begin : mul_disabled
    assign MulResultE = 32'b0;
  end endgenerate
  // B3 uses its frozen isolated unit, with the same forwarded sources as D.
  flopenrc #(2) idex_packedreg(
    .clk(clk), .reset(reset), .en(1'b1), .clear(FlushE),
    .d({PackedD, 1'b0}), .q({PackedE, PackedHalfE})
  );
  generate if (ENABLE_XQDOT4 != 0) begin : packed_enabled
    xqdot4 packed_dot(
      .weights_word(SrcAE), .activations_word(WriteDataE),
      .half(PackedHalfE), .result(PackedResultE)
    );
  end else begin : packed_disabled
    assign PackedResultE = 32'b0;
  end endgenerate
  assign ExecuteResultE = QDotE ? QDotResultE :
                          (PackedE ? PackedResultE : (MulE ? MulResultE : ALUResultE));

  mux3 #(WIDTH) forwardamux(
    .d0(RD1E),
    .d1(ResultW),
    .d2(ResultM),
    .s(ForwardAE),
    .y(SrcAE)
  );

  mux3 #(WIDTH) forwardbmux(
    .d0(RD2E),
    .d1(ResultW),
    .d2(ResultM),
    .s(ForwardBE),
    .y(WriteDataE)
  );

  mux2 #(WIDTH) srcbmux(
    .d0(WriteDataE),
    .d1(ImmExtE),
    .s(ALUSrcE),
    .y(SrcBE)
  );

  alu alu(
    .a(SrcAE),
    .b(SrcBE),
    .alucontrol(ALUControlE),
    .result(ALUResultE),
    .zero(ZeroE)
  );

  adder pcaddbranch(
    .a(PCE),
    .b(ImmExtE),
    .y(PCBranchTargetE)
  );

  assign CondBitE = ALUResultE[0];
  assign PCJalrTargetE = {ALUResultE[31:1], 1'b0};
  assign PCTargetE = JalrE ? PCJalrTargetE : PCBranchTargetE;

  // EX/MEM pipeline register
  flopr #(WIDTH) exmem_aluresultreg(
    .clk(clk),
    .reset(reset),
    .d(ExecuteResultE),
    .q(ALUResultM)
  );

  flopr #(WIDTH) exmem_writedatareg(
    .clk(clk),
    .reset(reset),
    .d(WriteDataE),
    .q(WriteDataM)
  );

  flopr #(5) exmem_rdreg(
    .clk(clk),
    .reset(reset),
    .d(RdE),
    .q(RdM)
  );

  flopr #(WIDTH) exmem_pcplusincreg(
    .clk(clk),
    .reset(reset),
    .d(PCPlusIncE),
    .q(PCPlusIncM)
  );

  mux3 #(WIDTH) resultmuxm(
    .d0(ALUResultM),
    .d1(ReadDataM),
    .d2(PCPlusIncM),
    .s(ResultSrcM),
    .y(ResultM)
  );

  // MEM/WB pipeline register
  flopr #(WIDTH) memwb_aluresultreg(
    .clk(clk),
    .reset(reset),
    .d(ALUResultM),
    .q(ALUResultW)
  );

  flopr #(WIDTH) memwb_readdatareg(
    .clk(clk),
    .reset(reset),
    .d(ReadDataM),
    .q(ReadDataW)
  );

  flopr #(5) memwb_rdreg(
    .clk(clk),
    .reset(reset),
    .d(RdM),
    .q(RdW)
  );

  flopr #(WIDTH) memwb_pcplusincreg(
    .clk(clk),
    .reset(reset),
    .d(PCPlusIncM),
    .q(PCPlusIncW)
  );

  // Writeback stage
  mux3 #(WIDTH) resultmux(
    .d0(ALUResultW),
    .d1(ReadDataW),
    .d2(PCPlusIncW),
    .s(ResultSrcW),
    .y(ResultW)
  );
endmodule
