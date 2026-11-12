"""`PREC-SETTINGS-01`: what a value of each setting may be, with no database (contract 1.51.0, migration ``0064``).

``checked_value`` is what the service asks before it claims the key, so a value the database's CHECKs would refuse -- and a few more the programme
refuses -- is told as ``validation_failed`` with a ``field`` and a ``constraint``. Each rule is shown by the value that is refused next to the one
that is not, and the one guard of the programme (`D-683`) is shown both ways: refused while ``ONE_LIST_READY`` is false, accepted when it is true.
"""

from __future__ import annotations

import pytest

from auditmanager.api.routers.precedents import APPEND_PRECEDENT_SETTING_COMMAND_TYPE as ROUTER_COMMAND_TYPE
from auditmanager.api.schemas import models
from auditmanager.precedents import settings as journal
from auditmanager.precedents.setting_journal.service import APPEND_PRECEDENT_SETTING_COMMAND_TYPE, checked_value
from auditmanager.precedents.vectors import window
from auditmanager.shared.errors import DomainError, ErrorCode

WINDOW = {"start": "01:00", "end": "06:00", "tz": "Asia/Yekaterinburg"}


def refused(name: object, value: object) -> dict[str, object]:
    with pytest.raises(DomainError) as caught:
        checked_value(name, value)
    assert caught.value.code == ErrorCode.VALIDATION_FAILED
    return dict(caught.value.detail_fields)


def test_the_names_the_command_type_and_the_window_word_are_the_contracts_and_the_routers() -> None:
    assert list(journal.SETTING_NAMES) == [item.value for item in models.PrecedentSettingName]
    assert journal.SETTING_VECTOR_WINDOW == window.SETTING_NAME
    assert APPEND_PRECEDENT_SETTING_COMMAND_TYPE == ROUTER_COMMAND_TYPE == "append_precedent_setting"


@pytest.mark.parametrize("name", ["one_list", "critic_context"])
def test_a_switch_is_exactly_an_enabled_flag_that_is_a_boolean(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(journal, "ONE_LIST_READY", True)      # what is shown here is the shape, not the guard
    assert checked_value(name, {"enabled": False}) == {"enabled": False}
    assert checked_value(name, {"enabled": True}) == {"enabled": True}
    for bad in ({}, {"enabled": "yes"}, {"enabled": 1}, {"enabled": None}, {"enabled": True, "note": "x"}, {"on": True}):
        assert refused(name, bad) == {"field": "value", "constraint": "switch_shape"}, bad


def test_one_list_cannot_be_switched_on_while_it_is_not_ready_and_can_be_switched_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(journal, "ONE_LIST_READY", False)
    assert refused("one_list", {"enabled": True}) == {"field": "value", "constraint": "one_list_not_ready"}
    assert checked_value("one_list", {"enabled": False}) == {"enabled": False}, "off is always allowed"
    assert checked_value("critic_context", {"enabled": True}) == {"enabled": True}, "the guard is one switch's"
    monkeypatch.setattr(journal, "ONE_LIST_READY", True)
    assert checked_value("one_list", {"enabled": True}) == {"enabled": True}, "the guard can be lifted with one line"


def test_the_completed_one_list_reader_allows_explicit_administrator_activation() -> None:
    assert checked_value("one_list", {"enabled": True}) == {"enabled": True}


def test_the_window_is_read_by_the_parser_the_night_window_reads_it_with() -> None:
    assert checked_value("vector_window", WINDOW) == WINDOW
    assert checked_value("vector_window", {"start": "22:00", "end": "03:00", "tz": "UTC"}) == {"start": "22:00", "end": "03:00", "tz": "UTC"}
    for bad in ({"start": "01:00", "end": "06:00"}, {**WINDOW, "extra": 1}, {**WINDOW, "start": "1:00"}, {**WINDOW, "end": "24:00"},
                {**WINDOW, "end": "01:00"}, {**WINDOW, "tz": "Mars"}, {**WINDOW, "tz": ""}, {**WINDOW, "start": 100}):
        assert refused("vector_window", bad) == {"field": "value", "constraint": "vector_window_shape"}, bad
        with pytest.raises(ValueError):
            window.parse_setting(bad)       # the worker would refuse the very same value, so it must never be journalled


def test_the_other_settings_are_the_shapes_the_pass_reads() -> None:
    """`PREC-PASS` gave the three their shapes (``tests/unit/precedents/test_section_switch.py`` shows each refusal): a value the pass could not read would be
    a switch that does nothing."""
    assert checked_value("stop_words", {"words": ["срочно"]}) == {"words": ["срочно"]}
    assert checked_value("thresholds", {"analogous": 0.85, "similar": 0.75, "history": 0.92}) == {"analogous": 0.85, "similar": 0.75, "history": 0.92}
    assert checked_value("section_labels", {"AR": {"enabled": True, "report_sha256": "a" * 64}}) == {
        "AR": {"enabled": True, "report_sha256": "a" * 64}}
    assert refused("thresholds", {}) == {"field": "value", "constraint": "thresholds_shape"}


def test_a_value_that_is_not_an_object_or_not_json_or_too_large_is_refused() -> None:
    for name in journal.SETTING_NAMES:
        for bad in ([1], "x", 1, None, True):
            assert refused(name, bad) == {"field": "value", "constraint": "object"}, (name, bad)
    assert refused("thresholds", {"a": float("nan")}) == {"field": "value", "constraint": "json"}
    assert refused("thresholds", {"a": float("inf")}) == {"field": "value", "constraint": "json"}
    assert refused("stop_words", {"words": "x" * journal.VALUE_MAX_OCTETS})["constraint"] == "value_too_large"
    # the limit counts octets of the UTF-8 text, as ``octet_length(value::text)`` does: two-octet letters reach it at half the characters
    assert refused("stop_words", {"w": "я" * (journal.VALUE_MAX_OCTETS // 2)})["constraint"] == "value_too_large"
    # the text of ``{"w": "..."}`` is nine octets longer than what is between the quotes: the limit is met exactly, and not one octet over
    # (no valid value of a shaped setting is that large, so the exact limit is shown by what is refused next: the shape, not the size)
    assert refused("stop_words", {"w": "x" * (journal.VALUE_MAX_OCTETS - 9)})["constraint"] == "stop_words_shape"
    assert refused("stop_words", {"w": "x" * (journal.VALUE_MAX_OCTETS - 8)})["constraint"] == "value_too_large"


def test_an_unknown_name_is_refused_before_the_value_is_looked_at() -> None:
    for name in ("ar_v3", "", "One_List", None, 1):
        assert refused(name, {"enabled": True}) == {"field": "setting_name", "constraint": "enum"}, name
