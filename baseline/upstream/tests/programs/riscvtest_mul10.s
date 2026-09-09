    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 6
    addi x9, x0, 6
    .option rvc
    slli x8, x8, 3
    slli x9, x9, 1
    add  x8, x8, x9
    .option norvc
    sw   x8, 0(x0)
