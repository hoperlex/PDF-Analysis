"""Pure W57a build-precondition and expected-digest comparison.

The caller must verify source bytes, the complete embedding stream, reviewed
map and expected artifact digests independently. A match here is only an input
to the later custody transaction; it never creates a verified set row.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from auditmanager.norms.retrieval.artifact import (
    SET_BUILDER_VERSION,
    CanonicalBlob,
    SetIdentity,
    canonical_json_bytes,
)
from auditmanager.norms.retrieval.candidate import RetrievalCandidate
from auditmanager.norms.retrieval.catalogue import CATALOGUE_VERSION
from auditmanager.norms.retrieval.qualification_reader import SnapshotBuildFacts


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class QualificationDecisionRefused(ValueError):
    """The build facts or candidate do not form a safe comparison input."""


@dataclass(frozen=True, slots=True)
class DigestComparison:
    status: Literal["matched", "rejected"]
    expected_set_sha256: str
    observed_set_sha256: str
    expected_catalogue_sha256: str
    observed_catalogue_sha256: str
    different_artifacts: tuple[Literal["retrieval_set", "catalogue"], ...]


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise QualificationDecisionRefused(f"invalid {label}")
    return value


def _payload(blob: CanonicalBlob, label: str) -> dict[str, object]:
    if not isinstance(blob, CanonicalBlob) or not isinstance(blob.data, bytes):
        raise QualificationDecisionRefused(f"invalid {label} blob")
    if hashlib.sha256(blob.data).hexdigest() != _digest(blob.sha256, f"{label} digest"):
        raise QualificationDecisionRefused(f"{label} bytes differ from digest")
    try:
        value = json.loads(blob.data.decode("utf-8"))
        if not isinstance(value, dict) or canonical_json_bytes(value) != blob.data:
            raise QualificationDecisionRefused(f"{label} is not canonical JSON")
    except (UnicodeError, ValueError, TypeError) as exc:
        raise QualificationDecisionRefused(f"{label} is not canonical JSON") from exc
    return value


def compare_retrieval_candidate(
    *,
    facts: SnapshotBuildFacts,
    identity: SetIdentity,
    candidate: RetrievalCandidate,
    independently_checked_source_digest: str,
    independently_checked_embedding_digest: str,
    expected_set_sha256: str,
    expected_catalogue_sha256: str,
) -> DigestComparison:
    """Refuse incomplete evidence; report each expected artifact SHA mismatch.

    The two independently checked digests and the expected artifact SHAs must
    come from outside this candidate and its stored DB completion rows.
    """
    source_digest = _digest(independently_checked_source_digest, "source proof digest")
    embedding_digest = _digest(independently_checked_embedding_digest, "embedding proof digest")
    expected_set = _digest(expected_set_sha256, "expected set digest")
    expected_catalogue = _digest(expected_catalogue_sha256, "expected catalogue digest")
    if not isinstance(facts, SnapshotBuildFacts) or not isinstance(identity, SetIdentity):
        raise QualificationDecisionRefused("build facts and set identity are required")
    if not isinstance(candidate, RetrievalCandidate):
        raise QualificationDecisionRefused("retrieval candidate is required")
    if identity.builder_version != SET_BUILDER_VERSION:
        raise QualificationDecisionRefused("unknown set builder version")
    if (
        facts.snapshot_id != identity.snapshot_id
        or facts.content_key != identity.reviewed_content_key
        or identity.embedding_build != f"{facts.embedding_profile}:{facts.chunking_profile}"
    ):
        raise QualificationDecisionRefused("snapshot or build identity differs from reviewed map")
    if facts.content_digest != source_digest:
        raise QualificationDecisionRefused("source digest differs from independent proof")
    if (
        facts.declared_document_count < 1
        or facts.stored_document_count != facts.declared_document_count
        or facts.pdf_bound_document_count != facts.declared_document_count
    ):
        raise QualificationDecisionRefused("snapshot documents or PDF custody incomplete")
    chunk = facts.chunk
    if (
        chunk is None or chunk.embedding is None
        or chunk.declared_chunk_count < 1
        or chunk.stored_chunk_count != chunk.declared_chunk_count
    ):
        raise QualificationDecisionRefused("chunk build incomplete")
    embedding = chunk.embedding
    if (
        embedding.declared_chunk_count != chunk.declared_chunk_count
        or embedding.stored_embedded_chunk_count != chunk.declared_chunk_count
        or embedding.declared_window_count < chunk.declared_chunk_count
        or embedding.stored_window_count != embedding.declared_window_count
    ):
        raise QualificationDecisionRefused("embedding build incomplete")
    if (
        embedding.embedding_set_sha256 != embedding_digest
        or candidate.embedding_set_sha256 != embedding_digest
    ):
        raise QualificationDecisionRefused("embedding digest differs from independent proof")

    set_payload = _payload(candidate.retrieval_set, "retrieval set")
    catalogue_payload = _payload(candidate.catalogue, "catalogue")
    if (
        set_payload.get("builder_version") != identity.builder_version
        or set_payload.get("identity") != {
            "map_sha256": identity.map_sha256,
            "reviewed_content_key": identity.reviewed_content_key,
            "norms_snapshot_id": identity.snapshot_id,
            "embedding_build": identity.embedding_build,
        }
        or set_payload.get("snapshot_content_digest") != source_digest
        or catalogue_payload.get("catalogue_version") != CATALOGUE_VERSION
        or catalogue_payload.get("norms_snapshot_id") != facts.snapshot_id
        or catalogue_payload.get("content_key") != facts.content_key
        or catalogue_payload.get("snapshot_content_digest") != source_digest
        or catalogue_payload.get("document_count") != facts.declared_document_count
        or not isinstance(catalogue_payload.get("documents"), list)
        or len(catalogue_payload["documents"]) != facts.declared_document_count
    ):
        raise QualificationDecisionRefused("candidate artifact identity differs from build facts")
    different = tuple(
        name for name, expected, observed in (
            ("retrieval_set", expected_set, candidate.retrieval_set.sha256),
            ("catalogue", expected_catalogue, candidate.catalogue.sha256),
        ) if expected != observed
    )
    return DigestComparison(
        status="rejected" if different else "matched",
        expected_set_sha256=expected_set,
        observed_set_sha256=candidate.retrieval_set.sha256,
        expected_catalogue_sha256=expected_catalogue,
        observed_catalogue_sha256=candidate.catalogue.sha256,
        different_artifacts=different,
    )


__all__ = ["DigestComparison", "QualificationDecisionRefused", "compare_retrieval_candidate"]
