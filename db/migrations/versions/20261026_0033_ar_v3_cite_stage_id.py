"""Admit the AR v3 citation-review stage id in ``stage_result``.

Revision ID: 0033_ar_v3_cite_stage_id
Revises: 0032_ar_v3_run_group

`D-225`, found by `PROD-11a` (``PROD-11A-V3-TEXT-LAYER-PROBE-01``). ``0002`` made the domain of
``stage_result.stage_id`` the nine stages of the analysis registry (``ck_stage_result_stage_id``).
``AR-V3-BETA-RUN-STAGE-SEAL-01`` added a tenth id, ``ar_v3_citation_review``, to the API
vocabulary and the v3 CITE writer records its ``StageResult`` under it, but no migration widened
the CHECK. The database therefore refused the CITE row of every AR v3 Run
(``new row for relation "stage_result" violates check constraint "ck_stage_result_stage_id"``)
and the carrier recorded the Run ``failed / internal_error``. No earlier test saw it: the v3
tests use fakes.

What this revision does
-----------------------
It replaces ``ck_stage_result_stage_id`` with the nine registry ids and ``ar_v3_citation_review``.
Nothing else moves: no table, column, row or trigger.

What it deliberately leaves alone
---------------------------------
Two more CHECKs enumerate the same nine ids, ``ck_model_call_stage_id`` and
``ck_finding_observation_stage_id`` (both ``0002``). The CITE id cannot reach either: the v3
provider call is journalled under ``text_analysis`` (the ``model_call`` INSERT names that literal
and ``provider_call_effect`` is held to it by ``ck_provider_effect_stage_id``), and the v3 review
writes no ``finding_observation`` row. The CITE stage's other writes land in places that already
admit the id: the ``stage.started`` / ``stage.finished`` event payloads (``audit_event.payload``
has no stage vocabulary) and ``analysis_artifact_publication.stage_id``
(``ck_analysis_artifact_stage_id`` is a lower-snake-case pattern, not a list). A CHECK widened
without a writer is a vocabulary nobody asked for, so those two stay at nine ids and a test
holds them there.

The vocabulary is restated, not imported: a migration is history and must not move when the
application does. ``tests/integration/db/test_ar_v3_cite_stage_id_migration.py`` holds the new
CHECK equal to the nine ids plus the one.

Downgrade
---------
Refuses while any ``stage_result`` row carries ``ar_v3_citation_review``: narrowing the CHECK
under such a row would either fail half-way or hide the row from the vocabulary that validates
it, and the row is the only record of that stage's outcome (the pattern of the refusals in
``0006``, ``0029`` and ``0032``). With no such row it restores ``0002``'s constraint exactly.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0033_ar_v3_cite_stage_id"
down_revision: str | None = "0032_ar_v3_run_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The nine stages of the analysis registry that ``0002`` admitted (``STAGE_IDS`` there).
_REGISTRY_STAGE_IDS = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
    "block_analysis",
    "finding_merge",
    "finding_review",
    "finding_correction",
    "norm_verification",
)
#: The one id this revision admits: the AR v3 review-only CITE stage.
_ADDED_STAGE_ID = "ar_v3_citation_review"
_NEW_STAGE_IDS = (*_REGISTRY_STAGE_IDS, _ADDED_STAGE_ID)


def _sql_values(values: tuple[str, ...]) -> str:
    """Quote only fixed, source-controlled enum literals, never database input."""
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _stage_check(values: tuple[str, ...]) -> None:
    op.execute(
        "ALTER TABLE stage_result "
        "DROP CONSTRAINT ck_stage_result_stage_id, "
        f"ADD CONSTRAINT ck_stage_result_stage_id CHECK (stage_id IN ({_sql_values(values)}))"
    )


def upgrade() -> None:
    _stage_check(_NEW_STAGE_IDS)


def downgrade() -> None:
    retained = op.get_bind().execute(
        text("SELECT EXISTS (SELECT 1 FROM stage_result WHERE stage_id = :added)"),
        {"added": _ADDED_STAGE_ID},
    ).scalar_one()
    if retained:
        raise RuntimeError(
            "0033 downgrade refused: a stage_result row carries ar_v3_citation_review; "
            "restore a backup instead of downgrading"
        )
    _stage_check(_REGISTRY_STAGE_IDS)
