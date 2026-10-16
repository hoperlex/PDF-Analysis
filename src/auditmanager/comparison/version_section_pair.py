"""Pure same-stage/section guard for ordinary W59 version comparison.

The caller must read both classifications from authoritative version-bound
state with the ordered pair in one consistent transaction. These supplied
values do not prove persistence, expert authorization or catalogue membership.
P-versus-R comparison belongs to a later, separate W62 workflow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts
from auditmanager.shared.identity import (
    DocumentUid,
    IdentityError,
    ProjectUid,
    VersionUid,
)


_SECTION_CODE = re.compile(r"[A-Z]{2,3}\Z")


class VersionSectionPairRefused(ValueError):
    """Supplied version classifications cannot enter ordinary comparison."""


@dataclass(frozen=True, slots=True)
class SuppliedVersionClassification:
    """One caller-loaded version's saved stage and confirmed section."""

    version_uid: str
    project_stage: str | None
    confirmed_section_code: str | None


@dataclass(frozen=True, slots=True)
class SameSectionVersionPair:
    """Exact supplied comparison coordinates after a compatibility check."""

    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    project_stage: Literal["P", "R"]
    confirmed_section_code: str


def _check_pair(pair: OrderedVersionPair) -> None:
    if (
        not isinstance(pair, OrderedVersionPair)
        or not isinstance(pair.source, VersionFacts)
        or not isinstance(pair.target, VersionFacts)
    ):
        raise VersionSectionPairRefused("version_pair_invalid")
    try:
        ProjectUid.parse(pair.project_uid)
        DocumentUid.parse(pair.document_uid)
        VersionUid.parse(pair.source.version_uid)
        VersionUid.parse(pair.target.version_uid)
    except (IdentityError, TypeError):
        raise VersionSectionPairRefused("version_pair_invalid") from None
    source, target = pair.source, pair.target
    if (
        source.version_uid == target.version_uid
        or source.project_uid != pair.project_uid
        or target.project_uid != pair.project_uid
        or source.document_uid != pair.document_uid
        or target.document_uid != pair.document_uid
        or type(source.version_ordinal) is not int
        or type(target.version_ordinal) is not int
        or source.version_ordinal < 1
        or source.version_ordinal >= target.version_ordinal
    ):
        raise VersionSectionPairRefused("version_pair_invalid")


def _check_classification(
    value: SuppliedVersionClassification,
    *,
    expected_uid: str,
    label: str,
) -> None:
    if not isinstance(value, SuppliedVersionClassification):
        raise VersionSectionPairRefused(f"{label}_classification_invalid")
    try:
        VersionUid.parse(value.version_uid)
    except (IdentityError, TypeError):
        raise VersionSectionPairRefused(f"{label}_version_invalid") from None
    if value.version_uid != expected_uid:
        raise VersionSectionPairRefused(f"{label}_version_mismatch")
    if type(value.project_stage) is not str or value.project_stage not in ("P", "R"):
        raise VersionSectionPairRefused(f"{label}_stage_unclassified")
    if (
        type(value.confirmed_section_code) is not str
        or _SECTION_CODE.fullmatch(value.confirmed_section_code) is None
    ):
        raise VersionSectionPairRefused(f"{label}_section_unconfirmed")


def prepare_same_section_version_pair(
    *,
    version_pair: OrderedVersionPair,
    source: SuppliedVersionClassification,
    target: SuppliedVersionClassification,
) -> SameSectionVersionPair:
    """Require explicit matching P/R stage and section on both exact versions.

    The future service must first prove each classification was persisted for
    the requested VersionUid by an expert and belongs to the sealed catalogue.
    This guard has no DB read, route or comparison approval authority.
    """
    _check_pair(version_pair)
    _check_classification(source, expected_uid=version_pair.source.version_uid, label="source")
    _check_classification(target, expected_uid=version_pair.target.version_uid, label="target")
    if source.project_stage != target.project_stage:
        raise VersionSectionPairRefused("project_stage_mismatch")
    if source.confirmed_section_code != target.confirmed_section_code:
        raise VersionSectionPairRefused("confirmed_section_mismatch")
    return SameSectionVersionPair(
        project_uid=version_pair.project_uid,
        document_uid=version_pair.document_uid,
        source_version_uid=version_pair.source.version_uid,
        target_version_uid=version_pair.target.version_uid,
        project_stage=cast(Literal["P", "R"], source.project_stage),
        confirmed_section_code=cast(str, source.confirmed_section_code),
    )


__all__ = [
    "SameSectionVersionPair",
    "SuppliedVersionClassification",
    "VersionSectionPairRefused",
    "prepare_same_section_version_pair",
]
