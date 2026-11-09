"""`UI-PARITY-C6`: ``BlockAdapter.list_run_finding_blocks`` joins a run's findings to the portal blocks, without a database.

The three saved documents (the run's block index and page inventory, the version's portal blocks) and the run's rows are
stubbed at the seams the adapter reads them through, so what is asserted is the adapter's own work: which answers it
gives when a document is absent (never an empty list passed off as "no links"), the order of the items, the pages it
reports as unlinked, which observations' evidence it reads (the canonical one's and every merged one's, once per block,
`D-520`), and the refusal of an unknown run. The geometry rule itself is ``test_finding_blocks.py``'s. The same method over a
real run is not exercised here (a stand-backed test is named in the lane report).
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


def finding(uid: str, observation: str, *merged: str) -> SimpleNamespace:
    """A finding group: the canonical observation and the others it merged, in the order given (the rows' order)."""
    return SimpleNamespace(
        canonical=SimpleNamespace(finding_uid=uid, finding_observation_id=observation),
        merged=tuple(SimpleNamespace(finding_uid=uid, finding_observation_id=other) for other in merged),
    )


def evidence(observation: str, page: int, start: int, end: int) -> SimpleNamespace:
    return SimpleNamespace(finding_observation_id=observation, page_number=page, char_start=start, char_end=end)


class Adapter(BlockAdapter):
    """The adapter with its documents answered from memory; ``portal`` is ``None`` for a version without geometry."""

    def __init__(self, *, portal: bool = True, documents: dict[str, Any] | None = None) -> None:
        super().__init__(sessionmaker(), blob_store=None)
        self._with_portal = portal
        self._documents = DOCUMENTS if documents is None else documents

    def _read(self, work: Any) -> Any:
        return work(None)

    def _portal_source(self, version_uid: str) -> Any:
        return SimpleNamespace(portal_blocks={"role": ROLE_PORTAL_BLOCKS}) if self._with_portal else None

    def _portal_document(self, reference: Any, role: str, version_uid: str) -> dict[str, Any]:
        assert version_uid == VERSION
        return self._documents[role]


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


def test_the_evidence_of_an_observation_the_finding_does_not_own_counts_for_nothing(run: dict[str, Any]) -> None:
    # `D-520` lifted "only the canonical observation's evidence counts" to "the finding's observations' evidence counts": an
    # observation that is neither the canonical one nor one the finding merged (here the other finding's) still links to nothing.
    run["evidence"] = (evidence("obs_other", 1, 3, 9), evidence("obs_second", 2, 20, 40))
    run["groups"] = (finding(FIRST, "obs_first"),)
    assert [item.portal_block_ids for item in Adapter().list_run_finding_blocks(run_id=RUN).items] == [[]]


# --- D-520: the evidence of the merged observations --------------------------------------------------------------------------
#
# One page, three lines stacked one above the other (A on top), three portal blocks that each hold exactly one line, listed
# in the portal's order A, B, C. Which observation's evidence is on which line is what each case sets.

LINE_A, LINE_B, LINE_C = (0, 20), (20, 40), (40, 60)
BLOCK_A, BLOCK_B, BLOCK_C = "blk_" + "a" * 32, "blk_" + "b" * 32, "blk_" + "c" * 32


def three_lines() -> dict[str, Any]:
    def line(name: str, top: float, span: tuple[int, int]) -> dict[str, Any]:
        return {"block_id": name, "page_number": 1, "bbox": {"x0": 100.0, "y0": top, "x1": 200.0, "y1": top + 12.0},
                "char_start": span[0], "char_end": span[1]}

    def block(identifier: str, top: float) -> dict[str, Any]:
        return {"portal_block_id": identifier, "page_number": 1, "bbox_norm": [0.1, top, 0.4, top + 0.1]}

    return {
        ROLE_PORTAL_BLOCKS: {"pages": PORTAL["pages"], "blocks": [block(BLOCK_A, 0.1), block(BLOCK_B, 0.3), block(BLOCK_C, 0.5)]},
        # 800 pt high: the lines stand at 90, 250 and 410 pt, inside the blocks that start at 80, 240 and 400 pt.
        ROLE_BLOCK_INDEX: {"blocks": [line("b_000001", 90.0, LINE_A), line("b_000002", 250.0, LINE_B), line("b_000003", 410.0, LINE_C)]},
        ROLE_PAGE_INVENTORY: INVENTORY,
    }


def blocks_of(run: dict[str, Any], *, finding_uid: str = FIRST) -> list[str]:
    links = Adapter(documents=three_lines()).list_run_finding_blocks(run_id=RUN)
    return next(item.portal_block_ids for item in links.items if item.finding_uid == finding_uid)


def test_a_merged_observations_evidence_on_a_linkable_page_is_linked(run: dict[str, Any]) -> None:
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_merged"),)
    run["evidence"] = (evidence("obs_canonical", 1, *LINE_A), evidence("obs_merged", 1, *LINE_B))
    assert blocks_of(run) == [BLOCK_A, BLOCK_B]


def test_a_finding_whose_only_evidence_is_a_merged_observations_is_linked(run: dict[str, Any]) -> None:
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_merged"),)
    run["evidence"] = (evidence("obs_merged", 1, *LINE_C),)
    assert blocks_of(run) == [BLOCK_C]


def test_a_block_that_holds_the_evidence_of_two_observations_is_listed_once(run: dict[str, Any]) -> None:
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_first_merged", "obs_second_merged"),)
    run["evidence"] = (
        evidence("obs_canonical", 1, 3, 9),         # line A
        evidence("obs_first_merged", 1, 10, 15),    # line A again, another span of it
        evidence("obs_second_merged", 1, *LINE_B),  # line B
        evidence("obs_second_merged", 1, 25, 30),   # line B again, by the same observation
    )
    assert blocks_of(run) == [BLOCK_A, BLOCK_B]


def test_the_canonical_observations_blocks_come_first_then_the_merged_ones_in_the_order_of_their_ids(run: dict[str, Any]) -> None:
    # The portal lists A, B, C. The canonical evidence is on C, "obs_1" on B, "obs_2" on A: the answer is neither the portal's
    # order (A, B, C) nor the order the merged rows came in (obs_2, obs_1), but the canonical first, then by observation id.
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_2", "obs_1"),)
    run["evidence"] = (evidence("obs_2", 1, *LINE_A), evidence("obs_1", 1, *LINE_B), evidence("obs_canonical", 1, *LINE_C))
    assert blocks_of(run) == [BLOCK_C, BLOCK_B, BLOCK_A]
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_1", "obs_2"),)
    run["evidence"] = tuple(reversed(run["evidence"]))
    assert blocks_of(run) == [BLOCK_C, BLOCK_B, BLOCK_A]


def test_a_merged_observation_gives_a_block_to_its_own_finding_only(run: dict[str, Any]) -> None:
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_merged"), finding(SECOND, "obs_second"))
    run["evidence"] = (evidence("obs_merged", 1, *LINE_B), evidence("obs_second", 1, *LINE_C))
    assert blocks_of(run, finding_uid=FIRST) == [BLOCK_B]
    assert blocks_of(run, finding_uid=SECOND) == [BLOCK_C]


def test_a_merged_observations_evidence_on_an_unlinked_page_links_nothing_and_the_page_stays_named(run: dict[str, Any]) -> None:
    # Page 2 is a geometry mismatch (the module's PORTAL): lifting the canonical-only limit does not link what the rule refuses.
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_merged"),)
    run["evidence"] = (evidence("obs_canonical", 1, 3, 9), evidence("obs_merged", 2, 20, 40))
    links = Adapter().list_run_finding_blocks(run_id=RUN)
    assert [(item.finding_uid, item.portal_block_ids) for item in links.items] == [(FIRST, [BLOCK_ON_PAGE_ONE])]
    assert links.unlinked_pages == [2]


def test_the_answer_keeps_its_shape_with_merged_observations(run: dict[str, Any]) -> None:
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_merged"),)
    run["evidence"] = (evidence("obs_canonical", 1, *LINE_A), evidence("obs_merged", 1, *LINE_B))
    links = Adapter(documents=three_lines()).list_run_finding_blocks(run_id=RUN)
    assert links.model_dump(mode="json") == {
        "run_id": RUN, "version_uid": VERSION, "status": "produced", "unlinked_pages": [2],
        "items": [{"finding_uid": FIRST, "portal_block_ids": [BLOCK_A, BLOCK_B]}],
    }


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
