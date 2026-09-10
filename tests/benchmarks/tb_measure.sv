`timescale 1ns/1ps
// Measurement harness for the comparison campaign.
//
// The window runs from the acceptance of the instruction at BEGIN_PC to the
// retirement of the instruction at END_PC, as required by the protocol. It
// observes the pipeline hierarchically and adds no instruction to the kernel,
// so the same text is measured that the variant would run unobserved.
// Counters are structural events of this model, not physical timing.
module tb_measure;
  // Common instruction capacity for every variant and arm, sized once the
  // kernels existed: the largest is B1's straight-line twin at N=16, near
  // twenty thousand words. Fetch is combinational, so capacity costs no cycle.
  localparam IMEM = 32768;
  parameter ENABLE_QDOT=0;
  parameter ENABLE_MUL=0;
  parameter ENABLE_PACKED=0;
  reg clk=0, reset=1;
  always #5 clk=~clk;
  wire [31:0] wd, address, faultpc, retirepc;
  wire we, fault, memoryfault, retire;
  wire [1:0] cause;
  string program_file;
  integer words, i, elapsed=0, trace=0, begin_pc=-1, end_pc=-1, text_end=-1;
  reg active=0, started=0, closed=0;
  integer start_cycle=0;
  // Running window counters, advanced once per cycle from the start event.
  integer w_cycles=0, w_retired=0, w_kernel=0, w_stores=0, w_loads=0, w_regwrites=0;
  integer w_stall_load_use=0, w_stall_fault_hold=0, w_flush_taken=0;
  // Snapshot of the last END_PC retirement: a looping kernel retires that PC
  // once per row, and the window closes at the final one.
  integer s_cycles=0, s_retired=0, s_kernel=0, s_stores=0, s_loads=0, s_regwrites=0;
  integer s_stall_load_use=0, s_stall_fault_hold=0, s_flush_taken=0, s_end_cycle=0;

  top #(.IMEM_WORDS(IMEM), .DMEM_WORDS(1024), .IMEM_FILE(""), .CHECKS(0),
        .ENABLE_XQDOT4Z(ENABLE_QDOT), .ENABLE_MUL(ENABLE_MUL),
        .ENABLE_XQDOT4(ENABLE_PACKED)) dut(
    .clk(clk),.reset(reset),.WriteData(wd),.DataAdr(address),.MemWrite(we),
    .Fault(fault),.FaultCause(cause),.FaultPC(faultpc),.MemoryFault(memoryfault),
    .RetireValid(retire),.RetirePC(retirepc));

  // Static extent of the kernel text. In a looping kernel the closing PC is
  // the output store, which is not the last instruction of the body, so
  // attribution needs the text range and not the window's closing PC.
  function automatic bit in_kernel(input [31:0] pc);
    in_kernel = (pc>=32'(begin_pc)) && (pc<=32'(text_end));
  endfunction

  initial begin
    if (!$value$plusargs("PROGRAM=%s",program_file) || !$value$plusargs("WORDS=%d",words))
      $fatal(1,"MEASURE_FAIL missing program arguments");
    if (!$value$plusargs("BEGIN_PC=%d",begin_pc) || !$value$plusargs("END_PC=%d",end_pc) ||
        !$value$plusargs("TEXT_END=%d",text_end))
      $fatal(1,"MEASURE_FAIL missing window arguments");
    if (end_pc<begin_pc || text_end<end_pc) $fatal(1,"MEASURE_FAIL inconsistent window");
    if (words<=0 || words>IMEM) $fatal(1,"MEASURE_FAIL program size");
    if ($value$plusargs("TRACE=%d",trace)) begin end
    for (i=0;i<IMEM;i=i+1) dut.imem.RAM[i]=32'h00100073;
    for (i=0;i<1024;i=i+1) dut.dmem.RAM[i]=0;
    $readmemh(program_file,dut.imem.RAM,0,words-1);
    #22; reset=0;
    wait(fault);
    repeat(4) @(negedge clk);
    #1;
    if (!started) $fatal(1,"MEASURE_FAIL window never opened");
    if (!closed) $fatal(1,"MEASURE_FAIL window never closed");
    $display("WINDOW|%0d|%0d",start_cycle,s_end_cycle);
    $display("MEASURE|cycles|%0d",s_cycles);
    $display("MEASURE|retired|%0d",s_retired);
    $display("MEASURE|retired_kernel|%0d",s_kernel);
    $display("MEASURE|retired_stores|%0d",s_stores);
    $display("MEASURE|retired_loads|%0d",s_loads);
    $display("MEASURE|register_writes|%0d",s_regwrites);
    $display("MEASURE|stall_load_use|%0d",s_stall_load_use);
    $display("MEASURE|stall_fault_hold|%0d",s_stall_fault_hold);
    $display("MEASURE|flush_taken_control|%0d",s_flush_taken);
    $display("MEASURE|data_read_bytes|%0d",4*s_loads);
    $display("MEASURE|data_write_bytes|%0d",4*s_stores);
    $display("MEASURE_PASS window closed"); $finish;
  end

  always @(posedge clk) if (!reset) begin
    elapsed=elapsed+1;
    if (elapsed>200000) $fatal(1,"MEASURE_FAIL pipeline timeout");
    if (memoryfault) $fatal(1,"MEASURE_FAIL data memory fault");
  end

  always @(negedge clk) if (!reset) begin
    // Acceptance: the first cycle the kernel's first instruction is valid in
    // decode. A flushed speculative pass leaves ValidD low and does not open
    // the window.
    if (!started && dut.rvpipe.dp.ValidD && dut.rvpipe.dp.PCD==32'(begin_pc)) begin
      started=1; active=1; start_cycle=elapsed;
    end
    if (active) begin
      w_cycles=w_cycles+1;
      if (dut.rvpipe.HazardStallF) w_stall_load_use=w_stall_load_use+1;
      // Only a fault raised by a kernel instruction holds the measured window.
      // Every program ends on a diagnostic EBREAK placed after END_PC, and
      // that one must not be attributed to the kernel.
      if ((dut.rvpipe.FaultValidE && in_kernel(dut.rvpipe.FaultPCE)) ||
          (fault && in_kernel(faultpc))) w_stall_fault_hold=w_stall_fault_hold+1;
      if (dut.rvpipe.PCSrcE) w_flush_taken=w_flush_taken+1;
      // The data address trace the pilot compares, and the outputs a kernel
      // must produce; both are traced together with retirements.
      if (we) begin
        w_stores=w_stores+1;
        if (trace!=0) $display("STORE|%08h|%08h",address,wd);
      end
      if (dut.rvpipe.MemReadM) begin
        w_loads=w_loads+1;
        if (trace!=0) $display("LOAD|%08h",address);
      end
      // Retirement counts instructions; a register write is reported apart so
      // the two are never conflated, and a stall never yields two retirements.
      if (retire) begin
        w_retired=w_retired+1;
        // Instructions accepted before the window can still retire inside it,
        // so the kernel's own retirements are counted apart from the total.
        if (in_kernel(retirepc)) w_kernel=w_kernel+1;
        if (dut.rvpipe.RegWriteW && dut.rvpipe.RdW!=0) w_regwrites=w_regwrites+1;
        if (trace!=0) $display("RETIRED|%08h",retirepc);
      end
      if (retire && retirepc==32'(end_pc)) begin
        closed=1; s_end_cycle=elapsed;
        s_cycles=w_cycles; s_retired=w_retired; s_stores=w_stores; s_loads=w_loads;
        s_kernel=w_kernel; s_regwrites=w_regwrites; s_stall_load_use=w_stall_load_use;
        s_stall_fault_hold=w_stall_fault_hold; s_flush_taken=w_flush_taken;
      end
    end
  end
endmodule
