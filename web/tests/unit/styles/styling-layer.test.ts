/**
 * Three properties of the styling layer that nothing could state before `W31-STYLE`, and
 * that a suite of 772 rendering tests structurally cannot see.
 *
 * The suite renders markup. A stylesheet is not markup, so every defect below was
 * invisible to it, and each of the three was a **real** defect in this tree rather than a
 * hypothetical one:
 *
 *   1. **A class the markup names and the stylesheet does not declare.** `R-18` found 55
 *      of them at `ca16a18` — `am-finding-row` was written as
 *      `className="am-finding-row am-button"`, so with no rule of its own every finding in
 *      the review list rendered as a full-width primary button. The markup was green, the
 *      screen was wrong, and no assertion in this suite could tell the difference.
 *
 *   2. **A rule whose selector matches nothing the markup emits.** `W31-UI` wrote
 *      `.am-evidence__pages .am-button[aria-current='true']` to mark the open page tab.
 *      The widget emits `aria-current="page"` — the correct ARIA value for a tab that is a
 *      page — so the rule matched no element ever and the open page looked exactly like
 *      the closed ones. Both sides were individually defensible, which is why only their
 *      *agreement* is checkable.
 *
 *   3. **A colour written into a rule rather than into a token.** A second theme is a
 *      block that overrides token VALUES; a colour spelled inside a rule is the thing that
 *      makes one expensive later. The reference system this programme is measured against
 *      carries a full `[data-theme="dark"]` token set and defaults to it, so this is not a
 *      hypothetical cost. Nothing here builds a theme, chooses a default or adds a toggle
 *      — that is an owner question. It only keeps the answer cheap.
 *
 * Every check is a pure function over text, so each is exercised twice: against a fixture
 * that is deliberately broken — which is what proves the check *can* fail — and against
 * the real files, which is what proves it is wired to this tree rather than to a fixture.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const SRC = join(WEB, 'src');
const GLOBALS = join(SRC, 'app', 'globals.css');

function walk(dir: string, match: (name: string) => boolean): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) out.push(...walk(path, match));
    else if (match(entry)) out.push(path);
  }
  return out;
}

// --------------------------------------------------------------- 1. declared classes

/** Every `am-…` class name a stylesheet declares. */
export function declaredClasses(css: string): Set<string> {
  return new Set((css.match(/\.am-[a-zA-Z0-9_-]+/g) ?? []).map((m) => m.slice(1)));
}

/**
 * Every `am-…` name the markup names.
 *
 * A name ending in `--` is the literal half of a template such as
 * `` `am-badge am-badge--${toneFor(verdict)}` ``: the modifier is computed, so the source
 * cannot say which one. It is reported as a PREFIX and satisfied by any declared class
 * carrying it — which is the most this check can honestly claim without evaluating the
 * component.
 */
export function referencedClasses(source: string): { names: string[]; prefixes: string[] } {
  const all = new Set(source.match(/am-[a-zA-Z0-9_-]*/g) ?? []);
  const names: string[] = [];
  const prefixes: string[] = [];
  for (const name of all) (name.endsWith('--') ? prefixes : names).push(name);
  return { names: names.sort(), prefixes: prefixes.sort() };
}

export function undeclared(
  referenced: ReturnType<typeof referencedClasses>,
  declared: Set<string>,
): string[] {
  const missing = referenced.names.filter((name) => !declared.has(name));
  for (const prefix of referenced.prefixes) {
    if (![...declared].some((name) => name.startsWith(prefix) && name.length > prefix.length)) {
      missing.push(`${prefix}* (no declared modifier)`);
    }
  }
  return missing.sort();
}

// ------------------------------------------------- 2. the selector / attribute agreement

/** The `aria-current` values a component can emit, read from its source. */
export function emittedAriaCurrent(source: string): string[] {
  return [...new Set((source.match(/aria-current=\{[^}]*?'([a-z]+)'/g) ?? []).map(
    (m) => (/'([a-z]+)'/.exec(m) as RegExpExecArray)[1] as string,
  ))].sort();
}

/** The `aria-current` values a stylesheet selects for. */
export function selectedAriaCurrent(css: string, scope: string): string[] {
  const rules = css.match(new RegExp(`${scope}[^,{]*\\[aria-current='([a-z]+)'\\]`, 'g')) ?? [];
  return [...new Set(rules.map((m) => (/'([a-z]+)'/.exec(m) as RegExpExecArray)[1] as string))].sort();
}

// ------------------------------------------------------------------- 3. colour literals

/**
 * Colour literals outside `:root`.
 *
 * `@media (prefers-reduced-motion)` carries a second `:root`, and a comment may quote a
 * hex value while describing one, so both are removed before the search. What remains is
 * declarations inside rules, which is exactly the thing that makes a second theme cost
 * more than a block of values.
 */
export function colourLiteralsOutsideTokens(css: string): string[] {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const withoutRoot = withoutComments.replace(/:root\s*\{[^}]*\}/g, '');
  return withoutRoot.match(/#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)/g) ?? [];
}

// ================================================================================ tests

describe('a class the markup names is a class the stylesheet declares', () => {
  const globals = readFileSync(GLOBALS, 'utf8');
  const modules = walk(SRC, (n) => n.endsWith('.module.css'));
  const declared = declaredClasses(globals + modules.map((p) => readFileSync(p, 'utf8')).join('\n'));

  it('can fail: the shape R-18 measured 55 of', () => {
    const broken = referencedClasses('<button className="am-finding-row am-button" />');
    expect(undeclared(broken, new Set(['am-button']))).toEqual(['am-finding-row']);
    // And a computed modifier with nothing declared under its prefix.
    const computed = referencedClasses('`am-badge am-badge--${tone}`');
    expect(undeclared(computed, new Set(['am-badge']))).toEqual(['am-badge--* (no declared modifier)']);
    // The same computed modifier IS satisfied by one declared modifier.
    expect(undeclared(computed, new Set(['am-badge', 'am-badge--ok']))).toEqual([]);
  });

  it('holds over every .tsx in web/src', () => {
    const sources = walk(SRC, (n) => n.endsWith('.tsx'));
    expect(sources.length).toBeGreaterThan(30);
    const missing = undeclared(referencedClasses(sources.map((p) => readFileSync(p, 'utf8')).join('\n')), declared);
    expect(missing).toEqual([]);
  });
});

describe('a rule that marks the open page tab selects a value the widget emits', () => {
  const globals = readFileSync(GLOBALS, 'utf8');
  const viewer = readFileSync(join(SRC, 'widgets/evidence-viewer/ui/evidence-viewer.tsx'), 'utf8');

  it('can fail: the exact disagreement W31-UI left', () => {
    const emitted = emittedAriaCurrent("aria-current={candidate === page ? 'page' : undefined}");
    const selected = selectedAriaCurrent(
      ".am-evidence__pages .am-button[aria-current='true'] { color: red; }",
      '\\.am-evidence__pages',
    );
    expect(emitted).toEqual(['page']);
    expect(selected).toEqual(['true']);
    expect(emitted.every((v) => selected.includes(v))).toBe(false);
  });

  it('holds between evidence-viewer.tsx and globals.css', () => {
    const emitted = emittedAriaCurrent(viewer);
    const selected = selectedAriaCurrent(globals, '\\.am-evidence__pages');
    expect(emitted.length).toBeGreaterThan(0);
    for (const value of emitted) expect(selected).toContain(value);
  });
});

describe('every colour is a token read, so a second theme is additive', () => {
  it('can fail: a colour spelled inside a rule', () => {
    expect(
      colourLiteralsOutsideTokens(':root { --am-ok: #1c6b45; }\n.am-badge { color: #1c6b45; }'),
    ).toEqual(['#1c6b45']);
    expect(
      colourLiteralsOutsideTokens('.x { box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); }'),
    ).toEqual(['rgba(0, 0, 0, 0.2)']);
  });

  it('holds over globals.css and every collocated module', () => {
    for (const path of [GLOBALS, ...walk(SRC, (n) => n.endsWith('.module.css'))]) {
      expect({ path, literals: colourLiteralsOutsideTokens(readFileSync(path, 'utf8')) }).toEqual({
        path,
        literals: [],
      });
    }
  });

  it('a collocated module defines no token of its own: it consumes the global ones', () => {
    for (const path of walk(SRC, (n) => n.endsWith('.module.css'))) {
      const declarations = readFileSync(path, 'utf8').match(/^\s*--[a-z-]+\s*:/gm) ?? [];
      expect({ path, declarations }).toEqual({ path, declarations: [] });
    }
  });
});
