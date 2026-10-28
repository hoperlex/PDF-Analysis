"""Accepted AI links under manual edits, and the sheet pairs the series reads (`CMP-MATRIX-01`)."""

from __future__ import annotations

from sqlalchemy import text

from auditmanager.comparison.public import read_adjacent_sheet_pairs
from auditmanager.shared.identity import new_ulid

from .support import apply, cell_of, get, link, page


def _ai_link(lab, doc, matrix_id: str, a: tuple[str, int], b: tuple[str, int], state: str = "doubtful") -> str:
    link_id = "cak_" + new_ulid()
    with lab.sessions() as session:
        session.execute(text(
            "INSERT INTO comparison_ai_link (comparison_ai_link_id, document_uid, comparison_matrix_id, page_version_uid, "
            "page_number, other_version_uid, other_page_number, answered_state) VALUES (:id, :d, :m, :a, :an, :b, :bn, :s)"),
            {"id": link_id, "d": doc.document_uid, "m": matrix_id, "a": a[0], "an": a[1], "b": b[0], "bn": b[1], "s": state})
        session.commit()
    return link_id


def _built(service, lab):
    doc = lab.clone()
    service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    return doc, get(service, doc)


def test_an_accepted_ai_link_shapes_its_cell_and_is_labelled_never_an_experts_act(service, lab) -> None:
    doc, matrix = _built(service, lab)
    v = doc.versions
    _row, medium = cell_of(matrix, doc, 4, 5)
    assert medium["confidence"] == "medium", "the algorithm doubted the part 5.1 against the old sheet"
    link_id = _ai_link(lab, doc, matrix["revision"]["matrix_id"], (v[3], 5), (v[4], 6))
    with_ai = get(service, doc)
    row, ai_cell = cell_of(with_ai, doc, 4, 6)
    assert (ai_cell["confidence"], ai_cell["ai_link_id"]) == ("ai", link_id) and "edit_id" not in ai_cell
    assert row["cells"][3]["page"]["page_number"] == 5, "the model's page stands in the older sheet's row"
    assert with_ai["counts"]["ai"] == 1 and with_ai["counts"]["manual"] == 0
    assert with_ai["revision"]["edit_no"] == 0, "an AI link is not an edit event"
    _row, displaced = cell_of(with_ai, doc, 4, 5)
    assert "confidence" not in displaced, "the page the model displaced stands alone, unlinked"
    listed = service.list_ai_links(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=10)
    [item] = listed.items
    assert (item["ai_link_id"], item["status"], item["answered_state"], item["matrix_id"]) == (
        link_id, "applied", "doubtful", matrix["revision"]["matrix_id"])
    assert item["page"]["page_number"] == 5 and item["other_page"]["page_number"] == 6 and "page_profile_id" in item["page"]


def test_a_manual_edit_wins_over_an_ai_link_and_the_link_reads_superseded(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    v = doc.versions
    link_id = _ai_link(lab, doc, matrix["revision"]["matrix_id"], (v[3], 5), (v[4], 6))
    with_ai = get(service, doc)
    after = apply(service, doc, with_ai, [link(page(v[3], 5), page(v[4], 5))], expert_uid)
    _row, cell = cell_of(after, doc, 4, 5)
    assert cell["confidence"] == "manual" and cell["edit_id"], "the expert's choice is the cell"
    assert after["counts"]["ai"] == 0
    [item] = service.list_ai_links(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=10).items
    assert item["ai_link_id"] == link_id and item["status"] == "superseded"


def test_a_link_bound_to_another_build_is_superseded(service, lab) -> None:
    doc, matrix = _built(service, lab)
    other_doc, other_matrix = _built(service, lab)
    # a link row must name a build of its own document: bind it to the first build, then make a newer build exist
    link_id = _ai_link(lab, doc, matrix["revision"]["matrix_id"], (doc.versions[3], 5), (doc.versions[4], 6))
    with lab.sessions() as session:
        session.execute(text(
            "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, profile_signature, "
            "rules_version, algo_version, rows, unassigned, summary) SELECT :new, project_uid, document_uid, 2, "
            "repeat('a', 64), 'v1.2', 'cmp-matrix/1', rows, unassigned, summary FROM comparison_matrix WHERE comparison_matrix_id = :old"),
            {"new": "cmx_" + new_ulid(), "old": matrix["revision"]["matrix_id"]})
        session.commit()
    [item] = service.list_ai_links(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=10).items
    assert item["ai_link_id"] == link_id and item["status"] == "superseded", "it answered a build that is not the latest"
    assert other_doc.document_uid != doc.document_uid and other_matrix["state"] == "ready"


def test_the_series_reads_the_sheet_pairs_of_each_adjacent_transition(service, lab) -> None:
    doc, matrix = _built(service, lab)
    pairs = read_adjacent_sheet_pairs(lab.sessions, project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert pairs.matrix_id == matrix["revision"]["matrix_id"] and pairs.edit_no == 0 and pairs.order == doc.versions
    assert [(t.source_version_uid, t.target_version_uid) for t in pairs.transitions] == list(zip(doc.versions, doc.versions[1:]))

    def summary(index: int) -> dict[str, int]:
        out: dict[str, int] = {}
        for pair in pairs.transitions[index].pairs:
            out[pair.relation] = out.get(pair.relation, 0) + 1
        return out

    assert summary(0) == {"matched": 6}  # V1 -> V2
    assert summary(1) == {"matched": 5, "removed": 1, "added": 1}  # V2 -> V3: sheet 6 gone, the specification new
    assert summary(2) == {"matched": 6}  # V3 -> V4: the scan replaces sheet 4 and stays its pair
    last = pairs.transitions[3]  # V4 -> V5: the plan split in two parts, the duplicate sheet is a flag not a pair
    assert summary(3) == {"matched": 6, "added": 1}
    split = [p for p in last.pairs if p.split is not None]
    assert {(p.page_a.page_number if p.page_a else None, p.page_b.page_number if p.page_b else None) for p in split} == {(5, 5), (None, 6)}
    assert all(p.split.kind == "split" and p.split.role == "part" and 0 < p.split.covered_percent <= 100 for p in split)
    assert all(not p.ai_dependent for t in pairs.transitions for p in t.pairs)
    scans = [p for p in last.pairs if "scan" in p.flags]
    assert len(scans) == 1 and scans[0].page_b.page_number == 4
