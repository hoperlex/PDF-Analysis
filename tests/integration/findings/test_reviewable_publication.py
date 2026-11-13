"""Fresh admission keeps relevant issues reviewable without pretending evidence."""
from types import SimpleNamespace

from sqlalchemy import text

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.findings import (CandidateGroup, CandidateMember, finding_by_uid, publish_candidate_groups,
    publish_gate_result, published_finding_count, run_grounding_gate)
from auditmanager.exports.query import export_rows
from auditmanager.exports.serializer import render_csv


def _publish(session, seeded, groups, **kwargs):
    return publish_candidate_groups(session, groups=groups, gate_inputs=kwargs.pop("gate_inputs", None),
        run_id=seeded.run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", reviewable=True, **kwargs)


def _group(number, count=1, **kwargs):
    return CandidateGroup(f"group_{number}", tuple(CandidateMember(f"xobs_{number}_{member}",
        f"Нужно согласовать сечение кабеля оборудования ЩР-{number}, вариант {member}.", **kwargs)
        for member in range(count)))


def test_171_members_of_134_groups_remain_reviewable_and_replay_keeps_their_identities(session, seeded):
    groups = [_group(number, 2 if number < 37 else 1, other_source_count=1) for number in range(134)]
    result = _publish(session, seeded, groups)
    assert result.published_count == 134
    assert result.observation_count == 171
    assert published_finding_count(session, seeded.run_id) == 134
    row = finding_by_uid(session, result.finding_uids[0])
    assert row.grounding_kind == "unverified" and row.unverified_reason == "source_binding_unverified"
    assert session.execute(text("SELECT count(*) FROM finding_evidence WHERE finding_observation_id IN "
        "(SELECT finding_observation_id FROM finding_observation WHERE run_id=:run)"), {"run": seeded.run_id}).scalar() == 0
    replay = _publish(session, seeded, groups)
    assert replay.finding_uids == result.finding_uids
    assert replay.observation_count == 171
    assert published_finding_count(session, seeded.run_id) == 134
    csv_rows = export_rows(session, seeded.run_id)
    assert len(csv_rows) == 134 and all(row.evidence_page is None for row in csv_rows)
    content = render_csv(csv_rows).decode("utf-8-sig")
    assert "unverified_reason" in content and "source_binding_unverified" in content


def test_unverified_decision_captures_real_votes_comments_and_limitation_atomically(session, seeded):
    result = _publish(session, seeded, [_group(1)])
    finding = finding_by_uid(session, result.finding_uids[0])
    geometry = SimpleNamespace(portal_crops_in=lambda *_: (), evidence_boxes_in=lambda *_: {})
    previous = registered_decision_recorded()
    register_decision_recorded(MemoryCaptureAssembler(geometry=geometry))
    try:
        def decide(kind, comment):
            return record_decision(session, finding_uid=finding.finding_uid,
                finding_observation_id=finding.finding_observation_id,
                event_type=kind, comment=comment, author_label="Эксперт", author_user_uid=None)
        decide("comment", "Проверить по рабочей схеме.")
        decide("reject", "Это допустимое исполнение для данного режима.")
        decide("accept", "Получена уточнённая схема: сечение нужно согласовать.")
    finally:
        register_decision_recorded(previous)
    assert session.execute(text("SELECT count(*) FROM decision_memory_case")).scalar() == 1
    assert session.execute(text("SELECT count(*) FROM decision_memory_decision")).scalar() == 2
    assert session.execute(text("SELECT count(*) FROM decision_memory_comment")).scalar() == 1
    content = session.execute(text("SELECT unverified_reason FROM decision_memory_content")).scalar()
    assert content == "source_binding_unverified"
    assert session.execute(text("SELECT capture_version FROM decision_memory_case")).scalar() == "dm-capture/3"
    assert session.execute(text("SELECT current_verdict FROM decision_memory_case_current")).scalar() == "accepted"


def test_unique_literal_native_source_gets_real_offsets(session, seeded, text_layer):
    page = text_layer.pages[0]
    quote = text_layer.slice(page.char_start, page.char_end)[:100]
    group = _group(1, native_sources=((page.page_number, quote),), other_source_count=1)
    result = _publish(session, seeded, [group], text_layer=text_layer)
    row = finding_by_uid(session, result.finding_uids[0])
    assert row.grounding_kind == "text_span" and row.unverified_reason is None
    stored = session.execute(text("SELECT quote, char_start, char_end FROM finding_evidence")).one()
    assert stored == (quote, page.char_start, page.char_start + len(quote))


def test_semantic_match_reuses_primary_finding_without_duplicate_or_vote_change(session, seeded,
        make_observations, corpus, text_layer):
    anchor = corpus.seeded_anchors()[0]
    observation_set = make_observations([{"category": "internal_contradiction", "finding_text": "Требуется согласование.",
        "evidence": [anchor]}])
    primary = publish_gate_result(session, gate_result=run_grounding_gate(observation_set, text_layer),
        observation_set=observation_set, run_id=seeded.run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid, reviewable=True)
    target = primary.finding_uids[0]
    semantic_group = CandidateGroup("semantic_match", (
        CandidateMember("primary_text_0", "Требуется согласование.", primary_text_ordinals=(0,)),
        CandidateMember("graphical_member", "На чертеже другое сечение.", other_source_count=1)))
    result = _publish(session, seeded, [semantic_group],
        primary_findings={0: target})
    assert result.finding_uids == (target,) and published_finding_count(session, seeded.run_id) == 1
    assert finding_by_uid(session, target).finding_text == "Требуется согласование."


def test_executor_reads_real_primary_wording_and_publishes_it_once(session, seeded, corpus):
    import json
    from auditmanager.analysis.public import publish_artifact
    from auditmanager.runs.executor import _read_gate_inputs, _run_evidence_gate
    from tests.integration.findings.test_candidate_publication import _executor_world, _text_observations, _run_row
    store, outputs, blobs = _executor_world(corpus, seeded)
    raw = _text_observations(corpus, seeded)
    original = raw["observations"][0]
    review = json.loads(store.objects[blobs["analysis.extended_review"]])
    review["result"]["flow_repair_policy"] = {"version": "v2-flow-repair-v1"}
    primary = review["result"]["observations"][3]
    primary.update(title=original["category"], description=original["finding_text"],
        original_primary_observation=original)
    outputs.refs["analysis.extended_review"], _ = publish_artifact(store, "analysis.extended_review", review)
    inputs = _read_gate_inputs(observations_document=raw, outputs=outputs, blob_store=store,
        publication_mode="one_list", run_id=seeded.run_id, version_uid=seeded.version_uid)
    _, result = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)
    assert result.published_count == 3
    assert result.published[0].finding_uid in result.candidates.finding_uids
    again = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)[1]
    assert result.finding_uids == again.finding_uids
    assert published_finding_count(session, seeded.run_id) == 3


def test_wrong_run_version_cannot_create_reviewable_finding(session, seeded):
    import pytest
    from auditmanager.shared.errors import DomainError
    with pytest.raises(DomainError):
        publish_candidate_groups(session, groups=[_group(1)], gate_inputs=None, run_id=seeded.run_id,
            project_uid=seeded.project_uid, version_uid="ver_01M2545JSD15ETSNNV904X991J",
            analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="recorded", reviewable=True)


def test_refused_storage_write_rolls_back_the_whole_reviewable_publication(session, seeded):
    import pytest
    from auditmanager.shared.errors import DomainError
    with pytest.raises(DomainError):
        publish_candidate_groups(session, groups=[_group(1), _group(2)], gate_inputs=None, run_id=seeded.run_id,
            project_uid=seeded.project_uid, version_uid=seeded.version_uid,
            analysis_profile_id="ap_invalid", prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="recorded", reviewable=True)
    assert published_finding_count(session, seeded.run_id) == 0


def test_csv_and_xlsx_active_sets_follow_real_reject_then_accept(session, seeded):
    import csv
    import io
    from auditmanager.exports.service import export_run_csv
    from auditmanager.exports.xlsx.query import read_xlsx_projection
    from tests.integration.dashboard.one_list_seed import insert_run

    run_id = insert_run(session, seeded.project_uid, seeded.version_uid, mode="one_list")
    profiles = session.execute(text("SELECT analysis_profile_id, prompt_bundle_id FROM audit_run WHERE run_id=:r"),
                               {"r": run_id}).mappings().one()
    run = SimpleNamespace(run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid, **profiles)
    published = _publish(session, run, [_group(1), _group(2)])
    first = finding_by_uid(session, published.finding_uids[0])
    all_ids = set(published.finding_uids)

    def exported(selection):
        rows = csv.DictReader(io.StringIO(export_run_csv(session, run_id, verdict=selection).content.decode("utf-8-sig")))
        csv_ids = {row["finding_uid"] for row in rows}
        _, findings = read_xlsx_projection(session, run_id, page_labels={},
            citations_by_finding={uid: () for uid in all_ids}, attribution="Синтетический тест", verdict=selection)
        xlsx_ids = {finding.finding_uid for finding in findings}
        assert csv_ids == xlsx_ids
        return csv_ids

    assert exported("active") == exported("all") == all_ids
    for event_type, expected in (("reject", all_ids - {first.finding_uid}), ("accept", all_ids)):
        record_decision(session, finding_uid=first.finding_uid, finding_observation_id=first.finding_observation_id,
            event_type=event_type, comment="Повторная проверка инженером.", author_label="Эксперт", author_user_uid=None)
        assert exported("active") == expected
        assert exported("all") == all_ids
    assert published_finding_count(session, run_id) == 2


def test_surviving_visual_work_is_published_when_primary_reply_and_text_layer_are_missing(session, seeded, corpus):
    import json
    from auditmanager.analysis.public import publish_artifact
    from auditmanager.runs.executor import _read_gate_inputs, _run_evidence_gate
    from tests.integration.findings.test_candidate_publication import _executor_world, _run_row
    store, outputs, blobs = _executor_world(corpus, seeded)
    review = json.loads(store.objects[blobs["analysis.extended_review"]])
    review["status"] = "partial"
    review["result"]["flow_repair_policy"] = {"version": "v2-flow-repair-v1"}
    review["result"]["observations"] = review["result"]["observations"][:3]
    outputs.refs["analysis.extended_review"], _ = publish_artifact(store, "analysis.extended_review", review)
    outputs.refs.pop("prepared.text_layer")
    inputs = _read_gate_inputs(observations_document=None, outputs=outputs, blob_store=store,
        publication_mode="one_list", run_id=seeded.run_id, version_uid=seeded.version_uid)
    assert inputs is not None and inputs.observation_set is None and inputs.text_layer is None
    _, result = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)
    assert result.published_count == 2 and result.published == ()
    assert published_finding_count(session, seeded.run_id) == 2


def test_migration_refuses_downgrade_with_unverified_review_data(session, seeded, monkeypatch):
    import importlib.util
    from pathlib import Path
    import pytest
    _publish(session, seeded, [_group(1)])
    path = Path(__file__).resolve().parents[3] / "db/migrations/versions/20261113_0068_reviewable_findings.py"
    spec = importlib.util.spec_from_file_location("reviewable_migration_test", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration.op, "get_bind", lambda: session.connection())
    with pytest.raises(RuntimeError, match="downgrade refused"):
        migration.downgrade()
    assert published_finding_count(session, seeded.run_id) == 1


def test_semantic_text_graphics_group_retains_all_claims_blocks_and_crops_in_human_memory(
        session, seeded, make_observations, corpus, text_layer, block_index):
    from auditmanager.bootstrap.adapters import _finding_view
    from auditmanager.findings import published_findings, published_finding_evidence, published_finding_block_evidence
    from auditmanager.storage.public import derive_blob_id
    from tests.integration.findings.test_candidate_publication import _geometry, _item, BLK_A, BOX_A, CROP_A
    raw_text = "Требуется согласовать расчётную нагрузку."
    observation_set = make_observations([{"category": "internal_contradiction", "finding_text": raw_text,
                                        "evidence": [corpus.seeded_anchors()[0]]}])
    primary = publish_gate_result(session, gate_result=run_grounding_gate(observation_set, text_layer, block_index),
        observation_set=observation_set, run_id=seeded.run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid, reviewable=True, extended_observation_refs={0: "t_0"})
    group = CandidateGroup("semantic_match", (
        CandidateMember("t_0", raw_text, primary_text_ordinals=(0,)),
        CandidateMember("g_0", "На чертеже другая нагрузка этого же ВРУ.", block_evidence=(_item(),)),
        CandidateMember("u_0", "Уточнить режим нагрузки по полной схеме.", other_source_count=1)))
    _publish(session, seeded, [group], primary_findings={0: primary.finding_uids[0]}, gate_inputs=_geometry(seeded.version_uid))
    head = finding_by_uid(session, primary.finding_uids[0])
    rows = published_findings(session, seeded.run_id)
    merged = [row for row in rows if row.finding_observation_id != head.finding_observation_id]
    view = _finding_view(head, published_finding_evidence(session, seeded.run_id), SimpleNamespace(), merged,
                         published_finding_block_evidence(session, seeded.run_id))
    assert view.origin == "cross_check" and view.block_evidence[0].portal_block_id == BLK_A
    blob_id = str(derive_blob_id(sha256="b" * 64, size=4096))
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:id)"), {"id": blob_id})
    crops = ({"portal_block_id": BLK_A, "page_number": 2, "bbox_norm": BOX_A,
              "blob_id": blob_id, "sha256": CROP_A, "size_bytes": 4096, "width_px": 900, "height_px": 700},)
    geometry = SimpleNamespace(portal_crops_in=lambda *_: crops, evidence_boxes_in=lambda *_: {})
    previous = registered_decision_recorded()
    register_decision_recorded(MemoryCaptureAssembler(geometry=geometry))
    try:
        for kind in ("accept", "reject"):
            record_decision(session, finding_uid=head.finding_uid, finding_observation_id=head.finding_observation_id,
                event_type=kind, comment="Сверено по общей схеме.", author_label="Эксперт", author_user_uid=None)
    finally:
        register_decision_recorded(previous)
    assert session.execute(text("SELECT capture_version FROM decision_memory_case")).scalar() == "dm-capture/4"
    sources = session.execute(text("SELECT source_observations FROM decision_memory_content")).scalar()
    assert len(sources) == 3 and {s["finding_text"] for s in sources} == {m.finding_text for m in group.members}
    assert next(s for s in sources if s["grounding_kind"] == "unverified")["unverified_reason"] == "source_binding_unverified"
    assert session.execute(text("SELECT portal_block_id FROM decision_memory_block_evidence")).scalar() == BLK_A
    assert session.execute(text("SELECT source_ref FROM decision_memory_crop")).scalar() == BLK_A
    assert session.execute(text("SELECT count(*) FROM decision_memory_evidence")).scalar() == 1
    assert session.execute(text("SELECT count(*) FROM decision_memory_decision")).scalar() == 2
