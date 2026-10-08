#!/usr/bin/env python3
"""List independently maintained paths affected by a declared change event.

The result is an advisory grant inventory. Literal facts come from the checked-in
registry; bounded scans add files with symbolic sets and live claims. A path ending
in ``/**`` represents a family that must be granted even before its next file exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "docs/program/CONTRACT_PIN_REGISTRY.md"
FACTS = "tests/support/expected_facts.json"
FACT_KEYS = {
    "reseal-surface": ("surface.path_count", "surface.operations", "surface.schema_names"),
    "error-code": ("error_catalog.api_codes", "error_catalog.stored_vocabulary"),
    "migration": ("migration_head",),
    "table": (),
    "route": ("surface.operations",),
    "contract-version": ("contract_version",),
}
EVENT_FAMILIES = {
    "reseal-surface": ("surface",),
    "error-code": ("error_catalog",),
    "migration": ("migration_head",),
    "table": (),
    "route": (),
    "contract-version": (),
}
SOURCE_GLOBS = (
    "tests/**/*.py", "web/tests/**/*.ts", "web/tests/**/*.tsx",
    "src/**/*.py", "web/src/**/*.ts", "web/src/**/*.tsx",
    "infra/deploy/**/*.py", "infra/deploy/**/*.md", "infra/deploy/**/*.conf",
    "docs/manual-tests/**/*.md",
)
LIVE_DOCS = (
    "docs/program/CURRENT_STATE.md", "docs/program/ALPHA_ROADMAP.md",
    "docs/program/P02_SEAMS.md",
)
EXACT = {
    "reseal-surface": (
        "contracts/api/v1/openapi.json", "web/openapi/openapi.json",
        "web/FRONTEND_LOCK.json", "web/src/shared/api/generated/**",
        "web/tests/guards/frontend-lock.guard.test.ts",
        "tests/e2e/pc01/journey/manifest.json",
        "infra/deploy/README.md", "infra/deploy/proxy/nginx.conf",
        "infra/deploy/serve.py", "src/auditmanager/api/README.md",
        "src/auditmanager/api/app.py",
    ),
    "error-code": (
        "contracts/domain/v1/error-codes.json", "contracts/api/v1/openapi.json",
        "web/openapi/openapi.json", "web/src/shared/api/generated/**",
        "web/FRONTEND_LOCK.json", "web/tests/guards/frontend-lock.guard.test.ts",
    ),
    "migration": (
        "db/migrations/versions/**", "tests/integration/db/test_migration_lifecycle.py",
        "tests/contract/api_v1/test_doc_prose_facts.py",
        "docs/manual-tests/PC-01_prototype.md",
    ),
    "table": (
        "db/migrations/versions/**", "tests/integration/p02_journey/journey.py",
        "tests/integration/db/test_schema_shape.py",
        "tests/integration/composition/test_reset_rehearsal_counts_base_tables.py",
        "tests/integration/composition/test_session_register_volume.py",
        "infra/deploy/compose.server.yml", "infra/deploy/deploy.sh",
        "infra/deploy/reset.sh",
    ),
    "route": (
        "web/src/shared/config/screen-registry.ts", "web/src/shared/lib/routes.ts",
        "web/tests/guards/screen-set.guard.test.ts",
        "web/tests/guards/server-credential.guard.test.ts",
        "web/tests/guards/dashboard-invalidation.guard.test.ts",
        "web/tests/unit/styles/contrast.test.ts", "web/tests/unit/styles/screens.ts",
        "tests/e2e/pc01/journey/manifest.json",
    ),
    "contract-version": (
        "VERSION", "contracts/domain/v1/README.md", "contracts/api/v1/README.md",
        "web/FRONTEND_LOCK.json", "web/tests/guards/frontend-lock.guard.test.ts",
    ),
}
# Rules deliberately identify a claim or an enumerable set, rather than every
# unrelated assertion that happens to use a length or a familiar number.
PATTERNS = {
    "reseal-surface": re.compile(
        r"FROZEN_(?:OPERATIONS?|SCHEMA_NAMES|SCHEMA_COUNT)|"
        r"(?:PATH|OPERATION|SCHEMA)_COUNT|SurfaceTriple\(|"
        r"len\((?:router\.(?:routes|operation_ids)|"
        r"(?:application|app|client\.app)\.router\.routes|paths|declared_operations\(\))\)|"
        r"toHaveLength\((?:SCHEMA_COUNT|SEAM_OPERATIONS\.length)\)|"
        r"(?:OPERATIONS|SCHEMA_NAMES|ROUTES|SCREENS)\)\.toHaveLength\(\d+\)|"
        r"\b(?:mutating|input.?less|paginated)\s*=\s*[\{\[(]|"
        r"\b(?:SEAM_OPERATIONS|OPERATION_IDS)\b", re.I
    ),
    "error-code": re.compile(
        r"ERROR_CODE_VALUES|(?:ERROR_CODES|raw\[.codes.\]|len\(declared\))"
        r".{0,60}(?:toHaveLength\(|len\(|==|=\s*\d)|"
        r"(?:toHaveLength\(|len\().{0,60}(?:ERROR_CODE_VALUES|ERROR_CODES)", re.I
    ),
    "migration": re.compile(
        r"_true_migration_head\(|(?:MIGRATION|ALEMBIC|HEAD)_?(?:HEAD|REVISION)|"
        r"down_revision\s*=", re.I
    ),
    "table": re.compile(
        r"P02_TABLES|(?:BASE|EXPECTED|APPLICATION|APP)_TABLES|"
        r"base_tables|(?:service_names|SERVICES|services:)\s*(?:=|\{|\[|$)", re.I
    ),
    "route": re.compile(
        r"(?:FROZEN|REGISTERED|SCREEN|APP)_ROUTES|(?:SCREEN|ROUTE)_REGISTRY|"
        r"(?:mutating|input.?less|paginated)\s*=\s*[\{\[(]|"
        r"route(?:s)?\.length|toHaveLength\(ROUTES\.length\)", re.I
    ),
    "contract-version": re.compile(
        r"(?:DOMAIN|API)_CONTRACT_VERSION\s*=|"
        r"(?:contract[_ -]?version|domain[_ -]?version).{0,50}\b\d+\.\d+\.\d+[-\w.]*\b|"
        r"\b\d+\.\d+\.\d+[-\w.]*\b.{0,50}(?:contract[_ -]?version|domain[_ -]?version)", re.I
    ),
}
PROSE = {
    "reseal-surface": re.compile(
        r"\b(?:api surface|openapi surface|frozen document|contract surface|served document|"
        r"(?:api|openapi|contract) (?:has|declares)|surface (?:is|has|contains))\b"
        r".{0,160}(?:\b\d+\b|\b(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[- ]?\w*)", re.I
    ),
    "error-code": re.compile(
        r"\b(?:error catalog|error-code catalog|code catalog)\b.{0,60}\b\d+\b|"
        r"\b\d+\b.{0,30}\b(?:error[- ]?code catalog|error catalog)\b", re.I
    ),
    "migration": re.compile(r"\b(?:migration|alembic)\s+head\b|\bhead\s+(?:is|at)\s+`?\d{4}", re.I),
    "table": re.compile(r"\b(?:base table|service list|application table)\b.{0,50}\b\d+\b", re.I),
    "route": re.compile(r"\b(?:screen registry|route registry|registered screens?)\b.{0,50}\b\d+\b", re.I),
    "contract-version": re.compile(r"\b(?:contract|domain|api)\s+version\b", re.I),
}
REGISTRY_BLOCK = re.compile(r"^```json\s*\n(?P<json>\{.*?\})\s*\n```", re.M | re.S)


class SweepError(ValueError):
    """An input would make the inventory incomplete or unsafe."""


def valid_path(value: str) -> str:
    if not value or value == "." or "\\" in value or value.startswith("/") or "//" in value:
        raise SweepError(f"invalid repository path: {value!r}")
    parts = PurePosixPath(value).parts
    if any(part in (".", "..") for part in parts) or any("*" in part and part != "**" for part in parts):
        raise SweepError(f"invalid repository path: {value!r}")
    return value


def read_registry(root: Path) -> list[dict[str, str]]:
    path = root / REGISTRY
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SweepError(f"missing registry input: {path}") from exc
    blocks = list(REGISTRY_BLOCK.finditer(source))
    if len(blocks) != 1:
        raise SweepError("registry must contain exactly one JSON block")
    try:
        data = json.loads(blocks[0].group("json"))
    except json.JSONDecodeError as exc:
        raise SweepError(f"malformed registry JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("registry_version") != 1 or not isinstance(data.get("pins"), list):
        raise SweepError("unsupported registry schema")
    seen: set[str] = set()
    locations: set[tuple[str, str]] = set()
    for pin in data["pins"]:
        required = ("pin_id", "family", "path", "needle", "event")
        if not isinstance(pin, dict) or any(
            not isinstance(pin.get(key), str) or not pin[key] for key in required
        ):
            raise SweepError("incomplete registry pin")
        valid_path(pin["path"])
        if pin["family"] not in {"surface", "error_catalog", "migration_head", "history_boundary"}:
            raise SweepError(f"unknown registry family: {pin['family']}")
        if pin["pin_id"] in seen:
            raise SweepError(f"duplicate registry pin: {pin['pin_id']}")
        location = (pin["path"], pin["needle"])
        if location in locations:
            raise SweepError(f"duplicate registry location: {pin['path']}")
        seen.add(pin["pin_id"])
        locations.add(location)
    return data["pins"]


def validate_facts_if_present(root: Path) -> None:
    path = root / FACTS
    if not path.exists():
        return  # The planned facts file is created by a separate task.
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SweepError(f"malformed expected facts: {exc}") from exc
    if not isinstance(data, dict) or data.get("facts_version") != 1:
        raise SweepError("unsupported expected facts schema")
    for keys in FACT_KEYS.values():
        for key in keys:
            value = data
            for part in key.split("."):
                if not isinstance(value, dict) or part not in value:
                    raise SweepError(f"missing expected fact: {key}")
                value = value[part]


def _source_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in SOURCE_GLOBS:
        files.update(path for path in root.glob(pattern) if path.is_file())
    files.update(root / name for name in LIVE_DOCS if (root / name).is_file())
    for path in files:
        if not path.resolve().is_relative_to(root):
            raise SweepError(f"candidate escapes repository: {path}")
    return sorted(files)


def collect(root: Path, events: list[str]) -> dict[str, list[str]]:
    unknown = sorted(set(events) - EVENT_FAMILIES.keys())
    if unknown or not events:
        raise SweepError(f"unknown or absent event: {', '.join(unknown) or '<none>'}")
    pins = read_registry(root)
    validate_facts_if_present(root)
    result: dict[str, set[str]] = defaultdict(set)

    def add(path: str, reason: str) -> None:
        result[valid_path(path)].add(reason)

    for event in sorted(set(events)):
        add(REGISTRY, f"{event}: registry")
        fields = ", ".join(FACT_KEYS[event]) or "no table field; review alongside schema"
        add(FACTS, f"{event}: expected facts ({fields})")
        for path in EXACT[event]:
            add(path, f"{event}: catalogue")
        if event in {"reseal-surface", "error-code", "migration", "table", "route", "contract-version"}:
            for doc in LIVE_DOCS:
                add(doc, f"{event}: live claims")
        for pin in pins:
            if pin["family"] in EVENT_FAMILIES[event]:
                add(pin["path"], f"{event}: {pin['pin_id']}")

    for file in _source_files(root):
        rel = file.relative_to(root).as_posix()
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SweepError(f"cannot read candidate: {rel}: {exc}") from exc
        is_prose = rel.endswith(".md") or rel.endswith(".conf")
        # Claims are sentence-sized; searching a whole source file would make an
        # unrelated number on the next page look like the count in a preceding note.
        lines = source.splitlines()
        for event in sorted(set(events)):
            pattern = PROSE[event] if is_prose else PATTERNS[event]
            if any(pattern.search(line) for line in lines):
                add(rel, f"{event}: {'prose' if is_prose else 'pattern'}")
            # Runtime comments and multiline strings carry live claims as well.
            runtime = rel.startswith(("src/", "web/src/", "infra/deploy/"))
            if not is_prose and runtime and any(PROSE[event].search(line) for line in lines):
                add(rel, f"{event}: live claim")
    return {path: sorted(reasons) for path, reasons in sorted(result.items())}


def grants_from_task(task: Path) -> list[str]:
    try:
        source = task.read_text(encoding="utf-8")
    except OSError as exc:
        raise SweepError(f"cannot read task: {task}") from exc
    match = re.search(r"^##\s+(?:Allowed paths|allowed_paths)\s*$", source, re.M | re.I)
    if not match:
        raise SweepError("task has no Allowed paths section")
    tail = source[match.end():].split("\n## ", 1)[0]
    grants: list[str] = []
    for line in tail.splitlines():
        if not re.match(r"^\s*[-*]\s+", line):
            continue
        for path in re.findall(r"`([^`]+)`", line):
            grants.extend(valid_path(item) for item in _expand_braces(path))
    if not grants:
        raise SweepError("task has no allowed_paths grants")
    return grants


def _expand_braces(path: str) -> list[str]:
    """Expand only the finite directory alternatives used in task grants."""
    match = re.search(r"\{([^{}]+)\}", path)
    if not match:
        return [path]
    choices = match.group(1).split(",")
    if not choices or any(not choice or "/" in choice or "*" in choice for choice in choices):
        raise SweepError(f"invalid grant alternatives: {path!r}")
    return [
        expanded
        for choice in choices
        for expanded in _expand_braces(path[:match.start()] + choice + path[match.end():])
    ]


def granted(path: str, grants: list[str]) -> bool:
    for grant in grants:
        if path == grant:
            return True
        if grant.endswith("/**") and path.startswith(grant[:-3] + "/"):
            return True
        if path.endswith("/**") and grant.endswith("/**") and path[:-3].startswith(grant[:-3] + "/"):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", nargs="+", choices=sorted(EVENT_FAMILIES))
    parser.add_argument("--check", type=Path, help="task file whose allowed_paths must cover the inventory")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (also for fixture tests)")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        inventory = collect(root, args.events)
        grants = grants_from_task(args.check) if args.check else None
    except (OSError, SweepError) as exc:
        print(f"pin_sweep: {exc}", file=sys.stderr)
        return 2
    missing = []
    for path, reasons in inventory.items():
        absent = grants is not None and not granted(path, grants)
        print(f"{'MISSING ' if absent else ''}{path}\t{'; '.join(reasons)}")
        if absent:
            missing.append(path)
    if missing:
        print(f"pin_sweep: {len(missing)} missing allowed_paths grants", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
