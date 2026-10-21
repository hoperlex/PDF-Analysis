"""Statements over the four tables of migration ``0026_price_lists``. No rule lives here.

Writers serialise on transaction advisory locks -- one per project for price lists, one per
(project or global, section) for vendor lists -- so two concurrent writers never compute the
same next ``revision_number``; the unique constraints are the backstop. The locks are released
at commit or rollback and are never held across an object-store call.

Positions are written with one statement per chunk: the rows travel as one JSON array and
``jsonb_to_recordset`` expands them, so a 20 000-row price list is a handful of round trips
and each unit price reaches ``numeric`` from its exact decimal text, never through a float.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from .identity import PriceListId, PriceListPositionId, VendorListId
from .parsing import ParsedPosition, price_text
from .policy import VendorListEntry

__all__ = [
    "OptimisationRepository",
    "PriceListPositionRecord",
    "PriceListRevisionRecord",
    "VendorListRevisionRecord",
]

_POSITION_CHUNK: Final[int] = 2000

_PRICE_LIST_COLUMNS = (
    "r.price_list_id, r.project_uid, r.revision_number, r.uploaded_by_user_uid, "
    "r.uploaded_at, r.blob_id, r.sha256, r.size_bytes, r.media_type, r.source_format, "
    "r.source_filename, r.default_currency, r.parse_report, r.data_row_count, "
    "r.accepted_row_count, r.skipped_row_count, "
    "(r.revision_number = (SELECT max(c.revision_number) FROM price_list_revision c "
    "WHERE c.project_uid = r.project_uid)) AS is_current"
)
_SELECT_PRICE_LIST = text(
    f"SELECT {_PRICE_LIST_COLUMNS} FROM price_list_revision r WHERE r.price_list_id = :id"
)
_LIST_PRICE_LISTS = text(
    f"SELECT {_PRICE_LIST_COLUMNS} FROM price_list_revision r "
    "WHERE r.project_uid = :project ORDER BY r.revision_number DESC"
)
_LOCK_PROJECT_PRICE_LISTS = text(
    "SELECT pg_advisory_xact_lock(hashtextextended('auditmanager.price_list|' || :project, 0))"
)
_NEXT_PRICE_LIST_NUMBER = text(
    "SELECT COALESCE(max(revision_number), 0) + 1 FROM price_list_revision "
    "WHERE project_uid = :project"
)
_INSERT_PRICE_LIST = text(
    "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, "
    "uploaded_by_user_uid, blob_id, sha256, size_bytes, media_type, source_format, "
    "source_filename, default_currency, parse_report, data_row_count, accepted_row_count, "
    "skipped_row_count) VALUES (:price_list_id, :project_uid, :revision_number, "
    ":uploaded_by_user_uid, :blob_id, :sha256, :size_bytes, :media_type, :source_format, "
    ":source_filename, :default_currency, CAST(:parse_report AS jsonb), :data_row_count, "
    ":accepted_row_count, :skipped_row_count)"
)
_INSERT_POSITIONS = text(
    "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, "
    "code, name, mark, unit, unit_price, currency, vendor, section_code) "
    "SELECT p.id, :price_list_id, p.row_number, p.code, p.name, p.mark, p.unit, "
    "CAST(p.unit_price AS numeric), p.currency, p.vendor, p.section_code "
    "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS p(id text, row_number integer, "
    "code text, name text, mark text, unit text, unit_price text, currency text, "
    "vendor text, section_code text)"
)
_POSITION_PAGE = text(
    "SELECT price_list_position_id, price_list_id, row_number, code, name, mark, unit, "
    "unit_price, currency, vendor, section_code FROM price_list_position "
    "WHERE price_list_id = :id ORDER BY row_number LIMIT :limit OFFSET :offset"
)

_VENDOR_COLUMNS = (
    "v.vendor_list_id, v.scope, v.project_uid, v.section_code, v.mode, v.revision_number, "
    "v.entry_count, v.set_by_user_uid, v.set_at"
)
_LOCK_VENDOR_SCOPE = text(
    "SELECT pg_advisory_xact_lock(hashtextextended("
    "'auditmanager.vendor_list|' || COALESCE(:project, '*') || '|' || :section, 0))"
)
_LATEST_VENDOR_LIST = text(
    f"SELECT {_VENDOR_COLUMNS} FROM vendor_list_revision v "
    "WHERE v.project_uid IS NOT DISTINCT FROM :project AND v.section_code = :section "
    "ORDER BY v.revision_number DESC LIMIT 1"
)
_LATEST_VENDOR_LISTS = text(
    f"SELECT DISTINCT ON (v.section_code) {_VENDOR_COLUMNS} FROM vendor_list_revision v "
    "WHERE v.project_uid IS NOT DISTINCT FROM :project "
    "ORDER BY v.section_code, v.revision_number DESC"
)
_VENDOR_HISTORY = text(
    f"SELECT {_VENDOR_COLUMNS} FROM vendor_list_revision v "
    "WHERE v.project_uid IS NOT DISTINCT FROM :project AND v.section_code = :section "
    "ORDER BY v.revision_number DESC LIMIT :limit"
)
_SELECT_VENDOR_LIST = text(
    f"SELECT {_VENDOR_COLUMNS} FROM vendor_list_revision v WHERE v.vendor_list_id = :id"
)
_INSERT_VENDOR_LIST = text(
    "INSERT INTO vendor_list_revision (vendor_list_id, scope, project_uid, section_code, mode, "
    "revision_number, entry_count, set_by_user_uid) VALUES (:vendor_list_id, :scope, "
    ":project_uid, :section_code, :mode, :revision_number, :entry_count, :set_by_user_uid)"
)
_INSERT_ENTRIES = text(
    "INSERT INTO vendor_list_entry (vendor_list_id, ordinal, material, vendor, note) "
    "SELECT :vendor_list_id, e.ordinal, e.material, e.vendor, e.note "
    "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS e(ordinal integer, material text, "
    "vendor text, note text)"
)
_ENTRIES_OF = text(
    "SELECT vendor_list_id, material, vendor, note FROM vendor_list_entry "
    "WHERE vendor_list_id = ANY(:ids) ORDER BY vendor_list_id, ordinal"
)


@dataclass(frozen=True, slots=True)
class PriceListRevisionRecord:
    """One uploaded price list. ``source_filename`` is display only; ``is_current`` derived."""

    price_list_id: str
    project_uid: str
    revision_number: int
    uploaded_by_user_uid: str
    uploaded_at: datetime
    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str
    source_format: str
    source_filename: str
    default_currency: str | None
    parse_report: Mapping[str, Any]
    data_row_count: int
    accepted_row_count: int
    skipped_row_count: int
    is_current: bool


@dataclass(frozen=True, slots=True)
class PriceListPositionRecord:
    """One stored position. ``row_number`` is the source row; the identity is the id."""

    price_list_position_id: str
    price_list_id: str
    row_number: int
    code: str | None
    name: str
    mark: str | None
    unit: str
    unit_price: Decimal
    currency: str
    vendor: str | None
    section_code: str | None


@dataclass(frozen=True, slots=True)
class VendorListRevisionRecord:
    """One vendor-list revision with its entries in order."""

    vendor_list_id: str
    scope: str
    project_uid: str | None
    section_code: str
    mode: str
    revision_number: int
    entry_count: int
    set_by_user_uid: str
    set_at: datetime
    entries: tuple[VendorListEntry, ...]


def _price_list(row: Any) -> PriceListRevisionRecord:
    values = tuple(row)
    report = values[12]
    if isinstance(report, str):  # pragma: no cover - psycopg decodes jsonb
        report = json.loads(report)
    return PriceListRevisionRecord(
        price_list_id=values[0],
        project_uid=values[1],
        revision_number=int(values[2]),
        uploaded_by_user_uid=values[3],
        uploaded_at=values[4],
        blob_id=values[5],
        sha256=values[6],
        size_bytes=int(values[7]),
        media_type=values[8],
        source_format=values[9],
        source_filename=values[10],
        default_currency=values[11],
        parse_report=report,
        data_row_count=int(values[13]),
        accepted_row_count=int(values[14]),
        skipped_row_count=int(values[15]),
        is_current=bool(values[16]),
    )


def _position(row: Any) -> PriceListPositionRecord:
    values = tuple(row)
    return PriceListPositionRecord(
        price_list_position_id=values[0],
        price_list_id=values[1],
        row_number=int(values[2]),
        code=values[3],
        name=values[4],
        mark=values[5],
        unit=values[6],
        unit_price=Decimal(values[7]),
        currency=values[8],
        vendor=values[9],
        section_code=values[10],
    )


class OptimisationRepository:
    """Write and read price lists, positions and vendor lists."""

    __slots__ = ()

    # -- price lists ---------------------------------------------------------

    def lock_project_price_lists(self, session: Session, project_uid: str) -> None:
        session.execute(_LOCK_PROJECT_PRICE_LISTS, {"project": project_uid})

    def next_price_list_number(self, session: Session, project_uid: str) -> int:
        return int(session.execute(_NEXT_PRICE_LIST_NUMBER, {"project": project_uid}).scalar_one())

    def insert_price_list(
        self,
        session: Session,
        *,
        price_list_id: PriceListId,
        project_uid: str,
        revision_number: int,
        uploaded_by_user_uid: str,
        blob_id: str,
        sha256: str,
        size_bytes: int,
        media_type: str,
        source_format: str,
        source_filename: str,
        default_currency: str | None,
        parse_report: Mapping[str, Any],
        data_row_count: int,
        accepted_row_count: int,
        skipped_row_count: int,
    ) -> None:
        session.execute(
            _INSERT_PRICE_LIST,
            {
                "price_list_id": str(price_list_id),
                "project_uid": project_uid,
                "revision_number": revision_number,
                "uploaded_by_user_uid": uploaded_by_user_uid,
                "blob_id": blob_id,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "media_type": media_type,
                "source_format": source_format,
                "source_filename": source_filename,
                "default_currency": default_currency,
                "parse_report": json.dumps(dict(parse_report), ensure_ascii=False, sort_keys=True),
                "data_row_count": data_row_count,
                "accepted_row_count": accepted_row_count,
                "skipped_row_count": skipped_row_count,
            },
        )

    def insert_positions(
        self, session: Session, price_list_id: PriceListId, positions: Sequence[ParsedPosition]
    ) -> None:
        for start in range(0, len(positions), _POSITION_CHUNK):
            rows = [
                {
                    "id": str(PriceListPositionId.new()),
                    "row_number": position.row_number,
                    "code": position.code,
                    "name": position.name,
                    "mark": position.mark,
                    "unit": position.unit,
                    "unit_price": price_text(position),
                    "currency": position.currency,
                    "vendor": position.vendor,
                    "section_code": position.section_code,
                }
                for position in positions[start : start + _POSITION_CHUNK]
            ]
            session.execute(
                _INSERT_POSITIONS,
                {"price_list_id": str(price_list_id), "rows": json.dumps(rows, ensure_ascii=False)},
            )

    def get_price_list(self, session: Session, price_list_id: str) -> PriceListRevisionRecord | None:
        row = session.execute(_SELECT_PRICE_LIST, {"id": price_list_id}).first()
        return None if row is None else _price_list(row)

    def list_price_lists(
        self, session: Session, project_uid: str
    ) -> tuple[PriceListRevisionRecord, ...]:
        rows = session.execute(_LIST_PRICE_LISTS, {"project": project_uid}).all()
        return tuple(_price_list(row) for row in rows)

    def position_page(
        self, session: Session, price_list_id: str, *, offset: int, limit: int
    ) -> tuple[PriceListPositionRecord, ...]:
        rows = session.execute(
            _POSITION_PAGE, {"id": price_list_id, "offset": offset, "limit": limit}
        ).all()
        return tuple(_position(row) for row in rows)

    # -- vendor lists --------------------------------------------------------

    def lock_vendor_scope(self, session: Session, *, project_uid: str | None, section: str) -> None:
        session.execute(_LOCK_VENDOR_SCOPE, {"project": project_uid, "section": section})

    def latest_vendor_list(
        self, session: Session, *, project_uid: str | None, section: str
    ) -> VendorListRevisionRecord | None:
        row = session.execute(
            _LATEST_VENDOR_LIST, {"project": project_uid, "section": section}
        ).first()
        return None if row is None else self._with_entries(session, [row])[0]

    def latest_vendor_lists(
        self, session: Session, *, project_uid: str | None
    ) -> dict[str, VendorListRevisionRecord]:
        rows = session.execute(_LATEST_VENDOR_LISTS, {"project": project_uid}).all()
        return {record.section_code: record for record in self._with_entries(session, rows)}

    def vendor_list_history(
        self, session: Session, *, project_uid: str | None, section: str, limit: int
    ) -> tuple[VendorListRevisionRecord, ...]:
        rows = session.execute(
            _VENDOR_HISTORY, {"project": project_uid, "section": section, "limit": limit}
        ).all()
        return tuple(self._with_entries(session, rows))

    def get_vendor_list(self, session: Session, vendor_list_id: str) -> VendorListRevisionRecord | None:
        row = session.execute(_SELECT_VENDOR_LIST, {"id": vendor_list_id}).first()
        return None if row is None else self._with_entries(session, [row])[0]

    def insert_vendor_list(
        self,
        session: Session,
        *,
        vendor_list_id: VendorListId,
        scope: str,
        project_uid: str | None,
        section: str,
        mode: str,
        revision_number: int,
        entries: Sequence[VendorListEntry],
        set_by_user_uid: str,
    ) -> None:
        session.execute(
            _INSERT_VENDOR_LIST,
            {
                "vendor_list_id": str(vendor_list_id),
                "scope": scope,
                "project_uid": project_uid,
                "section_code": section,
                "mode": mode,
                "revision_number": revision_number,
                "entry_count": len(entries),
                "set_by_user_uid": set_by_user_uid,
            },
        )
        if entries:
            rows = [
                {
                    "ordinal": ordinal,
                    "material": entry.material,
                    "vendor": entry.vendor,
                    "note": entry.note,
                }
                for ordinal, entry in enumerate(entries, start=1)
            ]
            session.execute(
                _INSERT_ENTRIES,
                {"vendor_list_id": str(vendor_list_id), "rows": json.dumps(rows, ensure_ascii=False)},
            )

    @staticmethod
    def _with_entries(session: Session, rows: Sequence[Any]) -> list[VendorListRevisionRecord]:
        heads = [tuple(row) for row in rows]
        if not heads:
            return []
        entries: dict[str, list[VendorListEntry]] = {}
        for vendor_list_id, material, vendor, note in session.execute(
            _ENTRIES_OF, {"ids": [head[0] for head in heads]}
        ):
            entries.setdefault(vendor_list_id, []).append(VendorListEntry(material, vendor, note))
        return [
            VendorListRevisionRecord(
                vendor_list_id=head[0],
                scope=head[1],
                project_uid=head[2],
                section_code=head[3],
                mode=head[4],
                revision_number=int(head[5]),
                entry_count=int(head[6]),
                set_by_user_uid=head[7],
                set_at=head[8],
                entries=tuple(entries.get(head[0], ())),
            )
            for head in heads
        ]
