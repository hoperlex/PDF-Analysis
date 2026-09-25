"""`R-40`, `D-56`: legacy's fourteen project sections, spelled in three places.

The vocabulary is restated rather than imported in each of the three -- the migration's
CHECK constraint, the frozen `ProjectSection` enum and `dashboard.repository`'s own
`PROJECT_SECTIONS` tuple -- for the same reason `test_contract_vocabulary.py` gives for
the error catalog and the state machines: a migration that imported application code
would change meaning when that code changes, and the domain layer does not import the
transport contract. Three independent spellings only stay one vocabulary if something
checks them against each other, which is what this file is.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SECTION_MIGRATION = (
    REPOSITORY_ROOT / "db" / "migrations" / "versions" / "20260925_0011_document_section.py"
)
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"

#: `D-56`, `backend/app/pipeline/stages/prepare/task_builder.py:1362`. The one place this
#: fourteen-item list is actually *written down* as a fact about the legacy system, rather
#: than restated by something that has to agree with it. Every other copy in this suite
#: and in the tree is checked against this tuple.
LEGACY_SECTIONS = (
    "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS",
)


@pytest.fixture(scope="module")
def section_migration_module() -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "w46_document_section", SECTION_MIGRATION
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def openapi_document() -> dict:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))


def test_legacy_measurement_is_fourteen_and_has_no_duplicate() -> None:
    """The control. If this ever failed, every other test in this file would be
    comparing three copies against a fourth that was itself wrong."""
    assert len(LEGACY_SECTIONS) == 14
    assert len(set(LEGACY_SECTIONS)) == 14


def test_the_migrations_check_constraint_matches_legacy(
    section_migration_module: ModuleType,
) -> None:
    assert tuple(section_migration_module.PROJECT_SECTIONS) == LEGACY_SECTIONS


def test_the_frozen_project_section_enum_matches_legacy(
    openapi_document: dict,
) -> None:
    declared = openapi_document["components"]["schemas"]["ProjectSection"]["enum"]
    assert declared == list(LEGACY_SECTIONS)


def test_the_dashboard_repositorys_vocabulary_matches_legacy() -> None:
    """`R-44`'s `section_breakdown` panel iterates its own tuple, not the migration's or
    the contract's -- see `dashboard.repository`'s own docstring for why the domain layer
    restates rather than imports across either boundary. Checked here so a fifteenth
    section added to one of the three could not silently miss this one."""
    from auditmanager.dashboard.repository import PROJECT_SECTIONS

    assert PROJECT_SECTIONS == LEGACY_SECTIONS


def test_upload_document_request_and_document_version_both_reference_the_enum(
    openapi_document: dict,
) -> None:
    """`R-40`'s field is on the document (see `docs/program/W46-SEAL.md` section 2), and
    both the write shape and the read shape must draw from the same enum -- a caller
    that could write a value the reader could not classify would be worse than not
    having the field at all."""
    schemas = openapi_document["components"]["schemas"]
    for name in ("UploadDocumentRequest", "DocumentVersion"):
        section_property = schemas[name]["properties"]["section"]
        assert section_property["$ref"] == "#/components/schemas/ProjectSection", name
        assert "section" not in schemas[name].get("required", []), (
            f"{name}.section is optional -- absent is not empty, and a required section "
            "would force every caller, tests/e2e/** included, to guess one"
        )
