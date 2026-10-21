"""The crop byte budget over the real geometry stage and the real object store (`RUN-ROBUSTNESS-01`, D-177).

``tests/unit/runs/test_crop_byte_budget.py`` shows where the line is with a store that records
what it is asked. This shows the decorator does its work where it is used: around the store a
real ``page_geometry_extraction`` publishes its crops to. The committed baseline bundle has two
IMAGE blocks and so two crops; a budget of exactly their bytes lets the stage succeed with
every crop published, and one byte less refuses it with the stage's typed reason after the
first crop only -- the second is never written.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.public import ROLE_CROP_IMAGE, StageStatus
from auditmanager.runs.crop_budget import REASON_CROPS_OVER_BUDGET, CropByteBudget
from auditmanager.shared.errors import ErrorCode
from tests.integration.analysis.geometry.geometry_support import (
    committed_bundle,
    prepare,
    run_geometry,
)
from tests.integration.analysis.recognised import recognised_support as support

store = support.store


class _Counting:
    """Counts the crop blobs that reach the object store; everything else is the store's."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.crop_puts = 0

    def put_blob(self, *args: Any, **kwargs: Any) -> Any:
        if str(kwargs["role"]) == "geometry_crop_image":
            self.crop_puts += 1
        return self._inner.put_blob(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _crop_bytes(result: Any) -> list[int]:
    return [ref.size_bytes for ref in result.artifacts if ref.role == ROLE_CROP_IMAGE]


def test_a_budget_of_exactly_the_crops_lets_the_stage_succeed_and_one_byte_less_refuses_it(store) -> None:
    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    reference = run_geometry(store, prepared)
    assert reference.status is StageStatus.SUCCEEDED
    sizes = _crop_bytes(reference)
    assert len(sizes) == 2, "the baseline bundle has two IMAGE blocks and so two crops"
    total = sum(sizes)

    counting = _Counting(store)
    within = run_geometry(CropByteBudget(counting, stage_id="page_geometry_extraction", budget=total), prepared)
    assert within.status is StageStatus.SUCCEEDED
    assert _crop_bytes(within) == sizes

    counting = _Counting(store)
    over = run_geometry(
        CropByteBudget(counting, stage_id="page_geometry_extraction", budget=total - 1), prepared
    )
    assert over.status is StageStatus.FAILED and over.artifacts == ()
    assert over.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert dict(over.error.details) == {
        "stage_id": "page_geometry_extraction",
        "reason": REASON_CROPS_OVER_BUDGET,
    }
    assert counting.crop_puts == 1, "the crop past the line was not written"


def test_the_stage_is_unchanged_without_a_budget_in_the_way(store) -> None:
    """The decorator at its real size changes nothing for the real export's order of magnitude."""
    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    plain = run_geometry(store, prepared)
    budgeted = run_geometry(CropByteBudget(store, stage_id="page_geometry_extraction"), prepared)
    assert plain.status is budgeted.status is StageStatus.SUCCEEDED
    assert [ref.blob_id for ref in plain.artifacts] == [ref.blob_id for ref in budgeted.artifacts]
