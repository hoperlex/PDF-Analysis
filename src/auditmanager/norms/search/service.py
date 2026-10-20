"""The norms reads: text search, a document, its paragraphs, the snapshots, the PDF binding.

`W55A-SEARCH-01` (`W55-PLAN.md` sections A3.4 and A3.6). Every function takes the caller's
session and returns frozen values of this module; the composition root's adapter maps them
into the transport shapes. Nothing here writes.

**Search.** ``q`` is parsed into a designation, a clause and words (:mod:`.query`):

* with words, reliable paragraphs whose ``text_tsv`` matches
  ``websearch_to_tsquery('russian', words)``, ranked by ``ts_rank_cd`` (descending), ties by
  ``npar_``; the designation and clause, when present, filter;
* without words, the reliable paragraphs of the matching documents and clauses, ordered by
  designation, then document, then ``ordinal``.

The candidates are cut to a **window of 1 000** in that order before any page is taken, so
paging never reaches past the thousandth hit. ``text_reliability = 'reliable'`` is a literal
of every search statement -- an unreliable paragraph is never a hit, and the literal is what
lets the planner use the partial indexes of ``0020``. The scope is the current snapshot, or
an explicit ``norms_snapshot_id`` that has been current at least once; otherwise
``required_norm_unavailable`` (``reference_kind: norms_snapshot``). The whole search runs under
``statement_timeout`` (``AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS``); a cancelled statement is
``validation_failed`` (``constraint: norms_search_too_broad``), never an empty or partial page.

Before any statement, a ``q`` holding a control character (other than tab, line feed and
carriage return) or with nothing to search for is ``validation_failed`` on ``q``
(``format``): a NUL cannot be bound, and a blank text would sort a whole snapshot
(`W55A-FIX`, JUDGE-X M2, M5; :func:`.query.unsearchable`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import NormDocumentId, NormsSnapshotId

from ..current_snapshot import (
    BUILD_COMPLETE_SQL,
    PDF_BINDING_SQL,
    QUALIFICATION_PARAMETERS,
    SOURCES_CONFIRMED_SQL,
    current_snapshot,
    has_been_current,
)
from .cursor import (
    DesignationPosition,
    ParagraphPosition,
    RankPosition,
    SnapshotPosition,
    decode_paragraph_cursor,
    decode_search_cursor,
    decode_snapshot_cursor,
    encode_paragraph_cursor,
    encode_search_cursor,
    encode_snapshot_cursor,
    query_binding,
)
from .display import reader_designation
from .fragment import (
    HEADLINE_OPTIONS,
    MARKERS,
    Fragment,
    fragment_from_headline,
    plain_fragment,
)
from .query import ParsedQuery, parse_query, unsearchable

__all__ = [
    "DocumentView",
    "PageOf",
    "ParagraphView",
    "PdfBinding",
    "SEARCH_WINDOW",
    "SearchHit",
    "SnapshotView",
    "get_document",
    "list_paragraphs",
    "list_snapshots",
    "pdf_binding",
    "resolve_scope",
    "search",
]

#: The most hits one search can reach, over all its pages (plan section A3.4).
SEARCH_WINDOW: Final[int] = 1000

#: PostgreSQL's ``query_canceled``: what ``statement_timeout`` raises.
_QUERY_CANCELED: Final[str] = "57014"


@dataclass(frozen=True, slots=True)
class SearchHit:
    norms_snapshot_id: str
    norm_document_id: str
    norm_paragraph_id: str
    designation: str
    title: str
    doc_type: str
    clause_number: str | None
    page_label: int
    block_ref: str
    fragment: Fragment
    source_attribution: str


@dataclass(frozen=True, slots=True)
class PageOf:
    items: tuple[Any, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class DocumentView:
    norm_document_id: str
    norms_snapshot_id: str
    designation: str
    title: str
    doc_type: str
    drawn_on: date | None
    pdf_page_count: int
    paragraph_count: int
    unreliable_paragraph_count: int
    content_available: bool
    source_attribution: str


@dataclass(frozen=True, slots=True)
class ParagraphView:
    norm_paragraph_id: str
    ordinal: int
    page_label: int
    block_ref: str
    kind: str
    clause_number: str | None
    text: str
    text_reliability: str


@dataclass(frozen=True, slots=True)
class SnapshotView:
    norms_snapshot_id: str
    content_key: str
    document_count: int
    paragraph_count: int
    unreliable_count: int
    #: ``complete``, ``incomplete`` or ``absent`` (``NormBuildState``).
    build_state: str
    #: Exactly :func:`auditmanager.norms.current_snapshot.qualification`'s answer.
    qualified: bool
    current: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PdfBinding:
    """The confirmed custody binding that serves one document's PDF, and its Blob facts."""

    norm_document_id: str
    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str


# --- scope ---------------------------------------------------------------------------------


def _no_snapshot(norms_snapshot_id: str | None = None) -> DomainError:
    details: dict[str, str] = {"reference_kind": "norms_snapshot"}
    if norms_snapshot_id is not None:
        details["norms_snapshot_id"] = norms_snapshot_id
    return DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE, **details)


def resolve_scope(session: Session, norms_snapshot_id: str | None) -> str:
    """The snapshot a search reads: the named one if it has ever been current, else the
    current one; ``required_norm_unavailable`` when neither exists."""
    if norms_snapshot_id is not None:
        named = str(NormsSnapshotId.parse(norms_snapshot_id))
        if not has_been_current(session, named):
            raise _no_snapshot(named)
        return named
    current = current_snapshot(session)
    if current is None:
        raise _no_snapshot()
    return current.norms_snapshot_id


# --- search --------------------------------------------------------------------------------

_DESIGNATION_FILTER: Final[str] = """
       AND d.designation_tokens @> norm_designation_tokens(:designation)
       AND d.designation_tokens[1:cardinality(norm_designation_tokens(:designation))]
           = norm_designation_tokens(:designation)
"""

_CLAUSE_FILTER: Final[str] = """
       AND p.clause_number IS NOT NULL
       AND (p.clause_number = :clause OR p.clause_number LIKE :clause_prefix)
"""

_HIT_COLUMNS: Final[str] = """
       p.norm_paragraph_id, d.norm_document_id, d.slug, d.title, d.doc_type,
       d.source_attribution, p.clause_number, p.page_label, p.block_ref, p.ordinal, p.text
"""


def _ranked_sql(parsed: ParsedQuery) -> str:
    designation = _DESIGNATION_FILTER if parsed.designation is not None else ""
    clause = _CLAUSE_FILTER if parsed.clause is not None else ""
    return f"""
    WITH tsq AS (
        SELECT websearch_to_tsquery('russian'::regconfig, :words) AS query
    ),
    hits AS (
        SELECT p.norm_paragraph_id, p.norms_snapshot_id, p.norm_document_pk,
               ts_rank_cd(p.text_tsv, tsq.query) AS hit_rank
          FROM norm_paragraph p
          JOIN norm_document d
            ON d.norms_snapshot_id = p.norms_snapshot_id
           AND d.norm_document_pk = p.norm_document_pk
         CROSS JOIN tsq
         WHERE p.norms_snapshot_id = :snapshot
           AND p.text_reliability = 'reliable'
           AND p.text_tsv @@ tsq.query
           {designation}
           {clause}
         ORDER BY hit_rank DESC, p.norm_paragraph_id COLLATE "C"
         LIMIT :search_window
    ),
    page AS (
        SELECT h.* FROM hits h
         WHERE CAST(:after_rank AS real) IS NULL
            OR h.hit_rank < CAST(:after_rank AS real)
            OR (h.hit_rank = CAST(:after_rank AS real)
                AND h.norm_paragraph_id COLLATE "C" > CAST(:after_id AS text) COLLATE "C")
         ORDER BY h.hit_rank DESC, h.norm_paragraph_id COLLATE "C"
         LIMIT :page_limit
    )
    SELECT h.hit_rank, {_HIT_COLUMNS},
           ts_headline('russian'::regconfig, translate(p.text, :markers, ''), tsq.query,
                       :headline_options) AS headline
      FROM page h
      JOIN norm_paragraph p ON p.norm_paragraph_id = h.norm_paragraph_id
      JOIN norm_document d
        ON d.norms_snapshot_id = p.norms_snapshot_id
       AND d.norm_document_pk = p.norm_document_pk
     CROSS JOIN tsq
     ORDER BY h.hit_rank DESC, h.norm_paragraph_id COLLATE "C"
    """


def _ordered_sql(parsed: ParsedQuery) -> str:
    designation = _DESIGNATION_FILTER if parsed.designation is not None else ""
    clause = _CLAUSE_FILTER if parsed.clause is not None else ""
    return f"""
    WITH hits AS (
        SELECT p.norm_paragraph_id, d.norm_document_id, p.ordinal,
               array_to_string(d.designation_tokens, ' ') COLLATE "C" AS designation_key
          FROM norm_paragraph p
          JOIN norm_document d
            ON d.norms_snapshot_id = p.norms_snapshot_id
           AND d.norm_document_pk = p.norm_document_pk
         WHERE p.norms_snapshot_id = :snapshot
           AND p.text_reliability = 'reliable'
           {designation}
           {clause}
         ORDER BY designation_key, d.norm_document_id COLLATE "C", p.ordinal
         LIMIT :search_window
    ),
    page AS (
        SELECT h.* FROM hits h
         WHERE CAST(:after_document AS text) IS NULL
            OR (h.designation_key COLLATE "C", h.norm_document_id COLLATE "C", h.ordinal)
               > ((SELECT array_to_string(ad.designation_tokens, ' ')
                     FROM norm_document ad
                    WHERE ad.norm_document_id = CAST(:after_document AS text)) COLLATE "C",
                  CAST(:after_document AS text) COLLATE "C",
                  CAST(:after_ordinal AS integer))
         ORDER BY h.designation_key COLLATE "C", h.norm_document_id COLLATE "C", h.ordinal
         LIMIT :page_limit
    )
    SELECT {_HIT_COLUMNS}
      FROM page h
      JOIN norm_paragraph p ON p.norm_paragraph_id = h.norm_paragraph_id
      JOIN norm_document d
        ON d.norms_snapshot_id = p.norms_snapshot_id
       AND d.norm_document_pk = p.norm_document_pk
     ORDER BY h.designation_key COLLATE "C", h.norm_document_id COLLATE "C", h.ordinal
    """


_SET_TIMEOUT = text("SELECT set_config('statement_timeout', :timeout, true)")


def _too_broad() -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The search took longer than this deployment allows; narrow the query.",
        field="q",
        constraint="norms_search_too_broad",
    )


def _unsearchable() -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The search text holds a control character or nothing to search for.",
        field="q",
        constraint="format",
    )


def _cancelled(exc: OperationalError) -> bool:
    return str(getattr(exc.orig, "sqlstate", "") or "") == _QUERY_CANCELED


def search(
    session: Session,
    *,
    q: str,
    norms_snapshot_id: str | None,
    cursor: str | None,
    limit: int,
    timeout_ms: int,
) -> PageOf:
    """One page of hits; see the module docstring."""
    if timeout_ms <= 0:  # pragma: no cover - settings refuse it first
        raise ValueError("the norms search timeout must be positive")
    if unsearchable(q):
        raise _unsearchable()
    parsed = parse_query(q)
    try:
        session.execute(_SET_TIMEOUT, {"timeout": str(int(timeout_ms))})
        snapshot = resolve_scope(session, norms_snapshot_id)
        binding = query_binding(q, snapshot)
        after = (
            None if cursor is None
            else decode_search_cursor(cursor, binding=binding, ranked=parsed.ranked)
        )
        rows = _search_rows(session, parsed, snapshot, after, limit)
    except OperationalError as exc:
        if _cancelled(exc):
            raise _too_broad() from None
        raise

    has_more = len(rows) > limit
    rows = rows[:limit]
    items = tuple(_hit(row, snapshot, parsed) for row in rows)
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        position: RankPosition | DesignationPosition = (
            RankPosition(float(last.hit_rank), str(last.norm_paragraph_id))
            if parsed.ranked
            else DesignationPosition(
                str(last.norm_document_id), int(last.ordinal), str(last.norm_paragraph_id)
            )
        )
        next_cursor = encode_search_cursor(binding, position)
    return PageOf(items=items, next_cursor=next_cursor)


def _search_rows(
    session: Session,
    parsed: ParsedQuery,
    snapshot: str,
    after: RankPosition | DesignationPosition | None,
    limit: int,
) -> Sequence[Any]:
    parameters: dict[str, Any] = {
        "snapshot": snapshot,
        "search_window": SEARCH_WINDOW,
        "page_limit": limit + 1,
    }
    if parsed.designation is not None:
        parameters["designation"] = parsed.designation
    if parsed.clause is not None:
        parameters["clause"] = parsed.clause
        parameters["clause_prefix"] = f"{parsed.clause}.%"
    if parsed.ranked:
        assert after is None or isinstance(after, RankPosition)
        parameters |= {
            "words": parsed.words,
            "markers": MARKERS,
            "headline_options": HEADLINE_OPTIONS,
            "after_rank": None if after is None else after.rank,
            "after_id": None if after is None else after.norm_paragraph_id,
        }
        return session.execute(text(_ranked_sql(parsed)), parameters).all()
    assert after is None or isinstance(after, DesignationPosition)
    parameters |= {
        "after_document": None if after is None else after.norm_document_id,
        "after_ordinal": None if after is None else after.ordinal,
    }
    return session.execute(text(_ordered_sql(parsed)), parameters).all()


def _hit(row: Any, snapshot: str, parsed: ParsedQuery) -> SearchHit:
    paragraph_text = str(row.text)
    fragment = (
        fragment_from_headline(str(row.headline or ""), fallback=paragraph_text)
        if parsed.ranked
        else plain_fragment(paragraph_text)
    )
    return SearchHit(
        norms_snapshot_id=snapshot,
        norm_document_id=str(row.norm_document_id),
        norm_paragraph_id=str(row.norm_paragraph_id),
        designation=reader_designation(str(row.slug)),
        title=str(row.title),
        doc_type=str(row.doc_type),
        clause_number=None if row.clause_number is None else str(row.clause_number),
        page_label=int(row.page_label),
        block_ref=str(row.block_ref),
        fragment=fragment,
        source_attribution=str(row.source_attribution),
    )


# --- one document and its paragraphs -------------------------------------------------------

_DOCUMENT = text(
    f"""
    SELECT d.norm_document_id, d.norms_snapshot_id, d.slug, d.title, d.doc_type, d.drawn_on,
           d.pdf_page_count, d.paragraph_count, d.source_attribution,
           (SELECT count(*) FROM norm_paragraph up
             WHERE up.norms_snapshot_id = d.norms_snapshot_id
               AND up.norm_document_pk = d.norm_document_pk
               AND up.text_reliability = 'unreliable') AS unreliable_paragraph_count,
           EXISTS ({PDF_BINDING_SQL}) AS content_available
      FROM norm_document d
     WHERE d.norm_document_id = :document
    """
)

_PARAGRAPHS = text(
    """
    SELECT p.norm_paragraph_id, p.ordinal, p.page_label, p.block_ref, p.kind,
           p.clause_number, p.text, p.text_reliability
      FROM norm_paragraph p
      JOIN norm_document d
        ON d.norms_snapshot_id = p.norms_snapshot_id
       AND d.norm_document_pk = p.norm_document_pk
     WHERE d.norm_document_id = :document
       AND p.ordinal > :after_ordinal
     ORDER BY p.ordinal
     LIMIT :row_limit
    """
)


def _document_not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type="NormDocument")


def _parse_document_id(norm_document_id: str) -> str:
    return str(NormDocumentId.parse(norm_document_id))


def get_document(session: Session, norm_document_id: str) -> DocumentView:
    """One document of any loaded snapshot; ``not_found`` for an identity naming nothing."""
    row = session.execute(
        _DOCUMENT,
        {"document": _parse_document_id(norm_document_id), **QUALIFICATION_PARAMETERS},
    ).one_or_none()
    if row is None:
        raise _document_not_found()
    return DocumentView(
        norm_document_id=str(row.norm_document_id),
        norms_snapshot_id=str(row.norms_snapshot_id),
        designation=reader_designation(str(row.slug)),
        title=str(row.title),
        doc_type=str(row.doc_type),
        drawn_on=row.drawn_on,
        pdf_page_count=int(row.pdf_page_count),
        paragraph_count=int(row.paragraph_count),
        unreliable_paragraph_count=int(row.unreliable_paragraph_count),
        content_available=bool(row.content_available),
        source_attribution=str(row.source_attribution),
    )


def list_paragraphs(
    session: Session, norm_document_id: str, *, cursor: str | None, limit: int
) -> tuple[DocumentView, PageOf]:
    """The document and one page of its paragraphs by ``ordinal``, unreliable ones included
    and marked by ``text_reliability``."""
    document = get_document(session, norm_document_id)
    after = (
        None if cursor is None
        else decode_paragraph_cursor(cursor, norm_document_id=document.norm_document_id)
    )
    rows = session.execute(
        _PARAGRAPHS,
        {
            "document": document.norm_document_id,
            "after_ordinal": -1 if after is None else after.ordinal,
            "row_limit": limit + 1,
        },
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = tuple(
        ParagraphView(
            norm_paragraph_id=str(row.norm_paragraph_id),
            ordinal=int(row.ordinal),
            page_label=int(row.page_label),
            block_ref=str(row.block_ref),
            kind=str(row.kind),
            clause_number=None if row.clause_number is None else str(row.clause_number),
            text=str(row.text),
            text_reliability=str(row.text_reliability),
        )
        for row in rows
    )
    next_cursor = (
        encode_paragraph_cursor(ParagraphPosition(document.norm_document_id, items[-1].ordinal))
        if has_more and items
        else None
    )
    return document, PageOf(items=items, next_cursor=next_cursor)


# --- the snapshots -------------------------------------------------------------------------

_SNAPSHOTS = text(
    f"""
    SELECT s.norms_snapshot_id, s.content_key, s.document_count, s.unreliable_count,
           s.created_at,
           COALESCE((SELECT sum(pd.paragraph_count) FROM norm_document pd
                      WHERE pd.norms_snapshot_id = s.norms_snapshot_id), 0) AS paragraph_count,
           ({BUILD_COMPLETE_SQL}) AS build_complete,
           ({SOURCES_CONFIRMED_SQL}) AS sources_confirmed,
           (EXISTS (SELECT 1 FROM norm_embedding_build ab
                     WHERE ab.norms_snapshot_id = s.norms_snapshot_id)
            OR EXISTS (SELECT 1 FROM norm_chunk_build cb
                        WHERE cb.norms_snapshot_id = s.norms_snapshot_id
                          AND cb.chunking_profile LIKE :q_reliable_chunking)) AS build_started,
           EXISTS (SELECT 1 FROM norm_current_snapshot c
                    WHERE c.norms_snapshot_id = s.norms_snapshot_id) AS is_current
      FROM norms_snapshot s
     WHERE CAST(:after_at AS timestamptz) IS NULL
        OR (s.created_at, s.norms_snapshot_id COLLATE "C")
           < (CAST(:after_at AS timestamptz), CAST(:after_id AS text) COLLATE "C")
     ORDER BY s.created_at DESC, s.norms_snapshot_id COLLATE "C" DESC
     LIMIT :row_limit
    """
)


def build_state(*, build_complete: bool, build_started: bool) -> str:
    """``complete`` (condition (a) holds), ``incomplete`` (a reliability-aware chunk build or
    some embedding build exists, but not the qualifying one) or ``absent``."""
    if build_complete:
        return "complete"
    return "incomplete" if build_started else "absent"


def list_snapshots(session: Session, *, cursor: str | None, limit: int) -> PageOf:
    """Every loaded snapshot, newest first, with the setter's own qualification."""
    after: SnapshotPosition | None = None if cursor is None else decode_snapshot_cursor(cursor)
    rows = session.execute(
        _SNAPSHOTS,
        {
            "after_at": None if after is None else after.created_at,
            "after_id": None if after is None else after.norms_snapshot_id,
            "row_limit": limit + 1,
            **QUALIFICATION_PARAMETERS,
        },
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = tuple(
        SnapshotView(
            norms_snapshot_id=str(row.norms_snapshot_id),
            content_key=str(row.content_key),
            document_count=int(row.document_count),
            paragraph_count=int(row.paragraph_count),
            unreliable_count=int(row.unreliable_count),
            build_state=build_state(
                build_complete=bool(row.build_complete), build_started=bool(row.build_started)
            ),
            qualified=bool(row.build_complete) and bool(row.sources_confirmed),
            current=bool(row.is_current),
            created_at=row.created_at,
        )
        for row in rows
    )
    next_cursor = (
        encode_snapshot_cursor(
            SnapshotPosition(items[-1].created_at, items[-1].norms_snapshot_id)
        )
        if has_more and items
        else None
    )
    return PageOf(items=items, next_cursor=next_cursor)


# --- the PDF -------------------------------------------------------------------------------

_PDF_BINDING = text(
    f"""
    SELECT d.norm_document_id, b.blob_id, b.sha256, b.size_bytes, b.media_type
      FROM norm_document d
      LEFT JOIN blob b ON b.blob_id = ({PDF_BINDING_SQL})
     WHERE d.norm_document_id = :document
    """
)


def pdf_binding(session: Session, norm_document_id: str) -> PdfBinding:
    """The confirmed binding of the document's PDF; ``not_found`` for an unknown document and
    ``required_norm_unavailable`` (``reference_kind: norm_source``) for one without it."""
    row = session.execute(
        _PDF_BINDING,
        {"document": _parse_document_id(norm_document_id), **QUALIFICATION_PARAMETERS},
    ).one_or_none()
    if row is None:
        raise _document_not_found()
    if row.blob_id is None or row.sha256 is None or row.size_bytes is None:
        raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE, reference_kind="norm_source")
    return PdfBinding(
        norm_document_id=str(row.norm_document_id),
        blob_id=str(row.blob_id),
        sha256=str(row.sha256),
        size_bytes=int(row.size_bytes),
        media_type=str(row.media_type),
    )
