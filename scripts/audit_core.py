"""Reproduce historical tests and focused probes without editing the snapshot.

Each invocation creates a new evidence directory; old evidence is retained.
The exit status describes successful reproduction, NOT ISA conformance.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "baseline/upstream"
LOCK = ROOT / "baseline/LOCK.json"
MANIFEST = ROOT / "baseline/SHA256SUMS"


def hashes():
    return {
        str(p.relative_to(SNAPSHOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(SNAPSHOT.rglob("*")) if p.is_file()
    }


def verify_snapshot():
    recorded = {}
    for line in MANIFEST.read_text().splitlines():
        digest, name = line.split("  ", 1)
        recorded[name] = digest
    current = hashes()
    if current != recorded:
        changed = sorted(k for k in current.keys() | recorded.keys()
                         if current.get(k) != recorded.get(k))
        raise SystemExit("Snapshot changed: " + ", ".join(changed))
    print(f"Snapshot intact: {len(current)} files")


def execute(command, cwd, output, name, timeout=60):
    run = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                         timeout=timeout, check=False)
    (output / f"{name}.stdout.log").write_text(run.stdout)
    (output / f"{name}.stderr.log").write_text(run.stderr)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true",
                        help="Create the initial snapshot manifest; refuses overwrite")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.seal:
        with MANIFEST.open("x") as handle:
            for name, digest in hashes().items():
                handle.write(f"{digest}  {name}\n")
    verify_snapshot()
    if args.verify_only or args.seal:
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "audit/results" / stamp
    output.mkdir(parents=True, exist_ok=False)
    lock = json.loads(LOCK.read_text())
    versions = {}
    for tool in ("iverilog", "vvp"):
        result = execute([tool, "-V"], ROOT, output, f"version-{tool}")
        versions[tool] = (result.stdout + result.stderr).splitlines()[0]

    with tempfile.TemporaryDirectory(prefix="xqdot4z-audit-") as temporary:
        work = Path(temporary) / "core"
        shutil.copytree(SNAPSHOT, work)
        regression = execute(["bash", "run_tests.sh"], work, output,
                             "regression", timeout=120)
        total = re.search(r"Total: (\d+) PASS, (\d+) FAIL", regression.stdout)
        if not total:
            raise SystemExit(f"No regression summary; inspect {output}")
        passed, failed = map(int, total.groups())
        # Keep compiler diagnostics that the historical runner does not print.
        logs = output / "compile-logs"
        logs.mkdir()
        for log in (work / "build").glob("*.compile.log"):
            shutil.copy2(log, logs / log.name)
        binary = Path(temporary) / "observations.vvp"
        sources = [work / "rtl/decompressor.v", work / "rtl/hazardunit.v",
                   ROOT / "audit/tests/tb_observations.sv"]
        compile_run = execute(["iverilog", "-g2012", "-s", "tb_observations",
                               "-o", str(binary), *map(str, sources)],
                              work, output, "probes-compile")
        if compile_run.returncode:
            raise SystemExit(f"Probe compilation failed; inspect {output}")
        probes = execute(["vvp", str(binary)], work, output, "probes")

    observations = []
    for line in probes.stdout.splitlines():
        if line.startswith("OBS|"):
            _, name, expected, observed = line.split("|")
            observations.append({"id": name, "expected": expected,
                                 "observed": observed,
                                 "matches": expected == observed})
    expected_ids = {"c_addi_control", "rv32_passthrough", "c_li", "c_addi4spn",
                    "c_addi16sp", "c_ebreak", "false_rs2_stall", "real_load_use"}
    if probes.returncode or {p["id"] for p in observations} != expected_ids:
        raise SystemExit(f"Incomplete probe execution; inspect {output}")
    summary = {
        "schema_version": 1, "timestamp_utc": stamp,
        "commit": lock["commit"], "tool_versions": versions,
        "snapshot_manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "probe_source_sha256": hashlib.sha256(
            (ROOT / "audit/tests/tb_observations.sv").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "historical_regression": {"passed": passed, "failed": failed,
                                  "exit_code": regression.returncode},
        "observations": observations,
        "scope": "Historical smoke tests and targeted unit probes, not ISA certification",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    verify_snapshot()
    # Pin manuscript evidence explicitly in paper/metadata.tex, not silently to latest.
    print(f"Historical regression: {passed} PASS, {failed} FAIL")
    for p in observations:
        print(f"{p['id']}: expected={p['expected']} observed={p['observed']} "
              f"{'MATCH' if p['matches'] else 'DIFFERENCE'}")
    print(f"Evidence: {output.relative_to(ROOT)}/summary.json")
    if regression.returncode or failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
