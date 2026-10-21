"""The fixtures the product-purge tests share: a stand in miniature, cloned per test.

`STAND-PURGE-TOOL-01`. ``seeded`` (module scope) builds ONE database and ONE bucket with
``purge_seed``; ``stand`` (function scope) gives each test a private clone of the database
(``CREATE DATABASE ... TEMPLATE``) and a private copy of the bucket, and points ``DATABASE_URL`` and
``S3_*`` at them for the code under test. The test modules import these by name.
"""

from __future__ import annotations

import contextlib
import io
import secrets
import types
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.storage import S3StorageSettings
from scripts.recovery.schema_coverage import TABLES
from tests.integration.recovery.purge_seed import bucket_profile, digest_of, s3, seed_stand

ALL_TABLES = sorted(TABLES)


@dataclass
class Stand:
    database: str
    bucket: str
    settings: DatabaseSettings
    engine: Engine
    values: dict[str, str]
    client: Any
    summary: dict[str, Any]


@pytest.fixture(scope="module")
def seeded(configured_settings, maintenance_engine, migrated_template) -> Iterator[dict[str, Any]]:
    base = S3StorageSettings.from_env()
    template = f"purge_tpl_{secrets.token_hex(6)}"
    bucket = f"{base.bucket[:36]}-tpl-{secrets.token_hex(5)}"
    with maintenance_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{template}" TEMPLATE "{migrated_template}"'))
    settings = DatabaseSettings(url=configured_settings.url.set(database=template))
    values = {
        "DATABASE_URL": settings.url.render_as_string(hide_password=False),
        "S3_ENDPOINT_URL": base.endpoint_url, "S3_REGION": base.region,
        "S3_ACCESS_KEY_ID": base.access_key_id, "S3_SECRET_ACCESS_KEY": base.secret_access_key,
        "S3_BUCKET": bucket,
    }
    client = s3(values)
    client.create_bucket(Bucket=bucket)
    try:
        summary = seed_stand(values, settings)
        yield {"template": template, "bucket": bucket, "values": values, "summary": summary}
    finally:
        _empty_and_delete(client, bucket)
        with maintenance_engine.connect() as connection:
            connection.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :n"), {"n": template})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{template}"'))


def _empty_and_delete(client: Any, bucket: str) -> None:
    for page in client.get_paginator("list_object_versions").paginate(Bucket=bucket):
        for item in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]:
            client.delete_object(Bucket=bucket, Key=item["Key"], VersionId=item["VersionId"])
    client.delete_bucket(Bucket=bucket)


@pytest.fixture
def stand(seeded, configured_settings, maintenance_engine, monkeypatch) -> Iterator[Stand]:
    """A private clone of the seeded database and a private copy of its bucket."""
    name = f"purge_clone_{secrets.token_hex(6)}"
    bucket = f"{seeded['bucket'][:36]}-c-{secrets.token_hex(5)}"
    with maintenance_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{seeded["template"]}"'))
    settings = DatabaseSettings(url=configured_settings.url.set(database=name))
    values = {**seeded["values"], "DATABASE_URL": settings.url.render_as_string(hide_password=False),
              "S3_BUCKET": bucket}
    client = s3(values)
    client.create_bucket(Bucket=bucket)
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=seeded["bucket"]):
        for item in page.get("Contents", []):
            client.copy_object(Bucket=bucket, Key=item["Key"], MetadataDirective="COPY",
                               CopySource={"Bucket": seeded["bucket"], "Key": item["Key"]})
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    engine = create_database_engine(settings)
    try:
        yield Stand(name, bucket, settings, engine, values, client, seeded["summary"])
    finally:
        engine.dispose()
        _empty_and_delete(client, bucket)
        with maintenance_engine.connect() as connection:
            connection.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :n"), {"n": name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


def state_of(stand: Stand) -> dict[str, Any]:
    """Every table by the test's own digest, every object by the bytes actually read."""
    return {"tables": {t: digest_of(stand.engine, t) for t in ALL_TABLES},
            "bucket": bucket_profile(stand.client, stand.bucket)}


def invoke(module: types.ModuleType, stand: Stand, *argv: str, database: str | None = None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err):
        code = module.run([*argv, "--database", database or stand.database, "--bucket", stand.bucket], out=out)
    return code, out.getvalue(), err.getvalue()


def _line(out: str, name: str) -> str:
    return next(line.split(": ", 1)[1] for line in out.splitlines() if line.startswith(f"{name}: "))


def full_purge(module: types.ModuleType, stand: Stand, dump: Path, *flags: str) -> dict[str, tuple[int, str, str]]:
    """The four steps the shell script drives, in its order."""
    steps = {"plan": invoke(module, stand, "plan", *flags)}
    assert steps["plan"][0] == 0, steps["plan"]
    sha = _line(steps["plan"][1], "plan-sha256")
    steps["snapshot"] = invoke(module, stand, "snapshot-objects", "--dump-dir", str(dump), *flags)
    assert steps["snapshot"][0] == 0, steps["snapshot"]
    listing = _line(steps["snapshot"][1], "objects-sha256")
    steps["apply"] = invoke(module, stand, "apply", "--expect-plan", sha,
                            "--objects-file", str(dump / "product-objects.tsv"), *flags)
    if steps["apply"][0] == 0:
        steps["delete"] = invoke(module, stand, "delete-objects", "--objects-file",
                                 str(dump / "product-objects.tsv"), "--objects-sha256", listing)
    return steps
