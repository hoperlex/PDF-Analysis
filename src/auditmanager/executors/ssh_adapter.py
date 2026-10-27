"""One forced SSH command per model call, with the verified PNGs, in order, on stdin.

The image envelope is the task's ``image`` member. One image is the object the forced command
has always read (``{"media_type", "data"}``), so a command installed before
`CMP-EXEC-IMAGES-01` serves it unchanged. Two or more are a **list** of such objects in the
same member: a command that predates several images checks that member for an object and
refuses a list (``invalid image envelope``, exit 64), so an old remote never answers from the
text alone or from one image of several. A list is never sent under a new member name, which an
old command would ignore.
"""

from __future__ import annotations

import base64
import json
import math
import time
from collections.abc import Mapping
from typing import Any

from auditmanager.analysis.public import ModelRequest, ModelResponse, ProviderMode, ProxyDispatchError
from auditmanager.executors.destinations import DestinationPolicy, DestinationRefused, DestinationUnresolvable
from auditmanager.executors.http_adapter import effective_timeout
from auditmanager.executors.image_input import checked_pngs
from auditmanager.executors.model import RevisionRecord
from auditmanager.executors.ssh_transport import SshEndpoint, SshFailure, run_command
from auditmanager.shared.errors import ErrorCode

#: A task with at most one image, as before: a 16 MiB PNG is about 21.4 MiB as base64.
MAX_TASK_BYTES = 24 << 20
#: A task with several images: 32 MiB of PNG is about 42.7 MiB as base64, plus the text.
MAX_MULTI_IMAGE_TASK_BYTES = 48 << 20
MAX_ANSWER_BYTES = 2 << 20


def _refused(message: str, *, sent: bool = False) -> ProxyDispatchError:
    return ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE,
        dispatch_class="outcome_unknown" if sent else "not_sent",
        retry_safe=not sent, message=message,
        details={"dependency": "model_provider"},
    )


def _task(request: ModelRequest, model: str) -> bytes:
    images = checked_pngs(request)
    body = request.body
    system = body.get("system")
    messages = body.get("messages")
    if not isinstance(system, str) or not system or not isinstance(messages, (list, tuple)):
        raise ProxyDispatchError(
            ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="not_sent", retry_safe=False,
            message="the SSH task has no valid prompt",
        )
    parts: list[str] = []
    for item in messages:
        if not isinstance(item, Mapping) or item.get("role") != "user" or not isinstance(item.get("content"), str):
            continue
        parts.append(item["content"])
    if not parts:
        raise ProxyDispatchError(
            ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="not_sent", retry_safe=False,
            message="the SSH task has no user prompt",
        )
    task: dict[str, Any] = {
        "model": model, "system": system, "user_text": "\n\n".join(parts),
        "max_tokens": body.get("max_tokens"),
    }
    output = body.get("output_config")
    if isinstance(output, Mapping) and isinstance(output.get("format"), Mapping):
        schema = output["format"].get("schema")
        if isinstance(schema, Mapping):
            task["output_schema"] = schema
    envelopes = [{"media_type": "image/png", "data": base64.b64encode(image).decode("ascii")}
                 for image in images]
    if len(envelopes) == 1:
        task["image"] = envelopes[0]
    elif envelopes:
        task["image"] = envelopes
    raw = json.dumps(task, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > (MAX_TASK_BYTES if len(images) <= 1 else MAX_MULTI_IMAGE_TASK_BYTES):
        raise ProxyDispatchError(
            ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="not_sent", retry_safe=False,
            message="the SSH task is too large",
        )
    return raw


def _reply(raw: bytes, latency_ms: int) -> ModelResponse:
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise _refused("the SSH command returned invalid JSON", sent=True) from None
    if not isinstance(data, dict) or data.get("is_error") is True:
        raise _refused("the SSH command did not return a model answer", sent=True)
    model, answer, stop = data.get("model"), data.get("output_text"), data.get("stop_reason")
    usage = (data.get("input_tokens"), data.get("output_tokens"))
    if (not isinstance(model, str) or not model or not isinstance(answer, str) or not answer
            or not isinstance(stop, str) or not stop
            or any(type(count) is not int or count < 0 for count in usage)):
        raise _refused("the SSH command returned an incomplete model answer", sent=True)
    cost = data.get("reported_cost_usd")
    if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float))
                             or not math.isfinite(cost) or cost < 0):
        raise _refused("the SSH command returned an invalid cost", sent=True)
    return ModelResponse(
        output_text=answer, stop_reason=stop, input_tokens=usage[0], output_tokens=usage[1],
        latency_ms=latency_ms, reported_cost_usd=cost, model=model,
    )


class SshCommandAdapter:
    """A remote forced command; the host key is pinned in the revision, never scanned here."""

    provider_mode = ProviderMode.LIVE

    def __init__(self, revision: RevisionRecord, key: str, policy: DestinationPolicy,
                 context: Any | None) -> None:
        self._revision = revision
        self._key = key
        self._policy = policy
        self._context = context

    def complete(self, request: ModelRequest) -> ModelResponse:
        settings = self._revision.settings
        assert settings.ssh_host and settings.ssh_port and settings.ssh_user
        # Verify bytes before opening a network path. The hostname policy is enforced again
        # on every Attempt, including one whose revision was frozen on an earlier run.
        payload = _task(request, settings.gateway_model)
        try:
            addresses = self._policy.check(settings.ssh_host, settings.ssh_port, transport="ssh_command")
        except (DestinationRefused, DestinationUnresolvable):
            raise _refused("the SSH destination is not available") from None
        timeout = effective_timeout(settings.timeout_seconds, self._context)
        if timeout is None:
            raise _refused("the attempt has too little time left")
        # Use the checked IP itself: another DNS lookup inside ssh must not re-aim the call.
        endpoint = SshEndpoint(addresses[0], settings.ssh_port, settings.ssh_user)
        started = time.monotonic()
        try:
            raw, _stderr = run_command(
                endpoint, self._key, settings.host_key, payload,
                timeout_s=timeout, max_output_bytes=MAX_ANSWER_BYTES,
            )
        except SshFailure as failure:
            raise _refused(f"the SSH command failed ({failure.outcome})", sent=failure.sent) from None
        return _reply(raw, int((time.monotonic() - started) * 1000))


def build_ssh_command_adapter(
    revision: RevisionRecord, key: str, policy: DestinationPolicy, context: Any | None,
) -> SshCommandAdapter:
    return SshCommandAdapter(revision, key, policy, context)
