"""The offline guard, and proof that it fires.

A guard nobody has watched fail is indistinguishable from a guard that was quietly
removed. :func:`test_socket_guard_refuses_a_socket` is that proof, and it runs on
every invocation rather than once in a report: if ``conftest._no_network`` ever stops
patching, this test goes red in the same run that would otherwise have started making
real calls.
"""

from __future__ import annotations

import socket

import pytest

from auditmanager.analysis.text import ProviderMode, RecordedAdapter


def test_socket_guard_refuses_a_socket():
    """The guard is live. This is the mutation, kept as a permanent test."""
    with pytest.raises(AssertionError):
        socket.socket()
    with pytest.raises(AssertionError):
        socket.getaddrinfo("example.invalid", 443)


def test_recorded_adapter_holds_no_client_and_no_credential(recorded_adapter):
    """There is no live path to fall back to, by construction rather than by policy.

    ``RecordedAdapter`` declares ``__slots__`` holding exactly one directory. It has
    no client attribute and nowhere to put one, so "fall back to live on a miss" is
    not a branch a future edit can flip on - it would have to be written from nothing.
    """
    assert RecordedAdapter.__slots__ == ("_directory",)
    assert set(vars(recorded_adapter.__class__)) & {"_client", "api_key"} == set()
    assert recorded_adapter.provider_mode is ProviderMode.RECORDED


def test_full_replay_runs_with_sockets_refused(text_layer_document, recorded_adapter):
    """The real thing: a whole stage run completes while every socket is refused."""
    from auditmanager.analysis.text import STATUS_SUCCEEDED, run_text_analysis
    from auditmanager.shared.identity import RunId

    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.artifact is not None
