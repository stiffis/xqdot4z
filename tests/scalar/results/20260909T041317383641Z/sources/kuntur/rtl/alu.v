module alu(input  [31:0] a, b,
           input  [3:0]  alucontrol,
           output [31:0] result,
           output zero);
  
  wire [31:0] condinvb, sum;

  reg [31:0] result_reg;
  assign result = result_reg;

  assign condinvb = alucontrol[0] ? ~b : b;
  assign sum = a + condinvb + alucontrol[0];

  always @* case (alucontrol)
      4'b0000: result_reg = sum; // add
      4'b0001: result_reg = sum; // subtract
      4'b0010: result_reg = a & b; // and
      4'b0011: result_reg = a | b; // or
      4'b0100: result_reg = a ^ b; // xor
      // Compare signed operands directly; sign of subtraction alone is wrong
      // when opposite-sign operands overflow a 32-bit subtraction.
      4'b0101: result_reg = {31'b0, ($signed(a) < $signed(b))}; // slt
      4'b0110: result_reg = b; // lui pass-through immediate
      4'b0111: result_reg = a << b[4:0]; // sll
      4'b1000: result_reg = a >> b[4:0]; // srl
      4'b1001: result_reg = $signed(a) >>> b[4:0]; // sra
      default: result_reg = 32'bx;
    endcase

  assign zero = (result == 32'b0);
endmodule
