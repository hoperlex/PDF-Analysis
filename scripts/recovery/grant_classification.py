"""`PROD-04-DB-ROLES-01`: what the application role may do to each object of the schema, said once.

`api` and `worker` connect as an application role that cannot change the schema, cannot truncate
and owns nothing (`R-146n` item 1, `AD-02`, `ADR-0021` section 3). The rights it does have are not
written in a migration -- a dump taken with ``pg_dump --no-owner --no-privileges`` carries none,
and ``copy-serve.sh restore-db`` drops and recreates schema ``public`` -- but granted by one
idempotent step, ``infra/deploy/apply-grants.sh``, after every ``migrate`` and every restore.

This module is the classification that step is derived from, and the guard that keeps it whole.
It is built on :mod:`scripts.recovery.schema_coverage` -- the recovery tooling's closed
declaration of the schema at head -- and does **not** keep a second list of the schema:

* the *universe* (every base table, view, sequence, trigger function) is ``schema_coverage.TABLES``,
  ``VIEWS``, ``SEQUENCES`` and ``TRIGGERS``; a migration that adds one of them is already red in
  ``tests/integration/recovery/test_schema_coverage.py`` until that declaration is extended;
* this module adds the one decision schema_coverage does not make, *which rights* each table gets,
  as four disjoint sets that must partition ``schema_coverage.TABLES`` exactly. A table with no
  decision here is a red test (``test_grant_classification.py``), and at run time the step REFUSES a
  relation it has no row for (fail closed: no rights, and a typed refusal that stops the deploy
  before ``api`` starts).

The four classes (``ADR-0021`` section 3 names the first two; the other two are the lane's):

``read-write``   ``SELECT, INSERT, UPDATE, DELETE``. Every table the code updates or deletes from.
``append-only``  ``SELECT, INSERT``. A table the schema declares immutable or append-only by a
                 guard trigger that refuses ``UPDATE`` and ``DELETE`` (``schema_coverage.TRIGGERS``,
                 functions ``am_immutable_row``, ``am_append_only``, ``am_guard_release_append_only``,
                 ``am_norm_chunk_no_update``): the database then refuses both twice, by privilege and
                 by trigger. Also, in :data:`APPEND_ONLY_BY_CODE_EVIDENCE`, a table no trigger guards
                 but the code only ever inserts into (``project``).
``read-only``    ``SELECT``. A table the application never writes (``alembic_version``: only the
                 migrator moves the head; two reference tables seeded by a migration).
``none``         nothing. Empty today; the class exists so that a future table the application must
                 not even read (a secret held for the operator) has somewhere to be.

Two ``append-only`` tables carry one more right, on one column: ``UPDATE`` on the first primary-key
column (:data:`LOCK_ONLY_UPDATE`). ``SELECT ... FOR UPDATE`` and ``FOR NO KEY UPDATE`` need an
``UPDATE`` privilege on at least one column, and the code locks those two tables' rows. The
immutability trigger fires on a row *update*, not on a row *lock*, so the lock works and every
actual ``UPDATE`` is still refused (by the column privilege for any other column, by the trigger
for the key column).

Views are ``read-only`` (``SELECT``). Sequences follow the table that owns them: ``USAGE`` when the
owner table allows ``INSERT``, nothing otherwise. Functions: trigger functions get no grant (a
trigger fires with the *table's* privileges check, not an ``EXECUTE`` check on its function), the
two plain SQL helpers in :data:`CALLABLE_FUNCTIONS` get ``EXECUTE`` (a ``CHECK`` constraint and an
index expression call them with the *invoker's* rights), and the functions an extension installs
(pgvector) keep the ``PUBLIC`` default.

No ``ALTER DEFAULT PRIVILEGES``: a table a later migration creates gets **no** rights until it is
classified here. That is the fail-closed half of the guard; the discipline is the same as
``schema_coverage``'s.

Evidence. The ``append-only`` and ``read-only`` decisions that are not the schema's own are derived
from the repository's code, not guessed: :func:`observed_statements` reads every SQL string in
``src/auditmanager`` and reports, per table, which of ``INSERT``, ``UPDATE`` (including
``ON CONFLICT ... DO UPDATE``), ``DELETE`` and row locks the code contains. The test compares that
with the rights granted, so a statement added to the code without a decision here is red.

This module never opens a transaction of its own; :func:`audit_grant_classification` reads the
catalogue with ``SELECT`` only.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from scripts.recovery import schema_coverage as coverage

READ_WRITE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")
APPEND_ONLY_PRIVILEGES = ("SELECT", "INSERT")
READ_ONLY_PRIVILEGES = ("SELECT",)
NO_PRIVILEGES: tuple[str, ...] = ()

CLASS_PRIVILEGES = {
    "read-write": READ_WRITE_PRIVILEGES,
    "append-only": APPEND_ONLY_PRIVILEGES,
    "read-only": READ_ONLY_PRIVILEGES,
    "none": NO_PRIVILEGES,
}

#: Every privilege PostgreSQL 17 knows on a table. The check asks for all of them, so a ``TRUNCATE``,
#: a ``REFERENCES``, a ``TRIGGER`` or a ``MAINTAIN`` granted behind the step's back is a finding.
ALL_TABLE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER", "MAINTAIN")

#: ``SELECT, INSERT, UPDATE, DELETE``. Updated or deleted from by the code, or an upsert. The scan in
#: :func:`observed_statements` names the statement for each; ``tests/integration/recovery/
#: test_grant_classification.py`` holds the two together.
READ_WRITE = frozenset((
    "account_release_mark",            # INSERT ... ON CONFLICT (user_uid) DO UPDATE (releases/repository.py)
    "analysis_artifact_publication",  # INSERT, UPDATE, upsert (jobs/repository.py)
    "app_user",                       # INSERT, UPDATE, DELETE of an archived account (access/accounts.py)
    "app_user_role",                  # INSERT, DELETE on revoke (access/accounts.py)
    "attempt",
    "audit_run",
    "blob",
    "command_record",
    "document",
    "execution_control",               # singleton upsert (jobs/repository.py)
    "executor_connection",
    "executor_probe",
    "executor_runner_token",
    "executor_secret",
    "executor_task",
    "finding",
    "job",
    "lease",
    "norm_current_snapshot",          # INSERT, UPDATE (norms/current_snapshot.py)
    "norm_custody_admission",
    "norm_repair_call",
    "provider_call_effect",
    "registration_request",
    "stage_result",                   # INSERT ... ON CONFLICT (run_id, stage_id) DO UPDATE (runs/repository.py)
    "worker",
))

#: ``SELECT, INSERT``. See the module docstring; each of these either carries a guard trigger that
#: refuses ``UPDATE`` (and, but for the four ``norm_*`` ``no_update`` tables, ``DELETE``) or is
#: inserted into by the code and by nothing else.
APPEND_ONLY = frozenset((
    "ar_v3_run_group", "ar_v3_run_group_member", "audit_event", "document_version",
    "document_version_classification", "document_version_classification_correction",
    "executor_connection_revision", "executor_route_event", "expert_decision_event",
    "finding_evidence", "finding_observation", "finding_observation_norm_citation",
    "input_manifest_entry", "model_call", "norm_chunk", "norm_chunk_build",
    "norm_current_snapshot_event", "norm_custody_binding", "norm_document", "norm_embedding",
    "norm_embedding_build", "norm_paragraph", "norm_retrieval_set", "norms_snapshot",
    "optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision",
    "price_list_position", "price_list_revision", "project",
    "release", "release_revision", "vendor_list_entry", "vendor_list_revision",
    "work_assignment", "work_assignment_event",
))

#: The ``append-only`` tables that no trigger protects, and the evidence that the code only inserts.
#: Everything else in :data:`APPEND_ONLY` is declared by the schema itself.
APPEND_ONLY_BY_CODE_EVIDENCE = {
    "project": "documents/repository.py inserts a project and nothing updates or deletes one (the project erase of "
               "PROD-07 runs as the migrator)",
}

#: ``SELECT``.
READ_ONLY = frozenset((
    "alembic_version",            # only the migrator moves the head
    "contract_state_transition",  # seeded by migration 0002; the code reads the topology
    "norm_embedding_profile",     # seeded by migration 0013; no INSERT in the code
))

#: Not even ``SELECT``. Empty at head.
NONE = frozenset()

#: ``append-only`` tables that also get ``UPDATE`` on their first primary-key column, and why.
LOCK_ONLY_UPDATE = {
    "work_assignment": (
        "dispatch/repository.py _LOCK_ASSIGNMENT: SELECT assignment_uid FROM work_assignment ... FOR UPDATE; "
        "a transition serialises on its assignment row. am_immutable_row fires on UPDATE, not on a lock."
    ),
    "document_version_classification": (
        "documents/repository.py _LOCK_CLASSIFICATION: SELECT version_uid FROM document_version_classification "
        "... FOR NO KEY UPDATE; two corrections of one version serialise on the original row."
    ),
}

#: Plain SQL functions (not triggers, not an extension's) that a constraint or an index calls with the
#: invoker's rights: they are granted ``EXECUTE`` explicitly, so a ``REVOKE ... FROM PUBLIC`` somewhere
#: cannot silently break a ``CHECK``.
CALLABLE_FUNCTIONS = frozenset(("am_is_ascending_page_list", "norm_designation_tokens"))

#: Trigger functions: derived from the recovery tooling's trigger declaration, not listed again.
TRIGGER_FUNCTIONS = frozenset(function for _, _, function, _ in coverage.TRIGGERS)

#: Triggers of these functions make a table's ``UPDATE`` and ``DELETE`` refuse (BEFORE, UPDATE and
#: DELETE bits of ``tgtype``), and ``norm_chunk_no_update`` refuses ``UPDATE`` alone.
IMMUTABLE_FUNCTIONS = frozenset(coverage.GUARD_FUNCTIONS) | {"am_norm_chunk_no_update"}


class GrantClassificationRefused(ValueError):
    """The schema, the classification and the code do not describe the same application role."""


# --- the classification as data ------------------------------------------------------------------


def table_class(table: str) -> str:
    """The class of one table; a table with no decision is refused by name."""
    for name, members in _CLASSES:
        if table in members:
            return name
    raise GrantClassificationRefused(f"table {table!r} has no grant classification")


_CLASSES = (
    ("read-write", READ_WRITE),
    ("append-only", APPEND_ONLY),
    ("read-only", READ_ONLY),
    ("none", NONE),
)


def table_privileges(table: str) -> tuple[str, ...]:
    return CLASS_PRIVILEGES[table_class(table)]


def immutable_tables() -> frozenset[str]:
    """Tables the schema itself declares append-only or immutable (a guard trigger on UPDATE)."""
    return frozenset(
        table for table, _, function, mask in coverage.TRIGGERS
        if function in IMMUTABLE_FUNCTIONS and mask & 2 and mask & 16
    )


def sequence_owner_class(sequence: str) -> str:
    table, _ = coverage.SEQUENCES[sequence]
    return table_class(table)


def sequence_privileges(sequence: str) -> tuple[str, ...]:
    return ("USAGE",) if "INSERT" in table_privileges(coverage.SEQUENCES[sequence][0]) else ()


def classification_problems() -> list[str]:
    """Static consistency of the declaration against schema_coverage; empty when whole."""
    problems: list[str] = []
    sets = dict(_CLASSES)
    names = list(sets)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            both = sets[left] & sets[right]
            if both:
                problems.append(f"in both {left} and {right}: {sorted(both)}")
    union = frozenset().union(*sets.values())
    if union != coverage.TABLES:
        problems.append(
            "the classes do not partition schema_coverage.TABLES: "
            f"unclassified={sorted(coverage.TABLES - union)}, unknown={sorted(union - coverage.TABLES)}"
        )
    for table in sorted(LOCK_ONLY_UPDATE):
        if table not in APPEND_ONLY:
            problems.append(f"LOCK_ONLY_UPDATE names {table}, which is not append-only")
    # A table the schema declares immutable must never be read-write (the privilege layer would contradict the
    # trigger); an append-only table has a reason: the schema declares it, or the code only inserts.
    for table in sorted(immutable_tables() & READ_WRITE):
        problems.append(f"{table} carries an immutability trigger and is classified read-write")
    unguarded = APPEND_ONLY - immutable_tables()
    if unguarded != set(APPEND_ONLY_BY_CODE_EVIDENCE):
        problems.append(
            "append-only tables without an immutability trigger differ from APPEND_ONLY_BY_CODE_EVIDENCE: "
            f"unexplained={sorted(unguarded - set(APPEND_ONLY_BY_CODE_EVIDENCE))}, "
            f"guarded={sorted(set(APPEND_ONLY_BY_CODE_EVIDENCE) - unguarded)}"
        )
    return problems


# --- the code's evidence -------------------------------------------------------------------------

_IDENT = r"[a-z_][a-z0-9_]*"
_INSERT = re.compile(rf"\bINSERT\s+INTO\s+(?:public\.)?({_IDENT})\b", re.IGNORECASE)
_UPDATE = re.compile(rf"(?<![A-Za-z_])UPDATE\s+(?:ONLY\s+)?(?:public\.)?({_IDENT})\b(?=[^;]*?\bSET\b)", re.IGNORECASE | re.DOTALL)
_DELETE = re.compile(rf"\bDELETE\s+FROM\s+(?:ONLY\s+)?(?:public\.)?({_IDENT})\b", re.IGNORECASE)
_UPSERT = re.compile(r"\bON\s+CONFLICT\b[^;]*?\bDO\s+UPDATE\b", re.IGNORECASE | re.DOTALL)
_LOCK = re.compile(
    rf"\bFOR\s+(?:NO\s+KEY\s+UPDATE|UPDATE|KEY\s+SHARE|SHARE)\b(?:\s+OF\s+(?P<of>{_IDENT}(?:\s*,\s*{_IDENT})*))?",
    re.IGNORECASE,
)
_RELATION = re.compile(
    rf"\b(?:FROM|JOIN)\s+(?:ONLY\s+)?(?:public\.)?(?P<table>{_IDENT})(?:\s+(?:AS\s+)?(?P<alias>{_IDENT}))?",
    re.IGNORECASE,
)
_NOT_ALIASES = frozenset((
    "where", "on", "set", "join", "left", "right", "inner", "outer", "cross", "full", "natural", "for",
    "order", "group", "having", "limit", "offset", "union", "except", "intersect", "returning", "using",
    "values", "select", "lateral", "window", "fetch", "do", "from", "and", "or", "not", "as",
))


@dataclass(frozen=True, slots=True)
class Observed:
    """What the code does to one table: any of ``INSERT``, ``UPDATE``, ``DELETE``, ``LOCK``."""

    verbs: frozenset[str]
    where: tuple[str, ...]


def _statements(path: Path) -> Iterable[tuple[int, str]]:
    """Every simple statement of a module, with the string constants in it joined.

    Joined per *statement* and not per constant because the code builds a few SQL strings by ``+``
    (``"SELECT ... " + (" FOR UPDATE" if lock else "")``); a literal that is a whole statement is
    still a single constant inside it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)):
            continue
        parts = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if parts:
            yield node.lineno, " ".join(parts)


def _locked_tables(statement: str, tables: frozenset[str]) -> set[str]:
    """Tables a ``FOR UPDATE`` / ``FOR SHARE`` in the statement locks, aliases resolved."""
    found: set[str] = set()
    for lock in _LOCK.finditer(statement):
        relations = [
            (m.group("table").lower(), (m.group("alias") or "").lower())
            for m in _RELATION.finditer(statement[: lock.start()] + " ")
        ]
        relations = [(t, a if a not in _NOT_ALIASES else "") for t, a in relations]
        if lock.group("of"):
            for alias in (a.strip().lower() for a in lock.group("of").split(",")):
                matched = {t for t, a in relations if alias in (a, t)}
                found |= matched & tables
        else:
            found |= {t for t, _ in relations} & tables
    return found


def observed_statements(source_root: Path, tables: frozenset[str] | None = None) -> dict[str, Observed]:
    """For each table, the write verbs the code under ``source_root`` contains (static)."""
    names = tables if tables is not None else coverage.TABLES
    verbs: dict[str, set[str]] = {}
    where: dict[str, set[str]] = {}

    def note(table: str, verb: str, path: Path, line: int) -> None:
        if table in names:
            verbs.setdefault(table, set()).add(verb)
            where.setdefault(table, set()).add(f"{path.relative_to(source_root)}:{line} {verb}")

    for path in sorted(source_root.rglob("*.py")):
        for line, statement in _statements(path):
            for match in _INSERT.finditer(statement):
                note(match.group(1).lower(), "INSERT", path, line)
                if _UPSERT.search(statement[match.end():]):
                    note(match.group(1).lower(), "UPDATE", path, line)
            for match in _UPDATE.finditer(statement):
                note(match.group(1).lower(), "UPDATE", path, line)
            for match in _DELETE.finditer(statement):
                note(match.group(1).lower(), "DELETE", path, line)
            for table in _locked_tables(statement, frozenset(names)):
                note(table, "LOCK", path, line)
    return {t: Observed(frozenset(verbs[t]), tuple(sorted(where[t]))) for t in sorted(verbs)}


def evidence_problems(observed: dict[str, Observed]) -> list[str]:
    """Statements in the code that the classification does not allow; empty when none."""
    problems: list[str] = []
    for table in sorted(coverage.TABLES):
        granted = set(table_privileges(table))
        if table in LOCK_ONLY_UPDATE:
            granted.add("LOCK")
        if "UPDATE" in granted:
            granted.add("LOCK")
        found = observed.get(table)
        if not found:
            continue
        missing = set(found.verbs) - granted
        if missing:
            problems.append(
                f"{table} is {table_class(table)} but the code needs {sorted(missing)}: {list(found.where)}"
            )
    return problems


# --- the SQL the step runs -----------------------------------------------------------------------

_SOURCE_NOTE = "-- generated by scripts/recovery/grant_classification.py; do not edit by hand"

_APPLY = r"""
\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('statement_timeout', '120s', true);
CREATE TEMP TABLE am_class (name text PRIMARY KEY, kind text NOT NULL, privs text NOT NULL, lock_only boolean NOT NULL) ON COMMIT DROP;
INSERT INTO am_class (name, kind, privs, lock_only) VALUES
@CLASS_ROWS@;
CREATE TEMP TABLE am_callable (name text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO am_callable (name) VALUES
@CALLABLE_ROWS@;
-- 0. fail closed: a relation the classification does not name is refused before any right is granted.
DO $am$
DECLARE unknown text;
BEGIN
  SELECT string_agg(format('%s %I.%I', CASE c.relkind WHEN 'S' THEN 'sequence' WHEN 'v' THEN 'view' ELSE 'table' END,
                           n.nspname, c.relname), ', ' ORDER BY n.nspname, c.relname)
    INTO unknown
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
     AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
     AND NOT (n.nspname = 'public' AND (
           (c.relkind IN ('r', 'p') AND EXISTS (SELECT 1 FROM am_class k WHERE k.name = c.relname AND k.kind = 'table'))
        OR (c.relkind = 'v' AND EXISTS (SELECT 1 FROM am_class k WHERE k.name = c.relname AND k.kind = 'view'))
        OR (c.relkind = 'S' AND EXISTS (
              SELECT 1 FROM pg_depend d JOIN pg_class t ON t.oid = d.refobjid
                JOIN am_class k ON k.name = t.relname AND k.kind = 'table'
               WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.refclassid = 'pg_class'::regclass
                 AND d.deptype IN ('a', 'i') AND t.relnamespace = 'public'::regnamespace))));
  IF unknown IS NOT NULL THEN
    RAISE EXCEPTION '[grants_unclassified] no grant classification for: %', unknown
      USING HINT = 'add it to scripts/recovery/grant_classification.py and regenerate infra/deploy/apply-grants.sh';
  END IF;
END
$am$;
-- 1. the role: created if absent, its attributes and password set every time (a rotated password lands here).
SELECT format('CREATE ROLE %I', :'app_role') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role') \gexec
ALTER ROLE :"app_role" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
SELECT format('REVOKE %s FROM %I', m.roleid::regrole, :'app_role')
  FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member WHERE r.rolname = :'app_role' ORDER BY m.roleid::regrole::text \gexec
-- 2. the database and the schema: connect and look, never create.
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_role') \gexec
SELECT format('REVOKE CREATE ON DATABASE %I FROM %I', current_database(), :'app_role') \gexec
GRANT USAGE ON SCHEMA public TO :"app_role";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM :"app_role";
-- 3. a clean slate, then exactly the classification.
SELECT format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', :'app_role') \gexec
SELECT format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', :'app_role') \gexec
SELECT format('GRANT %s ON TABLE public.%I TO %I', k.privs, k.name, :'app_role')
  FROM am_class k WHERE k.privs <> '' AND to_regclass(format('public.%I', k.name)) IS NOT NULL ORDER BY k.name \gexec
SELECT format('GRANT UPDATE (%I) ON TABLE public.%I TO %I', a.attname, k.name, :'app_role')
  FROM am_class k
  JOIN pg_index i ON i.indrelid = to_regclass(format('public.%I', k.name)) AND i.indisprimary
  JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
 WHERE k.lock_only ORDER BY k.name \gexec
SELECT format('GRANT USAGE ON SEQUENCE public.%I TO %I', s.relname, :'app_role')
  FROM pg_class s
  JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = s.oid AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
  JOIN pg_class t ON t.oid = d.refobjid AND t.relnamespace = 'public'::regnamespace
  JOIN am_class k ON k.name = t.relname AND k.kind = 'table'
 WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace AND k.privs LIKE '%INSERT%' ORDER BY s.relname \gexec
SELECT format('GRANT EXECUTE ON FUNCTION %s TO %I', p.oid::regprocedure, :'app_role')
  FROM pg_proc p JOIN am_callable f ON f.name = p.proname
 WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f' ORDER BY p.proname \gexec
COMMIT;
"""

_CHECK = r"""
\set ON_ERROR_STOP on
WITH
cls (name, kind, privs, lock_only) AS (VALUES
@CLASS_ROWS@),
callable (name) AS (VALUES
@CALLABLE_ROWS@),
role AS (SELECT oid, rolname FROM pg_roles WHERE rolname = :'app_role'),
privileges (privilege) AS (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER'), ('MAINTAIN')),
problems (object, detail) AS (
  SELECT 'role', 'does not exist' WHERE NOT EXISTS (SELECT 1 FROM role)
  UNION ALL SELECT 'role', 'has an attribute it must not have (superuser, createdb, createrole, replication, bypassrls) or cannot log in'
    FROM pg_roles r WHERE r.rolname = :'app_role'
     AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls OR NOT r.rolcanlogin)
  UNION ALL SELECT 'role', 'is a member of ' || m.roleid::regrole::text
    FROM pg_auth_members m JOIN role ON role.oid = m.member
  UNION ALL SELECT 'schema public', 'the role can CREATE in it'
    FROM role WHERE has_schema_privilege(role.oid, 'public', 'CREATE')
  UNION ALL SELECT 'schema public', 'the role cannot USAGE it'
    FROM role WHERE NOT has_schema_privilege(role.oid, 'public', 'USAGE')
  UNION ALL SELECT 'database ' || current_database(), 'the role can CREATE in it'
    FROM role WHERE has_database_privilege(role.oid, current_database(), 'CREATE')
  UNION ALL SELECT 'database ' || current_database(), 'the role cannot CONNECT'
    FROM role WHERE NOT has_database_privilege(role.oid, current_database(), 'CONNECT')
  UNION ALL SELECT 'owner', format('the role owns %s %s', CASE c.relkind WHEN 'S' THEN 'sequence' WHEN 'v' THEN 'view' ELSE 'table' END, c.relname)
    FROM pg_class c JOIN role ON role.oid = c.relowner
  UNION ALL SELECT 'owner', 'the role owns function ' || p.proname FROM pg_proc p JOIN role ON role.oid = p.proowner
  UNION ALL SELECT 'owner', 'the role owns schema ' || n.nspname FROM pg_namespace n JOIN role ON role.oid = n.nspowner
  UNION ALL SELECT 'owner', 'the role owns database ' || d.datname FROM pg_database d JOIN role ON role.oid = d.datdba
  UNION ALL SELECT 'relation ' || n.nspname || '.' || c.relname, 'has no grant classification'
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
     AND NOT (n.nspname = 'public' AND (
           (c.relkind IN ('r', 'p') AND EXISTS (SELECT 1 FROM cls k WHERE k.name = c.relname AND k.kind = 'table'))
        OR (c.relkind = 'v' AND EXISTS (SELECT 1 FROM cls k WHERE k.name = c.relname AND k.kind = 'view'))
        OR (c.relkind = 'S' AND EXISTS (
              SELECT 1 FROM pg_depend d JOIN pg_class t ON t.oid = d.refobjid JOIN cls k ON k.name = t.relname AND k.kind = 'table'
               WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.refclassid = 'pg_class'::regclass
                 AND d.deptype IN ('a', 'i') AND t.relnamespace = 'public'::regnamespace))))
  UNION ALL SELECT k.kind || ' ' || k.name,
         CASE WHEN want THEN 'the role lacks ' ELSE 'the role holds ' END || p.privilege
    FROM (SELECT cls.*, to_regclass(format('public.%I', cls.name)) AS rel FROM cls) k
    CROSS JOIN privileges p CROSS JOIN role
    CROSS JOIN LATERAL (SELECT strpos(' ' || replace(k.privs, ',', ' ') || ' ', ' ' || p.privilege || ' ') > 0 AS want) w
   WHERE k.rel IS NOT NULL
     AND has_table_privilege(role.oid, k.rel, p.privilege) <> w.want
  UNION ALL SELECT 'table ' || k.name, 'the role has no UPDATE on its lock column ' || a.attname
    FROM (SELECT cls.*, to_regclass(format('public.%I', cls.name)) AS rel FROM cls) k
    JOIN pg_index i ON i.indrelid = k.rel AND i.indisprimary
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0] CROSS JOIN role
   WHERE k.lock_only AND NOT has_column_privilege(role.oid, k.rel, a.attname, 'UPDATE')
  UNION ALL SELECT 'table ' || k.name, 'the role can UPDATE ' || a.attname || ', which is not its lock column'
    FROM (SELECT cls.*, to_regclass(format('public.%I', cls.name)) AS rel FROM cls) k
    JOIN pg_attribute a ON a.attrelid = k.rel AND a.attnum > 0 AND NOT a.attisdropped CROSS JOIN role
   WHERE k.lock_only AND has_column_privilege(role.oid, k.rel, a.attname, 'UPDATE')
     AND a.attnum <> (SELECT i.indkey[0] FROM pg_index i WHERE i.indrelid = k.rel AND i.indisprimary)
  UNION ALL SELECT 'sequence ' || s.relname,
         CASE WHEN k.privs LIKE '%INSERT%' THEN 'the role cannot USAGE it' ELSE 'the role can USAGE it' END
    FROM pg_class s
    JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = s.oid AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
    JOIN pg_class t ON t.oid = d.refobjid AND t.relnamespace = 'public'::regnamespace
    JOIN cls k ON k.name = t.relname AND k.kind = 'table' CROSS JOIN role
   WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace
     AND has_sequence_privilege(role.oid, s.oid, 'USAGE') <> (k.privs LIKE '%INSERT%')
  UNION ALL SELECT 'sequence ' || s.relname, 'the role holds ' || p.privilege
    FROM pg_class s CROSS JOIN (VALUES ('SELECT'), ('UPDATE')) p (privilege) CROSS JOIN role
   WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace
     AND has_sequence_privilege(role.oid, s.oid, p.privilege)
  UNION ALL SELECT 'function ' || p.proname, 'the role cannot EXECUTE it'
    FROM pg_proc p JOIN callable f ON f.name = p.proname CROSS JOIN role
   WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f' AND NOT has_function_privilege(role.oid, p.oid, 'EXECUTE')
)
SELECT object || ': ' || detail FROM problems ORDER BY object, detail;
"""


def _rows(items: Iterable[str]) -> str:
    return ",\n".join(items)


def _class_rows() -> str:
    rows: list[str] = []
    for table in sorted(coverage.TABLES):
        privileges = ", ".join(table_privileges(table))
        lock = "true" if table in LOCK_ONLY_UPDATE else "false"
        rows.append(f"  ('{table}', 'table', '{privileges}', {lock})")
    for view in sorted(coverage.VIEWS):
        rows.append(f"  ('{view}', 'view', 'SELECT', false)")
    return _rows(rows)


def _callable_rows() -> str:
    return _rows(f"  ('{name}')" for name in sorted(CALLABLE_FUNCTIONS))


def render_sql(kind: str) -> str:
    """The psql script for ``apply`` or ``check``; it expects ``:app_role`` (and, for apply, ``:app_password``)."""
    template = {"apply": _APPLY, "check": _CHECK}.get(kind)
    if template is None:
        raise GrantClassificationRefused(f"unknown SQL kind {kind!r}; expected apply or check")
    body = template.replace("@CLASS_ROWS@", _class_rows()).replace("@CALLABLE_ROWS@", _callable_rows())
    return f"{_SOURCE_NOTE}\n{body.strip()}\n"


#: How `apply-grants.sh` embeds a generated block. The markers are the contract between this module and
#: the script: `verify_script` extracts what lies between them and compares it, byte for byte.
def block_markers(kind: str) -> tuple[str, str]:
    return (f"# >>> generated: {kind}-sql", f"# <<< generated: {kind}-sql")


def render_block(kind: str) -> str:
    begin, end = block_markers(kind)
    variable = "APPLY_SQL" if kind == "apply" else "CHECK_SQL"
    return f"{begin}\n{variable}=\"$(cat <<'AM_GRANTS_SQL'\n{render_sql(kind)}AM_GRANTS_SQL\n)\"\n{end}\n"


def extract_block(script_text: str, kind: str) -> str | None:
    begin, end = block_markers(kind)
    pattern = re.compile(rf"^{re.escape(begin)}\n.*?^{re.escape(end)}\n", re.DOTALL | re.MULTILINE)
    found = pattern.findall(script_text)
    return found[0] if len(found) == 1 else None


def script_drift(script_text: str) -> list[str]:
    """Which embedded blocks differ from what this module generates (empty when the script is current)."""
    drift: list[str] = []
    for kind in ("apply", "check"):
        block = extract_block(script_text, kind)
        if block is None:
            drift.append(f"{kind}: the script does not hold exactly one {block_markers(kind)[0]!r} block")
        elif block != render_block(kind):
            drift.append(f"{kind}: the embedded SQL differs from the classification")
    return drift


def write_blocks(script_text: str) -> str:
    """The script with both generated blocks replaced by the current ones."""
    result = script_text
    for kind in ("apply", "check"):
        block = extract_block(result, kind)
        if block is None:
            raise GrantClassificationRefused(f"cannot rewrite: no single {kind} block in the script")
        result = result.replace(block, render_block(kind))
    return result


# --- the catalogue against the declaration (SELECT only) -------------------------------------------

_CATALOG_RELATIONS = text("""
    SELECT n.nspname AS schema_name, c.relname AS name, c.relkind::text AS kind
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
       AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
""")
_CATALOG_SEQUENCE_OWNERS = text("""
    SELECT s.relname AS sequence, t.relname AS owner_table
      FROM pg_catalog.pg_class s
      JOIN pg_catalog.pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = s.oid
       AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
      JOIN pg_catalog.pg_class t ON t.oid = d.refobjid
     WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace
""")
_CATALOG_FUNCTIONS = text("""
    SELECT p.proname AS name, (p.prorettype = 'trigger'::regtype) AS is_trigger
      FROM pg_catalog.pg_proc p
     WHERE p.pronamespace = 'public'::regnamespace
       AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_depend d
                        WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e')
""")


def audit_grant_classification(session: Session) -> None:
    """Refuse a catalogue that holds a table, view, sequence or function with no decision.

    The same discipline as :func:`schema_coverage.audit_restored_schema`, for rights instead of
    structure. Raises :class:`GrantClassificationRefused` naming every difference at once.
    """
    problems = classification_problems()
    relations = [dict(row) for row in session.execute(_CATALOG_RELATIONS).mappings()]
    outside = sorted(f"{r['schema_name']}.{r['name']}" for r in relations if r["schema_name"] != "public")
    if outside:
        problems.append(f"relations outside schema public: {outside}")
    tables = {r["name"] for r in relations if r["schema_name"] == "public" and r["kind"] in ("r", "p")}
    views = {r["name"] for r in relations if r["schema_name"] == "public" and r["kind"] == "v"}
    sequences = {r["name"] for r in relations if r["schema_name"] == "public" and r["kind"] == "S"}
    other = sorted(r["name"] for r in relations if r["schema_name"] == "public" and r["kind"] in ("m", "f"))
    if other:
        problems.append(f"materialised or foreign relations have no classification: {other}")
    classified = frozenset().union(READ_WRITE, APPEND_ONLY, READ_ONLY, NONE)
    if tables - classified:
        problems.append(f"tables with no grant classification: {sorted(tables - classified)}")
    if classified - tables:
        problems.append(f"classified tables the catalogue does not hold: {sorted(classified - tables)}")
    if views != set(coverage.VIEWS):
        problems.append(f"views differ from schema_coverage.VIEWS: catalogue={sorted(views)}")
    owners = {row["sequence"]: row["owner_table"] for row in session.execute(_CATALOG_SEQUENCE_OWNERS).mappings()}
    unowned = sorted(sequences - set(owners))
    if unowned:
        problems.append(f"sequences owned by no table: {unowned}")
    unknown_owner = sorted(name for name, owner in owners.items() if owner not in classified)
    if unknown_owner:
        problems.append(f"sequences owned by an unclassified table: {unknown_owner}")
    declared = {name: owner for name, (owner, _) in coverage.SEQUENCES.items()}
    if {name: owners.get(name) for name in sequences} != declared:
        problems.append(
            f"sequence owners differ from schema_coverage.SEQUENCES: catalogue={sorted(owners.items())}"
        )
    functions = [dict(row) for row in session.execute(_CATALOG_FUNCTIONS).mappings()]
    triggers = {f["name"] for f in functions if f["is_trigger"]}
    plain = {f["name"] for f in functions if not f["is_trigger"]}
    if triggers != set(TRIGGER_FUNCTIONS):
        problems.append(
            "trigger functions differ from schema_coverage.TRIGGERS: "
            f"missing={sorted(set(TRIGGER_FUNCTIONS) - triggers)}, unknown={sorted(triggers - set(TRIGGER_FUNCTIONS))}"
        )
    if plain != set(CALLABLE_FUNCTIONS):
        problems.append(
            "plain functions differ from CALLABLE_FUNCTIONS: "
            f"missing={sorted(set(CALLABLE_FUNCTIONS) - plain)}, unknown={sorted(plain - set(CALLABLE_FUNCTIONS))}"
        )
    if problems:
        raise GrantClassificationRefused("; ".join(problems))


# --- command line ----------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.recovery.grant_classification")
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument("--print", dest="kind", choices=("apply", "check"), help="print the psql script")
    commands.add_argument("--verify-script", metavar="PATH", help="exit 1 if the script's embedded SQL is stale")
    commands.add_argument("--write-script", metavar="PATH", help="rewrite the script's embedded SQL in place")
    arguments = parser.parse_args(argv)
    if arguments.kind:
        sys.stdout.write(render_sql(arguments.kind))
        return 0
    target = Path(arguments.verify_script or arguments.write_script)
    original = target.read_text(encoding="utf-8")
    if arguments.verify_script:
        drift = script_drift(original)
        for line in drift:
            print(f"{target}: {line}", file=sys.stderr)
        return 1 if drift else 0
    target.write_text(write_blocks(original), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALL_TABLE_PRIVILEGES", "APPEND_ONLY", "APPEND_ONLY_BY_CODE_EVIDENCE", "CALLABLE_FUNCTIONS", "CLASS_PRIVILEGES", "GrantClassificationRefused",
    "LOCK_ONLY_UPDATE", "NONE", "Observed", "READ_ONLY", "READ_WRITE", "TRIGGER_FUNCTIONS",
    "audit_grant_classification", "block_markers", "classification_problems", "evidence_problems",
    "extract_block", "immutable_tables", "observed_statements", "render_block", "render_sql",
    "script_drift", "sequence_privileges", "table_class", "table_privileges", "write_blocks",
]
