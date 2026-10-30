"""Read immutable visual-input facts for a fresh section-workflow cost estimate."""
from __future__ import annotations

import hashlib

from auditmanager.analysis.recognised.portal import IMAGE, read_block_list
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id

MAX_VISUAL_SOURCES = 1000
MAX_TEXT_PAGES = 500
VISUAL_WINDOW_SIZE = 16


def estimate_visual_scope(*, version, blob_store=None):
    """Count actual portal IMAGE inputs; a native/TEXT-only PDF uses page visuals.

    This is input accounting, not a claim that every page or portal box will pass
    geometry admission. The worker reports those later refusals explicitly.
    """
    pages = version.page_count
    if type(pages) is not int or not 1 <= pages <= MAX_TEXT_PAGES:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="source_preparation",
                          reason="cost_page_count_unavailable")
    companion = next((entry for entry in version.manifest
                      if str(entry.role) == "source.structured_companion"), None)
    kind, count, companion_sha = "native_pages", pages, None
    if companion is not None:
        if blob_store is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_visual_cost_source")
        raw = blob_store.read(parse_blob_id(str(companion.blob_id)), verify=True)
        if (len(raw) != companion.size_bytes or hashlib.sha256(raw).hexdigest() != companion.sha256):
            raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="source.structured_companion")
        blocks = read_block_list(raw, page_count=pages, stage_id="source_preparation")
        images = sum(block.block_type == IMAGE for block in blocks)
        kind, count = ("portal_image_blocks", images) if images else ("portal_page_visuals", pages)
        companion_sha = companion.sha256
    if count > MAX_VISUAL_SOURCES:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="source_preparation",
                          reason="cost_visual_source_limit_exceeded")
    maximum = count
    return {"source_kind": kind, "total_sources": count, "max_blocks": maximum,
            "window_size": VISUAL_WINDOW_SIZE,
            "max_windows": max((maximum + VISUAL_WINDOW_SIZE - 1) // VISUAL_WINDOW_SIZE,
                               (pages + VISUAL_WINDOW_SIZE - 1) // VISUAL_WINDOW_SIZE),
            "text_page_limit": pages,
            "uncovered_sources": max(0, count - maximum),
            "page_count": pages, "companion_sha256": companion_sha}
