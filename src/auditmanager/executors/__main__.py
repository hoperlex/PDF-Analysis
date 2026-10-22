"""``python -m auditmanager.executors import-env | rewrap | reach`` -- the operator's commands.

Run on the **worker** (``docker compose exec worker python -m auditmanager.executors ...``), from
its image and environment: it holds the private key ring and the network path real calls take.
Output is identities, counts and outcome words; a key, a header or an address is never printed.

Exit codes: ``0`` done (or nothing to do), ``2`` refused (the message says why), ``3`` import-env
created the connection but its probe did not pass, so it is not routed yet.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping

from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.operations import (
    SYSTEM_ACTOR_UID,
    OperationRefused,
    import_env,
    reach,
    rewrap,
)
from auditmanager.executors.sealing import SealingConfigurationError, load_private_ring

__all__ = ["main"]


def _session_factory(environ: Mapping[str, str]):  # type: ignore[no-untyped-def]
    from auditmanager.shared.db import create_database_engine, create_session_factory
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url

    url = environ.get("DATABASE_URL", "").strip()
    if not url:
        raise OperationRefused("DATABASE_URL is unset")
    return create_session_factory(
        create_database_engine(DatabaseSettings(url=parse_database_url(url))))


def _ring(environ: Mapping[str, str]):  # type: ignore[no-untyped-def]
    try:
        return load_private_ring(
            environ.get("AUDITMANAGER_SECRETS_KEYS"), environ.get("AUDITMANAGER_SECRETS_ACTIVE_KID"))
    except SealingConfigurationError as failure:
        raise OperationRefused(str(failure)) from None


def run(argv: list[str], environ: Mapping[str, str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m auditmanager.executors")
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser(
        "import-env", help="turn PROXY_LLM_* into the first connection (idempotent)")
    importer.add_argument("--actor", default=SYSTEM_ACTOR_UID,
                          help="the administrator's usr_ identity the journal names")
    rewrapper = commands.add_parser(
        "rewrap", help="re-seal every current secret to the active key id")
    rewrapper.add_argument("--actor", default=SYSTEM_ACTOR_UID)
    reacher = commands.add_parser(
        "reach", help="may this container send a key to the address, and does it connect")
    reacher.add_argument("url")
    reacher.add_argument("--transport", choices=("direct", "vpn"), default="direct")
    arguments = parser.parse_args(argv)
    policy = DestinationPolicy.from_environment(dict(environ))
    try:
        if arguments.command == "reach":
            report = reach(arguments.url, transport=arguments.transport, policy=policy)
            print(f"reach: {report.outcome}" + (f" ({report.category})" if report.category else ""))
            return 0 if report.outcome == "reachable" else 2
        sessions = _session_factory(environ)
        ring = _ring(environ)
        if arguments.command == "import-env":
            result = import_env(sessions, environ, ring=ring, policy=policy,
                                actor_uid=arguments.actor)
            if not result.created:
                print(f"import-env: already imported as {result.connection_id}; nothing changed")
                return 0
            print(f"import-env: created {result.connection_id}; probe {result.probe_outcome}; "
                  f"{'routed to text_analysis' if result.routed else 'NOT routed'}")
            return 0 if result.routed else 3
        report = rewrap(sessions, ring=ring, actor_uid=arguments.actor)
        print(f"rewrap: {report.rewrapped} re-sealed, {report.already_active} already on the "
              f"active key, {len(report.unreadable)} unreadable")
        for secret_id in report.unreadable:
            print(f"rewrap: unreadable {secret_id}")
        return 0 if not report.unreadable else 2
    except OperationRefused as refusal:
        print(f"auditmanager-executors: {refusal}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    return run(sys.argv[1:] if argv is None else argv, os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
