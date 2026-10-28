"""What the matrix reads of a page: kind, service zones, scan, tokens, the bounded mask cache (`CMP-MATRIX-01`)."""

from __future__ import annotations

import numpy as np

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.features import MM, MaskCache, PageFeatures, detect_frame, norm
from auditmanager.comparison.profile.models import VectorLine

from .pages import WIDTH, features, page, tokens, words


def test_a_word_is_its_lower_case_text_without_edge_punctuation() -> None:
    assert norm("  «Щит-3», ") == "щит-3" and norm("...") == "" and norm(None) == ""  # type: ignore[arg-type]


def test_the_kind_follows_the_stamp_the_designation_and_the_words_of_the_top_of_the_page() -> None:
    plain = features([page("v", 1, tokens("о", 12))])[0]
    assert plain.kind == "unknown" and plain.stamp_source == ""
    cover = features([page("v", 1, ["Рабочая", "документация", "том", "1"] + tokens("о", 12))])[0]
    assert cover.kind == "title" and cover.token_total >= 10
    stamped = features([page("v", 1, tokens("о", 12), designation="Д-1", sheet_number="1", title="Общие данные")])[0]
    assert stamped.kind == "drawing" and stamped.stamp_source == "text" and stamped.title == "общие данные"
    spec_by_designation = features([page("v", 1, tokens("о", 12), designation="Д-1.СО")])[0]
    assert spec_by_designation.kind == "spec"
    header = words(["Поз.", "Наименование", "Кол."], y0=40)
    assert features([page("v", 1, tokens("о", 12), extra_words=header, y0=300)])[0].kind == "spec"
    assert features([page("v", 1, tokens("о", 12), extra_words=words(["Разрешение"], y0=20), y0=300)])[0].kind == "permit"


def test_the_stamp_block_is_a_service_zone_and_its_words_are_not_the_pages_text() -> None:
    inside = words(["штамп1", "штамп2"], x0=300, y0=800)  # lower right: the 190 x 60 mm block
    body = tokens("о", 12)
    f = features([page("v", 1, body, designation="Д-1", extra_words=inside)])[0]
    assert "штамп1" not in f.tokens and f.token_total == 12 and len(f.zones) == 1
    unstamped = features([page("v", 1, body, extra_words=inside)])[0]
    assert "штамп1" in unstamped.tokens and unstamped.zones == [], "no stamp, no frame: no zone"


def test_the_frame_is_found_from_long_lines_near_the_edges() -> None:
    height = 842.0
    lines = [(20 * MM, 0, 20 * MM, height), (WIDTH - 5 * MM, 0, WIDTH - 5 * MM, height),
             (0, 5 * MM, WIDTH, 5 * MM), (0, height - 5 * MM, WIDTH, height - 5 * MM)]
    frame = detect_frame(WIDTH, height, lines)
    assert frame is not None and abs(frame[0] - 20 * MM) < 1e-9 and abs(frame[3] - (height - 5 * MM)) < 1e-9
    assert detect_frame(WIDTH, height, lines[:2]) is None, "fewer than three sides is no frame"
    page_with_frame = page("v", 1, tokens("о", 12))
    from dataclasses import replace

    framed = replace(page_with_frame, lines=tuple(VectorLine(x0, y0, x1, y1, 1.0, None) for x0, y0, x1, y1 in lines))
    f = PageFeatures(framed, rules=settings.RULES, cache=MaskCache())
    assert f.frame is not None and len(f.zones) == 5, "the stamp block and the four margins outside the frame"


def test_a_page_without_text_has_no_tokens_and_a_scan_keeps_its_flag() -> None:
    scan = features([page("v", 1, scan=True, mask=True)])[0]
    assert scan.scan is True and scan.token_total == 0 and scan.has_text is False and scan.has_mask is True
    assert features([page("v", 1, tokens("о", 12))])[0].has_mask is False


def test_the_mask_cache_stays_inside_its_budget_and_the_value_is_the_same_either_way() -> None:
    cache = MaskCache(budget_bytes=2_000)
    made = []

    def make(i: int):
        def build() -> np.ndarray:
            made.append(i)
            return np.full((30, 30), i, dtype=np.uint8)  # 900 bytes
        return build

    for i in range(10):
        assert int(cache.get(("p", str(i)), make(i))[0, 0]) == i
        assert cache.used_bytes <= 2_000, "least recently used pages are dropped"
    assert int(cache.get(("p", "9"), make(99))[0, 0]) == 9 and made.count(99) == 0, "a recent one is still there"
    assert int(cache.get(("p", "0"), make(0))[0, 0]) == 0 and made.count(0) == 2, "an old one is made again, not lost"


def test_a_mask_is_kept_compressed_and_comes_back_equal() -> None:
    p = page("v", 1, tokens("о", 12), mask=True)
    f = features([p])[0]
    assert f.full_mask() is not None and f.full_mask().shape == (f.full_shape()[0], f.full_shape()[1])
    assert f.mask is not None and f.mask.dtype == np.uint8 and int(f.mask.sum()) == f.half_ink == 0
