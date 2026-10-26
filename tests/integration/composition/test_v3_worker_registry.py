"""The API carrier and worker chain receive the server-owned v3 registry."""

from __future__ import annotations

import auditmanager.runs as runs_public

from auditmanager.bootstrap.adapters import RunAdapter
from auditmanager.runs import carrier
from auditmanager.runs.v3_group import TrustedPackRegistry


class Session:
    def __init__(self):
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def commit(self):
        self.commits += 1


def test_run_adapter_passes_its_pack_registry_to_carrier(monkeypatch):
    registry = TrustedPackRegistry.empty()
    seen = {}

    def run_to_terminal(*args, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(runs_public, "run_to_terminal", run_to_terminal)
    adapter = RunAdapter(
        lambda: Session(), blob_store=object(), adapter=object(),
        provider_config=object(), provider_mode="recorded",
        analysis_profile_id="ap_fixture", prompt_bundle_id="pb_fixture",
        carrier=object(), ar_v3_pack_registry=registry,
    )
    adapter._job("run_test")()
    assert seen["ar_v3_pack_registry"] is registry
    assert registry.select_beta() is None


def test_carrier_forwards_registry_to_run_executor(monkeypatch):
    registry = TrustedPackRegistry.empty()
    session = Session()
    seen = {}

    def execute(*args, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(carrier, "execute_run", execute)
    carrier.run_to_terminal(
        lambda: session, "run_test", blob_store=object(), adapter=object(),
        provider_config=object(), ar_v3_pack_registry=registry,
    )
    assert seen["ar_v3_pack_registry"] is registry
    assert session.commits == 1
