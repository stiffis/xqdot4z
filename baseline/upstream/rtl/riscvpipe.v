module riscvpipe(input  clk, reset,
                 output [31:0] PCF,
                 input  [31:0] InstrF,
                 output MemWriteM,
                 output [31:0] DataAdrM,
                 output [31:0] WriteDataM,
                 input  [31:0] ReadDataM);
  
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

  controller c(
    .clk(clk),
    .reset(reset),
    .FlushE(FlushE),
    .opD(opD),
    .funct3D(funct3D),
    .funct7b5D(funct7b5D),
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
    .StallF(StallF),
    .StallD(StallD),
    .FlushD(FlushD),
    .FlushE(FlushE),
    .ForwardAE(ForwardAE),
    .ForwardBE(ForwardBE)
  );

  datapath dp(
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
