"""The ``prepared.recognised_text`` document (`W55B-RECOGNISED-01`, ``P02_SEAMS`` section 4.8).

Container-free: the builder over the committed bundles, checked by a strict structural
validator written in ``recognised_support`` (no JSON schema exists for this role), plus the
entry order, the two kinds, STAMP blocks, the verbatim text and byte determinism.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from auditmanager.analysis.engine.serialization import canonical_bytes
from auditmanager.analysis.recognised.artifact import build_recognised_text
from auditmanager.analysis.recognised.markdown import read_blocks
from auditmanager.analysis.recognised.portal import read_portal
from tests.integration.analysis.recognised.recognised_support import (
    VERSION_UID,
    assert_recognised_text_shape,
    committed_names,
    manifest_entry,
    members,
)

ACCEPTED = [name for name in committed_names() if manifest_entry(name)["expected"] == "accepted"]


def _build(name: str, markdown: bytes | None = None) -> dict:
    bundle = members(name)
    text = bundle.markdown if markdown is None else markdown
    page_count = manifest_entry(name)["page_count"]
    portal = read_portal(text, bundle.block_list, page_count=page_count)
    return build_recognised_text(portal, version_uid=VERSION_UID, markdown=text)


@pytest.mark.parametrize("name", ACCEPTED)
def test_every_accepted_bundle_builds_the_sealed_shape(name: str) -> None:
    bundle = members(name)
    document = _build(name)
    assert_recognised_text_shape(
        document,
        version_uid=VERSION_UID,
        markdown=bundle.markdown,
        page_count=manifest_entry(name)["page_count"],
    )
    counts = manifest_entry(name)["blocks"]
    assert len(document["entries"]) == counts["text"] + counts["image"]


def test_the_validator_is_strict_enough_to_refuse_each_way_an_entry_can_be_wrong() -> None:
    """Six damaged copies of a good document; the validator refuses every one."""
    bundle = members("ar_baseline.zip")
    good = _build("ar_baseline.zip")
    text_entry = next(e for e in good["entries"] if e["kind"] == "recognised_text")
    image_entry = next(e for e in good["entries"] if e["kind"] == "portal_description")
    damages = [
        lambda d: d.update(extra=1),
        lambda d: d.update(results_sha256="0" * 64),
        lambda d: d["entries"][d["entries"].index(text_entry)].update(char_start=0),
        lambda d: d["entries"][d["entries"].index(text_entry)].update(quote_source="pdf"),
        lambda d: d["entries"][d["entries"].index(image_entry)].update(flags=[]),
        lambda d: d["entries"].reverse(),
    ]
    for damage in damages:
        copy = json.loads(json.dumps(good))
        # Re-find the two entries in the copy by identity of their ids.
        text_entry = next(e for e in copy["entries"] if e["portal_block_id"] == text_entry["portal_block_id"])
        image_entry = next(e for e in copy["entries"] if e["portal_block_id"] == image_entry["portal_block_id"])
        damage(copy)
        with pytest.raises(AssertionError):
            assert_recognised_text_shape(
                copy, version_uid=VERSION_UID, markdown=bundle.markdown, page_count=8
            )


def test_a_text_block_is_marked_recognised_and_an_image_block_is_a_description_only() -> None:
    bundle = members("ar_baseline.zip")
    types = {b["block_id"]: b["block_type"] for b in bundle.blocks}
    document = _build("ar_baseline.zip")

    for entry in document["entries"]:
        if types[entry["portal_block_id"]] == "text":
            assert entry["kind"] == "recognised_text"
            assert entry["quote_source"] == "recognised"
            assert "flags" in entry
        else:
            assert types[entry["portal_block_id"]] == "image"
            assert entry["kind"] == "portal_description"
            assert "quote_source" not in entry and "flags" not in entry
    kinds = [e["kind"] for e in document["entries"]]
    assert kinds.count("recognised_text") == 8 and kinds.count("portal_description") == 2


def test_a_stamp_block_has_no_entry() -> None:
    bundle = members("ar_baseline.zip")
    stamps = {b["block_id"] for b in bundle.blocks if b["block_type"] == "stamp"}
    assert len(stamps) == 2
    assert not stamps & {e["portal_block_id"] for e in _build("ar_baseline.zip")["entries"]}


def test_the_quote_source_marker_is_on_recognised_entries_and_nowhere_else() -> None:
    document = _build("ar_baseline.zip")
    marked = [e for e in document["entries"] if "quote_source" in e]
    assert marked and all(e["kind"] == "recognised_text" for e in marked)
    assert all(e["quote_source"] == "recognised" for e in marked)
    assert "quote_source" not in document


def test_each_entry_text_is_the_body_exactly_as_the_markdown_holds_it() -> None:
    bundle = members("ar_baseline_ocr_defects.zip")
    bodies = {b.portal_block_id: b.body for b in read_blocks(bundle.markdown.decode("utf-8"))}
    for entry in _build("ar_baseline_ocr_defects.zip")["entries"]:
        assert entry["text"] == bodies[entry["portal_block_id"]]
    assert any("кажд梯й" in e["text"] for e in _build("ar_baseline_ocr_defects.zip")["entries"])


def test_entries_are_ordered_by_page_then_by_place_in_the_markdown() -> None:
    """Page 3 of the baseline holds a TEXT and an IMAGE block; swapping their sections in
    the markdown swaps them in the artifact, and moving page 8 to the top moves nothing."""
    bundle = members("ar_baseline.zip")
    text = bundle.markdown.decode("utf-8")
    original = [(e["page_number"], e["portal_block_id"]) for e in _build("ar_baseline.zip")["entries"]]
    assert [page for page, _ in original] == sorted(page for page, _ in original)

    page_3 = text.index("## Page 3\n")
    page_4 = text.index("## Page 4\n")
    section = text[page_3:page_4]
    first = section.index("### BLOCK")
    second = section.index("### BLOCK", first + 1)
    swapped = section[:first] + section[second:] + section[first:second]
    page_8 = text.index("## Page 8\n")
    edited = text[:page_3] + swapped + text[page_4:page_8]
    moved = text[: text.index("## Page 1\n")] + text[page_8:].rstrip("\n") + "\n\n" + edited[
        text.index("## Page 1\n") :
    ]
    rebuilt = [(e["page_number"], e["portal_block_id"]) for e in _build("ar_baseline.zip", moved.encode())["entries"]]

    on_page_3 = [identifier for page, identifier in original if page == 3]
    assert [identifier for page, identifier in rebuilt if page == 3] == on_page_3[::-1]
    assert [page for page, _ in rebuilt] == sorted(page for page, _ in rebuilt)
    assert sorted(rebuilt) == sorted(original)


def test_an_empty_body_is_kept_as_an_entry_flagged_empty_text() -> None:
    bundle = members("ar_baseline_minimal.zip")
    text = bundle.markdown.decode("utf-8")
    page_2 = text.index("## Page 2\n")
    page_3 = text.index("## Page 3\n")
    header_end = text.index("> **Crop:**", page_2)
    header_end = text.index("\n", header_end) + 1
    emptied = (text[:header_end] + "\n" + text[page_3:]).encode("utf-8")

    document = _build("ar_baseline_minimal.zip", emptied)
    on_page_2 = [e for e in document["entries"] if e["page_number"] == 2]
    assert len(on_page_2) == 1
    assert on_page_2[0]["text"] == "" and on_page_2[0]["flags"] == ["empty_text"]


def test_results_sha256_is_the_digest_of_the_stored_markdown_bytes() -> None:
    bundle = members("ar_baseline.zip")
    assert _build("ar_baseline.zip")["results_sha256"] == hashlib.sha256(bundle.markdown).hexdigest()


def test_the_same_input_builds_the_same_bytes() -> None:
    first = canonical_bytes(_build("ar_baseline_ocr_defects.zip"))
    second = canonical_bytes(_build("ar_baseline_ocr_defects.zip"))
    assert first == second


def test_the_recorded_flags_land_on_the_seeded_blocks() -> None:
    entries = {e["portal_block_id"]: e for e in _build("ar_baseline_ocr_defects.zip")["entries"]}
    seeded = manifest_entry("ar_baseline_ocr_defects.zip")["seeded_text_defects"]
    flagged_blocks = {d["block_id"] for d in seeded if d["flaggable"]}
    designation_block = {d["block_id"] for d in seeded if not d["flaggable"]}

    assert {i for i, e in entries.items() if e["flags"]} == flagged_blocks
    assert all(entries[i]["flags"] == [] for i in designation_block)
