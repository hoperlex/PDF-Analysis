"""`W49-EDGE-01` -- the guest throttle at the proxy, held to the catalog and to the contract.

`W49-PLAN.md` section 3.5: `/api/v1/` is public behind nginx, so the edge limits
`POST /api/v1/registrations` and `POST /api/v1/registrations/status` per client address and
answers the excess with the catalog's `rate_limited` envelope; the `web` service is told
it runs behind that proxy (`AUDITMANAGER_BEHIND_PROXY`), so the web tier may key its own
guest bucket on the `X-Real-IP` the proxy sets.

**What this file reads, and why three files.** The throttle lives in both server bodies --
`nginx.conf` is always loaded and `tls-server.conf` is copied beside it when a certificate
exists -- and the flag lives in `compose.server.yml`. Any one of the three can lose its line
while the other two still look right, so each is read and each is checked:

* the `map` and the `limit_req_zone` are http-level, declared **once**, in `nginx.conf`, and
  never in `tls-server.conf` (a second declaration stops nginx from starting);
* the map keys exactly the registration calls the frozen OpenAPI document names, by
  method and by the full served path, and nothing else -- no regex key, no prefix;
* both server bodies throttle inside the existing `location /api/v1/` and nowhere else,
  with no new `/api/v1` location;
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
MAP_HEADER = re.compile(r'^map "\$request_method:\$uri" (\$\w+) \{$')
ZONE_LINE = re.compile(r"^limit_req_zone (\$\w+) zone=(\w+):\d+[km] rate=\d+r/[sm];$")
LIMIT_LINE = re.compile(r"^limit_req zone=(\w+) burst=\d+( nodelay)?;$")
RETURN_LINE = re.compile(r"^return (\d{3}) '(.*)';$")
CLIENT_ADDRESS = "$binary_remote_addr"
NAMED_LOCATION = "@rate_limited"
API_LOCATIONS = frozenset({"location = /api/v1 {", "location /api/v1/ {"})
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


def expected_map_keys() -> dict[str, str]:
    """`METHOD:/api/v1<path>` for each throttled operation, read out of the frozen document."""
    document = json.loads(OPENAPI.read_text(encoding="utf-8"))
    base = document["servers"][0]["url"]
    keys = {
        f"{method.upper()}:{base}{path}": CLIENT_ADDRESS
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if isinstance(operation, dict) and operation.get("operationId") in THROTTLED_OPERATIONS
    }
    assert len(keys) == len(THROTTLED_OPERATIONS), (
        f"the frozen document no longer names every throttled operation: {sorted(keys)}"
    )
    return keys


# ---------------------------------------------------------------------------------------
# The checks -- each returns what is wrong, so the same function can be shown to fail
# ---------------------------------------------------------------------------------------


def declaration_problems(plain: str, tls: str) -> list[str]:
    """The map and the zone: once, at http level, in the always-loaded file, keyed exactly."""
    problems: list[str] = []
    lines = statements(plain)
    maps = [line for line in lines if line.startswith("map ")]
    zones = [line for line in lines if line.startswith("limit_req_zone ")]
    outer = top_level(lines)
    if len(maps) != 1 or maps[0] not in outer:
        return [f"nginx.conf must declare exactly one map, at http level: {maps}"]
    if len(zones) != 1 or zones[0] not in outer:
        return [f"nginx.conf must declare exactly one limit_req_zone, at http level: {zones}"]
    header = MAP_HEADER.match(_norm(maps[0]))
    zone = ZONE_LINE.match(_norm(zones[0]))
    if header is None:
        problems.append(f'the map is not keyed by "$request_method:$uri": {maps[0]!r}')
    if zone is None:
        problems.append(f"the limit_req_zone is not the expected shape: {zones[0]!r}")
    if header and zone and zone.group(1) != header.group(1):
        problems.append(
            f"the zone counts {zone.group(1)} but the map yields {header.group(1)}"
        )
    (inner,) = blocks(lines, _norm(maps[0]))
    entries = _map_entries(inner)
    wanted = {"default": "", **expected_map_keys()}
    if entries != wanted:
        problems.append(
            "the map must yield the client address for exactly the registration calls and "
            f"the empty string otherwise; it reads {entries}, expected {wanted}"
        )
    for line in statements(tls):
        if line.startswith(("map ", "limit_req_zone ")):
            problems.append(
                "tls-server.conf declares an http-level throttle directive; nginx loads it "
                f"beside nginx.conf, so this is a duplicate that stops the master: {line!r}"
            )
    return problems


def zone_name(plain: str) -> str | None:
    for line in statements(plain):
        match = ZONE_LINE.match(_norm(line))
        if match:
            return match.group(2)
    return None


def throttle_problems(name: str, config: str, zone: str | None, status: int) -> list[str]:
    """One server body: the limit inside the one `location /api/v1/`, and nowhere else."""
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
    if len(limits) != 1:
        problems.append(f"{name}: `location /api/v1/` carries {len(limits)} limit_req lines")
    else:
        match = LIMIT_LINE.match(limits[0])
        if match is None or match.group(1) != zone:
            problems.append(f"{name}: {limits[0]!r} does not use the declared zone {zone!r}")
    for needed in (f"limit_req_status {status};", f"error_page {status} = {NAMED_LOCATION};"):
        if needed not in inner:
            problems.append(f"{name}: `location /api/v1/` lacks {needed!r}")
    for prefix in ("limit_req ", "limit_req_status ", "error_page "):
        everywhere = [line for line in lines if line.startswith(prefix)]
        inside = [line for line in inner if line.startswith(prefix)]
        if len(everywhere) != len(inside):
            problems.append(
                f"{name}: a `{prefix.strip()}` outside `location /api/v1/` would reach "
                f"requests the plan never throttles: {everywhere}"
            )
    return problems


def envelope_of(name: str, config: str) -> tuple[list[str], int | None, dict[str, Any] | None]:
    """The status and the parsed body the named location returns, or why there are none."""
    named = blocks(statements(config), f"location {NAMED_LOCATION} {{")
    if len(named) != 1:
        return [f"{name}: expected one `location {NAMED_LOCATION}`, found {len(named)}"], None, None
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
    zone = zone_name(plain)
    problems = declaration_problems(plain, tls)
    for name in ("nginx.conf", "tls-server.conf"):
        problems += throttle_problems(name, texts[name], zone, status)
        problems += envelope_problems(name, texts[name])
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
    zone = zone_name(texts["nginx.conf"])
    assert zone is not None
    status = _catalog()["codes"][CODE]["http"]
    assert throttle_problems(name, texts[name], zone, status) == []


@pytest.mark.parametrize("name", ["nginx.conf", "tls-server.conf"])
def test_the_refusal_is_the_catalog_rate_limited_envelope(name: str) -> None:
    assert envelope_problems(name, _texts()[name]) == []


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
        '"correlation_id":"$request_id"',
        '"correlation_id":"edge"',
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
        "        default_type application/json;\n",
        "",
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
