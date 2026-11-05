"""`EXEC2-GROUP-RUN-01`: which group revision a start is admitted on (``executors.resolver.admit_group``) and what the composition
root adds to it (``bootstrap.providers.GroupAdmission``).

The group reads (``group_summary``, ``resolve_rule``, ``group_revision_of``, ``routing_mode``) are replaced by values; the
rules under test are the resolver's own:

* a **named** group is admitted on its **current** revision in either routing mode; an unknown or malformed id is
  ``validation_failed`` on ``executor_group_id`` (``unknown_executor_group``); an archived group is ``conflict``
  (``group_archived``);
* **no selector** is admitted only while the mode is ``rules``, by the current rule of the work kind: the group revision *the
  rule names* (immutable, not the group's current one) and the rule revision; a kind with no rule is
  ``dependency_unavailable`` (``no_rule_for_work_kind``). While the mode is ``legacy`` the answer is ``None``: the start is what it
  always was;
* the admission reads and locks nothing it writes -- it writes nothing;
* ``GroupAdmission`` spells the billing as the estimate does and takes the input budget from the group's pin.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

import auditmanager.bootstrap.providers as providers
import auditmanager.executors.resolver as resolver
from auditmanager.executors.groups import GroupRecord, GroupRevisionRecord, GroupSummary, ModeState, RuleRecord
from auditmanager.shared.errors import DomainError, ErrorCode

GROUP = "exg_01M2545JSD15ETSNNV904X991G"
OTHER = "exg_01M2545JSD15ETSNNV904X992G"
CURRENT = "exgr_01M2545JSD15ETSNNV904X992R"
RULED = "exgr_01M2545JSD15ETSNNV904X991R"
RULE = "exrr_01M2545JSD15ETSNNV904X991U"
NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)
ADMIN = "usr_" + "0" * 26


def _revision(revision_id: str, group_id: str, number: int, *, billing: str = "not_metered") -> GroupRevisionRecord:
    return GroupRevisionRecord(
        group_revision_id=revision_id, group_id=group_id, revision_no=number, pin_id="claude-sonnet-5",
        gateway_model="claude-sonnet-5", billing=billing, input_per_mtok_usd=Decimal("3"),
        output_per_mtok_usd=Decimal("15"), strategy="least_loaded", created_at=NOW, created_by=ADMIN,
    )


def _summary(group_id: str, *, archived: bool = False) -> GroupSummary:
    record = GroupRecord(
        group_id=group_id, display_name="Pool", rotation_cursor=0, created_at=NOW, created_by=ADMIN,
        archived_at=NOW if archived else None, archived_by=ADMIN if archived else None)
    return GroupSummary(group=record, current_revision=_revision(CURRENT, group_id, 2))


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    state = SimpleNamespace(mode="legacy", groups={GROUP: _summary(GROUP)}, rule=None, calls=[])

    def group_summary(session: Any, group_id: str, groups: Any = None) -> GroupSummary:
        state.calls.append(("group_summary", group_id))
        if group_id not in state.groups:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorGroup")
        return state.groups[group_id]

    def routing_mode(session: Any, groups: Any = None) -> ModeState:
        state.calls.append(("routing_mode",))
        return ModeState(mode=state.mode)

    def resolve_rule(session: Any, work_kind: str, groups: Any = None) -> Any:
        state.calls.append(("resolve_rule", work_kind))
        return state.rule

    def group_revision_of(session: Any, group_revision_id: str, groups: Any = None) -> Any:
        state.calls.append(("group_revision_of", group_revision_id))
        return {RULED: _revision(RULED, OTHER, 1), CURRENT: _revision(CURRENT, GROUP, 2)}.get(group_revision_id)

    monkeypatch.setattr(resolver, "group_summary", group_summary)
    monkeypatch.setattr(resolver, "routing_mode", routing_mode)
    monkeypatch.setattr(resolver, "resolve_rule", resolve_rule)
    monkeypatch.setattr(resolver, "group_revision_of", group_revision_of)
    return state


def _refusal(call: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


# --- a named group ------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["legacy", "rules"])
def test_a_named_group_is_admitted_on_its_current_revision_in_either_mode(reads: SimpleNamespace, mode: str) -> None:
    reads.mode = mode
    admitted = resolver.admit_group(None, "text_analysis", group_id=GROUP)  # type: ignore[arg-type]
    assert admitted == resolver.AdmittedGroupRevision(
        group_id=GROUP, group_revision_id=CURRENT, pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5",
        billing="not_metered", rule_revision_id=None)
    assert ("resolve_rule", "text_analysis") not in reads.calls, "naming the group is the selector: the rules are not read"


@pytest.mark.parametrize("bad", [OTHER, "not-an-id", "exg_", "exc_01M2545JSD15ETSNNV904X991G", ""])
def test_an_unknown_or_malformed_group_is_validation_failed_on_the_field(reads: SimpleNamespace, bad: str) -> None:
    error = _refusal(lambda: resolver.admit_group(None, "text_analysis", group_id=bad))  # type: ignore[arg-type]
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert dict(error.detail_fields) == {"field": "executor_group_id", "constraint": "unknown_executor_group"}
    assert not bad or bad not in str(error), "the refusal echoes no value"


def test_an_archived_group_is_a_conflict_with_its_reason(reads: SimpleNamespace) -> None:
    reads.groups[GROUP] = _summary(GROUP, archived=True)
    error = _refusal(lambda: resolver.admit_group(None, "text_analysis", group_id=GROUP))  # type: ignore[arg-type]
    assert error.code is ErrorCode.CONFLICT and dict(error.detail_fields) == {
        "conflict_reason": "group_archived", "aggregate_type": "ExecutorGroup",
    }


# --- no selector ----------------------------------------------------------------------------------------------------------


def test_with_no_selector_and_the_mode_legacy_the_start_is_not_admitted_and_no_rule_is_read(reads: SimpleNamespace) -> None:
    assert resolver.admit_group(None, "text_analysis") is None  # type: ignore[arg-type]
    assert reads.calls == [("routing_mode",)]


def test_with_no_selector_and_the_mode_rules_the_rule_names_the_revision_and_is_recorded(reads: SimpleNamespace) -> None:
    reads.mode = "rules"
    reads.rule = RuleRecord(
        rule_revision_id=RULE, work_kind="text_analysis", rule_no=3, group_revision_id=RULED, group_id=OTHER,
        set_at=NOW, set_by=ADMIN)
    admitted = resolver.admit_group(None, "text_analysis")  # type: ignore[arg-type]
    assert (admitted.group_id, admitted.group_revision_id, admitted.rule_revision_id) == (OTHER, RULED, RULE), (
        "the immutable revision the rule names, not the group's current one")


def test_a_work_kind_without_a_rule_is_refused_and_does_not_fall_back_to_the_route(reads: SimpleNamespace) -> None:
    reads.mode = "rules"
    error = _refusal(lambda: resolver.admit_group(None, "text_analysis"))  # type: ignore[arg-type]
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(error.detail_fields) == {"dependency": "no_rule_for_work_kind"}


def test_the_group_of_a_revision_is_read_back_for_a_repeat(reads: SimpleNamespace) -> None:
    assert resolver.group_of_revision(None, CURRENT) == GROUP  # type: ignore[arg-type]
    assert resolver.group_of_revision(None, "exgr_NOWHERE") is None  # type: ignore[arg-type]


# --- the composition root's wrapper ------------------------------------------------------------------------------------------


def test_the_database_source_spells_billing_as_the_estimate_does_and_takes_the_budget_from_the_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[tuple[str, float]] = []

    def budget(pin_id: str, ceiling: float) -> int:
        asked.append((pin_id, ceiling))
        return 123_456

    monkeypatch.setattr(providers, "input_budget_characters", budget)
    for billing, spelled in (("not_metered", "unmetered"), ("metered", "metered")):
        monkeypatch.setattr(providers, "admit_group", lambda session, kind, group_id=None, _b=billing: (
            resolver.AdmittedGroupRevision(
                group_id=GROUP, group_revision_id=CURRENT, pin_id="claude-sonnet-5",
                gateway_model="claude-sonnet-5", billing=_b)))
        admitted = providers.GroupAdmission(ceiling_usd=2.5)(None, group_id=GROUP)  # type: ignore[arg-type]
        assert admitted is not None
        assert (admitted.billing, admitted.input_budget_characters, admitted.group_revision_id) == (
            spelled, 123_456, CURRENT)
        assert admitted.rule_revision_id is None
    assert asked == [("claude-sonnet-5", 2.5)] * 2


def test_the_database_source_passes_a_legacy_none_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(providers, "admit_group", lambda session, kind, group_id=None: None)
    assert providers.GroupAdmission(ceiling_usd=1.0)(None) is None  # type: ignore[arg-type]


def test_only_the_database_source_has_an_admitter() -> None:
    environment = providers.EnvironmentProviders(SimpleNamespace(), SimpleNamespace())
    database = providers.DatabaseProviders(
        ring=None, policy=None, base_config=SimpleNamespace(), ceiling_usd=1.0)  # type: ignore[arg-type]
    assert environment.admit_group is None and environment.freeze is None
    assert isinstance(database.admit_group, providers.GroupAdmission) and database.freeze is not None
