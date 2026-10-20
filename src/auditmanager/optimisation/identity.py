"""The three identities this boundary mints: a price list, one of its positions, a vendor list.

``prl_<ULID>`` -- one uploaded price-list revision; ``prp_<ULID>`` -- one parsed position of it;
``vnl_<ULID>`` -- one revision of a vendor list. `W60-PRICE-LIST-01` phase B contracted all
three (``contracts/domain/v1/identifiers.json`` revision 15), so the shared registry
(:mod:`auditmanager.shared.identity.ids`) owns the prefixes and their patterns, and migration
``0026_price_lists`` restates each as a format CHECK. The types here **validate through the
registry's types** (:class:`~auditmanager.shared.identity.PriceListId` and the two beside it),
as :class:`auditmanager.access.public.UserUid` does for ``usr``, and add only this boundary's
refusal shape: a malformed value is ``validation_failed`` naming the field, never a bare
identity error.

A price list is identified by this value and by nothing else: never by its project, its
revision number, its file name, its digest or a position in a list (``AGENTS.md`` §4). A
position is never identified by its row number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Self

from auditmanager.shared import identity as registry
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, OpaqueId

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

PRICE_LIST_ID_PREFIX: Final[str] = registry.PriceListId.prefix
PRICE_LIST_POSITION_ID_PREFIX: Final[str] = registry.PriceListPositionId.prefix
VENDOR_LIST_ID_PREFIX: Final[str] = registry.VendorListId.prefix

PRICE_LIST_ID_PATTERN: Final[str] = registry.pattern_for(PRICE_LIST_ID_PREFIX)
PRICE_LIST_POSITION_ID_PATTERN: Final[str] = registry.pattern_for(PRICE_LIST_POSITION_ID_PREFIX)
VENDOR_LIST_ID_PATTERN: Final[str] = registry.pattern_for(VENDOR_LIST_ID_PREFIX)


@dataclass(frozen=True, slots=True)
class _LocalId:
    """An opaque identity of this boundary. Immutable, compared by value, never decoded."""

    value: str

    registry_type: ClassVar[type[OpaqueId]]
    field: ClassVar[str]

    def __post_init__(self) -> None:
        try:
            self.registry_type(self.value)
        except IdentityError:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"{self.field} must match {self.pattern()}",
                field=self.field,
                constraint="pattern",
            ) from None

    @classmethod
    def pattern(cls) -> str:
        return registry.pattern_for(cls.registry_type.prefix)

    @classmethod
    def new(cls) -> Self:
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(str(cls.registry_type.new()))

    @classmethod
    def parse(cls, value: str) -> Self:
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PriceListId(_LocalId):
    registry_type: ClassVar[type[OpaqueId]] = registry.PriceListId
    field: ClassVar[str] = "price_list_id"


@dataclass(frozen=True, slots=True)
class PriceListPositionId(_LocalId):
    registry_type: ClassVar[type[OpaqueId]] = registry.PriceListPositionId
    field: ClassVar[str] = "price_list_position_id"


@dataclass(frozen=True, slots=True)
class VendorListId(_LocalId):
    registry_type: ClassVar[type[OpaqueId]] = registry.VendorListId
    field: ClassVar[str] = "vendor_list_id"
