"""Attempt-bound pull calls and durable images for runner tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from auditmanager.analysis.public import ProxyDispatchError
from auditmanager.comparison.work.model import ATTEMPT_WATCHDOG_SECONDS, WorkItem
from auditmanager.executors.public import checked_descriptors, checked_pngs
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage.public import StorageError

if TYPE_CHECKING:
    from auditmanager.analysis.public import ModelRequest, ModelResponse


ROLE_MODEL_CROP = "comparison_model_crop"


class ComparisonCallContext:
    """The identifiers and remaining watchdog time that a pull task must carry."""

    def __init__(self, session_factory: Any) -> None:
        self._sessions = session_factory
        self.comparison_attempt_id: str | None = None
        self.call_id: str | None = None

    def bind(self, item: WorkItem, call_id: str) -> None:
        self.comparison_attempt_id = item.attempt_id
        self.call_id = call_id

    def remaining_seconds(self) -> float:
        attempt_id = self.comparison_attempt_id
        if attempt_id is None:
            return 0.0
        with self._sessions() as session:
            seconds = session.execute(text(
                "SELECT extract(epoch FROM created_at + make_interval(secs => :watchdog) - clock_timestamp()) "
                "FROM comparison_work_attempt WHERE comparison_work_attempt_id = :attempt AND state = 'running'"
            ), {"attempt": attempt_id, "watchdog": ATTEMPT_WATCHDOG_SECONDS}).scalar_one_or_none()
        return max(0.0, float(seconds or 0.0))


class PublishedPullAdapter:
    """Publish each checked crop before a pull task exposes its descriptor to a runner."""

    def __init__(self, adapter: Any, publisher: Any) -> None:
        self._adapter, self._publisher = adapter, publisher

    @property
    def provider_mode(self) -> Any:
        return self._adapter.provider_mode

    @property
    def identity_basis(self) -> Any:
        return self._adapter.identity_basis

    def complete(self, request: ModelRequest) -> ModelResponse:
        raws = checked_pngs(request)
        descriptors = checked_descriptors(request.body.get("images", ()))
        for descriptor, raw in zip(descriptors, raws, strict=True):
            try:
                published = self._publisher.publish(raw, role=ROLE_MODEL_CROP, media_type="image/png")
            except StorageError:
                raise ProxyDispatchError(
                    ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="not_sent", retry_safe=True,
                    details={"dependency": "comparison_model_crop_store"},
                ) from None
            if published != descriptor["blob_id"]:
                raise ProxyDispatchError(
                    ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="not_sent", retry_safe=False,
                    message="a published crop did not match its descriptor",
                )
        return self._adapter.complete(request)
