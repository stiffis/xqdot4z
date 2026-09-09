`timescale 1ns/1ps
module tb_slt;
  reg [64:0] vectors[0:20000];
  reg [31:0] a, b;
  wire [31:0] result;
  wire zero;
  integer count, i;
  reg [1023:0] path;
  alu dut(a, b, 4'b0101, result, zero);
  initial begin
    if (!$value$plusargs("vectors=%s", path) || !$value$plusargs("count=%d", count))
      $fatal(1, "Missing vector file/count");
    $readmemh(path, vectors, 0, count-1);
    for (i=0; i<count; i=i+1) begin
      a=vectors[i][63:32]; b=vectors[i][31:0]; #1;
      if (result !== {31'b0,vectors[i][64]} || zero !== !vectors[i][64])
        $fatal(1, "SLT a=%08h b=%08h result=%08h expected=%b", a,b,result,vectors[i][64]);
    end
    $display("PASS signed comparison vectors=%0d", count); $finish;
  end
endmodule
