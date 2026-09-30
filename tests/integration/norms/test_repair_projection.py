"""The re-recognition ledger changes the text the deterministic projection emits.

`W39-CORPUS` built and guarded both halves independently: a ledger can hold clean replacement
text and `repaired_snapshot` gives that text a distinct identity. Before NORM-LEDGER-01 no
production function joined those halves. These tests pin the join and its fail-closed edge.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from auditmanager.norms import (
    PageRepair,
    RepairOutcome,
    ledger_of,
    recognised_text,
    repaired_snapshot,
    segment,
)
from auditmanager.norms.corpus_source import (
    RepairProjectionMismatch,
    segment_corpus,
    snapshot_of,
)

NOW = "2026-09-30T00:00:00+00:00"
SLUG = "СП_000_13330_2026"
BLOCK_ID = "blk_" + "a" * 32
RAW_TEXT = "The document is a technical table from a Russian construction standard."
REPAIRED_TEXT = (
    "##### 7.2 РАСЧЁТ ПО ПРЕДЕЛЬНЫМ СОСТОЯНИЯМ\n\n"
    "7.2.4 Расчёт элементов производят для сечений, нормальных к продольной оси."
)


def _markdown(text: str = RAW_TEXT) -> str:
    return f"""# Document: СП 000.13330.2026.pdf

Path: normative/СП 000.13330.2026.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 7

### BLOCK #1 [TEXT]: {BLOCK_ID}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop)

{text}
"""


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    document = root / SLUG
    document.mkdir(parents=True)
    (document / "results.md").write_text(_markdown(), encoding="utf-8")
    (document / "blocks.json").write_text(
        json.dumps({"document_id": "doc_source_0001"}), encoding="utf-8"
    )
    return root


def _repair(*, replacement: str | None = REPAIRED_TEXT) -> PageRepair:
    return PageRepair(
        document_slug=SLUG,
        block_id=BLOCK_ID,
        page_label=7,
        original_sha256=hashlib.sha256(RAW_TEXT.encode("utf-8")).hexdigest(),
        original_characters=len(RAW_TEXT),
        crop_sha256="1" * 64,
        outcome=(
            RepairOutcome.REPAIRED
            if replacement is not None
            else RepairOutcome.STILL_DEGENERATE
        ),
        replacement=replacement,
        attempts=(),
    )


def test_segment_anchors_paragraphs_in_the_effective_repaired_text() -> None:
    paragraphs, report = segment(
        SLUG, _markdown(), replacements={BLOCK_ID: REPAIRED_TEXT}
    )
    effective = recognised_text(_markdown(), replacements={BLOCK_ID: REPAIRED_TEXT})

    assert RAW_TEXT not in effective
    assert [paragraph.text for paragraph in paragraphs] == [
        "##### 7.2 РАСЧЁТ ПО ПРЕДЕЛЬНЫМ СОСТОЯНИЯМ",
        "7.2.4 Расчёт элементов производят для сечений, нормальных к продольной оси.",
    ]
    for paragraph in paragraphs:
        assert (
            effective[paragraph.char_offset : paragraph.char_offset + paragraph.char_length]
            == paragraph.text
        )
    assert report.recognised_characters == len(REPAIRED_TEXT)


def test_an_unknown_direct_replacement_is_refused() -> None:
    with pytest.raises(ValueError, match="absent from the document"):
        segment(SLUG, _markdown(), replacements={"blk_missing": REPAIRED_TEXT})


def test_the_whole_corpus_projection_applies_repair_and_carries_its_identity(
    corpus_root: Path,
) -> None:
    base = snapshot_of(corpus_root)
    ledger = ledger_of(base.snapshot_id, NOW, [_repair()])
    effective = repaired_snapshot(base, ledger)

    rows = list(
        segment_corpus(
            corpus_root,
            effective.snapshot_id,
            repair_ledger=ledger,
        )
    )

    assert len(rows) == 1
    report, paragraphs, chunks = rows[0]
    assert report.document_slug == SLUG
    assert RAW_TEXT not in "\n".join(paragraph.text for paragraph in paragraphs)
    assert REPAIRED_TEXT == "\n\n".join(paragraph.text for paragraph in paragraphs)
    assert {chunk.snapshot_id for chunk in chunks} == {effective.snapshot_id}
    assert "\n\n".join(chunk.text for chunk in chunks) == REPAIRED_TEXT


def test_an_unapplied_repair_keeps_raw_text_and_base_identity(corpus_root: Path) -> None:
    base = snapshot_of(corpus_root)
    ledger = ledger_of(base.snapshot_id, NOW, [_repair(replacement=None)])

    rows = list(segment_corpus(corpus_root, base.snapshot_id, repair_ledger=ledger))

    _report, paragraphs, chunks = rows[0]
    assert [paragraph.text for paragraph in paragraphs] == [RAW_TEXT]
    assert {chunk.snapshot_id for chunk in chunks} == {base.snapshot_id}


def test_a_ledger_from_another_snapshot_is_refused_before_projection(
    corpus_root: Path,
) -> None:
    ledger = ledger_of("another-snapshot", NOW, [_repair()])
    with pytest.raises(ValueError, match="attribute one corpus's repairs to another"):
        list(segment_corpus(corpus_root, "irrelevant", repair_ledger=ledger))


def test_the_requested_projection_identity_must_name_the_effective_text(
    corpus_root: Path,
) -> None:
    base = snapshot_of(corpus_root)
    ledger = ledger_of(base.snapshot_id, NOW, [_repair()])
    with pytest.raises(RepairProjectionMismatch, match="does not identify"):
        list(segment_corpus(corpus_root, base.snapshot_id, repair_ledger=ledger))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"document_slug": "absent-document"}, "document absent"),
        ({"block_id": "blk_absent"}, "block absent"),
        ({"page_label": 8}, "page 8 != 7"),
        ({"original_characters": len(RAW_TEXT) + 1}, "characters"),
        ({"original_sha256": "0" * 64}, "original_sha256"),
    ],
)
def test_a_partially_applicable_ledger_is_refused(
    corpus_root: Path, mutation: dict[str, object], message: str
) -> None:
    base = snapshot_of(corpus_root)
    repair = replace(_repair(), **mutation)
    ledger = ledger_of(base.snapshot_id, NOW, [repair])
    effective = repaired_snapshot(base, ledger)

    with pytest.raises(RepairProjectionMismatch, match=message):
        list(
            segment_corpus(
                corpus_root,
                effective.snapshot_id,
                repair_ledger=ledger,
            )
        )
