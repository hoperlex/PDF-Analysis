"""The PC-01 journey, end to end, through the REAL public surfaces.

Eight sessions built this backend in parallel and each verified its own segment. This
module drives all of them in one sequence, starting where a product starts: a project
and an upload through ``IngestService``.

**This suite is red at base 92bece8, and that is its finding.** ``IngestService`` writes
the manifest role ``source_document`` where the frozen stage registry declares
``source.document``, so no version it produces can start a run. The defect is owned by
the ingest/documents tree and is stated precisely in
``tests/integration/p02_journey/test_manifest_role_seam.py``.

It is deliberately not worked around here. The sibling integration suite seeds a
contract-correct manifest and measures everything after the seam, so the journey figures
exist; this suite is what says whether a product could actually reach them. It goes green
with no edit once the owning tree is corrected.
"""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import text


@pytest.fixture(scope="module")
def corpus_journey(journey_harness, session_factory, blob_store, recorded_adapter, provider_config):
    """Drive the journey once for the module; every test below reads the same run.

    Module-scoped because the journey is the expensive thing and re-running it per test
    would say nothing extra -- each test asserts a different property of one composition.
    """
    from auditmanager.ingest import IngestService
    from auditmanager.shared.errors import DomainError

    h = journey_harness
    with session_factory() as session:
        service = IngestService(blob_store, session_factory=session_factory)
        try:
            record = h.drive_journey(
                session,
                ingest=service,
                blob_store=blob_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
                project_name=f"B-III convergence {h.new_key('proj')}",
                upload_key=h.new_key("upload"),
                run_key=h.new_key("run"),
            )
        except DomainError as refusal:
            pytest.fail(
                "the real upload path cannot start a run, so the journey never begins: "
                f"{refusal}. IngestService writes the manifest role 'source_document'; "
                "contracts/analysis/v1/stage-registry.json declares 'source.document'. "
                "Owned by the ingest/documents tree; see "
                "tests/integration/p02_journey/test_manifest_role_seam.py."
            )
        yield record


def test_journey_reaches_published_with_an_empty_degradation_set(corpus_journey):
    assert corpus_journey.state == "published", (
        f"run {corpus_journey.run_id} terminated {corpus_journey.state!r}"
    )
    degradation = corpus_journey.degradation_set
    assert not degradation, f"expected an empty degradation set, got {degradation!r}"


def test_four_pc01_stages_all_recorded_succeeded(corpus_journey, session, journey_harness):
    from auditmanager.runs import PC01_STAGES

    rows = session.execute(
        text("SELECT stage_id, status FROM stage_result WHERE run_id = :r ORDER BY stage_id"),
        {"r": corpus_journey.run_id},
    ).mappings().all()
    observed = {row["stage_id"]: row["status"] for row in rows}
    assert set(observed) == set(PC01_STAGES), (
        f"stages recorded {sorted(observed)} != PC01_STAGES {sorted(PC01_STAGES)}"
    )
    assert set(observed.values()) == {"succeeded"}, observed


def test_findings_and_evidence_resolve_to_this_run(corpus_journey, session):
    from auditmanager.findings import published_findings

    findings = published_findings(session, corpus_journey.run_id)
    assert len(findings) == corpus_journey.published_finding_count
    for row in findings:
        assert row.run_id == corpus_journey.run_id
        assert row.project_uid == corpus_journey.project_uid
        assert row.version_uid == corpus_journey.version_uid


def test_csv_resolves_every_row_back_to_the_journey(corpus_journey, session):
    from auditmanager.exports import COLUMNS, export_run_csv

    export = export_run_csv(session, corpus_journey.run_id)
    # The literal byte-order mark, not the module's constant: importing BOM from the
    # module under test makes this assertion vacuously true if the constant is ever empty.
    assert export.content.startswith(b"\xef\xbb\xbf"), "CSV does not open with a UTF-8 BOM"
    body = export.content[3:].decode("utf-8")
    assert "\r\n" in body, "CSV is not CRLF-terminated"

    reader = csv.reader(io.StringIO(body))
    header = next(reader)
    rows = [r for r in reader if r]
    assert tuple(header) == tuple(COLUMNS)
    assert len(header) == 17

    index = {name: position for position, name in enumerate(header)}
    for row in rows:
        assert row[index["project_uid"]] == corpus_journey.project_uid
        assert row[index["version_uid"]] == corpus_journey.version_uid
        assert row[index["run_id"]] == corpus_journey.run_id
        assert row[index["run_state"]] == "published"


def test_two_exports_are_byte_identical(corpus_journey, session):
    from auditmanager.exports import export_run_csv

    first = export_run_csv(session, corpus_journey.run_id).content
    second = export_run_csv(session, corpus_journey.run_id).content
    assert first == second
    assert len(first) > 0


def test_no_internal_identifier_leaks_into_the_csv(corpus_journey, session):
    """No bucket, object key or ``s3://`` reference may reach an exported row."""
    from auditmanager.exports import export_run_csv
    import os

    content = export_run_csv(session, corpus_journey.run_id).content.decode("utf-8")
    assert "s3://" not in content
    assert os.environ["S3_BUCKET"] not in content
    assert "blob_" not in content
