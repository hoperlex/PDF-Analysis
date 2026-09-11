"""The append-only expert decision ledger and the current-verdict projection.

Every expert judgement is a new event; nothing is ever updated or removed, and the
current verdict is read from ``finding_current_verdict`` — a view, so the projection is
rebuildable by construction. The model never writes a verdict.
"""

from auditmanager.decisions.ledger import (
    CONFIGURED_AUTHOR_LABEL,
    DECLARED_EVENT_TYPES,
    PC01_EVENT_TYPES,
    VERDICT_FOR_EVENT,
    DecisionEvent,
    decision_history,
    COMMAND_TYPE_APPEND_DECISION,
    append_decision_under_key,
    record_decision,
)
from auditmanager.decisions.projection import (
    CurrentVerdict,
    current_verdict,
    rebuild_current_verdict,
)

__all__ = [
    "CONFIGURED_AUTHOR_LABEL",
    "DECLARED_EVENT_TYPES",
    "PC01_EVENT_TYPES",
    "VERDICT_FOR_EVENT",
    "CurrentVerdict",
    "DecisionEvent",
    "current_verdict",
    "decision_history",
    "rebuild_current_verdict",
    "COMMAND_TYPE_APPEND_DECISION",
    "append_decision_under_key",
    "record_decision",
]
