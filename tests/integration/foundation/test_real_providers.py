"""Anti-vacuity: prove this run used the real providers, not a substitute.

Every other file in this suite asserts a behaviour. This one asserts that the
things those behaviours were asserted *about* are a real PostgreSQL server and a
real S3 service reached over the network -- because a cross-provider suite that
would also pass against SQLite and a temporary directory proves nothing about
what ships.

``FF-01`` section 4 lists "direct filesystem or JSON canonical storage" among
the approaches that are not approved, and the database boundary refuses any
driver but ``postgresql+psycopg`` precisely so that "the migration and test
contract is PostgreSQL, never SQLite" stays true. These tests are where that is
checked at run time rather than assumed.
"""

from __future__ import annotations

import inspect
import pkgutil
from importlib import import_module
from typing import Any
from urllib.parse import urlparse

import psycopg
import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import URL

import auditmanager.storage as storage_package
from auditmanager.shared.db.config import REQUIRED_DRIVERNAME, parse_database_url
from auditmanager.shared.db.errors import DatabaseConfigurationError
from auditmanager.storage import S3BlobStore, S3StorageSettings

#: The method set that makes a class a ``BlobStore`` implementation.
_BLOB_STORE_METHODS = (
    "check_access",
    "stage_temporary",
    "verify_temporary",
    "publish",
    "discard_temporary",
    "put_blob",
    "inspect",
    "read",
)


# --------------------------------------------------------------------------
# PostgreSQL is real
# --------------------------------------------------------------------------


def test_database_url_names_the_locked_postgresql_driver(database_url: URL) -> None:
    """The configured URL is ``postgresql+psycopg``, not SQLite and not psycopg2."""
    assert database_url.drivername == REQUIRED_DRIVERNAME, (
        f"DATABASE_URL names driver {database_url.drivername!r}. This suite is "
        f"only meaningful against {REQUIRED_DRIVERNAME!r}."
    )
    assert database_url.database, "DATABASE_URL carries no database name"


def test_a_sqlite_substitute_is_refused_by_the_boundary() -> None:
    """The boundary refuses a SQLite URL, so it can never be silently swapped in.

    This is the substitution the suite must be unable to accept. It is asserted
    against the provider's own validator rather than against a local rule, so
    what this suite refuses is exactly what the application refuses.
    """
    for substitute in (
        "sqlite:///foundation.db",
        "sqlite+pysqlite:///:memory:",
        "postgresql://user:pw@127.0.0.1:5432/db",  # psycopg2, not the locked driver
    ):
        with pytest.raises(DatabaseConfigurationError):
            parse_database_url(substitute)


def test_the_engine_speaks_postgresql_over_psycopg(engine: Engine) -> None:
    """The live engine's dialect and driver are the locked pair."""
    assert engine.dialect.name == "postgresql", (
        f"the engine dialect is {engine.dialect.name!r}; a foundation suite that "
        "ran against anything but PostgreSQL asserts nothing about what ships"
    )
    assert engine.dialect.driver == "psycopg", (
        f"the engine driver is {engine.dialect.driver!r}, not the locked psycopg 3"
    )


def test_the_server_is_a_real_postgresql_reached_over_tcp(
    independent_db: psycopg.Connection, database_url: URL
) -> None:
    """A raw-driver connection reaches a real server over a real socket.

    ``inet_server_addr()`` is NULL for a Unix-socket connection and for anything
    that is not a server at all; a value proves this went over TCP to the
    published port. ``server_version_num`` and ``pg_backend_pid()`` come from a
    backend process, which no embedded database has.
    """
    with independent_db.cursor() as cursor:
        cursor.execute(
            "SELECT version(), inet_server_addr()::text, "
            "current_setting('server_version_num')::int, pg_backend_pid(), "
            "current_database()"
        )
        version, server_addr, version_num, backend_pid, database = cursor.fetchone()

    assert version.startswith("PostgreSQL "), (
        f"SELECT version() returned {version!r}, which is not a PostgreSQL server"
    )
    assert server_addr, (
        "inet_server_addr() is NULL: this connection is not a TCP connection to a "
        "server, so the suite is not talking to the instance the .env names"
    )
    assert version_num >= 170000, f"server_version_num is {version_num}, expected >= 17"
    assert backend_pid > 0, "no backend process id: this is not a server connection"
    assert database == database_url.database, (
        f"connected to database {database!r}, not the configured "
        f"{database_url.database!r}"
    )


def test_the_schema_carries_postgresql_only_constructs(
    independent_db: psycopg.Connection,
) -> None:
    """The migrated schema uses triggers and partial indexes SQLite cannot have.

    This is the sharpest available refutation of a silent substitute: the P02
    head's invariants are ``plpgsql`` trigger functions raising custom SQLSTATEs
    and a partial unique index. A database that answers this query has run the
    real migration on a real PostgreSQL server.
    """
    with independent_db.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
            "AND tgname IN ('trg_blob_state_guard', 'trg_blob_write_once_guard')"
        )
        (trigger_count,) = cursor.fetchone()
        cursor.execute(
            "SELECT indpred IS NOT NULL FROM pg_index "
            "WHERE indexrelid = 'uq_blob_available_content'::regclass"
        )
        (is_partial,) = cursor.fetchone()
        cursor.execute("SELECT count(*) FROM pg_language WHERE lanname = 'plpgsql'")
        (plpgsql,) = cursor.fetchone()

    assert trigger_count == 2, (
        f"expected both blob guards to exist as triggers, found {trigger_count}"
    )
    assert is_partial, "uq_blob_available_content is not a partial index"
    assert plpgsql == 1, "plpgsql is absent: this is not the migrated PostgreSQL schema"


# --------------------------------------------------------------------------
# object storage is real
# --------------------------------------------------------------------------


def test_the_storage_endpoint_is_a_real_s3_service(
    storage_settings: S3StorageSettings, frozen_env: dict[str, str], http_get: Any
) -> None:
    """The endpoint answers MinIO's health probe with S3 response headers.

    A filesystem substitute has no endpoint, no ``Server`` header and no
    ``x-amz-request-id``. The port is asserted against ``S3_API_PORT`` so the
    suite cannot be pointed at some other running service.
    """
    endpoint = urlparse(storage_settings.endpoint_url)
    assert endpoint.scheme in ("http", "https"), (
        f"S3_ENDPOINT_URL scheme is {endpoint.scheme!r}; a filesystem path is not "
        "an S3 endpoint and this suite refuses to run against one"
    )
    assert str(endpoint.port) == frozen_env["S3_API_PORT"], (
        f"S3_ENDPOINT_URL port {endpoint.port} does not match S3_API_PORT "
        f"{frozen_env['S3_API_PORT']}"
    )

    status, headers = http_get(f"{storage_settings.endpoint_url}/minio/health/live")
    assert status == 200, f"the S3 health probe returned {status}, not 200"
    lowered = {name.lower(): value for name, value in headers.items()}
    assert "minio" in lowered.get("server", "").lower(), (
        f"the endpoint's Server header is {lowered.get('server')!r}; this is not "
        "the pinned MinIO service"
    )
    assert "x-amz-request-id" in lowered, (
        "the endpoint returned no x-amz-request-id: it is not answering as an S3 "
        "service, so nothing this suite publishes would prove S3 behaviour"
    )


def test_the_adapter_under_test_is_the_s3_adapter(
    store: S3BlobStore, storage_settings: S3StorageSettings
) -> None:
    """The fixture resolves to the real adapter bound to the configured endpoint."""
    assert type(store) is S3BlobStore
    assert type(store).__module__ == "auditmanager.storage.s3"
    client = store._client
    assert type(client).__module__.startswith("botocore."), (
        f"the adapter's client is {type(client)!r}, not a botocore client"
    )
    assert client.meta.endpoint_url == storage_settings.endpoint_url, (
        f"the adapter is bound to {client.meta.endpoint_url!r}, not to the "
        f"configured {storage_settings.endpoint_url!r}"
    )


def test_the_storage_package_offers_no_filesystem_canonical_adapter() -> None:
    """``S3BlobStore`` is the only BlobStore implementation in the package.

    ``FF-01`` section 4 does not approve filesystem or JSON canonical storage,
    and the port's own docstring says this package "must never gain one". A
    second implementation would give a future run somewhere to degrade to, so
    its absence is asserted rather than assumed.
    """
    found: dict[str, str] = {}
    for module_info in pkgutil.walk_packages(
        storage_package.__path__, prefix=f"{storage_package.__name__}."
    ):
        module = import_module(module_info.name)
        for name, obj in vars(module).items():
            if not inspect.isclass(obj) or obj.__module__ != module_info.name:
                continue
            # The Protocol itself declares the same methods. It is the contract,
            # not an implementation, and nothing can degrade to it.
            if getattr(obj, "_is_protocol", False):
                continue
            if all(callable(getattr(obj, method, None)) for method in _BLOB_STORE_METHODS):
                found[f"{module_info.name}.{name}"] = module_info.name

    assert list(found) == ["auditmanager.storage.s3.S3BlobStore"], (
        "the storage package defines a BlobStore implementation other than the S3 "
        f"adapter: {sorted(found)}. FF-01 section 4 does not approve a filesystem "
        "canonical store, and a second implementation is somewhere to degrade to."
    )


# --------------------------------------------------------------------------
# one .env, both providers
# --------------------------------------------------------------------------


def test_both_providers_are_configured_from_the_same_dotenv(
    frozen_env: dict[str, str],
    dotenv_values: dict[str, str],
    frozen_env_names: tuple[str, ...],
) -> None:
    """The values this process holds are the values in the single ``.env`` file.

    This is what makes the cross-provider claim a claim about *one* instance: if
    the database and the bucket could be configured from different sources, a
    green run would say nothing about them being the same deployment.
    """
    disagreements = [
        f"{name}: process has {frozen_env[name]!r}, .env has {dotenv_values.get(name)!r}"
        for name in frozen_env_names
        if dotenv_values.get(name) != frozen_env[name]
    ]
    assert not disagreements, (
        "the running configuration does not match the .env this suite reads:\n  "
        + "\n  ".join(disagreements)
    )


def test_the_two_provider_sides_of_the_env_agree(
    frozen_env: dict[str, str], database_url: URL, storage_settings: S3StorageSettings
) -> None:
    """The application-facing values carry the same ports as the service values."""
    assert str(database_url.port) == frozen_env["POSTGRES_PORT"], (
        "DATABASE_URL does not address POSTGRES_PORT"
    )
    assert database_url.database == frozen_env["POSTGRES_DB"]
    assert database_url.username == frozen_env["POSTGRES_USER"]
    assert str(urlparse(storage_settings.endpoint_url).port) == frozen_env["S3_API_PORT"]
    assert storage_settings.bucket == frozen_env["S3_BUCKET"]
    assert frozen_env["S3_API_PORT"] != frozen_env["S3_CONSOLE_PORT"]


def test_the_anti_vacuity_hooks_are_registered(foundation_conftest: Any) -> None:
    """The registered conftest still refuses skips, empty collection and collect-only.

    These three hooks are the reason a green run of this suite is evidence. If a
    later edit removes one, that removal must break a test rather than quietly
    widen what counts as a pass. The plugin object comes from pytest's own
    plugin manager, so this asserts on the hooks that are actually running.
    """
    for hook in (
        "pytest_configure",
        "pytest_collection_modifyitems",
        "pytest_runtest_makereport",
    ):
        assert callable(getattr(foundation_conftest, hook, None)), (
            f"the foundation conftest no longer defines {hook}; one of the three "
            "anti-vacuity guards has been removed"
        )
    assert inspect.isgeneratorfunction(foundation_conftest.pytest_runtest_makereport), (
        "pytest_runtest_makereport is no longer a hook wrapper, so a skipped test "
        "would no longer be converted into a failure"
    )
