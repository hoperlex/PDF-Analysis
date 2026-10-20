"""The optimisation boundary's rules, with no I/O: who may do what, and what a value may be.

**Roles** (`R-60`: roles are a set; `R-80`: an account with no role reads no product data):

* upload a price list -- ``expert``;
* set the **global** vendor list of a section -- ``admin``;
* set a **project** override of a section's vendor list -- ``expert``;
* read price lists, positions and vendor lists -- ``admin`` or ``expert``.

**Vendor lists** (``ROADMAP-TO-BETA.md`` §10.1 A-3). The global list of a section is kept by an
administrator; a project may override it per section. A project revision's mode is ``list``
(its entries apply -- none at all is a valid, explicit "no restriction" for this project) or
``inherit`` (the override is removed and the global list applies again). The **effective**
list of a section is the latest project revision when its mode is ``list``, else the latest
global revision, else none (:func:`effective_source`).

**Exact repeats** write nothing: setting the entries (and mode) the latest revision already
has answers that revision; an ``inherit`` with no override in force answers the current state.
An ``expected_vendor_list_id`` that is not the latest revision is ``conflict``
(``conflict_reason: vendor_list_changed``) -- somebody changed the list since the caller read it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal

from auditmanager.access.public import ROLE_ADMIN, ROLE_EXPERT
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AGGREGATE_PRICE_LIST",
    "AGGREGATE_VENDOR_LIST",
    "CONFLICT_VENDOR_LIST_CHANGED",
    "MAX_ENTRY_NOTE_LENGTH",
    "MAX_MATERIAL_LENGTH",
    "MAX_VENDOR_LENGTH",
    "MAX_VENDOR_LIST_ENTRIES",
    "MODE_INHERIT",
    "MODE_LIST",
    "MODES",
    "SCOPE_GLOBAL",
    "SCOPE_PROJECT",
    "SCOPES",
    "SECTION_ORDER",
    "SOURCE_GLOBAL",
    "SOURCE_NONE",
    "SOURCE_PROJECT",
    "VendorListEntry",
    "effective_source",
    "normalize_entries",
    "parse_currency_code",
    "parse_mode",
    "parse_section_code",
    "require_admin",
    "require_expert",
    "require_reader",
]

AGGREGATE_PRICE_LIST: Final[str] = "PriceList"
AGGREGATE_VENDOR_LIST: Final[str] = "VendorList"
CONFLICT_VENDOR_LIST_CHANGED: Final[str] = "vendor_list_changed"

#: The fifteen sections in the vocabulary's order (migration ``0026`` restates this tuple;
#: ``tests/unit/optimisation`` holds both equal to ``sections.public.SECTION_CODES``).
SECTION_ORDER: Final[tuple[str, ...]] = (
    "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS",
)

SCOPE_GLOBAL: Final[str] = "global"
SCOPE_PROJECT: Final[str] = "project"
SCOPES: Final[tuple[str, ...]] = (SCOPE_GLOBAL, SCOPE_PROJECT)

MODE_LIST: Final[str] = "list"
MODE_INHERIT: Final[str] = "inherit"
MODES: Final[tuple[str, ...]] = (MODE_LIST, MODE_INHERIT)

SOURCE_PROJECT: Final[str] = "project"
SOURCE_GLOBAL: Final[str] = "global"
SOURCE_NONE: Final[str] = "none"

MAX_VENDOR_LIST_ENTRIES: Final[int] = 500
MAX_MATERIAL_LENGTH: Final[int] = 500
MAX_VENDOR_LENGTH: Final[int] = 500
MAX_ENTRY_NOTE_LENGTH: Final[int] = 1000

_CURRENCY: Final[re.Pattern[str]] = re.compile(r"[A-Z]{3}")


def _denied(capability: str, aggregate_type: str, message: str | None = None) -> DomainError:
    return DomainError(
        ErrorCode.PERMISSION_DENIED,
        message=message,
        aggregate_type=aggregate_type,
        required_capability=capability,
    )


def require_reader(roles: frozenset[str], *, aggregate_type: str) -> None:
    """`R-80`: an account without a role reads no product data."""
    if not roles & {ROLE_ADMIN, ROLE_EXPERT}:
        raise _denied("role:admin|expert", aggregate_type)


def require_expert(roles: frozenset[str], *, aggregate_type: str, act: str) -> None:
    """Uploading a price list and overriding a project's vendor list are an expert's acts."""
    if ROLE_EXPERT not in roles:
        raise _denied("role:expert", aggregate_type, f"only an expert can {act}")


def require_admin(roles: frozenset[str], *, aggregate_type: str, act: str) -> None:
    """The global vendor list is an administrator's."""
    if ROLE_ADMIN not in roles:
        raise _denied("role:admin", aggregate_type, f"only an administrator can {act}")


def parse_section_code(value: Any, *, field: str = "section_code") -> str:
    if not isinstance(value, str) or value not in SECTION_ORDER:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="enum")
    return value


def parse_mode(value: Any) -> str:
    if not isinstance(value, str) or value not in MODES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="mode", constraint="enum")
    return value


def parse_currency_code(value: Any, *, field: str = "default_currency") -> str | None:
    """An ISO 4217 code (three upper-case Latin letters) or nothing."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    cleaned = value.strip()
    if not cleaned:
        return None
    if _CURRENCY.fullmatch(cleaned) is None:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern")
    return cleaned


@dataclass(frozen=True, slots=True)
class VendorListEntry:
    """One entry: the material or equipment group it covers, the vendor, a note."""

    material: str | None
    vendor: str
    note: str | None


def _text(raw: Any, *, field: str, maximum: int, required: bool) -> str | None:
    if raw is None:
        cleaned = ""
    elif isinstance(raw, str):
        cleaned = " ".join(raw.split())
    else:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    if not cleaned:
        if required:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="required")
        return None
    if len(cleaned) > maximum:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"{field} is longer than {maximum} characters",
            field=field,
            constraint="max_length",
        )
    return cleaned


def normalize_entries(raw: Sequence[Any] | None) -> tuple[VendorListEntry, ...]:
    """Validate and normalise the entries of a requested revision, keeping their order.

    Each entry is a mapping with ``vendor`` (required), ``material`` and ``note`` (optional);
    whitespace runs collapse to one space. More than :data:`MAX_VENDOR_LIST_ENTRIES` entries,
    a missing vendor, or a value over its bound is ``validation_failed``.
    """
    if raw is None:
        return ()
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="entries", constraint="type")
    if len(raw) > MAX_VENDOR_LIST_ENTRIES:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"a vendor list holds at most {MAX_VENDOR_LIST_ENTRIES} entries",
            field="entries",
            constraint="max_items",
        )
    entries: list[VendorListEntry] = []
    for item in raw:
        if isinstance(item, VendorListEntry):
            item = {"material": item.material, "vendor": item.vendor, "note": item.note}
        if not isinstance(item, dict):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="entries", constraint="type")
        vendor = _text(item.get("vendor"), field="vendor", maximum=MAX_VENDOR_LENGTH, required=True)
        assert vendor is not None
        entries.append(
            VendorListEntry(
                material=_text(
                    item.get("material"),
                    field="material",
                    maximum=MAX_MATERIAL_LENGTH,
                    required=False,
                ),
                vendor=vendor,
                note=_text(
                    item.get("note"), field="note", maximum=MAX_ENTRY_NOTE_LENGTH, required=False
                ),
            )
        )
    return tuple(entries)


Source = Literal["project", "global", "none"]


def effective_source(*, project_mode: str | None, has_global: bool) -> Source:
    """Which revision applies to a section: the project's list, the global one, or none."""
    if project_mode == MODE_LIST:
        return "project"
    if has_global:
        return "global"
    return "none"
