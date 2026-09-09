"""Positive and mutation checks for a plan, not measurements or kernel tests."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_campaign import validate, zero_points


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())

    def test_inventory(self):
        self.assertEqual(validate(self.manifest), dict(planned_cases=2280,
                         profile_cases={"zc_controls": 360, "zs_balanced_u4": 1920},
                         balanced_shape_seed_checks=30, execution_ready=False))

    def test_explicit_zero_point_schedule(self):
        zc, zs = self.manifest["zero_point_profiles"]
        self.assertEqual(zero_points(zc, 8, 2, 2), [[8, 8], [8, 8]])
        # Two groups exercise the assignment rule, not the initial campaign's K.
        self.assertEqual(zero_points(zs, 15, 2, 2), [[15, 4], [0, 5]])

    def test_reject_incomplete_or_misleading_plans(self):
        mutations = [
            lambda m: m["grid"].update(N=[1]),
            lambda m: m["grid"].update(N=[True, 4, 16]),
            lambda m: m["grid"].update(variants=["B1", "B2", "D"]),
            lambda m: m["grid"]["tensor_seeds"].append(True),
            lambda m: m["zero_point_profiles"][1].update(phases=list(range(15))),
            lambda m: m["zero_point_profiles"][0].update(values=[False, 8, 15]),
            lambda m: m["zero_point_profiles"][1].update(group_stride=0),
            lambda m: m["zero_point_profiles"][1].update(rationale=""),
            lambda m: m["zero_point_strata"]["remaining_u4_codes"].append(0),
            lambda m: m["reporting"].update(retain_every_planned_case=False),
            lambda m: m["reporting"].update(global_speedup_across_z_profiles=True),
            lambda m: m["reporting"].update(terminal_statuses=["pass"]),
            lambda m: m["optimization"].update(force_runtime_correction_for_z_zero=True),
            lambda m: m["optimization"].update(allow_compile_time_tensor_arithmetic=True),
            lambda m: m.update(status="ready"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(self.manifest)
                mutate(changed)
                with self.assertRaises(ValueError):
                    validate(changed)


if __name__ == "__main__":
    unittest.main()
