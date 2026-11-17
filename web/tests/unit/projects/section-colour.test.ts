/**
 * Every section has one colour, and the list that says which is whole (`UIP-G-17`).
 *
 * The list is `SECTION_COLOUR_TOKENS`, section code to palette token, in
 * `entities/project/model/section-colour.ts`. A list that names a colour is the shape that
 * rots quietly: a sixteenth section added to the catalogue gets no colour and the menu draws
 * a hole, a token renamed in `globals.css` leaves a `var()` that resolves to nothing (the
 * dot is then transparent, and nothing fails), two sections end up sharing one colour. So it
 * is held against both of its authorities, the catalogue (`PROJECT_SECTIONS`) and the
 * stylesheet, by a pure function that is run twice: on fixtures that are broken on purpose
 * (which is what proves it can fail) and on the real list.
 *
 * The colours themselves, their contrast and their distance, are `section-palette.test.ts`.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  PROJECT_SECTIONS,
  SectionDot,
  UnknownProjectSectionError,
  sectionColourStyle,
  sectionColourVar,
} from '@/entities/project';
import type { ProjectSectionCode } from '@/entities/project';
import { SECTION_COLOUR_TOKENS } from '@/entities/project/model/section-colour';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseTokens } from '../styles/contrast';

const CSS = readFileSync(join(WEB_ROOT, 'src', 'app', 'globals.css'), 'utf8');

/** The tokens `:root` declares for sections: `--am-section-NN`, and not the dot's own property. */
const declaredSectionTokens = (css: string): Set<string> =>
  new Set([...parseTokens(css).keys()].filter((name) => /^--am-section-\d\d$/.test(name)));

/** Everything wrong with a code-to-token list, one sentence each. Empty when it is whole. */
export function listProblems(
  list: Readonly<Record<string, string>>,
  codes: readonly string[],
  declared: ReadonlySet<string>,
): string[] {
  const problems: string[] = [];
  for (const code of codes) {
    if (!(code in list)) problems.push(`${code} has no token`);
  }
  for (const code of Object.keys(list)) {
    if (!codes.includes(code)) problems.push(`${code} is not a section of the catalogue`);
  }
  const wearers = new Map<string, string[]>();
  for (const [code, token] of Object.entries(list)) {
    if (!declared.has(token)) problems.push(`${code} names ${token}, which the stylesheet does not declare`);
    wearers.set(token, [...(wearers.get(token) ?? []), code]);
  }
  for (const [token, codes2] of wearers) {
    if (codes2.length > 1) problems.push(`${token} is worn by ${codes2.join(' and ')}`);
  }
  for (const token of declared) {
    if (!wearers.has(token)) problems.push(`${token} is declared and no section wears it`);
  }
  return problems;
}

const CODES = PROJECT_SECTIONS.map((section) => section.code);

describe('the code-to-token list is held against the catalogue and the stylesheet', () => {
  const real = { ...SECTION_COLOUR_TOKENS } as Record<string, string>;
  const declared = declaredSectionTokens(CSS);

  it('is not vacuous: fifteen sections, fifteen declared tokens', () => {
    expect(CODES).toHaveLength(15);
    expect(declared.size).toBe(15);
  });

  it('is whole: every section has a token, every token exists, none is shared, none is left over', () => {
    expect(listProblems(real, CODES, declared)).toEqual([]);
  });

  it('can fail: a section left out of the list', () => {
    const { PB: _left, ...withoutPb } = real;
    void _left;
    expect(listProblems(withoutPb, CODES, declared)).toEqual([
      'PB has no token',
      '--am-section-12 is declared and no section wears it',
    ]);
  });

  it('can fail: a code the catalogue does not have, a token the stylesheet does not have, a shared token', () => {
    expect(listProblems({ ...real, XX: '--am-section-12' }, CODES, declared)).toEqual([
      'XX is not a section of the catalogue',
      '--am-section-12 is worn by PB and XX',
    ]);
    expect(listProblems({ ...real, AR: '--am-section-16' }, CODES, declared)).toEqual([
      'AR names --am-section-16, which the stylesheet does not declare',
      '--am-section-01 is declared and no section wears it',
    ]);
    expect(listProblems({ ...real, AR: real.AI as string }, CODES, declared)).toEqual([
      '--am-section-05 is worn by AR and AI',
      '--am-section-01 is declared and no section wears it',
    ]);
  });

  it('can fail on the stylesheet side: a token declared and worn by no section', () => {
    const more = new Set([...declared, '--am-section-16']);
    expect(listProblems(real, CODES, more)).toEqual(['--am-section-16 is declared and no section wears it']);
  });
});

describe('the list is read through two functions', () => {
  it('gives every section the var() of its own token', () => {
    for (const code of CODES) {
      expect(sectionColourVar(code), code).toBe(`var(${SECTION_COLOUR_TOKENS[code]})`);
      expect(sectionColourVar(code), code).toMatch(/^var\(--am-section-\d\d\)$/);
    }
  });

  it('gives a style that sets the one property the dot reads', () => {
    for (const code of CODES) {
      expect(sectionColourStyle(code), code).toEqual({ '--am-section-colour': sectionColourVar(code) });
    }
  });

  it('gives «Без раздела» an existing neutral token and no section colour', () => {
    const neutral = sectionColourVar(null);
    expect(neutral).toBe('var(--am-inert)');
    expect(parseTokens(CSS).has('--am-inert')).toBe(true);
    expect(CODES.map((code) => sectionColourVar(code))).not.toContain(neutral);
    expect(sectionColourStyle(null)).toEqual({ '--am-section-colour': neutral });
  });

  it('refuses a code outside the catalogue instead of guessing a colour', () => {
    expect(() => sectionColourVar('XX' as ProjectSectionCode)).toThrow(UnknownProjectSectionError);
    expect(() => sectionColourStyle('constructor' as ProjectSectionCode)).toThrow(UnknownProjectSectionError);
  });

  it('declares the property a dot reads, once, as a reference to the neutral token', () => {
    const values = [...CSS.matchAll(/--am-section-colour\s*:\s*([^;]+);/g)].map((match) => (match[1] as string).trim());
    expect(values).toEqual(['var(--am-inert)']);
  });
});

describe('the dot of a section', () => {
  it('is a circle with no text, hidden from assistive technology, carrying its section colour', () => {
    for (const code of CODES) {
      const html = renderToStaticMarkup(createElement(SectionDot, { code }));
      expect(html, code).toMatch(/^<span /);
      expect(html, code).toContain('aria-hidden="true"');
      expect(html, code).toContain(`data-section-dot="${code}"`);
      expect(html, code).toContain(`style="--am-section-colour:${sectionColourVar(code)}"`);
      expect(html, code).toMatch(/><\/span>$/);
    }
  });

  it('draws «Без раздела» with the neutral colour and says so', () => {
    const html = renderToStaticMarkup(createElement(SectionDot, { code: null }));
    expect(html).toContain('data-section-dot="none"');
    expect(html).toContain('style="--am-section-colour:var(--am-inert)"');
  });

  it('draws a different colour for every section', () => {
    const styles = CODES.map((code) => renderToStaticMarkup(createElement(SectionDot, { code })).match(/style="([^"]*)"/)?.[1]);
    expect(new Set(styles).size).toBe(CODES.length);
  });
});
