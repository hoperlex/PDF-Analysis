"""The servers, as a service: the stub `HOSTS-SEAL-1` ships and `HOSTS-BACKEND-01` replaces (ADR-0028).

``HostsService`` is what ``bootstrap/hosts_adapter.py`` delegates to. It will hold, over ``executor_host`` and its journals
(migration ``0062``): the host row and its name, the «Использовать» journal, the slots journal, the latest report, the cooldowns, the
availability of a model on a host (computed at read time from the facts, never stored), the system connections and groups the stand keeps for
each found (host, provider, access, model), the host-targeted enrollment and install, and the archive. The adapter parses nothing and
decides nothing; every rule lives here.

Every method refuses with ``503 dependency_unavailable`` (``dependency`` ``executor_hosts``) until the lane replaces its body: nothing is
read, written or sent to a model, and there is no fallback (AGENTS section 4). The signatures are the contract of the seam; a lane keeps
them and fills the bodies.
"""

from __future__ import annotations

from typing import Any, Final, NoReturn

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "HostsService"]

#: The stable class name of the refusal while the servers are not implemented.
DEPENDENCY: Final[str] = "executor_hosts"


def _not_implemented() -> NoReturn:
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)


class HostsService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def list_hosts(self) -> Any:
        _not_implemented()

    def get_host(self, *, host_id: str) -> Any:
        _not_implemented()

    def get_host_details(self, *, host_id: str) -> Any:
        _not_implemented()

    def set_enabled(self, *, host_id: str, enabled: bool, user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def set_slots(self, *, host_id: str, slots: dict[str, int], user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def archive_host(self, *, host_id: str, user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def issue_enrollment(self, *, display_name: str, user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def create_agent_install(self, *, body: Any, user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def get_agent_install(self, *, host_id: str, install_id: str) -> Any:
        _not_implemented()

    def confirm_agent_install_host_key(
        self, *, host_id: str, install_id: str, host_key_fingerprint: str, user_uid: str, idempotency_key: str
    ) -> Any:
        _not_implemented()
