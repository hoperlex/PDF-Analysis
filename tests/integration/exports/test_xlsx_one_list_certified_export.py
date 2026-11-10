"""`FIX-685` (D-685): a ``one_list`` run that pins a norm snapshot still exports once it has a block finding (PostgreSQL and S3).

A run that pins a verified retrieval set is read by the certified chain: ``export_run_xlsx`` calls W57a's citation reader with the run's
registered profile and refuses the whole workbook (``required_norm_unavailable``) when the reader refuses. A block finding of a ``one_list`` run
is written by the real publisher with ``grounding_kind = 'portal_block'`` and the stage ``block_analysis`` / ``finding_merge``, and the reader
used to accept the stage ``text_analysis`` only. What this suite pins, over the real publisher, the real reader and the version's real portal
companion:

* the run pinned to a verified set, with a certified text finding (a certified zero) and a drawing and a cross-check finding, is exported by the
  certified chain: the three rows with their sources, the citation source naming the snapshot and the set, two exports byte-identical;
* the control that the reader is what decides: the same run without a succeeded ``norm_verification`` stage is refused as before;
* the control that the block rows are read, not skipped: a block observation written under the stage ``text_analysis`` is refused by the same reader.

The pin, the verified set, its two custody bindings and the stage row are seeded by hand (``session_replication_role = replica`` for the rows the
norms builder owns); the findings are not. Every transaction is rolled back by the harness.
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import zipfile
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports import ExportAuthorization, export_run_xlsx
from auditmanager.findings import CandidateGroup, publish_candidate_groups
from auditmanager.findings.public import read_verified_citations
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AnalysisProfileId, FindingObservationId, FindingUid, PromptBundleId, RunId, StageLayoutRevisionId
from auditmanager.storage.models import derive_blob_id, parse_blob_id
from tests.integration.dashboard.one_list_seed import BLK_A, BLK_B, block_member, geometry
from tests.integration.exports.test_xlsx_run_export import _add_companion

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _uid(prefix: str) -> str:
    return prefix + "_" + "".join(random.choices(_ALPHABET, k=26))


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _authorization(run_id: str) -> ExportAuthorization:
    return ExportAuthorization(
        run_id=run_id, principal_id="usr_01M5B0000000000000000000U1", operation="exportRunXlsx", decision="allow",
        decision_ref="role-register:exportRunXlsx",
    )


def _export(session: Session, blob_store, run_id: str):  # type: ignore[no-untyped-def]
    """The use case with W57a's real citation reader injected, as the composition root injects it."""
    return export_run_xlsx(
        session, run_id, authorization=_authorization(run_id),
        read_blob=lambda blob_id: blob_store.read(parse_blob_id(blob_id)),
        read_citations=read_verified_citations,
    )


def _pinned_one_list_run(session: Session, project_uid: str, version_uid: str, *, certified: bool) -> dict[str, str]:
    """A published ``one_list`` run pinned to a verified retrieval set; ``certified`` also gives it the succeeded ``norm_verification`` stage."""
    ids = {"snapshot": _uid("ns"), "set": _uid("nrs"), "run": str(RunId.new()), "profile": str(AnalysisProfileId.new()),
           "bundle": str(PromptBundleId.new())}
    key = "key-" + ids["snapshot"]
    session.execute(text("SET LOCAL session_replication_role = replica"))  # the norms builder's rows: no foreign keys, no triggers
    session.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, content_digest, undated_documents, "
        "document_count, segmentation_profile, repair_count, unreliable_count) VALUES (:s, :k, :k, :d, 0, 1, 'seg', 0, 0)"),
        {"s": ids["snapshot"], "k": key, "d": _sha("digest")})
    blobs = {}
    for role, size in (("norm_retrieval_set", 10), ("norm_catalogue", 11)):
        sha = _sha(f"{ids['set']}:{role}")
        blob_id = str(derive_blob_id(sha256=sha, size=size))
        blobs[role] = (blob_id, sha, size)
        session.execute(text(
            "INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) VALUES (:b, 'available', :h, :n, 'application/json')"),
            {"b": blob_id, "h": sha, "n": size})
    (set_blob, set_sha, set_size), (catalogue_blob, catalogue_sha, catalogue_size) = blobs["norm_retrieval_set"], blobs["norm_catalogue"]
    session.execute(text(
        "INSERT INTO norm_retrieval_set (norm_retrieval_set_id, norms_snapshot_id, map_sha256, reviewed_content_key, chunking_profile, "
        "embedding_profile, builder_version, state, expected_set_sha256, observed_set_sha256, expected_catalogue_sha256, "
        "observed_catalogue_sha256, set_blob_id, set_size_bytes, catalogue_blob_id, catalogue_size_bytes, prompt_part_characters) "
        "VALUES (:r, :s, :m, :k, 'chunk', 'embed', 'b1', 'verified', :a, :a, :c, :c, :sb, :sn, :cb, :cn, 100)"),
        {"r": ids["set"], "s": ids["snapshot"], "m": _sha("map"), "k": key, "a": set_sha, "c": catalogue_sha, "sb": set_blob, "sn": set_size,
         "cb": catalogue_blob, "cn": catalogue_size})
    for role, (blob_id, _, _) in blobs.items():
        session.execute(text(
            "INSERT INTO norm_custody_binding (norm_custody_binding_id, norm_custody_admission_id, role, target_kind, target_id, "
            "anchor_kind, anchor, blob_id) VALUES (:n, :a, :role, 'norm_retrieval_set', :t, 'artifact', :role, :b)"),
            {"n": _uid("nbd"), "a": _uid("nad"), "role": role, "t": ids["set"], "b": blob_id})
    session.execute(text("SET LOCAL session_replication_role = origin"))

    plan = json.dumps({"layout_revision_id": str(StageLayoutRevisionId.new()), "cells": [
        {"cell_key": "review:main", "model_id": "claude-opus-5-5", "effort": "medium", "access": "subscription"}]})
    session.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
        "frozen_input_digest, binding_state, stage_plan, publication_mode, norms_snapshot_id, norm_retrieval_set_id) "
        "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :d, 'pending', CAST(:plan AS jsonb), 'one_list', :s, :set)"),
        {"r": ids["run"], "p": project_uid, "v": version_uid, "ap": ids["profile"], "pb": ids["bundle"], "d": _sha(ids["run"]),
         "plan": plan, "s": ids["snapshot"], "set": ids["set"]})
    for step in ("queued", "running", "validating", "published"):
        session.execute(text(
            "UPDATE audit_run SET state = :s, terminal_at = CASE WHEN :s = 'published' THEN now() ELSE NULL END, "
            "degradation_set = CASE WHEN :s = 'published' THEN '[]'::jsonb ELSE degradation_set END WHERE run_id = :r"),
            {"s": step, "r": ids["run"]})
    if certified:
        session.execute(text(
            "INSERT INTO stage_result (run_id, stage_id, stage_version, status, started_at, finished_at) "
            "VALUES (:r, 'norm_verification', '1.0.0', 'succeeded', now(), now())"), {"r": ids["run"]})
    return ids


def _certified_zero_text_finding(session: Session, project_uid: str, version_uid: str, ids: dict[str, str]) -> str:
    """The text path's finding of a run that pins a set: a non-norm category with a certified partition of zero citations."""
    finding_uid, observation_id = str(FindingUid.new()), str(FindingObservationId.new())
    session.execute(
        text("INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) VALUES (:f, :p, :v, :r, 'layout')"),
        {"f": finding_uid, "p": project_uid, "v": version_uid, "r": ids["run"]})
    session.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
        "recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode, norm_citation_count) "
        "VALUES (:o, :r, :f, 'text_analysis', 'layout', 'Текстовое замечание', 'Исправить', true, :ap, :pb, 'recorded', 0)"),
        {"o": observation_id, "r": ids["run"], "f": finding_uid, "ap": ids["profile"], "pb": ids["bundle"]})
    session.execute(text(
        "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, page_number, quote, char_start, char_end) "
        "VALUES (:o, 0, 1, 'x', 0, 1)"), {"o": observation_id})
    session.execute(text("UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"), {"o": observation_id, "f": finding_uid})
    return finding_uid


def _publish_blocks(session: Session, project_uid: str, version_uid: str, ids: dict[str, str]):  # type: ignore[no-untyped-def]
    """A drawing finding and a cross-check finding, written by the real publisher with the run's own profile, bundle and mode."""
    groups = [
        CandidateGroup("xgrp_1", (block_member("xgrp_1_0", BLK_A),)),
        CandidateGroup("xgrp_2", (block_member("xgrp_2_0", BLK_B, other_source_count=1),)),
    ]
    result = publish_candidate_groups(
        session, groups=groups, gate_inputs=geometry(version_uid), run_id=ids["run"], project_uid=project_uid, version_uid=version_uid,
        analysis_profile_id=ids["profile"], prompt_bundle_id=ids["bundle"], provider_mode="recorded",
    )
    assert len(result.published) == 2 and result.diagnostic_count == 0
    return result.published


def _cells(content: bytes, part: str = "xl/worksheets/sheet2.xml") -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read(part))
    cells: dict[str, str] = {}
    for cell in root.findall(f".//{MAIN}c"):
        node = cell.find(f"{MAIN}is/{MAIN}t")
        if node is None:
            node = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = (node.text or "") if node is not None else ""
    return cells


def _row_of(cells: dict[str, str], finding_uid: str) -> int:
    (row,) = [int(address[1:]) for address, value in cells.items() if address[0] == "M" and value == finding_uid]
    return row


def test_a_one_list_run_pinned_to_a_norm_set_exports_its_block_findings(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    ids = _pinned_one_list_run(session, seeded.project_uid, seeded.version_uid, certified=True)
    written = _certified_zero_text_finding(session, seeded.project_uid, seeded.version_uid, ids)
    drawing, cross = _publish_blocks(session, seeded.project_uid, seeded.version_uid, ids)
    _add_companion(session, blob_store, seeded.version_uid)

    export = _export(session, blob_store, ids["run"])
    # the certified chain read the run (a run with no pin names «no-citation-partitions»), and twice over the same bytes
    assert export.citation_source_ref == f"{ids['run']}:{ids['snapshot']}:{ids['set']}"
    assert export.content == _export(session, blob_store, ids["run"]).content

    sheet = _cells(export.content)
    for finding_uid, source in ((written, "Текст"), (drawing.finding_uid, "Чертёж"), (cross.finding_uid, "Сверка")):
        row = _row_of(sheet, finding_uid)
        assert sheet[f"D{row}"] == source
        # a block finding cites no norm: its norm and quote cells are empty, not dropped and not invented
        assert (sheet[f"I{row}"], sheet[f"J{row}"]) == ("", "")


def test_the_control_the_reader_decides_a_pinned_run_without_the_cite_stage_is_refused(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    ids = _pinned_one_list_run(session, seeded.project_uid, seeded.version_uid, certified=False)
    _publish_blocks(session, seeded.project_uid, seeded.version_uid, ids)
    _add_companion(session, blob_store, seeded.version_uid)
    with pytest.raises(DomainError) as refused:
        _export(session, blob_store, ids["run"])
    assert refused.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE


def test_the_control_a_block_observation_of_a_text_stage_is_still_refused(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    """The block rows are read, not skipped: a ``portal_block`` observation written under the stage ``text_analysis`` is refused by the reader.

    (A block observation that claims a norm category cannot be written at all: ``ck_finding_observation_norm_category_shape`` refuses it.)
    """
    ids = _pinned_one_list_run(session, seeded.project_uid, seeded.version_uid, certified=True)
    drawing, _ = _publish_blocks(session, seeded.project_uid, seeded.version_uid, ids)
    session.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
        "recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode, grounding_kind) "
        "SELECT :o, run_id, :f, 'text_analysis', 'drawing_discrepancy', 'Подделка', 'Нет', true, analysis_profile_id, prompt_bundle_id, "
        "provider_mode, 'portal_block' FROM audit_run WHERE run_id = :r"),
        {"o": str(FindingObservationId.new()), "f": drawing.finding_uid, "r": ids["run"]})
    _add_companion(session, blob_store, seeded.version_uid)
    with pytest.raises(DomainError) as refused:
        _export(session, blob_store, ids["run"])
    assert refused.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
