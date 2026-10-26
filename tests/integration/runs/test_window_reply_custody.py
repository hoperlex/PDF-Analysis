"""`SECTION-CHUNKED-ANALYSIS-01`: the custody of a finished window's reply, with an in-memory store.

``WindowReplyCustody`` writes a window's answer as a private blob and, on a restart, hands it back only when
the blob agrees byte for byte with the references on the ``model_call`` row and its envelope agrees with that
call. Every refusal below is a separate way the saved reply can disagree with the call it claims to answer; each
is shown to be refused, because a custody that returns whatever bytes it finds would let a restarted run publish
findings from text no provider produced for that window.

No database and no container: the store keeps bytes in a dict and the reader of finished calls returns the rows the
test builds. The same custody against PostgreSQL and MinIO is ``test_text_windows_executor.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelResponse, ProviderMode, WindowIdentity
from auditmanager.analysis.text.windows import (
    WindowPolicy,
    build_window_request,
    plan_text_windows,
    window_key,
)
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.jobs.public import AttemptAuthority, CompletedWindowCall
from auditmanager.runs.window_reply_custody import (
    MAX_REPLY_BYTES,
    REPLY_BLOB_ROLE,
    WindowReplyCustody,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId
from auditmanager.storage import BlobNotFoundError, StorageUnavailableError
from auditmanager.storage.models import derive_blob_id
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

RUN = "run_01M2545JSD15ETSNNV904X991J"
AUTHORITY = AttemptAuthority(
    run_id=RUN,
    job_id="job_01M2545JSD15ETSNNV904X991J",
    attempt_id="att_01M2545JSD15ETSNNV904X991J",
    lease_id="lease_01M2545JSD15ETSNNV904X991J",
    execution_token="test-token",
)
PAGE = "Страница {n}. Высота потолка {n} м. Дверь {n}."
MODEL = "claude-opus-5"


def _plan():
    texts = [PAGE.format(n=n) for n in range(1, 10)]
    pages, offset = [], 0
    for number, body in enumerate(texts, start=1):
        pages.append({"page_number": number, "char_start": offset, "char_end": offset + len(body), "text": body})
        offset += len(body)
    document = {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset, "pages": pages,
    }
    return plan_text_windows(load_text_layer(document), WindowPolicy(3 * len(texts[0]) + 5, 12))


class Store:
    """Bytes in a dict, with the two operations the custody uses."""

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.puts: list[dict[str, Any]] = []
        self.readback_lies = False
        self.unavailable = False

    def put_blob(self, data: bytes, *, declared_sha256: str, declared_size: int, role: str, media_type: str):
        if self.unavailable:
            raise StorageUnavailableError()
        assert hashlib.sha256(data).hexdigest() == declared_sha256 and len(data) == declared_size
        blob_id = derive_blob_id(sha256=declared_sha256, size=declared_size)
        self.blobs[str(blob_id)] = data
        self.puts.append({"role": role, "media_type": media_type})
        return SimpleNamespace(blob_id=blob_id, sha256=declared_sha256, size=declared_size)

    def read(self, blob_id: Any, *, verify: bool = False) -> bytes:
        if str(blob_id) not in self.blobs:
            raise BlobNotFoundError(blob_id=str(blob_id))
        data = self.blobs[str(blob_id)]
        return data + b" " if self.readback_lies else data


class Jobs:
    def __init__(self) -> None:
        self.calls: dict[str, CompletedWindowCall] = {}

    def completed_window_calls(self, session: Any, authority: AttemptAuthority) -> dict[str, CompletedWindowCall]:
        return dict(self.calls)


def _custody(store: Store, jobs: Jobs, mode: ProviderMode = ProviderMode.LIVE, provider: str = "anthropic"):
    return WindowReplyCustody(
        session=object(), jobs=jobs, authority=AUTHORITY, store=store, mode=mode, provider=provider,  # type: ignore[arg-type]
    )


def _response(text: str = '{"observations": []}', stop_reason: str = "end_turn", cost: float | None = 0.1):
    return ModelResponse(
        output_text=text, stop_reason=stop_reason, input_tokens=120, output_tokens=15, latency_ms=9,
        reported_cost_usd=cost, model="claude-opus-5",
    )


class Case:
    """One finished window: preserved by the custody, and the row the reader would return for it."""

    def __init__(self, *, response: ModelResponse | None = None, mode: ProviderMode = ProviderMode.LIVE) -> None:
        self.plan = _plan()
        self.window = self.plan.windows[1]
        self.request = build_window_request(
            model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=self.plan, window=self.window
        )
        self.key = window_key(
            plan=self.plan, window=self.window, profile_sha256=V1_REFERENCE_PROFILE.content_sha256,
            model_id=MODEL, request_sha256=self.request.request_sha256,
        )
        self.identity = WindowIdentity(
            key=self.key, index=1, count=3, first_page=self.window.first_page, last_page=self.window.last_page
        )
        self.response = response or _response()
        self.store, self.jobs = Store(), Jobs()
        self.mode = mode
        self.call_id = ModelCallId.new()
        self.refs = _custody(self.store, self.jobs, mode).preserve(
            model_call_id=self.call_id, window=self.identity, request=self.request, response=self.response
        )
        self.row = CompletedWindowCall(
            key=self.key, run_id=RUN, job_id=AUTHORITY.job_id, attempt_id=AUTHORITY.attempt_id,
            model_call_id=str(self.call_id), provider="anthropic", model_id=MODEL, provider_mode=mode.value,
            request_sha256=self.request.request_sha256, response_sha256=self.response.response_sha256,
            input_tokens=120, output_tokens=15, latency_ms=9, cost_micros=100_000, cost_basis="measured",
            status="truncated" if self.response.truncated else "succeeded",
            window_index=1, window_count=3, first_page=self.window.first_page, last_page=self.window.last_page,
            reply_blob_id=self.refs["text_window_reply_blob_id"],
            reply_blob_sha256=self.refs["text_window_reply_blob_sha256"],
            reply_blob_size=self.refs["text_window_reply_blob_size"],
        )

    def recover(self, **changes: Any):
        self.jobs.calls = {self.key: replace(self.row, **changes)}
        return _custody(self.store, self.jobs, self.mode).recover(self.key)

    def rewrite_blob(self, edit) -> dict[str, Any]:
        """Replace the saved bytes with an edited envelope, keeping the row's references consistent with them."""
        old = self.store.blobs[self.row.reply_blob_id]
        document = edit(json.loads(old))
        data = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        blob_id = str(derive_blob_id(sha256=digest, size=len(data)))
        self.store.blobs[blob_id] = data
        return {"reply_blob_id": blob_id, "reply_blob_sha256": digest, "reply_blob_size": len(data)}


def _refused(case: Case, reason: str, **changes: Any) -> None:
    with pytest.raises(DomainError) as refused:
        case.recover(**changes)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields["reason"] == reason


# -- preserve and recover round trip ----------------------------------------------------------------------


def test_a_preserved_reply_is_recovered_as_the_answer_that_was_given() -> None:
    case = Case(response=_response('{"observations": [{"x": "Высота"}]}'))
    recovered = case.recover()
    assert recovered is not None and str(recovered.model_call_id) == str(case.call_id)
    assert recovered.response == replace(case.response, model="claude-opus-5")
    assert recovered.response.response_sha256 == case.response.response_sha256
    assert case.store.puts == [{"role": REPLY_BLOB_ROLE, "media_type": "application/json"}]


def test_a_cut_short_reply_is_recovered_as_cut_short() -> None:
    case = Case(response=_response('{"observations": [', stop_reason="max_tokens"))
    assert case.recover().response.truncated is True


def test_a_window_nobody_finished_is_not_recovered() -> None:
    case = Case()
    case.jobs.calls = {}
    assert _custody(case.store, case.jobs).recover(case.key) is None


def test_preserving_returns_exactly_the_three_references_the_model_call_will_carry() -> None:
    case = Case()
    assert set(case.refs) == {
        "text_window_reply_blob_id", "text_window_reply_blob_sha256", "text_window_reply_blob_size"
    }
    assert case.refs["text_window_reply_blob_sha256"] == hashlib.sha256(
        case.store.blobs[case.refs["text_window_reply_blob_id"]]
    ).hexdigest()


# -- every way the saved reply can disagree with its call ---------------------------------------------------------


def test_a_blob_that_is_gone_is_refused() -> None:
    case = Case()
    del case.store.blobs[case.row.reply_blob_id]
    _refused(case, "window_reply_unreadable")


def test_a_blob_whose_bytes_changed_is_refused() -> None:
    case = Case()
    case.store.blobs[case.row.reply_blob_id] += b" "
    _refused(case, "window_reply_blob_digest_mismatch")


def test_a_blob_of_the_wrong_size_is_refused() -> None:
    case = Case()
    _refused(case, "window_reply_blob_digest_mismatch", reply_blob_size=case.row.reply_blob_size + 1)


def test_a_blob_the_row_names_with_another_digest_is_refused() -> None:
    case = Case()
    _refused(case, "window_reply_blob_digest_mismatch", reply_blob_sha256="f" * 64)


@pytest.mark.parametrize("field,value", [
    ("window_key", "0" * 64),
    ("model_call_id", "mc_01M2545JSD15ETSNNV904X991J"),
    ("run_id", "run_01M2545JSD15ETSNNV904X991K"),
    ("first_page", 99),
    ("window_index", 2),
    ("request_sha256", "1" * 64),
    ("provider", "another"),
])
def test_an_envelope_that_names_another_call_or_window_is_refused(field: str, value: Any) -> None:
    case = Case()
    refs = case.rewrite_blob(lambda document: {**document, field: value})
    _refused(case, "window_reply_call_binding_mismatch", **refs)


def test_an_envelope_with_an_extra_or_a_missing_field_is_refused() -> None:
    case = Case()
    extra = case.rewrite_blob(lambda document: {**document, "note": "x"})
    _refused(case, "window_reply_envelope_invalid", **extra)
    missing = case.rewrite_blob(lambda document: {k: v for k, v in document.items() if k != "reported_model"})
    _refused(case, "window_reply_envelope_invalid", **missing)


def test_an_envelope_that_is_not_json_or_repeats_a_key_is_refused() -> None:
    case = Case()
    for data in (b"not json", '{"format":"x","format":"y"}'.encode(), b'{"cost": NaN}'):
        blob_id = str(derive_blob_id(sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
        case.store.blobs[blob_id] = data
        _refused(
            case, "window_reply_json_invalid", reply_blob_id=blob_id,
            reply_blob_sha256=hashlib.sha256(data).hexdigest(), reply_blob_size=len(data),
        )


def test_a_reply_whose_text_no_longer_matches_the_recorded_response_digest_is_refused() -> None:
    case = Case()
    refs = case.rewrite_blob(lambda document: {**document, "output_text": '{"observations": [{"forged": 1}]}'})
    _refused(case, "window_reply_response_digest_mismatch", **refs)


def test_a_reply_cut_short_in_the_blob_but_complete_on_the_row_is_refused() -> None:
    case = Case()
    refs = case.rewrite_blob(lambda document: {**document, "stop_reason": "max_tokens"})
    # The stop reason is part of the response digest, so the forged envelope fails there first.
    _refused(case, "window_reply_response_digest_mismatch", **refs)
    _refused(case, "window_reply_status_mismatch", status="truncated")


def test_an_envelope_with_a_field_of_the_wrong_type_is_refused() -> None:
    case = Case()
    refs = case.rewrite_blob(lambda document: {**document, "reported_cost_usd": "free"})
    _refused(case, "window_reply_fields_invalid", **refs)


def test_a_call_of_another_mode_or_provider_is_refused_not_recovered() -> None:
    case = Case()
    _refused(case, "window_call_binding_mismatch", provider_mode="recorded")
    _refused(case, "window_call_binding_mismatch", provider="another")


# -- preserve refuses what it cannot keep ---------------------------------------------------------------------


def test_a_cost_that_is_not_a_cost_is_refused_before_anything_is_written() -> None:
    for cost in (float("nan"), -1.0, float("inf")):
        store = Store()
        custody = _custody(store, Jobs())
        plan = _plan()
        window = plan.windows[0]
        request = build_window_request(model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=plan, window=window)
        identity = WindowIdentity(key="a" * 64, index=0, count=3, first_page=1, last_page=3)
        with pytest.raises(DomainError):
            custody.preserve(model_call_id=ModelCallId.new(), window=identity, request=request, response=_response(cost=cost))
        assert store.blobs == {}


def test_a_reply_larger_than_the_custody_limit_is_refused() -> None:
    plan = _plan()
    request = build_window_request(model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=plan, window=plan.windows[0])
    identity = WindowIdentity(key="a" * 64, index=0, count=3, first_page=1, last_page=3)
    store = Store()
    with pytest.raises(DomainError) as refused:
        _custody(store, Jobs()).preserve(
            model_call_id=ModelCallId.new(), window=identity, request=request,
            response=_response("x" * (MAX_REPLY_BYTES + 1)),
        )
    assert refused.value.detail_fields["reason"] == "window_reply_too_large" and store.blobs == {}


def test_a_store_that_is_down_is_a_dependency_failure_not_a_lost_reply_swallowed() -> None:
    plan = _plan()
    request = build_window_request(model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=plan, window=plan.windows[0])
    identity = WindowIdentity(key="a" * 64, index=0, count=3, first_page=1, last_page=3)
    store = Store()
    store.unavailable = True
    with pytest.raises(DomainError) as refused:
        _custody(store, Jobs()).preserve(
            model_call_id=ModelCallId.new(), window=identity, request=request, response=_response()
        )
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_a_readback_that_differs_from_what_was_written_is_an_integrity_failure() -> None:
    plan = _plan()
    request = build_window_request(model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=plan, window=plan.windows[0])
    identity = WindowIdentity(key="a" * 64, index=0, count=3, first_page=1, last_page=3)
    store = Store()
    store.readback_lies = True
    with pytest.raises(DomainError) as refused:
        _custody(store, Jobs()).preserve(
            model_call_id=ModelCallId.new(), window=identity, request=request, response=_response()
        )
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
