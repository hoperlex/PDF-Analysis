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
 *   1. **Discovers** every `features/<feature>/model/use-*.ts` file that calls `useMutation(`,
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
import { dirname, join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';

const FEATURES_ROOT = join(WEB_ROOT, 'src', 'features');
const DASHBOARD_INVALIDATION = 'queryKeys.dashboard.summary()';

/**
 * Every mutation hook under `features/**`, keyed by its path relative to `WEB_ROOT`, and
 * whether it must invalidate the dashboard's one read. `true` is checked positively
 * (the invalidation must be found); `false` is recorded so the hook is not silently
 * unmapped, not asserted as an absence — a hook is free to gain one later.
 */
const EXPECTED_INVALIDATION: Readonly<Record<string, boolean>> = {
  'src/features/append-comment/model/use-append-comment.ts': true,
  'src/features/create-project/model/use-create-project.ts': true,
  'src/features/export-run/model/use-export-run.ts': false,
  'src/features/record-verdict/model/use-record-verdict.ts': true,
  'src/features/start-run/model/use-start-run.ts': true,
  'src/features/upload-document/model/use-upload-document.ts': true,
};

/** Every `features/<feature>/model/use-*.ts` file that calls `useMutation(`, relative to `WEB_ROOT`. */
function discoverMutationHooks(): string[] {
  return walkFiles(FEATURES_ROOT, (path) => /\/model\/use-[^/]+\.ts$/.test(path))
    .filter((path) => /useMutation\s*[<(]/.test(readText(path)))
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
  const text = readText(filePath);
  if (text.includes(DASHBOARD_INVALIDATION) && new RegExp(`\\b${name}\\b`).test(text)) return true;

  const namedReExport = text.match(
    new RegExp(`export\\s*\\{[^}]*\\b${name}\\b[^}]*\\}\\s*from\\s*'([^']+)'`),
  );
  if (namedReExport) {
    const resolved = resolveImport(namedReExport[1]!, filePath);
    if (resolved !== null && definitionInvalidatesDashboard(resolved, name, depth + 1)) return true;
  }
  for (const starExport of text.matchAll(/export\s*\*\s*from\s*'([^']+)'/g)) {
    const resolved = resolveImport(starExport[1]!, filePath);
    if (resolved !== null && definitionInvalidatesDashboard(resolved, name, depth + 1)) return true;
  }
  return false;
}

/**
 * Whether `hookPath` invalidates the dashboard's one read: directly, or by delegating to
 * an imported `*CacheKeys` helper that itself does (`decisionCacheKeys`'s shape).
 */
function invalidatesDashboard(hookPath: string): boolean {
  const text = readText(hookPath);
  if (text.includes(DASHBOARD_INVALIDATION)) return true;

  const importLine = /import\s*\{([^}]+)\}\s*from\s*'([^']+)';/g;
  for (const match of text.matchAll(importLine)) {
    const names = match[1]!.split(',').map((n) => n.trim().split(/\s+as\s+/)[0]!.trim());
    const spec = match[2]!;
    for (const name of names) {
      if (!/CacheKeys$/.test(name)) continue; // not the delegation shape this guard follows
      if (!new RegExp(`\\b${name}\\(`).test(text)) continue; // imported but never called here
      const resolved = resolveImport(spec, hookPath);
      if (resolved !== null && definitionInvalidatesDashboard(resolved, name)) return true;
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
});
