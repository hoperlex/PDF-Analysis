"""The project section: ``document.section``, nullable, checked against legacy's fourteen.

Revision ID: 0011_document_section
Revises: 0010_run_terminal_detail

`R-40`, both halves taken deliberately against the drafting session's cheaper
recommendation (`docs/program/OWNER_RULINGS_2026-09-17.md` section 3.15): the field and its
aggregation land in the same wave. This revision is the field.

`D-56` measured the shape: legacy organises every document into one of fourteen project
sections (``backend/app/pipeline/stages/prepare/task_builder.py:1362``) --

    AR, AI, KM, KJ, OV, EOM, VK, PT, PB, SS, ITP, GP, TX, POS

-- and ours carried none. The fourteen codes are restated here as a CHECK rather than
imported, for the same reason ``0002``'s ``ERROR_CODES`` restates the catalog rather than
reading it: a migration that imports application code changes meaning when that code
changes, and ``tests/contract/domain_p02/test_project_section_catalog.py`` is what asserts
this list and ``auditmanager.api.schemas.models.ProjectSection`` agree.

Where the field lives, argued in full in ``docs/program/W46-SEAL.md`` section 2: on
``document``, not ``document_version`` or ``project``. A section classifies *what a
document is* -- a document's category of evidence -- not which revision of its bytes a
reviewer is looking at, and a project has many sections in it rather than being one, so
neither of the other two candidates can carry a single value for it.

Why nullable, and why this is not the `0009` shape restated
-------------------------------------------------------------
The obvious alternative is ``NOT NULL``, forcing every upload to choose. It is refused for
a reason distinct from ``0009``'s -- that revision kept ``NULL`` to preserve a fact a
backfill would have destroyed; this column starts with **no rows to backfill at all**, so
that argument does not apply here.

The reason is the brief's own: **absent is not empty**, and the programme's guard family
about it is not only about a collection reading empty -- it is about a fact nobody has
supplied being a different answer from a fact recorded as a known one. A ``NOT NULL``
column with no server-chosen default would force every existing caller of
``upload_single_pdf`` -- and every multipart caller of ``uploadDocument`` that predates this
reseal, `tests/e2e/**` among them, which this session does not own and may not edit -- to
start naming a section it may not know, on pain of a write failing. A document a reviewer
has not yet classified is a real, common state, not a defect, and forcing a guess at upload
time would put a fabricated classification in the one place ``AGENTS.md`` section 4 forbids
inventing one: an append-only fact about what a document is. So this stays alongside
``document.display_title`` in one more respect -- ``UploadDocumentRequest.section`` is
optional in the frozen contract, exactly as ``display_title`` is, and a caller that omits it
gets a document with no section rather than a refused upload.

The per-section aggregation this same wave adds (``getDashboardSummary``,
``section_breakdown``) answers for the unclassified case honestly: a bucket with no
``section`` property is not fabricated to look like one of the fourteen, and it is not
dropped from the response either -- see that operation's contract description.

The CHECK
---------
``section IS NULL OR section IN (...)`` -- the fourteen codes, and nothing else. A caller
cannot write a fifteenth section through this column any more than through the contract's
``ProjectSection`` enum; the CHECK is what makes that a property of the table, not only of
one edge that validates it, matching this migration's own convention (``0009``'s
``ck_app_user_display_name``, ``0010``'s two ``terminal_detail`` checks).

No index. Fourteen values plus NULL over a table this alpha's data volumes never approach a
sequential scan on is not a query this migration needs to make cheap; one can be added
later without a second reseal, because an index is not part of the contract.

Downgrade
---------
Drops the column and its CHECK. Every value it held was typed at upload time and exists
nowhere else, so the downgrade is loud about what it destroys, in the same shape ``0009``'s
downgrade is loud about display names -- an operator downgrading during an incident is told
the cost rather than finding out afterwards.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0011_document_section"
down_revision: str | None = "0010_run_terminal_detail"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.document_section")

#: `D-56`'s fourteen, verbatim. Restated (not imported) for the reason the module
#: docstring gives; kept in one place here so the CHECK and the log line below cannot
#: disagree with each other.
PROJECT_SECTIONS: tuple[str, ...] = (
    "AR",
    "AI",
    "KM",
    "KJ",
    "OV",
    "EOM",
    "VK",
    "PT",
    "PB",
    "SS",
    "ITP",
    "GP",
    "TX",
    "POS",
)


def _section_list_sql() -> str:
    return ", ".join(f"'{code}'" for code in PROJECT_SECTIONS)


def upgrade() -> None:
    op.execute("ALTER TABLE document ADD COLUMN section text;")
    op.execute(
        f"""
        ALTER TABLE document
            ADD CONSTRAINT ck_document_section CHECK (
                section IS NULL OR section IN ({_section_list_sql()})
            );
        """
    )
    op.execute(
        "COMMENT ON COLUMN document.section IS "
        "'One of legacy''s fourteen project sections (D-56), or NULL for a document "
        "nobody has classified yet. NULL is never backfilled and never treated as a "
        "fifteenth section -- absent is not empty. Set once, at upload "
        "(UploadDocumentRequest.section), and never rewritten: a reclassification is a "
        "decision this contract does not yet publish a way to make, not a value this "
        "column silently changes under a caller.';"
    )


def downgrade() -> None:
    """Drop the column, after naming every document whose classification it destroys.

    See the module docstring: a section is typed once at upload and lives nowhere else,
    so unlike ``0011``'s own upgrade this loses real, unrecoverable classification work
    the moment it runs.
    """
    classified = (
        op.get_bind()
        .execute(
            text(
                "SELECT document_uid, section FROM document "
                "WHERE section IS NOT NULL ORDER BY document_uid"
            )
        )
        .all()
    )
    if classified:
        _log.warning(
            "0011_document_section downgrade: %d document(s) carry a section somebody "
            "typed and it exists nowhere else (%s). Dropping the column destroys it. "
            "Every document keeps working with no section, exactly like a document that "
            "was never classified.",
            len(classified),
            ", ".join(f"{doc} ({section})" for doc, section in classified),
        )
    op.execute("ALTER TABLE document DROP CONSTRAINT ck_document_section;")
    op.execute("ALTER TABLE document DROP COLUMN section;")
