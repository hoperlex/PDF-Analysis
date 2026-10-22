"""`W59-ANALYSIS-SETTINGS-01`, `SECTION-RECORDINGS-01`: the synthetic section recordings and how the
recorded adapter finds them.

Container-free. What is held here:

* every section with a registered profile but AR -- АИ, ПЗ, ПОС, ТХ, КЖ, КМ, ОВ, ВК, ПТ, ЭОМ, СС,
  ИТП, ГП and ПБ, fourteen -- has exactly one recording, filed under the key of the request its own
  profile sends over the committed AR corpus text layer, labelled synthetic in its ``origin`` and
  carrying no provider mode; the builder reports no drift; a profile added to the registry without
  a recording fails here;
* the fourteen keys differ from each other and from AR's, so no recording can answer another
  profile's request;
* ``RecordedAdapter()`` (what the composition root serves) answers AR exactly as the
  canonical directory does and answers each recorded section; an adapter given one directory
  reads only that directory;
* each section's request is refused by every other section's directory, by the canonical AR
  directory and by an empty one (``recording_missing``), and by its own reply filed under another
  key (``recording_key_mismatch``); the same holds through the real stage, which fails closed with
  no artifact;
* every section's recording replays through the real stage with that section's own profile and
  publishes exactly the observations it holds, grounded in the corpus text;
* one key in two searched directories is refused, never answered by directory order;
* the registry keeps each package's ``source`` block (AR, written here, and an authored package
  such as ПБ's have none).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from auditmanager.analysis.text import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    run_text_analysis,
)
from auditmanager.analysis.text import recorded as recorded_module
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.adapter import ModelRequest, build_request
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE
from auditmanager.analysis.text.profile_registry import (
    AUTHORED_SECTIONS,
    PACKAGES_ROOT,
    TextProfileSource,
    TextProfileSourceFile,
    load_text_profile_registry,
)
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANONICAL = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"
SECTIONS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections"
TEXT_LAYER = CANONICAL / "inputs" / "ar_baseline_text_layer.json"
MODEL_ID = "claude-opus-5"
#: The first four came with `W59-ANALYSIS-SETTINGS-01`; the other ten with `SECTION-RECORDINGS-01`.
FIRST_FOUR = ("AI", "PS", "POS", "TX")
RECORDED_SECTIONS = (
    *FIRST_FOUR, "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP", "PB",
)
TASK_OF = {
    code: "W59-ANALYSIS-SETTINGS-01" if code in FIRST_FOUR else "SECTION-RECORDINGS-01"
    for code in RECORDED_SECTIONS
}
REGISTRY = load_text_profile_registry()


def _request(code: str) -> ModelRequest:
    bundle = (
        AR_TEXT_PROFILE.prompt_bundle if code == "AR"
        else REGISTRY.entries[code].profile.prompt_bundle
    )
    layer = load_text_layer(json.loads(TEXT_LAYER.read_text(encoding="utf-8")))
    return build_request(model_id=MODEL_ID, bundle=bundle, text_layer=layer)


def _reason(adapter: RecordedAdapter, request: ModelRequest) -> str:
    with pytest.raises(DomainError) as refused:
        adapter.complete(request)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.code.retryable is False
    return str(refused.value.detail_fields["reason"])


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_each_section_has_one_synthetic_recording_keyed_to_its_own_request(code: str) -> None:
    request = _request(code)
    directory = SECTIONS / code.lower()
    assert sorted(item.name for item in directory.iterdir()) == [f"{request.request_sha256}.json"]
    document = json.loads((directory / f"{request.request_sha256}.json").read_text(encoding="utf-8"))
    assert document["request_sha256"] == request.request_sha256
    assert document["model_id"] == MODEL_ID

    entry = REGISTRY.entries[code]
    origin = document["origin"]
    assert origin["kind"] == "synthetic"
    assert "No model produced this reply" in origin["statement"]
    assert "Not field evidence" in origin["statement"]
    assert origin["task_id"] == TASK_OF[code]
    assert f"authored by hand for {TASK_OF[code]}" in origin["statement"]
    assert origin["section_code"] == code
    assert origin["analysis_profile_id"] == entry.analysis_profile_id
    assert origin["prompt_bundle_id"] == entry.prompt_bundle_id
    assert origin["prompt_bundle_sha256"] == entry.profile.prompt_bundle.content_sha256
    for mapping in (document, origin):
        assert not {"provider_mode", "mode"} & set(mapping)

    observations = json.loads(document["output_text"])["observations"]
    assert observations
    assert all(item["finding_text"].startswith("Синтетический ответ (") for item in observations)


def test_the_requests_are_pairwise_distinct_and_none_is_ars() -> None:
    keys = [_request(code).request_sha256 for code in ("AR", *RECORDED_SECTIONS)]
    assert len(set(keys)) == len(keys)


def test_the_builder_reports_no_drift() -> None:
    completed = subprocess.run(
        [sys.executable, str(SECTIONS / "build_fixtures.py"), "--check"],
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "fixtures match"


def test_the_builder_plans_exactly_the_recorded_sections() -> None:
    """`--check` only looks at what the builder plans, so a section dropped from the builder (and
    its recording left behind or never made) would pass it: the plan itself is held here."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "section_recordings_builder", SECTIONS / "build_fixtures.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    path_before = list(sys.path)
    try:
        spec.loader.exec_module(module)  # inserts the repository's src on sys.path
        planned = module.plan()
    finally:
        sys.path[:] = path_before
    assert len(planned) == len(RECORDED_SECTIONS) == 14
    assert {path.parent.name for path, _ in planned} == {code.lower() for code in RECORDED_SECTIONS}
    assert {document["origin"]["section_code"] for _, document in planned} == set(RECORDED_SECTIONS)
    assert {document["origin"]["task_id"] for _, document in planned} == set(TASK_OF.values())


def test_the_served_adapter_answers_ar_exactly_as_the_canonical_directory() -> None:
    served = RecordedAdapter()
    assert served.recording_dir == CANONICAL
    assert served.recording_dirs == (
        CANONICAL,
        # `ar_specification` is the recorded AR reply for the Form-7 specification bundle
        # (`SPEC-TABLE-RECORDING-01`); it is searched like a section directory but is not a section.
        *(SECTIONS / name for name in sorted([code.lower() for code in RECORDED_SECTIONS] + ["ar_specification"])),
    )
    request = _request("AR")
    assert served.complete(request) == RecordedAdapter(CANONICAL).complete(request)
    assert RecordedAdapter(CANONICAL).recording_dirs == (CANONICAL,)


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not(
    code: str,
) -> None:
    request = _request(code)
    document = json.loads(
        (SECTIONS / code.lower() / f"{request.request_sha256}.json").read_text(encoding="utf-8")
    )
    response = RecordedAdapter().complete(request)
    assert response.output_text == document["output_text"]
    assert response.input_tokens == document["usage"]["input_tokens"]
    assert _reason(RecordedAdapter(CANONICAL), request) == "recording_missing"


def test_every_registered_section_has_a_recording_and_nothing_else_does() -> None:
    """A profile added to the registry without a recording (or the reverse) fails here."""
    assert set(REGISTRY.entries) == {"AR", *RECORDED_SECTIONS}
    assert len(RECORDED_SECTIONS) == 14 == len(set(RECORDED_SECTIONS))
    directories = {
        item.name for item in SECTIONS.iterdir()
        if item.is_dir() and not item.name.startswith(("_", "."))
    }
    assert directories == {code.lower() for code in RECORDED_SECTIONS} | {"ar_specification"}


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_a_section_without_a_recording_fails_explicitly(code: str, tmp_path: Path) -> None:
    """The seam for "no recording" is an empty directory: every section has one on disk now."""
    assert _reason(RecordedAdapter(tmp_path), _request(code)) == "recording_missing"


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_no_other_directory_answers_a_section_request(code: str) -> None:
    """A recording for one section never answers another section's request."""
    request = _request(code)
    assert _reason(RecordedAdapter(CANONICAL), request) == "recording_missing"
    foreign = [other for other in RECORDED_SECTIONS if other != code]
    assert len(foreign) == 13
    for other in foreign:
        assert _reason(RecordedAdapter(SECTIONS / other.lower()), request) == "recording_missing", (
            code, other,
        )
    # And the section's own directory is the only one that does answer it.
    assert RecordedAdapter(SECTIONS / code.lower()).complete(request).output_text


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_a_section_reply_filed_under_another_key_is_not_replayed(code: str, tmp_path: Path) -> None:
    own = _request(code)
    other_code = next(candidate for candidate in RECORDED_SECTIONS if candidate != code)
    other = _request(other_code)
    forged = tmp_path / "forged"
    forged.mkdir()
    shutil.copyfile(
        SECTIONS / code.lower() / f"{own.request_sha256}.json",
        forged / f"{other.request_sha256}.json",
    )
    assert _reason(RecordedAdapter(forged), other) == "recording_key_mismatch"


# --- the real stage, with each section's own profile ---------------------------------------


def _stage(code: str, adapter: RecordedAdapter):
    return run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=json.loads(TEXT_LAYER.read_text(encoding="utf-8")),
        adapter=adapter,
        profile=REGISTRY.entries[code].profile,
        config=ProviderConfig(
            mode=ProviderMode.RECORDED, model_id=MODEL_ID, run_cost_ceiling_usd=1.00,
            api_key=None, ceiling_is_explicit=True,
        ),
    )


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_each_recording_replays_through_the_stage_under_its_own_profile(code: str) -> None:
    entry = REGISTRY.entries[code]
    request = _request(code)
    document = json.loads(
        (SECTIONS / code.lower() / f"{request.request_sha256}.json").read_text(encoding="utf-8")
    )
    expected = json.loads(document["output_text"])["observations"]

    outcome = _stage(code, RecordedAdapter())

    assert outcome.status == STATUS_SUCCEEDED, outcome.error
    artifact = outcome.artifact
    assert artifact["provider_mode"] == "recorded"
    assert artifact["analysis_profile_id"] == entry.analysis_profile_id
    assert artifact["prompt_bundle_id"] == entry.prompt_bundle_id
    assert outcome.metrics["request_sha256"] == request.request_sha256
    assert outcome.metrics["prompt_bundle_sha256"] == entry.profile.prompt_bundle.content_sha256
    # Grounded in the corpus text: every authored quote resolved to the page it names.
    assert outcome.metrics["observations_proposed"] == len(expected)
    assert outcome.metrics["observations_emitted"] == len(expected)
    assert outcome.metrics["evidence_unresolved"] == 0
    assert outcome.metrics["observations_dropped_unresolved"] == 0
    assert len(artifact["observations"]) == len(expected)
    assert all(
        item["finding_text"].startswith("Синтетический ответ (") for item in expected
    )


@pytest.mark.parametrize("code", RECORDED_SECTIONS)
def test_a_foreign_section_directory_fails_the_stage_closed_with_no_artifact(code: str) -> None:
    other = next(candidate for candidate in RECORDED_SECTIONS if candidate != code)
    outcome = _stage(code, RecordedAdapter(SECTIONS / other.lower()))

    assert outcome.status == STATUS_FAILED
    assert outcome.artifact is None
    assert outcome.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert outcome.error.detail_fields.get("reason") == "recording_missing"


def test_every_recording_carries_its_own_authored_usage_signature() -> None:
    """Fourteen replies, fourteen distinguishable ones: none could pass for another's.

    The figures are authored, not measured; they differ on purpose, so a run that consumed another
    section's recording would show another section's usage in its metrics.
    """
    signatures = set()
    for code in RECORDED_SECTIONS:
        request = _request(code)
        document = json.loads(
            (SECTIONS / code.lower() / f"{request.request_sha256}.json").read_text(encoding="utf-8")
        )
        signatures.add((
            document["usage"]["input_tokens"], document["usage"]["output_tokens"],
            document["latency_ms"],
        ))
    assert len(signatures) == len(RECORDED_SECTIONS)


def test_the_ai_recording_never_answers_the_ps_request(tmp_path: Path) -> None:
    ai, ps = _request("AI"), _request("PS")
    assert _reason(RecordedAdapter(SECTIONS / "ai"), ps) == "recording_missing"
    forged = tmp_path / "forged"
    forged.mkdir()
    shutil.copyfile(
        SECTIONS / "ai" / f"{ai.request_sha256}.json", forged / f"{ps.request_sha256}.json"
    )
    assert _reason(RecordedAdapter(forged), ps) == "recording_key_mismatch"


def test_one_key_in_two_searched_directories_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request("PS")
    source = SECTIONS / "ps" / f"{request.request_sha256}.json"
    canonical = tmp_path / "fixtures" / "recorded" / "text_analysis"
    section = tmp_path / "fixtures" / "recorded" / "sections" / "ps"
    for directory in (canonical, section):
        directory.mkdir(parents=True)
        shutil.copyfile(source, directory / source.name)
    (tmp_path / "fixtures" / "recorded" / "sections" / "README.md").write_text("x", encoding="utf-8")
    (tmp_path / "fixtures" / "recorded" / "sections" / "__pycache__").mkdir()
    monkeypatch.setattr(recorded_module, "_REPO_ROOT", tmp_path)

    served = RecordedAdapter()
    assert served.recording_dirs == (canonical, section)
    assert _reason(served, request) == "recording_ambiguous"
    # Each directory alone answers: the refusal is about the pair, not about either file.
    for directory in (canonical, section):
        assert RecordedAdapter(directory).complete(request).output_text


def test_a_recording_origin_cannot_carry_a_provider_mode() -> None:
    request = _request("AI")
    fields = dict(
        request=request, output_text="{}", stop_reason="end_turn", input_tokens=1,
        output_tokens=1, latency_ms=1, note="",
    )
    assert set(recording_document(**fields)) == {
        "recording_version", "request_sha256", "model_id", "stop_reason", "output_text",
        "usage", "latency_ms", "note",
    }
    for forged in ({"provider_mode": "live"}, {"kind": "synthetic", "mode": "live"}):
        with pytest.raises(ValueError):
            recording_document(**fields, origin=forged)


def test_the_registry_keeps_each_packages_source_block() -> None:
    assert REGISTRY.entries["AR"].source is None
    authored = set()
    for code, entry in REGISTRY.entries.items():
        if code == "AR":
            continue
        declared = json.loads((PACKAGES_ROOT / code.lower() / "profile.json").read_text(encoding="utf-8"))
        if declared["source"] is None:
            # An authored package (`PB-PROFILE-01`) declares no legacy source and the registry keeps none.
            assert entry.source is None, code
            authored.add(code)
            continue
        assert entry.source == TextProfileSource(
            repository=declared["source"]["repository"],
            commit=declared["source"]["commit"],
            files=tuple(
                TextProfileSourceFile(path=item["path"], sha256=item["sha256"])
                for item in declared["source"]["files"]
            ),
        )
    assert authored == set(AUTHORED_SECTIONS), "only the sections the loader declares authored"


def test_the_listing_order_is_the_webs_project_structure_order() -> None:
    """`listAnalysisProfiles` answers in ``PROJECT_STRUCTURE_ORDER``; the web titles the same
    order ``PROJECT_STRUCTURE_ORDER`` (``web/src/entities/project/model/section.ts``). Read from
    the source rather than restated, so the two literals cannot drift apart silently."""
    import re

    from auditmanager.analysis.text.profile_registry import (
        PROJECT_STRUCTURE_ORDER,
        SECTION_CODES,
    )

    source = (
        REPOSITORY_ROOT / "web" / "src" / "entities" / "project" / "model" / "section.ts"
    ).read_text(encoding="utf-8")
    block = re.search(
        r"export const PROJECT_STRUCTURE_ORDER: readonly ProjectSectionCode\[\] = \[(.*?)\];",
        source,
        re.DOTALL,
    )
    assert block is not None, "the web's PROJECT_STRUCTURE_ORDER literal was not found"
    web_order = tuple(re.findall(r"'([A-Z]+)'", block.group(1)))
    assert web_order == PROJECT_STRUCTURE_ORDER
    assert set(PROJECT_STRUCTURE_ORDER) == SECTION_CODES and len(PROJECT_STRUCTURE_ORDER) == 15
