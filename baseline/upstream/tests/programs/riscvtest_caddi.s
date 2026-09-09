    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 5
    .option rvc
    addi x8, x8, 3
    .option norvc
    sw   x8, 0(x0)
