"""The decisions a restart carries to the run that replaced its source (`RUN-RESTART-01`, owner ruling `R-155b`).

A restart creates a new run that replaces a ``partial``, ``failed`` or ``cancelled`` source; when the new run publishes, the source is
tombstoned (`R-155g`). The expert's decisions on the findings of that source -- and of every run behind it, since a restart of a restart
starts from the run before the last -- are carried **automatically** to the findings of the new run that match verbatim. No expert confirms
them: this is the one carry that departs from the confirm-only carryover of `W59-DECISION-CARRYOVER-01`
(:mod:`auditmanager.decisions.carryover`), and it says so in every event it writes.

Public surface (re-exported by :mod:`auditmanager.decisions.public`):

* :func:`carry_restart_decisions` -- the idempotent carry of one restart run; called by the executor after the run published and by the
  worker sweeper for a run whose carry did not finish;
* :func:`pending_restart_carries` -- the restart runs that published and whose carry is not complete, for that sweeper;
* :class:`RestartCarryReport` -- what a call did, for the caller to log.

What is carried, from where
---------------------------
**The lineage.** ``audit_run.started_from_run_id`` is walked from the new run while the run walked from has a ``restart_point`` (the restart
columns of migration ``0071``), up to and including the first run that has none: the root of the chain. Those runs are, or are about to be,
tombstoned; the tombstone keeps their data (`R-155a`), and they are read all the same.

**The match is content, 1:1.** A finding is identified for the carry by what is stored for it, never by its identity (a restart allocates
fresh ``finding_uid`` values, `P02` section 5.2) and never by a position or a number: the category, the finding text and the recommendation
text of its canonical observation, and that observation's evidence (page, quote, ``char_start``, ``char_end``, in evidence order). There is
no title field. A block finding has no ``finding_evidence`` rows (its crops live in ``finding_block_evidence``), so it matches on the text and
the category.

**Ties.** Findings with identical content are paired in ``extended_observation_ref`` order, natural-sorted (the reference the publisher
stored on each observation, unique within a run), and only when both sides have the same number of them and every one has a reference that
is unique on its side; otherwise nothing of that group is carried and the report counts it (``ties_skipped``). A run of the lineage whose
group cannot be paired is skipped for that group alone; the other runs of the lineage still carry theirs.

**Newest wins.** When several runs of the lineage decided the same content, the verdict is the one whose event is newest (the ledger's total
order, ``sequence_no``, the order the projection itself uses). A withdrawal (``revoke``) is a decision too: when it is the newest, no
verdict is carried (``withdrawn``). Comments are not competing decisions: every direct comment of every matching finding of the lineage is
carried, in the order it was written.

**What is a source.** A verdict event is a source whatever it is (a direct one, an earlier restart's own carried copy, a confirmed carryover of
`W59`). A comment is a source only when an expert wrote it (``carried_from_decision_id`` is ``NULL``) and it is not itself the copy a restart
made (its command is :data:`CARRY_DECISION_COMMAND_TYPE`): the sentence of a carried event is the system's, not anyone's words.

What is written
---------------
Everything goes through :func:`~auditmanager.decisions.ledger.record_decision`, in the order *verdict, then comments*, so the finding's latest
comment ends as the expert's own:

* the verdict is an ``accept`` or ``reject`` event with ``carried_from_decision_id`` naming the source decision, and the comment
  :func:`~auditmanager.decisions.carryover.carryover_comment` renders for mode ``restart`` (the identities of the source run, decision and
  finding and of the target run; nothing says «после подтверждения экспертом»). Its severity is carried when the target observation can hold
  one (``proposed_severity`` on the canonical observation, the rule of ``ledger._SEVERITY_TARGET``); otherwise the verdict is carried
  without it and the report counts that (``severities_skipped``) -- the carry is never refused as a whole for it;
* a comment is a ``comment`` event whose text is a fixed sentence naming the source run and the original author, then the original words
  (cut at the ledger's 4000 characters and counted in ``truncated_comments`` when they do not fit). The 0058 CHECK lets only ``accept`` and
  ``reject`` carry a link, so a comment's provenance is this text and its command's outcome, never the link;
* the author is ``actor_user_uid`` -- the account that started the restart -- and the label is that account's display label. The original
  author of a comment is named in its text; of a verdict, by the link.

**One command per carried event.** The key is derived from the target run and the source decision (``restart-carry:<run>:<decision>:v`` for
the verdict and ``:c`` for a comment), so ``uq_expert_decision_event_command_id`` and the command's own ``UNIQUE (command_type,
idempotency_key)`` make a repeat answer the existing event and append nothing. The command's outcome records ``mode = "restart"``, the
source run (``run_id``), and the source and target findings: it is what :func:`~auditmanager.decisions.carryover.carried_origins` joins to
fill the ``mode`` of the wire's ``DecisionCarriedFrom``.

**The target is left alone when an expert decided it.** Each target finding is locked ``FOR UPDATE`` (so an ``appendDecision`` on it waits),
and when it holds any event this carry did not write, nothing is carried to it (``already_decided``): a verdict appended after an expert's
own would otherwise silently replace it.

**A failed item does not stop the batch.** Each item runs in a savepoint of its target's transaction; one that raises -- the decision
memory's port included, whose failure fails the decision by design (`ADR-0027`) -- leaves no trace of itself, is recorded in the report
(``failures``, ``failure_details``) and is retried by the next call. Carried verdicts do not vote in precedents: ``record_decision`` derives
their origin as ``carried`` from the link, and ``precedents.votes.case_vote`` leaves such events out.

When the carry is complete
--------------------------
A call that finishes with no failure writes the **marker**: one ``command_record`` of type :data:`CARRY_RUN_COMMAND_TYPE`, key
``restart-carry-run:<run_id>``, state ``succeeded``, whose outcome holds the report's counts and ``mode = "restart"``. It is durable, so a
restart of the process loses nothing, and it is the whole definition of «complete»: :func:`pending_restart_carries` lists the restart runs
that published (``published`` or ``partial``) and have no such record, and a call that finds the marker answers it without reading anything
else. Unmatched decisions, skipped ties, targets an expert decided and withdrawals are outcomes, not failures, and do not hold the marker
back; an item that fails does, so a run with a persistently failing item stays pending (loudly: the report names it) until that is fixed.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.decisions.carryover import (
    RESTART_MODE,
    CarryoverProvenance,
    carryover_comment,
)
from auditmanager.decisions.ledger import record_decision
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, RunId
from auditmanager.shared.identity.ids import UserUid

__all__ = [
    "CARRY_DECISION_COMMAND_TYPE",
    "CARRY_RUN_COMMAND_TYPE",
    "COMMENT_CHARS",
    "CarryEvent",
    "CarryFinding",
    "CarryItem",
    "CarryPlan",
    "RestartCarryReport",
    "carried_comment_text",
    "carry_restart_decisions",
    "item_idempotency_key",
    "marker_idempotency_key",
    "pending_restart_carries",
    "plan_restart_carry",
]

if TYPE_CHECKING:
    from auditmanager.ingest.public import CommandRepository

_log = logging.getLogger(__name__)

#: The command type of one carried event, and of the run-level marker that says the carry of a run is complete. ``command_record``'s
#: ``ck_command_record_command_type`` is lowercase snake_case, 3 to 64 characters.
CARRY_DECISION_COMMAND_TYPE: Final[str] = "carry_restart_decision"
CARRY_RUN_COMMAND_TYPE: Final[str] = "carry_restart_run"

#: The ledger's ``ck_expert_decision_event_comment_length`` upper bound.
COMMENT_CHARS: Final[int] = 4000

#: The longest lineage walked: a guard against a cycle the schema's own checks should make impossible, never a rule about restarts.
_MAX_LINEAGE: Final[int] = 64

_KIND_VERDICT: Final[str] = "verdict"
_KIND_COMMENT: Final[str] = "comment"
_KEY_SUFFIX: Final[dict[str, str]] = {_KIND_VERDICT: "v", _KIND_COMMENT: "c"}

_CARRYING_STATES: Final[tuple[str, ...]] = ("published", "partial")

#: How many observation identities one evidence read names; an ``IN`` list of this length is cheap and a project's findings can be thousands.
_EVIDENCE_CHUNK: Final[int] = 500


# ---------------------------------------------------------------------------------------------------------------------------------
# The content a finding is matched on, and the events that decide it. Plain values: the plan below is a pure function of them.
# ---------------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CarryFinding:
    """One finding as the carry sees it: its canonical observation's content and what is needed to write to it.

    ``evidence`` is ``(page_number, quote, char_start, char_end)`` per evidence row, in ``evidence_ordinal`` order; empty for a block finding.
    ``extended_ref`` is the publisher's ``extended_observation_ref`` of the observation, the only ordinal a finding has.
    ``severity_eligible`` says whether a decision on this observation may carry a severity (``ledger._SEVERITY_TARGET``).
    """

    finding_uid: str
    run_id: str
    version_uid: str
    version_ordinal: int
    observation_id: str
    category: str
    finding_text: str
    recommendation_text: str
    extended_ref: str | None = None
    severity_eligible: bool = False
    evidence: tuple[tuple[int, str, int, int], ...] = ()

    @property
    def signature(self) -> tuple[Any, ...]:
        """What two findings must share, verbatim, to be the same finding for the carry."""
        return (self.category, self.finding_text, self.recommendation_text, self.evidence)


@dataclass(frozen=True, slots=True)
class CarryEvent:
    """One ledger event of a source finding, with the two facts the carry needs beside it: its place in the total order and its command's type."""

    decision_id: str
    finding_uid: str
    sequence_no: int
    event_type: str
    verdict: str | None
    severity: str | None
    comment: str | None
    author_label: str
    carried_from_decision_id: str | None = None
    command_type: str | None = None

    @property
    def is_direct_comment(self) -> bool:
        """The event carries words an expert wrote: no link to a carried source and not the copy an earlier restart made."""
        return (
            self.comment is not None
            and bool(self.comment.strip())
            and self.carried_from_decision_id is None
            and self.command_type != CARRY_DECISION_COMMAND_TYPE
        )


@dataclass(frozen=True, slots=True)
class CarryItem:
    """One event to append to a target finding."""

    kind: str
    target: CarryFinding
    source: CarryFinding
    source_event: CarryEvent
    event_type: str
    severity: str | None = None
    #: A verdict whose source had a severity the target cannot hold: carried without it.
    severity_skipped: bool = False


@dataclass(frozen=True, slots=True)
class CarryPlan:
    """What the carry will append, and what it found it could not."""

    items: tuple[CarryItem, ...]
    sources_decided: int
    unmatched_decisions: int
    ties_skipped: int
    withdrawn: int


# ---------------------------------------------------------------------------------------------------------------------------------
# The plan: a pure function, so the matching rules are testable without a database.
# ---------------------------------------------------------------------------------------------------------------------------------

_DIGITS = re.compile(r"(\d+)")


def _natural(ref: str) -> tuple[tuple[int, int, str], ...]:
    """``primary_text_2`` before ``primary_text_10``: digit runs compare as numbers, the rest as text."""
    return tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in _DIGITS.split(ref) if part != ""
    )


def _order_key(finding: CarryFinding) -> tuple[Any, ...]:
    ref = finding.extended_ref or ""
    return (_natural(ref), ref, finding.finding_uid)


def _orderable(group: Sequence[CarryFinding]) -> bool:
    """Every member has a reference and no two share one: the only case in which an order of equal findings means anything."""
    refs = [member.extended_ref for member in group]
    return all(ref is not None for ref in refs) and len(set(refs)) == len(refs)


def _pair(targets: Sequence[CarryFinding], sources: Sequence[CarryFinding]) -> list[tuple[CarryFinding, CarryFinding]] | None:
    """Pair equal findings of the target run and of one run of the lineage, or ``None`` when no pairing is defined (a tie)."""
    if len(targets) == 1 and len(sources) == 1:
        return [(targets[0], sources[0])]
    if len(targets) != len(sources) or len(targets) < 2:
        return None
    if not (_orderable(targets) and _orderable(sources)):
        return None
    return list(zip(sorted(targets, key=_order_key), sorted(sources, key=_order_key)))


def _last_verdict_event(events: Sequence[CarryEvent]) -> CarryEvent | None:
    """The verdict-bearing event that stands for a finding: its newest (``revoke`` carries the verdict ``pending``, as in the view)."""
    bearing = [event for event in events if event.verdict is not None]
    return max(bearing, key=lambda event: event.sequence_no) if bearing else None


def _direct_comments(events: Sequence[CarryEvent]) -> list[CarryEvent]:
    return sorted((event for event in events if event.is_direct_comment), key=lambda event: event.sequence_no)


def _is_decided(events: Sequence[CarryEvent]) -> bool:
    return _last_verdict_event(events) is not None or bool(_direct_comments(events))


def plan_restart_carry(
    *,
    target_run_id: str,
    lineage_run_ids: Sequence[str],
    findings: Sequence[CarryFinding],
    events: Mapping[str, Sequence[CarryEvent]],
) -> CarryPlan:
    """Match the findings of ``target_run_id`` to those of its lineage and say which events to append to which.

    ``events`` maps a ``finding_uid`` to its ledger events; a finding absent from it has none. Deterministic: the same input is the same
    plan in the same order (the targets by identity, the verdict before the comments, the comments in the order they were written).
    """
    lineage = set(lineage_run_ids)
    targets_by_sig: dict[tuple[Any, ...], list[CarryFinding]] = {}
    sources_by_sig: dict[tuple[Any, ...], dict[str, list[CarryFinding]]] = {}
    sources_decided = 0
    for finding in findings:
        if finding.run_id == target_run_id:
            targets_by_sig.setdefault(finding.signature, []).append(finding)
        elif finding.run_id in lineage:
            sources_by_sig.setdefault(finding.signature, {}).setdefault(finding.run_id, []).append(finding)
            if _is_decided(events.get(finding.finding_uid, ())):
                sources_decided += 1

    candidates: dict[str, list[CarryFinding]] = {}
    unmatched = ties = 0
    for signature in sorted(sources_by_sig, key=repr):
        runs = sources_by_sig[signature]
        decided_runs = {run for run, members in runs.items() if any(_is_decided(events.get(m.finding_uid, ())) for m in members)}
        if not decided_runs:
            continue
        targets = targets_by_sig.get(signature)
        if not targets:
            unmatched += 1
            continue
        tied = False
        for run in sorted(runs):
            pairs = _pair(targets, runs[run])
            if pairs is None:
                tied = tied or run in decided_runs
                continue
            for target, source in pairs:
                candidates.setdefault(target.finding_uid, []).append(source)
        if tied:
            ties += len(targets)

    items: list[CarryItem] = []
    withdrawn = 0
    target_by_uid = {finding.finding_uid: finding for group in targets_by_sig.values() for finding in group}
    for target_uid in sorted(candidates):
        target = target_by_uid[target_uid]
        sources = candidates[target_uid]
        stands = [
            (event, source) for source in sources
            if (event := _last_verdict_event(events.get(source.finding_uid, ()))) is not None
        ]
        if stands:
            event, source = max(stands, key=lambda pair: pair[0].sequence_no)
            if event.verdict == "pending":
                withdrawn += 1
            elif event.event_type in ("accept", "reject"):
                severity = event.severity if event.event_type == "accept" else None
                carried = severity if severity is not None and target.severity_eligible else None
                items.append(CarryItem(
                    kind=_KIND_VERDICT, target=target, source=source, source_event=event, event_type=event.event_type,
                    severity=carried, severity_skipped=severity is not None and carried is None,
                ))
        comments = sorted(
            ((event, source) for source in sources for event in _direct_comments(events.get(source.finding_uid, ()))),
            key=lambda pair: pair[0].sequence_no,
        )
        for event, source in comments:
            items.append(CarryItem(
                kind=_KIND_COMMENT, target=target, source=source, source_event=event, event_type="comment",
            ))
    return CarryPlan(
        items=tuple(items), sources_decided=sources_decided, unmatched_decisions=unmatched, ties_skipped=ties, withdrawn=withdrawn,
    )


# ---------------------------------------------------------------------------------------------------------------------------------
# Keys and sentences.
# ---------------------------------------------------------------------------------------------------------------------------------


def item_idempotency_key(run_id: str, item: CarryItem) -> str:
    """The key of one carried event: the target run and the source decision, and which of the source's two roles it is carried in.

    A source decision can be both a finding's verdict and its comment (an ``accept`` that carries words), and the two are two events.
    Shape: ``restart-carry:run_<ULID>:dec_<ULID>:v`` -- inside ``ck_command_record_idempotency_key`` (1 to 128 characters).
    """
    return f"restart-carry:{run_id}:{item.source_event.decision_id}:{_KEY_SUFFIX[item.kind]}"


def marker_idempotency_key(run_id: str) -> str:
    """The key of the marker that says the carry of ``run_id`` is complete."""
    return f"restart-carry-run:{run_id}"


def carried_comment_text(source_run_id: str, author_label: str, words: str) -> tuple[str, bool]:
    """The text of a carried comment, and whether the original words had to be cut to fit the ledger's 4000 characters.

    Deterministic: a fixed sentence (the source run and the original author, whom the event's own author, the restart's starter, is not),
    then the words.
    """
    prefix = f"Перенесено при перезапуске из прогона {source_run_id} (автор: {author_label}): "
    room = COMMENT_CHARS - len(prefix)
    if len(words) <= room:
        return prefix + words, False
    return prefix + words[: room - 1] + "…", True


# ---------------------------------------------------------------------------------------------------------------------------------
# The report.
# ---------------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RestartCarryReport:
    """What one call of :func:`carry_restart_decisions` found and did, for its caller to log.

    ``carried_verdicts`` and ``carried_comments`` are the planned events that stand in the ledger after the call (appended by it or by an
    earlier call), so a repeat reports the same numbers; ``appended`` is how many events this call appended (0 for a repeat) and
    ``replayed`` how many items it found already carried. The rest are outcomes the carry could not turn into an event, none of them a
    failure: ``severities_skipped`` (verdicts carried without their severity, the target observation having no ``proposed_severity``),
    ``unmatched_decisions`` (distinct contents decided in the lineage that no finding of the run matches), ``ties_skipped`` (findings of the
    run whose identical twins could not be paired), ``already_decided`` (targets an expert had decided, left alone), ``withdrawn`` (targets
    whose newest source verdict is a withdrawal) and ``truncated_comments``. ``failures`` is the one that holds the run's marker back, and
    ``failure_details`` names each (the source decision and the error); ``complete`` says the marker stands, ``already_complete`` that this call
    found it and did nothing else.
    """

    run_id: str
    lineage: tuple[str, ...] = ()
    sources_decided: int = 0
    carried_verdicts: int = 0
    carried_comments: int = 0
    appended: int = 0
    replayed: int = 0
    severities_skipped: int = 0
    unmatched_decisions: int = 0
    ties_skipped: int = 0
    already_decided: int = 0
    withdrawn: int = 0
    truncated_comments: int = 0
    failures: int = 0
    failure_details: tuple[str, ...] = ()
    complete: bool = False
    already_complete: bool = False

    _COUNTS = (
        "sources_decided", "carried_verdicts", "carried_comments", "appended", "replayed", "severities_skipped",
        "unmatched_decisions", "ties_skipped", "already_decided", "withdrawn", "truncated_comments", "failures",
    )

    def as_fields(self) -> dict[str, Any]:
        """Flat, loggable fields: the counts, the run, the lineage and whether the carry is complete."""
        fields: dict[str, Any] = {"run_id": self.run_id, "lineage": list(self.lineage)}
        fields.update({name: getattr(self, name) for name in self._COUNTS})
        fields["complete"] = self.complete
        fields["already_complete"] = self.already_complete
        return fields

    def marker_outcome(self) -> dict[str, Any]:
        """The outcome the marker stores: the counts, never the failure details (a marker stands only without failures)."""
        outcome = self.as_fields()
        outcome["mode"] = RESTART_MODE
        return outcome

    @classmethod
    def from_marker(cls, run_id: str, outcome: Mapping[str, Any]) -> "RestartCarryReport":
        counts = {
            name: outcome[name] for name in cls._COUNTS
            if isinstance(outcome.get(name), int) and not isinstance(outcome.get(name), bool)
        }
        lineage = outcome.get("lineage")
        return cls(
            run_id=run_id, lineage=tuple(lineage) if isinstance(lineage, list) else (), complete=True, already_complete=True,
            **{**counts, "appended": 0},
        )


@dataclass(slots=True)
class _Tally:
    carried_verdicts: int = 0
    carried_comments: int = 0
    appended: int = 0
    replayed: int = 0
    severities_skipped: int = 0
    already_decided: int = 0
    truncated_comments: int = 0
    failures: int = 0
    details: list[str] = field(default_factory=list)

    def merge(self, other: "_Tally") -> None:
        for name in (
            "carried_verdicts", "carried_comments", "appended", "replayed", "severities_skipped", "already_decided",
            "truncated_comments", "failures",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        self.details.extend(other.details)


# ---------------------------------------------------------------------------------------------------------------------------------
# Reads.
# ---------------------------------------------------------------------------------------------------------------------------------

_RUN = text("SELECT run_id, state, restart_point FROM audit_run WHERE run_id = :run_id")

#: The chain behind a restart run: the runs it started from, nearest first, the root last. Recursion goes on only through a run that is
#: itself a restart, so the first run without a ``restart_point`` ends it and is included.
_LINEAGE = text(
    """
    WITH RECURSIVE chain (run_id, started_from_run_id, restart_point, depth) AS (
        SELECT r.run_id, r.started_from_run_id, r.restart_point, 0
          FROM audit_run r WHERE r.run_id = :run_id
        UNION ALL
        SELECT p.run_id, p.started_from_run_id, p.restart_point, c.depth + 1
          FROM chain c JOIN audit_run p ON p.run_id = c.started_from_run_id
         WHERE c.restart_point IS NOT NULL AND c.depth < :max_depth
    )
    SELECT run_id FROM chain WHERE depth > 0 ORDER BY depth
    """
)

#: One row per finding of the named runs, with the content of its canonical observation (the first observation by identity for a finding
#: that names none), the version's display ordinal and whether a decision on that observation may carry a severity.
_FINDINGS = text(
    """
    SELECT f.finding_uid, f.allocated_by_run_id AS run_id, f.version_uid, dv.version_ordinal,
           o.finding_observation_id, o.category, o.finding_text, o.recommendation_text, o.extended_observation_ref,
           COALESCE(o.proposed_severity IS NOT NULL AND f.canonical_observation_id = o.finding_observation_id, false)
               AS severity_eligible
      FROM finding f
      JOIN document_version dv ON dv.version_uid = f.version_uid
      JOIN LATERAL (
            SELECT x.finding_observation_id, x.category, x.finding_text, x.recommendation_text, x.extended_observation_ref,
                   x.proposed_severity
              FROM finding_observation x
             WHERE x.finding_uid = f.finding_uid
             ORDER BY (x.finding_observation_id = f.canonical_observation_id) DESC, x.finding_observation_id COLLATE "C"
             LIMIT 1
      ) o ON true
     WHERE f.allocated_by_run_id IN :run_ids
     ORDER BY f.finding_uid COLLATE "C"
    """
).bindparams(bindparam("run_ids", expanding=True))

_EVIDENCE = text(
    """
    SELECT finding_observation_id, page_number, quote, char_start, char_end
      FROM finding_evidence
     WHERE finding_observation_id IN :observation_ids
     ORDER BY finding_observation_id COLLATE "C", evidence_ordinal
    """
).bindparams(bindparam("observation_ids", expanding=True))

_EVENTS = text(
    """
    SELECT e.decision_id, e.finding_uid, e.sequence_no, e.event_type, e.verdict, e.severity, e.comment, e.author_label,
           e.carried_from_decision_id, c.command_type
      FROM expert_decision_event e
      LEFT JOIN command_record c ON c.command_id = e.command_id
     WHERE e.finding_uid IN :finding_uids
     ORDER BY e.finding_uid COLLATE "C", e.sequence_no
    """
).bindparams(bindparam("finding_uids", expanding=True))

_MARKER = text(
    "SELECT state, outcome FROM command_record WHERE command_type = :command_type AND idempotency_key = :key"
)

_LOCK_TARGET = text("SELECT finding_uid FROM finding WHERE finding_uid = :finding_uid FOR UPDATE")

#: An event on the target that this carry did not write: an expert (or another path) decided or commented it.
_FOREIGN_EVENT = text(
    """
    SELECT 1
      FROM expert_decision_event e
      LEFT JOIN command_record c ON c.command_id = e.command_id
     WHERE e.finding_uid = :finding_uid AND c.command_type IS DISTINCT FROM :command_type
     LIMIT 1
    """
)

_PENDING = text(
    """
    SELECT r.run_id
      FROM audit_run r
     WHERE r.restart_point IS NOT NULL
       AND r.state IN :states
       AND NOT EXISTS (
            SELECT 1 FROM command_record m
             WHERE m.command_type = :marker_type
               AND m.idempotency_key = 'restart-carry-run:' || r.run_id
               AND m.state = 'succeeded'
       )
     ORDER BY r.created_at, r.run_id COLLATE "C"
    """
).bindparams(bindparam("states", expanding=True))


def _chunks(values: Sequence[str], size: int) -> list[list[str]]:
    return [list(values[start:start + size]) for start in range(0, len(values), size)]


def _read_run(session: Session, run_id: str) -> Mapping[str, Any]:
    row = session.execute(_RUN, {"run_id": run_id}).mappings().first()
    if row is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    if row["restart_point"] is None or row["state"] not in _CARRYING_STATES:
        # A run that is no restart has no lineage; a run that has not published has no findings to carry to, and a marker written for it
        # would say «complete» about nothing.
        raise DomainError(
            ErrorCode.CONFLICT, aggregate_type="AuditRun", conflict_reason="restart_carry_run_not_a_published_restart",
        )
    return row


def _read_marker(session: Session, run_id: str) -> Mapping[str, Any] | None:
    row = session.execute(
        _MARKER, {"command_type": CARRY_RUN_COMMAND_TYPE, "key": marker_idempotency_key(run_id)},
    ).mappings().first()
    if row is None or row["state"] != "succeeded" or not isinstance(row["outcome"], dict):
        return None
    return row["outcome"]


def _read_findings(session: Session, run_ids: Sequence[str]) -> list[CarryFinding]:
    rows = session.execute(_FINDINGS, {"run_ids": list(run_ids)}).mappings().all()
    evidence: dict[str, list[tuple[int, str, int, int]]] = {}
    observation_ids = [row["finding_observation_id"] for row in rows]
    for chunk in _chunks(observation_ids, _EVIDENCE_CHUNK):
        for item in session.execute(_EVIDENCE, {"observation_ids": chunk}).mappings():
            evidence.setdefault(item["finding_observation_id"], []).append(
                (int(item["page_number"]), item["quote"], int(item["char_start"]), int(item["char_end"])),
            )
    return [
        CarryFinding(
            finding_uid=row["finding_uid"], run_id=row["run_id"], version_uid=row["version_uid"],
            version_ordinal=int(row["version_ordinal"]), observation_id=row["finding_observation_id"], category=row["category"],
            finding_text=row["finding_text"], recommendation_text=row["recommendation_text"],
            extended_ref=row["extended_observation_ref"], severity_eligible=bool(row["severity_eligible"]),
            evidence=tuple(evidence.get(row["finding_observation_id"], ())),
        )
        for row in rows
    ]


def _read_events(session: Session, finding_uids: Sequence[str]) -> dict[str, list[CarryEvent]]:
    events: dict[str, list[CarryEvent]] = {}
    for chunk in _chunks(list(finding_uids), _EVIDENCE_CHUNK):
        for row in session.execute(_EVENTS, {"finding_uids": chunk}).mappings():
            events.setdefault(row["finding_uid"], []).append(CarryEvent(
                decision_id=row["decision_id"], finding_uid=row["finding_uid"], sequence_no=int(row["sequence_no"]),
                event_type=row["event_type"], verdict=row["verdict"], severity=row["severity"], comment=row["comment"],
                author_label=row["author_label"], carried_from_decision_id=row["carried_from_decision_id"],
                command_type=row["command_type"],
            ))
    return events


def _author_label(session: Session, actor_user_uid: str) -> str:
    """The display label of the account that started the restart: the name its events are attributed to (`R-37`)."""
    from auditmanager.access.public import AccountRepository

    account = AccountRepository().get_account(session, actor_user_uid)
    if account is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="User")
    label = account.record.display_label
    if not label.strip() or len(label) > 128:
        # `ck_expert_decision_event_author_label`: an account with no complete profile can have a login longer than a label may be.
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="actor_user_uid", constraint="author_label")
    return label


def pending_restart_carries(session: Session) -> list[str]:
    """The restart runs whose carry is not complete: they published (``published`` or ``partial``) and have no marker, oldest first.

    «Complete» is the marker :func:`carry_restart_decisions` writes (see the module docstring). A run that has not published is not listed:
    it has no findings to carry to, and the executor calls the carry after publication. An empty list is the normal answer.
    """
    rows = session.execute(_PENDING, {"states": list(_CARRYING_STATES), "marker_type": CARRY_RUN_COMMAND_TYPE}).scalars().all()
    return [str(run_id) for run_id in rows]


# ---------------------------------------------------------------------------------------------------------------------------------
# The carry.
# ---------------------------------------------------------------------------------------------------------------------------------


def _validated(value: str, kind: Any, field_name: str) -> None:
    try:
        kind.parse(value)
    except (IdentityError, TypeError):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field_name, constraint="format") from None


def _carry_item(
    session: Session, commands: "CommandRepository", *, run_id: str, item: CarryItem, actor_user_uid: str, author_label: str,
    local: _Tally,
) -> None:
    """Append one carried event under its own command, or find it already carried. Raises on any failure; the caller's savepoint undoes it."""
    from auditmanager.ingest.public import CommandReplay, payload_fingerprint

    source, target, event = item.source, item.target, item.source_event
    payload: dict[str, str] = {
        "command": "carry_restart_decision.v1",
        "run_id": run_id,
        "kind": item.kind,
        "source_decision_id": event.decision_id,
        "source_finding_uid": source.finding_uid,
        "source_run_id": source.run_id,
        "target_finding_uid": target.finding_uid,
        "target_finding_observation_id": target.observation_id,
    }
    truncated = False
    if item.kind == _KIND_VERDICT:
        provenance = CarryoverProvenance(
            source_finding_uid=source.finding_uid, source_decision_id=event.decision_id, source_version_uid=source.version_uid,
            source_version_ordinal=source.version_ordinal, target_version_uid=target.version_uid, mode=RESTART_MODE,
            source_run_id=source.run_id, target_run_id=run_id,
        )
        comment: str = carryover_comment(provenance)
        link: str | None = event.decision_id
    else:
        assert event.comment is not None  # a direct comment: the plan took it for its words
        comment, truncated = carried_comment_text(source.run_id, event.author_label, event.comment)
        link = None

    with nested_transaction(session):
        claimed = commands.begin(
            session, command_type=CARRY_DECISION_COMMAND_TYPE, idempotency_key=item_idempotency_key(run_id, item),
            fingerprint=payload_fingerprint(payload),
        )
        if isinstance(claimed, CommandReplay):
            replayed = True
        else:
            replayed = False
            appended = record_decision(
                session, finding_uid=target.finding_uid, finding_observation_id=target.observation_id,
                event_type=item.event_type, severity=item.severity, comment=comment, command_id=str(claimed.command_id),
                author_label=author_label, author_user_uid=actor_user_uid, carried_from_decision_id=link,
            )
            commands.succeed(
                session, command_id=claimed.command_id,
                outcome={
                    "decision_id": appended.decision_id, "kind": item.kind, "mode": RESTART_MODE, "run_id": source.run_id,
                    "target_run_id": run_id, "source_decision_id": event.decision_id, "source_finding_uid": source.finding_uid,
                    "target_finding_uid": target.finding_uid, "severity_carried": item.severity is not None,
                },
            )
    # Counted only after the savepoint released: an item that raised is the caller's failure, not a carried event.
    if item.kind == _KIND_VERDICT:
        local.carried_verdicts += 1
        local.severities_skipped += 1 if item.severity_skipped else 0
    else:
        local.carried_comments += 1
        local.truncated_comments += 1 if truncated else 0
    if replayed:
        local.replayed += 1
    else:
        local.appended += 1


def _carry_target(
    session_factory: Callable[[], Session], commands: "CommandRepository", *, run_id: str, items: Sequence[CarryItem],
    actor_user_uid: str, author_label: str,
) -> _Tally:
    """Carry every item of one target finding in one transaction: the finding locked, an expert's own events respected, each item in a savepoint."""
    local = _Tally()
    target = items[0].target
    try:
        with session_factory() as session:
            # `appendDecision` on the finding takes a key-share lock through the event's foreign key: it waits for this transaction,
            # and what is read below cannot be overtaken by an expert's decision before the carried one is appended.
            session.execute(_LOCK_TARGET, {"finding_uid": target.finding_uid})
            if session.execute(
                _FOREIGN_EVENT, {"finding_uid": target.finding_uid, "command_type": CARRY_DECISION_COMMAND_TYPE},
            ).first() is not None:
                local.already_decided += 1
                return local
            kept = _Tally()
            for item in items:
                try:
                    _carry_item(
                        session, commands, run_id=run_id, item=item, actor_user_uid=actor_user_uid, author_label=author_label,
                        local=kept,
                    )
                except Exception as exc:  # noqa: BLE001 - one item's failure (the memory port's included) must not stop the batch
                    kept.failures += 1
                    kept.details.append(
                        f"{item.kind}:{item.source_event.decision_id}->{target.finding_uid}: {type(exc).__name__}: {exc}"
                    )
                    _log.warning(
                        "restart_carry_item_failed run=%s kind=%s source_decision=%s target_finding=%s error=%s: %s",
                        run_id, item.kind, item.source_event.decision_id, target.finding_uid, type(exc).__name__, exc,
                    )
            session.commit()
            local.merge(kept)
    except Exception as exc:  # noqa: BLE001 - the transaction itself (connect, lock, commit) failed: nothing of this target is known carried
        local = _Tally(failures=len(items), details=[f"target:{target.finding_uid}: {type(exc).__name__}: {exc}"])
        _log.warning(
            "restart_carry_target_failed run=%s target_finding=%s items=%d error=%s: %s",
            run_id, target.finding_uid, len(items), type(exc).__name__, exc,
        )
    return local


def _write_marker(session_factory: Callable[[], Session], commands: "CommandRepository", report: RestartCarryReport) -> None:
    """Record that the carry of ``report.run_id`` is complete. Two callers that finish together write one marker; the other finds it."""
    from auditmanager.ingest.public import CommandReplay, payload_fingerprint

    with session_factory() as session:
        try:
            claimed = commands.begin(
                session, command_type=CARRY_RUN_COMMAND_TYPE, idempotency_key=marker_idempotency_key(report.run_id),
                fingerprint=payload_fingerprint({"command": "carry_restart_run.v1", "run_id": report.run_id}),
            )
            if isinstance(claimed, CommandReplay):
                return
            commands.succeed(session, command_id=claimed.command_id, outcome=report.marker_outcome())
            session.commit()
        except DomainError as exc:
            if exc.code is ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS:
                return  # the other caller is committing exactly this marker
            raise


def carry_restart_decisions(
    session_factory: Callable[[], Session], *, run_id: str, actor_user_uid: str,
) -> RestartCarryReport:
    """Carry the decisions of ``run_id``'s lineage to the findings of ``run_id`` that match verbatim (`R-155b`). Idempotent.

    ``run_id`` must be a restart run (``restart_point`` set) that published (``published`` or ``partial``); anything else is a ``conflict``
    refused before anything is read or written, and an unknown run or account is ``not_found``. ``actor_user_uid`` is the restart's
    ``started_by_user_uid``: the author of every carried event. ``session_factory`` is a callable returning a ``Session`` (a
    ``sessionmaker``); the carry opens its own sessions and commits them -- one per target finding, so a failure of one leaves the others --
    and the caller holds no transaction open across it.

    A repeat appends nothing (each carried event has its own command key, see the module docstring) and answers the same totals; a call that
    finds the run's marker answers it and reads nothing else. A call with failures writes no marker and returns them in the report; the
    next call retries exactly the items that are not carried. See the module docstring for the matching rules and for what is left alone.
    """
    from auditmanager.ingest.public import CommandRepository

    _validated(run_id, RunId, "run_id")
    _validated(actor_user_uid, UserUid, "actor_user_uid")

    with session_factory() as session:
        _read_run(session, run_id)
        marker = _read_marker(session, run_id)
        if marker is not None:
            return RestartCarryReport.from_marker(run_id, marker)
        author_label = _author_label(session, actor_user_uid)
        lineage = tuple(str(value) for value in session.execute(_LINEAGE, {"run_id": run_id, "max_depth": _MAX_LINEAGE}).scalars())
        findings = _read_findings(session, [run_id, *lineage])
        events = _read_events(session, [finding.finding_uid for finding in findings if finding.run_id != run_id])

    plan = plan_restart_carry(target_run_id=run_id, lineage_run_ids=lineage, findings=findings, events=events)

    by_target: dict[str, list[CarryItem]] = {}
    for item in plan.items:
        by_target.setdefault(item.target.finding_uid, []).append(item)
    commands = CommandRepository()  # its state-machine topology is read once and shared by every command below
    total = _Tally()
    for target_uid in sorted(by_target):
        total.merge(_carry_target(
            session_factory, commands, run_id=run_id, items=by_target[target_uid], actor_user_uid=actor_user_uid,
            author_label=author_label,
        ))

    report = RestartCarryReport(
        run_id=run_id, lineage=lineage, sources_decided=plan.sources_decided, carried_verdicts=total.carried_verdicts,
        carried_comments=total.carried_comments, appended=total.appended, replayed=total.replayed,
        severities_skipped=total.severities_skipped, unmatched_decisions=plan.unmatched_decisions, ties_skipped=plan.ties_skipped,
        already_decided=total.already_decided, withdrawn=plan.withdrawn, truncated_comments=total.truncated_comments,
        failures=total.failures, failure_details=tuple(total.details),
    )
    if report.failures:
        return report
    complete = replace(report, complete=True)
    _write_marker(session_factory, commands, complete)
    return complete
