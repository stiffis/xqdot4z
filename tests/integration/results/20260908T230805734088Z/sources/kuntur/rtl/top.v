module top #(parameter IMEM_WORDS = 64, parameter DMEM_WORDS = 64,
             parameter IMEM_FILE = "riscvtest.mem", parameter CHECKS = 1,
             parameter ENABLE_XQDOT4Z = 0, parameter ENABLE_MUL = 0)
          (input clk, reset,
           output [31:0] WriteData, DataAdr,
           output MemWrite,
           output Fault, output [1:0] FaultCause, output [31:0] FaultPC,
           output MemoryFault,
           output RetireValid, output [31:0] RetirePC);
  
  wire [31:0] PCF, InstrF, ReadData;
  wire FetchFault, MemRead;
  
  riscvpipe #(.ENABLE_XQDOT4Z(ENABLE_XQDOT4Z), .ENABLE_MUL(ENABLE_MUL)) rvpipe(
    .clk(clk),
    .reset(reset),
    .PCF(PCF),
    .InstrF(InstrF),
    .MemWriteM(MemWrite),
    .DataAdrM(DataAdr),
    .WriteDataM(WriteData),
    .ReadDataM(ReadData), .FetchFaultF(FetchFault), .MemReadM(MemRead),
    .Fault(Fault), .FaultCause(FaultCause), .FaultPC(FaultPC),
    .RetireValidW(RetireValid), .RetirePCW(RetirePC)
  );

  imem #(.WORDS(IMEM_WORDS), .INIT_FILE(IMEM_FILE)) imem(
    .a(PCF),
    .rd(InstrF), .access_fault(FetchFault)
  );

  dmem #(.WORDS(DMEM_WORDS)) dmem(
    .clk(clk),
    .we(MemWrite),
    .re(MemRead),
    .a(DataAdr),
    .wd(WriteData),
    .rd(ReadData), .access_fault(MemoryFault)
  );

  // Model diagnostics, not architectural exception handlers.
  // CHECKS=0 is used only by directed tests which inspect the fault outputs.
  generate if (CHECKS) begin : simulation_checks
`ifndef SYNTHESIS
  always @(negedge clk) if (!reset) begin
    if (Fault) $fatal(1, "Instruction fault: cause=%0d pc=%08h", FaultCause, FaultPC);
    if (MemoryFault || ((MemRead || MemWrite) && (^DataAdr === 1'bx)))
      $fatal(1, "Data memory fault: address=%08h", DataAdr);
  end
`endif
  end endgenerate
endmodule
