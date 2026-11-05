"""0054 -- the designer's execution status of an accepted finding (`UI-PARITY-P0I`, ruling `R-151g`).

The original badges a finding «Принято · Учтено / Внесено / Отклонено / По согл.» from the external SU-10 registry: what
the designer did with an accepted remark. The owner ruled «Статус исполнения у нас»: our own status, entered by hand, no
import of the registry. The value set follows the original's labels: ``taken_into_account`` (Учтено), ``amended``
(Внесено), ``declined`` (Отклонено), ``agreed`` (По согласованию).

``finding_execution_status`` holds the current status of a finding (at most one row, removed when the status is
cleared); the writer is a RESTRICT reference to ``app_user`` (registered) with the ``0049`` identity check. Every set and
clear appends ``finding.execution_status_set`` to the audit trail in the command's transaction, so the history is kept.
The status is not an expert decision: it never changes the verdict, the decision journal or any counter.

Downgrade drops the table; the statuses are lost.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0054_finding_execution_status"
down_revision: str | None = "0053_document_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE finding_execution_status (
            finding_uid     text PRIMARY KEY,
            status          text NOT NULL,
            set_by_user_uid text NOT NULL,
            set_at          timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_finding_execution_status_finding
                FOREIGN KEY (finding_uid) REFERENCES finding (finding_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_finding_execution_status_set_by
                FOREIGN KEY (set_by_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT ck_finding_execution_status_status
                CHECK (status IN ('taken_into_account', 'amended', 'declined', 'agreed')),
            CONSTRAINT ck_finding_execution_status_set_by_user_uid_format
                CHECK (set_by_user_uid ~ '^usr_[0-9A-HJKMNP-TV-Z]{26}$')
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE finding_execution_status IS "
        "'R-151g: what the designer did with an accepted finding (the original''s SU-10 labels), entered by hand.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE finding_execution_status")
