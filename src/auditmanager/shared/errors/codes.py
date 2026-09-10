"""The closed error-code enum.

The member set is exactly the key set of the frozen catalog. It is closed on purpose: a
code that is not in the catalog is never emitted and never invented at the edge, so
there is no ``UNKNOWN`` member and no way to construct one from an arbitrary string
without going through :func:`from_internal`, which maps to ``internal_error``.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

from auditmanager.shared.errors.catalog import CODES, UNKNOWN_INTERNAL_CODE


class ErrorCode(str, Enum):
    """Exactly the twenty codes of ``contracts/domain/v1/error-codes.json``."""

    VALIDATION_FAILED = "validation_failed"
    NOT_FOUND = "not_found"
    AUTHENTICATION_REQUIRED = "authentication_required"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    STATE_TRANSITION_NOT_ALLOWED = "state_transition_not_allowed"
    IDEMPOTENCY_KEY_REUSE = "idempotency_key_reuse"
    IDEMPOTENCY_KEY_IN_PROGRESS = "idempotency_key_in_progress"
    IDEMPOTENCY_KEY_STALE = "idempotency_key_stale"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    STORAGE_INTEGRITY_ERROR = "storage_integrity_error"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    REQUIRED_NORM_UNAVAILABLE = "required_norm_unavailable"
    ANALYSIS_INPUT_INVALID = "analysis_input_invalid"
    ANALYSIS_FAILED = "analysis_failed"
    PARTIAL_RESULT_NOT_PUBLISHABLE = "partial_result_not_publishable"
    COST_BUDGET_EXCEEDED = "cost_budget_exceeded"
    STALE_ATTEMPT = "stale_attempt"
    EXECUTION_TOKEN_INVALID = "execution_token_invalid"
    INTERNAL_ERROR = "internal_error"

    @property
    def retryable(self) -> bool:
        """Pinned by the catalog. Never inferred from an HTTP status or a message."""
        return bool(CODES[self.value]["retryable"])

    @property
    def http_status(self) -> int:
        return int(CODES[self.value]["http"])

    @property
    def summary(self) -> str:
        return str(CODES[self.value]["summary"])

    @property
    def safe_detail_keys(self) -> frozenset[str]:
        return frozenset(CODES[self.value].get("safe_detail_keys", ()))


def from_internal(internal_code: str) -> ErrorCode:
    """Map an internally typed failure reason to a catalog code.

    An internal code with no declared mapping becomes ``internal_error``; the original
    stays in protected diagnostics. This is the catalog's ``internal_mapping`` rule.
    """
    try:
        return ErrorCode(internal_code)
    except ValueError:
        return ErrorCode(UNKNOWN_INTERNAL_CODE)


#: Guards the enum against the contract at import. A code added to the catalog without a
#: member here, or a member with no catalog entry, is a hard failure rather than a
#: silently narrower vocabulary.
_MEMBERS: Final[frozenset[str]] = frozenset(c.value for c in ErrorCode)
if _MEMBERS != frozenset(CODES):
    missing = sorted(frozenset(CODES) - _MEMBERS)
    extra = sorted(_MEMBERS - frozenset(CODES))
    raise RuntimeError(
        "auditmanager.shared.errors.codes is out of step with "
        f"contracts/domain/v1/error-codes.json: missing={missing} extra={extra}"
    )
