"""`D-678` (`HOSTS-CMP-01`): ``_ComparisonRoutes.route`` builds a server member's pull adapter with the job's cell as its ``HostCall``.

A comparison job the stage layout admitted froze a cell. When it is bound to a **system member of a server** (a connection with a capacity pool) the
host agent must be told the cell's provider, access, model, effort, limit, timeout and key (``payload.host``), and the cell's timeout is the task's
window. That is done in ``bootstrap/composition.py`` ``_ComparisonRoutes.route``, which no test reached: ``tests/unit/comparison/spend`` builds the
adapter by hand. Here ``_ComparisonRoutes`` is the real class over fakes of the binder (``bind_connection``) only; the pull adapter, ``host_call_of``,
``split_pool``, ``access_of_billing`` and the wrapper are the real ones.

* a job with a cell, bound to a member with a capacity pool: the adapter carries the cell's ``HostCall`` -- provider from the pool, access from the
  connection's billing, model, effort, limit, timeout and ``cell_key`` of the cell -- and the runtime's engine;
* the same job on a metered connection is told ``api``, on an unmetered one ``subscription``;
* a job with **no cell** gets the plain adapter the binder made, with no host call;
* a job with a cell bound to a connection with **no pool** (a legacy connection) gets the plain adapter too;
* a cell whose model is not the member's is refused by the adapter (``ValueError``), not sent.

Break-it-once (in a scratch copy of ``src``): with the ``cell is not None and pool is not None`` branch removed from ``route``, the first, second and last
tests fail; with ``cell`` ignored (the branch taken for any server member) the no-cell test fails, with ``pool`` ignored the no-pool test fails, and with
``host_call=None`` passed to the adapter the first, second and last fail again.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings
from auditmanager.bootstrap.composition import _ComparisonRoutes
from auditmanager.comparison.spend.pull_images import PublishedPullAdapter
from auditmanager.executors import runtime
from auditmanager.executors.public import HostCall, pinned_models
from auditmanager.executors.pull import PullAdapter

PIN = pinned_models()[0].model_id
CELL = CellSettings(cell_key="comparison_pair_check:main", model_id=PIN, effort="medium", max_output_tokens=1200, timeout_seconds=1500)
ENGINE = object()
SESSIONS = object()


def _bound(*, pool: str | None, billing: str = "not_metered", gateway_model: str = PIN, plain: Any = None) -> SimpleNamespace:
    revision = SimpleNamespace(
        revision_id="ecr_frozen",
        settings=SimpleNamespace(pin_id=PIN, gateway_model=gateway_model, billing=billing, answer_deadline_seconds=900),
    )
    return SimpleNamespace(
        adapter=plain if plain is not None else object(), revision=revision, connection=SimpleNamespace(kind="pull", capacity_pool=pool),
    )


def _route(monkeypatch: pytest.MonkeyPatch, bound: SimpleNamespace, *, cell: CellSettings | None) -> Any:
    monkeypatch.setattr(runtime, "bind_connection", lambda *_args, **_kwargs: bound)
    job = SimpleNamespace(connection_revision_id="ecr_frozen", pinned_model=PIN, provider_mode="live", cell=cell)
    routes = _ComparisonRoutes(
        ring=object(), policy=object(), runtime=SimpleNamespace(session_factory=SESSIONS, engine=ENGINE), blob_store=object())
    return routes.route(object(), job)


def _pull(route: Any) -> Any:
    """The adapter inside the crop-publishing wrapper the route of a ``pull`` member always has."""
    assert isinstance(route.adapter, PublishedPullAdapter)
    return route.adapter._adapter


def test_a_job_with_a_cell_on_a_server_member_gets_a_pull_adapter_carrying_the_cells_host_call(monkeypatch: pytest.MonkeyPatch) -> None:
    plain = object()
    route = _route(monkeypatch, _bound(pool="exh_01M2545JSD15ETSNNV904X991M:codex", plain=plain), cell=CELL)

    adapter = _pull(route)
    assert isinstance(adapter, PullAdapter) and adapter is not plain, "the plain adapter the binder made is replaced"
    call = adapter._host_call
    assert isinstance(call, HostCall)
    assert (call.provider, call.access) == ("codex", "subscription"), "the provider is the pool's, the access the connection's billing"
    assert (call.model_id, call.effort, call.max_output_tokens, call.timeout_seconds, call.cell_key) == (
        CELL.model_id, "medium", 1200, 1500, "comparison_pair_check:main")
    assert call.members(900) == {
        "provider": "codex", "access": "subscription", "model_id": CELL.model_id, "effort": "medium", "max_output_tokens": 1200,
        "timeout_seconds": 900, "cell_key": "comparison_pair_check:main",
    }
    assert adapter._engine is ENGINE and adapter._sessions is SESSIONS, "the runtime's engine and sessions reach the adapter it builds"
    assert route.connection_revision_id == "ecr_frozen" and route.expected_model == PIN and route.unmetered is True


def test_the_access_the_host_is_told_is_the_connections_billing(monkeypatch: pytest.MonkeyPatch) -> None:
    metered = _route(monkeypatch, _bound(pool="exh_01M2545JSD15ETSNNV904X991M:claude_code", billing="metered"), cell=CELL)
    call = _pull(metered)._host_call
    assert (call.provider, call.access) == ("claude_code", "api")
    assert metered.unmetered is False


def test_a_job_with_no_cell_gets_the_plain_adapter_and_no_host_call(monkeypatch: pytest.MonkeyPatch) -> None:
    plain = PullAdapter(
        session_factory=SESSIONS, revision=_bound(pool="exh_01M2545JSD15ETSNNV904X991M:codex").revision, context=None, engine=ENGINE)  # type: ignore[arg-type]
    route = _route(monkeypatch, _bound(pool="exh_01M2545JSD15ETSNNV904X991M:codex", plain=plain), cell=None)

    assert _pull(route) is plain
    assert plain._host_call is None


def test_a_cell_on_a_connection_with_no_pool_leaves_the_adapter_as_the_binder_made_it(monkeypatch: pytest.MonkeyPatch) -> None:
    plain = PullAdapter(
        session_factory=SESSIONS, revision=_bound(pool=None).revision, context=None, engine=ENGINE)  # type: ignore[arg-type]
    route = _route(monkeypatch, _bound(pool=None, plain=plain), cell=CELL)

    assert _pull(route) is plain and plain._host_call is None, "only a server's system member is told the cell"


def test_a_cell_whose_model_is_not_the_members_is_refused_by_the_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="names the model of the connection"):
        _route(monkeypatch, _bound(pool="exh_01M2545JSD15ETSNNV904X991M:codex", gateway_model="another-gateway-model"), cell=CELL)
