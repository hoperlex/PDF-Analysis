"""`RUN-DELETE-01` (owner hotfix 2026-11-11): ``delete_audit_run`` removes a partial, failed or cancelled run from the run lists.

The command is taken as a function with stand-ins for the run repository and the command ledger: no database. What is held here is
the decision table the command makes; the tombstone row, the lists that leave the run and ``getRunStatus`` still answering it are held
on real PostgreSQL by ``tests/integration/runs/test_delete_run.py``.

* the roles: an expert and an administrator; a viewer (or no role) is ``permission_denied`` before anything is read;
* the states: ``partial``, ``failed`` and ``cancelled`` are deleted, every other state is ``state_transition_not_allowed``
  (``machine`` ``audit_run``, ``requested_state`` ``delete``), and nothing is written then;
* a run that already has a tombstone and an unknown run are ``not_found``;
* a repeat of the same keyed call replays the first answer and writes no second tombstone, even though the run has one by then.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.runs.commands import _DELETABLE_RUN_STATES, delete_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId

RUN = "run_01M2545JSD15ETSNNV904X991K"
USER = "usr_01M2545JSD15ETSNNV904X991K"
KEY = "key-delete-1"
EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})
STATES = ("created", "queued", "running", "validating", "published", "partial", "failed", "cancelled")


class _Session:
    """Answers the one ``SELECT ... FOR UPDATE`` the command opens with and records that it was asked."""

    def __init__(self) -> None:
        self.locked: list[Any] = []

    def execute(self, statement: Any, params: Any = None) -> Any:
        self.locked.append(params)

        class _Result:
            @staticmethod
            def scalar_one_or_none() -> None:
                return None

        return _Result()


@dataclass
class _Row:
    state: str


class _Runs:
    def __init__(self, state: str | None, *, deleted: bool = False) -> None:
        self.state, self.deleted = state, deleted
        self.written: list[dict[str, str]] = []

    def get(self, session: Any, run_id: str) -> _Row:
        if self.state is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        return _Row(self.state)

    def is_deleted(self, session: Any, run_id: str) -> bool:
        return self.deleted

    def record_deletion(self, session: Any, *, run_id: str, user_uid: str, command_id: str) -> None:
        self.written.append({"run_id": run_id, "user_uid": user_uid, "command_id": command_id})


class _Ledger:
    def __init__(self, *, replay: bool = False) -> None:
        self.replay = replay
        self.begun: list[dict[str, Any]] = []
        self.succeeded: list[tuple[Any, dict[str, Any]]] = []
        self.command_id = CommandId.new()

    def begin(self, session: Any, *, command_type: str, idempotency_key: Any, fingerprint: Any) -> Any:
        self.begun.append({"command_type": command_type, "key": str(idempotency_key), "fingerprint": str(fingerprint)})
        if self.replay:
            return CommandReplay(command_id=self.command_id, outcome={"run_id": RUN})
        return CommandStarted(command_id=self.command_id)

    def succeed(self, session: Any, command_id: Any, outcome: dict[str, Any]) -> None:
        self.succeeded.append((command_id, dict(outcome)))


def _delete(runs: _Runs, ledger: _Ledger, *, roles: frozenset[str] = EXPERT, run_id: str = RUN) -> str:
    return delete_audit_run(
        _Session(), run_id=run_id, roles=roles, user_uid=USER, idempotency_key=KEY,
        runs=runs, commands=ledger,  # type: ignore[arg-type]
    )


def test_the_deletable_states_are_the_three_that_end_without_a_result() -> None:
    assert _DELETABLE_RUN_STATES == {"partial", "failed", "cancelled"}


@pytest.mark.parametrize("state", ["partial", "failed", "cancelled"])
@pytest.mark.parametrize("roles", [EXPERT, ADMIN, frozenset({"expert", "viewer"})])
def test_a_deletable_run_gets_one_tombstone_and_one_succeeded_receipt(state: str, roles: frozenset[str]) -> None:
    runs, ledger = _Runs(state), _Ledger()
    assert _delete(runs, ledger, roles=roles) == RUN
    assert runs.written == [{"run_id": RUN, "user_uid": USER, "command_id": str(ledger.command_id)}]
    assert [(entry["command_type"], entry["key"]) for entry in ledger.begun] == [("delete_audit_run", KEY)]
    assert ledger.succeeded == [(ledger.command_id, {"run_id": RUN})]


@pytest.mark.parametrize("state", [state for state in STATES if state not in {"partial", "failed", "cancelled"}])
def test_any_other_state_is_refused_with_the_machine_and_both_states_and_writes_nothing(state: str) -> None:
    runs, ledger = _Runs(state), _Ledger()
    with pytest.raises(DomainError) as refused:
        _delete(runs, ledger)
    error = refused.value
    assert error.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert dict(error.detail_fields) == {"machine": "audit_run", "current_state": state, "requested_state": "delete"}
    # The catalogue's screen of the details accepts these keys: the envelope builds, and says what the refusal says.
    envelope = error.envelope("corr_01M2545JSD15ETSNNV904X991K")
    assert envelope.error_code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert dict(envelope.details or {}) == {"machine": "audit_run", "current_state": state, "requested_state": "delete"}
    assert runs.written == [] and ledger.succeeded == []


@pytest.mark.parametrize("roles", [frozenset(), frozenset({"viewer"}), frozenset({"reviewer"})])
def test_a_caller_without_the_expert_or_admin_role_is_denied_before_anything_is_read(roles: frozenset[str]) -> None:
    runs, ledger = _Runs("partial"), _Ledger()
    with pytest.raises(DomainError) as refused:
        _delete(runs, ledger, roles=roles)
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert runs.written == [] and ledger.begun == []


def test_an_unknown_run_is_not_found_and_claims_no_key() -> None:
    runs, ledger = _Runs(None), _Ledger()
    with pytest.raises(DomainError) as refused:
        _delete(runs, ledger)
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert runs.written == [] and ledger.begun == []


@pytest.mark.parametrize("state", ["partial", "failed", "cancelled", "published", "running"])
def test_a_run_that_already_has_a_tombstone_is_not_found_whatever_its_state(state: str) -> None:
    runs, ledger = _Runs(state, deleted=True), _Ledger()
    with pytest.raises(DomainError) as refused:
        _delete(runs, ledger)
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert runs.written == [] and ledger.succeeded == []


def test_a_repeat_of_the_same_keyed_call_replays_and_writes_no_second_tombstone() -> None:
    # By the replay the run has its tombstone; the first answer still comes back, not `not_found`.
    runs, ledger = _Runs("partial", deleted=True), _Ledger(replay=True)
    assert _delete(runs, ledger) == RUN
    assert runs.written == [] and ledger.succeeded == []
    assert [entry["command_type"] for entry in ledger.begun] == ["delete_audit_run"]


def test_the_fingerprint_is_the_run_so_one_key_cannot_delete_two_runs() -> None:
    first, second = _Ledger(), _Ledger()
    _delete(_Runs("failed"), first)
    _delete(_Runs("failed"), second, run_id="run_01M2545JSD15ETSNNV904X991M")
    assert first.begun[0]["fingerprint"] != second.begun[0]["fingerprint"]


def test_the_run_row_is_locked_before_the_key_is_claimed() -> None:
    order: list[str] = []

    class _Recording(_Session):
        def execute(self, statement: Any, params: Any = None) -> Any:
            order.append("lock")
            return super().execute(statement, params)

    class _Ledger2(_Ledger):
        def begin(self, session: Any, **kwargs: Any) -> Any:
            order.append("begin")
            return super().begin(session, **kwargs)

    delete_audit_run(
        _Recording(), run_id=RUN, roles=EXPERT, user_uid=USER, idempotency_key=KEY,
        runs=_Runs("failed"), commands=_Ledger2(),  # type: ignore[arg-type]
    )
    assert order == ["lock", "begin"]
