"""0052 -- a document can be archived (`UI-PARITY-P0G`, ruling `R-151a`).

The original deletes a version, a project and its results and renames a folder; the owner ruled instead «Архив и
переименование»: a document is hidden from lists by a reversible flag and keeps its whole history, and its display title
can change while ``document_uid`` stays. Versions, runs and results are never deleted.

* ``document.archived_at`` and ``archived_by_user_uid`` hold the current state; both are NULL for a document in use and
  both are set for an archived one (``ck_document_archived_pair``). The actor is a RESTRICT reference to ``app_user``
  (registered in ``access/references.py``) with the ``0049`` identity check.
* The history is the audit trail: every archive, restore and rename appends an ``audit_event`` (``Document``,
  ``document.archived`` / ``document.restored`` / ``document.renamed``) in the command's transaction, so a restored
  document still shows that it was archived, by whom and when.
* ``display_title`` was already mutable (no trigger guards ``document``); renaming changes it and ``updated_at``.

Downgrade refuses while any document is archived (the state would be lost silently); otherwise it drops the columns.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0052_document_archive"
down_revision: str | None = "0051_run_started_by"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE document "
        "ADD COLUMN archived_at timestamptz NULL, "
        "ADD COLUMN archived_by_user_uid text NULL"
    )
    op.execute(
        "ALTER TABLE document ADD CONSTRAINT fk_document_archived_by "
        "FOREIGN KEY (archived_by_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT"
    )
    op.execute(
        "ALTER TABLE document ADD CONSTRAINT ck_document_archived_by_user_uid_format "
        "CHECK (archived_by_user_uid IS NULL OR archived_by_user_uid ~ '^usr_[0-9A-HJKMNP-TV-Z]{26}$')"
    )
    op.execute(
        "ALTER TABLE document ADD CONSTRAINT ck_document_archived_pair "
        "CHECK ((archived_at IS NULL) = (archived_by_user_uid IS NULL))"
    )
    op.execute(
        "COMMENT ON COLUMN document.archived_at IS "
        "'R-151a: when the document was archived (hidden from lists, history kept); NULL while in use.'"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM document WHERE archived_at IS NOT NULL) THEN
                RAISE EXCEPTION 'downgrade refused: archived documents exist; restore them first';
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE document DROP CONSTRAINT ck_document_archived_pair")
    op.execute("ALTER TABLE document DROP CONSTRAINT ck_document_archived_by_user_uid_format")
    op.execute("ALTER TABLE document DROP CONSTRAINT fk_document_archived_by")
    op.execute("ALTER TABLE document DROP COLUMN archived_by_user_uid, DROP COLUMN archived_at")
