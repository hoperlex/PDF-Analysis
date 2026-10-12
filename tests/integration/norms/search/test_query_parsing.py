"""How a search text splits into a designation, a clause and words -- without a database.

`W55A-SEARCH-01` (`W55-PLAN.md` section A3.4). The database owns the match
(``norm_designation_tokens`` on both sides); this module owns where the designation, the
clause and the words begin and end, and the fold it uses to recognise a document-type word.
Two properties are checked against migration ``0020`` itself rather than against this
package: the fold is the same character map, and a parsed designation, tokenised the way the
SQL function tokenises it, matches the leading tokens of ``СП_54_…`` and never ``СП_542_…``.
The database half of the same claims is ``test_search_window.py``.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.norms.search.query import (
    DESIGNATION_TYPES,
    FOLD_FROM,
    FOLD_TO,
    ParsedQuery,
    designation_of,
    fold,
    parse_query,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = REPOSITORY_ROOT / "db/migrations/versions/20261012_0020_norms_search.py"

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP542 = "СП_542_1325800_2024__Свод_правил__Защитные_сооружения"
GOST_10140 = "ГОСТ_10140-2003__Межгосударственный_стандарт__Плиты"
GOST_R_ISO = "ГОСТ_Р_ИСО_17637-2024__Национальный_стандарт"
GOST_2_305 = "ГОСТ_2_305-2008__Межгосударственный_стандарт__Единая_система"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("w55a_search_0020", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sql_tokens(value: str) -> list[str]:
    """``norm_designation_tokens`` restated from the migration's own tables."""
    module = _migration()
    head = value.split("__", 1)[0]
    folded = head.translate(str.maketrans(module.FOLD_FROM, module.FOLD_TO))
    return [token for token in re.split(r"[ ._-]+", folded) if token]


def _finds(q: str, slug: str) -> bool:
    designation = parse_query(q).designation
    assert designation is not None, q
    wanted = _sql_tokens(designation)
    return bool(wanted) and _sql_tokens(slug)[: len(wanted)] == wanted


def test_the_fold_is_the_migrations_character_map() -> None:
    module = _migration()
    assert (FOLD_FROM, FOLD_TO) == (module.FOLD_FROM, module.FOLD_TO)
    assert fold("CП ГОСТ Ёж") == "сп гост еж"


def test_every_designation_type_is_folded() -> None:
    assert all(fold(word) == word for word in DESIGNATION_TYPES)
    assert {"гост", "сп", "снип", "всн", "мдс", "рд", "пэу"} <= DESIGNATION_TYPES


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("СП 54", ParsedQuery("СП 54", None, None)),
        ("СП 54 жилые здания", ParsedQuery("СП 54", None, "жилые здания")),
        ("жилые здания СП 54", ParsedQuery("СП 54", None, "жилые здания")),
        ("п. 7.1.4", ParsedQuery(None, "7.1.4", None)),
        ("п.7.1.", ParsedQuery(None, "7.1", None)),
        ("пункт 5 требования", ParsedQuery(None, "5", "требования")),
        ("СП 54 п. 7.1 лестницы", ParsedQuery("СП 54", "7.1", "лестницы")),
        ("ГОСТ Р 52085 опалубка", ParsedQuery("ГОСТ Р 52085", None, "опалубка")),
        ("ГОСТ Р ИСО 17637", ParsedQuery("ГОСТ Р ИСО 17637", None, None)),
        ("ГОСТ_10140-2003", ParsedQuery("ГОСТ_10140-2003", None, None)),
        ("СНиП 2.01.07-85 нагрузки", ParsedQuery("СНиП 2.01.07-85", None, "нагрузки")),
        ("CП 54", ParsedQuery("CП 54", None, None)),
        ("бетон 25 мм", ParsedQuery(None, None, "бетон 25 мм")),
        ("ГОСТ опалубка", ParsedQuery(None, None, "ГОСТ опалубка")),
        ("здания", ParsedQuery(None, None, "здания")),
        ("СП 54.13330.2022", ParsedQuery("СП 54.13330.2022", None, None)),
    ],
)
def test_a_query_splits_into_its_parts(q: str, expected: ParsedQuery) -> None:
    assert parse_query(q) == expected


def test_only_words_are_ranked() -> None:
    assert parse_query("здания").ranked
    assert parse_query("СП 54 здания").ranked
    assert not parse_query("СП 54").ranked
    assert not parse_query("СП 54 п. 5").ranked


def test_the_clause_is_not_read_inside_a_word() -> None:
    """``СП 54``: the ``П`` follows ``С``, so it opens no clause; ``ПБ 01`` neither."""
    assert parse_query("СП 54").clause is None
    assert parse_query("ППБ 01-03").clause is None
    assert parse_query("ППБ 01-03").designation == "ППБ 01-03"


def test_sp_54_finds_sp_54_and_never_sp_542() -> None:
    assert _finds("СП 54", SP54)
    assert not _finds("СП 54", SP542)
    assert _finds("СП 542", SP542)
    assert not _finds("СП 542", SP54)
    assert _finds("СП 54.13330", SP54)


def test_gost_lookup_by_its_leading_tokens() -> None:
    assert _finds("ГОСТ 10140", GOST_10140)
    assert not _finds("ГОСТ 1014", GOST_10140)
    assert _finds("ГОСТ Р ИСО 17637", GOST_R_ISO)
    assert _finds("ГОСТ 2.305", GOST_2_305)
    assert _finds("ГОСТ_10140-2003", GOST_10140)


def test_homoglyphs_and_case_find_the_same_document() -> None:
    for typed in ("CП 54", "сп 54", "Cп 54", "сП-54", "СП_54"):
        assert _finds(typed, SP54), typed
    for typed in ("ГOCT 10140", "гост 10140", "rOCT 10140"):
        parsed = parse_query(typed)
        if typed.startswith("r"):
            # ``r`` is no homoglyph of ``г``: not a designation, so words.
            assert parsed.designation is None, typed
        else:
            assert _finds(typed, GOST_10140), typed


def test_the_designation_a_reader_sees() -> None:
    assert designation_of(SP54) == "СП 54 13330 2022"
    assert designation_of(GOST_10140) == "ГОСТ 10140-2003"
    assert designation_of("Приказ_МЧС_России_от_20.07.2020_N_539") == (
        "Приказ МЧС России от 20.07.2020 N 539"
    )
