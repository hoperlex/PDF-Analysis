"""`W57B-NORMS-CATALOGUE-XLSX-01`: the catalogue's display name, rule by rule.

Every slug below is a real ``norm_document.slug`` of the 674-document W54 snapshot
(``ns_01M59N8QNBVN91ACA2HCE6VE74``), copied from the local stand by a read-only query,
except where a case says it is constructed. The expected strings are written out, never
computed with the code under test, and the stored projection a case compares against is the
search's own :func:`designation_of`.
"""

from __future__ import annotations

import pytest

from auditmanager.norms.catalogue import DisplayName, display_name
from auditmanager.norms.search import designation_of


@pytest.mark.parametrize(
    ("slug", "designation", "title"),
    [
        # The truncation the W54 stand report names: the split on `__` cut the edition note.
        (
            "Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)",
            "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)",
            None,
        ),
        # The file name was cut after a complete edition date: the note is closed.
        (
            "Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023",
            "Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)",
            None,
        ),
        # Cut inside the edition note: what is known is said, the rest is an ellipsis.
        (
            "Постановление_Правительства_РФ_от_04_05_2012_N_442_(ред__от",
            "Постановление Правительства РФ от 04.05.2012 N 442 (ред. …)",
            None,
        ),
        (
            "Постановление_Правительства_РФ_от_16_02_2008_N_87_(ред__от_2",
            "Постановление Правительства РФ от 16.02.2008 N 87 (ред. …)",
            None,
        ),
        (
            "Решение_Комиссии_Таможенного_союза_от_16_08_2011_N_768_(ред_",
            "Решение Комиссии Таможенного союза от 16.08.2011 N 768 (ред. …)",
            None,
        ),
        (
            "Приказ_Минстроя_России_от_19_12_2019_N_823_пр_(с_изм__от_22_",
            "Приказ Минстроя России от 19.12.2019 N 823 пр (с изм. …)",
            None,
        ),
        # An act's subject is its title, after the number and a closed edition note.
        (
            "Приказ_МЧС_РФ_от_25_03_2009_N_182_(ред__от_09_12_2010)_Об_у",
            "Приказ МЧС РФ от 25.03.2009 N 182 (ред. от 09.12.2010)",
            "Об у",
        ),
        (
            "Приказ_Минрегиона_России_от_05_07_2011_N_320_Об_утверждении",
            "Приказ Минрегиона России от 05.07.2011 N 320",
            "Об утверждении",
        ),
        (
            "Письмо_Минстроя_России_от_06_11_2019_N_39419-ОГ_08_О_возмож",
            "Письмо Минстроя России от 06.11.2019 N 39419-ОГ 08",
            "О возмож",
        ),
        # Dotted designation numbers after a document-type word.
        (
            "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные",
            "СП 54.13330.2022",
            "Свод правил. Здания жилые многоквартирные",
        ),
        (
            "ГОСТ_1759_5-87_(СТ_СЭВ_5958-87)__Гайки__Механические_свойст",
            "ГОСТ 1759.5-87 (СТ СЭВ 5958-87)",
            "Гайки. Механические свойст",
        ),
        ("ГОСТ_Р_2_105-2019__Национальный_стандарт_Российской_Федерац",
         "ГОСТ Р 2.105-2019", "Национальный стандарт Российской Федерац"),
        ("МДС_12-24_2006__Устройство_обычных,_декоративных_и_гидроизо",
         "МДС 12-24.2006", "Устройство обычных, декоративных и гидроизо"),
        ("ВСН_25-09_67-85__Ведомственные_строительные_нормы__Правила",
         "ВСН 25-09.67-85", "Ведомственные строительные нормы. Правила"),
        ("РД_34_21_122-87__Инструкция_по_устройству_молниезащиты_здан",
         "РД 34.21.122-87", "Инструкция по устройству молниезащиты здан"),
        # The asterisk of `2.01.07-85*` was written as `_`; it is not guessed back.
        ("СНиП_2_01_07-85___Строительные_нормы_и_правила__Нагрузки_и",
         "СНиП 2.01.07-85", "Строительные нормы и правила. Нагрузки и"),
        # A designation inside an act's name is repaired too.
        (
            "Изменение_N_3_к_СП_51_13330_2011_СНиП_23-03-2003_Защита_от",
            "Изменение N 3 к СП 51.13330.2011 СНиП 23-03-2003 Защита от",
            None,
        ),
        # Inside parentheses the lost character may have been a colon: left as spaces.
        (
            "ГОСТ_12_4_293-2015_(EN_136_1998)__Межгосударственный_станда",
            "ГОСТ 12.4.293-2015 (EN 136 1998)",
            "Межгосударственный станда",
        ),
        ("ГОСТ_4907-81", "ГОСТ 4907-81", None),
    ],
)
def test_real_slugs(slug: str, designation: str, title: str | None) -> None:
    name = display_name(slug)
    assert name == DisplayName(
        designation=designation, title=title, derived=designation != designation_of(slug)
    )


@pytest.mark.parametrize(
    "slug",
    [
        # A date cut short is not a date: nothing to derive, the stored text stands.
        "Градостроительный_кодекс_Российской_Федерации_от_29_12_200",
        # Already readable, or nothing a rule applies to.
        "ГОСТ_IEC_61439-1-2024__Межгосударственный_стандарт__Устройс",
        "Постановление_ФАС_Поволжского_округа_от_26.04.2011_по_делу_N_А55-12924_2010",
        "Здания_и_фрагменты_зданий__Метод_натурных_огневых_испытаний",
    ],
)
def test_underivable_designations_are_the_stored_projection_verbatim(slug: str) -> None:
    name = display_name(slug)
    assert name.designation == designation_of(slug)
    assert name.derived is False


@pytest.mark.parametrize(
    "slug",
    [
        # Constructed: an unclosed parenthesis that is not an edition note.
        "Приказ_МЧС_России_от_24_04_2013_N_288_(приложение",
        # Constructed: two unclosed parentheses.
        "Приказ_МЧС_России_от_24_04_2013_N_288_(ред_(от",
        # Constructed: a stray closing parenthesis.
        "Приказ_МЧС_России_от_24_04_2013_N_288)",
    ],
)
def test_an_unbalanced_designation_falls_back_whole(slug: str) -> None:
    """All or nothing: the date rule would apply, but the row is shown as stored."""
    name = display_name(slug)
    assert name.designation == designation_of(slug)
    assert name.derived is False


@pytest.mark.parametrize(
    ("slug", "designation"),
    [
        # Constructed: day 32 and month 13 are not dates.
        ("Приказ_МЧС_России_от_32_04_2013_N_1", "Приказ МЧС России от 32 04 2013 N 1"),
        ("Приказ_МЧС_России_от_12_13_2013_N_1", "Приказ МЧС России от 12 13 2013 N 1"),
        # Constructed: the date is a date only after `от`.
        ("Приказ_N_24_04_2013", "Приказ N 24 04 2013"),
    ],
)
def test_only_real_dates_after_ot_are_dotted(slug: str, designation: str) -> None:
    assert display_name(slug).designation == designation


def test_the_same_slug_gives_the_same_name() -> None:
    slug = "Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)"
    assert display_name(slug) == display_name(slug)


def test_the_name_is_never_empty() -> None:
    assert display_name("__").designation == designation_of("__")
