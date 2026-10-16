"""Guarded operator callback for an isolated W58 PostgreSQL restore drill.

The operator supplies a fresh, disposable loopback database and an Engine
created through the application's owned database factory. This module cannot
prove that a loopback endpoint is not a tunnel to a source/production host.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import stat
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from scripts.recovery.isolated_restore_drill import RestoredDatabase

_REPO = Path(__file__).resolve().parents[2]
_STAND_SQL_SOURCE = _REPO / "infra/deploy/copy-serve.sh"
_START = "-- >>> stand-fingerprint-v1\n"
_END = "-- <<< stand-fingerprint-v1\n"
_STAND_SQL_SHA256 = "dc1a7923faca4462c3e55b6c3976bc30179c69684c74ae41d3804192efbc6a72"
_TABLE_LINE = re.compile(r"([a-z_][a-z0-9_]*)\|(0|[1-9][0-9]*)\|([0-9a-f]{64})\Z")
_DATABASE = re.compile(r"auditmanager_w58_[a-z0-9_]{1,43}\Z")
_USER = re.compile(r"[a-z_][a-z0-9_]{0,62}\Z")
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_RELATIONS = """
    SELECT count(*) FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp_%'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
"""


class IsolatedPostgresRestoreRefused(ValueError):
    """The target, dump, restore process or fingerprint failed a safety check."""


@dataclass(frozen=True, slots=True)
class IsolatedPostgresTarget:
    host: str
    port: int
    database: str
    user: str
    pgpass_file: Path | None = None

    def __post_init__(self) -> None:
        try:
            loopback = ipaddress.ip_address(self.host).is_loopback
        except (TypeError, ValueError):
            loopback = False
        if not loopback or type(self.port) is not int or not 1024 <= self.port <= 65535 \
                or self.port == 5432 or type(self.database) is not str \
                or not _DATABASE.fullmatch(self.database) or type(self.user) is not str \
                or not _USER.fullmatch(self.user):
            raise IsolatedPostgresRestoreRefused("target must be a named disposable loopback database on a nondefault port")
        if self.pgpass_file is not None and (not isinstance(self.pgpass_file, Path)
                                             or not self.pgpass_file.is_absolute()):
            raise IsolatedPostgresRestoreRefused("libpq passfile must be an absolute private path")


def _private_file(path: Path, *, label: str) -> BinaryIO:
    try:
        descriptor = os.open(path, _FILE_FLAGS)
    except OSError:
        raise IsolatedPostgresRestoreRefused(f"{label} cannot be opened without following links") from None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() \
                or info.st_mode & 0o077 or info.st_nlink != 1:
            raise IsolatedPostgresRestoreRefused(f"{label} must be an owned private regular file")
        return os.fdopen(descriptor, "rb", buffering=0)
    except BaseException:
        os.close(descriptor)
        raise


def _file_identity(stream: BinaryIO) -> tuple[int, int, int, int, int, int]:
    info = os.fstat(stream.fileno())
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _check_engine_url(engine: Engine, target: IsolatedPostgresTarget) -> None:
    url = engine.url
    if url.drivername != "postgresql+psycopg" or url.query or (
        url.host, url.port, url.database, url.username
    ) != (
        target.host, target.port, target.database, target.user
    ):
        raise IsolatedPostgresRestoreRefused("Engine URL differs from the isolated CLI target")


def _check_sql_identity(connection: object, target: IsolatedPostgresTarget) -> None:
    actual = tuple(connection.exec_driver_sql(  # type: ignore[attr-defined]
        "SELECT current_database(), current_user, current_setting('server_version_num')::integer"
    ).one())
    if len(actual) != 3 or actual[:2] != (target.database, target.user) \
            or type(actual[2]) is not int or actual[2] // 10000 != 17:
        raise IsolatedPostgresRestoreRefused("connected database identity or PostgreSQL major version differs")


def _environment(target: IsolatedPostgresTarget) -> dict[str, str]:
    result = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C", "LC_ALL": "C",
        "PGHOST": target.host, "PGPORT": str(target.port),
        "PGDATABASE": target.database, "PGUSER": target.user,
        "PGSSLMODE": "disable", "PGCONNECT_TIMEOUT": "10",
        "PGAPPNAME": "auditmanager-w58-isolated-restore",
    }
    if target.pgpass_file is not None:
        with _private_file(target.pgpass_file, label="libpq passfile"):
            pass
        result["PGPASSFILE"] = str(target.pgpass_file)
    return result


def _fingerprint_sql(source: Path) -> str:
    try:
        value = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise IsolatedPostgresRestoreRefused("stand fingerprint source cannot be read") from None
    if value.count(_START) != 1 or value.count(_END) != 1:
        raise IsolatedPostgresRestoreRefused("stand fingerprint markers are missing or repeated")
    sql = _START + value.split(_START, 1)[1].split(_END, 1)[0] + _END
    if hashlib.sha256(sql.encode("utf-8")).hexdigest() != _STAND_SQL_SHA256:
        raise IsolatedPostgresRestoreRefused("stand fingerprint SQL differs from frozen source")
    return sql


def _fingerprint_digest(output: str) -> str:
    if type(output) is not str or not output.endswith("\n") or "\r" in output:
        raise IsolatedPostgresRestoreRefused("stand fingerprint output is empty or malformed")
    lines = output[:-1].split("\n")
    names: list[str] = []
    for line in lines:
        match = _TABLE_LINE.fullmatch(line)
        if match is None:
            raise IsolatedPostgresRestoreRefused("stand fingerprint table line is malformed")
        names.append(match.group(1))
    if not names or names != sorted(set(names)):
        raise IsolatedPostgresRestoreRefused("stand fingerprint table set is empty, unordered or repeated")
    return hashlib.sha256(("\n".join(lines) + "\n").encode("ascii")).hexdigest()


@contextmanager
def restore_isolated_postgres(
    dump_path: Path, *, engine: Engine, target: IsolatedPostgresTarget,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    fingerprint_source: Path = _STAND_SQL_SOURCE,
    timeout_seconds: int = 3600,
) -> Iterator[RestoredDatabase]:
    """Restore one empty target and hold a read-only snapshot for W58 audit.

    This must only be called by an operator who proved the target is disposable
    and isolated. A retry after any failed restore requires a fresh empty DB.
    """
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 86400:
        raise IsolatedPostgresRestoreRefused("restore timeout is invalid")
    if dump_path.name != "db.dump" or not callable(runner):
        raise IsolatedPostgresRestoreRefused("dump or process runner is invalid")
    _check_engine_url(engine, target)
    environment = _environment(target)
    sql = _fingerprint_sql(fingerprint_source)
    with _private_file(dump_path, label="db.dump") as dump:
        before = _file_identity(dump)
        if before[3] == 0:
            raise IsolatedPostgresRestoreRefused("db.dump is empty")
        with engine.connect() as connection:
            _check_sql_identity(connection, target)
            empty = connection.exec_driver_sql(_RELATIONS).scalar_one()
            if type(empty) is not int or empty != 0:
                raise IsolatedPostgresRestoreRefused("isolated target is not empty")
        try:
            restored = runner(
                ["pg_restore", "--no-password", "--no-owner", "--no-privileges", "--exit-on-error",
                 "--single-transaction", "--dbname", target.database],
                stdin=dump, env=environment, capture_output=True, text=True,
                timeout=timeout_seconds, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise IsolatedPostgresRestoreRefused("atomic pg_restore did not complete") from None
        if restored.returncode != 0 or _file_identity(dump) != before:
            raise IsolatedPostgresRestoreRefused("atomic pg_restore failed or dump changed")
    try:
        fingerprint = runner(
            ["psql", "--no-password", "--no-psqlrc", "--quiet", "--no-align", "--tuples-only",
             "--set", "ON_ERROR_STOP=1", "--dbname", target.database],
            input=sql, env=environment, capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise IsolatedPostgresRestoreRefused("stand fingerprint query did not complete") from None
    if fingerprint.returncode != 0:
        raise IsolatedPostgresRestoreRefused("stand fingerprint query failed")
    digest = _fingerprint_digest(fingerprint.stdout)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            _check_sql_identity(connection, target)
            mode = tuple(connection.exec_driver_sql(
                "SELECT current_setting('transaction_isolation'), current_setting('transaction_read_only')"
            ).one())
            if mode != ("repeatable read", "on"):
                raise IsolatedPostgresRestoreRefused("restored DB audit transaction is not read-only repeatable-read")
            with Session(bind=connection, autoflush=False, expire_on_commit=False) as session:
                yield RestoredDatabase(session, digest)
        finally:
            if transaction.is_active:
                transaction.rollback()


__all__ = ["IsolatedPostgresRestoreRefused", "IsolatedPostgresTarget", "restore_isolated_postgres"]
