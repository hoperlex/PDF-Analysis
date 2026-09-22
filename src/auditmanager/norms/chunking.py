"""Paragraphs joined into retrieval chunks.

`R-16` measured 58 021 chunks at ~1200 characters averaging 1072, over 319 730 substantive
paragraphs. The join is greedy and forward-only: accumulate consecutive paragraphs of one
document until the next would carry the chunk past the target, then emit.

Two rules that are decisions rather than mechanics:

- **A paragraph is never split.** A paragraph longer than the target becomes a chunk on its
  own. Splitting mid-sentence to hit a character count would hand an expert a quotation that
  does not end, and the anchoring `R-16` fixed is by page — there is no sub-paragraph anchor
  to split against.
- **A chunk may cross a page boundary.** Norm clauses run across page breaks constantly and
  the ConsultantPlus export cuts mid-sentence at one. A chunk carries `page_first` and
  `page_last`; the expert is shown one page crop per page in the span.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import Chunk, Paragraph

#: The character target `R-16` measured against.
DEFAULT_TARGET_CHARACTERS = 1200

#: How paragraphs are rejoined inside a chunk. A blank line, because that is what separated
#: them in the source and what makes the chunk readable when an expert is shown it.
JOIN = "\n\n"


def join_into_chunks(
    paragraphs: Sequence[Paragraph],
    snapshot_id: str,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
) -> tuple[Chunk, ...]:
    """Join one document's substantive paragraphs into chunks."""
    if target_characters <= 0:
        raise ValueError("target_characters must be positive")

    chunks: list[Chunk] = []
    batch: list[Paragraph] = []

    def flush() -> None:
        if not batch:
            return
        text = JOIN.join(paragraph.text for paragraph in batch)
        chunks.append(
            Chunk(
                snapshot_id=snapshot_id,
                document_slug=batch[0].document_slug,
                ordinal=len(chunks),
                page_first=min(paragraph.page_label for paragraph in batch),
                page_last=max(paragraph.page_label for paragraph in batch),
                char_offset=batch[0].char_offset,
                char_length=batch[-1].char_offset + batch[-1].char_length - batch[0].char_offset,
                paragraph_count=len(batch),
                clause_numbers=tuple(
                    paragraph.clause_number
                    for paragraph in batch
                    if paragraph.clause_number is not None
                ),
                text=text,
            )
        )
        batch.clear()

    running = 0
    for paragraph in paragraphs:
        addition = len(paragraph.text) + (len(JOIN) if batch else 0)
        if batch and running + addition > target_characters:
            flush()
            running = 0
            addition = len(paragraph.text)
        batch.append(paragraph)
        running += addition
    flush()
    return tuple(chunks)
