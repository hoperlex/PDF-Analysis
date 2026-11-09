"""`HOSTS-AGENT-01`: the host members of the runner client (`runner_client.py`, `RUNNER_API.md` section 10).

A claimed task either has all the host members or none; a host answer carries ``provider``, ``access``,
``reported_model`` and ``usage`` and a single-model answer is byte-for-byte what it was; a host enrollment document is
checked and a connection's is too.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

for _name, _file in (("executor_runner_support", "_support.py"), ("executor_runner_agent_support", "_agent_support.py"),
                     ("executor_runner_host_support", "_host_support.py")):
    if _name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(_name, Path(__file__).with_name(_file))
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_name] = _module
        _spec.loader.exec_module(_module)
S = sys.modules["executor_runner_support"]
A = sys.modules["executor_runner_agent_support"]
H = sys.modules["executor_runner_host_support"]
rc = A.load_module("exec_host_client_under_test", A.RUNNER_DIR / "runner_client.py")


def _client(stand):
    return rc.RunnerClient(stand.origin, S.TOKEN, allow_insecure_http=True)


def test_a_host_task_is_returned_with_its_members_and_a_task_without_them_is_unchanged():
    with H.HostStand() as stand:
        stand.add_task(stand.host_task("ext_A1", "codex", "gpt-6.1-sol", effort="low"))
        stand.add_task(S.make_task("ext_A2", "claude-opus-5"))
        host, plain = _client(stand).claim(1), _client(stand).claim(1)
    assert (host["provider"], host["access"], host["model_id"], host["model"], host["effort"]) == (
        "codex", "subscription", "gpt-6.1-sol", "gpt-6.1-sol", "low")
    assert (host["max_output_tokens"], host["timeout_seconds"], host["cell_key"]) == (4000, 20, "text:main")
    assert not any(key in plain for key in rc.HOST_TASK_KEYS)


def test_a_task_that_names_only_model_id_gets_its_model_from_it_and_two_different_names_are_refused():
    with H.HostStand() as stand:
        task = stand.host_task("ext_B1", "codex", "gpt-6.1-sol")
        del task["model"]
        stand.add_task(task)
        assert _client(stand).claim(1)["model"] == "gpt-6.1-sol"
        stand.add_task(stand.host_task("ext_B2", "codex", "gpt-6.1-sol", model="gpt-6-sol"))
        with pytest.raises(rc.RunnerUnavailable, match="malformed host task"):
            _client(stand).claim(1)


@pytest.mark.parametrize("change", [
    {"provider": "gemini"}, {"access": "free"}, {"effort": ""}, {"effort": 3}, {"max_output_tokens": 0},
    {"max_output_tokens": True}, {"max_output_tokens": "4000"}, {"timeout_seconds": 0}, {"timeout_seconds": 10 ** 7},
    {"cell_key": ""}, {"cell_key": None}, {"provider": None},
])
def test_a_host_member_that_is_missing_or_ill_typed_makes_the_whole_task_malformed(change):
    with H.HostStand() as stand:
        task = stand.host_task("ext_C1", "codex", "gpt-6.1-sol")
        task.update(change)
        stand.add_task(task)
        with pytest.raises(rc.RunnerUnavailable, match="malformed host task"):
            _client(stand).claim(1)


def test_a_task_with_only_some_of_the_host_members_is_malformed():
    with H.HostStand() as stand:
        task = stand.host_task("ext_C2", "codex", "gpt-6.1-sol")
        del task["cell_key"]
        stand.add_task(task)
        with pytest.raises(rc.RunnerUnavailable, match="malformed host task"):
            _client(stand).claim(1)


def test_a_host_answer_names_provider_access_reported_model_and_usage_and_sends_no_top_level_token_counts():
    with H.HostStand() as stand:
        _client(stand).answer("ext_D1", '{"a":1}', "claude-opus-5-5", 11, 7, provider="claude_code", access="subscription",
                              reported_model="claude-opus-5-5-20261001")
        _client(stand).answer("ext_D2", '{"a":1}', "gpt-6.1-sol", provider="codex", access="api", reported_model="gpt-6.1-sol")
        bodies = {r["task_id"]: r["body"] for r in stand.of_kind("answer")}
    assert bodies["ext_D1"] == {"output_text": '{"a":1}', "model": "claude-opus-5-5", "provider": "claude_code",
                                "access": "subscription", "reported_model": "claude-opus-5-5-20261001",
                                "usage": {"input_tokens": 11, "output_tokens": 7}}
    assert "usage" not in bodies["ext_D2"], "no count is invented"


def test_a_single_model_answer_is_the_wire_it_always_was():
    with H.HostStand() as stand:
        _client(stand).answer("ext_D3", '{"a":1}', "claude-opus-5", 5, 2)
        _client(stand).answer("ext_D4", '{"a":1}', "claude-opus-5")
        bodies = {r["task_id"]: r["body"] for r in stand.of_kind("answer")}
    assert bodies["ext_D3"] == {"output_text": '{"a":1}', "model": "claude-opus-5", "input_tokens": 5, "output_tokens": 2}
    assert bodies["ext_D4"] == {"output_text": '{"a":1}', "model": "claude-opus-5"}


@pytest.mark.parametrize("kwargs", [
    {"provider": "gemini", "access": "api", "reported_model": "x"}, {"provider": "codex", "access": "free", "reported_model": "x"},
    {"provider": "codex", "access": "api", "reported_model": ""}, {"provider": "codex", "access": "api", "reported_model": "x" * 201},
    {"provider": "codex", "access": "api", "reported_model": None},
])
def test_a_host_answer_that_names_no_valid_provider_access_or_reported_model_is_never_sent(kwargs):
    with H.HostStand() as stand:
        with pytest.raises(rc.RunnerRejected):
            _client(stand).answer("ext_D5", "{}", "m", **kwargs)
        assert stand.of_kind("answer") == []


def test_a_host_enrollment_document_is_checked_for_its_host_id_and_a_connections_for_its_metadata(monkeypatch):
    with H.HostStand() as stand:
        client = rc.RunnerClient(stand.origin, H.HOST_SECRET, allow_insecure_http=True)
        issued = client.redeem_enrollment(H.HOST_SECRET, "instance-abcdef-01", "0.9.0")
        assert issued["host_id"] == H.HOST_ID and isinstance(issued["catalogue"], list) and len(issued["token"]) == 56
        original = stand._decide

        def decide(kind, record, document=None):
            reply = original(kind, record)
            if kind == "enroll":
                reply.body = {**reply.body, **(document or {})}
            return reply

        for change, ok in (({"host_id": "exh_not-a-ulid"}, False), ({"catalogue": {"a": 1}}, False),
                           ({"host_id": None, "runner_token": None}, False),  # neither a host nor a connection's metadata
                           ({"runner_token": None}, True)):  # a host document may leave the metadata out
            monkeypatch.setattr(stand, "_decide", lambda kind, record, change=change: decide(kind, record, change))
            if ok:
                assert client.redeem_enrollment(H.HOST_SECRET, "instance-abcdef-01")["host_id"] == H.HOST_ID
            else:
                with pytest.raises(rc.RunnerUnavailable):
                    client.redeem_enrollment(H.HOST_SECRET, "instance-abcdef-01")


def test_the_host_id_pattern_is_the_contracts_ulid_alphabet():
    assert rc.HOST_ID_RE.fullmatch(H.HOST_ID)
    for bad in ("exh_", "exh_01J9ZZZZZZZZZZZZZZZZZZZZZ", "exh_01J9ZZZZZZZZZZZZZZZZZZZZZZZ", "exh_01J9ZZZZZZZZZZZZZZZZZZZZZU", "con_01J9ZZZZZZZZZZZZZZZZZZZZZZ"):
        assert rc.HOST_ID_RE.fullmatch(bad) is None, bad
