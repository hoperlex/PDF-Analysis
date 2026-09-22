/**
 * The icon set keeps its convention, and the notice keeps up with the set.
 *
 * Two different claims, one file, and they are different on purpose.
 *
 * **The convention.** Every icon inherits its colour through `currentColor` and writes no
 * colour of its own. That is what lets one icon read correctly on a button, in a badge and
 * in an error panel, and what keeps the set alive through a theme change. A single
 * `fill="#333"` pasted in from somewhere breaks it silently -- the icon looks right on the
 * light theme the author is looking at -- so the check is mechanical: render every icon,
 * and fail on any colour literal anywhere in the markup.
 *
 * `hardcodedColour` is a detector, and a detector that has never been seen to fire proves
 * nothing, so it is run against markup that is deliberately wrong as well as against the
 * real set.
 *
 * **The notice.** `D-52` says the geometry is Feather's, MIT, and that a copy carries an
 * obligation. `web/NOTICE` discharges it by listing which Feather file each icon came
 * from. A table maintained by hand goes stale the first time someone adds an icon, so the
 * table is read back here and compared with `FEATHER_SOURCE` in both directions.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import type { IconName, IconProps } from '@/shared/ui';
import { FEATHER_SOURCE, ICON_NAMES, Icon } from '@/shared/ui';

function markup(props: IconProps): string {
  return renderToStaticMarkup(createElement(Icon, props));
}

/**
 * Colour literals in rendered markup.
 *
 * Three shapes, because there are three ways a colour gets written by accident: a hex
 * literal, a functional notation, and a bare CSS colour keyword sitting in a paint
 * attribute. The keyword case is checked by reading every `fill` and `stroke` in the
 * markup and admitting exactly two values -- `none` and `currentColor` -- rather than by
 * listing the 148 named colours, so `stroke="rebeccapurple"` is caught without anyone
 * having had to think of it.
 */
function hardcodedColour(html: string): string[] {
  const found: string[] = [];
  for (const match of html.matchAll(/#[0-9a-fA-F]{3,8}\b/g)) found.push(match[0]);
  for (const match of html.matchAll(/\b(?:rgba?|hsla?|color|lab|lch|oklab|oklch)\([^)]*\)/g)) {
    found.push(match[0]);
  }
  for (const match of html.matchAll(/\b(?:fill|stroke|stop-color|flood-color)="([^"]*)"/g)) {
    const value = match[1] ?? '';
    if (value !== 'none' && value !== 'currentColor') found.push(match[0]);
  }
  return found;
}

/** The `<svg …>` open tag, which is where the whole convention lives. */
function rootTag(html: string): string {
  return /<svg[^>]*>/.exec(html)?.[0] ?? '';
}

/** Everything inside the root -- the geometry, which must carry no presentation. */
function children(html: string): string {
  return html.replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '');
}

describe('the icon set renders one convention', () => {
  it('names every icon once and derives the list rather than counting it', () => {
    // This asserted `toHaveLength(16)` and went red when the owner asked for a sun and a
    // moon — a hard-coded count that reddens on a correct change and teaches the next reader
    // to bump the literal. `W30-LISTS` ruled against exactly this two waves ago and this was
    // one of them. The relationship below is what the case was for: the names and the source
    // map describe the same set, and neither may quietly gain a member the other lacks.
    expect(ICON_NAMES.length).toBeGreaterThan(1);
    expect(new Set(ICON_NAMES).size).toBe(ICON_NAMES.length);
    expect([...ICON_NAMES].sort()).toEqual(Object.keys(FEATHER_SOURCE).sort());
  });

  it('gives every icon Feather geometry attributes and no others', () => {
    for (const name of ICON_NAMES) {
      const tag = rootTag(markup({ name }));
      expect(tag, name).toContain('viewBox="0 0 24 24"');
      expect(tag, name).toContain('fill="none"');
      expect(tag, name).toContain('stroke="currentColor"');
      expect(tag, name).toContain('stroke-width="2"');
      expect(tag, name).toContain('stroke-linecap="round"');
      expect(tag, name).toContain('stroke-linejoin="round"');
    }
  });

  it('carries the machine name in a data attribute, which is never translated', () => {
    for (const name of ICON_NAMES) {
      expect(markup({ name }), name).toContain(`data-icon="${name}"`);
    }
  });

  it('draws geometry only: no child element carries its own paint or width', () => {
    for (const name of ICON_NAMES) {
      const inside = children(markup({ name }));
      expect(inside, name).not.toMatch(/\b(?:fill|stroke|stroke-width|style)=/);
      expect(inside.length, name).toBeGreaterThan(0);
    }
  });

  it('draws a different shape for every name', () => {
    const shapes = new Map<string, IconName>();
    for (const name of ICON_NAMES) {
      const inside = children(markup({ name }));
      const seen = shapes.get(inside);
      expect(seen, `${name} draws the same shape as ${String(seen)}`).toBeUndefined();
      shapes.set(inside, name);
    }
  });
});

describe('colour is inherited, never written', () => {
  it('finds no colour literal in any icon', () => {
    for (const name of ICON_NAMES) {
      expect(hardcodedColour(markup({ name })), name).toEqual([]);
    }
  });

  it('finds none when the whole set is rendered at once', () => {
    const all = ICON_NAMES.map((name) => markup({ name })).join('');
    expect(hardcodedColour(all)).toEqual([]);
  });

  // The detector, shown failing. Each string is a way this has actually been broken
  // elsewhere: a pasted icon that kept its author's hex, a themed stroke that was
  // resolved at author time, and a keyword nobody would think to put on an allowlist.
  it.each([
    ['a hex fill', '<svg fill="#333"><path d="M0 0"/></svg>'],
    ['a functional notation', '<svg stroke="rgb(0, 0, 0)"><path d="M0 0"/></svg>'],
    ['a colour keyword', '<svg stroke="none"><path stroke="rebeccapurple" d="M0 0"/></svg>'],
    ['a hex inside a style', '<svg style="color:#fff"><path d="M0 0"/></svg>'],
  ])('reports %s', (_what, html) => {
    expect(hardcodedColour(html).length).toBeGreaterThan(0);
  });

  it('accepts the two paint values the convention allows', () => {
    expect(hardcodedColour('<svg fill="none" stroke="currentColor"></svg>')).toEqual([]);
  });
});

describe('size comes from outside', () => {
  it('defaults to the surrounding text size', () => {
    const tag = rootTag(markup({ name: 'project' }));
    expect(tag).toContain('width="1em"');
    expect(tag).toContain('height="1em"');
  });

  it('takes a number of pixels', () => {
    const tag = rootTag(markup({ name: 'project', size: 32 }));
    expect(tag).toContain('width="32"');
    expect(tag).toContain('height="32"');
  });

  it('takes any CSS length', () => {
    const tag = rootTag(markup({ name: 'project', size: '1.5rem' }));
    expect(tag).toContain('width="1.5rem"');
    expect(tag).toContain('height="1.5rem"');
  });
});

describe('an icon says nothing unless it is alone', () => {
  it('is hidden from assistive technology by default', () => {
    const tag = rootTag(markup({ name: 'accept' }));
    expect(tag).toContain('aria-hidden="true"');
    expect(tag).not.toContain('role=');
    expect(tag).not.toContain('aria-label=');
  });

  it('becomes an image with the caller’s name when it stands alone', () => {
    const tag = rootTag(markup({ name: 'accept', label: 'Принять' }));
    expect(tag).toContain('role="img"');
    expect(tag).toContain('aria-label="Принять"');
    expect(tag).not.toContain('aria-hidden');
  });

  it('is never a tab stop', () => {
    expect(rootTag(markup({ name: 'back' }))).toContain('focusable="false"');
  });
});

describe('the notice matches the set', () => {
  const NOTICE = readFileSync(fileURLToPath(new URL('../../NOTICE', import.meta.url)), 'utf8');

  /** The attribution table, parsed back out: our name -> the Feather file it names. */
  function noticeTable(): Map<string, string> {
    const rows = new Map<string, string>();
    for (const line of NOTICE.split('\n')) {
      const match = /^\|\s*`([a-z-]+)`\s*\|\s*`([a-z-]+)`\s*\|\s*(\S+)\s*\|$/.exec(line.trim());
      if (match !== null) rows.set(match[1] as string, `${match[2]}\u0000${match[3]}`);
    }
    return rows;
  }

  it('reproduces the licence rather than linking to it', () => {
    expect(NOTICE).toContain('The MIT License (MIT)');
    expect(NOTICE).toContain('Copyright (c) 2013-2023 Cole Bemis');
    expect(NOTICE).toContain(
      'The above copyright notice and this permission notice shall be included in all',
    );
  });

  it('names the Feather file behind every icon, and no icon that does not exist', () => {
    const table = noticeTable();
    expect([...table.keys()].sort()).toEqual([...ICON_NAMES].sort());
    for (const name of ICON_NAMES) {
      expect(table.get(name), name).toBe(`${FEATHER_SOURCE[name]}\u0000Feather`);
    }
  });

  it('states what is ours, so silence is not read as an omission', () => {
    expect(NOTICE).toContain('What is ours');
    expect(NOTICE).toMatch(/Of the icons in `web\/src\/shared\/ui\/icon\.tsx`: none\./);
  });
});
