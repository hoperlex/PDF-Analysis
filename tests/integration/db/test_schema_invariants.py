"""Every database-level guard in the P02 head, proved able to fail.

A constraint nobody has watched refuse anything is a comment with a syntax error
budget. Each test here performs the write the guard exists to stop and asserts the
refusal, its SQLSTATE and - where the contract fixes it - the reported code.

The mirror-image assertions matter as much: the *declared* transitions succeed, so
these tests cannot pass by refusing everything.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from auditmanager.shared.db.schema import (
    SQLSTATE_APPEND_ONLY_VIOLATION,
    SQLSTATE_IMMUTABLE_ROW_VIOLATION,
    SQLSTATE_TO_CATALOG_CODE,
    SQLSTATE_UNDECLARED_TRANSITION,
)
from auditmanager.shared.db.session import create_session_factory, session_scope
from auditmanager.shared.identity import (
    AnalysisProfileId,
    BlobId,
    CommandId,
    DecisionId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64

# Passed as bind parameters, never inlined into the statement: ``text()`` reads a
# bare ``:true`` inside a JSON literal as a bind parameter, and the statement then
# fails for a reason that has nothing to do with the constraint under test.
NON_RETRYABLE_ERROR = '{"code": "analysis_failed", "message": "x", "retryable": false}'
RETRYABLE_ERROR = '{"code": "out_of_scope", "message": "x", "retryable": true}'


def sqlstate_of(error: DBAPIError) -> str:
    """The five-character SQLSTATE the server reported."""
    return str(getattr(error.orig, "sqlstate", "") or "")


@pytest.fixture
def session(migrated_engine: Engine):
    factory = create_session_factory(migrated_engine)
    with session_scope(factory) as active:
        yield active


class Fixture:
    """A minimal published journey: project, document, version, blob, manifest, run."""

    def __init__(self, session: Session) -> None:
        self.project_uid = str(ProjectUid.new())
        self.document_uid = str(DocumentUid.new())
        self.version_uid = str(VersionUid.new())
        self.blob_id = str(BlobId.new())
        self.run_id = str(RunId.new())
        self.session = session

        session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:uid, 'AR review')"),
            {"uid": self.project_uid},
        )
        session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:doc, :prj, 'AR-1')"
            ),
            {"doc": self.document_uid, "prj": self.project_uid},
        )
        session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": self.blob_id})
        session.execute(
            text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": self.blob_id}
        )
        session.execute(
            text(
                "UPDATE blob SET state = 'available', sha256 = :d, size_bytes = 1024, "
                "media_type = 'application/pdf' WHERE blob_id = :b"
            ),
            {"b": self.blob_id, "d": DIGEST_A},
        )
        session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:ver, :doc, 1, 'application/pdf', 1024, :d, 12)"
            ),
            {"ver": self.version_uid, "doc": self.document_uid, "d": DIGEST_A},
        )
        session.execute(
            text(
                "INSERT INTO input_manifest_entry "
                "(version_uid, role, blob_id, sha256, size_bytes, media_type) "
                "VALUES (:ver, 'source.document', :b, :d, 1024, 'application/pdf')"
            ),
            {"ver": self.version_uid, "b": self.blob_id, "d": DIGEST_A},
        )
        session.execute(
            text(
                "UPDATE document SET current_version_uid = :ver WHERE document_uid = :doc"
            ),
            {"ver": self.version_uid, "doc": self.document_uid},
        )
        session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:run, :prj, :ver, :ap, :pb, 'recorded', :d)"
            ),
            {
                "run": self.run_id,
                "prj": self.project_uid,
                "ver": self.version_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
                "d": DIGEST_B,
            },
        )
        session.flush()

    def advance_run_to(self, state: str) -> None:
        path = {
            "queued": ["queued"],
            "running": ["queued", "running"],
            "validating": ["queued", "running", "validating"],
            "published": ["queued", "running", "validating", "published"],
        }[state]
        for step in path:
            terminal = step in {"published", "partial", "failed", "cancelled"}
            self.session.execute(
                text(
                    "UPDATE audit_run SET state = :s, "
                    "terminal_at = CASE WHEN :terminal THEN now() ELSE NULL END "
                    "WHERE run_id = :run"
                ),
                {"s": step, "run": self.run_id, "terminal": terminal},
            )
            self.session.flush()

    def publish_finding(self) -> tuple[str, str]:
        finding_uid = str(FindingUid.new())
        observation_id = str(FindingObservationId.new())
        self.session.execute(
            text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, "
                "allocated_by_run_id, category) "
                "VALUES (:f, :prj, :ver, :run, 'internal_contradiction')"
            ),
            {
                "f": finding_uid,
                "prj": self.project_uid,
                "ver": self.version_uid,
                "run": self.run_id,
            },
        )
        self.session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, "
                "finding_uid, stage_id, category, finding_text, recommendation_text, "
                "grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
                "VALUES (:o, :run, :f, 'text_analysis', 'internal_contradiction', "
                "'Two fire-resistance classes', 'Reconcile the two statements', true, "
                ":ap, :pb, 'recorded')"
            ),
            {
                "o": observation_id,
                "run": self.run_id,
                "f": finding_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
            },
        )
        self.session.flush()
        return finding_uid, observation_id


@pytest.fixture
def journey(session: Session) -> Fixture:
    return Fixture(session)


# ---------------------------------------------------------------------------
# The declared topology is enforced, and the declared edges work.
# ---------------------------------------------------------------------------


def test_the_declared_run_path_to_published_is_permitted(journey: Fixture) -> None:
    journey.advance_run_to("published")
    state = journey.session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": journey.run_id}
    ).scalar_one()
    assert state == "published"


@pytest.mark.parametrize(
    ("reachable", "target"),
    [
        ("created", "running"),
        ("created", "validating"),
        ("created", "published"),
        ("queued", "validating"),
        ("queued", "published"),
        ("running", "published"),
        ("running", "queued"),
    ],
)
def test_an_undeclared_run_transition_is_refused(
    journey: Fixture, reachable: str, target: str
) -> None:
    if reachable != "created":
        journey.advance_run_to(reachable)
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(
            text("UPDATE audit_run SET state = :s WHERE run_id = :r"),
            {"s": target, "r": journey.run_id},
        )
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_UNDECLARED_TRANSITION
    assert "state_transition_not_allowed" in str(raised.value.orig)
    assert SQLSTATE_TO_CATALOG_CODE[SQLSTATE_UNDECLARED_TRANSITION] == (
        "state_transition_not_allowed"
    )


@pytest.mark.parametrize("target", ["running", "queued", "created", "validating"])
def test_a_terminal_run_is_never_reopened(journey: Fixture, target: str) -> None:
    """The contract's headline rule, and the one a reviewer will look for."""
    journey.advance_run_to("published")
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(
            text("UPDATE audit_run SET state = :s WHERE run_id = :r"),
            {"s": target, "r": journey.run_id},
        )
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_UNDECLARED_TRANSITION


def test_a_run_cannot_be_created_in_a_non_initial_state(journey: Fixture) -> None:
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest, state, terminal_at) "
                "VALUES (:run, :prj, :ver, :ap, :pb, 'recorded', :d, 'published', now())"
            ),
            {
                "run": str(RunId.new()),
                "prj": journey.project_uid,
                "ver": journey.version_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
                "d": DIGEST_B,
            },
        )
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_UNDECLARED_TRANSITION
    assert "may not be created in state" in str(raised.value.orig)


def test_an_undeclared_blob_transition_is_refused(journey: Fixture) -> None:
    """``temporary -> available`` skips verification, which is the whole point of it."""
    blob_id = str(BlobId.new())
    journey.session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob_id})
    journey.session.flush()
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(
            text(
                "UPDATE blob SET state = 'available', sha256 = :d, size_bytes = 1, "
                "media_type = 'application/pdf' WHERE blob_id = :b"
            ),
            {"b": blob_id, "d": DIGEST_B},
        )
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_UNDECLARED_TRANSITION


def test_verified_blob_metadata_is_write_once(journey: Fixture) -> None:
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(
            text("UPDATE blob SET sha256 = :d WHERE blob_id = :b"),
            {"b": journey.blob_id, "d": DIGEST_B},
        )
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_IMMUTABLE_ROW_VIOLATION


def test_the_declared_topology_itself_cannot_be_extended(session: Session) -> None:
    """Closes the bypass: declare the edge you want, then take it."""
    with pytest.raises(DBAPIError) as raised:
        session.execute(
            text(
                "INSERT INTO contract_state_transition (machine, from_state, to_state) "
                "VALUES ('audit_run', 'published', 'running')"
            )
        )
        session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_IMMUTABLE_ROW_VIOLATION


# ---------------------------------------------------------------------------
# Immutability of published input state and emitted evidence.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE document_version SET page_count = 13 WHERE version_uid = :ver",
        "DELETE FROM document_version WHERE version_uid = :ver",
        "UPDATE input_manifest_entry SET size_bytes = 2 WHERE version_uid = :ver",
        "DELETE FROM input_manifest_entry WHERE version_uid = :ver",
    ],
)
def test_a_published_version_and_its_manifest_are_immutable(
    journey: Fixture, statement: str
) -> None:
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(text(statement), {"ver": journey.version_uid})
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_IMMUTABLE_ROW_VIOLATION


def test_a_run_frozen_column_cannot_be_edited(journey: Fixture) -> None:
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(
            text("UPDATE audit_run SET analysis_profile_id = :ap WHERE run_id = :r"),
            {"ap": str(AnalysisProfileId.new()), "r": journey.run_id},
        )
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_IMMUTABLE_ROW_VIOLATION
    assert "frozen at creation" in str(raised.value.orig)


def test_a_run_may_still_record_its_progress(journey: Fixture) -> None:
    """The frozen guard must not freeze the whole row."""
    journey.advance_run_to("running")
    journey.session.execute(
        text("UPDATE audit_run SET updated_at = now() WHERE run_id = :r"),
        {"r": journey.run_id},
    )
    journey.session.flush()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE finding_observation SET finding_text = 'edited' "
        "WHERE finding_observation_id = :o",
        "DELETE FROM finding_observation WHERE finding_observation_id = :o",
    ],
)
def test_an_emitted_observation_is_immutable(journey: Fixture, statement: str) -> None:
    _, observation_id = journey.publish_finding()
    with pytest.raises(DBAPIError) as raised:
        journey.session.execute(text(statement), {"o": observation_id})
        journey.session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_IMMUTABLE_ROW_VIOLATION


# ---------------------------------------------------------------------------
# The append-only decision ledger.
# ---------------------------------------------------------------------------


def _append_decision(
    journey: Fixture, finding_uid: str, observation_id: str, event_type: str, comment: str | None
) -> str:
    verdict = {"accept": "accepted", "reject": "rejected", "revoke": "pending"}.get(event_type)
    decision_id = str(DecisionId.new())
    journey.session.execute(
        text(
            "INSERT INTO expert_decision_event (decision_id, finding_uid, "
            "finding_observation_id, event_type, verdict, comment, author_label) "
            "VALUES (:d, :f, :o, :t, :v, :c, 'local-reviewer')"
        ),
        {
            "d": decision_id,
            "f": finding_uid,
            "o": observation_id,
            "t": event_type,
            "v": verdict,
            "c": comment,
        },
    )
    journey.session.flush()
    return decision_id


def test_the_decision_ledger_refuses_update_and_delete(journey: Fixture) -> None:
    finding_uid, observation_id = journey.publish_finding()
    decision_id = _append_decision(journey, finding_uid, observation_id, "accept", None)

    for statement in (
        "UPDATE expert_decision_event SET verdict = 'rejected' WHERE decision_id = :d",
        "DELETE FROM expert_decision_event WHERE decision_id = :d",
    ):
        # A SAVEPOINT per attempt, so the refusal aborts its own subtransaction and
        # the second statement still runs against a live one.
        with pytest.raises(DBAPIError) as raised:
            with journey.session.begin_nested():
                journey.session.execute(text(statement), {"d": decision_id})
                journey.session.flush()
        assert sqlstate_of(raised.value) == SQLSTATE_APPEND_ONLY_VIOLATION
        assert "append-only ledger" in str(raised.value.orig)

    survived = journey.session.execute(
        text("SELECT verdict FROM expert_decision_event WHERE decision_id = :d"),
        {"d": decision_id},
    ).scalar_one()
    assert survived == "accepted", "the event neither changed nor disappeared"


def test_the_audit_trail_refuses_update_and_delete(session: Session) -> None:
    from auditmanager.shared.identity import AuditEventId

    event_id = str(AuditEventId.new())
    session.execute(
        text(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
            "aggregate_id) VALUES (:e, 'blob.reconciled', 'Blob', :a)"
        ),
        {"e": event_id, "a": str(BlobId.new())},
    )
    session.flush()
    with pytest.raises(DBAPIError) as raised:
        session.execute(
            text("DELETE FROM audit_event WHERE audit_event_id = :e"), {"e": event_id}
        )
        session.flush()
    assert sqlstate_of(raised.value) == SQLSTATE_APPEND_ONLY_VIOLATION


def test_accept_then_comment_then_reject_appends_three_events(journey: Fixture) -> None:
    """The PC-01 journey, and the projection that follows from it."""
    finding_uid, observation_id = journey.publish_finding()

    _append_decision(journey, finding_uid, observation_id, "accept", None)
    verdict = journey.session.execute(
        text("SELECT current_verdict FROM finding_current_verdict WHERE finding_uid = :f"),
        {"f": finding_uid},
    ).scalar_one()
    assert verdict == "accepted"

    _append_decision(journey, finding_uid, observation_id, "comment", "second thoughts")
    row = journey.session.execute(
        text(
            "SELECT current_verdict, latest_comment, decision_event_count "
            "FROM finding_current_verdict WHERE finding_uid = :f"
        ),
        {"f": finding_uid},
    ).one()
    assert row.current_verdict == "accepted", "a comment must not change the verdict"
    assert row.latest_comment == "second thoughts"
    assert row.decision_event_count == 2

    last = _append_decision(journey, finding_uid, observation_id, "reject", None)
    row = journey.session.execute(
        text(
            "SELECT current_verdict, latest_comment, latest_decision_id, "
            "decision_event_count FROM finding_current_verdict WHERE finding_uid = :f"
        ),
        {"f": finding_uid},
    ).one()
    assert row.current_verdict == "rejected"
    assert row.latest_comment == "second thoughts", "history is not overwritten"
    assert row.latest_decision_id == last
    assert row.decision_event_count == 3

    stored = journey.session.execute(
        text(
            "SELECT event_type FROM expert_decision_event WHERE finding_uid = :f "
            "ORDER BY sequence_no"
        ),
        {"f": finding_uid},
    ).scalars().all()
    assert stored == ["accept", "comment", "reject"]


def test_a_finding_with_no_events_projects_to_pending(journey: Fixture) -> None:
    finding_uid, _ = journey.publish_finding()
    verdict = journey.session.execute(
        text("SELECT current_verdict FROM finding_current_verdict WHERE finding_uid = :f"),
        {"f": finding_uid},
    ).scalar_one()
    assert verdict == "pending"


def test_a_revocation_moves_the_projection_to_pending(journey: Fixture) -> None:
    """PD-01: revocation never restores an earlier superseded verdict."""
    finding_uid, observation_id = journey.publish_finding()
    _append_decision(journey, finding_uid, observation_id, "accept", None)
    _append_decision(journey, finding_uid, observation_id, "reject", None)
    _append_decision(journey, finding_uid, observation_id, "revoke", None)
    verdict = journey.session.execute(
        text("SELECT current_verdict FROM finding_current_verdict WHERE finding_uid = :f"),
        {"f": finding_uid},
    ).scalar_one()
    assert verdict == "pending"


@pytest.mark.parametrize(
    ("event_type", "verdict", "comment"),
    [
        ("accept", "rejected", None),
        ("reject", "accepted", None),
        ("comment", "accepted", "text"),
        ("comment", None, None),
        ("revoke", "accepted", None),
        ("accept", None, None),
    ],
)
def test_an_incoherent_decision_event_is_refused(
    journey: Fixture, event_type: str, verdict: str | None, comment: str | None
) -> None:
    finding_uid, observation_id = journey.publish_finding()
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, comment, author_label) "
                "VALUES (:d, :f, :o, :t, :v, :c, 'local-reviewer')"
            ),
            {
                "d": str(DecisionId.new()),
                "f": finding_uid,
                "o": observation_id,
                "t": event_type,
                "v": verdict,
                "c": comment,
            },
        )
        journey.session.flush()


def test_one_command_record_appends_at_most_one_decision_event(journey: Fixture) -> None:
    """Replaying a decision command under one key appends exactly one event."""
    finding_uid, observation_id = journey.publish_finding()
    command_id = str(CommandId.new())
    journey.session.execute(
        text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, "
            "payload_fingerprint, state, outcome) "
            "VALUES (:c, 'append_decision', 'key-1', :d, 'in_progress', NULL)"
        ),
        {"c": command_id, "d": DIGEST_A},
    )
    journey.session.flush()
    for _ in range(1):
        journey.session.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, author_label, command_id) "
                "VALUES (:d, :f, :o, 'accept', 'accepted', 'local-reviewer', :c)"
            ),
            {
                "d": str(DecisionId.new()),
                "f": finding_uid,
                "o": observation_id,
                "c": command_id,
            },
        )
        journey.session.flush()
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, author_label, command_id) "
                "VALUES (:d, :f, :o, 'accept', 'accepted', 'local-reviewer', :c)"
            ),
            {
                "d": str(DecisionId.new()),
                "f": finding_uid,
                "o": observation_id,
                "c": command_id,
            },
        )
        journey.session.flush()


# ---------------------------------------------------------------------------
# Identity, idempotency and the StageResult fail-closed rule.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("statement", "parameters"),
    [
        (
            "INSERT INTO project (project_uid, name) VALUES (:v, 'x')",
            {"v": "doc_01M2545JSD15ETSNNV904X991S"},
        ),
        (
            "INSERT INTO project (project_uid, name) VALUES (:v, 'x')",
            {"v": "prj_notaulidatall"},
        ),
        (
            "INSERT INTO project (project_uid, name) VALUES (:v, 'x')",
            {"v": "prj_01M2545JSD15ETSNNV904X99IL"},  # I and L are not in the alphabet
        ),
        (
            "INSERT INTO project (project_uid, name) VALUES (:v, 'x')",
            {"v": "/var/lib/projects/ar-1"},
        ),
    ],
)
def test_a_malformed_identifier_is_refused_by_the_database(
    session: Session, statement: str, parameters: dict[str, str]
) -> None:
    """The value type rejects these too; this proves raw SQL cannot slip past it."""
    with pytest.raises(IntegrityError):
        session.execute(text(statement), parameters)
        session.flush()


def test_a_command_key_is_unique_per_command_type(session: Session) -> None:
    for command_type, key, should_conflict in (
        ("start_run", "key-a", False),
        ("upload_document", "key-a", False),  # same key, different command type: fine
        ("start_run", "key-a", True),
    ):
        statement = text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, "
            "payload_fingerprint) VALUES (:c, :t, :k, :d)"
        )
        parameters = {
            "c": str(CommandId.new()),
            "t": command_type,
            "k": key,
            "d": DIGEST_A,
        }
        if should_conflict:
            with pytest.raises(IntegrityError):
                session.execute(statement, parameters)
                session.flush()
        else:
            session.execute(statement, parameters)
            session.flush()


def test_available_blob_content_is_unique_by_checksum_and_size(session: Session) -> None:
    for _ in range(2):
        blob_id = str(BlobId.new())
        session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob_id})
        session.execute(
            text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob_id}
        )
        session.flush()
        statement = text(
            "UPDATE blob SET state = 'available', sha256 = :d, size_bytes = 7, "
            "media_type = 'application/pdf' WHERE blob_id = :b"
        )
        if _ == 0:
            session.execute(statement, {"b": blob_id, "d": DIGEST_B})
            session.flush()
        else:
            with pytest.raises(IntegrityError):
                session.execute(statement, {"b": blob_id, "d": DIGEST_B})
                session.flush()


def test_a_succeeded_stage_result_may_not_carry_an_error(journey: Fixture) -> None:
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO stage_result (run_id, stage_id, stage_version, status, error) "
                "VALUES (:r, 'source_preparation', '1.0.0', 'succeeded', CAST(:e AS jsonb))"
            ),
            {"r": journey.run_id, "e": NON_RETRYABLE_ERROR},
        )
        journey.session.flush()


@pytest.mark.parametrize("status", ["failed", "partial", "skipped"])
def test_a_non_succeeded_stage_result_requires_an_error(
    journey: Fixture, status: str
) -> None:
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO stage_result (run_id, stage_id, stage_version, status) "
                "VALUES (:r, 'text_analysis', '1.0.0', :s)"
            ),
            {"r": journey.run_id, "s": status},
        )
        journey.session.flush()


def test_a_skipped_stage_result_is_empty_and_not_retryable(journey: Fixture) -> None:
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO stage_result (run_id, stage_id, stage_version, status, error) "
                "VALUES (:r, 'block_analysis', '1.0.0', 'skipped', CAST(:e AS jsonb))"
            ),
            {"r": journey.run_id, "e": RETRYABLE_ERROR},
        )
        journey.session.flush()


def test_a_published_run_may_not_carry_a_degradation_set(journey: Fixture) -> None:
    journey.advance_run_to("validating")
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "UPDATE audit_run SET state = 'published', terminal_at = now(), "
                "degradation_set = CAST(:g AS jsonb) WHERE run_id = :r"
            ),
            {"r": journey.run_id, "g": '["text_analysis"]'},
        )
        journey.session.flush()


def test_a_partial_run_must_record_its_degradation_set(journey: Fixture) -> None:
    journey.advance_run_to("validating")
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "UPDATE audit_run SET state = 'partial', terminal_at = now() WHERE run_id = :r"
            ),
            {"r": journey.run_id},
        )
        journey.session.flush()


def test_an_ungrounded_observation_carries_no_finding(journey: Fixture) -> None:
    """The grounding gate's structural consequence, both ways round."""
    observation_id = str(FindingObservationId.new())
    journey.session.execute(
        text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, "
            "stage_id, category, finding_text, recommendation_text, grounded, "
            "ungrounded_reason, analysis_profile_id, prompt_bundle_id, provider_mode) "
            "VALUES (:o, :run, NULL, 'text_analysis', 'explicit_placeholder', 'TBD found', "
            "'Complete the field', false, 'quotation_absent', :ap, :pb, 'recorded')"
        ),
        {
            "o": observation_id,
            "run": journey.run_id,
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
        },
    )
    journey.session.flush()

    finding_uid, _ = journey.publish_finding()
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, "
                "finding_uid, stage_id, category, finding_text, recommendation_text, "
                "grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
                "provider_mode) VALUES (:o, :run, :f, 'text_analysis', "
                "'explicit_placeholder', 'x', 'y', false, 'quotation_absent', :ap, :pb, "
                "'recorded')"
            ),
            {
                "o": str(FindingObservationId.new()),
                "run": journey.run_id,
                "f": finding_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
            },
        )
        journey.session.flush()


def test_an_evidence_span_must_match_the_quotation_length(journey: Fixture) -> None:
    _, observation_id = journey.publish_finding()
    journey.session.execute(
        text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
            "page_number, quote, char_start, char_end, block_id) "
            "VALUES (:o, 0, 4, :q, 100, :end, 'b_000042')"
        ),
        {"o": observation_id, "q": "класс огнестойкости II", "end": 100 + len("класс огнестойкости II")},
    )
    journey.session.flush()
    with pytest.raises(IntegrityError):
        journey.session.execute(
            text(
                "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
                "page_number, quote, char_start, char_end) "
                "VALUES (:o, 1, 4, 'класс огнестойкости III', 200, 210)"
            ),
            {"o": observation_id},
        )
        journey.session.flush()
