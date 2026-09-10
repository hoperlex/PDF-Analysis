"""The profile, the prompt bundle, and the shape of what the stage publishes.

Two questions this file answers, both of which are cheap to answer now and expensive
to answer later from a live transcript:

* **Is the prompt still narrow?** PC-01 answers one product question with two
  categories. A prompt that grows a third category, starts naming external norms, or
  starts asking the model for offsets has stopped being this stage.
* **Is the artifact exactly what section 4.7 declares?** It is ``B4``'s only input, so
  an extra root key is not a harmless addition - the gate is deterministic and takes no
  model input of any other kind.
"""

from __future__ import annotations

import json

from auditmanager.analysis.text import (
    ARTIFACT_ROLE,
    ARTIFACT_VERSION,
    AR_TEXT_PROFILE,
    AR_TEXT_PROMPT_BUNDLE,
    CATEGORIES,
    STAGE_ID,
    build_request,
    load_text_layer,
    provider_lock,
    resolve_profile,
    run_text_analysis,
)
from auditmanager.analysis.text.prompt import RESPONSE_SCHEMA, SYSTEM_PROMPT
from auditmanager.shared.identity import RunId


# --- the profile is immutable and resolved by identity --------------------------


def test_the_profile_is_resolved_by_a_pinned_identity():
    resolved = resolve_profile(AR_TEXT_PROFILE.analysis_profile_id)
    assert resolved is AR_TEXT_PROFILE
    assert str(AR_TEXT_PROFILE.analysis_profile_id).startswith("ap_")
    assert str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id).startswith("pb_")


def test_the_identities_are_stable_across_resolutions():
    """Immutable means the same identity every time, not a fresh ULID per run."""
    first = resolve_profile().analysis_profile_id
    second = resolve_profile().analysis_profile_id
    assert first == second
    assert resolve_profile().content_sha256 == AR_TEXT_PROFILE.content_sha256


def test_the_profile_hash_covers_the_bundle_it_binds():
    """A prompt edit must move the profile hash too, or the two can drift in a record."""
    import dataclasses

    edited_bundle = dataclasses.replace(
        AR_TEXT_PROMPT_BUNDLE, system_prompt=SYSTEM_PROMPT + "\nЕщё одно правило."
    )
    edited_profile = dataclasses.replace(AR_TEXT_PROFILE, prompt_bundle=edited_bundle)
    assert edited_bundle.content_sha256 != AR_TEXT_PROMPT_BUNDLE.content_sha256
    assert edited_profile.content_sha256 != AR_TEXT_PROFILE.content_sha256


def test_a_prompt_edit_changes_the_request_checksum(text_layer_document):
    """So a stale recording is reported missing, never replayed at a new prompt."""
    import dataclasses

    text_layer = load_text_layer(text_layer_document)
    model_id = provider_lock().primary_model_id
    original = build_request(
        model_id=model_id, bundle=AR_TEXT_PROMPT_BUNDLE, text_layer=text_layer
    )
    edited = build_request(
        model_id=model_id,
        bundle=dataclasses.replace(AR_TEXT_PROMPT_BUNDLE, system_prompt=SYSTEM_PROMPT + " "),
        text_layer=text_layer,
    )
    assert original.request_sha256 != edited.request_sha256


# --- the prompt is narrow -------------------------------------------------------


def test_exactly_two_categories_everywhere():
    assert CATEGORIES == ("internal_contradiction", "explicit_placeholder")
    assert AR_TEXT_PROFILE.categories == CATEGORIES
    enum = RESPONSE_SCHEMA["properties"]["observations"]["items"]["properties"]["category"][
        "enum"
    ]
    assert enum == list(CATEGORIES)
    assert all(category.isascii() for category in CATEGORIES)


def test_the_schema_never_asks_the_model_for_an_offset():
    """The model does not compute reliable offsets, so it is not given a place to."""
    rendered = json.dumps(RESPONSE_SCHEMA)
    for field in ("char_start", "char_end", "offset", "block_id"):
        assert field not in rendered
    evidence = RESPONSE_SCHEMA["properties"]["observations"]["items"]["properties"]["evidence"]
    assert evidence["items"]["required"] == ["page_number", "quote"]
    assert evidence["items"]["additionalProperties"] is False
    assert evidence["minItems"] == 1


def test_the_prompt_closes_off_the_questions_this_stage_does_not_answer():
    """Each near-miss class in the corpus has a rule that excludes it."""
    for phrase in (
        "СНиП",             # external norms, named so they can be excluded
        "чертеж",           # no inference from drawings
        "вердикт",          # no verdict
        "разным здани",     # different objects are not a contradiction
        "этаж",             # different storeys are not a contradiction
        "того же значения", # a repeated value is agreement, not a discrepancy
        "ссылка на таблицу",  # a reference to where the value is given is a decision
        "не решаешь, что должно было быть указано",  # no "it was required" claim
    ):
        assert phrase.lower() in SYSTEM_PROMPT.lower(), phrase


def test_the_prompt_asks_for_verbatim_quotations():
    for phrase in ("дословн", "посимвольно", "page_number"):
        assert phrase.lower() in SYSTEM_PROMPT.lower()


def test_no_sampling_parameter_is_sent(text_layer_document):
    """``temperature``/``top_p``/``top_k`` are removed on the pinned family - 400."""
    request = build_request(
        model_id=provider_lock().primary_model_id,
        bundle=AR_TEXT_PROMPT_BUNDLE,
        text_layer=load_text_layer(text_layer_document),
    )
    assert set(request.body) == {
        "model",
        "max_tokens",
        "system",
        "messages",
        "thinking",
        "output_config",
    }
    assert request.body["output_config"]["format"]["type"] == "json_schema"
    assert request.body["thinking"] == {"type": "adaptive"}


def test_the_model_identity_comes_from_the_lock(text_layer_document):
    lock = provider_lock()
    request = build_request(
        model_id=lock.primary_model_id,
        bundle=AR_TEXT_PROMPT_BUNDLE,
        text_layer=load_text_layer(text_layer_document),
    )
    assert request.body["model"] == lock.primary_model_id
    assert set(lock.models) >= {lock.primary_model_id}


# --- the artifact is exactly what section 4.7 declares ---------------------------


def test_the_artifact_root_carries_exactly_the_declared_keys(
    text_layer_document, recorded_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    assert set(outcome.artifact) == {
        "artifact_role",
        "artifact_version",
        "run_id",
        "stage_id",
        "analysis_profile_id",
        "prompt_bundle_id",
        "provider_mode",
        "pages_analysed",
        "observations",
    }
    assert outcome.artifact["artifact_role"] == ARTIFACT_ROLE == "analysis.text_observations"
    assert outcome.artifact["artifact_version"] == ARTIFACT_VERSION == "1.0.0"
    assert outcome.artifact["stage_id"] == STAGE_ID == "text_analysis"


def test_each_observation_carries_exactly_the_declared_fields(
    text_layer_document, recorded_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    for observation in outcome.artifact["observations"]:
        assert set(observation) == {
            "observation_ordinal",
            "category",
            "finding_text",
            "recommendation_text",
            "model_call_id",
            "evidence",
        }
        for item in observation["evidence"]:
            assert set(item) <= {
                "evidence_ordinal",
                "page_number",
                "quote",
                "char_start",
                "char_end",
                "block_id",
            }
            assert {"evidence_ordinal", "page_number", "quote", "char_start", "char_end"} <= set(
                item
            )


def test_the_model_call_record_carries_the_declared_provenance(
    text_layer_document, recorded_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    record = outcome.model_calls[0].as_dict()
    assert set(record) == {
        "model_call_id",
        "provider",
        "model_id",
        "provider_mode",
        "parameters",
        "request_sha256",
        "response_sha256",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "status",
        "cost_usd",
    }
    assert record["provider"] == "anthropic"
    assert record["provider_mode"] == "recorded"
    assert len(record["request_sha256"]) == 64
    assert len(record["response_sha256"]) == 64
    # The record carries parameters, not the prompt. A prompt in a persisted record
    # is document content in a place nobody expects to find it.
    rendered = json.dumps(record, ensure_ascii=False)
    assert "Степень" not in rendered
    assert "Ты — инструмент" not in rendered
