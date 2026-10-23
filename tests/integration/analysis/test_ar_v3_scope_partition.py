"""Unserved AR partition invariants and optional repaired-bundle acceptance."""

from __future__ import annotations

import json
import os
from array import array
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.analysis.profiles.ar_v3.scope_partition import (
    PROMPT_CHAR_CAP,
    ScopePartitionRefused,
    plan_scope_partition,
    validate_rendered_scope,
)
from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.ranking import (
    PROMPT_CHAR_CAP as W57_PROMPT_CHAR_CAP,
    RankingRefused,
    RetrievalItem,
    RetrievalParagraph,
    TargetSpan,
    select_prompt_part,
)
from auditmanager.norms.search.display import reader_designation


IDS = tuple(f"C{i:02d}" for i in range(1, 23))
EXPECTED_GROUPS = {
    "F1": IDS[0:3], "F2": IDS[3:10], "A1": IDS[10:14],
    "A2": IDS[14:20], "S1": IDS[20:21], "S2": IDS[21:22],
}


def _dummy_items() -> tuple[SimpleNamespace, ...]:
    return tuple(SimpleNamespace(item_id=item_id) for item_id in IDS)


def test_partition_totality_order_and_stable_digest() -> None:
    first = plan_scope_partition(_dummy_items())
    replay = plan_scope_partition(tuple(reversed(_dummy_items())))
    assert PROMPT_CHAR_CAP == W57_PROMPT_CHAR_CAP == 22_000
    assert tuple(group.scope_id for group in first.groups) == tuple(EXPECTED_GROUPS)
    assert {group.scope_id: group.item_ids for group in first.groups} == EXPECTED_GROUPS
    assert tuple(item_id for group in first.groups for item_id in group.item_ids) == IDS
    assert len(set(item_id for group in first.groups for item_id in group.item_ids)) == 22
    assert first == replay
    assert first.composition_sha256 == "79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781"


def test_partition_refuses_unknown_missing_duplicate_and_over_cap() -> None:
    with pytest.raises(ScopePartitionRefused, match="unknown candidate item"):
        plan_scope_partition(_dummy_items() + (SimpleNamespace(item_id="C23"),))
    with pytest.raises(ScopePartitionRefused, match="missing candidate item"):
        plan_scope_partition(_dummy_items()[:-1])
    with pytest.raises(ScopePartitionRefused, match="duplicate candidate item"):
        plan_scope_partition(_dummy_items() + _dummy_items()[:1])
    plan = plan_scope_partition(_dummy_items())
    with pytest.raises(ScopePartitionRefused, match="unknown scope id"):
        validate_rendered_scope(plan, "ALL", "x")
    with pytest.raises(ScopePartitionRefused, match="composition invalid"):
        validate_rendered_scope(replace(plan, groups=plan.groups[1:]), "F1", "x")
    with pytest.raises(ScopePartitionRefused, match="character cap"):
        validate_rendered_scope(plan, "F1", "x" * (PROMPT_CHAR_CAP + 1))
    with pytest.raises(ScopePartitionRefused, match="empty"):
        validate_rendered_scope(plan, "F1", "")
    assert validate_rendered_scope(plan, "F1", "x" * PROMPT_CHAR_CAP).prompt_part_characters == PROMPT_CHAR_CAP


def test_actual_w57_rendered_part_over_cap_is_refused() -> None:
    vector = array("f", [1.0] + [0.0] * (DIMENSIONS - 1))
    items = tuple(
        RetrievalItem(item_id, vector, (TargetSpan("ndoc_1", 0, 0),))
        for item_id in IDS
    )
    paragraph = RetrievalParagraph(
        "ndoc_1", "npar_1", "СП 1", "Проверка", 0, "1", "1", "а" * 10_000,
    )
    plan = plan_scope_partition(items)
    oversized = select_prompt_part(plan.group("F1").items, (paragraph,), (), char_cap=100_000)
    assert len(oversized.prompt_part) > PROMPT_CHAR_CAP
    with pytest.raises(ScopePartitionRefused, match="character cap"):
        validate_rendered_scope(plan, "F1", oversized.prompt_part)
    with pytest.raises(RankingRefused, match="target rows alone"):
        select_prompt_part(plan.group("F1").items, (paragraph,), ())


# Candidate evidence from AR-MAP-BUDGET-01 §2. These spans are not an approved map.
D = {
    "D1": "ndoc_01M59N9JD4VPS1C8ACDFC01BGG",
    "D2": "ndoc_01M59N9WF2B93HJQ3GYNR5FCWS",
    "D3": "ndoc_01M59N9WJPYS8FAQED34RPJF14",
    "D4": "ndoc_01M59N9VSS64AB4R6N6XX3Q74G",
    "D5": "ndoc_01M59N9W1JY06JA08QK08DE2HT",
    "D6": "ndoc_01M59N9Z9MD1RNV7QJDBFNC87X",
}
SPANS = {
    "S01": ("D1", 132, 137), "S02": ("D1", 357, 370),
    "S03": ("D1", 139, 140), "S04": ("D1", 129, 131),
    "S05": ("D1", 168, 169), "S06": ("D1", 213, 214),
    "S07": ("D1", 392, 393), "S08": ("D1", 240, 248),
    "S09": ("D1", 299, 303), "S09a": ("D1", 299, 300),
    "S12": ("D1", 206, 207), "S13": ("D2", 359, 359),
    "S14": ("D1", 388, 391), "S15": ("D1", 100, 100),
    "S16": ("D6", 932, 932), "S17": ("D2", 343, 345),
    "S18": ("D2", 348, 348), "S19": ("D6", 356, 356),
    "A11": ("D3", 301, 304), "A12": ("D3", 365, 373),
    "A14": ("D3", 377, 380), "A15": ("D3", 390, 391),
    "A16": ("D3", 296, 300), "A17": ("D3", 345, 346),
    "A18": ("D3", 447, 452), "A19": ("D4", 138, 142),
    "T2": ("D5", 289, 300), "T1note": ("D5", 238, 238),
    "T3": ("D5", 301, 308),
}


def _spans(*names: str) -> tuple[TargetSpan, ...]:
    return tuple(TargetSpan(D[SPANS[name][0]], SPANS[name][1], SPANS[name][2]) for name in names)


def _candidate_items(branch: str, *, sound: str = "broad", mixed: bool = False) -> tuple[RetrievalItem, ...]:
    targets: dict[str, tuple[TargetSpan, ...]] = {}
    if branch in {"N", "R"}:
        targets.update(C01=_spans("S01", "S02"), C03=_spans("S06", "S07"))
        targets["C05"] = _spans("S09a" if branch == "N" else "S09")
        targets["C06"] = _spans("S12", "S13", "S14")
        targets["C09"] = _spans("S17")
    else:
        targets["C01"] = _spans("S01", "S03") + (_spans("S04") if mixed else ())
        targets.update(C03=_spans("S06"), C05=_spans("S09"), C06=_spans("S12"), C09=_spans("S18"))
    targets.update(
        C02=_spans("S05"), C04=_spans("S08"), C07=_spans("S15"),
        C08=_spans("S16"), C10=_spans("S19"), C11=_spans("A11"),
        C12=_spans("A12"), C13=_spans("A12"), C14=_spans("A14"),
        C15=_spans("A15"), C16=_spans("A16"), C17=_spans("A17"),
        C18=_spans("A18"), C19=_spans("A19"), C20=_spans("A19"),
        C21=_spans("T2"),
    )
    targets["C22"] = {
        "broad": _spans("T2"),
        "shop_top_down": _spans("T2", "T1note"),
        "bottom_up": _spans("T3"),
    }[sound]
    vector = array("f", [1.0] + [0.0] * (DIMENSIONS - 1))
    return tuple(RetrievalItem(item_id, vector, targets[item_id]) for item_id in IDS)


@pytest.fixture(scope="module")
def repaired_paragraphs() -> tuple[RetrievalParagraph, ...]:
    path = os.environ.get("AR_SCOPE_BUNDLE_ROWS")
    if path is None:
        pytest.skip("AR_SCOPE_BUNDLE_ROWS is required for real candidate acceptance")
    rows = Path(path)
    documents = {}
    for line in (rows / "documents.jsonl").open(encoding="utf-8"):
        record = json.loads(line)
        if record["norm_document_id"] in D.values():
            documents[record["norm_document_id"]] = record
    assert set(documents) == set(D.values())
    selected = []
    for line in (rows / "paragraphs.jsonl").open(encoding="utf-8"):
        record = json.loads(line)
        if record["norm_document_id"] in documents:
            selected.append(record)
    assert len(selected) == 5_833
    assert all(row["text_reliability"] == "reliable" for row in selected if any(
        row["norm_document_id"] == D[alias] and first <= row["ordinal"] <= last
        for alias, first, last in SPANS.values()
    ))
    return tuple(
        RetrievalParagraph(
            row["norm_document_id"], row["norm_paragraph_id"],
            reader_designation(documents[row["norm_document_id"]]["slug"]),
            documents[row["norm_document_id"]]["title"], row["ordinal"],
            row["clause_number"], str(row["page_label"]), row["text"],
            row["text_reliability"] == "reliable",
        )
        for row in selected
    )


@pytest.mark.parametrize(
    ("branch", "sound", "mixed", "expected"),
    [
        ("N", "broad", False, (14783, 14479, 15032, 14143, 14078, 14078)),
        ("R", "broad", False, (14783, 15907, 15032, 14143, 14078, 14078)),
        ("P", "broad", False, (7560, 11459, 15032, 14143, 14078, 14078)),
        ("P", "shop_top_down", False, (7560, 11459, 15032, 14143, 14078, 17607)),
        ("P", "bottom_up", False, (7560, 11459, 15032, 14143, 14078, 5789)),
        ("P", "shop_top_down", True, (9752, 11459, 15032, 14143, 14078, 17607)),
    ],
)
def test_real_candidate_groups_pass_and_all22_refuses(
    repaired_paragraphs: tuple[RetrievalParagraph, ...],
    branch: str, sound: str, mixed: bool, expected: tuple[int, ...],
) -> None:
    items = _candidate_items(branch, sound=sound, mixed=mixed)
    plan = plan_scope_partition(items)
    lengths = []
    for group in plan.groups:
        selection = select_prompt_part(group.items, repaired_paragraphs, ())
        verified = validate_rendered_scope(plan, group.scope_id, selection.prompt_part)
        assert tuple(dict.fromkeys(row.item_id for row in selection.rows)) == group.item_ids
        assert verified.item_ids == group.item_ids
        assert verified.composition_sha256 == plan.composition_sha256
        lengths.append(verified.prompt_part_characters)
    assert tuple(lengths) == expected
    with pytest.raises(RankingRefused, match="target rows alone"):
        select_prompt_part(items, repaired_paragraphs, ())
