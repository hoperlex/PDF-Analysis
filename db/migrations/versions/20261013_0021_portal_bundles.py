"""Portal bundles: the page ceiling moves to 500 and a version records its text counts.

Revision ID: 0021_portal_bundles
Revises: 0020_norms_search

`W55B-SEAL-01` (`W55-PLAN.md` section B3.2; owner ruling R-116).

* ``ck_document_version_page_count`` widens from 1..30 to 1..500. The envelope's admission
  probe is the first guard and the message; the CHECK stays the backstop. No existing row
  is affected: every version published so far has at most 30 pages.
* ``document_version`` gains three **nullable** columns, ``NULL`` for every version that
  predates the bundle upload:

  - ``text_character_count`` -- pypdfium2's character count over the whole document. The
    analysis input budget (G-11) is checked against it, so it is a **count of characters of
    pypdfium2's reading**, which includes generated line breaks and differs from
    pdfplumber's text layer. It is a budget input, never a statement about the text.
  - ``textless_pages`` -- the ascending, 1-based numbers of the pages whose pypdfium2
    character count is below the threshold ``W55B-FREEZE-01`` pins (50); empty when no page
    qualifies. ``W56-PLAN.md`` section A9 reads it to tell a raster page from a page that is
    merely short.
  - ``recognised_character_count`` -- the characters of recognised text the portal's
    ``_results.md`` holds for those pages.

  The three are all ``NULL`` or all set: a version carrying a count without the page list
  that explains it would be a partial record, and a published version is immutable, so the
  database refuses the half-written row instead of leaving it to be found later. The page
  list is checked by an ``IMMUTABLE`` function -- 1-based, strictly ascending, within the
  page count -- because a ``CHECK`` cannot contain a subquery.

Adding a column or replacing a ``CHECK`` fires no row trigger, so the immutability triggers
of ``0002`` are not engaged and no existing row is rewritten by the columns.

A populated 0021 is not downgraded: a version above 30 pages or one that carries any of the
three counts refuses it, and a database backup is restored instead. A database that holds
neither is returned to the 1..30 ceiling and loses only the empty columns.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from alembic import op
from sqlalchemy import text

revision: str = "0021_portal_bundles"
down_revision: str | None = "0020_norms_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The ceiling this revision introduces and the one a clean downgrade returns to.
NEW_MAX_PAGES: Final[int] = 500
OLD_MAX_PAGES: Final[int] = 30

_PAGE_LIST_FUNCTION = "am_is_ascending_page_list"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE FUNCTION {_PAGE_LIST_FUNCTION}(pages integer[], page_count integer)
        RETURNS boolean
        LANGUAGE sql IMMUTABLE PARALLEL SAFE
        AS $fn$
            SELECT cardinality(pages) = 0
                OR (
                    array_ndims(pages) = 1
                    AND page_count IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1
                        FROM generate_subscripts(pages, 1) AS i
                        WHERE pages[i] IS NULL
                           OR pages[i] < 1
                           OR pages[i] > page_count
                           OR (i > array_lower(pages, 1) AND pages[i] <= pages[i - 1])
                    )
                )
        $fn$
        """
    )
    op.execute(
        f"COMMENT ON FUNCTION {_PAGE_LIST_FUNCTION}(integer[], integer) IS "
        "'True for an empty list, or a one-dimensional list of 1-based page numbers that is "
        "strictly ascending and within the page count. IMMUTABLE so a CHECK may call it.';"
    )

    op.execute("ALTER TABLE document_version DROP CONSTRAINT ck_document_version_page_count")
    op.execute(
        "ALTER TABLE document_version ADD CONSTRAINT ck_document_version_page_count "
        f"CHECK (page_count BETWEEN 1 AND {NEW_MAX_PAGES})"
    )
    op.execute(
        "COMMENT ON COLUMN document_version.page_count IS "
        f"'Bounded by the portal-bundle envelope: at most {NEW_MAX_PAGES} pages. An "
        "over-page-count file is refused by the admission probe with validation_failed "
        "before it reaches this table; the CHECK is the backstop, not the message.';"
    )

    op.execute(
        "ALTER TABLE document_version "
        "ADD COLUMN text_character_count integer NULL, "
        "ADD COLUMN textless_pages integer[] NULL, "
        "ADD COLUMN recognised_character_count integer NULL"
    )
    op.execute(
        "ALTER TABLE document_version "
        "ADD CONSTRAINT ck_document_version_text_character_count "
        "CHECK (text_character_count IS NULL OR text_character_count >= 0), "
        "ADD CONSTRAINT ck_document_version_recognised_character_count "
        "CHECK (recognised_character_count IS NULL OR recognised_character_count >= 0), "
        "ADD CONSTRAINT ck_document_version_textless_pages "
        f"CHECK (textless_pages IS NULL OR {_PAGE_LIST_FUNCTION}(textless_pages, page_count)), "
        "ADD CONSTRAINT ck_document_version_bundle_counts_together "
        "CHECK ((text_character_count IS NULL) = (textless_pages IS NULL) "
        "AND (text_character_count IS NULL) = (recognised_character_count IS NULL))"
    )
    op.execute(
        "COMMENT ON COLUMN document_version.text_character_count IS "
        "'G-11 analysis input budget input: the character count of the whole document as "
        "pypdfium2 reads it (generated line breaks included; not pdfplumber''s text layer). "
        "NULL for a version that predates the portal-bundle upload.';"
    )
    op.execute(
        "COMMENT ON COLUMN document_version.textless_pages IS "
        "'Ascending 1-based numbers of the pages whose pypdfium2 character count is below "
        "the frozen threshold; empty when none; NULL before the portal-bundle upload.';"
    )
    op.execute(
        "COMMENT ON COLUMN document_version.recognised_character_count IS "
        "'Characters of recognised text the portal results hold for the textless pages. "
        "NULL before the portal-bundle upload.';"
    )


# --- downgrade ----------------------------------------------------------------------------

_RETAINED_DATA: Final[tuple[tuple[str, str], ...]] = (
    (
        f"a version above {OLD_MAX_PAGES} pages",
        f"SELECT EXISTS (SELECT 1 FROM document_version WHERE page_count > {OLD_MAX_PAGES})",
    ),
    (
        "a version carrying its text counts",
        "SELECT EXISTS (SELECT 1 FROM document_version WHERE text_character_count IS NOT NULL "
        "OR textless_pages IS NOT NULL OR recognised_character_count IS NOT NULL)",
    ),
)


def downgrade() -> None:
    bind = op.get_bind()
    retained = [name for name, probe in _RETAINED_DATA if bind.execute(text(probe)).scalar_one()]
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0021_portal_bundles with retained portal-bundle data "
            f"({'; '.join(retained)}); restore a database backup instead"
        )
    op.execute(
        "ALTER TABLE document_version "
        "DROP CONSTRAINT ck_document_version_bundle_counts_together, "
        "DROP CONSTRAINT ck_document_version_textless_pages, "
        "DROP CONSTRAINT ck_document_version_recognised_character_count, "
        "DROP CONSTRAINT ck_document_version_text_character_count"
    )
    op.execute(
        "ALTER TABLE document_version "
        "DROP COLUMN recognised_character_count, "
        "DROP COLUMN textless_pages, "
        "DROP COLUMN text_character_count"
    )
    op.execute(f"DROP FUNCTION {_PAGE_LIST_FUNCTION}(integer[], integer)")
    op.execute("ALTER TABLE document_version DROP CONSTRAINT ck_document_version_page_count")
    op.execute(
        "ALTER TABLE document_version ADD CONSTRAINT ck_document_version_page_count "
        f"CHECK (page_count BETWEEN 1 AND {OLD_MAX_PAGES})"
    )
    op.execute(
        "COMMENT ON COLUMN document_version.page_count IS "
        f"'Bounded by the PC-01 input envelope: at most {OLD_MAX_PAGES} pages. An "
        "over-page-count file is refused by the admission probe with validation_failed "
        "before it reaches this table; the CHECK is the backstop, not the message.';"
    )
