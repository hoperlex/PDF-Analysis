"""The shape of a text-analysis profile, and the retired АР v1 identity.

``ADR-0011`` requires an immutable analysis profile and prompt bundle, content-hashed
and resolved by identity at run time. :class:`AnalysisProfile` is that shape; the profiles the
product registers are the data packages of the other 14 sections
(:mod:`auditmanager.analysis.text.profile_registry`).

**АР is not a profile.** The АР text profile of PC-01 (``AR_TEXT_PROFILE``) was registered from
this module's constants until ``PROD-11-AR-V1-V2-REMOVAL-01`` (``ADR-0024`` section 2, ``AD-12``):
the АР analysis path of production is the six-Run v3 group only. :data:`ANALYSIS_PROFILE_ID` stays
as the **retired identity** of that profile: persisted runs pin it, and the AR v3 beta profile
asserts that its own identity never equals it (``ar_v3.v3_profile``). Nothing resolves it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.text.prompt import PromptBundle, canonical_json
from auditmanager.shared.identity import AnalysisProfileId

#: The retired identity of the АР v1 text profile. Pinned, never generated: a fresh ULID per run
#: would make "resolved by identity" mean nothing. No registry entry carries it.
ANALYSIS_PROFILE_ID: Final[AnalysisProfileId] = AnalysisProfileId.parse(
    "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
)


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
