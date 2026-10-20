"""Cross-context surface of the decisions boundary.

Everything the package root exports, plus the batch projections and the confirmed
carryover command (`W59-DECISION-CARRYOVER-01`) that the comparison context calls. A
context outside ``decisions`` imports from here (ALR-05), never from a module beside it.
"""

from __future__ import annotations

from auditmanager.decisions import (
    COMMAND_TYPE_APPEND_DECISION,
    DECLARED_EVENT_TYPES,
    PC01_EVENT_TYPES,
    VERDICT_FOR_EVENT,
    CurrentVerdict,
    DecisionEvent,
    JournalEntry,
    append_decision_under_key,
    current_verdict,
    decision_history,
    decision_journal,
    rebuild_current_verdict,
    record_decision,
)
from auditmanager.decisions.carryover import (
    CARRIED_EVENT_FOR_VERDICT,
    CARRYOVER_COMMAND_TYPE,
    CARRYOVER_CONFLICT_REASONS,
    CARRYOVER_MODES,
    CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED,
    CONFLICT_CARRYOVER_SEVERITY_NOT_CARRYABLE,
    CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT,
    CONFLICT_CARRYOVER_TARGET_ALREADY_DECIDED,
    CarriedDecision,
    CarryoverProvenance,
    carry_over_decision,
    carryover_comment,
)
from auditmanager.decisions.ledger import decision_events_by_id
from auditmanager.decisions.projection import current_verdicts

__all__ = [
    "CARRIED_EVENT_FOR_VERDICT",
    "CARRYOVER_COMMAND_TYPE",
    "CARRYOVER_CONFLICT_REASONS",
    "CARRYOVER_MODES",
    "COMMAND_TYPE_APPEND_DECISION",
    "CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED",
    "CONFLICT_CARRYOVER_SEVERITY_NOT_CARRYABLE",
    "CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT",
    "CONFLICT_CARRYOVER_TARGET_ALREADY_DECIDED",
    "CarriedDecision",
    "CarryoverProvenance",
    "CurrentVerdict",
    "DECLARED_EVENT_TYPES",
    "DecisionEvent",
    "JournalEntry",
    "PC01_EVENT_TYPES",
    "VERDICT_FOR_EVENT",
    "append_decision_under_key",
    "carry_over_decision",
    "carryover_comment",
    "current_verdict",
    "current_verdicts",
    "decision_events_by_id",
    "decision_history",
    "decision_journal",
    "rebuild_current_verdict",
    "record_decision",
]
