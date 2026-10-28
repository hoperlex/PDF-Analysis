"""Manual edits against a base revision, undo, replay, roles, the migrated rows, staleness and orphans
(`CMP-MATRIX-01`, ADR-0025 decisions 13, 14, 16): real PostgreSQL, real stored profiles."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid

from .support import absent, apply, cell_of, edits_of, get, key, link, page, undo, unlink


def _built(service, lab):
    doc = lab.clone()
    assert service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid).outcome == "built"
    return doc, get(service, doc)


def _count(lab, doc) -> int:
    return lab.rows("SELECT count(*) AS n FROM comparison_matrix_edit WHERE document_uid = :d", d=doc.document_uid)[0]["n"]


def test_a_batch_is_applied_together_and_the_revision_moves(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    v = doc.versions
    after = apply(service, doc, matrix, [link(page(v[0], 6), page(v[2], 6)), unlink(page(v[4], 8))], expert_uid)
    assert after["revision"] == {"matrix_id": matrix["revision"]["matrix_id"], "edit_no": 2}
    assert after["counts"]["manual"] >= 2 and after["state"] == "ready"
    row, cell = cell_of(after, doc, 2, 6)
    assert cell["confidence"] == "manual" and cell["edit_id"]
    assert row["cells"][0]["page"]["page_number"] == 6, "the older page of the row is the one the cell was linked to"
    history = edits_of(service, doc)
    assert [(e["edit_no"], e["kind"], e["source"], e["status"]) for e in history] == [
        (2, "unlink", "expert", "applied"), (1, "link", "expert", "applied")]
    assert history[1]["page"]["page_number"] == 6 and history[1]["other_page"]["version_uid"] == v[2]
    assert all("page_profile_id" in e["page"] for e in history), "an edit is shown with its profile identity"
    rows = lab.rows("SELECT edit_no, batch_position FROM comparison_matrix_edit WHERE document_uid = :d ORDER BY edit_no", d=doc.document_uid)
    assert [(r["edit_no"], r["batch_position"]) for r in rows] == [(1, 1), (2, 2)]


def test_a_moved_base_revision_is_a_stale_conflict_and_nothing_is_written(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    apply(service, doc, matrix, [unlink(page(doc.versions[4], 8))], expert_uid)
    for bad in ({"matrix_id": matrix["revision"]["matrix_id"], "edit_no": 0},  # the edit count moved
                {"matrix_id": "cmx_" + new_ulid(), "edit_no": 1}):  # another build
        with pytest.raises(DomainError) as refusal:
            service.apply_edits(
                project_uid=doc.project_uid, document_uid=doc.document_uid, base_matrix_id=bad["matrix_id"],
                base_edit_no=bad["edit_no"], edits=[unlink(page(doc.versions[3], 5))], user_uid=expert_uid,
                actor_label="Т", actor_roles=frozenset({"expert"}), idempotency_key=key())
        assert refusal.value.code is ErrorCode.CONFLICT and refusal.value.detail_fields["conflict_reason"] == "comparison_matrix_stale"
    assert _count(lab, doc) == 1
    stale_undo = dict(matrix)
    with pytest.raises(DomainError) as refusal:
        undo(service, doc, stale_undo, expert_uid)
    assert refusal.value.detail_fields["conflict_reason"] == "comparison_matrix_stale" and _count(lab, doc) == 1


def test_a_batch_with_one_invalid_edit_writes_none_of_them(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    v = doc.versions
    foreign = page("ver_" + new_ulid(), 1)
    cases = {
        "a page outside its version": [unlink(page(v[0], 7))],
        "a page of a version that is not the document's": [link(page(v[0], 1), foreign)],
        "a link that joins a version to itself": [link(page(v[0], 1), page(v[0], 2))],
        "mark_absent in the page's own version": [absent(page(v[0], 1), v[0])],
        "mark_absent in a foreign version": [absent(page(v[0], 1), foreign.version_uid)],
        "a member the kind does not take": [type(unlink(page(v[0], 1)))(kind="unlink", page=page(v[0], 1), other_page=page(v[1], 1))],
        "a link with no other page": [type(unlink(page(v[0], 1)))(kind="link", page=page(v[0], 1))],
    }
    for name, bad in cases.items():
        with pytest.raises(DomainError) as refusal:
            apply(service, doc, matrix, [unlink(page(v[4], 8)), *bad], expert_uid)
        assert refusal.value.code is ErrorCode.VALIDATION_FAILED, name
        assert refusal.value.detail_fields == {"field": "edits", "constraint": "comparison_edit_invalid"}, name
    assert _count(lab, doc) == 0, "the valid edit that came first was not written either"
    with pytest.raises(DomainError) as refusal:
        apply(service, doc, matrix, [unlink(page(v[0], 1))] * 501, expert_uid)
    assert refusal.value.detail_fields == {"field": "edits", "constraint": "comparison_edits_limit"}


def test_undo_reverses_the_latest_applied_edit_and_none_left_is_refused(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    v = doc.versions
    with pytest.raises(DomainError) as refusal:
        undo(service, doc, matrix, expert_uid)
    assert refusal.value.detail_fields["conflict_reason"] == "comparison_edit_none"
    one = apply(service, doc, matrix, [absent(page(v[0], 1), v[3])], expert_uid)
    two = apply(service, doc, one, [unlink(page(v[4], 8))], expert_uid)
    assert two["counts"]["manual"] > one["counts"]["manual"]
    back = undo(service, doc, two, expert_uid)
    assert back["revision"]["edit_no"] == 3 and back["counts"] == one["counts"] and back["rows"] == one["rows"]
    history = edits_of(service, doc)
    assert [(e["edit_no"], e["kind"], e["status"]) for e in history] == [(3, "undo", "applied"), (2, "unlink", "undone"), (1, "mark_absent", "applied")]
    assert history[0]["undoes_edit_id"] == history[1]["edit_id"]
    after_two = undo(service, doc, back, expert_uid)
    assert after_two["rows"] == matrix["rows"], "every edit undone: the algorithm alone"
    with pytest.raises(DomainError) as refusal:
        undo(service, doc, after_two, expert_uid)
    assert refusal.value.detail_fields["conflict_reason"] == "comparison_edit_none"


def test_the_same_key_replays_and_the_same_key_with_another_payload_is_refused(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    token = key()
    first = apply(service, doc, matrix, [unlink(page(doc.versions[4], 8))], expert_uid, idempotency_key=token)
    again = apply(service, doc, matrix, [unlink(page(doc.versions[4], 8))], expert_uid, idempotency_key=token)
    assert again["revision"] == first["revision"] and _count(lab, doc) == 1
    with pytest.raises(DomainError) as refusal:
        apply(service, doc, matrix, [unlink(page(doc.versions[3], 5))], expert_uid, idempotency_key=token)
    assert refusal.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE and _count(lab, doc) == 1


def test_a_writer_without_the_expert_role_is_refused_in_the_transaction_that_acts(service, lab, admin_uid) -> None:
    doc, matrix = _built(service, lab)
    with pytest.raises(DomainError) as refusal:
        apply(service, doc, matrix, [unlink(page(doc.versions[4], 8))], admin_uid, roles=frozenset({"admin"}))
    assert refusal.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(DomainError) as refusal:
        service.prepare_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid, user_uid=admin_uid,
                               actor_roles=frozenset({"admin"}), idempotency_key=key())
    assert refusal.value.code is ErrorCode.PERMISSION_DENIED and _count(lab, doc) == 0


def test_a_migrated_approval_reads_as_a_manual_edit(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    v = doc.versions
    provenance = '{"comparison_id": "cmp_' + new_ulid() + '", "sheet_link_id": "sln_' + new_ulid() + '", "link_revision": 2}'
    with lab.sessions() as session:
        session.execute(text(
            "INSERT INTO comparison_matrix_edit (comparison_matrix_edit_id, project_uid, document_uid, edit_no, kind, "
            "source, page_version_uid, page_number, other_version_uid, other_page_number, provenance, actor_user_uid, "
            "actor_label) VALUES (:id, :p, :d, 1, 'link', 'migrated_sheet_link', :v1, 6, :v3, 6, CAST(:prov AS jsonb), "
            ":u, 'Утвердил Т.')"), {"id": "cme_" + new_ulid(), "p": doc.project_uid, "d": doc.document_uid, "v1": v[0],
                                    "v3": v[2], "prov": provenance, "u": expert_uid})
        session.commit()
    [edit] = edits_of(service, doc)
    assert (edit["source"], edit["kind"], edit["status"], edit["created_by"]) == ("migrated_sheet_link", "link", "applied", expert_uid)
    assert edit["provenance"]["link_revision"] == 2 and "order_id" not in edit
    matrix_after = get(service, doc)
    assert matrix_after["revision"]["edit_no"] == 1
    _row, cell = cell_of(matrix_after, doc, 2, 6)
    assert cell["confidence"] == "manual" and cell["edit_id"] == edit["edit_id"]
    # it is an edit like any other: the next batch builds on it and an undo takes it back
    assert undo(service, doc, matrix_after, expert_uid)["rows"] == matrix["rows"]


def test_a_reorder_or_a_new_version_makes_the_build_stale_with_its_reasons(service, lab, expert_uid, sessions) -> None:
    from auditmanager.ingest.comparison_pdf.public import ComparisonVersionOrderService

    doc, matrix = _built(service, lab)
    assert matrix["state"] == "ready"
    orders = ComparisonVersionOrderService(session_factory=sessions)
    orders.append_order(
        project_uid=doc.project_uid, document_uid=doc.document_uid, version_uids=list(reversed(doc.versions)),
        base_revision_no=0, user_uid=expert_uid, actor_label="Т", actor_roles=frozenset({"expert"}), idempotency_key=key())
    reordered = get(service, doc)
    assert reordered["state"] == "stale" and reordered["stale_reasons"] == ["order_changed"]
    assert reordered["rows"] == matrix["rows"], "the stale build is still shown, as it was built"
    added = lab.add_version(doc)
    unprofiled = get(service, doc)
    assert unprofiled["stale_reasons"] == ["order_changed"], "a version with no profile yet is in the order, not in the digest"
    lab.add_version(doc, profiles=True)
    both = get(service, doc)
    assert both["state"] == "stale" and both["stale_reasons"] == ["order_changed", "profiles_changed"]
    assert added not in [c["version_uid"] for c in both["columns"]], "the columns are those of the build"


def test_an_edit_whose_cells_do_not_exist_is_kept_and_listed_as_orphaned(service, lab, expert_uid) -> None:
    doc, matrix = _built(service, lab)
    new_version = lab.add_version(doc)
    kept = apply(service, doc, matrix, [link(page(doc.versions[0], 1), page(new_version, 1))], expert_uid)
    assert len(kept["orphaned_edit_ids"]) == 1 and kept["counts"]["manual"] == 0
    [edit] = edits_of(service, doc)
    assert edit["status"] == "orphaned" and edit["edit_id"] == kept["orphaned_edit_ids"][0]
    assert _count(lab, doc) == 1, "kept in the history, not dropped"
    # an undo may take it back
    assert undo(service, doc, kept, expert_uid)["orphaned_edit_ids"] == []
