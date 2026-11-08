"""`UI-PARITY-C6`: ``BlockAdapter.list_run_finding_blocks`` joins a run's findings to the portal blocks, without a database.

The three saved documents (the run's block index and page inventory, the version's portal blocks) and the run's rows are
stubbed at the seams the adapter reads them through, so what is asserted is the adapter's own work: which answers it
gives when a document is absent (never an empty list passed off as "no links"), the order of the items, the pages it
reports as unlinked, and the refusal of an unknown run. The geometry rule itself is ``test_finding_blocks.py``'s. The
same method over a real run is not exercised here (a stand-backed test is named in the lane report).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import sessionmaker

import auditmanager.findings as findings_module
from auditmanager.analysis.public import ROLE_BLOCK_INDEX, ROLE_PAGE_INVENTORY, ROLE_PORTAL_BLOCKS
from auditmanager.bootstrap.adapters import BlockAdapter
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
FIRST, SECOND = "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV", "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAW"
BLOCK_ON_PAGE_ONE = "blk_" + "1" * 32
BLOCK_ON_PAGE_TWO = "blk_" + "2" * 32

PORTAL = {
    "pages": [
        {"page_number": 1, "width_px": 1200, "height_px": 1600, "rotation_deg": 0, "geometry": "ok"},
        {"page_number": 2, "width_px": 1200, "height_px": 1600, "rotation_deg": 0, "geometry": "geometry_mismatch"},
    ],
    "blocks": [
        {"portal_block_id": BLOCK_ON_PAGE_ONE, "page_number": 1, "bbox_norm": [0.1, 0.1, 0.4, 0.2]},
        {"portal_block_id": BLOCK_ON_PAGE_TWO, "page_number": 2, "bbox_norm": [0.1, 0.1, 0.4, 0.2]},
    ],
}
INDEX = {
    "blocks": [
        {"block_id": "b_000001", "page_number": 1, "bbox": {"x0": 100.0, "y0": 90.0, "x1": 200.0, "y1": 102.0},
         "char_start": 0, "char_end": 20},
        {"block_id": "b_000002", "page_number": 2, "bbox": {"x0": 100.0, "y0": 90.0, "x1": 200.0, "y1": 102.0},
         "char_start": 20, "char_end": 40},
    ],
}
INVENTORY = {
    "pages": [
        {"page_number": 1, "width_pt": 600.0, "height_pt": 800.0, "rotation_deg": 0},
        {"page_number": 2, "width_pt": 600.0, "height_pt": 800.0, "rotation_deg": 0},
    ],
}

DOCUMENTS = {ROLE_PORTAL_BLOCKS: PORTAL, ROLE_BLOCK_INDEX: INDEX, ROLE_PAGE_INVENTORY: INVENTORY}


def stage(status: str, role: str) -> SimpleNamespace:
    return SimpleNamespace(status=status, artifacts=({"role": role, "blob_id": "stub"},))


def stages(*, geometry: str = "succeeded", preparation: str = "succeeded") -> dict[str, Any]:
    return {
        "page_geometry_extraction": stage(geometry, ROLE_BLOCK_INDEX),
        "source_preparation": stage(preparation, ROLE_PAGE_INVENTORY),
    }


def finding(uid: str, observation: str) -> SimpleNamespace:
    return SimpleNamespace(canonical=SimpleNamespace(finding_uid=uid, finding_observation_id=observation), merged=())


def evidence(observation: str, page: int, start: int, end: int) -> SimpleNamespace:
    return SimpleNamespace(finding_observation_id=observation, page_number=page, char_start=start, char_end=end)


class Adapter(BlockAdapter):
    """The adapter with its documents answered from memory; ``portal`` is ``None`` for a version without geometry."""

    def __init__(self, *, portal: bool = True) -> None:
        super().__init__(sessionmaker(), blob_store=None)
        self._with_portal = portal

    def _read(self, work: Any) -> Any:
        return work(None)

    def _portal_source(self, version_uid: str) -> Any:
        return SimpleNamespace(portal_blocks={"role": ROLE_PORTAL_BLOCKS}) if self._with_portal else None

    def _portal_document(self, reference: Any, role: str, version_uid: str) -> dict[str, Any]:
        assert version_uid == VERSION
        return DOCUMENTS[role]


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A run that exists, with two findings (listed out of order) and one evidence item each."""
    state: dict[str, Any] = {
        "run": SimpleNamespace(version_uid=VERSION),
        "stages": stages(),
        # SECOND is listed before FIRST: the answer is ordered by finding uid, not by the order the rows came in.
        "groups": (finding(SECOND, "obs_second"), finding(FIRST, "obs_first")),
        "evidence": (evidence("obs_first", 1, 3, 9), evidence("obs_second", 2, 20, 40)),
    }
    monkeypatch.setattr(RunRepository, "find", lambda self, session, run_id: state["run"])
    monkeypatch.setattr(RunRepository, "stage_results", lambda self, session, run_id: tuple(
        SimpleNamespace(stage_id=name, status=row.status, artifacts=row.artifacts) for name, row in state["stages"].items()
    ))
    monkeypatch.setattr(findings_module, "published_findings", lambda session, run_id: ())
    monkeypatch.setattr(findings_module, "group_published_findings", lambda rows: state["groups"])
    monkeypatch.setattr(findings_module, "published_finding_evidence", lambda session, run_id: state["evidence"])
    return state


def test_each_finding_is_linked_to_the_blocks_that_hold_its_evidence_in_the_order_of_the_finding_uid(run: dict[str, Any]) -> None:
    links = Adapter().list_run_finding_blocks(run_id=RUN)
    assert links.status == "produced"
    assert (links.run_id, links.version_uid) == (RUN, VERSION)
    assert [(item.finding_uid, item.portal_block_ids) for item in links.items] == [
        (FIRST, [BLOCK_ON_PAGE_ONE]),
        # Page 2 is a geometry mismatch: the evidence there is in a line the portal's raster cannot place.
        (SECOND, []),
    ]


def test_a_page_the_portals_raster_does_not_describe_is_named_unlinked(run: dict[str, Any]) -> None:
    assert Adapter().list_run_finding_blocks(run_id=RUN).unlinked_pages == [2]


def test_a_finding_whose_evidence_no_block_covers_is_listed_with_no_blocks(run: dict[str, Any]) -> None:
    run["evidence"] = (evidence("obs_first", 1, 3, 9),)
    run["groups"] = (finding(FIRST, "obs_first"), finding(SECOND, "obs_second"))
    items = Adapter().list_run_finding_blocks(run_id=RUN).items
    assert [(item.finding_uid, item.portal_block_ids) for item in items] == [(FIRST, [BLOCK_ON_PAGE_ONE]), (SECOND, [])]


def test_only_the_canonical_observations_evidence_counts(run: dict[str, Any]) -> None:
    run["evidence"] = (evidence("obs_other", 1, 3, 9), evidence("obs_second", 2, 20, 40))
    run["groups"] = (finding(FIRST, "obs_first"),)
    assert [item.portal_block_ids for item in Adapter().list_run_finding_blocks(run_id=RUN).items] == [[]]


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda run: run.update(stages={}), id="no-stage-ran"),
        pytest.param(lambda run: run.update(stages=stages(geometry="failed")), id="geometry-stage-failed"),
        pytest.param(lambda run: run.update(stages=stages(preparation="failed")), id="inventory-stage-failed"),
        pytest.param(lambda run: run["stages"].update(page_geometry_extraction=SimpleNamespace(status="succeeded", artifacts=())), id="no-block-index"),
        pytest.param(lambda run: run["stages"].update(source_preparation=SimpleNamespace(status="succeeded", artifacts=())), id="no-inventory"),
    ],
)
def test_a_run_without_its_text_layer_geometry_answers_not_produced_and_no_items(run: dict[str, Any], mutation: Any) -> None:
    mutation(run)
    links = Adapter().list_run_finding_blocks(run_id=RUN)
    assert (links.status, links.items, links.unlinked_pages) == ("not_produced", [], [])


def test_a_version_without_portal_geometry_answers_not_produced_and_no_items(run: dict[str, Any]) -> None:
    links = Adapter(portal=False).list_run_finding_blocks(run_id=RUN)
    assert (links.status, links.items, links.unlinked_pages) == ("not_produced", [], [])


def test_an_unknown_run_is_not_found_never_an_empty_answer(run: dict[str, Any]) -> None:
    run["run"] = None
    with pytest.raises(DomainError) as refused:
        Adapter().list_run_finding_blocks(run_id=RUN)
    assert refused.value.code == ErrorCode.NOT_FOUND
