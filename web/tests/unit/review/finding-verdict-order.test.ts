/**
 * `UI-A-71`: the findings of «Разбор» in the original's order, pending → accepted → rejected, with the run's own order kept
 * inside each of the three; the list keeps its category headings and orders inside them, the table is flat as the
 * original's. A finding's number is the run's, so a decision that moves a row does not renumber it.
 *
 * `UI-A-74`: the table's count of the portal blocks that hold a finding's evidence, drawn only where the server named some.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { Finding, FindingCategory, Verdict } from '@/shared/api';
import { groupByCategory } from '@/entities/finding';
import { declaredPages } from '@/entities/finding-observation';
import { FindingList, findingNumbers, findingsAsShown, inVerdictOrder } from '@/widgets/finding-list';

import { findingDetail, observation } from './fixtures';

const uid = (n: number): string => `fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q${String(n).padStart(2, '0')}`;

function make(n: number, verdict: Verdict, category: FindingCategory = 'internal_contradiction'): Finding {
  return findingDetail({
    finding_uid: uid(n),
    category,
    current_verdict: verdict,
    observation: observation({ category, finding_text: `Замечание ${n}` }),
  });
}

// The run's own order: 1 rejected, 2 pending, 3 accepted, 4 needs_manual_review (waits), 5 rejected, 6 accepted — one category;
// 7 accepted, 8 pending — a second one.
const RUN = [
  make(1, 'rejected'),
  make(2, 'pending'),
  make(3, 'accepted'),
  make(4, 'needs_manual_review'),
  make(5, 'rejected'),
  make(6, 'accepted'),
  make(7, 'accepted', 'dimensions' as FindingCategory),
  make(8, 'pending', 'dimensions' as FindingCategory),
];
const GROUPS = groupByCategory(RUN);
const uids = (findings: readonly Finding[]): number[] => findings.map((f) => Number(f.finding_uid.slice(-2)));

describe('the original’s order', () => {
  it('puts the waiting first, then the accepted, then the rejected, and keeps the run’s order inside each', () => {
    expect(uids(inVerdictOrder(RUN.slice(0, 6)))).toEqual([2, 4, 3, 6, 1, 5]);
  });

  it('does not change a run that is all pending, and does not touch its input', () => {
    const pending = [make(1, 'pending'), make(2, 'pending'), make(3, 'pending')];
    expect(uids(inVerdictOrder(pending))).toEqual([1, 2, 3]);
    const before = uids(RUN);
    inVerdictOrder(RUN);
    expect(uids(RUN)).toEqual(before);
  });

  it('orders inside each category in the list and across the run in the table', () => {
    expect(uids(findingsAsShown(GROUPS, 'list'))).toEqual([2, 4, 3, 6, 1, 5, 8, 7]);
    expect(uids(findingsAsShown(GROUPS, 'table'))).toEqual([2, 4, 8, 3, 6, 7, 1, 5]);
  });
});

describe('the list and the table draw that order', () => {
  const rows = (markup: string, attribute: string): number[] =>
    [...markup.matchAll(new RegExp(`${attribute}="(fnd_[A-Z0-9]+)"`, 'g'))].map((m) => Number((m[1] as string).slice(-2)));

  it('draws the list’s rows in order inside their category, the headings staying where the run puts them', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {} }));
    expect(rows(markup, 'data-finding-uid')).toEqual([2, 4, 3, 6, 1, 5, 8, 7]);
    expect(markup.indexOf('data-category="internal_contradiction"')).toBeLessThan(markup.indexOf('data-category="dimensions"'));
  });

  it('draws the table flat in order, and gives each finding the number the run gave it', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table' }));
    expect(rows(markup, 'data-row-key')).toEqual([2, 4, 8, 3, 6, 7, 1, 5]);
    expect([...findingNumbers(GROUPS).values()]).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
    // Finding 8 stands third and is still «№ 8»: the number belongs to the run, not to the row’s place.
    expect(markup).toContain(`data-finding-uid="${uid(8)}">8</button>`);
  });

  it('orders what is left of a filter in the same way', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, {
      groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table', severityFilter: 'undetermined',
    }));
    expect(rows(markup, 'data-row-key')).toEqual([2, 4, 8, 3, 6, 7, 1, 5]);
    const accepted = renderToStaticMarkup(createElement(FindingList, {
      groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table', verdictFilter: 'accepted',
    }));
    expect(rows(accepted, 'data-row-key')).toEqual([3, 6, 7]);
  });
});

describe('the blocks of a finding in the table', () => {
  const table = (blockCountOf?: (findingUid: string) => number | undefined) =>
    renderToStaticMarkup(createElement(FindingList, {
      groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table', blockCountOf,
    }));

  it('says how many blocks hold the evidence of the findings the server named blocks for', () => {
    const markup = table((findingUid) => (findingUid === uid(3) ? 2 : findingUid === uid(8) ? 1 : undefined));
    expect(markup).toContain('data-finding-block-count="2"');
    expect(markup).toContain('data-finding-block-count="1"');
    expect((markup.match(/data-finding-block-count=/g) ?? []).length).toBe(2);
    expect(markup).toContain('title="Блоков замечания: 2"');
    expect(markup).toContain('2 бл.');
  });

  it('calls the count partial when the finding also cites a page the server could not place evidence on (J3 F7)', () => {
    const cited = RUN.find((finding) => finding.finding_uid === uid(3));
    const page = declaredPages((cited as Finding).observation)[0] as number;
    const markup = renderToStaticMarkup(createElement(FindingList, {
      groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table',
      blockCountOf: (findingUid) => (findingUid === uid(3) ? 2 : undefined), unlinkedPages: new Set([page]),
    }));
    expect(markup).toContain('data-finding-block-partial=""');
    expect(markup).toContain('2+ бл.');
    expect(markup).toContain(`Блоков замечания: не менее 2. Цитата на стр. ${page}`);
    expect((markup.match(/data-finding-block-partial=/g) ?? []).length).toBe(1);
  });

  it('keeps the exact count when no page the finding cites is unlinked', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, {
      groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view: 'table',
      blockCountOf: (findingUid) => (findingUid === uid(3) ? 2 : undefined), unlinkedPages: new Set([999]),
    }));
    expect(markup).not.toContain('data-finding-block-partial');
    expect(markup).toContain('2 бл.');
  });

  it('draws nothing where the links are not produced, and no «0» where a finding has none', () => {
    expect(table()).not.toContain('data-finding-block-count');
    expect(table(() => 0)).not.toContain('data-finding-block-count');
    expect(table(() => undefined)).not.toContain('data-finding-block-count');
  });

  it('draws no count in the list, whose rows are the finding’s text', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, {
      groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, blockCountOf: () => 3,
    }));
    expect(markup).not.toContain('data-finding-block-count');
  });
});
