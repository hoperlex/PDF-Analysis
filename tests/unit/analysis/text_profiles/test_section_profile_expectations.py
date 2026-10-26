"""`PROD-14-0-EXPECTATIONS-01`: the one file that says which status and version each section's
package must declare, and the guard that it agrees with the packages.

``section_profile_expectations.json`` has one line per non-AR section package. The registry,
package and HTTP tests and the web ``analysis-settings`` test read it instead of pinning
``draft`` / ``1.0.0`` themselves, so a section lane that moves its profile out of ``draft``
changes that section's ``profile.json`` and one line here, and no shared test file.

This suite pins the file itself, read with ``json``/``pathlib`` only (like the package suite,
it does not import the registry loader's behaviour, only its ``PROJECT_STRUCTURE_ORDER``):

* the format, the key set of the file and of every line, one line per section in the file;
* exactly one line for every package that exists, none for AR, none for a section without a
  package, in the registry's order (``AI, PS, ... GP, PB``);
* the status and version on a line are the ones the package's ``profile.json`` declares.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from auditmanager.analysis.text.profile_registry import PROJECT_STRUCTURE_ORDER

ROOT = Path(__file__).resolve().parents[4]
PROFILES = ROOT / "src/auditmanager/analysis/text/profiles"
EXPECTATIONS = Path(__file__).resolve().with_name("section_profile_expectations.json")

FORMAT = "section-profile-expectations/1"
LINE_KEYS = frozenset({"code", "status", "profile_version"})
#: ``builtin`` is AR's alone and AR has no package; a package is ``draft`` or ``reviewed``.
PACKAGE_STATUSES = frozenset({"draft", "reviewed"})
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
REGISTRY_ORDER = tuple(code for code in PROJECT_STRUCTURE_ORDER if code != "AR")


def _document() -> dict[str, Any]:
    return json.loads(EXPECTATIONS.read_text("utf-8"))


def _declared() -> dict[str, tuple[str, str]]:
    """``code -> (status, profile_version)`` for every package on disk, from its ``profile.json``."""
    found: dict[str, tuple[str, str]] = {}
    for manifest in sorted(PROFILES.glob("*/profile.json")):
        data = json.loads(manifest.read_text("utf-8"))
        assert data["section_code"] not in found, f"{data['section_code']}: two packages"
        found[data["section_code"]] = (data["status"], data["profile_version"])
    return found


def test_the_file_has_the_expected_format_and_one_line_per_section() -> None:
    document = _document()
    assert set(document) == {"format", "about", "sections"}
    assert document["format"] == FORMAT
    assert isinstance(document["about"], str) and document["about"].strip()
    rows = document["sections"]
    assert isinstance(rows, list) and rows
    for row in rows:
        assert set(row) == LINE_KEYS, row
        assert all(isinstance(row[key], str) for key in LINE_KEYS), row
    # One physical line per section: a section lane's change is a one-line diff.
    text_lines = [line for line in EXPECTATIONS.read_text("utf-8").splitlines() if '"code"' in line]
    assert len(text_lines) == len(rows), "each section must be written on a line of its own"
    for line, row in zip(text_lines, rows, strict=True):
        assert json.loads(line.strip().rstrip(",")) == row, line


def test_the_vocabulary_is_a_package_status_and_a_three_part_version() -> None:
    for row in _document()["sections"]:
        assert row["status"] in PACKAGE_STATUSES, row
        assert SEMVER.fullmatch(row["profile_version"]), row


def test_one_line_per_section_in_the_registry_order_and_none_for_ar() -> None:
    codes = [row["code"] for row in _document()["sections"]]
    assert len(codes) == len(set(codes)), f"a section is written twice: {codes}"
    assert "AR" not in codes, "AR has no package; its status is builtin"
    assert codes == list(REGISTRY_ORDER)


def test_a_line_exists_for_every_package_and_a_package_for_every_line() -> None:
    expected = {row["code"]: row for row in _document()["sections"]}
    declared = _declared()
    assert set(declared) - set(expected) == set(), "a package has no line in the expectations file"
    assert set(expected) - set(declared) == set(), "a line has no package under profiles/"


def test_every_line_agrees_with_its_package_profile_json() -> None:
    expected = {row["code"]: row for row in _document()["sections"]}
    disagreements = {
        code: {"profile.json": declared, "expectations": (expected[code]["status"], expected[code]["profile_version"])}
        for code, declared in _declared().items()
        if code in expected and declared != (expected[code]["status"], expected[code]["profile_version"])
    }
    assert disagreements == {}, "profile.json and the expectations file disagree"
