.include "xqdot4zi.inc"
.option norelax
.option norvc
.text
.global _start
_start:
addi x5,x0,3
kernel_begin:
addi x5,x5,-1
kernel_end:
sw x5,0(x0)
loop_end:
bne x5,x0,kernel_begin
ebreak
