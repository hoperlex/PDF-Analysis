"""`W60-OPT-MATCH-01` phase A: specification rows matched to price-list positions, container-free.

The money rule is the subject: a price and an amount only for a row matched to exactly one
position in the same unit with a numeric quantity; totals per currency over those rows only,
with every other row counted by the reason it is left out. Matching is exact on normalised
text -- code or mark first, then the name -- and never fuzzy.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from auditmanager.optimisation.matching import (
    BASIS_CODE,
    BASIS_MARK,
    BASIS_NAME,
    EXCLUSION_REASONS,
    MATCH_ALGORITHM,
    MAX_LISTED_CANDIDATES,
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    STATUS_UNMATCHED,
    canonical_amount,
    match_specification,
    name_key,
    unit_key,
)
from auditmanager.optimisation.repository import PriceListPositionRecord
from auditmanager.optimisation.specification import SpecificationRow, extract_specification

PRICE_LIST = "prl_01M2545JSD15ETSNNV904XA001"


def _position(
    number: int,
    name: str,
    unit: str,
    price: str,
    *,
    currency: str = "RUB",
    code: str | None = None,
    mark: str | None = None,
    vendor: str | None = None,
) -> PriceListPositionRecord:
    return PriceListPositionRecord(
        price_list_position_id=f"prp_01M2545JSD15ETSNNV904X{number:03d}",
        price_list_id=PRICE_LIST,
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
    quantity: str | None = "1",
    *,
    line: int = 1,
    issue: str | None = None,
) -> SpecificationRow:
    return SpecificationRow(
        row_id=f"sr-{line:032x}",
        page_number=1,
        sheet_label=None,
        line_start=line,
        line_end=line,
        table_ordinal=1,
        group=None,
        position=str(line),
        name=name,
        unit_text=unit,
        unit=unit,
        unit_source=None if unit is None else "column",
        quantity_text=quantity,
        quantity=None if quantity is None or issue else Decimal(quantity.replace(",", ".")),
        quantity_issue=issue,
        mass_text=None,
        note=None,
    )


def _one(row: SpecificationRow, *positions: PriceListPositionRecord):
    outcome = match_specification([row], positions)
    (match,) = outcome.matches
    return match, outcome


# -- code and mark -----------------------------------------------------------------------


def test_a_position_code_inside_the_description_matches_first() -> None:
    door = _position(1, "Дверь", "шт", "25000", code="ДПМ-01/60")
    match, outcome = _one(_row("Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет»", quantity="4"), door)
    assert (match.status, match.basis, match.position, match.amount) == (
        STATUS_MATCHED, BASIS_CODE, door, Decimal("100000"),
    )
    assert outcome.algorithm == MATCH_ALGORITHM


def test_a_mark_matches_as_whole_tokens_only() -> None:
    wall = _position(1, "Стена из газобетона", "м3", "7000", mark="СВ-1.2")
    assert _one(_row("Стена СВ-1.2 D600", unit="м3"), wall)[0].basis == BASIS_MARK
    assert _one(_row("Стена СВ-1.25 D600", unit="м3"), wall)[0].status == STATUS_UNMATCHED


@pytest.mark.parametrize(
    "key",
    ["МЩ-1", "ГОСТ 530-2012", "ТУ 5767-001-2010", "ГОСТ30674-99", "EN ISO 13849-1", "ПВХ", "12345"],
)
def test_short_or_shared_keys_never_match_by_code(key: str) -> None:
    position = _position(1, "Изделие", "шт", "10", code=key, mark=key)
    match, _ = _one(_row(f"Окно ПВХ {key} шт"), position)
    assert (match.status, match.reason) == (STATUS_UNMATCHED, "no_position")


def test_a_code_match_in_another_unit_does_not_fall_back_to_the_name() -> None:
    by_code = _position(1, "Мембрана", "рулон", "9000", code="ТЭ-ЭПП-4")
    by_name = _position(2, "Мембрана Техноэласт ТЭ-ЭПП-4", "м2", "400")
    match, _ = _one(_row("Мембрана Техноэласт ТЭ-ЭПП-4", unit="м2", quantity="10"), by_code, by_name)
    assert (match.status, match.reason, match.amount) == (STATUS_UNMATCHED, "unit_mismatch", None)
    assert match.candidate_ids == (by_code.price_list_position_id,)


def test_two_positions_with_the_same_code_are_a_tie() -> None:
    first = _position(1, "Кабель", "м", "120", code="ВВГнг-LS-3х2,5")
    second = _position(2, "Кабель", "м", "118", code="ВВГнг-LS-3х2,5")
    match, outcome = _one(_row("Кабель ВВГнг-LS-3х2,5", unit="м", quantity="100"), first, second)
    assert (match.status, match.reason, match.position, match.amount) == (
        STATUS_AMBIGUOUS, "several_positions", None, None,
    )
    assert match.candidate_ids == (first.price_list_position_id, second.price_list_position_id)
    assert outcome.totals == ()


# -- names -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "listed"),
    [
        ("Рифлёная сталь 690х395 t=4 мм", "рифленая  сталь 690x395 t=4мм"),
        ("Рифлёнаясталь 690х395 t=4 мм", "Рифленая сталь, 690х395, t = 4 мм"),
        ("Мет. щит МЩ-1", "Металлический щит МЩ-1"),
        ("Труба оцинк. 2,5 мм", "Труба оцинкованная 2.5 мм"),
        ("Плита ж/б ПК 60-12", "Плита железобетонная ПК 60-12"),
        ("ОКНО ПВХ", "окно пвх"),
    ],
)
def test_names_compare_after_normalisation(spec: str, listed: str) -> None:
    position = _position(1, listed, "шт", "10")
    match, _ = _one(_row(spec), position)
    assert (match.status, match.basis) == (STATUS_MATCHED, BASIS_NAME), (name_key(spec), name_key(listed))


@pytest.mark.parametrize(
    ("spec", "listed"),
    [
        ("Металлический щит МЩ-1", "Металлический щит МЩ-2"),
        ("Металлический щит МЩ-1", "Металлический щит"),
        ("Щит металлический МЩ-1", "Металлический щит МЩ-1"),
        ("Труба 2,5 мм", "Труба 25 мм"),
        ("Плита ПК 60-12", "Плита ПК 60.12"),
    ],
)
def test_names_are_never_matched_fuzzily(spec: str, listed: str) -> None:
    match, _ = _one(_row(spec), _position(1, listed, "шт", "10"))
    assert (match.status, match.reason, match.amount) == (STATUS_UNMATCHED, "no_position", None)


def test_the_name_followed_by_mark_code_and_vendor_in_form7_order_matches() -> None:
    position = _position(
        1, "Утеплитель минераловатный", "м3", "6100", mark="ВЕНТИ БАТТС", vendor="ROCKWOOL"
    )
    assert _one(_row("Утеплитель минераловатный ВЕНТИ БАТТС", unit="м3"), position)[0].status == (
        STATUS_MATCHED
    )
    assert _one(_row("Утеплитель минераловатный ВЕНТИ БАТТС ROCKWOOL", unit="м3"), position)[
        0
    ].status == STATUS_MATCHED
    assert _one(_row("Утеплитель минераловатный ROCKWOOL ВЕНТИ БАТТС", unit="м3"), position)[
        0
    ].status == STATUS_UNMATCHED


# -- units, ties, quantities -------------------------------------------------------------


def test_area_and_length_mismatch_is_unmatched_and_adds_nothing() -> None:
    profile = _position(1, "Профиль направляющий ПН 50х40", "м", "95")
    match, outcome = _one(_row("Профиль направляющий ПН 50х40", unit="м2", quantity="120"), profile)
    assert (match.status, match.reason, match.position, match.amount, match.excluded_reason) == (
        STATUS_UNMATCHED, "unit_mismatch", None, None, "unit_mismatch",
    )
    assert match.candidate_ids == (profile.price_list_position_id,)
    assert outcome.totals == ()
    assert dict(outcome.excluded_by_reason) == {"unit_mismatch": 1}


def test_the_candidate_in_the_rows_unit_is_the_match() -> None:
    per_square = _position(1, "Мембрана Техноэласт ЭПП", "м²", "410")
    per_roll = _position(2, "Мембрана Техноэласт ЭПП", "рулон", "4000")
    match, _ = _one(_row("Мембрана Техноэласт ЭПП", unit="м2", quantity="340,8"), per_roll, per_square)
    assert (match.status, match.position, match.amount) == (
        STATUS_MATCHED, per_square, Decimal("139728.0"),
    )


def test_equally_good_candidates_are_ambiguous_even_at_one_price() -> None:
    first = _position(1, "Пена монтажная", "шт", "700")
    second = _position(2, "Пена монтажная", "шт.", "700")
    match, outcome = _one(_row("Пена монтажная", quantity="3"), first, second)
    assert (match.status, match.amount, match.excluded_reason, match.candidate_count) == (
        STATUS_AMBIGUOUS, None, "ambiguous", 2,
    )
    assert outcome.totals == ()


def test_a_row_without_a_unit_is_never_priced() -> None:
    match, _ = _one(_row("Решётка вентиляционная", unit=None, quantity="6"),
                    _position(1, "Решётка вентиляционная", "шт", "900"))
    assert (match.status, match.reason, match.amount) == (STATUS_UNMATCHED, "row_unit_missing", None)


@pytest.mark.parametrize(("quantity", "issue"), [("-", "not_numeric"), ("1 250", "ambiguous")])
def test_a_matched_row_without_a_numeric_quantity_has_a_price_but_no_amount(
    quantity: str, issue: str
) -> None:
    position = _position(1, "Кирпич керамический", "шт", "38,5".replace(",", "."))
    match, outcome = _one(_row("Кирпич керамический", quantity=quantity, issue=issue), position)
    assert (match.status, match.position, match.amount, match.excluded_reason) == (
        STATUS_MATCHED, position, None, "quantity_not_numeric",
    )
    assert outcome.totals == ()


def test_the_candidate_listing_is_capped_and_the_count_complete() -> None:
    positions = [_position(n, "Хомут", "шт", "5") for n in range(1, 9)]
    match, _ = _one(_row("Хомут"), *positions)
    assert match.candidate_count == 8
    assert len(match.candidate_ids) == MAX_LISTED_CANDIDATES
    assert match.candidate_ids == tuple(p.price_list_position_id for p in positions[:5])


# -- totals ------------------------------------------------------------------------------


def test_totals_are_per_currency_and_state_every_excluded_row() -> None:
    positions = [
        _position(1, "Дверь", "шт", "25000", code="ДПМ-01/60"),
        _position(2, "Окно ПВХ ОП В2 1460х1460", "шт", "18500.5"),
        _position(3, "Анкер химический HIT-HY", "шт", "12.75", currency="EUR"),
        _position(4, "Профиль ПН 50х40", "м", "95"),
        _position(5, "Пена монтажная", "шт", "700"),
        _position(6, "Пена монтажная", "шт", "710"),
    ]
    rows = [
        _row("Дверь ДПМ-01/60 EI60", quantity="4", line=1),
        _row("Окно ПВХ ОП В2 1460х1460", quantity="12", line=2),
        _row("Анкер химический HIT-HY", quantity="200", line=3),
        _row("Профиль ПН 50х40", unit="м2", quantity="120", line=4),
        _row("Пена монтажная", quantity="3", line=5),
        _row("Кирпич", quantity="1 250", issue="ambiguous", line=6),
        _row("Не из прайса", quantity="1", line=7),
    ]
    outcome = match_specification(rows, positions)
    assert [(t.currency, t.amount, t.row_count) for t in outcome.totals] == [
        ("EUR", Decimal("2550.00"), 1),
        ("RUB", Decimal("322006.0"), 2),
    ]
    assert dict(outcome.excluded_by_reason) == {
        "no_position": 2, "unit_mismatch": 1, "ambiguous": 1,
    }
    assert dict(outcome.status_counts) == {"matched": 3, "ambiguous": 1, "unmatched": 3}
    contributing = sum(t.row_count for t in outcome.totals)
    assert contributing + sum(outcome.excluded_by_reason.values()) == len(rows)
    assert set(outcome.excluded_by_reason) <= set(EXCLUSION_REASONS)
    assert all(
        (match.amount is None) == (match.excluded_reason is not None) for match in outcome.matches
    )
    assert all(
        match.amount is None or match.status == STATUS_MATCHED for match in outcome.matches
    )


def test_amounts_are_exact_and_served_without_exponent_or_rounding() -> None:
    position = _position(1, "Плитка", "м2", "1234.567891")
    match, _ = _one(_row("Плитка", unit="м2", quantity="12,5"), position)
    assert match.amount == Decimal("15432.0986375")
    assert canonical_amount(match.amount) == "15432.0986375"
    assert canonical_amount(Decimal("1E+3")) == "1000"
    assert canonical_amount(Decimal("2550.00")) == "2550"


def test_matching_is_deterministic_and_independent_of_position_order() -> None:
    positions = [
        _position(1, "Пена монтажная", "шт", "700"),
        _position(2, "Окно ПВХ", "шт", "100"),
        _position(3, "Пена монтажная", "шт", "710"),
    ]
    rows = [_row("Пена монтажная", line=1), _row("Окно ПВХ", line=2)]
    forward = match_specification(rows, positions)
    backward = match_specification(rows, list(reversed(positions)))
    assert forward == backward


def test_extracted_rows_are_matched_end_to_end() -> None:
    page = (
        "Поз. Наименование Кол-во, шт. Примечание\n"
        "1 Металлический щит МЩ-1 12\n"
        "3 Рифленая сталь 690х395 t=4 мм 7\n"
    )
    rows = extract_specification(version_uid="ver_01M2545JSD15ETSNNV904XA001", pages={1: page}).rows
    positions = [
        _position(1, "Мет. щит МЩ-1", "шт.", "15000"),
        _position(2, "Рифлёная сталь 690x395 t=4 мм", "кг", "120"),
    ]
    first, second = match_specification(rows, positions).matches
    assert (first.status, first.amount) == (STATUS_MATCHED, Decimal("180000"))
    assert (second.status, second.reason) == (STATUS_UNMATCHED, "unit_mismatch")


@pytest.mark.parametrize(
    ("left", "right", "equal"),
    [
        ("м²", "м2", True), ("кв. м", "м2", True), ("шт.", "шт", True), ("п.м.", "м", True),
        ("упак.", "Упак", True), ("рулон", "м2", False), ("", None, True),
    ],
)
def test_unit_keys(left: str, right: str | None, equal: bool) -> None:
    assert (unit_key(left) == unit_key(right)) is equal


def test_a_row_unit_is_compared_through_the_same_key() -> None:
    row = replace(_row("Плитка", unit="м2"), unit_text="м²")
    match, _ = _one(row, _position(1, "Плитка", "кв.м", "100"))
    assert match.status == STATUS_MATCHED


def test_the_amount_guard_itself_refuses_another_unit_or_no_quantity() -> None:
    """``_contributes`` is the second barrier behind the unit filter; it must hold alone."""
    from auditmanager.optimisation import matching

    per_metre = _position(1, "Профиль", "м", "95")
    assert matching._contributes(_row("Профиль", unit="м", quantity="2"), per_metre) is True
    assert matching._contributes(_row("Профиль", unit="п.м", quantity="2"), per_metre) is True
    assert matching._contributes(_row("Профиль", unit="м2", quantity="2"), per_metre) is False
    assert matching._contributes(_row("Профиль", unit="м", quantity=None), per_metre) is False
    assert matching._contributes(_row("Профиль", unit=None, quantity="2"), per_metre) is False
    assert matching._contributes(_row("Профиль", unit="м", quantity="2"), None) is False


@pytest.mark.parametrize('source_unit,price_unit', [('п.м', 'м'), ('м', 'п.м'), ('пог. м', 'м'), ('м.п.', 'м')])
def test_running_metres_match_at_exact_factor_one(source_unit, price_unit) -> None:
    position = _position(1, 'Кабель ВВГ 3х2.5', price_unit, '95.125')
    row = _row('Кабель ВВГ 3х2.5', unit=source_unit, quantity='120.5')
    match, outcome = _one(row, position)
    assert match.status == STATUS_MATCHED
    assert match.amount == Decimal('11462.5625')
    assert outcome.totals[0].amount == match.amount
    assert row.unit == source_unit and position.unit == price_unit


def test_equivalent_metres_still_require_one_unambiguous_position() -> None:
    row = _row('Кабель ВВГ 3х2.5', unit='п.м', quantity='2')
    result = match_specification([row], [_position(1, 'Кабель ВВГ 3х2.5', 'м', '10'), _position(2, 'Кабель ВВГ 3х2.5', 'п.м', '9')])
    assert result.matches[0].status == STATUS_AMBIGUOUS
    assert result.matches[0].amount is None and result.totals == ()
