"""The two opaque identities of the recorded AR v2 profile.

``ar_v3.v3_profile`` asserts that its own identities differ from v1's and v2's, so it needs
these two values without importing the recorded v2 registration (which also holds
``resolve_recorded_profile`` and imports the v2 prompt material and response schema).
``ar_v2.registered`` reads them from here; the values are unchanged since the
registration (``PROD-10``, ``ADR-0024`` section 2).
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId

PROFILE_ID: Final[AnalysisProfileId] = AnalysisProfileId.parse(
    "ap_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
)
PROMPT_BUNDLE_ID: Final[PromptBundleId] = PromptBundleId.parse(
    "pb_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
)
