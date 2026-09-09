    .section .text
    .globl _start
_start:
    .option norvc
    addi x10, x0, 0
    jal  x5, L0
L0:
    addi x5, x5, 18
    .option rvc
    jalr x5
    .option norvc
    addi x10, x10, 1
    sw   x10, 0(x0)
STOP:
    jal  x0, STOP
TARGET:
    addi x10, x0, 8
    .option rvc
    jr   x1
