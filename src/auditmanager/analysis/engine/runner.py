"""The in-process stage runner.

This is the seam ``P2-RUN-01`` calls and the only way a stage in this package is
executed. It takes stage inputs by ``blob_id``, resolves canonical identity from the
registry, runs one handler and returns a ``StageResult``.

What it deliberately does not do
--------------------------------
It requires no attempt authority, and it builds no ``JobPackage`` and no
``ResultPackage``. Those envelopes carry attempt authority because they exist to cross
a *remote dispatch* boundary, and ``PC-01`` does not dispatch remotely. Constructing
one here would mean minting an authority for a call that has no boundary to cross.

The fail-closed mapping
-----------------------
Three guards run around every handler, in this order:

1. **Before.** Every ``required_input`` role the registry declares must be supplied.
   A missing one is ``failed`` with ``analysis_input_invalid`` and no artifact - the
   handler is never entered, so it cannot half-succeed.
2. **The handler.** It returns, or it raises ``DomainError``. A raise is ``failed``
   carrying that error's own catalog code; there is no second error type here.
3. **After.** Every ``required_output`` role must be present in what the handler
   produced. A missing one is ``failed`` with ``analysis_failed``, *even though the
   handler returned normally*. A stage that published two of its three required roles
   is not a success with a gap; the registry says
   ``succeeded_requires_all_required_outputs`` and this is where that is enforced.

``partial`` and ``skipped`` have no constructor. :func:`_result_for` is reachable only
with ``SUCCEEDED`` or ``FAILED``, and :func:`assert_status_allowed` refuses any status
the stage's own ``status_policy`` forbids. For the three preparation stages both flags
are false, so even a future caller reaching past the runner is refused by the policy
rather than by a comment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Mapping

from auditmanager.analysis.engine.registry import (
    StageDefinition,
    StageRegistry,
    default_registry,
)
from auditmanager.analysis.engine.result import (
    MetricValue,
    StageError,
    StageResult,
    StageStatus,
)
from auditmanager.analysis.ports.stage import StageContext, StageHandler, StageProduction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import BlobStore
from auditmanager.storage.models import BlobId

#: Injected in tests so a result's timestamps are not a source of flake.
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def assert_status_allowed(definition: StageDefinition, status: StageStatus) -> None:
    """Refuse a status this stage's registry ``status_policy`` does not permit.

    ``GJ-02-EO-13``: skippability comes only from the versioned registry. So does
    partiality. The runner never *produces* either status for these three stages, and
    this guard means that anything that ever tries to is refused at the boundary
    rather than trusted because the runner is believed not to.
    """
    if status is StageStatus.SKIPPED and not definition.skip_allowed:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the stage registry declares this stage may not be skipped; "
                "skippability comes only from the versioned registry"
            ),
            stage_id=definition.stage_id,
            reason="skip_not_allowed",
        )
    if status is StageStatus.PARTIAL and not definition.partial_allowed:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the stage registry declares this stage may not report a partial "
                "result; a partial outcome is a failure for it"
            ),
            stage_id=definition.stage_id,
            reason="partial_not_allowed",
        )


def run_stage(
    stage_id: str,
    *,
    version_uid: str,
    inputs: Mapping[str, BlobId],
    blob_store: BlobStore,
    handler: StageHandler | None = None,
    registry: StageRegistry | None = None,
    clock: Clock = _utc_now,
) -> StageResult:
    """Run one canonical stage and return its contract-shaped result.

    ``stage_id`` must be a canonical registry identity. A legacy alias is not
    resolved here and never will be: the registry's ``alias_resolution`` rule puts
    that at the control plane's boundary, and an unknown identity raises.

    ``handler`` defaults to the implementation registered for ``stage_id``. It is a
    parameter so a test can drive the runner's guards with a stage that misbehaves in
    a way the real implementations structurally cannot.
    """
    active = registry or default_registry()
    definition = active.stage(stage_id)

    if handler is None:
        from auditmanager.analysis.stages import handler_for

        handler = handler_for(definition.stage_id)

    started = clock()

    missing = definition.missing_inputs(inputs)
    if missing:
        return _failed(
            definition,
            DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message=(
                    "a required stage input was not supplied; the stage was not run "
                    "and no artifact was published"
                ),
                stage_id=definition.stage_id,
                reason="missing_required_input",
            ),
            started=started,
            finished=clock(),
            metrics={"missing_input_count": len(missing)},
        )

    context = StageContext(
        definition=definition,
        version_uid=version_uid,
        inputs=dict(inputs),
        blob_store=blob_store,
    )

    try:
        production = handler(context)
    except DomainError as error:
        return _failed(definition, error, started=started, finished=clock())

    if not isinstance(production, StageProduction):
        return _failed(
            definition,
            DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="the stage handler did not return a stage production",
            ),
            started=started,
            finished=clock(),
        )

    absent = definition.missing_outputs(production.roles)
    if absent and definition.succeeded_requires_all_required_outputs:
        return _failed(
            definition,
            DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message=(
                    "the stage did not produce every output role the registry marks "
                    "required; a missing required output is failure, never a "
                    "success with a gap"
                ),
                stage_id=definition.stage_id,
            ),
            started=started,
            finished=clock(),
            metrics={"missing_output_count": len(absent)},
        )

    finished = clock()
    metrics = dict(production.metrics)
    metrics.setdefault("duration_ms", _elapsed_ms(started, finished))
    return _result_for(
        definition,
        StageStatus.SUCCEEDED,
        artifacts=production.artifacts,
        metrics=metrics,
        error=None,
        started=started,
        finished=finished,
    )


def _failed(
    definition: StageDefinition,
    error: DomainError,
    *,
    started: datetime,
    finished: datetime,
    metrics: Mapping[str, MetricValue] | None = None,
) -> StageResult:
    """The single construction site of a failed result. No artifact survives it."""
    combined: dict[str, MetricValue] = dict(metrics or {})
    combined.setdefault("duration_ms", _elapsed_ms(started, finished))
    return _result_for(
        definition,
        StageStatus.FAILED,
        artifacts=(),
        metrics=combined,
        error=StageError.from_domain_error(error),
        started=started,
        finished=finished,
    )


def _result_for(
    definition: StageDefinition,
    status: StageStatus,
    *,
    artifacts: tuple,
    metrics: Mapping[str, MetricValue],
    error: StageError | None,
    started: datetime,
    finished: datetime,
) -> StageResult:
    assert_status_allowed(definition, status)
    return StageResult(
        stage_id=definition.stage_id,
        stage_version=definition.stage_version,
        status=status,
        artifacts=tuple(artifacts),
        metrics=dict(metrics),
        error=error,
        started_at=started,
        finished_at=finished,
    )


def _elapsed_ms(started: datetime, finished: datetime) -> int:
    return max(0, int((finished - started).total_seconds() * 1000))


__all__ = ["Clock", "assert_status_allowed", "run_stage"]
