"""The reads of part B: the specifications of a series, of a transition, and the changes of a transition (`CMP-VC-SPEC-01`).

Reading starts nothing: no job, no model, no PDF. The state of a transition is derived from the row of its whole-specification
comparison and from the job that runs it:

* no row, and no specification sheet in either version: ``not_applicable`` (method «листовой ИИ»: there is nothing to read as a whole);
* no row, and a specification sheet: ``not_started``;
* a row ``queued`` or ``running``: ``running``, or ``paused`` while its job is paused, with the phase it is in;
* ``completed``, ``incomplete``, ``failed``, ``cancelled`` as the row says. An ``incomplete`` comparison reads «листовой ИИ»: a side
  that could not be read whole is described sheet by sheet (the original's rule, ``docs/whole_specification_comparison.md``
  lines 362-371).

The number of specification sheets of a version is the row's, once there is one, and otherwise the number of its pages whose title
block says «specification» (:func:`~.table.is_spec_stamp`): a test on the stored summary of the profile, so listing the transitions
of a series opens no archive.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.specification.reader import SpecificationReader, spec_candidates
from auditmanager.comparison.specification.repository import ComparisonRow, SpecificationRepository, TransitionScope
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["PAGE_MAX", "SpecificationPage", "SpecificationService"]

PAGE_MAX: Final[int] = 200
_COVERAGE_KEYS: Final[tuple[str, ...]] = ("blocks_total", "blocks_covered", "rows_total", "rows_unresolved")


def _not_found(what: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


class SpecificationPage:
    __slots__ = ("items", "next_after")

    def __init__(self, items: list[dict[str, Any]], next_after: int | None) -> None:
        self.items, self.next_after = items, next_after


def _coverage(raw: dict[str, Any] | None) -> dict[str, int] | None:
    return None if raw is None else {key: int(raw.get(key, 0)) for key in _COVERAGE_KEYS}


class SpecificationService:
    def __init__(self, session_factory: sessionmaker[Session], blob_store: Any, *, repository: SpecificationRepository | None = None,
                 reader: SpecificationReader | None = None) -> None:
        self._factory = session_factory
        self._repository = repository or SpecificationRepository()
        self._reader = reader or SpecificationReader(session_factory, blob_store)

    # -- one transition -------------------------------------------------------------------------------------------------

    def scope_of(self, transition_id: str) -> TransitionScope:
        """The project, document and versions of a transition; an unknown one is ``not_found``."""
        with session_scope(self._factory) as session:
            scope = self._repository.transition(session, transition_id)
        if scope is None:
            raise _not_found("ComparisonTransition")
        return scope

    def close_cancelled(self, job_id: str) -> bool:
        """The job was cancelled: its transition's comparison row, if it is still waiting or running, is cancelled with it (an
        item still in flight finds the row no longer ``running`` and writes nothing)."""
        with session_scope(self._factory) as session:
            return self._repository.cancel_of_job(session, job_id)

    def get_specification(self, *, transition_id: str) -> dict[str, Any]:
        with session_scope(self._factory) as session:
            scope = self._repository.transition(session, transition_id)
            if scope is None:
                raise _not_found("ComparisonTransition")
            row = self._repository.whole(session, transition_id)
        return self._view(scope, row, self._sheets(scope, row, {}))

    def list_changes(self, *, transition_id: str, kind: str | None, offset: int, limit: int) -> tuple[list[dict[str, Any]], int | None]:
        """The stored changes of the transition's comparison, in the order it lists them, optionally of one kind."""
        bounded = max(1, min(limit, PAGE_MAX))
        with session_scope(self._factory) as session:
            if self._repository.transition(session, transition_id) is None:
                raise _not_found("ComparisonTransition")
            row = self._repository.whole(session, transition_id)
        changes = [c for c in (row.changes if row is not None else []) if kind is None or c["kind"] == kind]
        page = changes[offset : offset + bounded]
        more = offset + bounded < len(changes)
        return page, (offset + bounded) if more else None

    # -- a series -------------------------------------------------------------------------------------------------------

    def list_specifications(self, *, series_id: str, after_no: int, limit: int) -> SpecificationPage:
        """The transitions of the series that have a specification, in transition order, after ``after_no``."""
        bounded = max(1, min(limit, PAGE_MAX))
        with session_scope(self._factory) as session:
            if not self._repository.series_exists(session, series_id):
                raise _not_found("ComparisonSeries")
            transitions = self._repository.transitions_after(session, series_id, after_no=after_no)
            rows = self._repository.wholes_of_series(session, series_id)
        cache: dict[str, int] = {}
        items: list[dict[str, Any]] = []
        last_no = after_no
        more = False
        for scope in transitions:
            row = rows.get(scope.transition_id)
            sheets = self._sheets(scope, row, cache)
            if row is None and sheets[0] + sheets[1] == 0:
                continue  # no specification here: not in the block «Полные спецификации (СО)»
            if len(items) == bounded:
                more = True
                break
            items.append(self._view(scope, row, sheets))
            last_no = scope.transition_no
        return SpecificationPage(items, last_no if more else None)

    # -- the shape ------------------------------------------------------------------------------------------------------

    def _sheets(self, scope: TransitionScope, row: ComparisonRow | None, cache: dict[str, int]) -> tuple[int, int]:
        if row is not None:
            return row.sheets_a, row.sheets_b
        return self._count(scope.source_version_uid, cache), self._count(scope.target_version_uid, cache)

    def _count(self, version_uid: str, cache: dict[str, int]) -> int:
        if version_uid not in cache:
            cache[version_uid] = len(spec_candidates(self._reader.version_rows(version_uid)))
        return cache[version_uid]

    @staticmethod
    def _state(row: ComparisonRow | None, sheets: tuple[int, int]) -> str:
        if row is None:
            return "not_applicable" if sheets[0] + sheets[1] == 0 else "not_started"
        if row.state in ("queued", "running"):
            return "paused" if row.job_state == "paused" else "running"
        return row.state

    def _view(self, scope: TransitionScope, row: ComparisonRow | None, sheets: tuple[int, int]) -> dict[str, Any]:
        state = self._state(row, sheets)
        out: dict[str, Any] = {
            "transition_id": scope.transition_id,
            "method": "sheet_ai" if state in ("not_applicable", "incomplete") else "whole",
            "state": state, "sheets_a": sheets[0], "sheets_b": sheets[1],
        }
        if row is None:
            return out
        out["comparison_id"] = row.comparison_id
        if row.phase and state in ("running", "paused", "completed"):
            out["phase"] = row.phase
        for member, value in (("coverage_a", _coverage(row.coverage_a)), ("coverage_b", _coverage(row.coverage_b)), ("totals", row.totals)):
            if value is not None:
                out[member] = value
        if row.reason:
            out["reason"] = row.reason
        if row.job_id:
            out["job_id"] = row.job_id
        if row.extraction_a_id:
            out["extraction_a_id"] = row.extraction_a_id
        if row.extraction_b_id:
            out["extraction_b_id"] = row.extraction_b_id
        out["updated_at"] = row.updated_at
        return out
