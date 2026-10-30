"""Targeted real SQL effect/custody/replay proof; no S3 or model connection.
Run with PYTHONPATH=src python this_file <assigned-env-file>. Entire DB transaction rolls back.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from hashlib import sha256
import json
import sys
from sqlalchemy.orm import Session

from auditmanager.analysis.public import (ModelRequest,ModelResponse,ModelCallRecord,ProviderConfig,ProviderMode,
    CostMeter,StageResult,StageStatus,ArtifactRef,publish_artifact,extended_artifact_envelope,extended_digest)
from auditmanager.documents.public import DocumentRepository,ManifestEntry
from auditmanager.jobs.public import JobRepository,extended_unit
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.executor import _DurableCallJournal
from auditmanager.runs.extended_review import _call,read_extended_review
from auditmanager.shared.db.config import DatabaseSettings,parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import RunId
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import BlobMetadataRepository,VerifiedBlob,parse_blob_role,declare_blob


def main():
    raw=next(l.split('=',1)[1].strip().strip('"').strip("'") for l in Path(sys.argv[1]).read_text().splitlines() if l.startswith('DATABASE_URL='))
    engine=create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    connection=engine.connect();outer=connection.begin();session=Session(bind=connection)
    blobs=BlobMetadataRepository();jobs=JobRepository();runs=RunRepository();store_data={}
    class Store:
        def read(self,bid,**_):return store_data[str(bid)]
    store=Store()
    def metadata(data,role):
        declaration=declare_blob(sha256=sha256(data).hexdigest(),size=len(data),role=parse_blob_role(role),media_type='application/json')
        blobs.record_declared(session,declaration)
        return declaration
    try:
        source=metadata(b'synthetic SQL source','source_document')
        blobs.record_verified(session,VerifiedBlob(source.blob_id,'sql-only',source.sha256,source.size,source.role,source.media_type));blobs.mark_available(session,source.blob_id)
        docs=DocumentRepository();project=docs.create_project(session,'Extended SQL recorded')
        document=docs.create_document(session,project_uid=project.project_uid,display_title='Extended SQL',section='AR')
        version=docs.publish_version(session,document_uid=document,media_type='application/pdf',byte_size=source.size,sha256=source.sha256,page_count=1,source_filename=None,
            entries=(ManifestEntry('source.document',source.blob_id,source.sha256,source.size,'application/pdf'),))
        run_id=str(RunId.new())
        runs.create(session,run_id=run_id,project_uid=str(project.project_uid),version_uid=str(version),
            analysis_profile_id='ap_39RX8F43693KEFP4DGHP4965RC',prompt_bundle_id='pb_0HP7C8WD8TJV158AX8GW24M3AX',
            provider_mode='recorded',frozen_input_digest='f'*64,command_id=None)
        runs.advance(session,run_id=run_id,from_state='created',to_state='queued')
        authority=jobs.start_execution(session,run_id=run_id)
        runs.advance(session,run_id=run_id,from_state='queued',to_state='running')
        runs.stage_started(session,run_id=run_id,stage_id='text_analysis')
        session.commit()
        class Adapter:
            provider_mode=ProviderMode.RECORDED
            count=0
            def complete(self,request):
                self.count+=1
                return ModelResponse('{"observations":[]}','end_turn',100,100,1)
        adapter=Adapter();binding=NS(adapter=adapter,config=ProviderConfig(ProviderMode.RECORDED,'claude-opus-5',10.,None,False),call=None)
        def publish(role,body):
            data=json.dumps(extended_artifact_envelope(role,str(version),**body),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            declaration=metadata(data,role.replace('.','_'))
            token=jobs.prepare_artifact(session,authority,stage_id='text_analysis',declaration=declaration)
            blobs.record_verified(session,VerifiedBlob(declaration.blob_id,token,declaration.sha256,declaration.size,declaration.role,declaration.media_type))
            store_data[str(declaration.blob_id)]=data
            ref=ArtifactRef(role,str(declaration.blob_id),declaration.sha256,declaration.size,'application/json')
            for bid in jobs.bind_artifacts(session,authority,stage_id='text_analysis',artifacts=(ref,)):blobs.mark_available(session,bid)
            session.commit();return ref
        request=ModelRequest('claude-opus-5',{'model':'claude-opus-5','max_tokens':6000,'messages':[{'role':'user','content':'Recorded merge'}]})
        args=dict(run_id=run_id,authority=authority,jobs=jobs,journal=_DurableCallJournal(session,jobs,authority),binding=binding,request=request,
            phase='merge',source_sha256='a'*64,meter=CostMeter(10.),store=store,publish=publish,checkpoint=lambda _:None)
        first,reused=_call(session,**args);assert not reused and adapter.count==1
        again,reused=_call(session,**args);assert reused and again==first and adapter.count==1
        changed_request=ModelRequest('claude-opus-5',{'model':'claude-opus-5','max_tokens':6000,'messages':[{'role':'user','content':'Changed merge body'}]})
        try:_call(session,**dict(args,request=changed_request));raise AssertionError('changed phase request resent')
        except DomainError:pass
        bad=dict(args,source_sha256='b'*64)
        try:_call(session,**bad);raise AssertionError('source change resent')
        except DomainError:pass
        phase='blocks:unknown'
        key=extended_digest({'format':'extended-review-v1','source':'a'*64,'phase':phase,'request':request.request_sha256,'model':request.model_id,'connection':None})
        jobs.prepare_provider_call(session,authority,provider='anthropic',model_identity=request.model_id,provider_mode='recorded',
            parameters={**request.parameters,'extended_unit_key':key,'extended_source_sha256':'a'*64,'extended_phase':phase},request_sha256=request.request_sha256)
        session.commit()
        try:_call(session,**dict(args,phase=phase));raise AssertionError('unknown effect resent')
        except DomainError:pass
        assert adapter.count==1
        result={'format':'extended-review-v1','preliminary':True,'observations':[],'coverage':{'blocks_total':0}}
        ref=publish('analysis.extended_review',{'run_id':run_id,'status':'completed','result':result})
        record=StageResult(stage_id='text_analysis',stage_version='1.1.0',status=StageStatus.SUCCEEDED,artifacts=(ref,))
        runs.record_stage_result(session,run_id=run_id,document=record.to_document());session.commit()
        read=read_extended_review(lambda:Session(bind=connection),store,run_id)
        assert read=={'run_id':run_id,'status':'completed','result':result}
        print('SQL PASS: durable effect+reply custody, completed replay without resend, changed-source/request refusal, unknown-effect fence, persisted result read')
    finally:
        session.close();outer.rollback();connection.close();engine.dispose()
if __name__=='__main__':main()
