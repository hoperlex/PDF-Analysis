#!/usr/bin/env python3
"""CP-00's final state, asserted against this tree.

Run from the repository root::

    .venv/bootstrap/bin/python -m unittest discover -s tests/contract

This module is the **verdict**; ``tests/checkpoint/test_cp00_final_state_contour.py`` is
the proof that the verdict can be wrong. The contour itself lives in
``tests/checkpoint/cp00_final_state.py`` and knows nothing about this repository: it
takes a tree and a tag and returns findings, so the same five checks run here, on a
candidate, or on any historical commit.

**What a reader of a red run should understand.** These assertions are red on the tree
they were written against, and that is the deliverable rather than a defect in it. CP-00
shipped a checkpoint whose own ratification gate fails, whose state checker reports
fourteen findings that are a true description of a ratified checkpoint rather than
defects, and whose 324-test suite passed without noticing either. There was no contour
able to tell a ratified checkpoint from an open round. This is that contour, and on this
tree it says the records do not describe the state they claim.

Every finding here names the task that owns the disposition — all of them ``W0-INT-02``,
none of them ``W0-QA-04``'s to fix, and none of them a value this module chooses. When
``W0-INT-02`` reconciles the bundle, these tests go green **with no edit to this file**:
that is what makes them a gate rather than a ledger of excuses.

**What is deliberately not here.** No expected-failure decoration, no recorded list of
open findings, no skip. A check that is quiet about a contradiction because somebody
wrote the contradiction down is the failure mode this whole checkpoint has spent ten
rounds on, and a self-updating allowance for it would be that failure mode with a test
name attached.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_CONTOUR = REPOSITORY_ROOT / "tests" / "checkpoint" / "cp00_final_state.py"
_spec = importlib.util.spec_from_file_location("cp00_final_state", _CONTOUR)
if _spec is None or _spec.loader is None:  # pragma: no cover - a missing contour
    raise AssertionError(f"the final-state contour is not at {_CONTOUR}")
contour = importlib.util.module_from_spec(_spec)
# Loaded by location rather than by ``sys.path``, so neither test directory has to
# become a package and neither suite can shadow the other's imports. Registered before
# execution because ``@dataclass`` resolves annotations through ``sys.modules``.
sys.modules[_spec.name] = contour
_spec.loader.exec_module(contour)

#: The tag the checkpoint records name. Read from the records rather than written down,
#: for the reason `tests/contract/test_cp00_candidate.py` stopped pinning it to one
#: literal: a superseding checkpoint publishes `v0.0.1-architecture`, and a literal here
#: would make the recovery's own required suite unreachable at the moment it ratifies.
#: There is deliberately **no literal fallback**. A default would be a fourth pin, and it
#: would answer "which tag?" with a guess at the very moment the records stop saying;
#: the empty name resolves to no tag and the contour reports that the records name none,
#: which is the truth and has an owner.
def _tag_name(tree: contour.Tree) -> str:
    return contour.recorded_tag(tree)


class _FinalState(unittest.TestCase):
    """One reading of the tree, shared. The contour writes nothing, so this is safe."""

    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.tree = contour.RepositoryTree(REPOSITORY_ROOT)
        cls.tag = contour.TagFacts.gather(REPOSITORY_ROOT, _tag_name(cls.tree))
        cls.verdict = contour.run(cls.tree, cls.tag)

    def _assert_check_clean(self, check: str, owner_note: str) -> None:
        findings = self.verdict.by_check(check)
        self.assertEqual(
            [f"{f.site}: {f.message}" for f in findings],
            [],
            f"{check} is red on this tree. {owner_note} Re-run the contour directly for "
            f"the full report:\n"
            f"    .venv/bootstrap/bin/python tests/checkpoint/cp00_final_state.py",
        )


class TerminalStateTests(_FinalState):
    """A tree is exactly one of open-round, closed-accepted-round, terminal-ratified."""

    def test_the_tree_classifies_to_exactly_one_terminal_state(self) -> None:
        self.assertIn(
            self.verdict.state,
            contour.STATES,
            "the checkpoint manifest describes no single terminal state; the fields "
            "that decide it are named in the finding",
        )

    def test_the_records_describe_the_state_the_manifest_derives(self) -> None:
        self._assert_check_clean(
            contour.CHECK_TERMINAL,
            "Reconciling the live state records is W0-INT-02's.",
        )

    def test_the_terminal_state_check_is_not_vacuous(self) -> None:
        """It went quiet at publication once. It must not have gone quiet again.

        The old sweep models the record as "which round is owed"; on a ratified tree
        nothing is owed, so it has nothing left to say and every one of its fourteen
        findings is a correct description of a ratified checkpoint. The obligations
        below are what this check still holds in the terminal state, and this asserts
        they had something to read.
        """
        rows = contour.checkpoint_status_cells(self.tree)
        self.assertGreaterEqual(
            len(rows), 1, "no live status row for CP-00 was read, so the row check "
            "passed by having nothing to look at"
        )
        manifest = self.tree.json(contour.MANIFEST)
        self.assertIsInstance(manifest, dict)
        self.assertGreaterEqual(
            len(manifest.get("acceptance_rounds", [])),
            2,
            "the round obligations need a record with rounds in it",
        )


class LiveVersusHistoricalTests(_FinalState):
    """A dated primary report may state a superseded fact; a live record may not."""

    def test_no_live_record_states_a_superseded_fact_and_no_dated_one_is_skipped(
        self,
    ) -> None:
        self._assert_check_clean(
            contour.CHECK_LIVE,
            "The evidence bundle is W0-INT-02's.",
        )

    def test_the_distinction_is_structural_and_pays_for_itself(self) -> None:
        """**The improvement over the sweep this sits beside.**

        That sweep excludes `docs/program/reviews/` and the dated reports *by path*, and
        its own acceptance record calls the exclusion "a narrowing it warned against".
        Here a record is historical because it declares a subject commit in its own
        bytes, or because the manifest binds it to a round — both read out of the tree —
        and its claims are then **re-derived at the commit it names** rather than
        skipped. This asserts that both classes are populated and that the re-derivation
        actually happened, because an exemption nobody pays for is a skip list with a
        better docstring.
        """
        live, historical = contour.classify_records(self.tree)
        self.assertGreater(len(live), 0, "no record is live; every obligation is vacuous")
        self.assertGreater(len(historical), 0, "no record is historical; the rule is untested")
        self.assertNotIn(
            "docs/program/reviews/W0-QA-01.md",
            [path for path, _ in historical],
            "the review report is judged as a live record here; it is not excluded by "
            "path the way the sweep beside this one excludes it",
        )
        _, verified = contour.live_vs_historical_report(self.tree)
        self.assertGreater(
            verified,
            0,
            "no historical claim was re-derived at the commit it names, so the "
            "exemption was granted and never paid for",
        )


class TagIntegrityTests(_FinalState):
    """The tag exists, is annotated, has not moved, and says nothing false."""

    def test_the_contour_read_a_tag_identity_out_of_the_records(self) -> None:
        """Anti-vacuity for the whole check: it must have had a tag to look at.

        What this does **not** do is hard-assert that the tag exists. It did, and that
        was a fourth instance of the pin defect wearing different clothes: the ratifying
        delta flips the records to the successor before that tag is created — the
        manifest is written in the commit that gets tagged, so the records are ahead of
        the refs by construction — and a bare `assertTrue(exists)` here would fail on
        `W0-INT-02`'s own output tree, which no task would then be licensed to leave.
        The verdict on existence, annotation and peeling is carried by
        :meth:`test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit`, where
        it arrives as a finding that names `W0-INT-03` — the task that publishes refs.
        """
        self.assertTrue(
            self.tag.name,
            "no checkpoint record names a tag, so tag-integrity has nothing to verify",
        )
        self.assertRegex(
            self.tag.name,
            r"^v\d+\.\d+\.\d+-[a-z]+$",
            "the tag the records name is not shaped like a checkpoint tag",
        )

    def test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit(self) -> None:
        self._assert_check_clean(
            contour.CHECK_TAG,
            "The tag is never moved. A tag message that is false of its own commit is "
            "corrected by a superseding checkpoint, which is W0-INT-03's act on "
            "W0-INT-02's record; a record naming a tag that does not exist yet is "
            "W0-INT-03's to close by publishing it.",
        )


class FileAndHashAccountingTests(_FinalState):
    """Every claimed file, every aggregate's members, one value per field."""

    def test_every_file_the_checkpoint_claims_exists_and_every_aggregate_is_enumerated(
        self,
    ) -> None:
        self._assert_check_clean(
            contour.CHECK_ACCOUNTING,
            "The manifest, the contract manifest and the evidence bundle are "
            "W0-INT-02's.",
        )


class CrossGateAgreementTests(_FinalState):
    """The two ratification gates of one checkpoint must agree. Neither is chosen here."""

    def test_the_gates_are_discovered_from_the_task_files(self) -> None:
        """Anti-vacuity: a gate check with no gates to read passes by silence."""
        assertions = contour.gate_assertions(self.tree)
        self.assertGreater(
            len(assertions), 0, "no task file states a ratification gate this contour "
            "can read, so the agreement check has nothing to compare"
        )
        self.assertIn(
            contour.ARCHITECTURE_REVIEW,
            {subject for _, subject, _, _, _ in assertions},
            "no discovered gate asserts on the architecture review",
        )

    def test_the_two_ratification_gates_agree(self) -> None:
        self._assert_check_clean(
            contour.CHECK_GATES,
            "W0-QA-04 tests the agreement and does not choose the value: applying the "
            "canonical review_status to docs/architecture/CP00_ARCHITECTURE_REVIEW.json "
            "is W0-INT-02's disposition, and this goes green when it lands.",
        )


class ContourHygieneTests(_FinalState):
    """The contour reads; it does not write, and it says what it cannot see."""

    def test_the_verdict_is_the_same_on_a_second_run(self) -> None:
        again = contour.run(self.tree, self.tag)
        self.assertEqual(again.state, self.verdict.state)
        self.assertEqual(
            [str(f) for f in again.findings], [str(f) for f in self.verdict.findings]
        )

    def test_every_finding_names_an_owner_and_a_known_check(self) -> None:
        for finding in self.verdict.findings:
            with self.subTest(site=finding.site):
                self.assertIn(finding.check, contour.CHECKS)
                self.assertTrue(finding.owner, "a finding with no owner is a complaint")
                self.assertGreater(len(finding.message), 30)

    def test_no_finding_is_this_task_s_own_defect(self) -> None:
        """The acceptance gate for a red run, asserted rather than left to a reader.

        A red check is acceptable here only while every one of its findings is a
        contradiction in records `W0-INT-02` owns. A finding owned by `W0-QA-04` is
        something else entirely: the contour raises those only when one of its own
        classes has gone degenerate — no live record, no historical record, no gate to
        read — and each of those means a check passed by having nothing to look at.
        Such a finding is a defect in this deliverable and must never be shipped red.
        """
        mine = [str(f) for f in self.verdict.findings if f.owner == "W0-QA-04"]
        self.assertEqual(
            mine,
            [],
            "the contour reports a defect in itself: one of its checks has nothing to "
            "read on this tree and is passing vacuously",
        )
        # And every other owner is a task that exists, resolved from the tree rather
        # than compared with a list of task ids here — a list would be one more literal
        # to edit the next time the graph changes.
        unknown = sorted(
            {
                finding.owner
                for finding in self.verdict.findings
                if not (REPOSITORY_ROOT / "docs" / "program" / "tasks"
                        / f"{finding.owner}.md").is_file()
            }
        )
        self.assertEqual(
            unknown, [], "a finding names an owner that is not a task in this programme"
        )

    def test_the_limitations_are_recorded_rather_than_asserted_away(self) -> None:
        self.assertGreaterEqual(len(contour.LIMITATIONS), 5)


if __name__ == "__main__":
    unittest.main()
