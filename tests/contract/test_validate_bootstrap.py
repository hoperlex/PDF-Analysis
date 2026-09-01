from __future__ import annotations

from importlib.metadata import version
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
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def _write_json(root: Path, relative_path: str, value: object) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_markdown(root: Path, relative_path: str, content: str | None = None) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or f"# {path.stem}\n", encoding="utf-8")


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def _make_validator_checkout(root: Path) -> Path:
    copied_validator = root / "scripts/validate_bootstrap.py"
    copied_validator.parent.mkdir(parents=True)
    shutil.copy2(VALIDATOR_PATH, copied_validator)
    return copied_validator


def _adr_filename(number: int, suffix: str = "test-decision") -> str:
    return f"ADR-{number:04d}-{suffix}.md"


def _write_adr_index(root: Path, filenames: list[str]) -> None:
    rows = [
        "# ADR index",
        "",
        "| ADR | Status | Decision |",
        "|---|---|---|",
    ]
    for filename in filenames:
        rows.append(f"| [{Path(filename).stem}](adr/{filename}) | proposed | Test |")
    _write_markdown(root, "docs/architecture/ADR_INDEX.md", "\n".join(rows) + "\n")


def _valid_error_catalog() -> dict[str, object]:
    return {
        "contract": "auditmanager.domain.errors",
        "version": "1.0.0-draft.0",
        "envelope": {
            "required": ["error_code", "message", "correlation_id"],
            "optional": ["details", "retryable"],
        },
        "codes": {
            "validation_failed": {"http": 422, "retryable": False},
            "dependency_unavailable": {"http": 503, "retryable": True},
        },
    }


def _make_valid_bootstrap(root: Path) -> None:
    init = _git(root, "init", "-q")
    if init.returncode != 0:
        raise AssertionError(init.stderr)

    (root / ".gitignore").write_text(
        ".venv/\nnode_modules/\n.local/\n__pycache__/\nfixtures/private/\nshadow-modules/\n",
        encoding="utf-8",
    )
    required_markdown = [
        "README.md",
        "AGENTS.md",
        "docs/architecture/ARCHITECTURE_BIBLE.md",
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

    adr_filenames = [_adr_filename(index) for index in range(1, 19)]
    for filename in adr_filenames:
        _write_markdown(root, f"docs/architecture/adr/{filename}")
    _write_adr_index(root, adr_filenames)

    _write_json(
        root,
        "contracts/domain/v1/identifiers.json",
        {
            "contract": "auditmanager.domain.identifiers",
            "version": "1.0.0-draft.0",
            "identifiers": {"audit_run": "run", "job": "job"},
        },
    )
    _write_json(
        root,
        "contracts/domain/v1/state-machines.json",
        {
            "contract": "auditmanager.domain.state-machines",
            "version": "1.0.0-draft.0",
            "machines": {
                "audit_run": {
                    "initial": "created",
                    "transitions": {"created": ["completed"]},
                    "terminal": ["completed"],
                }
            },
        },
    )
    _write_json(root, "contracts/domain/v1/error-codes.json", _valid_error_catalog())

    schema = {"$schema": SCHEMA_DIALECT, "type": "object"}
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


def _run_validator(
    validator: Path,
    shadow_module_source: str | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if shadow_module_source is None:
        environment.pop("PYTHONPATH", None)
    else:
        shadow_directory = validator.parents[1] / "shadow-modules"
        shadow_directory.mkdir(exist_ok=True)
        (shadow_directory / "jsonschema.py").write_text(
            shadow_module_source,
            encoding="utf-8",
        )
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
    def assert_validation_failure(
        self,
        result: subprocess.CompletedProcess[str],
        *expected_fragments: str,
    ) -> str:
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertNotIn("Traceback", output)
        self.assertIsNone(re.search(r"(?m)^PASS$", output))
        for fragment in expected_fragments:
            self.assertIn(fragment, output)
        return output

    def test_missing_jsonschema_fails_closed_without_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            validator = _make_validator_checkout(Path(temporary_directory))
            result = _run_validator(
                validator,
                "raise ImportError('simulated missing dependency')\n",
            )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 2)
        self.assertIn("jsonschema", output)
        self.assertIn("Action:", output)
        self.assertNotIn("Traceback", output)
        self.assertIsNone(re.search(r"(?m)^PASS$", output))

    def test_unexpected_jsonschema_import_error_is_sanitized_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            validator = _make_validator_checkout(Path(temporary_directory))
            result = _run_validator(
                validator,
                "raise RuntimeError('secret-like import detail')\n",
            )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 2)
        self.assertIn("RuntimeError", output)
        self.assertNotIn("secret-like import detail", output)
        self.assertNotIn("Traceback", output)
        self.assertIsNone(re.search(r"(?m)^PASS$", output))

    def test_imported_but_unusable_validator_fails_closed(self) -> None:
        unusable_modules = {
            "none validator": "Draft202012Validator = None\n",
            "missing check_schema": "class Draft202012Validator:\n    pass\n",
        }
        for case, module_source in unusable_modules.items():
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    validator = _make_validator_checkout(Path(temporary_directory))
                    result = _run_validator(validator, module_source)

                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 2)
                self.assertIn("jsonschema", output)
                self.assertIn("unusable (TypeError)", output)
                self.assertIn("Action:", output)
                self.assertNotIn("Traceback", output)
                self.assertIsNone(re.search(r"(?m)^PASS$", output))

    def test_real_jsonschema_runs_full_control_path(self) -> None:
        self.assertEqual(version("jsonschema"), "4.26.0")
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            result = _run_validator(validator)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIsNotNone(re.search(r"(?m)^PASS$", output))
        self.assertIn("json_files=11", output)
        self.assertIn("stages=11", output)
        self.assertIn("manual_runbooks=11", output)
        self.assertIn("adrs=18", output)

    def test_git_discovery_includes_tracked_and_untracked_but_excludes_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            tracked = _git(root, "add", "README.md")
            self.assertEqual(tracked.returncode, 0, tracked.stderr)
            _write_json(root, "contracts/untracked.json", {"kind": "untracked"})
            ignored_json = root / ".venv/lib/private.json"
            ignored_json.parent.mkdir(parents=True)
            ignored_json.write_text("{not-json", encoding="utf-8")
            _write_markdown(
                root,
                "fixtures/private/customer.md",
                "[private broken link](missing.md)\n",
            )
            result = _run_validator(validator)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("json_files=12", output)
        self.assertNotIn("private.json", output)
        self.assertNotIn("customer.md", output)
        self.assertIsNotNone(re.search(r"(?m)^PASS$", output))

    def test_force_tracked_private_dependency_and_venv_paths_remain_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            denied_files = (
                "node_modules/package/malformed.json",
                "node_modules/package/broken.md",
                ".venv/lib/malformed.json",
                ".venv/lib/broken.md",
                "fixtures/private/malformed.json",
                "fixtures/private/broken.md",
                "vendor/nested/node_modules/package/malformed.json",
                "vendor/nested/.venv/lib/broken.md",
            )
            for relative in denied_files:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix == ".json":
                    path.write_text("{not-json", encoding="utf-8")
                else:
                    path.write_text("[broken](missing.md)\n", encoding="utf-8")
            force_add = _git(root, "add", "-f", *denied_files)
            self.assertEqual(force_add.returncode, 0, force_add.stderr)
            result = _run_validator(validator)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("json_files=11", output)
        for relative in denied_files:
            self.assertNotIn(relative, output)
        self.assertIsNotNone(re.search(r"(?m)^PASS$", output))

    def test_force_tracked_nested_fixtures_private_sequence_remains_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            denied_json = "vendor/deep/fixtures/private/malformed.json"
            denied_markdown = "vendor/deep/fixtures/private/broken.md"
            json_path = root / denied_json
            markdown_path = root / denied_markdown
            json_path.parent.mkdir(parents=True)
            json_path.write_text("{not-json", encoding="utf-8")
            markdown_path.write_text("[broken](missing.md)\n", encoding="utf-8")
            force_add = _git(root, "add", "-f", denied_json, denied_markdown)
            self.assertEqual(force_add.returncode, 0, force_add.stderr)
            result = _run_validator(validator)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("json_files=11", output)
        self.assertNotIn(denied_json, output)
        self.assertNotIn(denied_markdown, output)
        self.assertIsNotNone(re.search(r"(?m)^PASS$", output))

    def test_git_discovery_failure_is_actionable_without_filesystem_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            validator = _make_validator_checkout(Path(temporary_directory))
            result = _run_validator(validator)

        self.assert_validation_failure(result, "Git discovery failed", "valid Git checkout")

    def test_non_string_schema_marker_is_accumulated_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_json(
                root,
                "contracts/non-string.schema.json",
                {"$schema": 42, "type": "object"},
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Malformed $schema",
            "contracts/non-string.schema.json",
            "json_files=12",
        )

    def test_missing_contract_input_is_accumulated_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            missing = root / "contracts/analysis/v1/examples/job-package.example.json"
            missing.unlink()
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Missing repository-owned contract example",
            "job-package.example.json",
            "stages=11",
        )

    def test_malformed_inputs_and_wrong_shape_accumulate_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            (root / "contracts/invalid-utf8.json").write_bytes(b"\xff\xfe")
            (root / "contracts/invalid-json.json").write_text("{broken", encoding="utf-8")
            _write_json(root, "contracts/domain/v1/identifiers.json", [])
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Invalid UTF-8 in JSON artifact: contracts/invalid-utf8.json",
            "Invalid JSON in JSON artifact: contracts/invalid-json.json",
            "Wrong top-level shape for domain identifier catalog",
        )

    def test_broken_markdown_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_markdown(root, "docs/broken.md", "[missing](not-here.md)\n")
            result = _run_validator(validator)

        self.assert_validation_failure(result, "Broken md link: docs/broken.md -> not-here.md")

    def test_empty_markdown_targets_are_artifact_specific_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_markdown(
                root,
                "docs/empty-targets.md",
                "[empty]( )\n[stripped](<>)\n",
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Malformed md link target: docs/empty-targets.md; target is empty",
            "target is empty after angle-bracket normalization",
        )

    def test_zero_length_markdown_target_is_artifact_specific_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_markdown(root, "docs/zero-target.md", "[empty]()\n")
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Malformed md link target: docs/zero-target.md; target is empty",
        )

    def test_state_machine_closure_and_terminal_edges_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_json(
                root,
                "contracts/domain/v1/state-machines.json",
                {
                    "contract": "auditmanager.domain.state-machines",
                    "version": "1.0.0-draft.0",
                    "machines": {
                        "audit_run": {
                            "initial": "unknown_initial",
                            "transitions": {
                                "created": ["missing"],
                                "completed": ["created"],
                            },
                            "terminal": ["completed"],
                        }
                    },
                },
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "State machine audit_run: initial state missing from state set",
            "transition created->missing points to unknown state",
            "terminal state completed has outgoing transition",
        )

    def test_duplicate_identifier_prefix_names_prefix_and_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_json(
                root,
                "contracts/domain/v1/identifiers.json",
                {
                    "contract": "auditmanager.domain.identifiers",
                    "version": "1.0.0-draft.0",
                    "identifiers": {"audit_run": "dup", "job": "dup"},
                },
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Duplicate domain identifier prefix 'dup': audit_run, job",
        )

    def test_error_catalog_structure_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            catalog = _valid_error_catalog()
            catalog["envelope"] = {
                "required": ["error_code", "message"],
                "optional": ["message"],
            }
            catalog["codes"] = {
                "Bad-Code": {"http": True, "retryable": "sometimes"},
                "dependency_unavailable": {"http": 700, "retryable": "yes"},
            }
            _write_json(root, "contracts/domain/v1/error-codes.json", catalog)
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "missing required envelope fields: correlation_id",
            "required/optional overlap: message",
            "Error catalog code invalid",
            "dependency_unavailable: http must be integer 400..599",
            "dependency_unavailable: retryable must be boolean",
        )

    def test_adr_registry_allows_indexed_addition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            filenames = [_adr_filename(index) for index in range(1, 20)]
            _write_markdown(root, f"docs/architecture/adr/{filenames[-1]}")
            _write_adr_index(root, filenames)
            result = _run_validator(validator)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("adrs=19", output)
        self.assertIsNotNone(re.search(r"(?m)^PASS$", output))

    def test_adr_registry_rejects_removal_of_baseline_file_and_index_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            (root / f"docs/architecture/adr/{_adr_filename(1)}").unlink()
            _write_adr_index(
                root,
                [_adr_filename(index) for index in range(2, 19)],
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Missing baseline ADR IDs: ADR-0001",
        )

    def test_adr_registry_rejects_unindexed_missing_and_duplicate_ids(self) -> None:
        cases = ("unindexed", "missing", "duplicate")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    validator = _make_validator_checkout(root)
                    _make_valid_bootstrap(root)
                    if case == "unindexed":
                        _write_markdown(
                            root,
                            "docs/architecture/adr/ADR-0019-unindexed.md",
                        )
                        expected = "ADR files missing from index"
                    elif case == "missing":
                        filenames = [_adr_filename(index) for index in range(1, 20)]
                        _write_adr_index(root, filenames)
                        expected = "ADR index targets missing files"
                    else:
                        _write_markdown(
                            root,
                            "docs/architecture/adr/ADR-0018-duplicate.md",
                        )
                        expected = "Duplicate ADR ID ADR-0018"
                    result = _run_validator(validator)

                self.assert_validation_failure(result, expected)

    def test_real_jsonschema_rejects_invalid_schema_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_json(
                root,
                "contracts/invalid.schema.json",
                {"$schema": SCHEMA_DIALECT, "type": 7},
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "JSON Schema invalid: contracts/invalid.schema.json",
            "rule=anyOf",
        )

    def test_real_jsonschema_rejects_invalid_example_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            validator = _make_validator_checkout(root)
            _make_valid_bootstrap(root)
            _write_json(
                root,
                "contracts/analysis/v1/examples/job-package.example.json",
                [],
            )
            result = _run_validator(validator)

        self.assert_validation_failure(
            result,
            "Contract example invalid: contracts/analysis/v1/examples/job-package.example.json",
            "rule=type",
        )


if __name__ == "__main__":
    unittest.main()
