"""AR-V3-BETA-ACCEPT-RECORDED-01: the recorded half of ``AR-V3-BETA-ACCEPT-01``, over HTTP.

``test_v3_saved_text_layer_probe.py`` drives the six AR v3 beta Runs through the service layer. Nothing
drove them the way a reviewer does: ``startArV3BetaGroup`` (``POST /ar-v3-beta/groups``),
``getArV3BetaGroup``, ``getArV3BetaGroupReview`` and ``getArV3BetaPackStatus`` over the real ASGI
application, the **stock recorded composition** (``build_application``) and a **sealed** synthetic pack
that the composition root installs from a manifest file, as a server does. This module is that drive.

What is real, what is stood in
------------------------------
* Real: a throw-away PostgreSQL database migrated to head, the S3 bucket, the pinned PDF extractor, the
  composition root (``build_application``: adapters, ``DurableCarrier``, the sealed-pack loader, the
  stock recorded ``EnvironmentProviders`` with its PROD-11C unmetered replay binding), the authorization
  seam (signed credentials that name real accounts), the ASGI transport, ``start_ar_v3_group``, the
  executor, the v3 provider-call journal, the CITE stage and the review reader.
* Stood in, as in the probe: the **reviewed pack** is data (``D-204``) that no code can supply, so its six
  norm sets are synthetic canonical sets seeded by the probe's own helpers; and the **model answer** is
  a recorded reply written on first sight into a temporary directory and replayed by the stock
  ``RecordedAdapter`` (the adapter holds no client and no credential). The reply carries one grounded
  proposal that cites ``N1`` of its scope and, deliberately, a stated and a required numeric value, so
  that "no numerical conclusion reaches a reviewer" is asserted against a reply that *tried*.

How the Runs are carried (``PROD-11D-V3-GROUP-QUEUE-01``)
---------------------------------------------------------
``startArV3BetaGroup`` is accepted exactly as ``startRun`` is: in the command's transaction each of the six
Runs goes ``created -> queued`` and gets its Job, and after the commit, only when the start was not a replay,
the adapter submits each Run's work to the carrier (``RunAdapter._job``). Before that task the start left six
``created`` Runs and no Job, nothing in a served process carried them, and this module carried them by hand
with ``RunAdapter.submit_existing`` (the gap this module's fact 5 pinned). The carry step is now what the
product does. One seam remains and is deliberate: the application's ``DurableCarrier`` is not started (the
serving lifespan starts it), so its ``submit`` would run the first Run on the pool at once and race every
reading taken right after the start. ``HeldCarrier`` therefore sits between the ``RunAdapter`` and that
carrier: it records what the adapter submits and forwards it, unchanged and in order, to the application's
own carrier when the module calls ``release()``; ``carrier.drain`` then waits for the Runs. The module itself
submits nothing.

Everything is measured once, in a module-scoped fixture, before the suite's ``_no_network`` autouse
fixture installs (a ``TestClient`` needs a socket pair); the tests below read what was captured.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import os
import socket
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.bootstrap import adapters as adapters_module
from auditmanager.bootstrap import composition as composition_module
from auditmanager.bootstrap.composition import build_application
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.public import PACK_MANIFEST_ENV, ReviewAttestation, seal_manifest
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
ERROR_CODES = REPOSITORY_ROOT / "contracts" / "domain" / "v1" / "error-codes.json"


# --- the probe's driver and pack helpers, loaded by path (never copied, never edited) ----------


def _load_probe() -> ModuleType:
    name = "prod11a_probe_helpers"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / "test_v3_saved_text_layer_probe.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: ``@dataclass(slots=True)`` resolves annotations through
    # ``sys.modules[cls.__module__]`` (the same reason ``conftest.py`` registers the harness).
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = _load_probe()
#: The probe's module-scoped fixture: a fresh database migrated to head by the literal migration
#: command and dropped afterwards, named ``prod11a_probe_<hex>`` (never the lane's shared database).
probe_database = probe.probe_database


# --- the scenario's constants ------------------------------------------------------------------

DEPLOYMENT_SECRET = "ar-v3-accept-recorded-suite"
REVIEW = ReviewAttestation(
    reviewer="Test Reviewer", capacity="expert", reviewed_at="2026-10-26",
    decision_ref="TEST-RULING-ACCEPT-RECORDED", scope_statement="six synthetic scopes, test only",
)
#: The beta policy's context-only items (``AR-BETA-CITATION-REVIEW-GATE-01.md``: a proposal that cites
#: one of them, alone or mixed with a provisional label, is withheld). Written out from that document,
#: not read from the code under test.
CONTEXT_ONLY = frozenset({"C05", "C06", "C08", "C09", "C10", "C15", "C21", "C22"})
#: The synthetic set's one paragraph (the probe's ``QUOTE``, replaced on this module's private copy of the
#: probe before the norms are seeded) states a required value. Every Run's recorded reply makes two
#: proposals over ``N1``, the first item of its scope: ordinal 0 is **grounded** (its required value is in the
#: norm quote and its stated value is in the PDF evidence quote, page 7 of the baseline) and ordinal 1 is
#: **ungrounded** (its stated value is not on the page), so it is rejected and a reviewer sees only a count.
NORM_QUOTE = "Минимальная ширина эвакуационных путей составляет 1,4 м."
EVIDENCE_PAGE = 7
EVIDENCE_QUOTE = "Ширина эвакуационных путей принята не менее 1,2 м"
REQUIRED_VALUE, STATED_VALUE, UNGROUNDED_VALUE = "1,4 м", "1,2 м", "9,9 м"
#: What the model said as conclusions. No answer a reviewer reads may carry any of it, in any field.
MODEL_PROSE = ("Проверить ширину прохода.", "Сверить проект и норму.", "operational", "evacuation")
probe.QUOTE = NORM_QUOTE  # this module's own copy of the probe: `_seed_norms` reads it when called


def _proposal(*, stated: str) -> dict[str, Any]:
    return {
        "category": "evacuation",
        "finding_text": MODEL_PROSE[0],
        "recommendation_text": MODEL_PROSE[1],
        "proposed_severity": MODEL_PROSE[2],
        "evidence": [{"page_number": EVIDENCE_PAGE, "quote": EVIDENCE_QUOTE}],
        "norm_citations": [{"label": "N1", "quote": NORM_QUOTE}],
        "required_value": REQUIRED_VALUE,
        "stated_value": stated,
    }


REPLY = json.dumps(
    {"observations": [_proposal(stated=STATED_VALUE), _proposal(stated=UNGROUNDED_VALUE)]},
    ensure_ascii=False,
)


# --- the wire ----------------------------------------------------------------------------------


@dataclass(slots=True)
class Exchange:
    """One request and the answer, as a reviewer's client receives it."""

    status: int
    body: bytes
    data: Any

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")


class Wire:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def call(
        self, method: str, path: str, *, token: str | None = None, key: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> Exchange:
        headers: dict[str, str] = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if key is not None:
            headers[IDEMPOTENCY_HEADER] = key
        content = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            content = json.dumps(body).encode("utf-8")
        answer = self._client.request(method, path, headers=headers, content=content)
        try:
            data = json.loads(answer.content)
        except ValueError:
            data = None
        return Exchange(answer.status_code, answer.content, data)


# --- the stock recorded composition, with only the model answer stood in -----------------------


class _GatedReplay(probe._RecordOnFirstSight):
    """The probe's replay (a reply written on first sight, then replayed by the stock adapter), with a
    barrier in front of its first call: ``entered`` is set when a Run reaches the provider and the call
    waits for ``release``. Between the two the Run is inside ``text_analysis``, after ``queued ->
    running`` was committed, so a read there must say so. No timer decides anything."""

    def __init__(self, directory: Path, output_text: str) -> None:
        super().__init__(directory, output_text)
        self.entered = threading.Event()
        self.release = threading.Event()
        self._first = True

    def complete(self, request: Any) -> Any:
        if self._first:
            self._first = False
            self.entered.set()
            assert self.release.wait(timeout=180), "the test never released the provider"
        return super().complete(request)


class _SwappedSource:
    """The stock ``EnvironmentProviders`` with only its adapter swapped; its ``call`` binding (the
    PROD-11C unmetered replay) is the composition root's own."""

    def __init__(self, source: Any, adapter: Any) -> None:
        self._source = source
        self._adapter = adapter
        self.freeze = source.freeze

    def resolve(self, session: Session, run: Any, context: Any) -> Any:
        return dataclasses.replace(self._source.resolve(session, run, context), adapter=self._adapter)


class HeldCarrier:
    """The seam between the ``RunAdapter`` and the application's own carrier, observed.

    ``submitted`` is every Run id the adapter handed to the carrier, in order, for ever (a Run id is read
    from the job: the spy tags what ``RunAdapter._job`` returns). While ``holding`` the jobs are kept, not
    run; ``release`` forwards them to the inner carrier unchanged. ``observe`` (optional) is called with the
    Run id at the moment of each ``submit``, before anything is kept: a test uses it to read, through another
    connection, what is already committed at the moment the adapter submits."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.submitted: list[str | None] = []
        self.observed: list[Any] = []
        self.observe: Callable[[str | None], Any] | None = None
        self.holding = True
        self._held: list[Callable[[], None]] = []

    def submit(self, job: Callable[[], None]) -> None:
        run_id = getattr(job, "run_id", None)
        self.submitted.append(run_id)
        if self.observe is not None:
            self.observed.append(self.observe(run_id))
        if self.holding:
            self._held.append(job)
        else:
            self.inner.submit(job)

    def release(self) -> None:
        self.holding = False
        held, self._held = self._held, []
        for job in held:
            self.inner.submit(job)

    def drain(self, timeout: float | None = None) -> bool:
        return self.inner.drain(timeout)

    def shutdown(self) -> None:
        self.inner.shutdown()


@dataclass(slots=True)
class BuiltApplication:
    client: TestClient
    wire: Wire
    application: Any
    run_adapter: Any
    replay: _GatedReplay
    held: HeldCarrier


def _build(environ: dict[str, str], recordings: Path) -> BuiltApplication:
    """``build_application`` (the composition root, unchanged) with two seams observed: the
    ``RunAdapter`` it builds is kept, and the model adapter it builds is replaced by the replay."""
    patch = pytest.MonkeyPatch()
    seen: dict[str, Any] = {}
    real_build_provider = composition_module._build_provider
    real_run_adapter = adapters_module.RunAdapter

    class RunAdapterSpy(real_run_adapter):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            seen["run_adapter"] = self
            # What the adapter submits goes through the held seam to the application's own carrier.
            self._carrier = seen["held"] = HeldCarrier(self._carrier)

        def _job(self, run_id: str) -> Any:
            job = super()._job(run_id)  # the unit of work the product submits, tagged with its Run
            job.run_id = run_id
            return job

    def build_provider(settings: Any, env: Any, *, runtime: Any = None) -> Any:
        _adapter, config, profile_id, bundle_id, source = real_build_provider(
            settings, env, runtime=runtime)
        seen["replay"] = _GatedReplay(recordings, REPLY)
        return seen["replay"], config, profile_id, bundle_id, _SwappedSource(source, seen["replay"])

    patch.setattr(composition_module, "_build_provider", build_provider)
    patch.setattr(composition_module, "RunAdapter", RunAdapterSpy)
    try:
        application = build_application(environ=environ)
    finally:
        patch.undo()
    app = create_asgi_app(environ={API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}, application=application)
    client = TestClient(app, raise_server_exceptions=False)
    return BuiltApplication(client, Wire(client), application, seen["run_adapter"], seen["replay"],
                            seen["held"])


def _environment(database_url: str, manifest: Path | None) -> dict[str, str]:
    """What a server process is started with: no provider variable (the recorded default), the
    deployment secret, this database, the lane's object store, and the pack manifest if installed."""
    env = {"DATABASE_URL": database_url, API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}
    for name in ("S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET"):
        env[name] = os.environ[name]
    if manifest is not None:
        env[PACK_MANIFEST_ENV] = str(manifest)
    return env


# --- accounts and credentials (real rows in the private database) ------------------------------


def _account(session: Session, label: str, roles: tuple[str, ...]) -> Any:
    from am_test_accounts import SUITE_NAMES, suite_login  # registered by tests/conftest.py
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository

    users, accounts = UserRepository(), AccountRepository()
    created = users.create_user(session, suite_login(label), "ar-v3-accept-password")
    accounts.complete_profile(session, user_uid=str(created.user_uid), email=None,
                              last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
    for role in roles:
        accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
    return users.find_by_login(session, suite_login(label))  # re-read: the grants raised the epoch


def _token(record: Any) -> str:
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    return signer.issue(
        Subject(user_uid=str(record.user_uid), login=record.login,
                token_epoch=record.token_epoch, display_label=record.display_label),
        is_default_credential=False,
    ).token


# --- the measurement ---------------------------------------------------------------------------

PROFILE_SNAPSHOT = resolve_beta_v3_profile(probe.PROFILE_ID, probe.BUNDLE_ID).snapshot_id
GROUPS = "/ar-v3-beta/groups"
PACK = "/ar-v3-beta/pack"


@dataclass(slots=True)
class Measurement:
    #: Every captured exchange, by step name.
    x: dict[str, Exchange] = field(default_factory=dict)
    #: Database readings, by name.
    db: dict[str, Any] = field(default_factory=dict)
    pack: Any = None
    version_uid: str = ""
    other_version_uid: str = ""
    provider_requests: int = 0
    peers: list[str] = field(default_factory=list)


def _rows(factory: sessionmaker[Session], sql: str, **params: Any) -> list[tuple[Any, ...]]:
    with factory() as session:
        return [tuple(row) for row in session.execute(text(sql), params).all()]


def _runs_of_group(factory: sessionmaker[Session], group_id: str) -> list[tuple[str, str]]:
    return [(str(scope), str(state)) for scope, state in _rows(factory, """
        SELECT m.scope_id, r.state FROM ar_v3_run_group_member m
          JOIN audit_run r ON r.run_id = m.run_id WHERE m.group_id = :g ORDER BY m.ordinal
    """, g=group_id)]


def _jobs_of_group(factory: sessionmaker[Session], group_id: str) -> list[tuple[str, str]]:
    return [(str(scope), str(state)) for scope, state in _rows(factory, """
        SELECT m.scope_id, j.state FROM ar_v3_run_group_member m
          JOIN job j ON j.run_id = m.run_id WHERE m.group_id = :g ORDER BY m.ordinal
    """, g=group_id)]


def _counts(factory: sessionmaker[Session], version_uid: str) -> dict[str, int]:
    return {
        "groups": _rows(factory, "SELECT count(*) FROM ar_v3_run_group WHERE version_uid = :v",
                        v=version_uid)[0][0],
        "runs": _rows(factory, "SELECT count(*) FROM audit_run WHERE version_uid = :v",
                      v=version_uid)[0][0],
        "jobs": _rows(factory, "SELECT count(*) FROM job j JOIN audit_run r ON r.run_id = j.run_id "
                               "WHERE r.version_uid = :v", v=version_uid)[0][0],
    }


def _drive(probe_database_url: str, blob_store: Any, recordings: Path, manifest_dir: Path) -> Measurement:
    out = Measurement()
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(probe_database_url)))
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    patch = pytest.MonkeyPatch()
    real_connect = socket.socket.connect

    def spy(self: socket.socket, address: Any, *args: Any, **kwargs: Any) -> Any:
        out.peers.append(str(address[0]) if isinstance(address, tuple) else str(address))
        return real_connect(self, address, *args, **kwargs)

    patch.setattr(socket.socket, "connect", spy)
    built: list[BuiltApplication] = []
    try:
        with factory() as session, session.begin():
            probe._require_probe_database(session.execute(text("SELECT current_database()")).scalar_one())
            expert = _account(session, "accept-expert", ("expert",))
            admin = _account(session, "accept-admin", ("admin",))
            suspended = _account(session, "accept-suspended", ())
            served = probe._publish_source(session, blob_store, title="AR v3 over HTTP",
                                           register_blob=True, actor=str(expert.user_uid))
            other = probe._publish_source(session, blob_store, title="AR v3 over HTTP, another",
                                          register_blob=False, actor=str(expert.user_uid))
            pack = probe._seed_norms(session, blob_store, served, str(expert.user_uid))
        tokens = {"expert": _token(expert), "admin": _token(admin), "suspended": _token(suspended)}
        out.pack, out.version_uid, out.other_version_uid = pack, served.version_uid, other.version_uid

        manifest = manifest_dir / "ar-v3-pack.json"
        manifest.write_bytes(seal_manifest(pack, REVIEW))
        url = probe_database_url
        installed = _build(_environment(url, manifest), recordings)
        empty = _build(_environment(url, None), recordings)
        built += [installed, empty]
        wire, bare = installed.wire, empty.wire
        body = {"version_uid": served.version_uid}

        x = out.x
        x["pack"] = wire.call("GET", PACK, token=tokens["expert"])
        x["pack_admin"] = wire.call("GET", PACK, token=tokens["admin"])
        x["pack_empty"] = bare.call("GET", PACK, token=tokens["expert"])
        x["start_empty_registry"] = bare.call("POST", GROUPS, token=tokens["expert"], key="accept-empty", body=body)
        x["start_admin"] = wire.call("POST", GROUPS, token=tokens["admin"], key="accept-admin", body=body)
        x["start_suspended"] = wire.call("POST", GROUPS, token=tokens["suspended"], key="accept-suspended", body=body)
        x["start_anonymous"] = wire.call("POST", GROUPS, key="accept-anonymous", body=body)
        x["start_with_authority"] = wire.call(
            "POST", GROUPS, token=tokens["expert"], key="accept-authority",
            body={**body, "pack_sha256": "a" * 64, "scopes": ["F1"]})
        out.db["after_refusals"] = _counts(factory, served.version_uid)
        out.db["submitted_after_refusals"] = installed.held.submitted + empty.held.submitted

        x["start"] = wire.call("POST", GROUPS, token=tokens["expert"], key="accept-start", body=body)
        group = x["start"].data
        gid = group["group_id"]
        out.db["after_start"] = _counts(factory, served.version_uid)
        out.db["states_after_start"] = _runs_of_group(factory, gid)
        out.db["job_states_after_start"] = _jobs_of_group(factory, gid)
        out.db["submitted_after_start"] = list(installed.held.submitted)
        with factory() as session:
            out.db["next_queued_run_after_start"] = JobRepository().next_queued_run(session)
        x["group_before"] = wire.call("GET", f"{GROUPS}/{gid}", token=tokens["expert"])
        x["review_before"] = wire.call("GET", f"{GROUPS}/{gid}/review", token=tokens["expert"])
        x["start_again"] = wire.call("POST", GROUPS, token=tokens["expert"], key="accept-start", body=body)
        x["start_reused_key"] = wire.call("POST", GROUPS, token=tokens["expert"], key="accept-start",
                                          body={"version_uid": other.version_uid})
        out.db["after_replay"] = _counts(factory, served.version_uid)
        out.db["other_after_replay"] = _counts(factory, other.version_uid)
        out.db["submitted_after_replay"] = list(installed.held.submitted)
        out.db["job_states_after_replay"] = _jobs_of_group(factory, gid)

        # The product has already queued the Runs and submitted them; the held seam forwards exactly what
        # the adapter submitted to the application's own carrier. Read while the first is at the provider.
        app = installed
        try:
            app.held.release()
            assert app.replay.entered.wait(timeout=180), "no Run reached the provider"
            x["group_midway"] = wire.call("GET", f"{GROUPS}/{gid}", token=tokens["expert"])
            x["review_midway"] = wire.call("GET", f"{GROUPS}/{gid}/review", token=tokens["expert"])
            out.db["states_midway"] = _runs_of_group(factory, gid)
            out.db["job_states_midway"] = _jobs_of_group(factory, gid)
        finally:
            app.replay.release.set()
        assert app.application.carrier.drain(timeout=300), "the six Runs never finished"
        out.provider_requests = len(app.replay.requests)

        x["group_after"] = wire.call("GET", f"{GROUPS}/{gid}", token=tokens["expert"])
        x["review_after"] = wire.call("GET", f"{GROUPS}/{gid}/review", token=tokens["expert"])
        x["review_after_again"] = wire.call("GET", f"{GROUPS}/{gid}/review", token=tokens["admin"])
        x["start_after"] = wire.call("POST", GROUPS, token=tokens["expert"], key="accept-start", body=body)
        x["pack_after"] = wire.call("GET", PACK, token=tokens["expert"])
        out.db["after_carry"] = _counts(factory, served.version_uid)
        out.db["states_after"] = _runs_of_group(factory, gid)
        out.db["job_states_after"] = _jobs_of_group(factory, gid)
        out.db["submitted_after_all"] = list(app.held.submitted)
        out.db["model_calls"] = _rows(factory, """
            SELECT m.scope_id, c.provider_mode, c.cost_basis, c.cost_micros, c.status
              FROM ar_v3_run_group_member m JOIN model_call c ON c.run_id = m.run_id
             WHERE m.group_id = :g ORDER BY m.ordinal, c.model_call_id
        """, g=gid)
        out.db["norm_ids"] = _rows(factory, """
            SELECT d.norm_document_id, p.norm_paragraph_id FROM norm_paragraph p
              JOIN norm_document d ON d.norm_document_pk = p.norm_document_pk
             WHERE p.norms_snapshot_id = :s
        """, s=PROFILE_SNAPSHOT)
        out.db["run_modes"] = _rows(factory, """
            SELECT DISTINCT r.provider_mode FROM ar_v3_run_group_member m
              JOIN audit_run r ON r.run_id = m.run_id WHERE m.group_id = :g
        """, g=gid)
    finally:
        for item in built:
            item.replay.release.set()
            item.application.carrier.shutdown()
            item.application.session_factory.kw["bind"].dispose()
        patch.undo()
        engine.dispose()
    return out


@pytest.fixture(scope="module")
def measured(probe_database: str, blob_store: Any, tmp_path_factory: pytest.TempPathFactory) -> Measurement:
    result = _drive(probe_database, blob_store, tmp_path_factory.mktemp("accept-recordings"),
                    tmp_path_factory.mktemp("accept-pack"))
    print("ACCEPT-MEASUREMENT " + json.dumps(
        {"x": {k: [v.status, v.data] for k, v in result.x.items()}, "db": result.db,
         "requests": result.provider_requests}, ensure_ascii=False, default=str, sort_keys=True))
    return result


# --- what the contract and the policy say, written out here (never read from the code under test) ----

CONTRACT = json.loads(OPENAPI.read_text(encoding="utf-8"))
SCHEMAS: dict[str, Any] = CONTRACT["components"]["schemas"]
ERROR_SPEC: dict[str, Any] = json.loads(ERROR_CODES.read_text(encoding="utf-8"))["codes"]
SCOPE_LABELS = ("F1", "F2", "A1", "A2", "S1", "S2")
#: The fixed C01-C22 partition (``AR-NORM-MAP-APPROVAL-PREP-01.md``), in the order a scope lists its items.
SCOPE_ITEMS = {
    "F1": ("C01", "C02", "C03"),
    "F2": ("C04", "C05", "C06", "C07", "C08", "C09", "C10"),
    "A1": ("C11", "C12", "C13", "C14"),
    "A2": ("C15", "C16", "C17", "C18", "C19", "C20"),
    "S1": ("C21",),
    "S2": ("C22",),
}
REVIEW_LABEL = "requires_expert_review"  # the wire value of the beta policy's «требует проверки эксперта»
#: Names that would make an answer a conclusion: the model's own fields and the words for a verdict.
FORBIDDEN_KEYS = frozenset({
    "required_value", "stated_value", "proposed_severity", "severity", "finding_text",
    "recommendation_text", "category", "verdict", "conclusion", "numeric_conclusion",
    "numeric_value", "value", "violation", "compliant", "compliance",
})
WIRE_SCHEMAS = ("ArV3BetaGroup", "ArV3BetaGroupMember", "ArV3BetaGroupReview", "ArV3BetaGroupReviewMember",
                "ArV3BetaVisibleReview", "ArV3BetaVisibleTopic", "ArV3BetaVisibleProposal",
                "ArV3BetaVisibleEvidence", "ArV3BetaVisibleCitation", "ArV3BetaPackStatus",
                "ArV3BetaPackReview")
ALLOWED_KEYS = frozenset(key for name in WIRE_SCHEMAS for key in SCHEMAS[name]["properties"])
#: The operation each captured exchange answers, for "the status is one the contract declares".
OPERATION_OF = {
    "pack": ("get", "/ar-v3-beta/pack"), "pack_admin": ("get", "/ar-v3-beta/pack"),
    "pack_empty": ("get", "/ar-v3-beta/pack"), "pack_after": ("get", "/ar-v3-beta/pack"),
    "start_empty_registry": ("post", "/ar-v3-beta/groups"), "start_admin": ("post", "/ar-v3-beta/groups"),
    "start_suspended": ("post", "/ar-v3-beta/groups"), "start_anonymous": ("post", "/ar-v3-beta/groups"),
    "start_with_authority": ("post", "/ar-v3-beta/groups"), "start": ("post", "/ar-v3-beta/groups"),
    "start_again": ("post", "/ar-v3-beta/groups"), "start_reused_key": ("post", "/ar-v3-beta/groups"),
    "start_after": ("post", "/ar-v3-beta/groups"),
    "group_before": ("get", "/ar-v3-beta/groups/{group_id}"),
    "group_midway": ("get", "/ar-v3-beta/groups/{group_id}"),
    "group_after": ("get", "/ar-v3-beta/groups/{group_id}"),
    "review_before": ("get", "/ar-v3-beta/groups/{group_id}/review"),
    "review_midway": ("get", "/ar-v3-beta/groups/{group_id}/review"),
    "review_after": ("get", "/ar-v3-beta/groups/{group_id}/review"),
    "review_after_again": ("get", "/ar-v3-beta/groups/{group_id}/review"),
}
PROFILE = resolve_beta_v3_profile(probe.PROFILE_ID, probe.BUNDLE_ID)


# --- the checks: each is a pure function of an answer and raises AssertionError ------------------------
# They are separate from the tests so that ``test_every_check_can_fail`` can feed each one a mutated copy.


def check_closed_keys(node: Any, schema: str, path: str = "") -> None:
    """Exactly the properties the contract declares for this schema, at every level of the answer."""
    assert isinstance(node, dict), f"{path or schema}: not an object"
    assert set(node) == set(SCHEMAS[schema]["properties"]), (
        f"{path or schema}: keys {sorted(node)} are not the contract's {sorted(SCHEMAS[schema]['properties'])}")


def check_group_keys(group: dict[str, Any]) -> None:
    check_closed_keys(group, "ArV3BetaGroup")
    assert len(group["members"]) == 6
    for member in group["members"]:
        check_closed_keys(member, "ArV3BetaGroupMember", "member")


def check_review_keys(review: dict[str, Any]) -> None:
    check_closed_keys(review, "ArV3BetaGroupReview")
    assert len(review["members"]) == 6
    for member in review["members"]:
        check_closed_keys(member, "ArV3BetaGroupReviewMember", "member")
        body = member["review"]
        if body is None:
            continue
        check_closed_keys(body, "ArV3BetaVisibleReview", "review")
        for topic in body["topics"]:
            check_closed_keys(topic, "ArV3BetaVisibleTopic", "topic")
        for proposal in body["provisional_citations"]:
            check_closed_keys(proposal, "ArV3BetaVisibleProposal", "proposal")
            for evidence in proposal["evidence"]:
                check_closed_keys(evidence, "ArV3BetaVisibleEvidence", "evidence")
            for citation in proposal["citations"]:
                check_closed_keys(citation, "ArV3BetaVisibleCitation", "citation")


def check_scope_labels(answer: dict[str, Any]) -> None:
    """Six scope outcomes with the right labels, in the contract's order, once each."""
    assert [member["scope_id"] for member in answer["members"]] == list(SCOPE_LABELS)


def check_group_binds_the_server_pack(group: dict[str, Any], m: Measurement) -> None:
    """The request named a version and nothing else; everything else the group says is the server's:
    the sealed pack's digest and, per scope, the map and the verified set it installed."""
    assert group["version_uid"] == m.version_uid
    assert group["provider_mode"] == "recorded"
    assert group["pack_sha256"] == m.pack.sha256
    assert group["analysis_profile_id"] == str(PROFILE.analysis_profile_id)
    assert group["prompt_bundle_id"] == str(PROFILE.prompt_bundle_id)
    assert group["norms_snapshot_id"] == PROFILE.snapshot_id
    assert [(x["scope_id"], x["map_sha256"], x["norm_retrieval_set_id"]) for x in group["members"]] == [
        (scope.scope_id, scope.identity.map_sha256, scope.set_id) for scope in m.pack.scopes]
    assert len({x["run_id"] for x in group["members"]}) == 6


def check_group_states(group: dict[str, Any], expected: list[str]) -> None:
    assert [member["state"] for member in group["members"]] == expected


def check_pending(review: dict[str, Any], expected_run_states: list[str]) -> None:
    """The review read before the Runs finish says so: pending, with nothing to show."""
    assert [member["run_state"] for member in review["members"]] == expected_run_states
    for member in review["members"]:
        assert member["review_state"] == "pending"
        assert member["review"] is None
        assert member["terminal_reason"] is None and member["refusal_code"] is None


def check_review_agrees_with_group(review: dict[str, Any], group: dict[str, Any]) -> None:
    assert review["group_id"] == group["group_id"]
    assert review["version_uid"] == group["version_uid"]
    assert [(r["scope_id"], r["run_id"], r["run_state"]) for r in review["members"]] == [
        (g["scope_id"], g["run_id"], g["state"]) for g in group["members"]]


def check_review_is_provisional(review: dict[str, Any]) -> None:
    """The beta policy, as invariants of any available review: every topic carries the expert-review
    label; a citation names only a provisional-citation topic; a context-only topic is never cited; each
    topic's count is the number of citations that name it."""
    for member in review["members"]:
        body = member["review"]
        assert body is not None, member["scope_id"]
        modes = {topic["item_id"]: topic["mode"] for topic in body["topics"]}
        cited: dict[str, int] = {}
        for proposal in body["provisional_citations"]:
            for citation in proposal["citations"]:
                assert citation["item_id"] in modes, f"{citation['item_id']} is not an item of {member['scope_id']}"
                assert modes[citation["item_id"]] == "provisional_citation", citation["item_id"]
                cited[citation["item_id"]] = cited.get(citation["item_id"], 0) + 1
        for topic in body["topics"]:
            assert topic["review_status"] == REVIEW_LABEL, topic["item_id"]
            assert topic["mode"] in {"provisional_citation", "context_only"}
            assert topic["provisional_citation_count"] == cited.get(topic["item_id"], 0)
            if topic["mode"] == "context_only":
                assert topic["provisional_citation_count"] == 0


def check_review_content(review: dict[str, Any], norm_ids: list[tuple[str, str]]) -> None:
    """What the recorded reply must have become in each scope (policy and reply written out above):
    the scope's own items in order; the policy's modes; the grounded proposal over ``N1`` a provisional
    citation where the scope's first item is a provisional-citation topic and a withheld proposal where
    it is context-only; the ungrounded proposal a rejected count and nothing else. The citation points at
    the one paragraph the pack's sets were built from (``norm_ids``, read from the database)."""
    assert len(norm_ids) == 1
    for member in review["members"]:
        scope, body = member["scope_id"], member["review"]
        assert member["review_state"] == "available" and member["run_state"] == "published"
        assert member["terminal_reason"] is None and member["refusal_code"] is None
        assert [t["item_id"] for t in body["topics"]] == list(SCOPE_ITEMS[scope])
        assert {t["item_id"]: t["mode"] for t in body["topics"]} == {
            item: ("context_only" if item in CONTEXT_ONLY else "provisional_citation")
            for item in SCOPE_ITEMS[scope]}
        first = SCOPE_ITEMS[scope][0]
        assert body["rejected_proposal_count"] == 1, scope
        if first in CONTEXT_ONLY:
            assert body["provisional_citations"] == [] and body["withheld_proposal_count"] == 1, scope
        else:
            assert body["withheld_proposal_count"] == 0, scope
            assert body["provisional_citations"] == [{
                "proposal_ordinal": 0,
                "evidence": [{"page_number": EVIDENCE_PAGE, "quote": EVIDENCE_QUOTE}],
                "citations": [{
                    "item_id": first, "label": "N1", "raw_quote": NORM_QUOTE, "state": "verified",
                    "document_id": norm_ids[0][0], "paragraph_id": norm_ids[0][1],
                }],
            }], scope


def _leaves(node: Any, key: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(node, dict):
        for name, value in node.items():
            yield from _leaves(value, name)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value, key)
    else:
        yield key, node


def check_no_numeric_conclusion(exchanges: list[Exchange]) -> None:
    """Nothing a reviewer reads is a conclusion, let alone a numeric one. The model said a required
    value, a stated value, a severity and two sentences; none of those fields exists in any answer, no
    answer carries a key outside the contract's, no answer carries a number that is not a count or an
    ordinal, and the numbers of the reply appear only inside the two verbatim quote fields."""
    for exchange in exchanges:
        for key, value in _leaves(exchange.data):
            assert key in ALLOWED_KEYS, f"unexpected field {key!r}"
            assert key not in FORBIDDEN_KEYS, key
            assert not isinstance(value, float), (key, value)
            if isinstance(value, str) and any(claim in value for claim in (REQUIRED_VALUE, STATED_VALUE)):
                assert key in {"quote", "raw_quote"}, (key, value)
        for prose in MODEL_PROSE:
            assert prose not in exchange.text, prose
        assert UNGROUNDED_VALUE not in exchange.text


def check_typed_refusal(exchange: Exchange, code: str, details: dict[str, Any] | None) -> None:
    """The failure is the contract's envelope, with the status and retryability the catalogue pins."""
    spec = ERROR_SPEC[code]
    assert exchange.status == spec["http"]
    assert set(exchange.data) <= set(SCHEMAS["ErrorEnvelope"]["properties"])
    assert exchange.data["error_code"] == code
    assert exchange.data["retryable"] is spec["retryable"]
    assert exchange.data["contract_version"] == CONTRACT["info"]["version"]
    assert exchange.data.get("details") == details


def check_same_group(first: dict[str, Any], again: dict[str, Any]) -> None:
    assert again["group_id"] == first["group_id"]
    assert [(x["scope_id"], x["run_id"], x["map_sha256"], x["norm_retrieval_set_id"]) for x in again["members"]] == [
        (x["scope_id"], x["run_id"], x["map_sha256"], x["norm_retrieval_set_id"]) for x in first["members"]]
    assert {key: value for key, value in again.items() if key != "members"} == {
        key: value for key, value in first.items() if key != "members"}


def check_nothing_created(counts: dict[str, int]) -> None:
    assert counts == {"groups": 0, "runs": 0, "jobs": 0}


def check_one_group_of_six(counts: dict[str, int], jobs: int) -> None:
    assert counts == {"groups": 1, "runs": 6, "jobs": jobs}


def check_accepted_like_start_run(db: dict[str, Any], group: dict[str, Any]) -> None:
    """What ``startRun`` leaves, six times: right after the 202 every Run is ``queued`` with a ``queued``
    Job (committed with the group), the poller's own query finds the first of them, and the adapter has
    submitted exactly the group's Runs to the carrier, once each, in scope order."""
    run_ids = [member["run_id"] for member in group["members"]]
    assert db["after_start"] == {"groups": 1, "runs": 6, "jobs": 6}
    assert db["states_after_start"] == [(scope, "queued") for scope in SCOPE_LABELS]
    assert db["job_states_after_start"] == [(scope, "queued") for scope in SCOPE_LABELS]
    assert db["next_queued_run_after_start"] == run_ids[0]
    assert db["submitted_after_start"] == run_ids


def check_a_replay_adds_nothing(db: dict[str, Any]) -> None:
    """The second request with the same key and body creates no Run and no Job, queues nothing again and
    submits nothing to the carrier."""
    assert db["after_replay"] == {"groups": 1, "runs": 6, "jobs": 6}
    assert db["job_states_after_replay"] == db["job_states_after_start"]
    assert db["submitted_after_replay"] == db["submitted_after_start"]


def check_a_refusal_submits_nothing(db: dict[str, Any]) -> None:
    assert db["submitted_after_refusals"] == []


# --- the facts -----------------------------------------------------------------------------------

def _ex(m: Measurement, name: str) -> Exchange:
    return m.x[name]


def test_the_contract_names_what_this_module_assumes() -> None:
    """The literals above are the contract's: the scope labels in order, and the policy sets only
    items the partition lists."""
    assert tuple(SCHEMAS["ArV3BetaGroupMember"]["properties"]["scope_id"]["enum"]) == SCOPE_LABELS
    assert tuple(SCHEMAS["ArV3BetaGroupReviewMember"]["properties"]["scope_id"]["enum"]) == SCOPE_LABELS
    assert tuple(SCHEMAS["ArV3BetaPackStatus"]["properties"]["scope_ids"]["items"]["enum"]) == SCOPE_LABELS
    assert [item for scope in SCOPE_LABELS for item in SCOPE_ITEMS[scope]] == [
        f"C{number:02d}" for number in range(1, 23)]
    assert CONTEXT_ONLY < {item for items in SCOPE_ITEMS.values() for item in items}
    assert not FORBIDDEN_KEYS & ALLOWED_KEYS, "the contract itself declares a conclusion-shaped property"


def test_every_status_observed_is_one_the_contract_declares_for_that_operation(measured: Measurement) -> None:
    for name, (method, path) in OPERATION_OF.items():
        declared = CONTRACT["paths"][path][method]["responses"]
        assert str(_ex(measured, name).status) in declared, (name, _ex(measured, name).status, sorted(declared))


def test_the_pack_status_is_the_sealed_synthetic_pack_the_composition_root_installed(
    measured: Measurement,
) -> None:
    for name in ("pack", "pack_admin", "pack_after"):
        answer = _ex(measured, name)
        assert answer.status == 200
        check_closed_keys(answer.data, "ArV3BetaPackStatus")
        check_closed_keys(answer.data["review"], "ArV3BetaPackReview")
        assert answer.data == {
            "state": "installed",
            "analysis_profile_id": str(PROFILE.analysis_profile_id),
            "prompt_bundle_id": str(PROFILE.prompt_bundle_id),
            "pack_sha256": measured.pack.sha256,
            "scope_ids": list(SCOPE_LABELS),
            "review": {
                "reviewer": REVIEW.reviewer, "capacity": REVIEW.capacity, "reviewed_at": REVIEW.reviewed_at,
                "decision_ref": REVIEW.decision_ref, "scope_statement": REVIEW.scope_statement,
            },
        }


def test_without_a_manifest_the_pack_status_says_not_installed(measured: Measurement) -> None:
    answer = _ex(measured, "pack_empty")
    assert (answer.status, answer.data) == (200, {"state": "not_installed"})


def test_a_start_with_an_empty_registry_is_refused_with_the_typed_error_and_creates_nothing(
    measured: Measurement,
) -> None:
    check_typed_refusal(_ex(measured, "start_empty_registry"), "dependency_unavailable",
                        {"dependency": "ar_v3_trusted_pack"})
    check_nothing_created(measured.db["after_refusals"])


@pytest.mark.parametrize("who", ("admin", "suspended"))
def test_a_start_by_a_non_expert_is_refused_and_creates_nothing(measured: Measurement, who: str) -> None:
    """An administrator may read the pack and the group but not start one; an account with no role is
    suspended from product data. Both are refused for the role, not for the credential."""
    check_typed_refusal(_ex(measured, f"start_{who}"), "permission_denied",
                        {"required_capability": "role:expert"})
    check_nothing_created(measured.db["after_refusals"])


def test_an_anonymous_start_is_refused_and_creates_nothing(measured: Measurement) -> None:
    check_typed_refusal(_ex(measured, "start_anonymous"), "authentication_required", None)
    check_nothing_created(measured.db["after_refusals"])


def test_a_request_that_names_a_pack_or_a_scope_is_refused_and_creates_nothing(
    measured: Measurement,
) -> None:
    """The request carries a version and nothing else: authority over sets is the server's."""
    check_typed_refusal(_ex(measured, "start_with_authority"), "validation_failed",
                        {"constraint": "additionalProperties", "field": "body"})
    check_nothing_created(measured.db["after_refusals"])


def test_the_start_creates_the_group_of_six_with_the_right_scope_labels(measured: Measurement) -> None:
    start = _ex(measured, "start")
    assert start.status == 202
    check_group_keys(start.data)
    check_scope_labels(start.data)
    check_group_binds_the_server_pack(start.data, measured)
    check_group_states(start.data, ["queued"] * 6)
    check_one_group_of_six(measured.db["after_start"], jobs=6)
    assert measured.db["states_after_start"] == [(scope, "queued") for scope in SCOPE_LABELS]


def test_the_group_read_after_the_start_is_the_group_the_start_answered(measured: Measurement) -> None:
    before = _ex(measured, "group_before")
    assert before.status == 200
    check_group_keys(before.data)
    check_same_group(_ex(measured, "start").data, before.data)
    check_group_states(before.data, ["queued"] * 6)


def test_the_http_start_queues_the_six_runs_and_hands_them_to_the_carrier_like_start_run(
    measured: Measurement,
) -> None:
    """Fact 5, flipped by ``PROD-11D-V3-GROUP-QUEUE-01``. It pinned a GAP (six ``created`` Runs, no Job,
    ``next_queued_run`` answering ``None``, so in a served process nothing carried the group). It now pins
    what ``startRun`` leaves, six times: ``queued`` Runs, ``queued`` Jobs, the poller's query finding the
    first Run, and one carrier submission per Run in scope order. The carry step that used to stand here
    (``RunAdapter.submit_existing``) is gone: the module submits nothing."""
    check_accepted_like_start_run(measured.db, _ex(measured, "start").data)
    check_a_refusal_submits_nothing(measured.db)


def test_the_review_read_before_the_runs_finish_says_pending(measured: Measurement) -> None:
    before = _ex(measured, "review_before")
    assert before.status == 200
    check_review_keys(before.data)
    check_scope_labels(before.data)
    check_pending(before.data, ["queued"] * 6)
    check_review_agrees_with_group(before.data, _ex(measured, "group_before").data)


def test_a_read_while_the_first_run_is_at_the_provider_says_one_running_and_five_pending(
    measured: Measurement,
) -> None:
    group, review = _ex(measured, "group_midway"), _ex(measured, "review_midway")
    expected = ["running"] + ["queued"] * 5
    assert (group.status, review.status) == (200, 200)
    check_group_keys(group.data)
    check_review_keys(review.data)
    check_group_states(group.data, expected)
    check_pending(review.data, expected)
    check_review_agrees_with_group(review.data, group.data)
    assert measured.db["states_midway"] == list(zip(SCOPE_LABELS, expected))
    # One slot, serially (R-146j): the first Run's Job is claimed, the other five still wait in the queue.
    first, rest = measured.db["job_states_midway"][0], measured.db["job_states_midway"][1:]
    assert first[0] == "F1" and first[1] in {"leased", "running"}, first
    assert rest == [(scope, "queued") for scope in SCOPE_LABELS[1:]]


def test_a_second_identical_start_is_the_same_group_and_creates_no_run(measured: Measurement) -> None:
    again = _ex(measured, "start_again")
    assert again.status == 202
    check_group_keys(again.data)
    check_same_group(_ex(measured, "start").data, again.data)
    check_group_states(again.data, ["queued"] * 6)
    check_a_replay_adds_nothing(measured.db)


def test_the_same_key_with_another_version_is_a_conflict_and_creates_nothing(measured: Measurement) -> None:
    check_typed_refusal(_ex(measured, "start_reused_key"), "idempotency_key_reuse",
                        {"command_type": "start_ar_v3_beta_group"})
    check_nothing_created(measured.db["other_after_replay"])
    check_one_group_of_six(measured.db["after_replay"], jobs=6)


def test_the_six_runs_reach_published_through_the_applications_own_carrier(measured: Measurement) -> None:
    after = _ex(measured, "group_after")
    assert after.status == 200
    check_group_keys(after.data)
    check_scope_labels(after.data)
    check_group_binds_the_server_pack(after.data, measured)
    check_same_group(_ex(measured, "start").data, after.data)
    check_group_states(after.data, ["published"] * 6)
    assert measured.db["states_after"] == [(scope, "published") for scope in SCOPE_LABELS]
    # The Jobs the start enqueued are the ones the carrier ran: all six succeeded, none was added.
    assert measured.db["job_states_after"] == [(scope, "succeeded") for scope in SCOPE_LABELS]
    assert measured.provider_requests == 6
    assert measured.db["run_modes"] == [("recorded",)]
    assert measured.db["model_calls"] == [(scope, "recorded", "unmetered", 0, "succeeded") for scope in SCOPE_LABELS]


def test_after_they_finish_the_review_has_six_available_outcomes_that_agree_with_the_group(
    measured: Measurement,
) -> None:
    for name in ("review_after", "review_after_again"):
        review = _ex(measured, name)
        assert review.status == 200
        check_review_keys(review.data)
        check_scope_labels(review.data)
        check_review_agrees_with_group(review.data, _ex(measured, "group_after").data)
        check_review_content(review.data, measured.db["norm_ids"])
    assert _ex(measured, "review_after").data == _ex(measured, "review_after_again").data


def test_every_topic_and_citation_is_provisional_and_labelled_for_expert_review(measured: Measurement) -> None:
    check_review_is_provisional(_ex(measured, "review_after").data)


def test_no_answer_carries_a_numerical_conclusion(measured: Measurement) -> None:
    answers = [exchange for name, exchange in measured.x.items()
               if exchange.status < 300 and exchange.data is not None]
    assert len(answers) == 14  # pack x4, start x3, group x3, review x4: the set cannot shrink silently
    check_no_numeric_conclusion(answers)


def test_a_start_after_the_runs_finished_is_still_the_same_group_with_no_new_work(
    measured: Measurement,
) -> None:
    after = _ex(measured, "start_after")
    assert after.status == 202
    check_group_keys(after.data)
    check_same_group(_ex(measured, "start").data, after.data)
    check_group_states(after.data, ["published"] * 6)
    check_one_group_of_six(measured.db["after_carry"], jobs=6)  # the six the start enqueued, no seventh
    assert measured.db["submitted_after_all"] == measured.db["submitted_after_start"]  # nothing submitted again
    assert measured.provider_requests == 6


def test_the_acceptance_stayed_on_the_loopback(measured: Measurement) -> None:
    probe._require_loopback(measured.peers)


# --- the checks can fail -----------------------------------------------------------------------------
# Each assertion above lives in a pure check. For every check, one fact of the real answer is flipped
# on a deep copy and the check must refuse it; the unmutated answer passes it. (The report lists the
# product-source mutations that were applied to the committed tree as well.)


def _with(data: Any, edit: Callable[[Any], None]) -> Any:
    clone = copy.deepcopy(data)
    edit(clone)
    return clone


def _as_exchange(data: Any, status: int = 200) -> Exchange:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Exchange(status, body, data)


def _first_available(review: dict[str, Any]) -> dict[str, Any]:
    return next(member for member in review["members"] if member["review"]["provisional_citations"])


def _inject_into_proposal(key: str, value: Any) -> Callable[[Any], None]:
    def edit(review: Any) -> None:
        _first_available(review)["review"]["provisional_citations"][0][key] = value
    return edit


def _case(name: str, check: Callable[..., None], args: Callable[[Measurement], tuple[Any, ...]],
          mutate: Callable[[tuple[Any, ...]], tuple[Any, ...]]) -> Any:
    return pytest.param(check, args, mutate, id=name)


def _first(edit: Callable[[Any], None]) -> Callable[[tuple[Any, ...]], tuple[Any, ...]]:
    return lambda args: (_with(args[0], edit), *args[1:])


def _swap_first_two_members(group: Any) -> None:
    group["members"][0], group["members"][1] = group["members"][1], group["members"][0]


CHECK_CASES = [
    _case("scope labels in another order", check_scope_labels,
          lambda m: (_ex(m, "start").data,), _first(_swap_first_two_members)),
    _case("a scope label that is not one of the six", check_scope_labels,
          lambda m: (_ex(m, "review_after").data,), _first(lambda d: d["members"][5].update(scope_id="S3"))),
    _case("a group member with an extra property", check_group_keys,
          lambda m: (_ex(m, "start").data,), _first(lambda d: d["members"][0].update(severity="high"))),
    _case("a group without its pack digest", check_group_keys,
          lambda m: (_ex(m, "start").data,), _first(lambda d: d.pop("pack_sha256"))),
    _case("a member bound to another map", check_group_binds_the_server_pack,
          lambda m: (_ex(m, "start").data, m), lambda a: (_with(a[0], lambda d: d["members"][2].update(map_sha256="0" * 64)), a[1])),
    _case("a group pinned to another pack", check_group_binds_the_server_pack,
          lambda m: (_ex(m, "start").data, m), lambda a: (_with(a[0], lambda d: d.update(pack_sha256="0" * 64)), a[1])),
    _case("a published group with one failed Run", lambda d: check_group_states(d, ["published"] * 6),
          lambda m: (_ex(m, "group_after").data,), _first(lambda d: d["members"][3].update(state="failed"))),
    _case("a pending review that shows a review", check_pending,
          lambda m: (_ex(m, "review_before").data, ["queued"] * 6),
          _first(lambda d: d["members"][0].update(review_state="available", review={}))),
    _case("a pending review that is not pending", check_pending,
          lambda m: (_ex(m, "review_midway").data, ["running"] + ["queued"] * 5),
          _first(lambda d: d["members"][0].update(review_state="failed"))),
    _case("a review that disagrees with its group about a Run", check_review_agrees_with_group,
          lambda m: (_ex(m, "review_after").data, _ex(m, "group_after").data),
          _first(lambda d: d["members"][4].update(run_id="run_00000000000000000000000000"))),
    _case("a review of another group", check_review_agrees_with_group,
          lambda m: (_ex(m, "review_after").data, _ex(m, "group_after").data),
          _first(lambda d: d.update(group_id="arg_00000000000000000000000000"))),
    _case("a review proposal with an injected numeric field", check_review_keys,
          lambda m: (_ex(m, "review_after").data,), _first(_inject_into_proposal("required_value", "1,4 м"))),
    _case("a topic without the expert-review label", check_review_is_provisional,
          lambda m: (_ex(m, "review_after").data,),
          _first(lambda d: d["members"][0]["review"]["topics"][0].update(review_status="reviewed"))),
    _case("a context-only item that is cited", check_review_is_provisional,
          lambda m: (_ex(m, "review_after").data,),
          _first(lambda d: d["members"][1]["review"]["provisional_citations"][0]["citations"][0].update(item_id="C05"))),
    _case("a citation of an item outside its scope", check_review_is_provisional,
          lambda m: (_ex(m, "review_after").data,),
          _first(lambda d: d["members"][0]["review"]["provisional_citations"][0]["citations"][0].update(item_id="C22"))),
    _case("a topic count that is not its citations", check_review_is_provisional,
          lambda m: (_ex(m, "review_after").data,),
          _first(lambda d: d["members"][0]["review"]["topics"][0].update(provisional_citation_count=2))),
    _case("a withheld proposal shown as a citation", lambda d, ids: check_review_content(d, ids),
          lambda m: (_ex(m, "review_after").data, m.db["norm_ids"]),
          _first(lambda d: d["members"][3]["review"].update(
              provisional_citations=copy.deepcopy(d["members"][0]["review"]["provisional_citations"]),
              withheld_proposal_count=0))),
    _case("a citation that quotes something else", lambda d, ids: check_review_content(d, ids),
          lambda m: (_ex(m, "review_after").data, m.db["norm_ids"]),
          _first(lambda d: _first_available(d)["review"]["provisional_citations"][0]["citations"][0].update(raw_quote="x"))),
    _case("a review without its rejected count", lambda d, ids: check_review_content(d, ids),
          lambda m: (_ex(m, "review_after").data, m.db["norm_ids"]),
          _first(lambda d: d["members"][1]["review"].update(rejected_proposal_count=0))),
    _case("a model field in an answer", check_no_numeric_conclusion,
          lambda m: ([_ex(m, "review_after")],),
          lambda a: ([_as_exchange(_with(a[0][0].data, _inject_into_proposal("stated_value", "1,2 м")))],)),
    _case("a severity in an answer", check_no_numeric_conclusion,
          lambda m: ([_ex(m, "review_after")],),
          lambda a: ([_as_exchange(_with(a[0][0].data, _inject_into_proposal("proposed_severity", "operational")))],)),
    _case("the model's sentence in a topic reason", check_no_numeric_conclusion,
          lambda m: ([_ex(m, "review_after")],),
          lambda a: ([_as_exchange(_with(a[0][0].data, lambda d: d["members"][0]["review"]["topics"][0].update(
              reason=MODEL_PROSE[0])))],)),
    _case("a stated value outside a quote field", check_no_numeric_conclusion,
          lambda m: ([_ex(m, "review_after")],),
          lambda a: ([_as_exchange(_with(a[0][0].data, lambda d: d["members"][0]["review"]["topics"][0].update(
              reason=f"ширина {STATED_VALUE}")))],)),
    _case("a float in an answer", check_no_numeric_conclusion,
          lambda m: ([_ex(m, "review_after")],),
          lambda a: ([_as_exchange(_with(a[0][0].data, lambda d: d["members"][0]["review"]["topics"][0].update(
              provisional_citation_count=1.5)))],)),
    _case("the empty-registry refusal under another code", lambda e: check_typed_refusal(e, "dependency_unavailable", {"dependency": "ar_v3_trusted_pack"}),
          lambda m: (_ex(m, "start_empty_registry"),), lambda a: (_as_exchange(
              _with(a[0].data, lambda d: d.update(error_code="not_found")), 503),)),
    _case("the empty-registry refusal answered 202", lambda e: check_typed_refusal(e, "dependency_unavailable", {"dependency": "ar_v3_trusted_pack"}),
          lambda m: (_ex(m, "start_empty_registry"),), lambda a: (_as_exchange(a[0].data, 202),)),
    _case("the empty-registry refusal naming another dependency", lambda e: check_typed_refusal(e, "dependency_unavailable", {"dependency": "ar_v3_trusted_pack"}),
          lambda m: (_ex(m, "start_empty_registry"),),
          lambda a: (_as_exchange(_with(a[0].data, lambda d: d.update(details={"dependency": "blob_store"})), 503),)),
    _case("a non-expert start that was accepted", lambda e: check_typed_refusal(e, "permission_denied", {"required_capability": "role:expert"}),
          lambda m: (_ex(m, "start_admin"),), lambda a: (_as_exchange(a[0].data, 202),)),
    _case("a second start that is another group", check_same_group,
          lambda m: (_ex(m, "start").data, _ex(m, "start_again").data),
          lambda a: (a[0], _with(a[1], lambda d: d.update(group_id="arg_00000000000000000000000000")))),
    _case("a second start that made other Runs", check_same_group,
          lambda m: (_ex(m, "start").data, _ex(m, "start_again").data),
          lambda a: (a[0], _with(a[1], lambda d: d["members"][5].update(run_id="run_00000000000000000000000000")))),
    _case("a refusal that created a group", check_nothing_created,
          lambda m: (m.db["after_refusals"],), lambda a: ({**a[0], "groups": 1},)),
    _case("a replay that made a seventh Run", lambda c: check_one_group_of_six(c, 6),
          lambda m: (m.db["after_replay"],), lambda a: ({**a[0], "runs": 7},)),
    _case("a replay that made a second group", lambda c: check_one_group_of_six(c, 6),
          lambda m: (m.db["after_replay"],), lambda a: ({**a[0], "groups": 2},)),
    _case("a start that left a Run created", check_accepted_like_start_run,
          lambda m: (m.db, _ex(m, "start").data),
          lambda a: (_with(a[0], lambda d: d["states_after_start"].__setitem__(3, ("A2", "created"))), a[1])),
    _case("a start that left a Run without its Job", check_accepted_like_start_run,
          lambda m: (m.db, _ex(m, "start").data),
          lambda a: (_with(a[0], lambda d: d.update(after_start={**d["after_start"], "jobs": 5})), a[1])),
    _case("a start whose Job is not queued", check_accepted_like_start_run,
          lambda m: (m.db, _ex(m, "start").data),
          lambda a: (_with(a[0], lambda d: d["job_states_after_start"].__setitem__(0, ("F1", "leased"))), a[1])),
    _case("a start the poller's query cannot see", check_accepted_like_start_run,
          lambda m: (m.db, _ex(m, "start").data),
          lambda a: (_with(a[0], lambda d: d.update(next_queued_run_after_start=None)), a[1])),
    _case("a start that submitted five of the six Runs", check_accepted_like_start_run,
          lambda m: (m.db, _ex(m, "start").data),
          lambda a: (_with(a[0], lambda d: d["submitted_after_start"].pop()), a[1])),
    _case("a start that submitted the Runs in another order", check_accepted_like_start_run,
          lambda m: (m.db, _ex(m, "start").data),
          lambda a: (_with(a[0], lambda d: d["submitted_after_start"].reverse()), a[1])),
    _case("a replay that submitted a Run again", check_a_replay_adds_nothing,
          lambda m: (m.db,),
          lambda a: (_with(a[0], lambda d: d["submitted_after_replay"].append(d["submitted_after_start"][0])),)),
    _case("a replay that enqueued a seventh Job", check_a_replay_adds_nothing,
          lambda m: (m.db,),
          lambda a: (_with(a[0], lambda d: d.update(after_replay={**d["after_replay"], "jobs": 7})),)),
    _case("a refusal that submitted work", check_a_refusal_submits_nothing,
          lambda m: (m.db,),
          lambda a: (_with(a[0], lambda d: d["submitted_after_refusals"].append("run_00000000000000000000000000")),)),
]


@pytest.mark.parametrize("check,args,mutate", CHECK_CASES)
def test_every_check_can_fail(measured: Measurement, check: Callable[..., None],
                              args: Callable[[Measurement], tuple[Any, ...]],
                              mutate: Callable[[tuple[Any, ...]], tuple[Any, ...]]) -> None:
    real = args(measured)
    check(*real)  # the real answer passes
    with pytest.raises(AssertionError):
        check(*mutate(real))
