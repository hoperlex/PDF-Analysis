"""The DB route keeps approved command authority while supplying its own model binding."""

from dataclasses import replace
from types import SimpleNamespace

from auditmanager.analysis.public import ProviderConfig, ProviderMode
from auditmanager.runs.executor import _bind_provider
from auditmanager.runs.provider import ProviderBinding


def test_database_binding_keeps_approved_cost_window_and_identity_pins():
    default = ProviderConfig(mode=ProviderMode.RECORDED, model_id="environment-model",
                             run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=False)
    approved = replace(default, approved_cost_ceiling=True, run_cost_ceiling_usd=2.5,
                       approved_window_characters=12345, approved_max_windows=4,
                       approved_model_id="database-model", approved_rate_sha256="a" * 64,
                       approved_connection_revision_id="exr_test")
    routed = replace(default, model_id="database-model", run_cost_ceiling_usd=100.0)
    adapter = SimpleNamespace(provider_mode=ProviderMode.RECORDED)
    original = ProviderBinding(adapter, routed, object())
    result = _bind_provider(object(), SimpleNamespace(provider_mode="recorded"), object(),
                            lambda *args: original, adapter, approved)
    assert result.adapter is original.adapter and result.call is original.call
    assert result.config.model_id == "database-model"
    assert result.config.run_cost_ceiling_usd == 2.5
    assert result.config.approved_window_characters == 12345
    assert result.config.approved_max_windows == 4
    assert result.config.approved_model_id == "database-model"
    assert result.config.approved_rate_sha256 == "a" * 64
    assert result.config.approved_connection_revision_id == "exr_test"
    assert original.config.run_cost_ceiling_usd == 100.0
