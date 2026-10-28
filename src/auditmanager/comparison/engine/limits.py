"""The numbers of the engine, each with the decision that sets it.

`CMP-ENGINE-01`. ADR-0025 decision 8 (the ceilings of the child), decision 9 (the 40 Mpx cap and the mask), decision 15
(the key). The thresholds of the comparison itself, with the line of the original that sets each, are in
:mod:`.child.settings`; this module restates what the worker's side needs.
"""

from __future__ import annotations

from typing import Final

from auditmanager.comparison.engine.child.settings import ALGO_VERSION, PARAMS, TOLERANCE_PT
from auditmanager.comparison.engine.child.status import FORCING_REASONS, ORIGINAL_FORCING_REASONS, OWN_FORCING_REASONS
from auditmanager.comparison.profile.limits import MIB, PIXEL_CAP, ChildLimits

__all__ = [
    "ALGO_VERSION",
    "CHILD_LIMITS",
    "FORCING_REASONS",
    "ORIGINAL_FORCING_REASONS",
    "OWN_FORCING_REASONS",
    "PARAMS",
    "PAIR_WORK_KIND",
    "PIXEL_CAP",
    "REASON_RENDER_FAILED",
    "ROLE_PAIR_MASK",
    "TOLERANCE_PT",
]

#: ADR-0025 decision 8 and its addendum: 768 MiB of address space, 300 s of CPU, 600 s of wall (below the 900 s
#: attempt watchdog of the queue). An end without a result is ``RENDER_FAILED`` for that pair only.
CHILD_LIMITS: Final[ChildLimits] = ChildLimits(768 * MIB, 300, 600.0)
REASON_RENDER_FAILED: Final[str] = "RENDER_FAILED"
#: The kind of the work item that computes one pair (the wave brief section 4 item 4).
PAIR_WORK_KIND: Final[str] = "pair_result"
#: The role of the mask blob in the blob journal.
ROLE_PAIR_MASK: Final[str] = "comparison_pair_mask"
