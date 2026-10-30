"""Image-only plans traverse every region and stop before unconsented windows."""

import base64
from hashlib import sha256
from types import SimpleNamespace

from auditmanager.comparison.stage_ai.validation import digest
from auditmanager.comparison.work.model import Failed, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.comparison.stage_ai.test_runtime import phase_to_end, scene, uid

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jC3sAAAAASUVORK5CYII=")


class Graphics:
    def __init__(self, left=None, right=None, size=5, evidence_id=None):
        self.raw = {"evidence_id": evidence_id or uid("sge", 1), "content_key": digest(["graphic", size]),
            "left_profile_id": left or uid("cpr", 1), "right_profile_id": right or uid("cpr", 2), "status": "reliable",
            "regions": [{"region_key": f"region-{number:04d}", "region_class": "graphic_changed", "layer": "vector",
                "left_box": [0., 0., 1., 1.], "right_box": [0., 0., 1., 1.],
                "registration": {"reliable": True, "transform": [1, 0, 0, 1, 0, 0]}} for number in range(size)]}
        self.bad_crop = False

    def evidence(self, run_id): return (self.raw,)

    def crop_plan(self, run_id, evidence_id, after=None, limit=4):
        rows = self.raw["regions"]
        start = 0 if after is None else next(index + 1 for index, row in enumerate(rows) if row["region_key"] == after)
        page = rows[start:start + limit]
        return tuple(page), (page[-1]["region_key"] if start + limit < len(rows) else None)

    def crop(self, run_id, evidence_id, region_key, side, long_side_px=1400):
        return SimpleNamespace(evidence_id=evidence_id, region_key=region_key, side=side,
            profile_id=self.raw[side + "_profile_id"], box=(0., 0., 1., 1.), data=PNG,
            sha256="0" * 64 if self.bad_crop else sha256(PNG).hexdigest())


def graphic_scene():
    runtime, item, repo, jobs, caller = scene()
    repo.source["fragments"], repo.source["differences"] = [], []
    runtime._graphics = Graphics()
    jobs.record.consent_no = 1
    caller.transform = lambda _source, answer, _number: answer if "cards" not in answer else answer | {
        "cards": [dict(card, **{"class": "REVIEW", "category": "uncertain", "system": "unknown",
                               "title": "Графические различия"}) for card in answer["cards"]]}
    return runtime, item, repo, jobs, caller


def test_graphic_only_traverses_remainder_after_fresh_consent_and_replays_without_calls():
    runtime, item, repo, jobs, caller = graphic_scene()
    assert phase_to_end(runtime, item, "review")["completed"] == 0
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="classify"), Yielded)
    assert caller.calls == 1 and not repo.answers
    assert len(caller.adapter.requests[0].images_bytes) == 8
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="classify"), Yielded)
    assert jobs.state == "paused" and repo.pauses == ["overrun"] and caller.calls == 1
    progress = next(iter(repo.units.values()))["payload"]
    assert progress["graphic_remaining_regions"] == 1
    jobs.state, jobs.record.consent_no = "running", 2
    assert phase_to_end(runtime, item, "classify")["completed"] == 1
    assert caller.calls == 2 and len(caller.adapter.requests[1].images_bytes) == 2
    assert len(repo.answers) == 1
    answer = next(iter(repo.answers.values()))
    assert answer["cards"][0]["evidence_ids"] == (uid("sge", 1),)
    assert phase_to_end(runtime, item, "synthesize")["completed"] == 1
    assert caller.calls == 3
    assert phase_to_end(runtime, item, "classify")["completed"] == 1 and caller.calls == 3


def test_graphic_crop_mismatch_refuses_before_provider_call():
    runtime, item, repo, jobs, caller = graphic_scene()
    runtime._graphics.bad_crop = True
    outcome = runtime.advance(item, run_id=uid("crn", 1), phase="classify")
    assert isinstance(outcome, Failed) and caller.calls == 0 and not repo.answers


def test_graphic_cursor_cannot_silently_drop_tail():
    runtime, item, repo, jobs, caller = graphic_scene()
    original = runtime._graphics.crop_plan
    runtime._graphics.crop_plan = lambda *args, **kwargs: (original(*args, **kwargs)[0], None)
    outcome = runtime.advance(item, run_id=uid("crn", 1), phase="classify")
    assert isinstance(outcome, Failed) and caller.calls == 0 and not repo.answers


def test_unreliable_graphic_produces_no_ai_proof():
    runtime, item, repo, jobs, caller = graphic_scene()
    runtime._graphics.raw["status"] = "unreliable"
    assert phase_to_end(runtime, item, "classify")["completed"] == 0
    assert caller.calls == 0 and not repo.answers


def test_unavailable_crop_is_explicit_not_checked_without_false_ai_answer():
    runtime, item, repo, jobs, caller = graphic_scene()

    def unavailable(*_args, **_kwargs):
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="stage_graphic_crop")

    runtime._graphics.crop = unavailable
    assert phase_to_end(runtime, item, "classify")["graphic_not_checked"] == 1
    assert phase_to_end(runtime, item, "synthesize")["graphic_not_checked"] == 1
    assert caller.calls == 0 and not repo.answers
