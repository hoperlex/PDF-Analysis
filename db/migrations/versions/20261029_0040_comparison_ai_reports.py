"""The version comparison AI, specifications, reports and launch queue: AI jobs, answers, descriptions, extractions, reports and queue entries.

Revision ID: 0040_comparison_ai_reports
Revises: 0039_comparison_core

`CMP-SEAL-C2` (wave C2 of `COMPARE-MODULES-PLAN`, `ADR-0025`). It creates the tables the C2 lanes
(`CMP-VC-AIPAIR-01`, `CMP-VC-AISHEET-01`, `CMP-VC-SPEC-01`, `CMP-VC-QUEUE-01`, `CMP-VC-REPORT-01`)
implement against, and nothing that implements them: no row is written and no code reads or writes a table.
Every table is reachable from ``project`` by foreign keys, so the project erase keeps its closure
(decision 7).

Tables (twelve)
---------------
``comparison_ai_job`` (``cai_``) -- one **consented AI job** of any of the four methods (``pair_check``,
``sheet_changes``, ``spec``, ``report``; each is also an executor work kind, ``comparison_<method>``). It
holds the estimate the user consented to (``estimate``, its digest, the micro-USD figure, the ceiling, the
connection revision and the pinned model), the state and the pause reason. The estimate and the consent
columns change only together and only by one consent number (a new consent after ``overrun`` or
``route_changed``, or for a retry). The spend of a job is **not** stored here: it is the journal
(``comparison_model_call``) read through the job's work items (``comparison_work.comparison_ai_job_id``, the
same id as the ``ai_job_id`` of the item's payload that `CMP-SPEND-01` sums for the ceilings), so there is one
money truth. At most one live job per scope.

``comparison_ai_pair_answer`` (``cpa_``) -- the **content-keyed** answer of the model to one question of the
pair check: a ULID id and a unique digest that includes ``project_uid`` (decision 15), so an answered question
is never sent again within a project; the digest is never a foreign key. Immutable.
``comparison_ai_pair_question`` (``cpq_``) -- one question of a job for one matrix cell, the answers it used
and the decision made of them; the accepted ones point at the ``comparison_ai_link`` they wrote. The raw
matrix and the raw answers are never rewritten.

``comparison_ai_sheet_item`` (``csi_``) -- one sheet pair of an AI description job with its outcome, calls and
tokens. ``comparison_sheet_description`` (``csd_``) -- the **content-keyed** description of one result (or of
one single added or removed page): keyed by content, prompt version and model, with a unique digest that
includes ``project_uid``. Immutable; the earlier descriptions of a sheet are its history.

``comparison_spec_extraction`` (``cse_``) -- the content-keyed reading of the whole specification of one
version. ``comparison_spec_comparison`` (``cscp_``) -- the comparison of the specifications of one transition,
either the deterministic ``positions`` (part A) or the AI ``whole`` comparison (part B).

``comparison_report`` (``crt_``) -- one PDF report of a series: a draft carries its estimate, a started one its
job; ``comparison_report_part`` (``crpt_``) the progress of one transition of it; ``comparison_report_artifact``
(``cra_``) a stored file of it (the PDF, the exact MD, the report text), append-only. A deleted report is a
tombstone (``deleted_at``): no published blob is ever deleted.

``comparison_launch_queue`` -- one row per project (pause and failure of its queue) and
``comparison_launch_entry`` (``cle_``) -- one selected step of one document set.

Other changes
-------------
``comparison_work.comparison_ai_job_id`` (nullable, frozen once set, equal to the item's payload ``ai_job_id``)
so that a job pauses, resumes and cancels its items the way a series does. ``ck_executor_route_work_kind`` is
widened to the four ``comparison_*`` work kinds of this wave beside ``text_analysis`` (ADR-0025 decision 17);
``comparison_stage_review`` joins with `CMP-SEAL-C4`. Nothing else of ``0038`` or ``0039`` is touched.

Downgrade
---------
Refuses while any row of the twelve tables exists, while any ``comparison_work`` carries a job or any executor
route names one of the new work kinds: they exist nowhere else (the pattern of ``0035`` to ``0039``). With none
it drops this revision's own objects and restores the single work kind.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0040_comparison_ai_reports"
down_revision: str | None = "0039_comparison_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
SHA256 = "^[0-9a-f]{64}$"
MAX_LABEL_LENGTH = 128
#: ``version_reader.MAX_VERSION_PAGES`` (``0021``): pages of a published version.
MAX_PAGE_NUMBER = 500

METHODS: tuple[str, ...] = ("pair_check", "sheet_changes", "spec", "report")
JOB_STATES: tuple[str, ...] = ("queued", "running", "paused", "completed", "failed", "cancelled")
JOB_LIVE: tuple[str, ...] = ("queued", "running", "paused")
PAUSE_REASONS: tuple[str, ...] = ("user", "quota", "auth", "overrun", "route_changed", "module_off")
PROVIDER_MODES: tuple[str, ...] = ("live", "recorded")
QUESTION_KINDS: tuple[str, ...] = ("review", "medium")
ANSWER_KINDS: tuple[str, ...] = ("review", "medium", "reverse")
CONFIDENCES: tuple[str, ...] = ("high", "medium", "low")
QUESTION_STATES: tuple[str, ...] = ("queued", "answered", "failed", "cancelled")
DECISIONS: tuple[str, ...] = (
    "accepted", "hint_table", "hint_confidence", "hint_taken", "hint_shared", "hint_reverse", "none",
    "mismatch", "failed", "medium_confirm", "medium_weak", "medium_other", "medium_none",
)
ITEM_STATES: tuple[str, ...] = ("queued", "running", "done", "failed", "cancelled", "skipped")
DESCRIPTION_STATES: tuple[str, ...] = (
    "done", "needs_clarification", "partial", "no_construction_changes",
)
DESCRIPTION_SOURCES: tuple[str, ...] = ("sheet", "whole_specification")
EXTRACTION_STATES: tuple[str, ...] = ("complete", "partial")
SPEC_SOURCES: tuple[str, ...] = ("positions", "whole")
SPEC_STATES: tuple[str, ...] = ("queued", "running", "completed", "incomplete", "failed", "cancelled")
SPEC_PHASES: tuple[str, ...] = ("preparation", "comparison", "done")
REPORT_KINDS: tuple[str, ...] = ("client", "analytic")
REPORT_SOURCES: tuple[str, ...] = ("series_summary", "uploaded_md")
REPORT_STATES: tuple[str, ...] = (
    "draft", "queued", "running", "paused", "completed", "partial", "failed", "cancelled",
)
REPORT_STAGES: tuple[str, ...] = ("intake", "analysis", "verification", "composition", "writing", "pdf")
UNIT_MARKS: tuple[str, ...] = ("done", "running", "failed", "pending")
ARTIFACT_KINDS: tuple[str, ...] = ("pdf", "source_md", "report_json")
LAUNCH_STEPS: tuple[str, ...] = ("profile", "matrix", "ai_pairs", "series", "ai_changes", "report")
LAUNCH_STATES: tuple[str, ...] = (
    "waiting", "running", "needs_consent", "done", "skipped", "failed",
)
LAUNCH_LIVE: tuple[str, ...] = ("waiting", "running", "needs_consent")
WORK_KINDS_BEFORE: tuple[str, ...] = ("text_analysis",)
WORK_KINDS_AFTER: tuple[str, ...] = (
    "text_analysis", "comparison_pair_check", "comparison_sheet_changes", "comparison_spec",
    "comparison_report",
)

#: ``(table, from_state, to_state)``: the only state changes the database allows for these tables.
EDGES: tuple[tuple[str, str, str], ...] = (
    ("comparison_ai_job", "queued", "running"),
    ("comparison_ai_job", "queued", "paused"),
    ("comparison_ai_job", "queued", "failed"),
    ("comparison_ai_job", "queued", "cancelled"),
    ("comparison_ai_job", "running", "paused"),
    ("comparison_ai_job", "running", "completed"),
    ("comparison_ai_job", "running", "failed"),
    ("comparison_ai_job", "running", "cancelled"),
    ("comparison_ai_job", "paused", "queued"),
    ("comparison_ai_job", "paused", "running"),
    ("comparison_ai_job", "paused", "cancelled"),
    ("comparison_ai_job", "completed", "queued"),
    ("comparison_ai_job", "failed", "queued"),
    ("comparison_ai_job", "cancelled", "queued"),
    ("comparison_ai_pair_question", "queued", "answered"),
    ("comparison_ai_pair_question", "queued", "failed"),
    ("comparison_ai_pair_question", "queued", "cancelled"),
    ("comparison_ai_pair_question", "failed", "queued"),
    ("comparison_ai_pair_question", "cancelled", "queued"),
    ("comparison_ai_sheet_item", "queued", "running"),
    ("comparison_ai_sheet_item", "queued", "cancelled"),
    ("comparison_ai_sheet_item", "queued", "skipped"),
    ("comparison_ai_sheet_item", "running", "done"),
    ("comparison_ai_sheet_item", "running", "failed"),
    ("comparison_ai_sheet_item", "running", "cancelled"),
    ("comparison_ai_sheet_item", "running", "queued"),
    ("comparison_ai_sheet_item", "failed", "queued"),
    ("comparison_ai_sheet_item", "cancelled", "queued"),
    ("comparison_spec_comparison", "queued", "running"),
    ("comparison_spec_comparison", "queued", "cancelled"),
    ("comparison_spec_comparison", "running", "completed"),
    ("comparison_spec_comparison", "running", "incomplete"),
    ("comparison_spec_comparison", "running", "failed"),
    ("comparison_spec_comparison", "running", "cancelled"),
    ("comparison_spec_comparison", "completed", "queued"),
    ("comparison_spec_comparison", "incomplete", "queued"),
    ("comparison_spec_comparison", "failed", "queued"),
    ("comparison_spec_comparison", "cancelled", "queued"),
    ("comparison_report", "draft", "queued"),
    ("comparison_report", "draft", "cancelled"),
    ("comparison_report", "queued", "running"),
    ("comparison_report", "queued", "paused"),
    ("comparison_report", "queued", "failed"),
    ("comparison_report", "queued", "cancelled"),
    ("comparison_report", "running", "paused"),
    ("comparison_report", "running", "completed"),
    ("comparison_report", "running", "partial"),
    ("comparison_report", "running", "failed"),
    ("comparison_report", "running", "cancelled"),
    ("comparison_report", "paused", "queued"),
    ("comparison_report", "paused", "running"),
    ("comparison_report", "paused", "cancelled"),
    ("comparison_report", "partial", "queued"),
    ("comparison_report", "failed", "queued"),
    ("comparison_report", "cancelled", "queued"),
    ("comparison_launch_entry", "waiting", "running"),
    ("comparison_launch_entry", "waiting", "needs_consent"),
    ("comparison_launch_entry", "waiting", "skipped"),
    ("comparison_launch_entry", "needs_consent", "waiting"),
    ("comparison_launch_entry", "needs_consent", "skipped"),
    ("comparison_launch_entry", "running", "done"),
    ("comparison_launch_entry", "running", "failed"),
    ("comparison_launch_entry", "running", "skipped"),
    ("comparison_launch_entry", "failed", "waiting"),
)

TABLES: tuple[str, ...] = (
    "comparison_ai_job", "comparison_ai_pair_answer", "comparison_ai_pair_question",
    "comparison_sheet_description", "comparison_ai_sheet_item", "comparison_spec_extraction",
    "comparison_spec_comparison", "comparison_report", "comparison_report_part",
    "comparison_report_artifact", "comparison_launch_queue", "comparison_launch_entry",
)

#: ``comparison_work``'s frozen list as ``0039`` left it, and with this revision's column.
_WORK_FROZEN = (
    "comparison_work_id", "project_uid", "module", "kind", "dedupe_key", "comparison_upload_id",
    "created_by_user_uid", "created_at", "comparison_series_id",
)


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _id(column: str, prefix: str, *, nullable: bool = False) -> str:
    check = f"{column} ~ '^{prefix}_{ULID}$'"
    return f"({column} IS NULL OR {check})" if nullable else check


def _edges_values() -> str:
    return ", ".join(f"('{t}', '{a}', '{b}')" for t, a, b in EDGES)


_EDGE_FUNCTION = f"""
        CREATE FUNCTION am_guard_comparison_ai_state_edges() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF OLD.state IS NOT DISTINCT FROM NEW.state THEN
                RETURN NEW;
            END IF;
            IF EXISTS (
                SELECT 1 FROM (VALUES {_edges_values()}) AS e (tbl, from_state, to_state)
                 WHERE e.tbl = TG_TABLE_NAME
                   AND e.from_state = OLD.state AND e.to_state = NEW.state
            ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'state_transition_not_allowed: % has no declared transition % -> %',
                TG_TABLE_NAME, OLD.state, NEW.state
                USING ERRCODE = 'AM001',
                      HINT = 'A comparison AI row moves only along the edges of migration 0040.';
        END
        $fn$;
        """

_JOB_SCOPE_FUNCTION = """
        CREATE FUNCTION am_check_comparison_ai_job_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.comparison_matrix_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_matrix m
                 WHERE m.comparison_matrix_id = NEW.comparison_matrix_id
                   AND m.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: build % is not a build of document %',
                    NEW.comparison_matrix_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.comparison_series_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_series s
                 WHERE s.comparison_series_id = NEW.comparison_series_id
                   AND s.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: series % is not a series of document %',
                    NEW.comparison_series_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.comparison_transition_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_transition t
                  JOIN comparison_series s ON s.comparison_series_id = t.comparison_series_id
                 WHERE t.comparison_transition_id = NEW.comparison_transition_id
                   AND s.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: transition % is not a transition of document %',
                    NEW.comparison_transition_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.comparison_sheet_pair_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_sheet_pair p
                  JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id
                  JOIN comparison_series s ON s.comparison_series_id = t.comparison_series_id
                 WHERE p.comparison_sheet_pair_id = NEW.comparison_sheet_pair_id
                   AND s.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: sheet pair % is not a pair of document %',
                    NEW.comparison_sheet_pair_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

#: The consent columns of a job change only together, and only by one consent number (a new consent after
#: an overrun or a route change, or for a retry). A change of the estimate under the same number is refused.
_JOB_CONSENT_FUNCTION = """
        CREATE FUNCTION am_guard_comparison_ai_job_consent() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF (NEW.estimate, NEW.estimate_digest, NEW.estimate_micros, NEW.ceiling_micros,
                NEW.connection_revision_id, NEW.pinned_model, NEW.provider_mode, NEW.consented_by_user_uid)
               IS DISTINCT FROM
               (OLD.estimate, OLD.estimate_digest, OLD.estimate_micros, OLD.ceiling_micros,
                OLD.connection_revision_id, OLD.pinned_model, OLD.provider_mode, OLD.consented_by_user_uid)
               AND NEW.consent_no <> OLD.consent_no + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the consented estimate of job % changes only with a new consent',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A new consent raises consent_no by one and carries the new estimate with it.';
            END IF;
            IF NEW.consent_no < OLD.consent_no OR NEW.consent_no > OLD.consent_no + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: consent_no of job % moves by one at most, upwards',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_PAIR_QUESTION_FUNCTION = """
        CREATE FUNCTION am_check_comparison_ai_pair_question() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM comparison_ai_job j
                 WHERE j.comparison_ai_job_id = NEW.comparison_ai_job_id
                   AND j.method = 'pair_check' AND j.document_uid = NEW.document_uid
                   AND j.project_uid = NEW.project_uid
                   AND j.comparison_matrix_id = NEW.comparison_matrix_id
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: job % is not a pair check of build % of document %',
                    NEW.comparison_ai_job_id, NEW.comparison_matrix_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM document_version a, document_version b
                 WHERE a.version_uid = NEW.page_version_uid AND a.document_uid = NEW.document_uid
                   AND NEW.page_number <= a.page_count
                   AND b.version_uid = NEW.version_uid AND b.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the page and the cell version of a question are of document %',
                    NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.hint_version_uid IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM document_version h
                 WHERE h.version_uid = NEW.hint_version_uid AND h.document_uid = NEW.document_uid
                   AND NEW.hint_page_number <= h.page_count
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the hinted page is not a page of a version of document %',
                    NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_SHEET_ITEM_FUNCTION = """
        CREATE FUNCTION am_check_comparison_ai_sheet_item() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM comparison_ai_job j
                  JOIN comparison_sheet_pair p ON p.comparison_sheet_pair_id = NEW.comparison_sheet_pair_id
                  JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id
                  JOIN comparison_series s ON s.comparison_series_id = t.comparison_series_id
                 WHERE j.comparison_ai_job_id = NEW.comparison_ai_job_id
                   AND j.method = 'sheet_changes' AND j.project_uid = NEW.project_uid
                   AND s.project_uid = NEW.project_uid AND s.document_uid = j.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: sheet pair % is not a pair of the sheet-description job %',
                    NEW.comparison_sheet_pair_id, NEW.comparison_ai_job_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_DESCRIPTION_FUNCTION = """
        CREATE FUNCTION am_check_comparison_sheet_description() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.result_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_sheet_pair_result r
                 WHERE r.comparison_sheet_pair_result_id = NEW.result_id
                   AND r.project_uid = NEW.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: result % is not a result of project %',
                    NEW.result_id, NEW.project_uid
                    USING ERRCODE = 'AM001',
                          HINT = 'A description is reused within one project only (ADR-0025 decision 15).';
            END IF;
            IF NEW.page_profile_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_page_profile p
                  JOIN document_version v ON v.version_uid = p.version_uid
                  JOIN document d ON d.document_uid = v.document_uid
                 WHERE p.comparison_page_profile_id = NEW.page_profile_id
                   AND d.project_uid = NEW.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: page profile % is not a page of project %',
                    NEW.page_profile_id, NEW.project_uid
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_EXTRACTION_FUNCTION = """
        CREATE FUNCTION am_check_comparison_spec_extraction() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM document_version v
                  JOIN document d ON d.document_uid = v.document_uid
                 WHERE v.version_uid = NEW.version_uid AND d.project_uid = NEW.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: version % is not a version of project %',
                    NEW.version_uid, NEW.project_uid
                    USING ERRCODE = 'AM001',
                          HINT = 'An extraction is reused within one project only (ADR-0025 decision 15).';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_SPEC_COMPARISON_FUNCTION = """
        CREATE FUNCTION am_check_comparison_spec_comparison() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            t record;
        BEGIN
            SELECT tt.source_version_uid, tt.target_version_uid, s.document_uid, s.project_uid
              INTO t
              FROM comparison_transition tt
              JOIN comparison_series s ON s.comparison_series_id = tt.comparison_series_id
             WHERE tt.comparison_transition_id = NEW.comparison_transition_id;
            IF t.document_uid IS DISTINCT FROM NEW.document_uid OR t.project_uid IS DISTINCT FROM NEW.project_uid THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: transition % is not a transition of document %',
                    NEW.comparison_transition_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.comparison_ai_job_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_ai_job j
                 WHERE j.comparison_ai_job_id = NEW.comparison_ai_job_id
                   AND j.method = 'spec'
                   AND j.comparison_transition_id = NEW.comparison_transition_id
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: job % is not the specification job of transition %',
                    NEW.comparison_ai_job_id, NEW.comparison_transition_id
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.extraction_a_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_spec_extraction x
                 WHERE x.comparison_spec_extraction_id = NEW.extraction_a_id
                   AND x.version_uid = t.source_version_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: extraction % is not of the older version of transition %',
                    NEW.extraction_a_id, NEW.comparison_transition_id
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.extraction_b_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_spec_extraction x
                 WHERE x.comparison_spec_extraction_id = NEW.extraction_b_id
                   AND x.version_uid = t.target_version_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: extraction % is not of the newer version of transition %',
                    NEW.extraction_b_id, NEW.comparison_transition_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_REPORT_FUNCTION = """
        CREATE FUNCTION am_check_comparison_report() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM comparison_series s
                 WHERE s.comparison_series_id = NEW.comparison_series_id
                   AND s.document_uid = NEW.document_uid AND s.project_uid = NEW.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: series % is not a series of document %',
                    NEW.comparison_series_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.comparison_ai_job_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_ai_job j
                 WHERE j.comparison_ai_job_id = NEW.comparison_ai_job_id
                   AND j.method = 'report' AND j.comparison_series_id = NEW.comparison_series_id
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: job % is not a report job of series %',
                    NEW.comparison_ai_job_id, NEW.comparison_series_id
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.prepared_from_report_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_report r
                 WHERE r.comparison_report_id = NEW.prepared_from_report_id
                   AND r.comparison_series_id = NEW.comparison_series_id AND r.kind = 'analytic'
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: report % is not an analytic report of series %',
                    NEW.prepared_from_report_id, NEW.comparison_series_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A client report is prepared from an analytic report of the same series.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_REPORT_PART_FUNCTION = """
        CREATE FUNCTION am_check_comparison_report_part() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM comparison_report r
                  JOIN comparison_transition t ON t.comparison_series_id = r.comparison_series_id
                 WHERE r.comparison_report_id = NEW.comparison_report_id
                   AND t.comparison_transition_id = NEW.comparison_transition_id
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: transition % is not a transition of the series of report %',
                    NEW.comparison_transition_id, NEW.comparison_report_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_FUNCTIONS: tuple[str, ...] = (
    "am_check_comparison_report_part", "am_check_comparison_report",
    "am_check_comparison_spec_comparison", "am_check_comparison_spec_extraction",
    "am_check_comparison_sheet_description", "am_check_comparison_ai_sheet_item",
    "am_check_comparison_ai_pair_question", "am_guard_comparison_ai_job_consent",
    "am_check_comparison_ai_job_scope", "am_guard_comparison_ai_state_edges",
)


def upgrade() -> None:
    _functions()
    _tables()
    _alter_existing()
    _guards()
    _comments()


def _functions() -> None:
    for function in (
        _EDGE_FUNCTION, _JOB_SCOPE_FUNCTION, _JOB_CONSENT_FUNCTION, _PAIR_QUESTION_FUNCTION,
        _SHEET_ITEM_FUNCTION, _DESCRIPTION_FUNCTION, _EXTRACTION_FUNCTION, _SPEC_COMPARISON_FUNCTION,
        _REPORT_FUNCTION, _REPORT_PART_FUNCTION,
    ):
        op.execute(function)


def _tables() -> None:
    _job()
    _pair_check()
    _sheet_changes()
    _specification()
    _report()
    _launch()


def _job() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_ai_job (
            comparison_ai_job_id      text PRIMARY KEY,
            project_uid               text NOT NULL,
            document_uid              text NOT NULL,
            method                    text NOT NULL,
            state                     text NOT NULL DEFAULT 'queued',
            pause_reason              text NULL,
            failure_reason            text NULL,
            comparison_matrix_id      text NULL,
            comparison_series_id      text NULL,
            comparison_transition_id  text NULL,
            comparison_sheet_pair_id  text NULL,
            restart                   boolean NOT NULL DEFAULT false,
            connection_revision_id    text NOT NULL,
            pinned_model              text NOT NULL,
            provider_mode             text NOT NULL,
            estimate                  jsonb NOT NULL,
            estimate_digest           text NOT NULL,
            estimate_micros           bigint NOT NULL,
            ceiling_micros            bigint NOT NULL,
            consent_no                integer NOT NULL DEFAULT 1,
            consented_by_user_uid     text NOT NULL,
            consented_at              timestamptz NOT NULL DEFAULT clock_timestamp(),
            command_id                text NOT NULL,
            created_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            finished_at               timestamptz NULL,
            CONSTRAINT fk_comparison_ai_job_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_matrix
                FOREIGN KEY (comparison_matrix_id) REFERENCES comparison_matrix (comparison_matrix_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_series
                FOREIGN KEY (comparison_series_id) REFERENCES comparison_series (comparison_series_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_transition
                FOREIGN KEY (comparison_transition_id) REFERENCES comparison_transition (comparison_transition_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_sheet_pair
                FOREIGN KEY (comparison_sheet_pair_id) REFERENCES comparison_sheet_pair (comparison_sheet_pair_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_revision
                FOREIGN KEY (connection_revision_id)
                REFERENCES executor_connection_revision (revision_id) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_job_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_ai_job_command UNIQUE (command_id),
            CONSTRAINT uq_comparison_ai_job_document UNIQUE (comparison_ai_job_id, document_uid),
            CONSTRAINT ck_comparison_ai_job_id_format CHECK ({_id('comparison_ai_job_id', 'cai')}),
            CONSTRAINT ck_comparison_ai_job_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_ai_job_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_ai_job_scope_ids_format CHECK (
                {_id('comparison_matrix_id', 'cmx', nullable=True)}
                AND {_id('comparison_series_id', 'cser', nullable=True)}
                AND {_id('comparison_transition_id', 'ctn', nullable=True)}
                AND {_id('comparison_sheet_pair_id', 'ctp', nullable=True)}),
            CONSTRAINT ck_comparison_ai_job_revision_id_format
                CHECK ({_id('connection_revision_id', 'excr')}),
            CONSTRAINT ck_comparison_ai_job_consented_by_format
                CHECK ({_id('consented_by_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_ai_job_command_id_format CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_comparison_ai_job_method CHECK (method IN ({_sql_list(METHODS)})),
            CONSTRAINT ck_comparison_ai_job_state CHECK (state IN ({_sql_list(JOB_STATES)})),
            CONSTRAINT ck_comparison_ai_job_pause_reason CHECK (
                (state = 'paused') = (pause_reason IS NOT NULL)
                AND (pause_reason IS NULL OR pause_reason IN ({_sql_list(PAUSE_REASONS)}))),
            CONSTRAINT ck_comparison_ai_job_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR failure_reason ~ '^[a-z][a-z0-9_]{{2,63}}$')),
            CONSTRAINT ck_comparison_ai_job_provider_mode
                CHECK (provider_mode IN ({_sql_list(PROVIDER_MODES)})),
            CONSTRAINT ck_comparison_ai_job_pinned_model
                CHECK (char_length(pinned_model) BETWEEN 1 AND 128),
            CONSTRAINT ck_comparison_ai_job_estimate_is_object CHECK (jsonb_typeof(estimate) = 'object'),
            CONSTRAINT ck_comparison_ai_job_estimate_digest CHECK (
                estimate_digest ~ '{SHA256}' AND estimate ->> 'estimate_digest' = estimate_digest),
            CONSTRAINT ck_comparison_ai_job_money
                CHECK (estimate_micros >= 0 AND ceiling_micros >= 0),
            CONSTRAINT ck_comparison_ai_job_consent_no CHECK (consent_no >= 1),
            CONSTRAINT ck_comparison_ai_job_scope CHECK (
                (method = 'pair_check'
                    AND comparison_matrix_id IS NOT NULL AND comparison_series_id IS NULL
                    AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL)
                OR (method = 'sheet_changes' AND comparison_matrix_id IS NULL
                    AND comparison_transition_id IS NULL
                    AND ((comparison_series_id IS NOT NULL) <> (comparison_sheet_pair_id IS NOT NULL)))
                OR (method = 'spec'
                    AND comparison_transition_id IS NOT NULL AND comparison_matrix_id IS NULL
                    AND comparison_series_id IS NULL AND comparison_sheet_pair_id IS NULL)
                OR (method = 'report'
                    AND comparison_series_id IS NOT NULL AND comparison_matrix_id IS NULL
                    AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL)),
            CONSTRAINT ck_comparison_ai_job_finished_at CHECK (
                (state IN ('completed', 'failed', 'cancelled')) = (finished_at IS NOT NULL))
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_ai_job_document ON comparison_ai_job (document_uid, created_at);")
    op.execute("CREATE INDEX ix_comparison_ai_job_project ON comparison_ai_job (project_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_ai_job_queue ON comparison_ai_job (method, created_at) "
        f"WHERE state IN ({_sql_list(JOB_LIVE)});"
    )
    live = f"state IN ({_sql_list(JOB_LIVE)})"
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_ai_job_live_pair_check ON comparison_ai_job (document_uid) "
        f"WHERE method = 'pair_check' AND {live};"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_ai_job_live_series ON comparison_ai_job (comparison_series_id) "
        f"WHERE method = 'sheet_changes' AND comparison_series_id IS NOT NULL AND {live};"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_ai_job_live_sheet ON comparison_ai_job (comparison_sheet_pair_id) "
        f"WHERE method = 'sheet_changes' AND comparison_sheet_pair_id IS NOT NULL AND {live};"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_ai_job_live_spec ON comparison_ai_job (comparison_transition_id) "
        f"WHERE method = 'spec' AND {live};"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_job_series ON comparison_ai_job (comparison_series_id) "
        "WHERE comparison_series_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_job_transition ON comparison_ai_job (comparison_transition_id) "
        "WHERE comparison_transition_id IS NOT NULL;"
    )


def _pair_check() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_ai_pair_answer (
            comparison_ai_pair_answer_id text PRIMARY KEY,
            project_uid                  text NOT NULL,
            content_key                  text NOT NULL,
            question_kind                text NOT NULL,
            prompt_version               text NOT NULL,
            model_identity               text NOT NULL,
            confidence                   text NOT NULL,
            answer                       jsonb NOT NULL,
            comparison_model_call_id     text NULL,
            created_at                   timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_ai_pair_answer_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_answer_model_call
                FOREIGN KEY (comparison_model_call_id)
                REFERENCES comparison_model_call (comparison_model_call_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_ai_pair_answer_content UNIQUE (project_uid, content_key),
            CONSTRAINT ck_comparison_ai_pair_answer_id_format
                CHECK ({_id('comparison_ai_pair_answer_id', 'cpa')}),
            CONSTRAINT ck_comparison_ai_pair_answer_project_uid_format
                CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_ai_pair_answer_model_call_format
                CHECK ({_id('comparison_model_call_id', 'cmc', nullable=True)}),
            CONSTRAINT ck_comparison_ai_pair_answer_content_key CHECK (content_key ~ '{SHA256}'),
            CONSTRAINT ck_comparison_ai_pair_answer_kind
                CHECK (question_kind IN ({_sql_list(ANSWER_KINDS)})),
            CONSTRAINT ck_comparison_ai_pair_answer_prompt_version
                CHECK (char_length(prompt_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_ai_pair_answer_model
                CHECK (char_length(model_identity) BETWEEN 1 AND 200),
            CONSTRAINT ck_comparison_ai_pair_answer_confidence
                CHECK (confidence IN ({_sql_list(CONFIDENCES)})),
            CONSTRAINT ck_comparison_ai_pair_answer_is_object CHECK (jsonb_typeof(answer) = 'object')
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_pair_answer_call ON comparison_ai_pair_answer "
        "(comparison_model_call_id) WHERE comparison_model_call_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_ai_pair_question (
            comparison_ai_pair_question_id text PRIMARY KEY,
            comparison_ai_job_id           text NOT NULL,
            project_uid                    text NOT NULL,
            document_uid                   text NOT NULL,
            comparison_matrix_id           text NOT NULL,
            kind                           text NOT NULL,
            page_version_uid               text NOT NULL,
            page_number                    integer NOT NULL,
            version_uid                    text NOT NULL,
            candidates                     jsonb NOT NULL DEFAULT '[]'::jsonb,
            state                          text NOT NULL DEFAULT 'queued',
            answer_id                      text NULL,
            reverse_answer_id              text NULL,
            decision                       text NULL,
            hint_version_uid               text NULL,
            hint_page_number               integer NULL,
            comparison_ai_link_id          text NULL,
            failure_reason                 text NULL,
            created_at                     timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                     timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_ai_pair_question_job
                FOREIGN KEY (comparison_ai_job_id, document_uid)
                REFERENCES comparison_ai_job (comparison_ai_job_id, document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_matrix
                FOREIGN KEY (comparison_matrix_id, document_uid)
                REFERENCES comparison_matrix (comparison_matrix_id, document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_page_version
                FOREIGN KEY (page_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_version
                FOREIGN KEY (version_uid) REFERENCES document_version (version_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_hint_version
                FOREIGN KEY (hint_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_answer
                FOREIGN KEY (answer_id) REFERENCES comparison_ai_pair_answer (comparison_ai_pair_answer_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_reverse
                FOREIGN KEY (reverse_answer_id)
                REFERENCES comparison_ai_pair_answer (comparison_ai_pair_answer_id) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_pair_question_link
                FOREIGN KEY (comparison_ai_link_id) REFERENCES comparison_ai_link (comparison_ai_link_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_ai_pair_question_cell UNIQUE
                (comparison_ai_job_id, page_version_uid, page_number, version_uid),
            CONSTRAINT uq_comparison_ai_pair_question_link UNIQUE (comparison_ai_link_id),
            CONSTRAINT ck_comparison_ai_pair_question_id_format
                CHECK ({_id('comparison_ai_pair_question_id', 'cpq')}),
            CONSTRAINT ck_comparison_ai_pair_question_job_id_format
                CHECK ({_id('comparison_ai_job_id', 'cai')}),
            CONSTRAINT ck_comparison_ai_pair_question_project_uid_format
                CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_ai_pair_question_document_uid_format
                CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_ai_pair_question_matrix_id_format
                CHECK ({_id('comparison_matrix_id', 'cmx')}),
            CONSTRAINT ck_comparison_ai_pair_question_version_uids_format CHECK (
                {_id('page_version_uid', 'ver')} AND {_id('version_uid', 'ver')}
                AND {_id('hint_version_uid', 'ver', nullable=True)}),
            CONSTRAINT ck_comparison_ai_pair_question_answer_ids_format CHECK (
                {_id('answer_id', 'cpa', nullable=True)} AND {_id('reverse_answer_id', 'cpa', nullable=True)}),
            CONSTRAINT ck_comparison_ai_pair_question_link_id_format
                CHECK ({_id('comparison_ai_link_id', 'cak', nullable=True)}),
            CONSTRAINT ck_comparison_ai_pair_question_kind CHECK (kind IN ({_sql_list(QUESTION_KINDS)})),
            CONSTRAINT ck_comparison_ai_pair_question_state
                CHECK (state IN ({_sql_list(QUESTION_STATES)})),
            CONSTRAINT ck_comparison_ai_pair_question_decision
                CHECK (decision IS NULL OR decision IN ({_sql_list(DECISIONS)})),
            CONSTRAINT ck_comparison_ai_pair_question_page_numbers CHECK (
                page_number BETWEEN 1 AND {MAX_PAGE_NUMBER}
                AND (hint_page_number IS NULL OR hint_page_number BETWEEN 1 AND {MAX_PAGE_NUMBER})),
            CONSTRAINT ck_comparison_ai_pair_question_cell_differs CHECK (page_version_uid <> version_uid),
            CONSTRAINT ck_comparison_ai_pair_question_candidates
                CHECK (jsonb_typeof(candidates) = 'array' AND jsonb_array_length(candidates) <= 8),
            CONSTRAINT ck_comparison_ai_pair_question_hint_pair
                CHECK ((hint_version_uid IS NULL) = (hint_page_number IS NULL)),
            CONSTRAINT ck_comparison_ai_pair_question_answered CHECK (
                (state = 'answered') = (decision IS NOT NULL AND decision <> 'failed')
                AND (state <> 'answered' OR answer_id IS NOT NULL)),
            CONSTRAINT ck_comparison_ai_pair_question_failed CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR failure_reason ~ '^[a-z][a-z0-9_]{{2,63}}$')),
            CONSTRAINT ck_comparison_ai_pair_question_link CHECK (
                comparison_ai_link_id IS NULL OR decision = 'accepted'),
            CONSTRAINT ck_comparison_ai_pair_question_reverse CHECK (
                reverse_answer_id IS NULL OR answer_id IS NOT NULL)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_pair_question_job ON comparison_ai_pair_question "
        "(comparison_ai_job_id, state);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_pair_question_document ON comparison_ai_pair_question "
        "(document_uid, created_at);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_pair_question_project ON comparison_ai_pair_question (project_uid);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_pair_question_matrix ON comparison_ai_pair_question "
        "(comparison_matrix_id);"
    )
    for column in ("answer_id", "reverse_answer_id"):
        op.execute(
            f"CREATE INDEX ix_comparison_ai_pair_question_{column} ON comparison_ai_pair_question "
            f"({column}) WHERE {column} IS NOT NULL;"
        )


def _sheet_changes() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_sheet_description (
            comparison_sheet_description_id text PRIMARY KEY,
            project_uid                     text NOT NULL,
            content_key                     text NOT NULL,
            result_id                       text NULL,
            page_profile_id                 text NULL,
            state                           text NOT NULL,
            source                          text NOT NULL DEFAULT 'sheet',
            prompt_version                  text NOT NULL,
            model_identity                  text NOT NULL,
            recorded                        boolean NOT NULL DEFAULT false,
            description                     jsonb NOT NULL,
            calls                           integer NOT NULL DEFAULT 0,
            input_tokens                    bigint NOT NULL DEFAULT 0,
            output_tokens                   bigint NOT NULL DEFAULT 0,
            comparison_model_call_id        text NULL,
            created_at                      timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_sheet_description_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_description_result
                FOREIGN KEY (result_id) REFERENCES comparison_sheet_pair_result (comparison_sheet_pair_result_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_description_page
                FOREIGN KEY (page_profile_id) REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_description_model_call
                FOREIGN KEY (comparison_model_call_id)
                REFERENCES comparison_model_call (comparison_model_call_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_sheet_description_content UNIQUE (project_uid, content_key),
            CONSTRAINT ck_comparison_sheet_description_id_format
                CHECK ({_id('comparison_sheet_description_id', 'csd')}),
            CONSTRAINT ck_comparison_sheet_description_project_uid_format
                CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_sheet_description_result_id_format
                CHECK ({_id('result_id', 'csp', nullable=True)}),
            CONSTRAINT ck_comparison_sheet_description_page_id_format
                CHECK ({_id('page_profile_id', 'cpr', nullable=True)}),
            CONSTRAINT ck_comparison_sheet_description_model_call_format
                CHECK ({_id('comparison_model_call_id', 'cmc', nullable=True)}),
            CONSTRAINT ck_comparison_sheet_description_content_key CHECK (content_key ~ '{SHA256}'),
            CONSTRAINT ck_comparison_sheet_description_subject
                CHECK ((result_id IS NOT NULL) <> (page_profile_id IS NOT NULL)),
            CONSTRAINT ck_comparison_sheet_description_state
                CHECK (state IN ({_sql_list(DESCRIPTION_STATES)})),
            CONSTRAINT ck_comparison_sheet_description_source
                CHECK (source IN ({_sql_list(DESCRIPTION_SOURCES)})),
            CONSTRAINT ck_comparison_sheet_description_prompt_version
                CHECK (char_length(prompt_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_sheet_description_model
                CHECK (char_length(model_identity) BETWEEN 1 AND 200),
            CONSTRAINT ck_comparison_sheet_description_is_object
                CHECK (jsonb_typeof(description) = 'object'),
            CONSTRAINT ck_comparison_sheet_description_figures
                CHECK (calls >= 0 AND input_tokens >= 0 AND output_tokens >= 0)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_description_result ON comparison_sheet_description "
        "(result_id, created_at) WHERE result_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_description_page ON comparison_sheet_description "
        "(page_profile_id, created_at) WHERE page_profile_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_description_project ON comparison_sheet_description (project_uid);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_description_call ON comparison_sheet_description "
        "(comparison_model_call_id) WHERE comparison_model_call_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_ai_sheet_item (
            comparison_ai_sheet_item_id     text PRIMARY KEY,
            comparison_ai_job_id            text NOT NULL,
            project_uid                     text NOT NULL,
            comparison_sheet_pair_id        text NOT NULL,
            state                           text NOT NULL DEFAULT 'queued',
            comparison_sheet_description_id text NULL,
            failure_reason                  text NULL,
            calls                           integer NOT NULL DEFAULT 0,
            input_tokens                    bigint NOT NULL DEFAULT 0,
            output_tokens                   bigint NOT NULL DEFAULT 0,
            elapsed_ms                      bigint NOT NULL DEFAULT 0,
            created_at                      timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                      timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_ai_sheet_item_job
                FOREIGN KEY (comparison_ai_job_id) REFERENCES comparison_ai_job (comparison_ai_job_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_sheet_item_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_sheet_item_pair
                FOREIGN KEY (comparison_sheet_pair_id) REFERENCES comparison_sheet_pair (comparison_sheet_pair_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_sheet_item_description
                FOREIGN KEY (comparison_sheet_description_id)
                REFERENCES comparison_sheet_description (comparison_sheet_description_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_ai_sheet_item_pair UNIQUE (comparison_ai_job_id, comparison_sheet_pair_id),
            CONSTRAINT ck_comparison_ai_sheet_item_id_format
                CHECK ({_id('comparison_ai_sheet_item_id', 'csi')}),
            CONSTRAINT ck_comparison_ai_sheet_item_job_id_format CHECK ({_id('comparison_ai_job_id', 'cai')}),
            CONSTRAINT ck_comparison_ai_sheet_item_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_ai_sheet_item_pair_id_format
                CHECK ({_id('comparison_sheet_pair_id', 'ctp')}),
            CONSTRAINT ck_comparison_ai_sheet_item_description_id_format
                CHECK ({_id('comparison_sheet_description_id', 'csd', nullable=True)}),
            CONSTRAINT ck_comparison_ai_sheet_item_state CHECK (state IN ({_sql_list(ITEM_STATES)})),
            CONSTRAINT ck_comparison_ai_sheet_item_done
                CHECK ((state = 'done') = (comparison_sheet_description_id IS NOT NULL)),
            CONSTRAINT ck_comparison_ai_sheet_item_failed CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR failure_reason ~ '^[a-z][a-z0-9_]{{2,63}}$')),
            CONSTRAINT ck_comparison_ai_sheet_item_figures
                CHECK (calls >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND elapsed_ms >= 0)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_sheet_item_job ON comparison_ai_sheet_item "
        "(comparison_ai_job_id, state);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_sheet_item_pair ON comparison_ai_sheet_item (comparison_sheet_pair_id);"
    )
    op.execute("CREATE INDEX ix_comparison_ai_sheet_item_project ON comparison_ai_sheet_item (project_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_ai_sheet_item_description ON comparison_ai_sheet_item "
        "(comparison_sheet_description_id) WHERE comparison_sheet_description_id IS NOT NULL;"
    )


def _specification() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_spec_extraction (
            comparison_spec_extraction_id text PRIMARY KEY,
            project_uid                   text NOT NULL,
            version_uid                   text NOT NULL,
            content_key                   text NOT NULL,
            state                         text NOT NULL,
            prompt_version                text NOT NULL,
            model_identity                text NOT NULL,
            recorded                      boolean NOT NULL DEFAULT false,
            source_sha256                 text NOT NULL,
            positions                     jsonb NOT NULL,
            coverage                      jsonb NOT NULL,
            comparison_model_call_id      text NULL,
            created_at                    timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_spec_extraction_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_extraction_version
                FOREIGN KEY (version_uid) REFERENCES document_version (version_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_extraction_model_call
                FOREIGN KEY (comparison_model_call_id)
                REFERENCES comparison_model_call (comparison_model_call_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_spec_extraction_content UNIQUE (project_uid, content_key),
            CONSTRAINT uq_comparison_spec_extraction_version UNIQUE (comparison_spec_extraction_id, version_uid),
            CONSTRAINT ck_comparison_spec_extraction_id_format
                CHECK ({_id('comparison_spec_extraction_id', 'cse')}),
            CONSTRAINT ck_comparison_spec_extraction_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_spec_extraction_version_uid_format CHECK ({_id('version_uid', 'ver')}),
            CONSTRAINT ck_comparison_spec_extraction_model_call_format
                CHECK ({_id('comparison_model_call_id', 'cmc', nullable=True)}),
            CONSTRAINT ck_comparison_spec_extraction_hashes
                CHECK (content_key ~ '{SHA256}' AND source_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_spec_extraction_state
                CHECK (state IN ({_sql_list(EXTRACTION_STATES)})),
            CONSTRAINT ck_comparison_spec_extraction_prompt_version
                CHECK (char_length(prompt_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_spec_extraction_model
                CHECK (char_length(model_identity) BETWEEN 1 AND 200),
            CONSTRAINT ck_comparison_spec_extraction_positions_is_array
                CHECK (jsonb_typeof(positions) = 'array'),
            CONSTRAINT ck_comparison_spec_extraction_coverage_is_object
                CHECK (jsonb_typeof(coverage) = 'object')
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_spec_extraction_version ON comparison_spec_extraction (version_uid);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_spec_extraction_call ON comparison_spec_extraction "
        "(comparison_model_call_id) WHERE comparison_model_call_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_spec_comparison (
            comparison_spec_comparison_id text PRIMARY KEY,
            project_uid                   text NOT NULL,
            document_uid                  text NOT NULL,
            comparison_transition_id      text NOT NULL,
            source                        text NOT NULL,
            state                         text NOT NULL DEFAULT 'queued',
            phase                         text NULL,
            comparison_ai_job_id          text NULL,
            extraction_a_id               text NULL,
            extraction_b_id               text NULL,
            sheets_a                      integer NOT NULL DEFAULT 0,
            sheets_b                      integer NOT NULL DEFAULT 0,
            coverage_a                    jsonb NULL,
            coverage_b                    jsonb NULL,
            totals                        jsonb NULL,
            changes                       jsonb NOT NULL DEFAULT '[]'::jsonb,
            reason                        text NULL,
            created_at                    timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                    timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_spec_comparison_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_comparison_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_comparison_transition
                FOREIGN KEY (comparison_transition_id) REFERENCES comparison_transition (comparison_transition_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_comparison_job
                FOREIGN KEY (comparison_ai_job_id) REFERENCES comparison_ai_job (comparison_ai_job_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_comparison_extraction_a
                FOREIGN KEY (extraction_a_id) REFERENCES comparison_spec_extraction (comparison_spec_extraction_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_spec_comparison_extraction_b
                FOREIGN KEY (extraction_b_id) REFERENCES comparison_spec_extraction (comparison_spec_extraction_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_spec_comparison_source UNIQUE (comparison_transition_id, source),
            CONSTRAINT ck_comparison_spec_comparison_id_format
                CHECK ({_id('comparison_spec_comparison_id', 'cscp')}),
            CONSTRAINT ck_comparison_spec_comparison_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_spec_comparison_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_spec_comparison_transition_id_format
                CHECK ({_id('comparison_transition_id', 'ctn')}),
            CONSTRAINT ck_comparison_spec_comparison_job_id_format
                CHECK ({_id('comparison_ai_job_id', 'cai', nullable=True)}),
            CONSTRAINT ck_comparison_spec_comparison_extraction_ids_format CHECK (
                {_id('extraction_a_id', 'cse', nullable=True)} AND {_id('extraction_b_id', 'cse', nullable=True)}),
            CONSTRAINT ck_comparison_spec_comparison_source CHECK (source IN ({_sql_list(SPEC_SOURCES)})),
            CONSTRAINT ck_comparison_spec_comparison_state CHECK (state IN ({_sql_list(SPEC_STATES)})),
            CONSTRAINT ck_comparison_spec_comparison_phase
                CHECK (phase IS NULL OR phase IN ({_sql_list(SPEC_PHASES)})),
            CONSTRAINT ck_comparison_spec_comparison_source_shape CHECK (
                (source = 'positions' AND comparison_ai_job_id IS NULL
                    AND extraction_a_id IS NULL AND extraction_b_id IS NULL)
                OR (source = 'whole' AND comparison_ai_job_id IS NOT NULL)),
            CONSTRAINT ck_comparison_spec_comparison_sheets CHECK (sheets_a >= 0 AND sheets_b >= 0),
            CONSTRAINT ck_comparison_spec_comparison_changes_is_array
                CHECK (jsonb_typeof(changes) = 'array'),
            CONSTRAINT ck_comparison_spec_comparison_objects CHECK (
                (coverage_a IS NULL OR jsonb_typeof(coverage_a) = 'object')
                AND (coverage_b IS NULL OR jsonb_typeof(coverage_b) = 'object')
                AND (totals IS NULL OR jsonb_typeof(totals) = 'object')),
            CONSTRAINT ck_comparison_spec_comparison_reason CHECK (
                (reason IS NULL OR reason ~ '^[A-Z][A-Z0-9_]{{2,63}}$')
                AND (state NOT IN ('failed', 'incomplete') OR reason IS NOT NULL)),
            CONSTRAINT ck_comparison_spec_comparison_completed
                CHECK (state <> 'completed' OR totals IS NOT NULL)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_spec_comparison_document ON comparison_spec_comparison (document_uid);"
    )
    op.execute("CREATE INDEX ix_comparison_spec_comparison_project ON comparison_spec_comparison (project_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_spec_comparison_job ON comparison_spec_comparison (comparison_ai_job_id) "
        "WHERE comparison_ai_job_id IS NOT NULL;"
    )
    for column in ("extraction_a_id", "extraction_b_id"):
        op.execute(
            f"CREATE INDEX ix_comparison_spec_comparison_{column} ON comparison_spec_comparison "
            f"({column}) WHERE {column} IS NOT NULL;"
        )


def _report() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_report (
            comparison_report_id     text PRIMARY KEY,
            project_uid              text NOT NULL,
            document_uid             text NOT NULL,
            comparison_series_id     text NOT NULL,
            kind                     text NOT NULL,
            source                   text NOT NULL,
            state                    text NOT NULL DEFAULT 'draft',
            stage                    text NULL,
            comparison_ai_job_id     text NULL,
            estimate                 jsonb NOT NULL,
            estimate_digest          text NOT NULL,
            reuse                    boolean NOT NULL DEFAULT false,
            source_name              text NULL,
            source_sha256            text NOT NULL,
            prepared_from_report_id  text NULL,
            failure_reason           text NULL,
            deleted_at               timestamptz NULL,
            actor_user_uid           text NOT NULL,
            actor_label              text NOT NULL,
            command_id               text NOT NULL,
            created_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            finished_at              timestamptz NULL,
            CONSTRAINT fk_comparison_report_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_series
                FOREIGN KEY (comparison_series_id) REFERENCES comparison_series (comparison_series_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_job
                FOREIGN KEY (comparison_ai_job_id) REFERENCES comparison_ai_job (comparison_ai_job_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_prepared_from
                FOREIGN KEY (prepared_from_report_id) REFERENCES comparison_report (comparison_report_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_report_command UNIQUE (command_id),
            CONSTRAINT uq_comparison_report_job UNIQUE (comparison_ai_job_id),
            CONSTRAINT ck_comparison_report_id_format CHECK ({_id('comparison_report_id', 'crt')}),
            CONSTRAINT ck_comparison_report_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_report_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_report_series_id_format CHECK ({_id('comparison_series_id', 'cser')}),
            CONSTRAINT ck_comparison_report_job_id_format
                CHECK ({_id('comparison_ai_job_id', 'cai', nullable=True)}),
            CONSTRAINT ck_comparison_report_prepared_from_format
                CHECK ({_id('prepared_from_report_id', 'crt', nullable=True)}),
            CONSTRAINT ck_comparison_report_actor_user_uid_format CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_report_command_id_format CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_comparison_report_kind CHECK (kind IN ({_sql_list(REPORT_KINDS)})),
            CONSTRAINT ck_comparison_report_source CHECK (source IN ({_sql_list(REPORT_SOURCES)})),
            CONSTRAINT ck_comparison_report_state CHECK (state IN ({_sql_list(REPORT_STATES)})),
            CONSTRAINT ck_comparison_report_stage
                CHECK (stage IS NULL OR stage IN ({_sql_list(REPORT_STAGES)})),
            CONSTRAINT ck_comparison_report_estimate_digest CHECK (
                jsonb_typeof(estimate) = 'object' AND estimate_digest ~ '{SHA256}'
                AND estimate ->> 'estimate_digest' = estimate_digest),
            CONSTRAINT ck_comparison_report_source_sha256 CHECK (source_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_report_source_name
                CHECK (source_name IS NULL OR char_length(source_name) BETWEEN 1 AND 200),
            CONSTRAINT ck_comparison_report_job_when_started
                CHECK ((state = 'draft') = (comparison_ai_job_id IS NULL)
                       OR (state = 'cancelled')),
            CONSTRAINT ck_comparison_report_prepared_is_client
                CHECK (prepared_from_report_id IS NULL OR kind = 'client'),
            CONSTRAINT ck_comparison_report_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR failure_reason ~ '^[a-z][a-z0-9_]{{2,63}}$')),
            CONSTRAINT ck_comparison_report_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n')),
            CONSTRAINT ck_comparison_report_finished_at CHECK (
                (state IN ('completed', 'partial', 'failed', 'cancelled')) = (finished_at IS NOT NULL))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_report_series ON comparison_report (comparison_series_id, created_at);"
    )
    op.execute("CREATE INDEX ix_comparison_report_project ON comparison_report (project_uid);")
    op.execute("CREATE INDEX ix_comparison_report_document ON comparison_report (document_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_report_prepared_from ON comparison_report (prepared_from_report_id) "
        "WHERE prepared_from_report_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_report_part (
            comparison_report_part_id text PRIMARY KEY,
            comparison_report_id      text NOT NULL,
            comparison_transition_id  text NOT NULL,
            analysis                  text NULL,
            verification              text NULL,
            selection                 text NULL,
            facts                     jsonb NULL,
            warnings                  integer NULL,
            points                    integer NULL,
            questions                 integer NULL,
            created_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_report_part_report
                FOREIGN KEY (comparison_report_id) REFERENCES comparison_report (comparison_report_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_part_transition
                FOREIGN KEY (comparison_transition_id) REFERENCES comparison_transition (comparison_transition_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_report_part_transition UNIQUE (comparison_report_id, comparison_transition_id),
            CONSTRAINT ck_comparison_report_part_id_format
                CHECK ({_id('comparison_report_part_id', 'crpt')}),
            CONSTRAINT ck_comparison_report_part_report_id_format CHECK ({_id('comparison_report_id', 'crt')}),
            CONSTRAINT ck_comparison_report_part_transition_id_format
                CHECK ({_id('comparison_transition_id', 'ctn')}),
            CONSTRAINT ck_comparison_report_part_marks CHECK (
                (analysis IS NULL OR analysis IN ({_sql_list(UNIT_MARKS)}))
                AND (verification IS NULL OR verification IN ({_sql_list(UNIT_MARKS)}))
                AND (selection IS NULL OR selection IN ({_sql_list(UNIT_MARKS)}))),
            CONSTRAINT ck_comparison_report_part_facts
                CHECK (facts IS NULL OR jsonb_typeof(facts) = 'object'),
            CONSTRAINT ck_comparison_report_part_counts CHECK (
                (warnings IS NULL OR warnings >= 0) AND (points IS NULL OR points >= 0)
                AND (questions IS NULL OR questions >= 0))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_report_part_transition ON comparison_report_part "
        "(comparison_transition_id);"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_report_artifact (
            comparison_report_artifact_id text PRIMARY KEY,
            comparison_report_id          text NOT NULL,
            kind                          text NOT NULL,
            blob_id                       text NOT NULL,
            sha256                        text NOT NULL,
            size_bytes                    bigint NOT NULL,
            created_at                    timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_report_artifact_report
                FOREIGN KEY (comparison_report_id) REFERENCES comparison_report (comparison_report_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_report_artifact_blob
                FOREIGN KEY (blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT ck_comparison_report_artifact_id_format
                CHECK ({_id('comparison_report_artifact_id', 'cra')}),
            CONSTRAINT ck_comparison_report_artifact_report_id_format
                CHECK ({_id('comparison_report_id', 'crt')}),
            CONSTRAINT ck_comparison_report_artifact_blob_id_format CHECK ({_id('blob_id', 'blob')}),
            CONSTRAINT ck_comparison_report_artifact_kind CHECK (kind IN ({_sql_list(ARTIFACT_KINDS)})),
            CONSTRAINT ck_comparison_report_artifact_sha256 CHECK (sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_report_artifact_size CHECK (size_bytes >= 0)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_report_artifact_report ON comparison_report_artifact "
        "(comparison_report_id, kind, created_at);"
    )
    op.execute("CREATE INDEX ix_comparison_report_artifact_blob ON comparison_report_artifact (blob_id);")


def _launch() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_launch_queue (
            project_uid     text PRIMARY KEY,
            paused          boolean NOT NULL DEFAULT false,
            failure_reason  text NULL,
            created_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_launch_queue_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT ck_comparison_launch_queue_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_launch_queue_failure_reason CHECK (
                failure_reason IS NULL OR failure_reason ~ '^[a-z][a-z0-9_]{{2,63}}$')
        );
        """
    )
    op.execute(
        f"""
        CREATE TABLE comparison_launch_entry (
            comparison_launch_entry_id text PRIMARY KEY,
            project_uid                text NOT NULL,
            document_uid               text NOT NULL,
            step                       text NOT NULL,
            state                      text NOT NULL DEFAULT 'waiting',
            position                   integer NOT NULL,
            restart                    boolean NOT NULL DEFAULT false,
            reason                     text NULL,
            consent_digest             text NULL,
            comparison_ai_job_id       text NULL,
            comparison_series_id       text NULL,
            actor_user_uid             text NOT NULL,
            actor_label                text NOT NULL,
            command_id                 text NOT NULL,
            created_at                 timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                 timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_launch_entry_queue
                FOREIGN KEY (project_uid) REFERENCES comparison_launch_queue (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_launch_entry_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_launch_entry_job
                FOREIGN KEY (comparison_ai_job_id) REFERENCES comparison_ai_job (comparison_ai_job_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_launch_entry_series
                FOREIGN KEY (comparison_series_id) REFERENCES comparison_series (comparison_series_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_launch_entry_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_launch_entry_command UNIQUE (command_id, document_uid, step),
            CONSTRAINT ck_comparison_launch_entry_id_format
                CHECK ({_id('comparison_launch_entry_id', 'cle')}),
            CONSTRAINT ck_comparison_launch_entry_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_launch_entry_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_launch_entry_job_id_format
                CHECK ({_id('comparison_ai_job_id', 'cai', nullable=True)}),
            CONSTRAINT ck_comparison_launch_entry_series_id_format
                CHECK ({_id('comparison_series_id', 'cser', nullable=True)}),
            CONSTRAINT ck_comparison_launch_entry_actor_user_uid_format CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_launch_entry_command_id_format CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_comparison_launch_entry_step CHECK (step IN ({_sql_list(LAUNCH_STEPS)})),
            CONSTRAINT ck_comparison_launch_entry_state CHECK (state IN ({_sql_list(LAUNCH_STATES)})),
            CONSTRAINT ck_comparison_launch_entry_position CHECK (position >= 1),
            CONSTRAINT ck_comparison_launch_entry_reason
                CHECK (reason IS NULL OR reason ~ '^[a-z][a-z0-9_]{{2,63}}$'),
            CONSTRAINT ck_comparison_launch_entry_consent_digest
                CHECK (consent_digest IS NULL OR consent_digest ~ '{SHA256}'),
            CONSTRAINT ck_comparison_launch_entry_consent_is_ai CHECK (
                consent_digest IS NULL OR step IN ('ai_pairs', 'ai_changes', 'report')),
            CONSTRAINT ck_comparison_launch_entry_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n'))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_launch_entry_queue ON comparison_launch_entry (project_uid, position);"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_launch_entry_live ON comparison_launch_entry "
        f"(document_uid, step) WHERE state IN ({_sql_list(LAUNCH_LIVE)});"
    )
    op.execute("CREATE INDEX ix_comparison_launch_entry_document ON comparison_launch_entry (document_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_launch_entry_job ON comparison_launch_entry (comparison_ai_job_id) "
        "WHERE comparison_ai_job_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_launch_entry_series ON comparison_launch_entry (comparison_series_id) "
        "WHERE comparison_series_id IS NOT NULL;"
    )


def _alter_existing() -> None:
    op.execute("ALTER TABLE comparison_work ADD COLUMN comparison_ai_job_id text NULL")
    op.execute(
        "ALTER TABLE comparison_work ADD CONSTRAINT fk_comparison_work_ai_job "
        "FOREIGN KEY (comparison_ai_job_id) REFERENCES comparison_ai_job (comparison_ai_job_id) "
        "ON DELETE RESTRICT"
    )
    op.execute(
        "ALTER TABLE comparison_work ADD CONSTRAINT ck_comparison_work_ai_job_id_format "
        f"CHECK ({_id('comparison_ai_job_id', 'cai', nullable=True)})"
    )
    op.execute(
        "ALTER TABLE comparison_work ADD CONSTRAINT ck_comparison_work_ai_job_payload "
        "CHECK (comparison_ai_job_id IS NULL OR payload ->> 'ai_job_id' = comparison_ai_job_id)"
    )
    op.execute(
        "CREATE INDEX ix_comparison_work_ai_job ON comparison_work (comparison_ai_job_id) "
        "WHERE comparison_ai_job_id IS NOT NULL;"
    )
    _frozen("comparison_work", _WORK_FROZEN + ("comparison_ai_job_id",))
    op.execute("ALTER TABLE executor_route_event DROP CONSTRAINT ck_executor_route_work_kind")
    op.execute(
        "ALTER TABLE executor_route_event ADD CONSTRAINT ck_executor_route_work_kind "
        f"CHECK (work_kind IN ({_sql_list(WORK_KINDS_AFTER)}))"
    )


def _frozen(table: str, columns: Sequence[str]) -> None:
    op.execute(f"DROP TRIGGER trg_{table}_frozen_guard ON {table}")
    op.execute(
        f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({_sql_list(columns)})"
    )


def _guards() -> None:
    for table in (
        "comparison_ai_job", "comparison_ai_pair_question", "comparison_ai_sheet_item",
        "comparison_spec_comparison", "comparison_report", "comparison_launch_entry",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_state_edges BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_comparison_ai_state_edges()"
        )
    frozen = {
        "comparison_ai_job": (
            "comparison_ai_job_id", "project_uid", "document_uid", "method", "comparison_matrix_id",
            "comparison_series_id", "comparison_transition_id", "comparison_sheet_pair_id", "restart",
            "command_id", "created_at",
        ),
        "comparison_ai_pair_question": (
            "comparison_ai_pair_question_id", "comparison_ai_job_id", "project_uid", "document_uid",
            "comparison_matrix_id", "kind", "page_version_uid", "page_number", "version_uid", "created_at",
        ),
        "comparison_ai_sheet_item": (
            "comparison_ai_sheet_item_id", "comparison_ai_job_id", "project_uid",
            "comparison_sheet_pair_id", "created_at",
        ),
        "comparison_spec_comparison": (
            "comparison_spec_comparison_id", "project_uid", "document_uid", "comparison_transition_id",
            "source", "created_at",
        ),
        "comparison_report": (
            "comparison_report_id", "project_uid", "document_uid", "comparison_series_id", "kind",
            "source", "estimate_digest", "source_sha256", "prepared_from_report_id", "actor_user_uid",
            "actor_label", "command_id", "created_at",
        ),
        "comparison_report_part": (
            "comparison_report_part_id", "comparison_report_id", "comparison_transition_id", "created_at",
        ),
        "comparison_launch_queue": ("project_uid", "created_at"),
        "comparison_launch_entry": (
            "comparison_launch_entry_id", "project_uid", "document_uid", "step", "actor_user_uid",
            "actor_label", "command_id", "created_at",
        ),
    }
    for table, columns in frozen.items():
        op.execute(
            f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({_sql_list(columns)})"
        )
    op.execute(
        "CREATE TRIGGER trg_comparison_ai_job_consent BEFORE UPDATE ON comparison_ai_job "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_comparison_ai_job_consent()"
    )
    for table in (
        "comparison_ai_pair_answer", "comparison_sheet_description", "comparison_spec_extraction",
        "comparison_report_artifact",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    for table in (
        "comparison_ai_job", "comparison_ai_pair_question", "comparison_spec_comparison",
        "comparison_report", "comparison_launch_entry",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_document BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_check_comparison_core_document()"
        )
    inserts = {
        "comparison_ai_job": ("scope", "am_check_comparison_ai_job_scope"),
        "comparison_ai_pair_question": ("pages", "am_check_comparison_ai_pair_question"),
        "comparison_ai_sheet_item": ("pair", "am_check_comparison_ai_sheet_item"),
        "comparison_sheet_description": ("subject", "am_check_comparison_sheet_description"),
        "comparison_spec_extraction": ("version", "am_check_comparison_spec_extraction"),
        "comparison_spec_comparison": ("inputs", "am_check_comparison_spec_comparison"),
        "comparison_report": ("inputs", "am_check_comparison_report"),
        "comparison_report_part": ("transition", "am_check_comparison_report_part"),
    }
    for table, (suffix, function) in inserts.items():
        op.execute(
            f"CREATE TRIGGER trg_{table}_{suffix} BEFORE INSERT ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {function}()"
        )


def _comments() -> None:
    comments = {
        "comparison_ai_job": (
            "CMP-SEAL-C2. One consented AI job of the version comparison (ADR-0025 decision 19): the method, "
            "the scope, the estimate the user consented to with its digest, micro-USD figure and ceiling, the "
            "connection revision and the pinned model. The consent columns change only together and by one "
            "consent_no. The spend is the comparison journal read through comparison_work.comparison_ai_job_id."
        ),
        "comparison_ai_pair_answer": (
            "CMP-SEAL-C2. The content-keyed answer of the model to one question of the pair check (ADR-0025 "
            "decision 15): unique by (project_uid, content_key), so an answered question is never sent again "
            "within a project. Immutable; the digest is never a foreign key."
        ),
        "comparison_ai_pair_question": (
            "CMP-SEAL-C2. One question of a pair-check job for one matrix cell, its answers and the decision "
            "made of them. An accepted decision points at the comparison_ai_link it wrote; the raw matrix and "
            "the raw answers are never rewritten (AGENTS section 4)."
        ),
        "comparison_ai_sheet_item": (
            "CMP-SEAL-C2. One sheet pair of an AI description job with its state, calls, tokens and time."
        ),
        "comparison_sheet_description": (
            "CMP-SEAL-C2. The content-keyed AI description of one result or one single page, by content, "
            "prompt version and model (ADR-0025 decisions 15 and 20), unique by (project_uid, content_key). "
            "Immutable; the earlier descriptions of a sheet are its history."
        ),
        "comparison_spec_extraction": (
            "CMP-SEAL-C2. The content-keyed reading of the whole specification of one version, unique by "
            "(project_uid, content_key). Immutable."
        ),
        "comparison_spec_comparison": (
            "CMP-SEAL-C2. The comparison of the specifications of one transition: the deterministic positions "
            "(part A) or the AI whole comparison (part B), one row of each source per transition."
        ),
        "comparison_report": (
            "CMP-SEAL-C2. One PDF report of a series (ADR-0025 decisions 3 and 20): a draft carries its "
            "estimate, a started one its AI job. A deleted report is a tombstone; no published blob is deleted."
        ),
        "comparison_report_part": "CMP-SEAL-C2. The progress of one transition of a report.",
        "comparison_report_artifact": (
            "CMP-SEAL-C2. A stored file of a report (the PDF, the exact MD, the report text), append-only; a "
            "rebuild of the PDF adds a row."
        ),
        "comparison_launch_queue": (
            "CMP-SEAL-C2. The launch queue of a project: whether it is paused and why it stopped."
        ),
        "comparison_launch_entry": (
            "CMP-SEAL-C2. One selected step of one document set in the launch queue of a project; the queue runs "
            "one step at a time across sets."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}';")
    for table in ("comparison_ai_job", "comparison_report", "comparison_launch_entry"):
        op.execute(
            f"COMMENT ON COLUMN {table}.{'consented_by_user_uid' if table == 'comparison_ai_job' else 'actor_user_uid'} "
            "IS 'The account that acted. Deliberately not a foreign key: the register of account references "
            "belongs to the access context.';"
        )


def downgrade() -> None:
    """Refuse while data exists that exists nowhere else, otherwise drop this revision's own objects."""
    bind = op.get_bind()
    occupied = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in TABLES
    }
    occupied["comparison_work (ai job)"] = int(
        bind.execute(
            text("SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id IS NOT NULL")
        ).scalar_one()
    )
    occupied["executor_route_event (comparison work kind)"] = int(
        bind.execute(
            text(
                "SELECT count(*) FROM executor_route_event "
                f"WHERE work_kind NOT IN ({_sql_list(WORK_KINDS_BEFORE)})"
            )
        ).scalar_one()
    )
    if any(occupied.values()):
        rendered = ", ".join(f"{name}={count}" for name, count in occupied.items() if count)
        raise RuntimeError(
            f"0040 downgrade refused: comparison data exists nowhere else ({rendered}); "
            "restore a backup instead of downgrading"
        )
    op.execute("ALTER TABLE executor_route_event DROP CONSTRAINT ck_executor_route_work_kind")
    op.execute(
        "ALTER TABLE executor_route_event ADD CONSTRAINT ck_executor_route_work_kind "
        f"CHECK (work_kind IN ({_sql_list(WORK_KINDS_BEFORE)}))"
    )
    op.execute("DROP INDEX ix_comparison_work_ai_job")
    op.execute("ALTER TABLE comparison_work DROP CONSTRAINT ck_comparison_work_ai_job_payload")
    op.execute("ALTER TABLE comparison_work DROP CONSTRAINT ck_comparison_work_ai_job_id_format")
    op.execute("ALTER TABLE comparison_work DROP CONSTRAINT fk_comparison_work_ai_job")
    _frozen("comparison_work", _WORK_FROZEN)
    op.execute("ALTER TABLE comparison_work DROP COLUMN comparison_ai_job_id")
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in _FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
