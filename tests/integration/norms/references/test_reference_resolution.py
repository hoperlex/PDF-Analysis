"""W57b reference extraction and catalogue outcomes stay deterministic."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from auditmanager.norms.references.families import parse_designation
from auditmanager.norms.references.resolution import (
    ABSENT,
    NEWER,
    OLDER,
    PRESENT,
    UNPARSED,
    CatalogueEntry,
    PinnedCatalogue,
    ReferenceRefused,
    TextPage,
    extract_references,
    resolve_references,
)
from auditmanager.norms.references.tokens import (
    FOLD_FROM,
    FOLD_TO,
    fold,
    sql_designation_tokens,
    text_designation_tokens,
)


SNAPSHOT = "ns_" + "0" * 26


def _document(number: int, slug: str) -> CatalogueEntry:
    return CatalogueEntry(f"ndoc_{number}", slug, sql_designation_tokens(slug))


def _catalogue(*slugs: str) -> PinnedCatalogue:
    return PinnedCatalogue(SNAPSHOT, tuple(_document(i, slug) for i, slug in enumerate(slugs, 1)))


def _resolve(text: str, catalogue: PinnedCatalogue):
    return resolve_references(
        extraction=extract_references((TextPage("1", text),)),
        catalogue=catalogue,
        pinned_snapshot_id=SNAPSHOT,
    )


@pytest.mark.parametrize(
    ("designation", "family", "base", "edition", "amendment"),
    [
        ("СП 54.13330.2022", "сп", ("54", "13330"), 2022, None),
        ("ГОСТ 21.101-2020", "гост", ("21", "101"), 2020, None),
        ("ГОСТ Р 57795-2017", "гост р", ("57795",), 2017, None),
        ("ГОСТ IEC 60331-1-2021", fold("ГОСТ IEC"), ("60331", "1"), 2021, None),
        ("ГОСТ ISO 3506-1-2014", fold("ГОСТ ISO"), ("3506", "1"), 2014, None),
        ("ГОСТ Р ИСО 17637-2024", "гост р исо", ("17637",), 2024, None),
        ("ГОСТ Р МЭК 60204-1-2007", "гост р мэк", ("60204", "1"), 2007, None),
        ("СНиП 31-01-2003", "снип", ("31", "01"), 2003, None),
        ("СанПиН 1.2.3685-21", "санпин", ("1", "2", "3685"), 2021, None),
        ("ВСН 01-89", "всн", ("01",), 1989, None),
        ("123-ФЗ", "фз", ("123",), None, None),
        ("ФЗ-123", "фз", ("123",), None, None),
        ("Федеральный закон № 123-ФЗ", "фз", ("123",), None, None),
        ("ПП РФ № 87", "пп рф", ("87",), None, None),
        ("Постановление Правительства РФ № 87", "пп рф", ("87",), None, None),
        ("Изменение N 3 к СП 51.13330.2011", "сп", ("51", "13330"), 2011, 3),
    ],
)
def test_family_vocabulary(designation, family, base, edition, amendment) -> None:
    parsed = parse_designation(designation)
    assert parsed is not None
    assert (parsed.family, parsed.base, parsed.edition, parsed.amendment_number) == (
        family, base, edition, amendment
    )


def test_python_fold_tables_are_exact_migration_0020_tables() -> None:
    root = Path(__file__).resolve().parents[4]
    migration = runpy.run_path(
        str(root / "db/migrations/versions/20261012_0020_norms_search.py")
    )
    assert (FOLD_FROM, FOLD_TO) == (migration["FOLD_FROM"], migration["FOLD_TO"])
    assert sql_designation_tokens("CП_54.13330.2022__текст") == (
        "сп", "54", "13330", "2022"
    )
    assert text_designation_tokens("С\u00a0П 54.13330.2022") != sql_designation_tokens(
        "С\u00a0П 54.13330.2022"
    )
    assert text_designation_tokens("ГОСТ\u00a021.101—2020") == (
        "гост", "21", "101", "2020"
    )


def test_extract_keeps_raw_offsets_and_unread_page_status() -> None:
    text = "Согласно CП\u00a054.13330.2022, ГОСТ\u00a021.101—2020 и ГОСТ IEC 60331-1-2021."
    extracted = extract_references((TextPage("A", text), TextPage("B", None)))
    assert extracted.unread_pages == ("B",)
    assert len(extracted.occurrences) == 3
    assert all(text[item.start:item.end] == item.raw_text for item in extracted.occurrences)


def test_gost_subseries_stays_distinct_from_numeric_gost() -> None:
    catalogue = _catalogue("ГОСТ_IEC_60331-1-2021", "ГОСТ_60331-1-2024")
    report = _resolve("ГОСТ IEC 60331-1-2021", catalogue)
    assert len(report.references) == 1
    assert report.references[0].outcome == PRESENT
    assert report.references[0].matched_document_id == "ndoc_1"


def test_newest_edition_wins_same_and_amendment_is_not_an_edition() -> None:
    catalogue = _catalogue(
        "СП_54.13330.2022", "СП_54.13330.2024",
        "Изменение_N_3_к_СП_54.13330.2022",
    )
    report = _resolve("СП 54.13330.2022; Изменение N 3 к СП 54.13330.2022", catalogue)
    assert [ref.outcome for ref in report.references] == [NEWER, NEWER]
    assert report.references[0].matched_designation == "СП 54.13330.2024"
    assert report.references[0].observation_text == (
        "Проект ссылается на СП 54.13330.2022; "
        "в корпусе есть более новая редакция: СП 54.13330.2024"
    )
    assert report.references[1].matched_document_id == "ndoc_2"


def test_amendment_matches_exact_amendment_when_no_newer_base_exists() -> None:
    report = _resolve(
        "Изменение N 3 к СП 51.13330.2011",
        _catalogue("СП_51.13330.2011", "Изменение_N_3_к_СП_51.13330.2011"),
    )
    assert report.references[0].outcome == PRESENT
    assert report.references[0].matched_document_id == "ndoc_2"


def test_older_absent_unparsed_and_law_number_outcomes() -> None:
    catalogue = _catalogue("ГОСТ_21.101-2020", "123-ФЗ")
    report = _resolve(
        "ГОСТ 21.101-2024; СП 54.13330.2022; СП 2.13130; ФЗ-123", catalogue
    )
    assert [ref.outcome for ref in report.references] == [OLDER, ABSENT, UNPARSED, PRESENT]
    assert all(ref.observation_text is None for ref in report.references)


def test_catalogue_mismatch_and_unlisted_slug_are_refused() -> None:
    extraction = extract_references((TextPage("1", "СП 54.13330.2022"),))
    with pytest.raises(ReferenceRefused, match="snapshot differs"):
        resolve_references(
            extraction=extraction,
            catalogue=PinnedCatalogue("ns_" + "1" * 26, ()),
            pinned_snapshot_id=SNAPSHOT,
        )
    with pytest.raises(ReferenceRefused, match="unlisted unparsed"):
        resolve_references(
            extraction=extraction,
            catalogue=_catalogue("неизвестный_документ"),
            pinned_snapshot_id=SNAPSHOT,
        )
    mismatched = PinnedCatalogue(
        SNAPSHOT, (CatalogueEntry("ndoc_1", "СП_54.13330.2022", ("wrong",)),)
    )
    with pytest.raises(ReferenceRefused, match="tokens mismatch"):
        resolve_references(
            extraction=extraction, catalogue=mismatched,
            pinned_snapshot_id=SNAPSHOT,
        )
