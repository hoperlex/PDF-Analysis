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

The one retry
-------------
The model stage is attempted more than once when, and only when, the provider was
unreachable. ``P4_CLOSURE.md`` §6 put that policy here rather than in each caller;
:mod:`auditmanager.runs.retry` holds the pins and the classification, and the loop in
:func:`_run_text_analysis_stage` is the whole of the mechanism. Three properties of it are
load-bearing and are each guarded by a test in ``tests/integration/runs``:

* the attempts share **one** :class:`~auditmanager.analysis.text.CostMeter`, built once per
  run, so ``OD-03``'s USD 1.00 ceiling binds across the attempts rather than once per
  attempt — a retry cannot buy a fresh budget;
* the budget is finite, and exhausting it ends the run at a terminal carrying the
  transport code rather than an invented state;
* the attempt count reaches the persisted ``stage_result.metrics``, so a first-try success
  and a third-try success stay distinguishable after the process is gone.

Every execution now commits one local ``Job`` and current ``Attempt`` before its first
external effect. Provider-call retries remain bounded call attempts inside that one
execution Attempt; an ambiguous live outcome is never retried automatically. Remote
workers, heartbeat-driven failover and resume remain out of scope.
"""

from __future__ import annotations

import time
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

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
from auditmanager.analysis.public import publish_artifact
from auditmanager.analysis.public import (
    AR_TEXT_PROFILE,
    ARTIFACT_ROLE as ROLE_TEXT_OBSERVATIONS,
    CostMeter,
    ModelAdapter,
    ModelCallJournal,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    ProviderConfig,
    ProviderMode,
    TextAnalysisOutcome,
    load_provider_config,
    run_text_analysis,
)
from auditmanager.analysis.public import TEXT_STAGE_VERSION
from auditmanager.documents.public import DocumentRepository
from auditmanager.findings.public import (
    BlockIndex,
    ObservationSet,
    PublicationResult,
    TerminalSelection,
    TextLayer,
    publish_gate_result,
    run_grounding_gate,
    select_terminal,
)
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.jobs.lease import start_for_current_thread, stop_for_current_thread
from auditmanager.runs.repository import (
    INITIAL_STATE,
    PC01_STAGES,
    RunRepository,
    RunRow,
)
from auditmanager.runs.retry import (
    AttemptLedger,
    AttemptSummary,
    RetryPolicy,
    not_attempted,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId, VersionUid
from auditmanager.storage.public import BlobStore, DurablePublicationStore
from auditmanager.storage.public import BlobMetadataRepository
from auditmanager.storage.public import BlobDeclaration, VerifiedBlob, parse_blob_id

Clock = Callable[[], datetime]

#: How the executor waits between attempts. Injected for the same reason ``Clock`` is: a
#: test must be able to assert *that* the pinned backoff was taken without spending it.
Sleep = Callable[[float], None]

#: Optional observer retained for narrow tests. Durability no longer depends on it:
#: ``execute_run`` commits Job/Attempt authority itself before any external effect.
Checkpoint = Callable[[], None]

#: Test/observability hook invoked only *after* a mandatory durability boundary. It
#: never performs the commit and production does not need to supply one.
EffectCheckpoint = Callable[[str], None]


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
    #: How many attempts the model stage took, and why a second one happened. The same
    #: facts are persisted on the stage row, so a caller that keeps this object and a
    #: reader who has only the database agree without either re-deriving the other.
    model_attempts: AttemptSummary

    @property
    def attempts(self) -> int:
        """Attempts at the model stage. ``1`` on a first-try run; never ``0`` on a run
        that reached the provider at all."""
        return self.model_attempts.attempts

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


class _DurableCallJournal(ModelCallJournal):
    """Commit every provider boundary under the current Attempt authority."""

    __slots__ = ("_session", "_jobs", "_authority", "_checkpoint")

    def __init__(
        self,
        session: Session,
        jobs: JobRepository,
        authority: AttemptAuthority,
        checkpoint: EffectCheckpoint | None = None,
    ) -> None:
        self._session = session
        self._jobs = jobs
        self._authority = authority
        self._checkpoint = checkpoint

    def _committed(self, boundary: str) -> None:
        if self._checkpoint is not None:
            self._checkpoint(boundary)

    def prepare(self, request: ModelRequest, *, mode: ProviderMode) -> ModelCallId:
        model_call_id = self._jobs.prepare_provider_call(
            self._session,
            self._authority,
            provider="anthropic",
            model_identity=request.model_id,
            provider_mode=mode.value,
            parameters=request.parameters,
            request_sha256=request.request_sha256,
        )
        self._session.commit()
        self._committed("provider_intent_committed")
        return model_call_id

    def response_received(
        self, model_call_id: ModelCallId, response: ModelResponse
    ) -> None:
        self._jobs.record_provider_response(
            self._session,
            self._authority,
            model_call_id=model_call_id,
            response_sha256=response.response_sha256,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )
        self._session.commit()
        self._committed("provider_response_committed")

    def complete(self, call: ModelCallRecord) -> None:
        self._jobs.complete_provider_call(
            self._session, self._authority, call=call.as_dict()
        )
        self._session.commit()
        self._committed("provider_call_completed")

    def outcome_unknown(
        self, model_call_id: ModelCallId, error: DomainError
    ) -> None:
        self._jobs.record_provider_unknown(
            self._session,
            self._authority,
            model_call_id=model_call_id,
            error_code=error.code.value,
        )
        self._session.commit()
        self._committed("provider_outcome_unknown")

    def not_processed(
        self, model_call_id: ModelCallId, error: DomainError, dispatch_class: str
    ) -> None:
        self._jobs.record_provider_not_processed(
            self._session, self._authority, model_call_id=model_call_id,
            error_code=error.code.value, dispatch_class=dispatch_class,
        )
        self._session.commit()
        self._committed("provider_not_processed")


def _publication_store(
    session: Session,
    *,
    store: BlobStore,
    jobs: JobRepository,
    blobs: BlobMetadataRepository,
    authority: AttemptAuthority,
    stage_id: str,
    checkpoint: EffectCheckpoint | None = None,
) -> DurablePublicationStore:
    def before_stage(declaration: BlobDeclaration) -> str:
        blobs.record_declared(session, declaration)
        upload_token = jobs.prepare_artifact(
            session, authority, stage_id=stage_id, declaration=declaration
        )
        # The breadcrumb is durable before BlobStore.stage_temporary performs the
        # first external effect. Process loss afterwards is DB-enumerable.
        session.commit()
        if checkpoint is not None:
            checkpoint(f"{stage_id}:artifact_upload_intent_committed")
        return upload_token

    def before_publish(verified: VerifiedBlob) -> None:
        blobs.record_verified(session, verified)
        # Verification is separately durable before canonical publication.
        session.commit()
        if checkpoint is not None:
            checkpoint(f"{stage_id}:artifact_intent_committed")

    def after_publish(_published: Any) -> None:
        if checkpoint is not None:
            checkpoint(f"{stage_id}:artifact_published")

    return DurablePublicationStore(
        store,
        before_stage=before_stage,
        before_publish=before_publish,
        after_publish=after_publish,
    )


def _persist_and_bind(
    session: Session,
    *,
    runs: RunRepository,
    jobs: JobRepository,
    blobs: BlobMetadataRepository,
    authority: AttemptAuthority,
    run_id: str,
    result: StageResult,
) -> None:
    _persist(session, runs, run_id, result)
    for blob_id in jobs.bind_artifacts(
        session,
        authority,
        stage_id=result.stage_id,
        artifacts=result.artifacts,
    ):
        blobs.mark_available(session, blob_id)


def _text_stage_result(
    outcome: TextAnalysisOutcome,
    *,
    artifact_ref: ArtifactRef | None,
    attempts: AttemptSummary,
    started: datetime,
    finished: datetime,
) -> StageResult:
    """Bind a :class:`TextAnalysisOutcome` onto the runner's ``StageResult`` shape.

    The one adaptation this module owns. ``partial`` survives it, which is the whole
    reason the binding is not a ``StageHandler``.

    ``started``/``finished`` span **every** attempt, not the last one: the stage is what
    the run waited for, and reporting only the successful attempt's duration would hide a
    266-second wait behind a 4-second number. The per-attempt tally is in the metrics.

    The scalar filter is not tidiness. ``contracts/analysis/v1/stage-result.schema.json``
    admits only ``number | integer | string | boolean | null`` in ``metrics``, so a stage
    that returned a structured metric would otherwise write a row the contract refuses.
    The attempt facts are merged *after* it, and are scalars by construction — see
    :meth:`AttemptSummary.metrics`.
    """
    status = StageStatus(outcome.status)
    metrics: dict[str, Any] = {}
    for key, value in dict(outcome.metrics).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            metrics[key] = value
    metrics.update(attempts.metrics())
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
    *,
    run_id: str,
    version_uid: str,
    outputs: _StageOutputs,
    blob_store: BlobStore,
    adapter: ModelAdapter,
    provider_config: ProviderConfig,
    cost_meter: CostMeter,
    policy: RetryPolicy,
    sleep: Sleep,
    clock: Clock,
    call_journal: ModelCallJournal,
) -> tuple[StageResult, Mapping[str, Any] | None, AttemptSummary]:
    """Run ``text_analysis``, retrying transport failures, and publish its artifact.

    Returns the stage result, the observations document, and the attempt tally.

    Everything the provider does not touch happens **once**, above the loop: the required
    inputs are checked and the three input artifacts are read before the first attempt, so
    a retry re-asks the provider and re-reads nothing. The loop therefore has exactly one
    reason to run twice, which is the one ``P4_CLOSURE.md`` §1 ruled on.
    """
    started = clock()
    ledger = AttemptLedger(attempt_budget=policy.attempt_budget)

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
                attempts=not_attempted(policy),
                started=started,
                finished=clock(),
            ),
            None,
            not_attempted(policy),
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

    while True:
        attempt = ledger.attempts + 1
        # The wait belongs to the attempt that is about to run, and is taken before it
        # rather than after the failure, so the last attempt never sleeps for nothing.
        waited = policy.backoff_before_attempt(attempt)
        if attempt > 1:
            waited = max(waited, outcome.retry_after_seconds)
        if waited:
            sleep(waited)

        outcome = run_text_analysis(
            run_id=RunId.parse(run_id),
            text_layer_document=text_layer_document,
            adapter=adapter,
            config=provider_config,
            document_graph=graph_document,
            block_index_document=block_index_document,
            profile=AR_TEXT_PROFILE,
            # One meter for the whole run, supplied by the caller above. Building it here
            # would give every attempt a fresh USD 1.00, which is precisely the reading of
            # OD-03 that a retry must not be able to buy.
            meter=cost_meter,
            call_journal=call_journal,
        )

        # Complete responses were committed by ``call_journal`` before parsing reached
        # this point. A live transport exception leaves an explicit outcome-unknown
        # intent and is not reissued automatically: no response is not proof that the
        # provider performed no billable effect.
        ledger.record(
            status=outcome.status, error=outcome.error, waited_seconds=waited
        )

        if (outcome.provider_effect_uncertain or outcome.provider_retry_allowed is False
                or not policy.retries(outcome.error)):
            # Succeeded, partial, or a failure no second attempt could answer
            # differently - `analysis_failed` above all, which is the model having
            # answered. The policy owns that classification; there is no status or code
            # comparison here.
            break
        if not policy.has_budget_for(attempt + 1):
            # Exhausted. The outcome of the last attempt stands as the stage's outcome,
            # carrying the transport error it failed with, and the run goes on to a
            # terminal from it. No new state and no invented code.
            break

    attempts = ledger.close()

    artifact_ref: ArtifactRef | None = None
    if outcome.artifact is not None:
        artifact_ref, _ = publish_artifact(
            blob_store, ROLE_TEXT_OBSERVATIONS, outcome.artifact
        )

    result = _text_stage_result(
        outcome,
        artifact_ref=artifact_ref,
        attempts=attempts,
        started=started,
        finished=clock(),
    )
    return result, outcome.artifact, attempts


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


def _execute_run_body(
    session: Session,
    run_id: str,
    *,
    blob_store: BlobStore,
    adapter: ModelAdapter,
    provider_config: ProviderConfig | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
    clock: Clock = _utc_now,
    retry_policy: RetryPolicy | None = None,
    cost_meter: CostMeter | None = None,
    sleep: Sleep = time.sleep,
    checkpoint: Checkpoint | None = None,
    effect_checkpoint: EffectCheckpoint | None = None,
    jobs: JobRepository | None = None,
    blob_metadata: BlobMetadataRepository | None = None,
) -> ExecutionResult:
    """Drive one run from ``created`` to a terminal state.

    The executor owns the authority and external-effect commits; the caller commits the
    final stage/result transaction on normal return. Every stage result is persisted as it
    is produced, and the terminal is whatever :func:`select_terminal` returns for the
    statuses that were actually written.

    ``cost_meter`` is the run's whole model budget, and it is built **here**, once, so that
    ``OD-03``'s ceiling is a property of the run rather than of an attempt. A caller may
    supply one already carrying spend — nothing in the deployment does, and a test does, to
    place a run mid-budget and show that a retry does not refill it.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    blob_repo = blob_metadata or BlobMetadataRepository()
    document_repo = documents or DocumentRepository()
    policy = retry_policy or RetryPolicy()
    # Resolved once, here, rather than once per attempt inside the stage: the ceiling the
    # meter is built against and the configuration the attempts run under must be the same
    # object, or a re-read of the environment mid-run could move one and not the other.
    config = provider_config or load_provider_config()
    prior_cost = run_repo.cost(session, run_id)
    meter = cost_meter or CostMeter(
        ceiling_usd=config.run_cost_ceiling_usd,
        spent_usd=0.0 if prior_cost is None else prior_cost.cost_micros / 1_000_000,
        call_count=0 if prior_cost is None else prior_cost.model_call_count,
    )
    if cost_meter is None and prior_cost is not None:
        # A persisted opening balance cannot be re-priced by this Attempt. Even a
        # zero-cost earlier call may have been estimated, so a resumed meter must
        # never re-label that historical contribution as measured.
        meter.unpriced_contributions = max(meter.unpriced_contributions, 1)

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
    # holds where it stands. This is the only place that holds both the run row and the
    # adapter — but it is **not** where the API path refuses, and the comment used to imply
    # that it was. `bootstrap/adapters.py` rejects a request for a mode the deployment does
    # not provide before a run row is written, so the API surface never reaches here:
    # `W6-CERT` removed this branch and the whole criterion-4 suite stayed green.
    #
    # It is defence in depth behind that one, and it guards a different thing: `adapters.py`
    # compares a *request* against a *deployment*, while this compares a persisted *row*
    # against the object about to write under it. A composition that wired the wrong adapter
    # is refused here and nowhere else. `tests/integration/runs/test_mode_crosscheck_is_
    # reachable.py` reaches it through `execute_run`, which is where it lives.
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

    # `D-20`. Two callers, two starting states, and the row is asked which one this is
    # rather than a flag being passed that could disagree with it.
    #
    # The API path queues the run inside the transaction that *accepts* it -- that is what
    # lets `startRun` answer `202 queued` without executing -- and hands the queued run to
    # a carrier, so what arrives here is already `queued`. An in-process caller that
    # creates and executes in one go (every suite under `tests/integration/runs`, the
    # export suites, the p02 journey) still hands over a run in `created`.
    #
    # Job authority must inspect the Run while it is still queued. Advancing first
    # would make a legitimate direct caller indistinguishable from an orphan
    # running Run whose prior provider effect might already have spent.
    if run.state == INITIAL_STATE:
        run_repo.advance(
            session, run_id=run_id, from_state=INITIAL_STATE, to_state="queued"
        )
    if run.state not in {INITIAL_STATE, "queued", "running"}:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED, machine="audit_run",
            current_state=run.state, requested_state="running",
        )
    authority = job_repo.start_execution(session, run_id=run_id)
    if run.state in {INITIAL_STATE, "queued"}:
        run_repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
    # `D-20`. The authority boundary that makes what has happened so far durable.
    #
    # Every state this function writes used to be written and overwritten inside the
    # caller's single uncommitted transaction, so `running` existed for the length of one
    # `UPDATE` and no second connection could ever read it. A poller therefore made exactly
    # one request and `PA-01` criterion 4's UI clause was unreachable.
    #
    # Effect journals add finer commits later in the stage loop. A crash can therefore
    # expose truthful partial rows. Lease recovery fences a lost Attempt and
    # resumes only when no provider effect can have spent; ambiguous effects fail.
    # Unlike the old optional checkpoint, this commit is unconditional. It makes the
    # running Run plus Job/Attempt/Lease authority durable before the first S3 or provider
    # effect on every caller path, including direct integration invocations.
    session.commit()
    start_for_current_thread(session, authority)
    if checkpoint is not None:
        checkpoint()

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
        run_repo.stage_started(session, run_id=run_id, stage_id=stage_id)
        session.commit()
        stage_store = _publication_store(
            session,
            store=blob_store,
            jobs=job_repo,
            blobs=blob_repo,
            authority=authority,
            stage_id=stage_id,
            checkpoint=effect_checkpoint,
        )
        result = run_stage(
            stage_id,
            version_uid=run.version_uid,
            inputs=outputs.blob_inputs(*roles),
            blob_store=stage_store,
            clock=clock,
        )
        _persist_and_bind(
            session,
            runs=run_repo,
            jobs=job_repo,
            blobs=blob_repo,
            authority=authority,
            run_id=run_id,
            result=result,
        )
        outputs.absorb(result)
        if result.status is not StageStatus.SUCCEEDED:
            # A failed preparation stage removes the inputs the rest of the chain
            # needs. Continuing would produce a cascade of identical
            # ``missing_required_input`` failures that say nothing extra.
            halted = True
            break

    # -- the AI stage ---------------------------------------------------------
    # A halted chain never reaches the provider, so it has no attempts rather than one
    # failed attempt. The two are different claims and the tally says which.
    attempts = not_attempted(policy)
    if not halted:
        run_repo.stage_started(session, run_id=run_id, stage_id="text_analysis")
        session.commit()
        text_store = _publication_store(
            session,
            store=blob_store,
            jobs=job_repo,
            blobs=blob_repo,
            authority=authority,
            stage_id="text_analysis",
            checkpoint=effect_checkpoint,
        )
        text_result, observations_document, attempts = _run_text_analysis_stage(
            run_id=run_id,
            version_uid=run.version_uid,
            outputs=outputs,
            blob_store=text_store,
            adapter=adapter,
            provider_config=config,
            cost_meter=meter,
            policy=policy,
            sleep=sleep,
            clock=clock,
            call_journal=_DurableCallJournal(
                session, job_repo, authority, effect_checkpoint
            ),
        )
        _persist_and_bind(
            session,
            runs=run_repo,
            jobs=job_repo,
            blobs=blob_repo,
            authority=authority,
            run_id=run_id,
            result=text_result,
        )
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
        # The stages' own error codes, so the run row can name what killed it instead
        # of flattening every failure into analysis_failed. Read back from the persisted
        # rows for the same reason stage_statuses is: the terminal is chosen from what
        # was actually written, not from an in-process tally.
        persisted = run_repo.stage_results(session, run_id)
        stage_errors = {
            row.stage_id: (row.error or {}).get("code") for row in persisted
        }
        # `D-46`. The classifiers the failing stage recorded, read back from the same
        # persisted rows and for the same reason: the terminal is chosen from what was
        # actually written. `StageError.from_domain_error` already screened these against
        # the catalog when the row was built, and `select_terminal` screens them again
        # against the code the RUN ends up reporting, which is not always the stage's.
        stage_details = {
            row.stage_id: (row.error or {}).get("details") for row in persisted
        }
        selection = select_terminal(
            statuses,
            required_stages=PC01_STAGES,
            gate_ran=gate_ran,
            stage_errors=stage_errors,
            stage_details=stage_details,
        )

    run_repo.terminate(
        session,
        run_id=run_id,
        from_state="validating",
        to_state=selection.state,
        degradation_set=selection.degradation_set,
        terminal_reason=selection.terminal_reason,
        terminal_detail=selection.terminal_detail,
    )
    job_repo.finish_execution(
        session, authority, publishes_result=selection.is_publishable
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
        model_attempts=attempts,
    )


@wraps(_execute_run_body)
def execute_run(*args: Any, **kwargs: Any) -> ExecutionResult:
    """Drive a run and stop its independent heartbeat on every exit path."""
    try:
        return _execute_run_body(*args, **kwargs)
    finally:
        stop_for_current_thread()


__all__ = [
    "Checkpoint",
    "Clock",
    "EffectCheckpoint",
    "ExecutionResult",
    "Sleep",
    "execute_run",
]
