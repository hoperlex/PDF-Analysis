/**
 * Three faults that made a screen scroll sideways at 390 px in the browser walk of lane V3 (2026-11-08, a throwaway stand, a built `next start`).
 *
 * The suite renders markup under `environment: 'node'` and cannot measure a width, so the cause is held as the declarations that
 * cured it; each check below is a pure function over a stylesheet's text, run on a fixture that lacks the rule (so it can fail)
 * and on the real module (so it reads this tree). The measurements are in the lane's evidence, not here.
 *
 *  - «Сравнение стадий»: `.actions label` was an inline flex row that could not wrap, and its `<select>` is as wide as its longest
 *    option («V3 · эксперимент, только текст PDF»). The batch panel's minimum width became 357 px, the grid track of the pair
 *    catalog followed it and the page ended at 399 px. The label now wraps its select under the caption.
 *  - «Сравнение стадий» with a confirmed pair: the pair catalog is a grid whose one track was `auto`, so the table of pairs
 *    (797 px of columns) set the track's minimum and the page ended at 839 px at 390 px and at 843 px at 780 px, while the table's
 *    own scroller never scrolled. The track is `minmax(0, 1fr)` now and the table scrolls inside its box.
 *  - The frame's end group («Выдача приостановлена», «Возобновить», the instance mark, the account): it was `flex: 0 0 auto` with
 *    no wrap, so while dispatch was paused an administrator's every screen ended at 471 px. The group is capped at the bar and wraps.
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

const CONTROLS = readFileSync(join(WEB_ROOT, 'src', 'widgets', 'stage-run-controls', 'ui', 'stage-run-controls.module.css'), 'utf8');
const FRAME = readFileSync(join(WEB_ROOT, 'src', '_app', 'app-frame.module.css'), 'utf8');
const CATALOG = readFileSync(join(WEB_ROOT, 'src', 'widgets', 'stage-pair-catalog', 'ui', 'stage-pair-catalog.module.css'), 'utf8');

describe('three screens keep inside 390 px (lane V3)', () => {
  it('can fail: a rule that lacks the declaration, or declares another value, reads as absent', () => {
    const css = '.actions label { display: inline-flex; gap: .35rem; }\n.end { flex-wrap: nowrap; max-width: none; }';
    expect(declares(css, '.actions label', 'flex-wrap', /^wrap$/)).toBe(false);
    expect(declares(css, '.end', 'flex-wrap', /^wrap$/)).toBe(false);
    expect(declares(css, '.end', 'max-width', /^100%$/)).toBe(false);
    expect(declares('.actions label { flex-wrap: wrap; }', '.actions label', 'flex-wrap', /^wrap$/)).toBe(true);
  });

  it('gives the pair catalog one track that may shrink, so the table of pairs scrolls inside its box', () => {
    expect(declares(CATALOG, '.catalog', 'display', /^grid$/)).toBe(true);
    expect(declares(CATALOG, '.catalog', 'grid-template-columns', /^minmax\(0, 1fr\)$/)).toBe(true);
    expect(declares('.catalog { display: grid; gap: 1.5rem; }', '.catalog', 'grid-template-columns', /^minmax\(0, 1fr\)$/)).toBe(false);
  });

  it('lets the label of the stage comparison\'s controls wrap its select under the caption', () => {
    expect(declares(CONTROLS, '.actions label', 'display', /inline-flex/)).toBe(true);
    expect(declares(CONTROLS, '.actions label', 'flex-wrap', /^wrap$/)).toBe(true);
  });

  it('caps the frame\'s end group at the bar and lets it wrap, so a paused-dispatch strip cannot widen every screen', () => {
    expect(declares(FRAME, '.end', 'flex-wrap', /^wrap$/)).toBe(true);
    expect(declares(FRAME, '.end', 'max-width', /^100%$/)).toBe(true);
  });
});
