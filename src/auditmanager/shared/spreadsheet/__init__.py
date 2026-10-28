"""Spreadsheet-safe text for the files this system writes: the one rule against formula injection.

A CSV is opened in a spreadsheet, and a text cell that the spreadsheet reads as the start of a formula
is run, not shown. The text of a cell can come from a client's document or from a model, so a writer
neutralises it. The rule lives here, once, and is a function of one string; each writer decides which
of its cells are text and keeps its own byte format.
"""

from auditmanager.shared.spreadsheet.formula_text import (
    CONTROL_STARTERS,
    FORMULA_NEUTRALISER,
    FORMULA_TRIGGERS,
    LEADING_SKIPPED,
    neutralise_formula,
)

__all__ = [
    "CONTROL_STARTERS",
    "FORMULA_NEUTRALISER",
    "FORMULA_TRIGGERS",
    "LEADING_SKIPPED",
    "neutralise_formula",
]
