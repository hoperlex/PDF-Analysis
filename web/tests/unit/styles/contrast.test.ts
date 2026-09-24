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
 *   the PAIRS       are computed by `census()` from forty-nine rendered screens crossed
 *                   with the stylesheet, plus `declaredPairs()` for the rules one server
 *                   render pass structurally cannot reach;
 *   the THRESHOLD   is a function of what the pair IS — 4.5 for text (WCAG 1.4.3 AA),
 *                   3.0 for a graphic that carries meaning (1.4.11), and, since `R-33`,
 *                   3.0 for EVERY border in the product.
 *
 * WHAT `R-33` CHANGED, 2026-09-23. Until wave 42 a border answered to 1.4.11 only where it
 * was the sole thing identifying a control — interactive per the markup, with a fill that
 * did not already distinguish it. That is what the standard asks for, and the owner ruled
 * for more than the standard asks: every border, every state, both palettes. So the
 * threshold no longer asks anything about the element a border surrounds, and
 * `R-33: every border that meets on a screen clears 3:1` asserts the floor a second time
 * WITHOUT consulting the register, because a product-wide floor that a paragraph can
 * excuse is the targeted rule again under another name.
 *
 * So the only hand-maintained set in this file is `REGISTERED`: pairs that are measured,
 * below threshold, and knowingly not repaired this wave, each with its reason. It is
 * held to the census in BOTH directions — a registered pair the screens no longer produce
 * is a failure, exactly as an unregistered pair below threshold is. A stale exemption
 * cannot sit here unnoticed, and a new failure cannot hide behind one. **It is empty as of
 * wave 42**, and the eight rows it carried were deleted by that both-directions check going
 * red after the tokens moved, not by anyone remembering to look.
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
  descendants,
  matches,
  palette,
  parseMarkup,
  parseRules,
  parseSelector,
  readColour,
  splitSelectorList,
  relativeLuminance,
  resolve,
  thresholdFor,
  unsupported,
} from './contrast';
import type { Occurrence, Rule, Theme, TokenName } from './contrast';
import { screens } from './screens';
import { derivedScreens, malformedVariants } from '../screens/route-screens';
import { DOCUMENT_UID, PROJECT_UID, RUN_ID, VERSION_UID } from '../review/fixtures';

/** The identities the census seeds, in the shape `route-screens.ts` asks for. */
const IDENTITIES = {
  projectUid: PROJECT_UID,
  documentUid: DOCUMENT_UID,
  versionUid: VERSION_UID,
  runId: RUN_ID,
};

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

/**
 * The properties that can carry a colour, taken from the cascade's own `applyRule`.
 *
 * Listed here rather than exported from `contrast.ts` because `EDGE_PROPERTIES` is the
 * edges alone; this is that set plus the two fill properties, which is the whole of what
 * a rule can contribute to a pair.
 */
const COLOUR_PROPERTIES = new Set([
  'color', 'background', 'background-color',
  'border', 'border-color', 'border-top', 'border-right', 'border-bottom', 'border-left',
  'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
  'outline', 'outline-color',
]);

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
   * EMPTY, and the eight rows that stood here were deleted by a red test rather than by
   * a tidy-up. Wave 42, `R-33` / `D-81`.
   *
   * What they said, in one sentence repeated eight times: `--am-line` is below 1.4.11 on
   * `--am-surface` and on `--am-paper`, resting and hovered and focused and active, in
   * both palettes; raising it is `--am-line-strong`'s own territory; a three-level border
   * scale cannot carry two levels at the 1.4.11 ceiling; that is a scale decision with an
   * owner and neither `W32-CONTRAST` §3 nor `W33-THEME` nor `W41-BLIND` had the grant to
   * take it. Every one of those clauses was true when it was written.
   *
   * The owner took the decision on 2026-09-23 and took it the wide way: `R-33` raises
   * EVERY border to 3:1 rather than the load-bearing ones, so there is no longer a ceiling
   * for two levels to compete for — the whole scale sits above the floor and the levels are
   * spread across what is left. `docs/program/W42-LOOK.md` §1 carries the arithmetic.
   *
   * THE ROWS WERE NOT DELETED BY THE HAND THAT MOVED THE TOKENS. The values changed first,
   * and `every registered row is still produced and still below its threshold` went red
   * naming all sixteen rows (eight pairs × two palettes) as excuses for pairs that now
   * pass. That is the both-directions check doing exactly what it was built for in wave 32,
   * and it is the second time it has forced a stale exemption out of this file — the first
   * was `::selection`, recorded in the comment `W32-CONTRAST` left above.
   *
   * An empty register is not a weaker guard: every assertion below still runs, and
   * `isRegistered` now excuses nothing at all. The next pair that drops below its threshold
   * fails loudly with nowhere to hide, which is the state this file has been working
   * towards since it was written.
   */
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
    // The floors moved with the census: 25 screens and 90 pairs at wave 32, 49 screens
    // and 148 pairs at wave 41. A floor left at the old figure lets twenty screens be
    // deleted in silence, which is this file's own defect one level up.
    expect(rendered.length).toBeGreaterThanOrEqual(45);
    const pairs = everyPair('light');
    expect(pairs.size).toBeGreaterThanOrEqual(140);
    /*
     * THE LIST OF EIGHTEEN COMPONENT NAMES THAT STOOD HERE IS GONE, and its deletion is
     * the repair rather than a tidy-up.
     *
     * It was a literal checked against a literal: `screens.ts` names a component and this
     * file asserts that `screens.ts` names it. Nothing anywhere asked the TREE. So the
     * knowledge base, the sign-in screen and the change-password screen -- three screens a
     * reviewer meets, two of them the first thing they meet -- were outside this census
     * and this case was green. `OPERATING_CONSTRAINTS.md` §12: the query shared an
     * assumption with its subject, so it could not see the subject being wrong.
     *
     * What replaces it is below, and it asks the stylesheet instead: every rule that
     * declares a colour must be REACHED by some rendered screen. A widget the census does
     * not render fails that by the rules it takes with it, and a screen list nobody
     * maintains cannot make it pass.
     */
    expect(new Set(rendered.map((s) => s.name)).size).toBe(rendered.length);
  });

  /**
   * `D-88`: the census opens every screen the product offers.
   *
   * The case above asks whether the census is BIG. This one asks whether it is the right
   * set, and it asks `web/src/app` rather than `screens.ts` — which is the difference
   * between this and the list of eighteen component names deleted above. The two defects
   * `D-88` names cost differently and this closes both: a screen that brought its own
   * `*.module.css` made the unreached-rule case say something FALSE, and a screen built
   * from the global `am-*` classes moved this census in neither direction and its silence
   * read as coverage.
   */
  it('opens every screen web/src/app offers, derived rather than listed', () => {
    const censused = new Set(screens().map((screen) => screen.name));
    const derived = derivedScreens();
    expect(derived.length, 'the route tree contributed no screens').toBeGreaterThan(10);
    expect(
      derived.filter((screen) => !censused.has(`${screen.name} cold`)).map((s) => s.address).sort(),
      'these addresses exist in `web/src/app` and this census renders no screen for them, ' +
        'so nothing measures the contrast of anything they draw. `screens.ts` takes the ' +
        'derived set; a screen missing here means the loop that consumes it was removed.',
    ).toEqual([]);
    // The refusal shapes too, so the `warning` tone is not reached by accident.
    expect(
      malformedVariants(IDENTITIES).filter((v) => !censused.has(v.name)).map((v) => v.name).sort(),
      'a malformed-segment shape is no longer censused',
    ).toEqual([]);
  });

  /**
   * Every colour-bearing rule in the stylesheets is REACHED by a rendered screen.
   *
   * ## Why this exists, measured at `295ff04` before it was written
   *
   * **31 of the 137 colour-bearing rules in this application were reached by no screen
   * this census renders** — 23% of the surface a file called a census is named after. The
   * screens it renders were a hand-written list, and `D-69` is the seventh consecutive
   * wave in which a guard was **sound and blind**: it rendered, saw, and permitted,
   * because the state that carries the defect was never reached.
   *
   * `D-64` was the same census's previous blindness — it matched **authored** class names
   * while the markup carries the bundler's — and it was repaired in wave 35. This is not
   * that defect returning. It is the layer outside it: the names now resolve, and the
   * screens that would carry them were never rendered.
   *
   * ## What this does not claim
   *
   * A rule this reaches is a rule the census EVALUATES. It is not a claim that the pair
   * passes — `every pair that meets on a screen clears the threshold its role asks of it`
   * is that claim, and it is only as wide as this.
   *
   * Nor is an unreached rule, on its own, a defect in the application. What it IS, always,
   * is a question with two answers the census cannot tell apart — a missing seed or a rule
   * nobody needs — so the list below answers it per entry, in the tree, rather than
   * carrying a count down. Wave 42 read all eleven: three were dead and are deleted, one
   * was a seed this harness could have taken all along, and seven are states a server
   * render pass cannot produce, each naming how its colours are measured instead.
   */
  const UNREACHED_BY_ANY_SCREEN: readonly { readonly selector: string; readonly why: string }[] = [
    /*
     * ELEVEN ENTRIES BECAME SEVEN IN WAVE 42, AND THE COUNT IS THE LEAST INTERESTING PART.
     *
     * `W41-BLIND` took this list from 31 to 11 by rendering screens nobody had rendered,
     * and closed with the sentence that made this wave's work: a rule no screen reaches is
     * either A MISSING SEED or A RULE NOBODY NEEDS, and **from the census's side the two
     * are indistinguishable**. So the eleven were not counted down again. Each was read in
     * `web/src` and given a verdict, which is the only place the distinction exists:
     *
     *   DEAD, deleted this wave (3):
     *     `hr`                  no module renders one -- `grep -rn "<hr" web/src` is empty
     *     `.am-app__context`    declared, rendered by nothing -- measured the same way
     *     `.am-evidence__none`  unreachable on EVERY input, `D-85`; the branch that carried
     *                           it is deleted too, and the invariant that made it dead is
     *                           now asserted in `tests/unit/review/viewer-and-panels.test.ts`
     *
     *   A MISSING SEED, seeded this wave (1):
     *     `.am-app__instance`   `W41-BLIND` reasoned that "a static render pass has no
     *                           environment to read one from". `getInstanceLabel()` reads
     *                           `process.env` in the component body and this harness is a
     *                           node process; `screens.ts` now sets one. The rule was never
     *                           unreachable -- the seed was missing, which is `D-69`'s own
     *                           shape and the reason this list is read rather than counted.
     *
     *   OUT OF REACH OF A SERVER RENDER PASS, and each one says how its colours ARE
     *   measured instead (7, below). None of them is excused for being unrendered: an
     *   entry whose reason is only "it is not rendered" is the defect being laundered,
     *   which is what the assertion below says in as many words.
     */
    {
      selector: '::selection',
      why:
        'A browser pseudo-element on the user\'s own selection highlight. No element in any ' +
        'markup carries it, and no render can produce one: the browser composes it. Its two ' +
        'colours are declared in the same block, so `declaredPairs` measures the pair without ' +
        'markup at all.',
    },
    {
      selector: ".am-theme__option[aria-pressed='true']",
      why:
        'Which theme option is pressed is decided in the browser. `theme-toggle.tsx` starts at ' +
        '`useState<ThemeChoice>(\'system\')` and the stored preference arrives in an EFFECT, ' +
        'which a server render pass does not run, so both options render `aria-pressed="false"` ' +
        'whatever the harness does. Checked rather than assumed this wave. The rule declares ' +
        '`background: var(--am-paper)` and `color: var(--am-ink)` in one block, so the pair it ' +
        'carries is measured by `declaredPairs`; what is unmeasured is only the CASCADE around ' +
        'it, and the pressed option sits on the same surfaces the unpressed one does.',
    },
    {
      selector: '.am-quotation:has(.am-quotation__inconsistent)',
      why:
        '`:has()` is one of the two constructs this matcher does not implement, and it is ' +
        'already named by `unsupported()` one case up. The rule sets `border-left-color` to ' +
        'the same `--am-degraded` its own child declares, so the pair is in the census anyway.',
    },
    {
      selector: '.am-export__disclosure[open] > summary',
      why:
        'A `<details>` is closed until a reader opens it, and the harness cannot fire the ' +
        'event that opens one; `export-panel.tsx` renders it with no `open` attribute and ' +
        'takes no prop that would add one, so this is a browser state rather than a missing ' +
        'seed. The summary in its CLOSED state is censused. The rule declares one colour -- ' +
        '`border-bottom: 1px solid var(--am-line-soft)` -- and that exact pair, ' +
        '`--am-line-soft` on `--am-surface`, is measured at other sites in both palettes, so ' +
        'no pair is missing from the census; the RULE is what is unevaluated.',
    },
    {
      selector: '.am-form__chosen',
      why:
        'Renders only after a file has been chosen, which needs a change event the harness ' +
        'cannot fire. It declares its ink and its tint in the SAME block, so `declaredPairs` ' +
        'measures the pair with no markup — the union of the two censuses is why this costs ' +
        'nothing rather than being excused.',
    },
    {
      selector: '.am-form__problem',
      why:
        'Renders only after a refused submission, which needs a click the harness cannot ' +
        'fire. Declares both halves in one block, so `declaredPairs` measures it; see ' +
        '`.am-form__chosen`.',
    },
    {
      selector: '.am-form__created',
      why:
        'Renders only after a project has been created, which needs a mutation to settle. ' +
        'Declares both halves in one block, so `declaredPairs` measures it; see ' +
        '`.am-form__chosen`.',
    },
  ];

  it('names every colour-bearing rule that NO rendered screen reaches', () => {
    const rules = [
      ...parseRules(readFileSync(GLOBALS, 'utf8'), 'globals.css'),
      ...moduleRules(),
    ].filter((rule) => [...rule.declarations.keys()].some((name) => COLOUR_PROPERTIES.has(name)));
    const elements = screens().flatMap((screen) => descendants(parseMarkup(screen.markup)));

    const unreached: string[] = [];
    for (const rule of rules) {
      const parsed = splitSelectorList(rule.selector)
        .map((one) => parseSelector(one))
        .filter((one): one is NonNullable<typeof one> => one !== null);
      const reached =
        parsed.length > 0 && parsed.some((one) => elements.some((el) => matches(el, one.base)));
      if (!reached) unreached.push(rule.selector.trim());
    }

    const excused = new Set(UNREACHED_BY_ANY_SCREEN.map((entry) => entry.selector));
    // The census has to be worth taking: a stylesheet that parsed to nothing, or a screen
    // list that rendered nothing, would satisfy every line below by having no work to do.
    expect(rules.length, 'no colour-bearing rule parsed at all').toBeGreaterThan(100);
    expect(elements.length, 'the screens rendered no elements').toBeGreaterThan(1000);

    expect(
      unreached.filter((selector) => !excused.has(selector)).sort(),
      'these rules declare a colour and NO screen in `screens.ts` renders an element they ' +
        'match, so their contrast is not measured by anything. Render the screen that ' +
        'carries them. If one truly cannot be rendered, add it to UNREACHED_BY_ANY_SCREEN ' +
        'with the reason — and an entry whose reason is only "it is not rendered" is the ' +
        'defect being laundered.',
    ).toEqual([]);

    // The other direction, so the list is a ratchet and may only shrink. A selector that
    // became reachable and stayed on the list would quietly re-hide the next one.
    expect(
      [...excused].filter((selector) => !unreached.includes(selector)).sort(),
      'these are excused from the census and a screen now reaches them. Delete their ' +
        'entries: a ratchet that keeps a repaired line goes back to proving nothing.',
    ).toEqual([]);

    for (const { selector, why } of UNREACHED_BY_ANY_SCREEN) {
      expect(why.length, `${selector} carries no reason`).toBeGreaterThan(80);
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
          // ALL the sites, not the first. `W44-JUDGE-A` put one failing border on two
          // screens at once and the message named only `blocks`; `workers` never
          // appeared. The verdict was never wrong -- the message was -- and `D-93` is
          // precisely the class where a product-wide regression reads as a local one,
          // because `AppFrame` is on every screen and a reader who sees one name looks
          // at one screen.
          where: m.occurrence.sites,
          screens: new Set(m.occurrence.sites.map((site) => site.split(' ')[0])).size,
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

// ================================================================== R-33: the border floor

describe('R-33: every border that meets on a screen clears 3:1, in both palettes', () => {
  /**
   * The product-wide floor, asserted WITHOUT consulting the register.
   *
   * This is deliberately not a row in `REGISTERED`'s question. The register answers *"is
   * this particular failing pair knowingly excused"*, and for six waves the answer for
   * `--am-line` was yes — eight rows of it, across two fills and four states, every one of
   * them ending in the same sentence: this is a scale decision with an owner. The owner
   * took it on 2026-09-23 (`R-33`, `D-81`) and chose the product-wide change over the
   * targeted one, so the floor is no longer a pair-by-pair negotiation and this assertion
   * is no longer excusable by writing a paragraph.
   *
   * It overlaps `every pair that meets on a screen clears the threshold its role asks of
   * it` by design, and the overlap is not redundancy: that assertion routes through
   * `thresholdFor` and through `isRegistered`, so a future row could excuse a border there.
   * Nothing excuses one here. If a border below 3:1 is ever deliberate again, it takes a
   * ruling that edits this test, not a register entry that slips past it.
   *
   * WHAT COUNTS AS A BORDER: every `edge` occurrence the census produces — the four
   * `border-*` properties and `outline`, on any element, in any state, in either palette.
   * Not graphics, which answer to 1.4.11 for a different reason and already did.
   */
  it('names the theme, the ratio and the site of every border under the floor', () => {
    const under = THEMES.flatMap((theme) =>
      measured(theme)
        .filter((m) => m.occurrence.kind === 'edge')
        .filter((m) => !(m.ratio >= AA_NON_TEXT))
        .map((m) => ({
          theme,
          pair: m.key,
          ratio: Number(m.ratio.toFixed(2)),
          needs: AA_NON_TEXT,
          // ALL the sites, not the first. `W44-JUDGE-A` put one failing border on two
          // screens at once and the message named only `blocks`; `workers` never
          // appeared. The verdict was never wrong -- the message was -- and `D-93` is
          // precisely the class where a product-wide regression reads as a local one,
          // because `AppFrame` is on every screen and a reader who sees one name looks
          // at one screen.
          where: m.occurrence.sites,
          screens: new Set(m.occurrence.sites.map((site) => site.split(' ')[0])).size,
        })),
    ).sort((a, b) => a.ratio - b.ratio || a.pair.localeCompare(b.pair));
    expect(
      under,
      'R-33: every border in this product clears 3:1 against the surface it is drawn on, ' +
        'in BOTH palettes. These do not. The repair is the token, not an exemption: this ' +
        'assertion reads no register.',
    ).toEqual([]);
  });

  it('measures borders at all, so an empty census cannot satisfy the floor', () => {
    // Anti-vacuity, and it is the one this assertion needs most: `.filter(kind === 'edge')`
    // over a census that produced no edges is an empty list agreeing with an empty list.
    for (const theme of THEMES) {
      const edges = measured(theme).filter((m) => m.occurrence.kind === 'edge');
      expect({ theme, edges: edges.length >= 20 }).toEqual({ theme, edges: true });
      // And every one of them is a real measurement rather than a NaN that `>=` swallows.
      expect({ theme, measurable: edges.every((m) => Number.isFinite(m.ratio)) })
        .toEqual({ theme, measurable: true });
    }
  });

  it('asks 3:1 of a border whatever the markup around it says', () => {
    // The ruling's own words -- "not only the load-bearing ones" -- as a property of
    // `thresholdFor` rather than of today's census: a decorative separator, a disabled
    // control's edge and an interactive control's sole boundary all answer to the same
    // number now. Built from a literal occurrence so it stays true when the screens change.
    const edge = (over: Partial<Occurrence>): Occurrence => ({
      kind: 'edge', foreground: '--am-line', background: '--am-paper',
      state: null, pseudo: 'border', site: 'synthetic', interactive: false,
      fillDistinguishes: false, ...over,
    });
    expect(thresholdFor(edge({}))).toBe(AA_NON_TEXT);
    expect(thresholdFor(edge({ interactive: true, fillDistinguishes: true }))).toBe(AA_NON_TEXT);
    expect(thresholdFor(edge({ state: 'disabled' }))).toBe(AA_NON_TEXT);
    expect(thresholdFor(edge({ state: 'hover' }))).toBe(AA_NON_TEXT);
    // Text is untouched by the ruling and still answers to 1.4.3.
    expect(thresholdFor(edge({ kind: 'text' }))).toBe(AA_TEXT);
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
