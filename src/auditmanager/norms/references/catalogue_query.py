"""Fail-closed decoding of a W57a catalogue for W57b reference resolution.

The expected digest and snapshot facts must come from a separately verified set
and its pinned snapshot. Migration 0022 has no verified-set table, so this
adapter deliberately performs no database read or custody assertion.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.norms.references.families import parse_designation
from auditmanager.norms.references.resolution import (
    CatalogueEntry,
    PinnedCatalogue,
    ReferenceRefused,
)
from auditmanager.norms.references.tokens import sql_designation_tokens


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"ndoc_[0-9A-HJKMNP-TV-Z]{26}\Z")
_FIELDS = frozenset(
    {
        "catalogue_version",
        "norms_snapshot_id",
        "content_key",
        "snapshot_content_digest",
        "document_count",
        "documents",
    }
)
_DOCUMENT_FIELDS = frozenset(
    {"norm_document_id", "slug", "designation_tokens", "title", "doc_type"}
)
_VERSION = "norm-catalogue-prep-v1"
_MAX_BYTES = 10_000_000


@dataclass(frozen=True, slots=True)
class CatalogueExpectation:
    """Independent facts to be read from a pinned, verified set and snapshot."""

    snapshot_id: str
    content_key: str
    snapshot_content_digest: str
    document_count: int
    catalogue_sha256: str


def _nfc(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or unicodedata.normalize("NFC", value) != value:
        raise ReferenceRefused(f"{label} must be nonempty NFC text")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ReferenceRefused(f"{label} must be lowercase SHA-256")
    return value


def _decode(blob: bytes) -> dict[str, Any]:
    if not isinstance(blob, bytes) or not blob or len(blob) > _MAX_BYTES:
        raise ReferenceRefused("catalogue must be bounded nonempty bytes")
    try:
        payload = json.loads(blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReferenceRefused("catalogue is not UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _FIELDS:
        raise ReferenceRefused("catalogue fields differ from frozen format")
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except UnicodeError as exc:
        raise ReferenceRefused("catalogue contains invalid Unicode") from exc
    if encoded != blob:
        raise ReferenceRefused("catalogue is not canonical JSON")
    return payload


def load_pinned_catalogue(
    *,
    blob: bytes,
    expected: CatalogueExpectation,
    listed_unparsed_slugs: tuple[str, ...],
) -> PinnedCatalogue:
    """Validate exact catalogue bytes before passing them to the pure resolver.

    The caller must fetch `blob` through a confirmed catalogue custody binding
    and obtain `expected` from the pinned verified set/snapshot. This function
    validates those supplied facts but cannot authenticate their source.
    """
    try:
        require_snapshot_id(expected.snapshot_id)
    except (TypeError, ValueError) as exc:
        raise ReferenceRefused("invalid expected snapshot id") from exc
    _nfc(expected.content_key, "expected content key")
    _digest(expected.snapshot_content_digest, "expected snapshot content digest")
    _digest(expected.catalogue_sha256, "expected catalogue digest")
    if type(expected.document_count) is not int or expected.document_count <= 0:
        raise ReferenceRefused("expected document count must be positive")
    if not isinstance(listed_unparsed_slugs, tuple):
        raise ReferenceRefused("unparsed slug listing must be a tuple")
    listed: set[str] = set()
    for slug in listed_unparsed_slugs:
        _nfc(slug, "listed unparsed slug")
        if slug in listed:
            raise ReferenceRefused("duplicate listed unparsed slug")
        listed.add(slug)
    if not isinstance(blob, bytes) or not blob or len(blob) > _MAX_BYTES:
        raise ReferenceRefused("catalogue must be bounded nonempty bytes")
    if hashlib.sha256(blob).hexdigest() != expected.catalogue_sha256:
        raise ReferenceRefused("catalogue digest differs from pinned expected digest")
    payload = _decode(blob)
    if payload["catalogue_version"] != _VERSION:
        raise ReferenceRefused("unknown catalogue version")
    if payload["norms_snapshot_id"] != expected.snapshot_id:
        raise ReferenceRefused("catalogue snapshot differs from pinned snapshot")
    if payload["content_key"] != expected.content_key:
        raise ReferenceRefused("catalogue content key differs from pinned snapshot")
    if payload["snapshot_content_digest"] != expected.snapshot_content_digest:
        raise ReferenceRefused("catalogue content digest differs from pinned snapshot")
    rows = payload["documents"]
    if (
        type(payload["document_count"]) is not int
        or payload["document_count"] != expected.document_count
        or not isinstance(rows, list)
        or len(rows) != expected.document_count
    ):
        raise ReferenceRefused("catalogue document count differs from pinned snapshot")
    documents: list[CatalogueEntry] = []
    ids: set[str] = set()
    slugs: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != _DOCUMENT_FIELDS:
            raise ReferenceRefused("catalogue document fields differ from frozen format")
        doc_id = _nfc(row["norm_document_id"], "document id")
        slug = _nfc(row["slug"], "slug")
        _nfc(row["title"], "title")
        _nfc(row["doc_type"], "document type")
        if _DOCUMENT_ID.fullmatch(doc_id) is None or doc_id in ids or slug in slugs:
            raise ReferenceRefused("duplicate or invalid catalogue identity")
        ids.add(doc_id)
        slugs.add(slug)
        raw_tokens = row["designation_tokens"]
        if not isinstance(raw_tokens, list) or not raw_tokens:
            raise ReferenceRefused("missing catalogue designation tokens")
        tokens = tuple(_nfc(token, "designation token") for token in raw_tokens)
        if tokens != sql_designation_tokens(slug):
            raise ReferenceRefused("catalogue SQL designation tokens mismatch")
        parsed = parse_designation(slug)
        if parsed is None and slug not in listed:
            raise ReferenceRefused("unlisted unparsed catalogue slug")
        if parsed is not None and slug in listed:
            raise ReferenceRefused("stale unparsed catalogue listing")
        documents.append(CatalogueEntry(doc_id, slug, tokens))
    if listed - slugs:
        raise ReferenceRefused("unparsed listing names absent catalogue slug")
    if [doc.document_id for doc in documents] != sorted(ids):
        raise ReferenceRefused("catalogue document order is not canonical")
    return PinnedCatalogue(expected.snapshot_id, tuple(documents), listed_unparsed_slugs)


__all__ = ["CatalogueExpectation", "load_pinned_catalogue"]
