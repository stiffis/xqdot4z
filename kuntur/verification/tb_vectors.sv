`timescale 1ns/1ps
module tb_vectors;
  reg [64:0] vectors[0:65535];
  reg [31:0] raw;
  wire [31:0] expanded;
  wire compressed, illegal;
  integer count, i;
  reg [1023:0] path;
  decompressor dut(.instrraw(raw), .instr(expanded), .compressed(compressed), .illegal(illegal));
  initial begin
    if (!$value$plusargs("vectors=%s", path) || !$value$plusargs("count=%d", count))
      $fatal(1, "Missing vector file/count");
    if (count > 65536) $fatal(1, "Vector capacity exceeded");
    $readmemh(path, vectors, 0, count-1);
    for (i=0; i<count; i=i+1) begin
      raw = vectors[i][31:0]; #1;
      if ({illegal, expanded} !== vectors[i][64:32] || compressed !== (raw[1:0] != 3))
        $fatal(1, "Decompression vector %0d raw=%08h expected=%09h actual=%09h",
               i, raw, vectors[i][64:32], {illegal, expanded});
    end
    $display("PASS decompressor vectors=%0d", count); $finish;
  end
endmodule
