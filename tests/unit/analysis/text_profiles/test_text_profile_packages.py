"""W59-SECTION-PROFILES-01: every non-AR section text-profile package is well formed.

The packages under ``src/auditmanager/analysis/text/profiles/<code>/`` are data
(``profile.json`` + ``system_prompt.md``, format ``text-profile/1``). The section-keyed
registry that serves them belongs to ``W59-SECTION-SEAL-01`` and is deliberately not
imported here: this suite reads the files with ``json``/``pathlib`` only, so it holds
before and after that registry lands.

What it pins:

* exactly the thirteen sections with legacy source material have a legacy package, PB
  (`PB-PROFILE-01`) has the one authored package, AR has none, and no section code is
  duplicated or outside the 15-code catalogue;
* identities are fresh, parse as their contract types and are unique;
* every profile's ``status`` and ``profile_version`` are the ones its line of
  ``section_profile_expectations.json`` names (all ``draft`` at ``1.0.0`` until a section's
  expert review moves its line), and there is a line for exactly the packages that exist;
  each legacy profile's source files are hash-pinned, both
  against the already-catalogued candidate metadata and, when the legacy repository is on
  this host, against the blob at the recorded commit; the authored profile declares
  ``"source": null`` and carries ``open_questions.md`` instead;
* every system prompt keeps v1's question, its two categories and its output contract
  byte-for-byte, and names no category or machine field beyond v1's.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text.prompt import CATEGORIES, PROMPT_BUNDLE_ID, RESPONSE_SCHEMA, SYSTEM_PROMPT
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId

ROOT = Path(__file__).resolve().parents[4]
PROFILES = ROOT / "src/auditmanager/analysis/text/profiles"
CATALOGUE = ROOT / "src/auditmanager/sections/suggestion_patterns.json"
CANDIDATES = ROOT / "src/auditmanager/analysis/profiles/section_candidates/metadata.json"
#: One line per package: the status and version its ``profile.json`` must declare
#: (`PROD-14-0-EXPECTATIONS-01`). A section lane edits its own line, not this suite.
EXPECTATIONS = Path(__file__).resolve().with_name("section_profile_expectations.json")
LEGACY = Path(os.environ.get("AUDITMANAGER_LEGACY_PROMPTS_REPO", "/root/projects/PDF-proverka"))

EXPECTED_SECTIONS = frozenset(
    {"AI", "PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP"}
)
AUTHORED_SECTIONS = frozenset({"PB"})
NO_PACKAGE = frozenset({"AR"})
PROFILE_KEYS = frozenset(
    {
        "format",
        "section_code",
        "analysis_profile_id",
        "prompt_bundle_id",
        "profile_version",
        "status",
        "title_ru",
        "source",
    }
)
#: `SECTION-CATEGORY-OCR-01` (`R-146ao`): the five sections that may report a same-document omission under the
#: existing category `documentation`. They are `text-profile/2` packages with a `categories` key; the other
#: nine stay `text-profile/1` and byte-identical.
OMISSION_SECTIONS = frozenset({"AI", "TX", "EOM", "SS", "ITP"})
OMISSION_CATEGORIES = ["internal_contradiction", "explicit_placeholder", "documentation"]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID_LITERAL = re.compile(r"\b(?:ap|pb)_[0-9A-HJKMNP-TV-Z]{26}\b")
SNAKE_TOKEN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def _expected_sections() -> dict[str, tuple[str, str]]:
    """``code -> (status, profile_version)`` for every non-AR package of this tree."""
    rows = json.loads(EXPECTATIONS.read_text("utf-8"))["sections"]
    return {row["code"]: (row["status"], row["profile_version"]) for row in rows}


def _catalogue() -> dict[str, str]:
    data = json.loads(CATALOGUE.read_text("utf-8"))
    return {entry["code"]: entry["name"] for entry in data["sections"]}


def _packages() -> list[tuple[Path, dict[str, Any]]]:
    """Every directory under ``profiles/`` that carries a ``profile.json``."""
    found = []
    for directory in sorted(path for path in PROFILES.iterdir() if path.is_dir()):
        manifest = directory / "profile.json"
        if manifest.is_file():
            found.append((directory, json.loads(manifest.read_text("utf-8"))))
    return found


def _legacy_packages() -> list[tuple[Path, dict[str, Any]]]:
    """The packages ported from the legacy repository: every one except the authored."""
    return [
        (directory, manifest)
        for directory, manifest in _packages()
        if manifest.get("section_code") not in AUTHORED_SECTIONS
    ]


def _authored_packages() -> list[tuple[Path, dict[str, Any]]]:
    return [
        (directory, manifest)
        for directory, manifest in _packages()
        if manifest.get("section_code") in AUTHORED_SECTIONS
    ]


def _v1_block(start: str, end: str) -> str:
    """A verbatim slice of v1's SYSTEM_PROMPT from ``start`` up to (not including) ``end``."""
    head = SYSTEM_PROMPT.index(start)
    return SYSTEM_PROMPT[head : SYSTEM_PROMPT.index(end, head)]


def _schema_field_names(node: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.get("properties", {}).items():
            names.add(key)
            names |= _schema_field_names(value)
        if "items" in node:
            names |= _schema_field_names(node["items"])
    return names


V1_QUESTION = _v1_block("ЕДИНСТВЕННЫЙ вопрос", "Ровно две категории")
V1_CATEGORIES = _v1_block("Ровно две категории", "\n\n")
V1_OUTPUT_CONTRACT = SYSTEM_PROMPT[SYSTEM_PROMPT.index("Требования к ответу:") :]
V1_CONDITIONS = (
    "Прежде чем сообщить находку, проверь каждое из пяти условий. Если выполняется хотя бы\n"
    "одно — находки нет:\n1. Разные объекты.",
    "\n2. Разные признаки.",
    "\n3. Совпадающие значения. Повторение одного и того же значения в разных разделах — это\n"
    "   согласованность, а не расхождение.\n4. Решение приведено в другом месте.",
    "\n5. Утверждения просто нет. Если документ ничего не говорит о чём-то — это не находка.\n"
    "   Ты не решаешь, что должно было быть указано.\n",
    "Ты не выносишь вердикт: принять или отклонить наблюдение решает эксперт.\n\n",
)
SCHEMA_FIELDS = _schema_field_names(RESPONSE_SCHEMA)
ALLOWED_SNAKE_TOKENS = frozenset(CATEGORIES) | {name for name in SCHEMA_FIELDS if "_" in name}


def test_the_v1_contract_anchors_this_suite_reads_exist() -> None:
    # Guard the guard: if v1's prompt is reworded, the slices above must not silently
    # become empty and make every comparison below vacuous.
    assert V1_QUESTION.startswith("ЕДИНСТВЕННЫЙ вопрос") and len(V1_QUESTION) > 100
    assert all(f"- {category} —" in V1_CATEGORIES for category in CATEGORIES)
    assert V1_OUTPUT_CONTRACT.startswith("Требования к ответу:") and "observations" in V1_OUTPUT_CONTRACT
    assert all(fragment in SYSTEM_PROMPT for fragment in V1_CONDITIONS)
    assert {"observations", "category", "finding_text", "recommendation_text", "evidence", "quote", "page_number"} <= SCHEMA_FIELDS


def test_exactly_the_thirteen_legacy_sections_and_pb_have_a_package() -> None:
    codes = [manifest.get("section_code") for _, manifest in _packages()]
    assert len(codes) == len(set(codes)), f"duplicate section_code across packages: {sorted(codes)}"
    assert set(codes) == EXPECTED_SECTIONS | AUTHORED_SECTIONS
    assert not NO_PACKAGE & set(codes)
    expected = _expected_sections()
    assert set(codes) - set(expected) == set(), "a package has no line in the expectations file"
    assert set(expected) - set(codes) == set(), "a line of the expectations file has no package"
    assert {manifest["section_code"] for _, manifest in _legacy_packages()} == EXPECTED_SECTIONS
    assert {manifest["section_code"] for _, manifest in _authored_packages()} == AUTHORED_SECTIONS
    catalogue = _catalogue()
    assert len(catalogue) == 15
    assert EXPECTED_SECTIONS | AUTHORED_SECTIONS | NO_PACKAGE == set(catalogue)
    for code in EXPECTED_SECTIONS:
        assert (PROFILES / code.lower() / "profile.json").is_file(), code
        assert (PROFILES / code.lower() / "system_prompt.md").is_file(), code
        assert not (PROFILES / code.lower() / "open_questions.md").exists(), code
    for code in AUTHORED_SECTIONS:
        for name in ("profile.json", "system_prompt.md", "open_questions.md"):
            assert (PROFILES / code.lower() / name).is_file(), (code, name)
    for code in NO_PACKAGE:
        assert not (PROFILES / code.lower() / "profile.json").exists(), code
        assert not (PROFILES / code.lower() / "system_prompt.md").exists(), code


def test_every_profile_manifest_has_the_text_profile_1_shape() -> None:
    catalogue = _catalogue()
    expected = _expected_sections()
    for directory, manifest in _legacy_packages():
        code = manifest["section_code"]
        if code in OMISSION_SECTIONS:
            assert set(manifest) == PROFILE_KEYS | {"categories"}, directory.name
            assert manifest["format"] == "text-profile/2", code
            assert manifest["categories"] == OMISSION_CATEGORIES, code
        else:
            assert set(manifest) == PROFILE_KEYS, directory.name
            assert manifest["format"] == "text-profile/1", code
        assert code in catalogue, code
        assert directory.name == code.lower(), (directory.name, code)
        assert code in expected, f"{code}: no line in the expectations file"
        assert manifest["profile_version"] == expected[code][1], (
            f"{code}: profile.json declares version {manifest['profile_version']!r}, "
            f"the expectations file {expected[code][1]!r}"
        )
        assert manifest["status"] == expected[code][0], (
            f"{code}: profile.json declares status {manifest['status']!r}, "
            f"the expectations file {expected[code][0]!r}"
        )
        assert manifest["title_ru"] == catalogue[code], code
        source = manifest["source"]
        assert set(source) == {"repository", "commit", "files"}, code
        assert source["repository"] == "PDF-proverka", code
        assert HEX40.match(source["commit"]), code
        paths = [entry["path"] for entry in source["files"]]
        assert paths and len(paths) == len(set(paths)), code
        for entry in source["files"]:
            assert set(entry) == {"path", "sha256"}, code
            assert entry["path"].startswith(f"prompts/disciplines/{code}/"), entry["path"]
            assert HEX64.match(entry["sha256"]), entry["path"]
        assert {f"prompts/disciplines/{code}/{name}" for name in ("role.md", "checklist.md")} <= set(paths), code


def test_the_authored_profile_declares_no_source_and_the_expected_status() -> None:
    catalogue = _catalogue()
    expected_status, expected_version = _expected_sections()["PB"]
    (directory, manifest), = _authored_packages()
    assert manifest["section_code"] == "PB" and directory.name == "pb"
    assert set(manifest) == PROFILE_KEYS, "the key set is the legacy one: source is declared null"
    assert manifest["source"] is None
    assert manifest["format"] == "text-profile/1"
    assert manifest["profile_version"] == expected_version, (
        f"PB: profile.json declares version {manifest['profile_version']!r}, the expectations file {expected_version!r}"
    )
    assert manifest["status"] == expected_status, (
        f"PB: profile.json declares status {manifest['status']!r}, the expectations file {expected_status!r}"
    )
    assert manifest["title_ru"] == catalogue["PB"] == "Пожарная безопасность"


def test_all_legacy_packages_name_one_legacy_commit() -> None:
    assert len({manifest["source"]["commit"] for _, manifest in _legacy_packages()}) == 1


def test_identities_parse_are_fresh_and_unique() -> None:
    profile_ids: list[str] = []
    bundle_ids: list[str] = []
    for _, manifest in _packages():
        profile_ids.append(str(AnalysisProfileId.parse(manifest["analysis_profile_id"])))
        bundle_ids.append(str(PromptBundleId.parse(manifest["prompt_bundle_id"])))
    ours = profile_ids + bundle_ids
    assert len(ours) == len(set(ours)) == 2 * len(EXPECTED_SECTIONS | AUTHORED_SECTIONS)
    assert str(PROMPT_BUNDLE_ID) not in ours
    # No identity literal anywhere else in the source tree (AR v1, AR v2/v3, fixtures in
    # code) may be reused by a package.
    elsewhere: set[str] = set()
    for path in (ROOT / "src/auditmanager").rglob("*.py"):
        elsewhere.update(ID_LITERAL.findall(path.read_text("utf-8")))
    assert elsewhere, "the scan found no identity literal at all; it is reading the wrong tree"
    assert not elsewhere & set(ours)


def test_source_hashes_agree_with_the_catalogued_candidate_metadata() -> None:
    catalogued = {
        entry["code"]: entry["source_sha256"]
        for entry in json.loads(CANDIDATES.read_text("utf-8"))["sections"]
    }
    for _, manifest in _legacy_packages():
        code = manifest["section_code"]
        for entry in manifest["source"]["files"]:
            name = entry["path"].rsplit("/", 1)[1]
            assert catalogued[code][name] == entry["sha256"], entry["path"]


def test_source_files_exist_at_the_recorded_legacy_commit() -> None:
    if not (LEGACY / ".git").exists():
        pytest.skip(f"legacy repository {LEGACY} is not on this host; hash-at-commit check skipped")
    checked = 0
    for _, manifest in _legacy_packages():
        commit = manifest["source"]["commit"]
        for entry in manifest["source"]["files"]:
            blob = subprocess.run(
                ["git", "-C", str(LEGACY), "show", f"{commit}:{entry['path']}"],
                check=True,
                capture_output=True,
            ).stdout
            assert hashlib.sha256(blob).hexdigest() == entry["sha256"], entry["path"]
            checked += 1
    assert checked >= 2 * len(EXPECTED_SECTIONS)


def test_every_system_prompt_keeps_the_v1_question_categories_and_output_contract() -> None:
    catalogue = _catalogue()
    for directory, manifest in _packages():
        code = manifest["section_code"]
        text = (directory / "system_prompt.md").read_text("utf-8")
        assert text.strip(), code
        assert "\r" not in text and text.endswith("\n") and not text.endswith("\n\n"), code
        body = text[:-1]
        opening = " ".join(body.split("\n\n", 1)[0].split())
        assert f"«{catalogue[code]}»" in opening, code
        assert "«Архитектурные решения» (АР)" not in body, code
        assert V1_QUESTION in body, code
        assert V1_CATEGORIES in body, code
        assert body.endswith(V1_OUTPUT_CONTRACT), code
        position = 0
        for fragment in V1_CONDITIONS:
            found = body.find(fragment, position)
            assert found >= 0, (code, fragment[:40])
            position = found + len(fragment)
        for category in CATEGORIES:
            assert category in body, (code, category)
        for field in SCHEMA_FIELDS:
            assert field in body, (code, field)
        stray = set(SNAKE_TOKEN.findall(body)) - ALLOWED_SNAKE_TOKENS
        assert not stray, (code, sorted(stray))
        assert "```" not in body and "{" not in body, code


# --- the authored profile (PB-PROFILE-01) -------------------------------------------------

#: The only numbers the authored prompt may carry besides its numbered conditions: the two norm
#: identifiers it names as families the model must NOT check against.
ALLOWED_PB_NUMBERS = frozenset({"123", "13130"})
#: The areas the task names for fire safety, each by a phrase that occurs in exactly one hint
#: bullet (whitespace-normalised), so dropping a bullet cannot be hidden by a word used elsewhere.
PB_AREAS = {
    "evacuation": "число, ширина в свету и расположение эвакуационных выходов",
    "fire resistance": "предел огнестойкости и класс пожарной опасности одной и той же строительной",
    "fire compartments": "границы, площадь и число этажей одного и того же пожарного отсека",
    "fire-fighting access": "ширина проезда для пожарной техники",
    "smoke control": "одной и той же системы противодымной защиты",
}


def _pb_prompt() -> str:
    return (PROFILES / "pb" / "system_prompt.md").read_text("utf-8")


def test_the_pb_prompt_covers_each_named_fire_safety_area() -> None:
    hints = _pb_prompt().split("Где в документе раздела ПБ", 1)[1].split("Прежде чем сообщить", 1)[0]
    hints = " ".join(hints.split())
    for area, marker in PB_AREAS.items():
        assert hints.count(marker) == 1, area


def test_the_pb_prompt_invents_no_requirement_number() -> None:
    """No clause, limit or class threshold: the only numerals are the two norm identifiers."""
    body = re.sub(r"(?m)^\s*[1-5]\. ", "", _pb_prompt())
    found = set(re.findall(r"\d+", body))
    assert found == ALLOWED_PB_NUMBERS, sorted(found)
    # And the identifiers appear only as families the model is told not to check.
    for sentence in re.findall(r"Ты НЕ проверяешь[^.]*\.", " ".join(body.split())):
        assert "123-ФЗ" in sentence and "13130" in sentence
    assert body.count("123") == 1 and body.count("13130") == 1


def test_pb_open_questions_are_listed_in_the_package() -> None:
    text = (PROFILES / "pb" / "open_questions.md").read_text("utf-8")
    questions = re.findall(r"(?m)^\d+\. ", text)
    assert len(questions) >= 8, "the package must list the expert's open questions"
    assert [int(n.rstrip(". ")) for n in questions] == list(range(1, len(questions) + 1))
    # Honest about what the profile is while it is a draft: no expert review, evidence or recordings.
    if _expected_sections()["PB"][0] == "draft":
        assert "`draft`" in text
    assert "D-178" in text
    assert "\r" not in text and text.endswith("\n")
