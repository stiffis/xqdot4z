module decompressor(input  [31:0] instrraw,
                    output reg [31:0] instr,
                    output        compressed,
                    output reg    illegal);

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
  wire [9:0] imm4spn = {c[10:7], c[12:11], c[5], c[6], 2'b00};
  wire [9:0] imm16sp = {c[12], c[4:3], c[5], c[2], c[6], 4'b0000};
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
    illegal = 1'b0;
    if (compressed) begin
      case ({op, funct3})
        5'b00_000: begin // c.addi4spn (zero immediate is reserved)
          instr = {2'b00, imm4spn, 5'd2, 3'b000, rs2p, 7'b0010011};
          illegal = (imm4spn == 0);
        end
        5'b00_010: instr = {5'b0, offlw, rs1p, 3'b010, rs2p, 7'b0000011};
        5'b00_110: instr = {5'b0, offlw[6:5], rs2p, rs1p, 3'b010,
                             offlw[4:2], 2'b00, 7'b0100011};
        5'b01_000: instr = {immci, rd, 3'b000, rd, 7'b0010011};
        5'b01_001: instr = {offcj[11], offcj[10:1], offcj[11],
                             {8{offcj[11]}}, 5'b00001, 7'b1101111}; // c.jal
        5'b01_010: instr = {immci, 5'd0, 3'b000, rd, 7'b0010011}; // c.li
        5'b01_011: begin
          if (rd == 5'd2) begin // c.addi16sp, not c.lui
            instr = {{2{imm16sp[9]}}, imm16sp, 5'd2, 3'b000, 5'd2, 7'b0010011};
            illegal = (imm16sp == 0);
          end else begin
            instr = {immlui, rd, 7'b0110111};
            illegal = (immlui == 0);
          end
        end
        5'b01_100:
          case (c[11:10])
            2'b00: begin
              instr = {7'b0000000, shamt, rdp, 3'b101, rdp, 7'b0010011};
              illegal = c[12]; // RV32 does not implement shamt[5] custom space
            end
            2'b01: begin
              instr = {7'b0100000, shamt, rdp, 3'b101, rdp, 7'b0010011};
              illegal = c[12];
            end
            2'b10: instr = {immci, rdp, 3'b111, rdp, 7'b0010011};
            2'b11: begin
              illegal = c[12]; // RV64 SUBW/ADDW and reserved encodings
              case (c[6:5])
                2'b00: instr = {7'b0100000, rs2p, rdp, 3'b000, rdp, 7'b0110011};
                2'b01: instr = {7'b0000000, rs2p, rdp, 3'b100, rdp, 7'b0110011};
                2'b10: instr = {7'b0000000, rs2p, rdp, 3'b110, rdp, 7'b0110011};
                2'b11: instr = {7'b0000000, rs2p, rdp, 3'b111, rdp, 7'b0110011};
              endcase
            end
          endcase
        5'b01_101: instr = {offcj[11], offcj[10:1], offcj[11],
                             {8{offcj[11]}}, 5'b00000, 7'b1101111}; // c.j
        5'b01_110: instr = {offcb[8], {3{offcb[8]}}, offcb[7:5],
                             5'b00000, rs1p, 3'b000, offcb[4:1],
                             offcb[8], 7'b1100011}; // c.beqz
        5'b01_111: instr = {offcb[8], {3{offcb[8]}}, offcb[7:5],
                             5'b00000, rs1p, 3'b001, offcb[4:1],
                             offcb[8], 7'b1100011}; // c.bnez
        5'b10_000: begin
          instr = {7'b0000000, shamt, rd, 3'b001, rd, 7'b0010011};
          illegal = c[12];
        end
        5'b10_010: begin
          instr = {4'b0, offsp, 5'b00010, 3'b010, rd, 7'b0000011}; // c.lwsp
          illegal = (rd == 0);
        end
        5'b10_100:
          if (!c[12] && rs2 == 5'b0) begin
            instr = {12'b0, rd, 3'b000, 5'b00000, 7'b1100111}; // c.jr
            illegal = (rd == 0);
          end
          else if (!c[12])
            instr = {7'b0, rs2, 5'b00000, 3'b000, rd, 7'b0110011}; // c.mv
          else if (rs2 == 5'b0)
            if (rd == 0)
              instr = 32'h00100073; // c.ebreak -> ebreak, NOT jalr x1,x0,0
            else
              instr = {12'b0, rd, 3'b000, 5'b00001, 7'b1100111}; // c.jalr
          else
            instr = {7'b0000000, rs2, rd, 3'b000, rd, 7'b0110011}; // c.add
        5'b10_110: instr = {4'b0, offssp[7:5], rs2, 5'b00010, 3'b010,
                             offssp[4:0], 7'b0100011}; // c.swsp
        default:   illegal = 1'b1; // unsupported FP/reserved quadrants
      endcase
      // Never pass an unexpanded 16-bit instruction into the base decoder.
      if (illegal) instr = 32'h00000013;
    end
  end
endmodule
