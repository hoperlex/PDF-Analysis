"""`PROD-06`: what an ``access.*`` payload may hold -- the writer's allow-list, with no database.

ADR-0023 section 4, commitment 6: every key an ``access.*`` event writes is in the writer's
allow-list and every value is a scalar. The writer (``auditmanager.access.audit``) enforces three
independent things, and each has cases here:

* a key outside the event type's allow-list is refused before any INSERT;
* a required key cannot be left out;
* a value outside the key's closed rule is refused under an allowed key, so a token or an
  address cannot be smuggled in as a "subject".

The stored-rows half (a scan of what the served operations actually wrote) is
``tests/integration/access/test_access_audit.py``.
"""

from __future__ import annotations

import pytest

from auditmanager.access import audit
from auditmanager.shared.identity.errors import IdentifierFormatError

USER_A = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
USER_B = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAB"

GOOD: dict[str, dict[str, object]] = {
    "access.sign_in_succeeded": {"subject_uid": USER_A, "source": "api", "default_credential": False},
    "access.sign_in_blocked": {"subject_uid": USER_A, "source": "api", "failures": 5},
    "access.role_granted": {"subject_uid": USER_A, "role": "admin", "source": "host_cli"},
    "access.role_revoked": {"subject_uid": USER_A, "actor_uid": USER_B, "role": "expert", "source": "api"},
    "access.password_changed": {"subject_uid": USER_A, "actor_uid": USER_A, "source": "api"},
    "access.password_reset": {"subject_uid": USER_A, "actor_uid": USER_B, "source": "api"},
    "access.sessions_ended": {"subject_uid": USER_A, "actor_uid": USER_B, "source": "api"},
}


class TestThePayloadAllowList:
    def test_the_first_six_types_are_adr_0023_section_4_and_the_seventh_is_contract_1_36_0(self) -> None:
        assert audit.ACCESS_EVENT_TYPES == (
            "access.sign_in_succeeded", "access.sign_in_blocked", "access.role_granted",
            "access.role_revoked", "access.password_changed", "access.password_reset",
            "access.sessions_ended")
        assert set(GOOD) == set(audit.ACCESS_EVENT_TYPES)

    @pytest.mark.parametrize("event_type", audit.ACCESS_EVENT_TYPES)
    def test_a_payload_of_exactly_the_documented_keys_is_accepted(self, event_type: str) -> None:
        assert audit._validated(event_type, GOOD[event_type]) == GOOD[event_type]

    @pytest.mark.parametrize("event_type", audit.ACCESS_EVENT_TYPES)
    @pytest.mark.parametrize(
        "extra", ["password", "token", "ip", "user_agent", "login", "email", "cookie", "hash", "name"]
    )
    def test_a_key_outside_the_allow_list_is_refused_before_any_insert(
        self, event_type: str, extra: str
    ) -> None:
        with pytest.raises(ValueError, match="non-allowlisted"):
            audit._validated(event_type, {**GOOD[event_type], extra: "x"})

    @pytest.mark.parametrize("event_type", audit.ACCESS_EVENT_TYPES)
    def test_a_required_key_cannot_be_left_out(self, event_type: str) -> None:
        required, _optional = audit.PAYLOAD_KEYS[event_type]
        for key in required:
            smaller = {k: v for k, v in GOOD[event_type].items() if k != key}
            with pytest.raises(ValueError, match="lacks"):
                audit._validated(event_type, smaller)

    def test_every_allowed_key_has_a_value_rule(self) -> None:
        keys = set().union(*(required | optional for required, optional in audit.PAYLOAD_KEYS.values()))
        assert keys == {"subject_uid", "actor_uid", "role", "source", "default_credential", "failures"}
        for event_type in audit.ACCESS_EVENT_TYPES:  # a rule exists, so none reaches the last branch
            audit._validated(event_type, GOOD[event_type])

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("subject_uid", "admin"),                    # a login is not an identity
            ("subject_uid", "ey.token.value"),           # nor is a token
            ("subject_uid", ["usr_01ARZ3NDEKTSV4RRFFQ69G5FAA"]),
            ("subject_uid", {"usr": USER_A}),
            ("source", "203.0.113.5"),                   # an address is not a source
            ("source", "api; curl/8"),
            ("role", "root"),
            ("role", "a@b.c"),
        ],
    )
    def test_a_value_outside_the_closed_vocabulary_is_refused_under_an_allowed_key(
        self, key: str, value: object
    ) -> None:
        with pytest.raises(ValueError):
            audit._validated("access.role_granted", {**GOOD["access.role_granted"], key: value})

    @pytest.mark.parametrize("value", [0, -1, True, "5", 5.5, [5], None])
    def test_the_count_is_a_positive_integer(self, value: object) -> None:
        with pytest.raises(ValueError):
            audit._validated("access.sign_in_blocked", {**GOOD["access.sign_in_blocked"], "failures": value})

    @pytest.mark.parametrize("value", [1, "true", None, [True]])
    def test_the_default_flag_is_a_boolean(self, value: object) -> None:
        with pytest.raises(ValueError):
            audit._validated(
                "access.sign_in_succeeded", {**GOOD["access.sign_in_succeeded"], "default_credential": value})


class TestTheCorrelationSeamRefusals:
    def test_an_id_the_column_would_refuse_is_refused_at_bind_time(self) -> None:
        for bad in ("", "has space", "-leading", "x" * 129):
            with pytest.raises(IdentifierFormatError):
                audit.bind_correlation_id(bad)


class TestTheJournalReadsWhatTheWriterAllows:
    """Contract 1.36.0: ``access.journal`` rebuilds a line from a stored payload; a field a type lacks is ``None``."""

    def test_a_row_becomes_a_line_with_the_facts_its_type_carries(self) -> None:
        from datetime import datetime, timezone

        from auditmanager.access.journal import AccessEvent, _event

        at = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
        assert _event(("evt_X", "access.role_granted", USER_A, at, {"subject_uid": USER_A, "role": "admin", "source": "host_cli"})) == AccessEvent(
            event_id="evt_X", event_type="access.role_granted", occurred_at=at, subject_uid=USER_A, actor_uid=None,
            source="host_cli", role="admin", failures=None, default_credential=None)
        assert _event(("evt_Y", "access.sign_in_blocked", USER_A, at, {"subject_uid": USER_A, "source": "api", "failures": 5})).failures == 5
        line = _event(("evt_Z", "access.sessions_ended", USER_A, at, GOOD["access.sessions_ended"]))
        assert (line.subject_uid, line.actor_uid, line.role, line.failures, line.default_credential) == (USER_A, USER_B, None, None, None)

    def test_the_subject_is_the_rows_aggregate_and_not_a_payload_claim(self) -> None:
        from datetime import datetime, timezone

        from auditmanager.access.journal import _event

        at = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
        assert _event(("evt_X", "access.password_changed", USER_B, at, GOOD["access.password_changed"])).subject_uid == USER_B
