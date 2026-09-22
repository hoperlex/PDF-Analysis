"""The append-only expert decision ledger and the projections read over it.

Every expert judgement is a new event; nothing is ever updated or removed, and the
current verdict is read from ``finding_current_verdict`` — a view, so the projection is
rebuildable by construction. The model never writes a verdict.

Three reads, three questions. ``decision_history`` answers *what was decided about this
finding*; ``current_verdict`` answers *what stands for it now*; ``decision_journal``
answers *what has been decided*, across every finding, which is what the knowledge base
is a view of. All three are projections over the one event stream.
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
from auditmanager.decisions.journal import JournalEntry, decision_journal
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
    "JournalEntry",
    "current_verdict",
    "decision_history",
    "decision_journal",
    "rebuild_current_verdict",
    "COMMAND_TYPE_APPEND_DECISION",
    "append_decision_under_key",
    "record_decision",
]
