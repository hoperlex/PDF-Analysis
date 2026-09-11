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
    # 1. The blob content index says what it actually does.
    #
    # B1 reported that its comment - "a rejected or erased blob must not block a later good
    # upload" - cannot be true, because blob_id is derived from (sha256, size) and is the
    # primary key, so a rejected blob bans those bytes regardless of the scope. That much is
    # correct and the owner accepted the consequence.
    #
    # **Dropping the index was wrong and two tests caught it.** The database does not know
    # that blob_id is derived; the storage adapter guarantees that, and nothing in the schema
    # does. Without the partial index, two `available` rows with different blob_ids and
    # identical content insert cleanly - so it was the only content-uniqueness guarantee the
    # database itself held, and removing it deleted a real invariant to fix a false comment.
    #
    # The index stays. The comment is corrected instead, which is all that was ever wrong.
    op.execute(
        """
        COMMENT ON INDEX uq_blob_available_content IS
            'Content uniqueness among available blobs, enforced by the database itself. '
            'It does NOT let a rejected blob be re-uploaded: blob_id is derived from '
            '(sha256, size) by the storage adapter and is the primary key, so those bytes '
            'are banned in every state. The scope to available is what the database can '
            'guarantee without knowing how blob_id is chosen. The PC-01 ingest path never '
            'rejects - it probes before claiming a key - so a refused upload writes no row.';
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
