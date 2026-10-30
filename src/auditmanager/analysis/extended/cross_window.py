"""Pure bounded selection of genuine text-piece pairs from different real windows.

Selection signals nominate a comparison, never establish a discrepancy. Every text
quote is an exact source slice; no recogniser, provider, storage or runtime is used.
"""
from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import re
import unicodedata

VERSION = 'cross-window-comprehensive-v1'
WINDOW_SIZE = 16
MAX_WINDOWS = 63
MAX_SOURCE_RECORDS = 20_000
MAX_ORIGIN_CHARACTERS = 2_000_000
MAX_ORIGIN_HASH_CHARACTERS = 32_000_000
MAX_INDEX_CHARACTERS = 8_000_000
MAX_INDEX_PIECES = 4_096
MAX_INDEX_ATTEMPTS = 24_096
MAX_TERMS_PER_PIECE = 96
MAX_INDEX_TERMS = 16_384
MAX_POSTINGS_PER_TERM = 32
MAX_LINK_EVENTS = 40_000
MAX_CANDIDATES = 2_048
MAX_PENDING_RECORDS = 128
MAX_OMISSION_RECORDS = 128
_MARK = re.compile(r'(?<!\w)[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_.\-/]{1,63}(?!\w)')
_WORD = re.compile(r'[A-Za-zА-Яа-яЁё]{4,64}')
_PARAMETER = re.compile(r'(?<!\w)([+−-]?\d+(?:[.,]\d+)?)\s*(мм|см|м²|м³|м2|м3|кВт|кВА|кВ|Вт|МПа|кПа|Па|кг|шт|л/с|м3/ч|м|т|А|В|°С)(?!\w)', re.IGNORECASE)
_STOP = frozenset(('проект', 'проекта', 'проектной', 'проектная', 'документация', 'документации',
    'раздел', 'листа', 'листы', 'страница', 'страницы', 'пункт', 'данные', 'данных', 'должен', 'должны',
    'должна', 'должно', 'может', 'могут', 'также', 'этого', 'этом', 'который', 'которые', 'согласно',
    'примечание', 'примечания', 'наименование', 'обозначение', 'количество', 'таблица', 'таблицы'))
_SHA = re.compile(r'^[0-9a-fA-F]{64}$')
_SERVICE_MARK = re.compile(r'^(?:v|rev|page|стр|лист|табл|рис|изм|формат)[._-]?\d+$',re.IGNORECASE)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _normal(value):
    return unicodedata.normalize('NFKC', value).casefold().replace('−', '-').replace('–', '-')


def _terms(text):
    marks = {_normal(match.group()) for match in _MARK.finditer(text)
        if any(char.isdigit() for char in match.group()) and not _SERVICE_MARK.fullmatch(match.group())}
    units = {_normal(match.group(2)) for match in _PARAMETER.finditer(text)}
    subjects = {_normal(match.group()) for match in _WORD.finditer(text)} - _STOP
    ordered = [('mark', value) for value in sorted(marks)]
    ordered += [('parameter_unit', value) for value in sorted(units)]
    ordered += [('subject', value) for value in sorted(subjects)]
    return ordered[:MAX_TERMS_PER_PIECE], max(0, len(ordered) - MAX_TERMS_PER_PIECE)


def _missing_ranges(count, present):
    output=[];start=0
    for number in sorted(present):
        if start<number:output.append([start,number])
        start=number+1
    if start<count:output.append([start,count])
    return output


def plan_global_cross_window(*, version_uid, text_layer, recognised, windows, sources,
        source_sha256, max_calls=8, piece_characters=20_000,
        text_layer_sha256=None, recognised_sha256=None):
    """Return at most8 real two-window pairs; omitted counts are not processing claims.

    Native offsets address page.text. Recognised offsets address one actual entry's
    text, preserving its provenance without inventing a joined native-text quote.
    Optional artifact hashes must come from the caller's verified custody references.
    """
    if (not isinstance(version_uid,str) or not version_uid or len(version_uid)>160
            or not isinstance(source_sha256,str) or not _SHA.fullmatch(source_sha256)
            or type(max_calls) is not int or not 0<=max_calls<=8
            or type(piece_characters) is not int or piece_characters!=20_000
            or not isinstance(text_layer,dict) or recognised is not None and not isinstance(recognised,dict)
            or not isinstance(windows,(list,tuple)) or not isinstance(sources,(list,tuple))):
        raise ValueError('cross_window_plan_arguments_invalid')
    for value in (text_layer_sha256,recognised_sha256):
        if value is not None and (not isinstance(value,str) or not _SHA.fullmatch(value)):
            raise ValueError('cross_window_artifact_sha_invalid')
    window_by_index={}
    actual_window_ids=set()
    for ordinal,window in enumerate(windows[:MAX_WINDOWS]):
        if not isinstance(window,dict):raise ValueError('cross_window_window_invalid')
        index=window.get('index',ordinal);identity=window.get('window_id')
        if (type(index) is not int or not 0<=index<MAX_WINDOWS or not isinstance(identity,str)
                or not identity or len(identity)>128 or index in window_by_index or identity in actual_window_ids):
            raise ValueError('cross_window_window_identity_invalid')
        window_by_index[index]=identity;actual_window_ids.add(identity)
    pages=text_layer.get('pages',[])
    entries=[] if recognised is None else recognised.get('entries',[])
    if not isinstance(pages,list) or not isinstance(entries,list):
        raise ValueError('cross_window_source_documents_invalid')
    origins=[];raw_records=len(pages)+len(entries);scanned=0
    non_text_records=0;invalid_records=0;empty_origins=0
    native_pages=set();recognised_pages=set()
    omission_counts=defaultdict(int)
    def add_origin(row,ordinal,kind,artifact_sha):
        nonlocal invalid_records,empty_origins,non_text_records
        if not isinstance(row,dict):invalid_records+=1;return
        if kind=='recognised_text' and row.get('kind')!='recognised_text':non_text_records+=1;return
        number=row.get('page_number');text=row.get('text')
        if type(number) is not int or number<1 or not isinstance(text,str):
            invalid_records+=1;return
        if isinstance(row.get('entry_id'),str) and len(row['entry_id'])>160:
            raise ValueError('cross_window_entry_identity_invalid')
        if kind=='native_text':
            if number in native_pages:raise ValueError('cross_window_duplicate_native_page')
            native_pages.add(number)
        else:recognised_pages.add(number)
        if not text:
            empty_origins+=1;return
        field='text' if kind=='native_text' else 'recognised_context'
        role='prepared.text_layer' if kind=='native_text' else 'prepared.recognised_text'
        window_id=window_by_index.get((number-1)//WINDOW_SIZE)
        locator={'page_number':number,'entry_ordinal':ordinal if kind=='recognised_text' else None,
            'entry_id':row.get('entry_id') if isinstance(row.get('entry_id'),str) else None}
        origin_id='gco_'+_digest({'version_uid':version_uid,'source_sha256':source_sha256,
            'artifact_sha256':artifact_sha,'role':role,'locator':locator})[:32]
        reason=('window_not_in_actual_plan' if window_id is None else
            'single_origin_character_limit' if len(text)>MAX_ORIGIN_CHARACTERS else None)
        origins.append({'origin_id':origin_id,'text':text,'source_type':kind,'character_field':field,
            'page_number':number,'window_id':window_id,'artifact_sha256':artifact_sha,
            'origin_artifact_role':role,'entry_ordinal':locator['entry_ordinal'],'entry_id':locator['entry_id'],
            'pieces_total':(len(text)+piece_characters-1)//piece_characters,
            'indexed':set(),'next_piece':0,'page_text_sha256':None,'reason':reason})
    # Round-robin input record scanning gives both real channels an opportunity
    # before a resource ceiling; it is not a native-prefix-as-complete fallback.
    for ordinal in range(max(len(pages),len(entries))):
        for records,kind,artifact in ((pages,'native_text',text_layer_sha256),
                (entries,'recognised_text',recognised_sha256)):
            if ordinal>=len(records):continue
            if scanned>=MAX_SOURCE_RECORDS:break
            add_origin(records[ordinal],ordinal,kind,artifact);scanned+=1
        if scanned>=MAX_SOURCE_RECORDS:break
    # Local observation/source lists can grow after a replay. They are not an
    # immutable origin for full text and never enter request or manifest identity.
    buckets=defaultdict(deque)
    for index,origin in enumerate(origins):
        if origin['reason'] is None:buckets[(origin['window_id'],origin['source_type'])].append(index)
    keys=sorted(buckets)
    pieces=[];indexed_chars=0;hashed_chars=0;attempts=0;limit_reason=None
    active=deque(keys)
    while active and len(pieces)<MAX_INDEX_PIECES and attempts<MAX_INDEX_ATTEMPTS:
        bucket_key=active.popleft();queue=buckets[bucket_key]
        origin_index=queue.popleft();origin=origins[origin_index];attempts+=1
        if origin['page_text_sha256'] is None:
            if hashed_chars+len(origin['text'])>MAX_ORIGIN_HASH_CHARACTERS:
                origin['reason']='origin_hash_character_limit'
                if queue:active.append(bucket_key)
                continue
            origin['page_text_sha256']=_text_sha(origin['text']);hashed_chars+=len(origin['text'])
        number=origin['next_piece'];start=number*piece_characters
        text=origin['text'][start:start+piece_characters]
        if indexed_chars+len(text)>MAX_INDEX_CHARACTERS:
            limit_reason='index_character_limit';break
        end=start+len(text);sha=_text_sha(text)
        identity='gcw_'+_digest({'origin_id':origin['origin_id'],'character_start':start,
            'character_end':end,'text_sha256':sha})[:32]
        piece={'source_id':identity,'kind':'text','source_type':origin['source_type'],
            'quote_source':'native' if origin['source_type']=='native_text' else 'recognised',
            'version_uid':version_uid,'page_number':origin['page_number'],'window_id':origin['window_id'],
            'window_ids':[origin['window_id']],'character_field':origin['character_field'],
            'character_start':start,'character_end':end,'piece_index':number,'quote':text,
            'character_offset_unit':'unicode_code_points',
            'text_sha256':sha,'page_text_sha256':origin['page_text_sha256'],
            'artifact_sha256':origin['artifact_sha256'],'source_sha256':source_sha256,
            'origin_artifact_role':origin['origin_artifact_role'],'origin_id':origin['origin_id'],
            'artifact_binding':'verified_artifact_sha256' if origin['artifact_sha256'] is not None else 'frozen_source_sha256'}
        if origin['entry_ordinal'] is not None:
            piece['entry_ordinal']=origin['entry_ordinal']
            if origin['entry_id'] is not None:piece['entry_id']=origin['entry_id']
        pieces.append(piece);indexed_chars+=len(text);origin['indexed'].add(number)
        origin['next_piece']+=1
        if origin['next_piece']<origin['pieces_total']:queue.append(origin_index)
        if queue:active.append(bucket_key)
    if active and limit_reason is None:
        limit_reason='index_piece_limit' if len(pieces)>=MAX_INDEX_PIECES else 'index_attempt_limit'
    postings={};term_omissions=0;piece_term_omissions=0
    for index,piece in enumerate(pieces):
        terms,dropped=_terms(piece['quote']);piece_term_omissions+=dropped
        for kind,value in terms:
            key=(kind,value)
            if key not in postings:
                if len(postings)>=MAX_INDEX_TERMS:term_omissions+=1;continue
                postings[key]={'rows':[],'frequency':0}
            entry=postings[key];entry['frequency']+=1
            # Stable min-hash reservoir avoids choosing the first32 occurrences
            # of a common term as though they represented every other window.
            row=(_digest({'term':key,'source_id':piece['source_id']}),index)
            if len(entry['rows'])<MAX_POSTINGS_PER_TERM:entry['rows'].append(row)
            else:
                worst=max(entry['rows'])
                if row<worst:entry['rows'].remove(worst);entry['rows'].append(row)
    candidate_map={};link_events=0;unexpanded_terms=0;candidate_events_omitted=0
    kind_order={'mark':0,'parameter_unit':1,'subject':2}
    ordered_terms=sorted(postings,key=lambda key:(kind_order[key[0]],postings[key]['frequency'],key[1]))
    for term_index,key in enumerate(ordered_terms):
        rows=sorted(index for _,index in postings[key]['rows'])
        stop=False
        for offset,left in enumerate(rows):
            for right in rows[offset+1:]:
                a,b=pieces[left],pieces[right]
                if a['window_id']==b['window_id']:continue
                if link_events>=MAX_LINK_EVENTS:stop=True;break
                link_events+=1;pair=tuple(sorted((left,right)))
                if pair not in candidate_map:
                    if len(candidate_map)>=MAX_CANDIDATES:candidate_events_omitted+=1;continue
                    candidate_map[pair]={'shared_marks':set(),'shared_parameter_units':set(),'shared_subjects':set()}
                field={'mark':'shared_marks','parameter_unit':'shared_parameter_units','subject':'shared_subjects'}[key[0]]
                candidate_map[pair][field].add(key[1])
            if stop:break
        if stop:
            unexpanded_terms=len(ordered_terms)-term_index
            break
    eligible=[]
    for pair,relation in candidate_map.items():
        if not (relation['shared_marks'] or len(relation['shared_subjects'])>=2
                or relation['shared_subjects'] and relation['shared_parameter_units']):continue
        a,b=(pieces[index] for index in pair)
        relation={key:sorted(value) for key,value in relation.items()}
        score=12*len(relation['shared_marks'])+3*len(relation['shared_parameter_units'])+len(relation['shared_subjects'])
        eligible.append({'pair':pair,'relation':relation,'score':score,'distance_pages':abs(a['page_number']-b['page_number'])})
    selected=[];selected_sources=set();selected_windows=set();remaining=list(eligible)
    for _ in range(min(max_calls,len(remaining))):
        def ranking(candidate):
            pair=candidate['pair'];left,right=(pieces[index] for index in pair)
            novelty=len({left['window_id'],right['window_id']}-selected_windows)
            new_pieces=len({left['source_id'],right['source_id']}-selected_sources)
            return (-(candidate['score']+4*novelty+2*new_pieces),-candidate['distance_pages'],
                tuple(sorted((left['source_id'],right['source_id']))))
        best=min(remaining,key=ranking);remaining.remove(best);selected.append(best)
        for index in best['pair']:
            selected_sources.add(pieces[index]['source_id']);selected_windows.add(pieces[index]['window_id'])
    def candidate_metadata(candidate):
        pair=[pieces[index] for index in candidate['pair']]
        return {'source_ids':[row['source_id'] for row in pair],
            'window_ids':[row['window_id'] for row in pair],'page_numbers':[row['page_number'] for row in pair],
            'relation':candidate['relation'],'selection_score':candidate['score'],'distance_pages':candidate['distance_pages']}
    batches=[]
    for index,candidate in enumerate(selected):
        pair=[pieces[number] for number in candidate['pair']]
        metadata=candidate_metadata(candidate)
        sha=_digest({'version':VERSION,'source_sha256':source_sha256,'pieces':pair,'relation':candidate['relation']})
        contexts=[{'source_id':row['source_id'],'page_number':row['page_number'],'window_id':row['window_id'],
            'source_type':row['source_type'],'character_field':row['character_field'],
            'character_start':row['character_start'],'character_end':row['character_end'],
            'character_offset_unit':'unicode_code_points',
            'text':row['quote'] if row['source_type']=='native_text' else '',
            'recognised_context':row['quote'] if row['source_type']=='recognised_text' else '',
            'text_sha256':row['text_sha256']} for row in pair]
        batches.append({**metadata,'index':index,'batch_key':'gcwb_'+sha[:32],
            'batch_sha256':sha,'sources':pair,'native_context':contexts,
            'input_characters':sum(len(row['quote']) for row in pair)})
    omitted=[];omitted_digest=hashlib.sha256();omitted_origins=0
    for origin in origins:
        missing=origin['pieces_total']-len(origin['indexed'])
        if not missing:continue
        reason=origin['reason'] or limit_reason or 'index_resource_limit'
        omission_counts[reason]+=missing;omitted_origins+=1
        row={'origin_id':origin['origin_id'],'page_number':origin['page_number'],
            'version_uid':version_uid,'artifact_sha256':origin['artifact_sha256'],
            'origin_artifact_role':origin['origin_artifact_role'],'source_sha256':source_sha256,
            'window_id':origin['window_id'],'source_type':origin['source_type'],
            'character_field':origin['character_field'],'characters_total':len(origin['text']),
            'pieces_omitted':missing,'piece_index_ranges':_missing_ranges(origin['pieces_total'],origin['indexed']),
            'character_ranges':[[start*piece_characters,min(end*piece_characters,len(origin['text']))]
                for start,end in _missing_ranges(origin['pieces_total'],origin['indexed'])],
            'character_offset_unit':'unicode_code_points',
            'range_convention':'start_inclusive_end_exclusive','reason':reason}
        omitted_digest.update(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
        if len(omitted)<MAX_OMISSION_RECORDS:omitted.append(row)
    window_counts=defaultdict(int)
    for piece in pieces:window_counts[piece['window_id']]+=1
    possible=len(pieces)*(len(pieces)-1)//2-sum(count*(count-1)//2 for count in window_counts.values())
    known_pieces=sum(origin['pieces_total'] for origin in origins)
    public_pieces=[{key:value for key,value in row.items() if key!='quote'} for row in pieces]
    coverage={'source_records_total':raw_records,'source_records_scanned':scanned,
        'source_records_not_scanned':max(0,raw_records-scanned),'invalid_source_records':invalid_records,
        'non_text_records':non_text_records,'empty_text_origins':empty_origins,
        'text_origins_known':len(origins),'pages_known':len(native_pages|recognised_pages),
        'windows_in_plan':len(actual_window_ids),'window_records_omitted':max(0,len(windows)-MAX_WINDOWS),
        'windows_indexed':len(window_counts),'windows_selected':len(selected_windows),
        'characters_total_known':sum(len(origin['text']) for origin in origins),
        'characters_indexed':indexed_chars,'characters_selected':sum(len(row['quote']) for row in pieces if row['source_id'] in selected_sources),
        'pieces_total_known':known_pieces,'pieces_indexed':len(pieces),'pieces_selected':len(selected_sources),
        'pieces_omitted_from_index':known_pieces-len(pieces),'pieces_not_selected':known_pieces-len(selected_sources),
        'pairs_possible_in_index':possible,'candidate_pairs_considered':len(candidate_map),
        'candidate_pairs_eligible':len(eligible),'pairs_selected':len(batches),'pairs_pending':len(remaining),
        'pair_link_events_considered':link_events,'candidate_pair_events_omitted':candidate_events_omitted,
        'index_terms':len(postings),'index_term_events_omitted':term_omissions,'piece_terms_omitted':piece_term_omissions,
        'postings_omitted':sum(max(0,row['frequency']-len(row['rows'])) for row in postings.values()),
        'unexpanded_terms':unexpanded_terms,'omitted_origin_records':omitted_origins,
        'omitted_manifest_truncated':omitted_origins>len(omitted),
        'pending_manifest_truncated':len(remaining)>MAX_PENDING_RECORDS,
        'local_observation_sources_used_for_identity':False,
        'max_calls':max_calls,'piece_characters':piece_characters,'all_pairs_complete':False,
        'complete_input_scan':scanned==raw_records,'omission_reason_counts':dict(omission_counts),
        'complete_document_claim':False}
    coverage['truncated']=bool(invalid_records or coverage['source_records_not_scanned'] or coverage['pieces_omitted_from_index']
        or term_omissions or piece_term_omissions or coverage['postings_omitted'] or unexpanded_terms
        or candidate_events_omitted or remaining or coverage['window_records_omitted'])
    pending=[candidate_metadata(row)|{'reason':'accepted_pair_call_limit'}
        for row in sorted(remaining,key=lambda row:(-row['score'],-row['distance_pages'],row['pair']))[:MAX_PENDING_RECORDS]]
    result={'version':VERSION,'version_uid':version_uid,'source_sha256':source_sha256,
        'range_convention':'start_inclusive_end_exclusive','character_offset_unit':'unicode_code_points',
        'sources':[row for row in pieces if row['source_id'] in selected_sources],
        'pieces':public_pieces,'batches':batches,'pending_batches':pending,'omitted':omitted,
        'omitted_manifest_sha256':omitted_digest.hexdigest(),'coverage':coverage,
        'limits':{'source_records':MAX_SOURCE_RECORDS,'index_pieces':MAX_INDEX_PIECES,
            'index_characters':MAX_INDEX_CHARACTERS,'origin_hash_characters':MAX_ORIGIN_HASH_CHARACTERS,
            'origin_characters':MAX_ORIGIN_CHARACTERS,'terms_per_piece':MAX_TERMS_PER_PIECE,
            'index_terms':MAX_INDEX_TERMS,'postings_per_term':MAX_POSTINGS_PER_TERM,
            'link_events':MAX_LINK_EVENTS,'candidate_pairs':MAX_CANDIDATES,
            'pending_records':MAX_PENDING_RECORDS,'omission_records':MAX_OMISSION_RECORDS},
        'selection_basis':'shared_literal_marks_subjects_parameter_units; bounded_candidate_selection_not_exhaustive'}
    result['manifest_sha256']=_digest({'version':VERSION,'version_uid':version_uid,'source_sha256':source_sha256,
        'pieces':public_pieces,'batch_keys':[row['batch_key'] for row in batches],
        'omitted_manifest_sha256':result['omitted_manifest_sha256'],'coverage':coverage,'limits':result['limits']})
    return result
