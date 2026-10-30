"""Safe provider refusal metadata survives settlement without weakening unknown outcomes."""

from types import SimpleNamespace

import pytest

from auditmanager.analysis.text.proxy import _classified_http_failure
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.errors import CallFailed, OutcomeUnknown


@pytest.mark.parametrize("status,body,kind,dispatch", [
    (402, b'{}', "quota", "definite_refusal"),
    (401, b'{}', "auth", "definite_refusal"),
    (429, b'{"error":{"code":"insufficient_quota"}}', "quota", "definite_refusal"),
    (429, b'{"error":{"code":{}}}', "rate_limit", "rate_limited"),
])
def test_refusal_metadata_reaches_typed_call_failure(monkeypatch, status, body, kind, dispatch):
    failure = _classified_http_failure(status, body, headers={"Retry-After": "12"})
    caller = ComparisonModelCaller(None)
    caller._repository = SimpleNamespace(fail=lambda *args, **kwargs: None)
    monkeypatch.setattr(ComparisonModelCaller, "_settle", lambda self, call_id, change: change(None))
    with pytest.raises(CallFailed) as caught:
        caller._settle_error("call", None, failure, mode="live", unmetered=True)
    assert caught.value.provider_failure_kind == kind
    assert caught.value.dispatch_class == dispatch
    assert caught.value.http_status == status
    assert caught.value.retry_safe is (kind == "rate_limit")


def test_ambiguous_server_failure_stays_unknown(monkeypatch):
    failure = _classified_http_failure(503, b'{}', headers={})
    caller = ComparisonModelCaller(None)
    caller._repository = SimpleNamespace(mark_unknown=lambda *args, **kwargs: None)
    monkeypatch.setattr(ComparisonModelCaller, "_settle", lambda self, call_id, change: change(None))
    with pytest.raises(OutcomeUnknown):
        caller._settle_error("call", None, failure, mode="live", unmetered=True)
