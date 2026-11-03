"""The deployment's intake mode: the one place that reads ``AUDITMANAGER_INTAKE_RELAXED``.

`REVIEW-FIX-BOUNDS-1102`. The numeric intake quotas of ADR-0025 (file, page, set, batch and
project counts and bytes, drawing-element and character ceilings, block counts) apply unless
the deployment sets ``AUDITMANAGER_INTAKE_RELAXED=1``; then they take the temporary
"statistics" values that ``af581631`` introduced. The flag is read once, when a module that
declares a quota is imported, so one process holds one mode and a restart changes it.

The flag moves **quotas only**. The sandbox never moves: the reader's address space and clock,
the PDF precheck child's limits, a ZIP's compression ratio, per-member and total uncompressed
size, the free-disk reservation and the proxy's body limit and timeouts are finite in both
modes. A quota that must stay finite in both modes is written as a plain constant, never
through :func:`quota`.
"""

from __future__ import annotations

import os
from typing import Final

__all__ = ["RELAXED_ENV", "intake_relaxed", "quota"]

RELAXED_ENV: Final[str] = "AUDITMANAGER_INTAKE_RELAXED"

_OFF: Final[frozenset[str]] = frozenset({"", "0", "false", "off"})
_ON: Final[frozenset[str]] = frozenset({"1", "true", "on"})


def intake_relaxed() -> bool:
    """Whether this deployment lifts the intake quotas; ``False`` unless the flag is set to 1.

    A value that is neither on nor off is refused rather than read as one of them: a typo in a
    deployment file must not silently decide which quotas apply.
    """
    value = os.environ.get(RELAXED_ENV, "0").strip().lower()
    if value in _OFF:
        return False
    if value in _ON:
        return True
    raise ValueError(f"{RELAXED_ENV} must be 0 or 1")


def quota(default: int, relaxed: int) -> int:
    """The ADR figure ``default``, or the lifted ``relaxed`` figure when the deployment is relaxed."""
    return relaxed if intake_relaxed() else default
