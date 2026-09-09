# Local custom-1 encoding, not native compiler/assembler extension support.
.macro xqdot4 rd, rs1, rs2, h
    .if (\h < 0) || (\h > 1)
        .error "xqdot4: h must be 0 or 1"
    .endif
    .insn r 0x2b, 0, (\h << 2), \rd, \rs1, \rs2
.endm
