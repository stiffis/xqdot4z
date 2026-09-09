module imem(input  [31:0] a,
            output [31:0] rd);
  
  reg [31:0] RAM[63:0];
  wire [31:0] w0, w1;

  initial begin
    $readmemh("riscvtest.mem", RAM);
  end

  assign w0 = RAM[a[31:2]];
  assign w1 = RAM[a[31:2] + 1];
  assign rd = a[1] ? {w1[15:0], w0[31:16]} : w0;
endmodule
