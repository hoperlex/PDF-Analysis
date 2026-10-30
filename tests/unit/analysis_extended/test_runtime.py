from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
from types import SimpleNamespace as NS
import json
import pytest
from auditmanager.analysis.public import ModelResponse, ProviderConfig, ProviderMode, CostMeter
from auditmanager.runs import extended_review as runtime
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.analysis_extended.test_core import documents, VERSION, item


class Session:
    def commit(self):pass
    def rollback(self):pass


class Store:
    def __init__(self, values):self.values=values
    def read(self,bid,**_):return self.values[str(bid)]


class Adapter:
    provider_mode=ProviderMode.RECORDED
    def __init__(self,bad_merge=False):self.requests=[];self.bad_merge=bad_merge
    def complete(self, request):
        self.requests.append(request)
        payload=json.loads(request.body['messages'][0]['content'])
        if request.images_bytes:
            assert len(request.images_bytes)<=8
            value=[item(payload['sources'][0]['source_id'])]
        else:
            value=[]
            context={c['paragraph_id']:c for c in payload['norm_context']}
            for source_item in payload['observations']:
                candidates=source_item['norm_candidate_ids']
                assessment=None
                if candidates:
                    paragraph=context[candidates[0]]
                    assert paragraph['quote']=='Текст корпуса' and paragraph['snapshot_id']=='snapshot'
                    assessment={'relation':'insufficient','explanation':'Цитата не раскрывает условие проекта',
                                'citations':[{'paragraph_id':paragraph['paragraph_id'],'quote':paragraph['quote']}]}
                value.append({k:source_item[k] for k in ('title','description','source_ids')} | {
                    'norm_queries':[], 'input_ids':[source_item['input_id']], 'norm_assessment':assessment})
        if not request.images_bytes and self.bad_merge:
            value[0]['norm_assessment']['citations'][0]['quote']='Поддельная цитата'
        return ModelResponse(json.dumps({'observations':value}), 'end_turn',100,100,1)


class Jobs:
    def __init__(self):self.n=0
    def require_current(self,*_):pass
    def prepare_provider_call(self,*_,**kwargs):
        self.n+=1
        return 'mc_'+f'{self.n:026d}'


class Journal:
    def __init__(self):self.calls=[]
    def response_received(self,*_):pass
    def complete(self, record):self.calls.append(record)
    def not_processed(self,*_):pass
    def outcome_unknown(self,*_):pass


@pytest.mark.parametrize('corpus_available,bad_merge',[(False,False),(True,False),(True,True)])
def test_recorded_full_path_uses_two_image_batches_and_one_merge_and_explicit_remaining(monkeypatch,corpus_available,bad_merge):
    portal,manifest,blobs=documents(18)
    docs={'geometry.portal_blocks':portal,'geometry.page_crops':manifest,
          'prepared.text_layer':{'pages':[{'page_number':i,'text':'План'} for i in range(1,19)]},
          'context.document_graph':{'sections':[]}}
    for role,doc in docs.items():blobs[role]=json.dumps(doc).encode()
    monkeypatch.setattr(runtime,'DocumentRepository',lambda:NS(get_version=lambda *_:NS(classification=NS(section_code='AR'))))
    import auditmanager.analysis.public as public
    monkeypatch.setattr(public,'read_artifact',lambda _store,bid,**_: (docs[str(bid)],'a'*64))
    # Artifact readers accept opaque persisted refs; this test replaces only their verified read seam.
    monkeypatch.setattr(runtime,'parse_blob_id',lambda x:x)
    monkeypatch.setattr(runtime,'extended_unit',lambda *_args,**_kw:None)
    if corpus_available:
        monkeypatch.setattr(runtime,'search_norms',lambda _session,**kwargs:NS(items=(NS(
            norms_snapshot_id=kwargs['norms_snapshot_id'],norm_document_id='doc',norm_paragraph_id='paragraph',
            designation='СП',clause_number='1.1',fragment=NS(text='Текст корпуса'),page_label=2),)))
    adapter=Adapter(bad_merge);jobs=Jobs();journal=Journal();saved=[];replies=[]
    def publish(role,doc):
        replies.append(doc)
        raw=json.dumps(doc).encode();key='reply'+str(len(replies));blobs[key]=raw
        return NS(blob_id=key,sha256=sha256(raw).hexdigest(),size_bytes=len(raw))
    binding=NS(adapter=adapter,config=ProviderConfig(ProviderMode.RECORDED,'claude-opus-5',20.,None,False),call=None)
    result=runtime.run_extended_review(Session(),run=NS(run_id='run',version_uid=VERSION),authority=NS(),
        jobs=jobs,journal=journal,binding=binding,outputs=NS(refs={k:NS(blob_id=k) for k in docs}),
        store=Store(blobs),meter=CostMeter(20.),publish=publish,progress=lambda status,value:saved.append((status,value)),
        checkpoint=lambda _:None,observations_document=None,snapshot_id='snapshot' if corpus_available else None)
    assert len(adapter.requests)==3 and [len(r.images_bytes) for r in adapter.requests]==[8,8,0]
    assert len(journal.calls)==3 and jobs.n==3
    assert result['coverage']['blocks_processed']==16 and result['coverage']['blocks_remaining']==2
    assert saved[-1][0]==('failed' if bad_merge else 'partial')
    assert len(result['observations'])==2
    assert all(x['norm_status']==('candidates' if corpus_available else 'unavailable') for x in result['observations'])
    assert all((x.get('norm_assessment') is not None)==(corpus_available and not bad_merge) for x in result['observations'])
    assert all(x['status']=='requires_expert_review' for x in result['observations'])
    assert all('extended_reply_blob_id' in record.parameters for record in journal.calls)


def test_unknown_effect_is_fenced_before_another_adapter_call(monkeypatch):
    def refuse(*_,**__):raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,stage_id='text_analysis',reason='extended_provider_outcome_unknown')
    monkeypatch.setattr(runtime,'extended_unit',refuse)
    adapter=Adapter()
    from auditmanager.analysis.extended.core import build_request
    with pytest.raises(DomainError):
        runtime._call(Session(),run_id='run',authority=NS(),jobs=Jobs(),journal=Journal(),
            binding=NS(adapter=adapter,call=None),request=build_request(model_id='claude-opus-5',run_id='run',phase='merge',section='AR',payload={}),
            phase='merge',source_sha256='a'*64,meter=CostMeter(2.),store=None,publish=None,checkpoint=lambda _:None)
    assert adapter.requests==[]


def test_saved_reply_replay_checks_digest_and_makes_no_adapter_call(monkeypatch):
    from auditmanager.analysis.extended.core import build_request
    request=build_request(model_id='claude-opus-5',run_id='run',phase='merge',section='AR',payload={})
    response=ModelResponse('{"observations":[]}','end_turn',10,10,1)
    raw=json.dumps({'request_sha256':request.request_sha256,'response':asdict(response)}).encode()
    row={'parameters':{'extended_reply_blob_id':'saved','extended_reply_size':len(raw),'extended_reply_sha256':sha256(raw).hexdigest()},
        'request_sha256':request.request_sha256,'response_sha256':response.response_sha256,'model_identity':request.model_id,'provider_mode':'recorded'}
    monkeypatch.setattr(runtime,'extended_unit',lambda *_,**__:row)
    monkeypatch.setattr(runtime,'parse_blob_id',lambda x:x)
    adapter=Adapter()
    result,reused=runtime._call(Session(),run_id='run',authority=NS(),jobs=Jobs(),journal=Journal(),
        binding=NS(adapter=adapter,call=None),request=request,phase='merge',source_sha256='a'*64,
        meter=CostMeter(1.),store=Store({'saved':raw}),publish=None,checkpoint=lambda _:None)
    assert reused and result==response and adapter.requests==[]


def test_norm_candidates_are_source_bound_and_global_lookup_window_is_explicit(monkeypatch):
    calls=[]
    def search(_session,**kwargs):
        calls.append(kwargs)
        return NS(items=(NS(norms_snapshot_id=kwargs['norms_snapshot_id'],norm_document_id='doc',
            norm_paragraph_id=kwargs['q'],designation='СП',clause_number='1.1',fragment=NS(text='Текст корпуса'),page_label=2),))
    monkeypatch.setattr(runtime,'search_norms',search)
    values=[{'norm_queries':['lookup '+str(i)],'norm_status':'unavailable','norm_candidates':[]} for i in range(15)]
    warnings=runtime._norms(Session(),values,'snapshot')
    assert len(calls)==12 and all(c['norms_snapshot_id']=='snapshot' and c['limit']==3 for c in calls)
    assert values[0]['norm_status']=='candidates' and values[0]['norm_candidates'][0]['status']=='candidate_not_verified'
    assert values[-1]['norm_status']=='unavailable' and values[-1]['norm_reason']=='lookup_window_exhausted'
    assert warnings==['norm_lookup_window_exhausted']
