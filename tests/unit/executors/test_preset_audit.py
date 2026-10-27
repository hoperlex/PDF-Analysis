"""`ANALYSIS-PRESETS-01`: the preset journal keeps identities and a number, and never the name."""

from __future__ import annotations

import json

import pytest

from auditmanager.executors import preset_audit as audit

PRESET = "evt_01M2545JSD15ETSNNV904XD001"
REVISION = "evt_01M2545JSD15ETSNNV904XD002"
CONNECTION = "exc_01M2545JSD15ETSNNV904XD001"
USER = "usr_01M2545JSD15ETSNNV904XD001"
CORRELATION = "req-0123456789abcdef"


def _payload(**changes):
    return {
        "preset_id": PRESET, "revision_id": REVISION, "revision_no": 2,
        "executor_connection_id": CONNECTION, "actor_uid": USER,
    } | changes


class _RecordingSession:
    """A session that only remembers what was executed on it."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, statement, parameters=None):
        self.calls.append(dict(parameters or {}))


def test_the_three_event_types_are_in_the_executor_family_the_purge_keeps() -> None:
    assert audit.PRESET_EVENT_TYPES == (
        "executor.preset_created", "executor.preset_revised", "executor.preset_archived")
    assert all(event.startswith("executor.") for event in audit.PRESET_EVENT_TYPES)


@pytest.mark.parametrize("event_type", audit.PRESET_EVENT_TYPES)
def test_a_complete_payload_is_kept_as_it_is(event_type: str) -> None:
    assert audit.validated(event_type, _payload()) == _payload()


@pytest.mark.parametrize("key", ["name", "preset_name", "label", "state", "ip_address", "note"])
def test_a_key_outside_the_allow_list_is_refused_and_the_name_is_one_of_them(key: str) -> None:
    with pytest.raises(ValueError, match="non-allowlisted"):
        audit.validated("executor.preset_created", _payload() | {key: "Чертежи"})


@pytest.mark.parametrize("key", sorted(_payload()))
def test_every_key_is_required(key: str) -> None:
    payload = _payload()
    del payload[key]
    with pytest.raises(ValueError, match="lacks"):
        audit.validated("executor.preset_revised", payload)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("preset_id", "evt_x"), ("preset_id", CONNECTION), ("revision_id", USER),
        ("executor_connection_id", PRESET), ("executor_connection_id", "exc_x"),
        ("actor_uid", "ivanov"), ("actor_uid", PRESET), ("revision_no", 0), ("revision_no", True),
        ("revision_no", "2"),
    ],
)
def test_a_value_that_is_not_what_its_key_says_is_refused(key: str, value: object) -> None:
    with pytest.raises(ValueError):
        audit.validated("executor.preset_created", _payload() | {key: value})


def test_the_event_is_inserted_on_the_callers_session_with_the_revisions_id() -> None:
    session = _RecordingSession()
    audit.record_preset_revised(
        session, preset_id=PRESET, revision_id=REVISION, revision_no=2,
        executor_connection_id=CONNECTION, actor_uid=USER, correlation_id=CORRELATION,
    )
    (call,) = session.calls
    assert call["event_id"] == REVISION  # one id: the row and its event
    assert call["event_type"] == "executor.preset_revised"
    assert call["aggregate_type"] == "AnalysisPreset" and call["aggregate_id"] == PRESET
    assert call["correlation_id"] == CORRELATION
    assert json.loads(call["payload"]) == _payload()


def test_no_correlation_id_is_left_unbound_and_a_malformed_one_writes_nothing() -> None:
    session = _RecordingSession()
    audit.record_preset_created(
        session, preset_id=PRESET, revision_id=REVISION, revision_no=1,
        executor_connection_id=CONNECTION, actor_uid=USER, correlation_id=None,
    )
    assert session.calls[0]["correlation_id"] is None
    refused = _RecordingSession()
    for malformed in ("", " leading", "x" * 129, "has space"):
        with pytest.raises(ValueError):
            audit.record_preset_created(
                refused, preset_id=PRESET, revision_id=REVISION, revision_no=1,
                executor_connection_id=CONNECTION, actor_uid=USER, correlation_id=malformed,
            )
    assert refused.calls == []


def test_a_bad_payload_writes_nothing() -> None:
    session = _RecordingSession()
    with pytest.raises(ValueError):
        audit.record_preset_archived(
            session, preset_id=PRESET, revision_id=REVISION, revision_no=0,
            executor_connection_id=CONNECTION, actor_uid=USER, correlation_id=None,
        )
    assert session.calls == []
