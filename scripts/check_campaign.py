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
    require(manifest["manifest_version"] == "0.1", "Unsupported manifest version")
    require(manifest["status"] == "design_only", "This checker does not certify runnable campaigns")
    require(manifest["protocol"] == "docs/EXPERIMENT_PROTOCOL.md" and
            manifest["protocol_version"] == "0.2", "Protocol reference mismatch")
    grid = manifest["grid"]
    integer_list(grid["N"], "N", 1, 16)
    integer_list(grid["K"], "K", 1, 512)
    require(grid["variants"] == ["B1", "B2", "B3", "D"], "All four variants required")
    require(grid["N"] == [1, 4, 16], "Initial campaign must retain the N sweep")
    require(grid["K"] == [32] and type(grid["G"]) is int and grid["G"] == 32,
            "Initial campaign is K=G=32; revise its version to expand")
    integer_list(grid["tensor_seeds"], "tensor_seeds", 0, 2**32-1)
    require(grid["tensor_seeds"] == list(range(20260908, 20260918)), "Initial seed inventory changed")
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
    pending = ("logical_elements_per_unrolled_iteration", "row_group_traversal", "register_allocation_and_spill_policy",
               "equal_z_correction_reuse_policy", "strength_reduction_and_scheduling_policy")
    require(all(optimization[key] is None for key in pending), "Version 0.1 has unresolved policies; revise before selecting them")
    require(len(manifest["execution_blockers"]) >= len(pending), "Missing explicit execution blockers")
    return dict(planned_cases=len(case_ids), profile_cases=dict(profile_cases),
                balanced_shape_seed_checks=distribution_checks, execution_ready=False)


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
