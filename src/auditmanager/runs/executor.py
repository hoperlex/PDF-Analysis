"""The sequential executor: the four v1 stages of a section run, or the AR v3 beta worker chain.

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
execution Attempt; an ambiguous live outcome is never retried automatically. Since W53
the Attempt's database lease is extended by an independent heartbeat
(:mod:`auditmanager.jobs.lease`), and an expired lease is reclaimed by the durable
dispatcher: the lost Attempt is fenced and the run is executed again from its first
stage under a new Attempt, but only when no provider effect of the lost Attempt can
have spent; otherwise the run fails with that uncertainty recorded. Remote workers and
outbox delivery remain out of scope.
"""

from __future__ import annotations

import time
from functools import partial, wraps
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_MARKDOWN,
    ROLE_SOURCE_STRUCTURED_COMPANION,
    ROLE_TEXT_LAYER,
    ArtifactRef,
    PdfPrecheckProgress,
    StageError,
    StageResult,
    StageStatus,
    read_artifact,
    run_stage,
    run_source_preparation_with_progress,
)
from auditmanager.analysis.public import publish_artifact
from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID,
    AR_V3_BETA_PROFILE_ID,
    ARTIFACT_ROLE as ROLE_TEXT_OBSERVATIONS,
    CostMeter,
    MAX_ANALYSIS_WINDOWS,
    ModelAdapter,
    ModelCallJournal,
    ModelCallRecord,
    ModelRequest,
    ProviderConfig,
    ProviderMode,
    TextAnalysisOutcome,
    load_provider_config,
    recognised_total_characters,
    run_text_analysis,
    run_text_analysis_windows,
    text_window_policy,
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
from auditmanager.ingest.public import CommandRepository
from auditmanager.jobs.public import (
    AttemptAuthority,
    AttemptContext,
    JobRepository,
    append_execution_event,
    start_attempt_lease_heartbeat,
    stop_attempt_lease_heartbeat,
)
from auditmanager.runs.crop_budget import MAX_CROP_BYTES, CropByteBudget
from auditmanager.runs.provider import ProviderBinding, ProviderResolver
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
from auditmanager.runs.section_recognised_input import load_section_recognised_pages
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.runs.window_reply_custody import MAX_REPLY_BYTES, WindowReplyCustody
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    CommandId,
    ModelCallId,
    RunId,
    VersionUid,
)
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
    #: How many attempts the model stage took, and why a second one happened.
    #: v1 facts are persisted on the stage row; the AR v3 beta chain makes one call per Run
    #: and does not use the v1 retry ladder.
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


class _ResponseEvidence(Protocol):
    """What the effect journal records of an answer: a full response or the evidence of
    an unusable one (the proxy's ``ReceivedResponse``)."""

    @property
    def response_sha256(self) -> str: ...

    @property
    def input_tokens(self) -> int: ...

    @property
    def output_tokens(self) -> int: ...

    @property
    def latency_ms(self) -> int: ...


class _DurableCallJournal(ModelCallJournal):
    """Commit every provider boundary under the current Attempt authority."""

    __slots__ = ("_session", "_jobs", "_authority", "_checkpoint", "_call", "_context")

    def __init__(
        self,
        session: Session,
        jobs: JobRepository,
        authority: AttemptAuthority,
        checkpoint: EffectCheckpoint | None = None,
        call: Any = None,
        context: AttemptContext | None = None,
    ) -> None:
        self._session = session
        self._jobs = jobs
        self._authority = authority
        self._checkpoint = checkpoint
        # `EXEC-HTTP-01`: the call binding of the connection serving this run (a
        # ``CallBinding``), or ``None`` for the environment source, whose rows are unchanged.
        self._call = call
        self._context = context

    def _committed(self, boundary: str) -> None:
        if self._checkpoint is not None:
            self._checkpoint(boundary)

    def prepare(self, request: ModelRequest, *, mode: ProviderMode) -> ModelCallId:
        call = self._call
        model_call_id = self._jobs.prepare_provider_call(
            self._session,
            self._authority,
            provider="anthropic" if call is None else call.provider_label,
            model_identity=request.model_id,
            provider_mode=mode.value,
            parameters=request.parameters,
            request_sha256=request.request_sha256,
            connection_revision_id=None if call is None else call.connection_revision_id,
            identity_basis=None if call is None else call.identity_basis,
        )
        if self._context is not None:
            self._context.bind_call(str(model_call_id))
        self._session.commit()
        self._committed("provider_intent_committed")
        return model_call_id

    def bind_current_call(self, model_call_id) -> None:
        if self._context is not None:
            self._context.bind_call(str(model_call_id))

    def response_received(
        self, model_call_id: ModelCallId, response: _ResponseEvidence
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
    profile: Any,
    call: Any = None,
    text_character_count: int | None = None,
    window_custody: Any = None,
    textless_pages: tuple[int, ...] | None = None,
    relaxed_limits: bool = False, force_durable_windows: bool = False,
) -> tuple[StageResult, Mapping[str, Any] | None, AttemptSummary]:
    """Run ``text_analysis``, retrying transport failures, and publish its artifact.

    ``profile`` is the run's pinned text profile, resolved before any effect
    (`W59-SECTION-SEAL-01`): its prompt bundle is the one every attempt sends.

    ``text_character_count`` (`SECTION-CHUNKED-ANALYSIS-01`) is the version's recorded count. A count
    above the one-call budget of the connection's model and the run's ceiling analyses the text in
    whole-page windows (``run_text_analysis_windows``, with ``window_custody``); no count, or a count not
    above the budget, is the one call it always was, through the same ``run_text_analysis``. The retry
    ladder below is the same for both: a re-invoked windowed stage recovers the windows it finished.

    ``textless_pages`` (`SECTION-CATEGORY-OCR-01`, `R-146aq`) is the version's stored list of text-less pages. For
    a portal bundle that has some, the recognised text of those pages (this run's own saved
    ``prepared.recognised_text``) is handed to the stage as marked context, counted in the window decision; it is
    never part of the text layer, so it cannot ground a finding. ``None`` or an empty list is every version
    without a scanned page, and nothing changes for it.

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

    # `SECTION-CATEGORY-OCR-01`: read once, like the three inputs above, so a retry re-reads nothing. An
    # inconsistent saved artifact fails the stage with its reason; an empty context is never substituted.
    try:
        recognised_pages = load_section_recognised_pages(
            blob_store=blob_store,
            refs=outputs.refs,
            version_uid=version_uid,
            textless_pages=textless_pages,
        )
    except DomainError as refusal:
        return (
            _text_stage_result(
                TextAnalysisOutcome(status="failed", artifact=None, model_calls=(), error=refusal),
                artifact_ref=None,
                attempts=not_attempted(policy),
                started=started,
                finished=clock(),
            ),
            None,
            not_attempted(policy),
        )

    # Comparison-upload PDFs have no ingest-time count; use the prepared layer's normalized count.
    if text_character_count is None:
        text_character_count = text_layer_document.get("total_char_count")
    # Decided once, before the first attempt: the predicate is the old refusal's (a count above the
    # per-call budget), so every run the budget used to admit goes through `run_text_analysis` untouched.
    # The recognised blocks are counted too: the version's count does not include them.
    window_policy = text_window_policy(
        text_character_count=text_character_count,
        model_id=provider_config.model_id,
        ceiling_usd=provider_config.run_cost_ceiling_usd,
        recognised_characters=recognised_total_characters(recognised_pages),
        # `SECTION-JUDGE-FIXES-01`: the call carries this profile's own prompt and schema, not the АР v1 pair.
        bundle=profile.prompt_bundle,
        relaxed_limits=relaxed_limits,
        approved_window_characters=provider_config.approved_window_characters,
        max_windows=provider_config.approved_max_windows or MAX_ANALYSIS_WINDOWS,
    )

    if force_durable_windows and window_policy is None and window_custody is not None:
        from auditmanager.analysis.public import WindowPolicy
        # Even a one-window fresh-v3 primary call uses existing saved-reply custody.
        window_policy=WindowPolicy(window_characters=provider_config.approved_window_characters,
            max_windows=max(2,provider_config.approved_max_windows or MAX_ANALYSIS_WINDOWS))

    while True:
        attempt = ledger.attempts + 1
        # The wait belongs to the attempt that is about to run, and is taken before it
        # rather than after the failure, so the last attempt never sleeps for nothing.
        waited = policy.backoff_before_attempt(attempt)
        if attempt > 1:
            waited = max(waited, outcome.retry_after_seconds)
        if waited:
            sleep(waited)

        if window_policy is None:
            outcome = run_text_analysis(
                run_id=RunId.parse(run_id),
                text_layer_document=text_layer_document,
                adapter=adapter,
                config=provider_config,
                document_graph=graph_document,
                block_index_document=block_index_document,
                profile=profile,
                # One meter for the whole run, supplied by the caller above. Building it here
                # would give every attempt a fresh USD 1.00, which is precisely the reading of
                # OD-03 that a retry must not be able to buy.
                meter=cost_meter,
                call_journal=call_journal,
                call=call,
                recognised_pages=recognised_pages,
                textless_pages=textless_pages,
            )
        else:
            outcome = run_text_analysis_windows(
                run_id=RunId.parse(run_id),
                text_layer_document=text_layer_document,
                adapter=adapter,
                config=provider_config,
                document_graph=graph_document,
                block_index_document=block_index_document,
                profile=profile,
                # The same one meter: the ceiling binds across every window of every attempt.
                meter=cost_meter,
                call_journal=call_journal,
                call=call,
                policy=window_policy,
                custody=window_custody,
                recognised_pages=recognised_pages,
                textless_pages=textless_pages,
                **({"force_single_window_custody":True} if force_durable_windows else {}),
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


@dataclass(frozen=True)
class _GateInputs:
    """The three artifacts the evidence gate consumes, read before the run row is locked."""

    observation_set: ObservationSet
    text_layer: TextLayer
    block_index: BlockIndex


def _read_gate_inputs(
    *,
    observations_document: Mapping[str, Any] | None,
    outputs: _StageOutputs,
    blob_store: BlobStore,
) -> _GateInputs | None:
    """Read what the evidence gate consumes from the store. No database statement.

    `W54-JUDGE-Y` F5: this runs **before** ``running -> validating``. That advance locks the
    ``audit_run`` row until the caller's final commit, and the S3 reads below used to run
    inside it, so a slow store held the run row lock for as long as the reads took. Reading
    first keeps the lock span to the gate's own writes and the terminal transition. `D-141`'s
    commit is untouched: it precedes this read, so the Lease is free throughout.

    ``None`` when the gate has nothing to ground (no observations, or no text layer).
    """
    if observations_document is None:
        return None

    text_layer_ref = outputs.refs.get(ROLE_TEXT_LAYER)
    if text_layer_ref is None:
        return None

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
    return _GateInputs(
        observation_set=ObservationSet.from_artifact(observations_document),
        text_layer=TextLayer.from_artifact(text_layer_document),
        block_index=block_index,
    )


def _run_evidence_gate(
    session: Session,
    *,
    run: RunRow,
    inputs: _GateInputs | None,
) -> tuple[bool, PublicationResult | None]:
    """Ground every proposed observation and publish what survives.

    ``B4`` owns every decision here. This function hands the gate the three artifacts
    :func:`_read_gate_inputs` already read; it applies no normalization, searches for no
    better anchor, and does not filter the verdicts. An ungrounded observation is written
    as a diagnostic with no ``finding_uid``, which is what keeps it out of every finding
    query and out of the CSV — enforced by the database, not by a ``WHERE`` clause.
    """
    if inputs is None:
        return False, None
    gate_result = run_grounding_gate(inputs.observation_set, inputs.text_layer, inputs.block_index)
    publication = publish_gate_result(
        session,
        gate_result=gate_result,
        observation_set=inputs.observation_set,
        run_id=run.run_id,
        project_uid=run.project_uid,
        version_uid=run.version_uid,
    )
    return True, publication


#: `W59-SECTION-SEAL-01`. ``(analysis_profile_id, prompt_bundle_id) -> text profile``,
#: raising ``LookupError`` for a pair it does not register. The composition root passes the
#: section-keyed text-profile registry's ``resolve``. The profile is opaque here: it goes to
#: ``run_text_analysis`` unread, which is why ``runs`` needs no import of its type.
TextProfileResolver = Callable[[str, str], Any]


def _pinned_text_profile(run: RunRow, resolve: TextProfileResolver | None) -> Any:
    """The run's pinned text profile, or the refusal that fails the run before any effect.

    A caller that supplies no registry gets the same refusal as a pair the registry does not
    hold (`PROD-11-AR-V1-V2-REMOVAL-01`): the executor used to run the АР profile for it, which is
    a silent fallback (`AGENTS.md` section 4) and no longer a profile of the product.
    """
    try:
        if resolve is None:
            raise LookupError("no text-profile registry was supplied")
        return resolve(run.analysis_profile_id, run.prompt_bundle_id)
    except LookupError:
        raise DomainError(
            ErrorCode.REQUIRED_NORM_UNAVAILABLE,
            message=(
                "the run's pinned analysis profile is not registered in this deployment; "
                "no other profile is substituted"
            ),
            reference_kind="analysis_profile",
            analysis_profile_id=run.analysis_profile_id,
            prompt_bundle_id=run.prompt_bundle_id,
        ) from None


def _bind_provider(
    session: Session, run: RunRow, context: AttemptContext,
    providers: ProviderResolver | None, adapter: ModelAdapter, config: ProviderConfig,
) -> ProviderBinding:
    """The adapter, configuration and call binding this Attempt's model stage runs with."""
    if providers is None:
        return ProviderBinding(adapter=adapter, config=config, call=None)
    binding = providers(session, run, context)
    mode = getattr(getattr(binding.adapter, "provider_mode", None), "value", None)
    if mode is not None and str(mode) != str(run.provider_mode):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the run declares a provider mode the resolved adapter does not "
                "provide; a recorded run is never presented as a live one"
            ),
        )
    if config.approved_cost_ceiling:
        # A database route contributes its model/credentials, while the accepted
        # run command retains the cost/window authority after binding that route.
        binding = replace(binding, config=replace(
            binding.config, run_cost_ceiling_usd=config.run_cost_ceiling_usd,
            approved_window_characters=config.approved_window_characters,
            approved_max_windows=config.approved_max_windows, approved_cost_ceiling=True,
            approved_model_id=config.approved_model_id,
            approved_rate_sha256=config.approved_rate_sha256,
            approved_connection_revision_id=config.approved_connection_revision_id,
        ))
    return binding


def _section_relaxed_limits(session: Session, run: RunRow) -> bool:
    """Read a section Run's accepted choice from its command after any restart."""
    if run.command_id is None:
        return False  # Legacy in-process Runs predate command custody.
    command = CommandRepository().get(session, CommandId.parse(run.command_id))
    if command.command_type not in {"start_audit_run", "reaudit_run"} or command.state != "succeeded":
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="section Run has no accepted command")
    outcome = command.outcome
    if (outcome is None or outcome.get("run_id") != run.run_id
            or type(outcome.get("relaxed_limits", False)) is not bool):
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="section Run limit policy is invalid")
    return outcome.get("relaxed_limits", False)


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
    text_profiles: TextProfileResolver | None = None,
    providers: ProviderResolver | None = None,
    ar_v3_pack_registry: TrustedPackRegistry | None = None,
) -> ExecutionResult:
    """Drive one run from ``created`` to a terminal state.

    ``providers`` (`EXEC-HTTP-01`) is the composition root's resolver. Called once per Attempt,
    just before the model stage, with the run row and the Attempt's context, it returns the
    :class:`~auditmanager.runs.provider.ProviderBinding` the stage runs with: for the
    ``database`` source the adapter of the connection revision the run froze at start, built with
    the connection's current key; for ``environment`` the adapter built at start-up. A refusal is
    a ``DomainError`` and fails the text stage with that code, calling nothing. ``None`` keeps the
    in-process harness's behaviour: ``adapter`` and ``provider_config`` serve every run.

    ``text_profiles`` (`W59-SECTION-SEAL-01`) resolves the run's **pinned**
    ``(analysis_profile_id, prompt_bundle_id)`` to the text profile the ``text_analysis``
    stage runs with, so a section-routed run executes with its own prompt bundle. It is
    called before any state change or effect; a pair it cannot resolve fails the run with
    ``required_norm_unavailable`` (``reference_kind: analysis_profile``) and no stage runs.
    The served application always passes the section-keyed registry
    (``bootstrap/composition.py``). ``None`` supplies no registry and a run that is not the
    AR v3 beta pair is refused like an unregistered pair; it used to run the v1 AR profile
    (`PROD-11-AR-V1-V2-REMOVAL-01`, ``AD-12``).

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
        if prior_cost.basis == "unmetered":
            # Earlier calls went through a connection with no per-call cost: they are counted,
            # and they are not a priced contribution the balance could mislabel.
            meter.unmetered_calls = prior_cost.model_call_count
        else:
            # A persisted opening balance cannot be re-priced by this Attempt. Even a
            # zero-cost earlier call may have been estimated, so a resumed meter must
            # never re-label that historical contribution as measured.
            meter.unpriced_contributions = max(meter.unpriced_contributions, 1)

    run = run_repo.get(session, run_id)
    # Only the exact sealed pair and an installed server-owned reviewed pack may
    # enter the v3 branch. In production the registry is still empty; either
    # mismatched half refuses before Job, Blob or provider effects begin.
    v3_profile = run.analysis_profile_id == str(AR_V3_BETA_PROFILE_ID)
    v3_bundle = run.prompt_bundle_id == str(AR_V3_BETA_BUNDLE_ID)
    v3_exact = v3_profile and v3_bundle
    relaxed_limits = False if v3_exact else _section_relaxed_limits(session, run)
    meter.enforce_ceiling = not relaxed_limits
    # Cost preflight owns the accepted immutable consent. Import the public seam
    # at execution time because runs.public also exports this executor.
    from auditmanager.runs.public import read_run_cost_policy

    cost_policy = read_run_cost_policy(
        session, run_id=run_id, default_ceiling_usd=config.run_cost_ceiling_usd,
        runs=run_repo,
    )
    meter.enforce_ceiling = cost_policy.enforce_ceiling
    extended_policy = getattr(cost_policy,"extended_review",None)
    v3_workflow = isinstance(extended_policy,dict) and extended_policy.get("plan_version")=="extended-review-v3"
    image_only_v3 = False
    v3_pretext_invoked = False
    v3_pretext_ambiguous = False
    if cost_policy.approved:
        meter.ceiling_usd = cost_policy.ceiling_usd
        config = replace(
            config, run_cost_ceiling_usd=cost_policy.ceiling_usd,
            approved_window_characters=cost_policy.window_characters,
            approved_max_windows=cost_policy.max_windows, approved_cost_ceiling=True,
            approved_model_id=cost_policy.model_id,
            approved_rate_sha256=cost_policy.rate_sha256,
            approved_connection_revision_id=cost_policy.connection_revision_id,
        )
    if (v3_profile or v3_bundle) and (
        not v3_exact
        or not isinstance(ar_v3_pack_registry, TrustedPackRegistry)
        or ar_v3_pack_registry.select_beta() is None
    ):
        raise DomainError(
            ErrorCode.REQUIRED_NORM_UNAVAILABLE,
            message="the pinned AR v3 beta reviewed pack is not installed",
            reference_kind="analysis_profile",
            analysis_profile_id=run.analysis_profile_id,
            prompt_bundle_id=run.prompt_bundle_id,
        )
    text_profile = None if v3_exact else _pinned_text_profile(run, text_profiles)
    if text_profile is not None:
        output_cap = text_profile.prompt_bundle.max_output_tokens
        if (relaxed_limits and output_cap != 64_000) or (not relaxed_limits and output_cap == 64_000):
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="section Run limit policy and bundle disagree")

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
    from .commands import analysis_source_entry
    source_entry = analysis_source_entry(version)

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
    attempt_context = start_attempt_lease_heartbeat(session, authority)
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
    # `W55B-RECOGNISED-01`: a portal bundle's markdown and block list, when the version's
    # manifest holds them, reach `source_preparation` as its two optional inputs. A version
    # without a bundle has neither, and the stage runs exactly as before.
    for entry in version.manifest:
        if entry.role in (ROLE_SOURCE_MARKDOWN, ROLE_SOURCE_STRUCTURED_COMPANION):
            outputs.refs[entry.role] = ArtifactRef(
                role=entry.role,
                blob_id=str(entry.blob_id),
                sha256=entry.sha256,
                size_bytes=entry.size_bytes,
                media_type=entry.media_type,
            )

    observations_document: Mapping[str, Any] | None = None

    # Full interpretation belongs to this durable background Attempt, before
    # either model branch. Page receipts are actual progress, never a heartbeat
    # masquerading as work. Do not hold a DB transaction while a page interprets.
    last_pdf_check = 0.0
    last_pdf_event = float("-inf")
    last_pdf_pages = 0

    def pdf_checkpoint() -> None:
        nonlocal last_pdf_check
        now = time.monotonic()
        if now - last_pdf_check < 1.0:
            return
        job_repo.check_current_unlocked(session, authority)
        session.commit()
        last_pdf_check = now

    def pdf_progress(receipt: PdfPrecheckProgress) -> None:
        nonlocal last_pdf_event, last_pdf_pages, last_pdf_check
        now = time.monotonic()
        if receipt.completed_pages > last_pdf_pages:
            attempt_context.progress()
            last_pdf_pages = receipt.completed_pages
        if (receipt.phase == "checking" and receipt.completed_pages < receipt.total_pages
                and now - last_pdf_event < 1.0):
            return
        # This fence also suppresses a failed-progress write from a cancelled or
        # superseded Attempt. A read-only checkpoint alone cannot authorise writes.
        job_repo.require_current(session, authority)
        payload: dict[str, str | int | bool | None] = {
            "stage_id": "source_preparation", "phase": receipt.phase,
            "completed_pages": receipt.completed_pages, "total_pages": receipt.total_pages,
        }
        if receipt.error_code is not None:
            payload["error_code"] = receipt.error_code
        if receipt.reason is not None:
            payload["reason"] = receipt.reason
        append_execution_event(
            session, event_type="stage.pdf_precheck", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id, payload=payload,
        )
        session.commit()
        last_pdf_event = last_pdf_check = now

    # -- the three deterministic stages, in registry dependency order ---------
    if v3_workflow:
        from auditmanager.analysis.public import run_document_context_with_visual_pages
    deterministic = (
        (
            "source_preparation",
            (ROLE_SOURCE_DOCUMENT, ROLE_SOURCE_MARKDOWN, ROLE_SOURCE_STRUCTURED_COMPANION),
        ),
        # `W55B-GEOMETRY-01`: the block list, when the version has one, is normalised into
        # `geometry.portal_blocks` and its IMAGE blocks are cut as crops.
        (
            "page_geometry_extraction",
            (ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER, ROLE_SOURCE_STRUCTURED_COMPANION),
        ),
        ("document_context_build", (ROLE_BLOCK_INDEX, ROLE_TEXT_LAYER)),
    )
    halted = False
    for stage_id, roles in deterministic:
        run_repo.stage_started(session, run_id=run_id, stage_id=stage_id)
        session.commit()
        # Fresh statistics runs count crop bytes without the historical 2 GiB refusal.
        # Previously accepted commands retain their frozen relaxed_limits value.
        stage_store = CropByteBudget(
            _publication_store(
                session,
                store=blob_store,
                jobs=job_repo,
                blobs=blob_repo,
                authority=authority,
                stage_id=stage_id,
                checkpoint=effect_checkpoint,
            ),
            stage_id=stage_id,
            budget=None if relaxed_limits else MAX_CROP_BYTES,
        )
        result = run_stage(
            stage_id,
            version_uid=run.version_uid,
            inputs=outputs.blob_inputs(*roles),
            blob_store=stage_store,
            handler=(
                partial(run_source_preparation_with_progress, progress=pdf_progress,
                        checkpoint=pdf_checkpoint, expected_page_count=version.page_count,
                        **({"allow_visual_only_pages":True} if v3_workflow else {}))
                if stage_id == "source_preparation" else
                partial(run_document_context_with_visual_pages,allow_visual_only_pages=True)
                if v3_workflow and stage_id == "document_context_build" else None
            ),
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

    if v3_exact:
        # The last deterministic artifact binding holds the Lease row until
        # commit. The v3 request and reply readers do external Blob I/O without
        # that lock, and the journal commits each intent before its effect.
        session.commit()
        from auditmanager.runs.v3_review_terminal import finish_v3_review_run
        from auditmanager.runs.v3_worker import run_v3_worker_chain

        if halted:
            terminal = finish_v3_review_run(
                session, authority=authority, registry=ar_v3_pack_registry,
                jobs=job_repo, runs=run_repo,
            )
            dispatched = False
        else:
            outcome = run_v3_worker_chain(
                session, authority=authority, registry=ar_v3_pack_registry,
                blob_store=blob_store,
                provider_for_dispatch=lambda: _bind_provider(
                    session, run, attempt_context, providers, adapter, config,
                ),
                cost_ceiling_usd=config.run_cost_ceiling_usd,
                jobs=job_repo, runs=run_repo, documents=document_repo,
                blobs=blob_repo,
            )
            terminal, dispatched = outcome.terminal, outcome.dispatched
        attempts = not_attempted(policy)
        if dispatched:
            ledger = AttemptLedger(attempt_budget=1)
            ledger.record(status="succeeded", error=None, waited_seconds=0.0)
            attempts = ledger.close()
        return ExecutionResult(
            run_id=run_id, selection=terminal.selection,
            stage_statuses=terminal.stage_statuses,
            published_finding_count=0, diagnostic_count=0,
            gate_ran=not halted, model_attempts=attempts,
        )

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
        binding = None
        try:
            binding = _bind_provider(
                session, run, attempt_context, providers, adapter, config
            )
        except DomainError as refusal:
            # The connection cannot serve this Attempt (its key cannot be opened for its
            # address, its route is gone): the stage fails with that code and nothing is called.
            started_at = clock()
            attempts = not_attempted(policy)
            observations_document = None
            text_result = _text_stage_result(
                TextAnalysisOutcome(
                    status="failed", artifact=None, model_calls=(), error=refusal
                ),
                artifact_ref=None, attempts=attempts, started=started_at, finished=clock(),
            )
        else:
            v3_state = None
            v3_stage_result = None
            if v3_workflow:
                from auditmanager.analysis.public import extended_artifact_envelope
                from auditmanager.jobs.public import has_ambiguous_provider_effect
                from auditmanager.runs.extended_review import run_extended_review, load_saved_workflow
                resumed = load_saved_workflow(session,store=text_store,run=run)
                v3_stage_result=StageResult(stage_id="text_analysis",stage_version=TEXT_STAGE_VERSION,
                    status=StageStatus.PARTIAL,metrics={"primary_text_pending":True},
                    error=StageError.from_domain_error(DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                        stage_id="text_analysis",reason="primary_text_pending")),started_at=clock())
                _persist(session,run_repo,run_id,v3_stage_result);session.commit()

                def v3_checkpoint(boundary):
                    job_repo.require_current(session,authority)
                    if run_repo.get(session,run_id).state != "running":
                        raise DomainError(ErrorCode.STALE_ATTEMPT,aggregate_type="Attempt")
                    session.commit()
                    if effect_checkpoint is not None:effect_checkpoint(boundary)

                def v3_publish(role,body):
                    ref,_=publish_artifact(text_store,role,extended_artifact_envelope(role,run.version_uid,**body))
                    for blob_id in job_repo.bind_artifacts(session,authority,stage_id="text_analysis",artifacts=(ref,)):
                        blob_repo.mark_available(session,blob_id)
                    session.commit()
                    return ref

                v3_last_progress=(meter.call_count,0,0)
                def v3_progress(status,result):
                    nonlocal v3_stage_result,v3_last_progress
                    ref=v3_publish("analysis.extended_review",{"run_id":run_id,"status":status,"result":result})
                    artifacts=tuple(a for a in v3_stage_result.artifacts if a.role != "analysis.extended_review")
                    pending=result.get("primary_text_status")=="pending"
                    metrics={**v3_stage_result.metrics,"primary_text_pending":pending,
                        "extended_review_status":status,"extended_blocks_processed":result["coverage"]["blocks_processed"],
                        "extended_blocks_total":result["coverage"]["blocks_total"]}
                    for procedure in result.get("procedures",[]):metrics["extended_"+procedure["id"]]=procedure["status"]
                    degraded=not pending and status in {"partial","failed","unavailable"} and v3_stage_result.status is StageStatus.SUCCEEDED
                    v3_stage_result=replace(v3_stage_result,artifacts=(*artifacts,ref),metrics=metrics,
                        status=StageStatus.PARTIAL if degraded else v3_stage_result.status,
                        error=StageError.from_domain_error(DomainError(ErrorCode.ANALYSIS_FAILED,
                            message="the accepted section workflow did not fully complete")) if degraded else v3_stage_result.error)
                    _persist(session,run_repo,run_id,v3_stage_result);outputs.absorb(v3_stage_result);session.commit()
                    actual_progress=(meter.call_count,result["coverage"]["blocks_processed"],
                        sum(p["status"] in {"completed","partial","failed","unavailable"} for w in result.get("windows",[]) for p in w.get("procedures",[])))
                    if actual_progress != v3_last_progress:
                        attempt_context.progress();v3_last_progress=actual_progress

                def v3_bind_native(artifacts):
                    for blob_id in job_repo.bind_artifacts(session,authority,stage_id="text_analysis",artifacts=artifacts):
                        blob_repo.mark_available(session,blob_id)
                    session.commit()

                v3_pretext_invoked=True
                v3_state=run_extended_review(session,run=run,authority=authority,jobs=job_repo,
                    journal=_DurableCallJournal(session,job_repo,authority,effect_checkpoint,call=binding.call,context=attempt_context),
                    binding=binding,outputs=outputs,store=text_store,meter=meter,publish=v3_publish,progress=v3_progress,
                    checkpoint=v3_checkpoint,observations_document=None,snapshot_id=run.norms_snapshot_id,
                    profile_sha256=text_profile.content_sha256,policy=extended_policy,bind_native=v3_bind_native,resume_state=resumed,
                    visual_only=True)
                v3_pretext_ambiguous=has_ambiguous_provider_effect(session,run_id=run_id);session.commit()
                native_document,_=read_artifact(text_store,parse_blob_id(outputs.refs[ROLE_TEXT_LAYER].blob_id),expected_role=ROLE_TEXT_LAYER)
                image_only_v3=native_document.get("total_char_count",0)==0
            if v3_workflow and (image_only_v3 or v3_pretext_ambiguous
                    or "extended_rules_changed_requires_consent" in (v3_state or {}).get("warnings",[])
                    or "cost_budget_exceeded" in (v3_state or {}).get("warnings",[])):
                reason=("provider_outcome_unknown" if v3_pretext_ambiguous else "cost_budget_exceeded"
                    if "cost_budget_exceeded" in (v3_state or {}).get("warnings",[]) else
                    "native_text_unavailable_visual_only" if image_only_v3 else "extended_rules_changed_requires_consent")
                error=DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,stage_id="text_analysis",reason=reason)
                text_result=_text_stage_result(TextAnalysisOutcome(status="failed" if v3_pretext_ambiguous else "partial",
                    artifact=None,model_calls=(),error=error),artifact_ref=None,attempts=not_attempted(policy),started=clock(),finished=clock())
                observations_document=None
                if image_only_v3 and not v3_pretext_ambiguous:
                    from auditmanager.analysis.public import empty_native_text_observations
                    observations_document=empty_native_text_observations(run_id=run_id,version_uid=run.version_uid,
                        profile=text_profile,provider_mode=binding.adapter.provider_mode)
                    empty_ref,_=publish_artifact(text_store,"analysis.text_observations",observations_document)
                    text_result=replace(text_result,artifacts=(empty_ref,),metrics={**text_result.metrics,
                        "native_text_unavailable":True,"model_call_count":0,"pages_analysed":0})
            else:
                text_result, observations_document, attempts = _run_text_analysis_stage(
                run_id=run_id,
                version_uid=run.version_uid,
                outputs=outputs,
                blob_store=text_store,
                adapter=binding.adapter,
                provider_config=binding.config,
                cost_meter=meter,
                policy=policy,
                sleep=sleep,
                clock=clock,
                call_journal=_DurableCallJournal(
                    session, job_repo, authority, effect_checkpoint,
                    call=binding.call, context=attempt_context,
                ),
                profile=text_profile,
                call=binding.call,
                text_character_count=version.text_character_count,
                textless_pages=version.textless_pages,
                relaxed_limits=relaxed_limits,
                force_durable_windows=v3_workflow,
                window_custody=(None if version.text_character_count is None
                                and getattr(version, "upload_kind", None) != "comparison_pdf"
                                else WindowReplyCustody(
                    session=session, jobs=job_repo, authority=authority, store=text_store,
                    mode=binding.adapter.provider_mode,
                    provider="anthropic" if binding.call is None else binding.call.provider_label,
                    max_reply_bytes=None if relaxed_limits else MAX_REPLY_BYTES,
                )),
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
        if v3_workflow and v3_pretext_invoked:
            v3_stage_result=text_result
            v3_pretext_ambiguous=has_ambiguous_provider_effect(session,run_id=run_id);session.commit()
            if (not v3_pretext_ambiguous and "extended_rules_changed_requires_consent" not in v3_state.get("warnings",[])
                    and "cost_budget_exceeded" not in v3_state.get("warnings",[])):
                v3_state=run_extended_review(session,run=run,authority=authority,jobs=job_repo,
                    journal=_DurableCallJournal(session,job_repo,authority,effect_checkpoint,call=binding.call,context=attempt_context),
                    binding=binding,outputs=outputs,store=text_store,meter=meter,publish=v3_publish,progress=v3_progress,
                    checkpoint=v3_checkpoint,observations_document=observations_document,snapshot_id=run.norms_snapshot_id,
                    profile_sha256=text_profile.content_sha256,policy=extended_policy,bind_native=v3_bind_native,
                    resume_state=v3_state,visual_only=False)
            elif v3_pretext_ambiguous or "cost_budget_exceeded" in v3_state.get("warnings",[]):
                stopped_reason="provider_outcome_unknown" if v3_pretext_ambiguous else "cost_budget_exceeded"
                v3_state["status"]="failed" if v3_pretext_ambiguous else "partial"
                for window in v3_state.get("windows",[]):
                    for procedure in window.get("procedures",[]):
                        if procedure["status"] in {"queued","running"}:
                            procedure.update(status="skipped",reason=stopped_reason)
                for procedure in v3_state.get("procedures",[]):
                    if procedure["status"] in {"queued","running"}:
                        procedure.update(status="skipped",reason=stopped_reason)
                v3_state.setdefault("warnings",[]).append("extended_provider_outcome_unknown" if v3_pretext_ambiguous else "cost_budget_exceeded")
            v3_state["primary_text_status"]=("unavailable" if image_only_v3 else
                "completed" if text_result.status is StageStatus.SUCCEEDED else text_result.status.value)
            if v3_state.get("report") is not None:
                v3_state["report"]["primary_text_status"]=v3_state["primary_text_status"]
            v3_progress(v3_state.get("status","partial"),v3_state)
            text_result=v3_stage_result
        outputs.absorb(text_result)
        # D-141 (`W54-WORKER-01`). Binding the text artifacts checked the authority, which
        # locks the Lease row. Committing here releases it, so the lease heartbeat keeps
        # extending the Lease while the evidence gate runs; the final transaction below
        # takes the Lease lock again only in `finish_execution`, for its last writes. The
        # deterministic stages already commit at the next `stage_started`, so this makes
        # the text stage durable exactly as they are.
        session.commit()

        # HOTFIX-ANALYSIS-1030. A fresh accepted cost authority alone enables
        # this additive preliminary review. Old accepted commands never buy
        # additional calls merely because a worker was upgraded.
        from auditmanager.analysis.public import extended_review_enabled
        extended_policy = getattr(cost_policy, "extended_review", None)
        v2_workflow = isinstance(extended_policy, dict) and extended_policy.get("plan_version") in {"extended-review-v2","extended-review-v3"}
        if (not v3_pretext_invoked and extended_review_enabled(extended_policy)
                and (v2_workflow or text_result.status in {StageStatus.SUCCEEDED, StageStatus.PARTIAL})):
            from auditmanager.analysis.public import extended_artifact_envelope
            from auditmanager.runs.extended_review import run_extended_review, planned_workflow_result

            def extended_checkpoint(boundary: str) -> None:
                job_repo.require_current(session, authority)
                current_run = run_repo.get(session, run_id)
                if current_run.state != "running":
                    raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
                session.commit()
                if effect_checkpoint is not None:
                    effect_checkpoint(boundary)

            def publish_extended(role: str, body: dict[str, Any]) -> ArtifactRef:
                ref, _ = publish_artifact(text_store, role,
                    extended_artifact_envelope(role, run.version_uid, **body))
                for blob_id in job_repo.bind_artifacts(session, authority,
                        stage_id="text_analysis", artifacts=(ref,)):
                    blob_repo.mark_available(session, blob_id)
                session.commit()
                return ref

            def extended_progress(status: str, result: dict[str, Any]) -> None:
                nonlocal text_result
                ref = publish_extended("analysis.extended_review",
                    {"run_id": run_id, "status": status, "result": result})
                artifacts = tuple(a for a in text_result.artifacts if a.role != "analysis.extended_review")
                metrics = {**text_result.metrics, "extended_review_status": status,
                    "extended_blocks_processed": result["coverage"]["blocks_processed"],
                    "extended_blocks_total": result["coverage"]["blocks_total"]}
                for procedure in result.get("procedures", []):
                    metrics["extended_"+procedure["id"]] = procedure["status"]
                degraded = status in {"failed","partial","unavailable"} and text_result.status is StageStatus.SUCCEEDED
                text_result = replace(text_result, artifacts=(*artifacts, ref), metrics=metrics,
                    status=StageStatus.PARTIAL if degraded else text_result.status,
                    error=StageError.from_domain_error(DomainError(ErrorCode.ANALYSIS_FAILED,
                        message="the accepted extended analysis workflow did not fully complete")) if degraded else text_result.error)

                _persist(session, run_repo, run_id, text_result)
                outputs.absorb(text_result)
                session.commit()

            def bind_native(artifacts):
                for blob_id in job_repo.bind_artifacts(session,authority,stage_id="text_analysis",artifacts=artifacts):
                    blob_repo.mark_available(session,blob_id)
                session.commit()

            skip_reason = None
            if text_result.status is StageStatus.FAILED:
                # Source-safe visual work is independent of text parser/admission success.
                # Unknown paid text effects and unavailable routes forbid further dispatch.
                unknown = any(effect.run_id == run_id for effect in job_repo.unresolved_provider_effects(session))
                session.commit()
                if unknown:
                    skip_reason = "provider_outcome_unknown"
                elif binding is None:
                    skip_reason = "provider_binding_unavailable"
                elif text_result.error is not None and text_result.error.code in {
                        ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED, ErrorCode.MODEL_IDENTITY_MISMATCH}:
                    skip_reason = "provider_binding_unavailable"
            if skip_reason:
                skipped = planned_workflow_result(reason=skip_reason,terminal=True,policy=extended_policy)
                extended_progress("unavailable",skipped)
            else:
                run_extended_review(session, run=run, authority=authority, jobs=job_repo,
                    journal=_DurableCallJournal(session, job_repo, authority, effect_checkpoint,
                        call=binding.call, context=attempt_context),
                    binding=binding, outputs=outputs, store=text_store, meter=meter,
                    publish=publish_extended, progress=extended_progress,
                    checkpoint=extended_checkpoint, observations_document=observations_document,
                    snapshot_id=run.norms_snapshot_id, profile_sha256=text_profile.content_sha256,
                    policy=extended_policy,bind_native=bind_native)

    # `W54-JUDGE-Y` F5: the gate's artifacts are read from the store here, before the
    # advance below locks the run row, so no S3 read happens under that lock.
    gate_inputs = _read_gate_inputs(
        observations_document=observations_document, outputs=outputs, blob_store=blob_store
    )

    run_repo.advance(session, run_id=run_id, from_state="running", to_state="validating")

    # -- validating: the evidence gate, then the terminal it implies ----------
    gate_ran, publication = _run_evidence_gate(session, run=run, inputs=gate_inputs)

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
        stop_attempt_lease_heartbeat()


__all__ = [
    "Checkpoint",
    "Clock",
    "EffectCheckpoint",
    "ExecutionResult",
    "Sleep",
    "TextProfileResolver",
    "execute_run",
]
