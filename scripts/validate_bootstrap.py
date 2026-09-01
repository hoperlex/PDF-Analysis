#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
BASELINE_ADR_IDS = {f"ADR-{number:04d}" for number in range(1, 19)}

REQUIRED_FILES = (
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
)

CONTRACT_EXAMPLE_PAIRS = (
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
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]*)\)")
ADR_FILE_RE = re.compile(
    r"^docs/architecture/adr/(ADR-\d{4})(?:-[A-Za-z0-9][A-Za-z0-9._-]*)?\.md$"
)
ADR_INDEX_LINK_RE = re.compile(r"\[([^\]]+)\]\((adr/[^)\s#]+\.md)(?:#[^)]*)?\)")
ADR_ID_RE = re.compile(r"^(ADR-\d{4})(?:\b|-)")
ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

DENIED_PATH_COMPONENTS = frozenset(
    {
        ".git",
        ".local",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
    }
)
DENIED_PATH_SEQUENCES = (
    ("artifacts", "local"),
    ("fixtures", "private"),
)
DENIED_FILENAMES = frozenset({".coverage", "coverage.xml"})


def _add_error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _is_denied_repository_path(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    if any(part in DENIED_PATH_COMPONENTS for part in parts):
        return True
    for sequence in DENIED_PATH_SEQUENCES:
        width = len(sequence)
        if any(parts[index : index + width] == sequence for index in range(len(parts) - width + 1)):
            return True
    if parts and parts[-1] in DENIED_FILENAMES:
        return True
    if parts and parts[-1] != ".env.example" and parts[-1].startswith(".env"):
        return True
    return bool(parts and parts[-1].endswith((".log", ".tmp", ".swp")))


def _discover_repository_files(root: Path, errors: list[str]) -> list[str]:
    command = (
        "git",
        "-C",
        str(root),
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
    )
    try:
        result = subprocess.run(command, capture_output=True, check=False)
    except OSError as exc:
        _add_error(
            errors,
            f"Git discovery unavailable ({type(exc).__name__}); "
            "run validation from a Git checkout with git installed",
        )
        return []

    if result.returncode != 0:
        _add_error(
            errors,
            f"Git discovery failed (exit {result.returncode}); "
            "run validation from a valid Git checkout",
        )
        return []

    discovered: set[str] = set()
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        try:
            relative = raw_path.decode("utf-8")
        except UnicodeDecodeError:
            _add_error(errors, "Git discovery returned a non-UTF-8 repository path")
            continue
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            _add_error(errors, "Git discovery returned an unsafe repository path")
            continue
        normalized = candidate.as_posix()
        if _is_denied_repository_path(normalized):
            continue
        discovered.add(normalized)
    return sorted(discovered)


class RepositoryReader:
    def __init__(self, root: Path, discovered: set[str], errors: list[str]) -> None:
        self.root = root
        self.discovered = discovered
        self.errors = errors
        self._text_cache: dict[str, str | None] = {}
        self._json_cache: dict[str, Any | None] = {}
        self._json_failures: set[str] = set()
        self._shape_errors: set[tuple[str, str]] = set()

    def read_text(self, relative: str, purpose: str) -> str | None:
        if relative in self._text_cache:
            return self._text_cache[relative]

        path = self.root / relative
        if relative not in self.discovered:
            _add_error(self.errors, f"Missing repository-owned {purpose}: {relative}")
            self._text_cache[relative] = None
            return None
        if path.is_symlink():
            _add_error(self.errors, f"Refusing symlink for {purpose}: {relative}")
            self._text_cache[relative] = None
            return None
        try:
            value = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            _add_error(self.errors, f"Missing {purpose}: {relative}")
            value = None
        except UnicodeDecodeError:
            _add_error(self.errors, f"Invalid UTF-8 in {purpose}: {relative}")
            value = None
        except OSError as exc:
            _add_error(
                self.errors,
                f"Cannot read {purpose}: {relative} ({type(exc).__name__})",
            )
            value = None
        self._text_cache[relative] = value
        return value

    def read_json(self, relative: str, purpose: str) -> Any | None:
        if relative in self._json_cache:
            return self._json_cache[relative]

        text = self.read_text(relative, purpose)
        if text is None:
            self._json_cache[relative] = None
            self._json_failures.add(relative)
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            _add_error(
                self.errors,
                f"Invalid JSON in {purpose}: {relative} "
                f"(line {exc.lineno}, column {exc.colno})",
            )
            value = None
            self._json_failures.add(relative)
        except (TypeError, ValueError) as exc:
            _add_error(
                self.errors,
                f"Cannot decode JSON for {purpose}: {relative} ({type(exc).__name__})",
            )
            value = None
            self._json_failures.add(relative)
        self._json_cache[relative] = value
        return value

    def json_failed(self, relative: str) -> bool:
        return relative in self._json_failures

    def require_object(
        self,
        relative: str,
        purpose: str,
        value: Any | None = None,
    ) -> dict[str, Any] | None:
        if value is None:
            value = self.read_json(relative, purpose)
        if self.json_failed(relative):
            return None
        if not isinstance(value, dict):
            key = (relative, purpose)
            if key not in self._shape_errors:
                _add_error(
                    self.errors,
                    f"Wrong top-level shape for {purpose}: {relative}; expected object",
                )
                self._shape_errors.add(key)
            return None
        return value


def _safe_validation_detail(exc: Exception) -> str:
    location = list(getattr(exc, "absolute_path", ()))
    rendered_location = ".".join(str(item) for item in location) or "<root>"
    rule = getattr(exc, "validator", None) or type(exc).__name__
    return f"at {rendered_location}; rule={rule}"


def _validate_schema_documents(
    reader: RepositoryReader,
    json_files: list[str],
    validator_class: Any,
    errors: list[str],
) -> dict[str, bool]:
    valid_schemas: dict[str, bool] = {}
    for relative in json_files:
        value = reader.read_json(relative, "JSON artifact")
        if reader.json_failed(relative):
            continue

        marker_present = isinstance(value, dict) and "$schema" in value
        schema_candidate = relative.endswith(".schema.json") or marker_present
        if not schema_candidate:
            continue

        schema = reader.require_object(relative, "JSON Schema", value)
        if schema is None:
            valid_schemas[relative] = False
            continue
        marker = schema.get("$schema")
        if not isinstance(marker, str):
            _add_error(
                errors,
                f"Malformed $schema in {relative}; expected string dialect URI",
            )
            valid_schemas[relative] = False
            continue
        if marker != SUPPORTED_SCHEMA_DIALECT:
            _add_error(
                errors,
                f"Unsupported $schema dialect in {relative}; expected Draft 2020-12",
            )
            valid_schemas[relative] = False
            continue
        try:
            validator_class.check_schema(schema)
        except Exception as exc:
            _add_error(
                errors,
                f"JSON Schema invalid: {relative}; {_safe_validation_detail(exc)}",
            )
            valid_schemas[relative] = False
        else:
            valid_schemas[relative] = True
    return valid_schemas


def _validate_contract_examples(
    reader: RepositoryReader,
    validator_class: Any,
    valid_schemas: dict[str, bool],
    errors: list[str],
) -> None:
    for schema_relative, example_relative in CONTRACT_EXAMPLE_PAIRS:
        schema = reader.require_object(schema_relative, "contract schema")
        example = reader.read_json(example_relative, "contract example")
        if schema is None or reader.json_failed(example_relative):
            continue
        if not valid_schemas.get(schema_relative, False):
            continue
        try:
            validator_class(schema).validate(example)
        except Exception as exc:
            _add_error(
                errors,
                f"Contract example invalid: {example_relative} vs {schema_relative}; "
                f"{_safe_validation_detail(exc)}",
            )


def _validate_identifiers(reader: RepositoryReader, errors: list[str]) -> None:
    relative = "contracts/domain/v1/identifiers.json"
    document = reader.require_object(relative, "domain identifier catalog")
    if document is None:
        return
    identifiers = document.get("identifiers")
    if not isinstance(identifiers, dict):
        _add_error(
            errors,
            f"Domain identifiers structure invalid: {relative}; identifiers must be object",
        )
        return

    by_prefix: dict[str, list[str]] = defaultdict(list)
    for identifier, prefix in identifiers.items():
        if not isinstance(identifier, str) or not identifier:
            _add_error(errors, f"Domain identifier key invalid: {relative}")
            continue
        if not isinstance(prefix, str) or not prefix:
            _add_error(
                errors,
                f"Domain identifier prefix invalid: {relative}; identifier={identifier}",
            )
            continue
        by_prefix[prefix].append(identifier)

    for prefix, identifiers_with_prefix in sorted(by_prefix.items()):
        if len(identifiers_with_prefix) > 1:
            _add_error(
                errors,
                f"Duplicate domain identifier prefix '{prefix}': "
                + ", ".join(sorted(identifiers_with_prefix)),
            )


def _validate_state_machines(reader: RepositoryReader, errors: list[str]) -> None:
    relative = "contracts/domain/v1/state-machines.json"
    document = reader.require_object(relative, "domain state-machine catalog")
    if document is None:
        return
    machines = document.get("machines")
    if not isinstance(machines, dict):
        _add_error(
            errors,
            f"State-machine catalog invalid: {relative}; machines must be object",
        )
        return

    for name, machine in sorted(machines.items(), key=lambda item: str(item[0])):
        if not isinstance(name, str) or not name:
            _add_error(errors, f"State-machine name invalid: {relative}")
            continue
        if not isinstance(machine, dict):
            _add_error(errors, f"State machine {name} invalid: expected object")
            continue

        initial = machine.get("initial")
        terminal = machine.get("terminal")
        transitions = machine.get("transitions")
        if not isinstance(initial, str) or not initial:
            _add_error(errors, f"State machine {name}: initial must be non-empty string")
        if not isinstance(terminal, list) or not all(
            isinstance(value, str) and value for value in terminal
        ):
            _add_error(errors, f"State machine {name}: terminal must be string array")
            terminal_states: list[str] = []
        else:
            terminal_states = terminal
            if len(terminal_states) != len(set(terminal_states)):
                _add_error(errors, f"State machine {name}: duplicate terminal state")
        if not isinstance(transitions, dict):
            _add_error(errors, f"State machine {name}: transitions must be object")
            continue

        usable_transitions: dict[str, list[str]] = {}
        for source, destinations in transitions.items():
            if not isinstance(source, str) or not source:
                _add_error(errors, f"State machine {name}: transition source invalid")
                continue
            if not isinstance(destinations, list) or not all(
                isinstance(destination, str) and destination for destination in destinations
            ):
                _add_error(
                    errors,
                    f"State machine {name}: destinations for {source} must be string array",
                )
                continue
            usable_transitions[source] = destinations

        states = set(usable_transitions) | set(terminal_states)
        if isinstance(initial, str) and initial and initial not in states:
            _add_error(errors, f"State machine {name}: initial state missing from state set")
        for source, destinations in usable_transitions.items():
            for destination in destinations:
                if destination not in states:
                    _add_error(
                        errors,
                        f"State machine {name}: transition {source}->{destination} "
                        "points to unknown state",
                    )
        for terminal_state in terminal_states:
            if usable_transitions.get(terminal_state):
                _add_error(
                    errors,
                    f"State machine {name}: terminal state {terminal_state} "
                    "has outgoing transition",
                )


def _validate_error_catalog(reader: RepositoryReader, errors: list[str]) -> None:
    relative = "contracts/domain/v1/error-codes.json"
    document = reader.require_object(relative, "domain error catalog")
    if document is None:
        return

    for field in ("contract", "version"):
        if not isinstance(document.get(field), str) or not document[field]:
            _add_error(
                errors,
                f"Error catalog invalid: {relative}; {field} must be non-empty string",
            )

    envelope = document.get("envelope")
    if not isinstance(envelope, dict):
        _add_error(errors, f"Error catalog invalid: {relative}; envelope must be object")
    else:
        required = envelope.get("required")
        optional = envelope.get("optional")
        for field_name, fields in (("required", required), ("optional", optional)):
            if not isinstance(fields, list) or not all(
                isinstance(field, str) and field for field in fields
            ):
                _add_error(
                    errors,
                    f"Error catalog invalid: {relative}; envelope.{field_name} "
                    "must be string array",
                )
            elif len(fields) != len(set(fields)):
                _add_error(
                    errors,
                    f"Error catalog invalid: {relative}; duplicate envelope.{field_name} field",
                )
        if isinstance(required, list) and all(isinstance(field, str) for field in required):
            missing = {"error_code", "message", "correlation_id"} - set(required)
            if missing:
                _add_error(
                    errors,
                    f"Error catalog invalid: {relative}; missing required envelope fields: "
                    + ", ".join(sorted(missing)),
                )
        if isinstance(required, list) and isinstance(optional, list):
            overlap = {field for field in required if isinstance(field, str)} & {
                field for field in optional if isinstance(field, str)
            }
            if overlap:
                _add_error(
                    errors,
                    f"Error catalog invalid: {relative}; required/optional overlap: "
                    + ", ".join(sorted(overlap)),
                )

    codes = document.get("codes")
    if not isinstance(codes, dict) or not codes:
        _add_error(errors, f"Error catalog invalid: {relative}; codes must be non-empty object")
        return
    for code, definition in sorted(codes.items(), key=lambda item: str(item[0])):
        if not isinstance(code, str) or not ERROR_CODE_RE.fullmatch(code):
            _add_error(errors, f"Error catalog code invalid: {relative}; code={code!r}")
            continue
        if not isinstance(definition, dict):
            _add_error(errors, f"Error catalog code {code}: definition must be object")
            continue
        http_status = definition.get("http")
        retryable = definition.get("retryable")
        if (
            not isinstance(http_status, int)
            or isinstance(http_status, bool)
            or not 400 <= http_status <= 599
        ):
            _add_error(errors, f"Error catalog code {code}: http must be integer 400..599")
        if not isinstance(retryable, bool):
            _add_error(errors, f"Error catalog code {code}: retryable must be boolean")


def _validate_markdown_links(
    reader: RepositoryReader,
    markdown_files: list[str],
    errors: list[str],
) -> None:
    for relative in markdown_files:
        text = reader.read_text(relative, "Markdown artifact")
        if text is None:
            continue
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target_parts = raw_target.strip().split()
            if not target_parts:
                _add_error(errors, f"Malformed md link target: {relative}; target is empty")
                continue
            target = target_parts[0].strip("<>")
            if not target:
                _add_error(
                    errors,
                    f"Malformed md link target: {relative}; "
                    "target is empty after angle-bracket normalization",
                )
                continue
            if target.startswith(("#", "http://", "https://", "mailto:", "urn:")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            if "<" in target or ">" in target:
                _add_error(
                    errors,
                    f"Malformed md link target: {relative}; invalid angle brackets",
                )
                continue
            resolved = (reader.root / relative).parent.joinpath(target).resolve()
            try:
                resolved.relative_to(reader.root.resolve())
            except ValueError:
                continue
            if not resolved.exists():
                _add_error(errors, f"Broken md link: {relative} -> {target}")


def _validate_adr_registry(
    reader: RepositoryReader,
    discovered: list[str],
    errors: list[str],
) -> int:
    candidate_paths = sorted(
        relative
        for relative in discovered
        if relative.startswith("docs/architecture/adr/ADR-") and relative.endswith(".md")
    )
    files_by_id: dict[str, list[str]] = defaultdict(list)
    for relative in candidate_paths:
        match = ADR_FILE_RE.fullmatch(relative)
        if not match:
            _add_error(errors, f"ADR filename invalid: {relative}")
            continue
        files_by_id[match.group(1)].append(relative)
        reader.read_text(relative, "ADR document")

    for adr_id, paths in sorted(files_by_id.items()):
        if len(paths) > 1:
            _add_error(errors, f"Duplicate ADR ID {adr_id}: " + ", ".join(paths))

    actual_ids = set(files_by_id)
    missing_baseline_files = BASELINE_ADR_IDS - actual_ids
    if missing_baseline_files:
        _add_error(
            errors,
            "Missing baseline ADR IDs: " + ", ".join(sorted(missing_baseline_files)),
        )

    index_relative = "docs/architecture/ADR_INDEX.md"
    index_text = reader.read_text(index_relative, "ADR index")
    if index_text is None:
        return len(candidate_paths)

    index_paths: list[str] = []
    index_ids: list[str] = []
    for label, target in ADR_INDEX_LINK_RE.findall(index_text):
        label_match = ADR_ID_RE.match(label)
        target_name = Path(target).name
        target_match = re.match(r"^(ADR-\d{4})(?:\b|-)", target_name)
        if label_match is None or target_match is None:
            _add_error(errors, f"ADR index entry invalid: {target}")
            continue
        label_id = label_match.group(1)
        target_id = target_match.group(1)
        if label_id != target_id:
            _add_error(
                errors,
                f"ADR index ID mismatch: label={label_id}, target={target_id}",
            )
        index_ids.append(target_id)
        index_paths.append(f"docs/architecture/{target}")

    for adr_id in sorted(set(index_ids)):
        if index_ids.count(adr_id) > 1:
            _add_error(errors, f"Duplicate ADR index ID: {adr_id}")
    for relative in sorted(set(index_paths)):
        if index_paths.count(relative) > 1:
            _add_error(errors, f"Duplicate ADR index path: {relative}")

    actual_paths = set(candidate_paths)
    indexed_paths = set(index_paths)
    unindexed = actual_paths - indexed_paths
    missing_files = indexed_paths - actual_paths
    if unindexed:
        _add_error(errors, "ADR files missing from index: " + ", ".join(sorted(unindexed)))
    if missing_files:
        _add_error(errors, "ADR index targets missing files: " + ", ".join(sorted(missing_files)))

    missing_baseline_index = BASELINE_ADR_IDS - set(index_ids)
    if missing_baseline_index:
        _add_error(
            errors,
            "ADR index missing baseline IDs: " + ", ".join(sorted(missing_baseline_index)),
        )
    return len(candidate_paths)


def _validate_repository(validator_class: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    notes: list[str] = []
    discovered = _discover_repository_files(ROOT, errors)
    discovered_set = set(discovered)
    reader = RepositoryReader(ROOT, discovered_set, errors)

    json_files = [relative for relative in discovered if relative.endswith(".json")]
    markdown_files = [relative for relative in discovered if relative.endswith(".md")]

    for relative in json_files:
        reader.read_json(relative, "JSON artifact")
    valid_schemas = _validate_schema_documents(reader, json_files, validator_class, errors)
    _validate_contract_examples(reader, validator_class, valid_schemas, errors)
    _validate_identifiers(reader, errors)
    _validate_state_machines(reader, errors)
    _validate_error_catalog(reader, errors)
    _validate_markdown_links(reader, markdown_files, errors)

    for relative in REQUIRED_FILES:
        reader.read_text(relative, "required file")

    stage_files = [
        relative
        for relative in discovered
        if re.fullmatch(r"docs/stages/S\d{2}_[^/]+\.md", relative)
    ]
    manual_files = [
        relative
        for relative in discovered
        if re.fullmatch(r"docs/manual-tests/CP-\d{2}_[^/]+\.md", relative)
    ]
    adr_count = _validate_adr_registry(reader, discovered, errors)

    notes.extend(
        (
            f"json_files={len(json_files)}",
            f"markdown_files={len(markdown_files)}",
            f"stages={len(stage_files)}",
            f"manual_runbooks={len(manual_files)}",
            f"adrs={adr_count}",
        )
    )
    if len(stage_files) != 11:
        _add_error(errors, f"Expected 11 stage files, got {len(stage_files)}")
    if len(manual_files) != 11:
        _add_error(errors, f"Expected 11 checkpoint runbooks, got {len(manual_files)}")
    return errors, notes


def main() -> int:
    try:
        from jsonschema import Draft202012Validator

        if not callable(Draft202012Validator):
            raise TypeError("Draft202012Validator is not callable")
        if not callable(getattr(Draft202012Validator, "check_schema", None)):
            raise TypeError("Draft202012Validator.check_schema is not callable")
    except Exception as exc:
        print("Bootstrap validation")
        print(
            "FAILED: required Python dependency 'jsonschema' is unavailable or "
            f"unusable ({type(exc).__name__})."
        )
        print(
            "Action: provision a compatible 'jsonschema' package in this command's "
            "Python environment, then rerun the validator."
        )
        return 2

    try:
        errors, notes = _validate_repository(Draft202012Validator)
    except Exception as exc:
        errors = [
            "Internal validator failure "
            f"({type(exc).__name__}); rerun with the focused contract tests"
        ]
        notes = []

    print("Bootstrap validation")
    for note in notes:
        print("  " + note)
    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for error in errors:
            print(" - " + error)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
