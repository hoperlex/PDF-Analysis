"""Rows for the connection-limit suites (`EXEC-PAR-QUEUE-01`): a connection, a queued run, a claim.

Database only. No object store is needed: a run's claim reads the run, its Job and its frozen
connection revision, never the document bytes, so the rows are written directly (the way the
migration suites write them) and the claim under test is the shipped ``JobRepository``. Every
write is committed, because the claim under test is made by other sessions and threads.

Loaded by explicit path from ``tests/integration/jobs`` and ``tests/integration/workers`` (the
mechanism ``conftest.py`` uses for the run harness), so the two suites share one copy.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs import RunRepository
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

ACTOR = f"usr_{'0' * 26}"
#: Mid-range, so a test can queue one run above its siblings (the range is -100 to 100).
PRIORITY = 50


def new_connection(sessions: sessionmaker[Session]) -> tuple[str, str]:
    """A committed connection and its first revision: ``(connection_id, revision_id)``."""
    connection_id = str(ExecutorConnectionId.new())
    revision_id = str(ExecutorConnectionRevisionId.new())
    with sessions() as session:
        session.execute(text(
            "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
            "VALUES (:id, 'http_api', 'connection-limit', :actor)"
        ), {"id": connection_id, "actor": ACTOR})
        session.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, "
            "created_by, pin_id, gateway_model, billing, allow_client_documents, "
            "timeout_seconds, api_flavour, base_url, transport) VALUES (:id, :c, 1, :actor, "
            "'claude-opus-5', 'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', "
            "'https://proxy.test', 'direct')"
        ), {"id": revision_id, "c": connection_id, "actor": ACTOR})
        session.commit()
    return connection_id, revision_id


def new_revision(sessions: sessionmaker[Session], connection_id: str, number: int) -> str:
    """A further revision of an existing connection (a run freezes one revision, not the connection)."""
    revision_id = str(ExecutorConnectionRevisionId.new())
    with sessions() as session:
        session.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, "
            "created_by, pin_id, gateway_model, billing, allow_client_documents, "
            "timeout_seconds, api_flavour, base_url, transport) VALUES (:id, :c, :n, :actor, "
            "'claude-opus-5', 'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', "
            "'https://proxy.test', 'direct')"
        ), {"id": revision_id, "c": connection_id, "n": number, "actor": ACTOR})
        session.commit()
    return revision_id


def queue_run(
    sessions: sessionmaker[Session], revision_id: str | None, *, priority: int = PRIORITY,
) -> str:
    """A committed ``queued`` run frozen to ``revision_id`` (or to none) with its queued Job."""
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()), "run": str(RunId.new()),
    }
    with sessions() as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'limit')"), ids)
        session.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:document, :project, 'limit')"
        ), ids)
        session.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"
        ), {**ids, "sha": "a" * 64})
        session.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
            "prompt_bundle_id, provider_mode, frozen_input_digest, connection_revision_id) "
            "VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, :revision)"
        ), {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
            "digest": "b" * 64, "revision": revision_id})
        RunRepository().advance(session, run_id=ids["run"], from_state="created", to_state="queued")
        jobs = JobRepository()
        job_id = jobs.enqueue(session, run_id=ids["run"])
        jobs.set_priority(session, job_id=job_id, priority=priority)
        session.commit()
    return ids["run"]


def claim(sessions: sessionmaker[Session], run_id: str, *, worker_id: str | None = None) -> AttemptAuthority:
    """The shipped claim, committed: the Job is ``running`` and holds an unreleased Lease."""
    with sessions() as session:
        authority = JobRepository(worker_id=worker_id).start_execution(session, run_id=run_id)
        session.commit()
    return authority


def finish(sessions: sessionmaker[Session], authority: AttemptAuthority) -> None:
    """End a claimed run the way a completed one ends: Job and Attempt succeeded, Lease released."""
    with sessions() as session:
        JobRepository().finish_execution(session, authority, publishes_result=True)
        session.commit()


def cancel(sessions: sessionmaker[Session], run_id: str) -> None:
    """Leave nothing queued or active behind: fence the Job and cancel the run, if it is runnable."""
    with sessions() as session:
        state = RunRepository().get(session, run_id).state
        if state in {"queued", "running"}:
            JobRepository().cancel_for_run(session, run_id=run_id)
            RunRepository().terminate(session, run_id=run_id, from_state=state, to_state="cancelled")
            session.commit()


def job_state(sessions: sessionmaker[Session], run_id: str) -> str:
    with sessions() as session:
        return str(session.execute(
            text("SELECT state FROM job WHERE run_id = :run_id"), {"run_id": run_id}
        ).scalar_one())


def attempts(sessions: sessionmaker[Session], run_id: str) -> int:
    with sessions() as session:
        return int(session.execute(text(
            "SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id WHERE j.run_id = :run_id"
        ), {"run_id": run_id}).scalar_one())


def active_runs(sessions: sessionmaker[Session], connection_id: str) -> list[str]:
    """The runs of one connection whose Job is leased, running or in retry_wait, read independently
    of the code under test (it names the three states itself)."""
    with sessions() as session:
        return [str(row[0]) for row in session.execute(text(
            "SELECT r.run_id FROM audit_run r "
            "JOIN executor_connection_revision rev ON rev.revision_id = r.connection_revision_id "
            "JOIN job j ON j.run_id = r.run_id "
            "WHERE rev.connection_id = :c AND j.state IN ('leased', 'running', 'retry_wait') "
            "ORDER BY r.run_id"
        ), {"c": connection_id}).all()]
