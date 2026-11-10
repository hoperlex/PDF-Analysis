"""`HOSTS-ENSEMBLE-01`: the blocks ensemble -- legs, then a judge -- as the run executes it (ADR-0028 decision 11).

Container-free. The member binder, the journal, the unit lookup and the store are fakes, but the code under test is the real one: the run's
own workflow (``extended_review._run_workflow_v2`` and ``run_extended_review``), the real ``_call`` with its idempotency key and journal, the
real ``StagePlanProviders`` and ``cell_binding`` (one binding per cell, held to the cell's model), and the real judge builder, parser and
reconciliation of ``analysis.extended.block_ensemble``.

Every guard here has been shown able to fail: the break-it-once runs of `HOSTS-ENSEMBLE-01` plant the defect each guard exists to catch (a
retry of ``outcome_unknown``, a retry outside the four classes, an unbounded retry, a leg failure that aborts the batch or skips the judge,
a judge that rewrites a leg's observation, the role dropped from the call identity, the cell resolved by the row alone) and record that this
file turns red.

The per-run leg breaker of D-662 (a leg that failed after its retries in three consecutive batches is no longer asked) is held to the same
rule: its break-it-once run is recorded in the commit that added it.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace as NS
from typing import Any, Callable

import pytest

from auditmanager.analysis.public import (
    CostMeter, ModelResponse, ProviderConfig, ProviderMode, ProxyDispatchError, block_leg_refs, build_block_judge_request,
    extended_coverage_policy, extended_review_bundle_digest, parse_block_judge_reply, reconcile_block_batch,
)
from auditmanager.bootstrap.stage_plan_providers import BoundMember, StagePlanProviders
from auditmanager.runs import extended_review as runtime
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.repository import CellBindingRow
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.analysis_extended.test_core import VERSION, documents

RUN_ID = "run_01M2545JSD15ETSNNV904X991K"
REVISION = "slr_01M2545JSD15ETSNNV904X991J"
GROUP_REV = "exgr_01M2545JSD15ETSNNV904X991R"
HOST = "exh_01M2545JSD15ETSNNV904X991A"
OPUS, SONNET, ASTRA, SOL, SOL61 = "claude-opus-5-5", "claude-sonnet-5-5", "gpt-6-astra", "gpt-6-sol", "gpt-6.1-sol"
RETRY_CLASSES = ("not_sent", "rate_limited", "proxy_unavailable", "definite_refusal")


# --- the fakes ---------------------------------------------------------------------------------------------------------------


def revision_of(cell_key: str) -> str:
    return "excr_" + (cell_key.replace(":", "").upper() + "0" * 26)[:26]


def dispatch_error(klass: str) -> DomainError:
    return ProxyDispatchError(ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class=klass, retry_safe=klass == "rate_limited")


class Jobs:
    def __init__(self) -> None:
        self.prepared: list[dict[str, Any]] = []

    def require_current(self, session: Any, authority: Any) -> None:
        return None

    def prepare_provider_call(self, session: Any, authority: Any, **kwargs: Any) -> str:
        self.prepared.append(kwargs)
        return "mc_" + f"{len(self.prepared):026d}"


class Journal:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def response_received(self, call_id: Any, response: Any) -> None:
        self.events.append(("received", call_id))

    def complete(self, record: Any) -> None:
        self.events.append(("complete", record.parameters["extended_phase"]))

    def not_processed(self, call_id: Any, error: Any, klass: str) -> None:
        self.events.append(("not_processed", klass))

    def outcome_unknown(self, call_id: Any, error: Any) -> None:
        self.events.append(("unknown", None))

    def bind_current_call(self, call_id: Any) -> None:
        return None


class Store:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self.blobs = blobs

    def read(self, blob_id: Any, **_: Any) -> bytes:
        return self.blobs[str(blob_id)]


class CellAdapter:
    """The adapter of one bound cell: answers as the harness's ``answer(cell_key, request, nth)`` says, or raises what it returns."""

    provider_mode = ProviderMode.LIVE

    def __init__(self, cell: layout.CellSettings, harness: "Harness") -> None:
        self.cell, self.harness, self.requests = cell, harness, []

    def complete(self, request: Any) -> ModelResponse:
        self.requests.append(request)
        self.harness.log.append((self.cell.cell_key, request))
        answer = self.harness.answer(self.cell.cell_key, request, len(self.requests))
        if isinstance(answer, BaseException):
            raise answer
        return ModelResponse(output_text=answer, stop_reason="end_turn", input_tokens=10, output_tokens=5, latency_ms=3,
                             model=self.harness.reported(self.cell))


def observation(source: str, title: str, description: str = "Уточнить обозначение аппарата") -> dict[str, Any]:
    return {"title": title, "description": description, "source_ids": [source], "norm_queries": []}


def default_answer(cell_key: str, request: Any, nth: int) -> str:
    """Each leg returns one observation of its own on the first source; the judge pairs the two legs' first observations when both are there
    and adds one observation neither leg made. Anything else (the comprehensive review) returns nothing."""
    payload = json.loads(request.body["messages"][0]["content"])
    role = cell_key.partition(":")[2]
    if role in ("leg1", "leg2", "main") and cell_key.startswith("blocks"):
        return json.dumps({"observations": [observation(payload["sources"][0]["source_id"], f"{role} находка {payload['sources'][0]['page_number']}",
                                                         f"Описание {role} для страницы {payload['sources'][0]['page_number']}")]}, ensure_ascii=False)
    if role == "judge":
        legs = {leg["leg"]: leg["observations"] for leg in payload["legs"]}
        pairs = ([{"left_ref": legs["leg1"][0]["ref"], "right_ref": legs["leg2"][0]["ref"], "relation": "extension", "extends": "right",
                   "confidence": 0.8, "reason": "один и тот же узел"}] if len(legs) == 2 and all(legs.values()) else [])
        gap = [observation(payload["sources"][-1]["source_id"], f"пропуск судьи {payload['sources'][0]['page_number']}",
                           "Совсем иная проблема: не указан класс огнестойкости заполнения проёма")]
        return json.dumps({"relationships": pairs, "gap_observations": gap, "gap_search": {
            "performed": True, "status": "gaps_found", "searched_categories": ["обозначения"], "summary": "найдено одно"}}, ensure_ascii=False)
    return json.dumps({"observations": []})


class Harness:
    """A planned run: its frozen plan, one scripted adapter per cell, and everything the workflow writes."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, kit: str = "claude_only", cells: tuple[layout.CellSettings, ...] | None = None,
                 answer: Callable[[str, Any, int], Any] = default_answer, access: str = "subscription",
                 reported: Callable[[layout.CellSettings], str | None] = lambda cell: cell.model_id) -> None:
        cells = cells if cells is not None else layout.preset_cells(kit)
        self.plan = layout.FrozenStagePlan(REVISION, kit, tuple(replace(c, access=access) for c in cells))
        self.answer, self.reported, self.log, self.sleeps, self.unit_keys, self.ambiguous = answer, reported, [], [], [], False
        self.checkpoints: list[str] = []
        self.stop_at_window: int | None = None
        self.adapters: dict[str, CellAdapter] = {}
        self.jobs, self.journal, self.saved = Jobs(), Journal(), []
        self.blobs: dict[str, bytes] = {}
        monkeypatch.setattr(runtime, "_sleep", self.sleeps.append)
        monkeypatch.setattr(runtime, "extended_unit", self._unit)
        monkeypatch.setattr("auditmanager.jobs.public.has_ambiguous_provider_effect", lambda session, run_id: self.ambiguous)
        harness = self

        class Runs:
            def cell_bindings(self, session: Any, run_id: str) -> dict[str, CellBindingRow]:
                return {c.cell_key: CellBindingRow(c.cell_key, GROUP_REV, revision_of(c.cell_key)) for c in harness.plan.cells}

            def get(self, session: Any, run_id: str) -> Any:
                return harness.run

        def binder(session: Any, *, connection_revision_id: str, cell: layout.CellSettings, context: Any) -> BoundMember:
            adapter = self.adapters.setdefault(cell.cell_key, CellAdapter(cell, self))
            return BoundMember(adapter=adapter, provider_label="claude_code", identity_basis="reported_model",
                               connection_revision_id=connection_revision_id, unmetered=cell.access == "subscription", host_id=HOST)

        self.run = NS(run_id=RUN_ID, version_uid=VERSION, stage_plan=self.plan.to_json(), provider_mode="live")
        config = ProviderConfig(mode=ProviderMode.LIVE, model_id=self.plan.cell("text:main").model_id, run_cost_ceiling_usd=100.0, api_key=None,
                                ceiling_is_explicit=True)
        self.binding = StagePlanProviders(binder=binder, base_config=config, runs=Runs()).resolve(None, self.run)

    def _unit(self, session: Any, *, run_id: str, unit_key: str, source_sha256: str, phase: str) -> Any:
        self.unit_keys.append((phase, unit_key))
        return None

    def publish(self, role: str, document: dict[str, Any]) -> Any:
        raw = json.dumps(document, sort_keys=True).encode()
        key = f"reply{len(self.blobs)}"
        self.blobs[key] = raw
        return NS(blob_id=key, sha256=sha256(raw).hexdigest(), size_bytes=len(raw))

    # -- the two workflows ------------------------------------------------------------------------------------------------------

    def documents(self, count: int) -> tuple[dict[str, Any], dict[str, bytes]]:
        portal, manifest, blobs = documents(count)
        docs = {"geometry.portal_blocks": portal, "geometry.page_crops": manifest,
                "prepared.text_layer": {"pages": [{"page_number": i, "text": "Текст страницы"} for i in range(1, count + 1)]},
                "context.document_graph": {"sections": []}}
        for role, doc in docs.items():
            blobs[role] = json.dumps(doc).encode()
        self.blobs.update(blobs)
        return docs, blobs

    def _wire(self, monkeypatch: pytest.MonkeyPatch, docs: dict[str, Any]) -> None:
        import auditmanager.analysis.public as public

        monkeypatch.setattr(runtime, "DocumentRepository", lambda: NS(get_version=lambda *_: NS(classification=NS(section_code="AR"), page_count=20)))
        monkeypatch.setattr(public, "read_artifact", lambda _store, bid, **_: (docs[str(bid)], "a" * 64))
        monkeypatch.setattr(runtime, "parse_blob_id", lambda x: x)

    def common(self, docs: dict[str, Any]) -> dict[str, Any]:
        return dict(authority=NS(), jobs=self.jobs, journal=self.journal, binding=self.binding,
                    outputs=NS(refs={k: NS(blob_id=k) for k in docs}), store=Store(self.blobs), meter=CostMeter(100.0),
                    publish=self.publish, progress=lambda status, value: self.saved.append((status, json.loads(json.dumps(value)))),
                    checkpoint=self.checkpoint, observations_document=None, snapshot_id=None, profile_sha256="p" * 64)

    def checkpoint(self, boundary: str) -> None:
        self.checkpoints.append(boundary)
        if self.stop_at_window is not None and boundary == "extended_v3_window" and self.checkpoints.count(boundary) > self.stop_at_window:
            raise Interrupted(boundary)

    def run_v2(self, monkeypatch: pytest.MonkeyPatch, blocks: int = 10) -> dict[str, Any]:
        """The accepted v2 plan: one flat loop, eight images a batch, no batch receipts."""
        self.checkpoints = []
        docs, _ = self.documents(blocks)
        self._wire(monkeypatch, docs)
        return runtime._run_workflow_v2(Session(), run=self.run, window_context=None, full_document=False, **self.common(docs))

    def run_v3_window(self, monkeypatch: pytest.MonkeyPatch, blocks: int = 10, *, repair: bool = False,
                      block_limit: int | None = None, parameter_context: bool = False) -> dict[str, Any]:
        """One v3 window under the batched coverage policy, stopped after its block analysis (``visual_only``): the production path."""
        self.checkpoints = []
        docs, _ = self.documents(blocks)
        self._wire(monkeypatch, docs)
        policy = {"enabled": True, "plan_version": "extended-review-v3", "max_blocks": 16, "window_size": 16, "max_windows": 1,
                  "text_page_limit": 16, "review": True, "review_scope": "full_document", "section_code": "AR",
                  "rules_sha256": extended_review_bundle_digest("AR"), **extended_coverage_policy(),
                  **({"completion_policy": "source-complete-v1", "semantic_repair_attempts": 1} if repair else {})}
        extra = {}
        if parameter_context:
            from auditmanager.analysis.public import project_parameter_context_policy, project_parameters_policy

            parameters = project_parameters_policy("AR", full_coverage=True, candidate_refusals=True)
            policy.update(project_parameters_policy=parameters, project_parameter_context_policy=project_parameter_context_policy(parameters))
            extra["project_parameters"] = {"policy": parameters, "status": "ready", "facts": [], "source_sha256": None, "manifest_sha256": None}
        if block_limit is not None:
            policy["phase_call_limits"] = {**policy["phase_call_limits"], "block_analysis": block_limit}
        window = {"window_id": "w001", "policy": policy, "offset": 0, "page_count": blocks, "global_sha256": "g" * 64,
                  "visual_only": True, "primary_text_status": "pending", **extra}
        return runtime._run_workflow_v2(Session(), run=self.run, window_context=window, full_document=False, **self.common(docs))

    def run_v3_run(self, monkeypatch: pytest.MonkeyPatch, blocks: int = 32, *, resume: dict[str, Any] | None = None) -> dict[str, Any]:
        """The whole v3 run of ``blocks`` images, sixteen a window, up to the end of its block analysis (``visual_only``, the first pass of
        production); ``resume`` is the state a previous attempt saved. This is the path that lends one breaker to every window."""
        self.checkpoints = []
        docs, _ = self.documents(blocks)
        self._wire(monkeypatch, docs)
        windows = (blocks + 15) // 16
        policy = {"enabled": True, "plan_version": "extended-review-v3", "max_blocks": 16 * windows, "window_size": 16, "max_windows": windows,
                  "text_page_limit": 16, "review": True, "review_scope": "full_document", "section_code": "AR",
                  "rules_sha256": extended_review_bundle_digest("AR"), **extended_coverage_policy()}
        kwargs = self.common(docs)
        kwargs["outputs"] = NS(refs={role: NS(blob_id=role, sha256=sha256(self.blobs[role]).hexdigest(), size_bytes=len(self.blobs[role]))
                                     for role in docs})
        return runtime._run_workflow_v3(Session(), run=self.run, policy=policy, resume_state=resume, visual_only=True, bind_native=None,
                                        **kwargs)

    def calls(self) -> list[str]:
        return [cell_key for cell_key, _ in self.log]


class Interrupted(Exception):
    """The attempt dies here. It is not a ``DomainError``, so no layer of the workflow turns it into a failed window."""


class Session:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def block_calls(harness: Harness) -> list[str]:
    return [key for key in harness.calls() if key.startswith("blocks")]


# --- the schemes and the sets ------------------------------------------------------------------------------------------------


def test_the_closed_list_of_block_schemes_is_exactly_the_two_ensembles_and_a_single_astra():
    assert [(s.scheme_id, s.cells) for s in layout.BLOCK_SCHEMES] == [
        ("claude_opus_judge_sonnet", (("leg1", OPUS, "medium"), ("judge", SONNET, "medium"))),
        ("codex_astra_sol_judge", (("leg1", ASTRA, "medium"), ("leg2", SOL, "medium"), ("judge", SOL61, "medium"))),
        ("codex_astra_single", (("main", ASTRA, "medium"),)),
    ]
    assert [s.legs for s in layout.BLOCK_SCHEMES] == [("leg1",), ("leg1", "leg2"), ("main",)]
    assert [s.is_ensemble for s in layout.BLOCK_SCHEMES] == [True, True, False]
    # a single Claude is on no scheme (the original forbids it); a single Astra is
    assert not any(s.cells[0][1].startswith("claude") and not s.is_ensemble for s in layout.BLOCK_SCHEMES)


def test_the_two_sets_carry_their_ensemble_and_the_flag_is_landed():
    assert layout.BLOCKS_ENSEMBLE_LANDED is True and layout.KIT_LABELS["claude_only"] == "Только Claude"
    assert layout.PRESET_CELLS["claude_only"]["blocks"] == layout.BLOCK_SCHEMES[0].cells
    assert layout.PRESET_CELLS["codex_only"]["blocks"] == layout.BLOCK_SCHEMES[1].cells
    assert [(c.cell_key, c.model_id, c.effort) for c in layout.preset_cells("claude_only") if c.row == "blocks"] == [
        ("blocks:leg1", OPUS, "medium"), ("blocks:judge", SONNET, "medium")]
    assert [(c.cell_key, c.model_id, c.effort) for c in layout.preset_cells("codex_only") if c.row == "blocks"] == [
        ("blocks:leg1", ASTRA, "medium"), ("blocks:leg2", SOL, "medium"), ("blocks:judge", SOL61, "medium")]


def test_the_role_of_a_call_identity_is_read_from_the_identity_and_a_repair_runs_on_the_cell_it_repairs():
    assert layout.role_of_phase("blocks:3:leg1") == "leg1" and layout.role_of_phase("blocks:3:judge:repair:1") == "judge"
    assert layout.role_of_phase("blocks:3:leg2") == "leg2"
    for identity in ("blocks:3", "blocks", "norm_verification:b002", "critic", "comprehensive:b001", "finding_review:b001:repair:1"):
        assert layout.role_of_phase(identity) == "main", identity
    assert layout.row_of_phase("blocks:3:leg1") == "blocks"


# --- the sequence of calls in a batch ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("kit,expected", [
    ("claude_only", ["blocks:leg1", "blocks:judge"]),
    ("codex_only", ["blocks:leg1", "blocks:leg2", "blocks:judge"]),
])
def test_each_batch_is_read_by_the_legs_in_order_and_then_by_the_judge_on_the_cells_of_the_plan(monkeypatch, kit, expected):
    harness = Harness(monkeypatch, kit=kit)
    result = harness.run_v2(monkeypatch, blocks=10)            # ten images: a batch of eight and a batch of two
    assert block_calls(harness) == expected * 2
    # the same block payload for every leg of a batch, and the judge reads the same sources and the legs' observations
    by_batch = [[json.loads(r.body["messages"][0]["content"]) for k, r in harness.log if k.startswith("blocks")][i:i + len(expected)]
                for i in (0, len(expected))]
    for payloads in by_batch:
        assert len({json.dumps(p["sources"], sort_keys=True) for p in payloads}) == 1
        assert payloads[-1]["procedure"] == "block_analysis_judge" and "legs" not in payloads[0]
    # every call is made on the adapter of its own cell, whose model it names
    for cell_key, request in harness.log:
        assert request.model_id == harness.plan.cell(cell_key).model_id
    assert [len(r.images_bytes) for k, r in harness.log if k.startswith("blocks")][:len(expected)] == [8] * len(expected)
    # one observation per leg per batch and the judge's pairing and gap observation stand beside them
    blocks = [o for o in result["observations"] if "provenance" in o]
    assert {o["provenance"]["origin"] for o in blocks} == {"leg", "gap_search"}
    assert result["coverage"]["blocks_processed"] == 10 and result["coverage"]["blocks_remaining"] == 0
    assert result["block_ensemble"]["cells"] == {c.role: c.model_id for c in harness.plan.cells if c.row == "blocks"}


def test_a_run_whose_blocks_row_is_one_model_calls_one_model_per_batch_as_before(monkeypatch):
    single = tuple(c for c in layout.preset_cells("codex_only") if c.row != "blocks") + (
        layout.CellSettings("blocks:main", ASTRA, "medium"),)
    harness = Harness(monkeypatch, kit="custom", cells=tuple(sorted(single, key=layout._position)))
    result = harness.run_v2(monkeypatch, blocks=10)
    assert block_calls(harness) == ["blocks:main"] * 2
    assert all("provenance" not in o for o in result["observations"]) and "block_ensemble" not in result


def test_a_run_without_a_plan_calls_one_model_per_batch_exactly_as_before(monkeypatch):
    harness = Harness(monkeypatch)
    harness.run = NS(run_id=RUN_ID, version_uid=VERSION, provider_mode="live")      # no stage_plan: the legacy route
    adapter = CellAdapter(layout.preset_cells("claude_only")[1], harness)
    harness.binding = NS(adapter=adapter, config=ProviderConfig(ProviderMode.RECORDED, OPUS, 20.0, None, False), call=None)
    harness.run_v2(monkeypatch, blocks=10)
    assert [k for k in harness.calls() if k == "blocks:leg1"] == ["blocks:leg1"] * 3, "two block batches and the comprehensive review"
    assert all("blocks:judge" not in k for k in harness.calls())


def test_the_v3_window_identities_carry_the_role_and_the_batch_receipt_keeps_each_call(monkeypatch):
    """The production path: batched coverage. ``kind:bNNN`` is widened to ``blocks:N:leg1`` and the call limit counts batches."""
    harness = Harness(monkeypatch, kit="codex_only")
    state = harness.run_v3_window(monkeypatch, blocks=10)
    assert block_calls(harness) == ["blocks:leg1", "blocks:leg2", "blocks:judge"] * 2
    batches = [b for b in state["batches"] if b["procedure"] == "block_analysis"]
    assert [b["index"] for b in batches] == [0, 1] and [b["status"] for b in batches] == ["completed", "completed"]
    for batch in batches:
        assert set(batch["cells"]) == {"leg1", "leg2", "judge"}
        assert {role: cell["cell"] for role, cell in batch["cells"].items()} == {r: f"blocks:{r}" for r in ("leg1", "leg2", "judge")}
        assert all(cell["status"] == "completed" and cell["attempts"] == 1 and cell["response_received"] for cell in batch["cells"].values())
        assert len({cell["request_sha256"] for cell in batch["cells"].values()}) == 3
        assert batch["reconciliation"]["status"] == "reviewed" and batch["reconciliation"]["mode"] == "compare_legs"
    coverage = state["phase_coverage"]["block_analysis"]
    assert (coverage["planned"], coverage["completed"], coverage["remaining"]) == (2, 2, 0), "coverage is in batches, not in calls"
    assert state["phase_call_counts"]["block_analysis"]["completed_calls"] == 6, "calls are counted one by one"
    procedures = {p["id"]: p["status"] for p in state["procedures"]}
    assert procedures["block_analysis"] == "completed"


def test_the_parameter_context_rides_on_every_block_request_of_the_ensemble_legs_and_judge_alike(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only")
    state = harness.run_v3_window(monkeypatch, blocks=8, parameter_context=True)
    assert block_calls(harness) == ["blocks:leg1", "blocks:leg2", "blocks:judge"]
    for cell_key, request in harness.log:
        payload = json.loads(request.body["messages"][0]["content"])
        assert payload["project_parameter_context"]["allowed_visual_source_ids"] == [s["source_id"] for s in payload["sources"]], cell_key
        assert "project_parameter_context" in request.body["system"]
    receipts = state["project_parameter_context_receipts"]
    assert sorted(receipts) == ["blocks:0:judge", "blocks:0:leg1", "blocks:0:leg2"], "one receipt per call, by its identity"
    assert all(r["request_prepared"] and r["response_received"] for r in receipts.values())
    assert len({r["request_sha256"] for r in receipts.values()}) == 3


def test_the_approved_call_limit_counts_batches_and_not_calls(monkeypatch):
    """One batch of an approved limit of one makes its three calls; the second batch is refused before any call."""
    harness = Harness(monkeypatch, kit="codex_only")
    state = harness.run_v3_window(monkeypatch, blocks=10, block_limit=1)
    assert block_calls(harness) == ["blocks:leg1", "blocks:leg2", "blocks:judge"]
    procedure = next(p for p in state["procedures"] if p["id"] == "block_analysis")
    assert (procedure["status"], procedure["reason"]) == ("failed", "approved_phase_call_limit")


# --- the idempotency keys, the journal, the cell bindings --------------------------------------------------------------------


def test_every_leg_and_the_judge_is_a_unit_of_its_own(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only")
    harness.run_v2(monkeypatch, blocks=8)
    phases = [phase for phase, _ in harness.unit_keys if "blocks" in phase]
    assert phases == ["v2:blocks:0:leg1", "v2:blocks:0:leg2", "v2:blocks:0:judge"]
    keys = [key for phase, key in harness.unit_keys if "blocks" in phase]
    assert len(set(keys)) == 3, "three calls, three idempotency keys"
    # the journal row of each names the row of the layout and the phase of the unit; the identity carries no host
    prepared = [p for p in harness.jobs.prepared if "blocks" in p["parameters"]["extended_phase"]]
    assert [p["parameters"]["extended_phase"] for p in prepared] == phases
    assert {p["stage_key"] for p in prepared} == {"blocks"} and {p["host_id"] for p in prepared} == {HOST}
    assert [p["model_identity"] for p in prepared] == [ASTRA, SOL, SOL61]
    assert [p["connection_revision_id"] for p in prepared] == [revision_of(f"blocks:{r}") for r in ("leg1", "leg2", "judge")]
    assert len({p["request_sha256"] for p in prepared}) == 3
    scopes = [r.idempotency_scope for k, r in harness.log if k.startswith("blocks")]
    assert len(set(scopes)) == 3, "the scope a transport may deduplicate on says the leg"
    assert [s.rsplit(":", 1)[-1] for s in scopes[:2]] == ["leg1", "leg2"]


def test_a_leg_that_reports_another_model_is_refused_by_its_own_cells_identity_check(monkeypatch):
    # leg1 is Astra; its host reports Sol (another cell's model): the call binding of the leg holds it to Astra
    harness = Harness(monkeypatch, kit="codex_only", reported=lambda cell: SOL if cell.cell_key == "blocks:leg1" else cell.model_id)
    state = harness.run_v2(monkeypatch, blocks=8)
    assert state["procedures"][0]["status"] == "failed", "the identity check (`R-133`) fails the workflow, never skips it"
    assert harness.calls() == ["blocks:leg1"], "the second leg and the judge are not asked after a refused identity"


# --- the retry policy of a leg ------------------------------------------------------------------------------------------------


def flaky(role_cell: str, klass: str, failures: int, base: Callable = default_answer):
    def answer(cell_key, request, nth):
        if cell_key == role_cell and nth <= failures:
            return dispatch_error(klass)
        return base(cell_key, request, nth)
    return answer


@pytest.mark.parametrize("klass", RETRY_CLASSES)
def test_a_leg_is_asked_again_for_the_four_classes_and_waits_thirty_seconds_between_asks(monkeypatch, klass):
    harness = Harness(monkeypatch, kit="codex_only", answer=flaky("blocks:leg2", klass, failures=2))
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls()[:5] == ["blocks:leg1", "blocks:leg2", "blocks:leg2", "blocks:leg2", "blocks:judge"]
    assert sum(harness.sleeps) == 60 and set(harness.sleeps) <= {5}, "two waits of thirty seconds, taken in slices a cancel can interrupt"
    assert harness.checkpoints.count("extended_leg_retry_wait") == 12
    batch = next(b for b in state["batches"] if b["procedure"] == "block_analysis")
    assert batch["status"] == "completed" and batch["cells"]["leg2"]["status"] == "completed" and batch["cells"]["leg2"]["attempts"] == 3
    assert "error_code" not in batch["cells"]["leg2"] and "error_code" not in batch, "an earlier failure of a retried unit is not its state"
    assert [e for e in harness.journal.events if e[0] == "not_processed"] == [("not_processed", klass)] * 2


def test_a_leg_is_retried_five_times_and_then_the_batch_is_partial_and_the_judge_works_with_the_leg_that_answered(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=flaky("blocks:leg2", "rate_limited", failures=99))
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls()[:8] == ["blocks:leg1"] + ["blocks:leg2"] * 6 + ["blocks:judge"], "one ask and five more, then the judge"
    assert sum(harness.sleeps) == 5 * 30
    batch = next(b for b in state["batches"] if b["procedure"] == "block_analysis")
    assert batch["status"] == "partial" and batch["reason"] == "block_ensemble_leg_failed"
    assert (batch["cells"]["leg2"]["status"], batch["cells"]["leg2"]["attempts"], batch["cells"]["leg2"]["dispatch_class"]) == ("failed", 6, "rate_limited")
    assert batch["cells"]["leg1"]["status"] == "completed" and batch["cells"]["judge"]["status"] == "completed"
    assert batch["reconciliation"]["failed_legs"] == ["leg2"] and batch["reconciliation"]["mode"] == "gap_search_only"
    judge = json.loads(next(r for k, r in harness.log if k == "blocks:judge").body["messages"][0]["content"])
    assert judge["legs_failed"] == ["leg2"] and [leg["leg"] for leg in judge["legs"]] == ["leg1"] and judge["mode"] == "gap_search_only"
    # the batch is not counted as covered, the procedure says why, and the artifact keeps what leg1 and the judge found
    assert state["coverage"]["blocks_remaining"] > 0
    assert next(p for p in state["procedures"] if p["id"] == "block_analysis")["status"] == "partial"
    assert next(p for p in state["procedures"] if p["id"] == "block_analysis")["reason"] == "block_ensemble_leg_failed"
    origins = [o["provenance"]["cell"] for o in state["observations"] if "provenance" in o]
    assert origins.count("blocks:leg1") >= 1 and "blocks:leg2" not in origins


def test_an_unknown_outcome_is_never_asked_again_and_the_fence_holds(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=flaky("blocks:leg1", "outcome_unknown", failures=99))
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls() == ["blocks:leg1"], "no second ask, no second leg, no judge: the provider may have processed the call"
    assert harness.sleeps == []
    assert harness.journal.events.count(("unknown", None)) == 1 and ("not_processed", "outcome_unknown") not in harness.journal.events
    assert next(p for p in state["procedures"] if p["id"] == "block_analysis")["status"] == "failed"


def test_an_unknown_outcome_on_the_second_leg_still_stops_the_batch_and_never_reaches_the_judge(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=flaky("blocks:leg2", "outcome_unknown", failures=99))
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls() == ["blocks:leg1", "blocks:leg2"]
    assert next(p for p in state["procedures"] if p["id"] == "block_analysis")["status"] == "failed"


def test_an_earlier_ambiguous_effect_fences_every_later_call_of_the_ensemble(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only")
    harness.ambiguous = True               # an earlier call of the run left an effect nobody can tell
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls() == [] and next(p for p in state["procedures"] if p["id"] == "block_analysis")["status"] == "failed"


@pytest.mark.parametrize("failure", [
    DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_budget_exceeded"),
    ValueError("not a dispatch"),
    dispatch_error("outcome_unknown"),
])
def test_only_the_four_classes_are_retried_whatever_else_fails(monkeypatch, failure):
    harness = Harness(monkeypatch, kit="claude_only", answer=lambda cell_key, request, nth: failure if cell_key == "blocks:leg1" else default_answer(cell_key, request, nth))
    harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls() == ["blocks:leg1"] and harness.sleeps == []


def test_every_failed_leg_fails_the_batch_as_a_failed_block_call_does_today(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only", answer=flaky("blocks:leg1", "not_sent", failures=99))
    state = harness.run_v3_window(monkeypatch, blocks=10)
    assert harness.calls() == ["blocks:leg1"] * 6, "the only leg is asked six times and the judge never runs"
    assert sum(harness.sleeps) == 150
    assert next(p for p in state["procedures"] if p["id"] == "block_analysis")["status"] == "failed"
    assert "blocks:judge" not in harness.calls()


def test_a_single_leg_failure_does_not_abort_the_stage_the_next_batch_is_read(monkeypatch):
    # the first batch's leg2 never answers; the second batch's does: the stage goes on (the original's ABORT_ON_LEG_FAILURE is off)
    def answer(cell_key, request, nth):
        if cell_key == "blocks:leg2" and nth <= 6:
            return dispatch_error("proxy_unavailable")
        return default_answer(cell_key, request, nth)
    harness = Harness(monkeypatch, kit="codex_only", answer=answer)
    state = harness.run_v3_window(monkeypatch, blocks=10)
    batches = {b["index"]: b for b in state["batches"] if b["procedure"] == "block_analysis"}
    assert (batches[0]["status"], batches[1]["status"]) == ("partial", "completed")
    assert harness.calls().count("blocks:judge") == 2 and harness.calls().count("blocks:leg1") == 2


def test_a_judge_that_cannot_be_reached_leaves_the_legs_observations_standing_unreviewed_and_the_batch_partial(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=flaky("blocks:judge", "rate_limited", failures=99))
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert harness.calls() == ["blocks:leg1", "blocks:leg2", "blocks:judge"], "the judge is asked once: the retry is the legs'"
    batch = next(b for b in state["batches"] if b["procedure"] == "block_analysis")
    assert batch["status"] == "partial" and batch["reason"] == "block_ensemble_judge_failed"
    assert batch["cells"]["judge"]["status"] == "failed" and batch["reconciliation"]["status"] == "unreviewed"
    legs = [o for o in state["observations"] if "provenance" in o]
    assert {o["provenance"]["relation"] for o in legs} == {"unreviewed"} and len(legs) == 2


def test_a_judge_that_fails_in_an_unknown_way_stops_the_workflow(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only", answer=flaky("blocks:judge", "outcome_unknown", failures=99))
    state = harness.run_v3_window(monkeypatch, blocks=8)
    assert next(p for p in state["procedures"] if p["id"] == "block_analysis")["status"] == "failed"
    assert harness.calls() == ["blocks:leg1", "blocks:judge"]


def test_a_refused_judge_reply_is_repaired_once_on_the_judge_cell_and_a_refused_leg_reply_on_the_leg_cell(monkeypatch):
    def answer(cell_key, request, nth):
        if cell_key == "blocks:leg1" and nth == 1:
            return json.dumps({"observations": [{"title": "x"}]})          # shape refused
        if cell_key == "blocks:judge" and nth == 1:
            return "not json"
        return default_answer(cell_key, request, nth)

    harness = Harness(monkeypatch, kit="claude_only", answer=answer)
    state = harness.run_v3_window(monkeypatch, blocks=8, repair=True)
    assert harness.calls() == ["blocks:leg1", "blocks:leg1", "blocks:judge", "blocks:judge"]
    phases = [phase for phase, _ in harness.unit_keys if "blocks" in phase]
    assert phases == ["v3:w001:blocks:0:leg1", "v3:w001:blocks:0:leg1:repair:1", "v3:w001:blocks:0:judge", "v3:w001:blocks:0:judge:repair:1"]
    batch = next(b for b in state["batches"] if b["procedure"] == "block_analysis")
    assert [a["cell"] for a in batch["repair_attempts"]] == ["blocks:leg1", "blocks:judge"] and batch["status"] == "completed"


# --- the per-run leg breaker (D-662) -----------------------------------------------------------------------------------------
#
# Batches are numbered across the run: eight images each, two to a window, so batch 2 is the first of window w001. A leg that fails
# is asked 1 + 5 times, 30 s apart (150 s a batch); the breaker exists so that a persistently failing leg stops costing that.


def batch_of(request: Any) -> int:
    return (json.loads(request.body["messages"][0]["content"])["sources"][0]["page_number"] - 1) // 8


def leg_fails(cell_key: str, batches: set[int] | None = None, klass: str = "rate_limited", base: Callable = default_answer):
    """``cell_key`` fails with ``klass`` on the given batches of the run (on every batch when ``None``)."""
    def answer(key, request, nth):
        if key == cell_key and (batches is None or batch_of(request) in batches):
            return dispatch_error(klass)
        return base(key, request, nth)
    return answer


def block_batches(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [b for b in state["batches"] if b["procedure"] == "block_analysis"]


def asked(harness: Harness, cell_key: str) -> dict[int, int]:
    return dict(Counter(batch_of(r) for k, r in harness.log if k == cell_key))


def breaker_of(state: dict[str, Any]) -> dict[str, Any]:
    return state["block_ensemble"]["breaker"]["legs"]


def breaker_doc(role: str = "leg1", model: str = ASTRA, streak=((16, 0), (16, 1), (32, 0)), frm=(16, 0), at=(32, 0)) -> dict[str, Any]:
    return {"format": "block-leg-breaker/1", "legs": {role: {"model_id": model, "streak": [list(p) for p in streak], "open": {
        "model_id": model, "consecutive": len(streak), "from": list(frm), "at": list(at), "batch": "w002:blocks:0"}}}}


def resumed_with(saved: dict[str, Any], breaker: dict[str, Any]) -> dict[str, Any]:
    state = deepcopy(saved)
    state["block_ensemble"] = {"breaker": breaker}
    return state


def test_the_breaker_threshold_is_three_batches():
    assert runtime.LEG_BREAKER_CONSECUTIVE_BATCHES == 3


def test_the_breaker_opens_after_three_consecutive_failed_batches_and_the_fourth_asks_only_the_other_leg(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1"))
    state = harness.run_v3_run(monkeypatch, blocks=32)                 # two windows, four batches
    assert asked(harness, "blocks:leg1") == {0: 6, 1: 6, 2: 6}, "three batches pay their five retries; the fourth does not ask the leg"
    assert asked(harness, "blocks:leg2") == {0: 1, 1: 1, 2: 1, 3: 1} and asked(harness, "blocks:judge") == {0: 1, 1: 1, 2: 1, 3: 1}
    assert sum(harness.sleeps) == 3 * 150, "the fourth batch waits for nothing"
    batches = block_batches(state)
    assert [b["status"] for b in batches] == ["partial"] * 4
    assert [b["reason"] for b in batches] == ["block_ensemble_leg_failed"] * 3 + ["block_ensemble_leg_skipped"]
    # the fourth batch: leg1 is named skipped and made no call, leg2 and the judge answered, the judge only searched for gaps
    fourth = batches[3]
    assert fourth["cells"]["leg1"] == {"cell": "blocks:leg1", "status": "skipped", "attempts": 0, "reason": "block_ensemble_leg_breaker_open"}
    assert fourth["cells"]["leg2"]["status"] == "completed" and fourth["cells"]["judge"]["status"] == "completed"
    assert fourth["reconciliation"]["skipped_legs"] == ["leg1"] and fourth["reconciliation"]["failed_legs"] == []
    assert fourth["reconciliation"]["mode"] == "gap_search_only"
    judge = json.loads([r for k, r in harness.log if k == "blocks:judge"][3].body["messages"][0]["content"])
    assert judge["legs_failed"] == ["leg1"] and [leg["leg"] for leg in judge["legs"]] == ["leg2"] and judge["mode"] == "gap_search_only"
    # coverage and the call counts stay honest: a skipped leg is not a call, and a batch that lost a leg is not covered
    phases = [p["parameters"]["extended_phase"] for p in harness.jobs.prepared]
    assert "v3:w001:blocks:1:leg1" not in phases and "v3:w001:blocks:1:leg2" in phases
    assert state["phase_call_counts"]["block_analysis"]["completed_calls"] == 8
    assert state["coverage"]["blocks_processed"] == 0 and state["coverage"]["blocks_remaining"] == 32
    # journalled once, on the batch that opened it, and kept in the run's saved state
    event = batches[2]["reconciliation"]["leg_breaker"]
    assert event == {"leg": "leg1", "model_id": ASTRA, "consecutive": 3, "from": [0, 0], "at": [16, 0], "batch": "w001:blocks:0"}
    assert ["leg_breaker" in b["reconciliation"] for b in batches] == [False, False, True, False]
    saved = harness.saved[-1][1]
    assert saved["block_ensemble"]["breaker"]["legs"]["leg1"]["open"] == {k: v for k, v in event.items() if k != "leg"}
    assert "leg2" not in breaker_of(saved)


def test_a_success_in_between_resets_the_count(monkeypatch):
    # fails on batches 0 and 1, answers batch 2, fails on 3, 4 and 5: the count restarts at 2, so it opens on 5 and not on 3
    harness = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1", {0, 1, 3, 4, 5}))
    state = harness.run_v3_run(monkeypatch, blocks=64)                 # four windows, eight batches
    assert asked(harness, "blocks:leg1") == {0: 6, 1: 6, 2: 1, 3: 6, 4: 6, 5: 6}, "batches 6 and 7 are not asked; 4 and 5 still are"
    batches = block_batches(state)
    assert [b.get("reason") for b in batches] == ["block_ensemble_leg_failed"] * 2 + [None] + ["block_ensemble_leg_failed"] * 3 + [
        "block_ensemble_leg_skipped"] * 2
    assert batches[5]["reconciliation"]["leg_breaker"] == {"leg": "leg1", "model_id": ASTRA, "consecutive": 3, "from": [16, 1], "at": [32, 1],
                                                           "batch": "w002:blocks:1"}
    assert sum(harness.sleeps) == 5 * 150


def test_an_unknown_outcome_never_opens_the_breaker_and_is_not_counted(monkeypatch):
    def answer(key, request, nth):
        if key == "blocks:leg1" and batch_of(request) == 2:
            return dispatch_error("outcome_unknown")
        return leg_fails("blocks:leg1", {0, 1, 4})(key, request, nth)

    harness = Harness(monkeypatch, kit="codex_only", answer=answer)
    state = harness.run_v3_run(monkeypatch, blocks=48)                 # three windows
    # batch 2 is the unknown outcome: asked once, never again, no judge, its window failed. It is neither a failure to count nor a success
    # to reset on: the third retryable failure is batch 4, and the breaker opens there, not before
    assert asked(harness, "blocks:leg1") == {0: 6, 1: 6, 2: 1, 4: 6}
    assert 2 not in asked(harness, "blocks:judge") and harness.journal.events.count(("unknown", None)) == 1
    assert next(p for p in state["windows"][1]["procedures"] if p["id"] == "block_analysis")["status"] == "failed"
    assert breaker_of(state)["leg1"]["open"] == {"model_id": ASTRA, "consecutive": 3, "from": [0, 0], "at": [32, 0], "batch": "w002:blocks:0"}
    assert sum(harness.sleeps) == 3 * 150


def test_a_leg_that_only_ever_fails_with_an_unknown_outcome_is_asked_in_every_window(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1", klass="outcome_unknown"))
    state = harness.run_v3_run(monkeypatch, blocks=64)
    assert asked(harness, "blocks:leg1") == {0: 1, 2: 1, 4: 1, 6: 1}, "one ask a window, the first batch of each, never retried and never skipped"
    assert harness.sleeps == [] and "block_ensemble" not in state


def test_when_the_other_leg_trips_too_the_last_error_propagates_and_the_window_fails_as_today(monkeypatch):
    # leg1 fails everywhere and opens on batch 2; leg2 then fails on every batch from 3 on, with nobody left to answer
    harness = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg2", {3, 4, 5}, base=leg_fails("blocks:leg1")))
    state = harness.run_v3_run(monkeypatch, blocks=48)
    assert asked(harness, "blocks:leg1") == {0: 6, 1: 6, 2: 6}
    assert asked(harness, "blocks:leg2") == {0: 1, 1: 1, 2: 1, 3: 6, 4: 6}, "the surviving leg keeps its retries; the breaker does not open on it"
    assert asked(harness, "blocks:judge") == {0: 1, 1: 1, 2: 1}, "a batch no leg answered has no judge"
    failed = [(w["window_id"], next(p for p in w["procedures"] if p["id"] == "block_analysis")["status"]) for w in state["windows"]]
    assert failed == [("w000", "partial"), ("w001", "failed"), ("w002", "failed")]
    third = next(b for b in block_batches(state) if b["index"] == 1 and b["window_id"] == "w001")
    assert third["cells"]["leg1"]["status"] == "skipped" and third["cells"]["leg2"]["status"] == "failed" and third["cells"]["leg2"]["attempts"] == 6
    assert set(breaker_of(state)) == {"leg1"}, "no state for the leg that was never silenced"


def test_a_batch_in_which_every_leg_failed_counts_for_no_leg(monkeypatch):
    harness = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg2", base=leg_fails("blocks:leg1")))
    state = harness.run_v3_run(monkeypatch, blocks=48)
    assert asked(harness, "blocks:leg1") == asked(harness, "blocks:leg2") == {0: 6, 2: 6, 4: 6}, "the first batch of each window, nothing skipped"
    assert "block_ensemble" not in state, "no leg answered, so nothing says either of them is the bad one"
    assert {n for n in asked(harness, "blocks:judge")} == set()


def test_a_run_with_one_leg_never_opens_it_and_never_silences_it(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only", answer=leg_fails("blocks:leg1"))
    state = harness.run_v3_run(monkeypatch, blocks=48)
    assert asked(harness, "blocks:leg1") == {0: 6, 2: 6, 4: 6} and "block_ensemble" not in state
    # a saved breaker that names the only leg open does not silence it
    healthy = Harness(monkeypatch, kit="claude_only")
    healthy.run_v3_run(monkeypatch, blocks=32)
    resumed = Harness(monkeypatch, kit="claude_only")
    resumed.run_v3_run(monkeypatch, blocks=32, resume=resumed_with(healthy.saved[-1][1], breaker_doc(model=OPUS, frm=(0, 0), at=(0, 1))))
    assert asked(resumed, "blocks:leg1") == {0: 1, 1: 1, 2: 1, 3: 1}


def test_a_resumed_attempt_keeps_the_open_breaker_and_never_asks_the_leg_again(monkeypatch):
    first = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1"))
    first.run_v3_run(monkeypatch, blocks=32)
    saved = first.saved[-1][1]
    assert breaker_of(saved)["leg1"]["open"] is not None
    second = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1"))
    state = second.run_v3_run(monkeypatch, blocks=32, resume=json.loads(json.dumps(saved)))
    assert "blocks:leg1" not in second.calls() and second.sleeps == [], "no ask and no wait: the state came with the resume"
    assert asked(second, "blocks:leg2") == {0: 1, 1: 1, 2: 1, 3: 1}
    assert [b["reason"] for b in block_batches(state)] == ["block_ensemble_leg_skipped"] * 4
    assert breaker_of(state) == breaker_of(saved), "and it is handed on to the next pass"


def test_a_batch_is_counted_once_however_often_a_resumed_attempt_runs_it_again(monkeypatch):
    first = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1"))
    first.stop_at_window = 1                                           # the attempt dies as the second window is about to start
    with pytest.raises(Interrupted):
        first.run_v3_run(monkeypatch, blocks=32)
    saved = first.saved[-1][1]
    assert breaker_of(saved)["leg1"]["streak"] == [[0, 0], [0, 1]] and breaker_of(saved)["leg1"]["open"] is None
    second = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1"))
    state = second.run_v3_run(monkeypatch, blocks=32, resume=json.loads(json.dumps(saved)))
    # the first window runs again and fails its two batches again: they are the same two, so the breaker opens on the third batch, as in
    # an attempt that was never interrupted, and not on the first one it meets
    assert asked(second, "blocks:leg1") == {0: 6, 1: 6, 2: 6}
    assert breaker_of(state)["leg1"]["open"] == {"model_id": ASTRA, "consecutive": 3, "from": [0, 0], "at": [16, 0], "batch": "w001:blocks:0"}


def test_a_window_run_again_before_the_streak_keeps_the_reply_its_leg_already_gave(monkeypatch):
    healthy = Harness(monkeypatch, kit="codex_only")
    healthy.run_v3_run(monkeypatch, blocks=32)
    resumed = Harness(monkeypatch, kit="codex_only")
    state = resumed.run_v3_run(monkeypatch, blocks=32, resume=resumed_with(healthy.saved[-1][1], breaker_doc(frm=(16, 0), at=(32, 0))))
    assert asked(resumed, "blocks:leg1") == {0: 1, 1: 1}, "batches 0 and 1 are before the first failure of the streak: asked, and answered"
    assert [b.get("reason") for b in block_batches(state)] == [None, None, "block_ensemble_leg_skipped", "block_ensemble_leg_skipped"]


def test_a_saved_breaker_of_another_model_is_not_honoured(monkeypatch):
    healthy = Harness(monkeypatch, kit="codex_only")
    healthy.run_v3_run(monkeypatch, blocks=32)
    resumed = Harness(monkeypatch, kit="codex_only")
    resumed.run_v3_run(monkeypatch, blocks=32, resume=resumed_with(healthy.saved[-1][1], breaker_doc(model="gpt-6-old", frm=(0, 0), at=(0, 1))))
    assert asked(resumed, "blocks:leg1") == {0: 1, 1: 1, 2: 1, 3: 1}


@pytest.mark.parametrize("saved", [
    breaker_doc("leg1") | {"legs": breaker_doc("leg1")["legs"] | breaker_doc("leg2", model=SOL)["legs"]},   # both legs open
    {"format": "block-leg-breaker/0", "legs": {}},
    {"format": "block-leg-breaker/1", "legs": {"judge": {"model_id": SOL61, "streak": [], "open": None}}},
    {"format": "block-leg-breaker/1", "legs": {"leg1": {"model_id": ASTRA, "streak": [[0]], "open": None}}},
    {"format": "block-leg-breaker/1", "legs": {"leg1": {"model_id": ASTRA, "streak": [], "open": None, "extra": 1}}},
    {"format": "block-leg-breaker/1", "legs": []},
    {"format": "block-leg-breaker/1", "legs": {}, "extra": 1},
    "open",
    {},
])
def test_a_saved_breaker_that_cannot_be_trusted_is_dropped_loudly_and_the_legs_are_asked_again(monkeypatch, saved):
    assert runtime._restore_breaker(saved) == ({"format": "block-leg-breaker/1", "legs": {}}, False)
    healthy = Harness(monkeypatch, kit="codex_only")
    healthy.run_v3_run(monkeypatch, blocks=32)
    resumed = Harness(monkeypatch, kit="codex_only")
    state = resumed.run_v3_run(monkeypatch, blocks=32, resume=resumed_with(healthy.saved[-1][1], saved))
    assert "block_ensemble_breaker_state_invalid" in state["warnings"]
    assert asked(resumed, "blocks:leg1") == {0: 1, 1: 1, 2: 1, 3: 1} and asked(resumed, "blocks:leg2") == {0: 1, 1: 1, 2: 1, 3: 1}


def test_a_trustworthy_saved_breaker_is_restored_as_it_was_and_nothing_saved_is_an_empty_one():
    assert runtime._restore_breaker(None) == ({"format": "block-leg-breaker/1", "legs": {}}, True)
    saved = breaker_doc()
    restored, valid = runtime._restore_breaker(saved)
    assert valid and restored == saved and restored is not saved and restored["legs"]["leg1"] is not saved["legs"]["leg1"]


def test_a_run_without_windows_keeps_the_breaker_beside_its_batches(monkeypatch):
    monkeypatch.setattr(runtime, "LEG_BREAKER_CONSECUTIVE_BATCHES", 1)
    harness = Harness(monkeypatch, kit="codex_only", answer=leg_fails("blocks:leg1"))
    result = harness.run_v2(monkeypatch, blocks=10)
    assert asked(harness, "blocks:leg1") == {0: 6}, "the second batch does not ask the leg"
    ensemble = result["block_ensemble"]
    assert ensemble["batches"][0]["leg_breaker"]["batch"] == "v2:blocks:0" and ensemble["batches"][1]["skipped_legs"] == ["leg1"]
    assert ensemble["breaker"]["legs"]["leg1"]["open"]["consecutive"] == 1
    procedure = next(p for p in result["procedures"] if p["id"] == "block_analysis")
    assert (procedure["status"], procedure["reason"]) == ("partial", "block_ensemble_leg_failed")


# --- the judge: request, reply, reconciliation -------------------------------------------------------------------------------

SOURCES = [{"source_id": "s1", "page_number": 1}, {"source_id": "s2", "page_number": 2}]
PAYLOAD = {"section": "AR", "sources": SOURCES, "page_contexts": [], "context_sections": [], "coverage": {}}
LEG1 = [observation("s1", "Лист 1: марка", "Марка П-1 не совпадает с ведомостью"), observation("s2", "Лист 2: отметка", "Отметка 3.300 против 3.000")]
LEG2 = [observation("s1", "Лист 1: марка П-1", "Марка П-1 не совпадает с ведомостью, указан иной типоразмер"), observation("s2", "Лист 2: дверь", "Нет двери Д-4")]


def judge_reply(**more):
    document = {"relationships": [], "gap_observations": [], "gap_search": {"performed": True, "status": "no_new_findings",
                                                                          "searched_categories": [], "summary": ""}}
    document.update(more)
    return json.dumps(document, ensure_ascii=False)


def refs():
    return block_leg_refs({"leg1": LEG1, "leg2": LEG2})


def test_the_judge_request_carries_the_batch_the_legs_observations_and_our_schema_and_rules():
    request = build_block_judge_request(model_id=SONNET, run_id="run", section="AR", payload=PAYLOAD, legs={"leg1": LEG1, "leg2": LEG2})
    body = json.loads(request.body["messages"][0]["content"])
    assert body["sources"] == SOURCES and body["mode"] == "compare_legs" and body["gap_search_enabled"] is True
    assert [leg["leg"] for leg in body["legs"]] == ["leg1", "leg2"] and body["legs"][0]["observations"][0]["ref"] == "leg1:001"
    assert request.body["model"] == SONNET and request.body["output_config"]["format"]["type"] == "json_schema"
    schema = request.body["output_config"]["format"]["schema"]
    assert schema["required"] == ["relationships", "gap_observations", "gap_search"]
    assert schema["properties"]["gap_observations"]["items"]["properties"]["source_ids"]["items"]["enum"] == ["s1", "s2"]
    assert schema["properties"]["relationships"]["items"]["properties"]["left_ref"]["enum"] == ["leg1:001", "leg1:002"]
    assert "НЕЗАВИСИМЫХ" in request.body["system"] and "match" in request.body["system"] and "НОВЫЕ" in request.body["system"]
    single = build_block_judge_request(model_id=SONNET, run_id="run", section="AR", payload=PAYLOAD, legs={"leg1": LEG1}, failed_legs=["leg2"])
    one = json.loads(single.body["messages"][0]["content"])
    assert one["mode"] == "gap_search_only" and one["legs_failed"] == ["leg2"] and "Сравнивать не с чем" in single.body["system"]
    assert single.body["output_config"]["format"]["schema"]["properties"]["relationships"]["maxItems"] == 0
    with pytest.raises(ValueError):
        build_block_judge_request(model_id=SONNET, run_id="run", section="AR", payload=PAYLOAD, legs={})
    # a v3 request carries the frozen rules digest and the section rubric, as every v3 block request does
    v3 = build_block_judge_request(model_id=SONNET, run_id="run", section="AR", payload=PAYLOAD, legs={"leg1": LEG1}, window_id="w001")
    assert json.loads(v3.body["messages"][0]["content"])["rules_sha256"] == extended_review_bundle_digest("AR") and len(v3.body["system"]) > len(single.body["system"])


def test_the_judge_prompt_is_in_the_rules_bundle_so_changing_it_asks_for_a_new_consent(monkeypatch):
    from pathlib import Path
    import auditmanager.analysis.extended.workflow as workflow

    before = extended_review_bundle_digest("AR")
    module = Path(workflow.__file__).with_name("block_ensemble.py")
    original = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: original(self) + b"#" if self == module else original(self))
    assert extended_review_bundle_digest("AR") != before


def test_the_judge_reply_is_parsed_into_relationships_gap_observations_and_the_gap_search_and_nothing_else():
    reply = judge_reply(
        relationships=[{"left_ref": "leg1:001", "right_ref": "leg2:001", "relation": "extension", "extends": "right", "confidence": 1.7, "reason": "  тот   же узел "}],
        gap_observations=[observation("s2", "Новое", "Другая проблема")],
        gap_search={"performed": True, "status": "gaps_found", "searched_categories": ["марки", " "], "summary": "ok"})
    records = parse_block_judge_reply(reply, allowed_sources={"s1", "s2"}, refs=refs())
    assert [r["kind"] for r in records] == ["relationship", "gap", "gap_search"]
    assert records[0]["confidence"] == 1.0 and records[0]["reason"] == "тот же узел" and records[0]["extends"] == "right"
    assert records[2]["searched_categories"] == ["марки"]
    for broken in ("{}", "[]", "not json", judge_reply(extra=1), json.dumps({"relationships": {}, "gap_observations": [], "gap_search": {}})):
        with pytest.raises(ValueError):
            parse_block_judge_reply(broken, allowed_sources={"s1"}, refs=refs())


def test_a_refused_record_is_kept_for_the_repair_and_the_valid_ones_survive():
    rejected: list[dict] = []
    reply = judge_reply(
        relationships=[{"left_ref": "leg2:001", "right_ref": "leg1:001", "relation": "match", "extends": "none", "confidence": 1, "reason": ""},   # sides swapped
                       {"left_ref": "leg1:001", "right_ref": "leg2:001", "relation": "match", "extends": "none", "confidence": 1, "reason": ""},
                       {"left_ref": "leg1:001", "right_ref": "leg2:002", "relation": "match", "extends": "none", "confidence": 1, "reason": ""}],  # leg1:001 used
        gap_observations=[observation("elsewhere", "Чужой источник"), observation("s1", "Свой источник")])
    records = parse_block_judge_reply(reply, allowed_sources={"s1", "s2"}, refs=refs(), rejected=rejected)
    assert [(r["section"], r["reason"]) for r in rejected] == [("relationships", "judge_relationship_invalid")] * 2 + [
        ("gap_observations", "observation_sources_or_limits_invalid")]
    assert [r["kind"] for r in records] == ["relationship", "gap", "gap_search"]


def test_with_one_leg_there_is_nothing_to_compare_and_any_relationship_the_judge_invents_is_ignored():
    reply = judge_reply(relationships=[{"left_ref": "leg1:001", "right_ref": "leg2:001", "relation": "match", "extends": "none", "confidence": 1, "reason": ""}])
    records = parse_block_judge_reply(reply, allowed_sources={"s1"}, refs=block_leg_refs({"leg1": LEG1}))
    assert [r["kind"] for r in records] == ["gap_search"]


def test_the_judge_never_rewrites_or_removes_a_leg_observation_and_every_one_says_who_found_it():
    records = parse_block_judge_reply(judge_reply(
        relationships=[{"left_ref": "leg1:001", "right_ref": "leg2:001", "relation": "extension", "extends": "right", "confidence": 0.9, "reason": "то же"},
                       {"left_ref": "leg1:002", "right_ref": "leg2:002", "relation": "disputed", "extends": "none", "confidence": 0.4, "reason": "разные отметки"}],
        gap_observations=[observation("s2", "Заполнение проёма", "Не указан класс огнестойкости")]), allowed_sources={"s1", "s2"}, refs=refs())
    items, report = reconcile_block_batch(batch="blocks:0", legs={"leg1": LEG1, "leg2": LEG2},
                                          cells={"leg1": ASTRA, "leg2": SOL, "judge": SOL61}, judge=records, sources=SOURCES)
    legs = [{k: v for k, v in i.items() if k != "provenance"} for i in items if i["provenance"]["origin"] == "leg"]
    assert legs == [*LEG1, *LEG2], "every leg observation, verbatim, in the legs' order"
    notes = {i["provenance"]["ref"]: i["provenance"] for i in items}
    assert (notes["leg1:001"]["relation"], notes["leg1:001"]["role"], notes["leg1:001"]["counterpart_refs"]) == ("extension", "base", ["leg2:001"])
    assert (notes["leg2:001"]["relation"], notes["leg2:001"]["role"]) == ("extension", "extends")
    assert notes["leg1:002"]["relation"] == notes["leg2:002"]["relation"] == "disputed"
    assert notes["gap:001"]["origin"] == "gap_search" and notes["gap:001"]["cell"] == "blocks:judge" and notes["gap:001"]["model_id"] == SOL61
    assert notes["leg1:001"]["cell"] == "blocks:leg1" and notes["leg2:001"]["model_id"] == SOL
    assert report["counts"] == {"matches": 0, "extensions": 1, "disputed": 1, "new": 1, "gap_observations": 1}
    assert report["gap_search"]["observations_added"] == 1 and report["status"] == "reviewed"


def test_a_gap_observation_that_repeats_a_leg_is_dropped_and_counted_and_the_gap_list_is_bounded():
    repeat = observation("s1", "Лист 1: марка П-1", "Марка П-1 не совпадает с ведомостью, указан иной типоразмер")      # a leg's own words
    topics = ["Воздуховод пересекает несущую балку", "Кабельный лоток без заземления", "Не указана марка бетона фундамента",
              "Клапан дымоудаления на плане отсутствует в спецификации", "Диаметр стояка отопления изменён между листами",
              "Уклон канализации менее нормативного", "Отметка пола не совпадает с разрезом", "Нет сечения кабеля питающей линии",
              "Класс пожарной опасности стен не указан", "Узел примыкания кровли не раскрыт"]
    fresh = [observation("s2", topic, f"Описание {index}: {topic.lower()} требует проверки по смежному разделу") for index, topic in enumerate(topics)]
    records = parse_block_judge_reply(judge_reply(gap_observations=[repeat, *fresh[:10]]), allowed_sources={"s1", "s2"}, refs=refs())
    items, report = reconcile_block_batch(batch="blocks:0", legs={"leg1": LEG1, "leg2": LEG2}, cells={"leg1": ASTRA, "leg2": SOL, "judge": SOL61},
                                          judge=records, sources=SOURCES)
    assert report["gap_search"]["duplicates_rejected"] == 1
    assert report["gap_search"]["observations_added"] == len(items) - 4 == 10 - report["gap_search"]["over_limit_dropped"]
    one_block = [SOURCES[0]]       # five a block: a single image allows five new observations
    items, report = reconcile_block_batch(batch="blocks:0", legs={"leg1": LEG1}, cells={"leg1": OPUS, "judge": SONNET}, sources=one_block,
        judge=parse_block_judge_reply(judge_reply(gap_observations=fresh[:10]), allowed_sources={"s1", "s2"}, refs=block_leg_refs({"leg1": LEG1})))
    assert report["gap_search"]["observations_added"] == 5 and report["gap_search"]["over_limit_dropped"] == 5, "dropped and counted, not silent"


def test_without_a_judge_the_legs_stand_unreviewed_and_nothing_is_dropped():
    items, report = reconcile_block_batch(batch="blocks:1", legs={"leg1": LEG1}, cells={"leg1": OPUS, "judge": SONNET}, judge=None, sources=SOURCES)
    assert [i["provenance"]["relation"] for i in items] == ["unreviewed", "unreviewed"] and report["status"] == "unreviewed"
    assert report["gap_search"]["performed"] is False and report["gap_search"]["status"] == "unreviewed"
