"""Bounded multimodal preliminary review under an ordinary Run's durable authority."""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
import logging
import math
import re
import time
from copy import deepcopy
from typing import Any

from auditmanager.analysis.public import (ModelCallRecord, ModelRequest, ModelResponse, ProviderMode, accepted_reported,
    build_extended_request, extended_canonical, extended_digest, finalize_extended_items,
    parse_extended_reply, plan_extended_inputs, EXTENDED_REVIEW_ROLE, EXTENDED_REPLY_ROLE,
    pinned_models, request_cost_upper_usd, require_approved_model, extended_block_payload,
    block_leg_refs, build_block_judge_request, parse_block_judge_reply, reconcile_block_batch,
    ORIGINAL_REVIEW_V2, original_review_critic, original_review_corrector, original_review_plan,
    original_review_procedures, original_review_summary)
from auditmanager.documents.public import DocumentRepository
from auditmanager.executors.public import CropImage, HostRepository, attach_images, cell_binding_of, token_health_of
from auditmanager.findings.public import BlockEvidenceItem, CandidateGroup, CandidateMember
from auditmanager.jobs.public import extended_unit
from auditmanager.norms.public import (
    MAX_NORM_QUERY_CHARACTERS, SEARCH_WINDOW, SEMANTIC_LOOKUP, NormPageImages, SemanticUnavailable, norm_embed_url,
    norm_observation_text, parse_norm_query, search_norms, semantic_norm_candidates,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.stage_plan import call_journal_columns, cell_binding, settings_of
from auditmanager.runs.stage_layout import ENSEMBLE_ROLES, parse_plan, role_of_phase, row_of_phase
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId
from auditmanager.storage.public import parse_blob_id
from sqlalchemy.exc import SQLAlchemyError

_log = logging.getLogger(__name__)


FORMAT = "extended-review-v1"


def _refuse(reason: str):
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason=reason)


def _original_review_enabled(policy, *, strict=False) -> bool:
    """`V2-ORIGINAL-REVIEW-01`: whether the frozen plan-v2 policy carries the marker of the original's deterministic critic and corrector.

    A v2 consent without it runs exactly as it ran before. ``strict`` refuses a marker this code does not know, as a failed review.
    """
    if not isinstance(policy, dict) or policy.get("plan_version") != "extended-review-v2" or "original_review" not in policy:
        return False
    if policy["original_review"] != ORIGINAL_REVIEW_V2:
        if strict:
            raise _refuse("original_review_policy_invalid")
        return False
    return True


#: `F8-PUBLISH` (plan-v5 section 2.4): the reference kinds a critic saw, stored on every candidate it reviewed (``context_kinds``), so that a
#: veto is never an echo of the same neighbours. Today the AI critic of plan v3 sees the paragraph text of the norms its candidate carried
#: (``norm_text``). The deterministic critic of plan v2 sees no reference at all and stores no key: its row says ``mode: deterministic`` and
#: ``model_called: false``, and a reader takes a reviewed candidate without ``context_kinds`` as one that saw none (writing ``[]`` there changed
#: the saved shape that ``tests/unit/analysis_extended/test_original_review_runtime.py`` compares). ``norm_images`` and ``precedents`` are
#: added by the lanes that hand them to the critic; the literals are those of ``precedents.models`` (``CONTEXT_NORM_TEXT``).
CONTEXT_NORM_TEXT = "norm_text"


#: `M7-NORM-PNG`: the page image of a norm paragraph the candidate carried was in the critic's task (``precedents.models.CONTEXT_NORM_IMAGES``).
CONTEXT_NORM_IMAGES = "norm_images"


def _critic_context_kinds(item, payload, imaged=frozenset()) -> list:
    """What the critic's request carried for this candidate: ``norm_text`` when a paragraph of the candidate's own norm candidates is in
    ``norm_context``, and ``norm_images`` when the page of one of them was declared in the task (``imaged``: the paragraph ids of the pages)."""
    supplied = {row.get("paragraph_id") for row in payload.get("norm_context", []) if isinstance(row, dict)}
    wanted = {row.get("paragraph_id") for row in item.get("norm_candidates", []) if isinstance(row, dict)}
    return ([CONTEXT_NORM_TEXT] if supplied & wanted else []) + ([CONTEXT_NORM_IMAGES] if imaged & wanted else [])


#: The cell of the critic's call, as ``binding_for(cell)`` and the stand name it (``f"{row}:{role}"``).
_CRITIC_CELL = "review:main"
#: The providers of a host agent whose command takes no image (``tools/executor-runner/host_mode.py``: ``image_input_unsupported``).
_PROVIDERS_WITHOUT_IMAGES = frozenset({"claude_code"})


class _CriticNormImages:
    """`M7-NORM-PNG` (plan-v5 section 3.4, ``ADR-0029`` decision 9): the page images of norm paragraphs that a critic task of this run declares.

    One per run (and per global review), made only for a run the critic's reference section is offered to (:func:`_reference_section`): a legacy
    run, a v2 run and a planned run without the «контекст критику» switch get ``None`` and are never asked. :meth:`attach` is called with the
    critic's request **when it is built**, so the task is created with its ``images``; it declares the pages (``crop_id: norm.<nbd_...>``) of
    the paragraphs of this request's own ``norm_context`` -- at most two, none unless the ``review:main`` member of the run serves images and is
    not a Claude Code host. What happened is written to ``state["norm_page_images"]`` (the pages declared, the paragraphs whose page could not be
    produced with the reason, or why none were offered): a page that is missing costs the image, never the text or the call. The render itself is
    made lazily by :class:`~auditmanager.norms.public.NormPageImages` and kept in ``norm_crop_render``, so the next task reuses it.
    """

    def __init__(self, session, run, store, *, pages=None):
        self._session, self._run, self._store = session, run, store
        self._pages = pages
        self._withheld: str | None | bool = False  # False: not asked yet

    def _factory(self):
        from sqlalchemy.orm import sessionmaker
        return sessionmaker(bind=self._session.get_bind())

    def _service(self):
        if self._pages is None:
            self._pages = NormPageImages(store=self._store, session_factory=self._factory())
        return self._pages

    def withheld(self):
        """Why the member does not take images (a fixed word), or ``None`` when it does. Asked once; the answer is read from the database, with a
        short transaction of its own, never from the run's."""
        if self._withheld is False:
            from auditmanager.shared.db import session_scope
            with session_scope(self._factory()) as session:
                member = cell_binding_of(session, self._run.run_id, _CRITIC_CELL)
                if member is None:
                    self._withheld = "member_not_bound"
                elif member.provider in _PROVIDERS_WITHOUT_IMAGES:
                    self._withheld = "provider_takes_no_images"
                else:
                    health = token_health_of(session, HostRepository().usable_tokens(session, member.host_id))
                    self._withheld = (None if any("images" in row.features for row in health.values())
                        else "member_declared_no_images")
        return self._withheld

    def attach(self, request, *, state, identity):
        """``(request, imaged)``: the request with the pages declared, and the ids of the paragraphs that sit on them. The request comes back as it
        was when there is no norm paragraph in it, no page to show or the member takes no image."""
        payload = json.loads(request.body["messages"][0]["content"])
        paragraphs = payload.get("norm_context")
        if not isinstance(paragraphs, list) or not paragraphs:
            return request, frozenset()
        receipts = state.setdefault("norm_page_images", [])
        reason = self.withheld()
        if reason is not None:
            receipts.append({"identity": identity, "status": "not_offered", "reason": reason})
            return request, frozenset()
        selection = self._service().select(paragraphs)
        receipts.append({"identity": identity, "status": "declared" if selection.images else "none",
            "images": [{"crop_id": image.crop_id, "paragraph_ids": list(image.paragraph_ids), "sha256": image.render.sha256,
                "size_bytes": image.render.size_bytes} for image in selection.images],
            "unavailable": [{"paragraph_id": paragraph, "reason": why} for paragraph, why in selection.unavailable]})
        if not selection.images:
            return request, frozenset()
        return attach_images(request, [CropImage(image.crop_id, image.data) for image in selection.images]), selection.paragraph_ids


def _critic_norm_images(session, run, store, binding, policy):
    """The helper above for a run whose critic task may carry the reference section, else ``None`` (that run's critic is built as it always was)."""
    return _CriticNormImages(session, run, store) if _reference_section(binding, policy) else None


def _review_original_v2(*, state, phase, pages, substantive=None) -> None:
    """The two procedures after the norm verification, over the saved observations. No model, no executor, no call.

    A defect here is a visible failed procedure (and a warning); it does not discard the results the paid calls above have saved.
    """
    phase("finding_review", "running")
    try:
        done = original_review_critic(state["observations"], state["sources"], pages)
    except (ValueError, TypeError, KeyError, AttributeError):
        state["warnings"].append("original_review_failed")
        phase("finding_review", "failed", "original_review_failed")
        phase("finding_correction", "skipped", "dependency_failed")
        return
    gap = substantive() if substantive is not None else False
    phase("finding_review", "partial" if gap else "completed",
        "substantive_review_reply_refused" if gap else None if done else "no_observations")
    phase("finding_correction", "running")
    try:
        if "flow_repair_policy" in state and substantive is not None:
            from auditmanager.analysis.public import flow_repair_helper
            corrections = flow_repair_helper("current_corrections", state["observations"])
        else:
            corrections = original_review_corrector(done)
    except (ValueError, TypeError, KeyError, AttributeError):
        for item, _, _ in done:
            item.pop("correction", None)
        state["warnings"].append("original_review_failed")
        phase("finding_correction", "failed", "original_review_failed")
        return
    state["original_review"] = {**state.get("original_review", original_review_plan()), **original_review_summary(done, corrections)}
    if substantive is not None:
        summary = state["original_review"]
        summary["structural_verdicts"] = dict(summary["verdicts"])
        summary.update(mode="substantive", model_called=state["substantive_review"]["model_called"],
            checks=["evidence", "alternatives", "materiality"], checks_not_built=[])
        summary["verdicts"] = dict(Counter(item["critic"]["original_verdict"] for item in state["observations"]))
    phase("finding_correction", "completed", None if corrections else "no_corrections_requested")


def _cell(binding, row, role="main"):
    """`binding_for(cell)` (ADR-0028 decision 6): the binding of the ``row`` cell -- the adapter of the member it was bound to, the cell's
    model and settings, the call binding that holds the reply to the cell's model. A run that is not frozen with a stage plan has one
    binding for every call, and this returns it. ``role`` is ``main`` except for a leg or the judge of the blocks ensemble."""
    return cell_binding(binding, f"{row}:{role}")


def _kw(binding, row, role="main"):
    """The keywords every request builder of the ``row`` cell takes: its model and its settings (``None`` outside a planned run, so the
    builder keeps the constants it always had)."""
    cell = _cell(binding, row, role)
    return {"model_id": cell.config.model_id, "settings": settings_of(cell)}


def _reference_section(binding, policy):
    """Whether the critic's task of this run may carry the reference section after its JSON (`CTX-CRITIC`, ``ADR-0029`` decision 3).

    Exactly the runs the stand serves: a run on the stage layout (its binding has cells, as `_phase_binding` reads it) whose frozen consent
    holds the ``executor_context_policy`` (``runs.preflight`` writes it only under plan v3 with the «контекст критику» switch on). The
    consent is the source, not the code now in force: a prompt must not change between an attempt and its resume, and the paragraph it
    gets says «if the section stands after the JSON», so a stand that serves nothing leaves it harmless. A legacy run, a v2 run and a
    planned run without the switch keep the prompt they always had."""
    return getattr(binding, "cells", None) is not None and isinstance(policy.get("executor_context_policy"), dict)


def _phase_binding(binding, identity):
    """The binding a call of ``identity`` runs with: the run's own for a run without a stage plan, else the cell of the row the phase
    belongs to. A semantic repair (``:repair:1``) is the phase it repairs, so it runs on that phase's cell. A phase that has no row has no
    model, and a planned run does not call one."""
    if getattr(binding, "cells", None) is None:
        return binding
    row = row_of_phase(identity)
    if row is None:
        raise _refuse("extended_phase_has_no_cell")
    return _cell(binding, row, role_of_phase(identity))


def _response_payload(response: ModelResponse) -> dict:
    value = asdict(response)
    if (not isinstance(response.output_text, str)
            or any(type(getattr(response, k)) is not int or getattr(response, k) < 0
                   for k in ("input_tokens", "output_tokens", "latency_ms"))
            or response.reported_cost_usd is not None and (isinstance(response.reported_cost_usd, bool)
                or not isinstance(response.reported_cost_usd, (int, float))
                or not math.isfinite(response.reported_cost_usd) or response.reported_cost_usd < 0)):
        raise _refuse("extended_response_invalid")
    return value


def _saved_response(store, row: dict, request: ModelRequest, binding, *, dispatched_sha256=None) -> ModelResponse:
    p = row["parameters"]
    expected_sha256 = request.request_sha256 if dispatched_sha256 is None else dispatched_sha256
    try:
        raw = store.read(parse_blob_id(p["extended_reply_blob_id"]), verify=True)
        if (len(raw) != p["extended_reply_size"] or hashlib.sha256(raw).hexdigest() != p["extended_reply_sha256"]
                or row["request_sha256"] != expected_sha256
                or row["model_identity"] != request.model_id
                or row["provider_mode"] != binding.adapter.provider_mode.value):
            raise ValueError()
        doc = json.loads(raw)
        response = ModelResponse(**doc["response"])
        _response_payload(response)
        if response.response_sha256 != row["response_sha256"] or doc["request_sha256"] != expected_sha256:
            raise ValueError()
        return response
    except (KeyError, TypeError, ValueError):
        raise _refuse("extended_saved_reply_invalid") from None


def _call(session, *, run_id, authority, jobs, journal, binding, request, phase, source_sha256,
          meter, store, publish, checkpoint, global_unknown_fence=False, dispatch_receipt=None):
    checkpoint("extended_before_call")
    if getattr(binding, "cells", None) is not None:
        # `HOSTS-LAYOUT-01` (`R-133`): a planned run's calls go through the binding of their cell (``runs.stage_plan.cell_binding``). The
        # run-level binding is the text cell's, and a block or a norm call made on it would run on the wrong model: refused, not skipped.
        raise _refuse("extended_call_without_cell")
    planned = binding.call is not None and getattr(binding.call, "cell_key", None) is not None
    flow_context = ":v2-flow-repair-v1:critic:" in (request.idempotency_scope or "")
    base_request_sha256 = request.request_sha256
    if flow_context:
        from auditmanager.jobs.public import extended_context_unit
        previous = extended_context_unit(session, run_id=run_id, phase=phase,
            source_sha256=source_sha256, base_request_sha256=base_request_sha256)
        session.commit()
        if previous is not None:
            if dispatch_receipt is not None:
                dispatch_receipt.update(request_sha256=previous["request_sha256"], replayed=True,
                    human_reference_receipt=previous["parameters"].get("human_reference_receipt", {}))
            return _saved_response(store, previous, request, binding,
                                   dispatched_sha256=previous["request_sha256"]), True
        from auditmanager.precedents.public import candidate_context_request
        # Current status locks live through provider-effect registration, then are
        # released before network I/O. No runner-side late context is appended.
        request = candidate_context_request(session, run_id=run_id, request=request)
    if dispatch_receipt is not None:
        dispatch_receipt.update(request_sha256=request.request_sha256, replayed=False)
    # The key of a saved reply. A planned call is identified by (source, phase, request, model) alone: neither the host nor the connection
    # revision is in it, so a retry served by another host after a move finds the reply already paid for. Every other call keeps the key
    # it has always had, so the replies of runs started before the layout are still found.
    key = extended_digest({"format": FORMAT, "source": source_sha256, "phase": phase,
        "request": request.request_sha256, "model": request.model_id,
        **({} if planned else {"connection": None if binding.call is None else binding.call.connection_revision_id})})
    saved = extended_unit(session, run_id=run_id, unit_key=key, source_sha256=source_sha256, phase=phase,
                          **({"replay_received_only": True} if flow_context else {}))
    if not flow_context or saved is not None:
        session.commit()  # no read/authority lock survives external Blob I/O
    if saved is not None:
        return _saved_response(store, saved, request, binding), True
    if global_unknown_fence:
        from auditmanager.jobs.public import has_ambiguous_provider_effect
        if has_ambiguous_provider_effect(session,run_id=run_id):
            session.commit()
            raise _refuse("extended_provider_outcome_unknown")
        if not flow_context:
            session.commit()
    pin = next((p for p in pinned_models() if p.model_id == request.model_id), None)
    if pin is None:
        raise _refuse("extended_model_price_unavailable")
    require_approved_model(binding.config, pin, binding.call)
    meter.check_before_call(pending_cost_usd=request_cost_upper_usd(pin, request))
    params = {**request.parameters, "extended_unit_key": key, "extended_source_sha256": source_sha256,
              "extended_phase": phase}
    if flow_context:
        params["flow_base_request_sha256"] = base_request_sha256
        from auditmanager.precedents.public import candidate_context_receipt
        params["human_reference_receipt"] = candidate_context_receipt(request)
        if dispatch_receipt is not None:
            dispatch_receipt["human_reference_receipt"] = params["human_reference_receipt"]
    from auditmanager.analysis.public import semantic_repair_metadata
    params.update(semantic_repair_metadata(request))
    # Re-use the standard journal callbacks, preserving the extra immutable unit
    # parameters both at intent and completion, without pretending this is a text window.
    provider = "anthropic" if binding.call is None else binding.call.provider_label
    jobs.require_current(session, authority)
    call_id = jobs.prepare_provider_call(session, authority, provider=provider,
        model_identity=request.model_id, provider_mode=binding.adapter.provider_mode.value,
        parameters=params, request_sha256=request.request_sha256,
        connection_revision_id=None if binding.call is None else binding.call.connection_revision_id,
        identity_basis=None if binding.call is None else binding.call.identity_basis,
        **call_journal_columns(binding.call))
    if global_unknown_fence:
        bind_current=getattr(journal,"bind_current_call",None)
        if callable(bind_current):bind_current(call_id)
    session.commit()
    checkpoint("extended_intent_committed")
    try:
        response = binding.adapter.complete(request)
    except Exception as error:
        dispatch = getattr(error, "dispatch_class", None)
        code = error if isinstance(error, DomainError) else _refuse("extended_provider_failed")
        if dispatch is not None and getattr(code, "dispatch_class", None) is None:
            code.dispatch_class = dispatch  # the retry policy of a leg reads what the transport proved, not the wrapper's code
        if binding.adapter.provider_mode is ProviderMode.RECORDED or dispatch in {"not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"}:
            journal.not_processed(call_id, code, "not_sent" if dispatch is None else dispatch)
        else:
            journal.outcome_unknown(call_id, code)
        raise code
    if not isinstance(response, ModelResponse):
        journal.outcome_unknown(call_id, _refuse("extended_response_invalid"))
        raise _refuse("extended_response_invalid")
    journal.response_received(call_id, response)
    response_payload = _response_payload(response)
    ref = publish(EXTENDED_REPLY_ROLE, {"format": FORMAT, "kind": "reply",
        "source_sha256": source_sha256, "unit_key": key,
        "request_sha256": request.request_sha256, "response": response_payload})
    params.update(extended_reply_blob_id=ref.blob_id, extended_reply_sha256=ref.sha256,
                  extended_reply_size=ref.size_bytes)
    unmetered = binding.call is not None and binding.call.unmetered
    cost = 0.0 if unmetered else (response.reported_cost_usd if response.reported_cost_usd is not None
        else pin.cost_usd(input_tokens=response.input_tokens, output_tokens=response.output_tokens))
    budget_error = None
    try:
        if unmetered:
            meter.record_unmetered()
        else:
            meter.charge(pin, input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                reported_cost_usd=response.reported_cost_usd)
    except DomainError as error:
        budget_error = error
    journal.complete(ModelCallRecord(model_call_id=ModelCallId.parse(str(call_id)), provider=provider,
        model_id=request.model_id, provider_mode=binding.adapter.provider_mode, parameters=params,
        request_sha256=request.request_sha256, response_sha256=response.response_sha256,
        input_tokens=response.input_tokens, output_tokens=response.output_tokens, latency_ms=response.latency_ms,
        status="truncated" if response.truncated else "succeeded", cost_usd=float(cost),
        cost_basis="unmetered" if unmetered else "measured" if response.reported_cost_usd is not None else "estimated"))
    if budget_error is not None:
        raise budget_error
    if (binding.call is not None and binding.call.check_identity
            and not accepted_reported(binding.call.expected_model, response.model)):
        raise _refuse("extended_model_identity_mismatch")
    return response, False


# --- the blocks ensemble (`HOSTS-ENSEMBLE-01`, ADR-0028 decision 11) --------------------------------------------------------------
#
# A block batch of a run whose plan holds the legs and the judge of the blocks row is read by each leg alone (the ordinary block request,
# on the leg's cell), then by the judge, which sees the batch again with the legs' observations. Calls are sequential. Each of them is its
# own unit: its own identity (``blocks:N:leg1``, ``blocks:N:leg2``, ``blocks:N:judge``), its own idempotency key, its own journal row and
# its own cell binding. A run without the legs and the judge in its plan (the legacy route, or a single model on the blocks row) calls one
# model per batch, exactly as before.

#: A leg that failed is asked again this many times, this many seconds apart (the original's ``STAGE01_LEG_RETRY_ATTEMPTS`` and
#: ``STAGE01_LEG_RETRY_DELAY_S``). The stage is never aborted because one leg failed (``STAGE01_ABORT_ON_LEG_FAILURE_ENABLED`` is off).
LEG_RETRY_ATTEMPTS = 5
LEG_RETRY_DELAY_SECONDS = 30
#: What a transport proved about a failed call: the only classes a leg is asked again on. ``outcome_unknown`` is never one of them: the
#: provider may have processed the call, the v3 ambiguity fence (`has_ambiguous_provider_effect`) holds, and asking again would pay twice.
LEG_RETRY_CLASSES = frozenset({"not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"})
#: The wait is taken in slices so that a cancelled run is noticed (the checkpoint re-reads the attempt and the run) within seconds.
_RETRY_WAIT_SLICE_SECONDS = 5
_sleep = time.sleep
#: The per-run leg breaker (D-662, approved by the owner 2026-11-10; the original has none). A leg that ended **failed after its retries**
#: in this many consecutive batches while the other leg answered is no longer asked for the rest of the run: the next batches go straight to
#: the surviving leg and the judge only searches for gaps, as it does when a leg fails. Without it a persistently failing model costs
#: ``LEG_RETRY_ATTEMPTS`` x ``LEG_RETRY_DELAY_SECONDS`` = 150 s on every batch and can push the attempt towards its 7200 s cap.
LEG_BREAKER_CONSECUTIVE_BATCHES = 3
_BREAKER_FORMAT = "block-leg-breaker/1"
_BREAKER_LEGS = ("leg1", "leg2")


def _new_breaker() -> dict:
    return {"format": _BREAKER_FORMAT, "legs": {}}


def _restore_breaker(saved) -> tuple[dict, bool]:
    """The breaker of a resumed attempt: ``(breaker, valid)``. ``saved`` is ``None`` when nothing was saved (valid, empty). A saved breaker of
    another shape, or one that has silenced both legs, is **not** trusted: the caller gets an empty breaker and ``valid`` false, and says so
    (a damaged breaker must cost a leg its retries again, never silence a leg on a guess)."""
    if saved is None:
        return _new_breaker(), True
    try:
        if saved["format"] != _BREAKER_FORMAT or set(saved) != {"format", "legs"} or not isinstance(saved["legs"], dict):
            raise ValueError()
        legs = {}
        for role, entry in saved["legs"].items():
            if (role not in _BREAKER_LEGS or set(entry) != {"model_id", "streak", "open"} or not isinstance(entry["model_id"], str)
                    or not isinstance(entry["streak"], list)
                    or any(not isinstance(p, list) or len(p) != 2 or any(type(n) is not int for n in p) for p in entry["streak"])):
                raise ValueError()
            opened = entry["open"]
            if opened is not None:
                if (set(opened) != {"model_id", "consecutive", "from", "at", "batch"} or type(opened["consecutive"]) is not int
                        or opened["model_id"] != entry["model_id"] or not isinstance(opened["batch"], str)
                        or any(not isinstance(opened[k], list) or len(opened[k]) != 2 or any(type(n) is not int for n in opened[k])
                               for k in ("from", "at"))):
                    raise ValueError()
            legs[role] = {"model_id": entry["model_id"], "streak": deepcopy(entry["streak"]), "open": deepcopy(opened)}
        if sum(entry["open"] is not None for entry in legs.values()) > 1:
            raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        return _new_breaker(), False
    return {"format": _BREAKER_FORMAT, "legs": legs}, True


def _breaker_skips(breaker, role, model_id, position) -> bool:
    """Whether the batch at ``position`` (``[window offset, batch index]``) does not ask ``role``. Only the batches from the first failure
    of the streak that opened the breaker on: an earlier batch of a re-run window keeps the reply the leg already gave it."""
    entry = breaker["legs"].get(role)
    return (entry is not None and entry["open"] is not None and entry["model_id"] == model_id
            and position >= entry["open"]["from"])


def _observe_breaker(breaker, *, position, batch, cells, answered, failed):
    """Fold the end of a batch's legs into the breaker; the opening event (``leg``, ``model_id``, ``consecutive``...) or ``None``.

    Evidence is a batch in which a leg **failed after its retries while another leg answered**. A batch in which no leg answered propagates
    and counts for none (it is today's failure, and the breaker would silence a leg on the word of a run with no survivor); a leg that
    answered, even with a reply refused after repair, ends its streak. A leg already open is not touched. Opening needs an answering leg,
    and an open leg never answers: the breaker cannot silence both. A batch is counted once however often a resumed attempt re-runs it."""
    for role in answered:
        entry = breaker["legs"].get(role)
        if entry is not None and entry["open"] is None:
            entry["streak"] = []
    event = None
    for role in failed:
        entry = breaker["legs"].setdefault(role, {"model_id": cells[role], "streak": [], "open": None})
        if entry["model_id"] != cells[role]:
            entry.update(model_id=cells[role], streak=[], open=None)
        if entry["open"] is not None:
            continue
        if position not in entry["streak"]:
            entry["streak"].append(list(position))
        if len(entry["streak"]) >= LEG_BREAKER_CONSECUTIVE_BATCHES:
            entry["open"] = {"model_id": cells[role], "consecutive": len(entry["streak"]), "from": list(entry["streak"][0]),
                             "at": list(position), "batch": batch}
            event = {"leg": role, **deepcopy(entry["open"])}
    return event


def _block_roles(run):
    """The roles of the blocks cells of a run: ``("main",)`` for a run without a plan or with one model on the blocks row, else the
    ensemble's ``("leg1", "judge")`` or ``("leg1", "leg2", "judge")`` from the plan the run froze at its start."""
    document = getattr(run, "stage_plan", None)
    if document is None:
        return ("main",)
    roles = parse_plan(document).roles_of_row("blocks")
    if roles == ("main",):
        return roles
    if not roles or roles[-1] != "judge" or any(role not in ENSEMBLE_ROLES for role in roles) or len(set(roles)) != len(roles) \
            or roles[0] != "leg1":
        raise _refuse("block_ensemble_cells_invalid")
    return roles


def _wait_before_retry(checkpoint):
    remaining = LEG_RETRY_DELAY_SECONDS
    while remaining > 0:
        checkpoint("extended_leg_retry_wait")
        step = min(_RETRY_WAIT_SLICE_SECONDS, remaining)
        _sleep(step)
        remaining -= step


def _leg_call(call, request, identity, *, checkpoint):
    """One leg call, asked again after a failure the transport proved harmless: ``(response, retries)``.

    Any other failure -- an ambiguous outcome, an exhausted budget, a refused identity, a limit of the approval -- propagates at once. After
    the last allowed retry the failure propagates too, carrying ``leg_attempts``; the caller decides what a failed leg means."""
    retries = 0
    while True:
        try:
            return call(request, identity), retries
        except DomainError as error:
            if getattr(error, "dispatch_class", None) not in LEG_RETRY_CLASSES or retries >= LEG_RETRY_ATTEMPTS:
                error.leg_attempts = retries
                raise
            retries += 1
            _wait_before_retry(checkpoint)


def _cell_receipt(state, index, role):
    """The sub-receipt of one call of an ensemble batch inside the batch's receipt (``None`` when the run keeps no batch receipts)."""
    row = next((row for row in state.get("batches", []) if row.get("procedure") == "block_analysis" and row.get("index") == index), None)
    return None if row is None else row.setdefault("cells", {}).setdefault(role, {})


def _ensemble_block_batch(*, run, binding, state, call, roles, section, index, batch, payload, crops, builder, extra, window_context,
                          policy, checkpoint, breaker):
    """One block batch of the ensemble: ``(observations, partial_reason)``.

    * each leg asks the ordinary block request on its own cell, retried as :data:`LEG_RETRY_CLASSES` allow; a leg whose retries are spent
      is **failed** and the batch is partial, a leg whose reply is refused after repair keeps the records it did get and the batch is
      partial too. If every leg failed the batch fails: the last error propagates, as a failed block call does today;
    * the judge then reads the batch with the observations of the legs that answered (and the names of those that did not). It is asked
      once. If it fails on a harmless class, or its reply holds nothing valid, the batch is partial and the legs' observations stand
      unreviewed; any other failure propagates;
    * the observations are the legs' as they wrote them (annotated with how the judge related them) and the judge's gap observations;
    * a leg the run's ``breaker`` has opened (:data:`LEG_BREAKER_CONSECUTIVE_BATCHES`, D-662) is not asked: it makes no call, the batch is
      partial with ``block_ensemble_leg_skipped`` and the judge is told the leg did not answer, as for a failed one. The breaker never
      opens for ``outcome_unknown`` (that propagates before it is consulted), never on a batch no leg answered, and never silences every
      leg.
    """
    allowed = {s["source_id"] for s in batch}
    identity = f"blocks:{index}"
    v3 = window_context is not None
    cells = {role: _cell(binding, "blocks", role).config.model_id for role in roles}
    legs = tuple(role for role in roles if role != "judge")
    position = [window_context["offset"] if v3 else 0, index]
    silent = {role for role in legs if _breaker_skips(breaker, role, cells[role], position)}
    if len(silent) == len(legs):
        silent = set()  # the breaker never silences every leg: with no leg asked there would be no batch at all
    leg_items, failed, skipped, last_error, refused_any = {}, [], [], None, False
    for role in legs:
        if role in silent:
            skipped.append(role)
            continue
        request = attach_images(builder(**_kw(binding, "blocks", role), run_id=run.run_id, phase="blocks", section=section,
                                        payload=payload, **extra), crops)
        # A leg's request differs from its neighbour's by the model alone; the scope the transport may deduplicate on says the leg.
        request = replace(request, idempotency_scope=f"{request.idempotency_scope}:{role}")
        try:
            response, retries = _leg_call(call, request, f"{identity}:{role}", checkpoint=checkpoint)
        except DomainError as error:
            if getattr(error, "dispatch_class", None) not in LEG_RETRY_CLASSES:
                raise
            failed.append(role)
            last_error = error
            cell = _cell_receipt(state, index, role)
            if cell is not None:
                cell.update(status="failed", attempts=1 + getattr(error, "leg_attempts", 0), error_code=error.code.value,
                            dispatch_class=error.dispatch_class)
            continue
        parsed, refused = _received_reply(state=state, request=request, response=response,
            parse=lambda text, **kwargs: parse_extended_reply(text, allowed_sources=allowed, **kwargs),
            call=call, identity=f"{identity}:{role}", policy=policy)
        leg_items[role] = parsed
        refused_any |= refused
        cell = _cell_receipt(state, index, role)
        if cell is not None:
            cell.update(status="partial" if refused else "completed", attempts=1 + retries, observations=len(parsed))
    for role in skipped:  # written after the legs: the batch's receipt is made by its first call
        cell = _cell_receipt(state, index, role)
        if cell is not None:
            for stale in ("error_code", "dispatch_class", "request_sha256", "response_received", "response_sha256", "observations"):
                cell.pop(stale, None)
            cell.update(cell=f"blocks:{role}", status="skipped", attempts=0, reason="block_ensemble_leg_breaker_open")
    if not leg_items:
        raise last_error
    opened = _observe_breaker(breaker, position=position, batch=f"{window_context['window_id'] if v3 else 'v2'}:{identity}", cells=cells,
                              answered=list(leg_items), failed=failed)
    refs = block_leg_refs(leg_items)
    judge_records, judge_failed = None, False
    judge_request = attach_images(build_block_judge_request(
        **_kw(binding, "blocks", "judge"), run_id=run.run_id, section=section, payload=payload, legs=leg_items, failed_legs=[*failed, *skipped],
        window_id=window_context["window_id"] if v3 else None,
        relaxed_limits=v3 and _bounds_lifted(window_context["policy"])), crops)
    judge_identity = f"{identity}:judge"
    try:
        judge_response = call(judge_request, judge_identity)
    except DomainError as error:
        if getattr(error, "dispatch_class", None) not in LEG_RETRY_CLASSES:
            raise
        judge_failed = True
        cell = _cell_receipt(state, index, "judge")
        if cell is not None:
            cell.update(status="failed", attempts=1, error_code=error.code.value, dispatch_class=error.dispatch_class)
    else:
        records, refused = _received_reply(state=state, request=judge_request, response=judge_response,
            parse=lambda text, **kwargs: parse_block_judge_reply(text, allowed_sources=allowed, refs=refs, **kwargs),
            call=call, identity=judge_identity, policy=policy)
        refused_any |= refused
        judge_failed = refused and not records  # nothing of the reply was valid: the judge did not answer
        judge_records = None if judge_failed else records
        cell = _cell_receipt(state, index, "judge")
        if cell is not None:
            cell.update(status="failed" if judge_failed else "partial" if refused else "completed", attempts=1)
    items, report = reconcile_block_batch(batch=identity, legs=leg_items, cells=cells, judge=judge_records, sources=batch)
    report.update(failed_legs=failed, judge_failed=judge_failed)
    if skipped:
        report["skipped_legs"] = skipped
    if opened is not None:
        report["leg_breaker"] = opened  # journalled once: on the batch that opened it
    holder = next((row for row in state.get("batches", []) if row.get("procedure") == "block_analysis" and row.get("index") == index), None)
    if holder is not None:
        holder["reconciliation"] = report
    else:
        ensemble = state.setdefault("block_ensemble", {"format": report["format"], "cells": cells, "batches": []})
        ensemble["batches"].append(report)
        if breaker["legs"]:
            ensemble["breaker"] = deepcopy(breaker)  # a run without windows keeps it beside its batches
    reason = ("block_ensemble_leg_failed" if failed else "block_ensemble_leg_skipped" if skipped
              else "block_ensemble_judge_failed" if judge_failed
              else "block_analysis_reply_refused" if refused_any else None)
    return items, reason


#: `NORM-ANY-WORDS-01`. A model writes a norm query as a phrase ("СП 16.13330 расчет сварных соединений опорных узлов стальных балок"),
#: and the norms search wants every word of it in one paragraph, so a phrase finds nothing: on the prod run of 2026-11-11 all 19
#: distinct queries of the blocks found 0 paragraphs in a 674-document snapshot. When the query as written has no hit, the lookup asks
#: once more with the same designation and clause and its words joined by ``or``; ``ts_rank_cd`` puts the paragraphs that hold most of
#: them first. The candidates stay ``candidate_not_verified`` -- the norm review judges each one -- and the receipt names the query.
_ANY_WORD_TOKEN = re.compile(r"\w[\w.-]*", re.UNICODE)
_ANY_WORD_MIN_LENGTH = 3
_QUERY_OPERATORS = frozenset({"or", "and", "not"})


def _any_words_query(query: str) -> str | None:
    """The query with its designation and clause kept and its words joined by ``or``; ``None`` when it has fewer than two words."""
    parsed = parse_norm_query(query)
    words = [word for word in _ANY_WORD_TOKEN.findall(parsed.words or "")
             if len(word) >= _ANY_WORD_MIN_LENGTH and word.casefold() not in _QUERY_OPERATORS]
    if len(words) < 2:
        return None
    head = " ".join(part for part in (parsed.designation, None if parsed.clause is None else f"п. {parsed.clause}") if part)
    while len(words) >= 2:
        relaxed = (head + " " if head else "") + " or ".join(words)
        if len(relaxed) <= MAX_NORM_QUERY_CHARACTERS:
            return relaxed
        words.pop()
    return None


#: `NORM-COVERAGE-01`. The reasons the lookup gives an observation that asked no norm question: a primary text finding (whose stage
#: never names norms) or a cross-check point the model gave no query. Such an observation is not a gap of the norm verification.
_NO_NORM_QUESTION = frozenset({"query_not_proposed", "no_normative_question"})


def _asked_norm_question(item: dict) -> bool:
    """Whether the lookup searched (or had to search) a norm for the observation; ``False`` for one that asked no norm question."""
    return item.get("norm_status") != "not_applicable" and item.get("norm_reason") not in _NO_NORM_QUESTION


def _norms(session, observations: list[dict], snapshot_id: str | None,
           *, full_document: bool = False, checkpoint=None, lookup_receipts=None,
           query_planning=False, strict_scope=False) -> list[str]:
    # Candidate retrieval is deterministic corpus lookup, never edition validation.
    available = snapshot_id is not None
    cache: dict[str, list[dict]] = {}
    cache_receipts: dict[str, dict] = {}
    lookup_pass = 1 + max((row.get("lookup_pass_ordinal", 0) for row in (lookup_receipts or [])), default=0)
    calls = 0
    warnings = []
    for ordinal, item in enumerate(observations):
        query_plan = None
        if query_planning:
            from .norm_queries import plan_flow_norm_queries, plan_norm_queries
            query_plan = plan_flow_norm_queries(item) if strict_scope else plan_norm_queries(item)
            if strict_scope:
                literal = plan_norm_queries({**item, "norm_queries": []})
                if literal["reason"] == "literal_standard_reference":
                    bounds = literal["queries"]
                    claimed = parse_norm_query(item.get("title", "") + " " + item.get("description", ""))
                    clause = claimed.clause if len(bounds) == 1 else None
                    scoped = []
                    for proposed in query_plan["queries"] or bounds:
                        words = parse_norm_query(proposed).words or ""
                        for bound in bounds:
                            head = bound + (f" п. {clause}" if clause else "")
                            value = head + (" " + words if words else "")
                            if len(value) > MAX_NORM_QUERY_CHARACTERS:
                                value = head  # never cut a designation, edition or clause
                            if value not in scoped:
                                scoped.append(value)
                    query_plan.update(queries=scoped, original_proposed_queries=deepcopy(item.get("norm_queries", [])),
                        scope_policy="literal_document_and_clause", literal_scope=deepcopy(literal["provenance"]))
        queries = item.pop("norm_queries", []) if query_plan is None else query_plan["queries"]
        if query_plan is not None:
            item.pop("norm_queries", None)
            item["norm_query_plan"] = deepcopy(query_plan)
        receipt = None
        if lookup_receipts is not None:
            receipt = {"version": "norm-search-receipt-v1", "observation_id": item.get("observation_id"),
                "lookup_pass_ordinal": lookup_pass,
                "observation_ordinal": ordinal, "title": item.get("title"), "source_ids": deepcopy(item.get("source_ids", [])),
                "requested_snapshot_id": snapshot_id, "proposed_queries": deepcopy(queries), "queries": [],
                "status": "running", "search_page_limit": 3, "additional_search_performed": False,
                "search_result_window_limit": SEARCH_WINDOW, "exhaustive_search_claimed": False,
                "edition_applicability_verified": False, "document_absence_proved": False}
            lookup_receipts.append(receipt)
            if query_plan is not None:
                receipt["query_plan"] = deepcopy(query_plan)
        def finish_receipt():
            if receipt is None:
                return
            answered = [query for query in receipt["queries"] if query.get("status") == "completed"]
            receipt.update(status=item.get("norm_status"), reason=item.get("norm_reason"),
                selected_candidate_ids=[candidate["paragraph_id"] for candidate in item.get("norm_candidates", [])],
                selected_candidate_count=len(item.get("norm_candidates", [])),
                queries_answered=len(answered), queries_without_answer=max(0, len(queries) - len(answered)),
                search_calls_started=sum(query.get("search_started") is True for query in receipt["queries"]),
                reused_query_answers=sum(query.get("cache_reused") is True for query in answered),
                search_tail_not_read=any(query.get("has_more") is True for query in answered))
        if query_plan is not None and query_plan["status"] == "not_applicable":
            item.update(norm_status="not_applicable", norm_reason=query_plan["reason"],
                norm_candidates=[], norm_review_status="not_required")
            finish_receipt()
            continue
        if not available or not queries:
            item["norm_status"] = "unavailable"
            item["norm_reason"] = "corpus_unavailable" if not available else "normative_query_required" if query_plan else "query_not_proposed"
            finish_receipt()
            continue
        candidates = []
        active_query = None
        try:
            for query in queries:
                key = " ".join(query.casefold().split())
                if receipt is not None:
                    active_query = {"query": query, "normalized_query": key, "status": "not_searched",
                        "search_started": False, "cache_reused": key in cache}
                    receipt["queries"].append(active_query)
                if key not in cache:
                    if not full_document and calls >= 12:
                        item["norm_reason"] = "lookup_window_exhausted"
                        warnings.append("norm_lookup_window_exhausted")
                        if active_query is not None:
                            active_query["reason"] = "lookup_window_exhausted"
                        break
                    if checkpoint is not None:
                        checkpoint("extended_norm_lookup")
                    calls += 1
                    if active_query is not None:
                        active_query["search_started"] = True
                    page = search_norms(session, q=query, norms_snapshot_id=snapshot_id,
                        cursor=None, limit=3, timeout_ms=1200)
                    any_words = None
                    if not page.items:
                        any_words = _any_words_query(query)  # NORM-ANY-WORDS-01
                        if any_words is not None:
                            if strict_scope and receipt is not None:
                                receipt["additional_search_performed"] = True
                                active_query["any_words_query"] = any_words
                            try:
                                page = search_norms(session, q=any_words, norms_snapshot_id=snapshot_id,
                                    cursor=None, limit=3, timeout_ms=1200)
                            except DomainError:
                                if strict_scope:
                                    # The fresh policy's negative outcome requires
                                    # the whole bounded strategy to have completed.
                                    # A failed broader lookup remains pending.
                                    raise
                                # The second pass is broader than the first. One the search refuses (too broad, at capacity) leaves
                                # the query where the first pass left it -- no hit -- and the receipt says the second was tried.
                                session.rollback()
                    cache[key] = [{"snapshot_id": hit.norms_snapshot_id, "document_id": hit.norm_document_id,
                        "paragraph_id": hit.norm_paragraph_id, "designation": hit.designation,
                        "clause_number": hit.clause_number, "quote": hit.fragment.text[:2000],
                        "page_label": hit.page_label, "status": "candidate_not_verified"} for hit in page.items]
                    if receipt is not None:
                        cache_receipts[key] = {"has_more": page.next_cursor is not None, "received_hits": len(page.items),
                            **({} if any_words is None else {"any_words_query": any_words}),
                            "hits": [{"snapshot_id": hit.norms_snapshot_id, "document_id": hit.norm_document_id,
                                "paragraph_id": hit.norm_paragraph_id, "designation": hit.designation,
                                "clause_number": hit.clause_number, "page_label": hit.page_label,
                                "received_fragment_characters": len(hit.fragment.text),
                                "candidate_quote_characters": min(2000, len(hit.fragment.text)),
                                "candidate_quote_truncated": len(hit.fragment.text) > 2000,
                                "candidate_quote_sha256": hashlib.sha256(hit.fragment.text[:2000].encode("utf-8")).hexdigest()}
                                for hit in page.items]}
                if active_query is not None:
                    active_query.update(deepcopy(cache_receipts[key]), status="completed")
                for candidate in cache[key]:
                    if any(c["paragraph_id"] == candidate["paragraph_id"]
                            and (not query_planning or c["quote"] == candidate["quote"]) for c in candidates):
                        continue
                    candidates.append(candidate)
            item["norm_status"] = "candidates" if candidates else "unavailable" if item.get("norm_reason") == "lookup_window_exhausted" else "not_found"
            item["norm_candidates"] = candidates if full_document else candidates[:6]
        except DomainError as error:
            session.rollback()
            item["norm_status"] = "unavailable"
            item["norm_reason"] = "lookup_unavailable"
            if active_query is not None:
                active_query.update(status="failed", error_code=error.code.value, reason="lookup_unavailable")
        finish_receipt()
    semantic_inputs = observations
    if strict_scope:
        semantic_inputs = []
        for item in observations:
            plan = item.get("norm_query_plan", {})
            bounded = bool(plan.get("literal_scope")) or any(
                parse_norm_query(query).designation is not None or parse_norm_query(query).clause is not None
                for query in plan.get("queries", []))
            if bounded:
                # The existing semantic endpoint is snapshot-scoped, not
                # document/edition/clause-scoped. It cannot replace a valid
                # negative bounded answer with another standard's neighbour.
                plan["semantic_lookup"] = "not_requested_bound_scope"
            else:
                semantic_inputs.append(item)
    _semantic_candidates(session, semantic_inputs, snapshot_id, checkpoint=checkpoint, warnings=warnings,
                         full_document=full_document)
    return sorted(set(warnings))


#: `NORM-VECTOR-TEMP-01` (temporary embedder, see ``norms/semantic.py``). The observations a word search left without a paragraph -- it
#: found nothing, or the model proposed no query (a primary text finding) -- get candidates near their meaning. Off unless
#: ``AUDITMANAGER_NORM_EMBED_URL`` is set. **Nothing here is hidden**: a lookup that fails, or one past the run's window, leaves its
#: observation ``unavailable`` with its own reason -- a gap of the norm verification, so the procedure is ``partial`` and says why --
#: and the run's warnings and the worker's log name the failure.
_SEMANTIC_LOOKUPS_PER_RUN = 60
_SEMANTIC_TARGETS = frozenset({("not_found", None), ("unavailable", "query_not_proposed")})
_SEMANTIC_FAILED = "semantic_lookup_failed"
_SEMANTIC_WINDOW_EXHAUSTED = "semantic_lookup_window_exhausted"


def _semantic_candidates(session, observations, snapshot_id, *, checkpoint, warnings, full_document, url=None):
    url = norm_embed_url() if url is None else url
    if url is None or snapshot_id is None:
        return
    targets = [item for item in observations
               if (item.get("norm_status"), item.get("norm_reason")) in _SEMANTIC_TARGETS and not item.get("norm_candidates")
               and norm_observation_text(item)]
    for looked, item in enumerate(targets):
        if looked >= _SEMANTIC_LOOKUPS_PER_RUN:
            for rest in targets[looked:]:
                rest.update(norm_status="unavailable", norm_reason=_SEMANTIC_WINDOW_EXHAUSTED)
            warnings.append("norm_semantic_lookup_window_exhausted")
            return
        if checkpoint is not None:
            checkpoint("extended_norm_semantic_lookup")
        try:
            found = semantic_norm_candidates(session, snapshot_id=snapshot_id, value=norm_observation_text(item), url=url,
                                             limit=6 if full_document else 3)
        except (SemanticUnavailable, SQLAlchemyError) as error:
            session.rollback()
            _log.error("norm semantic lookup failed for run observations (%s): %s", type(error).__name__, error, exc_info=True)
            for rest in targets[looked:]:
                rest.update(norm_status="unavailable", norm_reason=_SEMANTIC_FAILED)
            warnings.append("norm_semantic_lookup_failed")
            return
        if found:
            item.update(norm_status="candidates", norm_candidates=found, norm_lookup_method=SEMANTIC_LOOKUP)


def run_extended_review(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
                        publish, progress, checkpoint, observations_document, snapshot_id=None, profile_sha256=None,
                        policy=None, bind_native=None, resume_state=None, visual_only=False) -> dict:
    """Dispatch the immutable accepted v1/v2 plan or the fresh windowed v3 workflow."""
    if isinstance(policy, dict) and policy.get("plan_version") == "extended-review-v3":
        return _run_workflow_v3(session,run=run,authority=authority,jobs=jobs,journal=journal,binding=binding,
            outputs=outputs,store=store,meter=meter,publish=publish,progress=progress,checkpoint=checkpoint,
            observations_document=observations_document,snapshot_id=snapshot_id,profile_sha256=profile_sha256,
            bind_native=bind_native,policy=policy,resume_state=resume_state,visual_only=visual_only)
    if isinstance(policy, dict) and policy.get("plan_version") == "extended-review-v2":
        return _run_workflow_v2(session,run=run,authority=authority,jobs=jobs,journal=journal,binding=binding,
            outputs=outputs,store=store,meter=meter,publish=publish,progress=progress,checkpoint=checkpoint,
            observations_document=observations_document,snapshot_id=snapshot_id,profile_sha256=profile_sha256,
            bind_native=bind_native,full_document=policy.get("max_blocks") == "all",policy=policy)
    from auditmanager.analysis.public import read_artifact
    state: dict[str, Any] = {"format": FORMAT, "preliminary": True, "section": "unknown",
        "observations": [], "sources": [], "warnings": [], "coverage": {
            "blocks_total": 0, "blocks_selected": 0, "blocks_processed": 0, "blocks_remaining": 0, "skipped": []}}
    def save(status):
        # Do not expose internal block contexts or model prompt material in the read DTO.
        public = {k: v for k, v in state.items() if k not in {"text_items", "context_sections"}}
        public["sources"] = [{k: v for k, v in source.items() if k != "context"} for source in state["sources"]]
        progress(status, public)
    try:
        doc = DocumentRepository().get_version(session, run.version_uid)
        section = doc.classification.section_code if doc.classification is not None else "unknown"
        state["section"] = section
        inputs = {}
        for key in ("geometry.portal_blocks", "geometry.page_crops", "prepared.text_layer", "context.document_graph"):
            ref = outputs.refs.get(key)
            if ref is None:
                state["warnings"].append("source_geometry_unavailable")
                save("unavailable")
                return state
            inputs[key], _ = read_artifact(store, parse_blob_id(ref.blob_id), expected_role=key)
        recognised = None
        recognised_ref = outputs.refs.get("prepared.recognised_text")
        if recognised_ref is not None:
            recognised, _ = read_artifact(store, parse_blob_id(recognised_ref.blob_id), expected_role="prepared.recognised_text")
        state = plan_extended_inputs(version_uid=run.version_uid, section=section,
            portal=inputs["geometry.portal_blocks"], manifest=inputs["geometry.page_crops"],
            text_layer=inputs["prepared.text_layer"], graph=inputs["context.document_graph"], observations=observations_document,
            recognised=recognised)
        state["source_sha256"] = extended_digest({"source": state["source_sha256"],
            "profile_sha256": profile_sha256, "norms_snapshot_id": snapshot_id, "analysis_profile_id": getattr(run, "analysis_profile_id", None),
            "prompt_bundle_id": getattr(run, "prompt_bundle_id", None), "run_input_digest": getattr(run, "frozen_input_digest", None)})
        state["model_id"] = binding.config.model_id
        state["provider_mode"] = binding.adapter.provider_mode.value
        save("running")
        images = [s for s in state["sources"] if s["kind"] == "image"]
        if not images:
            state["observations"] = finalize_extended_items(state["text_items"], state["sources"])
            state["warnings"].extend(_norms(session, state["observations"], snapshot_id))
            state["warnings"].append("no_image_blocks_available")
            save("unavailable")
            return state
        block_items = []
        for start in range(0, len(images), 8):
            batch = images[start:start+8]
            crops = []
            for source in batch:
                raw = store.read(parse_blob_id(source["blob_id"]), verify=True)
                if len(raw) != source["size_bytes"] or hashlib.sha256(raw).hexdigest() != source["crop_sha256"]:
                    raise _refuse("extended_crop_digest_invalid")
                crops.append(CropImage(source["source_id"], raw))
            payload, context_cut = extended_block_payload(section=section, batch=batch,
                sections=state["context_sections"], coverage=state["coverage"])
            if context_cut and "page_context_truncated" not in state["warnings"]:
                state["warnings"].append("page_context_truncated")
            request = attach_images(build_extended_request(**_kw(binding, "blocks"), run_id=run.run_id,
                phase="blocks", section=section, payload=payload), crops)
            response, reused = _call(session, run_id=run.run_id, authority=authority, jobs=jobs, journal=journal,
                binding=_cell(binding, "blocks"), request=request, phase=f"blocks:{start//8}", source_sha256=state["source_sha256"],
                meter=meter, store=store, publish=publish, checkpoint=checkpoint)
            if response.truncated:
                raise _refuse("extended_response_truncated")
            block_items.extend(parse_extended_reply(response.output_text,
                allowed_sources={s["source_id"] for s in batch}))
            state["coverage"]["blocks_processed"] += len(batch)
            state["coverage"]["blocks_remaining"] = state["coverage"]["blocks_total"] - state["coverage"]["blocks_processed"]
            state["observations"] = finalize_extended_items(block_items, state["sources"])
            save("running")
        items = finalize_extended_items([*state["text_items"], *block_items], state["sources"])
        state["warnings"].extend(_norms(session, items, snapshot_id))
        # Search excerpts can differ by query for one paragraph. Freeze one real
        # excerpt per ID, shared by both the model context and its validation.
        norm_context = {}
        for item in items:
            item["norm_candidates"] = [norm_context.setdefault(c["paragraph_id"], c)
                for c in item["norm_candidates"]]
        # Persist the original source-bound observations before model review.
        # A malformed/failed merge must not erase either text or visual inputs.
        state["observations"] = items
        save("running")
        indexed = {"xmi_"+extended_digest({"ordinal": i, "observation": item})[:24]: item for i, item in enumerate(items)}
        if any(len(item["description"]) > 800 for item in items):
            state["warnings"].append("merge_context_truncated")
        # The v1 plan's semantic merge is the « Свод » of the original; the layout values it by analogy with the cross-check row.
        request = build_extended_request(**_kw(binding, "cross_check"), run_id=run.run_id, phase="merge",
            section=section, payload={"observations": [{
                "title": item["title"], "description": item["description"][:800], "source_ids": item["source_ids"],
                "norm_candidate_ids": [c["paragraph_id"] for c in item["norm_candidates"]],
                "norm_status": item["norm_status"], "input_id": key} for key, item in indexed.items()],
                "norm_context": list(norm_context.values()), "norm_review_version": "quote-review-v1",
                "sources": [{k:v for k,v in s.items() if k != "context"}
                for s in state["sources"]], "source_sha256": state["source_sha256"]})
        response, reused = _call(session, run_id=run.run_id, authority=authority, jobs=jobs, journal=journal,
            binding=_cell(binding, "cross_check"), request=request, phase="merge", source_sha256=state["source_sha256"],
            meter=meter, store=store, publish=publish, checkpoint=checkpoint)
        if response.truncated:
            raise _refuse("extended_response_truncated")
        merged = parse_extended_reply(response.output_text, allowed_sources={s["source_id"] for s in state["sources"]}, expected_inputs=indexed)
        represented = {k for item in merged for k in item["input_ids"]}
        # A semantic merge may consolidate but never silently lose an input observation.
        omitted = [item for key, item in indexed.items() if key not in represented]
        if omitted:
            state["warnings"].append("merge_omitted_sources_retained")
            merged.extend(omitted)
        for item in merged:
            ids = item.pop("input_ids", None)
            if ids is None:  # retained original observation after an omitted merge input
                continue
            candidates = {c["paragraph_id"]: c for key in ids for c in indexed[key]["norm_candidates"]}
            item["norm_candidates"] = list(candidates.values())
            item["norm_status"] = "candidates" if candidates else "unavailable"
            if not candidates:
                item["norm_reason"] = "no_candidate_context"
        state["observations"] = finalize_extended_items(merged, state["sources"])
        status = "partial" if state["coverage"]["blocks_remaining"] or state["warnings"] else "completed"
        save(status)
        return state
    except (DomainError, ValueError, KeyError, TypeError) as error:
        reason = error.detail_fields.get("reason") if isinstance(error, DomainError) else "extended_reply_or_source_invalid"
        state["warnings"].append(str(reason or "extended_review_failed"))
        # These remain explicit preliminary candidates, not canonical publication.
        for item in state.get("observations", []):
            item.pop("norm_queries", None)
        save("failed")
        return state


def _attach_consolidation(result, *, version_uid, include_saved_relationships=False):
    """Add a derived view; raw candidates, windows and expert state are unchanged."""
    from auditmanager.analysis.public import consolidate_extended_observations
    try:
        source_rows = result.get("sources", [])
        windows = result.get("windows", [])
        if not isinstance(source_rows, list) or not isinstance(windows, list):
            raise ValueError("consolidation_saved_source_invalid")
        sources = list(source_rows)
        for window in windows:
            if not isinstance(window, dict) or not isinstance(window.get("sources", []), list):
                raise ValueError("consolidation_window_source_invalid")
            sources.extend(window.get("sources", []))
        if "flow_repair_policy" in result:
            from auditmanager.analysis.public import flow_repair_helper
            derived = flow_repair_helper("consolidate_flow", result.get("observations", []),
                sources=sources, version_uid=version_uid,
                relationships=result.get("semantic_relationships", []),
                ensemble_batches=result.get("block_ensemble", {}).get("batches", []))
        else:
            derived = consolidate_extended_observations(result.get("observations", []),
            sources=sources, version_uid=version_uid,
            ensemble_batches=result.get("block_ensemble", {}).get("batches", [])
                if "quality_policy" in result or include_saved_relationships else None)
    except ValueError:
        derived = {"consolidation": {"version": "strict-cross-window-v1",
            "method": "identical_text_shared_source", "complete": False,
            "reason": "saved_observation_or_source_binding_invalid",
            "raw_count": len(result.get("observations", [])) if isinstance(result.get("observations"), list) else 0,
            "group_count": 0, "canonical_findings_unchanged": True,
            "expert_decisions_written": False}, "consolidated_observations": []}
    return dict(result, **derived)


def read_extended_review(sessions, blob_store, run_id: str) -> dict:
    with sessions() as session:
        run = RunRepository().get(session, run_id)
        rows = RunRepository().stage_results(session, run_id)
        stage = next((s for s in rows if s.stage_id == "text_analysis"), None)
        refs = [] if stage is None else stage.artifacts
        ref = next((r for r in refs if r.get("role") == EXTENDED_REVIEW_ROLE), None)
        if ref is None:
            from auditmanager.runs.cost_policy import read_run_cost_policy
            policy = read_run_cost_policy(session,run_id=run_id,default_ceiling_usd=1.).extended_review
            if isinstance(policy,dict) and policy.get("plan_version") in {"extended-review-v2","extended-review-v3"}:
                terminal = run.state in {"published","partial","failed","cancelled"}
                reason = "workflow_not_executed" if terminal else None
                if terminal and any(row.stage_id != "text_analysis" and row.status in {"failed","partial"} for row in rows):
                    reason = "source_preparation_failed"
                return {"run_id":run_id,"status":"unavailable" if terminal else "not_started",
                    "result":dict(planned_workflow_result(reason=reason,terminal=terminal,policy=policy),
                        version_uid=run.version_uid)}
            return {"run_id":run_id,"status":"unavailable","result":{
                "workflow_version":"extended-review-v1" if policy else None,"procedures":[],
                "version_uid":run.version_uid,"reason":"legacy_policy_no_v2_workflow" if policy else "not_in_accepted_policy"}}

        version_uid = run.version_uid
    raw = blob_store.read(parse_blob_id(ref["blob_id"]), verify=True)
    if len(raw) != ref["size_bytes"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=EXTENDED_REVIEW_ROLE)
    try:
        doc = json.loads(raw)
        status = doc["status"]
        if (doc.get("artifact_role") != EXTENDED_REVIEW_ROLE or doc.get("version_uid") != version_uid
                or doc.get("run_id") != run_id or status not in {"running","completed","partial","failed","unavailable"}):
            raise ValueError()
        result = doc["result"]
        if not isinstance(result, dict) or result.get("version_uid", version_uid) != version_uid:
            raise ValueError()
        # Read projection from the already checked envelope/Run binding. Older
        # workflow snapshots did not repeat the source identity inside result.
        # This adds no observation, anchor, paid request or guessed source.
        projected = dict(result, version_uid=version_uid)
        consolidation = result.get("consolidation")
        if (status in {"completed", "partial", "failed", "unavailable"}
                and (result.get("workflow_version") == "extended-review-v3" or "quality_policy" in result)
                and (not isinstance(consolidation, dict)
                    or consolidation.get("version") != "strict-cross-window-v1")):
            projected = _attach_consolidation(projected, version_uid=version_uid)
        if (status in {"completed", "partial", "failed", "unavailable"}
                and result.get("workflow_version") == "extended-review-v2"
                and isinstance(result.get("block_ensemble"), dict)
                and isinstance(result["block_ensemble"].get("batches"), list)):
            # Read-only presentation of retained legacy ensemble links; no saved
            # artifact, consent, observation or expert decision is rewritten.
            projected = _attach_consolidation(projected, version_uid=version_uid, include_saved_relationships=True)
        return {"run_id": run_id, "status": status, "result": projected}
    except (ValueError, KeyError, TypeError):
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=EXTENDED_REVIEW_ROLE) from None


def _planned_global_cross_window(policy, *, reason=None, terminal=False):
    result = {"version": "cross-window-comprehensive-v1", "status": "queued", "policy": deepcopy(policy),
        "source_sha256": None, "manifest_sha256": None, "coverage": {"global_semantic_complete": False},
        "phase_coverage": {}, "phase_call_counts": {}, "batches": [], "omitted": [],
        "observations": [], "original_observations": [], "sources": [], "warnings": [],
        "report": {"status": "queued", "preliminary": True, "expert_decisions_written": False},
        "procedures": [{"id": identity, "title": title, "status": "queued"} for identity, title in (
            ("comprehensive_analysis", "Межоконная комплексная сверка"),
            ("norm_verification", "Нормативная сверка межоконных наблюдений"),
            ("finding_review", "Критик межоконных наблюдений"),
            ("finding_correction", "Предложения по уточнению межоконных наблюдений"),
            ("report_generation", "Межоконный отчёт"))]}
    if terminal:
        result.update(status="skipped", reason=reason or "source_preparation_failed")
        result["report"].update(status="skipped", reason=result["reason"])
        for procedure in result["procedures"]:
            procedure.update(status="skipped", reason=result["reason"])
    return result


def planned_workflow_result(*, reason=None, terminal=False, policy=None):
    from auditmanager.analysis.public import extended_workflow_procedures
    v3=isinstance(policy,dict) and policy.get("plan_version")=="extended-review-v3"
    original=False
    if v3:
        from auditmanager.analysis.public import extended_workflow_procedures_v3
        procedures=extended_workflow_procedures_v3()
    else:
        procedures = extended_workflow_procedures()
        # `V2-ORIGINAL-REVIEW-01`: a v2 consent that carries the marker plans the original's critic and corrector after the norms.
        original=_original_review_enabled(policy)
        if original:
            procedures = [*procedures, *original_review_procedures()]
        if isinstance(policy, dict) and "quality_policy" in policy:
            for procedure in procedures:
                if procedure["id"] == "finding_review":
                    procedure.update(title="Критик наблюдений", model_called=False)
    if reason:
        for procedure in procedures:
            procedure.update(status="skipped" if terminal else "queued", reason=reason)
    version="extended-review-v3" if v3 else "extended-review-v2"
    parameter_result = {}
    if v3 and "project_parameters_policy" in policy:
        from .project_parameters import planned_parameters
        parameter_result = {"project_parameters": planned_parameters(policy["project_parameters_policy"], reason=reason, terminal=terminal)}
    return {"format":version,"workflow_version":version,"preliminary":True,
        **({"finding_proposals": deepcopy(policy["finding_proposals"])}
           if isinstance(policy, dict) and "finding_proposals" in policy else {}),
        **({"quality_policy": deepcopy(policy["quality_policy"])} if isinstance(policy, dict) and "quality_policy" in policy else {}),
        **({"flow_repair_policy": deepcopy(policy["flow_repair_policy"])}
           if isinstance(policy, dict) and "flow_repair_policy" in policy else {}),
        **({"original_review": {**original_review_plan(), **({"mode": "substantive"}
            if isinstance(policy, dict) and "quality_policy" in policy else {})}} if original else {}),
        **parameter_result,
        **({"project_parameter_context_policy": deepcopy(policy["project_parameter_context_policy"])}
           if v3 and "project_parameter_context_policy" in policy else {}),
        **({"norm_paragraph_context_policy": deepcopy(policy["norm_paragraph_context_policy"]), "normative_context_receipts": []}
           if v3 and "norm_paragraph_context_policy" in policy else {}),
        **({"global_cross_window": _planned_global_cross_window(policy["global_cross_window_policy"], reason=reason, terminal=terminal)}
           if v3 and "global_cross_window_policy" in policy else {}),
        **({"windows":[],"window_progress":{"completed":0,"total":policy["max_windows"],"current":None,"window_size":16},
            "rules_sha256":policy["rules_sha256"],"section":policy.get("section_code"),"primary_text_status":"pending",
            "review_scope":"full_document",
            **({"coverage_version":"batched-v1","phase_call_limits":dict(policy["phase_call_limits"]),
                "phase_coverage":{},"batches":[],"phase_call_counts":{},
                **{key:policy[key] for key in ("coverage_budget_mode","estimated_text_characters",
                    "comprehensive_piece_characters") if key in policy}}
                if policy.get("coverage_version")=="batched-v1" else {})} if v3 else {}),
        "observations":[],"sources":[],"warnings":[],"procedures":procedures,"ocr_status":"not_performed",
        "reason":reason,"coverage":{"blocks_total":0,"blocks_selected":0,"blocks_processed":0,
            "blocks_remaining":0,"skipped":[]}}


def _full_comprehensive_review(*, run, model_id, section, state, pages, block_items, call, settings=None, related_index=None,
        flow_policy=None, phase=None, pair_call_limit=0):
    """Cover every page character and source in repeatable provider-sized batches."""
    if flow_policy is not None:
        return _flow_comprehensive_review(run=run, model_id=model_id, section=section, state=state, pages=pages,
            block_items=block_items, call=call, settings=settings, related_index=related_index,
            phase=phase, pair_call_limit=pair_call_limit)
    from auditmanager.analysis.public import build_comprehensive_request
    units = []
    sources_by_page = {}
    for source in state["sources"]:
        sources_by_page.setdefault(source.get("page_number"), []).append(source)
    for page in pages:
        number = page["page_number"]
        value = str(page.get("text", ""))
        source_id = "native_text_" + extended_digest({"version_uid": run.version_uid,
            "page": number, "text": value})[:24]
        source = {"source_id": source_id, "kind": "text", "source_type": "native_text",
            "page_number": number, "version_uid": run.version_uid, "quote": value[:2000],
            "text_sha256": hashlib.sha256(value.encode()).hexdigest()}
        state["sources"].append(source)
        sources_by_page.setdefault(number, []).append(source)
        page_ids = {source["source_id"] for source in sources_by_page[number]}
        visual = [item for item in block_items if page_ids.intersection(item["source_ids"])]
        textual = [item for item in state["text_items"] if page_ids.intersection(item["source_ids"])]
        visual_batches = [visual[i:i+40] for i in range(0, len(visual), 40)] or [[]]
        text_batches = [textual[i:i+40] for i in range(0, len(textual), 40)] or [[]]
        pieces = [value[i:i+40_000] for i in range(0, len(value), 40_000)] or [""]
        tasks = [(index, 0) for index in range(len(pieces))]
        tasks.extend((0, index) for index in range(1, max(len(visual_batches), len(text_batches))))
        for piece_index, batch_index in tasks:
            chosen_visual = visual_batches[batch_index] if batch_index < len(visual_batches) else []
            chosen_text = text_batches[batch_index] if batch_index < len(text_batches) else []
            allowed = {source_id}
            for item in (*chosen_visual, *chosen_text):
                allowed.update(item["source_ids"])
            units.append(({"source_id": source_id, "page_number": number,
                "text": pieces[piece_index], "character_start": piece_index * 40_000},
                chosen_visual, chosen_text, allowed))

    observations = []
    batch_contexts, batch_visual, batch_text, batch_allowed = [], [], [], set()
    def flush(batch_number):
        if not batch_contexts:
            return
        sources = [{k: v for k, v in source.items() if k != "context"}
            for source in state["sources"] if source["source_id"] in batch_allowed]
        payload={"native_context": batch_contexts, "visual_observations": batch_visual,
                "text_observations": batch_text, "sources": sources,
                "source_sha256": state["source_sha256"], "coverage": state["coverage"]}
        allowed = set(batch_allowed)
        if related_index is not None:
            from auditmanager.analysis.public import select_related_review_context
            related = select_related_review_context(related_index,
                texts=[row["text"] for row in batch_contexts] + [row["title"] + " " + row["description"] for row in batch_visual],
                page_numbers={row["page_number"] for row in batch_contexts})
            payload["related_context"] = related
            for source in related["sources"]:
                if source["source_id"] not in allowed:
                    sources.append(source); allowed.add(source["source_id"])
                if source["source_id"] not in {row["source_id"] for row in state["sources"]}:
                    state["sources"].append(source)
            state.setdefault("related_context_receipts", []).append({"identity": f"comprehensive:{batch_number}", **related})
            if not related["complete"]:
                state["warnings"].append("related_context_incomplete")
        request = build_comprehensive_request(model_id=model_id, run_id=run.run_id, section=section, settings=settings, payload=payload)
        response = call(request, f"comprehensive:{batch_number}")
        observations.extend(parse_extended_reply(response.output_text, allowed_sources=allowed))

    batch_number = 0
    for context, visual, textual, allowed in units:
        if batch_contexts and (len(batch_contexts) == 8
                or sum(len(item["text"]) for item in batch_contexts) + len(context["text"]) > 40_000
                or len(batch_visual) + len(visual) > 40 or len(batch_text) + len(textual) > 40):
            flush(batch_number)
            batch_number += 1
            batch_contexts, batch_visual, batch_text, batch_allowed = [], [], [], set()
        batch_contexts.append(context)
        batch_visual.extend(visual)
        batch_text.extend(textual)
        batch_allowed.update(allowed)
    flush(batch_number)
    return observations


def _flow_comprehensive_review(*, run, model_id, section, state, pages, block_items, call, settings,
        related_index, phase, pair_call_limit):
    """Checkpoint independent findings and original-style T/G relationships per packet."""
    from auditmanager.analysis.public import (flow_repair_helper, select_related_review_context,
        build_semantic_repair_request)
    text_items = state["text_items"]
    for kind, rows in (("text", text_items), ("visual", block_items)):
        for ordinal, item in enumerate(rows):
            item.setdefault("origin_id", flow_repair_helper("origin_id", {**item, "occurrence": ordinal}, kind))
    registry = {source["source_id"]: source for source in state["sources"]}
    page_texts = {page["page_number"]: str(page.get("text", "")) for page in pages}
    native_by_page = {}
    for number, value in page_texts.items():
        for start in range(0, max(1, len(value)), 40_000):
            text = value[start:start+40_000]
            ref = "native_text_" + extended_digest({"version_uid": run.version_uid,
                "page": number, "text": value, "character_start": start})[:24]
            source = {"source_id": ref, "kind": "text", "source_type": "native_text",
                "page_number": number, "version_uid": run.version_uid, "quote": text,
                "character_start": start, "character_end": start+len(text),
                "text_sha256": hashlib.sha256(value.encode()).hexdigest()}
            registry[ref] = source; state["sources"].append(source)
            native_by_page.setdefault(number, []).append({"source_id": ref, "page_number": number,
                "text": text, "character_start": start})
    empty_index = {"by_object": {}, "excerpts": []}
    origins = {item["origin_id"]: item for item in [*text_items, *block_items]}
    def item_pages(item):
        return {registry[ref].get("page_number") for ref in item["source_ids"] if ref in registry}
    def object_keys(item):
        return set(select_related_review_context(empty_index,
            texts=[item["title"] + " " + item["description"]], page_numbers=set())["object_keys"])
    page_map = {key: item_pages(item) for key, item in origins.items()}
    keys = {key: object_keys(item) for key, item in origins.items()}
    required = sorted({tuple(sorted((left["origin_id"], right["origin_id"])))
        for left in text_items for right in block_items
        if page_map[left["origin_id"]] & page_map[right["origin_id"]]
            or keys[left["origin_id"]] & keys[right["origin_id"]]})
    packets = []
    for number in sorted(native_by_page):
        visual = [item for item in block_items if number in page_map[item["origin_id"]]]
        textual = [item for item in text_items if number in page_map[item["origin_id"]]]
        count = max(1, math.ceil(len(visual)/10), math.ceil(len(textual)/10))
        for context in native_by_page[number]:
            for index in range(count if context["character_start"] == 0 else 1):
                packets.append({"native_context": [context], "visual_observations": visual[index*10:(index+1)*10],
                    "text_observations": textual[index*10:(index+1)*10], "pair_packet": False})
    co_located = set()
    for packet in packets:
        refs = {item["origin_id"] for item in [*packet["text_observations"], *packet["visual_observations"]]}
        packet["required_pairs"] = [list(pair) for pair in required if set(pair) <= refs]
        co_located.update(tuple(pair) for pair in packet["required_pairs"])
    pending_pairs = [pair for pair in required if pair not in co_located]
    # Additional pair work is explicitly capped and priced in the fresh consent.
    pair_packets = 0
    while pending_pairs and pair_packets < pair_call_limit:
        chosen, refs = [], set()
        for pair in pending_pairs:
            if len(chosen) < 100 and len(refs | set(pair)) <= 40:
                chosen.append(pair); refs.update(pair)
        pending_pairs = [pair for pair in pending_pairs if pair not in chosen]
        numbers = sorted(set().union(*(page_map[ref] for ref in refs)))
        contexts = []
        budget = 40_000
        for number in numbers:
            # The pair's actual observation quotes are always present below;
            # relevant native excerpts supplement them without unbounded pages.
            for context in native_by_page.get(number, []):
                if not budget:
                    break
                copied = dict(context, text=context["text"][:budget])
                contexts.append(copied); budget -= len(copied["text"])
        packets.append({"native_context": contexts,
            "visual_observations": [item for item in block_items if item["origin_id"] in refs],
            "text_observations": [item for item in text_items if item["origin_id"] in refs],
            "required_pairs": [list(pair) for pair in chosen], "pair_packet": True})
        pair_packets += 1
    observations, relationships, receipts = [], [], []
    state["comprehensive_batches"] = receipts
    state["semantic_relationships"] = relationships
    state["semantic_pair_coverage"] = {"expected": len(required), "valid": 0,
        "pending": len(required), "refused": 0, "excluded": 0,
        "unpackaged_pairs": [list(pair) for pair in pending_pairs], "pair_call_limit": pair_call_limit}
    covered = set()
    for ordinal, packet in enumerate(packets):
        own = {ref for item in [*packet["text_observations"], *packet["visual_observations"]]
            for ref in item["source_ids"]}
        own.update(context["source_id"] for context in packet["native_context"])
        selected = [{key: deepcopy(value) for key, value in registry[ref].items() if key != "context"}
            for ref in sorted(own) if ref in registry]
        payload = {**packet, "sources": selected, "source_sha256": state["source_sha256"], "coverage": state["coverage"]}
        if related_index is not None:
            related = select_related_review_context(related_index,
                texts=[item["title"] + " " + item["description"] for item in
                    [*packet["text_observations"], *packet["visual_observations"]]],
                page_numbers={row["page_number"] for row in packet["native_context"]})
            payload["related_context"] = related
            for source in related["sources"]:
                if source["source_id"] not in own:
                    selected.append(source); own.add(source["source_id"])
                if source["source_id"] not in registry:
                    registry[source["source_id"]] = source; state["sources"].append(source)
        refs = {item["origin_id"] for item in [*packet["text_observations"], *packet["visual_observations"]]}
        identity = f"comprehensive:{ordinal}"
        request = flow_repair_helper("build_flow_comprehensive_request", model_id=model_id,
            run_id=run.run_id, section=section, settings=settings, payload=payload)
        response = call(request, identity)
        rejected = []
        def parse(text, refused, expected_pairs=None):
            expected_pairs = packet["required_pairs"] if expected_pairs is None else expected_pairs
            try:
                return flow_repair_helper("parse_flow_comprehensive_reply", text, allowed_sources=own,
                    origins=refs, required_pairs=expected_pairs, rejected=refused)
            except (ValueError, TypeError, KeyError) as error:
                refused.append({"reason": str(error) if str(error).isidentifier() else "reply_unreadable"})
                return [], [], expected_pairs
        found, links, missing = parse(response.output_text, rejected)
        if response.truncated:
            rejected.append({"reason": "extended_response_truncated"})
        original_refusals = deepcopy(rejected)
        if rejected:
            if found or links:
                state["observations"] = finalize_extended_items([*text_items, *block_items, *observations, *found], state["sources"])
                state["semantic_relationships"] = [*relationships, *(dict(link, packet=identity) for link in links)]
                if phase is not None:
                    phase("comprehensive_analysis", "running")
            repaired_request = flow_repair_helper("build_flow_repair_request", request, rejected=rejected[:128],
                accepted_records=found, reply_sha256=response.response_sha256, procedure="comprehensive",
                required_pairs=missing, accepted_relationships=links)
            repaired_response = call(repaired_request, identity + ":repair:1")
            rejected = []
            repaired, repaired_links, _ = parse(repaired_response.output_text, rejected, expected_pairs=missing)
            by_hash = {extended_digest(item): item for item in [*found, *repaired]}
            found = list(by_hash.values())
            by_pair = {tuple(sorted((link["left_origin_id"], link["right_origin_id"]))): link for link in links}
            for link in repaired_links:
                by_pair.setdefault(tuple(sorted((link["left_origin_id"], link["right_origin_id"]))), link)
            links = list(by_pair.values())
            # Completion belongs to the union of both validated responses, not
            # to the addressed repair's intentionally smaller answer alone.
            missing = [list(pair) for pair in packet["required_pairs"] if tuple(sorted(pair)) not in by_pair]
            rejected = [row for row in rejected if row.get("reason") != "flow_required_pairs_missing"]
            if missing:
                rejected.append({"reason": "flow_required_pairs_missing", "missing_pairs": missing})
            if repaired_response.truncated:
                rejected.append({"reason": "extended_response_truncated"})
        observations.extend(found); relationships.extend(dict(link, packet=identity) for link in links)
        state["semantic_relationships"] = relationships
        covered.update(tuple(sorted((link["left_origin_id"], link["right_origin_id"]))) for link in links)
        receipts.append({"identity": identity, "pair_packet": packet["pair_packet"],
            "origin_ids": sorted(refs), "required_pairs": packet["required_pairs"],
            "missing_pairs": missing, "accepted_observations": len(found),
            "rejected_records": original_refusals, "unresolved_records": deepcopy(rejected),
            "request_sha256": request.request_sha256, "response_sha256": response.response_sha256})
        valid = len(set(required) & covered)
        state["semantic_pair_coverage"].update(valid=valid, pending=len(required)-valid)
        # Durable progress precedes the next provider call; the ordinary exact
        # provider journal supplies paid-response replay after a process restart.
        state["observations"] = finalize_extended_items([*text_items, *block_items, *observations], state["sources"])
        if phase is not None:
            phase("comprehensive_analysis", "running")
    state["comprehensive_execution_complete"] = not pending_pairs and not any(
        receipt["unresolved_records"] or receipt["missing_pairs"] for receipt in receipts)
    return observations


#: The reason of a norm stage in which a reply record was refused or an input got no accepted record.
NORM_REPLY_REFUSED = "norm_verification_reply_refused"


def _full_norm_verification(*, session, run, model_id, section, state, snapshot_id, call, phase, checkpoint, settings=None,
        flow_policy=None):
    """Search and review every candidate-bearing observation in bounded model calls."""
    if flow_policy is not None:
        return _flow_norm_verification(session=session, run=run, model_id=model_id, section=section,
            state=state, snapshot_id=snapshot_id, call=call, phase=phase, checkpoint=checkpoint, settings=settings)
    from auditmanager.analysis.public import build_norm_review_request
    items = state["observations"]
    state["warnings"].extend(_norms(session, items, snapshot_id,
        full_document=True, checkpoint=checkpoint))
    registry = {}
    for item in items:
        item["norm_candidates"] = [registry.setdefault(candidate["paragraph_id"], candidate)
            for candidate in item.get("norm_candidates", [])]
    candidates = [item for item in items if item.get("norm_candidates")]
    asked = [item for item in items if _asked_norm_question(item)]
    if not candidates:
        if snapshot_id is not None and not asked:
            phase("norm_verification", "completed", "no_normative_question")  # NORM-COVERAGE-01
        else:
            phase("norm_verification", "unavailable",
                "corpus_unavailable" if snapshot_id is None else "candidate_context_unavailable")
        return
    batches = []
    batch, characters = [], 0
    for item in candidates:
        size = len(item["title"]) + len(item["description"]) + sum(
            len(candidate["quote"]) for candidate in item["norm_candidates"])
        if batch and (len(batch) == 40 or characters + size > 80_000):
            batches.append(batch)
            batch, characters = [], 0
        batch.append(item)
        characters += size
    if batch:
        batches.append(batch)
    refused = False
    for batch_number, batch in enumerate(batches):
        indexed = {"xni_" + extended_digest({"ordinal": i, "item": item})[:24]: item
            for i, item in enumerate(batch, start=batch_number * 40)}
        norm_context = {candidate["paragraph_id"]: candidate
            for item in batch for candidate in item["norm_candidates"]}
        request = build_norm_review_request(model_id=model_id, run_id=run.run_id, section=section, settings=settings,
            quote_echo=False,
            payload={"observations": [{"title": item["title"], "description": item["description"],
                "source_ids": item["source_ids"], "input_id": key,
                "norm_candidate_ids": [candidate["paragraph_id"] for candidate in item["norm_candidates"]]}
                for key, item in indexed.items()], "norm_context": list(norm_context.values()),
                "source_sha256": state["source_sha256"]})
        refused |= _review_norms_per_record(state=state, request=request, call=call,
            identity=f"norm_verification:{batch_number}", indexed=indexed)
    if refused:
        phase("norm_verification", "partial", NORM_REPLY_REFUSED)
        return
    # NORM-COVERAGE-01: complete when every observation that asked a norm question has its candidates; one that asked none (a primary
    # text finding, a cross-check point without a normative question) is not a gap of this procedure.
    phase("norm_verification", "partial" if any(not item.get("norm_candidates") for item in asked) else "completed")


def _review_norms_per_record(*, state, request, call, identity, indexed, flow=False, on_accepted=None):
    """Ask one norm review question and read its reply per record (`NORM-REPLY-PER-RECORD-01`).

    One refused record costs only its own input: the others keep their assessment, the refused
    one is ``not_reviewed`` with ``norm_verification_reply_refused``, and the stage goes on
    (``partial``) so the critic and the corrector still run. The receipt of a refusal is in
    ``state["reply_refusals"]``; ``policy={}`` means no repair call is ever made here. A reply
    that is not valid as a whole refuses every input of the question the same way. A transport
    failure (``DomainError``) is not a reply and propagates. Returns whether the question has a
    gap: a refusal receipt (a refused record, a truncated reply) or an input with no accepted
    record, one the reply did not carry included.
    """
    from auditmanager.analysis.public import parse_norm_review
    response = call(request, identity)
    allowed = {source["source_id"] for source in state["sources"]}
    reviewed, gap = _received_reply(state=state, request=request, response=response, call=call, identity=identity,
        parse=lambda text, **kwargs: parse_norm_review(text, observations=indexed, allowed_sources=allowed,
            quote_echo=False, **kwargs), policy={"semantic_repair_attempts": 1} if flow else {},
        expected_inputs=set(indexed) if flow else None, on_accepted=on_accepted)
    accepted = {result["input_ids"][0]: result for result in reviewed}
    for key, item in indexed.items():
        if key in accepted:
            item.update(norm_assessment=accepted[key]["norm_assessment"], norm_review_status="reviewed",
                norm_review_reason=None)
        else:
            item.update(norm_review_status="not_reviewed", norm_review_reason=NORM_REPLY_REFUSED)
            gap = True
    return gap


def _flow_norm_verification(*, session, run, model_id, section, state, snapshot_id, call, phase, checkpoint, settings):
    """Resolver parity: a valid negative lookup is completed work, not a failed job."""
    from auditmanager.analysis.public import build_norm_review_request
    items = state["observations"]
    state["warnings"].extend(_norms(session, items, snapshot_id, full_document=True,
        checkpoint=checkpoint, query_planning=True, strict_scope=True,
        lookup_receipts=state.setdefault("norm_lookup_receipts", [])))
    candidates = [item for item in items if item.get("norm_candidates")]
    for item in items:
        if item.get("norm_status") == "not_found":
            item.update(norm_review_status="not_required", finding_norm_status="not_verified",
                norm_review_reason="search_completed_without_match")
        elif item.get("norm_status") == "not_applicable":
            item.update(norm_review_status="not_required", finding_norm_status="not_applicable")
        elif item.get("norm_status") == "unavailable":
            item.update(norm_review_status="not_reviewed", finding_norm_status="not_verified")
    # Deduplicate transmission by exact fragment, never replace all occurrences
    # of a paragraph with its first returned quote. Each variant has a temporary
    # request-local alias; persisted citations return the real paragraph identity.
    batches, batch, characters = [], [], 0
    for item in candidates:
        size = len(item["title"]) + len(item["description"]) + sum(len(c["quote"]) for c in item["norm_candidates"])
        if batch and (len(batch) >= 40 or characters + size > 80_000):
            batches.append(batch); batch, characters = [], 0
        batch.append(item); characters += size
    if batch:
        batches.append(batch)
    for number, batch in enumerate(batches):
        originals, indexed, context = {}, {}, {}
        alias_to_paragraph = {}
        for ordinal, item in enumerate(batch):
            key = "xni_" + extended_digest({"observation_id": item["observation_id"]})[:24]
            originals[key] = item
            copied = deepcopy(item)
            for candidate in copied["norm_candidates"]:
                real = candidate["paragraph_id"]
                alias = "xnv_" + extended_digest({"paragraph_id": real, "snapshot_id": candidate.get("snapshot_id"),
                    "document_id": candidate.get("document_id"), "quote": candidate["quote"]})[:24]
                candidate.update(paragraph_id=alias, actual_paragraph_id=real)
                alias_to_paragraph[alias] = real; context[alias] = candidate
            indexed[key] = copied
        request = build_norm_review_request(model_id=model_id, run_id=run.run_id, section=section,
            settings=settings, quote_echo=False, payload={
                "observations": [{"title": item["title"], "description": item["description"],
                    "source_ids": item["source_ids"], "input_id": key,
                    "norm_candidate_ids": [c["paragraph_id"] for c in item["norm_candidates"]]}
                    for key, item in indexed.items()], "norm_context": list(context.values()),
                "source_sha256": state["source_sha256"], "candidate_identity_policy": "exact-fragment-alias-v1"})
        from .flow_norm_context import attach_flow_norm_context
        request, context_receipt = attach_flow_norm_context(session, request, originals=originals,
            indexed=indexed, snapshot_id=snapshot_id, checkpoint=checkpoint)
        state.setdefault("normative_context_receipts", {})[str(number)] = context_receipt
        def save_accepted(accepted):
            for result in accepted:
                assessment = deepcopy(result.get("norm_assessment"))
                if assessment:
                    for citation in assessment.get("citations", []):
                        citation["paragraph_id"] = alias_to_paragraph[citation["paragraph_id"]]
                target = originals[result["input_ids"][0]]
                target.update(norm_assessment=assessment, norm_review_status="reviewed", norm_review_reason=None)
            if accepted:
                phase("norm_verification", "running")
        _review_norms_per_record(state=state, request=request, call=call,
            identity=f"norm_verification:{number}", indexed=indexed, flow=True, on_accepted=save_accepted)
        for key, copied in indexed.items():
            target = originals[key]
            for field in ("norm_review_status", "norm_review_reason"):
                target[field] = copied.get(field)
            assessment = deepcopy(copied.get("norm_assessment"))
            if assessment:
                for citation in assessment.get("citations", []):
                    citation["paragraph_id"] = alias_to_paragraph[citation["paragraph_id"]]
                target["norm_assessment"] = assessment
            complete_context = target["normative_context"]["complete"]
            if not complete_context:
                target["norm_review_reason"] = "norm_paragraph_context_incomplete"
            target["finding_norm_status"] = ("partially_verified" if complete_context and assessment
                and assessment.get("relation") == "supports" else "not_verified")
        phase("norm_verification", "running")
    excluded = sum(item.get("norm_status") == "not_applicable" for item in items)
    valid = sum(item.get("norm_status") == "not_found" or (item.get("norm_review_status") == "reviewed"
        and item.get("normative_context", {}).get("complete") is True) for item in items)
    pending = len(items)-excluded-valid
    procedure = next(p for p in state["procedures"] if p["id"] == "norm_verification")
    procedure["input_accounting"] = {"expected": len(items), "valid": valid, "pending": pending,
        "refused": 0, "excluded": excluded, "exclusion_reason": "no_normative_question"}
    phase("norm_verification", "partial" if pending else "completed",
        "norm_inputs_unresolved" if pending else "no_normative_question" if excluded == len(items) else None)


def _bounds_lifted(policy):
    """Whether the frozen policy belongs to a ``relaxed_limits`` run (`REVIEW-FIX-BOUNDS-1102`).

    Preflight stamps ``unbounded_stats`` on the policy of such a run and of no other; the
    section-run bounds (1000 sources, 63 windows, 500 text pages, 900 000 request bytes) hold
    for every other run.
    """
    return policy.get("unbounded_stats") is True


#: The body size the section builders allow a norm request (`analysis/extended/workflow.py`
#: MAX_V3_REQUEST_BYTES; a ``relaxed_limits`` run lifts it). The norm paragraph context is attached
#: after that check, so the final body is measured again. A unit test pins the figure to the builders'.
_NORM_REQUEST_BODY_BYTES = 900_000


def _norm_request_within_bounds(request, *, policy):
    if not _bounds_lifted(policy) and len(extended_canonical(request.body).encode("utf-8")) > _NORM_REQUEST_BODY_BYTES:
        raise ValueError("norm_paragraph_context_request_window_too_large")


def _reply_refusal_code(error):
    """What a parser said about a refused reply, when that is a plain code; a decoder message is not kept."""
    code = str(error)
    return code if code.isidentifier() and code.islower() else "reply_unreadable"


def _source_sized(policy):
    return policy.get("completion_policy") == "source-complete-v1" or policy.get("source_sized_calls") is True


def _received_reply(*, state, request, response, parse, call, identity, policy, expected_inputs=None, on_accepted=None):
    """Keep valid records and repair a received semantic refusal under fresh consent.

    The second call has its own durable identity. Transport failures and ambiguous
    provider effects propagate; this helper never retries an unknown outcome.
    """
    request = getattr(call, "prepared_requests", {}).get(identity, request)
    rejected = []
    try:
        accepted = parse(response.output_text, rejected=rejected)
    except ValueError as error:
        accepted = []
        rejected = [{"reason": _reply_refusal_code(error), "reply_ordinal": None}]
    if response.truncated:
        rejected.append({"reason": "extended_response_truncated", "reply_ordinal": None})
    def input_key(item):
        ids = item.get("input_ids", [])
        return item.get("input_id") or (ids[0] if len(ids) == 1 else extended_digest(item))
    if expected_inputs is not None:
        valid = {input_key(item) for item in accepted}
        rejected.extend({"reason": "review_input_missing", "input_id": key}
            for key in sorted(expected_inputs - valid))
    if on_accepted is not None:
        on_accepted(accepted)
    if not rejected:
        return accepted, False
    receipt = {"phase_key": identity, "request_sha256": request.request_sha256,
        "response_sha256": response.response_sha256, "rejected_records": deepcopy(rejected),
        "accepted_record_count": len(accepted), "status": "unresolved"}
    state.setdefault("reply_refusals", []).append(receipt)
    if expected_inputs is not None and expected_inputs <= {input_key(item) for item in accepted}:
        receipt["status"] = "all_inputs_answered_extra_records_refused"
        return accepted, False
    if policy.get("semantic_repair_attempts") != 1:
        return accepted, True
    from auditmanager.analysis.public import build_semantic_repair_request
    if expected_inputs is not None:
        from auditmanager.analysis.public import flow_repair_helper
        repaired_request = flow_repair_helper("build_flow_repair_request", request, rejected=rejected,
            accepted_records=accepted, reply_sha256=response.response_sha256,
            procedure=identity.split(":", 1)[0], missing_input_ids=expected_inputs-{input_key(item) for item in accepted})
    else:
        repaired_request = build_semantic_repair_request(request, rejected=rejected,
            accepted_records=accepted, reply_sha256=response.response_sha256,
            procedure=identity.split(":", 1)[0])
    receipt.update(status="repairing", repair_request_sha256=repaired_request.request_sha256)
    repaired_response = call(repaired_request, identity + ":repair:1")
    repair_rejected = []
    try:
        repaired = parse(repaired_response.output_text, rejected=repair_rejected)
    except ValueError as error:
        repaired = []
        repair_rejected = [{"reason": _reply_refusal_code(error), "reply_ordinal": None}]
    if repaired_response.truncated:
        repair_rejected.append({"reason": "extended_response_truncated", "reply_ordinal": None})
    # A valid original candidate must survive a model's later omission. Reviews
    # are keyed by their immutable input; an updated valid review supersedes it.
    merged = {}
    for item in [*accepted, *repaired]:
        key = input_key(item) if expected_inputs is not None else item.get("input_id") or extended_digest(item)
        if expected_inputs is None:
            merged[key] = item
        else:
            merged.setdefault(key, item)
    if expected_inputs is not None:
        repair_rejected.extend({"reason": "review_input_missing", "input_id": key}
            for key in sorted(expected_inputs - set(merged)))
    receipt.update(status="unresolved" if repair_rejected else "resolved",
        repair_response_sha256=repaired_response.response_sha256,
        repair_rejected_records=deepcopy(repair_rejected),
        accepted_record_count=len(merged))
    return list(merged.values()), bool(repair_rejected)


def _run_workflow_v2(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
        publish, progress, checkpoint, observations_document, snapshot_id, profile_sha256, bind_native=None,
        window_context=None, full_document=False, policy=None):
    from auditmanager.analysis.public import (read_artifact, prepare_native_page_sources,
        build_comprehensive_request, deterministic_extended_merge,
        build_norm_review_request, parse_norm_review)
    v3=window_context is not None
    batched=v3 and window_context["policy"].get("coverage_version")=="batched-v1"
    state = planned_workflow_result(policy=policy if not v3 else window_context["policy"])
    if v3 and _source_sized(window_context["policy"]):
        state.update(source_sized_calls=True, completion_policy=window_context["policy"].get("completion_policy"))
    # The separately accepted global budget belongs only to the parent Run;
    # a local 16-source window must never advertise or acquire its own copy.
    state.pop("global_cross_window", None)
    if v3 and "project_parameter_context_policy" in window_context["policy"]:
        state.pop("project_parameters", None)
    if v3:
        state["window_id"]=window_context["window_id"]
        state["primary_text_status"]=window_context.get("primary_text_status","pending")
        # The planned (parent) result carries the aggregated list; a window keeps its receipts by batch
        # index (the batch writer and the parent's aggregate both read a mapping). The list made every
        # v3 run with a norm paragraph context policy raise AttributeError at its first window save.
        if isinstance(state.get("normative_context_receipts"), list):
            state["normative_context_receipts"]={}
    current = None
    used_batches={}
    # The run's leg breaker (D-662): the parent of a v3 window owns it and lends it to every window; a run without windows keeps its own.
    breaker=window_context.get("block_breaker") if v3 else None
    if breaker is None:
        breaker=_new_breaker()
    def save(status):
        public = {k:v for k,v in state.items() if k not in {"text_items","context_sections"}}
        public["sources"] = [{k:v for k,v in s.items() if k != "context"} for s in state["sources"]]
        progress(status, public)
    def phase(identity, status, reason=None):
        nonlocal current
        current = identity
        procedure = next(p for p in state["procedures"] if p["id"] == identity)
        procedure.update(status=status)
        procedure.pop("reason", None)
        if reason: procedure["reason"] = reason
        save("running")
    def call(request, identity):
        base_identity, repair_separator, repair_attempt = identity.partition(":repair:")
        repairing = bool(repair_separator)
        flow_approved = not v3 and isinstance(policy, dict) and "flow_repair_policy" in policy
        if repairing and (repair_attempt != "1" or not (flow_approved
                or v3 and window_context["policy"].get("semantic_repair_attempts") == 1)):
            raise _refuse("semantic_repair_not_approved")
        receipt=None
        parameter_context_receipt=None
        parameter_review_receipt=None
        # Only the batched builders take ``relaxed_limits``; a decorator holds the ceiling of the builder
        # that made the request.
        if (v3 and not repairing and identity.startswith("blocks:")
                and "project_parameter_context_policy" in window_context["policy"]):
            from auditmanager.analysis.public import attach_project_parameter_context
            request, provided_context = attach_project_parameter_context(request,
                parameters=window_context["project_parameters"],
                accepted=window_context["policy"]["project_parameter_context_policy"],
                parameters_policy=window_context["policy"]["project_parameters_policy"],
                relaxed_limits=batched and _bounds_lifted(window_context["policy"]))
            parameter_context_receipt = {**provided_context, "request_sha256": request.request_sha256,
                "request_prepared": True, "response_received": False}
            state.setdefault("project_parameter_context_receipts", {})[identity] = parameter_context_receipt
            save("running")
        review_kind = base_identity.split(":", 1)[0]
        review_context = window_context["policy"].get("project_parameter_review_context_policy") if v3 else None
        if not repairing and review_context is not None and review_kind in review_context["scopes"]:
            from auditmanager.analysis.public import attach_project_parameter_review_context
            request, parameter_review_receipt = attach_project_parameter_review_context(request,
                parameters=window_context["project_parameters"], accepted=review_context,
                parameters_policy=window_context["policy"]["project_parameters_policy"], procedure=review_kind,
                relaxed_limits=batched and _bounds_lifted(window_context["policy"]))
            parameter_review_receipt.update(request_sha256=request.request_sha256,
                request_prepared=True, response_received=False)
            state.setdefault("project_parameter_review_context_receipts", {})[identity] = parameter_review_receipt
            save("running")
        if not hasattr(call, "prepared_requests"):
            call.prepared_requests = {}
        call.prepared_requests[identity] = request
        cell_receipt=None
        if batched:
            raw_kind, raw_rest=base_identity.split(":",1)
            # ``blocks:3:leg1``: a call of the blocks ensemble names its cell after the batch. The batch is the unit of coverage and of the
            # approved call limit; each of its calls is a unit of its own (`HOSTS-ENSEMBLE-01`).
            raw_index, _, role=raw_rest.partition(":")
            if role and (raw_kind != "blocks" or role not in ENSEMBLE_ROLES):
                raise _refuse("extended_phase_identity_invalid")
            kind={"blocks":"block_analysis"}.get(raw_kind,raw_kind)
            index=int(raw_index.removeprefix("b"))
            batch_identity=f"{raw_kind}:{raw_index}"
            keys=used_batches.setdefault(kind,set())
            if (batch_identity not in keys and not window_context["policy"].get("unbounded_stats")
                    and not _source_sized(window_context["policy"])
                    and len(keys)>=window_context["policy"]["phase_call_limits"][kind]):
                raise _refuse("approved_phase_call_limit")
            keys.add(batch_identity)
            key=f'{window_context["window_id"]}:{kind}:b{index:03d}'
            receipt=next((row for row in state.setdefault("batches",[]) if row["batch_key"]==key),None)
            if receipt is None:
                payload=json.loads(request.body["messages"][0]["content"])
                source_rows=payload.get("sources",[])
                receipt={"batch_key":key,"window_id":window_context["window_id"],"procedure":kind,
                    "index":index,"input_ids":[],"source_ids":[row["source_id"] for row in source_rows],
                    "page_numbers":sorted({row["page_number"] for row in source_rows}),
                    "input_count":len(source_rows),"input_characters":0}
                state["batches"].append(receipt)
                state.setdefault("phase_coverage",{}).setdefault(kind,{"planned":0,"completed":0,
                    "remaining":0,"limit":window_context["policy"]["phase_call_limits"][kind],
                    "processed_items":0,"total_items":0,"characters_processed":0,"characters_total":0})
                coverage=state["phase_coverage"][kind]
                coverage["planned"]+=1;coverage["remaining"]+=1;coverage["total_items"]+=len(source_rows)
            if role and not repairing:
                cell_receipt=receipt.setdefault("cells",{}).setdefault(role,{})
                for stale in ("error_code","dispatch_class"):cell_receipt.pop(stale,None)
                cell_receipt.update(cell=f"blocks:{role}",status="running",request_sha256=request.request_sha256)
            if repairing:
                parent_receipt = receipt
                receipt = {"attempt": 1, "status": "running", **({"cell": f"blocks:{role}"} if role else {})}
                parent_receipt.setdefault("repair_attempts", []).append(receipt)
            receipt.pop("error_code",None)  # a retried call has not failed yet; an earlier failure of the same unit is not its state
            receipt.update(status="running",request_sha256=request.request_sha256)
            save("running")
        dispatch_receipt = None
        if flow_approved:
            if not hasattr(call, "dispatch_receipts"):
                call.dispatch_receipts = {}
            dispatch_receipt = call.dispatch_receipts.setdefault(identity, {})
        try:
            response, replayed = _call(session,run_id=run.run_id,authority=authority,jobs=jobs,journal=journal,
                binding=_phase_binding(binding, identity),request=request,phase=("v3:"+window_context["window_id"]+":" if v3 else "v2:")+identity,
                source_sha256=state["source_sha256"],meter=meter,store=store,publish=publish,checkpoint=checkpoint,
                global_unknown_fence=v3 or flow_approved,
                **({"dispatch_receipt": dispatch_receipt} if flow_approved else {}))
        except DomainError as error:
            for failed_receipt in (receipt, cell_receipt, parameter_context_receipt, parameter_review_receipt):
                if failed_receipt is not None:
                    failed_receipt.update(error_code=error.code.value)
                    dependency=error.detail_fields.get("dependency")
                    if dependency is not None:
                        failed_receipt["dependency"]=dependency
            raise
        if parameter_context_receipt is not None:
            parameter_context_receipt.update(response_received=True, replayed=replayed,
                response_sha256=response.response_sha256)
        if parameter_review_receipt is not None:
            parameter_review_receipt.update(response_received=True, replayed=replayed,
                response_sha256=response.response_sha256)
        if cell_receipt is not None:
            cell_receipt.update(response_received=True,replayed=replayed,response_sha256=response.response_sha256)
        if receipt is not None:
            receipt.update(response_received=True,replayed=replayed,response_sha256=response.response_sha256)
            if repairing:
                receipt["status"] = "received"
            counts=state.setdefault("phase_call_counts",{}).setdefault(kind,{"completed_calls":0,"replayed":0})
            counts["replayed" if replayed else "completed_calls"]+=1
        if response.truncated and not (flow_approved
                or v3 and window_context["policy"].get("semantic_repair_attempts") == 1):
            raise _refuse("extended_response_truncated")
        return response
    save("running")
    try:
        # A marker this code does not know is a failed review, never a v2 run without the original's critic.
        original_review=not v3 and _original_review_enabled(policy,strict=True)
        quality = not v3 and isinstance(policy, dict) and "quality_policy" in policy
        flow_policy = policy.get("flow_repair_policy") if not v3 and isinstance(policy, dict) else None
        if flow_policy is not None:
            from auditmanager.analysis.public import validate_flow_repair_policy
            validate_flow_repair_policy(flow_policy)
            if not quality or policy.get("semantic_repair_attempts") != 1:
                raise _refuse("flow_repair_quality_policy_missing")
        proposals = policy.get("finding_proposals") if not v3 and isinstance(policy, dict) else None
        if proposals is not None:
            from auditmanager.analysis.public import validate_finding_proposal_policy
            validate_finding_proposal_policy(proposals)
            if not quality:
                raise _refuse("finding_proposals_quality_policy_missing")
        related_index = None
        if quality:
            from auditmanager.analysis.public import validate_v2_quality_policy
            validate_v2_quality_policy(policy["quality_policy"])
            if not original_review:
                raise _refuse("v2_quality_review_policy_missing")
        if v3:
            section=window_context["policy"]["section_code"]
        else:
            version = DocumentRepository().get_version(session,run.version_uid)
            section = version.classification.section_code if version.classification else "unknown"
        state["section"] = section
        checkpoint("extended_v2_inputs")
        data = {}
        for role in ("prepared.text_layer","context.document_graph","geometry.portal_blocks","geometry.page_crops","prepared.recognised_text"):
            ref = outputs.refs.get(role)
            if ref is not None:
                data[role], _ = read_artifact(store,parse_blob_id(ref.blob_id),expected_role=role)
        if "prepared.text_layer" not in data or "context.document_graph" not in data:
            raise _refuse("extended_prepared_inputs_unavailable")
        native = None
        portal = data.get("geometry.portal_blocks")
        manifest = data.get("geometry.page_crops")
        text_only_portal = False
        if portal is not None and manifest is not None:
            # Validate the saved portal cohort before considering native rendering.
            # Native pages supplement genuine TEXT-only input; they never conceal an
            # IMAGE refusal or a known page/region geometry mismatch.
            plan_extended_inputs(version_uid=run.version_uid,section=section,portal=portal,manifest=manifest,
                text_layer=data["prepared.text_layer"],graph=data["context.document_graph"],
                observations=None,plan_version="extended-review-v2")
            text_only_portal = (not manifest.get("crops") and bool(portal.get("blocks"))
                and all(block.get("block_type") == "text" and block.get("geometry") == "ok"
                    for block in portal["blocks"])
                and all(page.get("geometry") == "ok" for page in portal.get("pages", [])))
        if portal is None or text_only_portal:
            source = outputs.refs.get("source.document")
            if source is None: raise _refuse("extended_native_source_unavailable")
            saved_visual=window_context.get("saved_visual") if v3 else None
            if v3 and window_context["offset"] >= window_context["policy"]["max_blocks"]:
                native={"sources":[],"artifacts":(),"warnings":[],
                    "coverage":{"blocks_total":window_context["page_count"],"skipped":[]},
                    "source_sha256":extended_digest({"source_sha256":source.sha256,"text_only_window":window_context["offset"]}),
                    "source_window":{"slots":0}}
            elif saved_visual is not None:
                saved_sources=[item for item in saved_visual.get("sources",[]) if item.get("kind")=="image"]
                if any(item.get("source_type")!="native_page" or item.get("version_uid")!=run.version_uid
                        or item.get("source_sha256")!=source.sha256 for item in saved_sources):
                    raise _refuse("extended_saved_native_source_changed")
                native={"sources":saved_sources,"artifacts":(),"warnings":["native_pdf_page_render_no_ocr"],
                    "coverage":{"blocks_total":saved_visual["source_window_total"],
                        "skipped":saved_visual["coverage"].get("skipped",[])},
                    "source_sha256":extended_digest({"sources":saved_sources,"source_sha256":source.sha256}),
                    "source_window":{"slots":saved_visual["coverage"]["blocks_total"]}}
            else:
                native = prepare_native_page_sources(version_uid=run.version_uid,source_ref=source,
                    blob_store=store,max_pages=16 if v3 else version.page_count if full_document else 16,checkpoint=checkpoint,
                    **({"window_offset":window_context["offset"],"max_sources":window_context["policy"]["max_blocks"],
                        "relaxed_limits":_bounds_lifted(window_context["policy"])} if v3 else {}))
            if text_only_portal:
                native["warnings"].append("portal_text_only_native_page_visuals")
            if bind_native is not None: bind_native(native["artifacts"])
        planned = plan_extended_inputs(version_uid=run.version_uid,section=section,
            portal=data.get("geometry.portal_blocks",{}),manifest=data.get("geometry.page_crops",{}),
            text_layer=data["prepared.text_layer"],graph=data["context.document_graph"],
            observations=observations_document,recognised=data.get("prepared.recognised_text"),
            native_sources=native,plan_version="extended-review-v3" if v3 else "extended-review-v2",full_document=full_document,
            **({"coverage_version":"batched-v1"} if batched else {}),
            **({"source_offset":window_context["offset"],"max_sources":window_context["policy"]["max_blocks"],
                "relaxed_limits":_bounds_lifted(window_context["policy"])} if v3 else {}))
        if v3:
            window_total=(native["source_window"]["slots"] if native is not None else len([s for s in planned["sources"] if s["kind"]=="image"]))
            planned["source_window_total"]=planned["coverage"]["blocks_total"]
            planned["coverage"]={**planned["coverage"],"blocks_total":window_total,"blocks_remaining":window_total,
                "skipped":native["coverage"]["skipped"] if native is not None else []}
        procedures = state["procedures"]
        state.update(planned,workflow_version="extended-review-v3" if v3 else "extended-review-v2",procedures=procedures,
            ocr_status="not_performed",model_id=binding.config.model_id,provider_mode=binding.adapter.provider_mode.value)
        state["source_sha256"] = extended_digest({"source":state["source_sha256"],"workflow_version":"extended-review-v2",
            "profile_sha256":profile_sha256,"norms_snapshot_id":snapshot_id,"run_input_digest":getattr(run,"frozen_input_digest",None)})
        if quality:
            state["source_sha256"] = extended_digest({"source": state["source_sha256"], "quality_policy": policy["quality_policy"]})
        if proposals is not None:
            state["source_sha256"] = extended_digest({"source": state["source_sha256"], "finding_proposals": proposals})
            primary = observations_document.get("observations", []) if isinstance(observations_document, dict) else []
            for item in state["text_items"]:
                refs = item["source_ids"]
                if len(refs) == 1 and re.fullmatch(r"text:[0-9]+", refs[0]):
                    index = int(refs[0].split(":")[1])
                    if index < len(primary) and isinstance(primary[index].get("recommendation_text"), str):
                        item["recommendation_text"] = primary[index]["recommendation_text"]
                    if flow_policy is not None and index < len(primary):
                        item["original_primary_observation"] = deepcopy(primary[index])
        if flow_policy is not None:
            state["source_sha256"] = extended_digest({"source": state["source_sha256"], "flow_repair_policy": flow_policy})
        if v3: state["source_sha256"]=window_context["global_sha256"]
        if batched:
            state["observations"]=finalize_extended_items(state["text_items"],state["sources"])
        pages = data["prepared.text_layer"].get("pages",[])
        by_page = {p["page_number"]:str(p.get("text","")) for p in pages}
        if quality:
            from auditmanager.analysis.public import build_review_input_passport, build_related_review_index
            pdf_sha = getattr(version, "sha256", None)
            source_ref = outputs.refs.get("source.document")
            bound_sha = getattr(source_ref, "sha256", None)
            if pdf_sha is not None and bound_sha is not None and pdf_sha != bound_sha:
                raise _refuse("input_passport_pdf_binding_invalid")
            state["input_passport"] = build_review_input_passport(version_uid=run.version_uid,
                pdf_sha256=pdf_sha or bound_sha, page_count=version.page_count, pages=pages,
                sources=state["sources"], skipped=state["coverage"]["skipped"])
            if flow_policy is not None:
                passport = state["input_passport"]
                for page in passport["pages"]:
                    number = page["page_number"]
                    has_text = bool(by_page.get(number, "").strip())
                    page.update(text_available=has_text, text_state="present" if has_text
                        else "visual_required" if page["crop_ids"] else "empty")
                passport["unrepresented_pages"] = [page["page_number"] for page in passport["pages"]
                    if not page["text_available"] and not page["crop_ids"]]
                passport["source_coverage_complete"] = not passport["unrepresented_pages"]
            related_index = build_related_review_index(pages, version_uid=run.version_uid)
        recognised_by_page={}
        recognised_artifact_sha=None
        if v3 and data.get("prepared.recognised_text") is not None:
            recognised_artifact_sha=outputs.refs["prepared.recognised_text"].sha256
            for entry in data["prepared.recognised_text"].get("entries",[]):
                if entry.get("kind")=="recognised_text" and isinstance(entry.get("text"),str):
                    recognised_by_page.setdefault(entry["page_number"],[]).append(entry["text"])
        # Native visual crops use the same genuine page context as portal crops.
        for source in state["sources"]:
            if source.get("source_type") == "native_page":
                source["context"] = [{"page_number":n,"text":by_page[n][:6000],
                    "recognised_context":"\n".join(recognised_by_page.get(n,[]))[:4000],
                    "context_truncated":len(by_page[n])>6000 or len("\n".join(recognised_by_page.get(n,[])))>4000} for n in (source["page_number"]-1,source["page_number"],source["page_number"]+1) if n in by_page]
        images = [s for s in state["sources"] if s["kind"] == "image"]
        block_items = []
        if images:
            phase("block_analysis","running")
            block_roles=_block_roles(run)
            ensemble="judge" in block_roles
            partial_reason=None
            any_refused=False
            for start in range(0,len(images),8):
                batch=images[start:start+8];crops=[]
                for source in batch:
                    raw=store.read(parse_blob_id(source["blob_id"]),verify=True)
                    if len(raw)!=source["size_bytes"] or hashlib.sha256(raw).hexdigest()!=source["crop_sha256"]:
                        raise _refuse("extended_crop_digest_invalid")
                    if quality:
                        from auditmanager.analysis.public import verify_review_passport_crop
                        verify_review_passport_crop(state["input_passport"], source, raw)
                    crops.append(CropImage(source["source_id"],raw))
                payload,cut=extended_block_payload(section=section,batch=batch,sections=state["context_sections"],coverage=state["coverage"])
                if cut: state["warnings"].append("page_context_truncated")
                builder=build_extended_request
                # `BLOCK-SOURCES-V2-01`: a v2 block request names its batch's sources (v3 always did); `extra` reaches the single call
                # and every leg of the ensemble. The judge request carries its own closed list of sources.
                extra={"bind_sources":True}
                if v3:
                    from auditmanager.analysis.public import build_extended_request_v3
                    builder=build_extended_request_v3;extra={"window_id":window_context["window_id"]}
                if ensemble:
                    # Legs, then the judge; each call is a unit of its own (`HOSTS-ENSEMBLE-01`).
                    parsed, batch_reason = _ensemble_block_batch(run=run, binding=binding, state=state, call=call,
                        roles=block_roles, section=section, index=start//8, batch=batch, payload=payload, crops=crops,
                        builder=builder, extra=extra, window_context=window_context,
                        policy=window_context["policy"] if v3 else {}, checkpoint=checkpoint, breaker=breaker)
                    refused = batch_reason is not None
                else:
                    request=attach_images(builder(**_kw(binding,"blocks"),run_id=run.run_id,
                        phase="blocks",section=section,payload=payload,**extra),crops)
                    response=call(request,"blocks:"+str(start//8))
                    parsed, refused = _received_reply(state=state, request=request, response=response,
                        parse=lambda text, **kwargs: parse_extended_reply(text,
                            allowed_sources={s["source_id"] for s in batch}, **kwargs),
                        call=call, identity="blocks:"+str(start//8),
                        policy=window_context["policy"] if v3 else policy if flow_policy is not None else {})
                    batch_reason="block_analysis_reply_refused" if refused else None
                partial_reason=partial_reason or (batch_reason if ensemble or not v3 else None)
                any_refused|=refused
                block_items.extend(parsed)
                if flow_policy is not None:
                    state["block_candidates"] = deepcopy(block_items)
                if batched:
                    _coverage_complete(state,kind="block_analysis",index=start//8,
                        partial=refused, reason=batch_reason)
                # A batch the model read counts as read even when the parser refused some of its records (`BLOCK-SOURCES-V2-01`): v2 only,
                # the refusal itself stays in the receipts and in the stage's status below. A reply refused whole counts for nothing.
                if not refused or (parsed and not v3):
                    state["coverage"]["blocks_processed"]+=len(batch)
                state["coverage"]["blocks_remaining"]=state["coverage"]["blocks_total"]-state["coverage"]["blocks_processed"]
                state["observations"]=finalize_extended_items([*state["text_items"],*block_items],state["sources"])
                save("running")
            partial_rows=[row for row in state.get("batches", [])
                if row["procedure"] == "block_analysis" and row.get("status") == "partial"]
            # v2: a refusal in any batch keeps the stage partial even when every batch counted as read.
            degraded=bool(state["coverage"]["blocks_remaining"] or (any_refused and not v3))
            phase("block_analysis","partial" if degraded else "completed",
                (next((row["reason"] for row in partial_rows if row.get("reason")), None)
                    or ("block_analysis_reply_refused" if partial_rows else partial_reason))
                if degraded else None)
        else:
            legitimate_text_window=(v3 and not window_context.get("known_visual_refusals")
                and not (native or {}).get("coverage",{}).get("skipped"))
            phase("block_analysis","completed" if legitimate_text_window else "unavailable",
                "no_visual_sources_in_window" if legitimate_text_window else "no_image_blocks_available")
        if v3:
            state["visual_phase_complete"]=True
        if v3 and window_context.get("visual_only"):
            state["primary_text_status"]="pending"
            save("running")
            return state
        contexts=[]
        if full_document:
            phase("comprehensive_analysis","running")
            comprehensive = _full_comprehensive_review(run=run, **_kw(binding,"cross_check"),
                section=section, state=state, pages=pages, block_items=block_items, call=call,
                **({"flow_policy": flow_policy, "phase": phase,
                    "pair_call_limit": policy["semantic_pair_call_limit"]} if flow_policy is not None else {}),
                **({"related_index": related_index} if quality else {}))
            if "page_context_truncated" in state["warnings"]:
                state["warnings"] = [warning for warning in state["warnings"] if warning != "page_context_truncated"]
                state["warnings"].append("visual_context_bounded_full_text_reviewed")
            complete = state.get("comprehensive_execution_complete", True)
            phase("comprehensive_analysis", "completed" if complete else "partial",
                None if complete else "comprehensive_inputs_unresolved")
        else:
            # Legacy v2 keeps its original request; v3 uses the current source/page window.
            contexts=[]
            context_pages=pages[:16]
            if v3:
                numbers={source["page_number"]+delta for source in images for delta in (-1,0,1)}
                numbers.update(range(window_context["offset"]+1,min(window_context["offset"]+16,
                    window_context["policy"]["text_page_limit"])+1))
                context_pages=[page for page in pages if page["page_number"] in numbers]
                if not context_pages:
                    context_pages=pages[window_context["offset"]:window_context["offset"]+16]
            for page in context_pages:
                number=page["page_number"];value=str(page.get("text",""))
                source_id="native_text_"+extended_digest({"version_uid":run.version_uid,"page":number,"text":value})[:24]
                state["sources"].append({"source_id":source_id,"kind":"text","source_type":"native_text",
                    "page_number":number,"version_uid":run.version_uid,"quote":value[:2000],"text_sha256":hashlib.sha256(value.encode()).hexdigest()})
                contexts.append({"source_id":source_id,"page_number":number,"text":value})
                if v3 and recognised_by_page.get(number):
                    recognised="\n".join(recognised_by_page[number])
                    recognised_id="recognised_"+extended_digest({"version_uid":run.version_uid,"page":number,
                        "artifact_sha256":recognised_artifact_sha,"text":recognised})[:24]
                    state["sources"].append({"source_id":recognised_id,"kind":"text","source_type":"recognised_text",
                        "quote_source":"recognised","page_number":number,"version_uid":run.version_uid,
                        "quote":recognised[:2000],"artifact_sha256":recognised_artifact_sha,
                        "text_sha256":hashlib.sha256(recognised.encode()).hexdigest()})
                    contexts.append({"source_id":recognised_id,"page_number":number,"text":"",
                        "recognised_context":recognised,"source_type":"recognised_text","quote_source":"recognised"})
            phase("comprehensive_analysis","running")
            if batched:
                state["context_page_numbers"]=[page["page_number"] for page in context_pages]
                comprehensive=_comprehensive_batched_v3(run=run,binding=binding,state=state,contexts=contexts,
                    block_items=block_items,phase=phase,call=call,window_context=window_context)
            else:
                builder=build_comprehensive_request
                extra={}
                if v3:
                    from auditmanager.analysis.public import build_comprehensive_request_v3
                    builder=build_comprehensive_request_v3;extra={"window_id":window_context["window_id"]}
                request=builder(**_kw(binding,"cross_check"),run_id=run.run_id,section=section,
                    **extra,payload={"native_context":contexts,"visual_observations":block_items,
                        "text_observations":([{k:item[k] for k in ("title","description","source_ids","norm_queries")}
                            for item in state["text_items"]] if v3 else state["text_items"]),
                        "sources":[{k:v for k,v in s.items() if k!="context"} for s in state["sources"]],
                        "source_sha256":state["source_sha256"],"coverage":state["coverage"]})
                context_payload=json.loads(request.body["messages"][0]["content"])
                context_cut = context_payload["context_coverage"]["truncated"]
                if v3:
                    state["context_page_numbers"]=[page["page_number"] for page in context_pages]
                    state["comprehensive_context_coverage"]=context_payload["context_coverage"]
                if context_cut: state["warnings"].append("page_context_truncated")
                if v3 and not images and not any(row.get("text","").strip() or row.get("recognised_context","").strip() for row in contexts):
                    comprehensive=[]
                    phase("comprehensive_analysis","unavailable","no_reliable_window_sources")
                else:
                    comprehensive=parse_extended_reply(call(request,"comprehensive").output_text,
                        allowed_sources={s["source_id"] for s in state["sources"]})
                    phase("comprehensive_analysis","partial" if (not v3 and len(pages)>16) or context_cut else "completed")
        phase("finding_merge","running")
        inputs = [*state["text_items"],*block_items,*comprehensive]
        items=inputs if quality else deterministic_extended_merge(inputs, full_document=full_document or batched)
        if quality:
            items = [dict(item, raw_occurrence=index) for index, item in enumerate(items)]
        state["observations"]=finalize_extended_items(items,state["sources"])
        if quality:
            state.update(_attach_consolidation(state, version_uid=run.version_uid))
        phase("finding_merge","completed")
        phase("norm_verification","running")
        if batched:
            _norm_batched_v3(session=session,run=run,binding=binding,state=state,snapshot_id=snapshot_id,
                phase=phase,call=call,checkpoint=checkpoint,window_context=window_context)
        elif full_document:
            _full_norm_verification(session=session, run=run, **_kw(binding,"norms"),
                section=section, state=state, snapshot_id=snapshot_id, call=call,
                phase=phase, checkpoint=checkpoint,
                **({"flow_policy": flow_policy} if flow_policy is not None else {}))
        else:
            window=state["observations"][:40]
            if v3:
                for item in window:
                    if len(item["source_ids"])>16:
                        item.update(norm_status="unavailable",norm_reason="norm_source_reference_window_exceeded")
                window=[item for item in window if len(item["source_ids"])<=16]
            for item in state["observations"][40:]:
                item.update(norm_status="unavailable",norm_reason="outside_norm_review_window")
            state["warnings"].extend(_norms(session,window,snapshot_id))
            registry={}
            for item in window:
                item["norm_candidates"]=[registry.setdefault(c["paragraph_id"],c) for c in item.get("norm_candidates",[])]
            bounded=[];remaining_chars=16_000
            for item in window:
                size=len(item["title"])+len(item["description"])+sum(len(c["quote"]) for c in item.get("norm_candidates",[]))
                if size>remaining_chars:
                    item.update(norm_status="unavailable",norm_reason="outside_norm_review_window")
                    continue
                bounded.append(item);remaining_chars-=size
            window=bounded
            registry={c["paragraph_id"]:c for item in window for c in item.get("norm_candidates",[])}
            if not registry and snapshot_id is not None and len(window)==len(state["observations"]) and not any(
                    _asked_norm_question(item) for item in window):
                phase("norm_verification","completed","no_normative_question")  # NORM-COVERAGE-01
            elif not registry:
                reason="corpus_unavailable" if snapshot_id is None else "candidate_context_unavailable"
                phase("norm_verification","unavailable",reason)
            else:
                indexed={"xni_"+extended_digest({"ordinal":i,"item":item})[:24]:item for i,item in enumerate(window)}
                builder=build_norm_review_request
                extra={"quote_echo":False}  # NORM-REPLY-PER-RECORD-01: v2 reads the reply per record; v3 below is unchanged
                if v3:
                    from auditmanager.analysis.public import build_norm_review_request_v3
                    builder=build_norm_review_request_v3;extra={"window_id":window_context["window_id"]}
                request=builder(**_kw(binding,"norms"),run_id=run.run_id,section=section,
                    **extra,payload={"observations":[{"title":item["title"],"description":item["description"],
                        "source_ids":item["source_ids"],"input_id":key,
                        "norm_candidate_ids":[c["paragraph_id"] for c in item.get("norm_candidates",[])]} for key,item in indexed.items()],
                        "norm_context":list(registry.values()),"source_sha256":state["source_sha256"]})
                if v3:
                    reviewed=parse_norm_review(call(request,"norm_verification").output_text,observations=indexed,
                        allowed_sources={s["source_id"] for s in state["sources"]})
                    # Parser requires exactly one assessment per original input; only annotations transfer.
                    for reviewed_item in reviewed:
                        target=indexed[reviewed_item["input_ids"][0]]
                        target["norm_assessment"]=reviewed_item["norm_assessment"]
                    phase("norm_verification","partial" if len(window)<len(state["observations"]) or any(
                        _asked_norm_question(item) and not item.get("norm_candidates") for item in window) else "completed")  # NORM-COVERAGE-01
                elif _review_norms_per_record(state=state,request=request,call=call,identity="norm_verification",indexed=indexed):
                    phase("norm_verification","partial",NORM_REPLY_REFUSED)
                else:
                    phase("norm_verification","partial" if len(window)<len(state["observations"]) or any(
                        _asked_norm_question(item) and not item.get("norm_candidates") for item in window) else "completed")  # NORM-COVERAGE-01
        if batched:
            _review_batched_v3(run=run,binding=binding,state=state,phase=phase,call=call,
                window_context=window_context,contexts=contexts,
                norm_images=_critic_norm_images(session,run,store,binding,window_context["policy"]))
        elif v3:
            _review_window_v3(session=session,run=run,binding=binding,state=state,phase=phase,call=call,
                window_id=window_context["window_id"],section=section,contexts=contexts,
                reference_section=_reference_section(binding,window_context["policy"]),
                norm_images=_critic_norm_images(session,run,store,binding,window_context["policy"]))
        elif original_review:
            substantive = None
            if quality:
                from .v2_quality import run_substantive_critic
                substantive = lambda: run_substantive_critic(state=state, run=run, **_kw(binding, "review"),
                    store=store, pages=by_page, related_index=related_index, call=call, phase=phase,
                    **({"flow_policy": flow_policy} if flow_policy is not None else {}),
                    **({"proposal_policy": proposals} if proposals is not None else {}))
            _review_original_v2(state=state,phase=phase,pages=by_page,substantive=substantive)
        if quality:
            state.update(_attach_consolidation(state, version_uid=run.version_uid))
        degraded=any(p["status"] in {"failed","partial","unavailable","skipped"}
            and p.get("reason") not in {"no_corrections_requested","no_observations"} for p in state["procedures"])
        save("partial" if degraded else "completed")
        return state
    except (DomainError,ValueError,TypeError,KeyError) as error:
        reason=(error.detail_fields.get("reason") or (error.code.value if v3 else None)) if isinstance(error,DomainError) else _reply_refusal_code(error)
        if isinstance(error,ValueError) and str(error).endswith("_window_too_large"):
            reason=str(error)  # a request over the size bound is not an invalid reply or source
        reason=str(reason or "extended_workflow_failed")
        for procedure in state["procedures"]:
            if procedure["status"]=="running": procedure.update(status="failed",reason=reason)
            elif procedure["status"]=="queued": procedure.update(status="skipped",reason="dependency_failed")
        state["warnings"].append(reason)
        for batch in state.get("batches",[]):
            if batch["status"]=="running":batch.update(status="failed",reason=reason)
            elif batch["status"]=="queued" and not batch.get("reason"):
                batch.update(status="unavailable",reason="dependency_failed")
        if not v3 and "flow_repair_policy" in state and state.get("observations"):
            # A failed later call does not revoke already parsed questions. The
            # failed procedure and provider uncertainty remain visible, while
            # the ordinary partial-result reader can publish the valid subset.
            state["execution_failure_reason"] = reason
            state.update(_attach_consolidation(state, version_uid=run.version_uid, include_saved_relationships=True))
            save("partial")
        else:
            save("failed")
        return state


def _review_window_v3(*, session, run, binding, state, phase, call, window_id, section, contexts, reference_section=False, norm_images=None):
    """Real critic/corrector calls annotate immutable candidates; neither decides for the expert.

    The critic's reply is read the way the batched path reads it (`CTX-CRITIC`): a record that does not satisfy the parser (a quote the sources
    do not hold, such as one taken from the reference section, included) costs that record, not the paid reply. The records that parsed are
    kept; the others are ``not_reviewed`` with ``finding_review_reply_refused`` and a receipt in ``state["reply_refusals"]``. There is no
    semantic repair here: this path is the legacy coverage's, whose consent never grants one (`call` refuses it)."""
    from auditmanager.analysis.public import (build_critic_request,parse_critic_reply,
        build_corrector_request,parse_corrector_reply)
    selected=[];remaining=16_000
    for item in state["observations"]:
        size=len(item["title"])+len(item["description"])+len(json.dumps(item.get("norm_assessment"),ensure_ascii=False))
        if len(selected)>=40 or size>remaining:
            item.update(review_status="not_reviewed",review_reason="outside_critic_window")
            continue
        selected.append(item);remaining-=size
    if not selected:
        if state["observations"]:
            phase("finding_review","partial","outside_critic_window")
            phase("finding_correction","unavailable","critic_inputs_unavailable")
        else:
            phase("finding_review","completed","no_observations")
            phase("finding_correction","completed","no_observations")
    else:
        indexed={"xri_"+extended_digest({"window_id":window_id,"ordinal":i,"observation":item})[:24]:item
            for i,item in enumerate(selected)}
        references={source for item in selected for source in item["source_ids"]}
        sources=[source for source in state["sources"] if source["source_id"] in references]
        context={"coverage":state["coverage"],"window_id":window_id,
            "source_sha256":state["source_sha256"],"ocr_status":"not_performed",
            "native_context":[row for row in contexts if row["source_id"] in references]}
        phase("finding_review","running")
        request=build_critic_request(**_kw(binding,"review"),run_id=run.run_id,section=section,
            observations=indexed,sources=sources,window_id=window_id,context=context,reference_section=reference_section)
        imaged=frozenset()
        if norm_images is not None:  # `M7-NORM-PNG`: the task is created with the pages of its own norm paragraphs
            request,imaged=norm_images.attach(request,state=state,identity="critic")
        critic_payload=json.loads(request.body["messages"][0]["content"])
        critic_cut=any(critic_payload.get(key,{}).get("truncated",False)
            for key in ("context_coverage","norm_context_coverage"))
        response=call(request,"critic")
        reviews,refused=_received_reply(state=state,request=request,response=response,
            parse=lambda text,**kwargs:parse_critic_reply(text,observations=indexed,sources=sources,
                allowed_sources=references,context=context,**kwargs),
            call=call,identity="critic",policy={})
        state["reviews"]=reviews
        state["critiques"]=reviews
        for review in reviews:
            indexed[review["input_id"]].update(critic=review,review_status="reviewed",
                context_kinds=_critic_context_kinds(indexed[review["input_id"]],critic_payload,imaged))
        if refused:
            # `_received_reply` keeps the records that parsed and returns the refusal: an item the reply did not carry was not left out of
            # the window, its answer was refused. The receipt in `state["reply_refusals"]` holds the parser's code for each record.
            for item in indexed.values():
                if item.get("review_status")!="reviewed":
                    item.update(review_status="not_reviewed",review_reason="finding_review_reply_refused")
        phase("finding_review","partial" if len(selected)<len(state["observations"]) or critic_cut or refused else "completed",
            "finding_review_reply_refused" if refused else "context_window_truncated" if critic_cut else None)
        # Only the records the critic answered go to the corrector: its partition has to cover exactly the inputs it is given.
        reviewed={key:item for key,item in indexed.items() if item.get("review_status")=="reviewed"}
        request=build_corrector_request(**_kw(binding,"correction"),run_id=run.run_id,section=section,
            observations=reviewed,critiques=reviews,sources=sources,window_id=window_id,context=context) if reviews else None
        if not reviews:
            phase("finding_correction","unavailable","critic_inputs_unavailable")
            state["corrections"]=[]
        elif request is None:
            phase("finding_correction","completed","no_corrections_requested")
            state["corrections"]=[]
        else:
            phase("finding_correction","running")
            correction_payload=json.loads(request.body["messages"][0]["content"])
            correction_cut=any(correction_payload.get(key,{}).get("truncated",False)
                for key in ("context_coverage","norm_context_coverage"))
            corrections=parse_corrector_reply(call(request,"corrector").output_text,observations=reviewed,
                critiques=reviews,sources=sources,allowed_sources=references,context=context)
            state["corrections"]=corrections
            for correction in corrections:
                indexed[correction["input_id"]]["correction"]=correction
            phase("finding_correction","partial" if correction_cut or any(c["action"]=="needs_context" for c in corrections) else "completed",
                "context_window_truncated" if correction_cut else None)
    phase("report_generation","running")
    state["report"]=_section_report_v3(state,window_id=window_id)
    phase("report_generation","completed")


def _section_report_v3(state, *, window_id=None):
    """Deterministic report over saved observations and actual coverage, without another call."""
    coverage=state.get("coverage",{})
    lines=[f"# Анализ раздела {state.get('section','unknown')}",
        "Предварительные наблюдения. Решение по каждому принимает эксперт.",
        f"Охват: обработано {coverage.get('blocks_processed',0)} из {coverage.get('blocks_total',0)}; "
        f"не исследовано {coverage.get('blocks_remaining',0)}.",
        "OCR не выполнялся. Отсутствие native текста не считается его распознаванием.",
        "Распознанный текст портала, если предоставлен, помечен отдельно от native цитат."]
    if state.get("coverage_version")=="batched-v1":
        text=state.get("text_coverage",state.get("comprehensive_context_coverage",{}))
        lines.append("Известный текстовый план: символов обработано "+str(text.get("characters_processed",
            text.get("characters_provided",0)))+" из "+str(text.get("characters_total",0))+".")
        for kind,counts in state.get("phase_coverage",{}).items():
            lines.append(f"{kind}: пакетов {counts['completed']} из {counts['planned']}; "
                f"остаток {counts['remaining']}." + (" План рассчитан по исходному материалу."
                    if state.get("source_sized_calls") else f" Принятый лимит вызовов {counts['limit']}."))
        if not state.get("source_sized_calls"):
            lines.append("Остаток сверх принятого лимита не проверен; первоначальные наблюдения сохранены.")
    consolidation = state.get("consolidation")
    if isinstance(consolidation, dict):
        if consolidation.get("complete"):
            lines.append("Строгий свод сохранённых записей: исходных наблюдений "
                + str(consolidation["raw_count"]) + ", групп " + str(consolidation["group_count"])
                + ". Объединяется только совпадающий текст с общим подтверждённым источником; "
                "все исходники и отдельные рекомендации сохранены. Это не экспертное решение.")
        else:
            lines.append("Строгий свод недоступен: сохранены все исходные наблюдения без группировки.")
    for number,item in enumerate(state.get("observations",[]),start=1):
        lines.extend([f"\n## {number}. {item['title']}",item['description'],
            "Источники: "+", ".join(item["source_ids"]),
            "Нормативная сверка: "+str(item.get("norm_status","unavailable"))])
        if item.get("norm_assessment"):
            lines.append("Модельная сверка по цитате: "+item["norm_assessment"]["explanation"])
        if item.get("critic"):
            lines.append("Критик: "+item["critic"]["explanation"])
        candidate=(item.get("correction") or {}).get("candidate")
        if candidate:
            lines.extend(["Предложенная редакция (оригинал сохранён): "+candidate["title"],candidate["description"]])
    return {"format":"section-review-report-v3","section":state.get("section"),"window_id":window_id,
        "coverage":coverage,"observation_count":len(state.get("observations",[])),
        **({"coverage_version":"batched-v1","phase_coverage":state.get("phase_coverage",{}),
            "phase_call_counts":state.get("phase_call_counts",{}),"text_coverage":state.get("text_coverage",{})}
            if state.get("coverage_version")=="batched-v1" else {}),
        "expert_review_required":True,"markdown":"\n\n".join(lines)}


def load_saved_workflow(session, *, store, run):
    """Read a custody-bound v3 receipt before the caller replaces its pending stage row."""
    rows=RunRepository().stage_results(session,run.run_id)
    stage=next((row for row in rows if row.stage_id=="text_analysis"),None)
    ref=None if stage is None else next((r for r in stage.artifacts if r.get("role")==EXTENDED_REVIEW_ROLE),None)
    session.commit()
    if ref is None:return None
    raw=store.read(parse_blob_id(ref["blob_id"]),verify=True)
    if len(raw)!=ref["size_bytes"] or hashlib.sha256(raw).hexdigest()!=ref["sha256"]:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR,role=EXTENDED_REVIEW_ROLE)
    try:
        doc=json.loads(raw)
        if doc.get("run_id")!=run.run_id or doc.get("version_uid")!=run.version_uid or doc.get("artifact_role")!=EXTENDED_REVIEW_ROLE:
            raise ValueError()
        result=doc["result"]
        return result if isinstance(result,dict) and result.get("workflow_version")=="extended-review-v3" else None
    except (ValueError,TypeError,KeyError):
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR,role=EXTENDED_REVIEW_ROLE) from None


def _run_workflow_v3(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
        publish, progress, checkpoint, observations_document, snapshot_id, profile_sha256,
        bind_native, policy, resume_state=None, visual_only=False):
    from auditmanager.analysis.public import (read_artifact,extended_review_enabled,
        extended_review_bundle_digest,extended_workflow_procedures_v3)
    from auditmanager.jobs.public import has_ambiguous_provider_effect
    state=planned_workflow_result(policy=policy)
    if _source_sized(policy):
        state.update(source_sized_calls=True, completion_policy=policy.get("completion_policy"))
    if (resume_state is not None and "global_cross_window_policy" in policy
            and isinstance(resume_state.get("global_cross_window"), dict)
            and resume_state["global_cross_window"].get("policy") == policy["global_cross_window_policy"]):
        state["global_cross_window"] = deepcopy(resume_state["global_cross_window"])
    if (resume_state is not None and "project_parameters_policy" in policy
            and isinstance(resume_state.get("project_parameters"), dict)
            and resume_state["project_parameters"].get("policy") == policy["project_parameters_policy"]):
        state["project_parameters"] = deepcopy(resume_state["project_parameters"])
    # The run's leg breaker (D-662) lives in this saved state, so an attempt that resumes it (the second pass included) keeps what the
    # first one learned. A saved breaker that cannot be trusted is dropped loudly, never silently.
    saved_breaker=None
    if resume_state is not None and "block_ensemble" in resume_state:
        saved_holder=resume_state["block_ensemble"]
        saved_breaker=saved_holder.get("breaker") if isinstance(saved_holder,dict) else {}
    breaker,breaker_valid=_restore_breaker(saved_breaker)
    if not breaker_valid:
        state["warnings"].append("block_ensemble_breaker_state_invalid")
    state["primary_text_status"]=("pending" if visual_only else "unavailable" if
        isinstance(observations_document,dict) and observations_document.get("input_disposition")=="image_only_no_native_text"
        else "completed" if observations_document is not None else "failed")
    def save(status):
        state["status"]=status
        progress(status,state)
    def parameter_work():
        if "project_parameters_policy" not in policy:
            return
        from .project_parameters import run_project_parameters
        accepted_parameters = policy["project_parameters_policy"]
        def parameter_call(request, index):
            if (type(index) is not int or index < 0
                    or not _source_sized(accepted_parameters) and index >= accepted_parameters["max_calls"]):
                raise _refuse("project_parameters_approved_call_limit")
            return _call(session, run_id=run.run_id, authority=authority, jobs=jobs, journal=journal,
                binding=_cell(binding, "cross_check"), request=request, phase=f"v3:project-parameters:b{index:03d}",
                source_sha256=state["source_sha256"], meter=meter, store=store, publish=publish,
                checkpoint=checkpoint, global_unknown_fence=True)
        run_project_parameters(run=run, **_kw(binding, "cross_check"), outputs=outputs, store=store,
            state=state, accepted=accepted_parameters, durable_call=parameter_call,
            checkpoint=checkpoint, aggregate=aggregate, save=save)
    def aggregate():
        records=state["windows"]
        if breaker["legs"]:
            state["block_ensemble"]={"breaker":breaker}
        source_index={}
        observations=[]
        for record in records:
            for source in record.get("sources",[]):source_index[source["source_id"]]=source
            for observation in record.get("observations",[]):
                observations.append({**observation,"window_id":record["window_id"]})
        global_review = state.get("global_cross_window")
        if isinstance(global_review, dict):
            for source in global_review.get("sources", []):
                previous = source_index.get(source["source_id"])
                if previous is not None and previous != source:
                    raise _refuse("global_cross_window_source_identity_conflict")
                source_index[source["source_id"]] = source
            observations.extend({**observation, "window_id": "global-cross-window",
                "origin_scope": "global_cross_window"} for observation in global_review.get("observations", []))
        for source in state.get("project_parameters", {}).get("sources", []):
            previous = source_index.get(source["source_id"])
            if previous is not None and previous != source:
                raise _refuse("project_parameters_source_identity_conflict")
            source_index[source["source_id"]] = source
        parameters = state.get("project_parameters")
        if isinstance(parameters, dict) and "project_parameter_context_policy" in policy:
            parameters["visual_context_policy"] = deepcopy(policy["project_parameter_context_policy"])
            parameters["visual_context_receipts"] = [{"window_id": record["window_id"], "phase_key": identity, **receipt}
                for record in records for identity, receipt in record.get("project_parameter_context_receipts", {}).items()]
        if isinstance(parameters, dict) and "project_parameter_review_context_policy" in policy:
            parameters["review_context_policy"] = deepcopy(policy["project_parameter_review_context_policy"])
            parameters["review_context_receipts"] = [{"window_id": record["window_id"], "phase_key": identity, **receipt}
                for record in records for identity, receipt in record.get("project_parameter_review_context_receipts", {}).items()]
            if isinstance(global_review, dict):
                parameters["review_context_receipts"].extend({"window_id": "global-cross-window", "phase_key": identity, **receipt}
                    for identity, receipt in global_review.get("project_parameter_review_context_receipts", {}).items())
        state["sources"]=list(source_index.values())
        state["observations"]=observations
        if policy.get("coverage_version") == "batched-v1":
            state["norm_lookup_receipts"] = [{"window_id": record["window_id"], **receipt}
                for record in records for receipt in record.get("norm_lookup_receipts", [])]
            state["reply_refusals"] = [{"window_id": record["window_id"], **receipt}
                for record in records for receipt in record.get("reply_refusals", [])]
            if isinstance(global_review, dict):
                state["norm_lookup_receipts"].extend({"window_id": "global-cross-window", **receipt}
                    for receipt in global_review.get("norm_lookup_receipts", []))
                state["reply_refusals"].extend({"window_id": "global-cross-window", **receipt}
                    for receipt in global_review.get("reply_refusals", []))
        else:
            # The window path's critic reads its reply tolerantly too (`CTX-CRITIC`): the receipts of a refused record are kept, and the
            # key stays absent from a run that has none, as before.
            refusals = [{"window_id": record["window_id"], **receipt}
                for record in records for receipt in record.get("reply_refusals", [])]
            if refusals:
                state["reply_refusals"] = refusals
        if "norm_paragraph_context_policy" in policy:
            state["norm_paragraph_context_policy"] = deepcopy(policy["norm_paragraph_context_policy"])
            state["normative_context_receipts"] = [{"window_id": record["window_id"], "batch_index": identity, **receipt}
                for record in records for identity, receipt in record.get("normative_context_receipts", {}).items()]
            if isinstance(global_review, dict):
                state["normative_context_receipts"].extend({"window_id": "global-cross-window", "batch_index": identity, **receipt}
                    for identity, receipt in global_review.get("normative_context_receipts", {}).items())
        if policy.get("coverage_version")=="batched-v1":
            state["batches"]=[dict(batch,window_id=record["window_id"])
                for record in records for batch in record.get("batches",[])]
            totals={}
            call_counts={}
            for record in records:
                for kind,coverage in record.get("phase_coverage",{}).items():
                    total=totals.setdefault(kind,{key:0 for key in ("planned","completed","remaining",
                        "limit","processed_items","total_items","characters_processed","characters_total")})
                    for key in total:total[key]+=coverage.get(key,0)
                for kind,counts in record.get("phase_call_counts",{}).items():
                    total=call_counts.setdefault(kind,{"completed_calls":0,"replayed":0})
                    for key in total:total[key]+=counts.get(key,0)
            state["phase_coverage"]=totals
            state["phase_call_counts"]=call_counts
        processed=sum(record.get("coverage",{}).get("blocks_processed",0) for record in records)
        state["coverage"]["blocks_processed"]=processed
        state["coverage"]["blocks_remaining"]=max(0,state["coverage"]["blocks_total"]-processed)
        complete=sum(record.get("status")=="completed" for record in records)
        finished=sum(record.get("status") not in {"queued","running"} for record in records)
        current=next((record["window_id"] for record in records if record.get("status")=="running"),None)
        state["window_progress"]={"completed":complete,"finished":finished,
            "failed":sum(record.get("status")=="failed" for record in records),
            "skipped":sum(record.get("status")=="skipped" for record in records),
            "partial":sum(record.get("status")=="partial" for record in records),
            "total":len(records),"current":current,"window_size":16}
        if state.get("text_coverage") is not None:
            covered=set()
            if policy.get("coverage_version")=="batched-v1":
                facts=_coverage_text_stats(records)
                covered={page for page in facts.pop("complete_pages") if 0<page<=policy["text_page_limit"]}
                state["text_coverage"].update(facts)
            else:
                for record in records:
                    comp=next((p for p in record.get("procedures",[]) if p["id"]=="comprehensive_analysis"),None)
                    if comp and comp["status"]=="completed":
                        covered.update(page for page in record.get("context_page_numbers",[]) if 0<page<=policy["text_page_limit"])
            state["text_coverage"]["pages_processed"]=len(covered)
            state["text_coverage"]["pages_remaining"]=max(0,state["text_coverage"]["pages_total"]-len(covered))
        for procedure in state["procedures"]:
            phase_records=list(records)
            if isinstance(global_review, dict) and any(p["id"] == procedure["id"]
                    for p in global_review.get("procedures", [])):
                phase_records.append({**global_review, "window_id": "global-cross-window"})
            values=[next((p for p in record.get("procedures",[]) if p["id"]==procedure["id"]),
                {"status":"queued"}) for record in phase_records]
            statuses=[p["status"] for p in values]
            if not values or all(value=="queued" for value in statuses):status="queued"
            elif "running" in statuses or "queued" in statuses:status="running"
            elif all(value=="completed" for value in statuses):status="completed"
            elif all(value=="skipped" for value in statuses):status="skipped"
            elif all(value=="unavailable" for value in statuses):status="unavailable"
            elif all(value=="failed" for value in statuses):status="failed"
            elif all(p["status"]=="completed" or p.get("reason") in {"no_observations","no_corrections_requested"} for p in values):status="completed"
            else:status="partial"
            procedure["status"]=status
            causes = [{"window_id": record["window_id"], "status": value["status"],
                "reason": value["reason"]} for record, value in zip(phase_records, values)
                if value.get("reason") and value["status"] != "completed"]
            procedure.pop("reason", None)
            procedure.pop("causes", None)
            if status != "completed" and causes:
                causes.sort(key=lambda cause: cause["reason"] in {"dependency_failed", "dependency_unavailable"})
                procedure.update(reason=causes[0]["reason"], causes=causes)
    save("running")
    try:
        if not extended_review_enabled(policy):raise _refuse("extended_v3_authority_invalid")
        version=DocumentRepository().get_version(session,run.version_uid)
        section=policy["section_code"]
        actual_rules=extended_review_bundle_digest(section)
        if actual_rules!=policy["rules_sha256"]:raise _refuse("extended_rules_changed_requires_consent")
        refs={role:{"blob_id":ref.blob_id,"sha256":ref.sha256,"size_bytes":ref.size_bytes}
            for role,ref in sorted(outputs.refs.items()) if role in {"source.document","prepared.text_layer",
                "geometry.portal_blocks","geometry.page_crops","context.document_graph","prepared.recognised_text"}}
        global_sha=extended_digest({"workflow_version":"extended-review-v3","version_uid":run.version_uid,
            "refs":refs,"policy":policy,"profile_sha256":profile_sha256,"norms_snapshot_id":snapshot_id,
            "run_input_digest":getattr(run,"frozen_input_digest",None)})
        state.update(section=section,version_uid=run.version_uid,rules_sha256=actual_rules,source_sha256=global_sha,review_scope="full_document",
            source_provenance={"workflow":"extended-review-v3","rules_bundle_sha256":actual_rules,
                "source_sha256":global_sha,"original_repository":"SU10KAZ/PDF-proverka",
                "original_commit":"3c99481719218b9cfa7560886529916646c61939"})
        total=version.page_count;selected=0;global_skipped=[];page_to_window={};known_visual_refusals=False
        portal_ref=outputs.refs.get("geometry.portal_blocks")
        if portal_ref is not None:
            portal,_=read_artifact(store,parse_blob_id(portal_ref.blob_id),expected_role="geometry.portal_blocks")
            manifest_ref=outputs.refs.get("geometry.page_crops")
            if manifest_ref is None:raise _refuse("extended_prepared_inputs_unavailable")
            manifest,_=read_artifact(store,parse_blob_id(manifest_ref.blob_id),expected_role="geometry.page_crops")
            known_visual_refusals=(any(page.get("geometry")!="ok" for page in portal.get("pages",[]))
                or any(block.get("geometry")!="ok" for block in portal.get("blocks",[])))
            image_blocks=[block for block in portal.get("blocks",[]) if block.get("block_type")=="image"]
            if image_blocks:
                total=len(image_blocks)
                reliable_ids={crop["portal_block_id"] for crop in manifest.get("crops",[])}
                selected=min(policy["max_blocks"],len(reliable_ids))
                ordered=sorted((block for block in image_blocks if block["portal_block_id"] in reliable_ids),
                    key=lambda block:(block["page_number"],block["portal_block_id"]))[:policy["max_blocks"]]
                for ordinal,block in enumerate(ordered):page_to_window.setdefault(block["page_number"],ordinal//16)
                global_skipped=[{"block_id":block["portal_block_id"],"page_number":block["page_number"],
                    "reason":"portal_image_unavailable"} for block in image_blocks if block["portal_block_id"] not in reliable_ids]
                known_visual_refusals=known_visual_refusals or bool(global_skipped)
            else:selected=min(policy["max_blocks"],total)
        else:selected=min(policy["max_blocks"],total)
        count=policy["max_windows"]
        state["text_coverage"]={"pages_total":version.page_count,"pages_selected":policy["text_page_limit"],
            "pages_processed":0,"pages_remaining":version.page_count,"complete_document_claim":False}
        state["coverage"]={"blocks_total":total,"blocks_selected":selected,"blocks_processed":0,
            "blocks_remaining":total,"skipped":global_skipped}
        if total>policy["max_blocks"]:
            state["warnings"].append("remaining_blocks_not_reviewed")
        saved_windows={};visual_windows={}
        if resume_state is not None:
            if resume_state.get("source_sha256")!=global_sha or resume_state.get("rules_sha256")!=actual_rules:
                raise _refuse("extended_saved_workflow_source_changed")
            saved_windows={record["window_id"]:record for record in resume_state.get("windows",[])
                if record.get("status") in {"completed","partial","failed","unavailable"}
                    and not (record.get("visual_phase_complete") and any(p["status"]=="queued" for p in record.get("procedures",[]))) }
            visual_windows={record["window_id"]:record for record in resume_state.get("windows",[])
                if record.get("visual_phase_complete") and record.get("source_window_total") is not None}
        state["windows"]=[]
        for index in range(count):
            window_id=f"w{index:03d}"
            # Carry every completed visual result before starting posttext work. A failure
            # in an earlier window must not erase later windows' already-journaled work.
            record=deepcopy(visual_windows.get(window_id,{
                "procedures":extended_workflow_procedures_v3(),"observations":[],"sources":[]}))
            record.update(window_id=window_id,index=index,total=count,status="queued")
            state["windows"].append(record)

        def stop_later_windows(index, reason):
            for pending in state["windows"][index+1:]:
                retained=any(procedure.get("status")=="completed" for procedure in pending["procedures"])
                pending.update(status="partial" if retained else "skipped",reason=reason)
                for procedure in pending["procedures"]:
                    if procedure.get("status") in {"queued","running"}:
                        procedure.update(status="skipped",reason=reason)
        aggregate();save("running")
        if "project_parameter_review_context_policy" in policy:
            from auditmanager.analysis.public import validate_project_parameter_review_context_policy
            try:
                if not validate_project_parameter_review_context_policy(policy["project_parameter_review_context_policy"],
                        parameters_policy=policy["project_parameters_policy"]):
                    raise ValueError()
            except ValueError:
                raise _refuse("project_parameter_review_context_changed_requires_consent") from None
        if "norm_paragraph_context_policy" in policy:
            from .norm_context import validate_policy as validate_norm_context_policy
            try:
                if not validate_norm_context_policy(policy["norm_paragraph_context_policy"]):
                    raise ValueError("norm_paragraph_context_policy_required")
            except ValueError:
                raise _refuse("norm_paragraph_context_changed_requires_consent") from None
        if "project_parameter_context_policy" in policy:
            from auditmanager.analysis.public import (validate_project_parameter_context_policy,
                validate_project_parameters_policy)
            try:
                if not validate_project_parameters_policy(policy["project_parameters_policy"], section=section):
                    raise ValueError("project_parameters_policy_required")
                if not validate_project_parameter_context_policy(policy["project_parameter_context_policy"],
                        parameters_policy=policy["project_parameters_policy"]):
                    raise ValueError("project_parameter_context_policy_required")
            except ValueError as error:
                reason = str(error)
                if reason not in {"project_parameters_changed_requires_consent", "project_parameters_policy_required",
                        "project_parameter_context_changed_requires_consent", "project_parameter_context_policy_required"}:
                    reason = "project_parameter_context_policy_required"
                raise _refuse(reason) from None
            if (state["project_parameters"].get("status") == "failed"
                    and state["project_parameters"].get("source_sha256") == global_sha):
                state["project_parameters"]["failed_context_retained_without_retry"] = True
                aggregate(); save("running")
            else:
                parameter_work()
        for index,record in enumerate(state["windows"]):
            checkpoint("extended_v3_window")
            window_id=record["window_id"]
            if window_id in saved_windows:
                record.update(saved_windows[window_id],index=index,total=count,replayed=True)
                aggregate();save("running")
                continue
            session.commit()
            record["status"]="running";aggregate();save("running")
            window_observations=observations_document
            if observations_document is not None:
                selected_primary=[]
                for primary_index,observation in enumerate(observations_document.get("observations",[])):
                    evidence=observation.get("evidence",[])
                    page=evidence[0].get("page_number") if evidence else None
                    assigned=((page-1)//16 if type(page) is int and 0<page<=policy["text_page_limit"]
                        else page_to_window.get(page,-1))
                    if assigned==index:selected_primary.append({**observation,"_extended_primary_index":primary_index})
                window_observations={**observations_document,"observations":selected_primary}
            def window_progress(status,result):
                record.update(result,status=status,window_id=window_id,index=index,total=count)
                aggregate();save("running")
            _run_workflow_v2(session,run=run,authority=authority,jobs=jobs,journal=journal,binding=binding,
                outputs=outputs,store=store,meter=meter,publish=publish,progress=window_progress,
                checkpoint=checkpoint,observations_document=window_observations,snapshot_id=snapshot_id,
                profile_sha256=profile_sha256,bind_native=bind_native,window_context={"window_id":window_id,
                    "offset":index*16,"policy":policy,"global_sha256":global_sha,"visual_only":visual_only,
                    "project_parameters": state.get("project_parameters"),"block_breaker":breaker,
                    "primary_text_status":state["primary_text_status"],"saved_visual":visual_windows.get(window_id),
                    "page_count":version.page_count,"known_visual_refusals":known_visual_refusals})
            budget_exhausted=any("cost_budget_exceeded" in str(warning) for warning in record.get("warnings",[]))
            if budget_exhausted:
                stop_later_windows(index,"cost_budget_exceeded")
                state["warnings"].append("cost_budget_exceeded")
                break
            if has_ambiguous_provider_effect(session,run_id=run.run_id):
                session.commit()
                stop_later_windows(index,"provider_outcome_unknown")
                state["warnings"].append("extended_provider_outcome_unknown")
                break
            session.commit()
        aggregate()
        state["window_progress"]["current"]=None
        if visual_only:
            state["visual_phase_complete"]=all(record.get("visual_phase_complete") for record in state["windows"])
            state["window_progress"]["visual_completed"]=sum(record.get("visual_phase_complete",False) for record in state["windows"])
            save("failed" if "extended_provider_outcome_unknown" in state["warnings"] else "running")
            return state
        if "global_cross_window_policy" in policy:
            _run_global_cross_window(session, run=run, authority=authority, jobs=jobs, journal=journal,
                binding=binding, outputs=outputs, store=store, meter=meter, publish=publish,
                checkpoint=checkpoint, snapshot_id=snapshot_id, state=state, policy=policy,
                aggregate=aggregate, save=save)
            aggregate()
        if "project_parameter_context_policy" not in policy:
            parameter_work()
        _retain_primary_observations_v3(state,observations_document=observations_document)
        state.update(_attach_consolidation(state, version_uid=run.version_uid))
        for procedure in state["procedures"]:
            if procedure["status"] in {"queued","running"}:
                procedure.update(status="partial",reason="incomplete_window_procedures")
        state["report"]=_section_report_v3(state)
        state["report"]["windows"]=len(state["windows"])
        report_procedure=next(p for p in state["procedures"] if p["id"]=="report_generation")
        report_procedure.update(status="completed")
        report_procedure.pop("reason", None)
        report_procedure.pop("causes", None)
        degraded=(state["coverage"]["blocks_remaining"]>0 or state["text_coverage"]["pages_remaining"]>0
            or any(record["status"]!="completed" for record in state["windows"])
            or bool(state.get("unreviewed_primary_observations"))
            or isinstance(state.get("global_cross_window"), dict) and state["global_cross_window"]["status"] != "completed"
            or isinstance(state.get("project_parameters"), dict) and state["project_parameters"]["status"] != "completed")
        state["report"]["status"]="partial" if degraded else "completed"
        save("partial" if degraded else "completed")
        return state
    except (DomainError,ValueError,TypeError,KeyError) as error:
        reason=error.detail_fields.get("reason") if isinstance(error,DomainError) else "extended_v3_input_or_reply_invalid"
        reason=str(reason or "extended_v3_failed")
        state["warnings"].append(reason)
        for key in ("global_cross_window", "project_parameters"):
            nested = state.get(key)
            if isinstance(nested, dict) and nested.get("status") in {"queued", "running"}:
                nested.update(status="failed", reason=reason)
                if isinstance(nested.get("report"), dict):
                    nested["report"].update(status="failed", reason=reason)
                for procedure in nested.get("procedures", []):
                    if procedure.get("status") in {"queued", "running"}:
                        procedure.update(status="skipped", reason=reason)
                for receipt in nested.get("batches", []):
                    if receipt.get("status") in {"queued", "running"}:
                        receipt.update(status="skipped", reason=reason)
        for procedure in state["procedures"]:
            if procedure["status"] in {"queued","running"}:procedure.update(status="failed",reason=reason)
        state["report"]=_section_report_v3(state)
        save("failed")
        return state


def _retain_primary_observations_v3(state, *, observations_document):
    """Retain every late primary-text proposal, including ones outside paid review windows."""
    if not isinstance(observations_document,dict):return
    seen={item.get("primary_observation_key") for item in state["observations"] if item.get("primary_observation_key")}
    retained=[]
    for index,original in enumerate(observations_document.get("observations",[])):
        key=extended_digest({"index":index,"observation":original})[:24]
        if key in seen:continue
        evidence=original.get("evidence",[])
        page=evidence[0].get("page_number") if evidence else None
        source_id="primary_text_"+key
        source={"source_id":source_id,"kind":"text","source_type":"primary_text_proposal",
            "page_number":page,"quote_source":"unverified_proposal","primary_observation_key":key}
        if not any(s["source_id"]==source_id for s in state["sources"]):state["sources"].append(source)
        item={"observation_id":"xobs_"+key,"primary_observation_key":key,
            "title":str(original.get("category","Текстовое наблюдение"))[:200],
            "description":str(original.get("finding_text",""))[:3000],"source_ids":[source_id],
            "source_kind":"text","status":"requires_expert_review","original_primary_observation":original,
            "review_status":"not_reviewed","review_reason":"outside_processed_review_window",
            "norm_status":"unavailable","norm_reason":"outside_processed_review_window","norm_candidates":[],
            "window_id":None}
        state["observations"].append(item);retained.append(item)
    state["unreviewed_primary_observations"]=retained
    if retained:
        state["warnings"].append("primary_text_observations_outside_review_window")
        next(p for p in state["procedures"] if p["id"]=="finding_review").update(
            status="partial",reason="primary_text_observations_outside_review_window")


def _coverage_plan_receipts(state, *, kind, plan, window_id):
    """Persist the complete known plan before any next paid request."""
    receipts = state.setdefault('batches', [])
    for batch in [*plan['batches'], *plan['pending_batches']]:
        key = f'{window_id}:{kind}:b{batch["index"]:03d}'
        receipt = {'batch_key': key, 'window_id': window_id, 'procedure': kind,
            'index': batch['index'], 'status': 'queued', 'input_ids': batch['input_ids'],
            'source_ids': batch['source_ids'], 'page_numbers': batch['page_numbers'],
            'input_characters': batch['input_characters'], 'input_count': len(batch['items']),
            'plan_sha256': batch['batch_sha256'], 'context_ranges': [
                {field: row[field] for field in ('source_id', 'page_number', 'character_start',
                    'character_end', 'character_field') if field in row}
                for row in batch['native_context']]}
        if batch['index'] >= plan['limit']:
            receipt['reason'] = 'approved_phase_call_limit'
        receipts.append(receipt)
    for row in plan['oversized']:
        receipts.append({'batch_key': f'{window_id}:{kind}:oversized:{row["ordinal"]}',
            'window_id': window_id, 'procedure': kind, 'index': None, 'status': 'unavailable',
            'input_ids': [row['input_id']], 'source_ids': [], 'page_numbers': [],
            'input_characters': row['input_characters'], 'input_count': 1, 'reason': row['reason']})
    state.setdefault('phase_coverage', {})[kind] = {'planned': plan['planned'] + len(plan['oversized']),
        'completed': 0, 'remaining': plan['planned'] + len(plan['oversized']), 'limit': plan['limit'],
        'processed_items': 0, 'total_items': plan['total_items'], 'characters_processed': 0,
        'characters_total': plan['total_characters']}


def _coverage_complete(state, *, kind, index, partial=False, reason=None):
    row = next(row for row in state['batches'] if row['procedure'] == kind and row['index'] == index)
    row['status'] = 'partial' if partial else 'completed'
    row.pop('reason', None)
    if reason:
        row['reason'] = reason
    coverage = state['phase_coverage'][kind]
    completed = [batch for batch in state['batches'] if batch['procedure'] == kind
        and batch['status'] == 'completed']
    coverage.update(completed=len(completed), remaining=coverage['planned'] - len(completed),
        processed_items=sum(batch.get('input_count', 0) for batch in completed),
        characters_processed=sum(batch.get('input_characters', 0) for batch in completed))


def _coverage_failed(state, *, kind, index, error):
    """A batch whose paid reply the parser refused: the receipt says so, the batches after it still run.

    ``response_received`` stays as the call left it, so the receipt shows that the reply was paid for.
    """
    row = next(row for row in state['batches'] if row['procedure'] == kind and row['index'] == index)
    row.update(status='failed', reason=f'{kind}_reply_refused', error_code=_reply_refusal_code(error))


def _comprehensive_batched_v3(*, run, binding, state, contexts, block_items, phase, call, window_context):
    from auditmanager.analysis.public import plan_extended_coverage, build_comprehensive_request_batched_v3
    kind = 'comprehensive_analysis'
    state['text_piece_sources']=[{'source_id':row['source_id'],'page_number':row['page_number'],
        'character_field':field,'characters_total':len(row.get(field,''))}
        for row in contexts for field in ('text','recognised_context') if row.get(field,'')]
    plan = plan_extended_coverage(kind=kind,
        items=[{'kind': 'visual', 'item': item} for item in block_items] +
            [{'kind': 'text', 'item': item} for item in state['text_items']],
        contexts=contexts, sources=state['sources'], limit=None if window_context['policy'].get('unbounded_stats') or _source_sized(window_context['policy'])
            else window_context['policy']['phase_call_limits'][kind])
    _coverage_plan_receipts(state, kind=kind, plan=plan, window_id=window_context['window_id'])
    phase(kind, 'running')
    output = []
    for batch in plan['batches']:
        selected = [source for source in state['sources'] if source['source_id'] in batch['source_ids']]
        payload = {'coverage_version': 'batched-v1', 'native_context': batch['native_context'],
            'visual_observations': [row['item'] for row in batch['items'] if row['kind'] == 'visual'],
            'text_observations': [{key: row['item'][key] for key in ('title', 'description', 'source_ids', 'norm_queries')}
                for row in batch['items'] if row['kind'] == 'text'],
            'sources': [{key: value for key, value in source.items() if key != 'context'} for source in selected],
            'source_sha256': state['source_sha256'], 'coverage': state['coverage'],
            'batch_index': batch['index'], 'batch_sha256': batch['batch_sha256']}
        request = build_comprehensive_request_batched_v3(**_kw(binding, "cross_check"),
            run_id=run.run_id, section=state['section'], payload=payload,
            window_id=window_context['window_id'] + f':comp:b{batch["index"]:03d}',
            relaxed_limits=_bounds_lifted(window_context['policy']))
        identity=f'{kind}:b{batch["index"]:03d}'
        parsed, refused = _received_reply(state=state, request=request, response=call(request, identity),
            parse=lambda text, **kwargs: parse_extended_reply(text,
                allowed_sources=set(batch['source_ids']), **kwargs), call=call, identity=identity,
            policy=window_context['policy'])
        output.extend(parsed)
        state['observations'] = finalize_extended_items([*state['text_items'], *block_items, *output], state['sources'])
        _coverage_complete(state, kind=kind, index=batch['index'], partial=refused,
            reason='comprehensive_analysis_reply_refused' if refused else None)
        phase(kind, 'running')
    deferred = bool(plan['pending_batches'] or plan['oversized'])
    refused = any(row.get('status') == 'partial' for row in state.get('batches', []) if row['procedure'] == kind)
    if not plan['batches']:
        phase(kind, 'unavailable', 'no_reliable_window_sources')
    else:
        phase(kind, 'partial' if deferred or refused else 'completed', 'approved_phase_call_limit' if deferred
            else 'comprehensive_analysis_reply_refused' if refused else None)
    state['comprehensive_context_coverage'] = {'characters_total': plan['total_characters'],
        'characters_provided': state['phase_coverage'][kind]['characters_processed'],
        'truncated': deferred, 'complete_document_claim': False}
    return output


def _norm_batched_v3(*, session, run, binding, state, snapshot_id, phase, call, checkpoint, window_context):
    from auditmanager.analysis.public import (plan_extended_coverage,
        build_norm_review_request_batched_v3, parse_norm_review_batched_v3)
    kind = 'norm_verification'
    accepted_context = window_context['policy'].get('norm_paragraph_context_policy')
    # Retrieval is local corpus work. Every observation remains present even if
    # its quote assessment is outside the separately accepted model-call limit.
    state['warnings'].extend(_norms(session, state['observations'], snapshot_id,
        full_document=True, checkpoint=checkpoint, lookup_receipts=state.setdefault('norm_lookup_receipts', []),
        query_planning=_source_sized(window_context['policy'])))
    registry={}
    quote_variants=False
    context_incomplete=False
    for item in state['observations']:
        if accepted_context is not None:
            # The fresh request supplies an exact candidate list per input, so
            # another observation's search excerpt must not replace this one.
            continue
        canonical_candidates=[]
        for candidate in item.get('norm_candidates',[]):
            canonical=registry.setdefault(candidate['paragraph_id'],candidate)
            if canonical['quote']!=candidate['quote']:
                item.setdefault('norm_candidate_variants',[]).append(candidate)
                quote_variants=True
            canonical_candidates.append(canonical)
        item['norm_candidates']=canonical_candidates
    candidates = [item for item in state['observations'] if item.get('norm_candidates')]
    plan = plan_extended_coverage(kind=kind, items=candidates,
        limit=None if window_context['policy'].get('unbounded_stats') or _source_sized(window_context['policy'])
            else window_context['policy']['phase_call_limits'][kind])
    _coverage_plan_receipts(state, kind=kind, plan=plan, window_id=window_context['window_id'])
    for item in candidates:
        item.update(norm_review_status='not_reviewed', norm_review_reason='approved_phase_call_limit')
    if not candidates:
        if not state['observations']:
            phase(kind,'completed','no_observations')
        elif _source_sized(window_context['policy']) and all(item.get('norm_status') in {'not_applicable', 'not_found'}
                for item in state['observations']):
            phase(kind, 'completed', 'no_norm_candidates_found' if any(item.get('norm_status') == 'not_found'
                for item in state['observations']) else 'no_normative_question')
        else:
            phase(kind, 'unavailable', 'corpus_unavailable' if snapshot_id is None else 'candidate_context_unavailable')
        return
    phase(kind, 'running')
    refused_replies = 0
    for batch in plan['batches']:
        indexed = {row['input_id']: row['item'] for row in batch['items']}
        registry = {candidate['paragraph_id']: candidate for item in indexed.values()
            for candidate in item['norm_candidates']}
        request = build_norm_review_request_batched_v3(**_kw(binding, "norms"),
            run_id=run.run_id, section=state['section'], window_id=window_context['window_id'] +
                f':norm:b{batch["index"]:03d}', relaxed_limits=_bounds_lifted(window_context['policy']), payload={'coverage_version': 'batched-v1',
                    'observations': [{'input_id': key, 'title': item['title'], 'description': item['description'],
                        'source_ids': item['source_ids'], 'norm_candidate_ids':
                            [candidate['paragraph_id'] for candidate in item['norm_candidates']]}
                        for key, item in indexed.items()], 'norm_context': list(registry.values()),
                    'source_sha256': state['source_sha256'], 'batch_sha256': batch['batch_sha256']})
        context_receipt = None
        if accepted_context is not None:
            from .norm_context import attach as attach_norm_context
            request, context_receipt = attach_norm_context(session, request, observations=indexed,
                snapshot_id=snapshot_id, accepted=accepted_context, checkpoint=checkpoint)
            _norm_request_within_bounds(request, policy=window_context['policy'])
            context_incomplete = context_incomplete or context_receipt['contexts_not_provided'] > 0 or any(
                row.get('search_quote_literal_in_paragraph') is not True
                for row in context_receipt['context']['paragraphs'])
            context_receipt.update(request_sha256=request.request_sha256, request_prepared=True, response_received=False)
            state.setdefault('normative_context_receipts', {})[str(batch['index'])] = context_receipt
            phase(kind, 'running')
        try:
            response = call(request, f'{kind}:b{batch["index"]:03d}')
            if context_receipt is not None:
                context_receipt.update(response_received=True, response_sha256=response.response_sha256)
        finally:
            if context_receipt is not None:
                paid_receipt = next((row for row in state.get('batches', [])
                    if row.get('procedure') == kind and row.get('index') == batch['index']), {})
                if paid_receipt.get('response_received'):
                    context_receipt.update(response_received=True, replayed=paid_receipt.get('replayed', False))
        try:
            parsed, refused = _received_reply(state=state, request=request, response=response,
                parse=lambda text, **kwargs: parse_norm_review_batched_v3(text,
                    observations=indexed, allowed_sources={source['source_id'] for source in state['sources']}),
                call=call, identity=f'{kind}:b{batch["index"]:03d}', policy=window_context['policy'])
            if refused:
                raise ValueError('norm_verification_reply_refused')
        except ValueError as error:
            # The reply is paid for and saved; one refused reply costs its own batch, not the window.
            _coverage_failed(state, kind=kind, index=batch['index'], error=error)
            for item in indexed.values():
                item.update(norm_review_status='not_reviewed', norm_review_reason=f'{kind}_reply_refused')
            refused_replies += 1
            phase(kind, 'running')
            continue
        for row in parsed:
            indexed[row['input_id']].update(norm_assessment=row['norm_assessment'],
                norm_review_status='reviewed', norm_review_reason=None)
        _coverage_complete(state, kind=kind, index=batch['index'])
        phase(kind, 'running')
    deferred = bool(plan['pending_batches'] or plan['oversized'])
    unprocessed = (any(item.get('norm_status') not in {'not_applicable', 'not_found', 'candidates'}
        for item in state['observations']) if _source_sized(window_context['policy'])
        else len(candidates) < len(state['observations']))
    incomplete = deferred or refused_replies or quote_variants or context_incomplete or unprocessed
    phase(kind, 'partial' if incomplete else 'completed', 'approved_phase_call_limit' if deferred
        else f'{kind}_reply_refused' if refused_replies
        else 'norm_quote_variants_retained' if quote_variants
        else 'norm_paragraph_context_incomplete' if context_incomplete
        else next((item.get('norm_reason') for item in state['observations']
            if item.get('norm_status') == 'unavailable'), 'normative_query_required') if unprocessed else None)


def _review_batched_v3(*, run, binding, state, phase, call, window_context, contexts, norm_images=None):
    from auditmanager.analysis.public import (plan_extended_coverage, build_critic_request,
        parse_critic_reply, build_corrector_request, parse_corrector_reply)
    window_id = window_context['window_id']
    limits = window_context['policy']['phase_call_limits']
    state['reviews'] = []; state['critiques'] = []; state['corrections'] = []
    for item in state['observations']:
        item.update(review_status='not_reviewed', review_reason='approved_phase_call_limit')
    kind = 'finding_review'
    plan = plan_extended_coverage(kind=kind, items=state['observations'],
        limit=None if window_context['policy'].get('unbounded_stats') or _source_sized(window_context['policy']) else limits[kind])
    _coverage_plan_receipts(state, kind=kind, plan=plan, window_id=window_id)
    critic_cut = False
    refused_replies = 0
    correction_targets = []
    if not state['observations']:
        phase(kind, 'completed', 'no_observations')
    else:
        phase(kind, 'running')
    for batch in plan['batches']:
        indexed = {row['input_id']: row['item'] for row in batch['items']}
        references = set(batch['source_ids'])
        sources = [source for source in state['sources'] if source['source_id'] in references]
        context = {'coverage': state['coverage'], 'window_id': window_id,
            'source_sha256': state['source_sha256'], 'ocr_status': 'not_performed',
            'native_context': [row for row in contexts if row['source_id'] in references]}
        request = build_critic_request(**_kw(binding, "review"), run_id=run.run_id,
            section=state['section'], observations=indexed, sources=sources,
            window_id=window_id + f':critic:b{batch["index"]:03d}', context=context,
            full_context=_source_sized(window_context['policy']),
            reference_section=_reference_section(binding, window_context['policy']))
        imaged = frozenset()
        if norm_images is not None:  # `M7-NORM-PNG`: the task is created with the pages of its own norm paragraphs
            request, imaged = norm_images.attach(request, state=state, identity=f'{kind}:b{batch["index"]:03d}')
        payload = json.loads(request.body['messages'][0]['content'])
        cut = any(payload.get(key, {}).get('truncated', False) for key in
            ('context_coverage', 'norm_context_coverage'))
        critic_cut |= cut
        response = call(request, f'{kind}:b{batch["index"]:03d}')
        try:
            reviews, refused = _received_reply(state=state, request=request, response=response,
                parse=lambda text, **kwargs: parse_critic_reply(text, observations=indexed, sources=sources,
                    allowed_sources=references, context=context, **kwargs), call=call,
                identity=f'{kind}:b{batch["index"]:03d}', policy=window_context['policy'])
        except ValueError as error:
            # The reply is paid for and saved; one refused reply costs its own batch, not the window.
            _coverage_failed(state, kind=kind, index=batch['index'], error=error)
            for item in indexed.values():
                item.update(review_status='not_reviewed', review_reason=f'{kind}_reply_refused')
            refused_replies += 1
            phase(kind, 'running')
            continue
        state['reviews'].extend(reviews); state['critiques'].extend(reviews)
        refused_replies += int(refused)
        for review in reviews:
            item = indexed[review['input_id']]
            item.update(critic=review, review_status='reviewed', review_reason=None,
                context_kinds=_critic_context_kinds(item, payload, imaged))
            if review['needs_correction']:
                correction_targets.append(item)
        if refused:
            # `_received_reply` keeps the records that parsed and returns instead of raising, so an item the reply did not
            # carry (all of them when the reply was unreadable) would keep the default `approved_phase_call_limit` set above:
            # it was not left out of the plan, its answer was refused. The refusal itself is in `state['reply_refusals']`.
            for item in indexed.values():
                if item['review_status'] != 'reviewed':
                    item['review_reason'] = f'{kind}_reply_refused'
        _coverage_complete(state, kind=kind, index=batch['index'], partial=cut or refused,
            reason=f'{kind}_reply_refused' if refused else 'context_window_truncated' if cut else None)
        phase(kind, 'running')
    deferred = bool(plan['pending_batches'] or plan['oversized'])
    if state['observations']:
        phase(kind, 'partial' if deferred or critic_cut or refused_replies else 'completed',
            'approved_phase_call_limit' if deferred else f'{kind}_reply_refused' if refused_replies
            else 'context_window_truncated' if critic_cut else None)
    kind = 'finding_correction'
    plan = plan_extended_coverage(kind=kind, items=correction_targets,
        limit=None if window_context['policy'].get('unbounded_stats') or _source_sized(window_context['policy']) else limits[kind])
    _coverage_plan_receipts(state, kind=kind, plan=plan, window_id=window_id)
    if not correction_targets:
        phase(kind, 'completed', 'no_corrections_requested')
    else:
        phase(kind, 'running')
    any_partial = False
    refused_replies = 0
    for batch in plan['batches']:
        indexed = {row['input_id']: row['item'] for row in batch['items']}
        # Re-key only the immutable critic input identity for this disjoint
        # correction batch; no original observation or critic content is changed.
        critiques = [{**item['critic'], 'input_id': key} for key, item in indexed.items()]
        references = set(batch['source_ids'])
        sources = [source for source in state['sources'] if source['source_id'] in references]
        context = {'coverage': state['coverage'], 'window_id': window_id,
            'source_sha256': state['source_sha256'], 'ocr_status': 'not_performed',
            'native_context': [row for row in contexts if row['source_id'] in references]}
        request = build_corrector_request(**_kw(binding, "correction"), run_id=run.run_id,
            section=state['section'], observations=indexed, critiques=critiques, sources=sources,
            window_id=window_id + f':corrector:b{batch["index"]:03d}', context=context,
            full_context=_source_sized(window_context['policy']))
        if request is None:
            _coverage_complete(state, kind=kind, index=batch['index'])
            continue
        payload = json.loads(request.body['messages'][0]['content'])
        cut = any(payload.get(key, {}).get('truncated', False) for key in
            ('context_coverage', 'norm_context_coverage'))
        response = call(request, f'{kind}:b{batch["index"]:03d}')
        try:
            corrections, refused = _received_reply(state=state, request=request, response=response,
                parse=lambda text, **kwargs: parse_corrector_reply(text, observations=indexed, critiques=critiques,
                    sources=sources, allowed_sources=references, context=context, **kwargs), call=call,
                identity=f'{kind}:b{batch["index"]:03d}', policy=window_context['policy'])
        except ValueError as error:
            # The critic rows of this batch stay without a proposal; the batches after it still run.
            _coverage_failed(state, kind=kind, index=batch['index'], error=error)
            refused_replies += 1
            phase(kind, 'running')
            continue
        state['corrections'].extend(corrections)
        refused_replies += int(refused)
        for row in corrections:
            indexed[row['input_id']]['correction'] = row
        # A valid needs_context recommendation completes this machine review;
        # it remains explicit advice for the expert. Unread available context
        # and refused records still make execution incomplete.
        partial = cut or refused or (not _source_sized(window_context['policy'])
            and any(row['action'] == 'needs_context' for row in corrections))
        any_partial |= partial
        _coverage_complete(state, kind=kind, index=batch['index'], partial=partial,
            reason=f'{kind}_reply_refused' if refused else 'context_window_truncated' if cut
            else 'additional_context_required' if partial else None)
        phase(kind, 'running')
    deferred = bool(plan['pending_batches'] or plan['oversized'])
    if correction_targets:
        phase(kind, 'partial' if deferred or any_partial or refused_replies else 'completed',
            'approved_phase_call_limit' if deferred else f'{kind}_reply_refused' if refused_replies
            else 'context_window_truncated' if any_partial else None)
    phase('report_generation', 'running')
    state['report'] = _section_report_v3(state, window_id=window_id)
    phase('report_generation', 'completed')


def _coverage_text_stats(records):
    expected, completed = {}, {}
    for record in records:
        for row in record.get('text_piece_sources', []):
            expected[(row['source_id'], row['character_field'])] = row
        for batch in record.get('batches', []):
            if batch['procedure'] != 'comprehensive_analysis' or batch['status'] != 'completed':
                continue
            for row in batch.get('context_ranges', []):
                completed.setdefault((row['source_id'], row['character_field']), []).append(
                    (row['character_start'], row['character_end']))
    total, processed, pages, complete_pages = 0, 0, {}, set()
    for key, source in expected.items():
        length = source['characters_total']
        total += length
        last, covered = 0, 0
        for start, end in sorted(completed.get(key, [])):
            start, end = max(0, start), min(length, end)
            if end > max(last, start):
                covered += end - max(last, start)
            last = max(last, end)
        processed += covered
        pages.setdefault(source['page_number'], []).append(covered >= length)
    for page, statuses in pages.items():
        if statuses and all(statuses):
            complete_pages.add(page)
    return {'complete_pages': complete_pages, 'characters_total': total,
        'characters_processed': processed, 'characters_remaining': max(0, total - processed),
        'known_page_contexts': len(pages)}


def _virtual_window_policy(accepted, policy):
    """The part of the consent the global cross-window review's virtual window carries: its own call limits, and of the run's consent only what
    the shared batched procedures read. The critic of the global review is a `review:main` task too, so the stand offers it the reference
    section when the consent holds the ``executor_context_policy`` (`CTX-CRITIC`); its prompt (`_reference_section`) has to say what that is."""
    return {"phase_call_limits": accepted["call_limits"],
        **({"completion_policy": policy["completion_policy"],
            "semantic_repair_attempts": policy["semantic_repair_attempts"]}
            if _source_sized(policy) else {}),
        **({"norm_paragraph_context_policy": policy["norm_paragraph_context_policy"]}
            if "norm_paragraph_context_policy" in policy else {}),
        **({"executor_context_policy": policy["executor_context_policy"]}
            if "executor_context_policy" in policy else {})}


def _run_global_cross_window(session, *, run, authority, jobs, journal, binding, outputs, store,
        meter, publish, checkpoint, snapshot_id, state, policy, aggregate, save):
    """A separate consent-bound virtual window; local originals are never replaced."""
    from auditmanager.analysis.public import (read_artifact, plan_global_cross_window,
        build_global_cross_window_request, parse_global_cross_window_reply,
        validate_extended_cross_window_policy)
    accepted = policy.get("global_cross_window_policy")
    if not validate_extended_cross_window_policy(accepted):
        raise _refuse("global_cross_window_authority_invalid")
    global_state = state["global_cross_window"]
    source_sha = state["source_sha256"]
    if global_state.get("source_sha256") not in {None, source_sha}:
        raise _refuse("global_cross_window_saved_source_changed")
    if (global_state.get("status") in {"completed", "partial", "unavailable"}
            and global_state.get("manifest_sha256") and global_state.get("policy") == accepted
            and all(row.get("status") in {"completed", "partial", "unavailable", "skipped", "failed"}
                    for row in global_state.get("procedures", []))):
        global_state["reused_saved_result"] = True
        aggregate(); save("running")
        return
    global_state.update(status="running", source_sha256=source_sha, section=state["section"],
        version_uid=run.version_uid, coverage_version="batched-v1", window_id="global-cross-window")
    if _source_sized(accepted):
        global_state["source_sized_calls"] = True
    used = {}
    active = None

    def update_coverage():
        completed = [row for row in global_state.get("batches", [])
            if row.get("procedure") == "comprehensive_analysis" and row.get("status") == "completed"]
        coverage = global_state["coverage"]
        completed_pairs = sum(row.get("pair_count", 1) for row in completed)
        coverage.update(pairs_completed=completed_pairs, source_pages_compared=len({page
            for row in completed for page in row.get("page_numbers", [])}),
            windows_compared=len({window for row in completed for window in row.get("window_ids", [])}),
            global_semantic_complete=False)
        candidate_count = coverage.get("candidate_pairs_eligible")
        if type(candidate_count) is int:
            coverage["pairs_remaining"] = max(0, candidate_count - completed_pairs)
        coverage["all_pairs_complete"] = coverage.get("pairs_remaining") == 0 and not coverage.get("truncated", False)

    def persist():
        update_coverage(); aggregate(); save("running")

    def phase(identity, status, reason=None):
        nonlocal active
        active = identity
        row = next(row for row in global_state["procedures"] if row["id"] == identity)
        row.update(status=status)
        row.pop("reason", None)
        if reason: row["reason"] = reason
        persist()

    def call(request, identity):
        base_identity, repair_separator, repair_attempt = identity.partition(":repair:")
        repairing = bool(repair_separator)
        if repairing and (policy.get("semantic_repair_attempts") != 1 or repair_attempt != "1"):
            raise _refuse("semantic_repair_not_approved")
        kind, ordinal = base_identity.rsplit(":", 1)
        index = int(ordinal.removeprefix("b"))
        if (kind not in accepted["call_limits"] or index < 0
                or not _source_sized(accepted) and index >= accepted["call_limits"][kind]):
            raise _refuse("global_cross_window_call_identity_invalid")
        visited = used.setdefault(kind, set())
        if (base_identity not in visited and not _source_sized(accepted)
                and len(visited) >= accepted["call_limits"][kind]):
            raise _refuse("global_cross_window_approved_phase_call_limit")
        visited.add(base_identity)
        parameter_review_receipt = None
        review_context = policy.get("project_parameter_review_context_policy")
        if not repairing and review_context is not None and kind in review_context["scopes"]:
            from auditmanager.analysis.public import attach_project_parameter_review_context
            request, parameter_review_receipt = attach_project_parameter_review_context(request,
                parameters=state["project_parameters"], accepted=review_context,
                parameters_policy=policy["project_parameters_policy"], procedure=kind)
            parameter_review_receipt.update(request_sha256=request.request_sha256,
                request_prepared=True, response_received=False)
            global_state.setdefault("project_parameter_review_context_receipts", {})[identity] = parameter_review_receipt
        if not hasattr(call, "prepared_requests"):
            call.prepared_requests = {}
        call.prepared_requests[identity] = request
        receipt = next(row for row in global_state["batches"] if row["procedure"] == kind and row["index"] == index)
        if repairing:
            parent_receipt = receipt
            receipt = {"attempt": 1, "status": "running"}
            parent_receipt.setdefault("repair_attempts", []).append(receipt)
        receipt.update(status="running", request_sha256=request.request_sha256)
        persist()
        response, replayed = _call(session, run_id=run.run_id, authority=authority, jobs=jobs,
            journal=journal, binding=_phase_binding(binding, identity), request=request,
            phase="v3:global-cross-window:" + identity, source_sha256=source_sha,
            meter=meter, store=store, publish=publish, checkpoint=checkpoint, global_unknown_fence=True)
        receipt.update(response_received=True, replayed=replayed, response_sha256=response.response_sha256)
        if repairing:
            receipt["status"] = "received"
        if parameter_review_receipt is not None:
            parameter_review_receipt.update(response_received=True, replayed=replayed,
                response_sha256=response.response_sha256)
        counts = global_state.setdefault("phase_call_counts", {}).setdefault(kind, {"completed_calls": 0, "replayed": 0})
        counts["replayed" if replayed else "completed_calls"] += 1
        if response.truncated and policy.get("semantic_repair_attempts") != 1:
            raise _refuse("extended_response_truncated")
        return response

    try:
        checkpoint("global_cross_window_source_plan")
        text_ref = outputs.refs.get("prepared.text_layer")
        if text_ref is None: raise _refuse("global_cross_window_text_source_unavailable")
        text_layer, _ = read_artifact(store, parse_blob_id(text_ref.blob_id), expected_role="prepared.text_layer")
        recognised_ref = outputs.refs.get("prepared.recognised_text")
        recognised = {}
        if recognised_ref is not None:
            recognised, _ = read_artifact(store, parse_blob_id(recognised_ref.blob_id), expected_role="prepared.recognised_text")
        plan = plan_global_cross_window(version_uid=run.version_uid, text_layer=text_layer, recognised=recognised,
            windows=state["windows"], sources=state["sources"], source_sha256=source_sha,
            max_calls=None if _source_sized(accepted) else accepted["call_limits"]["comprehensive_analysis"],
            **({"coverage_mode": accepted["coverage_mode"]} if _source_sized(accepted) else {}),
            piece_characters=accepted["piece_characters"],
            text_layer_sha256=text_ref.sha256,
            recognised_sha256=None if recognised_ref is None else recognised_ref.sha256)
        if (plan.get("version") != accepted["version"] or plan.get("version_uid") != run.version_uid
                or plan.get("source_sha256") != source_sha
                or not _source_sized(accepted) and len(plan["batches"]) > accepted["call_limits"]["comprehensive_analysis"]
                or not isinstance(plan.get("manifest_sha256"), str) or len(plan["manifest_sha256"]) != 64):
            raise _refuse("global_cross_window_plan_invalid")
        if global_state.get("manifest_sha256") not in {None, plan["manifest_sha256"]}:
            raise _refuse("global_cross_window_saved_manifest_changed")
        global_state.update(manifest_sha256=plan["manifest_sha256"], sources=deepcopy(plan["sources"]),
            pieces=deepcopy(plan.get("pieces", [])), pending_batches=deepcopy(plan.get("pending_batches", [])),
            omitted=deepcopy(plan.get("omitted", [])), coverage=deepcopy(plan["coverage"]),
            batches=[], phase_coverage={}, phase_call_counts={})
        global_state["coverage"].update(global_semantic_complete=False)
        selected_keys = {batch["batch_key"] for batch in plan["batches"]}
        originals = global_state.setdefault("original_observations", [])
        if any(item.get("cross_window_batch_key") not in selected_keys for item in originals):
            raise _refuse("global_cross_window_saved_observation_scope_changed")
        global_state["observations"] = deepcopy(originals)
        known_batches = [*plan["batches"], *plan.get("pending_batches", [])]
        indexed_pieces = {row["source_id"]: row for row in plan.get("pieces", [])}
        for ordinal, batch in enumerate(known_batches):
            index = batch.get("index", ordinal)
            rows = batch.get("sources") or [indexed_pieces[key] for key in batch.get("source_ids", []) if key in indexed_pieces]
            receipt = {"batch_key": f"global-cross-window:comprehensive_analysis:b{index:03d}",
                "planner_batch_key": batch.get("batch_key"), "window_id": "global-cross-window",
                "procedure": "comprehensive_analysis", "index": index,
                "status": "queued" if ordinal < len(plan["batches"]) else "pending",
                "input_ids": [], "source_ids": list(batch.get("source_ids", [])),
                "page_numbers": list(batch.get("page_numbers", [])), "window_ids": list(batch.get("window_ids", [])),
                "input_count": len(batch.get("source_ids", [])),
                "pair_count": batch.get("pair_count", 1),
                "input_characters": sum(row["character_end"] - row["character_start"] for row in rows),
                "plan_sha256": batch.get("batch_sha256"), "context_ranges": [
                    {key: row[key] for key in ("source_id", "page_number", "window_id", "character_field", "character_start", "character_end")
                     if key in row} for row in rows]}
            if ordinal >= len(plan["batches"]): receipt["reason"] = "approved_global_phase_call_limit"
            global_state["batches"].append(receipt)
        global_state["phase_coverage"]["comprehensive_analysis"] = {"planned": len(known_batches), "completed": 0,
            "remaining": len(known_batches), "limit": accepted["call_limits"]["comprehensive_analysis"],
            "processed_items": 0, "total_items": sum(row["input_count"] for row in global_state["batches"]),
            "characters_processed": 0, "characters_total": sum(row["input_characters"] for row in global_state["batches"])}
        phase("comprehensive_analysis", "running" if plan["batches"] else "completed",
              None if plan["batches"] else "no_cross_window_candidates")
        for batch in plan["batches"]:
            checkpoint("global_cross_window_batch")
            request = build_global_cross_window_request(**_kw(binding, "cross_check"), run_id=run.run_id,
                section=state["section"], batch=batch, source_sha256=source_sha, policy=accepted)
            response = call(request, f'comprehensive_analysis:b{batch["index"]:03d}')
            parsed, refused = _received_reply(state=global_state, request=request, response=response,
                parse=lambda text, **kwargs: parse_global_cross_window_reply(text, batch=batch, **kwargs),
                call=call, identity=f'comprehensive_analysis:b{batch["index"]:03d}', policy=policy)
            finalized = finalize_extended_items(parsed, global_state["sources"])
            previous = [item for item in originals if item["cross_window_batch_key"] == batch["batch_key"]]
            if previous and extended_digest(previous) != extended_digest(finalized):
                raise _refuse("global_cross_window_saved_original_changed")
            originals[:] = [item for item in originals if item["cross_window_batch_key"] != batch["batch_key"]] + finalized
            global_state["observations"] = deepcopy(originals)
            _coverage_complete(global_state, kind="comprehensive_analysis", index=batch["index"],
                partial=refused, reason="global_cross_window_reply_refused" if refused else None)
            phase("comprehensive_analysis", "running")
        deferred = bool(plan.get("pending_batches") or plan.get("omitted") or plan["coverage"].get("truncated")
            or any(row.get("status") == "partial" for row in global_state["batches"]))
        phase("comprehensive_analysis", "partial" if deferred else "completed",
              "approved_global_phase_call_limit_or_source_selection" if deferred else None)
        virtual_context = {"window_id": "global-cross-window", "policy": _virtual_window_policy(accepted, policy)}
        contexts = [{"source_id": source["source_id"], "page_number": source["page_number"],
            "text": source["quote"] if source["character_field"] == "text" else "",
            "recognised_context": source["quote"] if source["character_field"] == "recognised_context" else ""}
            for source in global_state["sources"]]
        _norm_batched_v3(session=session, run=run, binding=binding, state=global_state, snapshot_id=snapshot_id,
            phase=phase, call=call, checkpoint=checkpoint, window_context=virtual_context)
        _review_batched_v3(run=run, binding=binding, state=global_state, phase=phase, call=call,
            window_context=virtual_context, contexts=contexts,
            norm_images=_critic_norm_images(session, run, store, binding, virtual_context["policy"]))
        next(row for row in global_state["procedures"] if row["id"] == "report_generation").update(status="completed")
        incomplete = deferred or any(row["status"] in {"partial", "unavailable", "failed", "skipped"}
                                    for row in global_state["procedures"])
        global_state["status"] = "partial" if incomplete else "completed"
        global_state.pop("reason", None)
        global_state["report"] = {"status": global_state["status"], "preliminary": True,
            "observation_count": len(global_state["observations"]),
            "coverage": deepcopy(global_state["coverage"]),
            "expert_decisions_written": False, "canonical_findings_unchanged": True}
        persist()
    except (DomainError, ValueError, TypeError, KeyError) as error:
        if isinstance(error, DomainError) and error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
            raise
        reason = getattr(error, "detail_fields", {}).get("reason") if isinstance(error, DomainError) else _reply_refusal_code(error)
        reason = str(reason or "global_cross_window_failed")
        global_state.update(status="failed", reason=reason)
        global_state.setdefault("report", {}).update(status="failed", reason=reason)
        global_state.setdefault("warnings", []).append(reason)
        state["warnings"].append(reason)
        for procedure in global_state["procedures"]:
            if procedure["status"] == "running": procedure.update(status="failed", reason=reason)
            elif procedure["status"] == "queued": procedure.update(status="skipped", reason="dependency_failed")
        if active is not None:
            for receipt in global_state.get("batches", []):
                if receipt.get("status") == "running": receipt.update(status="failed", reason=reason)
                elif receipt.get("status") == "queued": receipt.update(status="skipped", reason="dependency_failed")
        persist()


# ---------------------------------------------------------------------------------------------
# One list (`F8-PUBLISH`, ADR-0029 decision 7, plan-v5 section 4): the saved candidates, read as groups for the publisher
# ---------------------------------------------------------------------------------------------

_BLOCK_SOURCE_ID = re.compile(r"blk_[0-9a-f]{32}")
#: A candidate's source that is a restatement of a text finding: plan v3 names it ``primary_text_<key>``, plan v2 ``text:<index>``.
_PRIMARY_TEXT_SOURCE_ID = re.compile(r"primary_text_[0-9a-f]+|text:[0-9]+")
_COMPLETE_STATUSES = frozenset({"completed", "partial"})
_CONSOLIDATION_VERSION = "strict-cross-window-v1"
_MAX_TEXT = 4000
_REFINING_ACTION = "propose_revision"


def _source_registry(result: dict) -> tuple[dict, set]:
    """Every source row of the saved result by ``source_id`` (the result's own, then each window's), and the ids saved under two shapes."""
    rows = list(result.get("sources") or [])
    for window in result.get("windows") or []:
        if isinstance(window, dict):
            rows.extend(window.get("sources") or [])
    registry: dict = {}
    conflicts: set = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("source_id"), str):
            continue
        known = registry.setdefault(row["source_id"], row)
        if known != row:
            conflicts.add(row["source_id"])
    return registry, conflicts


def _primary_ordinals(result: dict, text_observations) -> dict:
    """``source_id -> observation_ordinal`` of the text observation each primary-text source restates.

    Plan v2 numbers its sources ``text:<index>`` by the position in the saved text observations; plan v3 names them ``primary_text_<key>``
    and keeps the original observation on the candidate that carries the key. A source that cannot be named is absent, and the candidate
    then counts it as a primary source without a link (it is still never published twice).
    """
    ordinals: dict = {}
    for item in result.get("observations") or []:
        if not isinstance(item, dict):
            continue
        key, original = item.get("primary_observation_key"), item.get("original_primary_observation")
        if isinstance(key, str) and isinstance(original, dict) and type(original.get("observation_ordinal")) is int:
            ordinals["primary_text_" + key] = original["observation_ordinal"]
    entries = text_observations.get("observations") if isinstance(text_observations, dict) else None
    for index, entry in enumerate(entries if isinstance(entries, list) else []):
        if isinstance(entry, dict) and type(entry.get("observation_ordinal")) is int:
            ordinals[f"text:{index}"] = entry["observation_ordinal"]
    return ordinals


def _candidate_words(item: dict) -> str | None:
    """The finding text of a candidate: its title over its description, within the column's 4000 characters; ``None`` when it has none."""
    title = item.get("title") if isinstance(item.get("title"), str) else ""
    description = item.get("description") if isinstance(item.get("description"), str) else ""
    title, description = title.strip(), description.strip()
    words = description if not title or description.startswith(title) else (f"{title}\n\n{description}" if description else title)
    return words if 1 <= len(words) <= _MAX_TEXT else None


def _candidate_refinement(item: dict) -> str | None:
    """The corrector's refinement of the candidate's description, when it proposed a revision with words of its own."""
    correction = item.get("correction")
    if not isinstance(correction, dict) or correction.get("action") != _REFINING_ACTION:
        return None
    proposed = correction.get("candidate")
    words = proposed.get("description") if isinstance(proposed, dict) else None
    words = words.strip() if isinstance(words, str) else ""
    return words if 1 <= len(words) <= _MAX_TEXT else None


def _candidate_member(item, *, registry: dict, conflicts: set, ordinals: dict, reviewable=False) -> CandidateMember | None:
    """One saved candidate as the publisher's member, or ``None`` when it cannot be one (no identity of 1 to 128 characters, no words)."""
    ref = item.get("observation_id") if isinstance(item, dict) else None
    if not isinstance(ref, str) or not 1 <= len(ref) <= 128:
        return None
    words = _candidate_words(item)
    if words is None:
        return None
    blocks: list = []
    primary: list = []
    native: list = []
    unlinked = other = 0
    seen: set = set()
    for source_id in item.get("source_ids") if isinstance(item.get("source_ids"), list) else []:
        if not isinstance(source_id, str) or source_id in seen:
            continue
        seen.add(source_id)
        row = registry.get(source_id)
        if (_BLOCK_SOURCE_ID.fullmatch(source_id) and row is not None and row.get("kind") == "image"
                and source_id not in conflicts and type(row.get("page_number")) is int and row["page_number"] >= 1):
            digest = row.get("crop_sha256")
            blocks.append(BlockEvidenceItem(evidence_ordinal=len(blocks), page_number=row["page_number"],
                portal_block_id=source_id, crop_sha256=digest if isinstance(digest, str) else ""))
        elif _PRIMARY_TEXT_SOURCE_ID.fullmatch(source_id):
            if source_id in ordinals:
                primary.append(ordinals[source_id])
            else:
                unlinked += 1
        else:
            other += 1
            if row is not None and row.get("kind") == "text" and type(row.get("page_number")) is int:
                # Prefer a literal quote actually reviewed by the critic. A
                # long native source is not shortened to a guessed prefix.
                quotes = [e.get("quote") for e in item.get("critic", {}).get("source_evidence", [])
                    if isinstance(e, dict) and e.get("source_id") == source_id]
                quotes.extend([row.get("quote")])
                for quote in quotes:
                    if isinstance(quote, str) and 1 <= len(quote) <= 2000 and quote.strip():
                        native.append((row["page_number"], quote)); break
    window_id = item.get("window_id")
    original = item.get("original_primary_observation")
    recommendation = item.get("recommendation_text")
    if (reviewable and len(set(primary)) == 1 and not blocks and not other and not unlinked
            and isinstance(original, dict)):
        # The existing text publisher owns this exact observation. Its finding
        # text excludes the category heading used by the preliminary UI row.
        # Preserve the same immutable content for replay/tamper verification.
        actual = original.get("finding_text")
        if isinstance(actual, str) and actual.strip() and len(actual) <= _MAX_TEXT:
            words = actual
        if recommendation is None and isinstance(original.get("recommendation_text"), str):
            recommendation = original["recommendation_text"]
    return CandidateMember(
        extended_observation_ref=ref, finding_text=words, block_evidence=tuple(blocks),
        refined_recommendation=_candidate_refinement(item), primary_text_ordinals=tuple(dict.fromkeys(primary)),
        native_sources=tuple(dict.fromkeys(native)),
        proposed_severity=item.get("proposed_severity"),
        proposed_recommendation=recommendation,
        primary_text_unlinked=unlinked, other_source_count=other,
        window_id=window_id if isinstance(window_id, str) else None,
        cross_window=item.get("origin_scope") == "global_cross_window" or window_id == "global-cross-window")


def read_candidate_groups(document: dict, *, run_id: str, version_uid: str,
        text_observations=None) -> tuple[tuple[CandidateGroup, ...], tuple[str, ...]]:
    """The groups of the strict consolidation of a saved ``analysis.extended_review`` document, as the publisher of groups takes them.

    Returns ``(groups, unread)``: ``unread`` says why nothing could be read (the review did not complete, or the saved candidates cannot be
    consolidated), never an empty answer without a reason. A document of another run or version is corruption, refused like
    :func:`read_extended_review` refuses it. A candidate that cannot be a member (no identity, no words) is left out of its group and counted
    in ``unread`` as ``candidate_invalid``; nothing is repaired, and no source is guessed: a source that is not a block of the run's geometry
    stays a source the candidate is counted as standing on, never evidence.

    The groups are those the saved result carries (plan v3) or that the consolidation computes over its observations and sources now (plan
    v2); the first member of a group is the first one in the saved order.
    """
    try:
        if (document.get("artifact_role") != EXTENDED_REVIEW_ROLE or document.get("run_id") != run_id
                or document.get("version_uid") != version_uid or not isinstance(document.get("result"), dict)):
            raise ValueError()
        status, result = document["status"], document["result"]
    except (ValueError, KeyError, AttributeError):
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=EXTENDED_REVIEW_ROLE) from None
    if status not in _COMPLETE_STATUSES:
        return (), ("extended_review_not_complete",)
    consolidation = result.get("consolidation")
    if not (isinstance(consolidation, dict) and consolidation.get("version") in {_CONSOLIDATION_VERSION, "v2-flow-repair-v1"}
            and isinstance(result.get("consolidated_observations"), list)):
        result = _attach_consolidation(dict(result), version_uid=version_uid)
        consolidation = result["consolidation"]
    if not isinstance(consolidation, dict) or consolidation.get("complete") is not True:
        return (), ("consolidation_unavailable",)
    observations = result.get("observations") if isinstance(result.get("observations"), list) else []
    registry, conflicts = _source_registry(result)
    ordinals = _primary_ordinals(result, text_observations)
    groups: list = []
    unread: list = []
    for group in result["consolidated_observations"]:
        members: list = []
        for origin in group.get("origin_records", []) if isinstance(group, dict) else []:
            index = origin.get("raw_index") if isinstance(origin, dict) else None
            member = (_candidate_member(observations[index], registry=registry, conflicts=conflicts, ordinals=ordinals,
                reviewable="flow_repair_policy" in result)
                if type(index) is int and 0 <= index < len(observations) else None)
            if member is None:
                unread.append("candidate_invalid")
            else:
                members.append(member)
        if members and isinstance(group.get("group_id"), str) and group["group_id"]:
            groups.append(CandidateGroup(group_id=group["group_id"], members=tuple(members)))
    return tuple(groups), tuple(unread)
