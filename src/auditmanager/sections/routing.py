"""Fail-closed section routing for a future persisted confirmation workflow.

A filename suggestion is not a confirmation. The caller must supply the
confirmed section stored for the same document version; this pure guard
cannot read the database or authorize the confirming actor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from auditmanager.sections.suggestion import _catalogue
from auditmanager.shared.identity import AnalysisProfileId, IdentityError, VersionUid


class SectionRouteUnavailable(ValueError):
    """A run has no confirmed and available section-specific profile."""


@dataclass(frozen=True, slots=True)
class ConfirmedSection:
    version_uid: str
    code: str


@dataclass(frozen=True, slots=True)
class SectionRoute:
    code: str
    analysis_profile_id: str


def route_confirmed_section(
    version_uid: str,
    confirmed: ConfirmedSection | None,
    available_profiles: Mapping[str, str],
) -> SectionRoute:
    """Resolve one version's confirmed code without an AR or suggestion fallback.

    ``available_profiles`` is the caller's sealed, currently executable
    profile registry. An unavailable profile is a refusal even when the
    suggested or confirmed code is valid in the fifteen-section catalogue.
    """
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SectionRouteUnavailable("version_identity_invalid") from None
    if confirmed is None:
        raise SectionRouteUnavailable("section_unconfirmed")
    if not isinstance(confirmed, ConfirmedSection):
        raise SectionRouteUnavailable("section_confirmation_invalid")
    if confirmed.version_uid != version_uid:
        raise SectionRouteUnavailable("section_confirmation_version_mismatch")
    if not isinstance(confirmed.code, str) or confirmed.code not in {
        section.code for section in _catalogue()
    }:
        raise SectionRouteUnavailable("section_unknown")
    profile_id = available_profiles.get(confirmed.code)
    if profile_id is None:
        raise SectionRouteUnavailable("section_profile_unavailable")
    try:
        AnalysisProfileId.parse(profile_id)
    except IdentityError:
        raise SectionRouteUnavailable("section_profile_invalid") from None
    return SectionRoute(code=confirmed.code, analysis_profile_id=profile_id)
