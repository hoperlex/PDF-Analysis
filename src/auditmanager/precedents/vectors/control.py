"""The pause of the vectors and the state of the night window, behind the two routes of the surface (`ADR-0029` decision 8, contract 1.51.0).

``getVectorControl`` and ``setVectorPaused`` are the two bodies `EMBED-01` replaced; the route reads and writes nothing itself and asks the
service below through the port of ``api/routers/precedents_ports.py``. The service answers in the contract's own shape (a mapping the route
validates against ``VectorControl``), opens its own session, and decides what the router may not:

* **who sees the counts**: the queued and the poisoned intents are for an administrator; an expert reads the pause, the window and its state;
* **who may pause**: an administrator, checked here again although the authorization seam has refused any other role (the register is the first
  line, not the only one);
* **a keyed write**: ``Idempotency-Key`` is required and the command is recorded as ``set_vector_paused``. The same key with the same body answers
  the control as it stands; the same key with another body is the ledger's ``409``. Setting the value already in force writes no event: the
  journal holds changes, not requests (`vector_control_event`, plan-v5 section 5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.precedents.vectors import repository as store
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = ["SET_VECTOR_PAUSED_COMMAND_TYPE", "VectorControlService"]

#: The command type of the keyed write, as ``command_record.command_type`` holds it (classified KEEP in ``scripts/recovery/product_purge.py``).
#: The router module exports the same word; a test holds the two equal.
SET_VECTOR_PAUSED_COMMAND_TYPE: Final[str] = "set_vector_paused"
_ADMIN: Final[str] = "admin"


def _roles_of(session: Session, user_uid: str) -> frozenset[str]:
    from auditmanager.access.public import AccountRepository

    return frozenset(str(role) for role in AccountRepository().roles_of(session, user_uid))


class VectorControlService:
    """The control row as the surface shows it. Wired by the composition root as ``build_router(vector_control=VectorControlService(sessions))``."""

    def __init__(
        self, session_factory: sessionmaker[Session], *, roles_of: Callable[[Session, str], frozenset[str]] = _roles_of,
    ) -> None:
        self._sessions = session_factory
        self._roles_of = roles_of

    # -- the read -----------------------------------------------------------------------------------------------

    @staticmethod
    def _view(session: Session, *, admin: bool) -> dict[str, Any]:
        control = store.read_control(session)
        setting = store.read_window_setting(session)
        view: dict[str, Any] = {
            "paused": control.paused,
            "window_state": control.window_state,
            "window_changed_at": control.window_changed_at,
            "window": setting.as_value(),
        }
        if control.paused_since is not None:
            view["paused_since"] = control.paused_since
        if control.window_reason is not None:
            view["window_reason"] = control.window_reason
        if admin:
            pending, poisoned = store.count_intents(session)
            view["pending_intents"] = pending
            view["poisoned_intents"] = poisoned
        return view

    def get_vector_control(self, *, user_uid: str) -> dict[str, Any]:
        with self._sessions() as session:
            return self._view(session, admin=_ADMIN in self._roles_of(session, user_uid))

    # -- the write ----------------------------------------------------------------------------------------------

    def set_vector_paused(self, *, paused: bool, user_uid: str, idempotency_key: str) -> dict[str, Any]:
        with self._sessions() as session:
            if _ADMIN not in self._roles_of(session, user_uid):
                raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")
            ledger = CommandRepository()
            claimed = ledger.begin(
                session, command_type=SET_VECTOR_PAUSED_COMMAND_TYPE, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=payload_fingerprint({"paused": paused, "actor_uid": user_uid}))
            control = store.lock_control(session)
            if not isinstance(claimed, CommandReplay):
                if control.paused != paused:
                    store.set_paused(session, paused=paused, actor=user_uid)
                ledger.succeed(session, claimed.command_id, {"paused": paused})
            view = self._view(session, admin=True)
            session.commit()
            return view
