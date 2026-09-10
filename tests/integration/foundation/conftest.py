"""Fixtures for the cross-provider foundation suite (``P1-QA-00``).

This suite is the only one in the repository that exercises **PostgreSQL and
MinIO together, in one process, configured from one ``.env``**. Each authoring
lane proved its own provider against its own throwaway instance; nothing there
could prove that the two agree about the same run, or that either survives a
restart.

Three rules govern everything in this file.

**Nothing is substituted.** There is no SQLite engine, no filesystem blob
store, no ``moto``, no stub client. Every fixture resolves to the real server
named by the frozen ``FF-01`` section 3 environment names, and
``tests/integration/foundation/test_real_providers.py`` fails the run if it did
not.

**Nothing is skipped.** A missing service is a failure, never a skip. The
hook :func:`pytest_runtest_makereport` below converts *any* skipped outcome
into a failure, because a suite whose negative paths can quietly not run is
exactly the vacuous evidence this task exists to rule out. The same reasoning
covers an empty collection: :func:`pytest_collection_modifyitems` refuses it.

**Nothing is cleaned up in bulk.** Every object and every row a test creates is
registered with :func:`published_blobs` or :func:`recorded_blob_rows` and
removed *by exact key* at teardown. No fixture empties a bucket, truncates a
table or drops a database: those would destroy state this suite does not own
and would make "the checkout is unchanged afterwards" a claim about luck.
"""

from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import psycopg
import pytest
from botocore import UNSIGNED
from botocore.client import Config
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.storage import BlobId, S3BlobStore, S3StorageSettings

#: ``tests/integration/foundation/conftest.py`` is three levels below the root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The fifteen names ``FF-01`` section 3 freezes. ``make`` exports every one of
#: them before invoking this suite; the literal ``.venv/bin/pytest`` path fills
#: them from ``.env`` through :func:`_load_dotenv_if_needed`.
FROZEN_ENV_NAMES: tuple[str, ...] = (
    "FOUNDATION_INSTANCE",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "DATABASE_URL",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "S3_ENDPOINT_URL",
    "S3_API_PORT",
    "S3_CONSOLE_PORT",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
)

#: A port nothing listens on, for the "an unreachable provider raises rather
#: than degrades" paths. Deliberately outside every instance range the briefs
#: allocate, so it can never collide with a running lane.
CLOSED_PORT = 59098


# --------------------------------------------------------------------------
# environment
# --------------------------------------------------------------------------


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Read ``.env`` as DATA, exactly as the Makefile's ``load_env`` does.

    No shell, no substitution, no execution -- the file's own header says it is
    data. Only the one matched wrapping quote pair the contract allows is
    stripped. This is not a general dotenv loader and must not become one.
    """
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        name, sep, value = line.partition("=")
        if not sep:
            continue
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return values


def _load_dotenv_if_needed() -> None:
    """Fill in frozen names that are missing, never overriding an exported one.

    Under ``make test-foundation`` this does nothing: ``load_env`` has already
    exported all fifteen. It exists so the literal
    ``.venv/bin/pytest tests/integration/foundation`` command -- the one used to
    demonstrate that each guard in this suite can fail -- resolves the same
    instance instead of a different one.
    """
    if all(os.environ.get(name) for name in FROZEN_ENV_NAMES):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for name, value in _parse_dotenv(dotenv).items():
        if name in FROZEN_ENV_NAMES and not os.environ.get(name):
            os.environ[name] = value


@pytest.fixture(scope="session")
def frozen_env() -> dict[str, str]:
    """The fifteen frozen names, proved present and non-empty.

    A missing name is a hard failure here rather than a default assumed later:
    ``FF-01`` section 3 freezes the whole set and ``.env.example`` lists every
    one, so an absent name means the instance was never configured.
    """
    _load_dotenv_if_needed()
    missing = [name for name in FROZEN_ENV_NAMES if not os.environ.get(name, "").strip()]
    if missing:
        raise AssertionError(
            "the foundation suite requires every frozen FF-01 section 3 name; "
            f"missing or empty: {', '.join(missing)}. "
            "Run `cp .env.example .env` and give this instance its own values."
        )
    return {name: os.environ[name] for name in FROZEN_ENV_NAMES}


@pytest.fixture(scope="session")
def dotenv_values() -> dict[str, str]:
    """The ``.env`` file's own bytes, for the "one .env, both providers" proof."""
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        raise AssertionError(
            f"{dotenv} is missing. The foundation suite is configured from the "
            "single git-ignored .env that `make` reads; there is no second source."
        )
    return _parse_dotenv(dotenv)


# --------------------------------------------------------------------------
# PostgreSQL
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def database_url(frozen_env: dict[str, str]) -> URL:
    """``DATABASE_URL`` parsed through the provider's own validator.

    Going through :func:`parse_database_url` rather than a local parser means a
    URL this suite accepts is exactly a URL the application accepts -- including
    its refusal of any driver but ``postgresql+psycopg``.
    """
    return parse_database_url(frozen_env["DATABASE_URL"])


@pytest.fixture(scope="session")
def engine(database_url: URL) -> Iterator[Engine]:
    """A session-scoped engine built from validated settings.

    Deliberately *not* the process-wide :func:`auditmanager.shared.db.get_engine`:
    the restart test disposes and rebuilds its engine, and doing that to global
    state would leak between tests.
    """
    built = create_database_engine(DatabaseSettings(url=database_url))
    try:
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """The DB session boundary under test, bound to this suite's engine."""
    return create_session_factory(engine)


def connect_psycopg(url: URL) -> psycopg.Connection:
    """Open a connection with the raw driver, bypassing SQLAlchemy entirely.

    Used as the *independent* reader in the cross-provider tests. A row written
    through the session boundary and read back through this connection has
    crossed the real PostgreSQL wire protocol, which no in-process substitute
    could satisfy.
    """
    return psycopg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname=url.database,
        connect_timeout=10,
    )


@pytest.fixture(scope="session")
def independent_db(database_url: URL) -> Iterator[psycopg.Connection]:
    """A raw psycopg connection, separate from the engine's pool."""
    connection = connect_psycopg(database_url)
    try:
        yield connection
    finally:
        connection.close()


# --------------------------------------------------------------------------
# object storage
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def storage_settings(frozen_env: dict[str, str]) -> S3StorageSettings:
    """Adapter configuration read through the provider's own loader."""
    return S3StorageSettings.from_env()


@pytest.fixture(scope="session")
def store(storage_settings: S3StorageSettings) -> S3BlobStore:
    """The BlobStore adapter under test, on the real endpoint."""
    return S3BlobStore(storage_settings)


def build_s3_client(settings: S3StorageSettings, *, anonymous: bool = False) -> Any:
    """Build a boto3 S3 client for the configured endpoint.

    ``anonymous=True`` signs nothing, which is how the privacy claims are
    proved: a bucket that answers an unsigned request is not private, whatever
    the credentialed path shows.
    """
    common: dict[str, Any] = {
        "endpoint_url": settings.endpoint_url,
        "region_name": settings.region,
    }
    config = Config(
        s3={"addressing_style": "path"},
        connect_timeout=settings.connect_timeout_seconds,
        read_timeout=settings.read_timeout_seconds,
        retries={"max_attempts": 1, "mode": "standard"},
        **({"signature_version": UNSIGNED} if anonymous else {}),
    )
    if not anonymous:
        common["aws_access_key_id"] = settings.access_key_id
        common["aws_secret_access_key"] = settings.secret_access_key
    return boto3.client("s3", config=config, **common)


@pytest.fixture(scope="session")
def independent_s3(storage_settings: S3StorageSettings) -> Any:
    """A credentialed client this suite builds itself, not the adapter's.

    The adapter is the writer; this is the out-of-band reader. "The bytes are
    on the S3 service" is asserted through this client so the proof never
    depends on the same object the adapter would have returned from memory.
    """
    return build_s3_client(storage_settings)


@pytest.fixture(scope="session")
def anonymous_s3(storage_settings: S3StorageSettings) -> Any:
    """An unsigned client, for the three anonymous-denial proofs."""
    return build_s3_client(storage_settings, anonymous=True)


# --------------------------------------------------------------------------
# scoped cleanup
# --------------------------------------------------------------------------


@pytest.fixture
def published_blobs(store: S3BlobStore) -> Iterator[list[BlobId]]:
    """Register every ``blob_id`` a test publishes; remove each by exact key.

    ``_purge_published`` deletes exactly one canonical object and is the hook
    the storage lane documents for this purpose ("it exists for the lane's own
    scoped cleanup ... one key at a time, so that no cleanup path in this
    repository is ever a broad bucket deletion"). Nothing here lists the bucket
    and nothing here deletes a key it did not create.
    """
    registered: list[BlobId] = []
    try:
        yield registered
    finally:
        for blob_id in registered:
            store._purge_published(blob_id)


@pytest.fixture
def recorded_blob_rows(session_factory: sessionmaker[Session]) -> Iterator[list[str]]:
    """Register every ``blob.blob_id`` a test inserts; delete each by primary key.

    One ``DELETE ... WHERE blob_id = :blob_id`` per registered identifier. There
    is no ``TRUNCATE``, no unqualified ``DELETE`` and no ``DROP``: this suite
    runs against the same migrated database the acceptance commands use, and a
    bulk statement here would destroy accepted state rather than the test's own.
    """
    registered: list[str] = []
    try:
        yield registered
    finally:
        with session_factory() as session:
            for blob_id in registered:
                session.execute(
                    text("DELETE FROM blob WHERE blob_id = :blob_id"),
                    {"blob_id": blob_id},
                )
            session.commit()


# --------------------------------------------------------------------------
# helpers shared by the tests
# --------------------------------------------------------------------------


def http_status(url: str, *, timeout: float = 10.0) -> tuple[int, dict[str, str]]:
    """GET a URL and return ``(status, headers)``, treating 4xx as an answer.

    An HTTP error code is a *result* here -- "403 is the denial we are proving"
    -- so it is returned rather than raised. Only a transport failure raises.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, dict(response.headers)
    except urllib.error.HTTPError as exc:
        headers = dict(exc.headers) if exc.headers else {}
        exc.close()
        return exc.code, headers


def run_make(target: str, *, timeout: float = 600.0) -> subprocess.CompletedProcess[str]:
    """Run one frozen ``make`` target from the repository root.

    The restart test stops and starts services through the frozen command
    surface rather than through ``docker`` directly, so what it proves is what
    an operator running the accepted commands would see.

    ``MAKEFLAGS`` and friends are stripped from the child environment. When this
    suite runs under ``make test-foundation`` the parent make exports them, and
    an inherited jobserver or flag set would change how the child behaves --
    which would make the restart a different action than the one an operator
    performs.
    """
    child_env = {
        name: value
        for name, value in os.environ.items()
        if name not in {"MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKE_TERMOUT", "MAKE_TERMERR"}
    }
    return subprocess.run(
        ["make", target],
        cwd=REPOSITORY_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def describe(result: subprocess.CompletedProcess[str]) -> str:
    """Render a completed command for an assertion message."""
    return (
        f"$ {' '.join(result.args)}\n"
        f"exit {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


# The helpers above are handed to tests as fixtures rather than imported. Under
# ``--import-mode=importlib`` -- which ``pyproject.toml`` sets for the whole
# repository -- a test module is imported by path and is not a package member,
# so ``from .conftest import ...`` is not available and ``import conftest``
# would depend on a sys.path entry pytest deliberately does not add. Fixtures
# are the supported channel, and they keep this suite working under both the
# ``make`` invocation and the literal ``.venv/bin/pytest`` one.


@pytest.fixture(scope="session")
def frozen_env_names() -> tuple[str, ...]:
    """The fifteen frozen ``FF-01`` section 3 names."""
    return FROZEN_ENV_NAMES


@pytest.fixture(scope="session")
def closed_port() -> int:
    """A port nothing listens on, for the unreachable-provider proofs."""
    return CLOSED_PORT


@pytest.fixture(scope="session")
def http_get() -> Any:
    """``(url) -> (status, headers)``; 4xx is a result, not an exception."""
    return http_status


@pytest.fixture(scope="session")
def make_target() -> Any:
    """``(target) -> CompletedProcess`` for one frozen ``make`` target."""
    return run_make


@pytest.fixture(scope="session")
def describe_command() -> Any:
    """Render a ``CompletedProcess`` for an assertion message."""
    return describe


@pytest.fixture(scope="session")
def psycopg_connector() -> Any:
    """``(URL) -> psycopg.Connection``: a raw-driver connection factory."""
    return connect_psycopg


@pytest.fixture(scope="session")
def s3_client_builder() -> Any:
    """``(settings, *, anonymous=False) -> boto3 S3 client``."""
    return build_s3_client


@pytest.fixture(scope="session")
def foundation_conftest(pytestconfig: pytest.Config) -> Any:
    """The *registered* conftest plugin object for this directory.

    Returned from the plugin manager rather than re-imported by path, so the
    anti-vacuity test inspects the module pytest is actually running hooks
    from, not a second copy of the same source.
    """
    here = Path(__file__).resolve()
    for plugin in pytestconfig.pluginmanager.get_plugins():
        if getattr(plugin, "__file__", None) and Path(plugin.__file__).resolve() == here:
            return plugin
    raise AssertionError(
        f"the foundation conftest at {here} is not registered as a pytest plugin; "
        "its anti-vacuity hooks are therefore not running"
    )


# --------------------------------------------------------------------------
# anti-vacuity hooks
# --------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Refuse a run that collects without executing.

    ``--collect-only`` exits 0 having proved nothing. The Makefile already
    scrubs ``PYTEST_ADDOPTS`` so it cannot arrive from the environment, but this
    suite is also run directly, and a green exit that executed no assertion must
    not be available by any route.
    """
    if config.getoption("collectonly", default=False):
        raise pytest.UsageError(
            "P1-QA-00: the foundation suite refuses --collect-only. "
            "Collection is not evidence; the suite exists to execute its assertions."
        )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Refuse an empty collection.

    pytest's own exit status for "no tests collected" is 5, which looks like
    nothing went wrong. ``run_suite`` in the Makefile refuses 5 for the ``make``
    path; this refuses it for every other path as well.
    """
    if not items:
        raise pytest.UsageError(
            "P1-QA-00: the foundation suite collected no tests. An empty or fully "
            "deselected run is not a pass -- it is the absence of evidence."
        )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Iterator[pytest.TestReport]:
    """Turn any skip into a failure.

    This is the load-bearing anti-vacuity rule. Every proof in this suite is a
    proof *about a real service*, so "the service was not there" is the failure
    the suite is for, not a reason to pass. A conditional skip, an
    ``importorskip`` or a ``skipif`` that silently became true would otherwise
    let the negative paths -- the ones that show the guards can fire -- report
    green by never running.
    """
    report = yield
    if report.skipped:
        report.outcome = "failed"
        report.longrepr = (
            f"P1-QA-00: {item.nodeid} was SKIPPED, and this suite refuses skips.\n"
            "A cross-provider proof that does not run is not a proof. Assert the "
            "real PostgreSQL and MinIO services; never skip when one is absent.\n"
            f"original skip reason: {report.longrepr}"
        )
    return report
