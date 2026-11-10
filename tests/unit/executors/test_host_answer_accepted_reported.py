"""`HOSTS-INT-WIRE-01` (ADR-0028 decision 6, `R-133`): the reported model of a host agent's answer is held to ``analysis.public.accepted_reported``.

No database. What is proved:

* the host answer's ``reported_model`` is judged by the one function the text stage and the extended review use (a substitute that refuses everything
  refuses the answer; one that accepts everything accepts it -- so the check *is* that function and not a copy of its list);
* the list is exact and per provider: an alias of the catalogue is accepted, a string that merely starts with one, differs in case, carries a space, names
  another model or is another provider's alias (OpenRouter's ``anthropic/...`` under ``claude_code``) is refused;
* the earlier wire stays exact: a connection token's declared model is the task's model and nothing else, an alias of the catalogue included.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.analysis import public as analysis_public
from auditmanager.executors.runner import RunnerPrincipal, submit_answer
from auditmanager.executors.runner_repository import RunnerRepository, TaskRecord

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
HOST = "exh_01M2545JSD15ETSNNV904X991M"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
TOKEN = "ern_01M2545JSD15ETSNNV904X991K"
TASK = "ext_01M2545JSD15ETSNNV904X991K"
OPUS = "claude-opus-5-5"
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}}, "required": ["observations"], "additionalProperties": False}
HOST_SIX = {"provider": "claude_code", "access": "subscription", "model_id": OPUS, "effort": "medium",
            "timeout_seconds": 600, "cell_key": "text:main"}


class Refused(Exception):
    pass


def _mismatch() -> Exception:
    return Refused("model_not_the_tasks")


class Repo(RunnerRepository):
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload, self.recorded = payload, []

    def get_task(self, session, task_id, *, lock=False):
        return TaskRecord(
            task_id=TASK, connection_id=CONNECTION, revision_id="excr_X", origin="run_call", run_id="run_X", attempt_id="att_X", model_call_id=None,
            probe_id=None, state="claimed", expected_model=OPUS, created_at=T0, deadline_at=T0, claimed_by_token_id=TOKEN, claim_expires_at=T0,
            first_claimed_at=T0, claim_count=1, declared_model=None, declared_input_tokens=None, declared_output_tokens=None, fail_reason=None,
            terminal_at=None, payload_cleared_at=None, past_deadline=False)

    def connection_host(self, session, connection_id):
        return HOST

    def payload_of(self, session, task_id):
        return self.payload

    def record_answer(self, session, *, task_id, answer_text, declared_model, input_tokens, output_tokens):
        self.recorded.append(declared_model)


HOST_PRINCIPAL = RunnerPrincipal(token_id=TOKEN, connection_id=None, host_id=HOST)
CONNECTION_PRINCIPAL = RunnerPrincipal(token_id=TOKEN, connection_id=CONNECTION)


def _host_answer(reported: str, *, repo: Repo | None = None) -> Repo:
    repo = repo or Repo({"system": "s", "user_text": "u", "output_schema": SCHEMA, "host": dict(HOST_SIX)})
    submit_answer(
        None, HOST_PRINCIPAL, TASK, output_text='{"observations": []}', model=OPUS, input_tokens=None, output_tokens=None,
        on_mismatch=_mismatch, repository=repo, provider="claude_code", access="subscription", reported_model=reported,
        usage=None)  # type: ignore[arg-type]
    return repo


def test_an_alias_of_the_catalogue_is_accepted_and_recorded_as_the_model_that_answered() -> None:
    for alias in (OPUS, "claude-opus-5-5[1m]"):
        assert _host_answer(alias).recorded == [alias]


@pytest.mark.parametrize("reported", [
    "claude-opus-5-5[1M]", "CLAUDE-OPUS-5-5", "Claude-Opus-5-5", "claude-opus-5-5 ", " claude-opus-5-5", "claude-opus-5-5-20261001",
    "claude-opus-5-5[1m]x", "claude-opus-5", "claude-sonnet-5-5", "gpt-6.1-sol",
    "anthropic/claude-opus-5-5",  # another provider's alias of the same model: the list is per provider
])
def test_a_string_outside_the_exact_list_is_refused_and_nothing_is_recorded(reported: str) -> None:
    repo = Repo({"system": "s", "user_text": "u", "output_schema": SCHEMA, "host": dict(HOST_SIX)})
    with pytest.raises(Refused):
        _host_answer(reported, repo=repo)
    assert repo.recorded == []


def test_the_check_is_the_function_of_analysis_public_not_a_copy_of_its_list(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[tuple[Any, ...]] = []

    def refuse_all(expected: Any, reported: Any, **kwargs: Any) -> bool:
        asked.append((expected, reported, kwargs))
        return False

    monkeypatch.setattr(analysis_public, "accepted_reported", refuse_all)
    with pytest.raises(Refused):
        _host_answer(OPUS)
    assert asked == [(OPUS, OPUS, {"provider": "claude_code"})], "asked for the task's model, the answer's string and the task's provider"

    monkeypatch.setattr(analysis_public, "accepted_reported", lambda expected, reported, **kwargs: True)
    assert _host_answer("a-string-no-catalogue-lists").recorded == ["a-string-no-catalogue-lists"]


def test_the_earlier_wire_stays_exact_and_asks_no_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analysis_public, "accepted_reported", lambda *a, **k: pytest.fail("the earlier wire reads no catalogue list"))

    def answer(model: str) -> Repo:
        repo = Repo({"system": "s", "user_text": "u", "output_schema": SCHEMA})
        submit_answer(None, CONNECTION_PRINCIPAL, TASK, output_text='{"observations": []}', model=model, input_tokens=1, output_tokens=2,
                      on_mismatch=_mismatch, repository=repo)  # type: ignore[arg-type]
        return repo

    assert answer(OPUS).recorded == [OPUS]
    for other in ("claude-opus-5-5[1m]", "CLAUDE-OPUS-5-5", "claude-opus-5-5 ", "claude-sonnet-5-5"):
        with pytest.raises(Refused):
            answer(other)
