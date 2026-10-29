"""What happens to a batch after its sets are confirmed: release one set at a time, complete, cancel, abandon.

:class:`BatchLifecycle` is the database side of the batch state machine. It is stateless (every method takes the
caller's session and never commits) so that the use cases of :mod:`.service`, the hook after a confirmation and the
work handler of :mod:`.handlers` all take the same decisions in the transaction that acts.

The machine
-----------
``uploading`` -> ``proposed`` and ``proposed`` -> ``completed`` belong to ``CMP-INGEST-01`` (the files are settled, the
sets are decided). This package adds ``proposed`` -> ``processing`` (the first confirmed set), ``processing`` <->
``paused``, ``processing`` -> ``completed`` and the move of any active state to ``cancelled``.

* **A confirmed set is released**, not enqueued at confirmation: its versions are made at once (``CMP-INGEST-01``), and
  the lifecycle puts their page profiles on the comparison queue (one item per version, carrying the batch's identity)
  **one set at a time**. A set is released only when no item of the batch is live, so the set in hand always finishes
  before the next one starts. That is what a pause means: it stops the *release* of the next set, never an item in
  flight, and never the rest of the set in hand.
* **The batch completes** when every set is ``done`` or ``excluded``, every ``done`` set has been released and no item
  of the batch is live. A set that ``failed`` keeps the batch open until it is retried or left out; an item that
  failed does not (its pages carry the result).
* **The drive** (:mod:`.handlers`) is one polling item per batch, not attached to the batch's identity (so the batch's
  own live-item count never includes it). It releases the next set, completes the batch, and cancels a batch that has
  been ``uploading`` and untouched for :data:`~.rules.ABANDON_AFTER_SECONDS`. The hooks do the same work at once, so the
  poll only covers what finishes later.
* **A cancel** is the whole decision in one transaction: the files that never completed fail, their parts are aborted,
  the sets that made no versions are left out, the batch is ``cancelled`` (which frees the account's one active slot),
  every waiting item of the batch is cancelled and every item in flight is asked to stop, and the abort sweep is
  enqueued **after** that (so the sweep is not one of the items the cancel just stopped). The store is touched later,
  by the sweep, from the database's decision: nothing is deleted here and no version, document or published blob is
  named by any statement.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.orm import Session

from auditmanager.comparison.public import (
    MODULE_VERSIONS,
    ComparisonWorkRepository,
    Enqueued,
    enqueue_series_after_preparation,
    enqueue_version_page_profiles,
)
from auditmanager.ingest.comparison_batch.repository import (
    ComparisonBatchRepository,
    compared,
    confirmed_versions,
    released,
)
from auditmanager.ingest.comparison_batch.rules import (
    ABANDON_AFTER_SECONDS,
    DRIVE_ACTIVE_SECONDS,
    DRIVE_IDLE_SECONDS,
    DRIVE_KIND,
    LIVE_ITEM_STATES,
    SWEEP_GRACE_SECONDS,
    SWEEP_KIND,
    drive_dedupe_key,
    sweep_dedupe_key,
)
from auditmanager.ingest.comparison_pdf.public import ComparisonUploadRepository
from auditmanager.ingest.comparison_pdf.repository import SetRow, UploadRow

__all__ = ["Advance", "BatchLifecycle", "CancelReport", "Drive"]


@dataclass(frozen=True, slots=True)
class Advance:
    """What one look at a ``processing`` batch decided: ``released`` a set, ``completed`` the batch, or ``waiting``."""

    outcome: str
    live_items: int


@dataclass(frozen=True, slots=True)
class CancelReport:
    files: int
    parts: int
    sets: int
    items_cancelled: int
    items_asked_to_stop: int
    sweep_enqueued: bool


@dataclass(frozen=True, slots=True)
class Drive:
    """What the drive does next: end (the batch is finished) or come back after ``delay_seconds``."""

    done: bool
    delay_seconds: float = 0.0


class BatchLifecycle:
    """Stateless decisions on a batch, taken in the caller's transaction."""

    __slots__ = ("_uploads", "_batches", "_work", "_sweep_delay")

    def __init__(
        self, *, work: ComparisonWorkRepository | None = None, sweep_delay_seconds: float = SWEEP_GRACE_SECONDS
    ) -> None:
        self._uploads = ComparisonUploadRepository()
        self._batches = ComparisonBatchRepository()
        self._work = work or ComparisonWorkRepository()
        self._sweep_delay = sweep_delay_seconds

    # -- the drive item --------------------------------------------------------------------------------

    def ensure_driver(self, session: Session, upload: UploadRow, *, delay_seconds: float = DRIVE_IDLE_SECONDS) -> Enqueued:
        """The batch's one polling item, or the live one that already is (the dedupe key is the batch)."""
        return self._work.enqueue(
            session,
            project_uid=upload.project_uid,
            module=MODULE_VERSIONS,
            kind=DRIVE_KIND,
            payload={"upload_id": upload.upload_id},
            dedupe_key=drive_dedupe_key(upload.upload_id),
            delay_seconds=delay_seconds,
            created_by_user_uid=upload.actor_user_uid,
        )

    # -- releasing a confirmed set ---------------------------------------------------------------------

    def live_items(self, session: Session, upload_id: str) -> int:
        """Items attached to the batch that are not terminal (the drive is not attached, so it is never counted)."""
        counts = self._work.counts(session, upload_id=upload_id)
        return sum(n for state, n in counts.items() if state in LIVE_ITEM_STATES)

    def pending_sets(self, session: Session, upload_id: str) -> list[SetRow]:
        """The ``done`` sets whose page profiles have not been put on the queue, in the order they were confirmed."""
        rows = [
            row for row in self._uploads.list_sets(session, upload_id)
            if row.state == "done" and not released(row.proposal)
        ]
        return sorted(rows, key=lambda row: (row.confirmed_at, row.set_id))

    def prepared_sets(self, session: Session, upload_id: str) -> list[SetRow]:
        """The ``done`` sets that were released and whose comparison follow-up is not on the queue, in the order they were
        confirmed (`CMP-SERIES-01`)."""
        rows = [
            row for row in self._uploads.list_sets(session, upload_id)
            if row.state == "done" and released(row.proposal) and not compared(row.proposal)
        ]
        return sorted(rows, key=lambda row: (row.confirmed_at, row.set_id))

    def queue_comparison(self, session: Session, upload: UploadRow, row: SetRow) -> None:
        """«После подготовки сравнить все соседние версии»: put the matrix preparation and then the series of the set's
        document on the queue, once (the mark on the set is written in the same transaction). The follow-up is an item of
        the batch -- a cancel reaches it, and the batch does not complete or release the next set while it waits -- and it
        is the act of the person who declared the batch. Reached through ``comparison.public`` names only."""
        if not upload.compare_after_preparation or row.document_uid is None or compared(row.proposal):
            return
        enqueued = enqueue_series_after_preparation(
            session,
            project_uid=upload.project_uid,
            document_uid=row.document_uid,
            set_id=row.set_id,
            comparison_upload_id=upload.upload_id,
            created_by_user_uid=row.confirmed_by_user_uid or upload.actor_user_uid,
            actor_label=upload.actor_label,
        )
        self._batches.mark_set_compared(session, row.set_id, work_id=enqueued.work_id)

    def release_remaining(self, session: Session, upload: UploadRow) -> None:
        """A batch that is already ``completed`` has nothing more to wait for: every set not yet released is released, in
        order, and every released set that asked for a comparison gets its follow-up (the follow-up waits for the
        preparation by itself)."""
        for pending in self.pending_sets(session, upload.upload_id):
            self.release_set(session, upload, pending)
        for prepared in self.prepared_sets(session, upload.upload_id):
            self.queue_comparison(session, upload, prepared)

    def promote_if_confirmed(self, session: Session, upload: UploadRow) -> UploadRow:
        """A ``proposed`` batch that holds a ``done`` set is being processed: move it there (and give it its drive).

        The hook after a confirmation does this at once; the drive and the exclusion do it for a batch whose hook never
        ran (a process killed between the confirmation's commit and the hook), so that nothing waits for a client.
        """
        if upload.state != "proposed" or not any(
            row.state == "done" for row in self._uploads.list_sets(session, upload.upload_id)
        ):
            return upload
        self._uploads.set_upload_state(session, upload.upload_id, to_state="processing")
        promoted = replace(upload, state="processing")
        self.ensure_driver(session, promoted)
        return promoted

    def release_set(self, session: Session, upload: UploadRow, row: SetRow) -> None:
        """Put the page profiles of every version the set made on the queue, once.

        One item per version, in the confirmed order, attached to the batch (its cancel reaches them) and filed
        under the batch's project; a live item of a version that already has one is returned, never doubled. The
        mark on the set is written in the same transaction, so a replay of the confirmation, the hook and the drive
        can all ask and the set is released exactly once.
        """
        work: dict[str, str] = {}
        for version_uid in confirmed_versions(row.proposal):
            enqueued = enqueue_version_page_profiles(
                session,
                project_uid=upload.project_uid,
                version_uid=version_uid,
                created_by_user_uid=row.confirmed_by_user_uid or upload.actor_user_uid,
                comparison_upload_id=upload.upload_id,
            )
            work[version_uid] = enqueued.work_id
        self._batches.mark_set_released(session, row.set_id, work=work)

    def advance(self, session: Session, upload: UploadRow) -> Advance:
        """Look at a ``processing`` batch (the caller holds its row lock): release the next set if none is in
        flight, complete the batch if nothing is left, else wait."""
        live = self.live_items(session, upload.upload_id)
        if live == 0 and upload.compare_after_preparation:
            # Nothing of the batch is in flight, so every released set has been prepared: queue its comparison
            # (`CMP-SERIES-01`). The follow-up is an item of the batch, so the next set waits for it.
            for prepared in self.prepared_sets(session, upload.upload_id):
                self.queue_comparison(session, upload, prepared)
            live = self.live_items(session, upload.upload_id)
        pending = self.pending_sets(session, upload.upload_id)
        if live == 0 and pending:
            self.release_set(session, upload, pending[0])
            return Advance("released", live)
        sets = self._uploads.list_sets(session, upload.upload_id)
        if live == 0 and not pending and sets and all(row.state in ("done", "excluded") for row in sets):
            self._uploads.set_upload_state(session, upload.upload_id, to_state="completed")
            return Advance("completed", 0)
        return Advance("waiting", live)

    # -- hooks -----------------------------------------------------------------------------------------

    def after_declaration(self, session: Session, upload_id: str) -> None:
        """Every batch has its drive from the moment it exists (it is what notices an abandoned upload)."""
        upload = self._uploads.get_upload(session, upload_id, for_update=True)
        if upload is not None and upload.state in ("uploading", "proposed", "processing", "paused"):
            self.ensure_driver(session, upload)

    def after_confirmation(self, session: Session, upload_id: str, set_id: str) -> None:
        """Idempotent: what a confirmed set needs next, decided under the batch's lock.

        A ``proposed`` batch becomes ``processing`` with its first confirmed set. A ``processing`` batch releases the
        set at once when none is in flight (otherwise the drive does, when the one in flight ends). A ``paused``
        batch only keeps its drive: the set waits for the resume. A ``cancelled`` batch releases nothing (the
        versions the set made stay; their pages are built when a comparison asks for them). A batch that
        ``CMP-INGEST-01`` completed with this very confirmation (its last set) has no drive to wait for, so every
        set not yet released is released now, in order.
        """
        upload = self._uploads.get_upload(session, upload_id, for_update=True)
        row = self._uploads.get_set(session, set_id)
        if upload is None or row is None or row.upload_id != upload_id or row.state != "done":
            return
        upload = self.promote_if_confirmed(session, upload)
        state = upload.state
        if state in ("processing", "paused"):
            self.ensure_driver(session, upload)
            if state == "processing":
                self.advance(session, upload)
        elif state == "completed":
            self.release_remaining(session, upload)

    # -- cancel ----------------------------------------------------------------------------------------

    def cancel(self, session: Session, upload: UploadRow, *, reason: str, created_by_user_uid: str | None) -> CancelReport:
        """«Отменить пакет» (``reason`` ``cancelled``) or the abandonment of a batch (``abandoned``).

        The caller holds the batch's row lock and has checked that the batch is active. The order is the guard: rows
        first, then the items of the batch, then the sweep, so the sweep is never among the items that were stopped.
        """
        counts = self._batches.cancel_rows(session, upload.upload_id)
        stopped = self._work.cancel_for_upload(session, upload.upload_id)
        enqueue_sweep = bool(self._batches.open_tokens(session, upload.upload_id))
        if enqueue_sweep:
            self._work.enqueue(
                session,
                project_uid=upload.project_uid,
                module=MODULE_VERSIONS,
                kind=SWEEP_KIND,
                payload={"upload_id": upload.upload_id, "reason": reason},
                dedupe_key=sweep_dedupe_key(upload.upload_id),
                delay_seconds=self._sweep_delay,
                max_attempts=5,
                comparison_upload_id=upload.upload_id,
                created_by_user_uid=created_by_user_uid or upload.actor_user_uid,
            )
        return CancelReport(
            files=counts["files"], parts=counts["parts"], sets=counts["sets"],
            items_cancelled=stopped.cancelled, items_asked_to_stop=stopped.requested, sweep_enqueued=enqueue_sweep,
        )

    # -- the drive's decision --------------------------------------------------------------------------

    def drive(self, session: Session, upload_id: str) -> Drive:
        """One poll of one batch, in one transaction: finished, or when to come back."""
        upload: Any = self._uploads.get_upload(session, upload_id, for_update=True)
        if upload is None or upload.state == "cancelled":
            return Drive(done=True)
        if upload.state == "completed":
            # ``CMP-INGEST-01`` completes a batch with its last confirmation; a set whose hook never ran is released
            # now, in order, and then the drive has nothing left to watch.
            self.release_remaining(session, upload)
            return Drive(done=True)
        upload = self.promote_if_confirmed(session, upload)
        if upload.state == "uploading":
            idle = self._batches.idle_seconds(session, upload_id)
            if idle >= ABANDON_AFTER_SECONDS:
                self.cancel(session, upload, reason="abandoned", created_by_user_uid=None)
                return Drive(done=True)
            return Drive(done=False, delay_seconds=min(DRIVE_IDLE_SECONDS, ABANDON_AFTER_SECONDS - idle))
        if upload.state == "processing":
            step = self.advance(session, upload)
            if step.outcome == "completed":
                return Drive(done=True)
            busy = step.live_items > 0 or step.outcome == "released"
            return Drive(done=False, delay_seconds=DRIVE_ACTIVE_SECONDS if busy else DRIVE_IDLE_SECONDS)
        # ``proposed`` or ``paused``: the batch waits for a person.
        return Drive(done=False, delay_seconds=DRIVE_IDLE_SECONDS)
