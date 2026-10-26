"""``analysis.text.profile``: the immutable profile and prompt-bundle identity.

`PROD-11-AR-V1-V2-REMOVAL-01`: АР is no longer a profile of the product, so ``AR_TEXT_PROFILE`` and
``resolve_profile`` are gone from ``src`` and with them row PR-02 (the unknown-identity refusal)
and the two resolution tests (three tests, four cases, deleted). What stays pinned is the **retired
identity** ``ANALYSIS_PROFILE_ID`` that ``profile.py`` keeps, the prompt-bundle identity, and the
v1 machinery's reference profile of the tests (``tests/support/v1_reference_profile.py``), whose
version, discipline, stage and categories the machinery tests are written against.

`W10-ANL` mutation sweep, rows PR-01, PR-04, PR-05. Changing the pinned
`ANALYSIS_PROFILE_ID`, changing `PROFILE_VERSION` and changing `DISCIPLINE` were all green across
`tests/integration/analysis_engine`, `tests/integration/analysis_text` and `tests/replay`.

`tests/integration/analysis_text/test_profile_and_artifact.py` has a test named
`test_the_profile_is_resolved_by_a_pinned_identity`, and it does not pin the identity:

    resolved = resolve_profile(V1_REFERENCE_PROFILE.analysis_profile_id)
    assert resolved is V1_REFERENCE_PROFILE
    assert str(V1_REFERENCE_PROFILE.analysis_profile_id).startswith("ap_")

It feeds the module's own constant back into the module and asserts the result is the
module's own object, so both sides of the comparison move together under mutation; the
`startswith("ap_")` assertion holds for any ULID at all. That is the wave-9 failure mode,
already in the tree. This file pins the literal instead.

`ADR-0011` requires the profile identity to be **immutable**: the same identity resolving to
the same content in every process and on every run. There is no external registry to check it
against — `P02_SEAMS.md` §4.7's `pb_01M2545JSD15ETSNNV904X991R` is an illustrative example in
a document body, not this bundle — so the literal written here *is* the pin. That is the
point: if the value may never change, a test that spells it out is the authority, and a
change to it must be a deliberate edit to this file rather than a silent drift.
"""

from __future__ import annotations

import re
from pathlib import Path

from auditmanager.analysis.text.profile import ANALYSIS_PROFILE_ID as RETIRED_PROFILE_ID
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Pinned literals. Never imported from the module and fed back to it.
ANALYSIS_PROFILE_ID = "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
PROMPT_BUNDLE_ID = "pb_01M25P3TH0PDQYVKTRQFEM0CYS"
PROFILE_VERSION = "1.0.0"
DISCIPLINE = "AR"
STAGE_ID = "text_analysis"
CATEGORIES = ("internal_contradiction", "explicit_placeholder")


def test_the_profile_identity_is_the_pinned_literal() -> None:
    """PR-01. The identity is this string and no other, in ``src`` (retired) and in the reference."""
    assert str(V1_REFERENCE_PROFILE.analysis_profile_id) == ANALYSIS_PROFILE_ID
    assert str(RETIRED_PROFILE_ID) == ANALYSIS_PROFILE_ID


def test_the_prompt_bundle_identity_is_the_pinned_literal() -> None:
    assert str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id) == PROMPT_BUNDLE_ID


def test_the_profile_declares_the_pinned_version_discipline_and_stage() -> None:
    """PR-04 and PR-05."""
    assert V1_REFERENCE_PROFILE.profile_version == PROFILE_VERSION
    assert V1_REFERENCE_PROFILE.discipline == DISCIPLINE
    assert V1_REFERENCE_PROFILE.stage_id == STAGE_ID


def test_the_profile_declares_exactly_the_two_pinned_categories() -> None:
    assert tuple(V1_REFERENCE_PROFILE.categories) == CATEGORIES


def test_the_pinned_categories_are_the_migration_s_finding_categories() -> None:
    """The independent authority: `db/migrations` declares the same closed set.

    `20260910_0002_pc01_schema.py` sets `FINDING_CATEGORIES` and builds
    `ck_finding_category` from it. `db/` is not this module's tree, so a profile that
    drifts away from the persisted vocabulary reddens here rather than at an INSERT.
    """
    migration = (
        REPO_ROOT / "db" / "migrations" / "versions" / "20260910_0002_pc01_schema.py"
    ).read_text(encoding="utf-8")
    declared = re.search(r"^FINDING_CATEGORIES = \((.*?)\)$", migration, re.M)
    assert declared is not None, "the migration no longer declares FINDING_CATEGORIES"
    from_migration = tuple(
        part.strip().strip('"').strip("'")
        for part in declared.group(1).split(",")
        if part.strip()
    )
    assert from_migration == CATEGORIES
