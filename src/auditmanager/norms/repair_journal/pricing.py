"""The rate card and the bound an unknown outcome is charged at.

`W54-PLAN.md` §3.3: the model is named explicitly (``PROXY_LLM_MODEL``) and must be on the
rate card; an ``outcome_unknown`` counts at the card's output rate for the full output
ceiling (8000 tokens) plus a pixel-derived input bound — about $0.20 on opus-5 and $0.08 on
sonnet-5.

The two rates are the ones ``docs/program/P02_LOCK.json`` records under ``models``. They are
restated here because this context reads nothing of another context's internals (ALR-05),
and ``tests/integration/norms/repair/test_pricing.py`` pins them to that file, so a change
on either side fails there rather than in a bill.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from .model import money

#: The values the proxy reads as "I am not choosing a model" (`analysis/text/proxy.py`). A
#: paid run never names one: the answer's model could then be anything.
MODEL_STUBS: frozenset[str] = frozenset({"proxy", "default", "auto"})

#: Anthropic's documented image-token estimate is ``width x height / 750``. The crop is
#: sent at its rendered size, so the pixel count bounds the image's input tokens from above.
PIXELS_PER_INPUT_TOKEN: int = 750
#: The system prompt and the message scaffolding, as a token allowance. The prompt is a
#: few hundred characters; one token per character is a generous upper bound.
TEXT_INPUT_ALLOWANCE_TOKENS: int = 2000
#: The output ceiling every repair call is sent with, and that the bound assumes.
OUTPUT_TOKEN_CEILING: int = 8000


@dataclass(frozen=True, slots=True)
class Rate:
    input_per_mtok_usd: Decimal
    output_per_mtok_usd: Decimal


#: `P02_LOCK.json` `models.primary` and `models.cheaper_tier`.
RATE_CARD: dict[str, Rate] = {
    "claude-opus-5": Rate(Decimal("5.0"), Decimal("25.0")),
    "claude-sonnet-5": Rate(Decimal("2.0"), Decimal("10.0")),
}


class ModelNotPriced(ValueError):
    """The named model is a stub or is not on the rate card; no paid run starts."""


def rate_for(model: str) -> Rate:
    """The card's rate for ``model``.

    A gateway may prefix the name with its vendor (``anthropic/claude-opus-5``); the rate is
    the card's for the bare name. The answer's model must still equal the configured name
    exactly — that check is the runner's, not this lookup's.
    """
    name = model.strip()
    if not name or name in MODEL_STUBS:
        raise ModelNotPriced(
            "the repair run needs an explicit model on the rate card; a stub such as "
            f"{sorted(MODEL_STUBS)} lets the gateway choose and is refused"
        )
    bare = name.rsplit("/", 1)[-1]
    rate = RATE_CARD.get(bare)
    if rate is None:
        raise ModelNotPriced(
            f"model {name!r} is not on the repair rate card ({sorted(RATE_CARD)}); an "
            "unknown outcome could not be bounded"
        )
    return rate


def unknown_outcome_bound(model: str, *, pixels: int, max_output_tokens: int = OUTPUT_TOKEN_CEILING) -> Decimal:
    """What one call is charged when its outcome is never learned.

    ``max_output_tokens`` at the output rate, plus the pixel-derived image tokens and the
    text allowance at the input rate, rounded up to the journal's scale.
    """
    if pixels < 0 or max_output_tokens < 1:
        raise ValueError("a bound needs a pixel count and an output ceiling")
    rate = rate_for(model)
    input_tokens = math.ceil(pixels / PIXELS_PER_INPUT_TOKEN) + TEXT_INPUT_ALLOWANCE_TOKENS
    usd = (
        Decimal(max_output_tokens) * rate.output_per_mtok_usd
        + Decimal(input_tokens) * rate.input_per_mtok_usd
    ) / Decimal(1_000_000)
    bounded = money(usd)
    return bounded if bounded >= usd else bounded + Decimal("0.000001")
