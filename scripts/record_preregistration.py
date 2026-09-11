"""Record the revision from which measuring may begin, and what was already seen.

This is the last blocker by construction. Everything the campaign depends on is
frozen by now, so the only thing left is to state the point it is frozen at and,
just as importantly, to write down the counters that were already observed while
building the kernels. A campaign that hid those could later be presented as if
it had been designed blind; this record makes that impossible to claim.

It records observations, not results. No speedup is computed here or anywhere
else in the project.
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/PREREGISTRATION.json"
PINNED_STATES = ["docs/MEASUREMENT_STATE.json", "docs/KERNEL_STATE.json",
                 "docs/INVENTORY_STATE.json", "docs/POLICY_FREEZE.json",
                 "benchmarks/campaign.json", "docs/EXPERIMENT_PROTOCOL.md"]
# Decisions taken after development counters had been seen. Each already carries
# its own reason and declared direction; listing them here keeps the set in one
# place instead of scattered through the log.
POST_OBSERVATION_DECISIONS = ["D33", "D34", "D35", "D36", "D37", "D38", "D39"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition: raise RuntimeError(message)


def hypotheses():
    """Hash the charter's hypotheses so a later edit to them is visible."""
    text = (ROOT / "docs/RESEARCH_CHARTER.md").read_text()
    block = re.search(r"(\*\*H1:\*\*.*?H1–H3 [^\n]*\n)", text, re.S)
    require(block is not None, "Could not locate the hypotheses in the charter")
    return hashlib.sha256(block.group(1).encode()).hexdigest()


def observed_timings():
    """The counters already seen, taken from the pinned kernel evidence itself."""
    state = json.loads((ROOT / "docs/KERNEL_STATE.json").read_text())
    evidence = ROOT / state["evidence"]
    require(sha(evidence) == state["evidence_sha256"], "Kernel evidence does not match its pin")
    report = json.loads(evidence.read_text())
    cycles = {name: case["counters"]["cycles"] for name, case in sorted(report["cases"].items())}
    return dict(source=state["evidence"], source_sha256=state["evidence_sha256"],
                arms=len(cycles), cycles=cycles,
                decomposition=report["zs_decomposition"],
                loop_control={n: e["cycles"] for n, e in sorted(report["loop_control"].items())},
                context="Observed while writing and verifying the kernels, which is "
                        "correctness work and not the campaign: two seeds of ten, four "
                        "settings of nineteen, no pilot and no pre-measurement record at "
                        "the time. Recorded so the campaign cannot later be presented as "
                        "though these numbers had not been seen.",
                speedup_computed=False, hypotheses_changed_after_seeing=False)


def build():
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    for path in PINNED_STATES:
        staged = subprocess.run(["git", "show", f":{path}"], cwd=ROOT,
                                capture_output=True, check=True).stdout
        require(hashlib.sha256(staged).hexdigest() == sha(ROOT / path),
                f"{path} is not staged; git add it before recording the revision")
    return dict(
        recorded_on=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        parent_git_revision=revision,
        pinned_states={p: sha(ROOT / p) for p in PINNED_STATES},
        charter_hypotheses_sha256=hypotheses(),
        post_observation_decisions=POST_OBSERVATION_DECISIONS,
        observed_development_timings=observed_timings(),
        measurement_may_begin_after="this record is committed with the files it pins",
        campaign_executed=False, pilot_executed=False, results_reported=False,
        note="Recording this does not run anything. It fixes the point measurement "
             "may start from, so any later change to a pinned state is a change to "
             "the registered design and must say so.")


def main():
    record = build()
    OUTPUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    timings = record["observed_development_timings"]
    print(f"registered after {record['parent_git_revision'][:7]}: "
          f"{len(record['pinned_states'])} states pinned, "
          f"{timings['arms']} observed arms, "
          f"{len(record['post_observation_decisions'])} post-observation decisions")
    print("Nothing has been measured; this only fixes where measuring may begin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
