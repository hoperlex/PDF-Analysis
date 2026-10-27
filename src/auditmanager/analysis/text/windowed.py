"""The ``text_analysis`` stage over whole-page windows (`SECTION-CHUNKED-ANALYSIS-01`).

:func:`run_text_analysis_windows` is :func:`~auditmanager.analysis.text.stage.run_text_analysis` for a volume
above the one-call budget. It adds nothing to the question the model answers or to what counts as a finding;
it changes how much of the text one call sees, and it keeps every guarantee the single call has:

* **One call per window, one ceiling.** The :class:`~auditmanager.analysis.text.cost.CostMeter` is the run's
  (the executor builds it once per run, from the persisted spend, so it is shared by every window and every
  Attempt). Before a fresh call ``check_before_call`` stops a run already at the ceiling; after it ``charge``
  stops a run the call carried past it, and the call that crossed is still recorded. Either stop fails the stage
  ``cost_budget_exceeded``, names the window, and publishes nothing.
* **One effect journal entry per window.** The same :class:`~auditmanager.analysis.text.stage.ModelCallJournal`
  (prepare, response_received, complete) is driven once per fresh window. Between ``response_received`` and
  ``complete`` the window's reply is handed to the :class:`~auditmanager.analysis.text.windows.WindowCustody`,
  and the call is completed with the window's identity and the reply's reference in its ``parameters``. A
  later call of the same run recovers a finished window by its key and **makes no call and charges nothing**
  for it.
* **Document-global offsets.** Windows are whole pages of the one text layer; quotes are bound against the full
  layer by :func:`~auditmanager.analysis.text.window_cohort.bind_window_claim_cohort` over the complete tuple of
  replies (a missing reply is a refusal, never an empty one), so an anchor is where it would be in a single
  call, and ``build_text_observations`` and the evidence gate run once over the merged set, unchanged.
* **Nothing is hidden.** A window whose reply is not a JSON observation list (and was not cut short) fails the
  stage naming the window, where a single call would read the same reply as "no findings"; a run that did not
  finish publishes none of the observations of the windows that did. Every window is analysed on its own: a
  finding that needs two windows is not found, the model is told so, and ``stage_result.metrics`` says it
  (:data:`~auditmanager.analysis.text.windows.WINDOWS_NOTE`).

A plan of one window is not this path: it is delegated to ``run_text_analysis`` unchanged.
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from auditmanager.analysis.text.adapter import PROVIDER, ModelAdapter, ModelResponse
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor
from auditmanager.analysis.text.artifact import Observation, build_text_observations
from auditmanager.analysis.text.binding import CallBinding
from auditmanager.analysis.text.chunk_preflight import ChunkPreflightError, TextChunk
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode, load_provider_config
from auditmanager.analysis.text.cost import BUDGET_SCOPE_RUN, CostMeter
from auditmanager.analysis.text.lock import STAGE_ID, ProviderLock, provider_lock
from auditmanager.analysis.text.profile import AnalysisProfile
from auditmanager.analysis.text.prompt import canonical_json
from auditmanager.analysis.text.provenance import (
    CALL_SUCCEEDED,
    CALL_TRUNCATED,
    ModelCallRecord,
    assert_consistent_mode,
)
from auditmanager.analysis.text.proxy import ProxyDispatchError
from auditmanager.analysis.text.response import ParsedResponse, parse_response
from auditmanager.analysis.text.stage import (
    STAGE_VERSION,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    ModelCallJournal,
    TextAnalysisOutcome,
    _check_graph_version,
    _identity_refusal,
    _journal_failed_call,
    _pages_analysed,
    _partial_error,
    run_text_analysis,
)
from auditmanager.analysis.text.textlayer import TextLayer, load_text_layer
from auditmanager.analysis.text.window_anchor import WindowAnchorError
from auditmanager.analysis.text.window_cohort import (
    WindowQuoteClaim,
    WindowReplyClaims,
    bind_window_claim_cohort,
)
from auditmanager.analysis.text.windows import (
    WINDOWS_NOTE,
    WindowCustody,
    WindowIdentity,
    WindowPlan,
    WindowPolicy,
    build_window_request,
    plan_text_windows,
    window_key,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId


@dataclass(frozen=True, slots=True)
class _Reply:
    """One window's reply, fresh or recovered, parsed and not yet grounded."""

    window: TextChunk
    model_call_id: ModelCallId
    response: ModelResponse
    parsed: ParsedResponse
    recovered: bool


def _where(window: TextChunk, count: int) -> str:
    return f"window {window.index + 1} of {count} (pages {window.first_page}-{window.last_page})"


def _failure(
    error: DomainError,
    metrics: Mapping[str, Any],
    *,
    model_calls: Sequence[ModelCallRecord] = (),
    uncertain: bool = False,
) -> TextAnalysisOutcome:
    """A failed stage. The transport facts of ``error`` are carried exactly as ``run_text_analysis`` carries them."""
    dispatch = isinstance(error, ProxyDispatchError)
    return TextAnalysisOutcome(
        status=STATUS_FAILED,
        artifact=None,
        model_calls=tuple(model_calls),
        error=error,
        metrics=dict(metrics),
        provider_effect_uncertain=uncertain,
        provider_retry_allowed=error.retry_safe if dispatch else None,
        retry_after_seconds=error.retry_after_seconds if dispatch else 0.0,
    )


def _window_record(
    model_call_id: ModelCallId,
    request: Any,
    response: ModelResponse,
    *,
    mode: ProviderMode,
    status: str,
    cost_usd: float,
    cost_basis: str,
    provider: str,
    parameters: Mapping[str, Any],
) -> ModelCallRecord:
    """The window's ``model_call`` record: the request's parameters plus the window's identity and reply reference."""
    return ModelCallRecord(
        model_call_id=model_call_id,
        provider=provider,
        model_id=request.model_id,
        provider_mode=mode,
        parameters=dict(parameters),
        request_sha256=request.request_sha256,
        response_sha256=response.response_sha256,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        status=status,
        cost_usd=cost_usd,
        cost_basis=cost_basis,
    )


def _ground_cohort(
    plan: WindowPlan,
    replies: Sequence[_Reply],
    block_index: BlockIndex | None,
) -> tuple[list[list[Observation]], int, int, int, int]:
    """Bind every window's quotes against the full layer and rebuild observations per window.

    Returns the observations of each window, the resolved evidence count, the unresolved evidence count,
    the evidence dropped for naming a page outside its own window, and the dropped observation count.
    A claim on a page outside its window never reaches the cohort (it would refuse the whole cohort); it is
    an unresolved anchor like a quote on the wrong page is in a single call: counted, never published.
    """
    claims_per_window: list[tuple[WindowQuoteClaim, ...]] = []
    for reply in replies:
        claims = tuple(
            WindowQuoteClaim(item.page_number, item.quote)
            for proposal in reply.parsed.observations
            for item in proposal.evidence
            if reply.window.first_page <= item.page_number <= reply.window.last_page
        )
        claims_per_window.append(claims)
    bound = bind_window_claim_cohort(
        plan.layer,
        plan.windows,
        tuple(WindowReplyClaims(index, claims) for index, claims in enumerate(claims_per_window)),
    )

    resolved_count = 0
    unresolved_count = 0
    outside_count = 0
    dropped = 0
    observations: list[list[Observation]] = []
    for reply, bound_window in zip(replies, bound, strict=True):
        anchors = iter(bound_window.anchors)
        window_observations: list[Observation] = []
        for proposal in reply.parsed.observations:
            kept: list[ResolvedAnchor] = []
            for item in proposal.evidence:
                if not reply.window.first_page <= item.page_number <= reply.window.last_page:
                    outside_count += 1
                    unresolved_count += 1
                    continue
                anchor = next(anchors)
                if isinstance(anchor, ResolvedAnchor):
                    if block_index is not None:
                        anchor = dataclasses.replace(
                            anchor,
                            block_id=block_index.containing(
                                anchor.page_number, anchor.char_start, anchor.char_end
                            ),
                        )
                    kept.append(anchor)
                else:
                    unresolved_count += 1
            if not kept:
                dropped += 1
                continue
            resolved_count += len(kept)
            window_observations.append(
                Observation(
                    category=proposal.category,
                    finding_text=proposal.finding_text,
                    recommendation_text=proposal.recommendation_text,
                    model_call_id=reply.model_call_id,
                    evidence=tuple(kept),
                )
            )
        observations.append(window_observations)
    return observations, resolved_count, unresolved_count, outside_count, dropped


def run_text_analysis_windows(
    *,
    run_id: RunId,
    text_layer_document: Mapping[str, Any],
    adapter: ModelAdapter,
    policy: WindowPolicy,
    config: ProviderConfig | None = None,
    document_graph: Mapping[str, Any] | None = None,
    block_index_document: Mapping[str, Any] | None = None,
    profile: AnalysisProfile,
    lock: ProviderLock | None = None,
    meter: CostMeter | None = None,
    call_journal: ModelCallJournal | None = None,
    call: CallBinding | None = None,
    custody: WindowCustody | None = None,
) -> TextAnalysisOutcome:
    """Run the stage over one document version in whole-page windows. Same contract as ``run_text_analysis``.

    ``policy`` says how large a window is and how many a run takes; ``custody`` lets a finished window survive a
    restart and is required for a live run with more than one window (without it a restart would pay for the
    finished windows again, and a live run does not start on that footing).
    """
    resolved_config = config or load_provider_config()
    resolved_lock = lock or provider_lock()
    pin = resolved_lock.model(resolved_config.model_id)
    cost_meter = meter or CostMeter(ceiling_usd=resolved_config.run_cost_ceiling_usd)
    base: dict[str, Any] = {"stage_id": STAGE_ID, "stage_version": STAGE_VERSION}

    try:
        text_layer = load_text_layer(text_layer_document)
        _check_graph_version(document_graph)
        block_index = BlockIndex.from_document(block_index_document)
        plan = plan_text_windows(text_layer, policy)
    except DomainError as error:
        return _failure(error, base)

    if len(plan.windows) == 1:
        # One window is the single call: the same request bytes, the same recording, the same artifact.
        return run_text_analysis(
            run_id=run_id,
            text_layer_document=text_layer_document,
            adapter=adapter,
            config=resolved_config,
            document_graph=document_graph,
            block_index_document=block_index_document,
            profile=profile,
            lock=resolved_lock,
            meter=cost_meter,
            call_journal=call_journal,
            call=call,
        )

    count = len(plan.windows)
    base.update(
        windows_total=count,
        window_characters_ceiling=plan.window_characters,
        windows_limit=policy.max_windows,
    )
    mode = adapter.provider_mode
    if mode is ProviderMode.LIVE and (call_journal is None or custody is None):
        reason = "durable_call_journal_required" if call_journal is None else "durable_window_custody_required"
        return _failure(
            DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message=(
                    "a live provider call requires a durable call journal"
                    if call_journal is None
                    else "a live run in windows requires durable window custody"
                ),
                stage_id=STAGE_ID,
                reason=reason,
            ),
            base,
        )

    provider_label = PROVIDER if call is None else call.provider_label
    unmetered = call is not None and call.unmetered
    replies: list[_Reply] = []
    records: list[ModelCallRecord] = []
    request_digests: list[str] = []

    for window in plan.windows:
        where = _where(window, count)
        request = build_window_request(
            model_id=resolved_config.model_id,
            bundle=profile.prompt_bundle,
            plan=plan,
            window=window,
            idempotency_scope=str(run_id),
        )
        request_digests.append(request.request_sha256)
        identity = WindowIdentity(
            key=window_key(
                plan=plan,
                window=window,
                profile_sha256=profile.content_sha256,
                model_id=resolved_config.model_id,
                request_sha256=request.request_sha256,
            ),
            index=window.index,
            count=count,
            first_page=window.first_page,
            last_page=window.last_page,
        )
        progress = {
            **base,
            "windows_completed": len(replies),
            "failed_window": window.index + 1,
            "failed_window_first_page": window.first_page,
            "failed_window_last_page": window.last_page,
        }

        try:
            recovered = None if custody is None else custody.recover(identity.key)
        except DomainError as error:
            return _failure(error, progress, model_calls=records)

        if recovered is not None:
            response, model_call_id = recovered.response, recovered.model_call_id
        else:
            try:
                cost_meter.check_before_call()
            except DomainError:
                return _failure(
                    DomainError(
                        ErrorCode.COST_BUDGET_EXCEEDED,
                        message=(
                            f"the per-run model cost ceiling is exhausted; the run stopped before {where} "
                            f"after {len(replies)} of {count} windows and published nothing"
                        ),
                        budget_scope=BUDGET_SCOPE_RUN,
                    ),
                    {**progress, "cost_usd": round(cost_meter.spent_usd, 8),
                     "cost_ceiling_usd": cost_meter.ceiling_usd},
                    model_calls=records,
                )
            model_call_id = (
                ModelCallId.new() if call_journal is None
                else call_journal.prepare(request, mode=mode)
            )
            try:
                response = adapter.complete(request)
                refusal = _identity_refusal(response, call, mode)
                if refusal is not None:
                    raise refusal
            except DomainError as error:
                if call_journal is not None:
                    _journal_failed_call(call_journal, model_call_id, error, mode=mode)
                return _failure(
                    error,
                    progress,
                    model_calls=records,
                    uncertain=mode is ProviderMode.LIVE and not (
                        isinstance(error, ProxyDispatchError)
                        and error.dispatch_class != "outcome_unknown"
                    ),
                )
            if call_journal is not None:
                call_journal.response_received(model_call_id, response)
            call_status = CALL_TRUNCATED if response.truncated else CALL_SUCCEEDED
            extra: Mapping[str, Any] = {}
            if custody is not None:
                try:
                    extra = custody.preserve(
                        model_call_id=model_call_id, window=identity, request=request, response=response
                    )
                except DomainError as error:
                    # The answer was received and may have been paid for, and its text is not kept:
                    # not repeatable, and the effect stays `response_received` for reconciliation.
                    return _failure(
                        error, progress, model_calls=records,
                        uncertain=mode is ProviderMode.LIVE,
                    )
            parameters = {**request.parameters, **identity.as_parameters(), **dict(extra)}
            try:
                cost = (
                    cost_meter.record_unmetered() if unmetered else cost_meter.charge(
                        pin,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        reported_cost_usd=response.reported_cost_usd,
                    )
                )
            except DomainError:
                overrun_call = _window_record(
                    model_call_id, request, response, mode=mode, status=call_status,
                    cost_usd=pin.cost_usd(
                        input_tokens=response.input_tokens, output_tokens=response.output_tokens
                    ),
                    cost_basis="estimated", provider=provider_label, parameters=parameters,
                )
                if call_journal is not None:
                    call_journal.complete(overrun_call)
                return _failure(
                    DomainError(
                        ErrorCode.COST_BUDGET_EXCEEDED,
                        message=(
                            f"the per-run model cost ceiling was exceeded by {where}; the run stopped "
                            f"after {len(replies) + 1} of {count} windows and published nothing"
                        ),
                        budget_scope=BUDGET_SCOPE_RUN,
                    ),
                    {**progress, "windows_completed": len(replies) + 1,
                     "provider_mode": mode.value, "cost_usd": round(cost_meter.spent_usd, 8),
                     "cost_basis": cost_meter.cost_basis,
                     "cost_ceiling_usd": cost_meter.ceiling_usd,
                     "input_tokens": response.input_tokens,
                     "output_tokens": response.output_tokens,
                     "output_tokens_source": "provider", "call_status": call_status},
                    model_calls=[*records, overrun_call],
                )
            record = _window_record(
                model_call_id, request, response, mode=mode, status=call_status, cost_usd=cost,
                provider=provider_label, parameters=parameters,
                cost_basis=(
                    "unmetered" if unmetered
                    else "measured" if response.reported_cost_usd is not None else "estimated"
                ),
            )
            if call_journal is not None:
                call_journal.complete(record)
            records.append(record)

        parsed = parse_response(response.output_text, truncated=response.truncated)
        if parsed.salvaged and not response.truncated:
            return _failure(
                DomainError(
                    ErrorCode.ANALYSIS_FAILED,
                    message=(
                        f"the model reply for {where} is not a valid observation list; "
                        "the run is not published"
                    ),
                    stage_id=STAGE_ID,
                ),
                progress,
                model_calls=records,
            )
        replies.append(_Reply(window, model_call_id, response, parsed, recovered is not None))

    try:
        grounded, resolved, unresolved, outside, dropped = _ground_cohort(plan, replies, block_index)
    except (WindowAnchorError, ChunkPreflightError):
        # The cohort refuses an inconsistent plan or reply set; it is never skipped past.
        return _failure(
            DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message="the window replies could not be bound to the saved text; the run is not published",
                stage_id=STAGE_ID,
            ),
            {**base, "windows_completed": len(replies)},
            model_calls=records,
        )

    for reply, window_observations in zip(replies, grounded, strict=True):
        if reply.response.truncated and not window_observations:
            return _failure(
                DomainError(
                    ErrorCode.ANALYSIS_FAILED,
                    message=(
                        f"the provider reply for {_where(reply.window, count)} was cut short and "
                        "yielded no usable observation"
                    ),
                    stage_id=STAGE_ID,
                ),
                {**base, "windows_completed": len(replies),
                 "failed_window": reply.window.index + 1,
                 "failed_window_first_page": reply.window.first_page,
                 "failed_window_last_page": reply.window.last_page},
                model_calls=records,
            )

    truncated_any = any(reply.response.truncated for reply in replies)
    analysed: list[int] = []
    for reply, window_observations in zip(replies, grounded, strict=True):
        pages = plan.pages_of(reply.window)
        if reply.response.truncated:
            window_layer = TextLayer(
                version_uid=plan.layer.version_uid,
                normalization_id=plan.layer.normalization_id,
                pages=pages,
                document_text=reply.window.text,
            )
            analysed.extend(_pages_analysed(window_layer, window_observations, truncated=True))
        else:
            analysed.extend(page.page_number for page in pages)
    observations = [observation for window_observations in grounded for observation in window_observations]

    call_status = CALL_TRUNCATED if truncated_any else CALL_SUCCEEDED
    metrics: dict[str, Any] = {
        **base,
        "provider_mode": mode.value,
        "model_id": resolved_config.model_id,
        "analysis_profile_sha256": profile.content_sha256,
        "prompt_bundle_sha256": profile.prompt_bundle.content_sha256,
        "windows_request_sha256": hashlib.sha256(
            canonical_json(request_digests).encode("utf-8")
        ).hexdigest(),
        "pages_total": len(plan.layer.pages),
        "pages_analysed": len(analysed),
        "observations_proposed": sum(len(r.parsed.observations) for r in replies),
        "observations_emitted": len(observations),
        "input_tokens": sum(r.response.input_tokens for r in replies),
        "output_tokens": sum(r.response.output_tokens for r in replies),
        "output_tokens_source": "provider",
        "call_status": call_status,
        "observations_dropped_unresolved": dropped,
        "evidence_emitted": resolved,
        "evidence_unresolved": unresolved,
        "evidence_outside_window": outside,
        "proposals_malformed": sum(r.parsed.malformed_count for r in replies),
        "cost_usd": round(cost_meter.spent_usd, 8),
        "cost_basis": cost_meter.cost_basis,
        "cost_ceiling_usd": cost_meter.ceiling_usd,
        "latency_ms": sum(r.response.latency_ms for r in replies),
        "windows_analysed": count,
        "windows_recovered": sum(1 for r in replies if r.recovered),
        "windows_independent": True,
        "windows_note": WINDOWS_NOTE,
    }
    try:
        assert_consistent_mode(mode, tuple(records))
        artifact = build_text_observations(
            run_id=run_id,
            profile=profile,
            provider_mode=mode,
            text_layer=plan.layer,
            pages_analysed=analysed,
            observations=observations,
        )
    except DomainError as error:
        return _failure(error, metrics, model_calls=records)

    if truncated_any:
        return TextAnalysisOutcome(
            status=STATUS_PARTIAL,
            artifact=artifact,
            model_calls=tuple(records),
            error=_partial_error(run_id),
            metrics=metrics,
        )
    return TextAnalysisOutcome(
        status=STATUS_SUCCEEDED,
        artifact=artifact,
        model_calls=tuple(records),
        error=None,
        metrics=metrics,
    )


__all__ = ["run_text_analysis_windows"]
