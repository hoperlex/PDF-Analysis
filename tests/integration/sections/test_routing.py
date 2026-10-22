"""A suggestion or another version's confirmation cannot route a run."""

from __future__ import annotations

import pytest

from auditmanager.sections.routing import (
    ConfirmedSection,
    SectionRoute,
    SectionRouteUnavailable,
    route_confirmed_section,
)
from auditmanager.sections.suggestion import suggest_sections


VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
OTHER_VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RQ"
AR_PROFILE = "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
PS_PROFILE = "ap_01M25P3TH08VVTTGJRXYBZZ7RQ"
PB_PROFILE = "ap_01M25P3TH08VVTTGJRXYBZZ7RR"


def test_filename_suggestion_cannot_route_without_a_confirmed_section() -> None:
    assert suggest_sections("01-АР-Планы.pdf", "")[0].code == "AR"
    with pytest.raises(SectionRouteUnavailable, match="section_unconfirmed"):
        route_confirmed_section(VERSION, None, {"AR": AR_PROFILE})


def test_explicit_section_may_differ_from_suggestion_without_ar_fallback() -> None:
    assert suggest_sections("01-АР-Планы.pdf", "")[0].code == "AR"
    confirmed = ConfirmedSection(VERSION, "PS")
    assert route_confirmed_section(
        VERSION, confirmed, {"AR": AR_PROFILE, "PS": PS_PROFILE}
    ) == SectionRoute("PS", PS_PROFILE)
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        route_confirmed_section(VERSION, confirmed, {"AR": AR_PROFILE})


def test_confirmation_is_bound_to_one_document_version() -> None:
    with pytest.raises(SectionRouteUnavailable, match="version_mismatch"):
        route_confirmed_section(
            VERSION, ConfirmedSection(OTHER_VERSION, "AR"), {"AR": AR_PROFILE}
        )


@pytest.mark.parametrize("code", ["unknown", "", "ПБ"])
def test_unknown_code_never_uses_ar_profile(code: str) -> None:
    with pytest.raises(SectionRouteUnavailable, match="section_unknown"):
        route_confirmed_section(VERSION, ConfirmedSection(VERSION, code), {"AR": AR_PROFILE})


def test_valid_but_unavailable_pb_does_not_use_ps_or_ar() -> None:
    """The router's own refusal, on a table built without PB (`PB-PROFILE-01`).

    PB now has a registered profile, so the seam for "a section with no profile" is the table
    handed to the router, not the section: the refusal itself is unchanged.
    """
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        route_confirmed_section(
            VERSION,
            ConfirmedSection(VERSION, "PB"),
            {"AR": AR_PROFILE, "PS": PS_PROFILE},
        )


def test_pb_routes_to_its_own_profile_when_one_is_registered() -> None:
    profiles = {"AR": AR_PROFILE, "PS": PS_PROFILE, "PB": PB_PROFILE}
    assert route_confirmed_section(
        VERSION, ConfirmedSection(VERSION, "PB"), profiles
    ) == SectionRoute("PB", PB_PROFILE)


@pytest.mark.parametrize("code", ["AR", "PS"])
def test_another_section_never_runs_under_the_pb_profile(code: str) -> None:
    profiles = {"AR": AR_PROFILE, "PS": PS_PROFILE, "PB": PB_PROFILE}
    route = route_confirmed_section(VERSION, ConfirmedSection(VERSION, code), profiles)
    assert route.analysis_profile_id == profiles[code] != PB_PROFILE
    with pytest.raises(SectionRouteUnavailable, match="section_profile_unavailable"):
        route_confirmed_section(VERSION, ConfirmedSection(VERSION, code), {"PB": PB_PROFILE})


def test_invalid_profile_identity_is_refused() -> None:
    with pytest.raises(SectionRouteUnavailable, match="section_profile_invalid"):
        route_confirmed_section(VERSION, ConfirmedSection(VERSION, "AR"), {"AR": "legacy-ar"})
