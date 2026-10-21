"""A W59 version comparison needs two explicit, matching classifications."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts
from auditmanager.comparison.version_section_pair import (
    SameSectionVersionPair,
    SuppliedVersionClassification,
    VersionSectionPairRefused,
    prepare_same_section_version_pair,
)


PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
OTHER_DOCUMENT = "doc_01M2545JSD15ETSNNV904X991K"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"
OTHER_VERSION = "ver_01M2545JSD15ETSNNV904X991M"


def _pair() -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT,
        DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, 2, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 3, "b" * 64, 100, 2, "application/pdf"),
    )


def _classifications(
    stage: str = "P", section: str = "PS"
) -> tuple[SuppliedVersionClassification, SuppliedVersionClassification]:
    return (
        SuppliedVersionClassification(SOURCE, stage, section),
        SuppliedVersionClassification(TARGET, stage, section),
    )


def _prepare(
    *,
    pair: OrderedVersionPair | None = None,
    source: SuppliedVersionClassification | None = None,
    target: SuppliedVersionClassification | None = None,
) -> SameSectionVersionPair:
    default_source, default_target = _classifications()
    return prepare_same_section_version_pair(
        version_pair=_pair() if pair is None else pair,
        source=default_source if source is None else source,
        target=default_target if target is None else target,
    )


@pytest.mark.parametrize("stage,section", [("P", "PS"), ("R", "PB")])
def test_same_explicit_stage_and_section_return_exact_immutable_pair(
    stage: str, section: str
) -> None:
    source, target = _classifications(stage, section)
    expected = SameSectionVersionPair(PROJECT, DOCUMENT, SOURCE, TARGET, stage, section)
    result = _prepare(source=source, target=target)
    assert result == expected
    assert result == _prepare(source=source, target=target)
    with pytest.raises(FrozenInstanceError):
        result.confirmed_section_code = "AR"


def test_p_and_r_or_ps_and_pb_cannot_be_an_ordinary_version_pair() -> None:
    source, target = _classifications()
    with pytest.raises(VersionSectionPairRefused, match="^project_stage_mismatch$"):
        _prepare(source=source, target=replace(target, project_stage="R"))
    with pytest.raises(VersionSectionPairRefused, match="^confirmed_section_mismatch$"):
        _prepare(source=source, target=replace(target, confirmed_section_code="PB"))


@pytest.mark.parametrize("which", ["source", "target"])
def test_missing_or_foreign_version_classification_refuses(which: str) -> None:
    source, target = _classifications()
    values = {"source": source, "target": target}
    values[which] = replace(values[which], version_uid=OTHER_VERSION)
    with pytest.raises(VersionSectionPairRefused, match=f"^{which}_version_mismatch$"):
        _prepare(**values)
    values[which] = None
    with pytest.raises(VersionSectionPairRefused, match=f"^{which}_classification_invalid$"):
        prepare_same_section_version_pair(version_pair=_pair(), **values)


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"project_stage": None}, "source_stage_unclassified"),
        ({"project_stage": "PR"}, "source_stage_unclassified"),
        ({"confirmed_section_code": None}, "source_section_unconfirmed"),
        ({"confirmed_section_code": ""}, "source_section_unconfirmed"),
        ({"confirmed_section_code": "ps"}, "source_section_unconfirmed"),
        ({"version_uid": "source.pdf"}, "source_version_invalid"),
    ],
)
def test_unclassified_or_malformed_source_refuses(
    change: dict[str, object], reason: str
) -> None:
    source, target = _classifications()
    with pytest.raises(VersionSectionPairRefused, match=f"^{reason}$"):
        _prepare(source=replace(source, **change), target=target)


def test_pair_must_still_name_one_ordered_project_set() -> None:
    pair = _pair()
    with pytest.raises(VersionSectionPairRefused, match="^version_pair_invalid$"):
        _prepare(pair=replace(pair, target=replace(pair.target, version_ordinal=1)))
    with pytest.raises(VersionSectionPairRefused, match="^version_pair_invalid$"):
        _prepare(pair=replace(pair, target=replace(pair.target, document_uid=OTHER_DOCUMENT)))
    with pytest.raises(VersionSectionPairRefused, match="^version_pair_invalid$"):
        _prepare(pair=replace(pair, target=replace(pair.target, version_uid=SOURCE)))
