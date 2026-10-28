"""`CMP-EXEC-IMAGES-01` (ADR-0025 decision 18): the server never hands a task to a claim that serves fewer images.

Real rows, the served application, the real authorization seam and the real claim statements. The
runner speaks to ``build_router(runner=RunnerAdapter(...))`` exactly as the pull tests do. Nothing
calls a model. The claim's ``max_images`` is the only thing that decides what a runner is offered;
an absent value is the shape every runner deployed before several images sends, and means one.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors.image_input import CropImage, attach_images
from auditmanager.executors.public import current_revision
from auditmanager.executors.runner_repository import RunnerRepository
from tests.integration.executors.test_runner_channel import (  # noqa: F401 - the fixtures
    GOOD,
    MODEL,
    SCHEMA,
    adapter_for,
    claim,
    issue,
    live_attempt,
    make_connection,
    play,
    runner_call,
    surface,
    task_row,
)
from tests.unit.executors.crop_support import crop, descriptor, png


def _claim(surface: Any, token: str, **declared: Any):
    return runner_call(surface, token, "/runner/tasks/claim", {"wait_seconds": 0, **declared})


def _write(session: Session, connection_id: str, attempt: dict[str, str], images: Any = None,
           *, deadline: float = 600, **payload: Any) -> str:
    """One open task whose payload carries ``images`` (a list, or whatever the test wants)."""
    revision = current_revision(session, connection_id)
    assert revision is not None
    body: dict[str, Any] = {"system": "S", "user_text": "U", "output_schema": SCHEMA, **payload}
    if images is not None:
        body["images"] = images
    task = RunnerRepository().insert_task(
        session, connection_id=connection_id, revision_id=revision.revision_id, origin="run_call",
        run_id=attempt["run_id"], attempt_id=attempt["attempt_id"], model_call_id=None,
        probe_id=None, expected_model=MODEL, payload=body, deadline_seconds=deadline)
    return task.task_id


def _crops(count: int, prefix: str = "q") -> list[dict[str, Any]]:
    return [descriptor(png(f"{prefix}{index}"), crop_id=f"crop-{prefix}-{index}") for index in range(count)]


def _state(session: Session, task_id: str) -> tuple[str, int]:
    row = task_row(session, task_id)
    return row["state"], row["claim_count"]


@pytest.fixture
def stand(session: Session, surface):
    connection_id = make_connection(surface)
    return connection_id, live_attempt(session)


# -- the old shape: the case the ADR names -------------------------------------------------------


def test_an_old_shape_claim_is_offered_no_multi_image_task(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    wide = _write(session, connection_id, attempt, _crops(3))
    widest = _write(session, connection_id, attempt, _crops(8, "w"))
    for old_shape in ({"wait_seconds": 0}, {"wait_seconds": 0, "max_images": 1}):
        answer = runner_call(surface, token, "/runner/tasks/claim", old_shape)
        assert answer.status == 204, answer.body
    assert _state(session, wide) == ("open", 0) and _state(session, widest) == ("open", 0), \
        "the task was never claimed, so no runner ever held it"


def test_a_claim_with_a_smaller_count_than_the_task_is_offered_nothing(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    wide = _write(session, connection_id, attempt, _crops(5))
    for declared in (1, 2, 4):
        assert _claim(surface, token, max_images=declared).status == 204
    assert _state(session, wide) == ("open", 0)
    served = _claim(surface, token, max_images=5)
    assert served.status == 200 and served.json()["task_id"] == wide
    assert _state(session, wide) == ("claimed", 1)


def test_the_task_arrives_whole_with_its_crop_references_in_their_order(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    images = _crops(4)
    task_id = _write(session, connection_id, attempt, images)
    answer = _claim(surface, token, max_images=4)
    assert answer.status == 200, answer.body
    document = answer.json()
    assert document["task_id"] == task_id and document["images"] == images
    assert [item["crop_id"] for item in document["images"]] == [f"crop-q-{index}" for index in range(4)]
    assert all("portal_block_id" not in item for item in document["images"]), \
        "a comparison crop is addressed by its opaque reference alone"


def test_the_one_image_portal_block_path_is_unchanged_for_an_old_shape_claim(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    block = descriptor(png("block"), portal_block_id="blk_" + "a" * 32)
    task_id = _write(session, connection_id, attempt, [block])
    document = _claim(surface, token).json()
    assert document["task_id"] == task_id and document["images"] == [block]
    text_only = _write(session, connection_id, attempt, None)
    second, _ = issue(surface, connection_id)
    assert _claim(surface, second).json()["task_id"] == text_only, "a text task needs no declaration at all"


# -- order: a task too wide for a claim is skipped, never waited on ------------------------------


def test_a_task_too_wide_for_the_claim_does_not_block_the_tasks_behind_it(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    wide = _write(session, connection_id, attempt, _crops(3))
    narrow = _write(session, connection_id, attempt, [_crops(1, "n")[0]])
    first = _claim(surface, token, max_images=2)
    assert first.status == 200 and first.json()["task_id"] == narrow
    assert _state(session, wide) == ("open", 0), "the older, wider task stays open for a runner that serves it"
    other, _ = issue(surface, connection_id)
    assert _claim(surface, other, max_images=3).json()["task_id"] == wide


def test_the_oldest_task_that_fits_is_served_first(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    older = _write(session, connection_id, attempt, _crops(2))
    _write(session, connection_id, attempt, _crops(1, "y"))
    assert _claim(surface, token, max_images=8).json()["task_id"] == older


# -- redelivery: the same rule for the claim a token already holds -------------------------------


def test_a_held_claim_is_not_handed_again_to_a_claim_that_serves_fewer_images(session, surface, stand) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    wide = _write(session, connection_id, attempt, _crops(3))
    assert _claim(surface, token, max_images=3).json()["task_id"] == wide
    again = _claim(surface, token, max_images=3)
    assert again.status == 200 and again.json()["task_id"] == wide, "a runner that kept its count is given its task again"
    for declared in ({}, {"max_images": 2}):
        refused = _claim(surface, token, **declared)
        assert refused.status == 204, "the lease is refreshed for nobody: it is not handed to a narrower claim"
    assert _state(session, wide) == ("claimed", 1), "and it is not claimed a second time"
    session.execute(text("UPDATE executor_task SET claim_expires_at = clock_timestamp() - interval '1 second' "
                         "WHERE task_id = :id"), {"id": wide})
    assert _claim(surface, token, max_images=2).status == 204
    assert _state(session, wide)[0] == "open", "the lapsed lease returned it to open; still not for two"


# -- a payload that is not what the writer wrote -------------------------------------------------


@pytest.mark.parametrize("malformed", [{"x": 1}, "text", 3, None])
def test_a_payload_whose_images_member_is_not_a_list_is_never_handed_out(
    session, surface, stand, malformed: Any,
) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    task_id = _write(session, connection_id, attempt, None)
    session.execute(text("UPDATE executor_task SET payload = jsonb_set(payload, '{images}', "
                         "CAST(:value AS jsonb)) WHERE task_id = :id"),
                    {"id": task_id, "value": json.dumps(malformed)})
    assert _claim(surface, token, max_images=8).status == 204
    assert _state(session, task_id) == ("open", 0)


# -- the wire ------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [0, 9, -1, 1.5, None])
def test_max_images_outside_the_contract_is_refused_and_claims_nothing(session, surface, stand, bad: Any) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)
    task_id = _write(session, connection_id, attempt, [_crops(1)[0]])
    answer = runner_call(surface, token, "/runner/tasks/claim", {"wait_seconds": 0, "max_images": bad})
    assert answer.status == 422, answer.body
    assert _state(session, task_id) == ("open", 0)


# -- the worker's side to the runner's, end to end -----------------------------------------------


def _request(crops: list[CropImage]) -> ModelRequest:
    return attach_images(ModelRequest(model_id=MODEL, body={
        "model": MODEL, "max_tokens": 16, "system": "SYSTEM-PROMPT",
        "messages": [{"role": "user", "content": "compare these crops"}],
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
    }), crops)


def test_a_comparison_request_reaches_a_runner_that_declared_enough_and_is_answered(
    session, surface, stand, monkeypatch,
) -> None:
    connection_id, attempt = stand
    wide_token, _ = issue(surface, connection_id)
    old_token, _ = issue(surface, connection_id)
    crops = [crop(label) for label in ("a1", "b1", "a2")]
    seen: dict[str, Any] = {}

    def runner() -> None:
        old = runner_call(surface, old_token, "/runner/tasks/claim", {"wait_seconds": 0})
        seen["old"] = old.status
        taken = _claim(surface, wide_token, max_images=8)
        assert taken.status == 200, taken.body
        seen["task"] = taken.json()
        answered = runner_call(surface, wide_token, f"/runner/tasks/{taken.json()['task_id']}/answer",
                               {"output_text": GOOD, "model": MODEL})
        assert answered.status == 200

    play(monkeypatch, runner)
    response = adapter_for(session, connection_id, attempt).complete(_request(crops))
    assert response.output_text == GOOD
    assert seen["old"] == 204, "the runner of the old shape was offered nothing while the task was open"
    assert [item["crop_id"] for item in seen["task"]["images"]] == [item.crop_id for item in crops]
    assert [item["size_bytes"] for item in seen["task"]["images"]] == [len(item.data) for item in crops]


def test_a_runner_that_refuses_the_images_ends_the_call_without_an_answer(
    session, surface, stand, monkeypatch,
) -> None:
    connection_id, attempt = stand
    token, _ = issue(surface, connection_id)

    def runner() -> None:
        taken = _claim(surface, token, max_images=8)
        failed = runner_call(surface, token, f"/runner/tasks/{taken.json()['task_id']}/fail",
                             {"reason": "image_input_unsupported: this session sees one image"})
        assert failed.status == 200

    play(monkeypatch, runner)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter_for(session, connection_id, attempt).complete(_request([crop("a"), crop("b")]))
    assert raised.value.detail_fields == {"dependency": "executor_image_input_unsupported"}
    assert task_row(session)["state"] == "failed" and task_row(session)["answer_text"] is None


def test_a_request_beyond_the_limits_never_becomes_a_task(session, surface, stand) -> None:
    connection_id, attempt = stand
    nine = ModelRequest(model_id=MODEL, body={
        "model": MODEL, "system": "S", "messages": [{"role": "user", "content": "u"}],
        "images": _crops(9)})
    before = session.execute(text("SELECT count(*) FROM executor_task")).scalar_one()
    with pytest.raises(ProxyDispatchError) as raised:
        adapter_for(session, connection_id, attempt).complete(nine)
    assert raised.value.dispatch_class == "not_sent"
    assert session.execute(text("SELECT count(*) FROM executor_task")).scalar_one() == before
