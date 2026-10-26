"""`W53-CLOSE` `C-18` -- the edge sends the security response headers on every answer.

Both server bodies (`infra/deploy/proxy/nginx.conf`, always loaded, and
`infra/deploy/proxy/tls-server.conf`, copied beside it when a certificate exists) must give
every answer they produce:

* `X-Content-Type-Options: nosniff`;
* `X-Frame-Options: DENY` and `Content-Security-Policy: frame-ancestors 'none'`;
* `Referrer-Policy: same-origin`;

each with `always`, so a 401, a 404 and the proxy's own 429 carry them too -- and the TLS body
alone adds `Strict-Transport-Security: max-age=31536000`.

**What this reads, and the one nginx rule it exists for.** `add_header` is inherited from the
enclosing level only when the inner level declares none: a single `add_header` inside a
`location` silently drops every server-level one for that location. So the check is not
"the server block has the lines" but "every `location` that answers -- by `proxy_pass` or by
`return` -- ends up with them", computed the way nginx computes it: the location's own
`add_header` set if it has one, otherwise the server's.

**What it cannot prove.** That nginx loads the file and the headers reach a browser. That
needs a daemon, which this battery does not have; the lane did not run one (container-free
by ruling `R-84`).

**Every check here is shown able to fail**, in `test_each_check_can_fail`, by putting a
mutation in front of the same function the real check uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROXY = ROOT / "infra" / "deploy" / "proxy"
PLAIN = PROXY / "nginx.conf"
TLS_BLOCK = PROXY / "tls-server.conf"

#: The four every answer carries, exactly as written in both files.
SECURITY_HEADERS: frozenset[str] = frozenset(
    {
        'add_header X-Content-Type-Options "nosniff" always;',
        'add_header X-Frame-Options "DENY" always;',
        "add_header Content-Security-Policy \"frame-ancestors 'none'\" always;",
        'add_header Referrer-Policy "same-origin" always;',
    }
)
#: The TLS block's fifth, and only its.
HSTS = 'add_header Strict-Transport-Security "max-age=31536000" always;'


# ---------------------------------------------------------------------------------------
# Reading the files
# ---------------------------------------------------------------------------------------


def statements(config: str) -> list[str]:
    """Every non-comment line, stripped, inner spacing collapsed.

    A `#` ends the line, the rule `test_proxy_tls_path.py` and `test_proxy_rate_limits.py`
    apply; neither file carries a `#` inside a quoted value.
    """
    out: list[str] = []
    for raw in config.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(" ".join(line.split()))
    return out


@dataclass
class Block:
    """One `{ }` block: its opening line, its own directives, and the blocks inside it."""

    header: str
    directives: list[str] = field(default_factory=list)
    children: list[Block] = field(default_factory=list)


def parse(config: str) -> Block:
    """The block tree of a file. The root's header is empty."""
    root = Block("")
    stack = [root]
    for line in statements(config):
        if line.endswith("{"):
            child = Block(line)
            stack[-1].children.append(child)
            stack.append(child)
        elif line == "}":
            if len(stack) == 1:
                raise ValueError("an unbalanced `}`")
            stack.pop()
        else:
            stack[-1].directives.append(line)
    if len(stack) != 1:
        raise ValueError("an unclosed block")
    return root


def headers_of(block: Block) -> set[str]:
    return {line for line in block.directives if line.startswith("add_header ")}


def answering_locations(server: Block) -> list[Block]:
    """Every `location`, nested ones included, that produces an answer itself."""
    found: list[Block] = []
    pending = [child for child in server.children if child.header.startswith("location ")]
    while pending:
        location = pending.pop(0)
        if any(line.startswith(("proxy_pass ", "return ")) for line in location.directives):
            found.append(location)
        pending.extend(child for child in location.children if child.header.startswith("location "))
    return found


def effective_headers(server: Block, location: Block) -> set[str]:
    """What nginx sends from ``location``: its own set if it declares any, else the server's.

    Nested locations are walked from the server down, each level replacing the inherited set
    when it declares one -- nginx's rule, not a union.
    """
    path: list[Block] = []

    def find(node: Block) -> bool:
        if node is location:
            return True
        for child in node.children:
            path.append(child)
            if find(child):
                return True
            path.pop()
        return False

    assert find(server), f"{location.header} is not inside this server"
    inherited = headers_of(server)
    for level in path:
        own = headers_of(level)
        if own:
            inherited = own
    return inherited


# ---------------------------------------------------------------------------------------
# The checks -- each returns what is wrong, so the same function can be shown to fail
# ---------------------------------------------------------------------------------------


def header_problems(name: str, config: str, *, tls: bool) -> list[str]:
    problems: list[str] = []
    try:
        tree = parse(config)
    except ValueError as error:
        return [f"{name}: {error}"]
    servers = [child for child in tree.children if child.header == "server {"]
    if len(servers) != 1:
        return [f"{name}: expected one server block, found {len(servers)}"]
    server = servers[0]
    expected = set(SECURITY_HEADERS) | ({HSTS} if tls else set())
    locations = answering_locations(server)
    if len(locations) < 4:
        problems.append(
            f"{name}: only {len(locations)} answering locations found -- the walk is broken"
        )
    for location in locations:
        sent = effective_headers(server, location)
        missing = expected - sent
        if missing:
            problems.append(f"{name}: `{location.header}` does not send {sorted(missing)}")
        if not tls and any(line.startswith("add_header Strict-Transport-Security") for line in sent):
            problems.append(f"{name}: `{location.header}` sends HSTS on a plain-HTTP listener")
    for line in statements(config):
        if line.startswith("add_header Strict-Transport-Security") and not tls:
            problems.append(f"{name}: HSTS on a plain-HTTP listener: {line}")
        if line.startswith("add_header ") and not line.endswith(" always;"):
            problems.append(f"{name}: `{line}` is not `always`, so error answers lose it")
    return problems


def all_problems(plain: str, tls: str) -> list[str]:
    return header_problems("nginx.conf", plain, tls=False) + header_problems(
        "tls-server.conf", tls, tls=True
    )


# ---------------------------------------------------------------------------------------
# The real assertions
# ---------------------------------------------------------------------------------------


def test_the_plain_body_sends_the_four_headers_from_every_location() -> None:
    assert header_problems("nginx.conf", PLAIN.read_text(), tls=False) == []


def test_the_tls_body_sends_the_four_and_hsts_from_every_location() -> None:
    assert header_problems("tls-server.conf", TLS_BLOCK.read_text(), tls=True) == []


def test_the_walk_reaches_the_rate_limited_envelope() -> None:
    """The 429 the proxy writes itself is an answer a browser renders; it is checked too."""
    for path in (PLAIN, TLS_BLOCK):
        server = next(c for c in parse(path.read_text()).children if c.header == "server {")
        headers = [location.header for location in answering_locations(server)]
        assert "location @rate_limited {" in headers, (path.name, headers)
        assert "location / {" in headers, (path.name, headers)


# ---------------------------------------------------------------------------------------
# Every check can fail
# ---------------------------------------------------------------------------------------

_LOCATION_WEB = "    location / {\n        proxy_pass http://web:3000;\n"

MUTATIONS = {
    "a header dropped from the plain server": (
        "plain",
        '    add_header X-Frame-Options "DENY" always;\n',
        "",
    ),
    "a header dropped from the TLS server": (
        "tls",
        "    add_header Content-Security-Policy \"frame-ancestors 'none'\" always;\n",
        "",
    ),
    "a location that declares its own header drops the inherited four": (
        "plain",
        _LOCATION_WEB,
        _LOCATION_WEB + '        add_header Cache-Control "no-store" always;\n',
    ),
    "HSTS on the plain listener": (
        "plain",
        '    add_header Referrer-Policy "same-origin" always;\n',
        '    add_header Referrer-Policy "same-origin" always;\n    ' + HSTS + "\n",
    ),
    "HSTS missing from the TLS listener": (
        "tls",
        "    " + HSTS + "\n",
        "",
    ),
    "a header without always": (
        "tls",
        '    add_header X-Content-Type-Options "nosniff" always;\n',
        '    add_header X-Content-Type-Options "nosniff";\n',
    ),
}


@pytest.mark.parametrize("case", sorted(MUTATIONS))
def test_each_check_can_fail(case: str) -> None:
    target, old, new = MUTATIONS[case]
    plain, tls = PLAIN.read_text(), TLS_BLOCK.read_text()
    if target == "plain":
        assert old in plain, f"the mutation for {case!r} no longer matches nginx.conf"
        plain = plain.replace(old, new, 1)
    else:
        assert old in tls, f"the mutation for {case!r} no longer matches tls-server.conf"
        tls = tls.replace(old, new, 1)
    assert all_problems(plain, tls) != [], f"{case!r} was not caught"


# ---------------------------------------------------------------------------------------
# The challenge listener -- `PROD-01-TLS-ACME-01`
# ---------------------------------------------------------------------------------------
#
# `infra/deploy/proxy/acme-challenge.conf` is a third server block, loaded beside the plain one when a
# certificate name is configured and published as public port 80. It answers two things -- a file from the
# ACME webroot and a redirect -- and the redirect and the 404 are pages a browser renders, so the four headers
# must be on both locations by the same rule as the other two bodies: at server level, `always`, and no
# `location` may declare an `add_header` of its own. Its locations do not all `proxy_pass` or `return` (the
# webroot one serves a file with `root` and `try_files`), so `answering_locations` would miss it; this walks
# EVERY location. No HSTS: it is a plain-HTTP listener, where the header means nothing.

CHALLENGE = PROXY / "acme-challenge.conf"


def challenge_problems(config: str) -> list[str]:
    try:
        tree = parse(config)
    except ValueError as error:
        return [f"acme-challenge.conf: {error}"]
    servers = [child for child in tree.children if child.header == "server {"]
    if len(servers) != 1:
        return [f"acme-challenge.conf: expected one server block, found {len(servers)}"]
    server = servers[0]
    locations = [child for child in server.children if child.header.startswith("location ")]
    problems: list[str] = []
    if len(locations) != 2:
        problems.append(f"acme-challenge.conf: expected two locations, found {len(locations)} -- the walk is broken")
    for location in locations:
        sent = effective_headers(server, location)
        missing = SECURITY_HEADERS - sent
        if missing:
            problems.append(f"acme-challenge.conf: `{location.header}` does not send {sorted(missing)}")
        if any(line.startswith("add_header Strict-Transport-Security") for line in sent):
            problems.append(f"acme-challenge.conf: `{location.header}` sends HSTS on a plain-HTTP listener")
    for line in statements(config):
        if line.startswith("add_header ") and not line.endswith(" always;"):
            problems.append(f"acme-challenge.conf: `{line}` is not `always`, so error answers lose it")
    return problems


def test_the_challenge_block_sends_the_four_headers_from_both_locations() -> None:
    assert challenge_problems(CHALLENGE.read_text()) == []


CHALLENGE_MUTATIONS = {
    "a header dropped from the challenge server": (
        '    add_header Referrer-Policy "same-origin" always;\n',
        "",
    ),
    "a location that declares its own header drops the inherited four": (
        "        default_type text/plain;\n",
        '        default_type text/plain;\n        add_header Cache-Control "no-store" always;\n',
    ),
    "HSTS on the plain challenge listener": (
        '    add_header Referrer-Policy "same-origin" always;\n',
        '    add_header Referrer-Policy "same-origin" always;\n    ' + HSTS + "\n",
    ),
    "a header without always": (
        '    add_header X-Frame-Options "DENY" always;\n',
        '    add_header X-Frame-Options "DENY";\n',
    ),
    "a third location": (
        "    location / {\n",
        "    location /extra {\n        return 204;\n    }\n\n    location / {\n",
    ),
}


@pytest.mark.parametrize("case", sorted(CHALLENGE_MUTATIONS))
def test_each_challenge_check_can_fail(case: str) -> None:
    old, new = CHALLENGE_MUTATIONS[case]
    config = CHALLENGE.read_text()
    assert old in config, f"the mutation for {case!r} no longer matches acme-challenge.conf"
    assert challenge_problems(config.replace(old, new, 1)) != [], f"{case!r} was not caught"
