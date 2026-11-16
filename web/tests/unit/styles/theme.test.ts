/**
 * The second palette, and the control that chooses it.
 *
 * `contrast.test.ts` answers "is the dark theme legible". This file answers the three
 * questions that come before it and that a contrast measurement structurally cannot ask:
 *
 *   1. **Is the dark palette COMPLETE?** A token declared in `:root` and not in the dark
 *      block is not a missing value — it is a light colour on a dark screen, and it is
 *      invisible to a contrast census, which only measures the pairs that MEET. A
 *      `--am-ok-light` left behind would be a white plaque in a dark interface and every
 *      ratio around it would still pass, because the ink on it would pass too.
 *   2. **Do the two dark blocks agree?** The values appear twice — once under
 *      `@media (prefers-color-scheme: dark)` for a visitor who has chosen nothing, once
 *      under `[data-theme='dark']` for a visitor who has chosen — because plain CSS has no
 *      other way to let a choice beat a system preference. Duplication that nothing checks
 *      drifts, and the drift would show as "the theme is almost right when I pick it and
 *      slightly different when my laptop picks it", which is the kind of defect nobody
 *      reports because nobody can describe it.
 *   3. **Is the control ONE button that switches to the other theme?** (`UIP-G-03`, `Г2-B`.)
 *      Its name and glyph stand for the theme a press switches TO, the glyph is chosen by the
 *      stylesheet from the palette's own selectors so the first frame is right, and a press
 *      stores an explicit `light`/`dark` and never `system`.
 *   4. **Does the control put the MACHINE value where a machine can read it?** The labels
 *      are Russian, because the interface is Russian. The value is not: `data-theme-choice`
 *      on the button and `data-theme` on the document element are what the browser journey
 *      and the PA-01 criterion-4 evidence select on, and they must survive the translation
 *      of every word beside them.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  THEME_ATTRIBUTE,
  THEME_CHOICES,
  THEME_LABELS,
  THEME_STORAGE_KEY,
  ThemeToggle,
  applyThemeChoice,
  isThemeChoice,
  readThemeChoice,
  writeThemeChoice,
} from '@/_app';
import type { ThemeStorage } from '@/_app';
import {
  SYSTEM_DARK_QUERY,
  THEME_SWITCH_LABEL,
  oppositeThemeAppearance,
  resolveThemeAppearance,
  switchTheme,
  systemDarkQuery,
  themeSwitchLabel,
} from '@/_app/theme';
import type { ThemeAppearance } from '@/_app/theme';

import { DARK_MEDIA_SELECTOR, DARK_SELECTOR, parseRules, parseTokens, parseTokensIn } from './contrast';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const GLOBALS = join(WEB, 'src', 'app', 'globals.css');
const CSS = readFileSync(GLOBALS, 'utf8');
const FRAME_CSS = readFileSync(join(WEB, 'src', '_app', 'app-frame.module.css'), 'utf8');

/** A token carries a colour when its value spells one; `--am-shadow-0: none` does not. */
function carriesColour(value: string): boolean {
  return /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/.test(value);
}

// ================================================================= 1. the palette is whole

describe('the dark palette overrides every token that carries a colour, and invents none', () => {
  const light = parseTokens(CSS);
  const dark = parseTokensIn(CSS, DARK_SELECTOR);

  it('leaves no colour-bearing token to fall through to the light value', () => {
    const missing = [...light]
      .filter(([, value]) => carriesColour(value))
      .map(([name]) => name)
      .filter((name) => !dark.has(name));
    expect(
      missing,
      'These tokens carry a colour in `:root` and have no value in the dark block, so a ' +
        'dark screen paints them with the LIGHT colour. A contrast census cannot see this: ' +
        'it measures the pairs that meet, and a light tint under light ink passes.',
    ).toEqual([]);
    // Anti-vacuity: there is a substantial palette here, not an empty filter.
    expect([...light].filter(([, v]) => carriesColour(v)).length).toBeGreaterThanOrEqual(25);
  });

  it('overrides nothing `:root` does not declare', () => {
    const invented = [...dark.keys()].filter((name) => !light.has(name));
    expect(
      invented,
      'A token that exists only in the dark block is a token the light theme renders as ' +
        'nothing. Declare it in `:root` first.',
    ).toEqual([]);
  });

  it('changes every one of them: a dark palette that repeats a light value is not one', () => {
    const unchanged = [...dark].filter(([name, value]) => light.get(name) === value).map(([name]) => name);
    expect(unchanged).toEqual([]);
  });
});

// ============================================================ 2. the two blocks cannot drift

describe('the system-preference block and the explicit-choice block are the same palette', () => {
  it('declares the same tokens with the same values in both', () => {
    const chosen = parseTokensIn(CSS, DARK_SELECTOR);
    const preferred = parseTokensIn(CSS, DARK_MEDIA_SELECTOR);
    // Compared as sorted entries rather than as text: the two blocks are indented
    // differently, and indentation is not a palette.
    const entries = (map: ReadonlyMap<string, string>): [string, string][] =>
      [...map].sort(([a], [b]) => a.localeCompare(b));
    expect(
      entries(preferred),
      'The dark values under `@media (prefers-color-scheme: dark)` and under ' +
        "`[data-theme='dark']` have drifted apart. A visitor who picked dark and a visitor " +
        'whose system picked it would see two different interfaces. Make them equal.',
    ).toEqual(entries(chosen));
    expect(entries(chosen).length).toBeGreaterThanOrEqual(25);
  });

  it('can fail: the check is comparing the blocks and not a block with itself', () => {
    const a = parseTokensIn(":root[data-theme='dark'] { --am-ink: #e2e8f0; }", DARK_SELECTOR);
    const b = parseTokensIn(
      "@media (x) { :root:not([data-theme='light']) { --am-ink: #e3e9f1; } }",
      DARK_MEDIA_SELECTOR,
    );
    expect([...a]).not.toEqual([...b]);
  });
});

// ================================================================== 3. the choice, as logic

describe('a theme choice is read, kept and applied', () => {
  const store = (initial: Record<string, string>): ThemeStorage & { readonly written: Record<string, string> } => {
    const written: Record<string, string> = { ...initial };
    return {
      written,
      getItem: (key) => written[key] ?? null,
      setItem: (key, value) => {
        written[key] = value;
      },
    };
  };

  const root = (): { setAttribute(n: string, v: string): void; removeAttribute(n: string): void; attrs: Record<string, string | null> } => {
    const attrs: Record<string, string | null> = {};
    return {
      attrs,
      setAttribute: (n, v) => {
        attrs[n] = v;
      },
      removeAttribute: (n) => {
        attrs[n] = null;
      },
    };
  };

  it('is `system` on a first visit, which is the case a two-value toggle cannot express', () => {
    expect(readThemeChoice(store({}))).toBe('system');
    expect(readThemeChoice(null)).toBe('system');
  });

  it('is `system` when what is stored is not a choice this application makes', () => {
    // A stale key from an earlier build, or a user editing storage by hand. Falling back
    // to a named default is the behaviour; guessing `dark` from a truthy string is not.
    expect(readThemeChoice(store({ [THEME_STORAGE_KEY]: 'sepia' }))).toBe('system');
    expect(readThemeChoice(store({ [THEME_STORAGE_KEY]: '' }))).toBe('system');
    expect(isThemeChoice('sepia')).toBe(false);
    for (const choice of THEME_CHOICES) expect(isThemeChoice(choice)).toBe(true);
  });

  it('survives a storage that refuses to answer, rather than taking the screen down with it', () => {
    const hostile: ThemeStorage = {
      getItem: () => {
        throw new Error('storage disabled');
      },
      setItem: () => {
        throw new Error('storage disabled');
      },
    };
    expect(readThemeChoice(hostile)).toBe('system');
    expect(() => writeThemeChoice(hostile, 'dark')).not.toThrow();
  });

  it('round-trips each choice through storage', () => {
    for (const choice of THEME_CHOICES) {
      const kept = store({});
      writeThemeChoice(kept, choice);
      expect(kept.written[THEME_STORAGE_KEY]).toBe(choice);
      expect(readThemeChoice(kept)).toBe(choice);
    }
  });

  it('writes the machine value to the document, and REMOVES it for `system`', () => {
    for (const choice of ['light', 'dark'] as const) {
      const element = root();
      applyThemeChoice(element, choice);
      expect(element.attrs[THEME_ATTRIBUTE]).toBe(choice);
    }
    // `system` must not become a third attribute value: there is no block that selects it,
    // and writing one would stop `@media (prefers-color-scheme: dark)` from being the
    // answer. Removal is the mechanism, not an omission.
    const element = root();
    applyThemeChoice(element, 'dark');
    applyThemeChoice(element, 'system');
    expect(element.attrs[THEME_ATTRIBUTE]).toBeNull();
  });

  it('the attribute it writes is the one the stylesheet selects on', () => {
    expect(CSS).toContain(`[${THEME_ATTRIBUTE}='dark']`);
    expect(CSS).toContain(`[${THEME_ATTRIBUTE}='light']`);
  });
});

// ===================================================== 4. one button, as logic (UIP-G-03)

describe('one press switches to the opposite of the theme showing, and keeps it', () => {
  const store = (initial: Record<string, string> = {}): ThemeStorage & { readonly kept: Record<string, string> } => {
    const kept: Record<string, string> = { ...initial };
    return { kept, getItem: (k) => kept[k] ?? null, setItem: (k, v) => void (kept[k] = v) };
  };
  const root = (): { setAttribute(n: string, v: string): void; removeAttribute(n: string): void; attrs: Record<string, string | null> } => {
    const attrs: Record<string, string | null> = {};
    return { attrs, setAttribute: (n, v) => void (attrs[n] = v), removeAttribute: (n) => void (attrs[n] = null) };
  };

  it('resolves a choice to the appearance showing: `system` is the operating system, and unknown until asked', () => {
    expect(resolveThemeAppearance('light', true)).toBe('light');
    expect(resolveThemeAppearance('dark', false)).toBe('dark');
    expect(resolveThemeAppearance('system', true)).toBe('dark');
    expect(resolveThemeAppearance('system', false)).toBe('light');
    // Before anything has read the system (the server render) nothing is guessed...
    expect(resolveThemeAppearance('system', null)).toBeNull();
    // ...but an explicit choice needs no system to be known.
    expect(resolveThemeAppearance('dark', null)).toBe('dark');
  });

  it('names the control for the theme it switches TO, as the original does', () => {
    expect(themeSwitchLabel('dark')).toBe('Светлая тема');
    expect(themeSwitchLabel('light')).toBe('Тёмная тема');
    expect(themeSwitchLabel('dark')).toBe(THEME_LABELS.light);
    expect(themeSwitchLabel('light')).toBe(THEME_LABELS.dark);
    // Not known yet: a neutral name rather than a wrong one.
    expect(themeSwitchLabel(null)).toBe(THEME_SWITCH_LABEL);
    expect(THEME_SWITCH_LABEL).not.toBe(THEME_LABELS.light);
    expect(THEME_SWITCH_LABEL).not.toBe(THEME_LABELS.dark);
  });

  it('switches away from what is showing, for every starting state', () => {
    const cases: readonly [choice: (typeof THEME_CHOICES)[number], systemDark: boolean, next: ThemeAppearance][] = [
      ['system', false, 'dark'], // first visit on a light machine: showing light, press gives dark
      ['system', true, 'light'], // first visit on a dark machine: showing dark, press gives light
      ['light', false, 'dark'],
      ['light', true, 'dark'], // an explicit choice beats the system: showing light, press gives dark
      ['dark', false, 'light'],
      ['dark', true, 'light'],
    ];
    for (const [choice, systemDark, next] of cases) {
      const kept = store();
      const element = root();
      const made = switchTheme(element, kept, choice, systemDark);
      expect({ choice, systemDark, made }).toEqual({ choice, systemDark, made: next });
      // Kept under the same key and value set as before, and put on the document.
      expect(kept.kept[THEME_STORAGE_KEY]).toBe(next);
      expect(element.attrs[THEME_ATTRIBUTE]).toBe(next);
      expect(readThemeChoice(kept)).toBe(next);
    }
  });

  it('never writes `system`, and cannot get back to it: the second press goes to the other explicit theme', () => {
    const kept = store();
    const element = root();
    let choice: (typeof THEME_CHOICES)[number] = 'system';
    const seen: string[] = [];
    for (let press = 0; press < 4; press += 1) {
      choice = switchTheme(element, kept, choice, false);
      seen.push(choice);
    }
    // From a light machine's `system`: dark, light, dark, light. Never `system` again.
    expect(seen).toEqual(['dark', 'light', 'dark', 'light']);
    expect(oppositeThemeAppearance('dark')).toBe('light');
    expect(oppositeThemeAppearance('light')).toBe('dark');
  });

  it('a press on a storage that refuses to write still switches the screen', () => {
    const hostile: ThemeStorage = {
      getItem: () => null,
      setItem: () => {
        throw new Error('quota');
      },
    };
    const element = root();
    expect(() => switchTheme(element, hostile, 'system', true)).not.toThrow();
    expect(element.attrs[THEME_ATTRIBUTE]).toBe('light');
    const none = root();
    expect(switchTheme(none, null, 'system', false)).toBe('dark');
    expect(none.attrs[THEME_ATTRIBUTE]).toBe('dark');
  });
});

describe('the system-preference query is asked for, not assumed', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('is `null` where there is no window or no `matchMedia`, which is the light palette the stylesheet shows', () => {
    expect(systemDarkQuery()).toBeNull(); // the suite runs under node: no window
    vi.stubGlobal('window', {});
    expect(systemDarkQuery()).toBeNull();
  });

  it('asks the media query the dark palette answers to', () => {
    const asked: string[] = [];
    const list = { matches: true, addEventListener: () => undefined, removeEventListener: () => undefined };
    vi.stubGlobal('window', { matchMedia: (query: string) => (asked.push(query), list) });
    expect(systemDarkQuery()).toBe(list);
    expect(asked).toEqual([SYSTEM_DARK_QUERY]);
    expect(CSS).toContain(`@media ${SYSTEM_DARK_QUERY}`);
  });

  it('is `null` when asking throws', () => {
    vi.stubGlobal('window', {
      matchMedia: () => {
        throw new Error('blocked');
      },
    });
    expect(systemDarkQuery()).toBeNull();
  });
});

// ============================================== 5. the glyph is chosen by the stylesheet

/**
 * The text between the braces of the first `@media <condition> { ... }`, and the stylesheet with
 * that block removed. `parseRules` flattens media blocks, which is right for the contrast census
 * and loses exactly the fact this section needs: which rules are under the dark media query.
 */
function splitMedia(css: string, condition: string): { inside: string; outside: string } {
  const head = css.indexOf(`@media ${condition}`);
  if (head < 0) return { inside: '', outside: css };
  const open = css.indexOf('{', head);
  let depth = 1;
  let at = open + 1;
  while (at < css.length && depth > 0) {
    if (css[at] === '{') depth += 1;
    else if (css[at] === '}') depth -= 1;
    at += 1;
  }
  return { inside: css.slice(open + 1, at - 1), outside: css.slice(0, head) + css.slice(at) };
}

type Glyph = 'sun' | 'moon';

/** The attribute selectors the palette in `globals.css` is keyed on. */
const ATTRIBUTE_DARK = `${THEME_ATTRIBUTE}='dark'`;
const ATTRIBUTE_LIGHT = `${THEME_ATTRIBUTE}='light'`;

/**
 * Which glyph is displayed for a document in one state, by evaluating the glyph rules of
 * `app-frame.module.css` as a cascade: the rules that match, the highest specificity, then the
 * later one. The selectors it understands are exactly the shapes the stylesheet uses (a plain
 * one, with or without the dark media query around it, and the explicit-dark and explicit-light
 * ones on `<html>`); a shape it does not know is not silently ignored, it fails the test.
 */
function glyphsShown(css: string, state: { attribute: 'light' | 'dark' | null; systemDark: boolean }): Glyph[] {
  const { inside, outside } = splitMedia(css, SYSTEM_DARK_QUERY);
  const rules = [
    ...parseRules(outside, 'frame').map((rule) => ({ rule, underMedia: false })),
    ...parseRules(inside, 'frame').map((rule) => ({ rule, underMedia: true })),
  ].filter(({ rule }) => rule.selector.includes('am-theme__icon'));
  const shown: Glyph[] = [];
  for (const glyph of ['sun', 'moon'] as const) {
    let winner: { specificity: number; order: number; display: string } | null = null;
    rules.forEach(({ rule, underMedia }, order) => {
      const display = rule.declarations.get('display');
      const names = rule.selector.match(/am-theme__icon--(sun|moon)/)?.[1];
      if (display === undefined || (names !== undefined && names !== glyph)) return;
      // A rule inside the dark media query applies only while the system is dark.
      if (underMedia && !state.systemDark) return;
      let specificity = 2;
      if (rule.selector.includes(`:root[${ATTRIBUTE_DARK}]`)) {
        if (state.attribute !== 'dark') return;
        specificity = 4;
      } else if (rule.selector.includes(`:root[${ATTRIBUTE_LIGHT}]`)) {
        if (state.attribute !== 'light') return;
        specificity = 4;
      } else {
        expect(rule.selector, 'a selector shape this evaluator does not know').toMatch(
          /^\.end :global\(\.am-theme__icon(--(sun|moon))?\)$/,
        );
      }
      if (winner === null || specificity > winner.specificity || (specificity === winner.specificity && order > winner.order)) {
        winner = { specificity, order, display };
      }
    });
    const chosen = winner as { display: string } | null;
    if (chosen !== null && chosen.display !== 'none') shown.push(glyph);
  }
  return shown;
}

describe('the stylesheet shows the glyph of the theme the press switches TO, on the first frame', () => {
  const STATES = [
    { attribute: null, systemDark: false },
    { attribute: null, systemDark: true },
    { attribute: 'light', systemDark: false },
    { attribute: 'light', systemDark: true },
    { attribute: 'dark', systemDark: false },
    { attribute: 'dark', systemDark: true },
  ] as const;

  for (const state of STATES) {
    it(`attribute ${state.attribute ?? 'absent'}, system ${state.systemDark ? 'dark' : 'light'}: exactly one glyph, the other theme's`, () => {
      const showing = resolveThemeAppearance(state.attribute ?? 'system', state.systemDark);
      // The sun stands for light, so it is shown while the screen is dark; the moon the reverse.
      const expected: Glyph = showing === 'dark' ? 'sun' : 'moon';
      expect(glyphsShown(FRAME_CSS, state)).toEqual([expected]);
    });
  }

  it('can fail: without the system-preference rules a dark machine with no choice shows the wrong glyph', () => {
    const { outside } = splitMedia(FRAME_CSS, SYSTEM_DARK_QUERY);
    expect(glyphsShown(outside, { attribute: null, systemDark: true })).toEqual(['moon']);
    expect(glyphsShown(FRAME_CSS, { attribute: null, systemDark: true })).toEqual(['sun']);
  });

  it('reads the palette\'s own two inputs, so the glyph cannot follow a different rule than the colours', () => {
    // The explicit-dark selector is the very one the dark token block uses; the explicit-light one is the
    // attribute the system-dark block excludes (`DARK_MEDIA_SELECTOR`); the media query is the same string.
    expect(FRAME_CSS).toContain(`:global(${DARK_SELECTOR})`);
    expect(FRAME_CSS).toContain(`:global(:root[${ATTRIBUTE_LIGHT}])`);
    expect(CSS).toContain(DARK_SELECTOR);
    expect(DARK_MEDIA_SELECTOR).toContain(`[${ATTRIBUTE_LIGHT}]`);
    expect(splitMedia(FRAME_CSS, SYSTEM_DARK_QUERY).inside).toContain('am-theme__icon--sun');
  });

  it('declares no `:not()`: the contrast census declines it, and its list of declined selectors is closed', () => {
    expect(FRAME_CSS.replace(/\/\*[\s\S]*?\*\//g, '')).not.toContain(':not(');
  });
});

// ============================================================ 6. the control, as it renders

describe('the theme control is Russian to read and machine-readable to test', () => {
  const markup = (): string => renderToStaticMarkup(createElement(ThemeToggle, {}));

  it('is ONE button, with no group around it and no second control', () => {
    const rendered = markup();
    expect((rendered.match(/<button/g) ?? []).length).toBe(1);
    expect(rendered).toContain('type="button"');
    expect(rendered).not.toContain('role="group"');
    expect(rendered).not.toContain('aria-label="Оформление"');
    // The old two-button wording must not survive as a second label.
    expect(rendered).not.toContain(`aria-label="${THEME_LABELS.light}"`);
    expect(rendered).not.toContain(`aria-label="${THEME_LABELS.dark}"`);
  });

  it('is named in Russian by `aria-label`, with the same words as the tooltip', () => {
    const rendered = markup();
    // The server cannot know which theme is showing, so it renders the neutral name; the
    // effect replaces it with the theme's name right after hydration.
    expect(rendered).toContain(`aria-label="${THEME_SWITCH_LABEL}"`);
    expect(rendered).toContain(`title="${THEME_SWITCH_LABEL}"`);
    for (const label of [THEME_SWITCH_LABEL, THEME_LABELS.light, THEME_LABELS.dark]) {
      // `aria-label` is where the rendered-language guard looks: it cannot silently become English.
      expect({ label, cyrillic: /[Ѐ-ӿ]/.test(label) }).toEqual({ label, cyrillic: true });
      expect({ label, latin: /[A-Za-z]/.test(label) }).toEqual({ label, latin: false });
    }
  });

  it('puts BOTH glyphs in the markup, so the stylesheet can choose without waiting for a script', () => {
    const rendered = markup();
    expect((rendered.match(/<svg/g) ?? []).length).toBe(2);
    expect(rendered).toContain('data-icon="light"');
    expect(rendered).toContain('data-icon="dark"');
    expect(rendered).toContain('am-theme__icon--sun');
    expect(rendered).toContain('am-theme__icon--moon');
  });

  it('keeps `system` a real choice even though it is not a position of the control', () => {
    // It is the state before the first press and the default; the stored value stays one of three.
    expect(THEME_CHOICES).toContain('system');
    expect(markup()).not.toContain('data-theme-choice="system"');
  });

  it('carries no pressed state: the name says what the press does, not where it stands', () => {
    // A pressed state AND a name that flips with it would be announced twice, and contradictorily.
    expect(markup()).not.toContain('aria-pressed');
  });

  it('renders the same on the server as on the first client render: nothing depends on storage or the system', () => {
    const rendered = markup();
    // `data-theme-choice` appears only once the appearance is known, which the server cannot say;
    // a first render that carried it would disagree with the one the effect makes.
    expect(rendered).not.toContain('data-theme-choice');
    expect(markup()).toBe(rendered);
  });
});
