`timescale 1ns/1ps
module tb_memory;
  reg clk=0, we=0, re=0;
  always #5 clk=~clk;
  reg [31:0] ia, da, wd;
  wire [31:0] ir, dr;
  wire ifault, dfault;
  imem #(.WORDS(2), .INIT_FILE("")) im(ia, ir, ifault);
  dmem #(.WORDS(2)) dm(clk, we, re, da, wd, dr, dfault);
  initial begin
    im.RAM[0]=32'h00130001; im.RAM[1]=32'h00010000;
    dm.RAM[0]=32'h12345678; dm.RAM[1]=0;
    ia=2; da=0; wd=0; #1;
    if (ifault !== 0 || ir !== 32'h00000013) $fatal(1,"Cross-word fetch");
    ia=6; #1;
    if (ifault !== 0 || ir[15:0] !== 16'h0001) $fatal(1,"Final compressed halfword");
    im.RAM[1]=32'h00130000; #1;
    if (ifault !== 1) $fatal(1,"Truncated final 32-bit instruction accepted");
    ia=8; #1; if (ifault !== 1) $fatal(1,"Out-of-range fetch accepted");
    ia=1; #1; if (ifault !== 1) $fatal(1,"Odd fetch accepted");
    @(negedge clk); we=1; da=2; wd=32'hdeadbeef; #1;
    if (dfault !== 1) $fatal(1,"Misaligned store accepted");
    @(negedge clk); we=0;
    if (dm.RAM[0] !== 32'h12345678) $fatal(1,"Misaligned store corrupted memory");
    we=1; da=8; #1; if (dfault !== 1) $fatal(1,"Out-of-range store accepted");
    @(negedge clk); we=0; re=1; da=2; #1;
    if (dfault !== 1 || dr !== 0) $fatal(1,"Misaligned load not rejected");
    da=8; #1; if (dfault !== 1 || dr !== 0) $fatal(1,"Out-of-range load not rejected");
    re=0; #1; if (dfault !== 0) $fatal(1,"Inactive bus reported fault");
    da=4; wd=32'hcafef00d; we=1;
    @(negedge clk); we=0; re=1; #1;
    if (dfault !== 0 || dr !== 32'hcafef00d) $fatal(1,"Last valid data word");
    $display("PASS memory boundaries/alignment"); $finish;
  end
endmodule
