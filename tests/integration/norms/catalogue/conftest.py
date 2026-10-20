"""Fixtures for the catalogue window suite: the norms search window's own database fixtures.

`W57B-NORMS-CATALOGUE-XLSX-01`. The catalogue reads the same rows the search reads, so it
uses the same throwaway, migrated PostgreSQL database and the same plain-SQL ``Corpus``
writer (``tests/integration/norms/search/conftest.py``) rather than a second copy of them:
the rows are written by SQL, never by the code under test.
"""

from __future__ import annotations

from tests.integration.norms.search.conftest import (  # noqa: F401 - fixtures by import
    Corpus,
    corpus,
    search_database,
    search_engine,
)
