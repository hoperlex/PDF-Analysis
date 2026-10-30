"""Fresh, consent-bound batches; every deferred input remains in a durable receipt."""
from __future__ import annotations
from copy import deepcopy
from .core import canonical, digest

COVERAGE_VERSION = 'batched-v1'
_PHASE_LIMITS = {'block_analysis': 2, 'comprehensive_analysis': 4,
    'norm_verification': 8, 'finding_review': 8, 'finding_correction': 8}
TEXT_CHARACTERS = 40_000
ITEM_CHARACTERS = 24_000
MAX_BATCH_ITEMS = 20


def cross_window_policy():
    """Separate run-global authority; these calls are never multiplied by windows."""
    return {'version': 'cross-window-comprehensive-v1', 'piece_characters': 20_000,
        'call_limits': {'comprehensive_analysis': 8, 'norm_verification': 8,
            'finding_review': 8, 'finding_correction': 8}}


def validate_cross_window_policy(value):
    if value is None:
        return False
    expected = cross_window_policy()
    if (not isinstance(value, dict) or set(value) != set(expected)
            or value.get('version') != expected['version']
            or type(value.get('piece_characters')) is not int
            or value['piece_characters'] != expected['piece_characters']
            or not isinstance(value.get('call_limits'), dict)
            or set(value['call_limits']) != set(expected['call_limits'])
            or any(type(count) is not int for count in value['call_limits'].values())
            or value['call_limits'] != expected['call_limits']):
        raise ValueError('extended_cross_window_authority_invalid')
    return True


def coverage_policy(*, text_characters=None):
    """Freeze enough comprehensive pieces for a long source, up to a finite cap.

    This is a conservative per-window allowance, not a completeness promise.
    Other phases retain their independent bounded observation budgets.
    """
    limits = dict(_PHASE_LIMITS)
    policy = {'coverage_version': COVERAGE_VERSION, 'phase_call_limits': limits}
    if text_characters is not None:
        if type(text_characters) is not int or text_characters < 0:
            raise ValueError('extended_coverage_source_size_invalid')
        if text_characters > 4 * TEXT_CHARACTERS:
            limits['comprehensive_analysis'] = min(128, (text_characters + TEXT_CHARACTERS - 1) // TEXT_CHARACTERS + 4)
        policy.update(coverage_budget_mode='source-sized-v1', estimated_text_characters=text_characters,
            comprehensive_piece_characters=TEXT_CHARACTERS)
    return policy


def validate_coverage_policy(policy):
    if not isinstance(policy, dict) or 'coverage_version' not in policy:
        return False
    limits = policy.get('phase_call_limits')
    if (policy.get('coverage_version') != COVERAGE_VERSION or not isinstance(limits, dict)
            or set(limits) != set(_PHASE_LIMITS)
            or any(type(value) is not int or not 1 <= value <= 128 for value in limits.values())
            or limits['block_analysis'] != 2):
        raise ValueError('extended_coverage_authority_invalid')
    if 'coverage_budget_mode' in policy or 'estimated_text_characters' in policy:
        characters = policy.get('estimated_text_characters')
        if (policy.get('coverage_budget_mode') != 'source-sized-v1'
                or type(characters) is not int or characters < 0
                or policy.get('comprehensive_piece_characters') != TEXT_CHARACTERS
                or limits != coverage_policy(text_characters=characters)['phase_call_limits']):
            raise ValueError('extended_coverage_source_budget_invalid')
    return True


def _item_id(item, ordinal):
    return 'ci_' + digest({'ordinal': ordinal, 'item': item})[:24]


def _size(item):
    # Quotes and assessments remain whole; splitting observations would lose the
    # critic/parser's exact input partition. Large singletons are explicit pending.
    return len(canonical({key: item[key] for key in ('title', 'description', 'source_ids',
        'norm_assessment', 'norm_candidates') if key in item}))


def _observation_batches(items):
    batches, oversized = [], []
    current, characters = [], 0
    for ordinal, item in enumerate(items):
        identity = _item_id(item, ordinal)
        size = _size(item)
        if size > ITEM_CHARACTERS:
            oversized.append({'input_id': identity, 'ordinal': ordinal,
                'reason': 'single_observation_character_limit', 'input_characters': size})
            continue
        if current and (len(current) >= MAX_BATCH_ITEMS or characters + size > ITEM_CHARACTERS):
            batches.append({'items': current, 'input_characters': characters, 'native_context': []})
            current, characters = [], 0
        current.append({'input_id': identity, 'ordinal': ordinal, 'item': item})
        characters += size
    if current:
        batches.append({'items': current, 'input_characters': characters, 'native_context': []})
    return batches, oversized


def _comprehensive_batches(items, contexts, sources):
    batches = []
    current, characters = [], 0
    # Both real native and recognised text are covered, retaining their distinct
    # anchors, exact character ranges and immutable artifact identity.
    for context in contexts:
        if not isinstance(context, dict) or not isinstance(context.get('text'), str):
            raise ValueError('extended_coverage_context_invalid')
        recognised = context.get('recognised_context', '')
        if not isinstance(recognised, str):
            raise ValueError('extended_coverage_context_invalid')
        for field, value in (('text', context['text']), ('recognised_context', recognised)):
            if not value:
                continue
            for start in range(0, len(value), TEXT_CHARACTERS):
                piece = value[start:start + TEXT_CHARACTERS]
                if current and (characters + len(piece) > TEXT_CHARACTERS or len(current) >= 16):
                    batches.append({'native_context': current, 'items': [], 'input_characters': characters})
                    current, characters = [], 0
                row = {key: deepcopy(value) for key, value in context.items()
                    if key not in {'text', 'recognised_context', 'context_truncated'}}
                row.update(text=piece if field == 'text' else '',
                    recognised_context=piece if field == 'recognised_context' else '',
                    character_start=start, character_end=start + len(piece), character_field=field,
                    context_truncated=False)
                current.append(row)
                characters += len(piece)
    if current:
        batches.append({'native_context': current, 'items': [], 'input_characters': characters})
    page_by_id = {source['source_id']: source.get('page_number') for source in sources}
    for ordinal, wrapped in enumerate(items):
        item = wrapped['item']
        identity = _item_id(wrapped, ordinal)
        pages = {page_by_id.get(key) for key in item['source_ids']}
        candidates = [batch for batch in batches if pages.intersection(
            context.get('page_number') for context in batch['native_context'])]
        target = next((batch for batch in candidates if len(batch['items']) < MAX_BATCH_ITEMS
            and sum(_size(row['item']) for row in batch['items']) + _size(item) <= ITEM_CHARACTERS), None)
        if target is None:
            target = next((batch for batch in batches if not batch['native_context']
                and len(batch['items']) < MAX_BATCH_ITEMS
                and sum(_size(row['item']) for row in batch['items']) + _size(item) <= ITEM_CHARACTERS), None)
        if target is None:
            target = {'native_context': [], 'items': [], 'input_characters': 0}
            batches.append(target)
        target['items'].append({'input_id': identity, 'ordinal': ordinal, 'item': item, 'kind': wrapped['kind']})
    return batches, []


def plan_extended_coverage(*, kind, items, limit, contexts=None, sources=None):
    if kind not in _PHASE_LIMITS or type(limit) is not int or not 1 <= limit <= 128 or not isinstance(items, list):
        raise ValueError('extended_coverage_plan_invalid')
    if kind == 'comprehensive_analysis':
        batches, oversized = _comprehensive_batches(items, contexts or [], sources or [])
    else:
        batches, oversized = _observation_batches(items)
    selected, remainder = batches[:limit], batches[limit:]
    for index, batch in enumerate(batches):
        references = {key for row in batch['items'] for key in row['item']['source_ids']}
        references.update(row['source_id'] for row in batch['native_context'])
        batch.update(index=index, input_ids=[row['input_id'] for row in batch['items']],
            source_ids=sorted(references), page_numbers=sorted({row['page_number']
                for row in batch['native_context']}), batch_sha256=digest({'kind': kind,
                    'items': batch['items'], 'native_context': batch['native_context']}))
    return {'coverage_version': COVERAGE_VERSION, 'batches': selected,
        'pending_batches': remainder, 'oversized': oversized, 'limit': limit,
        'total_items': len(items), 'planned': len(batches),
        'total_characters': sum(batch['input_characters'] for batch in batches) +
            sum(row['input_characters'] for row in oversized),
        'pending_items': sum(len(batch['items']) for batch in remainder) + len(oversized),
        'pending_characters': sum(batch['input_characters'] for batch in remainder) +
            sum(row['input_characters'] for row in oversized)}
