"""The fixed AR analysis profile.

``ADR-0011`` requires an immutable analysis profile and prompt bundle, content-hashed
and resolved by identity at run time. PC-01 has exactly one profile: the AR text-only
internal-consistency check. There is no profile registry to configure, no per-project
override and no second discipline - a second profile is a scope change, visible as a
new constant here rather than as a row somebody inserted.

The identity is a pinned literal, not ``AnalysisProfileId.new()``. Immutable means the
same identity resolves to the same content on every run and in every process; a fresh
ULID per run would make the artifact unreproducible and would make "resolved by
identity" mean nothing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.analysis.text.prompt import (
    AR_TEXT_PROMPT_BUNDLE,
    CATEGORIES,
    PromptBundle,
    canonical_json,
)
from auditmanager.shared.identity import AnalysisProfileId

ANALYSIS_PROFILE_ID: Final[AnalysisProfileId] = AnalysisProfileId.parse(
    "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
)

PROFILE_VERSION: Final[str] = "1.0.0"
DISCIPLINE: Final[str] = "AR"


@dataclass(frozen=True, slots=True)
class AnalysisProfile:
    """One immutable analysis profile bound to one immutable prompt bundle."""

    analysis_profile_id: AnalysisProfileId
    profile_version: str
    stage_id: str
    discipline: str
    categories: tuple[str, ...]
    prompt_bundle: PromptBundle

    @property
    def content_sha256(self) -> str:
        """Hash of the profile including the bundle it binds.

        A prompt edit therefore changes the profile hash too, so the two cannot drift
        apart in a run record that quotes only one of them.
        """
        return hashlib.sha256(
            canonical_json(
                {
                    "analysis_profile_id": str(self.analysis_profile_id),
                    "profile_version": self.profile_version,
                    "stage_id": self.stage_id,
                    "discipline": self.discipline,
                    "categories": list(self.categories),
                    "prompt_bundle_id": str(self.prompt_bundle.prompt_bundle_id),
                    "prompt_bundle_sha256": self.prompt_bundle.content_sha256,
                }
            ).encode("utf-8")
        ).hexdigest()


AR_TEXT_PROFILE: Final[AnalysisProfile] = AnalysisProfile(
    analysis_profile_id=ANALYSIS_PROFILE_ID,
    profile_version=PROFILE_VERSION,
    stage_id=STAGE_ID,
    discipline=DISCIPLINE,
    categories=CATEGORIES,
    prompt_bundle=AR_TEXT_PROMPT_BUNDLE,
)


def resolve_profile(analysis_profile_id: AnalysisProfileId | str = ANALYSIS_PROFILE_ID) -> AnalysisProfile:
    """Resolve a profile by identity. PC-01 declares exactly one."""
    if str(analysis_profile_id) != str(ANALYSIS_PROFILE_ID):
        raise KeyError("no analysis profile is registered under that identity")
    return AR_TEXT_PROFILE
