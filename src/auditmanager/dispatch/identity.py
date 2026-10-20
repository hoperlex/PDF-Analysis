"""``asg_<ULID>``: the identity of one work assignment, minted by this boundary.

The shared registry (:mod:`auditmanager.shared.identity.ids`) owns every *contracted* prefix,
and ``tests/contract/domain_p02/test_identifier_catalog.py`` holds it equal to
``contracts/domain/v1/identifiers.json`` in both directions. Phase A of `W61-DISPATCHER-01`
owns neither file, so this type follows the registry's conventions **without registering**:
the pattern is :func:`~auditmanager.shared.identity.pattern_for` of the prefix, the body is
:func:`~auditmanager.shared.identity.new_ulid`, and nothing decodes it. It is how
``auditmanager.access`` minted ``usr_`` before `W49-SEAL-01` contracted that prefix. When the
assignment is contracted, ``asg`` moves into the registry and this class validates through
the registry's type, exactly as :class:`auditmanager.access.public.UserUid` does now.

The assignment is identified by this value and by nothing else: never by its project, its
document, its assignee or a position in a list (``AGENTS.md`` §4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid, pattern_for

__all__ = ["ASSIGNMENT_UID_PATTERN", "ASSIGNMENT_UID_PREFIX", "AssignmentUid"]

#: Free in the registry (`W61-DISPATCHER-01` checked ``IDENTITY_TYPES_BY_PREFIX``); restated
#: in migration ``0025_work_assignments`` as ``ck_work_assignment_assignment_uid_format``.
ASSIGNMENT_UID_PREFIX: Final[str] = "asg"
ASSIGNMENT_UID_PATTERN: Final[str] = pattern_for(ASSIGNMENT_UID_PREFIX)

_PATTERN: Final[re.Pattern[str]] = re.compile(ASSIGNMENT_UID_PATTERN)


@dataclass(frozen=True, slots=True)
class AssignmentUid:
    """An opaque assignment identity. Immutable, compared by value, never decoded."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or _PATTERN.match(self.value) is None:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"an assignment identity must match {ASSIGNMENT_UID_PATTERN}",
                field="assignment_uid",
                constraint="pattern",
            )

    @classmethod
    def new(cls) -> "AssignmentUid":
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(f"{ASSIGNMENT_UID_PREFIX}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> "AssignmentUid":
        return cls(value)

    def __str__(self) -> str:
        return self.value
