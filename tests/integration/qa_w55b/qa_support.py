"""`W55B-QA-01` support (not a test module): the merged W55b candidate driven the way a client meets it.

Every probe in this directory talks **HTTP to a real API process**: the repository's own
entry point ``infra/deploy/serve.py``, started here as a child this conftest owns, wired to
the lane's PostgreSQL and S3 (the names of the lane's ``.env``), in ``recorded`` provider
mode -- the deterministic, offline adapter every automated suite uses (`OD-13`). No model
is called and no paid API is reached: the child's environment carries no key, no proxy and
no live mode, and a request the recordings cannot answer fails the run, never falls back.

What the lanes tested in isolation is crossed here: an upload through the transport
(STREAM) into the bundle reader (INGEST), a run started under the derived budget (BUDGET),
executed by the in-process dispatcher through ``source_preparation`` (RECOGNISED) and
``page_geometry_extraction`` (GEOMETRY), and read back through the two portal-block
operations -- over a socket, with real credentials, against one database and one bucket.

The harness reuses what exists and edits none of it: accounts are created with the access
boundary's own repositories and credentials are minted with the seam's own signer, exactly
as ``tests/support/accounts.py`` does; the bundles are the committed ones under
``fixtures/synthetic/ar/bundles`` and the generators under ``tools/fixtures/portal_bundle``
(put on the path the way ``tests/integration/ingest/conftest.py`` puts them).

**Process discipline.** Only the child started here is ever signalled, after its working
directory is confirmed to be this worktree. A port already in use fails the session: this
harness never stops something it did not start.
"""

from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BUNDLES = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles"
PYTHON = REPOSITORY_ROOT / ".venv" / "bin" / "python"
SERVE = REPOSITORY_ROOT / "infra" / "deploy" / "serve.py"

_TOOLS_FIXTURES = str(REPOSITORY_ROOT / "tools" / "fixtures")
if _TOOLS_FIXTURES not in sys.path:
    sys.path.insert(0, _TOOLS_FIXTURES)

#: The QA lane's API ports (`W55B-QA-01` brief). Overridable so the integrator can rerun the
#: probes on another free pair without editing this file.
API_PORT = int(os.environ.get("W55B_QA_API_PORT", "57500"))
HEALTH_PORT = int(os.environ.get("W55B_QA_HEALTH_PORT", str(API_PORT + 1)))
HOST = "127.0.0.1"

#: The suite's own deployment secret; credentials are signed with a key derived from it.
SECRET = "w55b-qa-01-deployment-secret"

#: The fifteen FF-01 names the lane's services and the application share.
_LANE_NAMES = (
    "DATABASE_URL",
    "S3_ENDPOINT_URL",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
)

#: Never handed to the child: anything that selects a provider, a key or a transport.
_NEVER_INHERITED = (
    "AUDITMANAGER_PROVIDER_MODE",
    "AUDITMANAGER_MODEL_ID",
    "AUDITMANAGER_RUN_COST_CEILING_USD",
    "ANTHROPIC_API_KEY",
    "PROXY_LLM_BASE_URL",
    "PROXY_LLM_TOKEN",
    "PROXY_LLM_MODEL",
    "EXECUTION_ROLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
)

TERMINAL_RUN_STATES = frozenset({"published", "partial", "failed", "cancelled"})


# ---------------------------------------------------------------------------------------
# the lane's configuration
# ---------------------------------------------------------------------------------------


def lane_environment() -> dict[str, str]:
    """The application-facing service names, from the process or else from the lane's ``.env``."""
    values = {name: os.environ[name] for name in _LANE_NAMES if os.environ.get(name)}
    dotenv = REPOSITORY_ROOT / ".env"
    if len(values) < len(_LANE_NAMES) and dotenv.is_file():
        for raw in dotenv.read_text(encoding="utf-8").splitlines():
            line = raw.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name, value = name.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if name in _LANE_NAMES and name not in values and value:
                values[name] = value
    missing = [name for name in _LANE_NAMES if name not in values]
    if missing:
        pytest.fail(f"the QA lane's services are not configured: {missing} (source the lane .env)")
    return values


# ---------------------------------------------------------------------------------------
# the served application
# ---------------------------------------------------------------------------------------


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((HOST, port)) != 0


def _child_environment(ceiling: str | None) -> dict[str, str]:
    environ = {k: v for k, v in os.environ.items() if k not in _NEVER_INHERITED}
    environ.update(lane_environment())
    environ.update(
        {
            "PYTHONPATH": str(REPOSITORY_ROOT / "src"),
            "AUDITMANAGER_API_TOKEN": SECRET,
            "AUDITMANAGER_PROVIDER_MODE": "recorded",
            "AUDITMANAGER_API_PORT": str(API_PORT),
            "AUDITMANAGER_HEALTH_PORT": str(HEALTH_PORT),
            "AUDITMANAGER_BIND_HOST": HOST,
        }
    )
    if ceiling is not None:
        environ["AUDITMANAGER_RUN_COST_CEILING_USD"] = ceiling
    return environ


@dataclass
class ServedApi:
    """One running ``serve.py`` child."""

    ceiling: str | None
    process: subprocess.Popen[bytes]
    log_path: Path

    @property
    def pid(self) -> int:
        return self.process.pid

    def log(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def vm_kib(self, key: str) -> int:
        for line in Path(f"/proc/{self.pid}/status").read_text().splitlines():
            if line.startswith(key + ":"):
                return int(line.split()[1])
        raise RuntimeError(key)


@dataclass
class StartRefusal:
    returncode: int
    output: str


class ApiControl:
    """Starts and stops the one API child of this session, on the lane's fixed ports."""

    def __init__(self) -> None:
        self.current: ServedApi | None = None
        self.log_directory = Path(tempfile.mkdtemp(prefix="w55b-qa-api-"))
        self.peaks: list[tuple[str | None, int]] = []

    def ensure(self, ceiling: str | None = None) -> ServedApi:
        """A served application at ``ceiling`` (``None``: the default, unset), started if needed."""
        if self.current is not None and self.current.ceiling == ceiling and self.current.process.poll() is None:
            return self.current
        self.stop()
        return self._start(ceiling)

    def _start(self, ceiling: str | None) -> ServedApi:
        for port in (API_PORT, HEALTH_PORT):
            if not _port_is_free(port):
                pytest.fail(f"port {port} is already in use; this harness never stops what it did not start")
        log_path = self.log_directory / f"api-{uuid.uuid4().hex[:8]}.log"
        with log_path.open("wb") as sink:
            process = subprocess.Popen(  # noqa: S603 - the repository's own entry point
                [str(PYTHON), str(SERVE)],
                cwd=REPOSITORY_ROOT,
                env=_child_environment(ceiling),
                stdout=sink,
                stderr=subprocess.STDOUT,
            )
        served = ServedApi(ceiling, process, log_path)
        assert Path(f"/proc/{process.pid}/cwd").resolve() == REPOSITORY_ROOT
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(f"the API exited with {process.returncode} while starting:\n{served.log()[-3000:]}")
            try:
                connection = http.client.HTTPConnection(HOST, HEALTH_PORT, timeout=2)
                connection.request("GET", "/readyz")
                ready = connection.getresponse().status == 200
                connection.close()
                if ready:
                    self.current = served
                    return served
            except OSError:
                pass
            time.sleep(0.5)
        self._terminate(served)
        pytest.fail(f"the API never became ready:\n{served.log()[-3000:]}")

    def refuses_to_start(self, ceiling: str, timeout: float = 120) -> StartRefusal:
        """Run ``serve.py`` at ``ceiling`` and expect it to exit on its own without binding."""
        self.stop()
        for port in (API_PORT, HEALTH_PORT):
            if not _port_is_free(port):
                pytest.fail(f"port {port} is already in use")
        completed = subprocess.run(  # noqa: S603
            [str(PYTHON), str(SERVE)],
            cwd=REPOSITORY_ROOT,
            env=_child_environment(ceiling),
            capture_output=True,
            timeout=timeout,
        )
        output = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        return StartRefusal(completed.returncode, output)

    def _terminate(self, served: ServedApi) -> None:
        process = served.process
        if process.poll() is not None:
            return
        try:
            cwd = Path(f"/proc/{process.pid}/cwd").resolve()
        except OSError:
            cwd = None
        # Signalled only when it is still the child this harness started, in this worktree.
        if cwd == REPOSITORY_ROOT:
            try:
                self.peaks.append((served.ceiling, served.vm_kib("VmHWM")))
            except (OSError, RuntimeError):
                pass
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=30)

    def stop(self) -> None:
        if self.current is not None:
            self._terminate(self.current)
            self.current = None


# ---------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------


@dataclass
class Answer:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def __repr__(self) -> str:  # the body, shortened, makes a failing assertion readable
        return f"Answer({self.status}, {self.body[:600]!r})"


def call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: Any = None,
    body: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    key: str | None = None,
    timeout: float = 300,
) -> Answer:
    sent: dict[str, str] = {}
    if token is not None:
        sent["Authorization"] = f"Bearer {token}"
    if key is not None:
        sent["Idempotency-Key"] = key
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        sent["Content-Type"] = "application/json"
    sent.update(headers or {})
    connection = http.client.HTTPConnection(HOST, API_PORT, timeout=timeout)
    try:
        connection.request(method, path, body=body, headers=sent)
        response = connection.getresponse()
        payload = response.read()
        return Answer(
            response.status, {k.lower(): v for k, v in response.getheaders()}, payload
        )
    finally:
        connection.close()


def new_key(prefix: str = "w55bqa") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:20]}"


def multipart(
    payload: bytes,
    *,
    filename: str = "bundle.zip",
    content_type: str | None = "application/zip",
    title: str | None = None,
) -> tuple[bytes, str]:
    """A ``multipart/form-data`` body with one ``file`` part (and an optional title)."""
    boundary = "w55bqa" + uuid.uuid4().hex
    parts: list[bytes] = []
    if title is not None:
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"display_title\"\r\n\r\n".encode()
            + title.encode("utf-8")
            + b"\r\n"
        )
    head = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
    if content_type is not None:
        head += f"Content-Type: {content_type}\r\n"
    parts.append(head.encode("utf-8") + b"\r\n" + payload + b"\r\n")
    data = b"".join(parts) + f"--{boundary}--\r\n".encode()
    return data, f"multipart/form-data; boundary={boundary}"


def upload(
    project_uid: str,
    payload: bytes,
    token: str,
    *,
    key: str | None = None,
    filename: str = "bundle.zip",
    content_type: str | None = "application/zip",
) -> Answer:
    data, kind = multipart(payload, filename=filename, content_type=content_type)
    return call(
        "POST",
        f"/projects/{project_uid}/documents",
        token=token,
        body=data,
        headers={"Content-Type": kind},
        key=key or new_key("upload"),
    )


def create_project(token: str, name: str = "W55B QA project") -> str:
    answer = call("POST", "/projects", token=token, json_body={"name": name}, key=new_key("project"))
    assert answer.status == 201, answer
    return str(answer.json()["project_uid"])


def start_run(version_uid: str, token: str, *, key: str | None = None) -> Answer:
    return call("POST", "/runs", token=token, json_body={"version_uid": version_uid}, key=key or new_key("run"))


def wait_terminal(run_id: str, token: str, *, timeout: float = 300) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: Any = None
    while time.monotonic() < deadline:
        answer = call("GET", f"/runs/{run_id}", token=token)
        assert answer.status == 200, answer
        last = answer.json()
        if last["state"] in TERMINAL_RUN_STATES:
            return last
        time.sleep(0.5)
    raise AssertionError(f"run {run_id} did not reach a terminal state in {timeout} s: {last}")


def portal_blocks(version_uid: str, token: str, *, limit: int = 200) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Every page of ``listVersionPortalBlocks``: (the first page's envelope, all items)."""
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    first: dict[str, Any] | None = None
    while True:
        query = f"?limit={limit}" + (f"&cursor={cursor}" if cursor else "")
        answer = call("GET", f"/versions/{version_uid}/portal-blocks{query}", token=token)
        assert answer.status == 200, answer
        page = answer.json()
        first = first or page
        items.extend(page["items"])
        cursor = page["page"]["next_cursor"]
        if not cursor:
            return first, items


# ---------------------------------------------------------------------------------------
# the database (read-mostly) and accounts
# ---------------------------------------------------------------------------------------


@dataclass
class Accounts:
    """Accounts in any standing the seam distinguishes, and credentials for them."""

    engine: Engine
    made: dict[str, str] = field(default_factory=dict)

    def credential(
        self,
        label: str,
        *,
        roles: frozenset[str] = frozenset({"expert"}),
        complete: bool = True,
        default_credential: bool = False,
        archived: bool = False,
    ) -> str:
        from auditmanager.access.accounts import AccountRepository
        from auditmanager.access.repository import UserRepository
        from auditmanager.api.security import Subject, build_signer

        users, accounts = UserRepository(), AccountRepository()
        login = f"w55bqa-{label}-{uuid.uuid4().hex[:8]}@suite.invalid"
        with Session(self.engine) as session:
            created = users.create_user(
                session, login, "w55b-qa-password-not-a-secret", is_default_credential=default_credential
            )
            uid = str(created.user_uid)
            if complete:
                accounts.complete_profile(session, user_uid=uid, email=None, last_name="Проверкина", first_name="Ада")
            for role in sorted(roles):
                accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
            session.commit()
            record = users.find_by_login(session, login)
            assert record is not None
            signer = build_signer({"AUDITMANAGER_API_TOKEN": SECRET})
            assert signer is not None
            token = signer.issue(
                Subject(
                    user_uid=uid,
                    login=record.login,
                    token_epoch=record.token_epoch,
                    display_label=record.display_label,
                ),
                is_default_credential=default_credential,
            ).token
            if archived:
                # Archived through the boundary's own command, by an administrator actor.
                admin = users.create_user(session, f"w55bqa-archiver-{uuid.uuid4().hex[:8]}@suite.invalid", "x" * 12)
                accounts.complete_profile(session, user_uid=str(admin.user_uid), email=None, last_name="Архивова", first_name="Ия")
                accounts.grant_role(session, user_uid=str(admin.user_uid), role="admin", granted_by=None)
                accounts.archive_account(session, actor_uid=str(admin.user_uid), user_uid=uid)
                session.commit()
        self.made[label] = uid
        return token


def scalar(engine: Engine, sql: str, **params: Any) -> Any:
    with engine.connect() as connection:
        return connection.execute(text(sql), params).scalar()


def rows(engine: Engine, sql: str, **params: Any) -> list[Any]:
    with engine.connect() as connection:
        return list(connection.execute(text(sql), params))


# ---------------------------------------------------------------------------------------
# the bundles
# ---------------------------------------------------------------------------------------


def committed(name: str) -> bytes:
    return (BUNDLES / name).read_bytes()


def bundle_manifest() -> dict[str, Any]:
    return json.loads((BUNDLES / "bundle_manifest.json").read_text(encoding="utf-8"))


def manifest_entry(manifest: Mapping[str, Any], name: str) -> dict[str, Any]:
    return next(entry for entry in manifest["bundles"] if entry["file"] == name)


def make_engine() -> Engine:
    return create_database_engine(
        DatabaseSettings(url=parse_database_url(lane_environment()["DATABASE_URL"]))
    )


# ---------------------------------------------------------------------------------------
# independent oracles (written here, not imported from the product)
# ---------------------------------------------------------------------------------------

#: The freeze's figures (`W55B-FREEZE-01`, "Fixed at the freeze"), restated as literals.
TEXTLESS_THRESHOLD = 50
MAX_CROP_PIXELS = 4_000_000
MIN_LONG_SIDE_PX = 800


def zip_members(archive: bytes) -> dict[str, bytes]:
    """The members of a committed synthetic bundle, by name (stdlib reader, never extracted)."""
    import io
    import zipfile

    with zipfile.ZipFile(io.BytesIO(archive)) as opened:
        return {info.filename: opened.read(info) for info in opened.infolist()}


def member_by_suffix(members: Mapping[str, bytes], suffix: str) -> bytes:
    found = [data for name, data in members.items() if name.endswith(suffix)]
    assert len(found) == 1, (suffix, list(members))
    return found[0]


def rebuild(archive: bytes, replace: Mapping[str, bytes]) -> bytes:
    """The same bundle with the members whose names end with a key of ``replace`` swapped."""
    import io
    import zipfile

    members = zip_members(archive)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as written:
        for name, data in members.items():
            for suffix, new in replace.items():
                if name.endswith(suffix):
                    data = new
            written.writestr(name, data)
    return out.getvalue()


def pdfium_page_characters(pdf: bytes) -> list[int]:
    """pypdfium2's character count per page: the length of ``get_text_range()`` on each page."""
    import pypdfium2

    document = pypdfium2.PdfDocument(pdf)
    try:
        counts = []
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            counts.append(len(textpage.get_text_range()))
            textpage.close()
            page.close()
        return counts
    finally:
        document.close()


def pdf_page_aspects(pdf: bytes) -> list[float]:
    """Each page's displayed width / height (CropBox after /Rotate), from pypdfium2."""
    import pypdfium2

    document = pypdfium2.PdfDocument(pdf)
    try:
        aspects = []
        for index in range(len(document)):
            page = document[index]
            width, height = page.get_size()
            aspects.append(width / height)
            page.close()
        return aspects
    finally:
        document.close()


_BLOCK_HEADER = r"^### BLOCK #\d+ \[(TEXT|IMAGE)\]: (blk_[0-9a-f]{32})\s*$"


def markdown_bodies(markdown: str) -> dict[str, tuple[str, str]]:
    """``{block_id: (TEXT|IMAGE, body)}`` read from ``_results.md`` by a reader written here.

    A body starts after the block header, its blank line and its ``> **Key:** value`` quote
    lines, and ends at the next block header or page heading; blank lines are trimmed at
    both ends; line breaks inside it are kept.
    """
    import re

    header = re.compile(_BLOCK_HEADER)
    bodies: dict[str, tuple[str, str]] = {}
    current: tuple[str, str] | None = None
    lines: list[str] = []

    def flush() -> None:
        if current is None:
            return
        body = list(lines)
        while body and (not body[0].strip() or body[0].startswith(">")):
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        bodies[current[1]] = (current[0], "\n".join(body))

    for raw in markdown.split("\n"):
        line = raw.rstrip("\r")
        matched = header.match(line)
        if matched or line.startswith("## Page "):
            flush()
            current = (matched.group(1), matched.group(2)) if matched else None
            lines = []
            continue
        if current is not None:
            lines.append(line)
    flush()
    return bodies


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) from a PNG's IHDR chunk."""
    import struct

    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def text_rich_bundle(pages: int, *, stem: str = "qa_text_rich", lines_per_page: int = 44) -> bytes:
    """A generated bundle whose every page is dense Cyrillic text: about 2 900 pypdfium2
    characters a page, built with the fixtures' own PDF writer and bundle builder."""
    import build_ar_corpus
    from ar_corpus import document
    from portal_bundle.bundle import build_bundle, make_files

    font = build_ar_corpus.load_font()
    sentence = "Проверка бюджета анализа: плотный текст страницы синтетического тома"
    contents = []
    for number in range(1, pages + 1):
        y = document.PAGE_HEIGHT - document.MARGIN_TOP
        page = []
        for line in range(lines_per_page):
            page.append((f"{number:03d}.{line:02d} {sentence}", 9.0, document.MARGIN_LEFT, y))
            y -= 16.5
        contents.append(page)
    pdf = document.simple_text_pdf(font, contents)
    return build_bundle(make_files(pdf, stem)).data
