"""``analysis.text.profile``: the immutable profile and prompt-bundle identity.

`W10-ANL` mutation sweep, rows PR-01, PR-02, PR-04, PR-05. Changing the pinned
`ANALYSIS_PROFILE_ID`, changing `PROFILE_VERSION`, changing `DISCIPLINE` and disabling
`resolve_profile`'s unknown-identity refusal were all green across
`tests/integration/analysis_engine`, `tests/integration/analysis_text` and `tests/replay`.

`tests/integration/analysis_text/test_profile_and_artifact.py` has a test named
`test_the_profile_is_resolved_by_a_pinned_identity`, and it does not pin the identity:

    resolved = resolve_profile(AR_TEXT_PROFILE.analysis_profile_id)
    assert resolved is AR_TEXT_PROFILE
    assert str(AR_TEXT_PROFILE.analysis_profile_id).startswith("ap_")

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

import pytest

from auditmanager.analysis.text.profile import AR_TEXT_PROFILE, resolve_profile

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Pinned literals. Never imported from the module and fed back to it.
ANALYSIS_PROFILE_ID = "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
PROMPT_BUNDLE_ID = "pb_01M25P3TH0PDQYVKTRQFEM0CYS"
PROFILE_VERSION = "1.0.0"
DISCIPLINE = "AR"
STAGE_ID = "text_analysis"
CATEGORIES = ("internal_contradiction", "explicit_placeholder")


def test_the_profile_identity_is_the_pinned_literal() -> None:
    """PR-01. The identity is this string and no other."""
    assert str(AR_TEXT_PROFILE.analysis_profile_id) == ANALYSIS_PROFILE_ID


def test_the_prompt_bundle_identity_is_the_pinned_literal() -> None:
    assert str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id) == PROMPT_BUNDLE_ID


def test_the_profile_declares_the_pinned_version_discipline_and_stage() -> None:
    """PR-04 and PR-05."""
    assert AR_TEXT_PROFILE.profile_version == PROFILE_VERSION
    assert AR_TEXT_PROFILE.discipline == DISCIPLINE
    assert AR_TEXT_PROFILE.stage_id == STAGE_ID


def test_the_profile_declares_exactly_the_two_pinned_categories() -> None:
    assert tuple(AR_TEXT_PROFILE.categories) == CATEGORIES


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


def test_resolving_the_pinned_literal_returns_the_profile() -> None:
    """The literal is what resolves — not a value taken back out of the module."""
    assert resolve_profile(ANALYSIS_PROFILE_ID) is AR_TEXT_PROFILE


def test_the_default_resolution_is_the_pinned_literal() -> None:
    assert str(resolve_profile().analysis_profile_id) == ANALYSIS_PROFILE_ID


@pytest.mark.parametrize(
    "unknown",
    [
        "ap_01M25P3TH08VVTTGJRXYBZZ7RQ",  # one character off the pinned identity
        "ap_00000000000000000000000000",
        "",
        "not-an-identity",
    ],
)
def test_an_unregistered_profile_identity_is_refused(unknown: str) -> None:
    """PR-02. `resolve_profile` refuses rather than returning the one profile anyway."""
    with pytest.raises(KeyError, match="no analysis profile is registered"):
        resolve_profile(unknown)
