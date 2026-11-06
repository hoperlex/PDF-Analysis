"""The proposals slice's rules, with no I/O: who may do what, and what a value may be.

**Roles** (`R-60`: roles are a set and an administrator without ``expert`` reads and does not
decide an expert's work; `R-80`: an account with no role reads no product data):

* start an optimisation pass -- ``expert``;
* append a decision to a proposal, or withdraw the standing one -- ``expert`` (an account holding
  only ``admin`` is ``permission_denied``);
* read passes, proposals and the CSV export -- ``admin`` or ``expert``.

**Decisions** are append-only events with one of four verdicts: ``accept``, ``reject``,
``revise`` or ``revoke``. ``revise`` means "the analog is right in principle, the proposal needs
changing" and therefore **requires** a comment; the comment is optional on the other three.
``revoke`` withdraws the standing decision (`UI-B-12`, «Снять решение»): it is itself an appended
event, never a deletion or an update, it takes the proposal back to ``pending`` and it is refused
(``conflict``, :data:`REFUSAL_NOTHING_TO_REVOKE`) when nothing stands -- the proposal has no
decision yet, or its latest event is already a ``revoke``. The current decision of a proposal is
its latest event unless that event is a ``revoke``; a proposal without one is ``pending``. Nothing
here, and nothing in the generator, ever writes a decision: a verdict is what an expert said
(``AGENTS.md`` §4).

**Refusals of a pass** are ``conflict`` with a ``conflict_reason`` naming the unmet
precondition (:data:`PASS_REFUSAL_REASONS`, in the order they are checked): the specification
read's own states (``version_unclassified``, ``section_not_ar``, ``price_list_missing``,
``analysis_missing``, ``text_unavailable``, ``specification_too_large``), then
``vendor_list_missing`` -- the version's own section has neither a project list nor a global one.
``section_not_ar`` stays in the list because the wire vocabulary keeps it, but no read produces it
any more: a version confirmed in any section is read.
"""

from __future__ import annotations

from typing import Any, Final

from auditmanager.access.public import ROLE_ADMIN, ROLE_EXPERT, ROLE_VIEWER
from auditmanager.shared.errors import DomainError, ErrorCode

from ..project_match import (
    STATE_ANALYSIS_MISSING,
    STATE_PRICE_LIST_MISSING,
    STATE_SECTION_NOT_AR,
    STATE_SPECIFICATION_TOO_LARGE,
    STATE_TEXT_UNAVAILABLE,
    STATE_VERSION_UNCLASSIFIED,
)

__all__ = [
    "AGGREGATE_OPTIMISATION_PASS",
    "AGGREGATE_OPTIMISATION_PROPOSAL",
    "COMMAND_TYPE_DECIDE_PROPOSAL",
    "COMMAND_TYPE_START_PASS",
    "DECISION_FILTERS",
    "DECISION_PENDING",
    "DEFAULT_PROPOSAL_PAGE",
    "MAX_COMMENT_LENGTH",
    "MAX_PASS_PAGE",
    "MAX_PROPOSAL_PAGE",
    "PASS_REFUSAL_REASONS",
    "REFUSAL_NOTHING_TO_REVOKE",
    "REFUSAL_VENDOR_LIST_MISSING",
    "STORED_VERDICTS",
    "VERDICTS",
    "VERDICT_ACCEPT",
    "VERDICT_REJECT",
    "VERDICT_REVISE",
    "VERDICT_REVOKE",
    "normalize_comment",
    "parse_decision_filter",
    "parse_verdict",
    "require_expert",
    "require_reader",
]

AGGREGATE_OPTIMISATION_PASS: Final[str] = "OptimisationPass"
AGGREGATE_OPTIMISATION_PROPOSAL: Final[str] = "OptimisationProposal"

#: Match ``ck_command_record_command_type`` (lowercase snake_case, 3-64 characters).
COMMAND_TYPE_START_PASS: Final[str] = "start_optimisation_pass"
COMMAND_TYPE_DECIDE_PROPOSAL: Final[str] = "decide_optimisation_proposal"

VERDICT_ACCEPT: Final[str] = "accept"
VERDICT_REJECT: Final[str] = "reject"
VERDICT_REVISE: Final[str] = "revise"
VERDICT_REVOKE: Final[str] = "revoke"
#: The verdicts that stand as a decision: what a proposal's current decision, its counts and the
#: ``decision`` filter are made of. Migration ``0027`` restated these three.
VERDICTS: Final[tuple[str, ...]] = (VERDICT_ACCEPT, VERDICT_REJECT, VERDICT_REVISE)
#: Every verdict an event may carry: the three above and the withdrawal. Restated by migration
#: ``0056`` (``ck_optimisation_proposal_decision_verdict``); the unit suite holds both equal.
STORED_VERDICTS: Final[tuple[str, ...]] = (*VERDICTS, VERDICT_REVOKE)
#: The current decision of a proposal nobody has decided yet. Not a stored verdict.
DECISION_PENDING: Final[str] = "pending"
#: What a proposal listing may be filtered by: no decision yet, or one current verdict.
DECISION_FILTERS: Final[tuple[str, ...]] = (DECISION_PENDING, *VERDICTS)

#: Restated by migration ``0027`` (``ck_optimisation_proposal_decision_comment``).
MAX_COMMENT_LENGTH: Final[int] = 2000

DEFAULT_PROPOSAL_PAGE: Final[int] = 50
MAX_PROPOSAL_PAGE: Final[int] = 200
MAX_PASS_PAGE: Final[int] = 100

REFUSAL_VENDOR_LIST_MISSING: Final[str] = "vendor_list_missing"
#: The ``conflict_reason`` of a ``revoke`` over a proposal with no standing decision.
REFUSAL_NOTHING_TO_REVOKE: Final[str] = "no_decision_to_revoke"
#: Every ``conflict_reason`` a refused pass can carry, in the order the preconditions are
#: checked.
PASS_REFUSAL_REASONS: Final[tuple[str, ...]] = (
    STATE_VERSION_UNCLASSIFIED,
    STATE_SECTION_NOT_AR,
    STATE_PRICE_LIST_MISSING,
    STATE_ANALYSIS_MISSING,
    STATE_TEXT_UNAVAILABLE,
    STATE_SPECIFICATION_TOO_LARGE,
    REFUSAL_VENDOR_LIST_MISSING,
)


def _denied(capability: str, aggregate_type: str, message: str | None = None) -> DomainError:
    return DomainError(
        ErrorCode.PERMISSION_DENIED,
        message=message,
        aggregate_type=aggregate_type,
        required_capability=capability,
    )


def require_reader(roles: frozenset[str], *, aggregate_type: str) -> None:
    """`R-80`: an account without a role reads no product data; `R-150e`: the viewer reads it."""
    if not roles & {ROLE_ADMIN, ROLE_EXPERT, ROLE_VIEWER}:
        raise _denied("role:admin|expert|viewer", aggregate_type)


def require_expert(roles: frozenset[str], *, aggregate_type: str, act: str) -> None:
    """Starting a pass and deciding a proposal are an expert's acts; ``admin`` alone is not."""
    if ROLE_EXPERT not in roles:
        raise _denied("role:expert", aggregate_type, f"only an expert can {act}")


def parse_verdict(value: Any) -> str:
    if not isinstance(value, str) or value not in STORED_VERDICTS:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="verdict", constraint="enum")
    return value


def parse_decision_filter(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in DECISION_FILTERS:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="decision", constraint="enum")
    return value


def normalize_comment(raw: Any, *, verdict: str) -> str | None:
    """Whitespace runs collapse to one space; empty is none; ``revise`` requires one."""
    if raw is None:
        cleaned = ""
    elif isinstance(raw, str):
        cleaned = " ".join(raw.split())
    else:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="comment", constraint="type")
    if len(cleaned) > MAX_COMMENT_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"a comment is at most {MAX_COMMENT_LENGTH} characters",
            field="comment",
            constraint="max_length",
        )
    if not cleaned:
        if verdict == VERDICT_REVISE:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="a revise decision says what to change: the comment is required",
                field="comment",
                constraint="required",
            )
        return None
    return cleaned
