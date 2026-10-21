"""`NORM-REFS-RUN-01`: the pinned catalogue is read from the snapshot's own document rows.

Container-free. A fake session answers the two statements ``read_snapshot_catalogue`` sends
(recognised by identity of the module-level ``text()`` objects) from a Python list, and
records every call, so what these prove is the Python around the SQL: the bounded keyset
paging, the totality check against the declared count, the canonical order, and the unparsed
slug list the parser computes. What the SQL itself selects is proved on PostgreSQL by
``tests/integration/norms/references/test_snapshot_catalogue_db.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.norms.references import snapshot_catalogue as module
from auditmanager.norms.references.families import parse_designation
from auditmanager.norms.references.resolution import (
    PinnedCatalogue,
    ReferenceRefused,
    extract_references,
    resolve_references,
    TextPage,
)
from auditmanager.norms.references.snapshot_catalogue import (
    MAX_SNAPSHOT_DOCUMENTS,
    SNAPSHOT_PAGE_SIZE,
    catalogue_from_rows,
    read_snapshot_catalogue,
)
from auditmanager.norms.references.tokens import sql_designation_tokens

SNAPSHOT = "ns_" + "0" * 26
OTHER = "ns_" + "1" * 26

PARSED = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
LAW = "Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023)"
UNPARSED_A = "МДС_12-24_2006__Устройство_обычных"
UNPARSED_B = "Приказ_МЧС_России_от_19_03_2020_N_194"


def _id(number: int) -> str:
    return f"ndoc_{number:026d}"


def _row(number: int, slug_text: str, **changes: Any) -> dict[str, Any]:
    row = {
        "norm_document_id": _id(number),
        "slug": slug_text,
        "designation_tokens": list(sql_designation_tokens(slug_text)),
    }
    row.update(changes)
    return row


def _rows(*slugs: str) -> list[dict[str, Any]]:
    return [_row(number, slug) for number, slug in enumerate(slugs, 1)]


# --- the pure part -----------------------------------------------------------------------


def test_the_unparsed_slugs_are_computed_by_the_parser_in_catalogue_order() -> None:
    catalogue = catalogue_from_rows(
        snapshot_id=SNAPSHOT, declared_count=4,
        rows=_rows(PARSED, UNPARSED_A, LAW, UNPARSED_B),
    )

    assert isinstance(catalogue, PinnedCatalogue)
    assert catalogue.snapshot_id == SNAPSHOT
    assert [d.slug for d in catalogue.documents] == [PARSED, UNPARSED_A, LAW, UNPARSED_B]
    assert catalogue.listed_unparsed_slugs == (UNPARSED_A, UNPARSED_B)
    assert [d.slug for d in catalogue.documents if parse_designation(d.slug) is None] == list(
        catalogue.listed_unparsed_slugs
    )
    assert all(d.designation_tokens == sql_designation_tokens(d.slug) for d in catalogue.documents)


def test_the_built_catalogue_is_accepted_by_the_resolver_unchanged() -> None:
    """The resolver's own consistency checks (unique identity, twin tokens, a complete and
    exact unparsed listing) accept what this reader builds -- there is no second rule."""
    catalogue = catalogue_from_rows(
        snapshot_id=SNAPSHOT, declared_count=3, rows=_rows(PARSED, UNPARSED_A, LAW)
    )

    report = resolve_references(
        extraction=extract_references((TextPage("1", "см. СП 54.13330.2022 и 123-ФЗ"),)),
        catalogue=catalogue,
        pinned_snapshot_id=SNAPSHOT,
    )

    assert [r.outcome for r in report.references] == ["есть в корпусе", "есть в корпусе"]


@pytest.mark.parametrize(
    ("rows", "declared", "reason"),
    [
        (_rows(PARSED), 2, "fewer"),
        (_rows(PARSED, LAW), 1, "more"),
        ([], 1, "fewer"),
        ([_row(2, PARSED), _row(1, LAW)], 2, "canonical order"),
        ([_row(1, PARSED), _row(1, LAW)], 2, "canonical order"),
        ([_row(1, PARSED, norm_document_id="doc_1")], 1, "document id"),
        ([_row(1, PARSED, norm_document_id=None)], 1, "document id"),
        ([_row(1, "")], 1, "slug"),
        ([_row(1, PARSED, slug=None)], 1, "slug"),
        ([_row(1, PARSED, designation_tokens=[])], 1, "tokens"),
        ([_row(1, PARSED, designation_tokens=None)], 1, "tokens"),
        ([_row(1, PARSED, designation_tokens=["сп", ""])], 1, "tokens"),
    ],
)
def test_inconsistent_rows_are_refused_not_repaired(rows, declared, reason) -> None:
    with pytest.raises(ReferenceRefused) as refused:
        catalogue_from_rows(snapshot_id=SNAPSHOT, declared_count=declared, rows=rows)
    assert reason in str(refused.value)


@pytest.mark.parametrize("declared", [0, -1, MAX_SNAPSHOT_DOCUMENTS + 1, True, "3", None])
def test_an_unusable_declared_count_is_refused(declared) -> None:
    with pytest.raises(ReferenceRefused, match="document count"):
        catalogue_from_rows(snapshot_id=SNAPSHOT, declared_count=declared, rows=_rows(PARSED))


def test_an_invalid_snapshot_id_is_refused() -> None:
    with pytest.raises(ReferenceRefused, match="snapshot id"):
        catalogue_from_rows(snapshot_id="ns_x", declared_count=1, rows=_rows(PARSED))


def test_a_stored_token_that_differs_from_the_twin_is_left_for_the_resolver_to_refuse() -> None:
    """This reader copies the stored tokens (as the saved catalogue does); the resolver is the
    one place that proves them equal to the Python twin, and it refuses a difference."""
    catalogue = catalogue_from_rows(
        snapshot_id=SNAPSHOT, declared_count=1,
        rows=[_row(1, PARSED, designation_tokens=["сп", "54", "13330", "2021"])],
    )

    with pytest.raises(ReferenceRefused, match="tokens mismatch"):
        resolve_references(
            extraction=extract_references((TextPage("1", "СП 54.13330.2022"),)),
            catalogue=catalogue,
            pinned_snapshot_id=SNAPSHOT,
        )


# --- the paged read ----------------------------------------------------------------------


class _Result:
    def __init__(self, rows: list[dict[str, Any]], scalar: Any = None) -> None:
        self._rows, self._scalar = rows, scalar

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class _Session:
    """Answers ``_DECLARED_COUNT`` and ``_DOCUMENT_PAGE`` from a list, in keyset order."""

    def __init__(self, rows: list[dict[str, Any]], *, declared: int | None, snapshot: str = SNAPSHOT):
        self.rows, self.declared, self.snapshot = rows, declared, snapshot
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, parameters: dict[str, Any]) -> _Result:
        self.calls.append((str(statement), dict(parameters)))
        assert parameters["snapshot_id"] == self.snapshot
        if statement is module._DECLARED_COUNT:
            return _Result([], self.declared)
        assert statement is module._DOCUMENT_PAGE
        after, size = parameters["after"], parameters["page_size"]
        page = [row for row in sorted(self.rows, key=lambda r: r["norm_document_id"])
                if row["norm_document_id"] > after][:size]
        return _Result(page)

    @property
    def pages(self) -> list[dict[str, Any]]:
        return [params for _, params in self.calls if "after" in params]


SLUGS = (PARSED, UNPARSED_A, LAW, UNPARSED_B, "СНиП_31-01-2003__Здания_жилые")


def test_the_snapshot_is_read_by_keyset_pages_of_the_requested_size() -> None:
    session = _Session(_rows(*SLUGS), declared=5)

    catalogue = read_snapshot_catalogue(session, snapshot_id=SNAPSHOT, page_size=2)

    assert [d.slug for d in catalogue.documents] == list(SLUGS)
    assert catalogue.listed_unparsed_slugs == (UNPARSED_A, UNPARSED_B)
    assert [(p["after"], p["page_size"]) for p in session.pages] == [
        ("", 2), (_id(2), 2), (_id(4), 2),
    ]


def test_an_exactly_full_last_page_costs_one_more_empty_read_and_no_more() -> None:
    session = _Session(_rows(*SLUGS[:4]), declared=4)

    read_snapshot_catalogue(session, snapshot_id=SNAPSHOT, page_size=2)

    assert [p["after"] for p in session.pages] == ["", _id(2), _id(4)]


def test_the_statements_are_select_only_keyset_and_bounded() -> None:
    session = _Session(_rows(PARSED), declared=1)

    read_snapshot_catalogue(session, snapshot_id=SNAPSHOT)

    sent = [sql for sql, _ in session.calls]
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in sent)
    page_sql = " ".join(sent[1].split())
    assert "norms_snapshot_id = :snapshot_id" in page_sql
    assert 'norm_document_id COLLATE "C" > :after' in page_sql
    assert 'ORDER BY norm_document_id COLLATE "C"' in page_sql
    assert "LIMIT :page_size" in page_sql
    assert "OFFSET" not in page_sql.upper()
    assert session.pages[0]["page_size"] == SNAPSHOT_PAGE_SIZE


def test_a_snapshot_storing_more_than_it_declares_stops_after_one_page() -> None:
    session = _Session(_rows(*SLUGS), declared=2)

    with pytest.raises(ReferenceRefused, match="more documents"):
        read_snapshot_catalogue(session, snapshot_id=SNAPSHOT, page_size=3)

    assert len(session.pages) == 1


def test_a_snapshot_storing_fewer_than_it_declares_is_refused() -> None:
    with pytest.raises(ReferenceRefused, match="fewer documents"):
        read_snapshot_catalogue(
            _Session(_rows(*SLUGS[:2]), declared=3), snapshot_id=SNAPSHOT, page_size=2
        )


def test_an_absent_snapshot_is_refused_before_any_document_is_read() -> None:
    session = _Session(_rows(PARSED), declared=None)

    with pytest.raises(ReferenceRefused, match="absent"):
        read_snapshot_catalogue(session, snapshot_id=SNAPSHOT)

    assert session.pages == []


@pytest.mark.parametrize("page_size", [0, -1, SNAPSHOT_PAGE_SIZE + 1, True, "2", None])
def test_an_unusable_page_size_is_refused_before_any_read(page_size) -> None:
    session = _Session(_rows(PARSED), declared=1)

    with pytest.raises(ReferenceRefused, match="page size"):
        read_snapshot_catalogue(session, snapshot_id=SNAPSHOT, page_size=page_size)

    assert session.calls == []


def test_an_invalid_snapshot_id_is_refused_before_any_read() -> None:
    session = _Session(_rows(PARSED), declared=1)

    with pytest.raises(ReferenceRefused, match="snapshot id"):
        read_snapshot_catalogue(session, snapshot_id="not-a-snapshot")

    assert session.calls == []


def test_the_page_size_ceiling_and_the_document_ceiling_are_the_documented_numbers() -> None:
    assert (SNAPSHOT_PAGE_SIZE, MAX_SNAPSHOT_DOCUMENTS) == (500, 20_000)
