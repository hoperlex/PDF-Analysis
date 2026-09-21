"""Provider mode: two adapters, and no way to present one as the other.

"A recorded run must never be presentable as a live one" is a named ``PC-01``
acceptance criterion, so it is tested as a set of things that are *impossible*, not as
a value that happens to be right in the happy path. Four mechanisms, four tests:

1. the mode is a closed enum with two members;
2. it is a read-only class constant on the adapter, not a caller's argument;
3. a recording file has no mode field to forge;
4. publishing refuses provenance that disagrees with its own call records.
"""

from __future__ import annotations

import json
import socket

import pytest

from auditmanager.analysis.text import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    LiveAdapter,
    ProviderMode,
    RecordedAdapter,
    assert_consistent_mode,
    load_provider_config,
    run_text_analysis,
)
from auditmanager.analysis.text.config import ENV_API_KEY, ENV_PROVIDER_MODE
from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.analysis.text.recorded import RECORDING_VERSION
from auditmanager.runs import RETRYABLE_STAGE_ERRORS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId


def test_socket_guard_refuses_a_socket():
    """The offline guard is live. Kept as a permanent test, not a one-off mutation."""
    with pytest.raises(AssertionError):
        socket.socket()


# --- 1. the vocabulary is closed ------------------------------------------------


def test_provider_mode_is_a_closed_two_member_enum():
    assert [member.value for member in ProviderMode] == ["live", "recorded"]
    with pytest.raises(DomainError) as raised:
        ProviderMode.parse("almost_live")
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_recorded_is_the_default_mode():
    """``OD-13``: a suite that sets nothing cannot reach the network."""
    assert load_provider_config({}).mode is ProviderMode.RECORDED
    assert load_provider_config({ENV_PROVIDER_MODE: "live"}).mode is ProviderMode.LIVE


# --- 2. the mode belongs to the adapter -----------------------------------------


def test_adapter_mode_is_not_settable(recorded_adapter):
    assert recorded_adapter.provider_mode is ProviderMode.RECORDED
    with pytest.raises(AttributeError):
        recorded_adapter.provider_mode = ProviderMode.LIVE  # type: ignore[misc]


def test_configuration_cannot_relabel_a_replay(text_layer_document, recorded_adapter):
    """Configure the run "live", replay it, and it is still recorded everywhere.

    This is the failure the criterion names: an operator sets live, the recorded
    adapter is what actually runs, and the artifact must not inherit the intent.
    """
    config = load_provider_config({ENV_PROVIDER_MODE: "live", ENV_API_KEY: "unused"})
    assert config.mode is ProviderMode.LIVE

    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=recorded_adapter,
        config=config,
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.artifact["provider_mode"] == "recorded"
    assert outcome.metrics["provider_mode"] == "recorded"
    assert all(call.provider_mode is ProviderMode.RECORDED for call in outcome.model_calls)


# --- 3. a recording has nothing to forge ----------------------------------------


def test_no_recording_file_carries_a_provider_mode(recorded_adapter, variant_adapter):
    directories = [recorded_adapter.recording_dir] + [
        variant_adapter(name).recording_dir
        for name in ("truncated", "over_budget", "ungrounded_quotation")
    ]
    seen = 0
    for directory in directories:
        for path in directory.glob("*.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            assert "provider_mode" not in document
            assert "mode" not in document
            seen += 1
    assert seen == 4


def test_a_forged_mode_field_in_a_recording_changes_nothing(
    tmp_path, text_layer_document, recorded_adapter
):
    """Add ``provider_mode: live`` to a recording by hand; the run is still recorded."""
    source = next(recorded_adapter.recording_dir.glob("*.json"))
    document = json.loads(source.read_text(encoding="utf-8"))
    document["provider_mode"] = "live"  # the forgery
    forged_dir = tmp_path / "forged"
    forged_dir.mkdir()
    (forged_dir / source.name).write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8"
    )

    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=RecordedAdapter(forged_dir),
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.artifact["provider_mode"] == "recorded"


# --- 4. inconsistent provenance is not publishable ------------------------------


def test_publishing_refuses_a_mode_that_disagrees_with_its_calls(
    text_layer_document, recorded_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    with pytest.raises(DomainError) as raised:
        assert_consistent_mode(ProviderMode.LIVE, outcome.model_calls)
    assert raised.value.code is ErrorCode.ANALYSIS_FAILED


# --- the two adapters' own boundaries -------------------------------------------


def test_missing_recording_is_not_a_transport_failure_and_never_a_live_call(
    text_layer_document, empty_recording_dir
):
    """No recording, no call -- and nothing for a retry ladder to do.

    Until `W29-RETRY` this asserted ``dependency_unavailable``, which is
    ``retryable: true`` in the frozen catalog, so a document with no recording bought
    three attempts and both pinned backoffs waiting for a file to appear on a local
    disk. The file is absent and will be absent in ten seconds. The socket guard is
    active for this whole suite, so "no call" is enforced rather than asserted.
    """
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=RecordedAdapter(empty_recording_dir),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.artifact is None
    assert outcome.model_calls == ()
    assert outcome.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert outcome.error.detail_fields == {
        "stage_id": STAGE_ID,
        "reason": "recording_missing",
    }
    # The property, against the catalog rather than against a literal: the executor
    # decides whether to ladder a failure by reading `code.retryable`, and nothing
    # else. A code that reads True here is a code this failure gets retried on.
    assert outcome.error.code.retryable is False
    assert outcome.error.code not in RETRYABLE_STAGE_ERRORS


def test_every_way_the_corpus_fails_to_answer_takes_the_same_non_retryable_code(
    empty_recording_dir, tmp_path
):
    """Absent, misfiled, unsupported version, malformed: one class, one code.

    All four are the same fact about the same local directory -- the corpus it holds
    does not answer this request -- and no second attempt at the same request changes
    any of them. The test enumerates the adapter's own `recording_*` reason vocabulary
    so that a fifth member added on a retryable code fails here.
    """
    from auditmanager.analysis.text import AR_TEXT_PROFILE, build_request, load_text_layer

    document = json.loads(
        (
            RecordedAdapter().recording_dir / "inputs/ar_baseline_text_layer.json"
        ).read_text(encoding="utf-8")
    )
    request = build_request(
        model_id="claude-opus-5",
        bundle=AR_TEXT_PROFILE.prompt_bundle,
        text_layer=load_text_layer(document),
    )

    corpus = tmp_path / "variants"
    corpus.mkdir()

    def _written(**overrides) -> RecordedAdapter:
        body = {
            "recording_version": RECORDING_VERSION,
            "request_sha256": request.request_sha256,
            "model_id": request.model_id,
            "stop_reason": "end_turn",
            "output_text": "{}",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "latency_ms": 1,
            "note": "",
        }
        body.update(overrides)
        directory = tmp_path / f"corpus-{len(list(tmp_path.iterdir()))}"
        directory.mkdir()
        (directory / f"{request.request_sha256}.json").write_text(
            json.dumps(body), encoding="utf-8"
        )
        return RecordedAdapter(directory)

    cases = {
        "recording_missing": RecordedAdapter(empty_recording_dir),
        "recording_key_mismatch": _written(request_sha256="0" * 64),
        "recording_version_unsupported": _written(recording_version="0.0.1"),
        "recording_malformed": _written(latency_ms="not a number"),
    }

    seen = {}
    for reason, adapter in cases.items():
        with pytest.raises(DomainError) as raised:
            adapter.complete(request)
        seen[reason] = raised.value.code
        assert raised.value.detail_fields.get("reason") == reason
        assert raised.value.code.retryable is False, (
            f"{reason} reports {raised.value.code.value}, which the catalog marks "
            "retryable: the executor will ladder a failure that cannot change"
        )

    assert set(seen.values()) == {ErrorCode.ANALYSIS_INPUT_INVALID}


def test_missing_recording_envelope_leaks_no_path_or_payload(empty_recording_dir):
    """The envelope screen has to accept the message this path produces."""
    from auditmanager.analysis.text import AR_TEXT_PROFILE, build_request, load_text_layer

    document = json.loads(
        (
            RecordedAdapter().recording_dir / "inputs/ar_baseline_text_layer.json"
        ).read_text(encoding="utf-8")
    )
    request = build_request(
        model_id="claude-opus-5",
        bundle=AR_TEXT_PROFILE.prompt_bundle,
        text_layer=load_text_layer(document),
    )
    with pytest.raises(DomainError) as raised:
        RecordedAdapter(empty_recording_dir).complete(request)

    envelope = raised.value.envelope("corr-b3-test").as_dict()
    assert envelope["error_code"] == "analysis_input_invalid"
    # Read from the catalog by the envelope itself, never a parameter: this is the
    # value the executor's retry policy acts on.
    assert envelope["retryable"] is False
    assert envelope["details"] == {"stage_id": STAGE_ID, "reason": "recording_missing"}
    # The screen already refuses a URL, a path or a credential shape; assert the
    # prompt itself did not travel either.
    assert "Степень" not in envelope["message"]
    assert str(empty_recording_dir) not in envelope["message"]


def test_live_mode_with_an_unset_key_fails_at_construction(monkeypatch):
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    config = load_provider_config({ENV_PROVIDER_MODE: "live"})
    assert config.mode is ProviderMode.LIVE
    assert config.api_key is None

    with pytest.raises(DomainError) as raised:
        LiveAdapter(api_key=config.api_key)
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert raised.value.detail_fields["reason"] == "provider_credential_missing"
    # It failed before rendering a prompt: no document text is anywhere near it.
    assert "Степень" not in str(raised.value)


def test_live_adapter_declares_the_live_mode():
    """Constructed with an injected client, so no credential and no network."""

    class _Unused:
        pass

    adapter = LiveAdapter(api_key=None, client=_Unused())
    assert adapter.provider_mode is ProviderMode.LIVE
