/**
 * Guard: `queryKeys.runs.detail(runId)` holds one type, and disagreeing about it is a
 * compile error rather than a rendering.
 *
 * `D-57` was two screens filling one cache key with two shapes — a bare `RunStatus` from
 * the run screen, the generated client's `{ data }` envelope from the review screen's
 * `useQuery`. Neither half was a type error. `getQueryData<RunStatus>(key)` *asserts* the
 * shape instead of checking it, `useQuery` takes its shape from its own `queryFn`, and the
 * key was the only thing the two sites shared. The repair is not "both sites now agree",
 * which is a state that lasts until the next site: the key carries its value type.
 *
 * **Two mechanisms, because one of them does not reach far enough**, and the split is
 * measured rather than assumed:
 *
 *   1. `@tanstack/query-core` 5.102.8 types `getQueryData`/`setQueryData` through
 *      `InferDataFromTag`, so a `DataTag` on the key is enforced at both. §1 below proves
 *      that on fixtures, by running `tsc` and reading its diagnostics, because a guard
 *      that merely re-states the type in a test file is not evidence the compiler agrees.
 *   2. `useQuery` in `@tanstack/react-query` 5.102.8 does NOT consult the tag —
 *      `InferDataFromTag` appears nowhere in that package's build — so a `useQuery` over
 *      this key can still file anything its `queryFn` returns. That is precisely the route
 *      the review screen took. §2 closes it the only way this version allows: one query
 *      factory for the key, and no other site may name it as a `queryKey`.
 *
 * If a later version of the library carries the tag into `useQuery`, §2 becomes redundant
 * and should be deleted rather than kept as decoration; §2's own comment says so.
 */

import { execFileSync } from 'node:child_process';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';

const TSC_BIN = join(WEB_ROOT, 'node_modules', '.bin', 'tsc');
const FIXTURE_PROJECT = 'tests/guards/fixtures/query-keys/tsconfig.json';

/** Run `tsc` over the fixture project and return its exit code with its diagnostics. */
function compileFixtures(): { exitCode: number; output: string } {
  try {
    const stdout = execFileSync(TSC_BIN, ['-p', FIXTURE_PROJECT], {
      cwd: WEB_ROOT,
      encoding: 'utf8',
    });
    return { exitCode: 0, output: stdout };
  } catch (error) {
    const failure = error as { status?: number; stdout?: string; stderr?: string };
    return {
      exitCode: failure.status ?? 1,
      output: `${failure.stdout ?? ''}${failure.stderr ?? ''}`,
    };
  }
}

// ======================================================================================
// 1. The tag is real: the compiler rejects both halves of D-57 on fixtures.
// ======================================================================================

describe('the compiler refuses the two shapes D-57 put under one key', () => {
  const compiled = compileFixtures();

  it('rejects writing the transport envelope under the key', () => {
    expect(compiled.exitCode).not.toBe(0);
    const line = compiled.output
      .split('\n')
      .find((l) => l.includes('writes-envelope.fixture.ts'));
    expect(line, `tsc said nothing about the write fixture:\n${compiled.output}`).toBeDefined();
    expect(line).toContain('error TS2345');
    // Named in the diagnostic, so this asserts the TAG refused it rather than some other
    // arity or overload mismatch: the parameter tsc expected is the key's value type.
    expect(line).toContain('NoInfer<RunStatus>');
    expect(line).toContain('data: RunStatus');
  });

  it('rejects reading `.data` off the entry, which is what the review screen did', () => {
    const line = compiled.output.split('\n').find((l) => l.includes('reads-envelope.fixture.ts'));
    expect(line, `tsc said nothing about the read fixture:\n${compiled.output}`).toBeDefined();
    expect(line).toContain('error TS2339');
    expect(line).toContain("Property 'data' does not exist on type 'RunStatus'");
  });

  it('accepts the control fixture, so the two reds are the shapes and not the directory', () => {
    expect(
      compiled.output,
      `the control fixture must compile, otherwise the reds above prove only that tsc ` +
        `dislikes this directory:\n${compiled.output}`,
    ).not.toContain('clean.fixture.ts');
  });

  it('needs no type argument to read the key, which is the whole difference', () => {
    // `getQueryData<RunStatus>(key)` compiles against ANY entry, because an explicit type
    // argument displaces the tag. The control fixture reads `.state` with no argument at
    // all; if that ever needed one again, the tag would have been dropped.
    const control = readText(
      join(WEB_ROOT, 'tests', 'guards', 'fixtures', 'query-keys', 'clean.fixture.ts'),
    );
    expect(control).toContain('client.getQueryData(queryKeys.runs.detail(runId))?.state');
    expect(control).not.toContain('getQueryData<');
  });
});

// ======================================================================================
// 1b. The compiler's verdict has to reach the gate, and `make gate` runs vitest.
// ======================================================================================

/**
 * `make gate`'s frontend half is `npm --prefix web test`, which is `vitest run`. Vitest
 * transforms TypeScript with esbuild and esbuild does not typecheck. So every rule the
 * tag enforces -- including the four `setQueryData` sites `D-57` was written across --
 * is enforced by a command the gate never runs, and a regression at any of them would
 * reach `main` with a green gate and fail at `npm run typecheck` or at `next build`.
 *
 * This case is the bridge. It is deliberately broader than `D-57`: it fails on any type
 * error in `web/`, not only on this key. That is the point -- a phantom type is worth
 * exactly as much as the frequency of the compiler running, and four seconds buys it.
 *
 * `--incremental false` so the run leaves no `tsconfig.tsbuildinfo` behind; `*.tsbuildinfo`
 * is git-ignored, but the battery's checkout guard is about files, not about tracking.
 */
describe('the compiler runs inside the gate, not only in a command nobody runs there', () => {
  it('typechecks web/ clean', () => {
    let output = '';
    let exitCode = 0;
    try {
      output = execFileSync(TSC_BIN, ['--noEmit', '--incremental', 'false'], {
        cwd: WEB_ROOT,
        encoding: 'utf8',
      });
    } catch (error) {
      const failure = error as { status?: number; stdout?: string; stderr?: string };
      exitCode = failure.status ?? 1;
      output = `${failure.stdout ?? ''}${failure.stderr ?? ''}`;
    }
    expect(exitCode, `tsc --noEmit reported:\n${output}`).toBe(0);
  });
});

// ======================================================================================
// 2. The hole the tag does not close: `useQuery` ignores it in this version.
// ======================================================================================

describe('one query fills the run-detail key, because useQuery ignores the tag', () => {
  const sources = walkFiles(join(WEB_ROOT, 'src'), (p) => /\.(ts|tsx)$/.test(p)).map((path) => ({
    path,
    text: readText(path),
  }));

  /** Source with line comments and doc-comment bodies removed. */
  const code = (text: string): string =>
    text.replace(/\/\/.*$/gm, '').replace(/^\s*\*.*$/gm, '');

  const FACTORY = join('entities', 'audit-run', 'api', 'run-status-query.ts');

  it('reads a non-trivial number of files, so a broken walk cannot pass vacuously', () => {
    expect(sources.length).toBeGreaterThan(40);
  });

  it('names the key as a queryKey in exactly one module', () => {
    const sites = sources.filter(({ text }) =>
      /queryKey\s*:\s*queryKeys\.runs\.detail\s*\(/.test(code(text)),
    );
    expect(sites.map((s) => repoRelative(s.path))).toEqual([
      repoRelative(join(WEB_ROOT, 'src', FACTORY)),
    ]);
  });

  it('keeps that module the only one that calls the run-status endpoint for it', () => {
    const factory = sources.find((s) => s.path.endsWith(FACTORY));
    expect(factory, 'the factory this guard is about has moved or gone').toBeDefined();
    // Its queryFn states its return type rather than inferring it from the transport,
    // which is what makes the unwrap a decision and not an accident.
    expect(code(factory?.text ?? '')).toContain('Promise<RunStatus>');
    expect(code(factory?.text ?? '')).toContain('response.data');
  });

  it('lets no site displace the tag with an explicit type argument', () => {
    // `getQueryData<Whatever>(queryKeys...)` type-checks against any entry at all: the
    // explicit argument wins over the tag. That single character sequence is how D-57
    // stayed invisible, so it is forbidden across every key, not only this one.
    const offenders = sources.filter(({ text }) =>
      /get(Query|Queries)Data\s*<[^>]*>\s*\(\s*queryKeys\./.test(code(text)),
    );
    expect(offenders.map((o) => repoRelative(o.path))).toEqual([]);
  });

  it('is still needed, which is a fact about the installed library', () => {
    // Delete this whole describe block if this ever fails: it would mean `useQuery`
    // consults the tag, and §1 alone would then cover the defect. Keeping a guard whose
    // premise has expired is how a suite fills with tests that protect nothing.
    const reactQueryBuild = join(WEB_ROOT, 'node_modules', '@tanstack', 'react-query', 'build');
    const consults = walkFiles(reactQueryBuild, (p) => p.endsWith('.d.ts')).some((p) =>
      readText(p).includes('InferDataFromTag'),
    );
    expect(
      consults,
      'react-query now mentions InferDataFromTag; re-measure whether useQuery honours ' +
        'the tag, and if it does, delete section 2 of this guard.',
    ).toBe(false);

    // The sibling half of the same measurement: query-core DOES consult it, which is what
    // section 1 depends on. Asserting both keeps the split honest rather than assumed.
    const coreTypes = join(
      WEB_ROOT,
      'node_modules',
      '@tanstack',
      'query-core',
      'build',
      'modern',
      'index.d.ts',
    );
    expect(relative(WEB_ROOT, coreTypes).length).toBeGreaterThan(0);
    const core = walkFiles(
      join(WEB_ROOT, 'node_modules', '@tanstack', 'query-core', 'build'),
      (p) => p.endsWith('.d.ts'),
    ).some((p) => readText(p).includes('InferDataFromTag'));
    expect(core).toBe(true);
  });
});
