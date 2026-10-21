"""Pure page-boundary partition of a saved text layer for future W56b calls.

The caller supplies a *document-text* character ceiling after reserving room
for its prompt, response schema, normative context and output. This module
does no pricing, model selection, request rendering or external I/O. Each
window retains the original document-global Unicode offsets; page text is
neither normalized nor decorated with prompt framing here.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.text.textlayer import Page, TextLayer


class ChunkPreflightError(ValueError):
    """A complete text plan cannot be made under the supplied ceiling."""

    def __init__(self, reason: str, *, page_number: int | None = None) -> None:
        self.reason = reason
        self.page_number = page_number
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A contiguous, whole-page slice in the saved document's coordinates."""

    version_uid: str
    normalization_id: str
    index: int
    first_page: int
    last_page: int
    char_start: int
    char_end: int
    text: str


def _checked_pages(layer: TextLayer) -> tuple[Page, ...]:
    # TextLayer is normally loaded by load_text_layer. Recheck here because a
    # caller can also construct that public dataclass directly.
    if (
        not isinstance(layer, TextLayer)
        or not isinstance(layer.version_uid, str)
        or not layer.version_uid
        or not isinstance(layer.normalization_id, str)
        or not layer.normalization_id
        or not isinstance(layer.pages, tuple)
        or not layer.pages
        or not isinstance(layer.document_text, str)
    ):
        raise ChunkPreflightError("invalid_text_layer")
    position = 0
    parts: list[str] = []
    for number, page in enumerate(layer.pages, start=1):
        if (
            not isinstance(page, Page)
            or type(page.page_number) is not int
            or page.page_number != number
            or type(page.char_start) is not int
            or page.char_start != position
            or type(page.char_end) is not int
            or not isinstance(page.text, str)
            or page.char_end - page.char_start != len(page.text)
        ):
            raise ChunkPreflightError("invalid_text_layer")
        parts.append(page.text)
        position = page.char_end
    if position != len(layer.document_text) or "".join(parts) != layer.document_text:
        raise ChunkPreflightError("invalid_text_layer")
    return layer.pages


def partition_text_layer(
    layer: TextLayer, *, max_chunk_characters: int
) -> tuple[TextChunk, ...]:
    """Return a complete, deterministic partition or refuse before any call.

    Greedy windows retain all pages, including empty ones. A nonempty page
    larger than the ceiling is refused; splitting one page and any desired
    overlap require a separately reviewed citation and budget rule.
    """
    if type(max_chunk_characters) is not int or max_chunk_characters < 1:
        raise ChunkPreflightError("invalid_max_chunk_characters")
    pages = _checked_pages(layer)
    if not layer.document_text.strip():
        raise ChunkPreflightError("empty_text_layer")
    # Validate the entire source before returning even the first chunk.
    for page in pages:
        if len(page.text) > max_chunk_characters:
            raise ChunkPreflightError("page_exceeds_limit", page_number=page.page_number)

    result: list[TextChunk] = []
    first = pages[0]
    chunk_start = first.char_start
    first_page = first.page_number
    used = 0
    for page in pages:
        if used and used + len(page.text) > max_chunk_characters:
            result.append(TextChunk(
                version_uid=layer.version_uid,
                normalization_id=layer.normalization_id,
                index=len(result),
                first_page=first_page,
                last_page=page.page_number - 1,
                char_start=chunk_start,
                char_end=page.char_start,
                text=layer.slice(chunk_start, page.char_start),
            ))
            first_page = page.page_number
            chunk_start = page.char_start
            used = 0
        used += len(page.text)
    result.append(TextChunk(
        version_uid=layer.version_uid,
        normalization_id=layer.normalization_id,
        index=len(result),
        first_page=first_page,
        last_page=pages[-1].page_number,
        char_start=chunk_start,
        char_end=pages[-1].char_end,
        text=layer.slice(chunk_start, pages[-1].char_end),
    ))
    return tuple(result)
