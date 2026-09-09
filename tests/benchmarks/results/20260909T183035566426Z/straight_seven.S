.include "xqdot4zi.inc"
.option norelax
.option norvc
.text
.global _start
_start:
kernel_begin:
addi x1,x0,1
addi x2,x0,2
addi x3,x0,3
add x4,x1,x2
add x5,x4,x3
add x6,x5,x5
kernel_end:
sw x6,0(x0)
ebreak
