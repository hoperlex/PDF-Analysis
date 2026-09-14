"""Fixtures for the PC-01 acceptance suite, session ``C2``.

Everything here builds the application the way a process does -- through
``auditmanager.api.app.create_app()`` -- and drives it through the ``Router`` that comes
back. Nothing in this tree imports ``IngestService``, ``execute_run`` or
``export_run_csv``. The one module reached for directly is
``tools/fixtures/ar_corpus/pdfextract.py``, and that is deliberate: it is the corpus's own
acceptance oracle, loaded by explicit path, used only to read the PDF back independently
so criterion 5 is not certified by asking the product whether the product was right.

**Provider configuration is set here, explicitly and visibly.** ``tests/conftest.py``
strips every provider-selecting variable for the whole session precisely so that a suite
which wants a mode has to say so. This suite wants ``recorded`` for everything except the
one test that names a live call in its own body.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE_PDF = CORPUS / "ar_baseline.pdf"
NEGATIVE = CORPUS / "negative"
EXPECTED_ISSUES = CORPUS / "expected_issues.json"

#: The session tag. Every identity this suite allocates carries it, so a run of this
#: suite can never collide with a peer's rows in the shared instance database and a
#: replay under "the same idempotency key" means the same key and no other.
SESSION_TAG = uuid.uuid4().hex[:12]


def load_env_file() -> None:
    """Put this worktree's ``.env`` into the environment.

    ``pytest`` does not read ``.env``; the ``make`` targets do. A suite that skipped on a
    missing ``DATABASE_URL`` would report success having proved nothing, so an absent file
    is a hard failure.
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


@pytest.fixture(scope="session", autouse=True)
def recorded_provider_mode() -> Iterator[None]:
    """Name the provider mode out loud, because the root conftest removed it.

    Asserted rather than assumed: if the root conftest's strip were ever reordered after
    this fixture, the suite would silently inherit whatever a developer had exported, and
    the ``proxy`` value in a live shell would make every test below a paid call.
    """
    load_env_file()
    os.environ["AUDITMANAGER_PROVIDER_MODE"] = "recorded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, (
            f"{leaked} reached this suite; the recorded journey must not be able to spend"
        )
    yield


# --------------------------------------------------------------------------------------
# The corpus oracle, read independently of the product.
# --------------------------------------------------------------------------------------


def _load_pdfextract() -> Any:
    """Load the corpus's own extractor by explicit path.

    ``importlib.util.spec_from_file_location`` is the mechanism ``tests/integration/runs``
    and ``tests/contract/api_v1`` already use for a helper beside a suite. It adds nothing
    to ``sys.path``. The module name is session-unique so it cannot collide with a peer's.
    """
    name = "c2_pc01_pdfextract"
    path = REPOSITORY_ROOT / "tools" / "fixtures" / "ar_corpus" / "pdfextract.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def manifest() -> Mapping[str, Any]:
    return json.loads(EXPECTED_ISSUES.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def page_texts(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    """The eight page texts of the baseline PDF, read back from the file bytes.

    Pinned against the manifest's ``page_text_sha256`` before any quotation is checked
    against them. Without that pin a quotation check would be asserting a property of
    whatever this extractor happened to produce rather than of the corpus.
    """
    import hashlib

    extractor = _load_pdfextract()
    pages = tuple(extractor.extract_pages(BASELINE_PDF.read_bytes()))
    declared = tuple(manifest["baseline"]["page_text_sha256"])
    observed = tuple(
        hashlib.sha256(text.encode("utf-8")).hexdigest() for text in pages
    )
    assert observed == declared, (
        "the corpus extractor no longer reproduces the page texts the manifest declares; "
        "every quotation check below would be measuring the extractor, not the corpus"
    )
    return pages


# --------------------------------------------------------------------------------------
# The composed application, driven request in / response out.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Answer:
    """One response, already decoded far enough to assert on."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @property
    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        for key, value in self.headers:
            if key.lower() == lowered:
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
    """A caller at the front door. Knows a method, a target, headers and bytes.

    Deliberately has no access to a session, an engine, a blob store or any module the
    router calls. Everything this suite learns, it learns from a response.
    """

    __slots__ = ("_app",)

    def __init__(self, app: Any) -> None:
        self._app = app

    @property
    def app(self) -> Any:
        return self._app

    def request(
        self,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] | Sequence[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> Answer:
        from auditmanager.api.routers import Request, dispatch

        request = Request.build(method, target, headers=headers, body=body)
        response = dispatch(self._app.router, request)
        return Answer(response.status, tuple(response.headers), response.body)

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
            f'\r\n--{boundary}\r\nContent-Disposition: form-data; '
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
    """A fresh application, wired from the environment, with named overrides applied.

    Every call to this is a new composition root: a new engine, a new session factory, a
    new model adapter and a new router. That is what makes the criterion-8 restart test a
    restart rather than a second look at the same objects.
    """
    environ = dict(os.environ) | overrides
    from auditmanager.api.app import create_app

    return Client(create_app(environ=environ))


@pytest.fixture(scope="session")
def client(recorded_provider_mode: None) -> Client:
    return build_client(AUDITMANAGER_PROVIDER_MODE="recorded")


def key(label: str, *, unique: bool = False) -> str:
    """An idempotency key. Stable per label within this session's run, by design.

    Criterion 9 replays *the same* key, so a key must be reproducible from its label.
    ``unique=True`` is for the cases that need a fresh command.
    """
    suffix = f"-{uuid.uuid4().hex[:8]}" if unique else ""
    return f"c2pc01-{SESSION_TAG}-{label}{suffix}"
