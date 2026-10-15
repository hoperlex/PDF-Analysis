from __future__ import annotations

from array import array

import pytest

from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.ranking import (
    RetrievalItem,
    RetrievalParagraph,
    select_prompt_part,
)
from auditmanager.norms.retrieval.targets import (
    TargetParagraph,
    TargetRefused,
    resolve_clause,
    resolve_range,
    resolve_table,
)


def _paragraph(
    ordinal: int,
    text: str,
    *,
    kind: str = "body",
    clause_number: str | None = None,
    reliable: bool = True,
) -> TargetParagraph:
    return TargetParagraph(
        document_id="ndoc_1",
        paragraph_id=f"npar_{ordinal}",
        ordinal=ordinal,
        text=text,
        kind=kind,
        clause_number=clause_number,
        reliable=reliable,
    )


def test_clause_includes_descendants_and_unnumbered_text_but_stops_at_sibling() -> None:
    paragraphs = (
        _paragraph(0, "7.1.3 Предыдущий пункт", clause_number="7.1.3"),
        _paragraph(1, "**7.1.4** Основной пункт"),
        _paragraph(2, "Продолжение без номера"),
        _paragraph(3, "7.1.4.1 Подпункт", clause_number="7.1.4.1"),
        _paragraph(4, "Строка продолжения"),
        _paragraph(5, "7.1.5 Следующий пункт", clause_number="7.1.5"),
    )
    result = resolve_clause(paragraphs, "7.1.4")
    assert [(span.ordinal_first, span.ordinal_last) for span in result.spans] == [(1, 4)]
    assert result.paragraph_ids == ("npar_1", "npar_2", "npar_3", "npar_4")


def test_clause_boundary_is_heading_even_when_numbered_as_descendant() -> None:
    paragraphs = (
        _paragraph(0, "7.1.4 Начало", clause_number="7.1.4"),
        _paragraph(1, "Текст"),
        _paragraph(2, "# 7.1.4.1 Новый заголовок", kind="heading", clause_number="7.1.4.1"),
        _paragraph(3, "Продолжение заголовка"),
    )
    assert resolve_clause(paragraphs, "7.1.4").paragraph_ids == ("npar_0", "npar_1")


def test_table_caption_markdown_forms_include_rows_and_notes() -> None:
    for caption in ("**Таблица 5.34** Размеры", "###### Таблица 5.34 Размеры"):
        paragraphs = (
            _paragraph(0, "5.1 Ранее", clause_number="5.1"),
            _paragraph(1, caption, kind="heading" if caption.startswith("#") else "body"),
            _paragraph(2, "| Показатель | Значение |", kind="table_row"),
            _paragraph(3, "Примечание. Значение уточняют."),
            _paragraph(4, "5.2 Следующий пункт", clause_number="5.2"),
        )
        result = resolve_table(paragraphs, "таблица 5.34")
        assert result.paragraph_ids == ("npar_1", "npar_2", "npar_3")


def test_explicit_range_excludes_unreliable_and_splits_contiguous_spans() -> None:
    paragraphs = (
        _paragraph(0, "А.2.1 Первый"),
        _paragraph(1, "Распознанное ненадёжное", reliable=False),
        _paragraph(2, "Формула R_o^{\\text{норм}}"),
        _paragraph(3, "Продолжение"),
    )
    result = resolve_range(paragraphs, "npar_0", "npar_3")
    assert [(span.ordinal_first, span.ordinal_last) for span in result.spans] == [(0, 0), (2, 3)]
    assert result.paragraph_ids == ("npar_0", "npar_2", "npar_3")
    assert result.excluded_unreliable == ("npar_1",)

    vector = array("f", [0.0]) * DIMENSIONS
    vector[0] = 1.0
    reliable_rows = tuple(
        RetrievalParagraph(
            document_id=paragraph.document_id,
            paragraph_id=paragraph.paragraph_id,
            designation="СП 50",
            title="Тепловая защита",
            ordinal=paragraph.ordinal,
            clause_number=paragraph.clause_number,
            page_label="1",
            text=paragraph.text,
        )
        for paragraph in paragraphs
        if paragraph.reliable
    )
    selected = select_prompt_part((RetrievalItem("item", vector, result.spans),), reliable_rows, ())
    assert tuple(row.paragraph_id for row in selected.rows) == result.paragraph_ids


def test_anchor_itself_must_be_reliable() -> None:
    with pytest.raises(TargetRefused, match="anchor paragraph is unreliable"):
        resolve_clause(
            (_paragraph(0, "7.1.4 Нечитаемо", clause_number="7.1.4", reliable=False),),
            "7.1.4",
        )


def test_ambiguous_missing_or_reversed_targets_fail_closed() -> None:
    paragraphs = (
        _paragraph(0, "Таблица 5.34 первая"),
        _paragraph(1, "Таблица 5.34 вторая"),
    )
    with pytest.raises(TargetRefused, match="ambiguous"):
        resolve_table(paragraphs, "таблица 5.34")
    with pytest.raises(TargetRefused, match="absent"):
        resolve_clause(paragraphs, "7.1.4")
    with pytest.raises(TargetRefused, match="reversed"):
        resolve_range(paragraphs, "npar_1", "npar_0")
    with pytest.raises(TargetRefused, match="absent"):
        resolve_range(paragraphs, "npar_missing", "npar_1")


def test_incomplete_ordinals_or_duplicate_identity_fail_before_resolution() -> None:
    paragraphs = (
        _paragraph(0, "7.1.4 Начало", clause_number="7.1.4"),
        _paragraph(2, "Текст"),
    )
    with pytest.raises(TargetRefused, match="not complete"):
        resolve_clause(paragraphs, "7.1.4")
    duplicates = (
        _paragraph(0, "Текст"),
        TargetParagraph("ndoc_1", "npar_0", 1, "Ещё текст", "body", None),
    )
    with pytest.raises(TargetRefused, match="duplicate paragraph"):
        resolve_range(duplicates, "npar_0", "npar_0")
