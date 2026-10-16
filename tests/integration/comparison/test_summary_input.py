"""Complete, bounded AI-input projection of exact W59 raw differences."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.comparison.raw_evidence_seal import seal_raw_version_evidence
from auditmanager.comparison.raw_text import ApprovedSheetPair, diff_approved_pairs
from auditmanager.comparison.summary_input import (
    MAX_CHANGED_CHARACTERS,
    SummaryInputRefused,
    prepare_version_summary_input,
)
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"
CMP = "cmp_00000000000000000000000001"
LINK_A = "sln_00000000000000000000000001"
LINK_B = "sln_00000000000000000000000002"


def _pair() -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT,
        DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, 2, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 101, 2, "application/pdf"),
    )


def _diffs(*, source_pages=None, target_pages=None):
    return diff_approved_pairs(
        comparison_id=CMP,
        source_version_uid=SOURCE,
        target_version_uid=TARGET,
        link_revision=3,
        approved_pairs=(
            ApprovedSheetPair(CMP, LINK_B, 3, SOURCE, TARGET, 2, 1),
            ApprovedSheetPair(CMP, LINK_A, 3, SOURCE, TARGET, 1, 2),
        ),
        source_pages=source_pages or {1: "Общее\nСтена 200\n", 2: "Без изменений\n"},
        target_pages=target_pages or {1: "Без изменений\n", 2: "Общее\nСтена 250\n"},
    )


def _prepare(*, pair=None, diffs=None, seal=None):
    pair = pair if pair is not None else _pair()
    diffs = diffs if diffs is not None else _diffs()
    seal = seal if seal is not None else seal_raw_version_evidence(
        version_pair=pair, comparison_id=CMP, link_revision=3, raw_diffs=diffs,
    )
    return prepare_version_summary_input(version_pair=pair, raw_diffs=diffs, raw_seal=seal)


def test_changed_lines_only_but_every_approved_sheet_keeps_provenance() -> None:
    result = _prepare()
    assert result.comparison_id == CMP
    assert (result.source_version_uid, result.target_version_uid) == (SOURCE, TARGET)
    assert result.link_revision == 3
    assert len(result.sheets) == 2
    assert result.sheets[0].sheet_link_id == LINK_A
    assert [change.tag for change in result.sheets[0].changes] == ["replace"]
    assert result.sheets[0].changes[0].source_lines == ("Стена 200\n",)
    assert result.sheets[0].changes[0].target_lines == ("Стена 250\n",)
    assert result.sheets[1].sheet_link_id == LINK_B
    assert result.sheets[1].changes == ()
    assert tuple(sheet.raw_evidence_sha256 for sheet in result.sheets) == tuple(
        diff.evidence_sha256 for diff in _diffs()
    )
    assert len(result.input_sha256) == 64
    with pytest.raises(FrozenInstanceError):
        result.input_sha256 = "0" * 64  # type: ignore[misc]


def test_raw_input_order_does_not_change_projection_or_digest() -> None:
    diffs = _diffs()
    seal = seal_raw_version_evidence(
        version_pair=_pair(), comparison_id=CMP, link_revision=3, raw_diffs=diffs,
    )
    assert _prepare(diffs=diffs, seal=seal) == _prepare(
        diffs=tuple(reversed(diffs)), seal=seal,
    )


def test_any_new_version_bytes_or_approval_revision_needs_a_new_seal() -> None:
    original = _prepare()
    pair = _pair()
    revised = replace(pair, target=replace(pair.target, sha256="c" * 64))
    with pytest.raises(SummaryInputRefused, match="^raw_seal_mismatch$"):
        _prepare(pair=revised, seal=seal_raw_version_evidence(
            version_pair=pair, comparison_id=CMP, link_revision=3, raw_diffs=_diffs(),
        ))
    assert _prepare(pair=revised).input_sha256 != original.input_sha256


def test_forged_or_mixed_raw_evidence_refuses_before_projection() -> None:
    diffs = _diffs()
    seal = seal_raw_version_evidence(
        version_pair=_pair(), comparison_id=CMP, link_revision=3, raw_diffs=diffs,
    )
    with pytest.raises(SummaryInputRefused, match="^raw_seal_mismatch$"):
        _prepare(seal=replace(seal, seal_sha256="0" * 64))
    with pytest.raises(SummaryInputRefused, match="^raw_diff_binding_mismatch$"):
        _prepare(diffs=(replace(diffs[0], link_revision=4), diffs[1]), seal=seal)
    with pytest.raises(SummaryInputRefused, match="^raw_diff_not_canonical$"):
        _prepare(diffs=(replace(diffs[0], evidence_sha256="f" * 64), diffs[1]), seal=seal)
    with pytest.raises(SummaryInputRefused, match="^raw_seal_invalid$"):
        prepare_version_summary_input(version_pair=_pair(), raw_diffs=diffs, raw_seal=None)  # type: ignore[arg-type]


def test_oversized_changed_lines_refuse_without_truncation() -> None:
    source = "A" * (MAX_CHANGED_CHARACTERS // 2 + 1)
    target = "B" * (MAX_CHANGED_CHARACTERS // 2 + 1)
    diffs = _diffs(
        source_pages={1: source, 2: "same"},
        target_pages={1: "same", 2: target},
    )
    seal = seal_raw_version_evidence(
        version_pair=_pair(), comparison_id=CMP, link_revision=3, raw_diffs=diffs,
    )
    with pytest.raises(SummaryInputRefused, match="^changed_input_too_large$"):
        _prepare(diffs=diffs, seal=seal)
