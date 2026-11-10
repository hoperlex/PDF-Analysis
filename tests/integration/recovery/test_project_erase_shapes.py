"""`PROD-07A-PROJECT-ERASE-CORE-01`: shapes of project the stand in miniature does not hold.

``test_project_erase.py`` runs the tool on the stand of ``purge_seed`` (documents, a published run,
findings, decisions, price and vendor lists, an optimisation pass). A kind of row the erase must
reach is not in it, and it is built here the way the owning code writes it:

* an **executor task** (`EXEC-PULL-01`): it carries what a remote executor was sent and answered
  (``payload``, ``answer_text``), references the run, the Attempt and the connection, and a task that
  is open or claimed is work in flight even when the run, job and attempt around it are terminal
  (`D-215`). The task goes with the project, the connection, revision and runner token stay.

It is measured with the test's own digests, as in the main file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.recovery import product_purge as purge
from scripts.recovery import project_erase as tool
from tests.integration.db.test_executor_pull_migration import _attempt, _connection, _task, _token
from tests.integration.recovery.purge_seed import digest_of
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, _line, invoke, seeded, stand,
)
from tests.integration.recovery.test_project_erase import REFERENCE, apply_flags, count, events, rows, sql


def _terminal_run(stand: Stand, run: str) -> None:
    """Cancel the run, its job and its attempt the way the state machines allow (created/queued -> cancelled)."""
    sql(stand, "UPDATE attempt SET state = 'cancelled', terminal_at = now() WHERE job_id IN "
               "(SELECT job_id FROM job WHERE run_id = :r)", r=run)
    sql(stand, "UPDATE job SET state = 'cancelled', terminal_at = now() WHERE run_id = :r", r=run)
    sql(stand, "UPDATE audit_run SET state = 'cancelled', terminal_at = now() WHERE run_id = :r", r=run)


def _executor_project(stand: Stand) -> tuple[str, str, str, str]:
    """A project with a run, a job, an attempt and an OPEN executor task; returns project, run, task, token."""
    with stand.engine.begin() as connection:
        run, attempt = _attempt(connection)
        connection_id, revision_id = _connection(connection)
        token = _token(connection, connection_id)
        task = _task(connection, connection_id, revision_id, run_id=run, attempt_id=attempt, state="open")
    project = rows(stand, "SELECT project_uid FROM audit_run WHERE run_id = :r", r=run)[0][0]
    return project, run, task, token


def _refused_for(stand: Stand, project: str) -> str:
    code, out, err = invoke(tool, stand, "--project", project)
    assert code == tool.EXIT_REFUSED, (code, out, err)
    return err


def test_an_executor_task_is_work_in_flight_until_it_is_terminal_and_goes_with_the_project(
    stand: Stand, tmp_path: Path
) -> None:
    project, run, task, token = _executor_project(stand)
    _terminal_run(stand, run)
    # run, job and attempt are terminal; the open task alone keeps the project from being erased
    assert "work of this project is not terminal: {'executor_task': 1}" in _refused_for(stand, project)
    # a task claimed by a remote runner counts too (D-215)
    sql(stand, "UPDATE executor_task SET state = 'claimed', claimed_by_token_id = :t, "
               "claim_expires_at = now() + interval '1 minute', claim_count = 1, first_claimed_at = now() "
               "WHERE task_id = :k", t=token, k=task)
    assert "work of this project is not terminal: {'executor_task': 1}" in _refused_for(stand, project)

    sql(stand, "UPDATE executor_task SET state = 'cancelled', terminal_at = now() WHERE task_id = :k", k=task)
    configuration = {t: digest_of(stand.engine, t) for t in sorted(purge.KEEP_EXECUTOR_TABLES)}
    assert configuration["executor_connection"][0] >= 1 and configuration["executor_runner_token"][0] == 1
    other = {p: count(stand, "audit_run", "project_uid = :p", p=p) for p in
             [r[0] for r in rows(stand, "SELECT project_uid FROM project WHERE project_uid <> :p", p=project)]}

    code, out, err = invoke(tool, stand, "--project", project)
    assert code == 0, err
    assert "  executor_task  (1 rows)" in out
    sha = _line(out, "plan-sha256")
    code, out, err = invoke(tool, stand, *apply_flags(project, sha, tmp_path / "dump"))
    assert code == 0, (out, err)

    assert count(stand, "executor_task", "task_id = :k", k=task) == 0
    assert count(stand, "audit_run", "run_id = :r", r=run) == 0 and count(stand, "project", "project_uid = :p", p=project) == 0
    # the connection, its revision, the runner token and the executor journal are configuration: untouched
    assert {t: digest_of(stand.engine, t) for t in sorted(purge.KEEP_EXECUTOR_TABLES)} == configuration
    assert other == {p: count(stand, "audit_run", "project_uid = :p", p=p) for p in other}
    assert [e[0] for e in events(stand)] == ["erasure.requested", "erasure.completed"]
    # the payload a remote executor was sent is in no table any more
    assert rows(stand, "SELECT count(*) FROM executor_task WHERE payload::text LIKE '%user_text%'") == [(0,)]


def test_the_in_flight_guard_has_the_executor_task_in_its_table_and_loses_it_without(
    stand: Stand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: with ``executor_task`` out of ``NON_TERMINAL_STATES`` an open task no longer stops the erase."""
    project, run, task, token = _executor_project(stand)
    _terminal_run(stand, run)
    assert _refused_for(stand, project)
    monkeypatch.setattr(tool, "NON_TERMINAL_STATES", {k: v for k, v in tool.NON_TERMINAL_STATES.items()
                                                       if k != "executor_task"})
    code, out, err = invoke(tool, stand, "--project", project)
    assert code == 0, err  # the mutated table lets the project through while a task is still open
