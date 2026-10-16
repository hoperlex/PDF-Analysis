"""The W57b page bridge preserves prepared PDF text and global anchors."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.norms.references.catalogue_query import CatalogueExpectation
from auditmanager.norms.references.pipeline import run_reference_pipeline
from auditmanager.norms.references.resolution import ReferenceRefused
from auditmanager.norms.references.text_pages import reference_pages_from_text_layer
from auditmanager.norms.references.tokens import sql_designation_tokens


VERSION = "ver_01"
SNAPSHOT = "ns_" + "0" * 26


def _layer(*page_texts: str):
    cursor = 0
    pages = []
    for number, text in enumerate(page_texts, start=1):
        pages.append({"page_number": number, "char_start": cursor, "char_end": cursor + len(text), "text": text})
        cursor += len(text)
    return load_text_layer({
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "normalization": {"id": "unicode-nfc"},
        "version_uid": VERSION,
        "pages": pages,
        "total_char_count": cursor,
    })


def test_cyrillic_and_multibyte_offsets_and_scanned_empty_page() -> None:
    first = "А😀Б"
    third = "СП 54.13330.2022"
    layer = _layer(first, "", third)
    pages = reference_pages_from_text_layer(text_layer=layer, version_uid=VERSION, page_count=3)
    assert [(p.page_label, p.page_number, p.char_start, p.text) for p in pages] == [
        ("1", 1, 0, first),
        ("2", 2, len(first), None),
        ("3", 3, len(first), third),
    ]
    assert len(first.encode("utf-8")) > len(first)
    assert layer.document_text == first + third
    assert layer.document_text[pages[2].char_start:] == third


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda layer: replace(layer, version_uid="ver_other"), "Version differs"),
        (lambda layer: replace(layer, pages=layer.pages[::-1]), "numbered 1..N"),
        (lambda layer: replace(layer, pages=(layer.pages[0], replace(layer.pages[1], page_number=3))), "numbered 1..N"),
        (lambda layer: replace(layer, pages=(layer.pages[0], replace(layer.pages[1], char_start=0))), "offsets differ"),
        (lambda layer: replace(layer, pages=(replace(layer.pages[0], char_end=99), layer.pages[1])), "offsets differ"),
        (lambda layer: replace(layer, pages=(replace(layer.pages[0], text="changed"), layer.pages[1])), "offsets differ"),
        (lambda layer: replace(layer, pages=(None, layer.pages[1])), "numbered 1..N"),
        (lambda layer: replace(layer, document_text="extra"), "document text differs"),
        (lambda layer: replace(layer, normalization_id=""), "normalization is undeclared"),
    ],
)
def test_forged_text_layer_is_refused(change, message: str) -> None:
    with pytest.raises(ReferenceRefused, match=message):
        reference_pages_from_text_layer(
            text_layer=change(_layer("А😀Б", "СП 54.13330.2022")),
            version_uid=VERSION,
            page_count=2,
        )


def test_independent_version_and_page_count_are_required() -> None:
    layer = _layer("а", "")
    for version, count, message in [
        ("ver_other", 2, "Version differs"),
        (VERSION, 1, "page count differs"),
        (VERSION, 0, "page count is invalid"),
        (VERSION, True, "page count is invalid"),
    ]:
        with pytest.raises(ReferenceRefused, match=message):
            reference_pages_from_text_layer(text_layer=layer, version_uid=version, page_count=count)


def test_pipeline_evidence_roundtrip_uses_same_source_offsets() -> None:
    layer = _layer("А😀Б", "", "См. СП 54.13330.2022.")
    pages = reference_pages_from_text_layer(text_layer=layer, version_uid=VERSION, page_count=3)
    slugs = ("СП_54.13330.2022", "СП_54.13330.2024")
    documents = [
        {
            "norm_document_id": f"ndoc_{number:026d}",
            "slug": slug,
            "designation_tokens": sql_designation_tokens(slug),
            "title": slug,
            "doc_type": "СП",
        }
        for number, slug in enumerate(slugs, start=1)
    ]
    blob = json.dumps({
        "catalogue_version": "norm-catalogue-prep-v1",
        "norms_snapshot_id": SNAPSHOT,
        "content_key": "reviewed-key",
        "snapshot_content_digest": "a" * 64,
        "document_count": len(documents),
        "documents": documents,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    expected = CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 2, hashlib.sha256(blob).hexdigest())
    result = run_reference_pipeline(
        catalogue_blob=blob,
        expected_catalogue=expected,
        listed_unparsed_slugs=(),
        pages=pages,
    )
    assert result.report.unread_pages == ("2",)
    candidate, = result.newer_candidates
    evidence, = candidate.evidence
    assert evidence.page_number == 3
    assert layer.document_text[evidence.char_start:evidence.char_end] == evidence.quote
    assert evidence.char_start >= len("А😀Б")
