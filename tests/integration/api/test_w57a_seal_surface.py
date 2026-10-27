"""The W57a route is role-guarded; `R-146at` serves it for an AR v3 beta Run and refuses before any unverified read."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
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


class _Session:
    """A session stand-in: ``get_norm_verification`` only sets the read snapshot on it."""

    def __init__(self) -> None:
        self.connection_options: dict[str, object] | None = None

    def connection(self, *, execution_options: dict[str, object]) -> None:
        self.connection_options = execution_options

    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _adapter(monkeypatch: pytest.MonkeyPatch, run: SimpleNamespace, session: _Session) -> RunAdapter:
    adapter = RunAdapter.__new__(RunAdapter)
    adapter._sessions = lambda: session  # type: ignore[attr-defined]
    adapter._blob_store = object()  # type: ignore[attr-defined]
    monkeypatch.setattr("auditmanager.runs.RunRepository.get", lambda self, s, run_id: run)
    return adapter


RUN_ID = 'run_01M2545JSD15ETSNNV904X991K'


def test_a_run_of_another_profile_is_not_found_and_nothing_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read = []
    monkeypatch.setattr(
        "auditmanager.runs.v3_norm_report.read_v3_norm_verification",
        lambda *args, **kwargs: read.append(1),
    )
    adapter = _adapter(
        monkeypatch, SimpleNamespace(analysis_profile_id='ap_01M2545JSD15ETSNNV904X991K', state='published'),
        _Session(),
    )
    with pytest.raises(DomainError) as caught:
        adapter.get_norm_verification(run_id=RUN_ID)
    assert caught.value.code is ErrorCode.NOT_FOUND and read == []


@pytest.mark.parametrize('state', ['created', 'queued', 'running', 'validating', 'failed', 'cancelled'])
def test_an_ar_v3_run_that_is_not_terminal_answers_the_declared_503_and_reads_nothing(
    monkeypatch: pytest.MonkeyPatch, state: str,
) -> None:
    read = []
    monkeypatch.setattr(
        "auditmanager.runs.v3_norm_report.read_v3_norm_verification",
        lambda *args, **kwargs: read.append(1),
    )
    adapter = _adapter(
        monkeypatch, SimpleNamespace(analysis_profile_id=str(AR_V3_BETA_PROFILE_ID), state=state),
        _Session(),
    )
    with pytest.raises(DomainError) as caught:
        adapter.get_norm_verification(run_id=RUN_ID)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert caught.value.detail_fields == {'dependency': 'norm_verification_reader'}
    assert read == []


@pytest.mark.parametrize('code', [ErrorCode.ANALYSIS_INPUT_INVALID, ErrorCode.STORAGE_INTEGRITY_ERROR])
def test_a_saved_review_that_fails_verification_answers_the_declared_503_with_no_data(
    monkeypatch: pytest.MonkeyPatch, code: ErrorCode,
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise DomainError(code, reason='published_finding_not_in_review')

    monkeypatch.setattr("auditmanager.runs.v3_norm_report.read_v3_norm_verification", refuse)
    adapter = _adapter(
        monkeypatch, SimpleNamespace(analysis_profile_id=str(AR_V3_BETA_PROFILE_ID), state='published'),
        _Session(),
    )
    with pytest.raises(DomainError) as caught:
        adapter.get_norm_verification(run_id=RUN_ID)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert caught.value.detail_fields == {'dependency': 'norm_verification_reader'}


def test_any_other_failure_of_the_reader_is_not_turned_into_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> None:
        raise DomainError(ErrorCode.INTERNAL_ERROR)

    monkeypatch.setattr("auditmanager.runs.v3_norm_report.read_v3_norm_verification", broken)
    adapter = _adapter(
        monkeypatch, SimpleNamespace(analysis_profile_id=str(AR_V3_BETA_PROFILE_ID), state='published'),
        _Session(),
    )
    with pytest.raises(DomainError) as caught:
        adapter.get_norm_verification(run_id=RUN_ID)
    assert caught.value.code is ErrorCode.INTERNAL_ERROR


def test_the_report_is_read_in_one_repeatable_read_only_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _Session()
    monkeypatch.setattr(
        "auditmanager.runs.v3_norm_report.read_v3_norm_verification",
        lambda *args, **kwargs: (_ for _ in ()).throw(DomainError(ErrorCode.ANALYSIS_INPUT_INVALID)),
    )
    adapter = _adapter(
        monkeypatch, SimpleNamespace(analysis_profile_id=str(AR_V3_BETA_PROFILE_ID), state='published'),
        session,
    )
    with pytest.raises(DomainError):
        adapter.get_norm_verification(run_id=RUN_ID)
    assert session.connection_options == {'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True}
