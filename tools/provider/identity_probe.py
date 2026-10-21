"""One bounded W56a identity probe, with sanitized output and no retries.

Run on the gateway host with its existing provider.env. Each invocation makes
at most one request. The operator records its result and rechecks the spend
ledger before invoking the next selection or gateway.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Mapping

from auditmanager.analysis.text.lock import ModelPin, provider_lock


MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,99}\Z")
STUBS = frozenset({"proxy", "default", "auto"})
NON_IDENTITIES = STUBS | frozenset({"unknown", "none", "null", "stub", "model"})
PROMPT = "Ответь одним словом: да."
MAX_OUTPUT_TOKENS = 16
MAX_RESPONSE_BYTES = 65_536


class ProbeFailure(ValueError):
    """A stable refusal code; never carries a URL, token or response body."""

    def __init__(self, code: str, *, evidence: Mapping[str, str | int] | None = None) -> None:
        super().__init__(code)
        self.evidence = dict(evidence or {})


def _name(raw: object) -> str:
    if not isinstance(raw, str) or MODEL_NAME.fullmatch(raw) is None:
        raise ProbeFailure("invalid_model_name")
    if raw.lower() in NON_IDENTITIES or raw.lower().startswith("stub/"):
        raise ProbeFailure("stub_model_response")
    return raw


def _usage(raw: object) -> tuple[int, int, Decimal]:
    if not isinstance(raw, Mapping):
        raise ProbeFailure("missing_usage")
    counts: list[int] = []
    for field in ("prompt_tokens", "completion_tokens"):
        value = raw.get(field)
        if type(value) is not int or value <= 0:
            raise ProbeFailure("invalid_usage_count")
        counts.append(value)
    try:
        cost = Decimal(str(raw.get("cost")))
    except (InvalidOperation, ValueError):
        raise ProbeFailure("invalid_usage_cost") from None
    if not cost.is_finite() or cost <= 0:
        raise ProbeFailure("invalid_usage_cost")
    return counts[0], counts[1], cost


def assess_response(
    payload: object, *, selection: str, expected_name: str, pin: ModelPin
) -> dict[str, str | int | bool]:
    """Check a response without ever retaining answer text in the result."""
    if selection not in {"explicit", "default"}:
        raise ProbeFailure("invalid_selection")
    expected_name = _name(expected_name)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("choices"), list):
        raise ProbeFailure("invalid_response_shape")
    if len(payload["choices"]) != 1:
        raise ProbeFailure("invalid_choice_count")
    choice = payload["choices"][0]
    if (
        not isinstance(choice, Mapping)
        or not isinstance(choice.get("message"), Mapping)
        or not isinstance(choice["message"].get("content"), str)
        or not choice["message"]["content"].strip()
    ):
        raise ProbeFailure("invalid_response_shape")
    reported_name = _name(payload.get("model"))
    input_tokens, output_tokens, reported_cost = _usage(payload.get("usage"))
    expected_cost = (
        Decimal(input_tokens) * Decimal(str(pin.input_per_mtok_usd))
        + Decimal(output_tokens) * Decimal(str(pin.output_per_mtok_usd))
    ) / Decimal(1_000_000)
    tolerance = max(expected_cost * Decimal("0.20"), Decimal("0.00002"))
    evidence: dict[str, str | int] = {
        "reported_model": reported_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reported_cost_usd": str(reported_cost),
        "expected_cost_usd": str(expected_cost) if selection == "explicit" else "not_checked",
        "tolerance_usd": str(tolerance) if selection == "explicit" else "not_checked",
    }
    if selection == "explicit":
        if reported_name != expected_name:
            raise ProbeFailure("model_identity_mismatch", evidence=evidence)
        if abs(reported_cost - expected_cost) > tolerance:
            raise ProbeFailure("model_rate_mismatch", evidence=evidence)
    elif reported_name == expected_name:
        raise ProbeFailure("default_echoed_selected_model", evidence=evidence)
    return {
        "selection": selection,
        **evidence,
        "pass": True,
    }


def _read_env(path: Path) -> tuple[str, str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in {"PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN", "PROXY_LLM_MODEL"}:
            values[key] = value.strip().strip('"\'')
    try:
        base, token, model = (values[k] for k in (
            "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN", "PROXY_LLM_MODEL"
        ))
    except KeyError:
        raise ProbeFailure("missing_gateway_configuration") from None
    try:
        parts = urllib.parse.urlsplit(base)
    except ValueError:
        raise ProbeFailure("invalid_gateway_configuration") from None
    if parts.scheme not in {"http", "https"} or not parts.hostname or not token:
        raise ProbeFailure("invalid_gateway_configuration")
    if "?" in base or "#" in base:
        raise ProbeFailure("invalid_gateway_configuration")
    return base.rstrip("/"), token, _name(model)


def _endpoint(base: str) -> str:
    return base + (
        "/chat/completions" if urllib.parse.urlsplit(base).path.strip("/")
        else "/api/v1/chat/completions"
    )


def probe_once(
    *, env_file: Path, selection: str, stub_model: str | None = None,
    opener: Any = urllib.request.urlopen,
) -> dict[str, str | int | bool]:
    """Issue one tiny request; caller owns ledger and gateway distinction."""
    if selection not in {"explicit", "default"}:
        raise ProbeFailure("invalid_selection")
    if stub_model is not None and (selection != "default" or stub_model not in STUBS):
        raise ProbeFailure("invalid_default_selector")
    base, token, expected_name = _read_env(env_file)
    pin = provider_lock().model(provider_lock().primary_model_id)
    body: dict[str, object] = {
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    if selection == "explicit":
        body["model"] = expected_name
    elif stub_model is not None:
        body["model"] = stub_model
    request = urllib.request.Request(
        _endpoint(base), data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Request-Id": str(uuid.uuid4()),
            "X-Idempotency-Key": str(uuid.uuid4()),
        },
    )
    try:
        with opener(request, timeout=45) as response:
            if response.status != 200:
                raise ProbeFailure("http_refusal")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError:
        raise ProbeFailure("http_refusal") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProbeFailure("transport_outcome_unknown") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProbeFailure("response_too_large")
    try:
        payload = json.loads(raw)
    except (UnicodeError, ValueError):
        raise ProbeFailure("invalid_response_json") from None
    return assess_response(payload, selection=selection, expected_name=expected_name, pin=pin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--gateway-role", choices=("stand", "recording"), required=True)
    parser.add_argument("--selection", choices=("explicit", "default"), required=True)
    parser.add_argument("--stub-model", choices=sorted(STUBS))
    args = parser.parse_args(argv)
    try:
        result = probe_once(
            env_file=args.env_file, selection=args.selection, stub_model=args.stub_model
        )
    except Exception as error:
        # The CLI must never let an unexpected urllib or parser exception print
        # a private URL or response body in a traceback.
        code = str(error) if isinstance(error, ProbeFailure) else "probe_failed"
        print(json.dumps({"gateway_role": args.gateway_role, "selection": args.selection,
                          "pass": False, "error": code,
                          **(error.evidence if isinstance(error, ProbeFailure) else {})}))
        return 1
    print(json.dumps({"gateway_role": args.gateway_role, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
