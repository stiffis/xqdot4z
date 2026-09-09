    .section .text
    .globl _start
_start:
    .option norvc
    addi x2, x0, 96
    addi x6, x0, 55
    .option rvc
    sw   x6, 20(x2)
    lw   x5, 20(x2)
    .option norvc
    sw   x5, 4(x0)
