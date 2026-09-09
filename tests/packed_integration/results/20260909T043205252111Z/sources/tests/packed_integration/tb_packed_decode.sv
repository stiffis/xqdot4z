`timescale 1ns/1ps
module tb_packed_decode;
  reg [31:0] instr;
  wire [7:0] supported, breakpoint, a, b;
  reg expected;
  integer op_select, f7, f3, layout, cfg, checked=0;
  genvar g;
  generate for (g=0;g<8;g=g+1) begin : policies
    instruction_policy #(.ENABLE_MUL(g/4), .ENABLE_XQDOT4Z((g/2)%2),
                          .ENABLE_XQDOT4(g%2)) dut(
      .instr(instr), .supported(supported[g]), .breakpoint(breakpoint[g]),
      .uses_rs1(a[g]), .uses_rs2(b[g]));
  end endgenerate
  initial begin
    for (op_select=0;op_select<2;op_select=op_select+1)
      for (f7=0;f7<128;f7=f7+1)
        for (f3=0;f3<8;f3=f3+1)
          for (layout=0;layout<32;layout=layout+1) begin
            instr=(32'(f7)<<25) | (32'(31-layout)<<20) | (32'(layout)<<15) |
                  (32'(f3)<<12) | (32'((layout+7)%32)<<7) |
                  (op_select==0 ? 32'h0b : 32'h2b);
            #1;
            for (cfg=0;cfg<8;cfg=cfg+1) begin
              if (op_select==0) expected=((cfg/2)%2==1) && f7%4==0 && f3==0;
              else expected=(cfg%2==1) && (f7==0 || f7==4) && f3==0;
              if (supported[cfg]!==expected || breakpoint[cfg]!==0 ||
                  a[cfg]!==expected || b[cfg]!==expected)
                $fatal(1,"PACKED_DECODE_FAIL instr=%h config=%0d",instr,cfg);
              checked=checked+1;
            end
          end
    $display("PACKED_DECODE_PASS checked=%0d",checked); $finish;
  end
endmodule
