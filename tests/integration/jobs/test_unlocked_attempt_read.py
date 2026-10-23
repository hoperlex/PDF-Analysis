"""A pre-Blob Attempt check never takes the heartbeat's lease row lock."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.shared.errors import DomainError, ErrorCode


AUTHORITY = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")


def _row():
    return {
        "run_id": AUTHORITY.run_id,
        "job_state": "running",
        "current_attempt_id": AUTHORITY.attempt_id,
        "attempt_state": "running",
        "execution_token": AUTHORITY.execution_token,
        "lease_id": AUTHORITY.lease_id,
        "released_at": None,
        "lease_current": True,
    }


class QuerySession:
    def __init__(self, row):
        self.row = row
        self.queries = []

    def execute(self, query, params):
        self.queries.append((str(query), params))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: self.row))


def test_matching_attempt_uses_one_unlocked_select():
    session = QuerySession(_row())
    JobRepository().check_current_unlocked(session, AUTHORITY)
    assert len(session.queries) == 1
    query, params = session.queries[0]
    assert query.startswith("SELECT ")
    assert "FOR UPDATE" not in query.upper()
    assert "FOR SHARE" not in query.upper()
    assert "LEFT JOIN lease" in query
    assert "expires_at > statement_timestamp()" in query
    assert params == {
        "job_id": AUTHORITY.job_id,
        "attempt_id": AUTHORITY.attempt_id,
        "lease_id": AUTHORITY.lease_id,
    }


@pytest.mark.parametrize(("field", "value"), [
    ("run_id", "run_other"),
    ("current_attempt_id", "att_other"),
    ("job_state", "queued"),
    ("attempt_state", "lost"),
    ("lease_id", None),
    ("released_at", "now"),
    ("lease_current", False),
    ("lease_current", None),
])
def test_stale_or_expired_authority_refuses(field, value):
    row = _row()
    row[field] = value
    with pytest.raises(DomainError) as caught:
        JobRepository().check_current_unlocked(QuerySession(row), AUTHORITY)
    assert caught.value.code is ErrorCode.STALE_ATTEMPT


def test_missing_job_refuses_as_stale():
    with pytest.raises(DomainError) as caught:
        JobRepository().check_current_unlocked(QuerySession(None), AUTHORITY)
    assert caught.value.code is ErrorCode.STALE_ATTEMPT


@pytest.mark.parametrize("token", [None, "wrong", 12])
def test_missing_or_wrong_token_has_execution_token_code(token):
    row = _row()
    row["execution_token"] = token
    with pytest.raises(DomainError) as caught:
        JobRepository().check_current_unlocked(QuerySession(row), AUTHORITY)
    assert caught.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
