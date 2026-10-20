"""The norms catalogue: every document of the current snapshot, filtered, sorted and paged.

`W57B-NORMS-CATALOGUE-XLSX-01`. One read, nothing written. The scope is the current
snapshot (:func:`auditmanager.norms.search.resolve_scope`); with none current the answer is
``required_norm_unavailable`` with ``reference_kind: norms_snapshot``, exactly as
``searchNorms`` answers, never an empty page.

**One statement, then pure work.** The snapshot's documents are read in one ``SELECT``
(identity, slug, kind, page and paragraph counts, attribution and ``content_available`` --
the same custody-binding expression ``getNormDocument`` evaluates). On the real corpus that is
674 rows in about 6 ms. Everything after it is a function of those rows: the display name
(:func:`auditmanager.norms.search.display_name`, whose designation ``searchNorms`` and
``getNormDocument`` show too), the filters, the order and the page. So the filters match what
a reader sees -- the derived designation and title -- and a row is never altered.

* ``q`` (1-200 characters) keeps a document when its designation and title, folded like the
  search's designations (case, ``ё``, Latin homoglyphs) with every run of punctuation as one
  space, contain ``q`` folded the same way **from the start of a word**, and a ``q`` ending in
  a digit ends a number there: ``24.04.2013`` finds ``от 24.04.2013``, ``СП 54.13330`` finds
  ``СП 54.13330.2022``, ``огнест`` finds ``огнестойкость``, while ``54`` finds neither ``154``
  nor ``542`` -- as ``searchNorms`` never finds ``СП 542`` for ``СП 54``.
  A ``q`` holding a control character, or nothing but punctuation, is ``validation_failed``
  on ``q`` (``format``).
* ``kind`` (1-100 characters) keeps documents whose stored ``doc_type`` equals it. An unknown
  kind is an empty page; ``kinds`` lists the snapshot's kinds and their counts.
* The order is by designation, natural and folded (``СП 2…`` before ``СП 10…``), then title,
  then identity, so it is total and stable.
* Paging is by an opaque cursor bound to ``(q, kind, snapshot)`` (:mod:`.cursor`); ``total``
  is the count of documents the filters keep.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

from ..current_snapshot import PDF_BINDING_SQL, QUALIFICATION_PARAMETERS
from ..search import display_name, fold, resolve_scope
from .cursor import (
    catalogue_binding,
    decode_catalogue_cursor,
    encode_catalogue_cursor,
    refused,
)

__all__ = [
    "CatalogueEntry",
    "CataloguePage",
    "KindCount",
    "MAX_KIND_CHARACTERS",
    "MAX_LIMIT",
    "MAX_QUERY_CHARACTERS",
    "list_documents",
    "matches",
    "sort_key",
]

#: ``q``'s and ``kind``'s declared bounds; the router enforces them, this restates them.
MAX_QUERY_CHARACTERS: Final[int] = 200
MAX_KIND_CHARACTERS: Final[int] = 100
#: The largest page; the router's ``limit`` bound.
MAX_LIMIT: Final[int] = 200

_DOCUMENTS = text(
    f"""
    SELECT d.norm_document_id, d.slug, d.doc_type, d.pdf_page_count, d.paragraph_count,
           d.source_attribution,
           EXISTS ({PDF_BINDING_SQL}) AS content_available
      FROM norm_document d
     WHERE d.norms_snapshot_id = :snapshot
     ORDER BY d.norm_document_id COLLATE "C"
    """
)

_PUNCTUATION: Final[re.Pattern[str]] = re.compile(r"[\W_]+")
_NUMBER_OR_TEXT: Final[re.Pattern[str]] = re.compile(r"\d+|\D+")
_WHITESPACE_CONTROLS: Final[frozenset[str]] = frozenset("\t\n\r")


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    norm_document_id: str
    #: The derived display designation (:func:`.designation.display_name`).
    designation: str
    #: The rest of the file name, or ``None`` when it carries nothing more.
    title: str | None
    #: ``norm_document.doc_type``, verbatim.
    kind: str
    page_count: int
    paragraph_count: int
    content_available: bool
    source_attribution: str


@dataclass(frozen=True, slots=True)
class KindCount:
    kind: str
    document_count: int


@dataclass(frozen=True, slots=True)
class CataloguePage:
    norms_snapshot_id: str
    items: tuple[CatalogueEntry, ...]
    next_cursor: str | None
    #: The documents the filters keep, over every page.
    total: int
    #: Every kind of the snapshot with its document count, most documents first.
    kinds: tuple[KindCount, ...]


def _searchable(value: str) -> str:
    """``value`` folded like a designation, every run of punctuation one space."""
    return " ".join(_PUNCTUATION.sub(" ", fold(value).casefold()).split())


def matches(entry: CatalogueEntry, needle: str) -> bool:
    """Whether a folded, non-empty ``needle`` starts a word of the entry's display text and,
    when it ends in a digit, ends a number there too."""
    haystack = _searchable(f"{entry.designation} {entry.title or ''}")
    numeric_end = needle[-1].isdigit()
    start = haystack.find(needle)
    while start != -1:
        end = start + len(needle)
        if (start == 0 or haystack[start - 1] == " ") and not (
            numeric_end and end < len(haystack) and haystack[end].isdigit()
        ):
            return True
        start = haystack.find(needle, start + 1)
    return False


def sort_key(entry: CatalogueEntry) -> tuple[Any, ...]:
    """Natural, folded designation order; then title; then identity (total)."""
    return (
        _natural(entry.designation),
        _natural(entry.title or ""),
        entry.norm_document_id,
    )


def _natural(value: str) -> tuple[tuple[int, int, str], ...]:
    folded = _searchable(value)
    return tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in _NUMBER_OR_TEXT.findall(folded)
    )


def _format_refused(field: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=f"The {field} parameter holds a control character or nothing to filter by.",
        field=field,
        constraint="format",
    )


def _has_control(value: str) -> bool:
    for character in value:
        category = unicodedata.category(character)
        if category == "Cs" or (category == "Cc" and character not in _WHITESPACE_CONTROLS):
            return True
    return False


def _needle(q: str | None) -> str | None:
    if q is None:
        return None
    if not 1 <= len(q) <= MAX_QUERY_CHARACTERS or _has_control(q):
        raise _format_refused("q")
    needle = _searchable(q)
    if not needle:
        raise _format_refused("q")
    return needle


def _kind(kind: str | None) -> str | None:
    if kind is None:
        return None
    if not 1 <= len(kind) <= MAX_KIND_CHARACTERS or _has_control(kind) or not kind.strip():
        raise _format_refused("kind")
    return kind


def _entry(row: Any) -> CatalogueEntry:
    name = display_name(str(row.slug))
    return CatalogueEntry(
        norm_document_id=str(row.norm_document_id),
        designation=name.designation,
        title=name.title,
        kind=str(row.doc_type),
        page_count=int(row.pdf_page_count),
        paragraph_count=int(row.paragraph_count),
        content_available=bool(row.content_available),
        source_attribution=str(row.source_attribution),
    )


def _kinds(entries: Sequence[CatalogueEntry]) -> tuple[KindCount, ...]:
    counted = Counter(entry.kind for entry in entries)
    return tuple(
        KindCount(kind=kind, document_count=count)
        for kind, count in sorted(counted.items(), key=lambda item: (-item[1], item[0]))
    )


def list_documents(
    session: Session,
    *,
    q: str | None,
    kind: str | None,
    cursor: str | None,
    limit: int,
) -> CataloguePage:
    """One page of the current snapshot's catalogue; see the module docstring."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError("the catalogue limit is outside 1..MAX_LIMIT")
    needle = _needle(q)
    wanted_kind = _kind(kind)
    snapshot = resolve_scope(session, None)
    binding = catalogue_binding(q, kind, snapshot)
    after = None if cursor is None else decode_catalogue_cursor(cursor, binding=binding)

    rows = session.execute(
        _DOCUMENTS, {"snapshot": snapshot, **QUALIFICATION_PARAMETERS}
    ).all()
    entries = [_entry(row) for row in rows]
    kept = sorted(
        (
            entry for entry in entries
            if (wanted_kind is None or entry.kind == wanted_kind)
            and (needle is None or matches(entry, needle))
        ),
        key=sort_key,
    )

    start = 0
    if after is not None:
        positions = {entry.norm_document_id: index for index, entry in enumerate(kept)}
        if after not in positions:
            raise refused()
        start = positions[after] + 1
    page = tuple(kept[start:start + limit])
    has_more = start + limit < len(kept)
    next_cursor = (
        encode_catalogue_cursor(binding, page[-1].norm_document_id)
        if has_more and page
        else None
    )
    return CataloguePage(
        norms_snapshot_id=snapshot,
        items=page,
        next_cursor=next_cursor,
        total=len(kept),
        kinds=_kinds(entries),
    )
