"""Paired kernels for the comparison campaign, under common policy v2.

A body is eight logical elements: one packed weight word, two activation words,
two packed operations and two accumulations. Bodies are unrolled within a row
and the activation window is two words, so nothing here depends on K fitting the
register file -- the reason policy v1 was withdrawn.

Row traversal is derived, not chosen. A variant loops over rows unless its
encoding cannot express the row body with one copy of code. Only D under a
varying zero point fails that test, because its zero point is an instruction
immediate. The straight-line form is the loop body replicated without its back
edge, so the two forms differ by exactly the loop control and can be subtracted.

A statically valid specialization is taken if and only if it needs no dispatch.
Under a constant zero point every variant may take all of them; under a varying
one the baselines decline them, which is why B3 emits a single row body.

This module emits text. It does not assemble, run or measure.
"""
from tensors import pack_activations, pack_weights, words_per_row

# Declared register reservation, identical for every variant.
ACT_LOW, ACT_HIGH = 1, 2   # the two-word activation window of one body
ACCUMULATOR = 3
WEIGHT = 4
WEIGHT_POINTER = 5
OUTPUT_POINTER = 6
SENTINEL = 7               # end of the weight region, the loop's stop condition
SUM_A = 8                  # Sa, computed once per group (B3)
CORRECTION = 9             # z*Sa, hoisted or per row (B3)
DOT_LOW, DOT_HIGH = 10, 11
ZERO_POINTER = 12          # walks the zero-point array when z varies (B3)


def li(reg, value):
    value &= 0xffffffff
    low = value & 4095
    if low >= 2048: low -= 4096
    return f"lui x{reg},0x{((value - low) >> 12) & 0xfffff:x}\naddi x{reg},x{reg},{low}\n"


def setup(activations, weights, zeros, layout):
    """Place the tensors in data memory. This precedes the measured window."""
    body = ""
    for index, word in enumerate(pack_activations(activations)):
        body += li(WEIGHT, word) + f"sw x{WEIGHT},{layout['activations'] + 4*index}(x0)\n"
    per_row = layout["weight_words_per_row"]
    for row, values in enumerate(weights):
        for index, word in enumerate(pack_weights(values)):
            address = layout["weights"] + 4 * (row * per_row + index)
            body += li(WEIGHT, word) + f"sw x{WEIGHT},{address}(x0)\n"
    for row, z in enumerate(zeros):
        body += li(WEIGHT, z[0]) + f"sw x{WEIGHT},{layout['zero_points'] + 4*row}(x0)\n"
    return body


def _bodies(layout, operation):
    """The unrolled bodies of one row, addressed through the weight pointer."""
    text = ""
    for index in range(layout["weight_words_per_row"]):
        activation = layout["activations"] + 8 * index
        text += f"lw x{ACT_LOW},{activation}(x0)\n"
        text += f"lw x{ACT_HIGH},{activation + 4}(x0)\n"
        text += f"lw x{WEIGHT},{4*index}(x{WEIGHT_POINTER})\n"
        text += operation(DOT_LOW, WEIGHT, ACT_LOW, 0)
        text += operation(DOT_HIGH, WEIGHT, ACT_HIGH, 1)
        text += f"add x{ACCUMULATOR},x{ACCUMULATOR},x{DOT_LOW}\n"
        text += f"add x{ACCUMULATOR},x{ACCUMULATOR},x{DOT_HIGH}\n"
    return text


def _advance(layout, looped, label):
    """Pointer maintenance is common; only the back edge distinguishes forms."""
    stride = 4 * layout["weight_words_per_row"]
    text = f"addi x{WEIGHT_POINTER},x{WEIGHT_POINTER},{stride}\n"
    text += f"addi x{OUTPUT_POINTER},x{OUTPUT_POINTER},4\n"
    if looped:
        text += f"bne x{WEIGHT_POINTER},x{SENTINEL},{label}\n"
    return text


def _preamble(rows, layout, looped):
    text = li(WEIGHT_POINTER, layout["weights"]) + li(OUTPUT_POINTER, layout["outputs"])
    if looped:
        text += li(SENTINEL, layout["weights"] + 4 * rows * layout["weight_words_per_row"])
    return text


def strength_reduction(z):
    """What a variant may fold when one static zero point governs the program."""
    if z == 0: return "elide"
    if z == 1: return "no_multiply"
    if z & (z - 1) == 0: return "shift"
    return "multiply"


def kernel_d(rows, k, zeros, layout, row_form="derived"):
    """D fuses the correction, so a row body is the products and one store.

    row_form "inline" is the structural twin of "loop": the same row body
    replicated without the back edge and the sentinel, so their difference is
    the loop control and nothing else.
    """
    if layout["weight_words_per_row"] != words_per_row(k): raise ValueError("layout/K mismatch")
    column = [row[0] for row in zeros]
    shared = len(set(column)) == 1
    looped = shared if row_form == "derived" else row_form == "loop"
    if looped and not shared:
        raise ValueError("D cannot loop over rows while its immediate zero point varies")
    text = "kernel_begin:\n" + _preamble(rows, layout, looped)

    def row_body(z, last, label=None):
        operation = lambda rd, a, b, h: f"xqdot4zi x{rd},x{a},x{b},{z},{h}\n"
        body = f"add x{ACCUMULATOR},x0,x0\n" + _bodies(layout, operation)
        body += ("kernel_end:\n" if last else "") + f"sw x{ACCUMULATOR},0(x{OUTPUT_POINTER})\n"
        return body + _advance(layout, label is not None, label)

    if looped:
        text += "d_rows:\n" + row_body(column[0], True, "d_rows")
    else:
        # The immediate cannot vary inside a loop, so one copy per row.
        for row, z in enumerate(column):
            text += row_body(z, row == rows - 1)
    return text + "kernel_text_end:\n"


def kernel_b3(rows, k, zeros, layout, row_form="derived"):
    """B3 computes the products without correction, then P - z*Sa.

    Its encoding can always express the row body once, so the derived form is
    the loop. The inline form is its structural twin, kept as the diagnostic
    that prices the loop control; it takes no extra specialization, because the
    point is to isolate the control and not to change the arithmetic.
    """
    if layout["weight_words_per_row"] != words_per_row(k): raise ValueError("layout/K mismatch")
    column = [row[0] for row in zeros]
    shared = len(set(column)) == 1
    fold = strength_reduction(column[0]) if shared else "multiply"
    looped = row_form != "inline"
    text = "kernel_begin:\n" + _preamble(rows, layout, looped)
    if fold != "elide":
        # Sa with unit weights: one packed dot sums a word's four activations,
        # so the group's sum costs one pass and every row reuses it.
        text += li(WEIGHT, 0x11111111) + f"add x{SUM_A},x0,x0\n"
        for index in range(layout["activation_words"]):
            text += f"lw x{ACT_LOW},{layout['activations'] + 4*index}(x0)\n"
            text += f"xqdot4 x{DOT_LOW},x{WEIGHT},x{ACT_LOW},0\n"
            text += f"add x{SUM_A},x{SUM_A},x{DOT_LOW}\n"
    if shared and fold == "no_multiply":
        text += f"add x{CORRECTION},x0,x{SUM_A}\n"
    elif shared and fold == "shift":
        text += f"slli x{CORRECTION},x{SUM_A},{column[0].bit_length() - 1}\n"
    elif shared and fold == "multiply":
        text += f"addi x{CORRECTION},x0,{column[0]}\n"
        text += f"mul x{CORRECTION},x{CORRECTION},x{SUM_A}\n"
    elif not shared:
        # Per-row folding would need dispatch, which the rule declines, so the
        # zero point is read from the array every row and multiplied in full.
        text += li(ZERO_POINTER, layout["zero_points"])
    operation = lambda rd, a, b, h: f"xqdot4 x{rd},x{a},x{b},{h}\n"

    def row_body(last, label=None):
        body = f"add x{ACCUMULATOR},x0,x0\n" + _bodies(layout, operation)
        if not shared:
            body += f"lw x{CORRECTION},0(x{ZERO_POINTER})\n"
            body += f"mul x{CORRECTION},x{CORRECTION},x{SUM_A}\n"
            body += f"addi x{ZERO_POINTER},x{ZERO_POINTER},4\n"
        if fold != "elide":
            body += f"sub x{ACCUMULATOR},x{ACCUMULATOR},x{CORRECTION}\n"
        body += ("kernel_end:\n" if last else "") + f"sw x{ACCUMULATOR},0(x{OUTPUT_POINTER})\n"
        return body + _advance(layout, label is not None, label)

    if looped:
        text += "b3_rows:\n" + row_body(True, "b3_rows")
    else:
        for row in range(rows):
            text += row_body(row == rows - 1)
    return text + "kernel_text_end:\n"


VARIANTS = {"D": dict(builder=kernel_d, enables=(1, 0, 0), include="xqdot4zi.inc"),
            "B3": dict(builder=kernel_b3, enables=(0, 1, 1), include="xqdot4.inc"),
            "B2": dict(builder=None, enables=(0, 1, 0), include=None),
            "B1": dict(builder=None, enables=(0, 0, 0), include=None)}


def _install_scalar_variants():
    """B2 is defined after VARIANTS so both live beside the packed builders."""
    VARIANTS["B2"]["builder"] = kernel_b2
    VARIANTS["B1"]["builder"] = kernel_b1


def required_row_bodies(variant, zeros):
    """The floor each ISA imposes: only D cannot express a varying z once."""
    column = {row[0] for row in zeros}
    return len(column) if variant == "D" else 1


# Scalar variants reuse the reservation: the packed result registers become the
# extracted operands, and Sa's register holds a runtime zero point when z varies.
NIBBLE, BYTE, PRODUCT, ZERO_POINT = DOT_LOW, DOT_HIGH, CORRECTION, SUM_A


def _scalar_elements(layout, multiply, z, shared):
    """Expand a body's eight elements: extract, centre, multiply, accumulate."""
    text = ""
    for index in range(layout["weight_words_per_row"]):
        activation = layout["activations"] + 8 * index
        text += f"lw x{ACT_LOW},{activation}(x0)\n"
        text += f"lw x{ACT_HIGH},{activation + 4}(x0)\n"
        text += f"lw x{WEIGHT},{4*index}(x{WEIGHT_POINTER})\n"
        for element in range(8):
            word = ACT_LOW if element < 4 else ACT_HIGH
            if element:
                text += f"srli x{NIBBLE},x{WEIGHT},{4*element}\n"
                text += f"andi x{NIBBLE},x{NIBBLE},15\n"
            else:
                text += f"andi x{NIBBLE},x{WEIGHT},15\n"
            # Centring is the zero point's only appearance in a scalar variant:
            # an immediate when one static z governs, a register when it varies.
            if not shared:
                text += f"sub x{NIBBLE},x{NIBBLE},x{ZERO_POINT}\n"
            elif z:
                text += f"addi x{NIBBLE},x{NIBBLE},{-z}\n"
            shift = 24 - 8 * (element % 4)
            text += f"slli x{BYTE},x{word},{shift}\n"
            text += f"srai x{BYTE},x{BYTE},24\n"
            text += multiply(PRODUCT, NIBBLE, BYTE)
            text += f"add x{ACCUMULATOR},x{ACCUMULATOR},x{PRODUCT}\n"
    return text


def _scalar_kernel(rows, k, zeros, layout, row_form, multiply, label):
    """B1 and B2 share everything but the multiply, which is their difference."""
    if layout["weight_words_per_row"] != words_per_row(k): raise ValueError("layout/K mismatch")
    column = [row[0] for row in zeros]
    shared = len(set(column)) == 1
    looped = row_form != "inline"
    text = "kernel_begin:\n" + _preamble(rows, layout, looped)
    if not shared:
        text += li(ZERO_POINTER, layout["zero_points"])

    def row_body(last, back=None):
        body = f"add x{ACCUMULATOR},x0,x0\n"
        if not shared:
            body += f"lw x{ZERO_POINT},0(x{ZERO_POINTER})\n"
            body += f"addi x{ZERO_POINTER},x{ZERO_POINTER},4\n"
        body += _scalar_elements(layout, multiply, column[0], shared)
        body += ("kernel_end:\n" if last else "") + f"sw x{ACCUMULATOR},0(x{OUTPUT_POINTER})\n"
        return body + _advance(layout, back is not None, back)

    if looped:
        text += f"{label}:\n" + row_body(True, label)
    else:
        for row in range(rows):
            text += row_body(row == rows - 1)
    return text + "kernel_text_end:\n"


def kernel_b2(rows, k, zeros, layout, row_form="derived"):
    """B2 has the scalar multiplier, so one instruction closes each element."""
    return _scalar_kernel(rows, k, zeros, layout, row_form,
                          lambda rd, a, b: f"mul x{rd},x{a},x{b}\n", "b2_rows")



MASK, TERM = 13, 14  # B1 needs two scratch registers the packed variants do not


def _b1_multiply(bits, signed):
    """The frozen bounded_masked_bit_decomposition_v1, expanded straight-line.

    Each bit contributes a shifted activation selected by an all-ones or
    all-zero mask, so no bit is a branch and the trajectory never depends on an
    operand. The top bit of a signed width is subtracted instead of added.
    """
    def emit(rd, weight, byte):
        text = f"andi x{weight},x{weight},{(1 << bits) - 1}\n"
        text += f"add x{rd},x0,x0\n"
        for bit in range(bits):
            text += (f"srli x{MASK},x{weight},{bit}\n" if bit else f"add x{MASK},x0,x{weight}\n")
            text += f"andi x{MASK},x{MASK},1\n"
            text += f"sub x{MASK},x0,x{MASK}\n"
            text += f"slli x{TERM},x{byte},{bit}\n"
            text += f"and x{TERM},x{TERM},x{MASK}\n"
            text += f"{'sub' if signed and bit == bits - 1 else 'add'} x{rd},x{rd},x{TERM}\n"
        return text
    return emit


def b1_operand_format(zeros):
    """Width folding is a property of the program, not of a row.

    With one static zero point the declared bounds apply; when z varies a looped
    kernel cannot fold per row without dispatch, so the general signed width
    governs every element, which the frozen policy's 'S5 otherwise' covers.
    """
    column = {row[0] for row in zeros}
    if len(column) != 1: return 5, True
    z = next(iter(column))
    if z == 0: return 4, False
    return (4 if z == 8 else 5), True


def kernel_b1(rows, k, zeros, layout, row_form="derived"):
    """B1 has no multiplier, so each element expands into masked bit terms."""
    bits, signed = b1_operand_format(zeros)
    return _scalar_kernel(rows, k, zeros, layout, row_form,
                          _b1_multiply(bits, signed), "b1_rows")


_install_scalar_variants()
