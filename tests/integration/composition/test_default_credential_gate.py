"""`PROD-02` (`R-146i`, `R-146s`, `R-146z`; `ADR-0021` section 2 and commitment 6, `ADR-0023` section 3 and
commitment 9) -- a deployment is not successful, and public port 443 is not published, while the PUBLISHED seeded
pair (`admin` / `password`) is valid.

The gate is `python -m auditmanager.access.check --gate` inside the `api` image (its own cases are
`tests/unit/access/test_access_check_gate.py`). This file drives everything that READS it:

* ``lib/proxy-listeners.sh`` -- the one place that classifies the gate's answer (``clean`` / ``finding`` /
  ``unknown``, the sentinel and the status having to agree), decides ``https_wanted`` (the operator's setting AND
  a clean gate), and recreates ONLY the proxy with or without the 443 overlay;
* ``deploy.sh``'s guard ``default-credential-gate`` (after ``migrations-at-head``) and ``listeners-library-present``;
* ``verify-deployed.sh``'s step ``default-credential-gate`` (exit 8 on a finding, 4 on an unanswered question);
* that ``readiness.sh`` keeps asking the WIDER question without ``--gate`` (`R-46`), and that ``reload-proxy.sh``
  no longer tells an operator to add only ``proxy/compose.tls.yml`` (`D-227` item 5).

**The restore paths** (``reset.sh --restore``, ``copy-serve.sh restore-db``) have their cases beside their other
cases: ``test_reset_script_refusals.py::TestTheRestoreEndsWithTheCredentialGate`` and the ``restore-db`` cases of
``test_stand_copy_refusals.py``.

**Every refusal is shown able to fail**: the same invocation against a copy of the script with the marked block
deleted no longer refuses, and the one that matters most -- the table of ``test_443_is_published_only_when_...``
-- is the *absence* of the exposure: 443 is published at the end of a deploy only when the setting, a certificate
pair and a clean gate all say yes.

**What this file does not prove**: that a real database answers the gate (the unit cases and a one-off against a
private database are the report's), and that compose merges the overlays the way these stubs assume
(``test_acme_overlay.py``; the owner's staging rehearsal).
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "infra/deploy/lib/proxy-listeners.sh"


def _load(name: str, relative: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


acme = _load("acme_harness", "tests/integration/composition/test_acme_deploy_guards.py")
probe = _load("probe_harness", "tests/integration/composition/test_deployed_stack_probe.py")

serving = acme.serving  # the fixtures, by the names pytest finds them under
world = probe.world
REFUSED = acme.REFUSED

CLEAN = "access-check GATE OK no published credential"
FINDING = (
    "access-check GATE DEFAULT CREDENTIAL: login=admin user_uid=usr_01ARZ3NDEKTSV4RRFFQ69G5FAA "
    "password_unchanged_since=2026-10-01T12:00:00+00:00\n"
    "access-check GATE: the account 'admin' still accepts the published password. "
    "Anyone who has read the deployment notes can sign in as it."
)
WARNING = (
    "access-check GATE WARNING temporary password: login=someone@example.invalid "
    "user_uid=usr_01ARZ3NDEKTSV4RRFFQ69G5FAB password_unchanged_since=2026-10-02T09:00:00+00:00"
)

# ====================================================================================================
# the library
# ====================================================================================================


def _bash(script: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'. "{LIB}"\n{script}'],
        capture_output=True, text=True, env={**os.environ, **env}, timeout=60,
    )


class TestTheVerdictNeedsTheSentinelAndTheStatusToAgree:
    @pytest.mark.parametrize(
        ("status", "output", "verdict"),
        [
            pytest.param("0", CLEAN, "clean", id="clean"),
            pytest.param("0", f"{WARNING}\n{CLEAN}", "clean", id="clean-with-a-warning"),
            pytest.param("0", f"some compose noise\n{CLEAN}\nmore noise", "clean", id="clean-among-noise"),
            pytest.param("1", FINDING, "finding", id="finding"),
            pytest.param("1", f"{WARNING}\n{FINDING}", "finding", id="finding-with-a-warning"),
            pytest.param("1", WARNING, "unknown", id="status-1-and-only-a-warning"),
            pytest.param("0", FINDING, "unknown", id="finding-text-and-status-0"),
            pytest.param("1", CLEAN, "unknown", id="clean-text-and-status-1"),
            pytest.param("0", f"{CLEAN}\n{FINDING}", "unknown", id="both-sentinels"),
            pytest.param("0", "", "unknown", id="status-0-and-nothing-printed"),
            pytest.param("0", "access-check OK no default credentials", "unknown", id="the-default-modes-sentinel"),
            pytest.param("0", "access-check DEFAULT CREDENTIAL: login=admin", "unknown", id="the-default-modes-finding"),
            pytest.param("2", "access-check FAILED: could not connect", "unknown", id="could-not-read"),
            pytest.param("125", "", "unknown", id="docker-could-not-start-it"),
            pytest.param("0", f"x{CLEAN}", "unknown", id="the-sentinel-must-be-a-whole-line"),
            pytest.param("0", f"{CLEAN} (not really)", "unknown", id="the-sentinel-must-be-exact"),
            pytest.param("", CLEAN, "unknown", id="no-status"),
        ],
    )
    def test_the_table(self, status: str, output: str, verdict: str) -> None:
        completed = _bash('listeners_gate_verdict "$S" "$O"', S=status, O=output)
        assert completed.stdout.strip() == verdict, (status, output, completed.stdout, completed.stderr)


class TestTheLoginsAreNamedAndNothingElse:
    def test_one_login_per_finding_line(self) -> None:
        two = FINDING + "\naccess-check GATE DEFAULT CREDENTIAL: login=ops@example.invalid user_uid=usr_x"
        completed = _bash('listeners_gate_logins "$O"', O=f"{WARNING}\n{two}")
        assert completed.stdout.split() == ["admin", "ops@example.invalid"], completed.stdout

    def test_a_warning_or_a_clean_answer_names_no_login(self) -> None:
        assert _bash('listeners_gate_logins "$O"', O=f"{WARNING}\n{CLEAN}").stdout.strip() == ""


class TestHttpsIsWantedOnlyOnTwoYeses:
    @pytest.mark.parametrize("setting", ["yes", "no", "", "maybe", "YES"])
    @pytest.mark.parametrize("verdict", ["clean", "finding", "unknown", "", "yes"])
    def test_the_table(self, setting: str, verdict: str) -> None:
        completed = _bash('listeners_https_wanted "$A" "$B"', A=setting, B=verdict)
        expected = "yes" if (setting, verdict) == ("yes", "clean") else "no"
        assert completed.stdout.strip() == expected, (setting, verdict, completed.stdout)

    def test_the_operators_setting_alone_never_opens_443(self) -> None:
        """PROD-01 computed `https_wanted` from the setting alone; that is exactly what `PROD-02` replaced."""
        text = (ROOT / "infra/deploy/deploy.sh").read_text(encoding="utf-8")
        assert 'listeners_https_wanted "$PUBLISH_HTTPS" "$GATE_VERDICT"' in text
        assert re.search(r'listeners_overlay_files "\$HERE" "\$CERT_NAME" "\$PUBLISH_HTTPS"', text) is None, (
            "an overlay list is still computed from the setting alone"
        )


FAKE_DOCKER = r"""#!/bin/sh
printf '%s\n' "$*" >> "$STUB_LOG"
case "$1" in
    port)
        if [ -f "$STUB_LOG.recreated" ]; then exit 1; fi
        printf '%s' "$STUB_PORT_OUT"; [ -n "$STUB_PORT_OUT" ] && exit 0; exit 1 ;;
    compose)
        case "$*" in
            *"ps --quiet proxy"*) [ "$STUB_PROXY" = 1 ] && echo container-of-proxy; exit 0 ;;
            *"up -d --no-deps proxy"*)
                [ "${STUB_UP_STATUS:-0}" = 0 ] && touch "$STUB_LOG.recreated"; exit "${STUB_UP_STATUS:-0}" ;;
            *"auditmanager.access.check"*)
                [ -n "$STUB_IN" ] && cat > "$STUB_LOG.stdin" ; printf '%s\n' "$STUB_GATE_OUTPUT"; exit "${STUB_GATE_STATUS:-0}" ;;
        esac ;;
esac
exit 0
"""


def _fake_docker(tmp_path: Path) -> tuple[Path, Path]:
    binary = tmp_path / "bin"
    binary.mkdir(parents=True, exist_ok=True)
    docker = binary / "docker"
    docker.write_text(FAKE_DOCKER, encoding="utf-8")
    docker.chmod(0o755)
    return binary, tmp_path / "docker.log"


def _with_docker(tmp_path: Path, script: str, **env: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    binary, log = _fake_docker(tmp_path)
    completed = _bash(
        script, PATH=f"{binary}{os.pathsep}{os.environ['PATH']}", STUB_LOG=str(log), **env
    )
    return completed, (log.read_text(encoding="utf-8").splitlines() if log.exists() else [])


COMPOSE = 'compose() { docker compose --env-file /e.env --file /c.yml "$@"; }\n'


class TestTheGateIsRunInsideTheApiImageThroughTheCallersCompose:
    def test_the_command_and_the_three_globals(self, tmp_path: Path) -> None:
        completed, calls = _with_docker(
            tmp_path,
            COMPOSE + 'listeners_gate_run compose\nprintf "%s|%s|%s\\n" "$LISTENERS_GATE_STATUS" "$LISTENERS_GATE_VERDICT" "$LISTENERS_GATE_OUTPUT"',
            STUB_GATE_OUTPUT=FINDING, STUB_GATE_STATUS="1",
        )
        assert completed.returncode == 0, completed.stderr
        assert calls == [
            "compose --env-file /e.env --file /c.yml run --rm --no-deps -T --entrypoint python api "
            "-m auditmanager.access.check --gate"
        ]
        assert completed.stdout.startswith("1|finding|access-check GATE DEFAULT CREDENTIAL: login=admin"), completed.stdout

    def test_it_does_not_read_the_callers_standard_input(self, tmp_path: Path) -> None:
        """`copy-serve.sh` runs as an ssh forced command: a `compose run` that inherited its stdin would eat
        the client's channel."""
        binary, log = _fake_docker(tmp_path)
        completed = subprocess.run(
            ["bash", "-c", f'. "{LIB}"\n{COMPOSE}listeners_gate_run compose; echo "after:$LISTENERS_GATE_STATUS"'],
            input="whatever the client sent\n", capture_output=True, text=True, timeout=60,
            env={**os.environ, "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}", "STUB_LOG": str(log),
                 "STUB_GATE_OUTPUT": CLEAN, "STUB_IN": "1"},
        )
        assert completed.returncode == 0, completed.stderr
        assert (Path(str(log) + ".stdin")).read_text(encoding="utf-8") == "", "the gate read its caller's stdin"

    def test_a_status_the_gate_could_not_give_is_unknown_not_clean(self, tmp_path: Path) -> None:
        completed, _ = _with_docker(
            tmp_path, COMPOSE + 'listeners_gate_run compose\necho "$LISTENERS_GATE_VERDICT"',
            STUB_GATE_OUTPUT="", STUB_GATE_STATUS="125",
        )
        assert completed.stdout.strip() == "unknown"


class TestOnlyTheProxyIsRecreatedAndOnlyWithTheFilesTheDecisionNames:
    DEPLOY = str(ROOT / "infra/deploy")
    APPLY = 'listeners_apply_https "%s" /e.env "%s" %s %s; echo "rc=$?"'

    def _apply(self, tmp_path: Path, name: str, wanted: str, pair: str):  # type: ignore[no-untyped-def]
        return _with_docker(tmp_path, self.APPLY % (self.DEPLOY, name, wanted, pair), STUB_PROXY="1")

    @pytest.mark.parametrize(
        ("wanted", "pair", "tls"),
        [("yes", "yes", True), ("yes", "no", False), ("no", "yes", False), ("no", "no", False), ("yes", "unknown", False)],
    )
    def test_the_overlay_list_follows_the_decision(self, tmp_path: Path, wanted: str, pair: str, tls: bool) -> None:
        completed, calls = self._apply(tmp_path, "x.sslip.io", wanted, pair)
        assert completed.stdout.strip() == "rc=0", completed.stdout
        (line,) = calls
        assert line.endswith(" up -d --no-deps proxy"), line
        assert ("compose.tls.yml" in line) is tls, line
        assert f"--file {self.DEPLOY}/compose.server.yml --file {ROOT}/infra/acme/compose.acme.yml" in line, line

    def test_no_name_means_no_terminator_and_no_docker_call(self, tmp_path: Path) -> None:
        completed, calls = self._apply(tmp_path, "", "no", "no")
        assert completed.stdout.strip() == "rc=0" and calls == [], (completed.stdout, calls)

    def test_a_half_installed_clone_is_an_error_and_nothing_is_recreated(self, tmp_path: Path) -> None:
        deploy = tmp_path / "infra/deploy"
        (deploy / "proxy").mkdir(parents=True)
        completed, calls = _with_docker(
            tmp_path, f'listeners_apply_https "{deploy}" /e.env x.sslip.io no no; echo "rc=$?"'
        )
        assert completed.stdout.strip() == "rc=2" and calls == [], (completed.stdout, calls)


class TestWithdrawing443:
    DEPLOY = str(ROOT / "infra/deploy")
    WITHHOLD = COMPOSE + 'listeners_withhold_https compose "%s" /e.env "%s"; echo "rc=$?"'

    def test_nothing_published_means_nothing_to_do(self, tmp_path: Path) -> None:
        completed, calls = _with_docker(tmp_path, self.WITHHOLD % (self.DEPLOY, "x.sslip.io"), STUB_PROXY="1")
        assert completed.stdout.strip() == "rc=0"
        assert not any(line.endswith("up -d --no-deps proxy") for line in calls), calls

    def test_no_proxy_container_means_nothing_to_do(self, tmp_path: Path) -> None:
        completed, calls = _with_docker(
            tmp_path, self.WITHHOLD % (self.DEPLOY, "x.sslip.io"), STUB_PROXY="0", STUB_PORT_OUT="0.0.0.0:443\n"
        )
        assert completed.stdout.strip() == "rc=0" and not any("up -d" in line for line in calls), calls

    def test_a_published_443_is_withdrawn_and_then_asked_again(self, tmp_path: Path) -> None:
        completed, calls = _with_docker(
            tmp_path, self.WITHHOLD % (self.DEPLOY, "x.sslip.io"), STUB_PROXY="1", STUB_PORT_OUT="0.0.0.0:443\n"
        )
        assert completed.stdout.strip() == "rc=0", completed.stdout
        (up,) = [line for line in calls if line.endswith("up -d --no-deps proxy")]
        assert "compose.tls.yml" not in up and "compose.acme.yml" in up, up
        assert calls[-1].startswith("port "), "it did not ask whether the port is really closed afterwards"

    def test_a_proxy_that_cannot_be_recreated_is_a_failure(self, tmp_path: Path) -> None:
        completed, _ = _with_docker(
            tmp_path, self.WITHHOLD % (self.DEPLOY, "x.sslip.io"),
            STUB_PROXY="1", STUB_PORT_OUT="0.0.0.0:443\n", STUB_UP_STATUS="1",
        )
        assert completed.stdout.strip() == "rc=1", completed.stdout

    def test_a_port_that_stays_published_after_a_successful_recreate_is_a_failure(self, tmp_path: Path) -> None:
        """Without a certificate name nothing can be dropped: there is no overlay to leave out."""
        completed, _ = _with_docker(
            tmp_path, self.WITHHOLD % (self.DEPLOY, ""), STUB_PROXY="1", STUB_PORT_OUT="0.0.0.0:443\n"
        )
        assert completed.stdout.strip() == "rc=1", completed.stdout


# ====================================================================================================
# deploy.sh
# ====================================================================================================

#: The acme suite's stub, with two additions: the gate's output and status come from the environment (already
#: there), and the proxy's published port is STATEFUL -- every `up` that names the proxy leaves it publishing 8443
#: exactly when the call carried the 443 overlay, which is what recreating a compose service does.
STATEFUL_PORT = '''if argv[:1] == ["port"]:
    state_file = setting("STUB_LOG") + ".published"
    if os.path.exists(state_file) and argv[-1] == "8443/tcp":
        published = open(state_file, encoding="utf-8").read().strip() == "yes"
        sys.stdout.write("0.0.0.0:443\\n" if published else "")
        sys.exit(0 if published else 1)
    sys.stdout.write(setting("STUB_PORT_OUT"))
    sys.exit(0)
'''
ORIGINAL_PORT = '''if argv[:1] == ["port"]:
    sys.stdout.write(setting("STUB_PORT_OUT"))
    sys.exit(0)
'''
STATEFUL_UP = '''    if sub == "up":
        if sub == "up" and rest[-3:] == ["-d", "--no-deps", "proxy"] and int(setting("STUB_PROXY_UP_STATUS", "0")):
            sys.exit(int(setting("STUB_PROXY_UP_STATUS", "0")))
        with open(setting("STUB_LOG") + ".published", "w", encoding="utf-8") as handle:
            handle.write("yes" if "compose.tls.yml" in " ".join(argv) else "no")
        sys.exit(0)
    if sub == "build":
        sys.exit(0)
'''
ORIGINAL_UP = '''    if sub in ("build", "up"):
        sys.exit(0)
'''


@pytest.fixture(autouse=True)
def _a_proxy_whose_published_port_follows_what_was_created(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = acme.DOCKER_STUB
    assert stub.count(ORIGINAL_PORT) == 1 and stub.count(ORIGINAL_UP) == 1, "the acme harness's docker stub changed shape"
    monkeypatch.setattr(acme, "DOCKER_STUB", stub.replace(ORIGINAL_PORT, STATEFUL_PORT).replace(ORIGINAL_UP, STATEFUL_UP))
    # verify-deployed.sh's harness: the proxy's published port, from the environment.
    probe_stub = probe.DOCKER_STUB
    anchor = 'if "auditmanager.access.check" in line:'
    assert probe_stub.count(anchor) == 1
    port = (
        'if argv[:1] == ["port"]:\n'
        '    sys.stdout.write(os.environ.get("STUB_PORT_OUT", ""))\n'
        '    sys.exit(0 if os.environ.get("STUB_PORT_OUT") else 1)\n\n'
    )
    monkeypatch.setattr(probe, "DOCKER_STUB", probe_stub.replace(anchor, port + anchor, 1))


def _gate(verdict: str) -> dict[str, str]:
    return {
        "clean": {"STUB_GATE_OUTPUT": CLEAN, "STUB_GATE_STATUS": "0"},
        "clean+warning": {"STUB_GATE_OUTPUT": f"{WARNING}\n{CLEAN}", "STUB_GATE_STATUS": "0"},
        "finding": {"STUB_GATE_OUTPUT": FINDING, "STUB_GATE_STATUS": "1"},
        "unknown": {"STUB_GATE_OUTPUT": "access-check FAILED: could not connect", "STUB_GATE_STATUS": "2"},
    }[verdict]


def _published_at_the_end(log: Path) -> bool | None:
    state = Path(str(log) + ".published")
    return None if not state.exists() else state.read_text(encoding="utf-8").strip() == "yes"


def _deploy(tmp_path: Path, port: int, *, named: bool, publish: str = "no", pair: str = "pair-absent",
            script: Path | None = None, now: bool = False, verdict: str = "clean", **more: str):  # type: ignore[no-untyped-def]
    staged = acme._stage(tmp_path, script=script)
    settings = acme._acme_settings(ALPHA_PUBLISH_HTTPS=publish) if named else {}
    stub = {"STUB_PAIR": pair, **_gate(verdict), **more}
    if now:
        stub["STUB_PORT_OUT"] = "0.0.0.0:443\n"
    completed, log = acme._run(staged, acme._env(tmp_path, port, **settings), tmp_path, stub=stub)
    return completed, log


def _proxy_ups(log: Path) -> list[str]:
    return [line for line in acme._compose_calls(log, "up") if line.endswith("up -d --no-deps proxy")]


def _gate_calls(log: Path) -> list[str]:
    return [line for line in acme._calls(log) if "auditmanager.access.check" in line]


class TestWithNoCertificateNameTheGateStillGuardsTheDeploy:
    def test_clean_the_deploy_goes_through_and_the_gate_ran_after_the_migrations_check(
        self, tmp_path: Path, serving: int
    ) -> None:
        completed, log = _deploy(tmp_path, serving, named=False)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        calls = acme._calls(log)
        (gate,) = [i for i, line in enumerate(calls) if "auditmanager.access.check" in line]
        database = next(i for i, line in enumerate(calls) if "auditmanager.shared.db.check" in line)
        conformance = next(i for i, line in enumerate(calls) if "openapi_conformance.py" in line)
        assert database < gate < conformance, calls
        assert "--entrypoint python api" in calls[gate] and calls[gate].endswith("-m auditmanager.access.check --gate")
        assert "no account accepts the published password" in completed.stdout
        assert _proxy_ups(log) == [], "no certificate name, no terminator: there is no proxy to recreate"

    def test_a_temporary_password_is_a_warning_and_never_a_refusal(self, tmp_path: Path, serving: int) -> None:
        completed, _ = _deploy(tmp_path, serving, named=False, verdict="clean+warning")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "GATE WARNING temporary password: login=someone@example.invalid" in completed.stdout, completed.stdout

    def test_the_published_pair_ends_the_deploy_non_zero_naming_the_login(self, tmp_path: Path, serving: int) -> None:
        completed, log = _deploy(tmp_path, serving, named=False, verdict="finding")
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "deploy.sh: REFUSED: [default_credential] the published admin/password pair is valid: admin still accepts" in completed.stderr, completed.stderr
        assert "SSH tunnel" in completed.stderr
        # The stack IS up and healthy: only the verdict fails, the services are not stopped.
        assert acme._compose_calls(log, "up") != [] and "every service is there" in completed.stdout
        assert "access-check GATE DEFAULT CREDENTIAL: login=admin" in completed.stdout, "the logins were not shown"
        # And what follows the gate did not run: the deploy is not successful.
        assert not any("openapi_conformance.py" in line for line in acme._calls(log))
        assert "is up at" not in completed.stdout

    @pytest.mark.parametrize("verdict", ["unknown"])
    def test_a_gate_that_cannot_be_answered_refuses_by_itself(self, verdict: str, tmp_path: Path, serving: int) -> None:
        completed, log = _deploy(tmp_path, serving, named=False, verdict=verdict)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "[default_credential_unanswered]" in completed.stderr and "exited 2" in completed.stderr, completed.stderr
        assert not any("openapi_conformance.py" in line for line in acme._calls(log))

    def test_a_gate_that_printed_nothing_is_not_a_clean_one(self, tmp_path: Path, serving: int) -> None:
        completed, _ = _deploy(tmp_path, serving, named=False, STUB_GATE_OUTPUT="", STUB_GATE_STATUS="0")
        assert completed.returncode == REFUSED and "[default_credential_unanswered]" in completed.stderr, completed.stderr

    def test_the_guard_is_shown_able_to_fail(self, tmp_path: Path, serving: int) -> None:
        cut = _cut(tmp_path / "cut", "default-credential-gate")
        completed, log = _deploy(tmp_path / "run", serving, named=False, verdict="finding", script=cut)
        assert "default_credential" not in completed.stderr, completed.stderr
        assert completed.returncode == 0, "with the gate deleted the published pair no longer stops the deploy"
        assert _gate_calls(log) == []


def _cut(directory: Path, guard: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    text = acme.DEPLOY.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n", re.DOTALL | re.MULTILINE
    )
    text, count = block.subn("", text)
    assert count == 1
    path = directory / "mutant.sh"
    path.write_text(text, encoding="utf-8")
    return path


class TestWithACertificateName443IsPublishedOnlyWhenEverythingAgrees:
    @pytest.mark.parametrize("now", [False, True], ids=["443-closed-before", "443-open-before"])
    @pytest.mark.parametrize("verdict", ["clean", "finding", "unknown"])
    @pytest.mark.parametrize("pair", ["pair-present", "pair-absent"])
    @pytest.mark.parametrize("publish", ["yes", "no"])
    def test_443_is_published_at_the_end_only_on_three_yeses(
        self, publish: str, pair: str, verdict: str, now: bool, tmp_path: Path, serving: int
    ) -> None:
        completed, log = _deploy(tmp_path, serving, named=True, publish=publish, pair=pair, now=now, verdict=verdict)
        wanted = publish == "yes" and pair == "pair-present"
        ended = _published_at_the_end(log)
        assert ended is not None, "no `up` was issued at all"
        if verdict == "clean":
            assert completed.returncode == 0, (completed.stdout, completed.stderr)
            assert ended is wanted, (publish, pair, now, ended)
        elif verdict == "finding":
            assert completed.returncode == REFUSED and "[default_credential]" in completed.stderr, completed.stderr
            assert ended is False, f"443 is published while the published pair is valid: {publish} {pair} {now}"
            assert "Public port 443 is NOT published" in completed.stderr
        else:
            # The gate could not be asked: this run opens nothing and changes nothing it was not already doing.
            assert completed.returncode == REFUSED and "[default_credential_unanswered]" in completed.stderr
            assert ended is (wanted and now), (publish, pair, now, ended)
        # In no case does a full `up` of a proxy that is not already published carry the 443 overlay.
        first_full = [line for line in acme._compose_calls(log, "up") if not line.endswith("--no-deps proxy")][0]
        assert ("compose.tls.yml" in first_full) is (now and wanted), first_full

    def test_a_finding_withdraws_a_published_443_by_recreating_only_the_proxy_without_the_overlay(
        self, tmp_path: Path, serving: int
    ) -> None:
        completed, log = _deploy(
            tmp_path, serving, named=True, publish="yes", pair="pair-present", now=True, verdict="finding"
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        (up,) = _proxy_ups(log)
        assert re.search(r"compose\.server\.yml --file \S+compose\.acme\.yml up -d --no-deps proxy$", up), up
        assert "public port" in completed.stdout and "NOT published: the proxy was recreated without the 443 overlay" in completed.stdout
        assert _published_at_the_end(log) is False
        # Every other service keeps running: nothing was stopped.
        assert not any(line.split()[:1] == ["compose"] and " stop" in line for line in acme._calls(log))

    def test_a_proxy_that_cannot_be_recreated_says_443_may_be_open(self, tmp_path: Path, serving: int) -> None:
        completed, _ = _deploy(
            tmp_path, serving, named=True, publish="yes", pair="pair-present", now=True,
            verdict="finding", STUB_PROXY_UP_STATUS="1",
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "could not be recreated to withdraw public port" in completed.stderr, completed.stderr
        assert "Public port 443 may be in the wrong state" in completed.stderr

    def test_an_unchanged_published_host_is_not_recreated_a_second_time(self, tmp_path: Path, serving: int) -> None:
        """`W24-IDEM`'s rule: a deploy that changes nothing changes nothing. Already published, still wanted, clean:
        the provisional `up` kept the overlay and the gate has nothing to converge."""
        completed, log = _deploy(
            tmp_path, serving, named=True, publish="yes", pair="pair-present", now=True, verdict="clean"
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert _proxy_ups(log) == [], acme._calls(log)
        assert _published_at_the_end(log) is True

    def test_the_guard_is_shown_able_to_fail_the_exposure_it_closes(self, tmp_path: Path, serving: int) -> None:
        cut = _cut(tmp_path / "cut", "default-credential-gate")
        completed, log = _deploy(
            tmp_path / "run", serving, named=True, publish="yes", pair="pair-present", now=True,
            verdict="finding", script=cut,
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert _published_at_the_end(log) is True, "with the guard deleted a valid published pair keeps 443 open"
        assert _proxy_ups(log) == []


class TestTheListenersLibraryMustBeThere:
    def test_a_clone_without_it_is_refused_before_docker_is_touched(self, tmp_path: Path, serving: int) -> None:
        staged = acme._stage(tmp_path)
        (staged.parent / "lib/proxy-listeners.sh").unlink()
        completed, log = acme._run(staged, acme._env(tmp_path, serving), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "proxy-listeners.sh is missing or unreadable" in completed.stderr, completed.stderr
        assert not log.exists(), acme._calls(log)

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, serving: int) -> None:
        staged = acme._stage(tmp_path / "run", script=_cut(tmp_path / "cut", "listeners-library-present"))
        (staged.parent / "lib/proxy-listeners.sh").unlink()
        completed, _ = acme._run(staged, acme._env(tmp_path / "run", serving), tmp_path / "run")
        assert "proxy-listeners.sh is missing or unreadable" not in completed.stderr, completed.stderr
        assert completed.returncode != REFUSED


# ====================================================================================================
# verify-deployed.sh
# ====================================================================================================

CREDENTIAL = 8


def _verify(world, tmp_path: Path, **stub: str):  # type: ignore[no-untyped-def]
    repo, deploy, image = world
    return probe._run(deploy / "verify-deployed.sh", tmp_path=tmp_path, repo=repo, STUB_IMAGE=str(image), **stub)


class TestVerifyDeployedAsksTheSameGate:
    def test_clean_it_is_still_this_tree(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, **_gate("clean"))
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "IS this tree" in completed.stdout
        (asked,) = [line for line in calls.splitlines() if "auditmanager.access.check" in line]
        assert asked.endswith("run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check --gate"), asked

    def test_a_temporary_password_only_warns(self, world, tmp_path: Path) -> None:
        completed, _ = _verify(world, tmp_path, **_gate("clean+warning"))
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "GATE WARNING temporary password: login=someone@example.invalid" in completed.stdout

    def test_the_published_pair_is_exit_8_and_names_the_login(self, world, tmp_path: Path) -> None:
        completed, _ = _verify(world, tmp_path, **_gate("finding"))
        assert completed.returncode == CREDENTIAL, (completed.stdout, completed.stderr)
        assert "the published admin/password pair is valid: admin still accepts the published password" in completed.stderr
        assert "Public port 443 is not published" in completed.stderr
        assert "IS this tree" not in completed.stdout

    def test_and_it_says_so_loudly_when_443_is_published_meanwhile(self, world, tmp_path: Path) -> None:
        completed, _ = _verify(world, tmp_path, STUB_PORT_OUT="0.0.0.0:443\n", **_gate("finding"))
        assert completed.returncode == CREDENTIAL, (completed.stdout, completed.stderr)
        assert "PUBLIC PORT 443 IS PUBLISHED while the pair is valid" in completed.stderr

    @pytest.mark.parametrize("verdict", ["unknown"])
    def test_a_gate_that_cannot_be_answered_is_exit_4_and_never_a_pass(self, world, tmp_path: Path, verdict: str) -> None:
        completed, _ = _verify(world, tmp_path, **_gate(verdict))
        assert completed.returncode == probe.UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "could not be answered" in completed.stderr and "IS this tree" not in completed.stdout

    def test_a_stack_that_is_not_this_tree_is_reported_as_that_before_the_gate_is_asked(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, STUB_OMIT="/app/src/auditmanager/runs/carrier.py", **_gate("finding"))
        assert completed.returncode == probe.DRIFT, (completed.stdout, completed.stderr)
        assert "auditmanager.access.check" not in calls

    def test_the_step_is_shown_able_to_fail(self, world, tmp_path: Path) -> None:
        repo, deploy, image = world
        text = (ROOT / "infra/deploy/verify-deployed.sh").read_text(encoding="utf-8")
        block = re.compile(
            r"^# >>> step: default-credential-gate\n.*?^# <<< step: default-credential-gate\n", re.DOTALL | re.MULTILINE
        )
        cut, count = block.subn("", text)
        assert count == 1
        script = deploy / "verify-deployed.sh"
        script.write_text(cut, encoding="utf-8")
        completed, calls = probe._run(script, tmp_path=tmp_path, repo=repo, STUB_IMAGE=str(image), **_gate("finding"))
        assert completed.returncode == 0, "with the step deleted a valid published pair no longer fails the verify"
        assert "auditmanager.access.check" not in calls


# ====================================================================================================
# what stays as it was, and the two stale hints
# ====================================================================================================


class TestReadinessKeepsTheWiderQuestionAndTheStaleHintsAreGone:
    def test_readiness_asks_the_default_mode_and_never_gates(self) -> None:
        readiness = (ROOT / "infra/deploy/readiness.sh").read_text(encoding="utf-8")
        asked = [line for line in readiness.splitlines() if "-m auditmanager.access.check" in line]
        assert len(asked) == 1 and "--gate" not in asked[0], asked
        assert "IT DOES NOT BLOCK A DEPLOY" in readiness

    def test_reload_proxy_names_both_overlays_in_its_hint(self) -> None:
        reload_proxy = (ROOT / "infra/deploy/reload-proxy.sh").read_text(encoding="utf-8")
        assert "(add proxy/compose.tls.yml if TLS is on)" not in reload_proxy
        assert "add infra/acme/compose.acme.yml if ALPHA_CERT_NAME is set, and proxy/compose.tls.yml if 443 is published" in reload_proxy
        assert "which this script does not know about and must not drop" not in reload_proxy

    def test_the_copy_key_installs_the_library_too(self) -> None:
        runbook = (ROOT / "docs/program/DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
        assert "lib/proxy-listeners.sh" in runbook[runbook.index("copy-serve/lib") :], (
            "section 13 must tell the owner to extract the library beside copy-serve.sh"
        )
