"""Which dependency: ``audit_run.terminal_detail``, bound to the reported code's own keys.

Revision ID: 0010_run_terminal_detail
Revises: 0009_reviewer_display_name

`D-46`, closed under `R-29` by the row's own cheaper option. `W29-SAY` made the screen
explain what ``dependency_unavailable`` **means** and registered the row because it still
could not say **which** dependency: neither ``RunStatus`` nor ``StageState`` carried a
detail object, the catalog's ``safe_detail_keys`` live on the **error envelope**, and a
``200`` run reading is not an error envelope. So the information was not in the data, and
inventing it was the one thing that task forbade.

The true sentence this makes sayable is *your document is fine, the provider is fine, this
deployment has no recording for it.* `R-30` put the stand in ``recorded`` mode the same
week, so a document with no recording is the ordinary case rather than a hypothetical: the
adapter raises ``analysis_input_invalid`` with ``reason: "recording_missing"`` and
``stage_id: "text_analysis"`` -- the two keys the frozen catalog declares safe for that
code -- and this column is what carries them onto the run reading.

**No catalog code was added.** That was the row's option 2 and it is a second reseal, which
is the owner's. The catalog stays at twenty-two and stays frozen.

What the two CHECKs are for, and what they are not
----------------------------------------------------
``ck_audit_run_terminal_detail_is_object`` refuses anything that is not a flat JSON object.
``ck_audit_run_terminal_detail_needs_a_reason`` refuses a detail with no ``terminal_reason``
beside it, and **that one is the point of the column rather than a tidiness rule**: the
allowlist bounding these keys is a property of the reported code, so a detail with no code
is unscreenable -- by anything, now or at any later time. Coupling it structurally is the
only way to make "restricted to the reported code's own safe_detail_keys" a property of the
table rather than a promise about one code path.

**The key allowlist itself is deliberately not encoded here.** It would mean writing the
frozen error catalog's twenty-two per-code key lists into a migration, where they could
drift from ``contracts/domain/v1/error-codes.json`` silently and where correcting them
would need another revision. The screen lives in
:func:`auditmanager.shared.errors.screen_details`, is the **same function** the error
envelope uses, and runs at three points in three different eras: when the run terminates
(``TerminalSelection.__post_init__``), when the row is written, and when a reader asks
(``run_status_body``). Only the third covers a row this code did not write, which is why
there are three and not one.

``NULL`` means no detail, and an empty object is not a different fact from no detail -- so
nothing writes ``'{}'::jsonb`` and the API renders nothing for it. That is a rule the
writers hold rather than a CHECK, because ``{}`` is a legal flat object and refusing it here
would make a harmless write an outage.

Downgrade
---------
Drops the column and its two constraints. What is lost is a *classifier* that the
``stage_result`` rows still carry in full -- this column is a projection of them onto the
run, written so a client can read one answer without walking four stage rows -- so nothing
is destroyed that exists nowhere else, and the downgrade is neither loud nor refused. It
exists because `R-11` reverted an entire wave over a reseal and this column is part of one:
the reseal has to be revertible without touching anything else, which is why `R-37`'s
column is a separate revision rather than sharing this one.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_run_terminal_detail"
down_revision: str | None = "0009_reviewer_display_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_run ADD COLUMN terminal_detail jsonb;")
    op.execute(
        """
        ALTER TABLE audit_run
            ADD CONSTRAINT ck_audit_run_terminal_detail_is_object CHECK (
                terminal_detail IS NULL OR jsonb_typeof(terminal_detail) = 'object'
            ),
            ADD CONSTRAINT ck_audit_run_terminal_detail_needs_a_reason CHECK (
                terminal_detail IS NULL OR terminal_reason IS NOT NULL
            );
        """
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.terminal_detail IS "
        "'D-46: safe scalar classifiers saying WHICH dependency a failed run terminated "
        "on, restricted to the safe_detail_keys the frozen catalog declares for the code "
        "in terminal_reason. A flat JSON object or NULL; never an empty object, because "
        "no detail and an empty detail are the same fact. It is a projection of the "
        "stage_result rows onto the run, so a client can read one answer without walking "
        "four rows; the rows remain the source. The key allowlist is NOT encoded in this "
        "table - it belongs to contracts/domain/v1/error-codes.json and is applied by "
        "auditmanager.shared.errors.screen_details, the same screen the error envelope "
        "uses. What IS structural here is that a detail cannot exist without a reason, "
        "because the allowlist that bounds it is a property of the reported code.';"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE audit_run "
        "DROP CONSTRAINT ck_audit_run_terminal_detail_needs_a_reason, "
        "DROP CONSTRAINT ck_audit_run_terminal_detail_is_object;"
    )
    op.execute("ALTER TABLE audit_run DROP COLUMN terminal_detail;")
