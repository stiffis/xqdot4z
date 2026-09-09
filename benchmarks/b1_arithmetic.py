"""Host model of the selected B1 arithmetic policy, not a performance kernel.

The protocol is normative. Bit steps use RV32 wrapping arithmetic; Python's
control flow specializes static z and expands fixed bit positions. This does
not implement register allocation, assembly, retirement or cycle measurement.
"""

POLICY_ID = "bounded_masked_bit_decomposition_v1"
MASK32 = (1 << 32) - 1


def operand_format(z):
    """Select a width from declared U4 bounds and static z, never tensor values."""
    if type(z) is not int or not 0 <= z <= 15:
        raise ValueError("z must be a U4 integer")
    if z == 0:
        return 4, False
    return (4 if z == 8 else 5), True


def _selected_shift(x, activation32, bit):
    mask = (-((x >> bit) & 1)) & MASK32
    return ((activation32 << bit) & MASK32) & mask


def multiply_term(weight, z, activation):
    """Compute one (U4-U4)*S8 term using masked shifts, adds and subtraction."""
    bits, signed = operand_format(z)
    if type(weight) is not int or not 0 <= weight <= 15:
        raise ValueError("weight must be a U4 integer")
    if type(activation) is not int or not -128 <= activation <= 127:
        raise ValueError("activation must be an S8 integer")
    x = (weight - z) & ((1 << bits) - 1)
    activation32 = activation & MASK32
    accumulator = 0
    for bit in range(bits - int(signed)):
        accumulator = (accumulator + _selected_shift(x, activation32, bit)) & MASK32
    if signed:  # Static specialization, not a branch on a runtime tensor bit.
        accumulator = (accumulator - _selected_shift(x, activation32, bits - 1)) & MASK32
    # Interpret the final register as INT32; this is not a kernel instruction.
    return accumulator if accumulator < (1 << 31) else accumulator - (1 << 32)
