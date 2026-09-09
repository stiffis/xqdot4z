module dmem #(parameter WORDS = 64)(input clk, we, re,
            input  [31:0] a, wd,
            output [31:0] rd,
            output access_fault);
  
  reg [31:0] RAM[0:WORDS-1];
  localparam INDEX_BITS = (WORDS > 1) ? $clog2(WORDS) : 1;
  wire [INDEX_BITS-1:0] word_index = a[INDEX_BITS+1:2];
  wire address_ok = (a[1:0] == 0) && (a[31:2] < WORDS);

  assign rd = (re && address_ok) ? RAM[word_index] : 32'b0;
  assign access_fault = (re || we) && !address_ok;

  always @(posedge clk) begin
    if (we && address_ok) RAM[word_index] <= wd;
  end
endmodule
