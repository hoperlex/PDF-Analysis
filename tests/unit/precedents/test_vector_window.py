"""`EMBED-01`: the night window of the vectors, as pure functions of a clock and a setting (`ADR-0029` decision 8, plan-v5 section 5).

Each rule is shown by a moment that is inside next to one that is outside, and every guard by an input that makes it refuse: a window that opened an
hour early would stop the stand's runs at an hour nobody chose.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from auditmanager.precedents.vectors.window import (
    DEFAULT_WINDOW,
    OPEN_STATES,
    SKIP_REASONS,
    STATES,
    parse_setting,
    current_span,
    wait_text,
)

YEKAT = timezone(timedelta(hours=5))


def at(hour: int, minute: int = 0, *, day: int = 11, tz: timezone = YEKAT) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=tz)


def test_the_default_window_is_one_to_six_at_yekaterinburg() -> None:
    assert DEFAULT_WINDOW.as_value() == {"start": "01:00", "end": "06:00", "tz": "Asia/Yekaterinburg"}


def test_inside_and_outside_the_default_window_are_told_apart_at_both_edges() -> None:
    inside = [at(1, 0), at(3, 30), at(5, 59)]
    outside = [at(0, 59), at(6, 0), at(12, 0), at(23, 59)]
    assert all(current_span(moment, DEFAULT_WINDOW) is not None for moment in inside)
    assert all(current_span(moment, DEFAULT_WINDOW) is None for moment in outside)


def test_the_window_is_read_on_the_zones_wall_clock_not_the_servers() -> None:
    """01:00 at +05 is 20:00 UTC the evening before: a window kept in UTC would open at 01:00 UTC, which is 06:00 at the stand."""
    in_utc = datetime(2026, 11, 10, 20, 30, tzinfo=UTC)
    assert current_span(in_utc, DEFAULT_WINDOW) is not None
    assert current_span(datetime(2026, 11, 11, 1, 30, tzinfo=UTC), DEFAULT_WINDOW) is None
    span = current_span(in_utc, DEFAULT_WINDOW)
    assert span is not None and span.opens_at == at(1, 0) and span.closes_at == at(6, 0)


def test_the_sentence_a_waiting_run_is_told_names_the_closing_hour_in_the_windows_zone() -> None:
    span = current_span(at(2, 0), DEFAULT_WINDOW)
    assert span is not None
    assert wait_text(span, DEFAULT_WINDOW) == "ночное окно векторов, до 06:00"
    other = parse_setting({"start": "22:30", "end": "03:15", "tz": "Europe/Moscow"})
    moscow = current_span(datetime(2026, 11, 11, 0, 0, tzinfo=timezone(timedelta(hours=3))), other)
    assert moscow is not None and wait_text(moscow, other) == "ночное окно векторов, до 03:15"


def test_a_window_that_crosses_midnight_is_open_on_both_sides_of_it() -> None:
    setting = parse_setting({"start": "22:00", "end": "03:00", "tz": "Asia/Yekaterinburg"})
    assert current_span(at(23, 0), setting) is not None
    late = current_span(at(1, 0, day=12), setting)
    assert late is not None and late.opens_at == at(22, 0, day=11) and late.closes_at == at(3, 0, day=12)
    assert current_span(at(3, 0, day=12), setting) is None
    assert current_span(at(21, 59), setting) is None


@pytest.mark.parametrize("value", [
    {"start": "01:00", "end": "01:00", "tz": "Asia/Yekaterinburg"},          # no window, or all of the day: the setting never says which
    {"start": "1:00", "end": "06:00", "tz": "Asia/Yekaterinburg"},
    {"start": "24:00", "end": "06:00", "tz": "Asia/Yekaterinburg"},
    {"start": "01:60", "end": "06:00", "tz": "Asia/Yekaterinburg"},
    {"start": "01:00", "end": "06:00", "tz": "Mars/Olympus"},
    {"start": "01:00", "end": "06:00", "tz": ""},
    {"start": "01:00", "end": "06:00"},
    {"start": "01:00", "end": "06:00", "tz": "Asia/Yekaterinburg", "days": 3},
    {"start": 100, "end": "06:00", "tz": "Asia/Yekaterinburg"},
])
def test_a_setting_that_is_not_the_shape_is_refused_not_read_as_the_default(value: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_setting(value)


def test_a_moment_without_a_zone_is_refused() -> None:
    with pytest.raises(ValueError):
        current_span(datetime(2026, 11, 11, 2, 0), DEFAULT_WINDOW)


def test_the_states_are_the_contracts_and_two_of_them_hold_the_stand() -> None:
    assert STATES == ("closed", "draining", "encoding", "skipped")
    assert OPEN_STATES == ("draining", "encoding")
    assert all(reason.replace("_", "").isalnum() and reason[0].isalpha() for reason in SKIP_REASONS)
    assert all(len(reason) <= 64 for reason in SKIP_REASONS)
