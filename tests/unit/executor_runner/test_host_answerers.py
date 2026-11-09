"""`HOSTS-AGENT-01`: the answerers of host mode, with stand-in CLIs and fake API servers (no model is called).

* ``claude_answer.run_host`` and ``codex_answer.run_host`` serve any catalogue model, pass the effort, return the model
  the CLI itself reported (exactly), classify an access failure and keep every key out of the child's environment;
* ``api_answer.call`` speaks the streamed Anthropic Messages, OpenAI Responses and OpenRouter chat completions, sends the
  model, effort and ``max_output_tokens``, returns the reported model and the usage, times out on silence and on the
  total, and never lets the key reach an exception, a message or a return value.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

_NAME = "executor_runner_host_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_host_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
H = sys.modules[_NAME]


def _load(name: str, file: str):
    sys.path.insert(0, str(H.RUNNER_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, H.RUNNER_DIR / file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(H.RUNNER_DIR))
    return module


claude_answer = _load("pdfa_host_claude_answer", "claude_answer.py")
codex_answer = _load("pdfa_host_codex_answer", "codex_answer.py")
api_answer = _load("pdfa_host_api_answer", "api_answer.py")

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell stand-ins")

SECRETS = {"ANTHROPIC_API_KEY": "sk-ant-api03-" + "A" * 40, "OPENAI_API_KEY": "sk-proj-" + "B" * 40,
           "OPENROUTER_API_KEY": "sk-or-v1-" + "C" * 40, "CODEX_API_KEY": "cx-" + "D" * 30,
           "ANTHROPIC_AUTH_TOKEN": "tok-" + "E" * 30, "CLAUDE_CODE_OAUTH_TOKEN": "oat-" + "F" * 30,
           "PDF_ANALYSIS_RUNNER_TOKEN": "amr_" + "G" * 52, "AUDITMANAGER_ENROLLMENT_SECRET": "ame_x"}
TASK = {"system": "Return JSON.", "user_text": "A page of data.", "output_schema": H.TASK_SCHEMA}


class Activity:
    def __init__(self) -> None:
        self.touches = 0

    def touch(self) -> None:
        self.touches += 1


def _claude_task():
    return dict(TASK)


# ------------------------------------------------------------------------------------ Claude Code CLI


def test_claude_serves_a_catalogue_model_with_its_effort_and_returns_what_the_cli_reported(tmp_path):
    cli = H.make_fake(tmp_path, "claude")
    activity = Activity()
    reply = claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="medium", timeout=20, claude=str(cli),
                                   activity=activity, max_output_tokens=4000)
    assert reply == {"output_text": '{"findings":[]}', "reported_model": "claude-opus-5-5", "input_tokens": 24, "output_tokens": 3}
    call = H.model_calls(tmp_path)[0].split()
    assert call[call.index("--model") + 1] == "claude-opus-5-5" and call[call.index("--effort") + 1] == "medium"
    assert activity.touches >= 2, "the start and the stream's bytes are signs of life"
    env = json.loads((tmp_path / "last_env_values.json").read_text())
    assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "4000"
    assert "claude-opus-5-5" not in claude_answer.ALLOWED_MODELS, "the single-model command line keeps its own two models"


def test_the_exact_reported_string_is_returned_when_the_catalogue_accepts_it(tmp_path):
    cli = H.make_fake(tmp_path, "claude", reported="claude-opus-5-5-20261001")
    reply = claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="high", timeout=20, claude=str(cli),
                                   accepted=("claude-opus-5-5-20261001",))
    assert reply["reported_model"] == "claude-opus-5-5-20261001"


@pytest.mark.parametrize("settings", [{"reported": "claude-sonnet-5-5"}, {"reported": "claude-opus-5-5-20261001"}, {"extra_usage": True}])
def test_a_model_that_is_not_the_requested_one_nor_an_accepted_one_is_refused(tmp_path, settings):
    cli = H.make_fake(tmp_path, "claude", **settings)
    with pytest.raises(claude_answer.TaskError, match="^claude_model_mismatch$"):
        claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="medium", timeout=20, claude=str(cli))


@pytest.mark.parametrize("settings,kind", [
    ({"behavior": "quota"}, "quota_exceeded"),
    ({"behavior": "auth_error"}, "auth_failed"),
    ({"models": ["claude-sonnet-5-5"]}, "model_not_found"),
])
def test_a_failure_about_the_hosts_access_is_classified_and_carries_no_text_of_the_cli(tmp_path, settings, kind):
    cli = H.make_fake(tmp_path, "claude", **settings)
    with pytest.raises(claude_answer.AccessError) as caught:
        claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="medium", timeout=20, claude=str(cli))
    assert caught.value.kind == kind and str(caught.value) == "claude_" + kind
    assert "limit" not in str(caught.value) and "1760000000" not in str(caught.value)


def test_an_effort_outside_the_five_documented_levels_is_refused_before_any_call(tmp_path):
    cli = H.make_fake(tmp_path, "claude")
    with pytest.raises(claude_answer.TaskError, match="invalid_effort"):
        claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="ludicrous", timeout=20, claude=str(cli))
    assert H.model_calls(tmp_path) == []


def test_a_call_that_is_asked_to_stop_is_killed(tmp_path):
    cli = H.make_fake(tmp_path, "claude", behavior="hang")
    flag = {"stop": ""}
    threading.Timer(0.7, lambda: flag.update(stop="stalled")).start()
    started = time.monotonic()
    with pytest.raises(claude_answer.Interrupted, match="stalled"):
        claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="medium", timeout=60, claude=str(cli),
                               should_stop=lambda: flag["stop"])
    assert time.monotonic() - started < 10
    [pid] = [int(path.name) for path in (tmp_path / "running").iterdir()]
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # the CLI process is gone, not only abandoned


def test_the_single_model_command_line_is_unchanged(tmp_path):
    cli = H.make_fake(tmp_path, "claude", reported="claude-sonnet-5")
    with pytest.raises(claude_answer.TaskError, match="claude_model_mismatch"):
        claude_answer.answer({**TASK, "model": "claude-opus-5"}, claude=str(cli))
    assert claude_answer.ALLOWED_MODELS == ("claude-opus-5", "claude-sonnet-5") and claude_answer.DEFAULT_MODEL == "claude-opus-5"


# ------------------------------------------------------------------------------------------ Codex CLI


def test_codex_serves_a_catalogue_model_with_the_reasoning_effort_the_documented_way(tmp_path):
    cli = H.make_fake(tmp_path, "codex")
    activity = Activity()
    reply = codex_answer.run_host(dict(TASK), model="gpt-6.1-sol", effort="medium", timeout=20, codex=str(cli), activity=activity)
    assert reply == {"output_text": '{"findings": []}', "reported_model": "gpt-6.1-sol", "input_tokens": 21, "output_tokens": 4}
    call = H.model_calls(tmp_path)[0].split()
    assert call[call.index("--model") + 1] == "gpt-6.1-sol"
    assert (tmp_path / "last_effort.txt").read_text() == 'model_reasoning_effort="medium"'
    assert activity.touches >= 1
    assert codex_answer.CODEX_MODELS == ("gpt-6.1-sol", "gpt-6-sol", "gpt-6-astra") and codex_answer.MODEL == "gpt-6-sol"


def test_codex_without_an_effort_passes_none_and_a_bad_effort_never_starts_the_cli(tmp_path):
    cli = H.make_fake(tmp_path, "codex")
    codex_answer.run_host(dict(TASK), model="gpt-6-astra", effort=None, timeout=20, codex=str(cli))
    assert (tmp_path / "last_effort.txt").read_text() == ""
    calls = len(H.model_calls(tmp_path))
    with pytest.raises(codex_answer.TaskError, match="invalid_effort"):
        codex_answer.run_host(dict(TASK), model="gpt-6-astra", effort="medium; rm -rf", timeout=20, codex=str(cli))
    with pytest.raises(codex_answer.TaskError, match="invalid_model"):
        codex_answer.run_host(dict(TASK), model="gpt-6 --evil", effort="low", timeout=20, codex=str(cli))
    assert len(H.model_calls(tmp_path)) == calls


@pytest.mark.parametrize("settings,kind", [({"behavior": "quota"}, "quota_exceeded"), ({"models": ["gpt-6-sol"]}, "model_not_found")])
def test_codex_access_failures_are_classified_from_its_events(tmp_path, settings, kind):
    cli = H.make_fake(tmp_path, "codex", **settings)
    with pytest.raises(codex_answer.AccessError) as caught:
        codex_answer.run_host(dict(TASK), model="gpt-6.1-sol", effort="low", timeout=20, codex=str(cli))
    assert caught.value.kind == kind and str(caught.value) == "codex_" + kind


def test_codex_reports_the_requested_model_unless_an_event_names_another(tmp_path):
    cli = H.make_fake(tmp_path, "codex", event_model="gpt-6.1-sol")
    assert codex_answer.run_host(dict(TASK), model="gpt-6.1-sol", effort="low", timeout=20, codex=str(cli))["reported_model"] == "gpt-6.1-sol"
    H.configure(tmp_path, "codex", event_model="gpt-5-mini")
    with pytest.raises(codex_answer.TaskError, match="codex_model_mismatch"):
        codex_answer.run_host(dict(TASK), model="gpt-6.1-sol", effort="low", timeout=20, codex=str(cli))
    H.configure(tmp_path, "codex", event_model="gpt-6.1-sol-2026-10-01")
    reply = codex_answer.run_host(dict(TASK), model="gpt-6.1-sol", effort="low", timeout=20, codex=str(cli), accepted=("gpt-6.1-sol-2026-10-01",))
    assert reply["reported_model"] == "gpt-6.1-sol-2026-10-01"


def test_codex_stderr_counts_as_output_and_a_silent_cli_shows_none(tmp_path):
    cli = H.make_fake(tmp_path, "codex", behavior="drip", drip_seconds=1.2)
    activity = Activity()
    codex_answer.run_host(dict(TASK), model="gpt-6-sol", effort="low", timeout=20, codex=str(cli), activity=activity)
    assert activity.touches >= 4, "the progress lines on stderr are signs of life"
    H.configure(tmp_path, "codex", behavior="hang")
    quiet = Activity()
    flag = {"stop": ""}
    threading.Timer(1.0, lambda: flag.update(stop="stalled")).start()
    with pytest.raises(codex_answer.Interrupted):
        codex_answer.run_host(dict(TASK), model="gpt-6-sol", effort="low", timeout=60, codex=str(cli), activity=quiet,
                              should_stop=lambda: flag["stop"])
    assert quiet.touches <= 4, "a silent CLI touches the clock at its start and for the events it printed, no more"


def test_the_codex_single_model_command_keeps_its_model_and_takes_the_other_two_with_a_flag(tmp_path):
    cli = H.make_fake(tmp_path, "codex")
    assert codex_answer.answer({**TASK, "model": "gpt-6-sol"}, codex=str(cli)) == '{"findings": []}'
    assert H.model_calls(tmp_path)[0].split()[H.model_calls(tmp_path)[0].split().index("--model") + 1] == "gpt-6-sol"
    assert codex_answer.main(["--model", "gpt-7"]) == 2
    assert codex_answer.main(["--nope"]) == 2


# ------------------------------------------------------------------------------ keys never reach a child


def test_no_key_token_or_secret_reaches_a_child_cli_of_either_answerer(tmp_path, monkeypatch):
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("HOME", str(tmp_path))
    claude_dir, codex_dir = tmp_path / "c", tmp_path / "x"
    claude = H.make_fake(claude_dir, "claude")
    codex = H.make_fake(codex_dir, "codex")
    claude_answer.run_host(_claude_task(), model="claude-opus-5-5", effort="low", timeout=20, claude=str(claude))
    codex_answer.run_host(dict(TASK), model="gpt-6-sol", effort="low", timeout=20, codex=str(codex))
    for directory in (claude_dir, codex_dir):
        seen = (directory / "last_env_values.json").read_text()
        for name, value in SECRETS.items():
            assert name not in seen and value not in seen, (directory.name, name)
        assert json.loads(seen)["HOME"] == str(tmp_path), "the login location still reaches the CLI"


@pytest.mark.parametrize("module", ["claude", "codex"])
def test_the_allowlist_is_checked_again_behind_itself(module, monkeypatch):
    """A name added to the allowlist by mistake (or smuggled in by a changed constant) still cannot carry a secret:
    ``_environment`` drops every name of the never-pass set and every name that ends like a secret."""
    answerer = claude_answer if module == "claude" else codex_answer
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("MY_CUSTOM_API_KEY", "secret-value")
    monkeypatch.setenv("HOME", "/h")
    environment = answerer._environment()
    assert environment["HOME"] == "/h"
    assert not set(environment) & (set(SECRETS) | {"MY_CUSTOM_API_KEY"})
    assert set(SECRETS) <= answerer.NEVER_PASS | {"AUDITMANAGER_ENROLLMENT_SECRET", "PDF_ANALYSIS_RUNNER_TOKEN"}
    assert {"OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"} <= answerer.NEVER_PASS


# ------------------------------------------------------------------------------------- API answerers

KEY = "sk-test-" + "K" * 40
PROVIDERS = [
    ("anthropic_api", "claude-opus-5-5", "/v1/messages", "medium"),
    ("openai_api", "gpt-6.1-sol", "/v1/responses", "high"),
    ("openrouter_api", "anthropic/claude-opus-5-5", "/v1/chat/completions", "medium"),
]


def _call(api, provider, model, effort, **kwargs):
    base = dict(api_key=KEY, model=model, effort=effort, max_output_tokens=4321, timeout=20, system=TASK["system"],
                user_text=TASK["user_text"], output_schema=TASK["output_schema"], base_url=api.url, idle_timeout=5)
    base.update(kwargs)
    return api_answer.call(provider, **base)


@pytest.mark.parametrize("provider,model,path,effort", PROVIDERS)
def test_each_api_answerer_sends_the_model_effort_and_ceiling_and_returns_the_reported_model_and_usage(provider, model, path, effort):
    with H.FakeApi() as api:
        activity = Activity()
        reply = _call(api, provider, model, effort, activity=activity)
        [request] = api.of(path)
    body = request["body"]
    assert reply.output_text == '{"findings":[]}' and reply.reported_model == model
    assert (reply.input_tokens, reply.output_tokens) == {"anthropic_api": (30, 9), "openai_api": (31, 8), "openrouter_api": (33, 7)}[provider]
    assert body["model"] == model and body["stream"] is True
    ceiling = body.get("max_tokens") or body.get("max_output_tokens")
    assert ceiling == 4321
    efforts = body.get("output_config", {}).get("effort") or body.get("reasoning", {}).get("effort")
    assert efforts == effort
    assert "findings" in json.dumps(body), "the output schema is part of what the model is told"
    assert activity.touches >= 2
    if provider == "anthropic_api":
        assert request["headers"]["x-api-key"] == KEY and request["headers"]["anthropic-version"] == "2023-06-01"
        assert "authorization" not in request["headers"]
    else:
        assert request["headers"]["authorization"] == "Bearer " + KEY
    assert KEY.encode() not in request["raw"], "the key is a header, never a part of the body"
    if provider == "openai_api":
        assert body["store"] is False
    if provider == "openrouter_api":
        assert body["provider"] == {"data_collection": "deny"}


def test_openai_gets_a_strict_schema_when_the_caller_has_one_and_the_others_never_do():
    strict = {"type": "object", "properties": {"findings": {"type": "array", "items": {}}}, "required": ["findings"], "additionalProperties": False}
    with H.FakeApi() as api:
        _call(api, "openai_api", "gpt-6.1-sol", "low", strict_schema=strict)
        _call(api, "anthropic_api", "claude-opus-5-5", "low", strict_schema=strict)
    assert api.of("/v1/responses")[0]["body"]["text"]["format"] == {"type": "json_schema", "name": "answer", "schema": strict, "strict": True}
    assert "text" not in api.of("/v1/messages")[0]["body"]


@pytest.mark.parametrize("provider,model,path,effort", PROVIDERS)
def test_the_reported_model_must_be_the_requested_one_or_an_accepted_string(provider, model, path, effort):
    with H.FakeApi() as api:
        api.reported = model + "-20261001"
        with pytest.raises(api_answer.ApiError, match="^reported_model_mismatch$"):
            _call(api, provider, model, effort)
        reply = _call(api, provider, model, effort, accepted=(model + "-20261001",))
        assert reply.reported_model == model + "-20261001", "returned exactly as the provider named it"


@pytest.mark.parametrize("behavior,code,kind", [
    ("401", "api_auth_failed", "auth_failed"), ("403", "api_auth_failed", "auth_failed"),
    ("404", "api_model_not_found", "model_not_found"), ("429", "api_quota_exceeded", "quota_exceeded"),
    ("400_quota", "api_quota_exceeded", "quota_exceeded"), ("400_schema", "api_bad_request", None),
    ("redirect", "api_redirect_refused", None), ("error_event", "api_unavailable", None),
    ("truncated", "api_stream_ended_early", None), ("max_tokens", "output_truncated", None),
])
@pytest.mark.parametrize("provider,model,path,effort", PROVIDERS)
def test_failures_are_fixed_words_with_the_access_ones_classified_and_no_text_of_the_response(provider, model, path, effort, behavior, code, kind):
    with H.FakeApi() as api:
        api.behavior = behavior
        with pytest.raises(api_answer.ApiError) as caught:
            _call(api, provider, model, effort)
    if behavior == "error_event" and provider == "openrouter_api":
        code = "api_stream_error"  # the chat stream's error carries a numeric code only
    assert caught.value.code == code and caught.value.kind == kind
    shown = str(caught.value) + repr(caught.value)
    assert KEY not in shown and "sk-LEAK" not in shown and "credit balance" not in shown


def test_a_stream_that_goes_silent_ends_the_call_at_the_idle_timeout_and_the_total_bounds_a_stream_that_never_ends():
    with H.FakeApi() as api:
        api.behavior = "hang"
        started = time.monotonic()
        with pytest.raises(api_answer.ApiError) as caught:
            _call(api, "anthropic_api", "claude-opus-5-5", "medium", idle_timeout=1.0)
        assert caught.value.code in ("api_stalled", "timeout") and time.monotonic() - started < 8
        api.behavior = "keepalive"
        api.keepalive_seconds = 30
        started = time.monotonic()
        activity = Activity()
        with pytest.raises(api_answer.ApiError, match="^timeout$"):
            _call(api, "anthropic_api", "claude-opus-5-5", "medium", timeout=1.5, activity=activity)
        assert time.monotonic() - started < 8 and activity.touches >= 5, "keep-alives are signs of life, the total still ends the call"


def test_a_call_that_is_asked_to_stop_is_dropped_at_once():
    with H.FakeApi() as api:
        api.behavior = "hang"
        flag = {"stop": ""}
        threading.Timer(0.6, lambda: flag.update(stop="claim_lost")).start()
        started = time.monotonic()
        with pytest.raises(api_answer.Interrupted, match="claim_lost"):
            _call(api, "openai_api", "gpt-6.1-sol", "low", should_stop=lambda: flag["stop"], idle_timeout=30)
        assert time.monotonic() - started < 6


def test_what_the_model_returns_is_one_compact_json_object_or_an_error():
    assert api_answer.answer_json(' {"a": 1} ') == '{"a":1}'
    assert api_answer.answer_json('```json\n{"a": [1, 2]}\n```') == '{"a":[1,2]}'
    for bad, code in (("not json", "answer_not_json"), ("[1]", "answer_not_object"), ("", "answer_not_json")):
        with pytest.raises(api_answer.ApiError, match=code):
            api_answer.answer_json(bad)


def test_the_arguments_are_checked_before_a_request_is_made():
    with H.FakeApi() as api:
        for kwargs, code in (({"effort": "ludicrous"}, "invalid_effort"), ({"model": "a b"}, "invalid_model"),
                             ({"max_output_tokens": 0}, "invalid_max_output_tokens"), ({"api_key": ""}, "api_auth_failed")):
            with pytest.raises(api_answer.ApiError, match=code):
                _call(api, "anthropic_api", kwargs.pop("model", "claude-opus-5-5"), kwargs.pop("effort", "medium"), **kwargs)
        assert api.requests == []
        with pytest.raises(ValueError):
            api_answer.call("codex", api_key=KEY, model="x", effort="low", max_output_tokens=1, timeout=1, system="", user_text="",
                            output_schema={})
        # the effort levels are the provider's own: `max` is Anthropic's, `minimal` is OpenAI's
        with pytest.raises(api_answer.ApiError, match="invalid_effort"):
            _call(api, "openai_api", "gpt-6.1-sol", "max")


def test_a_key_is_sent_only_over_https_or_to_loopback_and_a_url_may_carry_no_credentials():
    assert api_answer.normalize_base_url("openrouter_api") == "https://openrouter.ai/api"
    assert api_answer.normalize_base_url("openai_api", "http://127.0.0.1:8080/") == "http://127.0.0.1:8080"
    for bad in ("http://api.example.org", "ftp://x", "https://u:p@api.example.org", "https://x/?a=1", "https:///", "https://x:notaport"):
        with pytest.raises(ValueError):
            api_answer.normalize_base_url("anthropic_api", bad)


def test_images_go_as_the_providers_own_image_blocks_in_order():
    pngs = [b"\x89PNG\r\n\x1a\none", b"\x89PNG\r\n\x1a\ntwo"]
    anthropic = api_answer.build_request("anthropic_api", model="m", effort="low", max_output_tokens=9, system="s", user_text="u",
                                         output_schema={}, images=pngs)
    kinds = [block["type"] for block in anthropic["messages"][0]["content"]]
    assert kinds == ["image", "image", "text"]
    openai = api_answer.build_request("openai_api", model="m", effort="low", max_output_tokens=9, system="s", user_text="u",
                                      output_schema={}, images=pngs)
    assert [block["type"] for block in openai["input"][0]["content"]] == ["input_text", "input_image", "input_image"]
    chat = api_answer.build_request("openrouter_api", model="m", effort="low", max_output_tokens=9, system="s", user_text="u",
                                    output_schema={}, images=pngs)
    assert [block["type"] for block in chat["messages"][1]["content"]] == ["text", "image_url", "image_url"]
