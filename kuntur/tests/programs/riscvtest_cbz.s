    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 0
    addi x9, x0, 5
    addi x10, x0, 0
    .option rvc
    beqz x8, L1
    .option norvc
    addi x10, x0, 99
L1:
    .option rvc
    bnez x9, L2
    .option norvc
    addi x10, x0, 99
L2:
    .option norvc
    addi x10, x10, 7
    sw   x10, 0(x0)
