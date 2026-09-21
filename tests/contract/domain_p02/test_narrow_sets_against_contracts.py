"""Hand-maintained subsets of contract-defined sets, held to their authority.

A hand-written list is not a defect. A hand-written list with nothing that reddens when
the set it narrows grows is, and this programme has paid for that shape three times:
``D-40`` (``PC01_ERROR_CODES`` missing four codes while a screen rendered one of them),
``D-18``/``W20-CODE`` (a catalog addition that was also an unbudgeted frontend reseal),
and ``W29-SAY`` (a sentence table nearly keyed on the wrong authority).

``web/src/shared/api/run-state.ts`` is the standard these assertions are written to. Its
split is hand-written on purpose and it carries a compile-time partition proof in both
directions, so adding a state to the contract without classifying it stops the build.
Python has no equivalent, so the same claim is made here as a test.

Every assertion below is about a **relationship** -- ``⊆``, ``==``, "the difference is
exactly this" -- and never about a count. A test asserting ``len(X) == 22`` reddens on
every catalog change including the correct ones, and teaches the next session to update
the number instead of reading the change.

Each constant is named with the reason its narrowing is legitimate, so a red here is
answerable: either the narrowing moved and the constant must follow, or someone edited the
constant and should not have. Nothing in this file is the authority for anything; the
contracts under ``contracts/`` are.
"""

from __future__ import annotations


def _audit_run_states(state_machines_contract: dict) -> set[str]:
    """Every state ``machines.audit_run`` declares, from its own topology."""
    machine = state_machines_contract["machines"]["audit_run"]
    declared = {machine["initial"]}
    for origin, targets in machine["transitions"].items():
        declared.add(origin)
        declared.update(targets)
    declared.update(machine["terminal"])
    return declared


# --- runs.carrier._TERMINAL_STATES -------------------------------------------------
#
# The carrier refuses to overwrite a run that has already reached a terminal. Its set is
# written out rather than read from the topology, and deliberately so: a guard that asks
# the thing it is guarding is not one. That argument is right and it is not a reason for
# the set to be unchecked -- it is a reason for the check to live here, in a test, rather
# than in the module.


def test_the_carriers_terminal_states_are_the_machines_terminals(
    state_machines_contract: dict,
) -> None:
    from auditmanager.runs.carrier import _TERMINAL_STATES

    declared = set(state_machines_contract["machines"]["audit_run"]["terminal"])
    assert set(_TERMINAL_STATES) == declared, (
        "runs/carrier.py's _TERMINAL_STATES no longer matches "
        "contracts/domain/v1/state-machines.json machines.audit_run.terminal. A terminal "
        "the carrier does not know is a terminal it will overwrite."
    )


def test_the_carriers_terminal_states_are_audit_run_states(
    state_machines_contract: dict,
) -> None:
    """The other direction: a member that is not a state of the machine at all."""
    from auditmanager.runs.carrier import _TERMINAL_STATES

    assert set(_TERMINAL_STATES) <= _audit_run_states(state_machines_contract)


# --- findings.terminal.STAGE_STATUSES ----------------------------------------------
#
# `tests/contract/domain_p02/test_contract_vocabulary.py` already holds the *migration's*
# STAGE_STATUSES to the stage-result schema. The findings module declares a second tuple
# under the same name and nothing held it to anything; the same-name collision is exactly
# the §12 shape where a grep answers for the wrong subject.


def test_the_selectors_stage_statuses_are_the_stage_result_schemas(
    stage_result_schema: dict,
) -> None:
    from auditmanager.findings import STAGE_STATUSES

    declared = set(stage_result_schema["properties"]["status"]["enum"])
    assert set(STAGE_STATUSES) == declared, (
        "findings/terminal.py's STAGE_STATUSES no longer matches "
        "contracts/analysis/v1/stage-result.schema.json properties.status.enum. "
        "select_terminal refuses any status outside this set, so a status the schema "
        "declares and this set omits fails a run that the contract says is well-formed."
    )


# --- runs.repository.PC01_STAGES ---------------------------------------------------
#
# "Not a second registry, just the PC-01 subset of one" -- and the subset is a *prefix*:
# the four stages PC-01 drives, in the order the registry declares them. The frontend's
# PC01_STAGE_IDS is already pinned to STAGE_ID_VALUES.slice(0, 4). The backend's was not.


def test_pc01_stages_are_the_registrys_first_stages_in_its_order(
    stage_registry_contract: dict,
) -> None:
    from auditmanager.runs import PC01_STAGES

    declared = [stage["stage_id"] for stage in stage_registry_contract["stages"]]
    assert list(PC01_STAGES) == declared[: len(PC01_STAGES)], (
        "runs/repository.py's PC01_STAGES is no longer a prefix of "
        "contracts/analysis/v1/stage-registry.json's stage order. It is documented as the "
        "PC-01 subset of the registry in the registry's own depends_on order, and the "
        "executor schedules it in this order."
    )


def test_pc01_stages_are_registry_stages(stage_registry_contract: dict) -> None:
    """The narrowing direction, stated separately from the ordering one."""
    from auditmanager.runs import PC01_STAGES

    declared = {stage["stage_id"] for stage in stage_registry_contract["stages"]}
    assert set(PC01_STAGES) <= declared


def test_pc01_stages_are_a_strict_narrowing(stage_registry_contract: dict) -> None:
    """A subset assertion that a set equal to the whole registry would also satisfy is
    half a check. PC-01 drives some of the registry and not all of it."""
    from auditmanager.runs import PC01_STAGES

    declared = {stage["stage_id"] for stage in stage_registry_contract["stages"]}
    assert set(PC01_STAGES) < declared


# --- analysis.text.prompt.CATEGORIES -----------------------------------------------
#
# Not a narrowing at all: the prompt's two categories are the whole FindingCategory enum,
# and the response schema the provider is held to is built from this tuple. A third
# category in the contract that the prompt never asks for would be a category no run can
# ever produce.


def test_the_prompts_categories_are_the_finding_category_enum(
    openapi_document: dict,
) -> None:
    from auditmanager.analysis.text.prompt import CATEGORIES

    declared = openapi_document["components"]["schemas"]["FindingCategory"]["enum"]
    assert list(CATEGORIES) == list(declared), (
        "analysis/text/prompt.py's CATEGORIES no longer matches the FindingCategory enum "
        "of contracts/api/v1/openapi.json. The prompt's response schema is built from "
        "this tuple, so a category the contract declares and the prompt omits is one no "
        "run can produce."
    )


# --- bootstrap.settings._DECLARED_MODES --------------------------------------------
#
# The only *wider*-than-contract set in this file, and the width is the point. `proxy` is
# a transport and not a provenance mode: a proxied call is recorded in the run as `live`,
# per OD-02 as revised on 2026-09-14. So the relationship is not a subset in either
# direction by accident -- it is "the contract's modes, plus exactly the transport".


def test_the_declared_modes_cover_every_contract_provider_mode(
    openapi_document: dict,
) -> None:
    from auditmanager.bootstrap.settings import _DECLARED_MODES

    declared = set(openapi_document["components"]["schemas"]["ProviderMode"]["enum"])
    assert declared <= set(_DECLARED_MODES), (
        "bootstrap/settings.py refuses a provider mode the contract declares. A mode in "
        "ProviderMode that _DECLARED_MODES omits cannot be configured at all."
    )


def test_the_only_configurable_mode_outside_the_contract_is_the_proxy_transport(
    openapi_document: dict,
) -> None:
    from auditmanager.bootstrap.settings import _DECLARED_MODES

    declared = set(openapi_document["components"]["schemas"]["ProviderMode"]["enum"])
    assert set(_DECLARED_MODES) - declared == {"proxy"}, (
        "bootstrap/settings.py accepts a configured mode that the contract's "
        "ProviderMode does not declare and that is not the proxy transport. A run's "
        "recorded provider_mode must be a contract value; `proxy` is exempt only because "
        "a proxied call is recorded as `live`."
    )


# --- storage.errors.SAFE_DETAIL_KEYS ------------------------------------------------
#
# Deliberately NOT guarded here. It does not match its own stated derivation today -- it
# omits `aggregate_type`, which two of the package's own error classes declare in
# `allowed_details` and which three of the catalog codes the package raises declare as a
# safe detail key. Writing the guard would commit a red. W30-LISTS reported it instead of
# changing the set; see docs/program/W30-LISTS.md.


# --- shared.db.schema.SQLSTATE_TO_CATALOG_CODE --------------------------------------
#
# Not a subset of the catalog but a map *into* it: three custom SQLSTATEs, each named
# with the code an edge must report. Two suites already pin its domain and pin its values
# to one literal; neither says that literal is a code the catalog still declares. A code
# renamed out of the catalog would leave the edge reporting a word no client can decode,
# and `internal_mapping` in the catalog forbids exactly that -- "a code that is not in
# this catalog is never emitted and never invented at the edge".


def test_every_sqlstate_maps_to_a_code_the_catalog_declares(
    error_codes_contract: dict,
) -> None:
    from auditmanager.shared.db.schema import SQLSTATE_TO_CATALOG_CODE

    declared = set(error_codes_contract["codes"])
    reported = set(SQLSTATE_TO_CATALOG_CODE.values())
    assert reported <= declared, (
        "shared/db/schema.py maps a custom SQLSTATE to a code that is not in "
        "contracts/domain/v1/error-codes.json. The catalog's internal_mapping rule is "
        "that a code outside it is never emitted at the edge."
    )
