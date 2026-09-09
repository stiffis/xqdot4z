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
        self._assert_all_rejected(mutations)

    def test_common_policy_matches_the_operand_word_shape(self):
        optimization = self.manifest["optimization"]
        elements = optimization["logical_elements_per_unrolled_iteration"]
        # Eight logical elements is one packed weight word and two activation
        # words, so an iteration consumes whole operands and divides every K.
        self.assertEqual(elements, 8)
        self.assertEqual(elements % 8, 0)
        self.assertEqual(elements % 4, 0)
        for k in self.manifest["grid"]["K"]:
            self.assertEqual(k % elements, 0)
        self.assertIs(optimization["row_group_traversal_exercised_in_initial_grid"], False)
        self.assertEqual(len(optimization["common_kernel_policy"]["declared_consequences"]), 3)

    def test_correction_reuse_follows_the_declared_schedule(self):
        zc, zs = self.manifest["zero_point_profiles"]
        for n in self.manifest["grid"]["N"]:
            # ZC repeats z across rows, so B3 may hoist z*Sa once per case.
            self.assertEqual(len({row[0] for row in zero_points(zc, 8, n, 1)}), 1)
            # ZS gives each row a distinct z for N<=16, so B3 corrects per row.
            for phase in zs["phases"]:
                rows = [row[0] for row in zero_points(zs, phase, n, 1)]
                self.assertEqual(len(set(rows)), n)

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
        self._assert_all_rejected(mutations)

    def test_reject_common_policy_regressions(self):
        mutations = [
            lambda m: m["optimization"].update(logical_elements_per_unrolled_iteration=None),
            lambda m: m["optimization"].update(logical_elements_per_unrolled_iteration=6),
            lambda m: m["optimization"].update(logical_elements_per_unrolled_iteration=True),
            lambda m: m["optimization"].update(row_group_traversal="row_outer_group_inner"),
            lambda m: m["optimization"].update(row_group_traversal_exercised_in_initial_grid=True),
            lambda m: m["optimization"].update(register_allocation_and_spill_policy="per_variant_manual"),
            lambda m: m["optimization"].update(
                equal_z_correction_reuse_policy="hoist_whenever_measured_values_repeat"),
            lambda m: m["optimization"].update(
                strength_reduction_and_scheduling_policy="per_variant_manual_reordering"),
            lambda m: m["optimization"]["common_kernel_policy"].update(id="tuned_after_timing_v2"),
            lambda m: m["optimization"]["common_kernel_policy"].update(status="selected_after_pilot"),
            lambda m: m["optimization"]["common_kernel_policy"].update(selection_basis="  "),
            lambda m: m["optimization"]["common_kernel_policy"]["declared_consequences"].pop(),
            lambda m: m["common_policy_freeze"].update(required_before="after_pilot"),
            lambda m: m["common_policy_freeze"].update(policy_id="bounded_masked_bit_decomposition_v1"),
            lambda m: m["common_policy_freeze"]["record"].remove("text_hash"),
            # Selecting the policies must not retire an unrelated blocker.
            lambda m: m["execution_blockers"].remove(
                "define and test the concrete measurement events and all protocol counters"),
            lambda m: m["execution_blockers"].remove(
                "freeze the common kernel policy, generator, assembly, disassembly,"
                " text hash and tests in Git before any kernel timing, including the pilot"),
        ]
        self._assert_all_rejected(mutations)

    def _assert_all_rejected(self, mutations):
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(self.manifest)
                mutate(changed)
                with self.assertRaises(ValueError):
                    validate(changed)


if __name__ == "__main__":
    unittest.main()
