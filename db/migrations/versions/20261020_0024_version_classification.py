"""A version's expert-confirmed classification, and ``PS`` in the current section vocabulary.

Revision ID: 0024_version_classification
Revises: 0023_norm_citations

`W59-SECTION-SEAL-01`, under the design decision `W59-SECTION-IDENTITY-DECISION-01`.

What this revision adds
-----------------------
``document_version_classification``: one row per classified version -- the explicit project
stage (``P`` or ``R``), one of the fifteen section codes, the confirming expert and when.
Run start reads it and routes the analysis profile from it; nothing infers it.

**Outside the immutable version row.** ``document_version`` is refused UPDATE and DELETE by
``trg_document_version_immutable`` (``0002``): a published version's bytes and manifest
never change. A classification is a later expert fact about that version, so it lives in its
own table keyed by ``version_uid`` and carries the same guarantee -- the same
``am_immutable_row`` trigger refuses UPDATE and DELETE (SQLSTATE ``AM003``). The first
confirmation stands; a different choice needs a separately specified, append-only
correction, which this revision does not provide. The primary key makes "one
classification per version" a property of the table, so two concurrent first confirmations
cannot both land.

**No backfill.** Every existing version stays unclassified: no row is fabricated from the
legacy ``document.section``, a file name, the current head or a display ordinal. Old runs
keep the profile they pinned and stay readable; an unclassified version is refused at the
next run start until an expert classifies it.

**The confirmer is a RESTRICT reference to ``app_user``.** An account that confirmed a
classification is history the classification points at, so purging it is refused
(``conflict``, ``account_referenced``) like an account that authored an expert decision.
The column is registered in ``access.references`` -- the register an account purge
consults and ``test_accounts_migration.py`` holds equal to the schema's foreign keys
(integrator grant, `W59-SECTION-SEAL-01`).

``PS`` in the current vocabulary
--------------------------------
``0011_document_section`` restated legacy's fourteen codes as ``ck_document_section``. That
file stays as written -- it is the historical record of what the column accepted then.
The current vocabulary is fifteen: ``PS`` (the explanatory note), distinct from ``PB``
(fire safety). This revision replaces the CHECK with the fifteen codes, so a document
uploaded with ``section: PS`` is stored rather than refused by the database while the API
enum accepts it. The codes are restated here rather than imported, for ``0011``'s reason.

Downgrade
---------
Drops the new table (every classification an expert recorded is lost; the downgrade names
how many) and restores the fourteen-code ``ck_document_section``. The restored CHECK is
``NOT VALID`` when a document already carries ``PS``, so the downgrade never deletes or
rewrites a document row: such rows are named in the log and remain as they are, and every
new write is held to the fourteen again.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0024_version_classification"
down_revision: str | None = "0023_norm_citations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.version_classification")

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: ``0011_document_section``'s fourteen, verbatim and in its order: what the downgrade restores.
LEGACY_PROJECT_SECTIONS: tuple[str, ...] = (
    "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS",
)

#: The current fifteen: legacy's fourteen, then ``PS``. Restated, not imported (see above);
#: ``tests/contract/domain_p02/test_project_section_catalog.py`` holds this tuple equal to
#: the contract's ``ProjectSection`` and the dashboard's vocabulary.
PROJECT_SECTIONS: tuple[str, ...] = (*LEGACY_PROJECT_SECTIONS, "PS")

#: The explicit project stages: design (``P``) and working (``R``) documentation.
PROJECT_STAGES: tuple[str, ...] = ("P", "R")


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE document_version_classification (
            version_uid           text PRIMARY KEY,
            project_stage         text NOT NULL,
            section_code          text NOT NULL,
            confirmed_by_user_uid text NOT NULL,
            confirmed_at          timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_document_version_classification_version
                FOREIGN KEY (version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_document_version_classification_confirmed_by
                FOREIGN KEY (confirmed_by_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            CONSTRAINT ck_document_version_classification_version_uid_format
                CHECK (version_uid ~ '^ver_{ULID}$'),
            CONSTRAINT ck_document_version_classification_project_stage
                CHECK (project_stage IN ({_sql_list(PROJECT_STAGES)})),
            CONSTRAINT ck_document_version_classification_section_code
                CHECK (section_code IN ({_sql_list(PROJECT_SECTIONS)})),
            CONSTRAINT ck_document_version_classification_confirmed_by_format
                CHECK (confirmed_by_user_uid ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_version_classification_immutable
            BEFORE UPDATE OR DELETE ON document_version_classification
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE document_version_classification IS "
        "'W59-SECTION-SEAL-01. One expert-confirmed project stage (P/R) and section per "
        "published version. Written once by the authenticated classify command and never "
        "updated or deleted (am_immutable_row); never backfilled from document.section, a "
        "file name or the current head. Run start routes the analysis profile from it.';"
    )
    op.execute("ALTER TABLE document DROP CONSTRAINT ck_document_section;")
    op.execute(
        f"""
        ALTER TABLE document
            ADD CONSTRAINT ck_document_section CHECK (
                section IS NULL OR section IN ({_sql_list(PROJECT_SECTIONS)})
            );
        """
    )


def downgrade() -> None:
    """Drop the classification table and restore the fourteen-code document CHECK."""
    bind = op.get_bind()
    classified = bind.execute(
        text("SELECT count(*) FROM document_version_classification")
    ).scalar_one()
    if classified:
        _log.warning(
            "0024_version_classification downgrade: %d version classification(s) recorded "
            "by experts exist nowhere else and are dropped with the table. Those versions "
            "become unclassified.",
            int(classified),
        )
    op.execute("DROP TABLE document_version_classification;")

    carrying_ps = bind.execute(
        text("SELECT document_uid FROM document WHERE section = 'PS' ORDER BY document_uid")
    ).scalars().all()
    op.execute("ALTER TABLE document DROP CONSTRAINT ck_document_section;")
    not_valid = " NOT VALID" if carrying_ps else ""
    if carrying_ps:
        _log.warning(
            "0024_version_classification downgrade: %d document(s) carry section PS (%s), "
            "which 0011's fourteen-code CHECK does not admit. They are kept unchanged and "
            "the restored CHECK is NOT VALID: it holds every new write to the fourteen.",
            len(carrying_ps),
            ", ".join(carrying_ps),
        )
    op.execute(
        f"""
        ALTER TABLE document
            ADD CONSTRAINT ck_document_section CHECK (
                section IS NULL OR section IN ({_sql_list(LEGACY_PROJECT_SECTIONS)})
            ){not_valid};
        """
    )
