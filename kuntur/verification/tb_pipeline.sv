`timescale 1ns/1ps
module tb_pipeline;
  parameter WORDS=64;
  reg clk=0, reset=1;
  always #5 clk=~clk;
  wire [31:0] wd, address, faultpc, retirepc;
  wire we, fault, memoryfault, retire;
  wire [1:0] cause;
  integer cycles=0;
  top #(.IMEM_WORDS(WORDS), .CHECKS(0)) dut(
    .clk(clk), .reset(reset), .WriteData(wd), .DataAdr(address), .MemWrite(we),
    .Fault(fault), .FaultCause(cause), .FaultPC(faultpc), .MemoryFault(memoryfault),
    .RetireValid(retire), .RetirePC(retirepc));
  initial begin
    #22; reset=0;
    wait(fault);
    // Drain older M/W instructions; the faulting instruction must not retire.
    repeat(4) @(negedge clk);
    #1;
    $display("FAULT|%0d|%08h", cause,faultpc);
    $display("REG3|%08h",dut.rvpipe.dp.rf.rf[3]);
    reset=1; #1;
    if (fault !== 0 || retire !== 0) $fatal(1,"Asynchronous reset did not clear fault/validity");
    $display("PASS pipeline completed diagnostic stop"); $finish;
  end
  always @(posedge clk) if (!reset) begin
    cycles=cycles+1;
    if (cycles>500) $fatal(1,"Pipeline timeout");
    if (memoryfault) $fatal(1,"Unexpected data memory fault");
    if (we) $display("STORE|%08h|%08h",address,wd);
    if (dut.rvpipe.HazardStallF) $display("STALL");
  end
  // One W-stage observation per cycle, aligned with the register-write edge.
  always @(negedge clk) if (!reset && retire) $display("RETIRE|%08h",retirepc);
endmodule
