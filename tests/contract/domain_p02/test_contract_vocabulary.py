"""The migration head encodes the frozen vocabulary, and claims nothing more.

Two directions matter equally. The schema must not *narrow* a frozen enum, or a
legal value becomes an unexplained constraint violation at run time; and it must not
*widen* one, or a value the contract never declared becomes storable and the fail-
closed rule is gone.
"""

from __future__ import annotations

from types import ModuleType

import pytest

PC01_MACHINES = ("audit_run", "blob", "command_idempotency")
NOT_INSTANTIATED_MACHINES = ("import", "job", "attempt")


def test_error_code_domain_equals_the_frozen_catalog(
    migration_module: ModuleType, error_codes_contract: dict
) -> None:
    assert set(migration_module.ERROR_CODES) == set(error_codes_contract["codes"])
    assert len(migration_module.ERROR_CODES) == 20


def test_stage_ids_equal_the_analysis_registry(
    migration_module: ModuleType, stage_registry_contract: dict
) -> None:
    declared = [stage["stage_id"] for stage in stage_registry_contract["stages"]]
    assert list(migration_module.STAGE_IDS) == declared


def test_stage_statuses_equal_the_stage_result_schema(
    migration_module: ModuleType, stage_result_schema: dict
) -> None:
    declared = stage_result_schema["properties"]["status"]["enum"]
    assert set(migration_module.STAGE_STATUSES) == set(declared)


def test_run_states_equal_the_audit_run_machine(
    migration_module: ModuleType, state_machines_contract: dict
) -> None:
    machine = state_machines_contract["machines"]["audit_run"]
    declared = {machine["initial"]}
    for origin, targets in machine["transitions"].items():
        declared.add(origin)
        declared.update(targets)
    declared.update(machine["terminal"])
    assert set(migration_module.RUN_STATES) == declared


def test_the_run_state_domain_has_no_succeeded(migration_module: ModuleType) -> None:
    """C-2. `succeeded` is a StageResult status on a different aggregate."""
    assert "succeeded" not in migration_module.RUN_STATES
    assert "published" in migration_module.RUN_STATES


def test_blob_states_equal_the_blob_machine(
    migration_module: ModuleType, state_machines_contract: dict
) -> None:
    machine = state_machines_contract["machines"]["blob"]
    declared = {machine["initial"], *machine["terminal"]}
    for origin, targets in machine["transitions"].items():
        declared.add(origin)
        declared.update(targets)
    assert set(migration_module.BLOB_STATES) == declared


def test_command_states_equal_the_idempotency_machine(
    migration_module: ModuleType, state_machines_contract: dict
) -> None:
    machine = state_machines_contract["machines"]["command_idempotency"]
    declared = {machine["initial"], *machine["terminal"]}
    for origin, targets in machine["transitions"].items():
        declared.add(origin)
        declared.update(targets)
    assert set(migration_module.COMMAND_STATES) == declared


@pytest.mark.parametrize("machine_name", PC01_MACHINES)
def test_the_seeded_topology_equals_the_declared_topology(
    migration_module: ModuleType, state_machines_contract: dict, machine_name: str
) -> None:
    """Edge for edge, in both directions."""
    machine = state_machines_contract["machines"][machine_name]
    declared: set[tuple[str, str | None, str]] = {
        (machine_name, None, machine["initial"])
    }
    for origin, targets in machine["transitions"].items():
        for target in targets:
            declared.add((machine_name, origin, target))

    seeded = {row for row in migration_module.STATE_TOPOLOGY if row[0] == machine_name}
    assert seeded == declared, (
        f"{machine_name}: seeded-but-undeclared {sorted(seeded - declared)}, "
        f"declared-but-unseeded {sorted(declared - seeded)}"
    )


@pytest.mark.parametrize("machine_name", NOT_INSTANTIATED_MACHINES)
def test_a_machine_pc01_does_not_instantiate_is_absent(
    migration_module: ModuleType, migration_sql: str, machine_name: str
) -> None:
    """Absent, not silently present-and-unreachable.

    The topology table's own CHECK is the second half of this: it admits only the
    three instantiated machine names, so seeding a fourth is refused by the database
    even before the immutability trigger stops the insert.
    """
    seeded = {row[0] for row in migration_module.STATE_TOPOLOGY}
    assert machine_name not in seeded
    admitted = migration_sql.split("ck_contract_state_transition_machine")[1].split(")")[0]
    assert f"'{machine_name}'" not in admitted


@pytest.mark.parametrize("machine_name", PC01_MACHINES)
def test_terminal_states_have_no_outgoing_edge(
    migration_module: ModuleType, state_machines_contract: dict, machine_name: str
) -> None:
    machine = state_machines_contract["machines"][machine_name]
    outgoing = {
        row[1] for row in migration_module.STATE_TOPOLOGY if row[0] == machine_name
    }
    for terminal in machine["terminal"]:
        assert terminal not in outgoing, (
            f"{machine_name}.{terminal} is terminal but has an outgoing edge; a "
            "terminal aggregate is never reopened"
        )


def test_publishing_a_run_backwards_is_undeclared(migration_module: ModuleType) -> None:
    """Named explicitly by P2-DOM-01's required tests."""
    edges = {row for row in migration_module.STATE_TOPOLOGY if row[0] == "audit_run"}
    assert ("audit_run", "published", "running") not in edges
    assert ("audit_run", "published", "queued") not in edges


def test_finding_categories_are_the_two_pc01_questions(migration_module: ModuleType) -> None:
    assert set(migration_module.FINDING_CATEGORIES) == {
        "internal_contradiction",
        "explicit_placeholder",
    }


def test_the_verdict_enum_is_closed_at_four_values(migration_module: ModuleType) -> None:
    assert set(migration_module.VERDICTS) == {
        "pending",
        "accepted",
        "rejected",
        "needs_manual_review",
    }


def test_the_decision_event_enum_keeps_revoke_implementable(
    migration_module: ModuleType,
) -> None:
    """PD-01 revocation must stay implementable without a schema change."""
    assert "revoke" in migration_module.DECISION_EVENT_TYPES
    assert set(migration_module.DECISION_EVENT_TYPES) == {
        "accept",
        "reject",
        "comment",
        "revoke",
    }


def test_the_head_is_the_single_p02_revision(migration_module: ModuleType) -> None:
    assert migration_module.revision == "0002_pc01_schema"
    assert migration_module.down_revision == "0001_baseline"
    assert migration_module.branch_labels is None


def test_no_table_exists_for_an_aggregate_pc01_does_not_instantiate(
    migration_sql: str,
) -> None:
    forbidden = (
        "CREATE TABLE job",
        "CREATE TABLE attempt",
        "CREATE TABLE lease",
        "CREATE TABLE import ",
        "CREATE TABLE export",
        "CREATE TABLE worker",
        "CREATE TABLE comparison",
        "CREATE TABLE norms_snapshot",
        "CREATE TABLE outbox",
    )
    for statement in forbidden:
        assert statement not in migration_sql


# Column-level claims - no object-key column, which tables are append-only - are
# asserted against a live database in tests/integration/db/test_schema_shape.py, by
# reading information_schema and pg_trigger. Grepping the migration source for a
# column name matches its own explanatory comments, which is how a test ends up
# proving that a docstring exists.


def test_the_error_envelope_enum_matches_the_catalog(
    error_envelope_schema: dict, error_codes_contract: dict
) -> None:
    """A premise of the OpenAPI test; asserted here so a failure names the right file."""
    envelope_codes = error_envelope_schema["properties"]["error_code"]["enum"]
    assert set(envelope_codes) == set(error_codes_contract["codes"])
