"""``analysis.engine``: the status policy, the registry's contract identity, and the
contract shape of an ``ArtifactRef``.

`W10-ANL` mutation sweep, rows RN-01, RN-02, RN-05, RN-07, RN-10, RG-01, RG-03 and
RS-01 to RS-06. All green across `tests/integration/analysis_engine`,
`tests/integration/analysis_text` and `tests/replay`.

The dispatch asks about "the fail-closed status mapping" and whether every status is now
mapped by something that would notice a changed mapping. `test_fail_closed.py` covers the two
mappings the runner *produces* — a missing input and a missing output are both `failed`, and
it asserts the catalog code and the `reason`, which is exactly right. What nothing covered is
`assert_status_allowed`, the guard the runner's own docstring says exists so that "anything
that ever tries to is refused at the boundary rather than trusted because the runner is
believed not to". Disabling either of its branches, or deleting the call from `_result_for`
altogether, was green.

That guard is reachable from the public surface: `assert_status_allowed` is exported from
`analysis.engine.runner` and takes a `StageDefinition` and a `StageStatus`. No private
surface is touched here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.analysis.engine.registry import StageRegistry, default_registry
from auditmanager.analysis.engine.result import ArtifactRef, StageStatus
from auditmanager.analysis.engine.runner import assert_status_allowed
from auditmanager.shared.errors import DomainError, ErrorCode

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = REPO_ROOT / "contracts" / "analysis" / "v1" / "stage-registry.json"

#: Pinned literals. The authority is `contracts/analysis/v1/stage-registry.json`, read and
#: compared below, so a contract edit that is not mirrored here reddens.
EXPECTED_CONTRACT = "auditmanager.analysis.stage_registry"
CONTRACT_VERSION = "1.0.0-draft.1"
PREPARATION_STAGES = ("source_preparation", "page_geometry_extraction", "document_context_build")
BLOB_ID = "blob_01M2545JSD15ETSNNV904X991J"
SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# --- the contract is what this file claims ------------------------------------------


def test_the_contract_document_declares_the_pinned_identity() -> None:
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert document["contract"] == EXPECTED_CONTRACT
    assert document["contract_version"] == CONTRACT_VERSION


def test_no_preparation_stage_permits_skipped_or_partial() -> None:
    """Read from the contract, which is the only source of skippability (`GJ-02-EO-13`)."""
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    policies = {s["stage_id"]: s["status_policy"] for s in document["stages"]}
    for stage_id in PREPARATION_STAGES:
        assert policies[stage_id]["skip_allowed"] is False
        assert policies[stage_id]["partial_allowed"] is False


# --- RG-01: the registry refuses a document that is not the stage registry ------------


@pytest.mark.parametrize(
    "contract",
    [
        "auditmanager.analysis.stage_registry_v2",
        "auditmanager.findings.registry",
        "",
        None,
    ],
)
def test_a_document_declaring_another_contract_is_refused(contract: object) -> None:
    """RG-01. Nothing fed `StageRegistry` a wrong document before this."""
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract is None:
        del document["contract"]
    else:
        document["contract"] = contract
    with pytest.raises(DomainError) as raised:
        StageRegistry(document)
    assert raised.value.code is ErrorCode.UNSUPPORTED_CONTRACT_VERSION


def test_the_real_contract_document_is_accepted() -> None:
    """The negative half."""
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert StageRegistry(document).contract_version == CONTRACT_VERSION


def test_an_unknown_stage_is_refused_by_the_unknown_stage_rule() -> None:
    """RG-03. Asserts *which* rule refused, not that something did."""
    with pytest.raises(DomainError) as raised:
        default_registry().stage("text_analysis_v2")
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["reason"] == "unknown_stage"
    assert error.detail_fields["stage_id"] == "text_analysis_v2"


# --- RN-01, RN-02, RN-07: the status policy guard ------------------------------------


@pytest.mark.parametrize("stage_id", PREPARATION_STAGES)
def test_a_stage_the_registry_forbids_skipping_refuses_skipped(stage_id: str) -> None:
    """RN-01."""
    definition = default_registry().stage(stage_id)
    with pytest.raises(DomainError) as raised:
        assert_status_allowed(definition, StageStatus.SKIPPED)
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["reason"] == "skip_not_allowed"
    assert error.detail_fields["stage_id"] == stage_id


@pytest.mark.parametrize("stage_id", PREPARATION_STAGES)
def test_a_stage_the_registry_forbids_partiality_refuses_partial(stage_id: str) -> None:
    """RN-02. A different `reason` from RN-01, so the two cannot cover for each other."""
    definition = default_registry().stage(stage_id)
    with pytest.raises(DomainError) as raised:
        assert_status_allowed(definition, StageStatus.PARTIAL)
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["reason"] == "partial_not_allowed"


@pytest.mark.parametrize("stage_id", PREPARATION_STAGES)
@pytest.mark.parametrize("status", [StageStatus.SUCCEEDED, StageStatus.FAILED])
def test_the_two_statuses_the_runner_produces_are_always_allowed(
    stage_id: str, status: StageStatus
) -> None:
    """The negative half: the guard must not refuse what the runner legitimately builds."""
    assert_status_allowed(default_registry().stage(stage_id), status) is None


def test_text_analysis_may_report_partial_but_still_may_not_be_skipped() -> None:
    """The guard is per-stage, not a blanket refusal.

    `text_analysis` declares `partial_allowed: true` and `skip_allowed: false`. If the two
    branches were collapsed, or if either read the wrong flag, this test separates them.
    """
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    policy = {s["stage_id"]: s["status_policy"] for s in document["stages"]}["text_analysis"]
    assert policy["partial_allowed"] is True
    assert policy["skip_allowed"] is False

    definition = default_registry().stage("text_analysis")
    assert_status_allowed(definition, StageStatus.PARTIAL)  # permitted
    with pytest.raises(DomainError) as raised:
        assert_status_allowed(definition, StageStatus.SKIPPED)
    assert raised.value.detail_fields["reason"] == "skip_not_allowed"


# --- RS-01 to RS-05: ArtifactRef is contract-shaped ----------------------------------


def test_a_contract_shaped_artifact_reference_is_accepted() -> None:
    reference = ArtifactRef(
        role="prepared.text_layer",
        blob_id=BLOB_ID,
        sha256=SHA256,
        size_bytes=0,
        media_type="application/json",
    )
    assert reference.to_document()["blob_id"] == BLOB_ID


@pytest.mark.parametrize(
    "role",
    ["Prepared.text_layer", "prepared..text_layer", ".text_layer", "prepared.text-layer",
     "1prepared.text_layer", "", "prepared.text_layer."],
)
def test_an_artifact_role_that_is_not_contract_shaped_is_refused(role: str) -> None:
    """RS-02."""
    with pytest.raises(ValueError, match="not contract-shaped"):
        ArtifactRef(role=role, blob_id=BLOB_ID, sha256=SHA256, size_bytes=1,
                    media_type="application/json")


@pytest.mark.parametrize(
    "blob_id",
    ["blob_01M2545JSD15ETSNNV904X991", "01M2545JSD15ETSNNV904X991J", "",
     "blob_01M2545JSD15ETSNNV904X991I", "blob_01m2545jsd15etsnnv904x991j"],
)
def test_a_blob_id_that_is_not_contract_shaped_is_refused(blob_id: str) -> None:
    """RS-04. `I`, `L`, `O` and `U` are excluded from Crockford base32 on purpose."""
    with pytest.raises(ValueError, match="blob identifier"):
        ArtifactRef(role="prepared.text_layer", blob_id=blob_id, sha256=SHA256,
                    size_bytes=1, media_type="application/json")


@pytest.mark.parametrize(
    "digest",
    ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, SHA256.upper()],
)
def test_a_checksum_that_is_not_64_lowercase_hex_is_refused(digest: str) -> None:
    """RS-03."""
    with pytest.raises(ValueError, match="64 lowercase hex"):
        ArtifactRef(role="prepared.text_layer", blob_id=BLOB_ID, sha256=digest,
                    size_bytes=1, media_type="application/json")


@pytest.mark.parametrize("size", [-1, -1024])
def test_a_negative_size_is_refused(size: int) -> None:
    """RS-05."""
    with pytest.raises(ValueError, match="size_bytes may not be negative"):
        ArtifactRef(role="prepared.text_layer", blob_id=BLOB_ID, sha256=SHA256,
                    size_bytes=size, media_type="application/json")


def test_a_reference_carries_no_key_url_or_credential_field() -> None:
    """The freeze: content-addressed and nothing else."""
    document = ArtifactRef(
        role="prepared.text_layer", blob_id=BLOB_ID, sha256=SHA256, size_bytes=1,
        media_type="application/json",
    ).to_document()
    assert set(document) == {"role", "blob_id", "sha256", "size_bytes", "media_type"}
