"""XQDot4Z numerical contract v0.1. See SPEC.md; this module does not model cycles.

Arithmetic uses unbounded Python integers. Only encode_s32 changes the signed
result into its two's-complement bit pattern; inputs are never silently masked.
"""

from collections.abc import Iterable

CONTRACT_VERSION = "0.1"
U32_MAX = (1 << 32) - 1
S32_MIN = -(1 << 31)
S32_MAX = (1 << 31) - 1
RESULT_MIN = -7680
RESULT_MAX = 7680


def _integer(value: int, name: str, low: int, high: int) -> int:
    # Reject bool explicitly: Python's bool is otherwise a subclass of int.
    if type(value) is not int:
        raise TypeError(f"{name} must be a Python int, not {type(value).__name__}")
    if not low <= value <= high:
        raise ValueError(f"{name} must be in [{low}, {high}], got {value}")
    return value


def _lanes(values: Iterable[int], name: str, count: int,
           low: int, high: int) -> tuple[int, ...]:
    lanes = tuple(values)
    if len(lanes) != count:
        raise ValueError(f"{name} must contain exactly {count} lanes")
    return tuple(_integer(value, f"{name}[{i}]", low, high)
                 for i, value in enumerate(lanes))


def pack_weights(values: Iterable[int]) -> int:
    """Pack exactly eight U4 codes; lane 0 occupies bits [3:0]."""
    lanes = _lanes(values, "weights", 8, 0, 15)
    return sum(value << (4 * i) for i, value in enumerate(lanes))


def unpack_weights(word: int) -> tuple[int, ...]:
    """Return all eight U4 codes, from least to most significant nibble."""
    _integer(word, "weights_word", 0, U32_MAX)
    return tuple((word >> (4 * i)) & 15 for i in range(8))


def pack_activations(values: Iterable[int]) -> int:
    """Pack exactly four S8 values as two's-complement bytes, lane 0 at [7:0]."""
    lanes = _lanes(values, "activations", 4, -128, 127)
    return sum((value & 255) << (8 * i) for i, value in enumerate(lanes))


def unpack_activations(word: int) -> tuple[int, ...]:
    """Decode four signed bytes; the input is an unsigned 32-bit bit pattern."""
    _integer(word, "activations_word", 0, U32_MAX)
    lanes = tuple((word >> (8 * i)) & 255 for i in range(4))
    return tuple(value if value < 128 else value - 256 for value in lanes)


def dot4(weights: Iterable[int], activations: Iterable[int], zero_point: int) -> int:
    """Exact four-term sum((w-z)*a), returned as a signed mathematical integer."""
    weights = _lanes(weights, "weights", 4, 0, 15)
    activations = _lanes(activations, "activations", 4, -128, 127)
    _integer(zero_point, "zero_point", 0, 15)
    return sum((w - zero_point) * a for w, a in zip(weights, activations))


def dot4_factored(weights: Iterable[int], activations: Iterable[int],
                  zero_point: int) -> int:
    """Same contract evaluated as P-z*Sa; does not call dot4."""
    weights = _lanes(weights, "weights", 4, 0, 15)
    activations = _lanes(activations, "activations", 4, -128, 127)
    _integer(zero_point, "zero_point", 0, 15)
    product_sum = sum(w * a for w, a in zip(weights, activations))
    activation_sum = sum(activations)
    return product_sum - zero_point * activation_sum


def qdot4z(weights_word: int, activations_word: int,
            zero_point: int, half: int = 0) -> int:
    """Evaluate packed operands. half selects W only, never a different A half."""
    _integer(half, "half", 0, 1)
    weights = unpack_weights(weights_word)
    activations = unpack_activations(activations_word)
    return dot4(weights[4 * half:4 * half + 4], activations, zero_point)


def encode_s32(value: int) -> int:
    """Encode a valid signed 32-bit integer as an unsigned 32-bit bit pattern."""
    _integer(value, "signed_result", S32_MIN, S32_MAX)
    return value if value >= 0 else value + (1 << 32)


def decode_s32(word: int) -> int:
    """Decode an unsigned 32-bit bit pattern as a signed 32-bit integer."""
    _integer(word, "result_word", 0, U32_MAX)
    return word if word < (1 << 31) else word - (1 << 32)


def qdot4z_bits(weights_word: int, activations_word: int,
                zero_point: int, half: int = 0) -> int:
    """Return the expected 32 output bits for a future RTL implementation."""
    return encode_s32(qdot4z(weights_word, activations_word, zero_point, half))
