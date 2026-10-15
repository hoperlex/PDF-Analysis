"""Pure W59 preparation for an expert's version-bound section decision.

This module does not grant authority to run analysis. A future transaction must
load the version, its stage and any persisted confirmation, authenticate the
actor, then persist an ``insert`` plan before the routing guard reads that row.
The legacy document-level section and file-name suggestions are never inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from auditmanager.access.public import ROLE_EXPERT, ROLES, UserUid
from auditmanager.sections.suggestion import _catalogue
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import IdentityError, VersionUid


class SectionConfirmationRefused(ValueError):
    """The proposed confirmation is not a valid expert decision."""


@dataclass(frozen=True, slots=True)
class ExpertSectionConfirmation:
    """A proposed or previously persisted decision for one immutable version."""

    version_uid: str
    code: str
    stage: Literal["P", "R"]
    expert_uid: str


@dataclass(frozen=True, slots=True)
class SectionConfirmationPlan:
    """An insert request or an unchanged previous decision; no I/O is performed."""

    action: Literal["insert", "unchanged"]
    confirmation: ExpertSectionConfirmation


def prepare_section_confirmation(
    *,
    version_uid: str,
    code: str,
    stage: str,
    expert_uid: str,
    actor_roles: frozenset[str],
    previous: ExpertSectionConfirmation | None = None,
) -> SectionConfirmationPlan:
    """Validate an explicit choice and preserve the first confirmer on retry.

    ``stage`` is the version's already established project stage, not a stage
    inferred from its file name. ``actor_roles`` must come from authenticated
    account state. A different choice needs a separately auditable correction
    workflow; this first-insert policy never rewrites a prior decision.
    """
    _require_version(version_uid)
    _require_section(code)
    _require_stage(stage)
    _require_expert(expert_uid, actor_roles)
    if previous is not None:
        if not isinstance(previous, ExpertSectionConfirmation):
            raise SectionConfirmationRefused("previous_confirmation_invalid")
        _require_version(previous.version_uid)
        _require_section(previous.code)
        _require_stage(previous.stage)
        _require_user(previous.expert_uid)
        if previous.version_uid != version_uid:
            raise SectionConfirmationRefused("previous_confirmation_version_mismatch")
        if previous.stage != stage:
            raise SectionConfirmationRefused("previous_confirmation_stage_mismatch")
        if previous.code != code:
            raise SectionConfirmationRefused("section_already_confirmed")
        return SectionConfirmationPlan("unchanged", previous)
    return SectionConfirmationPlan(
        "insert",
        ExpertSectionConfirmation(version_uid, code, cast(Literal["P", "R"], stage), expert_uid),
    )


def _require_version(version_uid: str) -> None:
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SectionConfirmationRefused("version_identity_invalid") from None


def _require_section(code: str) -> None:
    if not isinstance(code, str) or code not in {item.code for item in _catalogue()}:
        raise SectionConfirmationRefused("section_unknown")


def _require_stage(stage: str) -> None:
    if stage not in ("P", "R") or not isinstance(stage, str):
        raise SectionConfirmationRefused("version_stage_unclassified")


def _require_user(expert_uid: str) -> None:
    try:
        UserUid.parse(expert_uid)
    except DomainError:
        raise SectionConfirmationRefused("expert_identity_invalid") from None


def _require_expert(expert_uid: str, actor_roles: frozenset[str]) -> None:
    _require_user(expert_uid)
    if (
        not isinstance(actor_roles, frozenset)
        or not actor_roles.issubset(ROLES)
        or ROLE_EXPERT not in actor_roles
    ):
        raise SectionConfirmationRefused("expert_role_required")
