"""Part A, the reads: the positions of a page and «Спецификация по позициям» of a sheet pair (`CMP-VC-SPEC-01`).

Deterministic and read-only: nothing is written, enqueued or sent to a model, and PDFium is not called -- the words, the vector
lines and the title-block zone come from the stored page profile (:class:`~auditmanager.comparison.profile.reader.PageProfileReader`).

* :meth:`SpecificationReader.page_positions` answers ``getVersionPageSpecPositions``: whether the page is a specification sheet and
  the positions the parser (:mod:`.table`) reads from it, alone, as the page is.
* :meth:`SpecificationReader.pair_positions` answers ``getComparisonSheetPairSpecPositions``: the changes that fall on the pages of
  the pair, computed from the positions of the **whole specification of each version** (the stream across the pages of the
  version, ``spec.py:249-325``), so that a position that moved to another page is not a change.

Which pages make a version's specification. A page counts when its title block says so (:func:`~.table.is_spec_stamp`: the
designation ends in «СО», or the title says «Спецификация») -- a test on the small summary stored with the profile, so the archives
of a hundred drawings are not opened to find ten tables -- or when it is one of the pages of the pair read (which are confirmed by
their header anyway). Every candidate is then confirmed by the header test of the parser. The comparison is not made over a stream
with a hole in it (the original's rule, ``jobs.py:833`` and ``:855-864``, made stricter: the original looks at the pair's own pages,
this at every page of the stream): a side with no readable specification page, or a specification page whose table was not read,
gives ``is_specification: true`` and no change -- never a claim of removals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile.repository import PageProfileRepository
from auditmanager.comparison.specification import diff, table, views
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["PagePositions", "PairPositions", "SpecificationReader", "VersionStream", "page_ref", "spec_candidates"]

#: ``version_reader.MAX_VERSION_PAGES``: a version has at most this many pages.
_MAX_PAGES: Final[int] = 500

_PAIR = text(
    "SELECT p.comparison_sheet_pair_id, p.page_a_profile_id, p.page_b_profile_id, t.source_version_uid, t.target_version_uid "
    "FROM comparison_sheet_pair p JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
    "WHERE p.comparison_sheet_pair_id = :id"
)


def _not_found(what: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


def page_ref(row: PageProfileRow) -> dict[str, Any]:
    """The contract's reference to a page: the version, the page number inside it and the stored profile."""
    return {"version_uid": row.version_uid, "page_number": row.page_number, "page_profile_id": row.page_profile_id}


def spec_candidates(rows: list[PageProfileRow]) -> list[PageProfileRow]:
    """The pages of a version whose title block says «specification»: ready, with a text layer, not a scan."""
    out = []
    for row in rows:
        if not row.is_ready or not row.summary.get("text_layer") or row.summary.get("scan"):
            continue
        stamp = row.summary.get("stamp") or {}
        if table.is_spec_stamp(stamp.get("designation"), stamp.get("sheet_name")):
            out.append(row)
    return out


def parse_data(data: PageProfileData) -> dict[str, Any] | None:
    """The parser's answer for an opened profile: ``None`` (not a specification page) or the dictionary of
    :func:`~.table.parse_page`."""
    if not data.words:
        return None
    return table.parse_page(
        [[w.x0, w.top, w.x1, w.bottom, w.text] for w in data.words],
        [[ln.x0, ln.top, ln.x1, ln.bottom] for ln in data.lines],
        data.width_pt, data.height_pt, data.row.summary.get("stamp_zone"),
    )


@dataclass(frozen=True, slots=True)
class PagePositions:
    page_profile_id: str
    is_specification: bool
    items: list[dict[str, Any]]
    ref: dict[str, Any]


@dataclass(slots=True)
class VersionStream:
    """The specification of one version: its positions across its pages, and which pages were read."""

    version_uid: str
    items: list[dict[str, Any]] = field(default_factory=list)
    #: ``page number -> page reference`` of every page of the stream.
    refs: dict[int, dict[str, Any]] = field(default_factory=dict)
    parsed_pages: set[int] = field(default_factory=set)
    #: Candidate pages whose header was found and whose table was not read.
    unparsed_pages: set[int] = field(default_factory=set)
    #: The pages that were read, in page order, as :func:`~.source.build_source` takes them: ``{"page", "sheet", "name", "columns", "rows"}``.
    parsed: list[dict[str, Any]] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return bool(self.parsed_pages)


@dataclass(frozen=True, slots=True)
class PairPositions:
    sheet_pair_id: str
    is_specification: bool
    changes: list[dict[str, Any]]
    refs: dict[str, dict[int, dict[str, Any]]]


class SpecificationReader:
    def __init__(self, session_factory: sessionmaker[Session], blob_store: Any) -> None:
        self._factory = session_factory
        self._profiles = PageProfileReader(session_factory, blob_store)
        self._repository = PageProfileRepository()

    # -- one page -------------------------------------------------------------------------------------------------------

    def page_positions(self, page_profile_id: str) -> PagePositions:
        """``getVersionPageSpecPositions``. An unknown profile is ``not_found``."""
        row = self._profiles.get_profile(page_profile_id)
        data = self._profiles.open_profile(row)
        parsed = parse_data(data)
        ref = page_ref(row)
        if parsed is None:
            return PagePositions(page_profile_id, False, [], ref)
        if not parsed.get("parsed"):
            return PagePositions(page_profile_id, True, [], ref)
        flow = table.assemble([{"page": row.page_number, "rows": parsed["rows"]}])
        return PagePositions(page_profile_id, True, flow["items"], ref)

    # -- one version ----------------------------------------------------------------------------------------------------

    def version_rows(self, version_uid: str) -> list[PageProfileRow]:
        """The ready-or-not profiles of the version, in page order (the current algorithm's)."""
        rows, _more = self._profiles.list_profiles(version_uid, after_page=0, limit=_MAX_PAGES)
        return rows

    def version_stream(self, version_uid: str, *, extra: list[PageProfileRow] | None = None, rows: list[PageProfileRow] | None = None) -> VersionStream:
        """The stream of positions over the specification pages of a version, in page order."""
        rows = rows if rows is not None else self.version_rows(version_uid)
        pages = {row.page_number: row for row in spec_candidates(rows)}
        for row in extra or ():
            pages.setdefault(row.page_number, row)
        stream = VersionStream(version_uid)
        parsed_pages: list[dict[str, Any]] = []
        for number in sorted(pages):
            row = pages[number]
            data = self._profiles.open_profile(row)
            parsed = parse_data(data)
            if parsed is None:
                continue  # the stamp said «specification» and the page has no specification header: not a page of the stream
            stream.refs[number] = page_ref(row)
            if not parsed.get("parsed"):
                stream.unparsed_pages.add(number)
                continue
            stream.parsed_pages.add(number)
            parsed_pages.append({"page": number, "rows": parsed["rows"]})
            stamp = row.summary.get("stamp") or {}
            stream.parsed.append({
                "page": number, "sheet": stamp.get("sheet_number") or "", "name": stamp.get("sheet_name") or "",
                "columns": parsed["columns"], "rows": parsed["rows"],
            })
        stream.items = table.assemble(parsed_pages)["items"] if parsed_pages else []
        return stream

    # -- one sheet pair -------------------------------------------------------------------------------------------------

    def pair_positions(self, sheet_pair_id: str) -> PairPositions:
        """``getComparisonSheetPairSpecPositions``. An unknown pair is ``not_found``."""
        with session_scope(self._factory) as session:
            pair = session.execute(_PAIR, {"id": sheet_pair_id}).mappings().first()
            if pair is None:
                raise _not_found("ComparisonSheetPair")
            row_a = self._repository.get(session, pair["page_a_profile_id"]) if pair["page_a_profile_id"] else None
            row_b = self._repository.get(session, pair["page_b_profile_id"]) if pair["page_b_profile_id"] else None
        refs: dict[str, dict[int, dict[str, Any]]] = {"a": {}, "b": {}}
        sides = {"a": (pair["source_version_uid"], row_a), "b": (pair["target_version_uid"], row_b)}
        own_parse: dict[str, dict[str, Any] | None] = {}
        for key, (_version, row) in sides.items():
            if row is not None:
                own_parse[key] = parse_data(self._profiles.open_profile(row))
                refs[key][row.page_number] = page_ref(row)
        if not any(parsed is not None for parsed in own_parse.values()):
            return PairPositions(sheet_pair_id, False, [], refs)
        # A page of the pair that is a specification and whose table was not read, or a side without a readable page: nothing can be
        # claimed (the original keeps the overlay and adds SPEC_NOT_PARSED, ``jobs.py:855-864``).
        streams: dict[str, VersionStream] = {}
        for key, (version_uid, row) in sides.items():
            streams[key] = self.version_stream(version_uid, extra=[row] if row is not None else None)
            refs[key].update(streams[key].refs)
        for key, (_version, row) in sides.items():
            parsed = own_parse.get(key)
            if row is not None and parsed is not None and not parsed.get("parsed"):
                return PairPositions(sheet_pair_id, True, [], refs)
        # A stream with a hole (a specification page whose table was not read) would show the positions of the hole as removed or
        # added: nothing is claimed over it. The contract has no member for the reason; it is a FIX item (report section 9).
        if any(not stream.readable or stream.unparsed_pages for stream in streams.values()):
            return PairPositions(sheet_pair_id, True, [], refs)
        result = diff.compare(streams["a"].items, streams["b"].items)
        wanted: set[str] = set()
        for key, (_version, row) in sides.items():
            if row is not None and own_parse.get(key) is not None:
                wanted |= {c["id"] for c in diff.page_changes(result["changes"], key, row.page_number)}
        changes = [c for c in result["changes"] if c["id"] in wanted]
        return PairPositions(sheet_pair_id, True, changes, refs)

    # -- the views of the contract --------------------------------------------------------------------------------------

    def page_view(self, page_profile_id: str) -> dict[str, Any]:
        found = self.page_positions(page_profile_id)
        return views.page_view(
            found.page_profile_id, is_specification=found.is_specification, items=found.items,
            refs={found.ref["page_number"]: found.ref},
        )

    def pair_view(self, sheet_pair_id: str) -> dict[str, Any]:
        found = self.pair_positions(sheet_pair_id)
        return views.pair_view(found.sheet_pair_id, is_specification=found.is_specification, changes=found.changes, refs=found.refs)
