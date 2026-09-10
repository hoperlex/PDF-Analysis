"""The fail-closed mapping, exercised against real storage.

A missing required input or output is ``failed`` with a typed error and no artifact.
``partial`` and ``skipped`` are structurally impossible for these three stages.

Every case here drives a *real* refusal rather than asserting one in prose. The three
guards that could otherwise pass by never running - missing input, missing output, and
an unreadable source - each have a case that reaches them, and the negative corpus
fixtures supply genuinely malformed bytes rather than a mock that returns an error.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.public import (
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    StageProduction,
    StageStatus,
    run_stage,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import sha256_of
from auditmanager.storage.models import ROLE_SOURCE_DOCUMENT as BLOB_ROLE_SOURCE

VERSION_UID = "ver_01M2545JSD15ETSNNV904X991J"

NEGATIVE = Path(__file__).resolve().parents[3] / "fixtures" / "synthetic" / "ar" / "negative"


def _publish(store: Any, payload: bytes, media_type: str = "application/pdf") -> Any:
    return store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=BLOB_ROLE_SOURCE,
        media_type=media_type,
    ).blob_id


# --- an unreadable source ----------------------------------------------------


def test_a_source_that_is_not_a_pdf_fails_with_analysis_input_invalid(
    store: Any,
) -> None:
    """The task's named case: an unreadable source blob is ``failed``, with no artifact."""
    blob_id = _publish(store, (NEGATIVE / "not_a_pdf.txt").read_bytes(), "text/plain")

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: blob_id},
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.artifacts == ()


def test_truncated_pdf_bytes_fail_closed(store: Any) -> None:
    """Bytes that begin like a PDF and stop mid-object are still a refusal."""
    baseline = (NEGATIVE.parent / "ar_baseline.pdf").read_bytes()
    blob_id = _publish(store, baseline[: len(baseline) // 3])

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: blob_id},
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_an_encrypted_source_is_refused_rather_than_read_as_empty(store: Any) -> None:
    """``OD-01``'s separate envelope probe earns its keep here.

    An extractor that returns empty text for an encrypted file would otherwise be
    indistinguishable from one that read a document with no text. ``pypdf`` answers
    the encryption question before any extraction is attempted.
    """
    blob_id = _publish(store, (NEGATIVE / "encrypted.pdf").read_bytes())

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: blob_id},
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "source_encrypted"


def test_an_image_only_source_is_refused_with_validation_failed(store: Any) -> None:
    """Section 4.2: ``has_text_layer`` is ``true`` for every page, or nothing is published.

    OCR is not silently substituted, and the page never reaches the inventory - which
    is what makes the refusal provable rather than a field a consumer must check.
    """
    blob_id = _publish(store, (NEGATIVE / "image_only.pdf").read_bytes())

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: blob_id},
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.VALIDATION_FAILED


# --- a missing required input ------------------------------------------------


@pytest.mark.parametrize(
    ("stage_id", "supplied"),
    [
        ("source_preparation", {}),
        ("page_geometry_extraction", {}),
        ("document_context_build", {}),
    ],
)
def test_a_missing_required_input_fails_before_the_stage_runs(
    store: Any, stage_id: str, supplied: dict[str, Any]
) -> None:
    result = run_stage(
        stage_id,
        version_uid=VERSION_UID,
        inputs=supplied,
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "missing_required_input"


def test_a_partially_supplied_input_set_still_fails(store: Any, source_blob: Any) -> None:
    """``page_geometry_extraction`` needs both prepared roles; one is not enough."""
    first = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    assert first.status is StageStatus.SUCCEEDED

    result = run_stage(
        "page_geometry_extraction",
        version_uid=VERSION_UID,
        inputs={ROLE_TEXT_LAYER: first.artifact(ROLE_TEXT_LAYER).blob_id},
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_an_input_carrying_the_wrong_artifact_role_is_refused(
    store: Any, source_blob: Any
) -> None:
    """A text layer supplied where a page inventory belongs fails closed."""
    first = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    text_layer_blob = first.artifact(ROLE_TEXT_LAYER).blob_id

    result = run_stage(
        "page_geometry_extraction",
        version_uid=VERSION_UID,
        inputs={
            ROLE_PAGE_INVENTORY: text_layer_blob,  # deliberately the wrong artifact
            ROLE_TEXT_LAYER: text_layer_blob,
        },
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "input_role_mismatch"


# --- a missing required output -----------------------------------------------


def test_a_stage_that_omits_a_required_output_is_failed_not_succeeded(
    store: Any, source_blob: Any
) -> None:
    """The post-condition guard, driven by a handler that returns normally.

    The three real implementations structurally cannot reach this - they publish
    every role or raise - so the guard is exercised with an injected handler. That is
    the only way to prove the check can fire rather than trusting that it would.
    """

    def publishes_only_one_role(context: Any) -> StageProduction:
        from auditmanager.analysis.stages import source_preparation

        full = source_preparation.run(context)
        kept = tuple(
            reference
            for reference in full.artifacts
            if reference.role == ROLE_PAGE_INVENTORY
        )
        return StageProduction(artifacts=kept, metrics=dict(full.metrics))

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
        handler=publishes_only_one_role,
    )

    assert result.status is StageStatus.FAILED
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_FAILED
    assert result.artifacts == (), "a failed result carries no artifact reference"


def test_a_stage_producing_nothing_at_all_is_failed(store: Any, source_blob: Any) -> None:
    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
        handler=lambda context: StageProduction(),
    )

    assert result.status is StageStatus.FAILED
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_FAILED


def test_the_guard_admits_a_handler_that_publishes_every_role(
    store: Any, source_blob: Any
) -> None:
    """The other side of the guard: it is not refusing everything.

    Without this, the missing-output test above would pass just as well against a
    runner that failed unconditionally.
    """
    from auditmanager.analysis.stages import source_preparation

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
        handler=source_preparation.run,
    )

    assert result.status is StageStatus.SUCCEEDED
    assert result.error is None


# --- an unknown stage --------------------------------------------------------


def test_an_unknown_stage_is_refused_by_the_registry(store: Any) -> None:
    """Not a ``failed`` result: a ``StageResult`` needs a stage version to carry.

    An identity the contract does not declare has no version, so no schema-valid
    result can be built for it. The refusal is a raise, which is what stops an
    unknown stage from being recorded as a run that merely failed.
    """
    with pytest.raises(DomainError) as raised:
        run_stage(
            "not_a_declared_stage",
            version_uid=VERSION_UID,
            inputs={},
            blob_store=store,
        )
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_a_declared_but_unimplemented_stage_is_refused(store: Any) -> None:
    with pytest.raises(DomainError) as raised:
        run_stage(
            "text_analysis",
            version_uid=VERSION_UID,
            inputs={},
            blob_store=store,
        )
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


# --- a stage bound to the wrong text layer -----------------------------------


def test_a_block_index_bound_to_a_different_text_layer_is_refused(
    store: Any, source_blob: Any
) -> None:
    """Section 4.4's binding, exercised with a text layer that would otherwise fit.

    The other document is *longer* than the baseline, so every one of the baseline's
    block spans lands inside its range and resolves to some text. Resolving is
    therefore not evidence of resolving correctly, and only ``text_layer_sha256``
    distinguishes the two. This case is why that check exists: without it the stage
    published a graph over anchors pointing at the wrong characters, and it did so
    reporting ``succeeded``.
    """
    first = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    second = run_stage(
        "page_geometry_extraction",
        version_uid=VERSION_UID,
        inputs={
            ROLE_PAGE_INVENTORY: first.artifact(ROLE_PAGE_INVENTORY).blob_id,
            ROLE_TEXT_LAYER: first.artifact(ROLE_TEXT_LAYER).blob_id,
        },
        blob_store=store,
    )

    other = _publish(store, (NEGATIVE / "too_many_pages.pdf").read_bytes())
    other_prepared = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: other},
        blob_store=store,
    )
    assert other_prepared.status is StageStatus.SUCCEEDED, other_prepared.error

    baseline_layer = json.loads(store.read(first.artifact(ROLE_TEXT_LAYER).blob_id))
    other_layer = json.loads(
        store.read(other_prepared.artifact(ROLE_TEXT_LAYER).blob_id)
    )
    assert other_layer["total_char_count"] > baseline_layer["total_char_count"], (
        "the substituted text layer must be long enough to hold the baseline's "
        "spans, or this case would be caught by the range check instead"
    )

    result = run_stage(
        "document_context_build",
        version_uid=VERSION_UID,
        inputs={
            ROLE_BLOCK_INDEX: second.artifact(ROLE_BLOCK_INDEX).blob_id,
            ROLE_TEXT_LAYER: other_prepared.artifact(ROLE_TEXT_LAYER).blob_id,
        },
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "text_layer_binding_mismatch"


def test_a_geometry_stage_given_a_text_layer_from_another_document_is_refused(
    store: Any, source_blob: Any
) -> None:
    """The re-extraction cross-check in ``page_geometry_extraction``."""
    baseline = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    other = _publish(store, (NEGATIVE / "too_many_pages.pdf").read_bytes())
    other_prepared = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: other},
        blob_store=store,
    )

    result = run_stage(
        "page_geometry_extraction",
        version_uid=VERSION_UID,
        inputs={
            # The inventory names the baseline; the text layer is the other document.
            ROLE_PAGE_INVENTORY: baseline.artifact(ROLE_PAGE_INVENTORY).blob_id,
            ROLE_TEXT_LAYER: other_prepared.artifact(ROLE_TEXT_LAYER).blob_id,
        },
        blob_store=store,
    )

    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
