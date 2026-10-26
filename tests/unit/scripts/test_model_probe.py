"""`PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01`: the model identity probe, driven by a stub transport.

**Nothing here touches a network, a credential file or money.** The tool is the real one
(`scripts/model_probe/probe.py`) and the adapter is the product's real builder
(`build_http_adapter`, flavour `openai_chat`); the only thing replaced is the opener under it, the
function that would open the socket. The gateway is a stub that records every request it is
handed and answers with a canned body. The "credential" is a made-up string that opens nothing.

The shape of each guard case is the repository's usual one: the refusal is shown with the number
of calls the stub received (`0` for every refusal), and the neighbouring case that is *not*
refused is shown too. The static guard at the end ("the tool reads only the lock and the
environment") carries its own can-fail case.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import logging
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from auditmanager.bootstrap import settings as bootstrap_settings
from auditmanager.executors import http_adapter
from auditmanager.executors.identity import PROMPT

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/model_probe/probe.py"
SPEC = importlib.util.spec_from_file_location("model_probe_tool", SCRIPT)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)

TOKEN = "sk-test-NOT-A-REAL-KEY-0123456789abcdef"
ANSWER = "ANSWER-TEXT-MARKER"
BASE_URL = "https://gateway.example.test"
ENV = {probe.BASE_URL_ENV: BASE_URL, probe.TOKEN_ENV: TOKEN}
PINS = list(probe.load_provider_lock(probe.LOCK_PATH).models.values())
SLUGS = {pin.model_id: f"gw/{pin.model_id}" for pin in PINS}
_ABSENT = object()


# -- the stub gateway ----------------------------------------------------------------------------

class _Reply:
    def __init__(self, status: int, body: bytes) -> None:
        self.status, self._body, self.headers = status, body, {}

    def __enter__(self) -> _Reply:
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def read(self, limit: int | None = None) -> bytes:
        return self._body if limit is None else self._body[:limit]


def chat(model: Any, *, cost: Any = _ABSENT, prompt: int = 14, completion: int = 3,
         pin: Any = None, usage: bool = True, finish: str = "stop") -> dict[str, Any]:
    """A chat-completions body. ``cost`` defaults to what the pin's rates give for the tokens."""
    document: dict[str, Any] = {
        "id": "gen-stub", "choices": [{"index": 0, "finish_reason": finish,
                                       "message": {"role": "assistant", "content": ANSWER}}],
    }
    if model is not _ABSENT:
        document["model"] = model
    if usage:
        if cost is _ABSENT:
            cost = fair_cost(pin, prompt, completion) if pin is not None else 0.0001
        document["usage"] = {"prompt_tokens": prompt, "completion_tokens": completion}
        if cost is not None:
            document["usage"]["cost"] = cost
    return document


def fair_cost(pin: Any, prompt: int = 14, completion: int = 3) -> float:
    return float((Decimal(prompt) * Decimal(str(pin.input_per_mtok_usd))
                  + Decimal(completion) * Decimal(str(pin.output_per_mtok_usd))) / 1_000_000)


class Gateway:
    """The stand-in for the opener: records each request, answers per requested slug."""

    def __init__(self, replies: Mapping[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._replies = dict(replies or {})

    def __call__(self, request: Any, timeout: float | None = None) -> _Reply:
        body = json.loads(request.data)
        self.calls.append({
            "url": request.full_url, "body": body,
            "headers": {key.lower(): value for key, value in request.header_items()},
        })
        spec = self._replies.get(body["model"], "default")
        if isinstance(spec, BaseException):
            raise spec
        if spec == "default":
            pin = next(p for p in PINS if SLUGS[p.model_id] == body["model"])
            spec = chat(body["model"], pin=pin)
        if isinstance(spec, tuple):
            return _Reply(spec[0], spec[1])
        return _Reply(200, json.dumps(spec).encode("utf-8"))


def stub_factory(gateway: Gateway) -> Any:
    """The product's own builder, with the network (and only the network) replaced."""
    def factory(*, base_url: str, token: str, slug: str) -> Any:
        adapter = probe.product_adapter(base_url=base_url, token=token, slug=slug)
        adapter._opener = gateway
        return adapter
    return factory


class Run:
    def __init__(self, code: int, out: str, err: str, path: Path, gateway: Gateway) -> None:
        self.code, self.out, self.err, self.path, self.gateway = code, out, err, path, gateway

    @property
    def report(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def block(self, pin_id: str) -> dict[str, str]:
        text = self.report.split(f"--- model {pin_id} ---\n", 1)[1].split("\n\n", 1)[0]
        return dict(line.split(": ", 1) for line in text.splitlines())

    def summary(self) -> dict[str, str]:
        text = self.report.split("--- summary ---\n", 1)[1]
        return dict(line.split(": ", 1) for line in text.splitlines() if ": " in line)


def run(tmp_path: Path, *extra: str, replies: Mapping[str, Any] | None = None,
        env: Mapping[str, str] | None = None, confirm: bool = True,
        slugs: Mapping[str, str] | None = None, report: str | None = "report.txt",
        run_id: str = "run-1", gateway: Gateway | None = None, **keywords: Any) -> Run:
    gateway = gateway or Gateway(replies)
    argv = ["--confirm-paid"] if confirm else []
    for pin_id, slug in (SLUGS if slugs is None else slugs).items():
        argv += ["--slug", f"{pin_id}={slug}"]
    path = tmp_path / (report or "unused")
    if report is not None:
        argv += ["--report", str(path)]
    argv += list(extra)
    out, err = StringIO(), StringIO()
    code = probe.main(argv, environ=ENV if env is None else env, adapter_factory=stub_factory(gateway),
                      out=out, err=err, run_id=run_id, **keywords)
    return Run(code, out.getvalue(), err.getvalue(), path, gateway)


def refused(result: Run) -> None:
    assert result.code == 2, result.err
    assert result.gateway.calls == []
    assert "refused before any call" in result.err


# -- a matching run --------------------------------------------------------------------------------

def test_a_matching_run_exits_0_and_reports_every_pinned_model(tmp_path: Path) -> None:
    result = run(tmp_path)
    assert result.code == 0, result.out
    assert len(result.gateway.calls) == len(PINS)
    for pin, call in zip(PINS, result.gateway.calls):
        block = result.block(pin.model_id)
        assert block["requested_slug"] == SLUGS[pin.model_id] == call["body"]["model"]
        assert block["reported_model"] == SLUGS[pin.model_id]
        assert block["verdict"] == "match" and block["adapter_outcome"] == "answered"
        assert (block["input_tokens"], block["output_tokens"], block["finish_reason"]) == ("14", "3", "stop")
        assert block["rate_check"] == "checked" and block["cost_basis"] == "reported"
    summary = result.summary()
    assert summary["all_identities_match"] == "yes" and summary["lock_candidate"] == "yes"
    assert summary["exit_code"] == "0" and summary["stopped"] == "none"
    assert summary["models_pinned_in_lock"] == summary["models_called"] == str(len(PINS))
    assert "P02_LOCK.json: not written" in result.report
    assert result.report.count("reported_model:") == len(PINS)


def test_the_request_is_the_minimal_one_through_the_products_adapter(tmp_path: Path) -> None:
    result = run(tmp_path)
    keys = []
    for pin, call in zip(PINS, result.gateway.calls):
        assert call["url"] == BASE_URL + "/api/v1/chat/completions"
        assert call["body"] == {"model": SLUGS[pin.model_id], "max_tokens": 16,
                                "messages": [{"role": "user", "content": PROMPT}]}
        assert call["headers"]["authorization"] == f"Bearer {TOKEN}"
        keys.append(call["headers"]["x-idempotency-key"])
    assert len(set(keys)) == len(PINS)
    again = run(tmp_path, report="again.txt", run_id="run-2")
    assert [c["headers"]["x-idempotency-key"] for c in again.gateway.calls] != keys


def test_the_product_adapter_is_the_one_the_tool_builds() -> None:
    adapter = probe.product_adapter(base_url=BASE_URL, token=TOKEN, slug="gw/x-model")
    assert type(adapter) is http_adapter.OpenAIImageAdapter
    assert adapter._settings.model == "gw/x-model" and adapter._settings.base_url == BASE_URL
    assert adapter._settings.model_aliases == ()
    assert type(adapter._opener).__name__ == "_Opener"


def test_the_pinned_destination_layer_refuses_an_internal_address_in_the_call(tmp_path: Path) -> None:
    out, err = StringIO(), StringIO()
    code = probe.main(
        ["--confirm-paid", "--report", str(tmp_path / "r.txt"),
         *[a for p in PINS for a in ("--slug", f"{p.model_id}={SLUGS[p.model_id]}")]],
        environ={probe.BASE_URL_ENV: "http://127.0.0.1:9", probe.TOKEN_ENV: TOKEN}, out=out, err=err)
    assert code == 1
    report = (tmp_path / "r.txt").read_text(encoding="utf-8")
    assert report.count("adapter_outcome: dependency_unavailable") == len(PINS)
    assert report.count("cost_basis: none") == len(PINS)


# -- the comparison is exact (R-133, AD-13) ----------------------------------------------------------

def _variants() -> list[tuple[str, Any]]:
    slug = SLUGS[PINS[0].model_id]
    return [
        ("another model", "meta/muse-spark-1.3-contributor"),
        ("a dated variant", slug + "-20261001"),
        ("the bare pin id", PINS[0].model_id),
        ("case folded", slug.upper()),
        ("a longer prefix", "openrouter/" + slug),
    ]


@pytest.mark.parametrize(("label", "reported"), _variants(), ids=[v[0] for v in _variants()])
def test_any_name_but_the_requested_one_is_a_mismatch_and_exit_1(
    tmp_path: Path, label: str, reported: str
) -> None:
    first = PINS[0]
    result = run(tmp_path, replies={SLUGS[first.model_id]: chat(reported, pin=first)})
    assert result.code == 1
    block = result.block(first.model_id)
    assert block["verdict"] == "mismatch" and block["verdict_reason"] == "other_model"
    assert block["reported_model"] == reported
    assert block["adapter_outcome"] == "model_identity_mismatch"  # the product's own refusal agrees
    assert len(result.gateway.calls) == len(PINS)  # a mismatch does not stop the others
    assert result.summary()["lock_candidate"] == "no" and result.summary()["all_identities_match"] == "no"
    assert result.block(PINS[1].model_id)["verdict"] == "match"


@pytest.mark.parametrize("reported", [_ABSENT, None, "", SLUGS[PINS[0].model_id] + " ", 7, "proxy"],
                         ids=["absent", "null", "empty", "trailing space", "number", "a placeholder"])
def test_a_reply_that_names_no_usable_model_is_a_mismatch(tmp_path: Path, reported: Any) -> None:
    first = PINS[0]
    result = run(tmp_path, replies={SLUGS[first.model_id]: chat(reported, pin=first)})
    block = result.block(first.model_id)
    assert result.code == 1
    assert block["verdict"] == "mismatch" and block["verdict_reason"] == "no_usable_model_named"
    assert block["adapter_outcome"] == "model_identity_mismatch"


# -- the ceiling -----------------------------------------------------------------------------------

def test_a_reply_that_costs_more_than_the_ceiling_stops_the_run(tmp_path: Path) -> None:
    first = PINS[0]
    result = run(tmp_path, replies={SLUGS[first.model_id]: chat(SLUGS[first.model_id], cost=0.60)})
    assert result.code == 3
    assert len(result.gateway.calls) == 1
    assert result.block(first.model_id)["verdict"] == "match"
    assert result.block(first.model_id)["counted_cost_usd"] == "0.6"
    for pin in PINS[1:]:
        assert result.block(pin.model_id)["verdict"] == "not_called"
        assert result.block(pin.model_id)["reported_model"] == "none"
    assert result.summary()["stopped"] == "ceiling_exceeded" and result.summary()["lock_candidate"] == "no"


def test_a_call_that_could_pass_the_ceiling_is_not_made(tmp_path: Path) -> None:
    result = run(tmp_path, "--max-usd", "0.0001")
    assert result.code == 3
    assert result.gateway.calls == []
    assert result.summary()["stopped"] == "projected_over_ceiling"
    assert all(result.block(p.model_id)["verdict"] == "not_called" for p in PINS)


def test_the_projection_counts_what_is_already_spent(tmp_path: Path) -> None:
    first, second = PINS[0], PINS[1]
    ceiling = probe.worst_case_usd(first) + Decimal("0.0001")
    result = run(tmp_path, "--max-usd", str(ceiling),
                 replies={SLUGS[first.model_id]: chat(SLUGS[first.model_id], cost=0.0015)})
    assert result.code == 3
    assert len(result.gateway.calls) == 1  # the second would have been the one to pass the ceiling
    assert result.block(second.model_id)["verdict"] == "not_called"
    assert result.summary()["stopped"] == "projected_over_ceiling"


def test_a_cost_the_gateway_does_not_report_is_counted_not_assumed_free(tmp_path: Path) -> None:
    first, second = PINS[0], PINS[1]
    result = run(tmp_path, replies={
        SLUGS[first.model_id]: chat(SLUGS[first.model_id], cost=None, pin=first),
        SLUGS[second.model_id]: chat(SLUGS[second.model_id], usage=False)})
    one, two = result.block(first.model_id), result.block(second.model_id)
    assert one["cost_basis"] == "estimated" and one["rate_check"] == "not_reported"
    assert Decimal(one["counted_cost_usd"]) == Decimal(str(fair_cost(first)))
    assert two["cost_basis"] == "bound"
    assert Decimal(two["counted_cost_usd"]) == probe.worst_case_usd(second)
    assert result.summary()["lock_candidate"] == "no"


def test_the_default_ceiling_is_half_a_dollar_and_five_is_the_limit(tmp_path: Path) -> None:
    assert run(tmp_path).report.count("ceiling_usd: 0.5\n") == 1
    assert run(tmp_path, "--max-usd", "5.00", report="five.txt").code == 0
    for bad in ("5.01", "0", "-1", "nan", "inf", "abc", ""):
        refused(run(tmp_path, "--max-usd", bad, report=f"bad-{len(bad)}-{bad or 'e'}.txt"))


# -- failures of a call --------------------------------------------------------------------------------

def test_a_refused_credential_costs_nothing_and_a_gateway_error_is_counted_at_the_worst_case(
    tmp_path: Path,
) -> None:
    first, second = PINS[0], PINS[1]
    result = run(tmp_path, replies={
        SLUGS[first.model_id]: (401, b'{"error": {"code": "unauthorized"}}'),
        SLUGS[second.model_id]: (500, b"upstream broke")})
    one, two = result.block(first.model_id), result.block(second.model_id)
    assert result.code == 1
    assert one["verdict"] == "no_verdict" and one["adapter_outcome"] == "dependency_credential_refused"
    assert one["counted_cost_usd"] == "0" and one["cost_basis"] == "none"
    assert two["verdict"] == "no_verdict" and two["cost_basis"] == "bound"
    assert Decimal(two["counted_cost_usd"]) == probe.worst_case_usd(second)
    assert len(result.gateway.calls) == len(PINS)  # no retry, and the run goes on to the next model


def test_an_error_body_is_never_read_as_an_answer(tmp_path: Path) -> None:
    first = PINS[0]
    lying = json.dumps(chat(SLUGS[first.model_id], pin=first)).encode("utf-8")
    result = run(tmp_path, replies={SLUGS[first.model_id]: (500, lying)})
    block = result.block(first.model_id)
    assert block["verdict"] == "no_verdict" and block["reported_model"] == "none"
    assert block["verdict_reason"] == "no_answer_body"


def test_an_unexpected_exception_is_reported_by_type_only(tmp_path: Path) -> None:
    first = PINS[0]
    result = run(tmp_path, replies={SLUGS[first.model_id]: RuntimeError(f"boom {TOKEN}")})
    assert result.block(first.model_id)["adapter_outcome"] == "unexpected_RuntimeError"
    assert TOKEN not in result.report + result.out + result.err


def test_the_report_is_on_disk_after_each_model(tmp_path: Path) -> None:
    second = PINS[1]
    gateway = Gateway({SLUGS[second.model_id]: KeyboardInterrupt()})
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, gateway=gateway)
    written = (tmp_path / "report.txt").read_text(encoding="utf-8")
    assert f"requested_slug: {SLUGS[PINS[0].model_id]}" in written and "verdict: match" in written
    assert "complete: no" in written


# -- rates ---------------------------------------------------------------------------------------------

def test_a_reported_cost_far_from_the_locks_rates_is_not_a_lock_candidate(tmp_path: Path) -> None:
    first = PINS[0]
    result = run(tmp_path, replies={SLUGS[first.model_id]: chat(SLUGS[first.model_id], cost=0.0009)})
    assert result.code == 0  # the identity is right; the rates are the integrator's call
    assert result.block(first.model_id)["rate_check"] == "mismatch"
    assert result.summary()["all_identities_match"] == "yes" and result.summary()["lock_candidate"] == "no"


def test_a_subset_is_never_a_lock_candidate(tmp_path: Path) -> None:
    first = PINS[0]
    result = run(tmp_path, "--only", first.model_id, slugs={first.model_id: SLUGS[first.model_id]})
    assert result.code == 0 and len(result.gateway.calls) == 1
    assert result.summary()["lock_candidate"] == "no"
    assert f"--- model {PINS[1].model_id} ---" not in result.report


# -- refusals before any call --------------------------------------------------------------------------

class _TouchedEnvironment(dict):  # type: ignore[type-arg]
    touched = False

    def get(self, *args: Any) -> Any:  # noqa: D102
        type(self).touched = True
        return super().get(*args)

    def __getitem__(self, key: Any) -> Any:
        type(self).touched = True
        return super().__getitem__(key)


def test_without_confirm_paid_nothing_is_read_and_nothing_is_called(tmp_path: Path) -> None:
    environment = _TouchedEnvironment(ENV)
    result = run(tmp_path, confirm=False, env=environment)
    refused(result)
    assert "--confirm-paid" in result.err
    assert _TouchedEnvironment.touched is False
    assert not result.path.exists()
    assert run(tmp_path, env=_TouchedEnvironment(ENV), report="ok.txt").code == 0


@pytest.mark.parametrize("env", [
    {}, {probe.BASE_URL_ENV: BASE_URL}, {probe.TOKEN_ENV: TOKEN},
    {probe.BASE_URL_ENV: BASE_URL, probe.TOKEN_ENV: ""},
    {probe.BASE_URL_ENV: BASE_URL, probe.TOKEN_ENV: "   "},
    {probe.BASE_URL_ENV: "  ", probe.TOKEN_ENV: TOKEN},
], ids=["nothing", "no token", "no base url", "empty token", "blank token", "blank base url"])
def test_without_a_credential_in_the_environment_nothing_is_called(tmp_path: Path, env: Mapping[str, str]) -> None:
    result = run(tmp_path, env=env)
    refused(result)
    assert not result.path.exists()


def test_a_base_url_the_product_adapter_refuses_is_refused_before_any_call(tmp_path: Path) -> None:
    refused(run(tmp_path, env={probe.BASE_URL_ENV: "ftp://gateway.example.test", probe.TOKEN_ENV: TOKEN}))
    refused(run(tmp_path, env={probe.BASE_URL_ENV: BASE_URL + "/v1?x=1", probe.TOKEN_ENV: TOKEN}))


def test_every_probed_model_needs_an_explicit_real_slug(tmp_path: Path) -> None:
    first = PINS[0]
    missing = {p.model_id: SLUGS[p.model_id] for p in PINS[1:]}
    refused(run(tmp_path, slugs=missing))
    refused(run(tmp_path, slugs={**SLUGS, first.model_id: "auto"}))
    refused(run(tmp_path, slugs={**SLUGS, first.model_id: "default"}))
    refused(run(tmp_path, slugs={**SLUGS, first.model_id: "has a space"}))
    refused(run(tmp_path, slugs={**SLUGS, "not-a-pinned-model": "gw/x"}))
    refused(run(tmp_path, "--slug", f"{first.model_id}={SLUGS[first.model_id]}"))  # twice
    refused(run(tmp_path, "--only", "not-a-pinned-model"))
    refused(run(tmp_path, "--only", first.model_id))  # the others' slugs name models not probed
    assert run(tmp_path, report="fine.txt").code == 0


def test_the_report_is_created_exclusively_and_privately(tmp_path: Path) -> None:
    existing = tmp_path / "taken.txt"
    existing.write_text("precious", encoding="utf-8")
    refused(run(tmp_path, report="taken.txt"))
    assert existing.read_text(encoding="utf-8") == "precious"
    refused(run(tmp_path, report="no-such-dir/report.txt"))
    result = run(tmp_path, report="private.txt")
    assert stat.S_IMODE(result.path.stat().st_mode) == 0o600


def test_the_default_report_path_is_outside_the_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    result = run(tmp_path, report=None, run_id="abc123")
    expected = tmp_path / "model-probe-abc123.txt"
    assert result.code == 0 and expected.exists()
    assert f"report_path: {expected}" in result.out
    assert ROOT not in probe.default_report_path("x").resolve().parents


def test_a_product_adapter_without_the_opener_seam_is_refused(tmp_path: Path) -> None:
    class Sealed:
        def complete(self, request: Any) -> None:
            raise AssertionError("must not be called")

    out, err = StringIO(), StringIO()
    code = probe.main(
        ["--confirm-paid", "--report", str(tmp_path / "r.txt"),
         *[a for p in PINS for a in ("--slug", f"{p.model_id}={SLUGS[p.model_id]}")]],
        environ=ENV, adapter_factory=lambda **_: Sealed(), out=out, err=err)
    assert code == 2 and "no opener seam" in err.getvalue()
    assert not (tmp_path / "r.txt").exists()


def test_usage_errors_exit_2_through_argparse() -> None:
    with pytest.raises(SystemExit) as stopped:
        probe.main(["--no-such-flag"], environ=ENV)
    assert stopped.value.code == 2


def test_the_command_line_entry_refuses_without_the_flag() -> None:
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    environment.pop(probe.TOKEN_ENV, None)
    done = subprocess.run(
        [sys.executable, "-m", "scripts.model_probe.probe"], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 2 and "refused before any call" in done.stderr
    assert done.stdout == ""


# -- no key material, no lock write -------------------------------------------------------------------------

def test_the_credential_never_reaches_the_report_or_the_console(tmp_path: Path) -> None:
    result = run(tmp_path)
    assert TOKEN not in result.report + result.out + result.err
    assert ANSWER not in result.report + result.out + result.err
    assert "credential_guard: clean" in result.report


def test_a_gateway_that_echoes_the_credential_is_redacted_and_exits_5(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    first = PINS[0]
    caplog.set_level("DEBUG")
    result = run(tmp_path, replies={SLUGS[first.model_id]: chat(TOKEN, pin=first)})
    assert result.code == 5
    assert TOKEN not in result.report + result.out + result.err
    assert any("identity mismatch" in r.getMessage() for r in caplog.records)  # the adapter did log
    assert all(TOKEN not in r.getMessage() for r in caplog.records)  # ... but not the credential
    block = result.block(first.model_id)
    assert block["reported_model"] == probe.REDACTED and block["verdict"] == "mismatch"
    assert result.summary()["credential_guard"] == "redacted" and result.summary()["exit_code"] == "5"
    assert result.summary()["lock_candidate"] == "no"


def test_the_log_record_factory_is_restored_after_a_run(tmp_path: Path) -> None:
    before = logging.getLogRecordFactory()
    run(tmp_path)
    assert logging.getLogRecordFactory() is before


def test_the_lock_is_never_written(tmp_path: Path) -> None:
    before = hashlib.sha256(probe.LOCK_PATH.read_bytes()).hexdigest()
    result = run(tmp_path)
    assert hashlib.sha256(probe.LOCK_PATH.read_bytes()).hexdigest() == before
    assert result.summary()["exit_code"] == "0"
    assert re.search(rf"^lock_sha256: {before}$", result.report, re.MULTILINE)
    copy = tmp_path / "P02_LOCK.json"
    copy.write_bytes(probe.LOCK_PATH.read_bytes())
    refused(run(tmp_path, report="P02_LOCK.json", lock_path=copy))
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == before


def test_a_lock_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    refused(run(tmp_path, lock_path=broken))
    refused(run(tmp_path, lock_path=tmp_path / "absent.json"))


def test_the_environment_names_are_the_products() -> None:
    assert probe.BASE_URL_ENV == bootstrap_settings.PROXY_BASE_URL_ENV
    assert probe.TOKEN_ENV == bootstrap_settings.PROXY_TOKEN_ENV


# -- the static guard: the tool reads the lock and the environment, nothing else ---------------------------

def source_findings(source: str) -> list[str]:
    """Every file-touching call or credential source in ``source`` besides the allowed ones: the
    one ``lock_file.read_bytes()`` and the one exclusive ``os.open``."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        if name != "os.open" and (name in {"open", "io.open"} or name.endswith(
                (".write_text", ".write_bytes", ".read_text", ".open", ".unlink", ".rename"))):
            found.append(name)
        if name == "os.open" and "O_EXCL" not in ast.unparse(node):
            found.append("os.open without O_EXCL")
        if name.endswith(".read_bytes") and name != "lock_file.read_bytes":
            found.append(name)
    for pattern in (r"provider\.env", r"\.env\b", r"dotenv", r"getenv", r"ANTHROPIC_API_KEY", r"environ\.items"):
        if re.search(pattern, source):
            found.append(f"mentions {pattern}")
    return found


def test_the_tool_reads_only_the_lock_and_the_environment() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert source_findings(source) == []
    assert source.count("lock_file.read_bytes()") == 1 and source.count("os.open(") == 1


@pytest.mark.parametrize("addition", [
    "\nopen('provider.env').read()\n",
    "\nPath('docs/program/P02_LOCK.json').write_text('x')\n",
    "\nx = os.environ.get('ANTHROPIC_API_KEY')\n",
    "\nos.open('p', os.O_WRONLY | os.O_CREAT)\n",
    "\nPath('.env').read_text()\n",
], ids=["open", "lock write", "other key", "no O_EXCL", "dotenv"])
def test_a_check_that_cannot_fail_is_not_a_check(addition: str) -> None:
    clean = SCRIPT.read_text(encoding="utf-8")
    assert source_findings(clean + addition) != source_findings(clean)
