"""One synthetic page pair through real profile children, engine, C4 evidence and crop tiles."""

import io
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from pypdf import PdfReader, PdfWriter
from sqlalchemy import text

from auditmanager.comparison.stage_graphic import StageGraphicService
from auditmanager.comparison.work.model import Completed
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from tests.integration.comparison.stage_text.test_store import _command, _id
from tests.integration.comparison.stage_review.test_service import _run


def test_real_degree_one_graphic_bridge_and_profile_crop(lane, tmp_path):
    root = Path(__file__).resolve().parents[4]
    project = lane.project()
    versions = []
    for version in (2, 3):
        source = PdfReader(root / "fixtures" / "comparison" / "vs1" / f"v{version}.pdf")
        writer = PdfWriter()
        writer.add_page(source.pages[1])  # corpus E02 V2→V3 adds a real graphic branch
        selected = tmp_path / f"source-v{version}.pdf"
        with selected.open("wb") as output:
            writer.write(output)
        versions.append(lane.seed(selected, 1, project_uid=project))
    pair, revision, actor = _id("stp"), _id("slk"), _id("usr")
    with session_scope(lane.sessions) as session:
        session.execute(text("INSERT INTO app_user(user_uid,login,password_algorithm,password_iterations,password_salt,password_hash) "
            "VALUES(:id,:login,'pbkdf2_sha256',100000,:salt,:hash)"),
            {"id": actor, "login": actor.lower(), "salt": "a" * 32, "hash": "b" * 64})
        docs = [session.execute(text("SELECT document_uid FROM document_version WHERE version_uid=:version"),
                                {"version": v.version_uid}).scalar_one() for v in versions]
        session.execute(text("INSERT INTO stage_pair(stage_pair_id,project_uid,left_document_uid,right_document_uid,state,"
            "confirmed_by_user_uid,confirmed_at,command_id) VALUES(:pair,:project,:left,:right,'confirmed',:actor,"
            "clock_timestamp(),:command)"), {"pair": pair, "project": project, "left": docs[0], "right": docs[1],
            "actor": actor, "command": _command(session, "confirm_stage_pair")})
        session.execute(text("INSERT INTO stage_link_revision(stage_link_revision_id,stage_pair_id,revision_no,source,"
            "input_sha256,actor_user_uid,command_id) VALUES(:id,:pair,1,'expert',:sha,:actor,:command)"),
            {"id": revision, "pair": pair, "sha": "e" * 64, "actor": actor,
             "command": _command(session, "apply_stage_sheet_map")})
        session.execute(text("INSERT INTO stage_link_item(stage_link_item_id,stage_link_revision_id,row_no,left_profile_id,"
            "right_profile_id,relation,confidence) VALUES(:id,:revision,1,:left,:right,'paired','manual')"),
            {"id": _id("sli"), "revision": revision, "left": versions[0].pages[1], "right": versions[1].pages[1]})
    with session_scope(lane.sessions) as session:
        run, item = _run(session, SimpleNamespace(_sessions=lane.sessions), pair, revision, actor)
    service = StageGraphicService(lane.sessions, blob_store=lane.blob_store)
    counts = service.advance(item, run)
    assert counts["graphic_reliable"] == 1 and counts["graphic_regions"] >= 1
    evidence = service.evidence(run)
    assert len(evidence) == 1
    assert any(r["region_class"] == "graphic_added" for r in evidence[0]["regions"])
    assert all(r["registration"]["reliable"] and r["registration"]["result_id"].startswith("csp_")
               for r in evidence[0]["regions"])
    plans, after = service.crop_plan(run, evidence[0]["evidence_id"])
    assert plans
    for side in ("left", "right"):
        crop = service.crop(run, evidence[0]["evidence_id"], plans[0]["region_key"], side)
        image = Image.open(io.BytesIO(crop.data))
        assert min(image.size) > 0 and max(image.size) <= 1400
    class NoChild:
        def run(self, settings, limits):
            raise AssertionError("completed stage receipt must not rerun the engine")
    assert StageGraphicService(lane.sessions, blob_store=lane.blob_store, runner=NoChild()).advance(item, run) == counts
    with session_scope(lane.sessions) as session:
        ComparisonWorkRepository().finish(session, item.authority, Completed())
