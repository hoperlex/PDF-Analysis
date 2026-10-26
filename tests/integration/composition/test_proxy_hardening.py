"""`HARDEN-01` / `F-16` (`EXPOSURE-REVIEW-02`, `D-242`): the proxy's TLS 1.2 suites are AEAD only, and its banner
carries no version.

The finding: ``tls-server.conf`` said "1.2's suites here are all AEAD" while NO ``ssl_ciphers`` was set, and nginx's
default ``HIGH:!aNULL:!MD5`` offers twenty non-AEAD TLS 1.2 suites (CBC, and static-RSA without forward secrecy) with
OpenSSL 3.0.13 -- measured with ``openssl ciphers -v``. And ``server_tokens`` was never turned off, so every answer
carried ``Server: nginx/<version>`` (1.24.0 on the live stand).

What is asserted is the configuration; what it DOES was measured once against a real nginx on loopback
(``docs/program/HARDEN-01.md``: a TLS 1.2 handshake restricted to ``ECDHE-RSA-AES256-SHA384`` was accepted by the old
file and answered ``handshake failure`` by the new one; ``Server: nginx/1.24.0 (Ubuntu)`` became ``Server: nginx``).
The served answer is asserted on a deployed stack by ``verify-deployed.sh`` (``test_verify_deployed_served_headers.py``).

No docker, no network: the files are read, comments removed, as the neighbours do.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PROXY = ROOT / "infra/deploy/proxy"
PLAIN = PROXY / "nginx.conf"
TLS_BLOCK = PROXY / "tls-server.conf"

#: ECDHE key exchange (forward secrecy) with an AEAD cipher: the whole TLS 1.2 vocabulary this proxy offers.
AEAD_SUITE = re.compile(r"^ECDHE-(?:ECDSA|RSA)-(?:AES(?:128|256)-GCM-SHA(?:256|384)|CHACHA20-POLY1305)$")


def _directives(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(" ".join(line.split()))
    return out


def _values(text: str, name: str) -> list[str]:
    """The value of every ``name <value>;`` directive, comments removed."""
    found = []
    for line in _directives(text):
        match = re.fullmatch(rf"{re.escape(name)}\s+(.+?);", line)
        if match:
            found.append(match.group(1))
    return found


def cipher_problems(config: str) -> list[str]:
    """What is wrong with the ``ssl_ciphers`` of one TLS server block, in words. Empty when it is AEAD-only."""
    lists = _values(config, "ssl_ciphers")
    if len(lists) != 1:
        return [f"expected exactly one ssl_ciphers directive, found {len(lists)}"]
    suites = lists[0].split(":")
    problems = [f"{suite!r} is not an ECDHE AEAD suite" for suite in suites if not AEAD_SUITE.fullmatch(suite)]
    if not any("-RSA-" in suite for suite in suites) or not any("-ECDSA-" in suite for suite in suites):
        problems.append("the list must serve an RSA pair and an ECDSA pair alike (the key type is the ACME client's choice)")
    return problems


def banner_problems(files: dict[str, str]) -> list[str]:
    """``server_tokens`` must be off once at http level (the plain file), and on in no file."""
    problems = []
    for name, text in sorted(files.items()):
        values = _values(text, "server_tokens")
        if any(value != "off" for value in values):
            problems.append(f"{name} sets server_tokens to something other than off")
    plain = files["nginx.conf"]
    before_first_server = plain.split("\nserver {", 1)[0]
    if _values(before_first_server, "server_tokens") != ["off"]:
        problems.append("nginx.conf does not set server_tokens off at http level, before its first server block")
    return problems


def _proxy_files() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(PROXY.glob("*.conf"))}


class TestTheTlsOneTwoSuitesAreAeadOnly:
    def test_the_tls_block_lists_only_ecdhe_aead_suites_for_both_key_types(self) -> None:
        assert cipher_problems(TLS_BLOCK.read_text(encoding="utf-8")) == []

    def test_the_plain_configuration_carries_no_cipher_list_of_its_own(self) -> None:
        """A list in the always-loaded file would apply to nothing (no ``listen ... ssl``) and read as if it did."""
        assert _values(PLAIN.read_text(encoding="utf-8"), "ssl_ciphers") == []

    def test_the_protocols_are_still_one_two_and_one_three_only(self) -> None:
        assert _values(TLS_BLOCK.read_text(encoding="utf-8"), "ssl_protocols") == ["TLSv1.2 TLSv1.3"]

    def test_openssl_agrees_that_every_suite_is_aead_with_forward_secrecy(self) -> None:
        """The list as the library reads it, when the host has the library's command: no name is taken on trust."""
        openssl = shutil.which("openssl")
        if openssl is None:
            pytest.skip("openssl is not on PATH on this host; the pattern test above still holds the list")
        (spec,) = _values(TLS_BLOCK.read_text(encoding="utf-8"), "ssl_ciphers")
        completed = subprocess.run([openssl, "ciphers", "-v", spec], capture_output=True, text=True, check=False)
        assert completed.returncode == 0, completed.stderr
        tls12 = [line for line in completed.stdout.splitlines() if " TLSv1.2 " in line]
        assert len(tls12) == len(spec.split(":")), completed.stdout
        for line in tls12:
            assert "Mac=AEAD" in line and "Kx=ECDH" in line, line

    @pytest.mark.parametrize(
        ("mutation", "fragment"),
        [
            (lambda text: text.replace(":ECDHE-RSA-CHACHA20-POLY1305", ":ECDHE-RSA-AES256-SHA384"), "ECDHE-RSA-AES256-SHA384"),
            (lambda text: text.replace(":ECDHE-RSA-CHACHA20-POLY1305", ":AES128-SHA"), "AES128-SHA"),
            (lambda text: text.replace(":ECDHE-RSA-CHACHA20-POLY1305", ":DHE-RSA-AES256-GCM-SHA384"), "DHE-RSA-AES256-GCM-SHA384"),
            (lambda text: re.sub(r"ssl_ciphers [^;]+;", "ssl_ciphers HIGH:!aNULL:!MD5;", text), "HIGH"),
            (lambda text: re.sub(r"^\s*ssl_ciphers [^;]+;\n", "", text, flags=re.MULTILINE), "exactly one"),
            (lambda text: text.replace("ssl_prefer_server_ciphers off;", "ssl_prefer_server_ciphers off;\n    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256;"), "exactly one"),
        ],
        ids=["cbc", "static-rsa", "dhe", "the-default", "no-list", "two-lists"],
    )
    def test_the_check_can_fail(self, mutation, fragment: str) -> None:  # type: ignore[no-untyped-def]
        original = TLS_BLOCK.read_text(encoding="utf-8")
        mutated = mutation(original)
        assert mutated != original
        problems = cipher_problems(mutated)
        assert problems and any(fragment in problem for problem in problems), problems

    def test_a_list_for_one_key_type_only_is_refused(self) -> None:
        original = TLS_BLOCK.read_text(encoding="utf-8")
        rsa_only = re.sub(
            r"ssl_ciphers [^;]+;",
            "ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;",
            original,
        )
        assert any("RSA pair and an ECDSA pair" in problem for problem in cipher_problems(rsa_only))


class TestTheBannerCarriesNoVersion:
    def test_server_tokens_is_off_once_at_http_level_and_on_nowhere(self) -> None:
        files = _proxy_files()
        assert {"nginx.conf", "tls-server.conf", "acme-challenge.conf"} <= set(files), sorted(files)
        assert banner_problems(files) == []

    @pytest.mark.parametrize(
        ("name", "mutation", "fragment"),
        [
            ("nginx.conf", lambda text: re.sub(r"^server_tokens off;\n", "", text, flags=re.MULTILINE), "does not set server_tokens off"),
            ("nginx.conf", lambda text: text.replace("server_tokens off;", "server_tokens on;", 1), "something other than off"),
            ("tls-server.conf", lambda text: text.replace("    http2 on;", "    http2 on;\n    server_tokens on;", 1), "something other than off"),
            ("acme-challenge.conf", lambda text: text.replace("    listen 8081;", "    listen 8081;\n    server_tokens build;", 1), "something other than off"),
            # off, but inside the server block: it would cover that block alone, and the other two would still print it
            (
                "nginx.conf",
                lambda text: re.sub(r"^server_tokens off;\n", "", text, count=1, flags=re.MULTILINE).replace(
                    "    listen 8080;", "    listen 8080;\n    server_tokens off;", 1
                ),
                "at http level",
            ),
        ],
        ids=["removed", "on", "on-in-the-tls-block", "build-in-the-challenge-block", "only-in-one-server"],
    )
    def test_the_check_can_fail(self, name: str, mutation, fragment: str) -> None:  # type: ignore[no-untyped-def]
        files = _proxy_files()
        mutated = dict(files)
        mutated[name] = mutation(files[name])
        assert mutated[name] != files[name], f"the mutation changed nothing in {name}"
        problems = banner_problems(mutated)
        assert problems and any(fragment in problem for problem in problems), problems
