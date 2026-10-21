"""Pure AR v3 input from supplied retrieval-set bytes.

Only the later caller can prove that the bytes came from the Run-pinned,
custody-checked Blob. Parsing bytes here grants no publication authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from auditmanager.norms.public import NormLabelBinding, NormParagraph
from auditmanager.shared.identity import NormDocumentId, NormParagraphId, NormsSnapshotId


MAX_SET_BYTES = 10_000_000
MAX_PROMPT_CHARACTERS = 22_000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SET_VERSION = "norm-retrieval-set-prep-v1"
_RANKING_VERSION = "norm-ranking-prep-v1"
_QUOTE_VERSION = "norm-quote-v1"
_VALUE_VERSION = "norm-value-v1"
_SOURCE_FIELDS = frozenset({
    "norm_document_id", "norm_paragraph_id", "designation", "title",
    "ordinal", "clause_number", "page_label", "text", "text_sha256",
})


class V3SetInputRefused(ValueError):
    """The supplied bytes cannot serve as a v3 prompt and grounding input."""


@dataclass(frozen=True, slots=True)
class V3SetInput:
    prompt_part: str
    paragraphs: tuple[NormParagraph, ...]
    label_bindings: tuple[NormLabelBinding, ...]


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise V3SetInputRefused("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise V3SetInputRefused(f"invalid_json_constant:{value}")


def _canonical(value: Any) -> bytes:
    def check(node: Any) -> None:
        if isinstance(node, str):
            if unicodedata.normalize("NFC", node) != node:
                raise V3SetInputRefused("non_nfc_set_text")
        elif isinstance(node, dict):
            for key, child in node.items():
                check(key)
                check(child)
        elif isinstance(node, list):
            for child in node:
                check(child)
        elif node is None or type(node) in {bool, int}:
            return
        else:
            raise V3SetInputRefused("unsupported_set_value")
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise V3SetInputRefused("set_json_invalid") from exc
    try:
        canonical = _canonical(decoded)
    except RecursionError as exc:
        raise V3SetInputRefused("set_json_too_deep") from exc
    except UnicodeError as exc:
        raise V3SetInputRefused("set_json_invalid") from exc
    if not isinstance(decoded, dict) or canonical != raw:
        raise V3SetInputRefused("set_json_noncanonical")
    return decoded


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _id(value: Any, identity: type) -> bool:
    if not isinstance(value, str):
        return False
    try:
        identity.parse(value)
    except (TypeError, ValueError):
        return False
    return True


def _source_row(row: Any) -> bool:
    return (
        isinstance(row, dict) and set(row) == _SOURCE_FIELDS
        and _id(row["norm_document_id"], NormDocumentId)
        and _id(row["norm_paragraph_id"], NormParagraphId)
        and all(_text(row[key]) for key in ("designation", "title", "text"))
        and type(row["ordinal"]) is int and row["ordinal"] >= 0
        and all(value is None or _text(value)
                for value in (row["clause_number"], row["page_label"]))
        and _sha(row["text_sha256"])
        and hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        == row["text_sha256"]
    )


def parse_v3_set_input(
    data: bytes, *, expected_sha256: str, expected_snapshot_id: str,
    expected_map_sha256: str,
) -> V3SetInput:
    """Bind supplied canonical set bytes to expected identities and grounding inputs.

    `expected_*` values must themselves come from a registered profile and
    the Run-pinned, custody-checked set; this function cannot establish that.
    """
    if (type(data) is not bytes or not 1 <= len(data) <= MAX_SET_BYTES
            or not _sha(expected_sha256) or not _sha(expected_map_sha256)
            or not _id(expected_snapshot_id, NormsSnapshotId)
            or hashlib.sha256(data).hexdigest() != expected_sha256):
        raise V3SetInputRefused("set_input_identity_invalid")
    payload = _decode(data)
    if set(payload) != {
        "builder_version", "identity", "snapshot_content_digest",
        "ranking_version", "norm_quote_version", "norm_value_version",
        "prompt_part", "prompt_part_characters", "windows_per_item",
        "inside_target_windows_dropped", "rebinding_paragraphs",
    }:
        raise V3SetInputRefused("set_shape_invalid")
    identity = payload["identity"]
    if (not isinstance(identity, dict) or set(identity) != {
        "map_sha256", "reviewed_content_key", "norms_snapshot_id", "embedding_build",
    } or identity["map_sha256"] != expected_map_sha256
            or identity["norms_snapshot_id"] != expected_snapshot_id
            or not _text(identity["reviewed_content_key"])
            or not _text(identity["embedding_build"])
            or not _sha(payload["snapshot_content_digest"])
            or payload["builder_version"] != _SET_VERSION
            or payload["ranking_version"] != _RANKING_VERSION
            or payload["norm_quote_version"] != _QUOTE_VERSION
            or payload["norm_value_version"] != _VALUE_VERSION
            or type(payload["windows_per_item"]) is not int
            or not 0 <= payload["windows_per_item"] <= 3
            or type(payload["inside_target_windows_dropped"]) is not bool):
        raise V3SetInputRefused("set_profile_or_version_mismatch")
    part = payload["prompt_part"]
    if (not isinstance(part, str) or not 1 <= len(part) <= MAX_PROMPT_CHARACTERS
            or type(payload["prompt_part_characters"]) is not int
            or payload["prompt_part_characters"] != len(part)):
        raise V3SetInputRefused("prompt_part_size_invalid")
    source_rows = payload["rebinding_paragraphs"]
    if not isinstance(source_rows, list) or not source_rows:
        raise V3SetInputRefused("rebinding_rows_missing")
    by_id: dict[str, dict[str, Any]] = {}
    seen_ordinals: set[tuple[str, int]] = set()
    paragraphs: list[NormParagraph] = []
    for row in source_rows:
        if (not _source_row(row) or row["norm_paragraph_id"] in by_id
                or (row["norm_document_id"], row["ordinal"]) in seen_ordinals):
            raise V3SetInputRefused("rebinding_row_invalid")
        by_id[row["norm_paragraph_id"]] = row
        seen_ordinals.add((row["norm_document_id"], row["ordinal"]))
        paragraphs.append(NormParagraph(
            paragraph_id=row["norm_paragraph_id"],
            document_id=row["norm_document_id"], text=row["text"],
        ))
    if source_rows != sorted(source_rows, key=lambda row: (
        row["norm_document_id"], row["ordinal"]
    )):
        raise V3SetInputRefused("rebinding_order_invalid")
    try:
        prompt = _decode(part.encode("utf-8"))
    except V3SetInputRefused as exc:
        raise V3SetInputRefused("prompt_part_noncanonical") from exc
    if (set(prompt) != {"builder_version", "paragraphs"}
            or prompt["builder_version"] != _RANKING_VERSION
            or not isinstance(prompt["paragraphs"], list)
            or not prompt["paragraphs"]):
        raise V3SetInputRefused("prompt_part_shape_invalid")
    labels: list[NormLabelBinding] = []
    seen_pairs: set[tuple[str, str]] = set()
    closed_items: set[str] = set()
    last_item: str | None = None
    last_order: tuple[str, int, str] | None = None
    for ordinal, row in enumerate(prompt["paragraphs"], 1):
        if (not isinstance(row, dict)
                or set(row) != _SOURCE_FIELDS | {"item_id", "label"}
                or not _text(row["item_id"]) or row["label"] != f"N{ordinal}"
                or not _source_row({key: row[key] for key in _SOURCE_FIELDS})
                or by_id.get(row["norm_paragraph_id"]) != {
                    key: row[key] for key in _SOURCE_FIELDS
                }):
            raise V3SetInputRefused("prompt_row_invalid")
        pair = (row["item_id"], row["norm_paragraph_id"])
        if pair in seen_pairs or row["item_id"] in closed_items:
            raise V3SetInputRefused("prompt_selection_duplicate_or_interleaved")
        order = (row["designation"], row["ordinal"], row["norm_document_id"])
        if row["item_id"] == last_item and last_order is not None and order < last_order:
            raise V3SetInputRefused("prompt_row_order_invalid")
        seen_pairs.add(pair)
        if last_item is not None and row["item_id"] != last_item:
            closed_items.add(last_item)
        last_item = row["item_id"]
        last_order = order
        labels.append(NormLabelBinding(row["label"], row["norm_paragraph_id"]))
    return V3SetInput(part, tuple(paragraphs), tuple(labels))


__all__ = ["V3SetInput", "V3SetInputRefused", "parse_v3_set_input"]
