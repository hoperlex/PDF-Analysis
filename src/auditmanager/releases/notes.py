"""Shape validation of authored release files; editorial prose rules run in the gate."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from auditmanager.releases.versioning import canonical_semver_sort_key

_ENTRY_NAME = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?\.json$")
_KINDS = frozenset({"new", "improved", "fixed"})
_KNOWN_NON_ENTRIES = frozenset({"schema.json", "dictionary.json"})
_SCHEMA_KEYS = frozenset({
    "$schema", "$defs", "$ref", "title", "type", "additionalProperties",
    "required", "properties", "items", "minItems", "minLength", "minimum",
    "enum", "format",
})


@dataclass(frozen=True, slots=True)
class ReleaseNote:
    version: str
    revision: int
    released_on: date
    title: str
    is_archive: bool
    range_label: str | None
    items: tuple[dict[str, str], ...]
    content: dict[str, Any]
    content_sha256: str


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"release note {name} must be a nonempty string")
    return value


def _validate_shape(value: Any, spec: dict[str, Any], root: dict[str, Any], path: str) -> None:
    """Evaluate exactly the shape keywords used by our checked-in JSON Schema.

    An unknown schema keyword refuses deployment, so this small runtime
    validator cannot silently ignore a future constraint.
    """
    unknown = set(spec) - _SCHEMA_KEYS
    if unknown:
        raise ValueError(f"unsupported release schema keyword at {path}: {sorted(unknown)}")
    ref = spec.get("$ref")
    if ref is not None:
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            raise ValueError(f"unsupported release schema reference at {path}")
        target = root.get("$defs", {}).get(ref.removeprefix("#/$defs/"))
        if not isinstance(target, dict):
            raise ValueError(f"missing release schema definition at {path}")
        _validate_shape(value, target, root, path)
        return
    kind = spec.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            raise ValueError(f"release note {path} must be an object")
        required = set(spec.get("required", ()))
        if not required <= set(value):
            raise ValueError(f"release note {path} is missing {sorted(required - set(value))}")
        properties = spec.get("properties", {})
        if spec.get("additionalProperties") is False and set(value) - set(properties):
            raise ValueError(f"release note {path} has unknown fields")
        for name, member in value.items():
            if name in properties:
                _validate_shape(member, properties[name], root, f"{path}.{name}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) < spec.get("minItems", 0):
            raise ValueError(f"release note {path} must be a nonempty array")
        for index, member in enumerate(value):
            _validate_shape(member, spec["items"], root, f"{path}[{index}]")
    elif kind == "string":
        if not isinstance(value, str) or len(value) < spec.get("minLength", 0):
            raise ValueError(f"release note {path} must be a string")
        if spec.get("format") == "date":
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError
                date.fromisoformat(value)
            except ValueError:
                raise ValueError(f"release note {path} must be a date") from None
    elif kind == "integer":
        if type(value) is not int or value < spec.get("minimum", -float("inf")):
            raise ValueError(f"release note {path} must be a positive integer")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError(f"release note {path} must be a boolean")
    elif kind is not None:
        raise ValueError(f"unsupported release schema type at {path}: {kind}")
    if "enum" in spec and value not in spec["enum"]:
        raise ValueError(f"release note {path} has an unknown value")


def parse_note(raw: Any, *, filename: str) -> ReleaseNote:
    """Validate the deployment shape, independently of editorial vocabulary."""
    if not isinstance(raw, dict) or set(raw) - {
        "version", "revision", "date", "title", "items", "is_archive", "range_label"
    } or not {"version", "revision", "date", "title", "items"} <= set(raw):
        raise ValueError(f"release note has unknown or missing fields: {filename}")
    version = _nonempty_string(raw["version"], "version")
    canonical_semver_sort_key(version)
    if filename != f"{version}.json":
        raise ValueError(f"release note filename does not match version: {filename}")
    revision = raw["revision"]
    if type(revision) is not int or revision < 1:
        raise ValueError(f"release note revision must be a positive integer: {filename}")
    date_text = _nonempty_string(raw["date"], "date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
        raise ValueError(f"release note date must be YYYY-MM-DD: {filename}")
    try:
        released_on = date.fromisoformat(date_text)
    except ValueError:
        raise ValueError(f"release note date is invalid: {filename}") from None
    title = _nonempty_string(raw["title"], "title")
    is_archive = raw.get("is_archive", False)
    if type(is_archive) is not bool:
        raise ValueError(f"release note is_archive must be boolean: {filename}")
    range_label = raw.get("range_label")
    if is_archive:
        _nonempty_string(range_label, "range_label")
    elif range_label is not None:
        raise ValueError(f"non-archive release has range_label: {filename}")
    items_raw = raw["items"]
    if not isinstance(items_raw, list) or not items_raw:
        raise ValueError(f"release note items must be a nonempty array: {filename}")
    items: list[dict[str, str]] = []
    for item in items_raw:
        if not isinstance(item, dict) or set(item) != {"kind", "screen", "where", "text"}:
            raise ValueError(f"release note item has wrong fields: {filename}")
        if not isinstance(item["kind"], str) or item["kind"] not in _KINDS:
            raise ValueError(f"release note item has unknown kind: {filename}")
        items.append({
            name: _nonempty_string(item[name], name)
            for name in ("kind", "screen", "where", "text")
        })
    # A revision number changes the event identity, not the authored content.
    # Hash only the latter, so a bumped revision with unchanged content refuses.
    content: dict[str, Any] = {
        "version": version, "date": date_text, "title": title,
        "is_archive": is_archive, "range_label": range_label, "items": items,
    }
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return ReleaseNote(
        version, revision, released_on, title, is_archive, range_label,
        tuple(items), content, hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def read_notes(directory: Path) -> dict[str, ReleaseNote]:
    if not directory.is_dir():
        raise FileNotFoundError(f"release note directory is absent: {directory}")
    if not (directory / "schema.json").is_file():
        raise FileNotFoundError("release note shape schema is absent")
    try:
        schema = json.loads((directory / "schema.json").read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid release note shape schema") from exc
    if not isinstance(schema, dict):
        raise ValueError("release note shape schema must be an object")
    notes: dict[str, ReleaseNote] = {}
    for path in sorted(directory.iterdir()):
        if path.name in _KNOWN_NON_ENTRIES and path.is_file():
            continue
        if not path.is_file() or _ENTRY_NAME.fullmatch(path.name) is None:
            raise ValueError(f"unknown release-notes entry: {path.name}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid release note JSON: {path.name}") from exc
        _validate_shape(raw, schema, schema, path.name)
        note = parse_note(raw, filename=path.name)
        notes[note.version] = note
    return notes
