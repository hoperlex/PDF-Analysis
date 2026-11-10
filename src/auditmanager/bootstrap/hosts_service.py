"""The servers, as a service (`HOSTS-BACKEND-01`, ADR-0028): what ``bootstrap/hosts_adapter.py`` delegates to.

Thin, like every adapter here: the rules live in ``auditmanager.executors`` (``host_commands``, ``hosts``, ``cell_binding``). This opens the
session, re-reads the actor's role set inside it (the router has already refused a role beyond the register; the command checks again), calls the
executors' public functions and maps what they return into the contract's shapes -- the adapter above validates each against the contract's model and
fails loudly on a shape that is not one.

* the reads (``list_hosts``, ``get_host``, ``get_host_details``) answer from facts read at one database instant: the report snapshot, the pulse, the
  «Использовать» journal, the slots and the cooldowns. Availability is **computed here, on read**, and the reasons for a model being unavailable
  appear **only** in the administrator's details, never in a list (ADR-0028 decision 16);
* the writes commit on a clean return. ``get_agent_install`` is a write on a read (an overdue session ends as ``failed``), so it commits too.

No method returns a secret but ``issue_enrollment`` (the grant's, once); no view carries a hash, a key, a path or a sealed byte.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "HostsService"]

#: The stable class name of the refusal when the servers cannot be served at all (kept from the stub for the integrator's wiring tests).
DEPENDENCY: Final[str] = "executor_hosts"


def _present(**fields: Any) -> dict[str, Any]:
    """Optional properties are absent when they have no value, never null."""
    return {name: value for name, value in fields.items() if value is not None}


class HostsService:
    def __init__(
        self, *, session_factory: sessionmaker[Session], ring: Any = None, public_origin: str | None = None,
    ) -> None:
        self._sessions = session_factory
        self._ring = ring
        self._public_origin = public_origin

    # -- plumbing ------------------------------------------------------------------------------------------

    def _write(self, work: Any) -> Any:
        from auditmanager.access.public import correlation_scope
        from auditmanager.api.routers.correlation import current_correlation_id

        with self._sessions() as session, correlation_scope(current_correlation_id()):
            result = work(session)
            session.commit()
            return result

    def _read(self, work: Any) -> Any:
        with self._sessions() as session:
            return work(session)

    @staticmethod
    def _roles(session: Session, user_uid: str) -> Any:
        from auditmanager.access.public import AccountRepository

        return AccountRepository().roles_of(session, user_uid)

    # -- views ---------------------------------------------------------------------------------------------

    @staticmethod
    def _host_view(facts: Any, models: Any) -> dict[str, Any]:
        """``ExecutorHost``: a model is listed only while it can be used (``available`` or ``busy``); the reasons are not here."""
        last_seen = (None if facts.pulse_age_seconds is None
                     else facts.now - timedelta(seconds=facts.pulse_age_seconds))
        return _present(
            host_id=facts.record.host_id, display_name=facts.record.display_name, enabled=facts.enabled, state=facts.state,
            last_seen_at=last_seen, agent_version=None if facts.report is None else facts.report.report.agent_version,
            models=[{"provider": item.provider, "model_id": item.model_id, "access": item.access, "state": item.state}
                    for item in models if item.state in ("available", "busy")],
            slots_total=facts.slots_total, slots_in_use=facts.slots_in_use, created_at=facts.record.created_at,
            created_by=facts.record.created_by, archived_at=facts.record.archived_at)

    def _one_host(self, session: Session, host_id: str) -> dict[str, Any]:
        from auditmanager.executors.public import model_availability, read_hosts

        found = read_hosts(session, [host_id], include_archived=True)
        if not found:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorHost")
        return self._host_view(found[0], model_availability(found[0]))

    # -- reads -----------------------------------------------------------------------------------------------

    def list_hosts(self) -> Any:
        from auditmanager.executors.public import model_availability, read_hosts

        def work(session: Session) -> dict[str, Any]:
            facts = read_hosts(session)
            items = [self._host_view(item, model_availability(item)) for item in facts]
            online = [item for item in facts if item.state != "offline"]
            return {
                "items": items, "online": len(online), "total": len(facts),
                "slots_free": sum(max(0, slot.slots - slot.in_use) for item in online for slot in item.slots),
                "slots_total": sum(item.slots_total for item in facts),
            }
        return self._read(work)

    def get_host(self, *, host_id: str) -> Any:
        return self._read(lambda session: self._one_host(session, host_id))

    def get_host_details(self, *, host_id: str) -> Any:
        """«Подробнее» of a server (administrator): its slots, each provider with the reasons its models cannot be used, and the tasks on it."""
        from auditmanager.executors.public import host_details

        def work(session: Session) -> dict[str, Any]:
            details = host_details(session, host_id)
            facts = details.facts
            report = None if facts.report is None else facts.report.report
            providers = []
            for provider in () if report is None else report.providers:
                models = [item for item in details.models if item.provider == provider.provider]
                providers.append(_present(
                    provider=provider.provider, access=provider.access, auth_state=provider.auth_state,
                    cli_version=provider.cli_version,
                    models=[_present(model_id=item.model_id, state=item.state, reasons=list(item.reasons),
                                     cooldown_until=item.cooldown_until) for item in models]))
            return {
                "host": self._host_view(facts, details.models),
                "slots": [{"provider": slot.provider, "access": slot.access, "slots": slot.slots, "in_use": slot.in_use}
                          for slot in facts.slots if slot.access is not None],
                "providers": providers,
                "tasks": [_present(task_id=task.task_id, run_id=task.run_id, provider=task.provider,
                                   model_id=task.model_id, stage_key=task.stage_key, since=task.since)
                          for task in details.tasks],
            }
        return self._read(work)

    # -- writes ----------------------------------------------------------------------------------------------

    def set_enabled(self, *, host_id: str, enabled: bool, user_uid: str, idempotency_key: str) -> Any:
        from auditmanager.executors.public import set_host_enabled

        def work(session: Session) -> dict[str, Any]:
            set_host_enabled(
                session, host_id=host_id, enabled=enabled, roles=self._roles(session, user_uid),
                idempotency_key=idempotency_key, actor_uid=user_uid)
            return self._one_host(session, host_id)
        return self._write(work)

    def set_slots(self, *, host_id: str, slots: dict[str, int], user_uid: str, idempotency_key: str) -> Any:
        from auditmanager.executors.public import set_host_slots

        def work(session: Session) -> dict[str, Any]:
            set_host_slots(
                session, host_id=host_id, slots=slots, roles=self._roles(session, user_uid),
                idempotency_key=idempotency_key, actor_uid=user_uid)
            return self._one_host(session, host_id)
        return self._write(work)

    def archive_host(self, *, host_id: str, user_uid: str, idempotency_key: str) -> Any:
        from auditmanager.executors.public import archive_host

        def work(session: Session) -> dict[str, Any]:
            archive_host(
                session, host_id=host_id, roles=self._roles(session, user_uid), idempotency_key=idempotency_key,
                actor_uid=user_uid)
            return self._one_host(session, host_id)
        return self._write(work)

    def issue_enrollment(self, *, display_name: str, user_uid: str, idempotency_key: str) -> Any:
        from auditmanager.executors.public import issue_host_enrollment

        def work(session: Session) -> dict[str, Any]:
            issued = issue_host_enrollment(
                session, display_name=display_name, roles=self._roles(session, user_uid),
                idempotency_key=idempotency_key, actor_uid=user_uid, configured_origin=self._public_origin)
            record = issued.record
            return {
                "secret": issued.secret, "package_version": issued.package.version, "package_sha256": issued.package.sha256,
                "command": issued.command,
                "enrollment": _present(
                    enrollment_id=record.enrollment_id, host_id=record.host_id, secret_prefix=record.secret_prefix,
                    state=record.state, created_at=record.created_at, created_by=record.created_by,
                    expires_at=record.expires_at, redeemed_at=record.redeemed_at, runner_token_id=record.runner_token_id,
                    revoked_at=record.revoked_at, revoked_by=record.revoked_by),
            }
        return self._write(work)

    @staticmethod
    def _install_view(record: Any) -> dict[str, Any]:
        """An install session of a host: a generated key shows its public half and the ``authorized_keys`` line (public by nature); the
        sealed private half is not a field of the record, and a pasted key shows nothing."""
        from auditmanager.executors.public import authorized_keys_line, observed_fingerprint

        return _present(
            install_id=record.install_id, host_id=record.host_id, state=record.state, access=record.access,
            ssh_host=record.ssh_host, ssh_port=record.ssh_port, ssh_user=record.ssh_user, public_key=record.public_key,
            authorized_keys_line=(None if record.public_key is None
                                  else authorized_keys_line(record.public_key, record.install_id)),
            observed_host_key_fingerprint=observed_fingerprint(record),
            host_key_confirmed_at=record.host_key_confirmed_at, host_key_confirmed_by=record.host_key_confirmed_by,
            package_version=record.package_version, package_sha256=record.package_sha256,
            failure_reason=record.failure_reason, key_removed_at=record.key_removed_at, created_at=record.created_at,
            created_by=record.created_by, updated_at=record.updated_at, finished_at=record.finished_at)

    def create_agent_install(self, *, body: Any, user_uid: str, idempotency_key: str) -> Any:
        from auditmanager.executors.public import create_host_agent_install

        def work(session: Session) -> dict[str, Any]:
            record = create_host_agent_install(
                session, display_name=body.display_name, access=body.access.value, ssh_host=body.ssh_host,
                ssh_port=body.ssh_port, ssh_user=body.ssh_user, private_key=body.private_key, ring=self._ring,
                roles=self._roles(session, user_uid), idempotency_key=idempotency_key, actor_uid=user_uid)
            return self._install_view(record)
        return self._write(work)

    def get_agent_install(self, *, host_id: str, install_id: str) -> Any:
        from auditmanager.executors.public import get_host_agent_install

        # A read that may end an overdue session and replace its key, so it commits (as for a connection's install).
        return self._write(lambda session: self._install_view(
            get_host_agent_install(session, host_id=host_id, install_id=install_id)))

    def confirm_agent_install_host_key(
        self, *, host_id: str, install_id: str, host_key_fingerprint: str, user_uid: str, idempotency_key: str
    ) -> Any:
        from auditmanager.executors.public import confirm_host_agent_install_host_key

        def work(session: Session) -> dict[str, Any]:
            record = confirm_host_agent_install_host_key(
                session, host_id=host_id, install_id=install_id, fingerprint=host_key_fingerprint,
                roles=self._roles(session, user_uid), idempotency_key=idempotency_key, actor_uid=user_uid)
            return self._install_view(record)
        return self._write(work)

    # -- the agent's: the three calls the integrator's runner adapter makes for a host token ----------------------

    def redeem_host_enrollment(self, *, enrollment: Any, runner_instance_id: str) -> dict[str, Any]:
        """The exchange of a **host** grant for the host token: the token's shape (``IssuedRunnerToken``) with ``host_id`` and the catalogue.
        ``enrollment`` is the seam's identity (``enrollment_id``, ``connection_id`` or ``host_id``, ``exchange_key``)."""
        from auditmanager.executors.public import EnrollmentPrincipal, catalogue, redeem_enrollment

        def work(session: Session) -> dict[str, Any]:
            redeemed = redeem_enrollment(
                session,
                EnrollmentPrincipal(
                    enrollment_id=enrollment.enrollment_id, connection_id=enrollment.connection_id,
                    exchange_key=enrollment.exchange_key, host_id=enrollment.host_id),
                runner_instance_id=runner_instance_id)
            record = redeemed.record
            return {"token": redeemed.value, "host_id": record.host_id, "catalogue": catalogue().for_agent()}
        return self._write(work)

    def report_health(self, *, runner: Any, body: Mapping[str, Any]) -> dict[str, Any]:
        """``reportRunnerHealth`` for a host token: the token's health as for any runner, then the host's snapshot only when it changed. ``body`` is
        the request as plain values (the adapter converts the model); answers ``{recorded_at, catalogue, enabled}``."""
        from auditmanager.executors.public import report_host_runner_health

        def work(session: Session) -> dict[str, Any]:
            ack = report_host_runner_health(
                session, token_id=runner.token_id, host_id=runner.host_id, agent_version=body["agent_version"],
                clis=body["clis"], concurrency=body["concurrency"], execution_profile=body["execution_profile"],
                features=body["features"], providers=body.get("providers"), slots=body.get("slots"),
                key_file=body.get("key_file"))
            return {"recorded_at": ack.recorded_at, "catalogue": ack.catalogue, "enabled": ack.enabled}
        return self._write(work)
