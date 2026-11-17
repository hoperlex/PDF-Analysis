"""`RUN-RESTART-01`: a restart takes the replies of the chips before its own from the source chain and makes no call for them.

The v2 workflow is run twice on in-memory fakes. The first pass is the **source**: every call is made and journalled, and its replies are kept as
the ``model_call`` rows a database would hold. The second pass is the **restart**: another run id, the same inputs, a ``RestartSpec`` naming the
source as its ancestor. What is measured:

* the boundary is the call identity: the calls of the rows before the restart point are replayed (the adapter is never asked), the calls of the
  point's own row and every later one are made and **never look in the chain**, even when the chain holds a reply for them;
* a call that cannot be replayed is refused, not made -- ``restart_reply_missing`` when no run of the chain answered the phase,
  ``restart_request_changed`` when one answered it for another request -- by an exception that is **not** a ``DomainError``: the workflow catches every
  ``DomainError`` and saves a partial result, which the evidence gate would still publish;
* a run that is no restart is unchanged: the chain is not consulted.
"""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace as NS

import pytest

import auditmanager.analysis.public as public
from auditmanager.analysis.public import CostMeter, ProviderConfig, ProviderMode
from auditmanager.jobs import public as jobs_public
from auditmanager.runs import extended_review as runtime
from auditmanager.runs.restart import (
    REASON_REPLY_MISSING, REASON_REQUEST_CHANGED, RESTART_POINTS, RestartRefused, RestartSpec, replay_rows,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.analysis_extended.test_core import VERSION, documents
from tests.unit.analysis_extended.test_runtime import Journal, Jobs, Session, Store
from tests.unit.analysis_extended.test_workflow_runtime import WorkflowAdapter

POLICY = {"enabled": True, "max_blocks": 16, "plan_version": "extended-review-v2"}
#: The call identities one pass makes with the norms corpus on: two block batches (ten images, eight to a batch), the cross-check, the norms.
IDENTITIES = ["v2:blocks:0", "v2:blocks:1", "v2:comprehensive", "v2:norm_verification"]
ROW_OF = {"v2:blocks:0": "blocks", "v2:blocks:1": "blocks", "v2:comprehensive": "cross_check", "v2:norm_verification": "norms"}


def _row(record) -> dict:
    return {"model_call_id": str(record.model_call_id), "provider": record.provider, "model_identity": record.model_id,
            "provider_mode": record.provider_mode.value, "parameters": dict(record.parameters), "request_sha256": record.request_sha256,
            "response_sha256": record.response_sha256, "input_tokens": record.input_tokens, "output_tokens": record.output_tokens,
            "latency_ms": record.latency_ms, "cost_micros": 0, "cost_basis": "measured", "status": record.status}


class Pass:
    """One run of the v2 workflow on fakes; ``chain`` is what the source chain holds (``unit_key -> model_call row``)."""

    def __init__(self, monkeypatch, *, run_id: str, restart: RestartSpec | None = None, chain: dict | None = None,
                 raise_domain_error_for_replay: bool = False, store: dict | None = None) -> None:
        portal, manifest, blobs = documents(10)
        blobs.update(store or {})  # the object store is shared by the runs of a chain: a reply the source published is readable by its restart
        self.docs = {"geometry.portal_blocks": portal, "geometry.page_crops": manifest,
                     "prepared.text_layer": {"pages": [{"page_number": i, "text": "Настоящий текст страницы"} for i in range(1, 11)]},
                     "context.document_graph": {"sections": []}}
        for role, doc in self.docs.items():
            blobs[role] = json.dumps(doc).encode()
        self.blobs = blobs
        self.run_id, self.restart, self.chain = run_id, restart, chain or {}
        monkeypatch.setattr(runtime, "DocumentRepository", lambda: NS(get_version=lambda *_: NS(classification=NS(section_code="AR"))))
        monkeypatch.setattr(public, "read_artifact", lambda _store, bid, **_: (self.docs[str(bid)], "a" * 64))
        monkeypatch.setattr(runtime, "parse_blob_id", lambda x: x)
        monkeypatch.setattr(runtime, "extended_unit", lambda *_args, **_kw: None)  # the run's own rows: none, in both passes
        monkeypatch.setattr(runtime, "search_norms", lambda _session, **kwargs: NS(items=(NS(
            norms_snapshot_id="snapshot", norm_document_id="doc", norm_paragraph_id="paragraph", designation="СП", clause_number="1",
            fragment=NS(text="Реальная цитата"), page_label=1),)))
        self.consulted: list[str] = []
        monkeypatch.setattr(jobs_public, "extended_unit_in_chain", self._in_chain)
        monkeypatch.setattr(jobs_public, "extended_phase_in_chain", self._phase_in_chain)
        if raise_domain_error_for_replay:
            def no_replay(session, *, restart, chip, phase):
                raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="restart_reply_missing")
            monkeypatch.setattr(runtime, "_no_replay", no_replay)
        self.adapter = WorkflowAdapter()
        self.journal = Journal()
        self.saved: list = []
        self.boundaries: list[str] = []

    def _in_chain(self, session, *, run_ids, unit_key):
        self.consulted.append(unit_key)
        assert tuple(run_ids) == self.restart.ancestors
        return deepcopy(self.chain.get(unit_key))

    def _phase_in_chain(self, session, *, run_ids, phase):
        return any(row["parameters"].get("extended_phase") == phase for row in self.chain.values())

    def run(self):
        blobs = self.blobs

        def publish(role, doc):
            raw = json.dumps(doc).encode()
            key = "reply" + str(len(blobs))
            blobs[key] = raw
            return NS(blob_id=key, sha256=sha256(raw).hexdigest(), size_bytes=len(raw))

        def checkpoint(boundary):
            self.boundaries.append(boundary)

        return runtime.run_extended_review(
            Session(), run=NS(run_id=self.run_id, version_uid=VERSION), authority=NS(), jobs=Jobs(), journal=self.journal,
            binding=NS(adapter=self.adapter, config=ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 20., None, False), call=None),
            outputs=NS(refs={**{k: NS(blob_id=k) for k in self.docs}, "source.document": NS(blob_id="source")}), store=Store(blobs),
            meter=CostMeter(20.), publish=publish,
            progress=lambda status, value: self.saved.append((status, json.loads(json.dumps(value)))), checkpoint=checkpoint,
            observations_document=None, snapshot_id="snapshot", policy=POLICY,
            **({"restart": self.restart} if self.restart is not None else {}))

    def chain_rows(self) -> dict:
        """What this pass's calls would leave in the database: the model_call rows, by unit key."""
        return {row["parameters"]["extended_unit_key"]: row for row in map(_row, self.journal.calls)}


class Chain(dict):
    """The source chain's ``model_call`` rows by unit key, and the object store they were published to."""

    def __init__(self, rows: dict, store: dict) -> None:
        super().__init__(rows)
        self.store = store


@pytest.fixture
def source(monkeypatch):
    first = Pass(monkeypatch, run_id="run_source")
    first.run()
    assert len(first.adapter.requests) == 4 and len(first.journal.calls) == 4
    rows = first.chain_rows()
    assert sorted(row["parameters"]["extended_phase"] for row in rows.values()) == sorted(IDENTITIES)
    return Chain(rows, first.blobs)


def _restart(point: str, ancestors=("run_source",)) -> RestartSpec:
    return RestartSpec(point=point, source_run_id=ancestors[0], ancestors=tuple(ancestors), replay=replay_rows(point))


def _rows_before(point: str) -> set[str]:
    return {identity for identity, row in ROW_OF.items() if row in replay_rows(point)}


@pytest.mark.parametrize("point", ["blocks", "cross_check", "merge", "norms", "review", "correction"])
def test_the_calls_of_the_chips_before_the_point_are_replayed_and_the_rest_are_made_again(monkeypatch, source, point) -> None:
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart(point), chain=source, store=source.store)
    result = again.run()
    replayed = _rows_before(point)
    made = {call.parameters["extended_phase"] for call in again.journal.calls}
    assert made == set(IDENTITIES) - replayed, "a call of the point's row or a later row is made, one of an earlier row is not"
    assert len(again.adapter.requests) == len(IDENTITIES) - len(replayed)
    # Only the calls that may be replayed ever looked in the chain; a call of the point and later rows never does, though the chain holds its reply.
    keys_of_replayed = {key for key, row in source.items() if row["parameters"]["extended_phase"] in replayed}
    assert set(again.consulted) == keys_of_replayed
    assert result["workflow_version"] == "extended-review-v2"
    assert {p["id"]: p["status"] for p in result["procedures"]}["comprehensive_analysis"] == "completed"
    # A replay is a sign of life of its own, and says it is the restart's: the boundary is raised once per replayed reply.
    assert again.boundaries.count("extended_reply_replayed") == len(replayed)


def test_the_replayed_result_is_the_sources_result(monkeypatch, source) -> None:
    """The saved replies are the whole of what the earlier chips produced: the restart from the last chip reproduces the observations."""
    first = Pass(monkeypatch, run_id="run_source")
    original = first.run()
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart("correction"), chain=first.chain_rows(), store=first.blobs)
    result = again.run()
    assert again.adapter.requests == [] and again.journal.calls == []
    assert result["observations"] == original["observations"]
    assert [p["status"] for p in result["procedures"]] == [p["status"] for p in original["procedures"]]


def test_a_run_that_is_no_restart_never_looks_in_the_chain(monkeypatch, source) -> None:
    plain = Pass(monkeypatch, run_id="run_plain", chain=source)
    plain.run()
    assert plain.consulted == [] and len(plain.adapter.requests) == 4 and "extended_reply_replayed" not in plain.boundaries


def test_a_reply_the_chain_does_not_hold_is_refused_not_made(monkeypatch, source) -> None:
    chain = {key: row for key, row in source.items() if row["parameters"]["extended_phase"] != "v2:comprehensive"}
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart("norms"), chain=chain, store=source.store)
    with pytest.raises(RestartRefused) as refused:
        again.run()
    assert (refused.value.reason, refused.value.restart_point) == (REASON_REPLY_MISSING, "cross_check")
    assert again.adapter.requests == [] and again.journal.calls == [], "no call is made for a chip that may only be replayed"
    status, saved = again.saved[-1]
    assert status == "failed" and "restart_reply_missing" in saved["warnings"]
    assert {p["id"]: p["status"] for p in saved["procedures"]}["norm_verification"] == "skipped"
    error = refused.value.domain_error()
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields == {"stage_id": "comprehensive_analysis", "reason": "restart_reply_missing", "restart_point": "cross_check"}


def test_a_saved_reply_that_cannot_be_read_back_is_a_missing_reply_not_a_partial_result(monkeypatch, source) -> None:
    """The row is in the chain but its blob is not in the store: without the conversion the workflow would catch ``extended_saved_reply_invalid`` (a
    ``DomainError``), save a partial result and the evidence gate would publish it."""
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart("cross_check"), chain=source)  # the store of the source is not handed over
    with pytest.raises(RestartRefused) as refused:
        again.run()
    assert (refused.value.reason, refused.value.restart_point) == (REASON_REPLY_MISSING, "blocks") and again.adapter.requests == []


def test_a_reply_for_another_request_is_refused_as_a_changed_request(monkeypatch, source) -> None:
    """The chain answered the phase, for a question this run does not ask: the key differs, the reply is not this call's."""
    chain = {}
    for key, row in source.items():
        if row["parameters"]["extended_phase"] == "v2:comprehensive":
            key = "0" * 64
            row = {**row, "parameters": {**row["parameters"], "extended_unit_key": key}}
        chain[key] = row
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart("norms"), chain=chain, store=source.store)
    with pytest.raises(RestartRefused) as refused:
        again.run()
    assert (refused.value.reason, refused.value.restart_point) == (REASON_REQUEST_CHANGED, "cross_check")
    assert again.adapter.requests == []


def test_the_refusal_is_the_first_chip_that_cannot_be_taken_not_the_last(monkeypatch, source) -> None:
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart("review"), chain={})
    with pytest.raises(RestartRefused) as refused:
        again.run()
    assert refused.value.restart_point == "blocks" and again.adapter.requests == []


def test_a_domain_error_in_the_same_place_would_have_been_swallowed_into_a_partial_result(monkeypatch, source) -> None:
    """The guard has teeth: were the refusal a ``DomainError`` the workflow would save its partial result and return it, and the evidence gate would
    publish what that holds. That is why ``RestartRefused`` is none of the four types the workflow catches."""
    again = Pass(monkeypatch, run_id="run_restart", restart=_restart("norms"), chain={}, raise_domain_error_for_replay=True, store=source.store)
    result = again.run()  # no exception: swallowed
    assert again.saved[-1][0] == "failed" and result["warnings"] == ["restart_reply_missing"]
    assert not isinstance(RestartRefused("x", "blocks"), (DomainError, ValueError, TypeError, KeyError))


def test_every_point_names_the_rows_it_may_only_replay() -> None:
    assert {point: sorted(replay_rows(point)) for point in RESTART_POINTS} == {
        "preparation": [], "text": [], "blocks": [], "cross_check": ["blocks"], "merge": ["blocks", "cross_check"],
        "norms": ["blocks", "cross_check"], "review": ["blocks", "cross_check", "norms"],
        "correction": ["blocks", "cross_check", "norms", "review"],
    }
