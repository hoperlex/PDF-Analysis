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

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import {
  AA_NON_TEXT,
  census,
  colourTokens,
  contrastRatio,
  declaredPairs,
  parseRules,
  readColour,
  relativeLuminance,
  resolve,
  thresholdFor,
  unsupported,
} from './contrast';
import type { Occurrence, TokenName } from './contrast';
import { screens } from './screens';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const GLOBALS = join(WEB, 'src', 'app', 'globals.css');
const MODULES = [join(WEB, 'src', 'widgets', 'run-progress', 'ui', 'run-progress.module.css')];

// --------------------------------------------------------------------------- the register

interface Registered {
  readonly key: string;
  readonly why: string;
}

/**
 * Below threshold, measured, and knowingly not repaired by `W32-CONTRAST`.
 *
 * Each row is a decision with an owner, not a silence. `docs/program/W32-CONTRAST.md` §3
 * carries the arithmetic for both.
 */
const REGISTERED: readonly Registered[] = [
  {
    key: 'text|--am-ink-inverse|--am-accent-light|-|selection',
    why:
      "`::selection` paints `--am-accent-light` UNDER whatever colour the text already " +
      'has and sets no colour of its own, so selecting a primary button label puts ' +
      '`--am-ink-inverse` (white) on a pale tint at 1.17:1 and the words vanish while ' +
      'the pointer is down. It is a real legibility defect and it is not a token value: ' +
      'the repair is a `color` on the `::selection` rule, and `W32-CONTRAST` may change ' +
      'values, not rules. Reported to the integrator rather than worked around.',
  },
  {
    key: 'edge|--am-line|--am-surface|-|border',
    why:
      '`--am-line` at 1.26:1 on `--am-surface`. It is a separator at forty sites and the ' +
      'ONLY boundary at three interactive ones whose fill does not distinguish them from ' +
      'the page: the finding row, the evidence page tabs and the page-action links. ' +
      '1.4.11 reaches those three. Raising it needs L ≤ 0.2568, which is ' +
      "`--am-line-strong`'s own territory — a three-level border scale cannot carry two " +
      'levels at the 1.4.11 ceiling. That is a scale decision, not a value repair, and ' +
      'it would darken every card, table rule and divider in the tree. W32-CONTRAST §3.',
  },
  {
    key: 'edge|--am-line|--am-surface|hover|border',
    why:
      'The same token on the same three controls, hovered. 1.4.11 covers states as well ' +
      'as components, so the hovered boundary is in scope for the same reason and is ' +
      'left for the same reason. The hover CHANGE is carried by `--am-line-strong` and ' +
      'by `--am-accent`, both of which now clear 3:1; only this resting edge does not.',
  },
  {
    key: 'edge|--am-line|--am-surface|focus-visible|border',
    why:
      'The same token, focused. What indicates focus is the `--am-accent` outline at ' +
      '7.62:1, which passes and is the thing 2.4.7 and 1.4.11 actually ask for here; ' +
      'this row is the resting border still showing underneath it, and repairing it ' +
      'would change nothing a keyboard user can see. Registered for completeness.',
  },
  {
    key: 'edge|--am-line|--am-surface|active|border',
    why:
      'The same token, on the finding row while the pointer is down. The active state is ' +
      'indicated by the shadow dropping to `--am-shadow-0`, not by this border, and the ' +
      'row is `--am-accent-light` with an inset `--am-accent` rail once selected. Same ' +
      'token, same scale decision, same owner. W32-CONTRAST §3.',
  },
];

// ------------------------------------------------------------------------- the measurement

function everyPair(): Map<string, Occurrence & { sites: string[] }> {
  const globals = readFileSync(GLOBALS, 'utf8');
  const tokens = colourTokens(globals);
  const rules = [
    ...parseRules(globals, 'globals.css'),
    ...MODULES.map((path) => parseRules(readFileSync(path, 'utf8'), path)).flat(),
  ];
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

function measured(): Measured[] {
  const tokens = colourTokens(readFileSync(GLOBALS, 'utf8'));
  return [...everyPair()].map(([key, occurrence]) => {
    const backdrop = tokens.get(occurrence.background) as string;
    const foreground = hexFor(occurrence.foreground, backdrop, tokens);
    return {
      key,
      occurrence,
      ratio: foreground === null ? Number.NaN : contrastRatio(foreground, backdrop),
      threshold: thresholdFor(occurrence),
    };
  });
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
    const pairs = everyPair();
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
    everyPair();
    // `:has()` is the one construct this matcher does not implement. The rule it guards
    // sets `border-left-color` on `.am-quotation` to the same `--am-degraded` its own
    // child already declares, so the pair it would contribute is in the census anyway.
    expect(unsupported()).toEqual(['.am-quotation:has(.am-quotation__inconsistent)']);
  });

  it('finds the pairs a reading of the token block alone cannot', () => {
    const pairs = everyPair();
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
});

// ========================================================================== the assertion

describe('every pair that meets on a screen clears the threshold its role asks of it', () => {
  it('holds, and names the ratio of anything that does not', () => {
    const failing = measured()
      .filter((m) => m.threshold !== null && !(m.ratio >= m.threshold))
      .filter((m) => !REGISTERED.some((r) => r.key === m.key))
      .map((m) => ({
        pair: m.key,
        ratio: Number(m.ratio.toFixed(2)),
        needs: m.threshold,
        where: m.occurrence.sites[0],
      }))
      .sort((a, b) => a.ratio - b.ratio);
    expect(failing).toEqual([]);
  });

  it('measures something: the thresholds are not all `null`', () => {
    const subject = measured().filter((m) => m.threshold !== null);
    expect(subject.filter((m) => m.occurrence.kind === 'text').length).toBeGreaterThanOrEqual(30);
    expect(subject.filter((m) => m.occurrence.kind !== 'text').length).toBeGreaterThanOrEqual(3);
  });
});

describe('the register is held to the census in both directions', () => {
  it('every registered pair is still produced and still below its threshold', () => {
    const all = new Map(measured().map((m) => [m.key, m]));
    const stale = REGISTERED.filter((r) => {
      const m = all.get(r.key);
      return m === undefined || m.threshold === null || m.ratio >= m.threshold;
    }).map((r) => r.key);
    // A row that has been repaired, or whose rule has gone, must be DELETED from the
    // register rather than left standing as an excuse for something else.
    expect(stale).toEqual([]);
  });

  it('every registered pair carries a reason a reader can act on', () => {
    for (const row of REGISTERED) {
      expect({ key: row.key, long: row.why.length > 80 }).toEqual({ key: row.key, long: true });
    }
  });
});

// =================================================== the two claims this wave's repair makes

describe('the repaired tokens say what they are for', () => {
  it('the third ink level is AA everywhere, and is no longer a level', () => {
    const tokens = colourTokens(readFileSync(GLOBALS, 'utf8'));
    const soft = tokens.get('--am-ink-soft') as string;
    const muted = tokens.get('--am-ink-muted') as string;
    // It is not `ink-muted` under another name: two tokens, two values.
    expect(soft).not.toEqual(muted);
    // But the separation it has left is not a step anybody can see, and saying so in a
    // test is the point: if a later wave believes it has three ink levels, this fails.
    expect(contrastRatio(soft, muted)).toBeLessThan(1.3);
    // The reason: AA on the darkest surface it carries text over caps it just above
    // `ink-muted`. Derived from the tokens, so a surface change moves both sides.
    const darkestTextSurface = tokens.get('--am-failed-light') as string;
    const ceiling = (relativeLuminance(darkestTextSurface) + 0.05) / 4.5 - 0.05;
    expect(relativeLuminance(soft)).toBeLessThanOrEqual(ceiling);
    expect(relativeLuminance(muted)).toBeLessThan(ceiling);
  });

  it('the strong line clears 1.4.11 on every surface a control sits on', () => {
    const tokens = colourTokens(readFileSync(GLOBALS, 'utf8'));
    const line = tokens.get('--am-line-strong') as string;
    for (const surface of ['--am-paper', '--am-surface', '--am-surface-sunken', '--am-accent-light'] as const) {
      const value = tokens.get(surface) as string;
      expect({ surface, ok: contrastRatio(line, value) >= AA_NON_TEXT }).toEqual({ surface, ok: true });
    }
    // And the three-level border scale still has three levels.
    const soft = tokens.get('--am-line-soft') as string;
    const base = tokens.get('--am-line') as string;
    expect(relativeLuminance(soft)).toBeGreaterThan(relativeLuminance(base));
    expect(relativeLuminance(base)).toBeGreaterThan(relativeLuminance(line));
  });
});
