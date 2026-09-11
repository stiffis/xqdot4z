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


def registrations():
    """The chain in order: the original registration, then each extension.

    A registration file that is not reachable from the chain is refused rather
    than ignored, since an unlinked record is exactly how a second design would
    be slipped in without declaring that it followed the first.
    """
    chain = [OUTPUT]
    sequence = 2
    while (candidate := ROOT / f"docs/PREREGISTRATION_{sequence}.json").exists():
        chain.append(candidate)
        sequence += 1
    stray = sorted(p.name for p in (ROOT / "docs").glob("PREREGISTRATION*.json")
                   if p not in chain)
    require(not stray, f"Registration files outside the chain: {stray}")
    return chain


def already_observed():
    """What had been measured and reported by the time an extension was written.

    Read back from the evidence rather than restated, so an extension cannot
    describe the results it follows as smaller or less conclusive than they were.
    """
    campaign = json.loads((ROOT / "docs/CAMPAIGN_STATE.json").read_text())
    pilot = json.loads((ROOT / "docs/PILOT_STATE.json").read_text())
    for state in (campaign, pilot):
        require(sha(ROOT / state["evidence"]) == state["evidence_sha256"],
                f"{state['evidence']} does not match its pin")
    return dict(
        campaign=dict(run_id=campaign["run_id"], evidence=campaign["evidence"],
                      evidence_sha256=campaign["evidence_sha256"],
                      planned_cases=campaign["planned_cases"],
                      status_counts=campaign["status_counts"]),
        pilot=dict(evidence=pilot["evidence"], evidence_sha256=pilot["evidence_sha256"],
                   cases=pilot["cases"]),
        reported_in=["paper/content_es.tex", "paper/content_en.tex"],
        note="These results were measured, reported and read before this record "
             "was written. What it registers in advance is only the part of the "
             "design they do not cover.")


def design_fingerprint():
    """The parts of the manifest that are design, as opposed to status prose."""
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    design = {key: manifest[key] for key in
              ("grid", "zero_point_profiles", "zero_point_strata", "pairing",
               "reporting", "optimization", "b1_freeze", "common_policy_freeze")}
    design["seed_policy"] = manifest["seed_policy"]
    return hashlib.sha256(json.dumps(design, sort_keys=True).encode()).hexdigest()


def amend(reason):
    """Amend an existing registration instead of overwriting it.

    A registered design may be corrected, but not silently: the original entry
    and every previous amendment are kept, the new hashes are recorded beside
    the old ones, and the amendment must demonstrate that the hypotheses and the
    design fingerprint did not move. An amendment that changed either of those
    would be a new design, not a correction, and is refused here.
    """
    require(OUTPUT.exists(), "There is no registration to amend")
    record = json.loads(OUTPUT.read_text())
    fresh = build()
    require(fresh["charter_hypotheses_sha256"] == record["charter_hypotheses_sha256"],
            "The hypotheses moved: that is a new design, not an amendment")
    baseline = record.get("design_fingerprint")
    current = design_fingerprint()
    if baseline is not None:
        require(current == baseline, "The design moved: amend by registering again, not by editing")
    changed = {path: dict(was=digest, now=fresh["pinned_states"][path])
               for path, digest in record["pinned_states"].items()
               if fresh["pinned_states"][path] != digest}
    require(changed, "Nothing changed; there is nothing to amend")
    record.setdefault("amendments", []).append(dict(
        amended_on=fresh["recorded_on"], parent_git_revision=fresh["parent_git_revision"],
        reason=reason, changed_states=changed,
        hypotheses_unchanged=True, design_unchanged=True))
    record["pinned_states"] = fresh["pinned_states"]
    record["design_fingerprint"] = current
    record["observed_development_timings"] = fresh["observed_development_timings"]
    return record


def extend(reason):
    """Register a design that moved, without touching the registration it follows.

    An amendment proves the design stayed put. An extension is the opposite case
    and needs the opposite proof: the fingerprint must have moved, the record it
    follows is pinned by its bytes so it cannot be edited afterwards, and what
    was already measured is declared rather than left implied. A registration
    written after results exist is not blind, and pretending otherwise is the
    failure this path is built to prevent.
    """
    chain = registrations()
    previous = chain[-1]
    prior = json.loads(previous.read_text())
    fresh = build()
    current = design_fingerprint()
    require(current != prior["design_fingerprint"],
            "The design did not move: that is an amendment, not an extension")
    changed = {path: dict(was=digest, now=fresh["pinned_states"][path])
               for path, digest in prior["pinned_states"].items()
               if fresh["pinned_states"].get(path) != digest}
    require(changed, "An extension that moves no pinned state is not one")
    observed = already_observed()
    record = dict(fresh)
    record.update(
        sequence=prior.get("sequence", 1) + 1,
        extends=dict(file=str(previous.relative_to(ROOT)), sha256=sha(previous),
                     design_fingerprint=prior["design_fingerprint"],
                     recorded_on=prior["recorded_on"]),
        design_fingerprint=current,
        reason=reason,
        changed_states=changed,
        already_observed=observed,
        note="This registration is not blind and does not claim to be. It was "
             "written after the results named in already_observed were measured "
             "and reported; what it fixes in advance is only what those results "
             "do not cover.")
    return record, ROOT / f"docs/PREREGISTRATION_{record['sequence']}.json"


def main():
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--extend":
        reason = " ".join(arguments[1:]).strip()
        require(reason, "An extension must say why")
        record, target = extend(reason)
        target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        observed = record["already_observed"]["campaign"]
        print(f"extension {record['sequence']} recorded in {target.relative_to(ROOT)}")
        print(f"extends {record['extends']['file']} pinned at "
              f"{record['extends']['sha256'][:12]}, which stays untouched")
        print(f"{len(record['changed_states'])} pinned states moved and so did the design "
              "fingerprint, which is what makes it an extension and not an amendment")
        print(f"declares {observed['planned_cases']} cases of run {observed['run_id']} "
              "as already observed")
        return 0
    reason = " ".join(arguments).strip()
    if reason:
        record = amend(reason)
        print(f"amended: {len(record['amendments'])} amendment(s); "
              f"{len(record['amendments'][-1]['changed_states'])} pinned states updated")
        print("Hypotheses and design fingerprint unchanged, which is what makes it an amendment.")
    else:
        record = build()
        record["design_fingerprint"] = design_fingerprint()
    OUTPUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    timings = record["observed_development_timings"]
    if reason: return 0
    print(f"registered after {record['parent_git_revision'][:7]}: "
          f"{len(record['pinned_states'])} states pinned, "
          f"{timings['arms']} observed arms, "
          f"{len(record['post_observation_decisions'])} post-observation decisions")
    print("Nothing has been measured; this only fixes where measuring may begin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
