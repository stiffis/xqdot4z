`timescale 1ns/1ps
module tb_decode;
  reg [31:0] instr;
  wire yes_on, bp_on, a_on, b_on, yes_off, bp_off, a_off, b_off;
  integer f7, f3, rd, count=0;
  reg expected;
  instruction_policy #(.ENABLE_XQDOT4Z(1)) enabled(instr,yes_on,bp_on,a_on,b_on);
  instruction_policy disabled(instr,yes_off,bp_off,a_off,b_off);
  initial begin
    for (f7=0; f7<128; f7=f7+1)
      for (f3=0; f3<8; f3=f3+1)
        for (rd=0; rd<32; rd=rd+1) begin
          instr = (f7 << 25) | ((31-rd) << 20) | (rd << 15) | (f3 << 12) | (rd << 7) | 32'h0b;
          expected = (f7 % 4 == 0) && (f3 == 0);
          #1;
          if ({yes_on,bp_on,a_on,b_on} !== {expected,1'b0,expected,expected})
            $fatal(1,"M3_FAIL decode enabled instr=%h",instr);
          if ({yes_off,bp_off,a_off,b_off} !== 4'b0)
            $fatal(1,"M3_FAIL decode disabled instr=%h",instr);
          count=count+1;
        end
    $display("DECODE_PASS checked=%0d",count); $finish;
  end
endmodule
