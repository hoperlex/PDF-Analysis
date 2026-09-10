"""Two replays of one recording produce the same request and the same observations.

The one thing this suite must never do is assert model wording. ``PROTOTYPE_PROFILE``
section 7.1 and the task's own rules forbid byte-equality on generated prose, because
a test that pins a sentence turns every prompt improvement into a test failure and
teaches the next author to freeze the prompt instead. So the assertions below compare
*structure* - the request checksum, the anchors, the categories, the ordinals - and
compare prose only between two replays of the same recording, where identity is the
determinism claim itself and not a claim about what the model should have said.
"""

from __future__ import annotations

from typing import Any

from auditmanager.analysis.text import (
    AR_TEXT_PROFILE,
    STATUS_SUCCEEDED,
    build_request,
    load_text_layer,
    run_text_analysis,
)
from auditmanager.shared.identity import RunId

MODEL_ID = "claude-opus-5"


def _run(text_layer_document: dict[str, Any], adapter: Any) -> Any:
    return run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=adapter
    )


def _observations_without_identity(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """The artifact's observations with the two legitimately fresh identities removed."""
    stripped = []
    for observation in artifact["observations"]:
        copy = dict(observation)
        copy.pop("model_call_id")
        stripped.append(copy)
    return stripped


def test_request_checksum_is_stable_across_builds(text_layer_document):
    text_layer = load_text_layer(text_layer_document)
    first = build_request(
        model_id=MODEL_ID, bundle=AR_TEXT_PROFILE.prompt_bundle, text_layer=text_layer
    )
    second = build_request(
        model_id=MODEL_ID, bundle=AR_TEXT_PROFILE.prompt_bundle, text_layer=text_layer
    )
    assert first.request_sha256 == second.request_sha256
    # Nothing time-varying, random or identity-bearing may enter the body. A run id or
    # a timestamp here would make every recording a single-use fixture.
    assert first.body == second.body


def test_two_replays_agree_on_request_and_observations(text_layer_document, recorded_adapter):
    first = _run(text_layer_document, recorded_adapter)
    second = _run(text_layer_document, recorded_adapter)

    assert first.status == second.status == STATUS_SUCCEEDED
    assert first.metrics["request_sha256"] == second.metrics["request_sha256"]
    assert first.model_calls[0].request_sha256 == second.model_calls[0].request_sha256
    assert first.model_calls[0].response_sha256 == second.model_calls[0].response_sha256
    assert _observations_without_identity(first.artifact) == _observations_without_identity(
        second.artifact
    )
    assert first.artifact["pages_analysed"] == second.artifact["pages_analysed"]


def test_each_replay_is_a_distinct_call_record(text_layer_document, recorded_adapter):
    """Same question, same answer, different call record.

    ``model_call`` rows are immutable and one per call, so two replays must not share
    an identity even though they replay the same bytes.
    """
    first = _run(text_layer_document, recorded_adapter)
    second = _run(text_layer_document, recorded_adapter)
    assert first.model_calls[0].model_call_id != second.model_calls[0].model_call_id
    assert first.artifact["run_id"] != second.artifact["run_id"]


def test_replay_asserts_no_wording(text_layer_document, recorded_adapter):
    """The prose is present, Russian, and not compared against a literal.

    ``OD-05``: finding and recommendation prose is Russian; machine fields, categories
    and identities stay ASCII. That split is checkable without pinning a sentence.
    """
    outcome = _run(text_layer_document, recorded_adapter)
    for observation in outcome.artifact["observations"]:
        assert observation["finding_text"].strip()
        assert observation["recommendation_text"].strip()
        assert any("Ѐ" <= ch <= "ӿ" for ch in observation["finding_text"])
        assert any("Ѐ" <= ch <= "ӿ" for ch in observation["recommendation_text"])
        assert observation["category"].isascii()
        assert observation["model_call_id"].isascii()
    assert outcome.artifact["artifact_role"].isascii()
    assert outcome.artifact["provider_mode"].isascii()
