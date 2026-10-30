"""Temporary section policy: durable intent, immutable variants, metered execution."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from auditmanager.analysis.text.cost import CostMeter
from auditmanager.analysis.text.adapter import build_request
from auditmanager.analysis.text.lock import ModelPin
from auditmanager.analysis.text.profile_registry import load_text_profile_registry, relaxed_profile_pair
from auditmanager.analysis.text.windows import relaxed_window_characters, text_window_policy
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.api.schemas.models import StartRunRequest
from auditmanager.ingest.public import CommandRepository, CommandStarted
from auditmanager.ingest.commands import CommandRecord
from auditmanager.runs import commands as run_commands
from auditmanager.runs import executor as run_executor
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, IdempotencyKey

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
COMMAND = "cmd_01M2545JSD15ETSNNV904X991C"
BLOB = "blob_sha256_" + "ab" * 32
MODEL = "claude-opus-5"


def test_api_accepts_only_explicit_boolean_and_defaults_off() -> None:
    assert StartRunRequest.model_validate({"version_uid": VERSION}).relaxed_limits is None
    assert StartRunRequest.model_validate({"version_uid": VERSION, "relaxed_limits": True}).relaxed_limits is True
    with pytest.raises(ValidationError):
        StartRunRequest.model_validate({"version_uid": VERSION, "relaxed_limits": "true"})


def test_all_fifteen_relaxed_pairs_resolve_to_distinct_immutable_64k_bundles() -> None:
    registry = load_text_profile_registry()
    assert len(registry.entries) == 15
    for entry in registry.entries.values():
        pair = relaxed_profile_pair(entry.analysis_profile_id, entry.prompt_bundle_id)
        normal = registry.resolve(entry.analysis_profile_id, entry.prompt_bundle_id)
        relaxed = registry.resolve(*pair)
        assert pair != (entry.analysis_profile_id, entry.prompt_bundle_id)
        assert normal.prompt_bundle.max_output_tokens == 16_000
        assert relaxed.prompt_bundle.max_output_tokens == 64_000
        assert normal.prompt_bundle.content_sha256 != relaxed.prompt_bundle.content_sha256
        assert normal.content_sha256 != relaxed.content_sha256
        assert relaxed_profile_pair(entry.analysis_profile_id, entry.prompt_bundle_id) == pair
        layer = TextLayer(version_uid=VERSION, normalization_id="nfc_v1",
                          pages=(Page(1, 0, 1, "x"),), document_text="x")
        assert build_request(model_id=MODEL, bundle=relaxed.prompt_bundle,
                             text_layer=layer).body["max_tokens"] == 64_000


def test_fingerprint_preserves_old_default_bytes_and_distinguishes_both_choices() -> None:
    base = dict(version_uid=VERSION, analysis_profile_id="ap_01M2545JSD15ETSNNV904X991A",
                prompt_bundle_id="pb_01M2545JSD15ETSNNV904X991P", provider_mode="recorded",
                input_basis_digest_value="a" * 64)
    old = run_commands.start_run_fingerprint(**base)
    assert old == run_commands.start_run_fingerprint(**base, relaxed_limits=False)
    raised = run_commands.start_run_fingerprint(**base, relaxed_limits=True)
    assert raised != old


class Ledger:
    def __init__(self):
        self.claims = []
        self.outcome = None

    def find(self, *_args, **_kwargs):
        return None

    def begin(self, *_args, **kwargs):
        self.claims.append(kwargs["fingerprint"])
        return CommandStarted(CommandId.parse(COMMAND))

    def succeed(self, _session, _command_id, outcome):
        self.outcome = outcome


class Runs:
    def __init__(self):
        self.row = None

    def create(self, _session, **row):
        self.row = row

    def find(self, _session, run_id):
        return SimpleNamespace(**self.row) if self.row and self.row["run_id"] == run_id else None


class Documents:
    def __init__(self, count):
        self.count = count

    def get_version(self, *_args):
        return SimpleNamespace(project_uid=PROJECT, text_character_count=self.count,
                               manifest=(SimpleNamespace(role="source.document", blob_id=BLOB),))


def _start(monkeypatch, count, raised):
    registry = load_text_profile_registry()
    entry = registry.entries["AI"]
    monkeypatch.setattr(run_commands, "route_classified_version", lambda *_: SimpleNamespace(
        analysis_profile_id=entry.analysis_profile_id, prompt_bundle_id=entry.prompt_bundle_id,
    ))
    ledger, runs = Ledger(), Runs()
    outcome = run_commands.start_audit_run(
        None, version_uid=VERSION, provider_mode="recorded", idempotency_key="section-relaxed",
        commands=ledger, runs=runs, documents=Documents(count), norms_snapshot=lambda _: None,
        section_profiles=registry.section_profiles(), input_budget_characters=100,
        relaxed_limits=raised, text_profiles=registry, operational_model_id=MODEL,
    )
    return outcome, ledger, runs, entry


def test_accepted_raised_run_pins_variant_and_saves_worker_choice(monkeypatch) -> None:
    started, ledger, runs, entry = _start(monkeypatch, 1100, True)
    assert not started.replayed
    assert (runs.row["analysis_profile_id"], runs.row["prompt_bundle_id"]) == relaxed_profile_pair(
        entry.analysis_profile_id, entry.prompt_bundle_id,
    )
    assert ledger.outcome == {"run_id": started.run_id, "relaxed_limits": True}
    assert len(ledger.claims) == 1


@pytest.mark.parametrize("first_raised", [False, True])
def test_known_key_replays_same_choice_and_rejects_opposite_choice(monkeypatch, first_raised) -> None:
    first, ledger, runs, entry = _start(monkeypatch, 100, first_raised)
    record = CommandRecord(
        command_id=CommandId.parse(COMMAND), command_type=run_commands.COMMAND_TYPE_START_RUN,
        idempotency_key=IdempotencyKey("section-relaxed"), payload_fingerprint=ledger.claims[0],
        state="succeeded", outcome=ledger.outcome, error_code=None,
    )

    class ReplayLedger:
        def find(self, *_args, **_kwargs):
            return record

        def begin(self, *_args, **kwargs):
            return CommandRepository._answer_existing(record, kwargs["fingerprint"])

    registry = load_text_profile_registry()
    def retry(raised):
        return run_commands.start_audit_run(
            None, version_uid=VERSION, provider_mode="recorded", idempotency_key="section-relaxed",
            commands=ReplayLedger(), runs=runs, documents=Documents(100), norms_snapshot=lambda _: None,
            section_profiles=registry.section_profiles(), input_budget_characters=100,
            relaxed_limits=raised, text_profiles=registry, operational_model_id=MODEL,
        )

    assert retry(first_raised).run_id == first.run_id
    assert retry(first_raised).replayed
    with pytest.raises(DomainError) as conflict:
        retry(not first_raised)
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_operational_twelve_window_bound_refuses_before_claim(monkeypatch) -> None:
    registry = load_text_profile_registry()
    entry = registry.entries["AI"]
    monkeypatch.setattr(run_commands, "route_classified_version", lambda *_: SimpleNamespace(
        analysis_profile_id=entry.analysis_profile_id, prompt_bundle_id=entry.prompt_bundle_id,
    ))
    ledger, runs = Ledger(), Runs()
    too_large = 12 * relaxed_window_characters(MODEL, entry.profile.prompt_bundle) + 1
    with pytest.raises(DomainError) as refusal:
        run_commands.start_audit_run(
            None, version_uid=VERSION, provider_mode="recorded", idempotency_key="large",
            commands=ledger, runs=runs, documents=Documents(too_large), norms_snapshot=lambda _: None,
            section_profiles=registry.section_profiles(), input_budget_characters=100,
            relaxed_limits=True, text_profiles=registry, operational_model_id=MODEL,
        )
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_BUDGET_EXCEEDED
    assert ledger.claims == [] and runs.row is None


def test_relaxed_window_sizing_uses_normal_reserve_but_keeps_twelve_windows() -> None:
    entry = load_text_profile_registry().entries["AI"]
    pair = relaxed_profile_pair(entry.analysis_profile_id, entry.prompt_bundle_id)
    bundle = load_text_profile_registry().resolve(*pair).prompt_bundle
    policies = [text_window_policy(text_character_count=1_000_000, model_id=MODEL,
                                   ceiling_usd=ceiling, bundle=bundle, relaxed_limits=True)
                for ceiling in (0.1, 10.0)]
    assert policies[0] == policies[1]
    assert policies[0] is not None
    assert policies[0].window_characters == relaxed_window_characters(MODEL, bundle)
    assert policies[0].max_windows == 12


def test_relaxed_meter_keeps_charging_after_crossing_former_ceiling() -> None:
    pin = ModelPin(model_id=MODEL, input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)
    meter = CostMeter(ceiling_usd=1.0, enforce_ceiling=False)
    meter.charge(pin, input_tokens=100, output_tokens=100, reported_cost_usd=1.25)
    meter.check_before_call()
    meter.charge(pin, input_tokens=100, output_tokens=100, reported_cost_usd=0.75)
    assert meter.spent_usd == 2.0 and meter.call_count == 2
    assert meter.cost_basis == "measured"


@pytest.mark.parametrize("saved,expected", [
    ({"run_id": "run_test"}, False),
    ({"run_id": "run_test", "relaxed_limits": True}, True),
    ({"run_id": "run_test", "relaxed_limits": False}, False),
])
def test_worker_reads_durable_choice_and_old_outcome_defaults_off(monkeypatch, saved, expected) -> None:
    class Commands:
        def get(self, _session, command_id):
            assert str(command_id) == COMMAND
            return SimpleNamespace(command_type="start_audit_run", state="succeeded", outcome=saved)

    monkeypatch.setattr(run_executor, "CommandRepository", Commands)
    run = SimpleNamespace(run_id="run_test", command_id=COMMAND)
    assert run_executor._section_relaxed_limits(None, run) is expected


@pytest.mark.parametrize("saved", [
    {"run_id": "other", "relaxed_limits": True},
    {"run_id": "run_test", "relaxed_limits": "true"},
    None,
])
def test_worker_refuses_corrupt_saved_choice_before_model_effect(monkeypatch, saved) -> None:
    class Commands:
        def get(self, _session, _command_id):
            return SimpleNamespace(command_type="start_audit_run", state="succeeded", outcome=saved)

    monkeypatch.setattr(run_executor, "CommandRepository", Commands)
    with pytest.raises(DomainError) as refusal:
        run_executor._section_relaxed_limits(None, SimpleNamespace(run_id="run_test", command_id=COMMAND))
    assert refusal.value.code is ErrorCode.INTERNAL_ERROR
