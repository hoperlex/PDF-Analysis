from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "docs" / "templates" / "TASK_TEMPLATE.md"
GUIDE = ROOT / "docs" / "program" / "WAVE_EXECUTION_GUIDE.md"
OPERATING = ROOT / "docs" / "program" / "dispatch" / "OPERATING_CONSTRAINTS.md"
ADDENDUM = ROOT / "docs" / "program" / "W46-HISTORICAL-ADDENDUM.md"
TASKS = ROOT / "docs" / "program" / "tasks"
FROZEN_BASE = "fad3c28748ef52bc9b5f711191ff0130483e0055"
GOVERNANCE_ACTIVATION_BASE = "14caf886e78883ed771d81fbf463c98af727c938"
W46_REPORTS = (
    "docs/program/W46-DASH.md",
    "docs/program/W46-WIRE.md",
    "docs/program/W46-CLIENT.md",
    "docs/program/W46-GUARD.md",
    "docs/program/W46-SEAL.md",
    "docs/program/W46-SPEND.md",
)


def _section(markdown: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)", markdown
    )
    return None if match is None else match.group("body")


def _field(section: str, name: str) -> str | None:
    match = re.search(rf"(?m)^- {re.escape(name)}:\s*(.+?)\s*$", section)
    return None if match is None else match.group(1)


def governance_findings(markdown: str) -> set[str]:
    """Return stable rule ids for a newly dispatched task document."""

    findings: set[str] = set()
    enumerator = _section(markdown, "Enumerator ownership")
    if enumerator is None:
        findings.add("ENUMERATOR_SECTION_REQUIRED")
    else:
        changed = _field(enumerator, "enumerated_set_changed")
        if changed not in {"yes", "no"}:
            findings.add("ENUMERATOR_CHANGE_DECLARATION_REQUIRED")
        elif changed == "yes":
            path = _field(enumerator, "enumerator_path")
            owner = _field(enumerator, "enumerator_owner")
            query = _field(enumerator, "totality_query")
            if not path or path == "not_applicable":
                findings.add("ENUMERATOR_PATH_REQUIRED")
            if not owner or owner == "not_applicable":
                findings.add("ENUMERATOR_OWNER_REQUIRED")
            if not query or query == "not_applicable":
                findings.add("ENUMERATOR_TOTALITY_REQUIRED")

    premises = _section(markdown, "Captured premise evidence")
    if premises is None:
        findings.add("PREMISE_SECTION_REQUIRED")
    elif _field(premises, "premise") is None:
        findings.add("PREMISE_DECLARATION_REQUIRED")
    elif _field(premises, "premise") != "none":
        if re.search(r"(?m)^- captured_at: \d{4}-\d{2}-\d{2}\s*$", premises) is None:
            findings.add("PREMISE_DATE_REQUIRED")
        if re.search(r"(?m)^- command: `[^`]+`\s*$", premises) is None:
            findings.add("PREMISE_COMMAND_REQUIRED")
        output = re.search(
            r"(?ms)^- captured_output:\s*$\n\s*```text\s*$\n(?P<output>.*?)\n\s*```\s*$",
            premises,
        )
        if output is None:
            findings.add("PREMISE_OUTPUT_REQUIRED")
        elif len(output.group("output").strip()) < 2:
            findings.add("PREMISE_OUTPUT_SUBSTANTIVE_REQUIRED")

    history = _section(markdown, "Historical evidence")
    if history is None:
        findings.add("HISTORY_SECTION_REQUIRED")
    else:
        mode = _field(history, "correction_mode")
        if mode not in {"none", "addendum"}:
            findings.add("HISTORICAL_ADDENDUM_REQUIRED")
        if mode == "addendum":
            source = _field(history, "source_record")
            addendum = _field(history, "addendum_path")
            if not source or source == "not_applicable" or not addendum or addendum == "not_applicable":
                findings.add("HISTORICAL_ADDENDUM_PATH_REQUIRED")

    publication = _section(markdown, "Publication authority")
    if publication is None:
        findings.add("PUBLICATION_SECTION_REQUIRED")
    else:
        target = _field(publication, "development_target")
        authority = _field(publication, "origin_main_authority") or ""
        if target == "origin/main":
            if not authority.startswith("separate direct owner instruction "):
                findings.add("MAIN_DIRECT_AUTHORITY_REQUIRED")
            elif re.fullmatch(r"separate direct owner instruction [0-9a-f]{40}", authority) is None:
                findings.add("MAIN_DIRECT_AUTHORITY_REFERENCE_REQUIRED")
        elif re.fullmatch(r"none(?:; .+)?", authority) is None:
            findings.add("MAIN_DIRECT_AUTHORITY_TARGET_MISMATCH")
        if target not in {"none", "origin/dev", "origin/main"}:
            findings.add("PUBLICATION_TARGET_INVALID")
    return findings


def _activation_task_paths() -> frozenset[str]:
    result = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            GOVERNANCE_ACTIVATION_BASE,
            "docs/program/tasks",
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return frozenset(result.stdout.splitlines())


def governed_task_findings(
    root: Path = ROOT, *, baseline_paths: frozenset[str] | None = None
) -> dict[str, set[str]]:
    """Validate every task absent from the exact governance-activation tree."""

    baseline = _activation_task_paths() if baseline_paths is None else baseline_paths
    tasks = root / "docs" / "program" / "tasks"
    findings: dict[str, set[str]] = {}
    for task in sorted(tasks.glob("*.md")):
        relative = task.relative_to(root).as_posix()
        if relative in baseline:
            continue
        task_findings = governance_findings(task.read_text(encoding="utf-8"))
        if task_findings:
            findings[relative] = task_findings
    return findings


VALID_TASK = """# Task W49-QA-01 — example

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: tests/e2e/manifest.json
- enumerator_owner: W49-INT-01
- totality_query: `find web/src/app -name page.tsx -print`

## Captured premise evidence
- premise: route count is 16

### P-01 — route count
- captured_at: 2026-10-02
- command: `find web/src/app -name page.tsx -print`
- captured_output:
  ```text
  web/src/app/page.tsx
  ```
- interpretation: one complete untruncated example output

## Historical evidence
- correction_mode: addendum
- source_record: docs/program/W46-CLIENT.md
- addendum_path: docs/program/W46-HISTORICAL-ADDENDUM.md

## Publication authority
- development_target: origin/dev
- origin_main_authority: none
"""


def test_the_task_template_carries_all_four_governance_sections() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert _section(text, "Enumerator ownership") is not None
    assert _section(text, "Captured premise evidence") is not None
    assert _section(text, "Historical evidence") is not None
    assert _section(text, "Publication authority") is not None
    assert "enumerator_owner" in text
    assert "captured_at: YYYY-MM-DD" in text
    assert "correction_mode: addendum" in text
    assert "separate direct owner instruction" in text


def test_a_complete_new_task_satisfies_the_executable_rules() -> None:
    assert governance_findings(VALID_TASK) == set()


def test_every_task_added_after_governance_activation_satisfies_the_rules() -> None:
    assert governed_task_findings() == {}


def test_the_activation_inventory_is_the_captured_85_task_baseline() -> None:
    baseline = _activation_task_paths()
    assert len(baseline) == 85
    assert "docs/program/tasks/W48-GOV.md" in baseline
    assert "docs/program/tasks/W48-JUDGE-X.md" not in baseline


def test_a_new_real_task_file_cannot_escape_the_enumerator(tmp_path: Path) -> None:
    tasks = tmp_path / "docs" / "program" / "tasks"
    tasks.mkdir(parents=True)
    legacy = tasks / "W48-LEGACY.md"
    broken = tasks / "W49-BROKEN.md"
    valid = tasks / "W49-VALID.md"
    legacy.write_text("# historical task without the new sections\n", encoding="utf-8")
    broken.write_text("# new task without the new sections\n", encoding="utf-8")
    valid.write_text(VALID_TASK, encoding="utf-8")

    findings = governed_task_findings(
        tmp_path,
        baseline_paths=frozenset({"docs/program/tasks/W48-LEGACY.md"}),
    )
    assert findings == {
        "docs/program/tasks/W49-BROKEN.md": {
            "ENUMERATOR_SECTION_REQUIRED",
            "PREMISE_SECTION_REQUIRED",
            "HISTORY_SECTION_REQUIRED",
            "PUBLICATION_SECTION_REQUIRED",
        }
    }


@pytest.mark.parametrize(
    ("broken", "expected"),
    (
        (
            VALID_TASK.replace("- enumerator_owner: W49-INT-01", "- enumerator_owner: not_applicable"),
            "ENUMERATOR_OWNER_REQUIRED",
        ),
        (
            VALID_TASK.replace("- captured_at: 2026-10-02\n", "").replace(
                "- captured_output:\n  ```text\n  web/src/app/page.tsx\n  ```\n", ""
            ),
            "PREMISE_OUTPUT_REQUIRED",
        ),
        (
            VALID_TASK.replace("- correction_mode: addendum", "- correction_mode: rewrite"),
            "HISTORICAL_ADDENDUM_REQUIRED",
        ),
        (
            VALID_TASK.replace("- development_target: origin/dev", "- development_target: origin/main"),
            "MAIN_DIRECT_AUTHORITY_REQUIRED",
        ),
    ),
)
def test_each_invalid_example_fails_for_its_intended_rule(broken: str, expected: str) -> None:
    assert expected in governance_findings(broken)


def test_empty_governance_sections_are_not_valid_declarations() -> None:
    broken = re.sub(
        r"(?ms)^## (Enumerator ownership|Captured premise evidence|Historical evidence|Publication authority)\n.*?(?=^## |\Z)",
        lambda match: f"## {match.group(1)}\n\n",
        VALID_TASK,
    )
    assert governance_findings(broken) >= {
        "ENUMERATOR_CHANGE_DECLARATION_REQUIRED",
        "PREMISE_DECLARATION_REQUIRED",
        "HISTORICAL_ADDENDUM_REQUIRED",
        "PUBLICATION_TARGET_INVALID",
    }


def test_enumerator_flag_captured_output_and_main_authority_are_validated() -> None:
    unread_enumerator = VALID_TASK.replace(
        "- enumerated_set_changed: yes", "- enumerated_set_changed: perhaps"
    )
    assert "ENUMERATOR_CHANGE_DECLARATION_REQUIRED" in governance_findings(unread_enumerator)

    one_character_output = VALID_TASK.replace("web/src/app/page.tsx", "x")
    assert "PREMISE_OUTPUT_SUBSTANTIVE_REQUIRED" in governance_findings(one_character_output)

    unbound_main = VALID_TASK.replace(
        "- development_target: origin/dev\n- origin_main_authority: none",
        "- development_target: origin/main\n"
        "- origin_main_authority: separate direct owner instruction x",
    )
    assert "MAIN_DIRECT_AUTHORITY_REFERENCE_REQUIRED" in governance_findings(unbound_main)


def test_main_authority_requires_a_main_target_and_exact_candidate_sha() -> None:
    base = VALID_TASK.replace(
        "- origin_main_authority: none",
        "- origin_main_authority: separate direct owner instruction " + "a" * 40,
    )
    assert "MAIN_DIRECT_AUTHORITY_TARGET_MISMATCH" in governance_findings(base)

    main = base.replace("- development_target: origin/dev", "- development_target: origin/main")
    assert governance_findings(main) == set()
    for reference in ("xxxxxxx", "a" * 39, "a" * 41, "a" * 40 + " later"):
        broken = main.replace("a" * 40, reference)
        assert "MAIN_DIRECT_AUTHORITY_REFERENCE_REQUIRED" in governance_findings(broken)


def test_the_operational_docs_state_the_same_rules_the_guard_executes() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    operating = OPERATING.read_text(encoding="utf-8")
    guide_flat = " ".join(guide.split())
    for phrase in (
        "enumerator ownership",
        "captured premise evidence",
        "new addendum that cites the immutable source",
        "origin/dev",
        "separate direct owner instruction",
    ):
        assert phrase in guide_flat
    for phrase in (
        "A maintained set has an enumerator",
        "A premise needs captured output",
        "history receives an addendum",
        "origin/dev` is a candidate",
        "origin/main` is a deployment action",
    ):
        assert phrase in operating


def test_the_original_w46_reports_are_byte_identical_to_the_stage_b_base() -> None:
    for relative in W46_REPORTS:
        frozen = subprocess.run(
            ["git", "show", f"{FROZEN_BASE}:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert (ROOT / relative).read_bytes() == frozen, relative


def test_the_addendum_carries_the_exact_corrections_without_claiming_a_rewrite() -> None:
    text = ADDENDUM.read_text(encoding="utf-8")
    for exact in (
        "AI: expected 4 to be +0",
        "f50e6565cbba324d8e832f1973afefc65db43458",
        "069f656b363c4a91b0f8f0df66dbc6359f9e18f6",
        "d56ae057fc895acf0ab4f7cb48f78bf9065fabbb",
        "08f0e7f066b0643098909fa850680364925bbafa",
        "1196ca7f3e14cc4b944fa8d193d8cb1c8fc02f3f",
        "GATE OK: battery, foundation, frontend and whitespace all pass",
    ):
        assert exact in text
    assert "does not invent" in text
    assert "byte-identical" in text


def test_d52s_later_repair_is_present_and_bound_to_a_notice() -> None:
    notice = (ROOT / "web" / "NOTICE").read_text(encoding="utf-8")
    icon = (ROOT / "web" / "src" / "shared" / "ui" / "icon.tsx").read_text(encoding="utf-8")
    assert "Copyright (c) 2013-2023 Cole Bemis" in notice
    assert "The MIT License (MIT)" in notice
    assert "https://github.com/feathericons/feather" in notice
    assert "web/NOTICE" in icon
    assert (ROOT / "web" / "tests" / "unit" / "icon-convention.test.ts").is_file()
    assert (ROOT / "web" / "tests" / "unit" / "icon-provenance.test.ts").is_file()
