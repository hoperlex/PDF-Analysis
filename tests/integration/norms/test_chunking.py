"""Joining paragraphs into retrieval chunks, and what a chunk carries.

`W33-CORPUS` requires a chunk to carry at minimum the document slug, the page, the offset in
the recognised text, whether the paragraph is a numbered clause, and the corpus-snapshot
identifier. The tests below are about the two rules that are decisions rather than mechanics
— a paragraph is never split, and a chunk may cross a page boundary — and about the fields
that make a chunk resolvable back to the page an expert is shown.
"""

from __future__ import annotations

import pytest

from auditmanager.norms import (
    DEFAULT_TARGET_CHARACTERS,
    Paragraph,
    ParagraphKind,
    join_into_chunks,
    segment,
)


def _paragraph(ordinal: int, page: int, text: str, clause: str | None = None) -> Paragraph:
    return Paragraph(
        document_slug="example",
        page_label=page,
        block_id=f"blk_{page:04d}",
        ordinal=ordinal,
        char_offset=ordinal * 1000,
        char_length=len(text),
        kind=ParagraphKind.BODY,
        clause_number=clause,
        text=text,
    )


def test_a_chunk_stops_before_the_target_and_the_next_one_starts() -> None:
    paragraphs = [_paragraph(index, 1, "я" * 500) for index in range(5)]
    chunks = join_into_chunks(paragraphs, "snap")
    assert [chunk.paragraph_count for chunk in chunks] == [2, 2, 1]
    assert all(len(chunk.text) <= DEFAULT_TARGET_CHARACTERS for chunk in chunks)
    assert [chunk.ordinal for chunk in chunks] == [0, 1, 2]


def test_a_paragraph_longer_than_the_target_becomes_its_own_chunk_and_is_not_split() -> None:
    """Splitting mid-sentence would hand an expert a quotation that does not end.

    It is not a theoretical case. The corpus's longest substantive paragraph is 62 359
    characters — a table transcribed with no blank line inside it — and 3 666 of 55 702
    chunks exceed the 1200-character target for this reason. The cost is real and belongs to
    the embedding stream as a decision, not to this one as a silent truncation.
    """
    long = "я" * 5000
    chunks = join_into_chunks([_paragraph(0, 1, long)], "snap")
    assert len(chunks) == 1
    assert chunks[0].text == long
    assert chunks[0].paragraph_count == 1


def test_a_chunk_records_the_pages_it_spans() -> None:
    """A clause routinely continues across a page break; the expert sees both crops."""
    paragraphs = [_paragraph(0, 5, "а" * 400), _paragraph(1, 6, "б" * 400)]
    chunk = join_into_chunks(paragraphs, "snap")[0]
    assert (chunk.page_first, chunk.page_last) == (5, 6)


def test_a_chunk_carries_the_snapshot_and_its_clause_numbers() -> None:
    paragraphs = [_paragraph(0, 1, "а" * 100, clause="4.2"), _paragraph(1, 1, "б" * 100)]
    chunk = join_into_chunks(paragraphs, "2026-07-23..2026-08-20+17d.4b74348debf7")[0]
    assert chunk.snapshot_id == "2026-07-23..2026-08-20+17d.4b74348debf7"
    assert chunk.clause_numbers == ("4.2",)
    assert chunk.contains_clause
    assert chunk.document_slug == "example"
    assert chunk.char_offset == 0


def test_a_chunk_with_no_numbered_clause_says_so() -> None:
    chunk = join_into_chunks([_paragraph(0, 1, "а" * 100)], "snap")[0]
    assert chunk.clause_numbers == ()
    assert not chunk.contains_clause


def test_every_paragraph_reaches_exactly_one_chunk(consultant_plus_markdown: str) -> None:
    """A join that loses a paragraph loses a clause, and a count would not show which."""
    paragraphs, _report = segment("example", consultant_plus_markdown)
    chunks = join_into_chunks(paragraphs, "snap")
    assert sum(chunk.paragraph_count for chunk in chunks) == len(paragraphs)
    rejoined = "\n\n".join(chunk.text for chunk in chunks)
    assert rejoined == "\n\n".join(paragraph.text for paragraph in paragraphs)


def test_a_nonpositive_target_is_refused_rather_than_looping() -> None:
    with pytest.raises(ValueError):
        join_into_chunks([_paragraph(0, 1, "а")], "snap", target_characters=0)
