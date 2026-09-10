"""``Finding``, ``FindingDetail``, ``FindingObservation``, ``Evidence``, provenance.

``FindingDetail`` restates ``Finding`` rather than composing it with ``allOf``. That is
not a style choice: under JSON Schema 2020-12 an ``additionalProperties: false`` is
evaluated against its own schema object's property annotations only, so an ``allOf``
branch over the closed ``Finding`` would reject the two properties the sibling branch
adds. The frozen document says so in ``FindingDetail.description``, and
``tests/contract/api_v1/test_finding_detail_composition.py`` -- the contract repair this
programme already made -- pins it. These view types mirror that: two closed shapes, the
detail one carrying exactly ``latest_comment`` and ``decision_event_count`` extra.

Everything listed here is **grounded**. An ungrounded model item is not a finding, has
no ``finding_uid``, appears in no finding query and reaches no response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from auditmanager.api.schemas.common import timestamp

__all__ = [
    "EvidenceView",
    "FindingDetailView",
    "FindingView",
    "ObservationView",
    "ProvenanceView",
    "finding_body",
    "finding_detail_body",
]

#: ``#/components/schemas/FindingCategory`` -- the only two questions PC-01 answers.
FINDING_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"internal_contradiction", "explicit_placeholder"}
)

#: ``#/components/schemas/Verdict``.
VERDICTS: Final[frozenset[str]] = frozenset(
    {"pending", "accepted", "rejected", "needs_manual_review"}
)


@dataclass(frozen=True, slots=True)
class EvidenceView:
    """Exactly the frozen ``Evidence``. Offsets are Unicode code points (§4.1)."""

    evidence_ordinal: int
    page_number: int
    quote: str
    char_start: int
    char_end: int
    block_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceView:
    """Exactly the frozen ``ObservationProvenance``.

    Checksums and identities only: never the prompt, the request or the response body.
    """

    stage_id: str
    analysis_profile_id: str
    prompt_bundle_id: str
    provider_mode: str
    model_call_id: str | None = None
    model_identity: str | None = None


@dataclass(frozen=True, slots=True)
class ObservationView:
    """Exactly the frozen ``FindingObservation``."""

    finding_observation_id: str
    run_id: str
    category: str
    finding_text: str
    recommendation_text: str
    evidence: tuple[EvidenceView, ...]
    provenance: ProvenanceView


@dataclass(frozen=True, slots=True)
class FindingView:
    """Exactly the frozen ``Finding``."""

    finding_uid: str
    project_uid: str
    version_uid: str
    run_id: str
    category: str
    observation: ObservationView
    current_verdict: str
    latest_decision_id: str | None = None
    decision_recorded_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FindingDetailView:
    """``Finding``'s property set plus exactly ``latest_comment`` and the event count."""

    finding: FindingView
    latest_comment: str | None = None
    decision_event_count: int = 0


def evidence_body(view: EvidenceView) -> dict[str, Any]:
    body: dict[str, Any] = {
        "evidence_ordinal": view.evidence_ordinal,
        "page_number": view.page_number,
        "quote": view.quote,
        "char_start": view.char_start,
        "char_end": view.char_end,
    }
    if view.block_id is not None:
        body["block_id"] = view.block_id
    return body


def provenance_body(view: ProvenanceView) -> dict[str, Any]:
    body: dict[str, Any] = {
        "stage_id": view.stage_id,
        "analysis_profile_id": view.analysis_profile_id,
        "prompt_bundle_id": view.prompt_bundle_id,
        "provider_mode": view.provider_mode,
    }
    # Both are `oneOf [<id>, null]`, so an explicit null is valid and says "this
    # observation had no model call" rather than "the field was forgotten".
    body["model_call_id"] = view.model_call_id
    if view.model_identity is not None:
        body["model_identity"] = view.model_identity
    return body


def observation_body(view: ObservationView) -> dict[str, Any]:
    return {
        "finding_observation_id": view.finding_observation_id,
        "run_id": view.run_id,
        "category": view.category,
        "finding_text": view.finding_text,
        "recommendation_text": view.recommendation_text,
        "evidence": [evidence_body(item) for item in view.evidence],
        "provenance": provenance_body(view.provenance),
    }


def finding_body(view: FindingView) -> dict[str, Any]:
    return {
        "finding_uid": view.finding_uid,
        "project_uid": view.project_uid,
        "version_uid": view.version_uid,
        "run_id": view.run_id,
        "category": view.category,
        "observation": observation_body(view.observation),
        "current_verdict": view.current_verdict,
        "latest_decision_id": view.latest_decision_id,
        "decision_recorded_at": (
            None
            if view.decision_recorded_at is None
            else timestamp(view.decision_recorded_at)
        ),
    }


def finding_detail_body(view: FindingDetailView) -> dict[str, Any]:
    body = finding_body(view.finding)
    body["latest_comment"] = view.latest_comment
    body["decision_event_count"] = view.decision_event_count
    return body
