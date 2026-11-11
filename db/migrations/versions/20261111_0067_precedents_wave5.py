"""0067 -- the storage of wave 5 of the «Прецеденты» programme (`CRIT-SEAL-53`, plan-v5 section 3.7; contract 1.54.0).

Planned as 0066 / 1.53.0; resealed to 0067 / 1.54.0 when `RUN-DELETE-01` (`0066_run_deletion`, contract 1.53.0) reached `main` first.

Revision ID: 0067_precedents_wave5
Revises: 0066_run_deletion

The wave-5 seal (called ``CRIT-SEAL-51`` in the task files; the numbers moved under `R-154h` and the debt seal 1.52.0). Storage and surface only: no
statement writes any of it until ``PAT-01``, ``XDOC-01`` and ``QUAL-01`` do. Every addition to an existing table is a vocabulary; a database at
``0066`` upgrades with no row touched.

What this revision adds
-----------------------
The decision memory (KEEP, content side: deletable only by a forget of the case) -- failure patterns, owner ruling Н4 (the algorithm proposes, an
expert approves)
    ``decision_memory_pattern`` -- one pattern: the representative case of a group of refusals in one section (``case_id``, the case whose refusing
    comment is the text), the text itself (a refusing comment, verbatim, never written by a model: hint P1 reads it once the pattern is approved),
    the counts the group had when it was proposed and the version of the proposing rule. Immutable; one pattern per representative case. The text is
    a copy of memory content, so the table takes the forget guard of ``0061`` (``DELETE`` only beside a ``forget`` event of ``case_id``) and the
    guard on ``INSERT`` of ``0064``: forgetting the representative case removes the pattern and its journal.
    ``decision_memory_pattern_status_event`` (``dps``) -- its status journal: ``proposed`` (the algorithm), then ``approved`` / ``rejected`` /
    ``suspended`` by an expert, or ``suspended`` by the algorithm when the group dissolves (``cause`` says which). Numbered per pattern without a
    gap; the database's own transition rule (``am_guard_decision_memory_pattern_status``): ``proposed`` first and only first, ``approved`` from
    ``proposed`` or ``suspended``, ``rejected`` from ``proposed``, ``suspended`` from ``approved``. A review by an expert names the account and the
    command that carried it. The journal carries ``case_id`` too, so the same forget guard reaches it.
    ``decision_memory_pattern_current`` (a view) -- a pattern with the status of its latest event, the read model hint P1 and the screen read. A
    pattern with no event has no status (NULL) and is never read as approved.
The product side (PRODUCT: leaves with the project) -- owner ruling Н6, a discrepancy of a parameter between two documents is a finding of the
newer document's run
    ``project_parameter_fact`` -- one parameter the extraction of a run found, in the queryable form the comparison reads: the type, the name, the
    value as the document states it (and its number when it is one), the unit (NULL when the text gives none: a parameter without a unit is never
    compared), the subject, and the first evidence (page, quote, span). The key is the run and the extractor's own fact reference (``ppf_`` and 32
    hexadecimal digits); the project and the version are the run's. Immutable.
    ``finding_cross_evidence`` -- the evidence of a finding that stands in **another** document: the finding's observation, the ordinal, the other
    version (``version_uid``), the page, the quote and its span in that version's text layer. As ``finding_evidence``, immutable, and no identity of
    its own. A trigger holds the other version to the same project as the finding and to a different version.
The vocabulary
    The ``FindingCategory`` checks of ``finding`` and ``finding_observation`` gain ``parameter_mismatch``.

Downgrade
---------
Refused while any row of the four tables, or any finding or observation of the new category, exists: dropping them would turn a fact into silence
(AGENTS section 4, no silent fallback). Otherwise it restores ``0066``'s checks (the same as ``0065``'s).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0067_precedents_wave5"
down_revision: str | None = "0066_run_deletion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_CODE = "^[a-z][a-z0-9_]{0,63}$"
_VERSION_TAG = "^[a-z0-9][a-z0-9._-]{0,63}$"
_PATTERN_STATUSES = "'proposed', 'approved', 'rejected', 'suspended'"
_PATTERN_CAUSES = "'proposed', 'expert_review', 'group_dissolved'"
_PARAMETER_TYPES = (
    "object_type", "storeys", "area", "level", "dimensions", "loads", "flows", "temperature", "pressure", "equipment", "materials", "system", "other",
)

#: ``FindingCategory`` as ``0064`` left it, and the category of a discrepancy of a parameter between two documents.
_CATEGORIES_0064 = (
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout", "facade", "roof", "documentation",
    "evacuation", "fire_safety", "accessibility", "insulation", "sound", "drawing_discrepancy", "cross_source",
)
_NEW_CATEGORIES = ("parameter_mismatch",)

_PATTERN_STATUS_FUNCTION = """
        CREATE FUNCTION am_guard_decision_memory_pattern_status() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            latest text;
        BEGIN
            -- ``am_check_gapless_number`` (which fires first) holds the advisory lock of this pattern, so the latest event below is stable.
            SELECT e.status INTO latest
              FROM decision_memory_pattern_status_event e
             WHERE e.pattern_id = NEW.pattern_id
             ORDER BY e.event_no DESC
             LIMIT 1;
            IF latest IS NULL AND NEW.status <> 'proposed' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory pattern % has no proposal, so a % event is refused', NEW.pattern_id, NEW.status
                    USING ERRCODE = 'AM003';
            ELSIF latest IS NOT NULL AND NEW.status = 'proposed' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory pattern % is already proposed', NEW.pattern_id
                    USING ERRCODE = 'AM003';
            ELSIF NEW.status = 'approved' AND latest NOT IN ('proposed', 'suspended') THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory pattern % is % and cannot be approved', NEW.pattern_id, latest
                    USING ERRCODE = 'AM003';
            ELSIF NEW.status = 'rejected' AND latest <> 'proposed' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory pattern % is % and cannot be rejected', NEW.pattern_id, latest
                    USING ERRCODE = 'AM003';
            ELSIF NEW.status = 'suspended' AND latest <> 'approved' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory pattern % is % and cannot be suspended', NEW.pattern_id, latest
                    USING ERRCODE = 'AM003';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_CROSS_EVIDENCE_FUNCTION = """
        CREATE FUNCTION am_check_finding_cross_evidence() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            own_version text;
            own_project text;
            other_project text;
        BEGIN
            SELECT r.version_uid, r.project_uid INTO own_version, own_project
              FROM finding_observation o JOIN audit_run r ON r.run_id = o.run_id
             WHERE o.finding_observation_id = NEW.finding_observation_id;
            SELECT d.project_uid INTO other_project
              FROM document_version v JOIN document d ON d.document_uid = v.document_uid WHERE v.version_uid = NEW.version_uid;
            IF other_project IS DISTINCT FROM own_project THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the cross evidence of observation % names version %, which is not in the observation''s project',
                    NEW.finding_observation_id, NEW.version_uid
                    USING ERRCODE = 'AM003',
                          HINT = 'A finding is a finding of one project; its other document is a version of the same project.';
            END IF;
            IF NEW.version_uid = own_version THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the cross evidence of observation % names the observation''s own version %',
                    NEW.finding_observation_id, NEW.version_uid
                    USING ERRCODE = 'AM003',
                          HINT = 'Cross evidence stands in the other document; evidence in the finding''s own version is finding_evidence.';
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


def _replace_check(table: str, name: str, expression: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})")


def _quoted(comment: str) -> str:
    return comment.replace("'", "''")


def _literals(values: Sequence[str]) -> str:
    return ", ".join("'" + value + "'" for value in values)


def upgrade() -> None:
    op.execute(_PATTERN_STATUS_FUNCTION)
    op.execute(_CROSS_EVIDENCE_FUNCTION)

    # --- the decision memory: failure patterns ------------------------------------------------------
    op.execute(f"""
        CREATE TABLE decision_memory_pattern (
            {_id("pattern_id", "dmp", "decision_memory_pattern")} PRIMARY KEY,
            {_id("case_id", "dmc", "decision_memory_pattern")}
                CONSTRAINT fk_decision_memory_pattern_case
                    REFERENCES decision_memory_case (case_id) ON DELETE RESTRICT
                CONSTRAINT uq_decision_memory_pattern_case UNIQUE,
            section_code text NOT NULL
                CONSTRAINT ck_decision_memory_pattern_section_code CHECK (char_length(section_code) BETWEEN 1 AND 64),
            data_class text NOT NULL
                CONSTRAINT ck_decision_memory_pattern_data_class CHECK (data_class IN ('test', 'real')),
            pattern_text text NOT NULL
                CONSTRAINT ck_decision_memory_pattern_pattern_text CHECK (char_length(pattern_text) BETWEEN 1 AND 2000),
            member_count integer NOT NULL
                CONSTRAINT ck_decision_memory_pattern_member_count CHECK (member_count >= 1),
            refusal_count integer NOT NULL
                CONSTRAINT ck_decision_memory_pattern_refusal_count CHECK (refusal_count >= 1),
            algorithm_version text NOT NULL
                CONSTRAINT ck_decision_memory_pattern_algorithm_version CHECK (algorithm_version ~ '{_VERSION_TAG}'),
            proposed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT uq_decision_memory_pattern_id_case UNIQUE (pattern_id, case_id),
            CONSTRAINT ck_decision_memory_pattern_refusals_within_members CHECK (refusal_count <= member_count)
        )
    """)
    op.execute("CREATE INDEX ix_decision_memory_pattern_section ON decision_memory_pattern (section_code, data_class)")
    op.execute(f"""
        CREATE TABLE decision_memory_pattern_status_event (
            {_id("pattern_event_id", "dps", "decision_memory_pattern_status_event")} PRIMARY KEY,
            {_id("pattern_id", "dmp", "decision_memory_pattern_status_event")},
            {_id("case_id", "dmc", "decision_memory_pattern_status_event")},
            event_no integer NOT NULL
                CONSTRAINT ck_decision_memory_pattern_status_event_event_no CHECK (event_no >= 1),
            status text NOT NULL
                CONSTRAINT ck_decision_memory_pattern_status_event_status CHECK (status IN ({_PATTERN_STATUSES})),
            cause text NOT NULL
                CONSTRAINT ck_decision_memory_pattern_status_event_cause CHECK (cause IN ({_PATTERN_CAUSES})),
            {_id("actor_user_uid", "usr", "decision_memory_pattern_status_event", nullable=True)}
                CONSTRAINT fk_decision_memory_pattern_status_event_actor REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            {_id("command_id", "cmd", "decision_memory_pattern_status_event", nullable=True)}
                CONSTRAINT fk_decision_memory_pattern_status_event_command REFERENCES command_record (command_id) ON DELETE RESTRICT,
            member_count integer NULL
                CONSTRAINT ck_decision_memory_pattern_status_event_member_count CHECK (member_count IS NULL OR member_count >= 0),
            refusal_count integer NULL
                CONSTRAINT ck_decision_memory_pattern_status_event_refusal_count CHECK (refusal_count IS NULL OR refusal_count >= 0),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_decision_memory_pattern_status_event_pattern FOREIGN KEY (pattern_id, case_id)
                REFERENCES decision_memory_pattern (pattern_id, case_id) ON DELETE RESTRICT,
            CONSTRAINT uq_decision_memory_pattern_status_event_number UNIQUE (pattern_id, event_no),
            CONSTRAINT ck_decision_memory_pattern_status_event_counts_pair CHECK ((member_count IS NULL) = (refusal_count IS NULL)),
            CONSTRAINT ck_decision_memory_pattern_status_event_counts_within
                CHECK (member_count IS NULL OR refusal_count <= member_count),
            CONSTRAINT ck_decision_memory_pattern_status_event_cause_for_status CHECK (
                (cause = 'proposed' AND status = 'proposed' AND actor_user_uid IS NULL AND command_id IS NULL)
                OR (cause = 'expert_review' AND status IN ('approved', 'rejected', 'suspended')
                    AND actor_user_uid IS NOT NULL AND command_id IS NOT NULL)
                OR (cause = 'group_dissolved' AND status = 'suspended' AND actor_user_uid IS NULL AND command_id IS NULL
                    AND member_count IS NOT NULL)
            ),
            CONSTRAINT ck_decision_memory_pattern_status_event_first_is_proposed CHECK ((event_no = 1) = (status = 'proposed'))
        )
    """)
    op.execute(
        "CREATE INDEX ix_decision_memory_pattern_status_event_pattern ON decision_memory_pattern_status_event (pattern_id, event_no DESC)"
    )
    for table in ("decision_memory_pattern", "decision_memory_pattern_status_event"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_forget_guard BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_forget()"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_forgotten_insert BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_forgotten_insert()"
        )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_pattern_status_event_number BEFORE INSERT ON decision_memory_pattern_status_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('pattern_id', 'event_no')"
    )
    op.execute(
        "CREATE TRIGGER trg_decision_memory_pattern_status_event_transition BEFORE INSERT ON decision_memory_pattern_status_event "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_pattern_status()"
    )
    op.execute("""
        CREATE VIEW decision_memory_pattern_current AS
        SELECT p.pattern_id,
               p.case_id,
               p.section_code,
               p.data_class,
               p.pattern_text,
               p.member_count,
               p.refusal_count,
               p.algorithm_version,
               p.proposed_at,
               s.status AS status,
               s.cause AS status_cause,
               s.event_no AS status_event_no,
               s.actor_user_uid AS status_actor_user_uid,
               s.created_at AS status_changed_at
          FROM decision_memory_pattern p
          LEFT JOIN (
                SELECT DISTINCT ON (e.pattern_id) e.pattern_id, e.status, e.cause, e.event_no, e.actor_user_uid, e.created_at
                  FROM decision_memory_pattern_status_event e
                 ORDER BY e.pattern_id, e.event_no DESC
          ) s ON s.pattern_id = p.pattern_id
    """)

    # --- the product side: the parameters a run found -----------------------------------------------
    op.execute(f"""
        CREATE TABLE project_parameter_fact (
            {_id("run_id", "run", "project_parameter_fact")}
                CONSTRAINT fk_project_parameter_fact_run REFERENCES audit_run (run_id) ON DELETE RESTRICT,
            fact_ref text NOT NULL
                CONSTRAINT ck_project_parameter_fact_fact_ref CHECK (fact_ref ~ '^ppf_[0-9a-f]{{32}}$'),
            parameter_type text NOT NULL
                CONSTRAINT ck_project_parameter_fact_parameter_type CHECK (parameter_type IN ({_literals(_PARAMETER_TYPES)})),
            name text NOT NULL
                CONSTRAINT ck_project_parameter_fact_name CHECK (char_length(name) BETWEEN 1 AND 160),
            value_text text NOT NULL
                CONSTRAINT ck_project_parameter_fact_value_text CHECK (char_length(value_text) BETWEEN 1 AND 500),
            value_number numeric NULL,
            unit text NULL
                CONSTRAINT ck_project_parameter_fact_unit CHECK (unit IS NULL OR char_length(unit) BETWEEN 1 AND 80),
            subject text NULL
                CONSTRAINT ck_project_parameter_fact_subject CHECK (subject IS NULL OR char_length(subject) BETWEEN 1 AND 300),
            page_number integer NOT NULL
                CONSTRAINT ck_project_parameter_fact_page_number CHECK (page_number >= 1),
            quote text NOT NULL
                CONSTRAINT ck_project_parameter_fact_quote CHECK (char_length(quote) BETWEEN 1 AND 2000),
            char_start integer NOT NULL,
            char_end integer NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_project_parameter_fact PRIMARY KEY (run_id, fact_ref),
            CONSTRAINT ck_project_parameter_fact_span CHECK (char_start >= 0 AND char_end > char_start),
            CONSTRAINT ck_project_parameter_fact_span_matches_quote CHECK (char_end - char_start = char_length(quote))
        )
    """)
    op.execute("CREATE INDEX ix_project_parameter_fact_type ON project_parameter_fact (parameter_type, name)")
    op.execute(
        "CREATE TRIGGER trg_project_parameter_fact_immutable BEFORE UPDATE OR DELETE ON project_parameter_fact "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    op.execute(f"""
        CREATE TABLE finding_cross_evidence (
            {_id("finding_observation_id", "fobs", "finding_cross_evidence")}
                CONSTRAINT fk_finding_cross_evidence_observation
                    REFERENCES finding_observation (finding_observation_id) ON DELETE RESTRICT,
            evidence_ordinal integer NOT NULL
                CONSTRAINT ck_finding_cross_evidence_evidence_ordinal CHECK (evidence_ordinal >= 0),
            {_id("version_uid", "ver", "finding_cross_evidence")}
                CONSTRAINT fk_finding_cross_evidence_version REFERENCES document_version (version_uid) ON DELETE RESTRICT,
            page_number integer NOT NULL
                CONSTRAINT ck_finding_cross_evidence_page_number CHECK (page_number >= 1),
            quote text NOT NULL
                CONSTRAINT ck_finding_cross_evidence_quote CHECK (char_length(quote) BETWEEN 1 AND 2000),
            char_start integer NOT NULL,
            char_end integer NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_finding_cross_evidence PRIMARY KEY (finding_observation_id, evidence_ordinal),
            CONSTRAINT ck_finding_cross_evidence_span CHECK (char_start >= 0 AND char_end > char_start),
            CONSTRAINT ck_finding_cross_evidence_span_matches_quote CHECK (char_end - char_start = char_length(quote))
        )
    """)
    op.execute("CREATE INDEX ix_finding_cross_evidence_version ON finding_cross_evidence (version_uid)")
    op.execute(
        "CREATE TRIGGER trg_finding_cross_evidence_immutable BEFORE UPDATE OR DELETE ON finding_cross_evidence "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_finding_cross_evidence_version BEFORE INSERT ON finding_cross_evidence "
        "FOR EACH ROW EXECUTE FUNCTION am_check_finding_cross_evidence()"
    )

    # --- the vocabulary -----------------------------------------------------------------------------
    categories = _literals((*_CATEGORIES_0064, *_NEW_CATEGORIES))
    for table in ("finding", "finding_observation"):
        _replace_check(table, f"ck_{table}_category", f"category IN ({categories})")

    comments = {
        "decision_memory_pattern": (
            "CRIT-SEAL-53 (plan-v5 section 3.7, owner ruling N4): a failure pattern proposed by an algorithm, approved by an expert: the "
            "representative case of a group of refusals in one section, the refusing comment as the text (verbatim, never written by a model), the "
            "counts of the group at the proposal. KEEP, content side: DELETE only beside a forget of the case, INSERT refused into a forgotten case."
        ),
        "decision_memory_pattern_status_event": (
            "CRIT-SEAL-53: the status journal of a pattern: proposed (the algorithm), approved, rejected or suspended by an expert, or suspended "
            "by the algorithm when the group dissolves; numbered per pattern without a gap; the transition rule is the database's. KEEP, content side."
        ),
        "project_parameter_fact": (
            "CRIT-SEAL-53 (plan-v5 section 3.7): one parameter the extraction of a run found, in the queryable form the cross-document comparison "
            "reads; the unit is NULL when the text gives none (such a parameter is never compared). PRODUCT, immutable."
        ),
        "finding_cross_evidence": (
            "CRIT-SEAL-53 (owner ruling N6): the evidence of a finding that stands in another version of the same project, with that "
            "version_uid, the page, the quote and its span. As finding_evidence: immutable, no identity of its own. PRODUCT."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{_quoted(comment)}';")
    op.execute(
        "COMMENT ON VIEW decision_memory_pattern_current IS "
        "'CRIT-SEAL-53: a pattern with the status of its latest journal event; NULL when it has none (never read as approved). "
        "The read model of hint P1 and of the screen of failure patterns.';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in ("decision_memory_pattern_status_event", "decision_memory_pattern", "finding_cross_evidence", "project_parameter_fact"):
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            retained.append(table)
    new_categories = _literals(_NEW_CATEGORIES)
    if bind.execute(text(
        f"SELECT EXISTS (SELECT 1 FROM finding WHERE category IN ({new_categories})) "
        f"OR EXISTS (SELECT 1 FROM finding_observation WHERE category IN ({new_categories}))"
    )).scalar_one():
        retained.append("a finding or an observation of the category parameter_mismatch")
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0067_precedents_wave5 with retained pattern, parameter or cross-evidence data "
            f"({', '.join(retained)}); restore a database backup instead"
        )

    categories = _literals(_CATEGORIES_0064)
    for table in ("finding_observation", "finding"):
        _replace_check(table, f"ck_{table}_category", f"category IN ({categories})")
    op.execute("DROP VIEW decision_memory_pattern_current")
    for table in ("finding_cross_evidence", "project_parameter_fact", "decision_memory_pattern_status_event", "decision_memory_pattern"):
        op.execute(f"DROP TABLE {table}")
    op.execute("DROP FUNCTION am_check_finding_cross_evidence()")
    op.execute("DROP FUNCTION am_guard_decision_memory_pattern_status()")
