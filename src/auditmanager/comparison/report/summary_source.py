"""What the MD summary reads from the database (`CMP-VC-REPORT-01`): the series, its transitions, their sheet pairs with the pages and the
stamp, the stored sheet descriptions and the whole-specification comparisons.

Reads only: no model call, no write. A sheet's current description is the newest row of ``comparison_sheet_description`` for its result (or
for its one page, when the sheet was added or removed); the earlier rows are the sheet's history and are not summarised. The shape of the
stored ``description`` is the contract's ``ComparisonSheetDescription`` (``changes``, ``unresolved``, …), read defensively: a member that is
absent is empty, and while no description exists the summary renders nothing for it.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.report.summary import (
    AiChange,
    SheetDescription,
    SheetInfo,
    SpecChangeInfo,
    SpecInfo,
    SummaryData,
    TransitionInfo,
    VersionInfo,
)

__all__ = ["SeriesRow", "SummaryReader"]

_SERIES = text(
    "SELECT s.comparison_series_id AS series_id, s.project_uid, s.document_uid, s.state, d.display_title "
    "FROM comparison_series s JOIN document d ON d.document_uid = s.document_uid WHERE s.comparison_series_id = :id"
)
_TRANSITIONS = text(
    "SELECT t.comparison_transition_id AS transition_id, t.transition_no, t.state, t.summary, t.verdict, t.updated_at, "
    "sv.version_ordinal AS source_ordinal, sv.source_filename AS source_file, "
    "tv.version_ordinal AS target_ordinal, tv.source_filename AS target_file "
    "FROM comparison_transition t "
    "JOIN document_version sv ON sv.version_uid = t.source_version_uid "
    "JOIN document_version tv ON tv.version_uid = t.target_version_uid "
    "WHERE t.comparison_series_id = :id ORDER BY t.transition_no"
)
_PAIRS = text(
    "SELECT p.comparison_transition_id AS transition_id, p.comparison_sheet_pair_id AS pair_id, p.pair_no, p.state, p.status, "
    "p.ai_dependent, p.result_id, p.page_a_profile_id, p.page_b_profile_id, p.updated_at, "
    "pa.page_number AS a_page, pa.profile->'stamp'->>'sheet_number' AS a_sheet, pa.profile->'stamp'->>'sheet_name' AS a_title, "
    "pb.page_number AS b_page, pb.profile->'stamp'->>'sheet_number' AS b_sheet, pb.profile->'stamp'->>'sheet_name' AS b_title "
    "FROM comparison_sheet_pair p "
    "LEFT JOIN comparison_page_profile pa ON pa.comparison_page_profile_id = p.page_a_profile_id "
    "LEFT JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
    "WHERE p.comparison_transition_id = ANY (CAST(:transitions AS text[])) ORDER BY p.comparison_transition_id, p.pair_no"
)
#: The newest description of every subject (a result, or one page): ``DISTINCT ON`` the subject, newest first.
_DESCRIPTIONS = text(
    "SELECT DISTINCT ON (subject) subject, state, description, recorded, model_identity, created_at FROM ("
    "SELECT coalesce(result_id, page_profile_id) AS subject, state, description, recorded, model_identity, created_at, "
    "comparison_sheet_description_id AS id FROM comparison_sheet_description WHERE project_uid = :project "
    "AND (result_id = ANY (CAST(:results AS text[])) OR page_profile_id = ANY (CAST(:pages AS text[])))) d "
    "ORDER BY subject, created_at DESC, id DESC"
)
_STAMPS = text(
    "SELECT DISTINCT ON (version_uid, page_number) version_uid, page_number, profile->'stamp'->>'sheet_number' AS sheet "
    "FROM comparison_page_profile WHERE version_uid = ANY (CAST(:versions AS text[])) AND page_number = ANY (CAST(:pages AS integer[])) "
    "ORDER BY version_uid, page_number, algo_version DESC"
)
_SPEC = text(
    "SELECT comparison_transition_id AS transition_id, state, changes, updated_at FROM comparison_spec_comparison "
    "WHERE comparison_transition_id = ANY (CAST(:transitions AS text[])) AND source = 'whole' "
    "AND state IN ('completed', 'incomplete')"
)


class SeriesRow:
    __slots__ = ("series_id", "project_uid", "document_uid", "state", "title")

    def __init__(self, series_id: str, project_uid: str, document_uid: str, state: str, title: str) -> None:
        self.series_id, self.project_uid, self.document_uid, self.state, self.title = series_id, project_uid, document_uid, state, title


def _str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _description(row: Mapping[str, Any]) -> SheetDescription:
    body = row["description"] if isinstance(row["description"], dict) else {}
    changes = []
    for item in body.get("changes") or []:
        if not isinstance(item, dict) or not _str(item.get("object_name")):
            continue
        changes.append(AiChange(
            change_id=_str(item.get("change_id")) or "c", object_name=item["object_name"],
            certainty=_str(item.get("certainty")) or "confirmed", kind=_str(item.get("kind")), place=_str(item.get("place")),
            was=_str(item.get("was")), now=_str(item.get("now")), was_tier=_str(item.get("was_tier")),
            now_tier=_str(item.get("now_tier")), limitation=_str(item.get("limitation")),
        ))
    unresolved = tuple(
        q["question"] for q in body.get("unresolved") or [] if isinstance(q, dict) and _str(q.get("question"))
    )
    summary = _str(body.get("summary")) or _str((body.get("single") or {}).get("summary") if isinstance(body.get("single"), dict) else None)
    return SheetDescription(
        state=row["state"], changes=tuple(changes), unresolved=unresolved, recorded=bool(row["recorded"]),
        model=_str(row["model_identity"]), created_at=row["created_at"], summary=summary,
    )


def _page_ref(position: Any) -> tuple[str | None, int | None]:
    """``(version_uid, page_number)`` of a position's page, when the position names one."""
    page = position.get("page") if isinstance(position, dict) else None
    if not isinstance(page, dict):
        return None, None
    number = page.get("page_number")
    return _str(page.get("version_uid")), number if isinstance(number, int) and number > 0 else None


_SPEC_KINDS: Final[frozenset[str]] = frozenset({"changed", "added", "removed", "unclear", "renumbered", "moved"})


def _spec_changes(raw: Any, sheets: Mapping[tuple[str, int], str] | None = None) -> tuple[SpecChangeInfo, ...]:
    sheets = sheets or {}
    out = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or item.get("kind") not in _SPEC_KINDS:
            continue
        fields = tuple(
            (str(f.get("field")), str(f.get("was") or ""), str(f.get("now") or ""))
            for f in item.get("fields") or [] if isinstance(f, dict) and f.get("field")
        )
        old_version, old_page = _page_ref(item.get("old"))
        new_version, new_page = _page_ref(item.get("new"))
        out.append(SpecChangeInfo(
            change_id=_str(item.get("change_id")) or "s", kind=item["kind"], text=_str(item.get("text")), fields=fields,
            old=item.get("old") if isinstance(item.get("old"), dict) else None,
            new=item.get("new") if isinstance(item.get("new"), dict) else None,
            old_page=old_page, new_page=new_page,
            old_sheet=sheets.get((old_version, old_page)) if old_version and old_page else None,
            new_sheet=sheets.get((new_version, new_page)) if new_version and new_page else None,
        ))
    return tuple(out)


class SummaryReader:
    """Stateless; every method takes the caller's session and only reads."""

    __slots__ = ()

    def series(self, session: Session, series_id: str) -> SeriesRow | None:
        row = session.execute(_SERIES, {"id": series_id}).mappings().first()
        if row is None:
            return None
        return SeriesRow(row["series_id"], row["project_uid"], row["document_uid"], row["state"], row["display_title"])

    def data(self, session: Session, series: SeriesRow) -> SummaryData:
        transitions = list(session.execute(_TRANSITIONS, {"id": series.series_id}).mappings())
        ids = [t["transition_id"] for t in transitions]
        pairs = list(session.execute(_PAIRS, {"transitions": ids}).mappings()) if ids else []
        results = [p["result_id"] for p in pairs if p["result_id"]]
        pages = [p["page_a_profile_id"] or p["page_b_profile_id"] for p in pairs if not p["result_id"]]
        found: dict[str, Mapping[str, Any]] = {}
        if results or pages:
            for row in session.execute(_DESCRIPTIONS, {"project": series.project_uid, "results": results, "pages": pages}).mappings():
                found[row["subject"]] = row
        specs = {
            row["transition_id"]: row for row in (session.execute(_SPEC, {"transitions": ids}).mappings() if ids else [])
        }
        sheets = self._sheet_numbers(session, [row["changes"] for row in specs.values()])
        stamps: list[datetime] = [t["updated_at"] for t in transitions] + [p["updated_at"] for p in pairs]
        stamps += [row["created_at"] for row in found.values()] + [row["updated_at"] for row in specs.values()]
        by_transition: dict[str, list[SheetInfo]] = {}
        for pair in pairs:
            subject = pair["result_id"] or pair["page_a_profile_id"] or pair["page_b_profile_id"]
            description = _description(found[subject]) if subject in found else None
            by_transition.setdefault(pair["transition_id"], []).append(SheetInfo(
                pair_no=pair["pair_no"], state=pair["state"], status=pair["status"], a_page=pair["a_page"], b_page=pair["b_page"],
                a_sheet=pair["a_sheet"], b_sheet=pair["b_sheet"], a_title=pair["a_title"], b_title=pair["b_title"],
                ai_dependent=bool(pair["ai_dependent"]), description=description,
            ))
        out = []
        for t in transitions:
            spec = specs.get(t["transition_id"])
            out.append(TransitionInfo(
                number=t["transition_no"], state=t["state"],
                source=VersionInfo(t["source_ordinal"], t["source_file"]), target=VersionInfo(t["target_ordinal"], t["target_file"]),
                summary=dict(t["summary"] or {}), verdict=tuple(t["verdict"] or ()), sheets=tuple(by_transition.get(t["transition_id"], ())),
                spec=None if spec is None else SpecInfo(
                    state=spec["state"], changes=_spec_changes(spec["changes"], sheets), updated_at=spec["updated_at"],
                ),
            ))
        return SummaryData(code=series.title, transitions=tuple(out), data_at=max(stamps) if stamps else None)

    @staticmethod
    def _sheet_numbers(session: Session, changes: list[Any]) -> dict[tuple[str, int], str]:
        """The sheet number (the stamp of the page profile) of every page a specification change names."""
        pages: set[tuple[str, int]] = set()
        for raw in changes:
            for item in raw if isinstance(raw, list) else []:
                for side in ("old", "new"):
                    version, number = _page_ref(item.get(side) if isinstance(item, dict) else None)
                    if version and number:
                        pages.add((version, number))
        if not pages:
            return {}
        rows = session.execute(_STAMPS, {
            "versions": sorted({v for v, _ in pages}), "pages": sorted({n for _, n in pages}),
        }).mappings()
        return {(r["version_uid"], r["page_number"]): r["sheet"] for r in rows if r["sheet"] and (r["version_uid"], r["page_number"]) in pages}

    @staticmethod
    def available(data: SummaryData) -> bool:
        """The summary exists once a sheet is described or a specification is compared (the contract of ``streamComparisonSeriesSummary``)."""
        return any(
            t.spec is not None or any(s.description is not None for s in t.sheets) for t in data.transitions
        )
