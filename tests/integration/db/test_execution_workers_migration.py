"""`W54-SEAL-01`: migration ``0019_execution_workers`` -- the worker registry and its lease.

Plan `W54-PLAN.md` section 4 requires, for both W54 migrations, a fresh upgrade, an upgrade
from the previous head with rows, and a refused downgrade with retained data.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AttemptId,
    DocumentUid,
    JobId,
    LeaseId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
    WorkerId,
)
from tests.support.expected_facts import FACTS


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _head(connection) -> str:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _job_with_attempt(connection, *, label: str) -> dict[str, str]:
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()), "run": str(RunId.new()), "job": str(JobId.new()),
        "attempt": str(AttemptId.new()), "lease": str(LeaseId.new()),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, :name)"),
                       {**ids, "name": f"workers-{label}"})
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, :title)"), {**ids, "title": label})
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, "
                            "version_ordinal, media_type, byte_size, sha256, page_count) "
                            "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
                       {**ids, "sha": "a" * 64})
    connection.execute(text("INSERT INTO audit_run (run_id, project_uid, version_uid, "
                            "analysis_profile_id, prompt_bundle_id, provider_mode, "
                            "frozen_input_digest) VALUES (:run, :project, :version, :profile, "
                            ":bundle, 'recorded', :digest)"),
                       {**ids, "profile": str(AnalysisProfileId.new()),
                        "bundle": str(PromptBundleId.new()), "digest": "b" * 64})
    connection.execute(text("INSERT INTO job (job_id, run_id, state) VALUES (:job, :run, 'queued')"), ids)
    connection.execute(text("INSERT INTO attempt (attempt_id, job_id, execution_token) "
                            "VALUES (:attempt, :job, :token)"), {**ids, "token": f"tok-{label}"})
    return ids


def _register(connection, *, slots: int = 1, version: str = "0.5.0+test") -> str:
    worker = str(WorkerId.new())
    connection.execute(text(
        "INSERT INTO worker (worker_id, version, slots) VALUES (:id, :version, :slots)"
    ), {"id": worker, "version": version, "slots": slots})
    return worker


def test_a_fresh_upgrade_creates_the_registry_and_the_lease_column(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        # `W55B-SEAL-01` moved the head past this revision; the registry is still there.
        assert _head(connection) == FACTS.migration_head
        assert connection.execute(text("SELECT to_regclass('public.worker')")).scalar_one()
        assert connection.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'lease' AND column_name = 'worker_id'"
        )).scalar_one() == "YES"
        frozen = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_lease_frozen_guard'"
        )).scalar_one()
        assert "'worker_id'" in frozen, frozen


def test_a_populated_0018_upgrades_and_its_leases_name_no_worker(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_0018 = foundation_command(_alembic("upgrade", "0018_norm_custody"), url)
    assert at_0018.returncode == 0, at_0018.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _job_with_attempt(connection, label="before-0019")
            connection.execute(text("INSERT INTO lease (lease_id, job_id, attempt_id) "
                                    "VALUES (:lease, :job, :attempt)"), ids)
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert _head(connection) == FACTS.migration_head
            assert connection.execute(text(
                "SELECT worker_id, expires_at IS NOT NULL FROM lease WHERE lease_id = :lease"
            ), ids).one() == (None, True)
            assert connection.execute(text("SELECT count(*) FROM worker")).scalar_one() == 0
    finally:
        engine.dispose()


@pytest.mark.parametrize("retained", ["worker", "lease.worker_id"])
def test_retained_worker_data_refuses_the_downgrade(
    empty_database, foundation_command, retained: str,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    # Pinned to this revision rather than `head` (`W55A-SEAL-01`): the whole downgrade is one
    # transaction, so from `0020` a refusal would leave the head at `0020`, not here.
    up = foundation_command(_alembic("upgrade", "0019_execution_workers"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            worker = _register(connection)
            if retained == "lease.worker_id":
                ids = _job_with_attempt(connection, label="held")
                connection.execute(text("INSERT INTO lease (lease_id, job_id, attempt_id, worker_id) "
                                        "VALUES (:lease, :job, :attempt, :worker)"),
                                   {**ids, "worker": worker})
        refused = foundation_command(_alembic("downgrade", "0018_norm_custody"), url)
        assert refused.returncode != 0
        assert "refusing to downgrade 0019_execution_workers" in refused.stderr
        assert retained in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == "0019_execution_workers"
    finally:
        engine.dispose()


def test_an_empty_0019_downgrades_and_restores_the_lease_guard(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    down = foundation_command(_alembic("downgrade", "0018_norm_custody"), url)
    assert down.returncode == 0, down.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.connect() as connection:
            assert _head(connection) == "0018_norm_custody"
            assert connection.execute(text("SELECT to_regclass('public.worker')")).scalar_one() is None
            frozen = connection.execute(text(
                "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_lease_frozen_guard'"
            )).scalar_one()
            assert "worker_id" not in frozen, frozen
    finally:
        engine.dispose()


def test_only_the_heartbeat_and_the_intake_switch_move(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        worker = _register(connection, slots=2)
        params = {"id": worker}
        connection.execute(text("UPDATE worker SET heartbeat_at = clock_timestamp(), "
                                "intake_enabled = false WHERE worker_id = :id"), params)
        for change in ("version = 'other'", "slots = 3", "started_at = started_at - interval '1 hour'"):
            with pytest.raises(DBAPIError) as refused:
                with connection.begin_nested():
                    connection.execute(text(f"UPDATE worker SET {change} WHERE worker_id = :id"), params)
            assert _sqlstate(refused) == "AM003", change
        for bad in ({"slots": 0}, {"version": ""}):
            with pytest.raises(DBAPIError) as refused:
                with connection.begin_nested():
                    _register(connection, **bad)
            assert _sqlstate(refused) == "23514", bad


def test_a_lease_never_changes_its_worker(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        first, second = _register(connection), _register(connection)
        ids = _job_with_attempt(connection, label="fenced")
        connection.execute(text("INSERT INTO lease (lease_id, job_id, attempt_id, worker_id) "
                                "VALUES (:lease, :job, :attempt, :worker)"), {**ids, "worker": first})
        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                connection.execute(text("UPDATE lease SET worker_id = :worker WHERE lease_id = :lease"),
                                   {**ids, "worker": second})
        assert _sqlstate(refused) == "AM003"
        with pytest.raises(DBAPIError) as unknown:
            with connection.begin_nested():
                other = _job_with_attempt(connection, label="unknown-worker")
                connection.execute(text("INSERT INTO lease (lease_id, job_id, attempt_id, worker_id) "
                                        "VALUES (:lease, :job, :attempt, :worker)"),
                                   {**other, "worker": str(WorkerId.new())})
        assert _sqlstate(unknown) == "23503"
        # The control: the heartbeat still moves on a held lease.
        connection.execute(text("UPDATE lease SET heartbeat_at = clock_timestamp() WHERE lease_id = :lease"), ids)
