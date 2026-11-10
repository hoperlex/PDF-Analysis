"""`D-673` (`HOSTS-DEBTS-01`): the member binder reads the call row's provider label and identity basis from the revision and its kind, and builds
exactly one adapter.

``DatabaseProviders._bind_member`` used to call ``bind_connection`` only for ``provider_label`` and ``identity_basis`` and then built the real
adapter (the cell's own ``HostCall``) with ``build_pull_adapter``: a whole pull adapter made and thrown away on every binding of a cell. The
two values are facts of the kind's table entry and the revision (``revision.settings.pull_client``, ``IDENTITY_BASIS_BY_KIND``).

No database: the repository and the adapter builder are fakes, and ``bind_connection`` is a tripwire.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings, ProviderConfig, ProviderMode
from auditmanager.bootstrap import providers as providers_module
from auditmanager.bootstrap.providers import DatabaseProviders
from auditmanager.executors.runtime import DestinationPolicy, KindRuntime
from auditmanager.shared.errors import DomainError, ErrorCode

HOST = "exh_01M2545JSD15ETSNNV904X991A"
REVISION = "excr_01M2545JSD15ETSNNV904X991R"
CELL = CellSettings("blocks:leg1", "claude-opus-5-5", "high", 6000, 1800, access="subscription")


def _revision(**settings: Any) -> SimpleNamespace:
    values = {"gateway_model": "claude-opus-5-5", "billing": "not_metered", "pull_client": "agent", "answer_deadline_seconds": 600, **settings}
    return SimpleNamespace(revision_id=REVISION, connection_id="exc_1", settings=SimpleNamespace(**values))


def _connection(kind: str = "pull") -> SimpleNamespace:
    return SimpleNamespace(connection_id="exc_1", kind=kind, host_id=HOST, capacity_pool=f"{HOST}:claude_code")


class _World:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, revision: Any, connection: Any) -> None:
        self.built: list[dict[str, Any]] = []

        class Repo:
            def get_revision(self, session: Any, revision_id: str) -> Any:
                return revision

            def get_connection(self, session: Any, connection_id: str) -> Any:
                return connection

        def tripwire(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("bind_connection builds a throwaway adapter: the label and the basis are read from the revision")

        def build(**kwargs: Any) -> Any:
            self.built.append(kwargs)
            return "ADAPTER"

        monkeypatch.setattr(providers_module, "ExecutorRepository", Repo)
        monkeypatch.setattr(providers_module, "bind_connection", tripwire)
        monkeypatch.setattr(providers_module, "build_pull_adapter", build)
        runtime = KindRuntime(session_factory=lambda: None, engine=None)  # type: ignore[arg-type,return-value]
        self.providers = DatabaseProviders(
            ring=None, policy=DestinationPolicy.from_environment({}), ceiling_usd=1.0, runtime=runtime,
            base_config=ProviderConfig(mode=ProviderMode.LIVE, model_id="claude-opus-5-5", run_cost_ceiling_usd=1.0, api_key=None,
                                       ceiling_is_explicit=True))

    def bind(self) -> Any:
        return self.providers._bind_member(None, connection_revision_id=REVISION, cell=CELL, context=object())  # type: ignore[arg-type]


def test_the_label_and_the_identity_basis_come_from_the_revision_and_one_adapter_is_built(monkeypatch: pytest.MonkeyPatch) -> None:
    world = _World(monkeypatch, _revision(pull_client="agent"), _connection())
    member = world.bind()
    assert (member.provider_label, member.identity_basis) == ("agent", "declared"), "the revision's pull client; a pull model is declared"
    assert (member.adapter, member.connection_revision_id, member.unmetered, member.host_id) == ("ADAPTER", REVISION, True, HOST)
    (built,) = world.built
    assert built["host_call"].cell_key == "blocks:leg1" and built["host_call"].timeout_seconds == 1800, "the one adapter carries the cell's own call"


def test_a_revision_that_names_no_client_is_labelled_by_its_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    member = _World(monkeypatch, _revision(pull_client=None), _connection()).bind()
    assert member.provider_label == "pull"


@pytest.mark.parametrize("kind", ["http_api", "ssh_command", "unknown_kind"])
def test_a_kind_that_is_not_a_channel_is_not_a_member_of_a_host(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    world = _World(monkeypatch, _revision(), _connection(kind))
    with pytest.raises(DomainError) as refused:
        world.bind()
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and world.built == [], "no adapter is built for a member that cannot serve"


def test_a_member_of_another_model_is_still_refused_before_anything_is_built(monkeypatch: pytest.MonkeyPatch) -> None:
    world = _World(monkeypatch, _revision(gateway_model="claude-sonnet-5-5"), _connection())
    with pytest.raises(DomainError) as refused:
        world.bind()
    assert refused.value.detail_fields["reason"] == "cell_member_serves_another_model" and world.built == []
