/**
 * The token set's legibility, as a measured figure with a guard.
 *
 * `W31-STYLE` built the styling layer and closed its report with a named risk, in its
 * own words: *"the `-light` tints were chosen by eye, no WCAG figure is claimed."* For an
 * interface whose whole purpose is that a domain expert reads findings carefully, "chosen
 * by eye" is the wrong standard for text legibility, and unlike most of `R-18` this one
 * has an objective measure. This file is that measure.
 *
 * WHAT IT ASSERTS, AND WHAT IT DELIBERATELY DOES NOT. It asserts a RELATIONSHIP — this
 * pair is at or above its threshold — and never a ratio. A test that said
 * `expect(ratio).toBe(4.62)` would redden on every correct change and would teach the
 * next reader to update the number instead of reading it, which is how a guard becomes a
 * transcription exercise.
 *
 * WHERE THE PAIRS AND THE THRESHOLDS COME FROM. Both are derived, because a hand-written
 * list of "the pairs that matter" is the exact class `W30-LISTS` closed eighteen
 * instances of: a hand-maintained subset standing in for a set something else decides,
 * with nothing that fails when the authority grows.
 *
 *   the PAIRS       are computed by `census()` from thirty rendered screens crossed with
 *                   the stylesheet, plus `declaredPairs()` for the rules one server
 *                   render pass structurally cannot reach;
 *   the THRESHOLD   is a function of what the pair IS — 4.5 for text (WCAG 1.4.3 AA),
 *                   3.0 for a boundary or a graphic that carries meaning (1.4.11) —
 *                   and whether a boundary carries meaning is itself derived: the
 *                   element is interactive per the MARKUP (an interactive tag, a `role`,
 *                   a `tabindex`), and its own fill does not already distinguish it from
 *                   what is behind it.
 *
 * So the only hand-maintained set in this file is `REGISTERED`: pairs that are measured,
 * below threshold, and knowingly not repaired this wave, each with its reason. It is
 * held to the census in BOTH directions — a registered pair the screens no longer produce
 * is a failure, exactly as an unregistered pair below threshold is. A stale exemption
 * cannot sit here unnoticed, and a new failure cannot hide behind one.
 */

/// <reference types="vite/client" />

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import {
  AA_NON_TEXT,
  AA_TEXT,
  DARK_MEDIA_SELECTOR,
  THEMES,
  census,
  contrastRatio,
  declaredPairs,
  palette,
  parseRules,
  readColour,
  relativeLuminance,
  resolve,
  thresholdFor,
  unsupported,
} from './contrast';
import type { Occurrence, Rule, Theme, TokenName } from './contrast';
import { screens } from './screens';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const GLOBALS = join(WEB, 'src', 'app', 'globals.css');

/**
 * Every collocated CSS module in the tree, FOUND rather than listed — and rewritten into
 * the class names the markup actually carries.
 *
 * TWO defects are closed here and the second is the one that mattered.
 *
 * **The list.** `MODULES` was a literal array of one: `run-progress.module.css`, the only
 * module that existed when this file was written. A second landed one wave later
 * (`project-sections.module.css`, `W33-SECT`) and the census did not read it — the
 * hand-maintained-subset shape `W30-LISTS` closed eighteen instances of, standing in for a
 * set the filesystem decides. `import.meta.glob` is the derivation; `styling-layer.test.ts`
 * has always walked for the same files.
 *
 * **The names.** A CSS module's class names are SCOPED at build time: the module declares
 * `.ordinal` and the markup carries `class="_ordinal_b1553c"`, with a different suffix per
 * file. `parseRules` reads the authored file, so every module selector this census parsed
 * matched **no element ever** — the cascade half of the measurement was empty for modules,
 * and the only module pair that ever reached the register did so through `declaredPairs`,
 * which needs `color` and `background` in one rule. So the sentence "the census crosses
 * MODULES with the rendered markup" was false for the whole of `W32-CONTRAST` and
 * `W33-THEME`, and `project-sections.module.css`'s own header — *"a colour declared in a
 * collocated module is a colour that census cannot see"* — was **right**, for a deeper
 * reason than the array. A session declined the architecture `globals.css` promises because
 * of it.
 *
 * The scoped name is read from the module's own export rather than reconstructed: the
 * mapping is the bundler's, and a guard that guessed its format would be measuring its own
 * guess. Scoping the module rules into the cascade takes the census from 118 pairs to 123
 * and introduces no failure in either palette.
 */
const MODULE_EXPORTS = import.meta.glob('../../../src/**/*.module.css', { eager: true }) as Record<
  string,
  { readonly default: Record<string, string> }
>;

/** One module's text, with every class selector rewritten to the name the markup carries. */
function scopedCss(relative: string): string {
  const scope = (MODULE_EXPORTS[relative] as { readonly default: Record<string, string> }).default;
  const css = readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf8');
  // A class selector only: the character after the dot must begin an identifier, so
  // `0.35rem` and `82ch` are untouched.
  return css.replace(/\.([a-zA-Z_][A-Za-z0-9_-]*)/g, (_match, name: string) => `.${scope[name]}`);
}

const MODULES = Object.keys(MODULE_EXPORTS).sort();

function moduleRules(): Rule[] {
  return MODULES.map((relative) => parseRules(scopedCss(relative), relative)).flat();
}

// --------------------------------------------------------------------------- the register

/**
 * A pair is measured ONCE PER PALETTE, and an exemption is granted the same way.
 *
 * `W33-THEME` gave this stylesheet a second token set, and a one-theme register would have
 * been the exact failure this file was built to refuse. The ratios are a property of the
 * VALUES: `--am-ink-soft` on `--am-accent-light` is 4.68:1 in the light palette and 4.78:1
 * in the dark one, and a pair may pass in one and fail in the other with nothing on screen
 * to say which. A register keyed only by pair would have let the failing half of any such
 * pair sit behind the passing half's row, silently — so each row names the themes it
 * excuses, and an unexcused failure in ANY theme is red.
 */
interface Registered {
  readonly key: string;
  /** The palettes this exemption covers. A failure in a palette not named here is a failure. */
  readonly themes: readonly Theme[];
  readonly why: string;
}

/**
 * Below threshold, measured, and knowingly not repaired.
 *
 * Each row is a decision with an owner, not a silence. `docs/program/W32-CONTRAST.md` §3
 * carries the arithmetic for the light palette; the dark one is in the second-palette
 * comment at the head of `globals.css`.
 */
const REGISTERED: readonly Registered[] = [
  /*
   * REMOVED, repaired rather than accepted. `W32-CONTRAST` registered
   * `text|--am-ink-inverse|--am-accent-light|-|selection` because `::selection` set no
   * `color` of its own, so selecting a primary button label put white on a pale tint at
   * 1.17:1 and the words vanished under the pointer. It could not fix it: the repair is a
   * rule, and that session's grant was token values.
   *
   * The integrator added `color: var(--am-ink)` to the `::selection` rule — 15.13:1 against
   * that tint, and the one foreground safe on every surface selection can land on.
   *
   * **This row's removal was forced by the guard, not noticed by a person.** The repair made
   * `every registered pair is still produced and still below its threshold` go red, which is
   * the both-directions check doing exactly what §4.2's M4 mutation predicted. A one-way
   * register would have kept a row describing a defect that no longer exists, and the next
   * reader would have believed it.
   */
  {
    key: 'edge|--am-line|--am-surface|-|border',
    themes: ['light', 'dark'],
    why:
      '`--am-line` at 1.26:1 on `--am-surface` in the light palette and 1.44:1 in the ' +
      'dark one. It is a separator at forty sites and the ONLY boundary at three ' +
      'interactive ones whose fill does not distinguish them from the page: the finding ' +
      'row, the evidence page tabs and the page-action links. 1.4.11 reaches those three. ' +
      'Raising it needs `--am-line-strong`\u2019s own territory in EITHER palette — a ' +
      'three-level border scale cannot carry two levels at the 1.4.11 ceiling — and it ' +
      'would darken (or lighten) every card, table rule and divider in the tree. That is ' +
      'one scale decision, it has the same answer in both themes, and `W33-THEME` did not ' +
      'take it either. W32-CONTRAST §3.',
  },
  {
    key: 'edge|--am-line|--am-surface|hover|border',
    themes: ['light', 'dark'],
    why:
      'The same token on the same three controls, hovered, in both palettes. 1.4.11 covers ' +
      'states as well as components, so the hovered boundary is in scope for the same ' +
      'reason and is left for the same reason. The hover CHANGE is carried by ' +
      '`--am-line-strong` and by `--am-accent`, both of which clear 3:1 in both themes; ' +
      'only this resting edge does not.',
  },
  {
    key: 'edge|--am-line|--am-surface|focus-visible|border',
    themes: ['light', 'dark'],
    why:
      'The same token, focused, in both palettes. What indicates focus is the ' +
      '`--am-accent` outline — 7.62:1 light, 7.67:1 dark — which passes and is the thing ' +
      '2.4.7 and 1.4.11 actually ask for here; this row is the resting border still ' +
      'showing underneath it, and repairing it would change nothing a keyboard user can see.',
  },
  {
    key: 'edge|--am-line|--am-surface|active|border',
    themes: ['light', 'dark'],
    why:
      'The same token, on the finding row while the pointer is down, in both palettes. The ' +
      'active state is indicated by the shadow dropping to `--am-shadow-0`, not by this ' +
      'border, and the row is `--am-accent-light` with an inset `--am-accent` rail once ' +
      'selected. Same token, same scale decision, same owner. W32-CONTRAST §3.',
  },
];

/** Is this pair excused in this palette? A pair excused in one is not excused in the other. */
function isRegistered(key: string, theme: Theme): boolean {
  return REGISTERED.some((row) => row.key === key && row.themes.includes(theme));
}

// ------------------------------------------------------------------------- the measurement

function everyPair(theme: Theme): Map<string, Occurrence & { sites: string[] }> {
  const globals = readFileSync(GLOBALS, 'utf8');
  const tokens = palette(globals, theme);
  const rules = [...parseRules(globals, 'globals.css'), ...moduleRules()];
  const all = census(screens(), rules, tokens);
  for (const [key, occurrence] of declaredPairs(rules)) {
    if (!all.has(key)) all.set(key, occurrence);
  }
  return all;
}

function hexFor(foreground: string, backdrop: string, tokens: ReadonlyMap<TokenName, string>): string | null {
  const [token, percent] = foreground.split('@');
  const value =
    percent === undefined
      ? `var(${token})`
      : `color-mix(in srgb, var(${token}) ${percent.replace('%', '')}%, transparent)`;
  const colour = readColour(value);
  return colour ? resolve(colour, tokens, backdrop, backdrop) : null;
}

interface Measured {
  readonly key: string;
  readonly occurrence: Occurrence & { sites: string[] };
  readonly ratio: number;
  readonly threshold: number | null;
}

/**
 * Rendering thirty screens twice is the cost of a second palette, so each palette is
 * rendered once and the result kept. Nothing here mutates a `Measured`.
 */
const MEASURED = new Map<Theme, Measured[]>();

function measured(theme: Theme): Measured[] {
  const cached = MEASURED.get(theme);
  if (cached) return cached;
  const tokens = palette(readFileSync(GLOBALS, 'utf8'), theme);
  const rows = [...everyPair(theme)].map(([key, occurrence]) => {
    const backdrop = tokens.get(occurrence.background) as string;
    const foreground = hexFor(occurrence.foreground, backdrop, tokens);
    return {
      key,
      occurrence,
      ratio: foreground === null ? Number.NaN : contrastRatio(foreground, backdrop),
      threshold: thresholdFor(occurrence),
    };
  });
  MEASURED.set(theme, rows);
  return rows;
}

// ======================================================================= the formula itself

describe('the formula is WCAG 2.1 and not an approximation of it', () => {
  it('reproduces the values the specification states outright', () => {
    // WCAG 2.1 gives black-on-white as 21:1 and identical colours as 1:1.
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 10);
    expect(contrastRatio('#777777', '#777777')).toBeCloseTo(1, 10);
    // The ratio is symmetric: which one is "the text" does not change it.
    expect(contrastRatio('#16191d', '#ffffff')).toBeCloseTo(contrastRatio('#ffffff', '#16191d'), 10);
    // `#767676` on white is the canonical 4.5 boundary quoted throughout WCAG's own
    // examples. Deriving it from a literal the module does not hold is what makes this
    // a check of the arithmetic rather than a restatement of it.
    expect(contrastRatio('#767676', '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#777777', '#ffffff')).toBeLessThan(4.5);
    // The linearisation kink at 0.03928 is the part an approximation gets wrong.
    expect(relativeLuminance('#0a0a0a')).toBeCloseTo(0.0030352698, 9);
  });
});

// ============================================================================ the census

describe('the census is taken over rendered screens, not over a list', () => {
  it('reaches enough of the application to be worth calling a census', () => {
    const rendered = screens();
    expect(rendered.length).toBeGreaterThanOrEqual(25);
    const pairs = everyPair('light');
    expect(pairs.size).toBeGreaterThanOrEqual(90);
    // Every page and every widget in `web/src` renders into it.
    const names = rendered.map((s) => s.name).join(' ');
    for (const screen of [
      'AppFrame', 'ProjectsPage', 'ProjectDetailPage', 'VersionDetailPage',
      'DocumentDetailPage', 'RunPage', 'ReviewPage', 'RunProgress', 'ProjectList',
      'DocumentList', 'VersionList', 'RunList', 'UploadPanel', 'FindingList',
      'EvidenceViewer', 'DecisionPanel', 'DecisionHistory', 'ExportPanel',
    ]) {
      expect({ screen, present: names.includes(screen) }).toEqual({ screen, present: true });
    }
  });

  it('names every selector it declined to evaluate, so a skipped rule is not a passing one', () => {
    everyPair('light');
    everyPair('dark');
    // `:has()` and `:not()` are the two constructs this matcher does not implement.
    //
    // `:has()` guards a rule that sets `border-left-color` on `.am-quotation` to the same
    // `--am-degraded` its own child already declares, so the pair it would contribute is in
    // the census anyway.
    //
    // `:not()` appears exactly once, in `W33-THEME`'s dark block under
    // `@media (prefers-color-scheme: dark)`, and the assertion below is what makes that
    // decline cost nothing: the rule declares CUSTOM PROPERTIES and no colour-bearing
    // property at all, so there is no pair for the matcher to have missed. Its values are
    // measured — they are the dark palette — but through `palette()`, which reads the
    // block, not through the cascade, which cannot match the selector.
    expect(unsupported()).toEqual([
      '.am-quotation:has(.am-quotation__inconsistent)',
      DARK_MEDIA_SELECTOR,
    ]);

    const declined = parseRules(readFileSync(GLOBALS, 'utf8'), 'globals.css').filter(
      (rule) => rule.selector.trim() === DARK_MEDIA_SELECTOR,
    );
    expect(declined.length).toBe(1);
    const properties = [...(declined[0] as (typeof declined)[number]).declarations.keys()];
    expect(properties.length).toBeGreaterThan(0);
    expect(properties.filter((name) => !name.startsWith('--am-'))).toEqual([]);
  });

  it('reads a collocated module through the CASCADE, not only through `declaredPairs`', () => {
    /*
     * Anti-vacuity for the scoping above, and the proof that it was not cosmetic.
     *
     * A module declares `.ordinal` and the markup carries `_ordinal_<hash>`. Parsing the
     * authored file — which is what this census did for two waves — produces selectors that
     * match no element, so a module contributed a pair only when one rule declared both
     * `color` and `background` and `declaredPairs` could read it without a screen. This
     * measures both ways and asserts the difference, so a change that silently went back to
     * the authored names is red rather than merely quieter.
     */
    const globals = readFileSync(GLOBALS, 'utf8');
    const tokens = palette(globals, 'light');
    const authored = MODULES.map((relative) =>
      parseRules(readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf8'), relative),
    ).flat();
    const base = parseRules(globals, 'globals.css');
    const unscoped = census(screens(), [...base, ...authored], tokens);
    const scoped = census(screens(), [...base, ...moduleRules()], tokens);
    const gained = [...scoped.keys()].filter((key) => !unscoped.has(key));
    expect(
      gained.length > 0,
      'Scoping the module class names gains no pair. Either no module declares a colour ' +
        'any more, or the rewrite has stopped matching the markup.',
    ).toBe(true);
    // And the module rules really are class rules: every module names at least one class,
    // so a module file that parsed to nothing is red rather than trivially agreeing.
    expect(MODULES.length).toBeGreaterThan(0);
    for (const relative of MODULES) {
      expect({ relative, rules: parseRules(scopedCss(relative), relative).length > 0 }).toEqual({
        relative,
        rules: true,
      });
      expect({ relative, scoped: /\._[A-Za-z]/.test(scopedCss(relative)) }).toEqual({
        relative,
        scoped: true,
      });
    }
  });

  it('finds the pairs a reading of the token block alone cannot', () => {
    const pairs = everyPair('light');
    // Each of these meets only through inheritance or through an ancestor's background:
    // no rule declares either half beside the other.
    for (const key of [
      // the correlation id under a failed query, inside `.am-state--error`
      'text|--am-ink-soft|--am-failed-light|-|-',
      // the page range inside the SELECTED finding row
      'text|--am-ink-soft|--am-accent-light|-|-',
      // the disclosure marker, and every placeholder
      'text|--am-ink-soft|--am-surface|-|marker',
      'text|--am-ink-soft|--am-paper|-|placeholder',
    ]) {
      expect({ key, found: pairs.has(key) }).toEqual({ key, found: true });
    }
  });

  it('produces the same pairs, and asks the same threshold of each, in both palettes', () => {
    // A second palette must not be a second CENSUS. The elements are the same, the rules
    // are the same and the cascade is the same: only the values differ. If this list is
    // ever non-empty, the two themes are being judged against different questions and the
    // per-theme comparison below would be comparing nothing.
    const light = new Map(measured('light').map((m) => [m.key, m.threshold]));
    const dark = new Map(measured('dark').map((m) => [m.key, m.threshold]));
    const disagreement = [...new Set([...light.keys(), ...dark.keys()])]
      .filter((key) => light.get(key) !== dark.get(key) || light.has(key) !== dark.has(key))
      .map((key) => ({ key, light: light.get(key) ?? 'absent', dark: dark.get(key) ?? 'absent' }));
    expect(
      disagreement,
      'A pair is present, or answers to a threshold, in one palette and not the other. ' +
        'Threshold is a function of the MARKUP (is it text, is it interactive, does its ' +
        'own fill distinguish it) — the only way a palette can change it is by moving a ' +
        'surface across the 3:1 line that decides `fillDistinguishes`. Say which, and why.',
    ).toEqual([]);
  });
});

// ========================================================================== the assertion

describe('every pair that meets on a screen clears the threshold its role asks of it', () => {
  it('holds in BOTH palettes, and names the theme and the ratio of anything that does not', () => {
    // One list over both palettes rather than one test each, so that a failure in the
    // theme nobody is looking at is as loud as a failure in the other.
    const failing = THEMES.flatMap((theme) =>
      measured(theme)
        .filter((m) => m.threshold !== null && !(m.ratio >= m.threshold))
        .filter((m) => !isRegistered(m.key, theme))
        .map((m) => ({
          theme,
          pair: m.key,
          ratio: Number(m.ratio.toFixed(2)),
          needs: m.threshold,
          where: m.occurrence.sites[0],
        })),
    ).sort((a, b) => a.ratio - b.ratio);
    expect(failing).toEqual([]);
  });

  it('measures something in each palette: the thresholds are not all `null`', () => {
    for (const theme of THEMES) {
      const subject = measured(theme).filter((m) => m.threshold !== null);
      expect({ theme, text: subject.filter((m) => m.occurrence.kind === 'text').length >= 30 })
        .toEqual({ theme, text: true });
      expect({ theme, other: subject.filter((m) => m.occurrence.kind !== 'text').length >= 3 })
        .toEqual({ theme, other: true });
    }
  });

  it('the two palettes disagree about at least one ratio, so this is two measurements', () => {
    // Anti-vacuity. If `palette('dark')` silently returned the light values — a typo in the
    // block selector would do it — every assertion above would still pass and would be
    // measuring the light theme twice. This is the check that the second measurement is a
    // second measurement.
    const light = new Map(measured('light').map((m) => [m.key, m.ratio]));
    const differing = measured('dark').filter((m) => Math.abs((light.get(m.key) as number) - m.ratio) > 0.01);
    expect(differing.length).toBeGreaterThan(20);
  });
});

describe('the register is held to the census in both directions, and in both palettes', () => {
  it('every registered row is still produced and still below its threshold, in every theme it names', () => {
    const stale: string[] = [];
    for (const row of REGISTERED) {
      for (const theme of row.themes) {
        const m = measured(theme).find((entry) => entry.key === row.key);
        if (m === undefined || m.threshold === null || m.ratio >= m.threshold) {
          stale.push(`${theme}: ${row.key}`);
        }
      }
    }
    // A row that has been repaired IN ONE PALETTE, or whose rule has gone, must lose that
    // palette from its `themes` rather than keep it as an excuse for the other one.
    expect(
      stale,
      'These rows excuse a pair that now passes, or that no screen produces, in the named ' +
        'palette. Drop the theme from the row — and the row, if it names no theme left.',
    ).toEqual([]);
  });

  it('every registered row names at least one palette and carries a reason a reader can act on', () => {
    for (const row of REGISTERED) {
      expect({ key: row.key, long: row.why.length > 80 }).toEqual({ key: row.key, long: true });
      expect({ key: row.key, themes: row.themes.length > 0 }).toEqual({ key: row.key, themes: true });
      for (const theme of row.themes) expect(THEMES).toContain(theme);
    }
  });
});

// ============================================ the claims each palette makes about its ink

describe('the ink ladder says, per palette, how many levels it actually has', () => {
  /** The luminance a foreground may not cross to stay AA on every text surface it meets. */
  function aaBound(theme: Theme, token: TokenName): { readonly bound: number; readonly luminance: number } {
    const tokens = palette(readFileSync(GLOBALS, 'utf8'), theme);
    const surfaces = measured(theme)
      .filter((m) => m.occurrence.kind === 'text' && m.occurrence.foreground === token)
      .map((m) => relativeLuminance(tokens.get(m.occurrence.background) as string));
    expect(surfaces.length).toBeGreaterThan(0);
    const luminance = relativeLuminance(tokens.get(token) as string);
    // Light theme: dark ink on the DARKEST surface it meets caps it from above.
    // Dark theme: light ink on the LIGHTEST surface it meets floors it from below.
    const surface = theme === 'light' ? Math.min(...surfaces) : Math.max(...surfaces);
    const bound =
      theme === 'light'
        ? (surface + 0.05) / AA_TEXT - 0.05
        : AA_TEXT * (surface + 0.05) - 0.05;
    return { bound, luminance };
  }

  it('the light palette has two visible levels and three tokens, and that is the honest form of it', () => {
    const tokens = palette(readFileSync(GLOBALS, 'utf8'), 'light');
    const soft = tokens.get('--am-ink-soft') as string;
    const muted = tokens.get('--am-ink-muted') as string;
    // It is not `ink-muted` under another name: two tokens, two values.
    expect(soft).not.toEqual(muted);
    // But the separation it has left is not a step anybody can see, and saying so in a
    // test is the point: if a later wave believes it has three ink levels, this fails.
    expect(contrastRatio(soft, muted)).toBeLessThan(1.3);
    // The reason: AA on the darkest surface it carries text over caps it just above
    // `ink-muted`. Derived from the census, so a surface change moves both sides.
    expect(aaBound('light', '--am-ink-soft').luminance).toBeLessThanOrEqual(aaBound('light', '--am-ink-soft').bound);
    expect(aaBound('light', '--am-ink-muted').luminance).toBeLessThan(aaBound('light', '--am-ink-muted').bound);
  });

  it('the dark palette has three, because nothing in it was already pinned', () => {
    const tokens = palette(readFileSync(GLOBALS, 'utf8'), 'dark');
    const ink = tokens.get('--am-ink') as string;
    const muted = tokens.get('--am-ink-muted') as string;
    const soft = tokens.get('--am-ink-soft') as string;
    // Two steps a reader can see, where the light palette has one. This is the assertion
    // that would redden if someone "unified" the two palettes by copying light's values.
    expect(contrastRatio(ink, muted)).toBeGreaterThanOrEqual(1.5);
    expect(contrastRatio(muted, soft)).toBeGreaterThanOrEqual(1.5);
    // And the quietest level is still AA on the LIGHTEST surface it lands on — which in a
    // dark theme is the most ELEVATED one, the opposite end from the light theme's worst
    // case. Copying the reference system's #4d6070 here would be 2.60:1 and this fails.
    const bound = aaBound('dark', '--am-ink-soft');
    expect(bound.luminance).toBeGreaterThanOrEqual(bound.bound);
    expect(relativeLuminance('#4d6070')).toBeLessThan(bound.bound);
  });
});

describe('the border scale says the same thing in both palettes', () => {
  it('the strong line clears 1.4.11 on every surface a control sits on', () => {
    for (const theme of THEMES) {
      const tokens = palette(readFileSync(GLOBALS, 'utf8'), theme);
      const line = tokens.get('--am-line-strong') as string;
      for (const surface of ['--am-paper', '--am-surface', '--am-surface-sunken', '--am-accent-light'] as const) {
        const value = tokens.get(surface) as string;
        expect({ theme, surface, ok: contrastRatio(line, value) >= AA_NON_TEXT })
          .toEqual({ theme, surface, ok: true });
      }
    }
  });

  it('the three border levels are three levels, measured as contrast and not as luminance', () => {
    // `W32-CONTRAST` stated this as a luminance order — soft lighter than base lighter than
    // strong — which is true of a light palette and FALSE of a dark one, where a border
    // becomes visible by getting lighter rather than darker. The property it meant is
    // theme-independent: each level stands out from the surface more than the one below it.
    for (const theme of THEMES) {
      const tokens = palette(readFileSync(GLOBALS, 'utf8'), theme);
      const against = tokens.get('--am-surface') as string;
      const step = (name: TokenName): number => contrastRatio(tokens.get(name) as string, against);
      expect({ theme, ordered: step('--am-line-soft') < step('--am-line') })
        .toEqual({ theme, ordered: true });
      expect({ theme, ordered: step('--am-line') < step('--am-line-strong') })
        .toEqual({ theme, ordered: true });
    }
  });
});
