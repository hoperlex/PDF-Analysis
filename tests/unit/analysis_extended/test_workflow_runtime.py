from hashlib import sha256
from types import SimpleNamespace as NS
import io,json,zipfile
from pathlib import Path
import pytest
from auditmanager.analysis.public import ProviderConfig,ProviderMode,ModelResponse,CostMeter,ArtifactRef
from auditmanager.analysis.extended.native_pages import prepare_native_page_sources
from auditmanager.runs import extended_review as runtime
from auditmanager.storage.public import derive_blob_id
from tests.unit.analysis_extended.test_core import documents,VERSION,item
from tests.unit.analysis_extended.test_runtime import Session,Store,Jobs,Journal


class NativeStore:
    def __init__(self,data): self.data=data;self.saved={}
    def inspect(self,bid):return NS(sha256=sha256(self.data).hexdigest(),size=len(self.data))
    def open_stream(self,*_,**__):yield self.data
    def put_blob(self,data,**kwargs):
        bid=str(derive_blob_id(sha256=kwargs['declared_sha256'],size=len(data)));self.saved[bid]=data
        return NS(blob_id=bid,sha256=kwargs['declared_sha256'],size=len(data),media_type='image/png')


def test_native_helper_renders_actual_pdf_and_keeps_real_page_provenance_and_remainder():
    with zipfile.ZipFile('fixtures/presentation-hotfix/AR-native-image-portal.zip') as bundle:
        data=bundle.read(next(n for n in bundle.namelist() if n.endswith('.pdf')))
    store=NativeStore(data);sha=sha256(data).hexdigest()
    source=ArtifactRef('source.document',str(derive_blob_id(sha256=sha,size=len(data))),sha,len(data),'application/pdf')
    result=prepare_native_page_sources(version_uid=VERSION,source_ref=source,blob_store=store,max_pages=2)
    assert len(result['sources'])==2 and result['coverage']['blocks_total']==8
    assert result['coverage']['blocks_remaining']==8 and len(result['coverage']['skipped'])==6
    assert all(s['source_type']=='native_page' and s['source_id'].startswith('native_') and s['source_sha256']==sha for s in result['sources'])
    assert all(raw.startswith(b'\x89PNG') for raw in store.saved.values())
    assert len(result['artifacts'])==2 and all(r.role=='analysis.extended_crop' for r in result['artifacts'])


class WorkflowAdapter:
    provider_mode=ProviderMode.RECORDED
    def __init__(self,bad_norm=False):self.requests=[];self.bad_norm=bad_norm
    def complete(self,request):
        self.requests.append(request);payload=json.loads(request.body['messages'][0]['content'])
        if request.images_bytes:
            values=[item(payload['sources'][0]['source_id'])]
        elif payload.get('procedure')=='comprehensive_analysis':
            assert payload['native_context'][0]['text']=='Настоящий текст страницы'
            values=[item(payload['native_context'][0]['source_id'])|{'title':'Комплексная сверка'}]
        else:
            quotes={c['paragraph_id']:c['quote'] for c in payload['norm_context']};values=[]
            for original in payload['observations']:
                refs=original['norm_candidate_ids']
                assessment=None if not refs else {'relation':'insufficient','explanation':'Требует экспертной сверки',
                    'citations':[{'paragraph_id':refs[0],'quote':'forged' if self.bad_norm else quotes[refs[0]]}]}
                values.append({k:original[k] for k in ('title','description','source_ids')}|
                    {'norm_queries':[],'input_ids':[original['input_id']],'norm_assessment':assessment})
        return ModelResponse(json.dumps({'observations':values}), 'end_turn',100,100,1)


@pytest.mark.parametrize('corpus,bad_norm,native_mode',[(False,False,False),(True,False,False),(True,True,False),(True,False,True),(True,False,'text_only'),(True,False,'mismatch')])
def test_v2_runtime_true_phases_four_call_cap_and_originals_survive_bad_norm(monkeypatch,corpus,bad_norm,native_mode):
    portal,manifest,blobs=documents(10)
    docs={'geometry.portal_blocks':portal,'geometry.page_crops':manifest,
        'prepared.text_layer':{'pages':[{'page_number':i,'text':'Настоящий текст страницы'} for i in range(1,11)]},
        'context.document_graph':{'sections':[]}}
    for role,doc in docs.items():blobs[role]=json.dumps(doc).encode()
    monkeypatch.setattr(runtime,'DocumentRepository',lambda:NS(get_version=lambda *_:NS(classification=NS(section_code='AR'))))
    import auditmanager.analysis.public as public
    monkeypatch.setattr(public,'read_artifact',lambda _store,bid,**_: (docs[str(bid)],'a'*64))
    if native_mode:
        native_sources=[]
        for crop in manifest['crops']:
            native_sources.append({'source_id':'native_'+sha256(crop['portal_block_id'].encode()).hexdigest()[:32],
                'kind':'image','source_type':'native_page','version_uid':VERSION,'page_number':crop['page_number'],
                'bbox_norm':[0.,0.,1.,1.],'crop_sha256':crop['sha256'],'blob_id':crop['blob_id'],
                'size_bytes':crop['size_bytes'],'context':[]})
        if native_mode in {'text_only','mismatch'}:
            for block in portal['blocks']:
                block['block_type']='text'
                if native_mode=='mismatch':block['geometry']='geometry_mismatch'
            if native_mode=='mismatch':
                for page in portal['pages']:page['geometry']='geometry_mismatch'
            manifest['crops']=[]
        else:
            docs.pop('geometry.portal_blocks');docs.pop('geometry.page_crops')
        def prepare_native(**kwargs):
            assert native_mode!='mismatch','known portal geometry refusal bypassed by native rendering'
            return {'sources':native_sources,'artifacts':(),
                'coverage':{'blocks_total':10,'blocks_selected':10,'blocks_processed':0,'blocks_remaining':10,'skipped':[]},
                'warnings':['native_pdf_page_render_no_ocr'],'source_sha256':'f'*64}
        monkeypatch.setattr(public,'prepare_native_page_sources',prepare_native)

    monkeypatch.setattr(runtime,'parse_blob_id',lambda x:x)
    monkeypatch.setattr(runtime,'extended_unit',lambda *_args,**_kw:None)
    monkeypatch.setattr(runtime,'search_norms',lambda _session,**kwargs:NS(items=(NS(norms_snapshot_id='snapshot',norm_document_id='doc',
        norm_paragraph_id='paragraph',designation='СП',clause_number='1',fragment=NS(text='Реальная цитата'),page_label=1),)))
    adapter=WorkflowAdapter(bad_norm);saved=[];journal=Journal()
    def publish(role,doc):
        raw=json.dumps(doc).encode();key='reply'+str(len(blobs));blobs[key]=raw
        return NS(blob_id=key,sha256=sha256(raw).hexdigest(),size_bytes=len(raw))
    result=runtime.run_extended_review(Session(),run=NS(run_id='run',version_uid=VERSION),authority=NS(),jobs=Jobs(),journal=journal,
        binding=NS(adapter=adapter,config=ProviderConfig(ProviderMode.RECORDED,'claude-opus-5',20.,None,False),call=None),
        outputs=NS(refs={**{k:NS(blob_id=k) for k in docs},'source.document':NS(blob_id='source')}),store=Store(blobs),meter=CostMeter(20.),publish=publish,
        progress=lambda status,value:saved.append((status,json.loads(json.dumps(value)))),checkpoint=lambda _:None,
        observations_document=None,snapshot_id='snapshot' if corpus else None,
        policy={'enabled':True,'max_blocks':16,'plan_version':'extended-review-v2'})
    assert len(adapter.requests)==(2 if native_mode=='mismatch' else 4 if corpus else 3)
    assert [len(r.images_bytes) for r in adapter.requests[:3]]==([0,0] if native_mode=='mismatch' else [8,2,0])
    assert result['workflow_version']=='extended-review-v2'
    procedures={p['id']:p['status'] for p in result['procedures']}
    assert procedures['block_analysis']==('unavailable' if native_mode=='mismatch' else 'completed')
    assert procedures['comprehensive_analysis']=='completed' and procedures['finding_merge']=='completed'
    assert procedures['norm_verification']==('unavailable' if not corpus else 'failed' if bad_norm else 'completed')
    assert len(result['observations'])==(1 if native_mode=='mismatch' else 2)
    assert sum(len(o.get('merged_observations',[o])) for o in result['observations'])==(1 if native_mode=='mismatch' else 3)
    assert saved[-1][0]==('partial' if not corpus or native_mode=='mismatch' else 'failed' if bad_norm else 'completed')
    assert all(p['status']=='queued' for p in saved[0][1]['procedures'])


def test_fresh_full_document_policy_reviews_all_forty_seven_blocks_and_pages(monkeypatch):
    portal, manifest, blobs = documents(47)
    docs = {'geometry.portal_blocks': portal, 'geometry.page_crops': manifest,
        'prepared.text_layer': {'pages': [{'page_number': i, 'text': 'Настоящий текст страницы'}
            for i in range(1, 48)]}, 'context.document_graph': {'sections': []}}
    for role, doc in docs.items():
        blobs[role] = json.dumps(doc).encode()
    monkeypatch.setattr(runtime, 'DocumentRepository', lambda: NS(get_version=lambda *_: NS(
        classification=NS(section_code='AR'), page_count=47)))
    import auditmanager.analysis.public as public
    monkeypatch.setattr(public, 'read_artifact', lambda _store, bid, **_: (docs[str(bid)], 'a'*64))
    monkeypatch.setattr(runtime, 'parse_blob_id', lambda value: value)
    monkeypatch.setattr(runtime, 'extended_unit', lambda *_args, **_kw: None)
    monkeypatch.setattr(runtime, 'search_norms', lambda _session, **kwargs: NS(items=(NS(
        norms_snapshot_id='snapshot', norm_document_id='doc', norm_paragraph_id='paragraph',
        designation='СП', clause_number='1', fragment=NS(text='Реальная цитата'), page_label=1),)))
    adapter = WorkflowAdapter()
    saved = []
    def publish(_role, doc):
        raw = json.dumps(doc).encode()
        key = 'reply' + str(len(blobs))
        blobs[key] = raw
        return NS(blob_id=key, sha256=sha256(raw).hexdigest(), size_bytes=len(raw))
    result = runtime.run_extended_review(Session(), run=NS(run_id='run', version_uid=VERSION),
        authority=NS(), jobs=Jobs(), journal=Journal(),
        binding=NS(adapter=adapter, config=ProviderConfig(ProviderMode.RECORDED, 'claude-opus-5', 50., None, False), call=None),
        outputs=NS(refs={k: NS(blob_id=k) for k in docs}), store=Store(blobs), meter=CostMeter(50.),
        publish=publish, progress=lambda status, value: saved.append(status), checkpoint=lambda _: None,
        observations_document=None, snapshot_id='snapshot',
        policy={'enabled': True, 'max_blocks': 'all', 'plan_version': 'extended-review-v2'})
    assert result['coverage']['blocks_processed'] == result['coverage']['blocks_selected'] == 47
    assert result['coverage']['blocks_remaining'] == 0
    assert not result['coverage']['skipped']
    assert len([r for r in adapter.requests if r.images_bytes]) == 6
    assert len([r for r in adapter.requests if json.loads(r.body['messages'][0]['content']).get('procedure') == 'comprehensive_analysis']) == 6
    assert {p['status'] for p in result['procedures']} == {'completed'}
    assert saved[-1] == 'completed'


def test_full_comprehensive_batches_cover_every_character_without_provider_truncation():
    pages = [{'page_number': 1, 'text': 'A' * 90_001}, {'page_number': 2, 'text': 'B' * 19_001}]
    state = {'sources': [], 'text_items': [], 'source_sha256': 'a'*64, 'coverage': {'blocks_total': 0}}
    seen = []
    def answer(request, _phase):
        payload = json.loads(request.body['messages'][0]['content'])
        assert payload['context_coverage']['truncated'] is False
        seen.extend(payload['native_context'])
        return NS(output_text='{"observations":[]}')
    assert runtime._full_comprehensive_review(run=NS(run_id='run', version_uid=VERSION),
        model_id='claude-opus-5', section='AR', state=state, pages=pages,
        block_items=[], call=answer) == []
    for page in pages:
        assert ''.join(context['text'] for context in seen if context['page_number'] == page['page_number']) == page['text']
    assert len(seen) == 4


def test_full_norm_review_processes_all_observations_in_multiple_calls(monkeypatch):
    sources = [{'source_id': f'source-{index}', 'kind': 'text', 'page_number': index}
        for index in range(41)]
    observations = [{'title': f'Наблюдение {index}', 'description': 'Сверить',
        'source_ids': [source['source_id']], 'norm_queries': ['СП 1'], 'norm_candidates': []}
        for index, source in enumerate(sources)]
    state = {'sources': sources, 'observations': observations, 'source_sha256': 'a'*64, 'warnings': []}
    monkeypatch.setattr(runtime, 'search_norms', lambda _session, **kwargs: NS(items=(NS(
        norms_snapshot_id='snapshot', norm_document_id='doc', norm_paragraph_id='paragraph',
        designation='СП', clause_number='1', fragment=NS(text='Реальная цитата'), page_label=1),)))
    calls, phases = [], []
    def answer(request, identity):
        calls.append(identity)
        payload = json.loads(request.body['messages'][0]['content'])
        values = []
        for original in payload['observations']:
            values.append({k: original[k] for k in ('title', 'description', 'source_ids')} |
                {'norm_queries': [], 'input_ids': [original['input_id']], 'norm_assessment': {
                    'relation': 'insufficient', 'explanation': 'Требует проверки',
                    'citations': [{'paragraph_id': 'paragraph', 'quote': 'Реальная цитата'}]}})
        return NS(output_text=json.dumps({'observations': values}))
    runtime._full_norm_verification(session=Session(), run=NS(run_id='run'),
        model_id='claude-opus-5', section='AR', state=state, snapshot_id='snapshot',
        call=answer, phase=lambda *args: phases.append(args), checkpoint=lambda _: None)
    assert len(calls) == 2
    assert phases == [('norm_verification', 'completed')]
    assert all(item['norm_assessment']['relation'] == 'insufficient' for item in observations)


def test_planned_v2_receipt_has_queued_phases_and_terminal_skip_reason():
    queued=runtime.planned_workflow_result()
    assert len(queued['procedures'])==4 and all(p['status']=='queued' for p in queued['procedures'])
    stopped=runtime.planned_workflow_result(reason='provider_outcome_unknown',terminal=True)
    assert all(p['status']=='skipped' and p['reason']=='provider_outcome_unknown' for p in stopped['procedures'])


@pytest.mark.parametrize('state,policy,expected_status,expected_procedures',[
    ('queued',{'enabled':True,'max_blocks':16,'plan_version':'extended-review-v2'},'not_started',4),
    ('failed',{'enabled':True,'max_blocks':16,'plan_version':'extended-review-v2'},'unavailable',4),
    ('published',None,'unavailable',0),
])
def test_read_helper_exposes_planned_or_terminal_skip_receipt_without_blob_reads(monkeypatch,state,policy,expected_status,expected_procedures):
    class Context:
        def __enter__(self):return Session()
        def __exit__(self,*_):pass
    monkeypatch.setattr(runtime,'RunRepository',lambda:NS(get=lambda *_:NS(state=state),stage_results=lambda *_:[]))
    import auditmanager.runs.cost_policy as cost
    monkeypatch.setattr(cost,'read_run_cost_policy',lambda *_,**__:NS(extended_review=policy))
    value=runtime.read_extended_review(Context,None,'run')
    assert value['status']==expected_status and len(value['result']['procedures'])==expected_procedures
    if state=='failed':assert all(p['status']=='skipped' for p in value['result']['procedures'])
