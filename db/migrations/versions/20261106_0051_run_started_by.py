"""0051 -- who started a run (`UI-PARITY-P0F`, ruling `R-151v`).

The owner ruled that a run records its starter from now on: «Да, с этого момента». ``audit_run`` gains
``started_by_user_uid``, the account whose ``startRun`` or ``reauditRun`` created the run. Runs created before this
revision have none and show «неизвестно»; nothing is back-filled, because nothing recorded who started them.

* The column is a RESTRICT reference to ``app_user`` like every other actor column of the product (the account
  register, ``access/references.py``, names it), so an account that started a run is archived, never purged.
* It has the identity format check of ``0049`` (``usr_`` and a ULID body).
* It is frozen: ``trg_audit_run_frozen_guard`` is re-created with the column added to its list, on the same function
  ``am_guard_audit_run_frozen`` (``0048``). A starter is written once, at INSERT, and never changed.

Downgrade restores the ``0048`` trigger list and drops the column with its constraints; the starters recorded are lost.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0051_run_started_by"
down_revision: str | None = "0050_viewer_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: ``0048``'s list (``_FROZEN_RUN_AFTER``), restated: a migration never imports another.
_FROZEN_0048 = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id', 'preset_revision_id', 'executor_group_revision_id', 'routing_rule_revision_id'"
)
_FROZEN_0051 = _FROZEN_0048 + ", 'started_by_user_uid'"


def _frozen_run_guard(columns: str) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_audit_run_frozen({columns})"
    )


def upgrade() -> None:
    op.execute("ALTER TABLE audit_run ADD COLUMN started_by_user_uid text NULL")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT fk_audit_run_started_by "
        "FOREIGN KEY (started_by_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_started_by_user_uid_format "
        "CHECK (started_by_user_uid IS NULL OR started_by_user_uid ~ '^usr_[0-9A-HJKMNP-TV-Z]{26}$')"
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.started_by_user_uid IS "
        "'The account whose startRun or reauditRun created this run (R-151v); NULL for runs created before 0051.'"
    )
    _frozen_run_guard(_FROZEN_0051)


def downgrade() -> None:
    _frozen_run_guard(_FROZEN_0048)
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_started_by_user_uid_format")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT fk_audit_run_started_by")
    op.execute("ALTER TABLE audit_run DROP COLUMN started_by_user_uid")
