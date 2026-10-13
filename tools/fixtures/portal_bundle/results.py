"""The portal's recognised-text rendering: `<stem>_results.md` and `<stem>_results.html`.

The markdown is the member the product reads. After a short header it has a `## Page N`
heading per page and, under it, one section per TEXT or IMAGE block:

    ### BLOCK #<ordinal> [TEXT]: blk_<32 hex>

    > **Created:** ...
    > **Crop:** [Crop](<capability URL>)

    <the block's recognised text>

A STAMP block never appears here; it lives in the block list alone. The envelope matches
headers to the block list in both directions, so the id and type in each header are what
this module must get exactly right.

The HTML is the portal's rendering of the same content. The product keeps only its digest,
never serves or renders it, so a small deterministic document is enough.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from dataclasses import dataclass

from . import portal_format as fmt
from .blocklist import Block

TYPE_LABEL = {fmt.KIND_TEXT: "TEXT", fmt.KIND_IMAGE: "IMAGE", fmt.KIND_STAMP: "STAMP"}


@dataclass(frozen=True)
class StampContext:
    """The title-block fields the portal puts on the document and on every block."""

    code: str
    stage: str
    obj: str
    organization: str

    def document_line(self) -> str:
        return (f"**Stamp:** Code: {self.code} | Stage: {self.stage} | "
                f"Object: {self.obj} | Organization: {self.organization}")

    def block_line(self, sheet: str) -> str:
        return (f"> **Stamp:** Code: {self.code} | Stage: {self.stage} | Sheet: {sheet} | "
                f"Object: {self.obj} | Name:  | Organization: {self.organization} | Revisions: ")


def _image_body(block: Block) -> list[str]:
    note = block.image
    if note is None:
        raise ValueError(f"IMAGE block {block.block_id} has no description")
    return [
        f"**[IMAGE]** | Type: {note.drawing_type} | Axes: {', '.join(note.axes)}",
        "",
        f"**Summary:** {note.summary}",
        "",
        f"**Description:** {note.description}",
        "",
        f"**Entities:** {', '.join(note.entities)}",
    ]


def _body(block: Block) -> list[str]:
    if block.kind == fmt.KIND_IMAGE:
        return _image_body(block)
    return block.text.strip("\n").split("\n")


def render_markdown(
    stem: str, display_path: str, page_count: int, blocks: Sequence[Block],
    *, stamp: StampContext | None,
) -> str:
    lines = [f"# Document: {stem}.pdf", "", f"Path: {display_path}", "",
             f"Generated: {fmt.GENERATED_AT_MARKDOWN}", ""]
    if stamp is not None:
        lines += [stamp.document_line(), ""]
    lines += ["---", ""]
    for page_index in range(page_count):
        lines += [f"## Page {page_index + 1}", ""]
        for block in blocks:
            if block.page_index != page_index or block.kind == fmt.KIND_STAMP:
                continue
            lines += [f"### BLOCK #{block.ordinal} [{TYPE_LABEL[block.kind]}]: {block.block_id}",
                      "", f"> **Created:** {fmt.BLOCK_CREATED_AT}",
                      f"> **Crop:** [Crop]({fmt.crop_url(block.block_id)})"]
            if stamp is not None:
                lines.append(stamp.block_line("" if page_index == 0 else str(page_index + 1)))
            lines += ["", *_body(block), ""]
    # The file ends after the last body line: no blank line, one newline.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def render_html(
    stem: str, display_path: str, page_count: int, blocks: Sequence[Block],
) -> str:
    esc = html.escape
    parts = [
        "<!DOCTYPE html>", '<html lang="ru">', "<head>", '<meta charset="utf-8">',
        f"<title>{esc(stem)}.pdf</title>", "</head>", "<body>",
        f"<h1>Document: {esc(stem)}.pdf</h1>", f"<p>Path: {esc(display_path)}</p>",
        f"<p>Generated: {fmt.GENERATED_AT_MARKDOWN}</p>",
    ]
    for page_index in range(page_count):
        parts.append(f"<h2>Page {page_index + 1}</h2>")
        for block in blocks:
            if block.page_index != page_index or block.kind == fmt.KIND_STAMP:
                continue
            parts += [
                f'<section id="{block.block_id}">',
                f"<h3>BLOCK #{block.ordinal} [{TYPE_LABEL[block.kind]}]</h3>",
                f"<pre>{esc(chr(10).join(_body(block)))}</pre>", "</section>",
            ]
    parts += ["</body>", "</html>"]
    return "\n".join(parts) + "\n"
