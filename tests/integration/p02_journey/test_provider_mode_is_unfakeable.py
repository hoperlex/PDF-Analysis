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


def test_recorded_run_declared_live_is_exported_as_recorded(
    session, blob_store, recorded_adapter, provider_config, journey_harness
):
    """The attack: declare ``live`` at start, execute with the recorded adapter.

    DEFECT as of base 92bece8: the run row and every CSV row report ``live`` while the
    adapter, the model-call provenance and the observation rows all say ``recorded``.
    """
    h = journey_harness
    seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("modeattack"))
    run_id = h.run_from_seed(
        session,
        seed,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
        declared_provider_mode="live",
        run_key=h.new_key("run"),
    )

    actual = recorded_adapter.provider_mode.value
    assert actual == "recorded", "fixture precondition: this adapter must be the recorded one"

    call_modes = set(
        session.execute(
            text("SELECT DISTINCT provider_mode FROM model_call WHERE run_id = :r"),
            {"r": run_id},
        ).scalars()
    )
    assert call_modes == {"recorded"}, (
        f"provenance disagrees with the adapter: model_call says {call_modes}"
    )

    run_row_mode = session.execute(
        text("SELECT provider_mode FROM audit_run WHERE run_id = :r"), {"r": run_id}
    ).scalar_one()
    exported = _csv_modes(session, run_id)

    assert exported == {actual}, (
        f"a run executed by the {actual} adapter is exported as {exported}. "
        f"audit_run.provider_mode is {run_row_mode!r}, taken unvalidated from the caller's "
        f"start_audit_run argument, while model_call.provider_mode is {call_modes}. "
        "Nothing reconciles the run row with the adapter that executed it, so the CSV "
        "an expert reads can claim a live review that never happened."
    )
    assert run_row_mode == actual, (
        f"audit_run.provider_mode is {run_row_mode!r} for a run executed by the {actual} adapter"
    )


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
