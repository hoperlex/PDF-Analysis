from __future__ import annotations

import base64
import hashlib
import json
import struct
import time
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


# -- signs of life and effort, `AR-V3-LIVENESS-01` ---------------------------------------------

from auditmanager.executors.http_adapter import DEADLINE_MARGIN_SECONDS  # noqa: E402
from auditmanager.executors.ssh_transport import SshFailure  # noqa: E402
from auditmanager.jobs.lease import AttemptContext  # noqa: E402
from auditmanager.shared.errors import ErrorCode  # noqa: E402


def request_with(output_config: object) -> ModelRequest:
    body = {"system": "system", "messages": [{"role": "user", "content": "describe"}], "max_tokens": 64}
    if output_config is not ... :
        body["output_config"] = output_config
    return ModelRequest(model_id="claude-opus-5", body=body)


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_the_effort_of_the_sealed_request_is_passed_to_the_command(effort: str) -> None:
    task = json.loads(_task(request_with({"effort": effort}), "claude-opus-5"))
    assert task["effort"] == effort
    assert set(task) == {"model", "system", "user_text", "max_tokens", "effort"}, "nothing else is set"


def test_the_effort_travels_beside_the_output_schema() -> None:
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
              "additionalProperties": False}
    task = json.loads(_task(request_with({"effort": "high", "format": {"type": "json_schema", "schema": schema}}),
                            "claude-opus-5"))
    assert task["effort"] == "high" and task["output_schema"] == schema


@pytest.mark.parametrize(
    "output_config",
    [..., None, {}, {"effort": None}, {"effort": ""}, {"effort": "HIGH"}, {"effort": "ultra"}, {"effort": 3},
     {"effort": ["high"]}, {"effort": {"level": "high"}}, {"effort": True}, "high", ["effort", "high"]],
)
def test_an_effort_that_is_not_one_of_the_five_is_left_out(output_config: object) -> None:
    assert "effort" not in json.loads(_task(request_with(output_config), "claude-opus-5"))


def make_context(**options: object) -> AttemptContext:
    return AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic(), **options)


def run_with(monkeypatch: pytest.MonkeyPatch, context: object, **seen_into: object) -> dict:
    """Run one call through a recorded ``run_command``; return the keyword arguments it got."""
    seen: dict = {}

    def fake_run(endpoint, key, host_key, payload, **kwargs):
        seen.update(kwargs)
        return answer(), ""

    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command", fake_run)
    SshCommandAdapter(revision(), "private", POLICY, context).complete(request())
    return seen


def test_without_a_context_the_call_is_made_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = run_with(monkeypatch, None)
    assert set(seen) == {"timeout_s", "max_output_bytes"}, "no live parameters at all"
    assert seen["timeout_s"] == 100.0


def test_with_a_context_the_call_is_live_to_the_attempts_ceiling_less_the_margin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = make_context()
    context.started_monotonic -= 1000  # claimed 1000 s ago: past the 900 s watchdog, so only a
    context.progress()                 # live Attempt (an earlier call signalled) can still call
    seen = run_with(monkeypatch, context)
    assert set(seen) == {"timeout_s", "max_output_bytes", "live_hard_cap_s", "live_stall_s", "on_signal"}
    assert 7200 - 1000 - DEADLINE_MARGIN_SECONDS - 5 < seen["live_hard_cap_s"] <= 7200 - 1000 - DEADLINE_MARGIN_SECONDS
    assert seen["live_stall_s"] == 600.0
    assert seen["on_signal"] == context.progress


def test_the_signal_the_transport_gets_makes_the_attempt_live(monkeypatch: pytest.MonkeyPatch) -> None:
    context = make_context()
    seen = run_with(monkeypatch, context)
    assert context.live is False
    seen["on_signal"]()
    assert context.live is True


def test_the_timeout_before_the_first_sign_is_what_it_was(monkeypatch: pytest.MonkeyPatch) -> None:
    """The revision's 100 s cut to what the 900 s watchdog leaves, less the margin: unchanged."""
    context = make_context()
    assert run_with(monkeypatch, context)["timeout_s"] == 100.0
    context.started_monotonic -= 800  # 100 s of the watchdog left, 40 s after the margin
    assert 39 <= run_with(monkeypatch, context)["timeout_s"] <= 40


def test_the_stall_window_is_the_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    assert run_with(monkeypatch, make_context(stall_seconds=45.0))["live_stall_s"] == 45.0


def test_an_attempt_past_its_ceiling_gets_a_ceiling_of_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    context = make_context(hard_cap_seconds=100.0, watchdog_seconds=10_000.0)
    context.started_monotonic -= 50  # 50 s of the ceiling left: less than the margin
    seen = run_with(monkeypatch, context)
    assert seen["live_hard_cap_s"] == 0.0


@pytest.mark.parametrize(
    "outcome,dependency",
    [("stalled", "executor_stalled"), ("hard_cap", "executor_hard_cap"), ("timeout", "model_provider"),
     ("protocol_error", "model_provider")],
)
def test_a_cut_call_is_dependency_unavailable_with_an_uncertain_effect(
    monkeypatch: pytest.MonkeyPatch, outcome: str, dependency: str,
) -> None:
    def fake_run(*args, **kwargs):
        raise SshFailure(outcome, "the command may have run", sent=True)

    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command", fake_run)
    with pytest.raises(ProxyDispatchError) as raised:
        SshCommandAdapter(revision(), "private", POLICY, make_context()).complete(request())
    error = raised.value
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert error.dispatch_class == "outcome_unknown" and error.retry_safe is False
    assert dict(error.detail_fields) == {"dependency": dependency}
    assert outcome in str(error)
    assert "may have run" not in str(error), "no remote text in the error"
    envelope = error.envelope("corr_1")  # the catalog accepts the details
    assert envelope.details == {"dependency": dependency}
