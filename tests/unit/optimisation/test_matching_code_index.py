"""`D-185` -- the matcher finds a code by its whole token sequence and gets the same positions.

A price list may carry thousands of codes that open with one token (``ПК 60-12-8``, ``ПК 63-15-8``,
...), and a specification row that names that token used to be compared with every one of them: 10 000
rows against 20 000 codes was 23 s of the request on the lane host (``docs/program/API-FOLLOWUPS-01.md``).
The index now keeps, under each first token, the codes by their whole token sequence and the lengths
those sequences have, so a row asks one dictionary per distinct length.

Two claims, both here: the positions found are exactly those a naive scan of every code finds (same
set, same basis -- a position matched by its code and by its mark is a ``code`` match -- same order);
and a row naming a token shared by two thousand codes makes as many lookups as the codes have distinct
lengths, not two thousand.
"""

from __future__ import annotations

import random
from decimal import Decimal

from auditmanager.optimisation import matching
from auditmanager.optimisation.matching import BASIS_CODE, BASIS_MARK
from auditmanager.optimisation.repository import PriceListPositionRecord

CODES = (
    "ПК 60-12", "ПК 63-15", "ПК 60-12-8", "ДПМ-01/60", "ДПМ-01/60 EI60", "HIT-HY 200", "HIT HY 200",
    "ГОСТ 123456", "ABC 12345", "ABC 12345 X", "12345678", "Z-9 100 200", "ПК 60", "Ду 50", "Ду 50 PN16",
)
WORDS = ("Плита", "Дверь", "Анкер", "Профиль", "EI60", "шт", "Ду", "50")


def _position(index: int, code: str | None, mark: str | None) -> PriceListPositionRecord:
    return PriceListPositionRecord(
        price_list_position_id=f"prp_{index:026d}", price_list_id="prl_01M2545JSD15ETSNNV904XA001",
        row_number=index + 1, code=code, name=f"Изделие {index}", mark=mark, unit="шт",
        unit_price=Decimal(index + 1), currency="RUB", vendor=None, section_code=None,
    )


def naive(positions, text):
    """Every code and mark tried against every window of the row: no index."""
    tokens = matching._code_tokens(text)
    found = {}
    for position in positions:
        for basis, value in ((BASIS_CODE, position.code), (BASIS_MARK, position.mark)):
            code = matching._specific_code(value)
            if code is None:
                continue
            if any(tokens[at : at + len(code)] == code for at in range(len(tokens))):
                identity = position.price_list_position_id
                if identity not in found or basis == BASIS_CODE:
                    found[identity] = (position, basis)
    return sorted(found.values(), key=lambda pair: pair[0].row_number)


def test_the_positions_found_by_token_sequence_are_those_a_naive_scan_finds() -> None:
    found = 0
    for seed in range(1500):
        rnd = random.Random(seed)
        positions = [
            _position(index, rnd.choice((None, *CODES)), rnd.choice((None, None, *CODES)))
            for index in range(rnd.randint(1, 40))
        ]
        index = matching._PriceIndex(positions)
        for _ in range(8):
            text = " ".join(rnd.choice(CODES + WORDS) for _ in range(rnd.randint(1, 6)))
            expected = naive(positions, text)
            assert index.by_code(text) == expected, (seed, text)
            found += len(expected)
    assert found > 3000, "the inputs must find codes, not merely agree on finding none"


class _Counting(dict):
    gets = 0

    def get(self, key, default=None):  # type: ignore[override]
        type(self).gets += 1
        return super().get(key, default)


def test_a_row_naming_a_token_shared_by_two_thousand_codes_asks_once_per_length() -> None:
    positions = [_position(index, f"ПК {10_000 + index}", None) for index in range(2000)]
    index = matching._PriceIndex(positions)
    assert index.code_lengths == {"пк": (2,)}
    index.codes["пк"] = _Counting(index.codes["пк"])
    _Counting.gets = 0

    found = index.by_code("Плита ПК 10042")

    assert [position.row_number for position, _ in found] == [43]
    assert _Counting.gets == 1, (
        f"{_Counting.gets} lookups for a token shared by 2000 codes of one length: "
        "the row was compared with the codes one by one"
    )
