"""W56b TEXT windows retain the saved page and document-global coordinates."""

from __future__ import annotations

import pytest

from auditmanager.analysis.text.chunk_preflight import (
    ChunkPreflightError,
    partition_text_layer,
)
from auditmanager.analysis.text.textlayer import Page, TextLayer


def _layer(*texts: str) -> TextLayer:
    pages: list[Page] = []
    position = 0
    for number, body in enumerate(texts, start=1):
        pages.append(Page(number, position, position + len(body), body))
        position += len(body)
    return TextLayer("ver_01", "NFC", tuple(pages), "".join(texts))


def test_complete_windows_preserve_unicode_global_spans_and_blank_pages() -> None:
    layer = _layer("А😀", "", "БВ", "цитата", "")

    windows = partition_text_layer(layer, max_chunk_characters=6)

    assert [(w.index, w.first_page, w.last_page, w.char_start, w.char_end)
            for w in windows] == [(0, 1, 3, 0, 4), (1, 4, 5, 4, 10)]
    assert tuple(w.text for w in windows) == ("А😀БВ", "цитата")
    assert {(w.version_uid, w.normalization_id) for w in windows} == {("ver_01", "NFC")}
    assert "".join(w.text for w in windows) == layer.document_text
    # A quote's local start maps back to the original evidence coordinate.
    quote = "тата"
    local = windows[1].text.index(quote)
    assert layer.slice(windows[1].char_start + local,
                       windows[1].char_start + local + len(quote)) == quote
    assert windows == partition_text_layer(layer, max_chunk_characters=6)


def test_exact_ceiling_stays_one_window_and_next_character_makes_two() -> None:
    layer = _layer("аб", "вг", "д")
    assert len(partition_text_layer(layer, max_chunk_characters=5)) == 1
    windows = partition_text_layer(layer, max_chunk_characters=4)
    assert [(w.first_page, w.last_page, w.text) for w in windows] == [
        (1, 2, "абвг"), (3, 3, "д")
    ]


def test_oversized_later_page_refuses_whole_plan_with_page_number() -> None:
    with pytest.raises(ChunkPreflightError) as caught:
        partition_text_layer(_layer("ok", "длинная"), max_chunk_characters=4)
    assert caught.value.reason == "page_exceeds_limit"
    assert caught.value.page_number == 2


@pytest.mark.parametrize("ceiling", [0, -1, True, 1.5, "5"])
def test_ceiling_must_be_a_positive_integer(ceiling: object) -> None:
    with pytest.raises(ChunkPreflightError, match="invalid_max_chunk_characters"):
        partition_text_layer(_layer("text"), max_chunk_characters=ceiling)  # type: ignore[arg-type]


def test_blank_document_and_forged_text_layer_refuse() -> None:
    with pytest.raises(ChunkPreflightError, match="empty_text_layer"):
        partition_text_layer(_layer("", ""), max_chunk_characters=2)
    good = _layer("ёж", "😀")
    invalid = (
        TextLayer(good.version_uid, good.normalization_id, good.pages, "еж😀"),
        TextLayer(good.version_uid, good.normalization_id,
                  (good.pages[0], Page(3, 2, 3, "😀")), good.document_text),
        TextLayer(good.version_uid, good.normalization_id,
                  (good.pages[0], Page(2, 2, 4, "😀")), good.document_text),
    )
    for layer in invalid:
        with pytest.raises(ChunkPreflightError, match="invalid_text_layer"):
            partition_text_layer(layer, max_chunk_characters=2)


@pytest.mark.parametrize("texts", [(" ", "\n\t"), ("\u00a0", "\u2003")])
def test_whitespace_only_pages_refuse_even_with_nonzero_character_count(
    texts: tuple[str, str],
) -> None:
    layer = _layer(*texts)
    assert layer.total_char_count > 0
    with pytest.raises(ChunkPreflightError, match="empty_text_layer"):
        partition_text_layer(layer, max_chunk_characters=4)
