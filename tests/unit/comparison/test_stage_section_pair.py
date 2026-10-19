"""The W62 П/Р guard's code slice (`W59-VERSION-COMPARE-01`, ``mode=stage``)."""

from __future__ import annotations

import pytest

from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts
from auditmanager.comparison.version_section_pair import (
    SuppliedVersionClassification,
    VersionSectionPairRefused,
    prepare_stage_section_version_pair,
)

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"


def _pair() -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT, DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 1, 2, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 1, 2, "application/pdf"),
    )


def _stage(source=("P", "AR"), target=("R", "AR")):
    return prepare_stage_section_version_pair(
        version_pair=_pair(),
        source=SuppliedVersionClassification(SOURCE, *source),
        target=SuppliedVersionClassification(TARGET, *target),
    )


def test_p_source_and_r_target_of_one_section_are_admitted() -> None:
    staged = _stage()
    assert (staged.source_stage, staged.target_stage, staged.confirmed_section_code) == (
        "P", "R", "AR",
    )
    assert (staged.source_version_uid, staged.target_version_uid) == (SOURCE, TARGET)


@pytest.mark.parametrize(
    ("source", "target", "reason"),
    [
        (("P", "AR"), ("P", "AR"), "stage_pair_invalid"),
        (("R", "AR"), ("R", "AR"), "stage_pair_invalid"),
        (("R", "AR"), ("P", "AR"), "stage_pair_invalid"),
        (("P", "PS"), ("R", "PB"), "confirmed_section_mismatch"),
        ((None, None), ("R", "AR"), "source_stage_unclassified"),
        (("P", "AR"), ("R", None), "target_section_unconfirmed"),
    ],
)
def test_every_other_pair_is_refused_and_never_relabelled(source, target, reason) -> None:
    with pytest.raises(VersionSectionPairRefused, match=reason):
        _stage(source, target)
