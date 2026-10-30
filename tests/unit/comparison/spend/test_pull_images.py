"""A pull runner sees published image bytes and the current comparison call's identity."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ModelRequest, ModelResponse, ProviderMode, ProxyDispatchError
from auditmanager.comparison.spend.pull_images import ComparisonCallContext, PublishedPullAdapter, ROLE_MODEL_CROP
from auditmanager.executors.public import CropImage, attach_images
from auditmanager.storage.public import StorageError, derive_blob_id

PNG = b"\x89PNG\r\n\x1a\n" + b"sample"


def test_context_binds_attempt_and_call_and_reads_remaining_watchdog_time() -> None:
    class Session:
        def execute(self, statement, parameters):
            assert "comparison_work_attempt" in str(statement)
            assert parameters["attempt"] == "cqa_current"
            return SimpleNamespace(scalar_one_or_none=lambda: 47.5)

    context = ComparisonCallContext(lambda: nullcontext(Session()))
    assert context.remaining_seconds() == 0.0
    context.bind(SimpleNamespace(attempt_id="cqa_current"), "cmc_prepared")  # type: ignore[arg-type]
    assert context.comparison_attempt_id == "cqa_current" and context.call_id == "cmc_prepared"
    assert context.remaining_seconds() == 47.5


def test_pull_publishes_checked_crops_before_the_adapter_exposes_the_task() -> None:
    events = []

    class Publisher:
        def publish(self, raw, *, role, media_type):
            events.append(("publish", role, media_type, raw))
            import hashlib

            return str(derive_blob_id(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw)))

    class Adapter:
        provider_mode = ProviderMode.LIVE
        identity_basis = "declared"

        def complete(self, request):
            events.append(("task", request.body["images"][0]["blob_id"]))
            return ModelResponse(output_text="{}", stop_reason="end_turn", input_tokens=1, output_tokens=1,
                                 latency_ms=1, reported_cost_usd=None, model="gateway")

    request = attach_images(ModelRequest(model_id="model", body={"system": "x", "messages": [{"role": "user", "content": "x"}]}),
                            [CropImage(crop_id="crop:1", data=PNG)])
    wrapped = PublishedPullAdapter(Adapter(), Publisher())
    assert wrapped.provider_mode is ProviderMode.LIVE and wrapped.identity_basis == "declared"
    wrapped.complete(request)
    assert events[0] == ("publish", ROLE_MODEL_CROP, "image/png", PNG)
    assert events[1][0] == "task"


def test_invalid_crop_never_reaches_publisher_or_runner() -> None:
    events = []
    request = attach_images(ModelRequest(model_id="model", body={"messages": [{"role": "user", "content": "x"}]}),
                            [CropImage(crop_id="crop:1", data=PNG)])
    request = replace(request, images_bytes=(b"changed",))
    wrapped = PublishedPullAdapter(SimpleNamespace(complete=lambda _request: events.append("task")),
                                   SimpleNamespace(publish=lambda *_args, **_kw: events.append("publish")))
    with pytest.raises(ProxyDispatchError):
        wrapped.complete(request)
    assert events == []


@pytest.mark.parametrize("published", [StorageError(), "blob_wrong"])
def test_a_crop_that_was_not_published_cannot_be_claimed_by_a_runner(published) -> None:
    events = []
    request = attach_images(ModelRequest(model_id="model", body={"messages": [{"role": "user", "content": "x"}]}),
                            [CropImage(crop_id="crop:1", data=PNG)])

    def publish(*_args, **_kwargs):
        if isinstance(published, Exception):
            raise published
        return published

    wrapped = PublishedPullAdapter(SimpleNamespace(complete=lambda _request: events.append("task")),
                                   SimpleNamespace(publish=publish))
    with pytest.raises(ProxyDispatchError) as refused:
        wrapped.complete(request)
    assert refused.value.dispatch_class == "not_sent" and events == []
