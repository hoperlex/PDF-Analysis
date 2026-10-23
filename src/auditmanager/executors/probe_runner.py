"""The worker's half of «Проверить»: pick up ``requested`` probes, run them, record the result.

`EXEC-HTTP-01` (`R-143`, plan section 4.1). The ``api`` records a probe as ``requested`` and the
worker that holds the private ring opens the key and makes the call, so the test goes over the
same network path as real calls. Three short transactions around one network exchange, so no
database transaction is open while the gateway is slow:

1. claim the oldest ``requested`` probe (``requested -> running``; ``FOR UPDATE SKIP LOCKED``);
2. read the revision and open the key **for the destination recomputed from that revision**;
3. after the exchange, record the result. A probe the ``api``'s sweep already ended
   (``no_worker``, ``timeout``) is left as the sweep wrote it.

The plaintext key lives in a local variable for the length of step 2 to 3. A probe that fails for
any reason is recorded (``protocol_error`` for the unexpected) and never raises into the worker
loop; the log line names the probe, the outcome and nothing else.

A ``pull`` connection (`EXEC-PULL-01`) has no key and no address: its probe posts a task and waits
for a runner to take it (up to two minutes) and answer it (two more). That wait would hold the
probe thread, so a ``pull`` probe is handed to a thread of its own (at most :data:`PULL_PROBE_THREADS`
at once) and the loop goes on taking the others. A worker that dies leaves the probe ``running``;
the ``api``'s sweep ends it.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import ModelPin, pinned_models
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.model import ProbeRecord, RevisionRecord, destination_for
from auditmanager.executors.probes import ProbeResult, probe_http_api, scrub
from auditmanager.executors.pull import probe_pull
from auditmanager.executors.public import (
    SecretUnreadableError,
    open_secret,
    record_probe_result,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PrivateRing
from auditmanager.executors.ssh_probe import probe_ssh_command, probe_ssh_tunnel
from auditmanager.executors.usability import is_served

__all__ = ["PULL_PROBE_THREADS", "ProbeRunner"]

_log = logging.getLogger(__name__)

#: Probes of ``pull`` connections that wait for a runner at the same time.
PULL_PROBE_THREADS = 4


class ProbeRunner:
    """Callable by the worker service: ``runner()`` handles what is waiting and returns how many."""

    def __init__(
        self, session_factory: sessionmaker[Session], *, ring: PrivateRing | None,
        policy: DestinationPolicy, repository: ExecutorRepository | None = None,
        batch: int = 4, engine: Engine | None = None,
    ) -> None:
        self._sessions = session_factory
        self._ring = ring
        self._policy = policy
        self._store = repository or ExecutorRepository()
        self._batch = batch
        #: The source of the ``LISTEN`` connection a ``pull`` probe waits on (``None`` polls).
        self._engine = engine
        self._pull_threads: set[threading.Thread] = set()
        self._pull_lock = threading.Lock()

    def __call__(self) -> int:
        return self.run_pending()

    def run_pending(self) -> int:
        handled = 0
        for _ in range(self._batch):
            with self._sessions() as session:
                probe = self._store.claim_requested_probe(session)
                session.commit()
            if probe is None:
                break
            if not self._run_apart(probe):
                self._run(probe)
            handled += 1
        return handled

    def join_pull_probes(self, timeout: float | None = None) -> None:
        """Wait for the ``pull`` probes in flight (a test, or an orderly stop)."""
        with self._pull_lock:
            threads = list(self._pull_threads)
        for thread in threads:
            thread.join(timeout)

    def _run_apart(self, probe: ProbeRecord) -> bool:
        """Hand a ``pull`` probe to a thread of its own; ``False`` when it is not one, or when
        :data:`PULL_PROBE_THREADS` are already waiting (it is then run in line, as any other)."""
        with self._sessions() as session:
            connection = self._store.get_connection(session, probe.connection_id)
        if connection is None or connection.kind != "pull":
            return False
        with self._pull_lock:
            self._pull_threads = {t for t in self._pull_threads if t.is_alive()}
            if len(self._pull_threads) >= PULL_PROBE_THREADS:
                return False
            thread = threading.Thread(
                target=self._run, args=(probe,), name=f"auditmanager-pull-probe-{probe.probe_id}",
                daemon=True,
            )
            self._pull_threads.add(thread)
        thread.start()
        return True

    # -- one probe ------------------------------------------------------------------------
    def _run(self, probe: ProbeRecord) -> None:
        try:
            result = self._evaluate(probe)
        except Exception as failure:  # noqa: BLE001 - recorded, never raised into the loop
            # The class name only: a message can carry anything, a key included.
            _log.error("probe %s failed unexpectedly (%s)", probe.probe_id, type(failure).__name__)
            result = ProbeResult("protocol_error", "the probe failed unexpectedly")
        try:
            with self._sessions() as session:
                recorded = record_probe_result(
                    session, probe.probe_id, outcome=result.outcome,
                    reported_model=result.reported_model, identity_basis=result.identity_basis,
                    latency_ms=result.latency_ms, http_status=result.http_status,
                    rate_check=result.rate_check, observed_host_key=result.observed_host_key,
                    detail=result.detail,
                    repository=self._store,
                )
                session.commit()
        except Exception as failure:  # noqa: BLE001
            _log.error("probe %s could not be recorded (%s)", probe.probe_id, type(failure).__name__)
            return
        _log.info("probe %s finished: %s%s", probe.probe_id, result.outcome,
                  "" if recorded else " (already ended by the sweep)")

    def _evaluate(self, probe: ProbeRecord) -> ProbeResult:
        with self._sessions() as session:
            connection = self._store.get_connection(session, probe.connection_id)
            revision = self._store.get_revision(session, probe.revision_id)
            if connection is None or revision is None:
                return ProbeResult("protocol_error", "the connection or its revision is gone")
            if not is_served(connection, revision):
                return ProbeResult("kind_not_served", "this kind of connection is not served yet")
            if connection.kind == "pull":
                pull_revision: RevisionRecord | None = revision
                key = ""
            else:
                pull_revision = None
                if probe.secret_id is None:
                    return ProbeResult("secret_unreadable", "no key is set for this connection")
                try:
                    key = open_secret(
                        session, self._ring, secret_id=probe.secret_id,
                        destination=destination_for(
                            connection.kind, revision.settings,
                            "ssh_private_key" if connection.kind == "ssh_command" else "api_key",
                        ),
                        repository=self._store,
                    )
                except SecretUnreadableError:
                    return ProbeResult(
                        "secret_unreadable",
                        "the key cannot be opened here for this address; enter it again",
                    )
                ssh_key = ""
                if connection.kind == "http_api" and revision.settings.transport == "ssh_tunnel":
                    ssh_secret = next((item for item in
                                       self._store.current_secrets(session, [connection.connection_id])
                                       .get(connection.connection_id, ())
                                       if item.purpose == "ssh_private_key"), None)
                    if ssh_secret is None:
                        return ProbeResult("secret_unreadable", "no SSH key is set for this tunnel")
                    try:
                        ssh_key = open_secret(
                            session, self._ring, secret_id=ssh_secret.secret_id,
                            destination=destination_for(connection.kind, revision.settings,
                                                        "ssh_private_key"),
                            repository=self._store,
                        )
                    except SecretUnreadableError:
                        return ProbeResult("secret_unreadable", "the SSH key cannot be opened here")
            settings = revision.settings
        if pull_revision is not None:
            # No key, no address, no transaction open: a runner must take a synthetic task.
            return probe_pull(
                self._sessions, pull_revision, probe.probe_id, engine=self._engine)
        pin: ModelPin | None = next(
            (item for item in pinned_models() if item.model_id == settings.pin_id), None)
        if connection.kind == "ssh_command":
            return probe_ssh_command(
                settings, key, policy=self._policy,
                input_per_mtok_usd=None if pin is None else pin.input_per_mtok_usd,
                output_per_mtok_usd=None if pin is None else pin.output_per_mtok_usd,
            )
        if connection.kind == "http_api" and settings.transport == "ssh_tunnel":
            return probe_ssh_tunnel(
                settings, key, ssh_key, policy=self._policy,
                input_per_mtok_usd=None if pin is None else pin.input_per_mtok_usd,
                output_per_mtok_usd=None if pin is None else pin.output_per_mtok_usd,
            )
        result = probe_http_api(
            settings, key, policy=self._policy,
            input_per_mtok_usd=None if pin is None else pin.input_per_mtok_usd,
            output_per_mtok_usd=None if pin is None else pin.output_per_mtok_usd,
        )
        return ProbeResult(
            result.outcome, scrub(result.detail, key), result.reported_model,
            result.identity_basis, result.latency_ms, result.http_status, result.rate_check,
        )


def runner_for(
    session_factory: sessionmaker[Session], *, ring: Any, environ: dict[str, str],
    engine: Engine | None = None,
) -> ProbeRunner:
    """The runner the composition root wires: the private ring and the environment's allowed hosts,
    and the engine a ``pull`` probe's ``LISTEN`` connection comes from."""
    return ProbeRunner(
        session_factory, ring=ring, policy=DestinationPolicy.from_environment(environ),
        engine=engine,
    )
