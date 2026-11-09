"""`ADR-0027`, F3 of judge J3: the decision memory reads a finding's geometry from **the finding's own run**, without a database.

A block reference (``b_NNNNNN``) is an anchor inside the artifact of the run that minted it. Two runs of one version may number their
lines differently (another text-extraction option, another pdfplumber), so the evidence of a finding decided on the older run must
find its box in the older run's block index, and its crops in the older run's crop manifest -- never in the version's newest run's.
The runs' rows and the saved documents are stubbed at the seams the adapter reads them through, as ``test_run_finding_blocks_adapter``
does; the same reads over a real database are ``tests/integration/decisions/test_decision_memory_capture.py``'s.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import sessionmaker

from auditmanager.analysis.public import (
    KIND_PORTAL_DESCRIPTION,
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
    ROLE_RECOGNISED_TEXT,
)
from auditmanager.bootstrap.adapters import BlockAdapter
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OLDER, NEWER = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV", "run_01ARZ3NDEKTSV4RRFFQ69G5FAW"
FIRST_LINE = "b_000001"


def _index(x0: float) -> dict[str, Any]:
    return {"blocks": [{
        "block_id": FIRST_LINE, "page_number": 1, "bbox": {"x0": x0, "y0": 10.0, "x1": x0 + 50.0, "y1": 22.0},
        "bbox_unit": "pt", "bbox_origin": "top_left", "char_start": 0, "char_end": 20,
    }]}


def _crops(blob: str) -> dict[str, Any]:
    return {"crops": [{"portal_block_id": "blk_" + "1" * 32, "page_number": 1, "bbox_norm": [0.1, 0.1, 0.5, 0.5], "blob_id": blob}]}


def _recognised(description: str) -> dict[str, Any]:
    return {"entries": [{"portal_block_id": "blk_" + "1" * 32, "kind": KIND_PORTAL_DESCRIPTION, "text": description}]}


def _ref(role: str, run: str) -> dict[str, Any]:
    return {"role": role, "blob_id": f"{run}:{role}"}


def _stages(run: str, *, geometry: str = "succeeded", portal: bool = True) -> dict[str, Any]:
    artifacts = [_ref(ROLE_BLOCK_INDEX, run)]
    if portal:
        artifacts += [_ref(ROLE_PORTAL_BLOCKS, run), _ref(ROLE_PAGE_CROPS, run)]
    return {
        "page_geometry_extraction": SimpleNamespace(stage_id="page_geometry_extraction", status=geometry, artifacts=tuple(artifacts)),
        "source_preparation": SimpleNamespace(
            stage_id="source_preparation", status="succeeded", artifacts=(_ref(ROLE_RECOGNISED_TEXT, run),)),
    }


class Adapter(BlockAdapter):
    """The adapter with its saved documents answered from memory and every document read recorded."""

    def __init__(self, documents: dict[tuple[str, str], dict[str, Any]]) -> None:
        super().__init__(sessionmaker(), blob_store=None)
        self.documents = documents
        self.reads: list[tuple[str, str]] = []

    def _portal_document(self, reference: Any, role: str, version_uid: str) -> dict[str, Any]:
        assert version_uid == VERSION
        run = reference["blob_id"].split(":")[0]
        self.reads.append((run, role))
        return self.documents[(run, role)]


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Two runs of one version, the newer listed first, each with its own geometry: the same ``b_000001`` is at x 100 in the older
    run's index and at x 300 in the newer run's."""
    state: dict[str, Any] = {
        "stages": {OLDER: _stages(OLDER), NEWER: _stages(NEWER)},
        "rows": {OLDER: SimpleNamespace(run_id=OLDER, version_uid=VERSION), NEWER: SimpleNamespace(run_id=NEWER, version_uid=VERSION)},
    }
    monkeypatch.setattr(RunRepository, "find", lambda self, session, run_id: state["rows"].get(run_id))
    monkeypatch.setattr(RunRepository, "list_for_version", lambda self, session, version_uid: (state["rows"][NEWER], state["rows"][OLDER]))
    monkeypatch.setattr(RunRepository, "stage_results", lambda self, session, run_id: tuple(state["stages"][run_id].values()))
    monkeypatch.setattr(
        "auditmanager.documents.repository.DocumentRepository.get_version", lambda self, session, version_uid: SimpleNamespace())
    return state


def _documents() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (OLDER, ROLE_BLOCK_INDEX): _index(100.0), (NEWER, ROLE_BLOCK_INDEX): _index(300.0),
        (OLDER, ROLE_PAGE_CROPS): _crops("older-crop"), (NEWER, ROLE_PAGE_CROPS): _crops("newer-crop"),
        (OLDER, ROLE_RECOGNISED_TEXT): _recognised("older description"), (NEWER, ROLE_RECOGNISED_TEXT): _recognised("newer description"),
    }


def test_the_box_of_a_block_reference_comes_from_the_index_of_the_run_that_minted_it(runs: dict[str, Any]) -> None:
    adapter = Adapter(_documents())
    older = adapter.evidence_boxes_in(None, OLDER)       # type: ignore[arg-type]
    newer = adapter.evidence_boxes_in(None, NEWER)       # type: ignore[arg-type]
    assert older[FIRST_LINE] == ((100.0, 10.0, 150.0, 22.0), "pt", "top_left")
    assert newer[FIRST_LINE] == ((300.0, 10.0, 350.0, 22.0), "pt", "top_left")
    assert adapter.reads == [(OLDER, ROLE_BLOCK_INDEX), (NEWER, ROLE_BLOCK_INDEX)]   # each run read its own index, nobody read the newest for another


def test_the_crops_and_their_descriptions_come_from_the_run_s_own_manifest(runs: dict[str, Any]) -> None:
    adapter = Adapter(_documents())
    (older,) = adapter.portal_crops_in(None, OLDER)       # type: ignore[arg-type]
    (newer,) = adapter.portal_crops_in(None, NEWER)       # type: ignore[arg-type]
    assert (older["blob_id"], older["portal_description"]) == ("older-crop", "older description")
    assert (newer["blob_id"], newer["portal_description"]) == ("newer-crop", "newer description")


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda state: state["stages"].update({OLDER: _stages(OLDER, geometry="failed")}), id="geometry-stage-failed"),
        pytest.param(lambda state: state["stages"].update({OLDER: {}}), id="no-stage-ran"),
        pytest.param(lambda state: state["stages"][OLDER].update(
            page_geometry_extraction=SimpleNamespace(stage_id="page_geometry_extraction", status="succeeded", artifacts=())), id="no-block-index"),
    ],
)
def test_a_run_without_its_own_block_index_has_no_boxes_even_when_a_newer_run_has_one(runs: dict[str, Any], mutation: Any) -> None:
    mutation(runs)
    adapter = Adapter(_documents())
    assert adapter.evidence_boxes_in(None, OLDER) == {}   # type: ignore[arg-type]
    assert adapter.reads == []                            # the newer run's index was not borrowed
    assert adapter.evidence_boxes_in(None, NEWER)[FIRST_LINE][0][0] == 300.0   # type: ignore[arg-type]


def test_a_run_that_published_no_portal_geometry_has_no_crops_and_borrows_none(runs: dict[str, Any]) -> None:
    runs["stages"][OLDER] = _stages(OLDER, portal=False)
    adapter = Adapter(_documents())
    assert adapter.portal_crops_in(None, OLDER) == ()     # type: ignore[arg-type]
    assert adapter.reads == []
    assert len(adapter.portal_crops_in(None, NEWER)) == 1  # type: ignore[arg-type]


def test_an_unknown_run_is_not_found_never_an_empty_answer(runs: dict[str, Any]) -> None:
    for read in (BlockAdapter.evidence_boxes_in, BlockAdapter.portal_crops_in):
        with pytest.raises(DomainError) as refused:
            read(Adapter(_documents()), None, "run_01ARZ3NDEKTSV4RRFFQ69G5FAX")   # type: ignore[arg-type]
        assert refused.value.code == ErrorCode.NOT_FOUND


def test_the_version_wide_portal_source_is_still_the_newest_run_with_portal_geometry(runs: dict[str, Any]) -> None:
    """The portal screens keep reading the version's newest portal source; only the memory reads a run's own."""
    runs["stages"][NEWER] = _stages(NEWER, portal=False)
    source = Adapter(_documents()).portal_source_in(None, VERSION)   # type: ignore[arg-type]
    assert source is not None and source.run_id == OLDER
