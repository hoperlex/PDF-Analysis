"""``python -m auditmanager.workers serve | health`` -- the worker service's entry point.

``serve`` builds the worker runtime from the environment (``EXECUTION_ROLE=worker``, the
API's configuration without ``AUDITMANAGER_API_TOKEN``), registers, and runs until
``SIGTERM`` or ``SIGINT``; then it drains for at most :data:`DRAIN_SECONDS` and exits. A
refused configuration exits ``2`` before anything is registered.

``health`` is the container's health check. It reads only the state directory -- the
identity file and the heartbeat file's age -- and touches neither the database nor the
network, so a probe every few seconds costs a process start and nothing else.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Final

#: How long ``SIGTERM`` waits for runs in flight. Below the compose ``stop_grace_period``
#: (300 s), so the process exits by itself and is not killed mid-write.
DRAIN_SECONDS: Final[float] = 270.0
#: The health check's limit: a heartbeat file older than the registry's stale threshold
#: means the heartbeat thread has not committed for that long.
HEALTH_MAX_AGE_SECONDS: Final[float] = 90.0

_log = logging.getLogger("auditmanager.workers")


def serve(environ: Mapping[str, str]) -> int:
    from auditmanager.bootstrap.public import ConfigurationError, build_worker_runtime
    from auditmanager.jobs.public import sweep_stale_temporaries
    from auditmanager.workers.service import WorkerService

    try:
        runtime = build_worker_runtime(environ=dict(environ))
    except ConfigurationError as failure:
        print(f"auditmanager-worker: refusing to start: {failure}", file=sys.stderr)
        return 2

    # `RUN-ROBUSTNESS-01` (D-170): the temporary PDFs a killed predecessor's stages left in
    # this container's /tmp. Only the exact stage prefixes, only files older than the attempt
    # watchdog; never raises.
    sweep_stale_temporaries()

    if (runtime.settings.provider_source == "database"
            and environ.get("PROXY_LLM_BASE_URL", "").strip()):
        from auditmanager.executors.public import DestinationPolicy, OperationRefused, import_env

        try:
            baseline = import_env(
                runtime.session_factory, environ, ring=runtime.settings.secrets_private_ring,
                policy=DestinationPolicy.from_environment(dict(environ)), queue_only=True,
            )
        except OperationRefused as failure:
            # No runner starts with an incomplete baseline. The exception exposes only
            # variable names and controlled outcomes, never the key or URL.
            print(f"auditmanager-worker: baseline connection refused: {failure}", file=sys.stderr)
            return 2
        _log.info("baseline connection %s: %s", baseline.connection_id,
                  "probe queued" if baseline.created else "already present")

    service = WorkerService(
        engine=runtime.engine,
        session_factory=runtime.session_factory,
        execute=runtime.execute,
        version=runtime.version,
        slots=runtime.slots,
        state_dir=runtime.state_dir,
        # `EXEC-HTTP-01`: «Проверить» runs on this process's network path; only a worker that
        # holds the private ring can open a connection's key, so only that one takes probes.
        probe_runner=runtime.probe_runner,
    )
    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        _log.info("signal %d: draining", signum)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    service.start()
    while not stop.wait(1.0):
        if service.failed:
            break
    drained = service.drain(timeout=DRAIN_SECONDS)
    if not drained:
        _log.warning(
            "worker %s exits with %d run(s) in flight; their leases expire and are reclaimed",
            service.worker_id, service.busy,
        )
    service.stop()
    return 0 if drained and not service.failed else 1


def health(environ: Mapping[str, str]) -> int:
    from auditmanager.workers.service import healthy

    state_dir = environ.get("AUDITMANAGER_WORKER_STATE_DIR", "").strip()
    if not state_dir:
        print("auditmanager-worker: no AUDITMANAGER_WORKER_STATE_DIR to check", file=sys.stderr)
        return 1
    ok = healthy(Path(state_dir), max_age_seconds=HEALTH_MAX_AGE_SECONDS, now=time.time())
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m auditmanager.workers")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="register and run claimed jobs until SIGTERM")
    commands.add_parser("health", help="exit 0 when the state directory shows a live worker")
    arguments = parser.parse_args(argv)
    if arguments.command == "health":
        return health(os.environ)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    code = serve(os.environ)
    logging.shutdown()
    sys.stdout.flush()
    sys.stderr.flush()
    # Runs still in flight after the drain hold non-daemon pool threads; the interpreter
    # would join them at exit. Leaving now is what lets their leases expire.
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
