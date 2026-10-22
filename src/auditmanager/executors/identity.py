"""Which model answered, and what it cost: the identity and rate check of a connection probe.

`EXEC-HTTP-01` (`R-133`, `R-143`). Ported from ``tools/provider/identity_probe.py`` (the
``assess_response`` of `R-136`); ``tools/`` is not imported because the image does not copy it.
The two differences from the tool are the point of the port:

* the **identity** is compared with the revision's *gateway model name* (what is sent), never
  with the pin id (what gives tariffs and the budget): the two are separate fields of a revision
  and neither is derived from the other;
* the **rate** check (within 20 %, at least USD 0.00002) applies only to a ``metered`` revision
  whose gateway *reports* a cost. A gateway that reports none (Ollama, vLLM, the Anthropic SDK)
  is recorded as ``not_reported``, not failed, and a ``not_metered`` revision as ``not_metered``.

A reply that names no model, names a placeholder (``proxy``, ``default``, ``auto``, ``unknown``,
``stub/...``) or names a different model is a ``model_mismatch``; it is never a pass, and a
gateway's name for a model is never guessed from what the reply did not say.

Nothing here keeps answer text. A detail is a fixed phrase.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Final

__all__ = [
    "MODEL_NAME",
    "NON_IDENTITIES",
    "PROMPT",
    "STUBS",
    "Assessment",
    "assess_chat_completion",
    "assess_identity",
    "is_placeholder",
    "rate_check",
]

#: A model name as gateways spell it: ``anthropic/claude-opus-5``, ``llama3:8b``.
MODEL_NAME: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:@+-]{0,127}")
STUBS: Final[frozenset[str]] = frozenset({"proxy", "default", "auto"})
NON_IDENTITIES: Final[frozenset[str]] = STUBS | frozenset(
    {"unknown", "none", "null", "stub", "model"}
)
#: The smallest completion that proves a key, a model and a route: one word back.
PROMPT: Final[str] = "Ответь одним словом: да."
_TOLERANCE_RATIO: Final[Decimal] = Decimal("0.20")
_TOLERANCE_FLOOR_USD: Final[Decimal] = Decimal("0.00002")


@dataclass(frozen=True, slots=True)
class Assessment:
    """The result of reading one successful answer. ``outcome`` is a probe outcome."""

    outcome: str
    reported_model: str | None
    rate_check: str
    detail: str | None = None


def is_placeholder(name: str | None) -> bool:
    """A name that selects nothing: a gateway stub or a non-identity."""
    if name is None:
        return True
    lowered = name.strip().lower()
    return lowered in NON_IDENTITIES or lowered.startswith("stub/")


def _clean(name: object) -> str | None:
    """The reported name when it is a plausible model name, else ``None``."""
    if not isinstance(name, str) or MODEL_NAME.fullmatch(name) is None:
        return None
    return name


def assess_identity(reported: object, expected_gateway_model: str) -> tuple[str, str | None]:
    """``(outcome, reported_model)``: ``ok`` only when the reply named the expected gateway model
    exactly (no prefix, no case folding). The expected name must itself be a real choice."""
    if is_placeholder(expected_gateway_model):
        return "model_mismatch", None
    name = _clean(reported)
    if name is None or is_placeholder(name):
        return "model_mismatch", None
    return ("ok" if name == expected_gateway_model else "model_mismatch"), name


def _count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def rate_check(
    usage: object, *, billing: str, input_per_mtok_usd: float, output_per_mtok_usd: float,
) -> str:
    """``checked``, ``mismatch``, ``not_reported`` or ``not_metered``.

    ``mismatch`` only when the gateway reported a cost and it is outside the tolerance around
    what the pin's rates give for the reported token counts."""
    if billing != "metered":
        return "not_metered"
    if not isinstance(usage, Mapping):
        return "not_reported"
    raw = usage.get("cost")
    tokens_in, tokens_out = _count(usage.get("prompt_tokens")), _count(
        usage.get("completion_tokens"))
    if raw is None or isinstance(raw, bool) or tokens_in is None or tokens_out is None:
        return "not_reported"
    try:
        reported = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return "not_reported"
    if not reported.is_finite() or reported < 0:
        return "not_reported"
    expected = (
        Decimal(tokens_in) * Decimal(str(input_per_mtok_usd))
        + Decimal(tokens_out) * Decimal(str(output_per_mtok_usd))
    ) / Decimal(1_000_000)
    tolerance = max(expected * _TOLERANCE_RATIO, _TOLERANCE_FLOOR_USD)
    return "checked" if abs(reported - expected) <= tolerance else "mismatch"


def assess_chat_completion(
    payload: Any, *, expected_gateway_model: str, billing: str,
    input_per_mtok_usd: float, output_per_mtok_usd: float,
) -> Assessment:
    """Read an OpenAI-shaped chat completion: shape, identity, then rate.

    ``protocol_error`` for a body that is not a chat completion with one non-empty answer;
    ``model_mismatch`` for the identity; ``rate_mismatch`` for a reported cost off the pin's
    rates; otherwise ``ok``."""
    if not isinstance(payload, Mapping) or not isinstance(payload.get("choices"), list):
        return Assessment("protocol_error", None, "not_reported", "the answer is not a chat completion")
    choices = payload["choices"]
    message = choices[0].get("message") if len(choices) == 1 and isinstance(choices[0], Mapping) else None
    content = message.get("content") if isinstance(message, Mapping) else None
    if not isinstance(content, str) or not content.strip():
        return Assessment("protocol_error", None, "not_reported", "the answer carries no text")
    outcome, reported = assess_identity(payload.get("model"), expected_gateway_model)
    rate = rate_check(
        payload.get("usage"), billing=billing, input_per_mtok_usd=input_per_mtok_usd,
        output_per_mtok_usd=output_per_mtok_usd,
    )
    if outcome != "ok":
        detail = (
            "the gateway model name is a placeholder"
            if is_placeholder(expected_gateway_model) else
            "the answer names no usable model" if reported is None else
            "the answer names another model than the revision's"
        )
        return Assessment("model_mismatch", reported, rate, detail)
    if rate == "mismatch":
        return Assessment("rate_mismatch", reported, rate,
                          "the reported cost differs from the pin's rates by more than 20 %")
    return Assessment("ok", reported, rate)
