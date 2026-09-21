"""The ``partial`` mapping, and the statuses that are not it.

``P02_SEAMS.md`` section 4.7 makes ``pages_analysed`` the thing that makes ``partial``
*checkable*: it is reported only when usable observations were produced over a
**strict subset** of pages, with a typed error. An unavailable provider is ``failed``
with ``dependency_unavailable``, never ``partial``.

The stage registry's status policy for ``text_analysis`` sets ``skip_allowed: false``
and ``partial_allowed: true``, so ``skipped`` must never appear. And
``P02_SEAMS.md`` section 3.4: ``succeeded`` carries no error, every other status
requires one - which :class:`TextAnalysisOutcome` enforces in its own constructor
rather than trusting each return site.
"""

from __future__ import annotations

import pytest

from auditmanager.analysis.text import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    RecordedAdapter,
    TextAnalysisOutcome,
    load_text_layer,
    run_text_analysis,
)
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import RunId


def test_a_truncated_reply_is_partial_and_never_succeeded(
    text_layer_document, variant_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("truncated"),
    )
    assert outcome.status == STATUS_PARTIAL
    assert outcome.status != STATUS_SUCCEEDED
    assert outcome.error is not None
    assert outcome.error.code is ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE
    assert outcome.artifact is not None


def test_partial_reports_a_strict_subset_of_pages(text_layer_document, variant_adapter):
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("truncated"),
    )
    text_layer = load_text_layer(text_layer_document)
    every_page = set(text_layer.page_numbers)
    analysed = set(outcome.artifact["pages_analysed"])

    assert analysed < every_page, "partial requires a strict subset"
    assert analysed, "partial also requires usable observations, so the subset is non-empty"
    assert outcome.artifact["observations"], "partial means usable observations were produced"


def test_the_incomplete_tail_of_a_truncated_reply_is_discarded(
    text_layer_document, variant_adapter
):
    """Two complete observations survive; the third, cut mid-element, does not.

    A half-written contradiction reads exactly like a whole one - it would carry one
    value where the finding claims two - so the salvage refuses to patch the JSON and
    keeps only elements that parsed on their own.
    """
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("truncated"),
    )
    assert outcome.metrics["observations_proposed"] == 2
    assert len(outcome.artifact["observations"]) == 2
    for observation in outcome.artifact["observations"]:
        assert observation["category"] == "internal_contradiction"
        assert len(observation["evidence"]) == 2


def test_the_truncated_call_is_recorded_as_truncated(text_layer_document, variant_adapter):
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("truncated"),
    )
    (call,) = outcome.model_calls
    assert call.status == "truncated"
    assert call.as_dict()["status"] == "truncated"


def test_an_unavailable_provider_is_failed_and_never_partial(
    text_layer_document, unreachable_provider
):
    """The transport case, driven by a provider that really is unreachable.

    It used a `RecordedAdapter` over an empty directory until `W29-RETRY`, which is a
    local miss rather than an outage; the name said one thing and the fixture did
    another.
    """
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=unreachable_provider,
    )
    assert unreachable_provider.calls == 1
    assert outcome.status == STATUS_FAILED
    assert outcome.status != STATUS_PARTIAL
    assert outcome.error.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_a_corpus_that_cannot_answer_is_failed_and_never_partial(
    text_layer_document, empty_recording_dir
):
    """The other half: `partial` is a strict subset of pages, and none is not a subset."""
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=RecordedAdapter(empty_recording_dir),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.status != STATUS_PARTIAL
    assert outcome.error.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_the_stage_never_reports_skipped(text_layer_document, recorded_adapter, variant_adapter):
    """``skip_allowed: false`` in the stage registry, held here as a behaviour."""
    adapters = [
        recorded_adapter,
        variant_adapter("truncated"),
        variant_adapter("over_budget"),
        variant_adapter("ungrounded_quotation"),
    ]
    for adapter in adapters:
        outcome = run_text_analysis(
            run_id=RunId.new(), text_layer_document=text_layer_document, adapter=adapter
        )
        assert outcome.status in {STATUS_SUCCEEDED, STATUS_PARTIAL, STATUS_FAILED}
        assert outcome.status != "skipped"


def test_succeeded_carries_no_error_and_nothing_else_may_omit_one():
    """Section 3.4, enforced by the outcome's own constructor."""
    with pytest.raises(ValueError):
        TextAnalysisOutcome(
            status=STATUS_SUCCEEDED,
            artifact={},
            model_calls=(),
            error=RuntimeError("x"),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        TextAnalysisOutcome(
            status=STATUS_PARTIAL, artifact={}, model_calls=(), error=None
        )
    with pytest.raises(ValueError):
        TextAnalysisOutcome(status=STATUS_FAILED, artifact=None, model_calls=(), error=None)


def test_a_text_layer_of_an_unexpected_version_fails_closed(text_layer_document):
    """Section 4: a consumer reading an unexpected ``artifact_version`` fails closed."""
    document = dict(text_layer_document)
    document["artifact_version"] = "2.0.0"
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=document, adapter=RecordedAdapter()
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert outcome.error.detail_fields["reason"] == "artifact_version_unsupported"
    assert outcome.model_calls == (), "it failed closed before calling anything"
