/**
 * Three layout faults of 0.20.3 that no width assertion could see, because nothing scrolled sideways: a grid column collapsed and the
 * page grew taller instead (browser walk WALK-V4, 2026-11-09, a throwaway stand of a built `next start`, DOM facts over CDP).
 *
 *  - «Главная»: the tasks and the section table sat side by side from 1280 px. The table's row needs about 520 px beside its name
 *    (five numbers of 5.5rem, the arrow, the gaps and the paddings), and the table's column is 0.575 of the page less 293 px: the
 *    name button was 12 px wide at 1280 (rows 797 px tall, the page 9065 px), 104 px at 1440, 242 px at 1680. Two columns now start
 *    at 1680 px, where the name is 190 px and a row is two lines at most.
 *  - «Главная» and «Дашборд» on a phone: the five numbers took 216 px of a 291 px row and left the name 37 px (0 px after the badge
 *    and the gap): rows up to 797 px, the dashboard 9855 px at 390 px. A row is two lines now (the name, then the five numbers under
 *    the header's labels), rows are 31 to 72 px and the dashboard 2624 px.
 *  - «Версия документа»: classification and runs sat side by side from 1280 px, and the runs' table (714 px of columns, 34 px of
 *    panel) scrolled inside a 490 px box (577 px at 1440, 708 px at 1680). The second column is 1.2fr of what the frame leaves, so
 *    it holds the table from 1691 px; the columns start at 1760 px, where the table has 752 px.
 *
 * The suite renders markup under `environment: 'node'` and cannot measure a width, so each cause is held as the declarations that
 * cured it, read from the right `@media` block. Every check runs first on a fixture that lacks the rule (so it can fail) and then
 * on the real module (so it reads this tree). The measurements are in the lane's evidence and in the debt register, not here.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { COMMENT, declares, declaresIn, mediaBlocks, withoutMedia } from './css-reads';

/** The `min-width` breakpoints (px) whose block gives the selector's grid more than one track. */
function columnBreakpoints(css: string, selector: string): readonly number[] {
  const found: number[] = [];
  for (const match of css.replace(COMMENT, '').matchAll(/@media \(min-width: (\d+)px\)/g)) {
    const px = Number(match[1]);
    if (mediaBlocks(css, `min-width: ${px}px`).some((block) => declares(block, selector, 'grid-template-columns', /^minmax\([^)]*\) minmax\([^)]*\)$/))) {
      found.push(px);
    }
  }
  return found;
}

const HOME = readFileSync(join(WEB_ROOT, 'src', '_pages', 'home', 'ui', 'home-page.module.css'), 'utf8');
const VERSION = readFileSync(join(WEB_ROOT, 'src', '_pages', 'version-detail', 'ui', 'version-detail-page.module.css'), 'utf8');
const SECTIONS = readFileSync(join(WEB_ROOT, 'src', 'widgets', 'dashboard', 'ui', 'sections-panel.module.css'), 'utf8');

const ONE_TRACK = /^minmax\(0, 1fr\)$/;
const HOME_TWO = /^minmax\(300px, 0\.85fr\) minmax\(0, 1\.15fr\)$/;
const VERSION_TWO = /^minmax\(0, 1fr\) minmax\(0, 1\.2fr\)$/;

describe('the readers of a stylesheet can fail (lane WALK-V4)', () => {
  const OLD_HOME =
    '.overviewGrid { display: grid; grid-template-columns: minmax(300px, 0.85fr) minmax(0, 1.15fr); }\n' +
    '@media (max-width: 1279px) { .overviewGrid { grid-template-columns: minmax(0, 1fr); } }';

  it('reads a base rule and a media rule apart', () => {
    expect(declares(withoutMedia(OLD_HOME), '.overviewGrid', 'grid-template-columns', ONE_TRACK)).toBe(false);
    expect(declares(withoutMedia(OLD_HOME), '.overviewGrid', 'grid-template-columns', HOME_TWO)).toBe(true);
    expect(declaresIn(OLD_HOME, 'max-width: 1279px', '.overviewGrid', 'grid-template-columns', ONE_TRACK)).toBe(true);
    expect(declaresIn(OLD_HOME, 'min-width: 1680px', '.overviewGrid', 'grid-template-columns', HOME_TWO)).toBe(false);
  });

  it('finds the breakpoint of a two-track grid, and none where the base rule has two tracks', () => {
    expect(columnBreakpoints(OLD_HOME, '.overviewGrid')).toEqual([]);
    expect(columnBreakpoints('.a { grid-template-columns: minmax(0, 1fr); }\n@media (min-width: 1680px) { .a { grid-template-columns: minmax(300px, 0.85fr) minmax(0, 1.15fr); } }', '.a')).toEqual([1680]);
  });
});

describe('«Главная»: the tasks and the section table share a row only where the table fits (lane WALK-V4)', () => {
  it('can fail: the old stylesheet, two tracks from the base rule, reads as wrong', () => {
    const old =
      '.overviewGrid { display: grid; grid-template-columns: minmax(300px, 0.85fr) minmax(0, 1.15fr); }\n' +
      '@media (max-width: 1279px) { .overviewGrid { grid-template-columns: minmax(0, 1fr); } }';
    expect(declares(withoutMedia(old), '.overviewGrid', 'grid-template-columns', ONE_TRACK)).toBe(false);
    expect(columnBreakpoints(old, '.overviewGrid')).toEqual([]);
  });

  it('is one column by default, and two only inside one min-width block', () => {
    expect(declares(withoutMedia(HOME), '.overviewGrid', 'grid-template-columns', ONE_TRACK)).toBe(true);
    expect(columnBreakpoints(HOME, '.overviewGrid')).toHaveLength(1);
  });

  it('starts the second column where the section table leaves its name 190 px (measured 190 px at 1680, 144 px at 1600)', () => {
    // The table's column is 0.575 of the page less 293 px; a row spends 556 px of it (the panel's 34, the row's 34, the five numbers
    // of 5.5rem with their gaps 456, the arrow 16 and two gaps 16), and the name sits 52 px inside its button (the badge and the gap).
    const column = (viewport: number): number => 0.575 * (viewport - 293);
    const name = (viewport: number): number => column(viewport) - 556 - 52;
    expect(Math.round(name(1680))).toBe(190);
    expect(Math.round(name(1280))).toBeLessThan(0);
    const [breakpoint] = columnBreakpoints(HOME, '.overviewGrid');
    expect(breakpoint).toBeDefined();
    expect(name(breakpoint ?? 0)).toBeGreaterThanOrEqual(189);
  });

  it('keeps the tiles at two columns below 1280 px, as before', () => {
    expect(declaresIn(HOME, 'max-width: 1279px', '.tiles', 'grid-template-columns', /^repeat\(2, minmax\(0, 1fr\)\)$/)).toBe(true);
    expect(declaresIn(HOME, 'max-width: 1279px', '.overviewGrid', 'grid-template-columns', ONE_TRACK)).toBe(false);
  });
});

describe('«Версия документа»: classification and runs share a row only where the runs\' table fits (lane WALK-V4)', () => {
  it('can fail: the old stylesheet, two tracks from 1280 px, reads as wrong', () => {
    const old =
      '.columns { display: grid; grid-template-columns: minmax(0, 1fr); }\n' +
      '@media (min-width: 1280px) { .columns { grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); } }';
    expect(columnBreakpoints(old, '.columns')).toEqual([1280]);
    expect(columnBreakpoints(old, '.columns')[0]).toBeLessThan(1691);
  });

  it('is one column by default, and two only inside one min-width block', () => {
    expect(declares(withoutMedia(VERSION), '.columns', 'grid-template-columns', ONE_TRACK)).toBe(true);
    expect(columnBreakpoints(VERSION, '.columns')).toHaveLength(1);
    const [breakpoint] = columnBreakpoints(VERSION, '.columns');
    expect(declaresIn(VERSION, `min-width: ${breakpoint}px`, '.columns', 'grid-template-columns', VERSION_TWO)).toBe(true);
  });

  it('starts the second column where it holds the runs\' table: 714 px of columns and 34 px of panel (measured)', () => {
    // The page is the viewport less the frame's 303 px; the columns share it less a 16 px gap, 1fr and 1.2fr.
    const secondColumn = (viewport: number): number => ((viewport - 303 - 16) * 1.2) / 2.2;
    const needed = 714 + 34;
    expect(Math.round(secondColumn(1680))).toBe(742); // measured 742: the table scrolled by 6 px
    expect(Math.round(secondColumn(1280))).toBe(524); // measured 524
    const [breakpoint] = columnBreakpoints(VERSION, '.columns');
    expect(breakpoint).toBeDefined();
    expect(secondColumn(breakpoint ?? 0)).toBeGreaterThanOrEqual(needed);
    expect(Math.round(secondColumn(1760))).toBe(786); // measured: the table's box was 752 px
  });
});

describe('«Главная» and «Дашборд» on a phone and a tablet: a section row is two lines (lane WALK-V4; the breakpoint moved from 600 to 1100 px by lane WALK-V5)', () => {
  const PHONE = 'max-width: 1100px';
  const OLD =
    '@media (max-width: 1100px) { .row { grid-template-columns: minmax(0, 1fr) auto 12px; } .header { grid-template-columns: minmax(0, 1fr) auto 12px; } }\n' +
    '@media (max-width: 1100px) { .metrics { grid-template-columns: repeat(5, 2.5rem); } }';

  it('can fail: the old stylesheet, one line with the numbers on 216 px, reads as wrong', () => {
    expect(declaresIn(OLD, PHONE, '.row > .metrics', 'grid-column', /^1 \/ -1$/)).toBe(false);
    expect(declaresIn(OLD, PHONE, '.row', 'grid-template-columns', /^minmax\(0, 1fr\) var\(--am-target-min\)$/)).toBe(false);
    expect(declaresIn(OLD, PHONE, '.metrics', 'grid-template-columns', /^repeat\(5, minmax\(0, 1fr\)\)$/)).toBe(false);
  });

  it('puts the name and the arrow on the first line and the five numbers on the second, across the whole row', () => {
    expect(declaresIn(SECTIONS, PHONE, '.row', 'grid-template-columns', /^minmax\(0, 1fr\) var\(--am-target-min\)$/)).toBe(true);
    for (const selector of ['.row > .rowButton', '.row > .totalLabel']) {
      expect(declaresIn(SECTIONS, PHONE, selector, 'grid-column', /^1$/), selector).toBe(true);
      expect(declaresIn(SECTIONS, PHONE, selector, 'grid-row', /^1$/), selector).toBe(true);
    }
    expect(declaresIn(SECTIONS, PHONE, '.row > .arrow', 'grid-column', /^2$/)).toBe(true);
    expect(declaresIn(SECTIONS, PHONE, '.row > .arrow', 'grid-row', /^1$/)).toBe(true);
    expect(declaresIn(SECTIONS, PHONE, '.row > .metrics', 'grid-column', /^1 \/ -1$/)).toBe(true);
    expect(declaresIn(SECTIONS, PHONE, '.row > .metrics', 'grid-row', /^2$/)).toBe(true);
  });

  it('gives the five numbers five equal tracks, in the rows and under the header, not 2.5rem each', () => {
    expect(declaresIn(SECTIONS, PHONE, '.metrics', 'grid-template-columns', /^repeat\(5, minmax\(0, 1fr\)\)$/)).toBe(true);
    expect(declaresIn(SECTIONS, PHONE, '.metrics', 'grid-template-columns', /2\.5rem/)).toBe(false);
    // The wide layout keeps its own tracks.
    expect(declares(withoutMedia(SECTIONS), '.metrics', 'grid-template-columns', /^repeat\(5, 5\.5rem\)$/)).toBe(true);
  });

  it('keeps the header\'s labels over the numbers: one track, no «Раздел» cell, no empty arrow cell', () => {
    expect(declaresIn(SECTIONS, PHONE, '.header', 'grid-template-columns', ONE_TRACK)).toBe(true);
    expect(declaresIn(SECTIONS, PHONE, '.header > :first-child', 'display', /^none$/)).toBe(true);
    expect(declaresIn(SECTIONS, PHONE, '.header::after', 'display', /^none$/)).toBe(true);
  });
});
