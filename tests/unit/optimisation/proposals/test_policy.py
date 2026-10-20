"""`W60-OPT-PROPOSALS-01` phase A: the rules, the identities and the migration's restatements.

Container-free. Migration ``0027_optimisation_proposals`` restates the proposal types, the
analog and match bases, the verdicts and the storage bounds rather than importing them (a
migration is history); this suite holds each restatement equal to the code it mirrors, so a
change on one side alone is a red test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.optimisation import matching, specification
from auditmanager.optimisation.policy import SCOPES
from auditmanager.optimisation.proposals import generator, policy
from auditmanager.optimisation.proposals.identity import (
    OPTIMISATION_PASS_ID_PREFIX,
    OPTIMISATION_PROPOSAL_ID_PREFIX,
    PROPOSAL_DECISION_ID_PREFIX,
    OptimisationPassId,
    OptimisationProposalId,
    ProposalDecisionId,
)
from auditmanager.optimisation.project_match import STATES, STATE_READY
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IDENTITY_TYPES_BY_PREFIX

MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "db"
    / "migrations"
    / "versions"
    / "20261020_0027_optimisation_proposals.py"
)


@pytest.fixture(scope="module")
def migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0027", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_chains_on_the_price_lists(migration: ModuleType) -> None:
    assert migration.revision == "0027_optimisation_proposals"
    assert migration.down_revision == "0026_price_lists"


def test_the_migration_restates_the_vocabularies(migration: ModuleType) -> None:
    assert migration.PROPOSAL_TYPES == generator.PROPOSAL_TYPES == ("cheaper_analog",)
    assert migration.ANALOG_BASES == generator.ANALOG_BASES
    assert migration.MATCH_BASES == matching.BASES
    assert migration.VERDICTS == policy.VERDICTS == ("accept", "reject", "revise")
    assert migration.VENDOR_LIST_SOURCES == SCOPES


def test_the_migration_restates_the_bounds(migration: ModuleType) -> None:
    assert migration.MAX_SPECIFICATION_ROWS == specification.MAX_SPECIFICATION_ROWS
    assert migration.MAX_PROPOSALS_PER_PASS == generator.MAX_PROPOSALS_PER_PASS
    assert generator.MAX_PROPOSALS_PER_PASS == (
        specification.MAX_SPECIFICATION_ROWS * generator.MAX_PROPOSALS_PER_ROW
    )
    assert migration.MAX_ROW_TEXT == generator.MAX_ROW_TEXT
    assert migration.MAX_ROW_POSITION == generator.MAX_ROW_POSITION
    assert migration.MAX_SHEET_LABEL == generator.MAX_SHEET_LABEL
    assert migration.MAX_QUANTITY_TEXT == generator.MAX_QUANTITY_TEXT
    assert migration.MAX_RATIONALE == generator.MAX_RATIONALE
    assert migration.MAX_COMMENT_LENGTH == policy.MAX_COMMENT_LENGTH


def test_the_algorithm_versions_fit_the_stored_pattern(migration: ModuleType) -> None:
    import re

    pattern = re.compile(rf"^[a-z0-9][a-z0-9.+-]{{0,{migration.MAX_ALGORITHM_LENGTH - 1}}}$")
    for version in (
        generator.GENERATOR_VERSION,
        matching.MATCH_ALGORITHM,
        specification.EXTRACTION_ALGORITHM,
    ):
        assert pattern.fullmatch(version), version


def test_every_refusal_reason_is_a_non_ready_specification_state_or_the_vendor_list() -> None:
    assert policy.PASS_REFUSAL_REASONS[:-1] == tuple(state for state in STATES if state != STATE_READY)
    assert policy.PASS_REFUSAL_REASONS[-1] == policy.REFUSAL_VENDOR_LIST_MISSING


def test_the_identities_are_contracted_and_validate_through_the_registry() -> None:
    """`W60-OPT-PROPOSALS-01` phase B contracted ``opp``, ``opr`` and ``opd`` (revision 17)."""
    from auditmanager.shared import identity as registry

    for identity, shared in (
        (OptimisationPassId, registry.OptimisationPassId),
        (OptimisationProposalId, registry.OptimisationProposalId),
        (ProposalDecisionId, registry.ProposalDecisionId),
    ):
        assert IDENTITY_TYPES_BY_PREFIX[shared.prefix] is shared
        minted = identity.new()
        assert str(minted).startswith(shared.prefix + "_") and len(str(minted)) == 30
        assert identity.parse(str(minted)) == minted
        shared(str(minted))  # the registry's own type accepts what this boundary mints
        with pytest.raises(DomainError) as caught:
            identity.parse(shared.prefix + "_short")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert OPTIMISATION_PASS_ID_PREFIX == "opp"
    assert OPTIMISATION_PROPOSAL_ID_PREFIX == "opr"
    assert PROPOSAL_DECISION_ID_PREFIX == "opd"
    with pytest.raises(DomainError):
        OptimisationPassId.parse(str(OptimisationProposalId.new()))


@pytest.mark.parametrize(
    ("roles", "allowed"),
    [
        (frozenset({"expert"}), True),
        (frozenset({"admin", "expert"}), True),
        (frozenset({"admin"}), False),
        (frozenset(), False),
    ],
)
def test_only_an_expert_starts_and_decides(roles: frozenset[str], allowed: bool) -> None:
    if allowed:
        policy.require_expert(roles, aggregate_type="OptimisationPass", act="start")
        return
    with pytest.raises(DomainError) as caught:
        policy.require_expert(roles, aggregate_type="OptimisationPass", act="start")
    assert caught.value.code is ErrorCode.PERMISSION_DENIED
    assert caught.value.detail_fields["required_capability"] == "role:expert"


@pytest.mark.parametrize(
    ("roles", "allowed"),
    [(frozenset({"expert"}), True), (frozenset({"admin"}), True), (frozenset(), False)],
)
def test_any_one_role_reads(roles: frozenset[str], allowed: bool) -> None:
    if allowed:
        policy.require_reader(roles, aggregate_type="OptimisationPass")
        return
    with pytest.raises(DomainError) as caught:
        policy.require_reader(roles, aggregate_type="OptimisationPass")
    assert caught.value.detail_fields["required_capability"] == "role:admin|expert"


def test_verdicts_and_filters() -> None:
    for verdict in ("accept", "reject", "revise"):
        assert policy.parse_verdict(verdict) == verdict
    for bad in ("pending", "Accept", "", None, 1):
        with pytest.raises(DomainError) as caught:
            policy.parse_verdict(bad)
        assert caught.value.detail_fields["field"] == "verdict"
    assert policy.parse_decision_filter(None) is None
    assert policy.parse_decision_filter("pending") == "pending"
    with pytest.raises(DomainError):
        policy.parse_decision_filter("accepted")


def test_comments_are_normalised_and_revise_requires_one() -> None:
    assert policy.normalize_comment("  дешевле,\n но   хуже ", verdict="accept") == "дешевле, но хуже"
    assert policy.normalize_comment("   ", verdict="reject") is None
    assert policy.normalize_comment(None, verdict="accept") is None
    with pytest.raises(DomainError) as caught:
        policy.normalize_comment("  ", verdict="revise")
    assert caught.value.detail_fields["constraint"] == "required"
    assert policy.normalize_comment("я" * 2000, verdict="revise") == "я" * 2000
    with pytest.raises(DomainError) as caught:
        policy.normalize_comment("я" * 2001, verdict="accept")
    assert caught.value.detail_fields["constraint"] == "max_length"
    with pytest.raises(DomainError):
        policy.normalize_comment(5, verdict="accept")
