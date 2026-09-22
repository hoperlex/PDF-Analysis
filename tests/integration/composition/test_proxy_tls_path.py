"""`R-15` -- the TLS path that activates on a certificate and is inert without one.

**What this file can and cannot prove.** The two halves -- the stack serving plain HTTP
with no certificate present, and serving TLS when one is -- were driven against real
containers and are recorded with their output in `docs/program/reviews/W26-HOST.md` §2,
including the control that shows the naive shape (`ssl_certificate` in a file nginx always
loads) exiting **1** with `[emerg] cannot load certificate`. That is a proof about a
running nginx and it does not belong in the battery, which touches no daemon.

What belongs here is everything that would make those proofs stop being true without
anyone noticing:

* the plain configuration never grows a TLS directive, so the served config cannot start
  depending on a certificate;
* the TLS block stays OUT of `conf.d/`, which is the whole mechanism -- nginx parses
  `ssl_certificate` at load time, so a block it always loads is a block that takes the
  site down on a host that has no certificate yet;
* the switch keeps un-installing on the disabled branch. A restarted container keeps its
  writable layer, so a `tls.conf` left behind after a certificate is removed would make
  nginx refuse to start;
* the two server bodies do not drift. They are duplicated on purpose -- `nginx.conf` is
  bind-mounted as a single file and a shared `include` would need a second mount in
  `compose.server.yml`, which `W26-OPS` owns -- so the drift is checked instead of avoided;
* no private key can be committed, asked of `git check-ignore` rather than of a comment.

**Every check here is shown able to fail**, in `test_*_can_fail`, by putting the mutation
in front of the same function the real check uses. A guard nobody has watched fail is a
guard nobody has tested.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PROXY = ROOT / "infra/deploy/proxy"
PLAIN = PROXY / "nginx.conf"
TLS_BLOCK = PROXY / "tls-server.conf"
SWITCH = PROXY / "enable-tls.sh"
OVERLAY = PROXY / "compose.tls.yml"
BASE_COMPOSE = ROOT / "infra/deploy/compose.server.yml"

#: Where the overlay must put each file inside the container, and why the path matters.
#: `tls-server.conf` is deliberately NOT under `/etc/nginx/conf.d/`, which the image's own
#: `include /etc/nginx/conf.d/*.conf;` is the only thing that reads.
MOUNTS = {
    "./proxy/tls": "/etc/nginx/tls",
    "./proxy/tls-server.conf": "/etc/nginx/tls-server.conf",
    "./proxy/enable-tls.sh": "/docker-entrypoint.d/25-enable-tls.sh",
}


def directives(config: str) -> list[str]:
    """The directive sequence of a config, with comments, blank lines and spacing gone.

    This is what "the two server bodies are the same body" is checked against. Comparing
    bytes would fail on the first comment either file grows; comparing this fails only
    when what nginx *does* differs.
    """
    out: list[str] = []
    for raw in config.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(" ".join(line.split()))
    return out


def application_body(config: str) -> list[str]:
    """The directives of a `server { }` block below its listener and `server_name`.

    Everything from the first directive that is neither `listen`, `http2`, `server_name`
    nor `ssl_*` down to the closing brace -- i.e. the part that is about the application
    rather than about the transport.
    """
    lines = directives(config)
    try:
        start = next(
            i
            for i, line in enumerate(lines)
            if line.startswith("server {") or line == "server {"
        )
    except StopIteration:  # pragma: no cover - a config with no server block
        pytest.fail("no `server {` block in this configuration")
    body = lines[start + 1 : -1] if lines[-1] == "}" else lines[start + 1 :]
    transport = ("listen ", "http2 ", "server_name ", "ssl_")
    return [line for line in body if not line.startswith(transport)]


def test_the_plain_configuration_carries_no_tls_at_all() -> None:
    """The file `compose.server.yml` mounts must never need a certificate.

    `W14-PKG` refused to write a `listen 443 ssl` block naming a certificate that has never
    existed, and `R-15` did not overturn that -- it asked for a path that switches on. This
    is the assertion that the switched-on path did not leak back into the always-loaded
    one.
    """
    body = PLAIN.read_text()
    assert "ssl_certificate" not in "\n".join(directives(body))
    assert not re.search(r"^\s*listen\s+(443|8443)", body, re.MULTILINE)


def test_the_tls_block_is_mounted_outside_conf_d() -> None:
    """The mechanism, stated as an assertion.

    nginx reads `ssl_certificate` when it PARSES the configuration, not when a connection
    arrives, so a TLS block under `conf.d/` is loaded whether or not the certificate is
    there -- and on a host that has none, the master refuses to start and the one published
    port goes dark. Driven, exit 1: `W26-HOST.md` §2.3.
    """
    overlay = OVERLAY.read_text()
    assert f"{TLS_BLOCK.name}:/etc/nginx/conf.d" not in overlay
    for source, target in MOUNTS.items():
        assert f"{source}:{target}:ro" in overlay, f"{source} is not mounted read-only at {target}"
    assert "/etc/nginx/conf.d" not in overlay


def test_the_switch_is_executable_in_git() -> None:
    """The image runs `/docker-entrypoint.d/*.sh` only when the file is executable.

    A bind mount carries the host's mode, and the host gets it from the clone -- so the
    mode has to be right in git, not on somebody's disk. The image's entrypoint prints
    "Ignoring ...: not executable" and carries on, which is the quietest possible way for
    this whole path to do nothing.
    """
    mode = subprocess.run(
        ["git", "ls-files", "--stage", "--", str(SWITCH.relative_to(ROOT))],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert mode and mode[0] == "100755", f"{SWITCH.name} is {mode[0] if mode else 'untracked'} in git"


def test_the_disabled_branch_uninstalls_a_stale_block() -> None:
    """A restarted container keeps its writable layer.

    So the branch that says "no certificate" has to REMOVE what an earlier start installed.
    Without this, taking a certificate away and restarting leaves nginx loading a block
    whose files are gone -- the failure this whole design exists to avoid, arrived at from
    the other side.
    """
    script = SWITCH.read_text()
    off = script[script.index("off() {") : script.index("exit 0\n}")]
    assert 'rm -f "$DST"' in off
    assert off.index('rm -f "$DST"') < off.index("say "), "it announces before it un-installs"


def test_the_two_server_bodies_do_not_drift() -> None:
    """The duplication is deliberate; the drift is not.

    `nginx.conf` is bind-mounted as ONE file, so the shared application body cannot be
    factored into an `include` without a second mount in `compose.server.yml` -- which
    another session owns this wave. The body is therefore copied, and this is the thing
    that makes the copy honest.
    """
    assert application_body(PLAIN.read_text()) == application_body(TLS_BLOCK.read_text())


def test_the_drift_check_can_fail() -> None:
    """The mutation this guard exists for, put in front of the same function."""
    mutated = TLS_BLOCK.read_text().replace("proxy_read_timeout 300s;", "proxy_read_timeout 30s;")
    assert mutated != TLS_BLOCK.read_text()
    assert application_body(PLAIN.read_text()) != application_body(mutated)


def test_a_private_key_cannot_be_committed() -> None:
    """Asked of git, not of the comment in `.gitignore`."""
    for name in ("privkey.pem", "fullchain.pem", "anything.key"):
        path = PROXY / "tls" / name
        assert subprocess.run(
            ["git", "check-ignore", "--quiet", "--", str(path.relative_to(ROOT))], cwd=ROOT
        ).returncode == 0, f"{name} would be committable"
    assert subprocess.run(
        ["git", "check-ignore", "--quiet", "--", "infra/deploy/proxy/tls/.gitignore"], cwd=ROOT
    ).returncode == 1, "the directory itself must stay tracked, or a clean clone has no mount source"


def test_the_overlay_introduces_no_name_that_could_hold_a_secret() -> None:
    """`docker compose config` prints substituted values, and a key must never be one.

    The certificate reaches the container as a PATH on a read-only mount, exactly as the
    provider credential reaches it through `env_file:` -- so neither ever enters compose
    substitution. The only variable this overlay adds is a port number.
    """
    used = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", OVERLAY.read_text()))
    # `ALPHA_BIND_ADDRESS` joined `ALPHA_HTTPS_PORT` on 2026-09-22, closing `D-49`: both
    # published ports bind `127.0.0.1` unless a host deliberately says otherwise, and the
    # overlay must carry the same rule as the base or a host would be published on one port
    # and not the other.
    #
    # THIS GUARD DID ITS JOB AND IS NOT BEING WEAKENED. It is here because `docker compose
    # config` prints substituted values in clear -- `D-42` measured that the provider
    # credential appears there -- so every name this overlay substitutes has to be one that
    # is safe to print. An interface address is: it is where the port listens, it is visible
    # in `docker port` and in `ss -ltn` to anyone on the host already, and it names no
    # endpoint, host, bucket or key. The set stays exhaustive and each member is reasoned.
    assert used == {"ALPHA_HTTPS_PORT", "ALPHA_BIND_ADDRESS"}, (
        f"the TLS overlay substitutes {sorted(used)}. Every name here is printed in clear by "
        "`docker compose config`, so a new one is only admissible if it cannot carry a "
        "secret -- and admitting it means saying so here, in this list."
    )
    assert "${ALPHA_HTTPS_PORT:-443}" in OVERLAY.read_text(), "it must default, or the base deploy breaks"


def _without_comments(text: str) -> str:
    """The configuration a compose file states, with the prose it carries stripped out.

    A `#` inside a quoted value is not a comment, so lines are kept whole and only a `#`
    that starts a line (after indentation) removes it. That is conservative in the safe
    direction: a trailing-comment mention would still fail the assertion, which is a false
    red rather than a missed one.
    """
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def test_the_base_deployment_is_unchanged_by_any_of_this() -> None:
    """Without the second `-f`, the certified stack is the certified stack.

    That is also the rollback: an operator turns TLS off by dropping one argument, and
    what they lose is the TLS listener and nothing else.
    """
    base = BASE_COMPOSE.read_text()

    # The claim is about CONFIGURATION, not about the word. This assertion read the whole
    # file, so it forbade `tls` in a comment too -- and on 2026-09-22 a comment explaining
    # `ALPHA_BIND_ADDRESS` mentioned serving TLS under `R-1` and turned the gate red on a
    # base that had gained no TLS whatsoever. Three live lanes were standing on that commit.
    #
    # Comments are stripped and the assertion is otherwise unchanged and no weaker: a real
    # `tls`-bearing key, value or filename in the base still fails it, and
    # `test_the_stripped_assertion_still_catches_real_tls_in_the_base` below proves exactly
    # that by feeding it one.
    directives = _without_comments(base)
    assert "tls" not in directives.lower(), (
        "the base compose gained TLS configuration; it is meant to be the certified stack "
        "until a second -f is passed"
    )
    assert "443" not in directives


def test_the_stripped_assertion_still_catches_real_tls_in_the_base() -> None:
    """The control for the comment-stripping above: it must not have made the guard vacuous.

    `_without_comments` exists so prose cannot redden a configuration claim. This case feeds
    the same assertion a base that really has gained TLS -- as a key, as a value and as a
    filename -- and requires each to be caught. Without it, stripping comments would be
    indistinguishable from deleting the check.
    """
    for injected in (
        '      - "./proxy/tls-server.conf:/etc/nginx/tls.conf:ro"',
        "        ALPHA_TLS_ENABLED: 1",
        '      - "${ALPHA_HTTPS_PORT:-443}:8443"',
    ):
        polluted = _without_comments(BASE_COMPOSE.read_text() + "\n" + injected)
        assert "tls" in polluted.lower() or "443" in polluted, (
            f"a base compose carrying {injected!r} was not caught after comment stripping; "
            "the strip has made the assertion vacuous"
        )
