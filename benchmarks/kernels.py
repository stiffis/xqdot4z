"""Paired kernels for the comparison campaign.

Every variant uses the same skeleton required by the frozen common policy: the
group's activation words stay resident in registers across rows, an unrolled
iteration covers eight logical elements -- one packed weight word and two
activation words -- and no variant gets a hand-tuned schedule the others lack.

Under static specialization the zero point is an instruction immediate, so rows
are emitted straight-line rather than looped: a loop cannot carry a per-row
immediate. Code size therefore grows with N, and code bytes is a reported
metric rather than a hidden cost.

This module emits text. It does not assemble, run or measure.
"""
from tensors import pack_activations, pack_weights, words_per_row

# Declared register reservation, identical for every variant.
ACTIVATION_REGS = tuple(range(1, 9))   # x1..x8 hold the group's activation words
ACCUMULATOR = 9                        # x9 accumulates one row
WEIGHT = 10                            # x10 holds the packed weight word
SUM_A = 11                             # x11 holds Sa (B3 only)
CORRECTION = 12                        # x12 holds a hoisted z*Sa (B3 only)
DOT_LOW, DOT_HIGH = 13, 14             # x13/x14 receive the two packed results
SCRATCH = 15                           # x15 builds a per-row correction


def li(reg, value):
    value &= 0xffffffff
    low = value & 4095
    if low >= 2048: low -= 4096
    return f"lui x{reg},0x{((value - low) >> 12) & 0xfffff:x}\naddi x{reg},x{reg},{low}\n"


def setup(activations, weights, layout):
    """Place the tensors in data memory. This precedes the measured window."""
    body = ""
    for index, word in enumerate(pack_activations(activations)):
        body += li(WEIGHT, word) + f"sw x{WEIGHT},{layout['activations'] + 4*index}(x0)\n"
    per_row = layout["weight_words_per_row"]
    for row, values in enumerate(weights):
        for index, word in enumerate(pack_weights(values)):
            address = layout["weights"] + 4 * (row * per_row + index)
            body += li(WEIGHT, word) + f"sw x{WEIGHT},{address}(x0)\n"
    return body


def _load_activations(layout):
    """Residency across rows is the condition RQ2 and H2 depend on."""
    return "".join(f"lw x{ACTIVATION_REGS[j]},{layout['activations'] + 4*j}(x0)\n"
                   for j in range(layout["activation_words"]))


def _row_products(row, layout, operation):
    """Four unrolled iterations of eight elements for K=32."""
    body = f"add x{ACCUMULATOR},x0,x0\n"
    per_row = layout["weight_words_per_row"]
    for index in range(per_row):
        address = layout["weights"] + 4 * (row * per_row + index)
        body += f"lw x{WEIGHT},{address}(x0)\n"
        low, high = ACTIVATION_REGS[2 * index], ACTIVATION_REGS[2 * index + 1]
        body += operation(DOT_LOW, WEIGHT, low, 0)
        body += operation(DOT_HIGH, WEIGHT, high, 1)
        body += f"add x{ACCUMULATOR},x{ACCUMULATOR},x{DOT_LOW}\n"
        body += f"add x{ACCUMULATOR},x{ACCUMULATOR},x{DOT_HIGH}\n"
    return body


def kernel_d(rows, k, zeros, layout):
    """D: the correction is fused into the operation, so no epilogue per row."""
    if layout["weight_words_per_row"] != words_per_row(k): raise ValueError("layout/K mismatch")
    body = "kernel_begin:\n" + _load_activations(layout)
    for row in range(rows):
        z = zeros[row][0]
        body += _row_products(row, layout,
                              lambda rd, a, b, h: f"xqdot4zi x{rd},x{a},x{b},{z},{h}\n")
        label = "kernel_end:\n" if row == rows - 1 else ""
        body += label + f"sw x{ACCUMULATOR},{layout['outputs'] + 4*row}(x0)\n"
    return body


def kernel_b3(rows, k, zeros, layout):
    """B3: the same products without correction, then P - z*Sa.

    Sa is computed once for the group and reused across rows. The declared
    schedule decides whether z*Sa can be hoisted too: it can when z repeats,
    which is the ZC case, and cannot when every row has its own z.
    """
    if layout["weight_words_per_row"] != words_per_row(k): raise ValueError("layout/K mismatch")
    column = [row[0] for row in zeros]
    shared = len(set(column)) == 1
    body = "kernel_begin:\n" + _load_activations(layout)
    # Sa with unit weights: one packed dot per activation word sums its four
    # activations, so the group's sum costs one pass and is reused by every row.
    body += li(WEIGHT, 0x11111111) + f"add x{SUM_A},x0,x0\n"
    for j in range(layout["activation_words"]):
        body += f"xqdot4 x{DOT_LOW},x{WEIGHT},x{ACTIVATION_REGS[j]},0\n"
        body += f"add x{SUM_A},x{SUM_A},x{DOT_LOW}\n"
    if shared:
        body += f"addi x{SCRATCH},x0,{column[0]}\n"
        body += f"mul x{CORRECTION},x{SCRATCH},x{SUM_A}\n"
    for row in range(rows):
        body += _row_products(row, layout,
                              lambda rd, a, b, h: f"xqdot4 x{rd},x{a},x{b},{h}\n")
        if shared:
            body += f"sub x{ACCUMULATOR},x{ACCUMULATOR},x{CORRECTION}\n"
        else:
            body += f"addi x{SCRATCH},x0,{column[row]}\n"
            body += f"mul x{SCRATCH},x{SCRATCH},x{SUM_A}\n"
            body += f"sub x{ACCUMULATOR},x{ACCUMULATOR},x{SCRATCH}\n"
        label = "kernel_end:\n" if row == rows - 1 else ""
        body += label + f"sw x{ACCUMULATOR},{layout['outputs'] + 4*row}(x0)\n"
    return body


VARIANTS = {"D": dict(builder=kernel_d, enables=(1, 0, 0), include="xqdot4zi.inc"),
            "B3": dict(builder=kernel_b3, enables=(0, 1, 1), include="xqdot4.inc")}
