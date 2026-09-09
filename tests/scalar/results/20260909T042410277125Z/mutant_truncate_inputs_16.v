// RV32 MUL only: the low 32 bits of a 32-by-32-bit product.
// Signed and unsigned interpretations have identical low halves (mod 2^32).
// The 32-bit expression width/truncation is intentional; no high-half result.
// Combinational functional prototype, not a physical timing guarantee.
module scalar_mul(input [31:0] lhs, rhs, output [31:0] result);
  assign result = lhs[15:0] * rhs[15:0];
endmodule
