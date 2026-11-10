"""Source-bound monetary consent, all ordinary sections and provider pre-call caps."""
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace as NS

import json
import pytest

from auditmanager.analysis.public import ProviderConfig, ProviderMode, ModelPin, model_rate_sha256
from auditmanager.analysis.text.cost import CostMeter, request_cost_upper_usd, require_approved_model
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.runs import preflight
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
MODEL = "claude-opus-5"


@pytest.fixture
def registry():
    return load_text_profile_registry()


def version(section="AI", count=300_000, pages=100):
    return NS(version_uid=VERSION, sha256="a"*64, text_character_count=count,
        recognised_character_count=0, page_count=pages, upload_kind="portal_bundle",
        classification=NS(version_uid=VERSION, confirmed_by_user_uid="usr_01M2545JSD15ETSNNV904X991J",
            section_code=section, project_stage="P", revision=1),
        manifest=(NS(role="source.document", blob_id="blob_sha256_"+"b"*64),))


def service(registry, **kwargs):
    return preflight.RunCostPreflight(section_profiles=registry.section_profiles(), text_profiles=registry,
        provider_config=ProviderConfig(ProviderMode.RECORDED, MODEL, 1.0, None, False),
        provider_mode="recorded", **kwargs)


def estimate(service, source, **kwargs):
    return service.estimate_run(None, version_uid=VERSION, version_record=source, **kwargs)


def consent(value, cap=None):
    return {"estimate_digest": value.estimate_digest, "ceiling_micros": value.as_dict()["recommended_ceiling_micros"] if cap is None else cap, "confirmed": True}


PLAN_ENV = "AUDITMANAGER_EXTENDED_ANALYSIS_PLAN"


def test_all_sections_price_before_start_under_the_v2_plan_when_it_is_named(registry, monkeypatch):
    """The v2 plan is an explicit choice since the shipped default became v3 (`S3-04`)."""
    monkeypatch.setenv(PLAN_ENV, "v2")
    policy = service(registry)
    assert len(registry.entries) == 15
    for section in registry.entries:
        small = estimate(policy, version(section, 500, 1))
        large = estimate(policy, version(section, 20_000_000, 500))
        # v2 reserves, for one page of 500 characters and no image count: 1 text window, 13 image
        # calls (100 possible images / 8), 16 comprehensive calls (page + text pieces + images +
        # window) and 30 norm calls = 1 + 13 + 16 + 30. No section changes that sum.
        assert small.as_dict()["calls"] == 60
        assert json.loads(small.authority_json)["extended_review"] == {
            "enabled": True, "max_blocks": "all", "plan_version": "extended-review-v2"}
        assert large.as_dict()["calls"] > 12
        assert large.as_dict()["estimated_cost_micros"] > small.as_dict()["estimated_cost_micros"] > 0
        accepted = large.approve(consent(large), actor_user_uid="expert")
        assert accepted["extended_review"]["plan_version"] == "extended-review-v2"
        assert accepted["max_windows"] == max(12, large.as_dict()["windows"])
        assert accepted["approved_by_user_uid"] == "expert"


def test_all_sections_price_before_start_under_the_default_v3_plan(registry, monkeypatch):
    """Nothing names a plan: the shipped default is v3, which bounds the visual scope by the page count."""
    monkeypatch.delenv(PLAN_ENV, raising=False)
    policy = service(registry)
    for section in registry.entries:
        small = estimate(policy, version(section, 500, 1))
        large = estimate(policy, version(section, 20_000_000, 500))
        small_review = json.loads(small.authority_json)["extended_review"]
        large_review = json.loads(large.authority_json)["extended_review"]
        # One page: 1 text window + 1 visual window of (2 block + 4 comprehensive + 8 norm +
        # 8 review + 8 correction) calls + 8 project-parameter calls. No global cross-window pass
        # exists below 16 text pages. Fresh consent also reserves one received-reply repair for every
        # initial extended call (`semantic_repair_attempts == 1`, `RunCostPreflight` doubles
        # `extra_calls` after the visual, parameter and global calls are summed); the text window is
        # not one of them: 1 + 2 * (30 + 8) = 77.
        assert small_review["semantic_repair_attempts"] == 1
        assert small.as_dict()["calls"] == 1 + 2 * (2 + 4 + 8 + 8 + 8 + 8)
        assert (small_review["plan_version"], small_review["max_blocks"], small_review["max_windows"]) == (
            "extended-review-v3", 1, 1)
        assert "global_cross_window_policy" not in small_review
        # 500 pages: the visual scope stops at 500 blocks over 32 windows of (2 + 128 + 8 + 8 + 8)
        # calls, then 32 global calls and 8 project-parameter calls, each reserved twice for its
        # repair, on top of the text windows.
        windows = large.as_dict()["windows"]
        assert windows > 12
        assert large.as_dict()["calls"] == windows + 2 * (32 * 154 + 32 + 8)
        assert (large_review["plan_version"], large_review["max_blocks"], large_review["max_windows"]) == (
            "extended-review-v3", 500, 32)
        assert large.as_dict()["estimated_cost_micros"] > small.as_dict()["estimated_cost_micros"] > 0
        accepted = large.approve(consent(large), actor_user_uid="expert")
        assert accepted["extended_review"]["plan_version"] == "extended-review-v3"
        assert accepted["max_windows"] == windows
        assert accepted["approved_by_user_uid"] == "expert"


def test_fresh_full_review_prices_images_without_rejecting_portal_stamps(registry, monkeypatch):
    kinds = ['image'] * 47 + ['text'] * 12 + ['stamp']
    raw = json.dumps({'pages': [{} for _ in range(30)], 'blocks': [
        {'block_id': f'blk_{index:032x}', 'block_type': kind, 'page_index': index % 30}
        for index, kind in enumerate(kinds)
    ]}).encode()
    digest = sha256(raw).hexdigest()
    source = version('AR', 300_000, 30)
    source.manifest += (NS(role='source.structured_companion',
        blob_id=str(derive_blob_id(sha256=digest, size=len(raw))), sha256=digest, size_bytes=len(raw)),)
    precise = service(registry, blob_store=NS(read=lambda *_args, **_kw: raw))
    assert precise._image_block_count(source) == 47
    monkeypatch.setenv('AUDITMANAGER_EXTENDED_ANALYSIS_PLAN', 'v2')
    exact = estimate(precise, source)
    fallback = estimate(service(registry), source)
    assert exact.as_dict()['calls'] < fallback.as_dict()['calls']
    assert exact.as_dict()['estimated_cost_micros'] < fallback.as_dict()['estimated_cost_micros']
    monkeypatch.setenv('AUDITMANAGER_EXTENDED_ANALYSIS_PLAN', 'v3')
    assert estimate(precise, source).as_dict()['estimated_cost_micros'] > 0
    with pytest.raises(DomainError) as failure:
        estimate(service(registry, blob_store=NS(read=lambda *_args, **_kw: b'bad')), source)
    assert failure.value.detail_fields['reason'] == 'cost_blocks_source_invalid'


def test_exact_micro_cost_does_not_round_fractions_down():
    assert preflight.estimated_micros(ModelPin("m", .1, .3), 1, 1) == 1
    assert preflight.estimated_micros(ModelPin("m", 3., 15.), 10, 20) == 330


@pytest.mark.parametrize("mutate", [lambda v: setattr(v, "sha256", "d"*64),
    lambda v: setattr(v, "recognised_character_count", 1),
    lambda v: setattr(v.classification, "revision", 2),
    lambda v: setattr(v.classification, "section_code", "EOM")])
def test_changed_source_or_classification_refuses_old_consent(registry, mutate):
    policy, source = service(registry), version()
    old = estimate(policy, source)
    mutate(source)
    with pytest.raises(DomainError) as failure:
        estimate(policy, source).approve(consent(old))
    assert failure.value.code is ErrorCode.CONFLICT
    assert failure.value.detail_fields["conflict_reason"] == "run_cost_estimate_stale"


def test_raised_output_price_and_route_rate_preset_changes_are_bound(registry):
    revision = NS(revision_id="erev1", model_id=MODEL, input_budget_characters=1, billing="metered", chosen_connection_id="exec1")
    chosen = NS(revision_id="prev1", executor_connection_id="exec1")
    policy = service(registry, connection_route=lambda *_args, **_kw: revision,
                     preset_resolver=lambda *_args: chosen)
    source = version()
    old = estimate(policy, source, preset_id="preset1")
    raised = estimate(policy, source, preset_id="preset1", relaxed_limits=True)
    assert raised.as_dict()["output_tokens"] - old.as_dict()["output_tokens"] == old.as_dict()["windows"] * 48_000
    assert raised.estimate_digest != old.estimate_digest
    revision.revision_id = "erev2"
    assert estimate(policy, source, preset_id="preset1").estimate_digest != old.estimate_digest
    revision.revision_id = "erev1"
    chosen.revision_id = "prev2"
    assert estimate(policy, source, preset_id="preset1").estimate_digest != old.estimate_digest
    policy.prices = lambda: (ModelPin(MODEL, 300., 1500.),)
    assert estimate(policy, source, preset_id="preset1").estimate_digest != old.estimate_digest


def test_section_stats_consent_accepts_zero_ceiling_and_keeps_source_binding(registry, monkeypatch):
    monkeypatch.delenv(PLAN_ENV, raising=False)
    value = estimate(service(registry), version("AR", 300_000, 30), relaxed_limits=True)
    approved = value.approve(consent(value, 0))
    assert approved["uncapped_stats"] is True
    assert approved["ceiling_micros"] == 0
    assert approved["extended_review"]["plan_version"] == "extended-review-v3"
    assert approved["extended_review"]["unbounded_stats"] is True
    # Native page pieces are on by default (`7e4b3364`): the cap follows the estimated windows
    # (11 here), floored at 12, and no longer follows the page count (30).
    assert value.as_dict()["windows"] == 11
    assert approved["max_windows"] == 12
    # Without page pieces the relaxed cap is the page count, which is the reading the old pin made.
    paged = service(registry).estimate_run(None, version_uid=VERSION, version_record=version("AR", 300_000, 30),
                                           relaxed_limits=True, allow_native_page_pieces=False)
    assert paged.approve(consent(paged, 0))["max_windows"] == 30
    normal = estimate(service(registry), version("AR", 300_000, 30))
    with pytest.raises(DomainError):
        normal.approve(consent(normal, 0))


@pytest.mark.parametrize("payload", [None, {}, {"confirmed": False}, {"confirmed": "true"}])
def test_missing_or_unconfirmed_consent_refuses(registry, payload):
    with pytest.raises(DomainError) as failure:
        estimate(service(registry), version()).approve(payload)
    assert failure.value.code is ErrorCode.VALIDATION_FAILED


def test_too_small_limit_refuses_and_unmetered_zero_is_explicit(registry):
    priced = estimate(service(registry), version())
    with pytest.raises(DomainError):
        priced.approve(consent(priced, priced.as_dict()["estimated_cost_micros"]-1))
    revision = NS(revision_id="rev", model_id=MODEL, input_budget_characters=1, billing="unmetered")
    unmetered = estimate(service(registry, connection_route=lambda _: revision), version())
    assert unmetered.as_dict()["billing"] == "unmetered"
    assert unmetered.as_dict()["estimated_cost_micros"] == unmetered.as_dict()["recommended_ceiling_micros"] == 0
    assert unmetered.approve(consent(unmetered, 0))["ceiling_micros"] == 0


def test_next_full_request_must_fit_accepted_limit_and_model_rate_revision_are_pinned():
    pin = ModelPin(MODEL, 3., 15.)
    request = ModelRequest(MODEL, {"system": "x"*5000, "max_tokens": 16000})
    pending = request_cost_upper_usd(pin, request)
    meter = CostMeter(ceiling_usd=pending, spent_usd=0)
    meter.check_before_call(pending_cost_usd=pending)
    with pytest.raises(DomainError) as failure:
        CostMeter(ceiling_usd=pending/2).check_before_call(pending_cost_usd=pending)
    assert failure.value.code is ErrorCode.COST_BUDGET_EXCEEDED
    # Explicit unmetered sources never acquire a monetary charge.
    CostMeter(ceiling_usd=0, enforce_ceiling=False).check_before_call(pending_cost_usd=pending)
    config = ProviderConfig(ProviderMode.RECORDED, MODEL, 1., None, False,
        approved_cost_ceiling=True, approved_model_id=MODEL,
        approved_rate_sha256=model_rate_sha256(pin), approved_connection_revision_id="rev1")
    require_approved_model(config, pin, NS(connection_revision_id="rev1"))
    with pytest.raises(DomainError):
        require_approved_model(config, ModelPin(MODEL, 30., 15.), NS(connection_revision_id="rev1"))
    with pytest.raises(DomainError):
        require_approved_model(config, pin, NS(connection_revision_id="rev2"))


def test_comparison_zip_pdf_can_be_priced_from_its_native_text(registry):
    """The manual SP1 pack has no portal count, yet its classified PDF gets a run estimate."""
    from io import BytesIO
    from zipfile import ZipFile
    from pathlib import Path

    pack = Path(__file__).resolve().parents[3] / 'fixtures/manual-comparison-1030/comparison-manual-pack.zip'
    with ZipFile(pack) as outer, ZipFile(BytesIO(outer.read('SP1-OLD.zip'))) as inner:
        raw = inner.read(inner.namelist()[0])
    digest = sha256(raw).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(raw))

    class Store:
        def inspect(self, _blob):
            return NS(sha256=digest, size=len(raw))

        def open_stream(self, _blob, **_kwargs):
            yield raw

    source = version('AR', None, 6)
    source.upload_kind = 'comparison_pdf'
    source.sha256 = digest
    source.manifest = (NS(role='comparison.source_pdf', blob_id=str(blob_id), sha256=digest,
                          size_bytes=len(raw), media_type='application/pdf'),)
    from auditmanager.runs.commands import _resolve_references
    _, blobs = _resolve_references(None, version_uid=VERSION,
        analysis_profile_id='ap_01ARZ3NDEKTSV4RRFFQ69G5FAV',
        prompt_bundle_id='pb_01ARZ3NDEKTSV4RRFFQ69G5FAV',
        documents=None, version=source)
    assert blobs['source.document'] == blobs['comparison.source_pdf'] == str(blob_id)
    priced = service(registry, blob_store=Store())
    _, chars, facts = priced._source(None, VERSION, source)
    assert chars > 0 and facts['native_characters'] == chars
    assert estimate(priced, source).as_dict()['estimated_cost_micros'] > 0


def test_six_scope_group_prices_all_calls_and_pins_each_verified_set(monkeypatch, registry):
    from auditmanager.runs import v3_group
    scopes = tuple(NS(scope_id=scope, identity=scope, chunking_profile="chunk-v1",
        set_id="set-"+scope, set_sha256=str(index)*64) for index, scope in enumerate(v3_group.SCOPES, 1))
    pack = NS(scopes=scopes, sha256="e"*64)
    profile = NS(snapshot_id="snapshot", content_sha256="p"*64,
                 system_prompt="rules", response_schema_json="{}")
    monkeypatch.setattr(v3_group, "_validate_pack", lambda _: profile)
    monkeypatch.setattr(preflight, "current_snapshot", lambda _: NS(norms_snapshot_id="snapshot"))
    monkeypatch.setattr(preflight, "qualification", lambda *_: NS(build_complete=True, sources_confirmed=True))
    refs = {scope.scope_id: NS(set_id=scope.set_id, set_sha256=scope.set_sha256,
                              set_size_bytes=10_000 + index) for index, scope in enumerate(scopes)}
    monkeypatch.setattr(preflight, "select_verified_retrieval_set", lambda _s, *, identity, **_: refs[identity])
    route = NS(revision_id="rev", model_id=MODEL, billing="metered", input_budget_characters=1)
    policy = service(registry, pack_registry=NS(select_beta=lambda: pack), connection_route=lambda _: route)
    value = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"))
    view, authority = value.as_dict(), value.approve(consent(value))
    assert view["calls"] == view["windows"] == 6
    assert view["output_tokens"] == 6*16_000
    assert view["estimated_cost_micros"] == sum(authority["scope_costs_micros"].values())
    raised = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"), relaxed_limits=True)
    assert raised.as_dict()["output_tokens"] == 6*64_000
    assert raised.as_dict()["estimated_cost_micros"] > view["estimated_cost_micros"]
    refs[scopes[0].scope_id].set_size_bytes += 1
    changed = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"))
    assert changed.estimate_digest != value.estimate_digest
    route.billing = "unmetered"
    free = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"))
    assert free.as_dict()["estimated_cost_micros"] == 0 and free.approve(consent(free))["billing"] == "unmetered"


def test_section_run_bounds_hold_unless_the_run_asks_for_relaxed_limits(registry, monkeypatch):
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS", "1")
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v3")
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_COVERAGE", "batched-v1")
    policy = service(registry)
    within = json.loads(estimate(policy, version("AR", 300_000, 500)).authority_json)["extended_review"]
    assert within["text_page_limit"] == 500 and "unbounded_stats" not in within
    with pytest.raises(DomainError) as failure:
        estimate(policy, version("AR", 300_000, 501))
    assert failure.value.detail_fields["reason"] == "cost_page_count_unavailable"
    relaxed = json.loads(estimate(policy, version("AR", 300_000, 501), relaxed_limits=True).authority_json)
    assert relaxed["extended_review"]["unbounded_stats"] is True
    assert relaxed["extended_review"]["text_page_limit"] == 501


def test_only_the_batched_coverage_can_lift_the_section_run_bounds(registry, monkeypatch):
    # The worker recognises a relaxed run by the stamp of the batched coverage policy, so a
    # relaxed run priced under another coverage keeps the bounds rather than being priced for a
    # run the worker would then refuse.
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS", "1")
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v3")
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_COVERAGE", "legacy")
    with pytest.raises(DomainError) as failure:
        estimate(service(registry), version("AR", 300_000, 501), relaxed_limits=True)
    assert failure.value.detail_fields["reason"] == "cost_page_count_unavailable"
