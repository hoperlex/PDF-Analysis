/**
 * `UI-PARITY-DENSE`, `UI-B-34`: a decision in the knowledge base is a row of the original's table (`kb-table`), not a card.
 *
 * The rows keep their markup (the render tests of the journal pin it); the page's module places the record's own children on
 * a grid. These cases hold that every child has an area, that the last paragraph (who, when, the way to the finding) is the
 * third column and not whichever `<p>` happens to come last, and that a narrow screen stacks them in reading order.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from '../styles/contrast';
import { declares, withoutMedia } from '../styles/css-reads';

const read = (path: string): string => readFileSync(join(WEB_ROOT, 'src', path), 'utf8');
const PAGE = read('_pages/knowledge-base/ui/knowledge-base-page.module.css');
const WIDGET = read('widgets/knowledge-base/ui/knowledge-base.module.css');
const area = (css: string, selector: string): string | undefined =>
  parseRules(css, 'module').find((rule) => rule.selector === selector)?.declarations.get('grid-area');

describe('the findings and «Все» rows', () => {
  it('place the heading, the place line, the text, the comment and the author line on the grid', () => {
    expect({
      heading: area(WIDGET, '.records :global(.am-kb__heading)'),
      place: area(WIDGET, '.records > :global(.am-kb__record) > [data-record-place]'),
      text: area(WIDGET, '.records :global(.am-kb__text)'),
      comment: area(WIDGET, '.records :global(.am-kb__comment)'),
      meta: area(WIDGET, '.records > :global(.am-kb__record) > :global(.am-kb__meta):last-child'),
    }).toEqual({ heading: 'head', place: 'place', text: 'text', comment: 'comment', meta: 'meta' });
  });

  it('are three columns and two lines, with the legend over the same three, and stack below 900px', () => {
    const rules = parseRules(WIDGET, 'module');
    const record = rules.find((rule) => rule.selector === '.records > :global(.am-kb__record)');
    expect(record?.declarations.get('display')).toBe('grid');
    const columns = record?.declarations.get('grid-template-columns');
    expect(columns?.match(/minmax/g)).toHaveLength(3);
    expect(rules.find((rule) => rule.selector === '.legend')?.declarations.get('grid-template-columns')).toBe(columns);
    const stacked = /@media \(max-width: 900px\)\s*\{[^@]*grid-template-areas:([^;]*);/.exec(WIDGET);
    expect((stacked?.[1] ?? '').match(/'([a-z]+)'/g)).toEqual(["'head'", "'place'", "'text'", "'comment'", "'meta'"]);
  });

  it('keep the page free of the layout, which the widget owns, and the three filters in a row', () => {
    expect(PAGE).not.toContain('grid-template-areas');
    const filter = parseRules(PAGE, 'module').find((rule) => rule.selector === '.filters :global(.am-kb__filter)');
    expect(filter?.declarations.get('flex-direction')).toBe('row');
  });
});

describe('the «Предложения» rows', () => {
  const JOURNAL = read('widgets/proposal-journal/ui/proposal-decisions.module.css');

  it('place the verdict, the row, the comment and the vendor line on the same three columns', () => {
    expect({
      head: area(JOURNAL, '.head'),
      text: area(JOURNAL, '.text'),
      comment: area(JOURNAL, '.comment'),
      meta: area(JOURNAL, '.meta'),
    }).toEqual({ head: 'head', text: 'text', comment: 'comment', meta: 'meta' });
  });
});

/**
 * `UIP-S12-02`: the table's rows are one or two lines. A stylesheet is read here, not measured (the suite renders markup in `node`);
 * each reading runs first on a fixture that lacks the rule, so it can fail, and then on the real module.
 */
describe('the table’s rows are dense (UIP-S12-02)', () => {
  const OLD = '.table td { overflow-wrap: anywhere; vertical-align: top; }\n.table tbody tr:hover { background: x; }';
  const base = withoutMedia(WIDGET);

  it('can fail: the old cells, which break a word anywhere and state no row height, read as wrong', () => {
    expect(declares(OLD, '.table td', 'overflow-wrap', /^break-word$/)).toBe(false);
    expect(declares(OLD, '.table tbody tr', 'height', /^var\(--am-row-step-tall\)$/)).toBe(false);
    expect(declares(OLD, '.place', 'text-overflow', /^ellipsis$/)).toBe(false);
  });

  it('keeps a word whole in a cell: break-word, never anywhere', () => {
    expect(declares(base, '.table td', 'overflow-wrap', /^break-word$/)).toBe(true);
    expect(declares(base, '.table td', 'word-break', /^normal$/)).toBe(true);
    expect(/overflow-wrap:\s*anywhere/.test(base.slice(base.indexOf('.tableFrame')))).toBe(false);
  });

  it('gives a row the step `UIP-G-14` made for this screen, a token and no literal', () => {
    expect(declares(base, '.table tbody tr', 'height', /^var\(--am-row-step-tall\)$/)).toBe(true);
  });

  it('cuts the object and the document at one line with an ellipsis, and the gist and the reason at two lines', () => {
    expect(declares(base, '.place', 'white-space', /^nowrap$/)).toBe(true);
    expect(declares(base, '.place', 'text-overflow', /^ellipsis$/)).toBe(true);
    expect(declares(base, '.place', 'overflow', /^hidden$/)).toBe(true);
    expect(declares(base, '.clamp', '-webkit-line-clamp', /^2$/)).toBe(true);
    expect(declares(base, '.clamp', 'overflow', /^hidden$/)).toBe(true);
  });

  it('keeps the date and the way to the finding on one line', () => {
    expect(declares(base, '.cellDate', 'white-space', /^nowrap$/)).toBe(true);
    expect(declares(base, '.cellLink', 'white-space', /^nowrap$/)).toBe(true);
  });

  it('draws the verdict stripe of a finding and of a proposal, in the ok and failed tokens', () => {
    const stripe = (selector: string) =>
      parseRules(WIDGET, 'module').find((rule) => rule.selector.split(',').some((part) => part.trim() === selector))?.declarations.get('box-shadow');
    expect(stripe(".table tbody tr[data-current-verdict='accepted'] > :first-child")).toBe('inset 3px 0 0 var(--am-ok)');
    expect(stripe(".table tbody tr[data-current-verdict='rejected'] > :first-child")).toBe('inset 3px 0 0 var(--am-failed)');
    expect(stripe(".table tbody tr[data-proposal-verdict='accept'] > :first-child")).toBe('inset 3px 0 0 var(--am-ok)');
    expect(stripe(".table tbody tr[data-proposal-verdict='reject'] > :first-child")).toBe('inset 3px 0 0 var(--am-failed)');
  });

  it('has no «Решение» column left: neither its floor nor its event label', () => {
    expect(WIDGET).not.toContain('.colVerdict');
    expect(read('widgets/knowledge-base/ui/knowledge-base-table.tsx')).not.toContain('colVerdict');
    expect(read('widgets/knowledge-base/ui/knowledge-base-table.tsx')).not.toContain('am-kb__event');
  });
});
