"""Valid bundles that look unusual, built at test time.

A reader that only ever met the archives one tool writes would fail on the first bundle
another tool wrote. Each builder here is a good bundle in a way a stricter-than-the-rules
reader could get wrong: ZIP64 sizes, sizes after the data, a name in each of the four
encodings the display rule covers, every optional member, a polygon block, real deflate.
Every one is built through `build_bundle`, so the validator has accepted it before the
caller sees it.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable

from . import archive_negatives as base
from . import blocklist
from . import portal_format as fmt
from .blocklist import Block
from .bundle import NAME_ENCODINGS, STAMP_CONTEXT, PortalFiles, build_bundle, make_files
from .committed import PLAN_IMAGE, SCHEME_IMAGE, SCHEME_POLYGON

CYRILLIC_STEM = "Проект_АР"


def _options_bundle(files: PortalFiles, **options) -> bytes:
    return build_bundle(files, **options).data


def _full_files(stem: str = base.STEM) -> PortalFiles:
    extra = [
        Block(fmt.KIND_IMAGE, 0, (0.12, 0.62, 0.88, 0.80), image=PLAN_IMAGE),
        Block(fmt.KIND_STAMP, 1, (0.50, 0.86, 0.905, 0.945),
              fields=(("code", STAMP_CONTEXT.code), ("stage", STAMP_CONTEXT.stage))),
    ]
    return make_files(base.base_files(stem).pdf, stem, extra_blocks=extra,
                      stamp=STAMP_CONTEXT, html=True, stamp_audit=True)


def minimal() -> bytes:
    """Exactly the three required members."""
    return _options_bundle(base.base_files())


def every_optional_member() -> bytes:
    """Five members: the three, the HTML, and a stamp audit with a stamp in it."""
    return _options_bundle(_full_files())


def polygon_image_block() -> bytes:
    pdf = base.base_files().pdf
    extra = [Block(fmt.KIND_IMAGE, 1, (0, 0, 0, 0), polygon=SCHEME_POLYGON, image=SCHEME_IMAGE)]
    return _options_bundle(make_files(pdf, base.STEM, extra_blocks=extra))


def _rectangles_edited(edit: Callable[[dict], None]) -> bytes:
    """The base bundle with `edit` applied to each rectangle block of its block list."""
    files = base.base_files()
    document = json.loads(files.blocks_json)
    rectangles = [b for b in document["blocks"] if b["shape_type"] == "rectangle"]
    assert rectangles, "the base bundle holds no rectangle block"
    for block in rectangles:
        edit(block)
    return _options_bundle(dataclasses.replace(files, blocks_json=blocklist.dump(document)))


def rectangle_with_empty_polygon_points() -> bytes:
    """Amendment 1: the vertices are "empty on rectangles"; this export writes `[]`."""
    return _rectangles_edited(lambda block: block.update(polygon_points=[]))


def rectangle_with_null_polygon_points() -> bytes:
    """The owner's real export writes `null` on every rectangle."""
    return _rectangles_edited(lambda block: block.update(polygon_points=None))


def block_without_shape_type() -> bytes:
    """`shape_type` is optional: a block without it (and without vertices) is accepted."""
    return _rectangles_edited(lambda block: block.pop("shape_type"))


def zip64_sizes() -> bytes:
    """ZIP64 extra fields on every entry, and a ZIP64 end record, with small sizes."""
    return _options_bundle(_full_files(), zip64=True, zip64_end=True)


def zip64_end_record_only() -> bytes:
    return _options_bundle(base.base_files(), zip64_end=True)


def data_descriptors() -> bytes:
    """General-purpose flag bit 3: the CRC and sizes follow each member's data."""
    return _options_bundle(_full_files(), descriptors=True)


def data_descriptors_with_zip64() -> bytes:
    """Bit 3 and ZIP64 together: a descriptor with 8-byte sizes."""
    return _options_bundle(_full_files(), descriptors=True, zip64=True)


def name_encoding(encoding: str) -> bytes:
    """A Cyrillic member name in one of the four encodings the display rule decodes."""
    if encoding not in NAME_ENCODINGS:
        raise ValueError(f"unknown name encoding {encoding!r}")
    files = make_files(base.base_files().pdf, CYRILLIC_STEM)
    return _options_bundle(files, encoding=encoding)


def real_deflate() -> bytes:
    """Members compressed by zlib (dynamic Huffman blocks), not hand-framed stored blocks."""
    return _options_bundle(_full_files(), deflate="zlib")


def everything_stored() -> bytes:
    return _options_bundle(_full_files(), stored=True)


POSITIVES: dict[str, Callable[[], bytes]] = {
    "minimal": minimal,
    "every_optional_member": every_optional_member,
    "polygon_image_block": polygon_image_block,
    "rectangle_with_empty_polygon_points": rectangle_with_empty_polygon_points,
    "rectangle_with_null_polygon_points": rectangle_with_null_polygon_points,
    "block_without_shape_type": block_without_shape_type,
    "zip64_sizes": zip64_sizes,
    "zip64_end_record_only": zip64_end_record_only,
    "data_descriptors": data_descriptors,
    "data_descriptors_with_zip64": data_descriptors_with_zip64,
    "real_deflate": real_deflate,
    "everything_stored": everything_stored,
    **{f"names_{encoding}": (lambda e=encoding: name_encoding(e)) for encoding in NAME_ENCODINGS},
}
