"""`W57B-NORMS-CATALOGUE-XLSX-01`: the catalogue over a real PostgreSQL at the migration head.

The rows are the search suite's plain-SQL rows (``Corpus``); the slugs are real slugs of the
W54 snapshot. Each case asserts what a reader of ``listNormDocuments`` would see: the scope,
the display names, the filters, the order, the paging and the refusals.
"""

from __future__ import annotations

import pytest

from auditmanager.norms.public import list_norm_catalogue
from auditmanager.shared.errors import DomainError, ErrorCode

ORDER_288 = "Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)"
LAW_123 = "Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023"
SP_54 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP_3 = "СП_3_13130_2009__Свод_правил__Системы_противопожарной_защит"
SP_7 = "СП_7_13130_2013__Свод_правил__Отопление,_вентиляция_и_конди"
SP_104 = "СП_104_13330_2016__Свод_правил__Инженерная_защита_территори"
GOST = "ГОСТ_1759_5-87_(СТ_СЭВ_5958-87)__Гайки__Механические_свойст"


def _list(corpus, **arguments):
    arguments.setdefault("q", None)
    arguments.setdefault("kind", None)
    arguments.setdefault("cursor", None)
    arguments.setdefault("limit", 50)
    with corpus.session_factory() as session:
        return list_norm_catalogue(session, **arguments)


def _current(corpus, *slugs: str) -> tuple[str, dict[str, str]]:
    snapshot = corpus.snapshot(documents=len(slugs))
    documents = {slug: corpus.document(snapshot, slug) for slug in slugs}
    corpus.designate(snapshot)
    return snapshot, documents


def test_no_current_snapshot_is_required_norm_unavailable(corpus) -> None:
    snapshot = corpus.snapshot()
    corpus.document(snapshot, SP_54)
    with pytest.raises(DomainError) as caught:
        _list(corpus)
    assert caught.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
    assert dict(caught.value.detail_fields) == {"reference_kind": "norms_snapshot"}


def test_the_current_snapshot_only_with_display_names_and_counts(corpus) -> None:
    old = corpus.snapshot()
    corpus.document(old, SP_104)
    corpus.designate(old)
    snapshot, documents = _current(corpus, ORDER_288, SP_54, GOST)
    corpus.bind_pdf(documents[SP_54])

    page = _list(corpus)
    assert page.norms_snapshot_id == snapshot
    assert page.total == 3 and page.next_cursor is None
    by_id = {item.norm_document_id: item for item in page.items}
    assert set(by_id) == set(documents.values())

    order = by_id[documents[ORDER_288]]
    assert order.designation == "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)"
    assert order.title is None and order.kind == "Приказ"
    sp = by_id[documents[SP_54]]
    assert (sp.designation, sp.title) == (
        "СП 54.13330.2022", "Свод правил. Здания жилые многоквартирные"
    )
    assert sp.content_available is True and order.content_available is False
    assert (sp.page_count, sp.paragraph_count, sp.source_attribution) == (
        50, 0, "consultant_plus"
    )
    assert [(kind.kind, kind.document_count) for kind in page.kinds] == [
        ("ГОСТ", 1), ("Приказ", 1), ("СП", 1)
    ]


def test_rows_are_never_altered(corpus) -> None:
    _snapshot, documents = _current(corpus, ORDER_288)
    _list(corpus)
    stored = corpus.scalar(
        "SELECT slug FROM norm_document WHERE norm_document_id = :d", d=documents[ORDER_288]
    )
    assert stored == ORDER_288


def test_order_is_by_designation_natural(corpus) -> None:
    _snapshot, documents = _current(corpus, SP_104, LAW_123, SP_54, GOST, SP_3, ORDER_288, SP_7)
    page = _list(corpus)
    assert [item.designation for item in page.items] == [
        "ГОСТ 1759.5-87 (СТ СЭВ 5958-87)",
        "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)",
        "СП 3.13130.2009",
        "СП 7.13130.2013",
        "СП 54.13330.2022",
        "СП 104.13330.2016",
        "Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)",
    ]


def test_filters_by_text_and_kind(corpus) -> None:
    _snapshot, documents = _current(corpus, SP_104, LAW_123, SP_54, GOST, SP_3, ORDER_288, SP_7)
    assert [item.norm_document_id for item in _list(corpus, q="24.04.2013").items] == [
        documents[ORDER_288]
    ]
    assert [item.designation for item in _list(corpus, q="сп 54.13330").items] == [
        "СП 54.13330.2022"
    ]
    protection = _list(corpus, q="защит")
    assert [item.designation for item in protection.items] == [
        "СП 3.13130.2009", "СП 104.13330.2016"
    ]
    assert protection.total == 2
    by_kind = _list(corpus, kind="СП")
    assert by_kind.total == 4 and {item.kind for item in by_kind.items} == {"СП"}
    assert [(kind.kind, kind.document_count) for kind in by_kind.kinds][0] == ("СП", 4)
    unknown = _list(corpus, kind="Указ")
    assert unknown.items == () and unknown.total == 0 and unknown.next_cursor is None
    assert _list(corpus, q="СП", kind="Приказ").items == ()


def test_paging_is_stable_and_bound_to_its_listing(corpus) -> None:
    slugs = (SP_104, LAW_123, SP_54, GOST, SP_3, ORDER_288, SP_7)
    _snapshot, _documents = _current(corpus, *slugs)
    whole = [item.norm_document_id for item in _list(corpus).items]

    seen: list[str] = []
    cursor = None
    while True:
        page = _list(corpus, cursor=cursor, limit=4)
        seen.extend(item.norm_document_id for item in page.items)
        assert page.total == len(slugs)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    assert seen == whole

    first = _list(corpus, limit=2)
    assert first.next_cursor is not None
    again = _list(corpus, cursor=first.next_cursor, limit=2)
    assert again == _list(corpus, cursor=first.next_cursor, limit=2)
    for foreign in ({"q": "СП"}, {"kind": "СП"}):
        with pytest.raises(DomainError) as caught:
            _list(corpus, cursor=first.next_cursor, limit=2, **foreign)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert dict(caught.value.detail_fields)["field"] == "cursor"


def test_a_token_from_an_earlier_current_snapshot_is_refused(corpus) -> None:
    _snapshot, _documents = _current(corpus, SP_7, SP_54, SP_3)
    token = _list(corpus, limit=1).next_cursor
    assert token is not None
    _current(corpus, SP_7, SP_54, SP_3)
    with pytest.raises(DomainError) as caught:
        _list(corpus, cursor=token, limit=1)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"q": "..."}, "q"),
        ({"q": "СП\x0054"}, "q"),
        ({"q": "x" * 201}, "q"),
        ({"kind": "   "}, "kind"),
        ({"kind": "К" * 101}, "kind"),
        ({"kind": "СП\x01"}, "kind"),
    ],
)
def test_unfilterable_values_are_refused_before_any_read(corpus, arguments, field) -> None:
    # No snapshot is current: a refusal here proves the value was checked first.
    with pytest.raises(DomainError) as caught:
        _list(corpus, **arguments)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": field, "constraint": "format"}
