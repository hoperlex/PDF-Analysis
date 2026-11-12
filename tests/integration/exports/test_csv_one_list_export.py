"""A real one-list publisher's canonical block evidence survives the frozen CSV surface."""
import csv
import io

from sqlalchemy.orm import Session

from auditmanager.exports import export_run_csv
from auditmanager.exports.query import export_rows
from auditmanager.findings import published_finding_count
from tests.integration.dashboard.one_list_seed import BLK_A, BLK_B, BLK_C, block_finding, insert_run, text_finding
from tests.integration.db.conftest import (  # noqa: F401
    configured_settings, maintenance_engine, migrated_database, migrated_database_factory, migrated_engine, migrated_template,
)
from tests.integration.documents.seeding import Seeder


def test_csv_keeps_text_drawing_and_cross_source_findings_and_their_exact_locations(migrated_engine):
    with Session(migrated_engine) as session:
        seed = Seeder(session)
        project = seed.project("CSV одного списка")
        version = seed.version(seed.document(project, "Документ"), classified=("R", "AR"))
        run = insert_run(session, project, version, mode="one_list")
        written = text_finding(session, project, version, run)
        drawing = block_finding(session, project, version, run, members=((BLK_A, BLK_C), (BLK_B,)), group_id="drawing")
        mixed = block_finding(session, project, version, run, members=((BLK_C,),), group_id="mixed", other_source_count=1)
        rows = export_rows(session, run)
        assert {row.finding_uid for row in rows} == {written, drawing.finding_uid, mixed.finding_uid}
        assert published_finding_count(session, run) == 3
        assert [row.evidence_page for row in rows if row.finding_uid == drawing.finding_uid] == [2, 3]
        # The merged member is retained by the API/XLSX, never duplicated as another CSV finding.
        assert len([row for row in rows if row.finding_uid == drawing.finding_uid]) == 2
        assert all(row.evidence_quote == "" for row in rows if row.category != "layout")
        assert next(row for row in rows if row.finding_uid == written).evidence_quote == "x"
        content = export_run_csv(session, run).content
        assert content == export_run_csv(session, run).content
        parsed = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
        assert {row["finding_uid"] for row in parsed} == {written, drawing.finding_uid, mixed.finding_uid}
        assert len(parsed) == 4
