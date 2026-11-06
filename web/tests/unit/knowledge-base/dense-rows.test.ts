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
const area = (css: string, selector: string): string | undefined =>
  parseRules(css, 'module').find((rule) => rule.selector === selector)?.declarations.get('grid-area');

describe('the findings and «Все» rows', () => {
  it('place the heading, the place line, the text, the comment and the author line on the grid', () => {
    expect({
      heading: area(PAGE, '.results :global(.am-kb__heading)'),
      place: area(PAGE, '.results :global(.am-kb__record > [data-record-place])'),
      text: area(PAGE, '.results :global(.am-kb__text)'),
      comment: area(PAGE, '.results :global(.am-kb__comment)'),
      meta: area(PAGE, '.results :global(.am-kb__record > .am-kb__meta:last-child)'),
    }).toEqual({ heading: 'head', place: 'place', text: 'text', comment: 'comment', meta: 'meta' });
  });

  it('are three columns and two lines, and stack below 900px', () => {
    const record = parseRules(PAGE, 'module').find((rule) => rule.selector === '.results :global(.am-kb__record)');
    expect(record?.declarations.get('display')).toBe('grid');
    expect(record?.declarations.get('grid-template-columns')?.match(/minmax/g)).toHaveLength(3);
    const stacked = /@media \(max-width: 900px\)\s*\{\s*\.results :global\(\.am-kb__record\)\s*\{[^}]*grid-template-areas:([^;]*);/.exec(PAGE);
    expect((stacked?.[1] ?? '').match(/'([a-z]+)'/g)).toEqual(["'head'", "'place'", "'text'", "'comment'", "'meta'"]);
  });

  it('keep the three filters in a row, each label beside its control', () => {
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
