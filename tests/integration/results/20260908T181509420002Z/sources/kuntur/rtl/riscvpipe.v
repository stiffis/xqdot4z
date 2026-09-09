module riscvpipe #(parameter ENABLE_XQDOT4Z = 0)(input  clk, reset,
                 output [31:0] PCF,
                 input  [31:0] InstrF,
                 output MemWriteM,
                 output [31:0] DataAdrM,
                 output [31:0] WriteDataM,
                 input  [31:0] ReadDataM,
                 input FetchFaultF,
                 output MemReadM,
                 output RetireValidW,
                 output [31:0] RetirePCW,
                 output reg Fault,
                 output reg [1:0] FaultCause,
                 output reg [31:0] FaultPC);
  
  wire [6:0] opD;
  wire [2:0] funct3D;
  wire       funct7b5D;
  wire [4:0] Rs1D, Rs2D, Rs1E, Rs2E, RdE, RdM, RdW;
  wire       ZeroE;
  wire       CondBitE;
  wire       PCSrcE, ALUSrcE, JalrE, RegWriteM, RegWriteW;
  wire       StallF, StallD, FlushD, FlushE;
  wire [1:0] ForwardAE, ForwardBE;
  wire [1:0] ResultSrcW, ResultSrcM, ResultSrcE, ImmSrcD;
  wire [3:0] ALUControlE;
  wire SupportedD, UsesRs1D, UsesRs2D;
  wire HazardStallF, HazardStallD, HazardFlushD, HazardFlushE;
  wire FaultValidE, ValidM;
  wire [1:0] FaultCauseE;
  wire [31:0] FaultPCE;

  assign StallF = HazardStallF | Fault | FaultValidE;
  assign StallD = HazardStallD | Fault | FaultValidE;
  assign FlushD = HazardFlushD | Fault | FaultValidE;
  assign FlushE = HazardFlushE | Fault | FaultValidE;
  assign MemReadM = ValidM && (ResultSrcM == 2'b01);
  always @(posedge clk or posedge reset) begin
    if (reset) begin Fault <= 0; FaultCause <= 0; FaultPC <= 0; end
    else if (FaultValidE && !Fault) begin
      Fault <= 1; FaultCause <= FaultCauseE; FaultPC <= FaultPCE;
    end
  end

  controller c(
    .clk(clk),
    .reset(reset),
    .FlushE(FlushE),
    .opD(opD),
    .funct3D(funct3D),
    .funct7b5D(funct7b5D),
    .SupportedD(SupportedD),
    .ZeroE(ZeroE),
    .CondBitE(CondBitE),
    .ResultSrcW(ResultSrcW),
    .ResultSrcM(ResultSrcM),
    .ResultSrcE(ResultSrcE),
    .MemWriteM(MemWriteM),
    .PCSrcE(PCSrcE),
    .ALUSrcE(ALUSrcE),
    .JalrE(JalrE),
    .RegWriteM(RegWriteM),
    .RegWriteW(RegWriteW),
    .ImmSrcD(ImmSrcD),
    .ALUControlE(ALUControlE)
  );

  hazardunit hu(
    .UsesRs1D(UsesRs1D), .UsesRs2D(UsesRs2D),
    .Rs1D(Rs1D),
    .Rs2D(Rs2D),
    .Rs1E(Rs1E),
    .Rs2E(Rs2E),
    .RdE(RdE),
    .RdM(RdM),
    .RdW(RdW),
    .ResultSrcE(ResultSrcE),
    .RegWriteM(RegWriteM),
    .RegWriteW(RegWriteW),
    .PCSrcE(PCSrcE),
    .StallF(HazardStallF),
    .StallD(HazardStallD),
    .FlushD(HazardFlushD),
    .FlushE(HazardFlushE),
    .ForwardAE(ForwardAE),
    .ForwardBE(ForwardBE)
  );

  datapath #(.ENABLE_XQDOT4Z(ENABLE_XQDOT4Z)) dp(
    .clk(clk),
    .reset(reset),
    .ResultSrcW(ResultSrcW),
    .ResultSrcM(ResultSrcM),
    .PCSrcE(PCSrcE),
    .ALUSrcE(ALUSrcE),
    .JalrE(JalrE),
    .RegWriteW(RegWriteW),
    .StallF(StallF),
    .StallD(StallD),
    .FlushD(FlushD),
    .FlushE(FlushE),
    .ForwardAE(ForwardAE),
    .ForwardBE(ForwardBE),
    .ImmSrcD(ImmSrcD),
    .ALUControlE(ALUControlE),
    .ZeroE(ZeroE),
    .CondBitE(CondBitE),
    .opD(opD),
    .funct3D(funct3D),
    .funct7b5D(funct7b5D),
    .SupportedD(SupportedD), .UsesRs1D(UsesRs1D), .UsesRs2D(UsesRs2D),
    .FetchFaultF(FetchFaultF),
    .FaultValidE(FaultValidE), .FaultCauseE(FaultCauseE), .FaultPCE(FaultPCE),
    .ValidM(ValidM), .ValidW(RetireValidW), .PCW(RetirePCW),
    .Rs1D(Rs1D),
    .Rs2D(Rs2D),
    .Rs1E(Rs1E),
    .Rs2E(Rs2E),
    .RdE(RdE),
    .RdM(RdM),
    .RdW(RdW),
    .PCF(PCF),
    .InstrF(InstrF),
    .ALUResultM(DataAdrM),
    .WriteDataM(WriteDataM),
    .ReadDataM(ReadDataM)
  );
endmodule
