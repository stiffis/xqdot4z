// Explicit whitelist for the teaching core, not a claim of full RV32I/M.
// Examine all funct7 bits: MUL must not alias ADD, and LB must not alias LW.
module instruction_policy #(parameter ENABLE_XQDOT4Z = 0)(input [31:0] instr,
                          output reg supported,
                          output reg breakpoint,
                          output reg uses_rs1, uses_rs2);
  wire [6:0] op = instr[6:0];
  wire [2:0] f3 = instr[14:12];
  wire [6:0] f7 = instr[31:25];
  always @* begin
    supported = 0;
    breakpoint = 0;
    uses_rs1 = 0;
    uses_rs2 = 0;
    case (op)
      7'b0001011: begin // custom-0: xqdot4zi, ISA prototype v0.1
        supported = (ENABLE_XQDOT4Z != 0) && (f3 == 0) && (instr[26:25] == 0);
        uses_rs1 = supported; uses_rs2 = supported;
      end
      7'b0000011: begin supported = (f3 == 3'b010); uses_rs1 = supported; end // LW
      7'b0100011: begin // SW
        supported = (f3 == 3'b010); uses_rs1 = supported; uses_rs2 = supported;
      end
      7'b0110011: begin
        case (f3)
          3'b000, 3'b101: supported = (f7 == 7'b0000000 || f7 == 7'b0100000);
          3'b001, 3'b010, 3'b100, 3'b110, 3'b111: supported = (f7 == 0);
          default: supported = 0;
        endcase
        uses_rs1 = supported; uses_rs2 = supported;
      end
      7'b0010011: begin
        case (f3)
          3'b000, 3'b010, 3'b100, 3'b110, 3'b111: supported = 1;
          3'b001: supported = (f7 == 0);
          3'b101: supported = (f7 == 0 || f7 == 7'b0100000);
          default: supported = 0;
        endcase
        uses_rs1 = supported;
      end
      7'b1100011: begin
        supported = (f3 == 3'b000 || f3 == 3'b001 || f3 == 3'b100 || f3 == 3'b101);
        uses_rs1 = supported; uses_rs2 = supported;
      end
      7'b0110111, 7'b1101111: supported = 1; // LUI, JAL: no source register
      7'b1100111: begin supported = (f3 == 0); uses_rs1 = supported; end
      7'b1110011: breakpoint = (instr == 32'h00100073);
      default: supported = 0;
    endcase
  end
endmodule
