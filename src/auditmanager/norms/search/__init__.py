"""Text search over the current norms snapshot, and the reads the «Нормы» screen makes.

`W55A-SEARCH-01` (`W55-PLAN.md` sections A3.4 and A3.6). Other contexts reach this package
through ``auditmanager.norms.public`` only (ALR-05).
"""

from __future__ import annotations

from .cursor import EventPosition, decode_event_cursor, encode_event_cursor
from .fragment import Fragment
from .query import DESIGNATION_TYPES, ParsedQuery, designation_of, fold, parse_query
from .service import (
    SEARCH_WINDOW,
    DocumentView,
    PageOf,
    ParagraphView,
    PdfBinding,
    SearchHit,
    SnapshotView,
    get_document,
    list_paragraphs,
    list_snapshots,
    pdf_binding,
    resolve_scope,
    search,
)

__all__ = [
    "DESIGNATION_TYPES",
    "SEARCH_WINDOW",
    "DocumentView",
    "EventPosition",
    "Fragment",
    "PageOf",
    "ParagraphView",
    "ParsedQuery",
    "PdfBinding",
    "SearchHit",
    "SnapshotView",
    "decode_event_cursor",
    "designation_of",
    "encode_event_cursor",
    "fold",
    "get_document",
    "list_paragraphs",
    "list_snapshots",
    "parse_query",
    "pdf_binding",
    "resolve_scope",
    "search",
]
