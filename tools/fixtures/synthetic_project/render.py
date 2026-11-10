"""SectionDoc -> PDF -> portal bundle ZIP, answer key and previews; refuses on any inconsistency."""

from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

from comparison import scene
from portal_bundle import bundle, results
from portal_bundle import portal_format as fmt
from portal_bundle.blocklist import Block, ImageNote

from .building import DISCLAIMER, OBJECT_CODE, OBJECT_NAME, ORGANISATION
from .kit import bbox_norm, font, texts_in
from .model import SectionDoc


class RenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Rendered:
    stem: str
    pdf: bytes
    zip_bytes: bytes
    answer_key: dict
    page_texts: list[str]
    blocks: tuple


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def page_texts(pdf: bytes) -> list[str]:
    doc = pdfium.PdfDocument(pdf)
    out = []
    for i in range(len(doc)):
        tp = doc[i].get_textpage()
        out.append(tp.get_text_range())
    return out


def build_pdf(doc: SectionDoc) -> tuple[bytes, list[scene.Sheet]]:
    f = font()
    sheets: list[scene.Sheet] = []
    for index, page in enumerate(doc.pages, start=1):
        stamp_ops, stamp_box = scene.frame_and_stamp(
            page.size, designation=doc.designation, title=page.title, stage=doc.stage,
            sheet_no=str(index), revision_label=doc.revision, date=doc.date, organisation=ORGANISATION, font=f)
        ops = list(page.ops.ops) + stamp_ops
        ids = [op.id for op in ops]
        if len(ids) != len(set(ids)):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            raise RenderError(f"{doc.code} page {index}: duplicate operation ids {dup[:5]}")
        sheets.append(scene.Sheet(sheet_id=f"{doc.code}-{index}", title=page.title, sheet_no=str(index),
                                  size=page.size, ops=ops, stamp_bbox=stamp_box))
    meta = scene.DocumentMeta(
        title=f"{doc.designation}. {doc.name}. Стадия {doc.stage}",
        subject=f"{OBJECT_NAME}. {DISCLAIMER}",
        doc_id_seed=f"synthetic-prod-2026-11-09/{doc.code}",
        creation_date="D:20261015000000Z")
    built = scene.build_document(sheets, meta, f)
    return built.data, sheets


def _blocks(doc: SectionDoc, sheets: list[scene.Sheet]) -> list[Block]:
    blocks: list[Block] = []
    for index, (page, sheet) in enumerate(zip(doc.pages, sheets)):
        for region in page.text_regions:
            lines = [t.text for t in texts_in(sheet.ops, region)]
            if not lines:
                raise RenderError(f"{doc.code} page {index + 1}: text region {region} holds no text")
            blocks.append(Block(fmt.KIND_TEXT, index, bbox_norm(region, page.size), text="\n".join(lines)))
        for image in page.images:
            blocks.append(Block(fmt.KIND_IMAGE, index, bbox_norm(image.box, page.size), image=ImageNote(
                image.drawing_type, image.axes, image.summary, image.description, image.entities)))
        if not page.text_regions and not page.images:
            raise RenderError(f"{doc.code} page {index + 1}: no block at all")
    return blocks


def render(doc: SectionDoc, number: int) -> Rendered:
    pdf, sheets = build_pdf(doc)
    texts = page_texts(pdf)
    if len(texts) != len(doc.pages):
        raise RenderError(f"{doc.code}: {len(texts)} pages read, {len(doc.pages)} built")
    norm_pages = [_norm(t) for t in texts]
    # every answer-key quote is on its page, verbatim
    problems = []
    for item in [*doc.expected, *doc.traps]:
        for q in item.quotes:
            if not 1 <= q.page <= len(texts):
                problems.append(f"{item.id}: page {q.page} out of range")
            elif _norm(q.text) not in norm_pages[q.page - 1]:
                problems.append(f"{item.id}: «{q.text}» not on page {q.page}")
    if problems:
        raise RenderError(f"{doc.code}: answer-key quotes not found:\n  " + "\n  ".join(problems))
    for item in doc.expected:
        if item.category not in ("internal_contradiction", "explicit_placeholder", "documentation"):
            raise RenderError(f"{doc.code}: {item.id} has unknown category {item.category}")

    stem = f"{doc.designation}"
    blocks = _blocks(doc, sheets)
    previous = bundle.DISPLAY_PATH
    try:
        bundle.DISPLAY_PATH = f"{OBJECT_CODE} / [{doc.abbr}] {doc.name} / {{stem}}"
        files = bundle.make_files(pdf, stem, blocks=blocks, stamp=results.StampContext(
            code=doc.designation, stage=doc.stage, obj=f"{OBJECT_NAME} (синтетический объект)",
            organization=f"{ORGANISATION} (вымышленная организация)"))
    finally:
        bundle.DISPLAY_PATH = previous
    built = bundle.build_bundle(files)
    if not built.verdict.accepted:
        raise RenderError(f"{doc.code}: the portal validator refused the bundle: {built.verdict}")

    key = {
        "schema": "synthetic-prod-section-key/1",
        "object": OBJECT_NAME, "designation": doc.designation, "section_code": doc.code,
        "section_abbr": doc.abbr, "section_name": doc.name, "stage": doc.stage, "number": number,
        "pdf_sha256": hashlib.sha256(pdf).hexdigest(), "pages": len(doc.pages),
        "page_titles": [p.title for p in doc.pages],
        "blocks": {"text": sum(b.kind == fmt.KIND_TEXT for b in files.blocks),
                   "image": sum(b.kind == fmt.KIND_IMAGE for b in files.blocks)},
        "image_blocks": [
            {"block_id": b.block_id, "page": b.page_index + 1, "bbox_norm": list(b.bbox),
             "type": b.image.drawing_type, "summary": b.image.summary}
            for b in files.blocks if b.kind == fmt.KIND_IMAGE],
        "expected_findings": [
            {"id": e.id, "category": e.category, "summary": e.summary,
             "quotes": [{"page": q.page, "text": q.text} for q in e.quotes]} for e in doc.expected],
        "traps_no_finding": [
            {"id": t.id, "why": t.why, "quotes": [{"page": q.page, "text": q.text} for q in t.quotes]}
            for t in doc.traps],
        "disclaimer": DISCLAIMER,
    }
    return Rendered(stem=stem, pdf=pdf, zip_bytes=built.data, answer_key=key, page_texts=texts, blocks=files.blocks)


def write_previews(r: Rendered, out_dir: Path, page_sizes: list[tuple[float, float]], dpi: int = 60) -> None:
    """Page PNGs at a low resolution and every IMAGE block cropped at 110 dpi, for a human look."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(r.pdf)
    for i in range(len(doc)):
        doc[i].render(scale=dpi / 72).to_pil().save(out_dir / f"page_{i + 1:02d}.png")
    for b in r.blocks:
        if b.kind != fmt.KIND_IMAGE:
            continue
        page = doc[b.page_index]
        img = page.render(scale=110 / 72).to_pil()
        w, h = img.size
        x0, y0, x1, y1 = b.bbox
        img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))).save(out_dir / f"crop_p{b.page_index + 1}_{b.ordinal:02d}.png")


def dump_json(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
