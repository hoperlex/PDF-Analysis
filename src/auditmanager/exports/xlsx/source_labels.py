"""Resolve XLSX display page labels from a version's verified portal companion.

The caller owns the database transaction and storage read. This module binds
the immutable input manifest to the returned bytes; it never infers a display
label from a PDF page number and cannot supply normative finding citations.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents.public import MANIFEST_ROLE_STRUCTURED_COMPANION


_ROLE = MANIFEST_ROLE_STRUCTURED_COMPANION
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_BLOCK_ID = re.compile(r"blk_[0-9a-f]{32}\Z")
_MAX_BLOCKS_BYTES = 4 * 1024 * 1024  # W55b admitted member ceiling
_MAX_BLOCKS = 3000  # W55b admitted block ceiling
_SOURCE = text("""
    SELECT v.version_uid, v.page_count,
           m.version_uid AS manifest_version_uid, m.role AS manifest_role,
           m.blob_id, m.sha256 AS manifest_sha256,
           m.size_bytes AS manifest_size_bytes, m.media_type AS manifest_media_type,
           b.state AS blob_state, b.sha256 AS blob_sha256,
           b.size_bytes AS blob_size_bytes, b.media_type AS blob_media_type
      FROM document_version v
      LEFT JOIN input_manifest_entry m
        ON m.version_uid = v.version_uid AND m.role = :role
      LEFT JOIN blob b ON b.blob_id = m.blob_id
     WHERE v.version_uid = :version_uid
""")


@dataclass(frozen=True, slots=True)
class VerifiedPageLabels:
    version_uid: str
    page_labels: Mapping[int, str]
    source_ref: str


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("xlsx_page_source_layout_invalid")
        result[key] = value
    return result


def _page_labels(raw: bytes, page_count: int) -> Mapping[int, str]:
    """Project only page indices and labels from admitted portal block bytes."""
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("xlsx_page_source_layout_invalid") from exc
    if (
        not isinstance(document, dict)
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != 1
        or document.get("coordinate_space") != "normalized_page_top_left"
        or not isinstance(document.get("pages"), list)
        or not isinstance(document.get("blocks"), list)
        or len(document["pages"]) != page_count
        or not 0 < len(document["blocks"]) <= _MAX_BLOCKS
    ):
        raise ValueError("xlsx_page_source_layout_invalid")
    page_indices: set[int] = set()
    for page in document["pages"]:
        if not isinstance(page, dict):
            raise ValueError("xlsx_page_source_layout_invalid")
        index = page.get("page_index")
        if type(index) is not int or index in page_indices:
            raise ValueError("xlsx_page_source_layout_invalid")
        page_indices.add(index)
    if page_indices != set(range(page_count)):
        raise ValueError("xlsx_page_source_layout_invalid")

    labels: dict[int, str] = {}
    block_ids: set[str] = set()
    for block in document["blocks"]:
        if not isinstance(block, dict):
            raise ValueError("xlsx_page_source_layout_invalid")
        block_id = block.get("block_id")
        index = block.get("page_index")
        label = block.get("page_label")
        if (
            not isinstance(block_id, str)
            or _BLOCK_ID.fullmatch(block_id) is None
            or block_id in block_ids
            or type(index) is not int or index not in page_indices
            or type(label) is not int or label < 1
        ):
            raise ValueError("xlsx_page_source_layout_invalid")
        block_ids.add(block_id)
        page_number = index + 1
        previous = labels.get(page_number)
        shown = str(label)
        if previous is not None and previous != shown:
            raise ValueError("xlsx_page_source_label_conflict")
        labels[page_number] = shown
    if set(labels) != set(range(1, page_count + 1)):
        raise ValueError("xlsx_page_source_label_missing")
    return MappingProxyType(labels)


def read_verified_page_labels(
    session: Session,
    version_uid: str,
    *,
    read_blob: Callable[[str], bytes],
) -> VerifiedPageLabels | None:
    """Read exact portal labels, or ``None`` when the version does not exist.

    A bare PDF or any page without a portal block cannot provide a verified
    display label through this source. Such inputs refuse rather than becoming
    their one-based page numbers. The caller must match this version to the run.
    """
    if not isinstance(version_uid, str) or not version_uid or not callable(read_blob):
        raise ValueError("xlsx_page_source_inputs_invalid")
    row = session.execute(
        _SOURCE, {"version_uid": version_uid, "role": _ROLE}
    ).mappings().first()
    if row is None:
        return None
    page_count = row["page_count"]
    blob_id = row["blob_id"]
    digest = row["manifest_sha256"]
    size = row["manifest_size_bytes"]
    if (
        row["version_uid"] != version_uid
        or row["manifest_version_uid"] != version_uid
        or row["manifest_role"] != _ROLE
        or type(page_count) is not int or not 1 <= page_count <= 30
        or not isinstance(blob_id, str) or not blob_id
        or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
        or type(size) is not int or not 0 < size <= _MAX_BLOCKS_BYTES
        or row["manifest_media_type"] != "application/json"
        or row["blob_state"] != "available"
        or row["blob_sha256"] != digest
        or row["blob_size_bytes"] != size
        or row["blob_media_type"] != "application/json"
    ):
        raise ValueError("xlsx_page_source_binding_invalid")
    try:
        raw = read_blob(blob_id)
    except Exception as exc:  # storage boundary must not silently fall back
        raise ValueError("xlsx_page_source_unreadable") from exc
    if (
        not isinstance(raw, bytes)
        or len(raw) != size
        or hashlib.sha256(raw).hexdigest() != digest
    ):
        raise ValueError("xlsx_page_source_bytes_invalid")
    return VerifiedPageLabels(
        version_uid=version_uid,
        page_labels=_page_labels(raw, page_count),
        source_ref=f"{version_uid}:{blob_id}:{digest}",
    )


__all__ = ["VerifiedPageLabels", "read_verified_page_labels"]
