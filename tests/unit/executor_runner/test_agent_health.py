"""`EXEC2-AGENT-01` -- B2 section 11, tests 5 and 8 (the agent half): the health report and the enrollment exchange.

* the report is exactly ``ReportRunnerHealthRequest`` of contract 1.15.0, coherent (no client twice, no version or
  login state for a client that is not installed), and is sent at start, again when detection changes and at the
  interval, without ever blocking the claim loop;
* ``agent.py --enroll-only`` exchanges the one-time secret (the bearer of ``POST /runner/enroll``) for a runner
  token, stores only the newest token in the environment file (mode 0600) and removes the secret from it;
* neither the secret nor a token appears in a log line, an error, the standard streams or an argument vector.

The stand is ``_agent_support.Stand`` (real HTTP on loopback); the agent is run in process where its objects are
under test and as a subprocess where its exit code and streams are.
"""

from __future__ import annotations

import importlib.util
import json
import re
import stat
import sys
import threading
import time
import types
from pathlib import Path

import pytest

for _name, _file in (("executor_runner_support", "_support.py"), ("executor_runner_agent_support", "_agent_support.py")):
    if _name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(_name, Path(__file__).with_name(_file))
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_name] = _module
        _spec.loader.exec_module(_module)
S = sys.modules["executor_runner_support"]
A = sys.modules["executor_runner_agent_support"]
agent = A.load_module("exec_agent_health_under_test", A.RUNNER_DIR / "agent.py")

SECRET, TOKEN = A.SECRET, A.WORKING_TOKEN
INSTANCE = "agent-instance-health"
GRANT_VAR = "AUDITMANAGER_ENROLLMENT_SECRET"
TOKEN_VAR = "PDF_ANALYSIS_RUNNER_TOKEN"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes and shell stand-ins")


def _cfg(**overrides):
    cfg = agent.Config(origin="http://127.0.0.1:1", declared_model="claude-opus-5", command_argv=["unused"])
    for name, value in overrides.items():
        setattr(cfg, name, value)
    return cfg


def _clis(codex: str = "valid", claude: str | None = None) -> list[dict]:
    items = [{"cli": "claude", "installed": False, "auth_state": "unknown"}]
    if claude is not None:
        items[0] = {"cli": "claude", "installed": True, "version": "2.1.310", "auth_state": claude}
    items.append({"cli": "codex", "installed": True, "version": "0.46.0", "auth_state": codex})
    return items


class Log:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self._lock = threading.Lock()

    def __call__(self, message: str) -> None:
        with self._lock:
            self.lines.append(message)

    @property
    def text(self) -> str:
        with self._lock:
            return "\n".join(self.lines)


def _eventually(predicate, timeout: float = 5.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def _reporter(stand, *, detector, token=TOKEN, report_seconds=60.0, detect_seconds=0.05, **cfg_overrides):
    cfg = _cfg(origin=stand.origin, **cfg_overrides)
    client = agent.RunnerClient(stand.origin, token, allow_insecure_http=True)
    log, stop = Log(), threading.Event()
    reporter = agent.HealthReporter(cfg, client, INSTANCE, log, stop, detector=detector, version="0.9.0",
                                    report_seconds=report_seconds, detect_seconds=detect_seconds)
    return reporter, log, stop


# ------------------------------------------------------------------------------------ the report


def test_the_report_is_the_contracts_request_in_both_profiles():
    report = agent.build_health_report(_cfg(), INSTANCE, _clis(), "0.9.0")
    assert A.schema_errors("ReportRunnerHealthRequest", report) == []
    assert report == {"agent_version": "0.9.0", "clis": _clis(), "concurrency": 1, "execution_profile": "command",
                      "features": [], "runner_instance_id": INSTANCE}
    wide = agent.build_health_report(_cfg(mode="endpoint", concurrency=3, endpoint_accept_images=True, endpoint_max_images=2),
                                     agent.new_instance_id(), _clis(claude="login_required"), "0.9.0")
    assert A.schema_errors("ReportRunnerHealthRequest", wide) == []
    assert wide["execution_profile"] == "endpoint" and wide["concurrency"] == 3 and wide["features"] == ["images"]
    assert agent.build_health_report(_cfg(command_accept_images=True), INSTANCE, [], "x")["features"] == ["images"]


def test_an_incoherent_report_is_never_built():
    with pytest.raises(ValueError):
        agent.build_health_report(_cfg(), INSTANCE, _clis() + [_clis()[1]], "0.9.0")  # codex twice
    with pytest.raises(ValueError):
        agent.build_health_report(_cfg(), INSTANCE, [{"cli": "claude", "installed": False, "version": "1.0.0", "auth_state": "unknown"}], "0.9.0")
    with pytest.raises(ValueError):
        agent.build_health_report(_cfg(), INSTANCE, [{"cli": "claude", "installed": False, "auth_state": "valid"}], "0.9.0")


def test_the_report_holds_enumerations_and_bounded_strings_only():
    text = json.dumps(agent.build_health_report(_cfg(), INSTANCE, _clis(), "0.9.0"))
    assert "/" not in text and "@" not in text and "amr_" not in text and "ame_" not in text


def test_the_version_is_the_packages_and_an_unversioned_checkout_says_so(tmp_path):
    assert agent.agent_version(tmp_path) == "unversioned"
    (tmp_path / "VERSION").write_text("0.9.0\n")
    assert agent.agent_version(tmp_path) == "0.9.0"
    (tmp_path / "VERSION").write_text("not a version at all\n")
    assert agent.agent_version(tmp_path) == "unversioned"
    assert re.fullmatch(agent.AGENT_VERSION_RE.pattern, "unversioned")


def test_the_real_detector_output_is_a_coherent_report(tmp_path, monkeypatch):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    A.make_cli(bin_dir, "codex", "0.46.0")
    A.log_in(home, "codex")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv(agent.detect.DIRS_ENV, str(bin_dir))
    report = agent.build_health_report(_cfg(), INSTANCE, agent.detect.detect_all(), "0.9.0")
    assert A.schema_errors("ReportRunnerHealthRequest", report) == []
    assert [item["installed"] for item in report["clis"]] == [False, True]


# --------------------------------------------------------------------------- the reporter in process


def test_the_first_report_goes_out_at_start_with_the_runner_token_and_conforms():
    with A.Stand() as stand:
        reporter, log, stop = _reporter(stand, detector=lambda: _clis())
        reporter.start()
        try:
            request = stand.wait_for("health")[0]
        finally:
            stop.set()
        assert request["authorization"] == "Bearer " + TOKEN and request["content_type"].startswith("application/json")
        assert A.schema_errors("ReportRunnerHealthRequest", request["body"]) == []
        assert request["body"]["runner_instance_id"] == INSTANCE and request["body"]["clis"] == _clis()
        assert TOKEN not in log.text


def test_an_unchanged_detection_is_not_resent_before_the_interval():
    with A.Stand() as stand:
        reporter, _, stop = _reporter(stand, detector=lambda: _clis(), report_seconds=60.0, detect_seconds=0.05)
        reporter.start()
        stand.wait_for("health")
        time.sleep(0.6)
        stop.set()
        assert len(stand.of("health")) == 1


def test_the_report_is_repeated_at_the_interval():
    with A.Stand() as stand:
        reporter, _, stop = _reporter(stand, detector=lambda: _clis(), report_seconds=0.25, detect_seconds=0.05)
        reporter.start()
        try:
            stand.wait_for("health", 3, timeout=10)
        finally:
            stop.set()


def test_a_change_in_what_detection_finds_is_reported_at_once_not_at_the_interval():
    state = {"codex": "login_required"}
    with A.Stand() as stand:
        reporter, log, stop = _reporter(stand, detector=lambda: _clis(codex=state["codex"]), report_seconds=600.0, detect_seconds=0.05)
        reporter.start()
        try:
            stand.wait_for("health")
            state["codex"] = "valid"  # the administrator signed the CLI in
            second = stand.wait_for("health", 2, timeout=10)[1]
        finally:
            stop.set()
        assert [item["auth_state"] for item in second["body"]["clis"] if item["cli"] == "codex"] == ["valid"]
        assert _eventually(lambda: "codex:installed/valid" in log.text)


def test_a_refused_token_ends_the_reporter_and_leaves_the_exit_code_to_the_claim_loop():
    with A.Stand(tokens=()) as stand:
        reporter, log, stop = _reporter(stand, detector=lambda: _clis())
        thread = reporter.start()
        thread.join(timeout=10)
        assert not thread.is_alive() and not stop.is_set()
        assert len(stand.of("health")) == 1 and "rejected the runner token" in log.text


def test_a_stand_without_the_route_is_logged_and_asked_again_only_at_the_interval():
    with A.Stand() as stand:
        stand.script("health", (404, A.envelope("not_found", "No such operation.")))
        reporter, log, stop = _reporter(stand, detector=lambda: _clis(), report_seconds=0.6, detect_seconds=0.05)
        reporter.start()
        try:
            first = stand.wait_for("health")[0]["body"]
            time.sleep(0.25)
            assert len(stand.of("health")) == 1, "not asked again before the interval"
            second = stand.wait_for("health", 2, timeout=10)[1]["body"]
        finally:
            stop.set()
        assert first == second and "does not take health reports (HTTP 404)" in log.text


def test_a_stand_that_refuses_the_report_is_logged_with_its_reason_and_not_hammered():
    with A.Stand() as stand:
        stand.script("health", (422, A.envelope("validation_failed", "agent_version does not match")))
        reporter, log, stop = _reporter(stand, detector=lambda: _clis(), report_seconds=60.0, detect_seconds=0.05)
        reporter.start()
        stand.wait_for("health")
        time.sleep(0.4)
        stop.set()
        assert len(stand.of("health")) == 1
        assert _eventually(lambda: "refused the report (HTTP 422 validation_failed)" in log.text)


def test_an_unreachable_stand_is_retried_with_the_same_report_and_never_blocks_the_caller():
    with A.Stand() as stand:
        stand.script("health", (503, A.envelope("dependency_unavailable", "down")))
        detections: list[int] = []

        def detector():
            detections.append(1)
            return _clis(codex="valid" if len(detections) == 1 else "login_required")  # a second detection would differ

        reporter, log, stop = _reporter(stand, detector=detector, report_seconds=60.0, detect_seconds=0.05)
        started = time.monotonic()
        reporter.start()
        assert time.monotonic() - started < 1.0  # start() returns at once
        try:
            requests = stand.wait_for("health", 2, timeout=15)
        finally:
            stop.set()
        assert requests[0]["body"] == requests[1]["body"], "the same report was retried, not a new detection"
        assert _eventually(lambda: "not reachable" in log.text)


class _Failing:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def report_health(self, report):
        raise self.error


@pytest.mark.parametrize("error,outcome", [
    (lambda: agent.RunnerAuthError("no", status=401), "token"),
    (lambda: agent.RunnerThrottled("slow", status=429, retry_after=0.5), "retry"),
    (lambda: agent.RunnerUnavailable("down"), "retry"),
    (lambda: agent.RunnerNotFound("none", status=404), "deferred"),
    (lambda: agent.RunnerRejected("bad", status=422, error_code="validation_failed"), "deferred"),
    (lambda: agent.RunnerConflict("busy", status=409), "deferred"),
])
def test_every_failure_of_the_call_has_one_outcome(error, outcome):
    reporter = agent.HealthReporter(_cfg(), _Failing(error()), INSTANCE, Log(), threading.Event(), detector=lambda: _clis(), version="0.9.0")
    kind, wait = reporter._send(reporter.report())
    assert kind == outcome and (wait >= 0.5 if error().status == 429 else wait == 0.0)


def test_a_detector_that_raises_is_logged_and_the_next_round_tries_again():
    calls = {"n": 0}

    def detector():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom with /secret/path")
        return _clis()

    with A.Stand() as stand:
        reporter, log, stop = _reporter(stand, detector=detector)
        reporter.start()
        try:
            stand.wait_for("health", 1, timeout=10)
        finally:
            stop.set()
        assert "detection failed (RuntimeError)" in log.text and "/secret/path" not in log.text


# ----------------------------------------------------------------------- the agent process end to end


def _run_agent(tmp_path, stand, *, bin_dir=None, token=TOKEN, extra_args=(), env=None):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    cfg = S.agent_config(tmp_path / "agent.toml", stand.origin, argv=["/bin/true"])
    environment = {"HOME": str(home), agent.detect.DIRS_ENV: str(bin_dir or tmp_path / "no-clis"), **(env or {})}
    return S.AgentProcess(cfg, *extra_args, token=token, env=environment)


def test_a_running_agent_reports_what_it_detects_as_the_service_user_and_keeps_claiming(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    A.make_cli(bin_dir, "codex", "0.46.0")
    A.log_in(home, "codex")
    with A.Stand() as stand:
        with _run_agent(tmp_path, stand, bin_dir=bin_dir) as proc:
            body = stand.wait_for("health")[0]["body"]
            stand.wait_for("claim", 2)
            proc.terminate()
            assert proc.wait(timeout=15) == 0, proc.stderr
        assert A.schema_errors("ReportRunnerHealthRequest", body) == []
        assert body["clis"] == [{"cli": "claude", "installed": False, "auth_state": "unknown"},
                                {"cli": "codex", "installed": True, "version": "0.46.0", "auth_state": "valid"}]
        assert body["concurrency"] == 1 and body["execution_profile"] == "command" and body["features"] == []
        assert body["agent_version"] == "unversioned" and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", body["runner_instance_id"])
        claim_instances = {r["body"].get("runner_instance_id") for r in stand.of("claim")}
        assert claim_instances == {body["runner_instance_id"]}, "the health report names the process the claims name"
        assert TOKEN not in proc.stderr and TOKEN not in proc.stdout


def test_a_revoked_token_still_exits_3_with_a_single_claim_and_the_health_report_changes_nothing(tmp_path):
    with A.Stand(tokens=()) as stand:
        with _run_agent(tmp_path, stand) as proc:
            assert proc.wait(timeout=15) == 3
        assert len(stand.of("claim")) == 1 and "rejected the runner token" in proc.stderr


def test_an_agent_on_a_stand_without_the_health_route_still_works(tmp_path):
    with A.Stand() as stand:
        stand.script("health", (404, A.envelope("not_found", "No such operation.")))
        with _run_agent(tmp_path, stand) as proc:
            stand.wait_for("health")
            stand.wait_for("claim", 2)
            proc.terminate()
            assert proc.wait(timeout=15) == 0
        assert "does not take health reports" in proc.stderr


# ----------------------------------------------------------------------- the client's two operations


def test_redeem_enrollment_sends_the_secret_as_the_bearer_and_exactly_the_contracts_body():
    with A.Stand() as stand:
        client = agent.RunnerClient(stand.origin, SECRET, allow_insecure_http=True)
        issued = client.redeem_enrollment(SECRET, INSTANCE, "0.9.0")
        request = stand.of("enroll")[0]
    assert request["authorization"] == "Bearer " + SECRET and request["path"] == "/api/v1/runner/enroll"
    assert request["body"] == {"runner_instance_id": INSTANCE, "agent_version": "0.9.0"}
    assert A.schema_errors("RedeemExecutorEnrollmentRequest", request["body"]) == []
    assert issued["token"] == stand.minted[0] and isinstance(issued["runner_token"], dict)
    with A.Stand() as stand:
        agent.RunnerClient(stand.origin, SECRET, allow_insecure_http=True).redeem_enrollment(SECRET, INSTANCE)
        assert stand.of("enroll")[0]["body"] == {"runner_instance_id": INSTANCE}, "agent_version is optional"


def test_redeem_enrollment_uses_the_secret_it_is_given_not_the_clients_token_and_scrubs_both():
    with A.Stand() as stand:
        stand.script("enroll", (409, A.envelope("conflict", f"echo {SECRET} and {TOKEN}")))
        client = agent.RunnerClient(stand.origin, TOKEN, allow_insecure_http=True)  # a client that already has a token
        with pytest.raises(agent.RunnerConflict) as caught:
            client.redeem_enrollment(SECRET, INSTANCE)
        assert stand.of("enroll")[0]["authorization"] == "Bearer " + SECRET
    assert SECRET not in str(caught.value) and TOKEN not in str(caught.value) and caught.value.status == 409


@pytest.mark.parametrize("status,error", [(401, "RunnerAuthError"), (409, "RunnerConflict"), (422, "RunnerRejected"),
                                           (429, "RunnerThrottled"), (503, "RunnerUnavailable")])
def test_redeem_enrollment_maps_the_stands_answers_to_the_clients_errors(status, error):
    with A.Stand() as stand:
        stand.script("enroll", (status, A.envelope("x", "no")))
        client = agent.RunnerClient(stand.origin, SECRET, allow_insecure_http=True)
        with pytest.raises(getattr(agent, error)):
            client.redeem_enrollment(SECRET, INSTANCE)


@pytest.mark.parametrize("secret,instance,version", [("", INSTANCE, None), ("has space", INSTANCE, None), ("tab\tin", INSTANCE, None),
                                                      (SECRET, "short", None), (SECRET, "bad/char-instance", None),
                                                      (SECRET, INSTANCE, "has space"), (SECRET, INSTANCE, "")])
def test_redeem_enrollment_refuses_a_malformed_call_before_anything_is_sent(secret, instance, version):
    with A.Stand() as stand:
        client = agent.RunnerClient(stand.origin, SECRET, allow_insecure_http=True)
        with pytest.raises(agent.RunnerRejected):
            client.redeem_enrollment(secret, instance, version)
        assert stand.requests == []


@pytest.mark.parametrize("document", [{"token": "short", "runner_token": {}}, {"runner_token": {}}, {"token": "x" * 56}, ["token"], {}])
def test_redeem_enrollment_treats_a_document_that_is_not_a_token_as_repeatable(document):
    with A.Stand() as stand:
        stand.script("enroll", (201, document))
        with pytest.raises(agent.RunnerUnavailable):
            agent.RunnerClient(stand.origin, SECRET, allow_insecure_http=True).redeem_enrollment(SECRET, INSTANCE)


def test_report_health_sends_the_report_with_the_runner_token_and_returns_the_acknowledgement():
    report = agent.build_health_report(_cfg(), INSTANCE, _clis(), "0.9.0")
    with A.Stand() as stand:
        client = agent.RunnerClient(stand.origin, TOKEN, allow_insecure_http=True)
        ack = client.report_health(report)
        request = stand.of("health")[0]
    assert request["authorization"] == "Bearer " + TOKEN and request["path"] == "/api/v1/runner/health" and request["body"] == report
    assert isinstance(ack["recorded_at"], str)


def test_report_health_refuses_what_is_not_a_report_and_an_answer_that_is_not_an_acknowledgement():
    with A.Stand() as stand:
        client = agent.RunnerClient(stand.origin, TOKEN, allow_insecure_http=True)
        with pytest.raises(agent.RunnerRejected):
            client.report_health(["not", "a", "report"])
        assert stand.requests == []
        stand.script("health", (200, {"ok": True}), (401, A.envelope("authentication_required", "no")))
        with pytest.raises(agent.RunnerUnavailable):
            client.report_health({})
        with pytest.raises(agent.RunnerAuthError):
            client.report_health({})


def test_the_agent_calls_the_clients_public_operations_and_no_private_one():
    source = (A.RUNNER_DIR / "agent.py").read_text()
    assert "client.report_health(" in source or "self.client.report_health(" in source
    assert ".redeem_enrollment(" in source and "_call(" not in source and "_stand_post" not in source


# --------------------------------------------------------------------------------- the environment file


def test_storing_a_token_keeps_other_lines_drops_the_spent_secret_and_ends_at_mode_0600(tmp_path):
    env_file = tmp_path / "agent.env"
    env_file.write_text(f"# kept\nOTHER=1\n{TOKEN_VAR}=amr_old\n{GRANT_VAR}={SECRET}\nENDPOINT_KEY=k\n")
    env_file.chmod(0o644)
    agent.store_runner_token(env_file, TOKEN_VAR, TOKEN, drop=(GRANT_VAR,))
    assert env_file.read_text() == f"# kept\nOTHER=1\nENDPOINT_KEY=k\n{TOKEN_VAR}={TOKEN}\n"
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    agent.store_runner_token(env_file, TOKEN_VAR, TOKEN, drop=(GRANT_VAR,))  # idempotent
    assert env_file.read_text().count(TOKEN_VAR) == 1
    assert [p.name for p in tmp_path.iterdir()] == ["agent.env"], "no temporary file is left"
    fresh = tmp_path / "new.env"
    agent.store_runner_token(fresh, TOKEN_VAR, TOKEN)
    assert fresh.read_text() == f"{TOKEN_VAR}={TOKEN}\n" and stat.S_IMODE(fresh.stat().st_mode) == 0o600


# --------------------------------------------------------------------------- the enrollment exchange


def _enroll(tmp_path, stand, *, secret=SECRET, env_file=None, args=None, pre=None, home="install"):
    """``agent.py --enroll-only`` as a subprocess; returns ``(process, env_file)``."""
    root = tmp_path / home
    root.mkdir(exist_ok=True)
    env_file = env_file or root / "agent.env"
    if pre is not None:
        env_file.write_text(pre)
        env_file.chmod(0o600)
    cfg = S.agent_config(root / "agent.toml", stand.origin, argv=["/bin/true"])
    env = {GRANT_VAR: secret} if secret is not None else {}
    proc = S.AgentProcess(cfg, *(args if args is not None else ["--env-file", str(env_file), "--enroll-only"]), token=None, env=env)
    proc.wait(timeout=30)
    return proc, env_file


def test_enrolling_exchanges_the_secret_for_a_token_and_stores_only_the_token(tmp_path):
    with A.Stand() as stand:
        proc, env_file = _enroll(tmp_path, stand, pre=f"OTHER=1\n{GRANT_VAR}={SECRET}\n")
        assert proc.proc.returncode == 0, proc.stderr
        request = stand.of("enroll")[0]
        assert request["authorization"] == "Bearer " + SECRET and request["path"] == "/api/v1/runner/enroll"
        assert A.schema_errors("RedeemExecutorEnrollmentRequest", request["body"]) == []
        assert set(request["body"]) == {"runner_instance_id", "agent_version"}
        minted = stand.minted[0]
        assert env_file.read_text() == f"OTHER=1\n{TOKEN_VAR}={minted}\n"
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
        for stream in (proc.stdout, proc.stderr):
            assert SECRET not in stream and minted not in stream
        instance_file = env_file.with_name("enroll-instance")
        assert instance_file.read_text().strip() == request["body"]["runner_instance_id"]
        assert stat.S_IMODE(instance_file.stat().st_mode) == 0o600
        assert not list(stand.of("claim")) and not list(stand.of("health")), "enrolling only enrolls"


def test_a_repeat_from_the_same_install_stores_the_fresh_token_and_only_that_one(tmp_path):
    with A.Stand() as stand:
        first, env_file = _enroll(tmp_path, stand)
        second, _ = _enroll(tmp_path, stand, env_file=env_file)
        assert first.proc.returncode == second.proc.returncode == 0, first.stderr + second.stderr
        one, two = stand.minted
        assert one != two and stand.revoked_tokens == {one} and stand.valid_tokens >= {two}
        assert env_file.read_text() == f"{TOKEN_VAR}={two}\n"
        ids = [r["body"]["runner_instance_id"] for r in stand.of("enroll")]
        assert ids[0] == ids[1], "the same install sends the same runner_instance_id"


def test_another_install_is_a_different_instance_and_is_refused_without_touching_anything(tmp_path):
    with A.Stand() as stand:
        first, _ = _enroll(tmp_path, stand, home="host-a")
        other, env_file = _enroll(tmp_path, stand, home="host-b")
        assert first.proc.returncode == 0 and other.proc.returncode == 3, other.stderr
        assert not env_file.exists() and len(stand.minted) == 1
        assert "already redeemed" in other.stderr and SECRET not in other.stderr


def test_a_repeat_after_the_window_is_refused_and_the_installed_token_is_untouched(tmp_path):
    with A.Stand() as stand:
        first, env_file = _enroll(tmp_path, stand)
        kept = env_file.read_text()
        stand.window_open = False
        late, _ = _enroll(tmp_path, stand, env_file=env_file)
        assert first.proc.returncode == 0 and late.proc.returncode == 3
        assert env_file.read_text() == kept


def test_an_unknown_expired_or_revoked_secret_exits_3_and_says_so_without_the_secret(tmp_path):
    with A.Stand() as stand:
        proc, env_file = _enroll(tmp_path, stand, secret=A.OTHER_SECRET, pre="OTHER=1\n")
        assert proc.proc.returncode == 3
        assert "refused the enrollment secret (HTTP 401)" in proc.stderr
        assert A.OTHER_SECRET not in proc.stderr + proc.stdout and env_file.read_text() == "OTHER=1\n"


@pytest.mark.parametrize("reply", [(503, A.envelope("dependency_unavailable", "down")), (500, A.envelope("internal_error", "boom"))])
def test_a_stand_that_cannot_answer_is_a_retryable_exit_75(tmp_path, reply):
    with A.Stand() as stand:
        stand.script("enroll", reply)
        proc, env_file = _enroll(tmp_path, stand, pre="OTHER=1\n")
        assert proc.proc.returncode == 75, proc.stderr
        assert "again" in proc.stderr and SECRET not in proc.stderr and env_file.read_text() == "OTHER=1\n"


def test_an_unreachable_stand_is_exit_75_too(tmp_path):
    dead = A.Stand()  # bound, never served, then closed: nothing listens on its port
    origin = dead.origin
    dead.httpd.server_close()
    proc, env_file = _enroll(tmp_path, types.SimpleNamespace(origin=origin), pre="OTHER=1\n")
    assert proc.proc.returncode == 75, proc.stderr
    assert env_file.read_text() == "OTHER=1\n" and SECRET not in proc.stderr


@pytest.mark.parametrize("document", [{"token": "short", "runner_token": {}}, {"runner_token": {}}, {"token": "x" * 56}, ["token"]])
def test_an_answer_that_is_not_a_runner_token_stores_nothing_and_may_be_repeated(tmp_path, document):
    """The exchange is idempotent for this install inside its window, so a garbled answer loses nothing: exit 75."""
    with A.Stand() as stand:
        stand.script("enroll", (201, document))
        proc, env_file = _enroll(tmp_path, stand, pre="OTHER=1\n")
        assert proc.proc.returncode == 75 and env_file.read_text() == "OTHER=1\n"
        assert SECRET not in proc.stderr


def test_nothing_is_sent_unless_the_token_can_be_stored(tmp_path):
    with A.Stand() as stand:
        no_file, _ = _enroll(tmp_path, stand, args=["--enroll-only"])
        assert no_file.proc.returncode == 2 and "--env-file" in no_file.stderr
        missing_dir, _ = _enroll(tmp_path, stand, args=["--env-file", str(tmp_path / "nowhere" / "agent.env"), "--enroll-only"])
        assert missing_dir.proc.returncode == 2 and "cannot store the runner token" in missing_dir.stderr
        no_secret, _ = _enroll(tmp_path, stand, secret=None)
        assert no_secret.proc.returncode == 2 and GRANT_VAR in no_secret.stderr
        assert stand.requests == [], "the secret was never used"


def test_a_normal_start_with_a_secret_enrolls_first_and_then_claims_with_the_new_token(tmp_path):
    with A.Stand() as stand:
        env_file = tmp_path / "agent.env"
        cfg = S.agent_config(tmp_path / "agent.toml", stand.origin, argv=["/bin/true"])
        with S.AgentProcess(cfg, "--env-file", str(env_file), token=None, env={GRANT_VAR: SECRET, "HOME": str(tmp_path)}) as proc:
            claims = stand.wait_for("claim", 1)
            proc.terminate()
            assert proc.wait(timeout=15) == 0, proc.stderr
        minted = stand.minted[0]
        assert claims[0]["authorization"] == "Bearer " + minted
        assert env_file.read_text() == f"{TOKEN_VAR}={minted}\n"
        assert SECRET not in proc.stderr and minted not in proc.stderr and SECRET not in json.dumps(stand.of("claim"))


def test_a_normal_start_with_a_secret_and_no_env_file_is_a_configuration_error_that_spends_nothing(tmp_path):
    with A.Stand() as stand:
        cfg = S.agent_config(tmp_path / "agent.toml", stand.origin, argv=["/bin/true"])
        with S.AgentProcess(cfg, token=None, env={GRANT_VAR: SECRET}) as proc:
            assert proc.wait(timeout=15) == 2
        assert stand.requests == [] and "--env-file" in proc.stderr


def test_the_secret_is_gone_from_the_agents_own_environment_before_anything_else_runs():
    source = (A.RUNNER_DIR / "agent.py").read_text()
    assert 'os.environ.pop(ENROLLMENT_SECRET_ENV, "")' in source
    main = source[source.index("def main("):]
    assert main.index("os.environ.pop(ENROLLMENT_SECRET_ENV") < main.index("load_config(")


def test_no_line_of_the_agent_interpolates_the_secret_or_a_token():
    """B2 section 11, test 5 (the agent half): no secret or token in a log line. The streams are checked above;
    this reads every line that could write one. The one line that writes the token is the environment file's."""
    source = (A.RUNNER_DIR / "agent.py").read_text()
    for number, line in enumerate(source.splitlines(), 1):
        assert not re.search(r"\{(secret|grant|issued)\b", line), (number, line)
        if re.search(r"\{token\b", line):
            assert "{token_env}={token}" in line, (number, line)
    enrollment = source[source.index("class EnrollmentRefused"):source.index("def build_parser")]
    assert "argv" not in enrollment, "the secret never travels in an argument vector"
