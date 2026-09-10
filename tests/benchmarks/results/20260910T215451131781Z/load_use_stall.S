.include "xqdot4zi.inc"
.option norelax
.option norvc
.text
.global _start
_start:
kernel_begin:
sw x0,0(x0)
lw x1,0(x0)
addi x2,x1,1
kernel_end:
sw x2,4(x0)
ebreak
