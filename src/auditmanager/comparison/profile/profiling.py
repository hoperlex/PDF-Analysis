"""Profile one page: run its two children, read what they wrote, assemble the row, the archive and the
two PNGs. Nothing here touches the database or the object store.

`CMP-PROFILE-01`. :func:`profile_page` is the unit of work. For one 0-based page of one PDF file it

1. runs the **render child** (768 MiB): the registration dpi, the preview and thumbnail PNGs, the
   36 dpi ink mask, the tile pyramid; a page over the pixel cap is **refused** there, before any
   bitmap exists, and no other child is started for it;
2. runs the **extraction child** (1024 MiB): words with boxes, vector lines, image boxes, annotations
   and the content Merkle;
3. reads the stamp zone, decides the scan flag, and builds the content key, the small summary kept in
   the row's ``profile`` column and the archive kept in ``profile_blob_id``.

**An end without a result is a typed page, not an exception.** A child that overruns its address
space, hits its CPU or wall ceiling, is killed by a signal or raises leaves the page ``needs_review``
with reason ``RENDER_FAILED`` (ADR-0025 addendum item 1); the failure names the stage and the class of
end and nothing of the page. If the render succeeded and only the extraction failed, the page keeps
its preview, thumbnail, mask and tiles (a viewer can still show it) and no words. A page is never
«same» because it could not be read: the status says so and the engine reads the status.

**The content key.** ``sha256`` of ``{algo, page, content Merkle, annotation hashes}`` for a profiled
page, so two identical pages of one version (a duplicated sheet) get different keys
(``UNIQUE (version, content_key)``) while the Merkle itself, kept in the summary, is the same: the
engine keys its sheet-pair cache on the Merkle (ADR-0025 decision 15). A page that was refused or
failed has a key over its page number and the version's digest, so it is unique and says nothing about
content it never read.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from auditmanager.comparison.profile import limits, pack
from auditmanager.comparison.profile.models import SUMMARY_SCHEMA
from auditmanager.comparison.profile.runner import ChildResult, ChildRunner
from auditmanager.comparison.profile.stamp import read_stamp

__all__ = [
    "PACK_SCHEMA",
    "PageOutcome",
    "SCAN_IMAGE_COVERAGE",
    "SCAN_MAX_VECTOR_OBJECTS",
    "content_key",
    "is_scan",
    "profile_page",
]

PACK_SCHEMA: Final[str] = "cmp-page-profile-pack/1"
#: A page is a **scan** when images cover at least this share of it and it draws almost no vector
#: content: a raster of a paper sheet, with or without an OCR text layer. A plan on a raster background
#: has vector content on top of the image and is not a scan.
SCAN_IMAGE_COVERAGE: Final[float] = 0.6
SCAN_MAX_VECTOR_OBJECTS: Final[int] = 20


@dataclass(frozen=True, slots=True)
class PageOutcome:
    """What one page produced, ready to be stored (blobs first, then the row)."""

    page_number: int
    status: str
    reason: str | None
    summary: dict[str, Any]
    content_key: str
    pack: bytes | None = None
    preview: bytes | None = None
    thumbnail: bytes | None = None
    timings: dict[str, Any] = field(default_factory=dict)


def content_key(
    *, page_number: int, merkle: str | None, annotation_hashes: list[str], version_sha256: str,
    status: str,
) -> str:
    """The unique, content-derived key of a profile (see the module docstring)."""
    if merkle is not None and status == limits.STATUS_READY:
        body: dict[str, Any] = {
            "kind": SUMMARY_SCHEMA,
            "algo": limits.ALGO_VERSION,
            "page": page_number,
            "merkle": merkle,
            "annotations": annotation_hashes,
        }
    else:
        body = {
            "kind": SUMMARY_SCHEMA,
            "algo": limits.ALGO_VERSION,
            "page": page_number,
            "unprofiled": status,
            "version": version_sha256,
        }
    return hashlib.sha256(pack.canonical_json(body)).hexdigest()


def is_scan(*, image_coverage: float, vector_objects: int) -> bool:
    return image_coverage >= SCAN_IMAGE_COVERAGE and vector_objects <= SCAN_MAX_VECTOR_OBJECTS


def _end_of(result: ChildResult) -> str:
    end = result.end
    return "memory" if end == "overrun" else end


def _failed(
    page_number: int, version_sha256: str, stage: str, result: ChildResult, timings: dict[str, Any]
) -> PageOutcome:
    return PageOutcome(
        page_number=page_number,
        status=limits.STATUS_NEEDS_REVIEW,
        reason=limits.REASON_RENDER_FAILED,
        summary={"schema": SUMMARY_SCHEMA, "failure": {"stage": stage, "end": _end_of(result)}},
        content_key=content_key(
            page_number=page_number, merkle=None, annotation_hashes=[], version_sha256=version_sha256,
            status=limits.STATUS_NEEDS_REVIEW,
        ),
        timings=timings,
    )


def _timings(render: ChildResult | None, extract: ChildResult | None) -> dict[str, Any]:
    timings: dict[str, Any] = {}
    for name, result in (("render", render), ("extract", extract)):
        if result is not None:
            timings[name] = {
                "status": result.status,
                "wall_s": result.wall_s,
                "cpu_s": result.cpu_s,
                "max_rss_kib": result.max_rss_kib,
                "vm_peak_kib": result.facts.get("vm_peak_kib"),
            }
    return timings


def _read_tiles(out_dir: Path) -> list[tuple[int, int, int, bytes]]:
    tiles: list[tuple[int, int, int, bytes]] = []
    root = out_dir / "tiles"
    if not root.is_dir():
        return tiles
    for level_dir in sorted(root.iterdir()):
        for tile in sorted(level_dir.iterdir()):
            column, _, row = tile.stem.partition("_")
            tiles.append((int(level_dir.name), int(column), int(row), tile.read_bytes()))
    return tiles


def profile_page(
    runner: ChildRunner,
    *,
    pdf_path: str,
    page_index: int,
    version_sha256: str,
    work_dir: str | None = None,
    render_limits: limits.ChildLimits = limits.RENDER_LIMITS,
    extract_limits: limits.ChildLimits = limits.EXTRACT_LIMITS,
    render_overrides: Mapping[str, int] | None = None,
) -> PageOutcome:
    """Profile 0-based page ``page_index`` of the PDF at ``pdf_path``; the rows' page number is 1-based."""
    page_number = page_index + 1
    with tempfile.TemporaryDirectory(prefix="cmp-profile-", dir=work_dir) as scratch:
        out_dir = Path(scratch)
        render = runner.run(
            {
                "mode": "render",
                "pdf": pdf_path,
                "page": page_index,
                "out_dir": str(out_dir),
                **limits.render_settings(**dict(render_overrides or {})),
            },
            render_limits,
        )
        if render.status == "refused":
            facts = dict(render.facts)
            return PageOutcome(
                page_number=page_number,
                status=limits.STATUS_REFUSED,
                reason=limits.REASON_PAGE_TOO_LARGE,
                summary={
                    "schema": SUMMARY_SCHEMA,
                    "width_pt": facts.get("width_pt"),
                    "height_pt": facts.get("height_pt"),
                    "refusal": {
                        "pixel_cap": limits.PIXEL_CAP,
                        "min_dpi": limits.MIN_REGISTRATION_DPI,
                    },
                },
                content_key=content_key(
                    page_number=page_number, merkle=None, annotation_hashes=[],
                    version_sha256=version_sha256, status=limits.STATUS_REFUSED,
                ),
                timings=_timings(render, None),
            )
        if not render.ok:
            return _failed(page_number, version_sha256, "render", render, _timings(render, None))

        extract = runner.run(
            {"mode": "extract", "pdf": pdf_path, "page": page_index, "out_dir": str(out_dir)},
            extract_limits,
        )
        preview = (out_dir / "preview.png").read_bytes()
        thumbnail = (out_dir / "thumbnail.png").read_bytes()
        mask = (out_dir / "mask.bin").read_bytes()
        tiles = _read_tiles(out_dir)
        body: dict[str, Any] | None = None
        if extract.ok:
            body = json.loads((out_dir / "extract.json").read_text(encoding="utf-8"))
        return _assemble(
            page_number, version_sha256, render, extract, body, preview, thumbnail, mask, tiles
        )


def _assemble(
    page_number: int,
    version_sha256: str,
    render: ChildResult,
    extract: ChildResult,
    body: dict[str, Any] | None,
    preview: bytes,
    thumbnail: bytes,
    mask: bytes,
    tiles: list[tuple[int, int, int, bytes]],
) -> PageOutcome:
    facts = render.facts
    summary: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA,
        "width_pt": facts["width_pt"],
        "height_pt": facts["height_pt"],
        "rotation": facts["rotation"],
        "raster": {
            "dpi": facts["dpi"],
            "width_px": facts["raster_width_px"],
            "height_px": facts["raster_height_px"],
        },
        "ink": {
            "mask_dpi": facts["mask"]["dpi"],
            "width_px": facts["mask"]["width_px"],
            "height_px": facts["mask"]["height_px"],
            "ratio": round(
                facts["mask"]["ink_pixels"] / max(1, facts["mask"]["width_px"] * facts["mask"]["height_px"]), 6
            ),
            "below": facts["mask"]["ink_below"],
        },
        "preview": dict(facts["preview"]),
        "thumbnail": dict(facts["thumbnail"]),
        "tiles": {
            "tile_px": facts["tile_px"],
            "levels": facts["levels"],
            "stored_count": facts["tiles_stored"],
            "stored_bytes": facts["tiles_stored_bytes"],
        },
    }
    document: dict[str, Any] = {
        "schema": PACK_SCHEMA,
        "algo_version": limits.ALGO_VERSION,
        "page_number": page_number,
        "width_pt": facts["width_pt"],
        "height_pt": facts["height_pt"],
        "rotation": facts["rotation"],
        "mask": {
            "dpi": facts["mask"]["dpi"],
            "width_px": facts["mask"]["width_px"],
            "height_px": facts["mask"]["height_px"],
            "row_bytes": facts["mask"]["row_bytes"],
            "below": facts["mask"]["ink_below"],
        },
        "raster": summary["raster"],
        "extract": None,
        "coordinates": (
            "points; origin at the top left of the page as displayed (CropBox applied, /Rotate applied); "
            "annotation rectangles are the PDF's own (origin lower left, unrotated)"
        ),
    }
    status, reason, merkle, hashes = limits.STATUS_NEEDS_REVIEW, limits.REASON_RENDER_FAILED, None, []
    if body is not None:
        ef = extract.facts
        width, height = float(body["page"]["width_pt"]), float(body["page"]["height_pt"])
        stamp = read_stamp(body["words"], width, height)
        coverage = min(
            1.0,
            sum(max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1]) for b in body["images"])
            / max(1.0, width * height),
        )
        has_text = int(ef["words"]) > 0
        # The scan test counts what the page draws (lines, rectangles, curves), not the segments the profile keeps of them.
        vector_objects = int(ef["drawn_lines"]) + int(ef["rects"]) + int(ef["curves"])
        scan = is_scan(image_coverage=coverage, vector_objects=vector_objects)
        stamp_fields = {
            key: value
            for key, value in (
                ("designation", stamp.designation),
                ("sheet_number", stamp.sheet_number),
                ("sheet_name", stamp.sheet_title),
                ("revision_number", stamp.revision_number),
                ("release_date", stamp.release_date),
            )
            if value is not None
        }
        merkle, hashes = str(ef["merkle"]), list(ef["annotation_hashes"])
        status, reason = limits.STATUS_READY, None
        agrees = abs(width - float(facts["width_pt"])) <= 0.5 and abs(height - float(facts["height_pt"])) <= 0.5
        if not agrees:
            status, reason = limits.STATUS_NEEDS_REVIEW, limits.REASON_FRAME_MISMATCH
        summary.update(
            {
                "counts": {
                    "words": ef["words"],
                    "lines": ef["lines"],
                    "drawn_lines": ef["drawn_lines"],
                    "rects": ef["rects"],
                    "curves": ef["curves"],
                    "chars": ef["chars"],
                    "images": ef["images"],
                    "annotations": ef["annotations"],
                },
                "text_layer": has_text,
                "scan": scan,
                "image_coverage": round(coverage, 4),
                "stamp": {**stamp_fields, "labels": list(stamp.labels)},
                "stamp_zone": [round(v, 2) for v in stamp.zone],
                "content_merkle": merkle,
                "annotation_hashes": hashes,
                "frame": {"offset": body["page"]["offset"], "agrees": agrees},
            }
        )
        document.update(
            {
                "words": body["words"],
                "lines": body["lines"],
                "images": body["images"],
                "annotations": body["annotations"],
                "stamp": stamp_fields,
                "stamp_zone": summary["stamp_zone"],
                "extract": {
                    "counts": summary["counts"],
                    "page_width_pt": width,
                    "page_height_pt": height,
                    "text_layer": has_text,
                    "scan": scan,
                },
            }
        )
    else:
        summary["failure"] = {"stage": "extract", "end": _end_of(extract)}
    archive = pack.build_pack(document, mask=mask, tiles=tiles)
    summary["pack_bytes"] = len(archive)
    return PageOutcome(
        page_number=page_number,
        status=status,
        reason=reason,
        summary=summary,
        content_key=content_key(
            page_number=page_number, merkle=merkle, annotation_hashes=hashes,
            version_sha256=version_sha256, status=status,
        ),
        pack=archive,
        preview=preview,
        thumbnail=thumbnail,
        timings=_timings(render, extract),
    )
