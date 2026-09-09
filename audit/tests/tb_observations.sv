`timescale 1ns/1ps
// Diagnostic probes of the unmodified historical core, not extension tests.
module tb_observations;
  reg [31:0] raw;
  wire [31:0] expanded;
  wire compressed;
  decompressor dc(raw, expanded, compressed);

  reg [4:0] rs1d, rs2d, rde;
  reg [1:0] result_src_e;
  wire stallf, stalld, flushd, flushe;
  wire [1:0] forwarda, forwardb;
  hazardunit hu(
    .Rs1D(rs1d), .Rs2D(rs2d), .Rs1E(5'd0), .Rs2E(5'd0),
    .RdE(rde), .RdM(5'd0), .RdW(5'd0), .ResultSrcE(result_src_e),
    .RegWriteM(1'b0), .RegWriteW(1'b0), .PCSrcE(1'b0),
    .StallF(stallf), .StallD(stalld), .FlushD(flushd), .FlushE(flushe),
    .ForwardAE(forwarda), .ForwardBE(forwardb));

  task probe_decode(input [255:0] name, input [31:0] insn,
                    input [31:0] expected);
    begin
      raw = insn;
      #1;
      $display("OBS|%0s|%08h|%08h", name, expected, expanded);
    end
  endtask

  initial begin
    raw = 0; rs1d = 0; rs2d = 0; rde = 0; result_src_e = 0;
    // Encodings and expansions are documented in docs/CORE_AUDIT.md.
    probe_decode("c_addi_control", 32'h00000285, 32'h00128293);
    probe_decode("rv32_passthrough", 32'h00100293, 32'h00100293);
    probe_decode("c_li", 32'h00004285, 32'h00100293);
    probe_decode("c_addi4spn", 32'h00000040, 32'h00410413);
    probe_decode("c_addi16sp", 32'h00006141, 32'h01010113);
    probe_decode("c_ebreak", 32'h00009002, 32'h00100073);
    // lw x5,... followed by addi x6,x0,5: instruction bits 24:20 = 5,
    // but ADDI does not read rs2. A data dependence does not exist.
    result_src_e = 2'b01; rde = 5; rs1d = 0; rs2d = 5;
    #1;
    $display("OBS|false_rs2_stall|%08h|%08h", 32'd0, {31'd0, stallf});
    // Control case: a real rs1 dependency must stall.
    rs1d = 5; rs2d = 0;
    #1;
    $display("OBS|real_load_use|%08h|%08h", 32'd1, {31'd0, stallf});
    $finish;
  end
endmodule
