"""Optimisation passes, their cheaper-analog proposals and the experts' decisions on them.

Revision ID: 0027_optimisation_proposals
Revises: 0026_price_lists

`W60-OPT-PROPOSALS-01` (``ROADMAP-TO-BETA.md`` §10.1 A-2..A-5: a proposal is a separate entity
beside findings with its own expert decisions, export and counts; the vendor list a run used
is recorded; a money figure only from matched price-list positions, absent rather than 0).

What this revision adds
-----------------------
``optimisation_pass`` -- one row per pass: its opaque identity (``opp_<ULID>``), the project,
the document set and the **version** it ran on, that version's **published run** and the
digest of the run's saved text layer the specification was read from, the **price-list
revision** and the **vendor-list revision** (with its source: the project's own list or the
global one) it used, the three algorithm versions (extraction, matching, generator), how
many specification rows it read, matched and proposed for, how many proposals it wrote, the
expert who started it and when. Written once, never updated or deleted
(``am_immutable_row``). ``uq_optimisation_pass_inputs`` makes the inputs the pass's natural
key: an exact repeat finds the stored pass instead of writing a second one.

``am_check_optimisation_pass_scope`` -- BEFORE INSERT: the document belongs to the project,
the version to the document, the run to the version; the version is classified ``AR``; the
price list belongs to the project; the vendor list is an ``AR`` list (``mode = 'list'``)
that is either global or this project's, and its scope is the recorded source. Else
``AM001``.

``optimisation_proposal`` -- one immutable row per proposal (``opr_<ULID>``): the pass, a
per-pass ``ordinal`` (display order, never an identity), the type (``cheaper_analog``
only), the specification row's provenance (its ``sr-`` key, page, sheet label, line span,
table, position and text), the matched and the proposed price-list positions with the
bases that chose them, the proposed vendor, the unit, the quantity (number and text), both
unit prices, the currency, the **saving** and a rationale. The money rule is a CHECK: the
saving is present exactly when the quantity is a number, and then equals
``(current_unit_price − proposed_unit_price) × quantity``; the proposed price is strictly
lower. ``am_check_optimisation_proposal_prices`` (BEFORE INSERT) holds both prices, the
currency and the vendor equal to the two positions, which must belong to the pass's price
list (``AM001``). ``am_require_optimisation_proposals`` -- a deferred constraint trigger: a
pass is refused at COMMIT unless exactly ``proposal_count`` proposals name it, so no pass is
ever visible with part of its proposals.

``optimisation_proposal_decision`` -- the append-only history of expert decisions
(``opd_<ULID>``): the proposal, a per-proposal ``seq`` (an order and the backstop that two
concurrent appends cannot take the same place; never an identity), the verdict (``accept``,
``reject``, ``revise`` -- ``revise`` requires a comment), the acting account, the claimed
``command_record`` (one decision per idempotency key) and the time. Never updated or
deleted (``am_immutable_row``). The current decision is the latest one, found by query.

**Account references.** ``started_by_user_uid`` and ``actor_user_uid`` are ``RESTRICT``
foreign keys to ``app_user`` and are registered in ``auditmanager.access.references``.

**Findings are untouched.** No column here names a finding or a decision of the findings
ledger, and nothing reads or writes those tables.

**No backfill.** Nothing existed before; the upgrade creates empty tables beside existing
rows and changes none of them.

Downgrade
---------
Drops the three tables and the three trigger functions -- and nothing else (the command
records the passes and decisions claimed stay, as every other command's do). The downgrade
names how many passes, proposals and decisions it drops.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0027_optimisation_proposals"
down_revision: str | None = "0026_price_lists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.optimisation_proposals")

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: Vocabularies and bounds restated rather than imported (a migration is history and must not
#: move when the application does); ``tests/unit/optimisation/proposals`` holds each equal to
#: ``auditmanager.optimisation.proposals``.
PROPOSAL_TYPES: tuple[str, ...] = ("cheaper_analog",)
ANALOG_BASES: tuple[str, ...] = ("code_family", "name_similarity")
MATCH_BASES: tuple[str, ...] = ("code", "mark", "name")
VERDICTS: tuple[str, ...] = ("accept", "reject", "revise")
VENDOR_LIST_SOURCES: tuple[str, ...] = ("global", "project")
MAX_SPECIFICATION_ROWS = 10000
MAX_PROPOSALS_PER_PASS = 30000
MAX_ROW_TEXT = 8000
MAX_ROW_POSITION = 100
MAX_SHEET_LABEL = 100
MAX_QUANTITY_TEXT = 100
MAX_UNIT_LENGTH = 50
MAX_VENDOR_LENGTH = 500
MAX_RATIONALE = 10000
MAX_COMMENT_LENGTH = 2000
MAX_ALGORITHM_LENGTH = 64


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _length(column: str, maximum: int, *, nullable: bool) -> str:
    check = f"char_length({column}) BETWEEN 1 AND {maximum}"
    return f"{column} IS NULL OR {check}" if nullable else check


def _price(column: str) -> str:
    return f"{column} > 0 AND {column} < 1e14 AND scale({column}) <= 6"


def upgrade() -> None:
    _create_pass()
    _create_proposal()
    _create_decision()


def _create_pass() -> None:
    algorithm = f"~ '^[a-z0-9][a-z0-9.+-]{{0,{MAX_ALGORITHM_LENGTH - 1}}}$'"
    op.execute(
        f"""
        CREATE TABLE optimisation_pass (
            optimisation_pass_id     text PRIMARY KEY,
            project_uid              text NOT NULL,
            document_uid             text NOT NULL,
            version_uid              text NOT NULL,
            run_id                   text NOT NULL,
            text_layer_sha256        text NOT NULL,
            price_list_id            text NOT NULL,
            vendor_list_id           text NOT NULL,
            vendor_list_source       text NOT NULL,
            extraction_algorithm     text NOT NULL,
            match_algorithm          text NOT NULL,
            generator_version        text NOT NULL,
            specification_row_count  integer NOT NULL,
            matched_row_count        integer NOT NULL,
            proposed_row_count       integer NOT NULL,
            proposal_count           integer NOT NULL,
            started_by_user_uid      text NOT NULL,
            started_at               timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_optimisation_pass_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_pass_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_pass_version
                FOREIGN KEY (version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_pass_run
                FOREIGN KEY (run_id) REFERENCES audit_run (run_id) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_pass_price_list
                FOREIGN KEY (price_list_id) REFERENCES price_list_revision (price_list_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_pass_vendor_list
                FOREIGN KEY (vendor_list_id) REFERENCES vendor_list_revision (vendor_list_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_pass_started_by
                FOREIGN KEY (started_by_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            CONSTRAINT uq_optimisation_pass_inputs
                UNIQUE (version_uid, run_id, price_list_id, vendor_list_id,
                        extraction_algorithm, match_algorithm, generator_version),
            CONSTRAINT ck_optimisation_pass_optimisation_pass_id_format
                CHECK (optimisation_pass_id ~ '^opp_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_project_uid_format
                CHECK (project_uid ~ '^prj_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_document_uid_format
                CHECK (document_uid ~ '^doc_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_version_uid_format
                CHECK (version_uid ~ '^ver_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_run_id_format
                CHECK (run_id ~ '^run_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_price_list_id_format
                CHECK (price_list_id ~ '^prl_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_vendor_list_id_format
                CHECK (vendor_list_id ~ '^vnl_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_started_by_user_uid_format
                CHECK (started_by_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_optimisation_pass_text_layer_sha256
                CHECK (text_layer_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_optimisation_pass_vendor_list_source
                CHECK (vendor_list_source IN ({_sql_list(VENDOR_LIST_SOURCES)})),
            CONSTRAINT ck_optimisation_pass_algorithms
                CHECK (
                    extraction_algorithm {algorithm}
                    AND match_algorithm {algorithm}
                    AND generator_version {algorithm}
                ),
            CONSTRAINT ck_optimisation_pass_counts
                CHECK (
                    specification_row_count BETWEEN 0 AND {MAX_SPECIFICATION_ROWS}
                    AND matched_row_count BETWEEN 0 AND specification_row_count
                    AND proposed_row_count BETWEEN 0 AND matched_row_count
                    AND proposal_count BETWEEN proposed_row_count AND {MAX_PROPOSALS_PER_PASS}
                    AND (proposal_count = 0) = (proposed_row_count = 0)
                )
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_optimisation_pass_project "
        "ON optimisation_pass (project_uid, started_at DESC, optimisation_pass_id DESC);"
    )
    op.execute(
        "CREATE INDEX ix_optimisation_pass_started_by ON optimisation_pass (started_by_user_uid);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_optimisation_pass_immutable
            BEFORE UPDATE OR DELETE ON optimisation_pass
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        """
        CREATE FUNCTION am_check_optimisation_pass_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM document d
                JOIN document_version v ON v.document_uid = d.document_uid
                JOIN audit_run r ON r.version_uid = v.version_uid
                JOIN document_version_classification c ON c.version_uid = v.version_uid
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
    )
    op.execute(
        """
        CREATE TRIGGER trg_optimisation_pass_scope
            BEFORE INSERT ON optimisation_pass
            FOR EACH ROW EXECUTE FUNCTION am_check_optimisation_pass_scope();
        """
    )
    op.execute(
        "COMMENT ON TABLE optimisation_pass IS "
        "'W60-OPT-PROPOSALS-01. One deterministic optimisation pass over the current AR "
        "version of a document set: the version, its published run and text layer digest, "
        "the price-list and vendor-list revisions it used, the algorithm versions and the "
        "counts. Written once and never updated or deleted (am_immutable_row); the inputs are "
        "its natural key (uq_optimisation_pass_inputs).';"
    )


def _create_proposal() -> None:
    op.execute(
        f"""
        CREATE TABLE optimisation_proposal (
            optimisation_proposal_id  text PRIMARY KEY,
            optimisation_pass_id      text NOT NULL,
            ordinal                   integer NOT NULL,
            proposal_type             text NOT NULL,
            spec_row_key              text NOT NULL,
            page_number               integer NOT NULL,
            sheet_label               text NULL,
            line_start                integer NOT NULL,
            line_end                  integer NOT NULL,
            table_ordinal             integer NOT NULL,
            row_position              text NULL,
            row_text                  text NOT NULL,
            matched_position_id       text NOT NULL,
            matched_basis             text NOT NULL,
            proposed_position_id      text NOT NULL,
            analog_basis              text NOT NULL,
            name_similarity           numeric NOT NULL,
            proposed_vendor           text NOT NULL,
            unit                      text NOT NULL,
            quantity                  numeric NULL,
            quantity_text             text NULL,
            current_unit_price        numeric NOT NULL,
            proposed_unit_price       numeric NOT NULL,
            currency                  text NOT NULL,
            saving                    numeric NULL,
            rationale                 text NOT NULL,
            CONSTRAINT fk_optimisation_proposal_pass
                FOREIGN KEY (optimisation_pass_id)
                REFERENCES optimisation_pass (optimisation_pass_id) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_proposal_matched_position
                FOREIGN KEY (matched_position_id)
                REFERENCES price_list_position (price_list_position_id) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_proposal_proposed_position
                FOREIGN KEY (proposed_position_id)
                REFERENCES price_list_position (price_list_position_id) ON DELETE RESTRICT,
            CONSTRAINT uq_optimisation_proposal_ordinal UNIQUE (optimisation_pass_id, ordinal),
            CONSTRAINT uq_optimisation_proposal_row_position
                UNIQUE (optimisation_pass_id, spec_row_key, proposed_position_id),
            CONSTRAINT ck_optimisation_proposal_optimisation_proposal_id_format
                CHECK (optimisation_proposal_id ~ '^opr_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_optimisation_pass_id_format
                CHECK (optimisation_pass_id ~ '^opp_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_matched_position_id_format
                CHECK (matched_position_id ~ '^prp_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_proposed_position_id_format
                CHECK (proposed_position_id ~ '^prp_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_ordinal
                CHECK (ordinal BETWEEN 1 AND {MAX_PROPOSALS_PER_PASS}),
            CONSTRAINT ck_optimisation_proposal_proposal_type
                CHECK (proposal_type IN ({_sql_list(PROPOSAL_TYPES)})),
            CONSTRAINT ck_optimisation_proposal_spec_row_key
                CHECK (spec_row_key ~ '^sr-[0-9a-f]{{32}}$'),
            CONSTRAINT ck_optimisation_proposal_provenance
                CHECK (
                    page_number >= 1
                    AND line_start >= 1
                    AND line_end >= line_start
                    AND table_ordinal >= 1
                ),
            CONSTRAINT ck_optimisation_proposal_sheet_label
                CHECK ({_length('sheet_label', MAX_SHEET_LABEL, nullable=True)}),
            CONSTRAINT ck_optimisation_proposal_row_position
                CHECK ({_length('row_position', MAX_ROW_POSITION, nullable=True)}),
            CONSTRAINT ck_optimisation_proposal_row_text
                CHECK ({_length('row_text', MAX_ROW_TEXT, nullable=False)}),
            CONSTRAINT ck_optimisation_proposal_matched_basis
                CHECK (matched_basis IN ({_sql_list(MATCH_BASES)})),
            CONSTRAINT ck_optimisation_proposal_analog_basis
                CHECK (analog_basis IN ({_sql_list(ANALOG_BASES)})),
            CONSTRAINT ck_optimisation_proposal_name_similarity
                CHECK (name_similarity BETWEEN 0 AND 1 AND scale(name_similarity) <= 4),
            CONSTRAINT ck_optimisation_proposal_another_position
                CHECK (proposed_position_id <> matched_position_id),
            CONSTRAINT ck_optimisation_proposal_proposed_vendor
                CHECK ({_length('proposed_vendor', MAX_VENDOR_LENGTH, nullable=False)}),
            CONSTRAINT ck_optimisation_proposal_unit
                CHECK ({_length('unit', MAX_UNIT_LENGTH, nullable=False)}),
            CONSTRAINT ck_optimisation_proposal_quantity
                CHECK (quantity IS NULL OR (quantity >= 0 AND quantity < 1e13)),
            CONSTRAINT ck_optimisation_proposal_quantity_text
                CHECK ({_length('quantity_text', MAX_QUANTITY_TEXT, nullable=True)}),
            CONSTRAINT ck_optimisation_proposal_prices
                CHECK (
                    {_price('current_unit_price')}
                    AND {_price('proposed_unit_price')}
                    AND proposed_unit_price < current_unit_price
                ),
            CONSTRAINT ck_optimisation_proposal_currency CHECK (currency ~ '^[A-Z]{{3}}$'),
            CONSTRAINT ck_optimisation_proposal_saving_presence
                CHECK ((saving IS NULL) = (quantity IS NULL)),
            CONSTRAINT ck_optimisation_proposal_saving_value
                CHECK (
                    saving IS NULL
                    OR saving = (current_unit_price - proposed_unit_price) * quantity
                ),
            CONSTRAINT ck_optimisation_proposal_rationale
                CHECK ({_length('rationale', MAX_RATIONALE, nullable=False)})
        );
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_optimisation_proposal_immutable
            BEFORE UPDATE OR DELETE ON optimisation_proposal
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        """
        CREATE FUNCTION am_check_optimisation_proposal_prices() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM optimisation_pass s
                JOIN price_list_position m ON m.price_list_position_id = NEW.matched_position_id
                JOIN price_list_position p ON p.price_list_position_id = NEW.proposed_position_id
                WHERE s.optimisation_pass_id = NEW.optimisation_pass_id
                  AND m.price_list_id = s.price_list_id
                  AND p.price_list_id = s.price_list_id
                  AND m.unit_price = NEW.current_unit_price
                  AND p.unit_price = NEW.proposed_unit_price
                  AND m.currency = NEW.currency
                  AND p.currency = NEW.currency
                  AND p.vendor = NEW.proposed_vendor
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: optimisation proposal % does not take its '
                    'prices, currency and vendor from two positions of its pass''s price list',
                    NEW.optimisation_proposal_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A money figure exists only from matched price-list '
                                 'positions (ROADMAP-TO-BETA A-4/A-5).';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_optimisation_proposal_prices
            BEFORE INSERT ON optimisation_proposal
            FOR EACH ROW EXECUTE FUNCTION am_check_optimisation_proposal_prices();
        """
    )
    op.execute(
        "COMMENT ON TABLE optimisation_proposal IS "
        "'W60-OPT-PROPOSALS-01. One deterministic proposal of a pass (cheaper_analog): the "
        "specification row''s provenance, the matched and proposed price-list positions, "
        "both unit prices, the currency and the saving -- present only with a numeric "
        "quantity, equal to (current - proposed) x quantity. ordinal is a display order "
        "inside the pass, never an identity. Never updated or deleted (am_immutable_row).';"
    )
    op.execute(
        """
        CREATE FUNCTION am_require_optimisation_proposals() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            found integer;
        BEGIN
            SELECT count(*) INTO found FROM optimisation_proposal
            WHERE optimisation_pass_id = NEW.optimisation_pass_id;
            IF found <> NEW.proposal_count THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: optimisation pass % has % proposal(s), '
                    'declares %', NEW.optimisation_pass_id, found, NEW.proposal_count
                    USING ERRCODE = 'AM001',
                          HINT = 'A pass is written together with every proposal in one '
                                 'transaction.';
            END IF;
            RETURN NULL;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_optimisation_pass_has_proposals
            AFTER INSERT ON optimisation_pass
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_require_optimisation_proposals();
        """
    )


def _create_decision() -> None:
    op.execute(
        f"""
        CREATE TABLE optimisation_proposal_decision (
            proposal_decision_id      text PRIMARY KEY,
            optimisation_proposal_id  text NOT NULL,
            seq                       integer NOT NULL,
            verdict                   text NOT NULL,
            comment                   text NULL,
            actor_user_uid            text NOT NULL,
            command_id                text NOT NULL,
            decided_at                timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_optimisation_proposal_decision_proposal
                FOREIGN KEY (optimisation_proposal_id)
                REFERENCES optimisation_proposal (optimisation_proposal_id) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_proposal_decision_actor
                FOREIGN KEY (actor_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_optimisation_proposal_decision_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_optimisation_proposal_decision_seq
                UNIQUE (optimisation_proposal_id, seq),
            CONSTRAINT uq_optimisation_proposal_decision_command UNIQUE (command_id),
            CONSTRAINT ck_optimisation_proposal_decision_proposal_decision_id_format
                CHECK (proposal_decision_id ~ '^opd_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_decision_proposal_id_format
                CHECK (optimisation_proposal_id ~ '^opr_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_decision_actor_user_uid_format
                CHECK (actor_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_decision_command_id_format
                CHECK (command_id ~ '^cmd_{ULID}$'),
            CONSTRAINT ck_optimisation_proposal_decision_seq CHECK (seq >= 1),
            CONSTRAINT ck_optimisation_proposal_decision_verdict
                CHECK (verdict IN ({_sql_list(VERDICTS)})),
            CONSTRAINT ck_optimisation_proposal_decision_comment
                CHECK ({_length('comment', MAX_COMMENT_LENGTH, nullable=True)}),
            CONSTRAINT ck_optimisation_proposal_decision_revise_has_comment
                CHECK (verdict <> 'revise' OR comment IS NOT NULL)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_optimisation_proposal_decision_actor "
        "ON optimisation_proposal_decision (actor_user_uid);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_optimisation_proposal_decision_immutable
            BEFORE UPDATE OR DELETE ON optimisation_proposal_decision
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE optimisation_proposal_decision IS "
        "'W60-OPT-PROPOSALS-01. Append-only expert decisions on one proposal: accept, reject "
        "or revise (with its comment), the acting account, the claimed command and the time. "
        "seq orders one proposal''s decisions and is never an identity; the current decision "
        "is the latest. Never updated or deleted (am_immutable_row).';"
    )


def downgrade() -> None:
    """Drop the three tables and the three trigger functions; nothing else is touched."""
    bind = op.get_bind()
    counts = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
        for table in (
            "optimisation_pass",
            "optimisation_proposal",
            "optimisation_proposal_decision",
        )
    }
    if any(counts.values()):
        _log.warning(
            "0027_optimisation_proposals downgrade: %d optimisation pass(es) with %d "
            "proposal(s) and %d expert decision(s) exist nowhere else and are dropped with "
            "their tables; the command records that claimed them are kept.",
            counts["optimisation_pass"],
            counts["optimisation_proposal"],
            counts["optimisation_proposal_decision"],
        )
    op.execute("DROP TABLE optimisation_proposal_decision;")
    op.execute("DROP TABLE optimisation_proposal;")
    op.execute("DROP TABLE optimisation_pass;")
    op.execute("DROP FUNCTION am_require_optimisation_proposals();")
    op.execute("DROP FUNCTION am_check_optimisation_proposal_prices();")
    op.execute("DROP FUNCTION am_check_optimisation_pass_scope();")
