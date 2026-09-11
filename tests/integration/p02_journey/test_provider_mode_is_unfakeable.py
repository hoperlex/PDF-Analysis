"""A recorded run must never be presentable as a live one.

``auditmanager.analysis.text`` gets this right where it can see it: ``stage.py`` reads
``mode = adapter.provider_mode`` off the adapter that produced the response, never off
configuration, and ``assert_consistent_mode`` refuses to publish provenance that
disagrees with itself. Its docstring names the failure it prevents -- "a recorded run
published with ``provider_mode: live``, and nothing downstream could detect that
afterwards".

That failure still occurs, one level up. ``audit_run.provider_mode`` is a string the
caller hands ``start_audit_run``; nothing validates it against the adapter that
``execute_run`` is given, and ``P02_SEAMS.md`` §6 column 6 sources the CSV's
``provider_mode`` from exactly that row. So the export -- the artifact an expert reads --
reports whatever the caller declared.

``auditmanager.exports`` is correct here: it reads the column the seam register names.
The reconciliation belongs to ``auditmanager.runs``, the only place holding both the run
row and the adapter.

These tests seed their version through ``DocumentRepository`` because the manifest-role
defect blocks the real upload path; that defect has its own test and is not masked here.
"""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import text


def _csv_modes(session, run_id: str) -> set[str]:
    from auditmanager.exports import export_run_csv

    content = export_run_csv(session, run_id).content
    reader = csv.reader(io.StringIO(content[3:].decode("utf-8")))
    header = next(reader)
    position = header.index("provider_mode")
    return {row[position] for row in reader if row}


def test_a_run_declared_live_and_executed_recorded_is_refused(
    session, blob_store, recorded_adapter, provider_config, journey_harness
):
    """The attack: declare ``live`` at start, execute with the recorded adapter.

    This test originally asserted that the export should *correct* the mode. The
    integrator closed the defect by **refusing** the mismatch instead, and changed this
    expectation — recorded here because the session that found the defect proposed the
    other remedy, and a reader deserves to know an expectation was overridden rather than
    met.

    The reason for refusing rather than correcting: ``audit_run.provider_mode`` is the
    canonical field. Correcting at the export leaves a false value standing in the
    database while one reader compensates, so every *other* reader — the API, the UI
    badge, a later export — is correct only as long as each one remembers to re-derive.
    Refusing before any stage runs means the column cannot hold a mode the run did not
    have, and every downstream reader is right by construction.

    ``analysis.text`` still guards its own provenance with ``assert_consistent_mode``;
    this is the same refusal one level up, in the only place holding both the run row and
    the adapter.
    """
    h = journey_harness
    seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("modeattack"))

    actual = recorded_adapter.provider_mode.value
    assert actual == "recorded", "fixture precondition: this adapter must be the recorded one"

    with pytest.raises(Exception) as raised:
        h.run_from_seed(
            session,
            seed,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            declared_provider_mode="live",
            run_key=h.new_key("run"),
        )
    assert "provider mode" in str(raised.value), (
        f"the mismatch was not refused for the stated reason: {raised.value}"
    )


def test_a_run_declared_recorded_and_executed_recorded_still_works(
    session, blob_store, recorded_adapter, provider_config, journey_harness
):
    """The control. The refusal above must reject a disagreement, not every run.

    Without this, a guard that refused unconditionally would look identical.
    """
    h = journey_harness
    seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("modeok"))
    run_id = h.run_from_seed(
        session,
        seed,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
        declared_provider_mode="recorded",
        run_key=h.new_key("run"),
    )
    assert _csv_modes(session, run_id) == {"recorded"}

def test_truthful_declaration_still_works(
    session, blob_store, recorded_adapter, provider_config, journey_harness
):
    """The control. Without it, the test above would also pass on a chain that always
    reported ``recorded`` regardless of what happened."""
    h = journey_harness
    seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("modehonest"))
    run_id = h.run_from_seed(
        session,
        seed,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
        declared_provider_mode="recorded",
        run_key=h.new_key("run"),
    )
    assert _csv_modes(session, run_id) == {"recorded"}
