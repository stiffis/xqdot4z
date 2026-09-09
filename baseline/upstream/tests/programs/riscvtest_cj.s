    .section .text
    .globl _start
_start:
    .option norvc
    addi x10, x0, 0
    .option rvc
    jal  ADD5
    j    END
    .option norvc
ADD5:
    addi x10, x10, 5
    jalr x0, x1, 0
END:
    sw   x10, 0(x0)
