/**
 * The count of raw length literals in the CSS modules may not grow.
 *
 * `W31-STYLE` and the design contract (`DESIGN-31-SCREEN-PLAN`, items 1 and 6) put spacing,
 * radii and type through tokens (`--am-gap-*`, `--am-radius-*`, `--am-text-*`). The tokens
 * exist and most modules read them, but nothing counted the places that spell the value
 * instead: `padding: 8px 14px`, `border-radius: 0.5rem`, `font-size: .8rem`. On 2026-11-02
 * the count was 560 across 59 of the 93 modules, with the largest in the newest code (the
 * application frame, 76, and the sign-in page, 61), so the drift was growing with every
 * design task. (The review of that day counted 465 with a coarser rule; this file's own
 * definition, below, is the one the number is measured by.)
 *
 * What is counted: a number followed by `px`, `rem` or `em` inside a declaration of
 * `border-radius` (and its corner longhands), `padding*`, `margin*`, `gap`, `row-gap`,
 * `column-gap`, `font-size` or `line-height`, in any `*.module.css`. A literal inside
 * `clamp()`/`calc()`/`minmax()` or a `var()` fallback is counted; a token read, a unitless
 * `0` and a percentage are not. It is a RATCHET and not a verdict: the number may fall (lower
 * the ceiling when it does) and may not rise, so a new rule that spells a value instead of
 * reading a token fails here and is written with the token.
 */

import { readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

import { parseRules } from './contrast';
import { WEB_ROOT, walkFiles } from '../../guards/lib/repo';

const SRC = join(WEB_ROOT, 'src');

const COUNTED =
  /^(?:border(?:-(?:top|bottom|start|end)-(?:left|right|start|end))?-radius|padding(?:-[a-z]+)*|margin(?:-[a-z]+)*|gap|row-gap|column-gap|font-size|line-height)$/;
const LITERAL = /(?<![\w-])[+-]?(?:\d+\.?\d*|\.\d+)(?:px|rem|em)\b/g;

export interface LengthLiteral {
  readonly property: string;
  readonly value: string;
  readonly count: number;
}

/** Every counted declaration that spells a length, with how many literals it spells. */
export function lengthLiterals(css: string): readonly LengthLiteral[] {
  const found: LengthLiteral[] = [];
  for (const rule of parseRules(css, 'module')) {
    for (const [property, value] of rule.declarations) {
      if (!COUNTED.test(property)) continue;
      const count = (value.match(LITERAL) ?? []).length;
      if (count > 0) found.push({ property, value, count });
    }
  }
  return found;
}

const MODULES = walkFiles(SRC, (path) => path.endsWith('.module.css'));

function countOf(path: string): number {
  return lengthLiterals(readFileSync(path, 'utf8')).reduce((sum, entry) => sum + entry.count, 0);
}

/**
 * Measured on 2026-11-02 over the modules of `web/src`, after the static inline styles had
 * moved into them (those use tokens and added none), by `lengthLiterals` below -- the second
 * case of this file prints the same sum when it fails. Lower it when you remove literals;
 * raising it needs a reason a reader can check.
 */
// 2026-11-06: the schedule modules and the second density pass replaced their literals with tokens (628 -> 442).
// 2026-11-07 (lane D5): the application frame, the sign-in page and the release notices read tokens (442 -> 306 measured);
// the ceiling is 320 so the lanes merged beside this one keep a little room, and it is lowered again when they settle.
// 2026-11-08 (lane P7): measured 255 on base 5f396ff26 and 242 after the frame module read the gap tokens its literals equal
// (13 of them); `npx vitest run` of the counting copy of this file printed 242. The ceiling is 250: eight literals of room.
const CEILING = 250;

describe('the CSS modules spell no more lengths than they did on 2026-11-02', () => {
  it('reads the modules of the whole tree', () => {
    expect(MODULES.length).toBeGreaterThan(80);
  });

  it('holds the count at or under the ceiling', () => {
    const perModule = MODULES.map((path) => ({ module: relative(WEB_ROOT, path), count: countOf(path) }));
    const total = perModule.reduce((sum, entry) => sum + entry.count, 0);
    const worst = perModule.filter((entry) => entry.count > 0).sort((a, b) => b.count - a.count).slice(0, 8);
    expect(
      total,
      `the modules spell ${total} lengths in spacing, radius and type declarations; the ceiling is ` +
        `${CEILING}. Read --am-gap-*, --am-radius-* and --am-text-* instead of a value. Largest: ` +
        worst.map((entry) => `${entry.module} ${entry.count}`).join('; '),
    ).toBeLessThanOrEqual(CEILING);
  });

  it('can fail: counts a spelled length, in every position, and counts a token read as nothing', () => {
    const css = [
      '.a { padding: 8px 0.5rem; margin: 0 auto; gap: var(--am-gap-sm); }',
      '.b { border-radius: .75rem; font-size: clamp(1rem, 2vw, 1.4rem); line-height: 1.5; }',
      '.c { margin-block: var(--am-gap, 4px); padding-inline: calc(var(--am-gap) + 2px); }',
      '.d { width: 10px; min-height: 5rem; border: 1px solid var(--am-line); }',
      '.e { border-top-left-radius: 3px; row-gap: -2px; font-size: var(--am-text-sm); }',
    ].join('\n');
    const found = lengthLiterals(css);
    expect(found.map((entry) => [entry.property, entry.count])).toEqual([
      ['padding', 2],
      ['border-radius', 1],
      ['font-size', 2],
      ['margin-block', 1],
      ['padding-inline', 1],
      ['border-top-left-radius', 1],
      ['row-gap', 1],
    ]);
    expect(found.reduce((sum, entry) => sum + entry.count, 0)).toBe(9);
    expect(lengthLiterals('.x { padding: var(--am-gap) 0; margin: 0; font-size: var(--am-text-md); gap: 50%; }')).toEqual([]);
  });
});
