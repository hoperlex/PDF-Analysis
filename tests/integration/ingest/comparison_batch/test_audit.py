"""D-263: one identity-only journal event per successful keyed batch act, atomic with state."""

import pytest
from sqlalchemy import text

from auditmanager.ingest.comparison_batch.public import ComparisonBatchService
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import new_ulid
from tests.integration.ingest.comparison_batch.test_exclude_retry import _fail


def _proposed(h, *, processing=False):
    """Seed valid metadata states: byte-upload behavior is covered by INGEST-02.

    These journal tests exercise the real act/command/state transaction. They
    intentionally need no multipart upload or PDF parser before reaching it.
    """
    upload = h.declare(["not-in-audit-name.pdf"]).upload_id
    sets = [f"cus_{new_ulid()}" for _ in range(2)]
    with session_scope(h.sessions) as session:
        for identity in sets:
            session.execute(text("INSERT INTO comparison_upload_set(comparison_upload_set_id,comparison_upload_id) VALUES(:id,:upload)"),
                            {"id": identity, "upload": upload})
            for state in ("reading", "needs_confirmation"):
                session.execute(text("UPDATE comparison_upload_set SET state=:state WHERE comparison_upload_set_id=:id"),
                                {"id": identity, "state": state})
        for state in (("proposed", "processing") if processing else ("proposed",)):
            session.execute(text("UPDATE comparison_upload SET state=:state WHERE comparison_upload_id=:id"),
                            {"id": upload, "state": state})
    return upload, sets[0]


@pytest.mark.parametrize("action,event", [
    ("exclude", "comparison.upload_set_excluded"),
    ("retry", "comparison.upload_set_retried"),
    ("pause", "comparison.upload_paused"),
    ("resume", "comparison.upload_resumed"),
    ("cancel", "comparison.upload_cancelled"),
])
def test_each_keyed_act_has_one_actor_command_event_and_replay_adds_none(h, action, event):
    if action == "cancel":
        upload = h.declare(["not-in-audit-name.pdf"]).upload_id
        set_id = None
    else:
        upload, first_id = _proposed(h, processing=action in {"pause", "resume"})
        set_id = first_id if action in {"exclude", "retry"} else None
        if action == "retry":
            _fail(h, set_id, "comparison_sets_limit")
        if action == "resume":
            h.pause(upload)
    key = f"batch-audit-{new_ulid()}"
    target = getattr(h, action)
    args = (upload, set_id) if set_id else (upload,)
    target(*args, key=key)
    target(*args, key=key)
    rows = h.rows("SELECT aggregate_type,aggregate_id,payload FROM audit_event WHERE event_type=:event AND aggregate_id=:id",
                  event=event, id=set_id or upload)
    assert len(rows) == 1
    aggregate, identity, payload = rows[0]
    assert aggregate == ("ComparisonUploadSet" if set_id else "ComparisonUpload") and identity == (set_id or upload)
    expected_keys = {"comparison_upload_id", "project_uid", "actor_uid", "command_id"}
    if set_id:
        expected_keys.add("set_id")
        assert payload["set_id"] == set_id
    assert set(payload) == expected_keys
    assert payload["comparison_upload_id"] == upload and payload["project_uid"] == h.project_uid
    assert payload["actor_uid"] == h.user and "not-in-audit-name" not in str(payload)
    assert h.rows("SELECT state FROM command_record WHERE command_id=:command", command=payload["command_id"]) == [("succeeded",)]


def test_audit_failure_rolls_back_act_and_command_then_same_key_can_retry(h, monkeypatch):
    upload, first_id = _proposed(h)
    key = f"batch-audit-{new_ulid()}"
    original = ComparisonBatchService._audit_act
    def fail(*args, **kwargs):
        raise RuntimeError("audit insert failed")
    monkeypatch.setattr(ComparisonBatchService, "_audit_act", staticmethod(fail))
    with pytest.raises(RuntimeError, match="audit insert failed"):
        h.exclude(upload, first_id, key=key)
    assert h.set_states(upload)[first_id] == "needs_confirmation"
    assert h.rows("SELECT count(*) FROM command_record WHERE idempotency_key=:key", key=key) == [(0,)]
    assert h.rows("SELECT count(*) FROM audit_event WHERE aggregate_id=:id AND event_type='comparison.upload_set_excluded'",
                  id=first_id) == [(0,)]
    monkeypatch.setattr(ComparisonBatchService, "_audit_act", staticmethod(original))
    assert h.exclude(upload, first_id, key=key).state == "excluded"
    assert h.rows("SELECT count(*) FROM audit_event WHERE aggregate_id=:id AND event_type='comparison.upload_set_excluded'",
                  id=first_id) == [(1,)]
