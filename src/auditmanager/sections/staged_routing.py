"""Pure P/R-bound route pin for a future authoritative W59 run-start read.

The caller supplies the version's saved stage and section confirmation. This
module checks their agreement, but cannot prove their DB provenance or that an
expert remains authorized. No served run calls it yet.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

from auditmanager.access.public import UserUid
from auditmanager.sections.confirmation import ExpertSectionConfirmation
from auditmanager.sections.routing import (
    ConfirmedSection,
    SectionRouteUnavailable,
    route_confirmed_section,
)
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import IdentityError, VersionUid


@dataclass(frozen=True, slots=True)
class StagedSectionRoute:
    """One checked supplied version/stage/section/profile combination."""

    version_uid: str
    project_stage: Literal["P", "R"]
    section_code: str
    analysis_profile_id: str


def route_staged_section(
    *,
    version_uid: str,
    project_stage: str | None,
    confirmation: ExpertSectionConfirmation | None,
    available_profiles: Mapping[str, str],
) -> StagedSectionRoute:
    """Require an explicit same-version, same-stage confirmation and profile.

    Future serving code must load both facts through an authorized persisted
    read and use this guard at run start in place of the section-only route.
    """
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SectionRouteUnavailable("version_identity_invalid") from None
    if project_stage not in ("P", "R") or not isinstance(project_stage, str):
        raise SectionRouteUnavailable("version_stage_unclassified")
    if confirmation is None:
        raise SectionRouteUnavailable("section_unconfirmed")
    if not isinstance(confirmation, ExpertSectionConfirmation):
        raise SectionRouteUnavailable("section_confirmation_invalid")
    if confirmation.version_uid != version_uid:
        raise SectionRouteUnavailable("section_confirmation_version_mismatch")
    if confirmation.stage != project_stage:
        raise SectionRouteUnavailable("section_confirmation_stage_mismatch")
    try:
        UserUid.parse(confirmation.expert_uid)
    except DomainError:
        raise SectionRouteUnavailable("section_confirmer_identity_invalid") from None
    if not isinstance(available_profiles, Mapping):
        raise SectionRouteUnavailable("section_profile_registry_invalid")
    route = route_confirmed_section(
        version_uid,
        ConfirmedSection(version_uid, confirmation.code),
        available_profiles,
    )
    return StagedSectionRoute(
        version_uid=version_uid,
        project_stage=cast(Literal["P", "R"], project_stage),
        section_code=route.code,
        analysis_profile_id=route.analysis_profile_id,
    )
