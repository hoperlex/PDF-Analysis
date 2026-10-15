from __future__ import annotations

import json
import math
from array import array

import pytest

from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.ranking import (
    MAX_CANDIDATE_WINDOWS,
    RankingRefused,
    RetrievalItem,
    RetrievalParagraph,
    RetrievalWindow,
    TargetSpan,
    exact_inner_product,
    select_prompt_part,
)


def _basis(axis: int = 0) -> array:
    vector = array("f", [0.0]) * DIMENSIONS
    vector[axis] = 1.0
    return vector


def _paragraph(
    ordinal: int, *, text: str | None = None, reliable: bool = True
) -> RetrievalParagraph:
    return RetrievalParagraph(
        document_id="ndoc_1",
        paragraph_id=f"npar_{ordinal}",
        designation="СП 1",
        title="Тестовый документ",
        ordinal=ordinal,
        clause_number=str(ordinal),
        page_label="1",
        text=text if text is not None else f"Абзац {ordinal} с нормативным текстом",
        reliable=reliable,
    )


def _item() -> RetrievalItem:
    return RetrievalItem("item-1", _basis(), (TargetSpan("ndoc_1", 0, 0),))


def _window(ordinal: int, *, axis: int = 1) -> RetrievalWindow:
    return RetrievalWindow("ndoc_1", ordinal, 0, ordinal, ordinal, _basis(axis))


def test_float32_inner_product_and_stable_tie_break_independent_of_input_order() -> None:
    query = _basis()
    assert exact_inner_product(query, query) == math.fsum(a * b for a, b in zip(query, query))
    paragraphs = tuple(_paragraph(n) for n in range(5))
    windows = (_window(4), _window(2), _window(3), _window(1, axis=0))
    first = select_prompt_part((_item(),), paragraphs, windows)
    replay = select_prompt_part((_item(),), tuple(reversed(paragraphs)), tuple(reversed(windows)))
    assert first == replay
    assert [row.paragraph_id for row in first.rows] == ["npar_0", "npar_1", "npar_2", "npar_3"]
    assert [row.label for row in first.rows] == ["N1", "N2", "N3", "N4"]
    assert len(first.prompt_part) <= 22_000
    assert (
        json.loads(first.prompt_part)["paragraphs"][1]["text_sha256"]
        == first.rows[1].text_sha256
    )


def test_reduction_ends_at_targets_without_truncating_text() -> None:
    paragraphs = tuple(_paragraph(n, text="Норма " + "а" * 150) for n in range(4))
    target_only = select_prompt_part((_item(),), paragraphs, ())
    result = select_prompt_part(
        (_item(),),
        paragraphs,
        (_window(1), _window(2), _window(3)),
        char_cap=len(target_only.prompt_part),
    )
    assert result.windows_per_item == 0
    assert result.inside_target_windows_dropped
    assert result.prompt_part == target_only.prompt_part
    with pytest.raises(RankingRefused, match="target rows alone"):
        select_prompt_part((_item(),), paragraphs, (), char_cap=len(target_only.prompt_part) - 1)


def test_reduction_lowers_window_limit_uniformly_from_three_to_two() -> None:
    items = (
        _item(),
        RetrievalItem("item-2", _basis(), (TargetSpan("ndoc_1", 0, 0),)),
    )
    paragraphs = tuple(_paragraph(n) for n in range(4))
    two_window_size = len(
        select_prompt_part(items, paragraphs, (_window(1), _window(2))).prompt_part
    )
    reduced = select_prompt_part(
        items,
        paragraphs,
        (_window(1), _window(2), _window(3)),
        char_cap=two_window_size,
    )
    assert reduced.windows_per_item == 2
    assert reduced.inside_target_windows_dropped
    assert [row.item_id for row in reduced.rows].count("item-1") == 3
    assert [row.item_id for row in reduced.rows].count("item-2") == 3


def test_inside_target_windows_are_dropped_before_reducing_uniform_limit() -> None:
    paragraphs = tuple(_paragraph(n) for n in range(2))
    target_only = select_prompt_part((_item(),), paragraphs, ())
    selected = select_prompt_part(
        (_item(),), paragraphs, (_window(0, axis=0), _window(1)),
        char_cap=len(target_only.prompt_part),
    )
    assert selected.inside_target_windows_dropped
    assert selected.windows_per_item == 0
    assert [row.paragraph_id for row in selected.rows] == ["npar_0"]


def test_only_reliable_and_nfc_paragraphs_may_be_resolved() -> None:
    with pytest.raises(RankingRefused, match="unreliable"):
        select_prompt_part((_item(),), (_paragraph(0, reliable=False),), ())
    with pytest.raises(RankingRefused, match="non-NFC"):
        select_prompt_part((_item(),), (_paragraph(0, text="A\u0301"),), ())
    with pytest.raises(RankingRefused, match="outside supplied paragraphs"):
        select_prompt_part((_item(),), (_paragraph(0),), (_window(1),))


def test_invalid_vectors_identities_and_window_limit_fail_closed() -> None:
    with pytest.raises(RankingRefused, match="float32"):
        exact_inner_product(array("d", [1.0]), _basis())
    invalid = _basis()
    invalid[1] = float("nan")
    with pytest.raises(RankingRefused, match="non-finite"):
        select_prompt_part((RetrievalItem("x", invalid, _item().targets),), (_paragraph(0),), ())
    with pytest.raises(RankingRefused, match="duplicate paragraph"):
        select_prompt_part((_item(),), (_paragraph(0), _paragraph(0)), ())
    with pytest.raises(RankingRefused, match="duplicate window"):
        select_prompt_part((_item(),), (_paragraph(0),), (_window(0), _window(0)))
    shared_vector = _basis()
    windows = tuple(
        RetrievalWindow("ndoc_1", index, 0, 0, 0, shared_vector)
        for index in range(MAX_CANDIDATE_WINDOWS + 1)
    )
    with pytest.raises(RankingRefused, match="too many candidate"):
        select_prompt_part((_item(),), (_paragraph(0),), windows)


def test_unmapped_document_windows_cannot_enter_the_prompt_part() -> None:
    unrelated = RetrievalWindow("ndoc_other", 0, 0, 0, 0, _basis())
    result = select_prompt_part((_item(),), (_paragraph(0),), (unrelated,))
    assert [row.document_id for row in result.rows] == ["ndoc_1"]


def test_impossible_huge_spans_are_refused_before_ordinal_expansion() -> None:
    huge = 10**12
    paragraph = _paragraph(0)
    item = RetrievalItem("item-1", _basis(), (TargetSpan("ndoc_1", 0, huge),))
    with pytest.raises(RankingRefused, match="target span lies outside"):
        select_prompt_part((item,), (paragraph,), ())
    window = RetrievalWindow("ndoc_1", 0, 0, 0, huge, _basis())
    with pytest.raises(RankingRefused, match="window span lies outside"):
        select_prompt_part((_item(),), (paragraph,), (window,))
