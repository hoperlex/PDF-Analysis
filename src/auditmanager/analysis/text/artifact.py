"""Building ``analysis.text_observations`` exactly as ``P02_SEAMS.md`` section 4.7
declares it.

This artifact is ``B4``'s **only** input; the gate takes no model input of any other
kind. So every invariant the gate relies on is checked here before the document is
written, not asserted in a comment:

* every observation carries at least one evidence item - an observation with none is
  malformed, not "ungrounded", and is rejected before the artifact exists;
* ``char_end - char_start`` equals the code-point length of ``quote``;
* the interval lies inside the declared page's interval, and the document-global
  sequence sliced at it equals the quote exactly;
* ``pages_analysed`` is a strict subset of the document's pages precisely when the
  stage reports ``partial``.

``observation_ordinal`` and ``evidence_ordinal`` are positions inside this artifact
and are **not identities**. ``finding_uid`` and ``finding_observation_id`` are
allocated by ``B4`` at publication and appear nowhere here. Neither does a verdict:
the model proposes, a human decides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Sequence

from auditmanager.analysis.text.anchors import ResolvedAnchor
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.analysis.text.profile import AnalysisProfile
from auditmanager.analysis.text.textlayer import TextLayer
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId

ARTIFACT_ROLE: Final[str] = "analysis.text_observations"
ARTIFACT_VERSION: Final[str] = "1.0.0"


def _malformed(reason: str, message: str) -> DomainError:
    """A refusal to write a malformed artifact. Carries no document text."""
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message=message,
        stage_id=STAGE_ID,
        reason=reason,
    )


@dataclass(frozen=True, slots=True)
class Observation:
    """One grounded proposal, ready to be written into the artifact."""

    category: str
    finding_text: str
    recommendation_text: str
    model_call_id: ModelCallId
    evidence: tuple[ResolvedAnchor, ...]


def build_text_observations(
    *,
    run_id: RunId,
    profile: AnalysisProfile,
    provider_mode: ProviderMode,
    text_layer: TextLayer,
    pages_analysed: Sequence[int],
    observations: Sequence[Observation],
) -> dict[str, Any]:
    """Validate and render the artifact document."""
    known_pages = set(text_layer.page_numbers)
    analysed = sorted(set(pages_analysed))
    if not set(analysed) <= known_pages:
        raise _malformed(
            "pages_analysed_unknown", "pages_analysed names a page the text layer does not carry"
        )

    rendered: list[dict[str, Any]] = []
    for observation_ordinal, observation in enumerate(observations):
        if not observation.evidence:
            raise _malformed(
                "observation_without_evidence",
                "an observation carries no evidence and cannot be written",
            )
        if observation.category not in profile.categories:
            raise _malformed(
                "category_not_declared",
                "an observation carries a category the analysis profile does not declare",
            )
        evidence: list[dict[str, Any]] = []
        for evidence_ordinal, anchor in enumerate(observation.evidence):
            _validate_anchor(text_layer, anchor)
            item: dict[str, Any] = {
                "evidence_ordinal": evidence_ordinal,
                "page_number": anchor.page_number,
                "quote": anchor.quote,
                "char_start": anchor.char_start,
                "char_end": anchor.char_end,
            }
            if anchor.block_id is not None:
                item["block_id"] = anchor.block_id
            evidence.append(item)
        rendered.append(
            {
                "observation_ordinal": observation_ordinal,
                "category": observation.category,
                "finding_text": observation.finding_text,
                "recommendation_text": observation.recommendation_text,
                "model_call_id": str(observation.model_call_id),
                "evidence": evidence,
            }
        )

    return {
        "artifact_role": ARTIFACT_ROLE,
        "artifact_version": ARTIFACT_VERSION,
        "run_id": str(run_id),
        "stage_id": STAGE_ID,
        "analysis_profile_id": str(profile.analysis_profile_id),
        "prompt_bundle_id": str(profile.prompt_bundle.prompt_bundle_id),
        "provider_mode": provider_mode.value,
        "pages_analysed": analysed,
        "observations": rendered,
    }


def _validate_anchor(text_layer: TextLayer, anchor: ResolvedAnchor) -> None:
    """Re-check the three things ``B4`` will re-check, before writing them out."""
    page = text_layer.page(anchor.page_number)
    if page is None:
        raise _malformed("evidence_page_unknown", "an evidence item cites a page that does not exist")
    if anchor.char_end - anchor.char_start != len(anchor.quote):
        # len() counts code points. A byte-derived span fails here.
        raise _malformed(
            "evidence_span_length_mismatch",
            "an evidence span does not match its quotation length in code points",
        )
    if not page.contains(anchor.char_start, anchor.char_end):
        raise _malformed(
            "evidence_span_outside_page", "an evidence span lies outside its declared page"
        )
    if text_layer.slice(anchor.char_start, anchor.char_end) != anchor.quote:
        raise _malformed(
            "evidence_quotation_mismatch",
            "an evidence span does not resolve to its own quotation",
        )
