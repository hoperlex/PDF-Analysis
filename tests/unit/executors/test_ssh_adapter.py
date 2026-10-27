from __future__ import annotations

import base64
import hashlib
import json
import struct
from datetime import datetime, timezone

import pytest

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.kinds import adapter_for
from auditmanager.executors.model import RevisionRecord, RevisionSettings
from auditmanager.executors.ssh_adapter import SshCommandAdapter, _task
from auditmanager.executors.ssh_probe import probe_ssh_command
from auditmanager.storage.public import derive_blob_id

PNG = b"\x89PNG\r\n\x1a\n" + b"crop"
DIGEST = hashlib.sha256(PNG).hexdigest()
HOST_KEY = "ssh-ed25519 " + base64.b64encode(struct.pack(">I", 11) + b"ssh-ed25519" + b"key").decode()
POLICY = DestinationPolicy(resolver=lambda host, port: ["8.8.8.8"], networks=lambda: ())


def revision(host_key: str | None = HOST_KEY) -> RevisionRecord:
    return RevisionRecord(
        revision_id="excr_1", connection_id="exc_1", revision_no=1,
        created_at=datetime.now(timezone.utc), created_by="usr_1",
        settings=RevisionSettings(
            pin_id="claude-opus-5", gateway_model="claude-opus-5", billing="metered",
            allow_client_documents=True, timeout_seconds=100, ssh_host="example.com", ssh_port=22,
            ssh_user="runner", host_key=host_key, ssh_profile="custom_command",
        ),
    )


def request(image: bytes | None = PNG) -> ModelRequest:
    images = [] if image is None else [{
        "blob_id": str(derive_blob_id(sha256=DIGEST, size=len(PNG))),
        "portal_block_id": "blk_" + "a" * 32, "sha256": DIGEST,
        "size_bytes": len(PNG), "media_type": "image/png",
    }]
    return ModelRequest(
        model_id="claude-opus-5", image_bytes=image,
        body={"system": "system", "messages": [{"role": "user", "content": "describe"}],
              "max_tokens": 64, "images": images},
    )


def answer(model: str = "claude-opus-5") -> bytes:
    return json.dumps({"model": model, "output_text": "ok", "stop_reason": "end_turn",
                       "input_tokens": 3, "output_tokens": 1}).encode()


def test_one_verified_png_is_in_ssh_stdin_and_checked_ip_is_dialed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, dict]] = []

    def fake_run(endpoint, key, host_key, payload, **kwargs):
        seen.append((endpoint.host, json.loads(payload)))
        assert host_key == HOST_KEY and key == "private"
        return answer(), ""

    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command", fake_run)
    result = SshCommandAdapter(revision(), "private", POLICY, None).complete(request())
    assert result.model == "claude-opus-5" and result.output_text == "ok"
    assert seen[0][0] == "8.8.8.8"
    image = seen[0][1]["image"]
    assert image["media_type"] == "image/png"
    assert base64.b64decode(image["data"]) == PNG


def test_changed_crop_is_refused_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command",
                        lambda *args, **kwargs: pytest.fail("ssh must not run"))
    with pytest.raises(ProxyDispatchError) as error:
        SshCommandAdapter(revision(), "private", POLICY, None).complete(request(PNG + b"changed"))
    assert error.value.dispatch_class == "not_sent"


def test_probe_shows_key_before_call_and_rejects_changed_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auditmanager.executors.ssh_probe.scan_host_key", lambda *args, **kwargs: HOST_KEY)
    monkeypatch.setattr("auditmanager.executors.ssh_probe.run_command",
                        lambda *args, **kwargs: pytest.fail("ssh must not run"))
    first = probe_ssh_command(revision(None).settings, "private", policy=POLICY)
    assert first.outcome == "host_key_unpinned" and first.observed_host_key == HOST_KEY
    changed = probe_ssh_command(revision("ssh-ed25519 " + base64.b64encode(
        struct.pack(">I", 11) + b"ssh-ed25519" + b"other").decode()).settings,
        "private", policy=POLICY)
    assert changed.outcome == "host_key_changed" and changed.observed_host_key == HOST_KEY


def test_probe_requires_reported_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auditmanager.executors.ssh_probe.scan_host_key", lambda *args, **kwargs: HOST_KEY)
    monkeypatch.setattr("auditmanager.executors.ssh_probe.run_command",
                        lambda *args, **kwargs: (answer("another-model"), ""))
    result = probe_ssh_command(revision().settings, "private", policy=POLICY)
    assert result.outcome == "model_mismatch" and result.reported_model == "another-model"
    assert result.identity_basis == "reported"


def test_registry_exposes_ssh_command_with_private_key() -> None:
    entry = adapter_for("ssh_command")
    assert entry is not None and entry.purpose == "ssh_private_key" and entry.serves(revision())


def test_task_envelope_has_no_image_when_none() -> None:
    assert "image" not in json.loads(_task(request(None), "claude-opus-5"))


# -- several images, `CMP-EXEC-IMAGES-01` --------------------------------------------------------

from auditmanager.executors.image_input import attach_images  # noqa: E402
from auditmanager.executors.ssh_adapter import MAX_MULTI_IMAGE_TASK_BYTES, MAX_TASK_BYTES  # noqa: E402
from tests.unit.executors.crop_support import crop  # noqa: E402

PLAIN = ModelRequest(model_id="claude-opus-5", body={
    "system": "system", "messages": [{"role": "user", "content": "describe"}], "max_tokens": 64})


def test_one_image_keeps_the_envelope_an_older_forced_command_reads() -> None:
    task = json.loads(_task(request(), "claude-opus-5"))
    assert set(task["image"]) == {"media_type", "data"}, "an object, as before"
    single = json.loads(_task(attach_images(PLAIN, [crop("a")]), "claude-opus-5"))
    assert isinstance(single["image"], dict) and base64.b64decode(single["image"]["data"]) == crop("a").data


def test_several_images_are_a_list_in_the_same_member_in_order() -> None:
    crops = [crop(label) for label in "abc"]
    task = json.loads(_task(attach_images(PLAIN, crops), "claude-opus-5"))
    assert isinstance(task["image"], list), "a list under `image`, which an older command refuses"
    assert "images" not in task
    assert [base64.b64decode(item["data"]) for item in task["image"]] == [item.data for item in crops]
    assert all(set(item) == {"media_type", "data"} for item in task["image"])


def test_several_images_may_exceed_the_size_of_one_but_not_the_multi_image_limit() -> None:
    assert MAX_MULTI_IMAGE_TASK_BYTES > MAX_TASK_BYTES
    big = [crop(str(index), pad=(9 << 20)) for index in range(3)]  # about 36 MiB as base64
    assert MAX_TASK_BYTES < len(_task(attach_images(PLAIN, big), "claude-opus-5")) <= MAX_MULTI_IMAGE_TASK_BYTES
    # a text so large that eight images and the text do not fit is refused before the network
    huge_text = ModelRequest(model_id="claude-opus-5", body={
        **PLAIN.body, "messages": [{"role": "user", "content": "x" * MAX_MULTI_IMAGE_TASK_BYTES}]})
    with pytest.raises(ProxyDispatchError):
        _task(attach_images(huge_text, [crop("a"), crop("b")]), "claude-opus-5")


def test_several_images_reach_the_command_and_a_bad_list_never_runs_ssh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict] = []

    def fake_run(endpoint, key, host_key, payload, **kwargs):
        seen.append(json.loads(payload))
        return answer(), ""

    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command", fake_run)
    crops = [crop(label) for label in "ab"]
    built = attach_images(PLAIN, crops)
    SshCommandAdapter(revision(), "private", POLICY, None).complete(built)
    assert [base64.b64decode(item["data"]) for item in seen[0]["image"]] == [c.data for c in crops]
    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command",
                        lambda *args, **kwargs: pytest.fail("ssh must not run"))
    for bad in (ModelRequest(built.model_id, built.body, images_bytes=built.images_bytes[:1]),
                ModelRequest(built.model_id, built.body, images_bytes=built.images_bytes[::-1])):
        with pytest.raises(ProxyDispatchError) as refusal:
            SshCommandAdapter(revision(), "private", POLICY, None).complete(bad)
        assert refusal.value.dispatch_class == "not_sent"
