"""The content Merkle of one PDF page, and the hashes of its annotations (pypdf).

`CMP-PROFILE-01`, ADR-0025 decision 15: a page is identified by "the content Merkle of the page
(its content stream and every referenced resource, XObjects and images included)", and the
annotations are hashed beside it, because an annotation-only change is a difference of its own.
The digest is the page's **content address**: two pages with equal digests draw the same thing
from the same bytes; two pages with different digests may still look the same, which is the safe
direction for a cache key.

What it hashes
--------------
* the page's ``/Contents`` stream(s), decoded, **without** interpreting them (pypdf's
  ``ContentStream`` parses every operator into Python objects, which is minutes and gigabytes on
  a page of 400 000 elements; the decoded bytes are all the digest needs);
* the page's ``/Resources`` tree, key by key in sorted order: dictionaries and arrays by value,
  streams by their dictionary and their decoded bytes (an image stream by its **encoded** bytes
  and its dictionary, so an image is never decoded here), indirect references by the digest of
  what they point at, so object numbers never reach the digest;
* the page boxes and ``/Rotate``, because the same stream on another box is another sheet.

A reference loop hashes as a fixed marker; the walk has a node budget and a depth ceiling and
raises :class:`MerkleBudgetExceeded` past them (the child reports it as a failure of that page,
never as a digest).

This module imports ``pypdf`` inside the functions that need it and nothing from the product, so
the extraction child program (``extract_job``) loads it as a top-level module.
"""

from __future__ import annotations

import hashlib
from typing import Any

__all__ = [
    "MAX_DEPTH",
    "MAX_NODES",
    "MerkleBudgetExceeded",
    "annotation_records",
    "displayed_page",
    "page_digest",
    "page_frame",
]

MAX_NODES = 2_000_000
MAX_DEPTH = 64
_DOMAIN = b"cmp-merkle/1\0"
#: Keys of an annotation that point back up the tree and would make the hash loop.
_ANNOTATION_BACK_REFERENCES = frozenset({"/P", "/Parent", "/Popup", "/IRT"})
_MAX_ANNOTATIONS = 20_000
_MAX_CONTENTS_CHARS = 500


class MerkleBudgetExceeded(Exception):
    """The page's object graph is larger than the walk's node budget or deeper than its ceiling."""


class _Walk:
    __slots__ = ("memo", "path", "nodes", "skip_keys")

    def __init__(self, skip_keys: frozenset[str] = frozenset()) -> None:
        self.memo: dict[tuple[int, int], bytes] = {}
        self.path: set[tuple[int, int]] = set()
        self.nodes = 0
        self.skip_keys = skip_keys

    def tick(self) -> None:
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise MerkleBudgetExceeded("nodes")


def _hash(*parts: bytes) -> bytes:
    digest = hashlib.sha256(_DOMAIN)
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.digest()


def _scalar(tag: bytes, text: str) -> bytes:
    return _hash(tag, text.encode("utf-8", "surrogatepass"))


def _number(value: float) -> str:
    return format(float(value), ".6g")


def _digest(value: Any, walk: _Walk, depth: int) -> bytes:
    from pypdf.generic import (
        ArrayObject,
        BooleanObject,
        ByteStringObject,
        DictionaryObject,
        FloatObject,
        IndirectObject,
        NameObject,
        NullObject,
        NumberObject,
        StreamObject,
        TextStringObject,
    )

    walk.tick()
    if depth > MAX_DEPTH:
        raise MerkleBudgetExceeded("depth")
    if isinstance(value, IndirectObject):
        key = (value.idnum, value.generation)
        if key in walk.memo:
            return walk.memo[key]
        if key in walk.path:
            return _hash(b"cycle")
        walk.path.add(key)
        try:
            target = value.get_object()
            result = _digest(target, walk, depth + 1)
        finally:
            walk.path.discard(key)
        walk.memo[key] = result
        return result
    if isinstance(value, StreamObject):
        return _stream_digest(value, walk, depth)
    if isinstance(value, DictionaryObject):
        return _dictionary_digest(value, walk, depth)
    if isinstance(value, ArrayObject):
        return _hash(b"array", *(_digest(item, walk, depth + 1) for item in value))
    if isinstance(value, NameObject):
        return _scalar(b"name", str(value))
    if isinstance(value, BooleanObject):
        return _scalar(b"bool", "1" if value.value else "0")
    if isinstance(value, NullObject) or value is None:
        return _hash(b"null")
    if isinstance(value, (NumberObject, FloatObject, int, float)):
        return _scalar(b"num", _number(value))
    if isinstance(value, ByteStringObject):
        return _hash(b"bytes", bytes(value))
    if isinstance(value, TextStringObject):
        return _scalar(b"text", str(value))
    return _scalar(b"other", str(value))


def _dictionary_digest(value: Any, walk: _Walk, depth: int, *, skip: frozenset[str] = frozenset()) -> bytes:
    parts: list[bytes] = [b"dict"]
    for key in sorted(value.keys(), key=str):
        if str(key) in skip or str(key) in walk.skip_keys:
            continue
        parts.append(_scalar(b"key", str(key)))
        parts.append(_digest(value.raw_get(key), walk, depth + 1))
    return _hash(*parts)


def _stream_digest(stream: Any, walk: _Walk, depth: int) -> bytes:
    # The dictionary without /Length (the length is a property of the encoding).
    head = _dictionary_digest(stream, walk, depth, skip=frozenset({"/Length"}))
    subtype = str(stream.get("/Subtype", ""))
    if subtype == "/Image":
        data = _encoded_bytes(stream)
    else:
        try:
            data = stream.get_data()
        except Exception:  # noqa: BLE001 - an undecodable stream is hashed as it is stored
            data = _encoded_bytes(stream)
    return _hash(b"stream", head, data)


def _encoded_bytes(stream: Any) -> bytes:
    raw = getattr(stream, "_data", None)
    return bytes(raw) if raw is not None else b""


def _resolve(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _content_streams(page: Any) -> list[Any]:
    from pypdf.generic import ArrayObject, StreamObject

    contents = page.get("/Contents")
    if contents is None:
        return []
    contents = contents.get_object() if hasattr(contents, "get_object") else contents
    if isinstance(contents, StreamObject):
        return [contents]
    if isinstance(contents, ArrayObject):
        resolved = [item.get_object() if hasattr(item, "get_object") else item for item in contents]
        return [item for item in resolved if isinstance(item, StreamObject)]
    return []


def page_frame(page: Any) -> tuple[float, float, int, float, float]:
    """``(width_pt, height_pt, rotation, offset_x, offset_y)`` of the page as a viewer shows it.

    The CropBox clipped to the MediaBox, its sides exchanged for a quarter-turn ``/Rotate``
    (`RUN-ROBUSTNESS-01`, D-159), the reading ``ingest/pdf_reader.py::_displayed`` makes with PDFium.
    ``pdfplumber`` reports the words of a page in the frame of the **rotated MediaBox**, origin at its
    top left; the displayed page starts at ``(offset_x, offset_y)`` inside that frame, which is where a
    renderer puts the raster's first pixel. Subtracting the offset gives displayed coordinates.
    """
    media = [float(value) for value in page.mediabox]
    crop = [float(value) for value in page.cropbox]
    rotation = int(_resolve(page.get("/Rotate", 0)) or 0)
    if rotation % 90 != 0:
        raise ValueError("a page rotation is a multiple of 90 degrees")
    rotation %= 360
    mx0, my0 = min(media[0], media[2]), min(media[1], media[3])
    mx1, my1 = max(media[0], media[2]), max(media[1], media[3])
    left = max(min(crop[0], crop[2]), mx0)
    bottom = max(min(crop[1], crop[3]), my0)
    right = max(left, min(max(crop[0], crop[2]), mx1))
    top = max(bottom, min(max(crop[1], crop[3]), my1))
    width, height = right - left, top - bottom
    # Where the displayed page's top-left corner is in the top-left frame of the rotated MediaBox.
    if rotation == 0:
        offset = (left - mx0, my1 - top)
    elif rotation == 90:
        offset = (bottom - my0, left - mx0)
    elif rotation == 180:
        offset = (mx1 - right, bottom - my0)
    else:
        offset = (my1 - top, mx1 - right)
    if rotation in (90, 270):
        width, height = height, width
    return width, height, rotation, offset[0], offset[1]


def displayed_page(page: Any) -> tuple[float, float, int]:
    """``(width_pt, height_pt, rotation)`` as a viewer shows the page (see :func:`page_frame`)."""
    return page_frame(page)[:3]


def page_digest(page: Any) -> str:
    """The content Merkle of a pypdf page, as 64 lowercase hexadecimal digits."""
    walk = _Walk()
    content = hashlib.sha256()
    for stream in _content_streams(page):
        data = stream.get_data()
        content.update(len(data).to_bytes(8, "big"))
        content.update(data)
        del data
    resources = page.get("/Resources")
    resources_digest = _digest(resources, walk, 0) if resources is not None else _hash(b"none")
    width, height, rotation = displayed_page(page)
    box = _scalar(b"box", f"{_number(width)} {_number(height)} {rotation}")
    return _hash(b"page", content.digest(), resources_digest, box).hex()


def annotation_records(page: Any) -> list[dict[str, Any]]:
    """One record per annotation of the page: subtype, rectangle, contents, and the digest of the
    whole annotation dictionary (appearance streams included, back references to the page left out).
    """
    annotations = page.get("/Annots")
    if annotations is None:
        return []
    annotations = annotations.get_object() if hasattr(annotations, "get_object") else annotations
    records: list[dict[str, Any]] = []
    for index, entry in enumerate(annotations):
        if index >= _MAX_ANNOTATIONS:
            raise MerkleBudgetExceeded("annotations")
        annotation = entry.get_object() if hasattr(entry, "get_object") else entry
        if annotation is None or not hasattr(annotation, "get"):
            records.append({"subtype": None, "rect": None, "contents": None, "sha256": _hash(b"unreadable").hex()})
            continue
        walk = _Walk(skip_keys=_ANNOTATION_BACK_REFERENCES)
        rect = annotation.get("/Rect")
        try:
            rect_list = [round(float(value), 2) for value in rect] if rect is not None else None
        except (TypeError, ValueError):
            rect_list = None
        contents = annotation.get("/Contents")
        text = str(contents)[:_MAX_CONTENTS_CHARS] if contents is not None else None
        subtype = annotation.get("/Subtype")
        records.append(
            {
                "subtype": str(subtype) if subtype is not None else None,
                "rect": rect_list,
                "contents": text,
                "sha256": _digest(annotation, walk, 0).hex(),
            }
        )
    return records
