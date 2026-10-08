/**
 * Guard: every mutation hook under `features/**` is mapped to whether it invalidates the
 * dashboard's one read.
 *
 * `W46-CLIENT`, `C3` (`X-6`/`Y6-a`). `query-keys.ts:165` promises *"every mutation that
 * changes a number this key answers for invalidates it"* — a promise four call sites keep
 * (`uploadDocument`, `startRun`, the run-status poll's terminal reading,
 * `decisionCacheKeys`) and one did not: `useCreateProject` invalidated `projects.all()`
 * only, a separate root namespace `dashboard.summary()` sits outside, so a fresh
 * deployment's first project left `/dashboard` reading *«Проектов пока нет.»* for up to
 * `staleTime: 30_000` after it existed.
 *
 * A render test cannot catch that kind of gap — nothing renders wrong, a query simply
 * never re-fires — so this guard reads the mutation hooks themselves. It does two things
 * together, and both matter:
 *
 *   1. **Discovers** every TypeScript file in a feature's `model/` directory that calls
 *      `useMutation(`,
 *      and refuses to run unless that discovered set is exactly `EXPECTED_INVALIDATION`'s
 *      keys — so a new mutation hook that nobody maps here fails loudly instead of
 *      silently passing by omission.
 *   2. **Checks** each mapped hook against the map's own claim, by reading whether the
 *      hook's source names `queryKeys.dashboard.summary()` directly, or delegates to an
 *      imported `*CacheKeys` helper (the `decisionCacheKeys` shape `append-comment` and
 *      `record-verdict` both use) whose own source does. One level of delegation only,
 *      deliberately: a hook that buries the invalidation two helpers deep is a design this
 *      repository does not have today, and this guard should fail loudly on one that
 *      tries rather than silently walking an unbounded import graph.
 *
 * `export-run` is mapped `false` on purpose, not left out: it downloads a CSV and mutates
 * no number the dashboard reads, so requiring an invalidation from it would be asking the
 * map to lie the other way.
 */

import { existsSync } from 'node:fs';
import { dirname, join, resolve, sep } from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';

const FEATURES_ROOT = join(WEB_ROOT, 'src', 'features');
const DASHBOARD_INVALIDATION = 'queryKeys.dashboard.summary';

function parsed(source: string, kind = ts.ScriptKind.TS): ts.SourceFile {
  return ts.createSourceFile('guard-subject.ts', source, ts.ScriptTarget.Latest, true, kind);
}

function callHasName(node: ts.CallExpression, name: string): boolean {
  return (
    (ts.isIdentifier(node.expression) && node.expression.text === name) ||
    (ts.isPropertyAccessExpression(node.expression) && node.expression.name.text === name)
  );
}

/** True only for an executable call expression; comments and string literals are not syntax nodes. */
function subtreeCalls(root: ts.Node, name: string): boolean {
  let found = false;
  const visit = (node: ts.Node): void => {
    if (ts.isCallExpression(node) && callHasName(node, name)) {
      found = true;
      return;
    }
    if (!found) ts.forEachChild(node, visit);
  };
  visit(root);
  return found;
}

function subtreeCallsExpression(sourceFile: ts.SourceFile, root: ts.Node, expression: string): boolean {
  let found = false;
  const visit = (node: ts.Node): void => {
    if (
      ts.isCallExpression(node) &&
      node.expression.getText(sourceFile).replace(/\s+/g, '') === expression
    ) {
      found = true;
      return;
    }
    if (!found) ts.forEachChild(node, visit);
  };
  visit(root);
  return found;
}

function sourceCalls(source: string, name: string, kind = ts.ScriptKind.TS): boolean {
  const sourceFile = parsed(source, kind);
  return subtreeCalls(sourceFile, name);
}

function subtreeInvalidatesDashboard(sourceFile: ts.SourceFile, root: ts.Node): boolean {
  let found = false;
  const visit = (node: ts.Node): void => {
    if (ts.isCallExpression(node) && callHasName(node, 'invalidateQueries')) {
      if (
        node.arguments.some((argument) =>
          subtreeCallsExpression(sourceFile, argument, DASHBOARD_INVALIDATION),
        )
      ) {
        found = true;
        return;
      }
    }
    if (!found) ts.forEachChild(node, visit);
  };
  visit(root);
  return found;
}

function sourceInvalidatesDashboard(source: string): boolean {
  const sourceFile = parsed(source);
  return subtreeInvalidatesDashboard(sourceFile, sourceFile);
}

function declaredFunctionCallsExpression(source: string, name: string, expression: string): boolean {
  const sourceFile = parsed(source);
  let found = false;
  const visit = (node: ts.Node): void => {
    const namedFunction = ts.isFunctionDeclaration(node) && node.name?.text === name;
    const namedVariable =
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.name.text === name &&
      node.initializer !== undefined &&
      (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer));
    if ((namedFunction || namedVariable) && subtreeCallsExpression(sourceFile, node, expression)) {
      found = true;
      return;
    }
    if (!found) ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  return found;
}

function importedBindings(source: string): ReadonlyArray<{
  exported: string;
  local: string;
  specifier: string;
}> {
  const bindings: Array<{ exported: string; local: string; specifier: string }> = [];
  for (const statement of parsed(source).statements) {
    if (!ts.isImportDeclaration(statement) || !ts.isStringLiteral(statement.moduleSpecifier)) continue;
    const elements = statement.importClause?.namedBindings;
    if (elements === undefined || !ts.isNamedImports(elements)) continue;
    for (const element of elements.elements) {
      bindings.push({
        exported: element.propertyName?.text ?? element.name.text,
        local: element.name.text,
        specifier: statement.moduleSpecifier.text,
      });
    }
  }
  return bindings;
}

/**
 * Every mutation hook under `features/**`, keyed by its path relative to `WEB_ROOT`, and
 * whether it must invalidate the dashboard's one read. `true` is checked positively
 * (the invalidation must be found); `false` is recorded so the hook is not silently
 * unmapped, not asserted as an absence — a hook is free to gain one later.
 */
const EXPECTED_INVALIDATION: Readonly<Record<string, boolean>> = {
  'src/features/edit-profile/model/use-edit-profile.ts': false,
  'src/features/manage-user/model/use-manage-user.ts': false,
  'src/features/mark-release-notes-read/model/use-mark-release-notes-read.ts': false,
  'src/features/decide-registration/model/use-decide-registration.ts': false,
  'src/features/append-comment/model/use-append-comment.ts': true,
  'src/features/create-project/model/use-create-project.ts': true,
  'src/features/export-run/model/use-export-run.ts': false,
  'src/features/record-verdict/model/use-record-verdict.ts': true,
  'src/features/start-run/model/use-start-run.ts': true,
  'src/features/upload-document/model/use-upload-document.ts': true,
};

/** A feature model source with an executable mutation call, independent of its filename. */
function isMutationHook(path: string, source: string): boolean {
  return path.startsWith(`${FEATURES_ROOT}${sep}`) &&
    path.includes(`${sep}model${sep}`) &&
    /\.(?:ts|tsx)$/.test(path) &&
    sourceCalls(source, 'useMutation', path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
}

/** Every feature model mutation hook, keyed by its path relative to `WEB_ROOT`. */
function discoverMutationHooks(): string[] {
  return walkFiles(FEATURES_ROOT, (path) => /\.(?:ts|tsx)$/.test(path))
    .filter((path) => isMutationHook(path, readText(path)))
    .map((path) => repoRelative(path).replace(/^web\//, ''))
    .sort();
}

/** Resolve a bare import specifier to a source file, the way this repo's own aliases do. */
function resolveImport(spec: string, fromFile: string): string | null {
  const base = spec.startsWith('@/')
    ? join(WEB_ROOT, 'src', spec.slice(2))
    : spec.startsWith('.')
      ? resolve(dirname(fromFile), spec)
      : null;
  if (base === null) return null; // a package, not a source file this guard can read
  for (const candidate of [`${base}.ts`, `${base}.tsx`, join(base, 'index.ts'), join(base, 'index.tsx')]) {
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

/**
 * Whether the module `name` is defined at `filePath`, or re-exported from there, carries
 * `queryKeys.dashboard.summary()` in its own text — following `export { name } from '…'`
 * and `export * from '…'` through barrel files (`@/entities/expert-decision`'s `index.ts`
 * re-exports `decisionCacheKeys` from `model/cache.ts`), bounded so a cycle cannot loop
 * forever.
 */
function definitionInvalidatesDashboard(filePath: string, name: string, depth = 0): boolean {
  if (depth > 4) return false;
  const source = readText(filePath);
  if (declaredFunctionCallsExpression(source, name, DASHBOARD_INVALIDATION)) return true;

  for (const statement of parsed(source).statements) {
    if (!ts.isExportDeclaration(statement)) continue;
    const moduleSpecifier = statement.moduleSpecifier;
    if (moduleSpecifier === undefined || !ts.isStringLiteral(moduleSpecifier)) continue;
    const exports = statement.exportClause;
    const reExportsName =
      exports === undefined ||
      (ts.isNamedExports(exports) &&
        exports.elements.some(
          (element) => (element.propertyName?.text ?? element.name.text) === name,
        ));
    if (!reExportsName) continue;
    const resolved = resolveImport(moduleSpecifier.text, filePath);
    if (resolved !== null && definitionInvalidatesDashboard(resolved, name, depth + 1)) return true;
  }
  return false;
}

/**
 * Whether `hookPath` invalidates the dashboard's one read: directly, or by delegating to
 * an imported `*CacheKeys` helper that itself does (`decisionCacheKeys`'s shape).
 */
function invalidatesDashboard(hookPath: string, source = readText(hookPath)): boolean {
  if (sourceInvalidatesDashboard(source)) return true;

  for (const binding of importedBindings(source)) {
    if (!/CacheKeys$/.test(binding.exported)) continue; // not the delegation shape this guard follows
    if (!sourceCalls(source, binding.local)) continue; // imported but never called here
    if (!sourceCalls(source, 'invalidateQueries')) continue; // keys read without invalidation do not refresh
    const resolved = resolveImport(binding.specifier, hookPath);
    if (
      resolved !== null &&
      definitionInvalidatesDashboard(resolved, binding.exported)
    ) {
      return true;
    }
  }
  return false;
}

describe('every mutation hook is mapped to whether it invalidates the dashboard', () => {
  it('names exactly the mutation hooks this repository has, no more and no fewer', () => {
    const discovered = discoverMutationHooks();
    const expected = Object.keys(EXPECTED_INVALIDATION).sort();
    expect(discovered, 'a mutation hook exists that this map does not name').toEqual(expected);
  });

  for (const [relPath, expected] of Object.entries(EXPECTED_INVALIDATION)) {
    it(`${relPath} ${expected ? 'invalidates' : 'does not claim to invalidate'} the dashboard summary`, () => {
      const found = invalidatesDashboard(join(WEB_ROOT, relPath));
      expect(found, `${relPath}: expected invalidatesDashboard() to be ${expected}, got ${found}`).toBe(
        expected,
      );
    });
  }

  it('goes red when create-project comments out the real invalidation call', () => {
    const hookPath = join(WEB_ROOT, 'src/features/create-project/model/use-create-project.ts');
    const original = readText(hookPath);
    const call = 'void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });';
    expect(original).toContain(call);
    const commentedOut = original.replace(call, `// ${call}`);
    expect(invalidatesDashboard(hookPath, commentedOut)).toBe(false);
  });

  it('does not confuse a dashboard read with invalidation', () => {
    const hookPath = join(WEB_ROOT, 'src/features/create-project/model/use-create-project.ts');
    const original = readText(hookPath);
    const invalidation = 'void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });';
    expect(original).toContain(invalidation);
    const readInstead = original.replace(
      invalidation,
      'void queryClient.getQueryData(queryKeys.dashboard.summary());',
    );
    expect(invalidatesDashboard(hookPath, readInstead)).toBe(false);
  });

  it('recognises namespace-qualified mutation hooks', () => {
    expect(sourceCalls('const mutation = RQ.useMutation({ mutationFn });', 'useMutation')).toBe(true);
  });

  it('discovers an executable hook in model/archive.ts without a use- filename', () => {
    const source = 'const mutation = RQ.useMutation({ mutationFn });';
    const archive = join(FEATURES_ROOT, 'archive-project', 'model', 'archive.ts');
    expect(isMutationHook(archive, source)).toBe(true);
    expect(isMutationHook(archive.replace(/\.ts$/, '.tsx'), source)).toBe(true);
    const tsx = 'const element = <div />; const mutation = RQ.useMutation({ mutationFn });';
    expect(isMutationHook(archive.replace(/\.ts$/, '.tsx'), tsx)).toBe(true);
    expect(isMutationHook(join(FEATURES_ROOT, 'archive-project', 'archive.ts'), source)).toBe(false);
    expect(isMutationHook(join(WEB_ROOT, 'src', 'entities', 'model', 'archive.ts'), source)).toBe(false);
    expect(isMutationHook(archive, `// ${source}`)).toBe(false);
    expect(isMutationHook(archive, `const example = ${JSON.stringify(source)};`)).toBe(false);
  });

  it('does not accept dashboard invalidation text that exists only in a decoy comment', () => {
    const hookPath = join(WEB_ROOT, 'src/features/export-run/model/use-export-run.ts');
    const decoy = `${readText(hookPath)}\n// queryKeys.dashboard.summary()\n`;
    expect(invalidatesDashboard(hookPath, decoy)).toBe(false);
  });
});
