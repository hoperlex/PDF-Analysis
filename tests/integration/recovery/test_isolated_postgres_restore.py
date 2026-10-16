"""The W58 PostgreSQL callback is exercised without a database or subprocess."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.recovery import isolated_postgres_restore as adapter

_LINE = "blob|1|" + "a" * 64 + "\n"


class _Result:
    def __init__(self, value: object) -> None:
        self.value = value

    def one(self) -> object:
        return self.value

    def scalar_one(self) -> object:
        return self.value


class _Transaction:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.is_active = True

    def rollback(self) -> None:
        self.events.append("rollback")
        self.is_active = False


class _Connection:
    def __init__(self, engine: _Engine) -> None:
        self.engine = engine

    def __enter__(self) -> _Connection:
        self.engine.events.append("connect")
        return self

    def __exit__(self, *_: object) -> None:
        self.engine.events.append("disconnect")

    def begin(self) -> _Transaction:
        self.engine.events.append("begin")
        return _Transaction(self.engine.events)

    def exec_driver_sql(self, statement: str) -> _Result:
        if "current_database()" in statement:
            self.engine.events.append("identity")
            return _Result((self.engine.database, self.engine.user, self.engine.version))
        if "pg_catalog.pg_class" in statement:
            self.engine.events.append("empty_check")
            return _Result(self.engine.relation_count)
        if statement.startswith("SET TRANSACTION"):
            self.engine.events.append("read_only_set")
            return _Result(None)
        if "transaction_isolation" in statement:
            self.engine.events.append("read_only_check")
            return _Result(self.engine.mode)
        raise AssertionError(f"unexpected SQL: {statement}")


class _Engine:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.database = "auditmanager_w58_drill"
        self.user = "restore"
        self.version = 170011
        self.relation_count = 0
        self.mode = ("repeatable read", "on")
        self.url = SimpleNamespace(drivername="postgresql+psycopg", query={},
                                   host="127.0.0.1", port=57490,
                                   database=self.database, username=self.user)

    def connect(self) -> _Connection:
        return _Connection(self)


class _Session:
    events: list[str] = []

    def __init__(self, *, bind: _Connection, autoflush: bool, expire_on_commit: bool) -> None:
        assert not autoflush and not expire_on_commit
        self.bind = bind
        self.events.append("session_new")

    def __enter__(self) -> _Session:
        self.events.append("session_enter")
        return self

    def __exit__(self, *_: object) -> None:
        self.events.append("session_exit")


class _Runner:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.restore_status = 0
        self.psql_status = 0
        self.psql_output = _LINE
        self.change_dump = False
        self.timeout_on: str | None = None

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append((argv, kwargs))
        name = argv[0]
        self.events.append(name)
        if self.timeout_on == name:
            raise subprocess.TimeoutExpired(argv, 1)
        if name == "pg_restore":
            assert kwargs["stdin"].read() == b"PGDMP\x00fake dump"  # type: ignore[union-attr]
            if self.change_dump:
                self.dump_path.write_bytes(b"changed during restore")
            return subprocess.CompletedProcess(argv, self.restore_status, "", "private failure")
        assert name == "psql"
        return subprocess.CompletedProcess(argv, self.psql_status, self.psql_output, "private failure")


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, _Engine, _Runner, adapter.IsolatedPostgresTarget, list[str]]:
    events: list[str] = []
    dump = tmp_path / "db.dump"
    dump.write_bytes(b"PGDMP\x00fake dump")
    dump.chmod(0o600)
    engine = _Engine(events)
    runner = _Runner(events)
    runner.dump_path = dump
    target = adapter.IsolatedPostgresTarget("127.0.0.1", 57490, engine.database, engine.user)
    _Session.events = events
    monkeypatch.setattr(adapter, "Session", _Session)
    return dump, engine, runner, target, events


def _restore(dump: Path, engine: _Engine, runner: _Runner, target: adapter.IsolatedPostgresTarget):
    return adapter.restore_isolated_postgres(
        dump, engine=engine, runner=runner, target=target  # type: ignore[arg-type]
    )


def test_atomic_restore_uses_one_target_then_yields_read_only_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    monkeypatch.setenv("PGHOST", "untrusted-inherited-host")
    with _restore(dump, engine, runner, target) as restored:
        assert restored.fingerprint_sha256 == hashlib.sha256(_LINE.encode()).hexdigest()
        assert restored.session.bind.engine is engine  # type: ignore[attr-defined]
        assert events.index("empty_check") < events.index("pg_restore") < events.index("psql")
        assert events.index("psql") < events.index("read_only_set") < events.index("session_enter")
    assert events[-3:] == ["session_exit", "rollback", "disconnect"]
    restore_args, restore_kw = runner.calls[0]
    assert restore_args == ["pg_restore", "--no-password", "--no-owner", "--no-privileges", "--exit-on-error",
                            "--single-transaction", "--dbname", target.database]
    assert restore_kw["env"]["PGHOST"] == "127.0.0.1"  # type: ignore[index]
    assert "PGPASSWORD" not in restore_kw["env"]  # type: ignore[operator]
    assert runner.calls[1][0][:3] == ["psql", "--no-password", "--no-psqlrc"]
    assert runner.calls[1][1]["env"] == restore_kw["env"]
    assert runner.calls[1][1]["input"].startswith("-- >>> stand-fingerprint-v1\n")  # type: ignore[union-attr]


@pytest.mark.parametrize("field,value", (
    ("host", "db.internal"), ("port", 5432), ("database", "production"),
    ("user", "bad;user"),
))
def test_target_requires_disposable_loopback_shape(field: str, value: object) -> None:
    fields: dict[str, object] = {
        "host": "127.0.0.1", "port": 57490,
        "database": "auditmanager_w58_drill", "user": "restore",
    }
    fields[field] = value
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="disposable loopback"):
        adapter.IsolatedPostgresTarget(**fields)  # type: ignore[arg-type]


def test_engine_url_mismatch_refuses_before_connection_or_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    engine.url.port = 9999
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="Engine URL"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert events == [] and runner.calls == []


def test_engine_url_query_cannot_redirect_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    engine.url.query = {"hostaddr": "10.0.0.9"}
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="Engine URL"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert events == [] and runner.calls == []


def test_nonempty_target_refuses_before_pg_restore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    engine.relation_count = 1
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="not empty"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert "pg_restore" not in events and runner.calls == []


@pytest.mark.parametrize("change", ("symlink", "public", "empty"))
def test_unsafe_dump_refuses_before_database_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    if change == "symlink":
        dump.rename(tmp_path / "actual")
        dump.symlink_to(tmp_path / "actual")
    elif change == "public":
        dump.chmod(0o644)
    else:
        dump.write_bytes(b"")
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert events == [] and runner.calls == []


def test_private_passfile_required_and_not_exposed_to_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, base, _ = _setup(tmp_path, monkeypatch)
    passfile = tmp_path / "pgpass"
    passfile.write_text("127.0.0.1:57490:auditmanager_w58_drill:restore:secret\n")
    passfile.chmod(0o644)
    target = adapter.IsolatedPostgresTarget(base.host, base.port, base.database, base.user, passfile)
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="private"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert runner.calls == []
    passfile.chmod(0o600)
    with _restore(dump, engine, runner, target):
        pass
    argv, kwargs = runner.calls[0]
    assert "secret" not in " ".join(argv)
    assert kwargs["env"]["PGPASSFILE"] == str(passfile)  # type: ignore[index]
    assert "PGPASSWORD" not in kwargs["env"]  # type: ignore[operator]


@pytest.mark.parametrize("fault", ("restore_error", "restore_timeout", "dump_changed"))
def test_failed_or_changed_restore_never_fingerprints_or_yields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    runner.restore_status = 1 if fault == "restore_error" else 0
    runner.timeout_on = "pg_restore" if fault == "restore_timeout" else None
    runner.change_dump = fault == "dump_changed"
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="pg_restore"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert "psql" not in events and "session_enter" not in events


@pytest.mark.parametrize("output", ("", "blob|1|bad\n", _LINE + _LINE, "z|1|" + "a" * 64 + "\na|1|" + "b" * 64 + "\n"))
def test_invalid_fingerprint_output_refuses_before_read_only_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    runner.psql_output = output
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="fingerprint"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert "session_enter" not in events


@pytest.mark.parametrize("fault", ("psql_error", "psql_timeout"))
def test_failed_fingerprint_command_refuses_without_exposing_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    runner.psql_status = 1 if fault == "psql_error" else 0
    runner.timeout_on = "psql" if fault == "psql_timeout" else None
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="fingerprint") as caught:
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert "private failure" not in str(caught.value)
    assert "session_enter" not in events


def test_changed_fingerprint_sql_refuses_before_database_or_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    source = tmp_path / "stand.sh"
    source.write_text("-- >>> stand-fingerprint-v1\nSELECT 1;\n-- <<< stand-fingerprint-v1\n")
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="frozen source"):
        with adapter.restore_isolated_postgres(
            dump, engine=engine, runner=runner, target=target, fingerprint_source=source,  # type: ignore[arg-type]
        ):
            pytest.fail("yielded")
    assert events == [] and runner.calls == []


def test_database_identity_and_major_version_are_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    engine.version = 160000
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="identity"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert runner.calls == [] and "pg_restore" not in events


def test_read_only_mode_refusal_rolls_back_without_yield(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump, engine, runner, target, events = _setup(tmp_path, monkeypatch)
    engine.mode = ("read committed", "off")
    with pytest.raises(adapter.IsolatedPostgresRestoreRefused, match="read-only"):
        with _restore(dump, engine, runner, target):
            pytest.fail("yielded")
    assert events[-2:] == ["rollback", "disconnect"]
    assert "session_enter" not in events
