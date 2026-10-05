"""The ``RegistrationRequest`` view and listing the registration port produces, and their bytes.

`W49-SEAL-01`, `R-56`. The administrator's view of a request carries the reason a request
was rejected for; the applicant's view carries nothing but ``{"status": "pending"}``, and it
is rendered by the router from the port's answer rather than from this view -- a decided
request is never shown to whoever holds its pair (the 2026-10-06 addendum to `R-56`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from auditmanager.api.schemas.common import timestamp

__all__ = [
    "RegistrationListingView",
    "RegistrationView",
    "registration_body",
]


@dataclass(frozen=True, slots=True)
class RegistrationView:
    """Exactly the frozen ``RegistrationRequest`` shape. No credential material."""

    request_id: str
    login: str
    display_label: str
    last_name: str
    first_name: str
    middle_name: str | None
    status: str
    submitted_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    rejection_reason: str | None
    created_user_uid: str | None


@dataclass(frozen=True, slots=True)
class RegistrationListingView:
    """``listRegistrations``: the requests, oldest first, and the pending total.

    ``pending_total`` is read in the same session as ``items`` and counts every pending
    request whatever the ``status`` filter, because it is the administrator's badge and not
    a property of the page.
    """

    items: tuple[RegistrationView, ...]
    pending_total: int


def registration_body(view: RegistrationView) -> dict[str, Any]:
    return {
        "request_id": view.request_id,
        "login": view.login,
        "display_label": view.display_label,
        "last_name": view.last_name,
        "first_name": view.first_name,
        "middle_name": view.middle_name,
        "status": view.status,
        "submitted_at": timestamp(view.submitted_at),
        "decided_at": None if view.decided_at is None else timestamp(view.decided_at),
        "decided_by": view.decided_by,
        "rejection_reason": view.rejection_reason,
        "created_user_uid": view.created_user_uid,
    }
