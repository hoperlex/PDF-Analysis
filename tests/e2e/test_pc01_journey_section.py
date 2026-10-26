"""`PROD-10B-JOURNEY-REBASE-01`: the journey runs on a section that stays, and says which steps cannot.

`PROD-11` removes the АР v1 run. The live journey (``tests/e2e/pc01/journey/``), its Python
twin (``tests/e2e/pc01/driver.py`` and ``test_acceptance.py``) and the manual protocol all
started a run on a version confirmed as АР. They now confirm ``driver.JOURNEY_SECTION`` --
ПБ -- and this file holds the four things that make that move checkable **without a browser
and without a stand**, the only two things this lane has:

1. *The chosen section's recorded answer is the AR baseline's answer.* Every figure the
   acceptance suite pinned on the AR run (three findings, five pieces of evidence, the
   categories, the pages and the quotations) was measured on the canonical recording. A
   section whose recording over the same text layer carries the same findings keeps every
   one of those pins and every assertion of the manifest that reads a finding, a comparison
   row, a carried decision, an export or a dashboard count. Compared here category for
   category and quotation for quotation, and the two pins that the acceptance suite states
   as literals are read from it and held to the recording.
2. *The chosen section is the one every classification of the main flow names*, is registered
   and ``reviewed`` (the journey's settings step asserts that row), and is not the section the
   «Оптимизация разделов» refusal step uses as its empty one.
3. *What cannot move is named.* The project's «Оптимизация» tab and the АР Form-7 exist for АР
   only and read the saved text of a published АР run. ``write.ar_bound`` in the manifest lists
   those steps; nothing else in the write half may name АР, classify a version as АР, or start a
   run on one -- and a pass or a specification read must be addressed to a document that an
   earlier step classified АР (the step ``optimisation-pass-over-a-set-without-a-table`` was
   silently bound to the journey's own set, now ПБ, until this file said so).
4. *The documents that describe the journey say the same section.*

What none of this proves: that a ПБ run publishes on a stand, that the screens render what the
manifest says, or what a live model finds under the ПБ profile. Those are ``verify live`` items
in ``docs/program/PROD-10B-JOURNEY-REBASE-01.md``.
"""

from __future__ import annotations

import ast
import copy
import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
JOURNEY_DIR = REPOSITORY_ROOT / "tests" / "e2e" / "pc01" / "journey"
MANIFEST = JOURNEY_DIR / "manifest.json"
README = JOURNEY_DIR / "README.md"
DRIVER = REPOSITORY_ROOT / "tests" / "e2e" / "pc01" / "driver.py"
ACCEPTANCE = REPOSITORY_ROOT / "tests" / "e2e" / "pc01" / "test_acceptance.py"
MANUAL_PROTOCOL = REPOSITORY_ROOT / "docs" / "manual-tests" / "ALPHA_PUBLIC_ACCEPTANCE.md"
SECTION_RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections"
CANONICAL_RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"
EXPECTATIONS = (
    REPOSITORY_ROOT / "tests" / "unit" / "analysis" / "text_profiles"
    / "section_profile_expectations.json"
)

#: The Russian abbreviation the screens and the documents use for the journey's section. A
#: new section has to be added here on purpose; the read of the catalogue's names would not
#: give an abbreviation.
ABBREVIATION = {"PB": "ПБ"}

#: The first-flow steps whose request or answer carries the section of the classification.
CLASSIFICATION_STEPS = (
    "classify-version",
    "classify-second-version",
    "classify-third-version",
)
CORRECTION_STEP = "classification-correction"
EMPTY_SECTION_STEP = "section-form7-without-members"

_CHOICE = re.compile(r'data-section-choice="([A-Z]{2,3})"')
_AR_PIN = re.compile(
    r'data-(?:section-choice|section|vendor-section)="AR"|"section_code":"AR"'
)


# --------------------------------------------------------------------------------------
# Reading the facts. Nothing here executes the code it reads.
# --------------------------------------------------------------------------------------


def _read(path: Path) -> str:
    """An absent input is a hard failure, never a skip: a skip would certify nothing."""
    if not path.is_file():
        pytest.fail(f"{path} is missing, so this check would prove nothing")
    return path.read_text(encoding="utf-8")


def module_constant(path: Path, name: str) -> object:
    """The literal a module assigns to ``name`` at its top level, read without importing it."""
    tree = ast.parse(_read(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    pytest.fail(f"{path} assigns no top-level constant {name}")


def journey_section() -> str:
    value = module_constant(DRIVER, "JOURNEY_SECTION")
    assert isinstance(value, str), value
    return value


def observations(recording: Path) -> list[dict]:
    document = json.loads(_read(recording))
    return json.loads(document["output_text"])["observations"]


def section_recording(code: str, root: Path = SECTION_RECORDINGS) -> Path:
    files = sorted((root / code.lower()).glob("*.json"))
    assert len(files) == 1, f"{code}: expected exactly one recording, found {[f.name for f in files]}"
    return files[0]


def canonical_recording(root: Path = CANONICAL_RECORDINGS) -> Path:
    files = sorted(root.glob("*.json"))
    assert len(files) == 1, f"expected one canonical recording, found {[f.name for f in files]}"
    return files[0]


def shape(found: list[dict]) -> list[tuple]:
    """What an acceptance pin can see of a recorded answer: category, page and quotation."""
    return sorted(
        (item["category"], tuple((e["page_number"], e["quote"]) for e in item["evidence"]))
        for item in found
    )


def write_steps(manifest: dict) -> list[dict]:
    return manifest["write"]["steps"]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(_read(MANIFEST))


# --------------------------------------------------------------------------------------
# 1. The chosen section's recorded answer is the AR baseline's.
# --------------------------------------------------------------------------------------


def recording_findings(
    chosen: list[dict], canonical: list[dict], *, findings_pin: int, evidence_pin: int
) -> list[str]:
    found: list[str] = []
    if shape(chosen) != shape(canonical):
        found.append(
            "the chosen section's recorded findings differ from the canonical AR recording's in "
            f"category, page or quotation: {shape(chosen)} against {shape(canonical)}"
        )
    if len(chosen) != findings_pin:
        found.append(f"the chosen recording publishes {len(chosen)} findings, the suite pins {findings_pin}")
    evidence = sum(len(item["evidence"]) for item in chosen)
    if evidence != evidence_pin:
        found.append(f"the chosen recording carries {evidence} pieces of evidence, the suite pins {evidence_pin}")
    return found


def test_the_journey_section_is_answered_with_the_ar_baseline_findings() -> None:
    code = journey_section()
    findings_pin = module_constant(ACCEPTANCE, "EXPECTED_FINDING_COUNT")
    evidence_pin = module_constant(ACCEPTANCE, "EXPECTED_CSV_ROWS")
    assert isinstance(findings_pin, int) and isinstance(evidence_pin, int)
    chosen_file = section_recording(code)
    document = json.loads(_read(chosen_file))
    assert document["origin"]["kind"] == "synthetic" and document["origin"]["section_code"] == code, (
        "the recording is not a synthetic answer of the journey's section"
    )
    found = recording_findings(
        observations(chosen_file),
        observations(canonical_recording()),
        findings_pin=findings_pin,
        evidence_pin=evidence_pin,
    )
    assert not found, "\n".join(found)


def test_control_a_recording_that_drops_or_rewrites_a_finding_is_detected() -> None:
    canonical = observations(canonical_recording())
    chosen = copy.deepcopy(canonical)
    assert recording_findings(chosen, canonical, findings_pin=3, evidence_pin=5) == []
    dropped = copy.deepcopy(chosen)
    dropped[0]["evidence"].pop()
    assert recording_findings(dropped, canonical, findings_pin=3, evidence_pin=5)
    fewer = copy.deepcopy(chosen)[:2]
    assert recording_findings(fewer, canonical, findings_pin=3, evidence_pin=5)
    moved = copy.deepcopy(chosen)
    moved[2]["evidence"][0]["page_number"] = 3
    assert recording_findings(moved, canonical, findings_pin=3, evidence_pin=5)
    reworded = copy.deepcopy(chosen)
    reworded[1]["evidence"][1]["quote"] += " "
    assert recording_findings(reworded, canonical, findings_pin=3, evidence_pin=5)
    recategorised = copy.deepcopy(chosen)
    recategorised[2]["category"] = "internal_contradiction"
    assert recording_findings(recategorised, canonical, findings_pin=3, evidence_pin=5)


def test_control_another_section_s_recording_is_not_the_ar_baseline_s() -> None:
    """The comparison can tell sections apart: КЖ answers with one finding, not three."""
    canonical = observations(canonical_recording())
    other = observations(section_recording("KJ"))
    assert recording_findings(other, canonical, findings_pin=3, evidence_pin=5)


# --------------------------------------------------------------------------------------
# 2. The section every classification of the main flow names.
# --------------------------------------------------------------------------------------


def classification_choice(step: dict) -> str | None:
    """The section a step's own actions choose in «Стадия и раздел», or ``None``."""
    chosen = [
        match.group(1)
        for action in step.get("actions") or ()
        for match in [_CHOICE.search(str(action.get("selector", "")))]
        if match
    ]
    return chosen[-1] if chosen else None


def expectations_status(code: str, expectations: dict) -> str | None:
    for entry in expectations["sections"]:
        if entry["code"] == code:
            return entry["status"]
    return None


def section_findings(manifest: dict, code: str, expectations: dict) -> list[str]:
    found: list[str] = []
    by_name = {step["name"]: step for step in write_steps(manifest)}
    bound = set((manifest["write"].get("ar_bound") or {}).get("steps") or ())

    for name in CLASSIFICATION_STEPS:
        step = by_name.get(name)
        if step is None:
            found.append(f"{name}: the step is gone")
            continue
        if classification_choice(step) != code:
            found.append(f"{name}: chooses {classification_choice(step)!r}, the journey's section is {code!r}")
        echoed = [
            check.get("equals")
            for check in step.get("expects_response") or ()
            if check.get("json_path") == "section_code"
        ]
        if echoed != [code]:
            found.append(f"{name}: requires the answer's section_code to be {echoed!r}, not {[code]!r}")
    for step in write_steps(manifest):
        chosen = classification_choice(step)
        if chosen is not None and step["name"] not in bound and chosen != code:
            found.append(f"{step['name']}: classifies as {chosen!r} outside write.ar_bound")

    correction = by_name.get(CORRECTION_STEP)
    if correction is None:
        found.append(f"{CORRECTION_STEP}: the step is gone")
    else:
        sent = [
            needle
            for check in correction.get("expects_request") or ()
            for needle in check.get("body_contains") or ()
        ]
        if f'"section_code":"{code}"' not in sent:
            found.append(f"{CORRECTION_STEP}: the request does not carry section_code {code}")
        echoed = [
            check.get("equals")
            for check in correction.get("expects_response") or ()
            if check.get("json_path") == "section_code"
        ]
        if echoed != [code]:
            found.append(f"{CORRECTION_STEP}: requires the answer's section_code to be {echoed!r}")

    dashboard = by_name.get("dashboard-sections-panel")
    selectors = [present.get("selector", "") for present in (dashboard or {}).get("expects_present") or ()]
    if not any(f'li[data-section="{code}"] strong' in selector for selector in selectors):
        found.append(f"dashboard-sections-panel: does not count the journey's section {code}")

    settings = by_name.get("analysis-settings-lists-the-profiles")
    status = expectations_status(code, expectations)
    if status != "reviewed":
        found.append(f"the expectations file gives {code} the status {status!r}; the settings step asserts 'reviewed'")
    selectors = [present.get("selector", "") for present in (settings or {}).get("expects_present") or ()]
    if f'tr[data-section="{code}"][data-profile="reviewed"]' not in selectors:
        found.append(f"analysis-settings-lists-the-profiles: does not assert the {code} row as reviewed")

    empty = by_name.get(EMPTY_SECTION_STEP)
    if empty is None or (empty.get("constants") or {}).get("section_code") == code:
        found.append(
            f"{EMPTY_SECTION_STEP}: must use a section no project confirms, and the journey confirms {code}"
        )
    return found


def test_every_classification_of_the_main_flow_names_the_journey_section(manifest: dict) -> None:
    expectations = json.loads(_read(EXPECTATIONS))
    found = section_findings(manifest, journey_section(), expectations)
    assert not found, "\n".join(found)


def _step(manifest: dict, name: str) -> dict:
    return next(step for step in write_steps(manifest) if step["name"] == name)


def test_control_a_classification_step_that_names_another_section_is_detected(manifest: dict) -> None:
    expectations = json.loads(_read(EXPECTATIONS))
    code = journey_section()
    assert section_findings(manifest, code, expectations) == []
    for name in CLASSIFICATION_STEPS:
        mutated = copy.deepcopy(manifest)
        for action in _step(mutated, name)["actions"]:
            action["selector"] = action["selector"].replace(f'"{code}"', '"AR"')
        assert section_findings(mutated, code, expectations), name
        echo = copy.deepcopy(manifest)
        for check in _step(echo, name)["expects_response"]:
            if check.get("json_path") == "section_code":
                check["equals"] = "AR"
        assert section_findings(echo, code, expectations), name
    correction = copy.deepcopy(manifest)
    for check in _step(correction, CORRECTION_STEP)["expects_request"][0:1]:
        check["body_contains"] = [n.replace(f'"section_code":"{code}"', '"section_code":"AR"') for n in check["body_contains"]]
    assert section_findings(correction, code, expectations)
    dashboard = copy.deepcopy(manifest)
    for present in _step(dashboard, "dashboard-sections-panel")["expects_present"]:
        present["selector"] = present["selector"].replace(f'"{code}"', '"AR"')
    assert section_findings(dashboard, code, expectations)
    unreviewed = copy.deepcopy(expectations)
    for entry in unreviewed["sections"]:
        if entry["code"] == code:
            entry["status"] = "draft"
    assert section_findings(manifest, code, unreviewed)
    shared = copy.deepcopy(manifest)
    _step(shared, EMPTY_SECTION_STEP)["constants"]["section_code"] = code
    assert section_findings(shared, code, expectations)


# --------------------------------------------------------------------------------------
# 3. What cannot move is named, and nothing else may name АР.
# --------------------------------------------------------------------------------------


def strings_of(value: object) -> Iterator[str]:
    """Every string a step says, apart from its prose (keys that start with ``$``)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, inner in value.items():
            if not str(key).startswith("$"):
                yield from strings_of(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from strings_of(inner)


def names_ar(step: dict) -> bool:
    return any(text == "AR" or _AR_PIN.search(text) for text in strings_of(step))


def ar_bound_findings(manifest: dict) -> list[str]:
    found: list[str] = []
    steps = write_steps(manifest)
    names = [step["name"] for step in steps]
    block = manifest["write"].get("ar_bound")
    if not isinstance(block, dict):
        return ["write.ar_bound is missing: nothing says which steps may name АР"]
    listed = list(block.get("steps") or ())
    needs_run = list(block.get("needs_published_run") or ())
    registry = list(block.get("registry_pins") or ())
    for label, group in (("steps", listed), ("needs_published_run", needs_run), ("registry_pins", registry)):
        for name in sorted({n for n in group if group.count(n) > 1}):
            found.append(f"ar_bound.{label} lists '{name}' twice")
        for name in group:
            if name not in names:
                found.append(f"ar_bound.{label} names '{name}', which is not a write step")
    for name in needs_run:
        if name not in listed:
            found.append(f"ar_bound.needs_published_run names '{name}', which ar_bound.steps does not list")
    exempt = set(listed) | set(registry)

    for step in steps:
        if step["name"] not in exempt and names_ar(step):
            found.append(f"{step['name']}: names АР but is not listed in write.ar_bound")

    # Where a run starts, and which document a specification or a pass is asked of, follows the
    # classification an earlier step made (a bind renames the alias, as `write.mjs` reads it).
    version_section: dict[str, str] = {}
    document_section: dict[str, str] = {}
    for step in steps:
        bind = step.get("bind") or {}
        chosen = classification_choice(step)
        if chosen is not None:
            version_section[bind.get("version_uid", "version_uid")] = chosen
            document_section[bind.get("document_uid", "document_uid")] = chosen
        calls = {call["operationId"]: call for call in step.get("expects_api") or ()}
        if "startRun" in calls:
            alias = (calls["startRun"].get("bind") or {}).get("version_uid") or bind.get(
                "version_uid", "version_uid"
            )
            section = version_section.get(alias)
            if section is None:
                found.append(f"{step['name']}: starts a run on '{alias}', which no earlier step classified")
            elif section == "AR" and step["name"] not in listed:
                found.append(f"{step['name']}: starts a run on an АР version outside write.ar_bound")
        for operation in ("startOptimisationPass", "getSpecificationPrices"):
            if operation in calls:
                alias = (calls[operation].get("bind") or {}).get("document_uid") or bind.get(
                    "document_uid", "document_uid"
                )
                section = document_section.get(alias)
                if section != "AR":
                    found.append(
                        f"{step['name']}: {operation} is asked of '{alias}', which the journey has "
                        f"classified {section!r}; the specification and the pass read АР sets only"
                    )
    return found


def test_only_the_named_steps_may_name_ar_or_run_an_ar_version(manifest: dict) -> None:
    found = ar_bound_findings(manifest)
    assert not found, "\n".join(found)


def test_the_ar_bound_block_is_the_size_it_was_measured_at(manifest: dict) -> None:
    """33 steps may name АР: the three that make the empty-pass set, the 29 of the «Оптимизация»
    span and the Form-7. A longer list is a step that moved there to stop being checked."""
    block = manifest["write"]["ar_bound"]
    assert len(block["steps"]) == 33, len(block["steps"])
    assert len(block["needs_published_run"]) == 15, len(block["needs_published_run"])
    assert block["registry_pins"] == ["analysis-settings-lists-the-profiles"]


def test_control_an_ar_pin_or_run_outside_the_named_steps_is_detected(manifest: dict) -> None:
    assert ar_bound_findings(manifest) == []

    flipped = copy.deepcopy(manifest)
    for action in _step(flipped, "classify-version")["actions"]:
        action["selector"] = action["selector"].replace('"PB"', '"AR"')
    assert any("starts a run on an АР version outside" in f for f in ar_bound_findings(flipped))
    assert any("classify-version: names АР" in f for f in ar_bound_findings(flipped))

    unlisted = copy.deepcopy(manifest)
    unlisted["write"]["ar_bound"]["steps"].remove("start-specification-run")
    unlisted["write"]["ar_bound"]["needs_published_run"].remove("start-specification-run")
    assert any(f.startswith("start-specification-run:") for f in ar_bound_findings(unlisted))

    unbound = copy.deepcopy(manifest)
    del _step(unbound, "optimisation-pass-over-a-set-without-a-table")["bind"]
    assert any("startOptimisationPass is asked of 'document_uid'" in f for f in ar_bound_findings(unbound))

    vendor = copy.deepcopy(manifest)
    _step(vendor, "norms-search").setdefault("expects_present", []).append(
        {"selector": 'tr[data-vendor-section="AR"] button'}
    )
    assert any(f.startswith("norms-search: names АР") for f in ar_bound_findings(vendor))

    body = copy.deepcopy(manifest)
    _step(body, "norms-search")["expects_request"] = [
        {"of": "searchNorms", "body_contains": ['"section_code":"AR"']}
    ]
    assert any(f.startswith("norms-search: names АР") for f in ar_bound_findings(body))

    constant = copy.deepcopy(manifest)
    _step(constant, "section-form7-without-members")["constants"]["section_code"] = "AR"
    assert any(f.startswith("section-form7-without-members: names АР") for f in ar_bound_findings(constant))

    unclassified = copy.deepcopy(manifest)
    _step(unclassified, "start-second-run")["bind"]["version_uid"] = "no_such_version_uid"
    assert any("which no earlier step classified" in f for f in ar_bound_findings(unclassified))

    ghost = copy.deepcopy(manifest)
    ghost["write"]["ar_bound"]["steps"].append("a-step-that-is-not-there")
    assert any("which is not a write step" in f for f in ar_bound_findings(ghost))

    stray = copy.deepcopy(manifest)
    stray["write"]["ar_bound"]["needs_published_run"].append("norms-search")
    assert any("which ar_bound.steps does not list" in f for f in ar_bound_findings(stray))

    missing = copy.deepcopy(manifest)
    del missing["write"]["ar_bound"]
    assert ar_bound_findings(missing) == ["write.ar_bound is missing: nothing says which steps may name АР"]


# --------------------------------------------------------------------------------------
# 4. The documents that describe the journey say the same section.
# --------------------------------------------------------------------------------------


def document_findings(code: str, readme: str, protocol: str) -> list[str]:
    abbreviation = ABBREVIATION.get(code)
    if abbreviation is None:
        return [f"ABBREVIATION in this file has no entry for {code}: add the Russian abbreviation"]
    found: list[str] = []
    row = next((line for line in readme.splitlines() if line.startswith("| `classify-version`")), "")
    if f"**{abbreviation}**" not in row or "**АР**" in row:
        found.append(f"the README's classify-version row does not choose **{abbreviation}** (or still chooses **АР**)")
    if f'section_code: "{code}"' not in row:
        found.append(f"the README's classify-version row does not echo section_code \"{code}\"")
    if f"section {abbreviation}" not in protocol.split("### A04", 1)[0].split("### A03", 1)[-1]:
        found.append(f"the manual protocol does not confirm section {abbreviation} between A03 and A04")
    return found


def test_the_readme_and_the_manual_protocol_name_the_journey_section() -> None:
    found = document_findings(journey_section(), _read(README), _read(MANUAL_PROTOCOL))
    assert not found, "\n".join(found)


def test_control_a_document_that_names_another_section_is_detected() -> None:
    readme, protocol = _read(README), _read(MANUAL_PROTOCOL)
    code = journey_section()
    assert document_findings(code, readme, protocol) == []
    assert document_findings(code, readme.replace("**ПБ**", "**АР**"), protocol)
    assert document_findings(code, readme, protocol.replace("section ПБ", "section АР"))
    assert document_findings("KJ", readme, protocol)
