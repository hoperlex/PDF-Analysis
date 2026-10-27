"""`W57B-NORMS-CATALOGUE-XLSX-01`: the run's Excel export over a real run, PostgreSQL and S3.

The run is the CSV suite's run: the seeded baseline version executed through the recorded
v1 chain (``tests/integration/runs/harness.py``), so the findings, observations, evidence
and the verdict view are what the chain wrote, never hand-built rows. The harness seeds a
bare PDF -- the shape of every version admitted before portal bundles -- and the export
refuses it. The portal companion that labels sheets is then added the only way the schema
allows, an ``INSERT`` into ``input_manifest_entry`` (the table refuses UPDATE and DELETE, not
INSERT) of an available Blob that is really in the bucket, and the same run exports. Every
transaction is rolled back by the harness.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import text

from auditmanager.exports import ExportAuthorization, export_run_csv, export_run_xlsx
from auditmanager.exports.xlsx.labels import CATEGORY_LABELS
from auditmanager.exports.xlsx.writer import CONTENT_TYPE, FINDING_COLUMNS
from auditmanager.findings import published_finding_count
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_id, parse_blob_role
from tests.support.v1_reference_profile import resolve_reference_profile

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
#: The seeded baseline PDF's page count (``harness.seed_version``).
PAGES = 8


def _authorization(run_id: str) -> ExportAuthorization:
    return ExportAuthorization(
        run_id=run_id, principal_id="usr_01M5B0000000000000000000U1",
        operation="exportRunXlsx", decision="allow",
        decision_ref="role-register:exportRunXlsx",
    )


def _run(session, seeded, blob_store, adapter, provider_config, key) -> str:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )
    execute_run(
        session, started.run_id, blob_store=blob_store, adapter=adapter,
        provider_config=provider_config,
        text_profiles=resolve_reference_profile,
    )
    return str(started.run_id)


def _export(session, blob_store, run_id: str):
    return export_run_xlsx(
        session, run_id, authorization=_authorization(run_id),
        read_blob=lambda blob_id: blob_store.read(parse_blob_id(blob_id)),
        read_citations=None,
    )


def _companion() -> bytes:
    """A portal block list for the baseline's pages: page ``n`` is labelled ``100 + n``."""
    document = {
        "schema_version": 1,
        "coordinate_space": "normalized_page_top_left",
        "pages": [
            {"page_index": index, "width_px": 2480, "height_px": 3508, "rotation": 0}
            for index in range(PAGES)
        ],
        "blocks": [
            {
                "block_id": f"blk_{index + 1:032x}", "page_index": index,
                "page_label": 101 + index, "ordinal": 0, "block_type": "text",
                "status": "ok", "coords_norm": [0.1, 0.1, 0.9, 0.9],
            }
            for index in range(PAGES)
        ],
    }
    return json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _add_companion(session, blob_store, version_uid: str) -> None:
    payload = _companion()
    published = blob_store.put_blob(
        payload, declared_sha256=sha256_of(payload), declared_size=len(payload),
        role=parse_blob_role("source_structured_companion"), media_type="application/json",
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(
        blob_id=published.blob_id, upload_token="w57b-xlsx-run-export",
        sha256=published.sha256, size=published.size, role=published.role,
        media_type=published.media_type,
    ))
    blobs.mark_available(session, published.blob_id)
    session.execute(
        text(
            "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, "
            "media_type) VALUES (:version, 'source.structured_companion', :blob, :sha, :size, "
            "'application/json')"
        ),
        {"version": version_uid, "blob": str(published.blob_id), "sha": published.sha256,
         "size": published.size},
    )


def _cells(content: bytes, part: str) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read(part))
    cells: dict[str, str] = {}
    for cell in root.findall(f".//{MAIN}c"):
        node = cell.find(f"{MAIN}is/{MAIN}t")
        if node is None:
            node = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = (node.text or "") if node is not None else ""
    return cells


def test_a_real_v1_run_exports_with_portal_labels_and_empty_norm_columns(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    run_id = _run(session, seeded, blob_store, recorded_adapter, provider_config,
                  new_key("w57b-xlsx-real-run"))
    state = session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run_id}
    ).scalar_one()
    assert state == "published"

    # A bare PDF has no sheet labels: refused, never page numbers passed off as labels.
    with pytest.raises(DomainError) as caught:
        _export(session, blob_store, run_id)
    assert caught.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert dict(caught.value.detail_fields) == {"role": "source.structured_companion"}

    _add_companion(session, blob_store, seeded.version_uid)
    export = _export(session, blob_store, run_id)
    assert export.content_type == CONTENT_TYPE and export.run_state == "published"
    assert export.citation_source_ref == f"{run_id}:no-citation-partitions"
    assert export.page_label_source_ref.startswith(f"{seeded.version_uid}:blob_")
    assert export.content == _export(session, blob_store, run_id).content

    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    assert tuple(findings[f"{column}1"] for column in "ABCDEFGHIJK") == FINDING_COLUMNS
    rows = sorted({int(address[1:]) for address in findings if address[0] == "A"} - {1})
    expected = published_finding_count(session, run_id)
    assert expected > 0 and rows == list(range(2, expected + 2))

    # One row per finding (v1 has no members), each labelled from the companion on the
    # pages of the finding's evidence, in evidence order.
    evidence = session.execute(text(
        "SELECT f.finding_uid, e.page_number FROM finding f "
        "JOIN finding_observation o ON o.finding_uid = f.finding_uid "
        "JOIN finding_evidence e ON e.finding_observation_id = o.finding_observation_id "
        "WHERE f.allocated_by_run_id = :r "
        "ORDER BY f.finding_uid COLLATE \"C\", e.evidence_ordinal"
    ), {"r": run_id}).all()
    labels: dict[str, list[str]] = {}
    for finding_uid, page in evidence:
        labels.setdefault(finding_uid, []).append(str(100 + page))
    assert [findings[f"B{row}"] for row in rows] == ["\n".join(value) for value in labels.values()]
    assert [findings[f"A{row}"] for row in rows] == [str(n) for n in range(1, expected + 1)]
    for row in rows:
        assert findings[f"H{row}"] == "" and findings[f"I{row}"] == ""
        assert findings[f"J{row}"] == "не решено"  # the screens' word for ``pending``
        assert findings[f"D{row}"]

    # «Категория» is the screens' label of the stored category, never the contract value.
    stored = session.execute(text(
        "SELECT f.category FROM finding f WHERE f.allocated_by_run_id = :r "
        "ORDER BY f.finding_uid COLLATE \"C\""
    ), {"r": run_id}).scalars().all()
    shown = [findings[f"C{row}"] for row in rows]
    assert shown == [CATEGORY_LABELS[category] for category in stored]
    assert not set(shown) & set(CATEGORY_LABELS)

    # «Сводка»: the run's identity and the counts by category of the same findings.
    summary = _cells(export.content, "xl/worksheets/sheet1.xml")
    assert summary["B2"] == seeded.project_uid and summary["B3"] == seeded.version_uid
    assert summary["B4"] == run_id and summary["B5"] == seeded.analysis_profile_id
    assert summary["B7"] == "ответы модели воспроизведены из записи (recorded)"
    categories = Counter(findings[f"C{row}"] for row in rows)
    counted = {
        summary[f"A{row}"]: int(summary[f"B{row}"])
        for row in range(1, 40)
        if f"A{row}" in summary and summary[f"A{row}"] in categories
    }
    assert counted == dict(categories)

    # The CSV of the same run is untouched by the workbook's existence.
    assert export_run_csv(session, run_id).content.startswith(b"\xef\xbb\xbf")


def test_unknown_and_unfinished_runs_are_refused_as_the_csv_refuses_them(
    session, seeded, blob_store, new_key
) -> None:
    unknown = "run_01M5B0000000000000000000R9"
    with pytest.raises(DomainError) as caught:
        _export(session, blob_store, unknown)
    assert caught.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as csv_caught:
        export_run_csv(session, unknown)
    assert csv_caught.value.code is caught.value.code

    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("w57b-xlsx-unfinished"),
    )
    run_id = str(started.run_id)
    with pytest.raises(DomainError) as caught:
        _export(session, blob_store, run_id)
    assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    with pytest.raises(DomainError) as csv_caught:
        export_run_csv(session, run_id)
    assert csv_caught.value.code is caught.value.code
    assert dict(csv_caught.value.detail_fields) == dict(caught.value.detail_fields)


def test_a_merged_finding_exports_its_canonical_row_and_a_member_row(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    """A v2-shaped finding over the same real run: a canonical observation that proposes a
    severity and a merged member, written as new rows (``finding_observation`` refuses
    UPDATE) and named by the finding, as ``test_v2_csv_severity.py`` writes them. The
    workbook shows the canonical text and proposal, then «также найдено» with the member's
    location and text, both coloured by the canonical severity."""
    from auditmanager.findings import published_findings
    from auditmanager.shared.identity import FindingObservationId

    run_id = _run(session, seeded, blob_store, recorded_adapter, provider_config,
                  new_key("w57b-xlsx-merged"))
    _add_companion(session, blob_store, seeded.version_uid)
    finding = sorted(
        published_findings(session, run_id), key=lambda item: str(item.finding_uid)
    )[0]
    original = str(finding.finding_observation_id)
    canonical = str(FindingObservationId.new())
    member = str(FindingObservationId.new())
    for observation, text_value, severity in (
        (canonical, "Каноническое замечание", "economic"),
        (member, "Замечание участника", "critical"),
    ):
        session.execute(text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, "
            "stage_id, category, finding_text, recommendation_text, grounded, "
            "analysis_profile_id, prompt_bundle_id, provider_mode, proposed_severity) "
            "SELECT :observation, run_id, finding_uid, stage_id, category, :text_value, "
            "recommendation_text, TRUE, analysis_profile_id, prompt_bundle_id, provider_mode, "
            ":severity FROM finding_observation WHERE finding_observation_id = :original"
        ), {"observation": observation, "text_value": text_value, "severity": severity,
            "original": original})
        session.execute(text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
            "page_number, quote, char_start, char_end) "
            "SELECT :observation, 0, page_number, quote, char_start, char_end "
            "FROM finding_evidence WHERE finding_observation_id = :original "
            "ORDER BY evidence_ordinal LIMIT 1"
        ), {"observation": observation, "original": original})
    session.execute(text(
        "UPDATE finding SET canonical_observation_id = :canonical WHERE finding_uid = :finding"
    ), {"canonical": canonical, "finding": str(finding.finding_uid)})
    original_pages = session.execute(text(
        "SELECT page_number FROM finding_evidence WHERE finding_observation_id = :original "
        "ORDER BY evidence_ordinal"
    ), {"original": original}).scalars().all()
    original_text = session.execute(text(
        "SELECT finding_text FROM finding_observation WHERE finding_observation_id = :original"
    ), {"original": original}).scalar_one()

    export = _export(session, blob_store, run_id)
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    styles = {cell.attrib["r"]: cell.attrib["s"] for cell in sheet.iter(f"{MAIN}c")}
    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    # The finding sorts first by identity. Its canonical row comes first, then one
    # «также найдено» row per other observation in identity order: the published v1
    # observation (now a member, the oldest identity) and the new member.
    assert (findings["A2"], findings["D2"], findings["G2"]) == (
        "1", "Каноническое замечание", "Экономическое"
    )
    assert (findings["A3"], findings["B3"], findings["D3"], findings["K3"]) == (
        "", "\n".join(str(100 + page) for page in original_pages), "также найдено",
        original_text,
    )
    assert (findings["A4"], findings["B4"], findings["D4"], findings["K4"]) == (
        "", str(100 + original_pages[0]), "также найдено", "Замечание участника"
    )
    assert findings["A5"] == "2"
    economic = styles["A2"]
    assert economic != "0" and styles["D3"] == styles["D4"] == economic
    # The CSV exports the canonical observation only, as before.
    rows = export_run_csv(session, run_id).content.decode("utf-8-sig")
    assert canonical in rows and member not in rows and original not in rows
