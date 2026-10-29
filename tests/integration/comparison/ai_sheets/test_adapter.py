"""``ComparisonAiSheetAdapter`` over the real service, with real accounts (`CMP-VC-AISHEET-01`).

What the adapter owns: the roles of the actor (an expert's act, read in the transaction that acts), the keys, the contract's models and
the cursors. The answers are validated by the generated models, so a shape the contract cannot carry fails here.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import ComparisonAiSheetAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import core


def account(lab: Any, label: str, roles: tuple[str, ...]) -> str:
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import SUITE_NAMES, SUITE_PASSWORD, suite_login

    users = UserRepository()
    with lab.db.sessions() as session:
        created = users.create_user(session, suite_login(label), SUITE_PASSWORD)
        accounts = AccountRepository()
        accounts.complete_profile(session, user_uid=str(created.user_uid), email=None, last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
        for role in roles:
            accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
        session.commit()
        return str(created.user_uid)


@pytest.fixture
def adapter(lab: Any) -> ComparisonAiSheetAdapter:
    return ComparisonAiSheetAdapter(lab.db.sessions, comparison_modules="versions", provider_mode="recorded", service=lab.service)


def test_an_expert_starts_the_description_and_the_adapter_answers_the_contracts_models(lab: Any, adapter: ComparisonAiSheetAdapter) -> None:
    expert = account(lab, "sheets-expert", ("expert",))
    estimate = adapter.estimate_series_changes(series_id=lab.world.series, only_failed=False)
    assert isinstance(estimate, models.ComparisonAiEstimate)
    consent = models.ComparisonAiConsent(estimate_digest=estimate.estimate_digest, confirmed=True)
    job = adapter.start_series_changes(series_id=lab.world.series, consent=consent, restart=False, user_uid=expert, idempotency_key="adapter-1")
    assert isinstance(job, models.ComparisonAiJob) and job.consented_by == expert
    for name in ("p1", "p6"):
        lab.record(name)
    lab.record_single("p4")
    lab.record_single("p5")
    lab.drain()
    assert isinstance(adapter.get_series_changes(series_id=lab.world.series), models.ComparisonAiSheetChanges)
    description = adapter.get_sheet_description(sheet_pair_id=lab.world["p1"].pair)
    assert isinstance(description, models.ComparisonSheetDescription) and description.state.value == "done"
    history = adapter.list_sheet_description_history(sheet_pair_id=lab.world["p1"].pair, cursor=None, limit=5)
    assert isinstance(history, models.ComparisonSheetDescriptionHistory) and len(history.items) == 1 and history.page.next_cursor is None
    md = adapter.read_sheet_description_md(sheet_pair_id=lab.world["p1"].pair)
    assert isinstance(md, bytes) and md.decode("utf-8").startswith("### План этажа")
    review = adapter.list_review_sheets(transition_id=lab.world.transition, cursor=None, limit=1)
    assert isinstance(review, models.ComparisonReviewSheetPage) and review.page.next_cursor is not None
    rest = adapter.list_review_sheets(transition_id=lab.world.transition, cursor=review.page.next_cursor, limit=5)
    assert len(review.items) + len(rest.items) == 2 and rest.page.next_cursor is None


def test_an_administrator_without_the_expert_role_is_refused_by_the_adapter_and_nothing_is_written(lab: Any, adapter: ComparisonAiSheetAdapter) -> None:
    admin = account(lab, "sheets-admin", ("admin",))
    estimate = adapter.estimate_series_changes(series_id=lab.world.series, only_failed=False)
    consent = models.ComparisonAiConsent(estimate_digest=estimate.estimate_digest, confirmed=True)
    with pytest.raises(DomainError) as refused:
        adapter.start_series_changes(series_id=lab.world.series, consent=consent, restart=False, user_uid=admin, idempotency_key="adapter-2")
    assert refused.value.code is ErrorCode.PERMISSION_DENIED and refused.value.detail_fields["required_capability"] == "role:expert"
    with pytest.raises(DomainError) as refused:
        adapter.start_sheet_description(sheet_pair_id=lab.world["p1"].pair, consent=consent, user_uid=admin, idempotency_key="adapter-3")
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert lab.db.state("SELECT count(*) FROM comparison_ai_job WHERE method = 'sheet_changes' AND project_uid = :p", p=lab.world.project) == 0
    assert adapter.get_sheet_description(sheet_pair_id=lab.world["p1"].pair).state.value == "not_processed"  # a read is any one role


def test_the_key_of_the_caller_is_the_key_of_the_command(lab: Any, adapter: ComparisonAiSheetAdapter) -> None:
    expert = account(lab, "sheets-expert-2", ("expert",))
    estimate = adapter.estimate_series_changes(series_id=lab.world.series, only_failed=False)
    consent = models.ComparisonAiConsent(estimate_digest=estimate.estimate_digest, confirmed=True)
    first = adapter.start_series_changes(series_id=lab.world.series, consent=consent, restart=False, user_uid=expert, idempotency_key="adapter-key")
    again = adapter.start_series_changes(series_id=lab.world.series, consent=consent, restart=False, user_uid=expert, idempotency_key="adapter-key")
    assert again.job_id == first.job_id and lab.db.state(
        "SELECT count(*) FROM comparison_ai_job WHERE method = 'sheet_changes' AND project_uid = :p", p=lab.world.project) == 1
    paused = adapter.pause_changes_job(job_id=first.job_id, user_uid=expert, idempotency_key="adapter-pause")
    assert paused.state.value == "paused"
    replay = adapter.pause_changes_job(job_id=first.job_id, user_uid=expert, idempotency_key="adapter-pause")
    assert replay.job_id == paused.job_id
    other = models.ComparisonAiConsent(estimate_digest="e" * 64, confirmed=True)
    with pytest.raises(DomainError) as reused:
        adapter.start_series_changes(series_id=lab.world.series, consent=other, restart=False, user_uid=expert, idempotency_key="adapter-key")
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_a_bad_cursor_is_a_validation_failure(lab: Any, adapter: ComparisonAiSheetAdapter) -> None:
    for call in (lambda: adapter.list_review_sheets(transition_id=lab.world.transition, cursor="not-a-cursor", limit=5),
                 lambda: adapter.list_sheet_description_history(sheet_pair_id=lab.world["p1"].pair, cursor="not-a-cursor", limit=5)):
        with pytest.raises(DomainError) as bad:
            call()
        assert bad.value.code is ErrorCode.VALIDATION_FAILED
