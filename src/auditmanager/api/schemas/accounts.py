"""The ``Account`` view the account port produces, and the bytes it renders as.

`W49-SEAL-01`. ``getMe``, ``updateMyProfile`` and the six account operations of an
administrator answer with one shape, so there is one view and one body function. The view
is built by the composition root's adapter from ``auditmanager.access``'s record; nothing
here reaches a database or decides a rule -- which account a caller may read, and what a
change may do, are the authorization seam's and the access boundary's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from auditmanager.api.schemas.common import timestamp

__all__ = ["AccountView", "PersonNamesView", "account_body"]


@dataclass(frozen=True, slots=True)
class AccountView:
    """Exactly the frozen ``Account`` shape.

    ``roles`` is a tuple in the order the body renders it -- sorted -- so the bytes of one
    account do not depend on the order a set happened to iterate in.
    """

    user_uid: str
    login: str
    display_label: str
    last_name: str | None
    first_name: str | None
    middle_name: str | None
    roles: tuple[str, ...]
    profile_complete: bool
    is_default_credential: bool
    archived_at: datetime | None


@dataclass(frozen=True, slots=True)
class PersonNamesView:
    """``PersonNames``: the three names an administrator sets together (``updateUser``)."""

    last_name: str
    first_name: str
    middle_name: str | None


def account_body(view: AccountView) -> dict[str, Any]:
    """Every property is required by the contract; the four that may be unknown are ``null``."""
    return {
        "user_uid": view.user_uid,
        "login": view.login,
        "display_label": view.display_label,
        "last_name": view.last_name,
        "first_name": view.first_name,
        "middle_name": view.middle_name,
        "roles": sorted(view.roles),
        "profile_complete": view.profile_complete,
        "is_default_credential": view.is_default_credential,
        "archived_at": None if view.archived_at is None else timestamp(view.archived_at),
    }
