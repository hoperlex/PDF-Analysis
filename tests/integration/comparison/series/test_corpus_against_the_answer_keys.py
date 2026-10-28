"""The series on the synthetic corpus VS-1 with the **real** engine, against its answer key (`CMP-SERIES-01`).

Every page is profiled by the real children, the matrix is the real build, every pair is compared by the real engine in its
ceilinged child, and the series' statuses, counts, verdicts, parts and permit are read back and judged against
``fixtures/comparison/vs1/answer_key.json`` -- authored next to the content, never captured from this lane's output. It is the
one slow test of the directory (the engine child takes seconds a pair)."""

from __future__ import annotations

from typing import Any

from auditmanager.comparison.series.verdict import verdict_codes

from .support import build, drain, pair_rows, runner_with, start


def sheet_of(key: dict[str, Any], version: str, page: int) -> str:
    for sheet in key["sheet_identity"]:
        if page in sheet["pages"].get(version, []):
            return sheet["sheet_id"]
    raise AssertionError((version, page))


def test_the_series_agrees_with_the_answer_key_sheet_by_sheet(
    lab, sessions, engine, blob_store, worker_id, service, matrix_service, expert_uid, vs1_key,
) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    series = start(service, doc, expert_uid)
    ran = drain(runner_with(sessions, engine, blob_store), worker_id, engine, sessions, doc.project_uid, limit=200)
    assert [state for kind, state in ran if kind == "series_pair"] == ["succeeded"] * 24

    done = service.get_series(series_id=series["series_id"])
    assert done["state"] == "completed", done["state"]
    from auditmanager.api.schemas import models

    models.ComparisonSeries.model_validate(done)  # what the engine wrote is what the contract can carry
    for stored in pair_rows(lab, series["series_id"]):
        models.ComparisonSheetPair.model_validate(service.get_sheet_pair(sheet_pair_id=stored["id"]))
    pages = {
        row["id"]: (row["version_uid"], int(row["page_number"]))
        for row in lab.rows("SELECT comparison_page_profile_id AS id, version_uid, page_number FROM comparison_page_profile "
                            "WHERE version_uid = ANY(CAST(:v AS text[]))", v=list(doc.versions))
    }
    version_ids = {uid: key_version["id"] for uid, key_version in zip(doc.versions, vs1_key["versions"])}
    rows = pair_rows(lab, series["series_id"])
    disagreements: list[str] = []
    for transition_key, transition in zip(vs1_key["transitions"], done["transitions"]):
        expected = {s["sheet_id"]: s for s in transition_key["sheets"]}
        seen: set[str] = set()
        for row in [r for r in rows if r["transition_no"] == done["transitions"].index(transition) + 1]:
            va, vb = transition_key["from"], transition_key["to"]
            sheet = sheet_of(vs1_key, va, pages[row["a"]][1]) if row["a"] else sheet_of(vs1_key, vb, pages[row["b"]][1])
            seen.add(sheet)
            want = expected[sheet]["expected_status"]
            if row["status"] != want:
                disagreements.append(f"{transition_key['id']} {sheet}: key {want}, series {row['status']}")
        assert seen == set(expected), transition_key["id"]
        # the counts: the key counts a split sheet once, the series counts each of its pairs
        splits = sum(len(s["parts"]) - 1 for s in transition_key["sheets"] if s.get("relation") == "split")
        counts = {k: v for k, v in transition_key["status_counts"].items()}
        summary = transition["summary"]
        assert (summary["same"], summary["zones_only"], summary["different"], summary["needs_review"], summary["added"],
                summary["removed"]) == (counts["same"], counts["same_zones_changed"], counts["different"],
                                        counts["needs_review"] + splits, counts["added"], counts["removed"]), transition_key["id"]
        assert transition["verdict"] == verdict_codes(
            {"different": counts["different"], "needs_review": counts["needs_review"], "added": counts["added"],
             "removed": counts["removed"], "failed": 0, "zones_only": counts["same_zones_changed"]},
            pairs_total=transition["items_total"], pairs_done=transition["items_total"]), transition_key["id"]
    assert disagreements == [], disagreements

    # the split sheet of V4 -> V5 is a review with its own reason and a parts coverage of both parts
    split = [r for r in rows if r["transition_no"] == 4 and r["parts"]]
    assert len(split) == 2 and {r["status"] for r in split} == {"needs_review"}
    for row in split:
        shown = service.get_sheet_pair(sheet_pair_id=row["id"])
        assert "SPLIT_SHEET" in shown["reasons"] and shown["parts"]["role"] == "part"
        # The engine registers the second part onto the left half of the older sheet (its area overlaps the first part's:
        # an item of `CMP-SERIES-01` section 9 for the engine's lane), so the ink figure is refused as unreliable and the
        # matrix's text coverage of the older sheet by its parts stands, marked as such.
        assert shown["parts"]["covered_percent"] == row["parts"]["text_percent"] and 0.0 < shown["parts"]["covered_percent"] <= 100.0
        assert row["parts"]["coverage_reliable"] is False
        assert "part" not in shown  # the engine's working member is not an API field
    # the duplicated sheet of V5 is the engine's review (DUPLICATE_SHEET), the scan of V4 is its NO_TEXT_LAYER
    by_sheet = {(r["transition_no"], sheet_of(vs1_key, vs1_key["transitions"][r["transition_no"] - 1]["to"], pages[r["b"]][1]) if r["b"] else "-"): r
                for r in rows}
    assert "DUPLICATE_SHEET" in service.get_sheet_pair(sheet_pair_id=by_sheet[(4, "E03")]["id"])["reasons"]
    assert "NO_TEXT_LAYER" in service.get_sheet_pair(sheet_pair_id=by_sheet[(3, "E04")]["id"])["reasons"]

    # the permit of V4 against the key's four classes
    key = vs1_key["transitions"][2]["permit"]
    states = {sheet: (service.get_sheet_pair(sheet_pair_id=by_sheet[(3, sheet)]["id"]).get("permit") or {}).get("state")
              for sheet in ("E01", "E02", "E03", "E04", "E05", "E07")}
    mapped = {"declared_and_found": "declared_and_found", "declared_not_found": "declared_no_diff",
              "declared_unverifiable_scan": "needs_review", "found_not_declared": "diff_not_declared"}
    expected = {sheet: mapped[name] for name, sheets in key["classes"].items() for sheet in sheets}
    assert {k: v for k, v in states.items() if v} == expected, states
    assert states["E01"] is None and states["E02"] is None  # the carrier of the permit and an unchanged sheet
