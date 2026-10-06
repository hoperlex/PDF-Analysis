/**
 * The avatar palette: fourteen pairs, both palettes, every value measured (`W50-SHELL-UI`).
 *
 * WHY A DEDICATED TEST AND NOT THE CENSUS. `contrast.test.ts` measures the pairs a seeded
 * screen happens to render, and an account's colour is a hash of its address: which pairs a
 * screen shows depends on which accounts it holds. So the census can never claim the whole
 * palette, and it cannot ask the second question this palette has at all — whether the
 * CIRCLE stands out from the page, which WCAG 1.4.11 asks of a graphic that identifies
 * something and which no text pair expresses. This file reads every declaration instead.
 *
 * It is a check in the spirit of `R-33` (3:1 for non-text), not a claim that `R-33` already
 * covered the avatar: `R-33` is about borders, and an avatar has none.
 *
 * WHAT IT READS. The declarations themselves, out of `globals.css`, by the block that holds
 * them — never a list written here. The palette size it asserts is the size it FINDS, and the
 * hash is then held to that size, so a fifteenth pair added without the hash (or the hash
 * widened without the pair) is red.
 *
 * WHAT A PAIR MUST CLEAR, in each of the three palette blocks:
 *
 *   the initials on their circle         4.5:1   WCAG 1.4.3 AA; the letters are small text
 *   the circle against the page           3:1    the `body` rule's background
 *   the circle against the bar            3:1    the `.am-app__bar` rule's background, where
 *                                                 the frame puts the account menu's trigger
 *
 * and the ink must be white or near-black, whichever reads better on that circle.
 *
 * The measured table: `AM_AVATAR_TABLE=1 npm --prefix web test -- --run
 * tests/unit/styles/avatar-palette.test.ts`.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { AVATAR_PALETTE_SIZE, avatarColourIndex } from '@/shared/ui';

import {
  AA_NON_TEXT,
  AA_TEXT,
  DARK_MEDIA_SELECTOR,
  DARK_SELECTOR,
  contrastRatio,
  parseRules,
  readColour,
  relativeLuminance,
} from './contrast';
import type { TokenName } from './contrast';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const GLOBALS = join(WEB, 'src', 'app', 'globals.css');
const CSS = readFileSync(GLOBALS, 'utf8');

// =================================================================== reading the palette

/** The three blocks a palette lives in: the light one, and the dark one written twice. */
export const PALETTE_BLOCKS = [':root', DARK_MEDIA_SELECTOR, DARK_SELECTOR] as const;
type PaletteBlock = (typeof PALETTE_BLOCKS)[number];

const AVATAR_NAME = /^--am-avatar-(\d{2})(-ink)?$/;

interface AvatarPair {
  readonly circle?: string | undefined;
  readonly ink?: string | undefined;
}

export interface AvatarPaletteReading {
  /** Per block, the pair number (`01` …) and its two values. */
  readonly blocks: ReadonlyMap<PaletteBlock, ReadonlyMap<string, AvatarPair>>;
  /** Everything wrong with the declarations, one sentence each. Empty when the palette is whole. */
  readonly problems: readonly string[];
}

const pairNumber = (n: number): string => String(n).padStart(2, '0');

function isPaletteBlock(selector: string): selector is PaletteBlock {
  return (PALETTE_BLOCKS as readonly string[]).includes(selector);
}

/** Every `--am-avatar` declaration in the stylesheet, grouped by block and checked for shape. */
export function readAvatarPalette(css: string): AvatarPaletteReading {
  const problems: string[] = [];
  const blocks = new Map<PaletteBlock, Map<string, AvatarPair>>();

  for (const rule of parseRules(css, 'globals.css')) {
    const selector = rule.selector.trim();
    const declared = [...rule.declarations].filter(([name]) => name.startsWith('--am-avatar'));
    if (declared.length === 0) continue;
    if (!isPaletteBlock(selector)) {
      problems.push(`${selector} declares ${declared.map(([name]) => name).join(', ')} outside the palette blocks`);
      continue;
    }
    if (blocks.has(selector)) {
      problems.push(`a second ${selector} block declares avatar tokens`);
      continue;
    }
    const pairs = new Map<string, AvatarPair>();
    for (const [name, value] of declared) {
      const match = AVATAR_NAME.exec(name);
      if (match === null) {
        problems.push(`${selector}: ${name} is neither --am-avatar-NN nor --am-avatar-NN-ink`);
        continue;
      }
      if (!/^#[0-9a-fA-F]{6}$/.test(value)) {
        problems.push(`${selector}: ${name} is ${value}, not a six-digit hex this measurement can read`);
      }
      const number = match[1] as string;
      const pair = pairs.get(number) ?? {};
      pairs.set(number, match[2] === undefined ? { ...pair, circle: value } : { ...pair, ink: value });
    }
    blocks.set(selector, pairs);
  }

  const everywhere = new Set([...blocks.values()].flatMap((pairs) => [...pairs.keys()]));
  for (const selector of PALETTE_BLOCKS) {
    const pairs = blocks.get(selector);
    if (pairs === undefined) {
      problems.push(`${selector} declares no avatar pair`);
      continue;
    }
    const numbers = [...pairs.keys()].sort();
    if (!numbers.every((number, i) => number === pairNumber(i + 1))) {
      problems.push(`${selector}: pairs ${numbers.join(' ')} are not 01 … ${pairNumber(numbers.length)}`);
    }
    for (const [number, pair] of pairs) {
      if (pair.circle === undefined) problems.push(`${selector}: pair ${number} has no circle, --am-avatar-${number}`);
      if (pair.ink === undefined) problems.push(`${selector}: pair ${number} has no ink, --am-avatar-${number}-ink`);
    }
    for (const number of [...everywhere].sort()) {
      if (!pairs.has(number)) problems.push(`${selector}: no pair ${number}, which another block declares`);
    }
  }

  const system = blocks.get(DARK_MEDIA_SELECTOR);
  const chosen = blocks.get(DARK_SELECTOR);
  if (system !== undefined && chosen !== undefined) {
    for (const number of new Set([...system.keys(), ...chosen.keys()])) {
      const a = system.get(number);
      const b = chosen.get(number);
      if (a?.circle !== b?.circle || a?.ink !== b?.ink) {
        problems.push(`pair ${number} differs between the two dark blocks`);
      }
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

/** The surfaces an avatar is drawn on: the page, and the bar that carries the account menu. */
export function surfacesUnderTheAvatar(css: string): { readonly page: TokenName; readonly bar: TokenName } {
  return { page: backgroundOfRule(css, 'body'), bar: backgroundOfRule(css, '.am-app__bar') };
}

/** Every token of one block, as the cascade resolves it: `:root` with the block laid over it. */
function tokensOf(css: string, block: PaletteBlock): Map<string, string> {
  const flat = (selector: string): [string, string][] =>
    parseRules(css, 'globals.css')
      .filter((rule) => rule.selector.trim() === selector)
      .slice(0, 1)
      .flatMap((rule) => [...rule.declarations].filter(([name]) => name.startsWith('--am-')));
  return new Map([...flat(':root'), ...(block === ':root' ? [] : flat(block))]);
}

type InkKind = 'white' | 'near-black' | 'neither';

function inkKind(hex: string): InkKind {
  const luminance = relativeLuminance(hex);
  if (luminance >= 0.95) return 'white';
  if (luminance <= 0.02) return 'near-black';
  return 'neither';
}

export interface AvatarRow {
  readonly block: PaletteBlock;
  readonly pair: string;
  readonly circle: string;
  readonly ink: string;
  readonly text: number;
  readonly page: number;
  readonly bar: number;
  readonly kind: InkKind;
  /** The kind of ink that contrasts more with this circle: white, or black. */
  readonly better: 'white' | 'near-black';
}

export function measureAvatarPalette(css: string): AvatarRow[] {
  const { blocks } = readAvatarPalette(css);
  const surfaces = surfacesUnderTheAvatar(css);
  const rows: AvatarRow[] = [];
  for (const block of PALETTE_BLOCKS) {
    const tokens = tokensOf(css, block);
    const page = tokens.get(surfaces.page) as string;
    const bar = tokens.get(surfaces.bar) as string;
    for (const pair of [...(blocks.get(block)?.keys() ?? [])].sort()) {
      const circle = tokens.get(`--am-avatar-${pair}`);
      const ink = tokens.get(`--am-avatar-${pair}-ink`);
      if (circle === undefined || ink === undefined) continue; // a completeness problem, reported there
      rows.push({
        block,
        pair,
        circle,
        ink,
        text: contrastRatio(ink, circle),
        page: contrastRatio(circle, page),
        bar: contrastRatio(circle, bar),
        kind: inkKind(ink),
        better: contrastRatio(circle, '#ffffff') >= contrastRatio(circle, '#000000') ? 'white' : 'near-black',
      });
    }
  }
  return rows;
}

/** Every pair below a floor, or wearing the wrong ink, one sentence each. */
export function avatarFailures(rows: readonly AvatarRow[]): string[] {
  const out: string[] = [];
  for (const row of rows) {
    const at = `${row.block} pair ${row.pair} (${row.ink} on ${row.circle})`;
    if (!(row.text >= AA_TEXT)) out.push(`${at}: initials ${row.text.toFixed(2)}:1 < ${AA_TEXT}`);
    if (!(row.page >= AA_NON_TEXT)) out.push(`${at}: circle on the page ${row.page.toFixed(2)}:1 < ${AA_NON_TEXT}`);
    if (!(row.bar >= AA_NON_TEXT)) out.push(`${at}: circle on the bar ${row.bar.toFixed(2)}:1 < ${AA_NON_TEXT}`);
    if (row.kind === 'neither') out.push(`${at}: the ink is neither white nor near-black`);
    else if (row.kind !== row.better) out.push(`${at}: the ink is ${row.kind}, and ${row.better} reads better here`);
  }
  return out;
}

/** The measured table, as the report quotes it. */
export function avatarTable(rows: readonly AvatarRow[]): string {
  const theme = (block: PaletteBlock): string => (block === ':root' ? 'light' : 'dark');
  const lines = [
    '| theme | pair | circle | ink | initials : circle | circle : page | circle : bar |',
    '|---|---|---|---|---|---|---|',
  ];
  // The two dark blocks are asserted equal, so the table shows the explicit-choice one.
  for (const row of rows.filter((r) => r.block !== DARK_MEDIA_SELECTOR)) {
    lines.push(
      `| ${theme(row.block)} | ${row.pair} | ${row.circle} | ${row.ink} | ${row.text.toFixed(2)} | ${row.page.toFixed(2)} | ${row.bar.toFixed(2)} |`,
    );
  }
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

describe('the avatar palette is whole, and it is the palette the hash indexes', () => {
  const reading = readAvatarPalette(CSS);

  it('declares exactly the pairs 01 … 14, each with a circle and an ink, in each of the three blocks', () => {
    expect(reading.problems).toEqual([]);
    const expected = Array.from({ length: 14 }, (_, i) => pairNumber(i + 1));
    for (const block of PALETTE_BLOCKS) {
      expect({ block, pairs: [...(reading.blocks.get(block)?.keys() ?? [])].sort() }).toEqual({
        block,
        pairs: expected,
      });
    }
  });

  it('the two dark blocks carry the same values', () => {
    const entries = (block: PaletteBlock) => [...(reading.blocks.get(block) ?? new Map())].sort();
    expect(entries(DARK_MEDIA_SELECTOR)).toEqual(entries(DARK_SELECTOR));
  });

  it("the hash's modulus is the number of pairs the stylesheet declares", () => {
    const found = reading.blocks.get(':root')?.size ?? 0;
    expect(AVATAR_PALETTE_SIZE).toBe(found);
    // Measured, not only declared: over two thousand invented addresses the hash lands on
    // every pair and on nothing past the last one.
    const seen = new Set<number>();
    for (let n = 0; n < 2000; n += 1) seen.add(avatarColourIndex(`account-${n}@example.test`));
    expect([...seen].sort((a, b) => a - b)).toEqual(Array.from({ length: found }, (_, i) => i));
  });

  it('each pair has its rule, and the rule reads that pair and no other', () => {
    const rules = parseRules(CSS, 'globals.css').filter((rule) => /^\.am-avatar--\d{2}$/.test(rule.selector.trim()));
    const numbers = [...(reading.blocks.get(':root')?.keys() ?? [])].sort();
    expect(rules.map((rule) => rule.selector.trim().slice('.am-avatar--'.length)).sort()).toEqual(numbers);
    for (const rule of rules) {
      const number = rule.selector.trim().slice('.am-avatar--'.length);
      expect({
        number,
        background: rule.declarations.get('background'),
        color: rule.declarations.get('color'),
      }).toEqual({
        number,
        background: `var(--am-avatar-${number})`,
        color: `var(--am-avatar-${number}-ink)`,
      });
    }
  });

  it('can fail: a pair missing from one dark block, the blocks drifting, a token outside them', () => {
    const missing = readAvatarPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-avatar-07', null));
    expect(missing.problems).toContain(`${DARK_SELECTOR}: pair 07 has no circle, --am-avatar-07`);
    expect(missing.problems).toContain('pair 07 differs between the two dark blocks');

    const drifted = readAvatarPalette(withDeclaration(CSS, DARK_MEDIA_SELECTOR, '--am-avatar-03-ink', '#111111'));
    expect(drifted.problems).toEqual(['pair 03 differs between the two dark blocks']);

    const stray = readAvatarPalette(`${CSS}\n.am-x { --am-avatar-15: #000000; }\n`);
    expect(stray.problems).toEqual(['.am-x declares --am-avatar-15 outside the palette blocks']);

    // A whole pair gone from the light block: thirteen there, fourteen in the dark ones.
    const gap = readAvatarPalette(
      withDeclaration(withDeclaration(CSS, ':root', '--am-avatar-14', null), ':root', '--am-avatar-14-ink', null),
    );
    expect(gap.problems).toEqual([':root: no pair 14, which another block declares']);
  });
});

describe('every pair is legible in both palettes', () => {
  const rows = measureAvatarPalette(CSS);

  it('measures all fourteen pairs in all three blocks', () => {
    expect(rows.length).toBe(14 * PALETTE_BLOCKS.length);
  });

  it('the initials clear 4.5:1 and the circle clears 3:1 against the page and the bar', () => {
    expect(avatarFailures(rows)).toEqual([]);
  });

  it('reads the surfaces off the stylesheet: the page is `body`, the bar is `.am-app__bar`', () => {
    expect(surfacesUnderTheAvatar(CSS)).toEqual({ page: '--am-surface', bar: '--am-paper' });
  });

  it('can fail: one value edited below each floor, in either theme', () => {
    // A light circle too pale for white initials: the text floor.
    const pale = measureAvatarPalette(withDeclaration(CSS, ':root', '--am-avatar-05', '#8a9a70'));
    expect(avatarFailures(pale).some((f) => f.startsWith(':root pair 05') && f.includes('initials'))).toBe(true);

    // A dark circle too dark to stand out from the dark page: the circle floor.
    const sunk = measureAvatarPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-avatar-11', '#2a3350'));
    expect(avatarFailures(sunk).some((f) => f.startsWith(`${DARK_SELECTOR} pair 11`) && f.includes('page'))).toBe(true);

    // A mid-grey ink: neither white nor near-black.
    const grey = measureAvatarPalette(withDeclaration(CSS, ':root', '--am-avatar-02-ink', '#bbbbbb'));
    expect(avatarFailures(grey).some((f) => f.includes('neither white nor near-black'))).toBe(true);

    // White ink on a dark-theme circle where black reads better.
    const wrong = measureAvatarPalette(withDeclaration(CSS, DARK_SELECTOR, '--am-avatar-09-ink', '#ffffff'));
    expect(avatarFailures(wrong).some((f) => f.includes('near-black reads better'))).toBe(true);
  });

  it('produces the measured table, fourteen rows per theme', () => {
    const table = avatarTable(rows);
    expect(table.split('\n').length).toBe(2 + 14 * 2);
    if (process.env.AM_AVATAR_TABLE === '1') console.log(`\n${table}\n`);
  });
});
