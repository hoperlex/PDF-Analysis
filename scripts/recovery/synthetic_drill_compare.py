"""Independent source-versus-target comparison for a W58 drill (`RECOVERY-REBASE-01`).

The drill's own verdict is produced by the recovery tooling about itself: the restored
database is fingerprinted by the stand SQL and audited against the tooling's declaration, the
target objects are read back through the tooling's storage port. This module is the cross-
check that does not share that code. It reads the SOURCE and the restored TARGET read-only,
side by side, and reports every difference in:

* every base table **and every view**, by row count and a content digest (the frozen
  fingerprint SQL's own recipe, but unfiltered: the ``norm*`` tables and the custody rows the
  stand fingerprint exempts are compared here too);
* the schema's shape: column definitions, constraints, indexes, trigger definitions and
  enabled state, function bodies, view definitions, sequence positions and extensions;
* every object of the two buckets, by key, size and the SHA-256 of the bytes actually read.

Both sides must be loopback services the operator owns. The comparison writes nothing. A
difference is a finding, never repaired here.

``probe_guards`` goes one step past "the trigger exists": on the restored TARGET only, inside
one transaction that is always rolled back, it tries to UPDATE and to DELETE one real row of
every populated table that carries an immutable or append-only guard, and requires the guard's
own SQLSTATE each time. A restore that kept a trigger's name but lost its event set, or left it
disabled, is caught by the shape digests; one whose trigger does not fire is caught here.

Which operation a guard refuses is a property of its trigger, and the probe reads it from the
catalog (``pg_trigger.tgtype``) instead of assuming both. A table that is guarded on one event by
design (``_NOT_GUARDED_BY_DESIGN``: a settings row that changes state but is never deleted, an
intent that changes state and is deleted only beside a forget) is not asked to refuse the other one.
That list is the only thing that excuses an operation. The catalog never does: a trigger narrowed
from ``UPDATE OR DELETE`` to ``DELETE`` looks exactly like a guard that was always ``DELETE``-only, so
the operation stays expected, and probed, on every table the list does not name.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text

_IDENT = re.compile(r"[a-z_][a-z0-9_]*\Z")
_SESSION = (
    "SET TimeZone = 'UTC'", "SET DateStyle = 'ISO, YMD'", "SET IntervalStyle = 'postgres'",
    "SET extra_float_digits = 1", "SET bytea_output = 'hex'",
)
_RELATIONS = text("""
    SELECT c.relname AS name, c.relkind::text AS kind
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v')
     ORDER BY c.relname COLLATE "C"
""")
#: Each shape query returns text lines; the digest is over the lines sorted bytewise.
_SHAPE = {
    "columns": """
        SELECT format('%s.%s #%s %s %s %s %s', table_name, column_name, ordinal_position,
                      data_type, udt_name, is_nullable, coalesce(column_default, ''))
          FROM information_schema.columns WHERE table_schema = 'public'""",
    "constraints": """
        SELECT format('%s %s %s validated=%s', conrelid::regclass, conname,
                      pg_get_constraintdef(oid), convalidated)
          FROM pg_catalog.pg_constraint
         WHERE connamespace = 'public'::regnamespace""",
    "indexes": "SELECT indexdef FROM pg_catalog.pg_indexes WHERE schemaname = 'public'",
    "triggers": """
        SELECT format('%s %s enabled=%s', tgrelid::regclass, pg_get_triggerdef(oid), tgenabled)
          FROM pg_catalog.pg_trigger
         WHERE NOT tgisinternal AND tgrelid::regclass::text !~ '^(pg_|information_schema)'""",
    "functions": """
        SELECT pg_get_functiondef(p.oid) FROM pg_catalog.pg_proc p
         WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f'""",
    "views": """
        SELECT format('%s %s', viewname, definition) FROM pg_catalog.pg_views
         WHERE schemaname = 'public'""",
    "sequences": """
        SELECT format('%s last=%s start=%s inc=%s', sequencename, coalesce(last_value::text, '-'),
                      start_value, increment_by)
          FROM pg_catalog.pg_sequences WHERE schemaname = 'public'""",
    "extensions": "SELECT format('%s %s', extname, extversion) FROM pg_catalog.pg_extension",
}


#: ``pg_get_constraintdef`` prints a CHECK from its parse tree. ``pg_dump`` re-emits it as text and
#: the restore parses it again, and the parser **flattens** a nested ``(a AND b) AND c`` into
#: ``a AND b AND c`` (the same predicate, one level less of parentheses). Found by the first
#: rebase drill: 28 CHECK constraints print differently on the restored side and mean the same.
#: Constraints are therefore compared with parentheses and whitespace removed (the exact text is
#: kept under ``informational`` and reported, never hidden). That is looser than the truth in one
#: way, precedence changes that only move parentheses, and tighter than nothing: every name,
#: operand, operator, literal, table, validation flag and the constraint count is still compared.
_LOOSE = frozenset({"constraints"})


def _digest(lines: list[str], *, loose: bool = False) -> list[Any]:
    if loose:
        lines = [re.sub(r"[()\s]+", "", line) for line in lines]
    body = "\n".join(sorted(lines, key=lambda line: line.encode("utf-8")))
    return [len(lines), hashlib.sha256(body.encode("utf-8")).hexdigest()]


def database_profile(engine: Engine) -> dict[str, Any]:
    """Counts and digests of one database, read in one repeatable-read read-only snapshot."""
    profile: dict[str, Any] = {"tables": {}, "views": {}, "shape": {}, "informational": {}}
    with engine.connect() as connection:
        connection = connection.execution_options(isolation_level="REPEATABLE READ",
                                                  postgresql_readonly=True)
        for statement in _SESSION:
            connection.exec_driver_sql(statement)
        for row in connection.execute(_RELATIONS).mappings().all():
            name = row["name"]
            if not _IDENT.fullmatch(name):
                raise ValueError(f"relation name {name!r} is not a plain identifier")
            count, digest = connection.execute(text(
                "SELECT count(*), encode(sha256(convert_to(coalesce(string_agg(r.t, E'\\n' "
                'ORDER BY r.t COLLATE "C"), \'\'), \'UTF8\')), \'hex\') '
                f'FROM (SELECT x::text AS t FROM public."{name}" AS x) AS r'
            )).one()
            profile["views" if row["kind"] == "v" else "tables"][name] = [count, digest]
        for label, statement in _SHAPE.items():
            lines = [str(value) for (value,) in connection.execute(text(statement)).all()]
            profile["shape"][label] = _digest(lines, loose=label in _LOOSE)
            if label in _LOOSE:
                profile["informational"][f"{label}_exact_text"] = _digest(lines)
        connection.rollback()
    return profile


#: The SQLSTATEs of ``am_append_only`` (``AM002``) and ``am_immutable_row`` (``AM003``).
_GUARD_SQLSTATES = ("AM002", "AM003")
#: The report's result for an operation the table is, by design, not guarded against. It is not a finding.
_BY_DESIGN = "by_design"
#: ``pg_trigger.tgtype`` bits of the events a trigger fires on (``TRIGGER_TYPE_DELETE`` and ``TRIGGER_TYPE_UPDATE``).
_TG_DELETE, _TG_UPDATE = 8, 16
#: The operations a guarded table is NOT asked to refuse, because its schema declares it open to them: ``vector_control`` (a
#: switch row, frozen on its key and never deleted: ``am_immutable_row`` on ``DELETE`` only) and ``decision_memory_embedding_intent``
#: (an intent that changes state: its forget guard is on ``DELETE`` only). Every other guarded table refuses both operations.
_NOT_GUARDED_BY_DESIGN: dict[str, frozenset[str]] = {
    "vector_control": frozenset({"update"}),
    "decision_memory_embedding_intent": frozenset({"update"}),
}
_GUARDS = text("""
    SELECT c.relname AS name, p.proname AS guard,
           bool_or((t.tgtype & 16) <> 0) AS on_update, bool_or((t.tgtype & 8) <> 0) AS on_delete,
           c.relname COLLATE "C" AS sort_key
      FROM pg_catalog.pg_trigger t
      JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
      JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
     WHERE NOT t.tgisinternal AND c.relnamespace = 'public'::regnamespace
       AND p.proname IN ('am_immutable_row', 'am_append_only', 'am_guard_release_append_only', 'am_guard_decision_memory_forget')
     GROUP BY c.relname, p.proname
     ORDER BY sort_key, guard
""")


def probe_guards(engine: Engine) -> list[dict[str, Any]]:
    """Try to UPDATE and DELETE one row of each populated guarded table; the guard must refuse.

    Always rolled back. Run it on the restored TARGET, never on a source anyone still needs.
    A table with no row proves nothing and is reported as ``empty``, not as refused.

    An operation is probed when the guard's trigger covers it in the catalog, or when the table is not declared open to it
    (``_NOT_GUARDED_BY_DESIGN``); a declared operation the trigger does not cover is reported as ``by_design`` and not tried.
    A disabled trigger keeps its events in the catalog, so it is probed, and the write it fails to refuse is ``ACCEPTED``.
    """
    from sqlalchemy.exc import DBAPIError

    report: list[dict[str, Any]] = []
    with engine.connect() as connection:
        try:
            for row in connection.execute(_GUARDS).mappings().all():
                name = row["name"]
                if not _IDENT.fullmatch(name):
                    raise ValueError(f"table name {name!r} is not a plain identifier")
                first = connection.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' "
                    "AND table_name = :t AND is_generated = 'NEVER' AND is_identity = 'NO' "
                    "ORDER BY ordinal_position LIMIT 1"), {"t": name}).scalar_one()
                one = f'ctid = (SELECT ctid FROM public."{name}" LIMIT 1)'
                if not connection.execute(text(f'SELECT EXISTS (SELECT 1 FROM public."{name}")')).scalar_one():
                    report.append({"table": name, "guard": row["guard"], "result": "empty"})
                    continue
                for operation, covered, statement in (
                    ("update", row["on_update"], f'UPDATE public."{name}" SET "{first}" = "{first}" WHERE {one}'),
                    ("delete", row["on_delete"], f'DELETE FROM public."{name}" WHERE {one}'),
                ):
                    if not covered and operation in _NOT_GUARDED_BY_DESIGN.get(name, frozenset()):
                        report.append({"table": name, "guard": row["guard"], "operation": operation,
                                       "result": _BY_DESIGN})
                        continue
                    nested = connection.begin_nested()
                    try:
                        connection.execute(text(statement))
                        outcome = "ACCEPTED"
                    except DBAPIError as error:
                        outcome = str(getattr(error.orig, "sqlstate", "") or "error")
                    finally:
                        nested.rollback()
                    report.append({"table": name, "guard": row["guard"], "operation": operation,
                                   "result": outcome})
        finally:
            connection.rollback()
    return report


def bucket_profile(client: Any, bucket: str) -> dict[str, list[Any]]:
    """``key -> [size, sha256 of the bytes read]`` for every object of the bucket."""
    keys: list[tuple[str, int]] = []
    token: str | None = None
    while True:
        arguments: dict[str, Any] = {"Bucket": bucket}
        if token:
            arguments["ContinuationToken"] = token
        page = client.list_objects_v2(**arguments)
        keys.extend((item["Key"], item["Size"]) for item in page.get("Contents", []))
        if not page.get("IsTruncated"):
            break
        token = page["NextContinuationToken"]
    profile: dict[str, list[Any]] = {}
    for key, size in sorted(keys):
        body = client.get_object(Bucket=bucket, Key=key)["Body"]
        try:
            data = body.read()
        finally:
            body.close()
        if len(data) != size:
            raise ValueError(f"object {key!r} listed {size} bytes and delivered {len(data)}")
        profile[key] = [size, hashlib.sha256(data).hexdigest()]
    return profile


def differences(source: dict[str, Any], target: dict[str, Any], path: str = "") -> list[str]:
    """Every leaf at which the two profiles disagree, with both values."""
    found: list[str] = []
    for key in sorted(set(source) | set(target)):
        here = f"{path}/{key}"
        if key not in source or key not in target:
            found.append(f"{here}: only in {'target' if key not in source else 'source'}")
        elif isinstance(source[key], dict) and isinstance(target[key], dict):
            found.extend(differences(source[key], target[key], here))
        elif source[key] != target[key]:
            found.append(f"{here}: source {source[key]} != target {target[key]}")
    return found


def _env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and not name.startswith("#"):
            values[name] = value
    if not values["DATABASE_URL"].split("@", 1)[1].startswith("127.0.0.1:") \
            or not values["S3_ENDPOINT_URL"].startswith("http://127.0.0.1:"):
        raise ValueError("both sides must be loopback services")
    return values


def _client(values: dict[str, str]) -> Any:
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3", endpoint_url=values["S3_ENDPOINT_URL"], region_name=values["S3_REGION"],
        aws_access_key_id=values["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=values["S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def main(argv: list[str] | None = None) -> int:
    from sqlalchemy import create_engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-env", type=Path, required=True)
    parser.add_argument("--target-env", type=Path, required=True)
    parser.add_argument("--probe-target-guards", action="store_true",
                        help="also try to UPDATE/DELETE a row of every guarded table of the TARGET "
                             "(rolled back); the guards must refuse")
    args = parser.parse_args(argv)
    source, target = _env(args.source_env), _env(args.target_env)
    if (source["DATABASE_URL"], source["S3_BUCKET"]) == (target["DATABASE_URL"], target["S3_BUCKET"]):
        parser.exit(2, "source and target are the same database and bucket\n")
    profiles = []
    for values in (source, target):
        engine = create_engine(values["DATABASE_URL"])
        try:
            profiles.append({
                "database": database_profile(engine),
                "objects": bucket_profile(_client(values), values["S3_BUCKET"]),
            })
        finally:
            engine.dispose()
    informational = differences(profiles[0]["database"]["informational"],
                                profiles[1]["database"]["informational"])
    for profile in profiles:
        del profile["database"]["informational"]
    found = differences(profiles[0], profiles[1])
    probe: list[dict[str, Any]] = []
    if args.probe_target_guards:
        engine = create_engine(target["DATABASE_URL"])
        try:
            probe = probe_guards(engine)
        finally:
            engine.dispose()
        found += [f"/guard_probe/{item['table']}/{item.get('operation', '-')}: {item['result']}"
                  for item in probe if item["result"] not in (*_GUARD_SQLSTATES, "empty", _BY_DESIGN)]
    summary = {
        "guard_probe": {
            "tables": len({item["table"] for item in probe}),
            "refused": sum(item["result"] in _GUARD_SQLSTATES for item in probe),
            "empty_tables": sorted(item["table"] for item in probe if item["result"] == "empty"),
            "by_design": sorted(f"{item['table']}/{item['operation']}" for item in probe
                                if item["result"] == _BY_DESIGN),
            "accepted_or_other": [item for item in probe
                                  if item["result"] not in (*_GUARD_SQLSTATES, "empty", _BY_DESIGN)],
        } if args.probe_target_guards else None,
        "informational": informational,
        "tables": len(profiles[0]["database"]["tables"]),
        "table_rows": sum(count for count, _ in profiles[0]["database"]["tables"].values()),
        "views": len(profiles[0]["database"]["views"]),
        "shape_categories": len(profiles[0]["database"]["shape"]),
        "objects": len(profiles[0]["objects"]),
        "object_bytes": sum(size for size, _ in profiles[0]["objects"].values()),
        "differences": found,
    }
    print(json.dumps(summary, sort_keys=True, indent=1, ensure_ascii=False))
    return 0 if not found else 3


if __name__ == "__main__":
    sys.exit(main())
