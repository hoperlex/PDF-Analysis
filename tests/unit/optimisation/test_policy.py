"""`W60-PRICE-LIST-01` phase A: the rules, the identities and every restated vocabulary.

Container-free. The migration ``0026_price_lists`` restates the fifteen sections, the
format/media-type pairs and the bounds instead of importing them (a migration is history);
these tests hold every spelling equal, so the copies stay one vocabulary.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.optimisation import policy
from auditmanager.optimisation.identity import PriceListId, PriceListPositionId, VendorListId
from auditmanager.optimisation.parsing import MEDIA_TYPES
from auditmanager.optimisation.parsing import limits
from auditmanager.optimisation.parsing.values import SECTION_ABBREVIATIONS
from auditmanager.sections.public import SECTION_CODES
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IDENTITY_TYPES_BY_PREFIX, pattern_for

MIGRATION = (
    Path(__file__).resolve().parents[3] / "db" / "migrations" / "versions" / "20261020_0026_price_lists.py"
)


@pytest.fixture(scope="module")
def migration() -> ModuleType:
    specification = importlib.util.spec_from_file_location("w60_price_lists", MIGRATION)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_the_migration_chains_on_the_dispatcher_revision(migration: ModuleType) -> None:
    assert migration.revision == "0026_price_lists"
    assert migration.down_revision == "0025_work_assignments"


def test_the_fifteen_sections_are_one_vocabulary(migration: ModuleType) -> None:
    assert migration.PROJECT_SECTIONS == policy.SECTION_ORDER
    assert set(policy.SECTION_ORDER) == set(SECTION_CODES)
    assert len(policy.SECTION_ORDER) == 15
    assert set(SECTION_ABBREVIATIONS) == set(SECTION_CODES)
    assert len(set(SECTION_ABBREVIATIONS.values())) == 15


def test_the_migration_restates_the_formats_and_the_bounds(migration: ModuleType) -> None:
    assert migration.SOURCE_MEDIA_TYPES == dict(MEDIA_TYPES)
    assert migration.MAX_DATA_ROWS == limits.MAX_DATA_ROWS
    assert migration.MAX_NAME_LENGTH == limits.MAX_NAME_LENGTH
    assert migration.MAX_CODE_LENGTH == limits.MAX_CODE_LENGTH
    assert migration.MAX_MARK_LENGTH == limits.MAX_MARK_LENGTH
    assert migration.MAX_UNIT_LENGTH == limits.MAX_UNIT_LENGTH
    assert migration.MAX_VENDOR_LENGTH == limits.MAX_VENDOR_LENGTH == policy.MAX_VENDOR_LENGTH
    assert migration.MAX_VENDOR_LIST_ENTRIES == policy.MAX_VENDOR_LIST_ENTRIES
    assert migration.MAX_MATERIAL_LENGTH == policy.MAX_MATERIAL_LENGTH
    assert migration.MAX_ENTRY_NOTE_LENGTH == policy.MAX_ENTRY_NOTE_LENGTH
    assert migration.VENDOR_LIST_SCOPES == policy.SCOPES
    assert migration.VENDOR_LIST_MODES == policy.MODES
    assert limits.MAX_BYTES == 10 * 1024 * 1024
    assert limits.MAX_DATA_ROWS == 20_000


@pytest.mark.parametrize("identity", [PriceListId, PriceListPositionId, VendorListId])
def test_each_identity_is_opaque_free_in_the_registry_and_checked(identity: type) -> None:
    assert identity.prefix not in IDENTITY_TYPES_BY_PREFIX
    minted = identity.new()
    assert identity.parse(str(minted)) == minted
    assert str(minted).startswith(f"{identity.prefix}_")
    assert identity._pattern.pattern == pattern_for(identity.prefix)
    for bad in ("", f"{identity.prefix}_short", "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", 7):
        with pytest.raises(DomainError) as caught:
            identity.parse(bad)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert caught.value.detail_fields["constraint"] == "pattern"


def test_the_migration_checks_name_the_same_identity_patterns(migration: ModuleType) -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    for prefix in ("prl", "prp", "vnl", "prj", "usr", "blob"):
        assert f"'^{prefix}_{{ULID}}$'" in source
    assert migration.ULID == "[0-9A-HJKMNP-TV-Z]{26}"
    assert pattern_for("prl") == "^prl_" + migration.ULID + "$"


@pytest.mark.parametrize(
    ("check", "roles", "allowed"),
    [
        (policy.require_reader, frozenset(), False),
        (policy.require_reader, frozenset({"expert"}), True),
        (policy.require_reader, frozenset({"admin"}), True),
    ],
)
def test_reading_needs_any_one_role(check, roles: frozenset[str], allowed: bool) -> None:
    if allowed:
        check(roles, aggregate_type="PriceList")
        return
    with pytest.raises(DomainError) as caught:
        check(roles, aggregate_type="PriceList")
    assert caught.value.code is ErrorCode.PERMISSION_DENIED
    assert caught.value.detail_fields["required_capability"] == "role:admin|expert"


@pytest.mark.parametrize(
    ("roles", "expert_ok", "admin_ok"),
    [
        (frozenset(), False, False),
        (frozenset({"expert"}), True, False),
        (frozenset({"admin"}), False, True),
        (frozenset({"admin", "expert"}), True, True),
    ],
)
def test_the_expert_and_the_administrator_acts(roles: frozenset[str], expert_ok: bool, admin_ok: bool) -> None:
    for check, ok, capability in (
        (policy.require_expert, expert_ok, "role:expert"),
        (policy.require_admin, admin_ok, "role:admin"),
    ):
        if ok:
            check(roles, aggregate_type="VendorList", act="act")
            continue
        with pytest.raises(DomainError) as caught:
            check(roles, aggregate_type="VendorList", act="act")
        assert caught.value.code is ErrorCode.PERMISSION_DENIED
        assert caught.value.detail_fields == {
            "aggregate_type": "VendorList",
            "required_capability": capability,
        }


def test_entries_are_normalised_in_order_and_bounded() -> None:
    entries = policy.normalize_entries(
        [
            {"material": "  Кабель   силовой ", "vendor": " Кабельный  завод ", "note": ""},
            {"vendor": "Завод 2"},
        ]
    )
    assert entries == (
        policy.VendorListEntry("Кабель силовой", "Кабельный завод", None),
        policy.VendorListEntry(None, "Завод 2", None),
    )
    assert policy.normalize_entries(None) == ()
    assert policy.normalize_entries([]) == ()
    assert policy.normalize_entries(list(entries)) == entries


@pytest.mark.parametrize(
    ("raw", "field", "constraint"),
    [
        ("text", "entries", "type"),
        ([{"material": "x"}], "vendor", "required"),
        ([{"vendor": "  "}], "vendor", "required"),
        ([{"vendor": 5}], "vendor", "type"),
        (["Завод"], "entries", "type"),
        ([{"vendor": "я" * 501}], "vendor", "max_length"),
        ([{"vendor": "Завод", "material": "я" * 501}], "material", "max_length"),
        ([{"vendor": "Завод", "note": "я" * 1001}], "note", "max_length"),
        ([{"vendor": "Завод"}] * 501, "entries", "max_items"),
    ],
)
def test_malformed_entries_are_refused(raw: object, field: str, constraint: str) -> None:
    with pytest.raises(DomainError) as caught:
        policy.normalize_entries(raw)  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert caught.value.detail_fields["field"] == field
    assert caught.value.detail_fields["constraint"] == constraint


def test_section_mode_and_currency_values() -> None:
    assert policy.parse_section_code("PS") == "PS"
    assert policy.parse_mode("inherit") == "inherit"
    assert policy.parse_currency_code(" RUB ") == "RUB"
    assert policy.parse_currency_code(None) is None
    assert policy.parse_currency_code("") is None
    for call, value in (
        (policy.parse_section_code, "ЭОМ"),
        (policy.parse_section_code, "eom"),
        (policy.parse_mode, "replace"),
        (policy.parse_currency_code, "rub"),
        (policy.parse_currency_code, "РУБ"),
        (policy.parse_currency_code, "RUBL"),
    ):
        with pytest.raises(DomainError) as caught:
            call(value)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED


@pytest.mark.parametrize(
    ("project_mode", "has_global", "expected"),
    [
        ("list", True, "project"),
        ("list", False, "project"),
        ("inherit", True, "global"),
        ("inherit", False, "none"),
        (None, True, "global"),
        (None, False, "none"),
    ],
)
def test_the_effective_list_is_the_project_list_else_the_global_else_none(
    project_mode: str | None, has_global: bool, expected: str
) -> None:
    assert policy.effective_source(project_mode=project_mode, has_global=has_global) == expected
