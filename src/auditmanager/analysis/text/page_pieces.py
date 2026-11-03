"""Fresh native-page pieces with complete source coverage and piece-local quotes.

The saved text and physical pages remain immutable. A piece cannot cite another
part of the same page, and partial-page omission proposals have no authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .anchors import REASON_ABSENT, ResolvedAnchor, UnresolvedAnchor
from .chunk_preflight import ChunkPreflightError, TextChunk, _checked_pages
from .window_anchor import WindowAnchorError
from .window_cohort import BoundWindowClaims, WindowQuoteClaim, WindowReplyClaims

VERSION = "native-page-pieces-v1"
FRAME_RESERVE = 1024
PAGE_FRAME = 512


def policy():
    root = Path(__file__).parent
    files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("page_pieces.py", "windows.py", "windowed.py")}
    bundle = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"version": VERSION, "bundle_sha256": bundle, "frame_characters": FRAME_RESERVE,
        "page_frame_characters": PAGE_FRAME,
        "source": "native_text", "partial_page_omissions": "not_evidenced"}


def validate_policy(value, *, compare_bundle=True):
    if value is None:
        return False
    expected = policy()
    if not compare_bundle and isinstance(value, dict):
        expected["bundle_sha256"] = value.get("bundle_sha256")
    if (not isinstance(value, dict) or set(value) != set(expected) or value != expected
            or type(value.get("frame_characters")) is not int
            or type(value.get("page_frame_characters")) is not int
            or not isinstance(value.get("bundle_sha256"), str) or len(value["bundle_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in value["bundle_sha256"])):
        raise ValueError("native_page_pieces_changed_requires_consent")
    return True


def partition(layer, *, max_chunk_characters, page_extra):
    pages = _checked_pages(layer)
    if type(max_chunk_characters) is not int or max_chunk_characters <= PAGE_FRAME:
        raise ChunkPreflightError("invalid_max_chunk_characters")
    if not layer.document_text.strip():
        raise ChunkPreflightError("empty_text_layer")
    if any(type(value) is not int or value < 0 for value in page_extra.values()):
        raise ChunkPreflightError("invalid_page_extra")
    for page in pages:
        if page_extra.get(page.page_number, 0) and len(page.text) + page_extra[page.page_number] + PAGE_FRAME > max_chunk_characters:
            raise ChunkPreflightError("page_exceeds_limit", page_number=page.page_number)
    chunks = []
    first = last = None
    start = end = used = 0

    def begin(page, position):
        nonlocal first, start
        if first is None:
            first, start = page.page_number, position

    def flush():
        nonlocal first, last, used
        if first is None:
            return
        chunks.append(TextChunk(layer.version_uid, layer.normalization_id, len(chunks),
            first, last, start, end, layer.slice(start, end)))
        first = last = None
        used = 0

    for page in pages:
        extra = page_extra.get(page.page_number, 0)
        if extra:
            weight = len(page.text) + extra + PAGE_FRAME
            if first is not None and used + weight > max_chunk_characters:
                flush()
            begin(page, page.char_start)
            last, end, used = page.page_number, page.char_end, used + weight
        elif not page.text:
            if first is not None and used + PAGE_FRAME > max_chunk_characters:
                flush()
            begin(page, page.char_start)
            last, end, used = page.page_number, page.char_end, used + PAGE_FRAME
        else:
            cursor = page.char_start
            while cursor < page.char_end:
                if last != page.page_number:
                    if first is not None and used + PAGE_FRAME >= max_chunk_characters:
                        flush()
                    begin(page, cursor)
                    used += PAGE_FRAME
                    last, end = page.page_number, cursor
                if used == max_chunk_characters:
                    flush()
                    continue
                begin(page, cursor)
                taken = min(page.char_end - cursor, max_chunk_characters - used)
                cursor += taken
                last, end, used = page.page_number, cursor, used + taken
    flush()
    return tuple(chunks)


def validate_plan(layer, windows):
    pages = _checked_pages(layer)
    if not isinstance(windows, tuple) or not windows:
        raise WindowAnchorError("invalid_native_piece_plan")
    next_page, next_offset = 1, 0
    for index, window in enumerate(windows):
        if (not isinstance(window, TextChunk) or window.version_uid != layer.version_uid
                or window.normalization_id != layer.normalization_id or type(window.index) is not int
                or window.index != index or type(window.first_page) is not int or type(window.last_page) is not int
                or window.first_page != next_page or not 1 <= window.first_page <= window.last_page <= len(pages)
                or type(window.char_start) is not int or type(window.char_end) is not int
                or window.char_start != next_offset or window.char_end < window.char_start
                or not isinstance(window.text, str)):
            raise WindowAnchorError("invalid_native_piece_plan")
        first, last = pages[window.first_page - 1], pages[window.last_page - 1]
        if (not first.char_start <= window.char_start <= first.char_end
                or not last.char_start <= window.char_end <= last.char_end
                or window.text != layer.slice(window.char_start, window.char_end)
                or (not window.text and any(page.text for page in pages[window.first_page - 1:window.last_page]))):
            raise WindowAnchorError("invalid_native_piece_plan")
        next_offset = window.char_end
        next_page = window.last_page + 1 if window.char_end == last.char_end else window.last_page
    if next_page != len(pages) + 1 or next_offset != len(layer.document_text):
        raise WindowAnchorError("incomplete_native_piece_plan")


def partial_window(layer, window):
    return (window.char_start != layer.pages[window.first_page - 1].char_start
        or window.char_end != layer.pages[window.last_page - 1].char_end)


def bind_claims(layer, windows, replies):
    validate_plan(layer, windows)
    if not isinstance(replies, tuple) or len(replies) != len(windows):
        raise WindowAnchorError("incomplete_window_reply_cohort")
    bound = []
    for index, reply in enumerate(replies):
        if (not isinstance(reply, WindowReplyClaims) or type(reply.window_index) is not int
                or reply.window_index != index or not isinstance(reply.claims, tuple)):
            raise WindowAnchorError("invalid_window_reply_cohort")
        window = windows[index]
        anchors = []
        for claim in reply.claims:
            if (not isinstance(claim, WindowQuoteClaim) or type(claim.page_number) is not int
                    or not isinstance(claim.quote, str) or not claim.quote):
                raise WindowAnchorError("invalid_quote_claim")
            if not window.first_page <= claim.page_number <= window.last_page:
                raise WindowAnchorError("page_outside_window")
            page = layer.pages[claim.page_number - 1]
            start, end = max(page.char_start, window.char_start), min(page.char_end, window.char_end)
            actual = layer.slice(start, end)
            anchor = UnresolvedAnchor(claim.page_number, claim.quote, REASON_ABSENT)
            for candidate in (claim.quote, claim.quote.strip()):
                if not candidate:
                    continue
                offset = actual.find(candidate)
                if offset >= 0:
                    anchor = ResolvedAnchor(claim.page_number, candidate, start + offset, start + offset + len(candidate))
                    break
            anchors.append(anchor)
        bound.append(BoundWindowClaims(index, tuple(anchors)))
    return tuple(bound)
