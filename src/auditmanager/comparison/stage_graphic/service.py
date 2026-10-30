"""Stage link→existing engine bridge. One durable link per advance, no synthetic pair IDs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_sheets.material import ProfileMaterial
from auditmanager.comparison.engine import ENGINE_ALGO_VERSION, PairResultRepository, compare_sheet_pair
from auditmanager.comparison.engine.key import content_key as engine_content_key
from auditmanager.comparison.engine.runner import ChildStartError
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.work.model import Failed, WorkItem, Yielded
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import StageGraphicEvidenceId

from .evidence import digest, project_result

_VERSION = "stage-graphic/1"
_MAX_LINKS = 1024
_MAX_CROP_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class GraphicCrop:
    evidence_id: str
    region_key: str
    side: str
    profile_id: str
    box: tuple[float, float, float, float]
    data: bytes
    sha256: str


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


class StageGraphicService:
    def __init__(self, sessions: sessionmaker[Session], *, blob_store: Any,
                 runner: Any = None, material: Any = None) -> None:
        self._sessions = sessions
        self._store = blob_store
        self._runner = runner
        self._material = material

    @staticmethod
    def _run(session: Session, run_id: str) -> dict[str, Any]:
        row = session.execute(text(
            "SELECT r.*,p.project_uid,coalesce(r.effective_link_revision_id,r.stage_link_revision_id) AS revision_id "
            "FROM stage_chain_run r JOIN stage_pair p ON p.stage_pair_id=r.stage_pair_id "
            "WHERE r.stage_chain_run_id=:run"
        ), {"run": run_id}).mappings().first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
        return dict(row)

    @classmethod
    def _fence(cls, session: Session, item: WorkItem, run_id: str, revision_id: str) -> dict[str, Any]:
        item.require_current(session)
        run = cls._run(session, run_id)
        # Same map lock as the map writer, acquired only for short publication transactions.
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                        {"key": "stage_link:" + run["stage_pair_id"]})
        latest = session.execute(text(
            "SELECT stage_link_revision_id FROM stage_link_revision WHERE stage_pair_id=:pair "
            "ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": run["stage_pair_id"]}).scalar_one_or_none()
        stale_versions = session.execute(text(
            "SELECT EXISTS(SELECT 1 FROM document_version v WHERE v.version_uid=ANY(CAST(:pins AS text[])) "
            "AND v.version_ordinal<>(SELECT max(n.version_ordinal) FROM document_version n WHERE n.document_uid=v.document_uid))"
        ), {"pins": list(run["pinned_version_uids"])}).scalar_one()
        if (item.project_uid != run["project_uid"] or item.kind != "stage_chain" or item.module != "stages"
                or item.payload.get("run_id") != run_id or run["kind"] != "full"
                or run["state"] != "running" or run["revision_id"] != revision_id
                or latest != revision_id or stale_versions):
            raise _conflict("stage_graphic_run_scope_invalid")
        return run

    @staticmethod
    def _links(session: Session, revision_id: str) -> list[dict[str, Any]]:
        rows = [dict(row) for row in session.execute(text(
            "SELECT i.*,l.content_key AS left_key,l.status AS left_status,l.profile AS left_summary,"
            "r.content_key AS right_key,r.status AS right_status,r.profile AS right_summary,"
            "(SELECT count(*) FROM stage_link_item x WHERE x.stage_link_revision_id=i.stage_link_revision_id "
            "AND x.left_profile_id=i.left_profile_id) AS left_degree,"
            "(SELECT count(*) FROM stage_link_item x WHERE x.stage_link_revision_id=i.stage_link_revision_id "
            "AND x.right_profile_id=i.right_profile_id) AS right_degree "
            "FROM stage_link_item i LEFT JOIN comparison_page_profile l ON l.comparison_page_profile_id=i.left_profile_id "
            "LEFT JOIN comparison_page_profile r ON r.comparison_page_profile_id=i.right_profile_id "
            "WHERE i.stage_link_revision_id=:revision ORDER BY i.row_no LIMIT 1025"
        ), {"revision": revision_id}).mappings()]
        if len(rows) > _MAX_LINKS:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_chain_run_id",
                              constraint="stage_graphic_link_budget")
        return rows

    @staticmethod
    def _key(run_id: str, link: dict[str, Any]) -> str:
        return digest({"format": _VERSION, "engine": ENGINE_ALGO_VERSION, "run_id": run_id,
                       "link_id": link["stage_link_item_id"], "left": link["left_profile_id"],
                       "right": link["right_profile_id"], "left_key": link["left_key"],
                       "right_key": link["right_key"], "relation": link["relation"],
                       "confidence": link["confidence"], "degrees": [link["left_degree"], link["right_degree"]]})

    @staticmethod
    def _refusal(link: dict[str, Any]) -> str | None:
        if link["relation"] != "paired" or not link["left_profile_id"] or not link["right_profile_id"]:
            return "graphics_not_checked_unpaired_link"
        if link["left_degree"] != 1 or link["right_degree"] != 1:
            return "graphics_not_checked_many_to_many"
        if link["confidence"] in {"review", "unpaired"}:
            return "graphics_not_checked_source_link_uncertain"
        if link["left_status"] != "ready" or link["right_status"] != "ready":
            return "graphics_not_checked_profile_unavailable"
        return None

    @staticmethod
    def _counts(session: Session, run_id: str, keys: list[str]) -> dict[str, int]:
        rows = session.execute(text(
            "SELECT status,count(*),sum(jsonb_array_length(regions)) FROM stage_graphic_evidence "
            "WHERE stage_chain_run_id=:run AND content_key=ANY(CAST(:keys AS text[])) GROUP BY status"
        ), {"run": run_id, "keys": keys}).all()
        counts = {"graphic_total": 0, "graphic_reliable": 0, "graphic_unreliable": 0,
                  "graphic_not_checked": 0, "graphic_regions": 0}
        for status, count, regions in rows:
            counts["graphic_total"] += int(count)
            counts[f"graphic_{status}"] = int(count)
            counts["graphic_regions"] += int(regions or 0)
        return counts

    def advance(self, item: WorkItem, run_id: str) -> dict[str, int] | Yielded | Failed:
        with session_scope(self._sessions) as session:
            run = self._run(session, run_id)
            revision_id = run["revision_id"]
            self._fence(session, item, run_id, revision_id)
            links = self._links(session, revision_id)
            keyed = [(self._key(run_id, link), link) for link in links]
            existing = set(session.execute(text(
                "SELECT content_key FROM stage_graphic_evidence WHERE stage_chain_run_id=:run"
            ), {"run": run_id}).scalars())
            pending = [(key, link) for key, link in keyed if key not in existing]
            if not pending:
                return self._counts(session, run_id, [key for key, _ in keyed])
        key, link = pending[0]
        reason = self._refusal(link)
        status, regions, result_id = "not_checked", [], None
        if reason is None:
            reader = PageProfileReader(self._sessions, self._store)
            expected_engine_key = engine_content_key(run["project_uid"],
                reader.get_profile(link["left_profile_id"]), reader.get_profile(link["right_profile_id"]))
            def before_publish() -> None:
                with session_scope(self._sessions) as opened:
                    self._fence(opened, item, run_id, revision_id)
            try:
                outcome = compare_sheet_pair(
                    self._sessions, self._store, project_uid=run["project_uid"],
                    page_a_profile_id=link["left_profile_id"], page_b_profile_id=link["right_profile_id"],
                    runner=self._runner, before_publish=before_publish,
                    fence=lambda opened: self._fence(opened, item, run_id, revision_id))
            except ChildStartError:
                return Failed("stage_graphic_child_unavailable", retry=True)
            result_id = outcome.result_id
            with session_scope(self._sessions) as session:
                stored = PairResultRepository().get(session, result_id) if result_id else None
            # The engine cache is keyed by page content, not profile identity: an
            # identical page of another version in this project may own its row.
            if (stored is None or stored.project_uid != run["project_uid"]
                    or stored.content_key != expected_engine_key):
                raise _conflict("stage_graphic_engine_result_scope_invalid")
            a, b = link["left_summary"], link["right_summary"]
            status, reason, regions = project_result(stored,
                left_size=(float(a.get("width_pt", 0)), float(a.get("height_pt", 0))),
                right_size=(float(b.get("width_pt", 0)), float(b.get("height_pt", 0))))
        with session_scope(self._sessions) as session:
            self._fence(session, item, run_id, revision_id)
            session.execute(text(
                "INSERT INTO stage_graphic_evidence(stage_graphic_evidence_id,stage_chain_run_id,stage_link_item_id,"
                "left_profile_id,right_profile_id,comparison_sheet_pair_result_id,status,reason,regions,content_key) "
                "VALUES(:id,:run,:link,:left,:right,:result,:status,:reason,CAST(:regions AS jsonb),:key) "
                "ON CONFLICT(stage_chain_run_id,content_key) DO NOTHING"
            ), {"id": str(StageGraphicEvidenceId.new()), "run": run_id, "link": link["stage_link_item_id"],
                "left": link["left_profile_id"], "right": link["right_profile_id"], "result": result_id,
                "status": status, "reason": reason, "regions": json.dumps(regions, allow_nan=False), "key": key})
            if len(pending) > 1:
                return Yielded(0)
            return self._counts(session, run_id, [key for key, _ in keyed])

    def evidence(self, run_id: str) -> tuple[dict[str, Any], ...]:
        """Atomic sge identities, only registered nonempty graphics; full raw region list."""
        with session_scope(self._sessions) as session:
            self._run(session, run_id)
            rows = session.execute(text(
                "SELECT g.stage_graphic_evidence_id AS evidence_id,g.content_key,g.left_profile_id,g.right_profile_id,"
                "g.status,g.regions FROM stage_graphic_evidence g JOIN stage_link_item i "
                "ON i.stage_link_item_id=g.stage_link_item_id JOIN stage_chain_run r ON r.stage_chain_run_id=g.stage_chain_run_id "
                "WHERE g.stage_chain_run_id=:run AND i.stage_link_revision_id=coalesce(r.effective_link_revision_id,r.stage_link_revision_id) "
                "AND g.status='reliable' AND jsonb_array_length(g.regions)>0 ORDER BY g.content_key"
            ), {"run": run_id}).mappings().all()
            return tuple(dict(row) for row in rows)

    def page(self, run_id: str, after: str | None = None, limit: int = 100
             ) -> tuple[tuple[dict[str, Any], ...], str | None]:
        """Frozen listStageGraphicEvidence DTOs, including explicit unchecked statuses."""
        if not 1 <= limit <= 500:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="limit", constraint="range")
        with session_scope(self._sessions) as session:
            self._run(session, run_id)
            if after and not session.execute(text(
                "SELECT 1 FROM stage_graphic_evidence WHERE stage_chain_run_id=:run AND content_key=:after"
            ), {"run": run_id, "after": after}).first():
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
            records = session.execute(text(
                "SELECT stage_graphic_evidence_id AS graphic_id,stage_chain_run_id AS run_id,"
                "stage_link_item_id AS link_item_id,left_profile_id,right_profile_id,"
                "comparison_sheet_pair_result_id AS result_id,status,reason,regions,content_key "
                "FROM stage_graphic_evidence WHERE stage_chain_run_id=:run AND content_key>:after "
                "ORDER BY content_key LIMIT :limit"
            ), {"run": run_id, "after": after or "", "limit": limit + 1}).mappings().all()
            visible = tuple({k: v for k, v in row.items() if v is not None} for row in records[:limit])
            return visible, visible[-1]["content_key"] if len(records) > limit else None

    def crop_plan(self, run_id: str, evidence_id: str, after: str | None = None, limit: int = 4
                  ) -> tuple[tuple[dict[str, Any], ...], str | None]:
        if not 1 <= limit <= 4:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="limit", constraint="range")
        evidence = next((e for e in self.evidence(run_id) if e["evidence_id"] == evidence_id), None)
        if evidence is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageGraphicEvidence")
        regions = evidence["regions"]
        if after is not None and not any(r["region_key"] == after for r in regions):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
        pending = [region for region in regions if after is None or region["region_key"] > after]
        selected = tuple({"region_key": r["region_key"], "left_profile_id": evidence["left_profile_id"],
                          "right_profile_id": evidence["right_profile_id"], "left_box": r["left_box"],
                          "right_box": r["right_box"], "region_class": r["region_class"],
                          "registration": r["registration"]} for r in pending[:limit])
        return selected, selected[-1]["region_key"] if len(pending) > limit else None

    def crop(self, run_id: str, evidence_id: str, region_key: str, side: str,
             long_side_px: int = 1400) -> GraphicCrop:
        if side not in {"left", "right"} or not 128 <= long_side_px <= 1950:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="crop", constraint="bounded_source")
        evidence = next((e for e in self.evidence(run_id) if e["evidence_id"] == evidence_id), None)
        if evidence is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageGraphicEvidence")
        region = next((r for r in evidence["regions"] if r["region_key"] == region_key), None)
        if region is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageGraphicRegion")
        profile_id, box = evidence[f"{side}_profile_id"], tuple(region[f"{side}_box"])
        material = self._material or ProfileMaterial(PageProfileReader(self._sessions, self._store))
        data = material.crop(profile_id, box, long_side_px=long_side_px)
        if not data or not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > _MAX_CROP_BYTES:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="stage_graphic_crop")
        return GraphicCrop(evidence_id, region_key, side, profile_id, box, data, hashlib.sha256(data).hexdigest())
