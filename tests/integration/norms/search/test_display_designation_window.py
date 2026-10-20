"""`NORMS-DISPLAY-DESIGNATION-01` against PostgreSQL: the designation moves, the search does not.

``searchNorms``, ``getNormDocument`` and the paragraphs read show the readable designation the
catalogue shows (``СП 54.13330.2022``), a derivation longer than the schemas allow falls back
to the stored text, and **nothing else moves**: the hits, their order and their ids for a
fixed set of queries are the ones the code produced *before* this task.

The golden (``GOLDEN``) was written from the statements' ordering rules and then **confirmed
on an untouched copy of the base tree** (``git archive 59f976fc``, ``designation_of`` in both
places): every golden and paging test passes there, twice, and the two designation tests
(``test_search_shows_...``, ``test_the_document_and_its_paragraphs_...``) fail there, as they
must. The same file passes on the changed tree. Ranks are made distinct by the number of
times the word occurs, so no order here is a tie broken by a random identity.

The rows are written by plain SQL (``conftest.Corpus``), never by the code under test.
"""

from __future__ import annotations

import pytest

from auditmanager.bootstrap.adapters import NormsSearchAdapter
from auditmanager.norms.public import (
    get_norm_document,
    list_norm_catalogue,
    list_norm_paragraphs,
    search_norms,
)
from tests.integration.norms.search.conftest import Corpus

SLUGS = {
    "sp54": "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные",
    "sp542": "СП_542_1325800_2024__Свод_правил__Защитные_сооружения",
    "gost": "ГОСТ_1759_5-87_(СТ_СЭВ_5958-87)__Гайки__Механические_свойст",
    "order": "Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)",
    "plain": "Здания_и_фрагменты_зданий__Метод_натурных_огневых_испытаний",
    # 500 characters (the column's bound): the derivation is 504 -- `(ред` becomes
    # `(ред. …)` -- and the stored projection 500, while the schemas allow 500.
    "long": "Приказ_" + "Б" * 488 + "_(ред",
}
#: What a reader sees for each document now. `long` is the stored text (the fallback).
SHOWN = {
    "sp54": "СП 54.13330.2022",
    "sp542": "СП 542.1325800.2024",
    "gost": "ГОСТ 1759.5-87 (СТ СЭВ 5958-87)",
    "order": "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)",
    "plain": "Здания и фрагменты зданий",
    "long": "Приказ " + "Б" * 488 + " (ред",
}
#: What the catalogue shows for `long`: its schema allows 520, so the derivation stands.
CATALOGUE_LONG = "Приказ " + "Б" * 488 + " (ред. …)"

PARAGRAPHS = [
    # label, document, ordinal, clause, text (the number of "лестницы" sets the rank)
    ("sp54.a", "sp54", 0, "7.1", "7.1 Лестницы"),
    ("sp54.b", "sp54", 1, "7.1.4", "7.1.4 Лестницы жилых зданий: лестницы и лестницы"),
    ("sp542.c", "sp542", 0, "7.1.2", "7.1.2 Лестницы защитных сооружений и лестницы"),
    ("gost.d", "gost", 0, "7.1.3", "7.1.3 Лестницы лестницы лестницы лестницы"),
    ("order.e", "order", 0, None, "Лестницы эвакуации лестницы лестницы лестницы лестницы"),
    ("plain.f", "plain", 0, None, "Лестницы лестницы лестницы лестницы лестницы лестницы"),
    ("long.g", "long", 0, None, "Карнизы выступающие"),
]

#: Fixed query -> the hits' labels in order, as the base tree (`59f976fc`) returned them.
GOLDEN = {
    "лестницы": ["plain.f", "order.e", "gost.d", "sp54.b", "sp542.c", "sp54.a"],
    "СП 54": ["sp54.a", "sp54.b"],
    "СП 542": ["sp542.c"],
    "СП 54 лестницы": ["sp54.b", "sp54.a"],
    "ГОСТ 1759": ["gost.d"],
    "п. 7.1": ["gost.d", "sp54.a", "sp54.b", "sp542.c"],
    "п. 7.1 лестницы": ["gost.d", "sp54.b", "sp542.c", "sp54.a"],
    "карнизы": ["long.g"],
}


class Seeded:
    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus
        self.snapshot = corpus.snapshot(documents=len(SLUGS))
        self.documents = {
            key: corpus.document(self.snapshot, slug) for key, slug in SLUGS.items()
        }
        self.paragraphs = {
            label: corpus.paragraph(
                self.documents[document], text, ordinal=ordinal, clause=clause
            )
            for label, document, ordinal, clause, text in PARAGRAPHS
        }
        self.label_of = {identity: label for label, identity in self.paragraphs.items()}
        self.key_of = {identity: key for key, identity in self.documents.items()}
        corpus.designate(self.snapshot)
        self.adapter = NormsSearchAdapter(corpus.session_factory, timeout_ms=3000)

    def labels(self, q: str, *, limit: int = 50) -> list[str]:
        """The hits' labels in the order the search returned them, paged to the end."""
        collected: list[str] = []
        cursor = None
        while True:
            page = self.adapter.search(q=q, norms_snapshot_id=None, cursor=cursor, limit=limit)
            collected += [self.label_of[item.norm_paragraph_id] for item in page.items]
            cursor = page.page.next_cursor
            if cursor is None:
                return collected


@pytest.fixture
def seeded(corpus: Corpus) -> Seeded:
    return Seeded(corpus)


# --- nothing but the designation moves -----------------------------------------------------


@pytest.mark.parametrize("q", sorted(GOLDEN))
def test_search_order_and_ids_are_the_golden(seeded: Seeded, q: str) -> None:
    assert seeded.labels(q) == GOLDEN[q]


@pytest.mark.parametrize("q", ["лестницы", "п. 7.1", "п. 7.1 лестницы"])
def test_paging_one_hit_at_a_time_walks_the_same_order(seeded: Seeded, q: str) -> None:
    assert seeded.labels(q, limit=1) == GOLDEN[q]
    assert seeded.labels(q, limit=2) == GOLDEN[q]


def test_the_search_service_and_the_adapter_agree_on_ids_and_order(seeded: Seeded) -> None:
    with seeded.corpus.session_factory() as session:
        page = search_norms(
            session, q="лестницы", norms_snapshot_id=None, cursor=None, limit=50,
            timeout_ms=3000,
        )
    assert [seeded.label_of[hit.norm_paragraph_id] for hit in page.items] == GOLDEN["лестницы"]
    assert {hit.norm_document_id for hit in page.items} == {
        seeded.documents[key] for key in ("sp54", "sp542", "gost", "order", "plain")
    }


# --- the designation ------------------------------------------------------------------------


def _shown_by_search(seeded: Seeded) -> dict[str, set[str]]:
    shown: dict[str, set[str]] = {}
    for q in ("лестницы", "карнизы"):
        page = seeded.adapter.search(q=q, norms_snapshot_id=None, cursor=None, limit=50)
        for hit in page.items:
            shown.setdefault(seeded.key_of[hit.norm_document_id], set()).add(hit.designation)
    return shown


def test_search_shows_the_readable_designation_and_one_per_document(seeded: Seeded) -> None:
    assert _shown_by_search(seeded) == {key: {text} for key, text in SHOWN.items()}


def test_the_document_and_its_paragraphs_show_the_same_designation(seeded: Seeded) -> None:
    for key, identity in seeded.documents.items():
        assert seeded.adapter.get_document(norm_document_id=identity).designation == SHOWN[key]
        with seeded.corpus.session_factory() as session:
            assert get_norm_document(session, identity).designation == SHOWN[key]
            document, _page = list_norm_paragraphs(session, identity, cursor=None, limit=10)
        assert document.designation == SHOWN[key]


def test_the_catalogue_shows_the_same_except_where_its_wider_schema_keeps_the_derivation(
    seeded: Seeded,
) -> None:
    with seeded.corpus.session_factory() as session:
        page = list_norm_catalogue(session, q=None, kind=None, cursor=None, limit=50)
    by_key = {seeded.key_of[item.norm_document_id]: item.designation for item in page.items}
    assert by_key == SHOWN | {"long": CATALOGUE_LONG}
    # Everywhere the derivation fits the search's 500, search, document and catalogue agree.
    assert {key for key in SHOWN if by_key[key] != SHOWN[key]} == {"long"}
    assert len(SHOWN["long"]) == 500 < len(CATALOGUE_LONG) <= 520


def test_the_long_document_still_validates_on_the_wire(seeded: Seeded) -> None:
    long = seeded.documents["long"]
    assert seeded.corpus.scalar(
        "SELECT char_length(slug) FROM norm_document WHERE norm_document_id = :d", d=long
    ) == 500
    served = seeded.adapter.get_document(norm_document_id=long)
    assert served.designation == SHOWN["long"] and len(served.designation) <= 500
    page = seeded.adapter.search(q="карнизы", norms_snapshot_id=None, cursor=None, limit=5)
    assert [hit.designation for hit in page.items] == [SHOWN["long"]]


def test_no_row_is_altered_by_reading(seeded: Seeded) -> None:
    _shown_by_search(seeded)
    for identity in seeded.documents.values():
        seeded.adapter.get_document(norm_document_id=identity)
    with seeded.corpus.session_factory() as session:
        list_norm_catalogue(session, q=None, kind=None, cursor=None, limit=50)
    stored = {
        row.norm_document_id: (row.slug, row.title, row.paragraph_count)
        for row in seeded.corpus.run(
            "SELECT norm_document_id, slug, title, paragraph_count FROM norm_document"
        ).all()
    }
    assert stored == {
        seeded.documents[key]: (
            slug,
            slug.split("__", 1)[-1].replace("_", " ") or slug,
            0,
        )
        for key, slug in SLUGS.items()
    }
    assert seeded.corpus.scalar("SELECT count(*) FROM norm_paragraph") == len(PARAGRAPHS)
