"""Freeze the selected policies in Git before any kernel is timed.

A freeze is only worth recording if a later change fails loudly, so this writes
hashes that check_project re-derives from the working tree: the policy text in
the manifest, the generators and tests that implement it, and the assembly,
disassembly and text of every kernel the pinned evidence already contains.
Changing any of them after this point requires the declared procedure, not a
quiet edit.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "riscv64-linux-gnu-"

# Which files implement each policy. kernels.py appears in both because the
# scalar and packed builders share it; overlap is honest, not a mistake.
IMPLEMENTS = {
    "bounded_masked_bit_decomposition_v1": dict(
        manifest_key="b1_software_multiply_policy",
        generator=["benchmarks/b1_arithmetic.py", "benchmarks/kernels.py"],
        tests=["tests/benchmarks/test_b1_arithmetic.py"],
        variants=["B1"]),
    "shared_tile_resident_skeleton_v2": dict(
        manifest_key="common_kernel_policy",
        generator=["benchmarks/kernels.py", "benchmarks/tensors.py"],
        tests=["tests/benchmarks/test_campaign.py"],
        variants=["B1", "B2", "B3", "D"]),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition: raise RuntimeError(message)


def disassemble(elf):
    """Hash the listing rather than store it; the ELF is already pinned."""
    listing = subprocess.run([PREFIX + "objdump", "-d", "--section=.text", str(elf)],
                             capture_output=True, text=True, check=True).stdout
    # Drop the header, which names the file and would hash its path.
    body = "\n".join(listing.splitlines()[2:])
    return hashlib.sha256(body.encode()).hexdigest()


def kernel_artifacts(variants):
    """Assembly, text and disassembly of every arm the pinned evidence holds."""
    state = json.loads((ROOT / "docs/KERNEL_STATE.json").read_text())
    evidence = ROOT / state["evidence"]
    require(sha(evidence) == state["evidence_sha256"], "Kernel evidence does not match its pin")
    report = json.loads(evidence.read_text())
    require(report["status"] == "pass", "Kernel evidence did not pass")
    arms = {}
    for name, case in sorted(report["cases"].items()):
        if case["variant"] not in variants: continue
        directory = evidence.parent
        arms[name] = dict(assembly=sha(directory / f"{name}.S"),
                          text=sha(directory / f"{name}.bin"),
                          disassembly=disassemble(directory / f"{name}.elf"))
    return state["evidence"], state["evidence_sha256"], arms


def freeze():
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    optimization = manifest["optimization"]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    record = dict(frozen_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                  parent_git_revision=revision,
                  required_before="first_kernel_timing_including_pilot",
                  post_measurement_change="new_version_with_reason_prior_observations_retained_and_affected_pairs_rerun",
                  measurements_taken=False, policies={})
    for policy_id, spec in IMPLEMENTS.items():
        policy = optimization[spec["manifest_key"]]
        require(policy["id"] == policy_id, f"Manifest policy id changed: {policy_id}")
        evidence, evidence_hash, arms = kernel_artifacts(spec["variants"])
        # The claim that matters is not that the whole tree is clean but that
        # every file this freeze pins lands in the same commit as the record:
        # freezing an uncommitted generator would pin something nobody else can
        # reproduce. Compare against the index, since the freeze is written and
        # committed together with the files it pins.
        for path in spec["generator"] + spec["tests"]:
            staged = subprocess.run(["git", "show", f":{path}"], cwd=ROOT,
                                    capture_output=True, check=True).stdout
            require(hashlib.sha256(staged).hexdigest() == sha(ROOT / path),
                    f"{path} is not staged as frozen; git add it before freezing")
        record["policies"][policy_id] = dict(
            manifest_key=spec["manifest_key"], policy=policy,
            generator={p: sha(ROOT / p) for p in spec["generator"]},
            tests={p: sha(ROOT / p) for p in spec["tests"]},
            frozen_files_committed_with_this_record=True,
            kernel_evidence=evidence, kernel_evidence_sha256=evidence_hash,
            variants=spec["variants"], arms=arms)
    return record


def main():
    record = freeze()
    (ROOT / "docs/POLICY_FREEZE.json").write_text(json.dumps(record, indent=2) + "\n")
    for policy_id, entry in record["policies"].items():
        print(f"frozen {policy_id}: {len(entry['arms'])} arms, "
              f"{len(entry['generator'])} generator files, {len(entry['tests'])} test files")
    print(f"parent {record['parent_git_revision'][:7]}; every pinned file is staged with this record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
