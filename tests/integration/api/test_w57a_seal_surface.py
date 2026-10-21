"""The W57a route is role-guarded and refuses before any unverified read."""

from __future__ import annotations

import pytest

from auditmanager.api.app import create_documentation_app
from auditmanager.api.security import OPERATION_ROLES
from auditmanager.bootstrap.adapters import RunAdapter
from auditmanager.shared.errors import DomainError, ErrorCode


def test_operation_is_served_with_any_role_register() -> None:
    app = create_documentation_app()
    operation = app.openapi()['paths']['/runs/{run_id}/norm-verification']['get']
    assert operation['operationId'] == 'getRunNormVerification'
    assert OPERATION_ROLES['getRunNormVerification'] == frozenset({'expert', 'admin'})
    assert '503' in operation['responses']


def test_shipping_adapter_has_typed_refusal_without_touching_storage() -> None:
    adapter = RunAdapter.__new__(RunAdapter)
    with pytest.raises(DomainError) as caught:
        adapter.get_norm_verification(run_id='run_01M2545JSD15ETSNNV904X991K')
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert caught.value.detail_fields == {'dependency': 'norm_verification_reader'}
