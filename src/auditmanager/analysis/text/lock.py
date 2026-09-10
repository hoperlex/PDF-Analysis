"""The pinned provider facts, read from ``docs/program/P02_LOCK.json``.

Nothing here restates a model identifier or a rate. ``B-0`` owns the lock and is the
sole writer of it; this module is the only place in ``analysis.text`` that reads it,
so a rate change is a lock edit and never a code edit.

The lock is a repository document, not packaged data. It is located relative to this
file because ``pyproject.toml`` declares ``package = false``: the tree under ``src/``
is reached through ``PYTHONPATH=src`` or the pytest ``pythonpath`` setting, never
installed, so ``__file__`` is always inside the checkout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Mapping

from auditmanager.shared.errors import DomainError, ErrorCode

#: ``src/auditmanager/analysis/text/lock.py`` -> repository root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
_LOCK_RELPATH: Final[str] = "docs/program/P02_LOCK.json"

#: The canonical stage identity, as the analysis stage registry spells it.
STAGE_ID: Final[str] = "text_analysis"


@dataclass(frozen=True, slots=True)
class ModelPin:
    """One model identity and its rates, exactly as the lock records them."""

    model_id: str
    input_per_mtok_usd: float
    output_per_mtok_usd: float

    def cost_usd(self, *, input_tokens: int, output_tokens: int) -> float:
        """Measured cost for one call, in USD.

        The lock records two rates per model and no separate cache rate, so a caller
        holding cache-read or cache-write tokens folds them into ``input_tokens``.
        Inventing a third rate here would put a number in the code that the lock does
        not carry, which is the thing this module exists to prevent.
        """
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must not be negative")
        return (
            input_tokens * self.input_per_mtok_usd + output_tokens * self.output_per_mtok_usd
        ) / 1_000_000.0


@dataclass(frozen=True, slots=True)
class ProviderLock:
    """The subset of ``P02_LOCK.json`` this stage is entitled to read."""

    sdk_version: str
    models: Mapping[str, ModelPin]
    primary_model_id: str

    def model(self, model_id: str) -> ModelPin:
        """The pin for ``model_id``.

        An unpinned model identifier is a configuration error, not a provider
        outage: the lock is the closed set of models this stage may call.
        """
        try:
            return self.models[model_id]
        except KeyError:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="the requested model identity is not one the P02 lock pins",
                stage_id=STAGE_ID,
                reason="model_not_pinned",
            ) from None


def _read_lock_document(lock_path: Path) -> Mapping[str, Any]:
    try:
        raw = lock_path.read_text(encoding="utf-8")
    except OSError:
        # The message names no path: the envelope screen forbids one, and an operator
        # who needs the location reads it from this module's docstring.
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            message="the P02 provider lock document could not be read",
        ) from None
    return json.loads(raw)


def load_provider_lock(lock_path: Path | None = None) -> ProviderLock:
    """Read the lock. ``lock_path`` exists so a test can point at a variant."""
    document = _read_lock_document(lock_path or (_REPO_ROOT / _LOCK_RELPATH))
    models_block = document["models"]
    pins: dict[str, ModelPin] = {}
    primary: str | None = None
    for tier, entry in models_block.items():
        if not isinstance(entry, dict) or "model_id" not in entry:
            continue  # "$comment" and any future annotation key
        pins[entry["model_id"]] = ModelPin(
            model_id=entry["model_id"],
            input_per_mtok_usd=float(entry["input_per_mtok_usd"]),
            output_per_mtok_usd=float(entry["output_per_mtok_usd"]),
        )
        if tier == "primary":
            primary = entry["model_id"]
    if primary is None:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            message="the P02 provider lock declares no primary model",
        )
    return ProviderLock(
        sdk_version=str(document["pins"]["anthropic"]["version"]),
        models=pins,
        primary_model_id=primary,
    )


@lru_cache(maxsize=1)
def provider_lock() -> ProviderLock:
    """The repository's lock, read once per process."""
    return load_provider_lock()
