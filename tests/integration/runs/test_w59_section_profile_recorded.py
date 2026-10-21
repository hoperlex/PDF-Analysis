"""`W59-ANALYSIS-SETTINGS-01`: АИ, ПЗ, ПОС and ТХ run end to end in recorded mode with their own profile.

`W59-SECTION-SEAL-01` routed a classified version to its section's text profile, but in
``recorded`` mode only AR had a recording, so a section-routed run failed at
``text_analysis``. With the synthetic section recordings (``fixtures/recorded/sections``)
and the adapter the composition root serves in recorded mode -- ``RecordedAdapter()``, no
directory -- each case below runs on the lane's own PostgreSQL and MinIO:

* classify the seeded version (stage ``P``, section X) -> ``start_audit_run`` with the
  registry's route table -> the run pins X's ``analysis_profile_id`` and
  ``prompt_bundle_id`` -> ``execute_run`` with the registry's resolver reaches
  ``published``; the text stage's persisted metrics carry X's prompt-bundle and profile
  hashes and the request key of X's recording, and the published findings are exactly the
  observations of X's recording, under X's pair, in ``recorded`` mode;
* ``PB`` is refused at run start (``section_profile_unavailable``) and
  an unclassified version is refused with ``version_classification_required``; neither writes a run;
* the АИ recording does not answer a ПЗ run: over the АИ directory alone the run ends
  ``failed`` with ``recording_missing``, and the АИ file filed under the ПЗ key ends it
  with ``recording_key_mismatch``; no finding is published either way.

The recordings are synthetic (their ``origin`` says so); passing here proves routing and
parsing, never a profile's quality.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import RecordedAdapter
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.findings import published_findings
from auditmanager.runs import PC01_STAGES, execute_run, start_audit_run
from auditmanager.sections.public import classify_document_version
from auditmanager.shared.errors import DomainError, ErrorCode

REGISTRY = load_text_profile_registry()
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SECTION_RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections"
RECORDED_SECTIONS = ("AI", "PS", "POS", "TX")


def _classify(session: Session, seeded: Any, code: str) -> None:
    from am_test_accounts import provisioned_record

    classify_document_version(
        session,
        project_uid=seeded.project_uid,
        document_uid=seeded.document_uid,
        version_uid=seeded.version_uid,
        project_stage="P",
        section_code=code,
        actor_uid=str(provisioned_record("w59-section-profile-recorded").user_uid),
        actor_roles=frozenset({"expert"}),
    )


def _start(session: Session, seeded: Any, key: str) -> str:
    return start_audit_run(
        session,
        version_uid=seeded.version_uid,
        provider_mode="recorded",
        idempotency_key=key,
        section_profiles=REGISTRY.section_profiles(),
    ).run_id


def _recording(code: str) -> tuple[str, dict[str, Any]]:
    """The one recording of ``code``: its key (the file name) and its document."""
    (path,) = sorted((SECTION_RECORDINGS / code.lower()).glob("*.json"))
    return path.stem, json.loads(path.read_text(encoding="utf-8"))


def _runs_of(session: Session, version_uid: str) -> int:
    return int(
        session.execute(
            text("SELECT count(*) FROM audit_run WHERE version_uid = :v"), {"v": version_uid}
        ).scalar_one()
    )


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_a_classified_section_runs_to_published_with_its_own_profile_and_recording(
    session: Session, seeded, blob_store, provider_config, new_key, helpers, code: str
) -> None:
    entry = REGISTRY.entries[code]
    key, recording = _recording(code)
    assert recording["origin"]["kind"] == "synthetic"

    _classify(session, seeded, code)
    run_id = _start(session, seeded, new_key(f"w59-section-recorded-{code}"))

    pinned = session.execute(
        text("SELECT analysis_profile_id, prompt_bundle_id FROM audit_run WHERE run_id = :r"),
        {"r": run_id},
    ).one()
    assert tuple(pinned) == (entry.analysis_profile_id, entry.prompt_bundle_id)

    # The adapter the composition root builds in recorded mode, not a directory picked here.
    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=RecordedAdapter(),
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    assert result.terminal_state == "published", (
        dict(result.stage_statuses), result.degradation_set,
    )
    assert helpers.run_state_of(session, run_id) == "published"
    assert set(result.stage_statuses) == set(PC01_STAGES)
    assert set(result.stage_statuses.values()) == {"succeeded"}

    metrics = session.execute(
        text(
            "SELECT metrics FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'"
        ),
        {"r": run_id},
    ).scalar_one()
    assert metrics["prompt_bundle_sha256"] == entry.profile.prompt_bundle.content_sha256
    assert metrics["analysis_profile_sha256"] == entry.profile.content_sha256
    assert metrics["request_sha256"] == key
    assert metrics["provider_mode"] == "recorded"
    assert recording["origin"]["prompt_bundle_sha256"] == metrics["prompt_bundle_sha256"]

    expected = json.loads(recording["output_text"])["observations"]
    findings = published_findings(session, run_id)
    assert result.published_finding_count == len(expected) == len(findings)
    assert sorted(f.finding_text for f in findings) == sorted(o["finding_text"] for o in expected)
    for finding in findings:
        assert (finding.analysis_profile_id, finding.prompt_bundle_id) == (
            entry.analysis_profile_id, entry.prompt_bundle_id,
        )
        assert finding.provider_mode == "recorded"
        assert finding.finding_text.startswith("Синтетический ответ (")


def test_a_pb_version_is_refused_at_run_start_without_a_substitute(
    session: Session, seeded, new_key
) -> None:
    assert "PB" not in REGISTRY.entries
    _classify(session, seeded, "PB")
    with pytest.raises(DomainError) as refused:
        _start(session, seeded, new_key("w59-section-recorded-PB"))
    assert refused.value.code is ErrorCode.SECTION_PROFILE_UNAVAILABLE
    assert refused.value.detail_fields == {}
    assert _runs_of(session, seeded.version_uid) == 0


def test_an_unclassified_version_is_refused_at_run_start(
    session: Session, seeded, new_key
) -> None:
    with pytest.raises(DomainError) as refused:
        _start(session, seeded, new_key("w59-section-recorded-unclassified"))
    assert refused.value.code is ErrorCode.VERSION_CLASSIFICATION_REQUIRED
    assert refused.value.detail_fields == {}
    assert _runs_of(session, seeded.version_uid) == 0


def _failed_with(session: Session, run_id: str, result: Any, reason: str) -> None:
    assert result.terminal_state == "failed", dict(result.stage_statuses)
    row = session.execute(
        text("SELECT state, terminal_reason, terminal_detail FROM audit_run WHERE run_id = :r"),
        {"r": run_id},
    ).mappings().one()
    assert row["state"] == "failed"
    assert row["terminal_reason"] == ErrorCode.ANALYSIS_INPUT_INVALID.value
    assert row["terminal_detail"]["stage_id"] == "text_analysis"
    assert row["terminal_detail"]["reason"] == reason
    assert published_findings(session, run_id) == ()


def test_the_ai_recording_does_not_answer_a_ps_run(
    session: Session, seeded, blob_store, provider_config, new_key, tmp_path: Path
) -> None:
    ai_key, _ = _recording("AI")
    ps_key, _ = _recording("PS")
    assert ai_key != ps_key

    _classify(session, seeded, "PS")

    # Only the АИ directory: the ПЗ request's key is not there.
    first = _start(session, seeded, new_key("w59-ps-over-ai-directory"))
    result = execute_run(
        session, first, blob_store=blob_store,
        adapter=RecordedAdapter(SECTION_RECORDINGS / "ai"),
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    _failed_with(session, first, result, "recording_missing")

    # The АИ reply filed under the ПЗ key: it declares the АИ key, so it is not replayed.
    forged = tmp_path / "ai-under-ps-key"
    forged.mkdir()
    shutil.copyfile(SECTION_RECORDINGS / "ai" / f"{ai_key}.json", forged / f"{ps_key}.json")
    second = _start(session, seeded, new_key("w59-ps-over-forged-ai"))
    result = execute_run(
        session, second, blob_store=blob_store, adapter=RecordedAdapter(forged),
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    _failed_with(session, second, result, "recording_key_mismatch")
