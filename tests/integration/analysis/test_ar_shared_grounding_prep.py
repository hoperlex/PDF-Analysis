"""OCR can explain missing AR v2 citations but cannot ground them."""

from __future__ import annotations

import pytest

from auditmanager.analysis.profiles.ar_shared.grounding import (
    REASON_RECOGNISED_ONLY,
    resolve_v2_anchor,
)
from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.textlayer import Page, TextLayer


def _layer() -> TextLayer:
    first = "Стена А — 200 мм"
    second = "Стена А — 250 мм"
    return TextLayer(
        version_uid="ver_grounding", normalization_id="NFC",
        pages=(Page(1, 0, len(first), first),
               Page(2, len(first), len(first) + len(second), second)),
        document_text=first + second,
    )


def test_pdf_text_is_the_only_source_of_a_resolved_interval() -> None:
    layer = _layer()
    ocr = (RecognisedContext(1, "Стена А — 200 мм", ()),)
    result = resolve_v2_anchor(
        layer, page_number=1, quote="Стена А — 200 мм", recognised_context=ocr
    )
    assert isinstance(result, ResolvedAnchor)
    assert layer.slice(result.char_start, result.char_end) == result.quote


def test_same_page_ocr_only_quote_has_diagnostic_and_no_anchor() -> None:
    result = resolve_v2_anchor(
        _layer(), page_number=1, quote=" Кровля плоская ",
        recognised_context=(RecognisedContext(1, "Кровля плоская", ("mixed_script",)),),
    )
    assert isinstance(result, UnresolvedAnchor)
    assert result.reason == REASON_RECOGNISED_ONLY
    assert not hasattr(result, "char_start")


def test_other_pdf_page_keeps_wrong_page_diagnostic_even_if_ocr_matches() -> None:
    result = resolve_v2_anchor(
        _layer(), page_number=1, quote="Стена А — 250 мм",
        recognised_context=(RecognisedContext(1, "Стена А — 250 мм", ()),),
    )
    assert isinstance(result, UnresolvedAnchor)
    assert result.reason == "quotation_on_different_page"


def test_ocr_on_another_page_and_near_match_do_not_repair_citation() -> None:
    layer = _layer()
    for context in (
        (RecognisedContext(2, "Кровля плоская", ()),),
        (RecognisedContext(1, "кровля плоская", ()),),
        (),
    ):
        result = resolve_v2_anchor(
            layer, page_number=1, quote="Кровля плоская", recognised_context=context
        )
        assert isinstance(result, UnresolvedAnchor)
        assert result.reason == "quotation_absent"


def test_unbound_ocr_page_is_refused_before_grounding() -> None:
    with pytest.raises(ValueError, match="recognised_page_absent_from_text_layer"):
        resolve_v2_anchor(
            _layer(), page_number=1, quote="Стена А — 200 мм",
            recognised_context=(RecognisedContext(3, "Стена А — 200 мм", ()),),
        )
