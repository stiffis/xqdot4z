`timescale 1ns/1ps
`default_nettype none
module tb_scalar_mul;
  reg [31:0] lhs, rhs, expected;
  wire [31:0] result;
  reg [1023:0] line;
  reg [7:0] character;
  string path;
  integer fd, count, checked=0, size, index, parsed;
  scalar_mul dut(.lhs(lhs), .rhs(rhs), .result(result));
  initial begin
    if (!$value$plusargs("VECTORS=%s",path) ||
        !$value$plusargs("COUNT=%d",count) || count<=0)
      $fatal(1,"MUL_FAIL arguments");
    fd=$fopen(path,"r");
    if (fd==0) $fatal(1,"MUL_FAIL cannot open vectors");
    size=$fgets(line,fd);
    while (size!=0) begin
      // Exactly three eight-digit hex fields, spaces and LF: 27 bytes.
      if (size!=27 || line[7:0]!==8'h0a) $fatal(1,"MUL_FAIL malformed vector");
      for (index=1;index<27;index=index+1) begin
        character=line[8*index +: 8];
        if (index==9 || index==18) begin
          if (character!==8'h20) $fatal(1,"MUL_FAIL malformed vector");
        end else if (!((character>=8'h30 && character<=8'h39) ||
                       (character>=8'h61 && character<=8'h66)))
          $fatal(1,"MUL_FAIL malformed vector");
      end
      parsed=$sscanf(line,"%h %h %h",lhs,rhs,expected);
      if (parsed!=3) $fatal(1,"MUL_FAIL malformed vector");
      #1; // Delta settling only; no timing measurement.
      if (result!==expected) $fatal(1,"MUL_FAIL mismatch at %0d",checked);
      checked=checked+1;
      size=$fgets(line,fd);
    end
    $fclose(fd);
    if (checked!=count) $fatal(1,"MUL_FAIL count");
    $display("MUL_PASS checked=%0d",checked);
    $finish;
  end
endmodule
`default_nettype wire
