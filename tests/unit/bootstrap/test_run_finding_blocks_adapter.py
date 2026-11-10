"""`UI-PARITY-C6`: ``BlockAdapter.list_run_finding_blocks`` joins a run's findings to the portal blocks, without a database.

The three saved documents (the run's block index and page inventory, the version's portal blocks) and the run's rows are
stubbed at the seams the adapter reads them through, so what is asserted is the adapter's own work: which answers it
gives when a document is absent (never an empty list passed off as "no links"), the order of the items, the pages it
reports as unlinked, which observations' evidence it reads (the canonical one's and every merged one's, once per block,
`D-520`), what it hands the rule's second witness (`D-590`: the evidence's quotation, the recognised text of the text blocks and
the blocks whose reading is doubtful, never an image's description; none of it when the version has no recognised text) and
the refusal of an unknown run. The geometry rule itself is ``test_finding_blocks.py``'s. The same method over a real run is
``tests/integration/analysis/geometry/test_finding_block_links.py``'s (a stand).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import sessionmaker

import auditmanager.findings as findings_module
from auditmanager.analysis.public import (
    KIND_PORTAL_DESCRIPTION,
    KIND_RECOGNISED_TEXT,
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_INVENTORY,
    ROLE_PORTAL_BLOCKS,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
)
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


def stages(*, geometry: str = "succeeded", preparation: str = "succeeded", text_layer: bool = True) -> dict[str, Any]:
    prepared = ({"role": ROLE_PAGE_INVENTORY, "blob_id": "stub"}, *(({"role": ROLE_TEXT_LAYER, "blob_id": "stub"},) if text_layer else ()))
    return {
        "page_geometry_extraction": stage(geometry, ROLE_BLOCK_INDEX),
        "source_preparation": SimpleNamespace(status=preparation, artifacts=prepared),
    }


def finding(uid: str, observation: str, *merged: str) -> SimpleNamespace:
    """A finding group: the canonical observation and the others it merged, in the order given (the rows' order)."""
    return SimpleNamespace(
        canonical=SimpleNamespace(finding_uid=uid, finding_observation_id=observation),
        merged=tuple(SimpleNamespace(finding_uid=uid, finding_observation_id=other) for other in merged),
    )


def evidence(observation: str, page: int, start: int, end: int, quote: str = "") -> SimpleNamespace:
    """An evidence row; ``quote`` is what the real row carries (``EvidenceRow.quote``) and the second witness reads."""
    return SimpleNamespace(finding_observation_id=observation, page_number=page, char_start=start, char_end=end, quote=quote)


class Adapter(BlockAdapter):
    """The adapter with its documents answered from memory; ``portal`` is ``None`` for a version without geometry, and the version
    has recognised text exactly when ``documents`` holds a ``ROLE_RECOGNISED_TEXT`` document."""

    def __init__(self, *, portal: bool = True, documents: dict[str, Any] | None = None) -> None:
        super().__init__(sessionmaker(), blob_store=None)
        self._with_portal = portal
        self._documents = DOCUMENTS if documents is None else documents

    def _read(self, work: Any) -> Any:
        return work(None)

    def _portal_source(self, version_uid: str) -> Any:
        if not self._with_portal:
            return None
        return SimpleNamespace(
            portal_blocks={"role": ROLE_PORTAL_BLOCKS},
            recognised_text={"role": ROLE_RECOGNISED_TEXT} if ROLE_RECOGNISED_TEXT in self._documents else None,
        )

    def _portal_document(self, reference: Any, role: str, version_uid: str) -> dict[str, Any]:
        assert version_uid == VERSION
        if reference is None:           # as the real reader: a reference the run did not record fails closed
            raise self._portal_integrity(role)
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


# --- D-590: the second witness (the recognised text of the portal's text blocks and the text layer's pages) ---------------------
#
# One page, one line that stands across two portal blocks that are cells of one row (LEFT is the left half of the line, RIGHT the
# right half, neither holds the whole line), and one more block (ABOVE) that holds a line of its own. The quotation is in the line's
# right half. What each case sets is the recognised text, the text layer's page and the quotation; the geometry alone links nothing
# to the crossed line. The rule's own conditions are ``test_finding_blocks.py``'s; what is asserted here is what the adapter hands it.

LEFT, RIGHT, ABOVE, PICTURE = "blk_" + "e" * 32, "blk_" + "f" * 32, "blk_" + "d" * 32, "blk_" + "9" * 32
QUOTE = "Степень огнестойкости здания — II."
LEFT_TEXT = "Пункт 1.3 Класс здания по назначению, этажность и площадь указаны в разделе 2."
RIGHT_TEXT = "1.3. Степень огнестойкости здания — II. Класс конструктивной пожарной опасности — С0."
PAGE_TEXT = LEFT_TEXT + "\n" + RIGHT_TEXT       # the text layer's page: the quotation occurs in it once
ROW = (30, 60)          # the line's span of characters: chars 30..60 of the page, the evidence is the span 33..60


def row_documents(
    *, texts: dict[str, str] | None = None, flags: dict[str, list[str]] | None = None, kinds: dict[str, str] | None = None,
    picture: bool = False, entries: list[dict[str, Any]] | None = None, page_text: str | None = PAGE_TEXT,
) -> dict[str, Any]:
    """The three documents of the row, the text layer and, when ``texts`` or ``entries`` is given, the recognised text.

    ``flags`` (by block) are the quality flags of an entry, ``kinds`` replaces an entry's kind, ``picture`` adds an image block over
    the line's middle (a block the line passes through that nothing reads), ``entries`` replaces the entries altogether and
    ``page_text`` is the text layer's text of the page."""
    def block(identifier: str, box: list[float], block_type: str = "text") -> dict[str, Any]:
        return {"portal_block_id": identifier, "page_number": 1, "block_type": block_type, "bbox_norm": box}

    line = {"block_id": "b_000001", "page_number": 1, "bbox": {"x0": 100.0, "y0": 250.0, "x1": 500.0, "y1": 262.0},
            "char_start": ROW[0], "char_end": ROW[1]}
    above = {"block_id": "b_000002", "page_number": 1, "bbox": {"x0": 100.0, "y0": 90.0, "x1": 200.0, "y1": 102.0},
             "char_start": 0, "char_end": 20}
    # 600 x 800 pt: the row stands at y 250..262 pt (0.3125..0.3275 of the page's height), x 100..500 pt (0.1667..0.8333).
    # LEFT covers x 0.1..0.5, RIGHT x 0.5..0.9: each holds half of the line, none holds all of it.
    blocks = [
        block(ABOVE, [0.1, 0.1, 0.4, 0.15]), block(LEFT, [0.1, 0.3, 0.5, 0.35]), block(RIGHT, [0.5, 0.3, 0.9, 0.35]),
    ]
    if picture:
        blocks.append(block(PICTURE, [0.4, 0.3, 0.6, 0.35], "image"))
    documents = {
        ROLE_PORTAL_BLOCKS: {"pages": PORTAL["pages"], "blocks": blocks},
        ROLE_BLOCK_INDEX: {"blocks": [above, line]},
        ROLE_PAGE_INVENTORY: INVENTORY,
        ROLE_TEXT_LAYER: {"pages": [{"page_number": 1, "text": page_text or ""}, {"page_number": 2, "text": ""}]},
    }
    if texts is not None or entries is not None:
        documents[ROLE_RECOGNISED_TEXT] = {"entries": entries if entries is not None else [
            {"portal_block_id": identifier, "page_number": 1, "kind": (kinds or {}).get(identifier, KIND_RECOGNISED_TEXT),
             "quote_source": "recognised", "text": text, "flags": (flags or {}).get(identifier, [])}
            for identifier, text in (texts or {}).items()
        ]}
    return documents


def row_links(documents: dict[str, Any], run: dict[str, Any], quote: str = QUOTE, *, merged: bool = False) -> list[str]:
    run["groups"] = (finding(FIRST, "obs_canonical", "obs_merged") if merged else finding(FIRST, "obs_canonical"),)
    run["evidence"] = (evidence("obs_merged" if merged else "obs_canonical", 1, ROW[0] + 3, ROW[1], quote),)
    links = Adapter(documents=documents).list_run_finding_blocks(run_id=RUN)
    return next(item.portal_block_ids for item in links.items if item.finding_uid == FIRST)


BOTH = {LEFT: LEFT_TEXT, RIGHT: RIGHT_TEXT}


def test_a_line_across_two_blocks_is_linked_to_the_one_whose_recognised_text_holds_the_quotation(run: dict[str, Any]) -> None:
    assert row_links(row_documents(texts=BOTH), run) == [RIGHT]


def test_without_recognised_text_the_answer_is_the_geometrys_and_the_same_line_links_to_no_block(run: dict[str, Any]) -> None:
    # The version has no recognised-text document: no witness, the answer of before `D-590`, whatever the quotation is.
    assert row_links(row_documents(), run) == []
    # The same documents with the text give the link, so the difference between the two answers is the text and nothing else.
    assert row_links(row_documents(texts=BOTH), run) == [RIGHT]


def test_the_witness_can_be_rolled_back_by_one_constant_and_then_neither_document_is_read(run: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BlockAdapter, "_SECOND_WITNESS", False)
    documents, asked = row_documents(texts=BOTH), []
    run["groups"], run["evidence"] = (finding(FIRST, "obs_canonical"),), (evidence("obs_canonical", 1, ROW[0] + 3, ROW[1], QUOTE),)

    class Recording(Adapter):
        def _portal_document(self, reference: Any, role: str, version_uid: str) -> dict[str, Any]:
            asked.append(role)
            return super()._portal_document(reference, role, version_uid)

    links = Recording(documents=documents).list_run_finding_blocks(run_id=RUN)
    assert links.items[0].portal_block_ids == []
    assert ROLE_RECOGNISED_TEXT not in asked and ROLE_TEXT_LAYER not in asked and len(asked) == 3


def test_a_recognised_text_that_holds_no_quotation_adds_no_link_and_takes_none_away(run: dict[str, Any]) -> None:
    # The finding's other evidence is held by the geometry (the line above, inside ABOVE): the witness leaves it as it was.
    run["groups"] = (finding(FIRST, "obs_canonical"),)
    run["evidence"] = (evidence("obs_canonical", 1, 3, 9, "Раздел разработан"), evidence("obs_canonical", 1, ROW[0] + 3, ROW[1], QUOTE))
    plain = Adapter(documents=row_documents()).list_run_finding_blocks(run_id=RUN)
    assert plain.items[0].portal_block_ids == [ABOVE]
    other = {LEFT: LEFT_TEXT, RIGHT: "Другой текст, в нём этой строки нет."}
    witnessed = Adapter(documents=row_documents(texts=other)).list_run_finding_blocks(run_id=RUN)
    assert witnessed.model_dump(mode="json") == plain.model_dump(mode="json")
    both = Adapter(documents=row_documents(texts=BOTH)).list_run_finding_blocks(run_id=RUN)
    assert both.items[0].portal_block_ids == [ABOVE, RIGHT]          # the portal's order: the geometry's block and the witness's


def test_a_flagged_reading_of_a_touching_block_makes_the_witness_abstain(run: dict[str, Any]) -> None:
    # The quotation may stand in exactly the block whose reading failed: a match in the other block is then not trusted.
    assert row_links(row_documents(texts=BOTH, flags={LEFT: ["homoglyph"]}), run) == []
    assert row_links(row_documents(texts=BOTH, flags={RIGHT: ["homoglyph"]}), run) == []


def test_an_unread_block_makes_the_witness_abstain_whether_its_body_is_empty_or_it_has_no_entry(run: dict[str, Any]) -> None:
    assert row_links(row_documents(texts={LEFT: "", RIGHT: RIGHT_TEXT}), run) == []
    assert row_links(row_documents(texts={RIGHT: RIGHT_TEXT}), run) == []


def test_a_picture_the_line_passes_through_is_a_block_nothing_reads_and_the_witness_abstains(run: dict[str, Any]) -> None:
    # `JUDGE-N2` H1 / M3: the plan of this row left image blocks out of the doubtful ones, so a drawing's label was linked to the
    # notes block that repeated it. An image has no reading; it can neither hold the quotation nor rule it out.
    description = {"portal_block_id": PICTURE, "page_number": 1, "kind": KIND_PORTAL_DESCRIPTION, "text": "План этажа"}
    reading = [
        {"portal_block_id": identifier, "page_number": 1, "kind": KIND_RECOGNISED_TEXT, "quote_source": "recognised",
         "text": text, "flags": []}
        for identifier, text in BOTH.items()
    ]
    assert row_links(row_documents(picture=True, entries=[*reading, description]), run) == []
    assert row_links(row_documents(entries=[*reading]), run) == [RIGHT], "and without the picture the link is made"


def test_a_picture_description_is_never_a_reading_even_when_it_is_the_only_place_the_quotation_is_found(run: dict[str, Any]) -> None:
    description = {"portal_block_id": PICTURE, "page_number": 1, "kind": KIND_PORTAL_DESCRIPTION, "text": QUOTE}
    other = {"portal_block_id": RIGHT, "page_number": 1, "kind": KIND_RECOGNISED_TEXT, "quote_source": "recognised",
             "text": "Другой текст, в нём этой строки нет.", "flags": []}
    left = {"portal_block_id": LEFT, "page_number": 1, "kind": KIND_RECOGNISED_TEXT, "quote_source": "recognised",
            "text": LEFT_TEXT, "flags": []}
    assert row_links(row_documents(picture=True, entries=[left, other, description]), run) == []


def test_two_touching_blocks_that_both_hold_the_quotation_give_no_link(run: dict[str, Any]) -> None:
    assert row_links(row_documents(texts={LEFT: RIGHT_TEXT, RIGHT: RIGHT_TEXT}), run) == []


def test_a_quotation_the_text_layer_repeats_on_the_page_is_not_asked_of_the_witness(run: dict[str, Any]) -> None:
    # `JUDGE-N2` H1: the evidence is the FIRST occurrence on the page; a block that holds a later copy would be a match for the
    # text and not for the place. The reading says the quotation is where RIGHT is; the layer says it is also elsewhere.
    twice = row_documents(texts=BOTH, page_text=PAGE_TEXT + "\n" + QUOTE)
    assert row_links(twice, run) == []
    assert row_links(row_documents(texts=BOTH, page_text="Другой текст страницы"), run) == [], "the layer does not hold it at all"
    assert row_links(row_documents(texts=BOTH), run) == [RIGHT]


def test_a_quotation_that_is_too_short_is_not_asked_of_the_witness(run: dict[str, Any]) -> None:
    texts = {LEFT: LEFT_TEXT, RIGHT: RIGHT_TEXT + " 3 м3"}
    assert row_links(row_documents(texts=texts, page_text=PAGE_TEXT + " 3 м3"), run, quote="м3") == []


def test_the_quotation_of_a_merged_observation_is_handed_to_the_witness_too(run: dict[str, Any]) -> None:
    assert row_links(row_documents(texts=BOTH), run, merged=True) == [RIGHT]


def test_recognised_text_without_the_runs_text_layer_is_an_integrity_error_never_a_witness_without_it(run: dict[str, Any]) -> None:
    run["stages"] = stages(text_layer=False)
    run["groups"], run["evidence"] = (finding(FIRST, "obs_canonical"),), (evidence("obs_canonical", 1, ROW[0] + 3, ROW[1], QUOTE),)
    with pytest.raises(DomainError) as refused:
        Adapter(documents=row_documents(texts=BOTH)).list_run_finding_blocks(run_id=RUN)
    assert refused.value.code == ErrorCode.STORAGE_INTEGRITY_ERROR
    # A version with no recognised text does not read the text layer, so its absence is not asked about.
    assert row_links(row_documents(), run) == []


@pytest.mark.parametrize(
    "entries",
    [
        pytest.param([{"portal_block_id": "blk_" + "0" * 32, "page_number": 1, "kind": KIND_RECOGNISED_TEXT, "text": "x", "flags": []}],
                     id="an-entry-of-a-block-the-list-does-not-hold"),
        pytest.param([{"portal_block_id": LEFT, "page_number": 1, "kind": KIND_PORTAL_DESCRIPTION, "text": "x"}],
                     id="a-description-of-a-text-block"),
        pytest.param([{"portal_block_id": PICTURE, "page_number": 1, "kind": KIND_RECOGNISED_TEXT, "text": "x", "flags": []}],
                     id="a-reading-of-an-image-block"),
    ],
)
def test_recognised_text_that_disagrees_with_the_portal_blocks_is_an_integrity_error_never_skipped(
    run: dict[str, Any], entries: list[dict[str, Any]]
) -> None:
    run["groups"], run["evidence"] = (finding(FIRST, "obs_canonical"),), (evidence("obs_canonical", 1, 33, 60, QUOTE),)
    with pytest.raises(DomainError) as refused:
        Adapter(documents=row_documents(picture=True, entries=entries)).list_run_finding_blocks(run_id=RUN)
    assert refused.value.code == ErrorCode.STORAGE_INTEGRITY_ERROR
