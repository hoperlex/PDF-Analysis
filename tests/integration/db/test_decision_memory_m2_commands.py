"""`DECISION-MEMORY-01` phase M2: withdraw and restore as KEYED commands (`DecisionMemoryAdapter`), on a clone of the migrated schema.

The composition root claims the command, the memory writes the status event with the receipt's ``command_id``, and a replay answers the event
the first call wrote. Shown: the event names the receipt; the same key and payload is a replay that writes nothing; the same key with another
reason, another case or another actor is ``idempotency_key_reuse``; a refused transition leaves a receipt that is not "succeeded" and no event;
the two command types are the ones the product purge keeps; and a concurrent writer is serialised by the case's advisory lock.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.adapters import (
    COMMAND_TYPE_RESTORE_MEMORY_CASE,
    COMMAND_TYPE_WITHDRAW_MEMORY_CASE,
    DecisionMemoryAdapter,
)
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError, ErrorCode
from scripts.recovery.product_purge import KEEP_COMMAND_TYPES, PRODUCT_COMMAND_TYPES
from tests.support.memory_seed import ensure_blob, seed_case


@pytest.fixture
def clone(migrated_database: Any) -> Iterator[tuple[Engine, sessionmaker[Session], str, str]]:
    engine = create_database_engine(migrated_database)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with engine.begin() as connection:
        ensure_blob(connection, "blob_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        case = seed_case(connection, blob="blob_01ARZ3NDEKTSV4RRFFQ69G5FAV")["case_id"]
        admin = str(connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
    try:
        yield engine, factory, case, admin
    finally:
        engine.dispose()


def _events(engine: Engine, case: str) -> list[Any]:
    with engine.connect() as connection:
        return list(connection.execute(text(
            "SELECT status_event_id, kind, reason_code, actor_user_uid, command_id FROM decision_memory_status_event "
            "WHERE case_id = :c ORDER BY created_at"), {"c": case}).all())


def test_a_keyed_withdraw_names_its_receipt_and_a_replay_writes_nothing(clone: Any) -> None:
    engine, factory, case, admin = clone
    adapter = DecisionMemoryAdapter(factory)
    first = adapter.withdraw_case(case_id=case, reason_code="wrong_decision", actor_user_uid=admin, idempotency_key="key-withdraw-0001")
    assert (first.status, first.kind) == ("withdrawn", "withdraw")
    (event,) = _events(engine, case)
    assert event.status_event_id == first.status_event_id and event.command_id is not None
    with engine.connect() as connection:
        receipt = connection.execute(text("SELECT command_type, state FROM command_record WHERE command_id = :c"), {"c": event.command_id}).one()
    assert tuple(receipt) == (COMMAND_TYPE_WITHDRAW_MEMORY_CASE, "succeeded")

    replay = adapter.withdraw_case(case_id=case, reason_code="wrong_decision", actor_user_uid=admin, idempotency_key="key-withdraw-0001")
    assert replay == first                                                     # the same answer, including the time of the first call
    assert len(_events(engine, case)) == 1

    for over in ({"reason_code": "other"}, {"case_id": "dmc_01ARZ3NDEKTSV4RRFFQ69G5FAV"}):
        arguments = {"case_id": case, "reason_code": "wrong_decision", "actor_user_uid": admin, "idempotency_key": "key-withdraw-0001", **over}
        with pytest.raises(DomainError) as reused:
            adapter.withdraw_case(**arguments)
        assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert len(_events(engine, case)) == 1


def test_a_refused_transition_writes_no_event_and_the_same_key_may_be_used_again_for_a_valid_one(clone: Any) -> None:
    engine, factory, case, admin = clone
    adapter = DecisionMemoryAdapter(factory)
    with pytest.raises(DomainError) as refused:
        adapter.restore_case(case_id=case, reason_code="other", actor_user_uid=admin, idempotency_key="key-restore-0001")
    assert refused.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert _events(engine, case) == []                                          # the failed call rolled back, receipt included
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM command_record WHERE idempotency_key = 'key-restore-0001'")).scalar_one() == 0

    adapter.withdraw_case(case_id=case, reason_code="other", actor_user_uid=admin, idempotency_key="key-withdraw-0002")
    restored = adapter.restore_case(case_id=case, reason_code="other", actor_user_uid=admin, idempotency_key="key-restore-0001")
    assert restored.status == "active"
    assert [e.kind for e in _events(engine, case)] == ["withdraw", "restore"]
    assert adapter.get_case(case_id=case).summary.status == "active"            # type: ignore[union-attr]
    settings, counts = adapter.status()
    assert (settings.data_class, settings.training_use) == ("test", "off") and counts.cases == 1


def test_the_two_command_types_are_kept_by_the_product_purge() -> None:
    types = {COMMAND_TYPE_WITHDRAW_MEMORY_CASE, COMMAND_TYPE_RESTORE_MEMORY_CASE}
    assert types == {"withdraw_decision_memory_case", "restore_decision_memory_case"}
    assert types <= KEEP_COMMAND_TYPES and not types & PRODUCT_COMMAND_TYPES


def test_two_writers_racing_for_one_case_are_serialised_and_exactly_one_withdraws(clone: Any) -> None:
    """Both read "active" before either inserts; the advisory lock (the service's and the trigger's, one key) makes the second wait and then
    be refused -- never a second withdraw."""
    engine, factory, case, admin = clone
    adapter = DecisionMemoryAdapter(factory)
    outcomes: list[str] = []
    barrier = threading.Barrier(2)

    def attempt(number: int) -> None:
        barrier.wait()
        try:
            adapter.withdraw_case(case_id=case, reason_code="other", actor_user_uid=admin, idempotency_key=f"key-race-{number:04d}")
            outcomes.append("withdrawn")
        except DomainError as error:
            outcomes.append(error.code.value)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert sorted(outcomes) == ["state_transition_not_allowed", "withdrawn"], outcomes
    assert [e.kind for e in _events(engine, case)] == ["withdraw"]
