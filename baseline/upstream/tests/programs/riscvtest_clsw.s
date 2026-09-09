    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 96
    addi x9, x0, 77
    .option rvc
    sw   x9, 0(x8)
    lw   x10, 0(x8)
    .option norvc
    sw   x10, 4(x8)
