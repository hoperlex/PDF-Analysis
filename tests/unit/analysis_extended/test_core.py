from __future__ import annotations
from copy import deepcopy
import json

import pytest
from auditmanager.analysis.extended.core import (enabled, plan_inputs, parse_reply, build_request,
    finalize_items, digest)
from auditmanager.storage.public import derive_blob_id

VERSION = 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAV'


def documents(count=18):
    from hashlib import sha256
    portal = {'artifact_role':'geometry.portal_blocks','artifact_version':'1.0.0','version_uid':VERSION,
        'blocks_sha256':'a'*64,'pages':[],'blocks':[]}
    manifest = {'artifact_role':'geometry.page_crops','artifact_version':'1.0.0','version_uid':VERSION,
        'crop_policy':'portal_image_blocks','crops':[]}
    blobs = {}
    for i in range(1, count+1):
        block = 'blk_'+f'{i:032x}'
        portal['pages'].append({'page_number':i,'width_px':2000,'height_px':1000,'rotation_deg':0,'geometry':'ok'})
        portal['blocks'].append({'portal_block_id':block,'page_number':i,'page_label':i,'ordinal':0,
            'block_type':'image','status':'complete','bbox_norm':[.1,.2,.8,.7],'geometry':'ok'})
        raw = b'\x89PNG\r\n\x1a\n'+str(i).encode()
        sha=sha256(raw).hexdigest();bid=str(derive_blob_id(sha256=sha,size=len(raw)))
        blobs[bid]=raw
        manifest['crops'].append({'portal_block_id':block,'page_number':i,'bbox_norm':[.1,.2,.8,.7],
            'render_profile':{'renderer':'recorded','scale':4.,'min_long_side_px':800,'max_pixels':4_000_000,'format':'png'},
            'blob_id':bid,'sha256':sha,'size_bytes':len(raw),'width_px':1000,'height_px':500})
    return portal,manifest,blobs


def plan(count=18, **changes):
    portal,manifest,blobs=documents(count)
    kwargs=dict(version_uid=VERSION,section='AR',portal=portal,manifest=manifest,
        text_layer={'pages':[{'page_number':i,'text':f'Текст страницы {i}'} for i in range(1,count+1)]},
        graph={'sections':[{'title':'Исходные данные'}]},observations=None)
    kwargs.update(changes)
    return plan_inputs(**kwargs),blobs


def test_only_new_exact_frozen_policy_enables_paid_calls():
    assert not enabled(None) and not enabled({})
    assert enabled({'enabled':True,'max_blocks':16,'plan_version':'extended-review-v1'})
    for change in [{'enabled':False},{'max_blocks':17},{'max_blocks':True},{'plan_version':'next'}]:
        assert not enabled({'enabled':True,'max_blocks':16,'plan_version':'extended-review-v1'}|change)


def test_complete_geometry_projects_only_sixteen_and_explicitly_keeps_remainder():
    value,_=plan()
    assert value['coverage']=={'blocks_total':18,'blocks_selected':16,'blocks_processed':0,'blocks_remaining':18,
        'skipped':[{'block_id':'blk_'+f'{i:032x}','page_number':i,'reason':'outside_approved_window'} for i in [17,18]]}
    assert len(value['sources'])==16
    assert value['sources'][0]['bbox_norm']==[.1,.2,.8,.7]
    assert len(value['sources'][0]['context'])==2
    assert value['warnings']==['remaining_blocks_not_reviewed']


def test_fresh_full_document_plan_selects_every_available_image_without_skips():
    value, _ = plan(47, plan_version='extended-review-v2', full_document=True)
    assert value['coverage']['blocks_total'] == value['coverage']['blocks_selected'] == 47
    assert value['coverage']['skipped'] == []
    assert value['review_scope'] == 'full_document'
    assert len(value['sources']) == 47
    old, _ = plan(47, plan_version='extended-review-v2')
    assert old['source_sha256'] != value['source_sha256']


def test_full_document_plan_keeps_text_observations_beyond_legacy_forty():
    observations = {'observations': [{'category': 'internal_contradiction',
        'finding_text': f'Сверка {index}', 'evidence': [{'page_number': 1, 'quote': 'Источник'}]}
        for index in range(41)]}
    full, _ = plan(1, observations=observations, plan_version='extended-review-v2', full_document=True)
    legacy, _ = plan(1, observations=observations, plan_version='extended-review-v2')
    assert len(full['text_items']) == 41
    assert len(legacy['text_items']) == 40
    assert 'text_observations_outside_merge_window' not in full['warnings']


def test_context_and_source_digest_bind_saved_ocr_without_native_quote_fabrication():
    original,_=plan(1)
    with_ocr,_=plan(1,recognised={'entries':[{'kind':'recognised_text','page_number':1,'text':'OCR marker'}]})
    assert with_ocr['source_sha256'] != original['source_sha256']
    assert with_ocr['sources'][0]['context'][0]['recognised_context']=='OCR marker'
    assert 'quote' not in with_ocr['sources'][0]


def test_inconsistent_crop_cohort_is_refused_without_selecting_a_fake_region():
    portal,manifest,_=documents(1)
    manifest['crops'][0]['bbox_norm']=[.2,.2,.9,.8]
    with pytest.raises(ValueError):
        plan_inputs(version_uid=VERSION,section='EOM',portal=portal,manifest=manifest,
                    text_layer={'pages':[]},graph={},observations=None)


def item(source='blk_1'):
    return {'title':'Сверка','description':'Уточнить обозначение аппарата','source_ids':[source],'norm_queries':['СП 256']}


def test_reply_sources_are_closed_and_have_no_expert_verdict_or_fake_quote():
    assert parse_reply(json.dumps({'observations':[item()]}),allowed_sources={'blk_1'})==[item()]
    result=finalize_items([item()],[{'source_id':'blk_1','kind':'image'}])
    assert result[0]['source_kind']=='image' and result[0]['status']=='requires_expert_review'
    assert result[0]['norm_status']=='unavailable'
    for replacement in [item('foreign'),item()|{'expert_verdict':'accepted'},item()|{'source_ids':[]},item()|{'description':'x'*3001}]:
        with pytest.raises(ValueError):
            parse_reply(json.dumps({'observations':[replacement]}),allowed_sources={'blk_1'})


def test_whole_reply_rejects_duplicate_keys_and_more_than_forty_items():
    with pytest.raises(ValueError):
        parse_reply('{"observations":[],"observations":[]}',allowed_sources=set())
    with pytest.raises(ValueError):
        parse_reply(json.dumps({'observations':[item()]*41}),allowed_sources={'blk_1'})


def test_multimodal_prompt_is_not_the_text_only_profile_wrapper():
    request=build_request(model_id='selected',run_id='run',phase='blocks',section='EOM',payload={'sources':[]})
    assert 'изображения' in request.body['system'] and 'EOM' in request.body['system']
    assert request.body['max_tokens']==6000
    assert 'source_ids' in request.body['output_config']['format']['schema']['properties']['observations']['items']['required']


def test_merge_binds_input_ids_to_their_exact_source_union():
    source='blk_1';original=item(source)
    merged=original|{'input_ids':['one'],'norm_assessment':None}
    assert parse_reply(json.dumps({'observations':[merged]}),allowed_sources={source},expected_inputs={'one':original})==[merged]
    for change in [{'input_ids':['foreign']},{'source_ids':['other']},{'input_ids':[]}]:
        with pytest.raises(ValueError):
            parse_reply(json.dumps({'observations':[merged|change]}),allowed_sources={source,'other'},expected_inputs={'one':original})


def norm_review_reply():
    original=item()|{'norm_candidates':[{'paragraph_id':'paragraph-1','quote':'Подлинная цитата корпуса'}]}
    output=item()|{'input_ids':['one'],'norm_assessment':{'relation':'supports','explanation':'Цитата указывает на условие, которое нужно сверить с проектом',
        'citations':[{'paragraph_id':'paragraph-1','quote':'Подлинная цитата корпуса'}]}}
    return original,output


def test_norm_review_accepts_only_the_actual_provided_quote_and_retains_expert_status():
    original,output=norm_review_reply()
    parsed=parse_reply(json.dumps({'observations':[output]}),allowed_sources={'blk_1'},expected_inputs={'one':original})
    assert parsed[0]['norm_assessment']['citations'][0]['quote']=='Подлинная цитата корпуса'
    result=finalize_items(parsed,[{'source_id':'blk_1','kind':'image'}])
    assert result[0]['status']=='requires_expert_review'


@pytest.mark.parametrize('citation',[
    {'paragraph_id':'forged','quote':'Подлинная цитата корпуса'},
    {'paragraph_id':'paragraph-1','quote':'Изменённая цитата'},
    {'paragraph_id':'paragraph-1'},
])
def test_norm_review_refuses_forged_reference_changed_or_missing_quote(citation):
    original,output=norm_review_reply();output['norm_assessment']['citations']=[citation]
    with pytest.raises(ValueError):
        parse_reply(json.dumps({'observations':[output]}),allowed_sources={'blk_1'},expected_inputs={'one':original})


def test_norm_review_cannot_claim_an_assessment_without_available_candidate_context():
    _,output=norm_review_reply()
    with pytest.raises(ValueError):
        parse_reply(json.dumps({'observations':[output]}),allowed_sources={'blk_1'},expected_inputs={'one':item()})
