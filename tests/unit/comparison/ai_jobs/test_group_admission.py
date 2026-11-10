"""`EXEC2-GROUP-CMP-01` (ADR-0026 decisions 12, 13, 15 and 17): admission of a comparison AI job by a rule or a group, container-free.

Written and **not run** in EXEC-2 (`R-149d`, D-292). It holds, with the executors' reads stood in for:

* the route of a work kind by the routing mode: ``legacy`` is the primary as it always was; ``rules`` is the group revision of the work
  kind's current rule -- its ``pin_id``, its rate snapshot and its billing, with no connection -- and a kind with no rule is the typed
  refusal ``dependency_unavailable`` / ``no_rule_for_work_kind`` that never falls back to the legacy route;
* the estimate of a start under ``rules`` priced at the **group revision's** rate snapshot, and the digest that binds the group;
* a job that is already admitted by a group re-estimated on **its own** group revision whatever the rule says now, a job made before the
  cut-over re-estimated through the legacy route, and the model a method reads while it counts being the job's;
* the read models: ``binding_state``, ``planned``, ``binding``, ``wait_reason`` and ``waiting_since`` on ``ComparisonAiJob``, ``binding_state``
  and ``wait_reason`` on ``ComparisonAiQueueItem``, the group plan on ``ComparisonAiRoute`` -- each document valid against the generated
  models, and the document of a job made before the cut-over unchanged;
* the job layer's answer to ``no_executor_online`` (the job ends ``failed``) and to a consent that does not hold (the reconsent pause).

The statements that really write the new columns, and the database's refusal of every other write of them, are
``tests/integration/comparison/test_group_binding.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin
from auditmanager.api.schemas import models
from auditmanager.comparison.ai_jobs import estimate as estimate_module
from auditmanager.comparison.ai_jobs.model import (
    AiCallGroup,
    AiCounts,
    AiJobRecord,
    AiJobSpend,
    AiJobView,
    AiMode,
    AiProgress,
    AiRoute,
    AiScope,
)
from auditmanager.comparison.ai_jobs.repository import _BIND, _MOVE, _RENEW_CONSENT, _SET_WAIT, AiJobRepository
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.spend.model import Spend
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    ComparisonAiJobId,
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ExecutorGroupId,
    ExecutorGroupRevisionId,
    ExecutorRoutingRuleRevisionId,
    ProjectUid,
)
from auditmanager.shared.identity.ids import UserUid

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
SHA = "ab" * 32
OPUS, SONNET = "claude-opus-5", "claude-sonnet-5"
GROUP, GROUP_NEW = str(ExecutorGroupId.new()), str(ExecutorGroupId.new())
REVISION, REVISION_NEW = str(ExecutorGroupRevisionId.new()), str(ExecutorGroupRevisionId.new())
RULE, RULE_NEW = str(ExecutorRoutingRuleRevisionId.new()), str(ExecutorRoutingRuleRevisionId.new())
CONNECTION, CONNECTION_REVISION = str(ExecutorConnectionId.new()), str(ExecutorConnectionRevisionId.new())
PROJECT, DOCUMENT, USER = str(ProjectUid.new()), str(DocumentUid.new()), str(UserUid.new())
WORK_KIND = "comparison_pair_check"


def counts(calls: int = 10) -> AiCounts:
    return AiCounts(groups=(AiCallGroup(calls=calls, prompt_chars=4000, output_tokens=1000, images=2, image_bytes=200_000),), units=calls)


def scope() -> AiScope:
    return AiScope(method="pair_check", project_uid=PROJECT, document_uid=DOCUMENT, matrix_id="cmx_" + "1" * 26)


def revision(identity: str = REVISION, *, group: str = GROUP, pin: str = OPUS, billing: str = "metered",
             rates: tuple[str, str] = ("2.0", "10.0")) -> SimpleNamespace:
    return SimpleNamespace(
        group_revision_id=identity, group_id=group, revision_no=1, pin_id=pin, gateway_model=f"anthropic/{pin}", billing=billing,
        input_per_mtok_usd=Decimal(rates[0]), output_per_mtok_usd=Decimal(rates[1]), strategy="least_loaded", members=(),
    )


class Executors:
    """The executors' public reads, as one scenario sets them."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, mode: str = "rules", rule: str | None = RULE_NEW,
                 rule_revision: str = REVISION_NEW) -> None:
        from auditmanager.executors import public
        from auditmanager.runs import public as runs

        self.mode, self.rule, self.rule_revision = mode, rule, rule_revision
        #: The stage layout is off here (`HOSTS-CMP-01`): ``read_route`` asks the switch first and these scenarios are the routes of the two modes.
        monkeypatch.setattr(runs, "SqlStageLayoutStore", lambda: SimpleNamespace(enabled=lambda session: False))
        self.revisions = {REVISION: revision(REVISION, group=GROUP, pin=OPUS), REVISION_NEW: revision(REVISION_NEW, group=GROUP_NEW, pin=SONNET)}
        #: The provider lock as these scenarios read it: the rates the revisions above snapshotted (a group is made at the lock's rates).
        #: A test moves a model's rates to show a snapshot that is no longer the lock's.
        self.lock: dict[str, tuple[float, float]] = {OPUS: (2.0, 10.0), SONNET: (2.0, 10.0)}
        self.legacy_reads = 0
        monkeypatch.setattr(public, "pinned_models", lambda: tuple(ModelPin(model, *rates) for model, rates in self.lock.items()))
        monkeypatch.setattr(public, "routing_mode", lambda session, groups=None: SimpleNamespace(mode=self.mode))
        monkeypatch.setattr(public, "resolve_rule", self._rule)
        monkeypatch.setattr(public, "group_revision_of", lambda session, identity, groups=None: self.revisions.get(identity))
        monkeypatch.setattr(public, "resolve_route", self._legacy)

    def _rule(self, session: Any, work_kind: str, groups: Any = None) -> Any:
        if self.rule is None:
            return None
        named = self.revisions.get(self.rule_revision)  # a rule may name a revision that is gone: then there is no group to read
        return SimpleNamespace(rule_revision_id=self.rule, work_kind=work_kind, rule_no=1, group_revision_id=self.rule_revision,
                               group_id=named.group_id if named is not None else GROUP_NEW)

    def _legacy(self, session: Any, work_kind: str, repository: Any = None) -> Any:
        self.legacy_reads += 1
        settings = SimpleNamespace(pin_id=OPUS, gateway_model=f"anthropic/{OPUS}", billing="metered")
        return SimpleNamespace(primary=SimpleNamespace(connection_id=CONNECTION, revision_id=CONNECTION_REVISION, settings=settings))


class CountingMethod:
    """Counts as a real method does: it learns the model from ``read_route`` -- the model its stored answers are keyed by."""

    method = "pair_check"
    prompt_version = "p1"

    def __init__(self, *, fail: bool = False) -> None:
        self.models: list[str] = []
        self.fail = fail

    def counts(self, session: Any, request: Any) -> AiCounts:
        self.models.append(estimate_module.read_route(session, WORK_KIND, "live").pinned_model)
        if self.fail:
            raise RuntimeError("the method broke while counting")
        return counts()

    def work_items(self, session: Any, job: Any, mode: Any) -> list[Any]:
        return []


class FakeRepository:
    def __init__(self, record: AiJobRecord | None = None) -> None:
        self.record, self.moves = record, []

    def get(self, session: Any, job_id: str, *, lock: bool = False) -> AiJobRecord | None:
        return self.record

    def spend(self, session: Any, job_id: str) -> AiJobSpend:
        return AiJobSpend(spent_micros=0, reserved_micros=0, calls=0, unknown_calls=0, input_tokens=0, output_tokens=0)

    def items(self, session: Any, job_id: str) -> list[Any]:
        return []

    def move(self, session: Any, job_id: str, *, from_states: Any, to_state: str, pause_reason: str | None = None,
             failure_reason: str | None = None) -> bool:
        self.moves.append((to_state, pause_reason, failure_reason))
        return True


class FakeSpend:
    def day_spend(self, session: Any) -> Spend:
        return Spend(0, 0)


def service(method: CountingMethod, record: AiJobRecord | None = None, **over: Any) -> ComparisonAiJobService:
    return ComparisonAiJobService(
        None, methods=[method], comparison_modules="versions", provider_mode="live",  # type: ignore[arg-type]
        repository=FakeRepository(record), spend=FakeSpend(), **over,  # type: ignore[arg-type]
    )


def session() -> Any:
    return SimpleNamespace(info={})


def record(**over: Any) -> AiJobRecord:
    """A pending job admitted on ``REVISION`` (opus) by the rule ``RULE``."""
    values: dict[str, Any] = {
        "job_id": str(ComparisonAiJobId.new()), "project_uid": PROJECT, "document_uid": DOCUMENT, "method": "pair_check",
        "state": "running", "pause_reason": None, "failure_reason": None, "matrix_id": "cmx_" + "1" * 26, "series_id": None,
        "transition_id": None, "sheet_pair_id": None, "restart": False, "connection_revision_id": None, "pinned_model": OPUS,
        "provider_mode": "live", "estimate": {}, "estimate_digest": SHA, "estimate_micros": 0, "ceiling_micros": 10_000_000,
        "consent_no": 1, "consented_by_user_uid": USER, "consented_at": NOW, "command_id": "cmd_" + "1" * 26,
        "created_at": NOW, "updated_at": NOW, "finished_at": None, "binding_state": "pending",
        "executor_group_revision_id": REVISION, "routing_rule_revision_id": RULE,
    }
    values.update(over)
    return AiJobRecord(**values)


def frozen(**over: Any) -> AiJobRecord:
    return record(binding_state="frozen_at_start", connection_revision_id=CONNECTION_REVISION, executor_group_revision_id=None,
                  routing_rule_revision_id=None, **over)


# --- the route of a work kind, by the routing mode (decisions 13 and 17) ---------------------------------------------------------


def test_under_rules_the_route_is_the_group_revision_of_the_current_rule_with_no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    Executors(monkeypatch)
    route = estimate_module.read_route(session(), WORK_KIND, "live")
    assert route.grouped and (route.connection_id, route.revision_id) == (None, None)
    assert (route.executor_group_id, route.executor_group_revision_id, route.routing_rule_revision_id) == (GROUP_NEW, REVISION_NEW, RULE_NEW)
    assert (route.pinned_model, route.gateway_model, route.billing) == (SONNET, f"anthropic/{SONNET}", "metered")
    assert route.metered and route.work_kind == WORK_KIND and route.provider_mode == "live"


def test_the_route_prices_at_the_rate_snapshot_of_the_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    executors = Executors(monkeypatch)
    executors.revisions[REVISION_NEW] = revision(REVISION_NEW, group=GROUP_NEW, pin=SONNET, rates=("0.5", "1.5"))
    executors.lock[SONNET] = (0.5, 1.5)
    route = estimate_module.read_route(session(), WORK_KIND, "live")
    assert (route.pin.model_id, route.pin.input_per_mtok_usd, route.pin.output_per_mtok_usd) == (SONNET, 0.5, 1.5)


# --- a snapshot that is not the lock's: refused by an explicit seam, only where the operation declares 422 (`EXEC2-FOLLOWUP-01`, M2, N1) ---


def stale_rates(executors: "Executors") -> None:
    """The lock moved after the group revision was made: the revision still holds 2.0 / 10.0, the lock now prices the model at 2.5 / 10.0."""
    executors.lock[SONNET] = (2.5, 10.0)
    executors.lock[OPUS] = (2.5, 10.0)


def assert_rates_stale(refused: pytest.ExceptionInfo[DomainError]) -> None:
    error = refused.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields == {"stage_id": WORK_KIND, "reason": "cost_estimate_binding_changed"}
    assert error.envelope("corr_01").details == error.detail_fields, "the catalogue lets this code carry exactly these two keys"


def test_the_estimate_is_computed_at_the_groups_snapshot_even_when_the_lock_moved_and_the_start_is_what_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N1: the estimate operations of a pair check, a sheet description and a specification declare no 422, so the estimate they serve is the
    one it was before the rates check existed -- priced at the snapshot -- and a job that is resumed is estimated the same way."""
    executors = Executors(monkeypatch)
    stale_rates(executors)
    method = CountingMethod()
    estimate = service(method).estimate_in(session(), scope())
    assert estimate.route.grouped and (estimate.route.pin.input_per_mtok_usd, estimate.route.pin.output_per_mtok_usd) == (2.0, 10.0)
    assert method.models == [SONNET], "the method counted: nothing refused the estimate"
    left = service(CountingMethod()).estimate_in(session(), scope(), AiMode.LEFT, job=record())
    assert left.route.executor_group_revision_id == REVISION


def test_the_route_readers_never_refuse_for_stale_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    """``read_route`` is read by every method while it counts, queues its items and names its model -- by a ``finish`` among others, which
    declares no 422. It must answer."""
    executors = Executors(monkeypatch)
    stale_rates(executors)
    assert estimate_module.read_route(session(), WORK_KIND, "live").grouped
    assert estimate_module.read_job_route(session(), record(), "live").grouped
    assert estimate_module.read_rule_route(session(), WORK_KIND, "live").grouped


def test_a_lock_that_no_longer_pins_the_model_still_answers_executor_route_missing_from_the_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    executors = Executors(monkeypatch)
    del executors.lock[SONNET]
    with pytest.raises(DomainError) as refused:
        estimate_module.read_route(session(), WORK_KIND, "live")
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and refused.value.detail_fields["dependency"] == "executor_route_missing"


def group_route_of(executors: "Executors", identity: str = REVISION_NEW) -> AiRoute:
    return estimate_module.read_route(session(), WORK_KIND, "live") if identity == REVISION_NEW else estimate_module.read_job_route(
        session(), record(), "live")


def test_the_seam_refuses_a_group_route_whose_snapshot_is_not_the_locks_with_the_registered_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    executors = Executors(monkeypatch)
    route = group_route_of(executors)
    estimate_module.require_group_rates_hold(session(), route)  # as made: the rates hold
    stale_rates(executors)
    with pytest.raises(DomainError) as refused:
        estimate_module.require_group_rates_hold(session(), route)
    assert_rates_stale(refused)
    with pytest.raises(DomainError) as job_refused:
        estimate_module.require_group_rates_hold(session(), group_route_of(executors, REVISION))
    assert_rates_stale(job_refused)


def test_the_seam_checks_the_pin_first_so_a_lock_that_stopped_pinning_the_model_is_executor_route_missing_not_stale_rates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N2: with no pin there are no rates to compare. The unusable route is what is said, and it is said before the rates are looked at."""
    executors = Executors(monkeypatch)
    route = group_route_of(executors)
    del executors.lock[SONNET]
    with pytest.raises(DomainError) as refused:
        estimate_module.require_group_rates_hold(session(), route)
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.detail_fields["dependency"] == "executor_route_missing"


def test_the_seam_asks_nothing_of_a_route_that_names_a_connection_and_a_revision_that_is_gone_is_a_missing_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executors = Executors(monkeypatch)
    from auditmanager.executors import public

    stale_rates(executors)
    monkeypatch.setattr(public, "group_revision_of", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a connection route reads no group")))
    estimate_module.require_group_rates_hold(session(), legacy_route())
    monkeypatch.setattr(public, "group_revision_of", lambda session, identity, groups=None: None)
    with pytest.raises(DomainError) as refused:
        estimate_module.require_group_rates_hold(session(), grouped_route())
    assert refused.value.detail_fields["dependency"] == "executor_route_missing"


def test_the_refusal_is_the_registered_cost_binding_reason_the_run_path_raises_too() -> None:
    from auditmanager.jobs.repository import CONSENT_LAPSED_REASON

    assert estimate_module.REASON_RATES_STALE == CONSENT_LAPSED_REASON == "cost_estimate_binding_changed"


def test_under_legacy_the_route_is_the_primary_exactly_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    executors = Executors(monkeypatch, mode="legacy")
    route = estimate_module.read_route(session(), WORK_KIND, "live")
    assert not route.grouped and (route.connection_id, route.revision_id) == (CONNECTION, CONNECTION_REVISION)
    assert (route.executor_group_id, route.executor_group_revision_id, route.routing_rule_revision_id) == (None, None, None)
    assert route.as_document() == {
        "connection_id": CONNECTION, "revision_id": CONNECTION_REVISION, "pinned_model": OPUS, "billing": "metered",
        "provider_mode": "live",
    }, "the document of a route with no group is the document it always was: no new key, so no new digest"
    assert executors.legacy_reads == 1


def test_a_work_kind_with_no_rule_under_rules_is_a_typed_refusal_and_never_a_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    executors = Executors(monkeypatch, rule=None)
    with pytest.raises(DomainError) as refused:
        estimate_module.read_route(session(), WORK_KIND, "live")
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.detail_fields["dependency"] == "no_rule_for_work_kind"
    assert executors.legacy_reads == 0, "the legacy route is not consulted under rules"


def test_a_rule_that_names_a_group_revision_that_is_gone_is_executor_route_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    Executors(monkeypatch, rule_revision=str(ExecutorGroupRevisionId.new()))
    with pytest.raises(DomainError) as refused:
        estimate_module.read_route(session(), WORK_KIND, "live")
    assert refused.value.detail_fields["dependency"] == "executor_route_missing"


# --- the shape of a route ------------------------------------------------------------------------------------------------------------


def grouped_route(**over: Any) -> AiRoute:
    values: dict[str, Any] = {
        "work_kind": WORK_KIND, "connection_id": None, "revision_id": None, "pinned_model": OPUS,
        "gateway_model": f"anthropic/{OPUS}", "billing": "metered", "provider_mode": "live",
        "pin": ModelPin(OPUS, 2.0, 10.0), "executor_group_id": GROUP, "executor_group_revision_id": REVISION,
        "routing_rule_revision_id": RULE,
    }
    values.update(over)
    return AiRoute(**values)


def test_a_group_route_names_the_group_and_no_connection() -> None:
    assert grouped_route().as_document() == {
        "pinned_model": OPUS, "billing": "metered", "provider_mode": "live", "executor_group_id": GROUP,
        "executor_group_revision_id": REVISION, "routing_rule_revision_id": RULE,
    }
    assert "routing_rule_revision_id" not in grouped_route(routing_rule_revision_id=None).as_document(), "a group named explicitly has no rule"


@pytest.mark.parametrize("over", [
    {"connection_id": CONNECTION},                    # a group route with a connection
    {"revision_id": CONNECTION_REVISION},
    {"executor_group_id": None},                      # a group revision without its group
])
def test_a_group_route_with_a_connection_or_without_its_group_is_refused(over: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        grouped_route(**over)


def legacy_route(**over: Any) -> AiRoute:
    values: dict[str, Any] = {
        "work_kind": WORK_KIND, "connection_id": CONNECTION, "revision_id": CONNECTION_REVISION, "pinned_model": OPUS,
        "gateway_model": f"anthropic/{OPUS}", "billing": "metered", "provider_mode": "live", "pin": ModelPin(OPUS, 2.0, 10.0),
    }
    values.update(over)
    return AiRoute(**values)


@pytest.mark.parametrize("over", [
    {"connection_id": None}, {"revision_id": None}, {"executor_group_id": GROUP}, {"routing_rule_revision_id": RULE},
])
def test_a_route_with_no_group_revision_names_its_connection_and_no_group_or_rule(over: dict[str, Any]) -> None:
    legacy_route()
    with pytest.raises(ValueError):
        legacy_route(**over)


def test_the_digest_binds_the_group_the_revision_and_the_rule() -> None:
    from auditmanager.comparison.public import build_ai_estimate

    def digest(route: AiRoute) -> str:
        return build_ai_estimate(
            scope=scope(), mode=AiMode.START, prompt_version="p1", counts=counts(), route=route,
        ).estimate_digest

    base = digest(grouped_route())
    assert base == digest(grouped_route())
    for change in ({"executor_group_id": GROUP_NEW}, {"executor_group_revision_id": REVISION_NEW}, {"routing_rule_revision_id": RULE_NEW},
                   {"routing_rule_revision_id": None}):
        assert digest(grouped_route(**change)) != base, change


def test_the_estimate_of_a_group_route_prices_at_its_pin_and_is_not_metered_at_zero() -> None:
    from auditmanager.comparison.public import build_ai_estimate

    totals = counts().totals()
    expected = -(-(totals.input_tokens * 2_000_000 + totals.output_tokens * 10_000_000) // 1_000_000)
    priced = build_ai_estimate(scope=scope(), mode=AiMode.START, prompt_version="p1", counts=counts(), route=grouped_route())
    assert priced.estimate_micros == expected and priced.ceiling_micros == 10_000_000 and priced.blocked_by is None
    free = build_ai_estimate(
        scope=scope(), mode=AiMode.START, prompt_version="p1", counts=counts(), route=grouped_route(billing="not_metered"),
    )
    assert (free.estimate_micros, free.ceiling_micros, free.day_remaining_micros, free.blocked_by) == (0, 0, None, None)


# --- the estimate of a start and of a job (decisions 13 and 17) ------------------------------------------------------------------


def test_a_start_under_rules_is_estimated_on_the_current_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    Executors(monkeypatch)
    method = CountingMethod()
    estimate = service(method).estimate_in(session(), scope())
    assert estimate.route.executor_group_revision_id == REVISION_NEW and estimate.route.pinned_model == SONNET
    assert method.models == [SONNET]
    document = estimate.as_dict()
    assert document["route"] == estimate.route.as_document() and "connection_id" not in document["route"]
    models.ComparisonAiEstimate.model_validate(document)


def test_a_job_admitted_by_a_group_is_estimated_on_its_own_revision_whatever_the_rule_says_now(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule now names another group of another model; the job was admitted on opus and finishes on opus -- for the price and for
    the model its method keys the stored answers by."""
    Executors(monkeypatch)
    method, current = CountingMethod(), session()
    estimate = service(method).estimate_in(current, scope(), AiMode.LEFT, job=record())
    assert (estimate.route.executor_group_revision_id, estimate.route.routing_rule_revision_id, estimate.route.pinned_model) == (REVISION, RULE, OPUS)
    assert method.models == [OPUS]
    assert estimate_module.JOB_ROUTE_KEY not in current.info, "the job's route answers only while its method counts"


def test_a_job_made_before_the_cut_over_is_estimated_through_the_legacy_route_even_under_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    executors = Executors(monkeypatch)
    method = CountingMethod()
    estimate = service(method).estimate_in(session(), scope(), AiMode.LEFT, job=frozen())
    assert not estimate.route.grouped and estimate.route.revision_id == CONNECTION_REVISION
    assert method.models == [OPUS] and executors.legacy_reads == 1, "the method's own read is answered by the same legacy route"


def test_the_job_route_is_put_back_when_the_method_breaks(monkeypatch: pytest.MonkeyPatch) -> None:
    Executors(monkeypatch)
    current = session()
    current.info[estimate_module.JOB_ROUTE_KEY] = "outer"
    with pytest.raises(RuntimeError):
        service(CountingMethod(fail=True)).estimate_in(current, scope(), AiMode.LEFT, job=record())
    assert current.info[estimate_module.JOB_ROUTE_KEY] == "outer"
    clean = session()
    with pytest.raises(RuntimeError):
        service(CountingMethod(fail=True)).estimate_in(clean, scope(), AiMode.LEFT, job=record())
    assert estimate_module.JOB_ROUTE_KEY not in clean.info


def test_an_injected_route_reader_serves_a_start_and_a_job_alike(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test (or a lane) that hands the service its own reader gets it for every estimate, as before."""
    Executors(monkeypatch)
    seen: list[str] = []

    def reader(current: Any, work_kind: str, provider_mode: str) -> AiRoute:
        seen.append(work_kind)
        return grouped_route(executor_group_revision_id=REVISION_NEW, executor_group_id=GROUP_NEW)

    method = CountingMethod()
    chosen = service(method, route_reader=reader)
    chosen.estimate_in(session(), scope())
    chosen.estimate_in(session(), scope(), AiMode.LEFT, job=record())
    assert seen == [WORK_KIND, WORK_KIND]


# --- the read models (decisions 12, 13 and 15) -----------------------------------------------------------------------------------


def estimate_document(route: AiRoute | None = None) -> dict[str, Any]:
    from auditmanager.comparison.public import build_ai_estimate

    return build_ai_estimate(
        scope=scope(), mode=AiMode.START, prompt_version="p1", counts=counts(), route=route or grouped_route(),
    ).as_dict(with_state=False)


def view(job: AiJobRecord, **over: Any) -> AiJobView:
    return AiJobView(
        record=job, progress=AiProgress(total=3, done=1, failed=0, unknown=0, by_state={}),
        spend=AiJobSpend(spent_micros=0, reserved_micros=0, calls=0, unknown_calls=0, input_tokens=0, output_tokens=0), **over,
    )


PLANNED = {
    "executor_group_id": GROUP, "executor_group_revision_id": REVISION, "routing_rule_revision_id": RULE,
    "pin_id": OPUS, "gateway_model": f"anthropic/{OPUS}", "billing": "metered",
}


def test_the_document_of_a_job_made_before_the_cut_over_is_the_document_it_always_was() -> None:
    legacy = view(frozen(estimate=estimate_document(legacy_route())))
    document = legacy.as_dict()
    for absent in ("binding_state", "planned", "binding", "wait_reason", "waiting_since"):
        assert absent not in document, absent
    assert "binding_state" not in legacy.as_queue_item() and "wait_reason" not in legacy.as_queue_item()
    parsed = models.ComparisonAiJob.model_validate(document)
    assert parsed.binding_state is None and parsed.planned is None and parsed.binding is None


def test_a_pending_job_shows_its_plan_and_why_it_waits() -> None:
    waiting = view(
        record(estimate=estimate_document(), wait_reason="executor_at_capacity", waiting_since=NOW), planned=PLANNED,
    )
    document = waiting.as_dict()
    assert document["binding_state"] == "pending" and document["planned"] == PLANNED and "binding" not in document
    assert (document["wait_reason"], document["waiting_since"]) == ("executor_at_capacity", NOW)
    parsed = models.ComparisonAiJob.model_validate(document)
    assert parsed.binding_state.value == "pending" and parsed.wait_reason.value == "executor_at_capacity"
    assert parsed.estimate.route.connection_id is None and str(parsed.estimate.route.executor_group_revision_id) == REVISION
    queued = waiting.as_queue_item()
    assert (queued["binding_state"], queued["wait_reason"]) == ("pending", "executor_at_capacity")
    models.ComparisonAiQueueItem.model_validate(queued)


def test_a_job_that_needs_a_new_consent_says_so_in_the_waiting_word() -> None:
    paused = view(
        record(estimate=estimate_document(), state="paused", pause_reason="route_changed", wait_reason="needs_reconsent", waiting_since=NOW),
        planned=PLANNED,
    )
    parsed = models.ComparisonAiJob.model_validate(paused.as_dict())
    assert (parsed.state.value, parsed.pause_reason.value, parsed.wait_reason.value) == ("paused", "route_changed", "needs_reconsent")


def test_a_bound_job_shows_the_member_it_is_on_and_no_longer_waits() -> None:
    binding = {
        "connection_id": CONNECTION, "connection_revision_id": CONNECTION_REVISION, "display_name": "Sonnet pool 1",
        "pin_id": OPUS, "gateway_model": f"anthropic/{OPUS}",
    }
    bound = view(record(estimate=estimate_document(), binding_state="bound", connection_revision_id=CONNECTION_REVISION),
                 planned=PLANNED, binding=binding)
    document = bound.as_dict()
    assert document["binding_state"] == "bound" and document["binding"] == binding and "wait_reason" not in document
    parsed = models.ComparisonAiJob.model_validate(document)
    assert parsed.binding.display_name == "Sonnet pool 1" and parsed.binding_state.value == "bound"
    models.ComparisonAiQueueItem.model_validate(bound.as_queue_item())


def test_the_plan_and_the_binding_are_read_from_the_executors_public_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.executors import public

    Executors(monkeypatch)
    monkeypatch.setattr(public, "executor_of_revision", lambda current, identity, repository=None: SimpleNamespace(
        connection_id=CONNECTION, display_name="Sonnet pool 1", pin_id=OPUS))
    views = ComparisonAiJobService._group_views  # noqa: SLF001
    assert views(session(), frozen()) == (None, None)
    planned, binding = views(session(), record())
    assert planned == PLANNED and binding is None
    planned, binding = views(session(), record(binding_state="bound", connection_revision_id=CONNECTION_REVISION))
    assert planned == PLANNED and binding == {
        "connection_id": CONNECTION, "connection_revision_id": CONNECTION_REVISION, "display_name": "Sonnet pool 1",
        "pin_id": OPUS, "gateway_model": f"anthropic/{OPUS}",
    }
    planned, _ = views(session(), record(routing_rule_revision_id=None))
    assert "routing_rule_revision_id" not in planned, "a group named explicitly has no rule"


# --- the job layer's answers to the spend wrapper (decisions 14 and 15) ----------------------------------------------------------


def test_no_executor_online_ends_the_job_through_its_own_failure_path() -> None:
    repository = FakeRepository(record(state="running"))
    ended = ComparisonAiJobService(
        None, methods=[], comparison_modules="versions", repository=repository, spend=FakeSpend(),  # type: ignore[arg-type]
    ).pause_for_spend(session(), "job", "no_executor_online")
    assert ended is True and repository.moves == [("failed", None, "no_executor_online")]


def test_a_consent_that_does_not_hold_pauses_the_job_for_reconsent_and_ends_nothing() -> None:
    repository = FakeRepository(record(state="running"))
    paused = ComparisonAiJobService(
        None, methods=[], comparison_modules="versions", repository=repository, spend=FakeSpend(),  # type: ignore[arg-type]
    ).pause_for_spend(session(), "job", "consent_stale")
    assert paused is True and repository.moves == [("paused", "route_changed", None)]


def test_the_consent_of_a_pending_job_names_the_group_revision_and_no_connection() -> None:
    consent = ComparisonAiJobService(
        None, methods=[], comparison_modules="versions", repository=FakeRepository(record()), spend=FakeSpend(),  # type: ignore[arg-type]
    ).consent_for_calls(session(), "job")
    assert consent.connection_revision_id is None and consent.executor_group_revision_id == REVISION
    assert consent.pinned_model == OPUS
    bound = ComparisonAiJobService(
        None, methods=[], comparison_modules="versions",  # type: ignore[arg-type]
        repository=FakeRepository(record(binding_state="bound", connection_revision_id=CONNECTION_REVISION)), spend=FakeSpend(),  # type: ignore[arg-type]
    ).consent_for_calls(session(), "job")
    assert (bound.connection_revision_id, bound.executor_group_revision_id) == (CONNECTION_REVISION, REVISION)


# --- the statements (decisions 12 and 16) ---------------------------------------------------------------------------------------------


def test_a_renewed_consent_never_writes_the_connection_revision_of_a_group_job_and_ends_its_wait() -> None:
    sql = str(_RENEW_CONSENT)
    assert "connection_revision_id = COALESCE(:revision_id, connection_revision_id)" in sql
    assert "wait_reason = NULL" in sql and "waiting_since = NULL" in sql
    assert "executor_group_revision_id" not in sql and "routing_rule_revision_id" not in sql, "what admission froze is not rewritten"


def test_the_binding_statement_writes_the_revision_once_from_pending_and_touches_no_consent_column() -> None:
    sql = str(_BIND)
    assert "binding_state = 'bound'" in sql and "connection_revision_id = :revision_id" in sql
    assert "binding_state = 'pending'" in sql, "the guard of the statement: only a pending job is bound"
    for consent_column in ("estimate", "estimate_digest", "estimate_micros", "ceiling_micros", "pinned_model", "provider_mode",
                           "consented_by_user_uid", "consent_no"):
        assert f"{consent_column} =" not in sql, consent_column


def test_the_wait_statement_restarts_the_clock_only_when_the_reason_changes() -> None:
    sql = str(_SET_WAIT)
    assert "WHEN wait_reason IS NOT DISTINCT FROM :reason THEN waiting_since ELSE clock_timestamp()" in sql
    assert "binding_state = 'pending'" in sql and "RETURNING" in sql


def test_only_a_live_job_is_given_a_wait() -> None:
    """The twin of the Run's ``_WRITE_WAIT`` (``state = 'queued'``): a cancelled or failed job is never given a wait."""
    sql = str(_SET_WAIT)
    assert "AND state IN ('queued', 'running', 'paused')" in sql, "queued, running or paused (a pause keeps its wait)"
    for ended in ("completed", "failed", "cancelled"):
        assert ended not in sql
    assert sql.index("binding_state = 'pending'") < sql.index("state IN ('queued', 'running', 'paused')") < sql.index("RETURNING")
    # the same three states are what the repository calls live everywhere else
    from auditmanager.comparison.ai_jobs.model import JOB_STATES, JOB_TERMINAL_STATES
    assert set(JOB_STATES) - set(JOB_TERMINAL_STATES) == {"queued", "running", "paused"}


def test_a_job_that_ends_stops_waiting() -> None:
    sql = str(_MOVE)
    assert "wait_reason = CASE WHEN :terminal THEN NULL ELSE wait_reason END" in sql
    assert "waiting_since = CASE WHEN :terminal THEN NULL ELSE waiting_since END" in sql


def test_a_wait_reason_is_one_of_the_contracts_three() -> None:
    with pytest.raises(ValueError):
        AiJobRepository().set_wait(None, "job", "waiting_for_something")  # type: ignore[arg-type]


def test_a_job_made_before_the_cut_over_is_inserted_frozen_and_a_group_job_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.comparison.public import build_ai_estimate

    class Capture:
        def __init__(self) -> None:
            self.parameters: dict[str, Any] = {}

        def execute(self, statement: Any, parameters: dict[str, Any]) -> None:
            self.parameters = parameters

    def inserted(route: AiRoute) -> dict[str, Any]:
        capture = Capture()
        AiJobRepository().insert(
            capture,  # type: ignore[arg-type]
            estimate=build_ai_estimate(scope=scope(), mode=AiMode.START, prompt_version="p1", counts=counts(), route=route),
            user_uid=USER, command_id="cmd_1",
        )
        return capture.parameters

    group = inserted(grouped_route())
    assert (group["binding_state"], group["revision_id"], group["group_revision_id"], group["rule_revision_id"]) == (
        "pending", None, REVISION, RULE)
    legacy = inserted(legacy_route())
    assert (legacy["binding_state"], legacy["revision_id"], legacy["group_revision_id"], legacy["rule_revision_id"]) == (
        "frozen_at_start", CONNECTION_REVISION, None, None)
