"""`CTX-STAND`: the claim carries the descriptor the adapter wrote, and only that.

``_claimed`` turns a claimed row into the task a runner receives. ``context_request`` is the payload's, re-read in the contract's shape
(``{input_id, text_sha256, section}``); a payload without one, or with one that is not exactly that shape, gives a task that is never offered reference
data. Nothing else of the task changes: the host members and the images are as they were.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from auditmanager.executors.runner import ClaimedTask, _claimed
from auditmanager.executors.runner_repository import ClaimedRow

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
SHA = "d" * 64
HOST = {"provider": "claude_code", "access": "subscription", "model_id": "m", "effort": "medium", "timeout_seconds": 600, "cell_key": "review:main"}


def claimed(**payload: Any) -> ClaimedTask:
    base = {"system": "s", "user_text": "u", "output_schema": {"type": "object"}}
    return _claimed(ClaimedRow("ext_T", NOW, NOW, "m", {**base, **payload}))


def test_the_descriptor_of_the_payload_is_the_claims_in_the_contracts_shape() -> None:
    entries = [{"input_id": "xri_1", "text_sha256": SHA, "section": "AR"}, {"input_id": "xri_2", "text_sha256": SHA, "section": "AR"}]
    task = claimed(host=HOST, context_request=entries)
    assert [dict(entry) for entry in task.context_request] == entries and task.cell_key == "review:main"


def test_a_task_without_a_descriptor_has_none_and_is_otherwise_what_it_was() -> None:
    task = claimed(host=HOST)
    assert task.context_request == () and (task.provider, task.model_id, task.cell_key) == ("claude_code", "m", "review:main")
    assert claimed().context_request == () and claimed(images=[]).images == ()


def test_a_descriptor_that_is_not_exactly_the_contracts_shape_is_not_carried() -> None:
    for bad in ([], [{"input_id": "a"}], [{"input_id": "a", "text_sha256": "x", "section": "AR"}], "a", {"input_id": "a"},
                [{"input_id": "a", "text_sha256": SHA, "section": "AR", "extra": 1}]):
        assert claimed(host=HOST, context_request=bad).context_request == (), bad
