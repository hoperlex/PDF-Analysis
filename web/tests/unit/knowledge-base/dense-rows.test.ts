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
