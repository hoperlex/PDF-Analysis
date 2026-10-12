"""`W54-SNAPSHOT-01`: reliability-aware projection, the `characters-v1` refusal and `D-126`.

Container-free. The database half of each rule is in
`tests/integration/db/test_norms_corpus_migration.py` (a heavy step for the window).

- **`F-4`.** A block the repair ledger holds that did not end ``REPAIRED`` keeps its corpus
  text, and every paragraph drawn from it is marked unreliable. ``characters-v2`` skips those
  paragraphs and breaks a chunk at each one: every reliable paragraph covered exactly once,
  exactly the unreliable set skipped. ``characters-v1`` joins every paragraph, so it is
  refused over a snapshot with any unreliable block.
- **`D-126`.** A segmentation profile other than the literal ``markdown-v1`` appends
  ``+seg-<profile>`` after the digest of both stored keys; ``markdown-v1`` adds nothing.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path

import pytest

from auditmanager.norms import (
    CHUNKING_PROFILE_VERSION,
    DEFAULT_CHUNKING_VERSION,
    RELIABLE_CHUNKING_PROFILE_VERSION,
    ChunkingRefused,
    PageRepair,
    RepairOutcome,
    TextReliability,
    chunk_paragraphs,
    join_into_chunks,
    ledger_of,
    repaired_snapshot,
    segment,
    segmentation,
    verify_coverage,
    with_segmentation_profile,
)
from auditmanager.norms.chunking import chunking_profile, parse_chunking_profile
from auditmanager.norms.corpus_source import (
    open_corpus_projection,
    segment_corpus,
    snapshot_of,
)
from auditmanager.norms.segmentation import blocks

NOW = "2026-10-12T00:00:00+00:00"
SLUG = "СП_001_13330_2026"
BLOCK_IDS = tuple(f"blk_{letter * 32}" for letter in "abc")

#: Three blocks on three pages, two paragraphs each. Block 2 is the one the ledger marks.
MARKDOWN = f"""# Document: {SLUG}.pdf

Path: normative/{SLUG}.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 1

### BLOCK #1 [TEXT]: {BLOCK_IDS[0]}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop/1)

1.1. Первый пункт первой страницы устанавливает требования к проектированию зданий.

1.2. Второй пункт первой страницы уточняет порядок приёмки выполненных работ.

Дата сохранения: 23.07.2026

## Page 2

### BLOCK #2 [TEXT]: {BLOCK_IDS[1]}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop/2)

Модель распознавания рассуждает о таблице вместо того чтобы её переписать.

Это вторая строка того же нечитаемого блока, которую нельзя показывать эксперту.

## Page 3

### BLOCK #3 [TEXT]: {BLOCK_IDS[2]}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop/3)

3.1. Третий пункт третьей страницы описывает испытания при приёмке.

3.2. Четвёртый пункт третьей страницы завершает раздел о контроле качества.
"""


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    document = root / SLUG
    document.mkdir(parents=True)
    (document / "results.md").write_text(MARKDOWN, encoding="utf-8")
    (document / "blocks.json").write_text(
        json.dumps({"document_id": "doc_source_0001"}), encoding="utf-8"
    )
    (root / "MANIFEST.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "slug": SLUG,
                        "document_id": "doc_source_0001",
                        "document_name": f"{SLUG}.pdf",
                        "doc_type": "СП",
                        "pdf_pages": 3,
                        "blocks_count": 3,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return root


def _repair(index: int, outcome: RepairOutcome, replacement: str | None = None) -> PageRepair:
    block = blocks(MARKDOWN)[index]
    return PageRepair(
        document_slug=SLUG,
        block_id=block.block_id,
        page_label=block.page_label,
        original_sha256=hashlib.sha256(block.text.encode("utf-8")).hexdigest(),
        original_characters=len(block.text),
        crop_sha256="1" * 64,
        outcome=outcome,
        replacement=replacement,
        attempts=(),
    )


def _unreliable_ledger(corpus: Path):
    return ledger_of(
        snapshot_of(corpus).snapshot_id, NOW, [_repair(1, RepairOutcome.STILL_DEGENERATE)]
    )


def _paragraphs(projection):
    documents = list(projection.iter_documents())
    assert len(documents) == 1
    return documents[0]


# --- F-4: the marks ------------------------------------------------------------------------


def test_the_paragraphs_of_an_unreliable_block_are_marked_and_nothing_else_moves(
    corpus: Path,
) -> None:
    plain = _paragraphs(open_corpus_projection(corpus))
    ledger = _unreliable_ledger(corpus)
    projection = open_corpus_projection(corpus, repair_ledger=ledger)
    marked = _paragraphs(projection)

    assert projection.unreliable_count == ledger.unreliable_count == 1
    assert projection.repair_count == 0
    assert [p.text for p in marked.paragraphs] == [p.text for p in plain.paragraphs]
    assert [dataclasses.replace(p, text_reliability=TextReliability.RELIABLE) for p in marked.paragraphs] == list(
        plain.paragraphs
    )
    assert {p.block_id for p in marked.paragraphs if not p.is_reliable} == {BLOCK_IDS[1]}
    assert [p.text_reliability for p in marked.paragraphs] == [
        TextReliability.RELIABLE,
        TextReliability.RELIABLE,
        TextReliability.UNRELIABLE,
        TextReliability.UNRELIABLE,
        TextReliability.RELIABLE,
        TextReliability.RELIABLE,
    ]
    assert marked.report == plain.report


def test_a_repaired_block_is_reliable_and_an_unrepaired_one_beside_it_is_not(
    corpus: Path,
) -> None:
    replacement = "1.1. Исправленный текст первой страницы, прочитанный повторно."
    ledger = ledger_of(
        snapshot_of(corpus).snapshot_id,
        NOW,
        [
            _repair(0, RepairOutcome.REPAIRED, replacement),
            _repair(1, RepairOutcome.CALL_FAILED),
        ],
    )
    projection = open_corpus_projection(corpus, repair_ledger=ledger)
    document = _paragraphs(projection)

    assert (projection.repair_count, projection.unreliable_count) == (1, 1)
    assert document.paragraphs[0].text == replacement
    assert document.paragraphs[0].is_reliable
    assert {p.block_id for p in document.paragraphs if not p.is_reliable} == {BLOCK_IDS[1]}


def test_segment_refuses_an_unreliable_mark_on_an_absent_or_replaced_block() -> None:
    with pytest.raises(ValueError, match="absent from the document"):
        segment(SLUG, MARKDOWN, unreliable_blocks={"blk_absent"})
    with pytest.raises(ValueError, match="both replaced and unreliable"):
        segment(
            SLUG,
            MARKDOWN,
            replacements={BLOCK_IDS[1]: "Текст."},
            unreliable_blocks={BLOCK_IDS[1]},
        )


def test_the_diagnostic_segment_corpus_marks_paragraphs_too(corpus: Path) -> None:
    ledger = _unreliable_ledger(corpus)
    effective = repaired_snapshot(snapshot_of(corpus), ledger)
    ((_report, paragraphs, _chunks),) = list(
        segment_corpus(corpus, effective.snapshot_id, repair_ledger=ledger)
    )
    assert {p.block_id for p in paragraphs if not p.is_reliable} == {BLOCK_IDS[1]}


# --- F-4: the reliability-aware profile and its invariant ------------------------------------


def test_characters_v2_skips_exactly_the_unreliable_set_and_breaks_at_it(corpus: Path) -> None:
    projection = open_corpus_projection(
        corpus, target_characters=100_000, repair_ledger=_unreliable_ledger(corpus)
    )
    assert projection.chunking_version == RELIABLE_CHUNKING_PROFILE_VERSION
    document = _paragraphs(projection)

    # A target large enough to hold the whole document still yields two chunks: the
    # unreliable paragraphs end the first, and the text either side is never stitched.
    spans = [(c.paragraph_ordinal_first, c.paragraph_ordinal_last) for c in document.chunks]
    assert spans == [(0, 1), (4, 5)]
    covered = {o for first, last in spans for o in range(first, last + 1)}
    reliable = {p.ordinal for p in document.paragraphs if p.is_reliable}
    assert covered == reliable
    assert not any("нечитаемого" in chunk.text for chunk in document.chunks)
    assert [chunk.ordinal for chunk in document.chunks] == [0, 1]
    assert [chunk.paragraph_count for chunk in document.chunks] == [2, 2]


def test_characters_v2_equals_characters_v1_when_nothing_is_unreliable(
    consultant_plus_markdown: str, unattributed_markdown: str, gapped_pages_markdown: str
) -> None:
    for markdown in (consultant_plus_markdown, unattributed_markdown, gapped_pages_markdown, MARKDOWN):
        paragraphs, _report = segment("example", markdown)
        for target in (40, 1200):
            v1 = chunk_paragraphs(paragraphs, "k", target, version=CHUNKING_PROFILE_VERSION)
            v2 = chunk_paragraphs(paragraphs, "k", target, version=RELIABLE_CHUNKING_PROFILE_VERSION)
            assert v1 == v2 == join_into_chunks(paragraphs, "k", target)


def test_the_coverage_invariant_refuses_every_way_a_chunk_set_can_be_wrong() -> None:
    paragraphs, _report = segment(
        SLUG, MARKDOWN, unreliable_blocks={BLOCK_IDS[1]}
    )
    good = chunk_paragraphs(paragraphs, "k", 100_000, version=RELIABLE_CHUNKING_PROFILE_VERSION)
    verify_coverage(paragraphs, good, version=RELIABLE_CHUNKING_PROFILE_VERSION)

    stitched = join_into_chunks(paragraphs, "k", 100_000)  # v1's join: one chunk over all six
    with pytest.raises(ChunkingRefused, match="unreliable paragraph 2"):
        verify_coverage(paragraphs, stitched, version=RELIABLE_CHUNKING_PROFILE_VERSION)
    with pytest.raises(ChunkingRefused, match="expected 4"):
        verify_coverage(paragraphs, good[:1], version=RELIABLE_CHUNKING_PROFILE_VERSION)
    with pytest.raises(ChunkingRefused, match="ordinal 0 is not 1"):
        verify_coverage(paragraphs, (good[0], good[0]), version=RELIABLE_CHUNKING_PROFILE_VERSION)
    overlapping = dataclasses.replace(good[0], ordinal=1)
    with pytest.raises(ChunkingRefused, match="overlaps"):
        verify_coverage(paragraphs, (good[0], overlapping), version=RELIABLE_CHUNKING_PROFILE_VERSION)
    miscounted = dataclasses.replace(good[1], paragraph_count=3)
    with pytest.raises(ChunkingRefused, match="counts 3"):
        verify_coverage(paragraphs, (good[0], miscounted), version=RELIABLE_CHUNKING_PROFILE_VERSION)
    with pytest.raises(ChunkingRefused, match="expected 6"):
        verify_coverage(paragraphs, good, version=CHUNKING_PROFILE_VERSION)


# --- F-4: the characters-v1 refusal ---------------------------------------------------------


def test_characters_v1_is_refused_over_a_snapshot_with_an_unreliable_block(corpus: Path) -> None:
    with pytest.raises(ChunkingRefused, match="1 unreliable block"):
        open_corpus_projection(
            corpus,
            repair_ledger=_unreliable_ledger(corpus),
            chunking_version=CHUNKING_PROFILE_VERSION,
        )


def test_characters_v1_is_refused_even_when_the_unreliable_block_yields_no_paragraph(
    corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal is on the snapshot's count, not on the paragraphs a projection happens to see."""
    from auditmanager.norms import corpus_source

    ledger = _unreliable_ledger(corpus)
    monkeypatch.setattr(
        corpus_source, "_validated_ledger", lambda _root, _ledger: ({}, {})
    )
    with pytest.raises(ChunkingRefused, match="1 unreliable block"):
        open_corpus_projection(
            corpus, repair_ledger=ledger, chunking_version=CHUNKING_PROFILE_VERSION
        )


def test_characters_v1_chunking_refuses_an_unreliable_paragraph() -> None:
    paragraphs, _report = segment(SLUG, MARKDOWN, unreliable_blocks={BLOCK_IDS[1]})
    with pytest.raises(ChunkingRefused, match="2 unreliable"):
        chunk_paragraphs(paragraphs, "k", version=CHUNKING_PROFILE_VERSION)


def test_characters_v1_is_still_built_over_a_fully_reliable_snapshot(corpus: Path) -> None:
    replacement = "Таблица переписана целиком и читается."
    ledger = ledger_of(
        snapshot_of(corpus).snapshot_id, NOW, [_repair(1, RepairOutcome.REPAIRED, replacement)]
    )
    projection = open_corpus_projection(
        corpus, repair_ledger=ledger, chunking_version=CHUNKING_PROFILE_VERSION
    )
    assert projection.chunking_profile == "characters-v1:1200"
    assert all(p.is_reliable for p in _paragraphs(projection).paragraphs)


def test_the_loader_default_is_the_reliability_aware_profile() -> None:
    assert DEFAULT_CHUNKING_VERSION == RELIABLE_CHUNKING_PROFILE_VERSION == "characters-v2"
    assert chunking_profile(1200) == "characters-v1:1200"
    assert parse_chunking_profile("characters-v2:1200") == ("characters-v2", 1200)
    for malformed in ("characters-v2", "characters-v2:", "characters-v2:01", "characters-v3:1200", "x:1"):
        with pytest.raises(ValueError):
            parse_chunking_profile(malformed)


# --- D-126: the segmentation profile in the key --------------------------------------------


def test_markdown_v1_keeps_every_key_byte_identical(corpus: Path) -> None:
    base = snapshot_of(corpus)
    projection = open_corpus_projection(corpus)
    assert segmentation.SEGMENTATION_PROFILE_VERSION == "markdown-v1"
    assert projection.snapshot == base
    assert projection.base_content_key == base.content_key
    assert "+seg-" not in projection.snapshot.content_key
    assert with_segmentation_profile(base, "markdown-v1") is base

    ledger = _unreliable_ledger(corpus)
    repaired = open_corpus_projection(corpus, repair_ledger=ledger)
    assert repaired.snapshot == repaired_snapshot(base, ledger)
    assert repaired.base_content_key == base.content_key


def test_raising_the_segmentation_profile_yields_a_new_key_for_both_stored_keys(
    corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = snapshot_of(corpus)
    ledger = _unreliable_ledger(corpus)
    monkeypatch.setattr(segmentation, "SEGMENTATION_PROFILE_VERSION", "markdown-v2")

    plain = open_corpus_projection(corpus)
    assert plain.segmentation_profile == "markdown-v2"
    assert plain.snapshot.content_key == f"{base.content_key}+seg-markdown-v2"
    assert plain.base_content_key == plain.snapshot.content_key
    assert plain.snapshot.content_digest == base.content_digest

    repaired = open_corpus_projection(corpus, repair_ledger=ledger)
    assert repaired.base_content_key == f"{base.content_key}+seg-markdown-v2"
    assert repaired.snapshot.content_key == (
        f"{repaired_snapshot(base, ledger).content_key}+seg-markdown-v2"
    )
    # The chunks carry the qualified key too, so nothing downstream names the old text.
    assert {c.snapshot_id for c in _paragraphs(repaired).chunks} == {repaired.snapshot.content_key}
    # The diagnostic projection agrees on which key names the effective text.
    rows = list(segment_corpus(corpus, repaired.snapshot.content_key, repair_ledger=ledger))
    assert len(rows) == 1


def test_a_segmentation_profile_outside_the_transport_grammar_is_refused(corpus: Path) -> None:
    base = snapshot_of(corpus)
    for profile in ("Markdown-v2", "markdown_v2", "markdown--v2", "-v2", "", "a" * 101):
        with pytest.raises(ValueError, match="segmentation profile"):
            with_segmentation_profile(base, profile)
    qualified = with_segmentation_profile(base, "markdown-v2")
    with pytest.raises(ValueError, match="already names"):
        with_segmentation_profile(qualified, "markdown-v3")


def _transport_content_key_grammar() -> re.Pattern[str]:
    script = Path(__file__).resolve().parents[3] / "infra/deploy/lib/forced-command.sh"
    values: dict[str, str] = {}
    for line in script.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(FC_BUNDLE_WINDOW_ERE|FC_BUNDLE_REPAIRS_ERE|FC_CONTENT_KEY_ERE)=(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
    content = (
        values["FC_CONTENT_KEY_ERE"].strip('"')
        .replace("${FC_BUNDLE_WINDOW_ERE}", values["FC_BUNDLE_WINDOW_ERE"].strip("'"))
        .replace("${FC_BUNDLE_REPAIRS_ERE}", values["FC_BUNDLE_REPAIRS_ERE"].strip("'"))
        .replace("\\\\", "\\")
    )
    return re.compile(f"^{content}$")


def test_every_qualified_key_matches_the_transport_grammar(
    corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grammar = _transport_content_key_grammar()
    ledger = _unreliable_ledger(corpus)
    for profile in ("markdown-v1", "markdown-v2", "markdown-v10-tables"):
        monkeypatch.setattr(segmentation, "SEGMENTATION_PROFILE_VERSION", profile)
        for repair_ledger in (None, ledger):
            key = open_corpus_projection(corpus, repair_ledger=repair_ledger).snapshot.content_key
            assert grammar.match(key), key
