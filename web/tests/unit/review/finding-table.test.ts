/**
 * `UI-A-68`: the findings table of «Разбор» — the original's full-width table, with the norms it cites, the
 * severity the expert decided apart from the one the model proposed, the verdict on the row, and the finding
 * opened under its row.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { NormCitation } from '@/shared/api';
import { groupByCategory } from '@/entities/finding';
import { ExportPanel } from '@/widgets/export-panel';
import { FindingList, FindingToolbar, findingNumbers, findingViewOf, pagesParts } from '@/widgets/finding-list';

import { newClient, renderWith } from '../screens/harness';
import { findingDetail, observation, RUN_ID } from './fixtures';

const A = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA1';
const B = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA2';
const C = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA3';

const CITATION = {
  clause_number: '7.1.4',
  designation: 'СП 54.13330',
  norm_document_id: 'nrm_01J9ZQ8K7NHVXW3T2R5M6P4QA1',
  norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4QA1',
  norms_snapshot_id: 'nsn_01J9ZQ8K7NHVXW3T2R5M6P4QA1',
  page_label: 12,
  quote: 'Высота помещения не менее 2,5 м',
  source_attribution: 'original_text',
  state: 'verified',
  title: 'Здания жилые',
} as unknown as NormCitation;

const FINDINGS = [
  findingDetail({
    finding_uid: A,
    current_verdict: 'accepted',
    decided_severity: 'critical',
    observation: observation({ finding_text: 'Первое замечание', norm_citations: [CITATION] }),
    merged_observations: [observation({}), observation({})],
  }),
  findingDetail({
    finding_uid: B,
    current_verdict: 'rejected',
    observation: observation({ finding_text: 'Второе замечание', proposed_severity: 'economic', norm_citations: [] }),
  }),
  findingDetail({
    finding_uid: C,
    current_verdict: 'pending',
    observation: observation({ finding_text: 'Третье замечание' }),
  }),
];
const GROUPS = groupByCategory(FINDINGS);

function table(props: Record<string, unknown> = {}): string {
  return renderToStaticMarkup(
    createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table', verdictFilter: 'all', ...props }),
  );
}

describe('the findings table', () => {
  it('draws the original’s columns and one row per finding, and no list beside it', () => {
    const markup = table();
    expect(markup).toContain('data-finding-table');
    for (const column of ['№', 'Критичность', 'Лист / стр.', 'Замечание', 'Норма', 'Рекомендация', 'Решение']) {
      expect(markup).toContain(`>${column}</th>`);
    }
    expect((markup.match(/data-row-key=/g) ?? []).length).toBe(3);
    expect(markup).not.toContain('am-finding-group');
  });

  it('lists the norms a finding cites, and says apart a finding whose gate found none and one never gated', () => {
    const markup = table();
    expect(markup).toContain('СП 54.13330');
    expect(markup).toContain('п. 7.1.4');
    expect(markup).toContain('подтверждена');
    expect(markup).toContain('«Высота помещения не менее 2,5 м»');
    expect(markup).toContain('ссылок нет');
  });

  it('keeps the expert’s severity as the badge and the model’s as a labelled note', () => {
    const markup = table();
    expect(markup).toContain('title="Критичность, решённая экспертом"');
    expect(markup).toContain('data-proposed-severity="economic"');
    expect(markup).toContain('предложено: Экономическое');
    // Only the first finding carries a decided severity: the proposal never became a badge.
    expect((markup.match(/title="Критичность, решённая экспертом"/g) ?? []).length).toBe(1);
  });

  it('marks the verdict on the row and a merged finding by its count', () => {
    const markup = table();
    expect(markup).toContain('data-verdict-bucket="accepted"');
    expect(markup).toContain('data-verdict-bucket="rejected"');
    expect(markup).toContain('data-verdict-bucket="waiting"');
    expect(markup).toContain('data-merged-observations="2"');
    expect(markup).toContain('×2');
  });

  it('keeps a finding’s number when a filter hides its neighbours', () => {
    expect([...findingNumbers(GROUPS).entries()]).toEqual([[A, 1], [B, 2], [C, 3]]);
    const markup = table({ verdictFilter: 'waiting' });
    expect(markup).toContain(`data-finding-uid="${C}">3</button>`);
    expect(markup).not.toContain(`data-finding-uid="${A}"`);
  });

  it('opens the finding under the selected row only', () => {
    const open = () => createElement('div', { 'data-opened': '' }, 'ОТКРЫТАЯ НАХОДКА');
    const none = table({ renderExpansion: open });
    expect(none).not.toContain('data-finding-expansion');
    // The table stands in the original's order (`UI-A-71`): C waits, A is accepted, B is rejected. A is the middle row.
    const selected = table({ selectedFindingUid: A, renderExpansion: open });
    expect((selected.match(/data-finding-expansion=/g) ?? []).length).toBe(1);
    expect(selected).toContain(`data-finding-expansion="${A}"`);
    expect(selected).toContain('ОТКРЫТАЯ НАХОДКА');
    // The row says which state it is in; the open row follows its strip, and the rows around it stay where they were.
    expect(selected.indexOf(`data-row-key="${C}"`)).toBeLessThan(selected.indexOf(`data-row-key="${A}"`));
    expect(selected.indexOf(`data-row-key="${A}"`)).toBeLessThan(selected.indexOf('data-finding-expansion'));
    expect(selected.indexOf('data-finding-expansion')).toBeLessThan(selected.indexOf(`data-row-key="${B}"`));
  });

  it('puts the total in front of the verdict counts', () => {
    const markup = table();
    expect(markup).toContain('data-finding-total="3"');
    expect(markup).toContain('Всего: 3');
  });

  it('draws the table by default and for an unknown view, and the list only when it is asked for (`UIP-S06-06`)', () => {
    expect(findingViewOf(null)).toBe('table');
    expect(findingViewOf('')).toBe('table');
    expect(findingViewOf('grid')).toBe('table');
    expect(findingViewOf('table')).toBe('table');
    expect(findingViewOf('list')).toBe('list');
    const byDefault = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {} }));
    expect(byDefault).toContain('data-finding-table');
    expect(byDefault).not.toContain('am-finding-group');
    const list = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'list' }));
    expect(list).not.toContain('data-finding-table');
    expect(list).toContain('data-verdict-bucket="accepted"');
    // The merged count shows on the list row too, beside its pages.
    expect(list).toContain('data-merged-observations="2"');
  });
});

describe('the sheet over the page', () => {
  it('sets the sheet apart when every page names one, and says the pages alone otherwise', () => {
    expect(pagesParts([7], () => 3)).toEqual({ sheet: 'Лист 3', pages: 'стр. 7' });
    expect(pagesParts([7, 8], (page) => page - 4)).toEqual({ sheet: 'Листы 3, 4', pages: 'стр. 7, 8' });
    expect(pagesParts([7, 8], (page) => (page === 7 ? 3 : undefined))).toEqual({ sheet: null, pages: 'стр. 7, 8' });
    expect(pagesParts([7])).toEqual({ sheet: null, pages: 'стр. 7' });
  });
});

describe('the export bar', () => {
  const panel = (layout: 'card' | 'bar') => renderWith(newClient(), createElement(ExportPanel, {
    runId: RUN_ID, runState: 'published', providerMode: 'recorded', onExport: () => {}, mayImportDecisions: true, layout,
  }));

  it('offers the same three file actions as the card, in the same words', () => {
    const card = panel('card');
    const bar = panel('bar');
    for (const markup of [card, bar]) {
      expect(markup).toContain('data-intent="export"');
      expect(markup).toContain('data-intent="export-xlsx"');
      expect(markup).toContain('data-export-format="xlsx"');
      expect(markup).toContain('Колонок:');
    }
    expect(bar).not.toBe(card);
  });
});

describe('the toolbar over the findings', () => {
  const props = (over: Record<string, unknown> = {}) => ({
    groups: GROUPS, verdictFilter: 'all', onVerdictFilterChange: () => {}, severityFilter: 'all', onSeverityFilterChange: () => {},
    view: 'table', onViewChange: () => {}, ...over,
  });
  const toolbar = (groups = GROUPS, over: Record<string, unknown> = {}) =>
    renderToStaticMarkup(createElement(FindingToolbar, props({ groups, ...over }) as never));

  it('is drawn on its own for a page that stands it across the width, and not twice', () => {
    expect(toolbar()).toContain('data-finding-toolbar');
    expect(toolbar()).toContain('Всего: 3');
    const outside = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'list', toolbar: 'outside' }));
    expect(outside).not.toContain('data-finding-toolbar');
    expect(outside).not.toContain('data-severity-strip');
    expect(outside).toContain('am-finding-group');
    const inside = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {} }));
    expect((inside.match(/data-finding-toolbar/g) ?? []).length).toBe(1);
  });

  it('puts the total with the accepted and the rejected in one line: «Всего: N · Принято: n · Отклонено: m»', () => {
    const markup = toolbar();
    expect(markup).toContain('data-finding-total="3"');
    expect(markup.replace(/<[^>]*>/g, '')).toContain('Всего: 3 · Принято: 1 · Отклонено: 1');
    expect(markup).toContain('data-verdict-tally="1/1/1"');
    // «Ждут» is the choice's word and not a tally of the line: the waiting are what is left of the total.
    expect(markup.replace(/<[^>]*>/g, '')).not.toContain('Ожидают решения');
  });

  it('stands the plates and the totals at the left of the first row and the file actions at its right, over the choice «Показывать»', () => {
    const markup = toolbar(GROUPS, { actions: createElement('span', { 'data-file-actions': '' }, 'файлы') });
    const at = (needle: string) => markup.indexOf(needle);
    expect(at('data-severity-strip')).toBeGreaterThan(-1);
    expect(at('data-severity-strip')).toBeLessThan(at('data-finding-total'));
    expect(at('data-finding-total')).toBeLessThan(at('data-file-actions'));
    expect(at('data-file-actions')).toBeLessThan(at('data-verdict-filter'));
    expect(toolbar()).not.toContain('data-file-actions');
  });

  it('is nothing for a run without findings', () => {
    expect(toolbar([])).toBe('');
  });

  it('offers one choice «Показывать: Все / Ждут / Приняты / Отклонены», «Все» pressed by default, and none of the former buttons', () => {
    const markup = toolbar();
    expect(markup).toContain('aria-label="Показывать"');
    const buttons = [...markup.matchAll(/<button[^>]*data-verdict-filter="(\w+)"[^>]*>([^<]*)<\/button>/g)].map((m) => [m[1], m[2]]);
    expect(buttons).toEqual([['all', 'Все'], ['waiting', 'Ждут'], ['accepted', 'Приняты'], ['rejected', 'Отклонены']]);
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-verdict-filter="all"/);
    const pressed = toolbar(GROUPS, { verdictFilter: 'rejected' });
    expect(pressed).toMatch(/aria-pressed="true"[^>]*data-verdict-filter="rejected"/);
    expect(pressed).toMatch(/aria-pressed="false"[^>]*data-verdict-filter="all"/);
    for (const gone of ['Активные', 'Ожидают решения', 'Все, включая историю', 'data-verdict-filter="active"']) {
      expect(markup, gone).not.toContain(gone);
    }
  });

  it('has no switch «Список | Таблица»: one link says what the other way of reading is, and goes to it', () => {
    const table = toolbar();
    expect(table).toContain('data-finding-view-link="list"');
    expect(table).toContain('>Показать списком<');
    expect(table).not.toContain('>Таблица<');
    expect(table).not.toContain('data-finding-view="');
    expect(table).not.toContain('aria-label="Вид списка замечаний"');
    const list = toolbar(GROUPS, { view: 'list' });
    expect(list).toContain('data-finding-view-link="table"');
    expect(list).toContain('>Показать таблицей<');
    expect(list).not.toContain('>Показать списком<');
  });

  it('draws no row of the model’s own: the proposal is a count under the severity plate, and the plate says so in its tooltip', () => {
    const markup = toolbar();
    expect(markup).not.toContain('Предложено моделью (не решение эксперта)');
    expect(markup).toContain('title="решено экспертом: 0 · предложено моделью: 1"');
    expect(markup).toContain('title="решено экспертом: 1 · предложено моделью: 0"');
  });
});
