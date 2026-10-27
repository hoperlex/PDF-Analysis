"""`COMPARE-PERSISTED-SUMMARY-01`: the comparison journal keeps ids and digests, nothing else."""

from __future__ import annotations

import pytest

from auditmanager.comparison import audit

CMP = "cmp_01M2545JSD15ETSNNV904XD001"
LINK = "sln_01M2545JSD15ETSNNV904XD001"
V1 = "ver_01M2545JSD15ETSNNV904XD001"
V2 = "ver_01M2545JSD15ETSNNV904XD002"
USER = "usr_01M2545JSD15ETSNNV904XD001"
SEAL = "a" * 64


def _payload(**changes):
    return {
        "comparison_id": CMP, "sheet_link_id": LINK, "link_revision": 1,
        "source_version_uid": V1, "target_version_uid": V2, "source_page_number": 1,
        "target_page_number": 2, "actor_uid": USER, "raw_evidence_seal_sha256": SEAL,
    } | changes


SUMMARY = "evt_01M2545JSD15ETSNNV904XD001"


def _summary_payload(**changes):
    return {
        "comparison_id": CMP, "link_revision": 2, "summary_id": SUMMARY, "input_sha256": "b" * 64,
        "raw_evidence_seal_sha256": SEAL, "state": "ready", "actor_uid": USER,
    } | changes


def test_the_summary_event_keeps_ids_digests_and_a_state_and_never_the_text() -> None:
    assert audit.validated(audit.EVENT_SUMMARY_GENERATED, _summary_payload()) == _summary_payload()
    for key in ("text", "statements", "model_identity", "cost_micros"):
        with pytest.raises(ValueError, match="non-allowlisted"):
            audit.validated(audit.EVENT_SUMMARY_GENERATED, _summary_payload() | {key: "x"})
    for key, value in (("state", "done"), ("summary_id", CMP), ("input_sha256", "B" * 64), ("link_revision", 0)):
        with pytest.raises(ValueError):
            audit.validated(audit.EVENT_SUMMARY_GENERATED, _summary_payload() | {key: value})


def test_a_complete_payload_is_kept_as_it_is() -> None:
    assert audit.validated(audit.EVENT_SHEET_LINK_APPROVED, _payload()) == _payload()


def test_the_seal_may_be_absent_only_from_a_withdrawal() -> None:
    bare = {k: v for k, v in _payload().items() if k != "raw_evidence_seal_sha256"}
    assert audit.validated(audit.EVENT_SHEET_LINK_WITHDRAWN, bare) == bare
    with pytest.raises(ValueError, match="lacks"):
        audit.validated(audit.EVENT_SHEET_LINK_APPROVED, bare)


@pytest.mark.parametrize("key", ["actor_label", "page_text", "quote", "ip_address", "note"])
def test_a_key_outside_the_allow_list_is_refused(key) -> None:
    with pytest.raises(ValueError, match="non-allowlisted"):
        audit.validated(audit.EVENT_SHEET_LINK_APPROVED, _payload() | {key: "Иванов"})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("comparison_id", "cmp_x"), ("comparison_id", LINK), ("sheet_link_id", CMP),
        ("actor_uid", "ivanov"), ("source_version_uid", USER),
        ("link_revision", 0), ("link_revision", True), ("source_page_number", 501),
        ("target_page_number", 0), ("raw_evidence_seal_sha256", "A" * 64),
        ("raw_evidence_seal_sha256", "a" * 63),
    ],
)
def test_a_value_that_is_not_what_its_key_says_is_refused(key, value) -> None:
    with pytest.raises(ValueError):
        audit.validated(audit.EVENT_SHEET_LINK_APPROVED, _payload() | {key: value})


class _RecordingSession:
    """A session that only remembers what was executed on it."""

    def __init__(self) -> None:
        self.executed: list[dict[str, object]] = []

    def execute(self, statement, parameters) -> None:  # noqa: ANN001  (the SQLAlchemy signature)
        self.executed.append(dict(parameters))


def _approve(session, correlation_id) -> None:
    audit.record_sheet_link_approved(
        session, comparison_id=CMP, sheet_link_id=LINK, link_revision=1, source_version_uid=V1,
        target_version_uid=V2, source_page_number=1, target_page_number=2, actor_uid=USER,
        raw_evidence_seal_sha256=SEAL, correlation_id=correlation_id,
    )


def test_the_request_correlation_id_rides_the_event_exactly_as_given() -> None:
    session = _RecordingSession()
    _approve(session, "req-0123456789abcdef")
    (written,) = session.executed
    assert written["correlation_id"] == "req-0123456789abcdef"
    assert written["aggregate_id"] == CMP and written["event_type"] == audit.EVENT_SHEET_LINK_APPROVED


def test_no_correlation_id_is_left_unbound_and_a_malformed_one_writes_nothing() -> None:
    session = _RecordingSession()
    _approve(session, None)
    assert session.executed[0]["correlation_id"] is None
    refused = _RecordingSession()
    for malformed in ("", " leading", "x" * 129, "has space"):
        with pytest.raises(ValueError):
            _approve(refused, malformed)
    assert refused.executed == []
