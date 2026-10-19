"""The norms catalogue: the current snapshot's documents with readable display names.

`W57B-NORMS-CATALOGUE-XLSX-01`. Other contexts reach this package through
``auditmanager.norms.public`` only (ALR-05).
"""

from __future__ import annotations

from .cursor import catalogue_binding, decode_catalogue_cursor, encode_catalogue_cursor
from .designation import DisplayName, display_name
from .service import (
    MAX_KIND_CHARACTERS,
    MAX_LIMIT,
    MAX_QUERY_CHARACTERS,
    CatalogueEntry,
    CataloguePage,
    KindCount,
    list_documents,
)

__all__ = [
    "MAX_KIND_CHARACTERS",
    "MAX_LIMIT",
    "MAX_QUERY_CHARACTERS",
    "CatalogueEntry",
    "CataloguePage",
    "DisplayName",
    "KindCount",
    "catalogue_binding",
    "decode_catalogue_cursor",
    "display_name",
    "encode_catalogue_cursor",
    "list_documents",
]
