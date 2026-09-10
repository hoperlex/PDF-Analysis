/**
 * Guard: no floating dependency version anywhere in the frontend toolchain.
 *
 * The foundation freeze forbids one — `A2` pins container images by digest, and a caret
 * in `web/package.json` would be the single soft edge in an otherwise reproducible tree.
 * A range means two checkouts of the same commit can install different code, and the
 * first person to notice is whoever is debugging a failure that reproduces nowhere else.
 *
 * Every positive assertion here is paired with a mutation: the same detector is run
 * against a manifest carrying the exact defect it exists to catch. A pinning check that
 * has never seen a caret has not been shown to detect one.
 */

import { describe, expect, it } from 'vitest';

import { LOCK_PATH, WEB_ROOT, readJson, readText } from './lib/repo';
import { join } from 'node:path';
import {
  EXACT_VERSION,
  findFloatingVersions,
  findUnpinnedLockEntries,
} from './lib/version-pins';

const MANIFEST_PATH = join(WEB_ROOT, 'package.json');
const LOCKFILE_PATH = join(WEB_ROOT, 'package-lock.json');
const NVMRC_PATH = join(WEB_ROOT, '.nvmrc');

interface Manifest {
  readonly engines?: Record<string, string>;
  readonly packageManager?: string;
  readonly dependencies?: Record<string, string>;
  readonly devDependencies?: Record<string, string>;
}

const manifest = readJson<Manifest>(MANIFEST_PATH);

describe('the committed manifest pins every version exactly', () => {
  it('has no floating version in any dependency section', () => {
    const violations = findFloatingVersions(manifest);
    expect(
      violations,
      `web/package.json carries floating versions:\n${violations
        .map((v) => `  ${v.where} = ${v.value}  (${v.reason})`)
        .join('\n')}`,
    ).toEqual([]);
  });

  it('declares at least one dependency, so an empty manifest cannot pass vacuously', () => {
    const count =
      Object.keys(manifest.dependencies ?? {}).length +
      Object.keys(manifest.devDependencies ?? {}).length;
    expect(count).toBeGreaterThan(0);
  });

  it('pins Node and npm in engines and packageManager', () => {
    expect(manifest.engines?.['node']).toMatch(EXACT_VERSION);
    expect(manifest.engines?.['npm']).toMatch(EXACT_VERSION);
    expect(manifest.packageManager).toMatch(/^npm@\d+\.\d+\.\d+$/);
  });

  it('agrees with .nvmrc on the Node version', () => {
    const nvmrc = readText(NVMRC_PATH).trim();
    expect(nvmrc, '.nvmrc must name one exact Node version').toMatch(EXACT_VERSION);
    expect(nvmrc).toBe(manifest.engines?.['node']);
  });
});

describe('the committed lockfile pins every artifact', () => {
  it('resolves every package to an exact version with an integrity hash', () => {
    const violations = findUnpinnedLockEntries(readJson(LOCKFILE_PATH));
    expect(
      violations.slice(0, 20),
      `package-lock.json has ${violations.length} unpinned entries`,
    ).toEqual([]);
  });

  it('is lockfileVersion 3, so `npm ci` is reproducible', () => {
    const lock = readJson<{ lockfileVersion: number }>(LOCKFILE_PATH);
    expect(lock.lockfileVersion).toBe(3);
  });
});

/**
 * The mutation half. Each case is the defect the guard exists to catch, applied to a copy
 * of the real manifest in memory. Nothing tracked is edited.
 */
describe('the detector goes red on a floating version', () => {
  const mutate = (patch: Record<string, unknown>): unknown => ({ ...manifest, ...patch });

  it('catches a caret range', () => {
    const violations = findFloatingVersions(
      mutate({ dependencies: { ...manifest.dependencies, next: '^15.5.25' } }),
    );
    expect(violations).toContainEqual({
      where: 'dependencies.next',
      value: '^15.5.25',
      reason: 'caret range accepts any compatible minor or patch',
    });
  });

  it('catches a tilde range', () => {
    const violations = findFloatingVersions(
      mutate({ devDependencies: { ...manifest.devDependencies, typescript: '~5.9.3' } }),
    );
    expect(violations.map((v) => v.where)).toContain('devDependencies.typescript');
  });

  it('catches a wildcard and a dist-tag', () => {
    expect(
      findFloatingVersions(mutate({ dependencies: { react: '*' } })).map((v) => v.reason),
    ).toContain('wildcard accepts anything');
    expect(
      findFloatingVersions(mutate({ dependencies: { react: 'latest' } })).map((v) => v.reason),
    ).toContain("dist-tag 'latest' moves under you");
  });

  it('catches a comparator range hidden in engines', () => {
    const violations = findFloatingVersions(mutate({ engines: { node: '>=22.0.0' } }));
    expect(violations.map((v) => v.where)).toContain('engines.node');
  });

  it('catches a range reintroduced through overrides', () => {
    const violations = findFloatingVersions(
      mutate({ overrides: { 'some-transitive': { react: '^19.0.0' } } }),
    );
    expect(violations.map((v) => v.where)).toContain('overrides.some-transitive.react');
  });

  it('catches an unpinned packageManager', () => {
    expect(findFloatingVersions(mutate({ packageManager: 'npm@10' })).map((v) => v.where)).toContain(
      'packageManager',
    );
  });

  it('catches a lockfile entry with no integrity hash', () => {
    const violations = findUnpinnedLockEntries({
      packages: { 'node_modules/example': { version: '1.0.0', resolved: 'https://example/x.tgz' } },
    });
    expect(violations.map((v) => v.reason)).toContain(
      'lockfile entry has no resolved URL and integrity hash',
    );
  });
});

describe('the frontend lock agrees with the manifest', () => {
  it('records the same Node and npm pins', () => {
    const lock = readJson<{ toolchain: { node: string; npm: string; packageManager: string } }>(
      LOCK_PATH,
    );
    expect(lock.toolchain.node).toBe(manifest.engines?.['node']);
    expect(lock.toolchain.npm).toBe(manifest.engines?.['npm']);
    expect(lock.toolchain.packageManager).toBe(manifest.packageManager);
  });
});
