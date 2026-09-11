.include "xqdot4zi.inc"
.option norelax
.option norvc
.text
.global _start
_start:
kernel_begin:
addi x1,x0,1
beq x1,x0,tgt
addi x3,x0,3
tgt:
kernel_end:
sw x3,0(x0)
ebreak
