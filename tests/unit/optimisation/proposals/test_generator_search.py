"""`D-185` -- the analog search is price-ordered and stops early, and finds exactly what the full scan found.

``startOptimisationPass`` runs inside the request. Its cost is dominated by one loop: for each
matched row, the generator looked at **every position of the row's bucket** (same unit, currency and
head word), built a candidate for each one that qualified, sorted all of them and kept three. A price
list whose positions share one head word -- ``Профиль ...`` twenty thousand times -- made that
10 000 rows x 20 000 positions: measured at 173 s for the scan alone when nothing qualified and
well past the 290 s the web tier waits when everything did (``docs/program/API-FOLLOWUPS-01.md``).

The repair keeps every output byte and changes only how the three are found: a bucket holds only the
positions whose vendor is on the list, ordered by unit price; a row looks only at the strictly cheaper
prefix, one equal-price group at a time, and stops after the first group that completes three. This file
holds the two halves of that claim:

* **equality** -- on thousands of seeded inputs built to collide (few head words, few distinct prices,
  equal-price groups wider than the cut-off, unrelated vendors, prices equal as numbers but written with
  different scales), the proposals are the ones an independent full-scan transcription of the rules
  yields, in the same order, with the same basis and similarity;
* **work** -- for a row whose cheapest analogs qualify, the number of candidates built does not depend
  on how many cheaper positions there are.

The reference below is written from the module note's six rules and uses only the module's public
helpers (``head_word``, ``name_similarity``, ``code_family``, ``vendor_key``), not its private index.
"""

from __future__ import annotations

import random
from decimal import ROUND_DOWN, Decimal
from fractions import Fraction

import pytest

from auditmanager.optimisation.matching import match_specification, unit_key
from auditmanager.optimisation.proposals import generator
from auditmanager.optimisation.proposals.generator import (
    BASIS_CODE_FAMILY,
    BASIS_NAME_SIMILARITY,
    MAX_PROPOSALS_PER_ROW,
    NAME_SIMILARITY_THRESHOLD,
    code_family,
    generate_cheaper_analogs,
    head_word,
    name_similarity,
    vendor_key,
)
from auditmanager.optimisation.repository import PriceListPositionRecord
from auditmanager.optimisation.specification import SpecificationRow

HEADS = ("профиль", "балка", "узел")
WORDS = ("стальная", "двутавр", "20Б1", "оцинк", "10", "12", "ПК", "ДПМ", "крепёж")
VENDORS = ("Промет", "Кнауф Гипс", "ООО «Завод»", "Промет", "Кнауф Гипс", "ЖБИ-3", None)
LISTED = ("Промет", "Кнауф Гипс", "Завод")


def _position(
    index: int, name: str, price: str, *, unit: str = "шт", currency: str = "RUB",
    code: str | None = None, vendor: str | None = "Промет",
) -> PriceListPositionRecord:
    return PriceListPositionRecord(
        price_list_position_id=f"prp_{index:026d}",
        price_list_id="prl_01M2545JSD15ETSNNV904XA001",
        row_number=index + 1,
        code=code,
        name=name,
        mark=None,
        unit=unit,
        unit_price=Decimal(price),
        currency=currency,
        vendor=vendor,
        section_code=None,
    )


def _row(name: str, line: int) -> SpecificationRow:
    return SpecificationRow(
        row_id=f"sr-{line:032x}", page_number=1, sheet_label=None, line_start=line, line_end=line,
        table_ordinal=1, group=None, position=str(line), name=name, unit_text="шт", unit="шт",
        unit_source="column", quantity_text="3", quantity=Decimal(3), quantity_issue=None,
        mass_text=None, note=None,
    )


def _similarity_value(value: Fraction) -> Decimal:
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    return exact.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def full_scan(
    matched: PriceListPositionRecord, positions: tuple[PriceListPositionRecord, ...], allowed: frozenset[str]
) -> list[tuple[str, str, Decimal]]:
    """The six rules of the module note, applied to every position, sorted, cut: no index, no early exit."""
    head, family = head_word(matched.name), code_family(matched)
    found: list[tuple[PriceListPositionRecord, str, Fraction]] = []
    for other in positions:
        if other.price_list_position_id == matched.price_list_position_id:  # 1
            continue
        if unit_key(other.unit) != unit_key(matched.unit):  # 2
            continue
        if other.currency != matched.currency:  # 3
            continue
        if not other.unit_price < matched.unit_price:  # 4
            continue
        vendor = vendor_key(other.vendor)  # 5
        if vendor is None or vendor not in allowed:
            continue
        if head is None or head_word(other.name) != head:  # 6
            continue
        similarity = name_similarity(matched.name, other.name)
        if family is not None and family == code_family(other):
            basis = BASIS_CODE_FAMILY
        elif similarity >= NAME_SIMILARITY_THRESHOLD:
            basis = BASIS_NAME_SIMILARITY
        else:
            continue
        found.append((other, basis, similarity))
    found.sort(key=lambda item: (
        item[0].unit_price, -item[2], item[0].row_number, item[0].price_list_position_id
    ))
    return [
        (other.price_list_position_id, basis, _similarity_value(similarity))
        for other, basis, similarity in found[:MAX_PROPOSALS_PER_ROW]
    ]


def _compare(positions: tuple[PriceListPositionRecord, ...], rows: list[SpecificationRow], vendors) -> int:
    """Assert the generator's proposals equal the full scan's, row by row; return how many there were."""
    matches = match_specification(rows, positions).matches
    outcome = generate_cheaper_analogs(matches, positions, vendors)
    allowed = frozenset(key for key in (vendor_key(vendor) for vendor in vendors) if key)
    expected: list[tuple[str, str, str, Decimal]] = []
    for match in matches:
        if match.position is None or match.status != "matched":
            continue
        for found in full_scan(match.position, positions, allowed):
            expected.append((match.row.row_id, *found))
    actual = [
        (draft.row.row_id, draft.proposed.price_list_position_id, draft.analog_basis, draft.similarity)
        for draft in outcome.proposals
    ]
    assert actual == expected
    return len(actual)


# -- equality with the full scan --------------------------------------------------------------


def _random_case(seed: int) -> tuple[tuple[PriceListPositionRecord, ...], list[SpecificationRow], tuple[str, ...]]:
    rnd = random.Random(seed)

    def name(index: int) -> str:
        words = [rnd.choice(HEADS), *(rnd.choice(WORDS) for _ in range(rnd.randint(0, 3)))]
        if rnd.random() < 0.7:  # mostly unique, so most rows match exactly one position
            words.append(str(index))
        return " ".join(words)

    positions = tuple(
        _position(
            index,
            name(index),
            # Few distinct values, some equal as numbers and different in scale: wide equal-price groups.
            rnd.choice(("1", "2", "2.0", "2.00", "3", "5", "5", "5.0", "8", "13", "0.5")),
            unit=rnd.choice(("шт",) * 6 + ("м",)),
            currency=rnd.choice(("RUB",) * 5 + ("EUR",)),
            code=rnd.choice((None, None, f"ПК {rnd.randint(1, 4)}", f"ДП{rnd.randint(1, 3)}-{rnd.randint(1, 9)}")),
            vendor=rnd.choice(VENDORS),
        )
        for index in range(rnd.randint(1, 70))
    )
    rows = [_row(rnd.choice(positions).name, line) for line in range(1, rnd.randint(2, 40))]
    return positions, rows, tuple(rnd.sample(LISTED, rnd.randint(1, len(LISTED))))


def test_the_proposals_are_those_of_the_full_scan_on_inputs_built_to_collide() -> None:
    total = 0
    for seed in range(1500):
        positions, rows, vendors = _random_case(seed)
        total += _compare(positions, rows, vendors)
    # The inputs must exercise the search, not merely agree on emptiness.
    assert total > 3000, total


def _proposed(positions, row_name: str, vendors=LISTED) -> list[int]:
    matches = match_specification([_row(row_name, 1)], positions).matches
    outcome = generate_cheaper_analogs(matches, positions, vendors)
    return [draft.proposed.row_number for draft in outcome.proposals]


def test_an_equal_price_group_wider_than_the_cut_off_is_ordered_by_similarity_then_source_row() -> None:
    positions = (
        _position(1, "Профиль стальной ПН 100", "100"),
        _position(10, "Профиль стальной ПН 51", "50"),  # similarity 3/5
        _position(11, "Профиль стальной ПН 100 новый", "50"),  # 4/5
        _position(12, "Профиль стальной ПН 100 а", "50.00"),  # 4/5, the same price written differently
        _position(13, "Профиль стальной ПН 52", "50"),  # 3/5
        _position(14, "Профиль стальной ПН 100 новый", "50.0"),  # 4/5
    )
    # Five analogs at one price: the three kept are the most similar, ties by source row.
    assert _proposed(positions, "Профиль стальной ПН 100") == [12, 13, 15]
    assert _compare(positions, [_row("Профиль стальной ПН 100", 1)], LISTED) == MAX_PROPOSALS_PER_ROW


def test_a_cheaper_position_that_does_not_qualify_does_not_stop_the_search() -> None:
    positions = (
        _position(1, "Профиль стальной ПН", "100"),
        _position(2, "Профиль", "10", vendor="Чужой"),  # cheaper, but off the vendor list
        _position(3, "Профиль совсем иной товар здесь", "20"),  # cheaper, same head, too dissimilar
        _position(4, "Профиль стальной ПН 40", "30"),  # qualifies, but only after both
    )
    assert _proposed(positions, "Профиль стальной ПН") == [5]
    assert _compare(positions, [_row("Профиль стальной ПН", 1)], LISTED) == 1


def test_a_position_with_the_same_price_or_dearer_is_never_reached() -> None:
    positions = (
        _position(1, "Профиль стальной ПН", "100"),
        _position(2, "Профиль стальной ПН 7", "100.00"),
        _position(3, "Профиль стальной ПН 8", "101"),
        _position(4, "Профиль стальной ПН 9", "99.99"),
    )
    assert _proposed(positions, "Профиль стальной ПН") == [5]
    assert _compare(positions, [_row("Профиль стальной ПН", 1)], LISTED) == 1


def _wide_case(seed: int) -> tuple[tuple[PriceListPositionRecord, ...], list[SpecificationRow], tuple[str, ...]]:
    """A bucket of several hundred positions in which most names carry a word nobody else has.

    That is the shape in which the word, family and short-name lists are small against the cheaper
    prefix and a row is searched through them: ten per cent of the names are the head word alone or
    the head word and one number, a third carry one of forty code families, and the rest share at
    most one of fifty words with anybody.
    """
    rnd = random.Random(10_000 + seed)
    heads = ("профиль", "балка")
    vocabulary = tuple(f"сл{n}" for n in range(50))

    def name(index: int) -> str:
        kind = rnd.random()
        head = rnd.choice(heads)
        if kind < 0.05:
            return head
        if kind < 0.10:
            return f"{head} {index}"
        words = [head, str(index)]
        words += rnd.sample(vocabulary, rnd.randint(0, 2))
        return " ".join(words)

    positions = tuple(
        _position(
            index,
            name(index),
            rnd.choice(("1", "2", "2.0", "3", "5", "5.0", "8", "13", "21", "34")),
            code=rnd.choice((None,) * 7 + tuple(f"К{chr(65 + n % 26)}{chr(65 + n // 26)} {n}" for n in range(40))),
            vendor=rnd.choice(("Промет",) * 9 + ("Чужой",)),
        )
        for index in range(rnd.randint(250, 450))
    )
    rows = [_row(rnd.choice(positions).name, line) for line in range(1, 41)]
    return positions, rows, ("Промет",)


def test_the_proposals_are_those_of_the_full_scan_when_rows_are_searched_through_the_lists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    through_lists = {"rows": 0, "ranks": 0}
    original = generator._qualifying_ranks

    def spy(matched, bucket, end):
        result = original(matched, bucket, end)
        if result is not None:
            through_lists["rows"] += 1
            through_lists["ranks"] += len(result)
        return result

    monkeypatch.setattr(generator, "_qualifying_ranks", spy)
    total = 0
    for seed in range(60):
        positions, rows, vendors = _wide_case(seed)
        total += _compare(positions, rows, vendors)
    # The inputs must send rows through the lists, and the lists must find analogs there.
    assert through_lists["rows"] > 300, through_lists
    assert total > 300, total


def test_a_row_whose_cheaper_prefix_holds_nothing_in_common_is_not_walked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Names that differ by one number each (``Профиль 17``) share only the head word, which is below
    the threshold for two-word names: the lists are empty and the prefix is not walked."""
    reached: list[int | None] = []
    original = generator._qualifying_ranks

    def spy(matched, bucket, end):
        result = original(matched, bucket, end)
        reached.append(None if result is None else len(result))
        return result

    monkeypatch.setattr(generator, "_qualifying_ranks", spy)
    positions = tuple(_position(index, f"Профиль {index}", str(index + 1)) for index in range(2000))
    dearest = positions[-1]
    matches = match_specification([_row(dearest.name, 1)], positions).matches

    outcome = generate_cheaper_analogs(matches, positions, LISTED)

    assert outcome.proposals == ()
    assert reached == [0], f"{reached}: a prefix of 1999 positions with nothing in common was walked"
    assert full_scan(dearest, positions, frozenset(vendor_key(v) for v in LISTED)) == []


def _flat_case(seed: int) -> tuple[tuple[PriceListPositionRecord, ...], list[SpecificationRow], tuple[str, ...]]:
    """Equal-price groups of dozens of positions with every similarity from 1/2 to 1 and ties among them."""
    rnd = random.Random(20_000 + seed)
    vocabulary = tuple(f"сл{n}" for n in range(6))
    cheap = [
        _position(
            index,
            " ".join(("профиль", str(index % 3), *rnd.sample(vocabulary, rnd.randint(1, 4)))),
            rnd.choice(("1", "1.0", "2")),
            code=rnd.choice((None, None, None, f"КФ{rnd.randint(1, 2)} {index}")),
        )
        for index in range(rnd.randint(30, 90))
    ]
    dear = [
        _position(1000 + n, " ".join(("профиль", f"x{n}", *rnd.sample(vocabulary, rnd.randint(1, 4)))), "50",
                  code=rnd.choice((None, f"КФ{rnd.randint(1, 2)} {n}")))
        for n in range(8)
    ]
    positions = (*cheap, *dear)
    return positions, [_row(position.name, line) for line, position in enumerate(dear, start=1)], ("Промет",)


def test_the_proposals_are_those_of_the_full_scan_when_a_price_group_is_wider_than_the_cut_off() -> None:
    total = 0
    for seed in range(120):
        positions, rows, vendors = _flat_case(seed)
        total += _compare(positions, rows, vendors)
    assert total > 600, total


@pytest.mark.parametrize("mask_words", [2, 0], ids=["two words have a bit", "no word has a bit"])
def test_the_proposals_are_those_of_the_full_scan_whatever_words_the_masks_cover(
    monkeypatch: pytest.MonkeyPatch, mask_words: int
) -> None:
    """The names' masks cover the most frequent words of a bucket and the rest are compared as sets.
    With almost no word covered nearly all of every comparison is the set half; with all of them
    covered, none is (the other tests). Both must give the full scan's answer."""
    monkeypatch.setattr(generator, "_MASK_WORDS", mask_words)
    total = 0
    for seed in range(400):
        positions, rows, vendors = _random_case(seed)
        total += _compare(positions, rows, vendors)
    for seed in range(20):
        positions, rows, vendors = _wide_case(seed)
        total += _compare(positions, rows, vendors)
    for seed in range(40):
        positions, rows, vendors = _flat_case(seed)
        total += _compare(positions, rows, vendors)
    assert total > 1000, total


# -- the work does not grow with the cheaper positions ------------------------------------------


def test_a_row_whose_cheapest_analogs_qualify_builds_no_more_candidates_than_it_keeps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = {"count": 0}
    original = generator._Candidate

    def counting(*arguments, **keywords):
        built["count"] += 1
        return original(*arguments, **keywords)

    monkeypatch.setattr(generator, "_Candidate", counting)
    current = _position(0, "Профиль вариант 0", "100000")
    cheaper = [_position(index, f"Профиль вариант {index}", str(index)) for index in range(1, 400)]
    positions = (current, *cheaper)
    matches = match_specification([_row("Профиль вариант 0", 1)], positions).matches

    outcome = generate_cheaper_analogs(matches, positions, LISTED)

    assert [draft.proposed.row_number for draft in outcome.proposals] == [2, 3, 4]
    assert built["count"] <= MAX_PROPOSALS_PER_ROW, (
        f"{built['count']} candidates were built for a row that keeps {MAX_PROPOSALS_PER_ROW}: "
        "the search no longer stops after the cheapest analogs"
    )


def test_an_equal_price_group_of_two_thousand_analogs_builds_no_more_candidates_than_it_keeps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rows of a flat price list: one price, two thousand names alike. The group is read once and
    only the places it can fill are judged; the group is not turned into two thousand candidates."""
    built = {"count": 0}
    original = generator._Candidate

    def counting(*arguments, **keywords):
        built["count"] += 1
        return original(*arguments, **keywords)

    monkeypatch.setattr(generator, "_Candidate", counting)
    current = _position(0, "Профиль вариант 0", "5")
    flat = [_position(index, f"Профиль вариант {index}", "1") for index in range(1, 2001)]
    positions = (current, *flat)
    matches = match_specification([_row("Профиль вариант 0", 1)], positions).matches

    outcome = generate_cheaper_analogs(matches, positions, LISTED)

    # Equal similarity throughout, so the places go to the earliest source rows.
    assert [draft.proposed.row_number for draft in outcome.proposals] == [2, 3, 4]
    assert built["count"] <= MAX_PROPOSALS_PER_ROW, (
        f"{built['count']} candidates were built from one equal-price group for a row that keeps "
        f"{MAX_PROPOSALS_PER_ROW}"
    )


def test_a_group_whose_analogs_arrive_in_rising_similarity_keeps_only_the_places_it_can_fill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Four analogs of one price meeting a row in ascending similarity (1/2, 5/7, 6/7, 1): each beats
    the last kept one, so a group that is not cut to its places would hold four and judge four."""
    built = {"count": 0}
    original = generator._Candidate

    def counting(*arguments, **keywords):
        built["count"] += 1
        return original(*arguments, **keywords)

    monkeypatch.setattr(generator, "_Candidate", counting)
    positions = (
        _position(0, "Профиль альфа бета гамма дельта эпсилон", "5"),
        _position(1, "Профиль альфа бета гамма ипсилон дзета", "1"),  # 4 shared of 8
        _position(2, "Профиль альфа бета гамма дельта ипсилон", "1"),  # 5 shared of 7
        _position(3, "Профиль альфа бета гамма дельта эпсилон ипсилон", "1"),  # 6 shared of 7
        _position(4, "Профиль бета альфа гамма дельта эпсилон", "1"),  # the same words, another order
    )
    matches = match_specification([_row("Профиль альфа бета гамма дельта эпсилон", 1)], positions).matches

    outcome = generate_cheaper_analogs(matches, positions, LISTED)

    assert [draft.proposed.row_number for draft in outcome.proposals] == [5, 4, 3]
    assert built["count"] <= MAX_PROPOSALS_PER_ROW, built
    assert _compare(positions, [_row("Профиль альфа бета гамма дельта эпсилон", 1)], LISTED) == 3
