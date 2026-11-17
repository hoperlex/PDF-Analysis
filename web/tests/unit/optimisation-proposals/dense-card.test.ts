/**
 * `UI-PARITY-DENSE`, `UI-B-06`: a proposal is a row of the original's table, not a card of ten stacked lines.
 *
 * The three columns are CSS grid areas over the card's own children: the source and the figures at the left, the
 * specification row with the two positions in the middle, the verdict with its form and history at the right. What this file
 * holds is that the grid names exist for every child, that the verdict group really holds the decision line, the controls
 * and the history together (a form outside it would fall into the middle column), and that a narrow screen stacks them.
 *
 * `UIP-S09-01`: the same module draws the table, which is the tab's default. The last block holds what its CSS says of a decided row (an
 * accepted row on the frame's «ok» green, a rejected row struck through but for its decision cell and its state word, colour from tokens
 * only, no word cut mid-letter, the row's height and padding the global table's) and that the markup carries the names that CSS selects.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ProposalCard, ProposalTable } from '@/widgets/optimisation-proposals';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from '../styles/contrast';
import { newClient, renderScreen } from '../screens/harness';
import { decision, proposal, proposalShapes } from './fixtures';

const CSS = readFileSync(join(WEB_ROOT, 'src/widgets/optimisation-proposals/ui/optimisation-proposals.module.css'), 'utf8');
const rules = parseRules(CSS, 'module');
const area = (selector: string): string | undefined => rules.find((rule) => rule.selector === selector)?.declarations.get('grid-area');

describe('a proposal row', () => {
  it('places every child of the card on a named area', () => {
    expect({
      head: area('.cardHead'),
      prov: area('.provenance'),
      quote: area('.quote'),
      frame: area('.frame'),
      figs: area('.figures'),
      basis: area('.basis'),
      judgement: area('.judgement'),
      blocks: area('.sheetBlocks'),
    }).toEqual({ head: 'head', prov: 'prov', quote: 'quote', frame: 'frame', figs: 'figs', basis: 'basis', judgement: 'judgement', blocks: 'blocks' });
  });

  it('stacks the same areas, in the old order, below 1100px, with the sheet’s block strip (UI-B-09) last', () => {
    const narrow = /@media \(max-width: 1100px\)\s*\{[^}]*\.card\s*\{[^}]*grid-template-areas:\s*([^;]*);/.exec(CSS);
    expect(narrow, 'no stacked layout under 1100px').not.toBeNull();
    expect((narrow?.[1] ?? '').match(/'([a-z]+)'/g)).toEqual(["'head'", "'prov'", "'quote'", "'frame'", "'figs'", "'basis'", "'judgement'", "'blocks'"]);
  });

  it('keeps the decision line, the controls and the history in the verdict group', () => {
    const markup = renderScreen(newClient(), createElement(ProposalCard, {
      proposal: proposal({ current_verdict: 'revise', current_decision: decision() }),
      controls: createElement('div', { 'data-test-controls': '' }),
      history: createElement('div', { 'data-test-history': '' }),
    }));
    const group = /<div class="[^"]*judgement[^"]*">([\s\S]*?)<\/div><\/article>/.exec(markup)?.[1] ?? '';
    expect(group).toContain('Решение:');
    expect(group.indexOf('data-test-controls')).toBeGreaterThan(group.indexOf('Решение:'));
    expect(group.indexOf('data-test-history')).toBeGreaterThan(group.indexOf('data-test-controls'));
    // The two figures lines stay out of it: the quantity and the saving are the left column's.
    expect(group).not.toContain('Количество:');
  });

  it('gives the pass facts two label-and-value pairs to a line', () => {
    const facts = rules.find((rule) => rule.selector === '.facts')?.declarations.get('grid-template-columns') ?? '';
    expect(facts.match(/max-content/g)).toHaveLength(2);
  });
});

describe('the action bar of a proposals tab', () => {
  function loaded(): string {
    const shape = proposalShapes().find((entry) => entry.name === 'proposals-loaded');
    if (shape === undefined) throw new Error('no shape proposals-loaded');
    const client = newClient();
    shape.seedClient?.(client);
    return renderScreen(client, shape.make());
  }

  it('keeps the explanation of how proposals are built one click away, in the markup', () => {
    const markup = loaded();
    expect(markup).toMatch(/<details[^>]*><summary>Как строятся предложения<\/summary><p[^>]*>Предложение — отдельная сущность/);
  });

  it('puts «Запустить проход» and what it does in one bar', () => {
    const markup = loaded();
    expect(markup).toMatch(/<div class="[^"]*bar[^"]*"><button[^>]*>Запустить проход<\/button><p class="am-form__hint [^"]*hint[^"]*">Проход читает текущую версию/);
  });
});

describe('the strip over the proposals (UI-B-05)', () => {
  function loaded(): string {
    const shape = proposalShapes().find((entry) => entry.name === 'proposals-loaded');
    if (shape === undefined) throw new Error('no shape proposals-loaded');
    const client = newClient();
    shape.seedClient?.(client);
    return renderScreen(client, shape.make());
  }

  it('stands the counts by decision and the export beside each other, before the pass’s facts and the proposals', () => {
    const markup = loaded();
    const filter = markup.indexOf('data-decision-filter');
    const exportAt = markup.indexOf('data-proposals-export');
    const facts = markup.indexOf('data-pass-summary');
    const first = markup.indexOf('data-proposal="');
    expect(filter).toBeGreaterThan(-1);
    expect(exportAt).toBeGreaterThan(filter);
    expect(facts).toBeGreaterThan(exportAt);
    expect(first).toBeGreaterThan(facts);
    // One strip holds both.
    expect(markup.slice(markup.lastIndexOf('<div', filter), exportAt)).toMatch(/strip/);
  });

  it('keeps the pass’s facts in the markup, in a block the reader opens', () => {
    const markup = loaded();
    expect(markup).toMatch(/<details[^>]*data-pass-summary=""[^>]*><summary>Сведения о проходе<\/summary>/);
    expect(markup).toContain('не смешиваются со счётчиками замечаний');
  });
});

describe('the table’s rows by verdict (`UIP-S09-01`)', () => {
  const selectors = (rule: { readonly selector: string }): string[] => rule.selector.split(',').map((part) => part.trim());
  const declared = (selector: string, property: string): string | undefined =>
    rules.find((rule) => selectors(rule).includes(selector))?.declarations.get(property);
  const ROW = ".proposalTable tbody tr[data-decision='";
  const tableRules = rules.filter((rule) => selectors(rule).some((part) => part.startsWith('.proposalTable')));

  it('draws an accepted row on the frame’s «ok» green, from the token', () => {
    expect(declared(`${ROW}accept'] > td`, 'background')).toBe('var(--am-ok-light)');
  });

  it('strikes a rejected row through, but for the decision cell and the state word, and keeps its number struck', () => {
    expect(declared(`${ROW}reject'] > td`, 'text-decoration')).toBe('line-through');
    expect(declared(`${ROW}reject'] > td.judgement`, 'text-decoration')).toBe('none');
    expect(declared(`${ROW}reject'] > td.numberCell`, 'text-decoration')).toBe('none');
    expect(declared(`${ROW}reject'] > td.numberCell > strong`, 'text-decoration')).toBe('line-through');
  });

  it('draws only the verdicts that carry a colour or a line: a row waiting or sent back is plain', () => {
    const verdicts = new Set(tableRules.flatMap((rule) => selectors(rule)).flatMap((part) => [...part.matchAll(/data-decision='([a-z]+)'/g)].map((match) => match[1])));
    expect([...verdicts].sort()).toEqual(['accept', 'reject']);
  });

  it('takes every colour from a token', () => {
    for (const rule of [...tableRules, ...rules.filter((entry) => selectors(entry).includes('.layoutLink'))]) {
      for (const property of ['color', 'background', 'background-color', 'box-shadow', 'border-color', 'text-decoration-color']) {
        const value = rule.declarations.get(property);
        if (value === undefined) continue;
        expect(value, `${rule.selector} { ${property} }`).not.toMatch(/#[0-9a-f]{3,8}\b|\brgba?\(|\bhsla?\(/i);
      }
    }
  });

  it('never cuts a word mid-letter, and leaves the row’s height and padding to the global table', () => {
    for (const rule of tableRules) {
      expect(rule.declarations.get('overflow-wrap'), `${rule.selector} overflow-wrap`).not.toBe('anywhere');
      expect(rule.declarations.get('word-break'), `${rule.selector} word-break`).toBeUndefined();
      for (const property of ['height', 'min-height', 'padding', 'padding-block', 'padding-inline', 'border', 'border-collapse']) {
        expect(rule.declarations.has(property), `${rule.selector} { ${property} }`).toBe(false);
      }
    }
  });

  it('relies on the global table for what it does not say: a row of one step, a word kept whole', () => {
    const globals = parseRules(readFileSync(join(WEB_ROOT, 'src/app/globals.css'), 'utf8'), 'global');
    const own = (selector: string, property: string) =>
      globals.find((rule) => selectors(rule).includes(selector))?.declarations.get(property);
    expect(own('tbody tr', 'height')).toBe('var(--am-row-step)');
    expect(own('tbody td', 'overflow-wrap')).toBe('break-word');
    expect(own('tbody td', 'word-break')).toBe('normal');
  });

  const rowWith = (verdict: 'accept' | 'reject' | 'pending') =>
    renderScreen(
      newClient(),
      createElement(ProposalTable, {
        items: [proposal({ current_verdict: verdict, current_decision: verdict === 'pending' ? null : decision({ verdict }) })],
        canDecide: true,
        controlsFor: () => createElement('div', { 'data-test-controls': '' }),
      }),
    );

  it('carries the names that CSS selects: the verdict on the row, the number cell and the decision cell', () => {
    for (const verdict of ['accept', 'reject'] as const) {
      const markup = rowWith(verdict);
      expect(markup).toContain(`data-decision="${verdict}"`);
      expect(markup).toMatch(/<td class="[^"]*numberCell[^"]*"><strong>1<\/strong><span class="[^"]*state[^"]*">/);
      // The decision cell is the last one, and it holds the controls: the line is not drawn over a button.
      expect(markup).toMatch(/<td class="[^"]*judgement[^"]*">[\s\S]*data-test-controls[\s\S]*<\/td><\/tr>/);
    }
  });

  it('says the verdict in words as well as in colour and line', () => {
    expect(rowWith('accept')).toMatch(/<span class="[^"]*state[^"]*">принято<\/span>/);
    expect(rowWith('reject')).toMatch(/<span class="[^"]*state[^"]*">отклонено<\/span>/);
    expect(rowWith('reject')).toContain('Решение: <strong>отклонено</strong>');
  });
});
