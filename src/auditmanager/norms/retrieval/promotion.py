"""Unserved W57a promotion of canonical retrieval-set bytes through 0023 custody.

Preparation is read-only and compares independent proofs before any admission or
object-store access. Matched bytes use R-76 admissions as the durable outbox;
the existing dispatcher publishes them. Finalization verifies both saved Blobs,
then inserts the immutable set row and both bindings in the caller's one transaction.
The caller retains ``set_id`` across retries and uses a durable custody source.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from auditmanager.norms.custody import (
    NORM_CATALOGUE, NORM_RETRIEVAL_SET, AdmissionRequest, AdmissionState,
    CustodyManifest, CustodySlot, DeclaredContent, admit, blob_id_for,
    publish_bindings,
)
from auditmanager.norms.custody.repository import CustodyRepository
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from auditmanager.norms.retrieval.artifact import (
    SET_BUILDER_VERSION, SetIdentity, canonical_json_bytes,
)
from auditmanager.norms.retrieval.candidate import (
    RetrievalCandidate, assemble_retrieval_candidate,
)
from auditmanager.norms.retrieval.evidence_bridge import ReviewedDesignation
from auditmanager.norms.retrieval.promotion_repository import (
    VerifiedSetReference, get_set, insert_set, verified_for_identity,
)
from auditmanager.norms.retrieval.qualification_decision import (
    DigestComparison, compare_retrieval_candidate,
)
from auditmanager.norms.retrieval.qualification_reader import read_snapshot_build_facts
from auditmanager.norms.retrieval.ranking import RetrievalItem
from auditmanager.norms.retrieval.source_reader import read_snapshot_evidence
from auditmanager.norms.retrieval.window_reader import read_retrieval_windows
from auditmanager.shared.identity import NormRetrievalSetId
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_ARTIFACT_BYTES = 10_000_000
_MEDIA_TYPE = "application/json"
_SET_ANCHOR = "retrieval-set.json"
_CATALOGUE_ANCHOR = "catalogue.json"


class PromotionRefused(ValueError):
    """The supplied reviewed proof, custody state or replay identity disagrees."""


@dataclass(frozen=True, slots=True)
class PromotionRequest:
    set_id: str
    identity: SetIdentity
    map_bytes: bytes
    reviewed_designations: tuple[ReviewedDesignation, ...]
    items: tuple[RetrievalItem, ...]
    chunking_profile: str
    independently_checked_source_digest: str
    independently_checked_embedding_digest: str
    expected_set_sha256: str
    expected_catalogue_sha256: str


@dataclass(frozen=True, slots=True)
class PreparedPromotion:
    request: PromotionRequest
    candidate: RetrievalCandidate
    comparison: DigestComparison


@dataclass(frozen=True, slots=True)
class PromotionOutcome:
    set_id: str
    state: Literal["rejected", "verified"]
    replayed: bool


def _digest(value: str, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PromotionRefused(f"invalid {label}")
    return value


def _checked(request: PromotionRequest) -> tuple[str, ...]:
    if not isinstance(request, PromotionRequest):
        raise PromotionRefused("promotion request is required")
    try:
        NormRetrievalSetId.parse(request.set_id)
    except (TypeError, ValueError) as exc:
        raise PromotionRefused("invalid retrieval set id") from exc
    identity = request.identity
    if not isinstance(identity, SetIdentity) or identity.builder_version != SET_BUILDER_VERSION:
        raise PromotionRefused("invalid builder identity")
    if identity.embedding_build != f"{EMBEDDING_PROFILE}:{request.chunking_profile}":
        raise PromotionRefused("embedding build differs from chunking profile")
    _digest(identity.map_sha256, "map digest")
    _digest(request.independently_checked_source_digest, "source proof digest")
    _digest(request.independently_checked_embedding_digest, "embedding proof digest")
    _digest(request.expected_set_sha256, "expected set digest")
    _digest(request.expected_catalogue_sha256, "expected catalogue digest")
    if (
        not isinstance(request.map_bytes, bytes)
        or len(request.map_bytes) > MAX_ARTIFACT_BYTES
        or hashlib.sha256(request.map_bytes).hexdigest() != identity.map_sha256
    ):
        raise PromotionRefused("reviewed map bytes differ from digest")
    try:
        mapping = json.loads(request.map_bytes.decode("utf-8"))
        if not isinstance(mapping, dict) or canonical_json_bytes(mapping) != request.map_bytes:
            raise PromotionRefused("reviewed map is not canonical JSON")
    except (UnicodeError, ValueError, TypeError) as exc:
        raise PromotionRefused("reviewed map is not canonical JSON") from exc
    mapped = mapping.get("mapped_document_ids")
    if not isinstance(mapped, list) or not mapped or any(not isinstance(x, str) for x in mapped):
        raise PromotionRefused("reviewed map has no document identities")
    if len(set(mapped)) != len(mapped):
        raise PromotionRefused("reviewed map repeats a document identity")
    return tuple(mapped)


def prepare_promotion(session: Session, request: PromotionRequest) -> PreparedPromotion:
    """Read one named snapshot/build and compare exact bytes, without writing.

    The caller must hold one consistent read transaction. The two independent
    proof digests and the map review come from outside these database readers;
    matching stored counts alone never qualifies the corpus.
    """
    mapped = _checked(request)
    identity = request.identity
    facts = read_snapshot_build_facts(
        session, snapshot_id=identity.snapshot_id,
        expected_content_key=identity.reviewed_content_key,
        chunking_profile=request.chunking_profile,
    )
    source = read_snapshot_evidence(
        session, snapshot_id=identity.snapshot_id,
        expected_content_key=identity.reviewed_content_key,
        mapped_document_ids=mapped,
    )
    windows = read_retrieval_windows(
        session, snapshot_id=identity.snapshot_id,
        expected_content_key=identity.reviewed_content_key,
        embedding_build=identity.embedding_build,
        expected_embedding_set_sha256=request.independently_checked_embedding_digest,
        mapped_document_ids=mapped,
    )
    candidate = assemble_retrieval_candidate(
        evidence=source, windows=windows, identity=identity,
        map_bytes=request.map_bytes, reviewed_designations=request.reviewed_designations,
        items=request.items,
    )
    comparison = compare_retrieval_candidate(
        facts=facts, identity=identity, candidate=candidate,
        independently_checked_source_digest=request.independently_checked_source_digest,
        independently_checked_embedding_digest=request.independently_checked_embedding_digest,
        expected_set_sha256=request.expected_set_sha256,
        expected_catalogue_sha256=request.expected_catalogue_sha256,
    )
    for label, blob in (("retrieval set", candidate.retrieval_set), ("catalogue", candidate.catalogue)):
        if not 1 <= len(blob.data) <= MAX_ARTIFACT_BYTES:
            raise PromotionRefused(f"{label} exceeds the bounded Blob size")
    return PreparedPromotion(request=request, candidate=candidate, comparison=comparison)


def _checked_prepared(prepared: PreparedPromotion) -> None:
    """Reject modified or invented comparison facts before persistence/admission."""
    if not isinstance(prepared, PreparedPromotion):
        raise PromotionRefused("prepared promotion is required")
    request, candidate, comparison = prepared.request, prepared.candidate, prepared.comparison
    _checked(request)
    if not isinstance(candidate, RetrievalCandidate) or not isinstance(comparison, DigestComparison):
        raise PromotionRefused("candidate or digest comparison is missing")
    if candidate.embedding_set_sha256 != request.independently_checked_embedding_digest:
        raise PromotionRefused("candidate embedding proof differs")
    observed: list[str] = []
    for label, blob in (("retrieval set", candidate.retrieval_set), ("catalogue", candidate.catalogue)):
        if not isinstance(blob.data, bytes) or not 1 <= len(blob.data) <= MAX_ARTIFACT_BYTES:
            raise PromotionRefused(f"{label} has invalid bounded bytes")
        digest = hashlib.sha256(blob.data).hexdigest()
        if blob.sha256 != digest:
            raise PromotionRefused(f"{label} bytes differ from candidate digest")
        try:
            payload = json.loads(blob.data.decode("utf-8"))
            if not isinstance(payload, dict) or canonical_json_bytes(payload) != blob.data:
                raise PromotionRefused(f"{label} is not canonical JSON")
        except (UnicodeError, ValueError, TypeError) as exc:
            raise PromotionRefused(f"{label} is not canonical JSON") from exc
        observed.append(digest)
    if (
        comparison.expected_set_sha256 != request.expected_set_sha256
        or comparison.expected_catalogue_sha256 != request.expected_catalogue_sha256
        or (comparison.observed_set_sha256, comparison.observed_catalogue_sha256) != tuple(observed)
    ):
        raise PromotionRefused("comparison digests differ from candidate or request")
    different = tuple(name for name, expected, actual in (
        ("retrieval_set", request.expected_set_sha256, observed[0]),
        ("catalogue", request.expected_catalogue_sha256, observed[1]),
    ) if expected != actual)
    if comparison.different_artifacts != different or comparison.status != (
        "rejected" if different else "matched"
    ):
        raise PromotionRefused("comparison outcome differs from exact digests")
    if comparison.status == "matched" and not 1 <= len(candidate.selection.prompt_part) <= 22_000:
        raise PromotionRefused("matched set has invalid prompt size")


def _require_fresh(session: Session, prepared: PreparedPromotion) -> None:
    """Rebuild against the pinned DB facts before a write or external effect.

    ``PreparedPromotion`` is a value type, not an authority token. Re-reading
    prevents a caller from constructing one by hand or reusing it after a build
    changed between preparation and custody finalization.
    """
    if prepare_promotion(session, prepared.request) != prepared:
        raise PromotionRefused("prepared evidence differs from pinned snapshot build")


def _row_values(prepared: PreparedPromotion, state: Literal["rejected", "verified"]) -> dict[str, object]:
    request = prepared.request
    comparison = prepared.comparison
    matched = state == "verified"
    return {
        "set_id": request.set_id,
        "snapshot_id": request.identity.snapshot_id,
        "map_sha256": request.identity.map_sha256,
        "content_key": request.identity.reviewed_content_key,
        "chunking_profile": request.chunking_profile,
        "embedding_profile": EMBEDDING_PROFILE,
        "builder_version": request.identity.builder_version,
        "state": state,
        "expected_set_sha256": comparison.expected_set_sha256,
        "observed_set_sha256": comparison.observed_set_sha256,
        "expected_catalogue_sha256": comparison.expected_catalogue_sha256,
        "observed_catalogue_sha256": comparison.observed_catalogue_sha256,
        "set_blob_id": blob_id_for(comparison.observed_set_sha256, len(prepared.candidate.retrieval_set.data)) if matched else None,
        "set_size_bytes": len(prepared.candidate.retrieval_set.data) if matched else None,
        "catalogue_blob_id": blob_id_for(comparison.observed_catalogue_sha256, len(prepared.candidate.catalogue.data)) if matched else None,
        "catalogue_size_bytes": len(prepared.candidate.catalogue.data) if matched else None,
        "prompt_part_characters": len(prepared.candidate.selection.prompt_part) if matched else None,
    }


def _same_row(existing: object, expected: dict[str, object]) -> bool:
    if existing is None:
        return False
    row = dict(existing)
    names = {
        "set_id": "norm_retrieval_set_id", "snapshot_id": "norms_snapshot_id",
        "content_key": "reviewed_content_key",
    }
    return all(row.get(names.get(key, key)) == value for key, value in expected.items())


def record_rejection(session: Session, prepared: PreparedPromotion) -> PromotionOutcome:
    """Persist one immutable mismatch row, with no admission or Blob effect."""
    _checked_prepared(prepared)
    if prepared.comparison.status != "rejected":
        raise PromotionRefused("a matched candidate is not a rejection")
    _require_fresh(session, prepared)
    values = _row_values(prepared, "rejected")
    if insert_set(session, values):
        return PromotionOutcome(prepared.request.set_id, "rejected", False)
    if _same_row(get_set(session, prepared.request.set_id), values):
        return PromotionOutcome(prepared.request.set_id, "rejected", True)
    raise PromotionRefused("retrieval set identity was reused with different evidence")


def _slots(prepared: PreparedPromotion) -> tuple[tuple[str, str, bytes, str], ...]:
    return (
        (NORM_RETRIEVAL_SET, _SET_ANCHOR, prepared.candidate.retrieval_set.data,
         prepared.comparison.observed_set_sha256),
        (NORM_CATALOGUE, _CATALOGUE_ANCHOR, prepared.candidate.catalogue.data,
         prepared.comparison.observed_catalogue_sha256),
    )


def admit_matched(
    session: Session, prepared: PreparedPromotion, *, manifest: CustodyManifest,
) -> tuple[str, str]:
    """Admit both artifacts as outbox rows; the caller commits before dispatch.

    ``manifest`` must be independently verified and its source bytes durable.
    Both slots are checked before the first admission is written.
    """
    _checked_prepared(prepared)
    if prepared.comparison.status != "matched":
        raise PromotionRefused("mismatched digests cannot be admitted")
    _require_fresh(session, prepared)
    existing = get_set(session, prepared.request.set_id)
    if existing is not None and not _same_row(existing, _row_values(prepared, "verified")):
        raise PromotionRefused("retrieval set identity was reused with different evidence")
    requests: list[AdmissionRequest] = []
    for role, anchor, data, sha256 in _slots(prepared):
        slot = CustodySlot(role, "norm_retrieval_set", prepared.request.set_id, "artifact", anchor)
        declared = DeclaredContent(sha256, len(data), _MEDIA_TYPE)
        if manifest.declared(slot) != declared:
            raise PromotionRefused("independent custody manifest differs from candidate")
        requests.append(AdmissionRequest(
            role=role, target_id=prepared.request.set_id, anchor_kind="artifact", anchor=anchor,
            sha256=sha256, size=len(data), media_type=_MEDIA_TYPE,
        ))
    first = admit(session, requests[0], manifest=manifest)
    second = admit(session, requests[1], manifest=manifest)
    return first.admission.admission_id, second.admission.admission_id


def _confirmed(prepared: PreparedPromotion) -> tuple[tuple[str, str, bytes, str], ...]:
    if prepared.comparison.status != "matched":
        raise PromotionRefused("mismatched digests cannot be verified")
    return _slots(prepared)


def _saved_bytes(store: BlobStore, *, blob_id: str, sha256: str, expected: bytes) -> None:
    """Re-read a confirmed canonical object, not a staged upload or metadata alone."""
    try:
        stream = store.open_stream(
            parse_blob_id(blob_id), expected_sha256=sha256, expected_size=len(expected),
        )
        try:
            observed = bytearray()
            for chunk in stream:
                if type(chunk) is not bytes or len(observed) + len(chunk) > len(expected):
                    raise PromotionRefused("canonical Blob size differs")
                observed.extend(chunk)
        finally:
            stream.close()
    except StorageError as exc:
        raise PromotionRefused("canonical Blob is unavailable") from exc
    if bytes(observed) != expected or hashlib.sha256(observed).hexdigest() != sha256:
        raise PromotionRefused("canonical Blob bytes differ from candidate")


def finalize_matched(
    session: Session, prepared: PreparedPromotion, *, blob_store: BlobStore,
) -> PromotionOutcome:
    """Insert the verified row and publish both bindings in this one DB transaction.

    The caller rolls back on any exception and commits only after the 0023
    deferred trigger has checked the build and both exact bindings.
    """
    _checked_prepared(prepared)
    _require_fresh(session, prepared)
    slots = _confirmed(prepared)
    values = _row_values(prepared, "verified")
    existing = get_set(session, prepared.request.set_id)
    if existing is not None and not _same_row(existing, values):
        raise PromotionRefused("retrieval set identity was reused with different evidence")
    custody = CustodyRepository()
    for role, anchor, data, sha256 in slots:
        slot = CustodySlot(role, "norm_retrieval_set", prepared.request.set_id, "artifact", anchor)
        admission = custody.live_in_slot(session, slot)
        if (
            admission is None or admission.state is not AdmissionState.CONFIRMED
            or admission.declared_sha256 != sha256
            or admission.declared_size_bytes != len(data)
            or admission.media_type != _MEDIA_TYPE
            or admission.blob_id != blob_id_for(sha256, len(data))
        ):
            raise PromotionRefused("confirmed custody admission differs from candidate")
    # Every identity, digest and admission mismatch above is refused before external access.
    for _role, _anchor, data, sha256 in slots:
        _saved_bytes(
            blob_store, blob_id=blob_id_for(sha256, len(data)), sha256=sha256, expected=data,
        )
    if existing is not None:
        return PromotionOutcome(prepared.request.set_id, "verified", True)
    if not insert_set(session, values):
        if _same_row(get_set(session, prepared.request.set_id), values):
            return PromotionOutcome(prepared.request.set_id, "verified", True)
        raise PromotionRefused("another set already holds this verified identity")
    publish_bindings(session, NORM_RETRIEVAL_SET, [prepared.request.set_id])
    publish_bindings(session, NORM_CATALOGUE, [prepared.request.set_id])
    return PromotionOutcome(prepared.request.set_id, "verified", False)


def select_verified_retrieval_set(
    session: Session, *, identity: SetIdentity, chunking_profile: str,
) -> VerifiedSetReference:
    """Read the one exact, confirmed set for a future Run pin; no fallback."""
    if (
        not isinstance(identity, SetIdentity)
        or identity.builder_version != SET_BUILDER_VERSION
        or identity.embedding_build != f"{EMBEDDING_PROFILE}:{chunking_profile}"
    ):
        raise PromotionRefused("invalid verified-set selection identity")
    reference = verified_for_identity(
        session, map_sha256=_digest(identity.map_sha256, "map digest"),
        snapshot_id=identity.snapshot_id, chunking_profile=chunking_profile,
        embedding_profile=EMBEDDING_PROFILE, builder_version=identity.builder_version,
    )
    if reference is None or reference.reviewed_content_key != identity.reviewed_content_key:
        raise PromotionRefused("verified retrieval set with custody is unavailable")
    return reference


__all__ = [
    "MAX_ARTIFACT_BYTES", "PreparedPromotion", "PromotionOutcome", "PromotionRefused",
    "PromotionRequest", "admit_matched", "finalize_matched", "prepare_promotion",
    "record_rejection", "select_verified_retrieval_set",
]
