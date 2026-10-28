"""The effective matrix on a hand-made build: layers, edits, undo, orphans, determinism (`CMP-MATRIX-01`).

ADR-0025 decision 3: algorithm, then accepted AI links, then manual edits, and manual wins; decision 14: an AI link
applies only while its cell is in the state it answered, an edit that no longer applies is orphaned, never silent."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from auditmanager.comparison.matrix.effective import canonical_json, effective_matrix, latest_applied_edit, page_index
from auditmanager.comparison.matrix.model import AiLinkRecord, BuildRecord, EditRecord, PageRef
from auditmanager.comparison.matrix.pairs import adjacent_pairs

A, B, C = "ver_A", "ver_B", "ver_C"
T0 = datetime(2026, 10, 28, tzinfo=timezone.utc)


def m(version: str, number: int, confidence: str | None = None, flags: tuple[str, ...] = (), **extra):
    cell = {"version_uid": version, "state": "matched", "page_number": number, "page_profile_id": f"cpr_{version[-1]}{number}",
            "flags": list(flags), "title": f"Лист {number}", "sheet_number": str(number)}
    if confidence:
        cell["confidence"] = confidence
        cell["score"] = 0.9
    cell.update(extra)
    return cell


def hole(version: str, state: str = "absent", candidates: list[tuple[int, str]] | None = None, ref: str = B, reason: str = "no_candidates"):
    if state == "absent":
        return {"version_uid": version, "state": "absent", "reason": reason}
    return {"version_uid": version, "state": "unmatched", "reason": "candidates_left", "ref_version_uid": ref,
            "candidates": [{"page_number": n, "page_profile_id": f"cpr_{version[-1]}{n}", "score": 0.4} for n, _ in candidates or []]}


def build(matrix_id: str = "cmx_ONE") -> BuildRecord:
    rows = [
        {"anchor": {}, "cells": [m(A, 1), m(B, 1, "high"), m(C, 1, "high")]},
        {"anchor": {}, "cells": [m(A, 2), m(B, 2, "medium"), hole(C, "unmatched", [(5, "x")])]},
        {"anchor": {}, "cells": [hole(A), m(B, 3), hole(C)]},
        {"anchor": {}, "cells": [hole(A), hole(B), m(C, 5)]},
        {"anchor": {}, "cells": [m(A, 4, flags=("scan",)), m(B, 4, "high", flags=("duplicate", "scan"), dups=[{"page_number": 6, "page_profile_id": "cpr_B6"}]), m(C, 4, "high")]},
    ]
    summary = {"order": [A, B, C], "page_counts": {A: 4, B: 6, C: 5}, "splits": []}
    return BuildRecord(matrix_id, 1, None, "a" * 64, "v1.2", "cmp-matrix/1", rows, [], summary, T0)


def edit(no: int, kind: str, page: PageRef | None, other: PageRef | None = None, absent: str | None = None, undoes: str | None = None):
    return EditRecord(f"cme_{no}", no, kind, "expert", page, other, absent, undoes, None, "usr_x", T0 + timedelta(minutes=no))


def ref(version: str, number: int) -> PageRef:
    return PageRef(version, number)


def ai(no: int, a: PageRef, b: PageRef, state: str, matrix_id: str = "cmx_ONE") -> AiLinkRecord:
    return AiLinkRecord(f"cak_{no}", "doc_X", matrix_id, a, b, state, T0 + timedelta(seconds=no))


def view(eff, version_index: int):
    return [r["cells"][version_index] for r in eff.rows]


def pages_of(eff, version_index: int):
    return [c["page"]["page_number"] if c["state"] == "matched" else c["state"] for c in view(eff, version_index)]


def test_without_a_layer_the_effective_matrix_is_the_algorithm() -> None:
    eff = effective_matrix(build(), [], [], page_counts={A: 4, B: 6, C: 5})
    assert eff.counts == {"rows": 5, "unmatched": 1, "manual": 0, "ai": 0, "groups": 0, "duplicates": 1}
    assert [r["row_id"] for r in eff.rows] == ["cpr_A1", "cpr_A2", "cpr_B3", "cpr_C5", "cpr_A4"]
    assert pages_of(eff, 2) == [1, "unmatched", "absent", 5, 4]
    row = eff.rows[1]["cells"][2]
    assert [c["page"]["page_number"] for c in row["candidates"]] == [5] and row["reason"] == "candidates_left"
    assert eff.rows[4]["cells"][1]["flags"] == ["duplicate", "scan"]
    assert eff.columns == [{"version_uid": v, "page_count": n} for v, n in ((A, 4), (B, 6), (C, 5))]
    assert eff.orphaned_edit_ids == [] and eff.rows[0]["title"] == "Лист 1" and eff.rows[0]["sheet_number"] == "1"


def test_a_link_moves_the_page_into_the_row_and_the_page_is_no_longer_a_candidate() -> None:
    eff = effective_matrix(build(), [edit(1, "link", ref(B, 2), ref(C, 5))], [])
    cell = eff.rows[1]["cells"][2]
    assert (cell["state"], cell["confidence"], cell["edit_id"], cell["page"]["page_number"]) == ("matched", "manual", "cme_1", 5)
    assert [r["row_id"] for r in eff.rows] == ["cpr_A1", "cpr_A2", "cpr_B3", "cpr_A4"], "the row C5 stood in alone is gone"
    assert eff.counts["manual"] == 1 and eff.counts["unmatched"] == 0 and eff.edit_status == {"cme_1": "applied"}


def test_a_link_over_a_cell_that_holds_another_page_displaces_it_to_a_row_of_its_own() -> None:
    eff = effective_matrix(build(), [edit(1, "link", ref(A, 1), ref(C, 5))], [])
    assert eff.rows[0]["cells"][2]["page"]["page_number"] == 5 and eff.rows[0]["cells"][2]["confidence"] == "manual"
    displaced = eff.rows[1]["cells"][2]
    assert displaced["page"]["page_number"] == 1 and displaced["confidence"] == "manual", "shown as touched by an expert, as in the original"
    assert eff.rows[1]["cells"][0]["state"] == "absent" and eff.rows[1]["cells"][1]["state"] == "absent"
    assert eff.rows[2]["row_id"] == "cpr_A2", "the old row stays; only its cell moved"


def test_linking_a_page_that_is_already_in_the_row_confirms_it_as_manual() -> None:
    eff = effective_matrix(build(), [edit(1, "link", ref(A, 1), ref(B, 1))], [])
    assert eff.rows[0]["cells"][1]["confidence"] == "manual" and len(eff.rows) == 5


def test_unlink_gives_the_page_a_row_of_its_own_after_the_old_one_and_leaves_a_hole() -> None:
    eff = effective_matrix(build(), [edit(1, "unlink", ref(B, 1))], [])
    assert [r["row_id"] for r in eff.rows][:3] == ["cpr_A1", "cpr_B1", "cpr_A2"]
    assert eff.rows[0]["cells"][1]["state"] == "unmatched" and eff.rows[0]["cells"][1]["reason"] == "edited"
    own = eff.rows[1]["cells"]
    assert own[1]["confidence"] == "manual" and [c["state"] for c in own] == ["absent", "matched", "absent"]


def test_unlink_of_a_duplicate_copy_takes_only_the_copy() -> None:
    eff = effective_matrix(build(), [edit(1, "unlink", ref(B, 6))], [])
    primary = next(r["cells"][1] for r in eff.rows if r["cells"][1]["state"] == "matched" and r["cells"][1]["page"]["page_number"] == 4)
    assert "duplicate" not in primary["flags"]
    copy = next(r["cells"][1] for r in eff.rows if r["cells"][1]["state"] == "matched" and r["cells"][1]["page"]["page_number"] == 6)
    assert copy["confidence"] == "manual" and eff.counts["duplicates"] == 0


def test_mark_absent_reads_as_the_experts_word_and_a_page_that_stood_there_gets_a_row() -> None:
    eff = effective_matrix(build(), [edit(1, "mark_absent", ref(A, 1), absent=B)], [])
    cell = eff.rows[0]["cells"][1]
    assert (cell["state"], cell["reason"], cell["edit_id"]) == ("absent", "marked_absent", "cme_1")
    assert eff.rows[1]["cells"][1]["page"]["page_number"] == 1 and eff.rows[1]["cells"][1]["confidence"] == "manual"


def test_an_undone_edit_and_the_undo_event_shape_nothing() -> None:
    edits = [edit(1, "unlink", ref(B, 1)), edit(2, "mark_absent", ref(A, 1), absent=B), edit(3, "undo", None, undoes="cme_2")]
    eff = effective_matrix(build(), edits, [])
    assert eff.edit_status == {"cme_1": "applied", "cme_2": "undone", "cme_3": "applied"}
    assert eff.rows[0]["cells"][1]["reason"] == "edited", "only the unlink shaped it"
    assert latest_applied_edit(edits).edit_id == "cme_1"
    assert latest_applied_edit([edit(1, "unlink", ref(B, 1)), edit(2, "undo", None, undoes="cme_1")]) is None
    assert latest_applied_edit([]) is None
    two = [edit(1, "unlink", ref(B, 1)), edit(2, "mark_absent", ref(A, 1), absent=B)]
    assert latest_applied_edit(two).edit_id == "cme_2", "the newest applied edit, not the oldest"
    assert latest_applied_edit([*two, edit(3, "undo", None, undoes="cme_2")]).edit_id == "cme_1", "then the one before it"


def test_an_edit_whose_cells_do_not_exist_is_orphaned_and_the_rest_still_apply() -> None:
    foreign = "ver_Z"
    edits = [edit(1, "link", ref(A, 1), ref(foreign, 1)), edit(2, "mark_absent", ref(A, 1), absent=foreign),
             edit(3, "unlink", ref(A, 99)), edit(4, "unlink", ref(C, 5)),  # C5 stands alone: nothing to detach
             edit(5, "unlink", ref(B, 1))]
    eff = effective_matrix(build(), edits, [])
    assert eff.orphaned_edit_ids == ["cme_1", "cme_2", "cme_3", "cme_4"]
    assert eff.edit_status["cme_5"] == "applied" and eff.counts["manual"] == 1


def test_an_ai_link_on_an_unmatched_cell_applies_and_is_labelled_ai() -> None:
    eff = effective_matrix(build(), [], [ai(1, ref(B, 2), ref(C, 5), "unmatched")])
    cell = eff.rows[1]["cells"][2]
    assert (cell["state"], cell["confidence"], cell["ai_link_id"]) == ("matched", "ai", "cak_1") and "edit_id" not in cell
    assert eff.counts["ai"] == 1 and eff.counts["manual"] == 0 and eff.ai_status == {"cak_1": "applied"}
    assert len(eff.rows) == 4, "the row the page stood in alone is merged into the answered row"


def test_an_ai_link_on_a_doubtful_cell_replaces_the_medium_page() -> None:
    eff = effective_matrix(build(), [], [ai(1, ref(A, 2), ref(C, 5), "doubtful")])
    # row 2 holds B2 at medium; the link says the A2 sheet continues as C5, but the doubtful cell is the one at C:
    assert eff.ai_status == {"cak_1": "superseded"}, "C is not the doubtful cell of that row (C is unmatched there)"
    eff = effective_matrix(build(), [], [ai(1, ref(A, 2), ref(B, 3), "doubtful")])
    cell = eff.rows[1]["cells"][1]
    assert (cell["page"]["page_number"], cell["confidence"], cell["ai_link_id"]) == (3, "ai", "cak_1")
    assert eff.ai_status == {"cak_1": "applied"}
    assert any(r["cells"][1]["state"] == "matched" and r["cells"][1]["page"]["page_number"] == 2 and "confidence" not in r["cells"][1] for r in eff.rows)


def test_manual_beats_ai_and_the_link_reads_superseded() -> None:
    links = [ai(1, ref(B, 2), ref(C, 5), "unmatched")]
    eff = effective_matrix(build(), [edit(1, "unlink", ref(C, 5))], links)
    assert eff.ai_status == {"cak_1": "superseded"} and eff.counts["ai"] == 0 and eff.counts["manual"] == 1
    assert eff.edit_status == {"cme_1": "applied"}
    undone = effective_matrix(build(), [edit(1, "unlink", ref(C, 5)), edit(2, "undo", None, undoes="cme_1")], links)
    assert undone.ai_status == {"cak_1": "applied"} and undone.counts["ai"] == 1, "undo the edit and the model's link shows again"


def test_an_ai_link_bound_to_another_build_or_to_a_cell_in_another_state_is_superseded() -> None:
    other = effective_matrix(build(), [], [ai(1, ref(B, 2), ref(C, 5), "unmatched", matrix_id="cmx_OLD")])
    assert other.ai_status == {"cak_1": "superseded"} and other.counts["ai"] == 0
    wrong_state = effective_matrix(build(), [], [ai(1, ref(B, 1), ref(C, 5), "unmatched")])
    assert wrong_state.ai_status == {"cak_1": "superseded"}, "B1 is linked at C already: the cell is no longer unmatched"
    missing = effective_matrix(build(), [], [ai(1, ref(B, 2), ref("ver_Z", 1), "unmatched")])
    assert missing.ai_status == {"cak_1": "superseded"}
    determined_absent = effective_matrix(build(), [], [ai(1, ref(B, 3), ref(C, 5), "unmatched")])
    assert determined_absent.ai_status == {"cak_1": "superseded"}, "the cell was ``absent``, not ``unmatched``: no candidates were left"
    joins_two_rows = effective_matrix(build(), [], [ai(1, ref(B, 2), ref(C, 4), "unmatched")])
    assert joins_two_rows.ai_status == {"cak_1": "superseded"}, "C4 already stands in a row that links older versions"
    assert joins_two_rows.counts["ai"] == 0


def test_the_same_inputs_give_the_same_bytes_whatever_the_order_they_arrive_in() -> None:
    edits = [edit(1, "link", ref(B, 2), ref(C, 5)), edit(2, "unlink", ref(B, 1)), edit(3, "mark_absent", ref(A, 4), absent=C),
             edit(4, "undo", None, undoes="cme_2")]
    links = [ai(2, ref(B, 2), ref(C, 5), "unmatched"), ai(1, ref(A, 2), ref(B, 3), "doubtful")]
    first = canonical_json(effective_matrix(build(), edits, links).rows)
    generator = random.Random(5)
    for _ in range(10):
        shuffled_edits, shuffled_links = edits[:], links[:]
        generator.shuffle(shuffled_edits)
        generator.shuffle(shuffled_links)
        assert canonical_json(effective_matrix(build(), shuffled_edits, shuffled_links).rows) == first
    assert canonical_json(effective_matrix(build(), edits, links).rows) == first
    # and the stored build is not changed by reading it
    stored = build()
    effective_matrix(stored, edits, links)
    assert canonical_json(stored.rows) == canonical_json(build().rows)


def test_a_page_is_shown_with_its_profile_identity_from_the_build() -> None:
    index = page_index(build())
    assert index[(B, 6)] == "cpr_B6" and index[(C, 5)] == "cpr_C5" and index[(A, 1)] == "cpr_A1"


def test_the_pairs_of_each_adjacent_transition_come_from_the_effective_rows() -> None:
    eff = effective_matrix(build(), [edit(1, "link", ref(B, 2), ref(C, 5))], [ai(1, ref(B, 3), ref(A, 99), "unmatched")])
    pairs = adjacent_pairs(build(), eff, edit_no=1)
    assert pairs.order == (A, B, C) and pairs.edit_no == 1 and pairs.matrix_id == "cmx_ONE"
    ab, bc = pairs.transitions
    assert [(p.page_a and p.page_a.page_number, p.page_b and p.page_b.page_number, p.relation) for p in ab.pairs] == [
        (1, 1, "matched"), (2, 2, "matched"), (None, 3, "added"), (4, 4, "matched")]
    assert [(p.page_a and p.page_a.page_number, p.page_b and p.page_b.page_number, p.relation, p.confidence) for p in bc.pairs] == [
        (1, 1, "matched", "high"), (2, 5, "matched", "manual"), (3, None, "removed", None), (4, 4, "matched", "high")]
    assert bc.pairs[1].edit_ids == ("cme_1",) and not any(p.ai_dependent for p in bc.pairs)
    ai_eff = effective_matrix(build(), [], [ai(1, ref(B, 2), ref(C, 5), "unmatched")])
    assert any(p.ai_dependent and p.ai_link_ids == ("cak_1",) for p in adjacent_pairs(build(), ai_eff, edit_no=0).transitions[1].pairs)
    unmatched = adjacent_pairs(build(), effective_matrix(build(), [], []), edit_no=0).transitions[1].pairs[1]
    assert unmatched.relation == "unmatched" and [c.page_number for c in unmatched.candidates] == [5]
