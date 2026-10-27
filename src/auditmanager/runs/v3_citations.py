"""Unserved bridge from a Run's verified norm-set Blob to AR v3 citations.

This prepares material and publication candidates. It never dispatches a model,
claims provider provenance, writes a StageResult or publishes a finding.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    BetaSourcePolicyRefused,
    BlockIndex,
    LocalV3Evaluation,
    RecognisedContext,
    SuppliedV3Response,
    TextLayer,
    V3RequestCandidate,
    evaluate_v3_supplied_response,
    load_beta_source_policy,
    parse_v3_set_input,
    prepare_v3_scoped_request_candidate,
    V3SetInputRefused,
)
from auditmanager.findings.public import (
    CitationEvidence,
    V3PublicationCandidate,
    VerifiedRetrievalSetInput,
    load_verified_retrieval_set,
)
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.norms.public import GroundedNormCitation
from auditmanager.runs.repository import RunRow
from auditmanager.storage.public import BlobStore


class V3CorpusCitationRefused(ValueError):
    """The saved Run, verified set and intended v3 profile do not agree."""


@dataclass(frozen=True, slots=True)
class PinnedV3CorpusRequest:
    run_id: str
    profile_id: str
    bundle_id: str
    scope_id: str
    composition_sha256: str
    verified_set: VerifiedRetrievalSetInput
    recognised_context: tuple[RecognisedContext, ...]
    candidate: V3RequestCandidate


@dataclass(frozen=True, slots=True)
class V3CorpusCitationPlan:
    request: PinnedV3CorpusRequest
    evaluation: LocalV3Evaluation
    normative_candidates: tuple[V3PublicationCandidate, ...]


@dataclass(frozen=True, slots=True)
class V3BetaTopicReview:
    item_id: str
    mode: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class V3BetaCitationReview:
    """Diagnostic-only beta review; it carries no publication candidates."""

    request: PinnedV3CorpusRequest
    evaluation: LocalV3Evaluation
    source_policy_sha256: str
    scenario: str
    numeric_output_policy: str
    topics: tuple[V3BetaTopicReview, ...]
    provisional_proposal_ordinals: tuple[int, ...]
    withheld_proposal_ordinals: tuple[int, ...]


PROVISIONAL_MODE = "provisional_citation"


@dataclass(frozen=True, slots=True)
class V3PromptRows:
    """Which item sends which paragraph, and under which label, in a set's prompt part.

    This is the item membership the model was shown: an item's rows are its reviewed target rows
    plus the retrieved-window rows the set selected for it. The set bytes do not say which rows
    are targets and which are windows, so a row of either kind is a row of the item.
    """

    label_items: Mapping[str, str]
    paragraph_items: Mapping[str, frozenset[str]]


def index_prompt_rows(rows: object) -> V3PromptRows:
    """Index the rows of a set's ``prompt_part`` by label and by paragraph.

    ``parse_v3_set_input`` has already proved the shape for the rows the classifier reads; the
    artifact builder reads the same bytes again and relies on this to refuse a damaged copy.
    """
    if not isinstance(rows, list):
        raise V3CorpusCitationRefused("beta_set_labels_invalid")
    label_items: dict[str, str] = {}
    paragraph_items: dict[str, set[str]] = {}
    for row in rows:
        if (not isinstance(row, dict)
                or not all(isinstance(row.get(key), str) and row[key]
                           for key in ("label", "item_id", "norm_paragraph_id"))
                or row["label"] in label_items):
            raise V3CorpusCitationRefused("beta_set_labels_invalid")
        label_items[row["label"]] = row["item_id"]
        paragraph_items.setdefault(row["norm_paragraph_id"], set()).add(row["item_id"])
    return V3PromptRows(
        label_items, {key: frozenset(value) for key, value in paragraph_items.items()},
    )


def grounded_citations_are_provisional(
    proposed_labels: Sequence[str], grounded: Sequence[GroundedNormCitation], *,
    rows: V3PromptRows, modes: Mapping[str, str],
) -> bool:
    """Whether every citation of a proposal rests on a paragraph the beta policy lets be cited.

    A citation is judged by the paragraph it was **grounded** to (``GroundedNormCitation``), not by
    the label the model wrote: ``ground_norm_observation`` may *rebind* a quote that is not in the
    labelled paragraph to the one other reliable paragraph of the same document that holds it, and
    that paragraph can be a context-only one or one that no item sent. A proposal is provisional
    only if, for each of its citations:

    * the labelled item is ``provisional_citation``;
    * the grounded paragraph is a row of at least one item, and **every** item that sends it is
      ``provisional_citation`` (a paragraph a context-only item also sends is a context-only
      span whatever label was used);
    * a ``rebound`` citation lands on a row of the **labelled** item. A rebound into another
      topic's paragraph, provisional or not, is withheld: the label names the topic and the
      quote does not ground it, and the system does not re-attribute a finding to another topic.

    Anything else withholds the whole proposal (the existing ``context_only_or_mixed_source``
    disposition; no new wire value). Unknown labels, a labels/grounding mismatch and an unknown
    state are refusals, never a quiet classification.
    """
    if len(proposed_labels) != len(grounded):
        raise V3CorpusCitationRefused("beta_citation_grounding_mismatch")
    provisional = True
    for label, citation in zip(proposed_labels, grounded):
        if citation.label != label:
            raise V3CorpusCitationRefused("beta_citation_grounding_mismatch")
        if citation.state not in {"verified", "rebound"}:
            raise V3CorpusCitationRefused("beta_citation_state_invalid")
        item_id = rows.label_items.get(label)
        if item_id is None or item_id not in modes:
            raise V3CorpusCitationRefused("beta_citation_label_invalid")
        carriers = rows.paragraph_items.get(citation.paragraph_id, frozenset())
        if (modes[item_id] != PROVISIONAL_MODE
                or not carriers
                or any(modes.get(carrier) != PROVISIONAL_MODE for carrier in carriers)
                or (citation.state == "rebound" and item_id not in carriers)):
            provisional = False
    return provisional


def _require_binding(
    run: RunRow, verified: VerifiedRetrievalSetInput, text_layer: TextLayer, *,
    profile_id: str, bundle_id: str, map_sha256: str,
) -> None:
    if (
        not isinstance(run, RunRow)
        or not isinstance(verified, VerifiedRetrievalSetInput)
        or not isinstance(text_layer, TextLayer)
        or run.state not in {"running", "validating"}
        or run.run_id != verified.run_id
        or run.version_uid != text_layer.version_uid
        or run.norms_snapshot_id != verified.norms_snapshot_id
        or run.norm_retrieval_set_id != verified.norm_retrieval_set_id
        or run.analysis_profile_id != profile_id
        or run.prompt_bundle_id != bundle_id
        or not isinstance(map_sha256, str)
        or len(map_sha256) != 64
        or verified.map_sha256 != map_sha256
    ):
        raise V3CorpusCitationRefused("run_set_profile_binding_invalid")


def prepare_v3_corpus_request(
    session: Session, *, run: RunRow, authority: AttemptAuthority,
    blob_store: BlobStore, text_layer: TextLayer, profile_id: str,
    bundle_id: str, map_sha256: str, scope_id: str,
    composition_sha256: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
    lock_authority: bool = True,
) -> PinnedV3CorpusRequest:
    """Read confirmed DB/Blob custody and send only its selected norm rows.

    Profile, bundle, map, scope and composition must come from a trusted
    reviewed pack. The later provider boundary must recheck current Attempt
    and budget before any external effect.
    """
    if (not isinstance(run, RunRow)
            or not isinstance(authority, AttemptAuthority)
            or authority.run_id != run.run_id):
        raise V3CorpusCitationRefused("attempt_run_mismatch")
    verified = load_verified_retrieval_set(
        session, authority=authority, blob_store=blob_store,
        lock_authority=lock_authority,
    )
    _require_binding(
        run, verified, text_layer, profile_id=profile_id,
        bundle_id=bundle_id, map_sha256=map_sha256,
    )
    candidate = prepare_v3_scoped_request_candidate(
        text_layer, verified.data, expected_version_uid=run.version_uid,
        expected_set_sha256=verified.set_sha256,
        expected_snapshot_id=verified.norms_snapshot_id,
        expected_map_sha256=verified.map_sha256,
        scope_id=scope_id,
        expected_composition_sha256=composition_sha256,
        recognised_context=recognised_context,
    )
    return PinnedV3CorpusRequest(
        run_id=run.run_id, profile_id=profile_id, bundle_id=bundle_id,
        scope_id=scope_id, composition_sha256=composition_sha256,
        verified_set=verified, recognised_context=recognised_context,
        candidate=candidate,
    )


def plan_v3_corpus_citations(
    request: PinnedV3CorpusRequest, response: SuppliedV3Response,
    text_layer: TextLayer, *, block_index: BlockIndex | None = None,
) -> V3CorpusCitationPlan:
    """Ground a supplied answer against the request's exact saved set bytes.

    The result remains untrusted for publication until the caller checks the
    saved model call/effect, current Attempt and CITE stage in one transaction.
    """
    if not isinstance(request, PinnedV3CorpusRequest):
        raise V3CorpusCitationRefused("pinned_request_required")
    if (request.run_id != request.verified_set.run_id
            or request.candidate.scope_id != request.scope_id
            or request.candidate.composition_sha256 != request.composition_sha256
            or request.candidate.norms_snapshot_id != request.verified_set.norms_snapshot_id
            or request.candidate.map_sha256 != request.verified_set.map_sha256
            or request.candidate.set_sha256 != request.verified_set.set_sha256):
        raise V3CorpusCitationRefused("pinned_request_set_mismatch")
    evaluation = evaluate_v3_supplied_response(
        request.candidate, response, text_layer, request.verified_set.data,
        recognised_context=request.recognised_context,
        block_index=block_index,
    )
    candidates: list[V3PublicationCandidate] = []
    for accepted in evaluation.grounding.accepted:
        if not accepted.norm_citations:
            continue
        candidates.append(_publication_candidate(accepted))
    return V3CorpusCitationPlan(request, evaluation, tuple(candidates))


def _publication_candidate(accepted: Any) -> V3PublicationCandidate:
    """The adapter boundary after both pure gates, with no model authority.

    ``accepted`` is one element of ``LocalV3Evaluation.grounding.accepted`` (``proposal``,
    ``evidence``, ``norm_citations``); the type lives in the analysis internals and is not
    exported, so it is read structurally.
    """
    proposal = accepted.proposal
    if proposal.required_value is None or proposal.stated_value is None:
        raise V3CorpusCitationRefused("normative_value_missing")
    return V3PublicationCandidate(
        category=proposal.category,
        finding_text=proposal.finding_text,
        recommendation_text=proposal.recommendation_text,
        proposed_severity=proposal.proposed_severity,
        evidence=tuple(CitationEvidence(
            anchor.page_number, anchor.quote, anchor.char_start,
            anchor.char_end, anchor.block_id,
        ) for anchor in accepted.evidence),
        norm_citations=accepted.norm_citations,
        required_value=proposal.required_value,
        stated_value=proposal.stated_value,
    )


def provisional_publication_candidates(
    review: V3BetaCitationReview,
) -> tuple[V3PublicationCandidate, ...]:
    """The publication candidates of the proposals the beta review marked provisional.

    A proposal is provisional when it passed both pure gates (it is in ``grounding.accepted``)
    and every citation it makes is of a ``provisional_citation`` topic (it is in
    ``provisional_proposal_ordinals``). A withheld (context-only or mixed) proposal, a rejected
    one and an accepted non-normative one yield no candidate. The result is in proposal order.
    """
    if not isinstance(review, V3BetaCitationReview):
        raise V3CorpusCitationRefused("beta_review_required")
    accepted_by_ordinal = {item.proposal_ordinal: item for item in review.evaluation.grounding.accepted}
    ordinals = review.provisional_proposal_ordinals
    if (len(set(ordinals)) != len(ordinals)
            or set(ordinals) & set(review.withheld_proposal_ordinals)
            or any(ordinal not in accepted_by_ordinal for ordinal in ordinals)):
        raise V3CorpusCitationRefused("provisional_ordinal_not_accepted")
    return tuple(_publication_candidate(accepted_by_ordinal[ordinal]) for ordinal in sorted(ordinals))


def plan_v3_beta_citation_review(
    request: PinnedV3CorpusRequest, response: SuppliedV3Response,
    text_layer: TextLayer, *, block_index: BlockIndex | None = None,
) -> V3BetaCitationReview:
    """Classify a grounded v3 response against the frozen F1.3 beta policy.

    A provisional citation is still an expert-review suggestion. Context-only
    topics, observations mixing them with provisional labels, and observations
    whose quote was grounded (rebound) to a paragraph the policy does not let be
    cited are withheld: the paragraph a citation was grounded to decides, not the
    label (``grounded_citations_are_provisional``). The returned object
    deliberately has no publication-candidate field.
    """
    if not isinstance(request, PinnedV3CorpusRequest):
        raise V3CorpusCitationRefused("pinned_request_required")
    try:
        policy = load_beta_source_policy()
        if (request.verified_set.norms_snapshot_id != policy.snapshot_id
                or request.composition_sha256 != policy.composition_sha256
                or request.candidate.item_ids != tuple(
                    item.item_id for item in policy.group(request.scope_id)
                )):
            raise V3CorpusCitationRefused("beta_policy_scope_mismatch")
        selected = parse_v3_set_input(
            request.verified_set.data,
            expected_sha256=request.verified_set.set_sha256,
            expected_snapshot_id=policy.snapshot_id,
            expected_map_sha256=request.verified_set.map_sha256,
        )
        if selected.selected_item_ids != request.candidate.item_ids:
            raise V3CorpusCitationRefused("beta_set_items_mismatch")
        prompt_rows = index_prompt_rows(json.loads(selected.prompt_part)["paragraphs"])
    except (BetaSourcePolicyRefused, V3SetInputRefused,
            json.JSONDecodeError, KeyError, TypeError) as exc:
        raise V3CorpusCitationRefused("beta_policy_or_set_invalid") from exc
    plan = plan_v3_corpus_citations(
        request, response, text_layer, block_index=block_index,
    )
    modes = {item.item_id: item.mode for item in policy.group(request.scope_id)}
    provisional: list[int] = []
    withheld: list[int] = []
    for accepted in plan.evaluation.grounding.accepted:
        if not accepted.norm_citations:
            continue
        citations = accepted.proposal.norm_citations
        if citations is None:
            raise V3CorpusCitationRefused("beta_normative_citations_missing")
        if grounded_citations_are_provisional(
            tuple(citation.label for citation in citations), accepted.norm_citations,
            rows=prompt_rows, modes=modes,
        ):
            provisional.append(accepted.proposal_ordinal)
        else:
            withheld.append(accepted.proposal_ordinal)
    return V3BetaCitationReview(
        request, plan.evaluation, policy.sha256, policy.scenario,
        policy.numeric_output_policy,
        tuple(V3BetaTopicReview(item.item_id, item.mode, item.reason, item.source_ids)
              for item in policy.group(request.scope_id)),
        tuple(provisional), tuple(withheld),
    )


__all__ = [
    "PROVISIONAL_MODE", "PinnedV3CorpusRequest", "V3BetaCitationReview", "V3BetaTopicReview",
    "V3CorpusCitationPlan", "V3CorpusCitationRefused", "V3PromptRows",
    "grounded_citations_are_provisional", "index_prompt_rows",
    "prepare_v3_corpus_request", "plan_v3_corpus_citations",
    "plan_v3_beta_citation_review", "provisional_publication_candidates",
]
