from __future__ import annotations

from decimal import Decimal

import pytest

from auditmanager.norms.citation_prep import (
    NormCitation,
    NormLabelBinding,
    NormParagraph,
    ground_norm_observation,
    normalize_paragraph,
    normalize_quote,
    value_in_quotes,
    value_tokens,
)


def _paragraph(
    text: str,
    *,
    label: str | None = "N1",
    paragraph_id: str = "p1",
    document_id: str = "d1",
    reliable: bool = True,
) -> NormParagraph:
    return NormParagraph(paragraph_id, document_id, text, label, reliable)


def _ground(
    paragraphs: tuple[NormParagraph, ...],
    quote: str,
    *,
    required: str = "1,4",
    stated: str = "1,2",
    evidence: tuple[str, ...] = ("Проектное значение 1,2 принято.",),
):
    return ground_norm_observation(
        paragraphs, (NormCitation("N1", quote),), required, stated, evidence
    )


def test_normalization_preserves_exact_raw_offsets_and_deletions() -> None:
    raw = "\u00a0\u2007**А\u00adБ\u2009\u200b\u202fВ\n  "
    normalized = normalize_paragraph(raw)
    assert normalized.text == "АБ В"
    assert normalized.raw_offsets == (4, 6, 7, 10)
    assert raw[normalized.raw_offsets[2]] == "\u2009"
    assert normalize_quote("A\u0301") == "Á"
    with pytest.raises(ValueError, match="norm_paragraph_not_nfc"):
        normalize_paragraph("A\u0301")
    assert normalize_quote("X**Y") == "XY"
    assert normalize_quote("a|b") == "a|b"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3{,}5 м^{2} и м2", (Decimal("3.5"),)),
        ("Rw52; 7.1.4; 1 000", (Decimal("1000"),)),
        ("−30", (Decimal("-30"),)),
        ("от -30 до +40", (Decimal("-30"), Decimal("40"))),
        ("1,2-1,5", (Decimal("1.2"), Decimal("1.5"))),
        ("1,2–1,5", (Decimal("1.2"), Decimal("1.5"))),
        ("1,2 - 1,5", (Decimal("1.2"), Decimal("1.5"))),
        ("1,2 -1,5", (Decimal("1.2"), Decimal("1.5"))),
        ("1\u00a0000", (Decimal("1000"),)),
    ],
)
def test_declared_numeric_tokenizer(value: str, expected: tuple[Decimal, ...]) -> None:
    assert value_tokens(value) == expected


def test_numeric_membership_does_not_match_substrings_or_missing_values() -> None:
    assert value_in_quotes("1,4", ("Значение 1.40 м",))
    assert not value_in_quotes("1,4", ("Значение 11,4 м",))
    assert not value_in_quotes("1,4", ("Значение 1,45 м",))
    assert value_in_quotes("класс А", ("Требуемый класс А",))
    assert not value_in_quotes("А", ("Требуемый класс А",))
    assert not value_in_quotes("1,4 и 2,5", ("Есть 1,4",))


def test_verification_stores_raw_substring_at_paragraph_start_and_end() -> None:
    raw = "**Минимальная ширина прохода 1\u00a0м** и требуемое значение 1,4."
    result = _ground((_paragraph(raw),), "Минимальная ширина прохода 1 м", required="1")
    assert result.accepted
    citation = result.citations[0]
    assert citation.state == "verified"
    assert citation.raw_offset == 2
    assert (
        raw[citation.raw_offset : citation.raw_offset + len(citation.raw_quote)]
        == citation.raw_quote
    )
    assert citation.raw_quote == "Минимальная ширина прохода 1\u00a0м"

    tail = "Таблица | требуемое значение 1,4 | применяется"
    end_result = _ground((_paragraph("Ввод. " + tail),), tail)
    assert end_result.accepted
    assert end_result.citations[0].raw_offset == len("Ввод. ")
    assert (
        _ground((_paragraph("Ввод. " + tail),), tail.replace("|", " ")).reason
        == "norm_quote_absent"
    )


def test_rebinds_only_to_one_reliable_paragraph_in_same_document() -> None:
    quote = "Требуемая толщина слоя составляет 1,4 м"
    paragraphs = (
        _paragraph("Здесь иное положение нормы 2,0 м"),
        _paragraph(quote, label=None, paragraph_id="p2"),
        _paragraph(quote, label=None, paragraph_id="p3", document_id="other"),
    )
    result = _ground(paragraphs, quote)
    assert result.accepted
    assert (result.citations[0].state, result.citations[0].paragraph_id) == ("rebound", "p2")
    ambiguous = _ground(paragraphs + (_paragraph(quote, label=None, paragraph_id="p4"),), quote)
    assert ambiguous.reason == "norm_quote_ambiguous"
    assert ambiguous.citations == ()


def test_citation_failures_withhold_all_and_follow_declared_order() -> None:
    quote = "Требуемое значение равно 1,4 метра"
    para = _paragraph(quote)
    assert (
        ground_norm_observation(
            (para,), (NormCitation("missing", quote),), "1,4", "1,2", ("1,2",)
        ).reason
        == "norm_label_unknown"
    )
    assert _ground((para,), "коротко").reason == "norm_quote_too_short"
    assert (
        _ground((para,), "Отсутствующее требование равно 1,4 метра").reason
        == "norm_quote_absent"
    )
    assert _ground((para,), quote, required="11,4").reason == "norm_value_not_in_quote"
    assert _ground((para,), quote, stated="11,2").reason == "stated_value_not_in_evidence"
    two = ground_norm_observation(
        (para,),
        (NormCitation("N1", quote), NormCitation("N1", "несуществующая достаточно длинная цитата")),
        "1,4",
        "1,2",
        ("1,2",),
    )
    assert two.reason == "norm_quote_absent" and two.citations == ()


def test_non_nfc_unreliable_and_cross_paragraph_quotes_are_excluded() -> None:
    quote = "Требуемое значение равно 1,4 метра"
    non_nfc = _paragraph(
        "A\u0301 Требуемое значение равно 1,4 метра", label=None, paragraph_id="bad"
    )
    result = _ground((_paragraph("В этом абзаце другая норма"), non_nfc), quote)
    assert result.reason == "norm_quote_absent"
    assert result.skipped_non_nfc == ("bad",)
    unreliable = _paragraph(quote, label=None, paragraph_id="ocr", reliable=False)
    assert (
        _ground((_paragraph("В этом абзаце другая норма"), unreliable), quote).reason
        == "norm_quote_absent"
    )
    first = _paragraph("Требуемое значение равно", label="N1")
    second = _paragraph("1,4 метра", label=None, paragraph_id="p2")
    assert _ground((first, second), quote).reason == "norm_quote_absent"


def test_raw_span_over_4000_is_absent_even_when_normalized_quote_matches() -> None:
    quote = "Требуемое значение равно 1,4 метра"
    raw = quote[:12] + "\u00ad" * 4001 + quote[12:]
    valid_elsewhere = _paragraph(quote, label=None, paragraph_id="p2")
    assert _ground((_paragraph(raw), valid_elsewhere), quote).reason == "norm_quote_absent"


def test_duplicate_paragraph_and_label_identities_are_refused() -> None:
    with pytest.raises(ValueError, match="duplicate_norm_paragraph_id"):
        _ground((_paragraph("a"), _paragraph("b")), "anything long enough 1,4")
    with pytest.raises(ValueError, match="duplicate_norm_label"):
        _ground((_paragraph("a"), _paragraph("b", paragraph_id="p2")), "anything long enough 1,4")


def test_two_map_item_labels_can_address_one_canonical_paragraph() -> None:
    quote = "Минимальная ширина прохода составляет 1,4 м"
    result = ground_norm_observation(
        (_paragraph(quote, label=None),),
        (NormCitation("N2", quote),),
        "1,4 м", "1,2 м", ("Ширина прохода 1,2 м",),
        label_bindings=(NormLabelBinding("N1", "p1"), NormLabelBinding("N2", "p1")),
    )
    assert result.accepted
    assert [(item.label, item.paragraph_id, item.state) for item in result.citations] == [
        ("N2", "p1", "verified"),
    ]


def test_separate_label_bindings_refuse_duplicate_foreign_or_mixed_sources() -> None:
    quote = "Минимальная ширина прохода составляет 1,4 м"
    no_inline = (_paragraph(quote, label=None),)
    arguments = ((NormCitation("N1", quote),), "1,4", "1,2", ("1,2",))
    with pytest.raises(ValueError, match="duplicate_norm_label"):
        ground_norm_observation(
            no_inline, *arguments,
            label_bindings=(NormLabelBinding("N1", "p1"), NormLabelBinding("N1", "p1")),
        )
    with pytest.raises(ValueError, match="invalid_norm_label_binding"):
        ground_norm_observation(
            no_inline, *arguments, label_bindings=(NormLabelBinding("N1", "foreign"),),
        )
    with pytest.raises(ValueError, match="mixed_or_invalid_norm_label_sources"):
        ground_norm_observation(
            (_paragraph(quote),), *arguments,
            label_bindings=(NormLabelBinding("N1", "p1"),),
        )
