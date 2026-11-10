/**
 * `D-615`: the stage table keeps the width of its words (lane FIX-D615).
 *
 * Lane WALK-V5 measured «Прогон» at 360, 414 and 1280 px with the width assertion's reading of a collapsed column (`D-565`: a visible
 * text box of 10 characters or more, under 90 px wide and over 70 px tall). `span.stage-table_name` was 72 x 71 px, four lines of
 * «Извлечение геометрии страниц и блоков», and `span.stage-table_dependency` 72 to 80 x 74 px, five lines of «после: …»: the table is
 * `width: 100%` with auto layout, its other four columns do not wrap, and the one column that holds words took what they left, down to
 * its longest word. Where the page is narrower than the columns the scroller takes the difference, so a floor on the one cell that
 * holds the name and what it waits for costs a scroll on a phone and nothing where the pane is wide.
 *
 * The table is drawn by `widgets/run-stages-dialog` («Этапы анализа раздела») and nowhere else. The suite renders markup in `node` and
 * cannot measure a width, so the cure is held as the declarations that make it (as `narrow-walk-v5.test.ts` holds the others); every
 * check runs first on a fixture that lacks the rule, so it can fail, and then on the real module, so it reads this tree.
 *
 *  - the cell that holds the name and the dependency has a floor, 11 rem or more, in no media query (it holds at every width);
 *  - it has no ceiling: where the pane can give the table its full width, it takes it;
 *  - the markup puts both the name and the dependency in that cell, so one floor covers both;
 *  - the dialog's right pane may shrink under the table (`min-width: 0`), so the floor is met by the scroller and not by a wider dialog.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from './contrast';
import { declares, withoutMedia } from './css-reads';

const source = (...parts: readonly string[]): string => readFileSync(join(WEB_ROOT, 'src', ...parts), 'utf8');

/** The `min-width` a selector declares in `rem`, as a number, or `null` when it declares none (or one in another unit). */
function minRem(css: string, selector: string): number | null {
  for (const rule of parseRules(withoutMedia(css), 'test')) {
    if (!rule.selector.split(',').some((part) => part.trim() === selector)) continue;
    const match = /^(\d+(?:\.\d+)?)rem$/.exec(rule.declarations.get('min-width') ?? '');
    if (match !== null) return Number(match[1]);
  }
  return null;
}

/** Whether any rule of the sheet, at any width, caps a width (`max-width`, or a fixed layout that fixes the columns). */
function capsAWidth(css: string): boolean {
  return parseRules(css, 'test').some(
    (rule) => rule.declarations.has('max-width') || /^fixed$/.test(rule.declarations.get('table-layout') ?? ''),
  );
}

describe('the readers can fail (lane FIX-D615)', () => {
  const OLD = '.name { font-weight: 500; }\n.dependency { display: block; margin-top: 2px; }';
  it('read no floor from the stylesheet as it was, and a floor from one that has it', () => {
    expect(minRem(OLD, '.stage')).toBeNull();
    expect(minRem(OLD, '.name')).toBeNull();
    expect(minRem('.stage { min-width: 12rem; }', '.stage')).toBe(12);
    expect(minRem('@media (max-width: 600px) { .stage { min-width: 12rem; } }', '.stage')).toBeNull();
    expect(minRem('.stage { min-width: 120px; }', '.stage')).toBeNull();
  });

  it('read a ceiling when there is one, and none when there is not', () => {
    expect(capsAWidth('.stage { min-width: 12rem; max-width: 14rem; }')).toBe(true);
    expect(capsAWidth('table { table-layout: fixed; }')).toBe(true);
    expect(capsAWidth('.stage { min-width: 12rem; }')).toBe(false);
  });
});

describe('«Прогон», the stage table: the name and what it waits for keep the width of their words (lane FIX-D615)', () => {
  const TABLE = source('entities', 'audit-run', 'ui', 'stage-table.module.css');
  const MARKUP = source('entities', 'audit-run', 'ui', 'stage-table.tsx');
  const DIALOG = source('widgets', 'run-stages-dialog', 'ui', 'run-stages-dialog.module.css');

  it('gives the cell a floor of 11 rem or more at every width: the longest name, two lines, never the 72 px of its longest word', () => {
    expect(minRem(TABLE, '.stage') ?? 0).toBeGreaterThanOrEqual(11);
    expect(declares(withoutMedia(TABLE), '.stage', 'min-width', /\S/)).toBe(true);
  });

  it('puts no ceiling on the table, its cell or its scroller, so a wide pane gives the table all of its width', () => {
    expect(capsAWidth(TABLE)).toBe(false);
    // The table itself is the global `width: 100%`; the scroller around it scrolls where the columns do not fit.
    expect(declares(TABLE, '.scroller', 'overflow-x', /^auto$/)).toBe(true);
  });

  it('draws the name and the dependency in the floored cell', () => {
    const cell = /<td className=\{styles\.stage\}>([\s\S]*?)<\/td>/.exec(MARKUP);
    expect(cell).not.toBeNull();
    expect(cell?.[1]).toContain('styles.name');
    expect(cell?.[1]).toContain('<DependencyNote');
  });

  it('lets the dialog\'s right pane shrink under the table, so the scroller meets the floor and the dialog does not widen', () => {
    expect(declares(DIALOG, '.detail', 'min-width', /^0$/)).toBe(true);
    expect(declares(withoutMedia(DIALOG), '.body', 'grid-template-columns', /^minmax\(0, 1fr\)$/)).toBe(true);
  });
});
