"""The built matrix against the synthetic corpus' answer key (`CMP-MATRIX-01`): real profiles, real database."""

from __future__ import annotations

import time

from auditmanager.comparison.matrix.effective import canonical_json
from auditmanager.comparison.public import matrix_build_dedupe_key


def _sheet_of(row: dict, versions: list[str], key: dict) -> str:
    """The key's sheet id of a matrix row (all the pages of one row agree)."""
    ids = set()
    for cell in row["cells"]:
        if cell["state"] != "matched":
            continue
        position = versions.index(cell["version_uid"])
        pages = key["versions"][position]["pages"]
        ids.add(pages[cell["page"]["page_number"] - 1]["sheet_id"])
    assert len(ids) == 1, ids
    return ids.pop()


def test_the_built_matrix_has_the_sheet_identity_of_the_key(service, lab, vs1_key) -> None:
    doc = lab.clone()
    began = time.perf_counter()
    result = service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    elapsed = time.perf_counter() - began
    assert result.outcome == "built" and result.build is not None
    matrix = service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert matrix["state"] == "ready" and "stale_reasons" not in matrix
    assert matrix["revision"] == {"matrix_id": result.build.matrix_id, "edit_no": 0}
    assert matrix["progress"] == {"total": 32, "ready": 32, "failed": 0}
    assert [c["version_uid"] for c in matrix["columns"]] == list(doc.versions)

    by_sheet: dict[str, list[dict]] = {}
    for row in matrix["rows"]:
        by_sheet.setdefault(_sheet_of(row, list(doc.versions), vs1_key), []).append(row)
    assert sorted(by_sheet) == [item["sheet_id"] for item in vs1_key["sheet_identity"]]
    # one row for each sheet, except the one the key says was split in V5: the part that has no older page is a row
    # of its own (one older page is one pair), flagged ``split``
    assert {sheet: len(rows) for sheet, rows in by_sheet.items() if len(rows) > 1} == {"E05": 2}

    for identity in vs1_key["sheet_identity"]:
        for index, version_key in enumerate(vs1_key["versions"]):
            wanted = identity["pages"].get(version_key["id"], [])
            found = [
                (c["page"]["page_number"], c)
                for row in by_sheet[identity["sheet_id"]] for c in [row["cells"][index]] if c["state"] == "matched"
            ]
            assert sorted(n for n, _ in found) == sorted(wanted[:2] if identity["sheet_id"] == "E05" else wanted[:1]), (
                identity["sheet_id"], version_key["id"], found)
            if len(wanted) > 1 and identity["sheet_id"] != "E05":
                assert all("duplicate" in c["flags"] for _n, c in found), "the duplicated sheet carries the flag"
    # the scans carry their flag, the duplicate is counted, the split parts are flagged
    scans = [(i, c["page"]["page_number"]) for row in matrix["rows"] for i, c in enumerate(row["cells"])
             if c["state"] == "matched" and "scan" in c["flags"]]
    assert sorted(scans) == [(3, 4), (4, 4)]
    assert matrix["counts"]["duplicates"] == 1 and matrix["counts"]["rows"] == len(matrix["rows"]) == 8
    split_cells = [c for row in matrix["rows"] for c in row["cells"] if c["state"] == "matched" and "split" in c["flags"]]
    assert {(c["version_uid"], c["page"]["page_number"]) for c in split_cells} == {
        (doc.versions[3], 5), (doc.versions[4], 5), (doc.versions[4], 6)}
    assert elapsed < 60


def test_a_second_build_of_the_same_inputs_writes_nothing(service, lab) -> None:
    doc = lab.clone()
    first = service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    second = service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert (first.outcome, second.outcome) == ("built", "existing")
    assert second.build is not None and first.build is not None and second.build.matrix_id == first.build.matrix_id
    assert lab.rows("SELECT count(*) AS n FROM comparison_matrix WHERE document_uid = :d", d=doc.document_uid)[0]["n"] == 1


def test_the_same_profiles_and_order_give_the_same_matrix_bytes_in_two_documents(service, lab) -> None:
    """Determinism through the database: two documents with equal profile content (different identities) give the
    same rows once the identities are put aside."""
    first, second = lab.clone(), lab.clone()
    a = service.build_matrix(project_uid=first.project_uid, document_uid=first.document_uid).build
    b = service.build_matrix(project_uid=second.project_uid, document_uid=second.document_uid).build
    assert a is not None and b is not None

    def shape(build, doc) -> bytes:
        names = {v: f"V{i}" for i, v in enumerate(doc.versions)}
        text_ = canonical_json({"rows": build.rows, "unassigned": build.unassigned}).decode()
        import re
        for uid, name in names.items():
            text_ = text_.replace(uid, name)
        return re.sub(r"cpr_[0-9A-Z]{26}", "cpr", text_).encode()

    assert shape(a, first) == shape(b, second)


def test_the_dedupe_key_is_one_live_build_per_document() -> None:
    assert matrix_build_dedupe_key("doc_X") == "matrix_build:doc_X"
