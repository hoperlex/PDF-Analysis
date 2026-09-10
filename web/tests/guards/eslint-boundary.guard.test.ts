/**
 * Guard: the FSD boundary rules in `eslint.config.mjs` actually fire.
 *
 * A lint config that has never rejected anything is a config nobody has tested. This
 * runs ESLint over fixtures under `tests/guards/fixtures/**` that violate one rule each,
 * asserts the specific rule id comes back, and runs it over a legal fixture in the same
 * directory to prove the failures are the rules and not the location.
 *
 * The fixtures are ignored by `npm run lint` and excluded from `tsconfig.json`, so they
 * break neither the lint gate nor the build. `--no-ignore` is what reaches them.
 */

import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from './lib/repo';

const ESLINT_BIN = join(WEB_ROOT, 'node_modules', '.bin', 'eslint');

interface EslintMessage {
  readonly ruleId: string | null;
  readonly message: string;
}

interface EslintResult {
  readonly filePath: string;
  readonly errorCount: number;
  readonly messages: readonly EslintMessage[];
}

/** Run ESLint on one fixture and return its exit code with the parsed report. */
function lintFixture(relativePath: string): { exitCode: number; results: EslintResult[] } {
  try {
    const stdout = execFileSync(ESLINT_BIN, ['--no-ignore', '-f', 'json', relativePath], {
      cwd: WEB_ROOT,
      encoding: 'utf8',
    });
    return { exitCode: 0, results: JSON.parse(stdout) as EslintResult[] };
  } catch (error) {
    const failure = error as { status?: number; stdout?: string };
    if (typeof failure.stdout !== 'string' || failure.stdout.length === 0) throw error;
    return { exitCode: failure.status ?? 1, results: JSON.parse(failure.stdout) as EslintResult[] };
  }
}

function ruleIds(results: readonly EslintResult[]): string[] {
  return results.flatMap((r) => r.messages.map((m) => m.ruleId ?? '<syntax>'));
}

describe('the FSD boundary rules go red on a violating fixture', () => {
  it('rejects a deep import past a slice public API', () => {
    const { exitCode, results } = lintFixture('tests/guards/fixtures/features/deep-import.fixture.ts');
    expect(exitCode).not.toBe(0);
    expect(ruleIds(results)).toContain('no-restricted-imports');
    expect(results[0]?.messages[0]?.message).toContain('FSD boundary');
  });

  it('rejects an upward import from entities to widgets', () => {
    const { exitCode, results } = lintFixture('tests/guards/fixtures/entities/upward-import.fixture.ts');
    expect(exitCode).not.toBe(0);
    expect(ruleIds(results)).toContain('no-restricted-imports');
    expect(results[0]?.messages[0]?.message).toContain('may not import');
  });

  it('rejects raw fetch outside src/shared/api', () => {
    const { exitCode, results } = lintFixture('tests/guards/fixtures/features/raw-fetch.fixture.ts');
    expect(exitCode).not.toBe(0);
    expect(ruleIds(results)).toContain('no-restricted-globals');
    expect(results[0]?.messages[0]?.message).toContain('Transport boundary');
  });

  it('accepts a legal fixture in the same directory', () => {
    const { exitCode, results } = lintFixture('tests/guards/fixtures/features/clean.fixture.ts');
    expect(
      exitCode,
      `the control fixture must pass, otherwise the failures above prove only that ` +
        `ESLint dislikes this directory: ${JSON.stringify(ruleIds(results))}`,
    ).toBe(0);
    expect(results[0]?.errorCount).toBe(0);
  });
});
