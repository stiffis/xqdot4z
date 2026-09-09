    .section .text
    .globl _start
_start:
    .option norvc
    addi x8, x0, 5        # contador n = 5
    addi x9, x0, 0        # acumulador = 0
    .option rvc
LOOP:
    add  x9, x9, x8       # c.add: acc += n
    addi x8, x8, -1       # c.addi: n--
    bnez x8, LOOP         # c.bnez: repetir si n != 0
    .option norvc
    sw   x9, 0(x0)        # Mem[0] = 15
