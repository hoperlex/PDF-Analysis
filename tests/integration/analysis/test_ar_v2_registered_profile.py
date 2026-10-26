"""The recorded AR v2 registration fails closed on identity or content drift."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from auditmanager.analysis.profiles.ar_shared import content, v2_identities
from auditmanager.analysis.profiles.ar_v2 import registered
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE


def test_exact_registration_binds_reviewed_material_and_stage_plan() -> None:
    profile = registered.resolve_recorded_profile(
        v2_identities.PROFILE_ID, v2_identities.PROMPT_BUNDLE_ID
    )

    assert profile.analysis_profile_id != AR_TEXT_PROFILE.analysis_profile_id
    assert profile.prompt_bundle_id != AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id
    assert profile.provider_mode == "recorded"
    assert profile.stage_plan == (
        "source_preparation", "page_geometry_extraction", "document_context_build",
        "text_analysis", "finding_merge",
    )
    assert len(profile.categories) == 7
    assert profile.reviewed_content_sha256 == registered.REVIEWED_CONTENT_SHA256
    assert profile.response_schema_sha256 == registered.SCHEMA_SHA256
    assert profile.material_sha256 == registered.MATERIAL_SHA256
    assert profile.content_sha256 == registered.PROFILE_CONTENT_SHA256
    assert profile == registered.resolve_recorded_profile(
        str(v2_identities.PROFILE_ID), str(v2_identities.PROMPT_BUNDLE_ID)
    )
    with pytest.raises(FrozenInstanceError):
        profile.provider_mode = "live"  # type: ignore[misc]


@pytest.mark.parametrize("wrong", ["ap_01M25P3TH08VVTTGJRXYBZZ7RP", "ap_invalid"])
def test_wrong_profile_identity_is_refused(wrong: str) -> None:
    with pytest.raises(registered.RecordedProfileError, match="not registered"):
        registered.resolve_recorded_profile(wrong, v2_identities.PROMPT_BUNDLE_ID)


def test_wrong_bundle_identity_is_refused() -> None:
    with pytest.raises(registered.RecordedProfileError, match="not registered"):
        registered.resolve_recorded_profile(
            v2_identities.PROFILE_ID, "pb_01M25P3TH0PDQYVKTRQFEM0CYS"
        )


@pytest.mark.parametrize(
    "name,changed",
    [
        ("reviewed_content_sha256", "0" * 64),
        ("material_sha256", "0" * 64),
        ("_profile_content_sha256", "0" * 64),
    ],
)
def test_changed_reviewed_inputs_are_refused(
    monkeypatch: pytest.MonkeyPatch, name: str, changed: str
) -> None:
    monkeypatch.setattr(registered, name, lambda: changed)
    with pytest.raises(registered.RecordedProfileError, match="material has changed"):
        registered.resolve_recorded_profile(
            v2_identities.PROFILE_ID, v2_identities.PROMPT_BUNDLE_ID
        )


def test_changed_schema_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registered, "response_schema", lambda: {"type": "null"})
    with pytest.raises(registered.RecordedProfileError, match="material has changed"):
        registered.resolve_recorded_profile(
            v2_identities.PROFILE_ID, v2_identities.PROMPT_BUNDLE_ID
        )


def test_changed_reviewed_resource_bytes_are_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for source in content.REVIEWED_SOURCES:
        raw = (content._RESOURCE_DIR / source.filename).read_bytes()
        if source == content.REVIEWED_SOURCES[0]:
            raw += b"\nchanged"
        (tmp_path / source.filename).write_bytes(raw)
    monkeypatch.setattr(content, "_RESOURCE_DIR", tmp_path)

    with pytest.raises(content.ProfileContentError, match="digest mismatch"):
        registered.resolve_recorded_profile(
            v2_identities.PROFILE_ID, v2_identities.PROMPT_BUNDLE_ID
        )
