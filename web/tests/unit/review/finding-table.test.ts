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
    for (const column of ['№', 'Важность', 'Лист / стр.', 'Замечание', 'Норма', 'Рекомендация', 'Решение']) {
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
    expect(markup).toContain('title="Важность, решённая экспертом"');
    expect(markup).toContain('data-proposed-severity="economic"');
    expect(markup).toContain('предложено: Экономическое');
    // Only the first finding carries a decided severity: the proposal never became a badge.
    expect((markup.match(/title="Важность, решённая экспертом"/g) ?? []).length).toBe(1);
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

  it('draws the list, not the table, by default and for an unknown view', () => {
    expect(findingViewOf(null)).toBe('list');
    expect(findingViewOf('grid')).toBe('list');
    expect(findingViewOf('table')).toBe('table');
    const list = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {} }));
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
  const toolbar = (groups = GROUPS) => renderToStaticMarkup(createElement(FindingToolbar, {
    groups, verdictFilter: 'all', onVerdictFilterChange: () => {}, severityFilter: 'all', onSeverityFilterChange: () => {},
    view: 'list', onViewChange: () => {},
  }));

  it('is drawn on its own for a page that stands it across the width, and not twice', () => {
    expect(toolbar()).toContain('data-finding-toolbar');
    expect(toolbar()).toContain('Всего: 3');
    const outside = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, toolbar: 'outside' }));
    expect(outside).not.toContain('data-finding-toolbar');
    expect(outside).not.toContain('data-severity-strip');
    expect(outside).toContain('am-finding-group');
    const inside = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {} }));
    expect((inside.match(/data-finding-toolbar/g) ?? []).length).toBe(1);
  });

  it('stands the total and the severity chips at the left of the first row and the file actions at its right, over the verdict row', () => {
    const markup = renderToStaticMarkup(createElement(FindingToolbar, {
      groups: GROUPS, verdictFilter: 'all', onVerdictFilterChange: () => {}, severityFilter: 'all', onSeverityFilterChange: () => {},
      view: 'list', onViewChange: () => {}, actions: createElement('span', { 'data-file-actions': '' }, 'файлы'),
    }));
    const at = (needle: string) => markup.indexOf(needle);
    expect(at('data-finding-total')).toBeGreaterThan(-1);
    expect(at('data-finding-total')).toBeLessThan(at('data-severity-strip'));
    expect(at('data-severity-strip')).toBeLessThan(at('data-file-actions'));
    expect(at('data-file-actions')).toBeLessThan(at('data-verdict-tally'));
    expect(toolbar()).not.toContain('data-file-actions');
  });

  it('is nothing for a run without findings', () => {
    expect(toolbar([])).toBe('');
  });

  it('offers the five explicitly labelled proposal filters, and hides them when nothing was proposed', () => {
    const markup = toolbar();
    expect(markup).toContain('Предложено моделью (не решение эксперта):');
    expect(markup).toContain('data-severity-filter="proposed:economic"');
    expect(markup).toContain('Экономическое 1');
    const decidedOnly = groupByCategory([
      findingDetail({ finding_uid: A, decided_severity: 'critical', observation: observation({}) }),
    ]);
    const bare = toolbar(decidedOnly);
    expect(bare).toContain('data-severity-strip');
    expect(bare).not.toContain('data-proposed-severity');
  });
});
