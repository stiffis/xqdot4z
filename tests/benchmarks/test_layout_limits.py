"""Pins how far the frozen data layout reaches, and where it stops being safe.

The campaign measured K=32 only. RQ3 also asks about K and G, so the layout will
have to reach further, and this file records what stands in the way before anyone
assumes it merely works. One of the entries is a defect kept on purpose: fixing it
edits a frozen generator, which the freeze allows only by versioning the policy,
and that moves the design fingerprint into a new registration. It is therefore
fixed together with the K extension that pays that cost anyway, not before.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks"))
import tensors


def activation_span(plan):
    low = plan["activations"]
    return low, low + plan["activation_words"] * 4 - 1


class LayoutLimitTests(unittest.TestCase):
    def test_measured_configuration_has_no_overlap(self):
        """K=32 is what the campaign ran, and its regions are adjacent, not shared."""
        for rows in (1, 4, 16):
            plan = tensors.layout(rows, 32)
            _, activation_high = activation_span(plan)
            self.assertLess(activation_high, plan["weights"])
            self.assertLess(plan["weights"] + rows * plan["weight_words_per_row"] * 4,
                            plan["zero_points"] + 1)

    def test_activation_guard_is_missing_above_k32(self):
        """Known defect, pinned so it cannot be forgotten.

        layout() checks weights against zero points and zero points against
        outputs, but never activations against weights. At K=32 the two regions
        end and begin on the same byte, so the omission never shows; above it the
        activations run straight into the weights and no error is raised. Fixing
        the guard makes this test fail, which is the point: it forces whoever
        fixes it to version the policy deliberately rather than in passing.
        """
        plan = tensors.layout(1, 128)
        _, activation_high = activation_span(plan)
        self.assertGreaterEqual(activation_high, plan["weights"])

    def test_weight_region_bounds_the_reachable_shapes(self):
        """The grid RQ3 asks for does not fit the frozen constants."""
        unreachable = [(16, 128), (4, 512), (16, 512)]
        for rows, k in unreachable:
            with self.assertRaises(ValueError):
                tensors.layout(rows, k)

    def test_largest_row_count_exhausts_the_weight_region(self):
        """N=16 at K=32 leaves no room, so any larger K needs new constants."""
        plan = tensors.layout(16, 32)
        used = plan["weights"] + 16 * plan["weight_words_per_row"] * 4
        self.assertEqual(used, plan["zero_points"])

    def test_k512_exceeds_the_data_memory_regardless_of_bases(self):
        """Even relaid out, K=512 is a memory-model change, not a layout change."""
        weights = 16 * tensors.words_per_row(512) * 4
        activations = (512 // 4) * 4
        self.assertGreater(weights + activations, tensors.DMEM_WORDS * 4)


if __name__ == "__main__":
    unittest.main()
