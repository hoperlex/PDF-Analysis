"""Artifact roles, the artifact-document envelope, and publication through BlobStore.

Every artifact document in ``P02_SEAMS`` section 4 carries ``artifact_role`` and
``artifact_version`` at its root, and a consumer reading an unexpected
``artifact_version`` fails closed rather than guessing. :func:`envelope` is the one
place those two fields are written, so a stage cannot forget them, and
:func:`read_artifact` is the one place they are checked.

The registry spells roles with dots (``prepared.text_layer``); the blob store's role
vocabulary is ``^[a-z][a-z0-9_]{2,63}$`` and admits none. :func:`blob_role_for` maps
between them by replacing ``.`` with ``_``. The mapping is total, injective over the
role set this package publishes, and deliberately mechanical - the artifact role in
the ``StageResult`` stays the contract spelling, which is what a consumer matches on.
"""

from __future__ import annotations

import json
from typing import Any, Final, Mapping

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import BlobStore, parse_blob_role
from auditmanager.storage.models import BlobId

# --- roles -------------------------------------------------------------------

ROLE_SOURCE_DOCUMENT: Final[str] = "source.document"
ROLE_PAGE_INVENTORY: Final[str] = "prepared.page_inventory"
ROLE_TEXT_LAYER: Final[str] = "prepared.text_layer"
ROLE_BLOCK_INDEX: Final[str] = "geometry.block_index"
ROLE_PAGE_CROPS: Final[str] = "geometry.page_crops"
ROLE_DOCUMENT_GRAPH: Final[str] = "context.document_graph"

#: Every artifact document shape in ``P02_SEAMS`` section 4 is at 1.0.0.
ARTIFACT_VERSION: Final[str] = "1.0.0"


def blob_role_for(artifact_role: str) -> str:
    """The blob-store role name for a dotted contract artifact role."""
    return parse_blob_role(artifact_role.replace(".", "_"))


def envelope(role: str, version_uid: str, **body: Any) -> dict[str, Any]:
    """Wrap an artifact body in the two root fields section 4 requires."""
    document: dict[str, Any] = {
        "artifact_role": role,
        "artifact_version": ARTIFACT_VERSION,
        "version_uid": version_uid,
    }
    document.update(body)
    return document


def publish_artifact(
    blob_store: BlobStore, role: str, document: Mapping[str, Any]
) -> tuple[ArtifactRef, bytes]:
    """Serialize, publish and return a checksum-verified reference to ``document``.

    The returned reference carries ``blob_id``, ``sha256``, ``size_bytes`` and
    ``media_type`` and nothing else - no object key, no URL, no credential. The bytes
    come back too, because a stage downstream in the same run needs the checksum of
    what was actually published to bind its own artifact to it.
    """
    payload = canonical_bytes(document)
    digest = sha256_hex(payload)
    published = blob_store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=blob_role_for(role),
        media_type=ARTIFACT_MEDIA_TYPE,
    )
    reference = ArtifactRef(
        role=role,
        blob_id=str(published.blob_id),
        sha256=published.sha256,
        size_bytes=published.size,
        media_type=published.media_type,
    )
    return reference, payload


def read_artifact(
    blob_store: BlobStore, blob_id: BlobId, *, expected_role: str
) -> tuple[dict[str, Any], str]:
    """Read a published artifact, refusing an unexpected role or version.

    Returns the document and the SHA-256 of the exact bytes read, so a consumer can
    record what it bound itself to rather than what it hoped it read.
    """
    try:
        payload = blob_store.read(blob_id, verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - narrowed to a typed refusal below
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a declared stage input could not be read from the blob store",
            reason="input_unreadable",
        ) from exc

    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a declared stage input is not a JSON artifact document",
            reason="input_not_json",
        ) from exc

    if not isinstance(document, dict):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a declared stage input is not a JSON object",
            reason="input_not_json",
        )
    if document.get("artifact_role") != expected_role:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a declared stage input carries a different artifact role",
            reason="input_role_mismatch",
        )
    if document.get("artifact_version") != ARTIFACT_VERSION:
        raise DomainError(
            ErrorCode.UNSUPPORTED_CONTRACT_VERSION,
            message=(
                "a declared stage input carries an artifact version this engine "
                "does not implement; it fails closed rather than guessing"
            ),
        )
    return document, sha256_hex(payload)


__all__ = [
    "ARTIFACT_VERSION",
    "ROLE_BLOCK_INDEX",
    "ROLE_DOCUMENT_GRAPH",
    "ROLE_PAGE_CROPS",
    "ROLE_PAGE_INVENTORY",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_TEXT_LAYER",
    "blob_role_for",
    "envelope",
    "publish_artifact",
    "read_artifact",
]
