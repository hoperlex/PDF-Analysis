"""Every ``StageResult`` this package emits validates against the frozen schema.

Scope, stated because its absence is evidence: this task constructs **no**
``ResultPackage`` and **no** ``JobPackage``, so neither is emitted or validated here.
``test_no_package_envelope_is_constructed`` asserts that absence rather than leaving
it to be inferred from a suite that simply does not mention them.

The two rejection cases are the point of the suite. A ``succeeded`` result carrying an
error and a ``failed`` result missing one must both be *rejected by the schema*; if
either were accepted, the fail-closed status mapping would be unenforceable at the
seam no matter how carefully this package behaved.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.engine.registry import StageRegistry, default_registry
from auditmanager.analysis.engine.result import (
    CONTRACT_VERSION,
    ArtifactRef,
    StageError,
    StageResult,
    StageStatus,
)
from auditmanager.analysis.engine.runner import assert_status_allowed
from auditmanager.shared.errors import DomainError, ErrorCode

#: The three stages this task owns.
PREPARATION_STAGES = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
)

_BLOB = "blob_J6VNHEG0551A6NP75YJQ23CSCX"
_SHA = "2cc895a80100e5b53610183aac08a4b07ee5e7f446d0ab5d78c2d0101ebc9d20"


def _artifact(role: str) -> ArtifactRef:
    return ArtifactRef(
        role=role,
        blob_id=_BLOB,
        sha256=_SHA,
        size_bytes=4096,
        media_type="application/json",
    )


def _succeeded(stage_id: str, registry: StageRegistry) -> StageResult:
    definition = registry.stage(stage_id)
    return StageResult(
        stage_id=stage_id,
        stage_version=definition.stage_version,
        status=StageStatus.SUCCEEDED,
        artifacts=tuple(_artifact(role) for role in definition.required_output_roles),
        metrics={"page_count": 8, "duration_ms": 1840},
    )


def _failed(stage_id: str, registry: StageRegistry) -> StageResult:
    return StageResult(
        stage_id=stage_id,
        stage_version=registry.stage(stage_id).stage_version,
        status=StageStatus.FAILED,
        artifacts=(),
        metrics={"duration_ms": 3},
        error=StageError(
            code=ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a required stage input was not supplied",
            retryable=ErrorCode.ANALYSIS_INPUT_INVALID.retryable,
            details={"stage_id": stage_id, "reason": "missing_required_input"},
        ),
    )


# --- the emitted shapes ------------------------------------------------------


def test_succeeded_results_validate(stage_result_schema: Any, validate: Any) -> None:
    registry = default_registry()
    cases = [
        {"name": stage_id, "payload": _succeeded(stage_id, registry).to_document()}
        for stage_id in PREPARATION_STAGES
    ]
    results = validate(stage_result_schema, cases)
    for stage_id in PREPARATION_STAGES:
        assert results[stage_id]["valid"], results[stage_id]["messages"]


def test_failed_results_validate(stage_result_schema: Any, validate: Any) -> None:
    registry = default_registry()
    cases = [
        {"name": stage_id, "payload": _failed(stage_id, registry).to_document()}
        for stage_id in PREPARATION_STAGES
    ]
    results = validate(stage_result_schema, cases)
    for stage_id in PREPARATION_STAGES:
        assert results[stage_id]["valid"], results[stage_id]["messages"]


def test_contract_examples_agree_with_the_schema(
    stage_result_schema: Any, contract_examples: Any, validate: Any
) -> None:
    """The contract's own examples, so this suite is pinned to the frozen file."""
    cases = [
        {"name": name, "payload": payload}
        for name, payload in contract_examples.items()
    ]
    results = validate(stage_result_schema, cases)
    for name, result in results.items():
        expected_valid = ".invalid." not in name
        assert result["valid"] is expected_valid, (name, result["messages"])


# --- the two rejections the task names ---------------------------------------


def test_succeeded_carrying_an_error_is_rejected(
    stage_result_schema: Any, validate: Any
) -> None:
    """A success that also explains a failure is not a shape the seam admits."""
    payload = _succeeded("source_preparation", default_registry()).to_document()
    payload["error"] = {
        "code": "analysis_failed",
        "message": "smuggled onto a success",
        "retryable": False,
    }
    results = validate(stage_result_schema, [{"name": "case", "payload": payload}])
    assert not results["case"]["valid"]


def test_succeeded_carrying_a_null_error_is_rejected(
    stage_result_schema: Any, validate: Any
) -> None:
    """``null`` is not "no error": it still satisfies ``required``.

    This is why :meth:`StageResult.to_document` omits the key rather than writing
    ``None``, and this case is what makes that decision load-bearing rather than
    stylistic.
    """
    payload = _succeeded("source_preparation", default_registry()).to_document()
    payload["error"] = None
    results = validate(stage_result_schema, [{"name": "case", "payload": payload}])
    assert not results["case"]["valid"]


def test_failed_missing_an_error_is_rejected(
    stage_result_schema: Any, validate: Any
) -> None:
    payload = _failed("source_preparation", default_registry()).to_document()
    del payload["error"]
    results = validate(stage_result_schema, [{"name": "case", "payload": payload}])
    assert not results["case"]["valid"]


def test_an_artifact_reference_carrying_an_object_key_is_rejected(
    stage_result_schema: Any, validate: Any
) -> None:
    """``additionalProperties: false`` on the artifact is what keeps a key out."""
    payload = _succeeded("source_preparation", default_registry()).to_document()
    payload["artifacts"][0]["object_key"] = "bucket/prefix/object"
    results = validate(stage_result_schema, [{"name": "case", "payload": payload}])
    assert not results["case"]["valid"]


# --- constructor-level fail-closed -------------------------------------------


def test_the_value_type_refuses_a_succeeded_result_with_an_error() -> None:
    with pytest.raises(ValueError):
        StageResult(
            stage_id="source_preparation",
            stage_version="1.0.0",
            status=StageStatus.SUCCEEDED,
            error=StageError(
                code=ErrorCode.ANALYSIS_FAILED,
                message="x",
                retryable=False,
            ),
        )


def test_the_value_type_refuses_a_failed_result_without_an_error() -> None:
    with pytest.raises(ValueError):
        StageResult(
            stage_id="source_preparation",
            stage_version="1.0.0",
            status=StageStatus.FAILED,
        )


def test_succeeded_documents_omit_the_error_key_entirely() -> None:
    document = _succeeded("source_preparation", default_registry()).to_document()
    assert "error" not in document


def test_contract_version_is_the_frozen_one(stage_result_schema: Any) -> None:
    assert (
        stage_result_schema["properties"]["contract_version"]["const"]
        == CONTRACT_VERSION
    )


# --- partial and skipped are structurally impossible -------------------------


@pytest.mark.parametrize("stage_id", PREPARATION_STAGES)
def test_the_registry_denies_partial_and_skipped(stage_id: str) -> None:
    definition = default_registry().stage(stage_id)
    assert definition.partial_allowed is False
    assert definition.skip_allowed is False
    assert definition.succeeded_requires_all_required_outputs is True


@pytest.mark.parametrize("stage_id", PREPARATION_STAGES)
@pytest.mark.parametrize("status", [StageStatus.PARTIAL, StageStatus.SKIPPED])
def test_the_status_guard_refuses_what_the_policy_denies(
    stage_id: str, status: StageStatus
) -> None:
    definition = default_registry().stage(stage_id)
    with pytest.raises(DomainError) as raised:
        assert_status_allowed(definition, status)
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


@pytest.mark.parametrize("stage_id", PREPARATION_STAGES)
def test_the_status_guard_admits_what_the_policy_allows(stage_id: str) -> None:
    definition = default_registry().stage(stage_id)
    assert_status_allowed(definition, StageStatus.SUCCEEDED)
    assert_status_allowed(definition, StageStatus.FAILED)


def test_a_stage_production_cannot_express_a_status() -> None:
    """The structural half of the claim, asserted rather than described.

    A handler returns :class:`StageProduction`. If that type ever gains a status,
    degraded or partial field, the runner's two-outcome mapping stops being
    structural and this test is where that change is noticed.
    """
    from auditmanager.analysis.ports.stage import StageProduction

    fields = set(StageProduction.__dataclass_fields__)
    assert fields == {"artifacts", "metrics"}


# --- no dispatch envelope ----------------------------------------------------


def test_no_package_envelope_is_constructed() -> None:
    """PC-01 does not dispatch remotely, so this package builds neither envelope.

    Asserted over the package's own source rather than over its public names: the
    claim is that nothing here constructs or defines one at all, not merely that
    nothing exports one. Docstring prose explaining the absence is not a
    construction, so the check looks for a definition or a call.
    """
    import pathlib

    import auditmanager.analysis as analysis

    package_root = pathlib.Path(analysis.__file__).parent
    offenders = []
    for path in sorted(package_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name in ("JobPackage", "ResultPackage"):
            if f"class {name}" in text or f"{name}(" in text:
                offenders.append(f"{path.name} defines or calls {name}")
    assert not offenders, offenders


def test_the_stage_seam_carries_no_attempt_authority() -> None:
    """The runner requires no attempt authority, so its context has nowhere to hold one."""
    from auditmanager.analysis.ports.stage import StageContext

    fields = set(StageContext.__dataclass_fields__)
    assert fields == {"definition", "version_uid", "inputs", "blob_store"}
    forbidden = {"attempt_id", "execution_token", "lease_id", "worker_id", "authority"}
    assert not fields & forbidden


# --- the registry loader -----------------------------------------------------


def test_the_registry_refuses_an_unknown_stage() -> None:
    with pytest.raises(DomainError) as raised:
        default_registry().stage("not_a_declared_stage")
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_the_registry_refuses_a_legacy_alias() -> None:
    """The engine never accepts a legacy name; resolution is the control plane's job.

    ``pdf_text_extraction`` is a legacy declaration name from the pinned inventory. It
    is not a canonical ``stage_id``, and the registry holds no alias table to turn it
    into one.
    """
    for legacy in ("pdf_text_extraction", "prepare_source", "build_context"):
        with pytest.raises(DomainError):
            default_registry().stage(legacy)


def test_stage_identity_and_version_come_from_the_contract() -> None:
    """``GJ-02-EO-11``: identity comes only from the versioned registry."""
    import json

    from auditmanager.analysis.engine.registry import CONTRACT_PATH

    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    declared = {
        entry["stage_id"]: entry["stage_version"] for entry in document["stages"]
    }
    registry = default_registry()
    for stage_id, stage_version in declared.items():
        assert registry.stage(stage_id).stage_version == stage_version
    assert registry.stage_ids == frozenset(declared)


def test_a_registry_document_of_another_contract_is_refused() -> None:
    with pytest.raises(DomainError) as raised:
        StageRegistry({"contract": "something.else", "stages": []})
    assert raised.value.code is ErrorCode.UNSUPPORTED_CONTRACT_VERSION


def test_an_unimplemented_declared_stage_is_refused_not_defaulted() -> None:
    """A declared stage with no implementation must raise, never no-op to success."""
    from auditmanager.analysis.stages import handler_for

    with pytest.raises(DomainError) as raised:
        handler_for("text_analysis")
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


# --- error details stay inside the catalog's safety rules --------------------


def test_error_details_are_narrowed_to_the_catalog_safe_keys() -> None:
    """A detail the catalog does not declare safe for the code is dropped, not shipped."""
    error = DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="refused",
        stage_id="source_preparation",
        reason="missing_required_input",
        object_key="bucket/prefix/object",
    )
    carried = StageError.from_domain_error(error)
    assert set(carried.details) == {"stage_id", "reason"}
    assert "object_key" not in carried.details


def test_retryable_is_read_from_the_catalog_not_chosen() -> None:
    error = DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message="refused")
    carried = StageError.from_domain_error(error)
    assert carried.retryable is ErrorCode.ANALYSIS_INPUT_INVALID.retryable


# --- the declared normalization actually normalizes ---------------------------


def test_the_declared_normalization_composes_decomposed_text() -> None:
    """``nfc_v1`` is applied, not merely declared.

    The corpus is already NFC, so no assertion over its published text can tell an
    applied normalization from an identity function. This one can: it feeds
    decomposed Cyrillic - ``и`` followed by a combining breve, which is how ``й`` can
    be spelled - through the same function ``source_preparation`` uses, and requires
    it to come back composed.

    It matters because ``B4``'s grounding gate compares exactly, after this one
    normalization and nothing else. If the text layer kept a decomposed spelling, a
    model quoting the composed one would be judged ungrounded on a difference no
    reader can see.
    """
    from auditmanager.analysis.stages.extraction import NORMALIZATION_ID, normalize

    decomposed = "й"  # и + combining breve
    composed = "й"  # й

    assert decomposed != composed
    assert normalize(decomposed) == composed
    assert normalize(composed) == composed
    assert NORMALIZATION_ID == "nfc_v1"


def test_normalization_does_not_case_fold_or_collapse_whitespace() -> None:
    """The declared description promises exactly NFC and nothing else."""
    from auditmanager.analysis.stages.extraction import (
        NORMALIZATION_DESCRIPTION,
        normalize,
    )

    sample = "СТЕПЕНЬ  огнестойкости\tзданий — II.\n"
    assert normalize(sample) == sample
    assert "No case folding" in NORMALIZATION_DESCRIPTION
    assert "no whitespace collapsing" in NORMALIZATION_DESCRIPTION
