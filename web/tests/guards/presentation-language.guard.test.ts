/**
 * No English prose is left in the presentation this stream owns.
 *
 * `R-18` names **mixed language — finding content in Russian, labels in English** as a
 * defect a manual test must not be allowed to meet. `W31-UI` translated the interface and
 * a later census found what a file-by-file pass leaves behind: Russian titles with English
 * `detail` tails appended to them, Russian `<Field label="Версия">` beside
 * `<Field label="Media type">`, and four upload rules of which two were translated. Those
 * are not findable by reading a diff, because each file **looks** translated.
 *
 * So this guard is not a list of strings. It reads the sources this stream owns, strips
 * comments, extracts every string literal and JSX text node, and fails on anything that
 * reads as an English sentence.
 *
 * **How "an English sentence" is decided, and why not by looking for Latin letters.** A
 * Latin-letter check would fire on `am-badge am-badge--ok`, `application/pdf`, `0.4rem
 * 0.5rem` and every `${a} · ${b}` skeleton, and the allowlist needed to quieten it would
 * grow until it covered the next real sentence too. Instead a string is English prose when
 * it carries **two or more distinct English function words** — `the`, `is`, `not`, `was`,
 * `this`, `and`, … — as whole words. No identifier, class name, media type, CSS length or
 * format skeleton in this tree carries two of those; an English sentence cannot avoid
 * them. The word list is closed and written below, so what this guard can and cannot see
 * is readable rather than inferred.
 *
 * **What it does not cover, said rather than implied.** `generated/**` is produced from
 * `contracts/api/v1/openapi.json` and is never hand-edited, so its JSDoc is out of scope —
 * and nothing renders a JSDoc comment. `shared/ui`, `widgets`, `_pages`, `features`,
 * `_app` and `app` are **not** scanned, because this stream does not own them and a guard
 * over a path its owner cannot satisfy is a guard that gets deleted.
 * `docs/program/W31-RUS.md` §1.2 is the census of what is still English there.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { WEB_ROOT, repoRelative, walkFiles } from './lib/repo';

/** The two trees `W31-RUS` owns. Nothing else is claimed. */
const OWNED = [
  join(WEB_ROOT, 'src', 'entities'),
  join(WEB_ROOT, 'src', 'shared', 'api'),
];

/** Produced from the contract, never hand-edited, and never rendered. */
const GENERATED = join(WEB_ROOT, 'src', 'shared', 'api', 'generated');

/**
 * Closed list. Two distinct members as whole words makes a string English prose.
 *
 * Deliberately function words only: a content word like `run` or `page` appears in
 * identifiers, and a list carrying them would fire on `data-run-outcome`.
 */
const ENGLISH_FUNCTION_WORDS: ReadonlySet<string> = new Set([
  'a', 'an', 'the', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be',
  'been', 'has', 'have', 'had', 'does', 'do', 'did', 'will', 'would', 'could', 'should',
  'may', 'must', 'not', 'no', 'never', 'nothing', 'and', 'or', 'but', 'of', 'to', 'in',
  'on', 'at', 'for', 'from', 'with', 'by', 'it', 'its', 'you', 'your', 'they', 'them',
  'their', 'there', 'here', 'what', 'which', 'when', 'where', 'why', 'how', 'than',
  'then', 'so', 'if', 'as', 'each', 'every', 'any', 'all', 'one', 'two', 'more', 'most',
  'same', 'other', 'another', 'again', 'still', 'only', 'also', 'into', 'out', 'up',
  'down', 'over', 'under', 'about', 'because', 'while', 'until', 'unless', 'rather',
]);

/**
 * Strings that are not prose and would otherwise be judged by their words alone.
 *
 * Exactly one member, and it is here because it is the only place this tree spells an
 * English preposition inside a machine value. A growing allowlist is how this class of
 * guard dies, so a second member is a reason to re-read the guard, not to add a third.
 */
const NOT_PROSE: ReadonlySet<string> = new Set(['no-store, no-cache, must-revalidate']);

/** Replace comments with spaces, preserving offsets, without touching string bodies. */
function stripComments(src: string): string {
  const out: string[] = [];
  let state: null | 'line' | 'block' | 'sq' | 'dq' | 'bt' = null;
  for (let i = 0; i < src.length; ) {
    const c = src[i] as string;
    if (state === null) {
      if (c === '/' && src[i + 1] === '/') { state = 'line'; out.push('  '); i += 2; continue; }
      if (c === '/' && src[i + 1] === '*') { state = 'block'; out.push('  '); i += 2; continue; }
      if (c === "'") state = 'sq';
      else if (c === '"') state = 'dq';
      else if (c === '`') state = 'bt';
      out.push(c); i += 1; continue;
    }
    if (state === 'line') {
      if (c === '\n') { state = null; out.push(c); } else out.push(' ');
      i += 1; continue;
    }
    if (state === 'block') {
      if (c === '*' && src[i + 1] === '/') { state = null; out.push('  '); i += 2; continue; }
      out.push(c === '\n' ? c : ' '); i += 1; continue;
    }
    if (c === '\\') { out.push(src.slice(i, i + 2)); i += 2; continue; }
    if ((state === 'sq' && c === "'") || (state === 'dq' && c === '"') || (state === 'bt' && c === '`')) {
      state = null;
    }
    out.push(c); i += 1;
  }
  return out.join('');
}

const STRING_LITERAL = /'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`/gs;
const JSX_TEXT = />([^<>{}]*[A-Za-z]{2,}[^<>{}]*)</g;

/**
 * Every candidate string a file could put on a screen, with its line.
 *
 * `isTsx` is not a convenience. The JSX-text pattern is `>text<`, and in a `.ts` file
 * that shape is a **generic** — `Map<string, Finding>` closing onto the next token — so
 * scanning `.ts` for JSX text reports type syntax as prose. Measured: it did, on
 * `entities/expert-decision/model/ledger.ts:50`, before this parameter existed.
 */
function candidates(source: string, isTsx: boolean): { readonly line: number; readonly text: string }[] {
  const code = stripComments(source);
  const found: { line: number; text: string }[] = [];
  const lineOf = (offset: number): number => code.slice(0, offset).split('\n').length;
  for (const m of code.matchAll(STRING_LITERAL)) {
    const text = m[1] ?? m[2] ?? m[3] ?? '';
    if (text.length > 0) found.push({ line: lineOf(m.index ?? 0), text });
  }
  if (!isTsx) return found;
  for (const m of code.matchAll(JSX_TEXT)) {
    const text = (m[1] ?? '').trim();
    if (text.length > 0) found.push({ line: lineOf(m.index ?? 0), text });
  }
  return found;
}

/** The distinct English function words a string carries, as whole words. */
export function englishFunctionWords(text: string): string[] {
  const words = text.toLowerCase().match(/[a-z]+/g) ?? [];
  return [...new Set(words.filter((w) => ENGLISH_FUNCTION_WORDS.has(w)))].sort();
}

/** English prose: two or more distinct function words, and not an allowlisted machine value. */
export function readsAsEnglishProse(text: string): boolean {
  if (NOT_PROSE.has(text.trim())) return false;
  // Prose has spaces. `not_a_finding` carries `not` and `a` and is a machine value; the
  // space test separates the two classes without an allowlist that would grow past them.
  if (!/\s/u.test(text.trim())) return false;
  return englishFunctionWords(text).length >= 2;
}

const sources = OWNED.flatMap((root) =>
  walkFiles(root, (p) => (p.endsWith('.ts') || p.endsWith('.tsx')) && !p.startsWith(GENERATED)),
);

describe('the guard can tell prose from a machine value', () => {
  // Anti-vacuity, in the file itself: a guard whose discriminator nobody exercised is a
  // guard nobody has watched work. `reset.sh`'s `grep '\t'` was inert inside its own suite.
  it('calls an English sentence English', () => {
    expect(readsAsEnglishProse('Nothing was published: no version, no manifest.')).toBe(true);
    expect(readsAsEnglishProse('That file is larger than 25 MiB.')).toBe(true);
    expect(readsAsEnglishProse('The run terminated failed. Nothing was published.')).toBe(true);
  });

  it('does not call a class name, a media type or a skeleton English', () => {
    expect(readsAsEnglishProse('am-badge am-badge--ok')).toBe(false);
    expect(readsAsEnglishProse('application/pdf')).toBe(false);
    expect(readsAsEnglishProse('0.4rem 0.5rem')).toBe(false);
    expect(readsAsEnglishProse('use client')).toBe(false);
    expect(readsAsEnglishProse('data-terminal-reason')).toBe(false);
    // Carries `not` and `a`, and is an enum member. The space test, not an allowlist.
    expect(readsAsEnglishProse('not_a_finding')).toBe(false);
    expect(readsAsEnglishProse('Идемпотентность')).toBe(false);
  });

  it('reads the tree it claims to read', () => {
    // A path set, never an exit code. `MEMORY.md`: assert path sets.
    expect(sources.length, 'the owned trees resolved to no source at all').toBeGreaterThan(30);
    const relative = sources.map(repoRelative);
    expect(relative).toContain('web/src/entities/audit-run/model/run-failure.ts');
    expect(relative).toContain('web/src/shared/api/catalog-message.ts');
    expect(relative.filter((p) => p.includes('/generated/'))).toEqual([]);
  });
});

describe('no English prose reaches a reviewer from the paths W31-RUS owns', () => {
  it('finds none in web/src/entities and web/src/shared/api', () => {
    const offences: string[] = [];
    for (const path of sources) {
      const source = readFileSync(path, 'utf8');
      for (const { line, text } of candidates(source, path.endsWith('.tsx'))) {
        if (!readsAsEnglishProse(text)) continue;
        offences.push(`${repoRelative(path)}:${line}  ${JSON.stringify(text.slice(0, 160))}`);
      }
    }
    expect(
      offences,
      'R-18 requires the alpha in Russian. These strings read as English prose and the ' +
        'paths they sit in are W31-RUS’s. Translate them, or if one is genuinely a ' +
        'machine value add it to NOT_PROSE with its reason.',
    ).toEqual([]);
  });
});
