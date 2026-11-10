"""0064 -- the storage of the «Прецеденты» programme (`CRIT-SEAL-50`, plan-v5 section 3.1; contract 1.51.0).

Revision ID: 0064_precedents_seal
Revises: 0063_drop_ar_v3_beta

`CRIT-SEAL-50` (the owner-approved plan of 2026-11-10; it lands on the AR v3 removal wave, which took ``0063`` and contract 1.50.0 (`R-154h`): precedents for the expert, norms for the critic through the executor client, the
night encoder and «один список»). It creates the storage of the surface of contract 1.50.0 and nothing that behaves: no statement writes
any of it until a later lane implements the operation or the pass that does. Every addition to an existing table is nullable or
defaulted, so a database at ``0063`` upgrades with no row touched.

What this revision adds
-----------------------
The decision memory (KEEP, content side: deletable only by a forget of the case)
    ``decision_memory_comment`` -- the experts' comments on a case (Р5), a table of its own beside the decision. ``decision_memory_block_evidence``
    -- the memory's copy of a block-grounded evidence item (``finding_block_evidence``). ``decision_memory_embedding_intent`` (``dmi``) and
    ``decision_memory_embedding`` -- the encoder's queue (``pending`` / ``done`` / ``poisoned``) and the vectors of cases (``bge-m3-dense-v1``,
    1024 dimensions, unit norm, **no HNSW index**: the search is an exact scan by section). All four take the forget guard of ``0061``
    (``am_guard_decision_memory_forget``: ``DELETE`` only beside a ``forget`` event of the same case in the same transaction) **and** a guard
    on ``INSERT`` (``am_guard_decision_memory_forgotten_insert``: nothing is added to a forgotten case, ``D-497`` item 1). The intent keeps its
    state transitions, so its guard is ``DELETE`` only plus a frozen-column guard on ``UPDATE``.
``decision_memory_decision.precedent_label_at_decision``, ``precedent_revision`` and ``precedent_history_verdict_shown``
    The label the server was giving the finding at the moment of the expert's decision, and the revision of the pass that gave it (plan
    section 2.1: a decision under a rejection label is not an independent vote); and the verdict of the history fact (hint `p5`, the earlier
    decision on the same document) that was shown at that moment, ``accepted`` or ``rejected``, NULL when none was shown. Written at insertion
    by the capture; NULL for every decision written before this revision. The label and the revision: both or neither; the verdict shown is
    independent of them.
The product side (PRODUCT: leaves with the project)
    ``decision_memory_probe`` -- the query vector of a candidate text of a run, key ``(run_id, input_id, text_sha256)``, a foreign key to
    ``audit_run`` **only**: the finding it becomes is not known yet, and the link to the observation (a bare identity) is written after
    publication. ``decision_memory_precedent_run`` / ``decision_memory_precedent_advice`` -- the state of the «Прецеденты» pass of a run and its
    result per finding (label, vote counts, hint codes, revision); no text. ``finding_block_evidence`` -- a block-grounded evidence item of a
    finding observation (``portal_block_id``, normalised box, crop digest, optional recognised quote); ``finding_evidence`` and its CHECK are
    not touched, and the old ``block_id`` / ``block_ref`` columns (``^b_[0-9]{6}$``) are not reused.
``precedent_setting_event``
    The switches and settings of the programme as an append-only journal the application writes (``INSERT`` for the app role, as
    ``schedule_setting_event``): ``one_list``, ``critic_context``, ``section_labels``, ``stop_words``, ``vector_window``, ``thresholds``; a
    revision per name, numbered without a gap; the actor is an account (RESTRICT). Nothing journalled means every switch is off. The memory's own
    journal ``decision_memory_setting_event`` and ``scripts/recovery/memory_setting.py`` are not touched.
``vector_control`` / ``vector_control_event``
    One row (key ``default``): whether the vectors are paused and the state of the night window (``closed`` / ``draining`` / ``encoding`` /
    ``skipped`` with a reason), and its journal with an actor for the administrator's pause and resume (``execution_control`` has no actor).
``executor_task_context_delivery`` (KEEP, **no foreign key, no text**)
    What the stand handed to an agent as reference data: the opaque task, run and model call, the kind, the status, the cases by identity, the
    character count and the digest of the block. It outlives the erase of the project it was handed for.
``audit_run.publication_mode``
    ``text_only`` (default) or ``one_list``, frozen at the start of the run: the column joins ``trg_audit_run_frozen_guard``, which is created
    again as ``0062`` did for ``stage_plan``. ``one_list`` needs a stage plan.
``finding_observation.grounding_kind`` / ``extended_observation_ref`` / ``related_finding_uid``
    ``text_span`` (default) or ``portal_block``; the reference to the extended-review candidate the observation was published from; and the
    finding the observation is related to (a bare identity: no key into ``finding``).
The vocabularies: the ``FindingCategory`` checks of ``finding`` and ``finding_observation`` gain ``drawing_discrepancy`` and ``cross_source``;
``ck_finding_observation_ungrounded_reason`` gains ``block_not_in_run_geometry``, ``block_crop_mismatch`` and ``block_quote_not_in_recognised``.

Not here: ``norm_crop_render`` (plan section 3.1, the PNG of a norm page). A table that holds a Blob reference needs an entry in
``scripts/recovery/blob_reference_audit.py``, a closed registry the lane that owns this revision may not edit; the table follows when that
file is granted (the report of `CRIT-SEAL-50` says so).

Downgrade
---------
Refused while any row of the new tables, any label on a decision, any one-list run, any block-grounded or related observation, or any finding or
observation of a new category or reason exists: dropping them would turn a fact into silence (AGENTS section 4, no silent fallback). Otherwise it
restores ``0063``'s schema, the frozen list and the checks.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0064_precedents_seal"
#: Lands on the AR v3 removal wave (`R-154h`): its migration is ``20261110_0063_drop_ar_v3_beta.py``. Until that wave is on the branch this
#: revision names a revision the tree does not have yet, so the chain cannot be run; the rebase makes it whole.
down_revision: str | None = "0063_drop_ar_v3_beta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_LABELS = "'none', 'few', 'often_rejected', 'cancel_suggested', 'likely_accepted', 'mixed'"
_HINT_CODES = "'p1', 'p4', 'p5'"
_SETTING_NAMES = "'one_list', 'critic_context', 'section_labels', 'stop_words', 'vector_window', 'thresholds'"
_VIEW_KINDS = "'finding_v1', 'evidence_v1'"
_INTENT_STATES = "'pending', 'done', 'poisoned'"
_PROBE_STATES = "'pending', 'done', 'poisoned'"
_PASS_STATES = "'pending', 'running', 'done', 'failed'"
_WINDOW_STATES = "'closed', 'draining', 'encoding', 'skipped'"
_CONTROL_EVENT_KINDS = "'paused', 'resumed', 'window_closed', 'window_draining', 'window_encoding', 'window_skipped'"
_DELIVERY_KINDS = "'similar_cases', 'patterns'"
_DELIVERY_STATUSES = "'delivered', 'unavailable'"
_PROFILE = "^[a-z0-9][a-z0-9._-]{0,63}$"
_CODE = "^[a-z][a-z0-9_]{0,63}$"
_SHA256 = "^[0-9a-f]{64}$"
_UNIT_NORM = "abs(vector_norm(embedding) - 1.0) <= 0.0001"

#: ``FindingCategory`` as ``0023`` left it, and the two categories of the groups of candidates.
_CATEGORIES_0023 = (
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout", "facade", "roof", "documentation",
    "evacuation", "fire_safety", "accessibility", "insulation", "sound",
)
_NEW_CATEGORIES = ("drawing_discrepancy", "cross_source")
#: ``ck_finding_observation_ungrounded_reason`` as ``0023`` left it, and the three refusals of the gate of block evidence.
_REASONS_0023 = (
    "quotation_absent", "quotation_on_different_page", "span_outside_page", "span_outside_block", "span_length_mismatch",
    "quote_in_recognised_text", "norm_label_unknown", "norm_quote_too_short", "norm_quote_ambiguous", "norm_quote_absent",
    "norm_value_not_in_quote", "stated_value_not_in_evidence",
)
_NEW_REASONS = ("block_not_in_run_geometry", "block_crop_mismatch", "block_quote_not_in_recognised")

#: ``audit_run``'s frozen list as ``0062`` left it, restated: a migration never imports another.
_FROZEN_RUN_0062 = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id', 'preset_revision_id', 'executor_group_revision_id', 'routing_rule_revision_id', "
    "'started_by_user_uid', 'started_from_run_id', 'start_stage_id', 'stage_plan'"
)
_FROZEN_RUN_0064 = _FROZEN_RUN_0062 + ", 'publication_mode'"

#: The tables the forget of a case deletes from, and the guard on their ``INSERT``. Creation order; the downgrade drops in the reverse.
_FORGET_GUARDED = (
    "decision_memory_comment",
    "decision_memory_block_evidence",
    "decision_memory_embedding_intent",
    "decision_memory_embedding",
)

_FORGOTTEN_INSERT_FUNCTION = """
        CREATE FUNCTION am_guard_decision_memory_forgotten_insert() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            -- ``am_guard_decision_memory_status`` lets nothing follow a forget, so a forget event IS the latest event.
            IF EXISTS (
                SELECT 1 FROM decision_memory_status_event e WHERE e.case_id = NEW.case_id AND e.kind = 'forget'
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory case % was forgotten; % takes no new row', NEW.case_id, TG_TABLE_NAME
                    USING ERRCODE = 'AM003',
                          HINT = 'A forgotten case is terminal: it keeps its tombstone and no content is added to it.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def _id(column: str, prefix: str, table: str, *, nullable: bool = False) -> str:
    """A column with its identity-format CHECK, named ``ck_<table>_<column>_format``."""
    check = f"{column} IS NULL OR {column} ~ '^{prefix}_{ULID}$'" if nullable else f"{column} ~ '^{prefix}_{ULID}$'"
    return (
        f"{column} text {'NULL' if nullable else 'NOT NULL'} "
        f"CONSTRAINT ck_{table}_{column}_format CHECK ({check})"
    )


def _guard(table: str, trigger: str, function: str, columns: str) -> None:
    op.execute(f"DROP TRIGGER {trigger} ON {table}")
    op.execute(
        f"CREATE TRIGGER {trigger} BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION {function}({columns})"
    )


def _replace_check(table: str, name: str, expression: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})")


def _literals(values: Sequence[str]) -> str:
    return ", ".join("'" + value + "'" for value in values)


def upgrade() -> None:
    op.execute(_FORGOTTEN_INSERT_FUNCTION)

    # --- the decision memory: comments --------------------------------------------------------------
    op.execute(f"""
        CREATE TABLE decision_memory_comment (
            {_id("comment_id", "dmk", "decision_memory_comment")} PRIMARY KEY,
            {_id("case_id", "dmc", "decision_memory_comment")}
                CONSTRAINT fk_decision_memory_comment_case
                    REFERENCES decision_memory_case (case_id) ON DELETE RESTRICT,
            {_id("source_decision_id", "dec", "decision_memory_comment")}
                CONSTRAINT uq_decision_memory_comment_source UNIQUE,
            author_user_uid text NULL
                CONSTRAINT ck_decision_memory_comment_author_user_uid_format
                    CHECK (author_user_uid IS NULL OR author_user_uid ~ '^usr_{ULID}$'),
            comment text NOT NULL
                CONSTRAINT ck_decision_memory_comment_comment CHECK (char_length(comment) BETWEEN 1 AND 4000),
            decided_at timestamptz NOT NULL,
            captured_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX ix_decision_memory_comment_case ON decision_memory_comment (case_id, decided_at)")

    # --- the decision memory: the label in force at the decision ------------------------------------
    op.execute("""
        ALTER TABLE decision_memory_decision
            ADD COLUMN precedent_label_at_decision text NULL,
            ADD COLUMN precedent_revision integer NULL,
            ADD COLUMN precedent_history_verdict_shown text NULL
    """)
    op.execute(f"""
        ALTER TABLE decision_memory_decision
            ADD CONSTRAINT ck_decision_memory_decision_precedent_label
                CHECK (precedent_label_at_decision IS NULL OR precedent_label_at_decision ~ '{_CODE}'),
            ADD CONSTRAINT ck_decision_memory_decision_precedent_revision
                CHECK (precedent_revision IS NULL OR precedent_revision >= 1),
            ADD CONSTRAINT ck_decision_memory_decision_precedent_pair
                CHECK ((precedent_label_at_decision IS NULL) = (precedent_revision IS NULL)),
            ADD CONSTRAINT ck_decision_memory_decision_precedent_history_verdict_shown
                CHECK (precedent_history_verdict_shown IS NULL OR precedent_history_verdict_shown IN ('accepted', 'rejected'))
    """)

    # --- the decision memory: block evidence --------------------------------------------------------
    op.execute(f"""
        CREATE TABLE decision_memory_block_evidence (
            {_id("case_id", "dmc", "decision_memory_block_evidence")},
            revision integer NOT NULL,
            ordinal integer NOT NULL
                CONSTRAINT ck_decision_memory_block_evidence_ordinal CHECK (ordinal >= 0),
            page_number integer NOT NULL
                CONSTRAINT ck_decision_memory_block_evidence_page_number CHECK (page_number >= 1),
            portal_block_id text NOT NULL
                CONSTRAINT ck_decision_memory_block_evidence_portal_block_id CHECK (portal_block_id ~ '^blk_[0-9a-f]{{32}}$'),
            bbox_x0 double precision NOT NULL,
            bbox_y0 double precision NOT NULL,
            bbox_x1 double precision NOT NULL,
            bbox_y1 double precision NOT NULL,
            crop_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_block_evidence_crop_sha256 CHECK (crop_sha256 ~ '{_SHA256}'),
            recognised_quote text NULL
                CONSTRAINT ck_decision_memory_block_evidence_recognised_quote
                    CHECK (recognised_quote IS NULL OR char_length(recognised_quote) BETWEEN 1 AND 2000),
            CONSTRAINT pk_decision_memory_block_evidence PRIMARY KEY (case_id, revision, ordinal),
            CONSTRAINT fk_decision_memory_block_evidence_content FOREIGN KEY (case_id, revision)
                REFERENCES decision_memory_content (case_id, revision) ON DELETE RESTRICT,
            CONSTRAINT ck_decision_memory_block_evidence_bbox
                CHECK (bbox_x0 >= 0 AND bbox_y0 >= 0 AND bbox_x1 <= 1 AND bbox_y1 <= 1
                       AND bbox_x1 > bbox_x0 AND bbox_y1 > bbox_y0)
        )
    """)

    # --- the decision memory: the encoder's queue and the vectors -----------------------------------
    op.execute(f"""
        CREATE TABLE decision_memory_embedding_intent (
            {_id("intent_id", "dmi", "decision_memory_embedding_intent")} PRIMARY KEY,
            {_id("case_id", "dmc", "decision_memory_embedding_intent")},
            revision integer NOT NULL,
            view_kind text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_intent_view_kind CHECK (view_kind IN ({_VIEW_KINDS})),
            embedding_profile text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_intent_profile CHECK (embedding_profile ~ '{_PROFILE}'),
            input_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_intent_input_sha256 CHECK (input_sha256 ~ '{_SHA256}'),
            state text NOT NULL DEFAULT 'pending'
                CONSTRAINT ck_decision_memory_embedding_intent_state CHECK (state IN ({_INTENT_STATES})),
            attempts smallint NOT NULL DEFAULT 0
                CONSTRAINT ck_decision_memory_embedding_intent_attempts CHECK (attempts BETWEEN 0 AND 5),
            poison_reason text NULL
                CONSTRAINT ck_decision_memory_embedding_intent_poison_reason
                    CHECK (poison_reason IS NULL OR poison_reason ~ '{_CODE}'),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            state_changed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_decision_memory_embedding_intent_content FOREIGN KEY (case_id, revision)
                REFERENCES decision_memory_content (case_id, revision) ON DELETE RESTRICT,
            CONSTRAINT uq_decision_memory_embedding_intent_view
                UNIQUE (case_id, revision, view_kind, embedding_profile),
            CONSTRAINT ck_decision_memory_embedding_intent_poison_pair
                CHECK ((state = 'poisoned') = (poison_reason IS NOT NULL))
        )
    """)
    # The queue is read by state and the encoder deduplicates a batch by the digest of its input.
    op.execute(
        "CREATE INDEX ix_decision_memory_embedding_intent_pending ON decision_memory_embedding_intent (created_at, intent_id) "
        "WHERE state = 'pending'"
    )
    op.execute(
        "CREATE INDEX ix_decision_memory_embedding_intent_input ON decision_memory_embedding_intent (embedding_profile, input_sha256)"
    )
    op.execute(f"""
        CREATE TABLE decision_memory_embedding (
            {_id("case_id", "dmc", "decision_memory_embedding")},
            revision integer NOT NULL,
            view_kind text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_view_kind CHECK (view_kind IN ({_VIEW_KINDS})),
            embedding_profile text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_profile CHECK (embedding_profile ~ '{_PROFILE}'),
            model_revision text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_model_revision CHECK (model_revision ~ '^[0-9a-f]{{40}}$'),
            input_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_input_sha256 CHECK (input_sha256 ~ '{_SHA256}'),
            embedding_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_embedding_embedding_sha256 CHECK (embedding_sha256 ~ '{_SHA256}'),
            embedding vector(1024) NOT NULL,
            embedded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_decision_memory_embedding PRIMARY KEY (case_id, revision, view_kind, embedding_profile),
            CONSTRAINT fk_decision_memory_embedding_content FOREIGN KEY (case_id, revision)
                REFERENCES decision_memory_content (case_id, revision) ON DELETE RESTRICT,
            CONSTRAINT ck_decision_memory_embedding_unit_norm CHECK ({_UNIT_NORM})
        )
    """)
    # No HNSW: a search is an exact scan of the cases of one section (plan section 2.2); the index below serves the dedup and the audit.
    op.execute("CREATE INDEX ix_decision_memory_embedding_input ON decision_memory_embedding (embedding_profile, input_sha256)")

    # The forget guard of ``0061`` (``DELETE`` only beside a forget of the case in the same transaction) and the guard on ``INSERT``.
    for table in ("decision_memory_comment", "decision_memory_block_evidence", "decision_memory_embedding"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_forget_guard BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_forget()"
        )
    # The intent changes state, so ``UPDATE`` is not refused; only its identity is frozen. The guard function lets a ``DELETE`` through
    # only beside a forget, and is attached to ``DELETE`` alone.
    op.execute(
        "CREATE TRIGGER trg_decision_memory_embedding_intent_frozen_guard BEFORE UPDATE ON decision_memory_embedding_intent "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'intent_id', 'case_id', 'revision', 'view_kind', 'embedding_profile', 'input_sha256', 'created_at')"
    )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_embedding_intent_forget_guard BEFORE DELETE ON decision_memory_embedding_intent "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_forget()"
    )
    for table in _FORGET_GUARDED:
        op.execute(
            f"CREATE TRIGGER trg_{table}_forgotten_insert BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_forgotten_insert()"
        )

    # --- the product side: the probe, the pass and its advice ---------------------------------------
    op.execute(f"""
        CREATE TABLE decision_memory_probe (
            {_id("run_id", "run", "decision_memory_probe")}
                CONSTRAINT fk_decision_memory_probe_run REFERENCES audit_run (run_id) ON DELETE RESTRICT,
            input_id text NOT NULL
                CONSTRAINT ck_decision_memory_probe_input_id CHECK (char_length(input_id) BETWEEN 1 AND 128),
            text_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_probe_text_sha256 CHECK (text_sha256 ~ '{_SHA256}'),
            view_kind text NOT NULL DEFAULT 'finding_v1'
                CONSTRAINT ck_decision_memory_probe_view_kind CHECK (view_kind IN ({_VIEW_KINDS})),
            embedding_profile text NOT NULL
                CONSTRAINT ck_decision_memory_probe_profile CHECK (embedding_profile ~ '{_PROFILE}'),
            input_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_probe_input_sha256 CHECK (input_sha256 ~ '{_SHA256}'),
            state text NOT NULL DEFAULT 'pending'
                CONSTRAINT ck_decision_memory_probe_state CHECK (state IN ({_PROBE_STATES})),
            attempts smallint NOT NULL DEFAULT 0
                CONSTRAINT ck_decision_memory_probe_attempts CHECK (attempts BETWEEN 0 AND 5),
            poison_reason text NULL
                CONSTRAINT ck_decision_memory_probe_poison_reason CHECK (poison_reason IS NULL OR poison_reason ~ '{_CODE}'),
            model_revision text NULL
                CONSTRAINT ck_decision_memory_probe_model_revision
                    CHECK (model_revision IS NULL OR model_revision ~ '^[0-9a-f]{{40}}$'),
            embedding_sha256 text NULL
                CONSTRAINT ck_decision_memory_probe_embedding_sha256
                    CHECK (embedding_sha256 IS NULL OR embedding_sha256 ~ '{_SHA256}'),
            embedding vector(1024) NULL,
            finding_observation_id text NULL
                CONSTRAINT ck_decision_memory_probe_finding_observation_id_format
                    CHECK (finding_observation_id IS NULL OR finding_observation_id ~ '^fobs_{ULID}$'),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            state_changed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_decision_memory_probe PRIMARY KEY (run_id, input_id, text_sha256),
            CONSTRAINT ck_decision_memory_probe_poison_pair CHECK ((state = 'poisoned') = (poison_reason IS NOT NULL)),
            CONSTRAINT ck_decision_memory_probe_vector_pair CHECK ((state = 'done') = (embedding IS NOT NULL)),
            CONSTRAINT ck_decision_memory_probe_vector_whole
                CHECK ((embedding IS NULL) = (embedding_sha256 IS NULL) AND (embedding IS NULL) = (model_revision IS NULL)),
            CONSTRAINT ck_decision_memory_probe_unit_norm CHECK (embedding IS NULL OR {_UNIT_NORM})
        )
    """)
    op.execute(
        "CREATE INDEX ix_decision_memory_probe_pending ON decision_memory_probe (created_at, run_id) WHERE state = 'pending'"
    )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_probe_frozen_guard BEFORE UPDATE ON decision_memory_probe "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'run_id', 'input_id', 'text_sha256', 'view_kind', 'embedding_profile', 'input_sha256', 'created_at')"
    )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_probe_write_once BEFORE UPDATE ON decision_memory_probe "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns('finding_observation_id')"
    )

    op.execute(f"""
        CREATE TABLE decision_memory_precedent_run (
            {_id("run_id", "run", "decision_memory_precedent_run")} PRIMARY KEY
                CONSTRAINT fk_decision_memory_precedent_run_run REFERENCES audit_run (run_id) ON DELETE RESTRICT,
            revision integer NOT NULL DEFAULT 1
                CONSTRAINT ck_decision_memory_precedent_run_revision CHECK (revision >= 1),
            state text NOT NULL DEFAULT 'pending'
                CONSTRAINT ck_decision_memory_precedent_run_state CHECK (state IN ({_PASS_STATES})),
            failure_code text NULL
                CONSTRAINT ck_decision_memory_precedent_run_failure_code
                    CHECK (failure_code IS NULL OR failure_code ~ '{_CODE}'),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            state_changed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_decision_memory_precedent_run_failure_pair CHECK ((state = 'failed') = (failure_code IS NOT NULL))
        )
    """)
    op.execute(
        "CREATE INDEX ix_decision_memory_precedent_run_open ON decision_memory_precedent_run (state_changed_at, run_id) "
        "WHERE state IN ('pending', 'running')"
    )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_precedent_run_frozen_guard BEFORE UPDATE ON decision_memory_precedent_run "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('run_id', 'created_at')"
    )

    op.execute(f"""
        CREATE TABLE decision_memory_precedent_advice (
            {_id("run_id", "run", "decision_memory_precedent_advice")}
                CONSTRAINT fk_decision_memory_precedent_advice_run REFERENCES audit_run (run_id) ON DELETE RESTRICT,
            {_id("finding_uid", "fnd", "decision_memory_precedent_advice")}
                CONSTRAINT fk_decision_memory_precedent_advice_finding REFERENCES finding (finding_uid) ON DELETE RESTRICT,
            revision integer NOT NULL
                CONSTRAINT ck_decision_memory_precedent_advice_revision CHECK (revision >= 1),
            label text NOT NULL
                CONSTRAINT ck_decision_memory_precedent_advice_label CHECK (label IN ({_LABELS})),
            critic_reviewed boolean NOT NULL,
            votes jsonb NOT NULL
                CONSTRAINT ck_decision_memory_precedent_advice_votes
                    CHECK (jsonb_typeof(votes) = 'object' AND octet_length(votes::text) <= 2048),
            hint_codes text[] NOT NULL DEFAULT '{{}}'
                CONSTRAINT ck_decision_memory_precedent_advice_hint_codes
                    CHECK (cardinality(hint_codes) <= 2 AND hint_codes <@ ARRAY[{_HINT_CODES}]::text[]),
            computed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_decision_memory_precedent_advice PRIMARY KEY (run_id, finding_uid, revision),
            CONSTRAINT ck_decision_memory_precedent_advice_cancel_needs_critic
                CHECK (label <> 'cancel_suggested' OR critic_reviewed)
        )
    """)
    op.execute(
        "CREATE INDEX ix_decision_memory_precedent_advice_finding ON decision_memory_precedent_advice (finding_uid, run_id, revision DESC)"
    )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_precedent_advice_immutable BEFORE UPDATE OR DELETE ON decision_memory_precedent_advice "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    # --- the product side: block evidence of a finding ----------------------------------------------
    op.execute(f"""
        CREATE TABLE finding_block_evidence (
            {_id("finding_observation_id", "fobs", "finding_block_evidence")}
                CONSTRAINT fk_finding_block_evidence_observation
                    REFERENCES finding_observation (finding_observation_id) ON DELETE RESTRICT,
            ordinal integer NOT NULL
                CONSTRAINT ck_finding_block_evidence_ordinal CHECK (ordinal >= 0),
            page_number integer NOT NULL
                CONSTRAINT ck_finding_block_evidence_page_number CHECK (page_number >= 1),
            portal_block_id text NOT NULL
                CONSTRAINT ck_finding_block_evidence_portal_block_id CHECK (portal_block_id ~ '^blk_[0-9a-f]{{32}}$'),
            bbox_x0 double precision NOT NULL,
            bbox_y0 double precision NOT NULL,
            bbox_x1 double precision NOT NULL,
            bbox_y1 double precision NOT NULL,
            crop_sha256 text NOT NULL
                CONSTRAINT ck_finding_block_evidence_crop_sha256 CHECK (crop_sha256 ~ '{_SHA256}'),
            recognised_quote text NULL
                CONSTRAINT ck_finding_block_evidence_recognised_quote
                    CHECK (recognised_quote IS NULL OR char_length(recognised_quote) BETWEEN 1 AND 2000),
            CONSTRAINT pk_finding_block_evidence PRIMARY KEY (finding_observation_id, ordinal),
            CONSTRAINT ck_finding_block_evidence_bbox
                CHECK (bbox_x0 >= 0 AND bbox_y0 >= 0 AND bbox_x1 <= 1 AND bbox_y1 <= 1
                       AND bbox_x1 > bbox_x0 AND bbox_y1 > bbox_y0)
        )
    """)
    op.execute(
        "CREATE TRIGGER trg_finding_block_evidence_immutable BEFORE UPDATE OR DELETE ON finding_block_evidence "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    # --- the observation: how it is grounded, where it came from, what it relates to ----------------
    op.execute("""
        ALTER TABLE finding_observation
            ADD COLUMN grounding_kind text NOT NULL DEFAULT 'text_span',
            ADD COLUMN extended_observation_ref text NULL,
            ADD COLUMN related_finding_uid text NULL
    """)
    op.execute(f"""
        ALTER TABLE finding_observation
            ADD CONSTRAINT ck_finding_observation_grounding_kind CHECK (grounding_kind IN ('text_span', 'portal_block')),
            ADD CONSTRAINT ck_finding_observation_extended_observation_ref
                CHECK (extended_observation_ref IS NULL OR char_length(extended_observation_ref) BETWEEN 1 AND 128),
            ADD CONSTRAINT ck_finding_observation_related_finding_uid_format
                CHECK (related_finding_uid IS NULL OR related_finding_uid ~ '^fnd_{ULID}$')
    """)
    op.execute("COMMENT ON COLUMN finding_observation.related_finding_uid IS "
               "'A bare identity, not a foreign key: the finding the observation is related to (a group of candidates that holds "
               "a primary text source is published as a finding of its own and names the text finding).';")

    # --- the vocabularies ---------------------------------------------------------------------------
    categories = _literals((*_CATEGORIES_0023, *_NEW_CATEGORIES))
    for table in ("finding", "finding_observation"):
        _replace_check(table, f"ck_{table}_category", f"category IN ({categories})")
    _replace_check(
        "finding_observation", "ck_finding_observation_ungrounded_reason",
        f"ungrounded_reason IS NULL OR ungrounded_reason IN ({_literals((*_REASONS_0023, *_NEW_REASONS))})",
    )

    # --- the run: the publication mode, frozen at the start -----------------------------------------
    op.execute("ALTER TABLE audit_run ADD COLUMN publication_mode text NOT NULL DEFAULT 'text_only'")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_publication_mode "
        "CHECK (publication_mode IN ('text_only', 'one_list'))"
    )
    # The marker is set only for a run that has a stage plan (plan section 3.6).
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_publication_mode_stage_plan "
        "CHECK (publication_mode = 'text_only' OR stage_plan IS NOT NULL)"
    )
    _guard("audit_run", "trg_audit_run_frozen_guard", "am_guard_audit_run_frozen", _FROZEN_RUN_0064)

    # --- the settings and the switches --------------------------------------------------------------
    op.execute(f"""
        CREATE TABLE precedent_setting_event (
            setting_name text NOT NULL
                CONSTRAINT ck_precedent_setting_event_setting_name CHECK (setting_name IN ({_SETTING_NAMES})),
            revision integer NOT NULL
                CONSTRAINT ck_precedent_setting_event_revision CHECK (revision >= 1),
            value jsonb NOT NULL
                CONSTRAINT ck_precedent_setting_event_value
                    CHECK (jsonb_typeof(value) = 'object' AND octet_length(value::text) <= 16384),
            actor_user_uid text NOT NULL
                CONSTRAINT ck_precedent_setting_event_actor_user_uid_format CHECK (actor_user_uid ~ '^usr_{ULID}$')
                CONSTRAINT fk_precedent_setting_event_actor REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_precedent_setting_event PRIMARY KEY (setting_name, revision),
            CONSTRAINT ck_precedent_setting_event_switch
                CHECK (setting_name NOT IN ('one_list', 'critic_context') OR jsonb_typeof(value -> 'enabled') = 'boolean'),
            CONSTRAINT ck_precedent_setting_event_window
                CHECK (setting_name <> 'vector_window'
                       OR (jsonb_typeof(value -> 'start') = 'string' AND jsonb_typeof(value -> 'end') = 'string'
                           AND jsonb_typeof(value -> 'tz') = 'string'))
        )
    """)
    op.execute(
        "CREATE TRIGGER trg_precedent_setting_event_immutable BEFORE UPDATE OR DELETE ON precedent_setting_event "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_precedent_setting_event_number BEFORE INSERT ON precedent_setting_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('setting_name', 'revision')"
    )

    # --- the vectors' pause and the night window ----------------------------------------------------
    op.execute(f"""
        CREATE TABLE vector_control (
            control_key text PRIMARY KEY
                CONSTRAINT ck_vector_control_key CHECK (control_key = 'default'),
            paused boolean NOT NULL DEFAULT false,
            paused_since timestamptz NULL,
            window_state text NOT NULL DEFAULT 'closed'
                CONSTRAINT ck_vector_control_window_state CHECK (window_state IN ({_WINDOW_STATES})),
            window_reason text NULL
                CONSTRAINT ck_vector_control_window_reason CHECK (window_reason IS NULL OR window_reason ~ '{_CODE}'),
            window_changed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_vector_control_paused_pair CHECK (paused = (paused_since IS NOT NULL)),
            CONSTRAINT ck_vector_control_skipped_reason CHECK ((window_state = 'skipped') = (window_reason IS NOT NULL))
        )
    """)
    op.execute("INSERT INTO vector_control (control_key) VALUES ('default')")
    op.execute(
        "CREATE TRIGGER trg_vector_control_frozen_guard BEFORE UPDATE ON vector_control "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('control_key')"
    )
    op.execute(
        "CREATE TRIGGER trg_vector_control_no_delete BEFORE DELETE ON vector_control "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(f"""
        CREATE TABLE vector_control_event (
            {_id("control_event_id", "vce", "vector_control_event")} PRIMARY KEY,
            control_key text NOT NULL REFERENCES vector_control (control_key),
            event_no integer NOT NULL
                CONSTRAINT ck_vector_control_event_number CHECK (event_no >= 1),
            kind text NOT NULL
                CONSTRAINT ck_vector_control_event_kind CHECK (kind IN ({_CONTROL_EVENT_KINDS})),
            reason text NULL
                CONSTRAINT ck_vector_control_event_reason CHECK (reason IS NULL OR reason ~ '{_CODE}'),
            actor_user_uid text NULL
                CONSTRAINT ck_vector_control_event_actor_user_uid_format
                    CHECK (actor_user_uid IS NULL OR actor_user_uid ~ '^usr_{ULID}$')
                CONSTRAINT fk_vector_control_event_actor REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT uq_vector_control_event_number UNIQUE (control_key, event_no),
            CONSTRAINT ck_vector_control_event_actor_for_kind
                CHECK ((kind IN ('paused', 'resumed')) = (actor_user_uid IS NOT NULL)),
            CONSTRAINT ck_vector_control_event_skipped_reason CHECK ((kind = 'window_skipped') = (reason IS NOT NULL))
        )
    """)
    op.execute(
        "CREATE TRIGGER trg_vector_control_event_append_only BEFORE UPDATE OR DELETE ON vector_control_event "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_vector_control_event_number BEFORE INSERT ON vector_control_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('control_key', 'event_no')"
    )

    # --- what the stand handed to an agent as reference data (KEEP, no foreign key, no text) ---------
    op.execute(f"""
        CREATE TABLE executor_task_context_delivery (
            {_id("delivery_id", "etd", "executor_task_context_delivery")} PRIMARY KEY,
            {_id("task_id", "ext", "executor_task_context_delivery")},
            {_id("run_id", "run", "executor_task_context_delivery")},
            {_id("model_call_id", "mc", "executor_task_context_delivery", nullable=True)},
            kind text NOT NULL
                CONSTRAINT ck_executor_task_context_delivery_kind CHECK (kind IN ({_DELIVERY_KINDS})),
            status text NOT NULL
                CONSTRAINT ck_executor_task_context_delivery_status CHECK (status IN ({_DELIVERY_STATUSES})),
            reason text NULL
                CONSTRAINT ck_executor_task_context_delivery_reason CHECK (reason IS NULL OR reason ~ '{_CODE}'),
            case_ids text[] NOT NULL DEFAULT '{{}}'
                CONSTRAINT ck_executor_task_context_delivery_case_ids
                    CHECK (cardinality(case_ids) <= 64
                           AND array_to_string(case_ids, ',') ~ '^(dmc_{ULID}(,dmc_{ULID})*)?$'),
            characters integer NOT NULL DEFAULT 0
                CONSTRAINT ck_executor_task_context_delivery_characters CHECK (characters BETWEEN 0 AND 1000000),
            block_sha256 text NULL
                CONSTRAINT ck_executor_task_context_delivery_block_sha256
                    CHECK (block_sha256 IS NULL OR block_sha256 ~ '{_SHA256}'),
            delivered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT uq_executor_task_context_delivery_task_kind UNIQUE (task_id, kind),
            CONSTRAINT ck_executor_task_context_delivery_reason_pair CHECK ((status = 'unavailable') = (reason IS NOT NULL)),
            CONSTRAINT ck_executor_task_context_delivery_block_pair CHECK ((status = 'delivered') = (block_sha256 IS NOT NULL))
        )
    """)
    op.execute("CREATE INDEX ix_executor_task_context_delivery_run ON executor_task_context_delivery (run_id, delivered_at)")
    op.execute(
        "CREATE TRIGGER trg_executor_task_context_delivery_immutable BEFORE UPDATE OR DELETE ON executor_task_context_delivery "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    comments = {
        "decision_memory_comment": (
            "CRIT-SEAL-50 (plan-v5 section 3.1, R5): an expert's comment on a memory case, a table of its own beside the decision. "
            "KEEP, content side: DELETE only beside a forget of the case, INSERT refused into a forgotten case."
        ),
        "decision_memory_block_evidence": (
            "CRIT-SEAL-50: the memory's copy of a block-grounded evidence item (finding_block_evidence): the portal block, its "
            "normalised box, the digest of its crop and an optional recognised quote. KEEP, content side."
        ),
        "decision_memory_embedding_intent": (
            "CRIT-SEAL-50: the encoder's queue, one row per (case, revision, view, profile): pending, done or poisoned. The "
            "input digest is indexed, not unique: the encoder deduplicates a batch by it. KEEP, content side."
        ),
        "decision_memory_embedding": (
            "CRIT-SEAL-50: the vector of a case view (bge-m3-dense-v1, 1024 dimensions, unit norm). No HNSW index: the search is an "
            "exact scan of one section. KEEP, content side: deleted by a forget of the case."
        ),
        "decision_memory_probe": (
            "CRIT-SEAL-50: the query vector of a candidate text of a run; a foreign key to audit_run only, the observation is a bare "
            "identity written after publication. PRODUCT."
        ),
        "decision_memory_precedent_run": (
            "CRIT-SEAL-50: the state of the Precedents pass of a run (pending, running, done, failed) and its current revision. PRODUCT."
        ),
        "decision_memory_precedent_advice": (
            "CRIT-SEAL-50: what the Precedents pass gave a finding of a run at a revision: the label, the vote counts, at most two "
            "hint codes. No text. PRODUCT, append-only."
        ),
        "finding_block_evidence": (
            "CRIT-SEAL-50: a block-grounded evidence item of a finding observation. finding_evidence and its CHECK are untouched. PRODUCT."
        ),
        "precedent_setting_event": (
            "CRIT-SEAL-50: the switches and settings of the Precedents programme as an append-only journal the application writes "
            "(one_list, critic_context, section_labels, stop_words, vector_window, thresholds); numbered without a gap per name."
        ),
        "vector_control": "CRIT-SEAL-50: one row, key default: the vectors' pause and the state of the night window.",
        "vector_control_event": (
            "CRIT-SEAL-50: the journal of the vectors' pause (with the administrator) and of the states of the night window."
        ),
        "executor_task_context_delivery": (
            "CRIT-SEAL-50: what the stand handed to an agent as reference data, by opaque task, run and model call identity, the cases "
            "by identity, the character count and the block digest. No foreign key, no text; KEEP, it outlives the erase of the project."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}';")
    op.execute(
        "COMMENT ON COLUMN decision_memory_decision.precedent_label_at_decision IS "
        "'The Precedents label in force for the finding when the expert decided (none, few, often_rejected, cancel_suggested, "
        "likely_accepted, mixed); NULL when none was known. With precedent_revision: both or neither.';"
    )
    op.execute(
        "COMMENT ON COLUMN decision_memory_decision.precedent_history_verdict_shown IS "
        "'The verdict of the history fact (hint p5: the earlier decision on the same document) shown when the expert decided "
        "(accepted or rejected); NULL when no such fact was shown.';"
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.publication_mode IS "
        "'CRIT-SEAL-50: text_only (the old publication) or one_list (candidates of the extended review become findings); frozen at the "
        "start of the run; one_list needs a stage plan.';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in (
        "decision_memory_comment", "decision_memory_block_evidence", "decision_memory_embedding_intent", "decision_memory_embedding",
        "decision_memory_probe", "decision_memory_precedent_run", "decision_memory_precedent_advice", "finding_block_evidence",
        "precedent_setting_event", "vector_control_event", "executor_task_context_delivery",
    ):
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            retained.append(table)
    new_categories = _literals(_NEW_CATEGORIES)
    new_reasons = _literals(_NEW_REASONS)
    for label, query in (
        ("vector_control state",
         "SELECT EXISTS (SELECT 1 FROM vector_control WHERE paused OR window_state <> 'closed' OR window_reason IS NOT NULL)"),
        ("decision_memory_decision.precedent_label_at_decision or precedent_history_verdict_shown",
         "SELECT EXISTS (SELECT 1 FROM decision_memory_decision "
         "WHERE precedent_label_at_decision IS NOT NULL OR precedent_history_verdict_shown IS NOT NULL)"),
        ("audit_run.publication_mode", "SELECT EXISTS (SELECT 1 FROM audit_run WHERE publication_mode <> 'text_only')"),
        ("finding_observation grounding_kind, extended_observation_ref or related_finding_uid",
         "SELECT EXISTS (SELECT 1 FROM finding_observation WHERE grounding_kind <> 'text_span' "
         "OR extended_observation_ref IS NOT NULL OR related_finding_uid IS NOT NULL)"),
        ("a finding or an observation of a new category",
         f"SELECT EXISTS (SELECT 1 FROM finding WHERE category IN ({new_categories})) "
         f"OR EXISTS (SELECT 1 FROM finding_observation WHERE category IN ({new_categories}))"),
        ("an observation diagnosed with a new reason",
         f"SELECT EXISTS (SELECT 1 FROM finding_observation WHERE ungrounded_reason IN ({new_reasons}))"),
    ):
        if bind.execute(text(query)).scalar_one():
            retained.append(label)
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0064_precedents_seal with retained precedent, vector or block-evidence data "
            f"({', '.join(retained)}); restore a database backup instead"
        )

    _guard("audit_run", "trg_audit_run_frozen_guard", "am_guard_audit_run_frozen", _FROZEN_RUN_0062)
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_publication_mode_stage_plan")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_publication_mode")
    op.execute("ALTER TABLE audit_run DROP COLUMN publication_mode")

    _replace_check(
        "finding_observation", "ck_finding_observation_ungrounded_reason",
        f"ungrounded_reason IS NULL OR ungrounded_reason IN ({_literals(_REASONS_0023)})",
    )
    categories = _literals(_CATEGORIES_0023)
    for table in ("finding_observation", "finding"):
        _replace_check(table, f"ck_{table}_category", f"category IN ({categories})")

    op.execute("""
        ALTER TABLE finding_observation
            DROP CONSTRAINT ck_finding_observation_related_finding_uid_format,
            DROP CONSTRAINT ck_finding_observation_extended_observation_ref,
            DROP CONSTRAINT ck_finding_observation_grounding_kind
    """)
    op.execute("""
        ALTER TABLE finding_observation
            DROP COLUMN related_finding_uid,
            DROP COLUMN extended_observation_ref,
            DROP COLUMN grounding_kind
    """)

    for table in (
        "executor_task_context_delivery", "vector_control_event", "vector_control", "precedent_setting_event", "finding_block_evidence",
        "decision_memory_precedent_advice", "decision_memory_precedent_run", "decision_memory_probe",
        "decision_memory_embedding", "decision_memory_embedding_intent", "decision_memory_block_evidence", "decision_memory_comment",
    ):
        op.execute(f"DROP TABLE {table}")

    op.execute("""
        ALTER TABLE decision_memory_decision
            DROP CONSTRAINT ck_decision_memory_decision_precedent_history_verdict_shown,
            DROP CONSTRAINT ck_decision_memory_decision_precedent_pair,
            DROP CONSTRAINT ck_decision_memory_decision_precedent_revision,
            DROP CONSTRAINT ck_decision_memory_decision_precedent_label
    """)
    op.execute("""
        ALTER TABLE decision_memory_decision
            DROP COLUMN precedent_history_verdict_shown,
            DROP COLUMN precedent_revision,
            DROP COLUMN precedent_label_at_decision
    """)
    op.execute("DROP FUNCTION am_guard_decision_memory_forgotten_insert()")
