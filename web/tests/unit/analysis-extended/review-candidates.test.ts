import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ReviewCandidateTable } from '@/widgets/extended-review';
import { reviewCandidates } from '@/widgets/extended-review/model/review-candidates';
import { ReviewWarnings } from '@/widgets/extended-review/ui/review-warnings';
import { finding, observation } from '../review/fixtures';

const candidate = (observation_id: string, source_ids = ['drawing']) => ({
  observation_id, title: 'Несовпадение размеров', description: 'На плане 3000 мм, в спецификации 2800 мм.', source_ids,
});
const value = {
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  sources: [{ source_id: 'drawing', kind: 'image', page_number: 2 }, { source_id: 'text', kind: 'text', page_number: 3 }],
  observations: [candidate('a'), candidate('b', ['text']), candidate('c')],
  consolidation: { complete: true, version: 'ensemble-linked-v1' },
  consolidated_observations: [
    { group_id: 'g1', ...candidate('a'), origin_records: [{ raw_index: 0 }, { raw_index: 1 }] },
    { group_id: 'g2', ...candidate('c'), origin_records: [{ raw_index: 2 }] },
  ],
};

describe('retained candidates in the same review journey', () => {
  it('shows linked groups with every original source, without mutating observations', () => {
    const before = JSON.stringify(value);
    const reading = reviewCandidates(value);
    expect(reading.rawCount).toBe(3);
    expect(reading.rows).toHaveLength(2);
    expect(reading.rows[0]?.members).toHaveLength(2);
    expect(reading.rows[0]?.pages).toEqual([2, 3]);
    expect(reading.rows[0]?.origin).toBe('cross_check');
    expect(reading.rows[0]?.severity).toBeUndefined();
    expect(reading.rows[0]?.recommendations).toEqual([]);
    expect(JSON.stringify(value)).toBe(before);
  });

  it('removes only exactly referenced published observations, including merged ones', () => {
    const published = finding({ observation: observation({ extended_observation_ref: 'a' }),
      merged_observations: [observation({ extended_observation_ref: 'b' })] });
    const reading = reviewCandidates(value, [published]);
    expect(reading.rows.map((row) => row.members.map((item) => item.observation_id))).toEqual([['c']]);
    expect(reading.publishedGroups).toBe(1);
    expect(reviewCandidates(value, [finding()]).rows).toHaveLength(2);
    const partial = { ...value, observations: [value.observations[0], { ...value.observations[1], description: 'Оставшаяся формулировка.' }, value.observations[2]] };
    const canonicalOnly = finding({ observation: observation({ extended_observation_ref: 'a' }) });
    expect(reviewCandidates(partial, [canonicalOnly]).rows[0]?.description).toBe('Оставшаяся формулировка.');
  });

  it('keeps all raw records and announces an incomplete grouping instead of losing candidates', () => {
    const reading = reviewCandidates({ ...value, consolidated_observations: [value.consolidated_observations[0]] });
    expect(reading.rows).toHaveLength(3);
    expect(reading.groupingIncomplete).toBe(true);
  });

  it('shows saved proposals only; disagreeing proposals in one group do not invent a common severity', () => {
    const observations = [
      { ...value.observations[0], proposed_severity: 'critical', recommendation_text: 'Сверить размеры.' },
      { ...value.observations[1], proposed_severity: 'economic', recommendation_text: 'Согласовать спецификацию.' },
      value.observations[2],
    ];
    const row = reviewCandidates({ ...value, observations }).rows[0];
    expect(row?.severity).toBeUndefined();
    expect(row?.recommendations).toEqual(['Сверить размеры.', 'Согласовать спецификацию.']);
  });

  it('has a dense read-only table and marks absent old proposals explicitly', () => {
    const markup = renderToStaticMarkup(createElement(ReviewCandidateTable, { value, projectUid: 'p' }));
    for (const label of ['Важность', 'Лист / стр.', 'Замечание', 'Норма', 'Рекомендация', 'Решение', 'Только просмотр', 'В этом прогоне отдельно не сохранена']) {
      expect(markup).toContain(label);
    }
    expect(markup).not.toContain('data-finding-row-actions');
    expect(markup).not.toContain('Принять замечание');
    expect(markup).toContain('Основание не подтверждено');
  });

  it('pages a long historical result instead of mounting every source viewer', () => {
    const observations = Array.from({ length: 139 }, (_, index) => candidate(String(index)));
    const markup = renderToStaticMarkup(createElement(ReviewCandidateTable, { value: { ...value, observations, consolidation: null }, projectUid: 'p' }));
    expect(markup.match(/data-candidate-row=/g)).toHaveLength(25);
    expect(markup).toContain('из 139');
    expect(markup).toContain('Следующие');
  });
});

describe('saved analysis warnings', () => {
  it('translates repeated known codes once and preserves their multiplicity', () => {
    const markup = renderToStaticMarkup(createElement(ReviewWarnings, { warnings: Array(11).fill('related_context_incomplete') }));
    expect(markup.match(/<li /g)).toHaveLength(1);
    expect(markup).toContain('Не весь найденный связанный контекст вошёл в запрос');
    expect(markup).toContain('Повторений в записи: 11');
    expect(markup).toContain('Код: related_context_incomplete');
  });

  it('retains an unknown code so different limitations remain distinguishable', () => {
    const markup = renderToStaticMarkup(createElement(ReviewWarnings, { warnings: ['future_limitation', 'other_limitation'] }));
    expect(markup.match(/<li /g)).toHaveLength(2);
    expect(markup).toContain('Код: future_limitation');
    expect(markup).toContain('Код: other_limitation');
  });
});
