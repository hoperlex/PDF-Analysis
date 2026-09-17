"""The ``text_analysis`` stage: one document, one call, one artifact.

Registered on ``B2``'s in-process stage-runner seam (``S3``). This module owns the
stage's behaviour; the binding of :class:`TextAnalysisOutcome` onto the runner's
``StageResult`` is a one-function adaptation that belongs to whoever composes the two,
because ``src/auditmanager/analysis/{engine,ports,stages}`` is ``B2``'s tree.

What this stage does **not** do, stated here because each is a thing a reader might
otherwise expect:

* it performs no grounding verification and no persistence, and is never the authority
  on what becomes a finding - ``B4`` re-verifies every anchor independently;
* it writes no verdict and allocates no ``finding_uid``;
* it does not retry, does not fall back to a second model, and never truncates the
  document or drops pages to fit a budget.

Status mapping, from the stage registry's status policy (``skip_allowed: false``,
``partial_allowed: true``) and ``P02_SEAMS.md`` section 4.7:

* ``succeeded`` - the whole document was analysed. Carries no error.
* ``partial`` - usable observations over a **strict subset** of pages, with a typed
  error. Only a provider reply cut short at the output ceiling produces this.
* ``failed`` - everything else, including an unavailable provider
  (``dependency_unavailable``) and an exhausted cost ceiling
  (``cost_budget_exceeded``). An unavailable provider is never ``partial``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from auditmanager.analysis.text.adapter import PROVIDER, ModelAdapter, build_request
from auditmanager.analysis.text.anchors import (
    BlockIndex,
    ResolvedAnchor,
    UnresolvedAnchor,
    resolve_anchor,
)
from auditmanager.analysis.text.artifact import Observation, build_text_observations
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode, load_provider_config
from auditmanager.analysis.text.cost import CostMeter
from auditmanager.analysis.text.lock import STAGE_ID, ProviderLock, provider_lock
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE, AnalysisProfile
from auditmanager.analysis.text.provenance import (
    CALL_SUCCEEDED,
    CALL_TRUNCATED,
    ModelCallRecord,
    assert_consistent_mode,
)
from auditmanager.analysis.text.response import parse_response
from auditmanager.analysis.text.textlayer import TextLayer, load_text_layer
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId

STATUS_SUCCEEDED = "succeeded"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"

STAGE_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class TextAnalysisOutcome:
    """What the stage hands back. ``succeeded`` carries no error; nothing else may omit one."""

    status: str
    artifact: dict[str, Any] | None
    model_calls: tuple[ModelCallRecord, ...]
    error: DomainError | None
    metrics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status == STATUS_SUCCEEDED and self.error is not None:
            raise ValueError("a succeeded stage result carries no error")
        if self.status != STATUS_SUCCEEDED and self.error is None:
            raise ValueError(f"a {self.status} stage result requires a typed error")


@dataclass(frozen=True, slots=True)
class _Grounding:
    observations: list[Observation]
    resolved_evidence: int
    unresolved: list[UnresolvedAnchor]
    dropped_observations: int


def _partial_error(run_id: RunId) -> DomainError:
    """The typed error that accompanies ``partial``.

    The frozen catalog has no code meaning "a stage produced usable output over a
    strict subset of its input". ``partial_result_not_publishable`` is the closest:
    its declared intent is that a partial outcome and its missing set stay visible
    rather than being silently completed or silently degraded, which is exactly the
    claim being made. ``pages_analysed`` in the artifact carries the missing set.
    """
    return DomainError(
        ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE,
        message=(
            "the provider reply stopped at the output ceiling, so observations cover "
            "only part of the document"
        ),
        run_id=str(run_id),
    )


def _ground(
    text_layer: TextLayer,
    proposals: Sequence[Any],
    *,
    model_call_id: ModelCallId,
    block_index: BlockIndex | None,
) -> _Grounding:
    """Resolve every proposed quotation, and keep only what actually resolved.

    An evidence item is emitted only when its quotation is found: ``char_end -
    char_start`` must equal the code-point length of ``quote``, and there is no honest
    interval for a string that is not in the text layer. An observation left with no
    resolved evidence is dropped rather than written, because section 4.7 makes an
    evidence-free observation malformed - it is not the same thing as an ungrounded
    one, and the gate has no way to read it as a diagnostic.

    An observation with *some* resolved evidence is emitted with the items that
    resolved. ``B4`` re-verifies every one of them independently.
    """
    observations: list[Observation] = []
    unresolved: list[UnresolvedAnchor] = []
    resolved_count = 0
    dropped = 0
    for proposal in proposals:
        anchors: list[ResolvedAnchor] = []
        for item in proposal.evidence:
            outcome = resolve_anchor(
                text_layer,
                page_number=item.page_number,
                quote=item.quote,
                block_index=block_index,
            )
            if isinstance(outcome, ResolvedAnchor):
                anchors.append(outcome)
            else:
                unresolved.append(outcome)
        if not anchors:
            dropped += 1
            continue
        resolved_count += len(anchors)
        observations.append(
            Observation(
                category=proposal.category,
                finding_text=proposal.finding_text,
                recommendation_text=proposal.recommendation_text,
                model_call_id=model_call_id,
                evidence=tuple(anchors),
            )
        )
    return _Grounding(
        observations=observations,
        resolved_evidence=resolved_count,
        unresolved=unresolved,
        dropped_observations=dropped,
    )


def _pages_analysed(
    text_layer: TextLayer, observations: Sequence[Observation], *, truncated: bool
) -> list[int]:
    """Which pages the stage can honestly claim to have a complete report for.

    On a complete reply that is every page. On a reply the provider cut short it is
    the pages up to the furthest page a *complete* observation cites: past that point
    the report simply stopped, and there is no evidence either way about what is
    there. The final clamp covers the case where the model reached the last page and
    was still cut off - a truncated report never proves full coverage, and section 4.7
    requires ``pages_analysed`` to be a strict subset whenever the status is
    ``partial``.
    """
    pages = list(text_layer.page_numbers)
    if not truncated:
        return pages
    frontier = 0
    for observation in observations:
        for anchor in observation.evidence:
            frontier = max(frontier, anchor.page_number)
    analysed = [page for page in pages if page <= frontier]
    if analysed == pages:
        analysed = pages[:-1]
    return analysed


def run_text_analysis(
    *,
    run_id: RunId,
    text_layer_document: Mapping[str, Any],
    adapter: ModelAdapter,
    config: ProviderConfig | None = None,
    document_graph: Mapping[str, Any] | None = None,
    block_index_document: Mapping[str, Any] | None = None,
    profile: AnalysisProfile = AR_TEXT_PROFILE,
    lock: ProviderLock | None = None,
    meter: CostMeter | None = None,
) -> TextAnalysisOutcome:
    """Run the stage over one document version.

    ``document_graph`` is accepted because the stage registry declares it a required
    input and ``B2`` publishes it. PC-01 sends one narrow prompt over the whole text
    layer, so the graph is not folded into the prompt: section 4.6 calls it a
    convenience for the model and never evidence, and adding an unused convenience
    would change the request checksum for no gain. It is read only for the fail-closed
    version check.
    """
    resolved_config = config or load_provider_config()
    resolved_lock = lock or provider_lock()
    pin = resolved_lock.model(resolved_config.model_id)
    cost_meter = meter or CostMeter(ceiling_usd=resolved_config.run_cost_ceiling_usd)

    try:
        text_layer = load_text_layer(text_layer_document)
        _check_graph_version(document_graph)
        block_index = BlockIndex.from_document(block_index_document)
        request = build_request(
            model_id=resolved_config.model_id,
            bundle=profile.prompt_bundle,
            text_layer=text_layer,
        )
        cost_meter.check_before_call()
        response = adapter.complete(request)
    except DomainError as error:
        return TextAnalysisOutcome(
            status=STATUS_FAILED,
            artifact=None,
            model_calls=(),
            error=error,
            metrics={"stage_id": STAGE_ID, "stage_version": STAGE_VERSION},
        )

    # The mode is read off the adapter that produced this response, never off the
    # configuration, so a run configured "live" that in fact replayed is recorded as
    # what it was.
    mode = adapter.provider_mode
    model_call_id = ModelCallId.new()
    call_status = CALL_TRUNCATED if response.truncated else CALL_SUCCEEDED

    try:
        cost = cost_meter.charge(
            pin,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            reported_cost_usd=response.reported_cost_usd,
        )
    except DomainError as error:
        # The spend that broke the budget is still recorded: the run report should
        # show what was actually spent, and no observation is published.
        overrun = pin.cost_usd(
            input_tokens=response.input_tokens, output_tokens=response.output_tokens
        )
        return TextAnalysisOutcome(
            status=STATUS_FAILED,
            artifact=None,
            model_calls=(
                _record(
                    model_call_id,
                    request,
                    response,
                    mode=mode,
                    status=call_status,
                    cost_usd=overrun,
                    # `overrun` above is `pin.cost_usd(...)` -- the pin's own rates over
                    # the token counts. It does not consult `response.reported_cost_usd`,
                    # so this basis is estimated whatever the provider reported, and the
                    # success path below can legitimately say `measured` for the very same
                    # response. Spelled out rather than defaulted: see `_record`.
                    cost_basis="estimated",
                ),
            ),
            error=error,
            metrics={
                "stage_id": STAGE_ID,
                "stage_version": STAGE_VERSION,
                "provider_mode": mode.value,
                "cost_usd": round(cost_meter.spent_usd, 8),
                # Which of the two the figure above is. The transport reports a real number
                # for a proxied or direct call and reports nothing for a replay, so the
                # basis is known here and was being discarded one layer later.
                "cost_basis": (
                    "measured" if response.reported_cost_usd is not None else "estimated"
                ),
                "cost_ceiling_usd": cost_meter.ceiling_usd,
                "observations_emitted": 0,
                # The reply was paid for and never parsed. Reporting the spend without
                # what was bought is how a budget overrun becomes unreadable afterwards.
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "output_tokens_source": "provider",
                "call_status": call_status,
            },
        )

    call = _record(
        model_call_id,
        request,
        response,
        mode=mode,
        status=call_status,
        cost_usd=cost,
        # The response is in scope here and nowhere below, so this is where the basis is
        # known. My first attempt set it only on the error path's own metrics dict, so
        # the provenance reached the `model_call` row on both paths but reached the
        # stage metrics on the overrun path alone. `W11-FIX` finished that: the success
        # metrics dict below now carries the same expression.
        cost_basis="measured" if response.reported_cost_usd is not None else "estimated",
    )
    parsed = parse_response(response.output_text, truncated=response.truncated)
    grounding = _ground(
        text_layer, parsed.observations, model_call_id=model_call_id, block_index=block_index
    )
    analysed = _pages_analysed(
        text_layer, grounding.observations, truncated=response.truncated
    )

    metrics: dict[str, Any] = {
        "stage_id": STAGE_ID,
        "stage_version": STAGE_VERSION,
        "provider_mode": mode.value,
        "model_id": resolved_config.model_id,
        "analysis_profile_sha256": profile.content_sha256,
        "prompt_bundle_sha256": profile.prompt_bundle.content_sha256,
        "request_sha256": request.request_sha256,
        "pages_total": len(text_layer.pages),
        "pages_analysed": len(analysed),
        "observations_proposed": len(parsed.observations),
        "observations_emitted": len(grounding.observations),
        # Beside the finding count deliberately. `P4_CLOSURE.md` §6: precision evidence
        # on this corpus is saturated - zero findings across nine controls - so the next
        # question is not how many findings but whether the document was read at all, and
        # `observations_emitted` alone cannot tell a model that read and found nothing
        # from one that returned after ten tokens. These two figures only mean something
        # together, so they are emitted together.
        #
        # Both are the PROVIDER's own, lifted from its usage block by the adapter and
        # never recomputed from the response text. `output_tokens_source` says so on the
        # record rather than in a comment a consumer cannot read.
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "output_tokens_source": "provider",
        "call_status": call_status,
        "observations_dropped_unresolved": grounding.dropped_observations,
        "evidence_emitted": grounding.resolved_evidence,
        "evidence_unresolved": len(grounding.unresolved),
        "proposals_malformed": parsed.malformed_count,
        "cost_usd": round(cost_meter.spent_usd, 8),
        # Beside `cost_usd` on every path, not only the overrun one. The figure above is
        # a provider-reported number or a figure computed from the lock's per-token
        # pins, and a consumer cannot tell which from the number. The overrun branch
        # carried this and the success branch did not, so `metrics["cost_basis"]`
        # answered on the one run that failed its budget and raised `KeyError` on the
        # run that succeeded - backwards from useful. The response is the only thing
        # that knows, and it is in scope here as it is there. Same expression, same
        # values, and the schema admits a string under `metrics`.
        "cost_basis": (
            "measured" if response.reported_cost_usd is not None else "estimated"
        ),
        "cost_ceiling_usd": cost_meter.ceiling_usd,
        "latency_ms": response.latency_ms,
    }

    if response.truncated and not grounding.observations:
        return TextAnalysisOutcome(
            status=STATUS_FAILED,
            artifact=None,
            model_calls=(call,),
            error=DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message="the provider reply was cut short and yielded no usable observation",
                stage_id=STAGE_ID,
            ),
            metrics=metrics,
        )

    try:
        assert_consistent_mode(mode, (call,))
        artifact = build_text_observations(
            run_id=run_id,
            profile=profile,
            provider_mode=mode,
            text_layer=text_layer,
            pages_analysed=analysed,
            observations=grounding.observations,
        )
    except DomainError as error:
        return TextAnalysisOutcome(
            status=STATUS_FAILED,
            artifact=None,
            model_calls=(call,),
            error=error,
            metrics=metrics,
        )

    if response.truncated:
        return TextAnalysisOutcome(
            status=STATUS_PARTIAL,
            artifact=artifact,
            model_calls=(call,),
            error=_partial_error(run_id),
            metrics=metrics,
        )
    return TextAnalysisOutcome(
        status=STATUS_SUCCEEDED,
        artifact=artifact,
        model_calls=(call,),
        error=None,
        metrics=metrics,
    )


def _record(
    model_call_id: ModelCallId,
    request: Any,
    response: Any,
    *,
    mode: ProviderMode,
    status: str,
    cost_usd: float,
    cost_basis: str,
) -> ModelCallRecord:
    """`cost_basis` has no default, and that is `D-3`.

    It used to default to ``"estimated"``. `W11-FIX` flagged the shape and declined to
    change behaviour with no defect behind it, which was right at the time: there was one
    call site and it passed the value. There are two now, and the second -- the
    cost-overrun path -- took the default. The value it recorded was *true*, because the
    overrun figure is computed from the pin's own rates; but it was true by coincidence of
    the default rather than because the call site established it, on the one path an
    operator reads when a budget broke.

    A provenance field is a claim about how a number was arrived at. The call site is the
    only place that knows, so it is the only place allowed to say, and a third call site
    cannot now be silent by accident.
    """
    return ModelCallRecord(
        model_call_id=model_call_id,
        provider=PROVIDER,
        model_id=request.model_id,
        provider_mode=mode,
        parameters=request.parameters,
        request_sha256=request.request_sha256,
        response_sha256=response.response_sha256,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        status=status,
        cost_usd=cost_usd,
        cost_basis=cost_basis,
    )


def _check_graph_version(document: Mapping[str, Any] | None) -> None:
    """Fail closed on an unexpected ``context.document_graph`` version."""
    if document is None:
        return
    if document.get("artifact_role") != "context.document_graph":
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the supplied document context is not a document graph artifact",
            stage_id=STAGE_ID,
            reason="artifact_role_unexpected",
        )
    if document.get("artifact_version") != "1.0.0":
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the document graph declares a version this stage was not written against",
            stage_id=STAGE_ID,
            reason="artifact_version_unsupported",
        )
