/**
 * Every `styles.X` a component reads exists in the CSS module it imports.
 *
 * `styling-layer.test.ts` holds that a GLOBAL class named in markup is declared somewhere. A
 * CSS-module class is a property read, `styles.flag`, and nothing held it: `matrix-cell.tsx`
 * read `styles.hintStale` from `version-series.module.css` while the rule lived in
 * `ai-steps.module.css`, so the property was `undefined`, the class string read
 * `"_flag_… undefined"` and the stale AI hint was drawn exactly like a fresh one. The markup
 * was valid, the typecheck was green (a CSS module's default export is an index signature),
 * and no render test could tell a styled element from an unstyled one.
 *
 * The check is a pure function over a component's text and a way to read the module it names,
 * so it is run twice: on literal sources that are deliberately broken (which is what proves it
 * can fail, including the `hintStale` shape) and on every `.tsx`/`.ts` under `web/src`.
 *
 * A module's classes are the ones its SELECTORS declare, outside `:global(...)` (a global class
 * is not exported), plus the names of its `@keyframes`, which a module also exports.
 */

import { readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';

import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import { parseRules } from './contrast';
import { WEB_ROOT, repoRelative, walkFiles } from '../../guards/lib/repo';

const SRC = join(WEB_ROOT, 'src');

/** The class names a module exports: those its selectors declare outside `:global()`, and its keyframes. */
export function exportedClasses(css: string): ReadonlySet<string> {
  const names = new Set<string>();
  for (const keyframes of css.matchAll(/@(?:-[a-z]+-)?keyframes\s+([A-Za-z_][\w-]*)/g)) {
    names.add(keyframes[1] as string);
  }
  for (const rule of parseRules(css, 'module')) {
    // `:global(...)` and what is inside it are not exported; peel it with its balanced parenthesis.
    let selector = '';
    let at = 0;
    for (;;) {
      const start = rule.selector.indexOf(':global(', at);
      if (start < 0) {
        selector += rule.selector.slice(at);
        break;
      }
      selector += rule.selector.slice(at, start);
      let depth = 0;
      let end = start + ':global'.length;
      for (; end < rule.selector.length; end += 1) {
        if (rule.selector[end] === '(') depth += 1;
        else if (rule.selector[end] === ')' && (depth -= 1) === 0) break;
      }
      at = end + 1;
    }
    // A class begins with a letter or underscore: `0.5rem` and `.5s` are not selectors anyway.
    for (const match of selector.matchAll(/\.([A-Za-z_][\w-]*)/g)) names.add(match[1] as string);
  }
  return names;
}

export interface ClassRead {
  /** The component, as a path under the repository. */
  readonly file: string;
  readonly line: number;
  /** The property read, or `null` for a computed read (`styles[kind]`). */
  readonly name: string | null;
  /** The module the read resolves to. */
  readonly module: string;
}

/** Every read of an imported CSS module's export in one source file. */
export function classReads(source: string, file: string): readonly ClassRead[] {
  const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const modules = new Map<string, string>();
  for (const statement of tree.statements) {
    if (
      ts.isImportDeclaration(statement) &&
      ts.isStringLiteral(statement.moduleSpecifier) &&
      statement.moduleSpecifier.text.endsWith('.module.css') &&
      statement.importClause?.name !== undefined
    ) {
      modules.set(
        statement.importClause.name.text,
        resolve(dirname(file), statement.moduleSpecifier.text),
      );
    }
  }
  const reads: ClassRead[] = [];
  const lineOf = (node: ts.Node): number => tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1;
  const visit = (node: ts.Node): void => {
    if (ts.isPropertyAccessExpression(node) && ts.isIdentifier(node.expression)) {
      const module = modules.get(node.expression.text);
      if (module !== undefined) reads.push({ file, line: lineOf(node), name: node.name.text, module });
    } else if (ts.isElementAccessExpression(node) && ts.isIdentifier(node.expression)) {
      const module = modules.get(node.expression.text);
      if (module !== undefined) {
        const key = node.argumentExpression;
        reads.push({
          file,
          line: lineOf(node),
          name: ts.isStringLiteralLike(key) ? key.text : null,
          module,
        });
      }
    } else if (
      ts.isVariableDeclaration(node) &&
      ts.isObjectBindingPattern(node.name) &&
      node.initializer !== undefined &&
      ts.isIdentifier(node.initializer)
    ) {
      // `const { flag, row: r } = styles` reads `flag` and `row`.
      const module = modules.get(node.initializer.text);
      if (module !== undefined) {
        for (const element of node.name.elements) {
          const property = element.propertyName ?? element.name;
          reads.push({
            file,
            line: lineOf(element),
            name: ts.isIdentifier(property) || ts.isStringLiteralLike(property) ? property.text : null,
            module,
          });
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(tree);
  return reads;
}

/** The reads that name a class the module does not export. Computed reads are not decided here. */
export function unknownReads(
  reads: readonly ClassRead[],
  classesOf: (module: string) => ReadonlySet<string>,
): readonly ClassRead[] {
  return reads.filter((read) => read.name !== null && !classesOf(read.module).has(read.name));
}

const CSS_CACHE = new Map<string, ReadonlySet<string>>();
function classesOfModule(path: string): ReadonlySet<string> {
  let known = CSS_CACHE.get(path);
  if (known === undefined) {
    known = exportedClasses(readFileSync(path, 'utf8'));
    CSS_CACHE.set(path, known);
  }
  return known;
}

const describeRead = (read: ClassRead): string =>
  `${repoRelative(read.file)}:${read.line}  styles.${read.name ?? '[…]'}  (${relative(SRC, read.module)})`;

// =========================================================================== the real tree

const SOURCES = walkFiles(SRC, (path) => /\.(?:ts|tsx)$/.test(path) && !path.endsWith('.d.ts'));
const ALL_READS = SOURCES.flatMap((file) => classReads(readFileSync(file, 'utf8'), file));

/**
 * Computed reads cannot be decided by reading the text. Each is named, with the file that owns
 * it; a new one fails until it is added here, and the list may only shrink.
 */
const COMPUTED_READS: readonly string[] = [
  // `isKnownReleaseKind(item.kind) ? styles[item.kind] : styles.dot` -- the kind is checked first.
  'web/src/widgets/version-history/ui/version-history.tsx',
];

describe('every styles.X a component reads is exported by the module it imports', () => {
  it('reads the whole of web/src: many components, many reads, many modules', () => {
    expect(SOURCES.length).toBeGreaterThan(500);
    expect(new Set(ALL_READS.map((read) => read.file)).size, 'components reading a module').toBeGreaterThan(100);
    expect(ALL_READS.length, 'reads of a module class').toBeGreaterThan(1000);
    expect(new Set(ALL_READS.map((read) => read.module)).size, 'modules read').toBeGreaterThan(80);
  });

  it('finds no read of a class its module does not declare', () => {
    const missing = unknownReads(ALL_READS, classesOfModule).map(describeRead).sort();
    expect(
      missing,
      'a component reads a CSS-module class that the module it imports does not declare, so the ' +
        'value is `undefined` and the element is drawn unstyled (the `hintStale` shape). Declare ' +
        'the class in that module, or import the module that has it.',
    ).toEqual([]);
  });

  it('names every computed read, so a read it cannot decide is a read somebody decided', () => {
    const computed = [
      ...new Set(ALL_READS.filter((read) => read.name === null).map((read) => repoRelative(read.file))),
    ].sort();
    expect(computed).toEqual([...COMPUTED_READS].sort());
  });

  it('resolves every module a component imports to a file that exists', () => {
    // `readFileSync` would throw inside `classesOfModule`; the walk above already did it for each read.
    for (const module of new Set(ALL_READS.map((read) => read.module))) {
      expect(classesOfModule(module).size, `${relative(SRC, module)} exports nothing`).toBeGreaterThan(0);
    }
  });
});

// ============================================================================ can it fail?

describe('can fail: the check names each shape of a missing class', () => {
  const MODULE = join(SRC, 'widgets', 'probe', 'ui', 'probe.module.css');
  const FILE = join(SRC, 'widgets', 'probe', 'ui', 'probe.tsx');
  const classes = (css: string) => (module: string): ReadonlySet<string> =>
    module === MODULE ? exportedClasses(css) : new Set<string>();

  it('the hintStale shape: a class declared in another module is undefined here', () => {
    const component = [
      "import styles from './probe.module.css';",
      'export const Hint = () => <span className={`${styles.flag} ${styles.hintStale}`} />;',
    ].join('\n');
    const reads = classReads(component, FILE);
    expect(reads.map((read) => [read.name, read.module])).toEqual([
      ['flag', MODULE],
      ['hintStale', MODULE],
    ]);
    const missing = unknownReads(reads, classes('.flag { color: red; }\n'));
    expect(missing.map((read) => read.name)).toEqual(['hintStale']);
    expect(unknownReads(reads, classes('.flag { color: red; }\n.hintStale { font-style: italic; }\n'))).toEqual([]);
  });

  it('reads a bracket, a destructuring and a second module under another local name', () => {
    const component = [
      "import styles from './probe.module.css';",
      "import ownStyles from './other.module.css';",
      "export const A = () => <i className={styles['row-gap']} />;",
      'const { panel, row: renamed } = styles;',
      'export const B = () => <i className={`${panel} ${renamed} ${ownStyles.card}`} />;',
      'export const C = (kind: string) => <i className={styles[kind]} />;',
    ].join('\n');
    const reads = classReads(component, FILE);
    expect(reads.map((read) => read.name)).toEqual(['row-gap', 'panel', 'row', 'card', null]);
    const known = classes('.row-gap {}\n.panel {}\n');
    expect(unknownReads(reads, (module) => (module.endsWith('other.module.css') ? new Set() : known(module))).map((r) => r.name)).toEqual(['row', 'card']);
  });

  it('declares what a module exports and not what it only mentions', () => {
    const css = [
      '/* .commented { } */',
      '.a, .b > .c:hover { color: red; }',
      '.d :global(.am-button:hover) { color: red; }',
      ':global(.am-gone) .e { margin: 0.5rem; }',
      '@media (max-width: 800px) { .f { gap: 0.25rem; } }',
      '@keyframes spin { from { opacity: 0; } to { opacity: 1; } }',
      '.g { background: url(x.png); }',
    ].join('\n');
    expect([...exportedClasses(css)].sort()).toEqual(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'spin']);
  });

  it('is not satisfied by a module that exports nothing', () => {
    const reads = classReads("import styles from './probe.module.css'; export const X = () => styles.anything;", FILE);
    expect(unknownReads(reads, classes('')).map((read) => read.name)).toEqual(['anything']);
  });
});
