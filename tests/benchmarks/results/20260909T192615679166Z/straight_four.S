.include "xqdot4zi.inc"
.option norelax
.option norvc
.text
.global _start
_start:
kernel_begin:
addi x1,x0,5
addi x2,x0,7
add x3,x1,x2
kernel_end:
sw x3,0(x0)
ebreak
