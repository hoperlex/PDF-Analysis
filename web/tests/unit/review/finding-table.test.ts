/**
 * `UI-A-68`, `UIP-S06-07`: the findings table of «Разбор» — the original's full-width table, with the norms it cites, the
 * severity the expert decided apart from the one the model proposed, the verdict on the row, and the finding
 * opened under its row. A row wears a stripe at its left in the tone of its severity (solid when decided, dashed when it is the
 * model's proposal), accepted rows stand on green, rejected rows are struck through and stand last. The look is held twice: the
 * markup says which stripe, tint and strike a row asks for, and the module's own rules are read to hold that they exist, each
 * checked first on a sheet that lacks the rule so the check can fail.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { DecisionCarriedFrom, NormCitation, Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import { groupByCategory, severityTone } from '@/entities/finding';
import { ExportPanel } from '@/widgets/export-panel';
import { FindingList, FindingRowActions, FindingToolbar, findingNumbers, findingViewOf, pagesParts } from '@/widgets/finding-list';

import { WEB_ROOT } from '../../guards/lib/repo';
import { declares } from '../styles/css-reads';
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

  it('keeps the expert’s severity as the pill and the model’s as the dashed pill with the word «предложено»', () => {
    const markup = table();
    expect(markup).toContain('title="Критичность, решённая экспертом"');
    expect(markup).toContain('data-severity="critical"');
    // The proposal is the same pill in its own variant: its own attribute, the dashed class, the word and the tooltip.
    expect(markup).toMatch(/<span class="am-badge am-badge--degraded [^"]*proposed[^"]*" data-proposed-severity="economic" title="Предложение модели, не решение эксперта">/);
    expect(markup).toContain('>Экономическое<');
    expect(markup).toContain('>предложено<');
    // Only the first finding carries a decided severity: the proposal never became a decision's pill.
    expect((markup.match(/title="Критичность, решённая экспертом"/g) ?? []).length).toBe(1);
    expect((markup.match(/data-severity="/g) ?? []).length).toBe(1);
    expect(markup).not.toContain('data-severity="economic"');
    // The old note is gone, and a finding with no severity says a dash, not a pill.
    expect(markup).not.toContain('предложено: ');
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

const TABLE_CSS = readFileSync(join(WEB_ROOT, 'src/widgets/finding-list/ui/finding-table.module.css'), 'utf8');

/** The opening tag of a finding's row. */
function rowTag(markup: string, uid: string): string {
  const found = new RegExp(`<tr[^>]*data-row-key="${uid}"[^>]*>`).exec(markup);
  if (found === null) throw new Error(`no row ${uid} in ${markup}`);
  return found[0];
}

describe('the stripe at the left of a row', () => {
  it('names the tone of the finding’s severity and whose it is: solid for the expert’s decision, dashed for the model’s proposal', () => {
    const markup = table();
    expect(rowTag(markup, A)).toContain('data-severity-tone="failed"');
    expect(rowTag(markup, A)).toContain('data-severity-source="decided"');
    expect(rowTag(markup, B)).toContain('data-severity-tone="degraded"');
    expect(rowTag(markup, B)).toContain('data-severity-source="proposed"');
  });

  it('has none for a finding with no severity at all, and draws a dash in its cell', () => {
    const markup = table();
    expect(rowTag(markup, C)).not.toContain('data-severity-tone');
    expect(rowTag(markup, C)).not.toContain('data-severity-source');
    expect(markup).toMatch(new RegExp(`data-row-key="${C}"[\\s\\S]*?<td class="[^"]*severity[^"]*"><span class="[^"]*none[^"]*">—</span></td>`));
  });

  it('takes the decision over a proposal for the same finding, and its tone from the severity and from nothing else', () => {
    const overruled = groupByCategory([
      findingDetail({ finding_uid: A, decided_severity: 'economic', observation: observation({ proposed_severity: 'critical' }) }),
    ]);
    const markup = renderToStaticMarkup(createElement(FindingList, { groups: overruled, selectedFindingUid: null, onSelect: () => {}, view: 'table' }));
    expect(rowTag(markup, A)).toContain('data-severity-tone="degraded"');
    expect(rowTag(markup, A)).toContain('data-severity-source="decided"');
  });

  it('gives each of the five severities its own tone, decided and proposed alike', () => {
    const tones = (source: 'decided' | 'proposed') => {
      const findings = SEVERITY_VALUES.map((severity: Severity, index: number) => findingDetail({
        finding_uid: `fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q${source === 'decided' ? 'D' : 'P'}${index}`,
        ...(source === 'decided' ? { decided_severity: severity } : {}),
        observation: observation({ ...(source === 'proposed' ? { proposed_severity: severity } : {}) }),
      }));
      const markup = renderToStaticMarkup(createElement(FindingList, {
        groups: groupByCategory(findings), selectedFindingUid: null, onSelect: () => {}, view: 'table',
      }));
      return findings.map((one) => /data-severity-tone="(\w+)"/.exec(rowTag(markup, one.finding_uid))?.[1]);
    };
    const expected = SEVERITY_VALUES.map((severity: Severity) => severityTone(severity));
    expect(new Set(expected).size).toBe(5);
    expect(tones('decided')).toEqual(expected);
    expect(tones('proposed')).toEqual(expected);
  });

  it('is drawn by the module: a left border on the first cell, in each tone’s colour, dashed for a proposal', () => {
    // The check can fail: a sheet without the rule does not declare it.
    expect(declares('.row { height: 1px; }', '.row > td:first-child', 'border-left', /solid/)).toBe(false);
    const colours: Readonly<Record<string, string>> = {
      failed: '--am-failed', degraded: '--am-degraded', active: '--am-accent', ok: '--am-ok', inert: '--am-inert',
    };
    expect(declares(TABLE_CSS, '.row > td:first-child', 'border-left', /^4px solid transparent$/)).toBe(true);
    expect(declares(TABLE_CSS, ".row[data-severity-source='proposed'] > td:first-child", 'border-left-style', /^dashed$/)).toBe(true);
    for (const tone of ['failed', 'degraded', 'active', 'ok', 'inert'] as const) {
      expect(declares(TABLE_CSS, `.row[data-severity-tone='${tone}'] > td:first-child`, 'border-left-color', new RegExp(`^var\\(${colours[tone]}\\)$`)), tone).toBe(true);
    }
  });
});

describe('the verdict on a row', () => {
  it('stands the waiting first, then the accepted, then the rejected last: C, A, B', () => {
    const markup = table();
    const at = (uid: string) => markup.indexOf(`data-row-key="${uid}"`);
    expect(at(C)).toBeLessThan(at(A));
    expect(at(A)).toBeLessThan(at(B));
  });

  it('says the verdict by its sign in the decision cell, the word being the sign’s name, and the cell is not struck through', () => {
    const markup = table();
    const cell = (uid: string): string => {
      const found = new RegExp(`data-row-key="${uid}"[\\s\\S]*?(<td class="[^"]*decisionCell[^"]*">[\\s\\S]*?</td>)`).exec(markup);
      if (found === null) throw new Error(`no decision cell of ${uid}`);
      return found[1] as string;
    };
    // One glyph (UIP-FIX-17: the cell is one line, and a word did not fit it beside the choice, ✓, ✕ and «Причина»); the word is its name.
    expect(cell(B)).toContain('>✕<');
    expect(cell(B)).toContain('aria-label="Отклонено"');
    expect(cell(A)).toContain('>✓<');
    expect(cell(A)).toContain('aria-label="Принято"');
    expect(cell(C)).toContain('>—<');
    expect(cell(C)).toContain('aria-label="Не решено"');
    expect(cell(C)).not.toContain('Отклонено');
    expect(declares(TABLE_CSS, ".row[data-verdict-bucket='rejected'] > td.decisionCell", 'text-decoration', /^none$/)).toBe(true);
  });

  it('is drawn by the module: accepted rows on green, rejected rows struck through, the decision cell left alone', () => {
    expect(declares(".row { }", ".row[data-verdict-bucket='rejected'] > td", 'text-decoration', /line-through/)).toBe(false);
    expect(declares(TABLE_CSS, ".row[data-verdict-bucket='accepted'] > td", 'background', /^var\(--am-ok-light\)$/)).toBe(true);
    expect(declares(TABLE_CSS, ".row[data-verdict-bucket='rejected'] > td", 'text-decoration', /^line-through$/)).toBe(true);
    // A waiting row keeps the page's paper: no rule tints it and no rule strikes it.
    expect(declares(TABLE_CSS, ".row[data-verdict-bucket='waiting'] > td", 'background', /./)).toBe(false);
    expect(declares(TABLE_CSS, ".row[data-verdict-bucket='waiting'] > td", 'text-decoration', /./)).toBe(false);
    expect(declares(TABLE_CSS, ".row[data-verdict-bucket='accepted'] > td", 'text-decoration', /./)).toBe(false);
  });

  it('leaves the opened finding under a rejected row unstruck: its strip is not one of the row’s cells', () => {
    const markup = table({ selectedFindingUid: B, renderExpansion: () => createElement('p', null, 'ОТКРЫТАЯ НАХОДКА') });
    expect(markup).toContain(`data-finding-expansion="${B}"`);
    expect(rowTag(markup, B)).toContain('data-verdict-bucket="rejected"');
    expect(/data-finding-expansion="[^"]*"/.exec(markup)?.[0]).toBeDefined();
    expect(/<tr class="[^"]*expansion[^"]*"[^>]*data-verdict-bucket/.test(markup)).toBe(false);
  });
});

describe('the size of a row and its words', () => {
  it('is one step high, by the common token, and a one-line cell stands in the middle', () => {
    expect(declares('.table { }', '.row', 'height', /var\(--am-row-step\)/)).toBe(false);
    expect(declares(TABLE_CSS, '.row', 'height', /^var\(--am-row-step\)$/)).toBe(true);
    expect(declares(TABLE_CSS, '.row > td', 'vertical-align', /^middle$/)).toBe(true);
  });

  it('cuts no word in a narrow column: cells and heads break only a word that cannot fit its own line', () => {
    for (const selector of ['.row > td', '.head']) {
      expect(declares(TABLE_CSS, selector, 'overflow-wrap', /^break-word$/), selector).toBe(true);
      expect(declares(TABLE_CSS, selector, 'word-break', /^normal$/), selector).toBe(true);
      expect(declares(TABLE_CSS, selector, 'overflow-wrap', /anywhere/), selector).toBe(false);
    }
    // The head may wrap between its words, so it is not held on one line.
    expect(declares(TABLE_CSS, '.head', 'white-space', /nowrap/)).toBe(false);
  });

  it('keeps the original’s seven columns in the original’s order, the severity column wide enough for its longest word', () => {
    const markup = table();
    const heads = [...markup.matchAll(/<th[^>]*>([^<]*)<\/th>/g)].map((m) => m[1]);
    expect(heads).toEqual(['№', 'Критичность', 'Лист / стр.', 'Замечание', 'Норма', 'Рекомендация', 'Решение']);
    const widths = ['colNumber', 'colSeverity', 'colPages', 'colText', 'colNorms', 'colRecommendation', 'colDecision'].map((name) => {
      const found = new RegExp(`\\.${name}\\s*\\{[^}]*width:\\s*(\\d+)%`).exec(TABLE_CSS);
      return Number(found?.[1]);
    });
    expect(widths.reduce((sum, width) => sum + width, 0)).toBe(100);
    expect(widths[1]).toBeGreaterThanOrEqual(14);
    // The finding is the widest column; the decision column is the second, for the whole line of its cell (`UIP-FIX-17`).
    const text = widths[3] as number;
    const decision = widths[6] as number;
    expect(text).toBe(Math.max(...widths));
    expect(decision).toBe([...widths].sort((left, right) => right - left)[1]);
    expect(decision).toBeGreaterThanOrEqual(24);
  });
});

/**
 * `UIP-FIX-17`: the «Решение» cell is one line. Its markup is the sign, then the row's field (`FindingRowActions`), then the mark of a
 * carried decision under them; its rules place the field from the cell, by the handles the markup carries, and each is checked first on a
 * sheet that lacks it (so the check can fail) and then on the module.
 */
describe('the decision cell is one line', () => {
  const CARRIED: DecisionCarriedFrom = {
    decision_id: 'dec_01J9ZQ8K7NHVXW3T2R5M6P4Q9A',
    finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q9B',
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q9C',
    version_ordinal: 2,
  };
  const withField = (props: Record<string, unknown> = {}): string =>
    table({
      renderRowActions: () =>
        createElement(FindingRowActions, {
          verdict: 'pending',
          sending: null,
          note: null,
          onAccept: () => {},
          onReject: () => {},
          severity: { value: '', onChange: () => {}, required: true, invalid: false },
        }),
      ...props,
    });
  const cellOf = (markup: string, uid: string): string => {
    const found = new RegExp(`data-row-key="${uid}"[\\s\\S]*?(<td class="[^"]*decisionCell[^"]*">[\\s\\S]*?</td></tr>)`).exec(markup);
    if (found === null) throw new Error(`no decision cell of ${uid}`);
    return found[1] as string;
  };

  it('stands the sign, the choice of severity, ✓, ✕ and «Причина» in that order in one box, and no word of the verdict', () => {
    const cell = cellOf(withField(), C);
    const at = (needle: string): number => cell.indexOf(needle);
    expect(at('data-verdict="pending"')).toBeGreaterThan(-1);
    expect(at('data-verdict="pending"')).toBeLessThan(at('data-row-severity'));
    expect(at('data-row-severity')).toBeLessThan(at('data-intent="accept"'));
    expect(at('data-intent="accept"')).toBeLessThan(at('data-intent="reject"'));
    expect(at('data-intent="reject"')).toBeLessThan(at('data-decision-reason'));
    expect(cell).not.toContain('am-badge');
  });

  it('puts the mark of a carried decision after the field, so it can stand under the line instead of inside it', () => {
    const carried = findingDetail({
      finding_uid: A,
      current_verdict: 'accepted',
      current_verdict_carried_from: CARRIED,
      observation: observation({ finding_text: 'Перенесённое замечание' }),
    });
    const cell = cellOf(withField({ groups: groupByCategory([carried]) }), A);
    expect(cell.indexOf('data-row-actions')).toBeGreaterThan(-1);
    expect(cell.indexOf('data-row-actions')).toBeLessThan(cell.indexOf('data-carried-from'));
  });

  it('is drawn by the module: a row of one line that never wraps its field under the buttons, narrower in a narrow column', () => {
    const rules: readonly (readonly [string, string, RegExp])[] = [
      ['.decision', 'display', /^flex$/],
      ['.decision', 'flex-wrap', /^wrap$/],
      ['.decision', 'align-items', /^flex-start$/],
      ['.decision > [data-verdict]', 'min-height', /^28px$/],
      ['.decision [data-row-actions]', 'flex-wrap', /^nowrap$/],
      ['.decision [data-row-actions]', 'max-width', /^none$/],
      ['.decision [data-row-actions]', 'min-width', /^\d+(\.\d+)?rem$/],
      ['.decision select[data-row-severity]', 'min-width', /^\d+(\.\d+)?rem$/],
      ['.decision [data-decision-control]', 'min-width', /^\d+(\.\d+)?rem$/],
      // The field takes the rest and gives first: no basis of its own (the base rule's 9rem is what put it under the buttons).
      ['.decision [data-decision-control] input[data-decision-reason]', 'flex', /^1 1 0$/],
      ['.decision [data-decision-control] input[data-decision-reason]', 'min-width', /^\d+(\.\d+)?rem$/],
      // The line of the last press is the one thing that goes under; so is the carried mark.
      ['.decision [data-decision-control] [data-decision-note]', 'flex', /^1 0 100%$/],
      ['.decision > [data-carried-from]', 'flex', /^1 0 100%$/],
    ];
    for (const [selector, property, value] of rules) {
      expect(declares('.decision { }', selector, property, value), `${selector} ${property} on a sheet without it`).toBe(false);
      expect(declares(TABLE_CSS, selector, property, value), `${selector} ${property}`).toBe(true);
    }
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
