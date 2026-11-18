/**
 * The section palette: fifteen colours, both palettes, every value measured (`UIP-G-17`, `Г1-C`).
 *
 * A section's colour is a dot (or a bar) on a neutral surface: `--am-section-01` ... `--am-section-15`
 * in `globals.css`, one per section, drawn next to the section's code or name. Colour never carries text
 * (the code stays `--am-ink`), so there is no ink to test. What this file holds is what a graphic that
 * identifies something has to hold, and what a palette of fifteen has to hold to be told apart.
 *
 * WHY A DEDICATED TEST AND NOT THE CENSUS. `contrast.test.ts` measures the pairs a rendered screen puts
 * together, and a dot has no text on it and no `color` of its own, so the census sees no pair in it.
 * This file reads the declarations instead, in the way `avatar-palette.test.ts` does for the avatar.
 *
 * WHAT IT READS. The declarations in `globals.css`, by the block that holds them, never a list written
 * here. The number of tokens it asserts is the number of sections `PROJECT_SECTIONS` has, so a sixteenth
 * section without a token (or a token without a section) is red. The surfaces are read through
 * `palette()` and `scopedPalettes()` of `contrast.ts`: every page is drawn inside `.am-app__main`, which
 * remaps the page, the card and the sunken surface to the showcase values, and the menu's band is
 * `.am-app__bar`'s background, so each surface is measured twice, as the root palette has it and as the
 * frame remaps it, and the lower ratio is the one that counts.
 *
 * WHAT A COLOUR MUST CLEAR, in each of the three palette blocks:
 *
 *   against the page, the card (`--am-paper`), the sunken surface, the menu band and the menu's
 *   current-row tint                                                             3:1  WCAG 1.4.11
 *   one lightness per palette (0.545 light, 0.75 dark, within 0.01), chroma at or under the cap (0.14 plus
 *   the rounding of a hex), a hue outside the muddy 75 to 130 degree band, and the same hue in both themes
 *   an OKLab distance between any two colours and between two neighbours of the menu
 *   (`PROJECT_STRUCTURE_ORDER`) of at least the thresholds below.
 *
 * THE THRESHOLDS, chosen from the measured table (`AM_SECTION_TABLE=1 npm --prefix web test -- --run
 * tests/unit/styles/section-palette.test.ts` prints it). The smallest distance between two of the fifteen
 * is 0.0427 in the light palette and 0.0432 in the dark one: neighbours on the colour wheel, where fifteen
 * colours of one lightness and a chroma the sRGB edge caps at 0.09 in the teals have nowhere else to go
 * (the arc from 138 to 62 degrees has a length of about 0.73 in OKLab, so 14 steps cannot average more than
 * 0.052). `MIN_ANY_TWO` is 0.04, twice the distance of about 0.02 that OKLab takes as the smallest visible
 * difference: any two colours of the palette are told apart side by side, and none is a copy of another.
 * The smallest distance between two NEIGHBOURS of the menu is 0.158 light and 0.163 dark, because the list
 * steps four hues at a time; `MIN_MENU_NEIGHBOURS` is 0.15, about seven times that difference, so two
 * sections one under the other in the menu are told apart at a glance and not only side by side.
 *
 * The distance to the colours of meaning (`--am-failed`, `--am-ok`, `--am-degraded`) is printed in the
 * table and has no threshold: a section may be red-ish, and its dot sits beside a code, never in place
 * of a status.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { PROJECT_SECTIONS, PROJECT_STRUCTURE_ORDER, sectionColourVar } from '@/entities/project';
import type { ProjectSectionCode } from '@/entities/project';

import {
  AA_NON_TEXT,
  DARK_MEDIA_SELECTOR,
  DARK_SELECTOR,
  THEMES,
  contrastRatio,
  palette,
  parseRules,
  readColour,
  scopedPalettes,
} from './contrast';
import type { Theme, TokenName } from './contrast';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const CSS = readFileSync(join(WEB, 'src', 'app', 'globals.css'), 'utf8');

/** Two colours of the palette closer than this are not two colours: twice the smallest visible OKLab difference. */
export const MIN_ANY_TWO = 0.04;
/** Two sections one under the other in the menu must be told apart at a glance. */
export const MIN_MENU_NEIGHBOURS = 0.15;

/** The lightness every colour of a palette sits at, and how far a hex rounded to eight bits may stray from it. */
const LIGHTNESS = { light: 0.545, dark: 0.75 } as const;
const LIGHTNESS_TOLERANCE = 0.01;
/** The chroma cap, with the room one rounded hex needs. */
const CHROMA_CAP = 0.14;
const CHROMA_TOLERANCE = 0.005;
/** The muddy yellow-olive band, in OKLCH degrees: nothing is drawn in it. */
const MUDDY_BAND = { from: 75, to: 130 } as const;
/** One section keeps its hue across the themes, give or take what a rounded hex does to it. */
const HUE_DRIFT_DEGREES = 3;

// ============================================================================ OKLab, OKLCH

type Lab = readonly [number, number, number];

function toLinear(channel: number): number {
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

/** A six-digit hex as OKLab (Ottosson's matrices), the space the distances are measured in. */
export function oklabOf(hex: string): Lab {
  const body = hex.trim().replace(/^#/, '');
  const [r, g, b] = [0, 2, 4].map((at) => toLinear(parseInt(body.slice(at, at + 2), 16) / 255)) as [number, number, number];
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

export function oklabDistance(a: Lab, b: Lab): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

/** Lightness, chroma and hue (degrees) of a hex. */
export function oklchOf(hex: string): readonly [number, number, number] {
  const [l, a, b] = oklabOf(hex);
  return [l, Math.hypot(a, b), ((Math.atan2(b, a) * 180) / Math.PI + 360) % 360];
}

/** The shorter way round the hue circle, in degrees. */
const hueGap = (a: number, b: number): number => {
  const gap = Math.abs(a - b) % 360;
  return gap > 180 ? 360 - gap : gap;
};

// =================================================================== reading the palette

/** The three blocks a palette lives in: the light one, and the dark one written twice. */
export const PALETTE_BLOCKS = [':root', DARK_MEDIA_SELECTOR, DARK_SELECTOR] as const;
type PaletteBlock = (typeof PALETTE_BLOCKS)[number];

const SECTION_TOKEN = /^--am-section-(\d{2})$/;
/** Not a colour: the property a dot reads, declared once in `:root` (`section-colour.test.ts` holds its value). */
const DOT_PROPERTY = '--am-section-colour';

export interface SectionPaletteReading {
  /** Per block, the token number (`01` ...) and its value. */
  readonly blocks: ReadonlyMap<PaletteBlock, ReadonlyMap<string, string>>;
  /** Everything wrong with the declarations, one sentence each. Empty when the palette is whole. */
  readonly problems: readonly string[];
}

const numberOf = (n: number): string => String(n).padStart(2, '0');

function isPaletteBlock(selector: string): selector is PaletteBlock {
  return (PALETTE_BLOCKS as readonly string[]).includes(selector);
}

/** Every `--am-section-NN` declaration in the stylesheet, grouped by block and checked for shape. */
export function readSectionPalette(css: string, count: number): SectionPaletteReading {
  const problems: string[] = [];
  const blocks = new Map<PaletteBlock, Map<string, string>>();

  for (const rule of parseRules(css, 'globals.css')) {
    const selector = rule.selector.trim();
    const declared = [...rule.declarations].filter(([name]) => name.startsWith('--am-section'));
    if (declared.length === 0) continue;
    if (!isPaletteBlock(selector)) {
      problems.push(`${selector} declares ${declared.map(([name]) => name).join(', ')} outside the palette blocks`);
      continue;
    }
    if (blocks.has(selector)) {
      problems.push(`a second ${selector} block declares section tokens`);
      continue;
    }
    const tokens = new Map<string, string>();
    for (const [name, value] of declared) {
      if (name === DOT_PROPERTY) {
        if (selector !== ':root') problems.push(`${selector} declares ${DOT_PROPERTY}, which is declared once, in :root`);
        continue;
      }
      const match = SECTION_TOKEN.exec(name);
      if (match === null) {
        problems.push(`${selector}: ${name} is neither --am-section-NN nor ${DOT_PROPERTY}`);
        continue;
      }
      if (!/^#[0-9a-fA-F]{6}$/.test(value)) {
        problems.push(`${selector}: ${name} is ${value}, not a six-digit hex this measurement can read`);
      }
      tokens.set(match[1] as string, value);
    }
    blocks.set(selector, tokens);
  }

  const everywhere = new Set([...blocks.values()].flatMap((tokens) => [...tokens.keys()]));
  for (const selector of PALETTE_BLOCKS) {
    const tokens = blocks.get(selector);
    if (tokens === undefined) {
      problems.push(`${selector} declares no section token`);
      continue;
    }
    const wanted = Array.from({ length: count }, (_, i) => numberOf(i + 1));
    const found = [...tokens.keys()].sort();
    if (found.join(' ') !== wanted.join(' ')) {
      problems.push(`${selector}: tokens ${found.join(' ')} are not 01 ... ${numberOf(count)}, one per section`);
    }
    for (const number of [...everywhere].sort()) {
      if (!tokens.has(number)) problems.push(`${selector}: no token ${number}, which another block declares`);
    }
  }

  const system = blocks.get(DARK_MEDIA_SELECTOR);
  const chosen = blocks.get(DARK_SELECTOR);
  if (system !== undefined && chosen !== undefined) {
    for (const number of [...new Set([...system.keys(), ...chosen.keys()])].sort()) {
      if (system.get(number) !== chosen.get(number)) problems.push(`token ${number} differs between the two dark blocks`);
    }
  }

  return { blocks, problems };
}

// ================================================================= measuring the palette

/** The token a rule paints its background with, read off the stylesheet. */
function backgroundOfRule(css: string, selector: string): TokenName {
  const rules = parseRules(css, 'globals.css').filter((rule) => rule.selector.trim() === selector);
  const tokens = rules
    .map((rule) => readColour(rule.declarations.get('background') ?? rule.declarations.get('background-color') ?? ''))
    .filter((colour) => colour?.kind === 'token')
    .map((colour) => (colour as { readonly token: TokenName }).token);
  if (tokens.length !== 1) throw new Error(`expected one background token on ${selector}, found ${tokens.length}`);
  return tokens[0] as TokenName;
}

/** What a base token resolves to below a scope that remaps it (`.am-app__main`, `.am-app__bar`), or itself. */
function aliasIn(css: string, scopeSelector: string): (token: TokenName) => TokenName {
  const scope = scopedPalettes(parseRules(css, 'globals.css')).find((one) => one.selectors.includes(scopeSelector));
  if (scope === undefined) throw new Error(`no scoped palette opens at ${scopeSelector}`);
  return (token) => scope.alias.get(token) ?? token;
}

export interface Surface {
  readonly name: string;
  readonly hex: string;
}

/**
 * The surfaces a section dot is drawn on, in one theme: the page, the card, the sunken surface, the menu's
 * band and the tint under the menu's current row, each as the root palette has it and as the frame remaps it.
 */
export function surfacesOf(css: string, theme: Theme): Surface[] {
  const tokens = palette(css, theme);
  const inMain = aliasIn(css, '.am-app__main');
  const inBar = aliasIn(css, '.am-app__bar');
  const band = backgroundOfRule(css, '.am-app__bar');
  const wanted: readonly (readonly [string, TokenName, (token: TokenName) => TokenName])[] = [
    ['page', '--am-surface', inMain],
    ['card', '--am-paper', inMain],
    ['sunken surface', '--am-surface-sunken', inMain],
    ['menu band', band, inBar],
    ['menu current-row tint', '--am-accent-light', inBar],
  ];
  const out: Surface[] = [];
  for (const [name, token, alias] of wanted) {
    const root = tokens.get(token);
    const framed = tokens.get(alias(token));
    if (root === undefined || framed === undefined) throw new Error(`${token} is not a hex colour in the ${theme} palette`);
    out.push({ name: `${name} (${token})`, hex: root });
    if (framed !== root) out.push({ name: `${name} in the frame (${alias(token)})`, hex: framed });
  }
  return out;
}

export interface PaletteRow {
  readonly theme: Theme;
  readonly token: string;
  readonly hex: string;
  readonly lch: readonly [number, number, number];
  /** The lowest ratio against any surface, and the surface that gives it. */
  readonly worst: { readonly ratio: number; readonly surface: string };
}

/** Every section token of one theme, as the cascade resolves it, with its lowest ratio against the surfaces. */
export function measureSectionPalette(css: string, theme: Theme, extra: readonly string[] = []): PaletteRow[] {
  const tokens = palette(css, theme);
  const surfaces = surfacesOf(css, theme);
  const names = [...tokens.keys()].filter((name) => SECTION_TOKEN.test(name)).sort();
  return [...names, ...extra].map((token) => {
    const hex = tokens.get(token as TokenName);
    if (hex === undefined) throw new Error(`${token} is not declared in the ${theme} palette`);
    let worst = { ratio: Infinity, surface: '' };
    for (const surface of surfaces) {
      const ratio = contrastRatio(hex, surface.hex);
      if (ratio < worst.ratio) worst = { ratio, surface: surface.name };
    }
    return { theme, token, hex, lch: oklchOf(hex), worst };
  });
}

/** Every token under the 3:1 a graphic needs against a surface, one sentence each. */
export function contrastFailures(rows: readonly PaletteRow[]): string[] {
  return rows
    .filter((row) => !(row.worst.ratio >= AA_NON_TEXT))
    .map((row) => `${row.theme} ${row.token} (${row.hex}) is ${row.worst.ratio.toFixed(2)}:1 on the ${row.worst.surface}, under ${AA_NON_TEXT}:1`);
}

/** What a palette must be to be a derived one, not a picked one, one sentence each. */
export function derivationFailures(rows: readonly PaletteRow[]): string[] {
  const out: string[] = [];
  for (const row of rows) {
    const [l, c, h] = row.lch;
    const at = `${row.theme} ${row.token} (${row.hex})`;
    if (Math.abs(l - LIGHTNESS[row.theme]) > LIGHTNESS_TOLERANCE) {
      out.push(`${at}: lightness ${l.toFixed(3)} is not ${LIGHTNESS[row.theme]} within ${LIGHTNESS_TOLERANCE}`);
    }
    if (c > CHROMA_CAP + CHROMA_TOLERANCE) out.push(`${at}: chroma ${c.toFixed(3)} is over the cap ${CHROMA_CAP}`);
    if (h >= MUDDY_BAND.from && h <= MUDDY_BAND.to) {
      out.push(`${at}: hue ${h.toFixed(0)} is inside the muddy ${MUDDY_BAND.from} to ${MUDDY_BAND.to} degree band`);
    }
  }
  return out;
}

/** A section keeps its hue from one theme to the other. */
export function hueDriftFailures(light: readonly PaletteRow[], dark: readonly PaletteRow[]): string[] {
  const out: string[] = [];
  for (const row of light) {
    const other = dark.find((candidate) => candidate.token === row.token);
    if (other === undefined) continue;
    const gap = hueGap(row.lch[2], other.lch[2]);
    if (gap > HUE_DRIFT_DEGREES) out.push(`${row.token}: hue ${row.lch[2].toFixed(0)} light and ${other.lch[2].toFixed(0)} dark, ${gap.toFixed(1)} degrees apart`);
  }
  return out;
}

/** The token a section wears, read through the public function the menu and the screens use. */
export function tokenOfCode(code: ProjectSectionCode): string {
  const match = /^var\((--am-section-\d\d)\)$/.exec(sectionColourVar(code));
  if (match === null) throw new Error(`${code} does not read a section token`);
  return match[1] as string;
}

export interface DistanceReading {
  readonly smallest: { readonly value: number; readonly pair: readonly [string, string] };
  readonly neighbours: readonly { readonly codes: readonly [string, string]; readonly tokens: readonly [string, string]; readonly value: number }[];
}

/** The smallest distance between two of the colours, and the distance between each two neighbours of the menu. */
export function measureDistances(
  rows: readonly PaletteRow[],
  order: readonly ProjectSectionCode[],
  tokenOf: (code: ProjectSectionCode) => string,
): DistanceReading {
  const lab = new Map(rows.map((row) => [row.token, oklabOf(row.hex)] as const));
  const at = (token: string): Lab => {
    const found = lab.get(token);
    if (found === undefined) throw new Error(`${token} is not in the palette`);
    return found;
  };
  let smallest: DistanceReading['smallest'] = { value: Infinity, pair: ['', ''] };
  for (let i = 0; i < rows.length; i += 1) {
    for (let j = i + 1; j < rows.length; j += 1) {
      const [a, b] = [rows[i] as PaletteRow, rows[j] as PaletteRow];
      const value = oklabDistance(at(a.token), at(b.token));
      if (value < smallest.value) smallest = { value, pair: [a.token, b.token] };
    }
  }
  const neighbours = order.slice(1).map((code, i) => {
    const previous = order[i] as ProjectSectionCode;
    const tokens: readonly [string, string] = [tokenOf(previous), tokenOf(code)];
    return { codes: [previous, code] as const, tokens, value: oklabDistance(at(tokens[0]), at(tokens[1])) };
  });
  return { smallest, neighbours };
}

export function distanceFailures(theme: Theme, reading: DistanceReading): string[] {
  const out: string[] = [];
  if (!(reading.smallest.value >= MIN_ANY_TWO)) {
    out.push(`${theme} ${reading.smallest.pair.join(' and ')} are ${reading.smallest.value.toFixed(3)} apart in OKLab, under ${MIN_ANY_TWO}`);
  }
  for (const next of reading.neighbours) {
    if (!(next.value >= MIN_MENU_NEIGHBOURS)) {
      out.push(
        `${theme} ${next.codes.join(' and ')} (${next.tokens.join(' and ')}) are neighbours in the menu and ${next.value.toFixed(3)} apart in OKLab, under ${MIN_MENU_NEIGHBOURS}`,
      );
    }
  }
  return out;
}

// =============================================================== the measured table

const f = (value: number, digits = 3): string => value.toFixed(digits);
const lchText = (lch: readonly [number, number, number]): string => `${f(lch[0])} ${f(lch[1])} ${lch[2].toFixed(0)}`;

/** The table the report quotes: every code, its token, the colour in both themes, the ratio, the neighbour distance. */
export function sectionTable(css: string): string {
  const light = measureSectionPalette(css, 'light');
  const dark = measureSectionPalette(css, 'dark');
  const lightDistance = measureDistances(light, PROJECT_STRUCTURE_ORDER, tokenOfCode);
  const darkDistance = measureDistances(dark, PROJECT_STRUCTURE_ORDER, tokenOfCode);
  const lines = [
    '| menu place | code | token | light | light OKLCH | light min ratio | dark | dark OKLCH | dark min ratio | to the previous in the menu, light / dark |',
    '|---|---|---|---|---|---|---|---|---|---|',
  ];
  PROJECT_STRUCTURE_ORDER.forEach((code, place) => {
    const token = tokenOfCode(code);
    const l = light.find((row) => row.token === token) as PaletteRow;
    const d = dark.find((row) => row.token === token) as PaletteRow;
    const previous = place === 0 ? '-' : `${f((lightDistance.neighbours[place - 1] as { value: number }).value)} / ${f((darkDistance.neighbours[place - 1] as { value: number }).value)}`;
    lines.push(
      `| ${place + 1} | ${code} | ${token} | ${l.hex} | ${lchText(l.lch)} | ${f(l.worst.ratio, 2)} | ${d.hex} | ${lchText(d.lch)} | ${f(d.worst.ratio, 2)} | ${previous} |`,
    );
  });
  lines.push(
    '',
    `smallest distance between two colours: light ${f(lightDistance.smallest.value, 4)} (${lightDistance.smallest.pair.join(', ')}), dark ${f(darkDistance.smallest.value, 4)} (${darkDistance.smallest.pair.join(', ')})`,
    `smallest distance between menu neighbours: light ${f(Math.min(...lightDistance.neighbours.map((n) => n.value)))}, dark ${f(Math.min(...darkDistance.neighbours.map((n) => n.value)))}`,
    '',
    '| token | light: failed / ok / degraded / neutral | dark: failed / ok / degraded / neutral |',
    '|---|---|---|',
  );
  const meaning = ['--am-failed', '--am-ok', '--am-degraded', '--am-inert'] as const;
  const distances = (theme: Theme, rows: readonly PaletteRow[]): Map<string, string> => {
    const tokens = palette(css, theme);
    return new Map(
      rows.map((row) => [row.token, meaning.map((name) => f(oklabDistance(oklabOf(row.hex), oklabOf(tokens.get(name) as string)))).join(' / ')] as const),
    );
  };
  const [lightMeaning, darkMeaning] = [distances('light', light), distances('dark', dark)];
  for (const row of light) lines.push(`| ${row.token} | ${lightMeaning.get(row.token)} | ${darkMeaning.get(row.token)} |`);
  const nearest = (theme: Theme, rows: readonly PaletteRow[]): string => {
    const tokens = palette(css, theme);
    return meaning
      .slice(0, 3)
      .map((name) => {
        const best = rows
          .map((row) => ({ token: row.token, d: oklabDistance(oklabOf(row.hex), oklabOf(tokens.get(name) as string)) }))
          .sort((a, b) => a.d - b.d)[0] as { token: string; d: number };
        return `${name} nearest ${best.token} at ${f(best.d)}`;
      })
      .join('; ');
  };
  lines.push('', `light: ${nearest('light', light)}`, `dark: ${nearest('dark', dark)}`);
  return lines.join('\n');
}

// =========================================================== editing a copy, in memory

/** The stylesheet with one declaration in one block replaced (or removed, for `null`). */
function withDeclaration(css: string, block: PaletteBlock, name: string, value: string | null): string {
  const escaped = block.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const head = new RegExp(`(^|\\n)[ \\t]*${escaped}\\s*\\{`).exec(css);
  if (head === null) throw new Error(`no ${block} block`);
  const start = head.index + head[0].length;
  const end = css.indexOf('}', start);
  const body = css.slice(start, end);
  const line = new RegExp(`\\n[ \\t]*${name}\\s*:[^;]*;`);
  if (!line.test(body)) throw new Error(`${name} is not declared in ${block}`);
  const edited = body.replace(line, value === null ? '' : `\n  ${name}: ${value};`);
  return css.slice(0, start) + edited + css.slice(end);
}

// ================================================================================== tests

const COUNT = PROJECT_SECTIONS.length;

describe('the section palette is whole, and it is as large as the catalogue', () => {
  const reading = readSectionPalette(CSS, COUNT);

  it('declares exactly one token per section, 01 ... 15, in each of the three blocks', () => {
    expect(COUNT).toBe(15);
    expect(reading.problems).toEqual([]);
    const expected = Array.from({ length: COUNT }, (_, i) => numberOf(i + 1));
    for (const block of PALETTE_BLOCKS) {
      expect({ block, numbers: [...(reading.blocks.get(block)?.keys() ?? [])].sort() }).toEqual({ block, numbers: expected });
    }
  });

  it('the two dark blocks carry the same values', () => {
    const entries = (block: PaletteBlock) => [...(reading.blocks.get(block) ?? new Map())].sort();
    expect(entries(DARK_MEDIA_SELECTOR)).toEqual(entries(DARK_SELECTOR));
  });

  it('the dark values are not the light ones', () => {
    const light = reading.blocks.get(':root') as ReadonlyMap<string, string>;
    const dark = reading.blocks.get(DARK_SELECTOR) as ReadonlyMap<string, string>;
    expect([...light].filter(([number, value]) => dark.get(number) === value)).toEqual([]);
  });

  it('can fail: a token missing from one dark block, the blocks drifting, a token outside them, a count that is not the catalogue', () => {
    const missing = readSectionPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-section-07', null), COUNT);
    expect(missing.problems).toContain(`${DARK_SELECTOR}: tokens ${Array.from({ length: COUNT }, (_, i) => numberOf(i + 1)).filter((n) => n !== '07').join(' ')} are not 01 ... 15, one per section`);
    expect(missing.problems).toContain(`${DARK_SELECTOR}: no token 07, which another block declares`);
    expect(missing.problems).toContain('token 07 differs between the two dark blocks');

    const drifted = readSectionPalette(withDeclaration(CSS, DARK_MEDIA_SELECTOR, '--am-section-03', '#111111'), COUNT);
    expect(drifted.problems).toEqual(['token 03 differs between the two dark blocks']);

    const stray = readSectionPalette(`${CSS}\n.am-x { --am-section-16: #000000; }\n`, COUNT);
    expect(stray.problems).toEqual(['.am-x declares --am-section-16 outside the palette blocks']);

    const hexless = readSectionPalette(withDeclaration(CSS, ':root', '--am-section-02', 'rebeccapurple'), COUNT);
    expect(hexless.problems).toEqual([':root: --am-section-02 is rebeccapurple, not a six-digit hex this measurement can read']);

    // A section added to the catalogue without a token: sixteen sections, fifteen tokens.
    const grown = readSectionPalette(CSS, COUNT + 1);
    expect(grown.problems.length).toBe(PALETTE_BLOCKS.length);
    expect(grown.problems[0]).toContain('are not 01 ... 16, one per section');

    // A whole token gone from the light block: fourteen there, fifteen in the dark ones.
    const gap = readSectionPalette(withDeclaration(CSS, ':root', '--am-section-15', null), COUNT);
    expect(gap.problems).toContain(':root: no token 15, which another block declares');
  });
});

describe('every colour is a derived one: one lightness per palette, a chroma cap, no muddy hue, one hue in both themes', () => {
  const light = measureSectionPalette(CSS, 'light');
  const dark = measureSectionPalette(CSS, 'dark');

  it('measures fifteen colours in each theme', () => {
    expect(light.length).toBe(COUNT);
    expect(dark.length).toBe(COUNT);
  });

  it('holds the lightness, the chroma and the hue band', () => {
    expect([...derivationFailures(light), ...derivationFailures(dark)]).toEqual([]);
  });

  it('keeps each hue from the light palette to the dark one', () => {
    expect(hueDriftFailures(light, dark)).toEqual([]);
  });

  it('can fail: a colour off its lightness, over the chroma cap, in the muddy band, with a hue that moved', () => {
    const pale = measureSectionPalette(withDeclaration(CSS, ':root', '--am-section-05', '#7fc4e2'), 'light');
    expect(derivationFailures(pale).some((line) => line.startsWith('light --am-section-05') && line.includes('lightness'))).toBe(true);

    const loud = measureSectionPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-section-09', '#d684ff'), 'dark');
    expect(derivationFailures(loud).some((line) => line.startsWith('dark --am-section-09') && line.includes('chroma'))).toBe(true);

    const olive = measureSectionPalette(withDeclaration(CSS, ':root', '--am-section-04', '#747526'), 'light');
    expect(derivationFailures(olive).some((line) => line.startsWith('light --am-section-04') && line.includes('muddy'))).toBe(true);

    const moved = measureSectionPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-section-12', '#fa8880'), 'dark');
    expect(hueDriftFailures(light, moved).some((line) => line.startsWith('--am-section-12'))).toBe(true);
  });
});

describe('every colour is a graphic that stands out from every surface it is drawn on, in both palettes', () => {
  it('reads the surfaces off the stylesheet, as the root palette has them and as the frame remaps them', () => {
    const light = surfacesOf(CSS, 'light');
    const names = light.map((surface) => surface.name);
    // `STYLE-ORIG-01`: the frame's remap to the `--am-showcase-*` tokens is now the same colour as the root palette in every surface,
    // so no surface is listed twice; the menu band is the flat side panel (`--am-panel`), no longer the card.
    expect(names).toEqual([
      'page (--am-surface)',
      'card (--am-paper)',
      'sunken surface (--am-surface-sunken)',
      'menu band (--am-panel)',
      'menu current-row tint (--am-accent-light)',
    ]);
    // The frame's remap is the root palette now, in both themes: the page in the frame is the page.
    for (const theme of THEMES) {
      const tokens = palette(CSS, theme);
      expect(tokens.get('--am-surface')).toBe(tokens.get('--am-showcase-bg'));
      expect(tokens.get('--am-paper')).toBe(tokens.get('--am-showcase-card'));
    }
  });

  it('clears 3:1 against the page, the card, the sunken surface, the menu band and the menu tint', () => {
    for (const theme of THEMES) {
      const rows = measureSectionPalette(CSS, theme, ['--am-inert']);
      expect(rows.length).toBe(COUNT + 1);
      expect(contrastFailures(rows)).toEqual([]);
    }
  });

  it('can fail: a colour too pale for the light page, one too dark for the dark card', () => {
    const pale = measureSectionPalette(withDeclaration(CSS, ':root', '--am-section-02', '#9fd2b8'), 'light');
    expect(contrastFailures(pale).some((line) => line.startsWith('light --am-section-02') && line.includes('3:1'))).toBe(true);

    const sunk = measureSectionPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-section-11', '#2a3350'), 'dark');
    expect(contrastFailures(sunk).some((line) => line.startsWith('dark --am-section-11'))).toBe(true);

    // The lowest ratio is the one that counts: a colour that clears the root card and not the frame's tint.
    const tint = measureSectionPalette(withDeclaration(CSS, ':root', '--am-section-03', '#4fb89f'), 'light');
    expect(contrastFailures(tint).some((line) => line.includes('--am-section-03') && line.includes('menu'))).toBe(true);
  });
});

describe('fifteen colours that can be told apart, and neighbours in the menu that are far apart', () => {
  it('keeps any two colours, and every two neighbours of the menu, over the thresholds in both palettes', () => {
    for (const theme of THEMES) {
      const rows = measureSectionPalette(CSS, theme);
      const reading = measureDistances(rows, PROJECT_STRUCTURE_ORDER, tokenOfCode);
      expect(distanceFailures(theme, reading)).toEqual([]);
      expect(reading.neighbours.length).toBe(COUNT - 1);
    }
  });

  it('measures every code of the menu once, and every one wears a token the palette declares', () => {
    expect(new Set(PROJECT_STRUCTURE_ORDER).size).toBe(COUNT);
    expect(PROJECT_STRUCTURE_ORDER.map(tokenOfCode).sort()).toEqual(
      Array.from({ length: COUNT }, (_, i) => `--am-section-${numberOf(i + 1)}`),
    );
  });

  it('can fail: two colours made one, two hues of the same colour, two sections that look alike next to each other', () => {
    const copy = measureSectionPalette(withDeclaration(CSS, ':root', '--am-section-02', '#428228'), 'light');
    const copied = measureDistances(copy, PROJECT_STRUCTURE_ORDER, tokenOfCode);
    expect(distanceFailures('light', copied)).toContain(`light --am-section-01 and --am-section-02 are 0.000 apart in OKLab, under ${MIN_ANY_TWO}`);

    const nearly = measureSectionPalette(withDeclaration(CSS, ':root', '--am-section-02', '#438328'), 'light');
    expect(distanceFailures('light', measureDistances(nearly, PROJECT_STRUCTURE_ORDER, tokenOfCode)).length).toBeGreaterThan(0);

    // The same palette, but the list hands the neighbours colours that are neighbours on the wheel.
    const rows = measureSectionPalette(CSS, 'light');
    const byHue = (code: ProjectSectionCode): string => `--am-section-${numberOf(PROJECT_STRUCTURE_ORDER.indexOf(code) + 1)}`;
    const alike = distanceFailures('light', measureDistances(rows, PROJECT_STRUCTURE_ORDER, byHue));
    expect(alike.length).toBe(COUNT - 1);
    expect(alike[0]).toContain('AR and AI (--am-section-01 and --am-section-02) are neighbours in the menu');
  });
});

describe('the measured table', () => {
  it('has a row per section, and prints on request', () => {
    const table = sectionTable(CSS);
    expect(table).toContain('| 15 | PB |');
    expect(table).toContain('smallest distance between two colours');
    if (process.env.AM_SECTION_TABLE === '1') console.log(`\n${table}\n`);
  });
});
