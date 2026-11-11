/**
 * What the shared stylesheets must keep so that a screen holds at 390 px (lane P7, 2026-11-08).
 *
 * The suite renders markup under `environment: 'node'`, so it cannot measure a width. The measurement was made once, with a
 * headless browser over the census screens (390, 768 and 1280 px, both themes), and what it found in the SHARED layer is
 * written down here as declarations a later edit cannot drop without a red test: the page header wraps instead of squeezing
 * its title, a dump scrolls inside its own box, a field never outgrows its column, and a notice strip wraps its buttons
 * under its text. Each check is a pure function over a stylesheet's text, exercised on a fixture that lacks the rule
 * (what proves it can fail) and on the real file (what proves it reads this tree).
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { Table } from '@/shared/ui';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from './contrast';

const GLOBALS = join(WEB_ROOT, 'src', 'app', 'globals.css');
const NOTICES = join(WEB_ROOT, 'src', '_app', 'release-notices.module.css');
const FRAME = join(WEB_ROOT, 'src', '_app', 'app-frame.module.css');

/** Whether any rule whose selector list contains `selector` declares `property` with a value matching `value`. */
export function declares(css: string, selector: string, property: string, value: RegExp): boolean {
  return parseRules(css, 'test').some(
    (rule) =>
      rule.selector.split(',').some((part) => part.trim() === selector) && value.test(rule.declarations.get(property) ?? ''),
  );
}

const globals = readFileSync(GLOBALS, 'utf8');

describe('the shared stylesheets keep a screen inside 390 px', () => {
  it('can fail: reads a declaration only where a rule for that selector makes it', () => {
    const css = '.a { display: flex; }\n.b, .c { flex-wrap: wrap; }\n@media (max-width: 590px) { .d { min-width: 0; } }';
    expect(declares(css, '.b', 'flex-wrap', /wrap/)).toBe(true);
    expect(declares(css, '.c', 'flex-wrap', /wrap/)).toBe(true);
    expect(declares(css, '.d', 'min-width', /^0$/)).toBe(true);
    expect(declares(css, '.a', 'flex-wrap', /wrap/)).toBe(false);
    expect(declares(css, '.b', 'flex-wrap', /nowrap/)).toBe(false);
    expect(declares(css, '.missing', 'flex-wrap', /wrap/)).toBe(false);
  });

  it('wraps the page header and lets its heading shrink below its content', () => {
    expect(declares(globals, '.am-page__header', 'flex-wrap', /^wrap$/)).toBe(true);
    expect(declares(globals, '.am-page__header > :first-child', 'min-width', /^0$/)).toBe(true);
    expect(declares(globals, '.am-page__title', 'overflow-wrap', /anywhere/)).toBe(true);
  });

  it('caps the page actions at the header\'s width so their links wrap inside them', () => {
    expect(declares(globals, '.am-page__actions', 'max-width', /^100%$/)).toBe(true);
  });

  it('gives a form one track that may shrink, so a long select option cannot widen the screen', () => {
    expect(declares(globals, '.am-form', 'grid-template-columns', /^minmax\(0, 1fr\)$/)).toBe(true);
    expect(declares(globals, '.am-form__field', 'min-width', /^0$/)).toBe(true);
  });

  it('lets a field shrink inside a grid track or a flex row, which `max-width` alone does not', () => {
    for (const control of ['select', 'textarea', "input[type='text']"]) {
      expect(declares(globals, control, 'min-width', /^0$/)).toBe(true);
    }
    expect(declares(globals, '.am-form__field', 'grid-template-columns', /^minmax\(0, 1fr\)$/)).toBe(true);
  });

  it('makes a table the containing block of the hidden labels it holds, so a scroller clips them', () => {
    expect(declares(globals, 'table', 'position', /^relative$/)).toBe(true);
  });

  it('gives the frame\'s navigation column one track that may shrink', () => {
    const frame = readFileSync(FRAME, 'utf8');
    expect(declares(frame, '.row', 'grid-template-columns', /^minmax\(0, 1fr\)$/)).toBe(true);
  });

  it('never lets a badge outgrow its column, and wraps a long one at a phone width', () => {
    expect(declares(globals, '.am-badge', 'max-width', /^100%$/)).toBe(true);
    const phone = [...globals.matchAll(/@media \(max-width: 590px\) \{([\s\S]*?)\n\}/g)].map((block) => block[1]).join('\n');
    expect(declares(phone, '.am-badge', 'white-space', /^normal$/)).toBe(true);
    // The override must come after the rule it overrides, or the equal-specificity `nowrap` above wins.
    expect(globals.indexOf('white-space: normal;\n    overflow-wrap: anywhere;')).toBeGreaterThan(globals.indexOf('\n.am-badge {'));
  });

  it('keeps the handles of a disclosure, and a badge that is pressed, at 24 px', () => {
    expect(declares(globals, 'summary', 'min-height', /^24px$/)).toBe(true);
    expect(declares(globals, 'a.am-badge', 'min-height', /^24px$/)).toBe(true);
    expect(declares(globals, 'button.am-badge', 'min-height', /^24px$/)).toBe(true);
    const frame = readFileSync(FRAME, 'utf8');
    expect(declares(frame, '.row :global(.am-disclosure__button)', 'min-height', /^24px$/)).toBe(true);
  });

  it('hangs the stacked «Меню» panel from the bar, as wide as the screen less a gutter', () => {
    const frame = readFileSync(FRAME, 'utf8');
    expect(declares(frame, '.stacked > :global(.am-disclosure)', 'position', /^static$/)).toBe(true);
    const panel = '.stacked > :global(.am-disclosure) > :global(.am-disclosure__panel)';
    expect(declares(frame, panel, 'left', /var\(--am-gap-sm\)/)).toBe(true);
    expect(declares(frame, panel, 'right', /var\(--am-gap-sm\)/)).toBe(true);
    expect(declares(frame, panel, 'max-width', /^none$/)).toBe(true);
    expect(declares(frame, panel, 'overflow-y', /^auto$/)).toBe(true);
  });

  it('lets Tab reach a table that scrolls inside its column, and names the region', () => {
    const table = (caption?: string) =>
      renderToStaticMarkup(
        createElement(Table<{ readonly id: string }>, {
          ...(caption === undefined ? {} : { caption }),
          columns: [{ key: 'id', header: 'Код', cell: (row) => row.id }],
          rows: [{ id: 'a' }],
          rowKey: (row) => row.id,
        }),
      );
    expect(table('Строки')).toMatch(/<div class="[^"]*" role="region" aria-label="Строки" tabindex="0">/);
    expect(table()).toMatch(/role="region" aria-label="Таблица" tabindex="0"/);
    const module = readFileSync(join(WEB_ROOT, 'src', 'shared', 'ui', 'table.module.css'), 'utf8');
    expect(declares(module, '.scroll:focus-visible', 'outline', /var\(--am-accent\)/)).toBe(true);
  });

  it('keeps a dump inside its own box, scrolling it rather than the page', () => {
    expect(declares(globals, 'pre', 'overflow-x', /^auto$/)).toBe(true);
    expect(declares(globals, 'pre', 'max-width', /^100%$/)).toBe(true);
  });

  it('never lets a field outgrow its column', () => {
    expect(declares(globals, 'select', 'max-width', /^100%$/)).toBe(true);
    expect(declares(globals, 'textarea', 'max-width', /^100%$/)).toBe(true);
  });

  it('breaks a quotation that has a word longer than the column', () => {
    expect(declares(globals, '.am-quotation__text', 'overflow-wrap', /anywhere/)).toBe(true);
  });

  it('wraps the release notice strip so its buttons drop under its text', () => {
    const notices = readFileSync(NOTICES, 'utf8');
    expect(declares(notices, '.notice', 'flex-wrap', /^wrap$/)).toBe(true);
    expect(declares(notices, '.text', 'min-width', /^0$/)).toBe(true);
  });

  it('keeps «Что нового» on one line at a desktop width: the name never shrinks, the disclosure has a fixed basis', () => {
    const notices = readFileSync(NOTICES, 'utf8');
    expect(declares(notices, '.title', 'flex', /^0 0 auto$/)).toBe(true);
    expect(declares(notices, '.title', 'white-space', /^nowrap$/)).toBe(true);
    expect(declares(notices, '.details', 'flex', /^1 1 auto$/)).toBe(false);
    expect(declares(notices, '.details', 'flex', /^1 1 \d+(\.\d+)?rem$/)).toBe(true);
    expect(declares(notices, '.first', 'flex', /^1 1 \d+(\.\d+)?rem$/)).toBe(true);
    expect(declares(notices, '.summary', 'flex-wrap', /^wrap$/)).toBe(true);
  });

  it('clears the pinned furniture when focus or a fragment scrolls a control into view', () => {
    expect(declares(globals, 'html', 'scroll-padding-top', /var\(--am-strip-height\)/)).toBe(true);
  });

  it('narrows the frame\'s side gutters at a phone width and keeps the frame bar wrapping', () => {
    const phone = /@media \(max-width: 590px\) \{([\s\S]*?)\n\}/.exec(globals)?.[1] ?? '';
    expect(declares(phone, '.am-app__main', 'padding', /var\(--am-gap-md\)/)).toBe(true);
    expect(declares(phone, '.am-app__utility', 'flex-wrap', /^wrap$/)).toBe(true);
    expect(declares(globals, '.am-app__bar', 'flex-wrap', /^wrap$/)).toBe(true);
  });

  it('keeps the frame module on the spacing tokens it already read', () => {
    const frame = readFileSync(FRAME, 'utf8');
    expect(declares(frame, '.stackedList', 'gap', /var\(--am-gap-2xs\)/)).toBe(true);
    expect(declares(frame, '.end', 'gap', /var\(--am-gap-sm\)/)).toBe(true);
  });
});
