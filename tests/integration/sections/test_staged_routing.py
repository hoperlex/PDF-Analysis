"""A supplied P/R fact must agree with the expert's section fact before routing."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.sections.confirmation import ExpertSectionConfirmation
from auditmanager.sections.routing import SectionRouteUnavailable
from auditmanager.sections.staged_routing import StagedSectionRoute, route_staged_section


VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
OTHER_VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RQ"
EXPERT = "usr_01M25P3TH08VVTTGJRXYBZZ7RP"
PS_PROFILE = "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
AR_PROFILE = "ap_01M25P3TH08VVTTGJRXYBZZ7RQ"
PB_PROFILE = "ap_01M25P3TH08VVTTGJRXYBZZ7RR"


def _route(
    *,
    stage: str | None = "P",
    confirmation: ExpertSectionConfirmation | None = None,
    profiles: object = None,
) -> StagedSectionRoute:
    if confirmation is None:
        confirmation = ExpertSectionConfirmation(VERSION, "PS", "P", EXPERT)
    if profiles is None:
        profiles = {"AR": AR_PROFILE, "PS": PS_PROFILE}
    return route_staged_section(
        version_uid=VERSION,
        project_stage=stage,
        confirmation=confirmation,
        available_profiles=profiles,
    )


@pytest.mark.parametrize("stage", ["P", "R"])
def test_same_version_and_stage_yield_an_immutable_exact_route_pin(stage: str) -> None:
    confirmation = ExpertSectionConfirmation(VERSION, "PS", stage, EXPERT)
    expected = StagedSectionRoute(VERSION, stage, "PS", PS_PROFILE)
    assert _route(stage=stage, confirmation=confirmation) == expected
    assert _route(stage=stage, confirmation=confirmation) == expected
    with pytest.raises(FrozenInstanceError):
        expected.section_code = "AR"


@pytest.mark.parametrize("stage", [None, "", "PR", "p"])
def test_missing_or_unclassified_version_stage_refuses(stage: str | None) -> None:
    with pytest.raises(SectionRouteUnavailable, match="version_stage_unclassified"):
        _route(stage=stage)


def test_conflicting_project_stage_cannot_route_same_version() -> None:
    with pytest.raises(SectionRouteUnavailable, match="section_confirmation_stage_mismatch"):
        _route(stage="R")


def test_foreign_version_confirmation_refuses_even_when_stage_agrees() -> None:
    confirmation = ExpertSectionConfirmation(OTHER_VERSION, "PS", "P", EXPERT)
    with pytest.raises(SectionRouteUnavailable, match="section_confirmation_version_mismatch"):
        _route(confirmation=confirmation)


def test_missing_confirmation_refuses_without_profile_fallback() -> None:
    with pytest.raises(SectionRouteUnavailable, match="section_unconfirmed"):
        route_staged_section(
            version_uid=VERSION, project_stage="P", confirmation=None,
            available_profiles={"AR": AR_PROFILE},
        )


def test_malformed_version_and_confirmation_type_refuse() -> None:
    confirmation = ExpertSectionConfirmation(VERSION, "PS", "P", EXPERT)
    with pytest.raises(SectionRouteUnavailable, match="version_identity_invalid"):
        route_staged_section(
            version_uid="bad-version", project_stage="P", confirmation=confirmation,
            available_profiles={"PS": PS_PROFILE},
        )
    with pytest.raises(SectionRouteUnavailable, match="section_confirmation_invalid"):
        route_staged_section(
            version_uid=VERSION, project_stage="P", confirmation="PS",  # type: ignore[arg-type]
            available_profiles={"PS": PS_PROFILE},
        )


def test_unavailable_ps_profile_never_selects_ar() -> None:
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        _route(profiles={"AR": AR_PROFILE})


def test_invalid_confirmer_identity_refuses_before_profile_lookup() -> None:
    confirmation = ExpertSectionConfirmation(VERSION, "PS", "P", "bad-user")
    with pytest.raises(SectionRouteUnavailable, match="section_confirmer_identity_invalid"):
        _route(confirmation=confirmation)


def test_unknown_section_and_invalid_profile_registry_refuse() -> None:
    confirmation = ExpertSectionConfirmation(VERSION, "ZZ", "P", EXPERT)
    with pytest.raises(SectionRouteUnavailable, match="section_unknown"):
        _route(confirmation=confirmation)
    with pytest.raises(SectionRouteUnavailable, match="section_profile_registry_invalid"):
        _route(profiles=[])


def test_a_different_section_cannot_inherit_ps_profile() -> None:
    """On a table built without PB (`PB-PROFILE-01`): PB is a section with no entry, here."""
    confirmation = ExpertSectionConfirmation(VERSION, "PB", "P", EXPERT)
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        _route(confirmation=confirmation)
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        _route(confirmation=replace(confirmation, code="AI"))


@pytest.mark.parametrize("stage", ["P", "R"])
def test_pb_routes_to_its_own_profile_at_either_stage(stage: str) -> None:
    confirmation = ExpertSectionConfirmation(VERSION, "PB", stage, EXPERT)
    profiles = {"AR": AR_PROFILE, "PS": PS_PROFILE, "PB": PB_PROFILE}
    assert _route(stage=stage, confirmation=confirmation, profiles=profiles) == StagedSectionRoute(
        VERSION, stage, "PB", PB_PROFILE
    )


def test_ps_and_ar_do_not_inherit_the_pb_profile() -> None:
    profiles = {"PB": PB_PROFILE}
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        _route(profiles=profiles)  # the default confirmation is PS
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        _route(
            confirmation=ExpertSectionConfirmation(VERSION, "AR", "P", EXPERT), profiles=profiles
        )
