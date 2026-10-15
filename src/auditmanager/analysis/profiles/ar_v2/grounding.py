"""Resolve AR v2 quotations against PDF text, marking OCR-only claims.

The PDF text layer remains the sole source of offsets and publishable evidence.
Recognised context may explain a refusal, but never supplies an anchor.
"""

from __future__ import annotations

from typing import Final

from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.text.anchors import (
    BlockIndex,
    REASON_ABSENT,
    ResolvedAnchor,
    UnresolvedAnchor,
    resolve_anchor,
)
from auditmanager.analysis.text.textlayer import TextLayer


REASON_RECOGNISED_ONLY: Final[str] = "quote_in_recognised_text"


def resolve_v2_anchor(
    text_layer: TextLayer,
    *,
    page_number: int,
    quote: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
    block_index: BlockIndex | None = None,
) -> ResolvedAnchor | UnresolvedAnchor:
    """Use v1's exact PDF resolver; refine only an otherwise absent quote.

    OCR matching is exact apart from the same outer whitespace candidate the
    PDF resolver accepts. It is confined to the claimed page. A quote on a
    different PDF page keeps ``quotation_on_different_page`` precedence.
    """
    page_numbers = set(text_layer.page_numbers)
    if any(item.page_number not in page_numbers for item in recognised_context):
        raise ValueError("recognised_page_absent_from_text_layer")
    outcome = resolve_anchor(
        text_layer, page_number=page_number, quote=quote, block_index=block_index
    )
    if isinstance(outcome, ResolvedAnchor) or outcome.reason != REASON_ABSENT:
        return outcome
    candidates = (quote, quote.strip()) if quote.strip() != quote else (quote,)
    if any(
        item.page_number == page_number
        and any(candidate and candidate in item.text for candidate in candidates)
        for item in recognised_context
    ):
        return UnresolvedAnchor(
            page_number=page_number, quote=quote, reason=REASON_RECOGNISED_ONLY
        )
    return outcome
