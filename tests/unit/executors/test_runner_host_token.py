"""`HOSTS-BACKEND-01` (ADR-0028 decisions 7 and 9, RUNNER_API 10.4 to 10.6): the host token in the pull channel.

No database: the runner repository is a stand-in. What is proved: a token or a claim names exactly one of a connection and a host; a host principal owns the
tasks of the connections of its host and no other; a host task carries all six members or none; a host answer is held to its task (provider, access) and its
``reported_model`` to the catalogue's exact accepted strings (`R-133`: no prefix, no case folding), and what is recorded as the call's model is the reported
string; a connection token that sends a host member is refused; a failure about the host's access starts the cooldown of the task's pair and any other failure
starts none; a retry served by another host finds the saved reply, because the answer of a task is keyed by the task and its model, never by a host.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.executors import runner as runner_module
from auditmanager.executors.runner import RunnerPrincipal, _claimed, fail_task, submit_answer
from auditmanager.executors.runner_repository import ClaimedRow, RunnerRepository, StoredToken, TaskRecord
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
HOST = "exh_01M2545JSD15ETSNNV904X991M"
OTHER_HOST = "exh_01M2545JSD15ETSNNV904X991N"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
TOKEN = "ern_01M2545JSD15ETSNNV904X991K"
TASK = "ext_01M2545JSD15ETSNNV904X991K"
OPUS = "claude-opus-5-5"
HOST_SIX = {"provider": "claude_code", "access": "subscription", "model_id": OPUS, "effort": "medium",
            "timeout_seconds": 600, "cell_key": "text:main"}
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}}, "required": ["observations"],
          "additionalProperties": False}


def _task(state: str = "claimed", *, connection: str = CONNECTION, token: str | None = TOKEN, model: str = OPUS) -> TaskRecord:
    return TaskRecord(
        task_id=TASK, connection_id=connection, revision_id="excr_X", origin="run_call", run_id="run_X", attempt_id="att_X",
        model_call_id=None, probe_id=None, state=state, expected_model=model, created_at=T0, deadline_at=T0, claimed_by_token_id=token,
        claim_expires_at=T0, first_claimed_at=T0, claim_count=1, declared_model=None, declared_input_tokens=None,
        declared_output_tokens=None, fail_reason=None, terminal_at=None, payload_cleared_at=None, past_deadline=False)


class FakeRunnerRepo(RunnerRepository):
    def __init__(self, task: TaskRecord | None, *, payload: dict[str, Any] | None = None, host_of: dict[str, str | None] | None = None,
                 answered: tuple[str | None, str | None] = (None, None)) -> None:
        self.task, self.payload = task, payload
        self.host_of = host_of if host_of is not None else {CONNECTION: HOST}
        self.answered = answered
        self.recorded: list[dict[str, Any]] = []
        self.failed: list[str] = []

    def get_task(self, session, task_id, *, lock=False):
        return self.task if self.task is not None and task_id == self.task.task_id else None

    def connection_host(self, session, connection_id):
        return self.host_of.get(connection_id)

    def payload_of(self, session, task_id):
        return self.payload

    def answer_of(self, session, task_id):
        return self.answered

    def record_answer(self, session, *, task_id, answer_text, declared_model, input_tokens, output_tokens):
        self.recorded.append({"model": declared_model, "input": input_tokens, "output": output_tokens, "text": answer_text})

    def record_failure(self, session, *, task_id, reason):
        self.failed.append(reason)


def _payload(**host: Any) -> dict[str, Any]:
    return {"system": "s", "user_text": "u", "output_schema": SCHEMA, "host": {**HOST_SIX, **host}}


class Refused(Exception):
    pass


def _mismatch() -> Exception:
    return Refused("model_not_the_tasks")


HOST_PRINCIPAL = RunnerPrincipal(token_id=TOKEN, connection_id=None, host_id=HOST)
CONNECTION_PRINCIPAL = RunnerPrincipal(token_id=TOKEN, connection_id=CONNECTION)


def _submit(repo: FakeRunnerRepo, principal: RunnerPrincipal = HOST_PRINCIPAL, **kwargs: Any) -> Any:
    body = {"output_text": '{"observations": []}', "model": OPUS, "input_tokens": None, "output_tokens": None,
            "provider": "claude_code", "access": "subscription", "reported_model": OPUS,
            "usage": {"input_tokens": 1200, "output_tokens": 300}}
    body.update(kwargs)
    return submit_answer(None, principal, TASK, on_mismatch=_mismatch, repository=repo, **body)  # type: ignore[arg-type]


# --- who owns a task ---------------------------------------------------------------------------------------------------


def test_a_host_principal_owns_the_tasks_of_the_connections_of_its_host() -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    assert _submit(repo).state == "answered"


def test_a_host_principal_never_touches_a_task_of_another_hosts_connection_or_of_a_legacy_one() -> None:
    for owner in (OTHER_HOST, None):
        repo = FakeRunnerRepo(_task(), payload=_payload(), host_of={CONNECTION: owner})
        with pytest.raises(DomainError) as refused:
            _submit(repo)
        assert refused.value.code is ErrorCode.NOT_FOUND and repo.recorded == [], "the answer never says which"


def test_a_connection_principal_keeps_the_task_of_its_own_connection_and_no_other() -> None:
    repo = FakeRunnerRepo(_task(), payload={"system": "s", "user_text": "u", "output_schema": SCHEMA})
    assert _submit(repo, CONNECTION_PRINCIPAL, provider=None, access=None, reported_model=None, usage=None,
                   input_tokens=3, output_tokens=4).state == "answered"
    assert repo.recorded[0]["model"] == OPUS and (repo.recorded[0]["input"], repo.recorded[0]["output"]) == (3, 4)
    stranger = RunnerPrincipal(token_id=TOKEN, connection_id="exc_01M2545JSD15ETSNNV904X991M")
    with pytest.raises(DomainError):
        _submit(FakeRunnerRepo(_task(), payload=_payload()), stranger, provider=None, access=None, reported_model=None, usage=None)


# --- the six members -------------------------------------------------------------------------------------------------


def _row(payload: dict[str, Any]) -> ClaimedRow:
    return ClaimedRow(TASK, T0, T0, OPUS, payload)


def test_a_host_task_is_handed_over_with_all_six_members_and_no_answer_cap() -> None:
    task = _claimed(_row(_payload()))
    assert (task.provider, task.access, task.model_id, task.effort, task.timeout_seconds, task.cell_key) == (
        "claude_code", "subscription", OPUS, "medium", 600, "text:main")
    assert not hasattr(task, "max_output_tokens"), "`R-153n`: no answer cap reaches the agent"


def test_a_task_written_before_the_cap_left_is_served_without_it() -> None:
    """A queued task of the previous release still holds ``max_output_tokens`` in its payload; it is not among the members, so it is dropped."""
    task = _claimed(_row(_payload(max_output_tokens=16000)))
    assert (task.provider, task.timeout_seconds, task.cell_key) == ("claude_code", 600, "text:main")
    assert not hasattr(task, "max_output_tokens")
    assert task.model == task.model_id == OPUS, "the earlier tooling reads ``model``: it equals ``model_id``"


@pytest.mark.parametrize("missing", list(HOST_SIX))
def test_a_host_task_that_lacks_a_member_is_not_served_at_all(missing: str) -> None:
    payload = _payload()
    del payload["host"][missing]
    with pytest.raises(DomainError) as refused:
        _claimed(_row(payload))
    assert refused.value.code is ErrorCode.INTERNAL_ERROR, "all six or none (the contract): a partial task is the writer's defect"


def test_a_task_of_a_connection_token_carries_none_of_them() -> None:
    task = _claimed(_row({"system": "s", "user_text": "u", "output_schema": SCHEMA}))
    assert (task.provider, task.access, task.model_id, task.effort, task.cell_key) == (None, None, None, None, None)


# --- the answer ---------------------------------------------------------------------------------------------------------


def test_the_recorded_model_is_the_reported_string_and_the_usage_is_the_tokens() -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    _submit(repo, reported_model="claude-opus-5-5[1m]")
    # the catalogue accepts this exact string for the model; what is recorded is what answered
    assert repo.recorded[0]["model"] == "claude-opus-5-5[1m]"
    assert (repo.recorded[0]["input"], repo.recorded[0]["output"]) == (1200, 300)


@pytest.mark.parametrize("reported", ["claude-opus-5-5-20261001", "Claude-Opus-5-5", "claude-opus-5-5 ", "claude-opus-5", "claude-opus-5-5[1m]x", ""])
def test_a_reported_model_outside_the_exact_accepted_list_is_refused_and_nothing_is_recorded(reported: str) -> None:
    """`R-133`: no prefix match, no date suffix, no case folding. (The catalogue lists the model and its ``[1m]`` form, nothing else.)"""
    repo = FakeRunnerRepo(_task(), payload=_payload())
    with pytest.raises((Refused, DomainError)):
        _submit(repo, reported_model=reported)
    assert repo.recorded == []


def test_a_host_answer_must_name_what_answered() -> None:
    for missing in ("provider", "access", "reported_model"):
        repo = FakeRunnerRepo(_task(), payload=_payload())
        with pytest.raises(DomainError) as refused:
            _submit(repo, **{missing: None})
        assert refused.value.detail_fields["constraint"] == "required" and repo.recorded == []


@pytest.mark.parametrize(("member", "value"), [("provider", "codex"), ("access", "api")])
def test_a_host_answer_for_another_provider_or_access_than_the_task_is_refused(member: str, value: str) -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    with pytest.raises(DomainError) as refused:
        _submit(repo, **{member: value})
    assert refused.value.detail_fields == {"field": member, "constraint": "not_the_task"} and repo.recorded == []


def test_the_task_model_is_still_held_equal_to_the_declared_model() -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    with pytest.raises(Refused):
        _submit(repo, model="claude-sonnet-5-5")


def test_a_connection_token_that_sends_a_host_member_is_refused() -> None:
    for member in ({"provider": "claude_code"}, {"reported_model": OPUS}, {"usage": {"input_tokens": 1, "output_tokens": 1}}):
        repo = FakeRunnerRepo(_task(), payload={"system": "s", "user_text": "u", "output_schema": SCHEMA})
        kwargs = {"provider": None, "access": None, "reported_model": None, "usage": None, **member}
        with pytest.raises(DomainError) as refused:
            _submit(repo, CONNECTION_PRINCIPAL, input_tokens=1, output_tokens=1, **kwargs)
        assert refused.value.detail_fields["constraint"] == "host_token_only" and repo.recorded == []


def test_without_usage_no_tokens_are_invented() -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    _submit(repo, usage=None)
    assert (repo.recorded[0]["input"], repo.recorded[0]["output"]) == (None, None)


def test_the_answer_must_still_conform_to_the_output_schema() -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    with pytest.raises(DomainError) as refused:
        _submit(repo, output_text='{"nope": 1}')
    assert refused.value.detail_fields["constraint"] == "output_schema" and repo.recorded == []


def test_a_retry_served_by_another_host_finds_the_saved_reply() -> None:
    """The reply of a task is keyed by the task and the model that answered; the host is not in the key. The same answer again, from the same token,
    after the task was answered, is accepted without a second write (the idempotency of ``submitExecutorTaskAnswer``); a different one is a conflict."""
    repo = FakeRunnerRepo(_task("answered"), payload=_payload(), answered=('{"observations": []}', OPUS))
    assert _submit(repo).state == "answered" and repo.recorded == []
    with pytest.raises(DomainError) as refused:
        _submit(repo, output_text='{"observations": [1]}')
    assert refused.value.detail_fields["conflict_reason"] == "answer_differs"


# --- failure and the cooldown -------------------------------------------------------------------------------------------


@pytest.fixture
def cooldowns(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    from auditmanager.executors import host_commands

    monkeypatch.setattr(host_commands, "record_task_failure", lambda session, **kwargs: seen.append(kwargs))
    return seen


def test_a_failure_about_access_reaches_the_cooldown_with_the_tasks_provider_and_model(cooldowns: list[dict[str, Any]]) -> None:
    repo = FakeRunnerRepo(_task(), payload=_payload())
    assert fail_task(None, HOST_PRINCIPAL, TASK, reason="quota_exceeded: monthly cap", repository=repo).state == "failed"  # type: ignore[arg-type]
    assert repo.failed == ["quota_exceeded: monthly cap"]
    assert cooldowns == [{"host_id": HOST, "provider": "claude_code", "model_id": OPUS, "reason": "quota_exceeded: monthly cap"}]


def test_a_connection_token_failure_starts_no_cooldown(cooldowns: list[dict[str, Any]]) -> None:
    repo = FakeRunnerRepo(_task(), payload={"system": "s", "user_text": "u", "output_schema": SCHEMA})
    fail_task(None, CONNECTION_PRINCIPAL, TASK, reason="quota_exceeded", repository=repo)  # type: ignore[arg-type]
    assert cooldowns == []


def test_a_task_with_no_payload_left_fails_without_a_cooldown(cooldowns: list[dict[str, Any]]) -> None:
    repo = FakeRunnerRepo(_task(), payload=None)
    fail_task(None, HOST_PRINCIPAL, TASK, reason="auth_failed", repository=repo)  # type: ignore[arg-type]
    assert repo.failed == ["auth_failed"] and cooldowns == []


# --- a token or a claim names exactly one target ------------------------------------------------------------------------------


def test_a_token_and_a_claim_name_exactly_one_of_a_connection_and_a_host() -> None:
    repo = RunnerRepository()
    for connection, host in ((None, None), (CONNECTION, HOST)):
        with pytest.raises(ValueError):
            repo.insert_token(None, connection_id=connection, host_id=host, token_prefix="amr_aaaaaaaa", token_hash=b"x", expires_in_days=1, actor_uid="u")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            repo.claim_next(None, connection_id=connection, host_id=host, token_id=TOKEN, lease_seconds=1)  # type: ignore[arg-type]
    from auditmanager.executors.enrollment_repository import EnrollmentRepository

    for connection, host in ((None, None), (CONNECTION, HOST)):
        with pytest.raises(ValueError):
            EnrollmentRepository().insert_enrollment(None, connection_id=connection, host_id=host, secret_prefix="ame_aaaaaaaa",  # type: ignore[arg-type]
                                                     secret_hash=b"x", lifetime_seconds=1, actor_uid="u")


def test_the_claim_of_a_host_reads_only_tasks_that_carry_the_host_members() -> None:
    class Session:
        def __init__(self) -> None:
            self.sql = ""

        def execute(self, statement, params):
            self.sql = str(statement)
            return SimpleNamespace(first=lambda: None)

    session = Session()
    RunnerRepository().claim_next(session, host_id=HOST, token_id=TOKEN, lease_seconds=120)  # type: ignore[arg-type]
    assert "p.payload -> 'host' IS NOT NULL" in session.sql
    assert "k.host_id = :c AND k.system_managed" in session.sql
    session = Session()
    RunnerRepository().claim_next(session, connection_id=CONNECTION, token_id=TOKEN, lease_seconds=120)  # type: ignore[arg-type]
    assert "payload -> 'host'" not in session.sql and "p.connection_id = :c" in session.sql


def test_the_stored_token_names_its_host() -> None:
    stored = StoredToken(TOKEN, None, b"h", True, HOST)
    assert (stored.connection_id, stored.host_id) == (None, HOST)
    assert runner_module.RunnerPrincipal(TOKEN, None, HOST).connection_id is None
