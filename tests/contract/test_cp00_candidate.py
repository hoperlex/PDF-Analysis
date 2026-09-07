"""Independent consumer-side verification of the CP-00 candidate (`W0-QA-01`).

This module is written by an agent that authored none of the reviewed artifacts. It
asserts cross-family invariants over repository data, invokes the documented analysis
Gates A-D verbatim, and proves each invariant by mutating exactly the thing it claims
to protect inside a throwaway copy.

Reviewed candidate: `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` (`W0-CLN-01`
integration). Every assertion here is a statement about that tree. The evidence commit
that carries this file is a different, later commit and certifies nothing.

Two rules the module holds itself to:

* Nothing under `contracts/**`, `fixtures/**`, `docs/architecture/**` or `scripts/**`
  is written. Mutations happen in `tempfile.mkdtemp()` copies and are removed again.
* A documented gate is executed as written, through a shell, from the repository root.
  A gate that cannot run as documented is a failing test, not a skipped one.
"""

from __future__ import annotations

import ast
import atexit
from collections import Counter
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys
import unittest
import unittest.mock
from typing import NamedTuple


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

REVIEWED_CANDIDATE_COMMIT = "92e13fa496a723ed6e4c3adbf138c4f4e1d7c368"

BOOTSTRAP_PYTHON = REPOSITORY_ROOT / ".venv/bootstrap/bin/python"

ANALYSIS = "contracts/analysis/v1"
DOMAIN = "contracts/domain/v1"
EVENTS = "contracts/events/v1"
GOLDEN = "fixtures/golden"

ANALYSIS_README = f"{ANALYSIS}/README.md"
DOMAIN_README = f"{DOMAIN}/README.md"
EVENTS_README = f"{EVENTS}/README.md"
LINT_RULES_MD = "docs/architecture/ARCHITECTURE_LINT_RULES.md"
LINT_RULES_JSON = "docs/architecture/ARCHITECTURE_LINT_RULES.json"
SELECTION_MD = f"{GOLDEN}/SELECTION.md"

CANONICAL_VERSION_KEY = "contract_version"
CANDIDATE_CONTRACT_VERSION = "1.0.0-draft.1"

#: Version keys that no machine contract under ``contracts/**`` may declare (`ID-01`,
#: `ALR-24`). The one deliberate exception is the negative fixture whose whole purpose
#: is to carry the rejected key.
FORBIDDEN_VERSION_KEYS = frozenset({"version", "schema_version"})
LEGACY_KEY_FIXTURE = f"{EVENTS}/examples/event-envelope.legacy-schema-version.invalid.json"

#: Attempt-authority field names that `ALR-25` and the domain identifier catalog forbid
#: as *field names*. All three legitimately occur as string values (forbidden-detail-key
#: lists, legacy evidence names), so only object keys are checked.
FORBIDDEN_AUTHORITY_KEYS = frozenset({"authority_token", "fencing_token", "fence_token"})

#: Every reviewed family. Byte identity with the candidate is asserted over all of them,
#: except for the narrow, externally declared ratification delta defined below.
REVIEWED_PREFIXES = ("contracts/", "fixtures/", "docs/architecture/", "scripts/")

#: Three of the four reviewed families are touched by nothing, ever. Ratification does
#: not reach them, so no record can license a byte of change here.
IMMUTABLE_REVIEWED_PREFIXES = ("contracts/", "fixtures/", "scripts/")

#: The one family ratification does reach, and then only inside the declared set.
RATIFIABLE_REVIEWED_PREFIX = "docs/architecture/"

#: The external record. It is outside every reviewed family on purpose: a record that
#: lived inside the tree it authorises could licence its own drift.
CHECKPOINT_MANIFEST = "artifacts/checkpoints/CP-00/manifest.json"
CHECKPOINT_REGISTRY = "docs/program/CHECKPOINT_REGISTRY.md"

#: **The registry's state vocabulary, closed and machine-readable.** The CP-00 row of
#: `CHECKPOINT_REGISTRY.md` states its state by citing, in a code span, the manifest key
#: that holds it. These are identifiers, not English words, so a sentence that negates
#: one cannot be mistaken for one that asserts it — the failure the first form of this
#: check had, where `\bratified\b` matched inside "not ratified" and a row denying
#: ratification read as a row confirming it.
RATIFIED_STATE_TOKEN = "ratification"
UNRATIFIED_STATE_TOKEN = "ratification_blocked"
REGISTRY_STATE_TOKENS = frozenset({RATIFIED_STATE_TOKEN, UNRATIFIED_STATE_TOKEN})

#: Only this task may ratify CP-00. `W0.3_ratification_integration.md` assigns the
#: ratification act, the CP-00 review and the checkpoint evidence to it alone.
RATIFYING_TASK = "W0-INT-01"

#: **The ceiling on any ratification delta, and the reason it cannot be widened
#: silently.** A ratification record names the files it changes, but a record that could
#: name anything would be no control at all — the integrator would only have to add a
#: path to the record it writes itself. So the record may name *fewer* paths than this
#: set and never one outside it. Widening the ceiling means editing this module, which
#: only `W0-QA-01` owns, which means reopening this task and passing another independent
#: review.
#:
#: The five entries are exactly the artifacts CP-00 ratification is recorded as needing:
#: the review document whose `ratified` flag is the ratification act, in both its forms,
#: and the three point-in-time statements listed under `known_pre_ratification_items` in
#: the checkpoint manifest — the `PD-02` precondition text in two documents, the stale
#: `GATE-E` prose in the lint specification, and the owner-decision count in the ADR
#: index. Nothing else in `docs/architecture/**` is reconciled by ratification.
RATIFICATION_DELTA_CEILING = frozenset(
    {
        "docs/architecture/ADR_INDEX.md",
        "docs/architecture/ARCHITECTURE_LINT_RULES.md",
        "docs/architecture/CP00_ARCHITECTURE_REVIEW.json",
        "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
        "docs/architecture/CP00_OWNER_DECISIONS.md",
    }
)

#: The two acceptance digests of the current manifest form. One identifies the immutable
#: input the acceptance streams judged, frozen before they run; the other identifies the
#: tree that carries their results. They are necessarily different, because writing the
#: results changes the tree — which is why the single retired `candidate_digest` was
#: wrong: computed last, it certified a tree the streams never saw.
ACCEPTANCE_DIGEST_FIELDS = ("tested_candidate_digest", "evidence_bundle_digest")

#: Where the acceptance streams' primary reports live. `manual_report`,
#: `automated_report` and both `report_path` values are **data**, so a manifest that
#: could license any path by naming it as a report would license its own drift. A
#: declared report path is honoured by the post-freeze delta only inside this prefix.
ACCEPTANCE_EVIDENCE_PREFIX = "artifacts/checkpoints/CP-00/"

#: **The checkpoint's acceptance record, and why it has to be licensed too.**
#:
#: `acceptance.md` is the narrative record of every acceptance round: what each stream
#: returned, what failed, what carried forward. Its round table can only be written
#: *after* a round reports, which is necessarily after that round's freeze — and it sits
#: inside :func:`_digest_paths` and outside every licence this module granted. So
#: recording a round's verdict voided the round it recorded: the round-nine defect one
#: file over. It has not bitten only because every round since the ceiling existed has
#: failed, and a failed round has nothing left to protect.
#:
#: The sweep script next to it, `check_state_records.py`, is deliberately **not**
#: licensed. It is a tool, not evidence: nothing about ratification requires it to
#: change, and a tool that changes after the freeze changes the tree the acceptance
#: streams judged, which is exactly what voiding a round is for. The distinction is the
#: same one :data:`ACCEPTANCE_EVIDENCE_PREFIX` draws — the round's own reports are
#: licensed, the directory they live in is not.
ACCEPTANCE_RECORD = ACCEPTANCE_EVIDENCE_PREFIX + "acceptance.md"

#: The heading the round table lives under, so the completeness rule below cannot be
#: satisfied by deleting the table it is about.
ACCEPTANCE_RECORD_HEADING = "## Rounds"

#: The tag CP-00 is published under. Pinned here rather than read out of the checkpoint
#: manifest's `tag_planned`, for the reason every ceiling in this module is pinned: the
#: integrator writes that manifest, and a value the integrator can change is not a value
#: a check can hold them to.
#: :meth:`TableExpectationTests.test_the_checkpoint_tag_and_manual_vocabulary_are_pinned`
#: compares it with the manifest, so the two disagreeing is a failure rather than a
#: silent re-tag. (The name is written out because it is checked: an earlier form of
#: this comment cited a method that does not exist, which is the module's own defect
#: shape — prose naming a check nobody can run — in a docstring.)
CHECKPOINT_TAG = "v0.0.0-architecture"

#: The manual runbook. Read-only for every task in this wave, which is what makes the
#: case list an **anchor** rather than a pin: the manual report's required verdicts are
#: enumerated out of this document by :func:`_manual_case_ids`, not written down here.
MANUAL_RUNBOOK = "docs/manual-tests/CP-00_architecture.md"

#: The verdict vocabulary a manual case may carry. `W0-INT-01` deliverable 3 names all
#: three; only `PASS` may stand on a ratified checkpoint, because the same deliverable
#: says any failure or unexplained block stops the task.
MANUAL_VERDICTS = ("PASS", "FAIL", "BLOCKED")

#: **The eight-file evidence bundle, and what each file has to say once it exists.**
#:
#: `W0-INT-01` deliverable 1 requires eight files under
#: :data:`ACCEPTANCE_EVIDENCE_PREFIX`. **None of them exists**, at the reviewed
#: candidate or today, and until this round nothing licensed them either:
#: :func:`_declared_evidence_paths` honours the current round's two acceptance *reports*
#: and nothing else. So writing the bundle put eight unlicensed paths into the
#: post-freeze delta, :func:`_post_freeze_delta_problems` declared the round void, and
#: the ratification that was supposed to publish the checkpoint destroyed the round
#: authorising it. The mechanism had no executable final state, by any sequence.
#:
#: Licensing the eight is the repair. The requirements beside each name are what the
#: licence is paid for, in the shape :func:`_state_document_problems` established: a
#: path that *may* move proves nothing, so each file is required to carry the content
#: its own task specification says it carries.
#:
#: The fields, all optional and all read by :func:`_deliverable_content_problems`:
#:
#: * `requires` — literal needles the text must contain.
#: * `values` — keys resolved by :func:`_deliverable_value` against **repository data**:
#:   the reviewed candidate commit, the candidate contract version, the tag, the round,
#:   and the reviewed-family manifest digest recomputed from the tree itself.
#: * `hashes` — repository paths whose SHA-256 must appear in the text. Absent files are
#:   reported rather than skipped, or the requirement would evaporate with its subject.
#: * `manifest_names` — checkpoint-manifest fields whose every entry or key must be
#:   named. An empty field is reported: requiring the entries of an empty list is the
#:   table-emptying defect one level down.
#: * `exact` — the whole stripped file, not a needle.
#: * `json_object` — must parse as a non-empty JSON object.
#: * `manual_cases` — every case ID in :data:`MANUAL_RUNBOOK` must carry a verdict.
#: * `note` — what the requirement is, and where it is **shape rather than content** it
#:   says so instead of dressing shape up as verification. §11.19.4 lists those three.
CHECKPOINT_DELIVERABLES = (
    {
        "name": "checkpoint-report.md",
        "values": ("candidate_commit", "contract_version", "checkpoint_tag"),
        "requires": (
            "CP-00",
            "contract-manifest.yaml",
            "manual-test-report.md",
            "known-risks.md",
            "restore-or-rollback-note.md",
        ),
        "manifest_names": ("integrated_w03_tasks",),
        "note": (
            "the integration report S00 requires: the frozen contract version and "
            "candidate commit, the tag, every merged task ID, and references to the "
            "manual report, the known risks and the rollback note"
        ),
    },
    {
        "name": "contract-manifest.yaml",
        "values": ("candidate_commit", "contract_version", "reviewed_manifest_digest"),
        "requires": ("migration_head: none",),
        "hashes": (
            "contracts/analysis/v1/stage-registry.json",
            "contracts/analysis/v1/legacy-stage-name-map.json",
            "fixtures/golden/selection.json",
            "requirements/validation.in",
            "requirements/validation.lock",
        ),
        "note": (
            "W0-INT-01 deliverable 2 in full: exact file hashes, contract versions, "
            "candidate commit, dependency-lock hashes, migration_head: none, the golden "
            "selection hash and the analysis registry/name-map hashes. Every value is "
            "recomputed from the repository, so a manifest describing another tree is a "
            "failure and not a difference of opinion"
        ),
    },
    {
        "name": "automated-summary.txt",
        "values": ("current_round",),
        "requires": ("PASS",),
        "note": (
            "the automated stream's summary for the round being ratified. Cross-record "
            "only: the manifest already has to say PASS for that round, so this catches "
            "a summary from another round or one that contradicts the record it "
            "summarises, not an independently verified test result"
        ),
    },
    {
        "name": "manual-test-report.md",
        "manual_cases": True,
        "note": (
            "W0-INT-01 deliverable 3: tester identity, timestamps and a verdict per "
            "case for every MT00 case the runbook defines. The case list is read out of "
            "the runbook and the runtime disposition out of the manifest; the tester "
            "name and the timestamp are shape only, because no repository value can "
            "say who ran a manual test or when"
        ),
    },
    {
        "name": "migration-head.txt",
        "exact": "none",
        "note": (
            "the migration head W0-INT-01's frozen inputs record: none. The whole file, "
            "not a needle in it"
        ),
    },
    {
        "name": "build-info.json",
        "json_object": True,
        "values": ("candidate_commit",),
        "note": (
            "a non-empty JSON object naming the commit it describes. Nothing else about "
            "this file is stated in any repository document, so nothing else is "
            "required: the object shape is shape, and is recorded as such"
        ),
    },
    {
        "name": "known-risks.md",
        "manifest_names": (
            "architecture_defer",
            "open_inputs_carried_forward",
            "open_escalations",
        ),
        "note": (
            "every risk the checkpoint record already carries has to appear in the "
            "risk note: the deferred ADR, the four carried-forward open inputs and the "
            "open escalations. A published bundle that silently drops one is the "
            "failure this catches"
        ),
    },
    {
        "name": "restore-or-rollback-note.md",
        "values": ("checkpoint_tag", "candidate_commit"),
        "note": (
            "what to roll back and what to roll back to. W0-INT-01's rollback section "
            "states no further content, and none is invented here"
        ),
    },
)

#: The eight bundle paths, as the post-freeze licence sees them.
CHECKPOINT_DELIVERABLE_PATHS = frozenset(
    ACCEPTANCE_EVIDENCE_PREFIX + entry["name"] for entry in CHECKPOINT_DELIVERABLES
)

#: Every way an entry above can state a content requirement, and the reason the list
#: exists as a list. :func:`_checkpoint_bundle_problems` requires each entry to carry at
#: least one of them: an entry with only `name` and `note` licenses a path to move and
#: asks nothing of it, which is the shape this whole round is a repair for, one level in
#: from the ceiling. The alternative — trusting the table pin to notice — leaves the
#: requirement silent on the tree rather than reported, and the module's own rule is
#: that a requirement over an empty collection is a problem to name, not a loop to skip.
DELIVERABLE_REQUIREMENT_KEYS = (
    "requires",
    "values",
    "hashes",
    "manifest_names",
    "exact",
    "json_object",
    "manual_cases",
)

#: **The three program records ratification reconciles, and the claim each must retract.**
#:
#: `W0-INT-01` deliverable 5 requires `CURRENT_STATE`, the checkpoint registry, the W0.3
#: wave plan and the S00 checklist to agree on the accepted commit, tag, frozen contract
#: set, exclusions and next unlocked S01 tasks; its allowed paths add `docs/INDEX.md`'s
#: status column so the index does not contradict the state it indexes. The first two
#: are licensed already and each has its own check — :func:`_registry_state_problem` and
#: :func:`_state_document_problems`. These three had neither licence nor check.
#:
#: They are **live-anchored**, like the state document and unlike
#: :data:`RECONCILIATIONS`: the program rewrites all three outside any review, so an
#: anchor pinned to the reviewed candidate would report rot the moment the integrator
#: writes an ordinary status update. Both directions are checked for the same reason
#: §11.12.3 gives: while `ratified: false` the denial must be **present** and the
#: post-ratification requirement **absent**, so the anchor cannot rot silently and the
#: requirement cannot be degenerate; once `ratified: true` they swap.
RATIFICATION_PUBLICATION_RECORDS = (
    {
        "item": "W0.3 wave plan",
        "path": "docs/program/waves/W0.3_ratification_integration.md",
        "denials": ("`W0-INT-01` is blocked", "| `W0-INT-01` | blocked |"),
        "requires": ("S01",),
        "must_still_contain": ("`v0.0.0-architecture`", "`W0-INT-01`"),
        "requires_note": (
            "the next unlocked S01 preparation tasks deliverable 5 names, with the "
            "wave's own status line and task row no longer calling W0-INT-01 blocked"
        ),
    },
    {
        "item": "S00 stage checklist",
        "path": "docs/stages/S00_architecture_and_behavior_freeze.md",
        "denials": (),
        "checklist": True,
        "requires": ("S01",),
        "must_still_contain": ("Automated exit evidence", "Manual local acceptance"),
        "requires_note": (
            "the next unlocked S01 preparation tasks, and every automated and manual "
            "exit-criterion box ticked: a checkpoint cannot be ratified while its own "
            "stage checklist still says its exit evidence is outstanding"
        ),
    },
    {
        "item": "documentation index status column",
        "path": "docs/INDEX.md",
        "row": "program/tasks/W0-INT-01.md",
        "denials": ("blocked",),
        "requires": ("accepted and integrated",),
        "must_still_contain": ("# Documentation index", "## Architecture", "## Program"),
        "requires_note": (
            "the status column this index already uses for every other completed task, "
            "on the one row that still says the ratifying task is blocked"
        ),
    },
)

#: The three publication documents, as the post-freeze licence sees them.
PUBLICATION_DOCUMENT_PATHS = frozenset(
    entry["path"] for entry in RATIFICATION_PUBLICATION_RECORDS
)

#: **The task files whose status banners ratification may close, and nothing else.**
#:
#: `W0-INT-01`'s allowed paths license `docs/program/tasks/W0-*.md` **status banners
#: only** — "requirements, gates and deliverables of an accepted task are frozen by its
#: acceptance" — plus its own banner and handoff. The set is written out rather than
#: globbed from the working tree for the reason the ceilings are: a licence computed
#: from a directory the integrator can add a file to is a licence the integrator can
#: widen. :meth:`TableExpectationTests.test_the_completed_task_files_are_pinned_and_are_the_candidate_set`
#: anchors the list to `git ls-tree` at the immutable reviewed candidate, so it cannot
#: rot into naming files that never existed.
#:
#: **What the licence is paid with, for all seventeen and not only for the ratifying
#: task.** Round thirteen's first form checked the banner *content* of exactly one file
#: — `W0-INT-01`'s own — and asked nothing of the other sixteen beyond "the rest of the
#: file did not move". That is a licence to rewrite sixteen accepted tasks' status text
#: to say anything at all, under cover of a ratification, which is precisely the "a path
#: that may move proves nothing" finding that produced :data:`RECONCILIATIONS` one layer
#: up. :func:`_task_banner_problems` now requires a banner ratification actually rewrote
#: to name :data:`CHECKPOINT_TAG` — a closure names the checkpoint it closes at — and
#: the requirement is two-directional: while `ratified: false` **no** licensed banner
#: may name the tag, which today none does, so it cannot be satisfied by a banner that
#: already said it. Untouched banners are asked for nothing, because `W0-INT-01`
#: *permits* the edit and does not require it; what is refused is spending the licence
#: on something other than the checkpoint.
COMPLETED_TASK_FILES = frozenset(
    {
        "docs/program/tasks/W0-ANA-01.md",
        "docs/program/tasks/W0-ARC-01.md",
        "docs/program/tasks/W0-ARC-02.md",
        "docs/program/tasks/W0-BHV-01.md",
        "docs/program/tasks/W0-BHV-02.md",
        "docs/program/tasks/W0-CLN-01.md",
        "docs/program/tasks/W0-DEP-01.md",
        "docs/program/tasks/W0-DOM-01.md",
        "docs/program/tasks/W0-DOM-02.md",
        "docs/program/tasks/W0-EVD-01.md",
        "docs/program/tasks/W0-EVT-01.md",
        "docs/program/tasks/W0-INT-00.md",
        "docs/program/tasks/W0-INT-01.md",
        "docs/program/tasks/W0-QA-00.md",
        "docs/program/tasks/W0-QA-01.md",
        "docs/program/tasks/W0-QA-02.md",
        "docs/program/tasks/W0-QA-03.md",
    }
)

#: The ratifying task's own file, and the denial its banner carries until CP-00 is
#: published. No other task file may close this one's banner, and this one may also
#: rewrite its own handoff — the two exceptions :func:`_task_banner_problems` makes.
RATIFYING_TASK_FILE = "docs/program/tasks/W0-INT-01.md"
RATIFYING_TASK_BANNER_DENIAL = "ratification and publication blocked"

#: The program's own state document: the **third** external record.
#:
#: It sits in the same structural position as :data:`CHECKPOINT_REGISTRY`. Both are
#: program-level records that state CP-00's status in prose, and both must move *at the
#: ratification act itself* — after any possible freeze, because neither can truthfully
#: say CP-00 is ratified before CP-00 is ratified. That is why the registry is licensed
#: below and why this document has to be too.
PROGRAM_STATE_DOCUMENT = "docs/program/CURRENT_STATE.md"

#: The state document's standing denial, and the anchor that keeps the check honest.
#:
#: While the manifest says `ratified: false` this sentence must be **present**; once it
#: says `true` the same sentence must be **gone**. Both directions are checked, so the
#: anchor cannot rot silently: reword the sentence while CP-00 is unratified and the
#: check fails immediately, saying so, instead of passing forever afterwards. That is
#: the property a one-directional removal check does not have, and the reason this is
#: not modelled as a :data:`RECONCILIATIONS` entry — see
#: :func:`_state_document_problems`.
STATE_DOCUMENT_DENIAL = "Nothing is ratified, nothing is tagged"

#: A guard against satisfying the removal by deleting the document, nothing more.
#: Neither needle is evidence that the state document was brought up to date — both are
#: in it already — exactly as `must_still_contain` is for the removal-only `GATE-E`
#: entry. The report says so rather than letting the pair read as content verification.
STATE_DOCUMENT_MUST_STILL_CONTAIN = ("# Current state", "CP-00")

#: **What may differ between the tree whose digest was frozen and the tree in front of a
#: ratification.**
#:
#: Recomputing `tested_candidate_digest` over the commit that froze it proves the value
#: names a real tree. It cannot prove that tree is the one the streams judged, because
#: the freeze commit is immutable: that half stays green however far the working tree
#: drifts afterwards. So the delta is bounded as well. After the freeze only the
#: acceptance evidence the round itself declares (and only inside
#: :data:`ACCEPTANCE_EVIDENCE_PREFIX`), the three external records, and the five files
#: ratification reconciles may move. Anything else means the streams judged a different
#: input, and the rule the manifest already states in prose applies — "if it must
#: change, the round is void and a new one begins".
#:
#: :data:`PROGRAM_STATE_DOCUMENT` was **not** in this set until round seven, and
#: leaving it out was a deadlock rather than a strictness: the state document is inside
#: :func:`_digest_paths`, so ratification either edited it and voided its own round or
#: left it denying the ratification it had just performed. Licensing it is not a free
#: pass — :func:`_state_document_problems` is what the licence is paid for, and it is
#: checked in both directions so that the licence cannot be spent silently.
#:
#: :data:`CHECKPOINT_DELIVERABLE_PATHS`, :data:`PUBLICATION_DOCUMENT_PATHS` and
#: :data:`COMPLETED_TASK_FILES` were **not** in this set until round thirteen, and
#: leaving them out was the same deadlock one size larger. `W0-INT-01` is required to
#: create eight evidence files, reconcile the wave plan, the S00 checklist and the
#: documentation index, and close the status banners of the tasks the checkpoint
#: completes. Every one of those paths is inside :func:`_digest_paths`, so an honest
#: ratification moved thirty-odd unlicensed paths and voided the round that authorised
#: it — the checkpoint mechanism had no executable final state at all. Three groups of
#: checks are what those licences are paid for, each two-directional:
#: :func:`_checkpoint_bundle_problems`, :func:`_publication_record_problems` and
#: :func:`_task_banner_problems`.
#:
#: Pinned here rather than read out of the record, for the same reason
#: :data:`RATIFICATION_DELTA_CEILING` is: a ceiling the integrator can widen by editing
#: the document they also write is not a ceiling. That applies to the three new groups
#: exactly as it does to the five architecture files — the bundle is eight named files,
#: not "anything under `artifacts/checkpoints/CP-00/`", and the task set is seventeen
#: named files, not "whatever `docs/program/tasks/` happens to hold".
POST_FREEZE_DELTA_CEILING = (
    frozenset(
        {
            CHECKPOINT_MANIFEST,
            CHECKPOINT_REGISTRY,
            PROGRAM_STATE_DOCUMENT,
            ACCEPTANCE_RECORD,
        }
    )
    | RATIFICATION_DELTA_CEILING
    | CHECKPOINT_DELIVERABLE_PATHS
    | PUBLICATION_DOCUMENT_PATHS
    | COMPLETED_TASK_FILES
)

#: The path the post-freeze probes move to prove the delta check fires.
#:
#: It has to be a path that can never *become* licensed, or the probe rots into a
#: tautology the day the ceiling widens — which is exactly what happened to its
#: predecessor, `docs/program/CURRENT_STATE.md`, when round seven licensed it.
#: `contracts/` is one of the :data:`IMMUTABLE_REVIEWED_PREFIXES`: this module's stated
#: policy is that ratification does not reach them and no record licenses a byte.
#: Widening the ceiling to cover this file would mean abandoning that policy, not
#: adjusting a list, and the probes assert the prefix property rather than assuming it.
POST_FREEZE_STRANGER = "contracts/README.md"

#: **What each of the five ceiling files must actually say once CP-00 is ratified.**
#:
#: Round four made the delta an equality of *paths*. An independent probe then declared
#: all five, edited four of them with a comment, changed no stale statement, and passed.
#: Path equality proves a file moved; it cannot prove the reconciliation was made. Each
#: entry below names the stale claim that must go and what must stand in its place.
#:
#: `stale` is also an anti-vacuity guard: it must be present in the file **at the
#: reviewed candidate**, or the anchor has rotted into a no-op and the test fails saying
#: so, instead of silently passing forever.
RECONCILIATIONS = (
    {
        "item": "PD-02 acceptance precondition, CP-00 architecture review",
        "path": "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
        "stale": "so the acceptance precondition is not yet met",
        "sentence_requires": ("62", "31", "satisfied"),
        "requires_note": (
            "a sentence recording the precondition as satisfied, with the 62 legacy "
            "names and 31 alias-bearing sites that show it"
        ),
    },
    {
        "item": "PD-02 acceptance precondition, owner decision ledger",
        "path": "docs/architecture/CP00_OWNER_DECISIONS.md",
        "stale": "so the precondition is not yet met",
        "sentence_requires": ("62", "31", "satisfied"),
        "requires_note": (
            "a sentence recording the precondition as satisfied, with the 62 legacy "
            "names and 31 alias-bearing sites that show it"
        ),
    },
    {
        "item": "stale GATE-E probe prose",
        "path": "docs/architecture/ARCHITECTURE_LINT_RULES.md",
        "stale": "still untracked",
        # Removal-only, and marked as such. `GATE-E` is already in the document, so it
        # cannot distinguish a made reconciliation from an unmade one; it is a guard
        # against gutting the file, not evidence that the work was done. Calling it
        # `must_contain` alongside genuinely-new requirements invited exactly that
        # confusion.
        "removal_only": True,
        "must_still_contain": ("GATE-E",),
        "requires_note": (
            "the GATE-E probe description with the untracked claim removed; the probe "
            "itself must still be documented"
        ),
    },
    {
        "item": "owner-decision count in the ADR index",
        "path": "docs/architecture/ADR_INDEX.md",
        "stale": "`PD-01`\u2013`PD-04`",
        "new_text": ("`PD-01`\u2013`PD-05`",),
        "requires_note": "the decision range widened to `PD-01`-`PD-05`",
    },
)

#: The review carries its own status twice, as JSON and as prose. Ratification must move
#: both; this is the value the Markdown must quote verbatim.
REVIEW_JSON = "docs/architecture/CP00_ARCHITECTURE_REVIEW.json"
REVIEW_MARKDOWN = "docs/architecture/CP00_ARCHITECTURE_REVIEW.md"
UNRATIFIED_REVIEW_STATUS = "owner_decisions_recorded"
REVIEW_DISCLAIMER = "still not the ratification act"

#: Provenance a ratification record must carry. A delta authorised by a bare boolean
#: would be an accident with a flag on it.
RATIFICATION_REQUIRED_FIELDS = ("task", "decided_on", "decided_by", "reason")

GATE_MARKERS = {
    "A": "name-map gate PASS",
    "B": "evidence gate PASS",
    "C": "reviewer gate PASS",
    "D": "decision-transfer gate PASS",
}

#: Gate C resolves the accepted inventory out of this repository's object database. A
#: mutated copy is not a Git work tree, so the object database is named explicitly for
#: that gate only. Gate B addresses the legacy repository with its own ``git -C`` and
#: must not inherit a ``GIT_DIR``.
GATE_NEEDS_OBJECT_STORE = frozenset({"C"})


def _read(relative: str) -> str:
    return (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def _load(relative: str) -> object:
    return json.loads(_read(relative))


def _repository_json_files(prefix: str) -> list[str]:
    root = REPOSITORY_ROOT / prefix
    return sorted(
        path.relative_to(REPOSITORY_ROOT).as_posix() for path in root.rglob("*.json")
    )


def _object_keys(document: object):
    """Yield every object key of a JSON document, at any depth."""
    if isinstance(document, dict):
        for key, value in document.items():
            yield key
            yield from _object_keys(value)
    elif isinstance(document, list):
        for value in document:
            yield from _object_keys(value)


def _declared_properties(document: object):
    """Yield every name declared as a JSON Schema ``properties`` member or ``required``
    entry, at any depth."""
    if isinstance(document, dict):
        for key, value in document.items():
            if key == "properties" and isinstance(value, dict):
                yield from value
            if key == "required" and isinstance(value, list):
                yield from (item for item in value if isinstance(item, str))
            yield from _declared_properties(value)
    elif isinstance(document, list):
        for value in document:
            yield from _declared_properties(value)


def _forbidden_name_hits(document: object, forbidden: frozenset[str]) -> list[str]:
    """Every forbidden name this document declares, by any of the three routes.

    §4 claims the sweep covers a name "neither as an object key at any depth, nor as a
    `properties` member, nor as a `required` entry". Three routes, one expression, so
    the claim is made in one place and can be controlled in one place —
    :class:`ForbiddenNameSweepControlTests` plants a name on each route in turn and
    requires *this* function to find it. It was previously written out twice, in the two
    sweeps, with nothing planting anything: four separate mutations
    (``FORBIDDEN_VERSION_KEYS = frozenset()``, ``FORBIDDEN_AUTHORITY_KEYS =
    frozenset()``, `_object_keys` not descending into lists, `_declared_properties` not
    yielding `required` entries) each left the whole suite green.
    """
    return sorted(
        {key for key in _object_keys(document) if key in forbidden}
        | {name for name in _declared_properties(document) if name in forbidden}
    )


def _values_for_key(document: object, wanted: str):
    if isinstance(document, dict):
        for key, value in document.items():
            if key == wanted and isinstance(value, str):
                yield value
            else:
                yield from _values_for_key(value, wanted)
    elif isinstance(document, list):
        for value in document:
            yield from _values_for_key(value, wanted)


def _fenced_blocks(relative: str) -> list[tuple[str | None, str]]:
    """Return ``(heading, body)`` for every fenced block of a Markdown document."""
    blocks: list[tuple[str | None, str]] = []
    heading: str | None = None
    lines = _read(relative).splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#"):
            heading = line.strip()
        if line.startswith("```"):
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            blocks.append((heading, "\n".join(body) + "\n"))
        index += 1
    return blocks


def _documented_analysis_gate(letter: str) -> str:
    """The executable body of one documented analysis gate, taken from the contract.

    The command is not restated here: it is read out of the artifact under review, so a
    gate that is edited, renamed or removed changes what this module runs.
    """
    wanted = f"### Gate {letter} "
    matches = [
        body
        for heading, body in _fenced_blocks(ANALYSIS_README)
        if heading is not None and heading.startswith(wanted)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Gate {letter} is not recorded exactly once as an executable block in "
            f"{ANALYSIS_README}; found {len(matches)}. A gate that cannot be located "
            "cannot be executed as documented."
        )
    return matches[0]


def _documented_blocks(relative: str, language: str = "bash") -> list[str]:
    """Every fenced block of one document, in source order."""
    lines = _read(relative).splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].startswith("```" + language):
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            blocks.append("\n".join(body) + "\n")
        index += 1
    return blocks


# ---------------------------------------------------------------------------
# The subprocess chokepoint.
#
# Round nine removed three names — ``GIT_DIR``, ``GIT_WORK_TREE``,
# ``GIT_INDEX_FILE`` — from an inherited environment. That list is complete for the
# *discovery* class, and an independent reviewer confirmed it: ``GIT_COMMON_DIR``,
# ``GIT_OBJECT_DIRECTORY``, ``GIT_ALTERNATE_OBJECT_DIRECTORIES``, ``GIT_NAMESPACE``
# and ``GIT_CEILING_DIRECTORIES`` all leave a seeded victim intact.
#
# It is the wrong class. Git *configuration* injection is strictly more powerful,
# because injected configuration is executed as a command. With no ``GIT_*`` variable
# set at all — only a ``HOME`` whose ``.gitconfig`` names ``core.fsmonitor`` — the same
# reviewer took three files out of another repository's index while this module's suite
# reported ``OK`` and ``_refuse_to_write_outside`` passed cleanly. Confirmed members:
# ``GIT_CONFIG_PARAMETERS``; ``HOME``/``XDG_CONFIG_HOME`` reaching ``.gitconfig``;
# ``GIT_CONFIG_COUNT`` with ``GIT_CONFIG_KEY_n``/``GIT_CONFIG_VALUE_n``; reaching
# ``core.fsmonitor``, ``core.hooksPath``, and ``core.attributesFile`` with
# ``filter.*.clean``; and ``PATH`` shadowing of ``git`` itself.
#
# The class is not closed by a longer denylist, because a denylist is a list of the
# names known on the day it was written. It is closed by never inheriting: the
# environment below is *constructed*, and a variable this module has not deliberately
# put there cannot reach a subprocess whatever it is called. That is why
# :func:`_allowlisted_env` has no reference to ``os.environ`` at all, and why
# :class:`GitSpawnChokepointTests` enumerates the module's own source rather than
# trusting the convention to hold.
# ---------------------------------------------------------------------------

#: The only ``PATH`` any subprocess this module spawns will see. The system
#: directories, and nothing the caller supplied.
#:
#: Inheriting ``PATH`` is a hole of the same class: a reviewer put an attacker's
#: executable named ``git`` earlier on the inherited ``PATH`` and routed all 28 of this
#: module's Git invocations through it with the suite still reporting ``OK``. Handing
#: Git *this* ``PATH`` closes it both for the programs this module names and for
#: everything Git itself goes on to spawn — hook scripts, ``git-`` subcommands,
#: ``core.fsmonitor``, clean and smudge filters.
#:
#: What it does not close is recorded rather than papered over: an attacker who can
#: write into these directories owns the host already, and no test module outranks
#: that. §11.15.4 states the limitation.
TRUSTED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

#: Every variable a subprocess spawned by this module receives, and **the reason it is
#: there**. The environment is built from this set and nothing else; the mapping is the
#: written justification the allowlist owes, and
#: :meth:`GitSpawnChokepointTests.test_the_allowlist_justifies_every_variable_it_admits`
#: fails if a variable is ever added without one.
GIT_ENV_ALLOWLIST: dict[str, str] = {
    "PATH": (
        "git, bash and the programs Git spawns have to be findable; TRUSTED_PATH, "
        "never the caller's"
    ),
    "HOME": (
        "an empty directory this module makes. Git reads ~/.gitconfig, "
        "~/.config/git/config, ~/.config/git/ignore and ~/.git-credentials from it; "
        "an empty HOME is the only value that makes all of them absent at once, and "
        "unsetting HOME entirely makes Git fall back to the passwd entry, which is the "
        "real user's home"
    ),
    "XDG_CONFIG_HOME": (
        "the second path to a global config and a global ignore file; pointed at an "
        "empty directory for the same reason as HOME"
    ),
    "GIT_CONFIG_GLOBAL": (
        "os.devnull, so the global config is empty by explicit statement and not only "
        "by HOME being empty — two independent reasons for the same fact"
    ),
    "GIT_CONFIG_SYSTEM": "os.devnull, the same for /etc/gitconfig",
    "GIT_CONFIG_NOSYSTEM": (
        "1, which suppresses the system config on Git versions predating "
        "GIT_CONFIG_SYSTEM"
    ),
    "GIT_TERMINAL_PROMPT": (
        "0: no probe here may block on a credential prompt, and a suite that hangs "
        "reports nothing"
    ),
    "LC_ALL": (
        "C.UTF-8. Not inherited, because the digest recipes sort paths and the "
        "documented gates read UTF-8 contract files; a locale reaching this module "
        "from outside would make both answer differently on different hosts"
    ),
    "LANG": "C.UTF-8, for the same reason and for programs that read LANG only",
    "TZ": "UTC, so any timestamp a documented gate prints is host-independent",
}

#: ``git`` and ``bash``, resolved from :data:`TRUSTED_PATH` alone, cached after the
#: first lookup. A test clears this to prove the resolution ignores the caller's
#: ``PATH``.
_PROGRAM_CACHE: dict[str, str] = {}

#: Filled on first use by :func:`_neutral_home` and removed at interpreter exit.
_NEUTRAL_HOME: Path | None = None


def _program(name: str) -> str:
    """The absolute path of ``name``, found on :data:`TRUSTED_PATH` and nowhere else.

    There is deliberately no fall back to the caller's ``PATH``. A fall back is how a
    shadowing attack succeeds on exactly the host where it matters, and "I could not
    find git in the system directories" is a failure a human can read and fix, whereas
    "I ran the git I was handed" is not a failure at all until much later.
    """
    resolved = _PROGRAM_CACHE.get(name)
    if resolved is None:
        resolved = shutil.which(name, path=TRUSTED_PATH)
        if resolved is None:
            raise AssertionError(
                f"{name!r} is not on the trusted path {TRUSTED_PATH!r}. This module "
                "refuses to fall back to the caller's PATH, because that is the "
                "shadowing vector it is closing; install the program in a system "
                "directory or widen TRUSTED_PATH deliberately."
            )
        _PROGRAM_CACHE[name] = resolved
    return resolved


def _neutral_home() -> Path:
    """An empty directory, made once, that every subprocess sees as its ``HOME``.

    It must be a real, existing, empty directory rather than a name: Git creates
    nothing here, but a ``HOME`` that does not exist makes some programs fall back to
    the passwd entry, which is the home this is supposed to replace.
    """
    global _NEUTRAL_HOME
    if _NEUTRAL_HOME is None or not _NEUTRAL_HOME.is_dir():
        home = Path(tempfile.mkdtemp(prefix="w0-qa-01-neutral-home-"))
        (home / "xdg").mkdir()
        atexit.register(shutil.rmtree, home, True)
        _NEUTRAL_HOME = home
    return _NEUTRAL_HOME


def _allowlisted_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for every subprocess this module spawns, built from nothing.

    **This function never reads** ``os.environ``. That is the property, not an
    implementation detail: a denylist is correct only for the names its author knew,
    and the defect this replaces was a denylist that was complete for the class its
    author was looking at and empty for the class that mattered. Construction from an
    allowlist is right for names nobody has thought of yet.

    ``extra`` is for a variable a *caller* names on purpose and can justify — today
    only :attr:`_MutableCopy.run_gate` and :class:`DocumentedGateTests`, which set
    ``GIT_DIR`` so that documented Gate C can reach the repository's object database
    from a copy that has none. It is a deliberate widening at one named call site, in
    the argument list where a reader can see it, and it is not inheritance.
    """
    home = _neutral_home()
    env = {
        "PATH": TRUSTED_PATH,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
    }
    if set(env) != set(GIT_ENV_ALLOWLIST):
        raise AssertionError(
            "the constructed environment and the allowlist that justifies it have "
            f"drifted: {sorted(set(env) ^ set(GIT_ENV_ALLOWLIST))}"
        )
    if extra:
        env.update(extra)
    return env


def _git(
    *arguments: str,
    cwd: Path | str | None = None,
    stdin: bytes | None = None,
    text: bool = False,
    check: bool = False,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """**The one place this module spawns Git.** Reading or writing, no exceptions.

    Before round ten there was no such place. 23 ``subprocess.run(["git", ...])`` calls
    were spread through the module; 5 passed a sanitised ``env=`` and 18 inherited the
    caller's environment whole, nine of those in production helpers rather than test
    bodies. The docstring of the sanitiser claimed it was "shared by every Git
    subprocess this module spawns" and it was shared by five of twenty-three.

    A convention that every call site should pass ``env=`` is not a structure: the
    nineteenth caller inherits nothing but the convention, and no test notices. This
    function is the structure, and :class:`GitSpawnChokepointTests` is what keeps it
    one — it parses this module's own source and fails on any Git subprocess spawned
    anywhere else.

    Note that the guard on *where a write may land*, :func:`_refuse_to_write_outside`,
    is deliberately not folded in here. It applies to the two writing helpers and takes
    a sandbox root and a prefix that a read has no notion of; putting it here would mean
    inventing a root for every ``ls-tree``. The two checks are orthogonal and both are
    enumerated by their own test.
    """
    return subprocess.run(
        [_program("git"), *arguments],
        input=stdin,
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=text,
        check=check,
        env=_allowlisted_env(env_extra),
    )


def _run_shell(script: str, cwd: Path, env_overrides: dict[str, str] | None = None):
    """Execute a documented block through a shell, exactly as it is written.

    The shell is deliberate. Three W0.3 gates were found to be one-directional, one of
    them because a ``$`` inside a double-quoted ``python -c`` string was expanded by the
    shell before Python ever saw it. Running the recorded text through ``bash`` is what
    exposes that class of defect; re-typing the body into Python would hide it.

    **The second chokepoint.** A documented gate is a shell script and several of them
    run ``git``; handing one the caller's environment hands Git the caller's
    environment one level down, so this builds its environment the same way
    :func:`_git` does, from :func:`_allowlisted_env`. Round nine's form did sanitise
    here, and nothing tested it: replacing that line with ``dict(os.environ)`` left all
    189 tests green. It is covered now by
    :meth:`ShellChokepointEnvironmentTests.test_a_gate_never_sees_the_callers_git_environment`.
    """
    return subprocess.run(
        [_program("bash"), "-c", script],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=_allowlisted_env(env_overrides),
    )


def _candidate_reviewed_paths(root: Path) -> list[str]:
    """Every reviewed-family path recorded in the candidate commit."""
    listing = _git(
        "-C",
        str(root),
        "--no-replace-objects",
        "ls-tree",
        "-r",
        "--name-only",
        REVIEWED_CANDIDATE_COMMIT,
        text=True,
    )
    if listing.returncode != 0:
        raise AssertionError(
            "the reviewed candidate commit is not readable from this checkout: "
            + listing.stderr.strip()
        )
    return [path for path in listing.stdout.split("\n") if path.startswith(REVIEWED_PREFIXES)]


def _present_reviewed_paths(root: Path) -> list[str]:
    """Every reviewed-family path present in the checkout now.

    Tracked plus untracked-not-ignored, which is the set the checkpoint manifest's own
    digest recipe describes. Globbing the working tree instead would pick up a
    gitignored ``scripts/__pycache__`` byte-code file and make the answer depend on
    whether anyone had run the validator; the manifest records that exact mistake.
    """
    listing = _git(
        "-C",
        str(root),
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        "contracts",
        "fixtures",
        "docs/architecture",
        "scripts",
        text=True,
    )
    if listing.returncode != 0:
        raise AssertionError("git could not enumerate the reviewed families")
    return sorted(path for path in listing.stdout.split("\n") if path)


def _candidate_blob(root: Path, relative: str) -> bytes | None:
    blob = _git(
        "-C",
        str(root),
        "--no-replace-objects",
        "show",
        f"{REVIEWED_CANDIDATE_COMMIT}:{relative}",
    )
    return blob.stdout if blob.returncode == 0 else None


def _drifted_reviewed_paths(root: Path) -> list[str]:
    """Reviewed paths that are not byte-identical to the candidate commit.

    Three ways a path drifts, and all three are reported: its bytes changed, it was
    deleted, or it did not exist at the candidate and exists now. The third was a blind
    spot in the first form of this check — it only walked the candidate's own file list,
    so a *new* architecture document could have been added without the check noticing.

    The comparison is byte-for-byte on purpose. A parsed-JSON comparison is blind to
    re-indentation and key reordering — the domain scope gate of `W0-DOM-02` had exactly
    that hole — and the hashes this review records are hashes of bytes, so anything
    weaker would certify a document nobody hashed.
    """
    at_candidate = set(_candidate_reviewed_paths(root))
    present = set(_present_reviewed_paths(root))
    drifted: set[str] = set()
    for relative in at_candidate:
        blob = _candidate_blob(root, relative)
        on_disk = root / relative
        if blob is None or not on_disk.is_file() or blob != on_disk.read_bytes():
            drifted.add(relative)
    drifted |= present - at_candidate
    return sorted(drifted)


def _checkpoint_manifest(root: Path) -> dict | None:
    """The external checkpoint record, or ``None`` when there is not one."""
    path = root / CHECKPOINT_MANIFEST
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return document if isinstance(document, dict) else None


def _ratification_record(root: Path) -> tuple[bool, frozenset[str], list[str]]:
    """Read the declared ratification from the external record.

    Returns ``(externally_ratified, declared_delta, problems)``. ``problems`` is empty
    only when the record is admissible; an inadmissible record licenses **nothing**, so
    the caller treats it exactly like a missing one and reports why.

    The policy this implements, in full:

    * No record, or ``ratified`` false — no delta at all. Every reviewed family stays
      byte-identical to the candidate. A record cannot pre-authorise an edit before the
      ratification it authorises has actually been taken.
    * ``ratified`` true — a delta is admissible only if the record names the paths
      explicitly, every named path lies under ``docs/architecture/``, every named path
      is inside :data:`RATIFICATION_DELTA_CEILING`, and every named path already existed
      at the candidate. A path that did not exist at the candidate is a **new** reviewed
      artifact; that needs review, not ratification.
    * The record must name the task that took the act, when, on whose authority, and
      why. A delta authorised by a bare boolean would be an accident with a flag on it.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return False, frozenset(), []

    problems: list[str] = []
    ratified = manifest.get("ratified")
    if not isinstance(ratified, bool):
        return False, frozenset(), [
            f"{CHECKPOINT_MANIFEST}: 'ratified' must be a boolean, got {ratified!r}"
        ]
    if not ratified:
        return False, frozenset(), []

    record = manifest.get("ratification")
    if not isinstance(record, dict):
        return True, frozenset(), [
            f"{CHECKPOINT_MANIFEST} declares ratified true but carries no 'ratification' "
            "object. Ratification may change the reviewed architecture family only "
            "through a record that names, explicitly: 'allowed_delta_paths' (a list of "
            "repository-relative paths under docs/architecture/), plus "
            + ", ".join(f"'{field}'" for field in RATIFICATION_REQUIRED_FIELDS)
            + "."
        ]

    for field in RATIFICATION_REQUIRED_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(
                f"{CHECKPOINT_MANIFEST}: ratification.{field} must be a non-empty string"
            )
    task = record.get("task")
    if isinstance(task, str) and task != RATIFYING_TASK:
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.task is {task!r}; only "
            f"{RATIFYING_TASK} may ratify CP-00"
        )

    declared = record.get("allowed_delta_paths")
    if not isinstance(declared, list) or not declared:
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths must be a "
            "non-empty list of repository-relative paths"
        )
        return True, frozenset(), problems
    if not all(isinstance(item, str) and item for item in declared):
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths must hold strings"
        )
        return True, frozenset(), problems
    if len(declared) != len(set(declared)):
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths repeats a path"
        )

    outside_family = sorted(
        item for item in declared if not item.startswith(RATIFIABLE_REVIEWED_PREFIX)
    )
    if outside_family:
        problems.append(
            "ratification may not reach outside "
            f"{RATIFIABLE_REVIEWED_PREFIX}: {outside_family}"
        )
    above_ceiling = sorted(set(declared) - RATIFICATION_DELTA_CEILING - set(outside_family))
    if above_ceiling:
        problems.append(
            "these paths are outside the ratification ceiling this module pins, so the "
            "record cannot authorise them: "
            f"{above_ceiling}. Widening the ceiling means reopening W0-QA-01."
        )
    absent_at_candidate = sorted(
        item
        for item in declared
        if item.startswith(RATIFIABLE_REVIEWED_PREFIX)
        and _candidate_blob(root, item) is None
    )
    if absent_at_candidate:
        problems.append(
            "these paths did not exist at the reviewed candidate, so they are new "
            f"reviewed artifacts and need review rather than ratification: "
            f"{absent_at_candidate}"
        )
    # The ceiling is not only an upper bound. For CP-00 the five files are not a menu:
    # each one is a reconciliation ratification is obliged to perform — the flag, the
    # `PD-02` precondition in two documents, the stale `GATE-E` sentence, the ADR-index
    # decision count. An earlier form of this check said "the record may name fewer
    # paths than the ceiling", which let a record declare the work and skip it.
    understated = sorted(RATIFICATION_DELTA_CEILING - set(declared))
    if understated:
        problems.append(
            "the record does not declare every reconciliation CP-00 ratification owes; "
            f"missing: {understated}. For this checkpoint the declared set is the whole "
            "ceiling, not a subset of it."
        )

    if problems:
        return True, frozenset(), problems
    return True, frozenset(declared), []


def _flat(text: str) -> str:
    """Whitespace-normalised text, so a re-wrapped paragraph still matches."""
    return re.sub(r"\s+", " ", text)


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", _flat(text))


#: A commit's tree never changes, and reading 214 blobs one ``git show`` at a time
#: costs 214 processes per probe. Cached per (repository, commit).
_TREE_BLOBS: dict[tuple[str, str], dict[str, bytes]] = {}


def _tree_blobs(root: Path, commit: str) -> dict[str, bytes] | None:
    """Every blob of a commit's tree, by path. ``None`` when the commit is unreadable.

    Two Git calls, whatever the size of the tree: one ``ls-tree -r -z`` for the object
    names and one ``cat-file --batch`` for the contents.
    """
    key = (str(root), commit)
    cached = _TREE_BLOBS.get(key)
    if cached is not None:
        return cached
    listing = _git(
        "-C", str(root), "--no-replace-objects", "ls-tree", "-r", "-z", commit
    )
    if listing.returncode != 0:
        return None
    entries: list[tuple[str, str]] = []
    for record in listing.stdout.decode("utf-8").split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        fields = meta.split()
        if len(fields) != 3 or fields[1] != "blob":
            continue
        entries.append((path, fields[2]))
    batch = _git(
        "-C",
        str(root),
        "--no-replace-objects",
        "cat-file",
        "--batch",
        stdin=b"\n".join(name.encode("ascii") for _, name in entries) + b"\n",
    )
    if batch.returncode != 0:
        return None
    payload = batch.stdout
    blobs: dict[str, bytes] = {}
    cursor = 0
    for path, _name in entries:
        newline = payload.find(b"\n", cursor)
        header = payload[cursor:newline].split()
        if newline < 0 or len(header) != 3:
            return None
        size = int(header[2])
        blobs[path] = payload[newline + 1 : newline + 1 + size]
        cursor = newline + 1 + size + 1
    _TREE_BLOBS[key] = blobs
    return blobs


def _digest_paths(root: Path) -> list[str]:
    """The path set the manifest's digest recipe enumerates.

    Tracked plus untracked-not-ignored, which is the recipe's own wording. Globbing the
    working tree instead would hash a gitignored ``.pyc``; the manifest records that
    mistake as the reason the recipe says what it says.
    """
    listing = _git(
        "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard",
        text=True, check=True,
    ).stdout
    return sorted({path for path in listing.split("\n") if path})


def _digest_over(field: str, paths, read) -> str:
    """The manifest's recipe over an arbitrary tree: blank **only the field computed**.

    Path bytes then the raw 32-byte SHA-256 of the content, in sorted path order. The
    manifest contributes the SHA-256 of its canonical JSON with ``field`` blanked at the
    top level and in every `acceptance_rounds` entry; the other digest keeps its real
    value.

    An earlier form blanked *both* fields, on the stated rationale that naming one would
    be self-referentially impossible once the other held a value. That rationale was
    wrong — each field is computed when the other is either still empty or already
    frozen — and the consequence was not theoretical: with both blanked, the evidence
    digest was arithmetically independent of `tested_candidate_digest`, so the field
    naming which tree the streams judged could hold any 64-hex string, forever, with
    every check silent.

    The recipe is expressed over an abstract ``(paths, read)`` pair because it must run
    over two different trees: the working tree, and the tree of the commit that froze
    `tested_candidate_digest`. Those are the same arithmetic and must not be two
    implementations that can drift apart.
    """
    if field not in ACCEPTANCE_DIGEST_FIELDS:
        raise AssertionError(f"not an acceptance digest field: {field}")
    running = hashlib.sha256()
    for relative in sorted(paths):
        running.update(relative.encode("utf-8"))
        content = read(relative)
        if relative == CHECKPOINT_MANIFEST:
            document = json.loads(content.decode("utf-8"))
            document[field] = ""
            for entry in document.get("acceptance_rounds", []):
                if isinstance(entry, dict) and field in entry:
                    entry[field] = ""
            content = json.dumps(
                document, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        running.update(hashlib.sha256(content).digest())
    return running.hexdigest()


def _acceptance_digest(root: Path, field: str = "evidence_bundle_digest") -> str:
    """The recipe over the tree in front of you."""
    return _digest_over(
        field, _digest_paths(root), lambda relative: (root / relative).read_bytes()
    )


def _acceptance_digest_at(root: Path, commit: str, field: str) -> str | None:
    """The same recipe over a commit's tree. ``None`` when the commit is unreadable."""
    blobs = _tree_blobs(root, commit)
    if blobs is None:
        return None
    return _digest_over(field, blobs.keys(), blobs.__getitem__)


def _freeze_commit(root: Path) -> str | None:
    """The commit that froze the live `tested_candidate_digest`, or ``None``.

    **The manifest never records its own commit; history supplies it.** A commit cannot
    name its own hash, which is why the manifest identifies its candidate by content —
    and the same fact makes the freeze commit discoverable rather than recordable. Walk
    the manifest's own history newest-to-oldest and take the *oldest consecutive* commit
    whose manifest already carries today's value both at the top level and in the entry
    for today's `current_round`. The walk stops at the first commit that does not, so a
    value that was set, changed, and set back again resolves to the commit that froze
    the value now in force, not to an older coincidence.

    §8.12 of the review used to assert that this was impossible — that the tree
    `tested_candidate_digest` describes "stops existing once the results are written",
    so nobody could ever recompute it. That is false, and it licensed leaving the field
    unchecked through four review rounds. The recipe blanks the field being computed, so
    the value is exactly the digest of the tree at the commit that froze it, and Git
    keeps that tree forever.

    **Oldest-consecutive is the whole property, and round eight is the first round that
    tested it.** Replacing ``freeze = commit`` with ``return commit`` — "the newest
    commit carrying the value" — left all 159 tests green, because every test ran where
    the freeze commit *was* `HEAD`: the live repository has one, and the sandboxes never
    commit. On the honest sequence the difference is the whole check. Freeze at `F`,
    record the streams' results at `G`; both carry the value, `G`'s tree carries the
    results, and only `F`'s tree digests to the declared value. A newest-first
    implementation returns `G` and the digest does not reproduce.
    :class:`FreezeCommitHistoryTests` builds that sequence as real commits in a
    throwaway repository, where the freeze commit is deliberately not `HEAD`.

    **No commit window, and the walk fails closed.** An earlier form passed ``-n 200``.
    That is not a safety margin, it is a wrong answer waiting: with more manifest
    revisions than the window, the walk ran off the end and returned the oldest commit
    *inside* the window — a commit that did not freeze the value — which
    :func:`_tested_digest_problems` then named as the commit that did. The history of one
    file is bounded by its own revisions and the loop already stops at the first commit
    that does not carry the value, so the window bought nothing. It is gone. An
    unreadable or unparseable ancestor now returns ``None`` rather than breaking the
    walk: breaking would silently yield a *newer* commit than the true freeze, which is
    the unsafe direction, and "I cannot tell" is the honest answer.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return None
    declared = manifest.get("tested_candidate_digest")
    if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-f]{64}", declared):
        return None
    number = manifest.get("current_round")
    history = _git(
        "-C", str(root), "log", "--format=%H", "--", CHECKPOINT_MANIFEST, text=True
    ).stdout
    freeze: str | None = None
    for commit in (line for line in history.split("\n") if line):
        blob = _git(
            "-C", str(root), "--no-replace-objects", "show",
            f"{commit}:{CHECKPOINT_MANIFEST}",
        )
        if blob.returncode != 0:
            return None
        try:
            past = json.loads(blob.stdout.decode("utf-8"))
        except ValueError:
            return None
        entries = [
            entry
            for entry in past.get("acceptance_rounds", [])
            if isinstance(entry, dict) and entry.get("round") == number
        ]
        carries = (
            past.get("tested_candidate_digest") == declared
            and len(entries) == 1
            and entries[0].get("tested_candidate_digest") == declared
        )
        if not carries:
            if freeze is None:
                # **Leading revisions newer than the freeze.** The manifest has moved on
                # -- to a later round, or to no frozen round at all -- while the value
                # being resolved is still the one the working tree carries. Breaking here
                # instead of skipping made a freeze unresolvable the moment the round
                # after it was opened, and that is not a corner: opening the next round
                # is the first thing that happens after a round is voided. It is what
                # made committing the round-ten QA remediation red 129 tests while the
                # identical uncommitted tree was green -- the suite was resolving the
                # freeze through an uncommitted HEAD and stopped being able to the moment
                # the deliverable was delivered. Skipping costs nothing: everything older
                # than the first carrier is still cut by the break below, so a value set,
                # changed and set back still resolves to the commit that froze the value
                # now in force rather than to an older coincidence.
                continue
            # The first revision older than the freeze that does not carry the value.
            # Everything older is a different value or none, so the previous iteration
            # is the freeze.
            break
        freeze = commit
    return freeze


def _tested_digest_problems(root: Path) -> list[str]:
    """**Half one: does `tested_candidate_digest` name a tree that ever existed?**

    Until round seven this field was checked for 64-hex shape and for top-level /
    per-round agreement, and never again. `_retro_edited_digests` catches a value
    changed *after* its commit and is silent by construction when the fabricated value
    is the one that got committed, and only `evidence_bundle_digest` was ever
    recomputed. An independent reviewer built a complete, content-correct ratification
    carrying `deadbeef…` as the tree the streams judged, sealed in the order the
    manifest's own recipe prescribes, and every check stayed silent.

    So the value is recomputed, with the manifest's own recipe, over the tree of the
    commit that froze it. A fabricated value fails twice over: it is frozen at no commit
    at all, and if one were manufactured it would not reproduce.

    Silent while no digest is recorded — `null` is the legitimate state of a round that
    has not been dispatched — and this is deliberately *not* gated on ratification: a
    frozen digest is a claim about the world from the moment it is written, not from the
    moment somebody ratifies on it.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    declared = manifest.get("tested_candidate_digest")
    if declared in (None, ""):
        return []
    if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-f]{64}", declared):
        # Shape is reported by :func:`_acceptance_problems`; saying it twice would make
        # one defect look like two.
        return []
    number = manifest.get("current_round")
    commit = _freeze_commit(root)
    if commit is None:
        return [
            f"tested_candidate_digest {declared} is frozen at no commit: no commit of "
            f"{CHECKPOINT_MANIFEST} carries it both at the top level and in the round "
            f"{number} entry, so it names no tree this repository can produce. Freezing "
            "a round means committing the value that identifies its input; a value that "
            "exists only in a working tree identifies nothing."
        ]
    recomputed = _acceptance_digest_at(root, commit, "tested_candidate_digest")
    if recomputed != declared:
        return [
            "tested_candidate_digest does not reproduce over the tree of "
            f"{commit[:12]}, the commit that froze it: declared {declared}, recomputed "
            f"{recomputed}. The value must be the digest of the tree the acceptance "
            "streams judged, computed by the recipe the manifest itself records."
        ]
    return []


def _canonical_report_paths(number: object) -> dict[str, str]:
    """The two report paths a round may license, by stream. Names, not a prefix.

    **The hole this closes.** `_declared_evidence_paths` used to honour *any* path under
    :data:`ACCEPTANCE_EVIDENCE_PREFIX` that the manifest named in one of its four report
    fields. The manifest is written by the integrator, so that made the effective licence
    -- `POST_FREEZE_DELTA_CEILING | _declared_evidence_paths(manifest)` -- widenable by
    the very task the ceiling exists to constrain, without editing this module at all.
    An independent reviewer demonstrated it end to end: naming
    `artifacts/checkpoints/CP-00/check_state_records.py` as a report licensed editing it
    after the freeze, and every one of the fourteen checkers stayed silent. That file is
    the one this round *deliberately* excluded from the ceiling, so the module's own
    stated control -- "the bundle is eight named files, not anything under
    `artifacts/checkpoints/CP-00/`" -- was prose beside a check that could not fail on
    the thing the prose named. The signature defect, one function over from where it was
    being fixed.

    The name is the same one :meth:`_CheckpointSandbox.write_acceptance_reports` builds
    and the same one the committed reports of rounds three and six to eight carry, so
    this pins the convention already in force rather than inventing one. A report under
    any other name is simply not licensed: the round is void, which is the safe
    direction and the manifest's own rule.
    """
    if not isinstance(number, int) or isinstance(number, bool):
        return {}
    return {
        stream: f"{ACCEPTANCE_EVIDENCE_PREFIX}{stream}-report-round-{number}.md"
        for stream in ("manual", "automated")
    }


def _declared_evidence_paths(manifest: dict) -> set[str]:
    """The current round's acceptance-evidence files, as the manifest declares them.

    Report paths are data, so they are honoured only under
    :data:`ACCEPTANCE_EVIDENCE_PREFIX`. Otherwise a round could license any drift it
    liked by naming the drifted file as its own report.
    """
    number = manifest.get("current_round")
    expected = _canonical_report_paths(number)
    candidates: list[tuple[str, object]] = []
    for entry in manifest.get("acceptance_rounds", []):
        if isinstance(entry, dict) and entry.get("round") == number:
            candidates.append(("manual", entry.get("manual_report")))
            candidates.append(("automated", entry.get("automated_report")))
    for stream, key in (("manual", "manual_acceptance"),
                        ("automated", "automated_acceptance")):
        record = manifest.get(key)
        if isinstance(record, dict):
            candidates.append((stream, record.get("report_path")))
    return {
        value
        for stream, value in candidates
        if isinstance(value, str)
        and value.startswith(ACCEPTANCE_EVIDENCE_PREFIX)
        and ".." not in value.split("/")
        and value == expected.get(stream)
    }


def _post_freeze_delta_problems(root: Path) -> list[str]:
    """**Half two: is the tree in front of you still the tree that was frozen?**

    Half one proves the digest names a real tree. It cannot prove that tree is the one
    the streams judged, and it never will: the freeze commit is immutable, so half one
    stays green however far the working tree drifts afterwards. The two halves are not
    interchangeable and neither is sufficient.

    So the delta is bounded by :data:`POST_FREEZE_DELTA_CEILING` plus the round's own
    declared acceptance evidence. A path outside it means the acceptance streams judged
    a different input from the one being ratified, and the manifest's own rule applies:
    the round is void and a new one opens.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return []
    commit = _freeze_commit(root)
    if commit is None:
        return []  # half one already reports it
    blobs = _tree_blobs(root, commit)
    if blobs is None:
        return []
    frozen = {path: hashlib.sha256(content).digest() for path, content in blobs.items()}
    present: dict[str, bytes] = {}
    for relative in _digest_paths(root):
        path = root / relative
        if path.is_file():
            present[relative] = hashlib.sha256(path.read_bytes()).digest()
    delta = sorted(
        path
        for path in set(frozen) | set(present)
        if frozen.get(path) != present.get(path)
    )
    licensed = set(POST_FREEZE_DELTA_CEILING) | _declared_evidence_paths(manifest)
    strangers = [path for path in delta if path not in licensed]
    if not strangers:
        return []
    return [
        f"round {manifest.get('current_round')} is void: these paths differ from the "
        f"tree frozen at {commit[:12]} as tested_candidate_digest, and nothing licenses "
        f"them: {strangers}. The acceptance streams judged the frozen tree; a delta "
        "outside the round's declared acceptance evidence, the two external records and "
        "the declared ratification set means they judged a different input. The "
        "manifest's own rule: if it must change, the round is void and a new one begins."
    ]


def _state_document_problems(root: Path) -> list[str]:
    """**The price of licensing the third external record.**

    :data:`PROGRAM_STATE_DOCUMENT` is inside :func:`_digest_paths`, so before round seven
    it was an unlicensed path in the post-freeze delta — and CP-00 could not be ratified
    without changing it, because the document says in as many words that nothing is
    ratified. That is a deadlock, not a guarantee: ratification either edited the file
    and :func:`_post_freeze_delta_problems` declared its own round void, or left it and
    the repository shipped a ratified checkpoint whose state document denies the
    ratification. Nothing checked the second horn — the registry had
    :func:`_registry_state_problem` and the state document had nothing at all.

    Licensing the path removes the deadlock. This function is what the licence buys back,
    and it is deliberately **two-directional**, which is the only reason it can be
    trusted:

    * `ratified: false` — the denial must be **present**. This is the anti-vacuity half.
      Reword the sentence and the check fails *now*, loudly, while CP-00 is still
      unratified and re-anchoring costs nothing.
    * `ratified: true` — the denial must be **gone**, and the document must still be a
      document rather than an empty file that satisfies the removal by deletion.

    **Why this is not a :data:`RECONCILIATIONS` entry.** Every entry in that table is
    anchored to the file *at the reviewed candidate*, and the state document is not a
    reviewed artifact: the program rewrites it every round, outside review. The
    ratification-relevant sentence has already been rewritten twice since
    :data:`REVIEWED_CANDIDATE_COMMIT` — the candidate says "Nothing is frozen, nothing is
    ratified", today's tree says "Nothing is ratified, nothing is tagged" — so a
    candidate-anchored entry would report anchor rot the moment the integrator writes an
    ordinary state update. The live document, checked in both directions, is the anchor
    that actually holds for a living document.

    **What this does not prove.** The `ratified: true` half is removal-only. It shows the
    denial is gone; it cannot show the document now says anything true, and
    :data:`STATE_DOCUMENT_MUST_STILL_CONTAIN` is a guard against deletion, not evidence.
    The stronger form — the closed-vocabulary code-span citation
    :func:`_registry_state_problem` reads out of the registry row — is not available
    here: the state document carries no such citation, so requiring one would mean
    either editing `docs/program/CURRENT_STATE.md`, which this task may not do, or
    inventing a convention for a document QA does not own. Recorded in
    `docs/program/reviews/W0-QA-01.md` §11.12 as a request, the same way §11.7 records
    the registry-format request, rather than decided here.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    path = root / PROGRAM_STATE_DOCUMENT
    if not path.is_file():
        return [f"{PROGRAM_STATE_DOCUMENT} is missing"]
    current = _flat(path.read_text(encoding="utf-8"))

    if manifest.get("ratified") is not True:
        if STATE_DOCUMENT_DENIAL not in current:
            return [
                f"anchor rot: {CHECKPOINT_MANIFEST} says ratified=false and "
                f"{PROGRAM_STATE_DOCUMENT} no longer carries {STATE_DOCUMENT_DENIAL!r}. "
                "That sentence is what the ratified half of this check requires to be "
                "removed, so with it already gone the check would pass forever without "
                "ever proving the state document was brought up to date. Re-anchor it "
                "in tests/contract/test_cp00_candidate.py before trusting it again."
            ]
        return []

    problems: list[str] = []
    if STATE_DOCUMENT_DENIAL in current:
        problems.append(
            f"{PROGRAM_STATE_DOCUMENT} still says {STATE_DOCUMENT_DENIAL!r} while "
            f"{CHECKPOINT_MANIFEST} declares ratified=true. A ratified checkpoint may "
            "not ship a state document that denies the ratification; this is the same "
            "two-record contradiction _registry_state_problem exists to prevent, in the "
            "one direction nothing was checking."
        )
    for needle in STATE_DOCUMENT_MUST_STILL_CONTAIN:
        if needle not in current:
            problems.append(
                f"{PROGRAM_STATE_DOCUMENT} does not carry {needle!r}. The denial must be "
                "removed by updating the state document, not by gutting it."
            )
    return problems


def _banner_split(text: str) -> tuple[str, str]:
    """``(the leading status banner, everything else)`` of a task file.

    The banner is the first contiguous run of blockquote lines, which is where every
    task file in this program carries its status. Nothing but a heading or a blank line
    may precede it: a blockquote further down is prose, not a banner, and treating it as
    one would licence a body edit as a banner edit. A file with no banner returns
    ``("", text)``, so a banner *added* by ratification still leaves the rest to compare.
    """
    lines = text.splitlines(keepends=True)
    start = None
    for index, line in enumerate(lines):
        if line.startswith(">"):
            start = index
            break
        if line.strip() and not line.startswith("#"):
            break
    if start is None:
        return "", text
    end = start
    while end < len(lines) and lines[end].startswith(">"):
        end += 1
    return "".join(lines[start:end]), "".join(lines[:start] + lines[end:])


def _strip_handoff(text: str) -> str:
    """Everything before the handoff section, for the one file that may rewrite one."""
    head, _, _tail = text.partition("\n## Handoff")
    return head


def _deliverable_value(root: Path, manifest: dict, key: str) -> str:
    """One expected value of an evidence deliverable, **derived from the repository**.

    Not read out of the bundle, and not read out of the record the integrator writes:
    the candidate commit and contract version are this module's own pinned constants,
    the reviewed-family digest is recomputed from the tree, and the round is the one the
    manifest is currently on — the only value here that a manifest edit can move, and it
    identifies which round the summary belongs to rather than asserting its result.
    """
    if key == "candidate_commit":
        return REVIEWED_CANDIDATE_COMMIT
    if key == "contract_version":
        return CANDIDATE_CONTRACT_VERSION
    if key == "checkpoint_tag":
        return CHECKPOINT_TAG
    if key == "reviewed_manifest_digest":
        return _reviewed_manifest_digest(root)[0]
    if key == "current_round":
        return f"round {manifest.get('current_round')}"
    raise AssertionError(f"no such deliverable value: {key}")


def _manual_case_ids(root: Path) -> list[str]:
    """The manual case IDs, read out of the runbook this task does not write."""
    path = root / MANUAL_RUNBOOK
    if not path.is_file():
        return []
    return sorted(set(re.findall(r"MT00-\d{2}", path.read_text(encoding="utf-8"))))


def _manual_report_problems(root: Path, manifest: dict, relative: str, text: str,
                            ratified: bool) -> list[str]:
    """`W0-INT-01` deliverable 3, checked against the runbook and the record.

    The case list comes from :data:`MANUAL_RUNBOOK` and the runtime disposition from the
    checkpoint manifest, so neither is a value this module invented. The tester name and
    the start timestamp are **shape**: a non-empty value, and a date-shaped one. No
    repository value can say who ran a manual test or when, and §11.19.4 records that
    rather than presenting the field check as content verification.
    """
    problems: list[str] = []
    cases = _manual_case_ids(root)
    if not cases:
        return [
            f"{MANUAL_RUNBOOK} defines no MT00 case IDs, so requiring {relative} to "
            "record a verdict for each of them proves nothing"
        ]
    lines = text.splitlines()
    for case in cases:
        carrying = [line for line in lines if case in line]
        if not carrying:
            problems.append(f"{relative} records no result for {case}")
            continue
        verdicts = {
            verdict
            for line in carrying
            for verdict in MANUAL_VERDICTS
            if re.search(rf"\b{verdict}\b", line)
        }
        if not verdicts:
            problems.append(
                f"{relative} names {case} without any of {list(MANUAL_VERDICTS)}; a "
                "manual report records a verdict per case, not a mention per case"
            )
        elif ratified and verdicts != {"PASS"}:
            problems.append(
                f"{relative} records {case} as {sorted(verdicts)} while "
                f"{CHECKPOINT_MANIFEST} declares ratified=true; any failure or "
                "unexplained block stops the task"
            )
    for field in ("tester", "started_at"):
        value = ""
        for line in lines:
            if field in line and ":" in line:
                value = line.split(":", 1)[1].strip(" |*`")
                if value:
                    break
        if not value:
            problems.append(
                f"{relative} carries no {field} value; the manual report records who "
                "ran it and when"
            )
        elif field == "started_at" and not re.search(r"\d{4}-\d{2}-\d{2}", value):
            problems.append(
                f"{relative} records started_at as {value!r}, which carries no date"
            )
    disposition = manifest.get("runtime_fields")
    if not isinstance(disposition, str) or not disposition.strip():
        problems.append(
            f"{CHECKPOINT_MANIFEST} records no runtime_fields disposition, so requiring "
            f"{relative} to carry it proves nothing"
        )
    else:
        for field in ("backend_runtime", "frontend_runtime"):
            if not any(field in line and disposition in line for line in lines):
                problems.append(
                    f"{relative} does not record {field} as {disposition!r}; CP-00 is "
                    "architecture-only and the disposition is recorded, not skipped"
                )
    return problems


def _deliverable_content_problems(root: Path, manifest: dict, entry: dict,
                                  relative: str, text: str, ratified: bool) -> list[str]:
    """What one evidence deliverable must say, whenever it exists.

    Deliberately **not** gated on ratification. A bundle file naming the wrong candidate
    commit is wrong from the moment it is written, and gating the content on the flag
    would leave the whole unratified branch asserting nothing — the guard-that-cannot-
    fail shape this task has been reopened over. What the flag gates is *existence*:
    before ratification these files are not required at all.
    """
    problems: list[str] = []
    flat = _flat(text)
    if entry.get("exact") is not None:
        if text.strip() != entry["exact"]:
            problems.append(
                f"{relative} is {text.strip()!r} and must be exactly "
                f"{entry['exact']!r}. Expected " + entry["note"]
            )
        return problems
    if entry.get("json_object"):
        try:
            document = json.loads(text)
        except ValueError:
            problems.append(f"{relative} is not JSON. Expected " + entry["note"])
            document = None
        if document is not None and not (isinstance(document, dict) and document):
            problems.append(
                f"{relative} is not a non-empty JSON object. Expected " + entry["note"]
            )
    if entry.get("manual_cases"):
        problems.extend(_manual_report_problems(root, manifest, relative, text, ratified))
    for needle in entry.get("requires", ()):
        if needle not in flat:
            problems.append(
                f"{relative} does not carry {needle!r}. Expected " + entry["note"]
            )
    for key in entry.get("values", ()):
        value = _deliverable_value(root, manifest, key)
        if value not in flat:
            problems.append(
                f"{relative} does not carry the {key} {value!r} this repository "
                "produces. Expected " + entry["note"]
            )
    for path_value in entry.get("hashes", ()):
        source = root / path_value
        if not source.is_file():
            problems.append(
                f"{path_value} is not in this repository, so requiring {relative} to "
                "carry its hash proves nothing"
            )
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest not in flat:
            problems.append(
                f"{relative} does not carry the SHA-256 of {path_value} ({digest}). "
                "Expected " + entry["note"]
            )
    for field in entry.get("manifest_names", ()):
        recorded = manifest.get(field)
        names = (
            sorted(recorded)
            if isinstance(recorded, (dict, list, tuple))
            else []
        )
        if not names:
            problems.append(
                f"{CHECKPOINT_MANIFEST}.{field} names nothing, so requiring {relative} "
                "to carry its entries proves nothing"
            )
            continue
        for name in names:
            if not isinstance(name, str) or name not in flat:
                problems.append(
                    f"{relative} does not name {name!r}, which "
                    f"{CHECKPOINT_MANIFEST}.{field} records. Expected " + entry["note"]
                )
    return problems


def _checkpoint_bundle_problems(root: Path) -> list[str]:
    """**The price of licensing the eight evidence deliverables.**

    Two directions, and neither is empty:

    * `ratified: false` — the bundle is not required. What *is* required is that none of
      the eight already exists at the reviewed candidate, or "ratification must create
      it" would be satisfied by a file that was there all along; and that any file
      already written carries its content, so a half-published bundle naming the wrong
      tree fails now rather than at the tag.
    * `ratified: true` — all eight exist and every content requirement holds.

    The anti-vacuity anchor is asserted against the candidate commit rather than the
    working tree on purpose. The integrator legitimately writes this bundle before
    setting the flag, and a check that made that state red would be round eight's defect
    again: a suite that cannot survive its own publication.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    ratified = manifest.get("ratified") is True
    if not CHECKPOINT_DELIVERABLES:
        return [
            "CHECKPOINT_DELIVERABLES is empty, so POST_FREEZE_DELTA_CEILING licenses "
            "bundle paths that nothing here checks: 'every deliverable' over an empty "
            "table is no requirement at all"
        ]
    problems: list[str] = []
    for entry in CHECKPOINT_DELIVERABLES:
        relative = ACCEPTANCE_EVIDENCE_PREFIX + entry["name"]
        if not any(entry.get(key) for key in DELIVERABLE_REQUIREMENT_KEYS):
            problems.append(
                f"{relative} is licensed to move and required to carry nothing: its "
                f"table entry declares none of {list(DELIVERABLE_REQUIREMENT_KEYS)}, so "
                "the licence is paid for with an existence check and an empty file "
                "would satisfy it"
            )
        if _candidate_blob(root, relative) is not None:
            problems.append(
                f"degenerate requirement: {relative} already exists at the reviewed "
                "candidate, so requiring ratification to produce it proves nothing"
            )
            continue
        path = root / relative
        if not path.is_file():
            if ratified:
                problems.append(
                    f"{relative} is missing while {CHECKPOINT_MANIFEST} declares "
                    "ratified=true. W0-INT-01 deliverable 1 is the evidence bundle; a "
                    "checkpoint published without it has no reproducible evidence at "
                    "all. Expected " + entry["note"]
                )
            continue
        problems.extend(
            _deliverable_content_problems(
                root, manifest, entry, relative, path.read_text(encoding="utf-8"), ratified
            )
        )
    return problems


def _acceptance_record_rows(text: str) -> dict[int, str]:
    """The round table, by round number. A row is a table line opening with an integer."""
    rows: dict[int, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*(\d+)\s*\|", line)
        if match:
            rows[int(match.group(1))] = line
    return rows


def _acceptance_record_problems(root: Path) -> list[str]:
    """**The price of licensing the acceptance record.**

    The rule is the one rounds seven and eight actually failed on: *the record of the
    rounds may not be behind the record it records.* Every round the manifest gives a
    verdict has to have a row here, and the sweep that was written after round eight
    covered a different axis and said so — "the round accounting it says nothing about
    has failed twice on its own".

    Deliberately **not** gated on ratification, and that is what makes it a check rather
    than a licence. The completeness rule can fail in either state and is the reason the
    path may move at all: a verdict lands, the record is written, and if the record is
    three rounds stale — which is what round eight found — the checkpoint is publishing
    an account of itself that its own manifest contradicts. The ratified half adds the
    one thing only ratification can require: the round being ratified is recorded, and
    recorded as passing.

    The anti-vacuity guard is on the manifest side, not the document side. If no round
    carries a verdict there is nothing to be complete about, and a completeness rule over
    an empty list is the table-emptying defect one level down, so it is reported.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    path = root / ACCEPTANCE_RECORD
    if not path.is_file():
        return [f"{ACCEPTANCE_RECORD} is missing"]
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    if ACCEPTANCE_RECORD_HEADING not in text:
        problems.append(
            f"{ACCEPTANCE_RECORD} does not carry {ACCEPTANCE_RECORD_HEADING!r}. The "
            "record is brought up to date by writing the round into it, not by removing "
            "the table it belongs in."
        )
    rows = _acceptance_record_rows(text)
    reported = [
        entry.get("round")
        for entry in manifest.get("acceptance_rounds", [])
        if isinstance(entry, dict) and entry.get("verdict")
    ]
    if not reported:
        problems.append(
            f"{CHECKPOINT_MANIFEST} records no round with a verdict, so requiring "
            f"{ACCEPTANCE_RECORD} to carry one proves nothing"
        )
    for number in reported:
        if number not in rows:
            problems.append(
                f"{ACCEPTANCE_RECORD} carries no row for round {number}, whose verdict "
                f"{CHECKPOINT_MANIFEST} already records. The acceptance record is what a "
                "reader is pointed at; a record behind the manifest is the stale round "
                "accounting rounds seven and eight failed on."
            )
    if manifest.get("ratified") is not True:
        return problems
    current = manifest.get("current_round")
    row = rows.get(current)
    if row is None:
        problems.append(
            f"{ACCEPTANCE_RECORD} carries no row for round {current}, the round CP-00 is "
            "being ratified on"
        )
        return problems
    if "PASS" not in row or "FAIL" in row:
        problems.append(
            f"{ACCEPTANCE_RECORD} records round {current} as {row.strip()!r} while "
            f"{CHECKPOINT_MANIFEST} declares ratified=true. A checkpoint is ratified on a "
            "round both streams passed, and its own record has to say so."
        )
    return problems


def _publication_scope(entry: dict, text: str, relative: str) -> tuple[str | None, str | None]:
    """The text one publication requirement is about: a whole document, or one row."""
    marker = entry.get("row")
    if marker is None:
        return text, None
    rows = [line for line in text.splitlines() if marker in line]
    if len(rows) != 1:
        return None, (
            f"{relative} carries {len(rows)} rows naming {marker!r}; the status column "
            "requirement is about exactly one"
        )
    return rows[0], None


def _publication_record_problems(root: Path) -> list[str]:
    """**The price of licensing the wave plan, the S00 checklist and the index.**

    The same two-directional shape :func:`_state_document_problems` uses, and for the
    same reason: these are living program documents, so an anchor pinned to the reviewed
    candidate would rot on the next ordinary status update, and a one-directional
    removal check would pass forever the day somebody rewords the sentence.

    * `ratified: false` — every denial must be **present** and every post-ratification
      requirement **absent**. The first half is anti-vacuity; the second is the
      degeneracy guard :func:`_reconciliation_problems` already applies at the candidate,
      applied here to the live document because that is the only anchor these have.
    * `ratified: true` — the denials are gone, the requirements are there, and the
      document still carries the structure the requirement was about, so the retraction
      cannot be made by deleting the section.

    The S00 checklist is checked structurally rather than by phrase: while CP-00 is
    unratified its exit-criterion boxes are unchecked, once ratified none may remain, and
    the checklist may not shrink below the candidate's — ticking every box by deleting
    the list is the gutting move `must_still_contain` exists to refuse.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    ratified = manifest.get("ratified") is True
    if not RATIFICATION_PUBLICATION_RECORDS:
        return [
            "RATIFICATION_PUBLICATION_RECORDS is empty, so POST_FREEZE_DELTA_CEILING "
            "licenses publication documents that nothing here checks: 'every record' "
            "over an empty table is no requirement at all"
        ]
    problems: list[str] = []
    for entry in RATIFICATION_PUBLICATION_RECORDS:
        relative = entry["path"]
        if not (entry["denials"] or entry.get("checklist")):
            problems.append(
                f"{entry['item']}: the entry names neither a denial nor a checklist, so "
                "nothing holds its anchor while CP-00 is unratified and the "
                "post-ratification requirement can rot into a no-op unnoticed"
            )
        if not entry["requires"]:
            problems.append(
                f"{entry['item']}: the entry names no post-ratification requirement, so "
                "the licence is paid for with a removal and a published document that "
                "says nothing about the checkpoint would satisfy it"
            )
        path = root / relative
        if not path.is_file():
            problems.append(f"{relative} is missing")
            continue
        raw = path.read_text(encoding="utf-8")
        scope, scope_problem = _publication_scope(entry, raw, relative)
        if scope_problem is not None:
            problems.append(scope_problem)
            continue
        flat = _flat(scope)
        for denial in entry["denials"]:
            if ratified and denial in flat:
                problems.append(
                    f"{entry['item']}: {relative} still says {denial!r} while "
                    f"{CHECKPOINT_MANIFEST} declares ratified=true. A published "
                    "checkpoint may not ship a plan that says its own ratification is "
                    "blocked."
                )
            if not ratified and denial not in flat:
                problems.append(
                    f"anchor rot: {relative} no longer carries {denial!r} while CP-00 "
                    "is unratified. That claim is what the ratified half requires to be "
                    "gone, so with it already gone the check would pass forever. "
                    "Re-anchor it in tests/contract/test_cp00_candidate.py."
                )
        for needle in entry["requires"]:
            if ratified and needle not in flat:
                problems.append(
                    f"{entry['item']}: {relative} does not carry {needle!r}. Expected "
                    + entry["requires_note"]
                )
            if not ratified and needle in flat:
                problems.append(
                    f"degenerate requirement: {relative} already carries {needle!r} "
                    "while CP-00 is unratified, so requiring it after ratification "
                    "proves nothing"
                )
        # Deliberately against the whole document, not `flat`. `flat` is the *scope* of
        # the status requirement, which for a row-scoped entry is the single row -- and
        # checking a document-level anti-gutting guard against one row is what made the
        # index entry's needle a tautology: the needle it looked for was the marker that
        # selected the row it looked in, so it could not fail while it was reached.
        whole = _flat(raw)
        for needle in entry["must_still_contain"]:
            if needle not in whole:
                problems.append(
                    f"{entry['item']}: {relative} does not carry {needle!r}. The stale "
                    "claim must be retracted by bringing the document up to date, not "
                    "by removing what it was about."
                )
        if entry.get("checklist"):
            problems.extend(_checklist_problems(root, relative, raw, ratified))
    return problems


def _checklist_problems(root: Path, relative: str, raw: str, ratified: bool) -> list[str]:
    """The S00 exit-criterion boxes, in both directions and against the candidate."""
    unchecked = len(re.findall(r"- \[ \]", raw))
    total = unchecked + len(re.findall(r"- \[[xX]\]", raw))
    blob = _candidate_blob(root, relative)
    if blob is None:
        return [f"{relative} does not exist at the reviewed candidate"]
    at_candidate = blob.decode("utf-8")
    candidate_total = len(re.findall(r"- \[[ xX]\]", at_candidate))
    if not candidate_total:
        return [
            f"anchor rot: {relative} carries no checklist at the reviewed candidate, so "
            "requiring ratification to complete one proves nothing"
        ]
    problems: list[str] = []
    if total < candidate_total:
        problems.append(
            f"{relative} carries {total} exit-criterion boxes and the reviewed candidate "
            f"carries {candidate_total}. The checklist is completed by ticking it, not "
            "by shortening it."
        )
    if not ratified:
        if not unchecked:
            problems.append(
                f"anchor rot: every exit-criterion box in {relative} is already ticked "
                "while CP-00 is unratified, so requiring ratification to tick them "
                "proves nothing"
            )
    elif unchecked:
        problems.append(
            f"{relative} still leaves {unchecked} exit-criterion boxes unticked while "
            f"{CHECKPOINT_MANIFEST} declares ratified=true; the stage checklist is the "
            "checkpoint's own exit evidence"
        )
    return problems


def _task_banner_problems(root: Path) -> list[str]:
    """**The price of licensing seventeen task files.**

    `W0-INT-01` licenses their **status banners** and says what that means: "Nothing but
    the banner may change here: requirements, gates and deliverables of an accepted task
    are frozen by its acceptance." A licence to move a file is not a licence to rewrite
    it, so that sentence is enforced rather than quoted — every licensed task file is
    compared with the tree the round was frozen at, and everything outside the banner
    must be byte-identical. The ratifying task's own file may also rewrite its handoff,
    which is the other half of what its allowed paths say, and nothing else may.

    The comparison is against the **frozen tree** rather than the reviewed candidate
    because that is what the post-freeze licence is about: these files legitimately move
    between the candidate and the freeze, and it is what happens *after* the freeze that
    the acceptance streams did not judge.

    Both directions, again. The banner rule holds in either state and can fail in
    either — it is a constraint, not a state assertion — and on top of it the ratifying
    task's own banner must carry its denial while CP-00 is unratified and the published
    tag once it is not.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    ratified = manifest.get("ratified") is True
    if not COMPLETED_TASK_FILES:
        return [
            "COMPLETED_TASK_FILES is empty, so POST_FREEZE_DELTA_CEILING licenses task "
            "files that nothing here checks: 'every licensed task file' over an empty "
            "set is no requirement at all"
        ]
    commit = _freeze_commit(root)
    blobs = _tree_blobs(root, commit) if commit is not None else None
    problems: list[str] = []
    for relative in sorted(COMPLETED_TASK_FILES):
        path = root / relative
        if not path.is_file():
            problems.append(f"{relative} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        banner, rest = _banner_split(text)
        # Whether ratification spent the banner licence on this file. ``None`` when
        # there is no frozen tree to compare with, which is the pre-dispatch state and
        # is reported by :func:`_tested_digest_problems` rather than twice here.
        rewritten: bool | None = None
        if blobs is not None and relative not in blobs:
            problems.append(
                f"{relative} is not in the tree frozen at {commit[:12]}, so nothing "
                "here can be compared with the tree the acceptance streams judged"
            )
        if blobs is not None and relative in blobs:
            frozen_banner, frozen_rest = _banner_split(blobs[relative].decode("utf-8"))
            rewritten = banner != frozen_banner
            if frozen_banner.strip() and not banner.strip():
                problems.append(
                    f"{relative}: the status banner is gone. Ratification closes a "
                    "banner; it does not remove one."
                )
            if relative == RATIFYING_TASK_FILE:
                rest, frozen_rest = _strip_handoff(rest), _strip_handoff(frozen_rest)
            if rest != frozen_rest:
                problems.append(
                    f"{relative} differs from the tree frozen at {commit[:12]} outside "
                    "its status banner. W0-INT-01 licenses the banner and nothing else: "
                    "the requirements, gates and deliverables of an accepted task are "
                    "frozen by its acceptance."
                )
        flat_banner = _flat(banner)
        if not ratified:
            if CHECKPOINT_TAG in flat_banner:
                problems.append(
                    f"degenerate requirement: the {relative} banner already names "
                    f"{CHECKPOINT_TAG} while CP-00 is unratified, so requiring a banner "
                    "ratification rewrote to name it would prove nothing"
                )
            if relative == RATIFYING_TASK_FILE:
                if RATIFYING_TASK_BANNER_DENIAL not in flat_banner:
                    problems.append(
                        f"anchor rot: the {relative} banner no longer says "
                        f"{RATIFYING_TASK_BANNER_DENIAL!r} while CP-00 is unratified. "
                        "That is what the ratified half requires to be gone; re-anchor "
                        "it in tests/contract/test_cp00_candidate.py."
                    )
            elif RATIFYING_TASK_BANNER_DENIAL in flat_banner:
                problems.append(
                    f"the {relative} banner says {RATIFYING_TASK_BANNER_DENIAL!r}, "
                    f"which is {RATIFYING_TASK_FILE}'s statement to make. A completed "
                    "task's banner may not open a second front on the ratification, "
                    "because no task is authorised to close one it did not open."
                )
            continue
        if RATIFYING_TASK_BANNER_DENIAL in flat_banner:
            problems.append(
                f"the {relative} banner still says {RATIFYING_TASK_BANNER_DENIAL!r} "
                f"while {CHECKPOINT_MANIFEST} declares ratified=true. No other task may "
                "close this banner, so nothing else can correct it."
            )
        if relative == RATIFYING_TASK_FILE:
            if CHECKPOINT_TAG not in flat_banner:
                problems.append(
                    f"the {relative} banner does not name {CHECKPOINT_TAG}, the tag the "
                    "ratification it records publishes"
                )
        elif rewritten and CHECKPOINT_TAG not in flat_banner:
            problems.append(
                f"{relative}: ratification rewrote this status banner and it names no "
                f"checkpoint. {CHECKPOINT_TAG} is what the act publishes, and a banner "
                "closed at CP-00 says so — otherwise the licence buys a free rewrite of "
                "sixteen accepted tasks' status text under cover of a ratification, "
                "which is a path that may move and is required to carry nothing."
            )
    return problems


def _verdict_token(value: object) -> str | None:
    """The leading verdict token of a stream result, or ``None`` if there is not one.

    A stream field carries a verdict and may carry detail after it (`PASS 6/6`,
    `FAIL - MT00-01`). Only the leading token is read: this is tokenising a verdict
    field, not interpreting a sentence.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    return value.split()[0]


def _acceptance_problems(root: Path) -> list[str]:
    """Ratification requires an accepted round, not merely a well-formed one.

    An independent probe ratified with both streams `owed`, the round's verdict `null`,
    both report paths `null` and invented digests, and the module passed: it checked
    shape and difference only. What ratification must structurally require is that a
    round actually passed, that both streams passed, that their primary reports exist as
    files, that the round's digests are the ones recorded at the top level, and that the
    evidence digest reproduces over the tree in front of you.

    The evidence digest also binds the evidence to its input — but only because the
    recipe was corrected to blank the computed field alone. While both fields were
    blanked the evidence digest was arithmetically independent of
    `tested_candidate_digest`, and this docstring claimed a binding that could not exist.
    The claim now stands on a probe rather than on prose:
    `test_the_evidence_digest_depends_on_the_tested_digest` builds two trees differing
    only in that value and requires the evidence digests to differ.

    Dependence is not verification, and round seven found the difference. Four trees
    differing only in `tested_candidate_digest` do produce four different evidence
    digests — and a ratification whose `tested_candidate_digest` named a tree that never
    existed was still accepted with every check silent, because nothing recomputed *that*
    field. Both halves are now checked: :func:`_tested_digest_problems` recomputes it
    over the commit that froze it, and :func:`_post_freeze_delta_problems` bounds what
    may have moved since.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return [f"{CHECKPOINT_MANIFEST} is missing"]
    problems: list[str] = []

    rounds = manifest.get("acceptance_rounds")
    if not isinstance(rounds, list) or not rounds:
        return [f"{CHECKPOINT_MANIFEST}: acceptance_rounds must be a non-empty list"]
    numbers = [entry.get("round") for entry in rounds if isinstance(entry, dict)]
    if len(numbers) != len(rounds) or not all(isinstance(n, int) for n in numbers):
        problems.append("every acceptance_rounds entry must be an object with an int round")
        return problems
    if len(set(numbers)) != len(numbers) or numbers != sorted(numbers):
        problems.append(f"acceptance_rounds numbers must be unique and ascending: {numbers}")
    current_number = manifest.get("current_round")
    if not isinstance(current_number, int):
        return problems + [f"{CHECKPOINT_MANIFEST}: current_round must be an integer"]
    matching = [entry for entry in rounds if entry.get("round") == current_number]
    if len(matching) != 1:
        return problems + [
            f"current_round is {current_number} and acceptance_rounds carries "
            f"{len(matching)} entries for it"
        ]
    current = matching[0]

    # The top level always speaks for the current round, ratified or not.
    for field in ACCEPTANCE_DIGEST_FIELDS:
        top = manifest.get(field)
        scoped = current.get(field)
        if top not in (None, "") and top != scoped:
            problems.append(
                f"{field}: the top level says {top!r} and round {current_number} says "
                f"{scoped!r}; the per-round copy exists so a retro-edit cannot hide"
            )

    # Half one of the tested-digest check, deliberately outside the ratification gate:
    # a frozen digest is a claim from the moment it is written.
    problems.extend(_tested_digest_problems(root))

    # Also outside the gate, and for the same kind of reason: the unratified half of
    # this check is the anti-vacuity anchor, and an anchor that is only consulted once
    # somebody ratifies is an anchor nobody can re-place in time.
    problems.extend(_state_document_problems(root))

    # The rest of what ratification has to write, and what each licence is paid for.
    # Outside the gate for the same reason the state document is: every one of these is
    # two-directional, and an anchor consulted only once somebody ratifies is an anchor
    # nobody can re-place in time.
    problems.extend(_checkpoint_bundle_problems(root))
    problems.extend(_publication_record_problems(root))
    problems.extend(_task_banner_problems(root))
    problems.extend(_acceptance_record_problems(root))

    if manifest.get("ratified") is not True:
        return problems

    # Half two. "At ratification, the tree in front of you is still the tree the streams
    # judged" is a precondition of ratifying, not of working: the licensed delta grows
    # legitimately while a round is in flight and is only closed when someone ratifies.
    problems.extend(_post_freeze_delta_problems(root))

    if current.get("verdict") != "PASS":
        problems.append(
            f"CP-00 cannot ratify on round {current_number}, whose verdict is "
            f"{current.get('verdict')!r}. Ratification requires an accepted round."
        )
    streams = current.get("streams")
    if not isinstance(streams, dict):
        problems.append(f"round {current_number} records no streams object")
    else:
        for name in ("automated", "manual"):
            if _verdict_token(streams.get(name)) != "PASS":
                problems.append(
                    f"the {name} stream of round {current_number} is "
                    f"{streams.get(name)!r}; both streams must pass"
                )
    for field in ("manual_report", "automated_report"):
        value = current.get(field)
        if not isinstance(value, str) or not value:
            problems.append(
                f"round {current_number} has no {field}: a ratified round must leave a "
                "primary report, not a claim that one was produced"
            )
        elif not (root / value).is_file():
            problems.append(f"round {current_number} names {field} {value!r}, which does not exist")
    for name in ("manual_acceptance", "automated_acceptance"):
        record = manifest.get(name)
        if not isinstance(record, dict):
            problems.append(f"{name} must be an object")
            continue
        if record.get("status") != "PASS":
            problems.append(
                f"{name}.status is {record.get('status')!r}; ratification requires PASS"
            )
        if record.get("round") != current_number:
            problems.append(
                f"{name}.round is {record.get('round')!r} and current_round is "
                f"{current_number}"
            )
        path_value = record.get("report_path")
        if not isinstance(path_value, str) or not path_value:
            problems.append(f"{name}.report_path is not recorded")
        elif not (root / path_value).is_file():
            problems.append(f"{name}.report_path {path_value!r} does not exist")
    for field in ACCEPTANCE_DIGEST_FIELDS:
        for where, value in (("top level", manifest.get(field)), (f"round {current_number}", current.get(field))):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                problems.append(
                    f"{field} at the {where} is {value!r}; a ratified checkpoint must "
                    "record both digests"
                )
    evidence = manifest.get("evidence_bundle_digest")
    if isinstance(evidence, str) and re.fullmatch(r"[0-9a-f]{64}", evidence):
        recomputed = _acceptance_digest(root)
        if evidence != recomputed:
            problems.append(
                "evidence_bundle_digest does not reproduce over this tree with the "
                f"recipe the manifest records: declared {evidence}, recomputed "
                f"{recomputed}. The evidence must describe the tree that carries it."
            )
    return problems


def _digest_history_problems(past: list[dict], current: dict) -> list[str]:
    """Pure comparison of per-round digests across manifest revisions.

    Extracted so the rule can be proved on synthetic history, because a rule that cannot
    fail today is a rule nobody has tested.

    **Why it is silent against this repository, stated correctly.** An earlier form of
    this docstring said every committed manifest carries `""` in every per-round digest
    "because no round has yet been sealed". That is false: `5207fb5` seals round 5 with
    `22e3027b…`, and it is the only commit of ten that carries a per-round value at all.
    The check is silent because that one value has not *changed* between commits, which
    is the thing it looks for — not because there is nothing to look at. Round eight's
    reviewer made it fire on real commits with a set/changed/set-back history, and the
    difference matters: "nothing to compare" would mean the rule is untested here, while
    "one value, unchanged" means it is running and satisfied.
    """
    now = {
        entry.get("round"): entry
        for entry in current.get("acceptance_rounds", [])
        if isinstance(entry, dict)
    }
    changed: set[str] = set()
    for revision, label in past:
        for entry in revision.get("acceptance_rounds", []):
            if not isinstance(entry, dict):
                continue
            number = entry.get("round")
            for field in ACCEPTANCE_DIGEST_FIELDS:
                was = entry.get(field)
                if not was:
                    continue
                is_now = now.get(number, {}).get(field)
                if is_now != was:
                    changed.add(
                        f"round {number} {field} was {was!r} in {label} and is "
                        f"{is_now!r} now"
                    )
    return sorted(changed)


def _retro_edited_digests(root: Path) -> list[str]:
    """Per-round digests that changed value between commits.

    `tested_candidate_digest` is frozen before the streams run and never edited
    afterwards; if it must change, the round is void and a new one begins. Round scoping
    is what makes that checkable — a legitimate new round adds an entry, while a
    retro-edit changes an existing one.

    **Walked from the freeze commit, not from `HEAD`.** The manifest in front of this
    function describes a round built on a particular frozen tree, and the revisions that
    matter are the ones that tree was built on. Walking from `HEAD` instead made the
    published checkpoint permanently red: once the integrator commits the publication,
    any later re-derivation of it — which is exactly what every sandbox in this module
    is — recomputes `evidence_bundle_digest` over its own tree, which can never be
    byte-identical to the integrator's, and the comparison read a legitimate
    re-derivation as a retro-edit. `test_the_checkpoint_mechanism_has_a_reachable_
    published_state`, the probe added to answer round nine's void, then failed on any
    published tree with the message that the checkpoint has no executable final state.
    Scoping to the freeze commit loses nothing: a retro-edit still shows up, because the
    freeze commit itself carries the value that was frozen, and every closed round's
    sealed digest is an ancestor of it.

    **No commit window.** The window was `-n 60`, which did not bound anything: with
    more manifest revisions than the window the oldest revisions simply stopped being
    compared, so a retro-edit *decayed into silence* after sixty further commits. The
    history of one file is bounded by its own revisions and the comparison is exact, so
    the window bought nothing and cost the guarantee.
    """
    start = _freeze_commit(root) or "HEAD"
    history = _git(
        "-C", str(root), "log", "--format=%H", start, "--", CHECKPOINT_MANIFEST,
        text=True,
    ).stdout
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return []
    past: list[tuple[dict, str]] = []
    for commit in (line for line in history.split("\n") if line):
        blob = _git(
            "-C", str(root), "--no-replace-objects", "show",
            f"{commit}:{CHECKPOINT_MANIFEST}",
        )
        if blob.returncode != 0:
            continue
        try:
            past.append((json.loads(blob.stdout.decode("utf-8")), commit[:12]))
        except ValueError:
            continue
    return _digest_history_problems(past, manifest)


def _reconciliation_problems(root: Path) -> list[str]:
    """Did ratification actually make each recorded reconciliation, or only touch bytes?

    Round four required the declared and observed path sets to be equal. That proves a
    file changed; it cannot prove the change was the one owed. An independent probe
    declared all five, added a comment to four of them and passed. These checks read the
    content each reconciliation is for.

    Every anchor is verified against the file **at the reviewed candidate** first. If a
    stale phrase is not there, the anchor has rotted and the check would silently pass
    forever, so it fails loudly instead.
    """
    problems: list[str] = []
    ratified = _checkpoint_manifest(root) is not None and (
        _checkpoint_manifest(root).get("ratified") is True
    )
    for entry in RECONCILIATIONS:
        relative = entry["path"]
        blob = _candidate_blob(root, relative)
        if blob is None:
            problems.append(f"{relative} does not exist at the reviewed candidate")
            continue
        at_candidate = _flat(blob.decode("utf-8"))
        stale = entry["stale"]
        if stale not in at_candidate:
            problems.append(
                f"anchor rot: {relative} does not contain {stale!r} at the reviewed "
                "candidate, so this reconciliation check proves nothing and must be "
                "re-anchored before it is trusted"
            )
            continue
        # The same guard on the other side. A positive requirement already satisfied by
        # the candidate cannot tell a made reconciliation from an unmade one, so every
        # `new_text` needle and every sentence conjunction must be *absent* there.
        # Removal-only entries declare that they have no positive signal instead of
        # dressing an existing phrase up as one.
        for needle in entry.get("new_text", ()):
            if needle in at_candidate:
                problems.append(
                    f"degenerate requirement: {relative} already carries {needle!r} at "
                    "the reviewed candidate, so requiring it proves nothing"
                )
        required_at_candidate = entry.get("sentence_requires")
        if required_at_candidate and any(
            all(token in sentence for token in required_at_candidate)
            for sentence in _sentences(blob.decode("utf-8"))
        ):
            problems.append(
                f"degenerate requirement: {relative} already has a sentence carrying "
                f"{list(required_at_candidate)} at the reviewed candidate"
            )
        if not entry.get("removal_only") and not (
            entry.get("new_text") or entry.get("sentence_requires")
        ):
            problems.append(
                f"{entry['item']}: no positive requirement and not marked removal_only, "
                "so removing the stale phrase is all that is ever checked"
            )

        on_disk_path = root / relative
        if not on_disk_path.is_file():
            problems.append(f"{relative} is missing")
            continue
        current = _flat(on_disk_path.read_text(encoding="utf-8"))

        if not ratified:
            if stale not in current:
                problems.append(
                    f"{relative}: the stale claim {stale!r} was removed without a "
                    "recorded ratification. Reconciling it is ratification's job and "
                    "needs the record that authorises the delta."
                )
            continue

        if stale in current:
            problems.append(
                f"{entry['item']}: {relative} still says {stale!r}. Ratification "
                "declared this reconciliation; changing the file without making it is "
                "not making it."
            )
        # Live, and it has to be: for a `removal_only` entry this is the *only* check
        # left standing on the far side of ratification. A guard written `if False and
        # …` is unreachable, so the removal could be satisfied by deleting the whole
        # passage the removal was supposed to leave behind — which is the exact defect
        # class this module exists to catch.
        for needle in entry.get("must_still_contain", ()):
            if needle not in current:
                problems.append(
                    f"{entry['item']}: {relative} does not carry {needle!r}. Expected "
                    + entry["requires_note"]
                )
        for needle in entry.get("new_text", ()):
            if needle not in current:
                problems.append(
                    f"{entry['item']}: {relative} does not carry {needle!r}. Expected "
                    + entry["requires_note"]
                )
        required = entry.get("sentence_requires")
        if required and not any(
            all(token in sentence for token in required)
            for sentence in _sentences(on_disk_path.read_text(encoding="utf-8"))
        ):
            problems.append(
                f"{entry['item']}: {relative} has no single sentence carrying all of "
                f"{list(required)}. Expected " + entry["requires_note"]
            )

    problems.extend(_review_consistency_problems(root, ratified))
    return problems


def _review_consistency_problems(root: Path, ratified: bool) -> list[str]:
    """The review states its status twice, as JSON and as prose. Both must move.

    Checking each document against itself would let the machine-readable half be
    ratified while the human half still tells the reader it ratifies nothing.
    """
    problems: list[str] = []
    try:
        review = json.loads((root / REVIEW_JSON).read_text(encoding="utf-8"))
        markdown = _flat((root / REVIEW_MARKDOWN).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [f"{REVIEW_JSON} or {REVIEW_MARKDOWN} is unreadable"]

    status = review.get("review_status")
    if not isinstance(status, str) or not status:
        return [f"{REVIEW_JSON}: review_status must be a non-empty string"]
    # **As a code span, not as a bare substring, and that is what makes the degeneracy
    # guard below survivable.** `W0-INT-01` requires `review_status == "ratified"`, and
    # "ratified" is an ordinary English word that occurs seven times in the reviewed
    # candidate of this very document -- in a table explaining what *may* be ratified. So
    # the bare-substring form of this check rejected the only value the ratifying task is
    # allowed to write: required tests 2 and 3 of that task could not both pass, on any
    # tree, and neither owner could fix it alone. The quotation is what the check is
    # about, so it asks for a quotation: `ratified` in a code span appears nowhere in the
    # candidate, while the word does. Round thirteen's harness sidestepped this by
    # inventing `ratified_at_w0_3`, which no external record asks for -- a ratification
    # the module could pass and the task would reject.
    quoted = f"`{status}`"
    if quoted not in markdown:
        problems.append(
            f"{REVIEW_MARKDOWN} does not quote the review_status {quoted!r} that "
            f"{REVIEW_JSON} declares; the two halves of one review disagree"
        )
    if ratified:
        candidate_markdown = _candidate_blob(root, REVIEW_MARKDOWN)
        if candidate_markdown is not None and quoted in _flat(
            candidate_markdown.decode("utf-8")
        ):
            problems.append(
                f"{REVIEW_JSON}: review_status {quoted!r} already appears in "
                f"{REVIEW_MARKDOWN} at the reviewed candidate, so requiring the "
                "Markdown to quote it proves nothing about ratification"
            )
        if status == UNRATIFIED_REVIEW_STATUS:
            problems.append(
                f"{REVIEW_JSON} declares ratified while review_status is still "
                f"{UNRATIFIED_REVIEW_STATUS!r}"
            )
        if REVIEW_DISCLAIMER in markdown:
            problems.append(
                f"{REVIEW_MARKDOWN} still tells the reader it is {REVIEW_DISCLAIMER!r} "
                "while the review declares itself ratified"
            )
    return problems


def _registry_state_problem(root: Path) -> str | None:
    """Compare the two external records by structure. ``None`` means they agree.

    The CP-00 row of the checkpoint registry states its state by citing, in a code span,
    the manifest key that holds it — `ratification_blocked` while blocked,
    `ratification` once ratified. Identifiers, not English: a row reading "not ratified"
    cannot be mistaken for one reading "ratified", which is exactly what the first form
    of this check got wrong.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return f"{CHECKPOINT_MANIFEST} is missing"
    external = manifest.get("ratified") is True
    rows = [
        line
        for line in (root / CHECKPOINT_REGISTRY).read_text(encoding="utf-8").splitlines()
        if line.startswith("| CP-00 ")
    ]
    if len(rows) != 1:
        return f"{CHECKPOINT_REGISTRY} does not carry exactly one CP-00 row"
    cited = {
        span for span in re.findall(r"`([^`]+)`", rows[0]) if span in REGISTRY_STATE_TOKENS
    }
    if len(cited) != 1:
        return (
            "the CP-00 registry row must cite exactly one manifest state key in a code "
            f"span, one of {sorted(REGISTRY_STATE_TOKENS)}; the row's prose is not read "
            f"and cannot carry the state. Row: {rows[0]}"
        )
    token = cited.pop()
    # Deliberately *not* also requiring the manifest to still carry a key of that name.
    # An unratified manifest has no `ratification` object and a ratified one may drop
    # `ratification_blocked` as spent history, so tying the comparison to key presence
    # would make it depend on whether history was kept — the ambient-state coupling this
    # module has had to remove twice already. The token is a state name from a closed
    # vocabulary; the comparison is between two states.
    if (token == RATIFIED_STATE_TOKEN) != external:
        return (
            f"{CHECKPOINT_REGISTRY} cites `{token}` for CP-00 while "
            f"{CHECKPOINT_MANIFEST} declares ratified={external}. A ratified checkpoint "
            f"cites `{RATIFIED_STATE_TOKEN}`; an unratified one cites "
            f"`{UNRATIFIED_STATE_TOKEN}`."
        )
    return None


def _undeclared_drift(root: Path) -> list[str]:
    """Reviewed-family drift that no admissible ratification record accounts for.

    One direction only — what changed without being declared. On its own this is not
    the policy: see :func:`_ratification_delta_problems`, which also requires the other
    direction, because a record that declares five reconciliations and performs one
    leaves nothing undeclared and would otherwise pass.
    """
    _, declared, problems = _ratification_record(root)
    licensed = frozenset() if problems else declared
    return sorted(set(_drifted_reviewed_paths(root)) - licensed)


def _unperformed_declarations(root: Path) -> list[str]:
    """Paths a valid record declares that are byte-identical to the candidate anyway.

    The other direction, and the one an independent negative probe found missing. A
    ratification record is a statement that these reconciliations were made; a declared
    path that never changed means the statement is false, whether by oversight or
    because the work was skipped and the record written anyway.
    """
    _, declared, problems = _ratification_record(root)
    if problems:
        return []
    return sorted(declared - set(_drifted_reviewed_paths(root)))


def _ratification_delta_problems(root: Path) -> list[str]:
    """The whole reviewed-family delta policy, both directions, in one answer.

    * every reviewed family byte-identical to the candidate, **except**
    * exactly the paths an admissible record declares — no more (undeclared drift) and
      no fewer (declared but not performed),
    * with `contracts/**`, `fixtures/**` and `scripts/**` untouchable regardless.
    """
    problems: list[str] = []
    _, declared, record_problems = _ratification_record(root)
    problems.extend(record_problems)

    immutable = _immutable_family_drift(root)
    if immutable:
        problems.append(
            "ratification does not reach these families and no record can license a "
            f"byte of them: {immutable}"
        )
    undeclared = _undeclared_drift(root)
    if undeclared:
        problems.append(
            "these reviewed artifacts differ from the candidate and no ratification "
            f"record accounts for them: {undeclared}"
        )
    unperformed = _unperformed_declarations(root)
    if unperformed:
        problems.append(
            "the ratification record declares these reconciliations and they were not "
            f"made — the files are byte-identical to the candidate: {unperformed}. "
            "Declaring the work is not doing it."
        )
    return problems


def _immutable_family_drift(root: Path) -> list[str]:
    """Drift in the three families ratification never reaches.

    Redundant with :func:`_undeclared_drift` while the ceiling holds, and stated
    separately anyway: the guarantee that `contracts/**`, `fixtures/**` and `scripts/**`
    are untouchable should not depend on reading the ceiling correctly.
    """
    return [
        path
        for path in _drifted_reviewed_paths(root)
        if path.startswith(IMMUTABLE_REVIEWED_PREFIXES)
    ]


def _reviewed_manifest_digest(root: Path) -> tuple[str, int]:
    """The checkpoint manifest's own `artifact_manifest_sha256` recipe, recomputed.

    For each tracked reviewed path in sorted order: the UTF-8 path bytes, then the raw
    32-byte SHA-256 of the file content — not its hex text.
    """
    tracked = sorted(
        _git(
            "-C",
            str(root),
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            "--",
            "contracts",
            "fixtures",
            "docs/architecture",
            "scripts",
            text=True,
            check=True,
        ).stdout.split("\n")
    )
    tracked = [path for path in tracked if path]
    running = hashlib.sha256()
    for relative in tracked:
        running.update(relative.encode("utf-8"))
        running.update(hashlib.sha256((root / relative).read_bytes()).digest())
    return running.hexdigest(), len(tracked)


#: Each way a root can be wrong, and the reason given when it is. Separate messages are
#: not decoration: a probe that only asserted "something raised" cannot tell one branch
#: from another, and an independent reviewer of round eight's submission removed a
#: branch and stayed green precisely because the surviving branch caught the same input
#: with a different message.
WRITE_REFUSAL_IS_THE_REPOSITORY = "it is the repository under review"
WRITE_REFUSAL_CONTAINS_THE_REPOSITORY = "it contains the repository under review"
WRITE_REFUSAL_INSIDE_THE_REPOSITORY = "it is inside the repository under review"
WRITE_REFUSAL_NOT_OURS = "it is not a throwaway directory this module created"


def _refuse_to_write_outside(root: Path, prefix: str) -> None:
    """Raise unless ``root`` is a throwaway this module made. **The safety guard.**

    Two helpers here run Git commands that write — :meth:`_CheckpointSandbox._git_write`
    drops paths from a sandbox's own index, and :meth:`_ManifestHistory._run` runs
    ``init``, ``add`` and ``commit``. Everything this task is allowed to claim rests on
    neither of them ever reaching the repository under review.

    **Round nine's blocker, and why this function exists at all.** The guard used to live
    inline in both places, byte-for-byte identical, and tested `root == repository or
    repository.is_relative_to(root)` — the target being the repository, or *containing*
    it. It never tested the direction that actually matters: the target being **inside**
    the repository. A directory under `REPOSITORY_ROOT` whose name happened to carry the
    `mkdtemp` prefix satisfied both asserted facts, and ``git -C`` walks up from there and
    finds the real `.git`. An independent reviewer used exactly that to drop
    `contracts/analysis/v1/README.md` — one of the immutable reviewed families — from the
    index. Nothing had ever pointed a root there, so the exposure was latent; the defect
    was the guard.

    The prefix branch was worse than untested: it was unreachable from the one probe that
    existed, which set the root to `REPOSITORY_ROOT` itself and so always tripped the
    first branch. Deleting the prefix check entirely left the suite green.

    All four branches are now distinct, carry distinct reasons, and are asserted
    individually against both callers by :class:`WritingCommandGuardTests` — which also
    asserts that no subprocess is spawned, so the guard is proved to run *before* the
    command rather than beside it.
    """
    resolved = root.resolve()
    repository = REPOSITORY_ROOT.resolve()
    if resolved == repository:
        reason = WRITE_REFUSAL_IS_THE_REPOSITORY
    elif repository.is_relative_to(resolved):
        reason = WRITE_REFUSAL_CONTAINS_THE_REPOSITORY
    elif resolved.is_relative_to(repository):
        reason = WRITE_REFUSAL_INSIDE_THE_REPOSITORY
    elif not resolved.name.startswith(prefix):
        reason = WRITE_REFUSAL_NOT_OURS
    else:
        return
    raise AssertionError(
        f"refusing to run a writing Git command against {resolved}: {reason}"
    )


class _CheckpointSandbox:
    """A throwaway working copy of the whole repository, object database included.

    Ratification probes have to answer questions about `git status`, about blobs at the
    candidate commit and about the external record all at once, so a partial copy will
    not do. **The invariant is that nothing here touches the repository under review**:
    the object database is copied, never shared, and every path any command is pointed at
    is inside :attr:`root`, which :meth:`_git_write` refuses to run without.

    Until round eight that invariant was stated as the stricter "no Git command that
    writes is ever run", and the strictness had a cost that only showed up at
    publication. Resetting to the frozen tree unlinks paths that are absent from it, and
    a *tracked* path cannot be unlinked without also leaving the index, so those were
    recorded in :attr:`unresettable` and every probe that needs a reset sandbox failed
    loudly. That is correct behaviour for an unresettable sandbox and the wrong rule: the
    moment the integrator commits this round's acceptance reports — which
    `docs/program/reviews/W0-QA-01.md` §11.12.6 tells them to do before ratifying — 26
    `RatificationRecordTests` die on a clean, unratified tree, and they are exactly the
    family certifying this round's repairs. A checkpoint would be tagged with none of
    them exercised. Narrowing the gate at publication was considered and rejected for the
    same reason.

    So the index of the sandbox's **own private copy** is now writable, through
    :meth:`_git_write`, guarded by :func:`_refuse_to_write_outside`. One arithmetic still
    serves both trees: `_digest_paths` is the recipe's own wording and is not
    special-cased anywhere.
    """

    #: Never copied: the live virtual environment, which is symlinked instead, and the
    #: object database, which is copied separately.
    NOT_COPIED = frozenset({".git", ".venv"})

    #: The `mkdtemp` prefix, and half of what :func:`_refuse_to_write_outside` checks.
    PREFIX = "w0-qa-01-checkpoint-"

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix=self.PREFIX))
        shutil.copytree(REPOSITORY_ROOT / ".git", self.root / ".git")
        # The whole tree, not a hand-listed subset. The candidate digest enumerates
        # every tracked path, so a sandbox that carried only the interesting
        # directories would make the recipe unrunnable rather than make the probe
        # meaningful — and a hand-listed subset silently rots as the repository grows.
        for entry in sorted(REPOSITORY_ROOT.iterdir()):
            if entry.name in self.NOT_COPIED:
                continue
            if entry.is_dir():
                shutil.copytree(entry, self.root / entry.name, symlinks=True)
            elif entry.is_file():
                shutil.copy2(entry, self.root / entry.name)
        (self.root / ".venv").symlink_to(REPOSITORY_ROOT / ".venv")
        # `.gitignore` ignores `.venv/` as a directory; here it is a symlink, which that
        # pattern does not match, so the sandbox would enumerate it as an untracked file
        # and the digest recipe would try to read a directory. Excluded in the sandbox's
        # own copied metadata — a plain file write, not a Git command — so the sandbox
        # enumerates exactly what the repository does.
        exclude = self.root / ".git/info/exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as handle:
            handle.write("\n.venv\n")
        self._pristine: dict[str, bytes] = {}
        #: The commit that froze the live `tested_candidate_digest`, the value it froze,
        #: and any path this sandbox could not return to that tree. Filled by
        #: :meth:`normalise_to_candidate`.
        self.frozen_commit: str | None = None
        self.frozen_digest: str | None = None
        self.unresettable: list[str] = []
        #: Whether this sandbox had to reach into history for a freeze. Recorded rather
        #: than hidden: a probe that wants to know which tree it is standing on can ask.
        self.recovered_freeze = self._ensure_a_frozen_round()

    def _ensure_a_frozen_round(self) -> bool:
        """Give the sandbox a frozen round to reset to when the live tree has none.

        **The failure this exists to remove.** `tested_candidate_digest: null` is the
        legitimate state of a round that has not been dispatched — the module says so in
        :func:`_tested_digest_problems` — and the live repository sits in it for as long
        as it takes to prepare the next round. Every probe in
        :class:`RatificationRecordTests` is about what may differ *from a frozen tree*,
        so on such a tree the family has nothing to measure. It did not go quiet: it went
        red. `_ratify_for_real` refuses to build a ratification on a digest no commit
        froze — the right refusal — and 122 tests then failed on a correct, unratified,
        between-rounds repository. A suite that cannot be green while the next round is
        being prepared cannot be the evidence for freezing it, which is the same
        no-executable-sequence shape round nine was voided over, one layer out.

        **Nothing is invented to remove it.** The refusal in `_ratify_for_real` stays
        exactly as it is; what changes is that the sandbox is given a real freeze to
        stand on. This repository has frozen nine rounds and Git keeps every one, so the
        newest manifest revision carrying a self-consistent freeze — the value at the top
        level and in the entry for that revision's own current round — is written into
        the sandbox's **private copy**, and the reset then proceeds exactly as it does
        when the live manifest carries one. The commit is real, the tree is real, and the
        digest is recomputed by the same recipe over the same paths.

        A recovery that quietly degraded into a fabrication would put every post-freeze
        probe back where round seven found them, so
        :meth:`SandboxResetTests.test_a_recovered_freeze_is_a_real_freeze` requires the
        recovered value to reproduce over the recovered commit's tree, and
        :meth:`SandboxResetTests.test_a_history_with_no_freeze_at_all_recovers_nothing`
        requires the recovery to report failure rather than guess when history holds no
        freeze. The live manifest is never read *through* this: `_tested_digest_problems`
        and `_post_freeze_delta_problems` still run against `REPOSITORY_ROOT` and still
        say so when the live value names no tree.
        """
        if _freeze_commit(self.root) is not None:
            return False
        recovered = self._the_newest_frozen_manifest()
        if recovered is None:
            return False
        (self.root / CHECKPOINT_MANIFEST).write_text(recovered, encoding="utf-8")
        return _freeze_commit(self.root) is not None

    def _the_newest_frozen_manifest(self) -> str | None:
        """The newest manifest revision that had a freeze in force, as text.

        Self-consistency is the whole filter: the top-level value, a single entry for
        that revision's own `current_round`, and the same value inside it. That is the
        shape :func:`_freeze_commit` walks for, so a revision this returns is one that
        function can resolve rather than one that merely carries a hex string.
        """
        history = _git(
            "-C", str(self.root), "log", "--format=%H", "--", CHECKPOINT_MANIFEST,
            text=True,
        ).stdout
        for commit in (line for line in history.split("\n") if line):
            blob = _git(
                "-C", str(self.root), "--no-replace-objects", "show",
                f"{commit}:{CHECKPOINT_MANIFEST}",
            )
            if blob.returncode != 0:
                continue
            text = blob.stdout.decode("utf-8")
            try:
                past = json.loads(text)
            except ValueError:
                continue
            digest = past.get("tested_candidate_digest")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                continue
            entries = [
                entry
                for entry in past.get("acceptance_rounds", [])
                if isinstance(entry, dict) and entry.get("round") == past.get("current_round")
            ]
            if len(entries) == 1 and entries[0].get("tested_candidate_digest") == digest:
                return text
        return None

    def _git_write(self, *arguments: str) -> None:
        """Run a Git command that writes, having proved it cannot reach the repository.

        Two independent things have to hold, and each has been found insufficient alone.

        **The path argument** is checked by :func:`_refuse_to_write_outside`, shared with
        :meth:`_ManifestHistory._run` rather than copied into it — an independent
        reviewer of round eight's submission found the copy carrying the original's blind
        spot, which is what a copied safety check is for.

        **The environment** is not checked at all here; it is :func:`_git`'s, and
        :func:`_git` constructs it. That division is deliberate. Round nine's form of
        this docstring said the environment was "sanitised too", meaning three
        discovery variables were deleted from the inherited one — and a reviewer walked
        around it with a ``HOME`` whose ``.gitconfig`` named ``core.fsmonitor``, which
        Git *executes*, taking three immutable-family files out of another repository's
        index while this guard passed cleanly and all 189 tests stayed green. A guard
        validates its argument; only measuring the destination establishes a property of
        the destination, and only an environment nobody outside this module contributed
        to makes that property hold for names nobody has thought of yet. See
        :func:`_allowlisted_env` and §11.16.
        """
        _refuse_to_write_outside(self.root, self.PREFIX)
        _git("-C", str(self.root.resolve()), *arguments, check=True)

    def normalise_to_candidate(self) -> None:
        """Put the sandbox into the pre-ratification state, whatever the host tree is.

        These probes are about the policy, not about today's repository. Without this
        the whole class would silently change meaning the moment `W0-INT-01` ratifies —
        half of it passing for the wrong reason and half failing for the wrong reason —
        which is exactly the ambient-state dependence that made the original
        `ratified is False` pin a trap. Reviewed files are rewritten from the candidate
        blob, anything added since is removed, and the external record is returned to
        `ratified: false` with no `ratification` object.
        """
        self._reset_to_the_frozen_tree()
        at_candidate = set(_candidate_reviewed_paths(self.root))
        for relative in sorted(set(_present_reviewed_paths(self.root)) - at_candidate):
            (self.root / relative).unlink(missing_ok=True)
        for relative in sorted(at_candidate):
            blob = _candidate_blob(self.root, relative)
            if blob is None:
                raise AssertionError(f"candidate blob unavailable for {relative}")
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file() or target.read_bytes() != blob:
                target.write_bytes(blob)
        manifest_path = self.root / CHECKPOINT_MANIFEST
        if manifest_path.is_file():
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["ratified"] = False
            document.pop("ratification", None)
            # The acceptance state is normalised too. Leaving the host's accepted round
            # in place would make every probe below mean something different depending
            # on whether the repository happened to be mid-ratification — the ambient
            # coupling this module has had to remove three times now.
            for field in ACCEPTANCE_DIGEST_FIELDS:
                document[field] = None
            for entry in document.get("acceptance_rounds", []):
                if isinstance(entry, dict) and entry.get("round") == document.get(
                    "current_round"
                ):
                    entry["verdict"] = None
                    entry["streams"] = {"automated": None, "manual": None}
                    entry["manual_report"] = None
                    entry["automated_report"] = None
                    for field in ACCEPTANCE_DIGEST_FIELDS:
                        entry[field] = ""
            for stream in ("manual", "automated"):
                record = document.get(f"{stream}_acceptance")
                if isinstance(record, dict):
                    record["status"] = "owed"
                    record["report_path"] = None
                    record["round"] = document.get("current_round")
            manifest_path.write_text(
                json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    def _reset_to_the_frozen_tree(self) -> None:
        """Return the whole sandbox to the tree whose digest the manifest froze.

        The probes below ask "is this the tree the acceptance streams judged?", and the
        answer must not depend on what the host working tree happens to be carrying —
        the fourth ambient-state coupling this module has had to remove. Without this,
        the very edit that fixes this module would sit in the sandbox's post-freeze
        delta and the *positive* probe would fail for a reason that has nothing to do
        with the policy it tests.

        Content is rewritten from the commit's blobs and strangers are unlinked. An
        untracked stranger needs nothing else; a *tracked* one must also leave the index,
        or `git ls-files --cached` keeps reporting it and `_digest_paths` — the recipe's
        own wording — keeps enumerating a path the frozen tree does not have. That
        deletion goes through :meth:`_git_write`, so it can only ever reach this
        sandbox's private index. Anything that still cannot be reset is recorded in
        :attr:`unresettable`, so a probe fails loudly rather than mysteriously; the list
        is no longer routinely non-empty, but it is the thing that would catch a reset
        this method got wrong.
        """
        commit = _freeze_commit(self.root)
        if commit is None:
            return
        blobs = _tree_blobs(self.root, commit)
        if blobs is None:
            return
        untracked = set(
            _git(
                "-C", str(self.root), "ls-files", "--others", "--exclude-standard",
                text=True, check=True,
            ).stdout.split("\n")
        )
        for relative, content in blobs.items():
            target = self.root / relative
            if not target.is_file() or target.read_bytes() != content:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        strangers = sorted(set(_digest_paths(self.root)) - set(blobs))
        tracked_strangers = [item for item in strangers if item not in untracked]
        if tracked_strangers:
            # Tracked and absent from the frozen tree: committed after the freeze. The
            # index of this sandbox's own copied object database is dropped for them, in
            # batches so a long list cannot overflow the argument limit.
            for start in range(0, len(tracked_strangers), 200):
                self._git_write(
                    "rm", "--cached", "--quiet", "--", *tracked_strangers[start : start + 200]
                )
        for relative in strangers:
            (self.root / relative).unlink(missing_ok=True)
        self.unresettable = sorted(set(_digest_paths(self.root)) - set(blobs))
        self.frozen_commit = commit
        manifest = json.loads(blobs[CHECKPOINT_MANIFEST].decode("utf-8"))
        self.frozen_digest = manifest.get("tested_candidate_digest")

    def __enter__(self) -> "_CheckpointSandbox":
        return self

    def __exit__(self, *_exc: object) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _remember(self, relative: str) -> None:
        if relative not in self._pristine:
            path = self.root / relative
            self._pristine[relative] = path.read_bytes() if path.is_file() else b""

    def edit(self, relative: str, marker: str = "\n<!-- ratification edit -->\n") -> None:
        """Append a visible marker, so the file drifts without becoming nonsense."""
        self._remember(relative)
        path = self.root / relative
        path.write_bytes(path.read_bytes() + marker.encode("utf-8"))

    def patch_json(self, relative: str, **fields: object) -> None:
        self._remember(relative)
        path = self.root / relative
        document = json.loads(path.read_text(encoding="utf-8"))
        document.update(fields)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def drop_json_key(self, relative: str, key: str) -> None:
        self._remember(relative)
        path = self.root / relative
        document = json.loads(path.read_text(encoding="utf-8"))
        document.pop(key, None)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def declare_ratification(
        self,
        paths: list[str],
        *,
        ratified: bool = True,
        task: str = RATIFYING_TASK,
        omit: tuple[str, ...] = (),
    ) -> None:
        """Write the external record the way `W0-INT-01` is expected to write it."""
        record: dict[str, object] = {
            "task": task,
            "decided_on": "2026-09-02",
            "decided_by": "repository owner, recorded by the program integrator",
            "reason": (
                "CP-00 ratification: set review.ratified and reconcile the three "
                "recorded point-in-time statements."
            ),
            "allowed_delta_paths": paths,
        }
        for field in omit:
            record.pop(field, None)
        self.patch_json(CHECKPOINT_MANIFEST, ratified=ratified, ratification=record)

    def set_registry_state(self, token: str | None, prose: str) -> None:
        """Rewrite the CP-00 registry row: a state token plus deliberate prose.

        `prose` exists so the probes can prove the English is never consulted — the
        combinations below pair a confirming token with denying prose and vice versa.
        """
        self._remember(CHECKPOINT_REGISTRY)
        path = self.root / CHECKPOINT_REGISTRY
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.startswith("| CP-00 "):
                cells = line.split("|")
                citation = f" see manifest `{token}`;" if token else ""
                cells[-2] = f" {prose};{citation} "
                lines[index] = "|".join(cells)
                break
        else:  # pragma: no cover - the registry always carries the row
            raise AssertionError("no CP-00 row to rewrite")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def reconcile(self, entry: dict) -> None:
        """Actually make one recorded reconciliation, the way ratification must."""
        self._remember(entry["path"])
        path = self.root / entry["path"]
        text = path.read_text(encoding="utf-8")
        stale = entry["stale"]
        flat = _flat(text)
        assert stale in flat, f"anchor missing before reconciliation: {entry['path']}"
        # Replace in place, tolerating the line wrapping the anchor may have crossed,
        # so the document keeps its structure — flattening it would quietly break the
        # Markdown table gates that read the same file.
        replacement = ""
        for needle in entry.get("new_text", ()):
            replacement = needle
        pattern = re.compile(r"\s+".join(re.escape(word) for word in stale.split()))
        text, count = pattern.subn(replacement or "the precondition is satisfied", text)
        assert count, f"anchor did not match in place: {entry['path']}"
        if entry.get("sentence_requires"):
            text += (
                "\n\nThe precondition is satisfied: `legacy-stage-name-map.json` carries "
                "62 legacy names over 31 alias-bearing declaration sites.\n"
            )
        path.write_text(text, encoding="utf-8")

    def update_state_document(
        self, replacement: str = "CP-00 is ratified and tagged"
    ) -> None:
        """Bring the third external record up to date, the way ratification must.

        Whitespace-tolerant as defence against a future rewrap, not as a description of
        today's document: `docs/program/CURRENT_STATE.md:16` carries the denial entirely
        on one line and that is its only occurrence. §11.16.7 corrected this sentence in
        the report and left the module's copy saying the opposite, which is the same
        defect one level down — a claim standing beside a check that does not make it.
        The flattening stays because a Markdown sentence is re-wrapped by any editor or
        formatter, and the day it wraps is the day an unmeasured check goes quiet; what
        keeps it honest is
        :meth:`RatificationRecordTests.test_the_state_document_denial_is_found_across_a_line_wrap`,
        which wraps the sentence in a sandbox copy and requires the check to still find
        it.
        """
        self._remember(PROGRAM_STATE_DOCUMENT)
        path = self.root / PROGRAM_STATE_DOCUMENT
        pattern = re.compile(
            r"\s+".join(re.escape(word) for word in STATE_DOCUMENT_DENIAL.split())
        )
        text, count = pattern.subn(replacement, path.read_text(encoding="utf-8"))
        assert count, f"no denial to update in {PROGRAM_STATE_DOCUMENT}"
        path.write_text(text, encoding="utf-8")

    def _retract(self, relative: str, claim: str, replacement: str) -> None:
        """Replace a claim in place, tolerating a line wrap it may have crossed."""
        self._remember(relative)
        path = self.root / relative
        pattern = re.compile(r"\s+".join(re.escape(word) for word in claim.split()))
        text, count = pattern.subn(replacement, path.read_text(encoding="utf-8"))
        assert count, f"no {claim!r} to retract in {relative}"
        path.write_text(text, encoding="utf-8")

    def _append(self, relative: str, addition: str) -> None:
        self._remember(relative)
        path = self.root / relative
        path.write_text(path.read_text(encoding="utf-8") + addition, encoding="utf-8")

    def write_checkpoint_bundle(self) -> None:
        """Write the eight evidence deliverables, the way `W0-INT-01` must.

        Called **after** the reconciliations and the document edits, because the contract
        manifest records the reviewed-family digest of the tree that is actually
        published: a bundle written first would describe the tree before ratification
        touched it.

        The bodies are written out here rather than generated from
        :data:`CHECKPOINT_DELIVERABLES`. A harness that derived its content from the same
        table the check reads would go green on a requirement deleted from that table,
        which is the defect class :class:`TableExpectationTests` exists for one level up.
        """
        manifest = json.loads(
            (self.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        number = manifest["current_round"]
        digest = _reviewed_manifest_digest(self.root)[0]
        disposition = manifest["runtime_fields"]

        def sha(relative: str) -> str:
            return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

        merged = "\n".join(
            f"- `{task}` at `{commit}`"
            for task, commit in sorted(manifest["integrated_w03_tasks"].items())
        )
        risks = "\n".join(
            f"- `{name}` carried forward."
            for name in sorted(manifest["architecture_defer"])
            + sorted(manifest["open_inputs_carried_forward"])
            + sorted(manifest["open_escalations"])
        )
        cases = "\n".join(
            f"| {case} | PASS | walked as written; no defect found |"
            for case in _manual_case_ids(self.root)
        )
        bodies = {
            "checkpoint-report.md": (
                f"# CP-00 checkpoint report\n\n"
                f"Tag: `{CHECKPOINT_TAG}`\n"
                f"Candidate commit: `{REVIEWED_CANDIDATE_COMMIT}`\n"
                f"Frozen contract versions: `{CANDIDATE_CONTRACT_VERSION}` for the "
                f"domain, analysis and events families.\n\n"
                f"## Merged tasks\n\n{merged}\n\n"
                f"## Evidence\n\n"
                f"- hashes and lock digests: `contract-manifest.yaml`\n"
                f"- manual acceptance: `manual-test-report.md`\n"
                f"- automated acceptance: `automated-summary.txt`\n"
                f"- deferred scopes and risks: `known-risks.md`\n"
                f"- rollback: `restore-or-rollback-note.md`\n"
                f"- migration head: `migration-head.txt`\n"
                f"- build information: `build-info.json`\n"
            ),
            "contract-manifest.yaml": (
                f"checkpoint: CP-00\n"
                f"tag: {CHECKPOINT_TAG}\n"
                f"candidate_commit: {REVIEWED_CANDIDATE_COMMIT}\n"
                f"migration_head: none\n"
                f"contract_versions:\n"
                f"  domain: {CANDIDATE_CONTRACT_VERSION}\n"
                f"  analysis: {CANDIDATE_CONTRACT_VERSION}\n"
                f"  events: {CANDIDATE_CONTRACT_VERSION}\n"
                f"artifact_manifest_sha256: {digest}\n"
                f"file_hashes:\n"
                f"  contracts/analysis/v1/stage-registry.json: "
                f"{sha('contracts/analysis/v1/stage-registry.json')}\n"
                f"  contracts/analysis/v1/legacy-stage-name-map.json: "
                f"{sha('contracts/analysis/v1/legacy-stage-name-map.json')}\n"
                f"  fixtures/golden/selection.json: "
                f"{sha('fixtures/golden/selection.json')}\n"
                f"dependency_locks:\n"
                f"  requirements/validation.in: {sha('requirements/validation.in')}\n"
                f"  requirements/validation.lock: {sha('requirements/validation.lock')}\n"
            ),
            "automated-summary.txt": (
                f"CP-00 automated acceptance, round {number}: PASS\n"
                f"Suite: python -m unittest discover -s tests/contract\n"
            ),
            "manual-test-report.md": (
                f"# CP-00 manual acceptance\n\n"
                f"tester: independent CP-00 manual tester\n"
                f"started_at: 2026-09-04T09:00:00Z\n"
                f"finished_at: 2026-09-04T11:20:00Z\n"
                f"candidate_commit: {REVIEWED_CANDIDATE_COMMIT}\n"
                f"backend_runtime: {disposition}\n"
                f"frontend_runtime: {disposition}\n\n"
                f"| Case | Verdict | Actual result |\n|---|---|---|\n{cases}\n"
            ),
            "migration-head.txt": "none\n",
            "build-info.json": json.dumps(
                {
                    "checkpoint": "CP-00",
                    "candidate_commit": REVIEWED_CANDIDATE_COMMIT,
                    "interpreter": "python3.12 (.venv/bootstrap)",
                    "runtime": disposition,
                },
                indent=2,
            )
            + "\n",
            "known-risks.md": f"# CP-00 known risks and deferred scopes\n\n{risks}\n",
            "restore-or-rollback-note.md": (
                f"# CP-00 restore or rollback\n\n"
                f"Before the tag: revert the evidence commit and reopen the failed "
                f"owner task.\n"
                f"After the tag `{CHECKPOINT_TAG}`: never move it. The accepted "
                f"candidate to restore to is `{REVIEWED_CANDIDATE_COMMIT}`; a "
                f"replacement checkpoint needs a new registry version.\n"
            ),
        }
        for name, body in bodies.items():
            relative = ACCEPTANCE_EVIDENCE_PREFIX + name
            self._remember(relative)
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    def recompute_manifest_digest(self) -> None:
        """Bring `artifact_manifest_sha256` up to the tree ratification just produced.

        Ratification edits five files inside `docs/architecture/**`, one of the four
        families that digest covers, so the value the record carried before the act
        describes a tree that no longer exists.
        :meth:`RatificationRecordTests.test_the_manifest_digest_describes_the_tree_it_manifests`
        reads it straight off the live repository, so a publication that skipped this
        step would red the very suite it has to pass — and a harness that skipped it
        would build a "fully ratified tree" that the real one cannot be, which is how a
        reachability proof stops proving reachability.

        Ordered the way the digest rule is ordered: structure first, then compute, then
        write only the value. It is called after the last `docs/architecture/**` write
        and before the acceptance digests are sealed, so the manifest bytes it changes
        are inside the tree `evidence_bundle_digest` then covers.
        """
        digest, count = _reviewed_manifest_digest(self.root)
        self.patch_json(
            CHECKPOINT_MANIFEST, artifact_manifest_sha256=digest, artifact_count=count
        )

    def publish_program_documents(self) -> None:
        """Retract the three program claims ratification is required to retract."""
        wave = "docs/program/waves/W0.3_ratification_integration.md"
        self._retract(
            wave, "`W0-INT-01` is blocked", "`W0-INT-01` is accepted and integrated"
        )
        self._retract(
            wave,
            "| `W0-INT-01` | blocked |",
            "| `W0-INT-01` | accepted and integrated |",
        )
        self._append(
            wave,
            "\n## Next unlocked tasks\n\nCP-00 is ratified and tagged; the S01 "
            "repository-foundation preparation tasks are unlocked.\n",
        )
        stage = "docs/stages/S00_architecture_and_behavior_freeze.md"
        self._remember(stage)
        path = self.root / stage
        path.write_text(
            path.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8"
        )
        self._append(
            stage,
            "\n## Next stage\n\nCP-00 is accepted; the S01 repository-foundation "
            "preparation tasks are unlocked.\n",
        )
        self._retract(
            "docs/INDEX.md", "specified; blocked on acceptance", "accepted and integrated"
        )

    def update_acceptance_record(self) -> None:
        """Write the round's verdict into the acceptance record, as its landing requires.

        The row for *this* round is replaced; every other row is left exactly as it is.
        The record is a history, and a publication that rewrote it would be erasing the
        failed rounds that explain why this one is the tenth -- but appending
        unconditionally is not the way to preserve them. The acceptance record carries a
        placeholder row for the round about to be frozen ("not frozen; the freeze is the
        step after ..."), so appending produced *two* rows for the same round, and the
        probe that removes the round's row with ``count=1`` then deleted the placeholder
        and left the verdict standing -- so the negative case it needed was never built,
        and freezing the round by the recorded procedure went red on a tree nobody had
        done anything wrong to. Round nine escaped it only because its table stopped at
        round eight.
        """
        manifest = json.loads(
            (self.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        number = manifest["current_round"]
        self._remember(ACCEPTANCE_RECORD)
        path = self.root / ACCEPTANCE_RECORD
        lines = path.read_text(encoding="utf-8").splitlines()
        rows = [
            index
            for index, line in enumerate(lines)
            if re.match(r"^\|\s*\d+\s*\|", line)
        ]
        assert rows, f"{ACCEPTANCE_RECORD} carries no round table to extend"
        verdict = f"| {number} | **PASS** | **PASS** — 6/6 | recorded in the manifest |"
        mine = [
            index
            for index in rows
            if re.match(rf"^\|\s*{number}\s*\|", lines[index])
        ]
        assert len(mine) <= 1, (
            f"{ACCEPTANCE_RECORD} already carries {len(mine)} rows for round {number}; "
            "the record cannot say two things about one round"
        )
        if mine:
            lines[mine[0]] = verdict
        else:
            lines.insert(rows[-1] + 1, verdict)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def close_task_banners(self) -> None:
        """Close the ratifying task's banner, and one other task's, as ratification may."""
        self._retract(
            RATIFYING_TASK_FILE,
            RATIFYING_TASK_BANNER_DENIAL,
            f"ratified and published as `{CHECKPOINT_TAG}`",
        )
        other = "docs/program/tasks/W0-CLN-01.md"
        self._remember(other)
        path = self.root / other
        text = path.read_text(encoding="utf-8")
        banner, _rest = _banner_split(text)
        assert banner, f"{other} carries no status banner to close"
        path.write_text(
            text.replace(banner, banner + f"> Closed at CP-00 `{CHECKPOINT_TAG}`.\n", 1),
            encoding="utf-8",
        )

    def touch_without_reconciling(self, entry: dict) -> None:
        """Change the bytes and leave every stale claim exactly where it was."""
        self._remember(entry["path"])
        path = self.root / entry["path"]
        path.write_text(
            path.read_text(encoding="utf-8") + "\n<!-- reviewed at ratification -->\n",
            encoding="utf-8",
        )

    def accept_round(
        self,
        *,
        verdict: str = "PASS",
        streams: tuple[str, str] = ("PASS", "PASS 6/6"),
        reports: bool = True,
        stream_status: str = "PASS",
    ) -> None:
        """Record a passing current round with primary reports that exist on disk."""
        self._remember(CHECKPOINT_MANIFEST)
        path = self.root / CHECKPOINT_MANIFEST
        manifest = json.loads(path.read_text(encoding="utf-8"))
        number = manifest["current_round"]
        report_paths = {}
        for stream in ("manual", "automated"):
            relative = f"artifacts/checkpoints/CP-00/{stream}-report-round-{number}.md"
            report_paths[stream] = relative if reports else None
            if reports:
                target = self.root / relative
                self._remember(relative)
                target.write_text(f"# {stream} report round {number}\n", encoding="utf-8")
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == number:
                entry["verdict"] = verdict
                entry["streams"] = {"automated": streams[0], "manual": streams[1]}
                entry["manual_report"] = report_paths["manual"]
                entry["automated_report"] = report_paths["automated"]
        for stream in ("manual", "automated"):
            manifest[f"{stream}_acceptance"] = {
                "status": stream_status,
                "round": number,
                "report_path": report_paths[stream],
                "history": manifest.get(f"{stream}_acceptance", {}).get("history", []),
            }
        path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def seal_digests(self, tested: str | None = None, evidence: str | None = None) -> None:
        """Write both digests at the top level and into the current round.

        The default `tested` is deliberately a value no commit ever froze, so a probe
        that forgets to pass the real one fails instead of quietly certifying a tree
        that never existed.
        """
        self._remember(CHECKPOINT_MANIFEST)
        path = self.root / CHECKPOINT_MANIFEST
        manifest = json.loads(path.read_text(encoding="utf-8"))
        number = manifest["current_round"]
        tested_value = tested or ("c" * 64)
        manifest["tested_candidate_digest"] = tested_value
        manifest["evidence_bundle_digest"] = evidence if evidence is not None else ""
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == number:
                entry["tested_candidate_digest"] = tested_value
                entry["evidence_bundle_digest"] = manifest["evidence_bundle_digest"]
        path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if evidence is None:
            computed = _acceptance_digest(self.root)
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["evidence_bundle_digest"] = computed
            for entry in manifest["acceptance_rounds"]:
                if entry.get("round") == number:
                    entry["evidence_bundle_digest"] = computed
            path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

    def rewrite(self, relative: str, old: str, new: str) -> None:
        """Replace a literal inside a sandbox file, remembering the original bytes."""
        self._remember(relative)
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} is not in {relative}"
        path.write_text(text.replace(old, new), encoding="utf-8")

    def restore_one(self, relative: str) -> None:
        """Put a single remembered path back, leaving the rest of the mutation alone."""
        payload = self._pristine.pop(relative)
        path = self.root / relative
        if payload:
            path.write_bytes(payload)
        elif path.is_file():
            path.unlink()

    def restore(self) -> None:
        for relative, payload in self._pristine.items():
            path = self.root / relative
            if payload:
                path.write_bytes(payload)
            elif path.is_file():
                path.unlink()
        self._pristine.clear()


class _MutableCopy:
    """A throwaway copy of the reviewed trees, for one mutation.

    The candidate is never written. Everything happens under ``tempfile.mkdtemp()`` and
    is removed in ``close()``. ``.venv`` is symlinked so a documented command's
    ``.venv/bootstrap/bin/python`` prefix resolves from the copy's own root.
    """

    def __init__(self, subtrees: tuple[str, ...] = ("contracts",)) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="w0-qa-01-mutation-"))
        for subtree in subtrees:
            shutil.copytree(REPOSITORY_ROOT / subtree, self.root / subtree)
        (self.root / ".venv").symlink_to(REPOSITORY_ROOT / ".venv")

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def load(self, relative: str) -> object:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def store(self, relative: str, document: object) -> None:
        (self.root / relative).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def run_gate(self, letter: str):
        overrides = (
            {"GIT_DIR": str(REPOSITORY_ROOT / ".git")}
            if letter in GATE_NEEDS_OBJECT_STORE
            else None
        )
        return _run_shell(_documented_analysis_gate(letter), self.root, overrides)

    def run_block(self, script: str):
        return _run_shell(script, self.root)


class _ManifestHistory:
    """A throwaway Git repository whose manifest has a real, scripted history.

    **Why this exists.** Every other probe in this module runs where the freeze commit
    *is* `HEAD`: the live repository has one commit that froze the digest and nothing
    after it, and the sandboxes copy a tree and never commit. So "the oldest consecutive
    commit carrying the value" and "the newest commit carrying the value" name the same
    commit in every one of them, and :func:`_freeze_commit` with ``freeze = commit``
    replaced by ``return commit`` passed all 159 tests. That mutant was the only survivor
    of seventeen in round eight's independent review, and the degeneracy that hid it is
    the same one §11.11 claims to have removed: a probe that cannot distinguish the thing
    it is named after.

    Real commits are the only way to separate the two, and this repository may not gain
    any — so the history is built somewhere else entirely: ``git init`` in a
    :func:`tempfile.mkdtemp`, commits made there under an explicit throwaway identity,
    and the directory removed in ``tearDown``. :meth:`_run` refuses any root that is, or
    contains, the repository under review, and any root this class did not create.
    """

    PREFIX = "w0-qa-01-history-"

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix=self.PREFIX))
        (self.root / CHECKPOINT_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
        self._run("init", "--quiet", "--initial-branch=history")
        self._run("config", "user.email", "w0-qa-01@example.invalid")
        self._run("config", "user.name", "W0-QA-01 freeze-history probe")

    def _run(self, *arguments: str) -> str:
        """Every Git command here writes — ``init``, ``add``, ``commit`` — so the same
        guard applies, and it is the *same function*, not a second copy of it.

        The environment is sanitised the same way :meth:`_CheckpointSandbox._git_write`
        is now — see its docstring. This class builds a whole repository from ``init``
        onward, so a hostile ``GIT_DIR`` here would not edit an existing repository's
        index quietly; it would make every command in this class address that
        repository from the start.
        """
        _refuse_to_write_outside(self.root, self.PREFIX)
        return _git(
            "-C", str(self.root.resolve()), *arguments, text=True, check=True
        ).stdout

    def write(self, document: dict, files: dict[str, str] | None = None) -> None:
        """Put a manifest, and optionally other files, in the working tree."""
        (self.root / CHECKPOINT_MANIFEST).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        for relative, text in (files or {}).items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def commit(
        self, message: str, document: dict, files: dict[str, str] | None = None
    ) -> str:
        self.write(document, files)
        self._run("add", "-A")
        self._run("commit", "--quiet", "-m", message)
        return self.head()

    def head(self) -> str:
        return self._run("rev-parse", "HEAD").strip()

    def manifest_commits(self) -> list[str]:
        """Every commit that touched the manifest, oldest first."""
        listing = self._run("log", "--format=%H", "--reverse", "--", CHECKPOINT_MANIFEST)
        return [line for line in listing.split("\n") if line]

    def oldest_manifest_commit(self) -> str:
        return self.manifest_commits()[0]

    def seal(self, **shape: object) -> str:
        """Structure first, then compute, then write only the value.

        The recipe blanks the field being computed, so the digest of a tree does not
        depend on the value about to be written into it — which is what makes a freeze
        commit recomputable at all, and it is the ordering rule this task has had to
        relearn: never write a digest before the structure it covers is final. The
        document is put in the working tree with the field unset, the digest is taken
        over that tree, and only the value is written afterwards.
        """
        self.write(_history_manifest(None, **shape))
        return _acceptance_digest(self.root, "tested_candidate_digest")

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _history_manifest(
    digest: str | None,
    *,
    number: int = 5,
    rounds: tuple[int, ...] = (4, 5),
    verdict: str | None = None,
    note: object = None,
) -> dict:
    """A minimal manifest of the shape :func:`_freeze_commit` reads.

    ``note`` carries nothing the walk reads; it exists so consecutive revisions can
    differ in bytes while carrying the same digest, which is the case the deep-history
    probe needs and `git commit` otherwise refuses to create.
    """
    return {
        "checkpoint": "CP-00",
        "ratified": False,
        "revision_note": note,
        "current_round": number,
        "tested_candidate_digest": digest,
        "evidence_bundle_digest": None,
        "acceptance_rounds": [
            {
                "round": item,
                "verdict": verdict if item == number else "FAIL",
                "tested_candidate_digest": digest if item == number else "",
                "evidence_bundle_digest": "",
            }
            for item in rounds
        ],
    }


class ACandidateIntegrityTests(unittest.TestCase):
    """The tree under test is the commit the report certifies, byte for byte.

    Named to sort first: if this fails, every other result in this module describes some
    other tree and the review report is void.

    One narrow exception exists, and it is the whole subject of
    :class:`RatificationRecordTests`. Ratification is recorded *in* the artifact it
    ratifies, so `W0-INT-01` cannot do its job without changing files inside
    `docs/architecture/**`. That is a declared act, not drift — but only when an external
    record says so, names the files, and stays inside the ceiling this module pins.
    Everything else, in every family, is still drift and still a failure.
    """

    def test_the_candidate_file_set_is_the_one_this_report_describes(self) -> None:
        reviewed = _candidate_reviewed_paths(REPOSITORY_ROOT)
        # The candidate is immutable, so its reviewed file count is a fixed number. A
        # different count means a different tree, not a looser check.
        self.assertEqual(
            len(reviewed),
            100,
            "the candidate's reviewed file set is not the one this report describes",
        )

    def test_the_three_untouchable_families_are_byte_identical(self) -> None:
        """`contracts/**`, `fixtures/**`, `scripts/**` — no record can license a byte."""
        self.assertEqual(
            _immutable_family_drift(REPOSITORY_ROOT),
            [],
            "ratification does not reach these families; any difference from the "
            "candidate voids the report",
        )

    def test_the_reviewed_delta_is_exactly_what_is_declared(self) -> None:
        """Both directions: nothing undeclared changed, and nothing declared was skipped."""
        external_ratified, declared, _ = _ratification_record(REPOSITORY_ROOT)
        self.assertEqual(
            _ratification_delta_problems(REPOSITORY_ROOT),
            [],
            f"record ratified={external_ratified}, declared={sorted(declared)}, "
            f"observed drift={_drifted_reviewed_paths(REPOSITORY_ROOT)}",
        )

    def test_recorded_analysis_hashes_are_reproducible(self) -> None:
        """The two artifacts the report names by hash still hash to those values."""
        expected = {
            f"{ANALYSIS}/stage-registry.json": (
                "2c7f952bd7e21d2f6b1015d759476d38126d2ed3b021202a4065a6384dfed1a5"
            ),
            f"{ANALYSIS}/legacy-stage-name-map.json": (
                "df999f88b445c0b6ed096b157841da4787cac397b4f4c05a75628f84f9eba3a3"
            ),
            f"{ANALYSIS}/legacy-stage-map.json": (
                "7ba0c9c8febeabac4d1da4b7e2ff417e9f534c93976c8690b8fee44e65f29b07"
            ),
        }
        actual = {
            relative: hashlib.sha256(
                (REPOSITORY_ROOT / relative).read_bytes()
            ).hexdigest()
            for relative in expected
        }
        self.assertEqual(actual, expected)


class DocumentedAnalysisGateTests(unittest.TestCase):
    """Gates A-D are invoked as written. A gate that cannot run is a failed review."""

    def test_all_four_gates_are_recorded_as_executable_blocks(self) -> None:
        for letter in "ABCD":
            with self.subTest(gate=letter):
                body = _documented_analysis_gate(letter)
                self.assertIn(
                    ".venv/bootstrap/bin/python",
                    body,
                    "the gate no longer names the provisioned validator interpreter",
                )

    def test_bootstrap_interpreter_the_gates_name_is_present(self) -> None:
        self.assertTrue(
            BOOTSTRAP_PYTHON.is_file(),
            f"{BOOTSTRAP_PYTHON} is missing; every documented gate names it, so none of "
            "them can be executed as documented",
        )

    def _assert_gate_passes(self, letter: str) -> str:
        overrides = (
            {"GIT_DIR": str(REPOSITORY_ROOT / ".git")}
            if letter in GATE_NEEDS_OBJECT_STORE
            else None
        )
        result = _run_shell(
            _documented_analysis_gate(letter), REPOSITORY_ROOT, overrides
        )
        self.assertEqual(
            result.returncode,
            0,
            f"documented Gate {letter} did not execute as written.\n"
            f"stdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}",
        )
        self.assertIn(GATE_MARKERS[letter], result.stdout)
        return result.stdout

    def test_gate_a_name_level_alias_map_structure(self) -> None:
        stdout = self._assert_gate_passes("A")
        self.assertIn("62 unique names", stdout)
        self.assertIn("293 observations", stdout)
        self.assertIn("31/31 alias-bearing sites", stdout)

    def test_gate_b_every_evidence_locator_resolves(self) -> None:
        stdout = self._assert_gate_passes("B")
        self.assertIn("293/293 locators resolve", stdout)

    def test_gate_c_independent_reviewer_checks(self) -> None:
        stdout = self._assert_gate_passes("C")
        self.assertIn("9/9 stages", stdout)
        self.assertIn("11/11 exclusion ids", stdout)

    def test_gate_d_owner_decisions_transferred(self) -> None:
        stdout = self._assert_gate_passes("D")
        self.assertIn("all 9 creation triggers", stdout)
        self.assertIn("RC-02 beats RC-05", stdout)

    def test_documented_analysis_command_block_runs_clean(self) -> None:
        """The `## Gates` command list, including the standalone validator run."""
        blocks = [
            body
            for heading, body in _fenced_blocks(ANALYSIS_README)
            if heading == "## Gates"
        ]
        self.assertEqual(len(blocks), 1)
        result = _run_shell(blocks[0], REPOSITORY_ROOT)
        self.assertEqual(
            result.returncode,
            0,
            f"the documented analysis command block failed: {result.stderr.strip()}",
        )
        self.assertIn("PASS", result.stdout)

    def test_documented_negative_examples_are_rejected(self) -> None:
        """The README's prose claim about the three `*.invalid.json` fixtures."""
        from jsonschema import Draft202012Validator

        pairs = {
            "result-package.missing-attempt-authority.invalid.json": (
                "result-package.schema.json"
            ),
            "stage-result.failed-missing-error.invalid.json": "stage-result.schema.json",
            "stage-result.succeeded-with-error.invalid.json": "stage-result.schema.json",
        }
        present = sorted(
            path.name
            for path in (REPOSITORY_ROOT / ANALYSIS / "examples").glob("*.invalid.json")
        )
        self.assertEqual(present, sorted(pairs))
        for example, schema in pairs.items():
            with self.subTest(example=example):
                validator = Draft202012Validator(_load(f"{ANALYSIS}/{schema}"))
                errors = list(
                    validator.iter_errors(_load(f"{ANALYSIS}/examples/{example}"))
                )
                self.assertTrue(errors, f"{example} was accepted by {schema}")


class DocumentedNeighbourGateTests(unittest.TestCase):
    """The domain, event and golden families document their own gates. Run those too."""

    def test_domain_documented_blocks(self) -> None:
        for index, block in enumerate(_documented_blocks(DOMAIN_README)):
            with self.subTest(block=index):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"domain block {index} failed: {result.stderr.strip()}",
                )

    def test_event_documented_blocks_including_the_declared_residue(self) -> None:
        blocks = _documented_blocks(EVENTS_README)
        self.assertEqual(len(blocks), 6, "the event README's gate list changed shape")
        expected_exit = {index: 0 for index in range(len(blocks))}
        # The fifth block is documented as exiting 1 and reporting exactly the negative
        # fixture. It is a declared residue, not a defect, and is asserted as such.
        expected_exit[4] = 1
        for index, block in enumerate(blocks):
            with self.subTest(block=index):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    expected_exit[index],
                    f"event block {index}: {result.stdout.strip()} "
                    f"{result.stderr.strip()}",
                )
                if index == 4:
                    self.assertIn("legacy-schema-version.invalid.json", result.stderr)
                    self.assertEqual(
                        1,
                        result.stderr.count("contracts/"),
                        "the un-excluded sweep must report exactly one file",
                    )

    def test_golden_documented_blocks(self) -> None:
        blocks = _documented_blocks(SELECTION_MD)
        self.assertEqual(len(blocks), 2)
        for index, block in enumerate(blocks):
            with self.subTest(block=index):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"golden block {index} failed: {result.stderr.strip()}",
                )
                self.assertNotIn("False", result.stdout)
        self.assertIn("U-05 PASS", _run_shell(blocks[1], REPOSITORY_ROOT).stdout)

    def test_architecture_documented_gates(self) -> None:
        lines = _read(LINT_RULES_MD).splitlines()
        blocks: list[tuple[str, str]] = []
        label = None
        index = 0
        while index < len(lines):
            match = re.match(r"\*\*(GATE-[A-F])\*\*", lines[index])
            if match:
                label = match.group(1)
            if lines[index].startswith("```bash"):
                body: list[str] = []
                index += 1
                while index < len(lines) and not lines[index].startswith("```"):
                    body.append(lines[index])
                    index += 1
                if label is not None:
                    blocks.append((label, "\n".join(body) + "\n"))
            index += 1
        self.assertEqual(
            sorted({label for label, _ in blocks}),
            ["GATE-A", "GATE-B", "GATE-C", "GATE-D", "GATE-E", "GATE-F"],
            "the architecture specification no longer records all six gates",
        )
        declared = _ratification_record(REPOSITORY_ROOT)[1]
        for position, (label, block) in enumerate(blocks):
            with self.subTest(gate=label, position=position):
                result = _run_shell(block, REPOSITORY_ROOT)
                if result.returncode == 0:
                    continue
                # The one admissible failure. GATE-F's strict form asserts that nothing
                # under docs/architecture is dirty except the two lint-rule files that
                # `W0-ARC-02` owned; it is a claim about *that* task's write boundary,
                # made against the working tree. A ratification edit in progress dirties
                # other files in the same directory and trips it. The gate is not
                # skipped and not weakened: it must still fail for no reason other than
                # the declared ratification delta, and the reported paths must be a
                # subset of it.
                reported = {
                    line.strip().strip("'\"")
                    for line in re.findall(r"'docs/architecture/[^']+'", result.stderr)
                }
                self.assertTrue(
                    reported and reported <= set(declared),
                    f"{label} block {position} failed for something other than the "
                    f"declared ratification delta.\nreported: {sorted(reported)}\n"
                    f"declared: {sorted(declared)}\nstderr: {result.stderr.strip()}",
                )


class ForbiddenNameSweepControlTests(unittest.TestCase):
    """**B3.** The `ID-01`/`ALR-25` sweeps had no negative control at all.

    Four mutations each left the whole suite green: `FORBIDDEN_VERSION_KEYS` emptied,
    `FORBIDDEN_AUTHORITY_KEYS` emptied, :func:`_object_keys` not descending into lists,
    and :func:`_declared_properties` not yielding `required` entries. All four are
    load-bearing — the live helpers find `schema_version` at depth inside a list and as
    a `required` entry, and the mutants do not — but nothing anywhere planted a
    forbidden name and required *this module's* sweep to find it. `MutationTests` rows
    7-9 do plant keys, and then assert the **documented gates** and the **owning
    schemas** reject them, which is a statement about the contract family, not about
    this module's own sweep. A sweep with no negative control reports `{}` for the same
    reason an empty sweep does.

    Every planted document below reaches the forbidden name by exactly one *shape*, so
    a document carrying it everywhere cannot pass for a document carrying it once. What
    that does **not** give — and what this docstring and §11.16.7 claimed until round
    eleven — is one route per branch. It is false for two of the six rows: a name
    declared as a `properties` member is also an object key at that depth, so
    :func:`_object_keys` finds it on its own and :func:`_declared_properties` is never
    consulted.

    Four rows do isolate a branch, two each way, and
    :meth:`test_each_route_helper_reaches_its_own_route` has carried the correct matrix
    all along: the two object-key rows isolate :func:`_object_keys`, because a bare key
    at depth is not a declaration either helper reads as one; the two `required` rows
    isolate :func:`_declared_properties`, because a `required` entry is a list *value*
    and no object key anywhere names it. Round eleven's form of this paragraph said
    "only the two `required` rows isolate a branch", which understated its own coverage
    and disagreed with the matrix twenty lines below it. Corrected in round twelve; the
    matrix is the normative statement and this prose now repeats it rather than
    competing with it.

    The consequence was measurable: `_declared_properties`' `properties` branch reduced
    to ``if False:`` left all 244 tests green.
    :meth:`test_each_route_helper_reaches_its_own_route` states the real matrix and
    asserts each helper directly, which is the only way to drive a branch whose output
    another helper duplicates.
    """

    #: The routes, and a document that reaches the forbidden name only by that route.
    @staticmethod
    def _only_via(route: str, name: str) -> dict:
        if route == "an object key at depth inside a list":
            return {
                "contract_version": CANDIDATE_CONTRACT_VERSION,
                "oneOf": [{"then": {"examples": [{"payload": {name: "x"}}]}}],
            }
        if route == "an object key at depth inside nested objects":
            return {"a": {"b": {"c": {name: "x"}}}}
        if route == "a properties member":
            return {"$defs": {"envelope": {"properties": {name: {"type": "string"}}}}}
        if route == "a properties member reached through a list":
            return {"allOf": [{"properties": {name: {"type": "string"}}}]}
        if route == "a required entry":
            return {"$defs": {"envelope": {"required": ["contract_version", name]}}}
        if route == "a required entry reached through a list":
            return {"anyOf": [{"required": [name]}]}
        raise AssertionError(route)

    ROUTES = (
        "an object key at depth inside a list",
        "an object key at depth inside nested objects",
        "a properties member",
        "a properties member reached through a list",
        "a required entry",
        "a required entry reached through a list",
    )

    def test_the_forbidden_tables_are_not_empty(self) -> None:
        """An empty table makes every sweep below report nothing, forever."""
        self.assertEqual(FORBIDDEN_VERSION_KEYS, frozenset({"version", "schema_version"}))
        self.assertEqual(
            FORBIDDEN_AUTHORITY_KEYS,
            frozenset({"authority_token", "fencing_token", "fence_token"}),
        )

    def test_the_sweep_finds_a_planted_name_by_every_route_it_claims_to_cover(
        self,
    ) -> None:
        for forbidden in (FORBIDDEN_VERSION_KEYS, FORBIDDEN_AUTHORITY_KEYS):
            for name in sorted(forbidden):
                for route in self.ROUTES:
                    with self.subTest(name=name, route=route):
                        planted = self._only_via(route, name)
                        self.assertEqual(
                            _forbidden_name_hits(planted, forbidden),
                            [name],
                            f"the sweep does not find {name!r} as {route}, so §4's "
                            "claim to cover that route is not measured anywhere",
                        )

    def test_each_route_helper_reaches_its_own_route(self) -> None:
        """**Which helper finds each planted name — including the two that are not a
        route at all.**

        `_forbidden_name_hits` unions two sweeps, so a route both sweeps reach is a route
        that measures neither of them. Reducing `_declared_properties`' `properties`
        branch to ``if False:`` left the whole suite green for exactly that reason: the
        two `properties` rows above were passing through `_object_keys`.

        The matrix is written out and both helpers are asserted separately, so the
        `properties` branch is driven by an assertion nothing else can satisfy. The
        third column is the honest statement of what the sweep covers: two rows isolate
        `_object_keys`, two isolate `_declared_properties`, and two isolate neither.
        """
        name = "schema_version"
        matrix = (
            ("an object key at depth inside a list", True, False),
            ("an object key at depth inside nested objects", True, False),
            ("a properties member", True, True),
            ("a properties member reached through a list", True, True),
            ("a required entry", False, True),
            ("a required entry reached through a list", False, True),
        )
        self.assertEqual(
            [route for route, _keys, _declarations in matrix],
            list(self.ROUTES),
            "the matrix and the route table have drifted apart",
        )
        for route, by_keys, by_declarations in matrix:
            with self.subTest(route=route):
                planted = self._only_via(route, name)
                self.assertEqual(
                    name in set(_object_keys(planted)),
                    by_keys,
                    f"_object_keys does not reach {name!r} as {route} the way this "
                    "matrix says it does",
                )
                self.assertEqual(
                    name in set(_declared_properties(planted)),
                    by_declarations,
                    f"_declared_properties does not reach {name!r} as {route} the way "
                    "this matrix says it does",
                )
        self.assertEqual(
            [
                route
                for route, by_keys, by_declarations in matrix
                if by_keys and by_declarations
            ],
            ["a properties member", "a properties member reached through a list"],
            "the rows that isolate no branch are not the two this class records",
        )

    def test_the_sweep_is_silent_on_a_document_that_declares_nothing_forbidden(
        self,
    ) -> None:
        """The other direction: a sweep that reports everything proves nothing either."""
        clean = {
            "contract_version": CANDIDATE_CONTRACT_VERSION,
            "oneOf": [{"properties": {"execution_token": {"type": "string"}}}],
            "$defs": {"envelope": {"required": ["contract_version", "execution_token"]}},
            "notes": ["schema_version is forbidden", "version is forbidden"],
        }
        for forbidden in (FORBIDDEN_VERSION_KEYS, FORBIDDEN_AUTHORITY_KEYS):
            with self.subTest(table=sorted(forbidden)):
                self.assertEqual(_forbidden_name_hits(clean, forbidden), [])

    def test_a_forbidden_name_as_a_string_value_is_not_a_declaration(self) -> None:
        """`ALR-25`'s names legitimately occur as values in forbidden-key lists and in
        legacy evidence. Only declarations are swept, and that distinction is the
        reason the sweep can be run over the whole family without exceptions."""
        values_only = {"forbidden_detail_keys": ["authority_token", "fencing_token"]}
        self.assertEqual(_forbidden_name_hits(values_only, FORBIDDEN_AUTHORITY_KEYS), [])

    def test_the_real_sweep_reports_a_planted_name_in_a_real_contract(self) -> None:
        """End to end, on a copy of an actual contract rather than a synthetic dict.

        The synthetic cases above prove the helper; this proves the helper is what the
        family sweep is made of, over a document with the shape and size of the real
        thing.
        """
        copy = _MutableCopy()
        self.addCleanup(copy.close)
        relative = f"{ANALYSIS}/job-package.schema.json"
        document = copy.load(relative)
        self.assertEqual(_forbidden_name_hits(document, FORBIDDEN_VERSION_KEYS), [])
        document.setdefault("$defs", {}).setdefault("planted", {})["required"] = [
            "schema_version"
        ]
        self.assertEqual(
            _forbidden_name_hits(document, FORBIDDEN_VERSION_KEYS), ["schema_version"]
        )

    def test_the_value_sweep_descends_into_lists_too(self) -> None:
        """`_values_for_key` has the same shape and the same gap.

        It is what collects every `stage_id` an example names, and the analysis examples
        put those inside arrays. Not descending into lists makes the referential check
        pass by finding nothing to check.
        """
        nested = {"stages": [{"stage_id": "finding_merge"}, {"stage_id": "text_analysis"}]}
        self.assertEqual(
            sorted(_values_for_key(nested, "stage_id")),
            ["finding_merge", "text_analysis"],
        )
        deeper = {"a": [[{"b": {"stage_id": "norm_verification"}}]]}
        self.assertEqual(list(_values_for_key(deeper, "stage_id")), ["norm_verification"])


class ContractVersionKeyTests(unittest.TestCase):
    """`ID-01`: exactly one version key across the three contract families."""

    def test_no_contract_declares_a_forbidden_version_key(self) -> None:
        offenders: dict[str, list[str]] = {}
        for relative in _repository_json_files("contracts"):
            if relative == LEGACY_KEY_FIXTURE:
                continue
            document = _load(relative)
            hits = _forbidden_name_hits(document, FORBIDDEN_VERSION_KEYS)
            if hits:
                offenders[relative] = hits
        self.assertEqual(offenders, {})

    def test_the_single_negative_fixture_is_the_only_declared_exception(self) -> None:
        document = _load(LEGACY_KEY_FIXTURE)
        self.assertIn("schema_version", document)
        self.assertEqual(document[CANONICAL_VERSION_KEY], CANDIDATE_CONTRACT_VERSION)
        notes = " ".join(
            rule["false_positive_notes"]
            for rule in _load(LINT_RULES_JSON)["rules"]
            if rule["rule_id"] == "ALR-24"
            for rule["false_positive_notes"] in [" ".join(rule["false_positive_notes"])]
        )
        self.assertIn(
            "legacy-schema-version.invalid.json",
            notes,
            "the exception this test relies on is not recorded in ALR-24",
        )

    def test_every_family_declares_the_same_candidate_version(self) -> None:
        declared: dict[str, str] = {}
        for relative in _repository_json_files("contracts"):
            document = _load(relative)
            if isinstance(document, dict) and CANONICAL_VERSION_KEY in document:
                value = document[CANONICAL_VERSION_KEY]
                if isinstance(value, str):
                    declared[relative] = value
        self.assertTrue(declared)
        self.assertEqual(
            sorted(set(declared.values())),
            [CANDIDATE_CONTRACT_VERSION],
            f"contract families disagree on the candidate version: {declared}",
        )

    def test_domain_and_event_schemas_pin_the_key_by_const(self) -> None:
        for relative in (
            f"{DOMAIN}/error-envelope.schema.json",
            f"{EVENTS}/event-envelope.schema.json",
        ):
            with self.subTest(schema=relative):
                schema = _load(relative)
                self.assertIn(CANONICAL_VERSION_KEY, schema["required"])
                self.assertEqual(
                    schema["properties"][CANONICAL_VERSION_KEY].get("const"),
                    CANDIDATE_CONTRACT_VERSION,
                )
                self.assertIs(schema.get("additionalProperties"), False)

    def test_golden_versions_itself_under_a_different_key(self) -> None:
        """A recorded cross-family fact, asserted rather than left to prose.

        `ID-01` and `ALR-24` are scoped to `contracts/**`. The golden baseline is
        fixture-local and keeps `schema_version`. This test pins that difference so it
        stays a deliberate boundary rather than drifting into an accident.
        """
        self.assertEqual(
            _load(LINT_RULES_JSON)["rules"][
                [rule["rule_id"] for rule in _load(LINT_RULES_JSON)["rules"]].index(
                    "ALR-24"
                )
            ]["scope"],
            ["contracts/**/*.json"],
            "ALR-24 changed scope; the golden exemption below rests on that scope",
        )
        carriers = sorted(
            relative
            for relative in _repository_json_files(GOLDEN)
            if "schema_version" in set(_object_keys(_load(relative)))
            | set(_declared_properties(_load(relative)))
        )
        self.assertEqual(
            carriers,
            [
                f"{GOLDEN}/GJ-01/manifest.json",
                f"{GOLDEN}/GJ-02/manifest.json",
                f"{GOLDEN}/GJ-03/manifest.json",
                f"{GOLDEN}/GJ-04/manifest.json",
                f"{GOLDEN}/GJ-05/manifest.json",
                f"{GOLDEN}/journey-manifest.schema.json",
                f"{GOLDEN}/selection.json",
                f"{GOLDEN}/selection.schema.json",
            ],
            "the golden family's use of schema_version moved; re-record the "
            "cross-family version-key statement in the review report",
        )


class ForbiddenAuthorityFieldNameTests(unittest.TestCase):
    """`ALR-25`: the attempt-authority capability is named `execution_token`."""

    def test_no_contract_declares_a_forbidden_authority_field_name(self) -> None:
        offenders: dict[str, list[str]] = {}
        for relative in _repository_json_files("contracts"):
            document = _load(relative)
            hits = _forbidden_name_hits(document, FORBIDDEN_AUTHORITY_KEYS)
            if hits:
                offenders[relative] = hits
        self.assertEqual(offenders, {})

    def test_the_legacy_names_survive_only_as_recorded_evidence_values(self) -> None:
        capability = _load(f"{DOMAIN}/identifiers.json")["authority_capabilities"][
            "execution_token"
        ]
        self.assertEqual(capability["canonical_field_name"], "execution_token")
        self.assertEqual(
            sorted(item["name"] for item in capability["legacy_evidence_names"]),
            ["authority_token", "fencing_token"],
        )
        for item in capability["legacy_evidence_names"]:
            self.assertEqual(item["status"], "legacy_evidence_only")

    def test_the_authority_bearing_packages_use_the_canonical_name(self) -> None:
        for relative in (
            f"{ANALYSIS}/job-package.schema.json",
            f"{ANALYSIS}/result-package.schema.json",
        ):
            with self.subTest(schema=relative):
                schema = _load(relative)
                authority = schema["$defs"]["attempt_authority"]
                self.assertIn("execution_token", authority["properties"])
                self.assertIn("execution_token", authority["required"])


class SchemaAndExampleValidityTests(unittest.TestCase):
    """Every owned schema is valid Draft 2020-12; every example behaves as declared."""

    def test_every_contract_schema_is_a_valid_draft_2020_12_schema(self) -> None:
        from jsonschema import Draft202012Validator

        schemas = [
            relative
            for relative in _repository_json_files("contracts")
            if relative.endswith(".schema.json")
        ]
        self.assertEqual(len(schemas), 11, "the owned schema set changed shape")
        for relative in schemas:
            with self.subTest(schema=relative):
                document = _load(relative)
                self.assertEqual(
                    document.get("$schema"),
                    "https://json-schema.org/draft/2020-12/schema",
                )
                Draft202012Validator.check_schema(document)

    def test_every_positive_example_validates_against_its_schema(self) -> None:
        from jsonschema import Draft202012Validator

        pairs = (
            (f"{ANALYSIS}/job-package.schema.json", f"{ANALYSIS}/examples/job-package.example.json"),
            (f"{ANALYSIS}/stage-result.schema.json", f"{ANALYSIS}/examples/stage-result.example.json"),
            (f"{ANALYSIS}/result-package.schema.json", f"{ANALYSIS}/examples/result-package.example.json"),
            (f"{DOMAIN}/error-envelope.schema.json", f"{DOMAIN}/examples/error-envelope.example.json"),
            (f"{EVENTS}/event-envelope.schema.json", f"{EVENTS}/examples/event-envelope.example.json"),
            (f"{DOMAIN}/identifiers.schema.json", f"{DOMAIN}/identifiers.json"),
            (f"{DOMAIN}/state-machines.schema.json", f"{DOMAIN}/state-machines.json"),
            (f"{DOMAIN}/error-codes.schema.json", f"{DOMAIN}/error-codes.json"),
            (f"{ANALYSIS}/stage-registry.schema.json", f"{ANALYSIS}/stage-registry.json"),
            (f"{ANALYSIS}/legacy-stage-map.schema.json", f"{ANALYSIS}/legacy-stage-map.json"),
            (f"{ANALYSIS}/legacy-stage-name-map.schema.json", f"{ANALYSIS}/legacy-stage-name-map.json"),
            (f"{GOLDEN}/selection.schema.json", f"{GOLDEN}/selection.json"),
        )
        for schema_relative, instance_relative in pairs:
            with self.subTest(instance=instance_relative):
                validator = Draft202012Validator(_load(schema_relative))
                errors = list(validator.iter_errors(_load(instance_relative)))
                self.assertEqual(
                    [error.message for error in errors],
                    [],
                    f"{instance_relative} does not validate against {schema_relative}",
                )

    def test_every_journey_manifest_validates(self) -> None:
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(_load(f"{GOLDEN}/journey-manifest.schema.json"))
        for journey in ("GJ-01", "GJ-02", "GJ-03", "GJ-04", "GJ-05"):
            with self.subTest(journey=journey):
                errors = list(
                    validator.iter_errors(_load(f"{GOLDEN}/{journey}/manifest.json"))
                )
                self.assertEqual([error.message for error in errors], [])

    def test_every_negative_example_is_rejected_for_its_own_reason(self) -> None:
        from jsonschema import Draft202012Validator

        cases = (
            (
                f"{DOMAIN}/error-envelope.schema.json",
                f"{DOMAIN}/examples/error-envelope.unknown-code.invalid.json",
                "error_code",
            ),
            (
                f"{EVENTS}/event-envelope.schema.json",
                LEGACY_KEY_FIXTURE,
                "schema_version",
            ),
        )
        for schema_relative, example_relative, blamed in cases:
            with self.subTest(example=example_relative):
                validator = Draft202012Validator(_load(schema_relative))
                errors = list(validator.iter_errors(_load(example_relative)))
                self.assertTrue(errors, f"{example_relative} was accepted")
                self.assertTrue(
                    any(
                        blamed in error.message or list(error.path)[:1] == [blamed]
                        for error in errors
                    ),
                    f"{example_relative} is not rejected for {blamed}: "
                    f"{[error.message for error in errors]}",
                )


class DomainErrorEnumParityTests(unittest.TestCase):
    """The envelope enum is exactly the catalog key set, and the family agrees on itself."""

    def test_envelope_enum_equals_the_catalog_exactly(self) -> None:
        catalog = _load(f"{DOMAIN}/error-codes.json")
        envelope = _load(f"{DOMAIN}/error-envelope.schema.json")
        enum = envelope["properties"]["error_code"]["enum"]
        self.assertEqual(len(enum), len(set(enum)), "the envelope enum repeats a code")
        self.assertEqual(sorted(enum), sorted(catalog["codes"]))
        self.assertEqual(len(catalog["codes"]), 20)

    def test_every_declared_code_carries_a_status_and_a_retry_flag(self) -> None:
        catalog = _load(f"{DOMAIN}/error-codes.json")
        for code, definition in sorted(catalog["codes"].items()):
            with self.subTest(code=code):
                self.assertRegex(code, r"^[a-z][a-z0-9_]*$")
                self.assertIsInstance(definition["http"], int)
                self.assertNotIsInstance(definition["http"], bool)
                self.assertTrue(400 <= definition["http"] <= 599)
                self.assertIsInstance(definition["retryable"], bool)
                self.assertIn(definition["category"], catalog["categories"])

    def test_state_machine_and_identifier_references_resolve(self) -> None:
        machines = _load(f"{DOMAIN}/state-machines.json")
        codes = set(_load(f"{DOMAIN}/error-codes.json")["codes"])
        identifiers = set(_load(f"{DOMAIN}/identifiers.json")["identifiers"])
        referenced = {machines["default_violation"]}
        for machine in machines["machines"].values():
            referenced |= {
                guard["on_violation"]
                for guard in machine["guards"]
                if "on_violation" in guard
            }
            for case in machine.get("run_creation", {}).get("cases", []):
                if "error_code" in case:
                    referenced.add(case["error_code"])
        self.assertLessEqual(referenced, codes, sorted(referenced - codes))
        used = {machine["identifier"] for machine in machines["machines"].values()} | {
            aggregate["identifier"]
            for aggregate in machines["non_state_machine_aggregates"].values()
        }
        self.assertLessEqual(used, identifiers, sorted(used - identifiers))

    def test_one_candidate_revision_across_the_family(self) -> None:
        revisions = {
            relative: _load(f"{DOMAIN}/{relative}")["candidate_revision"]
            for relative in ("identifiers.json", "state-machines.json", "error-codes.json")
        }
        self.assertEqual(len(set(revisions.values())), 1, revisions)


class AnalysisReferentialIntegrityTests(unittest.TestCase):
    """Reference resolution recomputed independently of the family's own gate text."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = _load(f"{ANALYSIS}/stage-registry.json")
        cls.sites = _load(f"{ANALYSIS}/legacy-stage-map.json")
        cls.names = _load(f"{ANALYSIS}/legacy-stage-name-map.json")
        cls.stage_ids = {stage["stage_id"] for stage in cls.registry["stages"]}
        cls.exclusion_ids = {
            item["excluded_scope_id"] for item in cls.registry["excluded_scope"]
        }
        cls.site_ids = {
            declaration["source_declaration_id"]
            for declaration in cls.sites["declarations"]
        }

    def test_declared_counts_are_the_recomputed_counts(self) -> None:
        self.assertEqual(len(self.stage_ids), 9)
        self.assertEqual(len(self.exclusion_ids), 11)
        self.assertEqual(len(self.site_ids), 31)
        self.assertEqual(len(self.sites["declarations"]), 31)
        self.assertEqual(len(self.names["names"]), self.names["name_count"])
        self.assertEqual(self.names["name_count"], 62)

    def test_every_stage_and_exclusion_reference_resolves(self) -> None:
        for entry in self.names["names"]:
            with self.subTest(name=entry["legacy_stage_name"]):
                if entry["resolution"] == "canonical_stage":
                    self.assertIn(entry["canonical_stage_id"], self.stage_ids)
                    self.assertNotIn("excluded_scope_id", entry)
                else:
                    self.assertIn(entry["excluded_scope_id"], self.exclusion_ids)
                    self.assertNotIn("canonical_stage_id", entry)
                for covered in entry.get("also_covers_stage_ids", []):
                    self.assertIn(covered, self.stage_ids)

    def test_every_declaration_site_reference_resolves(self) -> None:
        for entry in self.names["names"]:
            observations = [entry] + entry.get("additional_observations", [])
            for observation in observations:
                self.assertIn(observation["source_declaration_id"], self.site_ids)
        for stage in self.registry["stages"]:
            self.assertLessEqual(
                set(stage["evidence"]["legacy_declaration_ids"]), self.site_ids
            )
        for exclusion in self.registry["excluded_scope"]:
            self.assertLessEqual(
                set(exclusion.get("legacy_declaration_ids", [])), self.site_ids
            )

    def test_every_dependency_edge_resolves(self) -> None:
        for stage in self.registry["stages"]:
            for dependency in stage["depends_on"]:
                self.assertIn(dependency, self.stage_ids)

    def test_every_example_stage_id_resolves(self) -> None:
        referenced: list[str] = []
        for path in sorted(
            (REPOSITORY_ROOT / ANALYSIS / "examples").glob("*.example.json")
        ):
            document = json.loads(path.read_text(encoding="utf-8"))
            referenced += list(_values_for_key(document, "stage_id"))
        self.assertTrue(referenced)
        self.assertLessEqual(set(referenced), self.stage_ids)

    def test_run_lifecycle_rule_ids_are_unique_and_complete(self) -> None:
        triggers = self.registry["run_lifecycle"]["triggers"]
        rule_ids = [trigger["rule_id"] for trigger in triggers]
        self.assertEqual(len(rule_ids), 9)
        self.assertEqual(sorted(rule_ids), [f"RC-{n:02d}" for n in range(1, 10)])
        precedence = self.registry["run_lifecycle"]["trigger_precedence"]
        self.assertEqual(len(precedence), 1)
        ruling = precedence[0]
        by_id = {trigger["rule_id"]: trigger for trigger in triggers}
        for reference in (
            [ruling["winning_rule_id"], ruling["losing_rule_id"]]
            + list(ruling["competing_rule_ids"])
        ):
            self.assertIn(reference, by_id)
        self.assertEqual(
            by_id[ruling["winning_rule_id"]]["trigger"],
            "idempotent_replay_same_key_and_payload",
        )
        self.assertEqual(
            by_id[ruling["losing_rule_id"]]["trigger"], "repeat_of_terminal_run"
        )

    def test_package_schemas_bind_the_registry_contract_by_const(self) -> None:
        for relative in (
            f"{ANALYSIS}/job-package.schema.json",
            f"{ANALYSIS}/result-package.schema.json",
        ):
            with self.subTest(schema=relative):
                block = _load(relative)["$defs"]["stage_registry_ref"]
                self.assertEqual(
                    block["properties"]["contract"]["const"],
                    self.registry["contract"],
                )
                self.assertEqual(
                    block["properties"][CANONICAL_VERSION_KEY]["const"],
                    CANDIDATE_CONTRACT_VERSION,
                )

    def test_alias_resolution_names_the_two_map_contracts(self) -> None:
        alias = self.registry["alias_resolution"]
        self.assertEqual(alias["name_map_contract"], self.names["contract"])
        self.assertEqual(alias["site_map_contract"], self.sites["contract"])

    def test_the_bundled_stage_result_equals_the_standalone_contract(self) -> None:
        bundled = _load(f"{ANALYSIS}/result-package.schema.json")["$defs"]["stage_result"]
        self.assertEqual(bundled, _load(f"{ANALYSIS}/stage-result.schema.json"))

    def test_remapping_a_name_to_another_existing_stage_stays_resolvable(self) -> None:
        """Recorded deliberately: this is the one thing the gates cannot decide.

        Re-pointing a legacy name from one existing stage to another existing stage
        leaves every reference valid. It is a semantic change, caught by review of the
        62 recorded `rationale` strings and by the product authority, never by
        referential integrity. This test asserts the residue exists rather than
        pretending it is closed.
        """
        remapped = json.loads(json.dumps(self.names))
        holders = Counter(
            item["canonical_stage_id"]
            for item in remapped["names"]
            if item["resolution"] == "canonical_stage"
        )
        entry = next(
            item
            for item in remapped["names"]
            if item["resolution"] == "canonical_stage"
            and item["canonical_stage_id"] != "norm_verification"
            and holders[item["canonical_stage_id"]] > 1
        )
        entry["canonical_stage_id"] = "norm_verification"
        for item in remapped["names"]:
            if item["resolution"] == "canonical_stage":
                self.assertIn(item["canonical_stage_id"], self.stage_ids)
        covered = {
            item["canonical_stage_id"]
            for item in remapped["names"]
            if item["resolution"] == "canonical_stage"
        }
        self.assertEqual(
            covered,
            self.stage_ids,
            "the chosen probe accidentally orphaned a stage; pick a name whose stage "
            "keeps other evidence, so the remap really is invisible to the gates",
        )


class GoldenBaselineInvariantTests(unittest.TestCase):
    """Selection shape, assertion totals and every declared checksum."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.selection = _load(f"{GOLDEN}/selection.json")
        cls.journeys = [journey["journey_id"] for journey in cls.selection["journeys"]]
        cls.manifests = {
            journey: _load(f"{GOLDEN}/{journey}/manifest.json") for journey in cls.journeys
        }

    def test_the_selected_set_is_five_stable_journeys(self) -> None:
        self.assertEqual(self.journeys, ["GJ-01", "GJ-02", "GJ-03", "GJ-04", "GJ-05"])

    def test_manifest_checksums_match_the_declared_values(self) -> None:
        for journey in self.selection["journeys"]:
            with self.subTest(journey=journey["journey_id"]):
                digest = hashlib.sha256(
                    (
                        REPOSITORY_ROOT / GOLDEN / journey["journey_id"] / "manifest.json"
                    ).read_bytes()
                ).hexdigest()
                self.assertEqual(digest, journey["manifest_sha256"])

    def test_every_input_artifact_checksum_and_size_matches(self) -> None:
        checked = 0
        for journey, manifest in self.manifests.items():
            for artifact in manifest["input_manifest"]["artifacts"]:
                with self.subTest(journey=journey, path=artifact["path"]):
                    payload = (REPOSITORY_ROOT / artifact["path"]).read_bytes()
                    self.assertEqual(
                        hashlib.sha256(payload).hexdigest(), artifact["sha256"]
                    )
                    self.assertEqual(len(payload), artifact["size_bytes"])
                    checked += 1
        self.assertEqual(checked, 19, "the declared input artifact count moved")

    def test_assertion_invariants_recompute_from_the_manifests(self) -> None:
        invariants = self.selection["assertion_invariants"]
        declared = {
            journey: {item["id"] for item in manifest["expected_outputs"]}
            | {item["id"] for item in manifest["failure_cases"]}
            for journey, manifest in self.manifests.items()
        }
        per_journey = {journey: len(ids) for journey, ids in declared.items()}
        self.assertEqual(invariants["per_journey_assertions"], per_journey)
        mapped = [
            identifier
            for row in self.selection["inventory_assertion_coverage"]
            for identifier in row["assertion_ids"]
        ]
        annotated = [
            identifier
            for row in self.selection["target_scope_annotations"]
            for identifier in row["assertion_ids"]
        ]
        self.assertEqual(invariants["inventory_mapped_assertions"], len(mapped))
        self.assertEqual(invariants["target_scope_annotation_assertions"], len(annotated))
        self.assertEqual(invariants["total_assertions"], len(mapped) + len(annotated))
        self.assertEqual(invariants["total_assertions"], 95)
        every = mapped + annotated
        self.assertEqual(len(every), len(set(every)), "an assertion is mapped twice")
        self.assertEqual(set(every), set().union(*declared.values()))

    def test_the_inventory_fan_in_map_is_complete_and_injective(self) -> None:
        fan_in = [
            candidate
            for journey in self.selection["journeys"]
            for candidate in journey["inventory_candidates"]
        ]
        self.assertEqual(
            sorted(fan_in), [f"GJ-{n:02d}" for n in range(1, 12)], "fan-in changed"
        )
        self.assertEqual(len(fan_in), len(set(fan_in)))

    def test_parity_evidence_is_only_ever_a_legacy_observation(self) -> None:
        legacy_commit = None
        for journey, manifest in self.manifests.items():
            for item in manifest["expected_outputs"] + manifest["failure_cases"]:
                with self.subTest(journey=journey, assertion=item["id"]):
                    if item.get("parity_oracle"):
                        self.assertEqual(item["provenance_class"], "legacy_observed")
                    self.assertIn(
                        item["provenance_class"],
                        {"legacy_observed", "greenfield_target", "pending_owner_decision"},
                    )
                    if item["provenance_class"] == "legacy_observed":
                        self.assertTrue(
                            item["legacy_evidence_refs"],
                            "a legacy observation carries no locator",
                        )
                    else:
                        self.assertFalse(
                            item.get("parity_oracle"),
                            "a target divergence is presented as parity evidence",
                        )
            commit = manifest["provenance"]["legacy_source_commit"]
            self.assertRegex(commit, r"^[0-9a-f]{40}$")
            legacy_commit = legacy_commit or commit
            self.assertEqual(commit, legacy_commit, "manifests name two legacy commits")

    def test_the_golden_legacy_commit_is_the_analysis_evidence_commit(self) -> None:
        analysis_commit = _load(f"{ANALYSIS}/legacy-stage-name-map.json")[
            "legacy_source_commit"
        ]
        for journey, manifest in self.manifests.items():
            with self.subTest(journey=journey):
                self.assertEqual(
                    manifest["provenance"]["legacy_source_commit"], analysis_commit
                )


class ArchitectureCoverageTests(unittest.TestCase):
    """ADR coverage and lint-rule coverage, recomputed from the artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = _load(LINT_RULES_JSON)
        cls.rules = cls.spec["rules"]
        cls.rule_ids = {rule["rule_id"] for rule in cls.rules}
        cls.review = _load("docs/architecture/CP00_ARCHITECTURE_REVIEW.json")

    def test_adr_files_index_and_review_agree(self) -> None:
        files = sorted(
            path.name[:8]
            for path in (REPOSITORY_ROOT / "docs/architecture/adr").glob("ADR-*.md")
        )
        self.assertEqual(files, [f"ADR-{n:04d}" for n in range(1, 19)])
        indexed = sorted(set(re.findall(r"ADR-\d{4}", _read("docs/architecture/ADR_INDEX.md"))))
        self.assertEqual(indexed, files)
        reviewed = sorted(entry["adr_id"] for entry in self.review["adrs"])
        self.assertEqual(reviewed, files)
        self.assertEqual(self.review["coverage"]["adrs_total"], len(files))

    def test_markdown_table_and_json_declare_the_same_rule_set(self) -> None:
        table_ids = re.findall(r"^\|\s*(ALR-\d{2})\s*\|", _read(LINT_RULES_MD), re.M)
        self.assertEqual(len(table_ids), len(set(table_ids)))
        self.assertEqual(sorted(table_ids), sorted(self.rule_ids))
        self.assertEqual(len(self.rule_ids), len(self.rules))

    def test_every_rule_identity_is_pinned(self) -> None:
        pin = self.spec["rule_identity_pin"]
        self.assertEqual(sorted(pin), sorted(self.rule_ids))
        for rule in self.rules:
            with self.subTest(rule=rule["rule_id"]):
                self.assertEqual(
                    pin[rule["rule_id"]],
                    {
                        "slug": rule["slug"],
                        "enforcement": rule["enforcement"],
                        "severity": rule["severity"],
                    },
                )
        self.assertEqual(len({rule["slug"] for rule in self.rules}), len(self.rules))

    def test_declared_counts_recompute(self) -> None:
        counts = self.spec["counts"]
        self.assertEqual(counts["rules_total"], len(self.rules))
        self.assertEqual(
            counts["by_enforcement"],
            dict(Counter(rule["enforcement"] for rule in self.rules)),
        )
        self.assertEqual(
            counts["by_severity"], dict(Counter(rule["severity"] for rule in self.rules))
        )
        self.assertEqual(
            counts["static_error_subset"],
            sum(
                1
                for rule in self.rules
                if rule["enforcement"] == "static" and rule["severity"] == "error"
            ),
        )
        self.assertEqual(counts["escalations"], len(self.spec["escalations"]))

    def test_every_agents_md_prohibition_is_covered_exactly_once_over(self) -> None:
        declared = set(self.spec["agents_md_prohibitions"])
        covered = {
            item for rule in self.rules for item in rule.get("covers_prohibitions", [])
        }
        self.assertEqual(declared, covered)
        self.assertEqual(len(declared), self.spec["counts"]["prohibitions_declared"])

    def test_every_alr_reference_in_the_specification_resolves(self) -> None:
        for field in (
            "review_only_subset",
            "handoff_w1_arc_01",
            "open_items",
            "escalations",
            "conflicts_checked_not_escalated",
        ):
            with self.subTest(field=field):
                referenced = set(
                    re.findall(r"ALR-\d{2}", json.dumps(self.spec[field]))
                )
                self.assertLessEqual(referenced, self.rule_ids)

    def test_every_anchor_file_is_a_repository_path(self) -> None:
        anchors = sorted(
            {anchor for rule in self.rules for anchor in rule["anchor_files"]}
        )
        missing = [
            anchor for anchor in anchors if not (REPOSITORY_ROOT / anchor).is_file()
        ]
        self.assertEqual(missing, [])

    def test_ratified_agrees_with_the_external_record(self) -> None:
        """The review may not decide its own ratification.

        This replaces a flat `assertIs(ratified, False)`. That pin was correct about the
        danger and wrong about the mechanism: it made ratification impossible rather than
        making self-ratification impossible, and `W0-INT-01` could not do its declared
        job without turning the suite red. The danger is unchanged and so is the answer
        to it — the flag is compared against a record kept outside the artifact.
        """
        external_ratified, _, problems = _ratification_record(REPOSITORY_ROOT)
        declared_here = self.review["ratified"]
        self.assertIsInstance(declared_here, bool)
        if declared_here:
            self.assertEqual(
                problems,
                [],
                "the review declares itself ratified and the external record does not "
                "admissibly say so",
            )
        self.assertEqual(
            declared_here,
            external_ratified,
            f"{LINT_RULES_JSON.rsplit('/', 1)[0]}/CP00_ARCHITECTURE_REVIEW.json says "
            f"ratified={declared_here} while {CHECKPOINT_MANIFEST} says "
            f"ratified={external_ratified}. A candidate cannot ratify itself, and a "
            "recorded ratification that the review does not carry is equally a "
            "contradiction.",
        )


class MutationTests(unittest.TestCase):
    """Each check is proved by breaking exactly the thing it claims to protect.

    Every mutation is applied to a `tempfile.mkdtemp()` copy. The candidate tree is
    never opened for writing.
    """

    def setUp(self) -> None:
        self.copies: list[_MutableCopy] = []

    def tearDown(self) -> None:
        for copy in self.copies:
            copy.close()

    def _copy(self, subtrees: tuple[str, ...] = ("contracts",)) -> _MutableCopy:
        copy = _MutableCopy(subtrees)
        self.copies.append(copy)
        return copy

    def _assert_gate_rejects(self, copy: _MutableCopy, letter: str, needle: str) -> None:
        result = copy.run_gate(letter)
        self.assertNotEqual(
            result.returncode,
            0,
            f"Gate {letter} accepted the mutation.\nstdout: {result.stdout.strip()}",
        )
        self.assertIn(needle, result.stdout + result.stderr)

    def _assert_gate_accepts(self, copy: _MutableCopy, letter: str) -> None:
        result = copy.run_gate(letter)
        self.assertEqual(
            result.returncode,
            0,
            f"Gate {letter} rejected the mutation, so it does not isolate the gate "
            f"under test.\nstderr: {result.stderr.strip()}",
        )

    def test_mutation_rotated_run_lifecycle_rule_ids(self) -> None:
        """`RC-01`..`RC-09` rotated by one across the nine triggers."""
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        triggers = registry["run_lifecycle"]["triggers"]
        rotated = [trigger["rule_id"] for trigger in triggers][1:] + [
            triggers[0]["rule_id"]
        ]
        for trigger, rule_id in zip(triggers, rotated):
            trigger["rule_id"] = rule_id
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_rejects(
            copy, "D", "a trigger carries a rule_id the owner ruling does not give it"
        )

    def test_mutation_swapped_two_canonical_stage_ids(self) -> None:
        """Two `stage_id` values exchanged. Every reference still resolves.

        This is the case existence checking cannot see: the identifier set is unchanged,
        so Gate A stays green and only Gate C's identity pin — capability evidence plus
        produced artifact roles — notices that a `stage_id` no longer denotes its stage.
        """
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        by_id = {stage["stage_id"]: stage for stage in registry["stages"]}
        by_id["text_analysis"]["stage_id"] = "block_analysis"
        by_id["block_analysis"]["stage_id"] = "text_analysis"
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_accepts(copy, "A")
        self._assert_gate_rejects(
            copy,
            "C",
            "a stage_id no longer denotes the stage whose capability evidence and "
            "produced roles it carries",
        )

    def test_mutation_renamed_a_referenced_exclusion_id(self) -> None:
        """`XS-07` renamed. A name map entry points at it, so the reference dangles."""
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        for exclusion in registry["excluded_scope"]:
            if exclusion["excluded_scope_id"] == "XS-07":
                exclusion["excluded_scope_id"] = "XS-77"
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_rejects(copy, "A", "excluded_scope_id absent from registry")
        self._assert_gate_rejects(
            copy,
            "C",
            "the eleven exclusion ids are not the ones every excluded_scope_id "
            "reference resolves against",
        )

    def test_mutation_renamed_an_unreferenced_exclusion_id(self) -> None:
        """`XS-02` is named by no name-map entry, so existence checking is blind to it.

        Gate A accepts the rename; Gate C's identity pin rejects it. Recorded because it
        shows the two gates are not redundant.
        """
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        referenced = {
            entry["excluded_scope_id"]
            for entry in copy.load(f"{ANALYSIS}/legacy-stage-name-map.json")["names"]
            if entry["resolution"] == "excluded"
        }
        self.assertNotIn("XS-02", referenced, "XS-02 gained a reference; pick another")
        for exclusion in registry["excluded_scope"]:
            if exclusion["excluded_scope_id"] == "XS-02":
                exclusion["excluded_scope_id"] = "XS-72"
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_accepts(copy, "A")
        self._assert_gate_rejects(
            copy,
            "C",
            "the eleven exclusion ids are not the ones every excluded_scope_id "
            "reference resolves against",
        )

    def test_mutation_observation_moved_to_a_site_that_lacks_its_name(self) -> None:
        """One evidence observation re-pointed at a declaration site in another file.

        The observed-site bookkeeping is updated with it, so Gate A stays green and the
        file-level binding in Gate B is the only thing standing between the map and an
        observation attributed to a site that never carried the name.
        """
        copy = self._copy()
        name_map = copy.load(f"{ANALYSIS}/legacy-stage-name-map.json")
        entry = name_map["names"][0]
        origin = entry["source_declaration_id"]
        entry["source_declaration_id"] = "LSD-31"
        entry["observed_declaration_ids"] = sorted(
            set(entry["observed_declaration_ids"]) - {origin} | {"LSD-31"}
        )
        copy.store(f"{ANALYSIS}/legacy-stage-name-map.json", name_map)
        self._assert_gate_accepts(copy, "A")
        self._assert_gate_rejects(
            copy, "B", "the evidence is not in the file this declaration site names"
        )

    def test_mutation_example_names_a_stage_absent_from_the_registry(self) -> None:
        """A valid example points at a stage that does not exist."""
        copy = self._copy()
        relative = f"{ANALYSIS}/examples/job-package.example.json"
        example = copy.load(relative)

        def rename(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "stage_id" and isinstance(value, str):
                        node[key] = "absent_stage_name"
                    else:
                        rename(value)
            elif isinstance(node, list):
                for value in node:
                    rename(value)

        rename(example)
        copy.store(relative, example)
        self._assert_gate_rejects(
            copy, "A", "an example names a stage_id absent from the registry"
        )

    def test_mutation_domain_reintroduces_a_bare_version_key(self) -> None:
        """The deprecated domain mirror comes back. Two independent gates reject it."""
        copy = self._copy()
        relative = f"{DOMAIN}/error-codes.json"
        catalog = copy.load(relative)
        catalog["version"] = CANDIDATE_CONTRACT_VERSION
        copy.store(relative, catalog)

        family = [
            block
            for block in _documented_blocks(DOMAIN_README)
            if "bare version key present" in block
        ]
        self.assertEqual(len(family), 1, "the domain family gate moved")
        result = copy.run_block(family[0])
        self.assertNotEqual(result.returncode, 0, "the domain family gate accepted it")
        self.assertIn("bare version key present", result.stderr)

        sweep = [
            block
            for block in _documented_blocks(EVENTS_README)
            if "if p.endswith('.invalid.json'): continue" in block
        ]
        self.assertEqual(len(sweep), 1, "the recursive version sweep moved")
        swept = copy.run_block(sweep[0])
        self.assertNotEqual(swept.returncode, 0, "the recursive sweep accepted it")
        self.assertIn("error-codes.json", swept.stderr)

        from jsonschema import Draft202012Validator

        errors = list(
            Draft202012Validator(_load(f"{DOMAIN}/error-codes.schema.json")).iter_errors(
                catalog
            )
        )
        self.assertTrue(errors, "the owning schema tolerated the reintroduced key")

    def test_mutation_events_reintroduce_schema_version(self) -> None:
        """The retired envelope key comes back, in the example and in the schema."""
        copy = self._copy()
        relative = f"{EVENTS}/examples/event-envelope.example.json"
        example = copy.load(relative)
        example["schema_version"] = 1
        copy.store(relative, example)

        sweep = [
            block
            for block in _documented_blocks(EVENTS_README)
            if "if p.endswith('.invalid.json'): continue" in block
        ]
        result = copy.run_block(sweep[0])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event-envelope.example.json", result.stderr)

        from jsonschema import Draft202012Validator

        errors = list(
            Draft202012Validator(
                _load(f"{EVENTS}/event-envelope.schema.json")
            ).iter_errors(example)
        )
        self.assertTrue(errors, "the envelope schema accepted schema_version")

        schema_copy = self._copy()
        schema_relative = f"{EVENTS}/event-envelope.schema.json"
        schema = schema_copy.load(schema_relative)
        schema["properties"]["schema_version"] = {"const": 1}
        schema["required"].append("schema_version")
        schema_copy.store(schema_relative, schema)
        swept = schema_copy.run_block(sweep[0])
        self.assertNotEqual(swept.returncode, 0)
        self.assertIn("event-envelope.schema.json", swept.stderr)

    def test_mutation_forbidden_authority_field_name(self) -> None:
        """`execution_token` renamed back to `authority_token` in a package schema."""
        copy = self._copy()
        relative = f"{ANALYSIS}/job-package.schema.json"
        schema = copy.load(relative)
        authority = schema["$defs"]["attempt_authority"]
        authority["properties"]["authority_token"] = authority["properties"].pop(
            "execution_token"
        )
        authority["required"] = [
            "authority_token" if name == "execution_token" else name
            for name in authority["required"]
        ]
        copy.store(relative, schema)
        self._assert_gate_rejects(copy, "A", "job-package.schema.json")

    def test_mutation_golden_manifest_byte_change_breaks_its_checksum(self) -> None:
        """One byte of a manifest, so the declared `manifest_sha256` no longer holds."""
        copy = self._copy(("fixtures",))
        path = copy.root / GOLDEN / "GJ-01/manifest.json"
        path.write_bytes(path.read_bytes().replace(b'"schema_version": 1', b'"schema_version":  1'))
        blocks = _documented_blocks(SELECTION_MD)
        result = copy.run_block(blocks[0])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "False",
            result.stdout,
            "the declared manifest checksum survived a change to the manifest bytes",
        )

    def test_mutation_golden_dropped_assertion_breaks_the_declared_totals(self) -> None:
        """One assertion removed from a manifest; the coverage gate must notice."""
        copy = self._copy(("fixtures",))
        relative = f"{GOLDEN}/GJ-01/manifest.json"
        manifest = copy.load(relative)
        manifest["expected_outputs"] = manifest["expected_outputs"][:-1]
        copy.store(relative, manifest)
        blocks = _documented_blocks(SELECTION_MD)
        result = copy.run_block(blocks[1])
        self.assertNotEqual(
            result.returncode, 0, "the coverage gate accepted a dropped assertion"
        )
        self.assertIn("AssertionError", result.stderr)

    def test_mutation_candidate_drift_is_detected(self) -> None:
        """The integrity check itself, exercised in the direction that must fail.

        A green byte-identity result is worthless unless the same comparison rejects a
        changed byte. This copies the object database into a scratch tree, changes one
        contract there and asserts the comparison names exactly that path — and it uses
        the same policy function the live check uses, so it exercises the real predicate
        rather than a simplified twin.
        """
        with _CheckpointSandbox() as sandbox:
            # Normalised, so this probe means the same thing before and after
            # ratification. Without it the sandbox inherits whatever the host tree
            # happens to be, and every negative assertion below inherits it too.
            sandbox.normalise_to_candidate()
            self.assertEqual(
                _undeclared_drift(sandbox.root),
                [],
                "the scratch copy did not start out identical to the candidate",
            )
            target = sandbox.root / DOMAIN / "error-codes.json"
            # A pure reformat: the parsed value is unchanged and only the bytes move.
            target.write_text(
                json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=4)
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _undeclared_drift(sandbox.root),
                [f"{DOMAIN}/error-codes.json"],
                "a re-indented contract was accepted as byte-identical",
            )
            (sandbox.root / ANALYSIS / "stage-registry.json").unlink()
            self.assertEqual(
                _undeclared_drift(sandbox.root),
                sorted(
                    [f"{DOMAIN}/error-codes.json", f"{ANALYSIS}/stage-registry.json"]
                ),
                "a deleted contract was not reported as drift",
            )
            new_artifact = sandbox.root / "docs/architecture/NEW_DOCUMENT.md"
            new_artifact.write_text("# added after the candidate\n", encoding="utf-8")
            self.assertIn(
                "docs/architecture/NEW_DOCUMENT.md",
                _undeclared_drift(sandbox.root),
                "a file added after the candidate was invisible to the drift check",
            )

    def test_mutation_lint_rule_rename_breaks_the_identity_pin(self) -> None:
        """A `rule_id` renamed inside a rule row while its pin entry stays put."""
        copy = self._copy(("docs",))
        relative = LINT_RULES_JSON
        spec = copy.load(relative)
        spec["rules"][0]["rule_id"] = "ALR-99"
        copy.store(relative, spec)
        gate_c = [
            block
            for block in _documented_blocks(LINT_RULES_MD)
            if "identity pin ok" in block
        ]
        self.assertEqual(len(gate_c), 1)
        result = copy.run_block(gate_c[0])
        self.assertNotEqual(result.returncode, 0, "the identity pin accepted a rename")


class RatificationRecordTests(unittest.TestCase):
    """What counts as a declared ratification delta, proved in both directions.

    The policy, stated once so it cannot be widened by reading:

    * **`contracts/**`, `fixtures/**`, `scripts/**` — never.** Ratification does not
      reach them. No record licenses a byte.
    * **`docs/architecture/**` — only under all four conditions at once.** An external
      record in `artifacts/checkpoints/CP-00/manifest.json` says `ratified: true`; that
      record carries a `ratification` object naming `allowed_delta_paths` plus its task,
      date, authority and reason; every named path lies under `docs/architecture/`, is
      inside `RATIFICATION_DELTA_CEILING`, and already existed at the reviewed
      candidate. A file outside the named set is drift, exactly as before.
    * **The ceiling is pinned here, not in the record.** The record may name fewer paths
      than the ceiling and never one outside it, so nobody can widen the delta by
      editing the record they also write. Widening means editing this module, which only
      `W0-QA-01` owns, which means reopening this task and another independent review.
    * **The review may not decide its own ratification.** `ratified` in
      `CP00_ARCHITECTURE_REVIEW.json` must equal the external record's, in both
      directions.

    Every probe below runs against a throwaway copy of the whole repository. The
    candidate is never written.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = _CheckpointSandbox()
        cls.sandbox.normalise_to_candidate()
        cls.review = "docs/architecture/CP00_ARCHITECTURE_REVIEW.json"
        cls.full_delta = sorted(RATIFICATION_DELTA_CEILING)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__()

    def setUp(self) -> None:
        self.addCleanup(self.sandbox.restore)
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            [],
            "the sandbox did not start clean",
        )

    def _ratify(self, paths: list[str] | None = None, **kwargs: object) -> None:
        """Apply a realistic ratification: the record, the flag, and the five edits."""
        declared = self.full_delta if paths is None else paths
        self.sandbox.declare_ratification(declared, **kwargs)
        self.sandbox.patch_json(self.review, ratified=True)
        for relative in declared:
            if relative != self.review and relative in RATIFICATION_DELTA_CEILING:
                self.sandbox.edit(relative)

    # ---- the direction that must pass -------------------------------------------

    def test_declared_ratification_of_the_whole_ceiling_is_accepted(self) -> None:
        self._ratify()
        external, declared, problems = _ratification_record(self.sandbox.root)
        self.assertTrue(external)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(declared), self.full_delta)
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            [],
            "a fully declared ratification was rejected, so ratification is still "
            "impossible and this reopening achieved nothing",
        )
        self.assertEqual(_immutable_family_drift(self.sandbox.root), [])
        self.assertEqual(
            sorted(_drifted_reviewed_paths(self.sandbox.root)),
            self.full_delta,
            "the drift is still observed and reported; it is licensed, not invisible",
        )

    def test_a_partial_declaration_is_rejected(self) -> None:
        """Inverted in round four. It used to assert the opposite, and was wrong.

        `test_a_partial_declared_ratification_is_accepted` asserted that "the record may
        name fewer paths than the ceiling", which pinned the defect as a property: an
        independent negative probe declared all five files, changed one, and the suite
        stayed green — four obligatory reconciliations skippable with the record still
        claiming them. For CP-00 the ceiling is not a menu. Each of the five is a
        reconciliation ratification owes, so the declared set must be all of it.
        """
        subset = [self.review, "docs/architecture/ADR_INDEX.md"]
        self._ratify(subset)
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("does not declare every reconciliation" in problem for problem in problems),
            problems,
        )
        self.assertNotEqual(_ratification_delta_problems(self.sandbox.root), [])

    # ---- the directions that must fail ------------------------------------------

    def test_declaring_five_reconciliations_and_making_one_is_rejected(self) -> None:
        """The exact false positive an independent negative probe produced.

        Full record, full declared set, one file actually reconciled. Nothing is
        undeclared, so the one-directional check said `[]` and the suite was green while
        four obligatory reconciliations had not been made.
        """
        self.sandbox.declare_ratification(self.full_delta)
        self.sandbox.patch_json(self.review, ratified=True)
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(problems, [], "the record itself is admissible")
        self.assertEqual(sorted(declared), self.full_delta)
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            [],
            "precondition: the one-directional check sees nothing wrong here",
        )
        skipped = [path for path in self.full_delta if path != self.review]
        self.assertEqual(
            _unperformed_declarations(self.sandbox.root),
            skipped,
            "the four unmade reconciliations must be named",
        )
        delta_problems = _ratification_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("Declaring the work is not doing it" in problem for problem in delta_problems),
            delta_problems,
        )

    def test_a_fully_declared_and_fully_performed_ratification_is_accepted(self) -> None:
        """The other side of the same rule: do all five and the suite is green."""
        self._ratify()
        self.assertEqual(_ratification_delta_problems(self.sandbox.root), [])
        self.assertEqual(_unperformed_declarations(self.sandbox.root), [])

    def test_ratification_without_any_record_is_drift(self) -> None:
        self.sandbox.patch_json(self.review, ratified=True)
        self.sandbox.edit("docs/architecture/ADR_INDEX.md")
        external, _, _ = _ratification_record(self.sandbox.root)
        self.assertFalse(external, "the manifest still says unratified")
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            ["docs/architecture/ADR_INDEX.md", self.review],
            "a self-declared ratification with no external record was accepted",
        )

    def test_both_directions_are_reported_at_once(self) -> None:
        """One reconciliation skipped and one stranger edited, in the same tree.

        The two failure modes are independent and neither may mask the other: the
        stranger must be named as undeclared drift and the skipped file as an unmade
        reconciliation, from a single evaluation.
        """
        self._ratify()
        skipped = "docs/architecture/ADR_INDEX.md"
        self.sandbox.restore_one(skipped)
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        self.assertEqual(
            _undeclared_drift(self.sandbox.root), ["docs/architecture/GLOSSARY.md"]
        )
        self.assertEqual(_unperformed_declarations(self.sandbox.root), [skipped])
        problems = _ratification_delta_problems(self.sandbox.root)
        self.assertTrue(any("no ratification record accounts" in x for x in problems), problems)
        self.assertTrue(any("Declaring the work is not doing it" in x for x in problems), problems)

    def test_an_undeclared_architecture_file_outside_the_ceiling_is_drift(self) -> None:
        """`GLOSSARY.md` is in the reviewed family and outside the ceiling."""
        self._ratify()
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            ["docs/architecture/GLOSSARY.md"],
        )

    def test_a_record_naming_a_path_above_the_ceiling_licenses_nothing(self) -> None:
        """The anti-widening control: the record cannot enlarge its own authority."""
        self._ratify(self.full_delta + ["docs/architecture/GLOSSARY.md"])
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("outside the ratification ceiling" in problem for problem in problems),
            problems,
        )
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            self.full_delta,
            "an inadmissible record still licensed a delta; every path it named must "
            "come back as drift, including the ones that were inside the ceiling",
        )

    def test_a_record_naming_a_path_outside_the_family_licenses_nothing(self) -> None:
        self._ratify([self.review, f"{DOMAIN}/error-codes.json"])
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("may not reach outside" in problem for problem in problems), problems
        )

    def test_a_record_naming_a_path_absent_at_the_candidate_licenses_nothing(self) -> None:
        new_path = "docs/architecture/RATIFICATION_NOTE.md"
        (self.sandbox.root / new_path).write_text("# new\n", encoding="utf-8")
        self.addCleanup(lambda: (self.sandbox.root / new_path).unlink(missing_ok=True))
        self._ratify([self.review, new_path])
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("need review rather than ratification" in p for p in problems), problems
        )

    def test_every_immutable_family_stays_immutable_under_ratification(self) -> None:
        self._ratify()
        for relative in (
            f"{DOMAIN}/error-codes.json",
            f"{GOLDEN}/selection.json",
            "scripts/validate_bootstrap.py",
        ):
            with self.subTest(path=relative):
                self.sandbox.edit(relative, marker="\n")
                self.assertIn(relative, _immutable_family_drift(self.sandbox.root))
                self.assertIn(relative, _undeclared_drift(self.sandbox.root))

    def test_a_record_missing_its_provenance_licenses_nothing(self) -> None:
        for field in RATIFICATION_REQUIRED_FIELDS:
            with self.subTest(missing=field):
                self._ratify(omit=(field,))
                _, declared, problems = _ratification_record(self.sandbox.root)
                self.assertEqual(declared, frozenset())
                self.assertTrue(
                    any(f"ratification.{field}" in problem for problem in problems),
                    problems,
                )
                self.sandbox.restore()

    def test_the_ratifying_task_is_anchored_to_the_documents_that_assign_the_act(
        self,
    ) -> None:
        r"""**A fifth self-referential anchor, and the one that did not have to be.**

        §11.16.8 disclosed four values that could be set to anything with the suite
        green, because the only thing writing the value was the probe that later looked
        for it. There were five: `RATIFYING_TASK` could be rotated to any string and all
        244 tests stayed green, because `_ratification_record` compares the record's
        `task` against this constant and the probe that builds the record reads the same
        constant to fill it in.

        It is unlike the other four in the way that matters: it has real external
        documents to anchor to. `W0.3_ratification_integration.md` assigns the CP-00
        ratification act to exactly one task, and that task has a file. So it is
        anchored rather than disclosed, and the count in §11.16.8 is corrected to four
        remaining.

        The row is asserted to name **one** task, not merely to contain this one: a row
        that assigned the act to two tasks would satisfy a containment test while
        meaning the opposite of what this constant claims.

        **Round twelve, RL-1.** That was the claim; the pattern did not make it. `W0-`
        task ids in this program are not all three letters — `W0-INT-01` and `W0-QA-01`
        sit side by side in the manifest — and ``W0-[A-Z]{3}-\d{2}`` cannot see a
        two-letter one. A row co-assigning the act to ``W0-INT-01`` and ``W0-QA-01``
        matched only `W0-INT-01`, so the set was still ``[RATIFYING_TASK]`` and all 281
        tests stayed green on a document saying the opposite of what is asserted here.
        The same row written with `W0-ARC-02` went red, which is why the finding failed
        closed and was weighed as a limitation rather than a blocker; it is closed
        anyway, because "fails closed for the ids that happen to be three letters" is
        not the property the paragraph above claims. ``{2,4}`` spans every id form this
        program uses.
        """
        self.assertEqual(RATIFYING_TASK, "W0-INT-01")
        wave = _read("docs/program/waves/W0.3_ratification_integration.md")
        rows = [
            line
            for line in wave.split("\n")
            if "CP-00 review ratification" in line and line.strip().startswith("|")
        ]
        self.assertEqual(
            len(rows),
            1,
            "the wave document no longer carries exactly one CP-00 ratification "
            "assignment row; re-anchor this probe rather than deleting it",
        )
        self.assertEqual(
            sorted(set(re.findall(r"W0-[A-Z]{2,4}-\d{2}", rows[0]))),
            [RATIFYING_TASK],
            "the document that assigns the CP-00 ratification act does not assign it to "
            f"{RATIFYING_TASK} alone",
        )
        self.assertTrue(
            (REPOSITORY_ROOT / f"docs/program/tasks/{RATIFYING_TASK}.md").is_file(),
            f"{RATIFYING_TASK} is not a task in this program",
        )

    def test_a_record_from_the_wrong_task_licenses_nothing(self) -> None:
        self._ratify(task="W0-ARC-02")
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(any("may ratify CP-00" in problem for problem in problems))

    def test_a_ratified_flag_with_no_ratification_object_licenses_nothing(self) -> None:
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=True)
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(any("carries no 'ratification' object" in p for p in problems))

    def test_an_empty_or_repeating_path_list_licenses_nothing(self) -> None:
        """Each malformation named, not merely "something was reported".

        Round nine's reviewer found this probe passing for a reason other than its name:
        both cases also trip an earlier check, and asserting `problems` is truthy could
        not tell which. The repeats case in particular said nothing about repetition. Each
        case now asserts the message for the defect it is named after — which also
        records, rather than hides, that an empty list is rejected as an empty list and
        never reaches the ceiling comparison.
        """
        expectations = (
            ([], "must be a non-empty list of repository-relative paths"),
            ([self.review, self.review], "repeats a path"),
        )
        for paths, expected in expectations:
            with self.subTest(paths=paths):
                self.sandbox.declare_ratification(paths)
                _, declared, problems = _ratification_record(self.sandbox.root)
                self.assertEqual(declared, frozenset())
                self.assertTrue(
                    any(expected in problem for problem in problems),
                    f"{paths} was rejected, but not for {expected!r}: {problems}",
                )
                self.sandbox.restore()

    def test_a_recorded_ratification_the_review_does_not_carry_is_a_contradiction(
        self,
    ) -> None:
        """The other direction of the flag check: record true, artifact still false."""
        self.sandbox.declare_ratification(self.full_delta)
        external, _, problems = _ratification_record(self.sandbox.root)
        self.assertTrue(external)
        self.assertEqual(problems, [])
        review = json.loads(
            (self.sandbox.root / self.review).read_text(encoding="utf-8")
        )
        self.assertIs(
            review["ratified"],
            False,
            "probe precondition: the review has not been ratified in the sandbox",
        )
        self.assertNotEqual(
            review["ratified"],
            external,
            "the flag check must reject a record the artifact does not carry",
        )

    def test_the_manifest_does_not_contradict_itself(self) -> None:
        """A record cannot pre-authorise a delta it has not taken.

        Structural, and independent of the registry: whatever format the human registry
        ends up carrying, the machine record must not hold a `ratification` object while
        declaring `ratified: false`.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        self.assertIsNotNone(manifest)
        if manifest.get("ratified") is not True:
            self.assertNotIn(
                "ratification",
                manifest,
                f"{CHECKPOINT_MANIFEST} carries a ratification object while declaring "
                "itself unratified",
            )

    def test_the_two_external_records_do_not_contradict_each_other(self) -> None:
        """Compared by structure. The previous form read English and was wrong.

        It asked whether the row contained the word `ratified`, which matches inside
        `not ratified`: a registry line *denying* ratification was indistinguishable
        from one confirming it, in both directions — a manifest saying `ratified: true`
        beside a row reading "not ratified" passed, and today's honest "not ratified"
        beside `ratified: false` failed. That is the same defect class this wave
        rejected three candidates for: a gate whose claim lives in prose rather than in
        checkable structure. No better prose parser replaces it; the row is not read as
        English at all.

        What is read instead is the one machine-readable element the row already
        carries: it cites, in a code span, the manifest key that holds CP-00's state.
        Today it cites `ratification_blocked`; a ratified checkpoint cites
        `ratification`. The vocabulary is closed, the tokens are identifiers rather than
        words, and negation cannot flip their meaning because no English is consulted.

        This formalises an existing convention rather than inventing a field, and it is
        satisfied by the registry as it stands. If the repository owner would rather the
        registry carry a first-class state column, that is a registry-format decision
        for the checkpoint-registry owner, not something this module should guess at;
        `docs/program/reviews/W0-QA-01.md` §11.7 records the request.
        """
        self.assertIsNone(_registry_state_problem(REPOSITORY_ROOT))

    # ---- round five: content, and an accepted round ------------------------------

    def _ratify_for_real(self, **round_kwargs: object) -> None:
        """A ratification that does the work: record, flag, five reconciliations, round.

        The tested digest sealed here is the **real** one — the value frozen at the
        commit the sandbox was reset to. A harness that sealed an invented value would
        be constructing the defect these probes exist to reject, and would make the
        positive case unfalsifiable in the same breath: that is exactly how
        `tested_candidate_digest` stayed unchecked for four rounds.
        """
        self.assertIsNotNone(
            self.sandbox.frozen_digest,
            "this repository records no frozen tested_candidate_digest, so no genuine "
            "ratification can be built here; refusing to build one on a fabricated "
            "value instead",
        )
        self.assertEqual(
            self.sandbox.unresettable,
            [],
            "the sandbox could not be returned to the frozen tree: these paths are "
            "tracked now and absent there, so every post-freeze probe would be "
            "measuring the host checkout instead of the policy",
        )
        self.sandbox.declare_ratification(self.full_delta)
        self.sandbox.patch_json(
            self.review, ratified=True, review_status="ratified"
        )
        for entry in RECONCILIATIONS:
            self.sandbox.reconcile(entry)
        markdown = self.sandbox.root / REVIEW_MARKDOWN
        disclaimer = re.compile(
            r"\s+".join(re.escape(word) for word in REVIEW_DISCLAIMER.split())
        )
        markdown.write_text(
            disclaimer.sub("the ratification act", markdown.read_text(encoding="utf-8"))
            + "\nStatus: `ratified`.\n",
            encoding="utf-8",
        )
        self.sandbox.set_registry_state(RATIFIED_STATE_TOKEN, "ratified")
        # The third external record, licensed in POST_FREEZE_DELTA_CEILING and required
        # to move by _state_document_problems. Before round seven a "ratification that
        # does the work" left this document denying the ratification and nothing minded.
        self.sandbox.update_state_document()
        # Every `docs/architecture/**` write is done, so the reviewed-family digest the
        # external record carries can be brought up to the tree that was just produced.
        # Before this the harness built a tree the real publication cannot be: the
        # record would still describe the pre-ratification families.
        self.sandbox.recompute_manifest_digest()
        # Round thirteen: the rest of what ratification has to write. The bundle comes
        # after the reconciliations because the contract manifest records the digest of
        # the reviewed families as published.
        self.sandbox.publish_program_documents()
        self.sandbox.close_task_banners()
        self.sandbox.write_checkpoint_bundle()
        self.sandbox.accept_round(**round_kwargs)
        # The verdict has landed, so the record of the rounds has to carry it. This is
        # the write that voided its own round until the acceptance record was licensed.
        self.sandbox.update_acceptance_record()
        self.sandbox.seal_digests(tested=self.sandbox.frozen_digest)

    def test_a_ratification_that_does_the_work_is_accepted(self) -> None:
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        self.assertIsNone(_registry_state_problem(self.sandbox.root))

    def test_each_reconciliation_touched_but_not_made_is_named(self) -> None:
        """The round-five false positive, one file at a time."""
        for entry in RECONCILIATIONS:
            with self.subTest(item=entry["item"]):
                self._ratify_for_real()
                self.sandbox.restore_one(entry["path"])
                self.sandbox.touch_without_reconciling(entry)
                problems = _reconciliation_problems(self.sandbox.root)
                self.assertTrue(
                    any(entry["item"] in problem for problem in problems),
                    f"a commented-out reconciliation passed: {problems}",
                )
                self.sandbox.restore()

    def test_a_dead_anchor_fails_instead_of_passing_forever(self) -> None:
        """Anti-vacuity: if a stale phrase is not in the candidate, say so."""
        entry = dict(RECONCILIATIONS[0])
        entry["stale"] = "a phrase that was never in this document"
        table = (entry,) + RECONCILIATIONS[1:]
        with unittest.mock.patch.object(
            sys.modules[__name__], "RECONCILIATIONS", table
        ):
            problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(any("anchor rot" in problem for problem in problems), problems)

    def _with_reconciliations(self, table: tuple) -> list[str]:
        """Run the reconciliation checks over a substituted requirement table."""
        with unittest.mock.patch.object(
            sys.modules[__name__], "RECONCILIATIONS", table
        ):
            return _reconciliation_problems(self.sandbox.root)

    def test_a_new_text_requirement_already_in_the_candidate_is_rejected(self) -> None:
        """Degeneracy, `new_text` side. The guard no test could tell from its absence.

        A positive requirement the candidate already satisfies cannot distinguish work
        done from work skipped: the reconciliation could be entirely unmade and the
        needle would still be found. This is the defect that put `must_contain:
        ("GATE-E",)` in the table as reconciliation evidence while `GATE-E` was already
        in the document three times, so the guard that detects it must itself be shown
        to fire.
        """
        entry = dict(RECONCILIATIONS[3])
        self.assertEqual(entry["path"], "docs/architecture/ADR_INDEX.md")
        entry["new_text"] = ("`PD-01`",)
        problems = self._with_reconciliations(RECONCILIATIONS[:3] + (entry,))
        self.assertTrue(
            any(
                "degenerate requirement" in problem and "`PD-01`" in problem
                for problem in problems
            ),
            "a new_text needle the candidate already carries was accepted as a "
            f"requirement: {problems}",
        )

    def test_a_sentence_requirement_already_satisfiable_at_the_candidate_is_rejected(
        self,
    ) -> None:
        """Degeneracy, `sentence_requires` side. Same principle, sentence granularity.

        The real requirement is one sentence carrying `62`, `31` and `satisfied`, none
        of which co-occur at the candidate. Substituted here is a conjunction the
        candidate's own stale sentence already satisfies — a requirement that would be
        met by doing nothing at all.
        """
        entry = dict(RECONCILIATIONS[0])
        self.assertEqual(
            entry["path"], "docs/architecture/CP00_ARCHITECTURE_REVIEW.md"
        )
        entry["sentence_requires"] = ("31", "alias", "precondition")
        problems = self._with_reconciliations((entry,) + RECONCILIATIONS[1:])
        self.assertTrue(
            any(
                "degenerate requirement" in problem
                and "already has a sentence carrying" in problem
                for problem in problems
            ),
            "a sentence conjunction the candidate already satisfies was accepted as a "
            f"requirement: {problems}",
        )

    def test_a_removal_with_no_positive_requirement_must_declare_itself(self) -> None:
        """The `removal_only` rule, which is the reason the other two guards are enough.

        An entry with no positive requirement checks one thing: that a phrase went away.
        Rewording alone satisfies it. That is a weaker guarantee than the other entries
        carry and it must be declared, not arrived at by omitting a field — otherwise a
        future editor drops a `new_text` and nobody can tell the difference between a
        deliberate removal-only anchor and an incomplete one.
        """
        entry = dict(RECONCILIATIONS[2])
        self.assertEqual(
            entry["path"], "docs/architecture/ARCHITECTURE_LINT_RULES.md"
        )
        entry.pop("removal_only")
        problems = self._with_reconciliations(
            RECONCILIATIONS[:2] + (entry,) + RECONCILIATIONS[3:]
        )
        self.assertTrue(
            any(
                "no positive requirement and not marked removal_only" in problem
                for problem in problems
            ),
            f"an undeclared removal-only requirement passed as a full one: {problems}",
        )

    def test_a_reconciliation_naming_a_path_absent_from_the_candidate_is_reported(
        self,
    ) -> None:
        """The other anti-vacuity direction: the file itself has to be there.

        `anchor rot` covers a phrase that stopped matching. A whole path that never
        existed at the reviewed candidate is the same failure one level up, and it is
        not hypothetical — the ceiling and the requirement table are edited by hand and
        by different tasks.
        """
        entry = {
            "item": "a reconciliation whose document is not in the candidate",
            "path": "docs/architecture/A_DOCUMENT_THAT_WAS_NEVER_REVIEWED.md",
            "stale": "anything at all",
            "new_text": ("anything else",),
            "requires_note": "a document that exists",
        }
        problems = self._with_reconciliations(RECONCILIATIONS + (entry,))
        self.assertTrue(
            any(
                "does not exist at the reviewed candidate" in problem
                and "A_DOCUMENT_THAT_WAS_NEVER_REVIEWED" in problem
                for problem in problems
            ),
            f"a requirement anchored on a file nobody reviewed passed: {problems}",
        )

    def test_removing_a_stale_claim_with_no_recorded_ratification_is_reported(
        self,
    ) -> None:
        """Reconciling is ratification's job, and needs the record that authorises it.

        The unratified direction. Without this the reconciliations could be made
        quietly, one commit at a time, and the ratification record would arrive later to
        find the work already done and nothing left to authorise — the delta control
        reduced to bookkeeping.
        """
        entry = RECONCILIATIONS[3]
        self.sandbox.reconcile(entry)
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(
            any(
                "was removed without a recorded ratification" in problem
                and entry["path"] in problem
                for problem in problems
            ),
            f"a stale claim was reconciled with no record authorising it: {problems}",
        )

    def test_a_reconciliation_that_removes_the_stale_claim_and_adds_nothing_is_named(
        self,
    ) -> None:
        """Removal is half the requirement; `new_text` is the other half.

        `test_each_reconciliation_touched_but_not_made_is_named` covers the file that
        never moved. This is its complement: the stale claim genuinely goes, and what
        was supposed to replace it never arrives, so the document now says nothing at
        all where it used to say something false.
        """
        entry = RECONCILIATIONS[3]
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
        self.sandbox.rewrite(
            entry["path"], entry["new_text"][0], "the recorded owner decisions"
        )
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(
            any(
                entry["item"] in problem and "does not carry" in problem
                for problem in problems
            ),
            f"a reconciliation that deleted the false claim and replaced it with "
            f"nothing passed: {problems}",
        )

    def test_a_reconciliation_that_drops_its_evidence_sentence_is_named(self) -> None:
        """The sentence conjunction, on the ratified side — for **every** entry that has
        one, and on each of the three tokens separately.

        The `62`/`31`/`satisfied` sentence is the evidence that the `PD-02` precondition
        is met. Removing the stale denial without it leaves a document that has stopped
        saying the precondition is unmet and never says it is met.

        Round ten drove entry 0 only, while the live code names both `PD-02` documents.
        That is the difference between a probe and a table: weakening
        ``RECONCILIATIONS[1]["sentence_requires"]`` from ``("62", "31", "satisfied")`` to
        ``("satisfied",)`` left all 244 tests green, because the appended sentence still
        contained the one surviving token and no probe ever asked entry 1 anything.
        Emptying the tuple outright *was* caught; only the weakening survived, which is
        why the loop below removes the tokens one at a time rather than removing the
        sentence.
        """
        entries = [entry for entry in RECONCILIATIONS if entry.get("sentence_requires")]
        self.assertEqual(
            [entry["path"] for entry in entries],
            [
                "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
                "docs/architecture/CP00_OWNER_DECISIONS.md",
            ],
            "the entries carrying an evidence sentence are not the two this probe "
            "was written for",
        )
        # One token removed at a time: the conjunction has to be a conjunction. The
        # replacements keep the sentence and take out exactly the evidence.
        removals = (
            ("62", "62 legacy names", "the legacy names"),
            ("31", "31 alias-bearing", "several alias-bearing"),
            ("satisfied", "precondition is satisfied", "precondition is addressed"),
        )
        for entry in entries:
            for token, old_text, new_text in removals:
                with self.subTest(item=entry["item"], token=token):
                    self.assertIn(
                        token,
                        entry["sentence_requires"],
                        f"{entry['item']} no longer requires {token!r}, so this "
                        "subtest is measuring a token nothing asks for",
                    )
                    self._ratify_for_real()
                    self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
                    self.sandbox.rewrite(entry["path"], old_text, new_text)
                    problems = _reconciliation_problems(self.sandbox.root)
                    self.assertTrue(
                        any(
                            entry["item"] in problem
                            and "has no single sentence carrying" in problem
                            for problem in problems
                        ),
                        f"a reconciliation with no evidence sentence passed: {problems}",
                    )
                    self.sandbox.restore()

    def test_the_review_status_quotation_is_found_across_a_line_wrap(self) -> None:
        """**The third `_flat` site**, re-anchored to the side a wrap can be built on.

        Round ten found `_flat` unmeasured in two places and gave each a probe. There
        are three on the ratified path: `_state_document_problems`, the candidate-side
        novelty check, and the *present* review-Markdown comparison. Dropping the
        flattening left all 244 tests green.

        **Why this probe moved from the candidate side to the live side.** Round
        thirteen made both halves of the comparison ask for the `review_status` as a
        **code span** rather than as a bare substring, because "ratified" -- the only
        value `W0-INT-01` is permitted to write -- occurs seven times in the candidate
        as ordinary English, so the bare form rejected the one honest ratification. The
        candidate blob is immutable and contains exactly one code span broken across a
        line, `approved with modification`, and that same phrase also appears unwrapped
        twenty-nine times, so it cannot serve as an anchor for a wrap. Rather than let
        the probe rot into one that passes without measuring a wrap, it is re-pointed at
        the live document, where the sandbox can construct the wrap and the same `_flat`
        decides the same question. Recorded rather than quietly dropped: the
        candidate-side `_flat` now has no wrap case, because this candidate offers none.

        The direction is positive on purpose -- a wrapped quotation must still be
        **found** -- which is what goes red if the flattening is removed.
        """
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])

        status = "ratified at CP-00"
        candidate = _candidate_blob(self.sandbox.root, REVIEW_MARKDOWN)
        self.assertIsNotNone(candidate, "the candidate review Markdown is unreadable")
        self.assertNotIn(
            f"`{status}`",
            _flat(candidate.decode("utf-8")),
            "the anchor is already in the candidate, so the novelty half would fire and "
            "this probe would pass for the wrong reason",
        )

        self.sandbox.patch_json(self.review, review_status=status)
        self.sandbox.rewrite(
            REVIEW_MARKDOWN, "Status: `ratified`.", "Status: `ratified at\nCP-00`."
        )
        markdown = (self.sandbox.root / REVIEW_MARKDOWN).read_text(encoding="utf-8")
        self.assertNotIn(
            f"`{status}`",
            markdown,
            "the quotation is not actually wrapped, so nothing here needs flattening",
        )
        self.assertIn(f"`{status}`", _flat(markdown))

        problems = _reconciliation_problems(self.sandbox.root)
        self.assertFalse(
            any("does not quote the review_status" in problem for problem in problems),
            "a review_status the document quotes across a line wrap was reported as "
            f"unquoted, so the comparison is not flattening: {problems}",
        )

    def test_the_status_the_ratifying_task_requires_is_one_this_module_accepts(
        self,
    ) -> None:
        """`W0-INT-01` required tests 2 and 3, together, on one tree.

        **The deadlock this closes.** Required test 3 of the ratifying task asserts
        ``r['review_status'] == 'ratified'``; required test 2 runs this suite. While the
        Markdown quotation was checked as a bare substring, those two could not both
        pass on any tree: "ratified" is an ordinary English word appearing seven times in
        the reviewed candidate of `CP00_ARCHITECTURE_REVIEW.md`, so the degeneracy guard
        rejected the only value the task is permitted to write, and
        :meth:`_ratify_for_real` had to invent `ratified_at_w0_3` -- a value no external
        record asks for -- to keep this module green. Neither owner could repair it
        alone: the task's required-tests section is outside `W0-INT-01`'s allowed paths,
        and this module is `W0-QA-01`'s.

        The repair is in this module, because the defect was here: a quotation check that
        cannot tell a quotation from a word. It is probed by executing the *task's own*
        assertion, verbatim from `docs/program/tasks/W0-INT-01.md`, rather than a
        paraphrase of it -- a paraphrase would drift from the requirement it stands for,
        which is the failure shape this checkpoint keeps finding.
        """
        self._ratify_for_real()

        review = json.loads(
            (self.sandbox.root / REVIEW_JSON).read_text(encoding="utf-8")
        )
        # Required test 3, verbatim.
        self.assertIs(review["ratified"], True)
        self.assertEqual(review["review_status"], "ratified")
        self.assertEqual(sum(x["disposition"] == "defer" for x in review["adrs"]), 1)
        self.assertEqual(
            next(x for x in review["adrs"] if x["adr_id"] == "ADR-0014")["disposition"],
            "defer",
        )

        # Required test 2, at the level this probe can reach it: the checks that judge
        # the same tree must be silent on the value required test 3 just demanded.
        self.assertEqual(
            _review_consistency_problems(self.sandbox.root, True),
            [],
            "the ratifying task's required review_status is one this module rejects; "
            "required tests 2 and 3 cannot both pass and the checkpoint has no "
            "executable final state",
        )
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])

        # Anti-vacuity: the bare word really is in the candidate, so the code-span form
        # is doing work rather than restating the substring test under another name.
        candidate = _candidate_blob(self.sandbox.root, REVIEW_MARKDOWN)
        self.assertIsNotNone(candidate)
        flat_candidate = _flat(candidate.decode("utf-8"))
        self.assertIn("ratified", flat_candidate)
        self.assertNotIn("`ratified`", flat_candidate)

    def test_a_review_status_already_in_the_candidate_markdown_proves_nothing(
        self,
    ) -> None:
        """`review_status` novelty — the same degeneracy across two documents.

        Ratification must move both halves of the review, and the Markdown half is
        checked by requiring it to quote the JSON half's `review_status` verbatim. If
        that token is one the candidate's Markdown already contains, the requirement is
        satisfied before any ratification happens and the cross-document check is
        decorative.
        """
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
        # A quoted token the candidate already carries. It moved from "ratification"
        # when the requirement became a code span: the bare word occurs in the candidate
        # as ordinary prose, which is exactly the ambiguity the quoted form removes, so
        # the probe now has to name something the candidate quotes.
        self.sandbox.patch_json(self.review, review_status="AuditRun")
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(
            any(
                "already appears in" in problem and "proves nothing" in problem
                for problem in problems
            ),
            "a review_status the candidate's Markdown already carried was accepted as "
            f"proof that the Markdown half moved: {problems}",
        )

    def test_gutting_the_probe_description_is_caught_by_must_still_contain(self) -> None:
        """`must_still_contain`, the only guarantee the removal-only entry has left.

        Removing the stale "still untracked" claim by deleting the whole `GATE-E` probe
        description would satisfy the removal and destroy the thing being reconciled.
        `must_still_contain` is not evidence the reconciliation was made — `GATE-E` is
        already in the document — it is the guard against gutting the file, and it is
        the entry's only remaining protection, so it must be shown to fire.
        """
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
        self.sandbox.rewrite(
            "docs/architecture/ARCHITECTURE_LINT_RULES.md", "GATE-E", "GATE-Q"
        )
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(
            any(
                "does not carry 'GATE-E'" in problem
                and "stale GATE-E probe prose" in problem
                for problem in problems
            ),
            f"the probe description was deleted and the reconciliation passed: {problems}",
        )

    def test_the_review_json_and_markdown_must_agree_on_ratification(self) -> None:
        self._ratify_for_real()
        markdown = self.sandbox.root / REVIEW_MARKDOWN
        markdown.write_text(
            markdown.read_text(encoding="utf-8") + f"\n{REVIEW_DISCLAIMER}\n",
            encoding="utf-8",
        )
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(any(REVIEW_DISCLAIMER in problem for problem in problems), problems)

    def test_a_markdown_that_does_not_quote_the_declared_status_is_rejected(self) -> None:
        """The cross-document check itself, which nothing exercised.

        `_ratify_for_real` appends the status line to the Markdown in every probe, so the
        requirement that the Markdown quote the JSON's `review_status` was satisfied by
        the harness everywhere and deleting the check left the suite green. Here the
        harness does its job and then the line is taken away again: the machine-readable
        half says ratified and the human half no longer carries the word.
        """
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
        self.sandbox.rewrite(REVIEW_MARKDOWN, "Status: `ratified`.", "")
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(
            any("does not quote the review_status" in problem for problem in problems),
            f"the two halves of one review disagreed and nothing said so: {problems}",
        )

    def test_ratifying_while_the_status_is_still_the_unratified_one_is_rejected(
        self,
    ) -> None:
        """The other unexercised branch: `ratified: true` beside the pre-ratification
        status token.

        Asserted on the specific message rather than on "something was reported". Setting
        the status back also trips the *degeneracy* branch — the candidate's Markdown
        already carries that token — so a probe that only checked for a non-empty list
        would still pass with this branch deleted, which is exactly how it survived.
        """
        self._ratify_for_real()
        self.sandbox.patch_json(self.review, review_status=UNRATIFIED_REVIEW_STATUS)
        problems = _reconciliation_problems(self.sandbox.root)
        self.assertTrue(
            any(
                f"declares ratified while review_status is still "
                f"{UNRATIFIED_REVIEW_STATUS!r}" in problem
                for problem in problems
            ),
            f"a ratified review kept its pre-ratification status: {problems}",
        )

    def test_ratifying_on_an_unaccepted_round_is_rejected(self) -> None:
        """Both streams owed, no verdict, no reports — the probe's construction."""
        self.sandbox.declare_ratification(self.full_delta)
        self.sandbox.patch_json(self.review, ratified=True)
        self.sandbox.seal_digests(tested="1" * 64, evidence="2" * 64)
        problems = _acceptance_problems(self.sandbox.root)
        for expected in ("whose verdict is", "must leave a", "requires PASS"):
            self.assertTrue(
                any(expected in problem for problem in problems),
                f"{expected!r} not reported: {problems}",
            )

    def test_a_single_failing_stream_blocks_ratification(self) -> None:
        for streams in (("FAIL - 2 blockers", "PASS 6/6"), ("PASS", "FAIL - MT00-01")):
            with self.subTest(streams=streams):
                self._ratify_for_real(streams=streams)
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any("both streams must pass" in problem for problem in problems),
                    problems,
                )
                self.sandbox.restore()

    def test_a_missing_primary_report_blocks_ratification(self) -> None:
        self._ratify_for_real(reports=False)
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("must leave a" in problem for problem in problems), problems
        )

    def test_an_owed_stream_status_blocks_ratification(self) -> None:
        self._ratify_for_real(stream_status="owed")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(any("requires PASS" in problem for problem in problems), problems)

    def test_top_level_and_round_digests_must_agree(self) -> None:
        self._ratify_for_real()
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, tested_candidate_digest="d" * 64)
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("the per-round copy exists" in problem for problem in problems), problems
        )

    # ---- deletion, line wraps, and the anchors nothing anchors --------------------

    def test_a_reviewed_path_deleted_after_the_freeze_voids_the_round(self) -> None:
        """**B5.** Three ways a path can differ from the frozen tree; only two were
        tested.

        `_post_freeze_delta_problems` walks ``set(frozen) | set(present)``, so it reports
        a path that changed, one that was *added*, and one that was **deleted**.
        Restricting the walk to ``present`` — dropping the deletion case — left all 189
        tests green, and deleting `contracts/analysis/v1/README.md`, a file in one of the
        `IMMUTABLE_REVIEWED_PREFIXES` families, is exactly the drift this check exists to
        void a round over. A tree missing a reviewed file is not the tree the acceptance
        streams judged.
        """
        # The frozen digest has to be back in the manifest, or `_freeze_commit` finds
        # no commit and this check returns early — which is how the deletion case could
        # look covered while measuring nothing at all.
        self._ratify_for_real()
        self.assertIsNotNone(_freeze_commit(self.sandbox.root))
        self.assertEqual(
            _post_freeze_delta_problems(self.sandbox.root),
            [],
            "the sandbox already differs from the frozen tree, so a deletion would not "
            "isolate the deletion case",
        )
        deleted = f"{ANALYSIS}/README.md"
        self.sandbox._remember(deleted)
        (self.sandbox.root / deleted).unlink()
        self.assertFalse((self.sandbox.root / deleted).is_file())

        problems = _post_freeze_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("is void" in problem and deleted in problem for problem in problems),
            f"a reviewed file was deleted after the freeze and the round stayed live: "
            f"{problems}",
        )

    def test_the_state_document_denial_is_found_across_a_line_wrap(self) -> None:
        """**B7.** The report claimed the denial *does* wrap in the real document.

        It does not — `docs/program/CURRENT_STATE.md` carries the sentence entirely on
        one line — so the flattening was unmeasured and the prose said something the
        tree contradicts. Both are worth fixing rather than one: the flattening earns
        its place because a Markdown sentence is re-wrapped by any editor or formatter,
        and the day it wraps is the day an unmeasured check goes quietly silent. This is
        the probe that makes the claim true, and §11.16 states the corrected version of
        the prose.
        """
        document = self.sandbox.root / PROGRAM_STATE_DOCUMENT
        original = document.read_text(encoding="utf-8")
        self.assertIn(
            STATE_DOCUMENT_DENIAL, original, "the denial is not there to be wrapped"
        )
        head, _, tail = STATE_DOCUMENT_DENIAL.partition(" ")
        wrapped = original.replace(STATE_DOCUMENT_DENIAL, f"{head}\n{tail}")
        self.sandbox._remember(PROGRAM_STATE_DOCUMENT)
        document.write_text(wrapped, encoding="utf-8")
        self.assertNotIn(
            STATE_DOCUMENT_DENIAL,
            document.read_text(encoding="utf-8"),
            "the sentence did not actually cross a line, so this probe measures nothing",
        )

        # Unratified: the anchor is still found, so no anchor rot is reported.
        self.assertEqual(
            _state_document_problems(self.sandbox.root),
            [],
            "a re-wrapped denial was read as a missing denial, which would void the "
            "anti-vacuity anchor the moment anyone reflowed the document",
        )

        # Ratified: the same wrapped sentence must still be found and reported as
        # surviving into a ratified checkpoint.
        self._ratify_for_real()
        self.sandbox._remember(PROGRAM_STATE_DOCUMENT)
        document.write_text(wrapped, encoding="utf-8")
        self.assertTrue(
            any(
                f"still says {STATE_DOCUMENT_DENIAL!r}" in problem
                for problem in _state_document_problems(self.sandbox.root)
            ),
            "a ratified checkpoint shipped a state document that still denies the "
            "ratification, because the sentence had been re-wrapped",
        )

    def test_the_review_disclaimer_is_found_across_a_line_wrap(self) -> None:
        """**B7**, the second unmeasured flattening: the review Markdown comparison."""
        self._ratify_for_real()
        self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
        markdown = self.sandbox.root / REVIEW_MARKDOWN
        head, _, tail = REVIEW_DISCLAIMER.partition(" ")
        self.sandbox._remember(REVIEW_MARKDOWN)
        markdown.write_text(
            markdown.read_text(encoding="utf-8") + f"\nIt is {head}\n{tail}.\n",
            encoding="utf-8",
        )
        self.assertNotIn(
            REVIEW_DISCLAIMER,
            markdown.read_text(encoding="utf-8"),
            "the disclaimer did not cross a line, so this probe measures nothing",
        )
        self.assertTrue(
            any(
                REVIEW_DISCLAIMER in problem
                for problem in _reconciliation_problems(self.sandbox.root)
            ),
            "a ratified review still tells the reader it ratifies nothing, and the "
            "check missed it because the sentence was re-wrapped",
        )

    def test_the_sandbox_does_not_enumerate_its_own_virtual_environment(self) -> None:
        """The `.venv` exclude the sandbox writes into its own copied metadata.

        `.gitignore` ignores `.venv/` as a *directory*; in the sandbox it is a symlink,
        which that pattern does not match. Without the exclude the sandbox enumerates it
        as an untracked path, the digest recipe tries to read a directory, and
        `_reset_to_the_frozen_tree` deletes the sandbox's own symlink to the live
        virtual environment — after which every documented gate in that sandbox fails
        for a reason that has nothing to do with what it is testing. Removing the
        exclude left the suite green.
        """
        self.assertEqual(
            [path for path in _digest_paths(self.sandbox.root) if path.startswith(".venv")],
            [],
            "the sandbox enumerates its own .venv symlink",
        )
        self.assertTrue(
            (self.sandbox.root / ".venv").is_symlink(),
            "the sandbox lost its .venv symlink, so its documented gates cannot run",
        )
        self.assertTrue((self.sandbox.root / ".venv/bootstrap/bin/python").exists())

    # ---- round thirteen: the rest of what ratification writes ---------------------
    #
    # `W0-INT-01` must create eight evidence files, reconcile three more program
    # documents and close the status banners of the tasks CP-00 completes. None of that
    # was licensed, so an honest ratification voided its own round and the checkpoint
    # had no reachable published state. The licence is now granted; these are what it
    # was paid for.

    def _bundle(self, name: str) -> Path:
        return self.sandbox.root / (ACCEPTANCE_EVIDENCE_PREFIX + name)

    def test_the_published_bundle_is_licensed_and_still_observed(self) -> None:
        """The positive direction: a complete publication no longer voids its round.

        And the delta is not made invisible to buy that — every path the publication
        touches is still *observed* moving, exactly as
        `test_declared_ratification_of_the_whole_ceiling_is_accepted` requires of the
        architecture five. Licensed is not the same as unseen.
        """
        self._ratify_for_real()
        self.assertEqual(_post_freeze_delta_problems(self.sandbox.root), [])
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        frozen = _tree_blobs(self.sandbox.root, self.sandbox.frozen_commit)
        moved = {
            path
            for path in _digest_paths(self.sandbox.root)
            if (self.sandbox.root / path).is_file()
            and (
                path not in frozen
                or (self.sandbox.root / path).read_bytes() != frozen[path]
            )
        }
        for group, label in (
            (CHECKPOINT_DELIVERABLE_PATHS, "the evidence bundle"),
            (PUBLICATION_DOCUMENT_PATHS, "the publication documents"),
            ({RATIFYING_TASK_FILE}, "the ratifying task banner"),
            ({ACCEPTANCE_RECORD}, "the acceptance record"),
        ):
            with self.subTest(group=label):
                self.assertEqual(
                    sorted(set(group) - moved),
                    [],
                    f"{label} did not move, so this probe proves nothing about the "
                    "licence",
                )

    def test_the_acceptance_record_may_not_be_behind_the_manifest(self) -> None:
        """The axis rounds seven and eight failed on, checked in both states.

        The record of the rounds is the document a reader is pointed at, and it is
        written after a round reports — which is after that round's freeze. Licensing it
        is what makes recording a verdict possible at all; this is what the licence is
        paid for, and it can fail whether or not anything is ratified.
        """
        record = self.sandbox.root / ACCEPTANCE_RECORD
        manifest = _checkpoint_manifest(self.sandbox.root) or {}
        reported = [
            entry["round"]
            for entry in manifest.get("acceptance_rounds", [])
            if isinstance(entry, dict) and entry.get("verdict")
        ]
        self.assertTrue(reported, "no round carries a verdict, so this probe measures nothing")

        # Unratified: the rule is already live.
        self.assertEqual(_acceptance_record_problems(self.sandbox.root), [])
        self.sandbox._remember(ACCEPTANCE_RECORD)
        text = record.read_text(encoding="utf-8")
        dropped = re.sub(rf"^\|\s*{reported[-1]}\s*\|.*$", "", text, count=1, flags=re.M)
        self.assertNotEqual(dropped, text, "the probe removed no row")
        record.write_text(dropped, encoding="utf-8")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any(f"no row for round {reported[-1]}" in problem for problem in problems),
            f"the acceptance record lost a reported round and nothing said so: {problems}",
        )
        self.sandbox.restore()

        # Ratified: the round being ratified must be in it, and recorded as passing.
        self._ratify_for_real()
        self.assertEqual(_acceptance_record_problems(self.sandbox.root), [])
        number = (_checkpoint_manifest(self.sandbox.root) or {})["current_round"]
        published = record.read_text(encoding="utf-8")
        record.write_text(
            re.sub(rf"^\|\s*{number}\s*\|.*$", "", published, count=1, flags=re.M),
            encoding="utf-8",
        )
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any(f"no row for round {number}" in problem for problem in problems),
            f"CP-00 ratified on a round its own record does not carry: {problems}",
        )
        record.write_text(
            published.replace(f"| {number} | **PASS**", f"| {number} | FAIL"),
            encoding="utf-8",
        )
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("A checkpoint is ratified on a round both streams passed" in problem
                for problem in problems),
            f"CP-00 ratified on a round its own record calls failed: {problems}",
        )

    def test_gutting_the_acceptance_record_is_not_a_way_to_satisfy_it(self) -> None:
        """Completeness over a deleted table is completeness over nothing."""
        self._ratify_for_real()
        record = self.sandbox.root / ACCEPTANCE_RECORD
        record.write_text("# CP-00 acceptance record\n", encoding="utf-8")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any(ACCEPTANCE_RECORD_HEADING in problem for problem in problems), problems
        )

    def test_a_manifest_reporting_no_round_makes_the_record_rule_vacuous(self) -> None:
        """The anti-vacuity guard is on the manifest side, where the emptying happens."""
        self.sandbox._remember(CHECKPOINT_MANIFEST)
        path = self.sandbox.root / CHECKPOINT_MANIFEST
        document = json.loads(path.read_text(encoding="utf-8"))
        for entry in document["acceptance_rounds"]:
            entry["verdict"] = None
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        problems = _acceptance_record_problems(self.sandbox.root)
        self.assertTrue(
            any("records no round with a verdict" in problem for problem in problems),
            problems,
        )

    def test_a_publication_missing_any_deliverable_is_rejected(self) -> None:
        """One file at a time, because "the bundle is there" is not eight statements."""
        for entry in CHECKPOINT_DELIVERABLES:
            with self.subTest(deliverable=entry["name"]):
                self._ratify_for_real()
                relative = ACCEPTANCE_EVIDENCE_PREFIX + entry["name"]
                self.sandbox.restore_one(relative)
                self.assertFalse((self.sandbox.root / relative).exists())
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(relative in problem and "is missing" in problem for problem in problems),
                    f"a checkpoint published without {entry['name']} was accepted: {problems}",
                )
                self.sandbox.restore()

    def test_every_deliverable_content_requirement_is_load_bearing(self) -> None:
        """Emptying each file in turn. A path that may move proves nothing.

        This is round four's finding one level out: there, five files were declared and
        four were edited with a comment. Here the licence is to *create* eight files,
        and a licence to create a file is satisfied by creating an empty one.
        """
        for entry in CHECKPOINT_DELIVERABLES:
            with self.subTest(deliverable=entry["name"]):
                self._ratify_for_real()
                relative = ACCEPTANCE_EVIDENCE_PREFIX + entry["name"]
                (self.sandbox.root / relative).write_text(
                    "published\n", encoding="utf-8"
                )
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(relative in problem for problem in problems),
                    f"an empty {entry['name']} satisfied its requirement: {problems}",
                )
                self.sandbox.restore()

    def test_a_contract_manifest_describing_another_tree_is_rejected(self) -> None:
        """The values are recomputed, so a bundle copied from another checkpoint fails.

        Three separate values, each mutated on its own: the candidate commit, the
        reviewed-family digest, and one of the five recorded hashes. A single probe over
        the file would not distinguish them, and `hashes` covering five paths would be
        satisfied by any one of them being right.
        """
        relative = ACCEPTANCE_EVIDENCE_PREFIX + "contract-manifest.yaml"
        manifest = _checkpoint_manifest(self.sandbox.root) or {}
        cases = {
            "candidate commit": (REVIEWED_CANDIDATE_COMMIT, "f" * 40),
            "reviewed manifest digest": (None, "0" * 64),
            "lock hash": (None, "1" * 64),
        }
        for label in cases:
            with self.subTest(value=label):
                self._ratify_for_real()
                path = self.sandbox.root / relative
                text = path.read_text(encoding="utf-8")
                if label == "candidate commit":
                    old, new = cases[label]
                elif label == "reviewed manifest digest":
                    old = _reviewed_manifest_digest(self.sandbox.root)[0]
                    new = cases[label][1]
                else:
                    old = hashlib.sha256(
                        (self.sandbox.root / "requirements/validation.lock").read_bytes()
                    ).hexdigest()
                    new = cases[label][1]
                self.assertIn(old, text, f"the harness never wrote the {label}")
                path.write_text(text.replace(old, new), encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(relative in problem for problem in problems),
                    f"a contract manifest with the wrong {label} was accepted: {problems}",
                )
                self.sandbox.restore()
        self.assertIsInstance(manifest, dict)

    def test_every_anti_vacuity_guard_in_the_bundle_checks_can_fire(self) -> None:
        """The guards that say "this requirement proves nothing", each made to say it.

        Four branches whose whole job is to refuse a *vacuous pass* -- a requirement that
        is satisfied because the thing it measures is absent rather than because it is
        right. An independent reviewer removed each one and the whole suite stayed green:
        they were live and untested, which is the same standing as absent, because
        nothing would notice if a later edit made them unreachable. Each is reached here
        by creating the condition it exists to name.

        The checklist anchor is reached by call rather than through a sandbox: its
        condition is "the document carries no checklist **at the reviewed candidate**",
        and the reviewed candidate is immutable by construction. Passing a document that
        genuinely has no checklist there is the honest way to reach it; faking a
        candidate would be measuring the fake.
        """
        self._ratify_for_real()
        root = self.sandbox.root
        self.assertEqual(_checkpoint_bundle_problems(root), [])

        # 1. The manifest declares no runtime disposition, so requiring the manual report
        #    to carry it proves nothing.
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, runtime_fields="   ")
        self.assertTrue(
            any(
                "records no runtime_fields disposition" in problem
                for problem in _checkpoint_bundle_problems(root)
            ),
            "a blank runtime_fields left the manual-report requirement passing on air",
        )
        self.sandbox.restore_one(CHECKPOINT_MANIFEST)
        self.assertEqual(_checkpoint_bundle_problems(root), [])

        # 2. A hashed source that is not in the repository, so requiring the contract
        #    manifest to carry its hash proves nothing. Reached by entry data rather than
        #    by deleting the real source: every hashed source is a tracked file inside an
        #    immutable reviewed family, and removing one from the tree breaks the digest
        #    recipe that reads it -- the probe would then be measuring its own damage.
        hashed = sorted(
            value
            for entry in CHECKPOINT_DELIVERABLES
            for value in entry.get("hashes", ())
        )
        self.assertTrue(hashed, "no deliverable declares a hashed source any more")
        for real in hashed:
            self.assertTrue(
                (root / real).is_file(),
                f"{real} is declared as a hashed source and is not in the tree, so the "
                "guard under test is already firing for real",
            )
        absent = "requirements/THIS-LOCK-DOES-NOT-EXIST.lock"
        self.assertFalse((root / absent).is_file())
        manifest = _checkpoint_manifest(root) or {}
        entry = dict(CHECKPOINT_DELIVERABLES[0])
        entry["hashes"] = (absent,)
        self.assertTrue(
            any(
                absent in problem and "proves nothing" in problem
                for problem in _deliverable_content_problems(
                    root,
                    manifest,
                    entry,
                    ACCEPTANCE_EVIDENCE_PREFIX + entry["name"],
                    "anything at all",
                    True,
                )
            ),
            "a hashed source that is not in the repository left its requirement passing "
            "on air",
        )
        self.assertEqual(_checkpoint_bundle_problems(root), [])

        # 3. A manual case named with no verdict at all: a report records a verdict per
        #    case, not a mention per case.
        report = ACCEPTANCE_EVIDENCE_PREFIX + "manual-test-report.md"
        self.assertIn(report, CHECKPOINT_DELIVERABLE_PATHS)
        self.sandbox._remember(report)
        text = (root / report).read_text(encoding="utf-8")
        case = _manual_case_ids(root)[0]
        stripped = "\n".join(
            line if case not in line else f"| {case} | (no verdict recorded) |"
            for line in text.splitlines()
        )
        (root / report).write_text(stripped + "\n", encoding="utf-8")
        self.assertTrue(
            any(
                case in problem and "verdict per case" in problem
                for problem in _checkpoint_bundle_problems(root)
            ),
            f"{case} was named without a verdict and nothing said so",
        )
        (root / report).write_text(text, encoding="utf-8")
        self.assertEqual(_checkpoint_bundle_problems(root), [])

        # 4. The checklist anchor, reached by call.
        boxless = "docs/INDEX.md"
        self.assertIsNotNone(
            _candidate_blob(root, boxless),
            f"{boxless} is not at the reviewed candidate, so this case cannot reach the "
            "anchor-rot branch",
        )
        self.assertEqual(
            re.findall(r"- \[[ xX]\]", _candidate_blob(root, boxless).decode("utf-8")),
            [],
            f"{boxless} carries checkbox syntax at the reviewed candidate, so it is no "
            "longer a document that reaches the anchor-rot branch",
        )
        self.assertEqual(
            _checklist_problems(root, boxless, "- [x] ticked\n", True),
            [
                f"anchor rot: {boxless} carries no checklist at the reviewed candidate, "
                "so requiring ratification to complete one proves nothing"
            ],
        )

    def test_a_manual_report_that_does_not_pass_every_case_cannot_ratify(self) -> None:
        """Deliverable 3, one failure mode at a time.

        The case list comes from the runbook, so a report that simply omits a case is
        caught by the same check that catches one recording a `FAIL` — and both are
        caught while the manifest's own `manual_acceptance` says `PASS`, which is the
        contradiction a checkpoint may not ship.
        """
        relative = ACCEPTANCE_EVIDENCE_PREFIX + "manual-test-report.md"
        cases = _manual_case_ids(self.sandbox.root)
        self.assertTrue(cases, "the runbook defines no manual cases")
        mutations = {
            "a failed case": lambda text: text.replace(
                f"| {cases[2]} | PASS |", f"| {cases[2]} | FAIL |"
            ),
            "a missing case": lambda text: "\n".join(
                line for line in text.splitlines() if cases[-1] not in line
            ),
            "a case with no verdict": lambda text: text.replace(
                f"| {cases[0]} | PASS |", f"| {cases[0]} | |"
            ),
            "no tester": lambda text: text.replace(
                "tester: independent CP-00 manual tester", "tester:"
            ),
            "no timestamp": lambda text: text.replace(
                "started_at: 2026-09-04T09:00:00Z", "started_at: whenever"
            ),
            "no runtime disposition": lambda text: text.replace(
                "backend_runtime: not applicable", "backend_runtime: 1.0"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(mutation=label):
                self._ratify_for_real()
                path = self.sandbox.root / relative
                before = path.read_text(encoding="utf-8")
                after = mutate(before)
                self.assertNotEqual(before, after, "the mutation changed nothing")
                path.write_text(after, encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(relative in problem for problem in problems),
                    f"a manual report with {label} was accepted: {problems}",
                )
                self.sandbox.restore()

    def test_a_runbook_defining_no_cases_is_reported_not_satisfied(self) -> None:
        """The manual case list is an anchor, so it has to be able to rot loudly.

        Every case in the report is required because the runbook names it. A runbook
        that named none would make the whole per-case requirement a loop over nothing —
        the emptying defect again, one document further out — so the empty case list is
        reported rather than passed.
        """
        self._ratify_for_real()
        self.assertEqual(_checkpoint_bundle_problems(self.sandbox.root), [])
        with unittest.mock.patch.object(
            sys.modules[__name__], "MANUAL_RUNBOOK", "docs/INDEX.md"
        ):
            self.assertEqual(_manual_case_ids(self.sandbox.root), [])
            problems = _checkpoint_bundle_problems(self.sandbox.root)
        self.assertTrue(
            any("defines no MT00 case IDs" in problem for problem in problems), problems
        )

    def test_build_information_must_be_an_object_and_not_merely_valid_json(self) -> None:
        """The one deliverable whose only stated requirement is its shape.

        Emptying the file is caught by the value it has to name, so that mutation does
        not isolate the shape branch. A JSON *array* carrying the same value does: it
        parses, it names the commit, and it is not a record of anything.
        """
        relative = ACCEPTANCE_EVIDENCE_PREFIX + "build-info.json"
        for label, body in (
            ("an array", json.dumps([REVIEWED_CANDIDATE_COMMIT])),
            ("an empty object", json.dumps({"note": REVIEWED_CANDIDATE_COMMIT}) and "{}"),
        ):
            with self.subTest(shape=label):
                self._ratify_for_real()
                (self.sandbox.root / relative).write_text(body + "\n", encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(relative in problem for problem in problems),
                    f"build information recorded as {label} was accepted: {problems}",
                )
                self.sandbox.restore()

    def test_a_retracted_claim_written_back_is_named(self) -> None:
        """The denial branch on its own.

        Restoring a whole document removes its new statement as well, so that probe
        cannot tell which of the two checks fired. Here the reconciliation is left
        entirely in place and only the retracted claim is put back — which is what a
        document says when somebody edits it after ratification and forgets what the
        ratification was for.
        """
        for entry in RATIFICATION_PUBLICATION_RECORDS:
            if not entry["denials"]:
                continue
            with self.subTest(item=entry["item"]):
                self._ratify_for_real()
                path = self.sandbox.root / entry["path"]
                text = path.read_text(encoding="utf-8")
                denial = entry["denials"][0]
                if entry.get("row"):
                    lines = text.splitlines()
                    row = next(line for line in lines if entry["row"] in line)
                    text = text.replace(row, f"{row} ({denial})")
                else:
                    text += f"\n{denial}\n"
                path.write_text(text, encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(denial in problem and entry["item"] in problem
                        for problem in problems),
                    f"{entry['item']} kept saying {denial!r} after ratification: "
                    f"{problems}",
                )
                self.sandbox.restore()

    def test_a_risk_note_that_drops_a_recorded_risk_is_rejected(self) -> None:
        """The bundle may not be a shorter story than the record it publishes."""
        relative = ACCEPTANCE_EVIDENCE_PREFIX + "known-risks.md"
        for dropped in ("ADR-0014", "U-04", "E-06"):
            with self.subTest(risk=dropped):
                self._ratify_for_real()
                path = self.sandbox.root / relative
                path.write_text(
                    "\n".join(
                        line
                        for line in path.read_text(encoding="utf-8").splitlines()
                        if dropped not in line
                    )
                    + "\n",
                    encoding="utf-8",
                )
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(dropped in problem and relative in problem for problem in problems),
                    f"a risk note that dropped {dropped} was accepted: {problems}",
                )
                self.sandbox.restore()

    def test_a_manifest_field_naming_nothing_is_reported_not_satisfied(self) -> None:
        """The table-emptying defect one level down, in the data instead of the table.

        `known-risks.md` is required to name every entry of three manifest fields. Empty
        the field and the loop runs zero times, so the requirement would be satisfied by
        a risk note that names nothing at all.
        """
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, architecture_defer=[])
        problems = _checkpoint_bundle_problems(self.sandbox.root)
        self.assertTrue(
            any("architecture_defer names nothing" in problem for problem in problems),
            problems,
        )

    def test_a_deliverable_that_already_exists_at_the_candidate_licenses_nothing(self) -> None:
        """Anti-vacuity: "ratification must create it" needs it not to be there already.

        Nothing under `artifacts/` exists at the reviewed candidate, so the live table
        cannot demonstrate this. A substituted table naming a document that *is* there
        can, and the check must refuse it rather than pass forever.
        """
        with unittest.mock.patch.object(
            sys.modules[__name__], "ACCEPTANCE_EVIDENCE_PREFIX", "docs/"
        ), unittest.mock.patch.object(
            sys.modules[__name__],
            "CHECKPOINT_DELIVERABLES",
            ({"name": "INDEX.md", "requires": ("CP-00",), "note": "a probe"},),
        ):
            problems = _checkpoint_bundle_problems(self.sandbox.root)
        self.assertTrue(
            any("degenerate requirement" in problem for problem in problems), problems
        )

    def test_the_bundle_is_checked_before_ratification_as_well(self) -> None:
        """The unratified branch is not a skip.

        Absence is silent — the integrator has not written the bundle yet, and requiring
        it before the act would be as wrong as never requiring it. Content is not: a
        file that exists and describes the wrong tree is wrong the moment it is written,
        and waiting for the flag to say so is how a check ends up unable to fail.
        """
        self.assertEqual(_checkpoint_bundle_problems(self.sandbox.root), [])
        relative = ACCEPTANCE_EVIDENCE_PREFIX + "migration-head.txt"
        self.sandbox._remember(relative)
        (self.sandbox.root / relative).write_text("head-of-the-line\n", encoding="utf-8")
        problems = _checkpoint_bundle_problems(self.sandbox.root)
        self.assertTrue(
            any(relative in problem for problem in problems),
            f"a wrong deliverable written before ratification passed: {problems}",
        )
        self.assertFalse(
            any("is missing" in problem for problem in problems),
            "the seven unwritten deliverables were demanded before the ratification "
            "that is supposed to create them",
        )

    def test_each_publication_claim_left_standing_is_named(self) -> None:
        """One document at a time: retract two of three and the third is named."""
        for entry in RATIFICATION_PUBLICATION_RECORDS:
            with self.subTest(item=entry["item"]):
                self._ratify_for_real()
                self.sandbox.restore_one(entry["path"])
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(entry["item"] in problem for problem in problems),
                    f"{entry['item']} was left at its pre-ratification state and the "
                    f"checkpoint ratified anyway: {problems}",
                )
                self.sandbox.restore()

    def test_the_publication_requirements_are_checked_before_ratification_too(self) -> None:
        """Both directions on the live documents, the shape §11.12.3 established.

        Reword the claim while CP-00 is unratified and the check fails **now**, saying
        so, instead of passing forever once the sentence it was waiting to see removed
        is already gone. Write the post-ratification requirement early and it is
        reported as degenerate for the same reason.
        """
        wave = RATIFICATION_PUBLICATION_RECORDS[0]
        self.sandbox._retract(
            wave["path"], wave["denials"][0], "`W0-INT-01` is proceeding"
        )
        problems = _publication_record_problems(self.sandbox.root)
        self.assertTrue(
            any("anchor rot" in problem and wave["path"] in problem for problem in problems),
            problems,
        )
        self.sandbox.restore()

        self.sandbox._append(wave["path"], "\nS01 preparation may begin.\n")
        problems = _publication_record_problems(self.sandbox.root)
        self.assertTrue(
            any("degenerate requirement" in problem for problem in problems), problems
        )
        self.sandbox.restore()

        # The structural half of the same anchor. A checklist already ticked before the
        # checkpoint is ratified cannot show that ratification ticked it.
        stage = RATIFICATION_PUBLICATION_RECORDS[1]["path"]
        self.sandbox._remember(stage)
        path = self.sandbox.root / stage
        path.write_text(
            path.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8"
        )
        problems = _publication_record_problems(self.sandbox.root)
        self.assertTrue(
            any("anchor rot" in problem and "already ticked" in problem
                for problem in problems),
            problems,
        )

    def test_an_automated_summary_that_contradicts_the_record_is_rejected(self) -> None:
        """The `requires` and `values` branches on one file, isolated from each other.

        Cross-record only, and the note on the table says so: the manifest already has
        to record `PASS` for the round being ratified, so what this catches is a summary
        that contradicts the record it summarises or belongs to another round. It is not
        an independent verification that the suite passed.
        """
        relative = ACCEPTANCE_EVIDENCE_PREFIX + "automated-summary.txt"
        number = (_checkpoint_manifest(self.sandbox.root) or {})["current_round"]
        for label, old, new in (
            ("a contradicted verdict", "PASS", "FAIL"),
            ("another round", f"round {number}", f"round {number + 1}"),
        ):
            with self.subTest(mutation=label):
                self._ratify_for_real()
                path = self.sandbox.root / relative
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text)
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(relative in problem for problem in problems),
                    f"an automated summary naming {label} was accepted: {problems}",
                )
                self.sandbox.restore()

    def test_every_anti_gutting_needle_is_load_bearing_on_its_own(self) -> None:
        """One probe per needle, because a probe over the loop proves only the loop.

        The probe below drops the whole `must_still_contain` iteration and goes red, and
        that was taken as evidence the anti-gutting guard was paid for. It is not: with
        five needles across three documents, a single end-to-end case can be satisfied by
        *any one* of them, and an independent reviewer measured the consequence -- the
        S00 entry's two needles could be emptied and the wave entry reduced to one with
        the whole suite green, and all three publication documents could then be reduced
        to the strings the check looks for (16031 -> 46, 6179 -> 131, 2519 -> 73 bytes)
        with nothing reported. "A mutation probe proves only what it mutates" is this
        module's own rule; here it is applied to its own needles.

        Each needle is removed from its document in turn, on an otherwise complete
        ratification, and must be named. The `assertIn` before each removal is the
        anti-vacuity half: a needle that has already drifted out of the document would
        make its case pass by removing nothing.
        """
        # Pinned per entry, and deliberately not derived from the table this probe
        # iterates. A count computed from that table is satisfied by any table -- the
        # first form of this probe asserted `checked >= 5` and both surviving mutants
        # walked through it, because emptying one entry's two needles still left five
        # across the other two. A licence may be reduced; it may not be reduced silently.
        expected_needles = {
            "docs/program/waves/W0.3_ratification_integration.md": 2,
            "docs/stages/S00_architecture_and_behavior_freeze.md": 2,
            "docs/INDEX.md": 3,
        }
        self._ratify_for_real()
        self.assertEqual(_publication_record_problems(self.sandbox.root), [])
        self.assertEqual(
            {e["path"] for e in RATIFICATION_PUBLICATION_RECORDS},
            set(expected_needles),
            "the publication document set moved; re-read why before re-pinning",
        )
        checked = 0
        for entry in RATIFICATION_PUBLICATION_RECORDS:
            relative = entry["path"]
            path = self.sandbox.root / relative
            self.assertEqual(
                len(entry["must_still_contain"]),
                expected_needles[relative],
                f"{relative} carries {len(entry['must_still_contain'])} anti-gutting "
                f"needles, not {expected_needles[relative]}. Dropping one drops the only "
                "thing standing between 'this document was updated' and 'this document "
                "was deleted down to the string the check looks for'.",
            )
            for needle in entry["must_still_contain"]:
                with self.subTest(document=relative, needle=needle):
                    self.sandbox._remember(relative)
                    before = path.read_text(encoding="utf-8")
                    self.assertIn(
                        needle,
                        before,
                        f"{relative} no longer carries {needle!r}, so removing it "
                        "removes nothing and this case proves nothing. Re-anchor the "
                        "needle in RATIFICATION_PUBLICATION_RECORDS.",
                    )
                    path.write_text(before.replace(needle, ""), encoding="utf-8")
                    problems = _publication_record_problems(self.sandbox.root)
                    path.write_text(before, encoding="utf-8")
                    self.assertTrue(
                        any(
                            relative in problem and repr(needle) in problem
                            for problem in problems
                        ),
                        f"{relative} was gutted of {needle!r} and nothing said so: "
                        f"{problems}",
                    )
                    checked += 1
        self.assertEqual(
            checked,
            sum(expected_needles.values()),
            "a needle was skipped rather than checked",
        )
        self.assertEqual(_publication_record_problems(self.sandbox.root), [])

    def test_deleting_a_licensed_path_is_reported_for_every_licensed_group(self) -> None:
        """Ratification may *move* these paths. Nothing said it may not delete them.

        Each of the three groups this round newly licensed reports a missing file, and
        until now not one of those branches had ever been executed by a test: an
        independent reviewer removed all three reports in turn and the whole suite stayed
        green. That is the difference between a guard that is live and a guard that is
        merely present -- and it matters most exactly here, because the reason these
        paths are in :data:`POST_FREEZE_DELTA_CEILING` at all is that ratification writes
        to them, so "moved" and "deleted at ratification" are one keystroke apart and the
        delta check cannot tell them apart.

        The eight checkpoint deliverables are not in this probe: their missing-file branch
        is already exercised by
        :meth:`test_a_publication_missing_any_deliverable_is_rejected`.
        """
        self._ratify_for_real()
        self.assertEqual(_publication_record_problems(self.sandbox.root), [])
        self.assertEqual(_acceptance_record_problems(self.sandbox.root), [])
        self.assertEqual(_task_banner_problems(self.sandbox.root), [])

        groups = (
            (
                "a licensed publication document",
                sorted(PUBLICATION_DOCUMENT_PATHS)[0],
                _publication_record_problems,
            ),
            ("the acceptance record", ACCEPTANCE_RECORD, _acceptance_record_problems),
            (
                "a licensed task file",
                sorted(COMPLETED_TASK_FILES)[0],
                _task_banner_problems,
            ),
        )
        for label, relative, checker in groups:
            with self.subTest(group=label, path=relative):
                self.assertIn(
                    relative,
                    POST_FREEZE_DELTA_CEILING,
                    f"{relative} is not licensed, so this case is not about the "
                    "deletion of a licensed path any more",
                )
                path = self.sandbox.root / relative
                self.sandbox._remember(relative)
                kept = path.read_bytes()
                path.unlink()
                problems = checker(self.sandbox.root)
                path.write_bytes(kept)
                self.assertTrue(
                    any(
                        relative in problem and "is missing" in problem
                        for problem in problems
                    ),
                    f"{label} was deleted at ratification and nothing said so: "
                    f"{problems}",
                )
        self.assertEqual(len(groups), 3)
        self.assertEqual(_publication_record_problems(self.sandbox.root), [])
        self.assertEqual(_acceptance_record_problems(self.sandbox.root), [])
        self.assertEqual(_task_banner_problems(self.sandbox.root), [])

    def test_a_publication_document_missing_its_statement_or_its_subject_is_named(self) -> None:
        """The two remaining branches: the new statement, and what it was about.

        Retracting the stale claim is half the job. A wave plan that says nothing about
        what CP-00 unlocked has not been reconciled with the checkpoint, and one that
        satisfies the retraction by deleting the tag it was about has been gutted — the
        distinction `must_still_contain` exists for and the one round four's probe
        walked straight through one level up.
        """
        wave = RATIFICATION_PUBLICATION_RECORDS[0]
        for label, old in (
            ("the new statement", "\n## Next unlocked tasks\n\nCP-00 is ratified and tagged; "
                                  "the S01 repository-foundation preparation tasks are unlocked.\n"),
            ("the tag it was about", "`v0.0.0-architecture`"),
        ):
            with self.subTest(missing=label):
                self._ratify_for_real()
                path = self.sandbox.root / wave["path"]
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text)
                path.write_text(text.replace(old, ""), encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(wave["item"] in problem for problem in problems),
                    f"a wave plan without {label} was accepted: {problems}",
                )
                self.sandbox.restore()

    def test_a_row_scoped_requirement_needs_exactly_one_row(self) -> None:
        """Two rows for one task is not a status; it is two statuses."""
        index = RATIFICATION_PUBLICATION_RECORDS[2]
        self._ratify_for_real()
        path = self.sandbox.root / index["path"]
        lines = path.read_text(encoding="utf-8").splitlines()
        row = next(line for line in lines if index["row"] in line)
        path.write_text("\n".join(lines + [row]) + "\n", encoding="utf-8")
        problems = _publication_record_problems(self.sandbox.root)
        self.assertTrue(
            any("carries 2 rows" in problem for problem in problems), problems
        )

    def test_the_stage_checklist_is_completed_and_not_shortened(self) -> None:
        """A ticked box is content; a deleted checklist is the gutting move."""
        stage = RATIFICATION_PUBLICATION_RECORDS[1]["path"]
        self._ratify_for_real()
        path = self.sandbox.root / stage
        published = path.read_text(encoding="utf-8")
        path.write_text(published.replace("- [x]", "- [ ]", 1), encoding="utf-8")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("unticked" in problem and stage in problem for problem in problems),
            f"CP-00 ratified with its own exit evidence outstanding: {problems}",
        )

        path.write_text(
            "\n".join(
                line
                for line in published.splitlines()
                if "- [x]" not in line
            )
            + "\nS01\n",
            encoding="utf-8",
        )
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("shortening" in problem or "boxes and the reviewed candidate" in problem
                for problem in problems),
            f"the checklist was completed by deleting it: {problems}",
        )

    def test_the_index_requirement_is_scoped_to_the_row(self) -> None:
        """The index already says "accepted and integrated" six times.

        A document-wide needle would therefore be satisfied by every other task's row,
        and the one row that still calls the ratifying task blocked would never be read.
        """
        index = RATIFICATION_PUBLICATION_RECORDS[2]
        self._ratify_for_real()
        self.sandbox.restore_one(index["path"])
        self.assertIn(
            "accepted and integrated",
            (self.sandbox.root / index["path"]).read_text(encoding="utf-8"),
            "the index no longer carries the phrase elsewhere, so this probe is not "
            "measuring the scoping",
        )
        problems = _publication_record_problems(self.sandbox.root)
        self.assertTrue(
            any(index["item"] in problem for problem in problems),
            f"the unretracted row passed on another row's status: {problems}",
        )

    def test_a_task_file_changed_outside_its_banner_is_named(self) -> None:
        """The licence is the status banner. The rest of an accepted task is frozen."""
        victim = "docs/program/tasks/W0-ARC-01.md"
        self._ratify_for_real()
        self.assertEqual(_task_banner_problems(self.sandbox.root), [])
        self.sandbox.edit(victim, marker="\n## Extra deliverable\n\nAnd one more.\n")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any(victim in problem and "outside its status banner" in problem
                for problem in problems),
            f"an accepted task's deliverables were rewritten at ratification: {problems}",
        )

    def test_a_banner_edit_is_what_the_licence_permits(self) -> None:
        """The positive direction, or the check above is satisfied by refusing always."""
        closed = "docs/program/tasks/W0-CLN-01.md"
        self._ratify_for_real()
        frozen = _tree_blobs(self.sandbox.root, self.sandbox.frozen_commit)
        self.assertNotEqual(
            (self.sandbox.root / closed).read_bytes(),
            frozen[closed],
            "the harness closed no other task's banner, so nothing here is permitted "
            "that could have been refused",
        )
        self.assertEqual(_task_banner_problems(self.sandbox.root), [])

    def test_a_removed_status_banner_is_named(self) -> None:
        """Closing a banner is not deleting one."""
        closed = "docs/program/tasks/W0-CLN-01.md"
        self._ratify_for_real()
        path = self.sandbox.root / closed
        banner, rest = _banner_split(path.read_text(encoding="utf-8"))
        self.assertTrue(banner, "the probe removed nothing")
        path.write_text(rest, encoding="utf-8")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any(closed in problem and "banner is gone" in problem for problem in problems),
            problems,
        )

    def test_the_ratifying_task_banner_moves_in_both_directions(self) -> None:
        """The one banner ratification must close, and no other task may."""
        flat = _flat((self.sandbox.root / RATIFYING_TASK_FILE).read_text(encoding="utf-8"))
        self.assertIn(RATIFYING_TASK_BANNER_DENIAL, flat)
        self.assertEqual(_task_banner_problems(self.sandbox.root), [])

        self.sandbox._retract(
            RATIFYING_TASK_FILE, RATIFYING_TASK_BANNER_DENIAL, "under way"
        )
        problems = _task_banner_problems(self.sandbox.root)
        self.assertTrue(
            any("anchor rot" in problem for problem in problems),
            f"the denial was reworded while CP-00 is unratified and nothing said so: "
            f"{problems}",
        )
        self.sandbox.restore()

        # And the other side of the same anchor: a banner that names the published tag
        # before there is a publication cannot show that ratification named it.
        self.sandbox._retract(
            RATIFYING_TASK_FILE,
            RATIFYING_TASK_BANNER_DENIAL,
            f"{RATIFYING_TASK_BANNER_DENIAL}; the tag will be `{CHECKPOINT_TAG}`",
        )
        problems = _task_banner_problems(self.sandbox.root)
        self.assertTrue(
            any("degenerate requirement" in problem for problem in problems), problems
        )
        self.sandbox.restore()

        # Each of the ratified branches on its own. Restoring the whole file would
        # remove the tag as well, so one probe would answer for two checks and neither
        # would be measured.
        closed = f"ratified and published as `{CHECKPOINT_TAG}`"
        for label, mutate in (
            (
                "the denial written back beside the tag",
                lambda text: text.replace(
                    closed, f"{closed}; {RATIFYING_TASK_BANNER_DENIAL}"
                ),
            ),
            ("the tag not named", lambda text: text.replace(closed, "ratified")),
        ):
            with self.subTest(mutation=label):
                self._ratify_for_real()
                path = self.sandbox.root / RATIFYING_TASK_FILE
                text = path.read_text(encoding="utf-8")
                self.assertIn(closed, text, "the harness closed no banner to mutate")
                path.write_text(mutate(text), encoding="utf-8")
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(RATIFYING_TASK_FILE in problem for problem in problems),
                    f"{label}: {problems}",
                )
                self.sandbox.restore()

    def test_the_ratifying_task_may_rewrite_its_own_handoff_and_nothing_else(self) -> None:
        """The second half of `W0-INT-01`'s own allowed path, and only that half."""
        self._ratify_for_real()
        path = self.sandbox.root / RATIFYING_TASK_FILE
        text = path.read_text(encoding="utf-8")
        self.assertIn("\n## Handoff", text, "the anchor this exception is cut at is gone")
        path.write_text(text + "\n- pushed main, the branch and the tag.\n", encoding="utf-8")
        self.assertEqual(
            _task_banner_problems(self.sandbox.root),
            [],
            "the ratifying task may record its own handoff",
        )
        path.write_text(
            text.replace("## Outcome", "## Outcome (revised)"), encoding="utf-8"
        )
        problems = _task_banner_problems(self.sandbox.root)
        self.assertTrue(
            any(RATIFYING_TASK_FILE in problem and "outside its status banner" in problem
                for problem in problems),
            f"the ratifying task rewrote its own outcome and passed: {problems}",
        )

    def test_the_new_licences_are_named_files_and_not_directories(self) -> None:
        """A ceiling that is a *prefix* is a ceiling anyone can widen by adding a file.

        Two strangers, one under the evidence prefix and one in the task directory,
        neither of them a licensed name. Both must void the round, or the licence is on
        `artifacts/checkpoints/CP-00/**` and `docs/program/tasks/**` rather than on the
        eight and the seventeen this module names.
        """
        self._ratify_for_real()
        self.assertEqual(_post_freeze_delta_problems(self.sandbox.root), [])
        for stranger in (
            ACCEPTANCE_EVIDENCE_PREFIX + "checkpoint-report-draft.md",
            "docs/program/tasks/W0-INT-02.md",
        ):
            with self.subTest(stranger=stranger):
                self.assertNotIn(stranger, POST_FREEZE_DELTA_CEILING)
                path = self.sandbox.root / stranger
                self.addCleanup(path.unlink, True)
                path.write_text("added after the freeze\n", encoding="utf-8")
                problems = _post_freeze_delta_problems(self.sandbox.root)
                self.assertTrue(
                    any("is void" in problem and stranger in problem for problem in problems),
                    f"an unnamed path in a licensed directory did not void the round: "
                    f"{problems}",
                )
                path.unlink()

    def test_a_banner_rewritten_without_naming_the_checkpoint_is_named(self) -> None:
        """**The price of licensing sixteen task files that need not move at all.**

        `_task_banner_problems` proved a licensed task file did not change *outside* its
        banner, and until now said nothing whatever about the banner of the sixteen that
        are not the ratifying task. So the licence bought a free rewrite of sixteen
        accepted tasks' status text under cover of a ratification — a path that may move
        and is required to carry nothing, which is the finding
        :data:`RECONCILIATIONS` exists for one layer up.

        What ratification writes into a banner is a closure, and a closure names the
        checkpoint it closes at. Three directions, because two of them can rot:

        * ratified and rewritten, no tag — the requirement, and it must fire;
        * unratified and already naming the tag — degenerate, and it must fire, or the
          requirement above could be satisfied by a banner that always said it;
        * unratified and carrying the ratifying task's denial — a second front on the
          ratification in a file no task may close, and it must fire.
        """
        closed = "docs/program/tasks/W0-CLN-01.md"
        self.assertNotEqual(closed, RATIFYING_TASK_FILE)
        marker = f"> Closed at CP-00 `{CHECKPOINT_TAG}`.\n"

        self._ratify_for_real()
        path = self.sandbox.root / closed
        self.assertEqual(_task_banner_problems(self.sandbox.root), [])
        text = path.read_text(encoding="utf-8")
        self.assertIn(marker, text, "the harness closed no other banner to strip")
        path.write_text(text.replace(marker, "> Closed.\n"), encoding="utf-8")
        problems = _task_banner_problems(self.sandbox.root)
        self.assertTrue(
            any(closed in problem and CHECKPOINT_TAG in problem for problem in problems),
            f"a status banner rewritten at ratification named no checkpoint: {problems}",
        )
        self.sandbox.restore()

        # Unratified from here: `restore` puts the manifest back to `ratified: false`.
        self.assertIsNot(
            (_checkpoint_manifest(self.sandbox.root) or {}).get("ratified"), True
        )
        for label, addition, expected in (
            ("the tag, before there is a publication", marker, "degenerate requirement"),
            (
                "the ratifying task's denial",
                f"> {RATIFYING_TASK_BANNER_DENIAL}.\n",
                RATIFYING_TASK_BANNER_DENIAL,
            ),
        ):
            with self.subTest(planted=label):
                self.sandbox._remember(closed)
                text = path.read_text(encoding="utf-8")
                banner, _rest = _banner_split(text)
                self.assertTrue(banner, f"{closed} carries no banner to plant in")
                path.write_text(text.replace(banner, banner + addition, 1), encoding="utf-8")
                problems = _task_banner_problems(self.sandbox.root)
                self.assertTrue(
                    any(closed in problem and expected in problem for problem in problems),
                    f"{label} was planted in a completed task's banner and nothing said "
                    f"so: {problems}",
                )
                self.sandbox.restore_one(closed)

    def test_an_emptied_requirement_table_is_reported_not_satisfied(self) -> None:
        """The table-emptying defect, in the three tables round thirteen added.

        Each of the three groups loops over a module table, and a loop over an empty
        table is not a weak requirement — it is no requirement, silently. The pins in
        :class:`TableExpectationTests` make emptying one *visible* in a diff; these
        guards make it *reported* on the tree, which is the difference between a reviewer
        having to notice and a check that fails. Both halves are exercised: the whole
        table emptied, and — for the deliverables, where an entry can be hollowed out
        without shortening the table — a single entry left with nothing to say.
        """
        for name, empty, checker, needle in (
            ("CHECKPOINT_DELIVERABLES", (), _checkpoint_bundle_problems,
             "CHECKPOINT_DELIVERABLES is empty"),
            ("RATIFICATION_PUBLICATION_RECORDS", (), _publication_record_problems,
             "RATIFICATION_PUBLICATION_RECORDS is empty"),
            ("COMPLETED_TASK_FILES", frozenset(), _task_banner_problems,
             "COMPLETED_TASK_FILES is empty"),
        ):
            with self.subTest(table=name):
                with unittest.mock.patch.object(sys.modules[__name__], name, empty):
                    problems = checker(self.sandbox.root)
                self.assertTrue(
                    any(needle in problem for problem in problems),
                    f"{name} was emptied and its group reported nothing: {problems}",
                )

        with unittest.mock.patch.object(
            sys.modules[__name__],
            "CHECKPOINT_DELIVERABLES",
            ({"name": "asks-for-nothing.md", "note": "a probe"},),
        ):
            problems = _checkpoint_bundle_problems(self.sandbox.root)
        self.assertTrue(
            any("required to carry nothing" in problem for problem in problems),
            f"a deliverable with no content requirement licensed its path: {problems}",
        )

        hollow = dict(RATIFICATION_PUBLICATION_RECORDS[0])
        hollow["denials"] = ()
        hollow["requires"] = ()
        with unittest.mock.patch.object(
            sys.modules[__name__], "RATIFICATION_PUBLICATION_RECORDS", (hollow,)
        ):
            problems = _publication_record_problems(self.sandbox.root)
        self.assertTrue(
            any("neither a denial nor a checklist" in problem for problem in problems)
            and any("no post-ratification requirement" in problem for problem in problems),
            f"a publication record with no anchor and no requirement passed: {problems}",
        )

    def test_the_checkpoint_mechanism_has_a_reachable_published_state(self) -> None:
        """**Round nine's void, answered by reaching the state instead of arguing it.**

        Round nine was voided before dispatch because `W0-INT-01` could not do its own
        job without voiding the round that authorised it: the eight evidence files, the
        three publication documents and the task banners are all inside
        :func:`_digest_paths` and were licensed by nothing, so an honest ratification put
        thirty-odd unlicensed paths into the post-freeze delta. "The mechanism has no
        executable final state, by any sequence" is a claim about reachability, and the
        only answer that is not more prose is a tree.

        So this builds the whole published state in a throwaway copy — the eight
        deliverables carrying what the table demands, the three records reconciled, the
        banners closed, the registry on the ratified token, the state document brought up
        to date, the reviewed-family digest recomputed over the tree ratification
        produced, and both acceptance digests sealed structure-first — and then asks
        every check in the module. All of them must be silent, and
        :func:`_post_freeze_delta_problems` above all: *its* silence is the repair, because
        it is the check that declared the round void.

        Then the other direction four times, because a mechanism that accepts everything
        has an executable state and no *final* one. Each omission is **re-sealed before
        it is judged**, so `evidence_bundle_digest` reproduces over the incomplete tree
        and the digest catch-all cannot answer for the requirement under test — without
        that, all four probes would pass on one piece of arithmetic and not one of the
        four requirements would have been measured. The four are then required to report
        something none of the others does, or they are one check with four names.
        """
        self._ratify_for_real()
        root = self.sandbox.root
        manifest = _checkpoint_manifest(root) or {}

        # It really is the published state, established before anything is asked of it.
        self.assertIs(manifest.get("ratified"), True)
        for relative in sorted(CHECKPOINT_DELIVERABLE_PATHS):
            self.assertTrue((root / relative).is_file(), f"{relative} was not written")
        self.assertIn(
            f"`{RATIFIED_STATE_TOKEN}`", (root / CHECKPOINT_REGISTRY).read_text(encoding="utf-8")
        )
        stage = RATIFICATION_PUBLICATION_RECORDS[1]["path"]
        self.assertNotIn("- [ ]", (root / stage).read_text(encoding="utf-8"))
        self.assertIn(
            CHECKPOINT_TAG,
            _flat(_banner_split((root / RATIFYING_TASK_FILE).read_text(encoding="utf-8"))[0]),
        )
        self.assertNotIn(
            STATE_DOCUMENT_DENIAL,
            _flat((root / PROGRAM_STATE_DOCUMENT).read_text(encoding="utf-8")),
        )
        digest, count = _reviewed_manifest_digest(root)
        self.assertEqual(
            manifest.get("artifact_manifest_sha256"),
            digest,
            "the external record still describes the reviewed families as they were "
            "before ratification edited them",
        )
        self.assertEqual(manifest.get("artifact_count"), count)
        self.assertEqual(manifest.get("tested_candidate_digest"), self.sandbox.frozen_digest)
        self.assertEqual(
            manifest.get("evidence_bundle_digest"),
            _acceptance_digest(root),
            "the evidence digest does not reproduce over the tree it was computed on, "
            "so the seal was taken before the structure was final",
        )
        self.assertNotEqual(
            manifest.get("evidence_bundle_digest"), manifest.get("tested_candidate_digest")
        )

        for label, check in (
            ("acceptance", _acceptance_problems),
            ("tested digest", _tested_digest_problems),
            ("post-freeze delta", _post_freeze_delta_problems),
            ("reconciliations", _reconciliation_problems),
            ("reviewed-family delta", _ratification_delta_problems),
            ("undeclared drift", _undeclared_drift),
            ("unperformed declarations", _unperformed_declarations),
            ("immutable family drift", _immutable_family_drift),
            ("retro-edited digests", _retro_edited_digests),
            ("state document", _state_document_problems),
            ("evidence bundle", _checkpoint_bundle_problems),
            ("publication records", _publication_record_problems),
            ("task banners", _task_banner_problems),
        ):
            with self.subTest(check=label):
                self.assertEqual(
                    check(root),
                    [],
                    f"a complete, honest CP-00 publication is refused by the {label} "
                    "check, so the checkpoint still has no executable final state",
                )
        self.assertIsNone(_registry_state_problem(root))

        # ---- and each single omission, judged on a re-sealed tree -------------------
        #
        # Back to the unratified tree first. Every omission below is built by ratifying
        # from scratch and breaking exactly one thing, and a second ratification laid
        # over the first would reconcile documents that are already reconciled — the
        # fixture would fail before the requirement under test was ever reached.
        self.sandbox.restore()
        dropped = ACCEPTANCE_EVIDENCE_PREFIX + "known-risks.md"
        wave = RATIFICATION_PUBLICATION_RECORDS[0]
        report = ACCEPTANCE_EVIDENCE_PREFIX + "manual-test-report.md"
        cases = _manual_case_ids(root)
        self.assertTrue(cases, "the runbook defines no manual case to fail")
        closed_banner = f"ratified and published as `{CHECKPOINT_TAG}`"

        def omit_a_deliverable() -> None:
            self.sandbox.restore_one(dropped)

        def leave_a_record_denying() -> None:
            self.sandbox.restore_one(wave["path"])

        def leave_a_banner_open() -> None:
            path = self.sandbox.root / RATIFYING_TASK_FILE
            text = path.read_text(encoding="utf-8")
            self.assertIn(closed_banner, text, "the harness closed no banner to reopen")
            path.write_text(
                text.replace(
                    closed_banner, f"{closed_banner}; {RATIFYING_TASK_BANNER_DENIAL}"
                ),
                encoding="utf-8",
            )

        def fail_a_manual_case() -> None:
            path = self.sandbox.root / report
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"| {cases[0]} | PASS |", text)
            path.write_text(
                text.replace(f"| {cases[0]} | PASS |", f"| {cases[0]} | FAIL |"),
                encoding="utf-8",
            )

        reported: dict[str, list[str]] = {}
        for label, omit, subject in (
            ("a missing evidence deliverable", omit_a_deliverable, dropped),
            ("a record still denying the ratification", leave_a_record_denying, wave["item"]),
            ("a status banner left open", leave_a_banner_open, RATIFYING_TASK_FILE),
            ("a manual case that did not pass", fail_a_manual_case, cases[0]),
        ):
            with self.subTest(omission=label):
                self._ratify_for_real()
                omit()
                self.sandbox.seal_digests(tested=self.sandbox.frozen_digest)
                problems = _acceptance_problems(self.sandbox.root)
                self.assertFalse(
                    any("does not reproduce" in problem for problem in problems),
                    "the incomplete tree was re-sealed, so the evidence-digest "
                    "catch-all must be silent and the requirement must answer on its "
                    f"own: {problems}",
                )
                self.assertTrue(
                    any(subject in problem for problem in problems),
                    f"{label} was published and the mechanism ratified anyway: {problems}",
                )
                reported[label] = problems
                self.sandbox.restore()

        for label, problems in reported.items():
            with self.subTest(distinct=label):
                elsewhere = {
                    problem
                    for other, group in reported.items()
                    if other != label
                    for problem in group
                }
                self.assertTrue(
                    set(problems) - elsewhere,
                    f"{label} reports nothing the other omissions do not also report, "
                    "so these are one check wearing four names",
                )

    # ---- the acceptance gate, one branch at a time (B1) ---------------------------
    #
    # An independent reviewer disabled six branches of `_acceptance_problems`
    # individually and the whole suite stayed green, while each one was demonstrably
    # load-bearing when driven against a fully ratified sandbox. The branches were not
    # untested by oversight: every existing probe drives an *unratified* or
    # *deliberately broken* tree, and these six live behind `if manifest.get("ratified")
    # is not True: return problems`. What was missing was a fixture that is a clean,
    # complete, accepted ratification — one thing broken at a time, everything else
    # right. `_ratify_for_real` builds one; `_a_clean_ratification` asserts it is clean
    # before anything is broken, because a probe run against an already-failing fixture
    # proves nothing about the branch it names.

    def _a_clean_ratification(self) -> Path:
        """A ratification with nothing wrong with it, asserted to be so."""
        self._ratify_for_real()
        self.assertEqual(
            _acceptance_problems(self.sandbox.root),
            [],
            "the fixture is not a clean ratification, so breaking one thing in it "
            "would not isolate the branch under test",
        )
        return self.sandbox.root / CHECKPOINT_MANIFEST

    @staticmethod
    def _amend(path: Path, mutate) -> int:
        """Apply one change to the manifest and its current round. Returns the round."""
        document = json.loads(path.read_text(encoding="utf-8"))
        number = document["current_round"]
        current = next(
            entry
            for entry in document["acceptance_rounds"]
            if entry.get("round") == number
        )
        mutate(document, current)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return number

    def test_a_ratification_recording_no_digests_at_all_is_rejected(self) -> None:
        """**B1, the material one.** The only check between CP-00 and a ratification
        that records nothing about what was tested.

        With the digest-shape branch disabled, a complete and content-correct
        ratification carrying ``tested_candidate_digest: null`` and
        ``evidence_bundle_digest: null`` produced `[]` from every check in the module —
        and not by coincidence. `_tested_digest_problems` returns `[]` on `None` **by
        design**, because `null` is a legitimate pre-round state; the evidence
        recomputation is gated on ``isinstance(evidence, str)`` for the same reason.
        Both halves of §8.12's two-half guarantee go silent together on exactly this
        input, so this one branch is the whole of the guarantee at ratification time.

        The probe therefore asserts the silence of the neighbours too. Without that it
        would be a test of one message; with it, it is the record of *why* the branch
        cannot be dropped.
        """
        path = self._a_clean_ratification()

        def blank(document, current):
            for field in ACCEPTANCE_DIGEST_FIELDS:
                document[field] = None
                current[field] = None

        number = self._amend(path, blank)
        root = self.sandbox.root

        # Every neighbouring check is silent on this tree — by design, not by accident.
        self.assertEqual(_tested_digest_problems(root), [])
        self.assertEqual(_reconciliation_problems(root), [])
        self.assertIsNone(_registry_state_problem(root))
        self.assertEqual(_ratification_delta_problems(root), [])
        self.assertEqual(_post_freeze_delta_problems(root), [])

        self.assertEqual(
            sorted(_acceptance_problems(root)),
            sorted(
                f"{field} at the {where} is None; a ratified checkpoint must record "
                "both digests"
                for field in ACCEPTANCE_DIGEST_FIELDS
                for where in ("top level", f"round {number}")
            ),
            "a ratified checkpoint recording neither digest was accepted",
        )

    def test_a_ratification_whose_digests_are_not_digests_is_rejected(self) -> None:
        """The other half of the same branch: present, wrong shape.

        `null` and ``"pending"`` fail for different reasons in the same expression, and
        a probe for one does not cover the other.
        """
        for bad in ("pending", "", "DEADBEEF" * 8, "a" * 63, 5):
            with self.subTest(value=bad):
                path = self._a_clean_ratification()
                number = self._amend(
                    path,
                    lambda document, current, value=bad: [
                        document.__setitem__("tested_candidate_digest", value),
                        current.__setitem__("tested_candidate_digest", value),
                    ],
                )
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(
                        f"tested_candidate_digest at the top level is {bad!r}" in problem
                        for problem in problems
                    ),
                    f"{bad!r} was accepted as a digest: {problems}",
                )
                self.assertTrue(
                    any(
                        f"tested_candidate_digest at the round {number} is" in problem
                        for problem in problems
                    ),
                    f"only the top level was checked: {problems}",
                )
                self.sandbox.restore()

    def test_a_round_whose_streams_are_not_an_object_is_rejected(self) -> None:
        """**B1's one uncovered branch of that class.**

        The B1 table drove the *contents* of `streams` — a stream that is not `PASS` —
        and never its *shape*. Reducing ``if not isinstance(streams, dict):`` to ``if
        False:`` left all 244 tests green, and the branch is load-bearing in both
        directions at once: live code reports ``round 5 records no streams object``,
        while the mutant reaches ``streams.get(name)`` and raises `AttributeError`
        against the same input. A check whose removal turns a reported problem into a
        crash is not decoration.

        Every shape a hand-edited manifest plausibly reaches this with, including the
        one that matters most — the key absent altogether, which is what a record
        written from a template that never had it looks like.
        """
        cases = (
            ("absent", None),
            ("a string", "PASS"),
            ("a list of the two stream names", ["automated", "manual"]),
            ("null", None),
            ("a bare boolean", True),
        )
        for label, value in cases:
            with self.subTest(streams=label):
                try:
                    path = self._a_clean_ratification()
                    if label == "absent":
                        number = self._amend(
                            path, lambda document, current: current.pop("streams", None)
                        )
                    else:
                        number = self._amend(
                            path,
                            lambda document, current, v=value: current.__setitem__(
                                "streams", v
                            ),
                        )
                    problems = _acceptance_problems(self.sandbox.root)
                    self.assertIn(
                        f"round {number} records no streams object",
                        problems,
                        "a round with no usable streams object was accepted",
                    )
                    # And not by the branch below it: a non-object never reaches the
                    # per-stream comparison, so a probe that accepted either message
                    # would pass on the mutant, which raises before reporting anything.
                    self.assertEqual(
                        [
                            problem
                            for problem in problems
                            if "both streams must pass" in problem
                        ],
                        [],
                    )
                finally:
                    self.sandbox.restore()
        self.assertEqual(len(cases), 5)

    def test_a_round_naming_a_primary_report_that_is_not_there_is_rejected(self) -> None:
        """B1: `manual_report`/`automated_report` must exist **as files**.

        `test_a_missing_primary_report_blocks_ratification` covers the branch above this
        one — the field being absent or not a string. The `elif` that opens the file is
        a different branch and had nothing driving it, so a round could name a report
        that was never written and ratify.
        """
        absent = "artifacts/checkpoints/CP-00/manual-report-round-never.md"
        for field in ("manual_report", "automated_report"):
            with self.subTest(field=field):
                path = self._a_clean_ratification()
                number = self._amend(
                    path,
                    lambda document, current, name=field: current.__setitem__(
                        name, absent
                    ),
                )
                self.assertFalse((self.sandbox.root / absent).exists())
                self.assertIn(
                    f"round {number} names {field} {absent!r}, which does not exist",
                    _acceptance_problems(self.sandbox.root),
                )
                self.sandbox.restore()

    def test_a_stream_acceptance_record_that_is_not_an_object_is_rejected(self) -> None:
        """B1: `manual_acceptance`/`automated_acceptance` must be objects.

        A string here does not merely fail to carry a status — it makes every field
        read off it silently absent, so without this branch the three checks below it
        become unreachable rather than failing.
        """
        for name in ("manual_acceptance", "automated_acceptance"):
            for value in ("PASS", ["PASS"], True, None):
                with self.subTest(record=name, value=value):
                    path = self._a_clean_ratification()
                    self._amend(
                        path,
                        lambda document, current, n=name, v=value: document.__setitem__(
                            n, v
                        ),
                    )
                    problems = _acceptance_problems(self.sandbox.root)
                    self.assertIn(f"{name} must be an object", problems)
                    self.assertFalse(
                        any(f"{name}.status" in problem for problem in problems),
                        "the branch fell through to the field reads, so it did not "
                        f"stop the way it must: {problems}",
                    )
                    self.sandbox.restore()

    def test_a_stream_acceptance_record_for_another_round_is_rejected(self) -> None:
        """B1: the stream's own record must be about the round being ratified.

        Otherwise last round's passing acceptance record ratifies this round — the
        record says `PASS`, it names a report that exists, and nothing compares the
        number it carries with `current_round`.
        """
        for name in ("manual_acceptance", "automated_acceptance"):
            with self.subTest(record=name):
                path = self._a_clean_ratification()
                number = self._amend(
                    path,
                    lambda document, current, n=name: document[n].__setitem__(
                        "round", document["current_round"] - 1
                    ),
                )
                self.assertIn(
                    f"{name}.round is {number - 1} and current_round is {number}",
                    _acceptance_problems(self.sandbox.root),
                )
                self.sandbox.restore()

    def test_a_stream_acceptance_report_path_that_is_not_there_is_rejected(self) -> None:
        """B1: `<stream>_acceptance.report_path` must exist as a file."""
        absent = "artifacts/checkpoints/CP-00/acceptance-that-was-never-written.md"
        for name in ("manual_acceptance", "automated_acceptance"):
            with self.subTest(record=name):
                path = self._a_clean_ratification()
                self._amend(
                    path,
                    lambda document, current, n=name: document[n].__setitem__(
                        "report_path", absent
                    ),
                )
                self.assertFalse((self.sandbox.root / absent).exists())
                self.assertIn(
                    f"{name}.report_path {absent!r} does not exist",
                    _acceptance_problems(self.sandbox.root),
                )
                self.sandbox.restore()

    def test_an_acceptance_round_that_is_not_an_object_with_an_int_round_is_rejected(
        self,
    ) -> None:
        """B1: the shape every later read of `acceptance_rounds` depends on.

        This branch guards the arithmetic, not the policy: `numbers` is zipped against
        `rounds` and every downstream comparison assumes an int. It fires before the
        ratification gate, so unlike the five above it is reachable on an unratified
        tree — it was untested all the same.
        """
        cases = (
            ("a non-object entry", "round six"),
            ("an entry with no round at all", {"verdict": "PASS"}),
            ("an entry whose round is a string", {"round": "6"}),
            ("an entry whose round is a float", {"round": 6.0}),
        )
        for label, entry in cases:
            with self.subTest(case=label):
                path = self._a_clean_ratification()
                self._amend(
                    path,
                    lambda document, current, e=entry: document[
                        "acceptance_rounds"
                    ].append(e),
                )
                self.assertEqual(
                    _acceptance_problems(self.sandbox.root),
                    [
                        "every acceptance_rounds entry must be an object with an int "
                        "round"
                    ],
                    "a malformed acceptance_rounds entry was read as a round",
                )
                self.sandbox.restore()

    # ---- the two admissibility guards on the data W0-INT-01 writes (B6) ------------

    def test_a_ratified_flag_that_is_not_a_boolean_is_rejected(self) -> None:
        """B6: ``"true"`` is a string, and a truthy one.

        `_ratification_record` reads this field and every delta decision hangs off it.
        The live code catches the string; nothing required it to, so the guard could be
        deleted with 189 tests green — and then the *string* ``"false"`` would license
        the full ratification delta, because a non-empty string is truthy.
        """
        for value in ("true", "false", 1, 0, [], None):
            with self.subTest(value=value):
                self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=value)
                _flag, _paths, problems = _ratification_record(self.sandbox.root)
                self.assertIn(
                    f"{CHECKPOINT_MANIFEST}: 'ratified' must be a boolean, got {value!r}",
                    problems,
                )
                self.sandbox.restore()

    def test_allowed_delta_paths_holding_something_other_than_strings_is_rejected(
        self,
    ) -> None:
        """B6: the list `W0-INT-01` writes is the licence, so its contents are checked.

        Without this, a non-string entry survives into the set the delta is compared
        against, where it can never match a path and so silently narrows nothing — or,
        worse, a dict is compared for membership and raises inside the check that is
        supposed to be reporting problems.
        """
        for bad in (["docs/architecture/GLOSSARY.md", 7], [None], [{"path": "x"}], [[]]):
            with self.subTest(value=bad):
                self.sandbox.declare_ratification(bad)
                _flag, _paths, problems = _ratification_record(self.sandbox.root)
                self.assertIn(
                    f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths must "
                    "hold strings",
                    problems,
                )
                self.sandbox.restore()

    def test_the_evidence_digest_depends_on_the_tested_digest(self) -> None:
        """The binding, measured. This is the check the prose used to stand in for.

        Two trees identical in every byte except the value of
        `tested_candidate_digest` — including a value describing a tree that never
        existed — must produce **different** evidence digests. Under the old blank-both
        recipe they produced one identical digest, so the field naming the judged tree
        could hold anything at all.
        """
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        digests = {}
        for tested in ("a" * 64, "0" * 64, "deadbeef" * 8):
            self.sandbox.seal_digests(tested=tested)
            digests[tested] = _acceptance_digest(
                self.sandbox.root, "evidence_bundle_digest"
            )
        self.assertEqual(
            len(set(digests.values())),
            len(digests),
            "the evidence digest is independent of tested_candidate_digest, so evidence "
            f"from any tree can be presented as this round's: {digests}",
        )
        # The line this probe used to stop one short of. Arithmetic dependence is not
        # verification: each of those three trees is a complete, content-correct
        # ratification whose `tested_candidate_digest` names a tree that never existed,
        # and every one of them was accepted with every check silent until round seven.
        for tested in digests:
            with self.subTest(tested=tested[:16]):
                self.sandbox.seal_digests(tested=tested)
                self.assertTrue(
                    any(
                        "is frozen at no commit" in problem
                        for problem in _acceptance_problems(self.sandbox.root)
                    ),
                    "a tested_candidate_digest naming a tree that never existed was "
                    "accepted; depending on a value is not checking it",
                )

    def test_swapping_the_tested_digest_alone_breaks_the_evidence_digest(self) -> None:
        """The same fact as a rejection, end to end through the live check."""
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        manifest = json.loads(
            (self.sandbox.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        number = manifest["current_round"]
        manifest["tested_candidate_digest"] = "deadbeef" * 8
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == number:
                entry["tested_candidate_digest"] = "deadbeef" * 8
        (self.sandbox.root / CHECKPOINT_MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("does not reproduce over this tree" in problem for problem in problems),
            "a tested_candidate_digest naming a tree that never existed was accepted: "
            f"{problems}",
        )

    def test_a_fabricated_tested_digest_is_rejected(self) -> None:
        """Round seven's blocker, in the construction the reviewer used.

        A complete, content-correct ratification — record, flag, five real
        reconciliations, an accepted round with both primary reports on disk, the
        registry in agreement — whose `tested_candidate_digest` names a tree that never
        existed. Sealed in the order the manifest's own recipe prescribes: all structure
        first, the tested value frozen, the evidence digest computed last over the
        finished tree, so it reproduces and nothing downstream notices.

        Every check was silent. `_acceptance_problems` read the field for 64-hex shape
        and for top-level/per-round agreement and never again; `_retro_edited_digests`
        catches a value changed *after* its commit and is silent by construction when
        the fabricated value is the one that got committed.
        """
        for fabricated in ("deadbeef" * 8, "c" * 64, "0" * 64):
            with self.subTest(tested=fabricated[:16]):
                self._ratify_for_real()
                self.sandbox.seal_digests(tested=fabricated)
                self.assertEqual(_reconciliation_problems(self.sandbox.root), [])
                self.assertIsNone(_registry_state_problem(self.sandbox.root))
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any("is frozen at no commit" in problem for problem in problems),
                    "a ratification naming a tree that never existed was accepted: "
                    f"{problems}",
                )
                self.sandbox.restore()

    def test_the_tested_digest_recomputes_over_the_commit_that_froze_it(self) -> None:
        """The premise that licensed leaving this field unchecked, tested and false.

        §8.12 said the value "cannot be recomputed after the fact by anyone", because
        the tree it describes stops existing once the results are written. The recipe
        blanks the field being computed, so the value is exactly the digest of the tree
        at the commit that froze it — and Git keeps that tree forever. The manifest
        never has to record its own commit: history supplies it.

        Two-way, so it cannot rot into a pass. If a digest is recorded it must be frozen
        at a commit and reproduce there; if none is recorded there must be no freeze
        commit to find. The recipe's tree-sensitivity is shown on real data rather than
        asserted: the same recipe over a different real tree gives a different value, so
        this is a comparison between trees and not a shape check that any 64-hex string
        would pass.
        """
        self.assertEqual(_tested_digest_problems(REPOSITORY_ROOT), [])
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        declared = manifest.get("tested_candidate_digest")
        commit = _freeze_commit(REPOSITORY_ROOT)
        if not declared:
            self.assertIsNone(
                commit,
                "no tested_candidate_digest is recorded, yet a commit was accepted as "
                "having frozen one",
            )
            return
        self.assertIsNotNone(
            commit, f"tested_candidate_digest {declared} is frozen at no commit"
        )
        self.assertEqual(
            _acceptance_digest_at(REPOSITORY_ROOT, commit, "tested_candidate_digest"),
            declared,
            "the declared tested_candidate_digest is not the digest of the tree at the "
            "commit that froze it",
        )
        self.assertNotEqual(
            _acceptance_digest_at(
                REPOSITORY_ROOT, REVIEWED_CANDIDATE_COMMIT, "tested_candidate_digest"
            ),
            declared,
            "the recipe returns the same value over two different trees, so recomputing "
            "it proves nothing about which tree was judged",
        )

    def test_a_tested_digest_that_does_not_reproduce_at_its_freeze_commit_is_rejected(
        self,
    ) -> None:
        """The second failure mode of half one, which needs a commit to construct.

        A value that no commit carries is caught by discovery. A value a commit *does*
        carry but that does not describe that commit's tree can only be built by writing
        a commit, so the freeze commit is substituted instead, which mutates exactly the
        thing under test: which tree the declared value is claimed to be the digest of.

        **Driven against the sandbox, not `REPOSITORY_ROOT`.** The live manifest carries
        `tested_candidate_digest: null` between rounds — the legitimate state
        :func:`_tested_digest_problems` returns `[]` for by design — and this probe then
        asserted nothing at all while reporting success, which is the shape this task
        exists to remove. The sandbox always stands on a real freeze, its own or the one
        recovered from history, so the digest sealed here is a value a commit genuinely
        carries and the substitution is the only thing that makes it wrong.
        """
        self.sandbox.seal_digests(tested=self.sandbox.frozen_digest)
        self.assertRegex(
            (_checkpoint_manifest(self.sandbox.root) or {}).get("tested_candidate_digest") or "",
            r"^[0-9a-f]{64}$",
            "no digest is declared, so the recomputation this probe is about does not run",
        )
        self.assertEqual(
            _tested_digest_problems(self.sandbox.root),
            [],
            "the sealed digest does not reproduce at its own freeze commit, so the "
            "substitution below is not what makes this fail",
        )
        with unittest.mock.patch.object(
            sys.modules[__name__],
            "_freeze_commit",
            lambda root: REVIEWED_CANDIDATE_COMMIT,
        ):
            problems = _tested_digest_problems(self.sandbox.root)
        self.assertTrue(
            any("does not reproduce over the tree of" in problem for problem in problems),
            problems,
        )

    def test_a_tree_that_moved_after_the_freeze_voids_the_round(self) -> None:
        """Half two: the judged tree must be the frozen tree.

        Recomputing over the freeze commit proves the value names a real tree. It cannot
        prove that tree is the one in front of you — the freeze commit is immutable, so
        half one stays green however far the working tree drifts. What bounds the drift
        is the ceiling: the round's declared acceptance evidence, the three external
        records, and the five files ratification itself reconciles. Anything else and
        the streams judged a different input.

        The probe also asserts the ceiling is a ceiling and not a shrug: the licensed
        paths a real ratification moves are *not* named as strangers.

        The stranger used to be `docs/program/CURRENT_STATE.md`, and round seven had to
        license that path — so the probe would have been asserting that a licensed file
        is unlicensed. The replacement is chosen so it can never become licensed rather
        than because it reads well: `contracts/**` is one of the
        :data:`IMMUTABLE_REVIEWED_PREFIXES` this module states ratification never
        reaches, and the assertions below pin that property instead of trusting it.
        """
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        stranger = POST_FREEZE_STRANGER
        self.assertTrue(stranger.startswith(IMMUTABLE_REVIEWED_PREFIXES))
        self.assertNotIn(stranger, POST_FREEZE_DELTA_CEILING)
        self.assertFalse(stranger.startswith(ACCEPTANCE_EVIDENCE_PREFIX))
        self.sandbox.edit(stranger, marker="\n<!-- moved after the freeze -->\n")
        problems = _post_freeze_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("is void" in problem and stranger in problem for problem in problems),
            f"the tree moved outside the ceiling and the round stayed live: {problems}",
        )
        reported = "\n".join(problems)
        for licensed in sorted(POST_FREEZE_DELTA_CEILING):
            self.assertNotIn(
                licensed,
                reported,
                "a path ratification is entitled to move was reported as voiding the "
                "round",
            )
        self.assertTrue(
            any("is void" in problem for problem in _acceptance_problems(self.sandbox.root)),
            "the void round was still ratifiable",
        )

    def test_an_untracked_path_added_after_the_freeze_voids_the_round(self) -> None:
        """The other half of the digest recipe, which nothing measured.

        `_digest_paths` is `--cached --others --exclude-standard`: tracked **and**
        untracked-not-ignored, which is the recipe's own wording and the reason the
        manifest gives for it — globbing the working tree would hash a gitignored
        `.pyc`. Round nine's reviewer deleted `--others` and the suite stayed green,
        because the probe above moves a *tracked* file and every other digest probe edits
        one too. An untracked file dropped into a reviewed family after the freeze is a
        different tree by the recipe's own definition, and until now nothing said so.
        """
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        stranger = "contracts/POST_FREEZE_UNTRACKED.md"
        path = self.sandbox.root / stranger
        self.addCleanup(path.unlink, True)
        path.write_text("added after the freeze, never committed\n", encoding="utf-8")

        self.assertIn(
            stranger,
            _digest_paths(self.sandbox.root),
            "the recipe does not enumerate untracked files, so this probe measures "
            "nothing",
        )
        self.assertNotIn(
            stranger,
            _git(
                "-C", str(self.sandbox.root), "ls-files", "--cached",
                text=True, check=True,
            ).stdout.split("\n"),
            "the path is tracked, so this is the case the probe above already covers",
        )
        problems = _post_freeze_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("is void" in problem and stranger in problem for problem in problems),
            f"an untracked file appeared after the freeze and the round stayed live: "
            f"{problems}",
        )

    def test_a_report_path_outside_the_evidence_prefix_licenses_nothing(self) -> None:
        """The round declares its own evidence, so the declaration is bounded.

        `manual_report` and `automated_report` are data. Without a prefix a round could
        license any drift it liked by naming the drifted file as its own report — the
        same manoeuvre the ceiling on `allowed_delta_paths` exists to stop one level up.
        """
        self._ratify_for_real()
        stranger = POST_FREEZE_STRANGER
        self.assertFalse(stranger.startswith(ACCEPTANCE_EVIDENCE_PREFIX))
        self.sandbox.edit(stranger, marker="\n<!-- moved after the freeze -->\n")
        manifest = json.loads(
            (self.sandbox.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == manifest["current_round"]:
                entry["manual_report"] = stranger
        manifest["manual_acceptance"]["report_path"] = stranger
        (self.sandbox.root / CHECKPOINT_MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        problems = _post_freeze_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("is void" in problem and stranger in problem for problem in problems),
            f"a round licensed its own drift by calling it a report: {problems}",
        )

    def test_a_declared_report_path_that_escapes_the_prefix_is_not_honoured(self) -> None:
        """The traversal clause, exercised where it is decidable — and its real reach,
        stated rather than overclaimed.

        ``".." not in value.split("/")`` survives removal with the whole suite green,
        and it is worth being exact about why. `_declared_evidence_paths` feeds one
        consumer, `_post_freeze_delta_problems`, which tests membership against a delta
        built from `git`-normalised repository-relative paths. A string containing `..`
        never equals one of those, so today the clause changes no verdict and no
        end-to-end probe can make it change one. Round eleven does not pretend otherwise
        by dressing an unreachable branch in a behavioural probe.

        What it *is* is the difference between a prefix test and a containment test, on
        a value that is manifest **data** — and the manifest is written by the task this
        module exists to constrain. `artifacts/checkpoints/CP-00/../../contracts/x`
        starts with `ACCEPTANCE_EVIDENCE_PREFIX` and names a file two families away. The
        clause is asserted here at the level it decides, so that removing it is red, and
        §11.17.5 records that its effect is defence for a future consumer rather than a
        live control.
        """
        escapes = (
            f"{ACCEPTANCE_EVIDENCE_PREFIX}../../contracts/README.md",
            f"{ACCEPTANCE_EVIDENCE_PREFIX}../manifest.json",
            f"{ACCEPTANCE_EVIDENCE_PREFIX}reports/../../../etc/passwd",
        )
        inside = f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-5.md"
        for value in escapes:
            with self.subTest(declared=value):
                self.assertTrue(
                    value.startswith(ACCEPTANCE_EVIDENCE_PREFIX),
                    "this case does not reach the traversal clause at all, because the "
                    "prefix test rejects it first",
                )
                manifest = {
                    "current_round": 5,
                    "acceptance_rounds": [{"round": 5, "manual_report": value}],
                    "manual_acceptance": {"report_path": value},
                }
                self.assertEqual(_declared_evidence_paths(manifest), set())
        # The control: a path that stays inside the prefix is still honoured, so the
        # clause is not simply rejecting everything.
        self.assertEqual(
            _declared_evidence_paths(
                {
                    "current_round": 5,
                    "acceptance_rounds": [{"round": 5, "manual_report": inside}],
                }
            ),
            {inside},
        )
        self.assertEqual(len(escapes), 3)

    def test_a_report_path_under_a_name_of_the_integrators_choosing_licenses_nothing(
        self,
    ) -> None:
        """The manifest may not widen its own licence by renaming a file a report.

        **The hole, as an independent reviewer demonstrated it end to end.** The
        effective post-freeze licence is
        ``POST_FREEZE_DELTA_CEILING | _declared_evidence_paths(manifest)``, and the
        second term used to admit *any* path under
        :data:`ACCEPTANCE_EVIDENCE_PREFIX`. The manifest is written by the integrator, so
        naming `check_state_records.py` as this round's report licensed editing it after
        the freeze and all fourteen checkers stayed silent. That is the one file in that
        directory this round deliberately kept out of the ceiling -- a tool, not evidence
        -- so the module's own control, "named files, not anything under
        `artifacts/checkpoints/CP-00/`", was defeated by the sibling code path that
        computes the other half of the same union.

        Both directions, because a licence probe that only shows the refusal proves the
        function is broken rather than that it is right: the canonical name for this
        round *is* honoured, and every other name is not.
        """
        self._ratify_for_real()
        self.assertEqual(_post_freeze_delta_problems(self.sandbox.root), [])

        tool = f"{ACCEPTANCE_EVIDENCE_PREFIX}check_state_records.py"
        self.assertNotIn(
            tool,
            POST_FREEZE_DELTA_CEILING,
            "this probe is about a path the ceiling deliberately excludes; the ceiling "
            "now licenses it, so the probe is measuring nothing and must be re-anchored",
        )
        self.sandbox.edit(tool, marker="\n# moved after the freeze\n")

        manifest = json.loads(
            (self.sandbox.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        number = manifest["current_round"]
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == number:
                entry["manual_report"] = tool
        manifest["manual_acceptance"]["report_path"] = tool
        (self.sandbox.root / CHECKPOINT_MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        problems = _post_freeze_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("is void" in problem and tool in problem for problem in problems),
            f"the manifest licensed its own drift by renaming a tool a report: {problems}",
        )

        # The positive direction, at the level the clause decides: the round's canonical
        # names are honoured, and only those two.
        self.assertEqual(
            _canonical_report_paths(number),
            {
                "manual": f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-{number}.md",
                "automated":
                    f"{ACCEPTANCE_EVIDENCE_PREFIX}automated-report-round-{number}.md",
            },
        )
        honoured = _declared_evidence_paths(
            {
                "current_round": number,
                "acceptance_rounds": [
                    {
                        "round": number,
                        "manual_report":
                            f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-{number}.md",
                        "automated_report": tool,
                    }
                ],
            }
        )
        self.assertEqual(
            honoured,
            {f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-{number}.md"},
            "the canonical name must still be licensed, and the renamed one must not",
        )

    def test_a_closed_rounds_report_path_does_not_license_drift(self) -> None:
        """`_declared_evidence_paths`' current-round filter, exercised directly.

        The probe above proves a report path needs the `ACCEPTANCE_EVIDENCE_PREFIX`.
        This one proves the separate half: it also needs to belong to the round that is
        open *now*. Without `entry.get("round") == number`, any past round's
        `manual_report` or `automated_report` — however long closed — would go on
        licensing drift to that path forever, the same "declaring the work is not doing
        it" shape §11.8 closed for the ratification delta, one field over. A round that
        is `spent` or `void` cannot un-declare a stranger just by having once named a
        path near it.
        """
        self._ratify_for_real()
        manifest = json.loads(
            (self.sandbox.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        current = manifest["current_round"]
        closed_rounds = [
            entry.get("round")
            for entry in manifest["acceptance_rounds"]
            if entry.get("round") != current
        ]
        self.assertTrue(closed_rounds, "this manifest has no closed round to attack")

        stranger = f"{ACCEPTANCE_EVIDENCE_PREFIX}old-round-report.md"
        path = self.sandbox.root / stranger
        self.addCleanup(path.unlink, True)
        path.write_text("claimed by a closed round, not the open one\n", encoding="utf-8")
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == closed_rounds[0]:
                entry["manual_report"] = stranger
        (self.sandbox.root / CHECKPOINT_MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.assertNotIn(
            stranger,
            _declared_evidence_paths(manifest),
            "a closed round's report path is licensed forever; the filter is not "
            "running",
        )
        problems = _post_freeze_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("is void" in problem and stranger in problem for problem in problems),
            f"a closed round's declared report path licensed drift after the freeze: "
            f"{problems}",
        )

    # ---- round seven: the third external record ----------------------------------

    def test_the_state_document_is_licensed_and_moving_it_does_not_void_the_round(
        self,
    ) -> None:
        """The deadlock round seven had to break, shown from the licensed side.

        `docs/program/CURRENT_STATE.md` is inside `_digest_paths`, and ratification
        cannot leave it alone: it says in as many words that nothing is ratified. Before
        this round it was unlicensed, so the very edit ratification owes voided the round
        that ratification stood on. The probe asserts both halves of the fix at once —
        the document really did move after the freeze, and the move is not a stranger.
        """
        self._ratify_for_real()
        frozen = _tree_blobs(self.sandbox.root, self.sandbox.frozen_commit)
        self.assertNotEqual(
            frozen[PROGRAM_STATE_DOCUMENT],
            (self.sandbox.root / PROGRAM_STATE_DOCUMENT).read_bytes(),
            "the harness did not move the state document, so this proves nothing",
        )
        self.assertEqual(_post_freeze_delta_problems(self.sandbox.root), [])
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])

    def test_a_ratified_checkpoint_may_not_still_deny_the_ratification(self) -> None:
        """What the licence is paid for. Nothing checked this before round seven.

        The registry had `_registry_state_problem`; the state document had nothing at
        all, so a ratified CP-00 could ship a state document reading "Nothing is
        ratified, nothing is tagged" and no check anywhere would notice.
        """
        self._ratify_for_real()
        self.assertEqual(_state_document_problems(self.sandbox.root), [])
        self.sandbox.restore_one(PROGRAM_STATE_DOCUMENT)
        problems = _state_document_problems(self.sandbox.root)
        self.assertTrue(
            any(
                "denies the ratification" in problem
                and STATE_DOCUMENT_DENIAL in problem
                for problem in problems
            ),
            f"a ratified checkpoint kept its denial and passed: {problems}",
        )
        self.assertTrue(
            any("denies the ratification" in problem for problem in
                _acceptance_problems(self.sandbox.root)),
            "the contradiction did not block ratification",
        )

    def test_gutting_the_state_document_is_not_a_way_to_remove_the_denial(self) -> None:
        """Removal-only checks are satisfiable by deletion; this is the guard.

        The same defect class as the `GATE-E` entry, whose `must_still_contain` guard
        sat unreachable behind `if False and ...` until this round. Neither needle is
        evidence the document was updated — both are already in it — and the report
        says so rather than letting the guard read as content verification.
        """
        self._ratify_for_real()
        self.assertEqual(_state_document_problems(self.sandbox.root), [])
        self.sandbox._remember(PROGRAM_STATE_DOCUMENT)
        (self.sandbox.root / PROGRAM_STATE_DOCUMENT).write_text(
            "gutted\n", encoding="utf-8"
        )
        problems = _state_document_problems(self.sandbox.root)

        # B2, the round-seven defect one constant over. Looping over the table means
        # `STATE_DOCUMENT_MUST_STILL_CONTAIN = ()` runs zero subtests, asserts nothing
        # and leaves the suite green with the anti-gutting guard gone. The identical
        # guard for `RECONCILIATIONS[2]` is killed by its own probe precisely because
        # that one asserts the literal message instead of looping over the table, so
        # this one now does the same: the needles are pinned here, in the test, and the
        # message for each is asserted by name.
        self.assertEqual(
            STATE_DOCUMENT_MUST_STILL_CONTAIN,
            ("# Current state", "CP-00"),
            "the anti-gutting table changed. Emptying or narrowing it must be a "
            "decision made here, in the probe, and not a silent one that leaves this "
            "test asserting nothing",
        )
        for needle in ("# Current state", "CP-00"):
            with self.subTest(needle=needle):
                self.assertIn(
                    f"{PROGRAM_STATE_DOCUMENT} does not carry {needle!r}. The denial "
                    "must be removed by updating the state document, not by gutting "
                    "it.",
                    problems,
                    f"the denial was removed by deleting the document: {problems}",
                )

    def test_removing_the_denial_before_ratification_is_reported_as_anchor_rot(
        self,
    ) -> None:
        """The anti-vacuity half, and the reason this is not a one-directional check.

        A removal requirement whose phrase has quietly been reworded passes forever
        without ever proving anything. Because the unratified state *requires* the
        sentence, a reword fails immediately — while CP-00 is still unratified and
        re-anchoring the module costs nothing — instead of failing to fire years later
        at the one moment it mattered.
        """
        self.assertIs(
            _checkpoint_manifest(self.sandbox.root).get("ratified"),
            False,
            "the sandbox is not in the unratified state this probe needs",
        )
        self.assertEqual(_state_document_problems(self.sandbox.root), [])
        self.sandbox.update_state_document()
        problems = _state_document_problems(self.sandbox.root)
        self.assertTrue(
            any(
                "anchor rot" in problem and STATE_DOCUMENT_DENIAL in problem
                for problem in problems
            ),
            f"the anchor was removed while unratified and nothing said so: {problems}",
        )

    # ---- round nine: branches no probe had reached --------------------------------

    def test_a_malformed_acceptance_record_is_named_branch_by_branch(self) -> None:
        """Structural branches of `_acceptance_problems`, each with its own message.

        All of these survived round nine's mutation sweep: every probe fed the check a
        well-formed manifest and attacked the *policy*, so the shape checks underneath ran
        and could not fail. They are cheap, they are the difference between a clear
        rejection and a `KeyError`, and the reviewer was right that nothing measured them.
        """
        cases = (
            ("acceptance_rounds is not a list", {"acceptance_rounds": {}},
             "must be a non-empty list"),
            ("acceptance_rounds is empty", {"acceptance_rounds": []},
             "must be a non-empty list"),
            ("an entry is not an object", {"acceptance_rounds": [1, 2]},
             "must be an object with an int round"),
            ("round numbers repeat", {"acceptance_rounds": [{"round": 5}, {"round": 5}]},
             "unique and ascending"),
            ("round numbers descend", {"acceptance_rounds": [{"round": 6}, {"round": 5}]},
             "unique and ascending"),
            ("current_round is not an integer", {"current_round": "five"},
             "current_round must be an integer"),
            ("no entry for the current round", {"current_round": 99},
             "acceptance_rounds carries 0 entries for it"),
        )
        for label, fields, expected in cases:
            with self.subTest(case=label):
                self.sandbox.patch_json(CHECKPOINT_MANIFEST, **fields)
                problems = _acceptance_problems(self.sandbox.root)
                self.assertTrue(
                    any(expected in problem for problem in problems),
                    f"{label} was accepted, or reported as something else: {problems}",
                )
                self.sandbox.restore()

    def test_a_per_round_digest_that_disagrees_with_the_top_level_is_named(self) -> None:
        """The per-round copy exists so a retro-edit cannot hide. The comparison must run."""
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        path = self.sandbox.root / CHECKPOINT_MANIFEST
        self.sandbox._remember(CHECKPOINT_MANIFEST)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for entry in manifest["acceptance_rounds"]:
            if entry.get("round") == manifest["current_round"]:
                entry["tested_candidate_digest"] = "f" * 64
        path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any(
                "the per-round copy exists so a retro-edit cannot hide" in problem
                for problem in problems
            ),
            f"the two copies of the tested digest disagreed and nothing said so: {problems}",
        )

    def test_the_registry_must_carry_exactly_one_cp00_row(self) -> None:
        """Zero rows and two rows are both ambiguity, and ambiguity is a failure."""
        path = self.sandbox.root / CHECKPOINT_REGISTRY
        original = path.read_text(encoding="utf-8")
        row = next(
            line for line in original.splitlines() if line.startswith("| CP-00 ")
        )
        cases = (
            ("no CP-00 row", original.replace(row, row.replace("| CP-00 ", "| CP-99 ", 1))),
            ("two CP-00 rows", original.replace(row, row + "\n" + row, 1)),
        )
        for label, text in cases:
            with self.subTest(case=label):
                self.sandbox._remember(CHECKPOINT_REGISTRY)
                path.write_text(text, encoding="utf-8")
                self.assertEqual(
                    _registry_state_problem(self.sandbox.root),
                    f"{CHECKPOINT_REGISTRY} does not carry exactly one CP-00 row",
                )
                self.sandbox.restore()

    def test_the_absent_document_branches_report_rather_than_assume_agreement(self) -> None:
        """A record that is not there is not a record that agrees.

        Nothing in the suite ever removed one of these files, so every "is missing"
        branch was removable while green. Absence has to be reported: the alternative is
        a check that reads nothing and returns nothing to say about it.
        """
        self.sandbox._remember(PROGRAM_STATE_DOCUMENT)
        (self.sandbox.root / PROGRAM_STATE_DOCUMENT).unlink()
        self.assertEqual(
            _state_document_problems(self.sandbox.root),
            [f"{PROGRAM_STATE_DOCUMENT} is missing"],
        )
        self.sandbox.restore()

        self.sandbox._remember(CHECKPOINT_MANIFEST)
        (self.sandbox.root / CHECKPOINT_MANIFEST).unlink()
        missing = f"{CHECKPOINT_MANIFEST} is missing"
        self.assertEqual(_registry_state_problem(self.sandbox.root), missing)
        self.assertEqual(_state_document_problems(self.sandbox.root), [missing])
        self.assertEqual(_acceptance_problems(self.sandbox.root), [missing])
        self.assertEqual(_tested_digest_problems(self.sandbox.root), [missing])

    def test_an_evidence_digest_that_does_not_reproduce_is_rejected(self) -> None:
        """Evidence from another tree cannot be presented as this round's."""
        self._ratify_for_real()
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        problems = _acceptance_problems(self.sandbox.root)
        self.assertTrue(
            any("does not reproduce over this tree" in problem for problem in problems),
            problems,
        )

    def test_the_retro_edit_rule_is_proved_on_synthetic_history(self) -> None:
        """The repository cannot exercise the rule, so prove it directly.

        **Corrected in round nine.** This docstring used to say "every committed manifest
        so far carries `""` in every per-round digest — no round has been sealed". That
        is false, and round eight had already retracted it in `_digest_history_problems`
        and in §11.11 without following the retraction here. `5207fb5` seals round 5 with
        `22e3027b…`, and it is the only one of the manifest's ten commits carrying a
        per-round value at all.

        The correction matters because it inverts what the sibling probe
        `test_no_per_round_digest_was_edited_after_the_fact` means. "Nothing to compare"
        would make its green meaningless; "one value present and unchanged across every
        commit that carries it" makes it a rule that is running and satisfied. What the
        repository still cannot supply is a value that *changed*, which is what this probe
        constructs and `test_a_real_retro_edit_is_caught_on_real_commits` now builds as
        actual commits.
        """
        sealed = {
            "acceptance_rounds": [
                {"round": 4, "tested_candidate_digest": "a" * 64, "evidence_bundle_digest": "b" * 64},
                {"round": 5, "tested_candidate_digest": "", "evidence_bundle_digest": ""},
            ]
        }
        unchanged = json.loads(json.dumps(sealed))
        self.assertEqual(_digest_history_problems([(sealed, "HEAD~1")], unchanged), [])

        retro = json.loads(json.dumps(sealed))
        retro["acceptance_rounds"][0]["tested_candidate_digest"] = "c" * 64
        self.assertTrue(
            any("was 'aaa" in problem for problem in _digest_history_problems([(sealed, "HEAD~1")], retro)),
            "a retro-edited tested_candidate_digest was accepted",
        )

        dropped = {"acceptance_rounds": [sealed["acceptance_rounds"][1]]}
        self.assertTrue(
            _digest_history_problems([(sealed, "HEAD~1")], dropped),
            "deleting the round entry hid its sealed digest",
        )

        renumbered = json.loads(json.dumps(sealed))
        renumbered["acceptance_rounds"][0]["round"] = 9
        self.assertTrue(
            _digest_history_problems([(sealed, "HEAD~1")], renumbered),
            "renumbering the round hid its sealed digest",
        )

        opened = json.loads(json.dumps(sealed))
        opened["acceptance_rounds"].append(
            {"round": 6, "tested_candidate_digest": "d" * 64, "evidence_bundle_digest": ""}
        )
        self.assertEqual(
            _digest_history_problems([(sealed, "HEAD~1")], opened),
            [],
            "opening a new round is not a retro-edit and must stay silent",
        )

    def test_the_two_records_are_compared_on_all_four_combinations(self) -> None:
        """Manifest state x registry state, every pairing, prose deliberately hostile.

        Each row pairs the structural token with English that says the opposite of what
        the token says, so a predicate that read the prose would get every row wrong.
        The two agreeing combinations must pass and the two contradicting ones must
        fail, whatever the sentence around the token happens to say.
        """
        confirming = "ratified 2026-09-02; tag not yet published"
        denying = "not ratified; not tagged"
        cases = [
            (True, RATIFIED_STATE_TOKEN, denying, None),
            (True, UNRATIFIED_STATE_TOKEN, confirming, "declares ratified=True"),
            (False, UNRATIFIED_STATE_TOKEN, confirming, None),
            (False, RATIFIED_STATE_TOKEN, denying, "declares ratified=False"),
        ]
        for ratified, token, prose, expected in cases:
            with self.subTest(manifest=ratified, registry=token):
                if ratified:
                    self.sandbox.declare_ratification(self.full_delta)
                else:
                    self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
                self.sandbox.set_registry_state(token, prose)
                problem = _registry_state_problem(self.sandbox.root)
                if expected is None:
                    self.assertIsNone(
                        problem,
                        f"agreeing records were rejected; the prose read {prose!r}",
                    )
                else:
                    self.assertIsNotNone(
                        problem,
                        f"contradicting records were accepted; the prose read {prose!r}",
                    )
                    self.assertIn(expected, problem)
                self.sandbox.restore()

    def test_a_registry_row_carrying_no_state_token_is_rejected(self) -> None:
        """The exact counterexamples the independent reviewer produced.

        Both sentences defeated the previous predicate: `\\bratified\\b` matched inside
        `not ratified`, so a denial read as a confirmation. Neither carries a state
        token, so both are now definite failures naming the token to write.
        """
        for prose in ("ratified 2026-09-02; tag not yet published", "not ratified; not tagged"):
            for ratified in (True, False):
                with self.subTest(prose=prose, manifest=ratified):
                    if ratified:
                        self.sandbox.declare_ratification(self.full_delta)
                    else:
                        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
                    self.sandbox.set_registry_state(None, prose)
                    problem = _registry_state_problem(self.sandbox.root)
                    self.assertIsNotNone(problem, "a stateless row was accepted")
                    self.assertIn("must cite exactly one manifest state key", problem)
                    self.sandbox.restore()

    def test_the_comparison_does_not_depend_on_manifest_history(self) -> None:
        """Dropping the spent `ratification_blocked` key must not change the verdict.

        The first form of this check also demanded that the manifest still carry a key
        named by the token. That coupled the two-record comparison to whether history
        was kept: a ratified manifest that retired the blocked entry, exactly as
        `W0-INT-01` would, flipped agreeing records into a failure. Removed, and pinned
        here so it cannot come back.
        """
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
        self.sandbox.drop_json_key(CHECKPOINT_MANIFEST, UNRATIFIED_STATE_TOKEN)
        self.sandbox.set_registry_state(UNRATIFIED_STATE_TOKEN, "not ratified")
        self.assertIsNone(_registry_state_problem(self.sandbox.root))

    def test_a_registry_row_citing_both_tokens_is_rejected(self) -> None:
        """Ambiguity is a failure, not a coin toss."""
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
        self.sandbox.set_registry_state(
            UNRATIFIED_STATE_TOKEN,
            f"not ratified, and not yet `{RATIFIED_STATE_TOKEN}`",
        )
        problem = _registry_state_problem(self.sandbox.root)
        self.assertIsNotNone(problem)
        self.assertIn("must cite exactly one manifest state key", problem)

    def test_each_recorded_reconciliation_is_actually_made(self) -> None:
        """Content, not bytes. Round five's blocker.

        Path equality proves a file moved. It cannot tell an edit that removed a stale
        claim from one that appended a comment beside it, and an independent probe used
        exactly that gap: all five declared, four given comments, no stale statement
        touched, 98/98 green.
        """
        self.assertEqual(_reconciliation_problems(REPOSITORY_ROOT), [])

    def test_ratification_requires_an_accepted_acceptance_round(self) -> None:
        """Ratification is not a field you set; it is a round you passed."""
        self.assertEqual(_acceptance_problems(REPOSITORY_ROOT), [])

    def test_no_per_round_digest_was_edited_after_the_fact(self) -> None:
        """`tested_candidate_digest` is frozen when the round opens."""
        self.assertEqual(_retro_edited_digests(REPOSITORY_ROOT), [])

    def test_the_state_document_and_the_manifest_do_not_contradict_each_other(
        self,
    ) -> None:
        """The third external record, against this repository rather than a sandbox.

        Non-vacuous today: CP-00 is unratified, so this asserts the state document does
        carry the denial the ratified half will require to be gone. A one-directional
        removal check would be silent here and would stay silent if the sentence were
        reworded out of existence.
        """
        self.assertEqual(_state_document_problems(REPOSITORY_ROOT), [])
        self.assertIn(
            PROGRAM_STATE_DOCUMENT,
            _digest_paths(REPOSITORY_ROOT),
            "the state document is outside the digest recipe, so the deadlock this "
            "check was licensed to break no longer exists and the licence should go",
        )

    def test_the_acceptance_digest_model_is_structurally_sound(self) -> None:
        """The split into a tested-input digest and an evidence digest is correct.

        An earlier form recorded one digest computed after the acceptance results were
        written, so it identified the post-acceptance tree rather than the input the
        streams judged. Splitting it is the right fix and this test does not argue with
        it. What it checks is that the split is *present and closed*: both fields exist,
        the retired single field has not come back, and the model documents both.

        Both values *are* recomputed, and not here.
        `test_the_tested_digest_recomputes_over_the_commit_that_froze_it` and
        `_tested_digest_problems` recompute `tested_candidate_digest` over the tree of
        the commit that froze it; `_acceptance_problems` recomputes
        `evidence_bundle_digest` over the tree in front of you. An earlier form of this
        docstring cited §11.9 to say recomputation was impossible until three missing
        fields were supplied. That was wrong, and it licensed leaving the field
        arithmetically unchecked for four rounds — the manifest's recipe blanks only the
        field being computed, and Git keeps the frozen tree forever, so nothing was
        missing.

        This test stops where it stops because the arithmetic and the *shape* are
        separate claims. Recomputation cannot notice that the retired single
        `candidate_digest` came back, that `digest_model` stopped explaining a field, or
        that one of the two fields was dropped altogether — a manifest with one digest
        reproduces perfectly over the one tree it names. That is what this checks, and
        only that.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        self.assertIsNotNone(manifest, f"{CHECKPOINT_MANIFEST} is missing")
        for field in ACCEPTANCE_DIGEST_FIELDS:
            self.assertIn(
                field, manifest, f"{CHECKPOINT_MANIFEST} lost the {field} field"
            )
        self.assertNotIn(
            "candidate_digest",
            manifest,
            "the retired single-digest field is back; it identified the tree that "
            "carried the acceptance results rather than the tree the streams judged",
        )
        model = manifest.get("digest_model")
        self.assertIsInstance(model, dict, "digest_model is missing")
        for field in ACCEPTANCE_DIGEST_FIELDS + ("artifact_manifest_sha256",):
            self.assertIn(field, model, f"digest_model does not explain {field}")

    def test_the_acceptance_digests_are_well_formed_distinct_and_present_when_ratified(
        self,
    ) -> None:
        """Shape, mutual difference, and the link that stops them staying empty.

        `null` is a legitimate state — the candidate is being rebuilt and no round has
        been dispatched — but it may not survive into ratification, or the split would
        be decorative: a checkpoint could ratify with no record of what was tested.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        values = {field: manifest.get(field) for field in ACCEPTANCE_DIGEST_FIELDS}
        for field, value in values.items():
            with self.subTest(field=field):
                if value is not None:
                    self.assertRegex(
                        str(value),
                        r"^[0-9a-f]{64}$",
                        f"{field} is neither null nor a SHA-256 digest",
                    )
        if manifest.get("ratified") is True:
            unset = sorted(field for field, value in values.items() if value is None)
            self.assertEqual(
                unset,
                [],
                "CP-00 cannot ratify while these are unrecorded: a ratified checkpoint "
                "must say which tree the streams judged and which tree carries their "
                "evidence",
            )
        recorded = [value for value in values.values() if value is not None]
        if len(recorded) == 2:
            self.assertNotEqual(
                recorded[0],
                recorded[1],
                "the two digests are equal, so the evidence tree and the tested tree "
                "are the same tree — which is the defect the split exists to prevent: "
                "writing the results changes the tree",
            )

    def test_the_reviewed_manifest_recipe_moves_when_a_reviewed_file_does(self) -> None:
        """A digest nobody proves sensitive is a digest nobody has verified.

        `artifact_manifest_sha256` is the one manifest digest whose recipe is still
        recorded accurately, so it is the one whose sensitivity can be demonstrated
        rather than assumed. One byte in any tracked reviewed file must change it.
        """
        baseline, count = _reviewed_manifest_digest(self.sandbox.root)
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        changed, changed_count = _reviewed_manifest_digest(self.sandbox.root)
        self.assertNotEqual(
            baseline, changed, "a changed reviewed file left the manifest digest alone"
        )
        self.assertEqual(count, changed_count)

    def test_the_manifest_digest_describes_the_tree_it_manifests(self) -> None:
        """The external record must be true about the tree it covers.

        Recomputed with the manifest's own recipe. Before ratification this is the
        candidate digest; after ratification the integrator must recompute it, which is
        the point — a record that kept the pre-ratification digest would be describing a
        tree that no longer exists.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        self.assertIsNotNone(manifest, f"{CHECKPOINT_MANIFEST} is missing")
        digest, count = _reviewed_manifest_digest(REPOSITORY_ROOT)
        self.assertEqual(manifest["artifact_count"], count)
        self.assertEqual(
            manifest["artifact_manifest_sha256"],
            digest,
            "artifact_manifest_sha256 does not match the tracked reviewed families; "
            "recompute it with the recipe the manifest itself records",
        )


class SandboxResetTests(unittest.TestCase):
    """The sandbox must reset to the frozen tree on the tree that actually gets published.

    Round eight's independent review found the whole `RatificationRecordTests` family
    dead — 26 tests, on a clean working tree with `ratified: false` — as soon as the
    integrator committed this round's acceptance reports, which
    `docs/program/reviews/W0-QA-01.md` §11.12.6 instructs them to do before ratifying.
    A path that is tracked and absent from the frozen tree could not be unlinked without
    leaving the index, the reset recorded it as unresettable, and every probe that needs
    a reset sandbox refused to run. The checkpoint would have been tagged with none of
    round seven's guarantees exercised.

    Both green orderings were illegitimate: leaving the reports untracked never publishes
    the evidence, and committing them before the freeze puts the streams' own verdicts
    inside the tree they judge — the retired single-`candidate_digest` defect. So the
    fix is not an ordering, and it is not a narrower gate at publication either.

    This probe reproduces the published tree inside the module: a sandbox, a file
    committed to its **own private copy** after the freeze, and a reset that must
    succeed. It is the permanent form of the clone reproduction in §11.13.1.
    """

    IDENTITY = (
        "-c",
        "user.email=w0-qa-01@example.invalid",
        "-c",
        "user.name=W0-QA-01 reset probe",
    )

    def setUp(self) -> None:
        self.sandbox = _CheckpointSandbox()
        self.addCleanup(self.sandbox.__exit__)

    def test_a_path_committed_after_the_freeze_still_resets(self) -> None:
        published = "artifacts/checkpoints/CP-00/probe-report-after-the-freeze.md"
        frozen = _freeze_commit(self.sandbox.root)
        self.assertIsNotNone(frozen, "this repository records no frozen digest")
        blobs = _tree_blobs(self.sandbox.root, frozen)
        self.assertNotIn(
            published, blobs, "the probe path is already in the frozen tree"
        )

        (self.sandbox.root / published).write_text("PASS\n", encoding="utf-8")
        self.sandbox._git_write("add", "--", published)
        self.sandbox._git_write(*self.IDENTITY, "commit", "--quiet", "-m", "publish")
        self.assertIn(
            published,
            _digest_paths(self.sandbox.root),
            "the probe did not actually publish anything",
        )
        self.assertNotIn(
            published,
            _git(
                "-C", str(self.sandbox.root), "ls-files", "--others",
                "--exclude-standard", text=True, check=True,
            ).stdout.split("\n"),
            "the published path is untracked, so it is not the case this probe is for",
        )

        self.sandbox.normalise_to_candidate()

        self.assertEqual(
            self.sandbox.unresettable,
            [],
            "the sandbox could not be returned to the frozen tree after a publication",
        )
        self.assertFalse((self.sandbox.root / published).exists())
        self.assertNotIn(published, _digest_paths(self.sandbox.root))
        self.assertEqual(
            _acceptance_digest(self.sandbox.root, "tested_candidate_digest"),
            self.sandbox.frozen_digest,
            "the reset tree does not digest to the frozen value, so the reset put the "
            "sandbox somewhere other than the tree the streams judged",
        )

    def test_unresettable_names_a_reset_that_did_not_finish(self) -> None:
        """The net is connected to something.

        Both call sites only ever assert that `unresettable` is empty, so replacing its
        computation with a literal `[]` passed the whole suite — an alarm nobody could
        distinguish from a disconnected one. Suppressing the index drop reproduces
        exactly the state the attribute exists to name: the published path is gone from
        the working tree, still in the index, still enumerated by the recipe, so the
        sandbox is genuinely not the frozen tree and must say so.

        **Round twelve: the literal expectation was itself pinned to the unratified
        tree.** ``[published]`` is the whole answer only while this probe's own file is
        the one thing committed since the freeze. On the tree that actually gets tagged
        it is not: `docs/program/reviews/W0-QA-01.md` §11.12.6 has the integrator commit
        both acceptance reports *before* ratifying, so they are post-freeze tracked paths
        too and the suppressed reset cannot return them either. The probe went red on a
        correctly published tree while the attribute it tests was behaving exactly as
        designed.

        So the expectation is **derived**, in both states, from what a legitimate
        publication is allowed to have added: this probe's own path plus the round's own
        declared acceptance evidence, taken from the manifest and filtered to what is
        actually in the index and actually absent from the frozen tree. On the
        unratified tree no round declares any evidence and the expectation is
        ``[published]``, exactly as before; on a published tree it is the honest three.
        It is still an equality against an independently produced set — the declared
        report paths and the index come from somewhere other than
        ``_digest_paths(...) - blobs`` — so `[]` fails in both states and so does a
        hardcoded ``[published]``, which is one more mutant than round eleven caught.

        Nothing else may appear here. A post-freeze path that is *not* declared
        acceptance evidence is what :func:`_post_freeze_delta_problems` voids the round
        for, so widening this expectation to "whatever turned up" would launder exactly
        the drift that check exists to refuse.

        **Round thirteen widened it by exactly one term, for the same reason round
        twelve widened it at all.** A published tree carries the eight evidence
        deliverables as well, committed after the freeze, so the expectation is the
        round's declared evidence *plus the post-freeze licence* — filtered, as before,
        to what is in the index and absent from the frozen tree. On the unratified tree
        every ceiling path is either already in the frozen tree or not in the index, so
        the answer is still ``[published]`` and both mutants round twelve added stay
        dead. It remains an equality against an independently produced set: the licence
        is a module constant and the index comes from `git ls-files --cached`, neither of
        which is ``_digest_paths(...) - blobs``.
        """
        published = "artifacts/checkpoints/CP-00/probe-report-unresettable.md"
        (self.sandbox.root / published).write_text("PASS\n", encoding="utf-8")
        self.sandbox._git_write("add", "--", published)
        self.sandbox._git_write(*self.IDENTITY, "commit", "--quiet", "-m", "publish")

        frozen = _freeze_commit(self.sandbox.root)
        self.assertIsNotNone(frozen, "this repository records no frozen digest")
        blobs = _tree_blobs(self.sandbox.root, frozen)
        self.assertIsNotNone(blobs, "the frozen tree is unreadable in the sandbox")
        cached = set(
            _git(
                "-C", str(self.sandbox.root), "ls-files", "--cached", text=True, check=True
            ).stdout.split("\n")
        )
        manifest = _checkpoint_manifest(self.sandbox.root) or {}
        evidence = {
            path
            for path in _declared_evidence_paths(manifest) | POST_FREEZE_DELTA_CEILING
            if path not in blobs and path in cached
        }
        expected = sorted({published} | evidence)

        with unittest.mock.patch.object(_CheckpointSandbox, "_git_write"):
            self.sandbox._reset_to_the_frozen_tree()

        self.assertEqual(
            self.sandbox.unresettable,
            expected,
            "the reset left a path the frozen tree does not have and reported nothing",
        )

    def test_the_sandbox_root_this_class_built_is_accepted(self) -> None:
        """The positive direction, so the guard cannot be satisfied by refusing always.

        Every refusal probe lives in :class:`WritingCommandGuardTests`; without this one
        a guard that raised unconditionally would pass all of them.
        """
        self.assertIsNone(_refuse_to_write_outside(self.sandbox.root, _CheckpointSandbox.PREFIX))

    def test_normalise_to_candidate_erases_an_ambient_mid_ratification_state(self) -> None:
        """`normalise_to_candidate`'s manifest reset, exercised against a dirtied tree.

        Every `RatificationRecordTests` probe trusts that starting from a normalised
        sandbox means starting from the same state regardless of what the *host*
        repository happens to be carrying — round five's fix for the third instance of
        this module's ambient-state coupling (§11.10). Nothing had directly attacked the
        reset itself: every existing caller only ever normalises a sandbox that was
        already close to clean. Here the manifest is driven into a fully ratified,
        fully accepted shape first — flag, record, sealed digests, an accepted round
        with reports on disk — and `normalise_to_candidate` is then required to erase
        all of it, not just the fields the other probes happen to touch.
        """
        self.sandbox.normalise_to_candidate()
        self.sandbox.declare_ratification(
            [POST_FREEZE_STRANGER]
        )  # any non-empty delta; only the manifest shape is under test here
        self.sandbox.accept_round()
        self.sandbox.seal_digests(tested=self.sandbox.frozen_digest)
        dirtied = json.loads(
            (self.sandbox.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        self.assertIs(dirtied["ratified"], True, "the harness did not dirty ratified")
        self.assertIn("ratification", dirtied, "the harness did not dirty the record")
        number = dirtied["current_round"]
        dirty_entry = next(
            e for e in dirtied["acceptance_rounds"] if e.get("round") == number
        )
        self.assertEqual(dirty_entry["verdict"], "PASS", "the harness did not dirty verdict")
        self.assertIsNotNone(
            dirty_entry["manual_report"], "the harness did not dirty manual_report"
        )

        self.sandbox.normalise_to_candidate()

        clean = json.loads(
            (self.sandbox.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        self.assertIs(clean["ratified"], False, "ratified was not reset")
        self.assertNotIn("ratification", clean, "the ratification record was not removed")
        for field in ACCEPTANCE_DIGEST_FIELDS:
            self.assertIsNone(clean[field], f"{field} was not reset at the top level")
        entry = next(e for e in clean["acceptance_rounds"] if e.get("round") == number)
        self.assertIsNone(entry["verdict"], "the round verdict was not reset")
        self.assertEqual(
            entry["streams"], {"automated": None, "manual": None},
            "the round's stream results were not reset",
        )
        self.assertIsNone(entry["manual_report"], "manual_report was not reset")
        self.assertIsNone(entry["automated_report"], "automated_report was not reset")
        for field in ACCEPTANCE_DIGEST_FIELDS:
            self.assertEqual(entry[field], "", f"the round's {field} copy was not reset")
        for stream in ("manual_acceptance", "automated_acceptance"):
            record = clean[stream]
            self.assertEqual(record["status"], "owed", f"{stream}.status was not reset")
            self.assertIsNone(record["report_path"], f"{stream}.report_path was not reset")
            self.assertEqual(record["round"], number, f"{stream}.round was not reset")
        # And the checks that read the manifest agree it is clean, not just the fields
        # this test happened to name.
        self.assertEqual(_acceptance_problems(self.sandbox.root), [])
        external, declared, problems = _ratification_record(self.sandbox.root)
        self.assertFalse(external)
        self.assertEqual(declared, frozenset())
        self.sandbox._git_write("status", "--porcelain")

    # ---- the freeze the sandbox stands on, when the live tree has none --------------

    def test_a_recovered_freeze_is_a_real_freeze(self) -> None:
        """**The price of letting the sandbox reach into history for a freeze.**

        A round that has not been dispatched carries `tested_candidate_digest: null`, and
        the live repository sits there between rounds. Every post-freeze probe then has
        no frozen tree to measure against and the whole family fails — not skips —
        because `_ratify_for_real` refuses to build a ratification on a digest no commit
        froze. :meth:`_CheckpointSandbox._ensure_a_frozen_round` removes that by writing
        the newest self-consistent frozen manifest out of history into the sandbox's own
        copy.

        What must not follow is a sandbox standing on a value nothing produced — that is
        precisely the defect round seven found in the live manifest. So whichever way the
        sandbox got its freeze, the value has to reproduce over the tree of the commit it
        names, by the recipe the manifest itself records, and the reset has to land on
        that tree.
        """
        commit = _freeze_commit(self.sandbox.root)
        self.assertIsNotNone(
            commit,
            "the sandbox has no frozen round to stand on, so every post-freeze probe "
            "in this module is measuring nothing",
        )
        declared = (_checkpoint_manifest(self.sandbox.root) or {}).get(
            "tested_candidate_digest"
        )
        self.assertEqual(
            _acceptance_digest_at(self.sandbox.root, commit, "tested_candidate_digest"),
            declared,
            "the freeze the sandbox stands on does not reproduce over the tree of the "
            "commit that froze it, so the recovery manufactured a value instead of "
            "finding one",
        )
        # Not always on. With a freeze already resolvable the recovery does nothing, so
        # a live repository that has frozen its own round is measured against *that*
        # freeze and never against an older one.
        self.assertFalse(
            self.sandbox._ensure_a_frozen_round(),
            "the recovery fired on a sandbox that already resolves a freeze of its own",
        )

        # And on. Driven into the between-rounds state the live repository holds while a
        # round is open and not yet frozen — which is where 122 tests failed — the
        # recovery must reach a real freeze again rather than leave the family dark.
        # Deliberately not read off the live manifest: that value moves under a
        # concurrently running integrator, and a probe whose direction depends on it
        # measures the ambient state rather than the mechanism.
        path = self.sandbox.root / CHECKPOINT_MANIFEST
        document = json.loads(path.read_text(encoding="utf-8"))
        document["tested_candidate_digest"] = None
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.assertIsNone(
            _freeze_commit(self.sandbox.root),
            "the probe did not reach the between-rounds state it is about",
        )
        self.assertTrue(
            self.sandbox._ensure_a_frozen_round(),
            "a sandbox with no freeze of its own recovered none from history, so every "
            "post-freeze probe would fail on a legitimate between-rounds repository",
        )
        self.assertEqual(_freeze_commit(self.sandbox.root), commit)

        self.sandbox.normalise_to_candidate()
        self.assertEqual(self.sandbox.frozen_commit, commit)
        self.assertEqual(self.sandbox.frozen_digest, declared)
        self.assertEqual(self.sandbox.unresettable, [])
        self.assertEqual(
            _acceptance_digest(self.sandbox.root, "tested_candidate_digest"),
            declared,
            "the reset landed somewhere other than the tree that freeze names",
        )

    def test_a_history_with_no_freeze_at_all_recovers_nothing(self) -> None:
        """The recovery discriminates; it does not return the newest thing it sees.

        Three revisions in a throwaway repository: one with no digest at all, one with a
        self-consistent freeze, and a newest one whose top-level value no round entry
        carries. The first must be refused, the third must be refused, and the second
        must be the answer — otherwise "the newest manifest revision that carried a
        freeze" is just "the newest manifest revision", and the sandbox would reset to a
        tree whose digest cannot reproduce.
        """
        history = _ManifestHistory()
        self.addCleanup(history.close)
        elsewhere = _CheckpointSandbox.__new__(_CheckpointSandbox)
        elsewhere.root = history.root

        history.commit("a round nobody froze", _history_manifest(None))
        self.assertIsNone(
            _CheckpointSandbox._the_newest_frozen_manifest(elsewhere),
            "a history whose manifests carry no digest at all produced a freeze",
        )

        digest = history.seal(number=5, rounds=(4, 5))
        history.commit("the freeze", _history_manifest(digest, number=5, rounds=(4, 5)))
        recovered = _CheckpointSandbox._the_newest_frozen_manifest(elsewhere)
        self.assertIsNotNone(recovered, "a real freeze in history was not found")
        self.assertEqual(json.loads(recovered).get("current_round"), 5)

        half = _history_manifest(digest, number=7, rounds=(6, 7))
        half["acceptance_rounds"][-1]["tested_candidate_digest"] = ""
        history.commit("a top-level value no round entry carries", half)
        recovered = _CheckpointSandbox._the_newest_frozen_manifest(elsewhere)
        self.assertIsNotNone(recovered)
        self.assertEqual(
            json.loads(recovered).get("current_round"),
            5,
            "a revision whose round entry does not carry the top-level value was "
            "accepted as a freeze; _freeze_commit cannot resolve one of those",
        )


class WritingCommandGuardTests(unittest.TestCase):
    """`_refuse_to_write_outside`, one branch at a time, against both of its callers.

    Round nine's blocker was that this guard's prose named a property its code did not
    have — it never tested whether the target was *inside* `REPOSITORY_ROOT` — and that
    its prefix branch was unreachable from the only probe that existed, so deleting
    either left the suite green. An independent reviewer used the gap to drop a file from
    one of the immutable reviewed families out of the index.

    Every case below asserts the **specific reason**, not merely that something raised.
    That is the whole difference: with a single shared message, deleting one branch
    leaves another catching the same input and every probe still passes. And every case
    asserts that `subprocess.run` was never called, so the guard is proved to run before
    the command rather than beside it.

    None of the bad roots is ever created on disk. The guard refuses on the path, so a
    probe that made a directory inside the repository to prove the point would be dirtying
    the tree it is protecting.
    """

    #: `(reason, root factory)`. The factory takes the prefix so a case can be built that
    #: passes every earlier branch and can only be caught by the one it is for.
    CASES = (
        (WRITE_REFUSAL_IS_THE_REPOSITORY, lambda prefix: REPOSITORY_ROOT),
        (WRITE_REFUSAL_CONTAINS_THE_REPOSITORY, lambda prefix: REPOSITORY_ROOT.parent),
        (
            WRITE_REFUSAL_INSIDE_THE_REPOSITORY,
            lambda prefix: REPOSITORY_ROOT / f"{prefix}not-really-a-sandbox",
        ),
        (
            WRITE_REFUSAL_NOT_OURS,
            lambda prefix: Path(tempfile.gettempdir()) / "not-one-of-ours",
        ),
    )

    def _refusals(self, prefix: str):
        for reason, factory in self.CASES:
            yield reason, factory(prefix)

    def test_every_branch_refuses_with_its_own_reason(self) -> None:
        for reason, root in self._refusals(_CheckpointSandbox.PREFIX):
            with self.subTest(reason=reason):
                with self.assertRaises(AssertionError) as caught:
                    _refuse_to_write_outside(root, _CheckpointSandbox.PREFIX)
                self.assertIn(reason, str(caught.exception))

    def test_the_case_for_each_branch_passes_every_earlier_branch(self) -> None:
        """Otherwise a case proves only that *some* branch fired.

        The inside-the-repository root carries the sandbox prefix, so the prefix branch
        cannot catch it; the wrong-prefix root is outside the repository, so none of the
        first three can. That is what makes deleting either one turn a probe red.
        """
        prefix = _CheckpointSandbox.PREFIX
        inside = REPOSITORY_ROOT / f"{prefix}not-really-a-sandbox"
        self.assertTrue(inside.name.startswith(prefix))
        self.assertTrue(inside.resolve().is_relative_to(REPOSITORY_ROOT.resolve()))

        stranger = Path(tempfile.gettempdir()) / "not-one-of-ours"
        resolved = stranger.resolve()
        repository = REPOSITORY_ROOT.resolve()
        self.assertNotEqual(resolved, repository)
        self.assertFalse(repository.is_relative_to(resolved))
        self.assertFalse(resolved.is_relative_to(repository))
        self.assertFalse(resolved.name.startswith(prefix))

    def test_the_sandbox_caller_refuses_before_spawning_anything(self) -> None:
        sandbox = _CheckpointSandbox.__new__(_CheckpointSandbox)
        for reason, root in self._refusals(_CheckpointSandbox.PREFIX):
            with self.subTest(reason=reason):
                sandbox.root = root
                with unittest.mock.patch.object(subprocess, "run") as spawned:
                    with self.assertRaises(AssertionError) as caught:
                        sandbox._git_write("rm", "--cached", "--", "contracts/README.md")
                self.assertIn(reason, str(caught.exception))
                spawned.assert_not_called()

    def test_the_history_caller_refuses_before_spawning_anything(self) -> None:
        """F2: the same guard, on the helper that runs `init`, `add` and `commit`.

        It used to be a byte-for-byte copy carrying the copy's blind spot, and nothing
        exercised it at all. It is now the same function, and this probe is what says so.
        """
        history = _ManifestHistory.__new__(_ManifestHistory)
        for reason, root in self._refusals(_ManifestHistory.PREFIX):
            with self.subTest(reason=reason):
                history.root = root
                with unittest.mock.patch.object(subprocess, "run") as spawned:
                    with self.assertRaises(AssertionError) as caught:
                        history._run("commit", "--allow-empty", "-m", "probe")
                self.assertIn(reason, str(caught.exception))
                spawned.assert_not_called()

    def test_both_callers_share_one_guard(self) -> None:
        """A copy is what failed; this is the probe that a copy has not come back."""
        source = inspect.getsource(_CheckpointSandbox._git_write) + inspect.getsource(
            _ManifestHistory._run
        )
        self.assertEqual(source.count("_refuse_to_write_outside("), 2)
        self.assertNotIn("is_relative_to", source)

    def test_a_throwaway_history_root_is_accepted(self) -> None:
        """The positive direction for the second caller."""
        history = _ManifestHistory()
        self.addCleanup(history.close)
        self.assertIsNone(_refuse_to_write_outside(history.root, _ManifestHistory.PREFIX))

    def _seed_victim_repository(self) -> Path:
        """A throwaway repository this test may lose, distinct from every root the
        module itself creates, standing in for "some other repository on the same
        host" — a post-commit hook's checkout, a colleague's clone, anything a
        hostile ``GIT_DIR`` could name."""
        victim = Path(tempfile.mkdtemp(prefix="w0-qa-01-victim-"))
        self.addCleanup(shutil.rmtree, victim, True)
        (victim / "contracts").mkdir()
        (victim / "contracts" / "README.md").write_text(
            "victim content, never written by this module\n", encoding="utf-8"
        )
        identity = ("-c", "user.email=victim@example.invalid", "-c", "user.name=victim")
        for arguments in (
            ["init", "--quiet"],
            [*identity, "add", "-A"],
            [*identity, "commit", "--quiet", "-m", "seed"],
        ):
            _git("-C", str(victim), *arguments, check=True)
        return victim

    @staticmethod
    def _tracked_listing(root: Path) -> str:
        return _git("-C", str(root), "ls-files", text=True, check=True).stdout

    @classmethod
    def _tracked_files(cls, root: Path) -> set[str]:
        """Tracked paths only — unlike :func:`_digest_paths`, dropping a path from
        the index does not make it vanish from this set's complement: the file is
        still on disk, so `_digest_paths` would immediately re-report it as
        untracked. This is the set that actually answers "is it still in the
        index"."""
        return {line for line in cls._tracked_listing(root).split("\n") if line}

    @staticmethod
    def _head(root: Path) -> str:
        """The victim's own `HEAD`. `_ManifestHistory._run` runs `commit`, not only
        index-editing commands, and `commit --allow-empty` changes no tracked file at
        all — so a tracked-file comparison alone would miss a spurious commit injected
        into the victim's history. This is what would catch that."""
        return _git(
            "-C", str(root), "rev-parse", "HEAD", text=True, check=True
        ).stdout.strip()

    def test_a_hostile_git_dir_cannot_redirect_either_writer(self) -> None:
        """BLOCKING 1, reproduced against a throwaway victim and shown closed.

        ``-C`` only sets the working directory Git starts discovery from. ``GIT_DIR``,
        ``GIT_WORK_TREE`` and ``GIT_INDEX_FILE`` override discovery outright and are not
        overridden by ``-C`` — the guard validated the path argument and never inspected
        the environment that actually decides where a write lands. An independent
        reviewer used exactly that gap, with a legitimate sandbox root, to drop a file
        from one of the immutable reviewed families out of another repository's index.

        The victim here is a throwaway this test seeds and deletes, never
        `REPOSITORY_ROOT` — this task may not write to the repository under review even
        to prove the point. Both writers are pointed at it through the environment,
        exactly the way a post-commit hook or ``git bisect run`` would set it, and the
        assertion is on the victim's bytes, not on a caught exception: a guard that
        raises proves the path argument was checked, which is precisely what round nine's
        blocker showed is not enough.
        """
        victim = self._seed_victim_repository()
        before_listing = self._tracked_listing(victim)
        before_content = (victim / "contracts" / "README.md").read_bytes()
        before_head = self._head(victim)

        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self.assertIn("contracts/README.md", self._tracked_files(sandbox.root))
        history = _ManifestHistory()
        self.addCleanup(history.close)
        history_head_before = history.commit("seed", _history_manifest(None))

        hostile = {
            "GIT_DIR": str(victim / ".git"),
            "GIT_WORK_TREE": str(victim),
            "GIT_INDEX_FILE": str(victim / ".git" / "index"),
        }
        with unittest.mock.patch.dict(os.environ, hostile):
            sandbox._git_write("rm", "--cached", "--", "contracts/README.md")
            history._run("commit", "--allow-empty", "-m", "hostile-environment probe")

        self.assertEqual(
            self._tracked_listing(victim),
            before_listing,
            "the victim repository's tracked-file set moved",
        )
        self.assertEqual(
            (victim / "contracts" / "README.md").read_bytes(),
            before_content,
            "the victim's tracked file moved",
        )
        self.assertEqual(
            self._head(victim),
            before_head,
            "the victim gained a commit — `commit --allow-empty` changes no tracked "
            "file, so the two assertions above would miss this on their own",
        )

        # Both commands still did what they were asked — against the right target.
        self.assertNotIn(
            "contracts/README.md",
            self._tracked_files(sandbox.root),
            "the sandbox's own write did not take effect; this probe would prove "
            "nothing about redirection",
        )
        self.assertNotEqual(
            history.head(),
            history_head_before,
            "the history's own write did not take effect; this probe would prove "
            "nothing about redirection",
        )

    def test_removing_the_environment_sanitiser_lets_the_hostile_git_dir_through(
        self,
    ) -> None:
        """The mutation this guard exists to fail: shown red without the fix.

        Without this, :meth:`test_a_hostile_git_dir_cannot_redirect_either_writer`
        proves nothing — a probe that asserts a victim is intact passes just as well
        when the redirect never worked in the first place. This is the other direction:
        the discovery variables *do* reach Git, and the write lands in the victim.

        **What is reconstructed, and what deliberately is not.** Round nine's form of
        this probe put the hostile names on ``os.environ`` and called
        ``subprocess.run`` with no ``env=`` at all, inheriting the caller's environment
        whole. That is a faithful reconstruction of the old *call*, and it is also a
        live copy of the defect this round exists to close: run the suite under a
        ``HOME`` whose ``.gitconfig`` sets ``core.fsmonitor``, and this one probe — the
        only remaining unsanitised spawn in the module — executed the attacker's
        script. The acceptance gate for round ten caught exactly this and nothing else.

        So the reconstruction is narrowed to the property under demonstration: the
        three discovery variables reach Git, through :func:`_git`'s one deliberate
        widening, ``env_extra``. Everything else is still the allowlist. The probe
        proves what it mutates and no longer ships what it is testing for — and it
        doubles as the record of what ``env_extra`` costs, which is why the widening
        exists at exactly one production call site and is named in the argument list
        where a reader can see it.
        """
        victim = self._seed_victim_repository()
        before_listing = self._tracked_listing(victim)

        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self.assertIn("contracts/README.md", self._tracked_files(sandbox.root))

        hostile = {
            "GIT_DIR": str(victim / ".git"),
            "GIT_WORK_TREE": str(victim),
            "GIT_INDEX_FILE": str(victim / ".git" / "index"),
        }

        def unguarded_git_write(self: _CheckpointSandbox, *arguments: str) -> None:
            _refuse_to_write_outside(self.root, self.PREFIX)
            # The path argument is checked, exactly as before; the environment that
            # actually decides where the write lands is not.
            _git("-C", str(self.root.resolve()), *arguments, check=True,
                 env_extra=hostile)

        with unittest.mock.patch.object(
            _CheckpointSandbox, "_git_write", unguarded_git_write
        ):
            sandbox._git_write("rm", "--cached", "--", "contracts/README.md")

        self.assertNotEqual(
            self._tracked_listing(victim),
            before_listing,
            "the unguarded call left the victim untouched, so it is not a faithful "
            "reconstruction of the pre-fix defect and this probe proves nothing",
        )
        # The victim is a throwaway seeded by this test and removed in cleanup; the
        # drift just proved is the point of the probe, not something to repair here.


#: The only functions in this module allowed to spawn a subprocess at all. Everything
#: else that needs Git calls :func:`_git`; everything that needs a documented shell
#: block calls :func:`_run_shell`.
#:
#: These are **module-level** names, and :func:`_spawn_sites` reports the whole enclosing
#: scope, so a chokepoint is a position in the file and not a spelling. Round ten matched
#: the innermost enclosing function *name*, which made "chokepoint" a property of what a
#: function is called: a helper named `_git` defined inside a test body was exempted from
#: the outside-a-chokepoint rule — the exact placement
#: :meth:`GitSpawnChokepointTests.test_a_helper_nested_inside_a_test_is_attributed_to_itself`
#: advertises this enumeration closes. A nested `_git` is now
#: ``ClassName.test_name._git``, which is not in this tuple and never can be.
GIT_SPAWN_CHOKEPOINTS = ("_git", "_run_shell")

#: The process-spawning APIs this enumeration covers, by **resolved** dotted name rather
#: than by the spelling at the call site — see :func:`_resolved_target`.
#:
#: **What "covers" means, stated at the width the method actually has.** Round eleven's
#: form of this comment said "every process-spawning API a future edit might reach for",
#: and an independent reviewer named three it does not reach:
#: `concurrent.futures.ProcessPoolExecutor`, a locally defined subclass of
#: `subprocess.Popen`, and `multiprocessing.get_context("fork").Process`. The first was
#: a real gap and is closed below — it is an ordinary dotted name and belongs in the
#: list. The other two are not spellings this list was missing; they are shapes
#: :func:`_resolved_target` does not resolve, and they are recorded as such in
#: :data:`UNRESOLVABLE_SPAWN_ROUTES` rather than chased with more entries. §11.17.3's
#: operative claim was already bounded correctly; it was this comment that overstated
#: it, which is the defect of putting a check beside a claim it cannot make — and
#: exactly why the sentence is narrowed rather than the list padded.
#:
#: What is claimed: a call whose target resolves, through any import spelling and in any
#: nesting, to one of the names below, outside a chokepoint, fails the suite the moment
#: it is written.
#:
#: Round ten's form of this list matched ``ast.unparse(node.func)`` against 19 literal
#: spellings, which is the failure mode §8.15 and §11.16.2 claim to have escaped, moved
#: up one level: from a list of Git command names known on the day it was written to a
#: list of Python API spellings known on the day it was written. ``import subprocess as
#: sp``, ``from subprocess import run``, ``from os import system`` and ``import os as
#: _o`` are four different spellings of three calls already in this list, and all four
#: walked past it. The ``l``-variants of the ``exec``/``spawn`` families were missing
#: outright while their ``v``-variants were present.
SPAWN_APIS = (
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.getoutput",
    "subprocess.getstatusoutput",
    "os.system",
    "os.popen",
    "os.execl",
    "os.execle",
    "os.execlp",
    "os.execlpe",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "os.posix_spawn",
    "os.posix_spawnp",
    "os.fork",
    "os.forkpty",
    "pty.spawn",
    "pty.fork",
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
    "asyncio.subprocess.create_subprocess_exec",
    "asyncio.subprocess.create_subprocess_shell",
    "multiprocessing.Process",
    "multiprocessing.Pool",
    "concurrent.futures.ProcessPoolExecutor",
)

#: **The cap on what a static enumeration can claim, recorded rather than chased.**
#:
#: Every route below reaches a subprocess through a target :func:`_resolved_target`
#: cannot reduce to a member of :data:`SPAWN_APIS`, so no list of API spellings contains
#: it. Five of the seven name something that does not exist until the program runs. The
#: last two, added in round twelve, are different and are described as what they are: a
#: subclass of a spawning API is a name that *does* exist statically, and an attribute
#: of a call's return value is spelled out in the source — resolving either would take
#: class-hierarchy analysis or return-type inference, neither of which this module does
#: and neither of which it claims. They are a limitation of the method, not a defect to
#: close, and pretending otherwise would put a check beside a claim it cannot make — the
#: shape of defect this module has had to repair in every round since seven.
#:
#: What the enumeration does claim is bounded and worth having: an *honest* edit — a
#: nineteenth caller written the way the eighteen were, under any import spelling, in
#: any nesting, at any of the API families above — fails the suite the moment it is
#: written. An author with write access to this file who is determined to run a
#: subprocess can run one; a test module does not outrank its own author, and §11.17.3
#: says so in the report rather than here alone.
UNRESOLVABLE_SPAWN_ROUTES = (
    "eval() or exec() over a string assembled at runtime",
    "importlib.import_module() with a computed module name",
    "getattr(subprocess, <computed attribute name>)",
    "a callable passed in as an argument, or read out of a dict or attribute",
    "rebinding an imported name at runtime, so the import no longer describes the call",
    "a class defined in this file whose base is a spawning API, called by its own name",
    "an attribute reached through a call's return value, such as "
    "multiprocessing.get_context('fork').Process",
)

#: The two keyword names that widen a constructed environment, kept as data so that
#: :func:`_widening_sites` and the two chokepoint signatures cannot drift into two
#: different lists.
ENV_WIDENING_KEYWORDS = ("env_extra", "env_overrides")

#: Names :func:`_table_reference` and :func:`_is_a_literal_expectation` treat as pure
#: shape, so ``sorted(TABLE)``, ``len(TABLE)`` and ``frozenset({"a"})`` read as a table
#: reference and a literal respectively. Nothing here can reach a value that is not in
#: the expression itself.
PURE_CONSTRUCTORS = frozenset({"frozenset", "set", "tuple", "list", "dict", "sorted", "len"})


def _import_bindings(tree: ast.AST) -> dict[str, str]:
    """``local name -> the dotted path it actually names``, for every import in ``tree``.

    This is the whole of the bounded repair. ``from subprocess import run as _spawn``
    binds ``_spawn`` to ``subprocess.run``; ``import os as _o`` binds ``_o`` to ``os``.
    Resolving the binding is what lets :data:`SPAWN_APIS` be a list of *APIs* instead of
    a list of *spellings*, and a list of spellings is a denylist wearing an allowlist's
    clothes: correct for the names its author typed.

    Imports are collected from the whole tree, not only module level, because a function
    body may import too — which is exactly where somebody would put one.
    """
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    bindings[alias.asname] = alias.name
                else:
                    head = alias.name.split(".")[0]
                    bindings[head] = head
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue  # a relative import; this module has none and never will
            for alias in node.names:
                bindings[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return bindings


def _resolved_target(node: ast.expr, bindings: dict[str, str]) -> str:
    """The dotted name a call reaches, with import aliases resolved.

    ``sp.run`` under ``import subprocess as sp`` resolves to ``subprocess.run``;
    ``_spawn`` under ``from subprocess import run as _spawn`` resolves to the same
    thing. A name this module did not import is returned as written, which is what makes
    ``_git``, ``_run_shell`` and ``_allowlisted_env`` resolvable by the same function.
    """
    spelled = ast.unparse(node)
    head, dot, rest = spelled.partition(".")
    resolved = bindings.get(head)
    if resolved is None:
        return spelled
    return f"{resolved}.{rest}" if dot else resolved


def _scopes(tree: ast.AST) -> list[tuple[int, int, str]]:
    """``(first line, last line, dotted scope)`` for every function, classes included.

    Class bodies contribute their name to the path, so two classes may each hold an
    ``_arm`` and the enumeration can still tell them apart — and so that a chokepoint
    cannot be counterfeited by naming a nested helper ``_git``.
    """
    spans: list[tuple[int, int, str]] = []

    def descend(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f"{prefix}.{child.name}" if prefix else child.name
                if not isinstance(child, ast.ClassDef):
                    spans.append(
                        (child.lineno, child.end_lineno or child.lineno, qualified)
                    )
                descend(child, qualified)
            else:
                descend(child, prefix)

    descend(tree, "")
    return spans


def _enclosing_functions(tree: ast.AST):
    """``(line) -> innermost enclosing function, fully qualified``, for one module."""
    spans = _scopes(tree)

    def enclosing(line: int) -> str:
        inner = [span for span in spans if span[0] <= line <= span[1]]
        return max(inner, key=lambda span: span[0])[2] if inner else "<module>"

    return enclosing


class _SpawnSite(NamedTuple):
    """One process spawn, as the enumeration sees it.

    ``function`` is the innermost enclosing function by simple name and is what a reader
    recognises; ``qualname`` is the whole scope path and is what the chokepoint test
    compares, because a simple name can be chosen and a position cannot.
    """

    line: int
    function: str
    qualname: str
    api: str
    env: str | None
    sanitised: bool


def _spawn_sites(source: str) -> list[_SpawnSite]:
    """Every process spawn in ``source``, with its scope and its ``env=``.

    Static, over the module's own text, because that is the only thing that answers the
    question actually being asked — not "did the calls we happened to exercise behave"
    but "is there anywhere in this file that spawns a process another way". A runtime
    spy answers the first and the first is what round nine passed.

    Three things are resolved rather than matched on surface text: the call target
    (:func:`_resolved_target`, so an aliased import is the same call), the enclosing
    scope (:func:`_scopes`, so a nested helper is not the function it sits in and cannot
    borrow a chokepoint's name), and ``env=``, which must be a **call to**
    :func:`_allowlisted_env` and not merely an expression that starts with its name.
    The round-ten predicate was ``environment.startswith("_allowlisted_env(")``, which
    accepts ``env=_allowlisted_env() | dict(os.environ)`` — the sanitiser and then the
    caller's whole environment on top of it.
    """
    tree = ast.parse(source)
    bindings = _import_bindings(tree)
    enclosing = _enclosing_functions(tree)

    sites: list[_SpawnSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        api = _resolved_target(node.func, bindings)
        if api not in SPAWN_APIS:
            continue
        keyword = next((word for word in node.keywords if word.arg == "env"), None)
        qualified = enclosing(node.lineno)
        sites.append(
            _SpawnSite(
                line=node.lineno,
                function=qualified.rsplit(".", 1)[-1],
                qualname=qualified,
                api=api,
                env=None if keyword is None else ast.unparse(keyword.value),
                sanitised=(
                    keyword is not None
                    and isinstance(keyword.value, ast.Call)
                    and _resolved_target(keyword.value.func, bindings)
                    == "_allowlisted_env"
                ),
            )
        )
    return sites


def _spawn_offenders(source: str) -> list[str]:
    """Spawn sites that are not a chokepoint building an allowlisted environment."""
    offenders = []
    for site in _spawn_sites(source):
        if site.qualname not in GIT_SPAWN_CHOKEPOINTS:
            offenders.append(
                f"{site.qualname}:{site.line} spawns a process outside a chokepoint"
            )
        elif not site.sanitised:
            offenders.append(
                f"{site.qualname}:{site.line} is a chokepoint but its env= is "
                f"{site.env!r}, not _allowlisted_env(...)"
            )
    return offenders


def _is_a_widening(node: ast.Call, target: str) -> bool:
    """Does this call add anything to the environment a subprocess will see?

    Four spellings, because a widening passed a fourth way is still a widening:

    * the named keyword, ``_git(..., env_extra=...)``;
    * :func:`_run_shell`'s third positional argument, which is how the documented-gate
      callers pass ``GIT_DIR``;
    * ``**{"env_extra": hostile}`` — a dict display, readable, and invisible to a scan
      that only looks at ``keyword.arg``;
    * ``**kw`` into a chokepoint, which cannot be read at all. A scan that cannot read
      it must not conclude it is safe, so it is reported. That is the only conservative
      answer available and it costs nothing: this module passes ``**`` to no chokepoint.

    A direct call to :func:`_allowlisted_env` with anything other than the chokepoints'
    own forwarding parameter is a widening too. Without that clause a helper nested
    inside a test could call ``subprocess.run(a, env=_allowlisted_env({"GIT_DIR": ...}))``
    and be a widening nothing enumerated.
    """
    for word in node.keywords:
        if word.arg in ENV_WIDENING_KEYWORDS:
            if not (isinstance(word.value, ast.Constant) and word.value.value is None):
                return True
        elif word.arg is None:
            if isinstance(word.value, ast.Dict):
                if any(
                    isinstance(key, ast.Constant) and key.value in ENV_WIDENING_KEYWORDS
                    for key in word.value.keys
                ):
                    return True
            elif target in GIT_SPAWN_CHOKEPOINTS or target == "_allowlisted_env":
                return True
    if target == "_run_shell" and len(node.args) >= 3:
        return True
    if target == "_allowlisted_env":
        forwarding = all(
            isinstance(argument, ast.Name) and argument.id in ENV_WIDENING_KEYWORDS
            for argument in node.args
        )
        if node.keywords or not forwarding:
            return True
    return False


def _widening_sites(source: str) -> list[str]:
    """Every scope that adds a variable to the constructed environment.

    Reported by fully qualified scope, for the same reason :func:`_spawn_sites` is: two
    classes may each define a helper called ``_arm``, and a justification list keyed by
    simple name would let the second inherit the first's reason without anybody saying
    so.
    """
    tree = ast.parse(source)
    bindings = _import_bindings(tree)
    enclosing = _enclosing_functions(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_a_widening(
            node, _resolved_target(node.func, bindings)
        ):
            found.add(enclosing(node.lineno))
    return sorted(found)


#: Tables this module deliberately holds no literal expectation over, and why. Both are
#: mutable caches: they start empty, are filled while the suite runs, and pinning a value
#: would pin a cache state rather than a property. They are named here — and the name set
#: is itself pinned — so that a real table cannot join the exemption by accident.
UNPINNED_RUNTIME_CACHES = ("_PROGRAM_CACHE", "_TREE_BLOBS")


def _module_tables(source: str) -> dict[str, int]:
    """``name -> line`` for every table this module defines.

    A *table* is an ``UPPER_CASE`` name bound to a container — a display, a
    ``frozenset``/``set``/``tuple``/``list``/``dict`` call, or a union of those — at
    module level or in a class body. Locals inside a function are not tables: they
    cannot be emptied from anywhere but the function they live in.
    """
    tree = ast.parse(source)
    tables: dict[str, int] = {}

    def container(value: ast.expr) -> bool:
        if isinstance(value, (ast.Tuple, ast.List, ast.Set, ast.Dict)):
            return True
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            return value.func.id in ("frozenset", "set", "tuple", "list", "dict")
        if isinstance(value, ast.BinOp):
            return container(value.left) or container(value.right)
        return False

    def scan(body) -> None:
        for statement in body:
            target = value = None
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target, value = statement.targets[0], statement.value
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                target, value = statement.target, statement.value
            if (
                isinstance(target, ast.Name)
                and target.id.isupper()
                and container(value)
            ):
                tables[target.id] = statement.lineno

    scan(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            scan(node.body)
    return tables


def _is_a_literal_expectation(node: ast.expr) -> bool:
    """True when ``node`` names nothing — its whole value is written in the source.

    This is the half that makes a pin a pin. ``sorted(_allowlisted_env())`` compared to
    ``sorted(GIT_ENV_ALLOWLIST)`` is not an expectation about the allowlist; it is the
    allowlist compared with itself, and emptying it satisfies both sides at once.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute):
            return False
        if isinstance(sub, ast.Name) and sub.id not in PURE_CONSTRUCTORS:
            return False
        if isinstance(sub, ast.Call) and not (
            isinstance(sub.func, ast.Name) and sub.func.id in PURE_CONSTRUCTORS
        ):
            return False
    return True


def _table_reference(node: ast.expr, tables) -> str | None:
    """The table an expression is *wholly* about, or ``None``.

    ``TABLE``, ``self.TABLE``, ``sorted(TABLE)``, ``len(TABLE)`` — nothing else. A
    projection such as ``[row[0] for row in TABLE]`` is deliberately not a pin: it can
    be true of a table with a field removed, and this test exists because partial
    agreement is what let four tables go quiet.
    """
    if isinstance(node, ast.Name):
        return node.id if node.id in tables else None
    if isinstance(node, ast.Attribute):
        return node.attr if node.attr in tables else None
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in PURE_CONSTRUCTORS:
            return None
        if node.keywords or len(node.args) != 1:
            return None
        return _table_reference(node.args[0], tables)
    return None


#: The assertions that can carry a pin. ``assertIn``/``assertTrue`` cannot: they are
#: true of a table with entries removed, which is the mutation being caught.
PINNING_ASSERTIONS = (
    "assertEqual",
    "assertCountEqual",
    "assertSetEqual",
    "assertTupleEqual",
    "assertListEqual",
    "assertDictEqual",
)


def _pinned_tables(source: str) -> dict[str, list[int]]:
    """``table -> the lines where a literal expectation pins it``.

    A pin is an equality assertion with the table (or ``sorted``/``len``/… of it) on one
    side and a literal on the other. Both orders are read, because ``assertEqual`` is
    symmetric and a reviewer should not have to remember which way round it was written.
    """
    tree = ast.parse(source)
    tables = set(_module_tables(source))
    pins: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        if (
            not isinstance(node.func, ast.Attribute)
            or node.func.attr not in PINNING_ASSERTIONS
        ):
            continue
        for observed, expected in (
            (node.args[0], node.args[1]),
            (node.args[1], node.args[0]),
        ):
            name = _table_reference(observed, tables)
            if name is not None and _is_a_literal_expectation(expected):
                pins.setdefault(name, []).append(node.lineno)
    return pins


def _unpinned_tables(source: str) -> list[str]:
    """Every table with no literal expectation anywhere, minus the named caches."""
    pinned = set(_pinned_tables(source))
    return sorted(
        name
        for name in _module_tables(source)
        if name not in pinned and name not in UNPINNED_RUNTIME_CACHES
    )


#: Every place this module widens the constructed environment, and why. The widening
#: itself is legitimate — Gate C genuinely needs the repository's object database and a
#: mutable copy has none — but it is the one way back to inheritance, so it is written
#: down rather than left to convention.
DELIBERATE_ENV_WIDENINGS: dict[str, str] = {
    "_MutableCopy.run_gate": (
        "documented Gate C reads the repository's object database and a _MutableCopy "
        "has none, so GIT_DIR names the real one on purpose (GATE_NEEDS_OBJECT_STORE)"
    ),
    "DocumentedAnalysisGateTests._assert_gate_passes": (
        "the same widening for the same gate, run from REPOSITORY_ROOT rather than "
        "from a copy"
    ),
    "AmbientGitConfigurationTests._arm": (
        "proves the hostile configuration is effective before any probe asserts it did "
        "not fire; an unarmed negative assertion measures nothing"
    ),
    "WritingCommandGuardTests.test_removing_the_environment_sanitiser_lets_the_hostile_git_dir_through.unguarded_git_write": (
        "reconstructs the pre-round-ten defect narrowly — the three discovery "
        "variables reach Git and nothing else does — so the positive probe is not "
        "passing because the redirect never worked"
    ),
    "AmbientGitConfigurationTests.test_a_global_ignore_file_cannot_change_what_a_read_enumerates": (
        "arms the injected core.excludesFile, showing it really does remove paths from "
        "the enumeration when it is let through"
    ),
    "AmbientGitConfigurationTests.test_core_hookspath_cannot_make_a_commit_run_an_attackers_hook": (
        "arms the injected core.hooksPath against this probe's own throwaway history"
    ),
    "AmbientGitConfigurationTests.test_no_ambient_form_can_reach_another_repository_through_a_writer": (
        "arms the end-to-end payload and watches the victim lose all three immutable "
        "families before asserting that no ambient form can do it"
    ),
    "ShellChokepointEnvironmentTests.test_a_gate_run_under_an_ambient_git_dir_does_not_reach_that_repository": (
        "arms the gate-level redirect through the same named widening the documented "
        "gate callers use"
    ),
}


class GitSpawnChokepointTests(unittest.TestCase):
    """**The structure, not the convention.** Every Git subprocess goes through one door.

    Round nine's blocking finding was not that a particular call was wrong. It was that
    there was no such door. An independent reviewer's AST scan found 23
    ``subprocess.run(["git", ...])`` calls in this module, 5 passing a sanitised ``env=``
    and 18 inheriting the caller's environment whole — nine of those in production
    helpers rather than test bodies: `_candidate_reviewed_paths`, `_present_reviewed_paths`,
    `_candidate_blob`, `_tree_blobs` twice, `_digest_paths`, `_freeze_commit` twice,
    `_retro_edited_digests` twice, `_reviewed_manifest_digest` and
    `_reset_to_the_frozen_tree`. The sanitiser's own docstring said it was "shared by
    every Git subprocess this module spawns, reading or writing … Neither is safe
    without this". It was shared by five of twenty-three, and nothing measured the gap.

    What existed instead was `test_both_callers_share_one_guard`, which counted the
    string ``_refuse_to_write_outside(`` inside two named writers. A writer added later
    is not one of those two, so it inherited neither the guard nor the sanitiser and no
    test noticed. That is a convention with a spot-check, and this class is what makes
    it a structure: the assertion is over *every* spawn in the file, so the nineteenth
    caller fails the suite the moment it is written.
    """

    @staticmethod
    def _own_source() -> str:
        return Path(__file__).resolve().read_text(encoding="utf-8")

    def test_the_scan_is_reading_this_modules_real_source(self) -> None:
        """Otherwise every assertion below is vacuously true over an empty string."""
        source = self._own_source()
        self.assertIn("def _allowlisted_env(", source)
        self.assertIn("class GitSpawnChokepointTests", source)
        self.assertGreaterEqual(len(_spawn_sites(source)), 2)

    def test_every_process_this_module_spawns_goes_through_a_chokepoint(self) -> None:
        self.assertEqual(_spawn_offenders(self._own_source()), [])

    def test_the_chokepoints_are_the_only_spawn_sites_and_there_are_two(self) -> None:
        """Named, so that adding a third door is a decision somebody has to make here.

        Compared on the **qualified** scope. Round ten compared the innermost function
        name, so a helper called `_git` nested inside a test body read as the chokepoint
        it was named after; the only thing that caught it was the accident that the
        sorted list then held ``_git`` twice.
        """
        self.assertEqual(
            sorted(site.qualname for site in _spawn_sites(self._own_source())),
            sorted(GIT_SPAWN_CHOKEPOINTS),
        )

    def test_the_enumeration_reports_a_git_subprocess_added_outside_the_chokepoint(
        self,
    ) -> None:
        """A probe proves only what it mutates. This mutates the thing.

        The nineteenth caller, written the way the eighteen were, applied to a source
        the scanner has never seen. If this ever passes with an empty offender list the
        enumeration above is decoration.
        """
        added = (
            "import subprocess\n"
            "def _git(*a, env_extra=None):\n"
            "    return subprocess.run(a, env=_allowlisted_env(env_extra))\n"
            "def _a_writer_added_later(root):\n"
            "    return subprocess.run(['git', '-C', root, 'rm', '--cached', 'x'],\n"
            "                          capture_output=True, check=True)\n"
        )
        self.assertEqual(
            _spawn_offenders(added),
            ["_a_writer_added_later:5 spawns a process outside a chokepoint"],
        )

    def test_the_enumeration_reports_a_chokepoint_that_stops_sanitising(self) -> None:
        """The other way the structure can rot: the door stays, the lock goes."""
        weakened = (
            "import os, subprocess\n"
            "def _git(*a):\n"
            "    return subprocess.run(a, env=dict(os.environ))\n"
        )
        self.assertEqual(
            _spawn_offenders(weakened),
            [
                "_git:3 is a chokepoint but its env= is 'dict(os.environ)', "
                "not _allowlisted_env(...)"
            ],
        )

    def test_the_enumeration_reports_a_chokepoint_that_passes_no_environment(
        self,
    ) -> None:
        silent = "import subprocess\ndef _git(*a):\n    return subprocess.run(a)\n"
        self.assertEqual(
            _spawn_offenders(silent),
            ["_git:3 is a chokepoint but its env= is None, not _allowlisted_env(...)"],
        )

    #: **The spellings round ten's enumeration walked past.** Each row is a source, and
    #: the offender the enumeration must now report for it — a literal expectation per
    #: row, so this table cannot go quiet by shrinking without the pin below saying so.
    #:
    #: The last two rows are the cap, not a gap: a name assembled at run time is not
    #: there to be read, and they carry an empty expectation on purpose.
    ALIAS_BYPASSES = (
        (
            "from subprocess import run as _spawn, in the helper it was demonstrated in",
            "from subprocess import run as _spawn\n"
            "def _reviewed_manifest_digest(root):\n"
            "    return _spawn(['git', '-C', str(root), 'rm', '--cached', 'x'])\n",
            ["_reviewed_manifest_digest:3 spawns a process outside a chokepoint"],
        ),
        (
            "import subprocess as sp",
            "import subprocess as sp\n"
            "def _a_writer_added_later(root):\n"
            "    return sp.run(['git', '-C', root, 'rm', '--cached', 'x'])\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "from subprocess import run",
            "from subprocess import run\n"
            "def _a_writer_added_later(root):\n"
            "    return run(['git', '-C', root, 'rm', '--cached', 'x'])\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "from os import system",
            "from os import system\n"
            "def _a_writer_added_later(root):\n"
            "    return system('git rm --cached x')\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "import os as _o",
            "import os as _o\n"
            "def _a_writer_added_later(root):\n"
            "    return _o.system('git rm --cached x')\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "an import inside the function body, where nobody looks for one",
            "def _a_writer_added_later(root):\n"
            "    import subprocess as q\n"
            "    return q.Popen(['git', 'rm', '--cached', 'x'])\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "os.execlp — the l-variant whose v-variant was listed",
            "import os\n"
            "def _a_writer_added_later(root):\n"
            "    return os.execlp('git', 'git', 'rm', '--cached', 'x')\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "os.spawnlp — the same omission in the other family",
            "import os\n"
            "def _a_writer_added_later(root):\n"
            "    return os.spawnlp(os.P_WAIT, 'git', 'git', 'rm')\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "pty.spawn",
            "import pty\n"
            "def _a_writer_added_later(root):\n"
            "    return pty.spawn(['git', 'rm', '--cached', 'x'])\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "asyncio.create_subprocess_exec",
            "import asyncio\n"
            "async def _a_writer_added_later(root):\n"
            "    return await asyncio.create_subprocess_exec('git', 'rm')\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "concurrent.futures.ProcessPoolExecutor — the third route round eleven's "
            "comment claimed and the list did not carry",
            "from concurrent.futures import ProcessPoolExecutor\n"
            "def _a_writer_added_later(root):\n"
            "    return ProcessPoolExecutor().submit(print, 'git')\n",
            ["_a_writer_added_later:3 spawns a process outside a chokepoint"],
        ),
        (
            "a subclass of subprocess.Popen, called by its own name — RECORDED LIMITATION",
            "import subprocess\n"
            "class _Runner(subprocess.Popen):\n"
            "    pass\n"
            "def _a_writer_added_later(root):\n"
            "    return _Runner(['git', 'rm', '--cached', 'x'])\n",
            [],
        ),
        (
            "multiprocessing.get_context('fork').Process — RECORDED LIMITATION",
            "import multiprocessing\n"
            "def _a_writer_added_later(root):\n"
            "    ctx = multiprocessing.get_context('fork')\n"
            "    return ctx.Process(target=print, args=('git',))\n",
            [],
        ),
        (
            "getattr with a computed attribute name — RECORDED LIMITATION",
            "import subprocess\n"
            "def _a_writer_added_later(root):\n"
            "    return getattr(subprocess, 'ru' + 'n')(['git', 'rm'])\n",
            [],
        ),
        (
            "eval over an assembled string — RECORDED LIMITATION",
            "def _a_writer_added_later(root):\n"
            "    return eval(\"__import__('os').sys\" + \"tem('git rm x')\")\n",
            [],
        ),
    )

    def test_the_enumeration_resolves_the_import_binding_not_the_spelling(self) -> None:
        """**The bounded repair, row by row, including the demonstrated bypass.**

        An independent reviewer put ``from subprocess import run as _spawn`` at the top
        of this module and one call to `_spawn` inside `_reviewed_manifest_digest` — a
        production helper the behavioural net does not reach — then ran the suite under
        a hostile ambient ``HOME`` with no ``GIT_*`` variable set. The victim repository
        lost all three `IMMUTABLE_REVIEWED_PREFIXES` families from its index over 60
        payload executions, the suite reported ``Ran 244 … OK``, and this enumeration
        reported ``offenders: []``.

        It reported nothing because it matched ``ast.unparse(node.func)`` against 19
        literal spellings and ``_spawn`` was not one of them — a list of names known on
        the day it was written, which is the failure mode §11.16.2 claims to have
        escaped. Resolving the import binding is what turns that list back into a list
        of *APIs*.
        """
        for label, source, expected in self.ALIAS_BYPASSES:
            with self.subTest(bypass=label):
                self.assertEqual(_spawn_offenders(source), expected)

    def test_the_bypass_table_still_carries_every_row_it_was_built_with(self) -> None:
        """A table-driven probe with an empty table runs zero subtests and reports OK.

        Eleven of the fifteen rows above are the enumeration's claim and four are its
        cap, so both the total and the split are pinned. See
        :class:`TableExpectationTests` for the property this is one instance of.

        Round twelve moved the split from 10/2 to 11/4: one route an independent
        reviewer named was a genuine gap and is now caught
        (`concurrent.futures.ProcessPoolExecutor`), and two are shapes
        :func:`_resolved_target` does not reduce, kept here as silent rows so that the
        cap is exercised rather than asserted in prose alone.
        """
        self.assertEqual(len(self.ALIAS_BYPASSES), 15)
        self.assertEqual(
            [bool(expected) for _, _, expected in self.ALIAS_BYPASSES],
            [True] * 11 + [False] * 4,
        )

    def test_dynamic_dispatch_is_a_recorded_limitation_and_says_so(self) -> None:
        """The cap, asserted as a fact of the method rather than left as a hope.

        `getattr(subprocess, 'ru' + 'n')` and `eval` reach the same call the rows above
        reach, and no static analysis resolves either: the attribute name does not exist
        until the expression runs. This test exists so that the two silent rows in
        :data:`ALIAS_BYPASSES` are silent *on purpose*, with the reasoning written down,
        rather than being two rows nobody noticed were empty.

        What the enumeration claims is bounded and stated plainly in §11.17.3: an honest
        edit is caught; an author with write access who is determined to run a
        subprocess is not. A test module does not outrank its own author.
        """
        self.assertEqual(len(UNRESOLVABLE_SPAWN_ROUTES), 7)
        for route in UNRESOLVABLE_SPAWN_ROUTES:
            with self.subTest(route=route):
                self.assertGreater(len(route), 20, "a limitation without a description")

    def test_a_chokepoints_name_cannot_be_borrowed_by_a_nested_helper(self) -> None:
        """`GIT_SPAWN_CHOKEPOINTS` names positions, not spellings.

        Round ten compared the innermost enclosing function *name*, so a helper called
        `_git` defined inside a test body satisfied the chokepoint rule by being called
        `_git`. It passed `_spawn_offenders` cleanly; the only thing that caught it was
        the accident that `test_the_chokepoints_are_the_only_spawn_sites_and_there_are_two`
        then saw ``_git`` twice in a sorted list. That is a catch by side effect and it
        disappears the moment the counterfeit is named something the real list can
        absorb.
        """
        counterfeit = (
            "import subprocess\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        def _git(*a):\n"
            "            return subprocess.run(\n"
            "                a, env=_allowlisted_env({'GIT_DIR': '/tmp/evil/.git'})\n"
            "            )\n"
            "        _git('rm', '--cached', 'x')\n"
        )
        self.assertEqual(
            _spawn_offenders(counterfeit),
            ["T.test_x._git:5 spawns a process outside a chokepoint"],
        )
        # And the widening it performs is reported too — see the next test for why the
        # keyword scan alone would not have seen it.
        self.assertEqual(_widening_sites(counterfeit), ["T.test_x._git"])

    def test_a_sanitiser_with_the_callers_environment_on_top_is_not_sanitised(
        self,
    ) -> None:
        """``env=`` is an equality on the call, not a prefix match on the text.

        Round ten's predicate was ``environment.startswith("_allowlisted_env(")``. It
        accepts ``env=_allowlisted_env() | dict(os.environ)``: the allowlist, and then
        the caller's whole environment merged over the top of it, which is precisely the
        inheritance the chokepoint exists to end.
        """
        widened = (
            "import os, subprocess\n"
            "def _git(*a):\n"
            "    return subprocess.run(a, env=_allowlisted_env() | dict(os.environ))\n"
        )
        self.assertEqual(
            _spawn_offenders(widened),
            [
                "_git:3 is a chokepoint but its env= is "
                "'_allowlisted_env() | dict(os.environ)', not _allowlisted_env(...)"
            ],
        )

    def test_the_widening_enumeration_reads_the_three_other_spellings(self) -> None:
        """A widening passed as ``**`` or straight into the sanitiser is still one.

        The keyword scan saw ``env_extra=`` and `_run_shell`'s third positional argument
        and nothing else. Three spellings walked past it: a dict display splatted into
        the call, an unreadable ``**kw`` — where the only conservative answer is to
        report it — and a direct ``_allowlisted_env({...})``, which is how a helper that
        had already borrowed a chokepoint's name would widen without naming a keyword at
        all.
        """
        cases = (
            (
                "a dict display splatted in",
                "def f(hostile):\n"
                "    return _git('-C', 'x', 'status', **{'env_extra': hostile})\n",
            ),
            (
                "keywords this scan cannot read",
                "def f(**kw):\n    return _git('-C', 'x', 'status', **kw)\n",
            ),
            (
                "the sanitiser widened directly",
                "import subprocess\n"
                "def f(hostile):\n"
                "    return subprocess.run(['git'], env=_allowlisted_env(hostile))\n",
            ),
        )
        for label, source in cases:
            with self.subTest(spelling=label):
                self.assertEqual(_widening_sites(source), ["f"])
        self.assertEqual(len(cases), 3)

    def test_the_widening_enumeration_reports_the_scope_not_the_bare_name(self) -> None:
        """Two classes may each hold an ``_arm``; a list keyed by simple name would let
        the second inherit the first's justification without anybody saying so."""
        source = (
            "class A:\n"
            "    def _arm(self, h):\n"
            "        return _git('-C', 'x', 'status', env_extra=h)\n"
            "class B:\n"
            "    def _arm(self, h):\n"
            "        return _git('-C', 'x', 'status', env_extra=h)\n"
        )
        self.assertEqual(_widening_sites(source), ["A._arm", "B._arm"])

    def test_a_helper_nested_inside_a_test_is_attributed_to_itself(self) -> None:
        """Round nine's unsanitised reconstruction lived inside a test body. An
        enumeration that attributed it to the enclosing test would have to exempt the
        test, and exempting a test exempts everything anyone later writes in it."""
        nested = (
            "import subprocess\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        def helper():\n"
            "            return subprocess.run(['git', 'status'])\n"
            "        helper()\n"
        )
        self.assertEqual([site[1] for site in _spawn_sites(nested)], ["helper"])

    def test_the_allowlist_justifies_every_variable_it_admits(self) -> None:
        """An allowlist without reasons is a denylist's twin: nobody can review it."""
        self.assertEqual(sorted(_allowlisted_env()), sorted(GIT_ENV_ALLOWLIST))
        for name, reason in GIT_ENV_ALLOWLIST.items():
            with self.subTest(variable=name):
                self.assertGreater(
                    len(reason), 30, f"{name} is admitted without a stated reason"
                )

    def test_a_variable_nobody_has_thought_of_does_not_reach_a_subprocess(self) -> None:
        """The property a denylist cannot have, stated over a name invented here.

        This is the whole difference between round nine and round ten. A denylist is
        correct for the names its author knew; the class that broke it — Git
        configuration injection — was reachable through ``HOME`` alone, a variable no
        denylist of ``GIT_*`` names would ever contain. The assertion is not "these
        particular hostile names are absent" but "nothing this module did not put there
        is present", which holds for names that do not exist yet.
        """
        invented = "W0_QA_01_A_VARIABLE_INVENTED_AFTER_THE_DENYLIST_WAS_WRITTEN"
        hostile = {
            invented: "x",
            "HOME": "/nonexistent/attacker",
            "GIT_CONFIG_PARAMETERS": "'core.fsmonitor'='/tmp/evil.sh'",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": "/tmp/evil-hooks",
            "GIT_DIR": "/tmp/evil/.git",
        }
        with unittest.mock.patch.dict(os.environ, hostile):
            self.assertEqual(sorted(_allowlisted_env()), sorted(GIT_ENV_ALLOWLIST))
            # And the same fact measured on a real child rather than on the dict.
            observed = _run_shell(
                'env | sed "s/=.*//" | sort', REPOSITORY_ROOT
            ).stdout.split()
        # bash adds a handful of its own; nothing else may appear.
        self.assertEqual(
            sorted(set(observed) - set(GIT_ENV_ALLOWLIST) - {"PWD", "SHLVL", "_", "OLDPWD"}),
            [],
            "a variable this module did not construct reached a child process",
        )
        self.assertNotIn(invented, observed)
        self.assertEqual(sorted(set(GIT_ENV_ALLOWLIST) - set(observed)), [])

    def test_the_constructed_environment_does_not_depend_on_the_callers_at_all(
        self,
    ) -> None:
        """Every **value**, not only every name — which is a different claim.

        A name-only assertion passes an environment built as
        ``{"GIT_CONFIG_GLOBAL": os.environ.get("GIT_CONFIG_GLOBAL", os.devnull), ...}``:
        the key set is right and the caller still chooses the global config file. That
        mutation survived the first version of this class with all 215 tests green,
        which is precisely the shape of defect this round exists to stop — a guard
        beside a check that cannot fail on the thing the guard names.

        Stating independence over the whole mapping covers every entry at once,
        including the ones added later, and it covers the determinism entries — an
        inherited ``LC_ALL`` changes how the digest recipes sort and how the documented
        gates decode UTF-8 contract files — which no security-shaped probe would think
        to look at.
        """
        clean = _allowlisted_env()
        poison = {name: f"hostile-value-for-{name}" for name in GIT_ENV_ALLOWLIST}
        poison.update(
            {
                "GIT_CONFIG_GLOBAL": "/tmp/attacker/.gitconfig",
                "GIT_CONFIG_SYSTEM": "/tmp/attacker/system.gitconfig",
                "GIT_CONFIG_NOSYSTEM": "0",
                "GIT_CONFIG_PARAMETERS": "'core.fsmonitor'='/tmp/evil.sh'",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": "/tmp/evil-hooks",
                "GIT_DIR": "/tmp/attacker/.git",
                "HOME": "/tmp/attacker",
                "XDG_CONFIG_HOME": "/tmp/attacker/.config",
                "LC_ALL": "tr_TR.UTF-8",
                "TZ": "Pacific/Kiritimati",
                "PATH": "/tmp/attacker/bin",
            }
        )
        with unittest.mock.patch.dict(os.environ, poison):
            under_attack = _allowlisted_env()
        self.assertEqual(
            under_attack,
            clean,
            "a value in the constructed environment came from the caller's",
        )

    def test_the_environment_neutralises_configuration_by_construction(self) -> None:
        """The named facts the allowlist is supposed to produce, asserted one by one."""
        env = _allowlisted_env()
        self.assertEqual(env["PATH"], TRUSTED_PATH)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(env["GIT_CONFIG_SYSTEM"], os.devnull)
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertNotIn("GIT_CONFIG_PARAMETERS", env)
        self.assertNotIn("GIT_CONFIG_COUNT", env)
        home = Path(env["HOME"])
        self.assertTrue(home.is_dir(), "HOME must exist or Git falls back to passwd")
        self.assertEqual(
            sorted(entry.name for entry in home.iterdir()),
            ["xdg"],
            "the neutral HOME is not empty, so a global config could live in it",
        )
        self.assertEqual(list(Path(env["XDG_CONFIG_HOME"]).iterdir()), [])
        self.assertFalse(
            home.resolve().is_relative_to(REPOSITORY_ROOT.resolve()),
            "the neutral HOME is inside the repository under review",
        )

    def test_every_deliberate_widening_is_named_and_justified_here(self) -> None:
        """``env_extra``/``env_overrides`` is the one escape hatch, so it is enumerated.

        Documented Gate C reads the repository's object database and a mutable copy has
        none, so `GIT_DIR` is supplied on purpose. That is a widening at a named call
        site, visible in the argument list. A silent second one would be the start of
        the same drift the chokepoint exists to stop, so every site is listed with its
        reason and this fails on one that is not.
        """
        sites = sorted({site for site in _widening_sites(self._own_source())})
        self.assertEqual(
            sites,
            sorted(DELIBERATE_ENV_WIDENINGS),
            "a call widened the subprocess environment without being justified in "
            "DELIBERATE_ENV_WIDENINGS",
        )
        for function, reason in DELIBERATE_ENV_WIDENINGS.items():
            with self.subTest(site=function):
                self.assertGreater(len(reason), 25, f"{function} widens without a reason")

    def test_the_widening_enumeration_reports_a_new_unjustified_site(self) -> None:
        added = (
            "def _somebody_elses_helper(root):\n"
            "    return _git('-C', root, 'status', env_extra={'GIT_DIR': '/tmp/x'})\n"
        )
        self.assertEqual(_widening_sites(added), ["_somebody_elses_helper"])

    def test_the_widening_enumeration_ignores_the_parameter_declarations(self) -> None:
        """Otherwise `_git` and `_run_shell` would report themselves forever and the
        list would carry two entries that mean nothing."""
        self.assertNotIn("_git", _widening_sites(self._own_source()))
        self.assertNotIn("_run_shell", _widening_sites(self._own_source()))


class TableExpectationTests(unittest.TestCase):
    """**Every table in this module carries a literal expectation of its own.**

    The defect class this closes, in one sentence: *a probe that iterates the same
    constant its guard reads asserts nothing when that constant is empty.* Emptying the
    table empties the loop, the loop runs zero subtests, and `unittest` reports the
    result of asserting nothing as ``OK``.

    Round ten met this once — `STATE_DOCUMENT_MUST_STILL_CONTAIN` — and pinned that one
    literal. It was live in four more places, and two independent reviewers found three
    of them by hand:

    * `RATIFICATION_REQUIRED_FIELDS = ()` — 244 green, and a `ratification` record
      carrying **no provenance at all** licensed the full five-path delta, beside a
      docstring reading "a delta authorised by a bare boolean would be an accident with
      a flag on it".
    * `ForbiddenNameSweepControlTests.ROUTES = ()` — 244 green, inside round ten's own
      repair for the same class of finding.
    * `SPAWN_APIS` cut from 19 entries to 1 — 244 green, eighteen APIs unexercised.

    Fixing three by hand would leave the fourth for the next reviewer, so the property is
    made structural instead. :func:`_module_tables` enumerates every table in this file
    from its own source, :func:`_pinned_tables` finds the literal expectations, and
    :meth:`test_every_table_this_module_defines_carries_a_literal_expectation` requires
    the second set to cover the first. A table added tomorrow with no pin fails the suite
    the day it is written, which is the same move `GitSpawnChokepointTests` makes for
    spawn sites and it reuses the same AST machinery.

    **What this class does and does not claim.** It proves a literal expectation exists
    for every table; the expectation itself is what proves the *contents*, and those are
    written out one table at a time below so a reviewer can read them against the
    definitions. A pin is deliberately narrow: an equality assertion, with the table (or
    ``sorted``/``len``/``set``/… of it) on one side and an expression naming nothing on
    the other. ``assertIn`` is not a pin and neither is comparing a table with itself —
    both stay true when entries are removed, which is the mutation being caught. Where a
    table holds values no literal can restate — `WritingCommandGuardTests.CASES` holds
    lambdas — the pin is on cardinality, which still turns emptying and shrinking red.

    Every table below has been shown red under emptying; §11.17.2 carries the table of
    24 mutations and the test each one kills.
    """

    @staticmethod
    def _own_source() -> str:
        return Path(__file__).resolve().read_text(encoding="utf-8")

    # ---- the structural property ---------------------------------------------------

    def test_the_scan_is_reading_this_modules_real_source(self) -> None:
        """Otherwise every assertion below is vacuously true over an empty string."""
        source = self._own_source()
        self.assertIn("def _module_tables(", source)
        self.assertGreaterEqual(len(_module_tables(source)), 25)

    def test_every_table_this_module_defines_carries_a_literal_expectation(self) -> None:
        self.assertEqual(
            _unpinned_tables(self._own_source()),
            [],
            "a table in this module can be emptied without turning a test red",
        )

    def test_the_table_census_is_the_one_this_class_reviewed(self) -> None:
        """Naming them, so adding a table is a decision somebody has to make here.

        Without this the structural test above is satisfiable by deleting a table as
        well as by pinning it, and a reviewer reading the class has no list to check the
        pins against.
        """
        self.assertEqual(
            sorted(_module_tables(self._own_source())),
            [
                "ACCEPTANCE_DIGEST_FIELDS",
                "ALIAS_BYPASSES",
                "CASES",
                "CHECKPOINT_DELIVERABLES",
                "CHECKPOINT_DELIVERABLE_PATHS",
                "COMPLETED_TASK_FILES",
                "DELIBERATE_ENV_WIDENINGS",
                # A pinned table, not a cache: it is a fixed list of the keys a
                # `CHECKPOINT_DELIVERABLES` entry may state a requirement in, read by
                # `_checkpoint_bundle_problems` and pinned whole beside that table in
                # `test_the_checkpoint_bundle_table_is_pinned_whole`. The cache
                # exemption is for names filled while the suite runs, and this one is
                # never written after definition, so it does not qualify for it and is
                # not given it.
                "DELIVERABLE_REQUIREMENT_KEYS",
                "ENV_WIDENING_KEYWORDS",
                "FORBIDDEN_AUTHORITY_KEYS",
                "FORBIDDEN_VERSION_KEYS",
                "GATE_MARKERS",
                "GATE_NEEDS_OBJECT_STORE",
                "GIT_ENV_ALLOWLIST",
                "GIT_SPAWN_CHOKEPOINTS",
                "IDENTITY",
                "IMMUTABLE_REVIEWED_PREFIXES",
                "MANUAL_VERDICTS",
                "NOT_COPIED",
                "PINNING_ASSERTIONS",
                "POST_FREEZE_DELTA_CEILING",
                "PUBLICATION_DOCUMENT_PATHS",
                "PURE_CONSTRUCTORS",
                "RATIFICATION_DELTA_CEILING",
                "RATIFICATION_PUBLICATION_RECORDS",
                "RATIFICATION_REQUIRED_FIELDS",
                "RECONCILIATIONS",
                "REGISTRY_STATE_TOKENS",
                "REVIEWED_PREFIXES",
                "ROUTES",
                "SPAWN_APIS",
                "STATE_DOCUMENT_MUST_STILL_CONTAIN",
                "UNPINNED_RUNTIME_CACHES",
                "UNRESOLVABLE_SPAWN_ROUTES",
                "_PROGRAM_CACHE",
                "_TREE_BLOBS",
            ],
        )

    def test_the_two_unpinned_names_are_runtime_caches_and_start_empty(self) -> None:
        """The only exemption, and the reason it is safe.

        A cache is filled while the suite runs, so a pinned value would pin a moment
        rather than a property. Both are asserted to be exactly that: empty at
        definition, and mutable mappings rather than tables of expectations.
        """
        self.assertEqual(UNPINNED_RUNTIME_CACHES, ("_PROGRAM_CACHE", "_TREE_BLOBS"))
        source = self._own_source()
        for name in UNPINNED_RUNTIME_CACHES:
            with self.subTest(cache=name):
                self.assertIn(f"{name}: dict[", source)
                self.assertIn("= {}", source.split(f"{name}: dict[")[1].split("\n")[0])

    # ---- negative controls: the scan has to be able to report something -------------

    def test_the_scan_reports_a_table_added_without_a_pin(self) -> None:
        """A probe proves only what it mutates. This mutates the thing."""
        added = (
            "SOMETHING_NEW = ('a', 'b')\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        for item in SOMETHING_NEW:\n"
            "            self.assertIn(item, 'ab')\n"
        )
        self.assertEqual(_unpinned_tables(added), ["SOMETHING_NEW"])

    def test_a_table_compared_with_itself_is_not_a_pin(self) -> None:
        """The exact shape that let `GIT_ENV_ALLOWLIST` look measured for two rounds.

        ``assertEqual(sorted(_allowlisted_env()), sorted(GIT_ENV_ALLOWLIST))`` is a real
        and useful assertion — it is how the constructed environment is held to its
        justification list — but it is not an expectation *about* the list. Empty the
        list and `_allowlisted_env` raises instead; empty both and the assertion holds.
        """
        self_referential = (
            "TABLE = ('a', 'b')\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        self.assertEqual(sorted(TABLE), sorted(TABLE))\n"
            "        self.assertIn('a', TABLE)\n"
            "        self.assertTrue(TABLE)\n"
        )
        self.assertEqual(_unpinned_tables(self_referential), ["TABLE"])

    def test_a_projection_of_a_table_is_not_a_pin(self) -> None:
        """One column agreeing does not pin the rows.

        This is `RECONCILIATIONS` exactly: every `path` could be right while
        `sentence_requires` was weakened from three tokens to one, which is the mutation
        that survived round ten green.
        """
        projected = (
            "TABLE = ({'path': 'a', 'needs': ('x', 'y')},)\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        self.assertEqual([row['path'] for row in TABLE], ['a'])\n"
        )
        self.assertEqual(_unpinned_tables(projected), ["TABLE"])
        # And the whole-value form of the same table is a pin.
        pinned = projected.replace(
            "self.assertEqual([row['path'] for row in TABLE], ['a'])",
            "self.assertEqual(TABLE, ({'path': 'a', 'needs': ('x', 'y')},))",
        )
        self.assertEqual(_unpinned_tables(pinned), [])

    def test_both_argument_orders_count_and_a_cardinality_pin_counts(self) -> None:
        """``assertEqual`` is symmetric, and ``len(TABLE)`` is the weakest pin allowed."""
        reversed_order = (
            "TABLE = ('a',)\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        self.assertEqual(('a',), TABLE)\n"
        )
        self.assertEqual(_unpinned_tables(reversed_order), [])
        cardinality = (
            "TABLE = ('a',)\n"
            "class T:\n"
            "    def test_x(self):\n"
            "        self.assertEqual(len(TABLE), 1)\n"
        )
        self.assertEqual(_unpinned_tables(cardinality), [])

    def test_the_pin_scan_finds_a_class_attribute_table(self) -> None:
        """`ROUTES` and `CASES` live in class bodies; a module-level-only scan would
        report them pinned by never seeing them at all."""
        in_a_class = (
            "class T:\n"
            "    ROUTES = ('a', 'b')\n"
            "    def test_x(self):\n"
            "        for route in self.ROUTES:\n"
            "            self.assertIn(route, 'ab')\n"
        )
        self.assertEqual(_unpinned_tables(in_a_class), ["ROUTES"])

    # ---- the pins themselves, one table at a time -----------------------------------
    #
    # Written out rather than derived. A pin that computed its expectation from the
    # table would be the defect it exists to catch.

    def test_the_reviewed_family_prefixes_are_pinned(self) -> None:
        self.assertEqual(
            REVIEWED_PREFIXES,
            ("contracts/", "fixtures/", "docs/architecture/", "scripts/"),
        )
        self.assertEqual(
            IMMUTABLE_REVIEWED_PREFIXES, ("contracts/", "fixtures/", "scripts/")
        )

    def test_the_registry_state_vocabulary_is_closed_at_two_tokens(self) -> None:
        """**A non-blocking survivor from round ten, closed.**

        `REGISTRY_STATE_TOKENS` admitted a third token with the suite green, so the
        "closed and machine-readable" property its docstring claims was unmeasured. The
        vocabulary is the whole point of the constant: `_registry_state_problem`
        compares the registry row against it, and a vocabulary that admits a new word is
        not closed.
        """
        self.assertEqual(
            sorted(REGISTRY_STATE_TOKENS), ["ratification", "ratification_blocked"]
        )

    def test_the_two_ratification_ceilings_are_pinned(self) -> None:
        self.assertEqual(
            sorted(RATIFICATION_DELTA_CEILING),
            [
                "docs/architecture/ADR_INDEX.md",
                "docs/architecture/ARCHITECTURE_LINT_RULES.md",
                "docs/architecture/CP00_ARCHITECTURE_REVIEW.json",
                "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
                "docs/architecture/CP00_OWNER_DECISIONS.md",
            ],
        )
        self.assertEqual(
            sorted(POST_FREEZE_DELTA_CEILING),
            [
                "artifacts/checkpoints/CP-00/acceptance.md",
                "artifacts/checkpoints/CP-00/automated-summary.txt",
                "artifacts/checkpoints/CP-00/build-info.json",
                "artifacts/checkpoints/CP-00/checkpoint-report.md",
                "artifacts/checkpoints/CP-00/contract-manifest.yaml",
                "artifacts/checkpoints/CP-00/known-risks.md",
                "artifacts/checkpoints/CP-00/manifest.json",
                "artifacts/checkpoints/CP-00/manual-test-report.md",
                "artifacts/checkpoints/CP-00/migration-head.txt",
                "artifacts/checkpoints/CP-00/restore-or-rollback-note.md",
                "docs/INDEX.md",
                "docs/architecture/ADR_INDEX.md",
                "docs/architecture/ARCHITECTURE_LINT_RULES.md",
                "docs/architecture/CP00_ARCHITECTURE_REVIEW.json",
                "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
                "docs/architecture/CP00_OWNER_DECISIONS.md",
                "docs/program/CHECKPOINT_REGISTRY.md",
                "docs/program/CURRENT_STATE.md",
                "docs/program/tasks/W0-ANA-01.md",
                "docs/program/tasks/W0-ARC-01.md",
                "docs/program/tasks/W0-ARC-02.md",
                "docs/program/tasks/W0-BHV-01.md",
                "docs/program/tasks/W0-BHV-02.md",
                "docs/program/tasks/W0-CLN-01.md",
                "docs/program/tasks/W0-DEP-01.md",
                "docs/program/tasks/W0-DOM-01.md",
                "docs/program/tasks/W0-DOM-02.md",
                "docs/program/tasks/W0-EVD-01.md",
                "docs/program/tasks/W0-EVT-01.md",
                "docs/program/tasks/W0-INT-00.md",
                "docs/program/tasks/W0-INT-01.md",
                "docs/program/tasks/W0-QA-00.md",
                "docs/program/tasks/W0-QA-01.md",
                "docs/program/tasks/W0-QA-02.md",
                "docs/program/tasks/W0-QA-03.md",
                "docs/program/waves/W0.3_ratification_integration.md",
                "docs/stages/S00_architecture_and_behavior_freeze.md",
            ],
            "the post-freeze licence is not the set this class reviewed",
        )

    def test_the_acceptance_digest_fields_are_pinned(self) -> None:
        self.assertEqual(
            ACCEPTANCE_DIGEST_FIELDS,
            ("tested_candidate_digest", "evidence_bundle_digest"),
        )

    def test_the_state_document_deletion_guard_is_pinned(self) -> None:
        self.assertEqual(
            STATE_DOCUMENT_MUST_STILL_CONTAIN, ("# Current state", "CP-00")
        )

    def test_the_ratification_provenance_fields_are_pinned(self) -> None:
        """`RATIFICATION_REQUIRED_FIELDS = ()` left 244 tests green and licensed a
        five-path delta from a record carrying nothing but a boolean."""
        self.assertEqual(
            RATIFICATION_REQUIRED_FIELDS,
            ("task", "decided_on", "decided_by", "reason"),
        )

    def test_the_reconciliation_table_is_pinned_whole(self) -> None:
        """Whole, not by projection.

        `RECONCILIATIONS[1]["sentence_requires"]` weakened from ``("62", "31",
        "satisfied")`` to ``("satisfied",)`` left 244 green: the live code names both
        `PD-02` documents, and the only probe for the evidence sentence drove entry 0.
        Emptying the field outright *is* caught; the weakening was not, and a pin over
        `path` alone would not have caught it either.
        """
        self.assertEqual(
            RECONCILIATIONS,
            (
                {
                    "item": "PD-02 acceptance precondition, CP-00 architecture review",
                    "path": "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
                    "stale": "so the acceptance precondition is not yet met",
                    "sentence_requires": ("62", "31", "satisfied"),
                    "requires_note": (
                        "a sentence recording the precondition as satisfied, with the "
                        "62 legacy names and 31 alias-bearing sites that show it"
                    ),
                },
                {
                    "item": "PD-02 acceptance precondition, owner decision ledger",
                    "path": "docs/architecture/CP00_OWNER_DECISIONS.md",
                    "stale": "so the precondition is not yet met",
                    "sentence_requires": ("62", "31", "satisfied"),
                    "requires_note": (
                        "a sentence recording the precondition as satisfied, with the "
                        "62 legacy names and 31 alias-bearing sites that show it"
                    ),
                },
                {
                    "item": "stale GATE-E probe prose",
                    "path": "docs/architecture/ARCHITECTURE_LINT_RULES.md",
                    "stale": "still untracked",
                    "removal_only": True,
                    "must_still_contain": ("GATE-E",),
                    "requires_note": (
                        "the GATE-E probe description with the untracked claim "
                        "removed; the probe itself must still be documented"
                    ),
                },
                {
                    "item": "owner-decision count in the ADR index",
                    "path": "docs/architecture/ADR_INDEX.md",
                    "stale": "`PD-01`\u2013`PD-04`",
                    "new_text": ("`PD-01`\u2013`PD-05`",),
                    "requires_note": "the decision range widened to `PD-01`-`PD-05`",
                },
            ),
        )

    def test_the_checkpoint_tag_and_manual_vocabulary_are_pinned(self) -> None:
        """Pinned here, anchored where an anchor exists.

        The tag is compared with the checkpoint manifest's own `tag_planned`: the
        manifest is a document the integrator writes, so it cannot be the *source* of
        the value, but a disagreement between the two is a re-tag nobody declared and is
        reported as one. The verdict vocabulary has no external anchor — it is the
        vocabulary `W0-INT-01` deliverable 3 names — so it is pinned and said to be.
        """
        self.assertEqual(CHECKPOINT_TAG, "v0.0.0-architecture")
        self.assertEqual(MANUAL_VERDICTS, ("PASS", "FAIL", "BLOCKED"))
        self.assertEqual(MANUAL_RUNBOOK, "docs/manual-tests/CP-00_architecture.md")
        self.assertEqual(
            _load(CHECKPOINT_MANIFEST).get("tag_planned"),
            CHECKPOINT_TAG,
            "the checkpoint record plans a different tag from the one this module "
            "requires the evidence bundle to name",
        )
        self.assertTrue(
            (REPOSITORY_ROOT / MANUAL_RUNBOOK).is_file(),
            "the manual runbook this module reads its case list out of is not there",
        )

    def test_the_checkpoint_bundle_table_is_pinned_whole(self) -> None:
        """Whole, not by projection: the names **and** what each one must say.

        A pin over `name` alone would be satisfied by a table whose every content
        requirement had been deleted, which is the licence granted with nothing paid
        for it — the exact defect this round exists to repair.
        """
        self.assertEqual(
            CHECKPOINT_DELIVERABLES,
            ({'name': 'checkpoint-report.md',
              'values': ('candidate_commit', 'contract_version', 'checkpoint_tag'),
              'requires': ('CP-00',
                           'contract-manifest.yaml',
                           'manual-test-report.md',
                           'known-risks.md',
                           'restore-or-rollback-note.md'),
              'manifest_names': ('integrated_w03_tasks',),
              'note': 'the integration report S00 requires: the frozen contract '
                      'version and candidate commit, the tag, every merged task ID, '
                      'and references to the manual report, the known risks and the '
                      'rollback note'},
             {'name': 'contract-manifest.yaml',
              'values': ('candidate_commit',
                         'contract_version',
                         'reviewed_manifest_digest'),
              'requires': ('migration_head: none',),
              'hashes': ('contracts/analysis/v1/stage-registry.json',
                         'contracts/analysis/v1/legacy-stage-name-map.json',
                         'fixtures/golden/selection.json',
                         'requirements/validation.in',
                         'requirements/validation.lock'),
              'note': 'W0-INT-01 deliverable 2 in full: exact file hashes, contract '
                      'versions, candidate commit, dependency-lock hashes, '
                      'migration_head: none, the golden selection hash and the '
                      'analysis registry/name-map hashes. Every value is recomputed '
                      'from the repository, so a manifest describing another tree is a '
                      'failure and not a difference of opinion'},
             {'name': 'automated-summary.txt',
              'values': ('current_round',),
              'requires': ('PASS',),
              'note': "the automated stream's summary for the round being ratified. "
                      'Cross-record only: the manifest already has to say PASS for '
                      'that round, so this catches a summary from another round or one '
                      'that contradicts the record it summarises, not an independently '
                      'verified test result'},
             {'name': 'manual-test-report.md',
              'manual_cases': True,
              'note': 'W0-INT-01 deliverable 3: tester identity, timestamps and a '
                      'verdict per case for every MT00 case the runbook defines. The '
                      'case list is read out of the runbook and the runtime '
                      'disposition out of the manifest; the tester name and the '
                      'timestamp are shape only, because no repository value can say '
                      'who ran a manual test or when'},
             {'name': 'migration-head.txt',
              'exact': 'none',
              'note': "the migration head W0-INT-01's frozen inputs record: none. The "
                      'whole file, not a needle in it'},
             {'name': 'build-info.json',
              'json_object': True,
              'values': ('candidate_commit',),
              'note': 'a non-empty JSON object naming the commit it describes. Nothing '
                      'else about this file is stated in any repository document, so '
                      'nothing else is required: the object shape is shape, and is '
                      'recorded as such'},
             {'name': 'known-risks.md',
              'manifest_names': ('architecture_defer',
                                 'open_inputs_carried_forward',
                                 'open_escalations'),
              'note': 'every risk the checkpoint record already carries has to appear '
                      'in the risk note: the deferred ADR, the four carried-forward '
                      'open inputs and the open escalations. A published bundle that '
                      'silently drops one is the failure this catches'},
             {'name': 'restore-or-rollback-note.md',
              'values': ('checkpoint_tag', 'candidate_commit'),
              'note': "what to roll back and what to roll back to. W0-INT-01's "
                      'rollback section states no further content, and none is '
                      'invented here'}),
        )
        self.assertEqual(
            sorted(CHECKPOINT_DELIVERABLE_PATHS),
            ['artifacts/checkpoints/CP-00/automated-summary.txt',
             'artifacts/checkpoints/CP-00/build-info.json',
             'artifacts/checkpoints/CP-00/checkpoint-report.md',
             'artifacts/checkpoints/CP-00/contract-manifest.yaml',
             'artifacts/checkpoints/CP-00/known-risks.md',
             'artifacts/checkpoints/CP-00/manual-test-report.md',
             'artifacts/checkpoints/CP-00/migration-head.txt',
             'artifacts/checkpoints/CP-00/restore-or-rollback-note.md'],
        )
        # The keys an entry may state a requirement in. Emptying this list would make
        # "declares no content requirement" unsatisfiable and the guard that reports it
        # unreachable, which is the emptying defect wearing the costume of a guard.
        self.assertEqual(
            DELIVERABLE_REQUIREMENT_KEYS,
            (
                "requires",
                "values",
                "hashes",
                "manifest_names",
                "exact",
                "json_object",
                "manual_cases",
            ),
        )

    def test_the_publication_record_table_is_pinned_whole(self) -> None:
        self.assertEqual(
            RATIFICATION_PUBLICATION_RECORDS,
            ({'item': 'W0.3 wave plan',
              'path': 'docs/program/waves/W0.3_ratification_integration.md',
              'denials': ('`W0-INT-01` is blocked', '| `W0-INT-01` | blocked |'),
              'requires': ('S01',),
              'must_still_contain': ('`v0.0.0-architecture`', '`W0-INT-01`'),
              'requires_note': 'the next unlocked S01 preparation tasks deliverable 5 '
                               "names, with the wave's own status line and task row no "
                               'longer calling W0-INT-01 blocked'},
             {'item': 'S00 stage checklist',
              'path': 'docs/stages/S00_architecture_and_behavior_freeze.md',
              'denials': (),
              'checklist': True,
              'requires': ('S01',),
              'must_still_contain': ('Automated exit evidence',
                                     'Manual local acceptance'),
              'requires_note': 'the next unlocked S01 preparation tasks, and every '
                               'automated and manual exit-criterion box ticked: a '
                               'checkpoint cannot be ratified while its own stage '
                               'checklist still says its exit evidence is outstanding'},
             {'item': 'documentation index status column',
              'path': 'docs/INDEX.md',
              'row': 'program/tasks/W0-INT-01.md',
              'denials': ('blocked',),
              'requires': ('accepted and integrated',),
              'must_still_contain': ('# Documentation index', '## Architecture',
                                     '## Program'),
              'requires_note': 'the status column this index already uses for every '
                               'other completed task, on the one row that still says '
                               'the ratifying task is blocked'}),
        )
        self.assertEqual(
            sorted(PUBLICATION_DOCUMENT_PATHS),
            ['docs/INDEX.md',
             'docs/program/waves/W0.3_ratification_integration.md',
             'docs/stages/S00_architecture_and_behavior_freeze.md'],
        )

    def test_the_completed_task_files_are_pinned_and_are_the_candidate_set(self) -> None:
        """Pinned, and anchored to the immutable candidate rather than to a directory.

        `git ls-tree` at the reviewed candidate is an independent enumeration: the pin
        below could name a file that never existed, or miss one, and this comparison
        says so. It is deliberately **not** a listing of `docs/program/tasks/` in the
        working tree — a licence computed from a directory is a licence anyone who can
        add a file to that directory can widen, which is the property
        :data:`RATIFICATION_DELTA_CEILING` is pinned to avoid.
        """
        self.assertEqual(
            sorted(COMPLETED_TASK_FILES),
            ['docs/program/tasks/W0-ANA-01.md',
             'docs/program/tasks/W0-ARC-01.md',
             'docs/program/tasks/W0-ARC-02.md',
             'docs/program/tasks/W0-BHV-01.md',
             'docs/program/tasks/W0-BHV-02.md',
             'docs/program/tasks/W0-CLN-01.md',
             'docs/program/tasks/W0-DEP-01.md',
             'docs/program/tasks/W0-DOM-01.md',
             'docs/program/tasks/W0-DOM-02.md',
             'docs/program/tasks/W0-EVD-01.md',
             'docs/program/tasks/W0-EVT-01.md',
             'docs/program/tasks/W0-INT-00.md',
             'docs/program/tasks/W0-INT-01.md',
             'docs/program/tasks/W0-QA-00.md',
             'docs/program/tasks/W0-QA-01.md',
             'docs/program/tasks/W0-QA-02.md',
             'docs/program/tasks/W0-QA-03.md'],
        )
        self.assertEqual(RATIFYING_TASK_FILE, "docs/program/tasks/W0-INT-01.md")
        self.assertEqual(
            RATIFYING_TASK_BANNER_DENIAL, "ratification and publication blocked"
        )
        self.assertIn(RATIFYING_TASK_FILE, COMPLETED_TASK_FILES)
        listing = _git(
            "-C", str(REPOSITORY_ROOT), "--no-replace-objects", "ls-tree", "-r",
            "--name-only", REVIEWED_CANDIDATE_COMMIT, "--", "docs/program/tasks",
            text=True, check=True,
        ).stdout
        self.assertEqual(
            sorted(COMPLETED_TASK_FILES),
            sorted(path for path in listing.split("\n") if path),
            "the licensed task files are not the task files the reviewed candidate has",
        )

    def test_the_gate_tables_are_pinned(self) -> None:
        self.assertEqual(
            GATE_MARKERS,
            {
                "A": "name-map gate PASS",
                "B": "evidence gate PASS",
                "C": "reviewer gate PASS",
                "D": "decision-transfer gate PASS",
            },
        )
        self.assertEqual(sorted(GATE_NEEDS_OBJECT_STORE), ["C"])

    def test_the_environment_allowlist_names_are_pinned(self) -> None:
        """The names, written out. The reasons are held to a length by
        :meth:`GitSpawnChokepointTests.test_the_allowlist_justifies_every_variable_it_admits`,
        and to their effect by the two independence probes beside it."""
        self.assertEqual(
            sorted(GIT_ENV_ALLOWLIST),
            [
                "GIT_CONFIG_GLOBAL",
                "GIT_CONFIG_NOSYSTEM",
                "GIT_CONFIG_SYSTEM",
                "GIT_TERMINAL_PROMPT",
                "HOME",
                "LANG",
                "LC_ALL",
                "PATH",
                "TZ",
                "XDG_CONFIG_HOME",
            ],
        )

    def test_the_spawn_enumeration_tables_are_pinned(self) -> None:
        """`SPAWN_APIS` cut from 19 entries to one left 244 tests green.

        Nothing iterated it — `_spawn_sites` tests membership — so no subtest count
        moved; the eighteen missing entries were simply never asked about. This is the
        same defect shape as an emptied loop table and it is caught the same way.
        """
        self.assertEqual(GIT_SPAWN_CHOKEPOINTS, ("_git", "_run_shell"))
        self.assertEqual(ENV_WIDENING_KEYWORDS, ("env_extra", "env_overrides"))
        self.assertEqual(
            sorted(SPAWN_APIS),
            [
                "asyncio.create_subprocess_exec",
                "asyncio.create_subprocess_shell",
                "asyncio.subprocess.create_subprocess_exec",
                "asyncio.subprocess.create_subprocess_shell",
                "concurrent.futures.ProcessPoolExecutor",
                "multiprocessing.Pool",
                "multiprocessing.Process",
                "os.execl",
                "os.execle",
                "os.execlp",
                "os.execlpe",
                "os.execv",
                "os.execve",
                "os.execvp",
                "os.execvpe",
                "os.fork",
                "os.forkpty",
                "os.popen",
                "os.posix_spawn",
                "os.posix_spawnp",
                "os.spawnl",
                "os.spawnle",
                "os.spawnlp",
                "os.spawnlpe",
                "os.spawnv",
                "os.spawnve",
                "os.spawnvp",
                "os.spawnvpe",
                "os.system",
                "pty.fork",
                "pty.spawn",
                "subprocess.Popen",
                "subprocess.call",
                "subprocess.check_call",
                "subprocess.check_output",
                "subprocess.getoutput",
                "subprocess.getstatusoutput",
                "subprocess.run",
            ],
        )

    def test_the_deliberate_widenings_are_pinned_by_scope(self) -> None:
        """The justification list, by qualified scope. Held to the *actual* widening
        sites by
        :meth:`GitSpawnChokepointTests.test_every_deliberate_widening_is_named_and_justified_here`
        — which is the comparison that fails on a new site, and this is the one that
        fails when both sides are emptied together."""
        self.assertEqual(
            sorted(DELIBERATE_ENV_WIDENINGS),
            [
                "AmbientGitConfigurationTests._arm",
                "AmbientGitConfigurationTests."
                "test_a_global_ignore_file_cannot_change_what_a_read_enumerates",
                "AmbientGitConfigurationTests."
                "test_core_hookspath_cannot_make_a_commit_run_an_attackers_hook",
                "AmbientGitConfigurationTests."
                "test_no_ambient_form_can_reach_another_repository_through_a_writer",
                "DocumentedAnalysisGateTests._assert_gate_passes",
                "ShellChokepointEnvironmentTests."
                "test_a_gate_run_under_an_ambient_git_dir_does_not_reach_that_repository",
                "WritingCommandGuardTests."
                "test_removing_the_environment_sanitiser_lets_the_hostile_git_dir_through"
                ".unguarded_git_write",
                "_MutableCopy.run_gate",
            ],
        )

    def test_the_scans_own_vocabularies_are_pinned(self) -> None:
        """The tables the pin scan itself reads. Emptying `PINNING_ASSERTIONS` would
        make every pin invisible and report every table unpinned — loud, not silent —
        but emptying `PURE_CONSTRUCTORS` narrows what counts as a literal in the quiet
        direction, so both are written out."""
        self.assertEqual(
            PINNING_ASSERTIONS,
            (
                "assertEqual",
                "assertCountEqual",
                "assertSetEqual",
                "assertTupleEqual",
                "assertListEqual",
                "assertDictEqual",
            ),
        )
        self.assertEqual(
            sorted(PURE_CONSTRUCTORS),
            ["dict", "frozenset", "len", "list", "set", "sorted", "tuple"],
        )

    def test_the_sandbox_and_probe_fixtures_are_pinned(self) -> None:
        self.assertEqual(sorted(_CheckpointSandbox.NOT_COPIED), [".git", ".venv"])
        self.assertEqual(
            SandboxResetTests.IDENTITY,
            (
                "-c",
                "user.email=w0-qa-01@example.invalid",
                "-c",
                "user.name=W0-QA-01 reset probe",
            ),
        )

    def test_the_write_refusal_case_table_is_pinned(self) -> None:
        """Cardinality, because the rows carry lambdas and no literal restates one.

        The reasons themselves are restated, which is the part that can go wrong
        quietly: a case removed from this table takes its branch's only probe with it,
        and that is exactly what an independent reviewer of round eight did — removing a
        branch and staying green because a surviving branch caught the same input with a
        different message.
        """
        self.assertEqual(len(WritingCommandGuardTests.CASES), 4)
        self.assertEqual(
            [reason for reason, _factory in WritingCommandGuardTests.CASES],
            [
                "it is the repository under review",
                "it contains the repository under review",
                "it is inside the repository under review",
                "it is not a throwaway directory this module created",
            ],
        )

    def test_the_forbidden_name_sweep_routes_are_pinned(self) -> None:
        """`ROUTES = ()` left 244 green — inside round ten's own repair for this class.

        Six routes, and the two the `properties` branch reaches are marked: a name
        declared as a `properties` member is *also* an object key, so those two rows
        cannot isolate the branch they name. See
        :meth:`ForbiddenNameSweepControlTests.test_each_route_helper_reaches_its_own_route`.
        """
        self.assertEqual(
            ForbiddenNameSweepControlTests.ROUTES,
            (
                "an object key at depth inside a list",
                "an object key at depth inside nested objects",
                "a properties member",
                "a properties member reached through a list",
                "a required entry",
                "a required entry reached through a list",
            ),
        )


class TrustedProgramResolutionTests(unittest.TestCase):
    """``$PATH`` shadowing of ``git`` itself, and what this module can and cannot do.

    A reviewer put an executable named ``git`` earlier on the inherited ``PATH`` and
    routed all 28 of this module's invocations through it with the suite reporting
    ``OK``. Two independent things close that here: the program is resolved to an
    absolute path from :data:`TRUSTED_PATH` alone, and the ``PATH`` handed to the child
    is :data:`TRUSTED_PATH`, so what Git itself spawns is covered too.

    The limitation is recorded in §11.15.4 rather than asserted away: an attacker who
    can write into ``/usr/bin`` has already won, and nothing a test module does outranks
    that.
    """

    def _shadow(self) -> tuple[Path, Path]:
        shadow = Path(tempfile.mkdtemp(prefix="w0-qa-01-shadow-path-"))
        self.addCleanup(shutil.rmtree, shadow, True)
        marker = shadow / "fired"
        program = shadow / "git"
        program.write_text(
            f'#!/bin/sh\nprintf "fired\\n" >> "{marker}"\nexit 0\n', encoding="utf-8"
        )
        program.chmod(0o755)
        return shadow, marker

    def test_a_shadowed_git_on_the_callers_path_is_not_the_git_that_runs(self) -> None:
        shadow, marker = self._shadow()
        cached = dict(_PROGRAM_CACHE)
        self.addCleanup(lambda: (_PROGRAM_CACHE.clear(), _PROGRAM_CACHE.update(cached)))
        with unittest.mock.patch.dict(
            os.environ, {"PATH": f"{shadow}{os.pathsep}{os.environ.get('PATH', '')}"}
        ):
            # Armed: a naive resolution would take the attacker's program.
            self.assertEqual(
                shutil.which("git"),
                str(shadow / "git"),
                "the shadow is not first on PATH, so this probe measures nothing",
            )
            _PROGRAM_CACHE.clear()
            resolved = _program("git")
            version = _git("--version", text=True, check=True).stdout
        self.assertFalse(
            marker.exists(), "the module ran the git it was handed by the caller"
        )
        self.assertTrue(version.startswith("git version"), version)
        self.assertTrue(Path(resolved).is_absolute())
        self.assertIn(str(Path(resolved).parent), TRUSTED_PATH.split(os.pathsep))

    def test_what_git_itself_spawns_gets_the_trusted_path_too(self) -> None:
        """The half an absolute program name does not cover: hooks, ``git-`` helpers,
        ``core.fsmonitor`` and clean/smudge filters are resolved by Git, on the ``PATH``
        Git is given."""
        shadow, _marker = self._shadow()
        with unittest.mock.patch.dict(
            os.environ, {"PATH": f"{shadow}{os.pathsep}{os.environ.get('PATH', '')}"}
        ):
            seen = _run_shell('printf "%s" "$PATH"', REPOSITORY_ROOT).stdout
        self.assertEqual(seen, TRUSTED_PATH)

    def test_both_programs_resolve_and_are_absolute(self) -> None:
        for name in ("git", "bash"):
            with self.subTest(program=name):
                self.assertTrue(Path(_program(name)).is_absolute())
                self.assertTrue(os.access(_program(name), os.X_OK))


class AmbientGitConfigurationTests(unittest.TestCase):
    """**Round ten's blocking class: Git configuration injection.**

    Round nine removed three repository-*discovery* variables from an inherited
    environment. An independent reviewer confirmed that list complete for its class and
    then walked around it: injected Git *configuration* is strictly more powerful,
    because a configured value such as `core.fsmonitor` is **executed as a command**.
    With no ``GIT_*`` variable set at all — only a ``HOME`` whose ``.gitconfig`` names
    `core.fsmonitor` — the reviewer took `contracts/README.md`, `fixtures/f.json` and
    `scripts/s.py` out of another repository's index, all three
    `IMMUTABLE_REVIEWED_PREFIXES` families, while this suite reported ``OK``, all 189
    tests stayed green and `_refuse_to_write_outside` passed cleanly. Against a
    disposable stand-in for the repository under review the same vector took 214 tracked
    files to 147 and 67 immutable-family files to 0.

    It is inside the module's own stated threat model, not next to it. §11.15.1 names
    the motivating scenario as "a post-commit hook, ``git rebase`` or ``git bisect
    run``", and what a post-commit hook's child actually inherits is::

        GIT_CONFIG_PARAMETERS='core.fsmonitor'='/tmp/evil.sh' 'user.email'='a@b' ...
        GIT_INDEX_FILE=.git/index

    ``git -c K=V`` propagates to every child as `GIT_CONFIG_PARAMETERS`. Round nine
    stripped `GIT_INDEX_FILE` from that line and left the other. And `core.fsmonitor` is
    an ordinary setting real developers configure: under it,
    :class:`WritingCommandGuardTests` alone executed the ambient hook 16 times per run,
    including inside the test asserting the victim was intact.

    Every probe below is armed first — the same configuration is shown to fire when it
    is deliberately let through — and only then asserted absent. An assertion that a
    marker file does not exist is worth nothing until the marker has been made to
    exist.
    """

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="w0-qa-01-hostile-home-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.marker = self.home / "fired"
        self.payload = self.home / "payload.sh"
        self.payload.write_text(
            f'#!/bin/sh\nprintf "fired\\n" >> "{self.marker}"\nprintf ""\n',
            encoding="utf-8",
        )
        self.payload.chmod(0o755)
        self.hooks = self.home / "hooks"
        self.hooks.mkdir()
        for hook in ("pre-commit", "post-commit"):
            script = self.hooks / hook
            script.write_text(
                f'#!/bin/sh\nprintf "fired\\n" >> "{self.marker}"\n', encoding="utf-8"
            )
            script.chmod(0o755)
        #: A global ignore file can only hide paths that are *untracked* — which is
        #: exactly the interesting case here, because this task's own report and every
        #: deliverable in flight are untracked, and `_digest_paths` enumerates them.
        self.untracked = "w0-qa-01-probe-untracked.json"
        self.ignore = self.home / "global-ignore"
        self.ignore.write_text(self.untracked + "\n", encoding="utf-8")
        self.gitconfig = self.home / ".gitconfig"
        self.gitconfig.write_text(
            "[core]\n"
            f"\tfsmonitor = {self.payload}\n"
            f"\thooksPath = {self.hooks}\n"
            f"\texcludesFile = {self.ignore}\n",
            encoding="utf-8",
        )

    #: What a caller's environment looks like when the vector is present. No ``GIT_*``
    #: variable at all in the first form — that is the point of it.
    def _ambient(self, form: str) -> dict[str, str]:
        if form == "home":
            return {"HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home)}
        if form == "parameters":
            return {
                "GIT_CONFIG_PARAMETERS": (
                    f"'core.fsmonitor'='{self.payload}' "
                    f"'core.hooksPath'='{self.hooks}' "
                    f"'core.excludesFile'='{self.ignore}' "
                    "'user.email'='a@b' 'user.name'='a'"
                )
            }
        if form == "global":
            # Neither HOME nor GIT_CONFIG_PARAMETERS: the caller simply names the file.
            # This is the form that the neutral HOME alone does not stop, and the
            # reason GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM are pinned at os.devnull
            # rather than left to follow HOME.
            return {
                "GIT_CONFIG_GLOBAL": str(self.gitconfig),
                "GIT_CONFIG_SYSTEM": str(self.gitconfig),
                "GIT_CONFIG_NOSYSTEM": "0",
            }
        if form == "count":
            return {
                "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_0": "core.fsmonitor",
                "GIT_CONFIG_VALUE_0": str(self.payload),
                "GIT_CONFIG_KEY_1": "core.hooksPath",
                "GIT_CONFIG_VALUE_1": str(self.hooks),
                "GIT_CONFIG_KEY_2": "core.excludesFile",
                "GIT_CONFIG_VALUE_2": str(self.ignore),
            }
        raise AssertionError(form)

    #: The same configuration, deliberately let through :func:`_git`'s named widening,
    #: to prove the payload is armed before anything asserts it did not fire. ``HOME``
    #: alone is enough in the wild; here `GIT_CONFIG_GLOBAL` is named too because the
    #: allowlist pins it at ``os.devnull`` and both names point at the same file.
    def _let_through(self) -> dict[str, str]:
        return {"HOME": str(self.home), "GIT_CONFIG_GLOBAL": str(self.gitconfig)}

    def _arm(self, root: Path) -> None:
        self.marker.unlink(missing_ok=True)
        _git("-C", str(root), "status", "--porcelain", env_extra=self._let_through())
        self.assertTrue(
            self.marker.is_file(),
            "the hostile configuration did not run even when it was deliberately let "
            "through, so every assertion below would pass for the wrong reason",
        )
        self.marker.unlink()

    def _victim(self) -> Path:
        victim = Path(tempfile.mkdtemp(prefix="w0-qa-01-victim-"))
        self.addCleanup(shutil.rmtree, victim, True)
        for family in ("contracts", "fixtures", "scripts"):
            (victim / family).mkdir()
            (victim / family / "seed.txt").write_text("victim\n", encoding="utf-8")
        identity = ("-c", "user.email=v@example.invalid", "-c", "user.name=v")
        _git("-C", str(victim), "init", "--quiet", check=True)
        _git("-C", str(victim), *identity, "add", "-A", check=True)
        _git("-C", str(victim), *identity, "commit", "--quiet", "-m", "seed", check=True)
        return victim

    @staticmethod
    def _tracked(root: Path) -> set[str]:
        return {
            line
            for line in _git("-C", str(root), "ls-files", text=True, check=True)
            .stdout.split("\n")
            if line
        }

    def test_a_global_gitconfig_alone_cannot_make_a_writer_run_anything(self) -> None:
        """The reviewer's exact vector: a ``HOME``, and no ``GIT_*`` variable at all."""
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self._arm(sandbox.root)

        with unittest.mock.patch.dict(os.environ, self._ambient("home")):
            sandbox._git_write("rm", "--cached", "--", "contracts/README.md")

        self.assertFalse(
            self.marker.exists(),
            "an ambient ~/.gitconfig made a writing Git command execute a script",
        )
        self.assertNotIn(
            "contracts/README.md",
            self._tracked(sandbox.root),
            "the sandbox's own write did not take effect, so this proves nothing",
        )

    def test_a_global_gitconfig_alone_cannot_make_a_reader_run_anything(self) -> None:
        """18 of round nine's 23 call sites were reads, and a read spawns Git too.

        `_present_reviewed_paths` runs ``ls-files --cached --others``, which refreshes
        the index and therefore consults `core.fsmonitor`. Nine of those eighteen were
        production helpers; this is the class of them.
        """
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self._arm(sandbox.root)

        with unittest.mock.patch.dict(os.environ, self._ambient("home")):
            present = _present_reviewed_paths(sandbox.root)
            digest_paths = _digest_paths(sandbox.root)
            candidate = _candidate_reviewed_paths(sandbox.root)
            blobs = _tree_blobs(sandbox.root, REVIEWED_CANDIDATE_COMMIT)

        self.assertFalse(self.marker.exists(), "an ambient ~/.gitconfig ran on a read")
        self.assertIn("contracts/analysis/v1/README.md", present)
        self.assertIn("contracts/analysis/v1/README.md", digest_paths)
        self.assertIn("contracts/analysis/v1/README.md", candidate)
        self.assertIsNotNone(blobs)

    def test_a_global_ignore_file_cannot_change_what_a_read_enumerates(self) -> None:
        """Configuration injection corrupts *answers*, not only writes.

        `core.excludesFile` is read by ``--exclude-standard``, which every path-set
        recipe in this module uses, and it hides *untracked* paths — which is the
        interesting half, because a deliverable in flight is untracked and
        `_digest_paths` is what enumerates it. An ambient global ignore naming one makes
        `_digest_paths` under-report, which makes the recomputed manifest digest wrong,
        which makes this module certify agreement it never checked. No script runs and
        nothing is written: a silently wrong ``ACCEPT`` is the whole of the damage, and
        it is the reason the eighteen unsanitised *reads* mattered as much as the five
        writes.
        """
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        (sandbox.root / self.untracked).write_text("{}\n", encoding="utf-8")

        honest = _digest_paths(sandbox.root)
        self.assertIn(self.untracked, honest)

        # Armed: let the same ignore file through and the path disappears from the
        # recipe's own enumeration.
        excluded = {
            line
            for line in _git(
                "-C",
                str(sandbox.root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                text=True,
                check=True,
                env_extra=self._let_through(),
            ).stdout.split("\n")
            if line
        }
        self.assertNotIn(
            self.untracked,
            excluded,
            "the global ignore file hid nothing, so this probe measures nothing",
        )

        for form in ("home", "global", "parameters", "count"):
            with self.subTest(form=form):
                with unittest.mock.patch.dict(os.environ, self._ambient(form)):
                    self.assertEqual(
                        _digest_paths(sandbox.root),
                        honest,
                        "an ambient global ignore file changed the path set this "
                        "module digests",
                    )

    def test_naming_the_global_config_file_outright_cannot_inject_configuration(
        self,
    ) -> None:
        """`GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` name the file directly.

        An empty ``HOME`` does not stop this one — Git reads the file it is told to
        read — which is why the allowlist pins both at ``os.devnull`` instead of
        letting them follow ``HOME``. Without this probe that pinning was decoration:
        replacing it with ``os.environ.get("GIT_CONFIG_GLOBAL", os.devnull)`` left all
        215 tests green.
        """
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self._arm(sandbox.root)
        with unittest.mock.patch.dict(os.environ, self._ambient("global")):
            sandbox._git_write("rm", "--cached", "--", "contracts/README.md")
            _present_reviewed_paths(sandbox.root)
            _digest_paths(sandbox.root)
        self.assertFalse(
            self.marker.exists(),
            "an ambient GIT_CONFIG_GLOBAL made Git execute a configured command",
        )
        self.assertNotIn("contracts/README.md", self._tracked(sandbox.root))

    def test_git_config_parameters_cannot_inject_configuration(self) -> None:
        """The line a post-commit hook's child actually inherits.

        ``git -c K=V`` propagates to every child as `GIT_CONFIG_PARAMETERS`. The same
        benign invocation §11.15.1 names as the motivating scenario delivers this.
        """
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self._arm(sandbox.root)
        with unittest.mock.patch.dict(os.environ, self._ambient("parameters")):
            sandbox._git_write("rm", "--cached", "--", "contracts/README.md")
            _present_reviewed_paths(sandbox.root)
        self.assertFalse(self.marker.exists())
        self.assertNotIn("contracts/README.md", self._tracked(sandbox.root))

    def test_git_config_count_key_and_value_cannot_inject_configuration(self) -> None:
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self._arm(sandbox.root)
        with unittest.mock.patch.dict(os.environ, self._ambient("count")):
            sandbox._git_write("rm", "--cached", "--", "contracts/README.md")
            _present_reviewed_paths(sandbox.root)
        self.assertFalse(self.marker.exists())
        self.assertNotIn("contracts/README.md", self._tracked(sandbox.root))

    def test_core_hookspath_cannot_make_a_commit_run_an_attackers_hook(self) -> None:
        """`_ManifestHistory.commit()` runs ``git commit``, which runs ``pre-commit``
        and ``post-commit`` from `core.hooksPath`. An injected `core.hooksPath` made it
        run the attacker's copies of both."""
        history = _ManifestHistory()
        self.addCleanup(history.close)

        # Armed, against this history's own repository, before anything is asserted.
        self.marker.unlink(missing_ok=True)
        _git(
            "-C",
            str(history.root),
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "arming",
            env_extra=self._let_through(),
        )
        self.assertTrue(
            self.marker.is_file(),
            "the injected hooksPath did not run when it was let through, so the "
            "assertions below would pass for the wrong reason",
        )
        self.marker.unlink()

        for form in ("home", "global", "parameters", "count"):
            with self.subTest(form=form):
                head_before = history.head()
                with unittest.mock.patch.dict(os.environ, self._ambient(form)):
                    # A distinct file per form: `commit` has nothing to do on an
                    # unchanged tree, and a commit that never ran would run no hook.
                    history.commit(
                        f"probe-{form}",
                        _history_manifest(None),
                        {f"probe-{form}.txt": form},
                    )
                self.assertFalse(
                    self.marker.exists(),
                    "an ambient core.hooksPath ran on commit",
                )
                self.assertNotEqual(
                    history.head(),
                    head_before,
                    "the commit did not happen, so no hook could have run either and "
                    "this iteration proves nothing",
                )

    def test_no_ambient_form_can_reach_another_repository_through_a_writer(
        self,
    ) -> None:
        """The end-to-end shape of the reviewer's finding, asserted on the bytes.

        Three families seeded in a throwaway victim — the `IMMUTABLE_REVIEWED_PREFIXES`
        families the reviewer emptied — and a payload whose job would be to empty them.
        The assertion is the victim's index, not a caught exception: round nine's
        blocker was precisely a guard that raised on the right input while the write
        went somewhere else.
        """
        victim = self._victim()
        before = self._tracked(victim)
        self.assertEqual(len(before), 3, before)

        emptier = self.home / "empty-the-victim.sh"
        emptier.write_text(
            "#!/bin/sh\n"
            f'printf "fired\\n" >> "{self.marker}"\n'
            "env -u HOME -u XDG_CONFIG_HOME -u GIT_CONFIG_GLOBAL "
            "-u GIT_CONFIG_PARAMETERS -u GIT_CONFIG_COUNT -u GIT_DIR -u GIT_WORK_TREE "
            f'-u GIT_INDEX_FILE "{_program("git")}" -c core.fsmonitor= '
            f'--git-dir="{victim}/.git" --work-tree="{victim}" '
            "rm -q --cached -r -- contracts fixtures scripts >/dev/null 2>&1\n"
            'printf ""\n',
            encoding="utf-8",
        )
        emptier.chmod(0o755)
        self.gitconfig.write_text(
            f"[core]\n\tfsmonitor = {emptier}\n\thooksPath = {self.hooks}\n",
            encoding="utf-8",
        )

        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)

        # Armed: let it through once and watch the victim lose all three families.
        _git("-C", str(sandbox.root), "status", "--porcelain",
             env_extra=self._let_through())
        self.assertEqual(
            self._tracked(victim),
            set(),
            "the payload did not empty the victim when it was let through, so this "
            "probe is not a reconstruction of the finding",
        )
        _git("-C", str(victim), "reset", "--quiet", "--hard", check=True)
        self.assertEqual(self._tracked(victim), before)

        for form in ("home", "global", "parameters", "count"):
            with self.subTest(form=form):
                self.marker.unlink(missing_ok=True)
                # A distinct path per form, so every iteration is a write that really
                # changes the sandbox index rather than a no-op that proves nothing.
                staged = f"probe-{form}.txt"
                (sandbox.root / staged).write_text(form + "\n", encoding="utf-8")
                with unittest.mock.patch.dict(os.environ, self._ambient(form)):
                    sandbox._git_write("add", "--", staged)
                    _present_reviewed_paths(sandbox.root)
                    _digest_paths(sandbox.root)
                self.assertIn(
                    staged,
                    self._tracked(sandbox.root),
                    "the sandbox's own write did not take effect, so this iteration "
                    "proves nothing about redirection",
                )
                self.assertEqual(
                    self._tracked(victim),
                    before,
                    "another repository lost tracked files while this suite was green",
                )
                self.assertFalse(self.marker.exists())


class ShellChokepointEnvironmentTests(unittest.TestCase):
    """F2: :func:`_run_shell` sanitised, and nothing measured that it did.

    Replacing `_run_shell`'s ``env = _sanitised_git_env()`` with ``dict(os.environ)``
    left all 189 tests green — the line was load-bearing and simply untested, which is
    the same shape of defect as a guarantee written in prose beside a check that cannot
    fail. A documented gate is a shell script and several of them run ``git``, so an
    unsanitised gate hands Git the caller's environment one level down, where none of
    the probes above are looking.
    """

    def test_a_gate_never_sees_the_callers_git_environment(self) -> None:
        hostile = {
            "GIT_DIR": "/tmp/w0-qa-01-not-a-repository/.git",
            "GIT_WORK_TREE": "/tmp/w0-qa-01-not-a-repository",
            "GIT_INDEX_FILE": "/tmp/w0-qa-01-not-a-repository/.git/index",
            "GIT_CONFIG_PARAMETERS": "'core.fsmonitor'='/tmp/evil.sh'",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": "/tmp/evil-hooks",
            "HOME": "/tmp/w0-qa-01-attacker-home",
        }
        script = "".join(
            f'printf \'{name}=%s\\n\' "${{{name}-unset}}"\n'
            for name in (*hostile, "PATH", "GIT_CONFIG_GLOBAL")
        )
        with unittest.mock.patch.dict(os.environ, hostile):
            result = _run_shell(script, REPOSITORY_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        reported = dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )
        for name in hostile:
            if name == "HOME":
                continue
            with self.subTest(variable=name):
                self.assertEqual(
                    reported[name],
                    "unset",
                    f"a documented gate was handed the caller's {name}",
                )
        self.assertNotEqual(reported["HOME"], hostile["HOME"])
        self.assertEqual(reported["HOME"], _allowlisted_env()["HOME"])
        self.assertEqual(reported["PATH"], TRUSTED_PATH)
        self.assertEqual(reported["GIT_CONFIG_GLOBAL"], os.devnull)

    def test_a_gate_run_under_an_ambient_git_dir_does_not_reach_that_repository(
        self,
    ) -> None:
        """The behavioural half. A `_MutableCopy` has no repository of its own, so a
        gate run inside one either finds nothing or finds whatever the environment
        names — which is the entire question."""
        victim = Path(tempfile.mkdtemp(prefix="w0-qa-01-gate-victim-"))
        self.addCleanup(shutil.rmtree, victim, True)
        _git("-C", str(victim), "init", "--quiet", check=True)

        copy = _MutableCopy()
        self.addCleanup(copy.close)
        script = 'git rev-parse --absolute-git-dir 2>&1 || true\n'

        # Armed: named on purpose through the one widening, the gate does reach it.
        reached = _run_shell(script, copy.root, {"GIT_DIR": str(victim / ".git")})
        self.assertIn(
            str(victim.resolve()),
            reached.stdout,
            "the ambient GIT_DIR is not reachable from a gate even when it is passed "
            "deliberately, so the assertion below would pass for the wrong reason",
        )

        with unittest.mock.patch.dict(os.environ, {"GIT_DIR": str(victim / ".git")}):
            blocked = _run_shell(script, copy.root)
        self.assertNotIn(
            str(victim.resolve()),
            blocked.stdout,
            "a documented gate resolved to the repository the caller's environment "
            "named",
        )

    def test_the_documented_gate_that_needs_the_object_database_still_gets_it(
        self,
    ) -> None:
        """The positive direction, so the class above is not passing by breaking Gate C.

        `GATE_NEEDS_OBJECT_STORE` exists because Gate C reads the repository's object
        database and a mutable copy has none. If the widening ever stopped working this
        class would still be green and the gate silently unrunnable.
        """
        self.assertIn("C", GATE_NEEDS_OBJECT_STORE)
        copy = _MutableCopy()
        self.addCleanup(copy.close)
        result = copy.run_gate("C")
        self.assertEqual(result.returncode, 0, result.stderr.strip())
        self.assertIn("reviewer gate PASS", result.stdout)


class SelfReferentialAnchorTests(unittest.TestCase):
    """Constants the harness writes and the check then reads, given something to hold on to.

    An independent reviewer found four of these: `UNRATIFIED_REVIEW_STATUS`,
    `REVIEW_DISCLAIMER`, `RATIFIED_STATE_TOKEN` and `_CheckpointSandbox.PREFIX` can each
    be set to any value at all and the suite stays green, because the only thing that
    ever writes the value is the probe that later looks for it. `RECONCILIATIONS`'
    `stale` field has the anchor-rot guard these lack — it is required to be *present*
    in the candidate document before it is required to be gone — and that is the pattern
    applied here wherever there is an external document to anchor to.

    Where there is not, the constant is **pinned to its literal value** instead, so
    changing it is a decision somebody makes in this file rather than a silent one. That
    is weaker than an anchor and is not described as anything else.

    **Round twelve: an anchor pinned to the unratified state is an anchor that dies at
    ratification.** Three of the probes below asserted the *unratified* reading and
    nothing else — the denial present, the registry citing `ratification_blocked`, the
    manifest carrying no `ratification` object. Each of those is exactly what
    ratification is required to change, so on a tree that had been honestly published
    the anchors and the checks they anchor demanded opposite things and the suite went
    red: four failures on a clean, correctly ratified tree, reproduced end to end in
    `docs/program/reviews/W0-QA-01.md` §11.18.

    They are now **two-directional**, the shape :func:`_state_document_problems` already
    had: each asserts the unratified reading while the manifest says `ratified: false`
    and the ratified reading once it says `true`. Neither state is exempt and neither
    branch is a skip, so there is no tree on which one of these probes stops asserting
    anything — which is the property, not a convenience: a guard switched off on the
    published tree is the defect class this task has been reopened over, wearing the
    costume of a fix.

    One constant is better off for it. :data:`RATIFIED_STATE_TOKEN` had nothing to
    anchor to while CP-00 was unratified and was pinned, with the limitation recorded.
    On a ratified tree there *is* something — the manifest's `ratification` object and
    the registry row that cites it — so the ratified half is a real anchor and the pin
    is kept only for the state in which no anchor can exist.
    """

    @staticmethod
    def _live_ratified() -> bool:
        """Which direction the live external record puts these anchors in.

        Read from the manifest rather than passed in, because the question these probes
        ask is about *this* repository's documents, and the answer has to move when the
        repository does.
        """
        return _load(CHECKPOINT_MANIFEST).get("ratified") is True

    def test_the_review_disclaimer_is_in_the_candidate_review(self) -> None:
        """Anchored: the sentence the ratified half requires to be *gone* must be there
        now, or the check passes forever without proving anything."""
        blob = _candidate_blob(REPOSITORY_ROOT, REVIEW_MARKDOWN)
        self.assertIsNotNone(blob, f"{REVIEW_MARKDOWN} is unreadable at the candidate")
        self.assertIn(
            REVIEW_DISCLAIMER,
            _flat(blob.decode("utf-8")),
            f"anchor rot: {REVIEW_MARKDOWN} no longer carries {REVIEW_DISCLAIMER!r}, so "
            "requiring a ratification to remove it proves nothing. Re-anchor it here.",
        )

    def test_the_unratified_review_status_is_the_candidate_status(self) -> None:
        """Anchored: the pre-ratification status is read out of the candidate, not
        asserted about a value this module also writes."""
        blob = _candidate_blob(REPOSITORY_ROOT, REVIEW_JSON)
        self.assertIsNotNone(blob)
        self.assertEqual(
            json.loads(blob.decode("utf-8")).get("review_status"),
            UNRATIFIED_REVIEW_STATUS,
            f"anchor rot: {REVIEW_JSON} no longer declares "
            f"{UNRATIFIED_REVIEW_STATUS!r} at the reviewed candidate",
        )

    def test_the_live_registry_cites_the_state_token_for_the_live_state(self) -> None:
        """Anchored in both directions: whichever token names the live state is the one
        the registry cites, and is a key the manifest actually carries.

        `_registry_state_problem` reads a code span out of the CP-00 registry row, and
        that row is a document this task does not write — so the anchor is real. What it
        was not, until round twelve, is *durable*: it asserted `ratification_blocked`
        unconditionally, and `_registry_state_problem` requires the row to move to
        `ratification` at the ratification act. The anchor demanded the row stay exactly
        where the check demanded it move, so the first honest publication turned it red.

        The manifest-key half is the part that keeps this from being a pin. A token is
        only a state *name* if some record carries it; asserting it against the registry
        alone would compare two strings this module chose.
        """
        ratified = self._live_ratified()
        token = RATIFIED_STATE_TOKEN if ratified else UNRATIFIED_STATE_TOKEN
        self.assertIn(
            f"`{token}`",
            _read(CHECKPOINT_REGISTRY),
            f"anchor rot: {CHECKPOINT_REGISTRY} no longer cites `{token}` while "
            f"{CHECKPOINT_MANIFEST} declares ratified={ratified}. That code span is what "
            "_registry_state_problem reads; with it gone the comparison has nothing to "
            "read and this anchor must be re-placed here.",
        )
        self.assertIn(
            token,
            _load(CHECKPOINT_MANIFEST),
            f"{token!r} is not a key the manifest carries, so the registry cites a "
            "state key that does not exist",
        )

    def test_the_state_document_says_what_the_live_state_requires(self) -> None:
        """The same two directions :func:`_state_document_problems` reads, asserted here
        directly so the anchor is visible next to the others.

        Round eleven's form asserted only that the denial was present, which is the
        unratified reading and nothing else. `_state_document_problems` *requires* that
        sentence to be gone once `ratified: true`, so this probe and that function asked
        for opposite things the moment CP-00 was ratified.

        Direct on the document, not delegated to `_state_document_problems`: a probe
        that calls the function it is supposed to anchor states nothing the function
        does not already state about itself.
        """
        document = _flat(_read(PROGRAM_STATE_DOCUMENT))
        if not self._live_ratified():
            self.assertIn(
                STATE_DOCUMENT_DENIAL,
                document,
                f"anchor rot: {PROGRAM_STATE_DOCUMENT} no longer carries "
                f"{STATE_DOCUMENT_DENIAL!r} while CP-00 is unratified. That sentence is "
                "what the ratified half requires to be removed; with it already gone, "
                "the removal proves nothing. Re-anchor it here.",
            )
            return
        self.assertNotIn(
            STATE_DOCUMENT_DENIAL,
            document,
            f"{PROGRAM_STATE_DOCUMENT} still says {STATE_DOCUMENT_DENIAL!r} while "
            f"{CHECKPOINT_MANIFEST} declares ratified=true",
        )
        for needle in STATE_DOCUMENT_MUST_STILL_CONTAIN:
            with self.subTest(needle=needle):
                self.assertIn(
                    needle,
                    document,
                    "the denial must be removed by bringing the state document up to "
                    "date, not by gutting it",
                )

    def test_the_ratified_state_token_is_pinned_until_the_manifest_carries_it(
        self,
    ) -> None:
        """Pinned while there is nothing to anchor to; anchored the moment there is.

        `ratification` is the manifest key `W0-INT-01` writes and the registry cites *at*
        ratification. While CP-00 is unratified no document carries it, so there is
        nothing to anchor to and an anchor asserted against a document this module also
        writes would be the vacuity it is meant to prevent — the literal pin is the
        honest answer, and §11.16 records it as weaker than an anchor.

        Round eleven's form stopped there, and its own failure message said what was
        missing: "the manifest now carries a `ratification` object, so this constant can
        and should be anchored to it rather than pinned". That message fired as a
        *failure* on a ratified tree — the probe was written to go red on exactly the
        tree the checkpoint is published on. It now takes its own advice: on a ratified
        tree the constant must name a key the manifest really carries, and that key must
        hold the record `_ratification_record` reads rather than any value at all.

        The unratified branch is not a skip. A manifest declaring `ratified: false`
        while carrying a `ratification` object is a record contradicting itself, and
        saying so is the assertion that direction owes.
        """
        self.assertEqual(RATIFIED_STATE_TOKEN, "ratification")
        self.assertEqual(UNRATIFIED_STATE_TOKEN, "ratification_blocked")
        manifest = _load(CHECKPOINT_MANIFEST)
        if not self._live_ratified():
            self.assertNotIn(
                RATIFIED_STATE_TOKEN,
                manifest,
                f"{CHECKPOINT_MANIFEST} declares ratified=false and carries a "
                f"`{RATIFIED_STATE_TOKEN}` object anyway; a record that pre-authorises "
                "the act it has not taken is the defect _ratification_record exists for",
            )
            return
        self.assertIn(
            RATIFIED_STATE_TOKEN,
            manifest,
            f"{CHECKPOINT_MANIFEST} declares ratified=true and carries no "
            f"`{RATIFIED_STATE_TOKEN}` object, so this constant names no key of the "
            "record it is supposed to name",
        )
        record = manifest[RATIFIED_STATE_TOKEN]
        self.assertIsInstance(
            record, dict, f"`{RATIFIED_STATE_TOKEN}` is not the ratification record"
        )
        for field in RATIFICATION_REQUIRED_FIELDS:
            with self.subTest(field=field):
                self.assertIn(
                    field,
                    record,
                    f"the key `{RATIFIED_STATE_TOKEN}` names does not carry {field!r}, "
                    "so it is some other object that happens to share the name",
                )

    def test_the_sandbox_prefix_is_self_defined_and_actually_used(self) -> None:
        """`_CheckpointSandbox.PREFIX` has nothing external to anchor to — it is this
        module's own `mkdtemp` prefix, invented here and meaningful nowhere else. What
        *can* be required is that the value the guard checks is the value the sandbox is
        actually created with, which is what makes `_refuse_to_write_outside`'s prefix
        branch reachable at all."""
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        self.assertTrue(sandbox.root.name.startswith(_CheckpointSandbox.PREFIX))
        self.assertTrue(_ManifestHistory.PREFIX != _CheckpointSandbox.PREFIX)
        self.assertIsNone(
            _refuse_to_write_outside(sandbox.root, _CheckpointSandbox.PREFIX)
        )
        with self.assertRaises(AssertionError):
            _refuse_to_write_outside(sandbox.root, _ManifestHistory.PREFIX)

    def test_the_reviewed_artifact_count_is_computed_and_not_a_constant(self) -> None:
        """`artifact_count` is 100, and so was the mutant.

        `_reviewed_manifest_digest` returning a hardcoded ``100`` instead of
        ``len(tracked)`` left the suite green, because the only probe compared it with
        the manifest's own declared value — which is also 100. The count is now checked
        against an independently produced path set: `_tree_blobs` reads `HEAD` through
        different Git plumbing (``ls-tree -r -z`` plus ``cat-file --batch``) than the
        ``ls-tree -r --name-only`` the digest uses, so agreement is a real second
        opinion rather than the same number twice.
        """
        digest, count = _reviewed_manifest_digest(REPOSITORY_ROOT)
        blobs = _tree_blobs(REPOSITORY_ROOT, "HEAD")
        self.assertIsNotNone(blobs)
        independent = sorted(
            path for path in blobs if path.startswith(REVIEWED_PREFIXES)
        )
        self.assertEqual(
            count,
            len(independent),
            "the reviewed-artifact count does not match an independent enumeration of "
            "the same trees",
        )
        self.assertGreater(count, 1, "an empty count would satisfy any comparison")
        self.assertEqual(_load(CHECKPOINT_MANIFEST)["artifact_count"], count)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

        # A second tree, with a *different* number of reviewed files. Without this the
        # hardcode is an equivalent mutant: `artifact_count` is 100, the independent
        # enumeration is 100, and `return running.hexdigest(), 100` agrees with both.
        # One data point cannot distinguish a computation from the constant it happens
        # to produce, and that is the whole reason this check was decorative.
        history = _ManifestHistory()
        self.addCleanup(history.close)
        planted = {
            "contracts/planted/one.json": "{}\n",
            "fixtures/planted/two.json": "{}\n",
            "docs/architecture/planted-three.md": "three\n",
            "scripts/planted_four.py": "pass\n",
            "docs/program/not-a-reviewed-family.md": "ignored\n",
        }
        history.commit("a tree with four reviewed files", _history_manifest(None), planted)
        _elsewhere, elsewhere_count = _reviewed_manifest_digest(history.root)
        self.assertEqual(
            elsewhere_count,
            4,
            "the reviewed-artifact count is not counting; it reports the same number "
            "for a tree with four reviewed files as for one with a hundred",
        )
        self.assertNotEqual(elsewhere_count, count)


class FreezeCommitHistoryTests(unittest.TestCase):
    """`_freeze_commit` on real commits, where the freeze commit is **not** `HEAD`.

    Round eight's independent review killed 16 of 17 mutations. The survivor was
    `_freeze_commit`'s ``freeze = commit`` replaced by ``return commit`` — "the newest
    commit carrying the value" instead of the oldest consecutive one — which left all 159
    tests green. The property is load-bearing, and nothing tested it: every probe in this
    module ran where the two answers coincide, because the live repository froze at
    `HEAD` and the sandboxes never commit.

    Every probe below therefore asserts that the freeze commit is not `HEAD` before it
    asserts anything else. A history where it is would prove exactly as little as the
    159 tests that missed this did.
    """

    def setUp(self) -> None:
        self.history = _ManifestHistory()
        self.addCleanup(self.history.close)

    def test_a_publication_committed_after_the_freeze_is_not_a_retro_edit(self) -> None:
        """The published checkpoint must not be permanently red, and still be guarded.

        **The failure.** `_retro_edited_digests` walked from `HEAD`, so once the
        integrator committed the publication, every later re-derivation of it compared
        its own freshly computed `evidence_bundle_digest` against the committed one. Those
        two can never be equal -- the value is computed over the tree that carries the
        results, and no re-derivation reproduces the integrator's tree byte for byte -- so
        the comparison read a legitimate re-derivation as a retro-edit. Every sandbox in
        this module is such a re-derivation, which made
        `test_the_checkpoint_mechanism_has_a_reachable_published_state` fail on any
        published tree, with the message that the checkpoint has no executable final
        state. The probe written to answer round nine's void would have failed the moment
        the void was answered.

        **Both directions, on real commits.** The publication commit is a *descendant* of
        the freeze, so scoping the walk to the freeze excludes it -- and excludes nothing
        else, because every closed round's sealed digest is an ancestor. The control
        proves that: round nine's digest is sealed at the freeze commit, and editing it
        is still named.
        """
        frozen, published, rederived = "a" * 64, "b" * 64, "c" * 64
        nine = "e" * 64

        def document(evidence: str, ninth: str = nine) -> dict:
            return {
                "checkpoint": "CP-00",
                "ratified": False,
                "current_round": 10,
                "tested_candidate_digest": frozen,
                "evidence_bundle_digest": evidence,
                "acceptance_rounds": [
                    {
                        "round": 9,
                        "verdict": "FAIL",
                        "tested_candidate_digest": ninth,
                        "evidence_bundle_digest": "",
                    },
                    {
                        "round": 10,
                        "verdict": None,
                        "tested_candidate_digest": frozen,
                        "evidence_bundle_digest": evidence,
                    },
                ],
            }

        freeze = self.history.commit("freeze round ten", document(""))
        publication = self.history.commit("publish CP-00", document(published))
        self.assertNotEqual(
            freeze,
            publication,
            "the publication must be a separate, later commit or this probe is not "
            "about a publication committed after the freeze",
        )
        self.assertEqual(
            _freeze_commit(self.history.root),
            freeze,
            "the freeze no longer resolves, so the scoping under test is not reached",
        )

        # A re-derivation of the same publication, over its own tree.
        self.history.write(document(rederived))
        self.assertEqual(
            _retro_edited_digests(self.history.root),
            [],
            "a re-derived evidence digest was read as a retro-edit, so a published "
            "CP-00 is permanently red and the mechanism has no final state",
        )

        # The control: a value the freeze commit itself carries, edited. Still named.
        self.history.write(document(rederived, ninth="f" * 64))
        problems = _retro_edited_digests(self.history.root)
        self.assertTrue(
            any("round 9" in problem and "tested_candidate_digest" in problem
                for problem in problems),
            f"scoping the walk to the freeze stopped it catching a real retro-edit of a "
            f"digest the freeze commit carries: {problems}",
        )

    def test_the_walk_is_scoped_to_the_round_the_manifest_names(self) -> None:
        """Round scoping is only ever exercised at round 5, which is not exercising it.

        The live manifest is round 5 and `_history_manifest` defaults to round 5, so
        `number = manifest.get("current_round")` replaced by `number = 5` survives every
        other probe in the module — in `_freeze_commit` and in
        `_declared_evidence_paths` alike. A history at a different round is the only
        thing that separates "reads current_round" from "happens to be 5", and this is
        it: rounds 8 and 9, with a round-5 entry deliberately present in the same
        manifest so the pinned mutant has something wrong to find.
        """
        shape = {"number": 9, "rounds": (5, 8, 9)}
        self.history.commit("open round 9", _history_manifest(None, **shape))
        digest = self.history.seal(**shape)
        freeze = self.history.commit("freeze round 9", _history_manifest(digest, **shape))
        results = self.history.commit(
            "record the round-9 acceptance results",
            _history_manifest(digest, verdict="PASS", **shape),
            {"artifacts/checkpoints/CP-00/manual-report-round-9.md": "PASS\n"},
        )

        self.assertNotEqual(freeze, results, "the freeze must not be HEAD here either")
        self.assertEqual(
            _freeze_commit(self.history.root),
            freeze,
            "the freeze walk did not resolve on a manifest whose current_round is not 5",
        )
        self.assertEqual(
            _acceptance_digest_at(
                self.history.root, freeze, "tested_candidate_digest"
            ),
            digest,
        )
        self.assertEqual(_tested_digest_problems(self.history.root), [])

        # The other pinned site: evidence paths are the current round's, not round 5's.
        manifest = json.loads(
            (self.history.root / CHECKPOINT_MANIFEST).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["current_round"], 9)
        five = next(e for e in manifest["acceptance_rounds"] if e["round"] == 5)
        five["manual_report"] = f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-5.md"
        nine = next(e for e in manifest["acceptance_rounds"] if e["round"] == 9)
        nine["manual_report"] = f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-9.md"
        declared = _declared_evidence_paths(manifest)
        self.assertIn(f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-9.md", declared)
        self.assertNotIn(
            f"{ACCEPTANCE_EVIDENCE_PREFIX}manual-report-round-5.md",
            declared,
            "another round's declared evidence was licensed for this round's delta",
        )

    def test_the_freeze_commit_is_the_freeze_and_not_the_results_commit(self) -> None:
        """The honest sequence: freeze at `F`, record the streams' results at `G`.

        Both commits carry the value — that is what makes the two implementations
        indistinguishable on a shape check — but only `F`'s tree digests to it, because
        `G`'s tree also carries the results. So the difference is not cosmetic: a
        newest-first `_freeze_commit` returns `G` and the declared digest stops
        reproducing, which is the whole of half one.
        """
        self.history.commit("open round 5", _history_manifest(None))
        digest = self.history.seal()
        freeze = self.history.commit("freeze round 5", _history_manifest(digest))
        results = self.history.commit(
            "record the round-5 acceptance results",
            _history_manifest(digest, verdict="PASS"),
            {"artifacts/checkpoints/CP-00/manual-report-round-5.md": "PASS\n"},
        )

        self.assertEqual(self.history.head(), results)
        self.assertNotEqual(
            freeze, results, "this probe needs the freeze commit not to be HEAD"
        )
        self.assertEqual(_freeze_commit(self.history.root), freeze)
        self.assertEqual(
            _acceptance_digest_at(self.history.root, freeze, "tested_candidate_digest"),
            digest,
            "the sealed value is not the digest of the tree it was sealed into",
        )
        self.assertNotEqual(
            _acceptance_digest_at(self.history.root, results, "tested_candidate_digest"),
            digest,
            "the results commit digests to the same value as the freeze, so this "
            "history cannot tell the two implementations apart and proves nothing",
        )
        self.assertEqual(_tested_digest_problems(self.history.root), [])

    def test_a_value_set_changed_and_set_back_resolves_to_the_later_freeze(self) -> None:
        """The reason the walk stops rather than running to the bottom.

        `V` at `C1`, `W` at `C2`, `V` again at `C3`, results at `C4`. `C1` and `C3` both
        carry today's value and only `C3` froze it. An implementation that walks past the
        `C2` terminator returns `C1`; one that takes the newest carrier returns `C4`.
        """
        digest = self.history.seal()
        other = "b" * 64
        first = self.history.commit("freeze", _history_manifest(digest))
        self.history.commit("void the round, reseal on another tree", _history_manifest(other))
        refrozen = self.history.commit("freeze again on the value in force", _history_manifest(digest))
        results = self.history.commit(
            "record results", _history_manifest(digest, verdict="PASS")
        )

        self.assertNotEqual(refrozen, self.history.head())
        self.assertEqual(_freeze_commit(self.history.root), refrozen)
        self.assertNotEqual(
            _freeze_commit(self.history.root),
            first,
            "the walk ran past the commit that carried a different value",
        )
        self.assertNotEqual(
            _freeze_commit(self.history.root),
            results,
            "the newest carrier was taken instead of the oldest consecutive one",
        )

    def test_a_revision_carrying_the_round_twice_ends_the_walk(self) -> None:
        """The disjunct nobody drove: ``len(entries) != 1``.

        Replacing it with ``False`` left all 244 tests green. Every other probe here
        builds manifests through `_history_manifest`, which emits one entry per round by
        construction, so the clause was never given a revision it could reject.

        It is not a shape check that belongs somewhere else. `_freeze_commit` reads
        ``entries[0]`` immediately afterwards, so a revision carrying the current round
        twice has an arbitrary "the" round entry — and a duplicate is precisely how a
        hand-edited manifest goes wrong. Here the oldest revision carries two round-5
        entries that both hold the value: live code stops at it and resolves the commit
        above, the mutant walks straight through and resolves the older, wrong freeze.
        """
        digest = self.history.seal()
        duplicated = _history_manifest(digest)
        current = [
            entry for entry in duplicated["acceptance_rounds"] if entry["round"] == 5
        ]
        self.assertEqual(len(current), 1, "the fixture already carries a duplicate")
        duplicated["acceptance_rounds"].append(dict(current[0]))
        wrong = self.history.commit("the round recorded twice", duplicated)
        freeze = self.history.commit("the round recorded once", _history_manifest(digest))
        results = self.history.commit(
            "record results", _history_manifest(digest, verdict="PASS")
        )

        self.assertNotEqual(freeze, results, "this probe needs the freeze not to be HEAD")
        self.assertEqual(
            _freeze_commit(self.history.root),
            freeze,
            "the walk did not stop at a revision carrying the current round twice",
        )
        self.assertNotEqual(
            _freeze_commit(self.history.root),
            wrong,
            "the walk read entries[0] of a revision with two entries for the round and "
            "took it as the freeze",
        )

    def test_a_round_entry_that_disagrees_with_the_top_level_ends_the_walk(self) -> None:
        """Both halves must carry the value; the per-round copy is why a retro-edit
        cannot hide, so a commit where only the top level agrees is not a freeze."""
        digest = self.history.seal()
        half = _history_manifest(digest)
        half["acceptance_rounds"][-1]["tested_candidate_digest"] = "c" * 64
        earlier = self.history.commit("top level only", half)
        freeze = self.history.commit("both halves", _history_manifest(digest))
        self.history.commit("results", _history_manifest(digest, verdict="PASS"))

        self.assertNotEqual(freeze, self.history.head())
        self.assertEqual(_freeze_commit(self.history.root), freeze)
        self.assertNotEqual(_freeze_commit(self.history.root), earlier)

    def test_a_top_level_that_disagrees_with_the_round_entry_ends_the_walk(self) -> None:
        """The mirror direction, and the clause round nine found removable.

        The test above builds a revision whose *top level* carries the value and whose
        round entry does not, so it exercises only the entry half of the conjunction.
        Deleting the top-level clause left the suite green. Here the round entry carries
        the value and the top level does not: an implementation reading the entry alone
        walks straight past this revision and answers `earlier` instead of `freeze`.

        Both clauses matter for the same reason the per-round copy exists at all — the
        two places must agree, and a walk satisfied by either one on its own would accept
        a manifest whose halves disagree as the tree the streams judged.
        """
        digest = self.history.seal()
        half = _history_manifest(digest)
        half["tested_candidate_digest"] = "c" * 64
        earlier = self.history.commit("round entry only", half)
        freeze = self.history.commit("both halves", _history_manifest(digest))
        self.history.commit("results", _history_manifest(digest, verdict="PASS"))

        self.assertEqual(
            half["acceptance_rounds"][-1]["tested_candidate_digest"],
            digest,
            "the probe's earlier revision must carry the value in its round entry, or "
            "it does not isolate the top-level clause",
        )
        self.assertNotEqual(freeze, self.history.head())
        self.assertEqual(_freeze_commit(self.history.root), freeze)
        self.assertNotEqual(_freeze_commit(self.history.root), earlier)

    def test_a_history_longer_than_the_retired_window_is_walked_to_its_oldest_commit(
        self,
    ) -> None:
        """No commit window, and the reason there is none.

        An earlier form passed ``-n 200`` to `git log`. With more manifest revisions than
        that the walk ran off the end of its own window and returned the oldest commit
        *inside* it — a commit that did not freeze the value — which
        `_tested_digest_problems` then named as the commit that did. Reported red, so
        never unsafe, but wrong, and §11.12.5 said it failed closed. It did not.

        205 revisions all carrying the value: the freeze is the first of them, and the
        walk must reach it. Consecutive revisions differ only in a field the walk does
        not read, so every one of them is a commit that carries the value.
        """
        digest = "a" * 64
        for index in range(205):
            self.history.commit(f"revision {index}", _history_manifest(digest, note=index))
        commits = self.history.manifest_commits()

        self.assertEqual(len(commits), 205)
        self.assertNotEqual(commits[0], self.history.head())
        self.assertEqual(_freeze_commit(self.history.root), commits[0])

    def _three_commit_history(self) -> str:
        """`E` without the value, `F` freezing it, `G` recording results. Returns `F`."""
        digest = "a" * 64
        self.history.commit("open round 5", _history_manifest(None))
        freeze = self.history.commit("freeze round 5", _history_manifest(digest))
        self.history.commit("results", _history_manifest(digest, verdict="PASS"))
        self.assertEqual(_freeze_commit(self.history.root), freeze)
        return freeze

    def test_an_unreadable_ancestor_fails_closed(self) -> None:
        """"I cannot tell" beats a commit that is newer than the truth.

        Breaking the walk on an unreadable ancestor returns whatever was found so far — a
        commit *newer* than the real freeze, whose tree carries more than the streams
        judged, and which the digest would then be recomputed against. That is the unsafe
        direction.

        The failure has to arrive **after** a freeze has been found or the probe proves
        nothing: with every `show` failing, fail-open and fail-closed both return `None`
        because there is nothing to keep. Two revisions are read successfully and the
        third — the one that would end the walk — is the one that breaks.
        """
        freeze = self._three_commit_history()
        with unittest.mock.patch.object(
            subprocess, "run", _failing_show_after(2, subprocess.run)
        ):
            self.assertIsNone(
                _freeze_commit(self.history.root),
                f"the walk returned a commit ({freeze[:12]}) on evidence it could not "
                "read to the end",
            )

    def test_an_unparseable_ancestor_fails_closed(self) -> None:
        """The same, for a revision that reads but is not JSON."""
        self._three_commit_history()
        with unittest.mock.patch.object(
            subprocess,
            "run",
            _failing_show_after(2, subprocess.run, payload=b"{ not json"),
        ):
            self.assertIsNone(_freeze_commit(self.history.root))

    def test_no_digest_recorded_means_no_freeze_commit(self) -> None:
        """The silent direction, so the check cannot rot into an unconditional answer."""
        self.history.commit("no round dispatched", _history_manifest(None))
        self.assertIsNone(_freeze_commit(self.history.root))

    def test_a_real_retro_edit_is_caught_on_real_commits(self) -> None:
        """`_retro_edited_digests` over history, not over a hand-built pair of dicts.

        The pure comparison is proved by
        `test_the_retro_edit_rule_is_proved_on_synthetic_history`. The walk that feeds it
        was not: replacing the whole function body with `return []` stayed green, because
        this repository carries one per-round value and it has never changed. Real
        commits are now available here, so the walk is exercised on them.
        """
        original = "a" * 64
        self.history.commit("freeze round 5", _history_manifest(original))
        self.assertEqual(
            _retro_edited_digests(self.history.root),
            [],
            "a history with one unchanged value must be silent, or the probe below "
            "proves only that the function is noisy",
        )
        self.history.commit("quietly reseal the same round", _history_manifest("b" * 64))
        problems = _retro_edited_digests(self.history.root)
        self.assertTrue(
            any(original in problem and "round 5" in problem for problem in problems),
            f"a per-round digest changed between commits and nothing said so: {problems}",
        )


def _failing_show_after(successes: int, real, *, payload: bytes | None = None):
    """A `subprocess.run` whose Git ``show`` calls stop working after ``successes``.

    ``payload`` `None` makes them fail outright; bytes make them succeed and return
    something that is not a manifest, which is the other way a revision becomes
    unreadable.
    """
    seen = 0

    def stand_in(arguments, *rest, **keywords):
        nonlocal seen
        if "show" in arguments:
            seen += 1
            if seen > successes:
                if payload is None:
                    return subprocess.CompletedProcess(
                        arguments, 128, b"", b"fatal: bad object"
                    )
                return subprocess.CompletedProcess(arguments, 0, payload, b"")
        return real(arguments, *rest, **keywords)

    return stand_in


class WriteBoundaryTests(unittest.TestCase):
    """This task owns two paths. Nothing else under them may appear.

    The gate asserts a path set, never a status code, so it holds before integration
    (`??`), while the files are being edited (` M`) and once they are committed and
    clean (no output at all) — the repair `W0-CLN-01` had to make to `GATE-F` after that
    gate became unsatisfiable by its own integration.

    **`--untracked-files=all`, corrected in round nine.** This docstring used to say
    `docs/program/reviews/` "is a new directory". It was, at round one; it has been
    tracked since `854a6820`, and both deliverables are tracked today. So the flag no
    longer changes this gate's output, and an independent reviewer of round eight's
    submission removed it and stayed green — correctly. It is kept because the reason it
    was added is real and returns the moment either deliverable is untracked again,
    which is the state every fresh task starts in: `--untracked-files=normal` collapses
    a wholly untracked directory to one directory entry, and the gate could then never
    name the file it is about.
    `test_the_untracked_files_flag_is_what_names_a_file_in_a_new_directory` exercises
    that difference on a sandbox rather than asserting it, since this repository can no
    longer show it. That the flag is *removable from this gate today* is recorded in
    `docs/program/reviews/W0-QA-01.md` §11.14.6 rather than papered over.
    """

    def test_the_untracked_files_flag_is_what_names_a_file_in_a_new_directory(self) -> None:
        """Why the flag is on the gate, shown rather than asserted.

        Run against a sandbox, because the repository can no longer demonstrate it: both
        deliverables are tracked, so the two forms of the command give identical output
        here. In a sandbox a wholly untracked directory is created and the difference is
        the whole point — the default form names the *directory* and the `-uall` form
        names the *file*.
        """
        sandbox = _CheckpointSandbox()
        self.addCleanup(sandbox.__exit__)
        directory = "docs/program/probe-a-wholly-untracked-directory"
        (sandbox.root / directory).mkdir(parents=True)
        (sandbox.root / directory / "deliverable.md").write_text("x\n", encoding="utf-8")

        def status(*flags: str) -> set[str]:
            result = _git(
                "-C", str(sandbox.root), "status", "--porcelain", *flags,
                "--", directory, text=True, check=True,
            )
            return {line[3:] for line in result.stdout.splitlines() if line}

        self.assertEqual(status(), {f"{directory}/"})
        self.assertEqual(status("--untracked-files=all"), {f"{directory}/deliverable.md"})

    def test_only_the_two_owned_paths_are_reported_under_the_owned_trees(self) -> None:
        owned = {
            "tests/contract/test_cp00_candidate.py",
            "docs/program/reviews/W0-QA-01.md",
        }
        result = _git(
            "-C",
            str(REPOSITORY_ROOT),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "tests/contract",
            "docs/program/reviews",
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        reported = {line[3:] for line in result.stdout.splitlines() if line}
        self.assertEqual(
            sorted(reported - owned),
            [],
            "a path outside this task's two allowed paths is dirty",
        )
        missing = sorted(
            path for path in owned if not (REPOSITORY_ROOT / path).is_file()
        )
        self.assertEqual(missing, [], "an owned deliverable is missing")

    def test_the_reviewed_families_carry_nothing_undeclared(self) -> None:
        """No working-tree change under a reviewed family beyond the declared delta.

        The earlier form asserted the status output was empty. That was one-directional
        in the way this wave keeps finding: it passed before a ratification edit and
        again after the edit was committed, and failed only in between — a gate that
        reports on the phase of the work rather than on the work. It now asserts the
        path set against the same declared delta the drift check uses, so it holds in
        every phase and still fails on any path nobody declared.
        """
        result = _git(
            "-C",
            str(REPOSITORY_ROOT),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "contracts",
            "fixtures",
            "docs/architecture",
            "scripts",
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        reported = {line[3:] for line in result.stdout.splitlines() if line}
        _, declared, problems = _ratification_record(REPOSITORY_ROOT)
        licensed = frozenset() if problems else declared
        self.assertEqual(
            sorted(reported - licensed),
            [],
            "a reviewed artifact is dirty and no ratification record declares it; "
            "this review writes to nothing it reviews",
        )


if __name__ == "__main__":
    unittest.main()
