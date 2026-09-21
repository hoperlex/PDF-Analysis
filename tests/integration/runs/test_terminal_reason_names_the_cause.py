"""A run that died because the provider was unreachable must say so on the run row.

`P4_CLOSURE.md` §2 made the point about the stage row: `dependency_unavailable` is
retryable, so a run that failed because the proxy was unreachable and was published as an
unclassified analysis failure left an operator with no reason to retry it. The stage row
carries the right code. The run row does not: `select_terminal` receives only statuses, so
every failed stage becomes `analysis_failed` whatever killed it.

`W2-RUN` named this the single most worthwhile follow-up and correctly did not reach outside
its tree to fix it. `audit_run.terminal_reason` is CHECK-constrained to the frozen
twenty-member error catalog, so `dependency_unavailable` is already a legal value — this
needs no new vocabulary and does not approach the twenty-first code.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from auditmanager.analysis.text import ProviderMode
from auditmanager.analysis.text.config import DEPENDENCY_NAME
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey


def _run_against(session, seeded, blob_store, adapter, provider_config) -> str:
    """Drive one run to its terminal and return its id.

    ``sleep`` is captured rather than left to the clock. The unreachable-provider case here
    goes through the retry loop -- ``dependency_unavailable`` is retryable, which is exactly
    what makes this fixture reach the exhausted-budget path -- so without the injection each
    run really waited out the pinned ``(2.0, 8.0)`` backoffs. ``W5-ADV`` measured ~20 s per
    battery spent asleep, proving nothing: the waits are already guarded, by order and by
    value, in ``test_retry_policy.py``.
    """
    waits: list[float] = []
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=IdempotencyKey(f"w3-reason-{uuid.uuid4()}"),
    )
    try:
        execute_run(
            session,
            started.run_id,
            blob_store=blob_store,
            adapter=adapter,
            provider_config=provider_config,
            sleep=waits.append,
        )
    except DomainError:
        pass
    return str(started.run_id)


def _terminal(session, run_id: str) -> dict:
    return dict(
        session.execute(
            text(
                "SELECT state, terminal_reason, degradation_set "
                "FROM audit_run WHERE run_id = :r"
            ),
            {"r": run_id},
        ).mappings().one()
    )


def _stage_error_code(session, run_id: str, stage_id: str) -> str | None:
    error = session.execute(
        text("SELECT error FROM stage_result WHERE run_id = :r AND stage_id = :s"),
        {"r": run_id, "s": stage_id},
    ).scalar_one_or_none()
    return None if not error else error.get("code")


class _NeverReachable:
    """A provider that is unreachable for good, raising exactly as ``live.py`` maps it.

    This fixture was a `RecordedAdapter` over an empty directory until `W29-RETRY`. That
    is a file missing from a local disk, not a provider that could not be reached, and
    once the adapter stopped calling it a transport failure this suite would have gone on
    claiming to cover the unreachable provider while driving a single-attempt local miss.
    The claim is the same; the fixture now produces the failure the claim is about.
    """

    def __init__(self) -> None:
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request):
        self.calls += 1
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model provider did not return a usable response",
            dependency=DEPENDENCY_NAME,
        )


@pytest.fixture()
def unreachable_provider_run(session, seeded, blob_store, provider_config) -> str:
    """A provider that is never reachable, driven through the whole retry ladder."""
    return _run_against(session, seeded, blob_store, _NeverReachable(), provider_config)


def test_the_stage_really_did_fail_on_the_transport(unreachable_provider_run, session):
    """The precondition. Without it the assertion below could pass on any failure at all."""
    code = _stage_error_code(session, unreachable_provider_run, "text_analysis")
    assert code == "dependency_unavailable", (
        f"the stage failed with {code!r}; this fixture is not producing the transport case"
    )


def test_the_run_row_names_the_transport_failure_not_a_generic_analysis_failure(
    unreachable_provider_run, session
):
    row = _terminal(session, unreachable_provider_run)
    assert row["state"] == "failed"
    assert row["terminal_reason"] == "dependency_unavailable", (
        "the run row flattens a transport failure into "
        f"{row['terminal_reason']!r}. dependency_unavailable is retryable and "
        "analysis_failed is not, so an operator reading the run has no reason to retry a "
        "run the provider simply could not answer."
    )


def test_a_real_analysis_failure_still_reads_as_one(
    session, seeded, blob_store, recorded_adapter, provider_config
):
    """The control. Without it the change could report dependency_unavailable for
    everything, which would be the same defect pointing the other way."""
    run_id = _run_against(session, seeded, blob_store, recorded_adapter, provider_config)
    row = _terminal(session, run_id)
    assert row["state"] == "published", (
        f"the clean corpus run did not publish: {row}; this control proves nothing"
    )
    assert row["terminal_reason"] is None
