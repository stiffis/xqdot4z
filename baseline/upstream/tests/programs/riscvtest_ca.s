    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 12
    addi x9, x0, 10
    .option rvc
    sub  x8, x8, x9
    .option norvc
    addi x10, x0, 12
    .option rvc
    xor  x10, x10, x9
    .option norvc
    addi x11, x0, 12
    .option rvc
    or   x11, x11, x9
    .option norvc
    addi x12, x0, 12
    .option rvc
    and  x12, x12, x9
    .option norvc
    sw   x8, 0(x0)
    sw   x10, 4(x0)
    sw   x11, 8(x0)
    sw   x12, 12(x0)
