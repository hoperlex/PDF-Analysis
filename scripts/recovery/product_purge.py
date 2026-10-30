"""STAND-PURGE-TOOL-01: remove a stand's product data and keep its accounts and its norm corpus.

The operator entry point is ``infra/deploy/purge-product-data.sh``; this module is the part that
runs inside the ``api`` image and talks to PostgreSQL and the bucket. It is an operator tool and
nothing in the product imports it. It is NOT a migration: the cancelled ``STAND-PURGE-0022-01``
baked a purge into a permanent revision (``D-194``) and that was rejected. This is run on purpose,
by a person, against one named stand, after a verified dump.

THE CLASSIFICATION IS CLOSED, AND IT IS BUILT ON ``schema_coverage``. Every base table of the
schema is exactly one of

* ``PRODUCT_TABLES``: truncated;
* ``KEEP_TABLES``: never written (accounts and everything account-side, release notes, lookup
  data and the whole ``norm*`` corpus -- the corpus half is :data:`schema_coverage.
  EXEMPT_FROM_FINGERPRINT`, reused, not retyped);
* ``MIXED_TABLES`` (``audit_event``, ``command_record``, ``blob``): rows are classified, product
  rows are deleted, keep rows stay.

A table in none of them stops the tool before it touches anything and is named. So does a
declaration that no longer equals :data:`schema_coverage.TABLES`: a migration that adds a table
is a decision about that table's fate, taken in two places on purpose.

WHAT "KEEP ROWS" MEANS IN THE THREE MIXED TABLES (``copy_record.py``'s frozen fingerprint is the
precedent: it excludes exactly these from the "client" rows):

* ``audit_event``: ``norm_custody.*`` events are the custody ledger's history, ``executor.*``
  events are the executor configuration's (who set a secret or a route, and when) and ``access.*``
  events are the account side's (who signed in, who was given or lost a role, whose password
  changed -- `PROD-06`, ADR-0023 section 4); all three stay. The run, job, attempt, provider and
  execution journal goes. An event type nobody classified stops the tool.
* ``command_record``: an idempotency receipt of a registration approval is account-side and stays;
  every receipt of a product command goes. A command type nobody classified stops the tool.
* ``blob``: a row any KEEP table references (a custody admission/binding, a retrieval set) stays,
  with its object, even if a product row references the same bytes too (a Blob is content-addressed
  and shared by design). Every other row goes, with its object.

HOW IT IS SAFE, in the order it acts: refusal guards (read-only) -> a plan whose SHA-256 the
shell script carries across the dump -> one transaction that locks, re-derives the plan, compares
it, truncates/deletes, re-reads every keep row's count and digest and rolls back on a difference
-> only after COMMIT, objects by exact key from the dumped list, never a prefix, never a key the
custody ledger owns. A failure after COMMIT leaves objects behind, never a half-deleted database.

GUARDS ARE DELIMITED BY ``# >>> guard: <name>`` / ``# <<< guard: <name>`` markers, the convention
of ``infra/deploy/reset.sh``: ``tests/integration/recovery/test_product_purge.py`` deletes ONE
guard block from a copy of this file and shows the copy no longer refuses. Do not remove a marker
without removing its test.

Exit codes: 0 done (or nothing to do), 2 usage, 3 REFUSED (nothing was changed), 4 FAILED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.config import load_settings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.storage.public import BlobId, S3StorageSettings, canonical_object_key_for_recovery
from scripts.recovery.blob_reference_audit import _CATALOG, _CATALOG_EXPECTED
from scripts.recovery.schema_coverage import EXEMPT_FROM_FINGERPRINT, TABLES, TRIGGERS, VIEWS

EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_FAILED = 0, 2, 3, 4

#: Accounts and everything account-side. The sign-in throttle is columns of ``app_user`` and
#: ``registration_request``; there is no table of its own.
KEEP_ACCOUNT_TABLES = frozenset((
    "account_release_mark", "app_user", "app_user_role", "registration_request",
))
#: The release notes the ``release-notes`` service loads.
KEEP_RELEASE_TABLES = frozenset(("release", "release_revision"))
#: Lookup data and control-plane state: the migration head, the state-machine transitions and
#: the queue's pause switch (an operator may have paused the queue before this window and must be
#: the one to resume it).
KEEP_LOOKUP_TABLES = frozenset(("alembic_version", "contract_state_transition", "execution_control"))
#: The whole normative corpus -- the exemption list of ``stand-fingerprint-v1``, reused.
KEEP_NORM_TABLES = EXEMPT_FROM_FINGERPRINT
#: `EXEC-SEAL-01` (R-143). Executor connections, revisions, sealed secrets, probes and route
#: events are configuration, like accounts: a purge of product data never touches them. They are
#: referenced by PRODUCT rows (a run, a call, an effect), never the other way round.
#: `EXEC-PULL-01`: the runner tokens are configuration too (the stand's credentials for its
#: runners, not product data); the tasks are the opposite -- they carry the stand's documents and
#: the model's answers, and reference runs, Attempts and calls -- so ``executor_task`` is PRODUCT.
#: `ANALYSIS-PRESETS-01` (`0037_analysis_presets`): a preset is a named choice of one of those
#: connections, kept with them. ``audit_run.preset_revision_id`` (PRODUCT) references it, never the
#: other way round.
KEEP_EXECUTOR_TABLES = frozenset((
    "analysis_preset_revision", "executor_connection", "executor_connection_revision",
    "executor_probe", "executor_route_event", "executor_runner_token", "executor_secret",
))
KEEP_TABLES = (
    KEEP_ACCOUNT_TABLES | KEEP_RELEASE_TABLES | KEEP_LOOKUP_TABLES | KEEP_NORM_TABLES
    | KEEP_EXECUTOR_TABLES
)

MIXED_TABLES = frozenset(("audit_event", "blob", "command_record"))

#: Truncated together, in one statement (they reference each other).
#: `0032_ar_v3_run_group`: a group of six runs of one version, with their pins and members.
#: ``ar_v3_run_group`` references the product ``project``, ``document_version`` and command
#: receipt; ``ar_v3_run_group_member`` references the group and ``audit_run``. Both are
#: immutable rows (``am_immutable_row``), so a row DELETE is refused by design: the one
#: multi-table TRUNCATE below is the only way out, and PostgreSQL refuses it unless a table and
#: every table that references it are named in the same statement.
PRODUCT_TABLES = frozenset((
    "analysis_artifact_publication", "ar_v3_run_group", "ar_v3_run_group_member", "attempt",
    "audit_run", "comparison_ai_job", "comparison_ai_link", "comparison_ai_pair_answer", "comparison_ai_pair_question",
    "comparison_ai_sheet_item", "comparison_launch_entry", "comparison_launch_queue", "comparison_matrix",
    "comparison_matrix_edit", "comparison_model_call", "comparison_report", "comparison_report_artifact",
    "comparison_report_part", "comparison_sheet_description", "comparison_spec_comparison", "comparison_spec_extraction",
    "comparison_page_profile", "comparison_series", "comparison_sheet_link", "comparison_sheet_pair",
    "comparison_sheet_pair_result", "comparison_transition",
    "comparison_summary", "comparison_upload", "comparison_upload_file", "comparison_upload_part",
    "comparison_upload_set", "comparison_version_order", "comparison_work",
    "comparison_work_attempt", "document", "document_version",
    # `0041_comparison_stage_core`: every stage row belongs to a product project.
    "stage_upload", "stage_upload_file", "stage_upload_part", "stage_upload_candidate",
    "stage_assembly", "stage_assembly_member", "stage_pair", "stage_link_revision",
    "stage_link_item", "stage_text_fragment", "stage_text_exclusion",
    "stage_text_difference", "stage_text_hint", "stage_chain_run", "stage_chain_step",
    "document_version_classification", "document_version_classification_correction",
    "executor_task", "expert_decision_event", "finding", "finding_evidence", "finding_observation",
    "finding_observation_norm_citation", "input_manifest_entry", "job", "lease", "model_call",
    "optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision",
    "price_list_position", "price_list_revision", "project", "provider_call_effect",
    "stage_result", "vendor_list_entry", "vendor_list_revision", "work_assignment",
    "work_assignment_event", "worker",
))

#: ``audit_event.event_type`` families. ``norm_custody.`` is the custody ledger's, ``executor.``
#: the append-only trail of who set an executor secret or route and when (`EXEC-SEAL-01`),
#: ``access.`` the account side's: sign-in, role grant and revoke, password change and reset
#: (`PROD-06`; kept "forever", ADR-0023 section 4), ``erasure.`` the record of a project erase
#: (`PROD-07a`, ADR-0022 section 3: who, when, what, hashes). Both the keep and the delete
#: predicate of ``audit_event`` are built from this tuple (``_event_keep``).
KEEP_EVENT_PREFIXES = ("norm_custody.", "executor.", "access.", "erasure.")
PRODUCT_EVENT_PREFIXES = (
    "artifact.", "attempt.", "audit_run.", "comparison.", "execution.", "findings.", "job.",
    "provider.", "stage.",
)
#: ``command_record.command_type``. A registration approval is account-side.
KEEP_COMMAND_TYPES = frozenset((
    "approve_registration",
    # `EXEC-SEAL-01`: the executor configuration commands, kept with the configuration.
    "archive_executor_connection", "create_executor_connection", "generate_executor_ssh_key",
    "request_executor_probe", "revise_executor_connection", "set_executor_route",
    "set_executor_secret",
    # `EXEC-PULL-01`: a runner token is issued and revoked as configuration.
    "issue_runner_token", "revoke_runner_token",
    # `ANALYSIS-PRESETS-01`: a preset is administered and kept like the connections it names.
    "archive_analysis_preset", "create_analysis_preset", "revise_analysis_preset",
))
PRODUCT_COMMAND_TYPES = frozenset((
    "append_decision", "approve_sheet_pairing", "cancel_audit_run", "carry_over_decision",
    "create_project", "generate_comparison_summary",
    "decide_optimisation_proposal", "reaudit_run", "set_execution_paused", "set_job_priority",
    "set_worker_intake",
    # `0032_ar_v3_run_group`: the receipt of a group start. ``ar_v3_run_group.command_id``
    # references it, and it is deleted only after the group is truncated.
    "start_ar_v3_beta_group",
    "start_audit_run", "start_optimisation_pass", "upload_price_list", "upload_source_document",
    # `0035_comparison_records`: the receipt of a withdrawal. ``comparison_sheet_link.command_id``
    # references it, and it is deleted only after the link table is truncated.
    "withdraw_sheet_pairing",
    # `0038_comparison_foundation` (`CMP-SEAL-C0`): the receipts of the ten keyed comparison writes, named
    # as the snake case of the operationId. ``comparison_upload.command_id`` and
    # ``comparison_version_order.command_id`` reference theirs, and each is deleted only after its table is
    # truncated. A lane that names a command type differently registers it here.
    "append_comparison_version_order", "cancel_comparison_upload", "complete_comparison_upload_file",
    "confirm_comparison_upload_set", "create_comparison_upload", "exclude_comparison_upload_set",
    "pause_comparison_upload", "resume_comparison_upload", "retry_comparison_upload_set",
    "upload_comparison_upload_part",
    # `0039_comparison_core` (`CMP-SEAL-C1`): the receipts of the eight keyed writes of the version comparison core,
    # named as the snake case of the operationId. ``comparison_matrix_edit.command_id`` and
    # ``comparison_series.command_id`` reference theirs.
    "apply_comparison_matrix_edits", "cancel_comparison_series", "finish_comparison_series",
    "pause_comparison_series", "prepare_comparison_matrix", "resume_comparison_series",
    "start_comparison_series", "undo_comparison_matrix_edit",
    # `0040_comparison_ai_reports` (`CMP-SEAL-C2`): the receipts of the twenty-seven keyed writes of the version comparison
    # AI, specifications, launch queue and reports, named as the snake case of the operationId.
    "start_comparison_ai_pair_check", "pause_comparison_ai_pair_check", "resume_comparison_ai_pair_check",
    "cancel_comparison_ai_pair_check", "start_comparison_ai_sheet_changes", "pause_comparison_ai_sheet_changes",
    "resume_comparison_ai_sheet_changes", "cancel_comparison_ai_sheet_changes",
    "finish_comparison_ai_sheet_changes", "dequeue_comparison_ai_sheet_changes",
    "retry_comparison_ai_sheet_changes", "start_comparison_sheet_description", "start_comparison_specification",
    "cancel_comparison_specification", "enqueue_comparison_launch", "pause_comparison_launch_queue",
    "resume_comparison_launch_queue", "clear_comparison_launch_queue", "remove_comparison_launch_entry",
    "create_comparison_report", "upload_comparison_report_source", "start_comparison_report",
    "cancel_comparison_report", "continue_comparison_report", "rebuild_comparison_report_pdf",
    "delete_comparison_report", "prepare_comparison_client_report",
    # `CMP-SEAL-C3`: the sixteen keyed stage commands use product receipts.
    "create_stage_upload", "upload_stage_upload_part", "complete_stage_upload_file",
    "confirm_stage_upload_candidate", "reject_stage_upload_candidate", "pause_stage_upload",
    "resume_stage_upload", "cancel_stage_upload", "confirm_stage_pair",
    "create_stage_assembly", "revise_stage_assembly", "set_stage_pair_completeness",
    "apply_stage_sheet_map", "recompute_stage_text_evidence", "start_stage_chain_run",
    "cancel_stage_chain_run",
    # Internal raw-multipart checkpoint of CMP-STAGE-PAIR-01. The public
    # complete_stage_upload_file receipt follows PDF/ZIP admission later.
    "stage_raw_completion",
))

#: Work that may be executing or resumed. The C3 upload and chain rows are kept from a
#: destructive purge until admission and execution have been stopped or cancelled.
RUNNING_STATES = {
    "audit_run": ("running", "validating"),
    "job": ("leased", "running"),
    "attempt": ("leased", "running"),
    "stage_upload": ("uploading", "admitting", "paused"),
    "stage_upload_file": ("declared", "receiving", "received", "admitting"),
    "stage_upload_candidate": ("confirmed", "admitting"),
    "stage_chain_run": ("queued", "running", "paused"),
    "stage_chain_step": ("queued", "running", "paused"),
}

TEMPORARY_KEY_PREFIX = "temporary/"
#: How long the transaction waits for its table locks. A test can shorten it; nothing else should.
LOCK_TIMEOUT = os.environ.get("PRODUCT_PURGE_LOCK_TIMEOUT", "15s")
_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*\Z")
_CANONICAL_KEY = re.compile(r"blobs/([0-9A-HJKMNP-TV-Z]{2})/([0-9A-HJKMNP-TV-Z]{2})/([0-9A-HJKMNP-TV-Z]{26})\Z")
_TEMPORARY_KEY = re.compile(r"temporary/[A-Za-z0-9._~-]{1,128}\Z")
_NOT_FOUND = frozenset(("404", "NoSuchKey", "NotFound"))
_SESSION = (
    "SET LOCAL TimeZone = 'UTC'", "SET LOCAL DateStyle = 'ISO, YMD'",
    "SET LOCAL IntervalStyle = 'postgres'", "SET LOCAL extra_float_digits = 1",
    "SET LOCAL bytea_output = 'hex'",
)


class PurgeRefused(Exception):
    """Nothing was changed, and the reason is in the message. Exit 3."""


class PurgeFailed(Exception):
    """Something broke; the message says what state that leaves. Exit 4."""


@dataclass(frozen=True, slots=True)
class PlanObject:
    key: str
    kind: str  # "canonical" | "temporary"
    ref: str  # the blob id or the upload token
    size: int | None  # None: the key is not in the bucket


@dataclass(frozen=True, slots=True)
class Plan:
    database: str
    bucket: str
    head: str
    product_counts: Mapping[str, int]
    product_digests: Mapping[str, tuple[int, str]]
    mixed: Mapping[str, Mapping[str, Any]]
    keep_counts: Mapping[str, int]
    objects: tuple[PlanObject, ...]
    norm_owned_present: int
    unaccounted: Mapping[str, int]
    unaccounted_total: int
    bucket_objects: int
    running: Mapping[str, int]
    queued: Mapping[str, int]
    database_bytes: int
    sha256: str

    @property
    def rows_to_delete(self) -> int:
        return sum(self.product_counts.values()) + sum(int(m["delete"]) for m in self.mixed.values())

    @property
    def objects_present(self) -> tuple[PlanObject, ...]:
        return tuple(o for o in self.objects if o.size is not None)

    @property
    def nothing_to_purge(self) -> bool:
        return self.rows_to_delete == 0 and not self.objects_present


def _identifier(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise PurgeFailed(f"{name!r} is not a plain identifier; a declared name must be")
    return f'public."{name}"'


def _tables_sql(names: Iterable[str]) -> str:
    return ", ".join(_identifier(name) for name in sorted(names))


# --- the classification -----------------------------------------------------------------------


def classification_problems() -> list[str]:
    """Self-consistency of the declaration alone (no database)."""
    problems = []
    groups = {"PRODUCT": PRODUCT_TABLES, "KEEP": KEEP_TABLES, "MIXED": MIXED_TABLES}
    names = sorted(groups)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            both = groups[left] & groups[right]
            if both:
                problems.append(f"{sorted(both)} are declared both {left} and {right}")
    declared = PRODUCT_TABLES | KEEP_TABLES | MIXED_TABLES
    if declared != TABLES:
        problems.append(
            "the purge declaration differs from schema_coverage.TABLES: "
            f"not classified={sorted(TABLES - declared)}, not in the schema={sorted(declared - TABLES)}"
        )
    return problems


def _relations(connection: Connection) -> tuple[set[str], set[str], list[str]]:
    rows = connection.execute(text("""
        SELECT n.nspname, c.relname, c.relkind::text
          FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
           AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
    """)).all()
    tables = {name for schema, name, kind in rows if schema == "public" and kind == "r"}
    views = {name for schema, name, kind in rows if schema == "public" and kind == "v"}
    strange = sorted(f"{schema}.{name} ({kind})" for schema, name, kind in rows
                     if schema != "public" or kind not in ("r", "v"))
    return tables, views, strange


def check_schema(connection: Connection) -> str:
    """Every refusal that needs only the catalog. Returns the migration head."""
    tables, views, strange = _relations(connection)
    declared = PRODUCT_TABLES | KEEP_TABLES | MIXED_TABLES

    # >>> guard: relations-recognised
    if strange:
        raise PurgeRefused(
            "the database holds a relation the purge does not understand "
            f"(outside schema public, or a partitioned/materialised/foreign table): {strange}"
        )
    # <<< guard: relations-recognised

    # >>> guard: classification-total
    unclassified = sorted(tables - declared)
    if unclassified:
        raise PurgeRefused(
            f"table(s) classified as neither PRODUCT, KEEP nor MIXED: {unclassified}. "
            "A new table is a decision about its fate (purge it or keep it) that has to be written "
            "into scripts/recovery/product_purge.py. Nothing was touched."
        )
    absent = sorted(declared - tables)
    if absent:
        raise PurgeRefused(
            f"declared table(s) missing from this database: {absent}. This is not the schema the "
            "tool was written for. Nothing was touched."
        )
    if views != VIEWS:
        raise PurgeRefused(
            f"views differ from schema_coverage.VIEWS: missing={sorted(VIEWS - views)}, "
            f"unknown={sorted(views - VIEWS)}. Nothing was touched."
        )
    # <<< guard: classification-total

    # >>> guard: declaration-matches-coverage
    problems = classification_problems()
    if problems:
        raise PurgeRefused("the purge declaration is inconsistent: " + "; ".join(problems))
    # <<< guard: declaration-matches-coverage

    # >>> guard: blob-columns-closed
    columns = {(schema, table, column) for schema, table, column in connection.execute(_CATALOG).all()}
    if columns != _CATALOG_EXPECTED:
        raise PurgeRefused(
            "the Blob-reference columns differ from blob_reference_audit's closed set: "
            f"missing={sorted(_CATALOG_EXPECTED - columns)}, unknown={sorted(columns - _CATALOG_EXPECTED)}. "
            "A new reference decides which Blobs are product and which are the corpus's."
        )
    # <<< guard: blob-columns-closed

    # >>> guard: keep-never-references-product
    references = connection.execute(text("""
        SELECT conrelid::regclass::text, confrelid::regclass::text
          FROM pg_catalog.pg_constraint WHERE contype = 'f'
    """)).all()
    bad = sorted((a, b) for a, b in references
                 if a.removeprefix("public.") in KEEP_TABLES | MIXED_TABLES
                 and b.removeprefix("public.") in PRODUCT_TABLES)
    if bad:
        raise PurgeRefused(
            f"a KEEP or MIXED table has a foreign key into a PRODUCT table: {bad}. Truncating the "
            "product table would need CASCADE, which this tool never uses."
        )
    # <<< guard: keep-never-references-product

    # >>> guard: no-truncate-guard-on-product
    guarded = connection.execute(text("""
        SELECT c.relname, t.tgname FROM pg_catalog.pg_trigger t
          JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
         WHERE NOT t.tgisinternal AND (t.tgtype::integer & 32) = 32 AND c.relname = ANY(:names)
    """), {"names": sorted(PRODUCT_TABLES)}).all()
    if guarded:
        raise PurgeRefused(
            f"a PRODUCT table carries a BEFORE TRUNCATE trigger: {sorted(tuple(r) for r in guarded)}. "
            "Someone decided that table must not be truncated; this tool does not disable a "
            "declared guard. (At the schema it was written for the only such triggers are on "
            "norm_current_snapshot and its event table, which are KEEP.)"
        )
    # <<< guard: no-truncate-guard-on-product

    # >>> guard: owner-may-write
    touched = sorted(PRODUCT_TABLES | MIXED_TABLES)
    foreign = connection.execute(text("""
        SELECT c.relname FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relname = ANY(:names)
           AND NOT pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
    """), {"names": touched}).scalars().all()
    if foreign:
        raise PurgeRefused(
            f"the connected role {_current_user(connection)!r} does not own: {sorted(foreign)}. "
            "TRUNCATE and the audit_event trigger switch need the owning role (the one the "
            "migrations run as), not a superuser mechanism."
        )
    # <<< guard: owner-may-write
    head = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
    if len(head) != 1:
        raise PurgeRefused(f"alembic_version holds {len(head)} rows, not one")
    return str(head[0])


def _current_user(connection: Connection) -> str:
    return str(connection.execute(text("SELECT current_user")).scalar_one())


def check_row_classes(connection: Connection) -> None:
    """Event types and command types: a value nobody classified is a refusal, not a guess."""
    # >>> guard: event-types-classified
    events = connection.execute(text("SELECT DISTINCT event_type FROM public.audit_event")).scalars().all()
    unknown = sorted(e for e in events if not e.startswith(KEEP_EVENT_PREFIXES + PRODUCT_EVENT_PREFIXES))
    if unknown:
        raise PurgeRefused(
            f"audit_event holds event type(s) nobody classified as product or keep: {unknown}. "
            "Classify them in scripts/recovery/product_purge.py. Nothing was touched."
        )
    # <<< guard: event-types-classified
    # >>> guard: command-types-classified
    commands = connection.execute(text("SELECT DISTINCT command_type FROM public.command_record")).scalars().all()
    unknown = sorted(c for c in commands if c not in KEEP_COMMAND_TYPES | PRODUCT_COMMAND_TYPES)
    if unknown:
        raise PurgeRefused(
            f"command_record holds command type(s) nobody classified as product or keep: {unknown}. "
            "Classify them in scripts/recovery/product_purge.py. Nothing was touched."
        )
    # <<< guard: command-types-classified


# --- digests ----------------------------------------------------------------------------------

def _event_keep() -> str:
    """The keep rows of ``audit_event``: every family of :data:`KEEP_EVENT_PREFIXES`, no other list."""
    return "(" + " OR ".join(f"starts_with(t.event_type, '{prefix}')" for prefix in KEEP_EVENT_PREFIXES) + ")"


def _command_keep() -> str:
    return "t.command_type IN (" + ", ".join(f"'{c}'" for c in sorted(KEEP_COMMAND_TYPES)) + ")"


def blob_columns(connection: Connection) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """``(KEEP-side, PRODUCT-side)`` Blob-reference ``(table, column)`` pairs, from the live catalog."""
    pairs = sorted((table, column) for schema, table, column in connection.execute(_CATALOG).all()
                   if (table, column) != ("blob", "blob_id"))
    keep = [pair for pair in pairs if pair[0] in KEEP_TABLES]
    product = [pair for pair in pairs if pair[0] in PRODUCT_TABLES]
    if len(keep) + len(product) != len(pairs):
        raise PurgeRefused("a Blob reference sits in a MIXED or unclassified table; nothing was touched")
    return keep, product


def _keep_blob_ids_sql(keep_pairs: Sequence[tuple[str, str]]) -> str:
    if not keep_pairs:
        return "SELECT NULL::text WHERE false"
    parts = []
    for table, column in keep_pairs:
        if not _IDENTIFIER.fullmatch(column):
            raise PurgeFailed(f"{column!r} is not a plain identifier")
        parts.append(f'SELECT "{column}" FROM {_identifier(table)} WHERE "{column}" IS NOT NULL')
    return " UNION ".join(parts)


def _predicates(keep_pairs: Sequence[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """``table -> (keep predicate, product predicate)`` for the three mixed tables."""
    keep_ids = _keep_blob_ids_sql(keep_pairs)
    return {
        "audit_event": (_event_keep(), f"NOT {_event_keep()}"),
        "command_record": (_command_keep(), f"NOT ({_command_keep()})"),
        "blob": (f"t.blob_id IN ({keep_ids})", f"t.blob_id NOT IN ({keep_ids})"),
    }


def fingerprint(connection: Connection, table: str, where: str = "true") -> tuple[int, str]:
    """``(exact row count, order-independent digest of the rows' text)``.

    The digest is the sum, as a ``numeric``, of the first 64 bits of each row's SHA-256: it is
    computed where the rows are, in one scan, with nothing shipped to the client, and it does not
    depend on row order or physical layout. It is a change detector, not a signature.
    """
    row = connection.execute(text(
        "SELECT count(*)::bigint, coalesce(sum(('x' || encode(substring("
        "sha256(convert_to(t::text, 'UTF8')) from 1 for 8), 'hex'))::bit(64)::bigint::numeric), 0)::text "
        f"FROM {_identifier(table)} AS t WHERE {where}"
    )).one()
    return int(row[0]), str(row[1])


def keep_fingerprints(connection: Connection, keep_pairs: Sequence[tuple[str, str]]) -> dict[str, tuple[int, str]]:
    """Every KEEP table whole, and the keep rows of each MIXED table."""
    result = {table: fingerprint(connection, table) for table in sorted(KEEP_TABLES)}
    for table, (keep, _) in _predicates(keep_pairs).items():
        result[f"{table}[keep rows]"] = fingerprint(connection, table, keep)
    return result


def _trigger_state(connection: Connection) -> list[tuple[str, str, str]]:
    return [tuple(row) for row in connection.execute(text("""
        SELECT tgrelid::regclass::text, tgname, tgenabled::text
          FROM pg_catalog.pg_trigger WHERE NOT tgisinternal ORDER BY 1, 2
    """)).all()]


# --- the bucket -------------------------------------------------------------------------------


def s3_client(settings: S3StorageSettings) -> Any:
    return boto3.client(
        "s3", endpoint_url=settings.endpoint_url, region_name=settings.region,
        aws_access_key_id=settings.access_key_id, aws_secret_access_key=settings.secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=settings.connect_timeout_seconds,
                      read_timeout=settings.read_timeout_seconds,
                      retries={"max_attempts": 3, "mode": "standard"}),
    )


def _head(client: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if str(error.response.get("Error", {}).get("Code")) in _NOT_FOUND:
            return None
        raise


def require_unversioned_bucket(client: Any, bucket: str) -> None:
    """A delete in a versioned bucket only adds a delete marker; the bytes would stay."""
    versioning = client.get_bucket_versioning(Bucket=bucket)
    # >>> guard: bucket-unversioned
    if versioning.get("Status") in ("Enabled", "Suspended"):
        raise PurgeRefused(
            f"bucket {bucket!r} is versioned ({versioning.get('Status')}): deleting a key would only add a "
            "delete marker and leave every byte in place. An all-versions cleanup is a different tool. "
            "Nothing was touched."
        )
    # <<< guard: bucket-unversioned


def _list_bucket(client: Any, bucket: str) -> dict[str, int]:
    """Every key with its size. Pages of 1000; the stand's bucket is ~29,000 keys."""
    found: dict[str, int] = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            found[item["Key"]] = int(item["Size"])
    return found


def canonical_key(blob_id: str) -> str:
    return canonical_object_key_for_recovery(BlobId(blob_id))


def temporary_key(token: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._~-]{1,128}", token):
        raise PurgeRefused("an upload token is not a plain token; nothing was touched")
    return f"{TEMPORARY_KEY_PREFIX}{token}"


# --- the plan ---------------------------------------------------------------------------------


def _count_all(connection: Connection) -> dict[str, int]:
    return {table: int(connection.execute(text(f"SELECT count(*) FROM {_identifier(table)}")).scalar_one())
            for table in sorted(PRODUCT_TABLES | KEEP_TABLES | MIXED_TABLES)}


def _wanted_objects(connection: Connection, keep_pairs: Sequence[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """``(key, kind, ref)`` of every object the product rows own. Derived from rows, never a listing."""
    keep_ids = _keep_blob_ids_sql(keep_pairs)
    wanted = [
        (canonical_key(blob_id), "canonical", blob_id)
        for blob_id in connection.execute(text(
            f"SELECT blob_id FROM public.blob t WHERE t.blob_id NOT IN ({keep_ids}) ORDER BY blob_id"
        )).scalars()
    ]
    wanted += [
        (temporary_key(token), "temporary", token)
        for token in connection.execute(text(
            "SELECT DISTINCT upload_token FROM public.analysis_artifact_publication ORDER BY 1"
        )).scalars()
    ]
    return sorted(wanted)


def norm_owned_keys(connection: Connection, keep_pairs: Sequence[tuple[str, str]]) -> set[str]:
    """The keys of every Blob a KEEP table references (the custody ledger's objects and kin)."""
    return {canonical_key(blob_id)
            for blob_id in connection.execute(text(_keep_blob_ids_sql(keep_pairs))).scalars()}


def _plan_digest(product: Mapping[str, tuple[int, str]], doomed: Mapping[str, tuple[int, str]],
                 keys: Sequence[tuple[str, str, str]]) -> str:
    document = {
        "product": {table: list(value) for table, value in sorted(product.items())},
        "mixed_delete": {table: list(value) for table, value in sorted(doomed.items())},
        "keys": [list(key) for key in keys],
    }
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_plan(connection: Connection, client: Any | None, *, database: str, bucket: str,
               allow_running: bool) -> Plan:
    """Everything that can be decided without writing. Raises :class:`PurgeRefused`.

    ``client=None`` skips the bucket listing (sizes stay unknown): the transaction re-derives the
    plan under its locks and must not hold them across ~30 listing requests.
    """
    for statement in _SESSION:
        connection.execute(text(statement))
    head = check_schema(connection)
    check_row_classes(connection)

    running = {}
    for table, states in RUNNING_STATES.items():
        count = connection.execute(text(f"SELECT count(*) FROM {_identifier(table)} WHERE state = ANY(:s)"),
                                   {"s": list(states)}).scalar_one()
        if count:
            running[table] = int(count)
    # >>> guard: quiescent
    if running and not allow_running:
        raise PurgeRefused(
            f"work is running right now: {running}. Let it finish or stop the worker; "
            "--allow-running overrides this and discards the rows from under a running worker."
        )
    # <<< guard: quiescent
    queued = {
        "audit_run": int(connection.execute(text(
            "SELECT count(*) FROM public.audit_run WHERE state IN ('created', 'queued')")).scalar_one()),
        "job": int(connection.execute(text(
            "SELECT count(*) FROM public.job WHERE state IN ('queued', 'retry_wait')")).scalar_one()),
    }

    keep_pairs, _ = blob_columns(connection)
    counts = _count_all(connection)
    product_digests = {table: fingerprint(connection, table) for table in sorted(PRODUCT_TABLES)}
    predicates = _predicates(keep_pairs)
    mixed: dict[str, dict[str, Any]] = {}
    doomed: dict[str, tuple[int, str]] = {}
    for table, (keep, product) in predicates.items():
        doomed[table] = fingerprint(connection, table, product)
        mixed[table] = {"delete": doomed[table][0], "keep": fingerprint(connection, table, keep)[0]}
    keys = _wanted_objects(connection, keep_pairs)
    norm_keys = norm_owned_keys(connection, keep_pairs)

    # >>> guard: norm-key-not-in-product-list
    shared = sorted({key for key, _, _ in keys} & norm_keys)
    if shared:
        raise PurgeRefused(f"a product object key is owned by the norm custody ledger: {shared[:5]}")
    # <<< guard: norm-key-not-in-product-list

    if client is not None:
        require_unversioned_bucket(client, bucket)
    listing = _list_bucket(client, bucket) if client is not None else {}
    objects = tuple(PlanObject(key, kind, ref, listing.get(key)) for key, kind, ref in keys)
    accounted = {key for key, _, _ in keys} | norm_keys
    stray = {key: size for key, size in listing.items() if key not in accounted}
    by_prefix: dict[str, int] = {}
    for key in stray:
        prefix = key.split("/", 1)[0] + "/" if "/" in key else "(no prefix)"
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
    size = int(connection.execute(text("SELECT pg_database_size(current_database())")).scalar_one())
    keep_counts = {table: counts[table] for table in sorted(KEEP_TABLES)}
    return Plan(
        database=database, bucket=bucket, head=head,
        product_counts={table: counts[table] for table in sorted(PRODUCT_TABLES)},
        product_digests=product_digests, mixed=mixed, keep_counts=keep_counts, objects=objects,
        norm_owned_present=sum(1 for key in norm_keys if key in listing),
        unaccounted=dict(sorted(by_prefix.items())), unaccounted_total=len(stray),
        bucket_objects=len(listing), running=running, queued=queued, database_bytes=size,
        sha256=_plan_digest(product_digests, doomed, keys),
    )


def render_plan(plan: Plan, *, dry_run: bool) -> str:
    out = [f"purge-product-data: database {plan.database} (migration head {plan.head}), bucket {plan.bucket}"]
    out.append("")
    out.append("-- PRODUCT tables: every row goes (TRUNCATE) --")
    for table, count in plan.product_counts.items():
        out.append(f"  {table}  ({count} rows)")
    out.append(f"  total: {sum(plan.product_counts.values())} rows in {len(plan.product_counts)} tables")
    out.append("")
    out.append("-- MIXED tables: product rows go, keep rows stay --")
    for table, info in plan.mixed.items():
        out.append(f"  {table}  (delete {info['delete']} rows, keep {info['keep']} rows)")
    out.append("")
    out.append("-- KEEP tables: never written --")
    for table, count in plan.keep_counts.items():
        out.append(f"  {table}  ({count} rows)")
    out.append(f"  total: {sum(plan.keep_counts.values())} rows in {len(plan.keep_counts)} tables")
    out.append("")
    present = plan.objects_present
    out.append("-- objects in the bucket --")
    out.append(f"  product objects to delete, by exact key: {len(present)} objects, "
               f"{sum(o.size or 0 for o in present)} bytes "
               f"({len(plan.objects) - len(present)} more keys are named by rows but not in the bucket)")
    out.append(f"  norm-owned objects (the custody ledger's, never touched): {plan.norm_owned_present}")
    stray = ", ".join(f"{prefix} {count}" for prefix, count in plan.unaccounted.items()) or "none"
    out.append(f"  other objects (named by no row; never touched): {plan.unaccounted_total} ({stray})")
    out.append(f"  objects in the bucket: {plan.bucket_objects}")
    out.append("")
    out.append("-- work in flight --")
    out.append(f"  running now: {dict(plan.running) or 'nothing'}"
               f"{'  (--allow-running given)' if plan.running else ''}")
    out.append(f"  queued, discarded with the rest: {plan.queued['audit_run']} runs, {plan.queued['job']} jobs")
    out.append("")
    if plan.nothing_to_purge:
        out.append("nothing to purge: every product table is empty and no product object is in the bucket.")
    elif dry_run:
        out.append("--dry-run: NOTHING ABOVE WAS CHANGED.")
    out.append(f"nothing-to-purge: {'yes' if plan.nothing_to_purge else 'no'}")
    out.append(f"database-bytes: {plan.database_bytes}")
    out.append(f"product-object-bytes: {sum(o.size or 0 for o in present)}")
    out.append(f"plan-sha256: {plan.sha256}")
    return "\n".join(out)


# --- the object half of the dump --------------------------------------------------------------


def _attr_fields(key: str, head: Mapping[str, Any]) -> list[str] | None:
    """The six ``objects.attrs`` fields ``reset.sh --restore`` reads, or ``None`` if one is missing."""
    meta = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
    fields = [key, meta.get("blob-id", ""), meta.get("blob-role", ""), meta.get("content-sha256", ""),
              meta.get("content-size", ""), head.get("ContentType", "")]
    return fields if all(fields) and not any("\t" in f or "\n" in f for f in fields) else None


def snapshot_objects(plan: Plan, client: Any, directory: Path) -> tuple[str, int, int]:
    """Copy every present product object into ``directory`` the way ``reset.sh`` dumps them.

    ``directory/objects/<key>`` holds the bytes, ``objects.attrs`` the six attributes per object
    ``reset.sh --restore`` re-attaches, ``product-objects.tsv`` the key list the deletion reads.
    Returns ``(sha256 of the key list, objects, bytes)``.
    """
    root = directory / "objects"
    root.mkdir(parents=True, exist_ok=True)
    attrs: list[str] = []
    rows: list[str] = []
    total = 0
    for item in plan.objects:
        if item.size is None:
            rows.append("\t".join((item.key, "-", item.kind, item.ref, "-", "absent")))
            continue
        response = client.get_object(Bucket=plan.bucket, Key=item.key)
        target = root / item.key
        target.parent.mkdir(parents=True, exist_ok=True)
        digest, size = hashlib.sha256(), 0
        with target.open("wb") as out:
            for chunk in response["Body"].iter_chunks(1024 * 1024):
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        recorded = {k.lower(): v for k, v in (response.get("Metadata") or {}).items()}.get("content-sha256")

        # >>> guard: mirror-bytes-match
        if size != item.size or (recorded is not None and recorded != digest.hexdigest()):
            raise PurgeRefused(
                f"the copy of {item.key} does not match the object ({size} bytes, sha256 "
                f"{digest.hexdigest()[:12]}; recorded {recorded and recorded[:12]}). Nothing was deleted."
            )
        # <<< guard: mirror-bytes-match
        fields = _attr_fields(item.key, response)
        if fields is not None:
            attrs.append("\t".join(fields))
        rows.append("\t".join((item.key, str(size), item.kind, item.ref, digest.hexdigest(),
                               "yes" if fields is not None else "no")))
        total += size
    (directory / "objects.attrs").write_text("".join(f"{r}\n" for r in attrs), encoding="utf-8")
    listing = "".join(f"{row}\n" for row in rows).encode("utf-8")
    (directory / "product-objects.tsv").write_bytes(listing)

    mirrored = [p for p in root.rglob("*") if p.is_file()]
    # >>> guard: mirror-complete
    if len(mirrored) != len(plan.objects_present) or sum(p.stat().st_size for p in mirrored) != total:
        raise PurgeRefused("the object mirror is not complete; nothing was deleted")
    # <<< guard: mirror-complete
    for path in [directory / "objects.attrs", directory / "product-objects.tsv", *root.rglob("*")]:
        os.chmod(path, 0o755 if path.is_dir() else 0o644)
    return hashlib.sha256(listing).hexdigest(), len(mirrored), total


def read_object_list(path: Path, expected_sha256: str | None) -> list[PlanObject]:
    """The dumped key list, parsed strictly. Anything that is not exactly an object key is refused."""
    raw = path.read_bytes()

    # >>> guard: object-list-intact
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise PurgeRefused(f"{path} is not the key list that was dumped (SHA-256 differs); nothing was deleted")
    # <<< guard: object-list-intact
    objects = []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        fields = line.split("\t")
        if len(fields) != 6:
            raise PurgeRefused(f"{path} line {number} does not have six fields; nothing was deleted")
        key, size, kind, ref = fields[:4]

        # >>> guard: key-shape
        if kind == "canonical":
            ok = (re.fullmatch(r"blob_[0-9A-HJKMNP-TV-Z]{26}", ref) is not None
                  and _CANONICAL_KEY.fullmatch(key) is not None and key == canonical_key(ref))
        else:
            ok = (kind == "temporary" and _TEMPORARY_KEY.fullmatch(key) is not None
                  and key == temporary_key(ref))
        if not ok:
            raise PurgeRefused(f"{path} line {number}: {key!r} is not exactly the key of {kind} {ref!r}; "
                               "this tool deletes exact keys it can derive, never a pattern")
        # <<< guard: key-shape
        objects.append(PlanObject(key, kind, ref, None if size == "-" else int(size)))
    return objects


def delete_objects(engine: Engine, client: Any, *, bucket: str, objects: Sequence[PlanObject]) -> dict[str, int]:
    """After COMMIT: delete the listed keys, each by its exact name."""
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        keep_pairs, _ = blob_columns(connection)
        owned = norm_owned_keys(connection, keep_pairs)
        canonical_refs = [o.ref for o in objects if o.kind == "canonical"]
        still = set(connection.execute(
            text("SELECT blob_id FROM public.blob WHERE blob_id = ANY(:ids)"), {"ids": canonical_refs}).scalars())
        tokens = [o.ref for o in objects if o.kind == "temporary"]
        pending = set(connection.execute(
            text("SELECT upload_token FROM public.analysis_artifact_publication WHERE upload_token = ANY(:t)"),
            {"t": tokens}).scalars())

    # >>> guard: norm-owned-key
    owned_hit = sorted(o.key for o in objects if o.key in owned)
    if owned_hit:
        raise PurgeRefused(f"the list names key(s) the norm custody ledger owns: {owned_hit[:5]}. "
                           "Nothing was deleted.")
    # <<< guard: norm-owned-key
    # >>> guard: row-gone
    alive = sorted(o.key for o in objects if (o.kind == "canonical" and o.ref in still)
                   or (o.kind == "temporary" and o.ref in pending))
    if alive:
        raise PurgeRefused(f"a row still (or again) names key(s) from the list: {alive[:5]}. "
                           "The list no longer describes a purged database; nothing was deleted.")
    # <<< guard: row-gone
    require_unversioned_bucket(client, bucket)
    result = {"deleted": 0, "already_absent": 0, "failed": 0, "bytes": 0}
    problems = []
    for item in objects:
        try:
            head = _head(client, bucket, item.key)
            if head is None:
                result["already_absent"] += 1
                continue
            client.delete_object(Bucket=bucket, Key=item.key)
            if _head(client, bucket, item.key) is not None:
                raise PurgeFailed(f"{item.key} is still in the bucket after its delete")
            result["deleted"] += 1
            result["bytes"] += int(head["ContentLength"])
        except (ClientError, PurgeFailed) as error:
            result["failed"] += 1
            problems.append(f"{item.key}: {error}")
    if problems:
        raise PurgeFailed(f"{len(problems)} object(s) could not be deleted (the database part is done): "
                          + "; ".join(problems[:5]))
    return result


# --- the transaction --------------------------------------------------------------------------


def apply_purge(engine: Engine, *, database: str, bucket: str, expected_plan: str,
                objects_file: Path | None, allow_running: bool) -> dict[str, Any]:
    """ONE transaction. Any exception, including a keep-row mismatch, rolls all of it back."""
    with engine.begin() as connection:
        for statement in _SESSION:
            connection.execute(text(statement))

        try:
            connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
            keep_pairs, _ = blob_columns(connection)
            connection.execute(text("LOCK TABLE " + _tables_sql(KEEP_TABLES) + " IN SHARE MODE"))
            connection.execute(text("LOCK TABLE " + _tables_sql(PRODUCT_TABLES | MIXED_TABLES)
                                    + " IN ACCESS EXCLUSIVE MODE"))
        except DBAPIError as error:
            # >>> guard: lock-available
            if getattr(error.orig, "sqlstate", "") == "55P03":
                raise PurgeRefused(f"could not lock the tables within {LOCK_TIMEOUT}: something is still "
                                   "writing. Stop api/web/worker and run it again; nothing was changed.") from error
            # <<< guard: lock-available
            raise

        # The plan again, under the locks: nothing can change from here to COMMIT.
        plan = build_plan(connection, None, database=database, bucket=bucket, allow_running=allow_running)

        # >>> guard: plan-unchanged
        if plan.sha256 != expected_plan:
            raise PurgeRefused(
                "the product data changed since the plan the dump was taken for "
                f"(plan {plan.sha256[:12]}, expected {expected_plan[:12]}). The dump is stale; "
                "nothing was changed. Stop the writers and run it again."
            )
        # <<< guard: plan-unchanged
        if objects_file is not None:
            listed = {(o.key, o.kind, o.ref) for o in read_object_list(objects_file, None)}
            derived = {(o.key, o.kind, o.ref) for o in plan.objects}

            # >>> guard: object-list-matches-plan
            if listed != derived:
                raise PurgeRefused("the dumped key list is not the key list of this plan; nothing was changed")
            # <<< guard: object-list-matches-plan

        keep_before = keep_fingerprints(connection, keep_pairs)
        triggers_before = _trigger_state(connection)
        head_before = plan.head
        before = _count_all(connection)

        predicates = _predicates(keep_pairs)
        append_only = [name for table, name, function, _ in TRIGGERS
                       if table == "audit_event" and function == "am_append_only"]
        if len(append_only) != 1:
            raise PurgeFailed("schema_coverage.TRIGGERS names no single append-only trigger on audit_event")
        trigger = append_only[0]
        # audit_event is append-only by trigger: switching that ONE named trigger off needs the
        # table's owner, not a superuser, and the switch is transactional -- a rollback restores it.
        connection.execute(text(f"ALTER TABLE public.audit_event DISABLE TRIGGER {trigger}"))
        connection.execute(text(f"DELETE FROM public.audit_event AS t WHERE {predicates['audit_event'][1]}"))
        connection.execute(text(f"ALTER TABLE public.audit_event ENABLE TRIGGER {trigger}"))
        connection.execute(text("TRUNCATE TABLE " + _tables_sql(PRODUCT_TABLES)))
        connection.execute(text(f"DELETE FROM public.command_record AS t WHERE {predicates['command_record'][1]}"))
        connection.execute(text(f"DELETE FROM public.blob AS t WHERE {predicates['blob'][1]}"))

        after = _count_all(connection)
        keep_after = keep_fingerprints(connection, keep_pairs)

        # >>> guard: keep-unchanged
        changed = sorted(table for table in keep_before if keep_before[table] != keep_after[table])
        if changed:
            raise PurgeRefused(f"the purge would have changed KEEP data in {changed}; rolled back, nothing changed")
        # <<< guard: keep-unchanged
        # >>> guard: product-emptied
        left = sorted(table for table in PRODUCT_TABLES if after[table])
        if left:
            raise PurgeRefused(f"PRODUCT table(s) still hold rows after the purge: {left}; rolled back")
        mixed_left = {table: after[table] - keep_after[f"{table}[keep rows]"][0] for table in MIXED_TABLES}
        if any(mixed_left.values()):
            raise PurgeRefused(f"MIXED table(s) hold product rows after the purge: {mixed_left}; rolled back")
        # <<< guard: product-emptied
        # >>> guard: triggers-restored
        if _trigger_state(connection) != triggers_before:
            raise PurgeRefused("a trigger's state differs after the purge; rolled back")
        if str(connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()) != head_before:
            raise PurgeRefused("alembic_version changed; rolled back")
        # <<< guard: triggers-restored
    return {"before": before, "after": after, "keep": keep_after, "plan": plan}


def render_applied(result: Mapping[str, Any]) -> str:
    before, after = result["before"], result["after"]
    out = ["purge-product-data: committed. Row counts per table (before -> after):"]
    for table in sorted(before):
        kind = "PRODUCT" if table in PRODUCT_TABLES else "MIXED  " if table in MIXED_TABLES else "KEEP   "
        out.append(f"  {kind} {table}  {before[table]} -> {after[table]}")
    out.append(f"  KEEP tables and keep rows verified unchanged inside the transaction: "
               f"{len(result['keep'])} fingerprints equal")
    return "\n".join(out)


# --- the command line -------------------------------------------------------------------------


def _no_ambient_libpq() -> None:
    """``PGHOSTADDR`` beats the host in ``DATABASE_URL``; ``PGSERVICE`` can supply anything else.

    The cancelled cleanup branch (``task/prod-project-cleanup``) found this by reading libpq: the
    URL is the only target this tool may have. Inside the ``api`` container nothing sets these.
    """
    ambient = sorted(name for name in os.environ if name.startswith("PG"))
    # >>> guard: no-ambient-libpq
    if ambient:
        raise PurgeRefused(f"libpq environment variable(s) {ambient} can redirect the connection that "
                           "DATABASE_URL names. Unset them; DATABASE_URL is the only target. Nothing was touched.")
    # <<< guard: no-ambient-libpq


def _typed_names(engine: Engine, s3: S3StorageSettings, database: str, bucket: str) -> None:
    with engine.connect() as connection:
        actual = str(connection.execute(text("SELECT current_database()")).scalar_one())
    # >>> guard: names-match
    if actual != database or s3.bucket != bucket:
        raise PurgeRefused(
            f"the typed names are not the connected ones: database {database!r} vs {actual!r}, "
            f"bucket {bucket!r} vs {s3.bucket!r}. Nothing was touched."
        )
    # <<< guard: names-match


def _read_only_plan(engine: Engine, client: Any, database: str, bucket: str, allow_running: bool) -> Plan:
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        return build_plan(connection, client, database=database, bucket=bucket, allow_running=allow_running)


def run(argv: Sequence[str] | None = None, *, out: Any = None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog="product_purge", description=__doc__.split("\n", 1)[0])
    parser.add_argument("command", choices=("plan", "snapshot-objects", "apply", "delete-objects"))
    parser.add_argument("--database", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--allow-running", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="plan: say that nothing was changed")
    parser.add_argument("--dump-dir", type=Path, help="snapshot-objects: where the object half goes")
    parser.add_argument("--objects-file", type=Path, help="apply, delete-objects: the dumped key list")
    parser.add_argument("--objects-sha256", help="delete-objects: SHA-256 of the key list as dumped")
    parser.add_argument("--expect-plan", help="apply: the plan digest the dump was taken for")
    args = parser.parse_args(argv)
    if args.command == "snapshot-objects" and args.dump_dir is None:
        parser.error("snapshot-objects needs --dump-dir")
    if args.command == "apply" and not args.expect_plan:
        parser.error("apply needs --expect-plan")
    if args.command == "delete-objects" and (args.objects_file is None or not args.objects_sha256):
        parser.error("delete-objects needs --objects-file and --objects-sha256")
    engine: Engine | None = None
    try:
        _no_ambient_libpq()
        s3 = S3StorageSettings.from_env()
        engine = create_database_engine(load_settings())
        _typed_names(engine, s3, args.database, args.bucket)
        client = s3_client(s3)
        if args.command == "plan":
            plan = _read_only_plan(engine, client, args.database, args.bucket, args.allow_running)
            print(render_plan(plan, dry_run=args.dry_run), file=out)
        elif args.command == "snapshot-objects":
            plan = _read_only_plan(engine, client, args.database, args.bucket, args.allow_running)
            digest, count, size = snapshot_objects(plan, client, args.dump_dir)
            print(f"snapshot-objects: {count} objects, {size} bytes copied to {args.dump_dir}/objects", file=out)
            print(f"plan-sha256: {plan.sha256}", file=out)
            print(f"objects-sha256: {digest}", file=out)
        elif args.command == "apply":
            result = apply_purge(engine, database=args.database, bucket=args.bucket,
                                 expected_plan=args.expect_plan, objects_file=args.objects_file,
                                 allow_running=args.allow_running)
            print(render_applied(result), file=out)
        else:
            objects = read_object_list(args.objects_file, args.objects_sha256)
            summary = delete_objects(engine, client, bucket=args.bucket, objects=objects)
            print("purge-product-data: objects deleted by exact key: "
                  f"{summary['deleted']} deleted ({summary['bytes']} bytes), "
                  f"{summary['already_absent']} already absent", file=out)
        return EXIT_OK
    except PurgeRefused as error:
        print(f"product_purge: REFUSED: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except PurgeFailed as error:
        print(f"product_purge: FAILED: {error}", file=sys.stderr)
        return EXIT_FAILED
    except Exception as error:  # noqa: BLE001 - the operator needs a status, not a traceback
        print(f"product_purge: FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_FAILED
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(run())
