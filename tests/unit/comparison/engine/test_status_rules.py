"""The status of a pair (`CMP-ENGINE-01`): «Совпадает» only when every applicable channel is ``checked``.

The sets are the original's (``status.py:11-20`` at ``23f379fd``); the one difference, ``annotations`` as a main
channel, is ADR-0025 decision 15 and the answer key of the corpus.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.engine.child import status as st
from auditmanager.comparison.engine.child.status import CHANNELS, checked, decide, not_applicable, unchecked


def _channels(**changes):
    channels = {name: checked(0) for name in CHANNELS}
    channels["annotations"] = not_applicable("нет")
    channels["warnings"] = not_applicable("нет")
    channels["spec_positions"] = not_applicable("нет")
    channels.update(changes)
    return channels


def test_all_channels_checked_without_a_difference_is_same() -> None:
    assert decide(_channels(), [])[0] == "same"


@pytest.mark.parametrize("channel", CHANNELS)
def test_a_channel_that_is_unchecked_is_never_same(channel: str) -> None:
    status, reasons = decide(_channels(**{channel: unchecked("не смотрели")}), [])
    assert status == "needs_review"
    assert f"UNCHECKED_CHANNEL:{channel}" in reasons


@pytest.mark.parametrize("channel", CHANNELS)
def test_a_channel_nobody_computed_is_unchecked_and_not_same(channel: str) -> None:
    channels = _channels()
    del channels[channel]
    status, reasons = decide(channels, [])
    assert status != "same" and channels[channel]["state"] == "unchecked"


def test_a_channel_that_does_not_apply_does_not_stop_a_same() -> None:
    assert decide(_channels(spec_positions=not_applicable("не спецификация")), [])[0] == "same"


@pytest.mark.parametrize("channel", ["geometry", "color", "text"])
def test_a_difference_in_a_main_channel_is_different(channel: str) -> None:
    assert decide(_channels(**{channel: checked(2)}), [])[0] == "different"


def test_an_annotation_only_change_is_different_not_a_service_change() -> None:
    """ADR-0025 decision 15: an annotation-only change gives ``different`` in ``annotations``."""
    status, _ = decide(_channels(annotations=checked(1)), [])
    assert status == "different"


@pytest.mark.parametrize("channel", ["zones", "warnings"])
def test_a_difference_in_a_service_channel_alone_is_same_with_zones_changed(channel: str) -> None:
    assert decide(_channels(**{channel: checked(1)}), [])[0] == "same_zones_changed"


def test_a_main_difference_beats_a_service_difference() -> None:
    assert decide(_channels(geometry=checked(1), zones=checked(3)), [])[0] == "different"


def test_a_difference_beats_an_unchecked_channel() -> None:
    """The original's order (``status.py:58-63``): a main difference is decided before an unchecked channel."""
    assert decide(_channels(geometry=checked(1), text_coverage=unchecked("нет")), [])[0] == "different"


ORIGINAL = {
    "MATCH_LOW_CONFIDENCE", "MATCH_AMBIGUOUS", "MATCH_UNRESOLVED", "ALIGNMENT_UNRELIABLE", "ALIGNMENT_PARTIAL",
    "PARTIAL_COVERAGE", "DUPLICATE_SHEET", "RENDER_FAILED", "NO_TEXT_LAYER", "TEXT_UNREADABLE_IN_DIFF_AREA",
    "STAMP_NOT_RECOGNIZED", "SPEC_NOT_PARSED",
}


def test_the_forcing_reasons_are_the_originals_and_two_of_this_product() -> None:
    assert st.ORIGINAL_FORCING_REASONS == ORIGINAL
    assert st.OWN_FORCING_REASONS == {"PAGE_TOO_LARGE", "FRAME_MISMATCH"}
    assert st.FORCING_REASONS == ORIGINAL | {"PAGE_TOO_LARGE", "FRAME_MISMATCH"}


@pytest.mark.parametrize("reason", sorted(ORIGINAL | {"PAGE_TOO_LARGE", "FRAME_MISMATCH"}))
def test_a_forcing_reason_gives_needs_review_whatever_the_channels_say(reason: str) -> None:
    assert decide(_channels(), [reason])[0] == "needs_review"
    assert decide(_channels(geometry=checked(5)), [reason])[0] == "needs_review"


def test_a_reason_with_a_detail_is_forcing_by_its_code() -> None:
    assert decide(_channels(), ["MATCH_LOW_CONFIDENCE:medium"])[0] == "needs_review"


@pytest.mark.parametrize("reason", ["TABLE_GROUP", "AI_MATCH", "SPLIT_SHEET", "CHAIN_ONLY"])
def test_a_reason_that_only_records_how_the_pair_was_made_does_not_force(reason: str) -> None:
    assert decide(_channels(), [reason])[0] == "same"


def test_the_reasons_keep_their_order_without_repeats() -> None:
    _, reasons = decide(_channels(), ["B", "A", "B"])
    assert reasons == ["B", "A"]


def test_a_reason_text_of_a_channel_fits_the_contract() -> None:
    assert len(unchecked("я" * 500)["reason"]) <= 128
    assert unchecked("")["reason"]
