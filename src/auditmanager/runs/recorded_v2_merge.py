"""Unactivated durable AR v2 finding-merge stage for a saved recorded run.

This stage consumes the already published observation Blob. It never reads a
recording, invokes a model or publishes finding rows. The future executor owns
terminal selection and finding publication after this stage has committed.
"""

from __future__ import annotations

from hashlib import sha256
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ArtifactRef,
    MERGE_ARTIFACT_ROLE,
    MERGE_ARTIFACT_VERSION,
    RecordedArtifactError,
    StageResult,
    StageStatus,
    default_registry,
    merge_grounded,
    publish_artifact,
    read_recorded_merge_input,
)
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.executor import _persist_and_bind, _publication_store
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import (
    BlobMetadataRepository, BlobStore, derive_blob_id, parse_blob_id,
)


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the saved recorded text stage cannot support finding merge",
        stage_id="finding_merge",
        reason=reason,
    )


def _text_reference(rows: tuple) -> ArtifactRef:
    text_stage = default_registry().stage("text_analysis")
    matches = tuple(row for row in rows if row.stage_id == text_stage.stage_id)
    if len(matches) != 1:
        raise _refuse("text_stage_result_missing_or_duplicate")
    row = matches[0]
    if (row.status != StageStatus.SUCCEEDED.value
            or row.stage_version != text_stage.stage_version
            or len(row.artifacts) != 1):
        raise _refuse("text_stage_not_complete")
    try:
        reference = ArtifactRef(**dict(row.artifacts[0]))
    except (TypeError, ValueError):
        raise _refuse("text_reference_invalid") from None
    if reference.role != "analysis.text_observations":
        raise _refuse("text_reference_invalid")
    return reference


def _source_references(rows: tuple) -> tuple[ArtifactRef, ArtifactRef | None]:
    source_stage = default_registry().stage("source_preparation")
    matches = tuple(row for row in rows if row.stage_id == source_stage.stage_id)
    if len(matches) != 1:
        raise _refuse("source_stage_result_missing_or_duplicate")
    row = matches[0]
    if row.status != StageStatus.SUCCEEDED.value or row.stage_version != source_stage.stage_version:
        raise _refuse("source_stage_not_complete")
    references: dict[str, ArtifactRef] = {}
    for raw in row.artifacts:
        try:
            reference = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise _refuse("source_reference_invalid") from None
        if reference.role in references:
            raise _refuse("source_reference_duplicate")
        references[reference.role] = reference
    text_ref = references.get("prepared.text_layer")
    if text_ref is None:
        raise _refuse("text_layer_reference_missing")
    return text_ref, references.get("prepared.recognised_text")


def run_recorded_v2_merge_stage(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
    clock: Clock = _utc_now,
) -> StageResult:
    """Persist one deterministic merge Blob and StageResult under a current Attempt.

    The saved text artifact has its own v2 reader. Reading it occurs before
    taking Job/Attempt locks. After the read, authority and StageResults are
    checked again; no stage effect is started from stale evidence. Blob intent
    commits precede external writes, and exact readback precedes success.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    blob_repo = blobs or BlobMetadataRepository()
    run_id = authority.run_id
    run = run_repo.get(session, run_id)
    if run.state != "running" or run.provider_mode != "recorded":
        raise _refuse("recorded_running_run_required")
    before = run_repo.stage_results(session, run_id)
    if any(row.stage_id == "finding_merge" for row in before):
        raise DomainError(ErrorCode.CONFLICT, message="finding merge already has a stage result")
    text_ref = _text_reference(before)
    source_refs = _source_references(before)
    try:
        prepared = read_recorded_merge_input(
            blob_store, text_ref, run_id=run_id, version_uid=run.version_uid,
            analysis_profile_id=run.analysis_profile_id,
            prompt_bundle_id=run.prompt_bundle_id,
        )
    except (RecordedArtifactError, TypeError, ValueError) as exc:
        raise _refuse("recorded_observation_artifact_invalid") from exc
    if (prepared.text_layer_ref, prepared.recognised_ref) != source_refs:
        raise _refuse("recorded_source_reference_mismatch")

    job_repo.require_current(session, authority)
    current = run_repo.get(session, run_id)
    after = run_repo.stage_results(session, run_id)
    if (current.state != "running" or current != run
            or any(row.stage_id == "finding_merge" for row in after)
            or _text_reference(after) != text_ref
            or _source_references(after) != source_refs):
        raise DomainError(ErrorCode.CONFLICT, message="recorded merge inputs changed during read")

    document = merge_grounded(prepared.observations)
    definition = default_registry().stage("finding_merge")
    if (document.get("artifact_role") != MERGE_ARTIFACT_ROLE
            or document.get("artifact_version") != MERGE_ARTIFACT_VERSION
            or not definition.succeeded_requires_all_required_outputs
            or definition.missing_outputs(frozenset({MERGE_ARTIFACT_ROLE}))):
        raise _refuse("merge_registry_output_mismatch")
    started_at = clock()
    run_repo.stage_started(session, run_id=run_id, stage_id=definition.stage_id)
    session.commit()

    publication_store = _publication_store(
        session, store=blob_store, jobs=job_repo, blobs=blob_repo,
        authority=authority, stage_id=definition.stage_id,
    )
    reference, payload = publish_artifact(publication_store, MERGE_ARTIFACT_ROLE, document)
    if (reference.sha256 != sha256(payload).hexdigest()
            or reference.size_bytes != len(payload)
            or reference.media_type != "application/json"
            or reference.blob_id != str(derive_blob_id(
                sha256=reference.sha256, size=reference.size_bytes,
            ))):
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            message="merge Blob publication returned metadata for different bytes",
            blob_id=reference.blob_id, role=reference.role,
        )
    readback = publication_store.read(parse_blob_id(reference.blob_id), verify=True)
    if readback != payload:
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            message="merge Blob readback differed from published bytes",
            blob_id=reference.blob_id, role=reference.role,
        )
    result = StageResult(
        stage_id=definition.stage_id,
        stage_version=definition.stage_version,
        status=StageStatus.SUCCEEDED,
        artifacts=(reference,),
        metrics={
            "group_count": len(document["groups"]),
            "observation_count": len(prepared.observations),
            "text_artifact_sha256": prepared.text_artifact_sha256,
        },
        started_at=started_at,
        finished_at=clock(),
    )
    result.to_document()
    _persist_and_bind(
        session, runs=run_repo, jobs=job_repo, blobs=blob_repo,
        authority=authority, run_id=run_id, result=result,
    )
    session.commit()
    return result


__all__ = ["run_recorded_v2_merge_stage"]
