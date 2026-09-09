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
                         balanced_shape_seed_checks=30, pilot_subset_cases=32, execution_ready=False))

    def test_explicit_zero_point_schedule(self):
        zc, zs = self.manifest["zero_point_profiles"]
        self.assertEqual(zero_points(zc, 8, 2, 2), [[8, 8], [8, 8]])
        # Two groups exercise the assignment rule, not the initial campaign's K.
        self.assertEqual(zero_points(zs, 15, 2, 2), [[15, 4], [0, 5]])

    def test_group_stride_is_inactive_for_one_group(self):
        profile = self.manifest["zero_point_profiles"][1]
        changed = dict(profile, group_stride=0)
        for n in self.manifest["grid"]["N"]:
            for phase in profile["phases"]:
                self.assertEqual(zero_points(profile, phase, n, 1),
                                 zero_points(changed, phase, n, 1))

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

    def test_reject_seed_and_b1_policy_regressions(self):
        mutations = [
            lambda m: m["seed_policy"].update(independent_timing_repetitions=True),
            lambda m: m["seed_policy"].update(collect_metrics_for_all_grid_seeds=False),
            lambda m: m["seed_policy"].update(full_kernel_cycle_invariance="verified"),
            lambda m: m["seed_policy"].update(reduce_grid_after_two_equal_cycle_totals=True),
            lambda m: m["seed_policy"]["pilot"].update(status="ready"),
            lambda m: m["seed_policy"]["pilot"].update(variants=["D"]),
            lambda m: m["seed_policy"]["pilot"].update(tensor_seeds=[20260908, 20260918]),
            lambda m: m["seed_policy"]["pilot"].update(compare=["cycles"]),
            lambda m: m["seed_policy"]["pilot"].update(zs_phases=[False]),
            lambda m: m["seed_policy"]["pilot"].update(equal_totals_prove_input_independence=True),
            lambda m: m["zero_point_profiles"][1].update(group_stride_exercised_in_initial_grid=True),
            lambda m: m["optimization"]["b1_software_multiply_policy"].update(width_and_sign="generic_32_bit"),
            lambda m: m["optimization"]["b1_software_multiply_policy"].update(selection_policy="branch_per_bit"),
            lambda m: m["optimization"]["b1_software_multiply_policy"].update(performance_driven_algorithm_search=True),
            lambda m: m["b1_freeze"].update(required_before="after_pilot"),
            lambda m: m["b1_freeze"]["record"].remove("text_hash"),
            lambda m: m["execution_blockers"].pop(-2),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(self.manifest)
                mutate(changed)
                with self.assertRaises(ValueError):
                    validate(changed)


if __name__ == "__main__":
    unittest.main()
