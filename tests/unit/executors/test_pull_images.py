"""The pull image reference and the token-scoped read, without a model or S3."""

from __future__ import annotations

import hashlib
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ModelRequest
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.executors.pull import _task_payload
from auditmanager.executors.runner import RunnerPrincipal, claimed_image
from auditmanager.executors import public as executor_public
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


PNG = b"\x89PNG\r\n\x1a\n" + b"small synthetic payload"
DIGEST = hashlib.sha256(PNG).hexdigest()
IMAGE = {
    "blob_id": str(derive_blob_id(sha256=DIGEST, size=len(PNG))),
    "portal_block_id": "blk_" + "a" * 32,
    "sha256": DIGEST, "size_bytes": len(PNG), "media_type": "image/png",
}


def _request(images: object = ()) -> ModelRequest:
    return ModelRequest(model_id="gpt-6-sol", body={
        "system": "Inspect one drawing crop.",
        "messages": [{"role": "user", "content": "Block blk_" + "a" * 32}],
        "output_config": {"format": {"schema": {"type": "object"}}},
        "images": images,
    })


def test_one_checked_blob_reference_enters_the_task_without_copying_png_bytes() -> None:
    payload = _task_payload(_request([IMAGE]))
    assert payload["images"] == [IMAGE]
    assert PNG not in repr(payload).encode()
    assert "images" not in _task_payload(_request())


@pytest.mark.parametrize("change", [
    {"sha256": "0" * 64}, {"size_bytes": 0}, {"size_bytes": 16 * 1024 * 1024 + 1},
    {"media_type": "application/pdf"}, {"portal_block_id": "../wrong"},
])
def test_invalid_or_oversized_reference_never_creates_a_task(change: dict) -> None:
    with pytest.raises(DomainError):
        _task_payload(_request([{**IMAGE, **change}]))


class FakeRepository:
    def __init__(self) -> None:
        self.task = SimpleNamespace(connection_id="exc_a", state="claimed",
                                    past_deadline=False, claimed_by_token_id="ern_a")
        self.live = True

    def get_task(self, _session, _task_id, *, lock):
        assert lock
        return self.task

    def live_claim_and_attempt(self, _session, _task_id, _token_id):
        return self.live

    def payload_of(self, _session, _task_id):
        return {"images": [IMAGE]}


def test_only_the_current_claimant_can_name_the_image() -> None:
    repository = FakeRepository()
    owner = RunnerPrincipal(token_id="ern_a", connection_id="exc_a")
    assert claimed_image(None, owner, "ext_a", IMAGE["blob_id"], repository) == IMAGE
    with pytest.raises(DomainError):
        claimed_image(None, RunnerPrincipal("ern_b", "exc_b"), "ext_a", IMAGE["blob_id"], repository)
    with pytest.raises(DomainError):
        claimed_image(None, owner, "ext_a", "blob_not_the_image", repository)
    repository.live = False
    with pytest.raises(DomainError):
        claimed_image(None, owner, "ext_a", IMAGE["blob_id"], repository)


class FakeBlobStore:
    def __init__(self, content: bytes = PNG) -> None:
        self.content = content
        self.reads = 0

    def inspect(self, _blob_id):
        return SimpleNamespace(size=len(PNG), sha256=DIGEST, media_type="image/png")

    def open_stream(self, _blob_id, *, expected_sha256, expected_size):
        assert (expected_sha256, expected_size) == (DIGEST, len(PNG))
        self.reads += 1
        yield self.content


def test_server_rechecks_claim_after_blob_read_and_refuses_changed_bytes(monkeypatch) -> None:
    checks = []

    def authorize(_session, _principal, _task_id, _blob_id):
        checks.append(True)
        return IMAGE

    monkeypatch.setattr(executor_public, "claimed_image", authorize)
    store = FakeBlobStore()
    adapter = RunnerAdapter(lambda: nullcontext(None), blob_store=store)
    runner = SimpleNamespace(token_id="ern_a", connection_id="exc_a")
    assert adapter.read_image(runner=runner, task_id="ext_a", blob_id=IMAGE["blob_id"]) == PNG
    assert len(checks) == 2 and store.reads == 1
    store.content = PNG + b"changed"
    with pytest.raises(DomainError):
        adapter.read_image(runner=runner, task_id="ext_a", blob_id=IMAGE["blob_id"])


def test_server_does_not_release_bytes_if_claim_ends_during_blob_read(monkeypatch) -> None:
    checks = 0

    def authorize(_session, _principal, _task_id, _blob_id):
        nonlocal checks
        checks += 1
        if checks == 2:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="claim_lost")
        return IMAGE

    monkeypatch.setattr(executor_public, "claimed_image", authorize)
    store = FakeBlobStore()
    adapter = RunnerAdapter(lambda: nullcontext(None), blob_store=store)
    runner = SimpleNamespace(token_id="ern_a", connection_id="exc_a")
    with pytest.raises(DomainError):
        adapter.read_image(runner=runner, task_id="ext_a", blob_id=IMAGE["blob_id"])
    assert checks == 2 and store.reads == 1
