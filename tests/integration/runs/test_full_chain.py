"""The whole chain, on the real corpus, against real services.

This is the first suite in the programme to run ``B1 -> B2 -> B3 -> B4`` end to end on
the **pinned** extractor. ``GATE_B1_CLOSURE.md`` §4 item 3 recorded that as the open
question of the wave: each session had verified its own segment on its own fixture, so
"six independently correct modules compose" was an assumption rather than a measurement.
:func:`test_the_pinned_extractor_reproduces_the_recorded_request` measures it directly,
and the rest of this module measures what the composed chain then produces.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.stages.extraction import extract_document
from auditmanager.analysis.text import AR_TEXT_PROFILE, build_request, load_text_layer
from auditmanager.exports import export_run_csv
from auditmanager.findings import published_finding_count, published_findings
from auditmanager.runs import PC01_STAGES, execute_run, start_audit_run

RECORDED_MODEL_ID = "claude-opus-5"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS_PDF = REPOSITORY_ROOT / "fixtures/synthetic/ar/ar_baseline.pdf"
RECORDINGS = REPOSITORY_ROOT / "fixtures/recorded/text_analysis"
COMMITTED_TEXT_LAYER = RECORDINGS / "inputs/ar_baseline_text_layer.json"


def test_the_pinned_extractor_reproduces_the_recorded_request():
    """``B2``'s extractor must produce the text layer the recording is keyed to.

    The recorded adapter keys on ``request_sha256``, the checksum of the exact body that
    would have gone to the provider, and that body contains the rendered text layer. So
    this equality is precisely the ``B2 -> B3`` seam: if the pinned ``pdfplumber``
    disagreed with the committed input by one character, the request checksum would
    differ and every recorded run in the programme would report
    ``dependency_unavailable`` instead of replaying.

    Asserted directly rather than inferred from a passing run, because a run that fails
    for this reason and a run that fails for any other look the same from the outside.
    """
    committed = json.loads(COMMITTED_TEXT_LAYER.read_text(encoding="utf-8"))
    pdf = CORPUS_PDF.read_bytes()

    extracted = [page.text for page in extract_document(pdf).pages]
    declared = [page["text"] for page in committed["pages"]]
    assert extracted == declared, (
        "the pinned pdfplumber extraction no longer matches the committed text layer "
        "the recordings are keyed to; every recorded run would fail closed"
    )

    request = build_request(
        model_id=RECORDED_MODEL_ID,
        bundle=AR_TEXT_PROFILE.prompt_bundle,
        text_layer=load_text_layer(committed),
    )
    recording = RECORDINGS / f"{request.request_sha256}.json"
    assert recording.is_file(), (
        f"no recording is keyed to {request.request_sha256}; the committed recording "
        "answers a different question than the one this chain asks"
    )


def test_a_full_run_over_the_corpus_reaches_a_terminal_and_publishes_findings(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, helpers
):
    """The gate command's headline: a real run, a terminal state, real findings."""
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("full-chain"),
    )
    assert started.replayed is False

    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    assert result.terminal_state == "published", (
        f"expected the success terminal; got {result.terminal_state!r} with "
        f"stage statuses {dict(result.stage_statuses)} and degradation set "
        f"{result.degradation_set}"
    )
    # The success terminal is `published`. There is no `succeeded` run state at all.
    assert helpers.run_state_of(session, started.run_id) == "published"
    assert result.degradation_set == ()
    assert result.gate_ran is True

    # Every one of the four PC-01 stages persisted a result, and each succeeded.
    assert set(result.stage_statuses) == set(PC01_STAGES)
    assert set(result.stage_statuses.values()) == {"succeeded"}

    # Findings actually reached the database, and the count the executor reported is the
    # count a reader querying independently sees.
    assert result.published_finding_count > 0
    assert published_finding_count(session, started.run_id) == result.published_finding_count


def test_the_csv_row_count_is_one_per_evidence_item(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """P02 §6 granularity, measured against the run that produced the rows.

    A finding with three quotations produces three rows, so the row count is the total
    evidence count and *not* the finding count. Asserting the relationship rather than a
    hard-coded number is what makes this survive a recording being re-cut.
    """
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("csv-granularity"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    evidence_total = int(
        session.execute(
            text(
                "SELECT count(*) FROM finding_evidence e "
                "JOIN finding_observation o "
                "  ON o.finding_observation_id = e.finding_observation_id "
                "JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :run_id"
            ),
            {"run_id": started.run_id},
        ).scalar_one()
    )

    export = export_run_csv(session, started.run_id)
    body = export.content.decode("utf-8-sig").split("\r\n")
    data_rows = [line for line in body if line][1:]  # drop the header

    assert len(data_rows) == evidence_total
    assert evidence_total >= published_finding_count(session, started.run_id), (
        "each published finding contributes at least one evidence row"
    )


def test_the_frozen_input_digest_is_recorded_before_execution(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, helpers
):
    """The frozen set is written at creation and never edited afterwards.

    Read the digest out of the row while the run is still ``created``, execute, and read
    it again. A run that re-froze its inputs at execution time would differ here, and
    "the frozen set is never edited" would be a comment rather than a property.
    """
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("frozen-digest"),
    )
    before = helpers.audit_run_row(session, started.run_id)
    assert before["state"] == "created"
    assert before["norms_snapshot_id"] is None, (
        "PC-01 pins no norms snapshot; the OD-24 note records that clause unevaluated"
    )
    assert len(before["frozen_input_digest"]) == 64

    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    after = helpers.audit_run_row(session, started.run_id)

    for column in (
        "frozen_input_digest",
        "version_uid",
        "project_uid",
        "analysis_profile_id",
        "prompt_bundle_id",
        "provider_mode",
        "command_id",
    ):
        assert after[column] == before[column], f"{column} changed during execution"


def test_model_call_provenance_records_the_adapter_that_answered(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Provenance says ``recorded`` because a recording answered, not because config did."""
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("provenance"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    rows = (
        session.execute(
            text(
                "SELECT stage_id, provider_mode, status, request_sha256, response_sha256 "
                "FROM model_call WHERE run_id = :run_id"
            ),
            {"run_id": started.run_id},
        )
        .mappings()
        .all()
    )
    assert rows, "the run made a provider call and recorded none"
    for row in rows:
        assert row["stage_id"] == "text_analysis"
        assert row["provider_mode"] == "recorded"
        assert row["status"] == "succeeded"
        assert len(row["request_sha256"]) == 64
        assert len(row["response_sha256"]) == 64


def test_every_published_finding_resolves_to_the_seeded_version(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Identity wiring: a finding points at the project and version that produced it."""
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("identity-wiring"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    rows = (
        session.execute(
            text(
                "SELECT project_uid, version_uid, allocated_by_run_id "
                "FROM finding WHERE allocated_by_run_id = :run_id"
            ),
            {"run_id": started.run_id},
        )
        .mappings()
        .all()
    )
    assert rows
    for row in rows:
        assert row["project_uid"] == seeded.project_uid
        assert row["version_uid"] == seeded.version_uid
        assert row["allocated_by_run_id"] == started.run_id

    # And the observation-side read agrees.
    findings = published_findings(session, started.run_id)
    assert len(findings) == len(rows)
    assert all(entry.provider_mode == "recorded" for entry in findings)
