"""The paid W56a probe's fail-closed signals, without network calls."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from auditmanager.analysis.text.lock import provider_lock
from tools.provider import identity_probe
from tools.provider.identity_probe import ProbeFailure, assess_response, probe_once


PIN = provider_lock().model(provider_lock().primary_model_id)
SELECTED = "anthropic/claude-opus-5"


def _answer(model: object = SELECTED, cost: object = 0.00047) -> dict[str, object]:
    return {
        "model": model,
        "usage": {"prompt_tokens": 14, "completion_tokens": 16, "cost": cost},
        "choices": [{"message": {"content": "private answer"}}],
    }


def test_selected_model_requires_identity_and_locked_rate() -> None:
    result = assess_response(_answer(), selection="explicit", expected_name=SELECTED, pin=PIN)
    assert result["reported_model"] == SELECTED
    assert Decimal(str(result["expected_cost_usd"])) == Decimal("0.00047")
    assert result["pass"] is True
    assert "private answer" not in str(result)

    with pytest.raises(ProbeFailure, match="model_identity_mismatch"):
        assess_response(_answer("meta/muse-spark-1.3-contributor"),
                        selection="explicit", expected_name=SELECTED, pin=PIN)
    with pytest.raises(ProbeFailure, match="model_rate_mismatch") as failed_rate:
        assess_response(_answer(cost=0.0000046),
                        selection="explicit", expected_name=SELECTED, pin=PIN)
    assert failed_rate.value.evidence["reported_model"] == SELECTED
    assert failed_rate.value.evidence["reported_cost_usd"] == "0.0000046"
    assert "private answer" not in str(failed_rate.value.evidence)


@pytest.mark.parametrize("cost", [None, "NaN", "Infinity", -1])
def test_missing_or_nonfinite_cost_refuses(cost: object) -> None:
    with pytest.raises(ProbeFailure, match="invalid_usage_cost"):
        assess_response(_answer(cost=cost), selection="explicit", expected_name=SELECTED, pin=PIN)


@pytest.mark.parametrize("count", [None, -1, True, 1.5])
def test_invalid_token_counts_refuse(count: object) -> None:
    answer = _answer()
    answer["usage"]["prompt_tokens"] = count  # type: ignore[index]
    with pytest.raises(ProbeFailure, match="invalid_usage_count"):
        assess_response(answer, selection="explicit", expected_name=SELECTED, pin=PIN)


def test_default_must_be_concrete_and_distinct() -> None:
    result = assess_response(_answer("meta/other-1", 0.00001),
                             selection="default", expected_name=SELECTED, pin=PIN)
    assert result["reported_model"] == "meta/other-1"
    with pytest.raises(ProbeFailure, match="default_echoed_selected_model"):
        assess_response(_answer(), selection="default", expected_name=SELECTED, pin=PIN)
    with pytest.raises(ProbeFailure, match="stub_model_response"):
        assess_response(_answer("proxy"), selection="default", expected_name=SELECTED, pin=PIN)


def test_one_choice_without_an_answer_refuses() -> None:
    answer = _answer()
    answer["choices"] = [{}]
    with pytest.raises(ProbeFailure, match="invalid_response_shape"):
        assess_response(answer, selection="explicit", expected_name=SELECTED, pin=PIN)


def test_one_request_uses_host_config_and_prints_no_answer(tmp_path: Path) -> None:
    env = tmp_path / "provider.env"
    env.write_text(
        "PROXY_LLM_BASE_URL=https://gateway.invalid/agent/v1\n"
        "PROXY_LLM_TOKEN=test-secret\n"
        f"PROXY_LLM_MODEL={SELECTED}\n",
        encoding="utf-8",
    )
    requests = []

    class Response:
        status = 200

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self, count: int) -> bytes:
            assert count == 65_537
            return json.dumps(_answer()).encode("utf-8")

    def open_fake(request, *, timeout: int):  # noqa: ANN001, ANN202
        requests.append(request)
        assert timeout == 45
        return Response()

    result = probe_once(env_file=env, selection="explicit", opener=open_fake)
    assert result["pass"] is True
    assert len(requests) == 1
    request = requests[0]
    assert request.full_url == "https://gateway.invalid/agent/v1/chat/completions"
    body = json.loads(request.data)
    assert body["model"] == SELECTED
    assert body["max_tokens"] == 16
    assert "test-secret" not in str(result)
    assert "private answer" not in str(result)


def test_stub_configuration_refuses_before_request(tmp_path: Path) -> None:
    env = tmp_path / "provider.env"
    env.write_text(
        "PROXY_LLM_BASE_URL=https://gateway.invalid/agent/v1\n"
        "PROXY_LLM_TOKEN=test-secret\nPROXY_LLM_MODEL=proxy\n",
        encoding="utf-8",
    )

    def no_network(*_: object, **__: object) -> object:
        raise AssertionError("network must not be used")

    with pytest.raises(ProbeFailure, match="stub_model_response"):
        probe_once(env_file=env, selection="explicit", opener=no_network)


def test_cli_hides_unexpected_exception_details(monkeypatch, capsys) -> None:  # noqa: ANN001
    def fail(**_: object) -> object:
        raise RuntimeError("private URL and token must stay hidden")

    monkeypatch.setattr(identity_probe, "probe_once", fail)
    code = identity_probe.main([
        "--env-file", "/private/provider.env", "--gateway-role", "stand",
        "--selection", "explicit",
    ])
    output = capsys.readouterr().out
    assert code == 1
    assert json.loads(output) == {
        "gateway_role": "stand", "selection": "explicit",
        "pass": False, "error": "probe_failed",
    }
    assert "private" not in output
