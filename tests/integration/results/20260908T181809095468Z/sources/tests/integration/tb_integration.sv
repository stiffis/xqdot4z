`timescale 1ns/1ps
module tb_integration;
  parameter ENABLE=1;
  reg clk=0, reset=1;
  always #5 clk=~clk;
  wire [31:0] wd, address, faultpc, retirepc;
  wire we, fault, memoryfault, retire;
  wire [1:0] cause;
  string program_file;
  integer words, i, cycles=0, reset_pc=-1;
  reg reset_done=0;
  top #(.IMEM_WORDS(8192), .DMEM_WORDS(64), .IMEM_FILE(""), .CHECKS(0),
        .ENABLE_XQDOT4Z(ENABLE)) dut(
    .clk(clk),.reset(reset),.WriteData(wd),.DataAdr(address),.MemWrite(we),
    .Fault(fault),.FaultCause(cause),.FaultPC(faultpc),.MemoryFault(memoryfault),
    .RetireValid(retire),.RetirePC(retirepc));
  initial begin
    if (!$value$plusargs("PROGRAM=%s",program_file) || !$value$plusargs("WORDS=%d",words))
      $fatal(1,"M3_FAIL missing program arguments");
    if (words<=0 || words>8192) $fatal(1,"M3_FAIL program size");
    if ($value$plusargs("RESET_PC=%d",reset_pc)) begin end
    for (i=0;i<8192;i=i+1) dut.imem.RAM[i]=32'h00100073;
    for (i=0;i<64;i=i+1) dut.dmem.RAM[i]=0;
    $readmemh(program_file,dut.imem.RAM,0,words-1);
    #22; reset=0;
    wait(fault);
    repeat(4) @(negedge clk);
    #1;
    if (reset_pc>=0 && !reset_done) $fatal(1,"M3_FAIL reset trigger not reached");
    $display("FAULT|%0d|%08h",cause,faultpc);
    for (i=1;i<32;i=i+1) $display("REG|%0d|%08h",i,dut.rvpipe.dp.rf.rf[i]);
    $display("M3_PASS diagnostic stop"); $finish;
  end
  always @(posedge clk) if (!reset) begin
    cycles=cycles+1;
    if (cycles>25000) $fatal(1,"M3_FAIL pipeline timeout");
    if (memoryfault) $fatal(1,"M3_FAIL data memory fault");
    if (we) $display("STORE|%08h|%08h",address,wd);
    if (dut.rvpipe.HazardStallF) $display("STALL");
  end
  always @(negedge clk) if (!reset) begin
    if (dut.rvpipe.RegWriteW && !retire) $fatal(1,"M3_FAIL write without retirement");
    if (retire) begin
      if (dut.rvpipe.RegWriteW && dut.rvpipe.RdW!=0)
        $display("RETIRE|%08h|%0d|%08h",retirepc,dut.rvpipe.RdW,dut.rvpipe.dp.ResultW);
      else $display("RETIRE|%08h|0|00000000",retirepc);
    end
    if (dut.rvpipe.dp.ValidE && dut.rvpipe.dp.QDotE)
      $display("QEXEC|%08h|%h|%h|%h|%h|%0d|%0d",dut.rvpipe.dp.PCE,
               dut.rvpipe.dp.SrcAE,dut.rvpipe.dp.WriteDataE,
               dut.rvpipe.dp.QDotZeroE,dut.rvpipe.dp.QDotHalfE,
               dut.rvpipe.ForwardAE,dut.rvpipe.ForwardBE);
  end
  // Interrupt a QDot in E, away from all clock edges. Registers do not reset;
  // only this in-flight operation and pipeline validity must be cancelled.
  always @(posedge clk) begin
    #2;
    if (!reset && !reset_done && reset_pc>=0 && dut.rvpipe.dp.ValidE &&
        dut.rvpipe.dp.QDotE && dut.rvpipe.dp.PCE==32'(reset_pc)) begin
      reset=1; reset_done=1;
      #1;
      if (dut.rvpipe.dp.QDotE !== 0 || retire !== 0 || we !== 0 || fault !== 0)
        $fatal(1,"M3_FAIL asynchronous reset left live controls");
      // Restart at an EBREAK, preserving the register and data memories.
      dut.imem.RAM[0]=32'h00100073;
      #10; reset=0;
      $display("RESET_PASS cancelled_pc=%08h",reset_pc);
    end
  end
endmodule
