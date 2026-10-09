"""0017 upgrade on populated 0016 data and its guarded rollback boundary."""

from __future__ import annotations

from sqlalchemy import text

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId, AttemptId, DocumentUid, JobId, LeaseId,
    ProjectUid, PromptBundleId, RunId, VersionUid,
)


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _run(connection, *, suffix: str) -> str:
    project_id, document_id, version_id, run_id = (
        str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new()), str(RunId.new())
    )
    connection.execute(text("INSERT INTO project(project_uid, name) VALUES (:id, :name)"),
                       {"id": project_id, "name": f"queue-{suffix}"})
    connection.execute(text("INSERT INTO document(document_uid, project_uid, display_title) "
                            "VALUES (:id, :project, :title)"),
                       {"id": document_id, "project": project_id, "title": suffix})
    connection.execute(text("INSERT INTO document_version(version_uid, document_uid, "
                            "version_ordinal, media_type, byte_size, sha256, page_count) "
                            "VALUES (:id, :document, 1, 'application/pdf', 1, :sha, 1)"),
                       {"id": version_id, "document": document_id, "sha": "a" * 64})
    connection.execute(text("INSERT INTO audit_run(run_id, project_uid, version_uid, "
                            "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
                            "VALUES (:id, :project, :version, :profile, :bundle, 'recorded', :digest)"),
                       {"id": run_id, "project": project_id, "version": version_id,
                        "profile": str(AnalysisProfileId.new()),
                        "bundle": str(PromptBundleId.new()), "digest": "b" * 64})
    connection.execute(text("UPDATE audit_run SET state = 'queued' WHERE run_id = :id"),
                       {"id": run_id})
    return run_id


def test_populated_0016_upgrade_backfills_job_expires_lease_and_refuses_downgrade(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_0016 = foundation_command(_alembic("upgrade", "0016_release_notes"), url)
    assert at_0016.returncode == 0, at_0016.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            queued_without_job = _run(connection, suffix="without-job")
            leased_run = _run(connection, suffix="unreleased-lease")
            job_id, attempt_id, lease_id = str(JobId.new()), str(AttemptId.new()), str(LeaseId.new())
            connection.execute(text("INSERT INTO job(job_id, run_id, state) "
                                    "VALUES (:job, :run, 'queued')"),
                               {"job": job_id, "run": leased_run})
            connection.execute(text("INSERT INTO attempt(attempt_id, job_id, execution_token) "
                                    "VALUES (:attempt, :job, 'migration-test-token')"),
                               {"attempt": attempt_id, "job": job_id})
            connection.execute(text("INSERT INTO lease(lease_id, job_id, attempt_id) "
                                    "VALUES (:lease, :job, :attempt)"),
                               {"lease": lease_id, "job": job_id, "attempt": attempt_id})
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0017_execution_queue"
            assert connection.execute(text("SELECT count(*) FROM job WHERE run_id = :run"),
                                      {"run": queued_without_job}).scalar_one() == 1
            assert connection.execute(text("SELECT expires_at <= statement_timestamp() "
                                           "AND heartbeat_at = acquired_at FROM lease "
                                           "WHERE lease_id = :lease"),
                                      {"lease": lease_id}).scalar_one() is True
            assert connection.execute(text("SELECT count(*) FROM execution_control")).scalar_one() == 0
        refused = foundation_command(_alembic("downgrade", "0016_release_notes"), url)
        assert refused.returncode != 0
        assert "refusing to downgrade 0017_execution_queue" in refused.stderr
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0017_execution_queue"
    finally:
        engine.dispose()


def test_empty_0017_downgrades_and_restores_old_frozen_guard(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    down = foundation_command(_alembic("downgrade", "0016_release_notes"), url)
    assert down.returncode == 0, down.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0016_release_notes"
            assert connection.execute(text("SELECT to_regclass('public.execution_control')")).scalar_one() is None
            assert connection.execute(text("SELECT count(*) FROM pg_trigger "
                                           "WHERE tgname = 'trg_audit_run_frozen_guard' "
                                           "AND NOT tgisinternal")).scalar_one() == 1
    finally:
        engine.dispose()


def test_existing_job_writer_gets_a_live_default_lease(migrated_engine) -> None:
    with migrated_engine.begin() as connection:
        run_id = _run(connection, suffix="stage-a-writer")
        job_id, attempt_id, lease_id = str(JobId.new()), str(AttemptId.new()), str(LeaseId.new())
        connection.execute(text("INSERT INTO job(job_id, run_id) VALUES (:job, :run)"),
                           {"job": job_id, "run": run_id})
        connection.execute(text("INSERT INTO attempt(attempt_id, job_id, execution_token) "
                                "VALUES (:attempt, :job, 'stage-a-compatible-token')"),
                           {"attempt": attempt_id, "job": job_id})
        # The current repository INSERT has exactly these three columns.
        connection.execute(text("INSERT INTO lease(lease_id, job_id, attempt_id) "
                                "VALUES (:lease, :job, :attempt)"),
                           {"lease": lease_id, "job": job_id, "attempt": attempt_id})
        assert connection.execute(text(
            "SELECT expires_at > statement_timestamp(), heartbeat_at IS NOT NULL "
            "FROM lease WHERE lease_id = :lease"
        ), {"lease": lease_id}).one() == (True, True)
