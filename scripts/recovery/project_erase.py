"""PROD-07A-PROJECT-ERASE-CORE-01: erase ONE project, as ADR-0022 section 3 defines it.

The operator entry point will be ``infra/deploy/erase-project.sh`` (a later lane, after the
database-role work); this module is the part that runs inside the ``api`` image and talks to
PostgreSQL and the bucket. It is an operator tool and nothing in the product imports it. It is
modelled on ``product_purge.py`` and reuses its classification instead of retyping it.

WHAT IT REMOVES (``R-146c``, ``R-146o``; ``ADR-0012`` addendum). Every row reachable from
``project`` by foreign key, found by a FOREIGN-KEY CLOSURE read from the catalog and not by a hand
list: documents, versions, pages' manifest entries, findings, evidence quotes, expert decisions
and comments, runs, jobs, attempts, model-call records, artifacts, classification, work
assignments, price and vendor lists of the project, optimisation passes -- together with the
idempotency receipts (``command_record``) of those rows and every Blob that no other project and
no KEEP table references, with its object. ``worker``, the global vendor list, accounts, the norm
corpus and the executor configuration are not project-scoped and stay.

WHAT STAYS. Accounts, release notes, executor configuration, the norm corpus; every other
project; the identity-only run journal (``audit_event`` rows of the project's runs); and the
record of the erasure itself: the ``erasure.requested`` and ``erasure.completed`` events and the
manifest of the erased Blobs. A Blob still referenced elsewhere stays with its object.

THE ONE PLACE THE APPEND-ONLY CONTRACT IS OVERRIDDEN (``R-146o``). ``expert_decision_event`` is
append-only and ``document_version``, ``finding_observation`` and others are immutable by trigger.
The erase switches ONE NAMED trigger off at a time, inside the transaction, deletes, switches it
on again and compares the whole trigger state before and after. Only the table owner can do it.

FOUR PHASES (the object deletion is an external side effect, so it is not a dual write):

1. ``plan``: read-only, always first. Guards, per-table row counts and digests of the project's
   rows, the Blob list classified exclusive or shared, the object keys, a SHA-256 over the
   canonical form of all that. Nothing is journalled and nothing is written.
2. ``commit``: ONE transaction. Lock, re-derive the plan and compare its digest, append
   ``erasure.requested``, move every exclusive Blob to ``erasure_pending``, delete the project's
   rows, verify that every row outside the project is unchanged by count and digest and that
   every trigger is restored, write the plan and manifest files, commit.
3. ``objects``: delete each exclusive Blob's object by exact key (an absent key counts as done).
4. ``finish``: ONE transaction. Delete the ``erasure_pending`` Blob rows, append
   ``erasure.completed`` with the manifest digest.

A crash after phase 2 leaves Blobs in ``erasure_pending`` and nothing referencing them;
``--resume era_<ULID>`` completes phases 3 and 4. Running a finished apply again finds the
``erasure.completed`` event of the project and exits 0 with "nothing to do".

``R-146aj``: by the owner's ruling an operator never erases a project without the owner's
permission. The tool cannot verify a permission; it REFUSES to apply or resume without an explicit
``--owner-permission-ref`` and records the text in both events.

GUARDS ARE DELIMITED BY ``# >>> guard: <name>`` / ``# <<< guard: <name>`` markers, the convention of
``product_purge.py``: ``tests/integration/recovery/test_project_erase.py`` deletes ONE guard block
from a copy of this file and shows the copy no longer refuses. Do not remove a marker without
removing its test.

USAGE (``DATABASE_URL`` is the owner role's -- the migrator's; ``S3_*`` as the application's; no ``PG*`` variable):

    python -m scripts.recovery.project_erase --database D --bucket B --project prj_...            # dry run
    python -m scripts.recovery.project_erase --database D --bucket B --project prj_... --apply \
        --plan-sha256 <digest the dry run printed> --actor <admin login> --reason client_request \
        --owner-permission-ref "<where the owner's permission is recorded>" --dump-dir DIR
    python -m scripts.recovery.project_erase --database D --bucket B --resume era_... \
        --actor <admin login> --owner-permission-ref "<...>" --dump-dir DIR

The dry run needs no permission reference: it is how the operator obtains the plan to show the owner.
``DIR/<era_id>/plan.json`` and ``manifest.json`` are written before the commit that makes them the only
record; the operator keeps them with the release record (the database holds only their digests).

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

from botocore.exceptions import ClientError
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.config import load_settings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AuditEventId, ErasureRequestId
from auditmanager.storage.public import S3StorageSettings
from scripts.recovery import product_purge as purge
from scripts.recovery.blob_reference_audit import _CATALOG, _CATALOG_EXPECTED
from scripts.recovery.schema_coverage import HEAD, VIEWS

EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_FAILED = 0, 2, 3, 4

ROOT_TABLE = "project"
#: PRODUCT tables that no project owns: they are not in the closure and an erase never writes them.
UNSCOPED_PRODUCT_TABLES = frozenset(("worker",))
#: The tables whose rows the tool writes besides the closure.
MIXED_TOUCHED = ("audit_event", "blob", "command_record")
#: The closed list of reasons. Free text is refused because it would put personal data into an
#: append-only table (ADR-0022 section 3).
REASON_CODES = ("client_request", "end_of_engagement", "test_data", "other")
EVENT_REQUESTED = "erasure.requested"
EVENT_COMPLETED = "erasure.completed"
EVENT_AGGREGATE = "ErasureRequest"
#: The only trigger functions the erase may switch off, one named trigger at a time.
DELETE_GUARD_FUNCTIONS = frozenset(("am_immutable_row", "am_append_only"))
#: A run, job, attempt or executor task in one of these states is work in flight (``D-215``: a
#: claimed remote task counts). Derived from ``ck_*_terminal_at`` and ``ck_executor_task_state`` by
#: ``tests/integration/recovery/test_project_erase.py``, which fails when a migration moves them.
NON_TERMINAL_STATES = {
    "audit_run": ("created", "queued", "running", "validating"),
    "job": ("queued", "leased", "running", "retry_wait"),
    "attempt": ("created", "leased", "running"),
    "executor_task": ("open", "claimed"),
    # `0038_comparison_foundation` (ADR-0025 decision 7): comparison work in flight. A paused item
    # and an item awaiting an explicit «Повторить» after a possible paid call (``spend_unknown``) are
    # in flight too: an operator cancels them before erasing the project.
    "comparison_work": ("queued", "leased", "running", "retry_wait", "paused", "spend_unknown"),
    "comparison_work_attempt": ("created", "leased", "running"),
}
#: The lock name of "another erase is running".
ADVISORY_LOCK_NAME = "auditmanager.project_erase"
#: How long the transaction waits for its table locks. A test can shorten it; nothing else should.
LOCK_TIMEOUT = os.environ.get("PROJECT_ERASE_LOCK_TIMEOUT", "15s")
PLAN_FILE_VERSION = 1
PERMISSION_REF_MAX = 200

_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*\Z")
_PROJECT_UID = re.compile(r"prj_[0-9A-HJKMNP-TV-Z]{26}\Z")
_ERASE_ID = re.compile(r"era_[0-9A-HJKMNP-TV-Z]{26}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_BLOB_ID = re.compile(r"blob_[0-9A-HJKMNP-TV-Z]{26}\Z")
_NOT_FOUND = frozenset(("404", "NoSuchKey", "NotFound"))
_SESSION = (
    "SET LOCAL TimeZone = 'UTC'", "SET LOCAL DateStyle = 'ISO, YMD'",
    "SET LOCAL IntervalStyle = 'postgres'", "SET LOCAL extra_float_digits = 1",
    "SET LOCAL bytea_output = 'hex'",
)
_KEYS = "CAST(:keys AS text[])"

NOT_REACHED = (
    "manual dumps, mirrors and copies on the host (infra/deploy/dumps/, the copy directory), the copy fetched "
    "to the development host, the VPS provider's snapshots and any copy outside the host: remove or age them by "
    "hand and record that in the release record",
    "the model provider and anything OpenRouter routed the text to, and the local copies of a remote executor",
    "the disk blocks of a deleted object (there is no secure wipe), container logs and exports a user already "
    "downloaded",
    "the legal-hold question (R-146aj: the owner's permission is the only ground; it is recorded, not verified)",
)


class EraseRefused(Exception):
    """Nothing was changed, and the reason is in the message. Exit 3."""


class EraseFailed(Exception):
    """Something broke; the message says what state that leaves. Exit 4."""


# --- values -----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ForeignKey:
    name: str
    child: str
    parent: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Closure:
    """The tables a project's rows can be in, with the keys that join them (read from the catalog)."""

    tables: tuple[str, ...]
    primary_keys: Mapping[str, tuple[str, ...]]
    edges: tuple[ForeignKey, ...]  # both ends inside the closure
    direct: Mapping[str, tuple[str, ...]]  # table -> its column(s) that reference project
    receipt_edges: tuple[ForeignKey, ...]  # closure table -> command_record


@dataclass(frozen=True, slots=True)
class BlobFact:
    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str
    state: str


@dataclass(frozen=True, slots=True)
class PlanObject:
    key: str
    kind: str  # "canonical" | "temporary"
    ref: str  # the blob id or the upload token
    size: int | None  # None: not looked up, or the key is not in the bucket


@dataclass(frozen=True, slots=True)
class Plan:
    database: str
    bucket: str
    head: str
    project_uid: str
    scope: Mapping[str, tuple[str, ...]]
    table_facts: Mapping[str, tuple[int, str]]
    receipts: tuple[str, ...]
    receipt_fact: tuple[int, str]
    exclusive: tuple[BlobFact, ...]
    shared: tuple[str, ...]
    objects: tuple[PlanObject, ...]
    journal_events: int
    sha256: str
    closure: Closure

    @property
    def rows_to_delete(self) -> int:
        return sum(count for count, _ in self.table_facts.values()) + len(self.receipts)

    @property
    def objects_present(self) -> tuple[PlanObject, ...]:
        return tuple(o for o in self.objects if o.size is not None)


@dataclass(frozen=True, slots=True)
class Committed:
    """What phase 2 leaves for phases 3 and 4."""

    erase_id: str
    project_uid: str
    plan_sha256: str
    manifest_sha256: str
    blob_ids: tuple[str, ...]
    objects: tuple[PlanObject, ...]
    rows_deleted: int
    blobs_shared: int
    actor_uid: str
    reason: str
    permission_ref: str
    directory: Path


# --- small pure helpers -----------------------------------------------------------------------


def _identifier(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise EraseFailed(f"{name!r} is not a plain identifier; a name read from the catalog must be")
    return f'public."{name}"'


def _column(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise EraseFailed(f"{name!r} is not a plain identifier; a name read from the catalog must be")
    return f'"{name}"'


def _tables_sql(names: Iterable[str]) -> str:
    return ", ".join(_identifier(name) for name in sorted(names))


def node_sql(alias: str, primary_key: Sequence[str]) -> str:
    """The text identity of a row: its primary key, joined with the unit separator when composite."""
    parts = [f"{alias}.{_column(column)}::text" for column in primary_key]
    return parts[0] if len(parts) == 1 else "concat_ws(chr(31), " + ", ".join(parts) + ")"


def canonical_json(document: Any) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def deletion_order(tables: Iterable[str], edges: Iterable[tuple[str, str]]) -> list[tuple[str, ...]]:
    """Groups of tables in an order where every group is deleted after every group that references it.

    ``edges`` are ``(child, parent)`` pairs: the child's foreign key points at the parent. Tables
    that reference each other (``document`` and ``document_version``, ``job`` and ``attempt``,
    ``finding`` and ``finding_observation``) form one group, deleted in one statement. The order is
    deterministic: ties are broken by table name.
    """
    nodes = sorted(set(tables))
    refers: dict[str, set[str]] = {node: set() for node in nodes}
    for child, parent in edges:
        if child in refers and parent in refers and child != parent:
            refers[child].add(parent)

    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []
    counter = [0]

    def visit(node: str) -> None:
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for other in sorted(refers[node]):
            if other not in index:
                visit(other)
                low[node] = min(low[node], low[other])
            elif other in on_stack:
                low[node] = min(low[node], index[other])
        if low[node] == index[node]:
            members = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                members.append(member)
                if member == node:
                    break
            components.append(tuple(sorted(members)))

    for node in nodes:
        if node not in index:
            visit(node)

    owner = {member: component for component in components for member in component}
    blocked_by: dict[tuple[str, ...], set[tuple[str, ...]]] = {component: set() for component in components}
    for node in nodes:
        for other in refers[node]:
            if owner[node] != owner[other]:
                # `other` (the parent) must wait for `node` (the child)
                blocked_by[owner[other]].add(owner[node])
    ordered: list[tuple[str, ...]] = []
    remaining = dict(blocked_by)
    while remaining:
        ready = sorted(component for component, waits in remaining.items() if not waits)
        if not ready:
            raise EraseFailed("the foreign keys of the closure have no deletion order")
        for component in ready:
            ordered.append(component)
            del remaining[component]
        for waits in remaining.values():
            waits.difference_update(ready)
    return ordered


def manifest_bytes(erase_id: str, project_uid: str, blobs: Sequence[BlobFact]) -> bytes:
    """The manifest of the erased Blobs: byte-deterministic, so ``sha256sum`` of the file is the event's digest."""
    document = {
        "blobs": [
            {"blob_id": b.blob_id, "media_type": b.media_type, "sha256": b.sha256, "size_bytes": b.size_bytes}
            for b in sorted(blobs, key=lambda blob: blob.blob_id)
        ],
        "erase_id": erase_id,
        "project_uid": project_uid,
        "version": PLAN_FILE_VERSION,
    }
    return (canonical_json(document) + "\n").encode("utf-8")


def plan_document(head: str, project_uid: str, table_facts: Mapping[str, tuple[int, str]],
                  receipt_fact: tuple[int, str], exclusive: Sequence[BlobFact], shared: Sequence[str],
                  objects: Sequence[PlanObject]) -> dict[str, Any]:
    """The canonical form the plan digest is taken over: nothing about who, why or when."""
    return {
        "blobs": {
            "exclusive": [[b.blob_id, b.sha256, b.size_bytes, b.media_type]
                          for b in sorted(exclusive, key=lambda blob: blob.blob_id)],
            "shared": sorted(shared),
        },
        "objects": [[o.key, o.kind, o.ref] for o in sorted(objects, key=lambda obj: obj.key)],
        "project_uid": project_uid,
        "receipts": list(receipt_fact),
        "schema_head": head,
        "tables": {table: list(fact) for table, fact in sorted(table_facts.items())},
        "version": PLAN_FILE_VERSION,
    }


def plan_digest(document: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(document))


def atomic_write(path: Path, data: bytes) -> None:
    """Write, flush to disk, rename: a reader sees the whole file or none."""
    temporary = path.with_name(path.name + ".part")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


# --- the catalog ------------------------------------------------------------------------------


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


def foreign_keys(connection: Connection) -> list[ForeignKey]:
    rows = connection.execute(text("""
        SELECT con.conname, child.relname, parent.relname,
               (SELECT array_agg(a.attname ORDER BY k.ord)
                  FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)
                  JOIN pg_catalog.pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum),
               (SELECT array_agg(a.attname ORDER BY k.ord)
                  FROM unnest(con.confkey) WITH ORDINALITY AS k(attnum, ord)
                  JOIN pg_catalog.pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.attnum)
          FROM pg_catalog.pg_constraint con
          JOIN pg_catalog.pg_class child ON child.oid = con.conrelid
          JOIN pg_catalog.pg_class parent ON parent.oid = con.confrelid
         WHERE con.contype = 'f' AND child.relnamespace = 'public'::regnamespace
           AND parent.relnamespace = 'public'::regnamespace
         ORDER BY child.relname, con.conname
    """)).all()
    return [ForeignKey(name, child, parent, tuple(child_columns), tuple(parent_columns))
            for name, child, parent, child_columns, parent_columns in rows]


def primary_keys(connection: Connection) -> dict[str, tuple[str, ...]]:
    rows = connection.execute(text("""
        SELECT rel.relname,
               (SELECT array_agg(a.attname ORDER BY k.ord)
                  FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)
                  JOIN pg_catalog.pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum)
          FROM pg_catalog.pg_constraint con JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
         WHERE con.contype = 'p' AND rel.relnamespace = 'public'::regnamespace
    """)).all()
    return {table: tuple(columns) for table, columns in rows}


def load_closure(connection: Connection) -> Closure:
    """The foreign-key closure from ``project``: every table that can hold a row of a project."""
    keys = foreign_keys(connection)
    members = {ROOT_TABLE}
    grown = True
    while grown:
        grown = False
        for key in keys:
            if key.parent in members and key.child not in members:
                members.add(key.child)
                grown = True
    pks = primary_keys(connection)
    missing = sorted(table for table in members if table not in pks)
    if missing:
        raise EraseFailed(f"table(s) without a primary key cannot be addressed row by row: {missing}")
    direct = {key.child: key.child_columns for key in keys if key.parent == ROOT_TABLE and key.child in members}
    return Closure(
        tables=tuple(sorted(members)),
        primary_keys={table: pks[table] for table in sorted(members)},
        edges=tuple(key for key in keys if key.child in members and key.parent in members),
        direct=direct,
        receipt_edges=tuple(key for key in keys if key.child in members and key.parent == "command_record"),
    )


def _current_user(connection: Connection) -> str:
    return str(connection.execute(text("SELECT current_user")).scalar_one())


def _delete_triggers(connection: Connection, tables: Iterable[str]) -> list[tuple[str, str, str]]:
    """``(table, trigger, function)`` of every user trigger that fires on DELETE of those tables."""
    return [tuple(row) for row in connection.execute(text("""
        SELECT c.relname, t.tgname, p.proname
          FROM pg_catalog.pg_trigger t
          JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
          JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
         WHERE NOT t.tgisinternal AND (t.tgtype::integer & 8) = 8
           AND c.relnamespace = 'public'::regnamespace AND c.relname = ANY(:names)
         ORDER BY 1, 2
    """), {"names": sorted(tables)}).all()]


def blob_reference_columns(connection: Connection, closure: Closure) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """``(KEEP-side, project-side)`` Blob-reference ``(table, column)`` pairs, from the live catalog."""
    pairs = sorted((table, column) for _, table, column in connection.execute(_CATALOG).all()
                   if (table, column) != ("blob", "blob_id"))
    keep = [pair for pair in pairs if pair[0] in purge.KEEP_TABLES]
    project = [pair for pair in pairs if pair[0] in closure.tables]
    return keep, project


def check_schema(connection: Connection) -> tuple[str, Closure]:
    """Every refusal that needs only the catalog. Returns the migration head and the closure."""
    tables, views, strange = _relations(connection)
    declared = purge.PRODUCT_TABLES | purge.KEEP_TABLES | purge.MIXED_TABLES

    # >>> guard: relations-recognised
    if strange:
        raise EraseRefused(
            "the database holds a relation the erase does not understand "
            f"(outside schema public, or a partitioned/materialised/foreign table): {strange}"
        )
    # <<< guard: relations-recognised

    # >>> guard: classification-total
    unclassified = sorted(tables - declared)
    if unclassified:
        raise EraseRefused(
            f"table(s) classified as neither PRODUCT, KEEP nor MIXED: {unclassified}. A new table is a decision "
            "about its fate (erase it with the project or keep it) that has to be written into "
            "scripts/recovery/product_purge.py. Nothing was touched."
        )
    absent = sorted(declared - tables)
    if absent:
        raise EraseRefused(
            f"declared table(s) missing from this database: {absent}. This is not the schema the tool was "
            "written for. Nothing was touched."
        )
    if views != VIEWS:
        raise EraseRefused(
            f"views differ from schema_coverage.VIEWS: missing={sorted(VIEWS - views)}, "
            f"unknown={sorted(views - VIEWS)}. Nothing was touched."
        )
    # <<< guard: classification-total

    # >>> guard: declaration-matches-coverage
    problems = purge.classification_problems()
    if problems:
        raise EraseRefused("the classification is inconsistent: " + "; ".join(problems))
    # <<< guard: declaration-matches-coverage

    # >>> guard: blob-columns-closed
    columns = {(schema, table, column) for schema, table, column in connection.execute(_CATALOG).all()}
    if columns != _CATALOG_EXPECTED:
        raise EraseRefused(
            "the Blob-reference columns differ from blob_reference_audit's closed set: "
            f"missing={sorted(_CATALOG_EXPECTED - columns)}, unknown={sorted(columns - _CATALOG_EXPECTED)}. "
            "A new reference decides which Blobs a project owns."
        )
    # <<< guard: blob-columns-closed

    closure = load_closure(connection)

    # >>> guard: closure-is-product
    outside = sorted(set(closure.tables) - purge.PRODUCT_TABLES)
    unscoped = sorted((purge.PRODUCT_TABLES - set(closure.tables)) - UNSCOPED_PRODUCT_TABLES)
    if outside or unscoped:
        raise EraseRefused(
            f"the foreign-key closure from {ROOT_TABLE} is not the product tables the tool knows: "
            f"KEEP or MIXED table(s) that reference a project's rows: {outside}; PRODUCT table(s) that are in "
            f"neither the closure nor the declared unscoped set {sorted(UNSCOPED_PRODUCT_TABLES)}: {unscoped}. "
            "A migration that adds a table is a decision about that table (D-213). Nothing was touched."
        )
    # <<< guard: closure-is-product

    # >>> guard: blob-refs-in-closure
    pairs = sorted((table, column) for _, table, column in connection.execute(_CATALOG).all()
                   if (table, column) != ("blob", "blob_id"))
    stray = [pair for pair in pairs if pair[0] not in purge.KEEP_TABLES and pair[0] not in closure.tables]
    if stray:
        raise EraseRefused(
            f"a Blob reference sits in a table that is neither KEEP nor in the project closure: {stray}. "
            "Nothing was touched."
        )
    # <<< guard: blob-refs-in-closure

    # >>> guard: delete-triggers-known
    unknown_triggers = [(table, name, function)
                        for table, name, function in _delete_triggers(connection, closure.tables)
                        if function not in DELETE_GUARD_FUNCTIONS]
    if unknown_triggers:
        raise EraseRefused(
            f"a table of the closure carries a DELETE trigger the erase does not know how to switch off: "
            f"{unknown_triggers}. Someone decided that row must not be deleted; this tool switches off only "
            f"{sorted(DELETE_GUARD_FUNCTIONS)}. Nothing was touched."
        )
    # <<< guard: delete-triggers-known

    # >>> guard: owner-may-write
    touched = sorted(set(closure.tables) | set(MIXED_TOUCHED))
    foreign = connection.execute(text("""
        SELECT c.relname FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relname = ANY(:names)
           AND NOT pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
    """), {"names": touched}).scalars().all()
    if foreign:
        raise EraseRefused(
            f"the connected role {_current_user(connection)!r} does not own: {sorted(foreign)}. "
            "Switching a table's guard trigger off needs the owning role (the one the migrations run as, "
            "the migrator), not the application's role."
        )
    # <<< guard: owner-may-write
    head = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
    if len(head) != 1:
        raise EraseRefused(f"alembic_version holds {len(head)} rows, not one")
    # >>> guard: head-is-declared
    if str(head[0]) != HEAD:
        raise EraseRefused(
            f"the database is at migration {head[0]}, the tool was written for {HEAD} (schema_coverage.HEAD). "
            "A migration is a decision about what an erase must reach; extend the declaration first. "
            "Nothing was touched."
        )
    # <<< guard: head-is-declared
    return str(head[0]), closure


# --- the scope --------------------------------------------------------------------------------


def _edge_selects(closure: Closure) -> list[str]:
    selects = []
    for key in closure.edges:
        child_pk, parent_pk = closure.primary_keys[key.child], closure.primary_keys[key.parent]
        on = " AND ".join(f"c.{_column(a)} = p.{_column(b)}"
                          for a, b in zip(key.child_columns, key.parent_columns, strict=True))
        selects.append(
            f"SELECT '{key.child}'::text AS ct, {node_sql('c', child_pk)} AS ck, "
            f"'{key.parent}'::text AS pt, {node_sql('p', parent_pk)} AS pk "
            f"FROM {_identifier(key.child)} c JOIN {_identifier(key.parent)} p ON {on}"
        )
    return selects


def derive_scope(connection: Connection, closure: Closure, project_uid: str) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, str]]]:
    """``(scope, outside)``: the project's rows per table, and the parents they reference outside it.

    One recursive query over the foreign keys of the closure: a row is in the project when ANY of
    its foreign keys points at a row that is. ``outside`` lists the rows of the closure that a row
    of the project references and that are not in it (a global vendor list; a row of another
    project would be a cross-project reference, which the caller refuses).
    """
    root_key = node_sql("r", closure.primary_keys[ROOT_TABLE])
    statement = (
        "WITH RECURSIVE edges AS MATERIALIZED (" + " UNION ALL ".join(_edge_selects(closure)) + "), "
        "scope(t, k) AS ("
        f"SELECT '{ROOT_TABLE}'::text, {root_key} FROM {_identifier(ROOT_TABLE)} r WHERE {root_key} = :project "
        "UNION SELECT e.ct, e.ck FROM edges e JOIN scope s ON e.pt = s.t AND e.pk = s.k), "
        "outside AS (SELECT DISTINCT e.pt, e.pk FROM edges e JOIN scope c ON c.t = e.ct AND c.k = e.ck "
        "LEFT JOIN scope p ON p.t = e.pt AND p.k = e.pk WHERE p.k IS NULL) "
        "SELECT 'scope', t, k FROM scope UNION ALL SELECT 'outside', pt, pk FROM outside"
    )
    scope: dict[str, list[str]] = {table: [] for table in closure.tables}
    outside: list[tuple[str, str]] = []
    for kind, table, key in connection.execute(text(statement), {"project": project_uid}).all():
        if kind == "scope":
            scope[table].append(key)
        else:
            outside.append((table, key))
    return ({table: tuple(sorted(keys)) for table, keys in scope.items()}, sorted(outside))


def _in_scope(closure: Closure, table: str, alias: str = "t") -> str:
    return f"{node_sql(alias, closure.primary_keys[table])} = ANY({_KEYS})"


def fingerprint(connection: Connection, table: str, where: str = "true",
                parameters: Mapping[str, Any] | None = None) -> tuple[int, str]:
    """``(exact row count, order-independent digest of the rows' text)``, computed where the rows are.

    The digest is the sum, as a ``numeric``, of the first 64 bits of each row's SHA-256. It is a
    change detector, not a signature, and no row text leaves the database.
    """
    row = connection.execute(text(
        "SELECT count(*)::bigint, coalesce(sum(('x' || encode(substring("
        "sha256(convert_to(t::text, 'UTF8')) from 1 for 8), 'hex'))::bit(64)::bigint::numeric), 0)::text "
        f"FROM {_identifier(table)} AS t WHERE {where}"
    ), dict(parameters or {})).one()
    return int(row[0]), str(row[1])


def _scoped_fingerprint(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]],
                        table: str) -> tuple[int, str]:
    return fingerprint(connection, table, _in_scope(closure, table), {"keys": list(scope[table])})


# --- the receipts and the Blobs ---------------------------------------------------------------


def derive_receipts(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    """The idempotency receipts of the project's rows.

    A receipt is the project's when a row of the project references it by foreign key (a run's
    ``command_id``), or when its outcome names the identity of a row of the project (a
    ``create_project`` receipt names the project, an upload receipt the version, a decision
    receipt the decision).
    """
    receipts: set[str] = set()
    for key in closure.receipt_edges:
        column = _column(key.child_columns[0])
        receipts |= set(connection.execute(text(
            f"SELECT DISTINCT t.{column} FROM {_identifier(key.child)} t "
            f"WHERE {_in_scope(closure, key.child)} AND t.{column} IS NOT NULL"
        ), {"keys": list(scope[key.child])}).scalars())
    identities = sorted({value for table in closure.tables if len(closure.primary_keys[table]) == 1
                         for value in scope[table]})
    if identities:
        receipts |= set(connection.execute(text("""
            SELECT c.command_id FROM public.command_record c
             WHERE c.outcome IS NOT NULL AND EXISTS (
                   SELECT 1 FROM jsonb_path_query(c.outcome, 'strict $.** ? (@.type() == "string")') AS v
                    WHERE (v #>> '{}') = ANY(CAST(:ids AS text[])))
        """), {"ids": identities}).scalars())
    return tuple(sorted(receipts))


def check_receipts(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]],
                   receipts: Sequence[str]) -> None:
    if not receipts:
        return
    # >>> guard: receipts-are-product-commands
    kinds = sorted(set(connection.execute(text(
        "SELECT DISTINCT command_type FROM public.command_record WHERE command_id = ANY(CAST(:ids AS text[]))"
    ), {"ids": list(receipts)}).scalars()))
    odd = [kind for kind in kinds if kind not in purge.PRODUCT_COMMAND_TYPES]
    if odd:
        raise EraseRefused(
            f"the project's receipts include command type(s) that are not product commands: {odd}. "
            "A receipt of the account or executor side is never erased with a project. Nothing was touched."
        )
    # <<< guard: receipts-are-product-commands
    # >>> guard: receipts-not-shared
    shared = []
    for key in closure.receipt_edges:
        column = _column(key.child_columns[0])
        count = connection.execute(text(
            f"SELECT count(*) FROM {_identifier(key.child)} t WHERE t.{column} = ANY(CAST(:ids AS text[])) "
            f"AND NOT ({_in_scope(closure, key.child)})"
        ), {"ids": list(receipts), "keys": list(scope[key.child])}).scalar_one()
        if count:
            shared.append((key.child, int(count)))
    if shared:
        raise EraseRefused(
            f"a receipt of the project is also referenced by rows outside it: {shared}. Nothing was touched."
        )
    # <<< guard: receipts-not-shared


def _blob_id_sql(pairs: Sequence[tuple[str, str]], closure: Closure, *, inside: bool) -> str:
    """Blob ids referenced by rows inside (or outside) the project; parameters ``:k_<table>``."""
    if not pairs:
        return "SELECT NULL::text WHERE false"
    parts = []
    for table, column in pairs:
        predicate = _in_scope(closure, table).replace(":keys", f":k_{table}")
        parts.append(f"SELECT t.{_column(column)} AS blob_id FROM {_identifier(table)} t "
                     f"WHERE t.{_column(column)} IS NOT NULL AND {'' if inside else 'NOT '}({predicate})")
    return " UNION ".join(parts)


def classify_blobs(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]],
                   ) -> tuple[list[BlobFact], list[str], set[str]]:
    """``(exclusive, shared, keep_ids)``: the project's Blobs by who else references them."""
    keep_pairs, project_pairs = blob_reference_columns(connection, closure)
    parameters = {f"k_{table}": list(scope[table]) for table, _ in project_pairs}
    candidates = set(connection.execute(text(_blob_id_sql(project_pairs, closure, inside=True)), parameters).scalars())
    elsewhere = set(connection.execute(text(_blob_id_sql(project_pairs, closure, inside=False)), parameters).scalars())
    keep_ids = set(connection.execute(text(purge._keep_blob_ids_sql(keep_pairs))).scalars())
    shared = sorted(candidates & (elsewhere | keep_ids))
    exclusive_ids = sorted(candidates - set(shared))  # Python order, not the collation's
    facts = sorted((BlobFact(*row) for row in connection.execute(text(
        "SELECT blob_id, coalesce(sha256, ''), coalesce(size_bytes, -1), coalesce(media_type, ''), state "
        "FROM public.blob WHERE blob_id = ANY(CAST(:ids AS text[]))"
    ), {"ids": exclusive_ids}).all()), key=lambda fact: fact.blob_id)
    if len(facts) != len(exclusive_ids):
        raise EraseFailed("a Blob id is referenced by a row of the project but has no blob row")
    return facts, shared, keep_ids


# --- the bucket -------------------------------------------------------------------------------


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
        raise EraseRefused(
            f"bucket {bucket!r} is versioned ({versioning.get('Status')}): deleting a key would only add a "
            "delete marker and leave every byte in place. Nothing was touched."
        )
    # <<< guard: bucket-unversioned


def check_object_keys(objects: Sequence[PlanObject], keep_ids: Iterable[str]) -> None:
    owned = {purge.canonical_key(blob_id) for blob_id in keep_ids}
    # >>> guard: norm-owned-key
    hit = sorted(o.key for o in objects if o.key in owned)
    if hit:
        raise EraseRefused(f"the erase list names key(s) the norm custody ledger owns: {hit[:5]}. Nothing was deleted.")
    # <<< guard: norm-owned-key


# --- the plan ---------------------------------------------------------------------------------


def _state_counts(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]]) -> dict[str, int]:
    counts = {}
    for table, states in NON_TERMINAL_STATES.items():
        found = connection.execute(text(
            f"SELECT count(*) FROM {_identifier(table)} t WHERE {_in_scope(closure, table)} AND t.state = ANY(:states)"
        ), {"keys": list(scope[table]), "states": list(states)}).scalar_one()
        if found:
            counts[table] = int(found)
    return counts


def build_plan(connection: Connection, client: Any | None, *, database: str, bucket: str,
               project_uid: str) -> Plan:
    """Everything that can be decided without writing. Raises :class:`EraseRefused`.

    ``client=None`` skips the bucket (sizes stay unknown): the transaction re-derives the plan
    under its locks and must not hold them across the object requests.
    """
    for statement in _SESSION:
        connection.execute(text(statement))
    head, closure = check_schema(connection)
    scope, outside = derive_scope(connection, closure, project_uid)

    # >>> guard: project-exists
    if (project_uid,) != scope[ROOT_TABLE]:
        raise EraseRefused(f"{project_uid} is not a project of this database. Nothing was touched.")
    # <<< guard: project-exists

    # >>> guard: scope-is-pure
    foreign = []
    for table in sorted({table for table, _ in outside}):
        keys = [key for t, key in outside if t == table]
        column = closure.direct.get(table)
        if column is None:
            foreign.append((table, len(keys)))
            continue
        owned = connection.execute(text(
            f"SELECT count(*) FROM {_identifier(table)} t WHERE {_in_scope(closure, table)} "
            f"AND t.{_column(column[0])} IS NOT NULL"
        ), {"keys": keys}).scalar_one()
        if owned:
            foreign.append((table, int(owned)))
    if foreign:
        raise EraseRefused(
            f"a row of the project references a row that belongs to another project (or to no table the tool can "
            f"place): {sorted(foreign)}. Erasing it would leave a dangling reference or take another project's "
            "data. Nothing was touched."
        )
    # <<< guard: scope-is-pure

    # >>> guard: quiescent
    running = _state_counts(connection, closure, scope)
    if running:
        raise EraseRefused(
            f"work of this project is not terminal: {running}. Let it finish, cancel it, or stop the worker "
            "(a claimed remote executor task counts). Nothing was touched."
        )
    # <<< guard: quiescent

    # >>> guard: no-pending-erasure
    pending = connection.execute(text("SELECT count(*) FROM public.blob WHERE state = 'erasure_pending'")).scalar_one()
    if pending:
        raise EraseRefused(
            f"{pending} Blob row(s) are in erasure_pending: an earlier erase committed and did not finish. "
            "Resume it (--resume era_<id>, found in its erasure.requested event) before erasing another project."
        )
    # <<< guard: no-pending-erasure

    receipts = derive_receipts(connection, closure, scope)
    check_receipts(connection, closure, scope, receipts)
    exclusive, shared, keep_ids = classify_blobs(connection, closure, scope)

    # >>> guard: blobs-available
    unsettled = sorted((fact.blob_id, fact.state) for fact in exclusive if fact.state != "available")
    if unsettled:
        raise EraseRefused(
            f"{len(unsettled)} Blob(s) only this project references are not 'available' (a failed or abandoned "
            f"upload): {unsettled[:5]}. They cannot enter erasure_pending; reconcile them first. Nothing was touched."
        )
    # <<< guard: blobs-available

    tokens = sorted(set(connection.execute(text(
        f"SELECT t.upload_token FROM public.analysis_artifact_publication t "
        f"WHERE {_in_scope(closure, 'analysis_artifact_publication')}"
    ), {"keys": list(scope["analysis_artifact_publication"])}).scalars()))
    wanted = sorted(
        [(purge.canonical_key(fact.blob_id), "canonical", fact.blob_id) for fact in exclusive]
        + [(purge.temporary_key(token), "temporary", token) for token in tokens]
    )
    check_object_keys([PlanObject(key, kind, ref, None) for key, kind, ref in wanted], keep_ids)

    sizes: dict[str, int | None] = {}
    if client is not None:
        require_unversioned_bucket(client, bucket)
        for key, _, _ in wanted:
            found = _head(client, bucket, key)
            sizes[key] = None if found is None else int(found["ContentLength"])
    objects = tuple(PlanObject(key, kind, ref, sizes.get(key)) for key, kind, ref in wanted)

    table_facts = {table: _scoped_fingerprint(connection, closure, scope, table) for table in closure.tables}
    receipt_fact = fingerprint(connection, "command_record", "t.command_id = ANY(CAST(:ids AS text[]))",
                               {"ids": list(receipts)})
    identities = sorted({value for table in closure.tables if len(closure.primary_keys[table]) == 1
                         for value in scope[table]})
    journal = connection.execute(text(
        "SELECT count(*) FROM public.audit_event WHERE aggregate_id = ANY(CAST(:ids AS text[]))"
    ), {"ids": identities}).scalar_one()
    document = plan_document(head, project_uid, table_facts, receipt_fact, exclusive, shared, objects)
    return Plan(
        database=database, bucket=bucket, head=head, project_uid=project_uid, scope=scope,
        table_facts=table_facts, receipts=receipts, receipt_fact=receipt_fact, exclusive=tuple(exclusive),
        shared=tuple(shared), objects=objects, journal_events=int(journal), sha256=plan_digest(document),
        closure=closure,
    )


def render_plan(plan: Plan, *, dry_run: bool) -> str:
    out = [f"erase-project: database {plan.database} (migration head {plan.head}), bucket {plan.bucket}",
           f"project: {plan.project_uid}", ""]
    out.append("-- rows of the project, by table (every one is deleted) --")
    for table, (count, _) in plan.table_facts.items():
        if count:
            out.append(f"  {table}  ({count} rows)")
    out.append(f"  command_record  ({len(plan.receipts)} idempotency receipts of those rows)")
    out.append(f"  total: {plan.rows_to_delete} rows in "
               f"{sum(1 for c, _ in plan.table_facts.values() if c) + (1 if plan.receipts else 0)} tables")
    out.append("")
    out.append("-- Blobs --")
    out.append(f"  only this project references: {len(plan.exclusive)} "
               f"({sum(b.size_bytes for b in plan.exclusive)} bytes); the blob rows are deleted and listed in the manifest")
    out.append(f"  shared with another project or the norm corpus: {len(plan.shared)} (stay, with their objects)")
    present = plan.objects_present
    out.append(f"  objects to delete, by exact key: {len(plan.objects)} keys, {len(present)} present in the bucket, "
               f"{sum(o.size or 0 for o in present)} bytes")
    out.append("")
    out.append("-- stays --")
    out.append(f"  run-journal events of the project (identities only): {plan.journal_events}")
    out.append("  accounts, release notes, executor configuration, the norm corpus, every other project")
    out.append("")
    if dry_run:
        out.append("--dry-run: NOTHING ABOVE WAS CHANGED.")
    out.append(f"blobs-exclusive: {len(plan.exclusive)}")
    out.append(f"blobs-shared: {len(plan.shared)}")
    out.append(f"rows-to-delete: {plan.rows_to_delete}")
    out.append(f"plan-sha256: {plan.sha256}")
    return "\n".join(out)


# --- the journal ------------------------------------------------------------------------------


def append_event(connection: Connection, event_type: str, erase_id: str, payload: Mapping[str, Any]) -> None:
    """One ``audit_event`` row in the caller's transaction. Identities, counts and digests only."""
    connection.execute(text(
        "INSERT INTO public.audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, "
        "correlation_id, payload) VALUES (:id, :type, :aggregate_type, :aggregate_id, :correlation, "
        "CAST(:payload AS jsonb))"
    ), {"id": str(AuditEventId.new()), "type": event_type, "aggregate_type": EVENT_AGGREGATE,
        "aggregate_id": erase_id, "correlation": erase_id, "payload": canonical_json(dict(payload))})


def erasure_events(connection: Connection, *, project_uid: str | None = None,
                   erase_id: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
    """``(event_type, erase_id, payload)`` of the erasure events of one project or one erase id."""
    rows = connection.execute(text(
        "SELECT event_type, aggregate_id, payload FROM public.audit_event "
        "WHERE event_type IN (:requested, :completed) "
        "AND (CAST(:project AS text) IS NULL OR payload ->> 'project_uid' = :project) "
        "AND (CAST(:erase AS text) IS NULL OR aggregate_id = :erase) ORDER BY sequence_no"
    ), {"requested": EVENT_REQUESTED, "completed": EVENT_COMPLETED, "project": project_uid,
        "erase": erase_id}).all()
    return [(event_type, aggregate_id, dict(payload)) for event_type, aggregate_id, payload in rows]


def resolve_actor(connection: Connection, login: str | None) -> str:
    """The ``usr_`` identity of an active account that holds ``admin``; the journal never holds the login."""
    rows = connection.execute(text("""
        SELECT u.user_uid, EXISTS (SELECT 1 FROM public.app_user_role r
                                    WHERE r.user_uid = u.user_uid AND r.role = 'admin')
          FROM public.app_user u WHERE u.login = :login AND u.archived_at IS NULL
    """), {"login": login or ""}).all()
    # >>> guard: actor-is-active-account
    if len(rows) != 1:
        raise EraseRefused(
            "--actor must be the login of an active (not archived) account: the journal records its usr_ "
            "identity, never the login. Nothing was touched."
        )
    # <<< guard: actor-is-active-account
    # >>> guard: actor-is-admin
    if not rows[0][1]:
        raise EraseRefused("--actor must hold the admin role; an expert cannot erase a project. Nothing was touched.")
    # <<< guard: actor-is-admin
    return str(rows[0][0])


# --- phase 2: the transaction -----------------------------------------------------------------


def _verification(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]],
                  receipts: Sequence[str], blob_ids: Sequence[str]) -> dict[str, tuple[int, str]]:
    """Count and digest of everything the erase must NOT change."""
    result = {table: fingerprint(connection, table)
              for table in sorted(purge.KEEP_TABLES | UNSCOPED_PRODUCT_TABLES | {"audit_event"})}
    for table in closure.tables:
        result[f"{table}[outside the project]"] = fingerprint(
            connection, table, f"NOT ({_in_scope(closure, table)})", {"keys": list(scope[table])})
    result["command_record[outside the project]"] = fingerprint(
        connection, "command_record", "NOT (t.command_id = ANY(CAST(:ids AS text[])))", {"ids": list(receipts)})
    result["blob[outside the erase]"] = fingerprint(
        connection, "blob", "NOT (t.blob_id = ANY(CAST(:ids AS text[])))", {"ids": list(blob_ids)})
    return result


def _delete_statement(closure: Closure, group: Sequence[str]) -> str:
    if len(group) == 1:
        table = group[0]
        return f"DELETE FROM {_identifier(table)} AS t WHERE {_in_scope(closure, table)}"
    parts = [f"d{index} AS (DELETE FROM {_identifier(table)} AS t "
             f"WHERE {_in_scope(closure, table).replace(':keys', f':k{index}')} RETURNING 1)"
             for index, table in enumerate(group)]
    counts = ", ".join(f"(SELECT count(*) FROM d{index})" for index in range(len(group)))
    return "WITH " + ", ".join(parts) + f" SELECT {counts}"


def delete_scope(connection: Connection, closure: Closure, scope: Mapping[str, Sequence[str]]) -> dict[str, int]:
    """Delete the project's rows, children first, one named guard trigger off at a time."""
    triggers: dict[str, list[str]] = {}
    for table, name, _ in _delete_triggers(connection, closure.tables):
        triggers.setdefault(table, []).append(name)
    deleted: dict[str, int] = {}
    for group in deletion_order(closure.tables, [(key.child, key.parent) for key in closure.edges]):
        members = [table for table in group if scope[table]]
        if not members:
            continue
        statement = _delete_statement(closure, members)
        parameters = ({"keys": list(scope[members[0]])} if len(members) == 1
                      else {f"k{index}": list(scope[table]) for index, table in enumerate(members)})
        switched = [(table, name) for table in members for name in triggers.get(table, ())]
        for table, name in switched:
            connection.execute(text(f"ALTER TABLE {_identifier(table)} DISABLE TRIGGER {_column(name)}"))
        result = connection.execute(text(statement), parameters)
        counts = [result.rowcount] if len(members) == 1 else list(result.one())
        for table, name in switched:
            connection.execute(text(f"ALTER TABLE {_identifier(table)} ENABLE TRIGGER {_column(name)}"))
        for table, count in zip(members, counts, strict=True):
            deleted[table] = int(count)
    return deleted


def write_erase_files(directory: Path, erase_id: str, plan: Plan, manifest: bytes) -> None:
    """The plan and the manifest, on disk before the commit that makes them the only record."""
    document = plan_document(plan.head, plan.project_uid, plan.table_facts, plan.receipt_fact,
                             plan.exclusive, plan.shared, plan.objects)
    directory.mkdir(parents=True, exist_ok=False)
    os.chmod(directory, 0o700)
    envelope = {"erase_id": erase_id, "plan": document, "plan_sha256": plan.sha256}
    atomic_write(directory / "plan.json", (canonical_json(envelope) + "\n").encode("utf-8"))
    atomic_write(directory / "manifest.json", manifest)
    for name in ("plan.json", "manifest.json"):
        os.chmod(directory / name, 0o600)


def phase_commit(engine: Engine, *, database: str, bucket: str, project_uid: str, expected_plan: str,
                 actor_uid: str, reason: str, permission_ref: str, dump_dir: Path) -> Committed:
    """Phase 2. ONE transaction. Any exception, including a verification mismatch, rolls all of it back."""
    erase_id = str(ErasureRequestId.new())
    directory = dump_dir / erase_id
    try:
        with engine.begin() as connection:
            for statement in _SESSION:
                connection.execute(text(statement))
            # the catalog guards first, before any lock: a role that does not own the tables is refused here
            # (and not by the database's "permission denied" at LOCK TABLE)
            closure = check_schema(connection)[1]
            try:
                connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
                # >>> guard: erase-lock-free
                if not connection.execute(text(
                        "SELECT pg_try_advisory_xact_lock(hashtextextended(:name, 0))"), {"name": ADVISORY_LOCK_NAME}).scalar_one():
                    raise EraseRefused("another erase holds the lock; wait for it to finish. Nothing was changed.")
                # <<< guard: erase-lock-free
                connection.execute(text("LOCK TABLE " + _tables_sql(
                    purge.KEEP_TABLES | UNSCOPED_PRODUCT_TABLES) + " IN SHARE MODE"))
                connection.execute(text("LOCK TABLE " + _tables_sql(
                    set(closure.tables) | set(MIXED_TOUCHED)) + " IN SHARE ROW EXCLUSIVE MODE"))
            except DBAPIError as error:
                # >>> guard: lock-available
                if getattr(error.orig, "sqlstate", "") == "55P03":
                    raise EraseRefused(f"could not lock the tables within {LOCK_TIMEOUT}: something is still writing. "
                                       "Stop api/web/worker and run it again; nothing was changed.") from error
                # <<< guard: lock-available
                raise

            # The plan again, under the locks: nothing can change from here to COMMIT.
            plan = build_plan(connection, None, database=database, bucket=bucket, project_uid=project_uid)

            # >>> guard: plan-unchanged
            if plan.sha256 != expected_plan:
                raise EraseRefused(
                    "the project's data (or the schema, or the Blob classification) changed since the plan "
                    f"that was approved (plan {plan.sha256[:12]}, expected {str(expected_plan)[:12]}). Run the dry run "
                    "again and show the owner the new plan; nothing was changed."
                )
            # <<< guard: plan-unchanged

            closure_checked = plan.closure
            manifest = manifest_bytes(erase_id, project_uid, plan.exclusive)
            manifest_sha256 = sha256_text(manifest)
            blob_ids = tuple(fact.blob_id for fact in plan.exclusive)
            requested = {
                "project_uid": project_uid, "actor_uid": actor_uid, "reason_code": reason,
                "owner_permission_ref": permission_ref, "plan_sha256": plan.sha256,
                "manifest_sha256": manifest_sha256, "rows_deleted": plan.rows_to_delete,
                "blobs_exclusive": len(plan.exclusive), "blobs_shared": len(plan.shared),
            }
            append_event(connection, EVENT_REQUESTED, erase_id, requested)

            before = _verification(connection, closure_checked, plan.scope, plan.receipts, blob_ids)
            triggers_before = purge._trigger_state(connection)

            moved = connection.execute(text(
                "UPDATE public.blob SET state = 'erasure_pending' "
                "WHERE blob_id = ANY(CAST(:ids AS text[])) AND state = 'available'"
            ), {"ids": list(blob_ids)}).rowcount
            deleted = delete_scope(connection, closure_checked, plan.scope)
            if plan.receipts:
                connection.execute(text(
                    "DELETE FROM public.command_record WHERE command_id = ANY(CAST(:ids AS text[]))"
                ), {"ids": list(plan.receipts)})

            after = _verification(connection, closure_checked, plan.scope, plan.receipts, blob_ids)

            # >>> guard: blobs-pending
            pending = connection.execute(text(
                "SELECT count(*) FROM public.blob WHERE blob_id = ANY(CAST(:ids AS text[])) AND state = 'erasure_pending'"
            ), {"ids": list(blob_ids)}).scalar_one()
            if moved != len(blob_ids) or pending != len(blob_ids):
                raise EraseRefused(
                    f"{moved} of {len(blob_ids)} exclusive Blob(s) moved to erasure_pending; rolled back, nothing changed"
                )
            # <<< guard: blobs-pending
            # >>> guard: keep-unchanged
            changed = sorted(name for name in before if before[name] != after[name])
            if changed:
                raise EraseRefused(f"the erase would have changed data outside the project in {changed}; rolled back, nothing changed")
            # <<< guard: keep-unchanged
            # >>> guard: project-emptied
            left = {}
            for table in closure_checked.tables:
                count = connection.execute(text(
                    f"SELECT count(*) FROM {_identifier(table)} t WHERE {_in_scope(closure_checked, table)}"
                ), {"keys": list(plan.scope[table])}).scalar_one()
                if count:
                    left[table] = int(count)
            receipts_left = connection.execute(text(
                "SELECT count(*) FROM public.command_record WHERE command_id = ANY(CAST(:ids AS text[]))"
            ), {"ids": list(plan.receipts)}).scalar_one()
            if left or receipts_left:
                raise EraseRefused(f"rows of the project remain after the erase: {left}, receipts {receipts_left}; rolled back")
            if sum(deleted.values()) + len(plan.receipts) != plan.rows_to_delete:
                raise EraseRefused("the number of deleted rows differs from the plan; rolled back")
            # <<< guard: project-emptied
            # >>> guard: triggers-restored
            if purge._trigger_state(connection) != triggers_before:
                raise EraseRefused("a trigger's state differs after the erase; rolled back")
            if str(connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()) != plan.head:
                raise EraseRefused("alembic_version changed; rolled back")
            # <<< guard: triggers-restored

            write_erase_files(directory, erase_id, plan, manifest)
            committed = Committed(
                erase_id=erase_id, project_uid=project_uid, plan_sha256=plan.sha256,
                manifest_sha256=manifest_sha256, blob_ids=blob_ids, objects=plan.objects,
                rows_deleted=plan.rows_to_delete, blobs_shared=len(plan.shared), actor_uid=actor_uid,
                reason=reason, permission_ref=permission_ref, directory=directory,
            )
    except BaseException:
        # the transaction is rolled back; the files (written just before the commit) describe nothing
        for name in ("plan.json", "manifest.json", "plan.json.part", "manifest.json.part"):
            (directory / name).unlink(missing_ok=True)
        try:
            directory.rmdir()
        except OSError:
            pass
        raise
    return committed


# --- phase 3: the objects ---------------------------------------------------------------------


def delete_objects(engine: Engine, client: Any, *, bucket: str, objects: Sequence[PlanObject],
                   blob_ids: Sequence[str]) -> dict[str, int]:
    """Phase 3. After COMMIT: delete the listed keys, each by its exact name. An absent key counts as done."""
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        closure = load_closure(connection)
        keep_pairs, project_pairs = blob_reference_columns(connection, closure)
        keep_ids = set(connection.execute(text(purge._keep_blob_ids_sql(keep_pairs))).scalars())
        referenced: set[str] = set()
        for table, column in project_pairs:
            referenced |= set(connection.execute(text(
                f"SELECT t.{_column(column)} FROM {_identifier(table)} t "
                f"WHERE t.{_column(column)} = ANY(CAST(:ids AS text[]))"
            ), {"ids": list(blob_ids)}).scalars())
        referenced |= set(connection.execute(text(purge._keep_blob_ids_sql(keep_pairs))).scalars()) & set(blob_ids)

    # >>> guard: object-key-shape
    for item in objects:
        try:
            derived = (purge.canonical_key(item.ref) if item.kind == "canonical" and _BLOB_ID.fullmatch(item.ref)
                       else purge.temporary_key(item.ref) if item.kind == "temporary" else None)
        except purge.PurgeRefused:
            derived = None
        if derived != item.key:
            raise EraseRefused(f"{item.key!r} is not exactly the key of {item.kind} {item.ref!r}; this tool deletes "
                               "exact keys it can derive, never a pattern. Nothing was deleted.")
    # <<< guard: object-key-shape
    check_object_keys(objects, keep_ids)
    # >>> guard: objects-unreferenced
    if referenced:
        raise EraseRefused(f"a row references Blob(s) of the erase list: {sorted(referenced)[:5]}. "
                           "The list no longer describes an erased project; nothing was deleted.")
    # <<< guard: objects-unreferenced
    require_unversioned_bucket(client, bucket)
    result = {"deleted": 0, "missing": 0, "bytes": 0}
    problems = []
    for item in objects:
        try:
            head = _head(client, bucket, item.key)
            if head is None:
                result["missing"] += 1
                continue
            client.delete_object(Bucket=bucket, Key=item.key)
            # >>> guard: objects-gone
            if _head(client, bucket, item.key) is not None:
                raise EraseFailed(f"{item.key} is still in the bucket after its delete")
            # <<< guard: objects-gone
            result["deleted"] += 1
            result["bytes"] += int(head["ContentLength"])
        except (ClientError, EraseFailed) as error:
            problems.append(f"{item.key}: {error}")
    if problems:
        raise EraseFailed(f"{len(problems)} object(s) could not be deleted: " + "; ".join(problems[:5]))
    return result


# --- phase 4: the finish ----------------------------------------------------------------------


def _pending_blobs(connection: Connection) -> list[BlobFact]:
    return sorted((BlobFact(*row) for row in connection.execute(text(
        "SELECT blob_id, coalesce(sha256, ''), coalesce(size_bytes, -1), coalesce(media_type, ''), state "
        "FROM public.blob WHERE state = 'erasure_pending'"
    )).all()), key=lambda fact: fact.blob_id)


def phase_finish(engine: Engine, committed: Committed, *, summary: Mapping[str, int], actor_uid: str,
                 permission_ref: str) -> None:
    """Phase 4. ONE transaction: delete the Blob rows, append ``erasure.completed``."""
    with engine.begin() as connection:
        for statement in _SESSION:
            connection.execute(text(statement))
        connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
        connection.execute(text("LOCK TABLE public.blob IN SHARE ROW EXCLUSIVE MODE"))
        pending = _pending_blobs(connection)

        # >>> guard: finish-matches-manifest
        digest = sha256_text(manifest_bytes(committed.erase_id, committed.project_uid, pending))
        if digest != committed.manifest_sha256 or tuple(b.blob_id for b in pending) != committed.blob_ids:
            raise EraseRefused(
                f"the Blobs in erasure_pending are not the manifest of {committed.erase_id} "
                f"({len(pending)} found, {len(committed.blob_ids)} expected). Nothing was deleted."
            )
        # <<< guard: finish-matches-manifest
        closure = load_closure(connection)
        keep_pairs, project_pairs = blob_reference_columns(connection, closure)
        referenced = 0
        for table, column in [*keep_pairs, *project_pairs]:
            referenced += int(connection.execute(text(
                f"SELECT count(*) FROM {_identifier(table)} t WHERE t.{_column(column)} = ANY(CAST(:ids AS text[]))"
            ), {"ids": list(committed.blob_ids)}).scalar_one())
        # >>> guard: pending-unreferenced
        if referenced:
            raise EraseRefused(f"{referenced} row(s) reference Blob(s) of the manifest; nothing was deleted.")
        # <<< guard: pending-unreferenced
        removed = connection.execute(text(
            "DELETE FROM public.blob WHERE blob_id = ANY(CAST(:ids AS text[])) AND state = 'erasure_pending'"
        ), {"ids": list(committed.blob_ids)}).rowcount
        left = connection.execute(text("SELECT count(*) FROM public.blob WHERE state = 'erasure_pending'")).scalar_one()
        # >>> guard: pending-cleared
        if removed != len(committed.blob_ids) or left:
            raise EraseRefused(f"{removed} of {len(committed.blob_ids)} Blob row(s) deleted, {left} still pending; rolled back")
        # <<< guard: pending-cleared
        append_event(connection, EVENT_COMPLETED, committed.erase_id, {
            "project_uid": committed.project_uid, "actor_uid": actor_uid,
            "reason_code": committed.reason, "owner_permission_ref": permission_ref,
            "plan_sha256": committed.plan_sha256, "manifest_sha256": committed.manifest_sha256,
            "rows_deleted": committed.rows_deleted, "blobs_exclusive": len(committed.blob_ids),
            "blobs_shared": committed.blobs_shared, "objects_deleted": summary["deleted"],
            "objects_missing": summary["missing"], "outcome": "completed",
        })


# --- apply and resume -------------------------------------------------------------------------


def apply_erase(engine: Engine, client: Any, *, database: str, bucket: str, project_uid: str,
                expected_plan: str, actor_uid: str, reason: str, permission_ref: str, dump_dir: Path,
                out: Any) -> Committed:
    committed = phase_commit(
        engine, database=database, bucket=bucket, project_uid=project_uid, expected_plan=expected_plan,
        actor_uid=actor_uid, reason=reason, permission_ref=permission_ref, dump_dir=dump_dir)
    print(f"erase-id: {committed.erase_id}", file=out, flush=True)
    finish(engine, client, committed, bucket=bucket, actor_uid=actor_uid, permission_ref=permission_ref, out=out)
    return committed


def finish(engine: Engine, client: Any, committed: Committed, *, bucket: str, actor_uid: str,
           permission_ref: str, out: Any) -> None:
    """Phases 3 and 4. A failure here leaves a committed erase that ``--resume`` completes."""
    try:
        summary = delete_objects(engine, client, bucket=bucket, objects=committed.objects, blob_ids=committed.blob_ids)
        print(f"objects-deleted: {summary['deleted']}", file=out, flush=True)
        print(f"objects-missing: {summary['missing']}", file=out, flush=True)
        phase_finish(engine, committed, summary=summary, actor_uid=actor_uid, permission_ref=permission_ref)
    except EraseRefused as error:
        raise EraseFailed(f"the database part of {committed.erase_id} is committed, the erase is not finished: "
                          f"{error} Resume with --resume {committed.erase_id}.") from error
    except Exception as error:  # noqa: BLE001 - the operator needs the id and the way forward, not a traceback
        raise EraseFailed(f"the database part of {committed.erase_id} is committed, the erase is not finished "
                          f"({type(error).__name__}: {error}). Resume with --resume {committed.erase_id}.") from error


def load_committed(engine: Engine, erase_id: str, dump_dir: Path, *, actor_uid: str, permission_ref: str,
                   out: Any) -> Committed | None:
    """Rebuild phase 2's result from the journal, the Blob rows and the plan file. ``None``: finished."""
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        for statement in _SESSION:
            connection.execute(text(statement))
        events = erasure_events(connection, erase_id=erase_id)
        pending = _pending_blobs(connection)
    # >>> guard: erase-id-known
    requested = [payload for kind, _, payload in events if kind == EVENT_REQUESTED]
    if len(requested) != 1:
        raise EraseRefused(f"{erase_id} has no erasure.requested event in this database. Nothing was touched.")
    # <<< guard: erase-id-known
    if any(kind == EVENT_COMPLETED for kind, _, _ in events):
        return None
    payload = requested[0]
    project_uid = str(payload["project_uid"])

    manifest = manifest_bytes(erase_id, project_uid, pending)
    # >>> guard: resume-manifest-matches
    if sha256_text(manifest) != payload["manifest_sha256"]:
        raise EraseRefused(
            f"the Blobs in erasure_pending ({len(pending)}) are not the manifest "
            f"({str(payload['manifest_sha256'])[:12]}) that {erase_id} recorded when it committed. Nothing was touched."
        )
    # <<< guard: resume-manifest-matches
    directory = dump_dir / erase_id
    manifest_file = directory / "manifest.json"
    # >>> guard: resume-manifest-file-matches
    if manifest_file.exists() and manifest_file.read_bytes() != manifest:
        raise EraseRefused(f"{manifest_file} differs from the manifest {erase_id} recorded (its digest is in the "
                           "erasure.requested event). Nothing was touched.")
    # <<< guard: resume-manifest-file-matches
    if not manifest_file.exists():
        directory.mkdir(parents=True, exist_ok=True)
        atomic_write(manifest_file, manifest)
        print(f"manifest-rewritten: {manifest_file}", file=out, flush=True)

    objects = [PlanObject(purge.canonical_key(blob.blob_id), "canonical", blob.blob_id, None) for blob in pending]
    plan_file = directory / "plan.json"
    if plan_file.exists():
        envelope = json.loads(plan_file.read_text(encoding="utf-8"))
        # >>> guard: resume-plan-file-matches
        if (envelope.get("plan_sha256") != payload["plan_sha256"]
                or plan_digest(envelope.get("plan", {})) != payload["plan_sha256"]):
            raise EraseRefused(f"{plan_file} is not the plan {erase_id} recorded. Nothing was touched.")
        # <<< guard: resume-plan-file-matches
        for key, kind, ref in envelope["plan"]["objects"]:
            if kind == "temporary":
                objects.append(PlanObject(key, kind, ref, None))
    else:
        print(f"WARNING: {plan_file} is absent: the staged temporary/ objects named by the erased publications cannot "
              "be listed, so they are not looked for; the Blob objects are deleted from the database's own list",
              file=sys.stderr, flush=True)
    return Committed(
        erase_id=erase_id, project_uid=project_uid, plan_sha256=str(payload["plan_sha256"]),
        manifest_sha256=str(payload["manifest_sha256"]), blob_ids=tuple(b.blob_id for b in pending),
        objects=tuple(sorted(objects, key=lambda o: o.key)), rows_deleted=int(payload["rows_deleted"]),
        blobs_shared=int(payload["blobs_shared"]), actor_uid=actor_uid, reason=str(payload["reason_code"]),
        permission_ref=permission_ref, directory=directory,
    )


# --- the command line -------------------------------------------------------------------------


def _no_ambient_libpq() -> None:
    """``PGHOSTADDR`` beats the host in ``DATABASE_URL``; ``PGSERVICE`` can supply anything else."""
    ambient = sorted(name for name in os.environ if name.startswith("PG"))
    # >>> guard: no-ambient-libpq
    if ambient:
        raise EraseRefused(f"libpq environment variable(s) {ambient} can redirect the connection that "
                           "DATABASE_URL names. Unset them; DATABASE_URL is the only target. Nothing was touched.")
    # <<< guard: no-ambient-libpq


def _typed_names(engine: Engine, s3: S3StorageSettings, database: str, bucket: str) -> None:
    with engine.connect() as connection:
        actual = str(connection.execute(text("SELECT current_database()")).scalar_one())
    # >>> guard: names-match
    if actual != database or s3.bucket != bucket:
        raise EraseRefused(
            f"the typed names are not the connected ones: database {database!r} vs {actual!r}, "
            f"bucket {bucket!r} vs {s3.bucket!r}. Nothing was touched."
        )
    # <<< guard: names-match


def _read_only_plan(engine: Engine, client: Any, database: str, bucket: str, project_uid: str) -> Plan:
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        return build_plan(connection, client, database=database, bucket=bucket, project_uid=project_uid)


def _already_erased(engine: Engine, project_uid: str) -> tuple[str, str | None] | None:
    """``(state, erase_id)``: ``("completed", id)``, ``("incomplete", id)`` or ``None`` for a project never erased."""
    with engine.connect() as connection:
        events = erasure_events(connection, project_uid=project_uid)
        exists = connection.execute(text("SELECT count(*) FROM public.project WHERE project_uid = :p"),
                                    {"p": project_uid}).scalar_one()
    if exists:
        return None
    completed = [erase_id for kind, erase_id, _ in events if kind == EVENT_COMPLETED]
    if completed:
        return ("completed", completed[-1])
    requested = [erase_id for kind, erase_id, _ in events if kind == EVENT_REQUESTED]
    if requested:
        return ("incomplete", requested[-1])
    return None


def check_arguments(args: argparse.Namespace) -> None:
    """The refusals that need no database: what an operator must say before anything is touched."""
    mode = "resume" if args.resume is not None else "apply" if args.apply else "plan"
    # >>> guard: project-identity-shape
    if mode != "resume" and not (args.project and _PROJECT_UID.fullmatch(args.project)):
        raise EraseRefused("--project must be a project identity (prj_ and 26 characters), never a name.")
    if mode == "resume" and not _ERASE_ID.fullmatch(args.resume):
        raise EraseRefused("--resume must be an erase identity (era_ and 26 characters).")
    # <<< guard: project-identity-shape
    if mode == "plan":
        return
    # >>> guard: owner-permission-ref
    reference = (args.owner_permission_ref or "").strip()
    if not reference or len(reference) > PERMISSION_REF_MAX or any(ord(ch) < 32 or ord(ch) == 127 for ch in reference):
        raise EraseRefused(
            "--owner-permission-ref is required and must say, in one line of at most "
            f"{PERMISSION_REF_MAX} characters, where the owner's permission to erase this project is recorded "
            "(R-146aj: an operator never erases a project without it). The tool cannot verify the reference; "
            "it records it. Nothing was touched."
        )
    # <<< guard: owner-permission-ref
    # >>> guard: dump-dir-required
    if args.dump_dir is None:
        raise EraseRefused("--dump-dir is required: the plan and the manifest of the erased Blobs are written there "
                           "and are the only record of what was erased. Nothing was touched.")
    # <<< guard: dump-dir-required
    if mode == "resume":
        return
    # >>> guard: plan-digest-required
    if not args.plan_sha256 or not _SHA256.fullmatch(args.plan_sha256):
        raise EraseRefused("--apply needs --plan-sha256 <the digest the dry run printed>: the apply refuses a plan "
                           "nobody approved. Nothing was touched.")
    # <<< guard: plan-digest-required
    # >>> guard: reason-closed-list
    if args.reason not in REASON_CODES:
        raise EraseRefused(f"--reason must be one of {list(REASON_CODES)}; free text is refused because it would put "
                           "personal data into an append-only table. Nothing was touched.")
    # <<< guard: reason-closed-list


def render_done(committed: Committed) -> str:
    out = [f"erase-project: {committed.project_uid} erased as {committed.erase_id}.",
           f"manifest-sha256: {committed.manifest_sha256}", f"manifest: {committed.directory / 'manifest.json'}",
           f"plan-sha256: {committed.plan_sha256}", f"rows-deleted: {committed.rows_deleted}", "",
           "Keep the manifest file with the release record: the database holds only its digest.",
           "An erase does not reach:"]
    out += [f"  - {item}" for item in NOT_REACHED]
    return "\n".join(out)


def run(argv: Sequence[str] | None = None, *, out: Any = None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog="project_erase", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--database", required=True, help="the typed name of the connected database")
    parser.add_argument("--bucket", required=True, help="the typed name of the connected bucket")
    parser.add_argument("--project", help="prj_<ULID>: an identity, never a name")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="the default: print the plan, change nothing")
    mode.add_argument("--apply", action="store_true", help="erase; needs --plan-sha256")
    mode.add_argument("--resume", metavar="era_ID", help="finish an erase that committed and did not complete")
    parser.add_argument("--plan-sha256", help="--apply: the digest the dry run printed")
    parser.add_argument("--actor", help="login of an active account that holds admin")
    parser.add_argument("--reason", help=f"one of {', '.join(REASON_CODES)}")
    parser.add_argument("--owner-permission-ref",
                        help="where the owner's permission is recorded (free text, one line; recorded, not verified)")
    parser.add_argument("--dump-dir", type=Path, help="where <era_ID>/plan.json and manifest.json are written")
    args = parser.parse_args(argv)
    engine: Engine | None = None
    try:
        check_arguments(args)
        _no_ambient_libpq()
        s3 = S3StorageSettings.from_env()
        engine = create_database_engine(load_settings())
        _typed_names(engine, s3, args.database, args.bucket)
        client = purge.s3_client(s3)
        if args.resume is None:
            erased = _already_erased(engine, args.project)
            if erased is not None:
                state, erase_id = erased
                if state == "completed":
                    print(f"erase-project: {args.project} was erased as {erase_id} and that erase is complete; "
                          "nothing to do.", file=out)
                    return EXIT_OK
                raise EraseRefused(f"{args.project} has no rows left and {erase_id} is not complete: resume it with "
                                   f"--resume {erase_id}. Nothing was touched.")
        if not args.apply and args.resume is None:
            plan = _read_only_plan(engine, client, args.database, args.bucket, args.project)
            print(render_plan(plan, dry_run=True), file=out)
            return EXIT_OK
        with engine.connect() as connection:
            actor_uid = resolve_actor(connection, args.actor)
        permission_ref = (args.owner_permission_ref or "").strip()
        if args.resume is not None:
            committed = load_committed(engine, args.resume, args.dump_dir, actor_uid=actor_uid,
                                       permission_ref=permission_ref, out=out)
            if committed is None:
                print(f"erase-project: {args.resume} is already complete; nothing to do.", file=out)
                return EXIT_OK
            print(f"erase-id: {committed.erase_id}", file=out, flush=True)
            finish(engine, client, committed, bucket=args.bucket, actor_uid=actor_uid,
                   permission_ref=permission_ref, out=out)
            print(render_done(committed), file=out)
            return EXIT_OK
        committed = apply_erase(
            engine, client, database=args.database, bucket=args.bucket, project_uid=args.project,
            expected_plan=args.plan_sha256, actor_uid=actor_uid, reason=args.reason,
            permission_ref=permission_ref, dump_dir=args.dump_dir, out=out)
        print(render_done(committed), file=out)
        return EXIT_OK
    except EraseRefused as error:
        print(f"project_erase: REFUSED: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except EraseFailed as error:
        print(f"project_erase: FAILED: {error}", file=sys.stderr)
        return EXIT_FAILED
    except Exception as error:  # noqa: BLE001 - the operator needs a status, not a traceback
        print(f"project_erase: FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_FAILED
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(run())
