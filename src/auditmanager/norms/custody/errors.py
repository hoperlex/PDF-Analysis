"""The typed refusals of norm-corpus custody.

Every refusal is a :class:`~auditmanager.shared.errors.DomainError` carrying a catalog code
and only that code's safe detail keys, so an envelope built from it is the same shape as any
other. ``reason`` is the stable custody classifier an operator, a test or the bundle importer
reads: the catalog has no code per custody rule, and inferring the rule from a message would
make the message a contract.
"""

from __future__ import annotations

from typing import Any, Final

from auditmanager.shared.errors import DomainError, ErrorCode

#: `D-143`: no Blob state-machine edge leaves ``rejected``. Bytes that resolve to a rejected
#: Blob are refused at admission and rejected at dispatch, naming the debt.
D143_REASON: Final[str] = "blob_rejected_d143"
D143_MESSAGE: Final[str] = (
    "These bytes resolve to a rejected Blob. Rejected is terminal and has no re-entry "
    "(D-143), so the custody admission is refused and nothing was written."
)


class CustodyRefused(DomainError):
    """A custody operation refused before it wrote anything.

    ``reason`` is a lowercase classifier (``blob_rejected_d143``, ``media_type_conflict``,
    ``slot_reuse``, ``not_in_manifest`` ...). The refusal is raised before the first write
    of the operation, so the caller's transaction holds nothing the refusal must undo.
    """

    __slots__ = ("reason",)

    def __init__(
        self,
        reason: str,
        code: ErrorCode,
        *,
        message: str | None = None,
        **detail_fields: Any,
    ) -> None:
        self.reason = reason
        super().__init__(code, message=message, **detail_fields)


def d143_refusal() -> CustodyRefused:
    """The admission of bytes whose Blob row is ``rejected``."""
    return CustodyRefused(
        D143_REASON,
        ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
        message=D143_MESSAGE,
        machine="blob",
        current_state="rejected",
        requested_state="norm_custody_admission",
    )


__all__ = ["D143_MESSAGE", "D143_REASON", "CustodyRefused", "d143_refusal"]
