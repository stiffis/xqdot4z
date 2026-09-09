`timescale 1ns/1ps
module tb_mul_decode;
  reg [31:0] instr;
  wire [3:0] supported, breakpoint, a, b;
  reg expected_base, expected;
  integer f7, f3, layout, config_id, checked=0;
  genvar g;
  generate for (g=0;g<4;g=g+1) begin : policies
    instruction_policy #(.ENABLE_MUL(g/2), .ENABLE_XQDOT4Z(g%2)) dut(
      .instr(instr), .supported(supported[g]), .breakpoint(breakpoint[g]),
      .uses_rs1(a[g]), .uses_rs2(b[g]));
  end endgenerate
  initial begin
    for (f7=0;f7<128;f7=f7+1)
      for (f3=0;f3<8;f3=f3+1)
        for (layout=0;layout<32;layout=layout+1) begin
          instr=(32'(f7)<<25) | (32'(31-layout)<<20) | (32'(layout)<<15) |
                (32'(f3)<<12) | (32'((layout+7)%32)<<7) | 32'h33;
          // Independent enumeration of supported base OP tuples.
          expected_base=(f7==0 && f3!=3) || (f7==32 && (f3==0 || f3==5));
          #1;
          for (config_id=0;config_id<4;config_id=config_id+1) begin
            expected=expected_base || (config_id>=2 && f7==1 && f3==0);
            if (supported[config_id]!==expected || a[config_id]!==expected ||
                b[config_id]!==expected || breakpoint[config_id]!==0)
              $fatal(1,"MUL_DECODE_FAIL instr=%h config=%0d",instr,config_id);
            checked=checked+1;
          end
        end
    $display("MUL_DECODE_PASS checked=%0d",checked); $finish;
  end
endmodule
