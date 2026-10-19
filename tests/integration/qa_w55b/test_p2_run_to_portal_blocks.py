"""Probe 2 -- upload, run, then «Блоки»'s data over HTTP (`W55B-QA-01`).

The bundle goes in through ``uploadDocument`` (INGEST), the version is classified through
``classifyDocumentVersion`` (stage ``P``, section ``AR``; `W59-SECTION-SEAL-01` refuses to
run an unclassified one), the run goes through ``startRun`` and
the served application's own in-process dispatcher in ``recorded`` mode (BUDGET's check,
RECOGNISED's ``source_preparation``, GEOMETRY's ``page_geometry_extraction``), and the
answer comes back through ``listVersionPortalBlocks`` and ``streamVersionPortalBlockCrop``.
No lane test crosses all of these: GEOMETRY's read tests seed the version through the
repository, INGEST's never run one.

Every expected value is computed here from the bundle's own members, with readers written
in ``qa_support.py`` -- never read back from the product.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from w55b_qa_support import (
    MAX_CROP_PIXELS,
    MIN_LONG_SIDE_PX,
    bundle_manifest,
    call,
    classify,
    committed,
    create_project,
    manifest_entry,
    markdown_bodies,
    member_by_suffix,
    pdf_page_aspects,
    png_size,
    portal_blocks,
    rebuild,
    rows,
    scalar,
    sha256_hex,
    start_run,
    upload,
    wait_terminal,
    zip_members,
)

#: ``bundle_manifest.json``'s seeded-defect kinds -> the flag the recognised text must carry.
FLAG_OF_KIND = {
    "latin_homoglyph": "homoglyph",
    "cjk_character": "cjk",
    "doubled_list_marker": "doubled_list_marker",
    "mixed_script_word": "mixed_script",
}


def _uploaded(token: str, archive: bytes, name: str) -> str:
    """Upload ``archive`` into a new project and classify the version (stage ``P``,
    section ``AR``): every probe here runs what it uploads, and since
    `W59-SECTION-SEAL-01` an unclassified version cannot be run."""
    project = create_project(token, f"QA P2 {name}")
    answer = upload(project, archive, token)
    assert answer.status == 201, answer
    classify(answer.json(), token)
    return str(answer.json()["version_uid"])


def _ran(token: str, version_uid: str) -> dict[str, Any]:
    started = start_run(version_uid, token)
    assert started.status == 202, started
    return wait_terminal(started.json()["run_id"], token)


def _crop_blob_ids(engine, run_id: str) -> list[str]:
    found = rows(
        engine,
        "SELECT artifacts FROM stage_result WHERE run_id = :r AND stage_id = 'page_geometry_extraction'",
        r=run_id,
    )
    assert len(found) == 1, found
    return [a["blob_id"] for a in found[0][0] if a["role"] == "geometry.crop_image"]


def _expected_order(blocks: list[dict]) -> list[str]:
    big = 10**12
    ordered = sorted(
        blocks,
        key=lambda b: (b["page_index"], big if b["ordinal"] is None else b["ordinal"], b["block_id"]),
    )
    return [b["block_id"] for b in ordered]


def _assert_crop(version_uid: str, item: dict, token: str, page_aspect: float) -> None:
    crop = item["crop"]
    answer = call("GET", f"/versions/{version_uid}/portal-blocks/{item['portal_block_id']}/crop", token=token)
    assert answer.status == 200, answer
    assert answer.headers["content-type"] == "image/png"
    assert sha256_hex(answer.body) == crop["sha256"]
    width, height = png_size(answer.body)
    assert (width, height) == (crop["width_px"], crop["height_px"])
    assert width * height <= MAX_CROP_PIXELS
    if max(width, height) < MIN_LONG_SIDE_PX:
        # Below the floor only when the pixel cap forced it: then the cap is (nearly) reached.
        assert width * height >= 0.99 * MAX_CROP_PIXELS, (width, height)
    # The crop is the block's clip, not the page: its aspect is the box's on the page.
    x0, y0, x1, y1 = item["bbox_norm"]
    box_aspect = ((x1 - x0) / (y1 - y0)) * page_aspect
    assert abs((width / height) / box_aspect - 1) < 0.01, (width / height, box_aspect)


def test_ar_baseline_blocks_crops_recognised_text_and_descriptions_end_to_end(api, engine, expert) -> None:
    """Expected, for ``ar_baseline.zip`` uploaded and run:

    * before any run, ``status: not_produced``, ``block_count: 0``, no items, and every crop
      ``404``;
    * the run is ``published``; afterwards ``status: produced`` by that run;
    * the block count, the ids and the types equal ``_blocks.json``'s (12: 8 text, 2 image,
      2 stamp), in the order page, ordinal (null last), id; ``page_number = page_index + 1``;
      ``bbox_norm`` is ``coords_norm``; ``polygon_points`` only on the polygon block;
    * every block is ``geometry: ok`` (the bundle's page boxes agree with the PDF) and every
      IMAGE block has a crop: a PNG whose digest is the listed one, whose size is the listed
      one, under 4 000 000 pixels, long side >= 800 unless capped, the box's aspect;
    * a TEXT block carries ``recognised_text`` marked ``recognised`` whose text is the
      markdown body; an IMAGE block ``portal_description`` (the body) and no recognised
      text; a stamp neither, and no crop;
    * no portal URL (``crop_url``, ``/api/crops/``, ``portal.invalid``) appears in any answer;
    * a crop of a TEXT block, of a stamp, and of an unknown id is ``404``."""
    archive = committed("ar_baseline.zip")
    members = zip_members(archive)
    document = json.loads(member_by_suffix(members, "_blocks.json"))
    bodies = markdown_bodies(member_by_suffix(members, "_results.md").decode("utf-8"))
    aspects = pdf_page_aspects(member_by_suffix(members, ".pdf"))
    version = _uploaded(expert, archive, "baseline")

    before, before_items = portal_blocks(version, expert)
    assert (before["status"], before["block_count"], before["produced_by_run_id"], before_items) == (
        "not_produced", 0, None, [],
    )
    some_image = next(b["block_id"] for b in document["blocks"] if b["block_type"] == "image")
    assert call("GET", f"/versions/{version}/portal-blocks/{some_image}/crop", token=expert).status == 404

    run = _ran(expert, version)
    assert run["state"] == "published", run

    first, items = portal_blocks(version, expert, limit=5)  # several pages of the cursor
    assert first["status"] == "produced"
    assert first["produced_by_run_id"] == run["run_id"]
    assert first["block_count"] == len(document["blocks"]) == 12
    assert [i["portal_block_id"] for i in items] == _expected_order(document["blocks"])
    by_id = {b["block_id"]: b for b in document["blocks"]}
    counts = {"text": 0, "image": 0, "stamp": 0}
    for item in items:
        source = by_id[item["portal_block_id"]]
        counts[item["block_type"]] += 1
        assert item["block_type"] == source["block_type"]
        assert item["page_number"] == source["page_index"] + 1
        assert item["page_label"] == source["page_label"]
        assert item["ordinal"] == source["ordinal"]
        assert item["bbox_norm"] == source["coords_norm"]
        assert item["geometry"] == "ok"
        if source.get("shape_type") == "polygon":
            assert item["polygon_points"] == source["polygon_points"]
        else:
            assert "polygon_points" not in item
        if item["block_type"] == "text":
            assert item["recognised_text"]["quote_source"] == "recognised"
            assert item["recognised_text"]["text"] == bodies[item["portal_block_id"]][1]
            assert "crop" not in item and "portal_description" not in item
        elif item["block_type"] == "image":
            assert item["portal_description"] == bodies[item["portal_block_id"]][1]
            assert "recognised_text" not in item
            _assert_crop(version, item, expert, aspects[source["page_index"]])
        else:
            assert not {"crop", "recognised_text", "portal_description"} & set(item)
    assert counts == manifest_entry(bundle_manifest(), "ar_baseline.zip")["blocks"]

    whole = call("GET", f"/versions/{version}/portal-blocks?limit=200", token=expert).body.decode("utf-8")
    for leaked in ("crop_url", "/api/crops/", "portal.invalid", "document_path"):
        assert leaked not in whole, leaked

    text_id = next(i["portal_block_id"] for i in items if i["block_type"] == "text")
    stamp_id = next(i["portal_block_id"] for i in items if i["block_type"] == "stamp")
    for absent in (text_id, stamp_id, "blk_" + "0" * 32):
        answer = call("GET", f"/versions/{version}/portal-blocks/{absent}/crop", token=expert)
        assert answer.status == 404, (absent, answer)
        assert answer.json()["error_code"] == "not_found"


def test_a_second_run_publishes_no_new_crop_blob(api, engine, expert) -> None:
    """Expected: crops are content-addressed. A second run of the same version is
    ``published``; its geometry stage names the same crop blobs as the first run's; the
    ``blob`` table gains no row for them (the whole table gains none for crops: every row the
    second run could add is a JSON artifact, never a PNG); the list now names the second run
    and the crops' digests are unchanged."""
    version = _uploaded(expert, committed("ar_baseline.zip"), "second run")
    first = _ran(expert, version)
    assert first["state"] == "published", first
    _, first_items = portal_blocks(version, expert)
    first_crops = _crop_blob_ids(engine, first["run_id"])
    assert len(first_crops) == 2
    png_rows = scalar(engine, "SELECT count(*) FROM blob WHERE media_type = 'image/png'")

    second = _ran(expert, version)
    assert second["state"] == "published", second
    assert _crop_blob_ids(engine, second["run_id"]) == first_crops
    assert scalar(engine, "SELECT count(*) FROM blob WHERE media_type = 'image/png'") == png_rows
    page, second_items = portal_blocks(version, expert)
    assert page["produced_by_run_id"] == second["run_id"]
    crops = lambda items: {i["portal_block_id"]: i["crop"]["sha256"] for i in items if "crop" in i}  # noqa: E731
    assert crops(second_items) == crops(first_items)


def test_ocr_defects_are_flagged_where_seeded_and_designations_are_not(api, expert) -> None:
    """Expected, for ``ar_baseline_ocr_defects.zip`` uploaded and run (its PDF is the
    baseline's, so the recorded answer applies): every TEXT block's ``recognised_text`` is
    marked ``recognised`` and is the markdown body; each block carrying a seeded flaw of a
    flaggable kind carries that kind's flag; the block carrying only engineering designations
    (``B25``, ``A500C``, ``1.A``, ``REI 150``) carries no flag; no block of a page without a
    seeded flaw carries a flag."""
    archive = committed("ar_baseline_ocr_defects.zip")
    entry = manifest_entry(bundle_manifest(), "ar_baseline_ocr_defects.zip")
    bodies = markdown_bodies(member_by_suffix(zip_members(archive), "_results.md").decode("utf-8"))
    version = _uploaded(expert, archive, "ocr defects")
    run = _ran(expert, version)
    assert run["state"] == "published", run
    _, items = portal_blocks(version, expert)
    flags = {i["portal_block_id"]: i["recognised_text"]["flags"] for i in items if i["block_type"] == "text"}
    for item in items:
        if item["block_type"] == "text":
            assert item["recognised_text"]["quote_source"] == "recognised"
            assert item["recognised_text"]["text"] == bodies[item["portal_block_id"]][1]

    expected: dict[str, set[str]] = {}
    for defect in entry["seeded_text_defects"]:
        wanted = expected.setdefault(defect["block_id"], set())
        if defect["flaggable"]:
            wanted.add(FLAG_OF_KIND[defect["kind"]])
    for block_id, wanted in expected.items():
        if wanted:
            assert wanted <= set(flags[block_id]), (block_id, wanted, flags[block_id])
        else:
            assert flags[block_id] == [], (block_id, flags[block_id])
    for block_id, found in flags.items():
        if block_id not in expected:
            assert found == [], (block_id, found)


def test_a_textless_page_with_a_block_runs_and_its_recognised_text_is_the_stored_count(api, engine, expert) -> None:
    """Expected, for ``image_only_with_block.zip`` ("the scanned PDF with one TEXT block on
    each of its two pages", ``bundle_manifest.json``): the version stores ``textless_pages =
    [1, 2]``; a run reaches the geometry stage (``source_preparation`` admits the pages because
    each holds a block -- "OCR is always marked") whatever the recorded model answer does
    afterwards; both blocks' ``recognised_text`` is marked ``recognised``; and the version's
    ``recognised_character_count`` (INGEST's reader) equals the length of the recognised text
    the list serves for the text-less pages (RECOGNISED's reader)."""
    version = _uploaded(expert, committed("image_only_with_block.zip"), "textless page")
    stored = rows(
        engine,
        "SELECT textless_pages, recognised_character_count FROM document_version WHERE version_uid = :v",
        v=version,
    )
    textless, recognised_count = list(stored[0][0]), stored[0][1]
    assert textless == [1, 2]
    run = _ran(expert, version)
    stages = {s["stage_id"]: s["status"] for s in run["stages"]}
    assert stages.get("source_preparation") == "succeeded", run
    assert stages.get("page_geometry_extraction") == "succeeded", run
    page, items = portal_blocks(version, expert)
    assert page["status"] == "produced"
    on_textless = [i for i in items if i["page_number"] in textless and i["block_type"] == "text"]
    assert len(on_textless) == 2
    assert all(i["recognised_text"]["quote_source"] == "recognised" for i in on_textless)
    assert recognised_count == sum(len(i["recognised_text"]["text"]) for i in on_textless)


def test_a_31_page_bundle_over_the_old_ceiling_runs_through_preparation_and_geometry(api, expert) -> None:
    """Expected: ``pages_31.zip`` (31 pages, refused before W55b) is accepted and a run
    produces its portal geometry: 31 TEXT blocks, one per page, pages 1 to 31."""
    version = _uploaded(expert, committed("pages_31.zip"), "31 pages")
    run = _ran(expert, version)
    stages = {s["stage_id"]: s["status"] for s in run["stages"]}
    assert stages.get("page_geometry_extraction") == "succeeded", run
    page, items = portal_blocks(version, expert)
    assert page["block_count"] == 31
    assert sorted(i["page_number"] for i in items) == list(range(1, 32))


def test_a_page_whose_portal_box_disagrees_is_marked_and_cut_no_crop_while_the_run_succeeds(api, expert) -> None:
    """Expected (plan section B3.7, freeze tolerance 0.5 %): ``ar_baseline.zip`` with page 3's
    ``width_px`` in ``_blocks.json`` raised by 2 % is accepted; the run is ``published``;
    every block on page 3 is ``geometry: geometry_mismatch`` and its IMAGE block has no
    ``crop`` (its crop is ``404``); the other pages stay ``ok`` and page 5's IMAGE block keeps
    its crop."""
    original = committed("ar_baseline.zip")
    document = json.loads(member_by_suffix(zip_members(original), "_blocks.json"))
    page = next(p for p in document["pages"] if p["page_index"] == 2)
    page["width_px"] = round(page["width_px"] * 1.02)
    archive = rebuild(original, {"_blocks.json": json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")})
    version = _uploaded(expert, archive, "page box mismatch")
    run = _ran(expert, version)
    assert run["state"] == "published", run
    _, items = portal_blocks(version, expert)
    for item in items:
        if item["page_number"] == 3:
            assert item["geometry"] == "geometry_mismatch", item
            assert "crop" not in item
            if item["block_type"] == "image":
                crop = call("GET", f"/versions/{version}/portal-blocks/{item['portal_block_id']}/crop", token=expert)
                assert crop.status == 404, crop
        else:
            assert item["geometry"] == "ok", item
    assert any(i["page_number"] == 5 and i["block_type"] == "image" and "crop" in i for i in items)


def test_an_empty_recognised_body_is_left_out_never_sent_empty(api, expert) -> None:
    """Expected: a bundle whose page-3 TEXT body is empty is accepted and runs; on the wire
    that block has no ``recognised_text`` member at all (the contract's ``text`` is
    ``minLength: 1``) -- never an empty string -- while the other TEXT blocks keep theirs."""
    from portal_bundle.bundle import build_bundle, make_files, text_blocks
    from portal_bundle.pdffacts import read_pages

    pdf = member_by_suffix(zip_members(committed("ar_baseline.zip")), ".pdf")
    pages = read_pages(pdf)
    files = make_files(pdf, "qa_empty_body", blocks=text_blocks(pages, bodies={2: ""}))
    try:
        archive = build_bundle(files).data
    except Exception as refused:  # the generator's own validator refusing is a fixture fact
        pytest.skip(f"the fixtures' validator refuses an empty TEXT body: {refused}")
    version = _uploaded(expert, archive, "empty body")
    run = _ran(expert, version)
    stages = {s["stage_id"]: s["status"] for s in run["stages"]}
    assert stages.get("page_geometry_extraction") == "succeeded", run
    _, items = portal_blocks(version, expert)
    texts = [i for i in items if i["block_type"] == "text"]
    empty = [i for i in texts if i["page_number"] == 3]
    assert len(empty) == 1 and "recognised_text" not in empty[0], empty
    assert all(i["recognised_text"]["text"] for i in texts if i["page_number"] != 3)


def test_recognised_text_descriptions_and_the_stamp_audit_never_reach_the_model_request(api, engine, expert) -> None:
    """Expected (R-116, R-117; plan section B3.6): three bundles around the **same PDF** --
    ``ar_baseline.zip`` (image descriptions, stamps, a stamp audit), ``ar_baseline_minimal.zip``
    (text blocks only) and ``ar_baseline_ocr_defects.zip`` (recognised text full of seeded
    flaws) -- produce runs whose one model request is byte-identical (equal
    ``model_call.request_sha256``): nothing the portal recognised or described, and nothing of
    the stamp audit, is in what analysis sends. (Recorded mode answers by that digest, so all
    three runs are ``published``.)"""
    digests = {}
    for name in ("ar_baseline.zip", "ar_baseline_minimal.zip", "ar_baseline_ocr_defects.zip"):
        version = _uploaded(expert, committed(name), f"request {name}")
        run = _ran(expert, version)
        assert run["state"] == "published", (name, run)
        found = rows(engine, "SELECT request_sha256 FROM model_call WHERE run_id = :r", r=run["run_id"])
        assert len(found) == 1, (name, found)
        digests[name] = found[0][0]
    assert len(set(digests.values())) == 1, digests


def test_two_versions_with_equal_crops_share_the_crop_blobs_and_keep_the_text_layer_block_index(
    api, engine, expert
) -> None:
    """Expected: the same bundle uploaded as two documents (two versions) and run once each
    gives both runs the same crop blob ids (content addressed across versions), adds no PNG
    row for the second, and both versions still answer ``getVersionBlocks`` (the text-layer
    block index of `W45`) as ``produced`` beside the portal blocks."""
    first_version = _uploaded(expert, committed("ar_baseline.zip"), "equal crops 1")
    second_version = _uploaded(expert, committed("ar_baseline.zip"), "equal crops 2")
    assert first_version != second_version
    first = _ran(expert, first_version)
    assert first["state"] == "published", first
    png_rows = scalar(engine, "SELECT count(*) FROM blob WHERE media_type = 'image/png'")
    second = _ran(expert, second_version)
    assert second["state"] == "published", second
    assert _crop_blob_ids(engine, second["run_id"]) == _crop_blob_ids(engine, first["run_id"])
    assert scalar(engine, "SELECT count(*) FROM blob WHERE media_type = 'image/png'") == png_rows
    for version in (first_version, second_version):
        index = call("GET", f"/versions/{version}/blocks", token=expert)
        assert index.status == 200, index
        assert index.json()["status"] == "produced"
        assert index.json()["block_count"] > 0


def test_a_500_page_bundle_runs_through_preparation_and_geometry_and_lists_every_block(api, expert) -> None:
    """Expected: the generated 500-page bundle (the upload ceiling; about 30 000 characters, so
    under the budget) is accepted, a run reaches ``source_preparation`` and
    ``page_geometry_extraction`` both ``succeeded``, and ``listVersionPortalBlocks``, paged with
    its cursor, returns 500 distinct TEXT blocks, one per page 1..500, in page order. (The time
    and the API process's peak memory are printed for the report; the rehearsal owns the
    stand's figures.)"""
    import time

    from portal_bundle import generated

    version = _uploaded(expert, generated.bundle_with_pages(500), "500 pages")
    started_at = time.monotonic()
    started = start_run(version, expert)
    assert started.status == 202, started
    run = wait_terminal(started.json()["run_id"], expert, timeout=900)
    elapsed = time.monotonic() - started_at
    stages = {s["stage_id"]: s["status"] for s in run["stages"]}
    print(f"\nw55b-qa: 500-page run {run['state']} in {elapsed:.1f} s; API VmHWM {api.vm_kib('VmHWM')} KiB; stages {stages}")
    assert stages.get("source_preparation") == "succeeded", run
    assert stages.get("page_geometry_extraction") == "succeeded", run
    page, items = portal_blocks(version, expert, limit=200)
    assert page["block_count"] == 500
    assert [i["page_number"] for i in items] == list(range(1, 501))
    assert len({i["portal_block_id"] for i in items}) == 500


def test_the_crop_budget_holds_at_both_ends_through_the_whole_path(api, expert) -> None:
    """Expected (freeze: long side >= 800 px, <= 4 000 000 pixels): the baseline PDF with two
    extra IMAGE blocks -- one covering the whole of page 2, one a 2 % square on page 4 -- is
    accepted and run; the whole-page crop is lowered to the pixel cap (between 99 % and 100 %
    of 4 000 000 pixels) with the page's aspect; the small crop is raised to the floor (long
    side >= 800 px) with the square's aspect on the page; each PNG decodes to its listed size
    and digest."""
    from portal_bundle import portal_format as fmt
    from portal_bundle.blocklist import Block, ImageNote
    from portal_bundle.bundle import build_bundle, make_files

    pdf = member_by_suffix(zip_members(committed("ar_baseline.zip")), ".pdf")
    note = ImageNote("План", ("1.A",), "Синтетическая иллюстрация.", "Блок для проверки бюджета пикселей.", ("ось 1",))
    whole = Block(fmt.KIND_IMAGE, 1, (0.0, 0.0, 1.0, 1.0), image=note)
    small = Block(fmt.KIND_IMAGE, 3, (0.40, 0.40, 0.42, 0.42), image=note)
    archive = build_bundle(make_files(pdf, "qa_crop_budget", extra_blocks=[whole, small])).data
    aspects = pdf_page_aspects(pdf)
    version = _uploaded(expert, archive, "crop budget")
    run = _ran(expert, version)
    stages = {s["stage_id"]: s["status"] for s in run["stages"]}
    assert stages.get("page_geometry_extraction") == "succeeded", run
    _, items = portal_blocks(version, expert)
    images = {i["page_number"]: i for i in items if i["block_type"] == "image"}
    assert set(images) == {2, 4}, images
    for page_number, item in images.items():
        assert item["geometry"] == "ok" and "crop" in item, item
        _assert_crop(version, item, expert, aspects[page_number - 1])
    capped = images[2]["crop"]
    assert 0.99 * MAX_CROP_PIXELS <= capped["width_px"] * capped["height_px"] <= MAX_CROP_PIXELS, capped
    floored = images[4]["crop"]
    assert max(floored["width_px"], floored["height_px"]) >= MIN_LONG_SIDE_PX, floored


def test_a_block_the_portal_marked_failed_is_accepted_and_shown_as_failed(api, expert) -> None:
    """Expected (plan section B3.5, the block-list schema: ``failed`` is tolerated and shown):
    ``ar_baseline.zip`` with its page-3 IMAGE block's ``status`` set to ``failed`` is accepted,
    the run is ``published``, and the list serves that block with ``status: failed`` and
    every other block with ``recognized``."""
    original = committed("ar_baseline.zip")
    document = json.loads(member_by_suffix(zip_members(original), "_blocks.json"))
    target = next(b for b in document["blocks"] if b["block_type"] == "image" and b["page_index"] == 2)
    target["status"] = "failed"
    archive = rebuild(original, {"_blocks.json": json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")})
    version = _uploaded(expert, archive, "failed block")
    run = _ran(expert, version)
    assert run["state"] == "published", run
    _, items = portal_blocks(version, expert)
    statuses = {i["portal_block_id"]: i["status"] for i in items}
    assert statuses.pop(target["block_id"]) == "failed"
    assert set(statuses.values()) == {"recognized"}
    shown = next(i for i in items if i["portal_block_id"] == target["block_id"])
    print(f"\nw55b-qa: a failed IMAGE block is served {'with' if 'crop' in shown else 'without'} a crop")
