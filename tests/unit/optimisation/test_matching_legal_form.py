"""`SPEC-TABLE-RECORDING-01` part 1: a vendor's legal form is optional on one side, never contradictory.

Container-free. The name tier of the matcher compares the row's description with a position's
name followed by any combination of mark, code and vendor. A specification writes its
manufacturer with a legal form (``ООО «Промет»``) where a price list often writes ``Промет``,
or the other way round, and a text layer runs the cells together. When the exact comparison
finds nothing, the legal form is dropped on the side that has one -- the row's
``manufacturer`` (set by the extractor from a legal form on) or the position's vendor -- and
only against a side that has none. ``ООО`` and ``ЗАО`` are two different legal forms and never
equal. The exact tier stays first and unchanged.
"""

from __future__ import annotations

from decimal import Decimal

from auditmanager.optimisation.matching import (
    BASIS_NAME,
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    STATUS_UNMATCHED,
    match_specification,
)
from auditmanager.optimisation.repository import PriceListPositionRecord
from auditmanager.optimisation.specification import SpecificationRow, extract_specification

PRICE_LIST = "prl_01M2545JSD15ETSNNV904XA001"


def _position(number: int, name: str, price: str, *, vendor: str | None, mark: str | None = None):
    return PriceListPositionRecord(
        price_list_position_id=f"prp_01M2545JSD15ETSNNV904X{number:03d}",
        price_list_id=PRICE_LIST,
        row_number=number,
        code=None,
        name=name,
        mark=mark,
        unit="шт",
        unit_price=Decimal(price),
        currency="RUB",
        vendor=vendor,
        section_code=None,
    )


def _row(name: str, *, manufacturer: str | None) -> SpecificationRow:
    return SpecificationRow(
        row_id=f"sr-{1:032x}",
        page_number=1,
        sheet_label=None,
        line_start=1,
        line_end=1,
        table_ordinal=1,
        group=None,
        position="1",
        name=name,
        unit_text="шт",
        unit="шт",
        unit_source="column",
        quantity_text="4",
        quantity=Decimal("4"),
        quantity_issue=None,
        mass_text=None,
        note=None,
        manufacturer=manufacturer,
    )


def _match(row: SpecificationRow, *positions: PriceListPositionRecord):
    (match,) = match_specification([row], positions).matches
    return match


def test_a_manufacturer_with_a_legal_form_matches_a_vendor_without_one() -> None:
    door = _position(1, "Дверь противопожарная", "25000", vendor="Промет")
    row = _row("Дверь противопожарная ООО «Промет»", manufacturer="ООО «Промет»")
    match = _match(row, door)
    assert (match.status, match.basis, match.position, match.amount) == (
        STATUS_MATCHED, BASIS_NAME, door, Decimal("100000"),
    )


def test_a_manufacturer_without_a_legal_form_matches_a_vendor_with_one() -> None:
    door = _position(1, "Дверь противопожарная", "25000", vendor="ООО «Промет»")
    row = _row("Дверь противопожарная Промет", manufacturer=None)
    match = _match(row, door)
    assert (match.status, match.basis, match.position) == (STATUS_MATCHED, BASIS_NAME, door)


def test_with_mark_and_code_in_front_of_the_vendor() -> None:
    door = _position(1, "Дверь противопожарная", "25000", vendor="Промет", mark="Д1")
    row = _row("Дверь противопожарная Д1 АО Промет", manufacturer="АО Промет")
    assert _match(row, door).position == door


def test_two_different_legal_forms_are_never_equal() -> None:
    door = _position(1, "Дверь противопожарная", "25000", vendor="ЗАО «Промет»")
    row = _row("Дверь противопожарная ООО «Промет»", manufacturer="ООО «Промет»")
    match = _match(row, door)
    assert (match.status, match.reason, match.position) == (STATUS_UNMATCHED, "no_position", None)


def test_the_exact_tier_answers_first_and_is_not_made_ambiguous_by_the_loose_one() -> None:
    exact = _position(1, "Дверь противопожарная", "25000", vendor="ООО «Промет»")
    loose = _position(2, "Дверь противопожарная", "24000", vendor="Промет")
    row = _row("Дверь противопожарная ООО «Промет»", manufacturer="ООО «Промет»")
    match = _match(row, exact, loose)
    assert (match.status, match.position) == (STATUS_MATCHED, exact)


def test_the_loose_tier_can_still_be_a_tie() -> None:
    first = _position(1, "Дверь противопожарная", "25000", vendor="Промет")
    second = _position(2, "Дверь противопожарная", "24000", vendor="Промет")
    row = _row("Дверь противопожарная ООО «Промет»", manufacturer="ООО «Промет»")
    match = _match(row, first, second)
    assert (match.status, match.reason, match.position) == (
        STATUS_AMBIGUOUS, "several_positions", None,
    )


def test_a_different_vendor_name_is_not_a_match() -> None:
    door = _position(1, "Дверь противопожарная", "25000", vendor="Север")
    row = _row("Дверь противопожарная ООО «Промет»", manufacturer="ООО «Промет»")
    assert _match(row, door).status == STATUS_UNMATCHED


def test_an_extracted_row_carries_the_manufacturer_the_matcher_drops_the_legal_form_from() -> None:
    page = (
        "Поз. Наименование Тип, марка Завод-изготовитель Ед. изм. Кол.\n"
        "1 Дверь противопожарная ДПМ-01/60 ООО «Промет» шт. 4\n"
    )
    result = extract_specification(version_uid="ver_01M2545JSD15ETSNNV904XA001", pages={1: page})
    (row,) = result.rows
    assert row.manufacturer == "ООО «Промет»"
    door = _position(1, "Дверь противопожарная ДПМ-01/60", "25000", vendor="Промет")
    assert _match(row, door).position == door
