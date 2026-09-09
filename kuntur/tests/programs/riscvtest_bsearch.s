_start:
    addi x14, x0, 32      # base = 32

    addi x8, x0, 3
    sw   x8, 0(x14)
    addi x8, x0, 7
    sw   x8, 4(x14)
    addi x8, x0, 12
    sw   x8, 8(x14)
    addi x8, x0, 18
    sw   x8, 12(x14)
    addi x8, x0, 25
    sw   x8, 16(x14)

    addi x8, x0, 0        # lo = 0
    addi x9, x0, 4         # hi = 4
    addi x13, x0, 18       # target = 18
    addi x15, x0, 60        # log = 60

LOOP:
    blt   x9, x8, NOTFOUND  # si hi < lo, no encontrado
    addi  x10, x8, 0         # mid = lo
    c.add x10, x9             # mid += hi
    c.srli x10, 1              # mid >>= 1
    c.sw  x10, 0(x15)           # log[i] = mid
    c.addi x15, 4                # log += 4
    addi  x11, x10, 0           # addr = mid
    c.slli x11, 2               # addr <<= 2
    c.add x11, x14              # addr += base
    c.lw  x12, 0(x11)            # value = mem[addr]
    beq   x12, x13, FOUND
    blt   x12, x13, GO_RIGHT
GO_LEFT:
    addi  x9, x10, 0            # hi = mid
    c.addi x9, -1                # hi -= 1
    c.j   LOOP
GO_RIGHT:
    addi  x8, x10, 0            # lo = mid
    c.addi x8, 1                  # lo += 1
    c.j   LOOP
FOUND:
    sw    x10, 20(x14)        # mem[52] = indice encontrado
    c.j   END
NOTFOUND:
    addi  x10, x0, -1
    sw    x10, 20(x14)
END:
