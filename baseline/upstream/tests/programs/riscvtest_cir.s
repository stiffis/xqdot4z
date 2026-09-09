    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 3
    .option rvc
    slli x8, x8, 2
    .option norvc
    addi x9, x0, 5
    .option rvc
    add  x8, x8, x9
    lui  x10, 1
    .option norvc
    sw   x8, 0(x0)
    sw   x10, 4(x0)
