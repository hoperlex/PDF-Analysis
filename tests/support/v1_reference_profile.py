"""The v1 machinery's reference text profile (`PROD-11-AR-V1-V2-REMOVAL-01`).

АР is no longer a text profile of the product (`ADR-0024` section 2, `AD-12`): ``AR_TEXT_PROFILE``,
its registry entry and every default to it are gone from ``src``. The v1 *machinery* stays
(``analysis/text/prompt.py``, ``stage.py``, ``budget.py``, ``proxy.py`` and the nine stage ids,
which the other 14 sections run on), and about fifty of its tests used the АР profile only as a
vehicle for retries, durable effects, cost, exports and recovery, with their assertions pinned to
that profile's prompt, request checksum and recording.

This module is that vehicle, in the tests and nowhere else: the same objects the removed constant
was made of (the v1 prompt bundle and category list that ``prompt.py`` keeps, the retired identity
that ``profile.py`` keeps), so ``content_sha256``, the request body and the checksum that keys
``fixtures/recorded/text_analysis`` are byte for byte what they were, and no assertion changed.
``tests/unit/analysis/test_text_profile_registry.py`` holds that the registry does not hold it.

Import it as ``from tests.support.v1_reference_profile import ...`` (the idiom of
``tests.support.expected_facts``).
"""

from __future__ import annotations

from typing import Final

from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.analysis.text.profile import ANALYSIS_PROFILE_ID, AnalysisProfile
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE, CATEGORIES

#: What ``content_sha256`` of the removed ``AR_TEXT_PROFILE`` was, measured at the base of the
#: removal (``1c8d29fa``). A change to the prompt bundle, the categories or the identity moves it.
EXPECTED_CONTENT_SHA256: Final[str] = "30053740f569ec84683f65dbd04ef7b0b1fd0a8b24ecdfb287e76533158d0553"

V1_REFERENCE_PROFILE: Final[AnalysisProfile] = AnalysisProfile(
    analysis_profile_id=ANALYSIS_PROFILE_ID,
    profile_version="1.0.0",
    stage_id=STAGE_ID,
    discipline="AR",
    categories=CATEGORIES,
    prompt_bundle=AR_TEXT_PROMPT_BUNDLE,
)


def resolve_reference_profile(analysis_profile_id: str, prompt_bundle_id: str) -> AnalysisProfile:
    """``TextProfileResolver`` for the reference profile: the exact pair, or ``LookupError``.

    The shape the executor's ``text_profiles`` parameter takes (the registry's ``resolve``). It
    never substitutes: any other pair is unregistered, as it is in the product.
    """
    if (
        str(analysis_profile_id) != str(V1_REFERENCE_PROFILE.analysis_profile_id)
        or str(prompt_bundle_id) != str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id)
    ):
        raise LookupError("no reference profile carries that identity pair")
    return V1_REFERENCE_PROFILE


__all__ = [
    "EXPECTED_CONTENT_SHA256",
    "V1_REFERENCE_PROFILE",
    "resolve_reference_profile",
]
