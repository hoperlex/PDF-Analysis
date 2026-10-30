"""Source-bound whole-spec extraction pieces with explicit ownership and genuine context."""
from __future__ import annotations
from copy import deepcopy
from bisect import bisect_left
import hashlib
import json

REVISION='spec-batches-v1'
PROMPT_VERSION='cmp-whole-spec/batched-1'
CHECKED_VERSION=PROMPT_VERSION+'/checked'
RAW_VERSION=PROMPT_VERSION+'/raw'
OWNED_LINES=80
OWNED_CHARACTERS=60_000
CONTEXT_LINES=12
CONTEXT_CHARACTERS=8_000
MAX_BATCHES=512
MAX_REPLY_CHARACTERS=1_000_000


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def plan(source):
    from .source import source_sha256
    flat=[(block,line) for block in source['blocks'] for line in block['lines']]
    by_page={};plain_by_page={}
    for position,(block,line) in enumerate(flat):
        by_page.setdefault(block['page'],[]).append(position)
        if '|' not in line['text']:plain_by_page.setdefault(block['page'],[]).append(position)
    owners=[];current=[];size=0
    for index,(_,line) in enumerate(flat):
        length=len(line['text'])+1
        if length>OWNED_CHARACTERS:raise ValueError('SPEC_SOURCE_LINE_TOO_LARGE')
        if current and (len(current)>=OWNED_LINES or size+length>OWNED_CHARACTERS):
            owners.append(current);current=[];size=0
        current.append(index);size+=length
    if current:owners.append(current)
    if len(owners)>MAX_BATCHES:raise ValueError('SPEC_BATCH_LIMIT')
    output=[]
    for index,owned in enumerate(owners):
        included=set(owned)
        for direction,origin in ((-1,owned[0]-1),(1,owned[-1]+1)):
            characters=0
            for step in range(CONTEXT_LINES):
                position=origin+direction*step
                if not 0<=position<len(flat):break
                length=len(flat[position][1]['text'])+1
                if characters+length>CONTEXT_CHARACTERS:break
                included.add(position);characters+=length
        pages={flat[position][0]['page'] for position in included}
        # Actual table headers and latest real section/parent text remain context,
        # never generated titles or guessed column meanings.
        for page in pages:
            included.update(by_page[page][:2])
            plain=plain_by_page.get(page,[])
            end=bisect_left(plain,owned[0])
            for position in plain[max(0,end-4):end]:
                if len(flat[position][1]['text'])<=2_000:included.add(position)
        selected_blocks={}
        for position in sorted(included):
            parent,line=flat[position]
            selected_blocks.setdefault(parent['block_id'],
                {key:deepcopy(value) for key,value in parent.items() if key!='lines'}|{'lines':[]})['lines'].append(deepcopy(line))
        blocks=list(selected_blocks.values())
        owned_ids=[flat[position][1]['line'] for position in owned]
        context_ids=[flat[position][1]['line'] for position in sorted(included-set(owned))]
        batch_id='sb_'+digest({'revision':REVISION,'source':source['source_sha256'],
            'owned':owned_ids,'context':context_ids})[:32]
        packet={**source,'blocks':blocks,'issues':[],'complete':True,'planning_revision':REVISION,
            'batch_id':batch_id,'selection':{'mode':'owned_lines_with_context','owned_line_ids':owned_ids,
                'context_line_ids':context_ids},'whole_source_sha256':source['source_sha256']}
        packet['source_sha256']=source_sha256(packet)
        from .source import packet_chars
        from . import prompt
        if packet_chars(packet)>140_000 or len(prompt.prompt_for(packet))>140_000:
            raise ValueError('SPEC_BATCH_CONTEXT_TOO_LARGE')
        output.append({'batch_id':batch_id,'index':index,'source':packet,'owned_line_ids':owned_ids,
            'context_line_ids':context_ids,'source_sha256':packet['source_sha256'],
            'pages':sorted(pages)})
    return tuple(output)


def aggregate(source, batches, records):
    from . import check
    full_map={line['line']:(block,line['text']) for block in source['blocks'] for line in block['lines']}
    issues=[]
    data,_,_=check._table_lines(full_map,issues)
    data_lines=set(data)
    all_lines=set(full_map);covered=set();rows_by_owner={};claimed={};batch_rows=[]
    for batch,record in zip(batches,records):
        complete=record.state=='complete'
        if complete:covered.update(batch['owned_line_ids'])
        else:issues.extend(record.coverage.get('issues',[]) or ['Batch extraction incomplete'])
        batch_rows.append({'batch_id':batch['batch_id'],'index':batch['index'],
            'owned_line_ids':batch['owned_line_ids'],'context_line_ids':batch['context_line_ids'],
            'source_sha256':batch['source_sha256'],'state':record.state,'extraction_id':record.extraction_id})
        for row in record.positions:
            refs={ref['line_start'] for ref in row['sources']}
            real=refs & data_lines
            owner=min(real or refs)
            signature={'fields':row['fields'],'section':row.get('section',''),'parent':row.get('parent','')}
            previous=rows_by_owner.get(owner)
            if previous is not None:
                if any(previous[key]!=signature[key] for key in signature):
                    issues.append(f'Conflicting batch position at source line {owner}')
                else:
                    for ref in row['sources']:
                        if ref not in previous['sources']:previous['sources'].append(ref)
            else:
                rows_by_owner[owner]={**deepcopy(signature),'id':'sr_'+digest({'source':source['source_sha256'],'owner':owner})[:32],
                    'sources':deepcopy(row['sources'])}
    for owner,row in rows_by_owner.items():
        for ref in row['sources']:
            number=ref['line_start']
            if number in data:
                if number in claimed and claimed[number]!=owner:
                    issues.append(f'Source data line belongs to multiple positions: {number}')
                claimed[number]=owner
    # Context can ground a row, but only an actually owned, checked source slice
    # counts as extraction coverage. No field-equality de-duplication loses repeats.
    missing_data=set(data)-set(claimed)
    if missing_data:issues.append(f'Unresolved source data lines: {len(missing_data)}')
    if covered!=all_lines:issues.append(f'Uncovered owned source lines: {len(all_lines-covered)}')
    complete=bool(batches) and len(records)==len(batches) and not issues
    coverage={'blocks_total':len(source['blocks']),
        'blocks_covered':sum(all(line['line'] in covered for line in block['lines']) for block in source['blocks']),
        'rows_total':len(data),'rows_unresolved':len(missing_data),
        'planning_revision':REVISION,'comparison_algorithm':'whole-spec-batched-v1-linear-metre1',
        'batches_total':len(batches),'batches_covered':sum(record.state=='complete' for record in records),
        'lines_total':len(all_lines),'lines_covered':len(covered),'batches':batch_rows,
        'issues':list(dict.fromkeys(issues)),'reason':None if complete else check.REASON_ANSWER,
        'candidate_positions':[] if complete else list(rows_by_owner.values())}
    return complete,[rows_by_owner[key] for key in sorted(rows_by_owner)] if complete else [],coverage


def parse_reply(text):
    if not isinstance(text,str) or len(text)>MAX_REPLY_CHARACTERS:return None
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise ValueError('duplicate_reply_key')
            result[key]=value
        return result
    try:
        value=json.loads(text,object_pairs_hook=pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_reply')))
        return value if isinstance(value,dict) else None
    except (ValueError,TypeError,RecursionError):return None
