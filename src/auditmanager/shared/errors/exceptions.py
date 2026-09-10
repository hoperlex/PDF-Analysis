"""The typed failure every module raises, and nothing else crosses the boundary."""

from __future__ import annotations

from typing import Any, Mapping

from auditmanager.shared.errors.codes import ErrorCode, from_internal
from auditmanager.shared.errors.envelope import ErrorEnvelope, build


class DomainError(Exception):
    """A failure carrying a catalog code.

    The message is the catalog summary unless a call site supplies a screened one. The
    exception never carries a bucket, key, path, URL, credential or SQL: those are
    rejected by the envelope screen, and this class has no other way to build a message.
    """

    __slots__ = ("code", "detail_fields", "custom_message")

    def __init__(
        self,
        code: ErrorCode,
        *,
        message: str | None = None,
        **detail_fields: Any,
    ) -> None:
        self.code = code
        self.custom_message = message
        self.detail_fields: Mapping[str, Any] = detail_fields
        super().__init__(message or code.summary)

    def envelope(self, correlation_id: str) -> ErrorEnvelope:
        return build(
            self.code,
            correlation_id,
            message=self.custom_message,
            details=self.detail_fields or None,
        )


class InternalError(DomainError):
    """An unmapped internal failure. The original code stays in diagnostics only."""

    def __init__(self, internal_code: str, *, message: str | None = None) -> None:
        self.internal_code = internal_code
        super().__init__(from_internal(internal_code), message=message)
