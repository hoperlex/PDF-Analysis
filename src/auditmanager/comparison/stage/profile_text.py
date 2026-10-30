"""Stored page words for stage search; a read never extracts the source PDF."""

from __future__ import annotations

import unicodedata
from typing import Any

from auditmanager.shared.errors import DomainError, ErrorCode


class StageProfileTextService:
    def __init__(self, profiles: Any) -> None:
        self.profiles = profiles

    def get(self, *, profile_id: str, query: str | None = None) -> dict[str, Any]:
        profile = self.profiles.read_page_profile(profile_id)
        if not profile.row.is_ready or profile.row.profile_blob_id is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_profile_text")
        if len(profile.words) > 50_000:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="profile_id",
                              constraint="stage_profile_text_budget")
        needle = unicodedata.normalize("NFKC", query or "").casefold().strip()
        words = [word for word in profile.words if not needle or
                 needle in unicodedata.normalize("NFKC", word.text).casefold()]
        return {"profile_id": profile.row.page_profile_id,
                "version_uid": profile.row.version_uid, "page_number": profile.row.page_number,
                "scan": profile.scan, "has_text_layer": profile.has_text_layer,
                "width_pt": profile.width_pt, "height_pt": profile.height_pt,
                "words": [{"text": word.text, "x0": word.x0, "top": word.top,
                           "x1": word.x1, "bottom": word.bottom} for word in words]}
