"""Real C4 receipts and source scopes; a separate small smoke runs the actual PDF engine."""

from dataclasses import replace
import io

import pytest
from PIL import Image
from sqlalchemy import text

from auditmanager.comparison.engine import PairResultRepository
from auditmanager.api.schemas.models import StageGraphicEvidence
from auditmanager.comparison.engine.key import content_key
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.stage_graphic import StageGraphicService
from auditmanager.comparison.work.model import Yielded
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError
from tests.integration.comparison.stage_text.test_store import _seed, _id
from tests.integration.comparison.stage_review.test_service import _run


def _state(session):
    store, pair, revision, actor, left, right = _seed(session)
    run, item = _run(session, store, pair, revision, actor)
    return store, run, item, revision, left, right


def test_many_to_many_is_durable_not_checked_one_link_per_advance_and_foreign_is_refused(comparison_session):
    store, run, item, revision, left, right = _state(comparison_session)
    comparison_session.execute(text("INSERT INTO stage_link_item(stage_link_item_id,stage_link_revision_id,row_no,"
        "left_profile_id,right_profile_id,relation,confidence) VALUES(:id,:revision,2,:left,:right,'paired','manual')"),
        {"id": _id("sli"), "revision": revision, "left": left, "right": right})
    service = StageGraphicService(store._sessions, blob_store=None)
    with pytest.raises(DomainError):
        service.advance(replace(item, project_uid=_id("prj")), run)
    assert isinstance(service.advance(item, run), Yielded)
    assert comparison_session.execute(text("SELECT count(*) FROM stage_graphic_evidence WHERE stage_chain_run_id=:run"), {"run": run}).scalar_one() == 1
    result = service.advance(item, run)
    assert result["graphic_not_checked"] == 2 and result["graphic_regions"] == 0
    assert service.advance(item, run) == result and service.evidence(run) == ()
    rows, after = service.page(run, limit=1)
    assert len(rows) == 1 and after is not None
    StageGraphicEvidence.model_validate(rows[0])
    assert service.page(run, after=after, limit=1)[1] is None


def test_reliable_real_result_reference_replay_and_native_crops(comparison_session, monkeypatch):
    store, run, item, revision, left, right = _state(comparison_session)
    # Immutable profiles are inserted with their dimensions in a separate fresh fixture.
    # The fixture's empty summaries cannot be updated, so project_result is exercised
    # below with a completed engine result and a size projection injected at its seam.
    reader = PageProfileReader(store._sessions, None)
    with session_scope(store._sessions) as opened:
        project = opened.execute(text("SELECT project_uid FROM stage_pair WHERE stage_pair_id=(SELECT stage_pair_id "
            "FROM stage_chain_run WHERE stage_chain_run_id=:run)"), {"run": run}).scalar_one()
        result_id = PairResultRepository().insert(opened, project_uid=project,
            content_key=content_key(project, reader.get_profile(left), reader.get_profile(right)),
            algo_version="cmp-engine/1", status="different", reasons=[], mask_blob_id=None,
            page_a_profile_id=left, page_b_profile_id=right,
            channels={"geometry": {"state": "checked", "diffs": 1}, "color": {"state": "checked", "diffs": 0}},
            result={"how_compared": {"transform": [1, 0, 0, 1, 10, 20], "dpi": 200},
                    "differences": [{"region_class": "graphic_changed", "layer": "main", "box": {"x": 50, "y": 60, "width": 20, "height": 30}}]})
    from auditmanager.comparison.stage_graphic import service as module
    from auditmanager.comparison.stage_graphic.evidence import project_result
    monkeypatch.setattr(module, "project_result", lambda stored, **kwargs: project_result(stored, left_size=(200, 200), right_size=(200, 200)))
    calls = []
    def engine(*args, **kwargs):
        calls.append(kwargs)
        from types import SimpleNamespace
        return SimpleNamespace(result_id=result_id)
    monkeypatch.setattr(module, "compare_sheet_pair", engine)
    png = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(png, format="PNG")
    crops = []
    class Material:
        def crop(self, profile, box, **kwargs):
            crops.append((profile, box))
            return png.getvalue()
    service = StageGraphicService(store._sessions, blob_store=None, material=Material())
    assert service.advance(item, run)["graphic_reliable"] == 1
    assert service.advance(item, run)["graphic_regions"] == 1 and len(calls) == 1
    evidence = service.evidence(run)[0]
    StageGraphicEvidence.model_validate(service.page(run)[0][0])
    plan, cursor = service.crop_plan(run, evidence["evidence_id"])
    assert cursor is None and len(plan) == 1
    image = service.crop(run, evidence["evidence_id"], plan[0]["region_key"], "right")
    assert image.profile_id == right and image.box == (40, 40, 60, 70)
    assert image.data == png.getvalue() and crops == [(right, (40, 40, 60, 70))]
    with pytest.raises(DomainError):
        service.crop(run, evidence["evidence_id"], "invented", "right")
    with pytest.raises(DomainError):
        service.crop_plan(_id("crn"), evidence["evidence_id"])
