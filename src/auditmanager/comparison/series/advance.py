"""What carries a series from its pairs to its verdict: reconcile, finalise a transition, conclude the series
(`CMP-SERIES-01`; ADR-0025 decisions 4, 7, 21).

:meth:`SeriesAdvancer.advance` is idempotent and is called by the handler of every pair after it wrote its pair, and by the
series' polling item (the drive). Everything it decides is read from and written to the database; nothing lives in memory
(AGENTS.md section 4). Every transaction that writes starts with the **fence** the caller hands over -- in the worker that is
``WorkItem.require_current``, which locks the item and its attempt and refuses an attempt that lost its lease -- so a worker
whose lease is gone writes nothing.

The three steps
---------------
1. **Reconcile.** A pair that waits for the engine although no item of its own is going to run (the item failed, was
   cancelled, or never existed) can never finish by itself: it is marked ``failed`` with the item's reason. This is the one
   place a lost item becomes a visible failure instead of a transition that never ends (a worker killed three times on the
   same pair ends its item through the queue's reclaim, which runs no handler).
2. **Finalise** each transition none of whose pairs is ``queued`` or ``computing``: the parts coverage of the sheets that
   were split across the versions (the original's ``_parts_phase``, :mod:`.parts`), the reconciliation of the permit's
   declared changes with the found ones (``_permit_phase``, :mod:`.permit`), and the counts and verdict codes
   (:mod:`.verdict`). The permit reads the first pages of the two versions' page profiles *outside* any transaction (object
   store reads must not hold a lock), then the transaction re-checks that the transition is still the one it read.
   A failure of a phase fails **that transition** with its reason (a «Досчитать» queues it again); it never loops silently.
3. **Conclude** the series: when no transition is ``queued`` or ``running`` it is ``completed``, or ``failed`` if a
   transition failed. A failed *pair* does not fail a transition or a series: the verdict of that transition says
   ``incomplete`` and ``calculation_failed``.

Lock order, everywhere: work item rows (the fence), then the series row, then its transition rows, then its pair rows.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.series import permit as permit_module
from auditmanager.comparison.series.model import (
    PAIR_DONE,
    SERIES_LIVE,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_PAUSED,
    STATE_QUEUED,
    STATE_RUNNING,
)
from auditmanager.comparison.series.parts import PartFact, group_coverage
from auditmanager.comparison.series.repository import SeriesRepository, SeriesRow, TransitionRow
from auditmanager.comparison.series.verdict import PairFacts, transition_verdict
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["Advance", "DRIVE_ACTIVE_SECONDS", "DRIVE_IDLE_SECONDS", "PERMIT_SCAN_PAGES", "SeriesAdvancer", "fail_orphans"]

_LOG = logging.getLogger(__name__)

#: How soon the drive looks again while pairs are being computed, and while nothing is (a paused series).
DRIVE_ACTIVE_SECONDS: Final[float] = 15.0
DRIVE_IDLE_SECONDS: Final[float] = 30.0
#: The permit form is on one of the first sheets; the profile has no page kind (see :mod:`.permit`).
PERMIT_SCAN_PAGES: Final[int] = 10
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})

Fence = Callable[[Session], None]


@dataclass(frozen=True, slots=True)
class Advance:
    """After one look: is the series still live, and when to look again."""

    live: bool
    delay_seconds: float = 0.0


def fail_orphans(repository: SeriesRepository, session: Session, series: SeriesRow) -> int:
    """Mark ``failed`` each pair that waits for a result although its item has ended or never was (see the module)."""
    failed = 0
    for pair_id, item_state, item_reason in repository.orphans(session, series):
        if item_state is None:
            reason = "series_item_missing"
        elif item_state == "succeeded":
            reason = "series_item_ended_without_result"
        elif item_state == "cancelled":
            reason = "series_item_cancelled"
        else:
            reason = (item_reason or "series_item_failed")[:128]
        failed += int(repository.fail_pair(session, pair_id, reason))
    return failed


class SeriesAdvancer:
    __slots__ = ("_factory", "_blobs", "_repo", "_permit_pages")

    def __init__(
        self, session_factory: sessionmaker[Session], blob_store: Any = None, *,
        repository: SeriesRepository | None = None, permit_pages: int = PERMIT_SCAN_PAGES,
    ) -> None:
        self._factory = session_factory
        self._blobs = blob_store
        self._repo = repository or SeriesRepository()
        self._permit_pages = permit_pages

    # -- the entry ---------------------------------------------------------------------------------------------

    def advance(self, series_id: str, *, fence: Fence) -> Advance:
        """One idempotent look at a series; see the module. ``fence`` is called first in every transaction that writes."""
        with session_scope(self._factory) as session:
            series = self._repo.get_series(session, series_id)
        if series is None or series.state not in SERIES_LIVE:
            return Advance(False)
        if series.state == STATE_PAUSED:
            return Advance(True, DRIVE_IDLE_SECONDS)
        ready = self._reconcile(series_id, fence)
        for transition_id in ready:
            self._finalise(series_id, transition_id, fence)
        return self._conclude(series_id, fence)

    # -- 1. reconcile ---------------------------------------------------------------------------------------------

    def _reconcile(self, series_id: str, fence: Fence) -> list[str]:
        with session_scope(self._factory) as session:
            fence(session)
            series = self._repo.get_series(session, series_id, for_update=True)
            if series is None or series.state not in (STATE_QUEUED, STATE_RUNNING):
                return []
            fail_orphans(self._repo, session, series)
            transitions = self._repo.transitions(session, series_id)
            progress = self._repo.progress(session, [t.transition_id for t in transitions])
            if series.state == STATE_QUEUED and any(p["started"] for p in progress.values()):
                self._repo.set_series_state(session, series_id, from_states=[STATE_QUEUED], to_state=STATE_RUNNING)
            for t in transitions:
                if t.state == STATE_QUEUED and progress.get(t.transition_id, {}).get("started"):
                    self._repo.run_transition(session, t.transition_id)
            return [
                t.transition_id for t in transitions
                if t.state in (STATE_QUEUED, STATE_RUNNING) and progress.get(t.transition_id, {}).get("open", 0) == 0
            ]

    # -- 2. finalise a transition ---------------------------------------------------------------------------------

    def _finalise(self, series_id: str, transition_id: str, fence: Fence) -> None:
        with session_scope(self._factory) as session:
            transition = self._repo.get_transition(session, transition_id)
            if transition is None or transition.state not in (STATE_QUEUED, STATE_RUNNING):
                return
            pairs = self._repo.permit_pairs(session, transition_id)
        try:
            reconciled = self._read_permit(transition, pairs)
        except DomainError as failure:
            if failure.code in _LEASE_GONE:
                raise
            self._fail_transition(series_id, transition_id, f"post_phase_{failure.code.value}", fence)
            return
        except Exception as failure:  # a phase that cannot run is a visible failure of that transition
            _LOG.exception("series %s transition %s: the permit phase failed", series_id, transition_id)
            self._fail_transition(series_id, transition_id, f"post_phase_{type(failure).__name__}", fence)
            return
        try:
            self._write_final(series_id, transition_id, reconciled, fence)
        except DomainError as failure:
            if failure.code in _LEASE_GONE:
                raise
            self._fail_transition(series_id, transition_id, f"post_phase_{failure.code.value}", fence)
        except Exception as failure:
            _LOG.exception("series %s transition %s: the post-phases failed", series_id, transition_id)
            self._fail_transition(series_id, transition_id, f"post_phase_{type(failure).__name__}", fence)

    def _read_permit(self, transition: TransitionRow, pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
        """The reconciliation of the newer version's permit against the pairs, or ``None`` when it has no permit."""
        reader = PageProfileReader(self._factory, self._blobs)
        permits_b = self._permits_of(reader, transition.target_version_uid)
        if not permits_b:
            return None
        with session_scope(self._factory) as session:
            permits_a = self._permits_of(reader, transition.source_version_uid)
            revisions = self._repo.revision_numbers(session, transition.source_version_uid, PAGE_PROFILE_ALGO_VERSION)
        izm_a = permit_module.izm_of([row for p in permits_a for row in p["rows"]], revisions)
        # A scan has no text, so its stamp is unreadable; the pair says the older sheet is the same sheet, whose number stands.
        stamps = {
            int(p["b_page"]): (p["stamp"] if (p["stamp"] or {}).get("sheet_number") else p["older_stamp"] or p["stamp"])
            for p in pairs if p["b_page"] is not None
        }
        found = [
            {
                "key": p["pair_id"], "b_page": int(p["b_page"]),
                # a pair that failed says nothing: its sheet needs a review, it is not «без отличий»
                "status": p["status"] if p["state"] == PAIR_DONE and p["status"] else "needs_review",
                "title": (p["stamp"] or {}).get("sheet_name"),
            }
            for p in pairs if p["b_page"] is not None
        ]
        return permit_module.reconcile(permits_b, izm_a, stamps, found)

    def _permits_of(self, reader: PageProfileReader, version_uid: str) -> list[dict[str, Any]]:
        with session_scope(self._factory) as session:
            profile_ids = self._repo.leading_text_pages(session, version_uid, PAGE_PROFILE_ALGO_VERSION, self._permit_pages)
        out: list[dict[str, Any]] = []
        for profile_id in profile_ids:
            data = reader.read_page_profile(profile_id)
            words = [(w.x0, w.top, w.x1, w.bottom, w.text) for w in data.words]
            vertical = [(line.x0, line.top, line.bottom) for line in data.lines if abs(line.x1 - line.x0) <= 0.5]
            rows = permit_module.parse_page(words, vertical, data.height_pt)
            if rows:
                out.append({"page": data.row.page_number, "rows": rows})
        return out

    def _write_final(
        self, series_id: str, transition_id: str, reconciled: dict[str, Any] | None, fence: Fence
    ) -> None:
        with session_scope(self._factory) as session:
            fence(session)
            series = self._repo.get_series(session, series_id, for_update=True)
            if series is None or series.state not in (STATE_QUEUED, STATE_RUNNING):
                return
            transition = self._repo.get_transition(session, transition_id, for_update=True)
            if transition is None or transition.state not in (STATE_QUEUED, STATE_RUNNING):
                return
            if self._repo.progress(session, [transition_id]).get(transition_id, {}).get("open", 0):
                return  # a pair came back to the queue meanwhile
            self._parts_phase(session, transition_id)
            if reconciled is not None:
                for pair_id, record in permit_module.pair_permits(reconciled).items():
                    self._repo.set_permit(session, pair_id, record)
            summary, verdict = transition_verdict(self._pair_facts(session, transition_id))
            if transition.state == STATE_QUEUED:  # no pair needed the engine: the database has no queued -> completed edge
                self._repo.run_transition(session, transition_id)
            self._repo.set_transition_state(
                session, transition_id, from_states=[STATE_QUEUED, STATE_RUNNING], to_state=STATE_COMPLETED,
                summary=summary, verdict=verdict,
            )

    def _pair_facts(self, session: Session, transition_id: str) -> list[PairFacts]:
        return [
            PairFacts(f.state, f.status, f.both_pages, f.ai_dependent, f.style_only)
            for f in self._repo.facts(session, [transition_id])
        ]

    def _parts_phase(self, session: Session, transition_id: str) -> None:
        """The coverage of each split sheet by its parts (``jobs.py:875-926``), written on every pair of the group."""
        groups: dict[str, list[tuple[str, dict[str, Any], Mapping[str, Any] | None]]] = {}
        for pair_id, record, member in self._repo.part_facts(session, transition_id):
            if record.get("kind") == "split":
                groups.setdefault(str(record["source_profile_id"]), []).append((pair_id, record, member))
        for items in groups.values():
            facts = [
                PartFact(
                    None if m is None else m.get("area_a_pt"), None if m is None else m.get("coverage_a"),
                    bool(m and m.get("reliable")),
                )
                for _pair, _record, m in items
            ]
            percent, reliable = group_coverage(float(items[0][1].get("text_percent", 0.0)), facts)
            for pair_id, record, _member in items:
                self._repo.set_parts(session, pair_id, {**record, "covered_percent": percent, "coverage_reliable": reliable})

    def _fail_transition(self, series_id: str, transition_id: str, reason: str, fence: Fence) -> None:
        with session_scope(self._factory) as session:
            fence(session)
            series = self._repo.get_series(session, series_id, for_update=True)
            if series is None or series.state not in (STATE_QUEUED, STATE_RUNNING):
                return
            self._repo.set_transition_state(
                session, transition_id, from_states=[STATE_QUEUED, STATE_RUNNING], to_state=STATE_FAILED,
                reason=reason[:128],
            )

    # -- 3. conclude ----------------------------------------------------------------------------------------------

    def _conclude(self, series_id: str, fence: Fence) -> Advance:
        with session_scope(self._factory) as session:
            fence(session)
            series = self._repo.get_series(session, series_id, for_update=True)
            if series is None or series.state not in SERIES_LIVE:
                return Advance(False)
            if series.state == STATE_PAUSED:
                return Advance(True, DRIVE_IDLE_SECONDS)
            transitions = self._repo.transitions(session, series_id)
            if transitions and all(t.state in (STATE_COMPLETED, STATE_FAILED) for t in transitions):
                if series.state == STATE_QUEUED:  # nothing needed the engine: the database has no queued -> completed edge
                    self._repo.set_series_state(session, series_id, from_states=[STATE_QUEUED], to_state=STATE_RUNNING)
                if any(t.state == STATE_FAILED for t in transitions):
                    self._repo.set_series_state(
                        session, series_id, from_states=[STATE_QUEUED, STATE_RUNNING], to_state=STATE_FAILED,
                        reason="transition_failed",
                    )
                else:
                    self._repo.set_series_state(
                        session, series_id, from_states=[STATE_QUEUED, STATE_RUNNING], to_state=STATE_COMPLETED
                    )
                return Advance(False)
            return Advance(True, DRIVE_ACTIVE_SECONDS)
