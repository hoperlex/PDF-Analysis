"""PROD-04-DB-ROLES-01: the application role can do what the contexts do, and nothing that changes the schema.

Every test runs ``infra/deploy/apply-grants.sh`` -- the shipped script, not a re-statement of its SQL --
against a PRIVATE clone of the migrated template, in the lane's real PostgreSQL. ``docker`` is a shim that
turns ``docker compose ... exec -T postgres psql ARGS`` into the host's ``psql ARGS`` against the lane
cluster, so what is exercised is the script's own guards, its stdin protocol and its SQL. The application
role has a unique name per test and is dropped afterwards, after its rights in the clone are; nothing is left
in the cluster (``test_nothing_is_left_behind`` asserts it for the whole module).

What is shown, in the order the task lists it:

(a) the role can do the CRUD the contexts do -- on a statement per class, with the real tables;
(b) it cannot CREATE, DROP, ALTER, TRUNCATE or take ownership of anything, nor grant, nor become another role;
(c) append-only tables refuse UPDATE and DELETE for it twice -- by privilege and, once the privilege is
    forced on, by the trigger;
(d) the step is idempotent: a second run leaves every ACL and every role attribute as the first left it;
(e) a database restored from a ``pg_dump --no-owner --no-privileges`` dump, in the two shapes the repository's
    restore paths produce, has no rights until the step runs and has exactly the rights after it.

Then the premise the migrator decision rests on, the end-to-end fail-closed case (a migration copy that adds
a table), a mutation proof per kind of difference ``--check`` reports, and the password rotation.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import stat
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from psycopg import errors
from sqlalchemy.engine import URL

from auditmanager.shared.db.config import DatabaseSettings
from scripts.recovery import grant_classification as grants
from scripts.recovery import schema_coverage as coverage

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra/deploy"

SHIM = r"""#!/usr/bin/env bash
# docker compose --env-file F --file C exec -T postgres psql ARGS  ->  the host's psql against the lane cluster.
if [ "${1:-}" = compose ] && [ "${6:-}" = exec ] && [ "${7:-}" = -T ] && [ "${8:-}" = postgres ] && [ "${9:-}" = psql ]; then
    shift 9
    exec psql -h "$SHIM_PGHOST" -p "$SHIM_PGPORT" "$@"
fi
echo "docker shim: unsupported call: $*" >&2
exit 99
"""

#: Roles this module created, dropped by the fixtures and checked by ``test_nothing_is_left_behind``.
_CREATED_ROLES: list[str] = []


def _cluster(settings: DatabaseSettings) -> URL:
    return settings.url


def _connect(url: URL, *, database: str | None = None, user: str | None = None,
             password: str | None = None, autocommit: bool = True) -> psycopg.Connection:
    return psycopg.connect(
        host=url.host, port=url.port, dbname=database or url.database,
        user=user or url.username, password=password if user else url.password,
        autocommit=autocommit,
    )


@dataclass
class Stand:
    """One private clone, one environment file, the shipped script, and the application role's name."""

    cluster: URL
    database: str
    role: str
    password: str
    root: Path
    owner_password: str
    databases: list[str]

    @property
    def script(self) -> Path:
        return self.root / "infra/deploy/apply-grants.sh"

    @property
    def env_file(self) -> Path:
        return self.root / "infra/deploy/env/alpha.env"

    def write_env(self, *, database: str | None = None, app_password: str | None = None,
                  extra: dict[str, str] | None = None, drop: tuple[str, ...] = ()) -> None:
        database = database or self.database
        password = app_password if app_password is not None else self.password
        owner = self.cluster.username
        values = {
            "ALPHA_INSTANCE": "prod04-test",
            "POSTGRES_DB": database,
            "POSTGRES_USER": owner,
            "POSTGRES_PASSWORD": self.owner_password,
            "ALPHA_APP_DB_USER": self.role,
            "ALPHA_APP_DB_PASSWORD": password,
            "DATABASE_URL": f"postgresql+psycopg://{self.role}:{password}@postgres:5432/{database}",
            "MIGRATOR_DATABASE_URL": f"postgresql+psycopg://{owner}:{self.owner_password}@postgres:5432/{database}",
        }
        values.update(extra or {})
        for name in drop:
            values.pop(name, None)
        self.env_file.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PATH"] = f"{self.root / 'bin'}{os.pathsep}{environment['PATH']}"
        environment["SHIM_PGHOST"] = str(self.cluster.host)
        environment["SHIM_PGPORT"] = str(self.cluster.port)
        environment["PGPASSWORD"] = self.owner_password
        return subprocess.run(
            [str(self.script), "--env-file", str(self.env_file), *args],
            capture_output=True, text=True, env=environment, timeout=120, check=False,
        )

    def apply(self) -> subprocess.CompletedProcess[str]:
        done = self.run()
        assert done.returncode == 0, f"apply-grants.sh exited {done.returncode}\n{done.stdout}\n{done.stderr}"
        return done

    def app(self, *, database: str | None = None, autocommit: bool = False) -> psycopg.Connection:
        return _connect(self.cluster, database=database or self.database, user=self.role,
                        password=self.password, autocommit=autocommit)

    def owner(self, *, database: str | None = None, autocommit: bool = True) -> psycopg.Connection:
        return _connect(self.cluster, database=database or self.database, autocommit=autocommit)


def _drop_role(cluster: URL, role: str, databases: list[str]) -> None:
    """Take the role's rights out of every database it was granted in, then the role."""
    for database in databases:
        try:
            with _connect(cluster, database=database) as connection:
                if connection.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                    connection.execute(f'DROP OWNED BY "{role}"')
        except psycopg.OperationalError:
            continue  # the database is already gone, and its rights with it
    with _connect(cluster, database="postgres") as connection:
        connection.execute(f'DROP ROLE IF EXISTS "{role}"')


@pytest.fixture
def stand(
    tmp_path: Path, configured_settings: DatabaseSettings,
    migrated_database_factory: Callable[[], DatabaseSettings],
) -> Iterator[Stand]:
    clone = migrated_database_factory()
    cluster = _cluster(configured_settings)
    root = tmp_path / "stand"
    (root / "infra/deploy/env").mkdir(parents=True)
    (root / "bin").mkdir()
    shutil.copy2(DEPLOY / "apply-grants.sh", root / "infra/deploy/apply-grants.sh")
    shutil.copy2(DEPLOY / "compose.server.yml", root / "infra/deploy/compose.server.yml")
    shim = root / "bin/docker"
    shim.write_text(SHIM, encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    role = f"prod04_app_{secrets.token_hex(4)}"
    _CREATED_ROLES.append(role)
    built = Stand(
        cluster=cluster, database=str(clone.url.database), role=role, password=secrets.token_hex(16),
        root=root, owner_password=str(cluster.password), databases=[str(clone.url.database)],
    )
    built.write_env()
    try:
        yield built
    finally:
        _drop_role(cluster, role, built.databases)
        _CREATED_ROLES.remove(role)


@pytest.fixture
def applied(stand: Stand) -> Stand:
    stand.apply()
    return stand


def _acl_snapshot(connection: psycopg.Connection, role: str) -> list[tuple[object, ...]]:
    """Every ACL and attribute the step can touch (not the password verifier: it is re-salted by design)."""
    rows = connection.execute("""
        SELECT 'relation', c.relname, c.relacl::text,
               (SELECT string_agg(a.attname || '=' || a.attacl::text, ',' ORDER BY a.attnum)
                  FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attacl IS NOT NULL)
          FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'v', 'S')
        UNION ALL SELECT 'schema', nspname, nspacl::text, NULL FROM pg_namespace WHERE nspname = 'public'
        UNION ALL SELECT 'database', datname, datacl::text, NULL FROM pg_database WHERE datname = current_database()
        UNION ALL SELECT 'function', proname, proacl::text, NULL FROM pg_proc
                   WHERE pronamespace = 'public'::regnamespace AND proname = ANY (%s)
        UNION ALL SELECT 'role', rolname,
                   concat_ws(',', rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolreplication, rolbypassrls, rolinherit,
                             rolconnlimit), NULL FROM pg_roles WHERE rolname = %s
        ORDER BY 1, 2
    """, (sorted(grants.CALLABLE_FUNCTIONS), role)).fetchall()
    return [tuple(row) for row in rows]


# --- (a) the CRUD the contexts do ------------------------------------------------------------------


def test_the_adr_row_7_query_prints_f_f_f_t(applied: Stand) -> None:
    """``ADR-0021`` row 7, verbatim, with the migrator's connection."""
    with applied.owner() as owner:
        row = owner.execute("""
            select rolsuper, has_schema_privilege(rolname,'public','CREATE'),
                   has_table_privilege(rolname,'public.audit_event','DELETE'),
                   has_table_privilege(rolname,'public.audit_event','INSERT')
              from pg_roles where rolname = %s
        """, (applied.role,)).fetchone()
    assert row == (False, False, False, True)


def test_the_step_verifies_what_it_applied(applied: Stand) -> None:
    done = applied.run("--check")
    assert done.returncode == 0, done.stderr
    assert f"grants-ok: {applied.role} on {applied.database}" in done.stdout


def test_the_application_role_does_the_crud_the_contexts_do(applied: Stand) -> None:
    event = "evt_" + "0123456789ABCDEFGHJKMNPQRS"
    project = "prj_" + "0123456789ABCDEFGHJKMNPQRS"
    with applied.app() as connection:  # one transaction, rolled back: the shared lane is not written
        # append-only: SELECT and INSERT (the identity sequence of audit_event is used implicitly)
        connection.execute("INSERT INTO project (project_uid, name) VALUES (%s, %s)", (project, "p"))
        connection.execute(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
            "VALUES (%s, 'access.grant_test', 'Account', %s, '{}'::jsonb)", (event, project),
        )
        assert connection.execute("SELECT count(*) FROM project WHERE project_uid = %s", (project,)).fetchone() == (1,)
        assert connection.execute("SELECT sequence_no > 0 FROM audit_event WHERE audit_event_id = %s", (event,)).fetchone() == (True,)
        # read-write: UPDATE, DELETE, INSERT, and the upsert of a singleton
        connection.execute("UPDATE execution_control SET paused = paused")
        connection.execute(
            "INSERT INTO execution_control (singleton, paused) VALUES (true, false) "
            "ON CONFLICT (singleton) DO UPDATE SET paused = EXCLUDED.paused"
        )
        deleted = connection.execute("DELETE FROM app_user_role WHERE role = 'expert' RETURNING user_uid").fetchall()
        assert len(deleted) == 1, "the migration's own admin account holds the expert role"
        connection.execute("INSERT INTO app_user_role (user_uid, role) VALUES (%s, 'expert')", (deleted[0][0],))
        # read-only and a view and a sequence
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (coverage.HEAD,)
        connection.execute("SELECT count(*) FROM contract_state_transition").fetchone()
        connection.execute("SELECT count(*) FROM finding_current_verdict").fetchone()
        assert connection.execute("SELECT nextval('audit_event_sequence_no_seq')").fetchone()[0] > 0
        # row locks: the two append-only tables the code locks, and a read-write one
        connection.execute("SELECT assignment_uid FROM work_assignment FOR UPDATE").fetchall()
        connection.execute("SELECT version_uid FROM document_version_classification FOR NO KEY UPDATE").fetchall()
        connection.execute("SELECT job_id FROM job FOR UPDATE SKIP LOCKED").fetchall()
        # the SQL helper a CHECK calls, and pgvector's operator (the extension keeps its PUBLIC default)
        assert connection.execute("SELECT am_is_ascending_page_list(ARRAY[1, 2, 3], 3)").fetchone() == (True,)
        assert connection.execute("SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector > 0").fetchone() == (True,)
        connection.rollback()


def test_the_privileges_are_exactly_the_classification(applied: Stand) -> None:
    """Not a sample: every table, view and sequence, every privilege PostgreSQL knows."""
    with applied.owner() as owner:
        def has(table: str, privilege: str) -> bool:
            row = owner.execute("SELECT has_table_privilege(%s::name, %s::regclass, %s)", (applied.role, f"public.{table}", privilege)).fetchone()
            assert row is not None
            return bool(row[0])

        for table in sorted(coverage.TABLES):
            held = {p for p in grants.ALL_TABLE_PRIVILEGES if has(table, p)}
            assert held == set(grants.table_privileges(table)), (table, grants.table_class(table), sorted(held))
        for view in sorted(coverage.VIEWS):
            assert {p for p in grants.ALL_TABLE_PRIVILEGES if has(view, p)} == {"SELECT"}, view
        for sequence, (table, _column) in sorted(coverage.SEQUENCES.items()):
            usage = owner.execute("SELECT has_sequence_privilege(%s::name, %s::regclass, 'USAGE'), has_sequence_privilege(%s::name, %s::regclass, 'UPDATE')",
                                  (applied.role, sequence, applied.role, sequence)).fetchone()
            assert usage == ("INSERT" in grants.table_privileges(table), False), sequence
        for table in grants.LOCK_ONLY_UPDATE:
            columns = owner.execute(
                "SELECT a.attname FROM pg_attribute a WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped "
                "AND has_column_privilege(%s::name, a.attrelid, a.attname, 'UPDATE')", (f"public.{table}", applied.role),
            ).fetchall()
            assert len(columns) == 1, (table, columns)
        owned = owner.execute("""
            SELECT (SELECT count(*) FROM pg_class WHERE relowner = r.oid) + (SELECT count(*) FROM pg_proc WHERE proowner = r.oid)
                 + (SELECT count(*) FROM pg_namespace WHERE nspowner = r.oid) + (SELECT count(*) FROM pg_database WHERE datdba = r.oid)
                 + (SELECT count(*) FROM pg_auth_members WHERE member = r.oid)
              FROM pg_roles r WHERE r.rolname = %s""", (applied.role,)).fetchone()
        assert owned == (0,), "the role owns nothing and is a member of nothing"


# --- (b) what it cannot do ---------------------------------------------------------------------------

_SCHEMA_CHANGES = {
    "create table": "CREATE TABLE zz_new (id int)",
    "create table as": "CREATE TABLE zz_new AS SELECT 1 AS id",
    "create schema": "CREATE SCHEMA zz_schema",
    "create view": "CREATE VIEW zz_view AS SELECT 1 AS one",
    "create index": "CREATE INDEX zz_index ON project (name)",
    "create function": "CREATE FUNCTION zz_fn() RETURNS int LANGUAGE sql AS 'SELECT 1'",
    "create type": "CREATE TYPE zz_type AS ENUM ('a')",
    "create sequence": "CREATE SEQUENCE zz_seq",
    "create extension": "CREATE EXTENSION pgcrypto",
    "create database": "CREATE DATABASE zz_database",
    "create role": "CREATE ROLE zz_role",
    "drop table": "DROP TABLE project",
    "drop view": "DROP VIEW finding_current_verdict",
    "drop function": "DROP FUNCTION am_is_ascending_page_list(integer[], integer)",
    "drop schema": "DROP SCHEMA public CASCADE",
    "alter table": "ALTER TABLE project ADD COLUMN zz int",
    "alter table drop column": "ALTER TABLE project DROP COLUMN name",
    "alter column type": "ALTER TABLE project ALTER COLUMN name TYPE varchar(5)",
    "alter table owner": "ALTER TABLE project OWNER TO CURRENT_USER",
    "disable trigger": "ALTER TABLE audit_event DISABLE TRIGGER trg_audit_event_append_only",
    "drop trigger": "DROP TRIGGER trg_audit_event_append_only ON audit_event",
    "drop constraint": "ALTER TABLE project DROP CONSTRAINT ck_project_name_length",
    "drop primary key": "ALTER TABLE project DROP CONSTRAINT project_pkey",
    "alter sequence": "ALTER SEQUENCE audit_event_sequence_no_seq RESTART",
    "comment": "COMMENT ON TABLE project IS 'x'",
    "make itself superuser": "ALTER ROLE CURRENT_USER SUPERUSER",
    "take createdb": "ALTER ROLE CURRENT_USER CREATEDB",
    "set a sequence": "SELECT setval('audit_event_sequence_no_seq', 1)",
    "become the owner": "SET ROLE @OWNER@",
    "create a policy": "CREATE POLICY zz ON project USING (true)",
    "reindex": "REINDEX TABLE project",
}


@pytest.mark.parametrize("statement", sorted(_SCHEMA_CHANGES))
def test_the_application_role_cannot_change_the_schema(applied: Stand, statement: str) -> None:
    sql = _SCHEMA_CHANGES[statement].replace("@OWNER@", f'"{applied.cluster.username}"')
    with applied.app(autocommit=True) as connection:
        before = connection.execute("SELECT count(*) FROM pg_class WHERE relnamespace = 'public'::regnamespace").fetchone()
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute(sql)
        after = connection.execute("SELECT count(*) FROM pg_class WHERE relnamespace = 'public'::regnamespace").fetchone()
        assert before == after
    with applied.owner() as owner:
        assert owner.execute("SELECT to_regclass('public.zz_new'), to_regclass('public.zz_view'), to_regclass('public.zz_seq')").fetchone() == (None, None, None)


@pytest.mark.parametrize("statement", [
    "GRANT ALL ON TABLE project TO PUBLIC",
    "GRANT TRUNCATE ON TABLE project TO CURRENT_USER",
    "GRANT UPDATE ON TABLE audit_event TO CURRENT_USER",
    "GRANT SELECT ON TABLE job TO PUBLIC WITH GRANT OPTION",
    "REVOKE SELECT ON TABLE project FROM PUBLIC",
    "REVOKE ALL ON TABLE job FROM CURRENT_USER",
    "GRANT CREATE ON SCHEMA public TO CURRENT_USER",
    "GRANT pg_read_all_data TO CURRENT_USER",
])
def test_the_application_role_cannot_change_a_privilege(applied: Stand, statement: str) -> None:
    """A GRANT by a role without the grant option is, for PostgreSQL, a warning rather than an error in some
    shapes -- so the proof is that no ACL anywhere moved, not that an exception was raised."""
    with applied.owner() as owner:
        before = _acl_snapshot(owner, applied.role)
        public_before = owner.execute("SELECT relacl::text FROM pg_class WHERE relname IN ('project', 'job', 'audit_event') ORDER BY relname").fetchall()
        memberships_before = owner.execute("SELECT count(*) FROM pg_auth_members").fetchone()
    with applied.app(autocommit=True) as connection:
        try:
            connection.execute(statement)
        except psycopg.errors.DatabaseError:
            pass  # refused outright, which is also fine
    with applied.owner() as owner:
        assert _acl_snapshot(owner, applied.role) == before
        assert owner.execute("SELECT relacl::text FROM pg_class WHERE relname IN ('project', 'job', 'audit_event') ORDER BY relname").fetchall() == public_before
        assert owner.execute("SELECT count(*) FROM pg_auth_members").fetchone() == memberships_before


def test_the_application_role_cannot_truncate_any_table(applied: Stand) -> None:
    """All 76, read-write ones included: ``TRUNCATE`` is the one privilege no class carries."""
    refused: list[str] = []
    with applied.app(autocommit=True) as connection:
        for table in sorted(coverage.TABLES):
            with pytest.raises(errors.InsufficientPrivilege):
                connection.execute(f'TRUNCATE TABLE "{table}"')
            refused.append(table)
    assert refused == sorted(coverage.TABLES) and len(refused) == 76  # 0038: the nine comparison tables (0037: analysis_preset_revision; 0035: comparison_sheet_link, comparison_summary)


# --- (c) append-only is refused twice ------------------------------------------------------------------


def _first_column(connection: psycopg.Connection, table: str, *, exclude: str | None = None) -> str:
    row = connection.execute(
        "SELECT attname FROM pg_attribute WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped "
        "AND attidentity = '' AND attgenerated = '' "
        "AND (%s::text IS NULL OR attname <> %s::text) ORDER BY attnum LIMIT 1", (f"public.{table}", exclude, exclude),
    ).fetchone()
    assert row is not None
    return str(row[0])


def test_append_only_tables_refuse_update_and_delete_by_privilege(applied: Stand) -> None:
    checked: list[str] = []
    with applied.owner() as owner, applied.app(autocommit=True) as connection:
        for table in sorted(grants.APPEND_ONLY):
            key = None
            if table in grants.LOCK_ONLY_UPDATE:
                row = owner.execute(
                    "SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0] "
                    "WHERE i.indrelid = %s::regclass AND i.indisprimary", (f"public.{table}",)).fetchone()
                assert row is not None
                key = str(row[0])
            column = _first_column(owner, table, exclude=key)
            with pytest.raises(errors.InsufficientPrivilege):
                connection.execute(f'UPDATE "{table}" SET "{column}" = "{column}" WHERE false')
            with pytest.raises(errors.InsufficientPrivilege):
                connection.execute(f'DELETE FROM "{table}" WHERE false')
            checked.append(table)
    assert checked == sorted(grants.APPEND_ONLY) and len(checked) == len(grants.APPEND_ONLY) == 40  # 0038: comparison_version_order (0037)


def test_read_only_tables_refuse_every_write(applied: Stand) -> None:
    with applied.owner() as owner, applied.app(autocommit=True) as connection:
        for table in sorted(grants.READ_ONLY):
            column = _first_column(owner, table)
            for statement in (f'UPDATE "{table}" SET "{column}" = "{column}"', f'DELETE FROM "{table}"',
                              f'INSERT INTO "{table}" SELECT * FROM "{table}"'):
                with pytest.raises(errors.InsufficientPrivilege):
                    connection.execute(statement)


def test_a_lock_only_table_can_be_locked_and_cannot_be_updated(applied: Stand) -> None:
    with applied.owner() as owner:
        others = {t: _first_column(owner, t, exclude=k) for t, k in
                  (("work_assignment", "assignment_uid"), ("document_version_classification", "version_uid"))}
    with applied.app(autocommit=False) as connection:
        for table, key in (("work_assignment", "assignment_uid"), ("document_version_classification", "version_uid")):
            other = others[table]
            connection.execute(f'SELECT "{key}" FROM "{table}" FOR UPDATE').fetchall()
            connection.execute(f'SELECT "{key}" FROM "{table}" FOR NO KEY UPDATE').fetchall()
            with pytest.raises(errors.InsufficientPrivilege):
                connection.execute(f'UPDATE "{table}" SET "{other}" = "{other}"')
            connection.rollback()
            assert table in grants.LOCK_ONLY_UPDATE


def test_a_second_wall_the_trigger_refuses_even_a_privilege_forced_on(applied: Stand) -> None:
    """``audit_event`` has a row (the application's own insert); give the role UPDATE and DELETE by hand and the
    trigger still refuses -- the 'twice' of ``ADR-0021`` section 3. The step then takes the privileges away."""
    event = "evt_" + "0123456789ABCDEFGHJKMNPQRT"
    aggregate = "prj_" + "0123456789ABCDEFGHJKMNPQRT"
    with applied.app(autocommit=True) as connection:
        connection.execute(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
            "VALUES (%s, 'access.grant_test', 'Account', %s, '{}'::jsonb)", (event, aggregate))
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("UPDATE audit_event SET event_type = 'access.other' WHERE audit_event_id = %s", (event,))
        with applied.owner() as owner:
            owner.execute(f'GRANT UPDATE, DELETE ON audit_event TO "{applied.role}"')
        for statement in ("UPDATE audit_event SET event_type = 'access.other' WHERE audit_event_id = %s",
                          "DELETE FROM audit_event WHERE audit_event_id = %s"):
            with pytest.raises(psycopg.errors.DatabaseError) as raised:
                connection.execute(statement, (event,))
            assert not isinstance(raised.value, errors.InsufficientPrivilege), "the privilege was forced on"
            assert raised.value.sqlstate == "AM002" and "append-only" in str(raised.value)
    drift = applied.run("--check")
    assert drift.returncode == 1 and "table audit_event: the role holds UPDATE" in drift.stderr
    applied.apply()
    with applied.app(autocommit=True) as connection, pytest.raises(errors.InsufficientPrivilege):
        connection.execute("DELETE FROM audit_event WHERE audit_event_id = %s", (event,))


# --- (d) idempotence ------------------------------------------------------------------------------------


def test_the_second_run_changes_nothing(applied: Stand) -> None:
    with applied.owner() as owner:
        first = _acl_snapshot(owner, applied.role)
    applied.apply()
    applied.apply()
    with applied.owner() as owner:
        second = _acl_snapshot(owner, applied.role)
    assert first == second
    assert len(first) > 70, "the snapshot covers every relation, the schema, the database, the helpers and the role"
    assert any(row[0] == "role" and row[2].startswith("f,f,f,t,f,f") for row in first), "no superuser, createdb, createrole; login; no replication, bypassrls"


def test_the_snapshot_would_see_a_change(applied: Stand) -> None:
    """The mutation proof of the test above: a privilege granted by hand changes the snapshot."""
    with applied.owner() as owner:
        before = _acl_snapshot(owner, applied.role)
        owner.execute(f'GRANT UPDATE ON project TO "{applied.role}"')
        assert _acl_snapshot(owner, applied.role) != before
        owner.execute(f'ALTER ROLE "{applied.role}" CREATEDB')
        assert [r for r in _acl_snapshot(owner, applied.role) if r[0] == "role"] != [r for r in before if r[0] == "role"]


def test_the_step_repairs_whatever_was_changed_by_hand(applied: Stand) -> None:
    with applied.owner() as owner:
        before = _acl_snapshot(owner, applied.role)
        for sql in (f'GRANT TRUNCATE ON audit_event TO "{applied.role}"', f'GRANT ALL ON schema public TO "{applied.role}"',
                    f'ALTER ROLE "{applied.role}" SUPERUSER', f'REVOKE SELECT ON job FROM "{applied.role}"',
                    f'GRANT pg_read_all_data TO "{applied.role}"'):
            owner.execute(sql)
    assert applied.run("--check").returncode == 1
    applied.apply()
    with applied.owner() as owner:
        assert _acl_snapshot(owner, applied.role) == before
        assert owner.execute("SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member WHERE r.rolname = %s",
                             (applied.role,)).fetchone() == (0,)


# --- --check: a mutation proof per kind of difference ------------------------------------------------------

_TAMPERING = {
    "a TRUNCATE on a table": ("GRANT TRUNCATE ON audit_event TO {role}", "table audit_event: the role holds TRUNCATE"),
    "an UPDATE on an append-only table": ("GRANT UPDATE ON project TO {role}", "table project: the role holds UPDATE"),
    "a DELETE on an append-only table": ("GRANT DELETE ON model_call TO {role}", "table model_call: the role holds DELETE"),
    "a missing SELECT": ("REVOKE SELECT ON job FROM {role}", "table job: the role lacks SELECT"),
    "a missing INSERT": ("REVOKE INSERT ON audit_event FROM {role}", "table audit_event: the role lacks INSERT"),
    "a write on a read-only table": ("GRANT INSERT ON alembic_version TO {role}", "table alembic_version: the role holds INSERT"),
    "a REFERENCES privilege": ("GRANT REFERENCES ON project TO {role}", "table project: the role holds REFERENCES"),
    "a TRIGGER privilege": ("GRANT TRIGGER ON project TO {role}", "table project: the role holds TRIGGER"),
    "a write on a view": ("GRANT UPDATE ON finding_current_verdict TO {role}", "view finding_current_verdict: the role holds UPDATE"),
    "a missing view": ("REVOKE SELECT ON finding_current_verdict FROM {role}", "view finding_current_verdict: the role lacks SELECT"),
    "a second column of a lock-only table": ("GRANT UPDATE (project_uid) ON work_assignment TO {role}",
                                             "table work_assignment: the role can UPDATE project_uid"),
    "a lost lock column": ("REVOKE UPDATE (assignment_uid) ON work_assignment FROM {role}",
                           "table work_assignment: the role has no UPDATE on its lock column assignment_uid"),
    "a sequence it may not set": ("GRANT UPDATE ON SEQUENCE audit_event_sequence_no_seq TO {role}",
                                  "sequence audit_event_sequence_no_seq: the role holds UPDATE"),
    "a lost sequence": ("REVOKE USAGE ON SEQUENCE audit_event_sequence_no_seq FROM {role}",
                        "sequence audit_event_sequence_no_seq: the role cannot USAGE it"),
    "CREATE on the schema": ("GRANT CREATE ON SCHEMA public TO {role}", "schema public: the role can CREATE in it"),
    "no USAGE on the schema": ("REVOKE USAGE ON SCHEMA public FROM {role}, PUBLIC", "schema public: the role cannot USAGE it"),
    "CREATE on the schema through PUBLIC": ("GRANT CREATE ON SCHEMA public TO PUBLIC", "schema public: the role can CREATE in it"),
    "CREATE on the database": ("GRANT CREATE ON DATABASE {database} TO {role}", "the role can CREATE in it"),
    "no CONNECT": ("REVOKE CONNECT ON DATABASE {database} FROM {role}, PUBLIC", "the role cannot CONNECT"),
    "superuser": ("ALTER ROLE {role} SUPERUSER", "role: has an attribute it must not have"),
    "createrole": ("ALTER ROLE {role} CREATEROLE", "role: has an attribute it must not have"),
    "no login": ("ALTER ROLE {role} NOLOGIN", "role: has an attribute it must not have"),
    "a membership": ("GRANT pg_read_all_data TO {role}", "role: is a member of pg_read_all_data"),
    "a table it owns": ("ALTER TABLE project OWNER TO {role}", "owner: the role owns table project"),
    "a function it owns": ("ALTER FUNCTION am_is_ascending_page_list(integer[], integer) OWNER TO {role}",
                           "owner: the role owns function am_is_ascending_page_list"),
    "a lost helper": ("REVOKE EXECUTE ON FUNCTION am_is_ascending_page_list(integer[], integer) FROM {role}, PUBLIC",
                      "function am_is_ascending_page_list: the role cannot EXECUTE it"),
    "a table nobody classified": ("CREATE TABLE zz_unclassified (a int)", "relation public.zz_unclassified: has no grant classification"),
    "a sequence nobody classified": ("CREATE SEQUENCE zz_unclassified_seq", "relation public.zz_unclassified_seq: has no grant classification"),
    "a view nobody classified": ("CREATE VIEW zz_unclassified_view AS SELECT 1", "relation public.zz_unclassified_view: has no grant classification"),
    "a relation in another schema": ("CREATE SCHEMA zz_other; CREATE TABLE zz_other.t (a int)", "relation zz_other.t: has no grant classification"),
}


@pytest.mark.parametrize("tampering", sorted(_TAMPERING))
def test_check_reports_each_kind_of_difference_and_the_step_repairs_it(applied: Stand, tampering: str) -> None:
    sql, expected = _TAMPERING[tampering]
    unclassified = tampering.endswith("nobody classified") or "another schema" in tampering
    ownership = tampering.endswith("it owns")
    with applied.owner() as owner:
        for part in sql.format(role=f'"{applied.role}"', database=f'"{applied.database}"').split("; "):
            owner.execute(part)
    found = applied.run("--check")
    assert found.returncode == 1, (found.stdout, found.stderr)
    assert expected in found.stderr, found.stderr
    assert "grants-ok" not in found.stdout
    if unclassified:
        refused = applied.run()
        assert refused.returncode == 3 and "[grants_unclassified]" in refused.stderr, refused.stderr
    elif ownership:
        # The step grants and revokes; it does not take ownership back. It must SAY so, loudly, and not exit 0.
        refused = applied.run()
        assert refused.returncode == 4 and "owns" in refused.stderr, (refused.returncode, refused.stderr)
        with applied.owner() as owner:
            owner.execute("ALTER TABLE project OWNER TO CURRENT_USER")
            owner.execute("ALTER FUNCTION am_is_ascending_page_list(integer[], integer) OWNER TO CURRENT_USER")
        applied.apply()
    else:
        applied.apply()
    if not unclassified:
        assert applied.run("--check").returncode == 0


# --- (e) a restored database --------------------------------------------------------------------------------


def _pg_binary(name: str, server_major: int) -> str:
    candidate = Path(f"/usr/lib/postgresql/{server_major}/bin/{name}")
    if candidate.is_file():
        return str(candidate)
    found = shutil.which(name)
    if found:
        version = subprocess.run([found, "--version"], capture_output=True, text=True, check=False).stdout
        if re.search(rf"\b{server_major}\.", version):
            return found
    pytest.fail(f"no {name} of major version {server_major} on this host: a --no-privileges restore cannot be driven")


def _dump_and_restore(stand: Stand, source: str, target: str, *, in_place_like_copy_serve: bool) -> None:
    with stand.owner(database="postgres") as connection:
        major = int(str(connection.execute("SHOW server_version_num").fetchone()[0])[:2])
    environment = dict(os.environ, PGPASSWORD=stand.owner_password)
    cluster = stand.cluster
    dump = stand.root / "db.dump"
    base = ["-h", str(cluster.host), "-p", str(cluster.port), "-U", str(cluster.username)]
    subprocess.run([_pg_binary("pg_dump", major), *base, "--format=custom", "--no-owner", "--no-privileges",
                    "-f", str(dump), source], check=True, env=environment, capture_output=True)
    if in_place_like_copy_serve:
        # `copy-serve.sh restore-db`, verbatim: drop and recreate schema public, give the owner it, then restore.
        with stand.owner(database=target) as connection:
            connection.execute(f'DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO "{cluster.username}"')
    subprocess.run([_pg_binary("pg_restore", major), *base, "--no-owner", "--no-privileges", "--exit-on-error",
                    "--single-transaction", "-d", target, str(dump)], check=True, env=environment, capture_output=True)


def test_a_database_restored_from_a_no_privileges_dump_has_no_rights_until_the_step_runs(
    applied: Stand, empty_database: DatabaseSettings,
) -> None:
    target = str(empty_database.url.database)
    applied.databases.append(target)
    _dump_and_restore(applied, applied.database, target, in_place_like_copy_serve=False)
    applied.write_env(database=target)
    # The dump carried no privilege, so the restored database has none for the role: the application would answer
    # "permission denied" to its first query -- the failure the step exists to prevent.
    with applied.app(database=target, autocommit=True) as connection:
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("SELECT count(*) FROM public.project")
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("SELECT version_num FROM public.alembic_version")
    assert applied.run("--check").returncode == 1
    applied.apply()
    assert applied.run("--check").returncode == 0
    with applied.app(database=target, autocommit=True) as connection:
        assert connection.execute("SELECT count(*) FROM project").fetchone() == (0,)
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("TRUNCATE TABLE project")
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("CREATE TABLE zz_after_restore (a int)")


def test_the_copy_serve_restore_shape_drop_schema_create_schema_then_restore(applied: Stand) -> None:
    """``restore-db`` drops and recreates schema public in the SAME database: the role then even lacks USAGE."""
    _dump_and_restore(applied, applied.database, applied.database, in_place_like_copy_serve=True)
    with applied.app(autocommit=True) as connection:
        # Without USAGE on the schema PostgreSQL does not even look in it: the unqualified name is "not found",
        # which is how the application would see a restore that was not followed by the step.
        with pytest.raises(errors.UndefinedTable):
            connection.execute("SELECT count(*) FROM project")
        with pytest.raises(errors.InsufficientPrivilege, match="schema public"):
            connection.execute("SELECT count(*) FROM public.project")
    assert applied.run("--check").returncode == 1
    applied.apply()
    assert applied.run("--check").returncode == 0
    with applied.app(autocommit=True) as connection:
        assert connection.execute("SELECT count(*) FROM project").fetchone() == (0,)
        assert connection.execute("SELECT nextval('audit_event_sequence_no_seq') > 0").fetchone() == (True,)
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("DELETE FROM audit_event")


# --- the fail-closed case: a migration that adds a table -----------------------------------------------------

_NEW_MIGRATION = '''"""A test-only revision: a table nobody classified."""
from alembic import op

revision = "0034_zz_prod04_probe"
down_revision = "{head}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TABLE zz_prod04_probe (id text PRIMARY KEY)")


def downgrade() -> None:
    op.execute("DROP TABLE zz_prod04_probe")
'''


def test_a_migration_that_adds_a_table_is_refused_by_the_step_and_by_the_guard(applied: Stand, tmp_path: Path) -> None:
    """The literal mutation: a COPY of the migrations gains one revision that creates a table, the clone is
    migrated with it, and (1) the step refuses with nothing granted, (2) the classification guard goes red."""
    from sqlalchemy.orm import Session

    from auditmanager.shared.db.engine import create_database_engine

    migrations = tmp_path / "migrations"
    shutil.copytree(ROOT / "db/migrations", migrations, ignore=shutil.ignore_patterns("__pycache__"))
    (migrations / "versions/99999999_0034_zz_prod04_probe.py").write_text(
        _NEW_MIGRATION.format(head=coverage.HEAD), encoding="utf-8")
    url = applied.cluster.set(database=applied.database).render_as_string(hide_password=False)
    done = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "alembic", "--config", str(migrations / "alembic.ini"), "upgrade", "head"],
        cwd=ROOT, env=dict(os.environ, PYTHONPATH="src", DATABASE_URL=url), capture_output=True, text=True, timeout=120, check=False,
    )
    assert done.returncode == 0, done.stderr
    refused = applied.run()
    assert refused.returncode == 3, (refused.stdout, refused.stderr)
    assert "[grants_unclassified]" in refused.stderr and "zz_prod04_probe" in refused.stderr
    # fail closed: the rights the role already had are untouched (the transaction was rolled back) ...
    with applied.app(autocommit=True) as connection:
        assert connection.execute("SELECT count(*) FROM project").fetchone() == (0,)
        # ... and the new table got nothing
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute("SELECT count(*) FROM zz_prod04_probe")
    engine = create_database_engine(DatabaseSettings(url=applied.cluster.set(database=applied.database)))
    try:
        with Session(engine) as session, pytest.raises(grants.GrantClassificationRefused, match="zz_prod04_probe"):
            grants.audit_grant_classification(session)
    finally:
        engine.dispose()


# --- the premise the migrator decision rests on -------------------------------------------------------------------


def test_the_bootstrap_role_is_a_superuser_and_pgvector_is_not_trusted(stand: Stand) -> None:
    with stand.owner() as owner:
        assert owner.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone() == (True,), (
            "the postgres image's POSTGRES_USER is a superuser: this is why the premise has to be stated")
        assert owner.execute(
            "SELECT superuser, trusted FROM pg_available_extension_versions WHERE name = 'vector' ORDER BY version DESC LIMIT 1"
        ).fetchone() == (True, False)


def test_a_plain_owner_cannot_migrate_a_fresh_database(stand: Stand) -> None:
    """Migration ``0013`` runs ``CREATE EXTENSION vector``; the pgvector in this stack is ``superuser = true,
    trusted = false``. A plain owner role therefore cannot run ``migrate`` on a fresh database, so the migrator
    stays the bootstrap superuser (``apply-grants.sh``, header). If this goes red the decision is open again."""
    plain = f"prod04_plain_{secrets.token_hex(4)}"
    _CREATED_ROLES.append(plain)
    database = f"prod04_plain_db_{secrets.token_hex(4)}"
    try:
        with stand.owner(database="postgres") as owner:
            owner.execute(f"CREATE ROLE \"{plain}\" LOGIN PASSWORD 'plain-owner-password-0123456789' NOSUPERUSER")
            owner.execute(f'CREATE DATABASE "{database}" OWNER "{plain}"')
        with _connect(stand.cluster, database=database, user=plain, password="plain-owner-password-0123456789") as connection:
            connection.execute("CREATE TABLE ordinary_owner_work (a int)")  # an owner can do ordinary DDL ...
            with pytest.raises(errors.InsufficientPrivilege, match="extension"):
                connection.execute("CREATE EXTENSION vector WITH VERSION '0.8.6'")  # ... but not what 0013 does
    finally:
        with stand.owner(database="postgres") as owner:
            owner.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
            owner.execute(f'DROP ROLE IF EXISTS "{plain}"')
        _CREATED_ROLES.remove(plain)


# --- the password -----------------------------------------------------------------------------------------------------


def test_a_rotated_password_lands_on_the_next_run_and_the_old_one_stops_working(applied: Stand) -> None:
    old = applied.password
    new = secrets.token_hex(16)
    applied.write_env(app_password=new)
    applied.apply()
    with pytest.raises(psycopg.OperationalError):
        _connect(applied.cluster, database=applied.database, user=applied.role, password=old)
    with _connect(applied.cluster, database=applied.database, user=applied.role, password=new) as connection:
        assert connection.execute("SELECT current_user").fetchone() == (applied.role,)


def test_the_password_is_not_on_any_command_line_the_script_runs(applied: Stand) -> None:
    """The shim records nothing, so read what the script would pass: the psql argument list is built by one
    function; the password is written to stdin only."""
    text_of_script = (DEPLOY / "apply-grants.sh").read_text(encoding="utf-8")
    argument_list = re.search(r"psql_owner\(\) \{\n(.*?)\n\}", text_of_script, re.DOTALL)
    assert argument_list is not None
    assert "APP_PASSWORD" not in argument_list.group(1) and "app_password" not in argument_list.group(1)
    assert "printf '\\\\set app_password" in text_of_script


# --- nothing is left behind ----------------------------------------------------------------------------------------------


def test_nothing_is_left_behind(configured_settings: DatabaseSettings) -> None:
    """Last in the module: no role of this module's naming and no private database of it is in the cluster."""
    with _connect(configured_settings.url, database="postgres") as connection:
        roles = [r[0] for r in connection.execute("SELECT rolname FROM pg_roles WHERE rolname LIKE 'prod04\\_%%'").fetchall()]
        databases = [r[0] for r in connection.execute("SELECT datname FROM pg_database WHERE datname LIKE 'prod04\\_%%'").fetchall()]
    live = [r for r in roles if r in _CREATED_ROLES]
    assert live == [] and _CREATED_ROLES == [], (roles, databases, _CREATED_ROLES)
