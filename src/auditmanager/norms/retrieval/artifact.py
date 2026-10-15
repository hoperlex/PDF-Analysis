"""Pure, byte-exact W57a retrieval-set preparation.

The caller owns review, snapshot qualification, DB totality and custody. This
module binds their supplied evidence into deterministic bytes; it never claims
that an input came from a promoted snapshot.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from auditmanager.norms.citation_prep import NORM_QUOTE_VERSION, NORM_VALUE_VERSION
from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.norms.retrieval.ranking import (
    BUILDER_VERSION as RANKING_VERSION,
    PROMPT_CHAR_CAP,
    PromptRow,
    PromptSelection,
    RetrievalParagraph,
)


SET_BUILDER_VERSION = "norm-retrieval-set-prep-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ArtifactRefused(ValueError):
    """A supplied identity or canonical row cannot be bound into a set."""


@dataclass(frozen=True, slots=True)
class CanonicalBlob:
    data: bytes
    sha256: str


@dataclass(frozen=True, slots=True)
class SnapshotBinding:
    snapshot_id: str
    content_key: str
    content_digest: str
    embedding_build: str
    document_count: int


@dataclass(frozen=True, slots=True)
class SetIdentity:
    map_sha256: str
    snapshot_id: str
    reviewed_content_key: str
    embedding_build: str
    builder_version: str = SET_BUILDER_VERSION


@dataclass(frozen=True, slots=True)
class SourceParagraph:
    paragraph: RetrievalParagraph
    text_sha256: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _nfc(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or unicodedata.normalize("NFC", value) != value:
        raise ArtifactRefused(f"{field} must be nonempty NFC text")
    return value


def _check_sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ArtifactRefused(f"{field} must be lowercase SHA-256")
    return value


def _check_json(value: Any) -> None:
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ArtifactRefused("JSON contains non-NFC text")
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ArtifactRefused("JSON object key must be text")
            _check_json(key)
            _check_json(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _check_json(child)
    elif value is None or isinstance(value, (bool, int)):
        return
    else:
        raise ArtifactRefused("JSON contains an unsupported value")


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical UTF-8 JSON: sorted keys, compact separators, NFC, no floats."""
    _check_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_blob(value: Any) -> CanonicalBlob:
    data = canonical_json_bytes(value)
    return CanonicalBlob(data, _sha256(data))


def _validated_snapshot(snapshot: SnapshotBinding) -> None:
    try:
        require_snapshot_id(snapshot.snapshot_id)
    except (TypeError, ValueError) as exc:
        raise ArtifactRefused("invalid snapshot id") from exc
    _nfc(snapshot.content_key, "content key")
    _check_sha256(snapshot.content_digest, "snapshot content digest")
    _nfc(snapshot.embedding_build, "embedding build")
    if type(snapshot.document_count) is not int or snapshot.document_count <= 0:
        raise ArtifactRefused("snapshot document count must be positive")


def _decoded_map(map_bytes: bytes) -> dict[str, Any]:
    if not isinstance(map_bytes, bytes) or len(map_bytes) > 10_000_000:
        raise ArtifactRefused("map must be bounded canonical JSON bytes")
    try:
        mapping = json.loads(map_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactRefused("map is not UTF-8 JSON") from exc
    if not isinstance(mapping, dict) or canonical_json_bytes(mapping) != map_bytes:
        raise ArtifactRefused("map is not canonical JSON")
    return mapping


def _prompt_row_object(row: PromptRow) -> dict[str, Any]:
    return {
        "item_id": row.item_id,
        "label": row.label,
        "norm_document_id": row.document_id,
        "norm_paragraph_id": row.paragraph_id,
        "designation": row.designation,
        "title": row.title,
        "ordinal": row.ordinal,
        "clause_number": row.clause_number,
        "page_label": row.page_label,
        "text": row.text,
        "text_sha256": row.text_sha256,
    }


def _source_rows(
    paragraphs: tuple[SourceParagraph, ...], mapped_document_ids: tuple[str, ...]
) -> tuple[dict[str, Any], ...]:
    if not paragraphs:
        raise ArtifactRefused("mapped documents have no canonical paragraphs")
    if len(mapped_document_ids) != len(set(mapped_document_ids)) or not mapped_document_ids:
        raise ArtifactRefused("duplicate or empty mapped document ids")
    expected_docs = set(mapped_document_ids)
    identities: set[str] = set()
    ordinals: dict[str, set[int]] = {doc: set() for doc in expected_docs}
    rows: list[dict[str, Any]] = []
    for source in paragraphs:
        row = source.paragraph
        if row.document_id not in expected_docs or row.paragraph_id in identities:
            raise ArtifactRefused("unmapped document or duplicate paragraph identity")
        identities.add(row.paragraph_id)
        if (
            type(row.ordinal) is not int
            or row.ordinal < 0
            or row.ordinal in ordinals[row.document_id]
        ):
            raise ArtifactRefused("duplicate or invalid paragraph ordinal")
        ordinals[row.document_id].add(row.ordinal)
        for field in ("document_id", "paragraph_id", "designation", "title", "text"):
            _nfc(getattr(row, field), field)
        for field in ("clause_number", "page_label"):
            value = getattr(row, field)
            if value is not None:
                _nfc(value, field)
        _check_sha256(source.text_sha256, "paragraph text digest")
        if _sha256(row.text.encode("utf-8")) != source.text_sha256:
            raise ArtifactRefused("paragraph content digest mismatch")
        if type(row.reliable) is not bool:
            raise ArtifactRefused("paragraph reliability must be boolean")
        if row.reliable:
            rows.append(
                {
                    "norm_document_id": row.document_id,
                    "norm_paragraph_id": row.paragraph_id,
                    "designation": row.designation,
                    "title": row.title,
                    "ordinal": row.ordinal,
                    "clause_number": row.clause_number,
                    "page_label": row.page_label,
                    "text": row.text,
                    "text_sha256": source.text_sha256,
                }
            )
    for doc, seen in ordinals.items():
        if seen != set(range(len(seen))):
            raise ArtifactRefused(f"canonical paragraph ordinals incomplete for {doc}")
        if not any(row["norm_document_id"] == doc for row in rows):
            raise ArtifactRefused(f"mapped document has no reliable text: {doc}")
    return tuple(sorted(rows, key=lambda row: (row["norm_document_id"], row["ordinal"])))


def build_retrieval_set(
    *,
    identity: SetIdentity,
    map_bytes: bytes,
    snapshot: SnapshotBinding,
    selection: PromptSelection,
    paragraphs: tuple[SourceParagraph, ...],
) -> CanonicalBlob:
    """Bind one supplied reviewed map and selected prompt to full reliable text.

    The map's canonical JSON must carry `reviewed_content_key`,
    `norms_snapshot_id`, `embedding_build` and `mapped_document_ids`. The later
    map owner must record these before review and provide the reviewed bytes.
    """
    _validated_snapshot(snapshot)
    _check_sha256(identity.map_sha256, "map digest")
    for field in ("reviewed_content_key", "embedding_build"):
        _nfc(getattr(identity, field), field)
    if identity.builder_version != SET_BUILDER_VERSION:
        raise ArtifactRefused("unknown set builder version")
    if (
        identity.snapshot_id != snapshot.snapshot_id
        or identity.reviewed_content_key != snapshot.content_key
        or identity.embedding_build != snapshot.embedding_build
    ):
        raise ArtifactRefused("snapshot binding does not match set identity")
    if not isinstance(map_bytes, bytes) or _sha256(map_bytes) != identity.map_sha256:
        raise ArtifactRefused("reviewed map digest mismatch")
    mapping = _decoded_map(map_bytes)
    for field, expected in (
        ("reviewed_content_key", identity.reviewed_content_key),
        ("norms_snapshot_id", identity.snapshot_id),
        ("embedding_build", identity.embedding_build),
    ):
        if mapping.get(field) != expected:
            raise ArtifactRefused(f"reviewed map {field} mismatch")
    mapped = mapping.get("mapped_document_ids")
    if not isinstance(mapped, list) or not mapped or any(
        not isinstance(doc, str) or not doc.startswith("ndoc_") for doc in mapped
    ):
        raise ArtifactRefused("map has no valid mapped_document_ids")
    mapped_ids = tuple(mapped)
    map_items = mapping.get("items")
    if not isinstance(map_items, list) or not map_items or any(
        not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]
        for item in map_items
    ):
        raise ArtifactRefused("map has no valid item ids")
    item_ids = tuple(item["id"] for item in map_items)
    if len(set(item_ids)) != len(item_ids):
        raise ArtifactRefused("duplicate map item id")
    source_rows = _source_rows(paragraphs, mapped_ids)
    by_id = {row["norm_paragraph_id"]: row for row in source_rows}
    if not selection.rows or len(selection.prompt_part) > PROMPT_CHAR_CAP:
        raise ArtifactRefused("prompt part is empty or exceeds cap")
    if (
        type(selection.windows_per_item) is not int
        or not 0 <= selection.windows_per_item <= 3
        or type(selection.inside_target_windows_dropped) is not bool
    ):
        raise ArtifactRefused("invalid prompt selection metadata")
    ordered_items = tuple(dict.fromkeys(row.item_id for row in selection.rows))
    if ordered_items != item_ids:
        raise ArtifactRefused("selected item ids differ from reviewed map")
    groups = [row.item_id for row in selection.rows]
    if groups != sorted(groups, key=lambda item_id: item_ids.index(item_id)):
        raise ArtifactRefused("prompt rows interleave map items")
    prompt_rows: list[dict[str, Any]] = []
    selected_keys: set[tuple[str, str]] = set()
    last_order: tuple[int, str, int, str] | None = None
    for index, row in enumerate(selection.rows, 1):
        source = by_id.get(row.paragraph_id)
        if row.label != f"N{index}" or source is None:
            raise ArtifactRefused("prompt label or paragraph is invalid")
        selected_key = (row.item_id, row.paragraph_id)
        order = (item_ids.index(row.item_id), row.designation, row.ordinal, row.document_id)
        if selected_key in selected_keys or (last_order is not None and order < last_order):
            raise ArtifactRefused("prompt rows are duplicated or out of order")
        selected_keys.add(selected_key)
        last_order = order
        prompt = _prompt_row_object(row)
        for key in (
            "norm_document_id", "norm_paragraph_id", "designation", "title",
            "ordinal", "clause_number", "page_label", "text", "text_sha256",
        ):
            if prompt[key] != source[key]:
                raise ArtifactRefused("prompt row differs from full reliable text")
        prompt_rows.append(prompt)
    expected_part = canonical_json_bytes(
        {"builder_version": RANKING_VERSION, "paragraphs": prompt_rows}
    ).decode("utf-8")
    if selection.prompt_part != expected_part:
        raise ArtifactRefused("prompt part differs from exact selected rows")
    return canonical_blob(
        {
            "builder_version": SET_BUILDER_VERSION,
            "identity": {
                "map_sha256": identity.map_sha256,
                "reviewed_content_key": identity.reviewed_content_key,
                "norms_snapshot_id": identity.snapshot_id,
                "embedding_build": identity.embedding_build,
            },
            "snapshot_content_digest": snapshot.content_digest,
            "ranking_version": RANKING_VERSION,
            "norm_quote_version": NORM_QUOTE_VERSION,
            "norm_value_version": NORM_VALUE_VERSION,
            "prompt_part": selection.prompt_part,
            "prompt_part_characters": len(selection.prompt_part),
            "windows_per_item": selection.windows_per_item,
            "inside_target_windows_dropped": selection.inside_target_windows_dropped,
            "rebinding_paragraphs": source_rows,
        }
    )
