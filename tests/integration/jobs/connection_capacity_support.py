"""Rows for the connection-capacity suites (`EXEC2-CAP-01`): a connection whose current revision carries
``max_active_runs``, and a claim made by a second *process*.

Built on ``connection_limit_support`` (a connection, a queued Run, the shipped claim), which this module loads by the
same explicit path every suite uses, so one copy of it serves them all. Database only, like that module. Loaded by
explicit path from ``tests/integration/jobs``, ``tests/integration/executors`` and ``tests/integration/comparison/spend``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.identity import ExecutorConnectionRevisionId

_BASE_NAME = "exec_par_queue_connection_limit_support"
if _BASE_NAME in sys.modules:
    base: ModuleType = sys.modules[_BASE_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_BASE_NAME, Path(__file__).resolve().parent / "connection_limit_support.py")
    assert _spec is not None and _spec.loader is not None
    base = importlib.util.module_from_spec(_spec)
    sys.modules[_BASE_NAME] = base
    _spec.loader.exec_module(base)

ACTOR = base.ACTOR
PRIORITY = base.PRIORITY
queue_run = base.queue_run
claim = base.claim
finish = base.finish
cancel = base.cancel
job_state = base.job_state
attempts = base.attempts
active_runs = base.active_runs
new_revision = base.new_revision


def new_revision_with_capacity(
    sessions: sessionmaker[Session], connection_id: str, number: int, capacity: int | None,
) -> str:
    """Revision ``number`` of ``connection_id``, written with ``max_active_runs = capacity`` (NULL for ``None``).

    The revision table is immutable, so a capacity changes only by a further revision with a higher number; the
    connection's *current* revision is the highest-numbered one, and that is the capacity every statement reads."""
    revision_id = str(ExecutorConnectionRevisionId.new())
    with sessions() as session:
        session.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, "
            "created_by, pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, "
            "api_flavour, base_url, transport, max_active_runs) VALUES (:id, :c, :n, :actor, "
            "'claude-opus-5', 'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', "
            "'https://proxy.test', 'direct', :capacity)"
        ), {"id": revision_id, "c": connection_id, "n": number, "actor": ACTOR, "capacity": capacity})
        session.commit()
    return revision_id


def new_connection(sessions: sessionmaker[Session], capacity: int | None = None) -> tuple[str, str]:
    """A committed connection and its current revision: ``(connection_id, revision_id)``.

    With ``capacity`` ``None`` the only revision has ``max_active_runs`` NULL, a connection written before the
    setting existed, which reads as one. Otherwise a second revision carries the capacity and is the current one
    (Runs queued on ``revision_id`` freeze the current revision; ``base.new_connection`` makes the first)."""
    connection_id, first = base.new_connection(sessions)
    if capacity is None:
        return connection_id, first
    return connection_id, new_revision_with_capacity(sessions, connection_id, 2, capacity)


def connection_of_revision(sessions: sessionmaker[Session], revision_id: str) -> str:
    with sessions() as session:
        return str(session.execute(
            text("SELECT connection_id FROM executor_connection_revision WHERE revision_id = :r"), {"r": revision_id}
        ).scalar_one())


def claim_in_a_second_process(run_id: str) -> subprocess.Popen[str]:
    """Start the shipped claim of ``run_id`` in a **separate Python process** with its own database connection.

    The child prints one JSON line: ``{"result": "claimed"}`` or ``{"result": "refused", "code": ...}``, or
    ``{"result": "failed", "error": <class name>}`` for anything else. The database URL travels in the
    environment (``DATABASE_URL``, which the run-suite harness has already loaded from ``.env`` if it was not
    exported), never on the command line."""
    import auditmanager

    source = str(Path(auditmanager.__file__).resolve().parents[1])
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([source, os.environ.get("PYTHONPATH", "")]).strip(os.pathsep)}
    return subprocess.Popen(
        [sys.executable, "-c", _CHILD, run_id], env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def child_result(process: subprocess.Popen[str], *, timeout: float = 60.0) -> dict[str, Any]:
    out, err = process.communicate(timeout=timeout)
    assert process.returncode == 0, f"the claiming process exited {process.returncode}: {err[-500:]}"
    return json.loads(out.strip().splitlines()[-1])


_CHILD = """
import json, os, sys
from sqlalchemy.orm import sessionmaker
from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
sessions = sessionmaker(bind=engine, expire_on_commit=False, future=True)
answer = {"result": "failed", "error": "none"}
try:
    with sessions() as session:
        try:
            JobRepository().start_execution(session, run_id=sys.argv[1])
            session.commit()
            answer = {"result": "claimed"}
        except ExecutionNotClaimed as refusal:
            session.rollback()
            answer = {"result": "refused", "code": refusal.code.value}
except BaseException as failure:
    answer = {"result": "failed", "error": type(failure).__name__}
finally:
    engine.dispose()
print(json.dumps(answer))
"""
