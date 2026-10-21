"""W57b catalogue bytes are admitted only against independent pinned facts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.norms.references.catalogue_query import (
    CatalogueExpectation,
    load_pinned_catalogue,
)
from auditmanager.norms.references.resolution import (
    NEWER,
    ReferenceRefused,
    TextPage,
    extract_references,
    resolve_references,
)
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.norms.retrieval.artifact import SnapshotBinding, canonical_blob
from auditmanager.norms.retrieval.catalogue import CatalogueDocument, build_catalogue


SNAPSHOT = "ns_" + "0" * 26


def _row(number: int, slug: str) -> dict[str, object]:
    return {
        "norm_document_id": f"ndoc_{number:026d}",
        "slug": slug,
        "designation_tokens": sql_designation_tokens(slug),
        "title": f"Document {number}",
        "doc_type": "СП",
    }


def _payload() -> dict[str, object]:
    return {
        "catalogue_version": "norm-catalogue-prep-v1",
        "norms_snapshot_id": SNAPSHOT,
        "content_key": "reviewed-key",
        "snapshot_content_digest": "a" * 64,
        "document_count": 3,
        "documents": [
            _row(1, "СП_54.13330.2022"),
            _row(2, "СП_54.13330.2024"),
            _row(3, "неизвестный_документ"),
        ],
    }


def _load(
    payload: dict[str, object] | None = None,
    *,
    listed: tuple[str, ...] = ("неизвестный_документ",),
    expected: CatalogueExpectation | None = None,
    blob: bytes | None = None,
):
    canonical = canonical_blob(_payload() if payload is None else payload)
    facts = expected or CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 3, canonical.sha256)
    return load_pinned_catalogue(
        blob=canonical.data if blob is None else blob,
        expected=facts,
        listed_unparsed_slugs=listed,
    )


def test_exact_bytes_resolve_newer_edition() -> None:
    rows = _payload()["documents"]
    built = build_catalogue(
        snapshot=SnapshotBinding(SNAPSHOT, "reviewed-key", "a" * 64, "bge-build", 3),
        documents=tuple(
            CatalogueDocument(
                row["norm_document_id"],
                row["slug"],
                row["designation_tokens"],
                row["title"],
                row["doc_type"],
            )
            for row in rows
        ),
    )
    catalogue = load_pinned_catalogue(
        blob=built.data,
        expected=CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 3, built.sha256),
        listed_unparsed_slugs=("неизвестный_документ",),
    )
    assert len(catalogue.documents) == 3
    report = resolve_references(
        extraction=extract_references((TextPage("7", "СП 54.13330.2022"),)),
        catalogue=catalogue,
        pinned_snapshot_id=SNAPSHOT,
    )
    assert report.references[0].outcome == NEWER
    assert report.references[0].matched_document_id == f"ndoc_{2:026d}"


def test_digest_and_canonical_bytes_are_required() -> None:
    canonical = canonical_blob(_payload())
    facts = CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 3, canonical.sha256)
    with pytest.raises(ReferenceRefused, match="digest differs"):
        load_pinned_catalogue(blob=canonical.data + b" ", expected=facts, listed_unparsed_slugs=("неизвестный_документ",))
    pretty = json.dumps(_payload(), ensure_ascii=False, indent=2).encode()
    with pytest.raises(ReferenceRefused, match="not canonical"):
        _load(expected=replace(facts, catalogue_sha256=hashlib.sha256(pretty).hexdigest()), blob=pretty)
    with pytest.raises(ReferenceRefused, match="bounded"):
        _load(blob=b"x" * 10_000_001)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("norms_snapshot_id", "ns_" + "1" * 26, "snapshot differs"),
        ("content_key", "other-key", "content key differs"),
        ("snapshot_content_digest", "b" * 64, "content digest differs"),
        ("document_count", 2, "document count differs"),
        ("catalogue_version", "future-v2", "unknown catalogue version"),
    ],
)
def test_pinned_snapshot_facts_and_version_are_exact(field: str, value: object, message: str) -> None:
    payload = _payload()
    payload[field] = value
    with pytest.raises(ReferenceRefused, match=message):
        _load(payload)


def test_missing_extra_and_duplicate_document_rows_are_refused() -> None:
    payload = _payload()
    payload["documents"] = payload["documents"][:-1]
    with pytest.raises(ReferenceRefused, match="document count differs"):
        _load(payload)
    payload = _payload()
    payload["documents"][2] = payload["documents"][1]
    with pytest.raises(ReferenceRefused, match="duplicate or invalid"):
        _load(payload)
    payload = _payload()
    payload["documents"][0]["unexpected"] = "field"
    with pytest.raises(ReferenceRefused, match="fields differ"):
        _load(payload)


def test_tokens_order_and_reviewed_unparsed_listing_are_required() -> None:
    payload = _payload()
    payload["documents"][0]["designation_tokens"] = ["wrong"]
    with pytest.raises(ReferenceRefused, match="tokens mismatch"):
        _load(payload)
    payload = _payload()
    payload["documents"] = list(reversed(payload["documents"]))
    with pytest.raises(ReferenceRefused, match="order is not canonical"):
        _load(payload)
    with pytest.raises(ReferenceRefused, match="unlisted unparsed"):
        _load(listed=())
    with pytest.raises(ReferenceRefused, match="stale unparsed"):
        _load(listed=("неизвестный_документ", "СП_54.13330.2022"))
    with pytest.raises(ReferenceRefused, match="absent catalogue"):
        _load(listed=("неизвестный_документ", "unknown_missing"))


def test_non_nfc_metadata_and_invalid_unicode_are_refused() -> None:
    payload = _payload()
    payload["documents"][0]["title"] = "e\u0301"
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    facts = CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 3, hashlib.sha256(blob).hexdigest())
    with pytest.raises(ReferenceRefused, match="NFC"):
        _load(expected=facts, blob=blob)
    payload = _payload()
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    raw = raw.replace("Document 1", "\\ud800")
    blob = raw.encode("utf-8")
    facts = CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 3, hashlib.sha256(blob).hexdigest())
    with pytest.raises(ReferenceRefused, match="invalid Unicode"):
        _load(expected=facts, blob=blob)


def test_invalid_independent_expectation_is_refused() -> None:
    valid = canonical_blob(_payload())
    facts = CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 3, valid.sha256)
    for invalid, message in (
        (replace(facts, snapshot_id="ns_bad"), "invalid expected snapshot"),
        (replace(facts, document_count=0), "document count must be positive"),
        (replace(facts, catalogue_sha256="A" * 64), "lowercase SHA-256"),
    ):
        with pytest.raises(ReferenceRefused, match=message):
            _load(expected=invalid)
