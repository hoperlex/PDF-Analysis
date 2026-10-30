"""`W60-OPT-PROPOSALS-01` phase A: the cheaper-analog generator, container-free.

The subject is the money rule and the analog rules: a proposal only for a row matched to
exactly one position; only a cheaper position of the same revision, in the same unit and
currency, from a vendor on the effective list, of the same kind (head word, then code
family or name similarity); at most N per row in a fixed order; the saving exactly
``(current − proposed) × quantity`` and absent -- never 0 -- without a numeric quantity.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import pytest

from auditmanager.optimisation.matching import (
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    STATUS_UNMATCHED,
    match_specification,
)
from auditmanager.optimisation.proposals.generator import (
    BASIS_CODE_FAMILY,
    BASIS_NAME_SIMILARITY,
    GENERATOR_VERSION,
    MAX_PROPOSALS_PER_ROW,
    MAX_ROW_TEXT,
    NAME_SIMILARITY_THRESHOLD,
    PROPOSAL_TYPE_CHEAPER_ANALOG,
    code_family,
    generate_cheaper_analogs,
    head_word,
    name_similarity,
    saving_for,
    vendor_key,
)
from auditmanager.optimisation.repository import PriceListPositionRecord
from auditmanager.optimisation.specification import SpecificationRow

PRICE_LIST = "prl_01M2545JSD15ETSNNV904XA001"
VENDORS = ("ООО «Промет»", "Кнауф Гипс", "Завод ЖБИ-3")


def _position(
    number: int,
    name: str,
    unit: str,
    price: str,
    *,
    currency: str = "RUB",
    code: str | None = None,
    mark: str | None = None,
    vendor: str | None = "Промет",
    price_list: str = PRICE_LIST,
) -> PriceListPositionRecord:
    return PriceListPositionRecord(
        price_list_position_id=f"prp_01M2545JSD15ETSNNV904X{number:03d}",
        price_list_id=price_list,
        row_number=number,
        code=code,
        name=name,
        mark=mark,
        unit=unit,
        unit_price=Decimal(price),
        currency=currency,
        vendor=vendor,
        section_code=None,
    )


def _row(
    name: str,
    unit: str | None = "шт",
    quantity: str | None = "10",
    *,
    line: int = 1,
    page: int = 1,
) -> SpecificationRow:
    return SpecificationRow(
        row_id=f"sr-{page:016x}{line:016x}",
        page_number=page,
        sheet_label="10",
        line_start=line,
        line_end=line,
        table_ordinal=1,
        group=None,
        position=str(line),
        name=name,
        unit_text=unit,
        unit=unit,
        unit_source="column" if unit else None,
        quantity_text=quantity if quantity is not None else "-",
        quantity=None if quantity is None else Decimal(quantity),
        quantity_issue=None if quantity is not None else "not_numeric",
        mass_text=None,
        note=None,
    )


DOOR = _position(1, "Дверь противопожарная", "шт", "25000", mark="ДПМ-01/60", vendor="Другой завод")
DOOR_CHEAP = _position(2, "Дверь противопожарная", "шт", "21000", mark="ДПМ-02/60")
DOOR_CHEAPER = _position(3, "Дверь противопожарная металлическая", "шт", "19500", vendor="Кнауф Гипс")
DOOR_EXPENSIVE = _position(4, "Дверь противопожарная", "шт", "26000")
WINDOW = _position(5, "Окно ПВХ двухкамерное", "шт", "18500")
SLAB = _position(6, "Плита перекрытия многопустотная", "шт", "9000", code="ПК 60-12-8",
                 vendor="Завод ЖБИ-3")
SLAB_CHEAP = _position(7, "Плита пустотная облегчённая", "шт", "8000", code="ПК 63-15-8",
                       vendor="АО «Завод ЖБИ-3»")
POSITIONS = (DOOR, DOOR_CHEAP, DOOR_CHEAPER, DOOR_EXPENSIVE, WINDOW, SLAB, SLAB_CHEAP)


def _generate(rows, positions=POSITIONS, vendors=VENDORS):
    outcome = match_specification(rows, positions)
    return generate_cheaper_analogs(outcome.matches, positions, vendors)


# -- the analog rules -------------------------------------------------------------------------


def test_a_matched_row_gets_its_cheaper_analogs_cheapest_first() -> None:
    result = _generate([_row("Дверь противопожарная ДПМ-01/60", quantity="4")])
    assert result.generator_version == GENERATOR_VERSION
    assert [draft.proposed.row_number for draft in result.proposals] == [3, 2]
    first, second = result.proposals
    assert (first.ordinal, second.ordinal) == (1, 2)
    assert first.proposal_type == PROPOSAL_TYPE_CHEAPER_ANALOG
    assert first.matched is DOOR and first.matched_basis == "mark"
    assert (first.current_unit_price, first.proposed_unit_price) == (Decimal("25000"), Decimal("19500"))
    assert (first.unit, first.currency, first.quantity) == ("шт", "RUB", Decimal("4"))
    assert first.saving == Decimal("22000")  # (25000 - 19500) x 4
    assert second.saving == Decimal("16000")  # (25000 - 21000) x 4
    assert first.analog_basis == BASIS_NAME_SIMILARITY and first.similarity == Decimal("0.6666")
    # ДПМ-01/60 and ДПМ-02/60: one code family wins over the (also full) name similarity.
    assert second.analog_basis == BASIS_CODE_FAMILY and second.similarity == Decimal("1")
    assert "Более дешёвый аналог" in first.rationale and "поставщик Кнауф Гипс" in first.rationale
    assert "вместо «Дверь противопожарная» (ДПМ-01/60)" in first.rationale
    assert not any(character.isdigit() for character in first.rationale.split("(")[0])
    assert (result.rows_total, result.rows_matched, result.rows_with_proposals) == (1, 1, 1)


def test_the_same_code_family_is_an_analog_even_with_dissimilar_names() -> None:
    result = _generate([_row("Плита перекрытия многопустотная ПК 60-12-8", quantity="20")])
    (draft,) = result.proposals
    assert draft.proposed is SLAB_CHEAP and draft.analog_basis == BASIS_CODE_FAMILY
    assert name_similarity(SLAB.name, SLAB_CHEAP.name) < NAME_SIMILARITY_THRESHOLD
    assert draft.saving == Decimal("20000")
    assert "семейство кода «пк»" in draft.rationale


def test_a_dearer_or_equal_position_is_never_proposed() -> None:
    equal = _position(8, "Дверь противопожарная", "шт", "25000")
    result = _generate([_row("Дверь противопожарная ДПМ-01/60")], (*POSITIONS, equal))
    assert {draft.proposed.row_number for draft in result.proposals} == {2, 3}


def test_another_unit_or_currency_is_never_an_analog() -> None:
    per_metre = _position(8, "Дверь противопожарная", "м", "100")
    in_euro = _position(9, "Дверь противопожарная", "шт", "200", currency="EUR")
    running = _position(10, "Профиль направляющий ПН 50х40", "м2", "50")
    metre = _position(11, "Профиль направляющий ПН 50х40", "м", "95")
    positions = (DOOR, per_metre, in_euro, running, metre)
    result = _generate(
        [_row("Дверь противопожарная ДПМ-01/60"), _row("Профиль направляющий ПН 50х40", "м", line=2)],
        positions,
    )
    assert result.proposals == ()
    assert (result.rows_matched, result.rows_without_analog) == (2, 2)


def test_a_vendor_off_the_list_or_no_vendor_is_never_proposed() -> None:
    nameless = replace(DOOR_CHEAPER, vendor=None)
    stranger = replace(DOOR_CHEAP, vendor="Неизвестный поставщик")
    result = _generate([_row("Дверь противопожарная ДПМ-01/60")], (DOOR, nameless, stranger))
    assert result.proposals == () and result.rows_without_analog == 1


def test_an_empty_vendor_list_proposes_nothing() -> None:
    result = _generate([_row("Дверь противопожарная ДПМ-01/60")], vendors=())
    assert result.proposals == () and result.rows_without_analog == 1


def test_another_kind_of_product_is_never_an_analog() -> None:
    cheap_window = _position(8, "Окно противопожарное", "шт", "100")
    cheap_hatch = _position(9, "Люк противопожарный", "шт", "100", mark="ДПМ-03")
    result = _generate([_row("Дверь противопожарная ДПМ-01/60")], (DOOR, cheap_window, cheap_hatch))
    assert result.proposals == ()


def test_at_most_n_proposals_per_row_in_a_fixed_order() -> None:
    many = tuple(
        _position(10 + index, "Дверь противопожарная", "шт", str(24000 - 1000 * (index % 3)))
        for index in range(6)
    )
    result = _generate([_row("Дверь противопожарная ДПМ-01/60")], (DOOR, *many))
    assert len(result.proposals) == MAX_PROPOSALS_PER_ROW == 3
    # Price ascending, then (equal similarity) source row.
    assert [draft.proposed.row_number for draft in result.proposals] == [12, 15, 11]


def test_ordinals_run_across_rows_in_extraction_order() -> None:
    rows = [
        _row("Плита перекрытия многопустотная ПК 60-12-8", line=1),
        _row("Окно ПВХ двухкамерное", line=2),
        _row("Дверь противопожарная ДПМ-01/60", line=3),
    ]
    result = _generate(rows)
    assert [(draft.ordinal, draft.row.line_start) for draft in result.proposals] == [
        (1, 1), (2, 3), (3, 3),
    ]
    assert (result.rows_matched, result.rows_with_proposals, result.rows_without_analog) == (3, 2, 1)


def test_the_generator_is_deterministic_and_independent_of_position_order() -> None:
    rows = [_row("Дверь противопожарная ДПМ-01/60"), _row("Плита перекрытия многопустотная ПК 60-12-8", line=2)]
    first = _generate(rows)
    again = _generate(rows, tuple(reversed(POSITIONS)))
    assert first == again


# -- the money rule ---------------------------------------------------------------------------


def test_without_a_numeric_quantity_the_saving_is_absent_not_zero() -> None:
    result = _generate([_row("Дверь противопожарная ДПМ-01/60", quantity=None)])
    assert result.proposals
    for draft in result.proposals:
        assert draft.quantity is None
        assert draft.saving is None
        assert draft.saving != Decimal(0)
        assert draft.current_unit_price > draft.proposed_unit_price  # prices still shown


def test_the_saving_is_exact_and_never_rounded() -> None:
    cheap = _position(8, "Дверь противопожарная", "шт", "24999.999999")
    result = _generate([_row("Дверь противопожарная ДПМ-01/60", quantity="2.5")], (DOOR, cheap))
    (draft,) = result.proposals
    assert draft.saving == Decimal("0.0000025")
    assert saving_for(current_unit_price=Decimal("3"), proposed_unit_price=Decimal("1"),
                      quantity=Decimal("0")) == Decimal("0")
    assert saving_for(current_unit_price=Decimal("3"), proposed_unit_price=Decimal("1"),
                      quantity=None) is None


def test_an_ambiguous_or_unmatched_row_never_yields_a_proposal() -> None:
    twin = _position(8, "Дверь противопожарная", "шт", "25000", mark="ДПМ-01/60", vendor="Промет")
    rows = [_row("Дверь противопожарная ДПМ-01/60"), _row("Что-то иное", line=2)]
    outcome = match_specification(rows, (DOOR, twin, DOOR_CHEAP))
    assert [match.status for match in outcome.matches] == [STATUS_AMBIGUOUS, STATUS_UNMATCHED]
    result = generate_cheaper_analogs(outcome.matches, (DOOR, twin, DOOR_CHEAP), VENDORS)
    assert result.proposals == ()
    assert (result.rows_not_matched, result.rows_matched) == (2, 0)


def test_a_unit_mismatched_row_never_yields_a_proposal() -> None:
    rows = [_row("Дверь противопожарная ДПМ-01/60", unit="м")]
    outcome = match_specification(rows, POSITIONS)
    assert outcome.matches[0].reason == "unit_mismatch"
    assert generate_cheaper_analogs(outcome.matches, POSITIONS, VENDORS).proposals == ()


def test_a_forged_matched_status_with_a_unit_mismatch_is_refused_by_the_generator() -> None:
    """The generator re-checks the unit itself: a match claiming another unit adds nothing."""
    (match,) = match_specification([_row("Дверь противопожарная ДПМ-01/60")], POSITIONS).matches
    assert match.status == STATUS_MATCHED
    forged = replace(match, row=replace(match.row, unit="м", unit_text="м"))
    assert generate_cheaper_analogs((forged,), POSITIONS, VENDORS).proposals == ()
    forged_status = replace(match, status=STATUS_AMBIGUOUS)
    assert generate_cheaper_analogs((forged_status,), POSITIONS, VENDORS).proposals == ()


def test_a_position_of_another_revision_is_a_caller_error() -> None:
    (match,) = match_specification([_row("Дверь противопожарная ДПМ-01/60")], POSITIONS).matches
    foreign = tuple(replace(position, price_list_id="prl_01M2545JSD15ETSNNV904XA002",
                            price_list_position_id=position.price_list_position_id[:-3] + "Z99")
                    for position in POSITIONS[1:])
    with pytest.raises(ValueError):
        generate_cheaper_analogs((match,), foreign, VENDORS)


def test_a_row_too_long_to_store_is_counted_not_cut() -> None:
    long_name = "Дверь противопожарная ДПМ-01/60 " + "x" * MAX_ROW_TEXT
    (match,) = match_specification([_row("Дверь противопожарная ДПМ-01/60")], POSITIONS).matches
    oversized = replace(match, row=replace(match.row, name=long_name))
    result = generate_cheaper_analogs((oversized,), POSITIONS, VENDORS)
    assert result.proposals == () and result.rows_out_of_bounds == 1


# -- the keys ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("ООО «Промет»", "Промет"),
        ('АО "Кнауф Гипс"', "кнауф  гипс"),
        ("Завод ЖБИ-3", "завод жби 3"),
        ("ЗАВОД ЖБИ-3, ООО", "Завод ЖБИ-3"),
        ("Ёлка", "Елка"),
    ],
)
def test_vendor_names_compare_without_case_quotes_punctuation_or_legal_form(left: str, right: str) -> None:
    assert vendor_key(left) == vendor_key(right) is not None


def test_vendor_keys_keep_different_names_apart() -> None:
    assert vendor_key("Промет") != vendor_key("Промет-2")
    assert vendor_key(None) is None and vendor_key("ООО") is None


def test_head_word_and_similarity() -> None:
    assert head_word("Мет. щит МЩ-1") == head_word("Металлический щит") == "мет"
    assert head_word("1250 Плита") == "плита"
    assert name_similarity("Плита перекрытия ПК 60-12-8", "Плита перекрытия ПК 63-15-8") == Fraction(3, 5)
    assert name_similarity("", "") == 0


def test_code_family_needs_two_letters_followed_by_a_digit() -> None:
    assert code_family(SLAB) == "пк"
    assert code_family(replace(SLAB, code=None, mark="ДПМ-01/60")) == "дпм"
    assert code_family(replace(SLAB, code="С21-1000")) is None  # one letter
    assert code_family(replace(SLAB, code="ГОСТ")) is None  # no digit
    assert code_family(replace(SLAB, code=None, mark=None)) is None


def test_running_metre_analog_uses_factor_one_and_price_list_money() -> None:
    current = _position(20, 'Кабель силовой ВВГ', 'м', '95', code='ВВГ-001')
    cheaper = _position(21, 'Кабель силовой ВВГ', 'п.м', '50', code='ВВГ-002')
    result = _generate([_row('Кабель силовой ВВГ ВВГ-001', 'м', quantity='12')], (current, cheaper))
    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert proposal.proposed is cheaper
    assert proposal.saving == Decimal('540')
    assert result.generator_version == 'cheaper-analog-v2'
