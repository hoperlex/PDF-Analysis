"""The deploy server's own subscriptions as a host (`LOCAL-AGENT-01`): the stand's half of `infra/deploy/local-agent.sh`.

The deploy server may itself hold signed-in ``codex`` and ``claude`` clients (the owner's subscription logins, often those of the VS Code
extensions under ``root``). `local-agent.sh` finds them on the machine and installs the ordinary host agent of ``HOSTS-AGENT-01`` for them;
this module is the part that has to run where the database is: inside the stack's ``api`` container, as

    python -m auditmanager.bootstrap.local_host package
    python -m auditmanager.bootstrap.local_host show   --name NAME
    python -m auditmanager.bootstrap.local_host enroll --name NAME --origin ORIGIN [--actor LOGIN]

Every command prints **one line of JSON** on stdout and nothing else there, so the script reads members, never prose:

* ``package`` -- ``{"package_version", "package_sha256"}``: the agent package this stand serves (``latest_package``), which the script
  downloads from the stand and checks against this digest, as the copyable command of path B does.
* ``show`` -- ``{"host": null}``, or ``{"host": {...}}`` with the live host of that name as the executor screen has it (``HostsService``'s view:
  ``host_id``, ``enabled``, ``state``, ``last_seen_at``, ``agent_version``, the usable ``models``).
* ``enroll`` -- issues the one-time grant of the host of that name through ``HostsService.issue_enrollment``, exactly as «Подключить сервер»
  does: a new host is created **enabled** (owner, 2026-11-20: the card is on at once; «Использовать» switches it off), a live one gets a new
  grant (a move). Prints ``{"secret", "host_id", "package_version", "package_sha256", "actor_login"}``. The secret is in that line and nowhere
  else: the script hands it to ``install.sh`` through the environment, and the stand keeps only its hash.

**The actor.** A grant records the administrator who issued it, and the command refuses anyone else. A deploy has no signed-in user, so the
grant is issued in the name of the active administrator named by ``--actor``, or -- when none is named -- of the active administrator account
created first. That is a rule, not a guess: the output names the account it used, and with no active administrator the command refuses.

**The origin** is the one the agent will use, ``http://127.0.0.1:<port>`` from the script (the stack's own proxy on the loopback interface; the
agent accepts plain HTTP only for a loopback host). The grant's install command carries it; the script does not run that command.

Exit codes: 0 done; 2 usage; 3 refused (a typed refusal of the stand, one line on stderr: its code and reason); 4 failed.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Callable, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.errors import DomainError

__all__ = ["DEFAULT_NAME", "choose_actor", "main", "run"]

#: The name of the deploy server's host card when the operator gives none.
DEFAULT_NAME: Final[str] = "Этот сервер"

EXIT_OK: Final[int] = 0
EXIT_USAGE: Final[int] = 2
EXIT_REFUSED: Final[int] = 3
EXIT_FAILED: Final[int] = 4


class Refused(Exception):
    """A refusal of this module itself (no administrator, an unknown actor); printed like a stand's refusal."""


def choose_actor(accounts: Sequence[Any], login: str | None) -> Any:
    """The administrator a grant is issued in the name of: the active account ``login`` when given (it must hold ``admin``), otherwise
    the active administrator created first (ties broken by ``user_uid``). ``Refused`` when there is none."""
    admins = [item for item in accounts if "admin" in item.roles and getattr(item.record, "archived_at", None) is None]
    if login is not None:
        for item in admins:
            if item.record.login == login:
                return item.record
        raise Refused(f"no active administrator with the login {login!r}")
    if not admins:
        raise Refused("the stand has no active administrator to issue the grant in the name of")
    first = min(admins, key=lambda item: (item.record.created_at, str(item.record.user_uid)))
    return first.record


def _plain(value: Any) -> Any:
    """JSON for the views: datetimes as ISO text, enums as their values."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value") and not isinstance(value, (str, int, float, bool)):
        return value.value
    return value


def _find_host(listing: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in listing.get("items", []):
        if str(item.get("display_name", "")).lower() == name.lower() and item.get("archived_at") is None:
            return item
    return None


def _package() -> dict[str, Any]:
    from auditmanager.executors.public import latest_package

    package = latest_package()
    return {"package_version": package.version, "package_sha256": package.sha256}


def run(
    argv: Sequence[str], *, session_factory: Callable[[], sessionmaker[Session]], package: Callable[[], dict[str, Any]] = _package,
) -> dict[str, Any]:
    """Do one command and return the line to print. Raises ``DomainError`` / ``Refused`` for a refusal, ``SystemExit`` for a usage error."""
    parser = argparse.ArgumentParser(prog="python -m auditmanager.bootstrap.local_host", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("package", help="the agent package this stand serves")
    show = commands.add_parser("show", help="the live host of a name")
    show.add_argument("--name", default=DEFAULT_NAME)
    enroll = commands.add_parser("enroll", help="issue the one-time grant of the host of a name")
    enroll.add_argument("--name", default=DEFAULT_NAME)
    enroll.add_argument("--origin", required=True, help="the origin the agent uses, e.g. http://127.0.0.1:8088")
    enroll.add_argument("--actor", default=None, help="the login of the active administrator the grant is issued in the name of")
    args = parser.parse_args(list(argv))

    if args.command == "package":
        return package()

    from auditmanager.bootstrap.hosts_service import HostsService

    if args.command == "show":
        service = HostsService(session_factory=session_factory())
        return {"host": _plain(_find_host(service.list_hosts(), args.name))}

    from auditmanager.access.public import AccountRepository

    factory = session_factory()
    with factory() as session:
        actor = choose_actor(AccountRepository().list_accounts(session, include_archived=False), args.actor)
    service = HostsService(session_factory=factory, public_origin=args.origin)
    issued = service.issue_enrollment(
        display_name=args.name, user_uid=str(actor.user_uid), idempotency_key=f"local-agent-{uuid.uuid4().hex}")
    return {
        "secret": issued["secret"], "host_id": issued["enrollment"]["host_id"], "package_version": issued["package_version"],
        "package_sha256": issued["package_sha256"], "actor_login": actor.login,
    }


def _default_factory() -> sessionmaker[Session]:
    from auditmanager.shared.db.session import get_session_factory

    return get_session_factory()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        line = run(sys.argv[1:] if argv is None else argv, session_factory=_default_factory)
    except SystemExit as stop:
        return EXIT_OK if stop.code in (0, None) else EXIT_USAGE
    except DomainError as error:
        fields = error.detail_fields
        reason = fields.get("conflict_reason") or fields.get("dependency") or fields.get("required_capability") or ""
        print(f"refused: {error.code.value} {reason}".rstrip(), file=sys.stderr)
        return EXIT_REFUSED
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except Exception as error:  # noqa: BLE001 - any other failure is "failed", and its class is all that is printed
        print(f"failed: {type(error).__name__}", file=sys.stderr)
        return EXIT_FAILED
    print(json.dumps(line, ensure_ascii=False, separators=(",", ":")))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
