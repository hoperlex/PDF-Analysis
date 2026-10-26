"""The reviewed AR v2 corpus stays narrow before runtime profile wiring."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from auditmanager.analysis.profiles.ar_shared import content
from auditmanager.analysis.profiles.ar_v2.response_schema import (
    CATEGORIES as AR_V2_CATEGORIES,
)
from auditmanager.analysis.profiles.ar_v3.response_schema import (
    NORMATIVE_CATEGORIES as AR_V3_NORMATIVE_CATEGORIES,
)


def test_reviewed_sections_are_fixed_and_match_the_frozen_category_enum() -> None:
    sections = content.reviewed_sections()
    assert len(sections) == 6
    assert len({section.source.legacy_path for section in sections}) == 6
    assert all(section.prompt_text for section in sections)
    assert content.reviewed_content_sha256() == content.reviewed_content_sha256()
    assert len(content.reviewed_content_sha256()) == 64

    category_text = next(
        section.prompt_text
        for section in sections
        if section.source.filename == "finding_categories.md"
    )
    named = re.findall(r"^- ([a-z_]+):", category_text, re.MULTILINE)
    api = json.loads(Path("contracts/api/v1/openapi.json").read_text())
    frozen = api["components"]["schemas"]["FindingCategory"]["enum"]
    # Since the normative-citation reseal the sealed enum holds twelve values:
    # the seven AR v2 emits ("exactly seven" in the reviewed prompt) followed by
    # the five normative ones that belong to AR v3. The AR v2 prompt names the
    # first seven, the ones its own response schema allows, and none of the rest.
    assert named == list(AR_V2_CATEGORIES)
    assert frozen == named + list(AR_V3_NORMATIVE_CATEGORIES)


def test_only_reviewed_prompt_blocks_are_returned() -> None:
    joined = "\n".join(section.prompt_text for section in content.reviewed_sections())
    assert "legacy_sha256" not in joined
    assert "Review:" not in joined
    assert "ГОСТ" not in joined
    assert not re.search(r"\bСП\s*\d|(?:≥|≤)|не менее\s*\d", joined)
    assert "Ф1.3" not in joined
    assert "только из дословно указанного текста" in joined
    assert "не предполагается по умолчанию" in joined
    assert "не выноси решение за эксперта" in joined


def test_tampered_or_missing_resource_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path(content.__file__).parent
    for source in content.REVIEWED_SOURCES:
        shutil.copyfile(original / source.filename, tmp_path / source.filename)
    monkeypatch.setattr(content, "_RESOURCE_DIR", tmp_path)

    target = tmp_path / "role.md"
    target.write_text(target.read_text() + "\nextra instruction\n")
    with pytest.raises(content.ProfileContentError, match="digest mismatch"):
        content.reviewed_sections()

    shutil.copyfile(original / "role.md", target)
    (tmp_path / "ar_checklist.md").unlink()
    with pytest.raises(content.ProfileContentError, match="unreadable"):
        content.reviewed_content_sha256()
