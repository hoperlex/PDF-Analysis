"""`EXEC-CANDIDATE-2`: the ``pull`` kind is wired into the resolver, the usability rule and the
worker's probe loop. No database and no network: the stores are stand-ins and the probe is a stub.

The adapter itself (the wait, the deadline, the two dispatch classes) is `test_pull_adapter.py`;
this file holds the seams that connect it to a run: that the registry serves the kind, that the
resolver builds its adapter with no key to open, that a route's usability asks for a probe on *no*
secret, and that a ``pull`` probe does not hold the probe thread for the minutes a runner needs.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.executors import probe_runner as probe_runner_module
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.kinds import KindRuntime, adapter_for
from auditmanager.executors.model import (
    PULL_PROBE_WINDOW_SECONDS,
    ConnectionRecord,
    ProbeRecord,
    RevisionRecord,
    RevisionSettings,
)
from auditmanager.executors.probe_runner import PULL_PROBE_THREADS, ProbeRunner
from auditmanager.executors.probes import ProbeResult
from auditmanager.executors.pull import PROBE_ANSWER_SECONDS, PROBE_CLAIM_SECONDS, PullAdapter
from auditmanager.executors.resolver import bind_connection
from auditmanager.executors.usability import ensure_routable, is_probed_ok, is_served
from auditmanager.jobs.lease import AttemptContext
from auditmanager.shared.errors import DomainError

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
MODEL = "claude-opus-5"


def _connection(kind: str = "pull", connection_id: str = "exc_C") -> ConnectionRecord:
    return ConnectionRecord(
        connection_id=connection_id, kind=kind, display_name="n", created_at=NOW, created_by="usr_A")


def _revision(*, client: str = "claude_code_session", connection_id: str = "exc_C") -> RevisionRecord:
    return RevisionRecord(
        revision_id="excr_R", connection_id=connection_id, revision_no=1, created_at=NOW,
        created_by="usr_A", settings=RevisionSettings(
            pin_id=MODEL, gateway_model=MODEL, billing="not_metered", allow_client_documents=False,
            timeout_seconds=60, pull_client=client, answer_deadline_seconds=600, max_claimed_tasks=1),
    )


def _ssh_revision() -> RevisionRecord:
    return RevisionRecord(
        revision_id="excr_S", connection_id="exc_S", revision_no=1, created_at=NOW,
        created_by="usr_A", settings=RevisionSettings(
            pin_id=MODEL, gateway_model=MODEL, billing="metered", allow_client_documents=False,
            timeout_seconds=60, ssh_host="h", ssh_port=22, ssh_user="u",
            ssh_profile="claude_code_headless"),
    )


def _probe(outcome: str | None = None, *, probe_id: str = "epb_P", state: str = "finished") -> ProbeRecord:
    return ProbeRecord(
        probe_id=probe_id, connection_id="exc_C", revision_id="excr_R", secret_id=None, state=state,
        outcome=outcome, reported_model=None, identity_basis=None, latency_ms=None, http_status=None,
        rate_check=None, observed_host_key=None, detail=None, requested_at=NOW, requested_by="usr_A",
        started_at=None, finished_at=None,
    )


class Store:
    """What the resolver and the usability rule ask of ``ExecutorRepository``, answered by hand."""

    def __init__(self, connection: ConnectionRecord, revision: RevisionRecord,
                 probe: ProbeRecord | None = None) -> None:
        self.connection, self.revision, self.probe = connection, revision, probe
        self.asked: list[tuple[str, str | None]] = []

    def get_revision(self, session: Any, revision_id: str) -> RevisionRecord | None:
        return self.revision if revision_id == self.revision.revision_id else None

    def get_connection(self, session: Any, connection_id: str) -> ConnectionRecord | None:
        return self.connection if connection_id == self.connection.connection_id else None

    def current_secrets(self, session: Any, connection_ids: Any) -> dict[str, list[Any]]:
        return {}

    def latest_finished_probe(self, session: Any, revision_id: str, secret_id: str | None) -> ProbeRecord | None:
        self.asked.append((revision_id, secret_id))
        return self.probe


class TestTheRegistryServesTheKind:
    def test_pull_is_a_channel_kind_with_no_key_and_http_api_is_not(self) -> None:
        pull_entry, http_entry = adapter_for("pull"), adapter_for("http_api")
        assert pull_entry is not None and http_entry is not None
        assert pull_entry.channel is not None and pull_entry.purpose is None
        assert http_entry.channel is None and http_entry.purpose == "api_key"
        assert adapter_for("ssh_command") is not None, "SSH command is served by its later slice"

    def test_every_pull_revision_is_served_whatever_its_client_and_the_label_names_the_client(self) -> None:
        entry = adapter_for("pull")
        assert entry is not None
        for client in ("claude_code_session", "agent"):
            revision = _revision(client=client)
            assert entry.serves(revision) is True and entry.provider_label(revision) == client
        assert is_served(_connection(), _revision()) is True
        assert is_served(_connection("ssh_command", "exc_S"), _ssh_revision()) is True

    def test_the_sweep_waits_for_the_whole_probe_window_a_runner_needs(self) -> None:
        assert PULL_PROBE_WINDOW_SECONDS == PROBE_CLAIM_SECONDS + PROBE_ANSWER_SECONDS == 240


class TestTheResolverBuildsTheAdapterWithNoKey:
    def _bind(self, store: Store, runtime: KindRuntime | None, context: AttemptContext | None = None) -> Any:
        return bind_connection(
            None, "excr_R", ring=None, policy=DestinationPolicy.from_environment({}),  # type: ignore[arg-type]
            context=context, repository=store, runtime=runtime,  # type: ignore[arg-type]
        )

    def test_a_pull_revision_binds_a_task_adapter_that_declares_its_model(self) -> None:
        @contextmanager
        def sessions():  # type: ignore[no-untyped-def]
            yield object()

        context = AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic())
        bound = self._bind(Store(_connection(), _revision()), KindRuntime(sessions, None), context)
        assert isinstance(bound.adapter, PullAdapter)
        assert (bound.identity_basis, bound.provider_label) == ("declared", "claude_code_session")
        assert bound.revision.revision_id == "excr_R" and bound.connection.kind == "pull"
        # The adapter is handed the Attempt's own context, the object the heartbeat and the call
        # journal update, so the deadline and the call id it reads are the live ones.
        assert bound.adapter._context is context

    def test_a_process_with_no_runtime_cannot_serve_it_and_says_so_as_a_missing_route(self) -> None:
        with pytest.raises(DomainError) as refused:
            self._bind(Store(_connection(), _revision()), None)
        assert refused.value.code.value == "dependency_unavailable"
        assert "executor_route_missing" in str(refused.value.detail_fields)


class TestAPullConnectionIsUsableOnAProbeWithNoSecret:
    def test_an_ok_probe_on_no_secret_makes_it_routable(self) -> None:
        store = Store(_connection(), _revision(), _probe("ok"))
        assert is_probed_ok(None, store, _connection(), _revision()) is True  # type: ignore[arg-type]
        assert store.asked == [("excr_R", None)], "no key exists for this kind: the probe is asked for on none"
        ensure_routable(None, store, _connection(), _revision())  # type: ignore[arg-type]

    @pytest.mark.parametrize("outcome", ["no_runner_online", "timeout", "model_mismatch", "protocol_error"])
    def test_any_other_outcome_is_not_usable(self, outcome: str) -> None:
        store = Store(_connection(), _revision(), _probe(outcome))
        assert is_probed_ok(None, store, _connection(), _revision()) is False  # type: ignore[arg-type]
        with pytest.raises(DomainError) as refused:
            ensure_routable(None, store, _connection(), _revision())  # type: ignore[arg-type]
        assert "connection_not_probed" in str(refused.value.detail_fields)

    def test_no_probe_at_all_is_not_usable_and_a_key_kind_without_a_key_still_is_not(self) -> None:
        assert is_probed_ok(None, Store(_connection(), _revision(), None), _connection(), _revision()) is False  # type: ignore[arg-type]
        http = ConnectionRecord("exc_H", "http_api", "n", NOW, "usr_A")
        store = Store(http, _revision(connection_id="exc_H"), _probe("ok"))
        assert is_probed_ok(None, store, http, _revision(connection_id="exc_H")) is False  # type: ignore[arg-type]
        assert store.asked == [], "an http_api connection with no key is not probed-ok, however the probe ended"


class _Sessions:
    @contextmanager
    def __call__(self):  # type: ignore[no-untyped-def]
        class Session:
            def commit(self) -> None: ...

        yield Session()


class _ProbeStore:
    def __init__(self, probes: list[ProbeRecord], kind: str = "pull") -> None:
        self.waiting, self.kind = list(probes), kind
        self.finished: dict[str, str] = {}
        self.lock = threading.Lock()

    def claim_requested_probe(self, session: Any) -> ProbeRecord | None:
        return self.waiting.pop(0) if self.waiting else None

    def get_connection(self, session: Any, connection_id: str) -> ConnectionRecord | None:
        return _connection(self.kind, connection_id)

    def get_revision(self, session: Any, revision_id: str) -> RevisionRecord | None:
        return _revision()

    def finish_probe(self, session: Any, probe_id: str, **fields: Any) -> bool:
        with self.lock:
            self.finished[probe_id] = fields["outcome"]
        return True


def _probe_record(probe_id: str) -> ProbeRecord:
    return _probe(probe_id=probe_id, state="running")


class TestThePullProbeIsRunOnTheWorkerWithoutHoldingItsProbeThread:
    def _runner(self, store: _ProbeStore) -> ProbeRunner:
        return ProbeRunner(
            _Sessions(), ring=None, policy=DestinationPolicy.from_environment({}),  # type: ignore[arg-type]
            repository=store, engine=None,  # type: ignore[arg-type]
        )

    def test_the_probe_is_the_runner_channels_and_no_key_is_opened(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _ProbeStore([_probe_record("epb_1")])
        seen: list[tuple[str, str]] = []

        def probe(sessions: Any, revision: RevisionRecord, probe_id: str, *, engine: Any = None) -> ProbeResult:
            seen.append((revision.revision_id, probe_id))
            return ProbeResult("ok", None, MODEL, "declared", 12, None, "not_metered")

        monkeypatch.setattr(probe_runner_module, "probe_pull", probe)
        monkeypatch.setattr(probe_runner_module, "open_secret", lambda *a, **k: pytest.fail("a pull probe opens no key"))
        runner = self._runner(store)
        assert runner.run_pending() == 1
        runner.join_pull_probes(5)
        assert seen == [("excr_R", "epb_1")] and store.finished == {"epb_1": "ok"}

    def test_run_pending_returns_while_a_runner_is_still_being_waited_for(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _ProbeStore([_probe_record("epb_slow")])
        release = threading.Event()

        def probe(sessions: Any, revision: RevisionRecord, probe_id: str, *, engine: Any = None) -> ProbeResult:
            assert release.wait(10)
            return ProbeResult("no_runner_online", "no runner took the probe task within 120 seconds")

        monkeypatch.setattr(probe_runner_module, "probe_pull", probe)
        runner = self._runner(store)
        started = time.monotonic()
        assert runner.run_pending() == 1
        assert time.monotonic() - started < 2, "the probe thread must be free for the next probe"
        assert store.finished == {}, "still waiting"
        release.set()
        runner.join_pull_probes(5)
        assert store.finished == {"epb_slow": "no_runner_online"}

    def test_a_probe_of_another_kind_is_run_in_line(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _ProbeStore([_probe_record("epb_h")], kind="http_api")
        runner = self._runner(store)
        threads: list[str] = []

        def evaluate(probe: ProbeRecord) -> ProbeResult:
            threads.append(threading.current_thread().name)
            return ProbeResult("ok")

        monkeypatch.setattr(runner, "_evaluate", evaluate)
        assert runner.run_pending() == 1
        assert threads == [threading.current_thread().name], "an http_api probe stays on the probe thread"

    def test_no_more_than_the_allowed_number_wait_at_once_the_rest_run_in_line(self, monkeypatch: pytest.MonkeyPatch) -> None:
        total = PULL_PROBE_THREADS + 1
        store = _ProbeStore([_probe_record(f"epb_{n}") for n in range(total)])
        release = threading.Event()
        names: list[str] = []

        def probe(sessions: Any, revision: RevisionRecord, probe_id: str, *, engine: Any = None) -> ProbeResult:
            names.append(threading.current_thread().name)
            if len(names) <= PULL_PROBE_THREADS:
                assert release.wait(10)
            return ProbeResult("ok")

        monkeypatch.setattr(probe_runner_module, "probe_pull", probe)
        runner = self._runner(store)
        runner._batch = total
        # The last one runs on this thread, after the others are parked: so release them from a timer.
        threading.Timer(0.5, release.set).start()
        assert runner.run_pending() == total
        runner.join_pull_probes(5)
        assert len(store.finished) == total
        assert names.count(threading.current_thread().name) == 1, "the overflow ran in line"
