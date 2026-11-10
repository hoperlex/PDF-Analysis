"""`HOSTS-CMP-01` (ADR-0028 decision 19): the route of a comparison kind under the stage layout, container-free, with the layout and the executors' reads
stood in for.

* with the switch off, and for a kind the layout holds no cell of (``comparison_stage_review``), the route is what it always was -- legacy, or the
  work kind's rule -- and the layout's availability is not even asked;
* with it on, the route is the current revision of the system group of the cell's model, a subscription before an API key, and carries the cell:
  the estimate and the digest bind it, the job freezes it;
* a kind whose model no server can serve is the typed ``executor_route_missing`` and is **not** routed anywhere else -- neither the legacy connection
  nor the rule nor another model is read;
* the cell caps the answer limit of the estimate (``min``), and a job that was admitted keeps its own cell whatever the layout says now.

The statements that read real hosts and groups are ``tests/integration/comparison/test_layout_route_db.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings, ModelPin
from auditmanager.comparison.ai_jobs import estimate as estimate_module
from auditmanager.comparison.ai_jobs import layout_route
from auditmanager.comparison.ai_jobs.model import AiCallGroup, AiCounts, AiRoute, AiScope, AiMode
from auditmanager.runs import stage_layout as layout
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorConnectionId, ExecutorConnectionRevisionId, ExecutorGroupId, ExecutorGroupRevisionId, ProjectUid, DocumentUid

ASTRA, SONNET, LUNA = "gpt-6-astra", "claude-sonnet-5-5", "gpt-6-luna"
SUB_GROUP, API_GROUP = str(ExecutorGroupId.new()), str(ExecutorGroupId.new())
SUB_REV, API_REV = str(ExecutorGroupRevisionId.new()), str(ExecutorGroupRevisionId.new())
CONNECTION, CONNECTION_REV = str(ExecutorConnectionId.new()), str(ExecutorConnectionRevisionId.new())
KIND = "comparison_pair_check"
CELL = CellSettings(f"{KIND}:main", ASTRA, "high")


def group_revision(identity: str, group: str, *, model: str, billing: str) -> SimpleNamespace:
    return SimpleNamespace(
        group_revision_id=identity, group_id=group, revision_no=1, pin_id=model, gateway_model=model, billing=billing,
        input_per_mtok_usd=Decimal("2.0"), output_per_mtok_usd=Decimal("10.0"), strategy="least_loaded", members=())


@dataclass
class Layout:
    """The layout store as the runs context answers it."""

    enabled_: bool = True
    cells: tuple[CellSettings, ...] | None = (CELL,)
    kit: str = "codex_only"
    asked: int = 0

    def enabled(self, session: Any) -> bool:
        self.asked += 1
        return self.enabled_

    def current_revision(self, session: Any) -> Any:
        from auditmanager.runs.public import LayoutRevisionRow

        return LayoutRevisionRow("slr_x", 1, self.kit, (), None, "usr_x", comparison_cells=self.cells)  # type: ignore[arg-type]


class World:
    """The executors' reads: which (model, access) pairs have an available member, which are full, and the route the legacy and the rule would read."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, free: tuple[str, ...] = ("subscription", "api"), full: tuple[str, ...] = (),
                 mode: str = "legacy", layout_state: Layout | None = None, source: str | None = "database", model: str = ASTRA) -> None:
        from auditmanager.executors import public as executors
        from auditmanager.runs import public as runs

        self.layout = layout_state or Layout()
        self.free, self.full, self.mode = free, full, mode
        self.evaluated: list[str] = []
        self.legacy_reads = self.rule_reads = 0
        revisions = {SUB_REV: group_revision(SUB_REV, SUB_GROUP, model=model, billing="not_metered"),
                     API_REV: group_revision(API_REV, API_GROUP, model=model, billing="metered")}
        self.revisions = revisions
        groups = {"subscription": (SUB_GROUP, SUB_REV), "api": (API_GROUP, API_REV)}
        lock = {ASTRA: (2.0, 10.0), SONNET: (2.0, 10.0), LUNA: (0.1, 0.5)}

        def evaluate_wait(session: Any, *, run_id: str, cells: Any, **kw: Any) -> Any:
            (cell,) = cells
            self.evaluated.append(cell.access)
            assert cell.model_id == self.layout.cells[0].model_id if self.layout.cells else True
            if cell.access in self.free:
                bound = SimpleNamespace(group_revision_id=groups[cell.access][1], access=cell.access, model_id=cell.model_id)
                return SimpleNamespace(bound=(bound,), reason=None, waits=())
            if cell.access in self.full:
                return SimpleNamespace(bound=None, reason="executor_at_capacity", waits=(SimpleNamespace(cause=executors.AT_CAPACITY),))
            return SimpleNamespace(bound=None, reason="model_unavailable", waits=(SimpleNamespace(cause="host_offline"),))

        class Hosts:
            def system_group_for(self, session: Any, name: str) -> str | None:
                return next((group for access, (group, _rev) in groups.items() if name.endswith(access)), None)

        def detail(session: Any, group_id: str, groups_: Any = None) -> Any:
            revision = next(rev for access, (group, rev) in groups.items() if group == group_id)
            return SimpleNamespace(revisions=(revisions[revision],))

        def legacy(session: Any, work_kind: str, repository: Any = None) -> Any:
            self.legacy_reads += 1
            settings = SimpleNamespace(pin_id=ASTRA, gateway_model=ASTRA, billing="metered")
            return SimpleNamespace(primary=SimpleNamespace(connection_id=CONNECTION, revision_id=CONNECTION_REV, settings=settings))

        def rule(session: Any, work_kind: str, groups_: Any = None) -> Any:
            self.rule_reads += 1
            return SimpleNamespace(rule_revision_id="exrr", work_kind=work_kind, rule_no=1, group_revision_id=API_REV, group_id=API_GROUP)

        monkeypatch.setattr(runs, "SqlStageLayoutStore", lambda: self.layout)
        monkeypatch.setattr(executors, "evaluate_wait", evaluate_wait)
        monkeypatch.setattr(executors, "HostRepository", Hosts)
        monkeypatch.setattr(executors, "pair_group_name", lambda model, access: f"{model} · {access}")
        monkeypatch.setattr(executors, "group_detail", detail)
        monkeypatch.setattr(executors, "group_revision_of", lambda session, identity, groups_=None: revisions.get(identity))
        monkeypatch.setattr(executors, "pinned_models", lambda: tuple(ModelPin(model, *rates) for model, rates in lock.items()))
        monkeypatch.setattr(executors, "routing_mode", lambda session, groups_=None: SimpleNamespace(mode=self.mode))
        monkeypatch.setattr(executors, "resolve_route", legacy)
        monkeypatch.setattr(executors, "resolve_rule", rule)
        if source is None:
            monkeypatch.delenv(layout_route.PROVIDER_SOURCE_ENV, raising=False)
        else:
            monkeypatch.setenv(layout_route.PROVIDER_SOURCE_ENV, source)

    def read(self, kind: str = KIND) -> AiRoute:
        return estimate_module.read_route(SimpleNamespace(info={}), kind, "live")  # type: ignore[arg-type]


def refused(world: World, kind: str = KIND) -> DomainError:
    with pytest.raises(DomainError) as caught:
        world.read(kind)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and caught.value.detail_fields["dependency"] == "executor_route_missing"
    return caught.value


# -- the third branch ---------------------------------------------------------------------------------------------------------


def test_the_layout_on_routes_the_kind_to_the_system_group_of_its_cells_model_with_the_cell(monkeypatch):
    world = World(monkeypatch)
    route = world.read()
    assert route.grouped and route.executor_group_revision_id == SUB_REV and route.executor_group_id == SUB_GROUP
    assert (route.pinned_model, route.billing, route.connection_id, route.revision_id) == (ASTRA, "not_metered", None, None)
    assert route.routing_rule_revision_id is None, "no rule routed it: the layout did"
    assert route.cell == CELL
    assert world.legacy_reads == 0 and world.rule_reads == 0


def test_a_subscription_is_tried_first_and_an_api_key_only_when_no_subscription_serves_the_model(monkeypatch):
    both = World(monkeypatch, free=("subscription", "api"))
    assert both.read().executor_group_revision_id == SUB_REV and both.evaluated == ["subscription"], "the api is not even asked"
    api_only = World(monkeypatch, free=("api",))
    route = api_only.read()
    assert (route.executor_group_revision_id, route.billing) == (API_REV, "metered") and api_only.evaluated == ["subscription", "api"]


def test_a_member_whose_pool_is_full_still_serves_the_job_waits_for_the_unit_rather_than_buying_an_api_key(monkeypatch):
    world = World(monkeypatch, free=("api",), full=("subscription",))
    route = world.read()
    assert route.executor_group_revision_id == SUB_REV and route.billing == "not_metered"
    assert world.evaluated == ["subscription"], "the api key is not tried because a subscription is busy"


def test_a_model_no_server_serves_is_refused_and_nothing_else_is_read(monkeypatch):
    world = World(monkeypatch, free=(), mode="rules")
    refused(world)
    assert world.evaluated == ["subscription", "api"]
    assert world.legacy_reads == 0 and world.rule_reads == 0, "never routed somewhere else, silently"


@pytest.mark.parametrize("mode", ["legacy", "rules"])
def test_the_layout_wins_over_the_routing_mode(monkeypatch, mode):
    world = World(monkeypatch, mode=mode)
    assert world.read().executor_group_revision_id == SUB_REV and world.legacy_reads == 0 and world.rule_reads == 0


def test_with_the_switch_off_the_route_is_what_it_was_and_the_layout_is_not_asked(monkeypatch):
    legacy = World(monkeypatch, layout_state=Layout(enabled_=False), mode="legacy")
    route = legacy.read()
    assert (route.connection_id, route.revision_id, route.cell) == (CONNECTION, CONNECTION_REV, None) and legacy.evaluated == []
    rules = World(monkeypatch, layout_state=Layout(enabled_=False), mode="rules")
    route = rules.read()
    assert (route.executor_group_revision_id, route.routing_rule_revision_id, route.cell) == (API_REV, "exrr", None) and rules.evaluated == []


def test_a_kind_the_layout_has_no_cell_for_is_read_as_before_even_with_it_on(monkeypatch):
    world = World(monkeypatch, mode="legacy")
    route = world.read("comparison_stage_review")
    assert route.connection_id == CONNECTION and route.cell is None
    assert world.layout.asked == 0, "the layout is not consulted for a kind it does not carry"


def test_the_layout_on_under_another_provider_source_is_refused_as_a_run_would_be(monkeypatch):
    for source in ("environment", None):
        world = World(monkeypatch, source=source)
        refused(world)
        assert world.evaluated == [] and world.legacy_reads == 0


def test_a_revision_with_no_cell_for_the_kind_is_refused_not_served_by_a_model_nobody_chose(monkeypatch):
    world = World(monkeypatch, layout_state=Layout(cells=None, kit="custom"))
    refused(world)
    assert world.evaluated == [] and world.legacy_reads == 0 and world.rule_reads == 0


def test_a_revision_that_follows_its_sets_table_gives_the_kind_the_sets_cell(monkeypatch):
    table_cell = layout.comparison_preset_cells("codex_only")[0]
    assert table_cell.model_id == LUNA, "the table of « Только Codex » gives the pair check gpt-6-luna since R-153m; the world serves that model"
    world = World(monkeypatch, layout_state=Layout(cells=None, kit="codex_only"), model=table_cell.model_id)
    assert world.read().cell == table_cell


def test_the_route_of_a_job_that_is_being_re_estimated_wins_over_the_layout(monkeypatch):
    world = World(monkeypatch, layout_state=Layout(cells=(replace(CELL, effort="low"),)))
    own = estimate_module.read_route.__globals__["route_of_group_revision"](None, API_REV, work_kind=KIND, provider_mode="live", rule_revision_id=None, cell=CELL)
    session = SimpleNamespace(info={estimate_module.JOB_ROUTE_KEY: own})
    assert estimate_module.read_route(session, KIND, "live") is own and world.layout.asked == 0


def test_a_group_that_pins_another_model_is_not_the_cells(monkeypatch):
    world = World(monkeypatch)
    world.revisions[SUB_REV].pin_id = SONNET
    refused(world)


# -- the route carries the cell into the estimate, the digest and the stored document ----------------------------------------------


def counts() -> AiCounts:
    return AiCounts(groups=(AiCallGroup(calls=10, prompt_chars=4_000, output_tokens=8_192, images=2, image_bytes=200_000),), units=10)


def scope() -> AiScope:
    return AiScope(method="pair_check", project_uid=str(ProjectUid.new()), document_uid=str(DocumentUid.new()), matrix_id="cmx_" + "1" * 26)


def route_with(cell: CellSettings | None, *, billing: str = "metered", kind: str = KIND) -> AiRoute:
    revision = group_revision(API_REV, API_GROUP, model=ASTRA, billing=billing)
    return AiRoute(
        work_kind=kind, connection_id=None, revision_id=None, pinned_model=ASTRA, gateway_model=ASTRA, billing=billing, provider_mode="live",
        pin=ModelPin(ASTRA, 2.0, 10.0), executor_group_id=API_GROUP, executor_group_revision_id=revision.group_revision_id, cell=cell)


def test_the_cell_is_in_the_routes_document_and_so_in_the_digest_the_user_consents_to():
    with_cell, without = route_with(CELL).as_document(), route_with(None).as_document()
    assert with_cell["cell"] == {"work_kind": KIND, "model_id": ASTRA, "effort": "high"}, "no answer limit and no timeout in the cell (`LIMITS-01`)"
    assert "cell" not in without, "a route with no cell is the document it always was"
    assert {k: v for k, v in with_cell.items() if k != "cell"} == without
    digests = {
        cell: estimate_module.build_estimate(scope=scope(), mode=AiMode.START, prompt_version="p", counts=AiCounts(groups=(), units=0), route=route_with(cell)).estimate_digest
        for cell in (None, CELL, replace(CELL, effort="medium"), replace(CELL, model_id=SONNET))
    }
    assert len(set(digests.values())) == 4, "a moved effort or model is another estimate: the consent covers what will run"


def test_nothing_caps_the_output_the_estimate_counts():
    """`R-153n`: a cell has no answer limit, so the estimate counts the module's own figure of every call, with or without a cell."""
    def build(cell):
        return estimate_module.build_estimate(scope=scope(), mode=AiMode.START, prompt_version="p", counts=counts(), route=route_with(cell))

    uncelled, celled = build(None), build(CELL)
    assert uncelled.totals.output_tokens == celled.totals.output_tokens == 10 * 8_192
    assert uncelled.estimate_micros == celled.estimate_micros
    assert "max_output_tokens" not in celled.as_dict(with_state=False)["route"]["cell"]


def test_a_subclass_of_the_counts_is_untouched_by_a_cell():
    from auditmanager.comparison.specification.method import SpecCounts

    spec = SpecCounts(groups=(AiCallGroup(calls=1, prompt_chars=10, output_tokens=32_000),), units=1, can_run_without_model=True)
    cell = replace(CELL, cell_key="comparison_spec:main")
    built = estimate_module.build_estimate(
        scope=AiScope(method="spec", project_uid=str(ProjectUid.new()), document_uid=str(DocumentUid.new()), transition_id="cmt_" + "1" * 26),
        mode=AiMode.START, prompt_version="p", counts=spec, route=route_with(cell, kind="comparison_spec"))
    assert type(built.counts) is SpecCounts and built.counts.can_run_without_model is True
    assert built.totals.output_tokens == 32_000, "the specification's own 32 000, not lowered by the cell"


def test_a_job_that_froze_its_cell_before_the_limits_left_is_shown_without_them():
    """`estimate_view`: the stored estimate of such a job holds an answer limit and a timeout in ``route.cell``; the contract's cell has neither, so
    the view drops them (the stored row is not rewritten) and the cell read back is the same cell."""
    from auditmanager.comparison.ai_jobs.model import cell_of_document, estimate_view

    stored = {"route": {"pinned_model": ASTRA, "cell": {**route_with(CELL).as_document()["cell"], "max_output_tokens": 1_200, "timeout_seconds": 900}}}
    shown = estimate_view(stored)
    assert shown["route"]["cell"] == {"work_kind": KIND, "model_id": ASTRA, "effort": "high"}
    assert "max_output_tokens" in stored["route"]["cell"], "the stored document is not changed"
    assert cell_of_document(stored["route"]["cell"]) == CELL
    assert estimate_view({"route": {"pinned_model": ASTRA}}) == {"route": {"pinned_model": ASTRA}}


def test_a_cell_belongs_to_a_group_route_and_to_its_own_kind():
    with pytest.raises(ValueError):
        AiRoute(work_kind=KIND, connection_id=CONNECTION, revision_id=CONNECTION_REV, pinned_model=ASTRA, gateway_model=ASTRA,
                billing="metered", provider_mode="live", cell=CELL)
    with pytest.raises(ValueError):
        route_with(replace(CELL, cell_key="comparison_report:main"))
