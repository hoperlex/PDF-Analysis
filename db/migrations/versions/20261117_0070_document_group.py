"""0070 -- one optional group on a document: ``document.group_label`` (`UIP-G-10`, programme `UI-PARITY-R3`).

Revision ID: 0070_document_group
Revises: 0069_account_last_project

Owner ruling Г11 (poll 2): a section screen shows its documents under group headings, a document moves between groups by drag, the
groups are in alphabetical order, and there is no renaming of a group and no empty group. So a group is **a value a document carries**,
not an entity: one optional text per document, beside the free tags (`0053`), which stay and stay a filter. ``R-151e``'s «no group» is
revised by Г11: the tags are unchanged and the group is a separate new field.

What this revision adds
-----------------------
``document.group_label`` -- the group of the document, ``NULL`` for «Без группы» (the default of every existing document). The wire name is
``group``; the column is ``group_label`` because ``GROUP`` is a reserved word of SQL. ``ck_document_group_label_length`` holds the shape
the command stores: 1 to 40 characters, with no leading or trailing space (the command trims and collapses inner runs of spaces, and a
blank value is stored as ``NULL``, never as an empty string). The column carries no foreign key and no index: a group has no identity and
is read with its project's documents.

The history is the audit trail, as for the title and the tags: a change of the group appends one ``document.group_set`` event of
aggregate ``Document`` (the group before and after, ``null`` for none) in the command's transaction. ``document`` is a PRODUCT table
already (the purge truncates it and the project erase removes its rows), so the new column needs no classification of its own.

Downgrade
---------
Drops the check and the column. The only fact lost is which group each document was in; nothing else reads it.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0070_document_group"
down_revision: str | None = "0069_account_last_project"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE document ADD COLUMN group_label text NULL")
    op.execute(
        "ALTER TABLE document ADD CONSTRAINT ck_document_group_label_length "
        "CHECK (group_label IS NULL OR (char_length(group_label) BETWEEN 1 AND 40 AND group_label = btrim(group_label)))"
    )
    op.execute(
        "COMMENT ON COLUMN document.group_label IS "
        "'UIP-G-10 (owner ruling G11): the one optional group of the document, 1 to 40 characters; NULL is «Без группы». "
        "A value the document carries, not an entity; the free tags (document_tag) are separate and unchanged.'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE document DROP CONSTRAINT ck_document_group_label_length")
    op.execute("ALTER TABLE document DROP COLUMN group_label")
