"""Step 7: the whole sequence repeated under the same keys, counted across every table.

Each module proved its own idempotency. This is the first thing to repeat the sequence
end to end and count rows across all sixteen P02 tables afterwards, which is what
"creates no duplicate versions, runs, observations or decisions" actually claims.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text


def test_the_table_list_this_suite_counts_is_complete(session, journey_harness):
    """A table added by a later migration and never counted would silently narrow the
    claim below from "every table" to "the ones we remembered"."""
    journey_harness.assert_table_list_is_complete(session)


def test_repeating_the_sequence_under_one_key_adds_no_row_anywhere(
    session_factory, blob_store, recorded_adapter, provider_config, journey_harness
):
    from auditmanager.analysis.text import AR_TEXT_PROFILE, AR_TEXT_PROMPT_BUNDLE
    from auditmanager.runs import execute_run, start_audit_run
    from auditmanager.shared.errors import DomainError

    h = journey_harness
    run_key = h.new_key("idempotent-run")

    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("idem"))

    def start() -> tuple[str, bool]:
        with session_factory() as session:
            started = start_audit_run(
                session,
                version_uid=seed["version_uid"],
                analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
                prompt_bundle_id=str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
                provider_mode="recorded",
                idempotency_key=run_key,
                )
            session.commit()
            return str(started.run_id), bool(started.replayed)

    first_run, first_replayed = start()
    assert first_replayed is False, "a fresh key must not report a replay"
    with session_factory() as session:
        execute_run(session, first_run, blob_store=blob_store, adapter=recorded_adapter,
                    provider_config=provider_config)
        session.commit()

    with session_factory() as session:
        before = h.table_counts(session)
        assert before["audit_run"] > 0, "counting an empty schema would prove nothing"

    second_run, second_replayed = start()
    assert second_run == first_run, "the same key returned a different run"
    assert second_replayed is True, "the same key did not report a replay"

    # The documented contract of start_audit_run is that the same key returns the original
    # run "whatever state that run has since reached". A caller that ignores `replayed`
    # and executes again meets the state machine, which refuses fail-closed rather than
    # duplicating anything. Both halves are asserted: the refusal, and the zero delta.
    with session_factory() as session:
        with pytest.raises(DomainError) as refusal:
            execute_run(session, second_run, blob_store=blob_store, adapter=recorded_adapter,
                        provider_config=provider_config)
        session.rollback()
    assert "transition" in str(refusal.value).lower()

    with session_factory() as session:
        after = h.table_counts(session)

    changed = {name: (before[name], after[name]) for name in before if before[name] != after[name]}
    assert not changed, f"repeating the sequence added rows: {changed}"
