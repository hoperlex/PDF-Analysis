"""Transactional, append-only storage for one current Stage Text map revision.

This is a worker-side repository, not an API entrypoint. The future run handler
owns complete profile extraction, pinned-version checks and the empty-result seal.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Sequence

if TYPE_CHECKING:
    from auditmanager.comparison.work.model import WorkItem

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    StageTextDifferenceId, StageTextExclusionId, StageTextFragmentId, StageTextHintId,
)

from .differences import RawTextPass
from .fragments import TextFragment
from .hints import CrossSheetHint

__all__ = ["EvidenceWrite", "StageTextEvidenceStore"]


@dataclass(frozen=True, slots=True)
class EvidenceWrite:
    fragment_count: int
    exclusion_count: int
    difference_count: int
    hint_count: int
    replayed: bool


def _digest(kind: str, revision_id: str, *parts: str | None) -> str:
    body = json.dumps(["stage-text-store-v1", kind, revision_id, *parts],
                      ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


class StageTextEvidenceStore:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    @staticmethod
    def _validate_batch(
        fragments: Sequence[TextFragment], raw: RawTextPass,
        hints: Sequence[CrossSheetHint], expected_keys: Mapping[str, frozenset[str]],
    ) -> dict[str, TextFragment]:
        if len(fragments) > 20_000 or len(hints) > 20_000 or len(expected_keys) > 20_000:
            raise ValueError("stage_text_store_budget_exceeded")
        by_key = {fragment.content_key: fragment for fragment in fragments}
        if len(by_key) != len(fragments):
            raise ValueError("duplicate_fragment_key")
        actual: dict[str, set[str]] = {profile: set() for profile in expected_keys}
        for fragment in fragments:
            if fragment.profile_id not in actual:
                raise ValueError("fragment_manifest_invalid")
            actual[fragment.profile_id].add(fragment.content_key)
        if any(frozenset(actual[profile]) != keys for profile, keys in expected_keys.items()):
            raise ValueError("fragment_manifest_mismatch")
        if any(fragment.side not in {"left", "right"} for fragment in fragments):
            raise ValueError("fragment_manifest_invalid")
        used_left: set[str] = set()
        used_right: set[str] = set()
        for exclusion in raw.exact_exclusions:
            left, right = by_key.get(exclusion.left_content_key), by_key.get(exclusion.right_content_key)
            if (left is None or right is None or left.side != "left" or right.side != "right"
                    or left.normalised_text != right.normalised_text
                    or exclusion.proof_kind not in {"same", "moved"}
                    or left.content_key in used_left or right.content_key in used_right):
                raise ValueError("exclusion_scope_invalid")
            used_left.add(left.content_key)
            used_right.add(right.content_key)
        for difference in raw.differences:
            left = by_key.get(difference.left_content_key) if difference.left_content_key else None
            right = by_key.get(difference.right_content_key) if difference.right_content_key else None
            if not (
                (difference.status == "changed" and left is not None and right is not None)
                or (difference.status == "removed" and left is not None and right is None)
                or (difference.status == "added" and left is None and right is not None)
            ) or (left is not None and (left.side != "left" or left.content_key in used_left)) or (
                right is not None and (right.side != "right" or right.content_key in used_right)
            ):
                raise ValueError("difference_scope_invalid")
            if left is not None and right is not None and left.normalised_text == right.normalised_text:
                raise ValueError("difference_exact_text_not_changed")
            if left is not None:
                used_left.add(left.content_key)
            if right is not None:
                used_right.add(right.content_key)
        for hint in hints:
            left, right = by_key.get(hint.source_content_key), by_key.get(hint.target_content_key)
            if left is None or right is None or left.side != "left" or right.side != "right":
                raise ValueError("hint_scope_invalid")
        return by_key

    @staticmethod
    def _require_revision(session: Session, pair_id: str, revision_id: str) -> None:
        # The migration's revision trigger takes this same lock. A map edit cannot
        # slip between the current-revision check and the batch commit.
        session.execute(text(
            "SELECT pg_advisory_xact_lock(hashtextextended('stage_link:' || :pair, 0))"
        ), {"pair": pair_id})
        state = session.execute(text(
            "SELECT state FROM stage_pair WHERE stage_pair_id = :pair"
        ), {"pair": pair_id}).scalar_one_or_none()
        if state != "confirmed":
            raise _conflict("stage_pair_not_confirmed")
        latest = session.execute(text(
            "SELECT stage_link_revision_id FROM stage_link_revision "
            "WHERE stage_pair_id = :pair ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": pair_id}).scalar_one_or_none()
        if latest != revision_id:
            raise _conflict("stage_link_revision_stale")

    @staticmethod
    def _require_profiles(
        session: Session, pair_id: str, fragments: Sequence[TextFragment],
        expected_keys: Mapping[str, frozenset[str]],
    ) -> None:
        from auditmanager.comparison.public import PAGE_PROFILE_ALGO_VERSION

        # The document FK locks taken by a concurrent version insert wait for
        # this publication transaction; validate latest only after locking.
        session.execute(text(
            "SELECT d.document_uid FROM document d WHERE d.document_uid IN "
            "(SELECT v.document_uid FROM document_version v JOIN comparison_page_profile pp "
            "ON pp.version_uid = v.version_uid WHERE pp.comparison_page_profile_id "
            "= ANY(CAST(:profiles AS text[]))) ORDER BY d.document_uid FOR UPDATE"
        ), {"profiles": list(expected_keys)}).all()
        sides: dict[str, str] = {}
        for fragment in fragments:
            previous = sides.setdefault(fragment.profile_id, fragment.side)
            if previous != fragment.side:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="PageProfile")
        for profile in expected_keys:
            row = session.execute(text(
                "SELECT pp.status, pp.algo_version, v.version_ordinal, "
                "(SELECT max(latest.version_ordinal) FROM document_version latest "
                "WHERE latest.document_uid = v.document_uid) AS latest_ordinal, "
                "am_stage_profile_in_pair(:pair, pp.comparison_page_profile_id, 'left') AS on_left, "
                "am_stage_profile_in_pair(:pair, pp.comparison_page_profile_id, 'right') AS on_right "
                "FROM comparison_page_profile pp JOIN document_version v ON v.version_uid = pp.version_uid "
                "WHERE pp.comparison_page_profile_id = :profile"
            ), {"pair": pair_id, "profile": profile}).first()
            side = sides.get(profile)
            if (row is None or row[0] != "ready" or row[1] != PAGE_PROFILE_ALGO_VERSION
                    or row[2] != row[3] or (side == "left" and not row[4])
                    or (side == "right" and not row[5])
                    or (side is None and not (row[4] or row[5]))):
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="PageProfile")

    @staticmethod
    def _existing_keys(session: Session, table: str, revision_id: str) -> set[str]:
        return set(session.execute(text(
            f"SELECT content_key FROM {table} WHERE stage_link_revision_id = :revision"
        ), {"revision": revision_id}).scalars())

    @staticmethod
    def _fragment_ids(
        session: Session, pair_id: str, fragments: Sequence[TextFragment],
    ) -> dict[str, str]:
        ids: dict[str, str] = {}
        for fragment in fragments:
            session.execute(text(
                "INSERT INTO stage_text_fragment "
                "(stage_text_fragment_id, stage_pair_id, page_profile_id, side, content_key, "
                "normalised_text, box_anchor) VALUES "
                "(:id, :pair, :profile, :side, :key, :text, CAST(:box AS jsonb)) "
                "ON CONFLICT (stage_pair_id, content_key) DO NOTHING"
            ), {
                "id": str(StageTextFragmentId.new()), "pair": pair_id,
                "profile": fragment.profile_id, "side": fragment.side,
                "key": fragment.content_key, "text": fragment.normalised_text,
                "box": json.dumps(fragment.box_anchor, sort_keys=True),
            })
            row = session.execute(text(
                "SELECT stage_text_fragment_id, page_profile_id, side, normalised_text, box_anchor "
                "FROM stage_text_fragment WHERE stage_pair_id = :pair AND content_key = :key"
            ), {"pair": pair_id, "key": fragment.content_key}).first()
            assert row is not None
            if (row[1] != fragment.profile_id or row[2] != fragment.side
                    or row[3] != fragment.normalised_text or row[4] != fragment.box_anchor):
                raise _conflict("stage_text_fragment_key_conflict")
            ids[fragment.content_key] = str(row[0])
        return ids

    def write(
        self, *, pair_id: str, revision_id: str,
        fragments: Sequence[TextFragment], expected_keys: Mapping[str, frozenset[str]],
        raw: RawTextPass, hints: Sequence[CrossSheetHint],
        work_item: WorkItem | None = None,
    ) -> EvidenceWrite:
        self._validate_batch(fragments, raw, hints, expected_keys)
        exclusion_rows = [
            (_digest("exclusion", revision_id, e.left_content_key, e.right_content_key, e.proof_kind), e)
            for e in raw.exact_exclusions
        ]
        difference_rows = [
            (_digest("difference", revision_id, d.status, d.left_content_key, d.right_content_key), d)
            for d in raw.differences
        ]
        hint_rows = [
            (_digest("hint", revision_id, h.source_content_key, h.target_content_key), h)
            for h in hints
        ]
        if (len({key for key, _ in exclusion_rows}) != len(exclusion_rows)
                or len({key for key, _ in difference_rows}) != len(difference_rows)
                or len({key for key, _ in hint_rows}) != len(hint_rows)):
            raise ValueError("stage_text_evidence_duplicate")
        desired = {
            "stage_text_exclusion": {key for key, _ in exclusion_rows},
            "stage_text_difference": {key for key, _ in difference_rows},
            "stage_text_hint": {key for key, _ in hint_rows},
        }
        with session_scope(self._sessions) as session:
            if work_item is not None:
                work_item.require_current(session)
            self._require_revision(session, pair_id, revision_id)
            self._require_profiles(session, pair_id, fragments, expected_keys)
            mapped = session.execute(text(
                "SELECT left_profile_id, right_profile_id FROM stage_link_item "
                "WHERE stage_link_revision_id = :revision"
            ), {"revision": revision_id}).all()
            if any(profile not in expected_keys for row in mapped for profile in row if profile is not None):
                raise _conflict("stage_text_map_profile_missing")
            paired = {(str(left), str(right)) for left, right in mapped
                      if left is not None and right is not None}
            paired_left = {left for left, _ in paired}
            paired_right = {right for _, right in paired}
            by_key = {fragment.content_key: fragment for fragment in fragments}
            for exclusion in raw.exact_exclusions:
                if (by_key[exclusion.left_content_key].profile_id,
                        by_key[exclusion.right_content_key].profile_id) not in paired:
                    raise _conflict("stage_text_unlinked_evidence")
            for difference in raw.differences:
                left = by_key.get(difference.left_content_key) if difference.left_content_key else None
                right = by_key.get(difference.right_content_key) if difference.right_content_key else None
                if ((left is not None and left.profile_id not in paired_left)
                        or (right is not None and right.profile_id not in paired_right)
                        or (left is not None and right is not None
                            and (left.profile_id, right.profile_id) not in paired)):
                    raise _conflict("stage_text_unlinked_evidence")
            for hint in hints:
                source = by_key[hint.source_content_key]
                target = by_key[hint.target_content_key]
                if (source.profile_id not in paired_left
                        or (source.profile_id, target.profile_id) in paired):
                    raise _conflict("stage_text_hint_not_cross_sheet")
            existing = {table: self._existing_keys(session, table, revision_id) for table in desired}
            replayed = any(existing.values())
            if replayed and existing != desired:
                raise _conflict("stage_text_revision_evidence_conflict")
            ids = self._fragment_ids(session, pair_id, fragments)
            for key, item in exclusion_rows:
                session.execute(text(
                    "INSERT INTO stage_text_exclusion "
                    "(stage_text_exclusion_id, stage_pair_id, stage_link_revision_id, "
                    "left_fragment_id, right_fragment_id, proof_kind, content_key) "
                    "VALUES (:id, :pair, :revision, :left, :right, :kind, :key) "
                    "ON CONFLICT (stage_pair_id, stage_link_revision_id, content_key) DO NOTHING"
                ), {"id": str(StageTextExclusionId.new()), "pair": pair_id,
                    "revision": revision_id, "left": ids[item.left_content_key],
                    "right": ids[item.right_content_key], "kind": item.proof_kind, "key": key})
            for key, item in difference_rows:
                session.execute(text(
                    "INSERT INTO stage_text_difference "
                    "(stage_text_difference_id, stage_pair_id, stage_link_revision_id, "
                    "left_fragment_id, right_fragment_id, status, content_key) "
                    "VALUES (:id, :pair, :revision, :left, :right, :status, :key) "
                    "ON CONFLICT (stage_pair_id, stage_link_revision_id, content_key) DO NOTHING"
                ), {"id": str(StageTextDifferenceId.new()), "pair": pair_id,
                    "revision": revision_id,
                    "left": ids[item.left_content_key] if item.left_content_key else None,
                    "right": ids[item.right_content_key] if item.right_content_key else None,
                    "status": item.status, "key": key})
            for key, item in hint_rows:
                session.execute(text(
                    "INSERT INTO stage_text_hint "
                    "(stage_text_hint_id, stage_pair_id, stage_link_revision_id, "
                    "source_fragment_id, target_fragment_id, content_key) "
                    "VALUES (:id, :pair, :revision, :source, :target, :key) "
                    "ON CONFLICT (stage_pair_id, stage_link_revision_id, content_key) DO NOTHING"
                ), {"id": str(StageTextHintId.new()), "pair": pair_id,
                    "revision": revision_id, "source": ids[item.source_content_key],
                    "target": ids[item.target_content_key], "key": key})
            return EvidenceWrite(len(fragments), len(exclusion_rows), len(difference_rows),
                                 len(hint_rows), replayed)
