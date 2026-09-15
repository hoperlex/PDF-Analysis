"""Make ``truncated`` a first-class ``model_call`` status instead of a tolerated one.

Revision ID: 0005_truncated_call_status
Revises: 0004_cost_basis

``0003_open_items`` widened ``ck_model_call_status`` to admit ``truncated``, and there the
repair stopped. Nothing else in the table learned what the third value means, and the
executor went on mapping it away — so the column *could* hold ``truncated`` and never did.
A value a schema admits and no writer produces is not a recorded fact; it is a spelling.

Two things were missing, and both are invariants rather than vocabulary:

1. **A truncated call produced output.** That is the whole difference between it and a
   failure: the provider answered, the answer was checksummed, and the reply stopped at the
   output ceiling part-way through. ``ck_model_call_succeeded_has_response`` asserted that
   for ``succeeded`` alone, so a ``truncated`` row with a NULL ``response_sha256`` — a row
   claiming a partial answer with no answer behind it — was accepted.

2. **A truncated call is not a catalog failure.** ``ck_model_call_failed_has_code`` requires
   an ``error_code`` for ``failed`` and says nothing about ``truncated``; without the
   converse rule, the first writer to reach for a code would silently make truncation a
   twenty-first kind of error at the row level. ``GATE_B1_CLOSURE.md`` §4 item 6 — the
   catalog has no code for "usable output over a strict subset of the input" — is an **owner
   decision that is still open**, and this migration is deliberately not the place it gets
   made. The constraint below keeps the two objects apart by refusing the row that would
   conflate them: a call status is not an error code, and ``truncated`` carries none.

Existing rows
-------------
**Nothing is rewritten, and nothing needs to be.** ``model_call`` carries
``trg_model_call_immutable`` (``0002``, §9), which refuses UPDATE and DELETE per row, so a
backfill here would have to defeat the guard that makes this table evidence. It also does
not need to: every truncated call written before this revision was persisted by
``runs/executor.py`` as ``succeeded`` **with the provider's own stop reason preserved in
``parameters.call_status``**, which was the point of that lossless workaround. The row
already says it was truncated; only the column did not. ``tools/validation/ledger_report.py``
reads the pre-0005 shape and reports it as ``truncated``, naming ``parameters.call_status``
as the source, in exactly the way it already names ``model_call.cost_basis`` versus a
derivation. The stored value and the derived one are both shown, so a reader can see which
of the two spoke.

Both constraints are therefore satisfied vacuously by every row in every existing database
**at the moment this revision was authored**: no row anywhere had ``status = 'truncated'``
yet, because until this revision the executor could not write one. Validation is immediate
and no table is rewritten.

.. note::

   **That justification expired the day this shipped, and is kept rather than rewritten
   because the distinction matters to anyone re-applying it.** The executor now writes
   ``truncated``, so any database that has run the proxy holds such rows -- ``W5-ADV`` found
   four in one lane. Re-applying this revision therefore validates the CHECKs against real
   data and *can* fail, where on the day it was written it could not.

   The migration itself is unchanged and correct: a row that fails validation is a row that
   violates the invariant, which is what the CHECK is for. What has changed is only the
   cost and the risk of running it -- no longer free, no longer certain.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_truncated_call_status"
down_revision: str | None = "0004_cost_basis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE model_call ADD CONSTRAINT ck_model_call_truncated_has_response
            CHECK (status <> 'truncated' OR response_sha256 IS NOT NULL);
        """
    )
    op.execute(
        """
        ALTER TABLE model_call ADD CONSTRAINT ck_model_call_truncated_has_no_error_code
            CHECK (status <> 'truncated' OR error_code IS NULL);
        """
    )
    op.execute(
        "COMMENT ON COLUMN model_call.status IS "
        "'Terminal state of one provider call, in a closed three-value vocabulary: "
        "succeeded, truncated, failed. truncated means the provider answered and stopped "
        "at the output ceiling - it produced a checksummed response and carries no error "
        "code, which is what distinguishes it from failed. It is not a stage status: the "
        "stage that consumed a truncated call is partial. ROWS WRITTEN BEFORE REVISION "
        "0005 never hold truncated: the executor mapped it onto succeeded and kept the "
        "provider stop reason in parameters.call_status, so a pre-0005 truncated call is "
        "the pair (status = succeeded, parameters->>''call_status'' = ''truncated'') and "
        "is read back as truncated by tools/validation/ledger_report.py.';"
    )
    op.execute(
        "COMMENT ON COLUMN model_call.output_tokens IS "
        "'How much the model actually said, as the PROVIDER reported it in its own usage "
        "block - never a recomputation from the response text, which would measure what "
        "survived parsing rather than what was generated. The two diverge exactly where "
        "the figure earns its keep: a reply cut short at the ceiling reports the full "
        "ceiling here while only its complete prefix is salvaged, and a reply that reasons "
        "at length and publishes nothing reports its reasoning here and no findings "
        "anywhere. P4_CLOSURE.md section 6 wanted this beside the finding count because "
        "precision evidence on this corpus is saturated and the open question became "
        "whether the document was read at all.';"
    )
    op.execute(
        "COMMENT ON CONSTRAINT ck_model_call_truncated_has_no_error_code ON model_call IS "
        "'A call status is not an error code. GATE_B1_CLOSURE.md section 4 item 6 - no "
        "catalog code means usable output over a strict subset of the input - is an open "
        "owner decision about a frozen twenty-member enum, and this constraint refuses the "
        "row that would quietly pre-empt it.';"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE model_call "
        "DROP CONSTRAINT IF EXISTS ck_model_call_truncated_has_no_error_code;"
    )
    op.execute(
        "ALTER TABLE model_call DROP CONSTRAINT IF EXISTS ck_model_call_truncated_has_response;"
    )
    op.execute("COMMENT ON COLUMN model_call.output_tokens IS NULL;")
    op.execute("COMMENT ON COLUMN model_call.status IS NULL;")
