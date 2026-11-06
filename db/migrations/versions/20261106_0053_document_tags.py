"""0053 -- free tags on a document (`UI-PARITY-P0H`, ruling `R-151e`).

The original groups a section's projects into folders with drag and order; the owner ruled «Метка документа»: a free
tag on a document and a filter by tag, with no order, no drag and no group entity.

``document_tag`` holds the current tags of each document: at most ten (enforced by the command), each 1 to 40
characters after trimming, unique per document regardless of case (``uq_document_tag_folded``). The writer is a RESTRICT
reference to ``app_user`` (registered in ``access/references.py``) with the ``0049`` identity check. A change of a
document's tags appends one ``document.tags_set`` audit event (before and after) in the command's transaction; the table
itself holds only the current set, so replacing it deletes rows of this table and nothing else.

Downgrade drops the table; the tags are lost.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0053_document_tags"
down_revision: str | None = "0052_document_archive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE document_tag (
            document_uid        text NOT NULL,
            tag                 text NOT NULL,
            created_by_user_uid text NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_document_tag PRIMARY KEY (document_uid, tag),
            CONSTRAINT fk_document_tag_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_document_tag_created_by
                FOREIGN KEY (created_by_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT ck_document_tag_length
                CHECK (char_length(tag) BETWEEN 1 AND 40 AND tag = btrim(tag)),
            CONSTRAINT ck_document_tag_created_by_user_uid_format
                CHECK (created_by_user_uid ~ '^usr_[0-9A-HJKMNP-TV-Z]{26}$')
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_document_tag_folded ON document_tag (document_uid, lower(tag))")
    op.execute("CREATE INDEX ix_document_tag_tag ON document_tag (lower(tag))")
    op.execute(
        "COMMENT ON TABLE document_tag IS "
        "'R-151e: the current free tags of a document (no order, no group); history in the audit trail.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE document_tag")
