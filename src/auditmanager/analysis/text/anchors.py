"""Resolving a model-proposed quotation to document-global offsets.

**The model does not compute reliable offsets, and it is never asked to.** It proposes
a page number and a verbatim quotation; this module finds that quotation in the text
layer and produces the anchor. An evidence item is emitted only when the quotation is
actually found, because ``char_end - char_start`` must equal the code-point length of
``quote`` and there is no honest way to satisfy that for a string that is not there.
Fabricating an interval would produce an item that ``B4``'s grounding gate rejects as
a diagnostic, which is worse than not emitting it: it reads as a finding until someone
opens it.

Two rules that look like details and are not:

* **Nothing here normalizes.** ``P02_SEAMS.md`` section 4.3 says the normalization is
  applied once by ``source_preparation`` and that ``B3`` must not normalize model
  output before writing an anchor, because ``B4`` compares after that one declared
  normalization and nothing else. A quotation in a different normal form therefore
  fails to resolve and is dropped, which is the correct fail-closed outcome.
* **Everything is code points.** ``str.find``, ``len`` and slicing all count code
  points in Python. No byte encoding appears in this module.

Whitespace is the one liberty taken. A model quoting a line often carries a leading or
trailing space that is not in the extracted text. The stripped quotation is retried,
and when it resolves it is the *stripped* literal that is emitted, so the emitted
``quote`` is still exactly what lies at the emitted interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Iterable, Mapping

from auditmanager.analysis.text.textlayer import TextLayer

#: Why a proposed quotation produced no evidence item. The values are the
#: ``ungrounded_reason`` vocabulary of ``P02_SEAMS.md`` section 5.1, reused so a
#: diagnostic written here reads the same as one written by the grounding gate.
REASON_ABSENT: Final[str] = "quotation_absent"
REASON_DIFFERENT_PAGE: Final[str] = "quotation_on_different_page"
REASON_SPAN_OUTSIDE_PAGE: Final[str] = "span_outside_page"
REASON_LENGTH_MISMATCH: Final[str] = "span_length_mismatch"


@dataclass(frozen=True, slots=True)
class ResolvedAnchor:
    """A quotation located in the document-global sequence."""

    page_number: int
    quote: str
    char_start: int
    char_end: int
    block_id: str | None = None


@dataclass(frozen=True, slots=True)
class UnresolvedAnchor:
    """A quotation that did not resolve, and why. Never emitted as evidence."""

    page_number: int
    quote: str
    reason: str


@dataclass(frozen=True, slots=True)
class BlockIndex:
    """The optional ``geometry.block_index`` binding, read only for ``block_id``.

    ``block_id`` is a nullable secondary anchor. When no block index is supplied the
    field is simply absent from the evidence item, which section 4.7 allows and
    section 5.1 rule 3 then does not apply to.
    """

    spans: tuple[tuple[str, int, int, int], ...]  # (block_id, page_number, start, end)

    @classmethod
    def from_document(cls, document: Mapping[str, Any] | None) -> "BlockIndex | None":
        if not document:
            return None
        blocks = document.get("blocks") or ()
        return cls(
            spans=tuple(
                (
                    str(block["block_id"]),
                    int(block["page_number"]),
                    int(block["char_start"]),
                    int(block["char_end"]),
                )
                for block in blocks
            )
        )

    def containing(self, page_number: int, char_start: int, char_end: int) -> str | None:
        """The block whose own span wholly contains this interval, if exactly one does."""
        found: str | None = None
        for block_id, block_page, start, end in self.spans:
            if block_page == page_number and start <= char_start and char_end <= end:
                if found is not None:
                    return None  # ambiguous; a secondary anchor is not worth guessing
                found = block_id
        return found


def _candidate_quotes(quote: str) -> Iterable[str]:
    """The literals to try, in order. Never a normalized or case-folded variant."""
    yield quote
    stripped = quote.strip()
    if stripped and stripped != quote:
        yield stripped


def resolve_anchor(
    text_layer: TextLayer,
    *,
    page_number: int,
    quote: str,
    block_index: BlockIndex | None = None,
) -> ResolvedAnchor | UnresolvedAnchor:
    """Locate ``quote`` on ``page_number`` and return its document-global interval.

    The declared page is part of the claim, so a quotation that exists elsewhere in
    the document but not on the page the model named does not resolve. Reporting it at
    the page where it happens to occur would silently repair the model's citation and
    hide the fact that it cited the wrong page.
    """
    page = text_layer.page(page_number)
    if page is None:
        return UnresolvedAnchor(page_number=page_number, quote=quote, reason=REASON_ABSENT)

    for candidate in _candidate_quotes(quote):
        offset_in_page = page.text.find(candidate)
        if offset_in_page < 0:
            continue
        char_start = page.char_start + offset_in_page
        char_end = char_start + len(candidate)

        # Belt and braces against an arithmetic slip: re-read the interval out of the
        # document-global sequence and require it to be the emitted literal.
        if text_layer.slice(char_start, char_end) != candidate:
            return UnresolvedAnchor(
                page_number=page_number, quote=quote, reason=REASON_LENGTH_MISMATCH
            )
        if not page.contains(char_start, char_end):
            return UnresolvedAnchor(
                page_number=page_number, quote=quote, reason=REASON_SPAN_OUTSIDE_PAGE
            )

        block_id = (
            block_index.containing(page_number, char_start, char_end) if block_index else None
        )
        return ResolvedAnchor(
            page_number=page_number,
            quote=candidate,
            char_start=char_start,
            char_end=char_end,
            block_id=block_id,
        )

    elsewhere = any(
        other.page_number != page_number and any(c in other.text for c in _candidate_quotes(quote))
        for other in text_layer.pages
    )
    return UnresolvedAnchor(
        page_number=page_number,
        quote=quote,
        reason=REASON_DIFFERENT_PAGE if elsewhere else REASON_ABSENT,
    )
