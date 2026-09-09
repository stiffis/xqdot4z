# GNU assembler macro, not an upstream RISC-V mnemonic or standard extension.
.macro xqdot4zi rd, rs1, rs2, z, h
  .if (\z < 0) || (\z > 15)
    .error "xqdot4zi: zero-point must be an immediate in [0,15]"
  .endif
  .if (\h < 0) || (\h > 1)
    .error "xqdot4zi: half must be an immediate in [0,1]"
  .endif
  .insn r 0x0b, 0, ((\z << 3) | (\h << 2)), \rd, \rs1, \rs2
.endm
