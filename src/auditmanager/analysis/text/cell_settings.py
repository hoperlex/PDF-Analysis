"""One cell of a run's stage plan, as the analysis code reads it (`HOSTS-LAYOUT-01`, ADR-0028 decisions 5, 10, 12; `LIMITS-01`).

A cell is « row · role »: the model and the reasoning effort one phase of a section analysis runs with, and, once a run has started, the access
it is served by. Since `LIMITS-01` (owner rulings `R-153n` and `R-153o`) a cell carries **no answer limit and no timeout of its own**:

* **No answer cap reaches a model.** The old « Ответ, токенов » setting is gone. :data:`ROW_ESTIMATE_OUTPUT_TOKENS` is a figure for the
  cost estimate only (what a call of the row is priced to answer at most, the ``max_tokens`` of the request body that is hashed, priced and
  journalled); no host call, no agent and no provider receives it as a cap (`HOTFIX-RUN-PARTIAL-1106`: « response-token figures are estimates,
  not output caps »).
* **A stage call's timeout is a code constant of its row** (:data:`ROW_TIMEOUT_SECONDS`), from the original (``PDF-proverka``
  ``backend/app/core/config.py``), and of a comparison kind (:data:`COMPARISON_TIMEOUT_SECONDS`). Nobody edits it. The attempt watchdog still
  cuts a call's window to what it leaves (``executors.pull.answer_window``).

The analysis builders take a cell as an optional ``settings`` argument and, with ``None``, build the request they always built, byte for byte.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Final, Mapping

__all__ = [
    "CellSettings", "COMPARISON_TIMEOUT_SECONDS", "DEFAULT_EFFORT", "ROW_ESTIMATE_OUTPUT_TOKENS", "ROW_TIMEOUT_SECONDS", "apply_to_bundle",
    "apply_to_body", "effort_of", "limit_of",
]

#: The effort every hard-coded builder asked for before the layout (``"effort": "high"``).
DEFAULT_EFFORT: Final[str] = "high"

#: The figure each row's calls are **priced** at, in output tokens -- an estimate, never a cap: ``analysis/text/prompt.py``
#: ``MAX_OUTPUT_TOKENS`` for the text analysis, 6000 for the block and the comprehensive requests (``analysis/extended/core.py``,
#: ``workflow.py``, ``cross_window_review.py``), 12000 for the norm review (``workflow.py``) and for the critic and the corrector
#: (``review.py``). It is the ``max_tokens`` of the request body and the output side of the cost estimate; the host task carries none.
ROW_ESTIMATE_OUTPUT_TOKENS: Final[Mapping[str, int]] = {
    "text": 16_000, "blocks": 6_000, "cross_check": 6_000, "norms": 12_000, "review": 12_000, "correction": 12_000,
}

#: The call window of one stage call, in seconds, per row (`R-153o`: « как в оригинале, в коде »). The original's totals
#: (``PDF-proverka/backend/app/core/config.py:214-232``): the text analysis ``CLAUDE_TEXT_ANALYSIS_TIMEOUT`` 1800; the blocks
#: ``CLAUDE_BLOCK_ANALYSIS_TIMEOUT`` 1800 (our call is a window of blocks, and a leg or the judge takes the row's value); the comprehensive
#: check ``CLAUDE_FINDINGS_MERGE_TIMEOUT`` 3600 (raised after the merge was killed twice at 1801 s with its work lost); the norms
#: ``CLAUDE_NORM_VERIFY_TIMEOUT`` 600; the critic ``CLAUDE_OPTIMIZATION_CRITIC_TIMEOUT`` 600; the refinement
#: ``CLAUDE_OPTIMIZATION_CORRECTOR_TIMEOUT`` 600. Each is cut to what the attempt watchdog leaves; the 7200 s hard cap of an attempt
#: (``jobs/lease.py``) is unchanged.
ROW_TIMEOUT_SECONDS: Final[Mapping[str, int]] = {
    "text": 1_800, "blocks": 1_800, "cross_check": 3_600, "norms": 600, "review": 600, "correction": 600,
}

#: The call window of each kind of comparison work, as the original sets it (``version_comparison_ai``: ``sheet_match`` 900 s, ``VC_SC``
#: 1800 s, the whole specification 900 s, ``VC_MR`` 2400 s). Constants nobody edits, like the rows'.
COMPARISON_TIMEOUT_SECONDS: Final[Mapping[str, int]] = {
    "comparison_pair_check": 900, "comparison_sheet_changes": 1_800, "comparison_spec": 900, "comparison_report": 2_400,
}


@dataclass(frozen=True, slots=True)
class CellSettings:
    """The model and the effort of one cell, and its access once a run has frozen it. The limits are derived, never stored: see the module
    docstring."""

    cell_key: str
    model_id: str
    effort: str
    #: ``subscription`` or ``api``, chosen when the run started and frozen with the plan; ``None`` in a layout (not yet a plan).
    access: str | None = None

    @property
    def row(self) -> str:
        return self.cell_key.partition(":")[0]

    @property
    def role(self) -> str:
        return self.cell_key.partition(":")[2]

    @property
    def timeout_seconds(self) -> int:
        """The call window of this cell: the constant of its row or of its comparison kind. A value an old layout revision or a frozen plan
        stored for the cell is **not read** (``R-153o``); a key that is neither a row nor a kind is refused, not given a default."""
        window = ROW_TIMEOUT_SECONDS.get(self.row, COMPARISON_TIMEOUT_SECONDS.get(self.row))
        if window is None:
            raise ValueError(f"cell {self.cell_key!r} has no timeout: its row is neither a stage row nor a comparison kind")
        return window

    @property
    def estimate_output_tokens(self) -> int:
        """The output figure the cost estimate prices a call of this cell at (:data:`ROW_ESTIMATE_OUTPUT_TOKENS`). It is **not a limit** and
        no call carries it. A comparison cell has none: the estimate counts the figure of the comparison module that makes the call."""
        figure = ROW_ESTIMATE_OUTPUT_TOKENS.get(self.row)
        if figure is None:
            raise ValueError(f"cell {self.cell_key!r} has no estimate figure: it is not a stage row")
        return figure


def effort_of(settings: CellSettings | None, default: str = DEFAULT_EFFORT) -> str:
    return default if settings is None else settings.effort


def limit_of(settings: CellSettings | None, default: int) -> int:
    """The ``max_tokens`` figure of a builder's request body: always the builder's own ``default``. A cell has no answer limit (``R-153n``);
    ``settings`` is accepted so the builders of ``analysis/extended`` keep one call shape. The figure is what the request is hashed and priced
    at -- an estimate -- and the host task that serves the request carries no cap."""
    return default


def apply_to_body(body: Mapping[str, Any], settings: CellSettings | None) -> dict[str, Any]:
    """A copy of a request body with the cell's effort. ``None`` is a plain copy, so a caller needs no branch. The body's ``max_tokens`` is left
    as the builder wrote it: an estimate figure, not a cap."""
    result = dict(body)
    if settings is None:
        return result
    output_config = dict(result.get("output_config") or {})
    output_config["effort"] = settings.effort
    result["output_config"] = output_config
    return result


def apply_to_bundle(bundle: Any, settings: CellSettings | None) -> Any:
    """The prompt bundle with the cell's effort (the text analysis reads it from its bundle). ``None`` returns it as is. The bundle's
    ``max_output_tokens`` becomes the row's estimate figure, as it always was for a planned run: it prices the call and is not sent as a cap."""
    if settings is None:
        return bundle
    return replace(bundle, max_output_tokens=settings.estimate_output_tokens, effort=settings.effort)
