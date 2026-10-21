"""A version may not hold more than `MAX_CROP_BYTES` of crops (`RUN-ROBUSTNESS-01`, D-177).

`W55B-JUDGE-X` X-4 left the bytes of a version's crops bounded only by their count: 1 000 IMAGE
blocks of 4 Mpx each, at 11.4 MiB for a high-entropy PNG, is about 11 GiB. The budget is a
decorator over the stage's publication store; these tests use a store that records what it was
asked, so they show **where the line is, that nothing past it is written, and that it counts
only crops** -- with no database and no container. The same decorator over the real stage and
the real object store is shown in ``tests/integration/analysis/geometry/test_crop_byte_budget_stage.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.runs.crop_budget import MAX_CROP_BYTES, REASON_CROPS_OVER_BUDGET, CropByteBudget
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_role

CROP = parse_blob_role("geometry_crop_image")
OTHER = parse_blob_role("geometry_portal_blocks")


class RecordingStore:
    """What a store is asked, and an attribute only it has."""

    marker = "the inner store's own"

    def __init__(self) -> None:
        self.puts: list[tuple[str, int]] = []

    def put_blob(self, source: Any, *, declared_sha256: str, declared_size: int, role: Any, media_type: str) -> str:
        self.puts.append((str(role), declared_size))
        return f"published-{len(self.puts)}"

    def read(self, blob_id: str) -> bytes:
        return b"read:" + blob_id.encode()


def put(store: Any, size: int, role: Any = CROP) -> Any:
    return store.put_blob(b"", declared_sha256="0" * 64, declared_size=size, role=role, media_type="image/png")


def test_the_budget_is_two_gibibytes_a_stage() -> None:
    # 0.79 MiB a crop measured on the 500-sheet set; a thousand of them are 0.77 GiB.
    assert MAX_CROP_BYTES == 2 * 1024**3
    assert MAX_CROP_BYTES > 1_000 * 0.79 * 1024**2 * 2
    assert MAX_CROP_BYTES < 1_000 * 11.4 * 1024**2 / 4  # a quarter of the worst case


def test_crops_up_to_the_budget_are_published_and_the_one_past_it_is_not() -> None:
    inner = RecordingStore()
    budget = CropByteBudget(inner, stage_id="page_geometry_extraction", budget=100)
    assert put(budget, 60) == "published-1"
    assert put(budget, 40) == "published-2"  # exactly at the budget: allowed
    assert budget.used == 100
    with pytest.raises(DomainError) as refused:
        put(budget, 1)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert dict(refused.value.detail_fields) == {
        "stage_id": "page_geometry_extraction",
        "reason": REASON_CROPS_OVER_BUDGET,
    }
    assert [size for _role, size in inner.puts] == [60, 40], "the crop past the line was never written"
    assert budget.used == 100, "a refused crop is not counted"


def test_a_crop_that_alone_exceeds_the_budget_is_refused_at_once() -> None:
    inner = RecordingStore()
    budget = CropByteBudget(inner, stage_id="page_geometry_extraction", budget=100)
    with pytest.raises(DomainError):
        put(budget, 101)
    assert inner.puts == []


def test_only_crop_images_are_counted() -> None:
    inner = RecordingStore()
    budget = CropByteBudget(inner, stage_id="page_geometry_extraction", budget=100)
    for _ in range(5):
        put(budget, 10_000, OTHER)  # the artifacts are bounded by their own rules
    assert budget.used == 0 and len(inner.puts) == 5
    assert put(budget, 100) == "published-6"


def test_everything_else_of_the_store_is_the_inner_stores() -> None:
    inner = RecordingStore()
    budget = CropByteBudget(inner, stage_id="page_geometry_extraction", budget=1)
    assert budget.marker == "the inner store's own"
    assert budget.read("blob") == b"read:blob"


def test_each_stage_execution_has_its_own_count() -> None:
    inner = RecordingStore()
    first = CropByteBudget(inner, stage_id="page_geometry_extraction", budget=100)
    second = CropByteBudget(inner, stage_id="page_geometry_extraction", budget=100)
    put(first, 100)
    put(second, 100)  # a resumed attempt publishes the same content-addressed blobs again
    assert first.used == second.used == 100


def test_the_refusal_names_no_number_and_echoes_nothing() -> None:
    budget = CropByteBudget(RecordingStore(), stage_id="page_geometry_extraction", budget=1)
    with pytest.raises(DomainError) as refused:
        put(budget, 2)
    text = str(refused.value)
    assert "more storage than a version may hold" in text
    assert not any(ch.isdigit() for ch in text)
