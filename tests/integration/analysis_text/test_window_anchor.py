"""A windowed TEXT reply cannot cite a page from another request."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.chunk_preflight import partition_text_layer
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.analysis.text.window_anchor import WindowAnchorError, resolve_window_anchor


def _source() -> tuple[TextLayer, tuple]:
    bodies = ("А😀 дом", "", "БВ фасад", "крыша")
    pages = []
    position = 0
    for number, body in enumerate(bodies, start=1):
        pages.append(Page(number, position, position + len(body), body))
        position += len(body)
    layer = TextLayer("ver_01", "NFC", tuple(pages), "".join(bodies))
    return layer, partition_text_layer(layer, max_chunk_characters=9)


def test_quote_resolves_to_saved_document_global_unicode_offset() -> None:
    layer, windows = _source()
    assert [(w.first_page, w.last_page) for w in windows] == [(1, 2), (3, 3), (4, 4)]

    answer = resolve_window_anchor(
        layer, windows, window_index=1, page_number=3, quote="фасад"
    )

    assert isinstance(answer, ResolvedAnchor)
    assert (answer.char_start, answer.char_end) == (9, 14)
    assert layer.slice(answer.char_start, answer.char_end) == answer.quote


def test_quote_on_another_window_is_refused_even_if_it_exists_in_source() -> None:
    layer, windows = _source()
    with pytest.raises(WindowAnchorError, match="page_outside_window"):
        resolve_window_anchor(layer, windows, window_index=0, page_number=3, quote="фасад")


def test_missing_quote_remains_unresolved_with_existing_reason() -> None:
    layer, windows = _source()
    answer = resolve_window_anchor(
        layer, windows, window_index=1, page_number=3, quote="нет такой строки"
    )
    assert isinstance(answer, UnresolvedAnchor)
    assert answer.reason == "quotation_absent"


@pytest.mark.parametrize("mutation", ["omit", "duplicate", "text", "identity", "ordinal", "span"])
def test_incomplete_or_forged_window_plan_is_refused(mutation: str) -> None:
    layer, windows = _source()
    if mutation == "omit":
        forged = windows[:-1]
    elif mutation == "duplicate":
        forged = (windows[0], windows[0], windows[2])
    elif mutation == "text":
        forged = (replace(windows[0], text="другая строка"), *windows[1:])
    elif mutation == "identity":
        forged = (replace(windows[0], version_uid="ver_foreign"), *windows[1:])
    elif mutation == "ordinal":
        forged = (replace(windows[0], index=1), *windows[1:])
    else:
        forged = (replace(windows[0], char_end=windows[0].char_end + 1), *windows[1:])
    with pytest.raises(WindowAnchorError, match="invalid_window_plan"):
        resolve_window_anchor(layer, forged, window_index=0, page_number=1, quote="А😀")


@pytest.mark.parametrize("index", [-1, 3, True, 0.5])
def test_invalid_window_index_is_refused(index: object) -> None:
    layer, windows = _source()
    with pytest.raises(WindowAnchorError, match="invalid_window_index"):
        resolve_window_anchor(layer, windows, window_index=index, page_number=1, quote="А😀")  # type: ignore[arg-type]
