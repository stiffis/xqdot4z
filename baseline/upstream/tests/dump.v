module dump;
  initial begin
    $dumpfile("wave.vcd");
    $dumpvars(0, testbench);
  end
endmodule
