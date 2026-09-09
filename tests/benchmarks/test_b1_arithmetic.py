"""Arithmetic-policy checks only: no CPU execution or performance evidence."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks"))
from b1_arithmetic import POLICY_ID, multiply_term, operand_format


class B1ArithmeticTests(unittest.TestCase):
    def test_policy_identity_and_static_widths(self):
        manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
        self.assertEqual(POLICY_ID, manifest["optimization"]["b1_software_multiply_policy"]["id"])
        for z in range(16):
            expected = (4, False) if z == 0 else (4, True) if z == 8 else (5, True)
            self.assertEqual(operand_format(z), expected)

    def test_all_u4_z_s8_triples(self):
        count = 0
        extrema = [0, 0]
        for weight in range(16):
            for z in range(16):
                for activation in range(-128, 128):
                    actual = multiply_term(weight, z, activation)
                    expected = (weight - z) * activation
                    self.assertEqual(actual, expected, (weight, z, activation))
                    extrema = [min(extrema[0], actual), max(extrema[1], actual)]
                    count += 1
        self.assertEqual(count, 65536)
        self.assertEqual(extrema, [-1920, 1920])

    def test_directed_sign_and_zero_cases(self):
        for operands, expected in [((0, 15, -128), 1920), ((15, 0, -128), -1920),
                                   ((0, 8, -128), 1024), ((15, 8, 127), 889),
                                   ((7, 8, 127), -127), ((0, 15, 127), -1905),
                                   ((8, 8, -128), 0), ((1, 15, 0), 0)]:
            with self.subTest(operands=operands):
                self.assertEqual(multiply_term(*operands), expected)

    def test_reject_out_of_contract_inputs(self):
        for index, invalid_values in enumerate(([-1, 16, True, 1.0],
                                                [-1, 16, False, 1.0],
                                                [-129, 128, True, 1.0])):
            for value in invalid_values:
                operands = [3, 8, -128]
                operands[index] = value
                with self.subTest(index=index, value=value):
                    with self.assertRaises(ValueError):
                        multiply_term(*operands)


if __name__ == "__main__":
    unittest.main()
