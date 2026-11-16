/**
 * The sizes of the reference interface as shared tokens (`UIP-G-14`).
 *
 * The comparison of 2026-11-16 measured the original's frame and lists: a 55 px top strip, a page margin of 20 px above and
 * below and 24 px at the sides, a table row one step of 40 px high, a document card of 161 by 67 px, an object picker 480 px wide.
 * The owner took the SIZES and left the look (radii, shadows, hairlines, colour, typeface: `R-33`, the poll of 2026-11-16), so a
 * size is a token in `globals.css` that the shared layer reads and a screen module reads after it, and not a number each module
 * spells for itself.
 *
 * The suite renders markup under `environment: 'node'` and cannot measure a row, so it holds the DECLARATIONS that produce the
 * measurement (the row heights, strip heights and margins were measured once in headless Chrome at 1440, 1024 and 390 px and are
 * in the task record). Each check is a pure function over a stylesheet's text, exercised on a fixture of the old shape (what
 * proves it can fail) and then on the real files (what proves it reads this tree).
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules, parseTokens, splitSelectorList } from './contrast';
import { declares, declaresIn, withoutMedia } from './css-reads';

const GLOBALS = readFileSync(join(WEB_ROOT, 'src', 'app', 'globals.css'), 'utf8');
const TABLE = readFileSync(join(WEB_ROOT, 'src', 'shared', 'ui', 'table.module.css'), 'utf8');
const VIEWER = readFileSync(join(WEB_ROOT, 'src', 'widgets', 'evidence-viewer', 'ui', 'document-viewer.module.css'), 'utf8');

/** What the first `:root` block must say, token by token. A size is declared once, in the base block, and never per theme. */
const SIZE_TOKENS: Readonly<Record<string, string>> = {
  '--am-strip-height': '55px',
  '--am-strip-height-compact': '44px',
  '--am-page-pad-y': '20px',
  '--am-page-pad-x': '24px',
  '--am-row-step': '40px',
  '--am-row-step-tall': '53px',
  '--am-card-doc-width': '161px',
  '--am-card-doc-height': '67px',
  '--am-picker-width': '480px',
  '--am-picker-width-max': '560px',
  '--am-picker-row-step': '42px',
  '--am-picker-badge-min': '38px',
};

const NARROW = 'max-width: 1023.98px';
const PHONE = 'max-width: 590px';

/** The declarations of `selector` in the base rules (no `@media` block) for one property, or `''`. */
function base(css: string, selector: string, property: string): string {
  for (const rule of parseRules(withoutMedia(css), 'test')) {
    if (rule.selector.split(',').some((part) => part.trim() === selector) && rule.declarations.has(property)) {
      return rule.declarations.get(property) ?? '';
    }
  }
  return '';
}

/** The `overflow-wrap` of every rule aimed at a cell of a table (one value per rule): a selector whose LAST compound is `td`, `th` or `.cell`. */
export function cellWrapValues(css: string): readonly string[] {
  const values: string[] = [];
  for (const rule of parseRules(css, 'test')) {
    const aimedAtACell = splitSelectorList(rule.selector).some((selector) => {
      const last = selector.split(/\s*[>+~]\s*|\s+/).pop() ?? '';
      return /^(?:td|th|\.cell)(?![\w-])/.test(last);
    });
    const wrap = rule.declarations.get('overflow-wrap');
    if (aimedAtACell && wrap !== undefined) values.push(wrap);
  }
  return values;
}

describe('the readers can fail (UIP-G-14)', () => {
  const OLD_ROOT = ':root { --am-gap: 16px; --am-strip-height: 44px; }';
  const OLD_RULES =
    '.am-app__main { padding: var(--am-gap) var(--am-gap-lg) var(--am-gap-lg); }\n' +
    '.am-app__utility { min-height: 44px; }\n' +
    'tbody td { padding: 5px 12px 5px 0; overflow-wrap: anywhere; }\n' +
    'tbody tr { transition: background 90ms; }\n' +
    '.cell { overflow-wrap: anywhere; }\n' +
    ':where(p, li, td) > code { overflow-wrap: anywhere; }';

  it('reads a token value only from the base block, and none from a stylesheet that lacks it', () => {
    expect(parseTokens(OLD_ROOT).get('--am-strip-height')).toBe('44px');
    expect(parseTokens(OLD_ROOT).has('--am-row-step')).toBe(false);
    expect(parseTokens(':root { --am-row-step: 40px; }').get('--am-row-step')).toBe('40px');
  });

  it('reads no token reader from the old rules', () => {
    expect(base(OLD_RULES, '.am-app__main', 'padding')).not.toContain('--am-page-pad');
    expect(base(OLD_RULES, '.am-app__utility', 'min-height')).not.toContain('var(--am-strip-height)');
    expect(base(OLD_RULES, 'tbody tr', 'height')).toBe('');
    expect(base('tbody tr { height: var(--am-row-step); }', 'tbody tr', 'height')).toBe('var(--am-row-step)');
    expect(declaresIn('@media (max-width: 590px) { .a { padding: 0; } }', PHONE, '.a', 'padding', /^0$/)).toBe(true);
    expect(declaresIn('.a { padding: 0; }', PHONE, '.a', 'padding', /^0$/)).toBe(false);
  });

  it('finds an overflow-wrap on a cell and not on a code chip inside one', () => {
    expect(cellWrapValues(OLD_RULES)).toEqual(['anywhere', 'anywhere']);
    expect(cellWrapValues(':where(p, li, td) > code { overflow-wrap: anywhere; }')).toEqual([]);
    expect(cellWrapValues('.table th, .table td { overflow-wrap: anywhere; }')).toEqual(['anywhere']);
    expect(cellWrapValues('tbody td { overflow-wrap: break-word; }')).toEqual(['break-word']);
  });
});

describe('the sizes of the reference interface are tokens (UIP-G-14)', () => {
  const tokens = parseTokens(GLOBALS);

  it('has every size token with the value the comparison measured', () => {
    for (const [name, value] of Object.entries(SIZE_TOKENS)) {
      expect(tokens.get(name as `--am-${string}`), `${name} in the base :root block`).toBe(value);
    }
  });

  it('declares each size once, so the two palettes cannot drift on it', () => {
    const css = GLOBALS.replace(/\/\*[\s\S]*?\*\//g, '');
    for (const name of Object.keys(SIZE_TOKENS)) {
      const declared = [...css.matchAll(new RegExp(`${name}\\s*:\\s*([^;]+);`, 'g'))].map((match) => (match[1] ?? '').trim());
      expect(declared, `${name} is declared more or less than once`).toEqual([SIZE_TOKENS[name]]);
    }
  });
});

describe('the frame reads the size tokens (UIP-G-14)', () => {
  it('stands the top strip at the strip height, and at the compact one where it is not pinned', () => {
    expect(base(GLOBALS, '.am-app__utility', 'min-height')).toBe('var(--am-strip-height)');
    expect(declaresIn(GLOBALS, NARROW, '.am-app__utility', 'min-height', /^var\(--am-strip-height-compact\)$/)).toBe(true);
    expect(declaresIn(GLOBALS, NARROW, '.am-app__utility', 'position', /^relative$/)).toBe(true);
  });

  it('starts every pinned panel and every focus jump below the strip, and below the old height where the strip is in the flow', () => {
    expect(base(GLOBALS, 'html', 'scroll-padding-top')).toBe('calc(var(--am-strip-height) + var(--am-gap-sm))');
    expect(declaresIn(GLOBALS, NARROW, 'html', 'scroll-padding-top', /var\(--am-strip-height-compact\)/)).toBe(true);
    expect(base(GLOBALS, '.am-review__list', 'top')).toBe('calc(var(--am-strip-height) + var(--am-gap-md))');
    expect(base(GLOBALS, '.am-review__list', 'max-height')).toContain('var(--am-strip-height)');
    expect(declaresIn(GLOBALS, NARROW, '.am-review__list', 'top', /var\(--am-strip-height-compact\)/)).toBe(true);
    expect(declaresIn(GLOBALS, NARROW, '.am-review__list', 'max-height', /var\(--am-strip-height-compact\)/)).toBe(true);
  });

  it('margins the page by the page tokens, and keeps 12/16 and 8/12 at the narrow widths', () => {
    expect(base(GLOBALS, '.am-app__main', 'padding')).toBe('var(--am-page-pad-y) var(--am-page-pad-x)');
    expect(declaresIn(GLOBALS, NARROW, '.am-app__main', 'padding', /^var\(--am-gap-md\) var\(--am-gap\)$/)).toBe(true);
    expect(declaresIn(GLOBALS, PHONE, '.am-app__main', 'padding', /^var\(--am-gap-sm\) var\(--am-gap-md\) var\(--am-gap-md\)$/)).toBe(true);
  });
});

describe('a table row is one step high, and a word keeps its width (UIP-G-14)', () => {
  it('floors the row of the base layer and the cell of the shared table at the row step', () => {
    expect(base(GLOBALS, 'tbody tr', 'height')).toBe('var(--am-row-step)');
    expect(base(TABLE, '.cell', 'height')).toBe('var(--am-row-step)');
  });

  it('centres a one-line cell in its row, so the step is not 11 px of nothing under the text', () => {
    expect(base(GLOBALS, 'tbody td', 'vertical-align')).toBe('middle');
    expect(base(TABLE, '.cell', 'vertical-align')).toBe('middle');
  });

  it('breaks a word only when it cannot fit its own line: no cell of the shared layer says `anywhere`', () => {
    expect(cellWrapValues(GLOBALS)).not.toContain('anywhere');
    expect(cellWrapValues(TABLE)).not.toContain('anywhere');
    expect(base(GLOBALS, 'tbody td', 'overflow-wrap')).toBe('break-word');
    expect(base(TABLE, '.cell', 'overflow-wrap')).toBe('break-word');
    // `word-break` is inherited, so a cell states it rather than trusting every ancestor.
    expect(base(GLOBALS, 'tbody td', 'word-break')).toBe('normal');
    expect(base(TABLE, '.cell', 'word-break')).toBe('normal');
  });

  it('keeps the head of the table where it was: a header stays one line and is not stretched to a row step', () => {
    expect(base(GLOBALS, 'thead th', 'white-space')).toBe('nowrap');
    expect(base(GLOBALS, 'thead th', 'height')).toBe('');
    expect(base(TABLE, '.head', 'height')).toBe('');
  });
});

describe('the viewer buttons keep their width when the strip grows (UIP-G-14)', () => {
  it('reads the compact height for the width of the step and close buttons, and never the strip height', () => {
    expect(declares(VIEWER, '.step', 'min-width', /^var\(--am-strip-height-compact\)$/)).toBe(true);
    expect(declares(VIEWER, '.close', 'min-width', /^var\(--am-strip-height-compact\)$/)).toBe(true);
    expect(VIEWER.replace(/\/\*[\s\S]*?\*\//g, '')).not.toMatch(/var\(--am-strip-height\)/);
  });
});
