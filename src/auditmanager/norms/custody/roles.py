"""The custody roles and the target each one binds to (`R-76`, migrations ``0018``/``0023``).

One row per role. It mirrors ``ck_norm_custody_role_shape`` -- the CHECK of the same name on
``norm_custody_admission`` and ``norm_custody_binding`` -- and the target arm of
``am_guard_norm_custody_binding``. The database refuses an unknown role, target kind or anchor
kind on its own; this table exists so that the application refuses first, with a typed error,
and knows which table holds each target kind.

Migration 0023 adds ``norm_retrieval_set`` and ``norm_catalogue`` (targets
that are not norm documents) by replacing that CHECK and the guard's target
arm. The table below mirrors the resulting shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Mapping

from auditmanager.shared.errors import ErrorCode

from .errors import CustodyRefused

#: Source PDF/crop role and the two artifact roles added by migration ``0023``.
NORM_SOURCE: Final[str] = "norm_source"
NORM_RETRIEVAL_SET: Final[str] = "norm_retrieval_set"
NORM_CATALOGUE: Final[str] = "norm_catalogue"

_ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}"


@dataclass(frozen=True, slots=True)
class RoleShape:
    """What one role binds to: a target kind, its identity prefix and its anchor kinds."""

    role: str
    target_kind: str
    target_prefix: str
    anchor_kinds: frozenset[str]

    def target_pattern(self) -> re.Pattern[str]:
        return re.compile(rf"^{self.target_prefix}_{_ULID_BODY}$")


ROLE_SHAPES: Final[Mapping[str, RoleShape]] = {
    NORM_SOURCE: RoleShape(
        role=NORM_SOURCE,
        target_kind="norm_document",
        target_prefix="ndoc",
        anchor_kinds=frozenset({"pdf", "crop"}),
    ),
    NORM_RETRIEVAL_SET: RoleShape(
        role=NORM_RETRIEVAL_SET,
        target_kind="norm_retrieval_set",
        target_prefix="nrs",
        anchor_kinds=frozenset({"artifact"}),
    ),
    NORM_CATALOGUE: RoleShape(
        role=NORM_CATALOGUE,
        target_kind="norm_retrieval_set",
        target_prefix="nrs",
        anchor_kinds=frozenset({"artifact"}),
    ),
}

#: For each target kind, the table and identity column that prove the target exists. The
#: binding guard asks the same question in the database at publication time (invariant 4).
TARGET_TABLES: Final[Mapping[str, tuple[str, str]]] = {
    "norm_document": ("norm_document", "norm_document_id"),
    "norm_retrieval_set": ("norm_retrieval_set", "norm_retrieval_set_id"),
}


def shape_of(role: str) -> RoleShape:
    """The shape of a known role, or a typed refusal naming the field."""
    shape = ROLE_SHAPES.get(role)
    if shape is None:
        raise CustodyRefused(
            "unknown_role",
            ErrorCode.VALIDATION_FAILED,
            field="role",
            constraint="a custody role ck_norm_custody_role_shape admits",
        )
    return shape


def require_target(shape: RoleShape, target_id: str) -> str:
    """Validate a target identity against its role's target kind."""
    if not isinstance(target_id, str) or not shape.target_pattern().fullmatch(target_id):
        raise CustodyRefused(
            "target_id_malformed",
            ErrorCode.VALIDATION_FAILED,
            field="target_id",
            constraint=f"the opaque {shape.target_prefix} identity of a {shape.target_kind}",
        )
    return target_id


def require_anchor(shape: RoleShape, anchor_kind: str, anchor: str) -> None:
    """An anchor is opaque text; only its kind and its length are checked here."""
    if anchor_kind not in shape.anchor_kinds:
        raise CustodyRefused(
            "anchor_kind_unknown",
            ErrorCode.VALIDATION_FAILED,
            field="anchor_kind",
            constraint="one of the anchor kinds of the role",
        )
    if not isinstance(anchor, str) or not 1 <= len(anchor) <= 500:
        raise CustodyRefused(
            "anchor_malformed",
            ErrorCode.VALIDATION_FAILED,
            field="anchor",
            constraint="1 to 500 characters of opaque text",
        )


__all__ = [
    "NORM_SOURCE",
    "NORM_RETRIEVAL_SET",
    "NORM_CATALOGUE",
    "ROLE_SHAPES",
    "TARGET_TABLES",
    "RoleShape",
    "require_anchor",
    "require_target",
    "shape_of",
]
