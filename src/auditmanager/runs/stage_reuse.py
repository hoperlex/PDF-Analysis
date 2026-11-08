"""Which completed stage outputs of an earlier run a new run may reuse (`R-151i`, `UI-A-60`, `D-301`).

A run started from a stage is a **new** run that takes the earlier run's outputs of every PC-01 stage *before* the chosen
one and computes the rest (``docs/program/RUN-FROM-STAGE-01.md``). This module is the one place that decides whether an
output may be taken. It is read twice with the same arguments -- when the cost is estimated and the start is accepted
(``runs.commands.start_run_from_stage``) and again when the executor materialises the reuse -- and it only ever answers
«yes, here are the outputs» or refuses with a typed reason. It never recomputes, never substitutes and never falls back
(AGENTS section 4: no silent fallback).

The rule, per reused stage, in the registry's order (the first stage that fails names the refusal):

1. the source run has a ``stage_result`` for it with status ``succeeded`` (``source_stage_not_completed``);
2. its ``stage_version`` is the version this deployment's registry declares today (``source_stage_version_changed``) --
   an output of an older algorithm is not the output a fresh run would produce;
3. its artifacts carry every output role the registry requires of that stage (``source_stage_output_incomplete``);
4. each artifact is still an ``available`` blob whose recorded sha256 and size are the artifact reference's
   (``source_artifact_unavailable``, ``source_artifact_changed``);
5. the one input of the deterministic stages that is not the version's own bytes -- whether the run's accepted consent
   lets pages without a text layer through (``extended-review-v3``) -- is the same for the source and the new run
   (``source_stage_inputs_changed``).

What the rule deliberately does **not** compare: the analysis profile, the prompt bundle and the norms snapshot. The
three stages before ``text_analysis`` read none of them (their handlers receive blob inputs and the version identity and
nothing else), while ``text_analysis`` -- the only stage that reads them -- is always among the stages the new run
computes. The new run therefore records today's configuration, exactly as a re-audit does (`R-82`), and reuses only what
that configuration cannot change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Mapping

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ArtifactRef, StageResult, StageStatus, default_registry
from auditmanager.ingest.public import CommandRepository
from auditmanager.runs.repository import PC01_STAGES, RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId
from auditmanager.storage.public import BlobMetadataRepository, parse_blob_id

#: The stages a run may be started from: every PC-01 stage after the first. A start at the first stage reuses nothing and
#: is a re-audit; the stages PC-01 does not schedule have nothing to start.
STARTABLE_STAGES: Final[tuple[str, ...]] = PC01_STAGES[1:]

#: The metric every reused ``stage_result`` row carries: the run whose output it is. The executor writes it and nothing
#: else does, so a reader can tell a reused row from a computed one.
REUSED_FROM_METRIC: Final[str] = "reused_from_run_id"

#: ``analysis_input_invalid.reason`` of each refusal (`stage_id` names the stage that cannot be taken).
REASON_NOT_COMPLETED: Final[str] = "source_stage_not_completed"
REASON_VERSION_CHANGED: Final[str] = "source_stage_version_changed"
REASON_OUTPUT_INCOMPLETE: Final[str] = "source_stage_output_incomplete"
REASON_ARTIFACT_UNAVAILABLE: Final[str] = "source_artifact_unavailable"
REASON_ARTIFACT_CHANGED: Final[str] = "source_artifact_changed"
REASON_INPUTS_CHANGED: Final[str] = "source_stage_inputs_changed"
REASONS: Final[tuple[str, ...]] = (
    REASON_NOT_COMPLETED, REASON_VERSION_CHANGED, REASON_OUTPUT_INCOMPLETE,
    REASON_ARTIFACT_UNAVAILABLE, REASON_ARTIFACT_CHANGED, REASON_INPUTS_CHANGED,
)

_EXTENDED_REVIEW_V3: Final[str] = "extended-review-v3"


def visual_only_pages_allowed(extended_review: Mapping[str, Any] | None) -> bool:
    """Whether an accepted consent's extended-review plan lets a page without a text layer through the early stages.

    The executor's ``v3_workflow``: ``source_preparation`` and ``document_context_build`` run with
    ``allow_visual_only_pages`` exactly when the run's consent carries the ``extended-review-v3`` plan. One definition,
    read by the executor and by the reuse rule."""
    return isinstance(extended_review, dict) and extended_review.get("plan_version") == _EXTENDED_REVIEW_V3


def require_startable_stage(stage_id: Any) -> str:
    """The stage a run is started from, or ``validation_failed`` on ``stage_id`` (nothing is read or written)."""
    if not isinstance(stage_id, str) or stage_id not in STARTABLE_STAGES:
        constraint = "nothing_to_reuse" if stage_id == PC01_STAGES[0] else "stage_not_startable"
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_id", constraint=constraint)
    return stage_id


@dataclass(frozen=True, slots=True)
class ReusedStage:
    """One source stage whose output the new run takes by reference."""

    stage_id: str
    stage_version: str
    artifacts: tuple[ArtifactRef, ...]
    #: The source row's scalar metrics (page counts and the like), carried so a reader of the new run's rows sees the
    #: facts of the output it was given.
    metrics: Mapping[str, Any]

    def as_stage_result(self, *, source_run_id: str, at: datetime) -> StageResult:
        """The new run's own ``stage_result`` for this stage: ``succeeded``, the same artifact references, marked as reused.

        Both times are the moment of reuse; the span the source spent computing it belongs to the source run."""
        return StageResult(
            stage_id=self.stage_id, stage_version=self.stage_version, status=StageStatus.SUCCEEDED,
            artifacts=self.artifacts, metrics={**self.metrics, REUSED_FROM_METRIC: source_run_id},
            started_at=at, finished_at=at,
        )


@dataclass(frozen=True, slots=True)
class StageReusePlan:
    """What a start from ``start_stage_id`` of ``source_run_id`` takes and what it computes."""

    source_run_id: str
    start_stage_id: str
    reused: tuple[ReusedStage, ...]
    #: The PC-01 stages the new run computes: the chosen one and every later one.
    computed_stage_ids: tuple[str, ...]

    @property
    def reused_stage_ids(self) -> tuple[str, ...]:
        return tuple(stage.stage_id for stage in self.reused)


def _refuse(stage_id: str, reason: str) -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id=stage_id, reason=reason)


def run_visual_only_pages(session: Session, run_id: str, *, runs: RunRepository | None = None) -> bool:
    """The flag of an earlier run, read from the consent its start accepted (``False`` for a run with no consent)."""
    run = (runs or RunRepository()).get(session, run_id)
    if run.command_id is None:
        return False
    command = CommandRepository().get(session, CommandId.parse(run.command_id))
    consent = (command.outcome or {}).get("cost_consent")
    return visual_only_pages_allowed(consent.get("extended_review") if isinstance(consent, dict) else None)


def _artifacts_of(stage_id: str, row: StageResultRow) -> tuple[ArtifactRef, ...]:
    try:
        return tuple(ArtifactRef(**dict(item)) for item in row.artifacts)
    except (TypeError, ValueError):
        raise _refuse(stage_id, REASON_ARTIFACT_CHANGED) from None


def plan_stage_reuse(
    session: Session, *, source_run_id: str, start_stage_id: str, visual_only_pages: bool,
    runs: RunRepository | None = None, blobs: BlobMetadataRepository | None = None,
) -> StageReusePlan:
    """The outputs a run started from ``start_stage_id`` of ``source_run_id`` reuses, or the first typed refusal.

    ``visual_only_pages`` is the new run's own flag (:func:`visual_only_pages_allowed` of the consent it accepts). The
    source must exist (``not_found``); that it is terminal, and of the standard analysis, is the command's concern."""
    require_startable_stage(start_stage_id)
    repository = runs or RunRepository()
    metadata = blobs or BlobMetadataRepository()
    repository.get(session, source_run_id)
    stored = {row.stage_id: row for row in repository.stage_results(session, source_run_id)}
    registry = default_registry()
    position = PC01_STAGES.index(start_stage_id)
    reused: list[ReusedStage] = []
    for stage_id in PC01_STAGES[:position]:
        row = stored.get(stage_id)
        if row is None or row.status != StageStatus.SUCCEEDED.value:
            raise _refuse(stage_id, REASON_NOT_COMPLETED)
        definition = registry.stage(stage_id)
        if row.stage_version != definition.stage_version:
            raise _refuse(stage_id, REASON_VERSION_CHANGED)
        artifacts = _artifacts_of(stage_id, row)
        if definition.missing_outputs(frozenset(ref.role for ref in artifacts)):
            raise _refuse(stage_id, REASON_OUTPUT_INCOMPLETE)
        for ref in artifacts:
            record = metadata.get(session, parse_blob_id(ref.blob_id))
            if record is None or not record.is_available:
                raise _refuse(stage_id, REASON_ARTIFACT_UNAVAILABLE)
            if record.sha256 != ref.sha256 or record.size_bytes != ref.size_bytes:
                raise _refuse(stage_id, REASON_ARTIFACT_CHANGED)
        reused.append(ReusedStage(
            stage_id=stage_id, stage_version=row.stage_version, artifacts=artifacts,
            metrics={key: value for key, value in dict(row.metrics).items()
                     if isinstance(value, (str, int, float, bool)) or value is None},
        ))
    if run_visual_only_pages(session, source_run_id, runs=repository) != bool(visual_only_pages):
        raise _refuse(PC01_STAGES[0], REASON_INPUTS_CHANGED)
    return StageReusePlan(
        source_run_id=source_run_id, start_stage_id=start_stage_id, reused=tuple(reused),
        computed_stage_ids=PC01_STAGES[position:],
    )


__all__ = [
    "REASONS",
    "REUSED_FROM_METRIC",
    "STARTABLE_STAGES",
    "ReusedStage",
    "StageReusePlan",
    "plan_stage_reuse",
    "require_startable_stage",
    "run_visual_only_pages",
    "visual_only_pages_allowed",
]
