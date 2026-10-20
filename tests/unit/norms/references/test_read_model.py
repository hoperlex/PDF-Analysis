"""`NORM-REFS-RUN-01`: the per-request read model of the norms a text cites.

Container-free, on recorded page text and a small seeded catalogue. These tests pin what the
*screen's* model promises on top of the unchanged W57b resolver, by the outcome rules the
plan fixes (`W57-PLAN.md` B3.2-B3.3): five outcomes; the newest edition wins (and wins over
the cited edition being present); an amendment is never an edition; both word orders of a
federal law and of a government act are one citation; at most ten retained occurrences with
the true count; pages with no text layer are listed, never read as empty; and the catalogue
slugs the family parser cannot read are listed explicitly.
"""

from __future__ import annotations

import pytest

from auditmanager.norms.references import read_model as module
from auditmanager.norms.references.read_model import (
    MAX_CITED_NORMS,
    OUTCOME_CODES,
    OUTCOME_ORDER,
    TooManyCitations,
    build_reference_read_model,
)
from auditmanager.norms.references.resolution import (
    MAX_EVIDENCE_OCCURRENCES,
    OUTCOMES,
    CatalogueEntry,
    PinnedCatalogue,
    ReferenceRefused,
)
from auditmanager.norms.references.snapshot_catalogue import catalogue_from_rows
from auditmanager.norms.references.tokens import sql_designation_tokens

SNAPSHOT = "ns_" + "0" * 26

SP54_2011 = "СП_54_13330_2011__Свод_правил__Здания_жилые_многоквартирные"
SP54_2022 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP54_2024 = "СП_54_13330_2024__Свод_правил__Здания_жилые_многоквартирные"
GOST_21_101 = "ГОСТ_21_101-2020__Система_проектной_документации"
SNIP_31 = "СНиП_31-01-2003__Здания_жилые_многоквартирные"
SP51_BASE = "СП_51_13330_2011__Свод_правил__Защита_от_шума"
SP51_AMEND = "Изменение_N_1_к_СП_51_13330_2011"
LAW_123 = "Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023)"
ACT_87 = "Постановление_Правительства_РФ_от_16_02_2008_N_87__О_составе_разделов"
MDS = "МДС_12-24_2006__Устройство_обычных"
ORDER = "Приказ_МЧС_России_от_19_03_2020_N_194"

FULL = (
    SP54_2011, SP54_2022, SP54_2024, GOST_21_101, SNIP_31, SP51_BASE, SP51_AMEND, LAW_123,
    ACT_87, MDS, ORDER,
)


def _catalogue(*slugs: str) -> PinnedCatalogue:
    rows = [
        {
            "norm_document_id": f"ndoc_{number:026d}",
            "slug": slug,
            "designation_tokens": list(sql_designation_tokens(slug)),
        }
        for number, slug in enumerate(slugs, 1)
    ]
    return catalogue_from_rows(snapshot_id=SNAPSHOT, declared_count=len(rows), rows=rows)


def _model(pages: dict[int, str], *slugs: str):
    return build_reference_read_model(
        pages=pages, catalogue=_catalogue(*(slugs or FULL)), pinned_snapshot_id=SNAPSHOT
    )


def _by_cited(model) -> dict[str, object]:
    return {item.cited: item for item in model.items}


def _outcome(text: str, *slugs: str):
    items = _model({1: text}, *slugs).items
    assert len(items) == 1, items
    return items[0]


# --- the five outcomes, with pages, counts and the matched norm ---------------------------

RECORDED = {
    1: (
        "Проект разработан в соответствии с СП 54.13330.2024, ГОСТ 21.101-2020 и "
        "СП 54.13330.2011. Класс опасности по ГОСТ Р 99999-2020 не установлен."
    ),
    2: "",
    3: "Шум по СП 54.13330. Огнестойкость по СНиП 31-01-2012 и СП 54.13330.2022.",
}


def test_the_recorded_text_resolves_to_all_five_outcomes_with_counts() -> None:
    model = _model(RECORDED)
    items = _by_cited(model)

    assert [(i.cited, i.outcome) for i in model.items] == [
        ("СП 54.13330.2024", "in_corpus"),
        ("ГОСТ 21.101-2020", "in_corpus"),
        ("СП 54.13330.2011", "newer_edition"),
        ("ГОСТ Р 99999-2020", "not_in_corpus"),
        ("СП 54.13330", "not_recognised"),
        ("СНиП 31-01-2012", "older_edition_only"),
        ("СП 54.13330.2022", "newer_edition"),
    ]
    assert dict(model.counts) == {
        "in_corpus": 2, "newer_edition": 2, "older_edition_only": 1,
        "not_in_corpus": 1, "not_recognised": 1,
    }
    assert tuple(model.counts) == OUTCOME_ORDER
    assert model.occurrence_count == 7
    assert (model.page_count, model.unread_pages) == (3, (2,))
    assert (model.norms_snapshot_id, model.snapshot_document_count) == (SNAPSHOT, len(FULL))

    newer = items["СП 54.13330.2011"]
    assert newer.matched_designation == "СП 54.13330.2024"
    assert newer.matched_document_id == f"ndoc_{FULL.index(SP54_2024) + 1:026d}"
    assert newer.matched_title == "Свод правил. Здания жилые многоквартирные"
    older = items["СНиП 31-01-2012"]
    assert older.matched_designation == "СНиП 31-01-2003"
    for missing in ("ГОСТ Р 99999-2020", "СП 54.13330"):
        assert (items[missing].matched_document_id, items[missing].matched_designation,
                items[missing].matched_title) == (None, None, None)


def test_every_anchor_names_its_page_and_quotes_its_text() -> None:
    model = _model(RECORDED)

    for item in model.items:
        for anchor in item.anchors:
            assert RECORDED[anchor.page_number][anchor.char_start:anchor.char_end] == anchor.quote
    assert [(i.cited, [a.page_number for a in i.anchors]) for i in model.items] == [
        ("СП 54.13330.2024", [1]),
        ("ГОСТ 21.101-2020", [1]),
        ("СП 54.13330.2011", [1]),
        ("ГОСТ Р 99999-2020", [1]),
        ("СП 54.13330", [3]),
        ("СНиП 31-01-2012", [3]),
        ("СП 54.13330.2022", [3]),
    ]


def test_the_outcome_codes_are_exactly_the_resolvers_five_outcomes_in_order() -> None:
    assert set(OUTCOME_CODES) == set(OUTCOMES)
    assert len(OUTCOMES) == 5
    assert OUTCOME_ORDER == (
        "in_corpus", "newer_edition", "older_edition_only", "not_in_corpus", "not_recognised",
    )


def test_counts_write_every_outcome_even_for_a_text_that_cites_nothing() -> None:
    model = _model({1: "Общие данные. Лист 1 из 1."})

    assert model.items == ()
    assert dict(model.counts) == {code: 0 for code in OUTCOME_ORDER}
    assert (model.occurrence_count, model.unread_pages) == (0, ())


# --- the newest edition wins ---------------------------------------------------------------


def test_the_newest_edition_wins_not_the_next_one() -> None:
    item = _outcome("СП 54.13330.2011", SP54_2011, SP54_2022, SP54_2024)

    assert item.outcome == "newer_edition"
    assert item.matched_designation == "СП 54.13330.2024"


def test_a_newer_edition_wins_over_the_cited_edition_being_present() -> None:
    item = _outcome("СП 54.13330.2022", SP54_2011, SP54_2022, SP54_2024)

    assert item.outcome == "newer_edition"
    assert item.matched_designation == "СП 54.13330.2024"


def test_the_cited_edition_is_in_the_corpus_when_nothing_newer_is() -> None:
    item = _outcome("СП 54.13330.2022", SP54_2011, SP54_2022)

    assert (item.outcome, item.matched_designation) == ("in_corpus", "СП 54.13330.2022")


def test_only_earlier_editions_report_the_newest_earlier_one() -> None:
    item = _outcome("СП 54.13330.2024", SP54_2011, SP54_2022)

    assert (item.outcome, item.matched_designation) == ("older_edition_only", "СП 54.13330.2022")


def test_a_family_or_base_the_corpus_lacks_is_not_in_the_corpus() -> None:
    assert _outcome("СП 99.13330.2020", SP54_2022).outcome == "not_in_corpus"
    assert _outcome("ГОСТ 21.101-2020", SP54_2022).outcome == "not_in_corpus"


# --- an amendment is never an edition ------------------------------------------------------


def test_an_amendment_document_is_not_a_newer_edition_of_its_base() -> None:
    item = _outcome("СП 51.13330.2011", SP51_BASE, SP51_AMEND)

    assert (item.outcome, item.matched_designation) == ("in_corpus", "СП 51.13330.2011")


def test_an_amendment_that_sorts_before_its_base_is_still_not_the_match() -> None:
    """The tie-break among equals is the document id; an amendment must not be an equal."""
    item = _outcome("СП 51.13330.2011", SP51_AMEND, SP51_BASE)

    assert (item.outcome, item.matched_designation) == ("in_corpus", "СП 51.13330.2011")
    assert item.matched_document_id == f"ndoc_{2:026d}"


def test_a_cited_amendment_is_matched_to_the_same_amendment_only() -> None:
    cited = "Изменение N 1 к СП 51.13330.2011"

    assert _outcome(cited, SP51_BASE, SP51_AMEND).outcome == "in_corpus"
    # The base alone does not hold the cited amendment: the amendment is absent.
    assert _outcome(cited, SP51_BASE).outcome == "not_in_corpus"
    # A different amendment number is a different citation.
    assert _outcome("Изменение N 2 к СП 51.13330.2011", SP51_BASE, SP51_AMEND).outcome == "not_in_corpus"


def test_a_cited_amendment_of_an_older_base_is_answered_by_a_newer_base_edition() -> None:
    item = _outcome("Изменение N 1 к СП 51.13330.2011", SP51_BASE, "СП_51_13330_2016__Защита_от_шума")

    assert (item.outcome, item.matched_designation) == ("newer_edition", "СП 51.13330.2016")


def test_a_cited_amendment_is_answered_by_the_newest_newer_base_edition() -> None:
    item = _outcome(
        "Изменение N 1 к СП 51.13330.2011",
        SP51_BASE, "СП_51_13330_2016__Защита_от_шума", "СП_51_13330_2022__Защита_от_шума",
    )

    assert (item.outcome, item.matched_designation) == ("newer_edition", "СП 51.13330.2022")


# --- laws and acts are one citation in both word orders -----------------------------------


def test_a_federal_law_in_every_word_order_is_one_citation_with_every_page() -> None:
    model = _model(
        {
            1: "Федеральный закон № 123-ФЗ о требованиях.",
            2: "Согласно ФЗ-123 и далее.",
            3: "Требования 123-ФЗ применены.",
        },
        LAW_123,
    )

    assert len(model.items) == 1
    item = model.items[0]
    assert (item.outcome, item.occurrence_count) == ("in_corpus", 3)
    assert [a.page_number for a in item.anchors] == [1, 2, 3]
    assert [a.quote for a in item.anchors] == ["Федеральный закон № 123-ФЗ", "ФЗ-123", "123-ФЗ"]
    assert item.matched_designation == "Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)"


def test_a_government_act_in_both_forms_is_one_citation() -> None:
    model = _model({1: "ПП РФ № 87 и Постановление Правительства РФ № 87."}, ACT_87)

    assert [(i.outcome, i.occurrence_count) for i in model.items] == [("in_corpus", 2)]


def test_a_non_breaking_space_and_a_dash_variant_group_with_the_plain_spelling() -> None:
    model = _model({1: "СП 54.13330.2022 и СП 54.13330.2022; ГОСТ 21.101–2020"}, SP54_2022, GOST_21_101)

    assert [(i.outcome, i.occurrence_count) for i in model.items] == [
        ("in_corpus", 2), ("in_corpus", 1),
    ]


# --- at most ten occurrences, the true count -----------------------------------------------


def test_at_most_ten_anchors_are_kept_in_reading_order_and_the_count_is_true() -> None:
    pages = {number: "См. СП 54.13330.2022." for number in range(1, 13)}

    item = _model(pages, SP54_2022).items[0]

    assert MAX_EVIDENCE_OCCURRENCES == 10
    assert item.occurrence_count == 12
    assert [a.page_number for a in item.anchors] == list(range(1, 11))


def test_the_occurrence_total_counts_every_citation_not_only_the_kept_anchors() -> None:
    pages = {number: "СП 54.13330.2022; ГОСТ 21.101-2020" for number in range(1, 13)}

    model = _model(pages, SP54_2022, GOST_21_101)

    assert model.occurrence_count == 24
    assert [len(item.anchors) for item in model.items] == [10, 10]


# --- pages with no text layer; the catalogue's unparsed slugs ------------------------------


def test_an_empty_page_is_unread_and_a_whitespace_page_is_read() -> None:
    model = _model({1: "", 2: " ", 3: "СП 54.13330.2022", 4: ""}, SP54_2022)

    assert model.unread_pages == (1, 4)
    assert model.page_count == 4
    assert [a.page_number for a in model.items[0].anchors] == [3]


def test_the_unparsed_catalogue_slugs_are_listed_with_what_the_reader_sees() -> None:
    model = _model({1: "СП 54.13330.2022"}, SP54_2022, MDS, ORDER)

    assert [(u.slug, u.designation, u.title) for u in model.unrecognised] == [
        (MDS, "МДС 12-24.2006", "Устройство обычных"),
        (ORDER, "Приказ МЧС России от 19.03.2020 N 194", None),
    ]
    assert [u.document_id for u in model.unrecognised] == [
        f"ndoc_{number:026d}" for number in (2, 3)
    ]


def test_the_unparsed_list_is_the_catalogues_own_not_a_reviewed_one() -> None:
    catalogue = _catalogue(SP54_2022, MDS)
    assert catalogue.listed_unparsed_slugs == (MDS,)

    # The same documents with no unparsed slug listed are refused by the resolver, not read.
    unlisted = PinnedCatalogue(SNAPSHOT, catalogue.documents, ())
    with pytest.raises(ReferenceRefused, match="unlisted unparsed"):
        build_reference_read_model(
            pages={1: "СП 54.13330.2022"}, catalogue=unlisted, pinned_snapshot_id=SNAPSHOT
        )


# --- refusals ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pages",
    [{}, {2: "x"}, {1: "x", 3: "y"}, {0: "x"}, {1: None}, {1: b"x"}, {True: "x"}, [("1", "x")], None],
)
def test_pages_that_are_not_numbered_one_to_n_with_text_are_refused(pages) -> None:
    with pytest.raises(ReferenceRefused):
        build_reference_read_model(
            pages=pages, catalogue=_catalogue(SP54_2022), pinned_snapshot_id=SNAPSHOT
        )


def test_a_catalogue_of_another_snapshot_is_refused() -> None:
    with pytest.raises(ReferenceRefused, match="differs from pinned"):
        build_reference_read_model(
            pages={1: "СП 54.13330.2022"}, catalogue=_catalogue(SP54_2022),
            pinned_snapshot_id="ns_" + "1" * 26,
        )


def test_a_catalogue_with_tokens_that_differ_from_the_twin_is_refused() -> None:
    bad = PinnedCatalogue(
        SNAPSHOT, (CatalogueEntry("ndoc_" + "0" * 26, SP54_2022, ("сп", "54")),)
    )
    with pytest.raises(ReferenceRefused, match="tokens mismatch"):
        build_reference_read_model(
            pages={1: "СП 54.13330.2022"}, catalogue=bad, pinned_snapshot_id=SNAPSHOT
        )


def test_more_distinct_citations_than_the_cap_are_refused_not_cut(monkeypatch) -> None:
    monkeypatch.setattr(module, "MAX_CITED_NORMS", 2)
    catalogue = _catalogue(SP54_2022)

    within = build_reference_read_model(
        pages={1: "СП 54.13330.2022 ГОСТ 21.101-2020"}, catalogue=catalogue, pinned_snapshot_id=SNAPSHOT
    )
    assert len(within.items) == 2
    with pytest.raises(TooManyCitations):
        build_reference_read_model(
            pages={1: "СП 54.13330.2022 ГОСТ 21.101-2020 ГОСТ 21.101-2021"},
            catalogue=catalogue, pinned_snapshot_id=SNAPSHOT,
        )
    assert issubclass(TooManyCitations, ReferenceRefused)


def test_the_citation_cap_is_the_documented_number() -> None:
    assert MAX_CITED_NORMS == 1000


def test_the_same_input_gives_the_same_model() -> None:
    assert _model(RECORDED) == _model(RECORDED)


# --- the model refuses a resolver answer that contradicts itself ---------------------------


def _stub_report(monkeypatch, **changes):
    """Replace the resolver's one report by a copy of its real one with fields changed."""
    from dataclasses import replace

    real = module.resolve_references

    def resolve(**keywords):
        report = real(**keywords)
        first = replace(report.references[0], **changes)
        return replace(report, references=(first, *report.references[1:]))

    monkeypatch.setattr(module, "resolve_references", resolve)


@pytest.mark.parametrize(
    "changes",
    [
        {"outcome": "неизвестный исход"},
        {"outcome": "нет в корпусе"},  # absent, yet it names a matched document
        {"matched_document_id": None},  # present, yet it names no document
        {"matched_document_id": "ndoc_" + "9" * 26},  # a document the catalogue does not hold
        {"matched_designation": None},
        {"occurrences": ()},
        {"total_occurrences": 0},
    ],
    ids=[
        "unknown-outcome", "absent-with-match", "present-without-match", "foreign-document",
        "present-without-designation", "no-occurrence", "total-below-kept",
    ],
)
def test_a_self_contradicting_resolver_answer_is_refused(monkeypatch, changes) -> None:
    _stub_report(monkeypatch, **changes)

    with pytest.raises(ReferenceRefused):
        _model({1: "СП 54.13330.2022"}, SP54_2022)
