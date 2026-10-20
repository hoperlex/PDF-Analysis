"""`NORMS-DISPLAY-DESIGNATION-01`: the designation ``searchNorms`` and ``getNormDocument`` show.

The catalogue's derivation (`W57B-NORMS-CATALOGUE-XLSX-01`) now serves the search and the
document page too, through ``reader_designation``: the derived designation, except that one
longer than the sealed schemas allow (500 characters) is replaced by the stored projection
``designation_of`` so the answer always validates and nothing is resealed.

Every expected string is written out; none is computed with the code under test. The slugs
are real ``norm_document.slug`` values of the 674-document W54 snapshot (the ones
``test_display_name.py`` already uses) except where a case says it is constructed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import auditmanager.norms.catalogue as catalogue
from auditmanager.norms import public
from auditmanager.norms.search import (
    DESIGNATION_MAX_CHARACTERS,
    DisplayName,
    designation_of,
    display_name,
    reader_designation,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NORMS_SOURCE = REPOSITORY_ROOT / "src" / "auditmanager" / "norms"
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"

#: (slug, what the reader saw before this task, what the reader sees now)
REAL = [
    (
        "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные",
        "СП 54 13330 2022",
        "СП 54.13330.2022",
    ),
    (
        "ГОСТ_1759_5-87_(СТ_СЭВ_5958-87)__Гайки__Механические_свойст",
        "ГОСТ 1759 5-87 (СТ СЭВ 5958-87)",
        "ГОСТ 1759.5-87 (СТ СЭВ 5958-87)",
    ),
    (
        "ГОСТ_Р_2_105-2019__Национальный_стандарт_Российской_Федерац",
        "ГОСТ Р 2 105-2019",
        "ГОСТ Р 2.105-2019",
    ),
    (
        "Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)",
        "Приказ МЧС России от 24 04 2013 N 288 (ред",
        "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)",
    ),
    (
        "Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023",
        "Федеральный закон от 22 07 2008 N 123-ФЗ (ред",
        "Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)",
    ),
    (
        "Постановление_Правительства_РФ_от_04_05_2012_N_442_(ред__от",
        "Постановление Правительства РФ от 04 05 2012 N 442 (ред",
        "Постановление Правительства РФ от 04.05.2012 N 442 (ред. …)",
    ),
    (
        "Приказ_Минрегиона_России_от_05_07_2011_N_320_Об_утверждении",
        "Приказ Минрегиона России от 05 07 2011 N 320 Об утверждении",
        "Приказ Минрегиона России от 05.07.2011 N 320",
    ),
    (
        "МДС_12-24_2006__Устройство_обычных,_декоративных_и_гидроизо",
        "МДС 12-24 2006",
        "МДС 12-24.2006",
    ),
]

#: Nothing a rule applies to, or an unclosed parenthesis that is not an edition note: the
#: reader sees what the document page showed before this task.
UNDERIVABLE = [
    "Градостроительный_кодекс_Российской_Федерации_от_29_12_200",
    "ГОСТ_IEC_61439-1-2024__Межгосударственный_стандарт__Устройс",
    "Здания_и_фрагменты_зданий__Метод_натурных_огневых_испытаний",
    "ГОСТ_4907-81",
    # Constructed: an unclosed parenthesis that is not an edition note.
    "Приказ_МЧС_России_от_24_04_2013_N_288_(приложение",
]


@pytest.mark.parametrize(("slug", "before", "after"), REAL)
def test_the_reader_sees_the_readable_designation(slug: str, before: str, after: str) -> None:
    assert designation_of(slug) == before  # the stored projection is not touched
    assert reader_designation(slug) == after


@pytest.mark.parametrize("slug", UNDERIVABLE)
def test_what_no_rule_can_derive_is_the_stored_projection_verbatim(slug: str) -> None:
    assert reader_designation(slug) == designation_of(slug)


@pytest.mark.parametrize("slug", [slug for slug, _, _ in REAL] + UNDERIVABLE)
def test_search_and_catalogue_show_one_designation(slug: str) -> None:
    assert reader_designation(slug) == catalogue.display_name(slug).designation
    assert reader_designation(slug) == public.display_name(slug).designation


def test_there_is_one_derivation_not_a_copy() -> None:
    assert catalogue.display_name is display_name
    assert catalogue.DisplayName is DisplayName
    assert public.display_name is display_name
    assert display_name.__module__ == "auditmanager.norms.search.display"
    definitions = [
        path.relative_to(NORMS_SOURCE).as_posix()
        for path in sorted(NORMS_SOURCE.rglob("*.py"))
        if "def display_name(" in path.read_text(encoding="utf-8")
    ]
    assert definitions == ["search/display.py"]
    assert not (NORMS_SOURCE / "catalogue" / "designation.py").exists()


# --- the schema bound ----------------------------------------------------------------------


def test_the_bound_is_the_sealed_schemas_bound() -> None:
    schemas = json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"]
    bounds = {
        name: schemas[name]["properties"]["designation"]["maxLength"]
        for name in ("NormSearchHit", "NormDocument")
    }
    assert bounds == {"NormSearchHit": 500, "NormDocument": 500}
    assert DESIGNATION_MAX_CHARACTERS == 500


def _cut_edition_slug(filler: int) -> str:
    """Constructed: an edition note cut after ``(ред`` is shown as ``(ред. …)``, which is
    nine characters after the filler (a space, ``(ред. …)``); the stored text keeps ``(ред``,
    five. The slug column allows 500 characters."""
    return "Б" * filler + "_(ред"


def test_a_derivation_of_exactly_the_bound_is_shown() -> None:
    slug = _cut_edition_slug(491)
    shown = reader_designation(slug)
    assert shown == "Б" * 491 + " (ред. …)"
    assert len(shown) == 500 == DESIGNATION_MAX_CHARACTERS


def test_a_derivation_over_the_bound_is_the_stored_projection() -> None:
    slug = _cut_edition_slug(492)
    assert display_name(slug).designation == "Б" * 492 + " (ред. …)"  # 501 characters
    shown = reader_designation(slug)
    assert shown == "Б" * 492 + " (ред"
    assert shown == designation_of(slug)
    assert len(shown) <= DESIGNATION_MAX_CHARACTERS


def test_the_stored_projection_always_fits_a_slug_the_column_allows() -> None:
    # `ck_norm_document_slug` allows 500 characters and the projection is a prefix of the slug.
    slug = _cut_edition_slug(495)
    assert len(slug) == 500
    assert len(reader_designation(slug)) <= DESIGNATION_MAX_CHARACTERS
