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
 *   3. **Does the control put the MACHINE value where a machine can read it?** The labels
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
import { describe, expect, it } from 'vitest';

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
import type { ThemeChoice, ThemeStorage } from '@/_app';

import { DARK_MEDIA_SELECTOR, DARK_SELECTOR, parseTokens, parseTokensIn } from './contrast';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const GLOBALS = join(WEB, 'src', 'app', 'globals.css');
const CSS = readFileSync(GLOBALS, 'utf8');

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

// ============================================================ 4. the control, as it renders

describe('the theme control is Russian to read and machine-readable to test', () => {
  const markup = (): string => renderToStaticMarkup(createElement(ThemeToggle, {}));

  /*
   * The control is TWO buttons now, sun and moon, on the owner's instruction of 2026-09-22.
   * `system` is still a `ThemeChoice` and still the default — it is simply no longer a
   * button, so these cases assert over the two that render rather than over all three.
   */
  const SHOWN: readonly ThemeChoice[] = ['light', 'dark'];

  it('offers the two schemes, each labelled in Russian', () => {
    const rendered = markup();
    for (const choice of SHOWN) {
      const label = THEME_LABELS[choice];
      // Icon-only buttons, so the label reaches a reader through `aria-label`, which is also
      // where the rendered-language guard looks — it cannot silently become English.
      expect({ choice, shown: rendered.includes(`aria-label="${label}"`) }).toEqual({
        choice,
        shown: true,
      });
      expect({ choice, cyrillic: /[Ѐ-ӿ]/.test(label) }).toEqual({ choice, cyrillic: true });
      expect({ choice, latin: /[A-Za-z]/.test(label) }).toEqual({ choice, latin: false });
    }
    // The icon is what a sighted reviewer sees, so assert it is actually there.
    expect((rendered.match(/<svg/g) ?? []).length).toBe(SHOWN.length);
  });

  it('keeps `system` a real choice even though it is not a button', () => {
    // The cost of two controls instead of three is that there is no way BACK to `system`
    // from the interface. It must still be the default, or the OS preference stops being
    // honoured at all — which would be a different and much larger change.
    expect(THEME_CHOICES).toContain('system');
    expect(markup()).not.toContain('data-theme-choice="system"');
  });

  it('carries the machine value beside the label, where the journey reads it', () => {
    const rendered = markup();
    for (const choice of SHOWN) {
      expect(rendered).toContain(`data-theme-choice="${choice}"`);
    }
  });

  it('renders nothing pressed, because the default is not a button', () => {
    const rendered = markup();
    // The server has no storage, so the markup it produces is the default — and the first
    // client render must agree with it or React discards the tree.
    // The default is `system`, which is no longer a button — so NOTHING is pressed, and
    // that is the assertion. A pressed control in the server markup would mean the default
    // had silently become an explicit choice.
    expect((rendered.match(/aria-pressed="true"/g) ?? []).length).toBe(0);
    expect((rendered.match(/aria-pressed="false"/g) ?? []).length).toBe(SHOWN.length);
  });

  it('is a labelled group of buttons rather than loose controls', () => {
    const rendered = markup();
    expect(rendered).toContain('role="group"');
    expect((rendered.match(/<button/g) ?? []).length).toBe(SHOWN.length);
    expect(rendered).toContain('type="button"');
  });
});
