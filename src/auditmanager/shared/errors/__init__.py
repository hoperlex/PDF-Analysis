"""Shared error kernel: the closed catalog code set, the envelope and the typed failure.

Every module raises :class:`DomainError`. Nothing defines its own error type, and nothing
maps a refusal on message text - the database refusals map on SQLSTATE through
``auditmanager.shared.db.schema.SQLSTATE_TO_CATALOG_CODE``.
"""

from auditmanager.shared.errors.catalog import CONTRACT_VERSION, SAFETY
from auditmanager.shared.errors.codes import ErrorCode, from_internal
from auditmanager.shared.errors.envelope import (
    ErrorEnvelope,
    UnsafeDetailKey,
    UnsafeMessage,
    build,
    screen_message,
)
from auditmanager.shared.errors.exceptions import DomainError, InternalError

__all__ = [
    "CONTRACT_VERSION",
    "SAFETY",
    "ErrorCode",
    "ErrorEnvelope",
    "DomainError",
    "InternalError",
    "UnsafeDetailKey",
    "UnsafeMessage",
    "build",
    "from_internal",
    "screen_message",
]
