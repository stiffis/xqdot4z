.include "xqdot4zi.inc"
.option norelax
.option norvc
.text
.global _start
_start:
kernel_begin:
lui x1,0x78f05
addi x1,x1,-1387
lui x2,0x2ff8
addi x2,x2,-128
xqdot4zi x3,x1,x2,8,0
xqdot4zi x4,x1,x2,15,1
add x5,x3,x4
kernel_end:
sw x5,0(x0)
ebreak
