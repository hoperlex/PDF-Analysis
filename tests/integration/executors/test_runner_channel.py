"""`EXEC-PULL-01`: the pull channel over the served application and real rows.

The runner speaks to ``build_router(runner=RunnerAdapter(...))`` through the real middlewares,
the real authorization seam and the real envelope; the worker side is the real
:class:`~auditmanager.executors.pull.PullAdapter` on the same rows. A runner and the worker
that waits for it share one session here, so the runner's moves are played *while the worker
waits* (``pull.time.sleep`` is the hook), which keeps every flow deterministic and free of
threads. Nothing calls a model.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from contextlib import nullcontext
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors import pull
from auditmanager.executors.public import (
    PullAdapter,
    current_revision,
    probe_pull,
    RunnerPrincipal,
)
from auditmanager.executors.runner_repository import RunnerRepository
from auditmanager.jobs.lease import AttemptContext
from auditmanager.shared.identity import (
    AnalysisProfileId, AttemptId, DocumentUid, ExecutorTaskId, JobId, ProjectUid, PromptBundleId,
    RunId, VersionUid,
)
from tests.integration.executors.conftest import ADMIN, driver

Request, dispatch = driver.Request, driver.dispatch

MODEL = "claude-opus-5"
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}},
          "required": ["observations"], "additionalProperties": False}
REQUEST = ModelRequest(model_id=MODEL, body={
    "model": MODEL, "max_tokens": 16, "system": "SYSTEM-PROMPT",
    "messages": [{"role": "user", "content": "USER-TEXT"}],
    "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
})
PULL_SETTINGS = {
    "pin_id": MODEL, "gateway_model": MODEL, "billing": "not_metered",
    "allow_client_documents": False, "timeout_seconds": 60,
    "pull_client": "claude_code_session", "answer_deadline_seconds": 60, "max_claimed_tasks": 1,
}
GOOD = '{"observations": []}'


# -- the harness ------------------------------------------------------------------------------


@pytest.fixture
def surface(session: Session, admin_account: str, rings):
    from contextlib import nullcontext as ctx

    from auditmanager.api.routers import build_router
    from auditmanager.bootstrap.adapters import ExecutorAdapter
    from auditmanager.bootstrap.runner import RunnerAdapter

    def sessions():
        return ctx(session)

    return driver.Surface(build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        executors=ExecutorAdapter(sessions, ring=rings.public),  # type: ignore[arg-type]
        runner=RunnerAdapter(sessions),  # type: ignore[arg-type]
    ))


def admin_call(surface, method: str, path: str, body: Any = None):
    headers = {"Content-Type": "application/json", "Idempotency-Key": f"pull-{uuid4().hex}"}
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def runner_call(surface, token: str | None, path: str, body: Any = None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    payload = b"{}" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build("POST", path, headers=headers, body=payload),
                    credential=None)


def make_connection(surface, *, kind: str = "pull", settings: dict | None = None) -> str:
    created = admin_call(surface, "POST", "/executor-connections",
                         {"kind": kind, "display_name": "Claude Code"})
    assert created.status == 201, created.body
    connection_id = created.json()["connection_id"]
    revised = admin_call(surface, "POST", f"/executor-connections/{connection_id}/revisions",
                         settings or PULL_SETTINGS)
    assert revised.status == 201, revised.body
    return connection_id


def issue(surface, connection_id: str, **body: Any) -> tuple[str, dict]:
    issued = admin_call(surface, "POST", f"/executor-connections/{connection_id}/runner-tokens", body)
    assert issued.status == 201, issued.body
    answer = issued.json()
    return answer["token"], answer["runner_token"]


def claim(surface, token: str, wait: int = 0):
    return runner_call(surface, token, "/runner/tasks/claim", {"wait_seconds": wait})


def live_attempt(session: Session) -> dict[str, str]:
    """A run with a job whose current Attempt is running: the Attempt a pull task waits in."""
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "run": str(RunId.new()),
           "job": str(JobId.new()), "attempt": str(AttemptId.new())}
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'pull')"), ids)
    session.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                         "VALUES (:document, :project, 'pull')"), ids)
    session.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                         "media_type, byte_size, sha256, page_count) VALUES (:version, :document, 1, "
                         "'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
    session.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
        "prompt_bundle_id, provider_mode, frozen_input_digest) VALUES (:run, :project, :version, "
        ":profile, :bundle, 'live', :digest)"
    ), {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
        "digest": "b" * 64})
    session.execute(text("INSERT INTO job (job_id, run_id) VALUES (:job, :run)"), ids)
    session.execute(text("INSERT INTO attempt (attempt_id, job_id, execution_token) "
                         "VALUES (:attempt, :job, :token)"), {**ids, "token": f"tok-{ids['attempt']}"})
    session.execute(text("UPDATE attempt SET state = 'leased' WHERE attempt_id = :attempt"), ids)
    session.execute(text("UPDATE attempt SET state = 'running' WHERE attempt_id = :attempt"), ids)
    session.execute(text("UPDATE job SET state = 'leased', current_attempt_id = :attempt "
                         "WHERE job_id = :job"), ids)
    session.execute(text("UPDATE job SET state = 'running' WHERE job_id = :job"), ids)
    return {"run_id": ids["run"], "attempt_id": ids["attempt"], "job_id": ids["job"]}


def adapter_for(session: Session, connection_id: str, attempt: dict[str, str], *, used: float = 0.0,
                deadline: int | None = None) -> PullAdapter:
    revision = current_revision(session, connection_id)
    assert revision is not None
    if deadline is not None:
        from dataclasses import replace

        revision = replace(revision, settings=replace(
            revision.settings, answer_deadline_seconds=deadline))
    context = AttemptContext(run_id=attempt["run_id"], attempt_id=attempt["attempt_id"],
                             started_monotonic=time.monotonic() - used)
    return PullAdapter(session_factory=lambda: nullcontext(session), revision=revision,  # type: ignore[arg-type,return-value]
                       context=context, poll_seconds=0.01)


def play(monkeypatch: pytest.MonkeyPatch, moves) -> None:
    """Run ``moves()`` once, the first time the worker waits."""
    done: list[bool] = []
    real = time.sleep

    def sleep(seconds: float) -> None:
        if not done:
            done.append(True)
            moves()
        real(min(seconds, 0.005))

    monkeypatch.setattr(pull.time, "sleep", sleep)


def task_row(session: Session, task_id: str | None = None) -> dict[str, Any]:
    query = "SELECT * FROM executor_task" + (" WHERE task_id = :id" if task_id else
                                             " ORDER BY created_at DESC LIMIT 1")
    return dict(session.execute(text(query), {"id": task_id}).mappings().one())


# -- issuing and revoking tokens ----------------------------------------------------------------


def test_a_token_is_shown_once_stored_only_as_a_hash_and_never_read_back(session, surface) -> None:
    connection_id = make_connection(surface)
    key = f"pull-{uuid4().hex}"
    headers = {"Content-Type": "application/json", "Idempotency-Key": key}
    path = f"/executor-connections/{connection_id}/runner-tokens"
    first = dispatch(surface, Request.build("POST", path, headers=headers, body=b"{}"))
    assert first.status == 201
    value = first.json()["token"]
    meta = first.json()["runner_token"]
    assert value.startswith(meta["token_prefix"] + "_") and len(value) == 56
    assert {"revoked_at", "revoked_by", "last_seen_at", "last_seen_address"}.isdisjoint(meta)
    stored = session.execute(text(
        "SELECT token_hash, token_prefix FROM executor_runner_token WHERE token_id = :id"
    ), {"id": meta["token_id"]}).one()
    assert bytes(stored[0]) == hashlib.sha256(value.encode()).digest()
    assert value.encode() not in bytes(stored[0]) and stored[1] == meta["token_prefix"]

    # An identical repeat cannot show it again: the value is not stored.
    again = dispatch(surface, Request.build("POST", path, headers=headers, body=b"{}"))
    assert again.status == 409 and again.json()["details"] == {"conflict_reason": "token_shown_once"}
    assert value not in again.body.decode()
    # No read of the connection returns it either.
    detail = admin_call(surface, "GET", f"/executor-connections/{connection_id}")
    assert detail.status == 200 and value not in detail.body.decode()
    listed = detail.json()["runner_tokens"]
    assert [t["token_id"] for t in listed] == [meta["token_id"]] and detail.json()["open_task_count"] == 0


def test_the_default_lifetime_is_thirty_days_and_a_range_is_enforced(session, surface) -> None:
    connection_id = make_connection(surface)
    _, meta = issue(surface, connection_id)
    days = session.execute(text(
        "SELECT extract(epoch FROM (expires_at - created_at)) / 86400 "
        "FROM executor_runner_token WHERE token_id = :id"), {"id": meta["token_id"]}).scalar_one()
    assert round(float(days)) == 30
    for bad in (0, 366):
        refused = admin_call(surface, "POST", f"/executor-connections/{connection_id}/runner-tokens",
                             {"expires_in_days": bad})
        assert refused.status == 422, refused.body


def test_only_a_pull_connection_takes_a_token_and_only_an_administrator_issues_one(
    session, surface,
) -> None:
    http = make_connection(surface, kind="http_api", settings={
        "pin_id": MODEL, "gateway_model": MODEL, "billing": "metered", "allow_client_documents": False,
        "timeout_seconds": 60, "api_flavour": "openai_chat", "base_url": "https://proxy.test/v1",
        "transport": "direct"})
    refused = admin_call(surface, "POST", f"/executor-connections/{http}/runner-tokens", {})
    assert refused.status == 422 and refused.json()["details"]["constraint"] == "kind_not_pull"
    surface.router.credentials.roles = frozenset({"expert"})
    denied = admin_call(surface, "POST", f"/executor-connections/{http}/runner-tokens", {})
    assert denied.status == 403


def test_a_revoked_token_gets_401_everywhere_and_revoking_twice_is_the_same_answer(
    session, surface,
) -> None:
    connection_id = make_connection(surface)
    token, meta = issue(surface, connection_id)
    assert claim(surface, token).status == 204
    revoked = admin_call(
        surface, "POST",
        f"/executor-connections/{connection_id}/runner-tokens/{meta['token_id']}/revoke")
    assert revoked.status == 200 and revoked.json()["revoked_at"]
    again = admin_call(
        surface, "POST",
        f"/executor-connections/{connection_id}/runner-tokens/{meta['token_id']}/revoke")
    assert again.status == 200 and again.json()["revoked_at"] == revoked.json()["revoked_at"]
    for path in ("/runner/tasks/claim", "/runner/tasks/ext_01M2545JSD15ETSNNV904X991K/extend",
                 "/runner/tasks/ext_01M2545JSD15ETSNNV904X991K/answer",
                 "/runner/tasks/ext_01M2545JSD15ETSNNV904X991K/fail"):
        answer = runner_call(surface, token, path, {"wait_seconds": 0, "output_text": "{}",
                                                    "model": MODEL, "reason": "x"})
        assert answer.status == 401 and answer.json()["error_code"] == "authentication_required", path


def test_an_expired_token_and_a_token_of_an_archived_connection_are_refused(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    # A token written already past its expiry (the column is frozen, so it is inserted so).
    from auditmanager.executors.runner import generate_token, hash_token

    stale, prefix = generate_token()
    session.execute(text(
        "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, token_hash, "
        "created_at, created_by, expires_at) VALUES (:id, :c, :p, :h, now() - interval '2 days', "
        ":actor, now() - interval '1 day')"
    ), {"id": "ern_" + "0" * 26, "c": connection_id, "p": prefix, "h": hash_token(stale),
        "actor": ADMIN})
    assert claim(surface, stale).status == 401
    assert claim(surface, token).status == 204
    archived = admin_call(surface, "POST", f"/executor-connections/{connection_id}/archive")
    assert archived.status == 200
    assert claim(surface, token).status == 401


def test_a_user_credential_is_not_a_runner_token_and_a_runner_token_is_not_a_user_credential(
    session, surface,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    # The suite's own user credential on a runner operation.
    as_user = dispatch(surface, Request.build(
        "POST", "/runner/tasks/claim", headers={"Content-Type": "application/json"}, body=b"{}"))
    assert as_user.status == 401
    # A runner token on user operations, reads and writes alike.
    for method, path in (("GET", "/executor-connections"), ("POST", "/executor-connections"),
                         ("GET", "/executor-routes")):
        answer = dispatch(surface, Request.build(
            method, path, headers={"Authorization": f"Bearer {token}",
                                   "Idempotency-Key": "k-" + uuid4().hex,
                                   "Content-Type": "application/json"}, body=b"{}"),
            credential=None)
        assert answer.status == 401, (path, answer.body)


def test_a_token_that_is_seen_records_when_and_from_where(session, surface) -> None:
    connection_id = make_connection(surface)
    token, meta = issue(surface, connection_id)
    answer = dispatch(surface, Request.build(
        "POST", "/runner/tasks/claim",
        headers={"Authorization": f"Bearer {token}", "X-Real-IP": "203.0.113.9",
                 "Content-Type": "application/json"}, body=b'{"wait_seconds": 0}'),
        credential=None)
    assert answer.status == 204
    seen = session.execute(text(
        "SELECT last_seen_at IS NOT NULL, last_seen_address FROM executor_runner_token "
        "WHERE token_id = :id"), {"id": meta["token_id"]}).one()
    assert tuple(seen) == (True, "203.0.113.9")


# -- the worker and the runner --------------------------------------------------------------------


def test_an_answered_task_completes_the_call_with_the_declared_model(
    session, surface, monkeypatch,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    seen: dict[str, Any] = {}

    def runner() -> None:
        claimed = claim(surface, token)
        assert claimed.status == 200, claimed.body
        task = claimed.json()
        seen.update(task)
        answered = runner_call(surface, token, f"/runner/tasks/{task['task_id']}/answer",
                               {"output_text": GOOD, "model": MODEL,
                                "input_tokens": 1234, "output_tokens": 321})
        assert answered.status == 200 and answered.json() == {
            "task_id": task["task_id"], "state": "answered"}

    play(monkeypatch, runner)
    response = adapter_for(session, connection_id, attempt).complete(REQUEST)
    assert response.output_text == GOOD and (response.input_tokens, response.output_tokens) == (1234, 321)
    assert response.reported_cost_usd is None
    assert seen["system"] == "SYSTEM-PROMPT" and seen["user_text"] == "USER-TEXT"
    assert seen["model"] == MODEL and seen["output_schema"] == SCHEMA
    row = task_row(session)
    assert (row["state"], row["origin"], row["run_id"], row["attempt_id"], row["declared_model"],
            row["claim_count"]) == ("answered", "run_call", attempt["run_id"],
                                    attempt["attempt_id"], MODEL, 1)
    assert row["terminal_at"] is not None and row["payload"] is not None


def test_a_wrong_declared_model_is_422_model_identity_mismatch_and_keeps_the_claim(
    session, surface,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    adapter = adapter_for(session, connection_id, attempt)
    task = adapter._write_task({"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    claimed = claim(surface, token).json()
    assert claimed["task_id"] == task.task_id
    wrong = runner_call(surface, token, f"/runner/tasks/{task.task_id}/answer",
                        {"output_text": GOOD, "model": "claude-sonnet-5"})
    assert wrong.status == 422 and wrong.json()["error_code"] == "model_identity_mismatch"
    assert "claude-sonnet-5" not in wrong.body.decode()
    held = task_row(session, task.task_id)
    assert held["state"] == "claimed" and held["answer_text"] is None
    extended = runner_call(surface, token, f"/runner/tasks/{task.task_id}/extend")
    assert extended.status == 200, "the claim was kept"
    right = runner_call(surface, token, f"/runner/tasks/{task.task_id}/answer",
                        {"output_text": GOOD, "model": MODEL})
    assert right.status == 200


def test_an_answer_that_violates_the_schema_is_422_and_the_claim_is_kept(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    task = adapter_for(session, connection_id, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    claim(surface, token)
    sentinel = "SENTINEL-ANSWER-0451"
    for bad, keyword in (('{"observations": 1}', "type"), ('{}', "required"),
                         (json.dumps({"observations": [], sentinel: 1}), "additionalProperties"),
                         ("```json\n{}\n```", "json")):
        refused = runner_call(surface, token, f"/runner/tasks/{task.task_id}/answer",
                              {"output_text": bad, "model": MODEL})
        body = refused.body.decode()
        assert refused.status == 422 and refused.json()["error_code"] == "validation_failed", body
        assert keyword in refused.json()["message"] and sentinel not in body
    assert task_row(session, task.task_id)["state"] == "claimed"
    assert runner_call(surface, token, f"/runner/tasks/{task.task_id}/answer",
                       {"output_text": GOOD, "model": MODEL}).status == 200


def test_a_double_submit_is_idempotent_and_a_different_answer_is_a_conflict(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    task = adapter_for(session, connection_id, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    claim(surface, token)
    path = f"/runner/tasks/{task.task_id}/answer"
    body = {"output_text": GOOD, "model": MODEL}
    assert runner_call(surface, token, path, body).status == 200
    assert runner_call(surface, token, path, body).json()["state"] == "answered"
    other = runner_call(surface, token, path, {"output_text": '{"observations": [1]}', "model": MODEL})
    assert other.status == 409 and other.json()["details"] == {"conflict_reason": "answer_differs"}
    assert runner_call(surface, token, f"/runner/tasks/{task.task_id}/fail",
                       {"reason": "late"}).status == 409


def test_a_token_of_another_connection_claims_nothing_and_touches_nothing(session, surface) -> None:
    mine, other = make_connection(surface), make_connection(surface)
    token_mine, _ = issue(surface, mine)
    token_other, _ = issue(surface, other)
    attempt = live_attempt(session)
    task = adapter_for(session, mine, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    assert claim(surface, token_other).status == 204, "the other connection's token sees no task"
    for suffix, body in (("extend", None), ("fail", {"reason": "x"}),
                         ("answer", {"output_text": GOOD, "model": MODEL})):
        answer = runner_call(surface, token_other, f"/runner/tasks/{task.task_id}/{suffix}", body)
        assert answer.status == 404 and answer.json()["error_code"] == "not_found", suffix
    assert task_row(session, task.task_id)["state"] == "open"
    assert claim(surface, token_mine).json()["task_id"] == task.task_id


def test_a_task_nobody_takes_before_the_deadline_is_no_executor_online(session, surface) -> None:
    connection_id = make_connection(surface)
    attempt = live_attempt(session)
    # 62.5 s of the 900 s watchdog left: the window is 2.5 s after the 60 s margin.
    adapter = adapter_for(session, connection_id, attempt, used=900 - 62.5)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter.complete(REQUEST)
    assert (raised.value.dispatch_class, raised.value.retry_safe) == ("not_sent", False)
    assert raised.value.detail_fields == {"dependency": "no_executor_online"}
    assert task_row(session)["state"] == "expired"


def test_a_late_answer_to_an_expired_task_is_refused(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    with pytest.raises(ProxyDispatchError):
        adapter_for(session, connection_id, attempt, used=900 - 62.5).complete(REQUEST)
    expired = task_row(session)
    late = runner_call(surface, token, f"/runner/tasks/{expired['task_id']}/answer",
                       {"output_text": GOOD, "model": MODEL})
    assert late.status == 409 and late.json()["details"]["conflict_reason"] == "task_expired"
    assert task_row(session, expired["task_id"])["state"] == "expired"


def test_a_claimed_task_that_is_never_answered_is_outcome_unknown(
    session, surface, monkeypatch,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    seen: list[str] = []

    def take() -> None:
        seen.append(claim(surface, token).json()["task_id"])

    adapter = adapter_for(session, connection_id, attempt, used=900 - 62.5)
    play(monkeypatch, take)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter.complete(REQUEST)
    assert raised.value.dispatch_class == "outcome_unknown"
    assert raised.value.detail_fields == {"dependency": "executor_deadline"}
    assert task_row(session)["claim_count"] == 1


def test_a_runner_that_fails_a_claimed_task_ends_the_wait_as_outcome_unknown(
    session, surface, monkeypatch,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)

    def runner() -> None:
        task = claim(surface, token).json()
        failed = runner_call(surface, token, f"/runner/tasks/{task['task_id']}/fail",
                             {"reason": "model_mismatch: running claude-sonnet-5, task pins claude-opus-5"})
        assert failed.status == 200 and failed.json()["state"] == "failed"
        assert runner_call(surface, token, f"/runner/tasks/{task['task_id']}/fail",
                           {"reason": "again"}).json()["state"] == "failed"

    play(monkeypatch, runner)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter_for(session, connection_id, attempt).complete(REQUEST)
    assert raised.value.dispatch_class == "outcome_unknown"
    assert task_row(session)["state"] == "failed"


# -- claims ---------------------------------------------------------------------------------------


def test_a_lapsed_claim_returns_the_task_to_open_and_the_old_claimant_is_told_so(
    session, surface,
) -> None:
    connection_id = make_connection(surface)
    first, _ = issue(surface, connection_id)
    second, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    task = adapter_for(session, connection_id, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    assert claim(surface, first).json()["task_id"] == task.task_id
    assert claim(surface, second).status == 204, "a held claim is not taken"
    session.execute(text("UPDATE executor_task SET claim_expires_at = clock_timestamp() - interval '1 second' "
                         "WHERE task_id = :id"), {"id": task.task_id})
    taken = claim(surface, second)
    assert taken.status == 200 and taken.json()["task_id"] == task.task_id
    row = task_row(session, task.task_id)
    assert row["claim_count"] == 2
    stale = runner_call(surface, first, f"/runner/tasks/{task.task_id}/answer",
                        {"output_text": GOOD, "model": MODEL})
    assert stale.status == 409 and stale.json()["details"]["conflict_reason"] == "claim_lost"
    assert runner_call(surface, first, f"/runner/tasks/{task.task_id}/extend").status == 409
    assert runner_call(surface, second, f"/runner/tasks/{task.task_id}/answer",
                       {"output_text": GOOD, "model": MODEL}).status == 200


def test_a_token_holding_its_only_claim_is_given_the_same_task_again(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    adapter = adapter_for(session, connection_id, attempt)
    first_task = adapter._write_task({"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    adapter._write_task({"system": "s2", "user_text": "u2", "output_schema": SCHEMA}, 60)
    one = claim(surface, token).json()
    again = claim(surface, token).json()
    assert one["task_id"] == again["task_id"] == first_task.task_id
    assert task_row(session, first_task.task_id)["claim_count"] == 1


def test_an_extension_never_passes_the_deadline(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    task = adapter_for(session, connection_id, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 30)
    claimed = claim(surface, token).json()
    assert claimed["claim_expires_at"] <= claimed["deadline_at"]
    extended = runner_call(surface, token, f"/runner/tasks/{task.task_id}/extend").json()
    assert extended["claim_expires_at"] <= claimed["deadline_at"]


def test_the_task_of_an_attempt_that_is_gone_is_never_served(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    task = adapter_for(session, connection_id, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    session.execute(text("UPDATE attempt SET state = 'lost', terminal_at = now() "
                         "WHERE attempt_id = :a"), {"a": attempt["attempt_id"]})
    assert claim(surface, token).status == 204
    assert task_row(session, task.task_id)["state"] == "cancelled"


def test_a_task_that_is_not_the_current_attempts_is_not_served(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    attempt = live_attempt(session)
    adapter_for(session, connection_id, attempt)._write_task(
        {"system": "s", "user_text": "u", "output_schema": SCHEMA}, 60)
    session.execute(text("UPDATE job SET current_attempt_id = NULL WHERE job_id = :j"),
                    {"j": attempt["job_id"]})
    assert claim(surface, token).status == 204


def test_the_claim_wait_is_bounded_to_twenty_five_seconds(surface, session) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    assert claim(surface, token, wait=26).status == 422
    assert claim(surface, token, wait=-1).status == 422


# -- the probe ------------------------------------------------------------------------------------


def test_the_probe_is_answered_by_a_runner_that_declares_the_revisions_model(
    session, surface, monkeypatch,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    requested = admin_call(surface, "POST", f"/executor-connections/{connection_id}/probes")
    assert requested.status == 202
    probe_id = requested.json()["probe_id"]
    revision = current_revision(session, connection_id)
    assert revision is not None

    def runner() -> None:
        task = claim(surface, token).json()
        assert task["model"] == MODEL
        echo = task["user_text"]
        assert runner_call(surface, token, f"/runner/tasks/{task['task_id']}/answer",
                           {"output_text": json.dumps({"echo": echo}), "model": MODEL}).status == 200

    play(monkeypatch, runner)
    result = probe_pull(lambda: nullcontext(session), revision, probe_id, poll_seconds=0.01)  # type: ignore[arg-type,return-value]
    assert (result.outcome, result.reported_model, result.identity_basis) == ("ok", MODEL, "declared")
    row = task_row(session)
    assert (row["origin"], row["probe_id"], row["run_id"], row["state"]) == (
        "probe", probe_id, None, "answered")


def test_a_probe_nobody_claims_is_no_runner_online(session, surface) -> None:
    connection_id = make_connection(surface)
    requested = admin_call(surface, "POST", f"/executor-connections/{connection_id}/probes")
    revision = current_revision(session, connection_id)
    assert revision is not None
    result = probe_pull(lambda: nullcontext(session), revision, requested.json()["probe_id"],  # type: ignore[arg-type,return-value]
                        claim_seconds=0.2, answer_seconds=0.2, poll_seconds=0.05)
    assert result.outcome == "no_runner_online"
    assert task_row(session)["state"] == "expired"


# -- retention and secrecy ------------------------------------------------------------------------


def test_the_payload_and_the_answer_are_cleared_a_week_after_the_task_ends(session, surface) -> None:
    connection_id = make_connection(surface)
    revision = current_revision(session, connection_id)
    assert revision is not None

    def terminal(age_days: int) -> str:
        task_id = str(ExecutorTaskId.new())
        session.execute(text(
            "INSERT INTO executor_task (task_id, connection_id, revision_id, origin, probe_id, state, "
            "expected_model, payload, created_at, deadline_at, claim_count, terminal_at, "
            "declared_model, answer_text) "
            "SELECT :id, :c, :r, 'probe', p.probe_id, 'answered', :m, "
            "CAST('{\"system\": \"s\", \"user_text\": \"u\", \"output_schema\": {}}' AS jsonb), "
            "now() - make_interval(days => :age + 1), now() - make_interval(days => :age) "
            "+ interval '1 minute', 1, now() - make_interval(days => :age), :m, 'ANSWER' "
            "FROM executor_probe p WHERE p.connection_id = :c ORDER BY p.requested_at LIMIT 1"
        ), {"id": task_id, "c": connection_id, "r": revision.revision_id, "m": MODEL, "age": age_days})
        return task_id

    admin_call(surface, "POST", f"/executor-connections/{connection_id}/probes")
    old, young = terminal(8), terminal(6)
    cleared = RunnerRepository().clear_terminal_payloads(session, older_than_days=7)
    assert cleared == 1
    gone, kept = task_row(session, old), task_row(session, young)
    assert gone["payload"] is None and gone["answer_text"] is None and gone["payload_cleared_at"]
    assert gone["state"] == "answered" and gone["declared_model"] == MODEL, "the row stays as the trail"
    assert kept["payload"] is not None and kept["answer_text"] == "ANSWER"


def test_the_sentinel_token_is_in_no_response_event_log_or_stored_row(
    session, surface, monkeypatch, caplog,
) -> None:
    caplog.set_level(logging.DEBUG)
    connection_id = make_connection(surface)
    key = f"pull-{uuid4().hex}"
    issued = dispatch(surface, Request.build(
        "POST", f"/executor-connections/{connection_id}/runner-tokens",
        headers={"Content-Type": "application/json", "Idempotency-Key": key}, body=b"{}"))
    sentinel = issued.json()["token"]
    token_id = issued.json()["runner_token"]["token_id"]
    attempt = live_attempt(session)
    bodies: list[str] = []

    def runner() -> None:
        for answer in (
            claim(surface, sentinel),
            runner_call(surface, "amr_wrongwrg_" + "x" * 43, "/runner/tasks/claim"),
        ):
            bodies.append(answer.body.decode() + str(answer.headers))
        task = claim(surface, sentinel).json()
        for suffix, body in (("extend", None), ("answer", {"output_text": "no", "model": MODEL}),
                             ("answer", {"output_text": GOOD, "model": "other"}),
                             ("answer", {"output_text": GOOD, "model": MODEL})):
            answer = runner_call(surface, sentinel, f"/runner/tasks/{task['task_id']}/{suffix}", body)
            bodies.append(answer.body.decode() + str(answer.headers))
        revoked = admin_call(surface, "POST", f"/executor-connections/{connection_id}/runner-tokens/"
                                              f"{token_id}/revoke")
        bodies.append(revoked.body.decode())
        bodies.append(claim(surface, sentinel).body.decode())
        bodies.append(admin_call(surface, "GET", f"/executor-connections/{connection_id}").body.decode())
        bodies.append(admin_call(surface, "GET", "/executor-connections").body.decode())

    play(monkeypatch, runner)
    adapter_for(session, connection_id, attempt).complete(REQUEST)
    assert bodies and all(sentinel not in body for body in bodies)
    assert sentinel not in caplog.text
    for table_query in (
        "SELECT payload::text FROM audit_event",
        "SELECT outcome::text FROM command_record",
        "SELECT t::text FROM executor_runner_token t",
        "SELECT t::text FROM executor_task t",
    ):
        rows = [row[0] or "" for row in session.execute(text(table_query)).all()]
        assert not any(sentinel in row for row in rows), table_query
    events = [row[0] for row in session.execute(text(
        "SELECT event_type FROM audit_event WHERE event_type LIKE 'executor.runner_token%' "
        "ORDER BY occurred_at"))]
    assert sorted(events) == ["executor.runner_token_issued", "executor.runner_token_revoked"]
