/**
 * Faults of 0.20.6 that the browser walk of lane WALK-V5 found at the widths nobody had walked (360, 414, 768, 1024, 1366, 1440 px,
 * and 1680 and 1920 for the two screens that change at 1680 and 1760), on a throwaway stand of a built `next start`, with the width
 * assertion's new reading of a collapsed column (`tests/e2e/pc01/journey/width.mjs`, `D-565`): a visible text box of 10 characters or
 * more, under 90 px wide and over 70 px tall.
 *
 * One cause behind most of them: a table cell says `overflow-wrap: anywhere`, which lets its minimum width fall to one character, so a
 * table at `width: 100%` squeezes its columns instead of letting its frame scroll, and the squeezed ones are the ones with words in
 * them. Each fault is held here as the declarations that cured it (the suite renders markup in `node` and cannot measure a width);
 * every check runs first on a fixture that lacks the rule, so it can fail, and then on the real module, so it reads this tree. The
 * measurements are in the lane's evidence and in the debt register, not here.
 *
 *  - «База знаний», the table: every column has a floor (the type cell was 53 x 202 px at 1280, 41 x 731 at 360); and the filters wrap
 *    (the type filter is 390 px of buttons; the page scrolled sideways by 30 px at 360).
 *  - «Сравнение версий», the table of sets: the «Версии» cell is the count over the date, on two lines (it read «12026-11-09»).
 *  - «Настройки анализа», «Сравнение этапов» (the stage names): the first columns keep the width of their words.
 *  - «Пользователи», «Журнал событий входа», «Диспетчер», «Журнал» and the run's journal on a phone: a table keeps the width of its
 *    columns and its frame scrolls.
 *  - «Дашборд» and «Главная»: a section row is two lines up to 1100 px, not 600 (at 768 px the name had 87 px; `narrow-walk-v4`).
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { declares, declaresIn, withoutMedia } from './css-reads';

const source = (...parts: readonly string[]): string => readFileSync(join(WEB_ROOT, 'src', ...parts), 'utf8');

/** A `min-width` of `rem` units, as a number, or `null` when the selector declares none. */
function minRem(css: string, selector: string, media: string | null = null): number | null {
  for (let rem = 1; rem <= 80; rem += 0.5) {
    const value = new RegExp(`^${rem}rem$`);
    const found = media === null ? declares(withoutMedia(css), selector, 'min-width', value) : declaresIn(css, media, selector, 'min-width', value);
    if (found) return rem;
  }
  return null;
}

describe('the readers can fail (lane WALK-V5)', () => {
  const NONE = '.cell { overflow-wrap: anywhere; }\n.table { width: 100%; }';
  it('read nothing from a stylesheet without a floor, and a floor from one with it', () => {
    expect(minRem(NONE, '.cell')).toBeNull();
    expect(minRem('.cell { min-width: 7rem; }', '.cell')).toBe(7);
    expect(minRem('@media (max-width: 600px) { .table { min-width: 36rem; } }', '.table')).toBeNull();
    expect(minRem('@media (max-width: 600px) { .table { min-width: 36rem; } }', '.table', 'max-width: 600px')).toBe(36);
  });
});

describe('«База знаний»: the table has a floor for each column and the filters wrap (lane WALK-V5)', () => {
  const TABLE = source('widgets', 'knowledge-base', 'ui', 'knowledge-base.module.css');
  const PAGE = source('_pages', 'knowledge-base', 'ui', 'knowledge-base-page.module.css');
  const COLUMNS = ['.colType', '.colPlace', '.colSection', '.colSeverity', '.colVerdict', '.colText', '.colReason', '.colDate', '.colLink'] as const;

  it('can fail: the old stylesheet, `anywhere` cells and no floor, reads as wrong', () => {
    const OLD = '.table { width: 100%; }\n.table td { overflow-wrap: anywhere; }';
    for (const column of COLUMNS) expect(minRem(OLD, column), column).toBeNull();
    expect(declares('.filters :global(.am-kb__filter) { flex-direction: row; }', '.filters :global(.am-kb__filter)', 'flex-wrap', /^wrap$/)).toBe(false);
  });

  it('gives every column a floor, 3.5 rem at least and 6 rem to the ones that hold words (three lines at the most for a stamp)', () => {
    for (const column of COLUMNS) expect(minRem(TABLE, column), column).not.toBeNull();
    for (const column of ['.colType', '.colPlace', '.colVerdict', '.colText', '.colReason', '.colDate', '.colLink'] as const) {
      expect(minRem(TABLE, column) ?? 0, column).toBeGreaterThanOrEqual(6);
    }
  });

  it('reads every floor from a class the table\'s header cells carry', () => {
    const markup = source('widgets', 'knowledge-base', 'ui', 'knowledge-base-table.tsx');
    for (const column of COLUMNS) expect(markup, column).toContain(`styles.${column.slice(1)}`);
  });

  it('lets a filter that does not fit break onto its next line', () => {
    expect(declares(PAGE, '.filters :global(.am-kb__filter)', 'flex-wrap', /^wrap$/)).toBe(true);
    expect(declares(PAGE, '.filters :global(.am-kb__filter)', 'min-width', /^0$/)).toBe(true);
    expect(declares(PAGE, '.filters :global(.am-kb__filter)', 'max-width', /^100%$/)).toBe(true);
  });
});

describe('«Сравнение версий»: the «Версии» cell is the count over the date (lane WALK-V5)', () => {
  const SERIES = source('widgets', 'version-series', 'ui', 'version-series.module.css');

  it('can fail: the old stylesheet, inline spans in an unfloored cell, reads as wrong', () => {
    const OLD = '.note { color: var(--am-ink-muted); overflow-wrap: anywhere; }';
    expect(minRem(OLD, '.versionsCell')).toBeNull();
    expect(declares(OLD, '.versionsCell .note', 'display', /^block$/)).toBe(false);
  });

  it('puts the date on its own line, on one line, in a column the width of a date', () => {
    expect(minRem(SERIES, '.versionsCell') ?? 0).toBeGreaterThanOrEqual(6.5);
    expect(declares(SERIES, '.versionsCell .note', 'display', /^block$/)).toBe(true);
    expect(declares(SERIES, '.versionsCell .note', 'white-space', /^nowrap$/)).toBe(true);
    expect(source('widgets', 'version-series', 'ui', 'projects-and-stages.tsx')).toContain('<td className={styles.versionsCell}>');
  });
});

describe('«Настройки анализа» and the stage names of «Сравнение»: the first columns keep the width of their words (lane WALK-V5)', () => {
  const PROFILE = source('widgets', 'analysis-profile-table', 'ui', 'analysis-profile-table.module.css');
  const STAGES = source('widgets', 'stage-comparison', 'ui', 'stage-comparison.module.css');

  it('can fail: the old stylesheets, no floor, read as wrong', () => {
    expect(minRem('.section span { font-weight: normal; }', '.section')).toBeNull();
    expect(minRem('.stageName { font-weight: 500; }', '.stageName')).toBeNull();
  });

  it('gives the section 8 rem and the version a line of its own, and the stage name 8 rem as a box', () => {
    expect(minRem(PROFILE, '.section')).toBe(8);
    expect(declares(PROFILE, '.version', 'white-space', /^nowrap$/)).toBe(true);
    expect(minRem(STAGES, '.stageName')).toBe(8);
    expect(declares(STAGES, '.stageName', 'display', /^inline-block$/)).toBe(true);
  });
});

describe('a table on a phone keeps the width of its columns and its frame scrolls (lane WALK-V5)', () => {
  const PHONE = 'max-width: 600px';
  const USERS = source('widgets', 'user-list', 'ui', 'user-list.module.css');
  const EVENTS = source('widgets', 'auth-event-list', 'ui', 'auth-event-list.module.css');
  const BOARD = source('widgets', 'assignment-board', 'ui', 'assignment-board.module.css');
  const JOURNAL = source('widgets', 'execution-journal', 'ui', 'execution-journal.module.css');

  it('can fail: the old stylesheets, a table at the frame\'s width, read as wrong', () => {
    expect(minRem('.table { width: 100%; table-layout: fixed; }', '.table', PHONE)).toBeNull();
    expect(declaresIn('.identity code { white-space: normal; }', PHONE, '.identity code', 'white-space', /^nowrap$/)).toBe(false);
  });

  it('holds the tables at 36 rem (the two fixed-layout lists) and 40 rem (the board)', () => {
    expect(minRem(USERS, '.table', PHONE)).toBe(36);
    expect(minRem(EVENTS, '.table', PHONE)).toBe(36);
    expect(minRem(BOARD, '.table', PHONE)).toBe(40);
  });

  it('lets the instant of an event break at its spaces on a phone, as the wide layout does not', () => {
    expect(declares(withoutMedia(EVENTS), '.when', 'white-space', /^nowrap$/)).toBe(true);
    expect(declaresIn(EVENTS, PHONE, '.when', 'white-space', /^normal$/)).toBe(true);
  });

  it('keeps the identity of a run on one line on a phone, and leaves the wide layout alone', () => {
    expect(declaresIn(JOURNAL, PHONE, '.identity code', 'white-space', /^nowrap$/)).toBe(true);
    expect(declares(withoutMedia(JOURNAL), '.identity code', 'white-space', /^normal$/)).toBe(true);
  });
});

describe('«Дашборд» and «Главная»: the two-line row holds up to 1100 px (lane WALK-V5)', () => {
  const SECTIONS = source('widgets', 'dashboard', 'ui', 'sections-panel.module.css');

  it('can fail: the old stylesheet, the phone block at 600 px, reads as wrong at 768 px', () => {
    const OLD = '@media (max-width: 600px) { .row > .metrics { grid-column: 1 / -1; } }';
    expect(declaresIn(OLD, 'max-width: 1100px', '.row > .metrics', 'grid-column', /^1 \/ -1$/)).toBe(false);
  });

  it('puts the five numbers under the name from the tablet down, and keeps the one-line row above 1100 px', () => {
    expect(declaresIn(SECTIONS, 'max-width: 1100px', '.row > .metrics', 'grid-column', /^1 \/ -1$/)).toBe(true);
    expect(declaresIn(SECTIONS, 'max-width: 600px', '.row > .metrics', 'grid-column', /^1 \/ -1$/)).toBe(false);
    expect(declares(withoutMedia(SECTIONS), '.row', 'grid-template-columns', /^minmax\(0, 1fr\) auto 16px$/)).toBe(true);
  });
});
