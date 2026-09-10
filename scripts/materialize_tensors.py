"""Materialize every planned case's inputs before any of them is measured.

The manifest requires the packed tensors, the zero-point matrix, the effective
histogram, the expected outputs and a hash to exist before measurement, so that
a later run cannot quietly use different inputs and so that a case that never
ran is visibly missing rather than silently absent.

Nothing here is a measurement. The values are derived from the seed and the
declared schedule, and check_project recomputes them rather than trusting this
file.
"""
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
from tensors import (tensors, zero_points, expected_outputs, activation_sum,
                     pack_activations, pack_weights)

OUTPUT = ROOT / "benchmarks/inventory.json"


def digest(*parts):
    stream = hashlib.sha256()
    for part in parts:
        stream.update(json.dumps(part, sort_keys=True, separators=(",", ":")).encode())
    return stream.hexdigest()


def settings(manifest):
    """Every declared z assignment, in the manifest's own order."""
    for profile in manifest["zero_point_profiles"]:
        values = profile["values"] if profile["regime"] == "ZC" else profile["phases"]
        for value in values:
            yield profile["id"], value


def build():
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    grid = manifest["grid"]
    k, g = grid["K"][0], grid["G"]
    record = dict(built_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                  manifest_version=manifest["manifest_version"],
                  k=k, g=g, shapes=grid["N"], seeds=grid["tensor_seeds"],
                  variants=grid["variants"], measurements_taken=False,
                  tensors={}, groups={}, cases={})

    for rows in grid["N"]:
        for seed in grid["tensor_seeds"]:
            activations, weights = tensors(seed, rows, k)
            packed_w = [pack_weights(row) for row in weights]
            packed_a = pack_activations(activations)
            record["tensors"][f"n{rows}_s{seed}"] = dict(
                rows=rows, seed=seed,
                packed_weights=packed_w, packed_activations=packed_a,
                activation_sum=activation_sum(activations),
                sha256=digest(packed_w, packed_a))

    for rows in grid["N"]:
        for seed in grid["tensor_seeds"]:
            activations, weights = tensors(seed, rows, k)
            for profile, value in settings(manifest):
                zeros = zero_points(profile, value, rows, k // g)
                column = [row[0] for row in zeros]
                outputs = expected_outputs(weights, activations, zeros)
                name = f"n{rows}_s{seed}_{profile}_{value}"
                record["groups"][name] = dict(
                    rows=rows, seed=seed, profile=profile, setting=value,
                    zero_point_matrix=zeros,
                    effective_z_histogram={str(z): c for z, c in sorted(Counter(column).items())},
                    expected_group_outputs=outputs,
                    sha256=digest(zeros, outputs))
                # A case binds a variant to a group and to its tensors, so any
                # input change moves the case hash and a swap cannot hide.
                tensor = record["tensors"][f"n{rows}_s{seed}"]
                for variant in grid["variants"]:
                    record["cases"][f"{variant}_{name}"] = dict(
                        variant=variant, group=name,
                        sha256=digest(variant, tensor["sha256"], record["groups"][name]["sha256"]))
    # A single row cannot have a varying zero point, so at N=1 the constant
    # controls coincide with the phases of the same value and the two regimes
    # produce identical inputs. Recorded because a ZC/ZS contrast at N=1 is
    # degenerate and must not be read as a regime effect.
    shared = sorted(set(manifest["zero_point_profiles"][0]["values"]) &
                    set(manifest["zero_point_profiles"][1]["phases"]))
    record["regimes_coincide_at_one_row"] = dict(
        shared_settings=shared,
        colliding_cases=len(shared) * len(grid["tensor_seeds"]) * len(grid["variants"]),
        note="At N=1 a constant zero point and a phase of the same value give the "
             "same program, so those cases share one input hash by construction.")
    return record


def main():
    record = build()
    OUTPUT.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(f"materialized {len(record['tensors'])} tensor sets, "
          f"{len(record['groups'])} groups and {len(record['cases'])} cases")
    print(f"inventory {OUTPUT.relative_to(ROOT)}: "
          f"{OUTPUT.stat().st_size // 1024} KB, no case has been measured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
