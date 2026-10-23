"""A v3 provider refusal remains legible on the failed Run."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.runs import carrier
from auditmanager.shared.errors import DomainError, ErrorCode


@pytest.mark.parametrize("identity,expected_reason", (
    ("v3", ErrorCode.COST_BUDGET_EXCEEDED.value),
    ("legacy", ErrorCode.ANALYSIS_FAILED.value),
    ("mixed", ErrorCode.ANALYSIS_FAILED.value),
))
def test_carrier_keeps_typed_refusal_only_for_exact_v3_pair(
    monkeypatch, identity, expected_reason,
):
    events = []
    profile = str(AR_V3_BETA_PROFILE_ID) if identity != "legacy" else "legacy-profile"
    bundle = str(AR_V3_BETA_BUNDLE_ID) if identity == "v3" else "legacy-bundle"
    row = SimpleNamespace(
        state="running", analysis_profile_id=profile, prompt_bundle_id=bundle,
    )

    class Runs:
        def find(self, session, run_id):
            assert run_id == "run_test"
            return row

        def terminate(self, session, **fields):
            events.append(("terminate", fields))

    class Jobs:
        def fail_for_run(self, session, *, run_id):
            events.append(("fail_job", run_id))

    class Session:
        def commit(self):
            events.append(("commit", None))

    @contextmanager
    def sessions():
        yield Session()

    monkeypatch.setattr(carrier, "JobRepository", Jobs)
    failure = DomainError(ErrorCode.COST_BUDGET_EXCEEDED, budget_scope="run")
    carrier._record_crash(sessions, "run_test", failure, runs=Runs())

    assert events[0] == ("fail_job", "run_test")
    assert events[1][0] == "terminate"
    fields = events[1][1]
    assert fields["to_state"] == "failed"
    assert fields["terminal_reason"] == expected_reason
    assert fields["terminal_detail"] == (
        {"budget_scope": "run"} if identity == "v3" else None
    )
    assert fields["interrupted_reason"] == carrier.CRASHED_REASON
    assert events[2] == ("commit", None)
