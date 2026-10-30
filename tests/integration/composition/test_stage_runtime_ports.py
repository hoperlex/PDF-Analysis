"""Positive domain-to-wire mappings for the integrated C4 adapters."""
from sqlalchemy import text

from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import ComparisonStageRunAdapter, ComparisonStageC4Adapter
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.conftest import comparison_engine, comparison_session  # noqa: F401
from tests.integration.comparison.stage_run.test_lifecycle import _scene
from tests.integration.comparison.stage_review.test_service import _fixture, _complete
from tests.support.accounts import complete_expert_account


def test_chain_and_batch_ports_map_durable_records(comparison_session):
    store, _service, _work, _worker, pair, revision, actor, _left, _right = _scene(comparison_session)
    runs = ComparisonStageRunAdapter(store._sessions, comparison_modules='versions,stages')
    c4 = ComparisonStageC4Adapter(store._sessions, comparison_modules='versions,stages')
    request = models.StartStageChainRunRequest(link_revision_id=revision, with_ai=False)
    run = runs.start_run(pair_id=pair, body=request, user_uid=actor, idempotency_key='port-start-'+new_ulid())
    assert run.kind == 'full' and run.with_ai is False and len(run.steps) == 7
    assert runs.get_run(run_id=run.run_id).run_id == run.run_id
    assert runs.list_runs(pair_id=pair, cursor=None, limit=1).items[0].run_id == run.run_id
    stopped = runs.cancel_run(run_id=run.run_id, user_uid=actor, idempotency_key='port-cancel-'+new_ulid())
    assert stopped.state == 'cancelled'
    resumed = c4.resume_run(run_id=run.run_id, body=models.ResumeStageChainRunRequest(),
                           user_uid=actor, idempotency_key='port-resume-'+new_ulid())
    assert resumed.state == 'queued'
    project = comparison_session.execute(text('SELECT project_uid FROM stage_pair WHERE stage_pair_id=:pair'), {'pair': pair}).scalar_one()
    batch = c4.start_batch(project_uid=project, body=models.StartStageChainBatchRequest(with_ai=False,
        selections=[models.StageChainBatchSelection(pair_id=pair, link_revision_id=revision)]),
        user_uid=actor, idempotency_key='port-batch-'+new_ulid())
    assert batch.counts['queued'] == 1
    assert c4.pause_batch(batch_id=batch.batch_id, user_uid=actor, idempotency_key='port-pause-'+new_ulid()).state == 'paused'
    assert c4.resume_batch(batch_id=batch.batch_id, user_uid=actor, idempotency_key='port-resume-batch-'+new_ulid()).state == 'queued'
    assert c4.cancel_batch(batch_id=batch.batch_id, user_uid=actor, idempotency_key='port-stop-'+new_ulid()).state == 'cancelled'


def test_cards_verdicts_and_exports_map_real_evidence(comparison_session):
    service, store, _pair, _revision, _actor, run, item = _fixture(comparison_session)
    service.advance(item, run)
    _complete(comparison_session, run)
    actor = str(complete_expert_account(comparison_session, 'port-'+new_ulid().lower()).user_uid)
    adapter = ComparisonStageC4Adapter(store._sessions, comparison_modules='versions,stages')
    cards = adapter.list_cards(run_id=run, cursor=None, limit=1)
    assert cards.counts['review'] == 1
    card = cards.items[0]
    assert adapter.get_card(card_id=card.card_id).evidence
    verdicts = adapter.apply_verdicts(run_id=run, body=models.ApplyStageCardVerdictsRequest(
        updates=[models.StageCardVerdictInput(card_id=card.card_id, expected_revision=0, decision='accepted', reason='')]),
        user_uid=actor, idempotency_key='port-verdict-'+new_ulid())
    assert verdicts.items[0].card_id == card.card_id
    assert adapter.list_verdicts(card_id=card.card_id, cursor=None, limit=1).items == verdicts.items
    assert adapter.get_journal(run_id=run, grouping='system').accepted_count == 1
    assert adapter.journal_xlsx(run_id=run).startswith(b'PK')
    assert adapter.journal_pdf(run_id=run).startswith(b'%PDF')
    assert b'<!doctype html>' in adapter.journal_html(run_id=run)
    assert adapter.list_ai_reviews(run_id=run, cursor=None, limit=500).items == []
    assert adapter.list_classifications(run_id=run, cursor=None, limit=50).items == []
    assert adapter.get_synthesis(run_id=run, cursor=None, limit=50).items == []
    assert adapter.list_graphics(run_id=run, cursor=None, limit=50).items == []
    assert adapter.list_repairs(run_id=run, cursor=None, limit=50).items == []
