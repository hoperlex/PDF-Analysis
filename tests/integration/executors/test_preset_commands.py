"""`ANALYSIS-PRESETS-01`: the preset commands over real PostgreSQL, one rolled-back transaction each.

Every guard here is shown able to fail: a refusal test asserts what was *not* written, the audit test
fails the event writer and expects the revision row to vanish with it, and the replay tests count rows.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.executors import preset_commands
from auditmanager.executors.preset_store import PresetStore
from auditmanager.executors.public import (
    archive_connection,
    archive_preset,
    choose_preset,
    create_connection,
    create_preset,
    list_presets,
    preset_of_revision,
    revise_preset,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.executors.conftest import ADMIN

ADMIN_ROLES = frozenset({"admin"})


def key() -> str:
    return f"preset-{uuid4().hex}"


def connection(session, name: str = "proxy") -> str:
    return create_connection(
        session, kind="http_api", display_name=name, roles=ADMIN_ROLES, idempotency_key=key(),
        actor_uid=ADMIN,
    ).connection_id


def make(session, name: str, connection_id: str, **extra):
    return create_preset(
        session, name=name, executor_connection_id=connection_id, roles=ADMIN_ROLES,
        idempotency_key=extra.pop("idempotency_key", key()), actor_uid=ADMIN, **extra,
    )


def revise(session, preset_id: str, name: str, connection_id: str, **extra):
    return revise_preset(
        session, preset_id=preset_id, name=name, executor_connection_id=connection_id,
        roles=ADMIN_ROLES, idempotency_key=extra.pop("idempotency_key", key()), actor_uid=ADMIN, **extra,
    )


def expect(raises, code: ErrorCode, **details) -> DomainError:
    error = raises.value
    assert isinstance(error, DomainError) and error.code is code, error
    for name, value in details.items():
        assert error.detail_fields.get(name) == value, (name, error.detail_fields)
    return error


def rows(session) -> int:
    return int(session.execute(text("SELECT count(*) FROM analysis_preset_revision")).scalar_one())


# -- create -------------------------------------------------------------------------------------


def test_a_created_preset_is_revision_one_named_active_and_its_own_identity(session) -> None:
    c = connection(session)
    record = make(session, "  Быстрый черновик ", c)
    assert record.revision_no == 1 and record.state == "active"
    assert record.name == "Быстрый черновик"  # trimmed
    assert record.executor_connection_id == c
    assert record.preset_id == record.revision_id  # the preset is the id of its first revision
    assert record.revised_by == ADMIN and record.created_at == record.revised_at


def test_the_event_and_the_revision_share_one_id_and_one_transaction(session) -> None:
    c = connection(session)
    record = make(session, "Основной", c, correlation_id="req-0123456789abcdef")
    event = session.execute(text(
        "SELECT event_type, aggregate_type, aggregate_id, correlation_id, payload FROM audit_event "
        "WHERE audit_event_id = :id"), {"id": record.revision_id}).mappings().one()
    assert event["event_type"] == "executor.preset_created"
    assert (event["aggregate_type"], event["aggregate_id"]) == ("AnalysisPreset", record.preset_id)
    assert event["correlation_id"] == "req-0123456789abcdef"
    payload = event["payload"] if isinstance(event["payload"], dict) else json.loads(event["payload"])
    assert payload == {
        "preset_id": record.preset_id, "revision_id": record.revision_id, "revision_no": 1,
        "executor_connection_id": c, "actor_uid": ADMIN}
    assert "Основной" not in json.dumps(payload, ensure_ascii=False)  # the name never enters an event


def test_a_failing_audit_event_takes_the_revision_with_it(session, monkeypatch) -> None:
    c = connection(session)

    def boom(*args, **kwargs):
        raise RuntimeError("the journal is down")

    monkeypatch.setattr(preset_commands, "record_preset_created", boom)
    before = rows(session)
    with pytest.raises(RuntimeError):
        with session.begin_nested():
            make(session, "Потерянный", c)
    assert rows(session) == before  # the INSERT happened and was rolled back with the failed event


def test_a_failing_audit_event_takes_a_revise_and_an_archive_with_it(session, monkeypatch) -> None:
    c = connection(session)
    first = make(session, "Основной", c)

    def boom(*args, **kwargs):
        raise RuntimeError("the journal is down")

    monkeypatch.setattr(preset_commands, "record_preset_revised", boom)
    monkeypatch.setattr(preset_commands, "record_preset_archived", boom)
    with pytest.raises(RuntimeError):
        with session.begin_nested():
            revise(session, first.preset_id, "Другое", c)
    with pytest.raises(RuntimeError):
        with session.begin_nested():
            archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES,
                           idempotency_key=key(), actor_uid=ADMIN)
    assert rows(session) == 1


@pytest.mark.parametrize("roles", [frozenset(), frozenset({"expert"}), frozenset({"reviewer"})])
def test_only_an_administrator_writes_a_preset(session, roles) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    before = rows(session)
    with pytest.raises(DomainError) as denied:
        create_preset(session, name="Иной", executor_connection_id=c, roles=roles,
                      idempotency_key=key(), actor_uid=ADMIN)
    expect(denied, ErrorCode.PERMISSION_DENIED, required_capability="role:admin")
    with pytest.raises(DomainError) as denied:
        revise_preset(session, preset_id=first.preset_id, name="Иной", executor_connection_id=c,
                      roles=roles, idempotency_key=key(), actor_uid=ADMIN)
    expect(denied, ErrorCode.PERMISSION_DENIED, required_capability="role:admin")
    with pytest.raises(DomainError) as denied:
        archive_preset(session, preset_id=first.preset_id, roles=roles, idempotency_key=key(),
                       actor_uid=ADMIN)
    expect(denied, ErrorCode.PERMISSION_DENIED, required_capability="role:admin")
    assert rows(session) == before  # not even a receipt: the role is read before the key is claimed


def test_an_expert_who_is_also_an_administrator_may_write(session) -> None:
    c = connection(session)
    assert create_preset(session, name="Ок", executor_connection_id=c,
                         roles=frozenset({"expert", "admin"}), idempotency_key=key(),
                         actor_uid=ADMIN).revision_no == 1


@pytest.mark.parametrize(
    ("name", "constraint"),
    [("", "required"), ("   ", "required"), ("Ж" * 121, "max_length"), ("А\tБ", "printable"), (7, "type")],
)
def test_a_bad_name_is_refused_on_the_field_and_writes_nothing(session, name, constraint) -> None:
    c = connection(session)
    with pytest.raises(DomainError) as bad:
        make(session, name, c)
    expect(bad, ErrorCode.VALIDATION_FAILED, field="name", constraint=constraint)
    assert rows(session) == 0


def test_an_unknown_connection_is_refused_on_its_field(session) -> None:
    with pytest.raises(DomainError) as bad:
        make(session, "Основной", "exc_01M2545JSD15ETSNNV904XD001")
    expect(bad, ErrorCode.VALIDATION_FAILED, field="executor_connection_id", constraint="unknown_connection")
    assert rows(session) == 0


def test_an_archived_connection_is_a_conflict_and_writes_nothing(session) -> None:
    c = connection(session)
    archive_connection(session, connection_id=c, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    with pytest.raises(DomainError) as bad:
        make(session, "Основной", c)
    expect(bad, ErrorCode.CONFLICT, conflict_reason="connection_archived")
    assert rows(session) == 0


def test_a_taken_name_is_a_conflict_without_regard_to_case(session) -> None:
    c = connection(session)
    make(session, "Чертежи", c)
    for name in ("Чертежи", "чертежи", "ЧЕРТЕЖИ"):
        with pytest.raises(DomainError) as taken:
            make(session, name, c)
        expect(taken, ErrorCode.CONFLICT, conflict_reason="preset_name_in_use", aggregate_type="AnalysisPreset")
    assert rows(session) == 1


def test_an_archive_frees_the_name(session) -> None:
    c = connection(session)
    first = make(session, "Чертежи", c)
    archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=key(),
                   actor_uid=ADMIN)
    assert make(session, "чертежи", c).revision_no == 1


def test_the_hundred_and_first_preset_is_a_conflict(session) -> None:
    c = connection(session)
    for number in range(100):
        make(session, f"Пресет {number:03d}", c)
    with pytest.raises(DomainError) as full:
        make(session, "Лишний", c)
    expect(full, ErrorCode.CONFLICT, conflict_reason="preset_limit_reached")
    assert rows(session) == 100


# -- idempotency --------------------------------------------------------------------------------


def test_the_same_key_and_payload_replays_the_first_answer_and_writes_nothing(session) -> None:
    c = connection(session)
    k = key()
    first = make(session, "Основной", c, idempotency_key=k)
    again = make(session, "Основной", c, idempotency_key=k)
    assert again == first and rows(session) == 1
    events = session.execute(text(
        "SELECT count(*) FROM audit_event WHERE event_type = 'executor.preset_created'")).scalar_one()
    assert events == 1


def test_a_replay_answers_the_revision_the_command_wrote_not_a_later_one(session) -> None:
    c = connection(session)
    k = key()
    first = make(session, "Основной", c, idempotency_key=k)
    revise(session, first.preset_id, "Другое имя", c)
    assert make(session, "Основной", c, idempotency_key=k) == first


def test_the_same_key_with_another_payload_is_a_reuse_conflict(session) -> None:
    c = connection(session)
    k = key()
    make(session, "Основной", c, idempotency_key=k)
    with pytest.raises(DomainError) as reuse:
        make(session, "Другое", c, idempotency_key=k)
    expect(reuse, ErrorCode.IDEMPOTENCY_KEY_REUSE)
    assert rows(session) == 1


OTHER_ADMIN = "usr_01M2545JSD15ETSNNV904XH0A2"


def test_a_second_administrator_reusing_a_create_key_does_not_get_the_first_ones_preset(session) -> None:
    """The key belongs to the actor who spent it, as in the comparison commands
    (`pairing.py`, `summaries.py`): the same key and the same payload from another administrator is a
    reuse conflict, never a replay of somebody else's answer, and writes nothing."""
    c = connection(session)
    k = key()
    first = make(session, "Основной", c, idempotency_key=k)
    with pytest.raises(DomainError) as reuse:
        create_preset(
            session, name="Основной", executor_connection_id=c, roles=ADMIN_ROLES,
            idempotency_key=k, actor_uid=OTHER_ADMIN,
        )
    expect(reuse, ErrorCode.IDEMPOTENCY_KEY_REUSE)
    assert rows(session) == 1
    # the first administrator's own retry is still a replay
    assert make(session, "Основной", c, idempotency_key=k) == first


def test_a_second_administrator_reusing_a_revise_key_does_not_get_the_first_ones_revision(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    k = key()
    revised = revise(session, first.preset_id, "Другое имя", c, idempotency_key=k)
    with pytest.raises(DomainError) as reuse:
        revise_preset(
            session, preset_id=first.preset_id, name="Другое имя", executor_connection_id=c,
            roles=ADMIN_ROLES, idempotency_key=k, actor_uid=OTHER_ADMIN,
        )
    expect(reuse, ErrorCode.IDEMPOTENCY_KEY_REUSE)
    assert rows(session) == 2
    assert revise(session, first.preset_id, "Другое имя", c, idempotency_key=k) == revised


def test_a_second_administrator_reusing_an_archive_key_does_not_get_the_first_ones_archive(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    k = key()
    archived = archive_preset(
        session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=k, actor_uid=ADMIN,
    )
    with pytest.raises(DomainError) as reuse:
        archive_preset(
            session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=k,
            actor_uid=OTHER_ADMIN,
        )
    expect(reuse, ErrorCode.IDEMPOTENCY_KEY_REUSE)
    assert rows(session) == 2
    assert archive_preset(
        session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=k, actor_uid=ADMIN,
    ) == archived


# -- revise -------------------------------------------------------------------------------------


def test_a_revision_is_a_new_row_under_the_same_preset(session) -> None:
    c, d = connection(session, "один"), connection(session, "два")
    first = make(session, "Основной", c)
    second = revise(session, first.preset_id, "Основной, на втором", d)
    assert (second.preset_id, second.revision_no, second.state) == (first.preset_id, 2, "active")
    assert second.revision_id != first.revision_id and second.executor_connection_id == d
    assert second.created_at == first.created_at and second.revised_at >= first.revised_at
    # the old revision is still what it was
    assert PresetStore().revision(session, first.revision_id) == first
    assert rows(session) == 2
    (current,) = list_presets(session)
    assert current == second
    event = session.execute(text(
        "SELECT event_type, aggregate_id FROM audit_event WHERE audit_event_id = :id"),
        {"id": second.revision_id}).one()
    assert tuple(event) == ("executor.preset_revised", first.preset_id)


def test_a_revision_that_changes_nothing_is_refused(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    with pytest.raises(DomainError) as same:
        revise(session, first.preset_id, " Основной ", c)
    expect(same, ErrorCode.VALIDATION_FAILED, field="name", constraint="differs_from_current")
    assert rows(session) == 1


def test_a_preset_may_keep_its_name_and_change_only_its_connection(session) -> None:
    c, d = connection(session, "один"), connection(session, "два")
    first = make(session, "Основной", c)
    assert revise(session, first.preset_id, "Основной", d).revision_no == 2


def test_a_revision_may_not_take_another_presets_name(session) -> None:
    c = connection(session)
    make(session, "Чертежи", c)
    other = make(session, "Текст", c)
    with pytest.raises(DomainError) as taken:
        revise(session, other.preset_id, "чертежи", c)
    expect(taken, ErrorCode.CONFLICT, conflict_reason="preset_name_in_use")
    assert rows(session) == 2


def test_an_unknown_preset_is_not_found_for_a_revision_and_an_archive(session) -> None:
    c = connection(session)
    ghost = "evt_01M2545JSD15ETSNNV904XD001"
    with pytest.raises(DomainError) as missing:
        revise(session, ghost, "Имя", c)
    expect(missing, ErrorCode.NOT_FOUND, aggregate_type="AnalysisPreset")
    with pytest.raises(DomainError) as missing:
        archive_preset(session, preset_id=ghost, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    expect(missing, ErrorCode.NOT_FOUND, aggregate_type="AnalysisPreset")


def test_a_revision_to_an_archived_connection_is_refused(session) -> None:
    c, d = connection(session, "один"), connection(session, "два")
    first = make(session, "Основной", c)
    archive_connection(session, connection_id=d, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    with pytest.raises(DomainError) as bad:
        revise(session, first.preset_id, "Основной", d)
    expect(bad, ErrorCode.CONFLICT, conflict_reason="connection_archived")


# -- archive ------------------------------------------------------------------------------------


def test_an_archive_is_a_new_revision_that_repeats_the_name_and_the_connection(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    archived = archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=key(),
                              actor_uid=ADMIN)
    assert (archived.revision_no, archived.state) == (2, "archived")
    assert (archived.name, archived.executor_connection_id) == (first.name, c)
    assert rows(session) == 2 and PresetStore().revision(session, first.revision_id).state == "active"
    event = session.execute(text("SELECT event_type FROM audit_event WHERE audit_event_id = :id"),
                            {"id": archived.revision_id}).scalar_one()
    assert event == "executor.preset_archived"


def test_nothing_follows_an_archive(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    with pytest.raises(DomainError) as again:
        archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=key(),
                       actor_uid=ADMIN)
    expect(again, ErrorCode.CONFLICT, conflict_reason="preset_archived")
    with pytest.raises(DomainError) as revised:
        revise(session, first.preset_id, "Новое", c)
    expect(revised, ErrorCode.CONFLICT, conflict_reason="preset_archived")
    assert rows(session) == 2


def test_a_preset_whose_connection_was_archived_can_still_be_archived(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    archive_connection(session, connection_id=c, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    assert archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=key(),
                          actor_uid=ADMIN).state == "archived"


# -- the list, the choice and the record of a run -------------------------------------------------


def test_the_list_is_active_first_by_name_then_archived(session) -> None:
    c = connection(session)
    b = make(session, "Б второй", c)
    a = make(session, "а первый", c)
    z = make(session, "Я архивный", c)
    archive_preset(session, preset_id=z.preset_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    assert [(p.name, p.state) for p in list_presets(session)] == [
        ("а первый", "active"), ("Б второй", "active"), ("Я архивный", "archived")]
    assert {a.preset_id, b.preset_id} <= {p.preset_id for p in list_presets(session)}


def test_a_run_start_takes_the_current_revision(session) -> None:
    c, d = connection(session, "один"), connection(session, "два")
    first = make(session, "Основной", c)
    chosen = choose_preset(session, first.preset_id)
    assert (chosen.preset_id, chosen.revision_id, chosen.revision_no, chosen.executor_connection_id) == (
        first.preset_id, first.revision_id, 1, c)
    second = revise(session, first.preset_id, "Основной", d)
    chosen = choose_preset(session, first.preset_id)
    assert (chosen.revision_id, chosen.revision_no, chosen.executor_connection_id) == (second.revision_id, 2, d)


def test_an_unknown_preset_cannot_be_chosen(session) -> None:
    with pytest.raises(DomainError) as unknown:
        choose_preset(session, "evt_01M2545JSD15ETSNNV904XD001")
    expect(unknown, ErrorCode.VALIDATION_FAILED, field="preset_id", constraint="unknown_preset")


def test_an_archived_preset_cannot_be_chosen(session) -> None:
    c = connection(session)
    first = make(session, "Основной", c)
    archive_preset(session, preset_id=first.preset_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    with pytest.raises(DomainError) as archived:
        choose_preset(session, first.preset_id)
    expect(archived, ErrorCode.CONFLICT, conflict_reason="preset_archived")


def test_a_recorded_revision_keeps_the_name_it_had(session) -> None:
    c = connection(session)
    first = make(session, "Старое имя", c)
    revise(session, first.preset_id, "Новое имя", c)
    kept = preset_of_revision(session, first.revision_id)
    assert (kept.preset_id, kept.revision_no, kept.name) == (first.preset_id, 1, "Старое имя")
    assert preset_of_revision(session, "evt_01M2545JSD15ETSNNV904XD001") is None
