"""`ANALYSIS-PRESETS-01`: the name rule and the bounds, no database.

A preset is a name plus an executor connection (the premise of the lane): the rules here are the
name's, and the migration restates the bounds instead of importing them, so the equalities are a
test's job.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.executors import presets
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "db/migrations/versions/20261027_0037_analysis_presets.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0037", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _constraint(raw: object) -> str:
    with pytest.raises(DomainError) as caught:
        presets.clean_name(raw)
    error = caught.value
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert error.detail_fields["field"] == "name"
    return str(error.detail_fields["constraint"])


def test_the_chain_and_the_revision_id() -> None:
    migration = _migration()
    assert migration.revision == "0037_analysis_presets"
    assert migration.down_revision == "0036_cite_partition_v3"
    # alembic_version.version_num is varchar(32): a longer id cannot be stored
    assert len(migration.revision) <= 32


def test_the_restated_bounds_and_states_equal_the_code() -> None:
    migration = _migration()
    assert migration.MAX_PRESETS == presets.MAX_PRESETS == 100
    assert migration.MAX_NAME_LENGTH == presets.MAX_NAME_LENGTH == 120
    assert tuple(migration.STATES) == presets.STATES == ("active", "archived")


def test_a_name_is_kept_trimmed() -> None:
    assert presets.clean_name("  Чертежи, быстрый \t\n") == "Чертежи, быстрый"


def test_a_name_of_exactly_the_limit_is_kept() -> None:
    name = "Ж" * presets.MAX_NAME_LENGTH
    assert presets.clean_name(name) == name


@pytest.mark.parametrize(
    ("raw", "constraint"),
    [
        (None, "type"), (7, "type"), (["x"], "type"),
        ("", "required"), ("   ", "required"), ("\t\n", "required"),
        ("Ж" * (presets.MAX_NAME_LENGTH + 1), "max_length"),
        ("А\x00Б", "printable"), ("А\tБ", "printable"), ("А\nБ", "printable"),
        ("А\x7fБ", "printable"), ("А\x85Б", "printable"), ("А Б", "printable"),
    ],
)
def test_a_name_that_is_not_acceptable_names_the_constraint_it_breaks(raw: object, constraint: str) -> None:
    assert _constraint(raw) == constraint


def test_the_length_is_measured_after_trimming() -> None:
    assert presets.clean_name(" " + "Ж" * presets.MAX_NAME_LENGTH + " ") == "Ж" * presets.MAX_NAME_LENGTH


def test_two_names_differing_only_by_case_are_one_name() -> None:
    assert presets.name_key("Чертежи") == presets.name_key("ЧЕРТЕЖИ") == presets.name_key("чертежи")
    assert presets.name_key("Чертежи") != presets.name_key("Чертежи 2")


def test_a_refusal_carries_the_existing_codes_and_detail_keys_only() -> None:
    conflict = presets.preset_conflict("preset_name_in_use")
    assert conflict.code is ErrorCode.CONFLICT
    assert conflict.detail_fields == {"conflict_reason": "preset_name_in_use", "aggregate_type": "AnalysisPreset"}
    assert presets.preset_archived().detail_fields["conflict_reason"] == "preset_archived"
    missing = presets.not_found()
    assert missing.code is ErrorCode.NOT_FOUND and missing.detail_fields == {"aggregate_type": "AnalysisPreset"}
