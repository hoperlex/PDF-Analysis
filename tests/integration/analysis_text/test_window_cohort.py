"""A complete W56b window claim cohort keeps page and global offsets honest."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.chunk_preflight import partition_text_layer
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.analysis.text.window_anchor import WindowAnchorError
from auditmanager.analysis.text.window_cohort import (
    WindowQuoteClaim,
    WindowReplyClaims,
    bind_window_claim_cohort,
)


def _source() -> tuple[TextLayer, tuple]:
    bodies = ("А😀 дом", "", "БВ фасад", "крыша")
    pages = []
    position = 0
    for number, body in enumerate(bodies, start=1):
        pages.append(Page(number, position, position + len(body), body))
        position += len(body)
    layer = TextLayer("ver_01", "NFC", tuple(pages), "".join(bodies))
    return layer, partition_text_layer(layer, max_chunk_characters=9)


def _replies() -> tuple[WindowReplyClaims, ...]:
    return (
        WindowReplyClaims(0, (WindowQuoteClaim(1, "А😀"),)),
        WindowReplyClaims(1, (WindowQuoteClaim(3, "фасад"),)),
        WindowReplyClaims(2, ()),
    )


def test_complete_cohort_preserves_global_unicode_offsets_and_empty_reply() -> None:
    layer, windows = _source()

    bound = bind_window_claim_cohort(layer, windows, _replies())

    assert tuple(item.window_index for item in bound) == (0, 1, 2)
    assert isinstance(bound[0].anchors[0], ResolvedAnchor)
    assert isinstance(bound[1].anchors[0], ResolvedAnchor)
    assert (bound[1].anchors[0].char_start, bound[1].anchors[0].char_end) == (9, 14)
    assert bound[2].anchors == ()
    assert bound == bind_window_claim_cohort(layer, windows, _replies())


def test_absent_quote_is_retained_as_unresolved_not_silently_dropped() -> None:
    layer, windows = _source()
    replies = (
        _replies()[0],
        WindowReplyClaims(1, (WindowQuoteClaim(3, "нет такой строки"),)),
        _replies()[2],
    )
    answer = bind_window_claim_cohort(layer, windows, replies)
    assert isinstance(answer[1].anchors[0], UnresolvedAnchor)
    assert answer[1].anchors[0].reason == "quotation_absent"


@pytest.mark.parametrize("variation", ["missing", "extra", "duplicate", "reordered"])
def test_every_window_requires_one_ordered_reply(variation: str) -> None:
    layer, windows = _source()
    replies = _replies()
    if variation == "missing":
        changed = replies[:-1]
    elif variation == "extra":
        changed = (*replies, WindowReplyClaims(3, ()))
    elif variation == "duplicate":
        changed = (replies[0], replies[0], replies[2])
    else:
        changed = (replies[1], replies[0], replies[2])
    with pytest.raises(WindowAnchorError):
        bind_window_claim_cohort(layer, windows, changed)


def test_claim_from_another_window_refuses_whole_cohort() -> None:
    layer, windows = _source()
    replies = (
        WindowReplyClaims(0, (WindowQuoteClaim(3, "фасад"),)),
        *_replies()[1:],
    )
    with pytest.raises(WindowAnchorError, match="page_outside_window"):
        bind_window_claim_cohort(layer, windows, replies)


@pytest.mark.parametrize("bad_claim", [WindowQuoteClaim(True, "А😀"), WindowQuoteClaim(1, "")])
def test_invalid_claim_refuses(bad_claim: WindowQuoteClaim) -> None:
    layer, windows = _source()
    replies = (WindowReplyClaims(0, (bad_claim,)), *_replies()[1:])
    with pytest.raises(WindowAnchorError, match="invalid_quote_claim"):
        bind_window_claim_cohort(layer, windows, replies)


def test_non_tuple_claims_refuse_instead_of_becoming_empty() -> None:
    layer, windows = _source()
    replies = (WindowReplyClaims(0, []), *_replies()[1:])  # type: ignore[arg-type]
    with pytest.raises(WindowAnchorError, match="invalid_window_reply_cohort"):
        bind_window_claim_cohort(layer, windows, replies)


def test_forged_plan_refuses_even_when_every_reply_has_no_claim() -> None:
    layer, windows = _source()
    forged = (replace(windows[0], text="подмена"), *windows[1:])
    empty_replies = tuple(WindowReplyClaims(i, ()) for i in range(len(windows)))
    with pytest.raises(WindowAnchorError, match="invalid_window_plan"):
        bind_window_claim_cohort(layer, forged, empty_replies)
