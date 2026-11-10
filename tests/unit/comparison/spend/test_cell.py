"""`HOSTS-CMP-01`: the frozen cell of a comparison job, applied to one call -- effort, the answer limit as a ceiling, and the host window.

Container-free. The wrapper applies it to every call of a job whose consent names a cell, before the request is hashed, priced and journalled;
a job with no cell (the legacy route, a rule) is called exactly as it always was.
"""

from __future__ import annotations

from typing import Any

from auditmanager.analysis.public import CellSettings, ModelRequest
from auditmanager.comparison.spend.cell import apply_cell, capped_output_tokens, host_call_of
from auditmanager.comparison.spend.model import CallEstimate

from .test_caller_unit import (
    MODEL, Adapter, FakeItem, Log, _consent, _make, _reply, _route,
)

CELL = CellSettings("comparison_pair_check:main", MODEL, "medium", 800, 600)


def body_of(request: ModelRequest) -> dict[str, Any]:
    return dict(request.body)


def test_the_limit_is_a_ceiling_over_the_modules_own_and_never_a_floor():
    assert capped_output_tokens(1_200, CELL) == 800, "a cell below the module's limit lowers it"
    assert capped_output_tokens(600, CELL) == 600, "a cell above the module's limit does not raise it"
    assert capped_output_tokens(1_200, None) == 1_200


def test_the_effort_replaces_the_modules_and_the_limit_caps_it():
    request = ModelRequest(model_id=MODEL, body={
        "model": MODEL, "max_tokens": 1_200, "messages": [], "output_config": {"effort": "high", "format": {"type": "json_schema"}}},
        idempotency_scope="job:work")
    applied, estimate = apply_cell(CELL, request, CallEstimate(input_tokens=5_000, output_tokens=1_200))
    assert body_of(applied)["max_tokens"] == 800
    assert body_of(applied)["output_config"] == {"effort": "medium", "format": {"type": "json_schema"}}, "only the effort moves"
    assert (estimate.input_tokens, estimate.output_tokens) == (5_000, 800), "the call is priced at what it may answer"
    assert applied.idempotency_scope == "job:work" and applied.model_id == MODEL, "a request is not otherwise touched"
    assert body_of(request)["max_tokens"] == 1_200 and body_of(request)["output_config"]["effort"] == "high", "the original is not mutated"
    assert applied.request_sha256 != request.request_sha256


def test_a_request_with_no_limit_or_no_effort_takes_the_cells():
    bare = ModelRequest(model_id=MODEL, body={"model": MODEL, "messages": []})
    applied, estimate = apply_cell(CELL, bare, CallEstimate(input_tokens=1, output_tokens=2_000))
    assert body_of(applied)["max_tokens"] == 800 and body_of(applied)["output_config"] == {"effort": "medium"}
    assert estimate.output_tokens == 800


def test_with_no_cell_nothing_changes():
    request = ModelRequest(model_id=MODEL, body={"model": MODEL, "max_tokens": 1_200, "messages": []})
    estimate = CallEstimate(input_tokens=1, output_tokens=1_200)
    assert apply_cell(None, request, estimate) == (request, estimate)


def test_the_images_of_a_request_ride_through():
    request = ModelRequest(model_id=MODEL, body={"model": MODEL, "max_tokens": 1_200, "images": [{"blob_id": "b"}]},
                           images_bytes=(b"png-1", b"png-2"))
    applied, _ = apply_cell(CELL, request, CallEstimate(input_tokens=1, output_tokens=1))
    assert applied.images_bytes == (b"png-1", b"png-2") and body_of(applied)["images"] == [{"blob_id": "b"}]


def test_a_host_is_told_the_cells_model_effort_limit_and_window():
    call = host_call_of(CELL, provider="codex", access="subscription")
    assert (call.provider, call.access, call.model_id, call.effort, call.max_output_tokens, call.timeout_seconds, call.cell_key) == (
        "codex", "subscription", MODEL, "medium", 800, 600, "comparison_pair_check:main")
    assert call.members(window_seconds=450.9) == {
        "provider": "codex", "access": "subscription", "model_id": MODEL, "effort": "medium", "max_output_tokens": 800,
        "timeout_seconds": 450, "cell_key": "comparison_pair_check:main"}


# -- the wrapper applies it to the call that is made, hashed and priced ---------------------------------------------------------


class Recording(Adapter):
    def __init__(self, log: Log, **kw: Any) -> None:
        super().__init__(log, **kw)
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest):
        self.requests.append(request)
        return super().complete(request)


def request_with_module_values() -> ModelRequest:
    return ModelRequest(model_id=MODEL, body={
        "model": MODEL, "max_tokens": 1_200, "messages": [{"role": "user", "content": "x"}],
        "output_config": {"effort": "high"}})


def test_the_adapter_receives_the_request_with_the_cells_effort_and_limit_and_the_journal_is_priced_on_them():
    log = Log()
    adapter = Recording(log, reply=_reply())
    caller = _make(log)
    estimate = CallEstimate(input_tokens=1_000_000, output_tokens=1_200)
    caller.call(FakeItem(log), _route(adapter), request_with_module_values(), estimate=estimate, consent=_consent(cell=CELL))
    sent = adapter.requests[0]
    assert body_of(sent)["max_tokens"] == 800 and body_of(sent)["output_config"]["effort"] == "medium"
    prepared = next(entry[1] for entry in log if isinstance(entry, tuple) and entry[0] == "prepare")
    assert prepared["request_sha256"] == sent.request_sha256, "the journal holds the request that was sent, not the one that was built"
    # USD 1 per million in, USD 5 per million out: 1 000 000 in and 800 out
    assert prepared["estimate_micros"] == 1_000_000 + 4_000


def test_a_consent_with_no_cell_sends_the_request_as_built():
    log = Log()
    adapter = Recording(log, reply=_reply())
    built = request_with_module_values()
    _make(log).call(FakeItem(log), _route(adapter), built, estimate=CallEstimate(input_tokens=1_000_000, output_tokens=1_200), consent=_consent())
    assert adapter.requests[0] is built
    prepared = next(entry[1] for entry in log if isinstance(entry, tuple) and entry[0] == "prepare")
    assert prepared["estimate_micros"] == 1_000_000 + 6_000, "priced at the module's own ceiling"


def test_a_recorded_reply_is_not_changed_by_a_consent_it_does_not_have():
    # a recorded job has no consent (nothing is spent) and so no cell: the call is made as built
    from auditmanager.analysis.public import ProviderMode

    log = Log()
    adapter = Recording(log, mode=ProviderMode.RECORDED, reply=_reply())
    built = request_with_module_values()
    _make(log).call(FakeItem(log), _route(adapter), built, estimate=CallEstimate(input_tokens=1, output_tokens=1), consent=None)
    assert adapter.requests[0] is built
