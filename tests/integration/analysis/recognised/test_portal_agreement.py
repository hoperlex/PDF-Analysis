"""The stored markdown and block list, re-read and held equal by the stage (`W55B-RECOGNISED-01`).

Container-free. INGEST refuses a disagreeing pair at upload; the stage re-checks the stored
bytes, and each way they can disagree is refused with ``analysis_input_invalid`` and its own
``reason`` -- asserted by that reason, never by "something raised". Every case starts from
the committed ``ar_baseline.zip`` (8 TEXT, 2 IMAGE, 2 STAMP blocks) and changes one thing.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import pytest

from auditmanager.analysis.recognised.portal import read_block_list, read_portal
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.analysis.recognised.recognised_support import members

BASELINE = members("ar_baseline.zip")
PAGES = 8


def _refusal(markdown: bytes, block_list: bytes, page_count: int = PAGES) -> str:
    with pytest.raises(DomainError) as raised:
        read_portal(markdown, block_list, page_count=page_count, stage_id="source_preparation")
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert raised.value.detail_fields.get("stage_id") == "source_preparation"
    return str(raised.value.detail_fields["reason"])


def _edited_list(edit: Callable[[dict[str, Any]], None]) -> bytes:
    document = json.loads(BASELINE.block_list)
    edit(document)
    return json.dumps(document).encode("utf-8")


def _of_type(block_type: str) -> list[str]:
    return [b["block_id"] for b in BASELINE.blocks if b["block_type"] == block_type]


def test_the_committed_pair_agrees_and_every_page_with_a_block_is_known() -> None:
    portal = read_portal(BASELINE.markdown, BASELINE.block_list, page_count=PAGES)

    assert len(portal.blocks) == 12
    assert {b.block_type for b in portal.blocks} == {"text", "image", "stamp"}
    assert len(portal.bodies) == 10  # stamps have no header
    assert portal.pages_with_block == frozenset(range(1, 9))
    assert all(b.page_number == raw["page_index"] + 1 for b, raw in zip(portal.blocks, BASELINE.blocks))


def test_a_stamp_alone_puts_its_page_among_the_pages_with_a_block() -> None:
    def keep_only_a_stamp_on_page_one(document: dict[str, Any]) -> None:
        stamp = next(b for b in document["blocks"] if b["block_type"] == "stamp")
        stamp["page_index"] = 0
        document["blocks"] = [stamp]

    blocks = read_block_list(_edited_list(keep_only_a_stamp_on_page_one), page_count=PAGES)
    assert [(b.block_type, b.page_number) for b in blocks] == [("stamp", 1)]


@pytest.mark.parametrize(
    ("label", "raw"),
    [
        ("not JSON", b"{not json"),
        ("not UTF-8", b"\xff\xfe{}"),
        ("an array", b"[]"),
        ("no blocks list", json.dumps({"pages": []}).encode()),
    ],
)
def test_a_block_list_that_is_not_the_list_is_refused(label: str, raw: bytes) -> None:
    assert _refusal(BASELINE.markdown, raw) == "portal_blocks_invalid", label


@pytest.mark.parametrize(
    ("label", "edit"),
    [
        ("a malformed id", lambda d: d["blocks"][0].update(block_id="blk_XYZ")),
        ("an unknown type", lambda d: d["blocks"][0].update(block_type="table")),
        ("a negative page index", lambda d: d["blocks"][0].update(page_index=-1)),
        ("a boolean page index", lambda d: d["blocks"][0].update(page_index=True)),
        ("a repeated id", lambda d: d["blocks"][1].update(block_id=d["blocks"][0]["block_id"])),
        ("a block that is not an object", lambda d: d["blocks"].append("blk")),
    ],
)
def test_a_block_the_stage_cannot_read_is_refused(label: str, edit: Callable[..., Any]) -> None:
    assert _refusal(BASELINE.markdown, _edited_list(edit)) == "portal_blocks_invalid", label


def test_a_list_of_another_page_count_than_the_pdf_is_refused() -> None:
    assert _refusal(BASELINE.markdown, BASELINE.block_list, page_count=9) == (
        "portal_blocks_page_mismatch"
    )


def test_a_block_on_a_page_the_pdf_does_not_have_is_refused() -> None:
    raw = _edited_list(lambda d: d["blocks"][0].update(page_index=PAGES))
    assert _refusal(BASELINE.markdown, raw) == "portal_blocks_page_mismatch"


def test_a_markdown_that_is_not_utf8_is_refused() -> None:
    assert _refusal(b"\xff" + BASELINE.markdown, BASELINE.block_list) == (
        "recognised_markdown_invalid"
    )


def _markdown_with(replace: str, by: str) -> bytes:
    text = BASELINE.markdown.decode("utf-8")
    assert text.count(replace) == 1
    return text.replace(replace, by).encode("utf-8")


def test_a_text_block_with_no_header_is_refused() -> None:
    identifier = _of_type("text")[0]
    markdown = _markdown_with(f"[TEXT]: {identifier}", f"[TEXT]: blk_{'0' * 32}")
    assert _refusal(markdown, BASELINE.block_list) == "recognised_markdown_mismatch"


def test_a_header_of_the_other_type_is_refused() -> None:
    identifier = _of_type("image")[0]
    markdown = _markdown_with(f"[IMAGE]: {identifier}", f"[TEXT]: {identifier}")
    assert _refusal(markdown, BASELINE.block_list) == "recognised_markdown_mismatch"


def test_a_repeated_header_is_refused() -> None:
    identifier = _of_type("text")[1]
    text = BASELINE.markdown.decode("utf-8") + f"\n### BLOCK #99 [TEXT]: {identifier}\n\nещё\n"
    assert _refusal(text.encode(), BASELINE.block_list) == "recognised_markdown_mismatch"


def test_a_header_for_a_stamp_is_refused() -> None:
    stamp = _of_type("stamp")[0]
    text = BASELINE.markdown.decode("utf-8") + f"\n### BLOCK #99 [TEXT]: {stamp}\n\nштамп\n"
    assert _refusal(text.encode(), BASELINE.block_list) == "recognised_markdown_mismatch"


def test_a_header_for_a_block_the_list_does_not_hold_is_refused() -> None:
    text = BASELINE.markdown.decode("utf-8") + f"\n### BLOCK #99 [IMAGE]: blk_{'e' * 32}\n\nx\n"
    assert _refusal(text.encode(), BASELINE.block_list) == "recognised_markdown_mismatch"


def test_a_lower_case_type_label_still_agrees() -> None:
    identifier = _of_type("text")[0]
    markdown = _markdown_with(f"[TEXT]: {identifier}", f"[text]: {identifier}")
    portal = read_portal(markdown, BASELINE.block_list, page_count=PAGES)
    assert len(portal.bodies) == 10
