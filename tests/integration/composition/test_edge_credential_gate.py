"""`HARDEN-AUTH-EDGE-01` -- the proxy refuses a stranger BEFORE it reads a body, and counts
the credential exchange per address. `EXPOSURE-REVIEW-01` `E-4` and `E-5`, debt `D-192`.

**What is claimed, in two halves, and which half each test proves.**

1. *E-5.* The two public locations that take a 260 MiB body (`/api/v1/projects/*/documents`
   and `/bff/v1/projects/*/documents`, each also `.../versions`) used to let nginx read the
   whole body -- memory, then a temporary file on the stand's scarce disk -- for any caller,
   and only then hand the request to a tier that answers 401 to a stranger. Each now carries
   an `auth_request` whose internal location asks the addressed tier one cheap authenticated
   read (`GET /me`, `GET /bff/v1/me`), which nginx runs in its access phase, before the
   content phase reads the body.
2. *E-4.* `POST /api/v1/auth/token` is counted per client address in a zone of its own
   (`token_exchange`), beside the registration zone, and refused with the catalog's
   `rate_limited` envelope.

**The static half** (`test_*_static_*`) reads `nginx.conf` and `tls-server.conf` and asserts
the structure that makes the claim true. It needs no daemon, so it runs wherever the battery
runs; but it cannot say that nginx behaves as the structure promises.

**The live half** (`test_*_live_*`) starts a REAL nginx on loopback with the committed
configuration -- only the three addresses changed (`api`, `web`, the listener) -- in front of
two stub upstreams that record what reached them, and drives the claims with raw sockets:
an unauthenticated upload that DECLARES 260 MiB gets 401 while the client has sent no body at
all, with no temporary body file on disk and no upload request at the application; the same
with a bad bearer and a megabyte of body actually sent; an authenticated upload still arrives
whole; the sign-in exchange is refused on its twelfth call in a burst and does not spend the
registration budget. It needs an `nginx` binary (`AUDITMANAGER_NGINX_BIN`, else `PATH`, else
`/usr/sbin/nginx`); without one the live half is skipped with that reason, and the static half
still holds. The pinned image's `nginx` is the same program with the same modules. The
instrument starts only its own process, stops it by the PID it started, and never signals any
other nginx on the host.

**Every guard is shown able to fail**, in `test_each_*_can_fail`, by putting a mutation in
front of the same function the real check uses.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from auditmanager.shared.errors import screen_message

ROOT = Path(__file__).resolve().parents[3]
PROXY = ROOT / "infra" / "deploy" / "proxy"
PLAIN = PROXY / "nginx.conf"
TLS_BLOCK = PROXY / "tls-server.conf"
CATALOG = ROOT / "contracts" / "domain" / "v1" / "error-codes.json"

UPLOAD_API = "location ~ ^/api/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {"
UPLOAD_BFF = "location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {"
CREDENTIAL_API = "location = /_edge/credential/api {"
CREDENTIAL_WEB = "location = /_edge/credential/web {"
AUTH_REQUIRED = "location @authentication_required {"
#: Which upload location asks which credential location, and which tier that one reaches.
GATES = {
    UPLOAD_API: ("auth_request /_edge/credential/api;", CREDENTIAL_API, "proxy_pass http://api:8000/me;"),
    UPLOAD_BFF: (
        "auth_request /_edge/credential/web;",
        CREDENTIAL_WEB,
        "proxy_pass http://web:3000/bff/v1/me;",
    ),
}
REFUSAL_PAGE = "error_page 401 = @authentication_required;"
UPLOAD_BODY_CAP = "client_max_body_size 260m;"
#: What a credential subrequest must say to carry a request's headers but not its body.
SUBREQUEST_BODYLESS = ("proxy_pass_request_body off;", 'proxy_set_header Content-Length "";')
#: The four the server level sets, which a location that declares one of its own drops.
SERVER_PROXY_HEADERS = (
    "proxy_set_header Host $http_host;",
    "proxy_set_header X-Real-IP $remote_addr;",
    "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
    "proxy_set_header X-Forwarded-Proto $scheme;",
)
TOKEN_ZONE = "token_exchange"
TOKEN_KEY = "POST:/api/v1/auth/token"
TOKEN_LIMIT = "limit_req zone=token_exchange burst=10 nodelay;"
SAMPLE_REQUEST_ID = "0123456789abcdef0123456789abcdef"


# ---------------------------------------------------------------------------------------
# Reading the files
# ---------------------------------------------------------------------------------------


def statements(config: str) -> list[str]:
    """Every non-comment line, stripped, inner spacing collapsed. A `#` ends the line."""
    out: list[str] = []
    for raw in config.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(" ".join(line.split()))
    return out


def blocks(lines: list[str], header: str) -> list[list[str]]:
    """The inner lines of every block whose opening line is exactly ``header``."""
    found: list[list[str]] = []
    for index, line in enumerate(lines):
        if line != header:
            continue
        depth = 1
        inner: list[str] = []
        for following in lines[index + 1 :]:
            if following.endswith("{"):
                depth += 1
            elif following == "}":
                depth -= 1
                if depth == 0:
                    break
            inner.append(following)
        found.append(inner)
    return found


def _catalog_entry(code: str) -> dict[str, Any]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {"contract_version": catalog["contract_version"], **catalog["codes"][code]}


def envelope_problems(name: str, config: str, location: str, code: str) -> list[str]:
    """The named location answers exactly what the catalog says ``code`` carries."""
    named = blocks(statements(config), location)
    if len(named) != 1:
        return [f"{name}: expected one `{location}`, found {len(named)}"]
    problems: list[str] = []
    inner = named[0]
    if "default_type application/json;" not in inner:
        problems.append(f"{name}: {location} does not answer as application/json")
    returns = [re.match(r"^return (\d{3}) '(.*)';$", line) for line in inner if line.startswith("return ")]
    if len(returns) != 1 or returns[0] is None:
        return problems + [f"{name}: {location} must hold one `return <status> '<json>';`"]
    status, body = int(returns[0].group(1)), returns[0].group(2)
    if re.findall(r"\$\{?\w+", body) != ["$request_id"]:
        problems.append(f"{name}: {location} must interpolate $request_id and nothing else")
    try:
        payload = json.loads(body.replace("$request_id", SAMPLE_REQUEST_ID))
    except json.JSONDecodeError as exc:
        return problems + [f"{name}: {location} body is not JSON: {exc}"]
    entry = _catalog_entry(code)
    if status != entry["http"]:
        problems.append(f"{name}: {location} returns {status}; the catalog gives {code} {entry['http']}")
    wanted = {
        "contract_version": entry["contract_version"],
        "error_code": code,
        "message": entry["summary"],
        "correlation_id": SAMPLE_REQUEST_ID,
        "retryable": entry["retryable"],
    }
    if payload != wanted:
        problems.append(f"{name}: {location} carries {payload}; the catalog says {wanted}")
    try:
        screen_message(str(payload.get("message", "")))
    except ValueError as exc:
        problems.append(f"{name}: {location} message fails the envelope screen: {exc}")
    return problems


def gate_problems(name: str, config: str) -> list[str]:
    """Each upload location asks its own tier before it reads a body, and answers the envelope."""
    lines = statements(config)
    problems: list[str] = []
    for upload, (request, credential, target) in GATES.items():
        found = blocks(lines, upload)
        if len(found) != 1:
            problems.append(f"{name}: expected one `{upload}`, found {len(found)}")
            continue
        inner = found[0]
        if inner.count(request) != 1:
            problems.append(f"{name}: `{upload}` must carry exactly one `{request}`: {inner}")
        if [line for line in inner if line.startswith("auth_request ")] != [request]:
            problems.append(f"{name}: `{upload}` asks something other than `{request}`")
        if REFUSAL_PAGE not in inner:
            problems.append(f"{name}: `{upload}` lacks {REFUSAL_PAGE!r}, so a 401 is nginx's HTML page")
        subs = blocks(lines, credential)
        if len(subs) != 1:
            problems.append(f"{name}: expected one `{credential}`, found {len(subs)}")
            continue
        sub = subs[0]
        if "internal;" not in sub:
            problems.append(f"{name}: `{credential}` is not internal; it would be an address anyone can ask")
        if sub.count(target) != 1 or [x for x in sub if x.startswith("proxy_pass ")] != [target]:
            problems.append(f"{name}: `{credential}` must proxy exactly to {target!r}: {sub}")
        for needed in (*SUBREQUEST_BODYLESS, *SERVER_PROXY_HEADERS, UPLOAD_BODY_CAP):
            if needed not in sub:
                problems.append(f"{name}: `{credential}` lacks {needed!r}")
        if [x for x in sub if x.startswith("client_max_body_size ")] != [UPLOAD_BODY_CAP]:
            problems.append(
                f"{name}: `{credential}` must hold the upload locations' own cap and no other: "
                "a subrequest re-checks the declared length against the cap of its location"
            )
        for line in sub:
            if line.startswith(("add_header ", "auth_request ")):
                problems.append(f"{name}: `{credential}` declares `{line}`")
    # No other location may ask a credential: the check belongs to the two big bodies.
    asking = [line for line in lines if line.startswith("auth_request ")]
    if sorted(asking) != sorted(request for request, _, _ in GATES.values()):
        problems.append(f"{name}: auth_request appears {asking}, not exactly in the two upload locations")
    # The only locations anyone may ask for `/_edge/` are the two internal ones.
    edge = [line for line in lines if line.startswith("location") and "/_edge/" in line]
    if sorted(edge) != sorted([CREDENTIAL_API, CREDENTIAL_WEB]):
        problems.append(f"{name}: unexpected /_edge/ locations: {edge}")
    problems += envelope_problems(name, config, AUTH_REQUIRED, "authentication_required")
    return problems


def token_throttle_problems(plain: str, tls: str) -> list[str]:
    """The exchange is counted per address in its own zone, declared once, applied in both bodies."""
    problems: list[str] = []
    lines = statements(plain)
    zones = [line for line in lines if line.startswith(f"limit_req_zone ") and f"zone={TOKEN_ZONE}:" in line]
    if len(zones) != 1:
        return [f"nginx.conf must declare the {TOKEN_ZONE} zone exactly once: {zones}"]
    match = re.match(r"^limit_req_zone (\$\w+) zone=token_exchange:\d+[km] rate=(\d+)r/m;$", zones[0])
    if match is None:
        return [f"the {TOKEN_ZONE} zone is not the expected shape: {zones[0]!r}"]
    variable = match.group(1)
    maps = [line for line in lines if line == f'map "$request_method:$uri" {variable} {{']
    if len(maps) != 1:
        return [f"{variable} must be the key of exactly one map keyed by the method and the path: {maps}"]
    (inner,) = blocks(lines, maps[0])
    entries = {}
    for line in inner:
        tokens = shlex.split(line.rstrip(";"))
        entries[tokens[0]] = tokens[1] if len(tokens) == 2 else "<not a key and a value>"
    if entries != {"default": "", TOKEN_KEY: "$binary_remote_addr"}:
        problems.append(f"{variable} must yield the address for {TOKEN_KEY!r} alone: {entries}")
    for name, config in (("nginx.conf", plain), ("tls-server.conf", tls)):
        body = statements(config)
        prefixed = blocks(body, "location /api/v1/ {")
        uploads = blocks(body, UPLOAD_API)
        if len(prefixed) != 1 or len(uploads) != 1:
            problems.append(f"{name}: expected one `location /api/v1/` and one API upload location")
            continue
        for where, inner_lines in (("location /api/v1/", prefixed[0]), ("the API upload location", uploads[0])):
            if inner_lines.count(TOKEN_LIMIT) != 1:
                problems.append(f"{name}: {where} lacks exactly one `{TOKEN_LIMIT}`")
        elsewhere = [line for line in body if line == TOKEN_LIMIT]
        if len(elsewhere) != 2:
            problems.append(f"{name}: `{TOKEN_LIMIT}` appears {len(elsewhere)} times, not in exactly the two API locations")
    for line in statements(tls):
        if line.startswith("limit_req_zone ") or (line.startswith("map ") and variable in line):
            problems.append(f"tls-server.conf declares an http-level directive: {line!r}")
    return problems


def all_static_problems(plain: str, tls: str) -> list[str]:
    problems = token_throttle_problems(plain, tls)
    for name, config in (("nginx.conf", plain), ("tls-server.conf", tls)):
        problems += gate_problems(name, config)
    for header in (UPLOAD_API, UPLOAD_BFF, CREDENTIAL_API, CREDENTIAL_WEB, AUTH_REQUIRED):
        if blocks(statements(plain), header) != blocks(statements(tls), header):
            problems.append(f"the two `{header}` blocks differ")
    return problems


# ---------------------------------------------------------------------------------------
# The mutations both halves are shown against. (case, file, exact text replaced, replacement)
# ---------------------------------------------------------------------------------------

_API_GATE = "        auth_request /_edge/credential/api;\n"
_WEB_GATE = "        auth_request /_edge/credential/web;\n"
_REFUSAL = "        error_page 401 = @authentication_required;\n"
_TOKEN_LINE = "        limit_req zone=token_exchange burst=10 nodelay;\n"

MUTATIONS: list[tuple[str, str, str, str]] = [
    ("the api upload location stops asking", "nginx.conf", _API_GATE, ""),
    ("the web upload location stops asking", "nginx.conf", _WEB_GATE, ""),
    ("the tls api upload location stops asking", "tls-server.conf", _API_GATE, ""),
    ("the tls web upload location stops asking", "tls-server.conf", _WEB_GATE, ""),
    (
        "the api upload location asks the web tier",
        "nginx.conf",
        _API_GATE,
        "        auth_request /_edge/credential/web;\n",
    ),
    ("the api refusal is nginx's HTML page", "nginx.conf", _REFUSAL, ""),
    (
        "the credential location can be asked for from outside",
        "nginx.conf",
        "    location = /_edge/credential/api {\n        internal;\n",
        "    location = /_edge/credential/api {\n",
    ),
    (
        "the credential location falls back to the server's cap",
        "nginx.conf",
        "        internal;\n        client_max_body_size 260m;\n        proxy_pass http://api:8000/me;\n",
        "        internal;\n        proxy_pass http://api:8000/me;\n",
    ),
    (
        "the credential subrequest carries the body",
        "nginx.conf",
        "        proxy_pass http://api:8000/me;\n        proxy_pass_request_body off;\n",
        "        proxy_pass http://api:8000/me;\n",
    ),
    (
        "the credential subrequest forwards the declared length",
        "tls-server.conf",
        '        proxy_pass http://api:8000/me;\n        proxy_pass_request_body off;\n        proxy_set_header Content-Length "";\n',
        "        proxy_pass http://api:8000/me;\n        proxy_pass_request_body off;\n",
    ),
    (
        "the credential subrequest drops the inherited headers",
        "nginx.conf",
        "        proxy_set_header Host $http_host;\n        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n\n    location = /_edge/credential/web {",
        "    }\n\n    location = /_edge/credential/web {",
    ),
    (
        "the credential subrequest asks a different read",
        "tls-server.conf",
        "proxy_pass http://web:3000/bff/v1/me;",
        "proxy_pass http://web:3000/bff/v1/projects;",
    ),
    (
        "the authentication envelope names another code",
        "nginx.conf",
        '"error_code":"authentication_required"',
        '"error_code":"permission_denied"',
    ),
    (
        "the authentication envelope is retryable",
        "tls-server.conf",
        '"retryable":false}',
        '"retryable":true}',
    ),
    ("the token limit is gone from the api location", "nginx.conf", _TOKEN_LINE, ""),
    ("the token limit is gone from the tls api location", "tls-server.conf", _TOKEN_LINE, ""),
    (
        "the token zone is keyed by the registration map",
        "nginx.conf",
        "limit_req_zone $token_exchange_client zone=token_exchange:1m",
        "limit_req_zone $guest_registration_client zone=token_exchange:1m",
    ),
    (
        "the token key no longer names the exchange",
        "nginx.conf",
        '"POST:/api/v1/auth/token"    $binary_remote_addr;',
        '"POST:/api/v1/auth/tokens"   $binary_remote_addr;',
    ),
    (
        "the token key widened to every post",
        "nginx.conf",
        '"POST:/api/v1/auth/token"    $binary_remote_addr;',
        '"POST:/api/v1/auth/token"    $binary_remote_addr;\n    "~^POST:"                    $binary_remote_addr;',
    ),
    (
        "the token key is the whole address space",
        "nginx.conf",
        "map \"$request_method:$uri\" $token_exchange_client {\n    default                      \"\";",
        "map \"$request_method:$uri\" $token_exchange_client {\n    default                      $binary_remote_addr;",
    ),
]


def mutated(case: str, plain: str, tls: str) -> tuple[str, str]:
    """``(plain, tls)`` with the named mutation applied once; the text replaced must exist."""
    for name, target, old, new in MUTATIONS:
        if name != case:
            continue
        text = plain if target == "nginx.conf" else tls
        assert old in text, f"{case}: the mutation matches nothing in {target}"
        text = text.replace(old, new, 1)
        return (text, tls) if target == "nginx.conf" else (plain, text)
    raise KeyError(case)


# ---------------------------------------------------------------------------------------
# The static half
# ---------------------------------------------------------------------------------------


def test_the_gate_and_the_token_throttle_are_in_both_bodies_static() -> None:
    assert all_static_problems(PLAIN.read_text(), TLS_BLOCK.read_text()) == []


@pytest.mark.parametrize("case", [name for name, *_ in MUTATIONS])
def test_each_static_guard_can_fail(case: str) -> None:
    plain, tls = mutated(case, PLAIN.read_text(), TLS_BLOCK.read_text())
    assert all_static_problems(plain, tls) != [], f"{case}: the static guard stayed green"


# ---------------------------------------------------------------------------------------
# The live half: a real nginx, two stub upstreams, raw sockets
# ---------------------------------------------------------------------------------------

GOOD_BEARER = "Bearer good-token"
GOOD_COOKIE = "am_session=good-session"
DECLARED_UPLOAD = 260 * 1024 * 1024
ONE_MEBIBYTE = 1024 * 1024
ANSWER_WITHIN = 5.0
FAST_ANSWER_WITHIN = 1.0
UPLOAD_PATH_API = "/api/v1/projects/prj_0123456789abcdef/documents"
UPLOAD_PATH_BFF = "/bff/v1/projects/prj_0123456789abcdef/documents"


def locate_nginx() -> str | None:
    for candidate in (os.environ.get("AUDITMANAGER_NGINX_BIN"), shutil.which("nginx"), "/usr/sbin/nginx"):
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    return None


class Upstream(ThreadingHTTPServer):
    """A stub tier: records every request it receives and answers from a small rulebook."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, tier: str) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.tier = tier
        self.seen: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def handle_error(self, request: Any, client_address: Any) -> None:
        """A proxy that hangs up on a stub it has no more use for is not a stub failure."""


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_: Any) -> None:  # silence
        return

    def _serve(self) -> None:
        server: Upstream = self.server  # type: ignore[assignment]
        declared = int(self.headers.get("Content-Length") or 0)
        received = 0
        while received < declared:
            chunk = self.rfile.read(min(65536, declared - received))
            if not chunk:
                break
            received += len(chunk)
        with server.lock:
            server.seen.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "received": received,
                }
            )
        status, body = self._decide(server.tier, received)
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True

    def _decide(self, tier: str, received: int) -> tuple[int, dict[str, Any]]:
        path = self.path.split("?", 1)[0]
        refused = (401, {"error_code": "authentication_required", "from": tier})
        if tier == "api":
            if path == "/me":
                return (200, {"login": "someone"}) if self.headers.get("Authorization") == GOOD_BEARER else refused
            if path == "/auth/token":
                return 401, {"error_code": "authentication_required", "from": "api-exchange"}
            if path == "/registrations":
                return 201, {"request_id": "r"}
            return (200, {"received": received}) if self.headers.get("Authorization") == GOOD_BEARER else refused
        if path == "/bff/v1/me":
            return (200, {"login": "someone"}) if GOOD_COOKIE in (self.headers.get("Cookie") or "") else refused
        return (200, {"received": received}) if GOOD_COOKIE in (self.headers.get("Cookie") or "") else refused

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _serve


class Answer:
    def __init__(self, raw: bytes, elapsed: float) -> None:
        head, _, body = raw.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        self.status = int(lines[0].split()[1])
        self.headers = {k.lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])}
        self.body = body
        self.elapsed = elapsed

    def json(self) -> Any:
        return json.loads(self.body or b"null")


def ask(
    port: int,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    declared: int | None = None,
    send: int | bytes = 0,
    wait: float = ANSWER_WITHIN,
) -> Answer | None:
    """One raw request on its own connection; ``None`` when nothing answers within ``wait``.

    ``declared`` is the Content-Length announced; ``send`` is how many body bytes are
    actually written afterwards (a count or the bytes), possibly none and possibly fewer than
    declared -- which is exactly the situation of a stranger announcing 260 MiB.
    """
    head = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{port}", "Connection: close"]
    for key, value in (headers or {}).items():
        head.append(f"{key}: {value}")
    if declared is not None:
        head.append(f"Content-Length: {declared}")
    started = time.monotonic()
    with socket.create_connection(("127.0.0.1", port), timeout=wait) as connection:
        connection.sendall(("\r\n".join(head) + "\r\n\r\n").encode("latin-1"))
        body = send if isinstance(send, bytes) else b"x" * send
        view = memoryview(body)
        try:
            for start in range(0, len(view), 65536):
                connection.sendall(view[start : start + 65536])
        except OSError:
            pass  # the proxy answered and closed before the body was taken: that is the point
        connection.settimeout(wait)
        received = b""
        deadline = started + wait
        try:
            while time.monotonic() < deadline:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                received += chunk
                if b"\r\n\r\n" in received:
                    head_bytes, _, rest = received.partition(b"\r\n\r\n")
                    match = re.search(rb"(?i)content-length:\s*(\d+)", head_bytes)
                    if match and len(rest) >= int(match.group(1)):
                        break
        except OSError:
            pass
    return Answer(received, time.monotonic() - started) if b"\r\n\r\n" in received else None


class Proxy:
    def __init__(self, process: subprocess.Popen[bytes], port: int, home: Path) -> None:
        self.process, self.port, self.home = process, port, home
        self.api = self.web = None  # set by `running`

    def body_files(self) -> list[str]:
        return sorted(os.listdir(self.home / "body"))


def render(config: str, *, port: int, api: int, web: int) -> str:
    text = config.replace("http://api:8000", f"http://127.0.0.1:{api}")
    text = text.replace("http://web:3000", f"http://127.0.0.1:{web}")
    return text.replace("listen 8080;", f"listen 127.0.0.1:{port};")


def tls_body_as_plain(tls: str, port: int) -> str:
    """The application body of `tls-server.conf` as a plain listener, nothing else changed."""
    out = []
    for line in tls.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped.startswith(("listen ", "http2 ", "ssl_", "add_header Strict-Transport-Security ")):
            if stripped.startswith("listen "):
                out.append(f"    listen 127.0.0.1:{port};")
            continue
        out.append(line)
    return "\n".join(out)


def http_level(plain: str) -> str:
    """`nginx.conf` up to its server block: the maps and zones both bodies use."""
    return re.split(r"(?m)^server \{$", plain, maxsplit=1)[0]


@contextmanager
def running(plain: str, tls: str, *, body: str) -> Iterator[tuple[Proxy, Upstream, Upstream]]:
    """A real nginx in front of two recording stubs. ``body`` is `plain` or `tls`."""
    binary = locate_nginx()
    assert binary is not None
    api, web = Upstream("api"), Upstream("web")
    for stub in (api, web):
        threading.Thread(target=stub.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix="edge-gate-") as raw:
        home = Path(raw)
        for sub in ("body", "proxy", "fcgi", "uwsgi", "scgi"):
            (home / sub).mkdir()
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        servers = (
            render(plain, port=port, api=api.server_port, web=web.server_port)
            if body == "plain"
            else render(http_level(plain), port=port, api=api.server_port, web=web.server_port)
            + render(tls_body_as_plain(tls, port), port=port, api=api.server_port, web=web.server_port)
        )
        (home / "default.conf").write_text(servers)
        user = "user root;\n" if os.geteuid() == 0 else ""
        (home / "nginx.conf").write_text(
            f"{user}pid {home}/nginx.pid;\nerror_log {home}/error.log notice;\nevents {{ worker_connections 128; }}\n"
            f"http {{\n access_log {home}/access.log;\n client_body_temp_path {home}/body;\n"
            f" proxy_temp_path {home}/proxy;\n fastcgi_temp_path {home}/fcgi;\n uwsgi_temp_path {home}/uwsgi;\n"
            f" scgi_temp_path {home}/scgi;\n include {home}/default.conf;\n}}\n"
        )
        command = [binary, "-p", str(home), "-c", str(home / "nginx.conf"), "-e", str(home / "startup.log")]
        check = subprocess.run([*command, "-t"], capture_output=True, text=True)
        if check.returncode != 0:
            for stub in (api, web):
                stub.shutdown()
            raise RuntimeError(f"nginx -t refused the configuration: {check.stderr.strip()}")
        process = subprocess.Popen([*command, "-g", "daemon off;"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError("nginx exited at start: " + (process.stderr.read() or b"").decode())
                    time.sleep(0.05)
            else:
                raise RuntimeError("nginx did not listen within five seconds")
            yield Proxy(process, port, home), api, web
        finally:
            process.terminate()  # the PID this function started, and no other
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.stderr:
                process.stderr.close()
            for stub in (api, web):
                stub.shutdown()
                stub.server_close()


def _uploads(stub: Upstream) -> list[dict[str, Any]]:
    return [r for r in stub.seen if r["path"].endswith("/documents")]


def _expect_refusal(label: str, answer: Answer | None, status: int, code: str, retryable: bool) -> list[str]:
    if answer is None:
        return [f"{label}: nothing answered within {ANSWER_WITHIN} s (the proxy was waiting for the body)"]
    problems: list[str] = []
    if answer.status != status:
        problems.append(f"{label}: status {answer.status}, wanted {status}")
    if "json" not in answer.headers.get("content-type", ""):
        problems.append(f"{label}: content-type {answer.headers.get('content-type')!r} is not JSON")
    try:
        payload = answer.json()
    except ValueError:
        return problems + [f"{label}: the body is not JSON: {answer.body[:80]!r}"]
    if not isinstance(payload, dict) or payload.get("error_code") != code or payload.get("retryable") is not retryable:
        problems.append(f"{label}: body {payload!r} is not the {code} envelope")
    elif not re.fullmatch(r"[0-9a-f]{32}", str(payload.get("correlation_id"))):
        problems.append(f"{label}: correlation_id {payload.get('correlation_id')!r} is not nginx's request id")
    if answer.headers.get("x-content-type-options") != "nosniff":
        problems.append(f"{label}: the security headers are missing from the refusal")
    return problems


def credential_scenarios(proxy: Proxy, api: Upstream, web: Upstream, *, fast: bool = False) -> list[str]:
    """E-5: a stranger is refused with no body read; an authenticated caller arrives whole."""
    problems: list[str] = []
    port = proxy.port
    patience = FAST_ANSWER_WITHIN if fast else ANSWER_WITHIN

    def go(*args: Any, **kwargs: Any) -> Answer | None:
        return ask(*args, **{"wait": patience, **kwargs})

    for tier, path, stub, good in (
        ("api", UPLOAD_PATH_API, api, {"Authorization": GOOD_BEARER}),
        ("web", UPLOAD_PATH_BFF, web, {"Cookie": GOOD_COOKIE}),
    ):
        wrong = {"Authorization": "Bearer nobody"} if tier == "api" else {"Cookie": "am_session=nobody"}
        other = {"Cookie": GOOD_COOKIE} if tier == "api" else {"Authorization": GOOD_BEARER}
        first = len(stub.seen)
        # 1. nothing presented, 260 MiB declared, NOT ONE BODY BYTE sent: the refusal must come
        #    while the client is still silent. A proxy that reads the body first never answers.
        answer = go(port, "POST", path, declared=DECLARED_UPLOAD)
        problems += _expect_refusal(f"{tier}: no credential, 260 MiB declared, no body sent", answer, 401, "authentication_required", False)
        if problems and fast:
            return problems
        # 1b. no declared length at all: a chunked body announces a megabyte chunk and sends
        #     four kilobytes of it. `client_max_body_size` cannot refuse this one at the header.
        answer = go(port, "POST", path, headers={"Transfer-Encoding": "chunked"}, send=b"fffff\r\n" + b"x" * 4096)
        problems += _expect_refusal(f"{tier}: no credential, chunked, a partial chunk", answer, 401, "authentication_required", False)
        if problems and fast:
            return problems
        # 2. a credential that is wrong, and a megabyte of body actually on the wire.
        answer = go(port, "POST", path, headers=wrong, declared=DECLARED_UPLOAD, send=ONE_MEBIBYTE)
        problems += _expect_refusal(f"{tier}: wrong credential, 1 MiB of 260 MiB sent", answer, 401, "authentication_required", False)
        if problems and fast:
            return problems
        # 3. the other tier's credential is not this tier's.
        answer = go(port, "POST", path, headers=other, declared=DECLARED_UPLOAD)
        problems += _expect_refusal(f"{tier}: the other tier's credential", answer, 401, "authentication_required", False)
        if problems and fast:
            return problems
        if proxy.body_files():
            problems.append(f"{tier}: nginx wrote a temporary body file for a stranger: {proxy.body_files()}")
        if any(r["method"] == "POST" for r in stub.seen[first:]):
            problems.append(f"{tier}: an unauthenticated upload reached the application")
        reads = [r for r in stub.seen[first:] if r["path"] in ("/me", "/bff/v1/me")]
        if len(reads) != 4:
            problems.append(f"{tier}: four refused requests should cost four reads of the credential, saw {len(reads)}")
        for read in reads:
            if "content-length" in read["headers"] or read["received"]:
                problems.append(f"{tier}: the credential read carried a body or a declared length: {read['headers']}")
        if problems and fast:
            return problems
        # 4. an authenticated upload arrives whole, at the application's own path.
        before = len(stub.seen)
        body = ONE_MEBIBYTE * 3
        answer = go(port, "POST", path, headers=good, declared=body, send=body, wait=15)
        if answer is None or answer.status != 200 or answer.json() != {"received": body}:
            problems.append(f"{tier}: an authenticated upload did not arrive whole: {answer and (answer.status, answer.body[:80])}")
        arrived = [r for r in stub.seen[before:] if r["method"] == "POST"]
        expected_path = "/projects/prj_0123456789abcdef/documents" if tier == "api" else UPLOAD_PATH_BFF
        if [r["path"] for r in arrived] != [expected_path]:
            problems.append(f"{tier}: the upload reached {[r['path'] for r in arrived]}, wanted {expected_path!r}")
        # 5. a read on the same path is checked too, and the credential still passes it.
        answer = go(port, "GET", path, headers=good)
        if answer is None or answer.status != 200:
            problems.append(f"{tier}: an authenticated GET on the upload path was refused")
        # 6. a body DECLARED above the cap is refused at the header, whoever sends it.
        answer = go(port, "POST", path, declared=DECLARED_UPLOAD + 1)
        if answer is None or answer.status != 413:
            problems.append(f"{tier}: a body declared over 260m was not refused at once with 413")
    # 7. the internal locations are not addresses.
    for edge in ("/_edge/credential/api", "/_edge/credential/web"):
        before = len(api.seen) + len(web.seen)
        answer = go(port, "GET", edge, headers={"Authorization": GOOD_BEARER, "Cookie": GOOD_COOKIE})
        if answer is None or answer.status != 404 or len(api.seen) + len(web.seen) != before:
            problems.append(f"{edge}: reachable from outside ({answer and answer.status})")
    return problems


def throttle_scenarios(proxy: Proxy, api: Upstream, web: Upstream, *, fast: bool = False) -> list[str]:
    """E-4: the exchange is counted per address, apart from the registration budget."""
    problems: list[str] = []
    port = proxy.port
    patience = FAST_ANSWER_WITHIN if fast else ANSWER_WITHIN

    def go(*args: Any, **kwargs: Any) -> Answer | None:
        return ask(*args, **{"wait": patience, **kwargs})

    json_body = b'{"login":"admin","password":"wrong"}'
    headers = {"Content-Type": "application/json"}

    def exchange(path: str = "/api/v1/auth/token") -> Answer | None:
        return go(port, "POST", path, headers=headers, declared=len(json_body), send=json_body)

    statuses = [(exchange() or Answer(b"HTTP/1.1 0 \r\n\r\n", 0)).status for _ in range(10)]
    # the eleventh is spelled differently and must land in the same bucket (`$uri` is normalised)
    spelled = exchange("/api/v1//auth/token?x=1")
    statuses.append(spelled.status if spelled else 0)
    if statuses != [401] * 11:
        problems.append(f"the first eleven exchanges (the burst) were not all passed to the application: {statuses}")
    twelfth = exchange()
    problems += _expect_refusal("the twelfth exchange in a burst", twelfth, 429, "rate_limited", True)
    # the budget of the registration calls is untouched by it, and has its own twelfth.
    register = [
        (go(port, "POST", "/api/v1/registrations", headers=headers, declared=len(json_body), send=json_body) or Answer(b"HTTP/1.1 0 \r\n\r\n", 0)).status
        for _ in range(11)
    ]
    if register != [201] * 11:
        problems.append(f"registrations were throttled by the exchange's budget: {register}")
    problems += _expect_refusal(
        "the twelfth registration",
        go(port, "POST", "/api/v1/registrations", headers=headers, declared=len(json_body), send=json_body),
        429,
        "rate_limited",
        True,
    )
    # and the other direction: a spent registration budget leaves the exchange where it was (spent).
    problems += _expect_refusal("the exchange after both budgets are spent", exchange(), 429, "rate_limited", True)
    # nothing else on the origin is counted.
    for method, path in (("GET", "/api/v1/me"), ("GET", "/api/v1/auth/token"), ("POST", "/api/v1/projects")):
        answer = go(port, method, path, headers={"Authorization": GOOD_BEARER})
        if answer is None or answer.status == 429:
            problems.append(f"{method} {path} was throttled; only the exchange and the registration calls are")
    reached = [r["path"] for r in api.seen if r["path"].startswith("/auth/token")]
    if len(reached) < 11:
        problems.append(f"the application saw {len(reached)} exchanges, wanted the first eleven")
    return problems


def drive(plain: str, tls: str, *, body: str, fast: bool = False) -> list[str]:
    """Start nginx on this text and run every live scenario; return what was wrong."""
    with running(plain, tls, body=body) as (proxy, api, web):
        return credential_scenarios(proxy, api, web, fast=fast)


def drive_throttle(plain: str, tls: str, *, body: str, fast: bool = False) -> list[str]:
    with running(plain, tls, body=body) as (proxy, api, web):
        return throttle_scenarios(proxy, api, web, fast=fast)


needs_nginx = pytest.mark.skipif(
    locate_nginx() is None,
    reason="no nginx binary (AUDITMANAGER_NGINX_BIN, PATH, /usr/sbin/nginx): the live half is not run; the static half still is",
)


@needs_nginx
@pytest.mark.parametrize("body", ["plain", "tls"])
def test_a_stranger_is_refused_before_the_body_live(body: str) -> None:
    assert drive(PLAIN.read_text(), TLS_BLOCK.read_text(), body=body) == []


@needs_nginx
@pytest.mark.parametrize("body", ["plain", "tls"])
def test_the_token_exchange_is_counted_per_address_live(body: str) -> None:
    assert drive_throttle(PLAIN.read_text(), TLS_BLOCK.read_text(), body=body) == []


#: Which live driver sees which mutation. Every mutation above must be seen by at least one.
CREDENTIAL_MUTATIONS = {
    "the api upload location stops asking": "plain",
    "the web upload location stops asking": "plain",
    "the tls api upload location stops asking": "tls",
    "the tls web upload location stops asking": "tls",
    "the api upload location asks the web tier": "plain",
    "the api refusal is nginx's HTML page": "plain",
    "the credential location can be asked for from outside": "plain",
    "the credential location falls back to the server's cap": "plain",
    "the credential subrequest forwards the declared length": "tls",
    "the credential subrequest asks a different read": "tls",
}
THROTTLE_MUTATIONS = {
    "the token limit is gone from the api location": "plain",
    "the token limit is gone from the tls api location": "tls",
    "the token zone is keyed by the registration map": "plain",
    "the token key no longer names the exchange": "plain",
    "the token key widened to every post": "plain",
    "the token key is the whole address space": "plain",
}


@needs_nginx
@pytest.mark.parametrize("case", sorted(CREDENTIAL_MUTATIONS))
def test_each_live_credential_guard_can_fail(case: str) -> None:
    plain, tls = mutated(case, PLAIN.read_text(), TLS_BLOCK.read_text())
    assert drive(plain, tls, body=CREDENTIAL_MUTATIONS[case], fast=True) != [], f"{case}: the live guard stayed green"


@needs_nginx
@pytest.mark.parametrize("case", sorted(THROTTLE_MUTATIONS))
def test_each_live_throttle_guard_can_fail(case: str) -> None:
    plain, tls = mutated(case, PLAIN.read_text(), TLS_BLOCK.read_text())
    assert drive_throttle(plain, tls, body=THROTTLE_MUTATIONS[case], fast=True) != [], f"{case}: the live guard stayed green"
