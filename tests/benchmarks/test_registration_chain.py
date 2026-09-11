"""The registration chain has to refuse the cases it exists to prevent.

An extension and an amendment are opposite claims about the same event: one says
the design moved, the other says it did not. Each path must reject the other's
case, or the distinction is decoration. These tests drive the refusals directly,
so a mechanism that silently accepted anything would fail here rather than pass
quietly into the record.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import record_preregistration as reg


def registration(sequence=1, fingerprint="aaaa", states=None):
    return dict(sequence=sequence, design_fingerprint=fingerprint,
                recorded_on="2026-09-11",
                pinned_states=states or {p: f"hash-of-{p}" for p in reg.PINNED_STATES})


class ChainDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="chain-")
        self.root = Path(self.temporary.name)
        (self.root / "docs").mkdir()
        self.output = self.root / "docs/PREREGISTRATION.json"
        self.output.write_text(json.dumps(registration()))
        patches = mock.patch.multiple(reg, ROOT=self.root, OUTPUT=self.output)
        patches.start()
        self.addCleanup(patches.stop)
        self.addCleanup(self.temporary.cleanup)

    def write(self, sequence, **fields):
        path = self.root / f"docs/PREREGISTRATION_{sequence}.json"
        path.write_text(json.dumps(registration(sequence=sequence, **fields)))
        return path

    def test_a_lone_registration_is_the_whole_chain(self):
        self.assertEqual(reg.registrations(), [self.output])

    def test_extensions_are_returned_in_order(self):
        second = self.write(2)
        third = self.write(3)
        self.assertEqual(reg.registrations(), [self.output, second, third])

    def test_a_registration_outside_the_chain_is_refused(self):
        """A gap is how a second design would arrive without declaring the first."""
        self.write(3)
        with self.assertRaises(RuntimeError) as refusal:
            reg.registrations()
        self.assertIn("outside the chain", str(refusal.exception))

    def test_an_unnumbered_registration_file_is_refused(self):
        (self.root / "docs/PREREGISTRATION_draft.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            reg.registrations()


class ExtensionRefusalTests(unittest.TestCase):
    """extend() must reject what amend() is for, and vice versa."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="extend-")
        self.root = Path(self.temporary.name)
        (self.root / "docs").mkdir()
        self.output = self.root / "docs/PREREGISTRATION.json"
        self.prior = registration(fingerprint="design-one")
        self.output.write_text(json.dumps(self.prior))
        patches = mock.patch.multiple(reg, ROOT=self.root, OUTPUT=self.output)
        patches.start()
        self.addCleanup(patches.stop)
        self.addCleanup(self.temporary.cleanup)
        self.observed = dict(campaign=dict(run_id="RUN", evidence="e.json",
                                           evidence_sha256="deadbeef",
                                           planned_cases=2280,
                                           status_counts={"pass": 2280}),
                             pilot=dict(evidence="p.json", evidence_sha256="cafe", cases=32))

    def attempt(self, fingerprint, states):
        fresh = dict(recorded_on="2026-09-12", parent_git_revision="f" * 40,
                     pinned_states=states, charter_hypotheses_sha256="h",
                     post_observation_decisions=[], observed_development_timings={},
                     campaign_executed=False, pilot_executed=False, results_reported=False,
                     note="")
        with mock.patch.object(reg, "build", return_value=fresh), \
             mock.patch.object(reg, "design_fingerprint", return_value=fingerprint), \
             mock.patch.object(reg, "already_observed", return_value=self.observed):
            return reg.extend("because the grid grew")

    def test_refused_when_the_design_did_not_move(self):
        moved = dict(self.prior["pinned_states"], **{reg.PINNED_STATES[0]: "moved"})
        with self.assertRaises(RuntimeError) as refusal:
            self.attempt("design-one", moved)
        self.assertIn("amendment, not an extension", str(refusal.exception))

    def test_refused_when_no_pinned_state_moved(self):
        with self.assertRaises(RuntimeError) as refusal:
            self.attempt("design-two", dict(self.prior["pinned_states"]))
        self.assertIn("moves no pinned state", str(refusal.exception))

    def test_accepted_extension_pins_its_predecessor_and_declares_what_it_knew(self):
        moved = dict(self.prior["pinned_states"], **{reg.PINNED_STATES[0]: "moved"})
        record, target = self.attempt("design-two", moved)
        self.assertEqual(record["sequence"], 2)
        self.assertEqual(target.name, "PREREGISTRATION_2.json")
        # The predecessor is pinned by its bytes, so editing it later breaks the link.
        self.assertEqual(record["extends"]["sha256"], reg.sha(self.output))
        self.assertEqual(record["extends"]["design_fingerprint"], "design-one")
        self.assertEqual(record["already_observed"]["campaign"]["planned_cases"], 2280)
        self.assertEqual(list(record["changed_states"]), [reg.PINNED_STATES[0]])
        self.assertFalse(record["results_reported"])

    def test_editing_the_predecessor_breaks_the_recorded_link(self):
        """The whole point of pinning bytes: rewriting history has to show."""
        moved = dict(self.prior["pinned_states"], **{reg.PINNED_STATES[0]: "moved"})
        record, _ = self.attempt("design-two", moved)
        self.output.write_text(json.dumps(dict(self.prior, recorded_on="2026-01-01")))
        self.assertNotEqual(record["extends"]["sha256"], reg.sha(self.output))


if __name__ == "__main__":
    unittest.main()
