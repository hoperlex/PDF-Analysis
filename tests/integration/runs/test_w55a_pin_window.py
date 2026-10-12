"""`W55A-PIN-01` on real PostgreSQL: runs and re-audits pin the current norms snapshot.

Plan `W55-PLAN.md` section A4 Stage B item 3 requires: a new run pins the current snapshot;
NULL when none, digest byte-identical; a retry after a change replays; a pre-W55 key
replays; a re-audit pins the current snapshot and its retry replays. Each is a test below,
and ``startRun``'s shipped adapter is driven once so ``RunStatus.norms_snapshot_id`` is
read back from the row the command wrote.

HEAVY: a window step (R-102, R-111, D-157), on the lane's PostgreSQL and S3 (the harness's
``seeded`` version puts its PDF in the bucket). Everything runs in the harness's rolled-back
transaction.

**Designation here is plain SQL, not ``setCurrentNormSnapshot``.** The setter admits only a
qualifying snapshot -- a complete ``bge-m3-dense-v1`` build and a confirmed custody binding
of every document's PDF -- and seeding both would test W54's loader, not the pin. The rows
below satisfy ``0020``'s guard exactly as the setter writes them: one history event from
the current snapshot (or from none) to the target, then the singleton row naming it. The
setter's own rules are proved by ``tests/integration/norms/search/test_current_snapshot_window.py``.

**"None current" is a precondition, not something a test can arrange**: there is no unset,
by design. The NULL cases fail loudly on a lane database where something committed a
designation; run them on a freshly migrated lane.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas.runs import run_status_body
from auditmanager.bootstrap.adapters import RunAdapter
from auditmanager.ingest.public import CommandRepository, payload_fingerprint
from auditmanager.norms.public import current_snapshot
from auditmanager.runs import COMMAND_TYPE_START_RUN, RunRepository
from auditmanager.runs.commands import (
    current_norms_snapshot,
    frozen_input_digest,
    input_basis_digest,
    reaudit_run,
    start_audit_run,
)
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import (
    AuditEventId,
    IdempotencyKey,
    NormsSnapshotId,
    RunId,
)
from auditmanager.shared.identity.ids import UserUid


def _key() -> str:
    return "w55a-pin-" + uuid4().hex


def _snapshot(session: Session) -> str:
    """One ``norms_snapshot`` row; nothing else is needed for a pin."""
    snapshot = str(NormsSnapshotId.new())
    key = f"w55a-pin-{snapshot[-12:].lower()}"
    session.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, segmentation_profile) "
        "VALUES (:s, :k, :k, :d, 0, 1, 'w55a-pin')"
    ), {"s": snapshot, "k": key, "d": "e" * 64})
    return snapshot


def _designate(session: Session, snapshot: str) -> None:
    """What ``set_current_snapshot`` writes, without its qualification (module docstring)."""
    before = current_snapshot(session)
    previous = None if before is None else str(before.norms_snapshot_id)
    event = str(AuditEventId.new())
    session.execute(text(
        "INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, to_snapshot_id, "
        "actor_user_uid) VALUES (:e, :f, :t, :a)"
    ), {"e": event, "f": previous, "t": snapshot, "a": str(UserUid.new())})
    if previous is None:
        session.execute(text(
            "INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) VALUES (:s, :e)"
        ), {"s": snapshot, "e": event})
    else:
        session.execute(text(
            "UPDATE norm_current_snapshot SET norms_snapshot_id = :s, event_id = :e"
        ), {"s": snapshot, "e": event})
    assert current_norms_snapshot(session) == snapshot


def _require_none_current(session: Session) -> None:
    current = current_norms_snapshot(session)
    if current is not None:
        pytest.fail(
            f"this lane database has a committed current norms snapshot ({current}); the "
            "NULL cases need a freshly migrated lane, because a designation cannot be unset"
        )


def _basis(seeded, helpers) -> str:
    return input_basis_digest(
        version_uid=seeded.version_uid,
        blob_ids={helpers.MANIFEST_ROLE_SOURCE: seeded.source_blob_id},
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
    )


def _pinned_digest(seeded, helpers, snapshot: str | None) -> str:
    return frozen_input_digest(
        version_uid=seeded.version_uid,
        blob_ids={helpers.MANIFEST_ROLE_SOURCE: seeded.source_blob_id},
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        norms_snapshot_id=snapshot,
    )


def _start(session: Session, seeded, key: str):
    return start_audit_run(
        session, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
        idempotency_key=key,
    )


# --- startRun --------------------------------------------------------------------------------


def test_a_new_run_with_none_current_pins_null_and_stores_its_basis(
    session, seeded, helpers
) -> None:
    _require_none_current(session)
    started = _start(session, seeded, _key())
    row = helpers.audit_run_row(session, started.run_id)
    assert row["norms_snapshot_id"] is None
    # Byte-identical: the stored digest is the basis, the pre-W55 computation.
    assert row["frozen_input_digest"] == _basis(seeded, helpers)
    assert row["frozen_input_digest"] == _pinned_digest(seeded, helpers, None)


def test_a_new_run_pins_the_current_snapshot(session, seeded, helpers) -> None:
    snapshot = _snapshot(session)
    _designate(session, snapshot)
    started = _start(session, seeded, _key())
    row = helpers.audit_run_row(session, started.run_id)
    assert row["norms_snapshot_id"] == snapshot
    assert row["frozen_input_digest"] == _pinned_digest(seeded, helpers, snapshot)
    assert row["frozen_input_digest"] != _basis(seeded, helpers), (
        "a pinned run's stored digest and its basis must differ"
    )


def test_a_retry_after_a_designation_change_replays(session, seeded, helpers) -> None:
    first_snapshot, second_snapshot = _snapshot(session), _snapshot(session)
    _designate(session, first_snapshot)
    key = _key()
    first = _start(session, seeded, key)
    before = helpers.audit_run_row(session, first.run_id)

    _designate(session, second_snapshot)
    retry = _start(session, seeded, key)
    assert retry.replayed is True and retry.run_id == first.run_id
    assert helpers.audit_run_row(session, first.run_id) == before
    assert before["norms_snapshot_id"] == first_snapshot

    fresh = _start(session, seeded, _key())
    assert fresh.replayed is False
    assert helpers.audit_run_row(session, fresh.run_id)["norms_snapshot_id"] == second_snapshot


def test_a_pre_w55_key_replays_after_a_designation(session, seeded, helpers) -> None:
    """A key accepted before W55: its fingerprint written by the pre-W55 rule, by hand.

    The fingerprint is built here from ``payload_fingerprint`` and the literal key names,
    not by ``start_run_fingerprint``, so a change to that function cannot hide itself.
    """
    key = _key()
    basis = _basis(seeded, helpers)
    ledger = CommandRepository()
    claimed = ledger.begin(
        session, command_type=COMMAND_TYPE_START_RUN, idempotency_key=IdempotencyKey(key),
        fingerprint=payload_fingerprint({
            "analysis_profile_id": seeded.analysis_profile_id,
            "frozen_input_digest": basis,
            "prompt_bundle_id": seeded.prompt_bundle_id,
            "provider_mode": "recorded",
            "version_uid": seeded.version_uid,
        }),
    )
    old_run = str(RunId.new())
    RunRepository().create(
        session, run_id=old_run, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
        frozen_input_digest=basis, command_id=str(claimed.command_id),
    )
    ledger.succeed(session, claimed.command_id, {"run_id": old_run})

    _designate(session, _snapshot(session))
    retry = _start(session, seeded, key)
    assert retry.replayed is True and retry.run_id == old_run
    assert helpers.audit_run_row(session, old_run)["norms_snapshot_id"] is None


def test_start_run_serves_the_pin_through_the_shipped_adapter(
    session, seeded, helpers
) -> None:
    snapshot = _snapshot(session)
    _designate(session, snapshot)

    class _NoCarrier:
        """Records the submission and runs nothing: only the accepted run is asserted."""

        def __init__(self) -> None:
            self.submitted: list[object] = []

        def submit(self, job: object) -> None:
            self.submitted.append(job)

    factory = sessionmaker(
        bind=session.connection(), expire_on_commit=False, future=True,
        join_transaction_mode="create_savepoint",
    )
    carrier = _NoCarrier()
    adapter = RunAdapter(
        factory, blob_store=None, adapter=None, provider_config=None,
        provider_mode="recorded", analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, carrier=carrier,
    )
    view = adapter.start_run(version_uid=seeded.version_uid, idempotency_key=_key())
    assert view.norms_snapshot_id == snapshot
    assert run_status_body(view)["norms_snapshot_id"] == snapshot
    assert adapter.get_run_status(run_id=view.run_id).norms_snapshot_id == snapshot
    assert len(carrier.submitted) == 1


# --- reauditRun ------------------------------------------------------------------------------


def _terminal_source(session: Session, seeded, *, snapshot: str | None) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
        frozen_input_digest="a" * 64, command_id=None, norms_snapshot_id=snapshot,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    runs.terminate(
        session, run_id=run_id, from_state="running", to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
    )
    return run_id


def _reaudit(session: Session, seeded, source_id: str, key: str):
    return reaudit_run(
        session, source_run_id=source_id, roles=frozenset({"expert"}), idempotency_key=key,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
    )


def test_a_reaudit_pins_the_current_snapshot_and_its_retry_replays(
    session, seeded, helpers
) -> None:
    old, current, later = _snapshot(session), _snapshot(session), _snapshot(session)
    source_id = _terminal_source(session, seeded, snapshot=old)
    _designate(session, current)
    key = _key()
    first = _reaudit(session, seeded, source_id, key)
    child = RunRepository().get(session, first.run_id)
    assert child.norms_snapshot_id == current, "the re-audit did not pin the current snapshot"
    assert child.frozen_input_digest == _pinned_digest(seeded, helpers, current)
    assert child.reaudit_of_run_id == source_id

    _designate(session, later)
    retry = _reaudit(session, seeded, source_id, key)
    assert retry.replayed is True and retry.run_id == first.run_id
    assert RunRepository().get(session, first.run_id).norms_snapshot_id == current


def test_a_reaudit_with_none_current_pins_null_whatever_the_source_pinned(
    session, seeded, helpers
) -> None:
    _require_none_current(session)
    source_id = _terminal_source(session, seeded, snapshot=_snapshot(session))
    started = _reaudit(session, seeded, source_id, _key())
    child = RunRepository().get(session, started.run_id)
    assert child.norms_snapshot_id is None
    assert child.frozen_input_digest == _basis(seeded, helpers)
