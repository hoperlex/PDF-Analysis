"""The sequential in-process executor: one run, four stages, one terminal.

This is the composition point of the whole prototype. Every module it drives already
exists and is merged; nothing here reimplements any of them:

* ``auditmanager.analysis`` — the stage runner and the three deterministic stages;
* ``auditmanager.analysis.text`` — ``text_analysis`` and its two adapters;
* ``auditmanager.findings`` — the grounding gate, publication, and terminal *selection*;
* ``auditmanager.runs.repository`` — the rows and the transition guard.

Two things this module is careful to get right.

**The executor never selects a terminal.** It walks ``created -> queued -> running ->
validating``, calls :func:`auditmanager.findings.select_terminal` at ``validating``, and
records what that returns. There is no branch here that writes ``published``: grep for
the literal and the only occurrences are in a docstring. That ordering is why
``P2-FND-01`` was built before this task — a runner authored against a stub that faked
``published`` would have proved nothing.

**State is persisted before execution, not after.** The run row exists in ``created``
before this function is entered (the command handler put it there), and each
``StageResult`` is written as its stage finishes rather than accumulated and flushed at
the end. A process killed mid-run therefore leaves a truthful partial record plus a
``running`` row that reconciliation can find, instead of a run that claims to have done
nothing.

The one adaptation
------------------
``text_analysis`` is declared by the registry but is not in ``B2``'s ``HANDLERS`` map,
by design: ``analysis/text/stage.py`` says the binding of :class:`TextAnalysisOutcome`
onto a ``StageResult`` "belongs to whoever composes the two". That is this module, and
:func:`_run_text_analysis_stage` is the whole of it. It cannot go through
:func:`run_stage` because a ``StageHandler`` returns a ``StageProduction``, which has no
status field — and ``text_analysis`` is the one PC-01 stage whose registry policy allows
``partial``. Routing it through the runner would silently flatten ``partial`` into
``succeeded``, which is precisely the silent degradation the whole design is arranged to
prevent.

No ``Job``, no ``Attempt``, no lease, no heartbeat, no fencing token, no resume, no
retry and no outbox. One execution per run, in one process.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    ArtifactRef,
    StageError,
    StageResult,
    StageStatus,
    read_artifact,
    run_stage,
)
from auditmanager.analysis.ports.artifacts import publish_artifact
from auditmanager.analysis.text import (
    AR_TEXT_PROFILE,
    ARTIFACT_ROLE as ROLE_TEXT_OBSERVATIONS,
    ModelAdapter,
    ModelCallRecord,
    ProviderConfig,
    TextAnalysisOutcome,
    run_text_analysis,
)
from auditmanager.analysis.text.stage import STAGE_VERSION as TEXT_STAGE_VERSION
from auditmanager.documents import DocumentRepository
from auditmanager.findings import (
    BlockIndex,
    ObservationSet,
    PublicationResult,
    TerminalSelection,
    TextLayer,
    publish_gate_result,
    run_grounding_gate,
    select_terminal,
)
from auditmanager.runs.repository import PC01_STAGES, RunRepository, RunRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId, VersionUid
from auditmanager.storage import BlobStore
from auditmanager.storage.models import parse_blob_id

#: The two vocabularies now agree, so nothing is mapped. ``analysis.text`` reports one of
#: ``succeeded|truncated|failed`` for a provider call and migration ``0005`` makes
#: ``model_call.status`` hold exactly those three, so the status is written through
#: unchanged. What stood here before was a map collapsing ``truncated`` onto ``succeeded``,
#: kept lossless by stashing the real stop reason in ``parameters.call_status`` — a
#: workaround adopted because the CHECK would have refused the row, and recorded as such in
#: ``GATE_B2_CLOSURE.md`` §5.3. It cost the ledger the one distinction the PC-02 report
#: needs: a reply cut short at the output ceiling is a different product fact from a clean
#: answer, and the run it belongs to is ``partial`` rather than ``published``.
#:
#: ``parameters.call_status`` is still written. It is now redundant for a new row and it is
#: deliberately kept, because it is the *only* thing that lets a row written before ``0005``
#: be read back correctly, and a key that disappears from new rows would leave the reader
#: unable to tell an old truncated call from an old clean one.
#:
#: A ``truncated`` row carries **no** ``error_code``. The catalog has no code meaning "usable
#: output over a strict subset of the input" — ``GATE_B1_CLOSURE.md`` §4 item 6, still an
#: open owner decision about a frozen twenty-member enum — and a call status is a different
#: object from an error code. ``ck_model_call_truncated_has_no_error_code`` refuses the row
#: that would conflate them.

_INSERT_MODEL_CALL = sql_text(
    """
    INSERT INTO model_call (
        model_call_id, run_id, stage_id, provider, model_identity, provider_mode,
        parameters, request_sha256, response_sha256, input_tokens, output_tokens,
        latency_ms, cost_micros, cost_basis, status, error_code
    ) VALUES (
        :model_call_id, :run_id, :stage_id, :provider, :model_identity, :provider_mode,
        CAST(:parameters AS jsonb), :request_sha256, :response_sha256, :input_tokens,
        :output_tokens, :latency_ms, :cost_micros, :cost_basis, :status, :error_code
    )
    """
)

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Everything one execution established, in terms a caller can assert on.

    It carries the gate's :class:`TerminalSelection` rather than a copy of its fields.
    That is not tidiness: re-deriving "which terminals publish" here would put a second
    definition of it in the tree, and the first place a definition drifts is its second
    copy. Every terminal fact below is delegated to the object the gate returned.
    """

    run_id: str
    selection: TerminalSelection
    stage_statuses: Mapping[str, str]
    published_finding_count: int
    diagnostic_count: int
    gate_ran: bool

    @property
    def terminal_state(self) -> str:
        return self.selection.state

    @property
    def degradation_set(self) -> tuple[str, ...]:
        return tuple(self.selection.degradation_set)

    @property
    def terminal_reason(self) -> str | None:
        return self.selection.terminal_reason

    @property
    def is_publishable(self) -> bool:
        """Delegated to the gate's own definition; this module has no opinion."""
        return self.selection.is_publishable


@dataclass
class _StageOutputs:
    """The artifact references produced so far, keyed by contract role."""

    refs: dict[str, ArtifactRef] = field(default_factory=dict)

    def blob_inputs(self, *roles: str) -> dict[str, Any]:
        """The ``{role: BlobId}`` map the stage runner takes.

        A role the previous stages did not publish is simply absent, and the runner's
        own before-guard turns that into ``analysis_input_invalid`` without entering
        the handler. That is deliberate: this module does not second-guess the guard.
        """
        supplied: dict[str, Any] = {}
        for role in roles:
            ref = self.refs.get(role)
            if ref is not None:
                supplied[role] = parse_blob_id(ref.blob_id)
        return supplied

    def absorb(self, result: StageResult) -> None:
        for ref in result.artifacts:
            self.refs[ref.role] = ref


def _persist(
    session: Session, runs: RunRepository, run_id: str, result: StageResult
) -> None:
    """Write the stage result the moment the stage finishes."""
    runs.record_stage_result(session, run_id=run_id, document=result.to_document())


def _record_model_calls(
    session: Session, *, run_id: str, stage_id: str, calls: tuple[ModelCallRecord, ...]
) -> None:
    """Persist provenance for every provider call, live or replayed.

    ``provider_mode`` comes off the record, which took it from the adapter's own class
    constant rather than from configuration — so a run configured "live" that in fact
    replayed is recorded as what it was.
    """
    for call in calls:
        document = call.as_dict()
        session.execute(
            _INSERT_MODEL_CALL,
            {
                "model_call_id": document["model_call_id"],
                "run_id": run_id,
                "stage_id": stage_id,
                "provider": document["provider"],
                "model_identity": document["model_id"],
                "provider_mode": document["provider_mode"],
                # The provider's own stop reason. Redundant with ``status`` since
                # ``0005`` and kept anyway: it is what makes a pre-0005 row legible.
                "parameters": json.dumps(
                    {**document["parameters"], "call_status": call.status},
                    sort_keys=True,
                ),
                "request_sha256": document["request_sha256"],
                "response_sha256": document["response_sha256"],
                "input_tokens": document["input_tokens"],
                "output_tokens": document["output_tokens"],
                "latency_ms": document["latency_ms"],
                "cost_micros": int(round(document["cost_usd"] * 1_000_000)),
                # Defaults to estimated rather than to the more flattering value: a row
                # whose basis the stage did not state was derived, and saying otherwise
                # would invent provenance.
                "cost_basis": document.get("cost_basis", "estimated"),
                # Written through, not mapped. The stage that consumed a truncated call
                # is ``partial``; the call itself is ``truncated``; the two are recorded
                # separately because they are separate facts.
                "status": call.status,
                "error_code": (
                    ErrorCode.ANALYSIS_FAILED.value if call.status == "failed" else None
                ),
            },
        )


def _text_stage_result(
    outcome: TextAnalysisOutcome,
    *,
    artifact_ref: ArtifactRef | None,
    started: datetime,
    finished: datetime,
) -> StageResult:
    """Bind a :class:`TextAnalysisOutcome` onto the runner's ``StageResult`` shape.

    The one adaptation this module owns. ``partial`` survives it, which is the whole
    reason the binding is not a ``StageHandler``.
    """
    status = StageStatus(outcome.status)
    metrics: dict[str, Any] = {}
    for key, value in dict(outcome.metrics).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            metrics[key] = value
    return StageResult(
        stage_id="text_analysis",
        stage_version=TEXT_STAGE_VERSION,
        status=status,
        artifacts=() if artifact_ref is None else (artifact_ref,),
        metrics=metrics,
        error=(
            None
            if outcome.error is None
            else StageError.from_domain_error(outcome.error)
        ),
        started_at=started,
        finished_at=finished,
    )


def _run_text_analysis_stage(
    session: Session,
    *,
    run_id: str,
    version_uid: str,
    outputs: _StageOutputs,
    blob_store: BlobStore,
    adapter: ModelAdapter,
    provider_config: ProviderConfig | None,
    clock: Clock,
) -> tuple[StageResult, Mapping[str, Any] | None]:
    """Run ``text_analysis`` and publish its artifact. Returns the result and document."""
    started = clock()

    text_layer_ref = outputs.refs.get(ROLE_TEXT_LAYER)
    graph_ref = outputs.refs.get(ROLE_DOCUMENT_GRAPH)
    if text_layer_ref is None or graph_ref is None:
        # The registry declares both required. Refuse exactly as the runner's
        # before-guard would, rather than calling the provider without them.
        error = DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "a required stage input was not supplied; the stage was not run and "
                "no artifact was published"
            ),
            stage_id="text_analysis",
            reason="missing_required_input",
        )
        return (
            _text_stage_result(
                TextAnalysisOutcome(
                    status="failed", artifact=None, model_calls=(), error=error
                ),
                artifact_ref=None,
                started=started,
                finished=clock(),
            ),
            None,
        )

    text_layer_document, _ = read_artifact(
        blob_store, parse_blob_id(text_layer_ref.blob_id), expected_role=ROLE_TEXT_LAYER
    )
    graph_document, _ = read_artifact(
        blob_store, parse_blob_id(graph_ref.blob_id), expected_role=ROLE_DOCUMENT_GRAPH
    )
    block_index_document: Mapping[str, Any] | None = None
    block_ref = outputs.refs.get(ROLE_BLOCK_INDEX)
    if block_ref is not None:
        block_index_document, _ = read_artifact(
            blob_store, parse_blob_id(block_ref.blob_id), expected_role=ROLE_BLOCK_INDEX
        )

    outcome = run_text_analysis(
        run_id=RunId.parse(run_id),
        text_layer_document=text_layer_document,
        adapter=adapter,
        config=provider_config,
        document_graph=graph_document,
        block_index_document=block_index_document,
        profile=AR_TEXT_PROFILE,
    )

    _record_model_calls(
        session, run_id=run_id, stage_id="text_analysis", calls=outcome.model_calls
    )

    artifact_ref: ArtifactRef | None = None
    if outcome.artifact is not None:
        artifact_ref, _ = publish_artifact(
            blob_store, ROLE_TEXT_OBSERVATIONS, outcome.artifact
        )

    result = _text_stage_result(
        outcome, artifact_ref=artifact_ref, started=started, finished=clock()
    )
    return result, outcome.artifact


def _run_evidence_gate(
    session: Session,
    *,
    run: RunRow,
    observations_document: Mapping[str, Any] | None,
    outputs: _StageOutputs,
    blob_store: BlobStore,
) -> tuple[bool, PublicationResult | None]:
    """Ground every proposed observation and publish what survives.

    ``B4`` owns every decision here. This function reads the three artifacts the gate
    consumes and hands them over; it applies no normalization, searches for no better
    anchor, and does not filter the verdicts. An ungrounded observation is written as a
    diagnostic with no ``finding_uid``, which is what keeps it out of every finding
    query and out of the CSV — enforced by the database, not by a ``WHERE`` clause.
    """
    if observations_document is None:
        return False, None

    text_layer_ref = outputs.refs.get(ROLE_TEXT_LAYER)
    if text_layer_ref is None:
        return False, None

    text_layer_document, _ = read_artifact(
        blob_store, parse_blob_id(text_layer_ref.blob_id), expected_role=ROLE_TEXT_LAYER
    )
    block_index = BlockIndex.empty()
    block_ref = outputs.refs.get(ROLE_BLOCK_INDEX)
    if block_ref is not None:
        block_document, _ = read_artifact(
            blob_store, parse_blob_id(block_ref.blob_id), expected_role=ROLE_BLOCK_INDEX
        )
        block_index = BlockIndex.from_artifact(block_document)

    observation_set = ObservationSet.from_artifact(observations_document)
    gate_result = run_grounding_gate(
        observation_set, TextLayer.from_artifact(text_layer_document), block_index
    )
    publication = publish_gate_result(
        session,
        gate_result=gate_result,
        observation_set=observation_set,
        run_id=run.run_id,
        project_uid=run.project_uid,
        version_uid=run.version_uid,
    )
    return True, publication


def execute_run(
    session: Session,
    run_id: str,
    *,
    blob_store: BlobStore,
    adapter: ModelAdapter,
    provider_config: ProviderConfig | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
    clock: Clock = _utc_now,
) -> ExecutionResult:
    """Drive one run from ``created`` to a terminal state.

    The caller owns the transaction. Every stage result is persisted as it is produced,
    and the terminal is whatever :func:`select_terminal` returns for the statuses that
    were actually written.
    """
    run_repo = runs or RunRepository()
    document_repo = documents or DocumentRepository()

    run = run_repo.get(session, run_id)

    # The run declares a provider mode; the adapter *is* one. Nothing compared them, so a
    # run started with provider_mode="live" and executed entirely by the recorded adapter
    # reached `published` and exported a CSV reading `live` on every row - while the
    # adapter, model_call.provider_mode and finding_observation.provider_mode all said
    # `recorded`. The export is correct: seam section 6 column 6 takes its value from
    # audit_run.provider_mode, which is precisely the field nobody had checked.
    #
    # `assert_consistent_mode` in analysis.text.provenance already guards the stage's own
    # provenance and its docstring names this exact failure - "a recorded run published
    # with provider_mode: live, and nothing downstream could detect that afterwards". It
    # holds where it stands. The refusal it names happens one level above it, which is
    # here, and this is the only place that holds both the run row and the adapter.
    #
    # PROTOTYPE_PROFILE section 8 criterion 4 requires live and recorded outcomes to be
    # distinguishable, and section 4 forbids presenting a recorded result as a live one.
    # Refusing before any stage runs means nothing is written under a false mode.
    actual_mode = getattr(adapter, "provider_mode", None)
    actual = getattr(actual_mode, "value", actual_mode)
    if actual is not None and str(actual) != str(run.provider_mode):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the run declares a provider mode the supplied adapter does not "
                "provide; a recorded run is never presented as a live one"
            ),
        )

    version = document_repo.get_version(session, VersionUid.parse(run.version_uid))
    source_entry = version.entry(ROLE_SOURCE_DOCUMENT)

    run_repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
    run_repo.advance(session, run_id=run_id, from_state="queued", to_state="running")

    outputs = _StageOutputs()
    outputs.refs[ROLE_SOURCE_DOCUMENT] = ArtifactRef(
        role=ROLE_SOURCE_DOCUMENT,
        blob_id=str(source_entry.blob_id),
        sha256=source_entry.sha256,
        size_bytes=source_entry.size_bytes,
        media_type=source_entry.media_type,
    )

    observations_document: Mapping[str, Any] | None = None

    # -- the three deterministic stages, in registry dependency order ---------
    deterministic = (
        ("source_preparation", (ROLE_SOURCE_DOCUMENT,)),
        ("page_geometry_extraction", (ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER)),
        ("document_context_build", (ROLE_BLOCK_INDEX, ROLE_TEXT_LAYER)),
    )
    halted = False
    for stage_id, roles in deterministic:
        result = run_stage(
            stage_id,
            version_uid=run.version_uid,
            inputs=outputs.blob_inputs(*roles),
            blob_store=blob_store,
            clock=clock,
        )
        _persist(session, run_repo, run_id, result)
        outputs.absorb(result)
        if result.status is not StageStatus.SUCCEEDED:
            # A failed preparation stage removes the inputs the rest of the chain
            # needs. Continuing would produce a cascade of identical
            # ``missing_required_input`` failures that say nothing extra.
            halted = True
            break

    # -- the AI stage ---------------------------------------------------------
    if not halted:
        text_result, observations_document = _run_text_analysis_stage(
            session,
            run_id=run_id,
            version_uid=run.version_uid,
            outputs=outputs,
            blob_store=blob_store,
            adapter=adapter,
            provider_config=provider_config,
            clock=clock,
        )
        _persist(session, run_repo, run_id, text_result)
        outputs.absorb(text_result)

    run_repo.advance(session, run_id=run_id, from_state="running", to_state="validating")

    # -- validating: the evidence gate, then the terminal it implies ----------
    gate_ran, publication = _run_evidence_gate(
        session,
        run=run,
        observations_document=observations_document,
        outputs=outputs,
        blob_store=blob_store,
    )

    statuses = run_repo.stage_statuses(session, run_id)
    missing = [stage for stage in PC01_STAGES if stage not in statuses]
    if missing:
        # A stage that never ran has no status, and terminal selection requires one for
        # every required stage. Record the stages that were skipped as failed-by-absence
        # rather than letting selection raise: the run must reach a terminal.
        selection = TerminalSelection(
            state="failed",
            degradation_set=tuple(missing),
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        )
    else:
        selection = select_terminal(
            statuses, required_stages=PC01_STAGES, gate_ran=gate_ran
        )

    run_repo.terminate(
        session,
        run_id=run_id,
        from_state="validating",
        to_state=selection.state,
        degradation_set=selection.degradation_set,
        terminal_reason=selection.terminal_reason,
    )

    return ExecutionResult(
        run_id=run_id,
        selection=selection,
        stage_statuses=dict(statuses),
        published_finding_count=(
            0 if publication is None else publication.published_count
        ),
        diagnostic_count=(0 if publication is None else publication.diagnostic_count),
        gate_ran=gate_ran,
    )


__all__ = ["Clock", "ExecutionResult", "execute_run"]
