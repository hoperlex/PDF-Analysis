"""Allow positive page counts above the former 500-page application quota.

The temporary statistics intake can admit a larger PDF without the database
rejecting its immutable version after full validation.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0044_section_stats_uncapped"
down_revision: str | None = "0043_stage_ai_generations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_document_version_page_count", "document_version", type_="check")
    op.create_check_constraint("ck_document_version_page_count", "document_version", "page_count >= 1")
    for table, name, condition in (
        ("stage_upload", "ck_stage_upload_files", "declared_files >= 1"),
        ("stage_upload", "ck_stage_upload_bytes", "declared_bytes >= 1"),
        ("stage_upload_file", "ck_stage_upload_file_size", "declared_size_bytes >= 1"),
        ("stage_upload_candidate", "ck_stage_upload_candidate_member", "member_number >= 1"),
        ("stage_upload_part", "ck_stage_upload_part_number", "part_number BETWEEN 1 AND 10000"),
    ):
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, condition)


def downgrade() -> None:
    if op.get_bind().execute(text("SELECT EXISTS(SELECT 1 FROM document_version WHERE page_count > 500)")).scalar_one():
        raise RuntimeError("section_stats_large_versions_exist")
    for table, column, maximum in (
        ("stage_upload", "declared_files", 1000),
        ("stage_upload", "declared_bytes", 2147483648),
        ("stage_upload_file", "declared_size_bytes", 2147483648),
        ("stage_upload_candidate", "member_number", 1000),
        ("stage_upload_part", "part_number", 128),
    ):
        if op.get_bind().execute(text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {column} > :maximum)"),
                                 {"maximum": maximum}).scalar_one():
            raise RuntimeError("section_stats_large_stage_uploads_exist")
    for table, name, condition in (
        ("stage_upload", "ck_stage_upload_files", "declared_files BETWEEN 1 AND 1000"),
        ("stage_upload", "ck_stage_upload_bytes", "declared_bytes BETWEEN 1 AND 2147483648"),
        ("stage_upload_file", "ck_stage_upload_file_size", "declared_size_bytes BETWEEN 1 AND 2147483648"),
        ("stage_upload_candidate", "ck_stage_upload_candidate_member", "member_number BETWEEN 1 AND 1000"),
        ("stage_upload_part", "ck_stage_upload_part_number", "part_number BETWEEN 1 AND 128"),
    ):
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, condition)
    op.drop_constraint("ck_document_version_page_count", "document_version", type_="check")
    op.create_check_constraint("ck_document_version_page_count", "document_version", "page_count BETWEEN 1 AND 500")
