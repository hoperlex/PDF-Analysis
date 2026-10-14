#!/usr/bin/env python3
"""Build the two synthetic 500-page portal bundles of W55B-REHEARSAL-01, deterministically.

    python scripts/rehearsal/w55b/build_bundles.py text-rich [--pages 500] [--seed 55] [--out PATH]
    python scripts/rehearsal/w55b/build_bundles.py low-text  [--pages 500] [--seed 55] [--out PATH]
    python scripts/rehearsal/w55b/build_bundles.py check                  # small builds, twice each

``text-rich`` is a real text layer on every page (the AR corpus writer and its embedded Cyrillic
font subset), dense like an architectural section, so the document is far above the analysis
input budget of the configured model and ceiling; the portal's block list carries one TEXT block
per page whose recognised text is the page's own text layer as the independent extractor reads it.

``low-text`` is a scanned set: every page one 300 dpi grayscale JPEG (A4, every fifth page
landscape) of scan-like content -- paper grain, a framed drawing with axes, walls, openings,
hatching and dimension lines, word-like marks in a notes area and a title block, dust -- with a
thin text layer (a sheet label) on two pages of three and none on the third. Every page carries an
IMAGE block over the drawing (so every page is admitted "for its portal block"), a TEXT block over
the notes with recognised text, and a STAMP block over the title block; every tenth IMAGE block is
a polygon. The drawing's size varies, so some crops reach the 4 000 000-pixel cap and some do not.

Both reuse ``tools/fixtures`` (the AR corpus PDF writer, the font, the portal-bundle builders and
the reference validator) and are then read by the product's own bundle reader and envelope
(``extract_bundle``, ``admit_bundle``), which must accept them; the summary records the product's
counts and the input budget the configured model and ceiling give. Same seed, same bytes: ``check``
builds a few pages of each variant twice and compares the archives' SHA-256.

Outputs go under ``.local/rehearsal-w55b/bundles/`` (git-ignored) unless ``--out`` says otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import common  # noqa: E402

sys.path[:0] = [str(common.ROOT / "src"), str(common.ROOT / "tools" / "fixtures")]

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import build_ar_corpus  # noqa: E402
from ar_corpus import content, document, pdfwrite  # noqa: E402
from ar_corpus.pdfwrite import Name  # noqa: E402
from portal_bundle import portal_format as fmt  # noqa: E402
from portal_bundle import zipwrite  # noqa: E402
from portal_bundle.blocklist import Block, ImageNote  # noqa: E402
from portal_bundle.bundle import GENERATOR_LIMITS, build_bundle, make_files, pack  # noqa: E402
from portal_bundle.pdffacts import PageFacts  # noqa: E402
from portal_bundle.validate import validate  # noqa: E402

DPI = 300
A4 = (document.PAGE_WIDTH, document.PAGE_HEIGHT)
JPEG_QUALITY = 60

# ------------------------------------------------------------------ text


def vocabulary() -> list[str]:
    """Russian words of the AR corpus' own text, so every glyph is in the embedded subset."""
    words: set[str] = set()
    for page in content.PAGES:
        for line in page.lines:
            for raw in line.text.split():
                word = raw.strip(".,;:()«»—–-\"'!?").lower()
                if len(word) >= 2 and all("а" <= c <= "я" or c == "ё" for c in word):
                    words.add(word)
    return sorted(words)


def sentence(rng: random.Random, words: list[str]) -> str:
    chosen = [rng.choice(words) for _ in range(rng.randint(6, 14))]
    text = " ".join(chosen)
    return text[0].upper() + text[1:] + "."


def wrapped_lines(rng: random.Random, words: list[str], font, size: float, width: float,
                  count: int) -> list[str]:
    lines: list[str] = []
    current = ""
    while len(lines) < count:
        for token in sentence(rng, words).split():
            trial = token if not current else current + " " + token
            if font.text_width(trial, size) > width:
                lines.append(current)
                current = token
                if len(lines) == count:
                    break
            else:
                current = trial
    return lines


# ------------------------------------------------------------------ (a) text-rich


def text_rich(pages: int, seed: int, out: Path) -> dict:
    font = build_ar_corpus.load_font()
    words = vocabulary()
    size, leading = 10.0, 13.5
    placements = []
    for number in range(1, pages + 1):
        rng = random.Random(f"w55b-text:{seed}:{number}")
        y = document.PAGE_HEIGHT - document.MARGIN_TOP
        page = [(f"Синтетический текстовый раздел. Лист {number} из {pages}.", 11.0,
                 document.MARGIN_LEFT, y)]
        y -= leading * 1.5
        for text in wrapped_lines(rng, words, font, size, document.TEXT_WIDTH, 46):
            page.append((text, size, document.MARGIN_LEFT, y))
            y -= leading
        placements.append(page)
    pdf = document.simple_text_pdf(font, placements)
    stem = f"w55b_rehearsal_text_{pages}"
    files = make_files(pdf, stem)                 # one TEXT block per page, the layer as read back
    built = build_bundle(files)                   # the reference validator must accept it
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(built.data)
    return {"variant": "text-rich", "stem": stem, "pdf_bytes": len(pdf),
            "blocks_json_bytes": len(files.blocks_json), "results_md_bytes": len(files.results_md),
            "blocks_by_kind": _kinds(files.blocks)}


# ------------------------------------------------------------------ (b) low-text


def _grain(rng: random.Random, size: int = 640) -> Image.Image:
    """A paper-grain tile from the seeded generator (Pillow's own noise is not seedable)."""
    tile = Image.frombytes("L", (size, size), rng.randbytes(size * size))
    return tile.point(lambda v: 238 + (v * 15) // 256)


def _words(draw: ImageDraw.ImageDraw, rng: random.Random, box: tuple[int, int, int, int],
           height: int, gap: int) -> None:
    """Rows of word-like marks: what a scan of printed text looks like from afar."""
    x0, y0, x1, y1 = box
    y = y0
    while y + height <= y1:
        x = x0 + rng.randint(0, 30)
        line_end = x1 - rng.randint(0, (x1 - x0) // 4)
        while x < line_end:
            width = rng.randint(height, height * 7)
            if x + width > line_end:
                break
            shade = rng.randint(25, 70)
            draw.rectangle((x, y + rng.randint(0, 3), x + width, y + height), fill=shade)
            x += width + rng.randint(gap // 2, gap)
        y += int(height * 1.9)


def _drawing(draw: ImageDraw.ImageDraw, rng: random.Random, box: tuple[int, int, int, int]) -> None:
    """A framed plan: axes with bubbles, walls, openings, hatching, dimension lines, labels."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, outline=20, width=6)
    nx, ny = rng.randint(3, 8), rng.randint(3, 7)
    xs = [x0 + (x1 - x0) * (i + 1) // (nx + 1) for i in range(nx)]
    ys = [y0 + (y1 - y0) * (j + 1) // (ny + 1) for j in range(ny)]
    for x in xs:                                            # axes
        draw.line((x, y0 + 40, x, y1 - 40), fill=90, width=2)
        draw.ellipse((x - 28, y0 + 8, x + 28, y0 + 64), outline=30, width=3)
    for y in ys:
        draw.line((x0 + 40, y, x1 - 40, y), fill=90, width=2)
        draw.ellipse((x0 + 8, y - 28, x0 + 64, y + 28), outline=30, width=3)
    for _ in range(rng.randint(12, 30)):                    # walls
        if rng.random() < 0.5:
            y = rng.choice(ys) + rng.randint(-6, 6)
            a, b = sorted(rng.sample(xs, 2)) if len(xs) > 1 else (x0 + 60, x1 - 60)
            draw.line((a, y, b, y), fill=rng.randint(10, 40), width=rng.randint(8, 18))
        else:
            x = rng.choice(xs) + rng.randint(-6, 6)
            a, b = sorted(rng.sample(ys, 2)) if len(ys) > 1 else (y0 + 60, y1 - 60)
            draw.line((x, a, x, b), fill=rng.randint(10, 40), width=rng.randint(8, 18))
    for _ in range(rng.randint(4, 12)):                     # openings (door swings)
        cx, cy, r = rng.choice(xs), rng.choice(ys), rng.randint(40, 110)
        start = rng.choice((0, 90, 180, 270))
        draw.arc((cx - r, cy - r, cx + r, cy + r), start, start + 90, fill=35, width=3)
    for _ in range(rng.randint(1, 4)):                      # hatching
        hx0 = rng.randint(x0 + 80, max(x0 + 81, x1 - 400))
        hy0 = rng.randint(y0 + 80, max(y0 + 81, y1 - 300))
        hx1, hy1 = hx0 + rng.randint(120, 380), hy0 + rng.randint(100, 280)
        for k in range(hx0 - (hy1 - hy0), hx1, 22):
            draw.line((k, hy1, k + (hy1 - hy0), hy0), fill=80, width=2)
        draw.rectangle((hx0, hy0, hx1, hy1), outline=25, width=4)
    for _ in range(rng.randint(3, 8)):                      # dimension lines with ticks
        y = rng.randint(y0 + 70, y1 - 70)
        a, b = sorted((rng.randint(x0 + 70, x1 - 70), rng.randint(x0 + 70, x1 - 70)))
        draw.line((a, y, b, y), fill=50, width=2)
        for t in (a, b):
            draw.line((t - 12, y + 12, t + 12, y - 12), fill=40, width=3)
        _words(draw, rng, (a + (b - a) // 3, y - 34, a + (b - a) // 3 + 120, y - 8), 20, 14)
    for _ in range(rng.randint(3, 9)):                      # room labels
        lx, ly = rng.randint(x0 + 80, x1 - 300), rng.randint(y0 + 80, y1 - 120)
        _words(draw, rng, (lx, ly, lx + rng.randint(140, 280), ly + 70), 22, 16)


def _scan_page(rng: random.Random, width: int, height: int, regions: dict) -> bytes:
    page = Image.new("L", (width, height), 245)
    grain = _grain(rng)
    ox, oy = rng.randrange(640), rng.randrange(640)
    for x in range(-ox, width, 640):
        for y in range(-oy, height, 640):
            page.paste(grain, (x, y))
    draw = ImageDraw.Draw(page)

    def px(box):
        return (int(box[0] * width), int(box[1] * height), int(box[2] * width), int(box[3] * height))

    _drawing(draw, rng, px(regions["drawing"]))
    _words(draw, rng, px(regions["notes"]), 24, 18)
    stamp = px(regions["stamp"])
    draw.rectangle(stamp, outline=20, width=5)
    sx0, sy0, sx1, sy1 = stamp
    for k in range(1, 4):
        draw.line((sx0, sy0 + (sy1 - sy0) * k // 4, sx1, sy0 + (sy1 - sy0) * k // 4), fill=30, width=3)
    _words(draw, rng, (sx0 + 20, sy0 + 12, sx1 - 20, sy1 - 10), 20, 14)
    page = page.filter(ImageFilter.GaussianBlur(0.8))       # the scanner's optics
    draw = ImageDraw.Draw(page)
    for _ in range(rng.randint(300, 1200)):                  # dust
        x, y, r = rng.randrange(width), rng.randrange(height), rng.choice((1, 1, 2, 3))
        draw.ellipse((x, y, x + r, y + r), fill=rng.randint(60, 160))
    out = io.BytesIO()
    page.save(out, "JPEG", quality=JPEG_QUALITY, dpi=(DPI, DPI))
    return out.getvalue()


def _regions(rng: random.Random, landscape: bool) -> dict:
    """Normalised boxes (top-left origin): the drawing, the notes under it, the title block."""
    width = rng.uniform(0.35, 0.86)
    height = rng.uniform(0.25, 0.66 if not landscape else 0.58)
    x0 = rng.uniform(0.05, 0.94 - width)
    y0 = rng.uniform(0.04, 0.10)
    drawing = (x0, y0, x0 + width, y0 + height)
    notes = (0.06, min(0.84, y0 + height + 0.03), 0.52, 0.94)
    stamp = (0.58, 0.84, 0.95, 0.96)
    return {"drawing": drawing, "notes": notes, "stamp": stamp}


def _rounded(box):
    return tuple(round(v, 4) for v in box)


def _notes_text(rng: random.Random, words: list[str]) -> str:
    lines = []
    for k in range(1, rng.randint(3, 6) + 1):
        lines.append(f"{k}. {sentence(rng, words)} {sentence(rng, words)}")
    return "\n".join(lines)


_DRAWING_TYPES = ("План этажа", "Разрез", "Фасад", "Узел", "Схема расположения")


def _image_note(rng: random.Random, words: list[str], number: int) -> ImageNote:
    return ImageNote(
        drawing_type=rng.choice(_DRAWING_TYPES),
        axes=tuple(str(k) for k in range(1, rng.randint(3, 8) + 1)),
        summary=f"Синтетический чертёж листа {number}.",
        description=" ".join(sentence(rng, words) for _ in range(rng.randint(2, 4))),
        entities=tuple(sorted({rng.choice(words) for _ in range(4)})),
    )


def _image_pdf(pages: int, seed: int, font) -> tuple[bytes, list[PageFacts], list[dict]]:
    """The scanned PDF: one JPEG XObject per page, a thin text layer on two pages of three."""
    pdf = pdfwrite.Pdf()
    catalog_ref, pages_ref = pdf.reserve(), pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)
    kids, facts, layout = [], [], []
    for number in range(1, pages + 1):
        rng = random.Random(f"w55b-scan:{seed}:{number}")
        landscape = number % 5 == 0
        width_pt, height_pt = (A4[1], A4[0]) if landscape else A4
        width_px, height_px = fmt.page_px(width_pt), fmt.page_px(height_pt)
        regions = _regions(rng, landscape)
        jpeg = _scan_page(rng, width_px, height_px, regions)
        image_ref = pdf.add_stream({
            "Type": Name("XObject"), "Subtype": Name("Image"), "Width": width_px,
            "Height": height_px, "ColorSpace": Name("DeviceGray"), "BitsPerComponent": 8,
            "Filter": Name("DCTDecode"),
        }, jpeg)
        stream = (f"q {pdfwrite.num(width_pt)} 0 0 {pdfwrite.num(height_pt)} 0 0 cm /Im1 Do Q\n")
        resources: dict = {"XObject": {"Im1": image_ref}}
        thin = number % 3 != 0
        label = f"Лист {number}"
        if thin:
            sx0, _, _, sy1 = regions["stamp"]
            stream += pdfwrite.show_text(font, document.FONT_RESOURCE, label, 8.0,
                                         sx0 * width_pt + 12, (1 - sy1) * height_pt + 8)
            resources["Font"] = {document.FONT_RESOURCE: font_ref}
        content_ref = pdf.add_stream({}, stream.encode("ascii"))
        kids.append(pdf.add({
            "Type": Name("Page"), "Parent": pages_ref, "MediaBox": [0, 0, width_pt, height_pt],
            "Resources": resources, "Contents": content_ref,
        }))
        facts.append(PageFacts(width_pt, height_pt, 0, label if thin else ""))
        layout.append({"regions": regions, "jpeg_bytes": len(jpeg)})
    pdf.put(pages_ref, {"Type": Name("Pages"), "Kids": kids, "Count": len(kids)})
    pdf.put(catalog_ref, {"Type": Name("Catalog"), "Pages": pages_ref})
    return pdf.serialize(catalog_ref, document.info_dictionary(), document.DOC_ID), facts, layout


def low_text(pages: int, seed: int, out: Path) -> dict:
    font = build_ar_corpus.load_font()
    words = vocabulary()
    started = time.monotonic()
    pdf, facts, layout = _image_pdf(pages, seed, font)
    raster_seconds = time.monotonic() - started
    blocks: list[Block] = []
    for index, item in enumerate(layout):
        rng = random.Random(f"w55b-blocks:{seed}:{index + 1}")
        regions = item["regions"]
        drawing = _rounded(regions["drawing"])
        polygon = None
        if (index + 1) % 10 == 0:                           # an L-shaped outline
            x0, y0, x1, y1 = drawing
            xm, ym = round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4)
            polygon = ((x0, y0), (x1, y0), (x1, ym), (xm, ym), (xm, y1), (x0, y1))
        blocks.append(Block(fmt.KIND_IMAGE, index, drawing, polygon=polygon,
                            image=_image_note(rng, words, index + 1)))
        blocks.append(Block(fmt.KIND_TEXT, index, _rounded(regions["notes"]),
                            text=_notes_text(rng, words)))
        blocks.append(Block(fmt.KIND_STAMP, index, _rounded(regions["stamp"]),
                            fields=(("sheet", str(index + 1)),)))
    stem = f"w55b_rehearsal_scan_{pages}"
    files = make_files(b"", stem, pages=facts, blocks=blocks)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out.with_suffix(".pdf.part")
    pdf_path.write_bytes(pdf)
    pdf_bytes = len(pdf)
    del pdf
    try:
        members = pack(files)
        members[0] = zipwrite.Member(name=members[0].name, payload=zipwrite.FromFile(pdf_path),
                                     method=zipwrite.STORED, flags=members[0].flags)
        zipwrite.write_zip(out, members)
    finally:
        pdf_path.unlink(missing_ok=True)
    verdict = validate(out, GENERATOR_LIMITS)                 # the reference validator
    if not verdict.accepted:
        raise SystemExit(f"the reference validator refuses the low-text bundle: {verdict.constraints}")
    jpeg = sorted(item["jpeg_bytes"] for item in layout)
    return {"variant": "low-text", "stem": stem, "pdf_bytes": pdf_bytes,
            "blocks_json_bytes": len(files.blocks_json), "results_md_bytes": len(files.results_md),
            "blocks_by_kind": _kinds(files.blocks),
            "jpeg_bytes_per_page": {"min": jpeg[0], "median": jpeg[len(jpeg) // 2], "max": jpeg[-1]},
            "landscape_pages": sum(1 for n in range(1, pages + 1) if n % 5 == 0),
            "pages_without_text_layer": sum(1 for f in facts if not f.text),
            "raster_seconds": round(raster_seconds, 1)}


# ------------------------------------------------------------------ the product's verdict


def _kinds(blocks) -> dict[str, int]:
    out: dict[str, int] = {}
    for block in blocks:
        out[block.kind] = out.get(block.kind, 0) + 1
    return out


def product_admission(path: Path) -> dict:
    """The product's own reader and envelope over the archive, and the input budget."""
    from auditmanager.analysis.public import input_budget_characters
    from auditmanager.ingest.bundle_archive import extract_bundle
    from auditmanager.ingest.bundle_envelope import admit_bundle

    model = os.environ.get("AUDITMANAGER_MODEL_ID", "").strip() or "claude-opus-5"
    ceiling = float(os.environ.get("AUDITMANAGER_RUN_COST_CEILING_USD", "").strip() or "1.00")
    started = time.monotonic()
    with path.open("rb") as handle:
        bundle = extract_bundle(handle)
        try:
            admission = admit_bundle(bundle)
        finally:
            bundle.close()
    budget = input_budget_characters(model, ceiling)
    return {
        "accepted_by_product": True,
        "product_seconds": round(time.monotonic() - started, 2),
        "page_count": admission.page_count,
        "pdf_member_bytes": admission.pdf_size,
        "text_character_count": admission.text_character_count,
        "textless_page_count": len(admission.textless_pages),
        "recognised_character_count": admission.recognised_character_count,
        "block_count": admission.block_count,
        "budget_model": model, "budget_ceiling_usd": ceiling, "budget_characters": budget,
        "over_budget": admission.text_character_count > budget,
    }


def describe(path: Path, built: dict, seed: int) -> dict:
    data_sha = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            data_sha.update(chunk)
    size = path.stat().st_size
    summary = {"seed": seed, "archive_bytes": size, "archive_mib": round(size / common.MiB, 2),
               "archive_sha256": data_sha.hexdigest(), **built}
    summary.update(product_admission(path))
    limits = {"pdf_member_le_250_mib": summary["pdf_bytes"] <= 250 * common.MiB,
              "archive_le_300_mib": size <= 300 * common.MiB}
    summary["limits"] = limits
    if not all(limits.values()):
        raise SystemExit(f"{path.name}: outside the ingest limits {limits}")
    return summary


def build(variant: str, pages: int, seed: int, out: Path | None) -> dict:
    common.ensure_out()
    target = (out or (common.OUT / "bundles" / f"{variant}-{pages}.zip")).resolve()
    started = time.monotonic()
    built = (text_rich if variant == "text-rich" else low_text)(pages, seed, target)
    seconds = round(time.monotonic() - started, 1)
    summary = describe(target, built, seed)
    summary["path"] = str(target.relative_to(common.ROOT))
    summary["build_seconds"] = seconds
    return summary


def check() -> int:
    """Each variant twice at a few pages: same bytes, accepted by both validators."""
    failures = 0
    scratch = common.ensure_out() / "bundles" / "check"
    for variant, pages, expect_over in (("text-rich", 60, True), ("low-text", 4, False)):
        digests = []
        for attempt in (1, 2):
            summary = build(variant, pages, 55, scratch / f"{variant}-{attempt}.zip")
            digests.append(summary["archive_sha256"])
            print(json.dumps({k: summary[k] for k in ("variant", "archive_bytes", "text_character_count",
                                                     "budget_characters", "over_budget", "block_count")}))
        other = build(variant, pages, 56, scratch / f"{variant}-other-seed.zip")
        same = digests[0] == digests[1]
        differs = other["archive_sha256"] != digests[0]
        print(f"{variant}: same seed same bytes: {same}; another seed other bytes: {differs}")
        failures += (not same) + (not differs)
        if summary["over_budget"] != expect_over:
            print(f"{variant}: over_budget is {summary['over_budget']}, expected {expect_over}")
            failures += 1
    for leftover in scratch.glob("*.zip"):
        leftover.unlink()
    scratch.rmdir()
    print("check: OK" if failures == 0 else f"check: {failures} failure(s)")
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("variant", choices=("text-rich", "low-text", "check"))
    parser.add_argument("--pages", type=int, default=500)
    parser.add_argument("--seed", type=int, default=55)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.variant == "check":
        return check()
    if not 1 <= args.pages <= fmt.MAX_PAGES:
        raise SystemExit(f"--pages must be 1..{fmt.MAX_PAGES}")
    common.capacity_gate(f"build {args.variant}")
    summary = build(args.variant, args.pages, args.seed, args.out)
    common.write_figures(f"bundle-{args.variant}-{args.pages}-seed{args.seed}", {"bundle": summary})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
