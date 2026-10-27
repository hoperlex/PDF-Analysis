"""Certify a citation partition by the AR v3 CITE stage as well as by ``norm_verification``.

Revision ID: 0036_cite_partition_v3
Revises: 0035_comparison_records

`R-146as` / `AR-V3-DECISIONS-01`. ``0023`` made the citation partition of a finding observation a
certificate: ``finding_observation.norm_citation_count`` is checked against the immutable
``finding_observation_norm_citation`` rows when the transaction commits, by the deferred
constraint triggers ``trg_finding_observation_partition`` and ``trg_norm_citation_partition``
(function ``am_verify_norm_citation_partition``). The function requires, besides the pinned and
verified retrieval set, a succeeded ``stage_result`` named ``norm_verification``. The AR v3 beta
Run has no such stage: its CITE stage is ``ar_v3_citation_review`` (``0033``). With the writer
alone, the commit of a published v3 finding would be refused here.

What this revision does
-----------------------
It replaces the one function with ``0023``'s body in which the stage test reads
``st.stage_id IN ('norm_verification', 'ar_v3_citation_review')`` (still ``status = 'succeeded'``,
still the pinned verified set, still the count check). No table, column, CHECK, trigger or view
moves, and the two triggers keep their names.

What it deliberately leaves alone
---------------------------------
``ck_finding_observation_stage_id`` (the observation of a v3 finding is written under
``text_analysis``, which it admits), the closed ``ungrounded_reason`` list (a v3 finding is
grounded; a withheld or rejected proposal is not a row), and the categories (the five normative
ones are already admitted by ``0023``). A CHECK widened without a writer is a vocabulary nobody
asked for.

The vocabulary is restated, not imported: a migration is history and must not move when the
application does. ``tests/integration/db/test_cite_partition_v3_migration.py`` holds the function
to ``0023``'s body plus the one id.

Downgrade
---------
Refuses while any certified ``finding_observation`` (``norm_citation_count`` not null) belongs to a
Run that has no succeeded ``norm_verification`` stage: restoring ``0023``'s function would leave
those rows certified by a stage the function no longer admits, and a later INSERT beside them
would be refused for a reason nobody can read. With no such row it restores ``0023``'s function
byte for byte (the pattern of the refusals in ``0006``, ``0029``, ``0032`` and ``0033``).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0036_cite_partition_v3"
down_revision: str | None = "0035_comparison_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BODY_HEAD = """
        CREATE OR REPLACE FUNCTION am_verify_norm_citation_partition() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            observation_id text;
            observation_run text;
            certified_count integer;
            actual_count integer;
        BEGIN
            observation_id := NEW.finding_observation_id;
            SELECT run_id, norm_citation_count INTO observation_run, certified_count
              FROM finding_observation
             WHERE finding_observation_id = observation_id;
            SELECT count(*) INTO actual_count FROM finding_observation_norm_citation
             WHERE finding_observation_id = observation_id;
            IF (certified_count IS NULL AND actual_count <> 0)
               OR (certified_count IS NOT NULL AND certified_count <> actual_count) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: citation partition count mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            IF certified_count IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM audit_run r
                JOIN norm_retrieval_set s
                  ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
                 AND s.norms_snapshot_id = r.norms_snapshot_id
                 AND s.state = 'verified'
                JOIN stage_result st ON st.run_id = r.run_id
                 AND {STAGE_TEST} AND st.status = 'succeeded'
                WHERE r.run_id = observation_run
            ) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: certified citation partition needs succeeded CITE stage and pinned verified set'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NULL;
        END $fn$;
        """

#: ``0023``'s stage test, verbatim: the downgrade restores exactly this.
_STAGE_TEST_0023 = "st.stage_id = 'norm_verification'"
#: This revision's test: the registry CITE stage or the AR v3 beta CITE stage.
_STAGE_TEST_0036 = "st.stage_id IN ('norm_verification', 'ar_v3_citation_review')"


def _function(stage_test: str) -> str:
    return _BODY_HEAD.replace("{STAGE_TEST}", stage_test)


def upgrade() -> None:
    op.execute(_function(_STAGE_TEST_0036))


def downgrade() -> None:
    retained = op.get_bind().execute(text(
        "SELECT count(*) FROM finding_observation o "
        "WHERE o.norm_citation_count IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM stage_result st WHERE st.run_id = o.run_id "
        "AND st.stage_id = 'norm_verification' AND st.status = 'succeeded')"
    )).scalar_one()
    if retained:
        raise RuntimeError(
            f"0036 downgrade refused: {retained} certified finding observation(s) rest on an "
            "ar_v3_citation_review stage; restore a backup instead of downgrading"
        )
    op.execute(_function(_STAGE_TEST_0023))
