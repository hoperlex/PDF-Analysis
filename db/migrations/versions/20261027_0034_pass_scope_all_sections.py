"""An optimisation pass pins a version of any section and the vendor list of that section.

Revision ID: 0034_pass_scope_all_sections
Revises: 0033_ar_v3_cite_stage_id

`OPT-PROJECT-ALL-SECTIONS-01` (PW4 lane OP; owner order 2026-10-27: «Оптимизация проекта» for
every section, `A-1`). ``0027`` created ``am_check_optimisation_pass_scope`` (the BEFORE INSERT
guard of ``optimisation_pass``) and ``0028`` replaced it so that it reads the version's *current*
classification. Both required two things that only the first section could satisfy: the version's
classification is section ``AR`` and the pinned vendor list is an ``AR`` list. The application
guard in ``optimisation/project_match.py`` and the vendor-list choice in
``optimisation/proposals/commands.py`` held the same rule, so lifting only those two produced a
pass that PostgreSQL refused (``state_transition_not_allowed``, SQLSTATE ``AM001``) at the INSERT.

What this revision does
-----------------------
It replaces that one function (``CREATE OR REPLACE``; the trigger ``trg_optimisation_pass_scope``
is untouched) with ``0028``'s body in which

* ``AND c.section_code = 'AR'`` is gone, and
* ``AND l.section_code = 'AR'`` reads ``AND l.section_code = c.section_code``: the vendor list
  the pass pins is the list **of the section the version is classified in**, not of any
  other section.

Every other condition is ``0028``'s, character for character: the document belongs to the project,
the version to the document, the run to the version and the project, the version has a current
classification (the join), the price list is the project's, the vendor list is a ``list`` (not an
``inherit`` marker) whose scope is the recorded source, and a project's own list is this
project's. Only the text of the exception changed, so that it stops saying «AR».

Both compared columns are ``NOT NULL`` (``document_version_classification.section_code`` and
``document_version_classification_correction.section_code``, which the view unions, and
``vendor_list_revision.section_code``) and both are held to the same fifteen codes by CHECKs, so
the equality can neither be unknown nor pair two spellings of one section. A version of section
``PB`` with an ``AR`` vendor list, and an ``AR`` version with a ``PB`` list, are refused as before.

What it deliberately leaves alone
---------------------------------
No table, column, CHECK, index, trigger, view or enum moves: ``optimisation_pass`` already records
the vendor list (and so its section), and a stored pass is never revalidated. The application's
choice of vendor list per section lives in ``optimisation/proposals/commands.py``.

Downgrade
---------
Refuses while any ``optimisation_pass`` pins a vendor list of a section other than ``AR``: the
restored ``0028`` function could not have written such a row, the row is the only record of the
pass and its proposals, and an unannounced downgrade would leave it standing in a schema whose
rule it breaks (the pattern of the refusals in ``0006``, ``0029``, ``0032`` and ``0033``). With no
such pass it restores ``0028``'s function exactly, byte for byte, which
``tests/unit/sections/test_pass_scope_migration_text.py`` holds equal to ``0028``'s own text.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0034_pass_scope_all_sections"
down_revision: str | None = "0033_ar_v3_cite_stage_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: ``0028``'s ``am_check_optimisation_pass_scope`` over ``version_classification_current``, restated
#: (a migration is history and must not import another), and restored by the downgrade.
_FUNCTION_0028 = """
        CREATE OR REPLACE FUNCTION am_check_optimisation_pass_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM document d
                JOIN document_version v ON v.document_uid = d.document_uid
                JOIN audit_run r ON r.version_uid = v.version_uid
                JOIN version_classification_current c ON c.version_uid = v.version_uid
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

#: The function this revision installs: ``_FUNCTION_0028`` without the AR condition on the version
#: and with the vendor list's section equal to the version's.
_FUNCTION_0034 = """
        CREATE OR REPLACE FUNCTION am_check_optimisation_pass_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM document d
                JOIN document_version v ON v.document_uid = d.document_uid
                JOIN audit_run r ON r.version_uid = v.version_uid
                JOIN version_classification_current c ON c.version_uid = v.version_uid
                JOIN price_list_revision p ON p.project_uid = d.project_uid
                JOIN vendor_list_revision l ON l.vendor_list_id = NEW.vendor_list_id
                WHERE d.document_uid = NEW.document_uid
                  AND d.project_uid = NEW.project_uid
                  AND v.version_uid = NEW.version_uid
                  AND r.run_id = NEW.run_id
                  AND r.project_uid = NEW.project_uid
                  AND p.price_list_id = NEW.price_list_id
                  AND l.section_code = c.section_code
                  AND l.mode = 'list'
                  AND l.scope = NEW.vendor_list_source
                  AND (l.scope = 'global' OR l.project_uid = NEW.project_uid)
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: optimisation pass % does not pin one classified '
                    'version of its project with that version''s run, a price list of the '
                    'project and a vendor list of that version''s section in force for it',
                    NEW.optimisation_pass_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A pass is written by auditmanager.optimisation.proposals '
                                 'from one consistent read.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

#: The section whose vendor list the restored function still accepts.
_RETAINED_SECTION = "AR"


def upgrade() -> None:
    op.execute(_FUNCTION_0034)


def downgrade() -> None:
    other = op.get_bind().execute(
        text(
            "SELECT count(*) FROM optimisation_pass p "
            "JOIN vendor_list_revision l ON l.vendor_list_id = p.vendor_list_id "
            "WHERE l.section_code <> :retained"
        ),
        {"retained": _RETAINED_SECTION},
    ).scalar_one()
    if other:
        raise RuntimeError(
            f"0034 downgrade refused: {other} optimisation pass(es) pin a vendor list of a section "
            "other than AR; restore a backup instead of downgrading"
        )
    op.execute(_FUNCTION_0028)
