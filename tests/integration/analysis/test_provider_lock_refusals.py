"""``analysis.text.lock`` and ``analysis.text.config``: the pinned-model refusals.

`W10-ANL` mutation sweep, rows LK-01, LK-02, LK-03, LK-04 and CF-04. Disabling
`ProviderLock.model`'s `KeyError` branch, changing its `reason` from `model_not_pinned`,
disabling the no-primary-model refusal, disabling `ModelPin.cost_usd`'s negative-token
refusal and deleting the `resolved_lock.model(model_id)` call from `load_provider_config`
were each green across `tests/integration/analysis_engine`,
`tests/integration/analysis_text` and `tests/replay`.

The dispatch asked directly whether that refusal is reachable and whether it is asserted by
its own rule. It is reachable, it was asserted by nothing, and it is asserted here by its
`reason`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.analysis.text.config import load_provider_config
from auditmanager.analysis.text.lock import (
    ModelPin,
    load_provider_lock,
    provider_lock,
)
from auditmanager.shared.errors import DomainError, ErrorCode

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = REPO_ROOT / "docs" / "program" / "P02_LOCK.json"

#: Pinned as literals. The authority is `docs/program/P02_LOCK.json`, read below and
#: compared against them, so a lock edit that is not mirrored here is a red test.
PRIMARY_MODEL_ID = "claude-opus-5"
CHEAPER_MODEL_ID = "claude-sonnet-5"
PRIMARY_INPUT_PER_MTOK_USD = 5.0
PRIMARY_OUTPUT_PER_MTOK_USD = 25.0


def test_the_lock_document_still_says_what_this_file_pins() -> None:
    """The literals above against the authority, so the rest of the file means something."""
    document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    models = document["models"]
    assert models["primary"]["model_id"] == PRIMARY_MODEL_ID
    assert models["cheaper_tier"]["model_id"] == CHEAPER_MODEL_ID
    assert models["primary"]["input_per_mtok_usd"] == PRIMARY_INPUT_PER_MTOK_USD
    assert models["primary"]["output_per_mtok_usd"] == PRIMARY_OUTPUT_PER_MTOK_USD


def test_the_loaded_lock_carries_exactly_the_two_pinned_identities() -> None:
    lock = provider_lock()
    assert set(lock.models) == {PRIMARY_MODEL_ID, CHEAPER_MODEL_ID}
    assert lock.primary_model_id == PRIMARY_MODEL_ID


def test_an_unpinned_model_identity_is_refused_by_model_not_pinned() -> None:
    """LK-01 and LK-02. The refusal fires, and it is *that* refusal."""
    lock = provider_lock()
    with pytest.raises(DomainError) as raised:
        lock.model("claude-opus-4")
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    # Field is not reason: assert the rule, not that something refused.
    assert error.detail_fields["reason"] == "model_not_pinned"
    assert error.detail_fields["stage_id"] == "text_analysis"


def test_the_refusal_names_no_model_identifier_it_was_not_given() -> None:
    lock = provider_lock()
    with pytest.raises(DomainError) as raised:
        lock.model("gpt-4o")
    assert "gpt-4o" not in str(raised.value)


def test_a_pinned_identity_is_not_refused() -> None:
    """The negative half: the guard admits what the lock pins."""
    lock = provider_lock()
    assert lock.model(PRIMARY_MODEL_ID).model_id == PRIMARY_MODEL_ID
    assert lock.model(CHEAPER_MODEL_ID).model_id == CHEAPER_MODEL_ID


def test_a_lock_declaring_no_primary_model_is_refused(tmp_path: Path) -> None:
    """LK-03. Built in the test; no corpus byte is added anywhere."""
    document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    document["models"] = {
        "cheaper_tier": document["models"]["cheaper_tier"],
        "$comment": document["models"]["$comment"],
    }
    variant = tmp_path / "P02_LOCK_no_primary.json"
    variant.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DomainError) as raised:
        load_provider_lock(variant)
    assert raised.value.code is ErrorCode.INTERNAL_ERROR
    assert "primary" in str(raised.value)


def test_an_annotation_key_is_skipped_rather_than_parsed_as_a_model(tmp_path: Path) -> None:
    """`$comment` and any future annotation key must not become a pin."""
    document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    document["models"]["$future_note"] = "not a model entry"
    variant = tmp_path / "P02_LOCK_annotated.json"
    variant.write_text(json.dumps(document), encoding="utf-8")

    lock = load_provider_lock(variant)
    assert set(lock.models) == {PRIMARY_MODEL_ID, CHEAPER_MODEL_ID}


def test_an_unreadable_lock_document_names_no_path(tmp_path: Path) -> None:
    with pytest.raises(DomainError) as raised:
        load_provider_lock(tmp_path / "absent.json")
    error = raised.value
    assert error.code is ErrorCode.INTERNAL_ERROR
    assert str(tmp_path) not in str(error)
    assert "absent.json" not in str(error)


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens"),
    [(-1, 0), (0, -1), (-3, -7)],
)
def test_a_negative_token_count_is_refused_by_cost_usd(
    input_tokens: int, output_tokens: int
) -> None:
    """LK-04. `ModelPin.cost_usd` refuses rather than returning a negative cost."""
    pin = ModelPin(
        model_id=PRIMARY_MODEL_ID,
        input_per_mtok_usd=PRIMARY_INPUT_PER_MTOK_USD,
        output_per_mtok_usd=PRIMARY_OUTPUT_PER_MTOK_USD,
    )
    with pytest.raises(ValueError, match="must not be negative"):
        pin.cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)


def test_cost_is_the_pinned_rate_per_million_tokens() -> None:
    """The arithmetic against literals, not against the module's own constants.

    1_000_000 input tokens at 5.0 USD/Mtok and 1_000_000 output tokens at 25.0 USD/Mtok
    is 30.0 USD. Both numbers are written here; neither is imported.
    """
    pin = ModelPin(
        model_id=PRIMARY_MODEL_ID,
        input_per_mtok_usd=PRIMARY_INPUT_PER_MTOK_USD,
        output_per_mtok_usd=PRIMARY_OUTPUT_PER_MTOK_USD,
    )
    assert pin.cost_usd(input_tokens=1_000_000, output_tokens=1_000_000) == 30.0
    assert pin.cost_usd(input_tokens=0, output_tokens=0) == 0.0


def test_configuration_refuses_an_unpinned_model_before_the_run_starts() -> None:
    """CF-04. The refusal at the configuration call site, by its own reason."""
    with pytest.raises(DomainError) as raised:
        load_provider_config(
            {
                "AUDITMANAGER_PROVIDER_MODE": "recorded",
                "AUDITMANAGER_MODEL_ID": "claude-opus-4",
            }
        )
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["reason"] == "model_not_pinned"


def test_configuration_accepts_a_pinned_model() -> None:
    config = load_provider_config(
        {
            "AUDITMANAGER_PROVIDER_MODE": "recorded",
            "AUDITMANAGER_MODEL_ID": CHEAPER_MODEL_ID,
        }
    )
    assert config.model_id == CHEAPER_MODEL_ID
