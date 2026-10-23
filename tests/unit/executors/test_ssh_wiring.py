from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from auditmanager.executors import probe_runner as module
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.model import ConnectionRecord, ProbeRecord
from auditmanager.executors.probe_runner import ProbeRunner
from auditmanager.executors.probes import ProbeResult
from tests.unit.executors.test_ssh_adapter import HOST_KEY, revision

NOW = datetime.now(timezone.utc)


class Store:
    def get_connection(self, session, connection_id):
        return ConnectionRecord("exc_1", "ssh_command", "SSH", NOW, "usr_1")

    def get_revision(self, session, revision_id):
        return revision()


@contextmanager
def sessions():
    yield object()


def probe() -> ProbeRecord:
    return ProbeRecord(
        "epb_1", "exc_1", "excr_1", "exs_1", "running", None, None, None, None,
        None, None, None, None, NOW, "usr_1", NOW, None,
    )


def test_worker_opens_ssh_key_for_ssh_destination(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = []
    monkeypatch.setattr(module, "open_secret", lambda session, ring, **kwargs:
                        opened.append(kwargs["destination"]) or "private")
    monkeypatch.setattr(module, "probe_ssh_command", lambda settings, key, **kwargs:
                        ProbeResult("ok", reported_model=settings.gateway_model))
    runner = ProbeRunner(sessions, ring=None, policy=DestinationPolicy(), repository=Store())
    result = runner._evaluate(probe())
    assert result.outcome == "ok"
    assert opened == ["ssh_command|example.com:22|"]


def test_worker_records_observed_host_key(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = []
    monkeypatch.setattr(ProbeRunner, "_evaluate", lambda self, item:
                        ProbeResult("host_key_unpinned", observed_host_key=HOST_KEY))
    monkeypatch.setattr(module, "record_probe_result", lambda session, probe_id, **kwargs:
                        recorded.append(kwargs) or True)
    runner = ProbeRunner(sessions, ring=None, policy=DestinationPolicy(), repository=Store())
    runner._run(probe())
    assert recorded[0]["observed_host_key"] == HOST_KEY
