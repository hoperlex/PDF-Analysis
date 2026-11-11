"""`CTX-STAND` wired by `CRIT-CAPTURE-01` part D: the runner adapter's two additions, with no database.

Shown, each by a test that fails without the line it names: a claimed critic task carries its ``context_request`` (one entry per candidate text, the
descriptor of what the agent may ask for) and any other task carries no such member, never an empty list; and ``get_task_context`` asks the executors'
public function for the runner's own principal, the task and the kind -- with **no source handed in**, which is what keeps the answer ``unavailable /
until_move`` while the night encoder is the only one -- and answers the contract's model from the answer's wire form, committing the journal row it wrote.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.api.security import RunnerIdentity
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.executors import public as executors_public
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
TASK = "ext_01M2545JSD15ETSNNV904X991K"
IDENTITY = RunnerIdentity(token_id="ern_01M2545JSD15ETSNNV904X991K", connection_id="exc_01M2545JSD15ETSNNV904X991K")
REQUEST = ({"input_id": "xri_1", "text_sha256": "a" * 64, "section": "AI"}, {"input_id": "xri_2", "text_sha256": "b" * 64, "section": "AI"})


class _Session:
    def __init__(self) -> None:
        self.committed = 0

    def commit(self) -> None:
        self.committed += 1

    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False


def _claimed(**members: Any) -> executors_public.ClaimedTask:
    return executors_public.ClaimedTask(
        task_id=TASK, claim_expires_at=T0, deadline_at=T0, model="claude-opus-5-5", system="s", user_text="u", output_schema={"type": "object"}, **members)


def _claim(monkeypatch: pytest.MonkeyPatch, **members: Any) -> models.ClaimedExecutorTask:
    monkeypatch.setattr(executors_public, "claim_task", lambda *args, **kwargs: _claimed(**members))
    task = RunnerAdapter(_Session).claim_task(runner=IDENTITY, wait_seconds=0)  # type: ignore[arg-type]
    assert task is not None
    return task


def test_a_claimed_critic_task_carries_its_context_request_and_the_wire_form_keeps_it(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _claim(monkeypatch, context_request=REQUEST)
    assert [entry.input_id for entry in task.context_request or []] == ["xri_1", "xri_2"]
    wire = task.model_dump(mode="json", exclude_unset=True)
    assert wire["context_request"] == [dict(entry) for entry in REQUEST]


def test_any_other_task_carries_no_context_request_not_even_an_empty_one(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _claim(monkeypatch)
    assert "context_request" not in task.model_dump(mode="json", exclude_unset=True)


class _Answer:
    def __init__(self, wire: dict[str, Any]) -> None:
        self._wire = wire

    def wire(self) -> dict[str, Any]:
        return self._wire


UNTIL_MOVE = {"kind": "similar_cases", "status": "unavailable", "reason": "until_move", "items": [], "not_fitted": 0}


def test_the_context_is_asked_for_the_runners_principal_the_task_and_the_kind_with_no_source(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[Any, Any, dict[str, Any]]] = []
    sessions: list[_Session] = []

    def factory() -> _Session:
        sessions.append(_Session())
        return sessions[-1]

    def get_task_context(session: Any, principal: Any, task_id: str, **kwargs: Any) -> _Answer:
        seen.append((session, principal, {"task_id": task_id, **kwargs}))
        return _Answer(UNTIL_MOVE)

    monkeypatch.setattr(executors_public, "get_task_context", get_task_context)
    answer = RunnerAdapter(factory).get_task_context(runner=IDENTITY, task_id=TASK, kind="similar_cases")  # type: ignore[arg-type]
    assert answer.model_dump(mode="json", exclude_unset=True) == UNTIL_MOVE
    ((session, principal, kwargs),) = seen
    assert session is sessions[0] and (principal.token_id, principal.connection_id, principal.host_id) == (IDENTITY.token_id, IDENTITY.connection_id, None)
    # no ``source=``: the default of the function is the one that answers «until_move» while the night encoder is the only one (ADR-0029 decision 2)
    assert kwargs == {"task_id": TASK, "kind": "similar_cases"}
    assert sessions[0].committed == 1, "the journal row and the remembered block written by the call are committed with it"


def test_a_delivered_block_is_the_contracts_model_with_its_optional_members_absent_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    delivered = {"kind": "similar_cases", "status": "available", "items": [{"input_id": "xri_1", "cases": []}], "not_fitted": 2, "context_sha256": "c" * 64}
    monkeypatch.setattr(executors_public, "get_task_context", lambda *args, **kwargs: _Answer(delivered))
    answer = RunnerAdapter(_Session).get_task_context(runner=IDENTITY, task_id=TASK, kind="similar_cases")  # type: ignore[arg-type]
    wire = answer.model_dump(mode="json", exclude_unset=True)
    assert wire == delivered and "reason" not in wire


def test_a_refusal_of_the_executors_function_propagates_and_nothing_is_committed(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions: list[_Session] = []

    def factory() -> _Session:
        sessions.append(_Session())
        return sessions[-1]

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorTask")

    monkeypatch.setattr(executors_public, "get_task_context", refuse)
    with pytest.raises(DomainError) as caught:
        RunnerAdapter(factory).get_task_context(runner=IDENTITY, task_id=TASK, kind="patterns")  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.NOT_FOUND and sessions[0].committed == 0
