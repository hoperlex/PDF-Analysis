"""`REAL-IP-EDGE-01` -- the per-address throttles count the CLIENT, and only when the operator
says which peer may name it. Debts `D-144` and `D-191` `E-3`, found again by a peer review on
2026-10-21.

**What was wrong.** On the deployed stand the traffic is browser -> a nginx on the HOST (the TLS
terminator, outside this repository) -> the repository's own proxy container. The container
accepts every connection from one peer, the compose network's gateway, so the registration
zone, the token-exchange zone (`HARDEN-AUTH-EDGE-01`) and the web tier's guest bucket (which
keys the `X-Real-IP` the proxy sets from `$remote_addr`) were each ONE bucket for all
visitors: a single script could spend everyone's sign-ups and token exchanges.

**What is claimed, in three halves, and which half each test proves.**

1. *The rule* (`nginx.conf`): `real_ip_header X-Forwarded-For; real_ip_recursive on;` at http
   level, no `set_real_ip_from` of its own. The trusted peers come from
   `ALPHA_TRUSTED_PROXY_CIDRS` through `proxy/trusted-proxies.sh`, which writes them into
   `conf.d/` -- or writes nothing, the default, and then the header is never read.
2. *The list* (`trusted-proxies.sh`): a value is validated, never quoted; a bad one stops the
   container instead of being read as empty; `0.0.0.0/0` is refused by name; an empty value
   removes what an earlier start left.
3. *The behaviour* (live): a real nginx with the committed configuration and the REAL script's
   output in front of two recording stubs, driven from loopback source addresses. With nothing
   trusted, or with a list that does not contain the peer, a forged `X-Forwarded-For` buys no
   bucket and the stub sees the peer in `X-Real-IP`. With the peer trusted, clients named in
   `X-Forwarded-For` get independent buckets in BOTH zones, the rightmost untrusted address
   wins, hops that are themselves trusted are stepped over, and nothing to the left of the
   winner is read. Both server bodies are driven: the TLS body inherits the http-level rule.

The static halves read files and need no daemon. The live half needs an `nginx` binary (as in
`test_edge_credential_gate.py`, whose harness it reuses) and is skipped without one; the image
half needs the pinned image already pulled and is skipped without it. **Every guard is shown
able to fail**: the `MUTATIONS` and `HOOK_MUTATIONS` below put a mutation in front of the same
function the real check uses.

Run with `python -m pytest` (the repository root must be on the path for the `tests.` import,
as for every other module in this directory that imports from `tests.support`).
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.integration.composition.test_edge_credential_gate import (
    PLAIN,
    TLS_BLOCK,
    Upstream,
    needs_nginx,
    running,
    statements,
)

ROOT = Path(__file__).resolve().parents[3]
PROXY = ROOT / "infra" / "deploy" / "proxy"
HOOK = PROXY / "trusted-proxies.sh"
COMPOSE = ROOT / "infra" / "deploy" / "compose.server.yml"
ENV_EXAMPLE = ROOT / "infra" / "deploy" / "env" / "alpha.env.example"
README = ROOT / "infra" / "deploy" / "README.md"
RUNBOOK = ROOT / "docs" / "program" / "DEPLOYMENT_RUNBOOK.md"

VARIABLE = "ALPHA_TRUSTED_PROXY_CIDRS"
HOOK_TARGET = "/docker-entrypoint.d/26-trusted-proxies.sh"
RULE = ("real_ip_header X-Forwarded-For;", "real_ip_recursive on;")
#: One request is answered at once and ten more are admitted as a burst; the twelfth is refused.
BURST = 11
#: zone -> (path through the proxy, path the stub api sees, status the stub answers).
ZONES = {
    "token_exchange": ("/api/v1/auth/token", "/auth/token", 401),
    "guest_registration": ("/api/v1/registrations", "/registrations", 201),
}
LOOPBACK = "127.0.0.1"


# ---------------------------------------------------------------------------------------
# The trust list: the real script, run for real
# ---------------------------------------------------------------------------------------


def run_hook(
    value: str | None,
    out: Path,
    *args: str,
    script: Path = HOOK,
) -> subprocess.CompletedProcess[str]:
    environment = {"PATH": "/usr/bin:/bin", "TRUSTED_PROXIES_CONF": str(out)}
    if value is not None:
        environment[VARIABLE] = value
    return subprocess.run(["sh", str(script), *args], capture_output=True, text=True, env=environment)


def trust_lines(value: str) -> str:
    """What the script writes for ``value``: its `set_real_ip_from` lines, or nothing."""
    with tempfile.TemporaryDirectory(prefix="trust-") as raw:
        out = Path(raw) / "trusted-proxies.conf"
        done = run_hook(value, out)
        assert done.returncode == 0, done.stderr
        return out.read_text() if out.exists() else ""


def with_trust(plain: str, lines: str) -> str:
    """``nginx.conf`` with ``lines`` at http level, before the server block, as `conf.d/` does."""
    head, marker, rest = plain.partition("\nserver {\n")
    assert marker, "nginx.conf has no server block"
    return head + "\n" + lines + marker + rest


# ---------------------------------------------------------------------------------------
# The static half: the rule is in the one file that is always loaded, and trusts nobody
# ---------------------------------------------------------------------------------------


def top_level(lines: list[str]) -> list[str]:
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


def rule_problems(plain: str, tls: str) -> list[str]:
    """The rule once, at http level, in `nginx.conf`; no trust of its own anywhere."""
    problems: list[str] = []
    plain_lines, tls_lines = statements(plain), statements(tls)
    outer = top_level(plain_lines)
    for directive in RULE:
        if plain_lines.count(directive) != 1:
            problems.append(f"nginx.conf must carry exactly one `{directive}`: {plain_lines.count(directive)}")
        elif directive not in outer:
            problems.append(f"`{directive}` is not at http level in nginx.conf; the TLS body would not inherit it")
    for name, lines in (("nginx.conf", plain_lines), ("tls-server.conf", tls_lines)):
        for line in lines:
            if line.startswith("set_real_ip_from"):
                problems.append(f"{name} trusts a peer of its own ({line!r}); trust comes from {VARIABLE} alone")
    other = [line for line in plain_lines if line.startswith("real_ip_") and line not in RULE]
    if other:
        problems.append(f"nginx.conf carries other real-ip directives: {other}")
    for line in tls_lines:
        if line.startswith("real_ip_"):
            problems.append(f"tls-server.conf repeats the rule ({line!r}); it inherits it, and a copy can drift")
    return problems


def test_the_rule_is_declared_once_and_trusts_nobody_static() -> None:
    assert rule_problems(PLAIN.read_text(), TLS_BLOCK.read_text()) == []


#: (case, file, exact text replaced, replacement). Each must be seen by the static check.
MUTATIONS: list[tuple[str, str, str, str]] = [
    ("recursion is off", "nginx.conf", "real_ip_recursive on;", "real_ip_recursive off;"),
    ("the header is X-Real-IP", "nginx.conf", "real_ip_header X-Forwarded-For;", "real_ip_header X-Real-IP;"),
    ("the header line is gone", "nginx.conf", "real_ip_header X-Forwarded-For;\n", ""),
    ("the recursion line is gone", "nginx.conf", "real_ip_recursive on;\n", ""),
    (
        "nginx.conf trusts everyone",
        "nginx.conf",
        "real_ip_recursive on;\n",
        "real_ip_recursive on;\nset_real_ip_from 0.0.0.0/0;\n",
    ),
    (
        "nginx.conf trusts the loopback",
        "nginx.conf",
        "real_ip_recursive on;\n",
        "real_ip_recursive on;\nset_real_ip_from 127.0.0.1;\n",
    ),
    (
        "the tls body trusts a peer of its own",
        "tls-server.conf",
        "    client_max_body_size 32m;\n",
        "    set_real_ip_from 10.0.0.0/8;\n    client_max_body_size 32m;\n",
    ),
    (
        "the tls body repeats the rule",
        "tls-server.conf",
        "    client_max_body_size 32m;\n",
        "    real_ip_header X-Forwarded-For;\n    client_max_body_size 32m;\n",
    ),
    (
        "the rule moved into the plain server block",
        "nginx.conf",
        "real_ip_header X-Forwarded-For;\nreal_ip_recursive on;\n",
        "",
    ),
]
#: The one mutation that is not a plain replacement: it re-inserts the two lines inside `server {`.
MOVED = "the rule moved into the plain server block"


def mutated(case: str, plain: str, tls: str) -> tuple[str, str]:
    for name, target, old, new in MUTATIONS:
        if name != case:
            continue
        text = plain if target == "nginx.conf" else tls
        assert old in text, f"{case}: the mutation matches nothing in {target}"
        text = text.replace(old, new, 1)
        if case == MOVED:
            text = text.replace("server {\n    listen 8080;\n", "server {\n    listen 8080;\n    real_ip_header X-Forwarded-For;\n    real_ip_recursive on;\n", 1)
            assert "    real_ip_recursive on;" in text
        return (text, tls) if target == "nginx.conf" else (plain, text)
    raise KeyError(case)


@pytest.mark.parametrize("case", [name for name, *_ in MUTATIONS])
def test_each_static_guard_can_fail(case: str) -> None:
    plain, tls = mutated(case, PLAIN.read_text(), TLS_BLOCK.read_text())
    assert rule_problems(plain, tls) != [], f"{case}: the static guard stayed green"


def test_the_script_is_executable_in_git() -> None:
    """The image runs `/docker-entrypoint.d/*.sh` only when the file is executable; an
    ignored hook is the quietest way for this whole path to do nothing (`enable-tls.sh`)."""
    mode = subprocess.run(
        ["git", "ls-files", "--stage", "--", str(HOOK.relative_to(ROOT))],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert mode and mode[0] == "100755", f"{HOOK.name} is {mode[0] if mode else 'untracked'} in git"


def test_the_compose_file_wires_the_value_and_the_hook() -> None:
    text = COMPOSE.read_text()
    uncommented = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert f"      {VARIABLE}: ${{{VARIABLE}:-}}" in uncommented, "the value must default to EMPTY, which trusts nobody"
    assert f"- ./proxy/trusted-proxies.sh:{HOOK_TARGET}:ro" in uncommented


def test_the_example_environment_leaves_it_empty_and_says_how_to_fill_it() -> None:
    lines = ENV_EXAMPLE.read_text().splitlines()
    assert f"#{VARIABLE}=" in lines, "the example must show the variable commented out, so a copy trusts nobody"
    assert not [x for x in lines if x.startswith(f"{VARIABLE}=")], "the example must not set it"
    prose = "\n".join(lines)
    for needed in ("docker network inspect", "X-Forwarded-For", "0.0.0.0/0"):
        assert needed in prose, f"alpha.env.example does not mention {needed!r}"


def test_the_operator_documents_name_the_value_and_the_terminator_line() -> None:
    for path in (README, RUNBOOK):
        text = path.read_text()
        assert VARIABLE in text, f"{path.name} does not name {VARIABLE}"
        assert "proxy_set_header X-Forwarded-For $remote_addr;" in text, (
            f"{path.name} does not state the host-side line the trust depends on"
        )
        assert "UNVERIFIED" in text, f"{path.name} does not mark what was not verified"


# ---------------------------------------------------------------------------------------
# The trust list script
# ---------------------------------------------------------------------------------------

STALE = "set_real_ip_from 203.0.113.99;\n"
ACCEPTED = [
    ("172.29.0.1/32", ["set_real_ip_from 172.29.0.1/32;"]),
    ("172.29.0.1", ["set_real_ip_from 172.29.0.1;"]),
    (
        "172.29.0.1, 10.0.0.0/8\n\tfd00::/8,2001:db8::1 ::1",
        [
            "set_real_ip_from 172.29.0.1;",
            "set_real_ip_from 10.0.0.0/8;",
            "set_real_ip_from fd00::/8;",
            "set_real_ip_from 2001:db8::1;",
            "set_real_ip_from ::1;",
        ],
    ),
]
EMPTY = [None, "", "   ", ",", " ,\t\n"]
#: Values the script must refuse, each with a word its message must carry.
REFUSED = [
    "127.0.0.1; return 200 'x'",
    "0.0.0.0/0",
    "::/0",
    "10.0.0.0/33",
    "fd00::/129",
    "300.1.1.1",
    "01.2.3.4",
    "1.2.3",
    "proxy.example.org",
    "all",
    "unix:/tmp/x",
    "$remote_addr",
    "10.0.0.1/8/8",
    "10.0.0.0/",
    "10.0.0.0/08",
    "10.0.0.0/-1",
    "::ffff:1.2.3.4",
    "1::2::3",
    ":1:2:3:4:5:6:7",
    "1:2:3:4:5:6:7:8:9",
    "::1;",
    "::1;x",
    "fd00::g",
    "10.0.0.1}",
    '10.0.0.1"',
    "*",
    "`id`",
    "172.29.0.1, not-an-address",
]


def _installed(out: Path) -> list[str]:
    return [x for x in out.read_text().splitlines() if x and not x.startswith("#")] if out.exists() else []


def hook_problems(script: Path) -> list[str]:
    """Run every case against ``script``; return what was wrong."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="hook-") as raw:
        out = Path(raw) / "trusted-proxies.conf"
        for value in EMPTY:
            out.write_text(STALE)
            done = run_hook(value, out, script=script)
            if done.returncode != 0 or out.exists():
                problems.append(f"empty {value!r}: exit {done.returncode}, file kept={out.exists()} (a stale file must go)")
        for value, wanted in ACCEPTED:
            out.write_text(STALE)
            done = run_hook(value, out, script=script)
            if done.returncode != 0 or _installed(out) != wanted:
                problems.append(f"{value!r}: exit {done.returncode}, wrote {_installed(out)}, wanted {wanted}")
        for value in REFUSED:
            out.write_text(STALE)
            done = run_hook(value, out, script=script)
            if done.returncode != 2:
                problems.append(f"{value!r} was not refused: exit {done.returncode}")
            if out.exists():
                problems.append(f"{value!r} was refused but a file is left: {_installed(out)}")
            if "refused" not in done.stderr:
                problems.append(f"{value!r}: the refusal does not say so: {done.stderr!r}")
        # --check validates and writes nothing, and touches nothing that is there.
        out.write_text(STALE)
        good = run_hook("172.29.0.1/32", out, "--check", script=script)
        bad = run_hook("0.0.0.0/0", out, "--check", script=script)
        empty = run_hook("", out, "--check", script=script)
        if (good.returncode, bad.returncode, empty.returncode) != (0, 2, 0):
            problems.append(f"--check exits {(good.returncode, bad.returncode, empty.returncode)}, wanted (0, 2, 0)")
        if not out.exists() or out.read_text() != STALE:
            problems.append("--check changed the file it was told not to write")
        if run_hook("", out, "--frobnicate", script=script).returncode != 2:
            problems.append("an unknown argument was not refused")
    return problems


def test_the_trust_list_script_accepts_exactly_what_it_should() -> None:
    assert hook_problems(HOOK) == []


#: (case, exact text replaced, replacement) applied to the script itself.
HOOK_MUTATIONS: list[tuple[str, str, str]] = [
    ("a prefix length of 0 is accepted", 'if [ "$_length" -eq 0 ]; then', "if false; then"),
    ("every entry is acceptable", '    WHY=""\n    _entry=$1\n', '    WHY=""\n    return 0\n    _entry=$1\n'),
    (
        "a bad value is read as empty",
        "'The client address'.\"\n        exit 2",
        "'The client address'.\"\n        exit 0",
    ),
    (
        "an empty value keeps the file an earlier start wrote",
        'if [ "$COUNT" -eq 0 ]; then\n    rm -f "$DST"\n',
        'if [ "$COUNT" -eq 0 ]; then\n',
    ),
    (
        "a bad value keeps the file an earlier start wrote",
        '[ "$CHECK" = yes ] || rm -f "$DST"\n',
        "",
    ),
    ("--check writes the file", '[ "$CHECK" = no ] || exit 0\n', ""),
    ("a number is anything", "number() {\n    case \"$1\" in\n", "number() {\n    return 0\n    case \"$1\" in\n"),
    (
        "an IPv6 entry may hold anything",
        "''|*[!0-9a-fA-F:]*|*:::*|*::*::*|:[!:]*|*[!:]:) return 1 ;;",
        "''|*:::*) return 1 ;;",
    ),
]


@pytest.mark.parametrize("case", [name for name, *_ in HOOK_MUTATIONS])
def test_each_trust_list_guard_can_fail(case: str, tmp_path: Path) -> None:
    (old, new) = next((o, n) for name, o, n in HOOK_MUTATIONS if name == case)
    text = HOOK.read_text()
    assert old in text, f"{case}: the mutation matches nothing in the script"
    cut = tmp_path / "trusted-proxies.sh"
    cut.write_text(text.replace(old, new, 1))
    assert hook_problems(cut) != [], f"{case}: the script guard stayed green"


# ---------------------------------------------------------------------------------------
# The live half: a real nginx, two recording stubs, loopback source addresses
# ---------------------------------------------------------------------------------------


def call(
    port: int,
    path: str,
    *,
    source: str = LOOPBACK,
    forwarded: list[str] | None = None,
    wait: float = 5.0,
) -> int:
    """One `POST` on its own connection FROM ``source``; each element of ``forwarded`` is one
    `X-Forwarded-For` header line (so two elements are two lines)."""
    body = b'{"login":"a","password":"b"}'
    head = [
        f"POST {path} HTTP/1.1",
        f"Host: 127.0.0.1:{port}",
        "Connection: close",
        "Content-Type: application/json",
        f"Content-Length: {len(body)}",
        *[f"X-Forwarded-For: {value}" for value in (forwarded or [])],
    ]
    with socket.socket() as connection:
        connection.settimeout(wait)
        connection.bind((source, 0))
        connection.connect((LOOPBACK, port))
        connection.sendall(("\r\n".join(head) + "\r\n\r\n").encode("latin-1") + body)
        received = b""
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            received += chunk
    return int(received.split(b" ", 2)[1]) if received.startswith(b"HTTP/") else 0


def real_ips(stub: Upstream, stub_path: str) -> list[str]:
    """The `X-Real-IP` each request that reached the application carried, in arrival order."""
    return [r["headers"].get("x-real-ip", "<none>") for r in stub.seen if r["path"] == stub_path]


def burst(port: int, path: str, forwarded: Callable[[int], list[str]] | None, *, source: str = LOOPBACK) -> list[int]:
    return [call(port, path, source=source, forwarded=forwarded(i) if forwarded else None) for i in range(BURST)]


def untrusted_scenarios(proxy_port: int, api: Upstream, *, peer: str = LOOPBACK) -> list[str]:
    """Nothing trusts ``peer``: a forged chain buys no bucket, and the application is told the peer."""
    problems: list[str] = []
    for zone, (path, stub_path, answer) in ZONES.items():
        before = len(real_ips(api, stub_path))
        statuses = burst(proxy_port, path, lambda i: [f"198.51.100.{i + 1}"], source=peer)
        if statuses != [answer] * BURST:
            problems.append(f"{zone}: the first {BURST} were {statuses}, wanted {[answer] * BURST}")
        twelfth = call(proxy_port, path, source=peer, forwarded=["198.51.100.200"])
        if twelfth != 429:
            problems.append(f"{zone}: a twelfth request with a never-seen forged address answered {twelfth}, not 429")
        seen = set(real_ips(api, stub_path)[before:])
        if seen != {peer}:
            problems.append(f"{zone}: the application was told X-Real-IP {sorted(seen)}, wanted only the peer {peer}")
    return problems


def trusted_scenarios(proxy_port: int, api: Upstream, *, peer: str = LOOPBACK) -> list[str]:
    """``peer`` is trusted: each client it names has a bucket of its own, in both zones."""
    problems: list[str] = []
    one, two = "198.51.100.10", "198.51.100.20"
    for zone, (path, stub_path, answer) in ZONES.items():
        before = len(real_ips(api, stub_path))
        spent = burst(proxy_port, path, lambda _i: [one], source=peer)
        if spent != [answer] * BURST:
            problems.append(f"{zone}: {one}'s first {BURST} were {spent}, wanted {[answer] * BURST}")
        if call(proxy_port, path, source=peer, forwarded=[one]) != 429:
            problems.append(f"{zone}: {one}'s twelfth was not refused")
        other = call(proxy_port, path, source=peer, forwarded=[two])
        if other != answer:
            problems.append(f"{zone}: {two} answered {other} while only {one} had spent a budget (wanted {answer})")
        if call(proxy_port, path, source=peer, forwarded=[one]) != 429:
            problems.append(f"{zone}: {one} was let off after {two} asked")
        seen = real_ips(api, stub_path)[before:]
        if seen != [one] * BURST + [two]:
            problems.append(f"{zone}: the application was told X-Real-IP {seen}, wanted {BURST}x {one} then {two}")
    # an IPv6 client is a client like any other, and does not share the IPv4 ones' buckets
    path, stub_path, answer = ZONES["token_exchange"]
    six = burst(proxy_port, path, lambda _i: ["2001:db8::1"], source=peer)
    if six != [answer] * BURST or call(proxy_port, path, source=peer, forwarded=["2001:db8::1"]) != 429:
        problems.append(f"an IPv6 client was not counted as one client: {six}")
    if call(proxy_port, path, source=peer, forwarded=["2001:db8::2"]) != answer:
        problems.append("a second IPv6 client shared the first one's bucket")
    if real_ips(api, stub_path)[-1] != "2001:db8::2":
        problems.append(f"X-Real-IP for an IPv6 client was {real_ips(api, stub_path)[-1]!r}")
    # a header that is not an address names nobody: the request is counted under the peer
    before = len(real_ips(api, stub_path))
    garbage = call(proxy_port, path, source=peer, forwarded=["not-an-address"])
    if garbage != answer or real_ips(api, stub_path)[before:] != [peer]:
        problems.append(f"an unparsable X-Forwarded-For: status {garbage}, X-Real-IP {real_ips(api, stub_path)[before:]}")
    return problems


def chain_scenarios(proxy_port: int, api: Upstream) -> list[str]:
    """The rule, chain by chain. 127.0.0.1 and the 192.0.2.0/24 hops are trusted."""
    problems: list[str] = []
    path, stub_path, answer = ZONES["token_exchange"]
    # 1. an address written at the LEFT is never read: eleven different forgeries in front of one
    #    real client are one client, and a forged address is not charged for what that client did.
    client, forged_victim = "198.51.100.31", "203.0.113.5"
    spent = burst(proxy_port, path, lambda i: [f"203.0.113.{i + 100}, {client}"])
    if spent != [answer] * BURST:
        problems.append(f"chains with eleven different forged heads were {spent}")
    if call(proxy_port, path, forwarded=[f"{forged_victim}, {client}"]) != 429:
        problems.append("a twelfth forged head bought a new bucket: the left of the chain was read")
    if call(proxy_port, path, forwarded=[forged_victim]) != answer:
        problems.append("an address that only ever appeared at the left of a chain was charged for it")
    # 2. trusted hops are stepped over (`real_ip_recursive on`): the client is the first address
    #    from the right that is not itself trusted.
    behind_hops, other = "198.51.100.32", "198.51.100.33"
    spent = burst(proxy_port, path, lambda i: [f"{behind_hops}, 192.0.2.{i + 1}"])
    if spent != [answer] * BURST:
        problems.append(f"requests behind trusted hops were {spent}")
    if call(proxy_port, path, forwarded=[f"{behind_hops}, 192.0.2.250"]) != 429:
        problems.append("a different trusted hop bought a new bucket: the hop was taken for the client (recursion is off)")
    if call(proxy_port, path, forwarded=[f"{other}, 192.0.2.1"]) != answer:
        problems.append("another client behind the same hop shared the first one's bucket")
    # 3. the RIGHTMOST untrusted address wins, so "attacker, victim" charges the VICTIM. That is
    #    what the README tells the operator to prevent on the host terminator: it must set the
    #    header to `$remote_addr` (or append to it), never forward a client's chain unchanged.
    victim = "198.51.100.34"
    spent = burst(proxy_port, path, lambda i: [f"203.0.113.{i + 150}, {victim}"])
    if spent != [answer] * BURST or call(proxy_port, path, forwarded=[victim]) != 429:
        problems.append("'attacker, victim' did not charge the victim, the rightmost address (the documented rule)")
    # 4. two header lines are one chain: the LAST line's rightmost address is the client.
    last = "198.51.100.35"
    spent = burst(proxy_port, path, lambda i: [f"203.0.113.{i + 180}", last])
    if spent != [answer] * BURST or call(proxy_port, path, forwarded=[last]) != 429:
        problems.append("two X-Forwarded-For lines were not read as one chain ending at the last line")
    return problems


def _plain_with(lines: str) -> str:
    return with_trust(PLAIN.read_text(), lines)


def drive(scenarios: Callable[..., list[str]], plain: str, *, body: str) -> list[str]:
    with running(plain, TLS_BLOCK.read_text(), body=body) as (proxy, api, _web):
        return scenarios(proxy.port, api)


@needs_nginx
@pytest.mark.parametrize("body", ["plain", "tls"])
def test_with_nothing_trusted_a_forged_chain_buys_no_bucket_live(body: str) -> None:
    """The default: `ALPHA_TRUSTED_PROXY_CIDRS` empty. Today's behaviour, and no way to spoof."""
    assert trust_lines("") == ""
    assert drive(untrusted_scenarios, _plain_with(""), body=body) == []


@needs_nginx
@pytest.mark.parametrize("body", ["plain", "tls"])
def test_a_peer_outside_the_list_is_not_believed_live(body: str) -> None:
    """A list that does not contain the connecting peer changes nothing for that peer."""
    lines = trust_lines("127.0.0.9/32, 192.0.2.0/24")
    assert "set_real_ip_from 127.0.0.9/32;" in lines
    assert drive(untrusted_scenarios, _plain_with(lines), body=body) == []


@needs_nginx
@pytest.mark.parametrize("body", ["plain", "tls"])
def test_a_trusted_peer_names_the_client_in_both_zones_live(body: str) -> None:
    assert drive(trusted_scenarios, _plain_with(trust_lines("127.0.0.1/32")), body=body) == []


@needs_nginx
def test_an_untrusted_peer_beside_a_trusted_one_is_still_not_believed_live() -> None:
    """The list is per peer: 127.0.0.1 is trusted, 127.0.0.2 connecting to the same proxy is not."""
    lines = trust_lines("127.0.0.1/32")
    plain = _plain_with(lines)
    with running(plain, TLS_BLOCK.read_text(), body="plain") as (proxy, api, _web):
        assert untrusted_scenarios(proxy.port, api, peer="127.0.0.2") == []


@needs_nginx
@pytest.mark.parametrize("body", ["plain", "tls"])
def test_the_rule_reads_chains_from_the_right_live(body: str) -> None:
    lines = trust_lines("127.0.0.1/32, 192.0.2.0/24")
    assert drive(chain_scenarios, _plain_with(lines), body=body) == []


#: Which live driver sees which mutation: (driver, trust list, file body).
LIVE_SEES: dict[str, tuple[Callable[..., list[str]], str, str]] = {
    "recursion is off": (chain_scenarios, "127.0.0.1/32, 192.0.2.0/24", "plain"),
    "the header is X-Real-IP": (trusted_scenarios, "127.0.0.1/32", "plain"),
    "the header line is gone": (trusted_scenarios, "127.0.0.1/32", "plain"),
    "the recursion line is gone": (chain_scenarios, "127.0.0.1/32, 192.0.2.0/24", "plain"),
    "nginx.conf trusts everyone": (untrusted_scenarios, "", "plain"),
    "nginx.conf trusts the loopback": (untrusted_scenarios, "", "plain"),
    MOVED: (trusted_scenarios, "127.0.0.1/32", "tls"),
}


@needs_nginx
@pytest.mark.parametrize("case", sorted(LIVE_SEES))
def test_each_live_guard_can_fail(case: str) -> None:
    driver, cidrs, body = LIVE_SEES[case]
    plain, _ = mutated(case, PLAIN.read_text(), TLS_BLOCK.read_text())
    assert drive(driver, with_trust(plain, trust_lines(cidrs)), body=body) != [], f"{case}: the live guard stayed green"


# ---------------------------------------------------------------------------------------
# The pinned image: the same files, mounted as compose mounts them, run by the image's own
# entrypoint (busybox `sh`, the real hook order) -- `nginx -T` dumps the configuration it loaded
# ---------------------------------------------------------------------------------------


def _pinned_image() -> str | None:
    match = re.search(r"^\s+image: (nginx:\S+)$", COMPOSE.read_text(), re.M)
    if match is None or shutil.which("docker") is None:
        return None
    present = subprocess.run(["docker", "image", "inspect", match.group(1)], capture_output=True)
    return match.group(1) if present.returncode == 0 else None


needs_image = pytest.mark.skipif(
    _pinned_image() is None,
    reason="docker, or the pinned proxy image from compose.server.yml, is not present locally (nothing is pulled)",
)


def image_dump(value: str | None) -> subprocess.CompletedProcess[str]:
    image = _pinned_image()
    assert image is not None
    environment = ["-e", f"{VARIABLE}={value}"] if value is not None else []
    return subprocess.run(
        [
            "docker", "run", "--rm", "--add-host", "api:127.0.0.1", "--add-host", "web:127.0.0.1",
            "-v", f"{PLAIN}:/etc/nginx/conf.d/default.conf:ro",
            "-v", f"{HOOK}:{HOOK_TARGET}:ro",
            *environment, image, "nginx", "-T",
        ],
        capture_output=True, text=True, timeout=120,
    )


def loaded_directives(dump: str) -> list[str]:
    """`nginx -T` prints every file with its comments, and the comments here name the directive."""
    return [x for x in (line.split("#", 1)[0].strip() for line in dump.splitlines()) if x]


@needs_image
@pytest.mark.parametrize("value", [None, ""])
def test_the_image_starts_and_trusts_nobody_when_the_value_is_empty(value: str | None) -> None:
    done = image_dump(value)
    assert done.returncode == 0, done.stderr
    assert "syntax is ok" in done.stderr and "test is successful" in done.stderr, done.stderr
    loaded = loaded_directives(done.stdout)
    assert not [x for x in loaded if x.startswith("set_real_ip_from")], "an empty value must trust nobody"
    assert "real_ip_header X-Forwarded-For;" in loaded and "real_ip_recursive on;" in loaded
    assert "no peer is trusted" in done.stderr, "the empty branch must say so on the container log"


@needs_image
def test_the_image_loads_the_list_the_hook_wrote() -> None:
    done = image_dump("172.29.0.1/32 fd00::/8")
    assert done.returncode == 0, done.stderr
    assert "syntax is ok" in done.stderr, done.stderr
    loaded = re.search(
        r"# configuration file /etc/nginx/conf\.d/trusted-proxies\.conf:\n(.*?)(?:\n# configuration file|\Z)",
        done.stdout, re.S,
    )
    assert loaded is not None, "nginx did not load conf.d/trusted-proxies.conf"
    assert [x for x in loaded.group(1).splitlines() if x and not x.startswith("#")] == [
        "set_real_ip_from 172.29.0.1/32;",
        "set_real_ip_from fd00::/8;",
    ]
    assert "2 peer(s) trusted" in done.stderr


@needs_image
@pytest.mark.parametrize("value", ["0.0.0.0/0", "172.29.0.1; return 200", "proxy.example"])
def test_the_image_does_not_start_on_a_bad_value(value: str) -> None:
    done = image_dump(value)
    assert done.returncode != 0, "the container started on a refused trust list"
    assert "refused" in done.stderr, done.stderr
    assert "syntax is ok" not in done.stderr
    assert not [x for x in loaded_directives(done.stdout) if x.startswith("set_real_ip_from")]


# ---------------------------------------------------------------------------------------
# Compose renders what the file claims
# ---------------------------------------------------------------------------------------


def _rendered_proxy(extra: str) -> dict[str, object]:
    # Under the repository and not under /tmp: a `docker` command on this host does not see the
    # test process's /tmp (the daemon resolves paths itself -- `D-37`).
    scratch = ROOT / ".local"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="realip-compose-", dir=scratch) as raw:
        env = Path(raw) / "alpha.env"
        env.write_text(ENV_EXAMPLE.read_text() + extra)
        done = subprocess.run(
            ["docker", "compose", "--env-file", str(env), "-f", str(COMPOSE), "config", "--format", "json"],
            capture_output=True, text=True, timeout=120,
        )
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)["services"]["proxy"]


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
@pytest.mark.parametrize(("extra", "value"), [("", ""), (f"\n{VARIABLE}=172.29.0.1/32\n", "172.29.0.1/32")])
def test_compose_hands_the_value_to_the_container_and_mounts_the_hook(extra: str, value: str) -> None:
    proxy = _rendered_proxy(extra)
    assert proxy["environment"] == {VARIABLE: value}  # type: ignore[index]
    mounts = {v["target"]: v for v in proxy["volumes"]}  # type: ignore[attr-defined]
    hook = mounts[HOOK_TARGET]
    assert Path(hook["source"]).name == HOOK.name and hook["read_only"] is True
    assert Path(hook["source"]).resolve() == HOOK.resolve()
