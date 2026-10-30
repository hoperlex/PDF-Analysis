"""The temporary AR v3 choice is a durable group intent, never a worker default."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from auditmanager.api.schemas.models import StartArV3BetaGroupRequest
from auditmanager.ingest.public import CommandRepository, payload_fingerprint
from auditmanager.ingest.commands import CommandRecord
from auditmanager.runs import v3_group, v3_worker
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, IdempotencyKey


VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
COMMAND_ID = "cmd_01M25P3TH08VVTTGJRXYBZZ7RP"


def test_group_request_defaults_to_standard_and_accepts_only_an_explicit_boolean() -> None:
    assert StartArV3BetaGroupRequest.model_validate({"version_uid": VERSION}).relaxed_limits is None
    assert StartArV3BetaGroupRequest.model_validate({
        "version_uid": VERSION, "relaxed_limits": True,
    }).relaxed_limits is True
    with pytest.raises(ValidationError):
        StartArV3BetaGroupRequest.model_validate({
            "version_uid": VERSION, "relaxed_limits": "true",
        })


def test_existing_group_fingerprint_stays_replayable_but_a_changed_choice_conflicts() -> None:
    standard = v3_group._fingerprint(VERSION, "live", "a" * 64)
    assert standard == payload_fingerprint({
        "version_uid": VERSION, "provider_mode": "live", "pack_sha256": "a" * 64,
    })
    record = CommandRecord(
        command_id=CommandId.parse(COMMAND_ID),
        command_type=v3_group.COMMAND_TYPE,
        idempotency_key=IdempotencyKey("v3-relaxed-test"),
        payload_fingerprint=standard,
        state="succeeded",
        outcome={"group_id": "arg_01M25P3TH08VVTTGJRXYBZZ7RP"},
        error_code=None,
    )
    assert CommandRepository._answer_existing(record, standard).outcome == record.outcome
    with pytest.raises(DomainError) as conflict:
        CommandRepository._answer_existing(
            record, v3_group._fingerprint(VERSION, "live", "a" * 64, True),
        )
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


@pytest.mark.parametrize("outcome,expected", [
    ({"group_id": "old"}, False),
    ({"group_id": "new", "relaxed_limits": False}, False),
    ({"group_id": "new", "relaxed_limits": True}, True),
])
def test_worker_reads_saved_group_choice_and_old_groups_default_to_standard(
    monkeypatch, outcome, expected,
) -> None:
    class Commands:
        def get(self, _session, command_id):
            assert str(command_id) == COMMAND_ID
            return SimpleNamespace(
                command_type=v3_group.COMMAND_TYPE, state="succeeded", outcome=outcome,
            )

    monkeypatch.setattr(v3_worker, "CommandRepository", Commands)
    runs = SimpleNamespace(get=lambda _session, _run_id: SimpleNamespace(command_id=COMMAND_ID))
    assert v3_worker._relaxed_limits_for_run(None, "run_test", runs) is expected


def test_relaxed_group_skips_only_the_cost_derived_input_preflight(monkeypatch) -> None:
    class Commands:
        def find(self, *_args, **_kwargs):
            return None

        def begin(self, *_args, **_kwargs):
            pytest.fail("a failed precondition claimed the command key")

    version = SimpleNamespace(
        classification=SimpleNamespace(section_code="AR"),
        manifest=[SimpleNamespace(role=v3_group.MANIFEST_ROLE_SOURCE_DOCUMENT, blob_id="blob_test")],
        text_character_count=101,
    )
    monkeypatch.setattr(v3_group, "CommandRepository", Commands)
    monkeypatch.setattr(v3_group, "DocumentRepository", lambda: SimpleNamespace(get_version=lambda *_: version))
    monkeypatch.setattr(v3_group, "refuse_comparison_only_version", lambda _version: None)
    monkeypatch.setattr(v3_group, "_validate_pack", lambda _pack: SimpleNamespace(snapshot_id="ns_test"))
    monkeypatch.setattr(v3_group, "current_snapshot", lambda _session: None)
    kwargs = dict(
        version_uid=VERSION, idempotency_key="v3-relaxed-test", provider_mode="live",
        pack=SimpleNamespace(sha256="a" * 64), input_budget_characters=100,
    )
    with pytest.raises(DomainError) as standard:
        v3_group.start_ar_v3_group(object(), **kwargs)
    assert standard.value.code is ErrorCode.ANALYSIS_INPUT_BUDGET_EXCEEDED
    with pytest.raises(DomainError) as relaxed:
        v3_group.start_ar_v3_group(object(), **kwargs, relaxed_limits=True)
    assert relaxed.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
