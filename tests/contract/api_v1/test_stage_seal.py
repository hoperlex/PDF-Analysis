"""The C3 routes are keyed expert commands and typed module-gated stubs."""

from __future__ import annotations

import inspect

import pytest

from auditmanager.api.app import create_documentation_app
from auditmanager.api.security import OPERATION_ROLES
from auditmanager.bootstrap.adapters import (
    ComparisonStageLinkAdapter, ComparisonStagePairAdapter, ComparisonStageRunAdapter,
    ComparisonStageTextAdapter, ComparisonStageUploadAdapter,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.support.expected_facts import FACTS

STAGE_OPERATIONS = frozenset(name for _method, _path, name in FACTS.operations[-32:])
ADAPTERS = (
    (ComparisonStagePairAdapter, "comparison_stage_pairs"),
    (ComparisonStageUploadAdapter, "comparison_stage_uploads"),
    (ComparisonStageLinkAdapter, "comparison_stage_links"),
    (ComparisonStageTextAdapter, "comparison_stage_text"),
    (ComparisonStageRunAdapter, "comparison_stage_runs"),
)


def test_all_stage_routes_have_closed_roles_and_keyed_writes() -> None:
    document = create_documentation_app().openapi()
    operations = {operation["operationId"]: (method, operation)
                  for item in document["paths"].values()
                  for method, operation in item.items() if method in {"get", "post", "put"}}
    assert len(STAGE_OPERATIONS) == 32
    assert STAGE_OPERATIONS <= operations.keys()
    for name in STAGE_OPERATIONS:
        method, operation = operations[name]
        assert operation["security"] == [{"bearerAuth": []}]
        keys = [p for p in operation.get("parameters", []) if p.get("name") == "Idempotency-Key"]
        if method == "get":
            assert OPERATION_ROLES[name] == frozenset({"expert", "admin"})
            assert not keys
        else:
            assert OPERATION_ROLES[name] == frozenset({"expert"})
            assert len(keys) == 1 and keys[0]["required"] is True
        for status in ("401", "403", "503"):
            assert status in operation["responses"]


@pytest.mark.parametrize("adapter,dependency", ADAPTERS)
def test_every_sealed_port_method_refuses_before_work(adapter: type, dependency: str) -> None:
    methods = [name for name, value in vars(adapter).items()
               if not name.startswith("_") and callable(value)]
    assert methods
    for modules, expected in (("none", "comparison_modules"),
                              ("versions", "comparison_modules"),
                              ("versions,stages", dependency)):
        port = adapter(comparison_modules=modules)
        for name in methods:
            signature = inspect.signature(getattr(port, name))
            arguments = {parameter.name: None for parameter in signature.parameters.values()}
            with pytest.raises(DomainError) as caught:
                getattr(port, name)(**arguments)
            assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
            assert caught.value.detail_fields == {"dependency": expected}, name
