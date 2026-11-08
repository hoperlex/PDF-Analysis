/**
 * A fault that made «Оптимизация разделов» scroll sideways at 390 px in the browser walk of lane J2 (2026-11-09, a throwaway stand of
 * the 0.18.2 tree, `journey.mjs --phase read --width 390`).
 *
 * The suite renders markup under `environment: 'node'` and cannot measure a width, so the cause is held as the declaration that
 * cured it, as in `narrow-walk-v3.test.ts`: a pure function over a stylesheet's text, run on a fixture that lacks the rule (so it can
 * fail) and on the real module (so it reads this tree). The measurement is in the lane's evidence, not here.
 *
 *  - «Оптимизация разделов», the section's project cards: the grid's track minimum was `24rem` (384 px), more than the 350 px a
 *    390 px screen leaves a card, so the card (`article`, right edge 409 px) pushed the page to `scrollWidth 409 > innerWidth 390`.
 *    The minimum is `min(100%, 24rem)` now, the idiom the preset, classify and connection forms and the workers overview use, so a
 *    track never asks for more than its container.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from './contrast';

function declares(css: string, selector: string, property: string, value: RegExp): boolean {
  return parseRules(css, 'test').some(
    (rule) =>
      rule.selector.split(',').some((part) => part.trim() === selector) && value.test(rule.declarations.get(property) ?? ''),
  );
}

const SPECIFICATION = readFileSync(
  join(WEB_ROOT, 'src', 'widgets', 'section-specification', 'ui', 'section-specification.module.css'),
  'utf8',
);

describe('«Оптимизация разделов» keeps inside 390 px (lane J2)', () => {
  const SHRINKS = /^repeat\(auto-fill, minmax\(min\(100%, 24rem\), 1fr\)\)$/;

  it('can fail: a track whose minimum is a fixed 24rem reads as absent', () => {
    expect(declares('.projects { grid-template-columns: repeat(auto-fill, minmax(24rem, 1fr)); }', '.projects', 'grid-template-columns', SHRINKS)).toBe(false);
    expect(declares('.projects { display: grid; }', '.projects', 'grid-template-columns', SHRINKS)).toBe(false);
    expect(
      declares('.projects { grid-template-columns: repeat(auto-fill, minmax(min(100%, 24rem), 1fr)); }', '.projects', 'grid-template-columns', SHRINKS),
    ).toBe(true);
  });

  it('gives the section\'s project cards a track that never asks for more than its container', () => {
    expect(declares(SPECIFICATION, '.projects', 'display', /^grid$/)).toBe(true);
    expect(declares(SPECIFICATION, '.projects', 'grid-template-columns', SHRINKS)).toBe(true);
    expect(declares(SPECIFICATION, '.project', 'min-width', /^0$/)).toBe(true);
  });
});
