"""`EMBED-01`: the pause of the vectors and the read of the night window, behind ``getVectorControl`` and ``setVectorPaused`` (contract 1.51.0).

Real PostgreSQL. The service is the one the composition root hands ``build_router``; the roles are read through the access boundary exactly as in
production for the seeded administrator, and injected for the cases that need an expert or a viewer. Each rule is shown by the caller or the write
that is refused or answered differently next to the one that is not.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.routers.precedents import SET_VECTOR_PAUSED_COMMAND_TYPE as ROUTER_COMMAND_TYPE
from auditmanager.precedents.public import SET_VECTOR_PAUSED_COMMAND_TYPE, VectorControlService
from auditmanager.shared.errors import DomainError, ErrorCode

pytestmark = pytest.mark.usefixtures("quiet_queue")


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


w = _load("embed01_vector_window_support", "vector_window_support.py")

ADMIN_ROLES = lambda _session, _user: frozenset({"admin"})  # noqa: E731
EXPERT_ROLES = lambda _session, _user: frozenset({"expert"})  # noqa: E731
VIEWER_ROLES = lambda _session, _user: frozenset({"viewer"})  # noqa: E731


@pytest.fixture(autouse=True)
def _control_back(sessions: sessionmaker[Session]) -> object:
    w.reset_control(sessions)
    yield
    w.reset_control(sessions)


def admin_uid(sessions: sessionmaker[Session]) -> str:
    with sessions() as session:
        return str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())


def key(label: str, sessions: sessionmaker[Session]) -> str:
    """A key no earlier run of this suite used (the ledger is append-only)."""
    with sessions() as session:
        return f"embed01-{label}-{session.execute(text('SELECT gen_random_uuid()')).scalar_one()}"


def test_the_command_type_is_the_one_the_router_and_the_recovery_tools_know() -> None:
    assert SET_VECTOR_PAUSED_COMMAND_TYPE == ROUTER_COMMAND_TYPE == "set_vector_paused"


def test_the_read_gives_the_pause_the_window_and_its_state_and_the_counts_to_an_administrator_only(sessions: sessionmaker[Session]) -> None:
    uid = admin_uid(sessions)
    as_admin = VectorControlService(sessions, roles_of=ADMIN_ROLES).get_vector_control(user_uid=uid)
    assert as_admin["paused"] is False and as_admin["window_state"] == "closed"
    assert as_admin["window"] == {"start": "01:00", "end": "06:00", "tz": "Asia/Yekaterinburg"}
    assert as_admin["pending_intents"] >= 0 and as_admin["poisoned_intents"] >= 0
    assert "paused_since" not in as_admin and "window_reason" not in as_admin, "an optional member with no value is absent, not null"
    as_expert = VectorControlService(sessions, roles_of=EXPERT_ROLES).get_vector_control(user_uid=uid)
    assert "pending_intents" not in as_expert and "poisoned_intents" not in as_expert
    assert {k: v for k, v in as_admin.items() if k not in ("pending_intents", "poisoned_intents")} == as_expert


def test_the_seeded_administrator_is_an_administrator_through_the_access_boundary(sessions: sessionmaker[Session]) -> None:
    """No injected roles: the default reads them as production does, so a wrong import path or role word shows here."""
    shown = VectorControlService(sessions).get_vector_control(user_uid=admin_uid(sessions))
    assert "pending_intents" in shown


def test_a_skipped_window_is_shown_with_its_reason(sessions: sessionmaker[Session]) -> None:
    from auditmanager.precedents.vectors import repository as store

    with sessions() as session:
        store.lock_control(session)
        store.set_window_state(session, state="skipped", reason="encoder_out_of_memory")
        session.commit()
    shown = VectorControlService(sessions, roles_of=EXPERT_ROLES).get_vector_control(user_uid=admin_uid(sessions))
    assert shown["window_state"] == "skipped" and shown["window_reason"] == "encoder_out_of_memory"


def test_pausing_is_journalled_with_the_actor_and_resuming_clears_the_pause(sessions: sessionmaker[Session]) -> None:
    uid, service = admin_uid(sessions), VectorControlService(sessions, roles_of=ADMIN_ROLES)
    mark = w.last_event_no(sessions)
    paused = service.set_vector_paused(paused=True, user_uid=uid, idempotency_key=key("pause", sessions))
    assert paused["paused"] is True and "paused_since" in paused
    resumed = service.set_vector_paused(paused=False, user_uid=uid, idempotency_key=key("resume", sessions))
    assert resumed["paused"] is False and "paused_since" not in resumed
    assert w.journal(sessions, since=mark) == [("paused", None), ("resumed", None)]
    with sessions() as session:
        actors = session.execute(text(
            "SELECT actor_user_uid FROM vector_control_event WHERE control_key = 'default' AND event_no > :m ORDER BY event_no"), {"m": mark}).scalars().all()
    assert actors == [uid, uid]


def test_the_same_key_and_body_answers_the_control_as_it_stands_and_writes_nothing_twice(sessions: sessionmaker[Session]) -> None:
    uid, service = admin_uid(sessions), VectorControlService(sessions, roles_of=ADMIN_ROLES)
    same = key("replay", sessions)
    first = service.set_vector_paused(paused=True, user_uid=uid, idempotency_key=same)
    mark = w.last_event_no(sessions)
    again = service.set_vector_paused(paused=True, user_uid=uid, idempotency_key=same)
    assert again["paused"] is True and again["paused_since"] == first["paused_since"]
    assert w.last_event_no(sessions) == mark


def test_setting_the_value_already_in_force_writes_no_event(sessions: sessionmaker[Session]) -> None:
    uid, service = admin_uid(sessions), VectorControlService(sessions, roles_of=ADMIN_ROLES)
    service.set_vector_paused(paused=True, user_uid=uid, idempotency_key=key("a", sessions))
    mark = w.last_event_no(sessions)
    answer = service.set_vector_paused(paused=True, user_uid=uid, idempotency_key=key("b", sessions))
    assert answer["paused"] is True and w.last_event_no(sessions) == mark, "the journal holds changes, not requests"


def test_the_same_key_with_another_body_is_refused_as_a_reuse_of_the_key(sessions: sessionmaker[Session]) -> None:
    uid, service = admin_uid(sessions), VectorControlService(sessions, roles_of=ADMIN_ROLES)
    same = key("conflict", sessions)
    service.set_vector_paused(paused=True, user_uid=uid, idempotency_key=same)
    with pytest.raises(DomainError) as caught:
        service.set_vector_paused(paused=False, user_uid=uid, idempotency_key=same)
    assert caught.value.code == ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert w.control(sessions)["paused"] is True, "and the refused write changed nothing"


@pytest.mark.parametrize("roles", [EXPERT_ROLES, VIEWER_ROLES])
def test_only_an_administrator_may_pause(sessions: sessionmaker[Session], roles: object) -> None:
    mark = w.last_event_no(sessions)
    with pytest.raises(DomainError) as caught:
        VectorControlService(sessions, roles_of=roles).set_vector_paused(  # type: ignore[arg-type]
            paused=True, user_uid=admin_uid(sessions), idempotency_key=key("denied", sessions))
    assert caught.value.code == ErrorCode.PERMISSION_DENIED
    assert w.control(sessions)["paused"] is False and w.last_event_no(sessions) == mark
