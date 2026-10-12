"""The ``OD-24`` scope note: every part of the ``audit_run`` contract PC-01 does not evaluate.

PC-01 uses the contract's state names and its transition topology, and claims no more
than that. This module records the **complete** unevaluated subset rather than a count,
because a partial list reads as a smaller claim than the one actually being made.

It is data, not documentation: a test reads it, so the note cannot quietly fall out of
step with what the executor does. It is also the answer to "which guards did you skip?"
that a reviewer can diff between releases.

Note the distinction the task draws and this module preserves. An **unevaluated guard**
is a clause of a declared transition guard that the alpha runner does not check. An
**absent capability** is a thing it does not have at all. W48-DURABLE-01 made
Job/Attempt publication authority executable and W53 added ``cancel_audit_run``, so
neither is in either list any more; what stays absent is remote execution and the
cancellation of a run that has already reached ``validating``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class UnevaluatedGuard:
    """One guard clause PC-01 declares it does not evaluate, and why."""

    transition: str
    clause: str
    reason: str


#: The two unevaluated clauses. Complete: there is no third, and the count is derived
#: from this tuple rather than written beside it.
UNEVALUATED_GUARDS: Final[tuple[UnevaluatedGuard, ...]] = (
    UnevaluatedGuard(
        transition="created -> queued",
        clause="the NormsSnapshot clause of the reference-resolution guard",
        reason=(
            "a run pins the current norms snapshot at creation (W55A-PIN-01), so a "
            "pinned snapshot resolves by construction, but a NULL pin -- written while "
            "no snapshot is current -- is admitted and no stage reads the pin before "
            "W57 (CD-6). The input-manifest, AnalysisProfile and PromptBundle clauses "
            "of this same guard ARE evaluated."
        ),
    ),
    UnevaluatedGuard(
        transition="validating -> published",
        clause="the ResultPackage schema clause",
        reason=(
            "PC-01 publishes no result package. It validates declared checksums and "
            "required artifact roles directly instead, through the stage runner's "
            "required-output guard and the artifact envelope check."
        ),
    ),
)

#: Not guards left unevaluated — capabilities PC-01 does not have. Recorded separately
#: and deliberately not merged into ``UNEVALUATED_GUARDS``.
ABSENT_CAPABILITIES: Final[tuple[str, ...]] = (
    (
        "remote execution: the worker service (R-105) runs on the API's host from the "
        "API's image against the one database; no remote worker, remote queue or "
        "JobPackage/ResultPackage transport exists"
    ),
    (
        "cancellation after validating: cancel_audit_run fences created, queued and "
        "running runs only, so the terminal 'cancelled' is unreachable from validating"
    ),
)

#: Schemas this module makes no conformance claim to, per C-3. PC-01 constructs neither:
#: both envelopes exist to cross a remote-dispatch boundary. The local executor now has
#: Attempt authority, but still does not claim either remote transport envelope.
SCHEMAS_NOT_CLAIMED: Final[tuple[str, ...]] = ("JobPackage", "ResultPackage")

#: Aggregates the alpha runner still does not instantiate (P02 §3.1). `W54-SEAL-01` removed
#: two: migration ``0019`` instantiates the ``worker`` registry (R-105), and migration
#: ``0018``'s ``norm_custody_admission`` is the custody outbox (R-76: the intent and its
#: outbox row are one record), so neither is absent any more. What a worker process *does*
#: was absent until `W54-WORKER-01`, which added the local worker service; remote workers
#: remain absent and :data:`ABSENT_CAPABILITIES` says so.
AGGREGATES_NOT_INSTANTIATED: Final[tuple[str, ...]] = (
    "import",
    "export",
    "comparison",
)

#: ``OD-10``: the vocabulary a stale ``running`` run reconciles into. There is no
#: ``interrupted`` state — the contract declares none, so none is invented. The run
#: moves to the declared terminal ``failed`` and the *reason* carries the interruption.
RECONCILIATION_TERMINAL: Final[str] = "failed"


__all__ = [
    "ABSENT_CAPABILITIES",
    "AGGREGATES_NOT_INSTANTIATED",
    "RECONCILIATION_TERMINAL",
    "SCHEMAS_NOT_CLAIMED",
    "UNEVALUATED_GUARDS",
    "UnevaluatedGuard",
]
