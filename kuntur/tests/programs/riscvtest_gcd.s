_start:
    addi x8, x0, 48       # a = 48
    addi x9, x0, 18       # b = 18
LOOP:
    beq  x8, x9, DONE     # si a == b, terminar
    blt  x8, x9, BLESS    # si a < b, restar a de b
    c.sub x8, x9          # a -= b
    c.j   LOOP
BLESS:
    c.sub x9, x8          # b -= a
    c.j   LOOP
DONE:
    sw   x8, 0(x0)        # Mem[0] = gcd(48,18) = 6
