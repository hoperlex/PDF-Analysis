"""Resolve a proposed TEXT quote only inside its saved W56b window.

This is a pure evidence boundary. It does not decide how observations from
different windows are merged, or whether a model request may be sent.
"""

from __future__ import annotations

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor, resolve_anchor
from auditmanager.analysis.text.chunk_preflight import TextChunk, _checked_pages
from auditmanager.analysis.text.textlayer import TextLayer


class WindowAnchorError(ValueError):
    """The plan or proposed quote cannot be attributed to the selected window."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def resolve_window_anchor(
    layer: TextLayer,
    windows: tuple[TextChunk, ...],
    *,
    window_index: int,
    page_number: int,
    quote: str,
) -> ResolvedAnchor | UnresolvedAnchor:
    """Return a document-global anchor for a quote on the selected window's page.

    Recheck the complete plan before using any one window. A forged window,
    omitted page, duplicate page or changed text is never publication evidence.
    The existing page/quote resolver retains its exact-match and normalization
    rules; this function adds only the window boundary.
    """
    pages = _checked_pages(layer)
    if not isinstance(windows, tuple) or not windows:
        raise WindowAnchorError("invalid_window_plan")
    if type(window_index) is not int or not 0 <= window_index < len(windows):
        raise WindowAnchorError("invalid_window_index")
    if type(page_number) is not int or not isinstance(quote, str) or not quote:
        raise WindowAnchorError("invalid_quote_claim")

    next_page = 0
    for index, window in enumerate(windows):
        if (
            not isinstance(window, TextChunk)
            or window.version_uid != layer.version_uid
            or window.normalization_id != layer.normalization_id
            or type(window.index) is not int
            or window.index != index
            or type(window.first_page) is not int
            or type(window.last_page) is not int
            or window.first_page != next_page + 1
            or window.last_page < window.first_page
            or window.last_page > len(pages)
        ):
            raise WindowAnchorError("invalid_window_plan")
        first = pages[next_page]
        last = pages[window.last_page - 1]
        if (
            type(window.char_start) is not int
            or type(window.char_end) is not int
            or not isinstance(window.text, str)
            or window.char_start != first.char_start
            or window.char_end != last.char_end
            or window.text != layer.slice(first.char_start, last.char_end)
        ):
            raise WindowAnchorError("invalid_window_plan")
        next_page = window.last_page
    if next_page != len(pages):
        raise WindowAnchorError("invalid_window_plan")

    selected = windows[window_index]
    if not selected.first_page <= page_number <= selected.last_page:
        raise WindowAnchorError("page_outside_window")
    return resolve_anchor(layer, page_number=page_number, quote=quote)
