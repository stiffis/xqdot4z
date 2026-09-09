module imem #(parameter WORDS = 64, parameter INIT_FILE = "riscvtest.mem")
           (input [31:0] a, output reg [31:0] rd, output reg access_fault);
  
  reg [31:0] RAM[0:WORDS-1];
  localparam INDEX_BITS = (WORDS > 1) ? $clog2(WORDS) : 1;
  wire [INDEX_BITS-1:0] word_index = a[INDEX_BITS+1:2];
  reg [31:0] w0;

  initial begin
    if (INIT_FILE != "") $readmemh(INIT_FILE, RAM);
  end

  always @* begin
    rd = 0; w0 = 0; access_fault = 1;
    if (!a[0] && a[31:2] < WORDS) begin
      w0 = RAM[word_index];
      if (!a[1]) begin rd = w0; access_fault = 0; end
      else if (w0[17:16] != 2'b11) begin
        // A final compressed halfword does not need the next word.
        rd = {16'b0, w0[31:16]}; access_fault = 0;
      end else if (a[31:2] < WORDS-1) begin
        rd = {RAM[word_index+1'b1][15:0], w0[31:16]}; access_fault = 0;
      end
    end
  end
endmodule
