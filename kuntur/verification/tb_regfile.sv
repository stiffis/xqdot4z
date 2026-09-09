`timescale 1ns/1ps
module tb_regfile;
  reg clk=0, we=0;
  reg [4:0] a1=0, a2=1, a3=0;
  reg [31:0] wd=0;
  wire [31:0] rd1, rd2;
  always #5 clk=~clk;
  regfile dut(clk,we,a1,a2,a3,wd,rd1,rd2);
  initial begin
    // The file is intentionally not reset; seed only what this test observes.
    dut.rf[0]=32'h12345678; dut.rf[1]=0;
    #1;
    if (rd1 !== 0) $fatal(1,"Architectural x0 read");
    we=1; wd=32'hdeadbeef;
    @(negedge clk); #1;
    if (rd1 !== 0 || dut.rf[0] !== 32'h12345678)
      $fatal(1,"Physical write to x0 was not suppressed");
    a3=1; wd=32'hcafef00d;
    @(posedge clk); #1;
    if (rd2 !== 0) $fatal(1,"Register changed before falling edge");
    @(negedge clk); #1;
    if (rd2 !== 32'hcafef00d) $fatal(1,"Falling-edge write failed");
    we=0; wd=0;
    @(negedge clk); #1;
    if (rd2 !== 32'hcafef00d) $fatal(1,"Disabled write changed register");
    $display("PASS regfile x0 and falling-edge writes"); $finish;
  end
endmodule
