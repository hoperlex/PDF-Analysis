"""Lossless MD line chunks, adapted from PDF-proverka md_report/plan.py at3c994817.

A transition is the report result; a chunk is only a bounded transmission unit.
Oversized individual lines are refused explicitly, matching the original's rule.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from bisect import bisect_right
from typing import Any, Mapping

REVISION = 'md-chunks-v1'
PROMPT_VERSION = 'cmp-analytic/chunked-1'
TARGET_CHARS = 80_000
HARD_LINE_CHARS = 150_000
MAX_CHUNKS = 256
MAX_PROMPT_CHARS = 300_000
MAX_REPLY_CHARS = 128_000


def transition_chunks(transition: Mapping[str, Any], lines: list[str]) -> tuple[dict, ...]:
    output = []
    first, size = transition['line_start'], 0
    for number in range(transition['line_start'], transition['line_end'] + 1):
        length = len(lines[number - 1]) + 1
        if length > HARD_LINE_CHARS:
            raise ValueError('chunk_source_line_too_large')
        if size and size + length > TARGET_CHARS:
            output.append(_chunk(transition, lines, first, number - 1))
            first, size = number, 0
        size += length
    if size:
        output.append(_chunk(transition, lines, first, transition['line_end']))
    if len(output) > MAX_CHUNKS:
        raise ValueError('chunk_count_limit')
    for index, chunk in enumerate(output):
        chunk.update(index=index, chunk_id=f'{transition["transition_id"]}:C{index:04d}',
            group_id=f'G_{transition["transition_id"]}_{index:04d}',
            block_id=f'B_{transition["transition_id"]}_{index:04d}',
            unit_id=f'U_{transition["transition_id"]}_{index:04d}')
    return tuple(output)


def _chunk(transition, lines, start, end):
    text = '\n'.join(lines[start - 1:end])
    return {'transition_id': transition['transition_id'], 'line_start': start, 'line_end': end,
        'chars': sum(len(lines[number - 1]) + 1 for number in range(start, end + 1)),
        'source_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}


def context(manifest, transition, chunk):
    view = deepcopy(manifest)
    for row in view['transitions']:
        if row['transition_id'] == transition['transition_id']:
            row.update(line_start=chunk['line_start'], line_end=chunk['line_end'], chars=chunk['chars'])
    block = {'block_id': chunk['block_id'], 'transition_id': transition['transition_id'],
        'kind': 'transition_chunk', 'ranges': [[chunk['line_start'], chunk['line_end']]],
        'context': [], 'chars': chunk['chars']}
    group = {'group_id': chunk['group_id'], 'transition_ids': [transition['transition_id']],
        'block_ids': [chunk['block_id']]}
    unit = {'unit_id': chunk['unit_id'], 'transition_ids': [transition['transition_id']],
        'group_ids': [chunk['group_id']]}
    return view, {'blocks': [block], 'groups': [group], 'units': [unit]}, group, unit


def note(chunk, total):
    return ('\n\nПРОГРАММНАЯ ГРАНИЦА ЗАДАНИЯ. Это часть перехода, а не переход целиком. '
        'Проверь все переданные строки; не делай вывод об отсутствии изменений вне этой части. '
        'Оценка относится только к части; общий итог составляется по всем проверенным частям. '
        + json.dumps({'planning_revision': REVISION, 'chunk_id': chunk['chunk_id'],
            'index': chunk['index'], 'chunks_total': total, 'line_start': chunk['line_start'],
            'line_end': chunk['line_end'], 'source_sha256': chunk['source_sha256']}, ensure_ascii=False, sort_keys=True))


def coverage(facts):
    chunks = facts.get('chunks', [])
    analysed = sum(chunk.get('analysis') == 'done' for chunk in chunks)
    verified = sum(chunk.get('verification') == 'done' for chunk in chunks)
    total = sum(chunk['chars'] for chunk in chunks)
    return {'revision': REVISION, 'chunks_total': len(chunks), 'analysed': analysed, 'verified': verified,
        'characters_total': total, 'characters_verified': sum(chunk['chars'] for chunk in chunks
            if chunk.get('verification') == 'done'),
        'complete': bool(chunks) and verified == len(chunks),
        'ranges': [{'chunk_id': chunk['chunk_id'], 'line_start': chunk['line_start'],
            'line_end': chunk['line_end'], 'source_sha256': chunk['source_sha256'],
            'analysis': chunk.get('analysis', 'pending'), 'verification': chunk.get('verification', 'pending')}
            for chunk in chunks]}


def decorate(report, *, doc, units, by_unit, verified, mode):
    """Full saved chunk results accompany the concise narrative; no prefix selection."""
    from . import analytic, facts as facts_module
    rows=[]
    sections=[]
    pattern=analytic._id_pattern(doc.manifest,doc.lines)
    for unit in units:
        part=by_unit.get(unit.transition_id)
        facts={} if part is None else dict(part.facts or {})
        if facts.get('planning_revision')!=REVISION:
            continue
        status=coverage(facts)
        rows.append(dict(status,transition_id=unit.transition_id,label=unit.transition['label']))
        for chunk in facts.get('chunks',[]):
            result=chunk.get('verification_result',{}).get('result')
            if result is None:
                continue
            display=[]
            for claim in result.get('claims',[]):
                display.append({'verdict':claim['verdict'],
                    'text':analytic.plain(analytic.humanize(claim.get('verified_wording',''),doc.manifest,pattern)),
                    'reason':analytic.plain(analytic.humanize(claim.get('brief_reason',''),doc.manifest,pattern)),
                    'evidence':deepcopy(claim.get('evidence',[])),
                    'missing_information':[analytic.plain(analytic.humanize(text,doc.manifest,pattern))
                        for text in claim.get('missing_information',[])]})
            sections.append({'label':unit.transition['label'],'index':chunk['index'],
                'chunks_total':len(facts.get('chunks',[])),'line_start':chunk['line_start'],
                'line_end':chunk['line_end'],'source_sha256':chunk['source_sha256'],
                'claims':display,'verified_result':deepcopy(result),
                'assessment_notes':[analytic.plain(analytic.humanize(str(row.get(field,'')),doc.manifest,pattern))
                    for row in result.get('transitions',[]) for field in
                    ('assessment_basis','main_changes','construction_impact') if row.get(field)],
                'candidate_notes':[analytic.plain(analytic.humanize(' — '.join(str(row.get(field,''))
                    for field in ('title','before_after','consequence')),doc.manifest,pattern))
                    for row in result.get('significant_candidates',[])],
                'questions':[analytic.plain(analytic.humanize(text,doc.manifest,pattern))
                    for text in result.get('unresolved_questions',[])],
                'input_problems':[analytic.plain(analytic.humanize(text,doc.manifest,pattern))
                    for text in chunk.get('analysis_result',{}).get('answer',{}).get('input_problems',[])]})
    report.update(planning_revision=REVISION,composition_mode=mode,chunk_coverage=rows,
        verified_chunk_sections=sections,
        chunk_assembly_complete=all(row['complete'] for row in rows))
    ranges=sorted((ref['md_from'],ref['md_to']) for result in verified.values()
        for row in [*result.get('claims',[]),*result.get('transitions',[]),*result.get('significant_candidates',[])]
        for ref in row.get('evidence',[]))
    merged=[]
    for start,end in ranges:
        if merged and start<=merged[-1][1]+1:merged[-1][1]=max(merged[-1][1],end)
        else:merged.append([start,end])
    starts=[row[0] for row in merged]
    already={fact['fact_id'] for fact in report.get('facts',[])}
    for fact in doc.registry['facts']:
        position=bisect_right(starts,fact['md_line'])-1
        if fact['fact_id'] not in already and position>=0 and fact['md_line']<=merged[position][1]:
            report['facts'].append(facts_module.passport(fact))
            already.add(fact['fact_id'])
    for row in rows:
        report['limitations'].append(f"{row['label']}: проверено частей {row['verified']} из {row['chunks_total']}, "
            f"символов {row['characters_verified']} из {row['characters_total']}. Строки каждой части приведены в приложении.")
    report['limitations'].append('Покрытие частей относится только к переданной MD-сводке. '
        'Оно не подтверждает проверку исходных PDF или экспертную достоверность выводов.')
    return report


def assemble_sections(*, run_id, doc, units, by_unit, verified):
    """Preplanned zero-call assembly of every verified chunk, without a global model prefix."""
    from . import analytic
    parts=analytic.verified_parts(verified)
    transitions=[]
    for transition in doc.manifest['transitions']:
        found=parts.get(transition['transition_id'],[])
        scope=max(found,key=lambda row:analytic.SCOPE_RANK[row['change_scope']])['change_scope'] if found else 'Не установлено'
        significance=max(found,key=lambda row:analytic.SIGNIFICANCE_RANK[row['significance']])['significance'] if found else 'Не установлена'
        transitions.append({'transition_id':transition['transition_id'],'change_scope':scope,
            'significance':significance,'main_changes':f'Проверенных частей: {len(found)}. '
                'Полные проверенные наблюдения и их границы сохранены по частям в приложении.',
            'changes':[],'construction_impact':'Последствия приведены как предварительные выводы модели в приложении; '
                'единая инженерная оценка не выполнялась.','impact_fact_ids':[]})
    answer={'run_id':run_id,'summary':['Все проверенные части сведены программно без дополнительного модельного отбора. '
        'Подробности каждой части, включая отвергнутые и недостаточно подтверждённые наблюдения, приведены в приложении.'],
        'summary_fact_ids':[],'transitions':transitions,'significant_changes':[],
        'limitations':['Единый модельный отбор главных изменений не выполнялся: '
            'до старта выбран полный свод по проверенным частям, а не сокращённый префикс исходных результатов.']}
    report=analytic.assemble(answer,doc.manifest,verified,doc.source,doc.lines,doc.registry)
    return decorate(report,doc=doc,units=units,by_unit=by_unit,verified=verified,mode='deterministic_chunk_sections')


def validate_shape(value, schema, depth=0):
    """Validate the closed provider schema before source/domain checks; no coercion."""
    if depth>30:raise ValueError('reply_nesting_limit')
    kind=schema.get('type')
    if kind=='object':
        if not isinstance(value,dict) or set(schema.get('required',[]))-set(value):
            raise ValueError('reply_object_shape')
        properties=schema.get('properties',{})
        if schema.get('additionalProperties') is False and set(value)-set(properties):
            raise ValueError('reply_unknown_fields')
        for key,item in value.items():
            if key in properties:validate_shape(item,properties[key],depth+1)
    elif kind=='array':
        if not isinstance(value,list):raise ValueError('reply_array_shape')
        for item in value:validate_shape(item,schema['items'],depth+1)
    elif kind=='string' and not isinstance(value,str):raise ValueError('reply_string_shape')
    elif kind=='integer' and type(value) is not int:raise ValueError('reply_integer_shape')
    elif kind=='boolean' and type(value) is not bool:raise ValueError('reply_boolean_shape')
    if 'enum' in schema and value not in schema['enum']:raise ValueError('reply_enum_shape')


def check_analyst(answer, run_id, group, plan, manifest):
    from . import analytic
    checked=analytic.check_analyst(answer,run_id,group,plan,manifest)
    identities=[row['claim_id'] for row in analytic.claims_for_unit({group['group_id']:answer})]
    if len(identities)!=len(set(identities)):
        checked['hard'].append('duplicate analyst claim identities')
    return checked


def check_verifier(answer, run_id, unit, claims, shown):
    from . import analytic
    checked=analytic.check_verifier(answer,run_id,unit,claims,shown)
    identities=[row['claim_id'] for row in answer.get('claims',[])]
    if len(identities)!=len(set(identities)) or set(identities)!={row['claim_id'] for row in claims}:
        checked['hard'].append('verifier must account for each assigned claim exactly once')
    if checked.get('bad_refs'):
        checked['hard'].append('verifier evidence must bind only the actual shown source ranges')
    return checked


def parse_reply(text):
    if not isinstance(text,str) or len(text)>MAX_REPLY_CHARS:
        return None
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate_reply_key')
            result[key]=value
        return result
    try:
        result=json.loads(text,object_pairs_hook=unique,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_reply')))
        return result if isinstance(result,dict) else None
    except (ValueError,TypeError,RecursionError):
        return None
