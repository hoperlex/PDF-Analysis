"""`PROD-01-TLS-ACME-01` -- the four scripts that obtain, export, serve and check a certificate, driven
against stand-ins, with no network, no daemon and no certificate authority.

The lane that wrote them could not contact an authority, and says so. What is proved here is therefore the
part that is OURS and can be wrong without any authority involved: what we ask `certbot` for, what we do
with what it leaves, what the proxy does when the pair on the volume changes, and how the verification
reads an answer. What is NOT proved -- that `certbot` accepts these flags against the real service, that
the authority validates the webroot, that the image builds -- is the staging rehearsal of
`DEPLOYMENT_RUNBOOK.md` section 6, which is the owner's and is written as a numbered procedure with the
expected output of each step.

**The four.**

* ``infra/acme/entrypoint.sh`` -- the loop: validate the settings, wait until the proxy serves the webroot,
  ``certbot certonly --webroot --keep-until-expiring``, export, sleep;
* ``infra/acme/export-pair.sh`` -- copy ONE lineage's pair into the volume the proxy reads, never a staging
  pair over a production one;
* ``infra/acme/check-served.sh`` -- ask the TLS listener what it serves and judge it;
* ``infra/deploy/proxy/watch-certificate.sh`` -- the proxy's timer: apply a changed pair by ``nginx -s
  reload``, but only after ``nginx -t`` accepts it.

**The stand-ins** are small shell scripts on ``PATH``: a ``certbot`` that records its arguments and leaves a
lineage, an ``openssl`` that answers from marker lines in the "certificate" it is handed, a ``wget``, and an
``nginx`` whose ``-t`` and ``-s reload`` are steered by files. They are the instruments: every assertion is
about an argument list, a file or an exit status that the script under test produced.

**Every guard is shown able to fail.** The two with marked blocks (``no-staging-over-production``,
``refuse-an-unloadable-pair``) by deleting the block from a copy; the others by the mutation table in
``docs/program/PROD-01-TLS-ACME-01.md``, where each line of the script a case depends on is changed and the
case is shown red.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ACME = ROOT / "infra/acme"
ENTRYPOINT = ACME / "entrypoint.sh"
EXPORT_PAIR = ACME / "export-pair.sh"
CHECK_SERVED = ACME / "check-served.sh"
WATCH = ROOT / "infra/deploy/proxy/watch-certificate.sh"

#: Literals, none of them the live name.
NAME = "rehearsal-host.sslip.io"
STAGING_ISSUER = "O=(STAGING) Let's Encrypt, CN=(STAGING) Ersatz Edamame E1"
REAL_ISSUER = "O=Let's Encrypt, CN=E7"

# --- the stand-ins ---------------------------------------------------------------------------------------------

#: An `openssl` that understands exactly the calls these scripts make. The "certificate" is any text; a line
#: `ISSUER:<dn>` in it is the issuer. `s_client` prints `STUB_CERT_BODY` (the served certificate) unless it is
#: the verifying call, which prints `STUB_VERIFY_LINE`.
OPENSSL = r'''#!/bin/sh
case "$1" in
    x509)
        shift
        infile=""
        mode=cat
        while [ $# -gt 0 ]; do
            case "$1" in
                -in) infile="$2"; shift 2 ;;
                -noout) shift ;;
                -issuer) mode=issuer; shift ;;
                -enddate) mode=enddate; shift ;;
                -checkend) mode=checkend; shift 2 ;;
                *) shift ;;
            esac
        done
        if [ -n "$infile" ]; then data="$(cat "$infile")"; else data="$(cat)"; fi
        case "$mode" in
            issuer) printf 'issuer=%s\n' "$(printf '%s\n' "$data" | sed -n 's/^ISSUER://p' | head -1)" ;;
            enddate) printf 'notAfter=Dec 30 10:00:00 2026 GMT\n' ;;
            checkend) exit "${STUB_CHECKEND:-0}" ;;
            cat) printf '%s\n' "$data" ;;
        esac
        ;;
    s_client)
        shift
        verify=no
        for argument in "$@"; do
            [ "$argument" != -verify_return_error ] || verify=yes
        done
        echo "$*" >> "${STUB_OPENSSL_LOG:-/dev/null}"
        if [ "$verify" = yes ]; then
            printf '%s\n' "${STUB_VERIFY_LINE:-Verify return code: 0 (ok)}"
        elif [ -n "${STUB_CERT_BODY:-}" ]; then
            printf '%s\n' "$STUB_CERT_BODY"
        fi
        ;;
esac
'''

#: A `certbot` that records its argument list and, unless told to fail, leaves a lineage under --config-dir.
CERTBOT = r'''#!/bin/sh
printf '%s\n' "$*" >> "$CERTBOT_LOG"
if [ "${CERTBOT_FAIL:-0}" = 1 ]; then
    echo "certbot: the authority refused" >&2
    exit 1
fi
lineage=""
config=""
while [ $# -gt 0 ]; do
    case "$1" in
        --cert-name) lineage="$2"; shift 2 ;;
        --config-dir) config="$2"; shift 2 ;;
        *) shift ;;
    esac
done
mkdir -p "$config/live/$lineage"
printf 'CERT-OF-%s\nISSUER:%s\n' "$lineage" "${CERT_ISSUER:-O=Let's Encrypt, CN=E7}" > "$config/live/$lineage/fullchain.pem"
printf 'KEY-OF-%s\n' "$lineage" > "$config/live/$lineage/privkey.pem"
mkdir -p "$config/accounts"
printf 'ACCOUNT-KEY\n' > "$config/accounts/private_key.json"
exit 0
'''

WGET = '''#!/bin/sh
[ "${WGET_FAIL:-0}" = 1 ] && exit 1
echo ok
'''

NGINX = r'''#!/bin/sh
echo "$*" >> "$NGINX_LOG"
case "$1" in
    -t)
        if [ -f "$NGINX_BROKEN_ALWAYS" ]; then
            echo "nginx: [emerg] host not found in upstream \"api\"" >&2
            exit 1
        fi
        if [ -f "$TLS_CONF" ] && [ -f "$NGINX_REJECTS_THE_PAIR" ]; then
            echo "nginx: [emerg] SSL_CTX_use_PrivateKey failed (key values mismatch)" >&2
            exit 1
        fi
        exit 0 ;;
    -s)
        [ ! -f "$NGINX_RELOAD_FAILS" ] || exit 1
        exit 0 ;;
esac
exit 0
'''

SWITCH = r'''#!/bin/sh
echo switch >> "$SWITCH_LOG"
if [ -s "$CERT" ] && [ -s "$KEY" ]; then
    : > "$TLS_CONF"
else
    rm -f "$TLS_CONF"
fi
'''


def _executable(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture()
def bench(tmp_path: Path) -> Path:
    """A directory of stand-ins: `bin/` on PATH, and the places the scripts write."""
    binary = tmp_path / "bin"
    binary.mkdir()
    _executable(binary / "openssl", OPENSSL)
    _executable(binary / "certbot", CERTBOT)
    _executable(binary / "wget", WGET)
    _executable(binary / "nginx", NGINX)
    return tmp_path


def _env(bench: Path, **more: str) -> dict[str, str]:
    environment = {
        "PATH": f"{bench / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(bench),
        "CERTBOT_LOG": str(bench / "certbot.log"),
        "NGINX_LOG": str(bench / "nginx.log"),
        "SWITCH_LOG": str(bench / "switch.log"),
    }
    environment.update(more)
    return environment


def _sh(script: Path, environment: dict[str, str], *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(script), *args], capture_output=True, text=True, env=environment, timeout=60, input=stdin
    )


# ================================================================================================================
# export-pair.sh
# ================================================================================================================


def _lineage(directory: Path, name: str, *, issuer: str = REAL_ISSUER, body: str = "") -> Path:
    live = directory / "live" / name
    live.mkdir(parents=True, exist_ok=True)
    (live / "fullchain.pem").write_text(f"CERT-{body or name}\nISSUER:{issuer}\n", encoding="utf-8")
    (live / "privkey.pem").write_text(f"KEY-{body or name}\n", encoding="utf-8")
    return live


def _export(bench: Path, live: Path, script: Path = EXPORT_PAIR) -> tuple[subprocess.CompletedProcess[str], Path]:
    export = bench / "export"
    export.mkdir(exist_ok=True)
    result = _sh(script, _env(bench, RENEWED_LINEAGE=str(live), ACME_EXPORT=str(export)))
    return result, export


class TestExportPair:
    def test_it_copies_the_pair_and_only_the_pair_with_the_right_modes(self, bench: Path) -> None:
        live = _lineage(bench / "state", NAME)
        (bench / "state" / "accounts").mkdir()
        (bench / "state" / "accounts" / "private_key.json").write_text("ACCOUNT-KEY\n", encoding="utf-8")
        result, export = _export(bench, live)
        assert result.returncode == 0, result.stderr
        assert sorted(p.name for p in export.iterdir()) == ["fullchain.pem", "privkey.pem"], list(export.iterdir())
        assert (export / "fullchain.pem").read_text() == (live / "fullchain.pem").read_text()
        assert (export / "privkey.pem").read_text() == (live / "privkey.pem").read_text()
        assert stat.S_IMODE((export / "privkey.pem").stat().st_mode) == 0o600
        assert stat.S_IMODE((export / "fullchain.pem").stat().st_mode) == 0o644
        assert "ACCOUNT" not in "".join(p.read_text() for p in export.iterdir())

    def test_a_second_run_with_the_same_pair_changes_nothing(self, bench: Path) -> None:
        live = _lineage(bench / "state", NAME)
        _, export = _export(bench, live)
        before = {p.name: p.stat().st_ino for p in export.iterdir()}
        result, _ = _export(bench, live)
        assert result.returncode == 0, result.stderr
        assert "already the one" in result.stderr
        assert {p.name: p.stat().st_ino for p in export.iterdir()} == before

    def test_a_renewed_pair_replaces_the_old_one(self, bench: Path) -> None:
        live = _lineage(bench / "state", NAME, body="one")
        _, export = _export(bench, live)
        _lineage(bench / "state", NAME, body="two")
        result, _ = _export(bench, live)
        assert result.returncode == 0, result.stderr
        assert (export / "fullchain.pem").read_text().startswith("CERT-two")
        assert (export / "privkey.pem").read_text() == "KEY-two\n"
        assert not [p for p in export.iterdir() if p.name.startswith(".")], "a temporary file was left behind"

    @pytest.mark.parametrize("missing", ["fullchain.pem", "privkey.pem"])
    def test_a_lineage_without_both_files_exports_nothing(self, missing: str, bench: Path) -> None:
        live = _lineage(bench / "state", NAME)
        (live / missing).unlink()
        result, export = _export(bench, live)
        assert result.returncode == 1
        assert "nothing was exported" in result.stderr
        assert list(export.iterdir()) == []

    def test_no_lineage_at_all_is_a_refusal_not_a_crash(self, bench: Path) -> None:
        result = _sh(EXPORT_PAIR, _env(bench, ACME_EXPORT=str(bench)))
        assert result.returncode == 1
        assert "RENEWED_LINEAGE is not set" in result.stderr

    def test_a_staging_pair_never_replaces_a_production_one(self, bench: Path) -> None:
        production = _lineage(bench / "state", NAME, issuer=REAL_ISSUER, body="prod")
        _, export = _export(bench, production)
        staging = _lineage(bench / "state", f"{NAME}-staging", issuer=STAGING_ISSUER, body="stage")
        result, _ = _export(bench, staging)
        assert result.returncode == 1
        assert "REFUSED" in result.stderr and "production one" in result.stderr
        assert (export / "fullchain.pem").read_text().startswith("CERT-prod"), "the production pair was replaced"

    @pytest.mark.parametrize(
        ("first", "second"),
        [(None, STAGING_ISSUER), (STAGING_ISSUER, STAGING_ISSUER), (STAGING_ISSUER, REAL_ISSUER), (REAL_ISSUER, REAL_ISSUER)],
        ids=["staging into an empty volume", "staging over staging", "production over staging", "production over production"],
    )
    def test_every_other_replacement_is_allowed(self, first: str | None, second: str, bench: Path) -> None:
        export = None
        if first is not None:
            _, export = _export(bench, _lineage(bench / "state", "first", issuer=first, body="first"))
        result, export = _export(bench, _lineage(bench / "state", "second", issuer=second, body="second"))
        assert result.returncode == 0, result.stderr
        assert (export / "fullchain.pem").read_text().startswith("CERT-second")

    def test_that_step_is_shown_able_to_fail(self, bench: Path) -> None:
        source = EXPORT_PAIR.read_text(encoding="utf-8")
        block = re.compile(
            r"^# >>> step: no-staging-over-production\n.*?^# <<< step: no-staging-over-production\n",
            re.DOTALL | re.MULTILINE,
        )
        mutated, count = block.subn("", source)
        assert count == 1 and mutated != source
        cut = bench / "export-pair-mutant.sh"
        cut.write_text(mutated, encoding="utf-8")
        production = _lineage(bench / "state", NAME, issuer=REAL_ISSUER, body="prod")
        _, export = _export(bench, production, script=cut)
        staging = _lineage(bench / "state", f"{NAME}-staging", issuer=STAGING_ISSUER, body="stage")
        result, _ = _export(bench, staging, script=cut)
        assert result.returncode == 0, "the mutant refused anyway, so this case was not testing that step"
        assert (export / "fullchain.pem").read_text().startswith("CERT-stage"), "the mutant kept the production pair"


# ================================================================================================================
# entrypoint.sh
# ================================================================================================================


def _acme_env(bench: Path, **more: str) -> dict[str, str]:
    settings = {
        "ACME_NAME": NAME,
        "ACME_WEBROOT": str(bench / "webroot"),
        "ACME_CONFIG_DIR": str(bench / "state"),
        "ACME_WORK_DIR": str(bench / "work"),
        "ACME_LOGS_DIR": str(bench / "logs"),
        "ACME_EXPORT": str(bench / "export"),
        "ACME_EXPORT_PAIR": str(EXPORT_PAIR),
        "ACME_CERTBOT": str(bench / "bin" / "certbot"),
        "ACME_ONCE": "1",
        "ACME_PROBE_TRIES": "1",
    }
    settings.update(more)
    (bench / "export").mkdir(exist_ok=True)
    return _env(bench, **settings)


def _certbot_args(bench: Path) -> list[list[str]]:
    log = bench / "certbot.log"
    return [line.split() for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


class TestEntrypoint:
    def test_staging_is_the_default_and_asks_the_test_endpoint_under_its_own_lineage(self, bench: Path) -> None:
        result = _sh(ENTRYPOINT, _acme_env(bench))
        assert result.returncode == 0, result.stderr
        (args,) = _certbot_args(bench)
        assert args[0] == "certonly"
        for expected in ("--non-interactive", "--agree-tos", "--webroot", "--keep-until-expiring", "--staging"):
            assert expected in args, (expected, args)
        assert args[args.index("-w") + 1] == str(bench / "webroot")
        assert args[args.index("-d") + 1] == NAME
        assert args[args.index("--cert-name") + 1] == f"{NAME}-staging"
        assert args[args.index("--config-dir") + 1] == str(bench / "state")
        assert args[args.index("--deploy-hook") + 1] == str(EXPORT_PAIR)
        assert "--register-unsafely-without-email" in args and "-m" not in args
        assert "STAGING" in result.stderr

    def test_production_is_explicit_and_uses_the_plain_lineage_and_no_staging_flag(self, bench: Path) -> None:
        result = _sh(ENTRYPOINT, _acme_env(bench, ACME_STAGING="no", ACME_EMAIL="ops@sslip.io"))
        assert result.returncode == 0, result.stderr
        (args,) = _certbot_args(bench)
        assert "--staging" not in args
        assert args[args.index("--cert-name") + 1] == NAME
        assert args[args.index("-m") + 1] == "ops@sslip.io" and "--register-unsafely-without-email" not in args
        assert "PRODUCTION" in result.stderr

    def test_the_pair_is_exported_after_a_pass_and_the_account_key_is_not(self, bench: Path) -> None:
        result = _sh(ENTRYPOINT, _acme_env(bench, ACME_STAGING="no"))
        assert result.returncode == 0, result.stderr
        export = bench / "export"
        assert sorted(p.name for p in export.iterdir()) == ["fullchain.pem", "privkey.pem"]
        assert (export / "privkey.pem").read_text() == f"KEY-OF-{NAME}\n"
        assert "ACCOUNT" not in "".join(p.read_text() for p in export.iterdir())

    def test_a_refusal_by_the_authority_is_a_retry_later_and_exports_nothing(self, bench: Path) -> None:
        result = _sh(ENTRYPOINT, _acme_env(bench, CERTBOT_FAIL="1"))
        assert result.returncode == 1
        assert "no certificate yet (attempt 1)" in result.stderr and "in 60s" in result.stderr
        assert list((bench / "export").iterdir()) == []

    def test_it_does_not_ask_the_authority_while_the_proxy_does_not_serve_the_webroot(self, bench: Path) -> None:
        result = _sh(ENTRYPOINT, _acme_env(bench, WGET_FAIL="1"))
        assert result.returncode == 1
        assert _certbot_args(bench) == [], "an attempt was spent on a proxy that was not serving the webroot"
        assert "did not serve the webroot" in result.stderr

    def test_the_probe_file_is_removed_after_it_is_used(self, bench: Path) -> None:
        _sh(ENTRYPOINT, _acme_env(bench))
        challenge = bench / "webroot" / ".well-known" / "acme-challenge"
        assert challenge.is_dir() and list(challenge.iterdir()) == []

    @pytest.mark.parametrize(
        ("overrides", "says"),
        [
            ({"ACME_NAME": ""}, "ACME_NAME is empty"),
            ({"ACME_NAME": "Upper.Case.io"}, "not a lower-case DNS name"),
            ({"ACME_NAME": "single"}, "single label"),
            ({"ACME_NAME": "a b.io"}, "not a lower-case DNS name"),
            ({"ACME_NAME": "$(touch x).io"}, "not a lower-case DNS name"),
            ({"ACME_STAGING": "maybe"}, "neither yes nor no"),
            ({"ACME_EMAIL": "no spaces@here.io"}, "character an address does not need"),
            ({"ACME_EMAIL": "plainword"}, "not an address"),
        ],
    )
    def test_a_bad_setting_stops_it_before_anything_is_asked(
        self, overrides: dict[str, str], says: str, bench: Path
    ) -> None:
        result = _sh(ENTRYPOINT, _acme_env(bench, **overrides))
        assert result.returncode == 2, (result.returncode, result.stderr)
        assert says in result.stderr, result.stderr
        assert _certbot_args(bench) == []

    def test_the_retry_schedule_stays_inside_the_authoritys_failure_limit(self) -> None:
        """1 minute, 5, 15, then hourly: four tries inside the first hour, under the authority's limit of
        five failed validations per hostname per hour. Source-read, because running the loop that long is not
        a test: the schedule is the `case` in the script and this pins its four arms."""
        source = ENTRYPOINT.read_text(encoding="utf-8")
        arms = dict(re.findall(r"^\s+(\d|\*)\) pause=(\d+) ;;$", source, re.M))
        assert arms == {"1": "60", "2": "300", "3": "900", "*": "3600"}, arms


# ================================================================================================================
# check-served.sh
# ================================================================================================================


def _served(bench: Path, *args: str, **more: str) -> subprocess.CompletedProcess[str]:
    return _sh(CHECK_SERVED, _env(bench, **more), *args)


CERT_OF = lambda issuer: f"-----BEGIN CERTIFICATE-----\nISSUER:{issuer}\n-----END CERTIFICATE-----"  # noqa: E731


class TestCheckServed:
    def test_a_trusted_unexpiring_production_certificate_passes(self, bench: Path) -> None:
        result = _served(bench, NAME, "proxy:8443", "14", "production", STUB_CERT_BODY=CERT_OF(REAL_ISSUER))
        assert result.returncode == 0, result.stdout
        assert result.stdout.startswith("served-certificate: OK name=" + NAME)
        assert "valid-for-at-least-days=14" in result.stdout

    def test_nothing_served_is_exit_10(self, bench: Path) -> None:
        result = _served(bench, NAME, "proxy:8443", "14", "production")
        assert result.returncode == 10, result.stdout
        assert "NOT SERVED" in result.stdout

    def test_a_staging_certificate_on_a_production_name_is_exit_13(self, bench: Path) -> None:
        result = _served(bench, NAME, "proxy:8443", "14", "production", STUB_CERT_BODY=CERT_OF(STAGING_ISSUER))
        assert result.returncode == 13, result.stdout
        assert "STAGING CERTIFICATE" in result.stdout

    def test_a_production_certificate_in_a_rehearsal_is_exit_13(self, bench: Path) -> None:
        result = _served(bench, NAME, "proxy:8443", "14", "staging", STUB_CERT_BODY=CERT_OF(REAL_ISSUER))
        assert result.returncode == 13, result.stdout
        assert "NOT A STAGING CERTIFICATE" in result.stdout

    def test_a_staging_certificate_in_a_rehearsal_passes_without_a_chain_check(self, bench: Path) -> None:
        """The chain of a staging certificate is untrusted by design, so the verifying call must not be made."""
        log = bench / "openssl.log"
        result = _served(
            bench, NAME, "proxy:8443", "14", "staging",
            STUB_CERT_BODY=CERT_OF(STAGING_ISSUER), STUB_VERIFY_LINE="Verify return code: 20", STUB_OPENSSL_LOG=str(log),
        )
        assert result.returncode == 0, result.stdout
        assert "-verify_return_error" not in log.read_text()

    def test_a_chain_that_does_not_verify_is_exit_12_and_the_name_is_part_of_the_question(self, bench: Path) -> None:
        log = bench / "openssl.log"
        result = _served(
            bench, NAME, "proxy:8443", "14", "production",
            STUB_CERT_BODY=CERT_OF(REAL_ISSUER), STUB_VERIFY_LINE="Verify return code: 62 (hostname mismatch)",
            STUB_OPENSSL_LOG=str(log),
        )
        assert result.returncode == 12, result.stdout
        assert "NOT TRUSTED" in result.stdout
        asked = [line for line in log.read_text().splitlines() if "-verify_return_error" in line]
        assert asked and f"-verify_hostname {NAME}" in asked[0] and f"-servername {NAME}" in asked[0], asked

    def test_a_certificate_inside_the_margin_is_exit_11(self, bench: Path) -> None:
        result = _served(
            bench, NAME, "proxy:8443", "14", "production", STUB_CERT_BODY=CERT_OF(REAL_ISSUER), STUB_CHECKEND="1"
        )
        assert result.returncode == 11, result.stdout
        assert "EXPIRING" in result.stdout and "within 14 days" in result.stdout

    def test_the_margin_is_passed_to_openssl_in_seconds(self, bench: Path) -> None:
        """14 days is 1209600 seconds -- the figure `ADR-0021` row 5 writes. Source-read: the stand-in's
        `-checkend` is steered by an environment variable, so the figure itself is pinned here."""
        source = CHECK_SERVED.read_text(encoding="utf-8")
        assert "SECONDS_LEFT=$((DAYS * 86400))" in source and '-checkend "$SECONDS_LEFT"' in source
        assert 14 * 86400 == 1209600

    @pytest.mark.parametrize(
        "arguments", [(NAME, "proxy:8443", "14", "both"), (NAME, "proxy:8443", "soon", "production")]
    )
    def test_a_usage_error_is_exit_2_and_asks_nothing(self, arguments: tuple[str, ...], bench: Path) -> None:
        log = bench / "openssl.log"
        result = _served(bench, *arguments, STUB_OPENSSL_LOG=str(log))
        assert result.returncode == 2
        assert not log.exists()


# ================================================================================================================
# watch-certificate.sh
# ================================================================================================================


class Watch:
    """A proxy's certificate watcher over a scratch directory, driven tick by tick in ONE shell, so the
    fingerprint it remembers between ticks is the state it keeps in production."""

    def __init__(self, bench: Path) -> None:
        self.bench = bench
        self.tls = bench / "tls"
        self.tls.mkdir()
        self.conf = bench / "conf.d"
        self.conf.mkdir()
        (self.conf / "acme-challenge.conf").write_text("server {}\n", encoding="utf-8")
        _executable(bench / "switch.sh", SWITCH)
        self.env = _env(
            bench,
            CERT_WATCH_CERT=str(self.tls / "fullchain.pem"),
            CERT_WATCH_KEY=str(self.tls / "privkey.pem"),
            CERT_WATCH_SWITCH=str(bench / "switch.sh"),
            CERT_WATCH_TLS_CONF=str(self.conf / "tls.conf"),
            CERT_WATCH_CHALLENGE_CONF=str(self.conf / "acme-challenge.conf"),
            CERT_WATCH_NGINX=str(bench / "bin" / "nginx"),
            CERT=str(self.tls / "fullchain.pem"),
            KEY=str(self.tls / "privkey.pem"),
            TLS_CONF=str(self.conf / "tls.conf"),
            CERT_WATCH_SOURCE_ONLY="1",
        )

    def put_pair(self, body: str) -> None:
        (self.tls / "fullchain.pem").write_text(f"CERT-{body}\n", encoding="utf-8")
        (self.tls / "privkey.pem").write_text(f"KEY-{body}\n", encoding="utf-8")

    def drop_pair(self) -> None:
        for name in ("fullchain.pem", "privkey.pem"):
            (self.tls / name).unlink()

    def flag(self, name: str, on: bool) -> Path:
        path = self.bench / name
        if on:
            path.write_text("", encoding="utf-8")
        elif path.exists():
            path.unlink()
        return path

    def run(self, *steps: str, script: Path = WATCH) -> subprocess.CompletedProcess[str]:
        """`steps` are shell lines run between ticks; each `tick` line calls the function."""
        flags = {
            "NGINX_BROKEN_ALWAYS": self.bench / "broken-always",
            "NGINX_REJECTS_THE_PAIR": self.bench / "rejects-pair",
            "NGINX_RELOAD_FAILS": self.bench / "reload-fails",
        }
        environment = dict(self.env)
        environment.update({key: str(value) for key, value in flags.items()})
        program = ". " + str(script) + "\n" + "\n".join(steps) + "\n"
        return subprocess.run(["sh", "-c", program], capture_output=True, text=True, env=environment, timeout=60)

    def log(self, name: str) -> list[str]:
        path = self.bench / name
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    @property
    def tls_conf(self) -> Path:
        return self.conf / "tls.conf"


@pytest.fixture()
def watch(bench: Path) -> Watch:
    return Watch(bench)


class TestWatchCertificate:
    def test_an_unchanged_pair_reloads_nothing(self, watch: Watch) -> None:
        watch.put_pair("one")
        result = watch.run("tick", "tick")
        assert result.returncode == 0, result.stderr
        assert watch.log("nginx.log") == [] and watch.log("switch.log") == []

    def test_a_pair_that_appears_is_switched_on_tested_and_reloaded_in_that_order(self, watch: Watch) -> None:
        result = watch.run(f'printf "CERT\\n" > "{watch.tls}/fullchain.pem"; printf "KEY\\n" > "{watch.tls}/privkey.pem"', "tick")
        assert result.returncode == 0, result.stderr
        assert watch.log("switch.log") == ["switch"]
        assert watch.log("nginx.log") == ["-t", "-s reload"]
        assert watch.tls_conf.exists()
        assert "nginx reloaded" in result.stderr

    def test_a_renewed_pair_is_reloaded(self, watch: Watch) -> None:
        watch.put_pair("one")
        result = watch.run(
            f'printf "CERT-two\\n" > "{watch.tls}/fullchain.pem"; printf "KEY-two\\n" > "{watch.tls}/privkey.pem"', "tick"
        )
        assert result.returncode == 0, result.stderr
        assert watch.log("nginx.log") == ["-t", "-s reload"]

    def test_a_pair_that_goes_away_takes_the_tls_block_out_and_reloads(self, watch: Watch) -> None:
        watch.put_pair("one")
        watch.tls_conf.write_text("", encoding="utf-8")
        result = watch.run(f'rm "{watch.tls}/fullchain.pem" "{watch.tls}/privkey.pem"', "tick")
        assert result.returncode == 0, result.stderr
        assert not watch.tls_conf.exists()
        assert watch.log("nginx.log") == ["-t", "-s reload"]

    def test_a_pair_nginx_rejects_is_not_applied_and_the_block_comes_out_again(self, watch: Watch) -> None:
        watch.flag("rejects-pair", True)
        result = watch.run(f'printf "CERT\\n" > "{watch.tls}/fullchain.pem"; printf "KEY\\n" > "{watch.tls}/privkey.pem"', "tick")
        assert result.returncode == 0, result.stderr
        assert "REFUSED" in result.stderr and "key values mismatch" in result.stderr
        assert "-s reload" not in watch.log("nginx.log"), watch.log("nginx.log")
        assert not watch.tls_conf.exists(), "a restart would now start on a configuration nginx refuses"

    def test_a_refused_pair_is_reported_once_and_a_changed_pair_is_tried_again(self, watch: Watch) -> None:
        def put(body: str) -> str:
            return f'printf "CERT-{body}\\n" > "{watch.tls}/fullchain.pem"; printf "KEY-{body}\\n" > "{watch.tls}/privkey.pem"'

        watch.flag("rejects-pair", True)
        result = watch.run(put("bad"), "tick", "tick", "tick", f'rm -f "{watch.bench}/rejects-pair"', put("good"), "tick")
        assert result.returncode == 0, result.stderr
        assert result.stderr.count("REFUSED") == 1, result.stderr
        # tick 1: -t fails, -t passes without the block; ticks 2 and 3: the same fingerprint, nothing asked;
        # tick 4: a new pair -> -t passes with the block, and nginx is told to reload
        assert watch.log("nginx.log") == ["-t", "-t", "-t", "-s reload"], watch.log("nginx.log")
        assert watch.tls_conf.exists()

    def test_a_configuration_nginx_refuses_with_or_without_the_block_is_not_blamed_on_the_pair(self, watch: Watch) -> None:
        """`host not found in upstream` while `api` restarts: the pair is fine and must be tried again."""
        watch.flag("broken-always", True)
        put = f'printf "CERT\\n" > "{watch.tls}/fullchain.pem"; printf "KEY\\n" > "{watch.tls}/privkey.pem"'
        result = watch.run(put, "tick", f'rm -f "{watch.bench}/broken-always"', "tick")
        assert result.returncode == 0, result.stderr
        assert "the pair is not the cause" in result.stderr
        assert "REFUSED" not in result.stderr
        assert watch.tls_conf.exists(), "the block was left out although the pair was never at fault"
        # nginx recovered between the ticks; the SAME pair is applied on the second one, without changing
        assert watch.log("nginx.log") == ["-t", "-t", "-t", "-s reload"], watch.log("nginx.log")
        assert watch.log("switch.log").count("switch") == 3, watch.log("switch.log")

    def test_a_failed_reload_is_retried_on_the_next_tick(self, watch: Watch) -> None:
        watch.flag("reload-fails", True)
        put = f'printf "CERT\\n" > "{watch.tls}/fullchain.pem"; printf "KEY\\n" > "{watch.tls}/privkey.pem"'
        failing = watch.run(put, "tick", f'rm -f "{watch.bench}/reload-fails"', "tick")
        assert failing.returncode == 0, failing.stderr
        assert "the reload failed" in failing.stderr
        assert watch.log("nginx.log").count("-s reload") == 2, watch.log("nginx.log")
        assert "nginx reloaded" in failing.stderr

    def test_without_the_challenge_block_it_watches_nothing(self, watch: Watch) -> None:
        (watch.conf / "acme-challenge.conf").unlink()
        environment = dict(watch.env)
        environment.pop("CERT_WATCH_SOURCE_ONLY")
        result = subprocess.run(["sh", str(WATCH)], capture_output=True, text=True, env=environment, timeout=30)
        assert result.returncode == 0
        assert "not configured for ACME; not watching" in result.stderr

    def test_the_background_loop_applies_a_pair_that_appears_and_stops_when_told(self, watch: Watch) -> None:
        """The one real-time case: the hook returns at once, leaves the loop behind, and the loop does the
        work on its own tick. Output goes to files so the test's pipes are not held open by the child."""
        stop = watch.bench / "stop"
        environment = dict(watch.env)
        environment.pop("CERT_WATCH_SOURCE_ONLY")
        environment.update(
            {
                "CERT_WATCH_SECONDS": "1",
                "CERT_WATCH_STOP": str(stop),
                "NGINX_BROKEN_ALWAYS": str(watch.bench / "broken-always"),
                "NGINX_REJECTS_THE_PAIR": str(watch.bench / "rejects-pair"),
                "NGINX_RELOAD_FAILS": str(watch.bench / "reload-fails"),
            }
        )
        out = (watch.bench / "watch.out").open("w")
        started = time.monotonic()
        subprocess.run(["sh", str(WATCH)], stdout=out, stderr=out, stdin=subprocess.DEVNULL, env=environment, timeout=30, check=True)
        assert time.monotonic() - started < 5, "the hook did not return; the loop is not detached"
        try:
            watch.put_pair("late")
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and "-s reload" not in watch.log("nginx.log"):
                time.sleep(0.2)
            assert "-s reload" in watch.log("nginx.log"), (watch.log("nginx.log"), (watch.bench / "watch.out").read_text())
        finally:
            stop.write_text("", encoding="utf-8")
            out.close()
            time.sleep(1.5)

    def test_that_step_is_shown_able_to_fail(self, watch: Watch) -> None:
        source = WATCH.read_text(encoding="utf-8")
        block = re.compile(
            r"^\s*# >>> step: refuse-an-unloadable-pair\n.*?^\s*# <<< step: refuse-an-unloadable-pair\n",
            re.DOTALL | re.MULTILINE,
        )
        mutated, count = block.subn("", source)
        assert count == 1 and mutated != source
        cut = watch.bench / "watch-mutant.sh"
        cut.write_text(mutated, encoding="utf-8")
        watch.flag("rejects-pair", True)
        result = watch.run(
            f'printf "CERT\\n" > "{watch.tls}/fullchain.pem"; printf "KEY\\n" > "{watch.tls}/privkey.pem"', "tick", script=cut
        )
        assert "REFUSED" not in result.stderr, result.stderr
        assert watch.tls_conf.exists(), "the mutant took the block out anyway, so this case was not testing that step"
