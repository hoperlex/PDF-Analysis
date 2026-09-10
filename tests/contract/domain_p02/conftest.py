"""Loaders for the frozen contracts, the migration head and the seam register.

This suite needs no database. It asserts that three descriptions of the same thing
agree: the frozen CP-00 contracts, the DDL in the P02 migration head, and the value
types and documents `A1` froze at Gate A. Each of the three is a separate artifact
somebody can edit alone, and that is exactly what these tests exist to catch.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPOSITORY_ROOT / "contracts"
MIGRATION = (
    REPOSITORY_ROOT / "db" / "migrations" / "versions" / "20260910_0002_pc01_schema.py"
)
OPENAPI = CONTRACTS / "api" / "v1" / "openapi.json"
SEAM_REGISTER = REPOSITORY_ROOT / "docs" / "program" / "P02_SEAMS.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def identifiers_contract() -> dict:
    return _load_json(CONTRACTS / "domain" / "v1" / "identifiers.json")


@pytest.fixture(scope="session")
def state_machines_contract() -> dict:
    return _load_json(CONTRACTS / "domain" / "v1" / "state-machines.json")


@pytest.fixture(scope="session")
def error_codes_contract() -> dict:
    return _load_json(CONTRACTS / "domain" / "v1" / "error-codes.json")


@pytest.fixture(scope="session")
def error_envelope_schema() -> dict:
    return _load_json(CONTRACTS / "domain" / "v1" / "error-envelope.schema.json")


@pytest.fixture(scope="session")
def stage_registry_contract() -> dict:
    return _load_json(CONTRACTS / "analysis" / "v1" / "stage-registry.json")


@pytest.fixture(scope="session")
def stage_result_schema() -> dict:
    return _load_json(CONTRACTS / "analysis" / "v1" / "stage-result.schema.json")


@pytest.fixture(scope="session")
def openapi_document() -> dict:
    return _load_json(OPENAPI)


@pytest.fixture(scope="session")
def migration_module() -> ModuleType:
    """The P02 migration, imported as a module.

    Its vocabulary tuples and its topology are Python data, so the tests read the
    same values the DDL is built from rather than regex-scraping SQL text.
    """
    specification = importlib.util.spec_from_file_location("p02_head", MIGRATION)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def migration_sql() -> str:
    """The migration's source text, for the assertions that are about the DDL itself."""
    return MIGRATION.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def seam_register_text() -> str:
    return SEAM_REGISTER.read_text(encoding="utf-8")


def parse_markdown_table(text: str, header_contains: str) -> list[dict[str, str]]:
    """Parse the first GitHub-flavoured table whose header row contains a phrase.

    The seam register is a document people read; keeping its machine-readable content
    in the same tables the reader sees avoids the usual failure where a duplicated
    JSON block and the prose drift apart.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|") or header_contains not in line:
            continue
        if index + 1 >= len(lines) or not re.match(r"^\|[\s:|-]+\|$", lines[index + 1]):
            continue
        columns = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.startswith("|"):
                break
            cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
            if len(cells) != len(columns):
                continue
            rows.append(dict(zip(columns, cells, strict=True)))
        return rows
    raise AssertionError(f"no markdown table whose header contains {header_contains!r}")


@pytest.fixture(scope="session")
def markdown_table():
    return parse_markdown_table
