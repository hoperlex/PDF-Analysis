"""`HOSTS-LAYOUT-01`: `binding_for(cell)` -- one `CallBinding` per cell, no call without one, `accepted_reported` exact, the idempotency
key without a host, and `stage_key` in the call journal.

Container-free: the member binder, the repositories, the journal and the store are fakes. What PostgreSQL does with the same rows is in
``tests/integration/runs/test_stage_plan_binding_db.py`` (written, not run by the lane).
"""

from __future__ import annotations

import dataclasses
import json
import hashlib
from dataclasses import asdict, replace
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import (
    CellSettings, CostMeter, ModelRequest, ModelResponse, ProviderConfig, ProviderMode, accepted_reported, extended_digest,
)
from auditmanager.analysis.text.binding import CallBinding
from auditmanager.analysis.text.stage import _identity_refusal
from auditmanager.bootstrap.stage_plan_providers import BoundMember, StagePlanProviders
from auditmanager.runs import extended_review as review
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.executor import _DurableCallJournal, _bind_provider
from auditmanager.runs.provider import ProviderBinding
from auditmanager.runs.repository import CellBindingRow
from auditmanager.runs.stage_plan import call_journal_columns, cell_binding
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import BlobId

RUN = "run_01M2545JSD15ETSNNV904X991K"
GROUP_REV = "exgr_01M2545JSD15ETSNNV904X991R"
HOST_A = "exh_01M2545JSD15ETSNNV904X991A"
HOST_B = "exh_01M2545JSD15ETSNNV904X991B"


def plan(access: str = "subscription") -> layout.FrozenStagePlan:
    cells = tuple(replace(c, access=access) for c in layout.preset_cells("claude_only"))
    return layout.FrozenStagePlan("slr_01M2545JSD15ETSNNV904X991J", "claude_only", cells)


def revision_of(cell_key: str, host: str = HOST_A) -> str:
    return "excr_" + (cell_key.replace(":", "")[:8].upper() + host[-6:]).ljust(26, "0")[:26]


class Adapter:
    provider_mode = ProviderMode.LIVE

    def __init__(self, reply_model: str | None, calls: list[ModelRequest] | None = None) -> None:
        self.reply_model, self.calls = reply_model, calls if calls is not None else []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        return ModelResponse(output_text='{"observations":[]}', stop_reason="end_turn", input_tokens=10, output_tokens=5,
                             latency_ms=3, model=self.reply_model)


class Binder:
    """The composition root's member binder: records what it was asked and answers a member of the host it is told."""

    def __init__(self, host: str = HOST_A, reply_model: str | None = None, unmetered: bool | None = None) -> None:
        self.asked: list[tuple[str, str]] = []
        self.host, self.reply_model, self.unmetered = host, reply_model, unmetered

    def __call__(self, session: Any, *, connection_revision_id: str, cell: CellSettings, context: Any) -> BoundMember:
        self.asked.append((connection_revision_id, cell.cell_key))
        return BoundMember(
            adapter=Adapter(self.reply_model or cell.model_id), provider_label="claude_code", identity_basis="reported_model",
            connection_revision_id=connection_revision_id,
            unmetered=(cell.access == "subscription") if self.unmetered is None else self.unmetered, host_id=self.host,
        )


class Runs:
    def __init__(self, bound_cells: tuple[str, ...] | None = None, the_plan: layout.FrozenStagePlan | None = None) -> None:
        self.plan = the_plan or plan()
        keys = bound_cells if bound_cells is not None else tuple(c.cell_key for c in self.plan.cells)
        self.bound = {k: CellBindingRow(k, GROUP_REV, revision_of(k)) for k in keys}

    def cell_bindings(self, session: Any, run_id: str) -> dict[str, CellBindingRow]:
        return self.bound

    def get(self, session: Any, run_id: str) -> Any:
        return self.run()

    def run(self) -> Any:
        return SimpleNamespace(run_id=RUN, stage_plan=self.plan.to_json(), provider_mode="live")


def base_config(**more: Any) -> ProviderConfig:
    return ProviderConfig(mode=ProviderMode.LIVE, model_id="claude-sonnet-5-5", run_cost_ceiling_usd=1.0, api_key=None,
                          ceiling_is_explicit=True, **more)


def providers(runs: Runs | None = None, binder: Binder | None = None) -> tuple[StagePlanProviders, Runs, Binder]:
    runs, binder = runs or Runs(), binder or Binder()
    return StagePlanProviders(binder=binder, base_config=base_config(), runs=runs), runs, binder


def refused(call, *args, **kwargs) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    return caught.value


# --- binding_for(cell): one CallBinding per cell -------------------------------------------------------------------------------


def test_every_cell_gets_its_own_adapter_and_a_call_binding_held_to_its_model() -> None:
    source, runs, binder = providers()
    binding = source.resolve(None, runs.run())
    assert binding.call.cell_key == "text:main" and binding.config.model_id == "claude-sonnet-5-5"
    seen = {}
    for cell in runs.plan.cells:
        one = binding.cells(cell.cell_key)
        call = one.call
        assert (call.expected_model, call.check_identity, call.cell_key, call.access) == (
            cell.model_id, True, cell.cell_key, "subscription")
        assert call.connection_revision_id == revision_of(cell.cell_key) and call.host_id == HOST_A and call.unmetered is True
        assert one.config.model_id == cell.model_id and one.config.cell_settings == cell
        assert one.adapter.reply_model == cell.model_id
        seen[cell.cell_key] = one
    assert seen["blocks:leg1"].call.expected_model == "claude-opus-5-5", "the blocks cell is not the text cell's model"
    assert len({id(one.adapter) for one in seen.values()}) == len(seen)
    # a cell is built once per resolve: a second ask is the same binding, and the binder was asked once per cell
    assert binding.cells("norms:main") is seen["norms:main"]
    assert sorted(binder.asked) == sorted((revision_of(c.cell_key), c.cell_key) for c in runs.plan.cells)


def test_binding_for_is_the_one_cells_binding() -> None:
    source, runs, _ = providers()
    one = source.binding_for(None, run_id=RUN, cell_key="review:main")
    assert one.call.cell_key == "review:main" and one.call.expected_model == "claude-sonnet-5-5"


def test_an_api_cell_is_metered_and_a_member_that_disagrees_is_refused() -> None:
    api = Runs(the_plan=plan("api"))
    source, _, _ = providers(api)
    assert source.resolve(None, api.run()).call.unmetered is False
    wrong = StagePlanProviders(binder=Binder(unmetered=False), base_config=base_config(), runs=Runs())
    error = refused(wrong.resolve, None, Runs().run())
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID and error.detail_fields["reason"] == "cost_estimate_binding_changed"


def test_a_cell_with_no_binding_row_a_foreign_cell_and_a_run_without_a_plan_are_refused() -> None:
    source, runs, _ = providers(Runs(bound_cells=("text:main", "blocks:leg1")))
    assert refused(source.resolve, None, runs.run()).detail_fields["reason"] == "cell_not_bound"
    source, runs, _ = providers()
    binding = source.resolve(None, runs.run())
    assert refused(binding.cells, "invented:main").detail_fields["reason"] == "cell_not_in_plan"
    assert refused(source.resolve, None, SimpleNamespace(run_id=RUN, stage_plan=None)).detail_fields["reason"] == "run_has_no_stage_plan"


# --- the run-level binding and the cell's binding ----------------------------------------------------------------------------


def approved_config() -> ProviderConfig:
    return base_config(approved_cost_ceiling=True, approved_models={"claude-sonnet-5-5": {"rate_sha256": "a" * 64, "access": "subscription"}},
                       approved_stage_plan_digest="d" * 64, approved_window_characters=1234)


def test_the_cell_binding_carries_the_consent_of_the_run() -> None:
    source, runs, _ = providers()
    run_level = replace(source.resolve(None, runs.run()), config=replace(source.resolve(None, runs.run()).config,
                        **{k: getattr(approved_config(), k) for k in (
                            "approved_cost_ceiling", "approved_models", "approved_stage_plan_digest", "approved_window_characters")}))
    one = cell_binding(run_level, "blocks:leg1")
    assert one.config.model_id == "claude-opus-5-5" and one.config.approved_cost_ceiling is True
    assert one.config.approved_models == approved_config().approved_models and one.config.approved_stage_plan_digest == "d" * 64
    assert one.config.approved_window_characters == 1234 and one.cells is None
    assert one.config.approved_connection_revision_id is None and one.config.approved_group_revision_id is None


def test_a_run_that_is_not_planned_has_one_binding_for_every_call() -> None:
    legacy = ProviderBinding(adapter=Adapter("m"), config=base_config(), call=CallBinding(expected_model="m", check_identity=True))
    assert cell_binding(legacy, "blocks:leg1") is legacy and cell_binding(legacy, "anything") is legacy


@pytest.mark.parametrize("resolved", [
    ProviderBinding(adapter=Adapter("m"), config=base_config(cell_settings=layout.preset_cells("claude_only")[1]), call=None),
    ProviderBinding(adapter=Adapter("m"), config=base_config(cell_settings=layout.preset_cells("claude_only")[1]),
                    call=CallBinding(expected_model="claude-opus-5-5", check_identity=True)),
    ProviderBinding(adapter=Adapter("m"), config=base_config(cell_settings=layout.preset_cells("claude_only")[1]),
                    call=CallBinding(expected_model="claude-opus-5-5", check_identity=True, cell_key="norms:main", access="api")),
    ProviderBinding(adapter=Adapter("m"), config=base_config(), call=CallBinding(
        expected_model="claude-opus-5-5", check_identity=True, cell_key="blocks:leg1", access="api")),
])
def test_a_cell_that_comes_back_without_its_call_binding_is_refused_never_skipped(resolved) -> None:
    run_level = ProviderBinding(adapter=Adapter("m"), config=approved_config(), call=None, cells=lambda key: resolved)
    error = refused(cell_binding, run_level, "blocks:leg1")
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID and error.detail_fields["reason"] == "cell_call_binding_missing"


def test_a_cell_call_binding_cannot_be_built_without_the_identity_check() -> None:
    with pytest.raises(ValueError):
        CallBinding(expected_model="claude-opus-5-5", check_identity=False, cell_key="blocks:leg1", access="api")
    with pytest.raises(ValueError):
        CallBinding(check_identity=True, cell_key="blocks:leg1", access="api")
    with pytest.raises(ValueError):
        CallBinding(expected_model="claude-opus-5-5", check_identity=True, cell_key="blocks:leg1")


def test_the_executor_hands_the_consent_to_a_planned_binding_and_keeps_its_cells() -> None:
    source, runs, _ = providers()
    config = approved_config()
    bound = _bind_provider(None, runs.run(), None, lambda session, run, context: source.resolve(session, run, context),
                           Adapter("x"), config)
    assert bound.cells is not None and bound.config.approved_models == config.approved_models
    assert bound.config.approved_stage_plan_digest == "d" * 64
    assert cell_binding(bound, "norms:main").config.approved_models == config.approved_models


def test_a_planned_run_is_never_served_by_one_binding_or_by_the_processs_own_adapter() -> None:
    runs = Runs()
    one_binding = lambda session, run, context: ProviderBinding(adapter=Adapter("x"), config=base_config(), call=CallBinding(
        expected_model="claude-sonnet-5-5", check_identity=True))
    for providers_arg in (None, one_binding):
        error = refused(_bind_provider, None, runs.run(), None, providers_arg, Adapter("x"), base_config())
        assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID and error.detail_fields["reason"] == "stage_plan_run_without_cells"
    # a run with no plan is bound exactly as before, with or without a resolver
    plain = SimpleNamespace(run_id=RUN, stage_plan=None, provider_mode="live")
    assert _bind_provider(None, plain, None, None, Adapter("x"), base_config()).cells is None
    assert _bind_provider(None, plain, None, one_binding, Adapter("x"), base_config()).call.expected_model == "claude-sonnet-5-5"


# --- the three exact comparisons of the reported model ---------------------------------------------------------------------


def reply(model: str | None) -> ModelResponse:
    return ModelResponse("{}", "end_turn", 1, 1, 1, model=model)


def identity(expected: str, reported: str | None) -> Any:
    call = CallBinding(expected_model=expected, check_identity=True)
    return _identity_refusal(reply(reported), call, ProviderMode.LIVE)


def test_the_text_stage_holds_the_reply_to_the_model_or_an_exact_listed_name() -> None:
    assert identity("claude-opus-5-5", "claude-opus-5-5") is None
    assert identity("claude-opus-5-5", "claude-opus-5-5[1m]") is None, "listed by the catalogue"
    assert identity("claude-sonnet-5-5", "claude-opus-5-5") is not None, "another model is refused"
    for outside in ("claude-opus-5-5-20261001", "Claude-Opus-5-5", "claude-opus-5-5 ", "claude-opus-5", "", None):
        assert identity("claude-opus-5-5", outside) is not None, outside
    # a gateway name the catalogue does not list is what it always was: equality
    assert identity("my-gateway", "my-gateway") is None and identity("my-gateway", "my-gateway-2") is not None


def test_the_helper_is_exact_for_every_catalogue_model() -> None:
    from auditmanager.analysis.public import model_catalogue

    catalogue = model_catalogue()
    for model in catalogue.model_ids():
        listed = catalogue.accepted_reported(model)
        assert model in listed
        for name in listed:
            assert accepted_reported(model, name)
            assert not accepted_reported(model, name + "-2") and not accepted_reported(model, name.upper() + "x")
            assert not accepted_reported(model, " " + name)
        assert not accepted_reported(model, None) and not accepted_reported(model, 3)
    assert accepted_reported("claude-opus-5-5", "anthropic/claude-opus-5-5", provider="openrouter_api")
    assert not accepted_reported("claude-opus-5-5", "anthropic/claude-opus-5-5", provider="claude_code")
    assert not accepted_reported(None, "x") and not accepted_reported("", "")


# --- the idempotency key and the call journal ---------------------------------------------------------------------------------


class Journal:
    def __init__(self) -> None:
        self.events: list[str] = []

    def response_received(self, call_id: Any, response: Any) -> None:
        self.events.append("received")

    def complete(self, record: Any) -> None:
        self.events.append("complete")

    def outcome_unknown(self, call_id: Any, error: Any) -> None:
        self.events.append("unknown")

    def not_processed(self, call_id: Any, error: Any, klass: str) -> None:
        self.events.append("not_processed")


class Jobs:
    def __init__(self) -> None:
        self.prepared: list[dict[str, Any]] = []

    def require_current(self, session: Any, authority: Any) -> None:
        return None

    def prepare_provider_call(self, session: Any, authority: Any, **kwargs: Any) -> str:
        self.prepared.append(kwargs)
        return "mc_01M2545JSD15ETSNNV904X991M"


class Session:
    def commit(self) -> None:
        return None


class Store:
    def __init__(self, blobs: dict[str, bytes] | None = None) -> None:
        self.blobs = blobs or {}

    def read(self, blob_id: Any, verify: bool = True) -> bytes:
        return self.blobs[str(blob_id)]


class Harness:
    """Drives ``extended_review._call`` with fakes and a ``extended_unit`` that finds only what an earlier call saved."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.saved: dict[str, dict[str, Any]] = {}
        self.store = Store()
        self.looked_up: list[str] = []
        self.published: list[dict[str, Any]] = []
        monkeypatch.setattr(review, "extended_unit", self._unit)

    def _unit(self, session: Any, *, run_id: str, unit_key: str, source_sha256: str, phase: str) -> Any:
        self.looked_up.append(unit_key)
        return self.saved.get(unit_key)

    def publish(self, role: str, document: dict[str, Any]) -> Any:
        raw = json.dumps(document, sort_keys=True).encode()
        blob_id = BlobId.new().value
        self.store.blobs[blob_id] = raw
        self.published.append(document)
        return SimpleNamespace(blob_id=blob_id, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

    def call(self, binding: Any, request: ModelRequest, jobs: Jobs | None = None, journal: Journal | None = None) -> tuple[Any, bool]:
        jobs = jobs or Jobs()
        result = review._call(
            Session(), run_id=RUN, authority=SimpleNamespace(), jobs=jobs, journal=journal or Journal(), binding=binding, request=request,
            phase="v3:w0:blocks:b001", source_sha256="s" * 64, meter=CostMeter(ceiling_usd=100.0), store=self.store,
            publish=self.publish, checkpoint=lambda boundary: None)
        self.last_jobs = jobs
        return result

    def remember(self, binding: Any, request: ModelRequest, response: ModelResponse) -> None:
        """What a first call on some host saved: the unit row ``extended_unit`` would return for this request's key."""
        key = self.last_key
        ref = self.publish("reply", {"format": review.FORMAT, "kind": "reply", "unit_key": key,
                                    "request_sha256": request.request_sha256, "response": asdict(response)})
        raw = self.store.blobs[ref.blob_id]
        self.saved[key] = {"parameters": {"extended_reply_blob_id": ref.blob_id, "extended_reply_size": len(raw),
                                          "extended_reply_sha256": ref.sha256},
                           "request_sha256": request.request_sha256, "model_identity": request.model_id,
                           "provider_mode": binding.adapter.provider_mode.value, "response_sha256": response.response_sha256}

    @property
    def last_key(self) -> str:
        return self.looked_up[-1]


def request_for(model: str, text: str = "q") -> ModelRequest:
    return ModelRequest(model, {"model": model, "max_tokens": 6000, "messages": [{"role": "user", "content": text}],
                                "output_config": {"effort": "high"}, "thinking": {"type": "adaptive"}})


def cell_of(source: StagePlanProviders, runs: Runs, key: str) -> ProviderBinding:
    return cell_binding(source.resolve(None, runs.run()), key)


def test_the_key_of_a_planned_call_has_neither_the_host_nor_the_connection_revision(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    request = request_for("claude-opus-5-5")
    on_a = cell_of(*providers(Runs(), Binder(HOST_A))[:2], "blocks:leg1")
    on_b = cell_of(*providers(Runs(), Binder(HOST_B))[:2], "blocks:leg1")
    moved = replace(on_b, call=replace(on_b.call, connection_revision_id="excr_" + "Z" * 26))
    keys = []
    for binding in (on_a, on_b, moved):
        harness.call(binding, request)
        keys.append(harness.last_key)
    assert keys[0] == keys[1] == keys[2]
    assert keys[0] == extended_digest({"format": review.FORMAT, "source": "s" * 64, "phase": "v3:w0:blocks:b001",
                                       "request": request.request_sha256, "model": "claude-opus-5-5"})
    other_model = request_for("claude-sonnet-5-5")
    harness.call(cell_of(*providers()[:2], "text:main"), other_model)
    assert harness.last_key != keys[0], "the model is part of the key"


def test_a_replay_on_another_host_finds_the_saved_answer_and_calls_nothing(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    request = request_for("claude-opus-5-5")
    first = cell_of(*providers(Runs(), Binder(HOST_A))[:2], "blocks:leg1")
    response, reused = harness.call(first, request)
    assert reused is False and len(first.adapter.calls) == 1
    harness.remember(first, request, response)
    second = cell_of(*providers(Runs(), Binder(HOST_B))[:2], "blocks:leg1")
    again, reused = harness.call(second, request)
    assert reused is True and again.output_text == response.output_text and second.adapter.calls == []
    assert harness.last_jobs.prepared == [], "nothing is journalled and nothing is paid for a saved reply"


def test_a_connection_bound_call_keeps_the_key_it_always_had(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    request = request_for("claude-sonnet-5-5")
    for revision in ("excr_" + "A" * 26, "excr_" + "B" * 26):
        binding = ProviderBinding(adapter=Adapter("claude-sonnet-5-5"), config=base_config(), call=CallBinding(
            expected_model="claude-sonnet-5-5", check_identity=True, connection_revision_id=revision, identity_basis="reported_model"))
        harness.call(binding, request)
        assert harness.last_key == extended_digest({
            "format": review.FORMAT, "source": "s" * 64, "phase": "v3:w0:blocks:b001", "request": request.request_sha256,
            "model": "claude-sonnet-5-5", "connection": revision})
    assert len(set(harness.looked_up)) == 2, "a legacy key still follows the connection revision"
    env = ProviderBinding(adapter=Adapter(None), config=base_config(), call=None)
    harness.call(env, request)
    assert harness.last_key == extended_digest({"format": review.FORMAT, "source": "s" * 64, "phase": "v3:w0:blocks:b001",
                                                "request": request.request_sha256, "model": "claude-sonnet-5-5", "connection": None})


def test_the_stage_key_host_and_access_reach_the_call_journal_of_a_planned_call_only(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    source, runs, _ = providers(Runs(the_plan=plan("api")), Binder(HOST_B))
    harness.call(cell_of(source, runs, "norms:main"), request_for("claude-sonnet-5-5"))
    (prepared,) = harness.last_jobs.prepared
    assert (prepared["stage_key"], prepared["host_id"], prepared["access"]) == ("norms", HOST_B, "api")
    legacy = ProviderBinding(adapter=Adapter("claude-sonnet-5-5"), config=base_config(), call=CallBinding(
        expected_model="claude-sonnet-5-5", check_identity=True))
    harness.call(legacy, request_for("claude-sonnet-5-5", "other"))
    assert not {"stage_key", "host_id", "access"} & set(harness.last_jobs.prepared[0])
    assert call_journal_columns(None) == {} and call_journal_columns(legacy.call) == {}


def test_the_text_journal_writes_the_row_of_the_text_cell(monkeypatch) -> None:
    jobs = Jobs()
    call = CallBinding(expected_model="claude-sonnet-5-5", check_identity=True, cell_key="text:main", access="subscription", host_id=HOST_A)
    journal = _DurableCallJournal(Session(), jobs, SimpleNamespace(), call=call)
    journal.prepare(request_for("claude-sonnet-5-5"), mode=ProviderMode.LIVE)
    assert jobs.prepared[0]["stage_key"] == "text" and jobs.prepared[0]["host_id"] == HOST_A and jobs.prepared[0]["access"] == "subscription"
    plain = Jobs()
    _DurableCallJournal(Session(), plain, SimpleNamespace(), call=CallBinding(expected_model="m", check_identity=True)).prepare(
        request_for("m"), mode=ProviderMode.LIVE)
    assert "stage_key" not in plain.prepared[0]


# --- no call without its cell, and the reply is held to the cell's model -----------------------------------------------------


def test_a_call_made_on_the_run_level_binding_of_a_planned_run_is_refused(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    source, runs, _ = providers()
    run_level = source.resolve(None, runs.run())
    error = refused(harness.call, run_level, request_for("claude-opus-5-5"))
    assert error.detail_fields["reason"] == "extended_call_without_cell"
    assert run_level.adapter.calls == [] and harness.looked_up == [], "refused before the key is looked up or anything is sent"


def test_another_reported_model_is_refused_and_a_listed_name_is_accepted(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    request = request_for("claude-opus-5-5")
    wrong = cell_of(*providers(Runs(), Binder(reply_model="claude-sonnet-5-5"))[:2], "blocks:leg1")
    error = refused(harness.call, wrong, request)
    assert error.detail_fields["reason"] == "extended_model_identity_mismatch"
    alias = cell_of(*providers(Runs(), Binder(reply_model="claude-opus-5-5[1m]"))[:2], "blocks:leg1")
    harness2 = Harness(monkeypatch)
    response, reused = harness2.call(alias, request)
    assert reused is False and response.model == "claude-opus-5-5[1m]"
    outside = cell_of(*providers(Runs(), Binder(reply_model="claude-opus-5-5-20261001"))[:2], "blocks:leg1")
    assert refused(Harness(monkeypatch).call, outside, request).detail_fields["reason"] == "extended_model_identity_mismatch"
    silent = cell_of(*providers(Runs(), Binder())[:2], "blocks:leg1")
    silent.adapter.reply_model = None
    assert refused(Harness(monkeypatch).call, silent, request).detail_fields["reason"] == "extended_model_identity_mismatch"


def test_a_phase_is_called_on_the_cell_of_its_row_and_a_phase_without_a_row_is_refused() -> None:
    source, runs, _ = providers()
    run_level = source.resolve(None, runs.run())
    expected = {"blocks:0:leg1": "blocks:leg1", "blocks:b002:judge": "blocks:judge", "blocks:0:leg1:repair:1": "blocks:leg1",
                "blocks:b001:judge:repair:1": "blocks:judge", "comprehensive": "cross_check:main",
                "comprehensive_analysis:b001": "cross_check:main", "norm_verification:b003:repair:1": "norms:main",
                "critic": "review:main", "finding_review:b001:repair:1": "review:main", "corrector": "correction:main"}
    for identity_, cell_key in expected.items():
        assert review._phase_binding(run_level, identity_).call.cell_key == cell_key, identity_
    # the plan's blocks row is an ensemble: a blocks call that names no leg or judge has no cell to run on, and is refused, not skipped
    # (the Claude ensemble has no second leg either)
    for no_cell in ("blocks:0", "blocks:b002:repair:1", "blocks:0:leg2"):
        assert refused(review._phase_binding, run_level, no_cell).detail_fields["reason"] == "cell_not_in_plan", no_cell
    for modelless in ("merge", "report", "unknown:b001"):
        error = refused(review._phase_binding, run_level, modelless)
        assert error.detail_fields["reason"] == "extended_phase_has_no_cell"
    legacy = ProviderBinding(adapter=Adapter("m"), config=base_config(), call=CallBinding(expected_model="m", check_identity=True))
    assert review._phase_binding(legacy, "merge") is legacy and review._phase_binding(legacy, "blocks:0") is legacy


def test_the_phase_dictionary_maps_every_call_identity_of_the_workflow_to_one_row() -> None:
    expected = {
        "blocks:3": "blocks", "blocks:b002": "blocks", "blocks:3:leg1": "blocks", "blocks:3:leg2": "blocks", "blocks:3:judge": "blocks", "comprehensive": "cross_check", "comprehensive:2": "cross_check",
        "comprehensive_analysis:b001": "cross_check", "norm_verification": "norms", "norm_verification:b004": "norms",
        "critic": "review", "finding_review:b001": "review", "corrector": "correction", "finding_correction:b003": "correction",
        "project_parameters": "cross_check", "text_analysis": "text",
    }
    for identity_, row in expected.items():
        assert layout.row_of_phase(identity_) == row, identity_
        assert layout.row_of_phase(identity_ + ":repair:1") == row, "a semantic repair runs on the cell of the phase it repairs"
    for modelless in ("merge", "report", "source_preparation", "unknown", ""):
        assert layout.row_of_phase(modelless) is None
