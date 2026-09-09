module decompressor(input  [31:0] instrraw,
                    output reg [31:0] instr,
                    output        compressed);

  wire [15:0] c      = instrraw[15:0];
  wire [1:0]  op     = c[1:0];
  wire [2:0]  funct3 = c[15:13];
  wire [4:0]  rd     = c[11:7];
  wire [4:0]  rs2    = c[6:2];
  wire [4:0]  shamt  = c[6:2];
  wire [4:0]  rdp    = {2'b01, c[9:7]};
  wire [4:0]  rs2p   = {2'b01, c[4:2]};
  wire [4:0]  rs1p   = {2'b01, c[9:7]};
  wire [11:0] immci  = {{7{c[12]}}, c[6:2]};
  wire [19:0] immlui = {{15{c[12]}}, c[6:2]};
  wire [6:0]  offlw  = {c[5], c[12:10], c[6], 2'b00};
  wire [7:0]  offsp  = {c[3:2], c[12], c[6:4], 2'b00};
  wire [7:0]  offssp = {c[8:7], c[12:9], 2'b00};
  wire [8:0]  offcb  = {c[12], c[6:5], c[2], c[11:10], c[4:3], 1'b0};
  wire [11:0] offcj  = {c[12], c[8], c[10], c[9], c[6], c[7],
                        c[2], c[11], c[5:3], 1'b0};

  assign compressed = (op != 2'b11);

  always @* begin
    instr = instrraw;
    if (compressed) begin
      case ({op, funct3})
        5'b00_010: instr = {5'b0, offlw, rs1p, 3'b010, rs2p, 7'b0000011};
        5'b00_110: instr = {5'b0, offlw[6:5], rs2p, rs1p, 3'b010,
                             offlw[4:2], 2'b00, 7'b0100011};
        5'b01_000: instr = {immci, rd, 3'b000, rd, 7'b0010011};
        5'b01_001: instr = {offcj[11], offcj[10:1], offcj[11],
                             {8{offcj[11]}}, 5'b00001, 7'b1101111}; // c.jal
        5'b01_011: instr = {immlui, rd, 7'b0110111};
        5'b01_100:
          case (c[11:10])
            2'b00: instr = {7'b0000000, shamt, rdp, 3'b101, rdp, 7'b0010011};
            2'b01: instr = {7'b0100000, shamt, rdp, 3'b101, rdp, 7'b0010011};
            2'b10: instr = {immci, rdp, 3'b111, rdp, 7'b0010011};
            2'b11:
              case (c[6:5])
                2'b00: instr = {7'b0100000, rs2p, rdp, 3'b000, rdp, 7'b0110011};
                2'b01: instr = {7'b0000000, rs2p, rdp, 3'b100, rdp, 7'b0110011};
                2'b10: instr = {7'b0000000, rs2p, rdp, 3'b110, rdp, 7'b0110011};
                2'b11: instr = {7'b0000000, rs2p, rdp, 3'b111, rdp, 7'b0110011};
              endcase
          endcase
        5'b01_101: instr = {offcj[11], offcj[10:1], offcj[11],
                             {8{offcj[11]}}, 5'b00000, 7'b1101111}; // c.j
        5'b01_110: instr = {offcb[8], {3{offcb[8]}}, offcb[7:5],
                             5'b00000, rs1p, 3'b000, offcb[4:1],
                             offcb[8], 7'b1100011}; // c.beqz
        5'b01_111: instr = {offcb[8], {3{offcb[8]}}, offcb[7:5],
                             5'b00000, rs1p, 3'b001, offcb[4:1],
                             offcb[8], 7'b1100011}; // c.bnez
        5'b10_000: instr = {7'b0000000, shamt, rd, 3'b001, rd, 7'b0010011};
        5'b10_010: instr = {4'b0, offsp, 5'b00010, 3'b010, rd,
                             7'b0000011}; // c.lwsp
        5'b10_100:
          if (!c[12] && rs2 == 5'b0)
            instr = {12'b0, rd, 3'b000, 5'b00000, 7'b1100111}; // c.jr
          else if (!c[12])
            instr = {7'b0, rs2, 5'b00000, 3'b000, rd, 7'b0110011}; // c.mv
          else if (rs2 == 5'b0)
            instr = {12'b0, rd, 3'b000, 5'b00001, 7'b1100111}; // c.jalr
          else
            instr = {7'b0000000, rs2, rd, 3'b000, rd, 7'b0110011}; // c.add
        5'b10_110: instr = {4'b0, offssp[7:5], rs2, 5'b00010, 3'b010,
                             offssp[4:0], 7'b0100011}; // c.swsp
        default:   instr = instrraw;
      endcase
    end
  end
endmodule
