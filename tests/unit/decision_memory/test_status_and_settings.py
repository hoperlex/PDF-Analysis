"""`DECISION-MEMORY-01` phase M2: the rule of a case's standing, the closed vocabularies and the settings' defaults, with no database.

The rule lives once (``decision_memory.status``) and is repeated where it cannot be bypassed (``am_guard_decision_memory_status`` in
migration ``0061``); this file pins the first and ties it to the second by text, and
``tests/integration/decisions/test_decision_memory_status.py`` shows the database refusing what the rule refuses.
"""

from __future__ import annotations

import re
from itertools import product
from pathlib import Path

import pytest

from auditmanager.decision_memory import public
from auditmanager.decision_memory.service import STATUS_LOCK_PREFIX
from auditmanager.decision_memory.status import (
    CASE_STATUSES,
    CONFLICT_CASE_FORGOTTEN,
    STATUS_ACTIVE,
    STATUS_FORGOTTEN,
    STATUS_KINDS,
    STATUS_REASON_CODES,
    STATUS_WITHDRAWN,
    check_reason,
    next_status,
    status_after_events,
)
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "db/migrations/versions/20261109_0061_decision_memory_m2.py"

#: The whole table of the rule, written out: (current standing, requested kind) -> the standing after, or the refusal's code.
EXPECTED = {
    (STATUS_ACTIVE, "withdraw"): STATUS_WITHDRAWN,
    (STATUS_ACTIVE, "restore"): ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
    (STATUS_ACTIVE, "forget"): STATUS_FORGOTTEN,
    (STATUS_WITHDRAWN, "withdraw"): ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
    (STATUS_WITHDRAWN, "restore"): STATUS_ACTIVE,
    (STATUS_WITHDRAWN, "forget"): STATUS_FORGOTTEN,
    (STATUS_FORGOTTEN, "withdraw"): ErrorCode.CONFLICT,
    (STATUS_FORGOTTEN, "restore"): ErrorCode.CONFLICT,
    (STATUS_FORGOTTEN, "forget"): ErrorCode.CONFLICT,
}


def test_the_table_covers_every_pair() -> None:
    assert set(EXPECTED) == set(product(CASE_STATUSES, STATUS_KINDS))


@pytest.mark.parametrize(("current", "kind"), sorted(EXPECTED))
def test_a_transition_is_allowed_or_refused_exactly_as_the_table_says(current: str, kind: str) -> None:
    expected = EXPECTED[(current, kind)]
    if not isinstance(expected, ErrorCode):
        assert next_status(current, kind) == expected
        return
    with pytest.raises(DomainError) as refused:
        next_status(current, kind)
    assert refused.value.code is expected
    if expected is ErrorCode.CONFLICT:
        assert refused.value.detail_fields["conflict_reason"] == CONFLICT_CASE_FORGOTTEN
    else:
        assert refused.value.detail_fields["machine"] == "decision_memory_case"
        assert refused.value.detail_fields["current_state"] == current


def test_the_standing_is_the_latest_event_and_none_is_active() -> None:
    assert status_after_events(None) == STATUS_ACTIVE
    assert status_after_events("withdraw") == STATUS_WITHDRAWN
    assert status_after_events("restore") == STATUS_ACTIVE
    assert status_after_events("forget") == STATUS_FORGOTTEN
    with pytest.raises(ValueError):
        status_after_events("delete")


def test_a_reason_is_one_of_the_closed_list_and_nothing_else() -> None:
    assert STATUS_REASON_CODES == ("capture_defect", "wrong_decision", "client_request", "test_data", "other")
    for reason in STATUS_REASON_CODES:
        assert check_reason(reason) == reason
    for free_text in ("", "because", "Wrong decision", "other "):
        with pytest.raises(DomainError) as refused:
            check_reason(free_text)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED


def test_the_vocabularies_are_the_ones_the_migration_checks() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    first = (ROOT / "db/migrations/versions/20261109_0059_decision_memory.py").read_text(encoding="utf-8")
    reasons = re.search(r"reason_code IN \(([^)]*)\)", first)
    assert reasons is not None
    assert tuple(re.findall(r"'([a-z_]+)'", reasons.group(1))) == STATUS_REASON_CODES
    kinds = re.search(r"\bkind IN \(([^)]*)\)", first)
    assert kinds is not None
    assert tuple(re.findall(r"'([a-z_]+)'", kinds.group(1))) == STATUS_KINDS
    for status in ("withdrawn", "forgotten", "active"):
        assert f"'{status}'" in source  # the view names the three standings


def test_the_service_and_the_database_guard_take_the_same_advisory_lock() -> None:
    """The check-then-insert of withdraw and restore is only atomic if the service and the trigger queue on one key."""
    source = MIGRATION.read_text(encoding="utf-8")
    assert f"'{STATUS_LOCK_PREFIX}' || NEW.case_id" in source
    forget = (ROOT / "scripts/recovery/memory_forget.py").read_text(encoding="utf-8")
    assert f'STATUS_LOCK_PREFIX = "{STATUS_LOCK_PREFIX}"' in forget


def test_the_settings_default_to_the_safe_values() -> None:
    assert public.SETTING_DEFAULTS == {"data_class": "test", "training_use": "off"}
    assert public.SETTING_VALUES == {"data_class": ("test", "real"), "training_use": ("off", "on")}
    assert public.SETTING_NAMES == ("data_class", "training_use")
    settings = public.MemorySettings(data_class="test", training_use="off")
    assert not settings.training_enabled and settings.data_class_revision == 0
    assert public.MemorySettings(data_class="real", training_use="on", training_use_revision=2).training_enabled


def test_the_settings_vocabulary_is_the_migrations() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "setting_name IN ('data_class', 'training_use')" in source
    assert "value IN ('test', 'real', 'off', 'on')" in source
    assert "(setting_name = 'data_class' AND value IN ('test', 'real'))" in source
    assert "(setting_name = 'training_use' AND value IN ('off', 'on'))" in source
