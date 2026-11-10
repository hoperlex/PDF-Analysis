/**
 * `NAV-01b`: every row of the side menu fits its column (owner measurement on 0.20.3, 1280 px, a section page, «Разделы» open:
 * `nav.app-frame_nav` scrollWidth 177 > clientWidth 172).
 *
 * **Why 172.** The bar is 200 px, less 2 px of border and 16 of padding: the nav box is 182 px. With the «Разделы» group open
 * (`R-153g`: all fifteen sections) the list is taller than the bar, the nav scrolls, and its thin scrollbar takes 10 px: the
 * rows have 172 px, not 182. Before `R-153g` the list was short and the scrollbar never came, which is why only this state showed it.
 *
 * **What was 177 wide.** Not a section row: that row draws the mark and the counters (its name is the link's `aria-label` and
 * `title`), a few dozen pixels. It is the group button of «Администрирование» (an admin session): 17 capitals at 11.5 px / 650 with
 * 0.11em tracking are 159.6 px, and with the 6 px gap and the chevron the button's content is 8 + 159.6 + 6 + 6.1 = 179.7 px. That fits
 * 182 and not 172. (The earlier 188-in-182 clip, `6dc5373f6`, was this same button, in an `auto` grid track.)
 *
 * A static render cannot lay anything out, so what is held here is the CSS that makes the rows fit and the budget that shows it
 * does: the declarations are read from the module itself, the label's width is the measured one, and every guard has a case
 * that fails on the rules as they were. What only a browser proves is listed in the lane's handoff.
 *
 * - the group label's width budget at the narrowest column (a figure measured from the font, below);
 * - the label may wrap as a last resort instead of overflowing, and the chevron never shrinks;
 * - the section row's text truncates with an ellipsis, its counters never wrap or shrink;
 * - the compact rail's nav (44 px, links of 40) takes no scrollbar from its width.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { FrameNavigationView } from '@/_app/frame-navigation';
import { MENU_GROUP_LABELS, buildNavigation } from '@/_app/navigation';
import { sectionNavigationOf } from '@/_app/section-navigation';
import styles from '@/_app/app-frame.module.css';
import { PROJECT_SECTIONS } from '@/entities/project';
import { routes } from '@/shared/lib';

import { parseRules } from '../styles/contrast';
import { ADMIN_AND_EXPERT } from './subjects';

const read = (relative: string): string => readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf8');
const FRAME_CSS = read('../../../src/_app/app-frame.module.css');
const GLOBALS = read('../../../src/app/globals.css');

/** The declarations of every rule with exactly this selector, merged in source order (a later one wins). */
function rule(css: string, selector: string): Map<string, string> {
  const merged = new Map<string, string>();
  for (const found of parseRules(css, 'module')) {
    if (found.selector.replace(/\s+/g, ' ') !== selector) continue;
    for (const [property, value] of found.declarations) merged.set(property, value.replace(/\s+/g, ' '));
  }
  return merged;
}

/** A token of the global `:root` block, in px (`--am-gap-xs: 4px`) or as a bare number of em (`--am-tracking-caps: 0.07em`). */
function token(name: string): number {
  const match = new RegExp(`${name}:\\s*([\\d.]+)(?:px|em)\\s*;`).exec(GLOBALS);
  if (match === null) throw new Error(`${name} is not a px/em token of globals.css`);
  return Number(match[1]);
}

/** A px length as the module spells it: a gap token or a plain `Npx`. */
function px(value: string): number {
  const gap = /^var\((--am-gap-[a-z0-9]+)\)$/.exec(value);
  if (gap !== null) return token(gap[1] as string);
  const plain = /^([\d.]+)px$/.exec(value);
  if (plain !== null) return Number(plain[1]);
  throw new Error(`not a length this test can read: ${value}`);
}

/** A tracking, in em: `var(--am-tracking-caps)`, that times a factor, or a plain `Nem`. */
function trackingEm(value: string | undefined): number {
  if (value === undefined) return 0;
  if (value === 'var(--am-tracking-caps)') return token('--am-tracking-caps');
  const scaled = /^calc\(var\(--am-tracking-caps\) \* ([\d.]+)\)$/.exec(value);
  if (scaled !== null) return token('--am-tracking-caps') * Number(scaled[1]);
  const plain = /^([\d.]+)em$/.exec(value);
  if (plain !== null) return Number(plain[1]);
  throw new Error(`not a tracking this test can read: ${value}`);
}

const GROUP_BUTTON = '.row :global(.am-disclosure__button)';
const GROUP_CHEVRON = '.row :global(.am-disclosure__button)::after';
const COMPACT_NAV = ":global(.am-app[data-sidebar='compact']) .nav";

/**
 * What a row needs to fit, as a list of what is missing: empty when the module holds all of it. Pure over the module's text, so the
 * cases below run it on the rules as they were before `NAV-01b` and show it names what was wrong.
 */
export function fitProblems(css: string): string[] {
  const problems: string[] = [];
  const need = (ok: boolean, what: string): void => {
    if (!ok) problems.push(what);
  };

  const button = rule(css, GROUP_BUTTON);
  need(button.get('overflow-wrap') === 'anywhere', 'a group label can wrap when it cannot fit (overflow-wrap: anywhere on the button)');
  need(
    rule(css, GROUP_CHEVRON).get('flex') === '0 0 auto',
    'the chevron keeps its size when the label shrinks (flex: 0 0 auto on the button\'s ::after)',
  );

  const mark = rule(css, '.sectionMark');
  need(mark.get('min-width') === '0', 'the section mark may shrink (min-width: 0)');
  need(mark.get('overflow') === 'hidden', 'the section mark clips at its own box (overflow: hidden)');
  need(mark.get('text-overflow') === 'ellipsis', 'the section mark ends in an ellipsis, not a cut (text-overflow: ellipsis)');
  need(mark.get('white-space') === 'nowrap', 'the section mark stays on one line (white-space: nowrap)');

  for (const selector of ['.sectionCount', '.itemBadges', '.badge']) {
    need(rule(css, selector).get('white-space') === 'nowrap', `${selector} never wraps (white-space: nowrap)`);
  }
  for (const selector of ['.sectionCount', '.itemBadges']) {
    need(rule(css, selector).get('flex') === '0 0 auto', `${selector} never shrinks (flex: 0 0 auto)`);
  }

  need(rule(css, COMPACT_NAV).get('scrollbar-width') === 'none', 'the compact rail\'s nav takes no scrollbar from its 44 px (scrollbar-width: none)');
  const media = css.indexOf('@media (min-width: 1024px)');
  const after = css.indexOf('@media (max-width: 1023.98px)');
  const at = css.indexOf(`${COMPACT_NAV} {`);
  need(media >= 0 && at > media && (after < 0 || at < after), 'the compact rail rule is in the desktop block, where the rail exists');
  return problems;
}

describe('NAV-01b: the rows of the side menu fit the column', () => {
  it('holds every rule the fit relies on', () => {
    expect(fitProblems(FRAME_CSS)).toEqual([]);
  });

  it('can fail: names each missing rule on the module as it was before the fix', () => {
    const before = [
      '.row :global(.am-disclosure__button) { display: flex; letter-spacing: 0.11em; }',
      '.sectionMark { flex: 1 1 auto; min-width: 0; font-weight: 650; }',
      '.sectionCount { flex: 0 0 auto; min-width: 2ch; }',
      '.itemBadges { display: inline-flex; flex: 0 0 auto; }',
      '.badge { min-width: 2ch; }',
      '@media (min-width: 1024px) {',
      "  :global(.am-app[data-sidebar='compact']) .row { display: none; }",
      '}',
      '@media (max-width: 1023.98px) { .row { display: none; } }',
    ].join('\n');
    expect(fitProblems(before)).toEqual([
      'a group label can wrap when it cannot fit (overflow-wrap: anywhere on the button)',
      "the chevron keeps its size when the label shrinks (flex: 0 0 auto on the button's ::after)",
      'the section mark clips at its own box (overflow: hidden)',
      'the section mark ends in an ellipsis, not a cut (text-overflow: ellipsis)',
      'the section mark stays on one line (white-space: nowrap)',
      '.sectionCount never wraps (white-space: nowrap)',
      '.itemBadges never wraps (white-space: nowrap)',
      '.badge never wraps (white-space: nowrap)',
      "the compact rail's nav takes no scrollbar from its 44 px (scrollbar-width: none)",
      'the compact rail rule is in the desktop block, where the rail exists',
    ]);
  });

  it('can fail: a compact-rail rule outside the desktop block is refused', () => {
    const outside = `${COMPACT_NAV} { scrollbar-width: none; }\n@media (min-width: 1024px) { .x { color: red; } }`;
    expect(fitProblems(outside)).toContain('the compact rail rule is in the desktop block, where the rail exists');
  });

  describe('the widest group label, in the narrowest column', () => {
    /**
     * «Администрирование», 17 capitals, set in `UbuntuSans-variable.ttf` at wght 650 and 11.5 px with no tracking: 138.1 px.
     * Measured with Pillow 12.2 on the Raqm (HarfBuzz) layout engine, the variation axes set, kerning on; the unkerned sum of the
     * advance widths read from `hmtx` is 137.8. Linux Chrome rounds advances, so a browser may differ by a pixel or two; the budget
     * keeps {@link SLACK} for that. Re-measure when a group is renamed (the next case fails then) or the font file changes.
     */
    const LABEL_PX = 138.1;
    const LETTERS = 17;
    const FONT_PX = 11.5;
    /** The chevron: `0.4em` wide and a 1.5 px border on its right (`globals.css`, `.am-disclosure__button::after`). */
    const CHEVRON_PX = 0.4 * FONT_PX + 1.5;
    /** The nav box is 182 px (the bar's 200, its border and padding); a 10 px thin scrollbar leaves 172 (measured, owner, 0.20.3). */
    const NARROWEST_COLUMN_PX = 172;
    /** What the browser's own rounding may take. */
    const SLACK = 4;

    it('is still «Администрирование», 17 letters: a longer name needs a new measurement', () => {
      const longest = Object.values(MENU_GROUP_LABELS).reduce((a, b) => (b.length > a.length ? b : a));
      expect(longest).toBe('Администрирование');
      expect(longest).toHaveLength(LETTERS);
    });

    /** What the widest label's button needs, in px, from the module's own gap, padding and tracking. */
    function need(css: string): number {
      const button = rule(css, GROUP_BUTTON);
      const padding = (button.get('padding') ?? '').split(' ').map(px);
      if (padding.length !== 4) throw new Error(`padding is four lengths: ${button.get('padding')}`);
      const [, right = 0, , left = 0] = padding;
      return LABEL_PX + LETTERS * trackingEm(button.get('letter-spacing')) * FONT_PX + px(button.get('gap') ?? '0px') + CHEVRON_PX + left + right;
    }

    it('fits with room to spare, label, gap, chevron and padding together', () => {
      expect(need(FRAME_CSS)).toBeLessThanOrEqual(NARROWEST_COLUMN_PX - SLACK);
    });

    it('can fail: the tracking, gap and padding the button had need 187.7 px of 172, the width the earlier clip measured as 188', () => {
      // `letter-spacing: 0.11em`, the 6 px gap `globals.css` gives a button, and 8 px on both sides.
      const was = FRAME_CSS
        .replace('letter-spacing: calc(var(--am-tracking-caps) * 0.5);', 'letter-spacing: 0.11em;')
        .replace('  gap: var(--am-gap-xs);\n  /* 11.5 px type', '  gap: 6px;\n  /* 11.5 px type')
        .replace('padding: var(--am-gap-xs) var(--am-gap-xs) var(--am-gap-xs) var(--am-gap-sm);', 'padding: var(--am-gap-xs) var(--am-gap-sm) var(--am-gap-xs) var(--am-gap-sm);');
      expect(was, 'the mutation changed nothing').not.toBe(FRAME_CSS);
      expect(need(was)).toBeCloseTo(187.7, 1);
      expect(need(was)).toBeGreaterThan(NARROWEST_COLUMN_PX - SLACK);
      // The old tracking alone is enough to overflow the 172 px column, with the new gap and padding.
      const trackingOnly = FRAME_CSS.replace('letter-spacing: calc(var(--am-tracking-caps) * 0.5);', 'letter-spacing: 0.11em;');
      expect(trackingOnly).not.toBe(FRAME_CSS);
      expect(need(trackingOnly)).toBeGreaterThan(NARROWEST_COLUMN_PX - SLACK);
    });
  });

  describe('the markup the rules are written for', () => {
    const sections = sectionNavigationOf(
      PROJECT_SECTIONS.map((section) => ({ section: section.code, document_count: 3, audit_counts: { awaiting_decision: 12 } })) as never,
      'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
      null,
    );
    const markup = renderToStaticMarkup(
      createElement(FrameNavigationView, {
        navigation: buildNavigation(ADMIN_AND_EXPERT),
        pathname: routes.project('prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B'),
        projectUid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
        sections,
      }),
    );
    const bar = markup.slice(markup.indexOf('data-nav-state="row"'), markup.indexOf('data-nav-state="rail"'));

    it('draws a section row as the mark and the counters, in the classes the fit rules name', () => {
      expect(styles.sectionMark, 'the module no longer exports sectionMark').toBeTruthy();
      const item = /<li class="am-disclosure__item" data-section-nav-item="AR">(.*?)<\/li>/s.exec(bar)?.[1] ?? '';
      expect(item).toContain(`<span class="${styles.sectionMark}">АР</span>`);
      expect(item).toMatch(new RegExp(`<span class="${styles.itemBadges}">.*<span class="${styles.sectionCount}">3</span></span></a>`));
      expect(item).toMatch(/title="[^"]+"/);
      expect(item).toMatch(/aria-label="АР [^"]+, документов: 3/);
    });

    it('draws the widest group button an admin session has, with the label as the button\'s own text', () => {
      expect(bar).toMatch(/<button\b[^>]*>Администрирование<\/button>/);
    });
  });
});
