"""The identity types, the contract catalog and the migration's CHECKs agree.

Three artifacts describe the same 25 identities. Any one of them can be edited
alone, which is what these tests are for.
"""

from __future__ import annotations

import re
from types import ModuleType

import pytest

from auditmanager.shared.identity import (
    IDENTIFIER_PATTERN,
    IDENTITY_TYPES_BY_ENTITY,
    IDENTITY_TYPES_BY_PREFIX,
    UNALLOCATED_IN_PC01,
    IdentifierFormatError,
    IdentifierPrefixError,
    OpaqueId,
    ProjectUid,
    RunId,
    is_valid_ulid,
    new_ulid,
    pattern_for,
)
from auditmanager.shared.identity.ulid import ULID_LENGTH, alphabet


def test_every_declared_identifier_has_a_type(identifiers_contract: dict) -> None:
    declared = set(identifiers_contract["identifiers"])
    implemented = {
        f"{entity}:{identity.prefix}" for entity, identity in IDENTITY_TYPES_BY_ENTITY.items()
    }
    assert len(implemented) == len(declared), (
        f"contract declares {len(declared)} identifiers, "
        f"{len(IDENTITY_TYPES_BY_ENTITY)} types exist"
    )


def test_entity_to_type_binding_matches_the_contract(identifiers_contract: dict) -> None:
    for entity, identifier_name in identifiers_contract["entities"].items():
        assert entity in IDENTITY_TYPES_BY_ENTITY, f"no identity type for entity {entity}"
        expected_prefix = identifiers_contract["identifiers"][identifier_name]
        assert IDENTITY_TYPES_BY_ENTITY[entity].prefix == expected_prefix


def test_prefixes_are_exactly_the_contract_prefixes(identifiers_contract: dict) -> None:
    assert set(IDENTITY_TYPES_BY_PREFIX) == set(identifiers_contract["identifiers"].values())


def test_prefixes_are_globally_unique(identifiers_contract: dict) -> None:
    prefixes = list(identifiers_contract["identifiers"].values())
    assert len(prefixes) == len(set(prefixes))


def test_generated_identifiers_match_the_catalog_pattern(identifiers_contract: dict) -> None:
    catalog_pattern = re.compile(identifiers_contract["id_pattern"])
    for prefix, identity in sorted(IDENTITY_TYPES_BY_PREFIX.items()):
        value = str(identity.new())
        assert catalog_pattern.match(value), f"{identity.__name__} produced {value!r}"
        assert re.match(pattern_for(prefix), value)


def test_the_local_pattern_constant_equals_the_catalog_one(identifiers_contract: dict) -> None:
    assert IDENTIFIER_PATTERN == identifiers_contract["id_pattern"]


def test_the_pattern_template_is_instantiated_faithfully(identifiers_contract: dict) -> None:
    template = identifiers_contract["pattern_template"]
    for prefix in sorted(IDENTITY_TYPES_BY_PREFIX):
        assert pattern_for(prefix) == template.replace("{prefix}", prefix)


def test_the_ulid_alphabet_and_length_match_the_contract(identifiers_contract: dict) -> None:
    declared = identifiers_contract["ulid"]
    assert alphabet() == declared["alphabet"]
    assert ULID_LENGTH == declared["length"]
    assert declared["encoding"].startswith("Crockford")


def test_generated_ulids_avoid_the_excluded_letters() -> None:
    """I, L, O and U are excluded so a human never confuses one for a digit."""
    excluded = set("ILOU")
    for _ in range(200):
        assert not (set(new_ulid()) & excluded)


def test_ulid_shape_validation_is_strict() -> None:
    assert is_valid_ulid(new_ulid())
    assert not is_valid_ulid("")
    assert not is_valid_ulid("0" * 25)
    assert not is_valid_ulid("0" * 27)
    assert not is_valid_ulid("I" * ULID_LENGTH)
    assert not is_valid_ulid(None)


def test_identifiers_are_unique_across_many_allocations() -> None:
    values = {str(RunId.new()) for _ in range(5000)}
    assert len(values) == 5000


def test_a_wrong_entity_identifier_is_rejected_at_construction() -> None:
    with pytest.raises(IdentifierPrefixError):
        ProjectUid.parse(str(RunId.new()))


@pytest.mark.parametrize(
    "value",
    [
        "prj_",
        "prj_TOOSHORT",
        "prj_01M2545JSD15ETSNNV904X991I",  # I is not in the alphabet
        "prj_01m2545jsd15etsnnv904x991f",  # lowercase body
        "PRJ_01M2545JSD15ETSNNV904X991F",  # uppercase prefix
        "prj-01M2545JSD15ETSNNV904X991F",  # wrong separator
        "/var/lib/projects/ar-1",
        "F-014",
        "",
    ],
)
def test_a_malformed_identifier_is_rejected_at_construction(value: str) -> None:
    with pytest.raises(IdentifierFormatError):
        ProjectUid.parse(value)


def test_a_non_string_is_rejected() -> None:
    for value in (None, 1, 1.0, b"prj_01M2545JSD15ETSNNV904X991F", ["x"]):
        with pytest.raises(IdentifierFormatError):
            ProjectUid.parse(value)  # type: ignore[arg-type]


def test_identities_are_immutable_and_compare_by_type_and_value() -> None:
    project = ProjectUid.new()
    assert ProjectUid.parse(str(project)) == project
    assert hash(ProjectUid.parse(str(project))) == hash(project)
    assert (project == str(project)) is False
    with pytest.raises(AttributeError):
        project.value = "prj_01M2545JSD15ETSNNV904X991F"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del project._value  # type: ignore[attr-defined]


def test_no_identity_type_exposes_a_decoder() -> None:
    """Opacity, asserted rather than trusted to a docstring.

    The contract forbids decoding the ULID body for creation time, ownership or
    ordering. There must be nothing to call.
    """
    banned = {
        "timestamp",
        "created_at",
        "datetime",
        "time",
        "decode",
        "to_datetime",
        "milliseconds",
        "randomness",
    }
    for identity in IDENTITY_TYPES_BY_PREFIX.values():
        exposed = {name for name in dir(identity) if not name.startswith("_")}
        assert not (exposed & banned), f"{identity.__name__} exposes {exposed & banned}"

    import auditmanager.shared.identity.ulid as ulid_module

    module_names = {name for name in dir(ulid_module) if not name.startswith("_")}
    assert not (module_names & {"decode", "decode_ulid", "timestamp_of", "parse_ulid"})


def test_identities_are_not_orderable() -> None:
    """Ordering by identity would be ordering by creation time through the back door."""
    first, second = RunId.new(), RunId.new()
    with pytest.raises(TypeError):
        _ = first < second  # type: ignore[operator]
    with pytest.raises(TypeError):
        sorted([first, second])


def test_a_duplicate_prefix_cannot_be_registered() -> None:
    with pytest.raises(TypeError, match="already bound"):

        class Duplicate(OpaqueId, prefix="prj", entity="Impostor"):
            pass


def test_the_unallocated_list_names_only_declared_identifiers(
    identifiers_contract: dict,
) -> None:
    declared = set(identifiers_contract["identifiers"])
    assert set(UNALLOCATED_IN_PC01) <= declared


def test_the_unallocated_list_covers_the_task_handoff() -> None:
    """P2-DOM-01's handoff names these explicitly; the seam register must too."""
    required = {
        "job_id",
        "attempt_id",
        "lease_id",
        "worker_id",
        "export_id",
        "comparison_id",
        "sheet_link_id",
        "norms_snapshot_id",
        "erasure_request_id",
        "import_id",
    }
    assert required <= set(UNALLOCATED_IN_PC01)


def test_the_migration_checks_use_the_contract_pattern(
    migration_module: ModuleType, identifiers_contract: dict
) -> None:
    """The database CHECK and the value type must accept exactly the same strings."""
    for prefix in sorted(IDENTITY_TYPES_BY_PREFIX):
        rendered = migration_module.id_check("column", prefix)
        expected = f"column ~ '{pattern_for(prefix)}'"
        assert rendered == expected


def test_the_migration_ulid_body_matches_the_contract(
    migration_module: ModuleType, identifiers_contract: dict
) -> None:
    template = identifiers_contract["pattern_template"]
    body = template.replace("^{prefix}_", "").replace("$", "")
    assert migration_module.ULID_BODY == body


def test_non_identity_values_are_a_separate_type() -> None:
    from auditmanager.shared.identity import CorrelationId, IdempotencyKey, Sha256

    for value_type in (CorrelationId, IdempotencyKey, Sha256):
        assert not issubclass(value_type, OpaqueId)


def test_non_identity_patterns_match_the_contract(identifiers_contract: dict) -> None:
    from auditmanager.shared.identity import CORRELATION_PATTERN, IDEMPOTENCY_KEY_PATTERN

    assert (
        CORRELATION_PATTERN
        == identifiers_contract["correlation_identifiers"]["correlation_id"]["pattern"]
    )
    assert (
        IDEMPOTENCY_KEY_PATTERN
        == identifiers_contract["command_keys"]["idempotency_key"]["pattern"]
    )
