/**
 * `UI-PARITY-DENSE`, `UI-B-06`: a proposal is a row of the original's table, not a card of ten stacked lines.
 *
 * The three columns are CSS grid areas over the card's own children: the source and the figures at the left, the
 * specification row with the two positions in the middle, the verdict with its form and history at the right. What this file
 * holds is that the grid names exist for every child, that the verdict group really holds the decision line, the controls
 * and the history together (a form outside it would fall into the middle column), and that a narrow screen stacks them.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ProposalCard } from '@/widgets/optimisation-proposals';

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
