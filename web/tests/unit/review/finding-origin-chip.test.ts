/**
 * The «Источник» chip of a finding on «Разбор» (`F8-WEB`, contract 1.51.0 `Finding.origin`).
 *
 * The three words are the server Excel's («Текст», «Чертёж», «Сверка»), and the screen draws the chip for a finding that is not text only:
 * a text finding, and a run that has no other kind, looks exactly as it did.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { FINDING_ORIGIN_VALUES } from '@/shared/api';
import { FINDING_ORIGIN_LABELS, OriginChip, findingOriginOf, groupByCategory, runHasNonTextFindings } from '@/entities/finding';
import { FindingList, FindingTable } from '@/widgets/finding-list';

import { blockFinding, finding, render } from './fixtures';

const noop = (): void => {};
const CROSS = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';
const DRAWING = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';

const mixed = () => [
  finding(),
  blockFinding({ finding_uid: DRAWING }),
  blockFinding({ finding_uid: CROSS, origin: 'cross_check', category: 'cross_source', observation: { ...blockFinding().observation, category: 'cross_source' } }),
];

describe('the words of the chip', () => {
  it('are exactly «Текст», «Чертёж» and «Сверка», one for each origin the contract has', () => {
    expect(FINDING_ORIGIN_LABELS).toEqual({ text: 'Текст', drawing: 'Чертёж', cross_check: 'Сверка' });
    expect(Object.keys(FINDING_ORIGIN_LABELS).sort()).toEqual([...FINDING_ORIGIN_VALUES].sort());
  });

  it('are the words the server Excel\'s «Источник» column carries', () => {
    const labels = readFileSync(fileURLToPath(new URL('../../../../src/auditmanager/exports/xlsx/labels.py', import.meta.url)), 'utf8');
    for (const [origin, words] of Object.entries(FINDING_ORIGIN_LABELS)) {
      expect(labels, `${origin} -> ${words}`).toContain(`"${origin}": "${words}"`);
    }
  });

  it('read an absent origin as text, as the contract says', () => {
    expect(findingOriginOf(finding())).toBe('text');
    expect(findingOriginOf(blockFinding())).toBe('drawing');
    expect(findingOriginOf({ origin: 'cross_check' })).toBe('cross_check');
  });
});

describe('the chip', () => {
  it('draws «Чертёж» and «Сверка», and nothing for a text finding', () => {
    expect(render(createElement(OriginChip, { origin: 'drawing' }))).toContain('>Чертёж<');
    expect(render(createElement(OriginChip, { origin: 'cross_check' }))).toContain('>Сверка<');
    expect(render(createElement(OriginChip, { origin: 'text' }))).toBe('');
  });

  it('keeps the contract value on the element and the words in Russian', () => {
    const markup = render(createElement(OriginChip, { origin: 'cross_check' }));
    expect(markup).toContain('data-finding-origin="cross_check"');
    expect(markup).not.toContain('>cross_check<');
  });
});

describe('the chip in a run\'s list and table', () => {
  const groups = () => groupByCategory(mixed());

  it('stands on the rows of a drawing and a cross-check, and not on the text row', () => {
    const markup = render(createElement(FindingList, { groups: groups(), selectedFindingUid: null, onSelect: noop }));

    expect(markup.match(/data-finding-origin=/g)).toHaveLength(2);
    expect(markup).toContain('data-finding-origin="drawing"');
    expect(markup).toContain('data-finding-origin="cross_check"');
    const textRow = markup.split('<li').find((row) => row.includes('Delivery term stated')) ?? '';
    expect(textRow).not.toContain('data-finding-origin');
  });

  it('stands on the same two rows of the table, in the finding\'s cell', () => {
    const markup = render(createElement(FindingTable, { findings: mixed(), numberOf: new Map(), selectedFindingUid: null, onSelect: noop }));

    expect(markup.match(/data-finding-origin=/g)).toHaveLength(2);
    expect(markup).toContain('Чертёж');
    expect(markup).toContain('Сверка');
  });

  it('is not in a text-only run at all: the list is the markup it always was', () => {
    const list = render(createElement(FindingList, { groups: groupByCategory([finding()]), selectedFindingUid: null, onSelect: noop }));
    const table = render(createElement(FindingTable, { findings: [finding()], numberOf: new Map(), selectedFindingUid: null, onSelect: noop }));

    expect(list).not.toContain('data-finding-origin');
    expect(table).not.toContain('data-finding-origin');
    expect(list).not.toContain('am-badge--inert');
  });
});

describe('a run that is not text only', () => {
  it('is known from its findings: a drawing, a cross-check or a block-grounded one', () => {
    expect(runHasNonTextFindings([finding()])).toBe(false);
    expect(runHasNonTextFindings([finding(), blockFinding()])).toBe(true);
    expect(runHasNonTextFindings([finding({ origin: 'cross_check' })])).toBe(true);
    expect(runHasNonTextFindings([finding({ observation: { ...finding().observation, grounding_kind: 'portal_block' } })])).toBe(true);
    expect(runHasNonTextFindings([finding({ observation: { ...finding().observation, grounding_kind: 'text_span' } })])).toBe(false);
    expect(runHasNonTextFindings([])).toBe(false);
  });
});
