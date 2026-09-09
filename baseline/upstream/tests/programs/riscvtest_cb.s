    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 40
    .option rvc
    srli x8, x8, 2
    .option norvc
    addi x9, x0, -8
    .option rvc
    srai x9, x9, 1
    .option norvc
    addi x10, x0, 13
    .option rvc
    andi x10, x10, 6
    .option norvc
    sw   x8, 0(x0)
    sw   x9, 4(x0)
    sw   x10, 8(x0)
