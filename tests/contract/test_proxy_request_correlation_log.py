"""A refusal the proxy writes itself can be found in its log by the envelope's correlation ID.

`EDGE-REQUEST-ID-LOG-01`, ported from `W52-DEBT-EDGE-LOG-129-01`. The proxy's own 401 and 429
envelopes carry `"correlation_id":"$request_id"`; both listeners log that same value in one shared
format that leaves out query strings, headers and bodies.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAIN = ROOT / "infra/deploy/proxy/nginx.conf"
TLS = ROOT / "infra/deploy/proxy/tls-server.conf"
FORMAT = "auditmanager_correlation"
LOG = f"access_log /dev/stdout {FORMAT};"


def _directives(source: str) -> list[tuple[int, str]]:
    """Return active directives and their brace depth in one conf.d file."""
    result: list[tuple[int, str]] = []
    depth = 0
    for raw in source.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        result.append((depth, line))
        if line.endswith("{"):
            depth += 1
        elif line == "}":
            depth -= 1
    return result


def logging_problems(plain: str, tls: str) -> list[str]:
    problems: list[str] = []
    formats = re.findall(rf"(?ms)^log_format\s+{FORMAT}\s+(.*?);", plain)
    if len(formats) != 1:
        problems.append("plain config must declare exactly one shared log format")
    else:
        body = formats[0]
        if body.count("$request_id") != 1 or "request_id=$request_id" not in body:
            problems.append("log format does not carry one request ID")
        forbidden = ("$request_uri", "$args", "$request", "$http_authorization", "$request_body")
        if "$uri" not in body or any(
            re.search(re.escape(token) + r"(?![A-Za-z0-9_])", body) for token in forbidden
        ):
            problems.append("log format may expose query values, headers or body")
        if "$status" not in body:
            problems.append("log format does not carry the response status")
    if re.search(rf"(?m)^\s*log_format\s+{FORMAT}\b", tls):
        problems.append("TLS config duplicates the http-level log format")
    for name, source in (("plain", plain), ("TLS", tls)):
        directives = _directives(source)
        if any(depth == 0 and line.startswith("access_log ") for depth, line in directives):
            problems.append(f"{name} config adds an http-level access log beside the image's own")
        server_logs = [line for depth, line in directives if depth == 1 and line.startswith("access_log ")]
        if server_logs != [LOG]:
            problems.append(f"{name} server does not use the shared access log")
        if '"correlation_id":"$request_id"' not in source:
            problems.append(f"{name} refusal no longer returns the logged request ID")
    return problems


def test_both_listeners_log_the_refusal_correlation_id() -> None:
    assert logging_problems(PLAIN.read_text(), TLS.read_text()) == []


def test_each_logging_guard_can_fail() -> None:
    plain, tls = PLAIN.read_text(), TLS.read_text()
    assert logging_problems(plain.replace(LOG, "", 1), tls)
    assert logging_problems(plain, tls.replace(LOG, "", 1))
    assert logging_problems(plain.replace("request_id=$request_id", "request_id=none", 1), tls)
    assert logging_problems(plain.replace('"$request_method $uri"', '"$request_method $request_uri"', 1), tls)
    assert logging_problems(plain, tls.replace("server_name _;", f"server_name _;\nlog_format {FORMAT} '$uri';", 1))
    assert logging_problems(plain.replace("\nserver {", f"\naccess_log /dev/stdout {FORMAT};\nserver {{", 1), tls)
    assert logging_problems(plain.replace(LOG, "access_log /var/log/nginx/access.log auditmanager_correlation;", 1), tls)
