"""`W49-EDGE-01` -- the guest throttle at the proxy, held to the catalog and to the contract.

`W49-PLAN.md` section 3.5: `/api/v1/` is public behind nginx, so the edge limits
`POST /api/v1/registrations` and `POST /api/v1/registrations/status` per client address and
answers the excess with the catalog's `rate_limited` envelope. `HARDEN-AUTH-EDGE-01`
(`EXPOSURE-REVIEW-01` `E-4`, `D-192`) adds the credential exchange, `POST /api/v1/auth/token`,
to the same edge, in a zone of its own so the two budgets cannot spend each other. The `web` service is told
it runs behind that proxy (`AUDITMANAGER_BEHIND_PROXY`), so the web tier may key its own
guest bucket on the `X-Real-IP` the proxy sets.

**What this file reads, and why three files.** The throttle lives in both server bodies --
`nginx.conf` is always loaded and `tls-server.conf` is copied beside it when a certificate
exists -- and the flag lives in `compose.server.yml`. Any one of the three can lose its line
while the other two still look right, so each is read and each is checked:

* the `map`s and their `limit_req_zone`s are http-level, declared **once**, in
  `nginx.conf`, and never in `tls-server.conf` (a second declaration stops nginx from
  starting). `EXEC-PULL-01` adds two pairs, the runner channel's: one counts each runner TOKEN
  (the key is the token's twelve-character prefix, read out of the `Authorization` header of a
  call to `/api/v1/runner/tasks/...`; it is empty for everything else), one counts each address
  for the same paths. Their maps are read as patterns and **run against the contract's own
  runner paths**: a call with a well-formed token yields exactly the prefix, a user's credential
  or no credential yields none, and no other path yields anything;
* each map keys exactly the calls the frozen OpenAPI document names for its zone -- the two
  registration calls for `guest_registration`, `issueToken` for `token_exchange` -- by
  method and by the full served path, and nothing else -- no regex key, no prefix;
* both server bodies throttle inside the existing `location /api/v1/` and in the one other
  API location there is -- `W55B-STREAM-01`'s upload location, which a regex match takes out
  of the prefix location and which therefore repeats the same throttle lines -- and nowhere
  else, with no other `/api/v1` location;
* the two upload locations (`/api/v1/projects/*/documents` and `/bff/v1/projects/*/documents`,
  each also matching `.../documents/*/versions` since `W59-VERSION-UPLOAD-01`) are the only
  places `client_max_body_size` is raised, to `260m` -- except the two internal credential
  locations `HARDEN-AUTH-EDGE-01` added, which repeat that cap because a subrequest re-checks
  the declared length (`tests/integration/composition/test_edge_credential_gate.py` holds
  everything else about them) -- with the explicit timeouts
  the plan fixes, the `rewrite` and the URI-less `proxy_pass` the API one needs, and neither
  declares a header of its own (that would drop the server's security headers);
* the named location both bodies send a 429 to returns JSON whose `error_code`,
  `retryable`, status, message and `contract_version` are the catalog's for `rate_limited`,
  whose correlation id is nginx's per-request `$request_id`, and which a real Draft 2020-12
  validator accepts against `error-envelope.schema.json`;
* the `web` service, and only it, sets the proxy flag to `1` in its `environment`.

**What it cannot prove.** That nginx loads this configuration and refuses the excess. That
was driven against the pinned image -- `nginx -t` with both files under `conf.d/` and a
throwaway certificate pair, and a running container answering the twelfth registration in a
burst with this envelope -- and is recorded with its commands and output in
`docs/program/W49-EDGE-01.md`. It needs a daemon, which the battery does not have.

**Every check here is shown able to fail**, in `test_each_check_can_fail`, by putting a
mutation in front of the same function the real check uses.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import pytest

from auditmanager.shared.errors import screen_message

ROOT = Path(__file__).resolve().parents[2]
PROXY = ROOT / "infra" / "deploy" / "proxy"
PLAIN = PROXY / "nginx.conf"
TLS_BLOCK = PROXY / "tls-server.conf"
COMPOSE = ROOT / "infra" / "deploy" / "compose.server.yml"
CATALOG = ROOT / "contracts" / "domain" / "v1" / "error-codes.json"
ENVELOPE_SCHEMA = ROOT / "contracts" / "domain" / "v1" / "error-envelope.schema.json"
OPENAPI = ROOT / "contracts" / "api" / "v1" / "openapi.json"
GOVERNANCE_PYTHON = ROOT / ".venv" / "bootstrap" / "bin" / "python"

#: The catalog code the edge answers with. The only literal for it in this file; every
#: property it must carry is read out of the catalog.
CODE = "rate_limited"
#: The operations the plan throttles, by `operationId`. Their method and path are read out of
#: the frozen document, so the expected map keys are not written down here a second time.
THROTTLED_OPERATIONS = frozenset({"submitRegistration", "readRegistrationStatus"})
#: `HARDEN-AUTH-EDGE-01`. The credential exchange has a zone of its own.
EXCHANGE_OPERATIONS = frozenset({"issueToken"})
#: `EXEC-PULL-01`. The four operations a runner calls with a runner token, by `operationId`; the
#: runner-channel maps are held against their full served paths.
RUNNER_OPERATIONS = frozenset({
    "claimExecutorTask", "extendExecutorTaskClaim", "submitExecutorTaskAnswer",
    "failExecutorTask", "getExecutorTaskImage",
})
#: The runner channel's two zones and the exact lines that declare them: the rates are the
#: decision (`docs/program/EXEC-PULL-01.md` replays a scripted runner against them), so they are
#: written out here and not read back from the file under test.
RUNNER_ZONE_LINES = {
    "runner_channel": "limit_req_zone $runner_token_client zone=runner_channel:1m rate=60r/m;",
    "runner_address": "limit_req_zone $runner_address_client zone=runner_address:1m rate=300r/m;",
}
RUNNER_TOKEN_MAP_HEADER = 'map "$uri|$http_authorization" $runner_token_client {'
RUNNER_ADDRESS_MAP_HEADER = "map $uri $runner_address_client {"
RUNNER_LIMIT_LINES = (
    "limit_req zone=runner_channel burst=30 nodelay;",
    "limit_req zone=runner_address burst=120 nodelay;",
)
#: zone name -> the operations whose full served path the zone's map keys on.
ZONES: dict[str, frozenset[str]] = {
    "guest_registration": THROTTLED_OPERATIONS,
    "token_exchange": EXCHANGE_OPERATIONS,
}
MAP_HEADER = re.compile(r'^map "\$request_method:\$uri" (\$\w+) \{$')
ZONE_LINE = re.compile(r"^limit_req_zone (\$\w+) zone=(\w+):\d+[km] rate=\d+r/[sm];$")
LIMIT_LINE = re.compile(r"^limit_req zone=(\w+) burst=\d+( nodelay)?;$")
RETURN_LINE = re.compile(r"^return (\d{3}) '(.*)';$")
CLIENT_ADDRESS = "$binary_remote_addr"
NAMED_LOCATION = "@rate_limited"
#: `W55B-STREAM-01`. The two regex locations that take the larger body, written out.
UPLOAD_API_LOCATION = "location ~ ^/api/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {"
UPLOAD_BFF_LOCATION = "location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {"
API_LOCATIONS = frozenset(
    {"location = /api/v1 {", "location /api/v1/ {", UPLOAD_API_LOCATION}
)
#: What the two upload locations say about size and time, and the default beside them.
UPLOAD_BODY_CAP = "client_max_body_size 260m;"
DEFAULT_BODY_CAP = "client_max_body_size 32m;"
#: The two internal credential locations repeat the upload cap (see the module note).
CREDENTIAL_LOCATIONS = ("location = /_edge/credential/api {", "location = /_edge/credential/web {")
UPLOAD_TIMEOUTS = ("client_body_timeout 120s;", "proxy_read_timeout 300s;")
UPLOAD_REWRITE = "rewrite ^/api/v1/(.*)$ /$1 break;"
HEADER_DIRECTIVES = ("add_header ", "proxy_set_header ")
PROXY_FLAG = "AUDITMANAGER_BEHIND_PROXY"
#: The shape of nginx's `$request_id`: 32 hexadecimal digits, fresh for every request.
SAMPLE_REQUEST_ID = "0123456789abcdef0123456789abcdef"


# ---------------------------------------------------------------------------------------
# Reading the files
# ---------------------------------------------------------------------------------------


def statements(config: str) -> list[str]:
    """Every non-comment line of an nginx file, stripped, in order.

    A `#` ends the line, as it does for nginx outside a quoted string -- the same rule
    `test_proxy_tls_path.py`'s drift check applies, which is why the envelope must never
    carry one. Inner spacing is kept, so a quoted body is read byte for byte.
    """
    out: list[str] = []
    for raw in config.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _norm(line: str) -> str:
    return " ".join(line.split())


def blocks(lines: list[str], header: str) -> list[list[str]]:
    """The inner lines of every block whose opening line is exactly ``header``."""
    found: list[list[str]] = []
    for index, line in enumerate(lines):
        if _norm(line) != header:
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


def top_level(lines: list[str]) -> list[str]:
    """The lines outside every block -- in a `conf.d/` file, the http-level directives."""
    out: list[str] = []
    depth = 0
    for line in lines:
        if depth == 0:
            out.append(line)
        if line.endswith("{"):
            depth += 1
        elif line == "}":
            depth -= 1
    return out


def _map_entries(inner: list[str]) -> dict[str, str]:
    """`key value;` pairs, quotes removed. Anything else -- `hostnames;`, `include ...;`,
    a three-token line -- is kept whole under a marker value, so it can never compare equal
    to the expected mapping."""
    entries: dict[str, str] = {}
    for line in inner:
        tokens = shlex.split(line.rstrip(";"))
        if len(tokens) == 2:
            entries[tokens[0]] = tokens[1]
        else:
            entries[line] = "<not a key and a value>"
    return entries


def service_blocks(compose: str) -> dict[str, list[str]]:
    """The lines of each service under ``services:``, comments included, keyed by name."""
    lines = compose.splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "services:")
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1 :]:
        if line.strip() and not line.lstrip().startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break
            if indent == 2 and line.rstrip().endswith(":"):
                current = line.strip().rstrip(":")
                found[current] = []
                continue
        if current is not None:
            found[current].append(line)
    return found


def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _schema() -> dict[str, Any]:
    return json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))


def expected_map_keys(operations: frozenset[str] = THROTTLED_OPERATIONS) -> dict[str, str]:
    """`METHOD:/api/v1<path>` for each throttled operation, read out of the frozen document."""
    document = json.loads(OPENAPI.read_text(encoding="utf-8"))
    base = document["servers"][0]["url"]
    keys = {
        f"{method.upper()}:{base}{path}": CLIENT_ADDRESS
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if isinstance(operation, dict) and operation.get("operationId") in operations
    }
    assert len(keys) == len(operations), (
        f"the frozen document no longer names every throttled operation: {sorted(keys)}"
    )
    return keys


# ---------------------------------------------------------------------------------------
# The checks -- each returns what is wrong, so the same function can be shown to fail
# ---------------------------------------------------------------------------------------


def declaration_problems(plain: str, tls: str) -> list[str]:
    """The maps and the zones: once each, at http level, in the always-loaded file, keyed exactly."""
    problems: list[str] = []
    lines = statements(plain)
    declared = len(ZONES) + len(RUNNER_ZONE_LINES)
    runner_headers = {RUNNER_TOKEN_MAP_HEADER, RUNNER_ADDRESS_MAP_HEADER}
    maps = [line for line in lines if line.startswith("map ")]
    zones = [line for line in lines if line.startswith("limit_req_zone ")]
    outer = top_level(lines)
    if len(maps) != declared or any(line not in outer for line in maps):
        return [f"nginx.conf must declare exactly {declared} maps, at http level: {maps}"]
    if len(zones) != declared or any(line not in outer for line in zones):
        return [f"nginx.conf must declare exactly {declared} limit_req_zones, at http level: {zones}"]
    by_name: dict[str, tuple[str, str]] = {}
    for zone_line in zones:
        zone = ZONE_LINE.match(_norm(zone_line))
        if zone is None:
            problems.append(f"the limit_req_zone is not the expected shape: {zone_line!r}")
            continue
        by_name[zone.group(2)] = (zone.group(1), zone_line)
    if sorted(by_name) != sorted([*ZONES, *RUNNER_ZONE_LINES]):
        return problems + [
            f"the zones must be exactly {sorted([*ZONES, *RUNNER_ZONE_LINES])}: {sorted(by_name)}"
        ]
    for name, operations in ZONES.items():
        variable, _ = by_name[name]
        keyed = [line for line in maps if (m := MAP_HEADER.match(_norm(line))) and m.group(1) == variable]
        if len(keyed) != 1:
            problems.append(
                f'zone {name} counts {variable}, which must be yielded by exactly one map keyed by '
                f'"$request_method:$uri": {keyed}'
            )
            continue
        (inner,) = blocks(lines, _norm(keyed[0]))
        entries = _map_entries(inner)
        wanted = {"default": "", **expected_map_keys(operations)}
        if entries != wanted:
            problems.append(
                f"the {name} map must yield the client address for exactly its own calls and "
                f"the empty string otherwise; it reads {entries}, expected {wanted}"
            )
    for line in maps:
        if MAP_HEADER.match(_norm(line)) is None and _norm(line) not in runner_headers:
            problems.append(f'a map is not keyed by "$request_method:$uri": {line!r}')
    for line in statements(tls):
        if line.startswith(("map ", "limit_req_zone ")):
            problems.append(
                "tls-server.conf declares an http-level throttle directive; nginx loads it "
                f"beside nginx.conf, so this is a duplicate that stops the master: {line!r}"
            )
    return problems


def _python_regex(nginx_key: str) -> re.Pattern[str]:
    """An nginx ``map`` regex key (``~`` and PCRE named groups) as a Python pattern."""
    assert nginx_key.startswith("~") and not nginx_key.startswith("~*"), nginx_key
    return re.compile(nginx_key[1:].replace("(?<", "(?P<"))


def runner_problems(plain: str) -> list[str]:
    """`EXEC-PULL-01`: the runner channel's zones and maps, run against the contract's paths."""
    problems: list[str] = []
    lines = statements(plain)
    for name, wanted in RUNNER_ZONE_LINES.items():
        if wanted not in [_norm(line) for line in lines]:
            problems.append(f"nginx.conf lacks the declaration {wanted!r}")
    document = json.loads(OPENAPI.read_text(encoding="utf-8"))
    base = document["servers"][0]["url"]
    paths = {
        operation["operationId"]: f"{base}{path}"
        for path, item in document["paths"].items()
        for operation in item.values()
        if isinstance(operation, dict) and operation.get("operationId") in RUNNER_OPERATIONS
    }
    if set(paths) != RUNNER_OPERATIONS:
        return problems + [f"the frozen document no longer names every runner operation: {paths}"]
    served = [path.replace("{task_id}", "ext_01M2545JSD15ETSNNV904X991K") for path in paths.values()]
    prefix = "amr_ab12cd34"
    token = f"{prefix}_" + "x" * 43

    token_map = blocks(lines, RUNNER_TOKEN_MAP_HEADER)
    if len(token_map) != 1:
        return problems + [f"expected one {RUNNER_TOKEN_MAP_HEADER!r}, found {len(token_map)}"]
    entries = _map_entries(token_map[0])
    regexes = {key: value for key, value in entries.items() if key != "default"}
    if entries.get("default") != "" or len(regexes) != 1:
        problems.append(f"the runner token map must hold a default of \"\" and one pattern: {entries}")
    else:
        ((key, value),) = regexes.items()
        try:
            pattern = _python_regex(key)
        except (AssertionError, re.error) as error:
            return problems + [f"the runner token map key is not a usable pattern: {error}"]
        group = re.findall(r"\(\?<(\w+)>", key)
        if len(group) != 1 or value != f"${group[0]}":
            problems.append(f"the runner token map must yield its one named group, not {value!r}")
        for uri in served:
            hit = pattern.match(f"{uri}|Bearer {token}")
            if hit is None or hit.group(group[0] if group else 0) != prefix:
                problems.append(f"{uri} with a runner token must be keyed on its prefix")
            if pattern.match(f"{uri}|") or pattern.match(f"{uri}|Bearer am2.payload.tag"):
                problems.append(f"{uri} without a runner token must have no key")
        for uri in (f"{base}/projects", f"{base}/executor-connections", f"{base}/runner/tasks",
                    f"{base}/runner/other/claim", "/bff/v1/runner/tasks/claim"):
            if pattern.match(f"{uri}|Bearer {token}"):
                problems.append(f"{uri} is not a runner path and must have no key")
    address_map = blocks(lines, RUNNER_ADDRESS_MAP_HEADER)
    if len(address_map) != 1:
        return problems + [f"expected one {RUNNER_ADDRESS_MAP_HEADER!r}, found {len(address_map)}"]
    entries = _map_entries(address_map[0])
    regexes = {key: value for key, value in entries.items() if key != "default"}
    if entries.get("default") != "" or len(regexes) != 1:
        problems.append(f"the runner address map must hold a default of \"\" and one pattern: {entries}")
    else:
        ((key, value),) = regexes.items()
        if value != CLIENT_ADDRESS:
            problems.append(f"the runner address map must yield the client address: {value!r}")
        try:
            pattern = _python_regex(key)
        except (AssertionError, re.error) as error:
            return problems + [f"the runner address map key is not a usable pattern: {error}"]
        for uri in served:
            if pattern.match(uri) is None:
                problems.append(f"{uri} must be counted per address")
        for uri in (f"{base}/projects", f"{base}/runner", f"{base}/auth/token", "/healthz"):
            if pattern.match(uri):
                problems.append(f"{uri} is not a runner path and must not be counted per address")
    return problems


def runner_limit_problems(name: str, config: str) -> list[str]:
    """Both server bodies carry the runner limits at the rates the zones were sized for, in the
    one `location /api/v1/` (the upload location repeats them; ``throttle_problems`` holds that),
    and no ``auth_request`` stands in front of the runner paths: the token is the credential."""
    lines = statements(config)
    (prefixed,) = blocks(lines, "location /api/v1/ {")
    inner = [_norm(line) for line in prefixed]
    problems = [
        f"{name}: `location /api/v1/` lacks {needed!r}"
        for needed in RUNNER_LIMIT_LINES if needed not in inner
    ]
    if any(line.startswith("auth_request") for line in inner):
        problems.append(f"{name}: `location /api/v1/` must not gate the runner paths on a session")
    return problems


def zone_names(plain: str) -> list[str]:
    """The declared zones, in file order."""
    names: list[str] = []
    for line in statements(plain):
        match = ZONE_LINE.match(_norm(line))
        if match:
            names.append(match.group(2))
    return names


def throttle_problems(name: str, config: str, zones: list[str], status: int) -> list[str]:
    """One server body: the limits inside the one `location /api/v1/`, and nowhere else."""
    problems: list[str] = []
    lines = statements(config)
    api = [_norm(line) for line in lines if line.startswith("location") and "/api/v1" in line]
    if sorted(api) != sorted(API_LOCATIONS):
        problems.append(
            f"{name}: the /api/v1 locations must be exactly {sorted(API_LOCATIONS)}: {api}"
        )
    prefixed = blocks(lines, "location /api/v1/ {")
    if len(prefixed) != 1:
        return problems + [f"{name}: expected one `location /api/v1/` block, found {len(prefixed)}"]
    inner = [_norm(line) for line in prefixed[0]]
    limits = [line for line in inner if line.startswith("limit_req ")]
    if len(limits) != len(zones):
        problems.append(
            f"{name}: `location /api/v1/` carries {len(limits)} limit_req lines, one per zone "
            f"{zones} is expected"
        )
    used: list[str | None] = []
    for line in limits:
        match = LIMIT_LINE.match(line)
        used.append(match.group(1) if match else None)
        if match is None or match.group(1) not in zones:
            problems.append(f"{name}: {line!r} does not use a declared zone {zones!r}")
    if sorted(zone for zone in used if zone) != sorted(zones):
        problems.append(f"{name}: `location /api/v1/` limits zones {used}, expected each of {zones}")
    for needed in (f"limit_req_status {status};", f"error_page {status} = {NAMED_LOCATION};"):
        if needed not in inner:
            problems.append(f"{name}: `location /api/v1/` lacks {needed!r}")
    uploads = blocks(lines, UPLOAD_API_LOCATION)
    if len(uploads) != 1:
        return problems + [
            f"{name}: expected one `{UPLOAD_API_LOCATION}` block, found {len(uploads)}"
        ]
    upload_inner = [_norm(line) for line in uploads[0]]
    # `error_page 429` and not every `error_page`: the upload locations also answer a 401 of
    # their own (`HARDEN-AUTH-EDGE-01`, held by test_edge_credential_gate.py).
    for prefix in ("limit_req ", "limit_req_status ", f"error_page {status} "):
        everywhere = [line for line in lines if line.startswith(prefix)]
        inside = [line for line in inner if line.startswith(prefix)]
        inside_upload = [line for line in upload_inner if line.startswith(prefix)]
        if len(everywhere) != len(inside) + len(inside_upload):
            problems.append(
                f"{name}: a `{prefix.strip()}` outside the two API locations that proxy "
                f"every `/api/v1/` request would reach requests the plan never throttles: "
                f"{everywhere}"
            )
        if inside != inside_upload:
            problems.append(
                f"{name}: the upload location must repeat `location /api/v1/`'s "
                f"`{prefix.strip()}` lines exactly: {inside} against {inside_upload}"
            )
    return problems


def upload_location_problems(name: str, config: str) -> list[str]:
    """The two upload locations: the only larger body, the explicit timeouts, no header."""
    problems: list[str] = []
    lines = statements(config)
    normalised = [_norm(line) for line in lines]
    caps = [line for line in normalised if line.startswith("client_max_body_size ")]
    if sorted(caps) != sorted([DEFAULT_BODY_CAP] + [UPLOAD_BODY_CAP] * 4):
        problems.append(
            f"{name}: `client_max_body_size` must be 32m once at server level and 260m in "
            f"the two upload locations and the two credential locations beside them, and "
            f"nowhere else: {caps}"
        )
    for credential in CREDENTIAL_LOCATIONS:
        held = blocks(lines, credential)
        if len(held) != 1 or [_norm(x) for x in held[0] if x.startswith("client_max_body_size ")] != [UPLOAD_BODY_CAP]:
            problems.append(f"{name}: `{credential}` must hold exactly the upload cap {UPLOAD_BODY_CAP!r}")
    server_level = top_level(blocks(lines, "server {")[0])
    if DEFAULT_BODY_CAP not in [_norm(line) for line in server_level]:
        problems.append(f"{name}: the server-wide default is no longer {DEFAULT_BODY_CAP!r}")
    for header, proxy in ((UPLOAD_API_LOCATION, "proxy_pass http://api:8000;"),
                          (UPLOAD_BFF_LOCATION, "proxy_pass http://web:3000;")):
        found = blocks(lines, header)
        if len(found) != 1:
            problems.append(f"{name}: expected one `{header}`, found {len(found)}")
            continue
        inner = [_norm(line) for line in found[0]]
        for needed in (UPLOAD_BODY_CAP, *UPLOAD_TIMEOUTS, proxy):
            if needed not in inner:
                problems.append(f"{name}: `{header}` lacks {needed!r}")
        proxies = [line for line in inner if line.startswith("proxy_pass ")]
        if proxies != [proxy]:
            problems.append(
                f"{name}: `{header}` must proxy with the URI-less {proxy!r}, "
                f"a URI is ignored after a rewrite: {proxies}"
            )
        for directive in HEADER_DIRECTIVES:
            if any(line.startswith(directive) for line in inner):
                problems.append(
                    f"{name}: `{header}` declares `{directive.strip()}`, which drops every "
                    "header inherited from the server level"
                )
        if header == UPLOAD_API_LOCATION:
            if UPLOAD_REWRITE not in inner:
                problems.append(f"{name}: `{header}` does not strip the prefix: {UPLOAD_REWRITE!r}")
            redirects = [line for line in inner if line.startswith("proxy_redirect ")]
            prefix_block = blocks(lines, "location /api/v1/ {")
            wanted = (
                [_norm(l) for l in prefix_block[0] if l.startswith("proxy_redirect ")]
                if prefix_block
                else []
            )
            if not wanted or redirects != wanted:
                problems.append(
                    f"{name}: `{header}` must repeat `location /api/v1/`'s proxy_redirect: "
                    f"{redirects} against {wanted}"
                )
    return problems


def envelope_of(
    name: str, config: str, location: str = NAMED_LOCATION
) -> tuple[list[str], int | None, dict[str, Any] | None]:
    """The status and the parsed body the named location returns, or why there are none."""
    named = blocks(statements(config), f"location {location} {{")
    if len(named) != 1:
        return [f"{name}: expected one `location {location}`, found {len(named)}"], None, None
    problems: list[str] = []
    if "default_type application/json;" not in [_norm(line) for line in named[0]]:
        problems.append(f"{name}: {NAMED_LOCATION} does not answer as application/json")
    returns = [RETURN_LINE.match(line) for line in named[0] if line.startswith("return ")]
    if len(returns) != 1 or returns[0] is None:
        shape = f"{name}: {NAMED_LOCATION} must hold one `return <status> '<json>';`"
        return problems + [shape], None, None
    status, body = int(returns[0].group(1)), returns[0].group(2)
    variables = re.findall(r"\$\{?\w+", body)
    if variables != ["$request_id"]:
        problems.append(
            f"{name}: the body must interpolate $request_id and nothing else: {variables}"
        )
    try:
        payload = json.loads(body.replace("$request_id", SAMPLE_REQUEST_ID))
    except json.JSONDecodeError as exc:
        return problems + [f"{name}: the body is not JSON: {exc}"], status, None
    if not isinstance(payload, dict):
        return problems + [f"{name}: the body is not a JSON object"], status, None
    return problems, status, payload


def envelope_problems(name: str, config: str) -> list[str]:
    """The refusal carries exactly what the catalog says `rate_limited` carries."""
    problems, status, payload = envelope_of(name, config)
    if payload is None:
        return problems
    catalog = _catalog()
    schema = _schema()
    entry = catalog["codes"].get(CODE)
    if entry is None:  # pragma: no cover - the catalog lost the code; nothing else holds
        return problems + [f"the catalog has no {CODE!r}"]
    if payload.get("error_code") != CODE:
        problems.append(f"{name}: error_code is {payload.get('error_code')!r}, not {CODE!r}")
    if payload.get("error_code") not in catalog["codes"]:
        problems.append(f"{name}: error_code {payload.get('error_code')!r} is not a catalog code")
    if status != entry["http"]:
        problems.append(f"{name}: returns {status}; the catalog gives {CODE} {entry['http']}")
    if payload.get("retryable") is not entry["retryable"]:
        problems.append(
            f"{name}: retryable is {payload.get('retryable')!r}; "
            f"the catalog pins {entry['retryable']!r}"
        )
    if payload.get("contract_version") != catalog["contract_version"]:
        problems.append(
            f"{name}: contract_version {payload.get('contract_version')!r} is not the catalog's"
        )
    if payload.get("contract_version") != schema["properties"]["contract_version"]["const"]:
        problems.append(f"{name}: contract_version is not the envelope schema's const")
    if payload.get("message") != entry["summary"]:
        problems.append(
            f"{name}: the message is not {CODE}'s catalog summary, which is what the "
            f"application sends when no call site supplies one: {payload.get('message')!r}"
        )
    try:
        screen_message(str(payload.get("message", "")))
    except ValueError as exc:
        problems.append(f"{name}: the message fails the envelope screen: {exc}")
    if payload.get("correlation_id") != SAMPLE_REQUEST_ID:
        problems.append(
            f"{name}: correlation_id is not nginx's $request_id: "
            f"{payload.get('correlation_id')!r}"
        )
    expected_keys = set(schema["required"]) | ({"details"} if entry["safe_detail_keys"] else set())
    if set(payload) != expected_keys:
        problems.append(
            f"{name}: the envelope carries {sorted(payload)}; the schema requires "
            f"{sorted(schema['required'])} and {CODE} declares no safe detail key"
        )
    return problems


def flag_problems(compose: str) -> list[str]:
    """`AUDITMANAGER_BEHIND_PROXY: "1"` in the web service's environment, and nowhere else."""
    services = service_blocks(compose)
    problems: list[str] = []
    if "web" not in services:
        return [f"compose.server.yml has no web service: {sorted(services)}"]
    for name, body in services.items():
        section: str | None = None
        hits: list[tuple[str | None, str]] = []
        for line in body:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 4:
                section = stripped.split(":", 1)[0]
            if stripped.startswith(f"{PROXY_FLAG}:") or stripped.startswith(f"- {PROXY_FLAG}="):
                hits.append((section, stripped))
        if name != "web":
            if hits:
                problems.append(f"{name} sets {PROXY_FLAG}; only the web tier reads it: {hits}")
            continue
        if len(hits) != 1:
            problems.append(f"the web service sets {PROXY_FLAG} {len(hits)} times: {hits}")
            continue
        section, stripped = hits[0]
        value = stripped.split(":", 1)[1].split(" #", 1)[0].strip().strip("\"'")
        if section != "environment" or value != "1":
            problems.append(
                f"the web service must set {PROXY_FLAG} to 1 in its environment; "
                f"found {stripped!r} under {section!r}"
            )
    return problems


# ---------------------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------------------


def _texts() -> dict[str, str]:
    return {
        "nginx.conf": PLAIN.read_text(encoding="utf-8"),
        "tls-server.conf": TLS_BLOCK.read_text(encoding="utf-8"),
        "compose.server.yml": COMPOSE.read_text(encoding="utf-8"),
    }


def all_problems(texts: dict[str, str]) -> list[str]:
    plain, tls = texts["nginx.conf"], texts["tls-server.conf"]
    status = _catalog()["codes"][CODE]["http"]
    zones = zone_names(plain)
    problems = declaration_problems(plain, tls)
    problems += runner_problems(plain)
    for name in ("nginx.conf", "tls-server.conf"):
        problems += throttle_problems(name, texts[name], zones, status)
        problems += runner_limit_problems(name, texts[name])
        problems += upload_location_problems(name, texts[name])
        problems += envelope_problems(name, texts[name])
    for header in (UPLOAD_API_LOCATION, UPLOAD_BFF_LOCATION):
        if blocks(statements(plain), header) != blocks(statements(tls), header):
            problems.append(f"the two `{header}` locations differ")
    if blocks(statements(plain), f"location {NAMED_LOCATION} {{") != blocks(
        statements(tls), f"location {NAMED_LOCATION} {{"
    ):
        problems.append(f"the two {NAMED_LOCATION} locations differ")
    problems += flag_problems(texts["compose.server.yml"])
    return problems


def test_the_map_and_the_zone_are_declared_once_in_the_file_nginx_always_loads() -> None:
    texts = _texts()
    assert declaration_problems(texts["nginx.conf"], texts["tls-server.conf"]) == []


@pytest.mark.parametrize("name", ["nginx.conf", "tls-server.conf"])
def test_the_server_body_throttles_inside_the_one_api_location(name: str) -> None:
    texts = _texts()
    zones = zone_names(texts["nginx.conf"])
    assert sorted(zones) == sorted([*ZONES, *RUNNER_ZONE_LINES])
    status = _catalog()["codes"][CODE]["http"]
    assert throttle_problems(name, texts[name], zones, status) == []


@pytest.mark.parametrize("name", ["nginx.conf", "tls-server.conf"])
def test_the_refusal_is_the_catalog_rate_limited_envelope(name: str) -> None:
    assert envelope_problems(name, _texts()[name]) == []


@pytest.mark.parametrize("name", ["nginx.conf", "tls-server.conf"])
def test_the_upload_locations_alone_take_the_larger_body(name: str) -> None:
    assert upload_location_problems(name, _texts()[name]) == []


def test_the_web_service_runs_behind_the_proxy_flag() -> None:
    assert flag_problems(_texts()["compose.server.yml"]) == []


def test_the_whole_guard_is_green() -> None:
    """The composition the mutation cases below are run against, so a mutation that turns
    red is red against a baseline shown here to be green."""
    assert all_problems(_texts()) == []


_VALIDATE = """
import json, sys
from jsonschema import Draft202012Validator
job = json.load(sys.stdin)
validator = Draft202012Validator(job["schema"])
print(json.dumps({name: sorted(error.message for error in validator.iter_errors(payload))
                  for name, payload in job["payloads"].items()}))
"""


def test_the_envelope_validates_against_the_envelope_schema() -> None:
    """A real Draft 2020-12 validator, not a re-implementation of the schema's rules.

    `jsonschema` lives only in the governance environment, so it is driven through that
    interpreter, as `tests/contract/api_v1/conftest.py` does. A missing interpreter is an
    error, never a skip. The negative payload is the control: a validator that accepted it
    would make the positive result worthless.
    """
    if not GOVERNANCE_PYTHON.exists():
        raise AssertionError(
            f"the governance interpreter is missing at {GOVERNANCE_PYTHON}. "
            "Run: make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12"
        )
    texts = _texts()
    payloads: dict[str, Any] = {}
    for name in ("nginx.conf", "tls-server.conf"):
        problems, _, payload = envelope_of(name, texts[name])
        assert problems == [] and payload is not None, problems
        payloads[name] = payload
    for name in ("nginx.conf", "tls-server.conf"):
        problems, _, payload = envelope_of(name, texts[name], "@authentication_required")
        assert problems == [] and payload is not None, problems
        payloads[f"{name} authentication_required"] = payload
    payloads["control: retryable false"] = {**payloads["nginx.conf"], "retryable": False}
    completed = subprocess.run(
        [str(GOVERNANCE_PYTHON), "-c", _VALIDATE],
        input=json.dumps({"schema": _schema(), "payloads": payloads}),
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    verdicts = json.loads(completed.stdout)
    assert verdicts["nginx.conf"] == [] and verdicts["tls-server.conf"] == [], verdicts
    for name in ("nginx.conf", "tls-server.conf"):
        assert verdicts[f"{name} authentication_required"] == [], verdicts
    assert verdicts["control: retryable false"], (
        "the validator accepted a retryable the schema pins"
    )


#: (case, file, the exact text replaced, its replacement). Each `old` is asserted present,
#: so a mutation that silently matched nothing cannot pass for a guard that fired.
MUTATIONS = [
    (
        "the limit removed from nginx.conf",
        "nginx.conf",
        "        limit_req zone=guest_registration burst=10 nodelay;\n",
        "",
    ),
    (
        "the limit removed from tls-server.conf",
        "tls-server.conf",
        "        limit_req zone=guest_registration burst=10 nodelay;\n",
        "",
    ),
    (
        "the 429 handler removed from tls-server.conf",
        "tls-server.conf",
        "        error_page 429 = @rate_limited;\n",
        "",
    ),
    (
        "the map widened to every POST",
        "nginx.conf",
        '    "POST:/api/v1/registrations/status" $binary_remote_addr;\n',
        '    "POST:/api/v1/registrations/status" $binary_remote_addr;\n'
        '    "~^POST:" $binary_remote_addr;\n',
    ),
    (
        "the map keyed on the method alone",
        "nginx.conf",
        'map "$request_method:$uri" $guest_registration_client {',
        "map $request_method $guest_registration_client {",
    ),
    (
        "the zone declared again in tls-server.conf",
        "tls-server.conf",
        "server {\n",
        "limit_req_zone $guest_registration_client zone=guest_registration:1m rate=6r/m;\n"
        "server {\n",
    ),
    (
        "the limit moved to server level in nginx.conf",
        "nginx.conf",
        "    client_max_body_size 32m;\n",
        "    client_max_body_size 32m;\n    limit_req zone=guest_registration burst=10 nodelay;\n",
    ),
    (
        "the upload location raised in the server-wide default",
        "nginx.conf",
        "    client_max_body_size 32m;\n",
        "    client_max_body_size 260m;\n",
    ),
    (
        "the larger cap leaking into another location",
        "tls-server.conf",
        "    location / {\n        proxy_pass http://web:3000;\n",
        "    location / {\n        client_max_body_size 260m;\n        proxy_pass http://web:3000;\n",
    ),
    (
        "the web upload location loses its cap",
        "nginx.conf",
        "    location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {\n        client_max_body_size 260m;\n",
        "    location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {\n",
    ),
    (
        "the api upload location loses its body timeout",
        "tls-server.conf",
        "        client_body_timeout 120s;\n        proxy_read_timeout 300s;\n        rewrite",
        "        proxy_read_timeout 300s;\n        rewrite",
    ),
    (
        "the api upload location reads for the server's default",
        "nginx.conf",
        "        proxy_read_timeout 300s;\n        rewrite",
        "        rewrite",
    ),
    (
        "the api upload location forgets to strip the prefix",
        "nginx.conf",
        "        rewrite ^/api/v1/(.*)$ /$1 break;\n",
        "",
    ),
    (
        "the api upload location proxies with a URI the rewrite makes useless",
        "tls-server.conf",
        "        rewrite ^/api/v1/(.*)$ /$1 break;\n        proxy_pass http://api:8000;\n",
        "        rewrite ^/api/v1/(.*)$ /$1 break;\n        proxy_pass http://api:8000/;\n",
    ),
    (
        "the api upload location forgets the proxy_redirect",
        "nginx.conf",
        "        proxy_pass http://api:8000;\n        proxy_redirect ~^(https?://[^/]+)/(.*)$ $1/api/v1/$2;\n        limit_req zone=guest_registration",
        "        proxy_pass http://api:8000;\n        limit_req zone=guest_registration",
    ),
    (
        "the api upload location forgets the throttle",
        "tls-server.conf",
        "        limit_req zone=guest_registration burst=10 nodelay;\n        limit_req zone=token_exchange burst=10 nodelay;\n"
        "        limit_req zone=runner_channel burst=30 nodelay;\n        limit_req zone=runner_address burst=120 nodelay;\n"
        "        limit_req_status 429;\n        error_page 429 = @rate_limited;\n        # The credential",
        "        # The credential",
    ),
    (
        "the api upload location forgets the exchange throttle",
        "nginx.conf",
        "        limit_req zone=token_exchange burst=10 nodelay;\n        limit_req zone=runner_channel burst=30 nodelay;\n"
        "        limit_req zone=runner_address burst=120 nodelay;\n        limit_req_status 429;\n        error_page 429 = @rate_limited;\n        # The credential",
        "        limit_req zone=runner_channel burst=30 nodelay;\n        limit_req zone=runner_address burst=120 nodelay;\n"
        "        limit_req_status 429;\n        error_page 429 = @rate_limited;\n        # The credential",
    ),
    (
        "the prefix location forgets the exchange throttle",
        "tls-server.conf",
        "        limit_req zone=token_exchange burst=10 nodelay;\n        # The runner-channel throttles",
        "        # The runner-channel throttles",
    ),
    (
        "the exchange map widened to every post",
        "nginx.conf",
        '    "POST:/api/v1/auth/token"    $binary_remote_addr;\n',
        '    "POST:/api/v1/auth/token"    $binary_remote_addr;\n    "~^POST:"                    $binary_remote_addr;\n',
    ),
    (
        "the exchange map no longer names the exchange",
        "nginx.conf",
        '"POST:/api/v1/auth/token"    $binary_remote_addr;',
        '"POST:/api/v1/auth/tokens"   $binary_remote_addr;',
    ),
    (
        "the exchange zone declared again in tls-server.conf",
        "tls-server.conf",
        "server {\n",
        "limit_req_zone $token_exchange_client zone=token_exchange:1m rate=6r/m;\nserver {\n",
    ),
    (
        "the exchange zone counts the registration map",
        "nginx.conf",
        "limit_req_zone $token_exchange_client zone=token_exchange:1m",
        "limit_req_zone $guest_registration_client zone=token_exchange:1m",
    ),
    (
        "an upload location that adds a header of its own",
        "nginx.conf",
        "        auth_request /_edge/credential/web;\n        error_page 401 = @authentication_required;\n        proxy_pass http://web:3000;\n",
        "        auth_request /_edge/credential/web;\n        error_page 401 = @authentication_required;\n"
        "        add_header Cache-Control \"no-store\" always;\n        proxy_pass http://web:3000;\n",
    ),
    (
        "an upload location that sets a header of its own",
        "tls-server.conf",
        "        auth_request /_edge/credential/web;\n        error_page 401 = @authentication_required;\n        proxy_pass http://web:3000;\n",
        "        auth_request /_edge/credential/web;\n        error_page 401 = @authentication_required;\n"
        "        proxy_set_header Host $host;\n        proxy_pass http://web:3000;\n",
    ),
    (
        "a credential location loses the upload cap",
        "nginx.conf",
        "        internal;\n        client_max_body_size 260m;\n        proxy_pass http://web:3000/bff/v1/me;",
        "        internal;\n        proxy_pass http://web:3000/bff/v1/me;",
    ),
    (
        "the upload location widened to a prefix",
        "nginx.conf",
        "location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {",
        "location ~ ^/bff/v1/projects/ {",
    ),
    (
        "a new /api/v1 location for the registration path",
        "nginx.conf",
        "    location @rate_limited {",
        "    location /api/v1/registrations {\n        proxy_pass http://api:8000/registrations;\n"
        "    }\n\n    location @rate_limited {",
    ),
    (
        "nginx's own 503 kept",
        "tls-server.conf",
        "        limit_req_status 429;\n",
        "        limit_req_status 503;\n",
    ),
    (
        "the envelope's error_code changed",
        "nginx.conf",
        '"error_code":"rate_limited"',
        '"error_code":"conflict"',
    ),
    (
        "the envelope's error_code outside the catalog",
        "tls-server.conf",
        '"error_code":"rate_limited"',
        '"error_code":"too_many_requests"',
    ),
    (
        "the envelope says retryable false",
        "nginx.conf",
        '"retryable":true}',
        '"retryable":false}',
    ),
    (
        "the correlation id a fixed literal",
        "nginx.conf",
        '"correlation_id":"$request_id","retryable":true}',
        '"correlation_id":"edge","retryable":true}',
    ),
    (
        "the envelope gains a detail",
        "tls-server.conf",
        '"retryable":true}',
        '"retryable":true,"details":{"login":"x"}}',
    ),
    (
        "the envelope served as nginx's default type",
        "nginx.conf",
        "    location @rate_limited {\n        default_type application/json;\n",
        "    location @rate_limited {\n",
    ),
    (
        "the runner token limit removed from nginx.conf",
        "nginx.conf",
        "        limit_req zone=runner_channel burst=30 nodelay;\n",
        "",
    ),
    (
        "the runner address limit removed from tls-server.conf",
        "tls-server.conf",
        "        limit_req zone=runner_address burst=120 nodelay;\n",
        "",
    ),
    (
        "the runner burst widened in tls-server.conf",
        "tls-server.conf",
        "        limit_req zone=runner_channel burst=30 nodelay;\n",
        "        limit_req zone=runner_channel burst=3000 nodelay;\n",
    ),
    (
        "the runner rate raised",
        "nginx.conf",
        "zone=runner_channel:1m rate=60r/m;",
        "zone=runner_channel:1m rate=6000r/m;",
    ),
    (
        "the runner zone declared again in tls-server.conf",
        "tls-server.conf",
        "server {\n",
        "limit_req_zone $runner_token_client zone=runner_channel:1m rate=60r/m;\n"
        "server {\n",
    ),
    (
        "the runner token map keyed on the whole credential",
        "nginx.conf",
        "{43}$\" $runner_token_prefix;",
        "{43}$\" $http_authorization;",
    ),
    (
        "the runner token map taking a user's credential",
        "nginx.conf",
        "(?<runner_token_prefix>amr_[0-9a-z]{8})_[A-Za-z0-9_-]{43}$",
        "(?<runner_token_prefix>[a-z0-9]{3})[^|]*$",
    ),
    (
        "the runner token map widened to every API path",
        "nginx.conf",
        '"~^/api/v1/runner/tasks/[^|]*',
        '"~^/api/v1/[^|]*',
    ),
    (
        "the runner address map widened to every API path",
        "nginx.conf",
        '"~^/api/v1/runner/tasks/" $binary_remote_addr;',
        '"~^/api/v1/" $binary_remote_addr;',
    ),
    (
        "a session gate put in front of the runner paths",
        "nginx.conf",
        "        error_page 429 = @rate_limited;\n    }\n\n    # THE TWO UPLOAD LOCATIONS",
        "        error_page 429 = @rate_limited;\n        auth_request /_edge/credential/api;\n    }\n\n    # THE TWO UPLOAD LOCATIONS",
    ),
    (
        "the compose flag dropped",
        "compose.server.yml",
        '      AUDITMANAGER_BEHIND_PROXY: "1"',
        "",
    ),
    (
        "the compose flag set to 0",
        "compose.server.yml",
        '      AUDITMANAGER_BEHIND_PROXY: "1"',
        '      AUDITMANAGER_BEHIND_PROXY: "0"',
    ),
    (
        "the compose flag given to the api as well",
        "compose.server.yml",
        "      AUDITMANAGER_PROVIDER_MODE: ",
        '      AUDITMANAGER_BEHIND_PROXY: "1"\n      AUDITMANAGER_PROVIDER_MODE: ',
    ),
]


@pytest.mark.parametrize(
    ("case", "target", "old", "new"), MUTATIONS, ids=[case for case, *_ in MUTATIONS]
)
def test_each_check_can_fail(case: str, target: str, old: str, new: str) -> None:
    texts = _texts()
    assert old in texts[target], f"{case}: the mutation matches nothing in {target}"
    texts[target] = texts[target].replace(old, new, 1)
    assert all_problems(texts), f"{case}: the guard stayed green on a mutated {target}"
