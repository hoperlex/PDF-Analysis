"""The saved text observations a restart takes **byte for byte** (`RUN-RESTART-01`, `R-155f`).

A restart from a chip after «Текст» does not run the text stage again: it takes the source chain's ``analysis.text_observations`` blob as it is. The
blob is never rewritten, copied or re-published, for three reasons that are facts of the code, not of taste:

* its sha256 enters ``source_sha256`` of **every** reply key of the extended review (``analysis/extended/core.py``, through ``plan_extended_inputs`` in
  ``runs/extended_review.py``), so another byte is another key and none of the saved replies of the source replays;
* it carries the ``run_id`` of the run that made it and a ``model_call_id`` on every observation, so a copy "for the new run" would be a different
  blob;
* ``finding_observation.model_call_id`` of the findings the new run publishes therefore points at the **source's** model calls (a foreign key to
  ``model_call``, which the source's rows satisfy) -- by design: the findings come from those calls.

This is the rule of its own that ``stage_reuse.plan_stage_reuse`` cannot be: that rule demands a ``succeeded`` row, and the text row of a
``partial`` source is ``partial`` when only the extended review degraded it (``runs/executor.py``). Here the **artifact** is what must be sound:

* the nearest run of the chain whose text row holds the artifact is the source of the blob (a restart that took the text itself holds it by reference);
* the row's ``stage_version`` is today's (``TEXT_STAGE_VERSION``);
* the blob is an ``available`` blob of the recorded sha256 and size;
* every page was analysed (``pages_analysed == pages_total``): a text that stopped half way is not the text a full run would have produced;
* the provider mode is the run's;
* and, read in the executor where the store is at hand, the document names the run's own analysis profile and prompt bundle and lists exactly the
  pages of the prepared text layer (:func:`reuse_saved_text`).

A refusal is ``analysis_input_invalid`` / ``restart_text_not_reusable`` at the chip ``text``. The visual-pages flag of the early stages is checked by the
preparation reuse (``stage_reuse.plan_stage_reuse``), which this runs after.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ARTIFACT_ROLE as TEXT_OBSERVATIONS_ROLE
from auditmanager.analysis.public import (
    ROLE_TEXT_LAYER, ArtifactRef, StageResult, StageStatus, TEXT_STAGE_VERSION, read_artifact,
)
from auditmanager.runs.repository import RunRepository, RunRow
from auditmanager.runs.restart import REASON_TEXT_NOT_REUSABLE, RestartRefused, refusal
from auditmanager.runs.stage_reuse import REUSED_FROM_METRIC
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import BlobMetadataRepository, parse_blob_id


@dataclass(frozen=True, slots=True)
class SavedText:
    """The text observations of the chain: the run whose row holds the artifact, its reference and the row's scalar metrics."""

    run_id: str
    stage_version: str
    ref: ArtifactRef
    metrics: Mapping[str, Any]


def _not_reusable() -> DomainError:
    return refusal(REASON_TEXT_NOT_REUSABLE, "text")


def find_saved_text(
    session: Session, *, chain: Sequence[str], provider_mode: str,
    runs: RunRepository | None = None, blobs: BlobMetadataRepository | None = None,
) -> SavedText:
    """The text observations a restart takes, or ``restart_text_not_reusable``.

    ``chain`` is the run's source and its ancestors, nearest first (``restart_chain`` of the source). Rows are read; no blob's bytes are."""
    repository = runs or RunRepository()
    metadata = blobs or BlobMetadataRepository()
    for run_id in chain:
        row = next((item for item in repository.stage_results(session, run_id) if item.stage_id == "text_analysis"), None)
        found = None if row is None else next((a for a in row.artifacts if a.get("role") == TEXT_OBSERVATIONS_ROLE), None)
        if row is None or found is None:
            continue  # this run made no text observations (a failed text stage): its own source may hold them
        if row.stage_version != TEXT_STAGE_VERSION:
            raise _not_reusable()
        try:
            ref = ArtifactRef(**dict(found))
        except (TypeError, ValueError):
            raise _not_reusable() from None
        record = metadata.get(session, parse_blob_id(ref.blob_id))
        if record is None or not record.is_available or record.sha256 != ref.sha256 or record.size_bytes != ref.size_bytes:
            raise _not_reusable()
        total, analysed = row.metrics.get("pages_total"), row.metrics.get("pages_analysed")
        if (type(total) is not int or type(analysed) is not int or total != analysed
                or row.metrics.get("provider_mode") not in (None, provider_mode)):
            raise _not_reusable()
        return SavedText(run_id=run_id, stage_version=row.stage_version, ref=ref,
                         metrics={key: value for key, value in dict(row.metrics).items()
                                  if isinstance(value, (str, int, float, bool)) or value is None})
    raise _not_reusable()


def reuse_saved_text(
    session: Session, *, run: RunRow, spec: Any, text_layer_ref: ArtifactRef | None, store: Any, at: datetime,
    runs: RunRepository | None = None, blobs: BlobMetadataRepository | None = None,
) -> tuple[StageResult, dict[str, Any]]:
    """The restart run's own ``text_analysis`` row (``succeeded``, the same artifact reference, marked ``reused_from_run_id``) and the document, read
    from the store and checked against the run. Raises :class:`~auditmanager.runs.restart.RestartRefused` (``restart_text_not_reusable``, chip
    ``text``) when it cannot be taken; nothing is published, nothing is called."""
    try:
        saved = find_saved_text(session, chain=(spec.source_run_id, *spec.ancestors), provider_mode=run.provider_mode, runs=runs, blobs=blobs)
    except DomainError as error:  # the executor wants the workflow's exception, which names the chip the same way
        if error.detail_fields.get("reason") == REASON_TEXT_NOT_REUSABLE:
            raise RestartRefused(REASON_TEXT_NOT_REUSABLE, "text") from None
        raise
    session.commit()
    if text_layer_ref is None:
        raise RestartRefused(REASON_TEXT_NOT_REUSABLE, "text")
    try:
        document, _ = read_artifact(store, parse_blob_id(saved.ref.blob_id), expected_role=TEXT_OBSERVATIONS_ROLE)
        layer, _ = read_artifact(store, parse_blob_id(text_layer_ref.blob_id), expected_role=ROLE_TEXT_LAYER)
    except DomainError:
        raise RestartRefused(REASON_TEXT_NOT_REUSABLE, "text") from None  # a blob that cannot be read as the text is not the text a full run produced
    pages = sorted(page["page_number"] for page in layer.get("pages", []))
    analysed = document.get("pages_analysed")
    if (document.get("analysis_profile_id") != run.analysis_profile_id
            or document.get("prompt_bundle_id") != run.prompt_bundle_id
            or document.get("provider_mode") != run.provider_mode
            or not isinstance(analysed, list) or sorted(analysed) != pages):
        raise RestartRefused(REASON_TEXT_NOT_REUSABLE, "text")
    result = StageResult(
        stage_id="text_analysis", stage_version=saved.stage_version, status=StageStatus.SUCCEEDED, artifacts=(saved.ref,),
        metrics={**saved.metrics, REUSED_FROM_METRIC: saved.run_id}, started_at=at, finished_at=at,
    )
    return result, document


__all__ = ["SavedText", "find_saved_text", "reuse_saved_text"]
