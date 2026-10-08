"""Small, history-free checks of the grant inventory and its refusal cases."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures/pin_sweep/w49_before_seal.json"
SPEC = importlib.util.spec_from_file_location("pin_sweep", ROOT / "tools/plan/pin_sweep.py")
assert SPEC and SPEC.loader
pin_sweep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pin_sweep)


def _snapshot(tmp_path: Path) -> tuple[Path, dict]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for rel, content in data["source_file_excerpts"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    registry = tmp_path / pin_sweep.REGISTRY
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(data["registry_source"], encoding="utf-8")
    return tmp_path, data


def test_w49_before_seal_has_no_pin_caused_omission(tmp_path: Path) -> None:
    root, fixture = _snapshot(tmp_path)
    for label, events in (
        ("reseal-surface+error-code", ["reseal-surface", "error-code"]),
        ("migration+table", ["migration", "table"]),
    ):
        found = pin_sweep.collect(root, events)
        expected = set(fixture["changed_pin_subset"][label])
        assert expected <= found.keys(), sorted(expected - found.keys())
    changed = set().union(*map(set, fixture["changed_pin_subset"].values()))
    excluded = fixture["excluded_changed_paths"]
    assert changed.isdisjoint(excluded)
    assert all(reason.strip() for reason in excluded.values())
    assert len(changed | excluded.keys()) == 145


def test_identity_judge_holes_are_named(tmp_path: Path) -> None:
    root, fixture = _snapshot(tmp_path)
    found = pin_sweep.collect(root, ["route"])
    assert set(fixture["identity_judge_holes"]) <= found.keys()


def test_new_symbolic_and_live_prose_pins_are_discovered(tmp_path: Path) -> None:
    root, _ = _snapshot(tmp_path)
    symbolic = root / "tests/contract/api_v1/test_future_surface.py"
    symbolic.parent.mkdir(parents=True, exist_ok=True)
    symbolic.write_text("assert len(router.routes) == 31\n", encoding="utf-8")
    prose = root / "src/auditmanager/api/new_note.py"
    prose.parent.mkdir(parents=True, exist_ok=True)
    prose.write_text('"The API surface has thirty-one operations."\n', encoding="utf-8")
    found = pin_sweep.collect(root, ["reseal-surface"])
    assert "tests/contract/api_v1/test_future_surface.py" in found
    assert "src/auditmanager/api/new_note.py" in found


def test_every_missing_grant_is_reported_and_an_umbrella_grant_covers_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, _ = _snapshot(tmp_path)
    inventory = pin_sweep.collect(root, ["route"])
    task = tmp_path / "task.md"
    task.write_text("# Task\n\n## Allowed paths\n\n- `tests/e2e/**`\n\n## Non-goals\n", encoding="utf-8")
    assert pin_sweep.main(["route", "--root", str(root), "--check", str(task)]) == 1
    output = capsys.readouterr().out
    missing = {line.split("\t", 1)[0].removeprefix("MISSING ") for line in output.splitlines() if line.startswith("MISSING ")}
    assert missing == {path for path in inventory if not pin_sweep.granted(path, ["tests/e2e/**"])}
    assert "tests/e2e/pc01/journey/manifest.json" not in missing
    all_paths = "\n".join(f"- `{path}`" for path in inventory)
    task.write_text(f"## Allowed paths\n\n{all_paths}\n\n## Non-goals\n", encoding="utf-8")
    assert pin_sweep.main(["route", "--root", str(root), "--check", str(task)]) == 0


def test_bad_inputs_fail_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, _ = _snapshot(tmp_path)
    with pytest.raises(pin_sweep.SweepError, match="unknown"):
        pin_sweep.collect(root, ["unrecognised"])
    registry = root / pin_sweep.REGISTRY
    registry.write_text("# no block\n", encoding="utf-8")
    with pytest.raises(pin_sweep.SweepError, match="exactly one JSON block"):
        pin_sweep.collect(root, ["migration"])
    registry.unlink()
    with pytest.raises(pin_sweep.SweepError, match="missing registry"):
        pin_sweep.collect(root, ["table"])
    assert pin_sweep.main(["migration", "--root", str(root)]) == 2
    assert "missing registry" in capsys.readouterr().err
    with pytest.raises(pin_sweep.SweepError, match="invalid repository path"):
        pin_sweep.valid_path("../escape")


def test_present_facts_file_must_follow_the_planned_schema(tmp_path: Path) -> None:
    root, _ = _snapshot(tmp_path)
    facts = root / pin_sweep.FACTS
    facts.parent.mkdir(parents=True, exist_ok=True)
    facts.write_text('{"facts_version": 1, "surface": {}}', encoding="utf-8")
    with pytest.raises(pin_sweep.SweepError, match="missing expected fact: surface.path_count"):
        pin_sweep.collect(root, ["route"])
    facts.write_text(json.dumps({
        "facts_version": 1,
        "surface": {"path_count": 1, "operations": [], "schema_names": []},
        "error_catalog": {"api_codes": 1, "stored_vocabulary": 1},
        "migration_head": "0000_example",
        "contract_version": "0.0.0-example",
    }), encoding="utf-8")
    assert pin_sweep.FACTS in pin_sweep.collect(root, ["contract-version"])


def test_grant_reader_requires_a_real_allowed_section(tmp_path: Path) -> None:
    task = tmp_path / "task.md"
    task.write_text("## Forbidden hotspots\n- `tests/**`\n", encoding="utf-8")
    with pytest.raises(pin_sweep.SweepError, match="Allowed paths"):
        pin_sweep.grants_from_task(task)
    task.write_text("## Allowed paths\n- `tests/**`\n\n## Forbidden hotspots\n- `secret/**`\n", encoding="utf-8")
    assert pin_sweep.grants_from_task(task) == ["tests/**"]
    task.write_text("## Allowed paths\n- `tests/integration/{api,db}/**`\n", encoding="utf-8")
    assert pin_sweep.grants_from_task(task) == ["tests/integration/api/**", "tests/integration/db/**"]
