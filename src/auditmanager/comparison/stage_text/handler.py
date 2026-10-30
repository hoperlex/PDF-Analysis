"""Lease-fenced worker for a pinned, deterministic two-step Stage Text run."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from auditmanager.comparison.stage_links.read import StageSheetReadService
from auditmanager.comparison.work.model import (
    Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded,
)
from auditmanager.ingest.public import payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .differences import build_grouped_raw_differences
from .exact import SheetLink
from .fragments import FragmentRefused, extract_fragments
from .hints import find_cross_sheet_hints
from .recompute import WORK_KIND, StageTextRecomputeService
from .store import StageTextEvidenceStore

__all__ = ["StageTextRecomputeHandler", "stage_text_recompute_handler"]

_LOG = logging.getLogger(__name__)
_MAX_PAGES = 512


class StageTextRecomputeHandler:
    kind = WORK_KIND

    def __init__(self, dependencies: WorkDependencies, *, profile_reader: Any = None) -> None:
        self._deps = dependencies
        self._profile_reader = profile_reader
        self._runs = StageTextRecomputeService(dependencies.session_factory)
        self._sheets = StageSheetReadService(dependencies.session_factory)
        self._store = StageTextEvidenceStore(dependencies.session_factory)

    def _profiles(self) -> Any:
        if self._profile_reader is None:
            from auditmanager.comparison.public import PageProfileReader
            self._profile_reader = PageProfileReader(
                self._deps.session_factory, self._deps.blob_store,
            )
        return self._profile_reader

    def _set_state(self, item: WorkItem, run_id: str, state: str,
                   *, counts: dict[int, dict[str, int]] | None = None,
                   reason: str | None = None) -> None:
        with session_scope(self._deps.session_factory) as session:
            item.require_current(session)
            changed = session.execute(text(
                "UPDATE stage_chain_run r SET state = :state, failure_reason = :reason, "
                "updated_at = clock_timestamp() WHERE stage_chain_run_id = :run "
                "AND EXISTS (SELECT 1 FROM command_record c WHERE c.command_id = r.command_id "
                "AND c.command_type = 'recompute_stage_text_evidence') "
                "AND EXISTS (SELECT 1 FROM stage_pair p WHERE p.stage_pair_id = r.stage_pair_id "
                "AND p.project_uid = :project)"
            ), {"run": run_id, "state": state, "reason": reason,
                "project": item.project_uid}).rowcount
            if changed != 1:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageTextRun")
            for number in (2, 3):
                step_counts = (counts or {}).get(number, {})
                session.execute(text(
                    "UPDATE stage_chain_step SET state = :state, "
                    "counts = CAST(:counts AS jsonb), failure_reason = :reason, "
                    "started_at = CASE WHEN :state = 'running' "
                    "THEN coalesce(started_at, clock_timestamp()) ELSE started_at END, "
                    "finished_at = CASE WHEN :state IN ('completed', 'failed', 'cancelled') "
                    "THEN clock_timestamp() ELSE finished_at END, "
                    "updated_at = clock_timestamp() "
                    "WHERE stage_chain_run_id = :run AND step_no = :number"
                ), {"run": run_id, "number": number, "state": state,
                    "counts": json.dumps(step_counts), "reason": reason})

    def run(self, item: WorkItem) -> Outcome:
        run_id = item.payload.get("run_id") if isinstance(item.payload, dict) else None
        if (item.kind != WORK_KIND or item.module != "stages" or not isinstance(run_id, str)
                or set(item.payload) != {"run_id"}):
            return Failed("stage_text_payload_invalid")
        record = None
        try:
            record = self._runs.get(run_id)
            if record.state == "completed":
                return Completed()
            if record.state not in {"queued", "running"}:
                return Failed("stage_text_run_not_active")
            with session_scope(self._deps.session_factory) as session:
                project = session.execute(text(
                    "SELECT p.project_uid FROM stage_chain_run r "
                    "JOIN stage_pair p ON p.stage_pair_id = r.stage_pair_id "
                    "WHERE r.stage_chain_run_id = :run"
                ), {"run": run_id}).scalar_one_or_none()
                item.check_current(session)
            if project != item.project_uid:
                return Failed("stage_text_payload_scope_invalid")
            if record.stale:
                self._set_state(item, run_id, "failed", reason="stage_text_run_stale")
                return Failed("stage_text_run_stale")
            self._set_state(item, run_id, "running")
            passports = self._sheets.passports(pair_id=record.pair_id)
            if len(passports) > _MAX_PAGES or tuple(dict.fromkeys(
                page.version_uid for page in passports
            )) != record.pinned_version_uids:
                raise ValueError("stage_text_profile_pins_stale")
            actual_input_sha = payload_fingerprint({
                "revision_id": record.revision_id,
                "profiles": [page.profile_id for page in passports],
                "versions": list(record.pinned_version_uids),
            })
            if str(actual_input_sha) != record.input_sha256:
                raise ValueError("stage_text_profile_pins_stale")
            profile_reader = self._profiles()
            all_fragments = []
            dimensions: dict[str, tuple[float, float]] = {}
            for page in passports:
                if item.lease_lost.is_set():
                    return Yielded()
                if item.cancelled.is_set():
                    self._set_state(item, run_id, "cancelled", reason="stage_text_cancelled")
                    return Yielded()
                profile = profile_reader.read_page_profile(page.profile_id)
                if (profile.row.page_profile_id != page.profile_id
                        or profile.row.version_uid != page.version_uid
                        or profile.row.profile_blob_id is None):
                    raise ValueError("stage_text_profile_archive_missing")
                dimensions[page.profile_id] = (profile.width_pt, profile.height_pt)
                all_fragments.extend(extract_fragments(profile, side=page.side))
            manifest = {
                page.profile_id: frozenset(
                    f.content_key for f in all_fragments if f.profile_id == page.profile_id
                ) for page in passports
            }
            with session_scope(self._deps.session_factory) as session:
                item.check_current(session)
                pairs = session.execute(text(
                    "SELECT left_profile_id, right_profile_id FROM stage_link_item "
                    "WHERE stage_link_revision_id = :revision AND relation = 'paired' "
                    "ORDER BY row_no"
                ), {"revision": record.revision_id}).all()
            links = tuple(SheetLink(str(left), str(right)) for left, right in pairs)
            linked_ids = {ref for link in links for ref in
                          (link.left_profile_id, link.right_profile_id)}
            linked_fragments = tuple(f for f in all_fragments if f.profile_id in linked_ids)
            raw = build_grouped_raw_differences(
                links, linked_fragments,
                {key: value for key, value in dimensions.items() if key in linked_ids},
                {key: value for key, value in manifest.items() if key in linked_ids},
            )
            excluded = frozenset(
                key for e in raw.exact_exclusions
                for key in (e.left_content_key, e.right_content_key)
            )
            hints = find_cross_sheet_hints(links, all_fragments, manifest, excluded)
            self._store.write(
                pair_id=record.pair_id, revision_id=record.revision_id,
                fragments=tuple(all_fragments), expected_keys=manifest,
                raw=raw, hints=hints, work_item=item,
            )
            self._set_state(item, run_id, "completed", counts={
                2: {"fragments": len(all_fragments),
                    "exclusions": len(raw.exact_exclusions)},
                3: {"differences": len(raw.differences), "hints": len(hints)},
            })
            return Completed()
        except DomainError as error:
            if error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
                return Yielded()
            if record is None:
                return Failed("stage_text_run_not_found")
            reason = "stage_text_evidence_unavailable"
        except (FragmentRefused, ValueError) as error:
            reason = "stage_text_evidence_invalid"
            _LOG.warning("stage text run %s refused: %s", run_id, type(error).__name__)
        except SQLAlchemyError:
            reason = "stage_text_storage_failed"
            _LOG.exception("stage text run %s storage failed", run_id)
        try:
            self._set_state(item, run_id, "failed", reason=reason)
        except DomainError as error:
            if error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
                return Yielded()
            raise
        return Failed(reason)


def stage_text_recompute_handler(dependencies: WorkDependencies) -> StageTextRecomputeHandler:
    return StageTextRecomputeHandler(dependencies)
