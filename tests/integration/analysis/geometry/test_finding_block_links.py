"""``BlockAdapter.list_run_finding_blocks`` over a real recorded run, on the lane's PostgreSQL and S3 (D-354).

`UI-PARITY-C6` proved the read against stubs at the adapter's own seams (``tests/unit/bootstrap/test_run_finding_blocks_adapter.py``)
and the rule as a pure function (``tests/unit/analysis/test_finding_blocks.py``). This module runs the whole join: the
``ar_baseline.zip`` bundle is published as a version, the recorded adapter carries a run to ``published`` through the real
chain, and the shipped adapter then answers ``listRunFindingBlocks`` from the three documents that run and that version stored
(the run's block index and page inventory, the version's portal blocks), each read with the digest its stage result recorded.

* ``produced`` with an item for every published finding, in the order of the finding uid, every linked id a block of
  ``listVersionPortalBlocks``;
* each link held against the PDF's own glyphs and against the portal's recognised text (``tests/support/finding_block_proof.py``):
  no linked block that misses the quotation's glyphs, no block that covers them and is not linked, every quotation in the text of
  the TEXT blocks it is linked to;
* ``not_produced`` for a run that never reached the geometry stage, and for a run of a version with no portal geometry;
* ``404`` for an unknown run;
* evidence on a page the portal's raster does not describe (``geometry_mismatch``) is named in ``unlinked_pages`` and links to
  nothing -- never to a block of another page, never to the page's blocks that cannot be trusted.

The run harness of ``tests/integration/runs`` is loaded by path (``reads_support``).
"""

from __future__ import annotations

import json

import pytest

from auditmanager.findings import group_published_findings, published_finding_evidence, published_findings
from auditmanager.runs import start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.analysis.geometry.reads_support import (
    TEXT_ID,
    block_adapter,
    harness,
    produced,
    run_published,
    seed_bundle_version,
)
from tests.integration.analysis.recognised.recognised_support import members
from tests.support.finding_block_proof import BlockFact, EvidenceFact, PdfOracle, analyse
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

_no_network = harness._no_network
engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter
seeded = harness.seeded
new_key = harness.new_key

ABSENT_RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _published(session, run_id):
    """``(groups, evidence by the canonical observation's id)`` of the run's published findings."""
    groups = sorted(group_published_findings(published_findings(session, run_id)), key=lambda g: g.canonical.finding_uid)
    evidence: dict[str, list] = {}
    for row in published_finding_evidence(session, run_id):
        evidence.setdefault(row.finding_observation_id, []).append(row)
    return groups, evidence


def _facts(groups, evidence):
    return {
        group.canonical.finding_uid: [
            EvidenceFact(e.page_number, e.char_start, e.char_end, e.quote)
            for e in evidence.get(group.canonical.finding_observation_id, ())
        ]
        for group in groups
    }


def _block_facts(adapter, version_uid):
    return [
        BlockFact(
            b.portal_block_id, b.page_number, b.block_type, tuple(b.bbox_norm),
            None if b.recognised_text is None else b.recognised_text.text,
        )
        for b in adapter.list_portal_blocks(version_uid=version_uid).blocks
    ]


# -- produced ------------------------------------------------------------------------------


def test_a_produced_run_has_an_item_for_every_published_finding_in_the_order_of_the_finding_uid(session, produced) -> None:
    links = produced["adapter"].list_run_finding_blocks(run_id=produced["run_id"])
    groups, evidence = _published(session, produced["run_id"])
    assert (links.status, links.run_id, links.version_uid) == ("produced", produced["run_id"], produced["version_uid"])
    assert len(groups) == 3, "the recorded reply holds three observations, each grounded"
    assert [item.finding_uid for item in links.items] == [group.canonical.finding_uid for group in groups]
    assert [item.finding_uid for item in links.items] == sorted(item.finding_uid for item in links.items)
    assert all(item.portal_block_ids for item in links.items), "every finding of the baseline sits in some block"
    assert links.unlinked_pages == []


def test_every_linked_id_is_a_block_of_the_version_and_lies_on_a_page_of_the_findings_evidence(session, produced) -> None:
    adapter = produced["adapter"]
    links = adapter.list_run_finding_blocks(run_id=produced["run_id"])
    listed = {b.portal_block_id: b for b in adapter.list_portal_blocks(version_uid=produced["version_uid"]).blocks}
    groups, evidence = _published(session, produced["run_id"])
    pages = {
        group.canonical.finding_uid: {e.page_number for e in evidence[group.canonical.finding_observation_id]}
        for group in groups
    }
    for item in links.items:
        assert len(set(item.portal_block_ids)) == len(item.portal_block_ids)
        for identifier in item.portal_block_ids:
            assert identifier in listed
            assert listed[identifier].page_number in pages[item.finding_uid]
    assert TEXT_ID not in {i for item in links.items for i in item.portal_block_ids}, "page 1 carries no evidence"


def test_each_link_agrees_with_the_pdfs_own_glyphs_and_the_portals_recognised_text(session, produced) -> None:
    """No wrong link, no missed link, and every quotation is in the recognised text of the TEXT blocks it links to."""
    adapter = produced["adapter"]
    links = adapter.list_run_finding_blocks(run_id=produced["run_id"])
    groups, evidence = _published(session, produced["run_id"])
    oracle = PdfOracle(members("ar_baseline.zip").pdf)
    try:
        report = analyse(
            items=[(i.finding_uid, i.portal_block_ids, i.finding_uid) for i in links.items],
            evidence=_facts(groups, evidence),
            blocks=_block_facts(adapter, produced["version_uid"]),
            unlinked_pages=links.unlinked_pages,
            oracle=oracle,
        )
    finally:
        oracle.close()
    assert report["pairs"], "the baseline links something"
    assert [p for p in report["pairs"] if p["geometry"] in ("WRONG", "unplaced")] == []
    assert report["misses"] == []
    assert all(f["has_truth"] for f in report["findings"]), "the oracle placed every quotation in some block"
    for pair in report["pairs"]:
        if pair["block_type"] == "text":
            assert pair["text"] == "contains", pair


# -- not produced and not found ------------------------------------------------------------


def test_a_run_that_never_reached_the_geometry_stage_is_not_produced_though_its_version_has_portal_geometry(
    session, produced, new_key
) -> None:
    started = start_audit_run(
        session, version_uid=produced["version_uid"],
        analysis_profile_id=str(V1_REFERENCE_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id),
        provider_mode="recorded", idempotency_key=new_key("finding-links-unexecuted"),
    )
    adapter = produced["adapter"]
    assert adapter.list_portal_blocks(version_uid=produced["version_uid"]).status == "produced"
    links = adapter.list_run_finding_blocks(run_id=str(started.run_id))
    assert (links.status, links.items, links.unlinked_pages) == ("not_produced", [], [])
    assert (links.run_id, links.version_uid) == (str(started.run_id), produced["version_uid"])


def test_a_run_of_a_version_without_portal_geometry_is_not_produced_though_its_text_layer_geometry_exists(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    run_id = run_published(session, seeded.version_uid, new_key("finding-links-bare"), blob_store, recorded_adapter, provider_config)
    adapter = block_adapter(session, blob_store)
    assert adapter.get_block_index(version_uid=seeded.version_uid).status == "produced"
    assert adapter.list_portal_blocks(version_uid=seeded.version_uid).status == "not_produced"
    links = adapter.list_run_finding_blocks(run_id=run_id)
    assert (links.status, links.items, links.unlinked_pages) == ("not_produced", [], [])
    assert (links.run_id, links.version_uid) == (run_id, seeded.version_uid)


def test_an_unknown_run_is_not_found_never_an_empty_answer(session, blob_store) -> None:
    with pytest.raises(DomainError) as refused:
        block_adapter(session, blob_store).list_run_finding_blocks(run_id=ABSENT_RUN)
    assert refused.value.code is ErrorCode.NOT_FOUND


# -- a page the portal's raster does not describe ------------------------------------------


def _with_landscape_rasters(pages: tuple[int, ...]) -> bytes:
    """The baseline block list with the raster of each named PDF page turned on its side (aspect no longer the page's)."""
    document = json.loads(members("ar_baseline.zip").block_list)
    for page in document["pages"]:
        if page["page_index"] + 1 in pages:
            page["width_px"], page["height_px"] = page["height_px"], page["width_px"]
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")


def test_evidence_on_a_page_the_portals_raster_does_not_describe_is_unlinked_never_in_a_wrong_block(
    session, produced, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    """Pages 2 and 8 are refused (``geometry_mismatch``). The baseline findings quote pages (2, 6), (3, 7) and (8):

    * the first keeps only its page-6 block, the second keeps both its blocks, the third (page 8 only) has none;
    * nothing is linked on a refused page although the page's TEXT block would cover the quotation in full;
    * the pages are named in ``unlinked_pages`` so that their blocks are not read as "no findings".
    """
    baseline = produced["adapter"].list_run_finding_blocks(run_id=produced["run_id"])
    version_uid = seed_bundle_version(session, blob_store, block_list=_with_landscape_rasters((2, 8)))
    run_id = run_published(session, version_uid, new_key("finding-links-refused-pages"), blob_store, recorded_adapter, provider_config)
    adapter = block_adapter(session, blob_store)
    portal = adapter.list_portal_blocks(version_uid=version_uid)
    refused_blocks = {b.portal_block_id for b in portal.blocks if b.geometry != "ok"}
    assert {b.page_number for b in portal.blocks if b.geometry != "ok"} == {2, 8}
    listed = {b.portal_block_id: b for b in portal.blocks}

    links = adapter.list_run_finding_blocks(run_id=run_id)
    assert links.status == "produced" and links.unlinked_pages == [2, 8]
    groups, evidence = _published(session, run_id)
    assert len(groups) == 3
    pages = {
        item.finding_uid: sorted({e.page_number for e in evidence[g.canonical.finding_observation_id]})
        for item, g in zip(links.items, groups)
    }
    for item in links.items:
        assert not set(item.portal_block_ids) & refused_blocks
        assert {listed[b].page_number for b in item.portal_block_ids} <= set(pages[item.finding_uid]) - {2, 8}
    by_pages = {tuple(pages[item.finding_uid]): item.portal_block_ids for item in links.items}
    assert by_pages[(8,)] == []
    assert {listed[b].page_number for b in by_pages[(2, 6)]} == {6}
    assert {listed[b].page_number for b in by_pages[(3, 7)]} == {3, 7}
    # What survives on the pages that stay is what the unrefused run linked there (the same TEXT blocks by id: the block list
    # is the baseline's, only the two rasters differ).
    baseline_ids = {i for item in baseline.items for i in item.portal_block_ids}
    kept_ids = {i for item in links.items for i in item.portal_block_ids}
    assert kept_ids == {i for i in baseline_ids if listed[i].page_number not in (2, 8)}
