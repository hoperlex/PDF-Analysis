"""A batch item that cannot start says why: the refusal is recorded in the transaction that fails the item."""

from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.stage_run import batch as batch_module
from auditmanager.comparison.stage_run.batch import StageBatchHandler, refusal_detail
from auditmanager.comparison.stage_run.service import BATCH_WORK_KIND
from auditmanager.comparison.stage_v3 import mode as v3_mode
from auditmanager.comparison.stage_v3 import policy as v3_policy
from auditmanager.comparison.work.model import Yielded
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import StageChainBatchId, StageChainBatchItemId, StageLinkRevisionId, StagePairId

BATCH, ITEM = str(StageChainBatchId.new()), str(StageChainBatchItemId.new())
PAIR, REVISION = str(StagePairId.new()), str(StageLinkRevisionId.new())
PROJECT, ACTOR = "prj_00000000000000000000000001", "usr_00000000000000000000000001"


class _Result:
    def __init__(self, row: Any = None) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row

    def scalar_one(self) -> Any:
        return self._row


class _Session:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = " ".join(str(statement).split())
        self.statements.append((sql, dict(params or {})))
        if "FOR NO KEY UPDATE" in sql:
            return _Result("running")
        if sql.startswith("SELECT state, project_uid, actor_user_uid, with_ai FROM stage_chain_batch"):
            return _Result(("queued", PROJECT, ACTOR, False))
        if "FROM stage_chain_batch_item" in sql and "state IN ('queued','running')" in sql:
            return _Result((ITEM, PAIR, REVISION, "queued", None, {}))
        return _Result()


def _run_refused(monkeypatch: pytest.MonkeyPatch, error: DomainError) -> tuple[Any, _Session]:
    session = _Session()

    @contextmanager
    def scope(factory: Any) -> Any:
        yield session

    def refuse(**_kw: Any) -> Any:
        raise error

    monkeypatch.setattr(batch_module, "session_scope", scope)
    monkeypatch.setattr(batch_module, "AccountRepository", lambda: SimpleNamespace(roles_of=lambda *_a: frozenset({"expert"})))
    monkeypatch.setattr(v3_mode, "engine_for_batch", lambda *_a: "classic")
    monkeypatch.setattr(v3_policy, "policy_for_batch", lambda *_a: None)
    handler = StageBatchHandler(SimpleNamespace(session_factory=object()))  # type: ignore[arg-type]
    handler.chains = SimpleNamespace(start=refuse)  # type: ignore[assignment]
    item = SimpleNamespace(kind=BATCH_WORK_KIND, module="stages", payload={"batch_id": BATCH},
                           project_uid=PROJECT, require_current=lambda _session: None)
    return handler.run(item), session  # type: ignore[arg-type]


def test_a_refused_start_fails_the_item_and_records_the_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    refusal = DomainError(ErrorCode.CONFLICT, conflict_reason="stage_link_revision_stale")
    outcome, session = _run_refused(monkeypatch, refusal)
    assert isinstance(outcome, Yielded)
    failed = [i for i, (sql, _p) in enumerate(session.statements)
              if sql.startswith("UPDATE stage_chain_batch_item SET state = 'failed'")]
    events = [i for i, (sql, _p) in enumerate(session.statements)
              if "'stage.batch_item_failed'" in sql and sql.startswith("INSERT INTO audit_event")]
    assert len(failed) == 1 and len(events) == 1 and failed[0] < events[0]
    params = session.statements[events[0]][1]
    assert params["batch"] == BATCH
    assert json.loads(params["payload"]) == {
        "actor_uid": ACTOR, "item_id": ITEM, "pair_id": PAIR, "link_revision_id": REVISION,
        "error_code": "conflict", "conflict_reason": "stage_link_revision_stale",
    }


def test_the_recorded_reason_keeps_codes_and_drops_everything_else() -> None:
    error = DomainError(ErrorCode.VALIDATION_FAILED, field="selections", constraint="unique_pairs",
                        path="/srv/private/file.pdf", message_text="x" * 200, conflict_reason="y" * 129)
    assert refusal_detail(error) == {"error_code": "validation_failed", "field": "selections",
                                     "constraint": "unique_pairs"}
    assert refusal_detail(DomainError(ErrorCode.CONFLICT)) == {"error_code": "conflict"}
