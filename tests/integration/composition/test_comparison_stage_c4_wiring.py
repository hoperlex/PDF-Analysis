"""C4 routes use the real module-gated services, including exports and expert commands."""
from __future__ import annotations

import pytest

from tests.integration.composition.test_comparison_stage_stub_operations import (
    _client, PATH_VALUES, PRJ, STP, SLK, CPR, SHA,
)
from tests.integration.composition.test_router_answers import static_token
from tests.support.expected_facts import FACTS

C4 = frozenset({
    'estimateStageChainRun', 'resumeStageChainRun', 'startStageChainBatch', 'getStageChainBatch',
    'pauseStageChainBatch', 'resumeStageChainBatch', 'cancelStageChainBatch', 'listStageAiReviews',
    'listStageClassifications', 'getStageSynthesis', 'listStageGraphicEvidence', 'listStageLinkRepairs',
    'undoStageLinkRepair', 'listStageChangeCards', 'getStageChangeCard', 'applyStageCardVerdicts',
    'listStageCardVerdicts', 'getStageChangeJournal', 'streamStageChangeJournalXlsx',
    'streamStageChangeJournalPdf', 'streamStageChangeJournalHtml', 'getStageProfileText', 'getStageAssembly',
})
UID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
VALUES = PATH_VALUES | {'stage_chain_batch_id': 'scb_'+UID, 'stage_link_repair_id': 'crp_'+UID,
    'stage_change_card_id': 'ccd_'+UID, 'comparison_page_profile_id': CPR, 'page_profile_id': CPR}
BODIES = {
    'resumeStageChainRun': {}, 'undoStageLinkRepair': {'base_revision_id': SLK},
    'startStageChainBatch': {'with_ai': False, 'selections': [{'pair_id': STP, 'link_revision_id': SLK}]},
    'applyStageCardVerdicts': {'updates': [{'card_id': 'ccd_'+UID, 'expected_revision': 0,
        'decision': 'accepted', 'reason': ''}]},
}
OPERATIONS = tuple(row for row in FACTS.operations if row[2] in C4)


@pytest.fixture(scope='module', params=['none', 'versions,stages'])
def client(request):
    with _client(str(request.param)) as app:
        yield app, str(request.param)


def test_all_c4_operations_are_named():
    assert len(OPERATIONS) == len(C4) == 23


@pytest.mark.parametrize('method,path,name', OPERATIONS, ids=[r[2] for r in OPERATIONS])
def test_real_c4_port_refuses_missing_scope_or_disabled_module(client, method, path, name):
    app, modules = client
    for key, value in VALUES.items():
        path = path.replace('{'+key+'}', value)
    assert '{' not in path, (name, path)
    headers = {'Authorization': f'Bearer {static_token()}'}
    kwargs = {}
    if method.lower() != 'get':
        headers['Idempotency-Key'] = f'c4-wiring-{name}'
        if name in BODIES:
            kwargs['json'] = BODIES[name]
    response = app.request(method, path, headers=headers, **kwargs)
    body = response.json()
    assert response.status_code == (503 if modules == 'none' else 404), (name, response.status_code, body)
    if modules == 'none':
        assert body['details'] == {'dependency': 'comparison_modules'}
    else:
        assert body['error_code'] == 'not_found'
