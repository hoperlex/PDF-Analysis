/**
 * Every `--am-*` token a stylesheet or a component READS is a token `globals.css` DEFINES.
 *
 * WHY THIS NEEDS ITS OWN GUARD. A custom property that nothing defines does not fail: `var()`
 * of an undefined name resolves to its fallback, or, with no fallback, makes the declaration
 * invalid at computed-value time and the property falls back to its initial value. Neither
 * produces an error, a warning or a red test. `WEB-BORDER-TOKEN-01` found eight module
 * stylesheets drawing twelve borders as `var(--am-border, currentColor)`: `--am-border` is
 * defined nowhere, so every one of them silently resolved to the TEXT colour. The fallback is
 * what hid it — it made the rule look defended while it defended nothing — and the contrast
 * census then measured text on its background and passed, because it reads a border it cannot
 * resolve as `currentColor`.
 *
 * `styling-layer.test.ts` already states the converse (a module defines no token of its own).
 * Together they close the pair: modules only CONSUME tokens, and every token they consume
 * exists. `globals.css` owns the set, so a token a module wants is added there or an existing
 * one is read; a spelling that exists in neither place is what this file refuses.
 *
 * A fallback does not excuse an undefined token. `var(--am-x, #fff)` with `--am-x` undefined is
 * a colour literal spelled inside a rule, which `styling-layer.test.ts` forbids for the same
 * reason, and it is the exact shape that hid the defect above.
 *
 * Every check is a pure function over text, exercised twice: against a deliberately broken
 * fixture (what proves it CAN fail) and against the real tree (what proves it is wired to it).
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
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
  return out.sort();
}

/** One place a token is read. */
export interface TokenReference {
  readonly token: string;
  readonly file: string;
  readonly line: number;
}

/** Block comments blanked, line numbers preserved: a comment may name a token it does not use. */
function withoutBlockComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, (comment) => comment.replace(/[^\n]/g, ' '));
}

/** Every `--am-x:` the stylesheet declares, wherever it declares it (any palette block). */
export function definedTokens(css: string): Set<string> {
  const found = withoutBlockComments(css).matchAll(/(?:^|[\s;{])(--am-[A-Za-z0-9_-]+)\s*:/g);
  return new Set([...found].map((match) => match[1] as string));
}

/**
 * Every `var(--am-x …)` in a source text, with the line it is on.
 *
 * A stylesheet's comments are blanked first; a component's source is read as written, so a
 * token spelled in a string, a template or a `style` object is found wherever it sits.
 */
export function referencedTokens(source: string, file: string, isCss: boolean): TokenReference[] {
  const text = isCss ? withoutBlockComments(source) : source;
  const out: TokenReference[] = [];
  text.split('\n').forEach((lineText, index) => {
    for (const match of lineText.matchAll(/var\(\s*(--am-[A-Za-z0-9_-]+)/g)) {
      out.push({ token: match[1] as string, file, line: index + 1 });
    }
  });
  return out;
}

export function undefinedReferences(
  references: readonly TokenReference[],
  defined: ReadonlySet<string>,
): TokenReference[] {
  return references.filter((reference) => !defined.has(reference.token));
}

const describeReference = (reference: TokenReference): string =>
  `${reference.file}:${reference.line} reads var(${reference.token})`;

/**
 * Tokens that are read and not defined, KNOWN and not repaired by this task. An entry is
 * keyed by token AND file, so a second site reading the same missing token is still red.
 * The list is a ratchet in both directions below: an entry whose site was repaired, or whose
 * token became defined, must be deleted.
 */
const KNOWN_UNDEFINED: readonly { readonly token: string; readonly file: string; readonly why: string }[] = [
];

// ================================================================================ tests

describe('a token a stylesheet or a component reads is a token globals.css defines', () => {
  it('can fail: the shape WEB-BORDER-TOKEN-01 measured, with a fallback that hides it', () => {
    const defined = definedTokens(':root { --am-line: #6e737b; }');
    const references = referencedTokens(
      '.item {\n  border: 1px solid var(--am-line);\n  outline: 1px solid var(--am-border, currentColor);\n}',
      'web/src/widgets/x/ui/x.module.css',
      true,
    );
    expect(undefinedReferences(references, defined).map(describeReference)).toEqual([
      'web/src/widgets/x/ui/x.module.css:3 reads var(--am-border)',
    ]);
  });

  it('can fail: an inline token in a component', () => {
    const defined = definedTokens(':root { --am-line: #6e737b; }');
    const references = referencedTokens(
      "const style = { borderColor: 'var(--am-nope)', color: `var( --am-line )` };",
      'web/src/widgets/x/ui/x.tsx',
      false,
    );
    expect(undefinedReferences(references, defined).map((r) => r.token)).toEqual(['--am-nope']);
  });

  it('reads a definition in any palette block and ignores one inside a comment', () => {
    const css = [
      ':root { --am-a: #111; }',
      "[data-theme='dark'] { --am-b: #222; }",
      '/* --am-ghost: #333; was removed */',
      '.x { color: var(--am-ghost); }',
    ].join('\n');
    expect([...definedTokens(css)].sort()).toEqual(['--am-a', '--am-b']);
    // The same comment is not a reference either: a note about a token is not a use of it.
    expect(referencedTokens('/* var(--am-ghost) */\n.x { color: var(--am-a); }', 'f.css', true)).toEqual([
      { token: '--am-a', file: 'f.css', line: 2 },
    ]);
  });

  describe('over the real tree', () => {
    const defined = definedTokens(readFileSync(GLOBALS, 'utf8'));
    const files = [
      ...walk(SRC, (name) => name.endsWith('.css')),
      ...walk(SRC, (name) => name.endsWith('.tsx') || name.endsWith('.ts')),
    ];
    const references = files.flatMap((path) =>
      referencedTokens(readFileSync(path, 'utf8'), relative(join(WEB, '..'), path), path.endsWith('.css')),
    );
    const undefinedNow = undefinedReferences(references, defined);

    it('is not vacuous: tokens are defined, many are read, and the modules are among the readers', () => {
      expect(defined.size, 'globals.css defined no token').toBeGreaterThan(40);
      expect(defined.has('--am-line'), 'the scan did not read the token block').toBe(true);
      const referenced = new Set(references.map((reference) => reference.token));
      expect(referenced.size, 'no token reference was found at all').toBeGreaterThan(40);
      const readingModules = new Set(
        references.filter((reference) => reference.file.endsWith('.module.css')).map((r) => r.file),
      );
      expect(readingModules.size, 'no collocated module reads a token').toBeGreaterThan(10);
    });

    it('reads no token that globals.css does not define, except the named, reasoned ones', () => {
      const known = new Set(KNOWN_UNDEFINED.map((entry) => `${entry.file}|${entry.token}`));
      const unexpected = undefinedNow.filter(
        (reference) => !known.has(`${reference.file}|${reference.token}`),
      );
      expect(
        unexpected.map(describeReference),
        'these tokens are read and defined nowhere: the declaration silently resolves to its ' +
          'fallback (or to the property default), not to the colour or length intended. Read a ' +
          'token `globals.css` defines, or ask the owner of `web/src/app/**` to add one.',
      ).toEqual([]);
    });

    it('keeps the known-undefined list a ratchet: an entry whose site is repaired is deleted', () => {
      const stillUndefined = new Set(
        undefinedNow.map((reference) => `${reference.file}|${reference.token}`),
      );
      expect(
        KNOWN_UNDEFINED.filter((entry) => !stillUndefined.has(`${entry.file}|${entry.token}`)).map(
          (entry) => `${entry.file} ${entry.token}`,
        ),
        'these entries are excused and no longer needed; delete them',
      ).toEqual([]);
      for (const entry of KNOWN_UNDEFINED) {
        expect(entry.why.length, `${entry.token} carries no reason`).toBeGreaterThan(80);
      }
    });
  });
});
