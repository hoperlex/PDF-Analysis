"""Append-only corrections of a version's classification, and the derived current classification.

Revision ID: 0028_classification_corrections
Revises: 0027_optimisation_proposals

`CLASSIFICATION-CORRECTION-01` (closes ``D-182``), under the rule
`W59-SECTION-IDENTITY-DECISION-01` set for it: a different stage or section after the first
confirmation is a separately specified, **append-only** correction with actor, reason and
revision, never an overwrite.

What this revision adds
-----------------------
``document_version_classification_correction`` -- one immutable row per correction: the version,
its **revision** (2, 3, ... -- revision 1 is the original confirmation, the unchanged
``document_version_classification`` row), the full corrected ``(project_stage, section_code)``
pair, the correcting expert, the reason and the time. The primary key ``(version_uid, revision)``
is the backstop that two concurrent corrections cannot both take the next place; the revision is
an order inside one version and has no meaning without it, never an identity of its own.
UPDATE and DELETE are refused (``am_immutable_row``, SQLSTATE ``AM003``).

``am_check_classification_correction_chain`` -- BEFORE INSERT, ``AM001``: revision ``n`` needs
revision ``n - 1`` (the original for 2, the previous correction otherwise), and the corrected
pair must differ from it. Gap-free numbering and "no no-op" are therefore properties of the
table, not only of the command.

``version_classification_revision`` -- a view: every revision of every classified version, the
original as revision 1 (no reason) and the corrections after it.
``version_classification_current`` -- a view, the derived **current classification**: the latest
revision of each classified version (the original while it has no correction). Its
``confirmed_by_user_uid`` and ``confirmed_at`` are those of the **current revision**: who stands
behind the current values. Nothing stores "current" anywhere, so nothing can disagree with the
history.

``am_check_optimisation_pass_scope`` is **replaced** (``CREATE OR REPLACE``, trigger untouched):
it asked ``0027``'s question -- is the version classified ``AR`` -- of the original row; it now
asks it of the current classification, so a correction into or out of ``AR`` changes what a new
pass may pin. Passes already written stay immutable and pinned to their version and run.

**The correcting expert is a RESTRICT reference to ``app_user``** and is registered in
``auditmanager.access.references``; purging a corrector is ``account_referenced``.

**No backfill.** The upgrade creates empty objects: every existing version's current
classification equals its original, and the stored original confirmations are never touched
(forbidden hotspot of the task; ``0024``'s trigger still refuses UPDATE and DELETE on them).

The vocabulary (stages, fifteen codes, reason bound) is restated, not imported: a migration is
history and must not move when the application does. ``tests/unit/sections`` holds the bounds
equal to ``auditmanager.sections.correction``.

Downgrade
---------
Drops this revision's own objects only: it first **restores** ``0027``'s body of
``am_check_optimisation_pass_scope``, then drops the two views, the correction table and the
chain function. Every recorded correction exists nowhere else; the downgrade names how many it
drops. The versions they corrected revert to their original confirmation, which is untouched.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0028_classification_corrections"
down_revision: str | None = "0027_optimisation_proposals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.classification_corrections")

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: The explicit project stages and the current fifteen section codes, restated (see above).
PROJECT_STAGES: tuple[str, ...] = ("P", "R")
PROJECT_SECTIONS: tuple[str, ...] = (
    "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS",
)

#: The longest reason, in characters; ``auditmanager.sections.correction.MAX_REASON_LENGTH``.
MAX_REASON_LENGTH = 2000


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _pass_scope_function(classification_relation: str) -> str:
    """``am_check_optimisation_pass_scope`` over one relation holding the classification.

    The body is ``0027``'s, character for character, except the relation the version's
    classification is read from: ``document_version_classification`` (what ``0027`` created and
    this revision's downgrade restores) or ``version_classification_current`` (what this
    revision installs).
    """
    return f"""
        CREATE OR REPLACE FUNCTION am_check_optimisation_pass_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM document d
                JOIN document_version v ON v.document_uid = d.document_uid
                JOIN audit_run r ON r.version_uid = v.version_uid
                JOIN {classification_relation} c ON c.version_uid = v.version_uid
                JOIN price_list_revision p ON p.project_uid = d.project_uid
                JOIN vendor_list_revision l ON l.vendor_list_id = NEW.vendor_list_id
                WHERE d.document_uid = NEW.document_uid
                  AND d.project_uid = NEW.project_uid
                  AND v.version_uid = NEW.version_uid
                  AND r.run_id = NEW.run_id
                  AND r.project_uid = NEW.project_uid
                  AND c.section_code = 'AR'
                  AND p.price_list_id = NEW.price_list_id
                  AND l.section_code = 'AR'
                  AND l.mode = 'list'
                  AND l.scope = NEW.vendor_list_source
                  AND (l.scope = 'global' OR l.project_uid = NEW.project_uid)
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: optimisation pass % does not pin one AR '
                    'version of its project with that version''s run, a price list of the '
                    'project and an AR vendor list in force for it', NEW.optimisation_pass_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A pass is written by auditmanager.optimisation.proposals '
                                 'from one consistent read.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE document_version_classification_correction (
            version_uid           text NOT NULL,
            revision              integer NOT NULL,
            project_stage         text NOT NULL,
            section_code          text NOT NULL,
            corrected_by_user_uid text NOT NULL,
            reason                text NOT NULL,
            corrected_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_document_version_classification_correction
                PRIMARY KEY (version_uid, revision),
            CONSTRAINT fk_document_version_classification_correction_original
                FOREIGN KEY (version_uid)
                REFERENCES document_version_classification (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_document_version_classification_correction_corrected_by
                FOREIGN KEY (corrected_by_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            CONSTRAINT ck_document_version_classification_correction_version_uid_format
                CHECK (version_uid ~ '^ver_{ULID}$'),
            CONSTRAINT ck_document_version_classification_correction_corrected_by_format
                CHECK (corrected_by_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_document_version_classification_correction_revision
                CHECK (revision >= 2),
            CONSTRAINT ck_document_version_classification_correction_project_stage
                CHECK (project_stage IN ({_sql_list(PROJECT_STAGES)})),
            CONSTRAINT ck_document_version_classification_correction_section_code
                CHECK (section_code IN ({_sql_list(PROJECT_SECTIONS)})),
            CONSTRAINT ck_document_version_classification_correction_reason
                CHECK (
                    char_length(reason) BETWEEN 1 AND {MAX_REASON_LENGTH}
                    AND reason = btrim(reason, E' \\t\\r\\n')
                )
        );
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_version_classification_correction_immutable
            BEFORE UPDATE OR DELETE ON document_version_classification_correction
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        """
        CREATE FUNCTION am_check_classification_correction_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            previous_stage text;
            previous_section text;
        BEGIN
            IF NEW.revision = 2 THEN
                SELECT c.project_stage, c.section_code
                  INTO previous_stage, previous_section
                  FROM document_version_classification c
                 WHERE c.version_uid = NEW.version_uid;
            ELSE
                SELECT k.project_stage, k.section_code
                  INTO previous_stage, previous_section
                  FROM document_version_classification_correction k
                 WHERE k.version_uid = NEW.version_uid AND k.revision = NEW.revision - 1;
            END IF;
            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: classification of % has no revision % to correct',
                    NEW.version_uid, NEW.revision - 1
                    USING ERRCODE = 'AM001',
                          HINT = 'A correction is revision n + 1 of an existing classification.';
            END IF;
            IF previous_stage = NEW.project_stage AND previous_section = NEW.section_code THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: correction % of % repeats the stage and '
                    'section of the revision before it', NEW.revision, NEW.version_uid
                    USING ERRCODE = 'AM001',
                          HINT = 'A correction must change the project stage, the section '
                                 'or both.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_version_classification_correction_chain
            BEFORE INSERT ON document_version_classification_correction
            FOR EACH ROW EXECUTE FUNCTION am_check_classification_correction_chain();
        """
    )
    op.execute(
        "COMMENT ON TABLE document_version_classification_correction IS "
        "'CLASSIFICATION-CORRECTION-01. One expert correction of a version''s project stage "
        "and section: revision 2, 3, ... (revision 1 is the unchanged original in "
        "document_version_classification), the full corrected pair, the correcting expert and "
        "the reason. Written once and never updated or deleted (am_immutable_row); each "
        "revision needs the one before it and must change the pair "
        "(am_check_classification_correction_chain). The current classification is the "
        "latest revision (view version_classification_current).';"
    )

    op.execute(
        """
        CREATE VIEW version_classification_revision AS
        SELECT
            c.version_uid,
            1 AS revision,
            c.project_stage,
            c.section_code,
            c.confirmed_by_user_uid AS actor_user_uid,
            c.confirmed_at AS decided_at,
            NULL::text AS reason
        FROM document_version_classification c
        UNION ALL
        SELECT
            k.version_uid,
            k.revision,
            k.project_stage,
            k.section_code,
            k.corrected_by_user_uid AS actor_user_uid,
            k.corrected_at AS decided_at,
            k.reason
        FROM document_version_classification_correction k;
        """
    )
    op.execute(
        "COMMENT ON VIEW version_classification_revision IS "
        "'CLASSIFICATION-CORRECTION-01. Every revision of every classified version, oldest "
        "first by revision: the original confirmation as revision 1 (no reason) and the "
        "corrections after it.';"
    )
    op.execute(
        """
        CREATE VIEW version_classification_current AS
        SELECT
            c.version_uid,
            COALESCE(k.revision, 1) AS revision,
            COALESCE(k.project_stage, c.project_stage) AS project_stage,
            COALESCE(k.section_code, c.section_code) AS section_code,
            COALESCE(k.corrected_by_user_uid, c.confirmed_by_user_uid) AS confirmed_by_user_uid,
            COALESCE(k.corrected_at, c.confirmed_at) AS confirmed_at
        FROM document_version_classification c
        LEFT JOIN LATERAL (
            SELECT x.revision, x.project_stage, x.section_code,
                   x.corrected_by_user_uid, x.corrected_at
            FROM document_version_classification_correction x
            WHERE x.version_uid = c.version_uid
            ORDER BY x.revision DESC
            LIMIT 1
        ) k ON TRUE;
        """
    )
    op.execute(
        "COMMENT ON VIEW version_classification_current IS "
        "'CLASSIFICATION-CORRECTION-01. The derived current classification of each classified "
        "version: its latest revision (the original while it has no correction), with the "
        "actor and time of that revision. Every read of a version''s classification goes "
        "through it; nothing stores the current value.';"
    )

    op.execute(_pass_scope_function("version_classification_current"))


def downgrade() -> None:
    """Restore ``0027``'s scope function, then drop this revision's objects; nothing else."""
    bind = op.get_bind()
    corrections = bind.execute(
        text("SELECT count(*) FROM document_version_classification_correction")
    ).scalar_one()
    if corrections:
        versions = bind.execute(
            text(
                "SELECT count(DISTINCT version_uid) "
                "FROM document_version_classification_correction"
            )
        ).scalar_one()
        _log.warning(
            "0028_classification_corrections downgrade: %d correction(s) of %d version(s) "
            "exist nowhere else and are dropped with their table. Those versions revert to "
            "their original confirmation, which is untouched; runs already routed under a "
            "correction keep the profile they pinned.",
            int(corrections),
            int(versions),
        )
    op.execute(_pass_scope_function("document_version_classification"))
    op.execute("DROP VIEW version_classification_current;")
    op.execute("DROP VIEW version_classification_revision;")
    op.execute("DROP TABLE document_version_classification_correction;")
    op.execute("DROP FUNCTION am_check_classification_correction_chain();")
