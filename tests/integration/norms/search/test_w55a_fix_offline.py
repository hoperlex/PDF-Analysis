"""`W55A-FIX`: the judges' search findings, driven without a container.

Through the shipped router and adapters over ``support.FakeNorms`` (the ``Surface`` of
``test_norms_surface_offline.py``), and through the pure modules:

* **X-M1** a forged cursor -- an ``s1d``/``p1`` ordinal past PostgreSQL's ``integer``, an
  ``n1``/``e1`` instant at the edge of :class:`datetime` with an offset -- is
  ``422 cursor/format``, never an internal error;
* **X-M2** a control character in ``q`` (a NUL above all) is ``422 q/format`` before any
  statement; tab, line feed and carriage return are whitespace;
* **X-M3** a ``Range`` number longer than 19 digits is ``422 Range/format``, not the
  ``ValueError`` ``int()`` raises past 4 300 digits;
* **X-M5** a blank ``q`` is ``422 q/format`` before any statement, not a sort of the whole
  snapshot;
* **Y-4** a designation typed with a no-break space, a tab or a dash U+2010-U+2015 is bound
  with ASCII separators, so it tokenises as ``norm_designation_tokens`` tokenises the slug.

The database half is ``test_w55a_fix_window.py``.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import pytest

from auditmanager.api.schemas.content import ByteRange
from auditmanager.norms.search import cursor as cursor_module
from auditmanager.norms.search import service as service_module
from auditmanager.norms.search.cursor import (
    MAX_ORDINAL,
    DesignationPosition,
    ParagraphPosition,
    decode_event_cursor,
    decode_paragraph_cursor,
    decode_search_cursor,
    decode_snapshot_cursor,
    encode_paragraph_cursor,
    encode_search_cursor,
    query_binding,
)
from auditmanager.norms.search.query import FOLD_FROM, FOLD_TO, parse_query, unsearchable
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.norms.search.support import Document, FakeNorms
from tests.integration.norms.search.test_norms_surface_offline import (
    BLOB_ID,
    DATA,
    DIGEST,
    NDOC,
    SNAPSHOT,
    Surface,
    _envelope,
    _searchable,
)

NPAR = "npar_01M2545JSD15ETSNNV904X9001"
EVT = "evt_01M2545JSD15ETSNNV904X9900"

FORMAT_CURSOR = {"field": "cursor", "constraint": "format"}
FORMAT_Q = {"field": "q", "constraint": "format"}


def _refusal(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def _sql_tokens(value: str) -> list[str]:
    """``norm_designation_tokens``: fold, then split on ``[ ._-]``, empty tokens dropped."""
    folded = value.split("__", 1)[0].translate(str.maketrans(FOLD_FROM, FOLD_TO))
    return [token for token in re.split(r"[ ._-]+", folded) if token]


# --- X-M1: forged cursors -----------------------------------------------------------------


def _forged_designation_cursor(q: str, ordinal: int) -> str:
    return encode_search_cursor(
        query_binding(q, SNAPSHOT), DesignationPosition(NDOC, ordinal, NPAR)
    )


def test_an_ordinal_past_postgresqls_integer_is_not_a_position() -> None:
    binding = query_binding("СП 54", SNAPSHOT)
    largest = decode_search_cursor(
        _forged_designation_cursor("СП 54", MAX_ORDINAL), binding=binding, ranked=False
    )
    assert isinstance(largest, DesignationPosition) and largest.ordinal == 2**31 - 1
    error = _refusal(lambda: decode_search_cursor(
        _forged_designation_cursor("СП 54", 2**31), binding=binding, ranked=False
    ))
    assert (error.code, dict(error.detail_fields)) == (ErrorCode.VALIDATION_FAILED, FORMAT_CURSOR)
    for ordinal in (2**31, 10**40):
        token = encode_paragraph_cursor(ParagraphPosition(NDOC, ordinal))
        error = _refusal(lambda: decode_paragraph_cursor(token, norm_document_id=NDOC))
        assert dict(error.detail_fields) == FORMAT_CURSOR, ordinal
    assert decode_paragraph_cursor(
        encode_paragraph_cursor(ParagraphPosition(NDOC, MAX_ORDINAL)), norm_document_id=NDOC
    ).ordinal == MAX_ORDINAL


EDGE_INSTANTS = [
    "0001-01-01T00:00:00+05:00",   # west of UTC's year 1
    "9999-12-31T23:00:00-05:00",   # east of UTC's year 9999
]


@pytest.mark.parametrize("instant", EDGE_INSTANTS)
def test_an_instant_with_no_utc_spelling_is_refused_not_an_overflow(instant: str) -> None:
    snapshot_token = cursor_module._encode(["n1", instant, SNAPSHOT])
    event_token = cursor_module._encode(["e1", instant, EVT])
    for decode, token in ((decode_snapshot_cursor, snapshot_token),
                          (decode_event_cursor, event_token)):
        error = _refusal(lambda: decode(token))
        assert (error.code, dict(error.detail_fields)) == (
            ErrorCode.VALIDATION_FAILED, FORMAT_CURSOR
        )


@pytest.mark.parametrize("instant", EDGE_INSTANTS)
def test_the_listings_answer_a_forged_instant_with_422(instant: str) -> None:
    surface = Surface(_searchable())
    snapshot_token = cursor_module._encode(["n1", instant, SNAPSHOT])
    event_token = cursor_module._encode(["e1", instant, EVT])
    for path in (f"/norms/snapshots?cursor={snapshot_token}",
                 f"/norms/snapshots/events?cursor={event_token}"):
        assert _envelope(surface.get(path)) == (422, "validation_failed", FORMAT_CURSOR), path


def test_the_search_answers_a_forged_ordinal_with_422() -> None:
    surface = Surface(_searchable())
    token = _forged_designation_cursor("СП 54", 2**31)
    assert _envelope(surface.get(f"/norms/search?q={quote('СП 54')}&cursor={token}")) == (
        422, "validation_failed", FORMAT_CURSOR
    )
    # The control: the largest real ordinal resumes.
    token = _forged_designation_cursor("СП 54", MAX_ORDINAL)
    assert surface.get(f"/norms/search?q={quote('СП 54')}&cursor={token}").status_code == 200


# --- X-M2 and X-M5: a q that is not a search text -----------------------------------------


@pytest.mark.parametrize(
    "q",
    ["здания\x00", "\x00", "здания\x07", "СП 54\x1b", "здания\x7f", "здания\x85", "\x0b",
     "здания\ud800"],
    ids=["nul", "nul-only", "bell", "escape", "delete", "c1-nel", "vertical-tab", "surrogate"],
)
def test_a_control_character_is_not_a_search_text(q: str) -> None:
    assert unsearchable(q)


@pytest.mark.parametrize("q", ["", " ", "   ", "\t\n\r", " ", "   \t "])
def test_a_blank_text_is_not_a_search_text(q: str) -> None:
    assert parse_query(q).empty and unsearchable(q)


@pytest.mark.parametrize("q", ["здания", "СП\t54", "здания\r\nлестницы", "п. 7.1", "...", "СП 54"])
def test_a_search_text_is_searchable(q: str) -> None:
    assert not unsearchable(q) and not parse_query(q).empty


@pytest.mark.parametrize(
    "encoded",
    ["%D0%B7%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F%00", "%00", "%07", "%1B", "%7F", "%C2%85",
     "%20", "%20%20%20", "%C2%A0%09", "%09%0A"],
    ids=["nul", "nul-only", "bell", "escape", "delete", "c1-nel",
         "space", "spaces", "nbsp-tab", "tab-lf"],
)
def test_the_search_refuses_it_with_422_before_any_statement(encoded: str) -> None:
    database = _searchable()
    response = Surface(database).get(f"/norms/search?q={encoded}")
    assert _envelope(response) == (422, "validation_failed", FORMAT_Q)
    assert database.sent == [], "a statement was sent for a refused q"


def test_tab_line_feed_and_carriage_return_are_whitespace_in_a_search_text() -> None:
    database = _searchable()
    q = quote("здания\t\r\nлестницы")
    response = Surface(database).get(f"/norms/search?q={q}")
    assert response.status_code == 200, response.text
    assert database.sent[0] == "set_timeout" and database.sent[-1] == "search"


# --- X-M3: a Range number too long to be an offset ----------------------------------------


@pytest.mark.parametrize(
    "header",
    ["bytes=0-" + "9" * 5000, "bytes=" + "1" * 5000 + "-", "bytes=-" + "7" * 5000,
     "bytes=0-" + "9" * 20],
    ids=["last-5000", "first-5000", "suffix-5000", "last-20"],
)
def test_a_range_number_past_nineteen_digits_is_malformed(header: str) -> None:
    error = _refusal(lambda: ByteRange.parse(header))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.VALIDATION_FAILED, {"field": "Range", "constraint": "format"}
    )


def test_nineteen_digits_still_parse_and_clamp_to_the_object() -> None:
    assert ByteRange.parse("bytes=0-" + "9" * 19).resolve(100) == (0, 99)
    assert ByteRange.parse("bytes=-" + "9" * 19).resolve(100) == (0, 99)


def test_the_norm_pdf_answers_a_5000_digit_range_with_422_and_touches_no_store() -> None:
    database = _searchable()
    database.documents = {NDOC: Document(NDOC, SNAPSHOT, pdf=(BLOB_ID, DIGEST, len(DATA)))}
    surface = Surface(database)
    status, code, details = _envelope(
        surface.get(f"/norm-documents/{NDOC}/content", Range="bytes=0-" + "9" * 5000)
    )
    assert (status, code, details) == (
        422, "validation_failed", {"field": "Range", "constraint": "format"}
    )
    assert surface.s3.requests == []
    # The control: a 19-digit last byte is the rest of the object.
    response = surface.get(f"/norm-documents/{NDOC}/content", Range="bytes=100-" + "9" * 19)
    assert response.status_code == 206 and response.content == DATA[100:]


# --- Y-4: the designation's separators ----------------------------------------------------

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые"
SNIP = "СНиП_2_01_07-85__Нагрузки_и_воздействия"
GOST = "ГОСТ_10140-2003__Межгосударственный_стандарт__Плиты"

TYPED = [
    ("СП 54", "СП 54", SP54),                         # no-break space
    ("СП\t54", "СП 54", SP54),                             # tab
    ("СП  54", "СП 54", SP54),                   # em space and no-break space
    ("СНиП 2.01.07–85", "СНиП 2.01.07-85", SNIP),     # en dash
    ("СНиП 2.01.07—85", "СНиП 2.01.07-85", SNIP),  # no-break space, em dash
    ("ГОСТ 10140‐2003", "ГОСТ 10140-2003", GOST),     # U+2010 hyphen
    ("ГОСТ 10140‑2003", "ГОСТ 10140-2003", GOST),     # U+2011 non-breaking hyphen
    ("ГОСТ 10140‒2003", "ГОСТ 10140-2003", GOST),     # U+2012 figure dash
    ("ГОСТ 10140―2003", "ГОСТ 10140-2003", GOST),     # U+2015 horizontal bar
]


@pytest.mark.parametrize(("typed", "ascii", "slug"), TYPED)
def test_a_designation_is_rebuilt_with_ascii_separators(typed: str, ascii: str, slug: str) -> None:
    parsed = parse_query(typed)
    assert parsed.designation == ascii
    assert parsed == parse_query(ascii)
    wanted = _sql_tokens(parsed.designation)
    assert wanted and _sql_tokens(slug)[: len(wanted)] == wanted


def test_the_words_around_a_rebuilt_designation_are_kept() -> None:
    assert parse_query("СНиП 2.01.07–85 нагрузки") == parse_query(
        "СНиП 2.01.07-85 нагрузки"
    )
    assert parse_query("жилые здания СП 54").words == "жилые здания"


class _Recording(FakeNorms):
    """``FakeNorms`` that also keeps the parameters each search statement was bound with."""

    bound: list[dict[str, Any]]

    def answer(self, statement: Any, parameters: dict[str, Any]) -> Any:
        if "norm_designation_tokens(:designation)" in str(statement):
            self.bound.append(dict(parameters))
        return super().answer(statement, parameters)


@pytest.mark.parametrize(("typed", "ascii", "slug"), TYPED)
def test_the_search_binds_the_rebuilt_designation(typed: str, ascii: str, slug: str) -> None:
    database = _Recording()
    database.bound = []
    database.snapshots = {SNAPSHOT: (True, True)}
    database.designate(SNAPSHOT)
    service_module.search(
        database(),  # type: ignore[arg-type]
        q=typed, norms_snapshot_id=None, cursor=None, limit=10, timeout_ms=1000,
    )
    assert [parameters["designation"] for parameters in database.bound] == [ascii]
