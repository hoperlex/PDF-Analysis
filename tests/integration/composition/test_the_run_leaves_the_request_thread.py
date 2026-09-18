"""`D-20`, over HTTP: the ``202`` is not the result, and ``running`` is a reading.

`W15RUN-6` measured the defect in a browser. ``RunAdapter.start_run`` imported
``execute_run`` and called it inside the same ``_write(...)`` that created the run, so:

* the ``202`` already carried a terminal, and ``pollRunStatus`` -- which loops until
  ``isTerminalRunState`` -- made exactly one request and stopped;
* ``queued`` and ``running`` were written by the executor and never committed, so no
  second connection could read either. The states were reachable in the code and
  unobservable from outside it.

**How this suite proves observability without sleeping.** Nothing here waits for a
duration. The model adapter is gated: it announces that it has been entered and then
blocks on a :class:`threading.Event` until the test releases it. Between those two points
the run is, definitionally, inside ``text_analysis`` -- which is after
``queued -> running`` and after the carrier's commit -- so a ``getRunStatus`` issued there
*must* read ``running``, on any machine, under any load. A test that polled for a second
and hoped would be a flaky test wearing a green tick; this programme has already spent a
session on a misdiagnosed flake.

The run port is the shipped :class:`~auditmanager.bootstrap.adapters.RunAdapter` behind
the shipped ``build_router``, driven through ``starlette``'s test client. The gate is in
the *provider*, which is a collaborator the composition root injects anyway -- no module
under test is patched and no private attribute is reached into.

**Why this module lives here and not beside the run executor.** It needs the run-suite
harness's ``seed_version``, and it loads it by explicit path exactly as
``tests/integration/exports`` does -- but it deliberately does **not** bind that harness's
autouse ``_no_network`` fixture, which refuses every new socket once a test body starts.
This module opens two that the run suite never does: ``TestClient`` creates a socketpair
for its portal, and the carrier's worker thread opens its own connection to the object
store. ``_no_network`` exists so a recorded suite cannot spend, and that property is held
here by two stronger things: the adapter is constructed in this file and is a
``RecordedAdapter`` (or this file's gate in front of one), and the root ``conftest`` has
already removed every provider-selecting variable and every credential from the process
for the whole session. There is nothing in this process to spend with.
"""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any, Iterator

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.analysis.text import ProviderMode, RecordedAdapter
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.bootstrap.adapters import RunAdapter
from auditmanager.runs import (
    CRASHED_REASON,
    INTERRUPTED_REASON,
    RunRepository,
    ThreadCarrier,
    reconcile_at_startup,
)

from auditmanager.analysis.text import ProviderConfig
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.storage import S3BlobStore, S3StorageSettings

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"

if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

#: `T-6`. Written out, not imported from the seam it authenticates against.
STATIC_TOKEN = "w20-exec-carrier-token"

#: The four `audit_run` terminals, written out rather than read from the topology this
#: suite drives: an expectation taken from the thing under test cannot report that it
#: moved.
TERMINALS = frozenset({"published", "partial", "failed", "cancelled"})


# --- the gated provider --------------------------------------------------------------


class GatedAdapter:
    """A real recorded adapter with a barrier in front of the one call it makes.

    Satisfies ``ModelAdapter``: ``provider_mode`` is a read-only property reporting what
    the delegate reports, so nothing here can make a replay look live -- ``execute_run``
    cross-checks the adapter's mode against the run row and would refuse.

    Two events, and neither is a timer. ``entered`` is set by the worker thread the moment
    it reaches the provider; ``release`` is waited on until the test sets it.
    """

    __slots__ = ("_delegate", "entered", "release", "fail_with")

    def __init__(self, delegate: RecordedAdapter, *, fail_with: BaseException | None = None) -> None:
        self._delegate = delegate
        self.entered = threading.Event()
        self.release = threading.Event()
        self.fail_with = fail_with

    @property
    def provider_mode(self) -> ProviderMode:
        return self._delegate.provider_mode

    def complete(self, request: Any) -> Any:
        self.entered.set()
        assert self.release.wait(timeout=60), "the test never released the provider"
        if self.fail_with is not None:
            raise self.fail_with
        return self._delegate.complete(request)


# --- the application under test ------------------------------------------------------


class _Built:
    """Just enough of ``Application`` for ``create_asgi_app``.

    Three attributes, and each is read by a named thing: ``router`` by the assembler,
    ``carrier`` published as ``app.state.run_carrier``, and ``session_factory`` by the
    startup lifespan's reconciliation. Unlike the other stand-ins in this repository this
    one really does serve runs, so it really does need all three.
    """

    __slots__ = ("router", "carrier", "session_factory")

    def __init__(self, router: Any, carrier: Any, sessions: Any) -> None:
        self.router = router
        self.carrier = carrier
        self.session_factory = sessions


@pytest.fixture(scope="module")
def engine() -> Any:
    """The lane's engine. This module's own, so no autouse guard comes with it."""
    harness._load_dotenv_if_needed()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set; this suite runs against real PostgreSQL")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="module")
def blob_store() -> S3BlobStore:
    harness._load_dotenv_if_needed()
    return S3BlobStore(S3StorageSettings.from_env())


@pytest.fixture(scope="module")
def provider_config() -> ProviderConfig:
    """Recorded mode, the pinned model, and a ceiling. Never a credential."""
    from auditmanager.analysis.text import ProviderMode as _Mode

    return ProviderConfig(
        mode=_Mode.RECORDED,
        model_id=harness.RECORDED_MODEL_ID,
        run_cost_ceiling_usd=1.0,
        api_key=None,
        ceiling_is_explicit=True,
    )


@pytest.fixture
def recorded_adapter() -> RecordedAdapter:
    return RecordedAdapter(harness.RECORDINGS)


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    """A **committing** session factory on the lane's engine.

    Deliberately not the suite's rolled-back ``session`` fixture. The whole question here
    is what a *second connection* can read, and a run inside an uncommitted transaction is
    the `D-20` defect rather than the setup for a test of it.
    """
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture
def committed_version(sessions: sessionmaker[Session], blob_store: Any) -> Any:
    """One published version, committed, for the worker thread to read.

    Committed rather than rolled back: the whole question is what a *second connection*
    can see, and the carrier's worker is one.
    """
    with sessions() as opened:
        seeded = harness.seed_version(opened, blob_store)
        opened.commit()
    return seeded


def _client(
    sessions: sessionmaker[Session],
    blob_store: Any,
    adapter: Any,
    provider_config: Any,
    carrier: Any,
) -> Iterator[TestClient]:
    run_port = RunAdapter(
        sessions,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        provider_mode="recorded",
        analysis_profile_id=str(_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(_PROFILE.prompt_bundle.prompt_bundle_id),
        carrier=carrier,
    )
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=None,  # type: ignore[arg-type]
        runs=run_port,
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
    )
    app = create_asgi_app(
        environ={API_TOKEN_VARIABLE: STATIC_TOKEN},
        application=_Built(router, carrier, sessions),  # type: ignore[arg-type]
    )
    yield TestClient(app, raise_server_exceptions=False)


def _resolve_profile() -> Any:
    from auditmanager.analysis.text import resolve_profile

    return resolve_profile()


_PROFILE = _resolve_profile()

_AUTH = {"Authorization": f"Bearer {STATIC_TOKEN}"}


def _start(client: TestClient, version_uid: str) -> dict[str, Any]:
    answer = client.post(
        "/runs",
        headers=_AUTH
        | {
            IDEMPOTENCY_HEADER: f"w20exec-{uuid.uuid4().hex[:16]}",
            "Content-Type": "application/json",
        },
        content=json.dumps({"version_uid": str(version_uid)}).encode("utf-8"),
    )
    assert answer.status_code == 202, answer.content
    return answer.json()  # type: ignore[no-any-return]


def _status(client: TestClient, run_id: str) -> dict[str, Any]:
    answer = client.get(f"/runs/{run_id}", headers=_AUTH)
    assert answer.status_code == 200, answer.content
    return answer.json()  # type: ignore[no-any-return]


# --- the claims ----------------------------------------------------------------------


class TestRunningIsAReadingAndNotAnInternalStep:
    """The `D-20` repair, asserted on response bodies a client could have received."""

    def test_a_poller_reads_running_while_the_provider_is_still_being_waited_on(
        self,
        sessions: sessionmaker[Session],
        blob_store: Any,
        recorded_adapter: RecordedAdapter,
        provider_config: Any,
        committed_version: Any,
    ) -> None:
        """202, then `running`, then a terminal -- three readings, one run.

        The sequence a browser gets. Before `D-20` it was one reading and the loop in
        `web/src/shared/api/polling.ts` exited on the first response.
        """
        gated = GatedAdapter(recorded_adapter)
        carrier = ThreadCarrier()
        try:
            client = next(_client(sessions, blob_store, gated, provider_config, carrier))
            started = _start(client, committed_version.version_uid)
            readings = [started["state"]]

            assert gated.entered.wait(timeout=60), (
                "the provider was never reached; the run is not executing off the "
                "request thread"
            )
            # The run is inside `text_analysis`. That is strictly after the carrier
            # committed `queued -> running`, so this reading cannot be anything else.
            readings.append(_status(client, started["run_id"])["state"])

            gated.release.set()
            assert carrier.drain(timeout=300), "the released run never finished"
            readings.append(_status(client, started["run_id"])["state"])

            assert readings == ["queued", "running", "published"], readings
        finally:
            gated.release.set()
            carrier.shutdown()

    def test_the_202_body_does_not_depend_on_how_fast_the_carrier_is(
        self,
        sessions: sessionmaker[Session],
        blob_store: Any,
        recorded_adapter: RecordedAdapter,
        provider_config: Any,
        committed_version: Any,
    ) -> None:
        """`startRun` answers the accepted state whether or not the worker has started.

        ``RunAdapter.start_run`` builds the view **before** it submits, so the body a
        client receives is a function of what was accepted and not of scheduling. Two runs
        here: one whose worker is held at the provider and one whose worker is free to
        finish, and both ``202`` bodies are the same accepted shape.
        """
        gated = GatedAdapter(recorded_adapter)
        carrier = ThreadCarrier()
        try:
            client = next(_client(sessions, blob_store, gated, provider_config, carrier))
            held = _start(client, committed_version.version_uid)
            assert gated.entered.wait(timeout=60)

            # A second run, submitted while the first occupies the single worker. It is
            # genuinely queued behind the first -- which is what `queued` has always
            # meant and what no client could see before this change.
            waiting = _start(client, committed_version.version_uid)
            assert _status(client, waiting["run_id"])["state"] == "queued"

            for body in (held, waiting):
                assert body["state"] == "queued", body
                assert body["stages"] == [], body
                assert "terminal_at" not in body, body
        finally:
            gated.release.set()
            carrier.drain(timeout=300)
            carrier.shutdown()


class TestACrashDoesNotStrandARun:
    """What a process death leaves, and what the next reader can do about it."""

    def test_an_exception_on_the_worker_terminates_the_run_rather_than_leaving_it_running(
        self,
        sessions: sessionmaker[Session],
        blob_store: Any,
        recorded_adapter: RecordedAdapter,
        provider_config: Any,
        committed_version: Any,
    ) -> None:
        """A fault that is not a ``DomainError`` reaches a terminal by itself.

        ``run_stage`` catches ``DomainError`` and turns it into a failed stage; anything
        else escapes ``execute_run``. While execution was inline that became a ``500`` and
        the caller learned about it. On a worker thread there is no caller, so the run row
        is the only reader -- and it must not be left saying ``running`` until somebody
        restarts the process.

        The reason is `CRASHED_REASON`, not `INTERRUPTED_REASON`: the process is alive and
        something raised, which sends an operator to a stack trace rather than to a dead
        container.
        """
        gated = GatedAdapter(recorded_adapter, fail_with=RuntimeError("the disk went away"))
        carrier = ThreadCarrier()
        try:
            client = next(_client(sessions, blob_store, gated, provider_config, carrier))
            started = _start(client, committed_version.version_uid)
            assert gated.entered.wait(timeout=60)
            gated.release.set()
            assert carrier.drain(timeout=300)

            body = _status(client, started["run_id"])
            assert body["state"] in TERMINALS, body
            assert body["state"] == "failed", body
            assert body["interrupted_reason"] == CRASHED_REASON, body
            assert body["terminal_reason"], body
        finally:
            gated.release.set()
            carrier.shutdown()

    def test_a_crashed_run_leaves_no_half_written_stage_results(
        self,
        sessions: sessionmaker[Session],
        blob_store: Any,
        recorded_adapter: RecordedAdapter,
        provider_config: Any,
        committed_version: Any,
    ) -> None:
        """The single commit boundary, asserted rather than described.

        Three deterministic stages succeed before the provider is reached, and their rows
        are written in the transaction that the escaping exception rolls back. A reader of
        the failed run therefore sees no stage results at all, rather than three
        successful ones belonging to a run that PC-01 can never finish or resume.
        """
        gated = GatedAdapter(recorded_adapter, fail_with=RuntimeError("the disk went away"))
        carrier = ThreadCarrier()
        try:
            client = next(_client(sessions, blob_store, gated, provider_config, carrier))
            started = _start(client, committed_version.version_uid)
            assert gated.entered.wait(timeout=60)
            gated.release.set()
            assert carrier.drain(timeout=300)

            assert _status(client, started["run_id"])["stages"] == [], (
                "a run whose execution was rolled back reported stage results; the "
                "commit boundary moved inside the analysis"
            )
        finally:
            gated.release.set()
            carrier.shutdown()

    @pytest.mark.parametrize("stranded_state", ["running", "queued"])
    def test_a_process_death_is_resolved_by_the_next_process_start(
        self,
        sessions: sessionmaker[Session],
        blob_store: Any,
        recorded_adapter: RecordedAdapter,
        provider_config: Any,
        committed_version: Any,
        stranded_state: str,
    ) -> None:
        """A killed process runs no ``except`` clause; the next start reconciles.

        Both non-terminal states a death can leave are covered. ``running`` is the worker
        dying mid-analysis; ``queued`` is the process dying between the transaction that
        accepted the run and the worker picking the job up -- a state that did not exist
        before `D-20`, because the accepting transaction used to commit a terminal.

        The kill is simulated by never submitting the job, which leaves exactly the row a
        death leaves: `SIGKILL` cannot be issued at a thread, and a test that killed this
        process would take the assertion with it.
        """
        carrier = ThreadCarrier()
        try:
            client = next(
                _client(sessions, blob_store, recorded_adapter, provider_config, _NoCarrier())
            )
            started = _start(client, committed_version.version_uid)
            run_id = started["run_id"]
            assert started["state"] == "queued"

            repository = RunRepository()
            if stranded_state == "running":
                with sessions() as opened:
                    repository.advance(
                        opened, run_id=run_id, from_state="queued", to_state="running"
                    )
                    opened.commit()
            assert _status(client, run_id)["state"] == stranded_state

            reconcile_at_startup(sessions)

            body = _status(client, run_id)
            assert body["state"] in TERMINALS, body
            assert body["state"] == "failed", body
            assert body["interrupted_reason"] == INTERRUPTED_REASON, body
        finally:
            carrier.shutdown()

    def test_the_lifespan_is_where_that_reconciliation_happens(
        self,
        sessions: sessionmaker[Session],
        blob_store: Any,
        recorded_adapter: RecordedAdapter,
        provider_config: Any,
        committed_version: Any,
    ) -> None:
        """Wiring, not library behaviour.

        ``reconcile`` has existed since `B5` and was called by nothing but its own test,
        because nothing ever committed a ``running`` row for it to find. This asserts the
        call site: entering a served application's lifespan resolves a stranded run, and
        it happens before the application answers anything.
        """
        client = next(
            _client(sessions, blob_store, recorded_adapter, provider_config, _NoCarrier())
        )
        started = _start(client, committed_version.version_uid)
        with sessions() as opened:
            RunRepository().advance(
                opened, run_id=started["run_id"], from_state="queued", to_state="running"
            )
            opened.commit()
        assert _status(client, started["run_id"])["state"] == "running"

        restarted = next(
            _client(sessions, blob_store, recorded_adapter, provider_config, _NoCarrier())
        )
        with restarted:  # the lifespan a served process enters
            body = _status(restarted, started["run_id"])
        assert body["state"] == "failed", body
        assert body["interrupted_reason"] == INTERRUPTED_REASON, body


class _NoCarrier:
    """A carrier that accepts work and never runs it: a process that died on submit.

    Named rather than a lambda because what it models is a specific, real thing -- the
    window between the accepting commit and the worker starting -- and a test that reads
    "a carrier that drops the job" says so.
    """

    def submit(self, job: Any) -> None:
        return None

    def drain(self, timeout: float | None = None) -> bool:
        return True

    def shutdown(self) -> None:
        return None


def test_the_run_row_a_killed_process_leaves_is_the_only_one_it_can_leave(
    sessions: sessionmaker[Session], committed_version: Any
) -> None:
    """`STRANDED_STATES` is complete, checked against the machine rather than asserted.

    Every non-terminal state the `audit_run` machine declares is either one this process
    can be killed in the middle of -- and is then reconciled -- or `created`, which is
    reached and left inside the accepting transaction and so is never committed on its
    own. `validating` is not stranded either: the checkpoint is before the stages, so a
    run that reaches `validating` does so inside the second transaction and a death rolls
    it back to `running`.
    """
    from auditmanager.runs import STRANDED_STATES

    with sessions() as opened:
        declared = {
            row[0]
            for row in opened.execute(
                text(
                    "SELECT DISTINCT to_state FROM contract_state_transition "
                    "WHERE machine = 'audit_run'"
                )
            )
        }
    non_terminal = (declared | {"created"}) - TERMINALS
    assert non_terminal == {"created", "queued", "running", "validating"}, non_terminal
    assert set(STRANDED_STATES) == {"queued", "running"}, STRANDED_STATES
    assert "created" not in STRANDED_STATES, (
        "a reconciler that terminated `created` runs would terminate runs mid-creation"
    )
