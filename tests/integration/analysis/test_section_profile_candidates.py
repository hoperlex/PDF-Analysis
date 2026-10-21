"""Legacy section metadata is vocabulary, not an active profile or rulebook."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.analysis.profiles.section_candidates import load_candidates
from auditmanager.analysis.profiles.section_candidates.metadata import (
    CandidateMetadataError,
    _read_catalogue,
)


RESOURCE = Path(__file__).resolve().parents[3] / (
    "src/auditmanager/analysis/profiles/section_candidates/metadata.json"
)
LEGACY_CODES = {
    "AI", "AR", "EOM", "GP", "ITP", "KJ", "KM", "OV", "POS",
    "PS", "PT", "SS", "TX", "VK",
}


def test_fourteen_legacy_candidates_and_no_implicit_pb_profile() -> None:
    candidates = load_candidates()
    assert {item.code for item in candidates} == LEGACY_CODES
    assert len(candidates) == 14
    assert sum(len(item.categories) for item in candidates) == 162
    assert sum(len(item.sheet_types) for item in candidates) == 201
    assert next(item.name for item in candidates if item.code == "PS") == "Пояснительная записка"
    assert all(item.source_sha256 for item in candidates)


def test_resource_contains_no_prompt_or_normative_prose() -> None:
    data = json.loads(RESOURCE.read_text(encoding="utf-8"))
    for section in data["sections"]:
        assert set(section) == {
            "code", "name", "categories", "sheet_types", "source_sha256"
        }
        assert set(section["source_sha256"]) >= {
            "role.md", "checklist.md", "finding_categories.md", "drawing_types.md"
        }
        assert all(set(sheet) == {"code", "label"} for sheet in section["sheet_types"])


def test_tampered_or_missing_catalogue_is_refused(tmp_path: Path) -> None:
    candidate = tmp_path / "metadata.json"
    with pytest.raises(CandidateMetadataError, match="unreadable"):
        _read_catalogue(candidate)
    candidate.write_bytes(RESOURCE.read_bytes() + b" ")
    with pytest.raises(CandidateMetadataError, match="digest_mismatch"):
        _read_catalogue(candidate)


def test_all_results_are_immutable_values() -> None:
    first = load_candidates()
    assert first is load_candidates()
    with pytest.raises(AttributeError):
        first[0].code = "PB"  # type: ignore[misc]
