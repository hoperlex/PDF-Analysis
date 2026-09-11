"""Three owner-ruled corrections to the P02 head.

Revision ID: 0003_open_items
Revises: 0002_pc01_schema

Each closes an item recorded in ``GATE_B1_CLOSURE.md`` or ``GATE_B2_CLOSURE.md`` and ruled
by the repository owner on 2026-09-11. None changes behaviour that PC-01 exercises today;
each removes a way for a later reader to be misled.
"""

from __future__ import annotations

from alembic import op

revision = "0003_open_items"
down_revision = "0002_pc01_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. The blob content index promised something it could not deliver.
    #
    # Its comment read "a rejected or erased blob must not block a later good upload", and
    # scoping it `WHERE state = 'available'` would achieve that only if blob_id were
    # allocated. It is derived from (sha256, size) - `machines.blob.retry` requires that
    # re-uploading identical content be idempotent by content - and blob_id is the PRIMARY
    # KEY, so content uniqueness already holds in every state and the partial scope bought
    # nothing. Session B1 found it by reading both halves; neither A1 nor A3 could, because
    # each had written only one.
    #
    # The owner ruled: accept the consequence, correct the claim. Rejected bytes are
    # permanently banned, the PC-01 ingest path never rejects - B1 designed around it and
    # pinned that with a test - and the index stops describing behaviour nobody has.
    op.execute("DROP INDEX IF EXISTS uq_blob_available_content;")
    op.execute(
        """
        COMMENT ON COLUMN blob.sha256 IS
            'Content checksum. Uniqueness of (sha256, size_bytes) is enforced by the '
            'PRIMARY KEY on blob_id, which is DERIVED from exactly those two values, so '
            'it holds in every state rather than only in available. A rejected blob '
            'therefore bans those bytes permanently. The PC-01 ingest path never rejects: '
            'it probes before claiming a key, so a refused upload creates no row at all.';
        """
    )

    # 2. model_call.status admitted two values; the provenance emits three.
    #
    # `analysis.text.provenance` reports `truncated` for a response that stopped on the
    # output limit - exactly the case that yields a `partial` stage. B5 mapped it to
    # `succeeded` and kept the real stop reason in `parameters`, because the CHECK would
    # have refused the row. That is a lossy map made under duress, not a decision.
    op.execute("ALTER TABLE model_call DROP CONSTRAINT ck_model_call_status;")
    op.execute(
        """
        ALTER TABLE model_call ADD CONSTRAINT ck_model_call_status
            CHECK (status IN ('succeeded', 'failed', 'truncated'));
        """
    )

    # 3. ungrounded_reason declared a five-value vocabulary and enforced none of it.
    #
    # Every other closed field on finding_observation carries a check; this one was plain
    # nullable text, so the database would accept 'looked_wrong'. B4 reported it and could
    # not fix it - db/migrations was not its tree.
    #
    # The owner ruled the diagnostic path itself is accepted as B-III found it: the analysis
    # stage drops unresolvable anchors before the gate sees one, so no grounded = false row
    # is written today and this vocabulary has no producer. The constraint is added anyway.
    # A declared vocabulary that nothing enforces is a vocabulary that drifts the moment a
    # producer appears, and the cost of enforcing it now is one line.
    op.execute(
        """
        ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_ungrounded_reason
            CHECK (
                ungrounded_reason IS NULL
                OR ungrounded_reason IN (
                    'quotation_absent',
                    'quotation_on_different_page',
                    'span_outside_page',
                    'span_outside_block',
                    'span_length_mismatch'
                )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE finding_observation "
        "DROP CONSTRAINT IF EXISTS ck_finding_observation_ungrounded_reason;"
    )
    op.execute("ALTER TABLE model_call DROP CONSTRAINT IF EXISTS ck_model_call_status;")
    op.execute(
        """
        ALTER TABLE model_call ADD CONSTRAINT ck_model_call_status
            CHECK (status IN ('succeeded', 'failed'));
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_blob_available_content
            ON blob (sha256, size_bytes)
            WHERE state = 'available';
        """
    )
