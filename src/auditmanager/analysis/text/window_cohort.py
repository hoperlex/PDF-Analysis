"""Bind a complete supplied W56b TEXT reply cohort to saved page windows.

This pure seam checks coverage and quote locations. It has no knowledge of a
provider response, Attempt, effect journal or finding publication. A caller
must establish those facts separately before treating a reply as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor, resolve_anchor
from auditmanager.analysis.text.chunk_preflight import TextChunk
from auditmanager.analysis.text.textlayer import TextLayer
from auditmanager.analysis.text.window_anchor import WindowAnchorError, validate_window_plan


@dataclass(frozen=True, slots=True)
class WindowQuoteClaim:
    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class WindowReplyClaims:
    window_index: int
    claims: tuple[WindowQuoteClaim, ...]


@dataclass(frozen=True, slots=True)
class BoundWindowClaims:
    window_index: int
    anchors: tuple[ResolvedAnchor | UnresolvedAnchor, ...]


def bind_window_claim_cohort(
    layer: TextLayer,
    windows: tuple[TextChunk, ...],
    replies: tuple[WindowReplyClaims, ...],
) -> tuple[BoundWindowClaims, ...]:
    """Require one ordered reply per window and resolve its claimed quotes.

    An empty claim list is valid: the corresponding reply can report no
    findings. An absent reply is not silently treated as an empty one.
    An absent quote retains the existing unresolved reason; a claim on a page
    outside its own window refuses the entire cohort.
    """
    validate_window_plan(layer, windows)
    if not isinstance(replies, tuple) or len(replies) != len(windows):
        raise WindowAnchorError("incomplete_window_reply_cohort")

    bound: list[BoundWindowClaims] = []
    for index, reply in enumerate(replies):
        if (
            not isinstance(reply, WindowReplyClaims)
            or type(reply.window_index) is not int
            or reply.window_index != index
            or not isinstance(reply.claims, tuple)
        ):
            raise WindowAnchorError("invalid_window_reply_cohort")
        window = windows[index]
        anchors: list[ResolvedAnchor | UnresolvedAnchor] = []
        for claim in reply.claims:
            if (
                not isinstance(claim, WindowQuoteClaim)
                or type(claim.page_number) is not int
                or not isinstance(claim.quote, str)
                or not claim.quote
            ):
                raise WindowAnchorError("invalid_quote_claim")
            if not window.first_page <= claim.page_number <= window.last_page:
                raise WindowAnchorError("page_outside_window")
            anchors.append(resolve_anchor(
                layer, page_number=claim.page_number, quote=claim.quote
            ))
        bound.append(BoundWindowClaims(index, tuple(anchors)))
    return tuple(bound)
