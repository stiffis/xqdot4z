`timescale 1ns/1ps
module tb_policy_hazards;
  reg [31:0] insn;
  wire supported, breakpoint, uses1, uses2;
  reg [4:0] rde;
  reg [1:0] src;
  wire sf, sd, fd, fe;
  wire [1:0] fa, fb;
  integer count=0;
  instruction_policy policy(insn, supported, breakpoint, uses1, uses2);
  hazardunit hu(.Rs1D(insn[19:15]), .Rs2D(insn[24:20]), .UsesRs1D(uses1), .UsesRs2D(uses2),
    .Rs1E(5'd0), .Rs2E(5'd0), .RdE(rde), .RdM(5'd0), .RdW(5'd0),
    .ResultSrcE(src), .RegWriteM(1'b0), .RegWriteW(1'b0), .PCSrcE(1'b0),
    .StallF(sf), .StallD(sd), .FlushD(fd), .FlushE(fe), .ForwardAE(fa), .ForwardBE(fb));
  task check(input [31:0] word, input [3:0] expected, input stall);
    begin
      insn=word; #1;
      if ({supported,breakpoint,uses1,uses2} !== expected || sf !== stall || sd !== stall)
        $fatal(1,"Policy/hazard word=%08h flags=%04b stall=%b",word,{supported,breakpoint,uses1,uses2},sf);
      count=count+1;
    end
  endtask
  initial begin
    rde=5; src=1;
    check(32'h00500313, 4'b1010, 0); // addi x6,x0,5: rs2 bits are immediate
    check(32'h00128313, 4'b1010, 1); // addi x6,x5,1: real rs1 dependency
    check(32'h00502323, 4'b1011, 1); // sw x5,6(x0): source usage (address checked separately)
    check(32'h00500337, 4'b1000, 0); // lui: no source registers
    check(32'h0050036f, 4'b1000, 0); // jal: no source registers
    check(32'h000280e7, 4'b1010, 1); // jalr reads rs1 only
    check(32'h02528333, 4'b0000, 0); // MUL is excluded, not ADD
    check(32'h00028303, 4'b0000, 0); // LB is excluded, not LW
    check(32'h00029303, 4'b0000, 0); // LH excluded
    check(32'h00500023, 4'b0000, 0); // SB excluded
    check(32'h00003313, 4'b0000, 0); // SLTIU excluded
    check(32'h0052e063, 4'b0000, 0); // BLTU excluded
    check(32'h00000317, 4'b0000, 0); // AUIPC excluded
    check(32'h02029313, 4'b0000, 0); // invalid RV32 SLLI
    check(32'h0202d313, 4'b0000, 0); // invalid RV32 SRLI
    check(32'h4002d313, 4'b1010, 1); // SRAI supported
    check(32'h00100073, 4'b0100, 0); // breakpoint separate from illegal
    check(32'h00000073, 4'b0000, 0); // ECALL not implemented
    check(32'h00000000, 4'b0000, 0);
    rde=0; check(32'h00000313, 4'b1010, 0); // load to x0 does not produce dependency
    src=0; rde=5; check(32'h00128313, 4'b1010, 0);
    $display("PASS policy/hazards cases=%0d",count); $finish;
  end
endmodule
