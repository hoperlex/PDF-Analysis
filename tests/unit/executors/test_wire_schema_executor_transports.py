"""The executor transports hand the model the wire form of the response schema (`AR-V3-WIRE-SCHEMA-01`).

Three of the four transports here (``http_api`` in both flavours, the SSH command, the pull task)
are driven for real and asserted on what reached the far side: the body a local gateway received,
the stdin an SSH command would have read, the payload written to the task table. The SSH tunnel
reuses the ``http_api`` adapter and is covered by it. The request's own body and checksum stay put.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.analysis.text.prompt import RESPONSE_SCHEMA
from auditmanager.analysis.text.wire_schema import to_wire_schema
from auditmanager.executors.answers import read_answer
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.http_adapter import build_http_adapter
from auditmanager.executors.model import RevisionRecord, RevisionSettings
from auditmanager.executors.pull import PullAdapter
from auditmanager.executors.runner_repository import TaskRecord
from auditmanager.executors.ssh_adapter import SshCommandAdapter, _task
from auditmanager.shared.errors import ErrorCode

MODEL = "claude-opus-5"
GATEWAY_MODEL = "anthropic/claude-opus-5"
KEY = "sk-sentinel-0123456789abcdef"
REFUSED = ('"oneOf"', '"minLength"', '"maxLength"', '"minimum"', '"maxItems"', '"pattern"')
NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def _request(schema: Any) -> ModelRequest:
    return ModelRequest(model_id=MODEL, body={
        "model": MODEL, "max_tokens": 4096, "system": "Система.",
        "messages": [{"role": "user", "content": "страница 1"}],
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    })


def _assert_no_refused_keyword(text: str) -> None:
    for refused in REFUSED:
        assert refused not in text, refused


def _assert_request_untouched(request: ModelRequest, body: dict[str, Any], sha: str) -> None:
    """The request's own body (the sealed schema in it) and its checksum are what they were."""
    assert request.body == body and request.request_sha256 == sha
    assert request.body["output_config"]["format"]["schema"] == response_schema()


# -- http_api, both flavours ------------------------------------------------------------------------------


def _http(gateway: Any, flavour: str) -> Any:
    return build_http_adapter(
        api_flavour=flavour, base_url=gateway.base_url("/agent/v1"), api_key=KEY, gateway_model=GATEWAY_MODEL,
        timeout_seconds=5, transport="direct", policy=gateway.policy(), context=None,
    )


def test_openai_chat_sends_the_gateway_the_wire_form_of_the_v3_schema(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    request = _request(response_schema())
    body, sha = copy.deepcopy(dict(request.body)), request.request_sha256
    _http(gateway, "openai_chat").complete(request)
    (seen,) = gateway.requests
    assert seen["path"] == "/agent/v1/chat/completions"
    sent = seen["body"]["response_format"]["json_schema"]
    assert sent["schema"] == to_wire_schema(response_schema())
    _assert_no_refused_keyword(json.dumps(seen["body"]))
    _assert_request_untouched(request, body, sha)


def test_anthropic_messages_sends_the_gateway_the_wire_form_of_the_v3_schema(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    request = _request(response_schema())
    body, sha = copy.deepcopy(dict(request.body)), request.request_sha256
    _http(gateway, "anthropic_messages").complete(request)
    (seen,) = gateway.requests
    assert seen["path"].endswith("/v1/messages")
    sent = seen["body"]["output_config"]["format"]
    assert sent["type"] == "json_schema"
    assert sent["schema"] == to_wire_schema(response_schema())
    assert seen["body"]["output_config"]["effort"] == "high"
    assert seen["body"]["model"] == GATEWAY_MODEL
    _assert_no_refused_keyword(json.dumps(seen["body"]))
    _assert_request_untouched(request, body, sha)


@pytest.mark.parametrize("flavour", ["openai_chat", "anthropic_messages"])
def test_a_v1_section_reaches_the_gateway_with_its_schema_as_it_was(
    gateway_factory: Any, flavour: str,
) -> None:
    gateway = gateway_factory()
    _http(gateway, flavour).complete(_request(RESPONSE_SCHEMA))
    (seen,) = gateway.requests
    if flavour == "openai_chat":
        sent = seen["body"]["response_format"]["json_schema"]["schema"]
    else:
        sent = seen["body"]["output_config"]["format"]["schema"]
    assert sent == RESPONSE_SCHEMA
    assert json.dumps(sent, sort_keys=True) == json.dumps(RESPONSE_SCHEMA, sort_keys=True)


# -- the SSH command ------------------------------------------------------------------------------------


def _ssh_revision() -> RevisionRecord:
    return RevisionRecord(
        revision_id="excr_1", connection_id="exc_1", revision_no=1, created_at=NOW, created_by="usr_1",
        settings=RevisionSettings(
            pin_id=MODEL, gateway_model=MODEL, billing="metered", allow_client_documents=True,
            timeout_seconds=100, ssh_host="example.com", ssh_port=22, ssh_user="runner",
            host_key="ssh-ed25519 AAAA", ssh_profile="custom_command",
        ),
    )


def test_the_ssh_command_reads_the_wire_form_on_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[bytes] = []

    def fake_run(endpoint: Any, key: Any, host_key: Any, payload: bytes, **kwargs: Any) -> tuple[bytes, str]:
        sent.append(payload)
        return json.dumps({"model": MODEL, "output_text": "ok", "stop_reason": "end_turn",
                           "input_tokens": 3, "output_tokens": 1}).encode(), ""

    monkeypatch.setattr("auditmanager.executors.ssh_adapter.run_command", fake_run)
    request = _request(response_schema())
    body, sha = copy.deepcopy(dict(request.body)), request.request_sha256
    policy = DestinationPolicy(resolver=lambda host, port: ["8.8.8.8"], networks=lambda: ())
    SshCommandAdapter(_ssh_revision(), "private", policy, None).complete(request)
    (stdin,) = sent
    task = json.loads(stdin)
    assert task["output_schema"] == to_wire_schema(response_schema())
    _assert_no_refused_keyword(stdin.decode("utf-8"))
    assert task["system"] == "Система." and task["max_tokens"] == 4096
    _assert_request_untouched(request, body, sha)


def test_the_ssh_task_of_a_v1_section_is_what_it_was() -> None:
    task = json.loads(_task(_request(RESPONSE_SCHEMA), MODEL))
    assert task["output_schema"] == RESPONSE_SCHEMA
    assert json.dumps(task["output_schema"]) == json.dumps(RESPONSE_SCHEMA)


def test_an_ssh_task_with_no_schema_still_has_none() -> None:
    request = ModelRequest(model_id=MODEL, body={
        "system": "s", "messages": [{"role": "user", "content": "u"}], "max_tokens": 4})
    assert "output_schema" not in json.loads(_task(request, MODEL))


# -- the pull task ---------------------------------------------------------------------------------------


class _Store:
    """The task table, answering at once; the payload written to it is what a runner would be served."""

    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None
        self.task: TaskRecord | None = None

    def insert_task(self, session: Any, **kwargs: Any) -> TaskRecord:
        self.payload = copy.deepcopy(dict(kwargs["payload"]))
        self.task = TaskRecord(
            task_id="ext_T", connection_id=kwargs["connection_id"], revision_id=kwargs["revision_id"],
            origin=kwargs["origin"], run_id=kwargs["run_id"], attempt_id=kwargs["attempt_id"],
            model_call_id=kwargs["model_call_id"], probe_id=kwargs["probe_id"], state="open",
            expected_model=kwargs["expected_model"], created_at=NOW, deadline_at=NOW,
            claimed_by_token_id=None, claim_expires_at=None, first_claimed_at=None, claim_count=0,
            declared_model=None, declared_input_tokens=None, declared_output_tokens=None,
            fail_reason=None, terminal_at=None, payload_cleared_at=None, past_deadline=False,
        )
        return self.task

    def get_task(self, session: Any, task_id: str, **_: Any) -> TaskRecord | None:
        assert self.task is not None
        return replace(self.task, state="answered", declared_model=MODEL, claim_count=1,
                       declared_input_tokens=1, declared_output_tokens=1, terminal_at=NOW)

    def answer_of(self, session: Any, task_id: str) -> tuple[str, str]:
        return '{"observations": []}', MODEL

    def cancel_task(self, session: Any, task_id: str) -> bool:
        return False


class _Sessions:
    @contextmanager
    def __call__(self):  # type: ignore[no-untyped-def]
        class Session:
            def commit(self) -> None: ...
        yield Session()


def _pull(store: _Store) -> PullAdapter:
    revision = RevisionRecord(
        revision_id="excr_R", connection_id="exc_C", revision_no=1, created_at=NOW, created_by="usr_A",
        settings=RevisionSettings(
            pin_id=MODEL, gateway_model=MODEL, billing="not_metered", allow_client_documents=False,
            timeout_seconds=60, pull_client="claude_code_session", answer_deadline_seconds=600,
            max_claimed_tasks=1),
    )
    return PullAdapter(session_factory=_Sessions(), revision=revision, context=None,
                       repository=store)  # type: ignore[arg-type]


def test_the_pull_task_is_written_with_the_wire_form_of_the_v3_schema() -> None:
    store = _Store()
    request = _request(response_schema())
    body, sha = copy.deepcopy(dict(request.body)), request.request_sha256
    _pull(store).complete(request)
    assert store.payload is not None
    assert store.payload["output_schema"] == to_wire_schema(response_schema())
    _assert_no_refused_keyword(json.dumps(store.payload))
    assert store.payload["system"] == "Система." and store.payload["user_text"] == "страница 1"
    _assert_request_untouched(request, body, sha)


def test_the_pull_task_of_a_v1_section_is_what_it_was() -> None:
    store = _Store()
    _pull(store).complete(_request(RESPONSE_SCHEMA))
    assert store.payload is not None
    assert store.payload["output_schema"] == RESPONSE_SCHEMA
    assert json.dumps(store.payload["output_schema"]) == json.dumps(RESPONSE_SCHEMA)


def test_the_pull_default_schema_for_a_body_with_none_is_still_a_plain_object() -> None:
    store = _Store()
    _pull(store).complete(ModelRequest(model_id=MODEL, body={
        "system": "s", "messages": [{"role": "user", "content": "u"}], "max_tokens": 4}))
    assert store.payload is not None and store.payload["output_schema"] == {"type": "object"}


def test_a_keyword_the_runner_validator_cannot_judge_is_still_refused_before_a_task_is_written() -> None:
    store = _Store()
    schema = {"type": "object", "properties": {"x": {"type": "string", "format": "date"}}}
    with pytest.raises(ProxyDispatchError) as raised:
        _pull(store).complete(_request(schema))
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert raised.value.dispatch_class == "not_sent"
    assert store.payload is None, "nothing was written"


def test_the_served_wire_schema_still_judges_the_shape_of_a_v3_answer() -> None:
    """The runner-side check now runs against the wire form: it still holds enums, required fields
    and the closed shape, and says nothing about the dropped length and pattern bounds (the local
    parser re-checks those)."""
    store = _Store()
    _pull(store).complete(_request(response_schema()))
    assert store.payload is not None
    schema = store.payload["output_schema"]
    good = {"observations": [{
        "category": "dimensions", "finding_text": "f", "recommendation_text": "r",
        "proposed_severity": "operational", "evidence": [{"page_number": 1, "quote": "q"}]}]}
    assert read_answer(schema, json.dumps(good)) is None
    bad_enum = copy.deepcopy(good)
    bad_enum["observations"][0]["category"] = "invented"
    assert read_answer(schema, json.dumps(bad_enum)) is not None
    missing = copy.deepcopy(good)
    del missing["observations"][0]["evidence"]
    assert read_answer(schema, json.dumps(missing)) is not None
    too_long = copy.deepcopy(good)
    too_long["observations"][0]["finding_text"] = "x" * 5000
    assert read_answer(schema, json.dumps(too_long)) is None, "the bound the provider cannot be told"
