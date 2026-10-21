"""`W59-SECTION-SEAL-01`: the section-keyed text-profile registry and its package loader.

Synthetic ``text-profile/1`` packages are written to a temporary directory by each case --
never under ``src`` -- so every refusal is shown on the exact defect it names. The last
cases load the real package root of this tree, whatever the profiles lane has put there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text.profile import AR_TEXT_PROFILE, resolve_profile
from auditmanager.analysis.text.profile_registry import (
    AUTHORED_SECTIONS,
    PACKAGE_FORMAT,
    PACKAGES_ROOT,
    SECTION_CODES,
    TextProfileLoadError,
    TextProfileUnavailable,
    load_text_profile_registry,
)
from auditmanager.analysis.text.prompt import (
    CATEGORIES,
    MAX_OUTPUT_TOKENS,
    RESPONSE_SCHEMA,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROMPT = "Ты — инструмент проверки синтетического раздела.\nОтвечай по схеме."


def _profile(code: str, **overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "format": PACKAGE_FORMAT,
        "section_code": code,
        "analysis_profile_id": "ap_01M5AXG1K82P9BCJ1NRYSTC2NA",
        "prompt_bundle_id": "pb_01M5AXG1K8EDTH597XY32Z696A",
        "profile_version": "1.0.0",
        "status": "draft",
        "title_ru": "Синтетический раздел",
        "source": {
            "repository": "synthetic",
            "commit": "0" * 40,
            "files": [{"path": "prompts/synthetic.md", "sha256": "a" * 64}],
        },
    }
    document.update(overrides)
    return document


def _package(root: Path, directory: str, profile: dict[str, Any], prompt: str = PROMPT + "\n") -> Path:
    path = root / directory
    path.mkdir(parents=True)
    (path / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    (path / "system_prompt.md").write_text(prompt, encoding="utf-8")
    return path


def test_section_codes_are_the_fifteen_of_the_contract_and_the_catalogue() -> None:
    contract = json.loads((REPOSITORY_ROOT / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    assert SECTION_CODES == frozenset(contract["components"]["schemas"]["ProjectSection"]["enum"])
    catalogue = json.loads(
        (REPOSITORY_ROOT / "src/auditmanager/sections/suggestion_patterns.json").read_text(encoding="utf-8")
    )
    assert SECTION_CODES == frozenset(entry["code"] for entry in catalogue["sections"])


def test_an_empty_root_registers_ar_from_the_v1_constants_alone(tmp_path: Path) -> None:
    registry = load_text_profile_registry(tmp_path)
    assert set(registry.entries) == {"AR"}
    assert registry.entries["AR"].profile is AR_TEXT_PROFILE
    assert registry.entries["AR"].status == "builtin"
    assert dict(registry.section_profiles()) == {
        "AR": (str(AR_TEXT_PROFILE.analysis_profile_id), str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id))
    }
    assert load_text_profile_registry(tmp_path / "absent").executable_sections() == {"AR"}


def test_a_package_keeps_v1_contract_and_replaces_only_the_system_prompt(tmp_path: Path) -> None:
    _package(tmp_path, "kj", _profile("KJ"))
    registry = load_text_profile_registry(tmp_path)
    entry = registry.entries["KJ"]
    bundle = entry.profile.prompt_bundle
    assert bundle.system_prompt == PROMPT, "exactly one trailing newline is stripped"
    assert bundle.response_schema == RESPONSE_SCHEMA and bundle.max_output_tokens == MAX_OUTPUT_TOKENS
    assert entry.profile.categories == CATEGORIES and entry.profile.discipline == "KJ"
    assert entry.profile.stage_id == AR_TEXT_PROFILE.stage_id
    assert entry.status == "draft" and entry.package == "kj"
    assert registry.resolve("ap_01M5AXG1K82P9BCJ1NRYSTC2NA", "pb_01M5AXG1K8EDTH597XY32Z696A") is entry.profile
    assert bundle.content_sha256 != AR_TEXT_PROFILE.prompt_bundle.content_sha256


def test_only_one_trailing_newline_is_stripped(tmp_path: Path) -> None:
    _package(tmp_path, "kj", _profile("KJ"), prompt=PROMPT + "\n\n")
    assert load_text_profile_registry(tmp_path).entries["KJ"].profile.prompt_bundle.system_prompt == PROMPT + "\n"


def test_resolve_needs_the_exact_pair_and_keeps_historical_ar(tmp_path: Path) -> None:
    _package(tmp_path, "kj", _profile("KJ"))
    registry = load_text_profile_registry(tmp_path)
    ar_profile, ar_bundle = registry.section_profiles()["AR"]
    assert registry.resolve(ar_profile, ar_bundle) is AR_TEXT_PROFILE
    assert resolve_profile(ar_profile) is AR_TEXT_PROFILE
    for pair in (
        (ar_profile, "pb_01M5AXG1K8EDTH597XY32Z696A"),
        ("ap_01M5AXG1K82P9BCJ1NRYSTC2NA", ar_bundle),
        ("ap_01M5AXG1K82P9BCJ1NRYSTC2NZ", "pb_01M5AXG1K8EDTH597XY32Z696Z"),
    ):
        with pytest.raises(TextProfileUnavailable):
            registry.resolve(*pair)


@pytest.mark.parametrize(
    ("directory", "profile", "reason"),
    [
        ("zz", _profile("ZZ"), "section_code_unknown"),
        ("kj", _profile("kj"), "section_code_unknown"),
        ("ov", _profile("KJ"), "package_directory_mismatch"),
        ("ar", _profile("AR"), "section_code_duplicate"),
        ("kj", _profile("KJ", format="text-profile/2"), "format_invalid"),
        ("kj", _profile("KJ", status="approved"), "status_invalid"),
        ("kj", _profile("KJ", profile_version="1.0"), "profile_version_invalid"),
        ("kj", _profile("KJ", analysis_profile_id="pb_01M5AXG1K82P9BCJ1NRYSTC2NA"), "identity_invalid"),
        ("kj", _profile("KJ", prompt_bundle_id="not-a-bundle"), "identity_invalid"),
        ("kj", _profile("KJ", title_ru=" "), "title_invalid"),
        ("kj", _profile("KJ", source={"repository": "x", "commit": "y", "files": []}), "source_files_invalid"),
        ("kj", _profile("KJ", source={"repository": "x", "commit": "y", "files": [{"path": "p", "sha256": "z"}]}), "source_files_invalid"),
        ("kj", {**_profile("KJ"), "extra": 1}, "profile_keys_invalid"),
    ],
)
def test_a_defective_package_refuses_the_whole_load(
    tmp_path: Path, directory: str, profile: dict[str, Any], reason: str
) -> None:
    _package(tmp_path, "ov", _profile(
        "OV", analysis_profile_id="ap_01M5AXG1KDVXRHH20N7KGBKPZA",
        prompt_bundle_id="pb_01M5AXG1KDEVEZ88HR6KYX2YPA",
    )) if directory != "ov" else None
    _package(tmp_path, directory, profile)
    with pytest.raises(TextProfileLoadError, match=reason):
        load_text_profile_registry(tmp_path)


def test_duplicate_sections_and_identities_refuse(tmp_path: Path) -> None:
    _package(tmp_path, "kj", _profile("KJ"))
    _package(tmp_path, "km", _profile("KM"))
    with pytest.raises(TextProfileLoadError, match="analysis_profile_id_duplicate"):
        load_text_profile_registry(tmp_path)
    other = tmp_path / "second"
    _package(other, "kj", _profile("KJ"))
    _package(other, "km", _profile("KM", analysis_profile_id="ap_01M5AXG1KB71SHN23H775AP55A"))
    with pytest.raises(TextProfileLoadError, match="prompt_bundle_id_duplicate"):
        load_text_profile_registry(other)


def test_an_empty_prompt_or_a_stray_file_refuses(tmp_path: Path) -> None:
    _package(tmp_path, "kj", _profile("KJ"), prompt="\n")
    with pytest.raises(TextProfileLoadError, match="system_prompt_empty"):
        load_text_profile_registry(tmp_path)
    other = tmp_path / "stray"
    path = _package(other, "kj", _profile("KJ"))
    (path / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(TextProfileLoadError, match="package_files_invalid"):
        load_text_profile_registry(other)


def test_private_entries_are_not_packages(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "README.md").write_text("not a package", encoding="utf-8")
    assert set(load_text_profile_registry(tmp_path).entries) == {"AR"}


def test_the_tree_registers_without_error_and_without_an_ar_package() -> None:
    """The real root: whatever packages the tree holds load, and AR stays the v1 constants."""
    registry = load_text_profile_registry()
    assert registry.entries["AR"].profile is AR_TEXT_PROFILE
    assert not (PACKAGES_ROOT / "ar").exists()
    for code, entry in registry.entries.items():
        if code == "AR":
            continue
        assert entry.package == code.lower() and entry.status in {"draft", "reviewed"}
        text = (PACKAGES_ROOT / entry.package / "system_prompt.md").read_text(encoding="utf-8")
        assert entry.profile.prompt_bundle.system_prompt == text.removesuffix("\n")


def test_the_tree_registers_all_fifteen_sections_pb_included() -> None:
    """`PB-PROFILE-01`: fire safety is routed to a profile of its own, not refused."""
    registry = load_text_profile_registry()
    assert set(registry.entries) == SECTION_CODES and len(registry.entries) == 15
    assert registry.executable_sections() == SECTION_CODES
    entry = registry.entries["PB"]
    assert entry.status == "draft", "no expert review exists: the status says so"
    assert entry.source is None and entry.package == "pb"
    assert entry.title_ru == "Пожарная безопасность"
    assert entry.profile.discipline == "PB"
    assert "«Пожарная безопасность» (ПБ)" in entry.profile.prompt_bundle.system_prompt
    assert (PACKAGES_ROOT / "pb" / "open_questions.md").read_text(encoding="utf-8").strip()


def test_pb_never_shares_an_identity_with_another_section() -> None:
    """A ПБ version never runs under another section's profile, nor another under ПБ."""
    registry = load_text_profile_registry()
    table = registry.section_profiles()
    pb_profile, pb_bundle = table["PB"]
    others = {code: pair for code, pair in table.items() if code != "PB"}
    assert all(pair != table["PB"] for pair in others.values())
    assert all(pair[0] != pb_profile and pair[1] != pb_bundle for pair in others.values())
    assert registry.resolve(pb_profile, pb_bundle) is registry.entries["PB"].profile
    for code, (profile, bundle) in others.items():
        assert registry.resolve(profile, bundle).discipline != "PB", code
        with pytest.raises(TextProfileUnavailable):
            registry.resolve(pb_profile, bundle)  # PB's profile with another section's bundle
        with pytest.raises(TextProfileUnavailable):
            registry.resolve(profile, pb_bundle)


# --- authored packages: no legacy source, declared (PB-PROFILE-01) -------------------------

QUESTIONS = "1. Вопрос эксперту.\n"


def _authored_profile(**overrides: Any) -> dict[str, Any]:
    document = _profile("PB", analysis_profile_id="ap_01M5AXG1K82P9BCJ1NRYSTC2NB",
                        prompt_bundle_id="pb_01M5AXG1K8EDTH597XY32Z696B", source=None)
    document.update(overrides)
    return document


def _authored(root: Path, profile: dict[str, Any] | None = None, questions: str | None = QUESTIONS) -> Path:
    path = _package(root, "pb", _authored_profile() if profile is None else profile)
    if questions is not None:
        (path / "open_questions.md").write_text(questions, encoding="utf-8")
    return path


def test_the_authored_sections_are_exactly_pb() -> None:
    assert AUTHORED_SECTIONS == frozenset({"PB"})
    assert AUTHORED_SECTIONS <= SECTION_CODES


def test_an_authored_package_with_a_null_source_and_its_questions_loads(tmp_path: Path) -> None:
    _authored(tmp_path)
    registry = load_text_profile_registry(tmp_path)
    entry = registry.entries["PB"]
    assert entry.source is None and entry.status == "draft" and entry.package == "pb"
    assert entry.profile.discipline == "PB" and entry.profile.prompt_bundle.system_prompt == PROMPT
    assert registry.executable_sections() == {"AR", "PB"}
    assert registry.resolve("ap_01M5AXG1K82P9BCJ1NRYSTC2NB", "pb_01M5AXG1K8EDTH597XY32Z696B") is entry.profile


@pytest.mark.parametrize(
    ("builder", "reason"),
    [
        pytest.param(
            lambda root: _authored(root, _authored_profile(source=_profile("PB")["source"])),
            "source_declared_for_authored_section", id="authored section with a source",
        ),
        pytest.param(
            lambda root: _authored(root, questions=None),
            "open_questions_missing", id="authored package without questions",
        ),
        pytest.param(
            lambda root: _authored(root, questions=" \n\n"),
            "open_questions_empty", id="authored package with blank questions",
        ),
        pytest.param(
            lambda root: _package(root, "kj", _profile("KJ", source=None)),
            "source_invalid", id="legacy section declaring no source",
        ),
    ],
)
def test_authored_declarations_are_checked_both_ways(
    tmp_path: Path, builder: Any, reason: str
) -> None:
    builder(tmp_path)
    with pytest.raises(TextProfileLoadError, match=reason):
        load_text_profile_registry(tmp_path)


def test_a_legacy_package_may_not_carry_the_authored_questions_file(tmp_path: Path) -> None:
    path = _package(tmp_path, "kj", _profile("KJ"))
    (path / "open_questions.md").write_text(QUESTIONS, encoding="utf-8")
    with pytest.raises(TextProfileLoadError, match="package_files_invalid"):
        load_text_profile_registry(tmp_path)


def test_a_missing_source_key_is_not_a_declaration(tmp_path: Path) -> None:
    profile = _authored_profile()
    del profile["source"]
    _authored(tmp_path, profile)
    with pytest.raises(TextProfileLoadError, match="profile_keys_invalid"):
        load_text_profile_registry(tmp_path)


def test_an_authored_package_refuses_a_stray_file(tmp_path: Path) -> None:
    path = _authored(tmp_path)
    (path / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(TextProfileLoadError, match="package_files_invalid"):
        load_text_profile_registry(tmp_path)
