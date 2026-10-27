"""`STAND-PURGE-TOOL-01`: the operator script, run for real against a lane's PostgreSQL and bucket.

`tests/integration/composition/test_purge_product_data_script.py` drives the script's order and exit
codes against a scripted `docker`. `test_product_purge.py` drives the Python half against the
database. This is where they meet: `infra/deploy/purge-product-data.sh` itself, with a `docker`
shim (`docker_shim.py`) that sends `exec postgres` to the lane's PostgreSQL container and the `api`
one-off to the repository's interpreter. The SQL, the transaction, the S3 calls, `pg_dump` and
`pg_restore` are all real; only the compose plumbing is translated, and the shim refuses every
docker call it was not written for.

What is proved here that the other two cannot: the operator's exact commands work end to end, the
dump the script writes is a whole database that restores, the object half is in `reset.sh`'s own
sidecar format, a half-done deletion is finished by `--finish-objects`, and a refusal leaves the
stand (and the worker) as it was.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from scripts.recovery.product_purge import KEEP_TABLES, PRODUCT_TABLES
from tests.integration.recovery.purge_seed import STRAY_KEY, bucket_profile, digest_of
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, seeded, stand, state_of,
)

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/deploy/purge-product-data.sh"
SHIM = ROOT / "tests/integration/recovery/docker_shim.py"
DOCKER = shutil.which("docker")


def _lane_container() -> str:
    """The lane's PostgreSQL container: ``<FOUNDATION_INSTANCE>-postgres-1`` (compose's own naming)."""
    instance = os.environ.get("FOUNDATION_INSTANCE", "")
    if not instance:
        for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if raw.startswith("FOUNDATION_INSTANCE="):
                instance = raw.partition("=")[2].strip().strip("\"'")
    assert instance, "no FOUNDATION_INSTANCE: run from a lane worktree with its .env"
    return f"{instance}-postgres-1"


class Operator:
    """The deployment directory an operator would have, wired to one cloned stand."""

    def __init__(self, stand: Stand, tmp: Path) -> None:
        assert DOCKER is not None, "this suite needs docker (the lane's PostgreSQL container)"
        self.stand, self.tmp = stand, tmp
        self.deploy = tmp / "deploy"
        self.deploy.mkdir()
        shutil.copy(SCRIPT, self.deploy / "purge-product-data.sh")
        (self.deploy / "compose.server.yml").write_text("services:\n  worker:\n    image: x\n", encoding="utf-8")
        user = stand.settings.url.username
        # `PROD-04`: the wrapper hands the python half the OWNER's url (`MIGRATOR_DATABASE_URL`); the docker shim below
        # ignores it and uses the lane's own url, which is the owner here, so the value only has to be well formed.
        (tmp / "alpha.env").write_text(
            f"ALPHA_INSTANCE=an-instance\nPOSTGRES_DB={stand.database}\nPOSTGRES_USER={user}\nS3_BUCKET={stand.bucket}\n"
            f"MIGRATOR_DATABASE_URL=postgresql+psycopg://{user}:owner-password@postgres:5432/{stand.database}\n",
            encoding="utf-8")
        (tmp / "lane.env").write_text("".join(f"{k}={v}\n" for k, v in stand.values.items()), encoding="utf-8")
        self.bin = tmp / "bin"
        self.bin.mkdir()
        shim = self.bin / "docker"
        shim.write_text(SHIM.read_text(encoding="utf-8").replace("#!/usr/bin/env python3", f"#!{sys.executable}", 1),
                        encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        self.log = tmp / "docker.log"
        self.dumps = tmp / "dumps"
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "ALPHA_ENV_FILE": str(tmp / "alpha.env"),
            "ALPHA_DUMP_ROOT": str(self.dumps), "ALPHA_PURGE_MODULE_DIR": str(ROOT / "scripts/recovery"),
            "SHIM_LOG": str(self.log), "SHIM_REAL_DOCKER": str(DOCKER), "SHIM_POSTGRES_CONTAINER": _lane_container(),
            "SHIM_PYTHON": sys.executable, "SHIM_REPOSITORY": str(ROOT), "SHIM_LANE_ENV": str(tmp / "lane.env"),
        }

    def run(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.deploy / "purge-product-data.sh"), "--database", self.stand.database,
             "--bucket", self.stand.bucket, *args],
            capture_output=True, text=True, env={**os.environ, **self.env, **extra}, timeout=600)

    @property
    def calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def called(self, needle: str) -> bool:
        return any(needle in call for call in self.calls)

    def dump_dir(self) -> Path:
        (found,) = self.dumps.glob("an-instance-purge-*")
        return found


@pytest.fixture
def operator(stand: Stand, tmp_path: Path) -> Operator:
    return Operator(stand, tmp_path)


def _keep_state(stand: Stand) -> dict[str, tuple[int, str]]:
    state = {t: digest_of(stand.engine, t) for t in sorted(KEEP_TABLES)}
    state["audit_event[keep]"] = digest_of(stand.engine, "audit_event", "starts_with(event_type, 'norm_custody.')")
    state["command_record[keep]"] = digest_of(stand.engine, "command_record", "command_type = 'approve_registration'")
    return state


def test_the_dry_run_prints_the_plan_and_changes_nothing(operator: Operator) -> None:
    before = state_of(operator.stand)
    completed = operator.run("--dry-run")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert state_of(operator.stand) == before
    assert "-- PRODUCT tables: every row goes (TRUNCATE) --" in completed.stdout
    assert re.search(r"product objects to delete, by exact key: \d+ objects, \d+ bytes", completed.stdout)
    assert "--dry-run. NOTHING ABOVE WAS CHANGED." in completed.stdout
    assert len(operator.calls) == 1 and "product_purge plan" in operator.calls[0]
    assert not operator.dumps.exists()


def test_the_script_purges_for_real_and_the_dump_it_leaves_restores(
    operator: Operator, maintenance_engine: Engine
) -> None:
    stand = operator.stand
    before, keep_before = state_of(stand), _keep_state(stand)
    product_before = {t: before["tables"][t][0] for t in sorted(PRODUCT_TABLES)}
    assert product_before["project"] > 0 and sum(product_before.values()) > 100

    completed = operator.run("--yes-purge-product-data")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert "KEEP tables and keep rows verified unchanged inside the transaction" in completed.stdout
    assert re.search(r"objects deleted by exact key: \d+ deleted \(\d+ bytes\), \d+ already absent", completed.stdout)

    # the worker was stopped for the window and started again; pg_dump ran before the purge
    indexes = [next(i for i, c in enumerate(operator.calls) if needle in c)
               for needle in ("product_purge plan", "stop worker", "pg_dump", "product_purge apply",
                              "product_purge delete-objects", "up -d --no-deps worker")]
    assert indexes == sorted(indexes)

    after = state_of(stand)
    assert all(after["tables"][t][0] == 0 for t in PRODUCT_TABLES)
    assert _keep_state(stand) == keep_before
    assert set(after["bucket"]) == set(stand.summary["norm_keys"]) | {STRAY_KEY}
    assert all(after["bucket"][k] == before["bucket"][k] for k in after["bucket"])

    # the dump: a whole database (the pre-purge one) and the object half in reset.sh's layout
    dump = operator.dump_dir()
    assert {p.name for p in dump.iterdir()} >= {"database.dump", "objects", "objects.attrs", "product-objects.tsv",
                                                 "plan.txt", "objects.sha256"}
    for row in (dump / "objects.attrs").read_text().splitlines():
        assert re.fullmatch(r"[^\t]+(\t[^\t]+){5}", row), "reset.sh's dump-verified regex would refuse this"
    scratch = f"purge_restore_{os.urandom(4).hex()}"
    with maintenance_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{scratch}"'))
    try:
        with (dump / "database.dump").open("rb") as source:
            restore = subprocess.run(
                [str(DOCKER), "exec", "-i", _lane_container(), "pg_restore", "--no-owner", "--username",
                 stand.settings.url.username, "--dbname", scratch],
                stdin=source, capture_output=True, text=True, timeout=300)
        assert restore.returncode == 0, restore.stderr
        engine = create_database_engine(DatabaseSettings(url=stand.settings.url.set(database=scratch)))
        try:
            restored = {t: digest_of(engine, t)[0] for t in sorted(PRODUCT_TABLES)}
            assert restored == product_before, "the dump is not the pre-purge database"
            assert digest_of(engine, "app_user") == before["tables"]["app_user"]
            assert digest_of(engine, "norm_paragraph") == before["tables"]["norm_paragraph"]
        finally:
            engine.dispose()
    finally:
        with maintenance_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{scratch}"'))
    mirrored = {p.relative_to(dump / "objects").as_posix() for p in (dump / "objects").rglob("*") if p.is_file()}
    assert mirrored == set(before["bucket"]) - set(after["bucket"])


def test_a_second_run_finds_nothing_dumps_nothing_and_says_so(operator: Operator) -> None:
    assert operator.run("--yes-purge-product-data").returncode == 0
    settled = state_of(operator.stand)
    dumps = sorted(operator.dumps.iterdir())
    operator.log.unlink()
    again = operator.run("--yes-purge-product-data")
    assert again.returncode == 0, again.stderr
    assert "nothing to purge. Nothing was dumped and nothing was changed." in again.stdout
    assert sorted(operator.dumps.iterdir()) == dumps and state_of(operator.stand) == settled
    assert len(operator.calls) == 1, "only the read-only preflight ran"


def test_a_running_job_refuses_with_status_3_before_a_dump_and_allow_running_overrides(operator: Operator) -> None:
    stand = operator.stand
    with stand.engine.begin() as connection:
        connection.execute(text("ALTER TABLE audit_run DISABLE TRIGGER trg_audit_run_state_guard"))
        connection.execute(text("UPDATE audit_run SET state = 'running' WHERE state = 'created'"))
        connection.execute(text("ALTER TABLE audit_run ENABLE TRIGGER trg_audit_run_state_guard"))
    before = state_of(stand)
    refused = operator.run("--yes-purge-product-data")
    assert refused.returncode == 3, (refused.stdout, refused.stderr)
    assert "work is running right now" in refused.stderr
    assert not operator.called("stop worker") and not operator.called("pg_dump") and not operator.dumps.exists()
    assert state_of(stand) == before
    forced = operator.run("--yes-purge-product-data", "--allow-running")
    assert forced.returncode == 0, (forced.stdout, forced.stderr)
    assert digest_of(stand.engine, "project")[0] == 0


def test_an_unclassified_table_refuses_before_anything_is_touched(operator: Operator) -> None:
    stand = operator.stand
    with stand.engine.begin() as connection:
        connection.execute(text("CREATE TABLE zz_throwaway (a int)"))
    before = state_of(stand)
    completed = operator.run("--yes-purge-product-data")
    assert completed.returncode == 3, (completed.stdout, completed.stderr)
    assert "['zz_throwaway']" in completed.stderr
    assert not operator.called("stop worker") and not operator.called("pg_dump")
    assert state_of(stand) == before
    dry = operator.run("--dry-run")
    assert dry.returncode == 3, "a dry run refuses the same way: it must not look fine and then refuse"


def test_a_deletion_that_failed_after_the_commit_is_finished_from_the_dumped_list(operator: Operator) -> None:
    stand = operator.stand
    before = state_of(stand)
    failed = operator.run("--yes-purge-product-data", SHIM_FAIL="product_purge delete-objects")
    assert failed.returncode == 4, (failed.stdout, failed.stderr)
    assert "THE DATABASE PART IS COMMITTED" in failed.stderr and "--finish-objects" in failed.stderr
    # the database part is done; the product objects are still in the bucket; the worker is back
    assert digest_of(stand.engine, "project")[0] == 0
    assert set(bucket_profile(stand.client, stand.bucket)) == set(before["bucket"])
    assert operator.calls[-1].endswith("up -d --no-deps worker") or "up -d --no-deps worker" in operator.calls[-1]
    dump = operator.dump_dir()
    finished = operator.run("--finish-objects", str(dump))
    assert finished.returncode == 0, (finished.stdout, finished.stderr)
    after = bucket_profile(stand.client, stand.bucket)
    assert set(after) == set(stand.summary["norm_keys"]) | {STRAY_KEY}
    again = operator.run("--finish-objects", str(dump))
    assert again.returncode == 0 and "0 deleted (0 bytes)" in again.stdout


def test_finish_objects_refuses_a_list_that_a_row_still_names(operator: Operator) -> None:
    """``--finish-objects`` before the purge: every listed Blob still has its row, so nothing goes."""
    stand = operator.stand
    assert operator.run("--yes-purge-product-data", SHIM_FAIL="product_purge apply").returncode == 4
    dump = operator.dump_dir()
    before = state_of(stand)
    refused = operator.run("--finish-objects", str(dump))
    assert refused.returncode == 3, (refused.stdout, refused.stderr)
    assert "still (or again) names" in refused.stderr
    assert state_of(stand) == before
