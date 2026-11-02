"""Allow comparison page numbers above the former 500-page application quota.

Revision ID: 0045_comparison_page_bounds
Revises: 0044_section_stats_uncapped

``0044`` let ``document_version.page_count`` exceed 500, and with ``AUDITMANAGER_INTAKE_RELAXED=1`` the
comparison reader (``comparison.version_reader.MAX_VERSION_PAGES``) admits such a version. The comparison
tables created in ``0035``, ``0038``, ``0039`` and ``0040`` still carried ``BETWEEN 1 AND 500`` on every
page coordinate, so the first page profile, sheet pair, AI link or manual edit above page 500 was refused
by the database instead of by a typed application refusal (code review 2026-11-02, S2-blocks-4-9-02).

This revision replaces the seven page-coordinate CHECKs in place (same names, same count) by their
lower bound alone. The upper bound of a stored coordinate is not lost: the ``NEW.<page> <= page_count``
triggers ``am_check_comparison_sheet_link_chain``, ``am_check_comparison_page_profile``,
``am_check_comparison_matrix_edit_chain``, ``am_check_comparison_ai_link`` and
``am_check_comparison_ai_pair_question`` tie each coordinate to the immutable version it belongs to, and
``0044`` makes that version's own ``page_count`` positive without a ceiling. ``declared_page_count`` of an
upload file is only a declaration and keeps just its lower bound.
``ck_comparison_version_order_versions_is_array`` reuses the constant ``500`` for the number of versions in
one order; it is not a page bound and is unchanged.

Downgrade refuses while any row holds a page coordinate above 500, because the restored CHECKs would
reject it; it never rewrites or deletes a row.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0045_comparison_page_bounds"
down_revision: str | None = "0044_section_stats_uncapped"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FORMER_MAXIMUM = 500

#: (table, constraint, relaxed condition, former condition, columns the former condition bounds).
PAGE_CHECKS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("comparison_sheet_link", "ck_comparison_sheet_link_source_page_number",
     "source_page_number >= 1",
     "source_page_number BETWEEN 1 AND 500",
     ("source_page_number",)),
    ("comparison_sheet_link", "ck_comparison_sheet_link_target_page_number",
     "target_page_number >= 1",
     "target_page_number BETWEEN 1 AND 500",
     ("target_page_number",)),
    ("comparison_upload_file", "ck_comparison_upload_file_declared_page_count",
     "declared_page_count IS NULL OR declared_page_count >= 1",
     "declared_page_count IS NULL OR declared_page_count BETWEEN 1 AND 500",
     ("declared_page_count",)),
    ("comparison_page_profile", "ck_comparison_page_profile_page_number",
     "page_number >= 1",
     "page_number BETWEEN 1 AND 500",
     ("page_number",)),
    ("comparison_matrix_edit", "ck_comparison_matrix_edit_page_numbers",
     "(page_number IS NULL OR page_number >= 1) AND (other_page_number IS NULL OR other_page_number >= 1)",
     "(page_number IS NULL OR page_number BETWEEN 1 AND 500) "
     "AND (other_page_number IS NULL OR other_page_number BETWEEN 1 AND 500)",
     ("page_number", "other_page_number")),
    ("comparison_ai_link", "ck_comparison_ai_link_page_numbers",
     "page_number >= 1 AND other_page_number >= 1",
     "page_number BETWEEN 1 AND 500 AND other_page_number BETWEEN 1 AND 500",
     ("page_number", "other_page_number")),
    ("comparison_ai_pair_question", "ck_comparison_ai_pair_question_page_numbers",
     "page_number >= 1 AND (hint_page_number IS NULL OR hint_page_number >= 1)",
     "page_number BETWEEN 1 AND 500 AND (hint_page_number IS NULL OR hint_page_number BETWEEN 1 AND 500)",
     ("page_number", "hint_page_number")),
)


def upgrade() -> None:
    for table, name, relaxed, _former, _columns in PAGE_CHECKS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, relaxed)


def downgrade() -> None:
    bind = op.get_bind()
    for table, _name, _relaxed, _former, columns in PAGE_CHECKS:
        above = " OR ".join(f"{column} > :maximum" for column in columns)
        if bind.execute(text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {above})"),
                        {"maximum": FORMER_MAXIMUM}).scalar_one():
            raise RuntimeError("comparison_page_bounds_large_pages_exist")
    for table, name, _relaxed, former, _columns in PAGE_CHECKS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, former)
