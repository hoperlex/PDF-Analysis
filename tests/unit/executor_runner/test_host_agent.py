"""`HOSTS-AGENT-01`: the host agent as a whole -- recount, report, claim, refuse, extend, slots, answer.

The agent runs in this process (``HostAgent``, ``HostHealthReporter`` and the probe thread) against a fake stand that
speaks the host protocol, stand-in CLIs whose behaviour the test changes while the agent runs, and a fake API server.
Intervals are fractions of a second so that the 60-second heartbeat and the six-hour recount can be seen to happen.
Nothing leaves the machine and no model is called.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

import pytest

for _name, _file in (("executor_runner_support", "_support.py"), ("executor_runner_agent_support", "_agent_support.py"),
                     ("executor_runner_host_support", "_host_support.py")):
    if _name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(_name, Path(__file__).with_name(_file))
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_name] = _module
        _spec.loader.exec_module(_module)
S = sys.modules["executor_runner_support"]
A = sys.modules["executor_runner_agent_support"]
H = sys.modules["executor_runner_host_support"]
agent = A.load_module("exec_host_agent_under_test", A.RUNNER_DIR / "agent.py")
detect = sys.modules["detect"]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes and shell stand-ins")

KEY_A = "sk-ant-api03-" + "A" * 40
KEY_A2 = "sk-ant-api03-" + "Z" * 40
KEY_O = "sk-proj-" + "B" * 40
PROVIDER_ENV = {"ANTHROPIC_API_KEY": KEY_A, "OPENAI_API_KEY": KEY_O, "PDF_ANALYSIS_RUNNER_TOKEN": "amr_" + "G" * 52}


class Sink:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self._lock = threading.Lock()

    def write(self, text: str) -> int:
        with self._lock:
            self.parts.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    @property
    def text(self) -> str:
        with self._lock:
            return "".join(self.parts)


class Host:
    """One host agent under test, stopped by the fixture."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stand: "H.HostStand", *, claude: dict | None = None,
                 codex: dict | None = None, keys: str | None = None, keys_mode: int = 0o600, api: "H.FakeApi | None" = None,
                 host_extra: str = "", slots: dict | None = None, window: float = 120.0, failed_retry: float = 900.0,
                 probe_interval: float = 21600.0, accept_images: bool = False) -> None:
        self.tmp, self.stand = tmp_path, stand
        self.claude_dir, self.codex_dir, self.home = tmp_path / "claude-bin", tmp_path / "codex-bin", tmp_path / "home"
        self.home.mkdir()
        self.bin_dir = tmp_path / "bin"
        self.bin_dir.mkdir()
        # one directory for both CLIs (the agent searches a list of directories), each stand-in logs beside itself
        for directory, name, settings in ((self.claude_dir, "claude", claude), (self.codex_dir, "codex", codex)):
            if settings is not None:
                H.make_fake(directory, name, **settings)
        monkeypatch.setenv("HOME", str(self.home))
        monkeypatch.setenv(detect.DIRS_ENV, ":".join(str(d) for d in (self.claude_dir, self.codex_dir)))
        self.keys = tmp_path / "keys.env"
        if keys is not None:
            self.keys.write_text(keys)
            self.keys.chmod(keys_mode)
        lines = ["[runner]", f'origin = "{stand.origin}"', "wait_seconds = 1", "allow_insecure_http = true",
                 "backoff_min_seconds = 0.2", "backoff_max_seconds = 1.0", "extend_floor_seconds = 0.3", "drain_seconds = 2",
                 "[executor]", 'mode = "host"', "[host]", f'key_file = "{self.keys}"', "detect_seconds = 0.2",
                 "report_seconds = 0.4", f"probe_interval_seconds = {probe_interval}", f"failed_retry_seconds = {failed_retry}",
                 "probe_timeout_seconds = 20", f"activity_window_seconds = {window}",
                 f"accept_images = {'true' if accept_images else 'false'}", host_extra]
        if slots:
            lines += ["[slots]"] + [f"{provider} = {count}" for provider, count in slots.items()]
        if api is not None:
            lines += ["[api]", f'anthropic_base_url = "{api.url}"', f'openai_base_url = "{api.url}"',
                      f'openrouter_base_url = "{api.url}"']
        self.config_path = tmp_path / "agent.toml"
        self.config_path.write_text("\n".join(lines) + "\n")
        self.cfg = agent.load_config(str(self.config_path))
        self.sink = Sink()
        self.client = agent.RunnerClient(self.cfg.origin, S.TOKEN, allow_insecure_http=True)
        self.agent = agent.HostAgent(self.cfg, self.client, self.sink)
        self.runtime = self.agent.runtime
        self.reporter = agent.HostHealthReporter(self.cfg, self.client, self.agent.instance_id, self.agent.log,
                                                 self.agent.stop, self.runtime, version="0.9.0")
        self.exit_code: list[int] = []
        self.thread = threading.Thread(target=lambda: self.exit_code.append(self.agent.run(None)), daemon=True)

    def start(self) -> "Host":
        self.reporter.start()
        self.runtime.start_probes()
        self.thread.start()
        return self

    def stop(self) -> None:
        self.agent.stop.set()
        self.runtime.urgent.set()
        self.runtime.wake.set()
        self.thread.join(timeout=15)

    @property
    def log(self) -> str:
        return self.sink.text

    def verified(self, report: dict, provider: str = "claude_code", model: str | None = None) -> bool:
        """Whether the model (by default every catalogue model of the provider) is reported verified: a test that
        sends a task for a model first waits until the report says so, or the task is rightly refused."""
        wanted = [model] if model else [c["model_id"] for c in self.stand.catalogue if c["provider"] == provider]
        return all(H.model_state(report, provider, m) == "verified" for m in wanted)


@pytest.fixture
def make_host(tmp_path, monkeypatch):
    made: list[Host] = []
    stands: list = []

    def factory(*, catalogue=None, send_catalogue=True, **kwargs) -> Host:
        stand = H.HostStand(catalogue, lease=kwargs.pop("lease", 3))
        stand.send_catalogue = send_catalogue
        stand.__enter__()
        stands.append(stand)
        for name, value in PROVIDER_ENV.items():
            monkeypatch.setenv(name, value)  # the agent's own environment holds keys: no child may see them
        host = Host(tmp_path, monkeypatch, stand, **kwargs)
        made.append(host)
        return host.start()

    yield factory
    for host in made:
        host.stop()
    for stand in stands:
        stand.__exit__(None, None, None)


# ----------------------------------------------------------------------------------- report and recount


def test_the_first_report_has_no_models_the_stand_sends_the_catalogue_and_the_agent_then_reports_what_it_verified(make_host):
    host = make_host(claude={}, codex={})
    first = host.stand.wait_report(lambda r: True)
    assert [p["provider"] for p in first["providers"]] == ["claude_code", "codex"]
    assert all(p["models"] == [] for p in first["providers"]), "no catalogue yet: nothing to check"
    assert set(first) == {"agent_version", "clis", "concurrency", "execution_profile", "features", "runner_instance_id",
                          "providers", "slots"}
    assert first["execution_profile"] == "command" and first["features"] == [] and first["agent_version"] == "0.9.0"
    ready = host.stand.wait_report(lambda r: host.verified(r) and H.model_state(r, "codex", "gpt-6.1-sol") == "verified")
    claude = H.provider_entry(ready, "claude_code")
    assert (claude["access"], claude["auth_state"], claude["cli_version"]) == ("subscription", "valid", "2.1.310")
    assert "cli_path" not in claude and str(host.tmp) not in json.dumps(ready), "no path leaves the host unless it is asked for"
    assert [m["model_id"] for m in claude["models"]] == ["claude-opus-5-5", "claude-sonnet-5-5"]
    assert all(m["state"] == "verified" and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", m["checked_at"]) and "failure_code" not in m
               for m in claude["models"])
    assert ready["slots"] == {"claude_code": 1, "codex": 1} and ready["concurrency"] == 2
    assert ready["clis"] == [{"cli": "claude", "installed": True, "version": "2.1.310", "auth_state": "valid"},
                             {"cli": "codex", "installed": True, "version": "0.46.0", "auth_state": "valid"}]
    # each model was checked once, at the cheapest effort it has
    assert sorted(line.split()[line.split().index("--effort") + 1] for line in H.model_calls(host.claude_dir)) == ["low", "medium"]
    assert len(H.model_calls(host.codex_dir)) == 2
    # the report is the host's pulse: it goes out with every cycle whether or not anything changed
    assert len(host.stand.of_kind("health")) >= 3


def test_the_catalogue_efforts_and_the_enabled_switch_are_taken_from_the_stands_answer(make_host):
    host = make_host(claude={})
    host.stand.enabled = False
    host.stand.wait_report(lambda r: host.verified(r))
    assert host.runtime.enabled is False and "«Использовать» is now off" in host.log
    host.stand.add_task(host.stand.host_task("ext_T1", "claude_code", "claude-sonnet-5-5", effort="low"))
    host.stand.wait_for("answer")
    assert host.runtime.slots.used("claude_code") == 0
    assert "claims go on for runs already bound" in host.log, "a host that is switched off still finishes the runs it holds"
    host.stand.enabled = True
    assert H.eventually(lambda: host.runtime.enabled is True)


def test_nothing_changing_means_no_snapshot_is_rebuilt_no_model_is_called_and_the_heartbeat_repeats_the_same_body(make_host):
    host = make_host(claude={}, codex={})
    host.stand.wait_report(lambda r: host.verified(r) and H.model_state(r, "codex", "gpt-6-astra") == "verified")
    time.sleep(0.5)
    builds, calls = host.runtime.book.builds, len(H.model_calls(host.claude_dir)) + len(H.model_calls(host.codex_dir))
    probe_lines = host.log.count("probe:")
    before = len(host.stand.health_reports())
    assert H.eventually(lambda: len(host.stand.health_reports()) >= before + 6, 20)
    steady = host.stand.health_reports()[before:before + 6]
    assert all(body == steady[0] for body in steady), "a heartbeat is the same snapshot again"
    assert host.runtime.book.builds == builds
    assert len(H.model_calls(host.claude_dir)) + len(H.model_calls(host.codex_dir)) == calls
    assert host.log.count("probe:") == probe_lines, "no further recount"


def test_a_login_that_goes_away_is_reported_with_no_model_call_and_a_login_that_returns_is_checked_again(make_host):
    host = make_host(claude={})
    host.stand.wait_report(lambda r: host.verified(r))
    calls = len(H.model_calls(host.claude_dir))
    H.configure(host.claude_dir, "claude", auth="out")
    gone = host.stand.wait_report(lambda r: (H.provider_entry(r, "claude_code") or {}).get("auth_state") == "login_required")
    assert H.model_state(gone, "claude_code", "claude-opus-5-5") == "not_verified" and gone["clis"][0]["auth_state"] == "login_required"
    time.sleep(0.8)
    assert len(H.model_calls(host.claude_dir)) == calls, "nothing is called while the CLI is not signed in"
    assert not host.runtime.book.is_verified("claude_code", "subscription", "claude-opus-5-5")
    H.configure(host.claude_dir, "claude", auth="subscription")
    host.stand.wait_report(lambda r: host.verified(r), fresh=True)
    assert len(H.model_calls(host.claude_dir)) == calls + 2


def test_a_changed_login_method_a_new_cli_version_and_a_new_catalogue_each_send_the_models_through_a_minimal_call_again(make_host):
    host = make_host(claude={})
    host.stand.wait_report(lambda r: host.verified(r))
    calls = len(H.model_calls(host.claude_dir))
    H.configure(host.claude_dir, "claude", version="2.1.311")
    host.stand.wait_report(lambda r: (H.provider_entry(r, "claude_code") or {}).get("cli_version") == "2.1.311" and host.verified(r))
    assert len(H.model_calls(host.claude_dir)) == calls + 2
    H.configure(host.claude_dir, "claude", auth="api")
    api = host.stand.wait_report(lambda r: (H.provider_entry(r, "claude_code") or {}).get("access") == "api" and host.verified(r))
    assert api["slots"]["claude_code"] == 2, "an API login gets two slots"
    assert len(H.model_calls(host.claude_dir)) == calls + 4
    # a model added to the catalogue is checked; the ones already verified are not
    host.stand.catalogue = host.stand.catalogue + [{"provider": "claude_code", "model_id": "claude-haiku-5-5", "efforts": ["low"], "accepted_reported": []}]
    host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-haiku-5-5") == "verified", fresh=True)
    assert len(H.model_calls(host.claude_dir)) == calls + 5


def test_a_model_the_cli_does_not_have_is_failed_with_a_code_and_the_others_are_served(make_host):
    host = make_host(claude={"models": ["claude-sonnet-5-5"]})
    report = host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-opus-5-5") == "failed"
                                    and H.model_state(r, "claude_code", "claude-sonnet-5-5") == "verified")
    opus = [m for m in H.provider_entry(report, "claude_code")["models"] if m["model_id"] == "claude-opus-5-5"][0]
    assert opus["failure_code"] == "model_not_found"


# ------------------------------------------------------------------------------------------- the claim


def test_a_task_is_answered_with_the_provider_access_reported_model_and_usage_the_stand_checks(make_host):
    host = make_host(claude={"reported": "claude-opus-5-5-20261001"}, codex={})
    host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-opus-5-5") == "verified")
    host.stand.add_task(host.stand.host_task("ext_T1", "claude_code", "claude-opus-5-5", effort="high"))
    [answer] = host.stand.wait_for("answer")
    assert answer["task_id"] == "ext_T1"
    assert answer["body"] == {
        "output_text": '{"findings":[]}', "model": "claude-opus-5-5", "provider": "claude_code", "access": "subscription",
        "reported_model": "claude-opus-5-5-20261001", "usage": {"input_tokens": 24, "output_tokens": 3}}
    last = H.model_calls(host.claude_dir)[-1].split()
    assert last[last.index("--effort") + 1] == "high" and last[last.index("--model") + 1] == "claude-opus-5-5"
    claim = host.stand.of_kind("claim")[0]["body"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{8,64}", claim["runner_instance_id"]) and claim["wait_seconds"] == 1
    assert host.stand.of_kind("fail") == []


def test_codex_tasks_run_with_their_effort_and_report_the_requested_model(make_host):
    host = make_host(codex={})
    host.stand.wait_report(lambda r: H.model_state(r, "codex", "gpt-6-astra") == "verified")
    host.stand.add_task(host.stand.host_task("ext_T2", "codex", "gpt-6-astra", effort="high"))
    [answer] = host.stand.wait_for("answer")
    assert answer["body"]["reported_model"] == "gpt-6-astra" and answer["body"]["provider"] == "codex"
    assert answer["body"]["usage"] == {"input_tokens": 21, "output_tokens": 4}
    assert (host.codex_dir / "last_effort.txt").read_text() == 'model_reasoning_effort="high"'


@pytest.mark.parametrize("task_args,code", [
    ({"provider": "claude_code", "model_id": "claude-haiku-5-5", "effort": "low"}, "model_not_available"),  # not in the catalogue
    ({"provider": "claude_code", "model_id": "claude-opus-5-5", "access": "api"}, "model_not_available"),  # verified for the other access
    ({"provider": "anthropic_api", "model_id": "claude-opus-5-5", "access": "api"}, "model_not_available"),  # no key here
    ({"provider": "codex", "model_id": "gpt-6.1-sol"}, "model_not_available"),  # no codex here
    ({"provider": "claude_code", "model_id": "claude-opus-5-5", "effort": "low"}, "effort_not_allowed"),  # not an effort of the model
])
def test_a_task_for_a_model_this_host_does_not_report_as_verified_is_refused_before_anything_runs(make_host, task_args, code):
    host = make_host(claude={})
    host.stand.wait_report(lambda r: host.verified(r))
    calls = len(H.model_calls(host.claude_dir))
    host.stand.add_task(host.stand.host_task("ext_R1", **{"access": "subscription", "effort": "medium", **task_args}))
    [failed] = host.stand.wait_for("fail")
    assert failed["body"]["reason"].startswith(code + ":"), failed["body"]
    assert host.stand.of_kind("answer") == [] and len(H.model_calls(host.claude_dir)) == calls, "no CLI was called"


def test_a_model_that_failed_its_check_is_refused_and_a_model_that_was_never_checked_too(make_host):
    host = make_host(claude={"models": ["claude-sonnet-5-5"]})
    host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-opus-5-5") == "failed")
    host.stand.add_task(host.stand.host_task("ext_R2", "claude_code", "claude-opus-5-5"))
    [failed] = host.stand.wait_for("fail")
    assert failed["body"]["reason"].startswith("model_not_available:")


def test_a_task_that_carries_no_host_members_is_failed_as_incomplete_not_guessed_at(make_host):
    host = make_host(claude={})
    host.stand.wait_report(lambda r: host.verified(r))
    task = S.make_task("ext_R3", "claude-opus-5-5")
    host.stand.add_task(task)
    [failed] = host.stand.wait_for("fail")
    assert failed["body"]["reason"].startswith("host_task_incomplete:")


def test_nothing_is_claimed_until_a_model_is_verified(make_host):
    host = make_host(claude={"models": []})  # every probe fails
    host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-opus-5-5") == "failed")
    host.stand.add_task(host.stand.host_task("ext_N1", "claude_code", "claude-opus-5-5"))
    time.sleep(1.5)
    assert host.stand.of_kind("claim") == [] and host.stand.of_kind("fail") == [], "a host with nothing verified does not take work"


def test_a_stand_that_sends_no_catalogue_gets_no_model_checked_and_no_claim(make_host):
    host = make_host(claude={}, send_catalogue=False)
    time.sleep(1.2)
    assert H.model_calls(host.claude_dir) == [] and host.stand.of_kind("claim") == []
    assert "carries no catalogue" in host.log
    host.stand.send_catalogue = True
    host.stand.wait_report(lambda r: host.verified(r))


def test_an_image_task_is_refused_when_the_host_does_not_take_images(make_host):
    host = make_host(claude={}, codex={})
    host.stand.wait_report(lambda r: H.model_state(r, "codex", "gpt-6-sol") == "verified" or H.model_state(r, "codex", "gpt-6.1-sol") == "verified")
    descriptor, _raw = S.make_image("a")
    task = host.stand.host_task("ext_I1", "codex", "gpt-6.1-sol")
    task["images"] = [descriptor]
    calls = len(H.model_calls(host.codex_dir))
    host.stand.add_task(task)
    [failed] = host.stand.wait_for("fail")
    assert failed["body"]["reason"] == "image_input_unsupported" and len(H.model_calls(host.codex_dir)) == calls
    assert host.stand.of_kind("claim")[0]["body"].get("max_images") is None, "a host that takes no image declares one"


# -------------------------------------------------------------------------- the claim is extended on output


def test_the_claim_is_extended_while_the_call_produces_output(make_host):
    host = make_host(claude={}, window=1.0, lease=2)
    host.stand.wait_report(lambda r: host.verified(r))
    H.configure(host.claude_dir, "claude", behavior="drip", drip_seconds=3.5)
    host.stand.add_task(host.stand.host_task("ext_E1", "claude_code", "claude-sonnet-5-5", effort="low", lease=2))
    host.stand.wait_for("answer", timeout=30)
    extends = host.stand.of_kind("extend")
    assert len(extends) >= 3, "output flowed for 3.5 s, past the 1 s window: the claim was extended all along"
    assert host.stand.of_kind("fail") == []


def test_a_call_with_no_output_lets_the_claim_lapse_is_stopped_and_nothing_is_submitted(make_host):
    host = make_host(claude={}, window=1.0, lease=2)
    host.stand.wait_report(lambda r: host.verified(r))
    H.configure(host.claude_dir, "claude", behavior="hang")
    host.stand.add_task(host.stand.host_task("ext_E2", "claude_code", "claude-sonnet-5-5", effort="low", lease=2))
    assert H.eventually(lambda: "claimed ext_E2" in host.log, 15)
    assert H.eventually(lambda: "no output from the call" in host.log, 15)
    settled = len(host.stand.of_kind("extend"))
    assert settled <= 4, "extensions stop with the output"
    time.sleep(2.0)
    assert len(host.stand.of_kind("extend")) == settled, "a hung CLI is not kept alive"
    assert host.stand.of_kind("answer") == [] and host.stand.of_kind("fail") == [], "the claim is left to lapse"
    [pid] = [int(p.name) for p in (host.claude_dir / "running").iterdir()]
    assert H.eventually(lambda: not _alive(pid), 5), "the hung CLI was killed"
    assert host.runtime.slots.used("claude_code") == 0, "and its slot is free again"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        with open(f"/proc/{pid}/stat") as handle:
            return handle.read().split()[2] != "Z"
    except OSError:
        return False


# ---------------------------------------------------------------------------- access failures take it out


def test_a_quota_error_on_a_real_call_fails_the_task_takes_the_model_out_of_service_and_a_later_check_returns_it(make_host):
    host = make_host(claude={}, failed_retry=1.0)
    host.stand.wait_report(lambda r: host.verified(r))
    H.configure(host.claude_dir, "claude", behavior="quota")
    host.stand.add_task(host.stand.host_task("ext_Q1", "claude_code", "claude-opus-5-5"))
    [failed] = host.stand.wait_for("fail")
    assert failed["body"]["reason"].startswith("quota_exceeded:") and "1760000000" not in failed["body"]["reason"]
    report = host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-opus-5-5") == "failed")
    [opus] = [m for m in H.provider_entry(report, "claude_code")["models"] if m["model_id"] == "claude-opus-5-5"]
    assert opus["failure_code"] == "quota_exceeded"
    assert H.model_state(report, "claude_code", "claude-sonnet-5-5") == "verified", "only the model that failed leaves service"
    H.configure(host.claude_dir, "claude", behavior="ok")
    host.stand.wait_report(lambda r: H.model_state(r, "claude_code", "claude-opus-5-5") == "verified", fresh=True)
    host.stand.add_task(host.stand.host_task("ext_Q2", "claude_code", "claude-opus-5-5"))
    host.stand.wait_for("answer")


def test_a_task_failure_that_is_not_about_access_leaves_the_model_in_service(make_host):
    host = make_host(claude={})
    host.stand.wait_report(lambda r: host.verified(r))
    H.configure(host.claude_dir, "claude", reported="claude-sonnet-5-5")  # the CLI answers as another model
    host.stand.add_task(host.stand.host_task("ext_Q3", "claude_code", "claude-opus-5-5"))
    [failed] = host.stand.wait_for("fail")
    assert failed["body"]["reason"].startswith("claude_model_mismatch:")
    time.sleep(0.8)
    assert host.runtime.book.is_verified("claude_code", "subscription", "claude-opus-5-5")


# ------------------------------------------------------------------------------------------------ slots


def test_within_a_provider_never_more_calls_than_its_slots_while_another_provider_runs_beside_it(make_host):
    host = make_host(claude={"behavior": "slow", "delay": 0.8}, codex={"behavior": "slow", "delay": 0.8}, lease=4)
    host.stand.wait_report(lambda r: host.verified(r) and H.model_state(r, "codex", "gpt-6-astra") == "verified")
    for number in range(3):
        host.stand.add_task(host.stand.host_task(f"ext_S{number}", "claude_code", "claude-sonnet-5-5", effort="low", lease=4))
    host.stand.add_task(host.stand.host_task("ext_SC", "codex", "gpt-6-astra", effort="low", lease=4))
    host.stand.wait_for("answer", 4, timeout=40)
    assert H.peak(host.claude_dir) == 1, "one subscription, one call at a time"
    assert H.peak(host.codex_dir) == 1
    assert host.stand.of_kind("fail") == []


def test_an_api_provider_runs_two_calls_at_once_and_no_more(make_host):
    with H.FakeApi() as api:
        host = make_host(catalogue=[c for c in H.CATALOGUE if c["provider"] == "anthropic_api"], keys=f"ANTHROPIC_API_KEY={KEY_A}\n",
                         api=api, lease=4)
        host.stand.wait_report(lambda r: H.model_state(r, "anthropic_api", "claude-opus-5-5") == "verified")
        api.behavior = "keepalive"
        api.keepalive_seconds = 0.8
        for number in range(5):
            host.stand.add_task(host.stand.host_task(f"ext_A{number}", "anthropic_api", "claude-opus-5-5", access="api", lease=4))
        host.stand.wait_for("answer", 5, timeout=40)
        assert api.peak_inflight == 2


def test_the_slots_can_be_set_in_the_config(make_host):
    host = make_host(claude={}, codex={}, slots={"claude_code": 3})
    report = host.stand.wait_report(lambda r: host.verified(r))
    assert report["slots"] == {"claude_code": 3, "codex": 1} and report["concurrency"] == 4


# ---------------------------------------------------------------------------------- API providers and keys


def test_an_api_key_in_the_key_file_makes_a_provider_that_is_checked_called_and_never_reported_or_logged(make_host):
    with H.FakeApi() as api:
        host = make_host(claude={}, keys=f"ANTHROPIC_API_KEY={KEY_A}\nOPENAI_API_KEY={KEY_O}\n", api=api)
        report = host.stand.wait_report(lambda r: H.model_state(r, "anthropic_api", "claude-opus-5-5") == "verified"
                                        and H.model_state(r, "openai_api", "gpt-6.1-sol") == "verified" and host.verified(r))
        providers = {p["provider"]: p for p in report["providers"]}
        assert [p["provider"] for p in report["providers"]] == ["claude_code", "anthropic_api", "openai_api"]
        assert providers["anthropic_api"]["access"] == "api" and providers["anthropic_api"]["auth_state"] == "valid"
        assert "cli_version" not in providers["anthropic_api"] and report["slots"]["anthropic_api"] == 2
        assert "openrouter_api" not in providers, "no key, no provider"
        host.stand.add_task(host.stand.host_task("ext_K1", "anthropic_api", "claude-opus-5-5", access="api", effort="high"))
        [answer] = host.stand.wait_for("answer")
        assert answer["body"]["provider"] == "anthropic_api" and answer["body"]["access"] == "api"
        assert answer["body"]["reported_model"] == "claude-opus-5-5" and answer["body"]["usage"] == {"input_tokens": 30, "output_tokens": 9}
        assert api.of("/v1/messages")[-1]["headers"]["x-api-key"] == KEY_A
        assert api.of("/v1/messages")[-1]["body"]["output_config"] == {"effort": "high"}
        assert api.of("/v1/messages")[-1]["body"]["max_tokens"] == 128_000, "Anthropic requires max_tokens: the model's maximum"
        everything = json.dumps([r["body"] for r in host.stand.requests]) + host.log
        for secret in (KEY_A, KEY_O, "sk-ant-", "sk-proj-"):
            assert secret not in everything, "a key never travels to the stand and never reaches a log"
        # the agent's own environment holds the keys (the fixture put them there); the child CLIs never saw them
        host.stand.add_task(host.stand.host_task("ext_K2", "claude_code", "claude-sonnet-5-5", effort="low"))
        host.stand.wait_for("answer", 2)
        seen = (host.claude_dir / "last_env_values.json").read_text()
        for name, value in PROVIDER_ENV.items():
            assert name not in seen and value not in seen


def test_no_answer_cap_reaches_a_model_even_when_an_older_stand_or_the_agents_own_environment_names_one(make_host, monkeypatch):
    """`LIMITS-01` (`R-153n`): the agent sends no answer cap on any analysis call.  The task of a stand older than contract 1.49.0 still carries
    ``max_output_tokens`` (``legacy_cap``) and the agent's environment names ``CLAUDE_CODE_MAX_OUTPUT_TOKENS``; neither reaches a model.  Anthropic
    requires ``max_tokens``, so it gets the model's maximum (128000); OpenAI gets none.  The availability probe keeps its own 4096 on an API call."""
    monkeypatch.setenv("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "999")
    with H.FakeApi() as api:
        host = make_host(claude={}, keys=f"ANTHROPIC_API_KEY={KEY_A}\nOPENAI_API_KEY={KEY_O}\n", api=api)
        host.stand.wait_report(lambda r: H.model_state(r, "anthropic_api", "claude-opus-5-5") == "verified"
                               and H.model_state(r, "openai_api", "gpt-6.1-sol") == "verified" and host.verified(r))
        assert api.of("/v1/messages")[0]["body"]["max_tokens"] == 4096 and api.of("/v1/responses")[0]["body"]["max_output_tokens"] == 4096, \
            "the probe is not an analysis answer: its own ceiling stays"
        probes = {path: len(api.of(path)) for path in ("/v1/messages", "/v1/responses")}
        host.stand.add_task(host.stand.host_task("ext_C1", "claude_code", "claude-sonnet-5-5", effort="low", legacy_cap=True))
        host.stand.add_task(host.stand.host_task("ext_C2", "anthropic_api", "claude-opus-5-5", access="api", effort="high", legacy_cap=True))
        host.stand.add_task(host.stand.host_task("ext_C3", "openai_api", "gpt-6.1-sol", access="api", effort="high", legacy_cap=True))
        host.stand.wait_for("answer", 3, timeout=40)
        seen = json.loads((host.claude_dir / "last_env_values.json").read_text())
        assert "CLAUDE_CODE_MAX_OUTPUT_TOKENS" not in seen, "the CLI is run without an answer ceiling, whatever the agent's own environment says"
        messages, responses = api.of("/v1/messages")[probes["/v1/messages"]:], api.of("/v1/responses")[probes["/v1/responses"]:]
        assert [m["body"]["max_tokens"] for m in messages] == [128_000], "Anthropic's required parameter: the model's maximum, not the task's 4000"
        assert len(responses) == 1 and "max_output_tokens" not in responses[0]["body"] and "max_tokens" not in responses[0]["body"]


def test_a_rotated_key_is_noticed_checked_again_and_used_at_once(make_host):
    with H.FakeApi() as api:
        host = make_host(catalogue=[c for c in H.CATALOGUE if c["provider"] == "anthropic_api"], keys=f"ANTHROPIC_API_KEY={KEY_A}\n", api=api)
        host.stand.wait_report(lambda r: H.model_state(r, "anthropic_api", "claude-opus-5-5") == "verified")
        probes = len(api.of("/v1/messages"))
        host.keys.write_text(f"ANTHROPIC_API_KEY={KEY_A2}\n")
        assert H.eventually(lambda: len(api.of("/v1/messages")) > probes, 15)
        assert api.of("/v1/messages")[-1]["headers"]["x-api-key"] == KEY_A2
        host.stand.wait_report(lambda r: H.model_state(r, "anthropic_api", "claude-opus-5-5") == "verified")


def test_a_key_the_provider_refuses_is_reported_login_required_with_a_failure_code(make_host):
    with H.FakeApi() as api:
        api.behavior = "401"
        host = make_host(catalogue=[c for c in H.CATALOGUE if c["provider"] == "openai_api"], keys=f"OPENAI_API_KEY={KEY_O}\n", api=api)
        report = host.stand.wait_report(lambda r: H.model_state(r, "openai_api", "gpt-6.1-sol") == "failed")
        entry = H.provider_entry(report, "openai_api")
        assert entry["auth_state"] == "login_required" and entry["models"][0]["failure_code"] == "auth_failed"
        assert KEY_O not in host.log


def test_a_key_file_that_is_not_mode_0600_is_ignored_with_the_reason_in_the_log_and_read_once_it_is_fixed(make_host):
    with H.FakeApi() as api:
        host = make_host(catalogue=[c for c in H.CATALOGUE if c["provider"] == "anthropic_api"], keys=f"ANTHROPIC_API_KEY={KEY_A}\n",
                         keys_mode=0o644, api=api)
        report = host.stand.wait_report(lambda r: True)
        time.sleep(0.8)
        assert H.provider_entry(host.stand.health_reports()[-1], "anthropic_api") is None and report["providers"] == []
        assert "mode_is_not_0600" in host.log and api.requests == [] and KEY_A not in host.log
        host.keys.chmod(0o600)
        host.stand.wait_report(lambda r: H.model_state(r, "anthropic_api", "claude-opus-5-5") == "verified")


# -------------------------------------------------------------------------------------- the single-model path


def test_a_single_model_config_still_loads_and_still_means_a_connection_bound_agent(tmp_path):
    path = A.RUNNER_DIR / "agent.example.toml"
    cfg = agent.load_config(str(path))
    assert cfg.mode == "command" and cfg.host is None and cfg.declared_model == "claude-sonnet-5"
    report = agent.build_health_report(cfg, "instance-xyz-1", [], "0.9.0")
    assert set(report) == {"agent_version", "clis", "concurrency", "execution_profile", "features", "runner_instance_id"}
    assert report["execution_profile"] == "command"
    other = tmp_path / "host-in-command.toml"
    other.write_text(path.read_text().replace("[runner]", "[host]\nkey_file = \"/x/y\"\n\n[runner]", 1))
    with pytest.raises(agent.ConfigError, match="belong to"):
        agent.load_config(str(other))


def test_a_host_config_needs_no_model_and_refuses_a_bad_section(tmp_path):
    good = tmp_path / "good.toml"
    good.write_text('[runner]\norigin = "https://stand.example.org"\n[executor]\nmode = "host"\n')
    cfg = agent.load_config(str(good))
    assert cfg.mode == "host" and cfg.declared_model == "" and cfg.host.key_file == "/etc/pdf-analysis-agent/keys.env"
    assert cfg.accept_images is False and cfg.declared_max_images == 1
    bad = tmp_path / "bad.toml"
    bad.write_text('[runner]\norigin = "https://stand.example.org"\n[executor]\nmode = "host"\n[slots]\nclaude_code = 0\n')
    with pytest.raises(agent.ConfigError, match="1..8"):
        agent.load_config(str(bad))
    secret = tmp_path / "secret.toml"
    secret.write_text('[runner]\norigin = "https://stand.example.org"\n[executor]\nmode = "host"\n[host]\napi_key = "sk-x"\n')
    with pytest.raises(agent.ConfigError, match="looks like a secret"):
        agent.load_config(str(secret))


def test_enrollment_of_a_host_stores_only_the_token_and_names_the_host(tmp_path, monkeypatch, capsys):
    with H.HostStand() as stand:
        config = tmp_path / "agent.toml"
        config.write_text(f'[runner]\norigin = "{stand.origin}"\nallow_insecure_http = true\n[executor]\nmode = "host"\n')
        env_file = tmp_path / "agent.env"
        env_file.write_text("")
        env_file.chmod(0o600)
        monkeypatch.setenv("AUDITMANAGER_ENROLLMENT_SECRET", H.HOST_SECRET)
        assert agent.main(["--config", str(config), "--env-file", str(env_file), "--enroll-only"]) == 0
        out = capsys.readouterr()
        assert f"enrolled: host {H.HOST_ID}" in out.out and H.HOST_SECRET not in out.out + out.err
        body = [r for r in stand.requests if r["kind"] == "enroll"][0]["body"]
    assert set(body) == {"runner_instance_id", "agent_version"}, "no model is sent: an enrollment is of a host"
    stored = env_file.read_text()
    assert stored.startswith("PDF_ANALYSIS_RUNNER_TOKEN=amr_") and H.HOST_SECRET not in stored and "AUDITMANAGER" not in stored
    assert "AUDITMANAGER_ENROLLMENT_SECRET" not in os.environ
