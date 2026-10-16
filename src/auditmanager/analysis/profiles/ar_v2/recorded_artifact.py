"""Build deterministic AR v2 recorded observations without publishing them.

The bytes use the existing ``analysis.text_observations`` role so the later
grounding gate can read accepted evidence. Rejected proposals are diagnostics,
never observations. A later stage owner publishes these bytes and constructs
its own StageResult and call journal in one durable workflow.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)
from auditmanager.analysis.profiles.ar_v2 import prompt_material, registered
from auditmanager.analysis.profiles.ar_v2.grounding import REASON_RECOGNISED_ONLY
from auditmanager.analysis.profiles.ar_v2.merge_input import prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    GroundedProposal, ProposalGroundingResult, RejectedProposal, UnresolvedEvidence,
)
from auditmanager.analysis.profiles.ar_v2.response import ProposedEvidence, ProposedObservation
from auditmanager.analysis.profiles.ar_v2.recorded_input import (
    PdfPageSource,
    RecordedV2Input,
)
from auditmanager.analysis.profiles.ar_v2.recorded_response import RecordedReplayResult
from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES, SEVERITIES
from auditmanager.analysis.stages.finding_merge import MergeEvidence, MergeObservation
from auditmanager.analysis.text.anchors import (
    REASON_ABSENT, REASON_DIFFERENT_PAGE, REASON_LENGTH_MISMATCH,
    REASON_SPAN_OUTSIDE_PAGE, ResolvedAnchor,
)
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId, VersionUid
from auditmanager.storage.public import BlobStore, derive_blob_id, parse_blob_id


ARTIFACT_ROLE: Final[str] = "analysis.text_observations"
ARTIFACT_VERSION: Final[str] = "2.0.0"
STAGE_ID: Final[str] = "text_analysis"


class RecordedArtifactError(ValueError):
    """A replay cannot be represented as a grounded recorded artifact."""


@dataclass(frozen=True, slots=True)
class BuiltRecordedArtifact:
    """Immutable bytes and Blob metadata; no Blob identity is allocated here."""

    payload: bytes
    sha256: str
    role: str = ARTIFACT_ROLE
    version: str = ARTIFACT_VERSION
    media_type: str = ARTIFACT_MEDIA_TYPE

    @property
    def size_bytes(self) -> int:
        return len(self.payload)


@dataclass(frozen=True, slots=True)
class RecordedMergeInput:
    """The complete grounded projection read from one sealed observation Blob."""

    observations: tuple[MergeObservation, ...]
    source_proposal_ordinals: tuple[int, ...]
    text_artifact_sha256: str
    text_layer_ref: ArtifactRef
    recognised_ref: ArtifactRef | None
    grounding: ProposalGroundingResult
    model_id: str
    model_call_id: str
    request_sha256: str
    response_sha256: str
    source_binding_sha256: str


def _complete_observations(document: dict[str, object]) -> tuple[
    tuple[MergeObservation, ...], tuple[int, ...], tuple[GroundedProposal, ...],
]:
    pages = document.get("page_sources")
    analysed = document.get("pages_analysed")
    if not isinstance(pages, list) or not pages or not isinstance(analysed, list):
        raise RecordedArtifactError("recorded_page_sources_invalid")
    page_ranges: dict[int, tuple[int, int]] = {}
    next_start = 0
    for page in pages:
        if not isinstance(page, dict) or set(page) != {"page_number", "char_start", "char_end"}:
            raise RecordedArtifactError("recorded_page_sources_invalid")
        number, start, end = page["page_number"], page["char_start"], page["char_end"]
        if (type(number) is not int or type(start) is not int or type(end) is not int
                or number < 1 or number in page_ranges or start != next_start or end < start
                or (page_ranges and number <= max(page_ranges))):
            raise RecordedArtifactError("recorded_page_sources_invalid")
        page_ranges[number] = (start, end)
        next_start = end
    if analysed != list(page_ranges):
        raise RecordedArtifactError("recorded_page_coverage_invalid")

    raw = document.get("observations")
    if not isinstance(raw, list):
        raise RecordedArtifactError("recorded_observations_invalid")
    observations: list[MergeObservation] = []
    source_ordinals: list[int] = []
    accepted: list[GroundedProposal] = []
    for ordinal, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != {
            "observation_ordinal", "source_proposal_ordinal", "category",
            "finding_text", "recommendation_text", "proposed_severity",
            "model_call_id", "evidence",
        }:
            raise RecordedArtifactError("recorded_observations_invalid")
        source = item["source_proposal_ordinal"]
        if (type(item["observation_ordinal"]) is not int
                or item["observation_ordinal"] != ordinal
                or type(source) is not int or source < 0
                or source in source_ordinals
                or not isinstance(item["category"], str) or item["category"] not in CATEGORIES
                or not isinstance(item["proposed_severity"], str)
                or item["proposed_severity"] not in SEVERITIES
                or not isinstance(item["finding_text"], str)
                or not 1 <= len(item["finding_text"]) <= 4000
                or not item["finding_text"].strip()
                or not isinstance(item["recommendation_text"], str)
                or not 1 <= len(item["recommendation_text"]) <= 4000
                or not item["recommendation_text"].strip()
                or item["model_call_id"] != document["model_call_id"]):
            raise RecordedArtifactError("recorded_observations_invalid")
        raw_evidence = item["evidence"]
        if not isinstance(raw_evidence, list) or not raw_evidence:
            raise RecordedArtifactError("recorded_evidence_invalid")
        evidence: list[MergeEvidence] = []
        proposed_evidence: list[ProposedEvidence] = []
        anchors: list[ResolvedAnchor] = []
        for evidence_ordinal, value in enumerate(raw_evidence):
            if not isinstance(value, dict) or set(value) != {
                "evidence_ordinal", "page_number", "quote", "char_start", "char_end",
            }:
                raise RecordedArtifactError("recorded_evidence_invalid")
            page, start, end, quote = (
                value["page_number"], value["char_start"], value["char_end"], value["quote"]
            )
            if (type(value["evidence_ordinal"]) is not int
                    or value["evidence_ordinal"] != evidence_ordinal
                    or type(page) is not int or page not in page_ranges
                    or type(start) is not int or type(end) is not int
                    or not isinstance(quote, str) or not 1 <= len(quote) <= 2000
                    or not quote.strip()
                    or not page_ranges[page][0] <= start < end <= page_ranges[page][1]
                    or end - start != len(quote)):
                raise RecordedArtifactError("recorded_evidence_invalid")
            evidence.append(MergeEvidence(page, start, end, quote))
            proposed_evidence.append(ProposedEvidence(page, quote))
            anchors.append(ResolvedAnchor(page, quote, start, end))
        source_ordinals.append(source)
        observations.append(MergeObservation(ordinal, str(item["category"]), tuple(evidence)))
        accepted.append(GroundedProposal(
            source,
            ProposedObservation(
                item["category"], item["finding_text"],
                item["recommendation_text"], item["proposed_severity"],
                tuple(proposed_evidence),
            ),
            tuple(anchors),
        ))
    if source_ordinals != sorted(source_ordinals):
        raise RecordedArtifactError("recorded_source_ordinals_invalid")
    return tuple(observations), tuple(source_ordinals), tuple(accepted)


def read_recorded_merge_input(
    blob_store: BlobStore,
    reference: ArtifactRef,
    *,
    run_id: str,
    version_uid: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
) -> RecordedMergeInput:
    """Read exact v2 bytes for merge; never consult a fixture or provider."""
    if (not isinstance(reference, ArtifactRef) or reference.role != ARTIFACT_ROLE
            or reference.media_type != ARTIFACT_MEDIA_TYPE
            or reference.blob_id != str(derive_blob_id(
                sha256=reference.sha256, size=reference.size_bytes,
            ))):
        raise RecordedArtifactError("recorded_reference_invalid")
    run = _require_identity(run_id, RunId, "invalid_run_id")
    version = _require_identity(version_uid, VersionUid, "invalid_version_uid")
    profile = registered.resolve_recorded_profile(analysis_profile_id, prompt_bundle_id)
    try:
        payload = blob_store.read(parse_blob_id(reference.blob_id), verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - typed boundary for the declared Blob
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the saved recorded observation Blob could not be read",
            stage_id="finding_merge", reason="input_unreadable",
        ) from exc
    if len(payload) != reference.size_bytes or sha256_hex(payload) != reference.sha256:
        raise RecordedArtifactError("recorded_artifact_digest_mismatch")
    try:
        document = json.loads(payload)
        if not isinstance(document, dict) or canonical_bytes(document) != payload:
            raise ValueError
    except (UnicodeDecodeError, TypeError, ValueError):
        raise RecordedArtifactError("recorded_artifact_not_canonical") from None
    if set(document) != {
        "artifact_role", "artifact_version", "run_id", "stage_id", "version_uid",
        "analysis_profile_id", "prompt_bundle_id", "profile_content_sha256",
        "provider_mode", "model_id", "model_call_id", "request_sha256",
        "source_binding_sha256", "response_sha256", "source_artifacts",
        "textless_pages", "page_sources", "pages_analysed", "observations",
        "diagnostics",
    }:
        raise RecordedArtifactError("recorded_artifact_shape_invalid")
    if (document.get("artifact_role") != ARTIFACT_ROLE
            or document.get("artifact_version") != ARTIFACT_VERSION
            or document.get("stage_id") != STAGE_ID
            or document.get("run_id") != run
            or document.get("version_uid") != version
            or document.get("analysis_profile_id") != str(profile.analysis_profile_id)
            or document.get("prompt_bundle_id") != str(profile.prompt_bundle_id)
            or document.get("profile_content_sha256") != profile.content_sha256
            or document.get("provider_mode") != ProviderMode.RECORDED.value):
        raise RecordedArtifactError("recorded_artifact_provenance_mismatch")
    _require_identity(document.get("model_call_id"), ModelCallId, "invalid_model_call_id")
    if not isinstance(document.get("model_id"), str) or not re.fullmatch(
        r"fixture/[a-z0-9][a-z0-9._-]{0,127}", document["model_id"]
    ):
        raise RecordedArtifactError("recorded_model_invalid")
    for key in ("request_sha256", "response_sha256", "source_binding_sha256"):
        value = document.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise RecordedArtifactError("recorded_checksum_invalid")
    sources = document.get("source_artifacts")
    if not isinstance(sources, dict) or set(sources) != {"text_layer", "recognised_text"}:
        raise RecordedArtifactError("recorded_sources_invalid")
    try:
        text_ref = ArtifactRef(**sources["text_layer"])
        recognised_ref = (None if sources["recognised_text"] is None
                          else ArtifactRef(**sources["recognised_text"]))
    except (TypeError, ValueError):
        raise RecordedArtifactError("recorded_sources_invalid") from None
    if (text_ref.role != "prepared.text_layer"
            or (recognised_ref is not None and recognised_ref.role != "prepared.recognised_text")):
        raise RecordedArtifactError("recorded_sources_invalid")
    textless = document.get("textless_pages")
    if textless is not None and (
        not isinstance(textless, list) or any(type(item) is not int or item < 1 for item in textless)
        or textless != sorted(set(textless))
    ):
        raise RecordedArtifactError("recorded_textless_pages_invalid")
    if (textless is None) != (recognised_ref is None):
        raise RecordedArtifactError("recorded_sources_invalid")
    binding = sha256_hex(canonical_bytes({
        "version_uid": version,
        "text_layer_ref": text_ref.to_document(),
        "recognised_ref": None if recognised_ref is None else recognised_ref.to_document(),
        "textless_pages": textless,
        "request_sha256": document["request_sha256"],
    }))
    if document["source_binding_sha256"] != binding:
        raise RecordedArtifactError("recorded_source_binding_mismatch")
    diagnostics = document.get("diagnostics")
    if (not isinstance(diagnostics, dict) or set(diagnostics) != {
        "rejected", "malformed_count", "salvaged", "truncated",
    } or diagnostics["truncated"] is not False or diagnostics["salvaged"] is not False
            or type(diagnostics["malformed_count"]) is not int
            or diagnostics["malformed_count"] < 0
            or not isinstance(diagnostics["rejected"], list)):
        raise RecordedArtifactError("recorded_coverage_incomplete")
    observations, source_ordinals, accepted = _complete_observations(document)
    if textless is not None and not set(textless).issubset(document["pages_analysed"]):
        raise RecordedArtifactError("recorded_textless_pages_invalid")
    rejected_ordinals: list[int] = []
    rejected_proposals: list[RejectedProposal] = []
    for rejected in diagnostics["rejected"]:
        if (not isinstance(rejected, dict) or set(rejected) != {"source_proposal_ordinal", "failures"}
                or type(rejected["source_proposal_ordinal"]) is not int
                or rejected["source_proposal_ordinal"] < 0
                or not isinstance(rejected["failures"], list) or not rejected["failures"]):
            raise RecordedArtifactError("recorded_diagnostics_invalid")
        failures: list[UnresolvedEvidence] = []
        for failure in rejected["failures"]:
            if (not isinstance(failure, dict)
                    or set(failure) != {"evidence_ordinal", "page_number", "quote", "reason"}
                    or type(failure["evidence_ordinal"]) is not int
                    or failure["evidence_ordinal"] < 0
                    or type(failure["page_number"]) is not int
                    or failure["page_number"] < 1
                    or not isinstance(failure["quote"], str)
                    or not 1 <= len(failure["quote"]) <= 2000
                    or not failure["quote"].strip()
                    or not isinstance(failure["reason"], str)
                    or failure["reason"] not in {
                        REASON_ABSENT, REASON_DIFFERENT_PAGE,
                        REASON_SPAN_OUTSIDE_PAGE, REASON_LENGTH_MISMATCH,
                        REASON_RECOGNISED_ONLY,
                    }):
                raise RecordedArtifactError("recorded_diagnostics_invalid")
            failures.append(UnresolvedEvidence(
                failure["evidence_ordinal"], failure["page_number"],
                failure["quote"], failure["reason"],
            ))
        if [item.evidence_ordinal for item in failures] != sorted({
            item.evidence_ordinal for item in failures
        }):
            raise RecordedArtifactError("recorded_diagnostics_invalid")
        rejected_ordinals.append(rejected["source_proposal_ordinal"])
        rejected_proposals.append(RejectedProposal(
            rejected["source_proposal_ordinal"], tuple(failures),
        ))
    all_ordinals = (*source_ordinals, *rejected_ordinals)
    if sorted(all_ordinals) != list(range(len(all_ordinals))):
        raise RecordedArtifactError("recorded_partition_invalid")
    return RecordedMergeInput(
        observations, source_ordinals, reference.sha256, text_ref, recognised_ref,
        ProposalGroundingResult(
            tuple(accepted), tuple(rejected_proposals), diagnostics["malformed_count"], False,
        ),
        document["model_id"], document["model_call_id"], document["request_sha256"],
        document["response_sha256"], document["source_binding_sha256"],
    )


def _require_identity(value: str, identity_type: type, reason: str) -> str:
    try:
        return str(identity_type.parse(value))
    except (TypeError, ValueError):
        raise RecordedArtifactError(reason) from None


def _verify_replay(prepared: RecordedV2Input, replay: RecordedReplayResult) -> None:
    if not isinstance(prepared, RecordedV2Input) or not isinstance(replay, RecordedReplayResult):
        raise RecordedArtifactError("recorded_inputs_required")
    if replay.provider_mode is not ProviderMode.RECORDED:
        raise RecordedArtifactError("recorded_mode_required")
    if (
        replay.model_id != prepared.request.model_id
        or prepared.request.body.get("model") != replay.model_id
        or replay.request_sha256 != prepared.request_sha256
        or replay.source_binding_sha256 != prepared.source_binding_sha256
        or replay.response_sha256 != replay.finished.response_sha256
    ):
        raise RecordedArtifactError("replay_provenance_mismatch")
    if prepared.text_layer.version_uid != prepared.version_uid:
        raise RecordedArtifactError("text_layer_version_mismatch")
    if prepared.page_sources != tuple(
        PdfPageSource(page.page_number, page.char_start, page.char_end)
        for page in prepared.text_layer.pages
    ):
        raise RecordedArtifactError("page_sources_mismatch")
    user_prompt = prompt_material.render_user_prompt(
        prepared.text_layer, recognised_context=prepared.recognised_context,
    )
    if prepared.request.body.get("messages") != [{"role": "user", "content": user_prompt}]:
        raise RecordedArtifactError("request_sources_mismatch")
    expected_binding = sha256_hex(canonical_bytes({
        "version_uid": prepared.version_uid,
        "text_layer_ref": prepared.text_layer_ref.to_document(),
        "recognised_ref": (
            None if prepared.recognised_ref is None
            else prepared.recognised_ref.to_document()
        ),
        "textless_pages": prepared.textless_pages,
        "request_sha256": prepared.request_sha256,
    }))
    if expected_binding != replay.source_binding_sha256:
        raise RecordedArtifactError("source_binding_mismatch")
    if replay.finished.merge != prepare_merge(replay.finished.grounding):
        raise RecordedArtifactError("merge_preparation_mismatch")


def build_recorded_observation_artifact(
    *,
    prepared: RecordedV2Input,
    replay: RecordedReplayResult,
    run_id: str,
    model_call_id: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
) -> BuiltRecordedArtifact:
    """Serialize verified recorded observations and all available diagnostics.

    ``run_id`` and ``model_call_id`` are allocated by a later durable caller.
    Same identities, verified input and replay produce byte-identical payloads.
    No model claim or rejected proposal receives a finding identity here.
    """
    _verify_replay(prepared, replay)
    run = _require_identity(run_id, RunId, "invalid_run_id")
    call = _require_identity(model_call_id, ModelCallId, "invalid_model_call_id")
    _require_identity(prepared.version_uid, VersionUid, "invalid_version_uid")
    profile = registered.resolve_recorded_profile(analysis_profile_id, prompt_bundle_id)

    observations = []
    for ordinal, item in enumerate(replay.finished.grounding.accepted):
        proposal = item.proposal
        if (
            proposal.category not in CATEGORIES
            or proposal.proposed_severity not in SEVERITIES
            or not item.evidence
            or len(item.evidence) != len(proposal.evidence)
        ):
            raise RecordedArtifactError("accepted_proposal_invalid")
        evidence = []
        for evidence_ordinal, anchor in enumerate(item.evidence):
            page = prepared.text_layer.page(anchor.page_number)
            if (
                page is None
                or anchor.block_id is not None
                or anchor.char_end - anchor.char_start != len(anchor.quote)
                or not page.contains(anchor.char_start, anchor.char_end)
                or prepared.text_layer.slice(anchor.char_start, anchor.char_end) != anchor.quote
            ):
                raise RecordedArtifactError("evidence_not_grounded_in_pdf")
            evidence.append({
                "evidence_ordinal": evidence_ordinal,
                "page_number": anchor.page_number,
                "quote": anchor.quote,
                "char_start": anchor.char_start,
                "char_end": anchor.char_end,
            })
        observations.append({
            "observation_ordinal": ordinal,
            "source_proposal_ordinal": item.proposal_ordinal,
            "category": proposal.category,
            "finding_text": proposal.finding_text,
            "recommendation_text": proposal.recommendation_text,
            "proposed_severity": proposal.proposed_severity,
            "model_call_id": call,
            "evidence": evidence,
        })

    diagnostics = [{
        "source_proposal_ordinal": item.proposal_ordinal,
        "failures": [{
            "evidence_ordinal": failure.evidence_ordinal,
            "page_number": failure.page_number,
            "quote": failure.quote,
            "reason": failure.reason,
        } for failure in item.failures],
    } for item in replay.finished.grounding.rejected]
    document = {
        "artifact_role": ARTIFACT_ROLE,
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run,
        "stage_id": STAGE_ID,
        "version_uid": prepared.version_uid,
        "analysis_profile_id": str(profile.analysis_profile_id),
        "prompt_bundle_id": str(profile.prompt_bundle_id),
        "profile_content_sha256": profile.content_sha256,
        "provider_mode": ProviderMode.RECORDED.value,
        "model_id": replay.model_id,
        "model_call_id": call,
        "request_sha256": replay.request_sha256,
        "source_binding_sha256": replay.source_binding_sha256,
        "response_sha256": replay.response_sha256,
        "source_artifacts": {
            "text_layer": prepared.text_layer_ref.to_document(),
            "recognised_text": (
                None if prepared.recognised_ref is None
                else prepared.recognised_ref.to_document()
            ),
        },
        "textless_pages": prepared.textless_pages,
        "page_sources": [{
            "page_number": page.page_number,
            "char_start": page.char_start,
            "char_end": page.char_end,
        } for page in prepared.page_sources],
        "pages_analysed": list(prepared.text_layer.page_numbers),
        "observations": observations,
        "diagnostics": {
            "rejected": diagnostics,
            "malformed_count": replay.finished.grounding.malformed_count,
            "salvaged": replay.finished.grounding.salvaged,
            "truncated": replay.finished.truncated,
        },
    }
    payload = canonical_bytes(document)
    return BuiltRecordedArtifact(payload=payload, sha256=sha256_hex(payload))


__all__ = [
    "ARTIFACT_ROLE", "ARTIFACT_VERSION", "BuiltRecordedArtifact",
    "RecordedArtifactError", "RecordedMergeInput", "build_recorded_observation_artifact",
    "read_recorded_merge_input",
]
