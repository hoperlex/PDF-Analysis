"""The comparison of two versions becomes a record: approved sheet pairings and the AI summary on top.

Revision ID: 0035_comparison_records
Revises: 0034_pass_scope_all_sections

`COMPARE-PERSISTED-SUMMARY-01` (PW4 lane B; owner's `C-2`: «sheet pairing, deterministic text
differences as evidence, AI classification and summary on top; AI never alters the raw
differences»). Until now ``compareDocumentVersions`` was a read that stored nothing: every
pairing was a proposal, and ``comparison.raw_text``, ``raw_evidence_seal`` and ``summary_input``
(written for an approved ``SheetLink`` at a ``link_revision``) had no state to read.

What this revision adds
-----------------------
``comparison_sheet_link`` -- one **append-only** table; every row is one event of one sheet link,
``approved`` or ``withdrawn``. A pairing is never updated and never deleted: withdrawing a link is
a new row naming the same ``sln_<ULID>``. The rows of one comparison (an ordered pair of versions
of one document, identity ``cmp_<ULID>``, allocated at the first row of the pair) are numbered
1, 2, 3, ... without a gap: that number is the ``link_revision`` that ``raw_text``,
``raw_evidence_seal`` and ``summary_input`` already take, and ``(comparison_id, link_revision)``
is the primary key, so two concurrent writers cannot both take the next place.

Identity is by ids and content digests, never by a sheet's display number or a file name: a sheet
is (version id, page number, SHA-256 of the page's text). The page number is a coordinate in an
immutable version; the two digests bind the content the expert saw, and ``suggestion_sha256`` the
proposal (page digests and rule) that was confirmed. ``raw_evidence_seal_sha256`` is the
``raw_evidence_seal`` of the approved set after the row (null only when a withdrawal empties the
set); the application recomputes it on every read.

``am_check_comparison_sheet_link_chain`` -- BEFORE INSERT, ``AM001``: revision n needs n - 1 (1 for
a pair that has no row); every row of a comparison names the same project, document and pair; the
pair is two versions of that document in that project, source older than target, both pages inside
their versions; for ``approved``, neither page is held by an active link and fewer than 32 links
(``raw_text.MAX_PAIRS``) are active; for ``withdrawn``, an approved row of the same link with
exactly the same pages and digests exists (``UNIQUE (comparison_id, sheet_link_id, event_kind)``
makes it once). ``UNIQUE (source_version_uid, target_version_uid, link_revision)`` is the backstop
that a pair cannot have two comparison identities. The function serialises the writers of one
pair with an advisory lock: the application role holds no UPDATE privilege, so it cannot take a
row lock. UPDATE and DELETE are refused (``am_immutable_row``, SQLSTATE ``AM003``).

The **approved set** at a revision is the ``approved`` rows that have no ``withdrawn`` row. It is
a query, not a stored state, so nothing can disagree with the history.

The actor (``actor_user_uid``) is a ``usr_`` identity with a format CHECK and **no foreign key** to
``app_user``: the register of account references (``auditmanager.access.references``) belongs to
the access context, which this revision does not touch. The label is stored beside the id (the
decision ledger's idiom), so the history stays readable if an account is later purged.

**No backfill.** Nothing existed before; the upgrade creates an empty table beside existing rows
and changes none of them.

``comparison_summary`` -- the AI summary over the approved pairs, **append-only** as well. A row holds the
summary of one revision of one comparison: the seal of the raw evidence it summarises, the digest of the
bounded input and of the exact request, the prompt version, the provider mode and model identity
(``recorded`` for a replayed reply), the state (``ready``, or ``rejected`` when the validator refused the
reply -- the reply was paid for, so the rejection is recorded, without statements), the statements as the
model wrote them with the span identities each cites (``<sheet_link_id>:<n>``), the cost through the meter
(``unmetered`` only for the recorded binding) and who asked. The summary never changes the raw differences:
nothing in this table is read back into them. Its identity is an ``audit_event_id`` (``evt_``), the id of the
audit event written in the same transaction (an appended history row is an audit event, as in ``0025``).
``(comparison_id, link_revision)`` references the history; ``am_check_comparison_summary`` (BEFORE INSERT,
``AM001``) requires the revision to be the comparison's **latest**, the project to be the comparison's and the
seal to be the one that revision stored, so a summary can neither describe a superseded approval set nor
another project's evidence. At most one ``ready`` row exists per (comparison, revision, input digest, prompt
version): an exact repeat never pays twice. UPDATE and DELETE are refused (``am_immutable_row``).

The vocabulary (the bounds, the thirty-two) is restated, not imported: a migration is history and
must not move when the application does. ``tests/unit/comparison`` holds the bounds equal to
``auditmanager.comparison``.

Downgrade
---------
Refuses while any row of either table exists: a recorded approval, withdrawal or summary exists
nowhere else, and an unannounced downgrade would drop the expert's work (the pattern of the refusals in
``0006``, ``0029``, ``0032``, ``0033`` and ``0034``). With no row it drops this revision's own objects,
and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0035_comparison_records"
down_revision: str | None = "0034_pass_scope_all_sections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

EVENT_KINDS: tuple[str, ...] = ("approved", "withdrawn")
#: ``raw_text.MAX_PAIRS``: the most pairs one raw artifact accepts, so the most links one
#: comparison may hold active.
MAX_ACTIVE_LINKS = 32
#: ``version_reader.MAX_VERSION_PAGES`` (W55B-SEAL-01, migration 0021): pages of a published version.
MAX_PAGE_NUMBER = 500
MAX_LABEL_LENGTH = 128
SUMMARY_STATES: tuple[str, ...] = ("ready", "rejected")
#: ``summary_validation.REJECTION_REASONS``.
REJECTION_REASONS: tuple[str, ...] = (
    "reply_not_json", "reply_shape_invalid", "unknown_hunk_reference",
)
PROVIDER_MODES: tuple[str, ...] = ("recorded", "live")
COST_BASES: tuple[str, ...] = ("unmetered", "measured", "estimated")
#: ``summary_prompt.MAX_STATEMENTS``.
MAX_STATEMENTS = 20


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_CHAIN_FUNCTION = f"""
        CREATE FUNCTION am_check_comparison_sheet_link_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_revision integer;
            opening comparison_sheet_link%ROWTYPE;
            active_links integer;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended(
                'comparison_sheet_link:' || NEW.source_version_uid || ':' || NEW.target_version_uid,
                0));
            IF NOT EXISTS (
                SELECT 1
                FROM document d
                JOIN document_version s ON s.document_uid = d.document_uid
                JOIN document_version t ON t.document_uid = d.document_uid
                WHERE d.document_uid = NEW.document_uid
                  AND d.project_uid = NEW.project_uid
                  AND s.version_uid = NEW.source_version_uid
                  AND t.version_uid = NEW.target_version_uid
                  AND s.version_ordinal < t.version_ordinal
                  AND NEW.source_page_number <= s.page_count
                  AND NEW.target_page_number <= t.page_count
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: comparison % does not name an older and a newer '
                    'version of one document of its project with both pages inside them',
                    NEW.comparison_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A sheet link is written by auditmanager.comparison from one '
                                 'consistent read.';
            END IF;

            SELECT max(link_revision) INTO last_revision
              FROM comparison_sheet_link WHERE comparison_id = NEW.comparison_id;
            IF last_revision IS NULL THEN
                IF NEW.link_revision <> 1 OR EXISTS (
                    SELECT 1 FROM comparison_sheet_link x
                     WHERE x.source_version_uid = NEW.source_version_uid
                       AND x.target_version_uid = NEW.target_version_uid
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: comparison % starts at revision 1 and only '
                        'for a pair of versions that has no comparison yet', NEW.comparison_id
                        USING ERRCODE = 'AM001',
                              HINT = 'One ordered pair of versions has one comparison identity.';
                END IF;
            ELSE
                IF NEW.link_revision <> last_revision + 1 THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: comparison % has revision % and cannot take %',
                        NEW.comparison_id, last_revision, NEW.link_revision
                        USING ERRCODE = 'AM001',
                              HINT = 'Revisions are numbered 1, 2, 3, ... without a gap.';
                END IF;
                SELECT * INTO opening FROM comparison_sheet_link
                 WHERE comparison_id = NEW.comparison_id AND link_revision = 1;
                IF opening.project_uid <> NEW.project_uid
                   OR opening.document_uid <> NEW.document_uid
                   OR opening.source_version_uid <> NEW.source_version_uid
                   OR opening.target_version_uid <> NEW.target_version_uid THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: comparison % is of another pair of versions',
                        NEW.comparison_id
                        USING ERRCODE = 'AM001',
                              HINT = 'Every row of a comparison names the pair its first row named.';
                END IF;
            END IF;

            IF NEW.event_kind = 'approved' THEN
                IF EXISTS (
                    SELECT 1 FROM comparison_sheet_link a
                     WHERE a.comparison_id = NEW.comparison_id
                       AND a.event_kind = 'approved'
                       AND (a.source_page_number = NEW.source_page_number
                            OR a.target_page_number = NEW.target_page_number)
                       AND NOT EXISTS (
                           SELECT 1 FROM comparison_sheet_link w
                            WHERE w.comparison_id = a.comparison_id
                              AND w.sheet_link_id = a.sheet_link_id
                              AND w.event_kind = 'withdrawn')
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: a page of comparison % is already held by an '
                        'active sheet link', NEW.comparison_id
                        USING ERRCODE = 'AM001',
                              HINT = 'A source page and a target page each belong to at most one '
                                     'active link; withdraw it first.';
                END IF;
                SELECT count(*) INTO active_links FROM comparison_sheet_link a
                 WHERE a.comparison_id = NEW.comparison_id
                   AND a.event_kind = 'approved'
                   AND NOT EXISTS (
                       SELECT 1 FROM comparison_sheet_link w
                        WHERE w.comparison_id = a.comparison_id
                          AND w.sheet_link_id = a.sheet_link_id
                          AND w.event_kind = 'withdrawn');
                IF active_links >= {MAX_ACTIVE_LINKS} THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: comparison % already has % active sheet links',
                        NEW.comparison_id, active_links
                        USING ERRCODE = 'AM001',
                              HINT = 'One raw artifact accepts at most {MAX_ACTIVE_LINKS} pairs.';
                END IF;
            ELSIF NOT EXISTS (
                SELECT 1 FROM comparison_sheet_link a
                 WHERE a.comparison_id = NEW.comparison_id
                   AND a.sheet_link_id = NEW.sheet_link_id
                   AND a.event_kind = 'approved'
                   AND a.source_page_number = NEW.source_page_number
                   AND a.target_page_number = NEW.target_page_number
                   AND a.source_page_text_sha256 = NEW.source_page_text_sha256
                   AND a.target_page_text_sha256 = NEW.target_page_text_sha256
                   AND a.suggestion_sha256 = NEW.suggestion_sha256
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: sheet link % of comparison % has no approval to '
                    'withdraw', NEW.sheet_link_id, NEW.comparison_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A withdrawal repeats the pages and digests of the approval it ends.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


_SUMMARY_FUNCTION = """
        CREATE FUNCTION am_check_comparison_summary() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM comparison_sheet_link l
                WHERE l.comparison_id = NEW.comparison_id
                  AND l.link_revision = NEW.link_revision
                  AND l.project_uid = NEW.project_uid
                  AND l.raw_evidence_seal_sha256 = NEW.raw_evidence_seal_sha256
                  AND NOT EXISTS (
                      SELECT 1 FROM comparison_sheet_link n
                       WHERE n.comparison_id = l.comparison_id AND n.link_revision > l.link_revision)
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: summary % does not describe the latest approved set '
                    'of comparison % with the seal that revision stored', NEW.summary_id, NEW.comparison_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A summary is written by auditmanager.comparison from the sealed '
                                 'evidence of the latest revision.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_sheet_link (
            comparison_id            text NOT NULL,
            link_revision            integer NOT NULL,
            event_kind               text NOT NULL,
            sheet_link_id            text NOT NULL,
            project_uid              text NOT NULL,
            document_uid             text NOT NULL,
            source_version_uid       text NOT NULL,
            target_version_uid       text NOT NULL,
            source_page_number       integer NOT NULL,
            target_page_number       integer NOT NULL,
            source_page_text_sha256  text NOT NULL,
            target_page_text_sha256  text NOT NULL,
            suggestion_sha256        text NOT NULL,
            raw_evidence_seal_sha256 text NULL,
            actor_user_uid           text NOT NULL,
            actor_label              text NOT NULL,
            command_id               text NOT NULL,
            decided_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_comparison_sheet_link PRIMARY KEY (comparison_id, link_revision),
            CONSTRAINT uq_comparison_sheet_link_pair_revision
                UNIQUE (source_version_uid, target_version_uid, link_revision),
            CONSTRAINT uq_comparison_sheet_link_event
                UNIQUE (comparison_id, sheet_link_id, event_kind),
            CONSTRAINT uq_comparison_sheet_link_command UNIQUE (command_id),
            CONSTRAINT fk_comparison_sheet_link_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_link_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_link_source_version
                FOREIGN KEY (source_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_link_target_version
                FOREIGN KEY (target_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_link_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id)
                ON DELETE RESTRICT,
            CONSTRAINT ck_comparison_sheet_link_comparison_id_format
                CHECK (comparison_id ~ '^cmp_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_sheet_link_id_format
                CHECK (sheet_link_id ~ '^sln_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_project_uid_format
                CHECK (project_uid ~ '^prj_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_document_uid_format
                CHECK (document_uid ~ '^doc_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_source_version_uid_format
                CHECK (source_version_uid ~ '^ver_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_target_version_uid_format
                CHECK (target_version_uid ~ '^ver_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_actor_user_uid_format
                CHECK (actor_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_command_id_format
                CHECK (command_id ~ '^cmd_{ULID}$'),
            CONSTRAINT ck_comparison_sheet_link_link_revision CHECK (link_revision >= 1),
            CONSTRAINT ck_comparison_sheet_link_event_kind
                CHECK (event_kind IN ({_sql_list(EVENT_KINDS)})),
            CONSTRAINT ck_comparison_sheet_link_versions_differ
                CHECK (source_version_uid <> target_version_uid),
            CONSTRAINT ck_comparison_sheet_link_source_page_number
                CHECK (source_page_number BETWEEN 1 AND {MAX_PAGE_NUMBER}),
            CONSTRAINT ck_comparison_sheet_link_target_page_number
                CHECK (target_page_number BETWEEN 1 AND {MAX_PAGE_NUMBER}),
            CONSTRAINT ck_comparison_sheet_link_source_page_text_sha256_format
                CHECK (source_page_text_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_sheet_link_target_page_text_sha256_format
                CHECK (target_page_text_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_sheet_link_suggestion_sha256_format
                CHECK (suggestion_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_sheet_link_raw_evidence_seal_sha256
                CHECK (raw_evidence_seal_sha256 IS NULL
                       OR raw_evidence_seal_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_sheet_link_approved_has_seal
                CHECK (event_kind <> 'approved' OR raw_evidence_seal_sha256 IS NOT NULL),
            CONSTRAINT ck_comparison_sheet_link_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n'))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_link_project ON comparison_sheet_link (project_uid);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_link_target_version "
        "ON comparison_sheet_link (target_version_uid);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_comparison_sheet_link_immutable
            BEFORE UPDATE OR DELETE ON comparison_sheet_link
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(_CHAIN_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_comparison_sheet_link_chain
            BEFORE INSERT ON comparison_sheet_link
            FOR EACH ROW EXECUTE FUNCTION am_check_comparison_sheet_link_chain();
        """
    )
    op.execute(
        "COMMENT ON TABLE comparison_sheet_link IS "
        "'COMPARE-PERSISTED-SUMMARY-01. The approved sheet pairings of two versions of one "
        "document, as an append-only history: one row per approval or withdrawal of one sheet "
        "link, numbered 1, 2, 3, ... per comparison (the link revision). A sheet is a version, a "
        "page coordinate and the SHA-256 of the page text, never a display number. Withdrawal is "
        "a new row. Never updated or deleted (am_immutable_row); each row needs the one before "
        "it and keeps the pair, the pages and the one-to-one rule "
        "(am_check_comparison_sheet_link_chain). The approved set is the approved rows without a "
        "withdrawal.';"
    )
    op.execute(
        "COMMENT ON COLUMN comparison_sheet_link.actor_user_uid IS "
        "'The approving or withdrawing account. Deliberately not a foreign key: the register of "
        "account references belongs to the access context; the label is kept beside it.';"
    )


    op.execute(
        f"""
        CREATE TABLE comparison_summary (
            summary_id               text PRIMARY KEY,
            comparison_id            text NOT NULL,
            link_revision            integer NOT NULL,
            project_uid              text NOT NULL,
            raw_evidence_seal_sha256 text NOT NULL,
            input_sha256             text NOT NULL,
            request_sha256           text NOT NULL,
            prompt_version           text NOT NULL,
            provider_mode            text NOT NULL,
            model_identity           text NOT NULL,
            state                    text NOT NULL,
            rejection_reason         text NULL,
            statements               jsonb NOT NULL,
            cost_basis               text NOT NULL,
            cost_micros              bigint NOT NULL,
            actor_user_uid           text NOT NULL,
            actor_label              text NOT NULL,
            command_id               text NOT NULL,
            created_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_summary_history
                FOREIGN KEY (comparison_id, link_revision)
                REFERENCES comparison_sheet_link (comparison_id, link_revision) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_summary_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_summary_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_summary_command UNIQUE (command_id),
            CONSTRAINT ck_comparison_summary_summary_id_format
                CHECK (summary_id ~ '^evt_{ULID}$'),
            CONSTRAINT ck_comparison_summary_comparison_id_format
                CHECK (comparison_id ~ '^cmp_{ULID}$'),
            CONSTRAINT ck_comparison_summary_project_uid_format
                CHECK (project_uid ~ '^prj_{ULID}$'),
            CONSTRAINT ck_comparison_summary_actor_user_uid_format
                CHECK (actor_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_comparison_summary_command_id_format
                CHECK (command_id ~ '^cmd_{ULID}$'),
            CONSTRAINT ck_comparison_summary_link_revision CHECK (link_revision >= 1),
            CONSTRAINT ck_comparison_summary_raw_evidence_seal_sha256_format
                CHECK (raw_evidence_seal_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_summary_input_sha256_format
                CHECK (input_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_summary_request_sha256_format
                CHECK (request_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_comparison_summary_prompt_version
                CHECK (prompt_version ~ '^[a-z][a-z0-9-]{{2,63}}$'),
            CONSTRAINT ck_comparison_summary_provider_mode
                CHECK (provider_mode IN ({_sql_list(PROVIDER_MODES)})),
            CONSTRAINT ck_comparison_summary_model_identity
                CHECK (char_length(model_identity) BETWEEN 1 AND 128),
            CONSTRAINT ck_comparison_summary_state
                CHECK (state IN ({_sql_list(SUMMARY_STATES)})),
            CONSTRAINT ck_comparison_summary_cost_basis
                CHECK (cost_basis IN ({_sql_list(COST_BASES)})),
            CONSTRAINT ck_comparison_summary_cost_micros CHECK (cost_micros >= 0),
            CONSTRAINT ck_comparison_summary_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n')),
            CONSTRAINT ck_comparison_summary_statements_is_array
                CHECK (jsonb_typeof(statements) = 'array'),
            CONSTRAINT ck_comparison_summary_ready_has_statements
                CHECK (state <> 'ready'
                       OR (rejection_reason IS NULL
                           AND CASE WHEN jsonb_typeof(statements) = 'array'
                                    THEN jsonb_array_length(statements) BETWEEN 1 AND {MAX_STATEMENTS}
                                    ELSE false END)),
            CONSTRAINT ck_comparison_summary_rejected_has_a_reason
                CHECK (state <> 'rejected'
                       OR (rejection_reason IS NOT NULL
                           AND rejection_reason IN ({_sql_list(REJECTION_REASONS)})
                           AND CASE WHEN jsonb_typeof(statements) = 'array'
                                    THEN jsonb_array_length(statements) = 0
                                    ELSE false END)),
            CONSTRAINT ck_comparison_summary_unmetered_only_when_recorded
                CHECK (cost_basis <> 'unmetered' OR (provider_mode = 'recorded' AND cost_micros = 0)),
            CONSTRAINT ck_comparison_summary_recorded_is_unmetered
                CHECK (provider_mode <> 'recorded'
                       OR (model_identity = 'recorded' AND cost_basis = 'unmetered'))
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_summary_ready_input "
        "ON comparison_summary (comparison_id, link_revision, input_sha256, prompt_version) "
        "WHERE state = 'ready';"
    )
    op.execute("CREATE INDEX ix_comparison_summary_project ON comparison_summary (project_uid);")
    op.execute(
        """
        CREATE TRIGGER trg_comparison_summary_immutable
            BEFORE UPDATE OR DELETE ON comparison_summary
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(_SUMMARY_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_comparison_summary_latest
            BEFORE INSERT ON comparison_summary
            FOR EACH ROW EXECUTE FUNCTION am_check_comparison_summary();
        """
    )
    op.execute(
        "COMMENT ON TABLE comparison_summary IS "
        "'COMPARE-PERSISTED-SUMMARY-01. The AI summary over the approved sheet pairs of one revision of "
        "a comparison, append-only: the seal and input it summarises, the prompt version, provider mode "
        "and model identity, ready statements citing the spans of the raw differences or a rejected "
        "reply with its reason, the cost through the meter (unmetered only for the recorded binding) and "
        "who asked. It never changes the raw differences. Never updated or deleted (am_immutable_row); "
        "it must describe the comparison''s latest revision with the seal that revision stored "
        "(am_check_comparison_summary); one ready row per revision, input and prompt version.';"
    )


def downgrade() -> None:
    """Refuse while a row exists, otherwise drop this revision's own objects and nothing else."""
    bind = op.get_bind()
    links = bind.execute(text("SELECT count(*) FROM comparison_sheet_link")).scalar_one()
    summaries = bind.execute(text("SELECT count(*) FROM comparison_summary")).scalar_one()
    if links or summaries:
        raise RuntimeError(
            f"0035 downgrade refused: {links} sheet link event(s) and {summaries} summary row(s) "
            "exist nowhere else; restore a backup instead of downgrading"
        )
    op.execute("DROP TABLE comparison_summary;")
    op.execute("DROP FUNCTION am_check_comparison_summary();")
    op.execute("DROP TABLE comparison_sheet_link;")
    op.execute("DROP FUNCTION am_check_comparison_sheet_link_chain();")
