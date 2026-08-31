from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts/validate_bootstrap.py"


def _write_json(root: Path, relative_path: str, value: object) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_markdown(root: Path, relative_path: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {path.stem}\n", encoding="utf-8")


def _make_validator_checkout(root: Path) -> Path:
    copied_validator = root / "scripts/validate_bootstrap.py"
    copied_validator.parent.mkdir(parents=True)
    shutil.copy2(VALIDATOR_PATH, copied_validator)
    return copied_validator


def _make_valid_bootstrap(root: Path) -> None:
    required_markdown = [
        "README.md",
        "AGENTS.md",
        "docs/architecture/ARCHITECTURE_BIBLE.md",
        "docs/architecture/ADR_INDEX.md",
        "docs/program/ROADMAP.md",
        "docs/program/WAVE_EXECUTION_GUIDE.md",
        "docs/program/CHECKPOINT_REGISTRY.md",
        "docs/program/VERSIONING_AND_FREEZE_POLICY.md",
        "docs/stages/S00_architecture_and_behavior_freeze.md",
        "docs/stages/S10_release_acceptance.md",
        "docs/manual-tests/CP-00_architecture.md",
        "docs/manual-tests/CP-10_release.md",
    ]
    for relative_path in required_markdown:
        _write_markdown(root, relative_path)
    for index in range(1, 10):
        _write_markdown(root, f"docs/stages/S{index:02d}_stage.md")
        _write_markdown(root, f"docs/manual-tests/CP-{index:02d}_runbook.md")
    for index in range(1, 19):
        _write_markdown(root, f"docs/architecture/adr/ADR-{index:04d}.md")

    _write_json(
        root,
        "contracts/domain/v1/identifiers.json",
        {"identifiers": {"audit_run": "run", "job": "job"}},
    )
    _write_json(
        root,
        "contracts/domain/v1/state-machines.json",
        {
            "machines": {
                "audit_run": {
                    "initial": "created",
                    "transitions": {"created": ["completed"]},
                    "terminal": ["completed"],
                }
            }
        },
    )

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
    }
    pairs = [
        (
            "contracts/analysis/v1/job-package.schema.json",
            "contracts/analysis/v1/examples/job-package.example.json",
        ),
        (
            "contracts/analysis/v1/stage-result.schema.json",
            "contracts/analysis/v1/examples/stage-result.example.json",
        ),
        (
            "contracts/analysis/v1/result-package.schema.json",
            "contracts/analysis/v1/examples/result-package.example.json",
        ),
        (
            "contracts/events/v1/event-envelope.schema.json",
            "contracts/events/v1/examples/event-envelope.example.json",
        ),
    ]
    for schema_path, example_path in pairs:
        _write_json(root, schema_path, schema)
        _write_json(root, example_path, {})


def _run_validator(validator: Path, shadow_module_source: str) -> subprocess.CompletedProcess[str]:
    shadow_directory = validator.parents[1] / "shadow-modules"
    shadow_directory.mkdir()
    (shadow_directory / "jsonschema.py").write_text(
        shadow_module_source,
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(shadow_directory)
    return subprocess.run(
        [sys.executable, str(validator)],
        cwd=validator.parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class ValidateBootstrapTests(unittest.TestCase):
    def test_missing_jsonschema_fails_closed_without_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            result = _run_validator(
                validator,
                "raise ImportError('simulated missing dependency')\n",
            )

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("jsonschema", output)
        self.assertIn("Action:", output)
        self.assertIsNone(re.search(r"(?m)^PASS$", output))

    def test_unexpected_jsonschema_import_error_is_sanitized_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            result = _run_validator(
                validator,
                "raise RuntimeError('secret-like import detail')\n",
            )

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RuntimeError", output)
        self.assertNotIn("secret-like import detail", output)
        self.assertIsNone(re.search(r"(?m)^PASS$", output))

    def test_imported_but_unusable_validator_fails_closed(self) -> None:
        unusable_modules = {
            "none validator": "Draft202012Validator = None\n",
            "missing check_schema": "class Draft202012Validator:\n    pass\n",
        }
        for case, module_source in unusable_modules.items():
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    validator = _make_validator_checkout(root)
                    result = _run_validator(validator, module_source)

                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("jsonschema", output)
                self.assertIn("unusable (TypeError)", output)
                self.assertIn("Action:", output)
                self.assertIsNone(re.search(r"(?m)^PASS$", output))

    def test_available_jsonschema_runs_full_control_path(self) -> None:
        jsonschema_stub = """
class Draft202012Validator:
    def __init__(self, schema):
        if schema.get('$schema') != 'https://json-schema.org/draft/2020-12/schema':
            raise AssertionError('unexpected schema')
        self.schema = schema

    @classmethod
    def check_schema(cls, schema):
        if schema.get('type') != 'object':
            raise AssertionError('schema check was not given the fixture schema')

    def validate(self, example):
        if example != {}:
            raise AssertionError('example validation was not given the fixture example')
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            result = _run_validator(validator, jsonschema_stub)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIsNotNone(re.search(r"(?m)^PASS$", output))
        self.assertIn("json_files=10", output)
        self.assertIn("stages=11", output)
        self.assertIn("manual_runbooks=11", output)
        self.assertIn("adrs=18", output)


if __name__ == "__main__":
    unittest.main()
