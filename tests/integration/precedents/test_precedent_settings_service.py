"""`PREC-SETTINGS-01`: the journal of the programme's switches and settings, behind ``listPrecedentSettings`` and ``appendPrecedentSetting`` (contract 1.51.0).

Real PostgreSQL. Every test runs inside one transaction that is rolled back (``journalled_sessions``): the journal is append-only, so what a test writes
cannot be taken back, and the window setting it writes is read by the night window's own suites. The roles are read through the access boundary
exactly as in production for the seeded administrator, and injected for the cases that need an expert or a viewer. Each rule is shown by the call
that is refused or answered differently next to the one that is not.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.precedents import settings as journal
from auditmanager.precedents.public import PrecedentSettingService, one_list_enabled
from auditmanager.precedents.vectors import repository as vectors
from auditmanager.shared.errors import DomainError, ErrorCode

ADMIN_ROLES = lambda _session, _user: frozenset({"admin"})  # noqa: E731
EXPERT_ROLES = lambda _session, _user: frozenset({"expert"})  # noqa: E731
VIEWER_ROLES = lambda _session, _user: frozenset({"viewer"})  # noqa: E731
WINDOW = {"start": "02:00", "end": "05:00", "tz": "Asia/Almaty"}


def key(label: str) -> str:
    return f"prec-settings-{label}-{uuid.uuid4()}"


def count(sessions: sessionmaker[Session], sql: str, **bind: Any) -> int:
    with sessions() as session:
        return int(session.execute(text(sql), bind).scalar_one())


def journal_rows(sessions: sessionmaker[Session]) -> int:
    return count(sessions, "SELECT count(*) FROM precedent_setting_event")


def commands(sessions: sessionmaker[Session]) -> int:
    return count(sessions, "SELECT count(*) FROM command_record WHERE command_type = 'append_precedent_setting'")


def events(sessions: sessionmaker[Session]) -> int:
    return count(sessions, "SELECT count(*) FROM audit_event WHERE event_type = 'precedent.setting_appended'")


def append(service: PrecedentSettingService, uid: str, name: str, value: dict[str, Any], label: str = "k") -> dict[str, Any]:
    return service.append_precedent_setting(setting_name=name, value=value, user_uid=uid, idempotency_key=key(label))


# -- the round trip ----------------------------------------------------------------------------------------------------


def test_an_administrator_appends_and_reads_back_and_the_revisions_have_no_gap(journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    rows, ledger, audit = journal_rows(sessions), commands(sessions), events(sessions)
    first = append(service, admin_uid, "critic_context", {"enabled": True})
    second = append(service, admin_uid, "critic_context", {"enabled": False})
    other = append(service, admin_uid, "stop_words", {"words": ["срочно"]})
    third = append(service, admin_uid, "critic_context", {"enabled": True})
    assert (second["revision"], third["revision"]) == (first["revision"] + 1, first["revision"] + 2)
    assert other["revision"] == count(sessions, "SELECT max(revision) FROM precedent_setting_event WHERE setting_name = 'stop_words'"), "numbered per name"
    for name in ("critic_context", "stop_words"):
        with sessions() as session:
            numbers = session.execute(text("SELECT revision FROM precedent_setting_event WHERE setting_name = :n ORDER BY revision"), {"n": name}).scalars().all()
        assert numbers == list(range(1, len(numbers) + 1)), f"{name}: gapless from 1"
    assert first["actor_user_uid"] == admin_uid and first["value"] == {"enabled": True} and first["created_at"].tzinfo is not None

    shown = service.list_precedent_settings(user_uid=admin_uid)
    by_name = {item["setting_name"]: item for item in shown["current"]}
    assert by_name["critic_context"]["revision"] == third["revision"] and by_name["critic_context"]["value"] == {"enabled": True}
    assert by_name["stop_words"]["value"] == {"words": ["срочно"]}
    names = [item["setting_name"] for item in shown["current"]]
    assert len(names) == len(set(names)), "at most one per name"
    assert names == [name for name in journal.SETTING_NAMES if name in names], "in the contract's order of the names"
    assert [(e["setting_name"], e["revision"]) for e in shown["events"][:4]] == [
        ("critic_context", third["revision"]), ("stop_words", other["revision"]),
        ("critic_context", second["revision"]), ("critic_context", first["revision"])], "the journal, newest first"
    moments = [e["created_at"] for e in shown["events"]]
    assert moments == sorted(moments, reverse=True)

    assert journal_rows(sessions) == rows + 4 and commands(sessions) == ledger + 4 and events(sessions) == audit + 4
    with sessions() as session:
        outcome = session.execute(text(
            "SELECT state, command_type FROM command_record WHERE command_type = 'append_precedent_setting' ORDER BY created_at DESC LIMIT 1")).one()
        payload = session.execute(text(
            "SELECT payload, aggregate_type FROM audit_event WHERE event_type = 'precedent.setting_appended' ORDER BY sequence_no DESC LIMIT 1")).one()
    assert tuple(outcome) == ("succeeded", "append_precedent_setting")
    assert payload[0] == {"setting_name": "critic_context", "revision": third["revision"], "actor_uid": admin_uid}, "no value in the event"
    assert payload[1] == "PrecedentSetting"


def test_the_seeded_administrator_is_an_administrator_through_the_access_boundary(
    journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    """No injected roles: the default reads them as production does, so a wrong import path or role word shows here."""
    service = PrecedentSettingService(journalled_sessions)
    written = append(service, admin_uid, "section_labels", {"AR": {"enabled": False}})
    assert written["actor_user_uid"] == admin_uid
    assert any(item["setting_name"] == "section_labels" and item["revision"] == written["revision"]
               for item in service.list_precedent_settings(user_uid=admin_uid)["current"])


def test_the_switch_the_run_start_reads_follows_what_the_administrator_journalled(
    journalled_sessions: sessionmaker[Session], admin_uid: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    append(service, admin_uid, "one_list", {"enabled": False})
    with sessions() as session:
        assert one_list_enabled(session) is False
    monkeypatch.setattr(journal, "ONE_LIST_READY", True)
    append(service, admin_uid, "one_list", {"enabled": True})
    with sessions() as session:
        assert one_list_enabled(session) is True, "what the run's start reads is what the administrator journalled"


# -- who may ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("roles", [EXPERT_ROLES, VIEWER_ROLES])
def test_only_an_administrator_may_read_or_write_and_a_refusal_writes_nothing(
    journalled_sessions: sessionmaker[Session], admin_uid: str, roles: object,
) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=roles)  # type: ignore[arg-type]
    rows, ledger, audit = journal_rows(sessions), commands(sessions), events(sessions)
    with pytest.raises(DomainError) as caught:
        append(service, admin_uid, "critic_context", {"enabled": False})
    assert caught.value.code == ErrorCode.PERMISSION_DENIED
    with pytest.raises(DomainError) as read:
        service.list_precedent_settings(user_uid=admin_uid)
    assert read.value.code == ErrorCode.PERMISSION_DENIED
    assert (journal_rows(sessions), commands(sessions), events(sessions)) == (rows, ledger, audit)


# -- what a value may be ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "value", "constraint"), [
    ("one_list", {"enabled": "yes"}, "switch_shape"),
    ("critic_context", {}, "switch_shape"),
    ("critic_context", {"enabled": True, "x": 1}, "switch_shape"),
    ("vector_window", {"start": "01:00", "end": "06:00"}, "vector_window_shape"),
    ("vector_window", {"start": "01:00", "end": "06:00", "tz": "Mars/Base"}, "vector_window_shape"),
    ("vector_window", {"start": "03:00", "end": "03:00", "tz": "UTC"}, "vector_window_shape"),
    ("thresholds", [1], "object"),
    ("thresholds", {"a": float("nan")}, "json"),
    ("stop_words", {"w": "x" * 20000}, "value_too_large"),
    ("ar_v3", {"enabled": True}, "enum"),
])
def test_a_value_that_is_not_the_shape_of_its_setting_is_refused_before_the_database_and_leaves_no_record(
    journalled_sessions: sessionmaker[Session], admin_uid: str, name: str, value: Any, constraint: str,
) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    rows, ledger, audit = journal_rows(sessions), commands(sessions), events(sessions)
    same = key("bad")
    with pytest.raises(DomainError) as caught:
        service.append_precedent_setting(setting_name=name, value=value, user_uid=admin_uid, idempotency_key=same)
    assert caught.value.code == ErrorCode.VALIDATION_FAILED and caught.value.detail_fields["constraint"] == constraint
    assert (journal_rows(sessions), commands(sessions), events(sessions)) == (rows, ledger, audit)
    # the refusal came before the key was claimed: the same key is free for the corrected request
    fixed = service.append_precedent_setting(setting_name="critic_context", value={"enabled": False}, user_uid=admin_uid, idempotency_key=same)
    assert fixed["setting_name"] == "critic_context"


def test_the_limit_on_the_size_of_a_value_is_the_databases_own(journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    """The value that just meets the limit is accepted by the journal's CHECK (``octet_length(value::text) <= 16384``), the one octet more is refused
    here: the service's count and the database's agree, so neither a refusal is spurious nor a database error reaches the administrator."""
    service = PrecedentSettingService(journalled_sessions, roles_of=ADMIN_ROLES)
    at_limit = append(service, admin_uid, "stop_words", {"w": "x" * (journal.VALUE_MAX_OCTETS - 9)})
    assert len(at_limit["value"]["w"]) == journal.VALUE_MAX_OCTETS - 9
    cyrillic = append(service, admin_uid, "thresholds", {"w": "я" * ((journal.VALUE_MAX_OCTETS - 9) // 2)})
    assert cyrillic["revision"] >= 1
    with pytest.raises(DomainError) as caught:
        append(service, admin_uid, "stop_words", {"w": "x" * (journal.VALUE_MAX_OCTETS - 8)})
    assert caught.value.detail_fields["constraint"] == "value_too_large"


def test_one_list_cannot_be_switched_on_while_it_is_not_ready_but_can_be_switched_off(
    journalled_sessions: sessionmaker[Session], admin_uid: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    monkeypatch.setattr(journal, "ONE_LIST_READY", False)
    rows = journal_rows(sessions)
    with pytest.raises(DomainError) as caught:
        append(service, admin_uid, "one_list", {"enabled": True})
    assert caught.value.code == ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": "value", "constraint": "one_list_not_ready"}
    assert journal_rows(sessions) == rows
    assert append(service, admin_uid, "one_list", {"enabled": False})["value"] == {"enabled": False}, "off is always allowed"
    monkeypatch.setattr(journal, "ONE_LIST_READY", True)
    assert append(service, admin_uid, "one_list", {"enabled": True})["value"] == {"enabled": True}, "and the guard is lifted by the one constant"


def test_the_window_that_is_journalled_is_the_window_the_night_reads(journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    written = append(service, admin_uid, "vector_window", WINDOW)
    assert written["value"] == WINDOW
    with sessions() as session:
        assert vectors.read_window_setting(session).as_value() == WINDOW


# -- a keyed write ---------------------------------------------------------------------------------------------------------


def test_the_same_key_and_body_answers_the_same_revision_and_writes_nothing_twice(journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    same = key("replay")
    first = service.append_precedent_setting(setting_name="critic_context", value={"enabled": True}, user_uid=admin_uid, idempotency_key=same)
    rows, ledger, audit = journal_rows(sessions), commands(sessions), events(sessions)
    again = service.append_precedent_setting(setting_name="critic_context", value={"enabled": True}, user_uid=admin_uid, idempotency_key=same)
    assert again == first
    # a later revision does not change what the key answers: the key made revision N, and still answers N
    later = append(service, admin_uid, "critic_context", {"enabled": False})
    assert later["revision"] == first["revision"] + 1
    assert service.append_precedent_setting(setting_name="critic_context", value={"enabled": True}, user_uid=admin_uid, idempotency_key=same) == first
    assert (journal_rows(sessions), commands(sessions), events(sessions)) == (rows + 1, ledger + 1, audit + 1)


def test_the_same_key_with_another_body_is_refused_as_a_reuse_of_the_key(journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    same = key("conflict")
    service.append_precedent_setting(setting_name="critic_context", value={"enabled": True}, user_uid=admin_uid, idempotency_key=same)
    rows = journal_rows(sessions)
    for name, value in (("critic_context", {"enabled": False}), ("section_labels", {"enabled": True})):
        with pytest.raises(DomainError) as caught:
            service.append_precedent_setting(setting_name=name, value=value, user_uid=admin_uid, idempotency_key=same)
        assert caught.value.code == ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert journal_rows(sessions) == rows, "and the refused write changed nothing"


def test_two_writers_of_one_name_queue_on_the_lock_the_journals_own_trigger_takes(journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    """The service reads the next number under the same advisory lock ``am_check_gapless_number`` takes (``precedent_setting_event:<name>``), so a
    second administrator is queued behind the first instead of meeting the trigger's refusal: the name hashes to one lock, not to two."""
    sessions = journalled_sessions
    service = PrecedentSettingService(sessions, roles_of=ADMIN_ROLES)
    append(service, admin_uid, "critic_context", {"enabled": False})
    with sessions() as session:
        held = session.execute(text(
            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()")).scalar_one()
        same = session.execute(text(
            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid() "
            "AND ((classid::bigint << 32) | objid::bigint) = hashtextextended('precedent_setting_event:critic_context', 0)")).scalar_one()
    assert held == 1 and same == 1
