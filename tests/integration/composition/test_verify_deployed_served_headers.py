"""`HARDEN-01` / `F-17` (`EXPOSURE-REVIEW-02`, `D-234`): `verify-deployed.sh` judges what the proxy ANSWERS on the
served name, not only what its configuration says.

`E-2` found HSTS, the `Secure` flag of the session cookie and the four security headers in the configuration; the
static tests read the configuration, and nothing asserted the answer, so a proxy that lost a header (or a web tier
that stopped believing `X-Forwarded-Proto`) would have stayed green. This file drives the new section 4b of the
script (``# --- 4b. what the proxy answers on that name``) through the answers the one request can get.

**What the script does and this file reads.** With ``ALPHA_CERT_NAME`` set, after the certificate is acceptable, it
sends ``GET /bff/v1/me`` with a well-formed session cookie that names no session to the proxy's TLS listener, from a
one-off container of the ACME image (the host promises no ``openssl``), and judges the RAW HEADERS that come back:
HSTS (a year, no ``includeSubDomains``/``preload``), the four ``C-18`` headers with their values, no version in
``Server`` (``F-16``) and the ``Secure`` attribute of the cleared ``am_session`` cookie the web tier answers with.
A finding is exit ``9``. An answer that cannot be read, or has no session cookie to judge, is exit ``4`` -- "no
finding" is not claimed for a property that was not observed.

**No network.** The same harness as ``test_verify_deployed_certificate.py`` and ``test_deployed_stack_probe.py``: a
``docker`` stub that answers the probe from the environment. The request the probe builds is tested separately by
running the probe's own text with an ``openssl`` that prints what it was sent.
"""

from __future__ import annotations

import importlib.util
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, relative: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cert = _load("cert_harness", "tests/integration/composition/test_verify_deployed_certificate.py")
probe = cert.probe  # ONE harness module: the neighbour's `_verify` runs the stub that is patched here

world = probe.world  # the fixture, by the name pytest finds it under

NAME = cert.NAME
HEADERS = 9
UNANSWERABLE = probe.UNANSWERABLE
CERTIFICATE = cert.CERTIFICATE
DRIFT = probe.DRIFT
MARKER = "served-headers-probe"
STALE_SESSION = "0" * 64

#: The answer a healthy stack gives: 401 and a cleared, `Secure` session cookie, with every header.
GOOD = (
    "HTTP/1.1 401 Unauthorized\r\n"
    "Server: nginx\r\n"
    "Content-Type: application/json\r\n"
    "Set-Cookie: am_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0; Secure\r\n"
    "Strict-Transport-Security: max-age=31536000\r\n"
    "X-Content-Type-Options: nosniff\r\n"
    "X-Frame-Options: DENY\r\n"
    "Content-Security-Policy: frame-ancestors 'none'\r\n"
    "Referrer-Policy: same-origin\r\n"
    "\r\n"
    '{"error_code": "authentication_required"}'
)


def _without(header: str, answer: str = GOOD) -> str:
    kept = [line for line in answer.split("\r\n") if not line.lower().startswith(header.lower() + ":")]
    assert len(kept) == len(answer.split("\r\n")) - 1, f"{header} was not in the good answer exactly once"
    return "\r\n".join(kept)


def _replace(old: str, new: str, answer: str = GOOD) -> str:
    assert old in answer
    return answer.replace(old, new, 1)


@pytest.fixture(autouse=True)
def _docker_that_also_answers_the_certificate_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """The certificate branch of the neighbour file, so a case here can refuse the certificate."""
    assert probe.DOCKER_STUB.count(cert.ANCHOR) == 1, "the harness's docker stub changed shape; move the branch"
    monkeypatch.setattr(probe, "DOCKER_STUB", probe.DOCKER_STUB.replace(cert.ANCHOR, cert.CERT_BRANCH + cert.ANCHOR, 1))


def _verify(world, tmp_path: Path, *args: str, name: str | None = NAME, script: Path | None = None, **stub: str):  # type: ignore[no-untyped-def]
    env = cert._tls_env(tmp_path, name=name, staging="no" if name else None)
    return cert._verify(world, tmp_path, *args, env=env, script=script, **stub)


def _probe_calls(calls: str) -> list[str]:
    """Each logged docker call that is the headers probe. A call spans lines (the probe text has newlines)."""
    entries = re.split(r"(?m)^(?=compose )", calls)
    return [entry for entry in entries if MARKER in entry]


class TestItIsAskedOnlyWhenThereIsAName:
    def test_without_a_name_the_script_is_what_it_was(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, name=None)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "the headers and the session cookie" not in completed.stdout
        assert _probe_calls(calls) == []

    def test_with_a_name_the_question_is_the_right_one(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "-- the headers and the session cookie the proxy serves --" in completed.stdout
        (asked,) = _probe_calls(calls)
        # the base file and the acme overlay, the one-off container, a shell with the probe text, the name as
        # SNI and Host, the proxy's own TLS listener, and a session identifier that names no session
        assert re.search(r"--file \S+compose\.server\.yml --file \S+acme/compose\.acme\.yml run --rm --no-deps -T", asked), asked
        assert "--entrypoint sh acme -c " in asked, asked
        assert "openssl s_client" in asked and "GET /bff/v1/me HTTP/1.1" in asked, asked
        assert asked.rstrip().endswith(f"{MARKER} {NAME} proxy:8443 {STALE_SESSION}"), asked
        assert "HSTS max-age=31536000" in completed.stdout and "session cookie is Secure" in completed.stdout
        assert "IS this tree" in completed.stdout

    def test_header_names_are_not_case_sensitive(self, world, tmp_path: Path) -> None:
        """HTTP/2 and some proxies spell them in lower case; the check must not call that a missing header."""
        lowered = "\r\n".join(
            (line.split(":", 1)[0].lower() + ":" + line.split(":", 1)[1]) if ":" in line and not line.startswith("HTTP") else line
            for line in GOOD.split("\r\n")
        )
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=lowered)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_the_cookie_attribute_is_found_wherever_it_stands_and_in_any_case(self, world, tmp_path: Path) -> None:
        moved = _replace("Path=/; HttpOnly; SameSite=Strict; Max-Age=0; Secure", "Path=/; secure; HttpOnly; SameSite=Strict; Max-Age=0")
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=moved)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_it_is_asked_after_the_certificate_is_accepted_and_never_instead_of_it(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(
            world, tmp_path, STUB_CERT_STATUS="11", STUB_CERT_OUTPUT="served-certificate: EXPIRING -- soon\n"
        )
        assert completed.returncode == CERTIFICATE, (completed.stdout, completed.stderr)
        assert _probe_calls(calls) == [], "the headers were asked of a stack whose certificate was refused"

    def test_drift_wins_and_the_headers_are_not_asked(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, STUB_CORRUPT="/app/src/auditmanager/runs/carrier.py")
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert _probe_calls(calls) == []


#: (id, the answer, a fragment the message must name). Each is one thing the configuration promises.
FINDINGS = [
    ("hsts-absent", _without("Strict-Transport-Security"), "Strict-Transport-Security is absent"),
    ("hsts-short", _replace("max-age=31536000", "max-age=300"), "max-age must be at least 31536000"),
    ("hsts-no-age", _replace("max-age=31536000", "includeSubDomains"), "max-age must be at least 31536000"),
    ("hsts-subdomains", _replace("max-age=31536000", "max-age=31536000; includeSubDomains"), "neither includeSubDomains nor preload"),
    ("hsts-preload", _replace("max-age=31536000", "max-age=63072000; preload"), "neither includeSubDomains nor preload"),
    ("nosniff-absent", _without("X-Content-Type-Options"), "X-Content-Type-Options is absent"),
    ("nosniff-wrong", _replace("nosniff", "none"), "X-Content-Type-Options is 'none'"),
    ("frame-absent", _without("X-Frame-Options"), "X-Frame-Options is absent"),
    ("frame-wrong", _replace("DENY", "SAMEORIGIN"), "X-Frame-Options is 'SAMEORIGIN'"),
    ("csp-absent", _without("Content-Security-Policy"), "Content-Security-Policy is absent"),
    ("csp-wrong", _replace("frame-ancestors 'none'", "default-src *"), "Content-Security-Policy is 'default-src *'"),
    ("referrer-absent", _without("Referrer-Policy"), "Referrer-Policy is absent"),
    ("referrer-wrong", _replace("same-origin", "unsafe-url"), "Referrer-Policy is 'unsafe-url'"),
    ("version-in-server", _replace("Server: nginx", "Server: nginx/1.24.0 (Ubuntu)"), "names a version"),
    (
        "cookie-not-secure",
        _replace("Path=/; HttpOnly; SameSite=Strict; Max-Age=0; Secure", "Path=/; HttpOnly; SameSite=Strict; Max-Age=0"),
        "the session cookie is not Secure",
    ),
    (
        "cookie-secure-only-in-its-name",
        _replace("Path=/; HttpOnly; SameSite=Strict; Max-Age=0; Secure", "Path=/; HttpOnly; SameSite=Strict; Max-Age=0; SecureX"),
        "the session cookie is not Secure",
    ),
]


class TestAnAnswerThatLacksWhatTheConfigurationPromises:
    @pytest.mark.parametrize(("answer", "fragment"), [(a, f) for _, a, f in FINDINGS], ids=[i for i, _, _ in FINDINGS])
    def test_is_exit_9_and_names_the_problem(self, answer: str, fragment: str, world, tmp_path: Path) -> None:
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=answer)
        assert completed.returncode == HEADERS, (completed.stdout, completed.stderr)
        assert fragment in completed.stderr, completed.stderr
        assert "1 finding(s)" in completed.stderr, completed.stderr
        assert "IS this tree" not in completed.stdout, "it called the stack good with a bad answer"

    def test_every_problem_is_listed_not_only_the_first(self, world, tmp_path: Path) -> None:
        answer = _without("Strict-Transport-Security", _without("X-Frame-Options"))
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=answer)
        assert completed.returncode == HEADERS, (completed.stdout, completed.stderr)
        assert "2 finding(s)" in completed.stderr
        assert "Strict-Transport-Security is absent" in completed.stderr and "X-Frame-Options is absent" in completed.stderr


class TestAnAnswerThatCannotBeJudged:
    """Exit 4 and nothing claimed: a property that was not observed is not a property that holds."""

    @pytest.mark.parametrize("output", ["", "\n", "the container printed prose and no response\n"], ids=["empty", "blank", "prose"])
    def test_no_response_at_all(self, output: str, world, tmp_path: Path) -> None:
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=output, STUB_HEADERS_STATUS="1", STUB_HEADERS_STDERR="docker: refused\n")
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "could not be read" in completed.stderr and "probe exit 1" in completed.stderr
        assert "IS this tree" not in completed.stdout

    def test_a_response_without_a_session_cookie_is_not_a_pass(self, world, tmp_path: Path) -> None:
        """A 502 from a proxy whose web tier is down has the transport headers and no cookie to judge."""
        bad_gateway = _without("Set-Cookie", _replace("401 Unauthorized", "502 Bad Gateway"))
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=bad_gateway)
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "no am_session cookie to judge" in completed.stderr and "502 Bad Gateway" in completed.stderr
        assert "IS this tree" not in completed.stdout

    def test_another_cookie_is_not_the_session_cookie(self, world, tmp_path: Path) -> None:
        other = _replace("am_session=;", "tracking=1;")
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=other)
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "no am_session cookie to judge" in completed.stderr

    def test_a_body_that_looks_like_a_header_is_not_read_as_one(self, world, tmp_path: Path) -> None:
        """Only the header block counts: a line in the BODY must not satisfy a missing header."""
        sneaky = _without("X-Frame-Options") + "\r\nX-Frame-Options: DENY"
        completed, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=sneaky)
        assert completed.returncode == HEADERS, (completed.stdout, completed.stderr)
        assert "X-Frame-Options is absent" in completed.stderr


class TestEachStepIsShownAbleToFail:
    """The guard is deleted and the same bad answer then passes: the step, and not something near it, is what failed."""

    @pytest.mark.parametrize(
        ("step", "answer", "fragment"),
        [
            ("served-hsts", _without("Strict-Transport-Security"), "Strict-Transport-Security is absent"),
            ("served-security-headers", _without("X-Frame-Options"), "X-Frame-Options is absent"),
            ("served-no-version", _replace("Server: nginx", "Server: nginx/1.24.0"), "names a version"),
            (
                "served-secure-cookie",
                _replace("Max-Age=0; Secure", "Max-Age=0"),
                "the session cookie is not Secure",
            ),
        ],
    )
    def test_the_step(self, step: str, answer: str, fragment: str, world, tmp_path: Path) -> None:
        source = (ROOT / "infra/deploy/verify-deployed.sh").read_text(encoding="utf-8")
        block = re.compile(rf"^\s*# >>> step: {step}\n.*?^\s*# <<< step: {step}\n", re.DOTALL | re.MULTILINE)
        mutated, count = block.subn("", source)
        assert count == 1 and mutated != source, f"step {step} is not marked exactly once"
        _, deploy, _ = world
        with_the_step, _ = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=answer)
        assert with_the_step.returncode == HEADERS and fragment in with_the_step.stderr, with_the_step.stderr
        # beside the staged script, so that it finds `lib/` the way the real one does
        cut = deploy / "verify-deployed-without-step.sh"
        cut.write_text(mutated, encoding="utf-8")
        cut.chmod(0o755)
        without_the_step, calls = _verify(world, tmp_path, STUB_HEADERS_OUTPUT=answer, script=cut)
        assert _probe_calls(calls) != [], "the mutant did not go on to ask, so this case was not testing that step"
        assert fragment not in without_the_step.stderr, without_the_step.stderr


class TestTheRequestTheProbeBuilds:
    """The probe's own text, run in `sh` with an `openssl` that prints what it was given, and a `timeout` that runs it."""

    @staticmethod
    def _probe_text() -> str:
        source = (ROOT / "infra/deploy/verify-deployed.sh").read_text(encoding="utf-8")
        match = re.search(r"<<'PROBE'\n(.*?)\nPROBE\n", source, re.DOTALL)
        assert match is not None, "the probe heredoc is gone"
        return match.group(1)

    def test_it_sends_a_get_for_the_stale_session_to_the_named_host_over_sni(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "openssl").write_text(
            "#!/bin/sh\nprintf 'ARGS:%s\\n' \"$*\"\ncat\n", encoding="utf-8"
        )
        (bin_dir / "timeout").write_text("#!/bin/sh\nshift\nexec \"$@\"\n", encoding="utf-8")
        for stub in bin_dir.iterdir():
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
        completed = subprocess.run(
            ["sh", "-c", self._probe_text(), MARKER, NAME, "proxy:8443", STALE_SESSION],
            capture_output=True, env=env, check=False,
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        out = completed.stdout  # bytes: the CRs are the point
        assert f"ARGS:s_client -connect proxy:8443 -servername {NAME} -quiet -ign_eof".encode() in out
        assert (
            f"GET /bff/v1/me HTTP/1.1\r\nHost: {NAME}\r\nCookie: am_session={STALE_SESSION}\r\n"
            "Accept: application/json\r\nConnection: close\r\n\r\n"
        ).encode() in out, repr(out)
