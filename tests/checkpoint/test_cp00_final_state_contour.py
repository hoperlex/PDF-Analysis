#!/usr/bin/env python3
"""The final-state contour, proved able to fail.

Run from the repository root::

    .venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint

**Every check carries a mutation here.** A guard nobody has made fail is a guard nobody
has tested, and that sentence is why CP-00 ran ten acceptance rounds: on the ratified
tree a 324-test suite was green while the checkpoint's own ratification assertion failed
and its state checker reported fourteen findings. So each of the five checks in
``cp00_final_state`` gets, in one place a reviewer can read down:

* a **positive** case -- a synthetic tree the check accepts;
* a **negative** case -- the same tree with one thing wrong, which it must reject;
* the assertion that the finding **names the thing that is wrong**, not merely that
  something was reported. With one shared message, deleting a branch leaves another
  branch catching the same input and every probe still passes.

The fixture is a whole small checkpoint rather than a stub per check. A stub proves the
function it was written for and nothing about the contour; the tree below classifies
terminal-ratified and is green on all five checks at once, so a mutation is a statement
about a checkpoint rather than about a helper.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "cp00_final_state", Path(__file__).resolve().parent / "cp00_final_state.py"
)
contour = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
# Registered before it is executed: ``@dataclass`` resolves a string annotation through
# ``sys.modules[cls.__module__]``, and a module that is not there yet raises during the
# decorator rather than at first use. Loading by location rather than by ``sys.path``
# keeps `tests/contract/test_cp00_final_state.py` able to import the same module without
# either directory having to be a package.
sys.modules[_spec.name] = contour
_spec.loader.exec_module(contour)


# ---------------------------------------------------------------------------
# The fixture: a whole small checkpoint that is green on every check.
# ---------------------------------------------------------------------------

SUBJECT = "a" * 40
TAGGED = "b" * 40
CANDIDATE = "c" * 40
MOVED = "d" * 40
REVIEW = "docs/architecture/CP00_ARCHITECTURE_REVIEW.json"
REGISTRY = "docs/program/CHECKPOINT_REGISTRY.md"
TASK = "docs/program/tasks/W0-INT-01.md"
MANUAL_REPORT = contour.BUNDLE + "manual-report-round-10.md"
AUTOMATED_REPORT = contour.BUNDLE + "automated-summary.txt"

#: The reviewed families of the fixture and their bytes at each revision. Two families
#: of two files: enough for an aggregate to have members, small enough to read.
FAMILY_FILES = {
    "contracts/a.json": b'{"a": 1}',
    "contracts/b.json": b'{"b": 2}',
    "fixtures/c.json": b'{"c": 3}',
    "fixtures/d.json": b'{"d": 4}',
}


def _digest(paths_and_blobs: dict[str, bytes]) -> str:
    """The recipe the checkpoint publishes, over an explicit mapping."""
    running = hashlib.sha256()
    for path in sorted(paths_and_blobs):
        running.update(path.encode("utf-8"))
        running.update(hashlib.sha256(paths_and_blobs[path]).digest())
    return running.hexdigest()


FAMILY_DIGEST = _digest(FAMILY_FILES)
FILE_HASHES = {
    path: hashlib.sha256(blob).hexdigest() for path, blob in FAMILY_FILES.items()
}


def _contract_manifest() -> str:
    return "\n".join(
        [
            "checkpoint: CP-00",
            "tag: v0.0.1-architecture",
            f"artifact_manifest_sha256: {FAMILY_DIGEST}",
            "artifact_count: 4",
            "",
            "families:",
            "  contracts:",
            "    files: 2",
            f"    sha256: {_digest({k: v for k, v in FAMILY_FILES.items() if k.startswith('contracts/')})}",
            f"    a.json: {FILE_HASHES['contracts/a.json']}",
            f"    b.json: {FILE_HASHES['contracts/b.json']}",
            "  fixtures:",
            "    files: 2",
            f"    sha256: {_digest({k: v for k, v in FAMILY_FILES.items() if k.startswith('fixtures/')})}",
            f"    c.json: {FILE_HASHES['fixtures/c.json']}",
            f"    d.json: {FILE_HASHES['fixtures/d.json']}",
            "",
        ]
    )


def _manifest() -> dict:
    return {
        "checkpoint": "CP-00",
        "tag": "v0.0.1-architecture",
        "tag_planned": "v0.0.1-architecture",
        "ratified": True,
        "status": "ratified",
        "artifact_manifest_sha256": FAMILY_DIGEST,
        "artifact_count": 4,
        "tested_candidate_digest": "t" * 64,
        "evidence_bundle_digest": "e" * 64,
        "current_round": 10,
        "acceptance_rounds": [
            {"round": 9, "verdict": None, "status": "void"},
            {
                "round": 10,
                "verdict": "PASS",
                "status": "accepted",
                "tested_candidate_digest": "t" * 64,
                "evidence_bundle_digest": "e" * 64,
                "manual_report": MANUAL_REPORT,
                "automated_report": AUTOMATED_REPORT,
            },
        ],
        "ratification": {"task": "W0-INT-01", "decided_on": "2026-09-07"},
        "checkpoint_deliverables": [
            contour.CONTRACT_MANIFEST,
            contour.BUILD_INFO,
            MANUAL_REPORT,
            AUTOMATED_REPORT,
        ],
    }


def _tree() -> tuple[contour.MappingTree, contour.TagFacts]:
    """A tree that is green on all five checks, with two other revisions to reach."""
    files: dict[str, str | bytes] = {
        path: blob for path, blob in FAMILY_FILES.items()
    }
    files[contour.MANIFEST] = json.dumps(_manifest(), indent=1)
    files[contour.CONTRACT_MANIFEST] = _contract_manifest()
    files[contour.BUILD_INFO] = json.dumps(
        {"checkpoint": "CP-00", "artifact_manifest_sha256": FAMILY_DIGEST}
    )
    # The two primary reports claim the size of the tree they name. The number is
    # derived from that tree rather than written down twice, so the fixture cannot go
    # stale against itself when a file is added to it.
    SUBJECT_PATHS = sorted({*files, MANUAL_REPORT, AUTOMATED_REPORT})
    files[MANUAL_REPORT] = (
        "# CP-00 manual acceptance - round 10\n"
        "\n"
        "```text\n"
        f"candidate_commit:  {SUBJECT}\n"
        "```\n"
        "\n"
        f"Recomputed over the {len(SUBJECT_PATHS)} tracked paths of the freeze "
        "commit's own objects.\n"
    )
    files[AUTOMATED_REPORT] = (
        "CP-00 automated acceptance summary - round 10\n"
        "\n"
        f"Candidate frozen at {SUBJECT}.\n"
        "\n"
        f"tree swept: the working tree, {len(SUBJECT_PATHS)} tracked paths\n"
    )
    files[REGISTRY] = (
        "# Checkpoint registry\n"
        "\n"
        "| CP | Tag | Status |\n"
        "|---|---|---|\n"
        "| CP-00 | `v0.0.1-architecture` | **ratified** on acceptance round ten |\n"
        "| CP-01 | `v0.1.0-foundation` | planned |\n"
    )
    files[REVIEW] = json.dumps({"ratified": True, "review_status": "ratified"})
    files[TASK] = (
        "# W0-INT-01\n"
        "\n"
        "- Command: `python -c \"import json; from pathlib import Path; "
        f"r=json.loads(Path('{REVIEW}').read_text()); assert r['ratified'] is True; "
        "assert r['review_status']=='ratified'\"`.\n"
    )

    subject_revision: dict[str, str | bytes] = {
        path: files[path] for path in SUBJECT_PATHS
    }
    assert sorted(subject_revision) == SUBJECT_PATHS

    revisions = {
        SUBJECT: subject_revision,
        TAGGED: dict(files),
        CANDIDATE: dict(files),
    }
    tag = contour.TagFacts(
        name="v0.0.1-architecture",
        exists=True,
        annotated=True,
        commit=TAGGED,
        message=(
            "CP-00 - architecture and behaviour freeze\n"
            "\n"
            f"Semantic freeze: artifact_manifest_sha256 {FAMILY_DIGEST} over 4 files, "
            f"byte identical to reviewed_candidate_commit {CANDIDATE}.\n"
        ),
    )
    return contour.MappingTree(files, revisions), tag


class _ContourCase(unittest.TestCase):
    """Shared fixture handling. Each mutation edits a copy; nothing here writes."""

    def setUp(self) -> None:
        self.tree, self.tag = _tree()

    # -- helpers -----------------------------------------------------------
    def files(self) -> dict:
        return dict(self.tree._files)

    def revisions(self) -> dict:
        return {k: dict(v) for k, v in self.tree._revisions.items()}

    def mutate(self, **replacements) -> contour.MappingTree:
        files = self.files()
        files.update(replacements)
        return contour.MappingTree(files, self.revisions())

    def mutate_manifest(self, edit) -> contour.MappingTree:
        manifest = copy.deepcopy(_manifest())
        edit(manifest)
        return self.mutate(**{contour.MANIFEST: json.dumps(manifest, indent=1)})

    def assert_fires(self, verdict_or_findings, check: str, needle: str) -> None:
        findings = (
            verdict_or_findings.findings
            if isinstance(verdict_or_findings, contour.Verdict)
            else verdict_or_findings
        )
        matching = [f for f in findings if f.check == check and needle in f.message]
        self.assertTrue(
            matching,
            f"nothing in {check} said {needle!r}; findings were "
            + "; ".join(str(f) for f in findings),
        )

    def assert_silent(self, findings, check: str) -> None:
        found = [f for f in findings if f.check == check]
        self.assertEqual(found, [], f"{check} fired on a tree it should accept")


class FixtureTests(_ContourCase):
    """Before any mutation: the fixture is green, and it is not green by being empty."""

    def test_the_fixture_is_a_terminal_ratified_checkpoint_with_no_findings(self) -> None:
        verdict = contour.run(self.tree, self.tag)
        self.assertEqual(verdict.state, contour.TERMINAL_RATIFIED)
        self.assertEqual(
            [str(f) for f in verdict.findings],
            [],
            "the fixture must be green before a mutation means anything",
        )

    def test_the_fixture_is_not_green_by_being_empty(self) -> None:
        """Anti-vacuity for the fixture itself, not only for the checks.

        A tree with no records passes every check that iterates over records. These
        counts are what make the mutations below statements about a checkpoint.
        """
        live, historical = contour.classify_records(self.tree)
        self.assertGreaterEqual(len(live), 6, "the fixture has live records to judge")
        self.assertEqual(
            sorted(historical),
            [(AUTOMATED_REPORT, SUBJECT), (MANUAL_REPORT, SUBJECT)],
            "both primary reports are historical by their own declared subject",
        )
        _, verified = contour.live_vs_historical_report(self.tree)
        self.assertEqual(
            verified, 2, "both historical claims are re-derived at the commit they name"
        )
        self.assertEqual(len(contour.checkpoint_status_cells(self.tree)), 1)
        self.assertEqual(len(contour.gate_assertions(self.tree)), 2)
        self.assertEqual(contour.reviewed_families(self.tree), ("contracts", "fixtures"))

    def test_the_verdict_is_the_same_on_a_second_run(self) -> None:
        """Idempotency, required by the task's failure cases."""
        first = contour.run(self.tree, self.tag)
        second = contour.run(self.tree, self.tag)
        self.assertEqual(first.state, second.state)
        self.assertEqual(
            [str(f) for f in first.findings], [str(f) for f in second.findings]
        )

    def test_every_named_check_is_reachable_from_run(self) -> None:
        """A check nothing calls is a check that cannot fail.

        One tree, broken in five ways at once, and every named check must be heard from.
        Asserting the checks exist as constants would prove nothing: the defect this
        contour replaces was a suite of 324 tests that ran and saw nothing.
        """
        manifest = copy.deepcopy(_manifest())
        manifest["acceptance_rounds"].append(
            {"round": 11, "verdict": None, "status": "owed"}
        )
        manifest["checkpoint_deliverables"].append("artifacts/checkpoints/CP-00/gone.md")
        files = self.files()
        files[contour.MANIFEST] = json.dumps(manifest)
        files[AUTOMATED_REPORT] = files[AUTOMATED_REPORT].replace(
            "tracked paths", "hundred tracked paths"
        ).replace("Candidate frozen at", "tree swept: 9999 tracked paths\nCandidate frozen at")
        files[REVIEW] = json.dumps({"ratified": True, "review_status": "elsewhere"})
        files[contour.CONTRACT_MANIFEST] = "\n".join(
            line
            for line in str(files[contour.CONTRACT_MANIFEST]).splitlines()
            if not re.match(r"^    [abcd]\.json:", line)
        )
        tag = contour.TagFacts(
            name="v0.0.1-architecture", exists=True, annotated=False, commit=TAGGED,
            message=self.tag.message,
        )
        heard = {f.check for f in contour.run(contour.MappingTree(files, self.revisions()), tag).findings}
        self.assertEqual(sorted(heard), sorted(contour.CHECKS))

    def test_a_tree_with_no_manifest_classifies_nothing_and_says_so(self) -> None:
        broken = contour.MappingTree({}, {})
        verdict = contour.run(broken, self.tag)
        self.assertEqual(verdict.state, contour.UNCLASSIFIED)
        self.assertTrue(verdict.findings, "a tree with no manifest passed silently")


class TerminalStateTests(_ContourCase):
    """Exactly one of three states, and the terminal one keeps its obligations."""

    def test_the_three_states_are_derived_and_exactly_one_holds(self) -> None:
        state, reasons = contour.classify(_manifest())
        self.assertEqual((state, reasons), (contour.TERMINAL_RATIFIED, []))

        opened = copy.deepcopy(_manifest())
        opened["acceptance_rounds"][1].update(verdict=None, status="owed")
        opened.update(ratified=False, status="open")
        opened.pop("ratification")
        self.assertEqual(contour.classify(opened)[0], contour.OPEN_ROUND)

        closed = copy.deepcopy(_manifest())
        closed.update(ratified=False, status="accepted")
        closed.pop("ratification")
        self.assertEqual(contour.classify(closed)[0], contour.CLOSED_ACCEPTED_ROUND)

        self.assertEqual(
            sorted({contour.OPEN_ROUND, contour.CLOSED_ACCEPTED_ROUND, contour.TERMINAL_RATIFIED}),
            sorted(contour.STATES),
        )

    def test_MUTATION_a_ratified_manifest_whose_round_is_still_open_classifies_nothing(
        self,
    ) -> None:
        """The state the previous checker could not express, in reverse.

        ``ratified: true`` over a round that is still owed satisfies neither
        terminal-ratified nor open-round. That is not one state, so it is a finding --
        and it is the exact shape a re-tag would leave if it moved the flag and not the
        round.
        """
        tree = self.mutate_manifest(
            lambda m: m["acceptance_rounds"][1].update(verdict=None, status="owed")
        )
        verdict = contour.run(tree, self.tag)
        self.assertEqual(verdict.state, contour.UNCLASSIFIED)
        self.assert_fires(verdict, contour.CHECK_TERMINAL, "exactly one must be true")

    def test_MUTATION_a_later_round_leaves_current_round_behind(self) -> None:
        """**The staleness a terminal state must still catch.**

        Round eleven is opened and ``current_round`` is not moved. Nothing is owed by the
        old model's reckoning, so a sweep that asks "which round is owed" says nothing;
        this says the accepted round is no longer the last one.
        """
        tree = self.mutate_manifest(
            lambda m: m["acceptance_rounds"].append(
                {"round": 11, "verdict": None, "status": "owed"}
            )
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_TERMINAL,
            "acceptance_rounds reaches round 11",
        )

    def test_MUTATION_a_status_row_left_on_the_previous_round(self) -> None:
        """The registry keeps its old round number after a new one is accepted."""
        tree = self.mutate(
            **{
                REGISTRY: self.files()[REGISTRY].replace(
                    "round ten", "round nine"
                )
            }
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_TERMINAL,
            "names acceptance round 9",
        )

    def test_MUTATION_a_status_row_still_calling_the_checkpoint_blocked(self) -> None:
        tree = self.mutate(
            **{
                REGISTRY: self.files()[REGISTRY].replace(
                    "**ratified** on acceptance round ten", "blocked; round ten owed"
                )
            }
        )
        self.assert_fires(
            contour.run(tree, self.tag), contour.CHECK_TERMINAL, "status cell states"
        )

    def test_MUTATION_the_accepted_rounds_two_streams_judged_different_trees(self) -> None:
        tree = self.mutate(
            **{
                AUTOMATED_REPORT: self.files()[AUTOMATED_REPORT].replace(
                    SUBJECT, "d" * 40
                )
            }
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_TERMINAL,
            "declare different subject commits",
        )

    def test_MUTATION_the_published_digest_is_not_the_accepted_rounds(self) -> None:
        tree = self.mutate_manifest(
            lambda m: m.update(tested_candidate_digest="f" * 64)
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_TERMINAL,
            "top-level tested_candidate_digest",
        )

    def test_MUTATION_no_live_record_corroborates_the_terminal_state(self) -> None:
        """Deleting the registry must not be a way to pass the status check."""
        files = self.files()
        files.pop(REGISTRY)
        tree = contour.MappingTree(files, self.revisions())
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_TERMINAL,
            "corroborated by nothing",
        )

    def test_a_status_table_without_a_status_column_is_not_a_status_claim(self) -> None:
        """The negative case for the column rule, measured on the real tree.

        ``README.md`` carries a CP-00 row in a roadmap table whose third column is the
        checkpoint's *main result*. Reading that as a status claim reported a summary of
        what CP-00 freezes as a stale state record; requiring a status column is what
        makes the row an attribution rather than a coincidence.
        """
        roadmap = (
            "| Checkpoint | Tag | Main result |\n"
            "|---|---|---|\n"
            "| CP-00 | `v0.0.1-architecture` | contracts frozen enough to code |\n"
        )
        tree = self.mutate(**{"README.md": roadmap})
        self.assert_silent(contour.run(tree, self.tag).findings, contour.CHECK_TERMINAL)
        self.assertEqual(len(contour.checkpoint_status_cells(tree)), 1)


class LiveVersusHistoricalTests(_ContourCase):
    """The distinction is a declaration rule, and the exemption is an obligation."""

    def test_the_rule_is_structural_and_not_a_path_list(self) -> None:
        self.assertIsNone(contour.subject_commit(self.tree, contour.CONTRACT_MANIFEST))
        self.assertEqual(contour.subject_commit(self.tree, MANUAL_REPORT), SUBJECT)
        self.assertEqual(contour.subject_commit(self.tree, AUTOMATED_REPORT), SUBJECT)
        # Both sources are read and neither is a path: the header declaration, and the
        # manifest's binding of a report path to a round and that round to a commit.
        self.assertEqual(contour.declared_subject(self.tree, MANUAL_REPORT), SUBJECT)
        self.assertEqual(contour.bound_subject(self.tree, MANUAL_REPORT), "round-10")

    def test_MUTATION_a_historical_claim_that_is_false_of_its_own_tree(self) -> None:
        """**The exemption is paid for.** The dated report is not skipped: its claim is
        re-derived at the commit it names, and a wrong count is reported there."""
        before = str(self.files()[AUTOMATED_REPORT])
        after = re.sub(r"\d+ tracked paths", "221 tracked paths", before)
        self.assertNotEqual(before, after, "the claim this mutation edits is not there")
        tree = self.mutate(**{AUTOMATED_REPORT: after})
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_LIVE,
            "claims 221 tracked paths of its own subject commit",
        )

    def test_MUTATION_a_dated_report_that_declares_no_subject_is_read_as_live(self) -> None:
        """The failure mode a path skip list hides: an undated report goes unjudged.

        Stripping the declaration makes the record live, so the round's own binding is
        gone and the terminal-state check says the accepted result is bound to nothing.
        """
        stripped = self.files()[MANUAL_REPORT].replace(f"candidate_commit:  {SUBJECT}", "")
        tree = self.mutate(**{MANUAL_REPORT: stripped})
        verdict = contour.run(tree, self.tag)
        # The record itself now declares nothing. The manifest still binds it to round
        # 10, and that binding is deliberately *not* accepted as the report's own
        # statement: conflating the two let a stripped header be excused by the round it
        # belongs to, and the accepted result of a checkpoint has to be legible from the
        # report a reader is handed.
        self.assertIsNone(contour.declared_subject(tree, MANUAL_REPORT))
        self.assertEqual(contour.bound_subject(tree, MANUAL_REPORT), "round-10")
        self.assert_fires(verdict, contour.CHECK_TERMINAL, "declares no subject commit")

    def test_MUTATION_a_subject_commit_this_tree_cannot_resolve(self) -> None:
        tree = contour.MappingTree(self.files(), {TAGGED: self.revisions()[TAGGED],
                                                  CANDIDATE: self.revisions()[CANDIDATE]})
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_LIVE,
            "which this tree cannot resolve",
        )

    def test_MUTATION_the_classifier_going_degenerate_is_itself_a_finding(self) -> None:
        """Every record historical, so every live obligation is vacuous."""
        files = {
            path: f"candidate_commit: {SUBJECT}\n" + str(self.files()[path])
            for path in (contour.CONTRACT_MANIFEST,)
        }
        tree = contour.MappingTree(
            {**files, MANUAL_REPORT: self.files()[MANUAL_REPORT]}, self.revisions()
        )
        findings = contour.live_vs_historical_problems(tree)
        self.assert_fires(findings, contour.CHECK_LIVE, "no record is live")

    def test_MUTATION_an_empty_historical_class_is_itself_a_finding(self) -> None:
        files = self.files()
        files[MANUAL_REPORT] = "# a report that declares nothing\n"
        files[AUTOMATED_REPORT] = "a summary that declares nothing\n"
        manifest = copy.deepcopy(_manifest())
        for entry in manifest["acceptance_rounds"]:
            entry.pop("manual_report", None)
            entry.pop("automated_report", None)
        files[contour.MANIFEST] = json.dumps(manifest)
        tree = contour.MappingTree(files, self.revisions())
        self.assert_fires(
            contour.live_vs_historical_problems(tree),
            contour.CHECK_LIVE,
            "the historical class is empty",
        )


class TagIntegrityTests(_ContourCase):
    """The tag exists, is annotated, has not moved, and its message is true of it."""

    def test_MUTATION_the_tag_has_moved(self) -> None:
        """A tag pointing at a tree whose reviewed families are not the published ones.

        This is the check that stands in for a recorded target commit, which a
        checkpoint cannot have: the tag sits on the commit that carries the manifest and
        a commit cannot name its own hash.
        """
        moved = dict(self.revisions())
        moved[MOVED] = {
            **{p: b for p, b in FAMILY_FILES.items()},
            "contracts/a.json": b'{"a": 999}',
        }
        tree = contour.MappingTree(self.files(), moved)
        tag = contour.TagFacts(
            name=self.tag.name, exists=True, annotated=True, commit=MOVED,
            message=self.tag.message,
        )
        self.assert_fires(
            contour.run(tree, tag), contour.CHECK_TAG, "either the tag has moved"
        )

    def test_MUTATION_the_tag_message_states_a_digest_that_is_not_its_own(self) -> None:
        tag = contour.TagFacts(
            name=self.tag.name, exists=True, annotated=True, commit=TAGGED,
            message=self.tag.message.replace(FAMILY_DIGEST, "9" * 64),
        )
        self.assert_fires(
            contour.run(self.tree, tag),
            contour.CHECK_TAG,
            "the tag message states artifact_manifest_sha256",
        )

    def test_MUTATION_the_tag_message_claims_a_byte_identity_it_does_not_have(self) -> None:
        revisions = self.revisions()
        revisions[CANDIDATE]["contracts/a.json"] = b'{"a": 42}'
        tree = contour.MappingTree(self.files(), revisions)
        self.assert_fires(
            contour.run(tree, self.tag), contour.CHECK_TAG, "byte identical to"
        )

    def test_MUTATION_a_lightweight_tag_is_not_a_checkpoint_tag(self) -> None:
        tag = contour.TagFacts(
            name=self.tag.name, exists=True, annotated=False, commit=TAGGED, message=""
        )
        self.assert_fires(
            contour.run(self.tree, tag), contour.CHECK_TAG, "not an annotated tag object"
        )

    def test_MUTATION_a_record_naming_a_different_tag(self) -> None:
        tree = self.mutate_manifest(lambda m: m.update(tag="v9.9.9-other"))
        self.assert_fires(
            contour.run(tree, self.tag), contour.CHECK_TAG, "more than one tag"
        )

    def test_MUTATION_the_tag_the_records_name_does_not_exist(self) -> None:
        tag = contour.TagFacts(name="v0.0.1-architecture", exists=False)
        self.assert_fires(
            contour.run(self.tree, tag), contour.CHECK_TAG, "does not exist"
        )


class AccountingTests(_ContourCase):
    """Every claimed file, every member of every aggregate, one value per field."""

    def test_MUTATION_a_claimed_file_that_is_not_there(self) -> None:
        tree = self.mutate_manifest(
            lambda m: m["checkpoint_deliverables"].append(
                "artifacts/checkpoints/CP-00/restore-or-rollback-note.md"
            )
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_ACCOUNTING,
            "which this tree does not track",
        )

    def test_MUTATION_a_claimed_test_module_that_is_not_there(self) -> None:
        """The prose half, narrowed to executable test artifacts on purpose.

        A checkpoint that names a test module as part of its blocking contour must have
        it. This is the shape CP-00 actually shipped: `checkpoint-report.md` describes a
        split into `tests/checkpoint/test_cp00_mechanism.py` and
        `tests/contract/test_cp00_contracts.py`, and neither exists at the tag.
        """
        report = contour.BUNDLE + "checkpoint-report.md"
        tree = self.mutate_manifest(
            lambda m: m["checkpoint_deliverables"].append(report)
        )
        tree = contour.MappingTree(
            {
                **dict(tree._files),
                report: "The blocking contour is `tests/checkpoint/test_absent.py`.\n",
            },
            self.revisions(),
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_ACCOUNTING,
            "tests/checkpoint/test_absent.py",
        )

    def test_MUTATION_one_field_two_values_across_two_live_records(self) -> None:
        """The shape CP-00 shipped: `artifact_manifest_sha256` pre- and post-
        ratification, one recipe over two trees, with neither record saying which."""
        tree = self.mutate(
            **{
                contour.BUILD_INFO: json.dumps(
                    {"checkpoint": "CP-00", "artifact_manifest_sha256": "5" * 64}
                )
            }
        )
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_ACCOUNTING,
            "give this top-level field different values",
        )

    def test_MUTATION_an_aggregate_whose_members_are_unlisted(self) -> None:
        stripped = "\n".join(
            line
            for line in self.files()[contour.CONTRACT_MANIFEST].splitlines()
            if not re.match(r"^    [abcd]\.json:", line)
        )
        tree = self.mutate(**{contour.CONTRACT_MANIFEST: stripped + "\n"})
        verdict = contour.run(tree, self.tag)
        self.assert_fires(
            verdict, contour.CHECK_ACCOUNTING, "lists 0 member hashes"
        )
        self.assert_fires(
            verdict, contour.CHECK_ACCOUNTING, "lists 0 per-file hashes"
        )

    def test_MUTATION_an_aggregate_over_an_unstated_number_of_files(self) -> None:
        stripped = self.files()[contour.CONTRACT_MANIFEST].replace(
            "    files: 2\n", "", 1
        )
        tree = self.mutate(**{contour.CONTRACT_MANIFEST: stripped})
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_ACCOUNTING,
            "over an unstated number of files",
        )

    def test_a_fully_enumerated_nested_record_is_accepted(self) -> None:
        """The negative case for the depth fix.

        The family blocks are nested, so a one-level count read a fully enumerated
        manifest as enumerating nothing. This is the case that would have gone red.
        """
        self.assert_silent(
            contour.accounting_problems(self.tree), contour.CHECK_ACCOUNTING
        )


class CrossGateTests(_ContourCase):
    """Test the agreement, not the value."""

    def test_the_gates_are_discovered_and_not_hardcoded(self) -> None:
        found = contour.gate_assertions(self.tree)
        self.assertEqual(
            sorted((task, key, op, expected) for task, _, key, op, expected in found),
            [
                (TASK, "ratified", "is", True),
                (TASK, "review_status", "==", "ratified"),
            ],
        )

    def test_MUTATION_the_two_gates_disagree(self) -> None:
        """Either side may move and the contour fails the same way, which is what
        "test the agreement, not the value" means."""
        review_moved = self.mutate(
            **{REVIEW: json.dumps({"ratified": True, "review_status": "ratified_at_w0_3"})}
        )
        self.assert_fires(
            contour.run(review_moved, self.tag),
            contour.CHECK_GATES,
            "two gates of one checkpoint disagree on 'review_status'",
        )

        task_moved = self.mutate(
            **{TASK: self.files()[TASK].replace("=='ratified'", "=='ratified_at_w0_3'")}
        )
        self.assert_fires(
            contour.run(task_moved, self.tag),
            contour.CHECK_GATES,
            "two gates of one checkpoint disagree on 'review_status'",
        )

    def test_MUTATION_a_field_a_gate_requires_and_the_document_lacks(self) -> None:
        tree = self.mutate(**{REVIEW: json.dumps({"ratified": True})})
        self.assert_fires(
            contour.run(tree, self.tag),
            contour.CHECK_GATES,
            "and the document does not carry it",
        )

    def test_MUTATION_no_gate_at_all_is_a_finding_not_a_pass(self) -> None:
        files = self.files()
        files.pop(TASK)
        tree = contour.MappingTree(files, self.revisions())
        self.assert_fires(
            contour.cross_gate_problems(tree),
            contour.CHECK_GATES,
            "the cross-gate check is vacuous",
        )


class SpawnChokepointTests(unittest.TestCase):
    """Every Git subprocess in the contour goes through one door, with a built
    environment. ``E-06`` is the measured reason; a convention is not a structure."""

    @staticmethod
    def _source() -> str:
        return (Path(__file__).resolve().parent / "cp00_final_state.py").read_text(
            encoding="utf-8"
        )

    def test_the_scan_is_reading_the_real_source(self) -> None:
        source = self._source()
        self.assertIn("def _allowlisted_env(", source)
        self.assertIn("def _git(", source)

    #: Every way a process can be started that this deliverable must not use directly.
    SPAWN_APIS = (
        "subprocess.run", "subprocess.Popen", "subprocess.call",
        "subprocess.check_call", "subprocess.check_output", "subprocess.getoutput",
        "os.system", "os.popen", "os.spawnv", "os.execv",
    )

    @staticmethod
    def _spawn_sites(source: str) -> list[int]:
        """The line of every direct process spawn in ``source``."""
        import ast

        sites = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            name = (
                f"{getattr(target.value, 'id', '?')}.{target.attr}"
                if isinstance(target, ast.Attribute)
                else getattr(target, "id", None)
            )
            if name in SpawnChokepointTests.SPAWN_APIS:
                sites.append(node.lineno)
        return sorted(sites)

    @staticmethod
    def _chokepoint_lines(source: str) -> range:
        """The line range of ``_git``'s body: the one place a spawn is permitted.

        Found by name in the AST rather than as an offset from the function's first
        line. An offset is a second thing to keep in step with the file, and a docstring
        edit would silently move the permitted site onto whatever followed it.
        """
        import ast

        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef) and node.name == "_git":
                return range(node.lineno, (node.end_lineno or node.lineno) + 1)
        return range(0)

    def test_the_only_spawn_site_is_the_chokepoint(self) -> None:
        source = self._source()
        permitted = self._chokepoint_lines(source)
        self.assertGreater(len(permitted), 1, "_git was not found in the contour")
        sites = self._spawn_sites(source)
        self.assertEqual(len(sites), 1, f"more than one spawn site: {sites}")
        self.assertIn(
            sites[0],
            permitted,
            "the contour spawns a process somewhere other than inside _git",
        )

    def test_no_module_of_this_deliverable_spawns_git_directly(self) -> None:
        """**The guard covers the test modules too, not only the module under test.**

        An independent reviewer found this one: the scan read `cp00_final_state.py` and
        nothing else, so the two test modules of the same deliverable sat outside their
        own guard — and one of them spawned an unqualified `git` with the inherited
        environment, which is precisely what `E-06` describes. Read-only commands, so the
        severity was low; the shape is the defect this checkpoint keeps re-learning, that
        a scan scoped to one file is a convention with a spot-check rather than a
        structure. Every Python file this task delivers is scanned now, and a third one
        added tomorrow is scanned the day it is written.
        """
        delivered = sorted(
            [Path(__file__).resolve().parent / "cp00_final_state.py"]
            + list(Path(__file__).resolve().parent.glob("test_*.py"))
            + [REPOSITORY_ROOT / "tests" / "contract" / "test_cp00_final_state.py"]
        )
        self.assertGreaterEqual(
            len(delivered), 3, "the scan found fewer files than this task delivers"
        )
        offenders = {}
        for path in delivered:
            source = path.read_text(encoding="utf-8")
            permitted = (
                self._chokepoint_lines(source)
                if path.name == "cp00_final_state.py"
                else range(0)
            )
            sites = [
                line for line in self._spawn_sites(source) if line not in permitted
            ]
            if sites:
                offenders[path.name] = sites
        self.assertEqual(
            offenders,
            {},
            "a module of this deliverable spawns a process outside contour._git; route "
            "it through the chokepoint so it gets a built environment and a qualified "
            "program path",
        )

    def test_the_scan_would_notice_a_direct_spawn(self) -> None:
        """Anti-vacuity: the scan is not simply blind to the pattern it looks for."""
        planted = "import subprocess\nsubprocess.run(['git', 'status'])\n"
        self.assertEqual(self._spawn_sites(planted), [2])
        self.assertEqual(self._spawn_sites("x = 1\n"), [])

    def test_the_environment_is_built_and_never_inherited(self) -> None:
        env = contour._allowlisted_env()
        self.assertEqual(sorted(env), sorted(contour.ENV_ALLOWLIST))
        self.assertEqual(env["PATH"], contour.TRUSTED_PATH)
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GIT_CONFIG_PARAMETERS", env)
        import ast

        # The property is that no *executable* line reads the inherited environment.
        # Two comments in that module say so in prose, which a substring scan over the
        # file cannot tell from a read; the AST can.
        reads = [
            node.lineno
            for node in ast.walk(ast.parse(self._source()))
            if isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and getattr(node.value, "id", None) == "os"
        ]
        self.assertEqual(reads, [], f"the environment is inherited at lines {reads}")

    def test_the_contour_runs_no_command_that_moves_a_ref(self) -> None:
        """It reads the repository and nothing else. Refs, index and working tree are
        untouched, which is what lets it run on a candidate the reader does not own."""
        source = self._source()
        for forbidden in (
            '"tag"', '"commit"', '"push"', '"add"', '"checkout"', '"reset"',
            '"update-ref"', '"merge"', '"rebase"', '"clean"', '"stash"',
        ):
            with self.subTest(command=forbidden):
                self.assertNotIn(f"_git({forbidden}", source)
                self.assertNotIn(f'_git("-C", str(root), {forbidden}', source)


class RealRepositoryTests(unittest.TestCase):
    """The contour, on this repository. Reading only, and re-runnable."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tree = contour.RepositoryTree(REPOSITORY_ROOT)
        cls.tag = contour.TagFacts.gather(REPOSITORY_ROOT, "v0.0.0-architecture")

    def test_the_tree_view_reads_this_repository(self) -> None:
        self.assertIn(contour.MANIFEST, self.tree.paths())
        self.assertGreater(len(self.tree.paths()), 100)
        self.assertIsNotNone(self.tree.read(contour.CONTRACT_MANIFEST))

    def test_the_checkpoint_tag_is_annotated_and_peels_to_a_commit(self) -> None:
        self.assertTrue(self.tag.exists, "the checkpoint tag is missing")
        self.assertTrue(self.tag.annotated, "the checkpoint tag is not annotated")
        self.assertRegex(self.tag.commit or "", r"^[0-9a-f]{40}$")

    @staticmethod
    def _status() -> str:
        """The working tree's status, read through the contour's own chokepoint.

        Through ``contour._git`` and not through a bare ``subprocess.run(["git", ...])``.
        The first version of this method spawned an unqualified ``git`` with the
        inherited environment — read-only commands, but exactly what ``E-06`` describes,
        in the one file of this deliverable that sat outside its own guard. The guard now
        covers this module too; see
        :meth:`SpawnChokepointTests.test_no_module_of_this_deliverable_spawns_git_directly`.
        """
        return contour._git(
            "status", "--porcelain", "-uall", root=REPOSITORY_ROOT
        ).stdout.decode("utf-8", "replace")

    def test_the_contour_leaves_the_repository_untouched(self) -> None:
        """Idempotency and read-only-ness, measured rather than asserted."""
        before = self._status()
        first = contour.run(self.tree, self.tag)
        second = contour.run(self.tree, self.tag)
        after = self._status()
        self.assertEqual(before, after, "the contour changed the working tree")
        self.assertEqual(
            [str(f) for f in first.findings], [str(f) for f in second.findings]
        )

    def test_the_recorded_limitations_are_stated_and_not_empty(self) -> None:
        # Compared with the count the report states, so a limitation deleted from the
        # module and left standing in prose is a failure. A static count that disagrees
        # with what the code holds is the defect this programme keeps writing down.
        self.assertEqual(
            len(contour.LIMITATIONS),
            7,
            "the recorded limitations changed; docs/program/reviews/W0-QA-04.md §7.3 "
            "enumerates them and must be brought with them",
        )
        for limitation in contour.LIMITATIONS:
            self.assertGreater(len(limitation), 60)


if __name__ == "__main__":
    unittest.main()
