"""Deterministic tensors and the common data layout for the campaign.

Every variant reads the same bytes at the same addresses. The layout does not
depend on N, so a shape change never moves an address and the variants stay
comparable. This module materializes inputs and the integer oracle; it does not
generate kernels, assemble, or measure anything.
"""
import random
import struct

MAX_ROWS = 16
ACTIVATION_BASE = 0
WEIGHT_BASE = 32          # eight activation words occupy bytes 0..31
ZERO_POINT_BASE = 288     # four weight words per row for MAX_ROWS rows
OUTPUT_BASE = 352         # one zero point per row
DMEM_WORDS = 1024


def words_per_row(k):
    """Eight U4 codes per packed word."""
    if k % 8: raise ValueError("K must pack whole weight words")
    return k // 8


def zero_points(profile, setting, rows, groups):
    """The manifest's declared schedule; kept identical to check_campaign."""
    if profile == "zc_controls":
        return [[setting] * groups for _ in range(rows)]
    if profile != "zs_balanced_u4":
        raise ValueError("unknown zero-point profile")
    return [[(setting + r + 5 * g) % 16 for g in range(groups)] for r in range(rows)]


def tensors(seed, rows, k):
    """Inputs depend on the seed and shape only, never on the variant."""
    if type(seed) is not int or type(rows) is not int or type(k) is not int:
        raise ValueError("seed, rows and K must be integers")
    if not 1 <= rows <= MAX_ROWS: raise ValueError("rows out of range")
    rng = random.Random(seed)
    activations = [rng.randrange(-128, 128) for _ in range(k)]
    weights = [[rng.randrange(16) for _ in range(k)] for _ in range(rows)]
    return activations, weights


def pack_activations(activations):
    return [int.from_bytes(struct.pack("4b", *activations[i:i + 4]), "little")
            for i in range(0, len(activations), 4)]


def pack_weights(row):
    return [sum(w << (4 * j) for j, w in enumerate(row[i:i + 8]))
            for i in range(0, len(row), 8)]


def expected_outputs(weights, activations, zeros):
    """The contract's subtotal, computed on unbounded integers."""
    return [sum((w - z) * a for w, a in zip(row, activations))
            for row, z in zip(weights, (z[0] for z in zeros))]


def activation_sum(activations):
    return sum(activations)


def layout(rows, k):
    """Byte addresses every variant must use.

    The zero-point array is materialized for every variant even though D reads
    its zero point from an instruction immediate: the campaign holds the data
    layout fixed, so it cannot depend on which variant is running.
    """
    per_row = words_per_row(k)
    if WEIGHT_BASE + rows * per_row * 4 > ZERO_POINT_BASE:
        raise ValueError("weights would overlap the zero-point region")
    if ZERO_POINT_BASE + rows * 4 > OUTPUT_BASE:
        raise ValueError("zero points would overlap the output region")
    return dict(activations=ACTIVATION_BASE,
                weights=WEIGHT_BASE,
                zero_points=ZERO_POINT_BASE,
                outputs=OUTPUT_BASE,
                weight_words_per_row=per_row,
                activation_words=k // 4)
