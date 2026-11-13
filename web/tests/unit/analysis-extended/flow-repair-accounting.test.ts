import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { InputAccounting } from '@/widgets/extended-review/ui/input-accounting';
import { InputPassport } from '@/widgets/extended-review/ui/input-passport';
import { extendedCandidateCounts } from '@/widgets/extended-review/ui/extended-review-summary';
import { reviewCandidates } from '@/widgets/extended-review/model/review-candidates';

import { render } from '../review/fixtures';

describe('execution accounting and evidence limitations remain separate', () => {
  it('does not present 0/0 without an exclusion reason as successful analysis', () => {
    const markup = render(createElement(InputAccounting, { value: { expected: 0, valid: 0, pending: 0, refused: 0, excluded: 0 } }));
    expect(markup).toContain('Основание не передано');
    expect(markup).not.toContain('100%');
  });

  it('shows technical refusals and pending inputs and detects missing accounting', () => {
    expect(render(createElement(InputAccounting, { value: { expected: 5, valid: 2, pending: 1, refused: 1, excluded: 1 } })))
      .toContain('data-input-accounting="balanced"');
    const mismatch = render(createElement(InputAccounting, { value: { expected: 5, valid: 2, pending: 0, refused: 1, excluded: 1 } }));
    expect(mismatch).toContain('Сумма исходов не совпадает');
    expect(render(createElement(InputAccounting, { value: { expected: 5, valid: 2 } }))).toContain('Учет входных записей передан не полностью');
  });

  it('distinguishes empty text and a scan without guessing that a page is blank or a sheet is missing', () => {
    const markup = render(createElement(InputPassport, { value: { page_count: 2, pages: [
      { page_number: 1, text_state: 'empty', text_available: false },
      { page_number: 2, text_state: 'visual_required', text_available: false },
    ], sheet_register: { entries: [{ status: 'unresolved', sheet_label: '30' }] } } }));
    expect(markup).toContain('текстовый слой пуст');
    expect(markup).toContain('нужна визуальная проверка');
    expect(markup).toContain('Соответствие не установлено');
    expect(markup).not.toContain('пустая страница подтверждена');
    expect(markup).not.toContain('— Отсутствует');
  });

  it('counts new semantic groups consistently with the retained-candidate list', () => {
    const observations = [{ observation_id: 't', title: 'Текст', description: 'ВРУ: 294' }, { observation_id: 'g', title: 'Графика', description: 'Схема: 336' }];
    const result = { observations, consolidation: { version: 'v2-flow-repair-v1', complete: true }, consolidated_observations: [
      { group_id: 'group', grouping_status: 'semantic_origin_relationship', origin_records: [{ raw_index: 0 }, { raw_index: 1 }] },
    ] };
    expect(extendedCandidateCounts(result).candidates).toBe(1);
    expect(reviewCandidates(result).rows[0]?.members).toHaveLength(2);
    expect(extendedCandidateCounts({ ...result, consolidated_observations: [] }).candidates).toBe(2);
  });
});
