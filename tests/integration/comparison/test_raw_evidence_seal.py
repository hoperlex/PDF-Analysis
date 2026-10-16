"""Exact integrity checks for one W59 approved version-comparison artifact."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.comparison.raw_evidence_seal import (
    RawEvidenceSealRefused,
    seal_raw_version_evidence,
)
from auditmanager.comparison.raw_text import ApprovedSheetPair, diff_approved_pairs
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"
CMP = "cmp_00000000000000000000000001"
LINK_A = "sln_00000000000000000000000001"
LINK_B = "sln_00000000000000000000000002"


def _version_pair() -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT,
        DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, 2, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 101, 2, "application/pdf"),
    )


def _diffs():
    pairs = (
        ApprovedSheetPair(CMP, LINK_B, 3, SOURCE, TARGET, 2, 1),
        ApprovedSheetPair(CMP, LINK_A, 3, SOURCE, TARGET, 1, 2),
    )
    return diff_approved_pairs(
        comparison_id=CMP,
        source_version_uid=SOURCE,
        target_version_uid=TARGET,
        link_revision=3,
        approved_pairs=pairs,
        source_pages={1: "Ось А\r\nСтена 200\n", 2: "Колонна 1\n"},
        target_pages={1: "Колонна 2\n", 2: "Ось А\r\nСтена 250\n"},
    )


def _seal(**changes):
    arguments = {
        "version_pair": _version_pair(),
        "comparison_id": CMP,
        "link_revision": 3,
        "raw_diffs": _diffs(),
    }
    arguments.update(changes)
    return seal_raw_version_evidence(**arguments)


def test_seal_is_canonical_and_binds_all_raw_pages_and_version_bytes() -> None:
    first = _seal()
    assert first == _seal(raw_diffs=tuple(reversed(_diffs())))
    assert first.sheet_evidence_sha256s == tuple(item.evidence_sha256 for item in _diffs())
    assert first.source_version_sha256 == "a" * 64
    assert first.target_version_sha256 == "b" * 64
    assert first.link_revision == 3
    assert len(first.seal_sha256) == 64
    with pytest.raises(FrozenInstanceError):
        first.seal_sha256 = "0" * 64  # type: ignore[misc]


def test_new_version_bytes_or_raw_text_produce_new_seal() -> None:
    original = _seal()
    pair = _version_pair()
    updated_target = replace(pair.target, sha256="c" * 64)
    assert _seal(version_pair=replace(pair, target=updated_target)).seal_sha256 != original.seal_sha256
    changed = diff_approved_pairs(
        comparison_id=CMP,
        source_version_uid=SOURCE,
        target_version_uid=TARGET,
        link_revision=3,
        approved_pairs=(ApprovedSheetPair(CMP, LINK_A, 3, SOURCE, TARGET, 1, 2),),
        source_pages={1: "Ось А\r\nСтена 200\n"},
        target_pages={2: "Ось А\r\nСтена 251\n"},
    )
    assert _seal(raw_diffs=changed).seal_sha256 != original.seal_sha256


def test_forged_digest_or_change_cannot_be_resealed() -> None:
    first, second = _diffs()
    with pytest.raises(RawEvidenceSealRefused, match="^raw_diff_not_canonical$"):
        _seal(raw_diffs=(replace(first, evidence_sha256="f" * 64), second))
    changed = replace(first.changes[-1], target_lines=("Недостоверный текст\n",))
    with pytest.raises(RawEvidenceSealRefused, match="^raw_diff_not_canonical$"):
        _seal(raw_diffs=(replace(first, changes=first.changes[:-1] + (changed,)), second))


@pytest.mark.parametrize("change, reason", [
    ({"comparison_id": "cmp_invalid"}, "comparison_id_invalid"),
    ({"link_revision": 4}, "raw_diff_binding_mismatch"),
    ({"raw_diffs": ()}, "raw_diffs_invalid"),
])
def test_explicit_comparison_and_revision_are_required(change, reason) -> None:
    with pytest.raises(RawEvidenceSealRefused, match=f"^{reason}$"):
        _seal(**change)


def test_cross_version_or_out_of_range_page_refuses() -> None:
    first, second = _diffs()
    with pytest.raises(RawEvidenceSealRefused, match="^raw_diff_binding_mismatch$"):
        _seal(raw_diffs=(replace(first, target_version_uid=SOURCE), second))
    with pytest.raises(RawEvidenceSealRefused, match="^raw_diff_page_out_of_range$"):
        _seal(raw_diffs=(replace(first, source_page_number=3), second))


def test_duplicate_page_refuses_even_if_raw_diffs_are_individually_canonical() -> None:
    first, second = _diffs()
    with pytest.raises(RawEvidenceSealRefused, match="^pair_not_one_to_one$"):
        _seal(raw_diffs=(first, replace(second, source_page_number=first.source_page_number)))


def test_empty_page_text_is_a_valid_exact_raw_diff() -> None:
    pair = ApprovedSheetPair(CMP, LINK_A, 3, SOURCE, TARGET, 1, 2)
    empty = diff_approved_pairs(
        comparison_id=CMP,
        source_version_uid=SOURCE,
        target_version_uid=TARGET,
        link_revision=3,
        approved_pairs=(pair,),
        source_pages={1: ""},
        target_pages={2: ""},
    )
    assert empty[0].changes == ()
    assert _seal(raw_diffs=empty).sheet_evidence_sha256s == (empty[0].evidence_sha256,)


def test_approved_page_500_can_be_sealed_but_501_cannot() -> None:
    pair = _version_pair()
    large_pair = replace(
        pair,
        source=replace(pair.source, page_count=500),
        target=replace(pair.target, page_count=500),
    )
    link = ApprovedSheetPair(CMP, LINK_A, 3, SOURCE, TARGET, 500, 500)
    raw = diff_approved_pairs(
        comparison_id=CMP,
        source_version_uid=SOURCE,
        target_version_uid=TARGET,
        link_revision=3,
        approved_pairs=(link,),
        source_pages={500: "Лист 500\n"},
        target_pages={500: "Лист 500, изменение\n"},
    )
    assert _seal(version_pair=large_pair, raw_diffs=raw).sheet_evidence_sha256s == (
        raw[0].evidence_sha256,
    )
    with pytest.raises(RawEvidenceSealRefused, match="^version_pair_invalid$"):
        _seal(version_pair=replace(large_pair, target=replace(large_pair.target, page_count=501)), raw_diffs=raw)
