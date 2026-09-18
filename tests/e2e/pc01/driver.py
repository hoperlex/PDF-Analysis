"""The front-door driver for the PC-01 acceptance suite, session ``C2``.

Everything here builds the application the way a process does -- through
``auditmanager.api.app.create_app()`` -- and reaches the twelve operations only through the
``Router`` that comes back. Nothing in this tree imports ``IngestService``, ``execute_run``
or ``export_run_csv``: if an operation cannot be reached from outside, that has to surface
as a failure rather than be routed around.

Loaded by explicit path from this suite's ``conftest.py`` and its test modules, which is
the mechanism ``tests/integration/runs`` and ``tests/contract/api_v1`` already use for a
helper beside a suite. It adds nothing to ``sys.path``, and under
``--import-mode=importlib`` a bare ``from driver import ...`` would not resolve anyway. The
module name is session-unique so it cannot collide with another lane's helper.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE_PDF = CORPUS / "ar_baseline.pdf"
NEGATIVE = CORPUS / "negative"
EXPECTED_ISSUES = CORPUS / "expected_issues.json"
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"

#: This run's tag. Every identity the suite allocates carries it, so a run can never
#: collide with a peer's rows in the shared instance database, and "the same idempotency
#: key" in the criterion-9 tests means the same key and no other.
SESSION_TAG = uuid.uuid4().hex[:12]


def load_env_file() -> None:
    """Put this worktree's ``.env`` into the environment.

    ``pytest`` does not read ``.env``; the ``make`` targets do. A suite that skipped on a
    missing ``DATABASE_URL`` would report success having proved nothing, so an absent file
    is a hard failure rather than a skip.
    """
    if os.environ.get("DATABASE_URL") and os.environ.get("S3_ENDPOINT_URL"):
        return
    path = REPOSITORY_ROOT / ".env"
    if not path.is_file():
        raise RuntimeError(
            f"{path} is missing. This suite runs against real services: "
            "copy .env.example and set this session's instance."
        )
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip())


def load_pdfextract() -> Any:
    """The corpus's own PDF text extractor, loaded by explicit path.

    Deliberately *not* ``auditmanager.analysis.text.textlayer``: criterion 5 asks whether a
    published quotation really is on the page, and asking the product's own extractor
    would be certifying the product against itself. This module parses the file bytes from
    scratch and shares no data structure with the writer that produced the corpus.
    """
    name = "c2_pc01_pdfextract"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = REPOSITORY_ROOT / "tools" / "fixtures" / "ar_corpus" / "pdfextract.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True, slots=True)
class Answer:
    """One response, decoded far enough to assert on and no further."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @property
    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        for key_name, value in self.headers:
            if key_name.lower() == lowered:
                return value
        return None

    @property
    def error_code(self) -> str | None:
        try:
            payload = self.json
        except Exception:
            return None
        return payload.get("error_code") if isinstance(payload, dict) else None


class Client:
    """A caller at the front door.

    Holds an ``Application`` and nothing else -- no session, no engine, no blob store, no
    module the router calls. Everything this suite learns, it learns from a response.
    """

    __slots__ = ("_app", "_application", "_client")

    def __init__(self, app: Any, application: Any = None) -> None:
        from starlette.testclient import TestClient

        self._app = app
        self._application = application if application is not None else app
        # `raise_server_exceptions=False`: a fault that reached the client as an envelope
        # is recorded as the envelope the client got. With the default, `TestClient`
        # re-raises inside the test and the acceptance runbook never sees the answer --
        # which is exactly the case `D-5` is about.
        self._client = TestClient(app, raise_server_exceptions=False)

    @property
    def app(self) -> Any:
        """The built ``Application``. ``criterion 8`` asks it what was wired."""
        return self._application

    @property
    def asgi_app(self) -> Any:
        """The ``FastAPI`` this client drives."""
        return self._app

    def request(
        self,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] | Sequence[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> Answer:
        """One request over the real transport.

        **The one place in this suite that knows how the API is reached**, which is why
        `T-1` changed this method and nothing else in the file. It was ``Request.build``
        plus ``dispatch``; it is now a ``starlette.testclient.TestClient`` over the
        ``FastAPI`` application, so every criterion below is asserted against routing, the
        declared parameters, the body models, the exception handlers and the middlewares
        rather than against a hand-rolled table in front of them.

        ``response.headers.raw`` rather than the mapping: ``httpx`` lower-cases header
        names when you iterate it, and this suite asserts them as the contract spells them.

        The `T-6` credential is presented on every call unless the caller supplies its own
        ``Authorization`` header -- which the authorization criteria do, to be refused.
        """
        sent = {name: value for name, value in dict(headers).items()}
        if not any(name.lower() == "authorization" for name in sent):
            sent["Authorization"] = f"Bearer {STATIC_TOKEN}"
        response = self._client.request(method, target, headers=sent, content=body)
        return Answer(
            response.status_code,
            tuple(
                (name.decode("latin-1"), value.decode("latin-1"))
                for name, value in response.headers.raw
            ),
            response.content,
        )

    # -- the twelve operations, spelled the way the frozen document spells them --------

    def create_project(self, *, name: str, key: str) -> Answer:
        return self.request(
            "POST",
            "/projects",
            headers={"Idempotency-Key": key, "Content-Type": "application/json"},
            body=json.dumps({"name": name}).encode("utf-8"),
        )

    def list_projects(self, query: str = "") -> Answer:
        return self.request("GET", "/projects" + query)

    def upload_document(
        self,
        *,
        project_uid: str,
        content: bytes,
        key: str,
        filename: str = "ar_baseline.pdf",
        title: str = "AR baseline",
        content_type: str | None = None,
    ) -> Answer:
        boundary = "c2pc01boundary"
        head = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'
        ).encode("utf-8")
        tail = (
            f"\r\n--{boundary}\r\nContent-Disposition: form-data; "
            f'name="display_title"\r\n\r\n{title}\r\n--{boundary}--\r\n'
        ).encode("utf-8")
        declared = content_type or f"multipart/form-data; boundary={boundary}"
        return self.request(
            "POST",
            f"/projects/{project_uid}/documents",
            headers={"Idempotency-Key": key, "Content-Type": declared},
            body=head + content + tail,
        )

    def get_version(self, version_uid: str) -> Answer:
        return self.request("GET", f"/versions/{version_uid}")

    def stream_content(self, version_uid: str, *, byte_range: str | None = None) -> Answer:
        headers = {"Range": byte_range} if byte_range else {}
        return self.request("GET", f"/versions/{version_uid}/content", headers=headers)

    def start_run(
        self, *, version_uid: str, key: str, provider_mode: str | None = None
    ) -> Answer:
        payload: dict[str, Any] = {"version_uid": version_uid}
        if provider_mode is not None:
            payload["provider_mode"] = provider_mode
        return self.request(
            "POST",
            "/runs",
            headers={"Idempotency-Key": key, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )

    def await_runs(self, timeout: float = 300.0) -> None:
        """Block until every run this client has started has reached a terminal.

        `D-20`. ``startRun`` answers ``202 queued`` and the analysis runs on a carrier
        thread, so a criterion that asks what a *finished* run reports has to say when it
        is finished. It waits on the carrier's own futures --
        ``ThreadCarrier.drain`` -- which is the completion of the real work; a suite that
        slept for a plausible number would be asserting against a guess and would be
        flaky on a loaded host in exactly the way this programme has paid for before.

        Deliberately a method on the driver rather than something each test remembers: a
        criterion that forgot to wait would read a `queued` run and blame the product.
        """
        assert self._application.carrier.drain(timeout=timeout), (
            f"a run started through this client did not finish within {timeout}s"
        )

    def run_status(self, run_id: str) -> Answer:
        return self.request("GET", f"/runs/{run_id}")

    def run_findings(self, run_id: str, query: str = "") -> Answer:
        return self.request("GET", f"/runs/{run_id}/findings" + query)

    def finding(self, finding_uid: str) -> Answer:
        return self.request("GET", f"/findings/{finding_uid}")

    def append_decision(
        self,
        *,
        finding_uid: str,
        observation_id: str,
        event_type: str,
        key: str,
        comment: str | None = None,
    ) -> Answer:
        payload: dict[str, Any] = {
            "event_type": event_type,
            "finding_observation_id": observation_id,
        }
        if comment is not None:
            payload["comment"] = comment
        return self.request(
            "POST",
            f"/findings/{finding_uid}/decisions",
            headers={"Idempotency-Key": key, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )

    def decision_history(self, finding_uid: str, query: str = "") -> Answer:
        return self.request("GET", f"/findings/{finding_uid}/decisions" + query)

    def export_csv(self, run_id: str) -> Answer:
        return self.request("GET", f"/runs/{run_id}/export.csv")


def build_client(**overrides: str) -> Client:
    """A fresh application, wired from the environment with named overrides applied.

    Every call is a new composition root: a new engine, a new session factory, a new model
    adapter and a new router. That is what makes the criterion-8 test a restart rather
    than a second look at the same objects.
    """
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: STATIC_TOKEN} | overrides
    from auditmanager.api.app import create_app, create_asgi_app

    application = create_app(environ=environ)
    return Client(
        create_asgi_app(environ=environ, application=application), application
    )


#: `T-6`. The credential this suite configures and presents, and the variable the
#: application reads it from. Literals: a driver that read the token out of the
#: application would drive an application that had stopped checking it.
STATIC_TOKEN = "c2-pc01-static-token"
API_TOKEN_VARIABLE = "AUDITMANAGER_API_TOKEN"


def key(label: str, *, unique: bool = False) -> str:
    """An idempotency key, reproducible from its label within one run of this suite.

    Criterion 9 replays *the same* key, so a key has to be derivable twice. ``unique=True``
    is for the cases that genuinely need a fresh command.
    """
    suffix = f"-{uuid.uuid4().hex[:8]}" if unique else ""
    return f"c2pc01-{SESSION_TAG}-{label}{suffix}"


#: The name this module is registered under. Both this suite's ``conftest.py`` and its test
#: modules load it by explicit path under this name and therefore get the *same* object,
#: which matters: :data:`SESSION_TAG` has to be one value for the whole run, or a
#: criterion-9 replay would present a different key than the command it claims to replay.
DRIVER_MODULE_NAME = "c2_pc01_driver"
