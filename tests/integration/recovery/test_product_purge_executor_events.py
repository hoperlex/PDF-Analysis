"""`DEV-PURGE-EXECUTOR-EVENTS-01`: the product purge keeps the ``executor.*`` audit events.

``KEEP_EVENT_PREFIXES`` always said ``("norm_custody.", "executor.")`` and three documents say the
executor events stay, but the keep and delete predicates of ``audit_event`` named ``norm_custody.``
only. The apply step therefore deleted every ``executor.*`` event while the executor tables and
their command receipts stayed, and the ``keep-unchanged`` and ``product-emptied`` guards could not
notice: they use the same predicate. The existing declaration test only asserted that the prefix is
in the tuple, so no test could fail on the delete.

* the first test needs no database: every prefix of the tuple appears in the keep predicate, the
  delete predicate is exactly its negation, and a prefix added to the tuple alone reaches both;
* the others run the real tool (plan, snapshot, apply, delete) on a private clone of the stand in
  miniature, after writing ONE event of each family the way the product writes it: an
  ``executor.secret_set`` (through the journal writer, with the payload ``set_secret`` writes), a
  ``norm_custody.bound`` (as ``purge_seed`` writes its custody journal) and an ``audit_run.created``.
  The executor and custody events must survive byte for byte, the run event must go, and the keep
  fingerprint of ``audit_event`` must be equal before and after, measured both with the tool's
  fingerprint and with the test's own digest (a comparison that shared the tool's predicate would
  prove nothing).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import text

from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import (
    AuditEventId, ExecutorConnectionId, ExecutorSecretId, NormsSnapshotId, RunId,
)
from scripts.recovery import product_purge as tool
from tests.integration.recovery.purge_seed import digest_of
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, full_purge, invoke, seeded, stand,
)

#: The test's own statement of which events are kept; it does not use the tool's predicate.
KEPT = "starts_with(event_type, 'norm_custody.') OR starts_with(event_type, 'executor.')"


# --- the predicates (no database) --------------------------------------------------------------


def test_the_audit_event_predicates_are_built_from_every_keep_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    keep, delete = tool._predicates([])["audit_event"]
    assert {"norm_custody.", "executor."} <= set(tool.KEEP_EVENT_PREFIXES)
    for prefix in tool.KEEP_EVENT_PREFIXES:
        assert f"starts_with(t.event_type, '{prefix}')" in keep, prefix
    # the delete set is exactly the complement of the keep set, and names no product family as kept
    assert delete == f"NOT {keep}"
    assert not any(prefix in keep for prefix in tool.PRODUCT_EVENT_PREFIXES)
    # a prefix added to the tuple alone reaches the keep predicate, the delete predicate and so the
    # fingerprint of the keep rows (``keep_fingerprints`` reads the same pair)
    monkeypatch.setattr(tool, "KEEP_EVENT_PREFIXES", (*tool.KEEP_EVENT_PREFIXES, "zz_future."))
    future_keep, future_delete = tool._predicates([])["audit_event"]
    assert "starts_with(t.event_type, 'zz_future.')" in future_keep
    assert future_delete == f"NOT {future_keep}"


# --- the purge, on a real database -------------------------------------------------------------


@dataclass(frozen=True)
class Events:
    executor: str
    custody: str
    product: str


def _seed_one_event_of_each_family(stand: Stand) -> Events:
    """One event per family, each identified by its ``audit_event_id`` (a fresh id, never the seed's)."""
    connection, run = str(ExecutorConnectionId.new()), str(RunId.new())
    with create_session_factory(stand.engine).begin() as session:
        # the writer and the payload of `executors/commands.py::set_secret`
        append_execution_event(
            session, event_type="executor.secret_set", aggregate_type="ExecutorConnection",
            aggregate_id=connection,
            payload={"connection_id": connection, "secret_id": str(ExecutorSecretId.new()),
                     "purpose": "api_key", "actor_uid": "usr_01M5F21PBT7E8WRN3M61BDQFDD"},
        )
        append_execution_event(
            session, event_type="audit_run.created", aggregate_type="AuditRun",
            aggregate_id=run, payload={"state": "created"},
        )
        custody = str(AuditEventId.new())
        session.execute(text(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
            "VALUES (:e, 'norm_custody.bound', 'NormCustody', :a, CAST('{}' AS jsonb))"),
            {"e": custody, "a": "nad_" + str(NormsSnapshotId.new()).removeprefix("ns_")})
    with stand.engine.connect() as raw:
        ids = dict(raw.execute(text(
            "SELECT aggregate_id, audit_event_id FROM audit_event WHERE aggregate_id = ANY(:a)"),
            {"a": [connection, run]}).all())
    return Events(executor=ids[connection], custody=custody, product=ids[run])


def _event_ids(stand: Stand) -> set[str]:
    with stand.engine.connect() as connection:
        return set(connection.execute(text("SELECT audit_event_id FROM audit_event")).scalars())


def _tool_keep_fingerprint(stand: Stand) -> tuple[int, str]:
    with stand.engine.connect() as connection:
        keep_pairs, _ = tool.blob_columns(connection)
        return tool.keep_fingerprints(connection, keep_pairs)["audit_event[keep rows]"]


def test_a_dry_run_counts_the_executor_event_as_a_row_that_stays(stand: Stand) -> None:
    events = _seed_one_event_of_each_family(stand)
    kept = digest_of(stand.engine, "audit_event", KEPT)[0]
    doomed = digest_of(stand.engine, "audit_event", f"NOT ({KEPT})")[0]
    assert kept >= 5 and doomed >= 25  # the seed's custody journal and run journal, plus one of each
    before = digest_of(stand.engine, "audit_event")

    code, out, err = invoke(tool, stand, "plan", "--dry-run")

    assert code == 0, err
    assert f"  audit_event  (delete {doomed} rows, keep {kept} rows)" in out
    assert digest_of(stand.engine, "audit_event") == before
    assert {events.executor, events.custody, events.product} <= _event_ids(stand)


def test_the_purge_keeps_the_executor_and_custody_events_and_deletes_the_run_event(
    stand: Stand, tmp_path: Path
) -> None:
    events = _seed_one_event_of_each_family(stand)
    kept_before = digest_of(stand.engine, "audit_event", KEPT)
    tool_before = _tool_keep_fingerprint(stand)
    executor_rows = digest_of(stand.engine, "audit_event", "starts_with(event_type, 'executor.')")
    assert executor_rows[0] == 1 and kept_before[0] >= 5

    steps = full_purge(tool, stand, tmp_path / "dump")

    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps
    surviving = _event_ids(stand)
    assert events.executor in surviving, "the executor.secret_set event was deleted by the purge"
    assert events.custody in surviving
    assert events.product not in surviving
    # the kept rows are the same rows: the test's own digest and the tool's fingerprint agree before and after
    assert digest_of(stand.engine, "audit_event", KEPT) == kept_before
    assert digest_of(stand.engine, "audit_event", "starts_with(event_type, 'executor.')") == executor_rows
    assert _tool_keep_fingerprint(stand) == tool_before
    # and nothing else is left in the table
    assert digest_of(stand.engine, "audit_event") == kept_before

    # a second pass has nothing to purge and still counts the executor event as a row that stays
    code, out, err = invoke(tool, stand, "plan")
    assert code == 0, err
    assert f"  audit_event  (delete 0 rows, keep {kept_before[0]} rows)" in out
    assert "nothing-to-purge: yes" in out
