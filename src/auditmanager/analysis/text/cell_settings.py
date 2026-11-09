"""One cell of a run's stage plan, as the analysis code reads it (`HOSTS-LAYOUT-01`, ADR-0028 decisions 5, 10, 12).

A cell is « row · role »: the model, the reasoning effort, the answer limit and the timeout one phase of a section analysis runs
with. The analysis builders take it as an optional ``settings`` argument and, with ``None``, build the request they always built,
byte for byte: the constants below are the answer limits and the effort that were code constants before the layout existed, and the
defaults of the layout's « Дополнительно » fields.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Final, Mapping

__all__ = [
    "CellSettings", "DEFAULT_EFFORT", "DEFAULT_TIMEOUT_SECONDS", "ROW_DEFAULT_MAX_OUTPUT_TOKENS", "apply_to_bundle", "apply_to_body",
    "effort_of", "limit_of",
]

#: The effort every hard-coded builder asked for before the layout (``"effort": "high"``).
DEFAULT_EFFORT: Final[str] = "high"

#: The answer limit, in tokens, that each row's calls carried as a code constant: ``analysis/text/prompt.py`` ``MAX_OUTPUT_TOKENS`` for
#: the text analysis, 6000 for the block and the comprehensive requests (``analysis/extended/core.py``, ``workflow.py``,
#: ``cross_window_review.py``), 12000 for the norm review (``workflow.py``) and for the critic and the corrector (``review.py``).
ROW_DEFAULT_MAX_OUTPUT_TOKENS: Final[Mapping[str, int]] = {
    "text": 16_000, "blocks": 6_000, "cross_check": 6_000, "norms": 12_000, "review": 12_000, "correction": 12_000,
}

#: The response window of one call when the layout says nothing else. There was no per-call constant for a host: a connection's own
#: ``answer_deadline_seconds`` (10 to 3600) bounded it. The wire allows 1 to 7200 (the attempt ceiling); this is half an hour.
DEFAULT_TIMEOUT_SECONDS: Final[int] = 1_800


@dataclass(frozen=True, slots=True)
class CellSettings:
    cell_key: str
    model_id: str
    effort: str
    max_output_tokens: int
    timeout_seconds: int
    #: ``subscription`` or ``api``, chosen when the run started and frozen with the plan; ``None`` in a layout (not yet a plan).
    access: str | None = None

    @property
    def row(self) -> str:
        return self.cell_key.partition(":")[0]

    @property
    def role(self) -> str:
        return self.cell_key.partition(":")[2]


def effort_of(settings: CellSettings | None, default: str = DEFAULT_EFFORT) -> str:
    return default if settings is None else settings.effort


def limit_of(settings: CellSettings | None, default: int) -> int:
    return default if settings is None else settings.max_output_tokens


def apply_to_body(body: Mapping[str, Any], settings: CellSettings | None) -> dict[str, Any]:
    """A copy of a request body with the cell's answer limit and effort. ``None`` is a plain copy, so a caller needs no branch."""
    result = dict(body)
    if settings is None:
        return result
    result["max_tokens"] = settings.max_output_tokens
    output_config = dict(result.get("output_config") or {})
    output_config["effort"] = settings.effort
    result["output_config"] = output_config
    return result


def apply_to_bundle(bundle: Any, settings: CellSettings | None) -> Any:
    """The prompt bundle with the cell's limit and effort (the text analysis reads both from its bundle). ``None`` returns it as is."""
    if settings is None:
        return bundle
    return replace(bundle, max_output_tokens=settings.max_output_tokens, effort=settings.effort)
