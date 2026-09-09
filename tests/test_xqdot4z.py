"""Numerical-contract tests, not processor or RTL verification."""

import itertools
import json
import random
import struct
import unittest
from pathlib import Path

from model import xqdot4z as model

SEED = 20260908
RANDOM_CASES = 10_000
COMPLETED_COUNTS = {}
EXAMPLES = Path(__file__).parent / "data/qdot4z_examples.json"


def setUpModule():
    COMPLETED_COUNTS.clear()


class ContractTests(unittest.TestCase):
    def test_documented_examples(self):
        examples = json.loads(EXAMPLES.read_text())
        self.assertEqual(examples["contract_version"], model.CONTRACT_VERSION)
        for case in examples["cases"]:
            with self.subTest(case=case["name"]):
                args = (int(case["weights_word"], 16), int(case["activations_word"], 16),
                        case["zero_point"], case["half"])
                self.assertEqual(model.qdot4z(*args), case["expected_signed"])
                self.assertEqual(model.qdot4z_bits(*args), int(case["expected_u32"], 16))
        COMPLETED_COUNTS["documented_examples"] = len(examples["cases"])

    def test_weight_packing_all_codes_and_positions(self):
        self.assertEqual(model.pack_weights([7, 6, 5, 4, 3, 2, 1, 0]), 0x01234567)
        self.assertEqual(model.unpack_weights(0xFEDCBA98), tuple(range(8, 16)))
        count = 0
        for position in range(8):
            for value in range(16):
                lanes = [0] * 8
                lanes[position] = value
                expected = int("".join(format(w, "x") for w in reversed(lanes)), 16)
                self.assertEqual(model.pack_weights(lanes), expected)
                self.assertEqual(model.unpack_weights(expected), tuple(lanes))
                count += 1
        COMPLETED_COUNTS["weight_code_positions"] = count

    def test_activation_packing_all_values_and_positions(self):
        count = 0
        for position in range(4):
            for value in range(-128, 128):
                lanes = [0] * 4
                lanes[position] = value
                expected = int.from_bytes(struct.pack("4b", *lanes), "little")
                self.assertEqual(model.pack_activations(lanes), expected)
                self.assertEqual(model.unpack_activations(expected), tuple(lanes))
                count += 1
        COMPLETED_COUNTS["activation_value_positions"] = count

    def test_little_endian_example(self):
        self.assertEqual((0x78F04A95).to_bytes(4, "little"), bytes.fromhex("954af078"))
        self.assertEqual((0x02FF7F80).to_bytes(4, "little"), bytes.fromhex("807fff02"))
        self.assertEqual(model.unpack_activations(0x02FF7F80), (-128, 127, -1, 2))

    def test_exhaustive_single_term_in_every_physical_lane(self):
        """All 16*16*256 tuples embedded at each of eight W positions."""
        tuples = placements = 0
        minimum, maximum = 0, 0
        for weight in range(16):
            for zero_point in range(16):
                for activation in range(-128, 128):
                    expected = weight * activation - zero_point * activation
                    minimum = min(minimum, expected)
                    maximum = max(maximum, expected)
                    for position in range(8):
                        word = weight << (4 * position)
                        # struct supplies an independent S8 representation.
                        byte = struct.pack("b", activation)[0]
                        acts = byte << (8 * (position % 4))
                        actual = model.qdot4z(word, acts, zero_point, position // 4)
                        if actual != expected:
                            self.fail(f"term w={weight} z={zero_point} a={activation} "
                                      f"position={position}: {actual} != {expected}")
                        placements += 1
                    tuples += 1
        self.assertEqual((minimum, maximum), (-1920, 1920))
        self.assertEqual(tuples, 65_536)
        self.assertEqual(placements, 524_288)
        COMPLETED_COUNTS["single_term_tuples"] = tuples
        COMPLETED_COUNTS["single_term_lane_placements"] = placements

    def test_random_full_dot_products_and_factorization(self):
        rng = random.Random(SEED)
        operations = 0
        for _ in range(RANDOM_CASES):
            weights = [rng.randrange(16) for _ in range(8)]
            activations = [rng.randrange(-128, 128) for _ in range(4)]
            z = rng.randrange(16)
            # These encoders do not call the model's packing functions.
            word = int("".join(format(w, "x") for w in reversed(weights)), 16)
            acts = int.from_bytes(struct.pack("4b", *activations), "little")
            for half in (0, 1):
                selected = weights[4 * half:4 * half + 4]
                expected = sum(w * a for w, a in zip(selected, activations)) - z * sum(activations)
                result = model.qdot4z(word, acts, z, half)
                self.assertEqual(result, expected)
                self.assertEqual(model.dot4(selected, activations, z), expected)
                self.assertEqual(model.dot4_factored(selected, activations, z), expected)
                self.assertEqual(model.qdot4z_bits(word, acts, z, half),
                                 int.from_bytes(struct.pack("<i", expected), "little"))
                self.assertTrue(model.RESULT_MIN <= result <= model.RESULT_MAX)
                operations += 1
        COMPLETED_COUNTS["random_inputs"] = RANDOM_CASES
        COMPLETED_COUNTS["random_dot_products"] = operations

    def test_selector_ignores_only_the_unselected_weight_half(self):
        rng = random.Random(SEED + 1)
        for _ in range(1000):
            selected, unused = rng.getrandbits(16), rng.getrandbits(16)
            acts, z = rng.getrandbits(32), rng.randrange(16)
            low = model.qdot4z(selected, acts, z, 0)
            high = model.qdot4z(selected << 16, acts, z, 1)
            self.assertEqual(low, high)
            self.assertEqual(model.qdot4z(selected | (unused << 16), acts, z, 0), low)
            self.assertEqual(model.qdot4z((selected << 16) | unused, acts, z, 1), high)
        COMPLETED_COUNTS["selector_invariance_inputs"] = 1000

    def test_zero_point_affine_identity(self):
        weights, acts = [0, 15, 2, 9], [-128, 127, -1, 5]
        for z1 in range(16):
            for z2 in range(16):
                self.assertEqual(model.dot4(weights, acts, z2) - model.dot4(weights, acts, z1),
                                 -(z2 - z1) * sum(acts))
        COMPLETED_COUNTS["zero_point_pairs"] = 256

    def test_zero_activations_and_centered_weights(self):
        for z in range(16):
            self.assertEqual(model.dot4([0, 1, 14, 15], [0] * 4, z), 0)
            self.assertEqual(model.dot4([z] * 4, [-128, -1, 1, 127], z), 0)
        self.assertEqual(model.dot4([0, 15, 0, 15], [127] * 4, 8), -254)
        self.assertEqual(model.dot4([15] * 4, [127, -127, 1, -1], 0), 0)

    def test_neutral_activation_padding_for_tails(self):
        weights, acts = [5, 9, 10, 4], [4, -3, 2, 1]
        for count in range(5):
            padded = acts[:count] + [0] * (4 - count)
            expected = sum((weights[i] - 8) * acts[i] for i in range(count))
            self.assertEqual(model.dot4(weights, padded, 8), expected)

    def test_joint_lane_permutation(self):
        weights, acts = [0, 1, 7, 15], [-128, 127, -3, 11]
        expected = sum((w - 8) * a for w, a in zip(weights, acts))
        for order in itertools.permutations(range(4)):
            self.assertEqual(model.dot4([weights[i] for i in order],
                                       [acts[i] for i in order], 8), expected)
        COMPLETED_COUNTS["joint_permutations"] = 24

    def test_subtotal_bounds_and_output_encoding(self):
        self.assertEqual(model.dot4([15] * 4, [-128] * 4, 0), model.RESULT_MIN)
        self.assertEqual(model.dot4([0] * 4, [-128] * 4, 15), model.RESULT_MAX)
        for result in range(model.RESULT_MIN, model.RESULT_MAX + 1):
            expected = int.from_bytes(struct.pack("<i", result), "little")
            self.assertEqual(model.encode_s32(result), expected)
            self.assertEqual(model.decode_s32(expected), result)
        COMPLETED_COUNTS["bounded_result_encodings"] = model.RESULT_MAX - model.RESULT_MIN + 1
        for result in (model.S32_MIN, -1, 0, 1, model.S32_MAX):
            self.assertEqual(model.decode_s32(model.encode_s32(result)), result)

    def test_word_range_errors(self):
        for bad in (-1, 1 << 32):
            for call in (lambda: model.qdot4z(bad, 0, 0),
                         lambda: model.qdot4z(0, bad, 0),
                         lambda: model.decode_s32(bad),
                         lambda: model.unpack_weights(bad),
                         lambda: model.unpack_activations(bad)):
                with self.assertRaises(ValueError):
                    call()
        for bad in (-1, 16):
            with self.assertRaises(ValueError):
                model.qdot4z(0, 0, bad)
        for bad in (-1, 2):
            with self.assertRaises(ValueError):
                model.qdot4z(0, 0, 0, bad)
        for bad in (model.S32_MIN - 1, model.S32_MAX + 1):
            with self.assertRaises(ValueError):
                model.encode_s32(bad)

    def test_wrong_types_are_not_coerced(self):
        for bad in (True, False, 0.0, "0", None):
            for position in range(4):
                args = [0, 0, 0, 0]
                args[position] = bad
                with self.assertRaises(TypeError):
                    model.qdot4z(*args)
            for call in (lambda: model.pack_weights([bad] + [0] * 7),
                         lambda: model.pack_activations([bad] + [0] * 3),
                         lambda: model.encode_s32(bad)):
                with self.assertRaises(TypeError):
                    call()

    def test_lane_lengths_and_ranges(self):
        for length in (0, 3, 4, 7, 9):
            with self.assertRaises(ValueError):
                model.pack_weights([0] * length)
        for length in (0, 3, 5, 8):
            with self.assertRaises(ValueError):
                model.pack_activations([0] * length)
            for operation in (model.dot4, model.dot4_factored):
                with self.assertRaises(ValueError):
                    operation([0] * length, [0] * 4, 0)
                with self.assertRaises(ValueError):
                    operation([0] * 4, [0] * length, 0)
        for bad in (-1, 16):
            with self.assertRaises(ValueError):
                model.pack_weights([bad] + [0] * 7)
        for bad in (-129, 128):
            with self.assertRaises(ValueError):
                model.pack_activations([bad] + [0] * 3)
        for operation in (model.dot4, model.dot4_factored):
            with self.assertRaises(ValueError):
                operation([16, 0, 0, 0], [0] * 4, 0)
            with self.assertRaises(ValueError):
                operation([0] * 4, [128, 0, 0, 0], 0)
            with self.assertRaises(ValueError):
                operation([0] * 4, [0] * 4, 16)


if __name__ == "__main__":
    unittest.main()
