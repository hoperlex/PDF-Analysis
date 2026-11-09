"""DECISION-MEMORY-01 phase M2: make the decision memory FORGET cases, as `DECISION-MEMORY-01` section 4.5 defines it.

The memory outlives the project and the document a case came from (`ADR-0027`); this operator tool is the one way a case's CONTENT
leaves it, on the owner's permission (`R-146aj`, the rule the project erase follows). It is an operator tool and nothing in the product
imports it. It is modelled on ``project_erase.py`` and reuses its helpers instead of retyping them.

WHAT IT REMOVES. For the chosen cases (``--case`` once or more, ``--origin-project`` or ``--all``): the five content-side tables
(``decision_memory_content``, ``_evidence``, ``_norm_ref``, ``_crop`` and the expert's comment, ``_decision_text``), and every crop Blob
(row and object) that nothing else references. WHAT STAYS. The case, its decisions (verdict, severity, author, time -- no words of the
expert) and one ``forget`` STATUS EVENT per case, the tombstone: who, when, why, the owner's permission reference and the digest of the
content that was forgotten (``forgotten_content_sha256``), which proves what is gone without holding it. A Blob that another case, a
live document's artifact or the norm corpus still references stays with its object. Everything the forgotten content was copied into
elsewhere is not reached (``NOT_REACHED``).

HOW THE CONTENT TABLES LET IT. They are not switched off: since migration ``0061`` the guard ``am_guard_decision_memory_forget`` permits
a ``DELETE`` only when a ``forget`` status event of the same case was inserted by the SAME transaction (its ``xmin`` is the transaction's
id), and the application role holds no ``DELETE`` privilege. So the status events and the deletes are one transaction here, or the
database refuses.

FOUR PHASES (the object deletion is an external side effect, so it is not a dual write):

1. ``plan``: read-only, always first. Guards, per-table row counts and digests of the rows to delete, the cases with the digest of their
   content, the Blob list classified exclusive or shared, the object keys, a SHA-256 over the canonical form of all that.
2. ``commit``: ONE transaction. Lock, re-derive the plan and compare its digest, append ``memory.forget_requested``, insert one
   ``forget`` status event per case, move every exclusive Blob to ``erasure_pending``, delete the content rows, verify that every row
   outside the scope is unchanged by count and digest, write the plan and manifest files, commit.
3. ``objects``: delete each exclusive Blob's object by exact key (an absent key counts as done).
4. ``finish``: ONE transaction. Delete the ``erasure_pending`` Blob rows, append ``memory.forget_completed`` with the manifest digest.

A crash after phase 2 leaves Blobs in ``erasure_pending`` and nothing referencing them; ``--resume era_<ULID>`` completes phases 3 and 4.
Running a finished forget again finds no case left to forget and exits 0 with "nothing to do".

The forget id is an ``era_`` identity (the erasure request identity; the audit events are ``memory.*``, the aggregate
``DecisionMemoryForget``). ``--owner-permission-ref`` is REQUIRED to apply or resume and is recorded in the status events and both audit
events; the tool cannot verify a permission. ``--reason`` is a closed list: free text would put personal data into an append-only table.

GUARDS ARE DELIMITED BY ``# >>> guard: <name>`` / ``# <<< guard: <name>`` markers, the convention of ``project_erase.py``:
``tests/integration/recovery/test_memory_forget.py`` deletes ONE guard block from a copy of this file and shows the copy no longer
refuses. Do not remove a marker without removing its test.

USAGE (``DATABASE_URL`` is the owner role's -- the migrator's; ``S3_*`` as the application's; no ``PG*`` variable):

    python -m scripts.recovery.memory_forget --database D --bucket B --origin-project prj_...            # dry run
    python -m scripts.recovery.memory_forget --database D --bucket B --origin-project prj_... --apply \\
        --plan-sha256 <digest the dry run printed> --actor <admin login> --reason client_request \\
        --owner-permission-ref "<where the owner's permission is recorded>" --dump-dir DIR
    python -m scripts.recovery.memory_forget --database D --bucket B --resume era_... \\
        --actor <admin login> --owner-permission-ref "<...>" --dump-dir DIR

Exit codes: 0 done (or nothing to do), 2 usage, 3 REFUSED (nothing was changed), 4 FAILED.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError
from sqlalchemy import Connection, Engine, text

from auditmanager.decision_memory.public import STATUS_REASON_CODES
from auditmanager.shared.db.config import load_settings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AuditEventId, DecisionMemoryStatusEventId, ErasureRequestId
from auditmanager.storage.public import S3StorageSettings
from scripts.recovery import product_purge as purge
from scripts.recovery import project_erase as erase
from scripts.recovery.blob_reference_audit import _CATALOG, _CATALOG_EXPECTED
from scripts.recovery.schema_coverage import HEAD

EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_FAILED = 0, 2, 3, 4

#: The closed list of reasons: the vocabulary of the status event's ``reason_code``.
REASON_CODES = STATUS_REASON_CODES
EVENT_REQUESTED = "memory.forget_requested"
EVENT_COMPLETED = "memory.forget_completed"
EVENT_AGGREGATE = "DecisionMemoryForget"
#: The lock name of "another forget is running".
ADVISORY_LOCK_NAME = "auditmanager.memory_forget"
#: The per-case lock of ``am_guard_decision_memory_status`` and ``decision_memory.service`` (the same key, character for character).
STATUS_LOCK_PREFIX = "decision_memory_status:"
LOCK_TIMEOUT = os.environ.get("MEMORY_FORGET_LOCK_TIMEOUT", "15s")
PLAN_FILE_VERSION = 1
PERMISSION_REF_MAX = erase.PERMISSION_REF_MAX
#: ``out of shared memory``: what PostgreSQL answers when the server-wide lock table has no slot left for one more lock.
SQLSTATE_OUT_OF_SHARED_MEMORY = "53200"
#: The three settings that size the server's lock table (``max_locks_per_transaction`` x (``max_connections`` + ``max_prepared_transactions``)).
LOCK_TABLE_SETTINGS = ("max_locks_per_transaction", "max_connections", "max_prepared_transactions")
#: The dry run warns when a selection needs more than this share of the lock table's documented size (4/5; integer arithmetic, `D-516`).
LOCK_WARN_NUMERATOR, LOCK_WARN_DENOMINATOR = 4, 5

#: The content side, in the order the rows are deleted (the foreign keys point at ``decision_memory_content``), with the predicate that
#: selects a case's rows; ``:cases`` is the case-id list.
_BY_CASE = "t.case_id = ANY(CAST(:cases AS text[]))"
_BY_DECISION = (
    "t.memory_decision_id IN (SELECT d.memory_decision_id FROM public.decision_memory_decision d "
    "WHERE d.case_id = ANY(CAST(:cases AS text[])))"
)
CONTENT_TABLES: dict[str, str] = {
    "decision_memory_crop": _BY_CASE,
    "decision_memory_evidence": _BY_CASE,
    "decision_memory_norm_ref": _BY_CASE,
    "decision_memory_decision_text": _BY_DECISION,
    "decision_memory_content": _BY_CASE,
}
#: Tables the tool writes besides the content tables.
TOUCHED = ("audit_event", "blob", "decision_memory_status_event")
#: Tables that must come out of the forget exactly as they went in.
UNCHANGED = ("decision_memory_case", "decision_memory_decision")

_CASE_ID = re.compile(r"dmc_[0-9A-HJKMNP-TV-Z]{26}\Z")
_PROJECT_UID = re.compile(r"prj_[0-9A-HJKMNP-TV-Z]{26}\Z")
_ERASE_ID = erase._ERASE_ID
_SHA256 = erase._SHA256
_BLOB_ID = erase._BLOB_ID
_SESSION = erase._SESSION

NOT_REACHED = (
    "exports already produced and anything trained on them (a training export is a copy outside the host; this tool cannot recall it)",
    "prompts already sent to a model provider and the local copies of a remote executor",
    "dumps, mirrors and copies on the host (infra/deploy/dumps/, the copy directory), the VPS provider's snapshots and any copy "
    "outside the host: remove or age them by hand and record that in the release record",
    "the disk blocks of a deleted object (there is no secure wipe) and container logs",
    "the legal-hold question (R-146aj: the owner's permission is the only ground; it is recorded, not verified)",
)


class ForgetRefused(Exception):
    """Nothing was changed, and the reason is in the message. Exit 3."""


class ForgetFailed(Exception):
    """Something broke; the message says what state that leaves. Exit 4."""


# --- values -----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Selector:
    """Which cases: ``cases`` (identities), ``origin_project`` (an identity) or ``all``."""

    kind: str
    values: tuple[str, ...] = ()

    def document(self) -> dict[str, Any]:
        if self.kind == "cases":
            return {"kind": "cases", "count": len(self.values), "case_ids": list(self.values)}
        if self.kind == "origin_project":
            return {"kind": "origin_project", "origin_project_uid": self.values[0]}
        return {"kind": "all"}

    def event_document(self) -> dict[str, Any]:
        """The same, for the audit event: identities and counts, never a list that grows with the memory."""
        document = self.document()
        document.pop("case_ids", None)
        return document


@dataclass(frozen=True, slots=True)
class Plan:
    database: str
    bucket: str
    head: str
    selector: Selector
    cases: tuple[tuple[str, str], ...]  # (case_id, content_sha256), ordered
    already_forgotten: int
    table_facts: Mapping[str, tuple[int, str]]
    exclusive: tuple[erase.BlobFact, ...]
    shared: tuple[str, ...]
    objects: tuple[erase.PlanObject, ...]
    sha256: str

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(case_id for case_id, _ in self.cases)

    @property
    def rows_to_delete(self) -> int:
        return sum(count for count, _ in self.table_facts.values())


@dataclass(frozen=True, slots=True)
class Committed:
    """What phase 2 leaves for phases 3 and 4."""

    forget_id: str
    plan_sha256: str
    manifest_sha256: str
    blob_ids: tuple[str, ...]
    objects: tuple[erase.PlanObject, ...]
    rows_deleted: int
    cases: int
    blobs_shared: int
    actor_uid: str
    reason: str
    permission_ref: str
    directory: Path


# --- the plan's canonical forms ---------------------------------------------------------------


def manifest_bytes(forget_id: str, blobs: Sequence[erase.BlobFact]) -> bytes:
    """The manifest of the forgotten Blobs: byte-deterministic, so ``sha256sum`` of the file is the event's digest."""
    document = {
        "blobs": [
            {"blob_id": b.blob_id, "media_type": b.media_type, "sha256": b.sha256, "size_bytes": b.size_bytes}
            for b in sorted(blobs, key=lambda blob: blob.blob_id)
        ],
        "forget_id": forget_id,
        "version": PLAN_FILE_VERSION,
    }
    return (erase.canonical_json(document) + "\n").encode("utf-8")


def plan_document(head: str, selector: Selector, cases: Sequence[tuple[str, str]], table_facts: Mapping[str, tuple[int, str]],
                  exclusive: Sequence[erase.BlobFact], shared: Sequence[str], objects: Sequence[erase.PlanObject]) -> dict[str, Any]:
    """The canonical form the plan digest is taken over: nothing about who, why or when."""
    return {
        "blobs": {
            "exclusive": [[b.blob_id, b.sha256, b.size_bytes, b.media_type] for b in sorted(exclusive, key=lambda blob: blob.blob_id)],
            "shared": sorted(shared),
        },
        "cases": [list(pair) for pair in cases],
        "objects": [[o.key, o.kind, o.ref] for o in sorted(objects, key=lambda obj: obj.key)],
        "schema_head": head,
        "selector": selector.document(),
        "tables": {table: list(fact) for table, fact in sorted(table_facts.items())},
        "version": PLAN_FILE_VERSION,
    }


# --- the catalog and the scope ----------------------------------------------------------------


def check_schema(connection: Connection) -> str:
    """Every refusal that needs only the catalog. Returns the migration head."""
    head = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
    if len(head) != 1:
        raise ForgetRefused(f"alembic_version holds {len(head)} rows, not one")
    # >>> guard: head-is-declared
    if str(head[0]) != HEAD:
        raise ForgetRefused(
            f"the database is at migration {head[0]}, the tool was written for {HEAD} (schema_coverage.HEAD). "
            "A migration is a decision about what a forget must reach; extend the declaration first. Nothing was touched."
        )
    # <<< guard: head-is-declared

    # >>> guard: forget-guard-installed
    guarded = {row[0] for row in connection.execute(text("""
        SELECT c.relname FROM pg_catalog.pg_trigger t
          JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
         WHERE NOT t.tgisinternal AND c.relnamespace = 'public'::regnamespace AND p.proname = 'am_guard_decision_memory_forget'
           AND t.tgenabled = 'O' AND (t.tgtype::integer & 8) = 8
    """)).all()}
    if guarded != set(CONTENT_TABLES):
        raise ForgetRefused(
            f"the forget guard is not installed and enabled on exactly the content tables (found {sorted(guarded)}, "
            f"expected {sorted(CONTENT_TABLES)}): without it a delete is refused, and a table without it would not be protected. "
            "Nothing was touched."
        )
    # <<< guard: forget-guard-installed

    # >>> guard: blob-columns-closed
    found = {tuple(row) for row in connection.execute(_CATALOG).all()}
    if found != {tuple(item) for item in _CATALOG_EXPECTED}:
        raise ForgetRefused(
            f"the Blob-reference columns of the schema differ from the registry (found-only {sorted(found - _CATALOG_EXPECTED)}, "
            f"registry-only {sorted(_CATALOG_EXPECTED - found)}). A new reference must be classified before a Blob is deleted. "
            "Nothing was touched."
        )
    # <<< guard: blob-columns-closed

    # >>> guard: owner-may-write
    foreign = connection.execute(text("""
        SELECT c.relname FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relname = ANY(:names)
           AND NOT pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
    """), {"names": sorted((*CONTENT_TABLES, *TOUCHED))}).scalars().all()
    if foreign:
        raise ForgetRefused(
            f"the connected role {erase._current_user(connection)!r} does not own: {sorted(foreign)}. "
            "A forget deletes content and moves Blobs: it needs the owning role (the migrator), not the application's role."
        )
    # <<< guard: owner-may-write
    return str(head[0])


def derive_scope(connection: Connection, selector: Selector) -> tuple[list[tuple[str, str]], int]:
    """``(cases to forget, count already forgotten)``: the chosen cases that have no ``forget`` event yet."""
    if selector.kind == "cases":
        rows = connection.execute(text(
            "SELECT c.case_id, c.content_sha256, EXISTS (SELECT 1 FROM public.decision_memory_status_event e "
            "WHERE e.case_id = c.case_id AND e.kind = 'forget') FROM public.decision_memory_case c "
            "WHERE c.case_id = ANY(CAST(:ids AS text[])) ORDER BY c.case_id"
        ), {"ids": list(selector.values)}).all()
        # >>> guard: cases-exist
        unknown = sorted(set(selector.values) - {row[0] for row in rows})
        if unknown:
            raise ForgetRefused(f"{len(unknown)} case(s) are not in this memory: {unknown[:5]}. Nothing was touched.")
        # <<< guard: cases-exist
    elif selector.kind == "origin_project":
        rows = connection.execute(text(
            "SELECT c.case_id, c.content_sha256, EXISTS (SELECT 1 FROM public.decision_memory_status_event e "
            "WHERE e.case_id = c.case_id AND e.kind = 'forget') FROM public.decision_memory_case c "
            "WHERE c.origin_project_uid = :project ORDER BY c.case_id"
        ), {"project": selector.values[0]}).all()
    else:
        rows = connection.execute(text(
            "SELECT c.case_id, c.content_sha256, EXISTS (SELECT 1 FROM public.decision_memory_status_event e "
            "WHERE e.case_id = c.case_id AND e.kind = 'forget') FROM public.decision_memory_case c ORDER BY c.case_id"
        )).all()
    return [(str(r[0]), str(r[1])) for r in rows if not r[2]], sum(1 for r in rows if r[2])


def table_fact(connection: Connection, table: str, cases: Sequence[str], *, outside: bool = False) -> tuple[int, str]:
    predicate = CONTENT_TABLES[table]
    return erase.fingerprint(connection, table, f"NOT ({predicate})" if outside else predicate, {"cases": list(cases)})


def classify_blobs(connection: Connection, cases: Sequence[str]) -> tuple[list[erase.BlobFact], list[str]]:
    """``(exclusive, shared)``: the Blobs the cases' crops reference, by who else references them.

    Exclusive: no crop of another case, no table of the catalog (a live document's artifact, the norm custody, a price list, ...)
    references it. Those leave with the forget; the others stay with their objects.
    """
    candidates = sorted(set(connection.execute(text(
        "SELECT t.blob_id FROM public.decision_memory_crop t WHERE t.case_id = ANY(CAST(:cases AS text[]))"
    ), {"cases": list(cases)}).scalars()))
    elsewhere: set[str] = set()
    if candidates:
        for _schema, table, column in sorted(tuple(row) for row in connection.execute(_CATALOG).all()):
            if (table, column) == ("blob", "blob_id"):
                continue
            where = "AND t.case_id <> ALL(CAST(:cases AS text[]))" if table == "decision_memory_crop" else ""
            elsewhere |= set(connection.execute(text(
                f"SELECT t.{erase._column(column)} FROM {erase._identifier(table)} t "
                f"WHERE t.{erase._column(column)} = ANY(CAST(:ids AS text[])) {where}"
            ), {"ids": candidates, "cases": list(cases)}).scalars())
    shared = sorted(set(candidates) & elsewhere)
    exclusive_ids = sorted(set(candidates) - elsewhere)
    facts = sorted((erase.BlobFact(*row) for row in connection.execute(text(
        "SELECT blob_id, coalesce(sha256, ''), coalesce(size_bytes, -1), coalesce(media_type, ''), state "
        "FROM public.blob WHERE blob_id = ANY(CAST(:ids AS text[]))"
    ), {"ids": exclusive_ids}).all()), key=lambda fact: fact.blob_id)
    if len(facts) != len(exclusive_ids):
        raise ForgetFailed("a crop references a Blob id that has no blob row")
    return facts, shared


def build_plan(connection: Connection, client: Any | None, *, database: str, bucket: str, selector: Selector) -> Plan:
    """Everything that can be decided without writing. Raises :class:`ForgetRefused`.

    ``client=None`` skips the bucket (sizes stay unknown): the transaction re-derives the plan under its locks and must not hold them
    across the object requests.
    """
    for statement in _SESSION:
        connection.execute(text(statement))
    head = check_schema(connection)
    cases, already = derive_scope(connection, selector)
    case_ids = [case_id for case_id, _ in cases]

    # >>> guard: no-pending-erasure
    pending = connection.execute(text("SELECT count(*) FROM public.blob WHERE state = 'erasure_pending'")).scalar_one()
    if pending:
        raise ForgetRefused(
            f"{pending} Blob row(s) are in erasure_pending: an earlier erase or forget committed and did not finish. "
            "Resume it (--resume era_<id>, found in its erasure.requested or memory.forget_requested event) first."
        )
    # <<< guard: no-pending-erasure

    exclusive, shared = classify_blobs(connection, case_ids)
    # >>> guard: blobs-available
    unsettled = sorted((fact.blob_id, fact.state) for fact in exclusive if fact.state != "available")
    if unsettled:
        raise ForgetRefused(
            f"{len(unsettled)} Blob(s) only these cases reference are not 'available': {unsettled[:5]}. "
            "They cannot enter erasure_pending; reconcile them first. Nothing was touched."
        )
    # <<< guard: blobs-available

    wanted = sorted((purge.canonical_key(fact.blob_id), "canonical", fact.blob_id) for fact in exclusive)
    sizes: dict[str, int | None] = {}
    if client is not None:
        if wanted:
            erase.require_unversioned_bucket(client, bucket)
        for key, _, _ in wanted:
            found = erase._head(client, bucket, key)
            sizes[key] = None if found is None else int(found["ContentLength"])
    objects = tuple(erase.PlanObject(key, kind, ref, sizes.get(key)) for key, kind, ref in wanted)
    table_facts = {table: table_fact(connection, table, case_ids) for table in CONTENT_TABLES}
    document = plan_document(head, selector, cases, table_facts, exclusive, shared, objects)
    return Plan(
        database=database, bucket=bucket, head=head, selector=selector, cases=tuple(cases), already_forgotten=already,
        table_facts=table_facts, exclusive=tuple(exclusive), shared=tuple(shared), objects=objects,
        sha256=erase.sha256_text(erase.canonical_json(document)),
    )


def render_plan(plan: Plan, *, dry_run: bool, lock_room: Sequence[str] = ()) -> str:
    out = [f"memory-forget: database {plan.database} (migration head {plan.head}), bucket {plan.bucket}",
           f"selector: {erase.canonical_json(plan.selector.event_document())}", ""]
    out.append(f"-- cases to forget: {len(plan.cases)} (already forgotten and skipped: {plan.already_forgotten}) --")
    out.append("  each keeps its case row, its decisions (verdict, severity, author, time) and a forget status event (the tombstone)")
    out.append("")
    out.append("-- content rows, by table (every one is deleted) --")
    for table, (count, _) in plan.table_facts.items():
        if count:
            out.append(f"  {table}  ({count} rows)")
    out.append(f"  total: {plan.rows_to_delete} rows")
    out.append("")
    out.append("-- Blobs (the crop images the cases reference) --")
    out.append(f"  only these cases reference: {len(plan.exclusive)} "
               f"({sum(b.size_bytes for b in plan.exclusive)} bytes); the blob rows are deleted and listed in the manifest")
    out.append(f"  also referenced by another case, a document's artifact or the norm corpus: {len(plan.shared)} (stay, with their objects)")
    present = tuple(o for o in plan.objects if o.size is not None)
    out.append(f"  objects to delete, by exact key: {len(plan.objects)} keys, {len(present)} present in the bucket, "
               f"{sum(o.size or 0 for o in present)} bytes")
    out.append("")
    if lock_room:
        out.extend(lock_room)
        out.append("")
    if dry_run:
        out.append("--dry-run: NOTHING ABOVE WAS CHANGED.")
    out.append(f"cases: {len(plan.cases)}")
    out.append(f"blobs-exclusive: {len(plan.exclusive)}")
    out.append(f"blobs-shared: {len(plan.shared)}")
    out.append(f"rows-to-delete: {plan.rows_to_delete}")
    out.append(f"plan-sha256: {plan.sha256}")
    return "\n".join(out)


# --- the journal ------------------------------------------------------------------------------


def append_event(connection: Connection, event_type: str, forget_id: str, payload: Mapping[str, Any]) -> None:
    """One ``audit_event`` row in the caller's transaction. Identities, counts and digests only."""
    connection.execute(text(
        "INSERT INTO public.audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, "
        "correlation_id, payload) VALUES (:id, :type, :aggregate_type, :aggregate_id, :correlation, "
        "CAST(:payload AS jsonb))"
    ), {"id": str(AuditEventId.new()), "type": event_type, "aggregate_type": EVENT_AGGREGATE,
        "aggregate_id": forget_id, "correlation": forget_id, "payload": erase.canonical_json(dict(payload))})


def forget_events(connection: Connection, forget_id: str) -> list[tuple[str, dict[str, Any]]]:
    rows = connection.execute(text(
        "SELECT event_type, payload FROM public.audit_event WHERE event_type IN (:requested, :completed) "
        "AND aggregate_id = :forget ORDER BY sequence_no"
    ), {"requested": EVENT_REQUESTED, "completed": EVENT_COMPLETED, "forget": forget_id}).all()
    return [(event_type, dict(payload)) for event_type, payload in rows]


def resolve_actor(connection: Connection, login: str | None) -> str:
    """The ``usr_`` identity of an active account that holds ``admin``; the journal never holds the login."""
    try:
        return erase.resolve_actor(connection, login)
    except erase.EraseRefused as error:
        raise ForgetRefused(str(error).replace("erase a project", "forget a case")) from error


# --- phase 2: the transaction -----------------------------------------------------------------


def lock_table_settings(connection: Connection) -> tuple[int, int, int]:
    """``max_locks_per_transaction``, ``max_connections`` and ``max_prepared_transactions`` of the server this connection is to."""
    per, connections, prepared = (int(connection.execute(text(f"SELECT current_setting('{name}')")).scalar_one())
                                  for name in LOCK_TABLE_SETTINGS)
    return per, connections, prepared


def lock_room_lines(cases: int, *, per: int, connections: int, prepared: int) -> list[str]:
    """What the dry run says about the lock table (`D-516`): the advisory locks the selection needs, the table's documented size, and a
    warning above 80 % of it.

    The apply takes one advisory lock per case and one more that says a forget is running, and holds them all until it commits. The table
    is shared by every session and sized by ``max_locks_per_transaction`` x (``max_connections`` + ``max_prepared_transactions``); PostgreSQL
    rounds it up, and on the default settings about twice that many fitted (13056 measured against the documented 6400), so the documented
    size is the cautious figure and above 80 % of it is the point at which an operator is told. The table's other users (the application's own
    sessions, and the relation locks of this very transaction) are not counted: the warning is a reason to read runbook section 21, not a
    promise either way. It is a statement in the plan's text and not a part of the plan: it is not in the plan's digest.
    """
    needed = cases + 1
    slots = per * (connections + prepared)
    lines = ["-- advisory locks (the apply holds them until it commits) --",
             f"  needed: {needed} ({cases} cases, one lock each, and one that says a forget is running)",
             f"  server lock table: max_locks_per_transaction {per} x (max_connections {connections} + max_prepared_transactions {prepared}) "
             f"= {slots} slots, shared by every session"]
    if needed * LOCK_WARN_DENOMINATOR > slots * LOCK_WARN_NUMERATOR:
        lines.append(f"  WARNING: this selection needs {-(-needed * 100 // slots)} % of that size (the warning starts above "
                     f"{LOCK_WARN_NUMERATOR * 100 // LOCK_WARN_DENOMINATOR} %). PostgreSQL rounds the table up and about twice the size fitted on "
                     "the default settings (measured), so it may still go through; when it does not, the apply is refused and changes nothing. "
                     "Forget fewer at a time (--origin-project, or --case in batches) with api and worker stopped, or raise "
                     "max_locks_per_transaction first (runbook section 21, 'Large selections').")
    return lines


def lock_room_for_dry_run(connection: Connection, cases: int) -> list[str]:
    """``lock_room_lines`` for the connection's server. A server that will not say its settings is said so, not left out."""
    try:
        per, connections, prepared = lock_table_settings(connection)
    except Exception as error:  # noqa: BLE001 - the numbers are help; the plan stands without them, and says that it does
        return ["-- advisory locks (the apply holds them until it commits) --",
                f"  needed: {cases + 1} ({cases} cases, one lock each, and one that says a forget is running)",
                f"  server lock table: its size could not be read ({type(error).__name__}); an apply that outgrows it is refused and changes nothing"]
    return lock_room_lines(cases, per=per, connections=connections, prepared=prepared)


def lock_table_message(engine: Engine, *, wanted: int, taken: int) -> str:
    """The refusal for a selection too large for the server's lock table (`D-497` item 6): numbers, and the two ways out.

    Every case needs one advisory lock until the single transaction commits, and the lock table is shared by every session of the server:
    ``max_locks_per_transaction`` x (``max_connections`` + ``max_prepared_transactions``) sizes it (default ``64`` x ``100`` = 6400);
    PostgreSQL rounds the shared memory up, and on the default settings about twice that many locks fit (13056 measured, 2026-11-09,
    ``.local/evidence/lane-mem-ops-d511/measure-locks-result.json``). The transaction was rolled back, so it is read on a connection of
    its own.
    """
    capacity = "unknown"
    try:
        with engine.connect() as connection:
            per, connections, prepared = lock_table_settings(connection)
        capacity = f"{per} x ({connections} + {prepared}) = {per * (connections + prepared)}"
    except Exception:  # noqa: BLE001 - the numbers are help; the refusal stands without them
        pass
    batch = max(1, taken // 2)
    return (f"{wanted} cases need one advisory lock each inside the single transaction of a forget, and the server's lock table ran out "
            f"after {taken}; the table is shared by every session and sized by max_locks_per_transaction x (max_connections + "
            f"max_prepared_transactions) = {capacity}. Nothing was changed. Forget fewer at a time -- one project (--origin-project) or at most {batch} cases "
            "(--case, repeated) per run -- with api and worker stopped, which frees the slots they hold; or raise "
            "max_locks_per_transaction in the server's configuration and restart it.")


def _verification(connection: Connection, cases: Sequence[str]) -> dict[str, tuple[int, str]]:
    """What must not move: the case and decision tables whole, the content tables outside the scope, the status events' old rows."""
    facts = {table: erase.fingerprint(connection, table) for table in UNCHANGED}
    for table in CONTENT_TABLES:
        facts[f"{table}:outside"] = table_fact(connection, table, cases, outside=True)
    return facts


def write_forget_files(directory: Path, forget_id: str, plan: Plan, manifest: bytes) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    envelope = {"forget_id": forget_id, "plan_sha256": plan.sha256,
                "plan": plan_document(plan.head, plan.selector, plan.cases, plan.table_facts, plan.exclusive, plan.shared, plan.objects)}
    erase.atomic_write(directory / "plan.json", (erase.canonical_json(envelope) + "\n").encode("utf-8"))
    erase.atomic_write(directory / "manifest.json", manifest)


def phase_commit(engine: Engine, *, database: str, bucket: str, selector: Selector, expected_plan: str, actor_uid: str,
                 reason: str, permission_ref: str, dump_dir: Path) -> Committed | None:
    """Phase 2. ONE transaction. Any exception, including a verification mismatch, rolls all of it back. ``None``: nothing to forget."""
    forget_id = str(ErasureRequestId.new())
    directory = dump_dir / forget_id
    try:
        with engine.begin() as connection:
            for statement in _SESSION:
                connection.execute(text(statement))
            check_schema(connection)  # the catalog guards first, before any lock
            connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
            # >>> guard: forget-lock-free
            if not connection.execute(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:name, 0))"),
                                      {"name": ADVISORY_LOCK_NAME}).scalar_one():
                raise ForgetRefused("another forget holds the lock; wait for it to finish. Nothing was changed.")
            # <<< guard: forget-lock-free
            try:
                # Captures insert decisions and their comments: queue them behind this transaction, so that a comment cannot arrive
                # for a case after its content was deleted and before the forget committed.
                connection.execute(text("LOCK TABLE public.decision_memory_decision, public.decision_memory_decision_text "
                                        "IN SHARE ROW EXCLUSIVE MODE"))
                # The status events are NOT table-locked: a withdraw or restore of a case queues on the case's advisory lock (taken below, and
                # by the transition guard), and a table lock here against a writer that holds that advisory lock would be a deadlock.
                connection.execute(text("LOCK TABLE " + erase._tables_sql({*CONTENT_TABLES, *UNCHANGED, "audit_event", "blob"})
                                        + " IN SHARE ROW EXCLUSIVE MODE"))
            except Exception as error:
                # >>> guard: lock-available
                if getattr(getattr(error, "orig", None), "sqlstate", "") == "55P03":
                    raise ForgetRefused(f"could not lock the tables within {LOCK_TIMEOUT}: something is still writing. "
                                        "Stop api/worker and run it again; nothing was changed.") from error
                # <<< guard: lock-available
                raise

            # The plan again, under the locks: nothing can change from here to COMMIT.
            plan = build_plan(connection, None, database=database, bucket=bucket, selector=selector)
            if not plan.cases:
                return None
            # >>> guard: plan-unchanged
            if plan.sha256 != expected_plan:
                raise ForgetRefused(
                    "the memory (or the schema, or the Blob classification) changed since the plan that was approved "
                    f"(plan {plan.sha256[:12]}, expected {str(expected_plan)[:12]}). Run the dry run again and show the owner "
                    "the new plan; nothing was changed."
                )
            # <<< guard: plan-unchanged

            manifest = manifest_bytes(forget_id, plan.exclusive)
            manifest_sha256 = erase.sha256_text(manifest)
            blob_ids = tuple(fact.blob_id for fact in plan.exclusive)
            cases_sha256 = erase.sha256_text("\n".join(plan.case_ids))
            append_event(connection, EVENT_REQUESTED, forget_id, {
                "actor_uid": actor_uid, "reason_code": reason, "owner_permission_ref": permission_ref,
                "selector": plan.selector.event_document(), "cases": len(plan.cases), "cases_sha256": cases_sha256,
                "plan_sha256": plan.sha256, "manifest_sha256": manifest_sha256, "rows_deleted": plan.rows_to_delete,
                "blobs_exclusive": len(plan.exclusive), "blobs_shared": len(plan.shared),
            })

            before = _verification(connection, plan.case_ids)
            events_before = int(connection.execute(text("SELECT count(*) FROM public.decision_memory_status_event")).scalar_one())
            triggers_before = purge._trigger_state(connection)

            taken = 0
            try:
                for case_id, content_sha256 in plan.cases:
                    # one writer per case, the key of the transition guard and of the product's withdraw and restore. The guard takes the
                    # same lock again on the INSERT below, so this one cannot be dropped to save a slot: a forget holds one advisory lock
                    # per case until it commits (`D-497` item 6).
                    connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                                       {"key": STATUS_LOCK_PREFIX + case_id})
                    taken += 1
                    connection.execute(text(
                        "INSERT INTO public.decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, "
                        "owner_permission_ref, forgotten_content_sha256) VALUES (:id, :case, 'forget', :reason, :actor, :ref, :digest)"
                    ), {"id": DecisionMemoryStatusEventId.new().value, "case": case_id, "reason": reason, "actor": actor_uid,
                        "ref": permission_ref, "digest": content_sha256})
            except Exception as error:
                # >>> guard: lock-table-room
                if getattr(getattr(error, "orig", None), "sqlstate", "") == SQLSTATE_OUT_OF_SHARED_MEMORY:
                    raise ForgetRefused(lock_table_message(engine, wanted=len(plan.cases), taken=taken)) from error
                # <<< guard: lock-table-room
                raise
            moved = connection.execute(text(
                "UPDATE public.blob SET state = 'erasure_pending' WHERE blob_id = ANY(CAST(:ids AS text[])) AND state = 'available'"
            ), {"ids": list(blob_ids)}).rowcount
            deleted = {}
            for table, predicate in CONTENT_TABLES.items():
                deleted[table] = connection.execute(
                    text(f"DELETE FROM {erase._identifier(table)} AS t WHERE {predicate}"), {"cases": list(plan.case_ids)}).rowcount

            after = _verification(connection, plan.case_ids)
            # >>> guard: blobs-pending
            pending = connection.execute(text(
                "SELECT count(*) FROM public.blob WHERE blob_id = ANY(CAST(:ids AS text[])) AND state = 'erasure_pending'"
            ), {"ids": list(blob_ids)}).scalar_one()
            if moved != len(blob_ids) or pending != len(blob_ids):
                raise ForgetRefused(f"{moved} of {len(blob_ids)} exclusive Blob(s) moved to erasure_pending; rolled back, nothing changed")
            # <<< guard: blobs-pending
            # >>> guard: keep-unchanged
            changed = sorted(name for name in before if before[name] != after[name])
            if changed:
                raise ForgetRefused(f"the forget would have changed data outside the chosen cases in {changed}; rolled back, nothing changed")
            # <<< guard: keep-unchanged
            # >>> guard: content-emptied
            left = {table: int(count) for table in CONTENT_TABLES
                    if (count := table_fact(connection, table, plan.case_ids)[0])}
            events_after = int(connection.execute(text("SELECT count(*) FROM public.decision_memory_status_event")).scalar_one())
            if left or events_after != events_before + len(plan.cases):
                raise ForgetRefused(f"content of the chosen cases remains ({left}) or the status events differ "
                                    f"({events_before} -> {events_after}); rolled back")
            if {table: count for table, count in deleted.items()} != {t: f[0] for t, f in plan.table_facts.items()}:
                raise ForgetRefused("the number of deleted rows differs from the plan; rolled back")
            # <<< guard: content-emptied
            # >>> guard: triggers-restored
            if purge._trigger_state(connection) != triggers_before:
                raise ForgetRefused("a trigger's state differs after the forget; rolled back")
            if str(connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()) != plan.head:
                raise ForgetRefused("alembic_version changed; rolled back")
            # <<< guard: triggers-restored

            write_forget_files(directory, forget_id, plan, manifest)
            committed = Committed(
                forget_id=forget_id, plan_sha256=plan.sha256, manifest_sha256=manifest_sha256, blob_ids=blob_ids,
                objects=plan.objects, rows_deleted=plan.rows_to_delete, cases=len(plan.cases), blobs_shared=len(plan.shared),
                actor_uid=actor_uid, reason=reason, permission_ref=permission_ref, directory=directory,
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


def _referenced(connection: Connection, blob_ids: Sequence[str]) -> set[str]:
    referenced: set[str] = set()
    for _schema, table, column in sorted(tuple(row) for row in connection.execute(_CATALOG).all()):
        if (table, column) == ("blob", "blob_id"):
            continue
        referenced |= set(connection.execute(text(
            f"SELECT t.{erase._column(column)} FROM {erase._identifier(table)} t WHERE t.{erase._column(column)} = ANY(CAST(:ids AS text[]))"
        ), {"ids": list(blob_ids)}).scalars())
    return referenced


def delete_objects(engine: Engine, client: Any, *, bucket: str, objects: Sequence[erase.PlanObject],
                   blob_ids: Sequence[str]) -> dict[str, int]:
    """Phase 3. After COMMIT: delete the listed keys, each by its exact name. An absent key counts as done."""
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        referenced = _referenced(connection, blob_ids)
    # >>> guard: object-key-shape
    for item in objects:
        try:
            derived = purge.canonical_key(item.ref) if item.kind == "canonical" and _BLOB_ID.fullmatch(item.ref) else None
        except purge.PurgeRefused:
            derived = None
        if derived != item.key:
            raise ForgetRefused(f"{item.key!r} is not exactly the key of {item.kind} {item.ref!r}; this tool deletes "
                                "exact keys it can derive, never a pattern. Nothing was deleted.")
    # <<< guard: object-key-shape
    # >>> guard: objects-unreferenced
    if referenced:
        raise ForgetRefused(f"a row references Blob(s) of the forget list: {sorted(referenced)[:5]}. "
                            "The list no longer describes forgotten content; nothing was deleted.")
    # <<< guard: objects-unreferenced
    if objects:
        erase.require_unversioned_bucket(client, bucket)
    result = {"deleted": 0, "missing": 0, "bytes": 0}
    problems = []
    for item in objects:
        try:
            head = erase._head(client, bucket, item.key)
            if head is None:
                result["missing"] += 1
                continue
            client.delete_object(Bucket=bucket, Key=item.key)
            # >>> guard: objects-gone
            if erase._head(client, bucket, item.key) is not None:
                raise ForgetFailed(f"{item.key} is still in the bucket after its delete")
            # <<< guard: objects-gone
            result["deleted"] += 1
            result["bytes"] += int(head["ContentLength"])
        except (ClientError, ForgetFailed) as error:
            problems.append(f"{item.key}: {error}")
    if problems:
        raise ForgetFailed(f"{len(problems)} object(s) could not be deleted: " + "; ".join(problems[:5]))
    return result


# --- phase 4: the finish ----------------------------------------------------------------------


def phase_finish(engine: Engine, committed: Committed, *, summary: Mapping[str, int], actor_uid: str, permission_ref: str) -> None:
    """Phase 4. ONE transaction: delete the Blob rows, append ``memory.forget_completed``."""
    with engine.begin() as connection:
        for statement in _SESSION:
            connection.execute(text(statement))
        connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
        connection.execute(text("LOCK TABLE public.blob IN SHARE ROW EXCLUSIVE MODE"))
        pending = erase._pending_blobs(connection)
        # >>> guard: finish-matches-manifest
        if (erase.sha256_text(manifest_bytes(committed.forget_id, pending)) != committed.manifest_sha256
                or tuple(b.blob_id for b in pending) != committed.blob_ids):
            raise ForgetRefused(
                f"the Blobs in erasure_pending are not the manifest of {committed.forget_id} "
                f"({len(pending)} found, {len(committed.blob_ids)} expected). Nothing was deleted."
            )
        # <<< guard: finish-matches-manifest
        referenced = _referenced(connection, committed.blob_ids)
        # >>> guard: pending-unreferenced
        if referenced:
            raise ForgetRefused(f"{len(referenced)} Blob(s) of the manifest are referenced again; nothing was deleted.")
        # <<< guard: pending-unreferenced
        removed = connection.execute(text(
            "DELETE FROM public.blob WHERE blob_id = ANY(CAST(:ids AS text[])) AND state = 'erasure_pending'"
        ), {"ids": list(committed.blob_ids)}).rowcount
        left = connection.execute(text("SELECT count(*) FROM public.blob WHERE state = 'erasure_pending'")).scalar_one()
        # >>> guard: pending-cleared
        if removed != len(committed.blob_ids) or left:
            raise ForgetRefused(f"{removed} of {len(committed.blob_ids)} Blob row(s) deleted, {left} still pending; rolled back")
        # <<< guard: pending-cleared
        append_event(connection, EVENT_COMPLETED, committed.forget_id, {
            "actor_uid": actor_uid, "reason_code": committed.reason, "owner_permission_ref": permission_ref,
            "plan_sha256": committed.plan_sha256, "manifest_sha256": committed.manifest_sha256, "cases": committed.cases,
            "rows_deleted": committed.rows_deleted, "blobs_exclusive": len(committed.blob_ids),
            "blobs_shared": committed.blobs_shared, "objects_deleted": summary["deleted"],
            "objects_missing": summary["missing"], "outcome": "completed",
        })


# --- apply and resume -------------------------------------------------------------------------


def finish(engine: Engine, client: Any, committed: Committed, *, bucket: str, actor_uid: str, permission_ref: str, out: Any) -> None:
    """Phases 3 and 4. A failure here leaves a committed forget that ``--resume`` completes."""
    try:
        summary = delete_objects(engine, client, bucket=bucket, objects=committed.objects, blob_ids=committed.blob_ids)
        print(f"objects-deleted: {summary['deleted']}", file=out, flush=True)
        print(f"objects-missing: {summary['missing']}", file=out, flush=True)
        phase_finish(engine, committed, summary=summary, actor_uid=actor_uid, permission_ref=permission_ref)
    except ForgetRefused as error:
        raise ForgetFailed(f"the database part of {committed.forget_id} is committed, the forget is not finished: "
                           f"{error} Resume with --resume {committed.forget_id}.") from error
    except Exception as error:  # noqa: BLE001 - the operator needs the id and the way forward, not a traceback
        raise ForgetFailed(f"the database part of {committed.forget_id} is committed, the forget is not finished "
                           f"({type(error).__name__}: {error}). Resume with --resume {committed.forget_id}.") from error


def load_committed(engine: Engine, forget_id: str, dump_dir: Path, *, actor_uid: str, permission_ref: str, out: Any) -> Committed | None:
    """Rebuild phase 2's result from the journal, the Blob rows and the plan file. ``None``: finished."""
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        for statement in _SESSION:
            connection.execute(text(statement))
        events = forget_events(connection, forget_id)
        pending = erase._pending_blobs(connection)
    # >>> guard: forget-id-known
    requested = [payload for kind, payload in events if kind == EVENT_REQUESTED]
    if len(requested) != 1:
        raise ForgetRefused(f"{forget_id} has no {EVENT_REQUESTED} event in this database. Nothing was touched.")
    # <<< guard: forget-id-known
    if any(kind == EVENT_COMPLETED for kind, _ in events):
        return None
    payload = requested[0]
    manifest = manifest_bytes(forget_id, pending)
    # >>> guard: resume-manifest-matches
    if erase.sha256_text(manifest) != payload["manifest_sha256"]:
        raise ForgetRefused(
            f"the Blobs in erasure_pending ({len(pending)}) are not the manifest ({str(payload['manifest_sha256'])[:12]}) that "
            f"{forget_id} recorded when it committed. Nothing was touched."
        )
    # <<< guard: resume-manifest-matches
    directory = dump_dir / forget_id
    manifest_file = directory / "manifest.json"
    # >>> guard: resume-manifest-file-matches
    if manifest_file.exists() and manifest_file.read_bytes() != manifest:
        raise ForgetRefused(f"{manifest_file} differs from the manifest {forget_id} recorded (its digest is in the "
                            f"{EVENT_REQUESTED} event). Nothing was touched.")
    # <<< guard: resume-manifest-file-matches
    if not manifest_file.exists():
        directory.mkdir(parents=True, exist_ok=True)
        erase.atomic_write(manifest_file, manifest)
        print(f"manifest-rewritten: {manifest_file}", file=out, flush=True)
    objects = [erase.PlanObject(purge.canonical_key(blob.blob_id), "canonical", blob.blob_id, None) for blob in pending]
    return Committed(
        forget_id=forget_id, plan_sha256=str(payload["plan_sha256"]), manifest_sha256=str(payload["manifest_sha256"]),
        blob_ids=tuple(b.blob_id for b in pending), objects=tuple(sorted(objects, key=lambda o: o.key)),
        rows_deleted=int(payload["rows_deleted"]), cases=int(payload["cases"]), blobs_shared=int(payload["blobs_shared"]),
        actor_uid=actor_uid, reason=str(payload["reason_code"]), permission_ref=permission_ref, directory=directory,
    )


# --- the command line -------------------------------------------------------------------------


def _no_ambient_libpq() -> None:
    """``PGHOSTADDR`` beats the host in ``DATABASE_URL``; ``PGSERVICE`` can supply anything else."""
    ambient = sorted(name for name in os.environ if name.startswith("PG"))
    # >>> guard: no-ambient-libpq
    if ambient:
        raise ForgetRefused(f"libpq environment variable(s) {ambient} can redirect the connection that "
                            "DATABASE_URL names. Unset them; DATABASE_URL is the only target. Nothing was touched.")
    # <<< guard: no-ambient-libpq


def _typed_names(engine: Engine, s3: S3StorageSettings, database: str, bucket: str) -> None:
    with engine.connect() as connection:
        actual = str(connection.execute(text("SELECT current_database()")).scalar_one())
    # >>> guard: names-match
    if actual != database or s3.bucket != bucket:
        raise ForgetRefused(f"the typed names are not the connected ones: database {database!r} vs {actual!r}, "
                            f"bucket {bucket!r} vs {s3.bucket!r}. Nothing was touched.")
    # <<< guard: names-match


def selector_of(args: argparse.Namespace) -> Selector:
    chosen = [bool(args.case), bool(args.origin_project), bool(args.all)]
    # >>> guard: one-selector
    if sum(chosen) != 1:
        raise ForgetRefused("name exactly one of --case (once or more), --origin-project or --all: which cases to forget. "
                            "Nothing was touched.")
    # <<< guard: one-selector
    # >>> guard: identity-shape
    if args.case:
        bad = [value for value in args.case if not _CASE_ID.fullmatch(value)]
        if bad:
            raise ForgetRefused(f"--case must be a case identity (dmc_ and 26 characters), never a description: {bad[:3]}")
        return Selector("cases", tuple(sorted(set(args.case))))
    if args.origin_project:
        if not _PROJECT_UID.fullmatch(args.origin_project):
            raise ForgetRefused("--origin-project must be a project identity (prj_ and 26 characters), never a name.")
        return Selector("origin_project", (args.origin_project,))
    # <<< guard: identity-shape
    return Selector("all")


def check_arguments(args: argparse.Namespace) -> None:
    """The refusals that need no database: what an operator must say before anything is touched."""
    mode = "resume" if args.resume is not None else "apply" if args.apply else "plan"
    if mode != "resume":
        selector_of(args)
    # >>> guard: resume-id-shape
    elif not _ERASE_ID.fullmatch(args.resume):
        raise ForgetRefused("--resume must be a forget identity (era_ and 26 characters).")
    # <<< guard: resume-id-shape
    if mode == "plan":
        return
    # >>> guard: owner-permission-ref
    reference = (args.owner_permission_ref or "").strip()
    if not reference or len(reference) > PERMISSION_REF_MAX or any(ord(ch) < 32 or ord(ch) == 127 for ch in reference):
        raise ForgetRefused(
            "--owner-permission-ref is required and must say, in one line of at most "
            f"{PERMISSION_REF_MAX} characters, where the owner's permission to forget these cases is recorded "
            "(R-146aj: an operator never removes the memory's content without it). The tool cannot verify the reference; "
            "it records it. Nothing was touched."
        )
    # <<< guard: owner-permission-ref
    # >>> guard: dump-dir-required
    if args.dump_dir is None:
        raise ForgetRefused("--dump-dir is required: the plan and the manifest of the forgotten Blobs are written there "
                            "and are the only record of what was forgotten. Nothing was touched.")
    # <<< guard: dump-dir-required
    if mode == "resume":
        return
    # >>> guard: plan-digest-required
    if not args.plan_sha256 or not _SHA256.fullmatch(args.plan_sha256):
        raise ForgetRefused("--apply needs --plan-sha256 <the digest the dry run printed>: the apply refuses a plan "
                            "nobody approved. Nothing was touched.")
    # <<< guard: plan-digest-required
    # >>> guard: reason-closed-list
    if args.reason not in REASON_CODES:
        raise ForgetRefused(f"--reason must be one of {list(REASON_CODES)}; free text is refused because it would put "
                            "personal data into an append-only table. Nothing was touched.")
    # <<< guard: reason-closed-list


def render_done(committed: Committed) -> str:
    out = [f"memory-forget: {committed.cases} case(s) forgotten as {committed.forget_id}.",
           f"manifest-sha256: {committed.manifest_sha256}", f"manifest: {committed.directory / 'manifest.json'}",
           f"plan-sha256: {committed.plan_sha256}", f"rows-deleted: {committed.rows_deleted}", "",
           "Keep the plan and the manifest with the release record: the database holds only their digests.",
           "A forget does not reach:"]
    out += [f"  - {item}" for item in NOT_REACHED]
    return "\n".join(out)


def run(argv: Sequence[str] | None = None, *, out: Any = None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog="memory_forget", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--database", required=True, help="the typed name of the connected database")
    parser.add_argument("--bucket", required=True, help="the typed name of the connected bucket")
    parser.add_argument("--case", action="append", metavar="dmc_ID", help="a case identity; repeat for several")
    parser.add_argument("--origin-project", metavar="prj_ID", help="every case that came from this project (an identity, never a name)")
    parser.add_argument("--all", action="store_true", help="every case of the memory that is not forgotten yet")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="the default: print the plan, change nothing")
    mode.add_argument("--apply", action="store_true", help="forget; needs --plan-sha256")
    mode.add_argument("--resume", metavar="era_ID", help="finish a forget that committed and did not complete")
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
            selector = selector_of(args)
            if not args.apply:
                with engine.connect() as connection:
                    connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
                    plan = build_plan(connection, client, database=args.database, bucket=args.bucket, selector=selector)
                    lock_room = lock_room_for_dry_run(connection, len(plan.cases)) if plan.cases else []
                print(render_plan(plan, dry_run=True, lock_room=lock_room), file=out)
                if not plan.cases:
                    print("memory-forget: no case of that selection is left to forget; nothing to do.", file=out)
                return EXIT_OK
        with engine.connect() as connection:
            actor_uid = resolve_actor(connection, args.actor)
        permission_ref = (args.owner_permission_ref or "").strip()
        if args.resume is not None:
            committed = load_committed(engine, args.resume, args.dump_dir, actor_uid=actor_uid,
                                       permission_ref=permission_ref, out=out)
            if committed is None:
                print(f"memory-forget: {args.resume} is already complete; nothing to do.", file=out)
                return EXIT_OK
            print(f"forget-id: {committed.forget_id}", file=out, flush=True)
            finish(engine, client, committed, bucket=args.bucket, actor_uid=actor_uid, permission_ref=permission_ref, out=out)
            print(render_done(committed), file=out)
            return EXIT_OK
        committed = phase_commit(
            engine, database=args.database, bucket=args.bucket, selector=selector, expected_plan=args.plan_sha256,
            actor_uid=actor_uid, reason=args.reason, permission_ref=permission_ref, dump_dir=args.dump_dir)
        if committed is None:
            print("memory-forget: no case of that selection is left to forget; nothing to do.", file=out)
            return EXIT_OK
        print(f"forget-id: {committed.forget_id}", file=out, flush=True)
        finish(engine, client, committed, bucket=args.bucket, actor_uid=actor_uid, permission_ref=permission_ref, out=out)
        print(render_done(committed), file=out)
        return EXIT_OK
    except ForgetRefused as error:
        print(f"memory_forget: REFUSED: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except ForgetFailed as error:
        print(f"memory_forget: FAILED: {error}", file=sys.stderr)
        return EXIT_FAILED
    except Exception as error:  # noqa: BLE001 - the operator needs a status, not a traceback
        print(f"memory_forget: FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_FAILED
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(run())
