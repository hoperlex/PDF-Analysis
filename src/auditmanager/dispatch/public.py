"""Cross-context surface of the dispatch boundary (`W61-DISPATCHER-01`).

The composition root serves the commands and the reads from here; nothing else in this
package is reached from outside it (``tests/contract/architecture/test_alr05_boundaries.py``).
"""

from __future__ import annotations

from auditmanager.dispatch.commands import assign_work, transition_assignment
from auditmanager.dispatch.identity import (
    ASSIGNMENT_UID_PATTERN,
    ASSIGNMENT_UID_PREFIX,
    AssignmentUid,
)
from auditmanager.dispatch.policy import (
    AGGREGATE_TYPE,
    CAPABILITY_ASSIGNEE,
    CONFLICT_ASSIGNMENT_OPEN,
    CONSTRAINT_ACTIVE_EXPERT,
    CONSTRAINT_ASSIGNEE_UNCHANGED,
    EVENT_KINDS,
    MACHINE,
    MAX_NOTE_LENGTH,
    MAX_REASON_LENGTH,
    OPEN_STATUSES,
    STATUSES,
    TERMINAL_STATUSES,
    TRANSITION_KINDS,
)
from auditmanager.dispatch.queries import AssignmentDetail, get_assignment, list_assignments
from auditmanager.dispatch.repository import AssignmentEvent, AssignmentRecord

__all__ = [
    "AGGREGATE_TYPE",
    "ASSIGNMENT_UID_PATTERN",
    "ASSIGNMENT_UID_PREFIX",
    "CAPABILITY_ASSIGNEE",
    "CONFLICT_ASSIGNMENT_OPEN",
    "CONSTRAINT_ACTIVE_EXPERT",
    "CONSTRAINT_ASSIGNEE_UNCHANGED",
    "EVENT_KINDS",
    "MACHINE",
    "MAX_NOTE_LENGTH",
    "MAX_REASON_LENGTH",
    "OPEN_STATUSES",
    "STATUSES",
    "TERMINAL_STATUSES",
    "TRANSITION_KINDS",
    "AssignmentDetail",
    "AssignmentEvent",
    "AssignmentRecord",
    "AssignmentUid",
    "assign_work",
    "get_assignment",
    "list_assignments",
    "transition_assignment",
]
