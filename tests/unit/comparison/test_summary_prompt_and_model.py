"""`COMPARE-PERSISTED-SUMMARY-01` (B2): the request is a pure function of the input; the recorded model
answers only the request it was recorded for and never calls anything."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.comparison import approved_evidence as evidence
from auditmanager.comparison import summary_model as model
from auditmanager.comparison.summary_input import prepare_version_summary_input
from auditmanager.comparison.summary_prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_request,
    canonical_json,
)
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts
from auditmanager.shared.errors import DomainError, ErrorCode

PROJECT = "prj_01M2545JSD15ETSNNV904XG001"
DOCUMENT = "doc_01M2545JSD15ETSNNV904XG001"
V1 = "ver_01M2545JSD15ETSNNV904XG001"
V2 = "ver_01M2545JSD15ETSNNV904XG002"
CMP = "cmp_01M2545JSD15ETSNNV904XG001"
LINK = "sln_01M2545JSD15ETSNNV904XG001"
SOURCE = {1: "общие данные\n", 2: "план\nразмер 30\n"}
TARGET = {1: "общие данные\n", 2: "план\nразмер 35\n"}


def _pair() -> OrderedVersionPair:
    def facts(uid: str, ordinal: int, sha: str) -> VersionFacts:
        return VersionFacts(uid, DOCUMENT, PROJECT, ordinal, sha, 4096, 2, "application/pdf")

    return OrderedVersionPair(PROJECT, DOCUMENT, facts(V1, 1, "a" * 64), facts(V2, 2, "b" * 64))


def _input(target=TARGET):
    pair = _pair()
    diffs, seal = evidence.raw_artifact(
        pair=pair, comparison_id=CMP, link_revision=1, links=[(LINK, 2, 2)],
        source_pages=SOURCE, target_pages=target,
    )
    return prepare_version_summary_input(version_pair=pair, raw_diffs=diffs, raw_seal=seal)


def test_the_request_is_a_pure_function_of_the_input() -> None:
    first, second = build_request(_input()), build_request(_input())
    assert first.request_sha256 == second.request_sha256
    assert canonical_json(first.body) == canonical_json(second.body)
    assert first.body["prompt_version"] == PROMPT_VERSION and first.body["instructions"] == SYSTEM_PROMPT
    assert first.hunk_ids == (f"{LINK}:0",)
    change = first.body["sheets"][0]["changes"][0]
    assert change["hunk_id"] == f"{LINK}:0"
    assert change["before"] == ["размер 30\n"] and change["after"] == ["размер 35\n"]
    # a request carries no identity of the run, the actor or the time
    assert "actor" not in canonical_json(first.body) and "run_id" not in canonical_json(first.body)


def test_another_input_is_another_key() -> None:
    changed = build_request(_input(TARGET | {2: "план\nразмер 36\n"}))
    assert changed.request_sha256 != build_request(_input()).request_sha256
    assert changed.input_sha256 != build_request(_input()).input_sha256


def _recording(directory: Path, request, reply: str = '{"statements": []}', **changes) -> Path:
    document = model.recording_document(
        request=request, output_text=reply, input_tokens=10, output_tokens=5,
        note="test", origin={"kind": "synthetic"},
    ) | changes
    path = directory / f"{request.request_sha256}.json"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def test_the_recorded_model_replays_only_the_request_it_was_recorded_for(tmp_path: Path) -> None:
    request = build_request(_input())
    _recording(tmp_path, request, reply="ответ")
    recorded = model.RecordedSummaryModel(tmp_path)
    reply = recorded.complete(request)
    assert (reply.output_text, reply.input_tokens, reply.output_tokens) == ("ответ", 10, 5)
    other = build_request(_input(TARGET | {2: "план\nразмер 36\n"}))
    with pytest.raises(DomainError) as refused:
        recorded.complete(other)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields["reason"] == "recording_missing"


@pytest.mark.parametrize(("changes", "reason"), [
    ({"request_sha256": "0" * 64}, "recording_key_mismatch"),
    ({"input_sha256": "0" * 64}, "recording_key_mismatch"),
    ({"recording_version": "9.9.9"}, "recording_version_unsupported"),
    ({"provider_mode": "live"}, "recording_malformed"),
    ({"usage": {"input_tokens": "x"}}, "recording_malformed"),
])
def test_a_defective_recording_is_an_explicit_refusal(tmp_path: Path, changes: dict, reason: str) -> None:
    request = build_request(_input())
    _recording(tmp_path, request, **changes)
    with pytest.raises(DomainError) as refused:
        model.RecordedSummaryModel(tmp_path).complete(request)
    assert refused.value.detail_fields["reason"] == reason


def test_a_recording_that_is_not_json_is_malformed(tmp_path: Path) -> None:
    request = build_request(_input())
    (tmp_path / f"{request.request_sha256}.json").write_text("{", encoding="utf-8")
    with pytest.raises(DomainError) as refused:
        model.RecordedSummaryModel(tmp_path).complete(request)
    assert refused.value.detail_fields["reason"] == "recording_malformed"


def test_a_recording_cannot_claim_a_provider_mode() -> None:
    request = build_request(_input())
    with pytest.raises(ValueError):
        model.recording_document(
            request=request, output_text="x", input_tokens=1, output_tokens=1, note="n",
            origin={"provider_mode": "live"},
        )


def test_the_mode_is_a_class_constant_and_the_class_holds_no_network_code() -> None:
    recorded = model.RecordedSummaryModel()
    assert (recorded.provider_mode, recorded.model_identity, recorded.unmetered) == (
        "recorded", "recorded", True,
    )
    with pytest.raises(AttributeError):
        recorded.provider_mode = "live"  # type: ignore[misc]
    source = Path(model.__file__).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import httpx", "import urllib", "import socket", "http.client"):
        assert forbidden not in source
    assert isinstance(recorded, model.SummaryModel)
