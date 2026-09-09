"""Validate the design-only campaign inventory; never run or time a kernel.

This checks structural/coverage properties, not semantic agreement with prose
or readiness to measure. The normative method remains EXPERIMENT_PROTOCOL.md.
"""

import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer_list(value, name, minimum, maximum):
    require(isinstance(value, list) and bool(value), f"{name}: nonempty list required")
    require(all(type(x) is int and minimum <= x <= maximum for x in value), f"{name}: invalid integer")
    require(len(value) == len(set(value)), f"{name}: duplicate value")


def zero_points(profile, setting, n, groups):
    if profile["assignment"] == "constant":
        return [[setting for _ in range(groups)] for _ in range(n)]
    require(profile["assignment"] == "cyclic_affine_modulo", "Unknown assignment")
    return [[(setting + profile["row_stride"]*r + profile["group_stride"]*g)
             % profile["modulus"] for g in range(groups)] for r in range(n)]


def validate(manifest):
    require(manifest["manifest_version"] == "0.3", "Unsupported manifest version")
    require(manifest["status"] == "design_only", "This checker does not certify runnable campaigns")
    require(manifest["protocol"] == "docs/EXPERIMENT_PROTOCOL.md" and
            manifest["protocol_version"] == "0.4", "Protocol reference mismatch")
    grid = manifest["grid"]
    integer_list(grid["N"], "N", 1, 16)
    integer_list(grid["K"], "K", 1, 512)
    require(grid["variants"] == ["B1", "B2", "B3", "D"], "All four variants required")
    require(grid["N"] == [1, 4, 16], "Initial campaign must retain the N sweep")
    require(grid["K"] == [32] and type(grid["G"]) is int and grid["G"] == 32,
            "Initial campaign is K=G=32; revise its version to expand")
    integer_list(grid["tensor_seeds"], "tensor_seeds", 0, 2**32-1)
    require(grid["tensor_seeds"] == list(range(20260908, 20260918)), "Initial seed inventory changed")
    seeds = manifest["seed_policy"]
    require(seeds["primary_role"] == "input_correctness_coverage", "Seeds are input coverage")
    require(seeds["collect_metrics_for_all_grid_seeds"] is True, "Do not silently reduce seed coverage")
    require(seeds["independent_timing_repetitions"] is False, "Seeds are not timing repetitions")
    require(seeds["full_kernel_cycle_invariance"] == "unverified", "No verified performance kernels yet")
    require(seeds["reduce_grid_after_two_equal_cycle_totals"] is False, "Two totals cannot authorize reduction")
    require(bool(seeds["reduction_gate"].strip()), "Explicit reduction gate required")
    pilot = seeds["pilot"]
    require(pilot["status"] == "blocked_until_kernels_and_counters_are_verified", "Pilot is not ready")
    require(all(type(pilot[key]) is int for key in ("N", "K", "G")), "Integer pilot dimensions required")
    require((pilot["N"], pilot["K"], pilot["G"]) == (4, 32, 32), "Initial pilot shape changed")
    require(pilot["variants"] == grid["variants"], "Pilot must exercise all variants")
    for key, expected in (("tensor_seeds", grid["tensor_seeds"][:2]), ("zc_values", [0, 8, 15]), ("zs_phases", [0])):
        integer_list(pilot[key], "pilot " + key, 0, 2**32-1)
        require(pilot[key] == expected, "Initial pilot selection changed: " + key)
    require(pilot["inventory_relation"] == "subset_of_grid_no_new_case_ids", "Pilot must reuse grid identifiers")
    require(pilot["hold_fixed"] == ["text_hash", "data_layout", "zero_point_matrix", "core_configuration", "memory_model", "measurement_events"], "Missing pilot controls")
    require(pilot["compare"] == ["cycles", "retired_instructions", "retired_pc_opcode_trace", "branch_outcomes", "stall_breakdown", "data_address_trace"], "Pilot must compare more than cycle totals")
    require(pilot["equal_totals_prove_input_independence"] is False, "Equal totals are not a proof")
    strata = manifest["zero_point_strata"]
    require(set(strata) == {"zero", "one", "powers_of_two_gt_one", "remaining_u4_codes"}, "Strata labels changed")
    codes = []
    for name, values in strata.items():
        integer_list(values, name, 0, 15)
        codes.extend(values)
    require(sorted(codes) == list(range(16)), "Strata must partition U4 exactly once")
    require(strata["zero"] == [0] and strata["one"] == [1] and
            strata["powers_of_two_gt_one"] == [2, 4, 8], "Special-code strata mismatch")
    profiles = manifest["zero_point_profiles"]
    require(len(profiles) == 2 and {p["id"] for p in profiles} == {"zc_controls", "zs_balanced_u4"},
            "Initial profile inventory changed")
    case_ids = set()
    distribution_checks = 0
    profile_cases = Counter()
    for profile in profiles:
        require(bool(profile["rationale"].strip()), "Profile rationale required")
        if profile["id"] == "zc_controls":
            require(profile["assignment"] == "constant" and profile["regime"] == "ZC", "ZC assignment mismatch")
            integer_list(profile["values"], "ZC values", 0, 15)
            require(profile["values"] == [0, 8, 15], "Initial ZC controls changed")
            settings = profile["values"]
        else:
            require(profile["assignment"] == "cyclic_affine_modulo" and profile["regime"] == "ZS", "ZS assignment mismatch")
            require(all(type(profile[key]) is int for key in ("modulus", "row_stride", "group_stride")), "Integer strides required")
            require((profile["modulus"], profile["row_stride"], profile["group_stride"]) == (16, 1, 5), "Initial ZS schedule changed")
            require(profile["group_stride_exercised_in_initial_grid"] is False, "K=G does not exercise group stride")
            integer_list(profile["phases"], "phases", 0, 15)
            require(profile["phases"] == list(range(16)), "All ZS phases required")
            settings = profile["phases"]
        for n, k, seed in itertools.product(grid["N"], grid["K"], grid["tensor_seeds"]):
            histogram = Counter()
            for setting in settings:
                matrix = zero_points(profile, setting, n, k//grid["G"])
                histogram.update(z for row in matrix for z in row)
                for variant in grid["variants"]:
                    case_id = (variant, n, k, grid["G"], seed, profile["id"], setting)
                    require(case_id not in case_ids, "Duplicate case identifier")
                    case_ids.add(case_id)
                    profile_cases[profile["id"]] += 1
            if profile["regime"] == "ZS":
                require(histogram == Counter({z: n*(k//grid["G"]) for z in range(16)}), "Unbalanced ZS coverage")
                distribution_checks += 1
    pilot_ids = {(variant, pilot["N"], pilot["K"], pilot["G"], seed, profile, setting)
                 for variant in pilot["variants"] for seed in pilot["tensor_seeds"]
                 for profile, settings in (("zc_controls", pilot["zc_values"]), ("zs_balanced_u4", pilot["zs_phases"]))
                 for setting in settings}
    require(len(pilot_ids) == 32 and pilot_ids <= case_ids, "Pilot must be a 32-case grid subset")
    require(manifest["pairing"]["text"] == "identical_across_tensor_seeds_for_each_variant_shape_and_z_assignment", "Seed pairs must share text")
    reporting = manifest["reporting"]
    for key in ("retain_every_planned_case", "retain_failed_attempts", "report_zc_and_zs_separately", "report_each_profile_and_phase"):
        require(reporting[key] is True, f"Required reporting policy: {key}")
    require(reporting["global_speedup_across_z_profiles"] is False, "No pooled z speedup")
    require(reporting["terminal_statuses"] == ["pass", "fail", "timeout", "unsupported"], "Missing outcome status")
    require(reporting["unsupported_or_failed_speedup"] is None, "Invalid cases have no speedup")
    optimization = manifest["optimization"]
    for key in ("shared_b3_d_skeleton_required", "common_policy_for_all_variants_required", "allow_semantically_valid_constant_specializations"):
        require(optimization[key] is True, f"Required optimization policy: {key}")
    require(optimization["force_runtime_correction_for_z_zero"] is False, "Do not force useless zero correction")
    require(optimization["allow_compile_time_tensor_arithmetic"] is False, "Do not precompute tensor arithmetic in codegen")
    b1 = optimization["b1_software_multiply_policy"]
    for key, expected in {
        "id": "bounded_masked_bit_decomposition_v1",
        "status": "selected_before_performance_measurement",
        "role": "context_baseline_not_fusion_causal_comparator",
        "formulation_and_scanned_operand": "direct_(w-z)*a_scan_weight_difference_bits",
        "width_and_sign": "U4_for_z0_S4_for_z8_S5_otherwise_S8_activation_RV32_arithmetic",
        "iteration_policy": "straight_line_positive_bit_additions_then_signed_top_bit_subtraction_no_early_exit",
        "selection_policy": "zero_or_all_one_masks_no_operand_dependent_branches_or_lookups",
        "specialization_policy": "static_z_materialization_and_z0_subtraction_elision_with_declared_width_folding_only_no_tensor_shortcuts_or_cross_row_factoring",
    }.items():
        require(b1[key] == expected, "Selected B1 policy changed: " + key)
    require(bool(b1["selection_basis"].strip()) and b1["performance_driven_algorithm_search"] is False,
            "B1 is a bounded contextual baseline, not an optimization search")
    common = optimization["common_kernel_policy"]
    for key, expected in {
        "id": "shared_group_resident_skeleton_v1",
        "status": "selected_before_performance_measurement",
        "role": "common_codegen_policy_for_all_four_variants",
    }.items():
        require(common[key] == expected, "Selected common policy changed: " + key)
    require(bool(common["selection_basis"].strip()), "Common policy selection basis required")
    require(len(common["declared_consequences"]) == 3 and
            all(bool(text.strip()) for text in common["declared_consequences"]),
            "Common policy must declare its unroll, residency and reuse consequences")
    elements = optimization["logical_elements_per_unrolled_iteration"]
    require(type(elements) is int and elements == 8,
            "Initial iteration is eight logical elements: one packed weight word and two activation words")
    require(all(k % elements == 0 for k in grid["K"]), "Unrolled iteration must divide every K")
    for key, expected in {
        "row_group_traversal": "group_outer_row_inner_activations_resident_across_rows",
        "register_allocation_and_spill_policy": "reserve_the_group_activation_words_and_the_row_accumulator_for_the_whole_group_no_inner_loop_spills_identical_reservation_for_every_variant",
        "equal_z_correction_reuse_policy": "hoist_the_shared_z_correction_only_when_the_declared_zero_point_schedule_repeats_z_never_from_tensor_or_measured_value_inspection",
        "strength_reduction_and_scheduling_policy": "reduce_only_on_statically_declared_constants_and_apply_one_common_scheduling_pass_to_every_variant_without_manual_per_variant_reordering",
    }.items():
        require(optimization[key] == expected, "Selected common policy changed: " + key)
    require(optimization["row_group_traversal_exercised_in_initial_grid"] is False,
            "K=G leaves the traversal order unexercised")
    # The reuse policy only pays off where the declared schedule repeats z, so
    # check the schedules themselves rather than trusting the prose.
    for profile in profiles:
        settings = profile["values"] if profile["regime"] == "ZC" else profile["phases"]
        for setting in settings:
            for n in grid["N"]:
                rows = [row[0] for row in zero_points(profile, setting, n, 1)]
                repeats = len(set(rows)) < len(rows)
                require(repeats is (profile["regime"] == "ZC" and n > 1),
                        "Reuse across rows must follow the declared schedule: " + profile["id"])
    for freeze, policy_id in ((manifest["b1_freeze"], b1["id"]), (manifest["common_policy_freeze"], common["id"])):
        require(freeze["required_before"] == "first_kernel_timing_including_pilot", "Policies must freeze before the pilot")
        require(freeze["policy_id"] == policy_id, "Freeze policy mismatch")
        require(freeze["record"] == ["policy", "generator", "assembly", "disassembly", "text_hash", "tests", "git_revision"], "Incomplete freeze record")
        require(freeze["post_measurement_change"] == "new_version_with_reason_prior_observations_retained_and_affected_pairs_rerun", "Policy changes must preserve history")
    require(manifest["execution_blockers"] == [
        "implement and verify paired kernels and their disassembly allowlist checks",
        "fix common memory capacities and the initialized data layout",
        "define and test the concrete measurement events and all protocol counters",
        "materialize tensors and the complete case inventory with hashes",
        "freeze B1 policy, generator, assembly, disassembly, text hash and tests in Git before any kernel timing, including the pilot",
        "freeze the common kernel policy, generator, assembly, disassembly, text hash and tests in Git before any kernel timing, including the pilot",
        "record the pre-measurement revision and any observed development timings",
    ], "Execution blockers changed; selecting the common policies does not unblock measurement")
    return dict(planned_cases=len(case_ids), profile_cases=dict(profile_cases),
                balanced_shape_seed_checks=distribution_checks, pilot_subset_cases=len(pilot_ids), execution_ready=False)


def check():
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    report = validate(manifest)
    protocol = (ROOT / manifest["protocol"]).read_text()
    require(protocol.startswith("# Protocolo experimental — versión " + manifest["protocol_version"] + "\n"),
            "Protocol document version mismatch")
    print("OK: static-z manifest:", json.dumps(report, sort_keys=True))
    print("Design-only coverage check; kernels, policies and measurement events remain unverified.")
    return report


if __name__ == "__main__":
    check()
