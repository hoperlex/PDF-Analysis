"""The status of a pair (`CMP-ENGINE-01`): «Совпадает» only when every applicable channel is ``checked``.

The sets are the original's (``status.py:11-20`` at ``23f379fd``); the one difference, ``annotations`` as a main
channel, is ADR-0025 decision 15 and the answer key of the corpus.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from auditmanager.comparison.engine.child import result as res
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
    assert f"UNCHECKED_CHANNEL_{channel.upper()}" in reasons


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


def _contract_reason_pattern() -> str:
    document = json.loads((Path(__file__).resolve().parents[4] / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    return document["components"]["schemas"]["ComparisonSheetPair"]["properties"]["reasons"]["items"]["pattern"]


def test_the_engine_never_writes_a_colon_and_every_reason_it_writes_fits_the_contracts_pattern() -> None:
    """`CMP-SERIES-01` section 9 item 1 (`CMP-C1-FIX-A` item 1): the first version wrote ``UNCHECKED_CHANNEL:<channel>``, which
    ``ComparisonSheetPair.reasons`` (``^[A-Z][A-Z0-9_]{2,63}$``) refuses. The pattern is read from the contract document."""
    pattern = re.compile(_contract_reason_pattern())
    everything = {name: unchecked("не смотрели") for name in CHANNELS}
    outcomes = [
        decide(everything, []),
        decide(_channels(), ["MATCH_LOW_CONFIDENCE"]),
        (None, res.failure_outcome("RENDER_FAILED", "не удалось")["reasons"]),
        (None, res.identical_outcome(width_pt=1.0, height_pt=1.0, dpi=72, reasons=["DUPLICATE_SHEET"], annotation_diffs=0,
                                     has_annotations=False, service_notes=[], is_spec=False)["reasons"]),
    ]
    for channel in CHANNELS:
        outcomes.append(decide(_channels(**{channel: unchecked("нет")}), []))
    written = [reason for _, reasons in outcomes for reason in reasons]
    assert any(reason.startswith("UNCHECKED_CHANNEL") for reason in written), "the probe must reach the unchecked-channel branch"
    for reason in written:
        assert ":" not in reason and pattern.fullmatch(reason), reason
    assert st.unchecked_channel_reason("spec_positions") == "UNCHECKED_CHANNEL_SPEC_POSITIONS"
    assert all(pattern.fullmatch(st.unchecked_channel_reason(name)) for name in CHANNELS)

