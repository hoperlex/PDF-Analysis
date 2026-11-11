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
Job/Attempt/Lease authority, its lease heartbeat and lease-expiry recovery are
deliberately owned by :mod:`auditmanager.jobs`, not by this run-row repository. Remote
workers and outbox delivery remain absent. There is also no ``succeeded`` run state: the success terminal is ``published``, and
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

from auditmanager.jobs.public import append_execution_event
from auditmanager.precedents.public import one_list_enabled

from auditmanager.shared.db import SQLSTATE_TO_CATALOG_CODE
from auditmanager.shared.errors import DomainError, ErrorCode, screen_details
from auditmanager.shared.statemachine import Topology, assert_initial, assert_transition
from auditmanager.shared.statemachine import load as load_topology

#: The machine name as ``contract_state_transition`` spells it. It matches the table
#: name here, unlike ``command_idempotency``.
RUN_MACHINE: Final[str] = "audit_run"

#: The one state an ``audit_run`` INSERT may create (P02 §3.3).
INITIAL_STATE: Final[str] = "created"

#: `F8-PUBLISH`: the two values of ``audit_run.publication_mode`` (``ck_audit_run_publication_mode``, migration 0064). ``text_only`` is the
#: default and what every run written before 0064 is; ``one_list`` publishes the extended-review candidates that pass gate v2 as well.
PUBLICATION_TEXT_ONLY: Final[str] = "text_only"
PUBLICATION_ONE_LIST: Final[str] = "one_list"
PUBLICATION_MODES: Final[tuple[str, ...]] = (PUBLICATION_TEXT_ONLY, PUBLICATION_ONE_LIST)

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
    "terminal_detail, "
    "interrupted_reason, degradation_set, terminal_at, created_at, reaudit_of_run_id, "
    "connection_revision_id, norm_retrieval_set_id, preset_revision_id, "
    "binding_state, executor_group_revision_id, routing_rule_revision_id, wait_reason, waiting_since, "
    "started_by_user_uid, started_from_run_id, start_stage_id, stage_plan, publication_mode"
)

_INSERT_RUN = text(
    """
    INSERT INTO audit_run (
        run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id,
        norms_snapshot_id, provider_mode, frozen_input_digest, command_id,
        reaudit_of_run_id, connection_revision_id, norm_retrieval_set_id, preset_revision_id,
        binding_state, executor_group_revision_id, routing_rule_revision_id, started_by_user_uid,
        started_from_run_id, start_stage_id, stage_plan, publication_mode
    ) VALUES (
        :run_id, :project_uid, :version_uid, :state, :analysis_profile_id,
        :prompt_bundle_id, :norms_snapshot_id, :provider_mode, :frozen_input_digest, :command_id,
        :reaudit_of_run_id, :connection_revision_id, :norm_retrieval_set_id, :preset_revision_id,
        :binding_state, :executor_group_revision_id, :routing_rule_revision_id, :started_by_user_uid,
        :started_from_run_id, :start_stage_id, CAST(:stage_plan AS jsonb), :publication_mode
    )
    """
)

_SELECT_RUN = text(f"SELECT {_RUN_COLUMNS} FROM audit_run WHERE run_id = :run_id")

#: `HOSTS-LAYOUT-01` (migration 0062): the member each cell of a planned run was bound to at dispatch. Written once, in the transaction that
#: moved the run to ``bound``; the database refuses an update or a delete.
_SELECT_CELL_BINDINGS = text(
    "SELECT cell_key, group_revision_id, connection_revision_id FROM audit_run_cell_binding WHERE run_id = :run_id"
)

#: `EXEC-PAR-START-01`. A run whose executor was **named** by the caller (or by the repeat of
#: such a run) carries exactly one of these events, written in the transaction that created it.
#: The run row holds only the frozen revision, which a routed run has as well, so the event is
#: what tells an explicit choice from a route: ``reaudit_run`` reads it to keep the executor.
EXECUTOR_CHOSEN_EVENT: Final[str] = "audit_run.executor_chosen"

_SELECT_CHOSEN_EXECUTOR = text(
    "SELECT payload ->> 'connection_id' FROM audit_event "
    "WHERE aggregate_type = 'AuditRun' AND aggregate_id = :run_id "
    "AND event_type = :event_type ORDER BY sequence_no LIMIT 1"
)

#: `EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12 and 15). What the execution queue shows of a Run admitted by a rule
#: or a group: its binding state and, while it is ``pending`` and not ended, why it waits. A Run whose executor was
#: frozen at start is not in the answer, so a queue item of an ordinary Run is exactly what it was.
_SELECT_BINDING_FACTS = text(
    "SELECT run_id, binding_state, "
    "CASE WHEN binding_state = 'pending' AND state NOT IN ('published', 'partial', 'failed', 'cancelled') "
    "THEN wait_reason END AS wait_reason "
    "FROM audit_run WHERE run_id = ANY(:run_ids) AND binding_state <> 'frozen_at_start'"
)
#: The terminal path of a Run that waited for an executor and was given none (``no_executor_online``) clears its
#: wait: a finished Run waits for nothing. ``wait_reason`` and ``waiting_since`` are not frozen columns.
_CLEAR_WAIT = text(
    "UPDATE audit_run SET wait_reason = NULL, waiting_since = NULL "
    "WHERE run_id = :run_id AND wait_reason IS NOT NULL"
)

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
           terminal_detail = CAST(:terminal_detail AS jsonb),
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
#:
#: `RUN-DELETE-01` (owner hotfix 2026-11-11): a **deleted** run (a row of ``audit_run_deletion``, a tombstone) is not in this
#: list. It is still stored and ``getRunStatus`` still answers it by its identity (:data:`_SELECT_RUN` has no such condition);
#: only the lists of runs leave it out. Each context that lists runs spells the same condition in its own SQL.
_LIST_RUNS_FOR_VERSION = text(
    f"SELECT {_RUN_COLUMNS} FROM audit_run WHERE version_uid = :version_uid "
    "AND NOT EXISTS (SELECT 1 FROM audit_run_deletion deleted WHERE deleted.run_id = audit_run.run_id) "
    "ORDER BY created_at DESC, run_id DESC"
)

#: The same list with the deleted runs kept in, for the operator's own reading of a run's re-audits (``hotfix_operator.status``): an
#: operator tool shows what is stored, and a tombstone hides a run from the product's lists, not from the operator.
_LIST_RUNS_FOR_VERSION_WITH_DELETED = text(
    f"SELECT {_RUN_COLUMNS} FROM audit_run WHERE version_uid = :version_uid ORDER BY created_at DESC, run_id DESC"
)

#: `RUN-DELETE-01`. The tombstone (migration ``0066_run_deletion``): written once by ``delete_audit_run``, in the transaction that
#: also finishes its command record. The table is immutable, so the statement is the whole write path.
_INSERT_DELETION = text(
    "INSERT INTO audit_run_deletion (run_id, deleted_by_user_uid, command_id) "
    "VALUES (:run_id, :user_uid, :command_id)"
)
_IS_DELETED = text("SELECT EXISTS (SELECT 1 FROM audit_run_deletion WHERE run_id = :run_id)")

#: `D-21`. What one run cost, from the `model_call` rows themselves.
#:
#: **Deliberately not from `stage_result.metrics`.** When this statement was written,
#: `DEBT_REGISTER.md` `D-15` measured that `metrics["cost_usd"]` is a sum over everything
#: the run's one `CostMeter` charged while `metrics["cost_basis"]` described the *last*
#: response only, so a summed figure could wear one contribution's provenance. `R-14` has
#: since ruled that pair onto the rule below, and `W25-COST` moved it there -- the stage
#: asks its meter, which is the only object that sees every contribution. The two places
#: now say the same thing, which was the point of the ruling.
#:
#: This statement still reads the per-call rows rather than the metrics, and that is not
#: redundancy: these rows exist for every run in every state, they survive a run whose
#: stage wrote no metrics at all, and `D-15` itself says they are the exact ones --
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
#:
#: **The run-level cost rule** (`EXEC-HTTP-01`, `R-143`). A call through an unmetered connection
#: has cost basis ``unmetered`` and no figure of its own, but the run did call a provider, so the
#: three fields still move together: when *every* call is unmetered the run reports cost ``0``,
#: basis ``unmetered`` and the call count; when unmetered and metered calls mix it reports the
#: *metered* sum with basis ``estimated`` (a total that leaves calls out is not a measurement of
#: the run). ``unmetered`` counts the first, ``unmeasured`` only the metered rows that are not
#: measured, so the mix is told from a clean measured run.
_COST_SUMMARY = text(
    "SELECT count(*) AS calls, "
    "       coalesce(sum(cost_micros) FILTER (WHERE cost_basis <> 'unmetered'), 0) AS cost_micros, "
    "       count(*) FILTER (WHERE cost_basis = 'unmetered') AS unmetered, "
    "       count(*) FILTER (WHERE cost_basis <> 'unmetered' "
    "         AND (cost_micros IS NULL OR cost_basis <> 'measured')) AS unmeasured "
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
    #: `D-46`. The classifiers that say which dependency, screened against
    #: ``terminal_reason``'s own ``safe_detail_keys``. ``None`` when there is no detail;
    #: never an empty object.
    terminal_detail: Mapping[str, Any] | None
    interrupted_reason: str | None
    degradation_set: tuple[str, ...]
    #: Required by the frozen `RunStatus`. The column existed in the schema from the first
    #: migration and simply was not selected, so a required API property had no producer.
    created_at: datetime
    terminal_at: datetime | None
    #: W53 lineage: the terminal run this one re-audits, or ``None`` for a run started
    #: from a document version. Written once by ``create`` and frozen by the database.
    reaudit_of_run_id: str | None = None
    #: `EXEC-HTTP-01`: the executor connection revision the run froze at start, or ``None`` for
    #: a run of the ``environment`` source. Written once by ``create`` and frozen by the database.
    connection_revision_id: str | None = None
    #: The 0023 immutable verified set pin, present only for a run that pinned a verified retrieval set.
    norm_retrieval_set_id: str | None = None
    #: `ANALYSIS-PRESETS-01`: the analysis-preset revision the run was started with, or ``None``
    #: for a run started by hand, by the route or by a repeat. Written once by ``create`` and
    #: frozen by the database, which also checks that the run froze that preset's connection.
    preset_revision_id: str | None = None
    #: `EXEC2-GROUP-RUN-01` (ADR-0026 decision 12). **What a ``None`` connection revision means.** With
    #: ``frozen_at_start`` it is the ``environment`` provider source: the run froze no connection and is never
    #: limited. With ``pending`` it is a run admitted by a rule or a group that no member has taken yet: the
    #: connection is chosen at dispatch, and a reader that treats it as ``environment`` runs the work on the wrong
    #: source. ``bound`` always has a revision, a member of ``executor_group_revision_id``. The database holds the
    #: shape (``ck_audit_run_binding_shape``); the default is what every row written before ``0048`` is.
    binding_state: str = "frozen_at_start"
    #: The immutable group revision admission froze, and the rule revision when a rule routed the run (``None`` when
    #: the group was named). Both ``None`` for ``frozen_at_start``; written once at INSERT and frozen.
    executor_group_revision_id: str | None = None
    routing_rule_revision_id: str | None = None
    #: Why a ``pending`` run is not dispatched (``executor_at_capacity``, ``runner_offline``, ``needs_reconsent``)
    #: and since when; both ``None`` unless it waits. Not frozen: the dispatcher keeps them.
    wait_reason: str | None = None
    waiting_since: datetime | None = None
    #: `R-151v` (migration 0051): the account whose command created the run; ``None`` before 0051. Frozen.
    started_by_user_uid: str | None = None
    #: `R-151i` (migration 0060): the terminal run whose completed stage outputs this run reuses, and the first stage it
    #: computes itself; both ``None`` for a run started from a version or as a re-audit (never one without the other).
    #: Frozen. Not ``reaudit_of_run_id``: a re-audit recomputes every stage.
    started_from_run_id: str | None = None
    start_stage_id: str | None = None
    #: `HOSTS-LAYOUT-01` (migration 0062, ADR-0028 decision 5): the plan the run froze at its start -- ``stage-plan/1``, one cell per row
    #: it calls with model, effort, limits and access (``runs.stage_layout.parse_plan`` reads it back) -- or ``None`` for a run on the
    #: legacy route. Written once at INSERT and frozen. A run with a plan has no connection, group or preset of its own: it is
    #: ``pending`` until dispatch binds each cell (``audit_run_cell_binding``).
    stage_plan: Mapping[str, Any] | None = None
    #: `F8-PUBLISH` (migration 0064, ADR-0029 decision 7, plan-v5 section 3.6): how the run publishes -- ``text_only`` (the gate publishes text
    #: findings only, as every run did before 0064) or ``one_list`` (the extended-review candidates that pass gate v2 become findings as well).
    #: Written once at INSERT and frozen by the database; ``one_list`` needs a ``stage_plan`` (``ck_audit_run_publication_mode_stage_plan``).
    publication_mode: str = "text_only"


@dataclass(frozen=True, slots=True)
class CellBindingRow:
    """One ``audit_run_cell_binding`` row: the system group revision and the member's connection revision a cell was bound to."""

    cell_key: str
    group_revision_id: str
    connection_revision_id: str


@dataclass(frozen=True, slots=True)
class RunCost:
    """What one run spent at the provider, and how well that figure is known.

    ``basis`` is an **aggregate over every contributing call**, and the rule is the
    conservative one: ``measured`` only when every row reports a measured cost, and
    ``estimated`` the moment one does not. The alternative -- reporting the last call's
    basis -- is the `D-15` defect, and inheriting it into a contract would have made it
    permanent. `stage_result.metrics["cost_basis"]` did exactly that until `R-14`;
    `W25-COST` gave it this same rule, over the contributions to its own figure.
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
        terminal_detail,
        interrupted_reason,
        degradation_set,
        terminal_at,
        created_at,
        reaudit_of_run_id,
        connection_revision_id,
        norm_retrieval_set_id,
        preset_revision_id,
        binding_state,
        executor_group_revision_id,
        routing_rule_revision_id,
        wait_reason,
        waiting_since,
        started_by_user_uid,
        started_from_run_id,
        start_stage_id,
        stage_plan,
        publication_mode,
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
        terminal_detail=terminal_detail or None,
        interrupted_reason=interrupted_reason,
        degradation_set=tuple(degradation_set or ()),
        terminal_at=terminal_at,
        created_at=created_at,
        reaudit_of_run_id=reaudit_of_run_id,
        connection_revision_id=connection_revision_id,
        norm_retrieval_set_id=norm_retrieval_set_id,
        preset_revision_id=preset_revision_id,
        binding_state=binding_state,
        executor_group_revision_id=executor_group_revision_id,
        routing_rule_revision_id=routing_rule_revision_id,
        wait_reason=wait_reason,
        waiting_since=waiting_since,
        started_by_user_uid=started_by_user_uid,
        started_from_run_id=started_from_run_id,
        start_stage_id=start_stage_id,
        stage_plan=stage_plan,
        publication_mode=publication_mode,
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
        reaudit_of_run_id: str | None = None,
        norms_snapshot_id: str | None = None,
        connection_revision_id: str | None = None,
        norm_retrieval_set_id: str | None = None,
        preset_revision_id: str | None = None,
        binding_state: str = "frozen_at_start",
        executor_group_revision_id: str | None = None,
        routing_rule_revision_id: str | None = None,
        started_by_user_uid: str | None = None,
        started_from_run_id: str | None = None,
        start_stage_id: str | None = None,
        stage_plan: Mapping[str, Any] | None = None,
        publication_mode: str | None = None,
    ) -> RunRow:
        """Insert the run in ``created``. The frozen set is written once, here.

        `F8-PUBLISH`: ``publication_mode`` is the marker of how the run publishes (plan-v5 section 3.6). A caller that leaves it ``None``
        gets ``one_list`` exactly when the run has a ``stage_plan`` **and** the latest journalled ``one_list`` switch is on (nothing
        journalled is off), and ``text_only`` otherwise; the switch is read here, once, in the transaction that creates the run, so a
        later change of the switch acts on new runs only. A caller may pass a value of its own (the database refuses ``one_list`` for a
        run without a plan). The database freezes the column, so the mode cannot change after this INSERT.

        ``started_by_user_uid`` (`R-151v`, migration 0051) is the account whose command created the run; frozen.

        ``started_from_run_id`` and ``start_stage_id`` (`R-151i`, migration 0060) are given together by
        ``start_run_from_stage`` and by nothing else: the terminal run whose stage outputs this run reuses and the first
        stage it computes. The executor reads them back from the row; the database refuses one without the other.

        ``norms_snapshot_id`` is the snapshot the creating command pinned
        (`W55A-PIN-01`): ``start_audit_run`` and ``reaudit_run`` read the current one in
        the same transaction and pass it, NULL while none is current. This method
        consults nothing; it writes what it is given, and the default NULL is only for
        callers that build rows outside those two commands.

        The optional 0023 set pin is written at INSERT time only. The database
        requires its row to be verified under the same snapshot. The served
        commands do not supply it until a later integration owns that
        selection and the associated frozen-input digest.

        `EXEC2-GROUP-RUN-01`: a run admitted by a rule or a group is written ``binding_state = 'pending'`` with the
        group revision (and the rule revision when a rule routed it) and **no** connection revision, which the claim
        writes once at dispatch (``ck_audit_run_binding_shape`` refuses any other combination). Every other caller
        leaves the defaults: ``frozen_at_start``, no group, no rule.

        `HOSTS-LAYOUT-01`: ``stage_plan`` (the document :class:`~auditmanager.runs.stage_layout.FrozenStagePlan` writes) is given with
        ``binding_state = 'pending'`` and **no** connection revision, group or preset (``ck_audit_run_binding_shape``); dispatch binds
        every cell, once, before the run goes to ``bound``.
        """
        if norm_retrieval_set_id is not None and norms_snapshot_id is None:
            raise ValueError("a retrieval set pin requires a snapshot pin")
        if publication_mode is None:
            publication_mode = (
                PUBLICATION_ONE_LIST if stage_plan is not None and one_list_enabled(session) else PUBLICATION_TEXT_ONLY
            )
        if publication_mode not in PUBLICATION_MODES:
            raise ValueError(f"{publication_mode!r} is not a publication mode")
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
                    "reaudit_of_run_id": reaudit_of_run_id,
                    "norms_snapshot_id": norms_snapshot_id,
                    "connection_revision_id": connection_revision_id,
                    "norm_retrieval_set_id": norm_retrieval_set_id,
                    "preset_revision_id": preset_revision_id,
                    "binding_state": binding_state,
                    "executor_group_revision_id": executor_group_revision_id,
                    "routing_rule_revision_id": routing_rule_revision_id,
                    "started_by_user_uid": started_by_user_uid,
                    "started_from_run_id": started_from_run_id,
                    "start_stage_id": start_stage_id,
                    "stage_plan": None if stage_plan is None else json.dumps(dict(stage_plan), sort_keys=True),
                    "publication_mode": publication_mode,
                },
            )
        except DBAPIError as exc:
            raise translate_refusal(exc) from exc
        append_execution_event(
            session, event_type="audit_run.created", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id, payload={"state": INITIAL_STATE},
        )
        return self.get(session, run_id)

    # -- reads ---------------------------------------------------------------

    def get(self, session: Session, run_id: str) -> RunRow:
        row = session.execute(_SELECT_RUN, {"run_id": run_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        return _run_row(row)

    def cell_bindings(self, session: Session, run_id: str) -> dict[str, CellBindingRow]:
        """``cell_key -> binding`` of a planned run (empty while it is ``pending``). A planned run is called only through these rows."""
        rows = session.execute(_SELECT_CELL_BINDINGS, {"run_id": run_id}).mappings().all()
        return {row["cell_key"]: CellBindingRow(row["cell_key"], row["group_revision_id"], row["connection_revision_id"]) for row in rows}

    def find(self, session: Session, run_id: str) -> RunRow | None:
        row = session.execute(_SELECT_RUN, {"run_id": run_id}).first()
        return None if row is None else _run_row(row)

    def binding_facts(
        self, session: Session, run_ids: Sequence[str]
    ) -> dict[str, tuple[str, str | None]]:
        """``run_id -> (binding_state, wait_reason)`` for the named Runs admitted by a rule or a group.

        A Run whose executor was frozen at start is absent, so a caller that renders only what is present leaves an
        ordinary Run's reading byte for byte what it was. ``wait_reason`` is ``None`` unless the Run is ``pending``
        and not ended."""
        if not run_ids:
            return {}
        rows = session.execute(_SELECT_BINDING_FACTS, {"run_ids": list(run_ids)}).all()
        return {str(row[0]): (str(row[1]), None if row[2] is None else str(row[2])) for row in rows}

    def clear_wait(self, session: Session, *, run_id: str) -> None:
        """Forget why a Run waited (it ended). Nothing else on the row changes."""
        session.execute(_CLEAR_WAIT, {"run_id": run_id})

    def chosen_executor_connection(self, session: Session, run_id: str) -> str | None:
        """The connection a caller named for this run (`EXEC-PAR-START-01`), or ``None`` when
        the run followed the route. Read from the run's ``audit_run.executor_chosen`` event."""
        found = session.execute(
            _SELECT_CHOSEN_EXECUTOR, {"run_id": run_id, "event_type": EXECUTOR_CHOSEN_EVENT}
        ).scalar_one_or_none()
        return None if found is None else str(found)

    def list_for_version(
        self, session: Session, version_uid: str, *, include_deleted: bool = False
    ) -> tuple[RunRow, ...]:
        """Every run of one version, newest first, without the runs an expert deleted (`RUN-DELETE-01`).

        ``include_deleted`` is for an operator's reading of what is stored; a product list never passes it. Every caller that
        walks "the newest run that ..." (the block index, the portal source, the comparison's run selection) takes the
        default and so never lands on a deleted run.

        No existence check on the version: this repository owns ``audit_run`` and knows
        nothing about ``document_version``. The caller proves the parent exists -- see
        ``RunAdapter.list_runs`` -- because a listing that answered an empty page for an
        unknown version would tell a caller "that document has never been analysed" about
        a document that does not exist.
        """
        statement = _LIST_RUNS_FOR_VERSION_WITH_DELETED if include_deleted else _LIST_RUNS_FOR_VERSION
        rows = session.execute(statement, {"version_uid": version_uid}).all()
        return tuple(_run_row(row) for row in rows)

    def is_deleted(self, session: Session, run_id: str) -> bool:
        """``True`` when the run has a tombstone (`RUN-DELETE-01`). An unknown run has none."""
        return bool(session.execute(_IS_DELETED, {"run_id": run_id}).scalar_one())

    def record_deletion(self, session: Session, *, run_id: str, user_uid: str, command_id: str) -> None:
        """Write the tombstone of a run: it leaves every list of runs, nothing else changes.

        The caller has locked the run row, checked its state and that it has no tombstone yet; the primary key is the
        last word if two callers race, and the database refuses a second row (a ``unique_violation`` the caller never
        sees, because the run row lock serialises them)."""
        session.execute(_INSERT_DELETION, {"run_id": run_id, "user_uid": user_uid, "command_id": command_id})

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
        unmetered = int(row["unmetered"])
        if unmetered == calls:
            return RunCost(model_call_count=calls, cost_micros=0, basis="unmetered")
        return RunCost(
            model_call_count=calls,
            cost_micros=int(row["cost_micros"]),
            basis="estimated" if unmetered or int(row["unmeasured"]) else "measured",
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
        either state means that process is gone. The local Lease has no heartbeat clock,
        so age remains the evidence available; ``OD-10`` says what to do about it rather
        than inventing an ``interrupted`` state to park it in.
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
        append_execution_event(
            session, event_type="audit_run.transition", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id,
            payload={"from_state": from_state, "to_state": to_state},
        )

    def terminate(
        self,
        session: Session,
        *,
        run_id: str,
        from_state: str,
        to_state: str,
        degradation_set: Sequence[str] = (),
        terminal_reason: str | None = None,
        terminal_detail: Mapping[str, Any] | None = None,
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
                    # `D-46`. Screened once more on the way in, against the reason this
                    # very statement writes: the row and the allowlist that bounds it have
                    # to be decided together, or a later reader has nothing to screen
                    # against. An empty result is written as NULL, because "no detail" and
                    # "an empty detail" are the same fact and the column spells it one way.
                    "terminal_detail": (
                        None
                        if not terminal_detail or terminal_reason is None
                        else json.dumps(
                            dict(
                                screen_details(
                                    ErrorCode(terminal_reason), terminal_detail
                                )
                            )
                        )
                    ),
                    "interrupted_reason": interrupted_reason,
                    "degradation_set": json.dumps(list(degradation_set)),
                },
            )
        except DBAPIError as exc:
            raise translate_refusal(exc) from exc
        self._require_moved(result.rowcount, from_state, to_state)
        append_execution_event(
            session, event_type="audit_run.transition", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id,
            payload={"from_state": from_state, "to_state": to_state},
        )

    # -- stage results -------------------------------------------------------

    def stage_started(self, session: Session, *, run_id: str, stage_id: str) -> None:
        append_execution_event(
            session, event_type="stage.started", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id, payload={"stage_id": stage_id},
        )

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
        append_execution_event(
            session, event_type="stage.finished", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id,
            payload={"stage_id": str(document["stage_id"]),
                     "state": str(document["status"])},
        )

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
    "CellBindingRow",
    "EXECUTOR_CHOSEN_EVENT",
    "INITIAL_STATE",
    "PC01_STAGES",
    "PUBLICATION_MODES",
    "PUBLICATION_ONE_LIST",
    "PUBLICATION_TEXT_ONLY",
    "RUN_MACHINE",
    "RunCost",
    "RunRepository",
    "RunRow",
    "StageResultRow",
    "translate_refusal",
]
