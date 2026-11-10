"""`D-353`, judge J3 F2: the adapter hands the run's text lines to the page guard, so a page they prove shifted is ``unlinked``.

A text on a page cannot lie outside it. A line above the page (or past its edge) means the extractor's coordinates are not the
page's -- it reports positions from the MediaBox's origin -- so the finding to block relation derived on that page would put
the evidence in the block that stands at the *shifted* place. The page must be named in ``unlinked_pages`` (the web reads
those blocks as unknown, not as "no findings") and link to nothing. Stubbed at the seams ``test_run_finding_blocks_adapter`` uses.
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

RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
FINDING = "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV"
BLOCK = "blk_" + "1" * 32

PORTAL = {
    "pages": [{"page_number": 1, "width_px": 1200, "height_px": 1600, "rotation_deg": 0, "geometry": "ok"}],
    "blocks": [{"portal_block_id": BLOCK, "page_number": 1, "bbox_norm": [0.0, 0.0, 1.0, 1.0]}],
}
INVENTORY = {"pages": [{"page_number": 1, "width_pt": 600.0, "height_pt": 800.0, "rotation_deg": 0}]}


def index(top: float) -> dict[str, Any]:
    """Two lines; the second at ``top`` (the judge's row B puts a line of a MediaBox-origin page at -31.7)."""
    def line(number: int, y0: float, start: int) -> dict[str, Any]:
        return {"block_id": f"b_{number:06d}", "page_number": 1, "bbox": {"x0": 150.0, "y0": y0, "x1": 441.2, "y1": y0 + 12.0},
                "char_start": start, "char_end": start + 20}
    return {"blocks": [line(1, 400.0, 0), line(2, top, 21)]}


class Adapter(BlockAdapter):
    def __init__(self, document: dict[str, Any]) -> None:
        super().__init__(sessionmaker(), blob_store=None)
        self._documents = {ROLE_PORTAL_BLOCKS: PORTAL, ROLE_BLOCK_INDEX: document, ROLE_PAGE_INVENTORY: INVENTORY}

    def _read(self, work: Any) -> Any:
        return work(None)

    def _portal_source(self, version_uid: str) -> Any:
        return SimpleNamespace(portal_blocks={"role": ROLE_PORTAL_BLOCKS}, recognised_text=None)

    def _portal_document(self, reference: Any, role: str, version_uid: str) -> dict[str, Any]:
        return self._documents[role]


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch) -> None:
    stages = {
        "page_geometry_extraction": SimpleNamespace(stage_id="page_geometry_extraction", status="succeeded",
                                                    artifacts=({"role": ROLE_BLOCK_INDEX, "sha256": None, "size_bytes": None},)),
        "source_preparation": SimpleNamespace(stage_id="source_preparation", status="succeeded",
                                              artifacts=({"role": ROLE_PAGE_INVENTORY, "sha256": None, "size_bytes": None},)),
    }
    finding = SimpleNamespace(canonical=SimpleNamespace(finding_uid=FINDING, finding_observation_id="obs_1"), merged=())
    monkeypatch.setattr(RunRepository, "find", lambda self, session, run_id: SimpleNamespace(version_uid=VERSION))
    monkeypatch.setattr(RunRepository, "stage_results", lambda self, session, run_id: tuple(stages.values()))
    monkeypatch.setattr(findings_module, "published_findings", lambda session, run_id: ())
    monkeypatch.setattr(findings_module, "group_published_findings", lambda rows: (finding,))
    monkeypatch.setattr(findings_module, "published_finding_evidence", lambda session, run_id: (
        SimpleNamespace(finding_observation_id="obs_1", page_number=1, char_start=0, char_end=20, quote="Раздел разработан"),))


def test_a_page_with_a_line_above_it_is_unlinked_and_its_evidence_links_to_nothing(run: None) -> None:
    links = Adapter(index(top=-31.7)).list_run_finding_blocks(run_id=RUN)
    assert links.status == "produced" and links.unlinked_pages == [1]
    assert [(item.finding_uid, item.portal_block_ids) for item in links.items] == [(FINDING, [])]


def test_the_same_page_with_every_line_inside_it_links_normally(run: None) -> None:
    links = Adapter(index(top=500.0)).list_run_finding_blocks(run_id=RUN)
    assert links.unlinked_pages == []
    assert [(item.finding_uid, item.portal_block_ids) for item in links.items] == [(FINDING, [BLOCK])]
