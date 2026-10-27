"""AR-V3-JUDGE-FIXES-01 finding 2: a published AR v3 beta Run's workbook, over a real database.

The Runs are the six of ``tests/integration/runs/test_v3_decisions_over_http.py`` (the stock recorded
composition, a sealed synthetic pack, driven to ``published`` on a private database migrated to head;
that module's own ``world`` fixture is reused unedited). F1, F2 and A1 each publish one provisional
finding with one certified citation; A2, S1 and S2 publish none.

What this proves, and what it does not:

* the workbook's use case, handed the composition root's citation reader
  (``bootstrap.adapters._read_citations_for_export``), reads the Run's certified citations through the
  ``ar_v3_citation_review`` stage and puts them in the «Норма» columns;
* the reader the adapter used before (``read_verified_citations`` with its default stage
  ``norm_verification``) does not certify a v3 Run, so the use case refused with
  ``required_norm_unavailable`` (the defect);
* the workbook has no column for, and no cell equal to, the model's claimed ``required_value`` /
  ``stated_value``, which stay unserved;
* a version without a verified portal companion is still refused, typed, as for every other Run
  (``storage_integrity_error``, role ``source.structured_companion``): the synthetic Runs' bare PDF has
  none, so the companion is added the only way the schema allows (an ``INSERT`` into
  ``input_manifest_entry``) inside a transaction that is rolled back.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
from auditmanager.bootstrap.adapters import _read_citations_for_export
from auditmanager.exports import ExportAuthorization, export_run_xlsx
from auditmanager.exports.xlsx.writer import FINDING_COLUMNS
from auditmanager.findings.citation_reader import read_verified_citations
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_id, parse_blob_role

RUNS = Path(__file__).resolve().parents[1] / "runs"
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
PAGES = 8  # the baseline PDF the synthetic Runs read


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # before execution: ``@dataclass(slots=True)`` resolves through it
    spec.loader.exec_module(module)
    return module


decisions = _load("ar_v3_decisions_http_helpers", "test_v3_decisions_over_http.py")
accept = decisions.accept
#: The decisions module's module-scoped fixtures, bound here so pytest registers them for this module.
world = decisions.world
probe_database = decisions.probe_database


@pytest.fixture
def session(probe_database: str, world: Any) -> Iterator[Session]:
    """One read transaction on the private database; everything a test adds is rolled back."""
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(probe_database)))
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as opened:
        try:
            yield opened
        finally:
            opened.rollback()
    engine.dispose()


def _authorization(run_id: str) -> ExportAuthorization:
    return ExportAuthorization(
        run_id=run_id, principal_id="usr_01M5B0000000000000000000U1",
        operation="exportRunXlsx", decision="allow", decision_ref="role-register:exportRunXlsx",
    )


def _export(session: Session, blob_store: Any, run_id: str, reader: Any):
    return export_run_xlsx(
        session, run_id, authorization=_authorization(run_id),
        read_blob=lambda blob_id: blob_store.read(parse_blob_id(blob_id)), read_citations=reader,
    )


def _add_companion(session: Session, blob_store: Any, version_uid: str) -> None:
    document = {
        "schema_version": 1, "coordinate_space": "normalized_page_top_left",
        "pages": [{"page_index": i, "width_px": 2480, "height_px": 3508, "rotation": 0}
                  for i in range(PAGES)],
        "blocks": [{"block_id": f"blk_{i + 1:032x}", "page_index": i, "page_label": 101 + i,
                    "ordinal": 0, "block_type": "text", "status": "ok",
                    "coords_norm": [0.1, 0.1, 0.9, 0.9]} for i in range(PAGES)],
    }
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
    published = blob_store.put_blob(
        payload, declared_sha256=sha256_of(payload), declared_size=len(payload),
        role=parse_blob_role("source_structured_companion"), media_type="application/json",
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(
        blob_id=published.blob_id, upload_token="ar-v3-judge-fixes-xlsx", sha256=published.sha256,
        size=published.size, role=published.role, media_type=published.media_type,
    ))
    blobs.mark_available(session, published.blob_id)
    session.execute(text(
        "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, "
        "media_type) VALUES (:version, 'source.structured_companion', :blob, :sha, :size, "
        "'application/json')"
    ), {"version": version_uid, "blob": str(published.blob_id), "sha": published.sha256,
        "size": published.size})


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


def test_the_runs_are_published_and_f1_holds_one_certified_citation(world: Any, session: Session) -> None:
    run_id = world.run_of["F1"]
    assert session.execute(text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run_id}).scalar_one() == "published"
    assert session.execute(text(
        "SELECT count(*) FROM finding_observation_norm_citation WHERE run_id = :r"), {"r": run_id}).scalar_one() == 1
    assert session.execute(text(
        "SELECT count(*) FROM stage_result WHERE run_id = :r AND stage_id = 'ar_v3_citation_review' "
        "AND status = 'succeeded'"), {"r": run_id}).scalar_one() == 1
    assert session.execute(text(
        "SELECT count(*) FROM stage_result WHERE run_id = :r AND stage_id = 'norm_verification'"),
        {"r": run_id}).scalar_one() == 0


@pytest.mark.parametrize("scope", decisions.PROVISIONAL_SCOPES)
def test_a_published_v3_run_exports_its_certified_citation_in_the_norm_columns(
    world: Any, session: Session, blob_store: Any, scope: str
) -> None:
    run_id = world.run_of[scope]
    _add_companion(session, blob_store, world.version_uid)
    export = _export(session, blob_store, run_id, _read_citations_for_export)
    assert export.run_state == "published"
    set_id = world.set_of[scope]
    assert export.citation_source_ref == f"{run_id}:{world.snapshot_id}:{set_id}"
    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    assert tuple(findings[f"{column}1"] for column in "ABCDEFGHIJK") == FINDING_COLUMNS
    rows = sorted({int(address[1:]) for address in findings if address[0] == "A"} - {1})
    assert rows == [2]
    # the norm columns carry the certified citation: designation and clause, then the exact quote
    assert findings["I2"] == accept.NORM_QUOTE
    assert findings["H2"] and findings["H2"] != findings["I2"]
    (partition,) = _read_citations_for_export(
        session, run_id=run_id, version_uid=world.version_uid, profile_id=str(AR_V3_BETA_PROFILE_ID),
    ).findings
    (citation,) = partition.canonical.citations
    assert citation.designation
    expected = (f"{citation.designation}, {citation.clause_number}"
                if citation.clause_number else citation.designation)
    assert findings["H2"] == expected  # the synthetic paragraph has no clause number
    assert export.content == _export(session, blob_store, run_id, _read_citations_for_export).content


@pytest.mark.parametrize("scope", decisions.PROVISIONAL_SCOPES)
def test_the_workbook_carries_neither_claimed_number_in_any_cell(
    world: Any, session: Session, blob_store: Any, scope: str
) -> None:
    """The model's text is served; its claimed ``required_value`` / ``stated_value`` are not."""
    run_id = world.run_of[scope]
    _add_companion(session, blob_store, world.version_uid)
    export = _export(session, blob_store, run_id, _read_citations_for_export)
    required, stated = session.execute(text(
        "SELECT required_value, stated_value FROM finding_observation WHERE run_id = :r"), {"r": run_id}).one()
    assert required and stated and required != stated
    every_cell = [value for part in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml")
                  for value in _cells(export.content, part).values()]
    assert required not in every_cell and stated not in every_cell
    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    assert not {"required_value", "stated_value"} & set(findings.values())
    assert len(FINDING_COLUMNS) == 11 and not any("required" in c or "stated" in c for c in FINDING_COLUMNS)


@pytest.mark.parametrize("scope", decisions.WITHHELD_SCOPES)
def test_a_published_v3_run_with_no_finding_exports_an_empty_findings_sheet(
    world: Any, session: Session, blob_store: Any, scope: str
) -> None:
    run_id = world.run_of[scope]
    _add_companion(session, blob_store, world.version_uid)
    export = _export(session, blob_store, run_id, _read_citations_for_export)
    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    assert tuple(findings[f"{column}1"] for column in "ABCDEFGHIJK") == FINDING_COLUMNS
    assert {int(address[1:]) for address in findings if address[0] == "A"} == {1}
    assert export.citation_source_ref == f"{run_id}:{world.snapshot_id}:{world.set_of[scope]}"


def test_the_reader_with_the_v1_v2_stage_does_not_certify_a_v3_run_and_the_export_is_closed(
    world: Any, session: Session, blob_store: Any
) -> None:
    """The defect, at the database: what the adapter handed the use case before this fix."""
    run_id = world.run_of["F1"]
    _add_companion(session, blob_store, world.version_uid)
    with pytest.raises(DomainError) as caught:
        _export(session, blob_store, run_id, read_verified_citations)
    assert caught.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
    assert dict(caught.value.detail_fields)["reference_kind"] == "norm_retrieval_set"


def test_without_a_verified_portal_companion_the_v3_export_is_still_refused_and_typed(
    world: Any, session: Session, blob_store: Any
) -> None:
    """What remains: the XLSX labels sheets from the version's portal companion for every Run."""
    with pytest.raises(DomainError) as caught:
        _export(session, blob_store, world.run_of["F1"], _read_citations_for_export)
    assert caught.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert dict(caught.value.detail_fields) == {"role": "source.structured_companion"}
