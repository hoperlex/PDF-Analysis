"""The two opaque identities of the **retired** recorded AR v2 profile.

The recorded v2 package is gone (``PROD-11-AR-V1-V2-REMOVAL-01``, ``ADR-0024`` section 2) and nothing
resolves these values. They stay because ``ar_v3.v3_profile`` asserts that its own identities
differ from v1's and v2's: a persisted row may still carry a retired pair, and the v3 beta pair
must never be mistaken for one. The values are unchanged since the registration.
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
