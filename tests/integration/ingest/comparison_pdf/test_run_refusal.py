"""`CMP-INGEST-01`: a section analysis never starts on a comparison-only version (ADR-0025 decision 11, ``Q-CMP-5``).

``startRun`` and ``reauditRun`` refuse a version whose ``upload_kind`` is ``comparison_pdf`` with
``analysis_input_invalid``, reason ``comparison_only_version``, **before** the profile is routed and **before** any key is
claimed, so the refusal writes nothing. The manifest check that already existed refuses the same version with another reason
(``missing_required_input``: the version has no ``source.document`` entry); the new reason is asked first, by the kind, because a
reviewer reads it in Russian and the other says a fault where the truth is a kind. Each is shown failing against the other.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest import CommandRepository
from auditmanager.ingest.comparison_pdf.public import ConfirmedFile
from auditmanager.runs import RunRepository, start_audit_run
from auditmanager.runs.commands import COMPARISON_ONLY_VERSION_REASON, reaudit_run, refuse_comparison_only_version
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey
from tests.integration.ingest.comparison_pdf.support import EXPERT, table, upload_batch, vs1

PROFILE = "ap_01ARZ3NDEKTSV4RRFFQ69G5FAV"
BUNDLE = "pb_01ARZ3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture
def comparison_version(comparison, project, user, session_factory):
    view = upload_batch(comparison, str(project.project_uid), {"a.pdf": vs1()["v1.pdf"]}, user=user)
    proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
    done = comparison.confirm_set(
        upload_id=view.upload_id, set_id=proposed.set_id, files=[ConfirmedFile(f.file_id) for f in proposed.files],
        designation=None, existing_document_uid=None, project_stage="R", section_code="AR", user_uid=user,
        actor_roles=EXPERT, idempotency_key="confirm")
    with session_factory() as session:
        return DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))[0]


def _written(factory: sessionmaker[Session]) -> list[int]:
    with factory() as session:
        return [table(session, f"SELECT count(*) FROM {name}")[0][0] for name in ("audit_run", "command_record", "job")]


class TestStartRun:
    def test_a_comparison_version_is_refused_by_its_kind_with_the_registered_reason(self, comparison_version, session_factory) -> None:
        before = _written(session_factory)
        with session_factory() as session:
            with pytest.raises(DomainError) as refused:
                start_audit_run(session, version_uid=comparison_version.version_uid, analysis_profile_id=PROFILE,
                                prompt_bundle_id=BUNDLE, provider_mode="recorded", idempotency_key=IdempotencyKey("start-1"))
        assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        assert refused.value.detail_fields == {"reason": COMPARISON_ONLY_VERSION_REASON} == {"reason": "comparison_only_version"}
        assert _written(session_factory) == before, "the refusal wrote a run, a command or a job"

    def test_the_refusal_is_before_the_profile_is_routed(self, comparison_version, session_factory) -> None:
        """With the section table in hand the version is classified AR, and routing would have answered something else
        (no profile registered in this suite); the kind is asked first."""
        with session_factory() as session:
            with pytest.raises(DomainError) as refused:
                start_audit_run(session, version_uid=comparison_version.version_uid, provider_mode="recorded",
                                idempotency_key=IdempotencyKey("start-2"), section_profiles={})
        assert refused.value.detail_fields == {"reason": "comparison_only_version"}

    def test_the_manifest_check_alone_would_have_said_missing_required_input(self, comparison_version) -> None:
        """The same version, with the kind forgotten: the old rule still refuses it, with the reason of a fault.

        This is the behaviour the new reason replaces; it also shows that the manifest role of a comparison version
        is distinct from ``source.document``, which is what keeps every other reader of the run's input safe."""
        from dataclasses import replace

        from auditmanager.runs.commands import _resolve_references

        forgotten = replace(comparison_version, upload_kind="portal_bundle")
        with pytest.raises(DomainError) as refused:
            _resolve_references(None, version_uid=comparison_version.version_uid, analysis_profile_id=PROFILE,
                                prompt_bundle_id=BUNDLE, documents=DocumentRepository(), version=forgotten)  # type: ignore[arg-type]
        assert refused.value.detail_fields == {"reason": "missing_required_input"}

    def test_the_reference_check_every_start_passes_through_asks_the_kind_too(self, comparison_version) -> None:
        """Defence in depth: the one function that resolves a run's references (``start_audit_run`` and
        ``reaudit_run`` both call it) refuses by the kind as well, so a start that reached it by another road cannot
        read the manifest of a comparison-only version."""
        from auditmanager.runs.commands import _resolve_references

        with pytest.raises(DomainError) as refused:
            _resolve_references(None, version_uid=comparison_version.version_uid, analysis_profile_id=PROFILE,  # type: ignore[arg-type]
                                prompt_bundle_id=BUNDLE, documents=DocumentRepository(), version=comparison_version)
        assert refused.value.detail_fields == {"reason": "comparison_only_version"}

    def test_a_portal_version_is_not_refused_by_this_rule(self, comparison_version) -> None:
        from dataclasses import replace

        refuse_comparison_only_version(replace(comparison_version, upload_kind="portal_bundle"))
        with pytest.raises(DomainError):
            refuse_comparison_only_version(comparison_version)


class TestReauditRun:
    def test_a_source_run_on_a_comparison_version_cannot_be_repeated(self, comparison_version, project, session_factory) -> None:
        """Such a run could not have been started; one is made here by hand (the row exists only to be named)."""
        with session_factory() as session:
            commands = CommandRepository()
            started = commands.begin(session, command_type="start_audit_run", idempotency_key=IdempotencyKey("seed"),
                                     fingerprint=__import__("auditmanager.ingest.public", fromlist=["payload_fingerprint"]).payload_fingerprint({"seed": 1}))
            RunRepository().create(
                session, run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAV", project_uid=str(project.project_uid),
                version_uid=str(comparison_version.version_uid), analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
                provider_mode="recorded", frozen_input_digest="0" * 64, command_id=str(started.command_id))
            session.commit()
        before = _written(session_factory)
        with session_factory() as session:
            with pytest.raises(DomainError) as refused:
                reaudit_run(session, source_run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAV", roles=frozenset({"expert"}),
                            idempotency_key="again-1", analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE, provider_mode="recorded")
        assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        assert refused.value.detail_fields == {"reason": "comparison_only_version"}
        assert _written(session_factory) == before
