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
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import ModelPin, pinned_models
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.model import ProbeRecord, destination_for
from auditmanager.executors.probes import ProbeResult, probe_http_api, scrub
from auditmanager.executors.public import (
    SecretUnreadableError,
    open_secret,
    record_probe_result,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PrivateRing
from auditmanager.executors.usability import is_served

__all__ = ["ProbeRunner"]

_log = logging.getLogger(__name__)


class ProbeRunner:
    """Callable by the worker service: ``runner()`` handles what is waiting and returns how many."""

    def __init__(
        self, session_factory: sessionmaker[Session], *, ring: PrivateRing | None,
        policy: DestinationPolicy, repository: ExecutorRepository | None = None,
        batch: int = 4,
    ) -> None:
        self._sessions = session_factory
        self._ring = ring
        self._policy = policy
        self._store = repository or ExecutorRepository()
        self._batch = batch

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
            self._run(probe)
            handled += 1
        return handled

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
                    rate_check=result.rate_check, detail=result.detail,
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
            if probe.secret_id is None:
                return ProbeResult("secret_unreadable", "no key is set for this connection")
            try:
                key = open_secret(
                    session, self._ring, secret_id=probe.secret_id,
                    destination=destination_for(connection.kind, revision.settings, "api_key"),
                    repository=self._store,
                )
            except SecretUnreadableError:
                return ProbeResult(
                    "secret_unreadable",
                    "the key cannot be opened here for this address; enter it again",
                )
            settings = revision.settings
        pin: ModelPin | None = next(
            (item for item in pinned_models() if item.model_id == settings.pin_id), None)
        result = probe_http_api(
            settings, key, policy=self._policy,
            input_per_mtok_usd=None if pin is None else pin.input_per_mtok_usd,
            output_per_mtok_usd=None if pin is None else pin.output_per_mtok_usd,
        )
        return ProbeResult(
            result.outcome, scrub(result.detail, key), result.reported_model,
            result.identity_basis, result.latency_ms, result.http_status, result.rate_check,
        )


def runner_for(session_factory: sessionmaker[Session], *, ring: Any, environ: dict[str, str]) -> ProbeRunner:
    """The runner the composition root wires: the private ring and the environment's allowed hosts."""
    return ProbeRunner(
        session_factory, ring=ring, policy=DestinationPolicy.from_environment(environ),
    )
