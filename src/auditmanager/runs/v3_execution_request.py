"""Read-only AR v3 request preparation under a current Job Attempt.

This operation checks the group's installed pack, reads the current Run's saved
source-stage text and confirmed set Blob, and rechecks the same group pins
before returning exact transport bytes. A later dispatch must recheck authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ModelRequest,
    RecognisedContext,
    SealedV3Request,
    V3GenerationSettings,
    build_v3_model_request,
    prepare_beta_v3_request,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.reference_text_input import (
    SavedReferenceTextInput,
    load_saved_reference_text,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_citations import PinnedV3CorpusRequest, prepare_v3_corpus_request
from auditmanager.runs.v3_execution_binding import (
    V3ExecutionBinding,
    resolve_v3_execution_binding,
)
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore


@dataclass(frozen=True, slots=True)
class V3PreparedExecutionRequest:
    binding: V3ExecutionBinding
    saved_text: SavedReferenceTextInput
    pinned_corpus: PinnedV3CorpusRequest
    sealed: SealedV3Request
    model_request: ModelRequest

    @property
    def candidate_sha256(self) -> str:
        return self.sealed.candidate.request_sha256

    @property
    def provider_body_sha256(self) -> str:
        return self.model_request.request_sha256


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.REQUIRED_NORM_UNAVAILABLE,
        reference_kind="norm_retrieval_set",
        reason=reason,
    )


def prepare_v3_execution_request(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    blob_store: BlobStore,
    max_text_bytes: int,
    expected_provider_mode: str,
    model_identity: str,
    settings: V3GenerationSettings,
    idempotency_scope: str | None = None,
    recognised_context: tuple[RecognisedContext, ...] = (),
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
) -> V3PreparedExecutionRequest:
    """Build one provider body from the persisted Run and verified set bytes.

    No provider, Blob write or database write occurs here. The text layer is
    read only from this Run's saved deterministic source stage and checked
    against its Version and Blob. The explicit byte ceiling bounds that read.
    """
    job_repo = jobs or JobRepository()
    run_repo = runs or RunRepository()
    binding = resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    )
    if (expected_provider_mode not in {"live", "recorded"}
            or binding.provider_mode != expected_provider_mode):
        raise _refuse("provider_mode_mismatch")
    saved_text = load_saved_reference_text(
        session, authority=authority, blob_store=blob_store,
        max_input_bytes=max_text_bytes, runs=run_repo, jobs=job_repo,
        documents=documents,
    )
    text_layer = saved_text.text_layer
    run = run_repo.get(session, binding.run_id)
    if (run.state != "running"
            or run.project_uid != binding.project_uid
            or run.version_uid != binding.version_uid
            or run.frozen_input_digest != binding.frozen_input_digest
            or saved_text.version_uid != binding.version_uid
            or text_layer.version_uid != binding.version_uid):
        raise _refuse("run_or_text_binding_mismatch")
    pinned = prepare_v3_corpus_request(
        session, run=run, authority=authority, blob_store=blob_store,
        text_layer=text_layer, profile_id=binding.analysis_profile_id,
        bundle_id=binding.prompt_bundle_id, map_sha256=binding.map_sha256,
        scope_id=binding.scope_id,
        composition_sha256=binding.composition_sha256,
        recognised_context=recognised_context,
    )
    verified = pinned.verified_set
    if (verified.run_id != binding.run_id
            or verified.norms_snapshot_id != binding.norms_snapshot_id
            or verified.norm_retrieval_set_id != binding.norm_retrieval_set_id
            or verified.map_sha256 != binding.map_sha256
            or verified.set_sha256 != binding.set_sha256):
        raise _refuse("verified_set_binding_mismatch")
    sealed = prepare_beta_v3_request(
        text_layer, verified.data,
        analysis_profile_id=binding.analysis_profile_id,
        prompt_bundle_id=binding.prompt_bundle_id,
        expected_version_uid=binding.version_uid,
        expected_set_sha256=binding.set_sha256,
        expected_snapshot_id=binding.norms_snapshot_id,
        expected_map_sha256=binding.map_sha256,
        scope_id=binding.scope_id,
        expected_composition_sha256=binding.composition_sha256,
        recognised_context=recognised_context,
    )
    if sealed.candidate != pinned.candidate:
        raise _refuse("candidate_rebinding_mismatch")
    request = build_v3_model_request(
        sealed, model_identity=model_identity, settings=settings,
        idempotency_scope=idempotency_scope,
    )
    if resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    ) != binding:
        raise _refuse("group_binding_changed_during_read")
    return V3PreparedExecutionRequest(binding, saved_text, pinned, sealed, request)


__all__ = ["V3PreparedExecutionRequest", "prepare_v3_execution_request"]
