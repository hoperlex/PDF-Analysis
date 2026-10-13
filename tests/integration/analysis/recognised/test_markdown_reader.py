"""The ``_results.md`` reader of ``analysis.recognised`` (`W55B-RECOGNISED-01`).

Container-free. The reader restates INGEST's body definition rather than importing it (a
deep import across bounded contexts is ALR-05's refusal), so the first test holds the two
equal, character for character, over every committed bundle. The rest are the edge cases
the brief names: CRLF, an empty body, a large file.
"""

from __future__ import annotations

import time

import pytest

from auditmanager.analysis.recognised.markdown import body_of, read_blocks
from auditmanager.ingest.bundle_envelope import recognised_characters
from tests.integration.analysis.recognised.recognised_support import committed_names, members

HEADER = "### BLOCK #{n} [{kind}]: blk_{hex:032x}"


@pytest.mark.parametrize("name", committed_names())
def test_the_reader_counts_every_body_as_ingest_does(name: str) -> None:
    """INGEST's ``recognised_characters`` is the product's other reading of a body."""
    bundle = members(name)
    text = bundle.markdown.decode("utf-8")
    wanted = {
        block["block_id"] for block in bundle.blocks if block["block_type"] in ("text", "image")
    }

    read = {block.portal_block_id: len(block.body) for block in read_blocks(text)}
    ingest = recognised_characters(text, wanted)

    assert set(read) == wanted
    assert read == ingest


def test_every_committed_bundle_was_compared() -> None:
    """The parametrisation above is not vacuous: seven bundles, five with bodies."""
    names = committed_names()
    assert len(names) == 7
    with_bodies = [
        name for name in names if read_blocks(members(name).markdown.decode("utf-8"))
    ]
    assert len(with_bodies) == 6  # every bundle but image_only.zip, whose list holds no block


def _markdown(*sections: tuple[int, str, str], crlf: bool = False) -> str:
    """A small portal-shaped markdown: ``(page, kind, body)`` per block."""
    lines = ["# Document: x.pdf", "", "---", ""]
    page = None
    for index, (number, kind, body) in enumerate(sections, start=1):
        if number != page:
            lines += [f"## Page {number}", ""]
            page = number
        lines += [
            HEADER.format(n=index, kind=kind, hex=index),
            "",
            "> **Created:** 2026-07-07 07:36:38 UTC",
            "> **Crop:** [Crop](https://portal.invalid/api/crops/x)",
            "",
            *body.split("\n"),
            "",
        ]
    text = "\n".join(lines) + "\n"
    return text.replace("\n", "\r\n") if crlf else text


def test_a_crlf_file_reads_to_the_same_bodies_as_its_lf_twin() -> None:
    sections = ((1, "TEXT", "первая строка\nвторая строка"), (2, "IMAGE", "**[IMAGE]** | Type: План"))
    lf = read_blocks(_markdown(*sections))
    crlf = read_blocks(_markdown(*sections, crlf=True))

    assert [b.body for b in crlf] == [b.body for b in lf]
    assert [b.body for b in lf] == ["первая строка\nвторая строка", "**[IMAGE]** | Type: План"]
    assert all("\r" not in block.body for block in crlf)


def test_a_crlf_file_counts_as_ingest_counts_it() -> None:
    text = _markdown((1, "TEXT", "а\nб"), (1, "TEXT", ""), crlf=True)
    read = {b.portal_block_id: len(b.body) for b in read_blocks(text)}
    assert read == recognised_characters(text, set(read))


def test_a_block_with_no_body_reads_as_an_empty_body() -> None:
    text = _markdown((1, "TEXT", ""), (1, "TEXT", "текст"))
    blocks = read_blocks(text)

    assert [b.body for b in blocks] == ["", "текст"]
    assert [b.position for b in blocks] == [0, 1]


def test_a_header_directly_followed_by_the_next_header_is_an_empty_body() -> None:
    text = "## Page 1\n" + HEADER.format(n=1, kind="TEXT", hex=1) + "\n" + HEADER.format(
        n=2, kind="IMAGE", hex=2
    ) + "\nописание\n"
    blocks = read_blocks(text)
    assert [(b.label, b.body) for b in blocks] == [("text", ""), ("image", "описание")]


def test_only_the_leading_quote_lines_are_metadata() -> None:
    """A quote line inside the text is the portal's text, not its metadata."""
    lines = ["", "> **Created:** x", "> **Crop:** [Crop](u)", "", "текст", "> **Note:** цитата", ""]
    assert body_of(lines) == "текст\n> **Note:** цитата"


def test_a_page_heading_ends_a_body_and_starts_no_block() -> None:
    text = (
        "## Page 1\n"
        + HEADER.format(n=1, kind="TEXT", hex=1)
        + "\nстрока\n## Page 2\nхвост без блока\n"
    )
    blocks = read_blocks(text)
    assert [(b.portal_block_id, b.body) for b in blocks] == [(f"blk_{1:032x}", "строка")]


def test_the_type_label_is_read_case_insensitively_as_ingest_reads_it() -> None:
    text = "## Page 1\n### BLOCK #1 [Text]: blk_" + "a" * 32 + "\nтекст\n"
    assert [b.label for b in read_blocks(text)] == ["text"]


def test_a_file_of_five_hundred_pages_and_nearly_sixteen_mebibytes_is_read_whole() -> None:
    """INGEST bounds the markdown at 16 MiB; the reader takes the largest file it can see."""
    body = ("Строка распознанного текста, достаточно длинная для объёма. " * 8 + "\n") * 36
    sections = [(page, "TEXT", body) for page in range(1, 501)]
    text = _markdown(*sections)
    size = len(text.encode("utf-8"))
    assert 15 * 2**20 < size <= 16 * 2**20, size

    started = time.monotonic()
    blocks = read_blocks(text)
    elapsed = time.monotonic() - started

    assert len(blocks) == 500
    assert all(block.body == body.strip("\n") for block in blocks)
    assert elapsed < 30, f"reading {size} bytes took {elapsed:.1f} s"
