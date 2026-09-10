"""The ``OD-24`` scope note: every part of the ``audit_run`` contract PC-01 does not evaluate.

PC-01 uses the contract's state names and its transition topology, and claims no more
than that. This module records the **complete** unevaluated subset rather than a count,
because a partial list reads as a smaller claim than the one actually being made.

It is data, not documentation: a test reads it, so the note cannot quietly fall out of
step with what the executor does. It is also the answer to "which guards did you skip?"
that a reviewer can diff between releases.

Note the distinction the task draws and this module preserves. An **unevaluated guard**
is a clause of a declared transition guard that PC-01 does not check. An **absent
capability** is a thing PC-01 does not have at all. Cancellation and Attempt publication
authority are the second kind, and folding them into the first would misdescribe both.
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


#: The four unevaluated clauses. Complete: there is no fifth, and the count is derived
#: from this tuple rather than written beside it.
UNEVALUATED_GUARDS: Final[tuple[UnevaluatedGuard, ...]] = (
    UnevaluatedGuard(
        transition="created -> queued",
        clause="the NormsSnapshot clause of the reference-resolution guard",
        reason=(
            "PC-01 pins no norms snapshot; audit_run.norms_snapshot_id is written NULL "
            "and read by no PC-01 path. The input-manifest, AnalysisProfile and "
            "PromptBundle clauses of this same guard ARE evaluated."
        ),
    ),
    UnevaluatedGuard(
        transition="queued -> running",
        clause="the whole guard",
        reason=(
            "it requires a Job to exist and its current Attempt to hold the execution "
            "token. PC-01 has no Job, no Attempt and no token, and therefore no "
            "producer for execution_token_invalid."
        ),
    ),
    UnevaluatedGuard(
        transition="running -> validating",
        clause="the whole guard",
        reason=(
            "it requires every delivered result to come from the current Attempt. "
            "PC-01 runs one execution in one process, so there is no second attempt a "
            "result could come from, and no producer for stale_attempt."
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
    "cancellation: no cancel command exists, so the terminal 'cancelled' is declared "
    "by the topology and unreachable in PC-01",
    "Attempt publication authority: there is no Job, no Attempt and no execution token "
    "for authority to be held by or lost from",
)

#: Schemas this module makes no conformance claim to, per C-3. PC-01 constructs neither:
#: both envelopes carry attempt authority because they exist to cross a remote-dispatch
#: boundary, and PC-01 does not dispatch remotely.
SCHEMAS_NOT_CLAIMED: Final[tuple[str, ...]] = ("JobPackage", "ResultPackage")

#: Aggregates PC-01 does not instantiate (P02 §3.1). A test asserts the tables' absence.
AGGREGATES_NOT_INSTANTIATED: Final[tuple[str, ...]] = (
    "job",
    "attempt",
    "lease",
    "import",
    "export",
    "worker",
    "comparison",
    "norms_snapshot",
    "outbox",
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
