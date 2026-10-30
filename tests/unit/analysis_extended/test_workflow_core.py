"""Real independent procedure inputs and conservative lossless source binding."""
from copy import deepcopy
import json
import pytest
from auditmanager.analysis.extended import core
from auditmanager.analysis.extended import workflow as w
from tests.unit.analysis_extended.test_core import plan, VERSION, item, norm_review_reply


def test_old_and_new_exact_policy_and_four_fresh_procedures():
    for version in (core.PLAN_VERSION, w.PLAN_VERSION_V2):
        assert core.enabled(dict(enabled=True, plan_version=version, max_blocks=16))
        assert not core.enabled(dict(enabled=True, plan_version=version, max_blocks=15))
    assert not core.enabled(dict(enabled=True, plan_version=[], max_blocks=16))
    procedures=w.workflow_procedures()
    assert [p['id'] for p in procedures]==['block_analysis','comprehensive_analysis','finding_merge','norm_verification']
    assert all(p['status']=='queued' for p in procedures)
    procedures[0]['status']='completed'
    assert w.workflow_procedures()[0]['status']=='queued'


def test_v2_portal_and_native_plans_have_real_sources_and_frozen_different_identity():
    old,_=plan(1)
    new,_=plan(1,plan_version=w.PLAN_VERSION_V2)
    assert 'workflow_version' not in old and new['workflow_version']==w.WORKFLOW_V2
    assert old['source_sha256']!=new['source_sha256']
    native={'sources':[{'source_id':'native_actual','kind':'image','source_type':'native_page',
        'page_number':1,'crop_sha256':'a'*64,'blob_id':'saved-png','size_bytes':100,'bbox_norm':[0,0,1,1]}],
        'coverage':{'blocks_total':2,'skipped':[{'page_number':2,'reason':'outside_approved_window'}]},
        'warnings':['native_page_window'],'source_sha256':'b'*64}
    value=core.plan_inputs(version_uid=VERSION,section='AR',portal={},manifest={},
        text_layer={'pages':[{'page_number':1,'text':'Реальный текст страницы'}]},graph={},observations=None,
        native_sources=native,plan_version=w.PLAN_VERSION_V2)
    assert value['sources'][0]['source_id']=='native_actual'
    assert value['sources'][0]['source_type']=='native_page'
    assert value['sources'][0]['context'][0]['text']=='Реальный текст страницы'
    assert value['coverage']['blocks_remaining']==2 and value['coverage']['blocks_selected']==1
    with pytest.raises(ValueError,match='require_v2'):
        core.plan_inputs(version_uid=VERSION,section='AR',portal={},manifest={},text_layer={},graph={},
                         observations=None,native_sources=native)


def test_comprehensive_is_independent_request_with_real_visual_and_native_context():
    payload={'visual_observations':[item('image-1')], 'text_observations':[item('text-1')],
        'sources':[{'source_id':'image-1','kind':'image','context':[{'text':'must-not-bypass-bound'}]},
                   {'source_id':'text-1','kind':'text'}],
        'native_context':[{'source_id':'image-1','page_number':1,'text':'Сумма 10+15=30.'*5000}]}
    original=deepcopy(payload)
    request=w.build_comprehensive_request(model_id='selected',run_id='run',section='AR',payload=payload)
    supplied=json.loads(request.body['messages'][0]['content'])
    assert supplied['visual_observations']==payload['visual_observations']
    assert supplied['context_coverage']['characters_provided']==48_000
    assert supplied['context_coverage']['truncated'] is True
    assert 'context' not in supplied['sources'][0] and payload==original
    assert 'арифметическую' in request.body['system'] and 'перекрёстную' in request.body['system']
    assert supplied['source_provenance']['commit'].startswith('3c994817')
    reply=json.dumps({'observations':[item('image-1')|{'source_ids':['image-1','text-1']}]})
    assert core.parse_reply(reply,allowed_sources={'image-1','text-1'})
    with pytest.raises(ValueError):
        core.parse_reply(reply,allowed_sources={'image-1'})


def test_deterministic_merge_preserves_all_observations_and_duplicate_metadata():
    left=item('a')|{'provenance':['first']}
    duplicate=item('b')|{'provenance':['second'],'norm_queries':['Other norm']}
    different=item('c')|{'description':'Другая проблема'}
    original=deepcopy([left,duplicate,different])
    merged=w.deterministic_lossless_merge(original)
    assert len(merged)==2 and merged[0]['source_ids']==['a','b']
    assert merged[0]['norm_queries']==['СП 256','Other norm']
    assert merged[0]['merged_observations']==[left,duplicate]
    assert original==[left,duplicate,different]
    assert len(w.deterministic_lossless_merge([item(str(i))|{'title':str(i)} for i in range(160)]))==160
    with pytest.raises(ValueError):
        w.deterministic_lossless_merge([item()]*161)


def test_norm_procedure_is_exact_partition_and_preserves_source_and_quote():
    before,answer=norm_review_reply()
    answer['norm_queries']=[]
    request=w.build_norm_review_request(model_id='selected',run_id='r',section='AR',payload={'observations':[before]})
    assert 'НЕ объединяй' in request.body['system'] and ':norm-review:' in request.idempotency_scope
    assert request.body['max_tokens']==12_000
    assert w.parse_norm_review(json.dumps({'observations':[answer]}),observations={'one':before})
    for bad in [answer|{'title':'Переписанная проблема'},answer|{'source_ids':['foreign']},
                answer|{'input_ids':['unknown']},answer|{'norm_queries':['new']}]:
        with pytest.raises(ValueError):
            w.parse_norm_review(json.dumps({'observations':[bad]}),observations={'one':before})
    forged=deepcopy(answer);forged['norm_assessment']['citations'][0]['quote']='Поддельная цитата'
    with pytest.raises(ValueError):
        w.parse_norm_review(json.dumps({'observations':[forged]}),observations={'one':before})
    with pytest.raises(ValueError,match='partition'):
        w.parse_norm_review('{"observations":[]}',observations={'one':before})
    with pytest.raises(ValueError,match='window'):
        w.parse_norm_review('{"observations":[]}',observations={str(i):before for i in range(41)})
