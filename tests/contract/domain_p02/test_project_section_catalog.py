"""`R-40`, `D-56`, `W59-SECTION-SEAL-01`: the project sections, spelled in several places.

The vocabulary is restated rather than imported in each copy -- the migrations' CHECK
constraints, the frozen `ProjectSection` enum, `dashboard.repository`'s own
`PROJECT_SECTIONS` tuple and the section suggestion catalogue -- for the same reason
`test_contract_vocabulary.py` gives for the error catalog and the state machines: a
migration that imported application code would change meaning when that code changes, and
the domain layer does not import the transport contract. Independent spellings only stay
one vocabulary if something checks them against each other, which is what this file is.

Two vocabularies are held apart on purpose. **Legacy's fourteen** is the historical record:
migration ``0011_document_section`` wrote it and keeps it, and the control below still
measures it. **The current fifteen** is legacy's fourteen plus ``PS`` (the explanatory
note, never ``PB``): the contract, the dashboard, migration ``0024_version_classification``
(the version classification CHECK and the widened ``document.section`` CHECK) and the
suggestion catalogue carry it.
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
CLASSIFICATION_MIGRATION = (
    REPOSITORY_ROOT
    / "db"
    / "migrations"
    / "versions"
    / "20261020_0024_version_classification.py"
)
SUGGESTION_CATALOGUE = (
    REPOSITORY_ROOT / "src" / "auditmanager" / "sections" / "suggestion_patterns.json"
)
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"

#: `D-56`, `backend/app/pipeline/stages/prepare/task_builder.py:1362`. The one place this
#: fourteen-item list is actually *written down* as a fact about the legacy system, rather
#: than restated by something that has to agree with it. Every other copy in this suite
#: and in the tree is checked against this tuple.
LEGACY_SECTIONS = (
    "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS",
)

#: `W59-SECTION-SEAL-01`: the current vocabulary, legacy's fourteen in legacy's order and then
#: ``PS``. Written here once; every current copy is checked against it.
CURRENT_SECTIONS = (*LEGACY_SECTIONS, "PS")


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
def classification_migration_module() -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "w59_version_classification", CLASSIFICATION_MIGRATION
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


def test_the_current_vocabulary_is_legacy_plus_ps_and_ps_is_not_pb() -> None:
    """The second control: fifteen distinct codes, the legacy fourteen as a prefix, and
    ``PS`` a new code rather than a respelling of ``PB``."""
    assert len(CURRENT_SECTIONS) == len(set(CURRENT_SECTIONS)) == 15
    assert CURRENT_SECTIONS[:14] == LEGACY_SECTIONS
    assert "PS" not in LEGACY_SECTIONS and "PB" in CURRENT_SECTIONS


def test_the_historical_0011_check_constraint_keeps_legacy_fourteen(
    section_migration_module: ModuleType,
) -> None:
    """``0011`` is history and is not rewritten: its CHECK stays the fourteen it wrote."""
    assert tuple(section_migration_module.PROJECT_SECTIONS) == LEGACY_SECTIONS


def test_the_0024_migration_carries_the_current_fifteen_and_restores_legacy(
    classification_migration_module: ModuleType,
) -> None:
    """``0024`` widens ``document.section`` and checks the classification against the
    current fifteen; its downgrade restores exactly ``0011``'s fourteen."""
    assert tuple(classification_migration_module.PROJECT_SECTIONS) == CURRENT_SECTIONS
    assert tuple(classification_migration_module.LEGACY_PROJECT_SECTIONS) == LEGACY_SECTIONS
    assert tuple(classification_migration_module.PROJECT_STAGES) == ("P", "R")


def test_the_frozen_project_section_enum_matches_the_current_vocabulary(
    openapi_document: dict,
) -> None:
    declared = openapi_document["components"]["schemas"]["ProjectSection"]["enum"]
    assert declared == list(CURRENT_SECTIONS)
    stages = openapi_document["components"]["schemas"]["ProjectStage"]["enum"]
    assert stages == ["P", "R"]


def test_the_dashboard_repositorys_vocabulary_matches_the_current_vocabulary() -> None:
    """`R-44`'s `section_breakdown` panel iterates its own tuple, not the migration's or
    the contract's -- see `dashboard.repository`'s own docstring for why the domain layer
    restates rather than imports across either boundary. Checked here so a sixteenth
    section added to one copy could not silently miss this one."""
    from auditmanager.dashboard.repository import PROJECT_SECTIONS

    assert PROJECT_SECTIONS == CURRENT_SECTIONS


def test_the_section_suggestion_catalogue_names_the_current_vocabulary() -> None:
    """The suggestion catalogue and the profile registry key on the same fifteen codes."""
    catalogue = json.loads(SUGGESTION_CATALOGUE.read_text(encoding="utf-8"))
    codes = [entry["code"] for entry in catalogue["sections"]]
    assert sorted(codes) == sorted(CURRENT_SECTIONS)


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
