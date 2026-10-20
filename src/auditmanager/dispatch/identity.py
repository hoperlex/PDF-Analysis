"""``asg_<ULID>``: the identity of one work assignment, minted by this boundary.

The prefix is contracted (``contracts/domain/v1/identifiers.json``, entity ``WorkAssignment``)
and owned by the shared registry (:class:`auditmanager.shared.identity.AssignmentUid`), which
``tests/contract/domain_p02/test_identifier_catalog.py`` holds equal to the catalog. This
class validates and mints **through** the registry's type, as
:class:`auditmanager.access.public.UserUid` does for ``usr_``, and keeps only this boundary's
refusal: ``validation_failed`` with ``field: assignment_uid``, so no caller sees a second
error type.

The assignment is identified by this value and by nothing else: never by its project, its
document, its assignee or a position in a list (``AGENTS.md`` §4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AssignmentUid as _SharedAssignmentUid
from auditmanager.shared.identity import IdentityError, pattern_for

__all__ = ["ASSIGNMENT_UID_PATTERN", "ASSIGNMENT_UID_PREFIX", "AssignmentUid"]

#: The registry's prefix; restated in migration ``0025_work_assignments`` as
#: ``ck_work_assignment_assignment_uid_format``.
ASSIGNMENT_UID_PREFIX: Final[str] = _SharedAssignmentUid.prefix
ASSIGNMENT_UID_PATTERN: Final[str] = pattern_for(ASSIGNMENT_UID_PREFIX)


@dataclass(frozen=True, slots=True)
class AssignmentUid:
    """An opaque assignment identity. Immutable, compared by value, never decoded."""

    value: str

    def __post_init__(self) -> None:
        try:
            _SharedAssignmentUid.parse(self.value)
        except IdentityError:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"an assignment identity must match {ASSIGNMENT_UID_PATTERN}",
                field="assignment_uid",
                constraint="pattern",
            ) from None

    @classmethod
    def new(cls) -> "AssignmentUid":
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(str(_SharedAssignmentUid.new()))

    @classmethod
    def parse(cls, value: str) -> "AssignmentUid":
        return cls(value)

    def __str__(self) -> str:
        return self.value
