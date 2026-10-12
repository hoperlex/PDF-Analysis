"""Norm-corpus custody, the paid repair journal, and the effect-journal settlements.

Revision ID: 0018_norm_custody
Revises: 0017_execution_queue

`W54-SEAL-01` (`W54-PLAN.md` sections 3.1 and 3.3; owner rulings R-76, R-79, R-104, R-106).

* ``norm_custody_admission`` is the custody intent **and** its outbox row (R-76's two-phase
  custody, phase one): a role, a generic target (``target_kind`` + ``target_id``), an opaque
  anchor, the content-derived ``blob_id`` and the declared size, SHA-256 and media type. The
  dispatcher drives ``pending`` rows (five tries, then ``poisoned``; ``requeue`` returns one to
  ``pending``) until the bytes are verified and the admission is ``confirmed``. A byte mismatch
  ``rejected`` the admission, never the shared Blob row.
* ``norm_custody_binding`` is phase two, ``publish_bindings(role, target)``: one immutable row
  per confirmed admission, inserted in the transaction that holds the target rows. Its insert
  guard re-checks invariants 1--4 of ``NORM_CORPUS_CUSTODY.md`` at publication time.
* ``ck_norm_custody_role_shape`` -- one CHECK name, on both tables -- maps each role to its
  target kind and anchor kinds. Today: ``norm_source`` -> ``norm_document``, a ``pdf`` or
  ``crop`` anchor. W57a adds its roles by replacing that CHECK (and the binding guard's
  target arm) in its own migration.
* ``norm_repair_call`` is the paid repair journal's database half (R-106): one row per
  provider try, its idempotency scope its own ``nrc`` id, the response checkpointed before
  parsing (``response_received`` with its SHA-256), terminal
  ``completed | not_processed | outcome_unknown``. The response *bytes* are not a column:
  ``test_schema_shape.py`` bans a ``response_body`` (a model payload) from every table, so
  the checkpoint's bytes live beside the fsynced local journal and the row pins their
  SHA-256.
* ``norm_paragraph.text_reliability`` and ``norms_snapshot.unreliable_count`` carry F-4's
  unreliable blocks; ``ck_norms_snapshot_raw_key`` is replaced so the base key equals the
  content key exactly when nothing was repaired **and** nothing is unreliable.
* `D-142`: ``analysis_artifact_publication`` gains ``abandoned`` (``prepared -> abandoned``).
* `D-148`: both effect-table state guards run ``BEFORE INSERT OR UPDATE``; an insert must be
  ``prepared``.

A populated 0018 is not downgraded: custody, journal or settlement rows refuse it, and a
database backup is restored instead.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0018_norm_custody"
down_revision: str | None = "0017_execution_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}"
SHA256 = "~ '^[0-9a-f]{64}$'"
CLASSIFIER = "~ '^[a-z][a-z0-9_]{2,63}$'"

#: The custody roles this migration admits, and the shape each one requires. W57a replaces
#: ``ck_norm_custody_role_shape`` with a wider disjunction; nothing else names the roles.
ROLE_SHAPE = (
    "(role = 'norm_source' AND target_kind = 'norm_document' "
    f"AND target_id ~ '^ndoc_{ULID_BODY}$' AND anchor_kind IN ('pdf', 'crop'))"
)

#: Admission states. ``confirmed`` and ``rejected`` are terminal.
ADMISSION_STATES: tuple[str, ...] = ("pending", "confirmed", "poisoned", "rejected")
#: R-76 / E-7: five dispatch tries (30 s ... 2 h), then ``poisoned``.
ADMISSION_MAX_ATTEMPTS = 5

#: Repair-call states. The last three are terminal (R-106).
REPAIR_CALL_STATES: tuple[str, ...] = (
    "prepared", "response_received", "completed", "not_processed", "outcome_unknown",
)

_SLOT_COLUMNS = "role, target_kind, target_id, anchor_kind, anchor"


def _id_check(column: str, prefix: str) -> str:
    return f"{column} ~ '^{prefix}_{ULID_BODY}$'"


def _in(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


# --- the durable-effect guard (D-142, D-148) ---------------------------------------------

_PROVIDER_MUTABLE = (
    "'state', 'response_sha256', 'input_tokens', 'output_tokens', "
    "'latency_ms', 'error_code', 'final_model_call_id', 'updated_at', 'dispatch_class'"
)


def _effect_guard_sql(*, with_insert_and_abandoned: bool) -> str:
    """``am_guard_durable_effect_transition`` as 0018 has it, or as 0017 left it."""
    insert_arm = (
        """
            IF TG_OP = 'INSERT' THEN
                IF NEW.state IS DISTINCT FROM 'prepared' THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: % may not be created in state %',
                        TG_TABLE_NAME, coalesce(NEW.state, '<null>')
                        USING ERRCODE = 'AM001',
                              HINT = 'A durable effect is always created prepared.';
                END IF;
                RETURN NEW;
            END IF;
        """
        if with_insert_and_abandoned else ""
    )
    abandoned_arm = (
        """
            IF TG_TABLE_NAME = 'analysis_artifact_publication'
               AND OLD.state = 'prepared' AND NEW.state = 'abandoned' THEN
                IF (to_jsonb(OLD) - ARRAY['state', 'abandoned_at']) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY['state', 'abandoned_at']) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: artifact publication identity is immutable'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
        """
        if with_insert_and_abandoned else ""
    )
    return f"""
        CREATE OR REPLACE FUNCTION am_guard_durable_effect_transition() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            {insert_arm}
            IF OLD.state IS NOT DISTINCT FROM NEW.state THEN
                IF OLD IS DISTINCT FROM NEW THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: durable effect rows are immutable within a state'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_TABLE_NAME = 'provider_call_effect' AND (
                (OLD.state = 'prepared' AND NEW.state IN ('response_received', 'outcome_unknown', 'not_processed'))
                OR (OLD.state = 'response_received' AND NEW.state = 'completed')
                OR (OLD.state IN ('prepared', 'response_received')
                    AND NEW.state = 'abandoned')
            ) THEN
                IF (to_jsonb(OLD) - ARRAY[{_PROVIDER_MUTABLE}]) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY[{_PROVIDER_MUTABLE}]) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: provider effect identity is immutable'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_TABLE_NAME = 'analysis_artifact_publication'
               AND OLD.state = 'prepared' AND NEW.state = 'bound' THEN
                IF (to_jsonb(OLD) - ARRAY['state', 'artifact_role', 'bound_at']) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY['state', 'artifact_role', 'bound_at']) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: artifact publication identity is immutable'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            {abandoned_arm}
            RAISE EXCEPTION 'state_transition_not_allowed: invalid durable effect transition'
                USING ERRCODE = 'AM001';
        END
        $fn$;
    """


def _effect_triggers(events: str) -> None:
    for table, trigger in (
        ("provider_call_effect", "trg_provider_call_effect_state_guard"),
        ("analysis_artifact_publication", "trg_analysis_artifact_state_guard"),
    ):
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
        op.execute(
            f"CREATE TRIGGER {trigger} BEFORE {events} ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_durable_effect_transition()"
        )


# --- upgrade ------------------------------------------------------------------------------


def upgrade() -> None:
    _settle_artifact_publications()
    _create_custody()
    _create_repair_journal()
    _mark_unreliable_text()


def _settle_artifact_publications() -> None:
    op.execute("ALTER TABLE analysis_artifact_publication ADD COLUMN abandoned_at timestamptz NULL")
    op.execute("ALTER TABLE analysis_artifact_publication DROP CONSTRAINT ck_analysis_artifact_state")
    op.execute(
        "ALTER TABLE analysis_artifact_publication ADD CONSTRAINT ck_analysis_artifact_state "
        "CHECK (state IN ('prepared', 'bound', 'abandoned'))"
    )
    op.execute(
        "ALTER TABLE analysis_artifact_publication ADD CONSTRAINT "
        "ck_analysis_artifact_abandoned_shape CHECK ((state = 'abandoned') = (abandoned_at IS NOT NULL))"
    )
    op.execute(_effect_guard_sql(with_insert_and_abandoned=True))
    _effect_triggers("INSERT OR UPDATE")


def _create_custody() -> None:
    op.execute(
        f"""
        CREATE TABLE norm_custody_admission (
            norm_custody_admission_id text PRIMARY KEY,
            role                text NOT NULL,
            target_kind         text NOT NULL,
            target_id           text NOT NULL,
            anchor_kind         text NOT NULL,
            anchor              text NOT NULL,
            blob_id             text NOT NULL,
            declared_size_bytes bigint NOT NULL,
            declared_sha256     text NOT NULL,
            media_type          text NOT NULL,
            state               text NOT NULL DEFAULT 'pending',
            attempt_count       integer NOT NULL DEFAULT 0,
            available_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
            last_failure        text NULL,
            created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            confirmed_at        timestamptz NULL,
            CONSTRAINT ck_norm_custody_admission_id_format
                CHECK ({_id_check('norm_custody_admission_id', 'nad')}),
            CONSTRAINT ck_norm_custody_role_shape CHECK {ROLE_SHAPE},
            CONSTRAINT ck_norm_custody_admission_anchor
                CHECK (char_length(anchor) BETWEEN 1 AND 500),
            CONSTRAINT ck_norm_custody_admission_blob_id_format
                CHECK ({_id_check('blob_id', 'blob')}),
            CONSTRAINT ck_norm_custody_admission_size CHECK (declared_size_bytes >= 0),
            CONSTRAINT ck_norm_custody_admission_sha256 CHECK (declared_sha256 {SHA256}),
            CONSTRAINT ck_norm_custody_admission_media_type
                CHECK (char_length(media_type) BETWEEN 1 AND 255),
            CONSTRAINT ck_norm_custody_admission_state
                CHECK (state IN ({_in(ADMISSION_STATES)})),
            CONSTRAINT ck_norm_custody_admission_attempts
                CHECK (attempt_count BETWEEN 0 AND {ADMISSION_MAX_ATTEMPTS}),
            CONSTRAINT ck_norm_custody_admission_failure
                CHECK (last_failure IS NULL OR last_failure {CLASSIFIER}),
            CONSTRAINT ck_norm_custody_admission_confirmed_shape
                CHECK ((state = 'confirmed') = (confirmed_at IS NOT NULL)),
            CONSTRAINT ck_norm_custody_admission_failed_shape
                CHECK (state NOT IN ('poisoned', 'rejected') OR last_failure IS NOT NULL),
            CONSTRAINT uq_norm_custody_admission_binding_tuple
                UNIQUE (norm_custody_admission_id, {_SLOT_COLUMNS}, blob_id)
        );
        """
    )
    # One live admission per binding slot; a rejected one leaves the slot free for a
    # corrected admission with a new ``nad`` identity.
    op.execute(
        f"CREATE UNIQUE INDEX uq_norm_custody_admission_live_slot "
        f"ON norm_custody_admission ({_SLOT_COLUMNS}) WHERE state <> 'rejected'"
    )
    op.execute(
        "CREATE INDEX ix_norm_custody_admission_dispatch "
        "ON norm_custody_admission (available_at, norm_custody_admission_id) "
        "WHERE state = 'pending'"
    )
    op.execute("CREATE INDEX ix_norm_custody_admission_blob_id ON norm_custody_admission (blob_id)")
    op.execute(
        "COMMENT ON TABLE norm_custody_admission IS "
        "'R-76 custody intent and outbox row. The anchor, target_id, file names and checksums "
        "are attributes; norm_custody_admission_id (nad) is the only identity.';"
    )

    op.execute(
        f"""
        CREATE TABLE norm_custody_binding (
            norm_custody_binding_id   text PRIMARY KEY,
            norm_custody_admission_id text NOT NULL,
            role        text NOT NULL,
            target_kind text NOT NULL,
            target_id   text NOT NULL,
            anchor_kind text NOT NULL,
            anchor      text NOT NULL,
            blob_id     text NOT NULL REFERENCES blob (blob_id),
            bound_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_norm_custody_binding_id_format
                CHECK ({_id_check('norm_custody_binding_id', 'nbd')}),
            CONSTRAINT ck_norm_custody_binding_admission_id_format
                CHECK ({_id_check('norm_custody_admission_id', 'nad')}),
            CONSTRAINT ck_norm_custody_binding_blob_id_format
                CHECK ({_id_check('blob_id', 'blob')}),
            CONSTRAINT ck_norm_custody_role_shape CHECK {ROLE_SHAPE},
            CONSTRAINT uq_norm_custody_binding_admission UNIQUE (norm_custody_admission_id),
            CONSTRAINT uq_norm_custody_binding_slot UNIQUE ({_SLOT_COLUMNS}),
            CONSTRAINT fk_norm_custody_binding_admission_tuple
                FOREIGN KEY (norm_custody_admission_id, {_SLOT_COLUMNS}, blob_id)
                REFERENCES norm_custody_admission (norm_custody_admission_id, {_SLOT_COLUMNS}, blob_id)
        );
        """
    )
    op.execute("CREATE INDEX ix_norm_custody_binding_blob_id ON norm_custody_binding (blob_id)")
    op.execute(
        "CREATE INDEX ix_norm_custody_binding_target "
        "ON norm_custody_binding (target_kind, target_id)"
    )
    op.execute(
        "COMMENT ON TABLE norm_custody_binding IS "
        "'R-76 published custody binding: a confirmed admission made visible in the "
        "transaction that holds its target. Retained in full (NORM-Q06).';"
    )

    op.execute(
        f"""
        CREATE FUNCTION am_guard_norm_custody_admission() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'state_transition_not_allowed: custody admissions are never deleted'
                    USING ERRCODE = 'AM003';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.state IS DISTINCT FROM 'pending' OR NEW.attempt_count <> 0 THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: a custody admission is created pending with no attempt'
                        USING ERRCODE = 'AM001';
                END IF;
                RETURN NEW;
            END IF;
            IF (to_jsonb(OLD) - ARRAY['state', 'attempt_count', 'available_at', 'last_failure',
                                      'updated_at', 'confirmed_at']) IS DISTINCT FROM
               (to_jsonb(NEW) - ARRAY['state', 'attempt_count', 'available_at', 'last_failure',
                                      'updated_at', 'confirmed_at']) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: custody admission identity is immutable'
                    USING ERRCODE = 'AM003';
            END IF;
            IF OLD.state IN ('confirmed', 'rejected') THEN
                IF OLD IS DISTINCT FROM NEW THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: a % custody admission is terminal', OLD.state
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.state = NEW.state
               OR (OLD.state = 'pending' AND NEW.state IN ('confirmed', 'poisoned', 'rejected'))
               OR (OLD.state = 'poisoned' AND NEW.state IN ('pending', 'rejected')) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'state_transition_not_allowed: custody admission has no transition % -> %',
                OLD.state, NEW.state
                USING ERRCODE = 'AM001';
        END
        $fn$;
        """
    )
    # Invariants 1-4 of NORM_CORPUS_CUSTODY.md, re-checked where the binding becomes
    # visible: the admission is confirmed, its Blob is available with exactly the declared
    # size, SHA-256 and media type, and the target exists now. An unknown target kind is
    # refused here as well as by the role-shape CHECK.
    op.execute(
        """
        CREATE FUNCTION am_guard_norm_custody_binding() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_admission norm_custody_admission%ROWTYPE;
            v_blob      blob%ROWTYPE;
        BEGIN
            SELECT * INTO v_admission FROM norm_custody_admission
             WHERE norm_custody_admission_id = NEW.norm_custody_admission_id
             FOR KEY SHARE;
            IF NOT FOUND OR v_admission.state IS DISTINCT FROM 'confirmed' THEN
                RAISE EXCEPTION 'state_transition_not_allowed: a custody binding needs a confirmed admission'
                    USING ERRCODE = 'AM001';
            END IF;
            SELECT * INTO v_blob FROM blob WHERE blob_id = NEW.blob_id FOR KEY SHARE;
            IF NOT FOUND OR v_blob.state IS DISTINCT FROM 'available'
               OR v_blob.sha256 IS DISTINCT FROM v_admission.declared_sha256
               OR v_blob.size_bytes IS DISTINCT FROM v_admission.declared_size_bytes
               OR v_blob.media_type IS DISTINCT FROM v_admission.media_type THEN
                RAISE EXCEPTION 'state_transition_not_allowed: a custody binding needs its available, verified blob'
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.target_kind = 'norm_document' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM norm_document WHERE norm_document_id = NEW.target_id
                ) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: the custody binding target does not exist'
                        USING ERRCODE = 'AM001';
                END IF;
            ELSE
                RAISE EXCEPTION 'state_transition_not_allowed: unknown custody target kind %', NEW.target_kind
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_norm_custody_admission_guard
            BEFORE INSERT OR UPDATE OR DELETE ON norm_custody_admission
            FOR EACH ROW EXECUTE FUNCTION am_guard_norm_custody_admission();
        CREATE TRIGGER trg_norm_custody_binding_guard
            BEFORE INSERT ON norm_custody_binding
            FOR EACH ROW EXECUTE FUNCTION am_guard_norm_custody_binding();
        CREATE TRIGGER trg_norm_custody_binding_immutable
            BEFORE UPDATE OR DELETE ON norm_custody_binding
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )


def _create_repair_journal() -> None:
    op.execute(
        f"""
        CREATE TABLE norm_repair_call (
            norm_repair_call_id text PRIMARY KEY,
            idempotency_scope   text NOT NULL,
            block_anchor        text NOT NULL,
            crop_sha256         text NOT NULL,
            request_sha256      text NOT NULL,
            model               text NOT NULL,
            attempt_number      integer NOT NULL,
            state               text NOT NULL DEFAULT 'prepared',
            response_sha256     text NULL,
            response_model      text NULL,
            cost_usd            numeric(12, 6) NULL,
            charged_usd         numeric(12, 6) NULL,
            failure             text NULL,
            prepared_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at         timestamptz NULL,
            CONSTRAINT ck_norm_repair_call_id_format
                CHECK ({_id_check('norm_repair_call_id', 'nrc')}),
            CONSTRAINT ck_norm_repair_call_scope CHECK (idempotency_scope = norm_repair_call_id),
            CONSTRAINT ck_norm_repair_call_block_anchor
                CHECK (char_length(block_anchor) BETWEEN 1 AND 200),
            CONSTRAINT ck_norm_repair_call_crop_sha256 CHECK (crop_sha256 {SHA256}),
            CONSTRAINT ck_norm_repair_call_request_sha256 CHECK (request_sha256 {SHA256}),
            CONSTRAINT ck_norm_repair_call_response_sha256
                CHECK (response_sha256 IS NULL OR response_sha256 {SHA256}),
            CONSTRAINT ck_norm_repair_call_model CHECK (char_length(model) BETWEEN 1 AND 200),
            CONSTRAINT ck_norm_repair_call_response_model
                CHECK (response_model IS NULL OR char_length(response_model) BETWEEN 1 AND 200),
            CONSTRAINT ck_norm_repair_call_attempt CHECK (attempt_number >= 1),
            CONSTRAINT ck_norm_repair_call_state CHECK (state IN ({_in(REPAIR_CALL_STATES)})),
            CONSTRAINT ck_norm_repair_call_money CHECK (
                (cost_usd IS NULL OR cost_usd >= 0) AND (charged_usd IS NULL OR charged_usd >= 0)
            ),
            CONSTRAINT ck_norm_repair_call_failure
                CHECK (failure IS NULL OR failure {CLASSIFIER}),
            CONSTRAINT ck_norm_repair_call_terminal_at CHECK (
                (state IN ('completed', 'not_processed', 'outcome_unknown'))
                = (terminal_at IS NOT NULL)
            ),
            CONSTRAINT ck_norm_repair_call_outcome_shape CHECK (
                (state = 'prepared' AND response_sha256 IS NULL
                    AND response_model IS NULL AND cost_usd IS NULL AND charged_usd IS NULL
                    AND failure IS NULL)
                OR (state = 'response_received' AND response_sha256 IS NOT NULL
                    AND charged_usd IS NULL)
                OR (state = 'completed' AND response_sha256 IS NOT NULL
                    AND charged_usd IS NOT NULL)
                OR (state = 'not_processed' AND response_sha256 IS NULL
                    AND cost_usd IS NULL AND charged_usd = 0 AND failure IS NOT NULL)
                OR (state = 'outcome_unknown' AND response_sha256 IS NULL
                    AND cost_usd IS NULL AND charged_usd IS NOT NULL
                    AND failure IS NOT NULL)
            ),
            CONSTRAINT uq_norm_repair_call_try
                UNIQUE (block_anchor, crop_sha256, model, attempt_number)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_norm_repair_call_unsettled ON norm_repair_call (state, prepared_at) "
        "WHERE state IN ('prepared', 'response_received')"
    )
    op.execute(
        "COMMENT ON TABLE norm_repair_call IS "
        "'R-106 paid repair journal (database half). The fsynced local journal file is "
        "written first; outcome_unknown is never re-paid and counts at its bound.';"
    )
    op.execute(
        """
        CREATE FUNCTION am_guard_norm_repair_call() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'state_transition_not_allowed: repair calls are never deleted'
                    USING ERRCODE = 'AM003';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.state IS DISTINCT FROM 'prepared' THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: a repair call is created prepared'
                        USING ERRCODE = 'AM001';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.state IS NOT DISTINCT FROM NEW.state THEN
                IF OLD IS DISTINCT FROM NEW THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: repair calls are immutable within a state'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF NOT (
                (OLD.state = 'prepared'
                    AND NEW.state IN ('response_received', 'not_processed', 'outcome_unknown'))
                OR (OLD.state = 'response_received' AND NEW.state = 'completed')
            ) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: repair call has no transition % -> %',
                    OLD.state, NEW.state
                    USING ERRCODE = 'AM001';
            END IF;
            IF (to_jsonb(OLD) - ARRAY['state', 'response_sha256', 'response_model',
                                      'cost_usd', 'charged_usd', 'failure', 'updated_at',
                                      'terminal_at']) IS DISTINCT FROM
               (to_jsonb(NEW) - ARRAY['state', 'response_sha256', 'response_model',
                                      'cost_usd', 'charged_usd', 'failure', 'updated_at',
                                      'terminal_at']) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: repair call identity is immutable'
                    USING ERRCODE = 'AM003';
            END IF;
            IF OLD.state = 'response_received'
               AND OLD.response_sha256 IS DISTINCT FROM NEW.response_sha256 THEN
                RAISE EXCEPTION 'state_transition_not_allowed: a checkpointed response is immutable'
                    USING ERRCODE = 'AM003';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_norm_repair_call_guard
            BEFORE INSERT OR UPDATE OR DELETE ON norm_repair_call
            FOR EACH ROW EXECUTE FUNCTION am_guard_norm_repair_call();
        """
    )


def _mark_unreliable_text() -> None:
    # Both tables are immutable to UPDATE and DELETE; adding a column with a constant
    # default rewrites no row and fires no row trigger.
    op.execute(
        "ALTER TABLE norm_paragraph ADD COLUMN text_reliability text NOT NULL DEFAULT 'reliable'"
    )
    op.execute(
        "ALTER TABLE norm_paragraph ADD CONSTRAINT ck_norm_paragraph_text_reliability "
        "CHECK (text_reliability IN ('reliable', 'unreliable'))"
    )
    op.execute("ALTER TABLE norms_snapshot ADD COLUMN unreliable_count integer NOT NULL DEFAULT 0")
    op.execute(
        "ALTER TABLE norms_snapshot ADD CONSTRAINT ck_norms_snapshot_unreliable_count "
        "CHECK (unreliable_count >= 0)"
    )
    op.execute("ALTER TABLE norms_snapshot DROP CONSTRAINT ck_norms_snapshot_raw_key")
    op.execute(
        "ALTER TABLE norms_snapshot ADD CONSTRAINT ck_norms_snapshot_raw_key CHECK ("
        "(repair_count = 0 AND unreliable_count = 0) = (base_content_key = content_key))"
    )
    op.execute(
        "COMMENT ON COLUMN norms_snapshot.unreliable_count IS "
        "'F-4: repair-ledger blocks that did not end REPAIRED (the +<m>u of the content key). "
        "Zero together with repair_count = 0 exactly when the base key is the content key.';"
    )


# --- downgrade ----------------------------------------------------------------------------

_RETAINED_DATA = (
    ("norm_custody_admission", "SELECT EXISTS (SELECT 1 FROM norm_custody_admission)"),
    ("norm_custody_binding", "SELECT EXISTS (SELECT 1 FROM norm_custody_binding)"),
    ("norm_repair_call", "SELECT EXISTS (SELECT 1 FROM norm_repair_call)"),
    ("analysis_artifact_publication.abandoned",
     "SELECT EXISTS (SELECT 1 FROM analysis_artifact_publication WHERE state = 'abandoned')"),
    ("norm_paragraph.unreliable",
     "SELECT EXISTS (SELECT 1 FROM norm_paragraph WHERE text_reliability <> 'reliable')"),
    ("norms_snapshot.unreliable_count",
     "SELECT EXISTS (SELECT 1 FROM norms_snapshot WHERE unreliable_count <> 0)"),
)


def downgrade() -> None:
    bind = op.get_bind()
    retained = [name for name, probe in _RETAINED_DATA if bind.execute(text(probe)).scalar_one()]
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0018_norm_custody with retained custody, repair or "
            f"settlement data ({', '.join(retained)}); restore a database backup instead"
        )
    op.execute("ALTER TABLE norms_snapshot DROP CONSTRAINT ck_norms_snapshot_raw_key")
    op.execute(
        "ALTER TABLE norms_snapshot ADD CONSTRAINT ck_norms_snapshot_raw_key CHECK ("
        "(repair_count = 0 AND base_content_key = content_key) "
        "OR (repair_count > 0 AND base_content_key <> content_key))"
    )
    op.execute("ALTER TABLE norms_snapshot DROP CONSTRAINT ck_norms_snapshot_unreliable_count")
    op.execute("ALTER TABLE norms_snapshot DROP COLUMN unreliable_count")
    op.execute("ALTER TABLE norm_paragraph DROP CONSTRAINT ck_norm_paragraph_text_reliability")
    op.execute("ALTER TABLE norm_paragraph DROP COLUMN text_reliability")

    op.execute("DROP TABLE norm_repair_call")
    op.execute("DROP FUNCTION am_guard_norm_repair_call()")
    op.execute("DROP TABLE norm_custody_binding")
    op.execute("DROP TABLE norm_custody_admission")
    op.execute("DROP FUNCTION am_guard_norm_custody_binding()")
    op.execute("DROP FUNCTION am_guard_norm_custody_admission()")

    _effect_triggers("UPDATE")
    op.execute(_effect_guard_sql(with_insert_and_abandoned=False))
    op.execute(
        "ALTER TABLE analysis_artifact_publication DROP CONSTRAINT "
        "ck_analysis_artifact_abandoned_shape"
    )
    op.execute("ALTER TABLE analysis_artifact_publication DROP CONSTRAINT ck_analysis_artifact_state")
    op.execute(
        "ALTER TABLE analysis_artifact_publication ADD CONSTRAINT ck_analysis_artifact_state "
        "CHECK (state IN ('prepared', 'bound'))"
    )
    op.execute("ALTER TABLE analysis_artifact_publication DROP COLUMN abandoned_at")
