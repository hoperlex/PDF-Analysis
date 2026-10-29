"""Put the follow-up of a prepared set on the queue (`CMP-SERIES-01`; `CMP-INGEST-02`'s ``BatchLifecycle.advance`` calls it).

A batch declared with ``compare_after_preparation`` («После подготовки сравнить все соседние версии») asks that, when a set's
preparation has completed, the matrix of the set's document is prepared and then the series of its adjacent transitions is
started. :func:`enqueue_series_after_preparation` writes the one ``comparison_work`` item that does it, in the caller's
transaction -- the caller commits. The item is attached to the upload (a cancel of the batch reaches it, and the batch does not
complete while it waits), is deduplicated by the set, and is the upload creator's act: the series it starts names that person.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.comparison.modules import MODULE_VERSIONS
from auditmanager.comparison.series.model import SERIES_AFTER_PREPARATION_KIND
from auditmanager.comparison.work.repository import ComparisonWorkRepository, Enqueued

__all__ = ["enqueue_series_after_preparation", "follow_up_dedupe_key"]


def follow_up_dedupe_key(set_id: str) -> str:
    """One live follow-up per set of a batch."""
    return f"{SERIES_AFTER_PREPARATION_KIND}:{set_id}"


def enqueue_series_after_preparation(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    set_id: str,
    comparison_upload_id: str,
    created_by_user_uid: str,
    actor_label: str,
) -> Enqueued:
    """Queue the preparation of the matrix of ``document_uid`` and then its series, or answer the live item that already is."""
    return ComparisonWorkRepository().enqueue(
        session,
        project_uid=project_uid,
        module=MODULE_VERSIONS,
        kind=SERIES_AFTER_PREPARATION_KIND,
        payload={"document_uid": document_uid, "set_id": set_id, "actor_label": actor_label},
        dedupe_key=follow_up_dedupe_key(set_id),
        max_attempts=3,
        comparison_upload_id=comparison_upload_id,
        created_by_user_uid=created_by_user_uid,
    )
