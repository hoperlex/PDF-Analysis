"""The three identities this boundary mints: a price list, one of its positions, a vendor list.

``prl_<ULID>`` -- one uploaded price-list revision; ``prp_<ULID>`` -- one parsed position of it;
``vnl_<ULID>`` -- one revision of a vendor list. Each is free in the shared registry
(`W60-PRICE-LIST-01` checked ``IDENTITY_TYPES_BY_PREFIX``) and is restated in migration
``0026_price_lists`` as a format CHECK.

The shared registry (:mod:`auditmanager.shared.identity.ids`) owns every *contracted* prefix,
and ``tests/contract/domain_p02/test_identifier_catalog.py`` holds it equal to
``contracts/domain/v1/identifiers.json``. Phase A of the task owns neither file, so these types
follow the registry's conventions **without registering** -- the pattern is
:func:`~auditmanager.shared.identity.pattern_for` of the prefix, the body is
:func:`~auditmanager.shared.identity.new_ulid`, nothing decodes it -- exactly as
``auditmanager.dispatch`` mints ``asg_``. Contracting them moves the prefixes into the registry.

A price list is identified by this value and by nothing else: never by its project, its
revision number, its file name, its digest or a position in a list (``AGENTS.md`` §4). A
position is never identified by its row number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Final, Self

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid, pattern_for

__all__ = [
    "PRICE_LIST_ID_PATTERN",
    "PRICE_LIST_ID_PREFIX",
    "PRICE_LIST_POSITION_ID_PATTERN",
    "PRICE_LIST_POSITION_ID_PREFIX",
    "VENDOR_LIST_ID_PATTERN",
    "VENDOR_LIST_ID_PREFIX",
    "PriceListId",
    "PriceListPositionId",
    "VendorListId",
]

PRICE_LIST_ID_PREFIX: Final[str] = "prl"
PRICE_LIST_POSITION_ID_PREFIX: Final[str] = "prp"
VENDOR_LIST_ID_PREFIX: Final[str] = "vnl"

PRICE_LIST_ID_PATTERN: Final[str] = pattern_for(PRICE_LIST_ID_PREFIX)
PRICE_LIST_POSITION_ID_PATTERN: Final[str] = pattern_for(PRICE_LIST_POSITION_ID_PREFIX)
VENDOR_LIST_ID_PATTERN: Final[str] = pattern_for(VENDOR_LIST_ID_PREFIX)


@dataclass(frozen=True, slots=True)
class _LocalId:
    """An opaque identity of this boundary. Immutable, compared by value, never decoded."""

    value: str

    prefix: ClassVar[str]
    field: ClassVar[str]
    _pattern: ClassVar[re.Pattern[str]]

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or self._pattern.match(self.value) is None:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"{self.field} must match {self._pattern.pattern}",
                field=self.field,
                constraint="pattern",
            )

    @classmethod
    def new(cls) -> Self:
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(f"{cls.prefix}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> Self:
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PriceListId(_LocalId):
    prefix: ClassVar[str] = PRICE_LIST_ID_PREFIX
    field: ClassVar[str] = "price_list_id"
    _pattern: ClassVar[re.Pattern[str]] = re.compile(PRICE_LIST_ID_PATTERN)


@dataclass(frozen=True, slots=True)
class PriceListPositionId(_LocalId):
    prefix: ClassVar[str] = PRICE_LIST_POSITION_ID_PREFIX
    field: ClassVar[str] = "price_list_position_id"
    _pattern: ClassVar[re.Pattern[str]] = re.compile(PRICE_LIST_POSITION_ID_PATTERN)


@dataclass(frozen=True, slots=True)
class VendorListId(_LocalId):
    prefix: ClassVar[str] = VENDOR_LIST_ID_PREFIX
    field: ClassVar[str] = "vendor_list_id"
    _pattern: ClassVar[re.Pattern[str]] = re.compile(VENDOR_LIST_ID_PATTERN)
