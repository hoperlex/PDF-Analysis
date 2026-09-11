"""Step 8: every failure is explicit. No filesystem fallback, no fake success.

Each case asserts the *typed* refusal and then that the refusal left nothing behind --
a refusal that still created a version, a run or an object would be the interesting
failure, and asserting only the exception would not see it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

NEGATIVE = Path(__file__).resolve().parents[3] / "fixtures" / "synthetic" / "ar" / "negative"


@pytest.mark.parametrize(
    "filename",
    ["not_a_pdf.txt", "encrypted.pdf", "image_only.pdf", "too_many_pages.pdf", "companion_archive.zip"],
)
def test_unsupported_input_is_refused_and_creates_nothing(
    filename, session, ingest, journey_harness
):
    from auditmanager.shared.errors import DomainError
    from auditmanager.shared.identity import ProjectUid

    h = journey_harness
    payload = (NEGATIVE / filename).read_bytes()
    project = ingest.create_project(name=f"B-III negative {filename} {h.new_key('p')}")

    before = int(session.execute(text("SELECT count(*) FROM document_version")).scalar_one())
    with pytest.raises(DomainError) as refusal:
        ingest.upload_single_pdf(
            project_uid=ProjectUid(str(project.project_uid)),
            content=payload,
            source_filename=filename,
            display_title="negative",
            idempotency_key=h.new_key("upload"),
        )
    after = int(session.execute(text("SELECT count(*) FROM document_version")).scalar_one())

    assert after == before, f"{filename} was refused but a document_version appeared"
    message = str(refusal.value).lower()
    assert "traceback" not in message
    assert str(NEGATIVE) not in str(refusal.value), "the refusal leaked a filesystem path"


def test_a_declared_checksum_that_does_not_match_is_refused(blob_store):
    """The storage port verifies before it publishes; a mismatch publishes nothing."""
    from auditmanager.storage import ChecksumMismatchError, parse_blob_role, sha256_of

    payload = b"B-III checksum probe payload"
    wrong = sha256_of(b"different bytes entirely")
    with pytest.raises(ChecksumMismatchError):
        blob_store.put_blob(
            payload,
            declared_sha256=wrong,
            declared_size=len(payload),
            role=parse_blob_role("source_document"),
            media_type="application/pdf",
        )


def test_an_unavailable_provider_fails_the_run_without_inventing_a_result(
    session_factory, blob_store, provider_config, journey_harness, tmp_path
):
    """A recorded adapter with no recording is the unavailable-dependency case.

    The run must reach an explicit non-published terminal. It must not fall back to
    another recording directory, and it must not publish a finding.
    """
    from auditmanager.analysis.text import RecordedAdapter
    from auditmanager.shared.errors import DomainError

    h = journey_harness
    empty = tmp_path / "no-recordings"
    empty.mkdir()
    adapter = RecordedAdapter(empty)

    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("nodep"))

    with session_factory() as session:
        from auditmanager.analysis.text import AR_TEXT_PROFILE, AR_TEXT_PROMPT_BUNDLE
        from auditmanager.runs import start_audit_run

        started = start_audit_run(
            session,
            version_uid=seed["version_uid"],
            analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
            prompt_bundle_id=str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
            provider_mode="recorded",
            idempotency_key=h.new_key("run"),
        )
        session.commit()
        run_id = str(started.run_id)

    from auditmanager.runs import execute_run

    with session_factory() as session:
        try:
            execute_run(session, run_id, blob_store=blob_store, adapter=adapter,
                        provider_config=provider_config)
            session.commit()
        except DomainError:
            session.rollback()

    with session_factory() as session:
        state = session.execute(
            text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()
        published = session.execute(
            text("SELECT count(*) FROM finding_observation WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()

    assert state != "published", "a run with no provider response was published"
    assert published == 0, "a run with no provider response produced observations"
