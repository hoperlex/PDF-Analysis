"""The selection rule of the executor-context policy (`plan-v5` 3.5): window order, at most 3 cases per candidate, 12 000 characters, then a line.

The caller gives the candidates in the critic window's order, each with its cases already ranked best first and each case already rendered
to the text that would go to the model (the separators included; the budget counts ``len(text)``). The selection is a strict prefix of
that order: the first case that does not fit ends it, so a later, smaller case never jumps ahead of an earlier one. Everything after the
cut, within the three-per-candidate cap, is counted in «не уместилось: N». The line is paid for out of the budget, so the selection plus
the line never exceeds ``max_characters``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

MAX_CASES_PER_ENTRY: Final[int] = 3
MAX_CHARACTERS: Final[int] = 12_000


def not_fitted_line(count: int) -> str:
    return f"не уместилось: {count}"


@dataclass(frozen=True, slots=True)
class BudgetCase:
    """One rendered case: its identity and the exact text that would be sent."""

    case_id: str
    text: str


@dataclass(frozen=True, slots=True)
class BudgetEntry:
    """One candidate of the window (``input_id``) with its ranked cases."""

    input_id: str
    cases: tuple[BudgetCase, ...]


@dataclass(frozen=True, slots=True)
class SelectedEntry:
    input_id: str
    cases: tuple[BudgetCase, ...]


@dataclass(frozen=True, slots=True)
class BudgetSelection:
    """The chosen cases per candidate, in window order (a candidate with nothing chosen is kept, with no cases).

    ``not_fitted`` counts the cases cut by the budget; ``over_cap`` counts the cases beyond three per candidate, which are by design never
    sent and are not part of the line.
    """

    entries: tuple[SelectedEntry, ...]
    characters_used: int
    not_fitted: int
    over_cap: int

    @property
    def line(self) -> str | None:
        return not_fitted_line(self.not_fitted) if self.not_fitted else None

    @property
    def characters_total(self) -> int:
        return self.characters_used + (len(self.line) if self.line else 0)


def _fill(capped: Sequence[tuple[str, tuple[BudgetCase, ...]]], budget: int) -> tuple[list[SelectedEntry], int, int]:
    selected: list[SelectedEntry] = []
    used = 0
    dropped = 0
    stopped = False
    for input_id, cases in capped:
        taken: list[BudgetCase] = []
        for case in cases:
            if stopped or used + len(case.text) > budget:
                stopped = True
                dropped += 1
            else:
                taken.append(case)
                used += len(case.text)
        selected.append(SelectedEntry(input_id=input_id, cases=tuple(taken)))
    return selected, used, dropped


def select_within_budget(
    entries: Sequence[BudgetEntry],
    *,
    max_cases_per_entry: int = MAX_CASES_PER_ENTRY,
    max_characters: int = MAX_CHARACTERS,
) -> BudgetSelection:
    if max_cases_per_entry < 1 or max_characters < 0:
        raise ValueError("max_cases_per_entry must be at least 1 and max_characters not negative")
    capped = [(entry.input_id, entry.cases[:max_cases_per_entry]) for entry in entries]
    over_cap = sum(max(0, len(entry.cases) - max_cases_per_entry) for entry in entries)

    selected, used, dropped = _fill(capped, max_characters)
    if dropped:
        reserve = len(not_fitted_line(sum(len(cases) for _, cases in capped)))
        selected, used, dropped = _fill(capped, max(0, max_characters - reserve))
    return BudgetSelection(entries=tuple(selected), characters_used=used, not_fitted=dropped, over_cap=over_cap)
