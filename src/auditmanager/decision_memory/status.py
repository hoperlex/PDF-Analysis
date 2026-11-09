"""The standing of a case: active, withdrawn or forgotten (`DECISION-MEMORY-01` section 3.7, `ADR-0027` decision 5).

A case is never edited. Its standing is the latest of its **status events**: ``withdraw`` (reversible: the case leaves hints, prompts and
exports), ``restore`` (undoes a withdraw) and ``forget`` (terminal: the operator tool removed the content; the case keeps a tombstone).
No event means ``active``. This module is the rule and only the rule -- pure values, no database -- so the application service, the
operator tool and the migration's own guard (``am_guard_decision_memory_status``, which repeats it where it cannot be bypassed) can be
compared against one statement of it.

====================  ===========  ==========  =========
current \\ requested   withdraw     restore     forget
====================  ===========  ==========  =========
active                withdrawn    refused     forgotten
withdrawn             refused      active      forgotten
forgotten             refused      refused     refused
====================  ===========  ==========  =========

A refusal is ``state_transition_not_allowed`` (the case is already in that state), or ``conflict`` with ``conflict_reason:
memory_case_forgotten`` when the case is forgotten and so accepts nothing.
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

#: The machine name carried by ``state_transition_not_allowed``.
CASE_MACHINE: Final[str] = "decision_memory_case"

STATUS_ACTIVE: Final[str] = "active"
STATUS_WITHDRAWN: Final[str] = "withdrawn"
STATUS_FORGOTTEN: Final[str] = "forgotten"
CASE_STATUSES: Final[tuple[str, ...]] = (STATUS_ACTIVE, STATUS_WITHDRAWN, STATUS_FORGOTTEN)

KIND_WITHDRAW: Final[str] = "withdraw"
KIND_RESTORE: Final[str] = "restore"
KIND_FORGET: Final[str] = "forget"
STATUS_KINDS: Final[tuple[str, ...]] = (KIND_WITHDRAW, KIND_RESTORE, KIND_FORGET)

#: The closed reasons of a status event (`ADR-0022` §3 gives the reason why there is no free text: it would put personal data into an
#: append-only table). Mirrors ``ck_decision_memory_status_event_reason_code``.
STATUS_REASON_CODES: Final[tuple[str, ...]] = ("capture_defect", "wrong_decision", "client_request", "test_data", "other")

#: ``conflict_reason`` of the refusal of any event on a forgotten case.
CONFLICT_CASE_FORGOTTEN: Final[str] = "memory_case_forgotten"

_STATUS_AFTER: Final[dict[str, str]] = {KIND_WITHDRAW: STATUS_WITHDRAWN, KIND_RESTORE: STATUS_ACTIVE, KIND_FORGET: STATUS_FORGOTTEN}
_ALLOWED_FROM: Final[dict[str, frozenset[str]]] = {
    KIND_WITHDRAW: frozenset({STATUS_ACTIVE}),
    KIND_RESTORE: frozenset({STATUS_WITHDRAWN}),
    KIND_FORGET: frozenset({STATUS_ACTIVE, STATUS_WITHDRAWN}),
}


def status_after_events(last_kind: str | None) -> str:
    """The standing of a case whose latest status event is ``last_kind`` (``None``: no event, so active)."""
    if last_kind is None:
        return STATUS_ACTIVE
    try:
        return _STATUS_AFTER[last_kind]
    except KeyError:
        raise ValueError(f"{last_kind!r} is not a decision-memory status event kind") from None


def check_reason(reason_code: str) -> str:
    if reason_code not in STATUS_REASON_CODES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="reason_code", constraint="enum")
    return reason_code


def next_status(current: str, kind: str) -> str:
    """The standing after ``kind`` is applied to ``current``, or the refusal."""
    if kind not in _ALLOWED_FROM:
        raise ValueError(f"{kind!r} is not a decision-memory status event kind")
    if current == STATUS_FORGOTTEN:
        raise DomainError(
            ErrorCode.CONFLICT, message="the decision-memory case was forgotten and accepts no further status event",
            conflict_reason=CONFLICT_CASE_FORGOTTEN,
        )
    if current not in _ALLOWED_FROM[kind]:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            message=f"the decision-memory case is {current}; a {kind} is not allowed",
            machine=CASE_MACHINE, current_state=current, requested_state=_STATUS_AFTER[kind],
        )
    return _STATUS_AFTER[kind]
