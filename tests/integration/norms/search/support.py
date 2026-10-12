"""A stand-in database for the container-free norms tests (`W55A-SEARCH-01`).

It answers **the exact statements** ``auditmanager.norms.search.service`` and
``auditmanager.norms.current_snapshot`` send -- recognised by identity (the module-level
``text()`` objects) or, for the search statements built per query, by a fragment of their
text -- from a few Python dicts, and records every statement it was sent in order. It proves
what the Python around the SQL does: the order of the setter's checks, the refusals, the
timeout's mapping, the adapters' shapes and the content path. What the SQL itself selects is
proved against PostgreSQL in ``test_search_window.py`` and ``test_current_snapshot_window.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable

from sqlalchemy.exc import OperationalError

from auditmanager.norms import current_snapshot as current_module
from auditmanager.norms.search import service as service_module

AT = datetime(2026, 10, 12, 9, 30, tzinfo=timezone.utc)


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def one_or_none(self) -> Any:
        assert len(self._rows) <= 1
        return self._rows[0] if self._rows else None

    def one(self) -> Any:
        assert len(self._rows) == 1
        return self._rows[0]

    def scalar_one(self) -> Any:
        row = self.one()
        return row[0] if isinstance(row, tuple) else row

    def all(self) -> list[Any]:
        return list(self._rows)


class _Cancelled(Exception):
    sqlstate = "57014"


class _OtherFailure(Exception):
    sqlstate = "40001"


@dataclass
class Document:
    norm_document_id: str
    norms_snapshot_id: str
    slug: str = "СП_54_13330_2022__Свод_правил__Здания_жилые"
    source_document_ref: str = "sp54"
    pdf_page_count: int = 40
    paragraph_count: int = 3
    unreliable_paragraph_count: int = 1
    #: ``(blob_id, sha256, size_bytes)`` of the confirmed PDF binding, or ``None``.
    pdf: tuple[str, str, int] | None = None


@dataclass
class FakeNorms:
    """The rows the statements read, and the history the setter writes."""

    snapshots: dict[str, tuple[bool, bool]] = field(default_factory=dict)
    documents: dict[str, Document] = field(default_factory=dict)
    current: SimpleNamespace | None = None
    events: list[SimpleNamespace] = field(default_factory=list)
    search_rows: list[Any] = field(default_factory=list)
    search_failure: str | None = None
    sent: list[str] = field(default_factory=list)
    timeouts: list[str] = field(default_factory=list)
    commits: int = 0

    # --- the session factory ---------------------------------------------------------------

    def __call__(self) -> "FakeSession":
        return FakeSession(self)

    def designate(self, snapshot: str, actor: str = "usr_01M2545JSD15ETSNNV904X991S") -> None:
        event = SimpleNamespace(
            event_id=f"evt_01M2545JSD15ETSNNV904X99{len(self.events):02d}",
            from_snapshot_id=None if self.current is None else self.current.norms_snapshot_id,
            to_snapshot_id=snapshot,
            actor_user_uid=actor,
            changed_at=AT,
        )
        self.events.append(event)
        self.current = SimpleNamespace(
            norms_snapshot_id=snapshot,
            event_id=event.event_id,
            changed_at=AT,
            actor_user_uid=actor,
        )

    # --- statements ------------------------------------------------------------------------

    def answer(self, statement: Any, parameters: dict[str, Any]) -> _Result:
        handlers: dict[int, tuple[str, Callable[[dict[str, Any]], list[Any]]]] = {
            id(service_module._SET_TIMEOUT): ("set_timeout", self._set_timeout),
            id(current_module._CURRENT): ("current", self._current),
            id(current_module._HAS_BEEN_CURRENT): ("has_been_current", self._has_been_current),
            id(current_module._LOCK): ("lock", lambda _: [(None,)]),
            id(current_module._QUALIFICATION): ("qualification", self._qualification),
            id(current_module._APPEND_EVENT): ("append_event", self._append_event),
            id(current_module._INSERT_CURRENT): ("insert_current", self._set_current),
            id(current_module._UPDATE_CURRENT): ("update_current", self._set_current),
            id(service_module._DOCUMENT): ("document", self._document),
            id(service_module._PDF_BINDING): ("pdf_binding", self._pdf_binding),
        }
        handled = handlers.get(id(statement))
        if handled is not None:
            name, handler = handled
            self.sent.append(name)
            return _Result(handler(parameters))
        sql = str(statement)
        if "websearch_to_tsquery" in sql or "array_to_string(d.designation_tokens" in sql:
            self.sent.append("search")
            if self.search_failure is not None:
                orig = _Cancelled() if self.search_failure == "cancel" else _OtherFailure()
                raise OperationalError(sql[:40], parameters, orig)
            return _Result(self.search_rows[: parameters["page_limit"]])
        raise AssertionError(f"an unexpected statement: {sql[:200]}")

    def _set_timeout(self, parameters: dict[str, Any]) -> list[Any]:
        self.timeouts.append(parameters["timeout"])
        return [(parameters["timeout"],)]

    def _current(self, _: dict[str, Any]) -> list[Any]:
        return [] if self.current is None else [self.current]

    def _has_been_current(self, parameters: dict[str, Any]) -> list[Any]:
        return [(any(e.to_snapshot_id == parameters["s"] for e in self.events),)]

    def _qualification(self, parameters: dict[str, Any]) -> list[Any]:
        found = self.snapshots.get(parameters["s"])
        if found is None:
            return []
        return [SimpleNamespace(build_complete=found[0], sources_confirmed=found[1])]

    def _append_event(self, parameters: dict[str, Any]) -> list[Any]:
        self.events.append(
            SimpleNamespace(
                event_id=parameters["event_id"],
                from_snapshot_id=parameters["from_id"],
                to_snapshot_id=parameters["to_id"],
                actor_user_uid=parameters["actor"],
                changed_at=AT,
            )
        )
        return [(AT,)]

    def _set_current(self, parameters: dict[str, Any]) -> list[Any]:
        event = next(e for e in self.events if e.event_id == parameters["event_id"])
        assert event.to_snapshot_id == parameters["to_id"]
        self.current = SimpleNamespace(
            norms_snapshot_id=parameters["to_id"],
            event_id=event.event_id,
            changed_at=event.changed_at,
            actor_user_uid=event.actor_user_uid,
        )
        return []

    def _document(self, parameters: dict[str, Any]) -> list[Any]:
        document = self.documents.get(parameters["document"])
        if document is None:
            return []
        return [
            SimpleNamespace(
                norm_document_id=document.norm_document_id,
                norms_snapshot_id=document.norms_snapshot_id,
                slug=document.slug,
                title="Свод правил. Здания жилые многоквартирные",
                doc_type="СП",
                drawn_on=date(2026, 7, 23),
                pdf_page_count=document.pdf_page_count,
                paragraph_count=document.paragraph_count,
                source_attribution="consultant_plus",
                unreliable_paragraph_count=document.unreliable_paragraph_count,
                content_available=document.pdf is not None,
            )
        ]

    def _pdf_binding(self, parameters: dict[str, Any]) -> list[Any]:
        document = self.documents.get(parameters["document"])
        if document is None:
            return []
        if document.pdf is None:
            return [SimpleNamespace(norm_document_id=document.norm_document_id, blob_id=None,
                                    sha256=None, size_bytes=None, media_type=None)]
        blob_id, sha256, size = document.pdf
        return [SimpleNamespace(norm_document_id=document.norm_document_id, blob_id=blob_id,
                                sha256=sha256, size_bytes=size, media_type="application/pdf")]


class FakeSession:
    def __init__(self, database: FakeNorms) -> None:
        self._database = database

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def execute(self, statement: Any, parameters: dict[str, Any] | None = None, **_: Any) -> Any:
        return self._database.answer(statement, dict(parameters or {}))

    def commit(self) -> None:
        self._database.commits += 1

    def rollback(self) -> None: ...

    def close(self) -> None: ...
