"""Restart an ended run from one of the eight stage chips (`RUN-RESTART-01`, owner rulings `R-155a`..`R-155i`).

A restart is a **new** run of the earlier run's document version that takes everything before the chosen chip from the source chain with no new
paid call and computes the chip and everything after it (``docs/program/tasks/RUN-RESTART-01.md``). This module is the one place that knows

* the eight chips and which procedures of the extended review each stands for (:data:`RESTART_POINTS`, :func:`replay_rows`);
* what is *taken* (stage artifacts by reference, the saved text observations byte for byte, the model replies of the rows before the chip)
  and what is *computed* (:class:`RestartSpec`);
* the chain a reply is looked for in (:func:`restart_chain`) and the lineage a publication tombstones (:func:`lineage_of`, :func:`replaced_by`);
* the refusals, typed as ``analysis_input_invalid`` with ``reason`` and ``restart_point`` (:func:`refusal`), and the one exception the
  workflow raises when a replay cannot be made (:class:`RestartRefused`).

Nothing here calls a model, writes a row or reads a blob's bytes; the callers (``runs.commands.restart_run``, ``runs.executor``,
``runs.preflight``) own the writes.

The chain, the lineage and the tombstones
-----------------------------------------
A restart of a run that is itself a failed or cancelled restart is allowed; its source is that run. The **chain** of a run is the run, its restart
source, that source's own restart source and so on, up to the run that is no restart (:func:`restart_chain`). Replies are looked for along it, the
run's own first (``runs.restart.chain_unit`` through ``jobs.extended_review``). The **lineage** of a run is every run whose chain ends at the same
root (:func:`lineage_of`).

When a restart run R publishes (``published`` or ``partial``, `R-155g`) exactly one run of its lineage stays listed -- R: its direct source is
tombstoned with R's own command (the database guard ``trg_audit_run_deletion_by_restart`` of migration 0071 admits that and nothing else), and every
other run of the lineage that has not been tombstoned and has ended without a published result (R's earlier ancestors and the failed or cancelled
sibling restarts) with a plain ``delete_audit_run`` command record of its own whose outcome names R (:func:`tombstone_lineage`). A lineage member
that has not ended, or that published, is left alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.runs.repository import RunRepository, RunRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

#: The eight chips of the run screen, in the order the rail draws them (the contract's ``RestartPoint``).
RESTART_POINTS: Final[tuple[str, ...]] = (
    "preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction",
)

#: The contract stage id or extended-review procedure id each chip covers (``details.stage_id`` of a refusal).
STAGE_OF_POINT: Final[Mapping[str, str]] = {
    "preparation": "source_preparation", "text": "text_analysis", "blocks": "block_analysis",
    "cross_check": "comprehensive_analysis", "merge": "finding_merge", "norms": "norm_verification",
    "review": "finding_review", "correction": "finding_correction",
}

#: The row of the stage layout whose model calls a chip makes. ``preparation`` and ``merge`` make none; ``text`` is the text stage, which a
#: restart takes by reference instead of replaying (it is not a call of the extended review).
ROW_OF_POINT: Final[Mapping[str, str]] = {
    "text": "text", "blocks": "blocks", "cross_check": "cross_check", "norms": "norms", "review": "review", "correction": "correction",
}
POINT_OF_ROW: Final[Mapping[str, str]] = {row: point for point, row in ROW_OF_POINT.items()}

#: The extended-review procedure whose status a kept chip must have reached (the metric ``extended_<id>`` of the text row).
PROCEDURE_OF_POINT: Final[Mapping[str, str]] = {
    "blocks": "block_analysis", "cross_check": "comprehensive_analysis", "merge": "finding_merge", "norms": "norm_verification",
    "review": "finding_review",
}
#: A kept procedure that ended in one of these states made the calls its successors depend on, or none at all by its own account; any other
#: state (``failed``, ``running``, ``queued``, ``skipped``) left calls unmade that a replay would have to take.
_PROCEDURE_REACHED_ITS_END: Final[frozenset[str]] = frozenset({"completed", "partial", "unavailable"})

#: ``analysis_input_invalid.reason`` of each refusal (the closed set of contract 1.59.0).
REASON_NOT_STAGE_LAYOUT: Final[str] = "restart_source_not_stage_layout"
REASON_NOT_V2: Final[str] = "restart_source_not_v2"
REASON_SETTINGS_DIFFER: Final[str] = "restart_settings_differ"
REASON_TEXT_NOT_REUSABLE: Final[str] = "restart_text_not_reusable"
REASON_REPLY_MISSING: Final[str] = "restart_reply_missing"
REASON_REQUEST_CHANGED: Final[str] = "restart_request_changed"
REASONS: Final[tuple[str, ...]] = (
    REASON_NOT_STAGE_LAYOUT, REASON_NOT_V2, REASON_SETTINGS_DIFFER, REASON_TEXT_NOT_REUSABLE, REASON_REPLY_MISSING,
    REASON_REQUEST_CHANGED,
)

#: ``conflict_reason`` of the three 409 refusals.
CONFLICT_SOURCE_DELETED: Final[str] = "restart_source_deleted"
CONFLICT_SOURCE_LEASED: Final[str] = "restart_source_leased"
CONFLICT_IN_PROGRESS: Final[str] = "restart_in_progress"

#: The states of a source a restart may start from (`R-155a`): a run that ended without a published result.
RESTARTABLE_STATES: Final[frozenset[str]] = frozenset({"partial", "failed", "cancelled"})
#: The states a restart run ends in when it replaces its source (`R-155g`).
REPLACING_STATES: Final[frozenset[str]] = frozenset({"published", "partial"})
_ACTIVE_STATES: Final[tuple[str, ...]] = ("created", "queued", "running", "validating")
_MAX_CHAIN: Final[int] = 256


def require_restart_point(point: Any) -> str:
    """The chip of a restart, or ``validation_failed`` on ``restart_point`` (nothing is read or written)."""
    if not isinstance(point, str) or point not in RESTART_POINTS:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="restart_point", constraint="restart_point_unknown")
    return point


def refusal(reason: str, point: str | None = None) -> DomainError:
    """``analysis_input_invalid`` with the reason and, where the refusal belongs to one chip, ``restart_point`` and ``stage_id``."""
    if point is None:
        return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason=reason)
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id=STAGE_OF_POINT[point], reason=reason, restart_point=point)


class RestartRefused(Exception):
    """A replay of a restart that cannot be made, raised inside the extended review (`RUN-RESTART-01`).

    **Not a** ``DomainError``, a ``ValueError``, a ``TypeError`` or a ``KeyError``, on purpose: the v2 workflow catches every one of those and saves its
    partial result, after which the evidence gate would still publish it. A restart that cannot take a reply fails the new run instead -- the
    executor catches this, fails the text stage with :meth:`domain_error` and publishes nothing. ``restart_point`` is the first chip whose work cannot
    be taken from the source chain.
    """

    def __init__(self, reason: str, restart_point: str) -> None:
        super().__init__(f"{reason} at {restart_point}")
        self.reason = reason
        self.restart_point = restart_point

    def domain_error(self) -> DomainError:
        return refusal(self.reason, self.restart_point)


def chips_before(point: str) -> tuple[str, ...]:
    return RESTART_POINTS[: RESTART_POINTS.index(point)]


def chips_from(point: str) -> tuple[str, ...]:
    return RESTART_POINTS[RESTART_POINTS.index(point):]


def replay_rows(point: str) -> frozenset[str]:
    """The rows of the stage layout whose model calls may **only** be replayed: those of the chips before ``point`` (never ``text``, which is taken by
    reference). The calls of ``point``'s own row and of every later one are computed and never look in the chain."""
    index = RESTART_POINTS.index(point)
    return frozenset(row for chip, row in ROW_OF_POINT.items() if chip != "text" and RESTART_POINTS.index(chip) < index)


def untaken_rows(point: str) -> frozenset[str]:
    """The rows that make **no** model call in a restart from ``point``: every row before it (the text row included) -- priced at zero."""
    index = RESTART_POINTS.index(point)
    return frozenset(row for chip, row in ROW_OF_POINT.items() if RESTART_POINTS.index(chip) < index)


def takes_preparation(point: str) -> bool:
    """Whether the three preparation stages are taken by reference (everything but a full rerun)."""
    return point != "preparation"


def takes_text(point: str) -> bool:
    """Whether the saved text observations are taken byte for byte: the chips after ``text``."""
    return RESTART_POINTS.index(point) > RESTART_POINTS.index("text")


@dataclass(frozen=True, slots=True)
class RestartSpec:
    """What a restart run takes and computes, read from its own row.

    ``ancestors`` is the chain the replies are looked for in after the run's own rows: the restart source, its restart source and so on, nearest
    first. ``None`` of this exists for a run that is no restart.
    """

    point: str
    source_run_id: str
    ancestors: tuple[str, ...]
    replay: frozenset[str]

    def replays_row(self, row: str | None) -> bool:
        return row is not None and row in self.replay


def spec_of(session: Session, run: RunRow) -> RestartSpec | None:
    """The restart spec of ``run``, or ``None`` when it is not a restart."""
    point = getattr(run, "restart_point", None)
    if point is None:
        return None
    chain = restart_chain(session, run.run_id)
    return RestartSpec(point=point, source_run_id=str(run.started_from_run_id), ancestors=tuple(chain[1:]), replay=replay_rows(point))


# --- the chain and the lineage -----------------------------------------------------------------------------------------------------

_SELECT_STEP = text("SELECT started_from_run_id FROM audit_run WHERE run_id = :run_id AND restart_point IS NOT NULL")


def restart_chain(session: Session, run_id: str) -> list[str]:
    """``[run_id, its restart source, that source's restart source, ...]``, nearest first, ending at the first run that is no restart (included).

    A cycle is impossible (a source exists before its restart); the bound is a guard against a corrupted row, never a limit a real chain reaches."""
    chain = [run_id]
    while len(chain) < _MAX_CHAIN:
        source = session.execute(_SELECT_STEP, {"run_id": chain[-1]}).scalar_one_or_none()
        if source is None:
            break
        chain.append(str(source))
    return chain


_SELECT_LINEAGE = text(
    """
    WITH RECURSIVE lineage (run_id) AS (
        SELECT CAST(:root AS text)
        UNION
        SELECT r.run_id FROM audit_run r JOIN lineage l ON r.started_from_run_id = l.run_id AND r.restart_point IS NOT NULL
    )
    SELECT r.run_id, r.state, r.restart_point, r.started_from_run_id,
           EXISTS (SELECT 1 FROM audit_run_deletion d WHERE d.run_id = r.run_id) AS tombstoned
      FROM audit_run r JOIN lineage l ON l.run_id = r.run_id
     ORDER BY r.created_at, r.run_id
    """
)


@dataclass(frozen=True, slots=True)
class LineageMember:
    run_id: str
    state: str
    restart_point: str | None
    started_from_run_id: str | None
    tombstoned: bool


def lineage_of(session: Session, run_id: str) -> tuple[LineageMember, ...]:
    """Every run whose restart chain ends where ``run_id``'s does, oldest first (the root, then its restarts and theirs)."""
    root = restart_chain(session, run_id)[-1]
    return tuple(
        LineageMember(str(row[0]), str(row[1]), None if row[2] is None else str(row[2]), None if row[3] is None else str(row[3]), bool(row[4]))
        for row in session.execute(_SELECT_LINEAGE, {"root": root}).all()
    )


def lineage_restart_active(session: Session, run_id: str) -> bool:
    """Whether a restart of any run of the lineage has not ended: one active restart per lineage, so two never race to replace it."""
    return any(member.restart_point is not None and member.state in _ACTIVE_STATES for member in lineage_of(session, run_id))


_SELECT_DIRECT_REPLACEMENT = text(
    "SELECT r.run_id FROM audit_run_deletion d JOIN audit_run r ON r.command_id = d.command_id AND r.restart_point IS NOT NULL "
    "WHERE d.run_id = :run_id"
)
_SELECT_LIVE_LEASE = text(
    "SELECT 1 FROM job j LEFT JOIN lease l ON l.job_id = j.job_id AND l.released_at IS NULL "
    "LEFT JOIN attempt a ON a.attempt_id = j.current_attempt_id AND a.state IN ('created', 'leased', 'running') "
    "WHERE j.run_id = :run_id AND (l.lease_id IS NOT NULL OR a.attempt_id IS NOT NULL) LIMIT 1"
)


def source_command_outcome(session: Session, run: RunRow) -> Mapping[str, Any]:
    """The outcome of the command that created ``run`` (its accepted cost consent, its ``relaxed_limits``), or an empty mapping for a run no
    command made."""
    if run.command_id is None:
        return {}
    from auditmanager.shared.identity import CommandId

    return CommandRepository().get(session, CommandId.parse(run.command_id)).outcome or {}


def has_live_lease(session: Session, run_id: str) -> bool:
    """Whether the work of the run still holds a lease or a live Attempt (it has not stopped yet)."""
    return session.execute(_SELECT_LIVE_LEASE, {"run_id": run_id}).first() is not None


def _next_replacement(session: Session, run_id: str, repository: RunRepository) -> str | None:
    """The run that took the place of one tombstoned run in one step (see :func:`replaced_by`), or ``None``."""
    if not repository.is_deleted(session, run_id):
        return None
    direct = session.execute(_SELECT_DIRECT_REPLACEMENT, {"run_id": run_id}).scalar_one_or_none()
    if direct is not None:
        return str(direct)
    for member in lineage_of(session, run_id):
        if member.restart_point is not None and member.state in REPLACING_STATES and not member.tombstoned:
            return member.run_id
    return None


def replaced_by(session: Session, run_id: str, *, runs: RunRepository | None = None) -> str | None:
    """The run that replaced a tombstoned run, or ``None`` (not tombstoned, a plain deletion that replaced nothing, a source whose restart has not
    published).

    Two rules, in this order: the run whose ``command_id`` is the tombstone's (the direct source of a restart that published, migration 0071); else,
    for a tombstoned run of a restart lineage, the one run of the lineage that is a restart, ended ``published`` or ``partial`` and is itself not
    tombstoned (the earlier ancestors and the failed or cancelled siblings, which :func:`tombstone_lineage` deleted with commands of their own). A
    run outside every restart lineage and deleted plainly has neither, so a plain ``deleteRun`` replaces nothing.

    The answer is the run that **stands**: a replacement that was itself replaced later (a restart of a restart, each of which published) is followed to
    the run that replaced it, so a reader of the oldest run is led to the one that is listed."""
    repository = runs or RunRepository()
    found = _next_replacement(session, run_id, repository)
    hops = 0
    while found is not None and repository.is_deleted(session, found) and hops < _MAX_CHAIN:
        following = _next_replacement(session, found, repository)
        if following is None:
            break
        found, hops = following, hops + 1
    return found


def tombstone_lineage(
    session: Session, *, run: RunRow, runs: RunRepository | None = None, commands: CommandRepository | None = None,
) -> tuple[str, ...]:
    """The publication of restart run ``run`` (``published`` or ``partial``) deletes what it replaces, in the transaction that moved its state.

    The direct source is tombstoned with the restart's own command (the guarded path); every other run of the lineage that has not been tombstoned
    and has ended ``partial``, ``failed`` or ``cancelled`` is tombstoned with a ``delete_audit_run`` command record of its own, keyed by the
    restart and the run, whose outcome says which run replaced it. A member that is active, or published, stays. Idempotent: a run already
    tombstoned is skipped and a repeated call writes nothing new. Returns the run ids it tombstoned, the direct source first."""
    repository = runs or RunRepository()
    ledger = commands or CommandRepository()
    if run.restart_point is None or run.started_from_run_id is None or run.command_id is None or run.started_by_user_uid is None:
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="a run that replaces another is made by a restart command")
    if run.state not in REPLACING_STATES:
        raise DomainError(ErrorCode.STATE_TRANSITION_NOT_ALLOWED, machine="audit_run", current_state=run.state, requested_state="restart_replace")
    done: list[str] = []
    source = str(run.started_from_run_id)
    if not repository.is_deleted(session, source):
        repository.record_deletion(session, run_id=source, user_uid=str(run.started_by_user_uid), command_id=str(run.command_id))
        done.append(source)
    for member in lineage_of(session, run.run_id):
        if member.run_id in {run.run_id, source} or member.tombstoned or member.state not in RESTARTABLE_STATES:
            continue
        claimed = ledger.begin(
            session, command_type="delete_audit_run",
            idempotency_key=IdempotencyKey(f"restart-lineage-{run.run_id}-{member.run_id}"),
            fingerprint=payload_fingerprint({"run_id": member.run_id, "replaced_by_run_id": run.run_id}),
        )
        if isinstance(claimed, CommandReplay) or not isinstance(claimed, CommandStarted):
            continue
        repository.record_deletion(session, run_id=member.run_id, user_uid=str(run.started_by_user_uid), command_id=str(claimed.command_id))
        ledger.succeed(session, claimed.command_id, {"run_id": member.run_id, "replaced_by_run_id": run.run_id})
        done.append(member.run_id)
    return tuple(done)


# --- the replies a restart takes ---------------------------------------------------------------------------------------------------

_SELECT_CHAIN_CALLS = text(
    """
    SELECT run_id, parameters ->> 'extended_phase' AS phase, parameters ->> 'extended_unit_key' AS unit_key, status,
           (parameters ? 'extended_reply_blob_id') AS has_reply
      FROM model_call
     WHERE run_id = ANY(:run_ids) AND parameters ? 'extended_phase'
    """
)


@dataclass(frozen=True, slots=True)
class ChainCalls:
    """The model calls the chain's runs made in the extended review, by the row of their phase."""

    #: ``row -> number of calls`` (the most any one run of the chain made for the row: a replay writes no call row, so the run that made the call
    #: holds it, and a restart that computed the row again holds its own count -- never a sum, which would count a call and its replay twice).
    calls_by_row: Mapping[str, int]
    #: ``row -> identities`` that no run of the chain answered: a call that failed (or whose outcome is unknown) and has no successful sibling of the
    #: same identity. A replay would have to make it, and a replay makes no call.
    unanswered_by_row: Mapping[str, frozenset[str]]


def _row_of_extended_phase(phase: str) -> str | None:
    from auditmanager.runs.stage_layout import row_of_phase

    identity = phase.split(":", 1)[1] if phase.startswith(("v2:", "v3:")) else phase
    return row_of_phase(identity)


def chain_calls(session: Session, chain: Sequence[str]) -> ChainCalls:
    """Read the extended-review calls of ``chain`` (``restart_chain`` of the source), grouped by row."""
    per_run: dict[tuple[str, str], int] = {}
    answered: dict[str, set[str]] = {}
    asked: dict[str, set[str]] = {}
    for row in session.execute(_SELECT_CHAIN_CALLS, {"run_ids": list(chain)}).mappings():
        phase = str(row["phase"])
        owner = _row_of_extended_phase(phase)
        if owner is None:
            continue
        key = (str(row["run_id"]), owner)
        per_run[key] = per_run.get(key, 0) + 1
        asked.setdefault(owner, set()).add(phase)
        if bool(row["has_reply"]) and str(row["status"]) in {"succeeded", "truncated"}:
            answered.setdefault(owner, set()).add(phase)
    counts: dict[str, int] = {}
    for (_run, owner), number in per_run.items():
        counts[owner] = max(counts.get(owner, 0), number)
    return ChainCalls(
        counts,
        {owner: frozenset(asked[owner] - answered.get(owner, set())) for owner in asked if asked[owner] - answered.get(owner, set())},
    )


_SELECT_UNAVAILABLE_REPLIES = text(
    """
    SELECT DISTINCT m.parameters ->> 'extended_phase'
      FROM model_call m
      LEFT JOIN blob b ON b.blob_id = m.parameters ->> 'extended_reply_blob_id'
     WHERE m.run_id = ANY(:run_ids) AND m.parameters ? 'extended_phase' AND m.parameters ? 'extended_reply_blob_id'
       AND m.status IN ('succeeded', 'truncated') AND (b.blob_id IS NULL OR b.state <> 'available')
    """
)


def rows_with_unavailable_replies(session: Session, chain: Sequence[str]) -> frozenset[str]:
    """The rows of the stage layout one of whose saved reply blobs the chain still names but the store no longer holds as ``available``: a replay of it
    would find the row and fail to read the reply, so the chip is refused as ``restart_reply_missing`` before anything is queued."""
    rows = {_row_of_extended_phase(str(phase)) for phase in session.execute(_SELECT_UNAVAILABLE_REPLIES, {"run_ids": list(chain)}).scalars()}
    return frozenset(row for row in rows if row is not None)


def kept_procedures_reached_their_end(point: str, metrics: Mapping[str, Any]) -> str | None:
    """The first kept chip whose procedure did not reach its end in the source's saved extended review, or ``None``.

    ``metrics`` is the text row's scalar metrics (``extended_<procedure id>``: the status each procedure was last saved in). A kept chip with no
    such metric is a procedure the source never started (its review did not get that far): a replay would take replies that do not exist."""
    for chip in chips_before(point):
        procedure = PROCEDURE_OF_POINT.get(chip)
        if procedure is None:
            continue
        if str(metrics.get("extended_" + procedure)) not in _PROCEDURE_REACHED_ITS_END:
            return chip
    return None


__all__ = [
    "CONFLICT_IN_PROGRESS",
    "CONFLICT_SOURCE_DELETED",
    "CONFLICT_SOURCE_LEASED",
    "ChainCalls",
    "LineageMember",
    "POINT_OF_ROW",
    "PROCEDURE_OF_POINT",
    "REASONS",
    "REASON_NOT_STAGE_LAYOUT",
    "REASON_NOT_V2",
    "REASON_REPLY_MISSING",
    "REASON_REQUEST_CHANGED",
    "REASON_SETTINGS_DIFFER",
    "REASON_TEXT_NOT_REUSABLE",
    "REPLACING_STATES",
    "RESTARTABLE_STATES",
    "RESTART_POINTS",
    "ROW_OF_POINT",
    "RestartRefused",
    "RestartSpec",
    "STAGE_OF_POINT",
    "chain_calls",
    "chips_before",
    "chips_from",
    "has_live_lease",
    "kept_procedures_reached_their_end",
    "lineage_of",
    "lineage_restart_active",
    "refusal",
    "replaced_by",
    "replay_rows",
    "require_restart_point",
    "restart_chain",
    "rows_with_unavailable_replies",
    "source_command_outcome",
    "spec_of",
    "takes_preparation",
    "takes_text",
    "tombstone_lineage",
    "untaken_rows",
]
