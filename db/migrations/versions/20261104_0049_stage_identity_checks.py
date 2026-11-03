"""The identity-format CHECK that ``0042`` left off 43 reference columns of the stage review.

Revision ID: 0049_stage_identity_checks
Revises: 0048_dispatch_time_binding

`EXEC2-FIX-CMP-INVENTORY` (found by ``tests/integration/db/test_schema_shape.py::
test_every_identity_column_carries_a_format_check``). Every identity column of this schema carries a CHECK of its
contract pattern, so that a raw statement cannot put a value of the wrong type in it. ``0041`` and the migrations
before it gave that CHECK to the foreign-key columns as well as to the primary keys; ``0042_comparison_stage_review``
(`CMP-SEAL-C4`) gave it to the primary keys only, so 43 columns that hold the identity of another row
(``stage_chain_run_id``, ``stage_ai_unit_id``, ``command_id``, ``actor_user_uid`` and the rest) accepted any text a
foreign key happened to allow. This revision adds the missing CHECKs and nothing else: no column, table, index,
trigger or function changes.

The pattern of each is the one the contract assigns to the identity the column holds
(``contracts/domain/v1/identifiers.json``): ``crn`` for a chain run, ``saunit`` for a stage AI unit, ``slk`` for a
link revision, ``cmd`` for a command, ``usr`` for a user, and so on. A column that may be NULL keeps passing: a CHECK
accepts NULL. Adding a CHECK validates the rows that exist and fires no row trigger, so it is allowed on the tables
``0042`` made immutable. Constraint names are ``ck_<table>_<column>_format``, except one that would be 64 characters
(PostgreSQL keeps 63) and is spelled ``ck_stage_graphic_evidence_pair_result_id_format``.

Downgrade
---------
Drops exactly these 43 constraints. No row is read, changed or refused.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0049_stage_identity_checks"
down_revision: str | None = "0048_dispatch_time_binding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: table -> ((column, identity prefix), ...). 14 tables, 43 columns.
_CHECKS: dict[str, tuple[tuple[str, str], ...]] = {
    "comparison_ai_job": (
        ("stage_chain_run_id", "crn"),
    ),
    "stage_ai_classification": (
        ("stage_ai_unit_id", "saunit"),
        ("stage_chain_run_id", "crn"),
    ),
    "stage_ai_review": (
        ("stage_ai_unit_id", "saunit"),
        ("stage_chain_run_id", "crn"),
    ),
    "stage_ai_synthesis": (
        ("stage_ai_unit_id", "saunit"),
        ("stage_chain_run_id", "crn"),
    ),
    "stage_ai_unit": (
        ("comparison_ai_job_id", "cai"),
        ("stage_chain_run_id", "crn"),
    ),
    "stage_card_evidence": (
        ("page_profile_id", "cpr"),
        ("source_difference_id", "std"),
        ("source_fragment_id", "stf"),
        ("source_graphic_evidence_id", "sge"),
        ("stage_chain_run_id", "crn"),
        ("stage_change_card_id", "ccd"),
    ),
    "stage_card_verdict": (
        ("actor_user_uid", "usr"),
        ("carried_from_verdict_id", "cdv"),
        ("command_id", "cmd"),
        ("stage_change_card_id", "ccd"),
    ),
    "stage_chain_batch": (
        ("command_id", "cmd"),
        ("project_uid", "prj"),
    ),
    "stage_chain_batch_item": (
        ("stage_chain_batch_id", "scb"),
        ("stage_chain_run_id", "crn"),
        ("stage_link_revision_id", "slk"),
        ("stage_pair_id", "stp"),
    ),
    "stage_chain_run": (
        ("comparison_ai_job_id", "cai"),
        ("effective_link_revision_id", "slk"),
        ("stage_chain_batch_id", "scb"),
    ),
    "stage_change_card": (
        ("stage_ai_classification_id", "sacls"),
        ("stage_chain_run_id", "crn"),
    ),
    "stage_graphic_evidence": (
        ("comparison_sheet_pair_result_id", "csp"),
        ("left_profile_id", "cpr"),
        ("right_profile_id", "cpr"),
        ("stage_chain_run_id", "crn"),
        ("stage_link_item_id", "sli"),
    ),
    "stage_link_repair": (
        ("after_revision_id", "slk"),
        ("before_revision_id", "slk"),
        ("stage_chain_run_id", "crn"),
    ),
    "stage_link_repair_event": (
        ("actor_user_uid", "usr"),
        ("command_id", "cmd"),
        ("recompute_run_id", "crn"),
        ("revision_id", "slk"),
        ("stage_link_repair_id", "crp"),
    ),
}

#: ``ck_<table>_<column>_format`` is 64 characters for this one column; PostgreSQL would silently keep 63.
_SHORT_NAMES = {
    ("stage_graphic_evidence", "comparison_sheet_pair_result_id"): "ck_stage_graphic_evidence_pair_result_id_format",
}


def _constraint_name(table: str, column: str) -> str:
    return _SHORT_NAMES.get((table, column), f"ck_{table}_{column}_format")


def upgrade() -> None:
    for table, columns in _CHECKS.items():
        for column, prefix in columns:
            op.execute(
                f"ALTER TABLE {table} ADD CONSTRAINT {_constraint_name(table, column)} "
                f"CHECK ({column} ~ '^{prefix}_{ULID}$')"
            )


def downgrade() -> None:
    for table, columns in reversed(list(_CHECKS.items())):
        for column, _prefix in reversed(columns):
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {_constraint_name(table, column)}")
