"""Independent W53 check: ambiguous proxy failures expose no false assurance or body."""

from __future__ import annotations

import io
import logging
import urllib.error

import pytest

from auditmanager.analysis.text import ModelRequest
from auditmanager.analysis.text.proxy import ProxyAdapter, ProxyDispatchError, ProxySettings


def _foreign_503(body: bytes) -> ProxyAdapter:
    def answer(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.HTTPError(
            "https://proxy.example/agent/v1/chat/completions", 503, "",
            {}, io.BytesIO(body),
        )

    return ProxyAdapter(
        ProxySettings(base_url="https://proxy.example/agent/v1", token="synthetic-test-token"),
        opener=answer,
    )


def test_ambiguous_503_does_not_claim_the_model_call_was_not_made() -> None:
    with pytest.raises(ProxyDispatchError) as caught:
        _foreign_503(b'{"error":{"code":"upstream_unavailable"}}').complete(
            ModelRequest(model_id="synthetic", body={"messages": []})
        )

    failure = caught.value
    assert failure.dispatch_class == "outcome_unknown"
    assert failure.retry_safe is False
    assert "call was not made" not in (failure.custom_message or "").lower()


def test_ambiguous_503_never_logs_arbitrary_upstream_body(caplog: pytest.LogCaptureFixture) -> None:
    synthetic_private_body = b'{"error":{"message":"QA PRIVATE CUSTOMER NOTE: release review delayed"}}'
    with caplog.at_level(logging.WARNING, logger="auditmanager.analysis.text.proxy"):
        with pytest.raises(ProxyDispatchError):
            _foreign_503(synthetic_private_body).complete(
                ModelRequest(model_id="synthetic", body={"messages": []})
            )

    assert "QA PRIVATE CUSTOMER NOTE" not in caplog.text
    assert "release review delayed" not in caplog.text
