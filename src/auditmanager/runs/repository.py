"""The ``audit_run`` and ``stage_result`` rows, and the only writer of either.

Every state move goes through :func:`auditmanager.shared.statemachine.assert_transition`
against the topology loaded from ``contract_state_transition`` — the same rows the
``AM001`` trigger consults. The guard refuses an undeclared edge *early*, with the typed
catalog code already attached; the trigger refuses it regardless. There are deliberately
two, and they cannot drift, because neither holds its own copy of the topology.

A refusal that does reach Python from the database is mapped on **SQLSTATE** through the
shared kernel's ``SQLSTATE_TO_CATALOG_CODE``. This module defines no error type of its
own and parses no message text: a message is a diagnostic string a server upgrade or a
locale may reword, and the SQLSTATE is the contract.

What is not here
----------------
No ``Job``, no ``Attempt``, no lease, no heartbeat, no fencing token and no outbox.
Those tables do not exist (P02 §3.1) and PC-01 instantiates none of those aggregates.
There is also no ``succeeded`` run state: the success terminal is ``published``, and
``succeeded`` is a *stage* status. The two vocabularies are separate and this module
keeps them separate.

The ``UPDATE ... WHERE state = :from_state`` pattern is compare-and-set, and every
caller asserts the row actually moved. A zero-row update means somebody else moved the
run first; reporting that as success would be the quiet half of a lost update.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.db import SQLSTATE_TO_CATALOG_CODE
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.statemachine import Topology, assert_initial, assert_transition
from auditmanager.shared.statemachine import load as load_topology

#: The machine name as ``contract_state_transition`` spells it. It matches the table
#: name here, unlike ``command_idempotency``.
RUN_MACHINE: Final[str] = "audit_run"

#: The one state an ``audit_run`` INSERT may create (P02 §3.3).
INITIAL_STATE: Final[str] = "created"

#: The four stages PC-01 drives, in the order the registry's ``depends_on`` declares.
#: Read by the executor and by terminal selection; not a second registry, just the
#: PC-01 subset of one.
PC01_STAGES: Final[tuple[str, ...]] = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
)

_RUN_COLUMNS = (
    "run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, "
    "norms_snapshot_id, provider_mode, frozen_input_digest, command_id, terminal_reason, "
    "interrupted_reason, degradation_set, terminal_at, created_at"
)

_INSERT_RUN = text(
    """
    INSERT INTO audit_run (
        run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id,
        norms_snapshot_id, provider_mode, frozen_input_digest, command_id
    ) VALUES (
        :run_id, :project_uid, :version_uid, :state, :analysis_profile_id,
        :prompt_bundle_id, NULL, :provider_mode, :frozen_input_digest, :command_id
    )
    """
)

_SELECT_RUN = text(f"SELECT {_RUN_COLUMNS} FROM audit_run WHERE run_id = :run_id")

#: `W17VIEW-2`. **`now()` is `transaction_timestamp()`** - one value for the whole
#: transaction, however long it runs. `start_run` creates the run *and* executes it inside
#: a single `self._write(...)`, so `created_at` (a `DEFAULT now()`), every `updated_at`
#: and `terminal_at` were all stamped with the instant the transaction opened. Measured on
#: this lane: a run whose stages really ran `…19.808917 -> …20.047389` reported
#: `created_at == updated_at == terminal_at == …19.797308`, identical to the microsecond,
#: and every duration computed from the API was zero.
#:
#: `statement_timestamp()` is the value that advances between statements of one
#: transaction and is *constant within* a statement - so `_TERMINATE` below stamps
#: `terminal_at` and `updated_at` with one identical value rather than two
#: `clock_timestamp()` readings a microsecond apart.
#:
#: `created_at`'s `DEFAULT now()` is left alone: the INSERT is the first statement of the
#: transaction, so the transaction timestamp *is* when the run was created (11 ms before
#: the first stage started, measured above). It is the two values that must move on later
#: statements that were wrong.
_ADVANCE = text(
    """
    UPDATE audit_run SET state = :to_state, updated_at = statement_timestamp()
    WHERE run_id = :run_id AND state = :from_state
    """
)

_TERMINATE = text(
    """
    UPDATE audit_run
       SET state = :to_state,
           terminal_at = statement_timestamp(),
           updated_at = statement_timestamp(),
           terminal_reason = :terminal_reason,
           interrupted_reason = :interrupted_reason,
           degradation_set = CAST(:degradation_set AS jsonb)
     WHERE run_id = :run_id AND state = :from_state
    """
)

#: `listRuns`. Every run of one published version, newest first -- the same order
#: `listProjects` declares, with the opaque identity as the tiebreaker so the order is
#: total and stable across pages. A run belongs to a version: `start_audit_run` takes a
#: `version_uid` and derives the project from it, so the version is the parent in the
#: create direction and this listing is its inverse.
_LIST_RUNS_FOR_VERSION = text(
    f"SELECT {_RUN_COLUMNS} FROM audit_run WHERE version_uid = :version_uid "
    "ORDER BY created_at DESC, run_id DESC"
)

#: `D-21`. What one run cost, from the `model_call` rows themselves.
#:
#: **Deliberately not from `stage_result.metrics`.** `DEBT_REGISTER.md` `D-15` measures
#: that `metrics["cost_usd"]` is a sum across retry attempts while `metrics["cost_basis"]`
#: describes the *last* response only, so a run that replayed once and then measured
#: publishes a two-attempt sum wearing one attempt's provenance. That pair is left exactly
#: as it is -- repairing it is a design call `D-15` records as not a lane decision -- and
#: this statement reads the per-call rows instead, which `D-15` itself says are exact:
#: "the model-call **records** are exact -- each carries its own basis".
#:
#: Three values, computed in one pass so they cannot disagree with each other:
#:
#: * `calls` -- how many `model_call` rows the sum spans. A reader who cannot see this
#:   cannot tell a one-attempt run from a two-attempt one, which is the very ambiguity
#:   `D-15` is about, so it is published rather than inferred.
#: * `cost_micros` -- the sum, in the stored integer unit. Never a float: the column is
#:   `bigint` millionths and `20260910_0002` says floating point money is not stored.
#: * `unmeasured` -- how many contributing rows are **not** a measured cost, counting a
#:   NULL `cost_micros` as unmeasured too. A NULL contributes nothing to `sum`, so a run
#:   with one NULL row would otherwise publish a short total wearing the word `measured`.
_COST_SUMMARY = text(
    "SELECT count(*) AS calls, "
    "       coalesce(sum(cost_micros), 0) AS cost_micros, "
    "       count(*) FILTER (WHERE cost_micros IS NULL OR cost_basis <> 'measured') "
    "         AS unmeasured "
    "FROM model_call WHERE run_id = :run_id"
)

_STALE_IN_STATE = text(
    f"SELECT {_RUN_COLUMNS} FROM audit_run "
    "WHERE state = :state AND updated_at < now() - CAST(:age AS interval) "
    "ORDER BY updated_at"
)

_UPSERT_STAGE_RESULT = text(
    """
    INSERT INTO stage_result (
        run_id, stage_id, stage_version, status, artifacts, metrics, error,
        started_at, finished_at
    ) VALUES (
        :run_id, :stage_id, :stage_version, :status,
        CAST(:artifacts AS jsonb), CAST(:metrics AS jsonb), CAST(:error AS jsonb),
        :started_at, :finished_at
    )
    ON CONFLICT (run_id, stage_id) DO UPDATE SET
        stage_version = EXCLUDED.stage_version,
        status        = EXCLUDED.status,
        artifacts     = EXCLUDED.artifacts,
        metrics       = EXCLUDED.metrics,
        error         = EXCLUDED.error,
        started_at    = EXCLUDED.started_at,
        finished_at   = EXCLUDED.finished_at
    """
)

#: `W17VIEW-1`. The upsert above has written `started_at` and `finished_at` since the
#: first migration, and this SELECT did not read them back, so the two columns were
#: write-only: the frozen `StageState` declares both, `api/schemas/runs.py` serialises
#: both, and a user was shown `Started -  Finished -` on a run whose rows held real
#: timings. Same shape as `D3` one layer up - a declared, stored, serialisable value
#: with no reader between the row and the response.
_SELECT_STAGE_RESULTS = text(
    "SELECT stage_id, stage_version, status, artifacts, metrics, error, "
    "started_at, finished_at "
    "FROM stage_result WHERE run_id = :run_id ORDER BY stage_id"
)


def translate_refusal(exc: DBAPIError) -> DomainError:
    """Map a database refusal on SQLSTATE, never on message text (P02 §3.2)."""
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
        exc, "code", None
    )
    mapped = SQLSTATE_TO_CATALOG_CODE.get(str(sqlstate)) if sqlstate else None
    if mapped is not None:
        return DomainError(
            ErrorCode(mapped),
            message=f"the database refused the write ({sqlstate})",
        )
    return DomainError(
        ErrorCode.INTERNAL_ERROR, message="the database refused the write"
    )


@dataclass(frozen=True, slots=True)
class RunRow:
    """One ``audit_run`` row, in the shape a caller asserts on."""

    run_id: str
    project_uid: str
    version_uid: str
    state: str
    analysis_profile_id: str
    prompt_bundle_id: str
    norms_snapshot_id: str | None
    provider_mode: str
    frozen_input_digest: str
    command_id: str | None
    terminal_reason: str | None
    interrupted_reason: str | None
    degradation_set: tuple[str, ...]
    #: Required by the frozen `RunStatus`. The column existed in the schema from the first
    #: migration and simply was not selected, so a required API property had no producer.
    created_at: datetime
    terminal_at: datetime | None


@dataclass(frozen=True, slots=True)
class RunCost:
    """What one run spent at the provider, and how well that figure is known.

    ``basis`` is an **aggregate over every contributing call**, and the rule is the
    conservative one: ``measured`` only when every row reports a measured cost, and
    ``estimated`` the moment one does not. The alternative -- reporting the last call's
    basis, which is what ``stage_result.metrics["cost_basis"]`` does -- is the `D-15`
    defect, and inheriting it into a contract would make it permanent.
    """

    model_call_count: int
    cost_micros: int
    basis: str

    @property
    def is_measured(self) -> bool:
        return self.basis == "measured"


@dataclass(frozen=True, slots=True)
class StageResultRow:
    """One persisted ``stage_result`` row."""

    stage_id: str
    stage_version: str
    status: str
    artifacts: tuple[Mapping[str, Any], ...]
    metrics: Mapping[str, Any]
    error: Mapping[str, Any] | None
    #: What the stage actually cost in wall-clock. Declared by the frozen `StageState`,
    #: written by the executor from a Python clock (so these are real per-stage spans and
    #: not one transaction timestamp), and nullable because a row may predate the write.
    started_at: datetime | None = None
    finished_at: datetime | None = None


def _run_row(row: Any) -> RunRow:
    (
        run_id,
        project_uid,
        version_uid,
        state,
        analysis_profile_id,
        prompt_bundle_id,
        norms_snapshot_id,
        provider_mode,
        frozen_input_digest,
        command_id,
        terminal_reason,
        interrupted_reason,
        degradation_set,
        terminal_at,
        created_at,
    ) = tuple(row)
    return RunRow(
        run_id=run_id,
        project_uid=project_uid,
        version_uid=version_uid,
        state=state,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        norms_snapshot_id=norms_snapshot_id,
        provider_mode=provider_mode,
        frozen_input_digest=frozen_input_digest,
        command_id=command_id,
        terminal_reason=terminal_reason,
        interrupted_reason=interrupted_reason,
        degradation_set=tuple(degradation_set or ()),
        terminal_at=terminal_at,
        created_at=created_at,
    )


class RunRepository:
    """Claim, advance and terminate ``audit_run`` rows, and persist stage results."""

    __slots__ = ("_topology",)

    def __init__(self) -> None:
        self._topology: Topology | None = None

    def topology(self, session: Session) -> Topology:
        """The declared topology, read once from the rows the trigger reads."""
        if self._topology is None:
            self._topology = load_topology(session)
        return self._topology

    # -- creation ------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        run_id: str,
        project_uid: str,
        version_uid: str,
        analysis_profile_id: str,
        prompt_bundle_id: str,
        provider_mode: str,
        frozen_input_digest: str,
        command_id: str | None,
    ) -> RunRow:
        """Insert the run in ``created``. The frozen set is written once, here.

        ``norms_snapshot_id`` is written NULL and is read by no PC-01 path: PC-01 pins
        no norms snapshot, which is why the ``NormsSnapshot`` clause of the
        ``created -> queued`` reference-resolution guard is recorded unevaluated under
        ``OD-24``. See :mod:`auditmanager.runs.scope`.
        """
        assert_initial(self.topology(session), RUN_MACHINE, INITIAL_STATE)
        try:
            session.execute(
                _INSERT_RUN,
                {
                    "run_id": run_id,
                    "project_uid": project_uid,
                    "version_uid": version_uid,
                    "state": INITIAL_STATE,
                    "analysis_profile_id": analysis_profile_id,
                    "prompt_bundle_id": prompt_bundle_id,
                    "provider_mode": provider_mode,
                    "frozen_input_digest": frozen_input_digest,
                    "command_id": command_id,
                },
            )
        except DBAPIError as exc:
            raise translate_refusal(exc) from exc
        return self.get(session, run_id)

    # -- reads ---------------------------------------------------------------

    def get(self, session: Session, run_id: str) -> RunRow:
        row = session.execute(_SELECT_RUN, {"run_id": run_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        return _run_row(row)

    def find(self, session: Session, run_id: str) -> RunRow | None:
        row = session.execute(_SELECT_RUN, {"run_id": run_id}).first()
        return None if row is None else _run_row(row)

    def list_for_version(
        self, session: Session, version_uid: str
    ) -> tuple[RunRow, ...]:
        """Every run of one version, newest first.

        No existence check on the version: this repository owns ``audit_run`` and knows
        nothing about ``document_version``. The caller proves the parent exists -- see
        ``RunAdapter.list_runs`` -- because a listing that answered an empty page for an
        unknown version would tell a caller "that document has never been analysed" about
        a document that does not exist.
        """
        rows = session.execute(
            _LIST_RUNS_FOR_VERSION, {"version_uid": version_uid}
        ).all()
        return tuple(_run_row(row) for row in rows)

    def cost(self, session: Session, run_id: str) -> RunCost | None:
        """What this run cost, or ``None`` when it made no provider call at all.

        ``None`` and ``RunCost(0, 0, "measured")`` are different facts and are kept
        different all the way to the wire: a run that never reached the provider has no
        cost to report, while a run that made two calls which both came back free has a
        cost and it is zero. Reporting the first as ``0`` would be the same class of
        invention as `D-3`'s defaulted provenance -- an answer produced for a question
        nothing was asked.
        """
        row = session.execute(_COST_SUMMARY, {"run_id": run_id}).mappings().one()
        calls = int(row["calls"])
        if calls == 0:
            return None
        return RunCost(
            model_call_count=calls,
            cost_micros=int(row["cost_micros"]),
            basis="estimated" if int(row["unmeasured"]) else "measured",
        )

    def stage_results(self, session: Session, run_id: str) -> tuple[StageResultRow, ...]:
        rows = session.execute(_SELECT_STAGE_RESULTS, {"run_id": run_id}).mappings().all()
        return tuple(
            StageResultRow(
                stage_id=row["stage_id"],
                stage_version=row["stage_version"],
                status=row["status"],
                artifacts=tuple(row["artifacts"] or ()),
                metrics=dict(row["metrics"] or {}),
                error=row["error"],
                started_at=row["started_at"],
                finished_at=row["finished_at"],
            )
            for row in rows
        )

    def stage_statuses(self, session: Session, run_id: str) -> dict[str, str]:
        """The map terminal selection consumes. Read back from the persisted rows.

        Deliberately re-read rather than accumulated in memory: the terminal is chosen
        from what was actually persisted, so a stage result that failed to write cannot
        be counted as a success by an in-process tally that never noticed.
        """
        return {
            row.stage_id: row.status for row in self.stage_results(session, run_id)
        }

    def stale_in_state(
        self, session: Session, *, state: str, older_than: str = "1 hour"
    ) -> tuple[RunRow, ...]:
        """Runs sitting in one non-terminal state longer than the threshold.

        `D-20`. There are now two such states, not one. A run is put into ``queued`` by
        the transaction that accepts it and handed to a carrier
        (:mod:`auditmanager.runs.carrier`); the carrier moves it to ``running`` and
        commits before the analysis begins. A process that dies can therefore leave a row
        in either -- ``queued`` if it died between the accepting commit and the worker
        picking the job up, ``running`` if it died during the analysis.

        PC-01 runs one execution in one process, so a row older than the threshold in
        either state means that process is gone. There is no lease and no heartbeat to
        consult: age is the only evidence available, and ``OD-10`` says what to do about
        it rather than inventing an ``interrupted`` state to park it in.
        """
        rows = session.execute(_STALE_IN_STATE, {"state": state, "age": older_than}).all()
        return tuple(_run_row(row) for row in rows)

    def stale_running(
        self, session: Session, *, older_than: str = "1 hour"
    ) -> tuple[RunRow, ...]:
        """The ``running`` half of :meth:`stale_in_state`, kept under its own name."""
        return self.stale_in_state(session, state="running", older_than=older_than)

    # -- transitions ---------------------------------------------------------

    def advance(
        self, session: Session, *, run_id: str, from_state: str, to_state: str
    ) -> None:
        """Move a run along a declared non-terminal edge."""
        assert_transition(self.topology(session), RUN_MACHINE, from_state, to_state)
        try:
            result = session.execute(
                _ADVANCE,
                {"run_id": run_id, "from_state": from_state, "to_state": to_state},
            )
        except DBAPIError as exc:
            raise translate_refusal(exc) from exc
        self._require_moved(result.rowcount, from_state, to_state)

    def terminate(
        self,
        session: Session,
        *,
        run_id: str,
        from_state: str,
        to_state: str,
        degradation_set: Sequence[str] = (),
        terminal_reason: str | None = None,
        interrupted_reason: str | None = None,
    ) -> None:
        """Move a run to a terminal state, recording everything that terminal requires.

        The coupling between ``partial`` and a non-empty ``degradation_set``, and
        between ``published`` and an empty one, is a CHECK constraint in the migration
        and is **not** re-asserted here. A silent degradation cannot reach the success
        terminal because the database refuses it, not because this method remembers to.
        """
        assert_transition(self.topology(session), RUN_MACHINE, from_state, to_state)
        try:
            result = session.execute(
                _TERMINATE,
                {
                    "run_id": run_id,
                    "from_state": from_state,
                    "to_state": to_state,
                    "terminal_reason": terminal_reason,
                    "interrupted_reason": interrupted_reason,
                    "degradation_set": json.dumps(list(degradation_set)),
                },
            )
        except DBAPIError as exc:
            raise translate_refusal(exc) from exc
        self._require_moved(result.rowcount, from_state, to_state)

    # -- stage results -------------------------------------------------------

    def record_stage_result(
        self, session: Session, *, run_id: str, document: Mapping[str, Any]
    ) -> None:
        """Persist one ``StageResult`` document, keyed ``(run_id, stage_id)``.

        ``document`` is ``StageResult.to_document()`` from the analysis seam. Nothing
        is reshaped here beyond the column split, so what is stored is what the stage
        contract declares — including ``error`` being *absent* on success rather than
        ``null``, which the schema distinguishes and the CHECK constraint enforces.
        """
        error = document.get("error")
        try:
            session.execute(
                _UPSERT_STAGE_RESULT,
                {
                    "run_id": run_id,
                    "stage_id": document["stage_id"],
                    "stage_version": document["stage_version"],
                    "status": document["status"],
                    "artifacts": json.dumps(document.get("artifacts", [])),
                    "metrics": json.dumps(document.get("metrics", {})),
                    "error": None if error is None else json.dumps(error),
                    "started_at": document.get("started_at"),
                    "finished_at": document.get("finished_at"),
                },
            )
        except DBAPIError as exc:
            raise translate_refusal(exc) from exc

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _require_moved(rowcount: int, from_state: str, to_state: str) -> None:
        """A compare-and-set that matched no row moved nothing."""
        if rowcount != 1:
            raise DomainError(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine=RUN_MACHINE,
                current_state=from_state,
                requested_state=to_state,
            )


__all__ = [
    "INITIAL_STATE",
    "PC01_STAGES",
    "RUN_MACHINE",
    "RunCost",
    "RunRepository",
    "RunRow",
    "StageResultRow",
    "translate_refusal",
]
