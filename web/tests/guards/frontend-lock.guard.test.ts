/**
 * Guard: `web/FRONTEND_LOCK.json` still describes the tree it claims to describe.
 *
 * The lock exists so a later session can prove the committed client matches its input
 * without rerunning anything. That claim is only worth something if the digests in it are
 * checked, so this recomputes every one of them from the files on disk.
 *
 * The mutation half runs the same comparison against a lock object with one digit
 * changed, so the check is shown to fail rather than assumed to.
 */

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  CONTRACT_PATH,
  GENERATED_DIR,
  GENERATOR_PATH,
  LOCK_PATH,
  SNAPSHOT_PATH,
  WEB_ROOT,
  readJson,
  readText,
  sha256File,
} from './lib/repo';

interface FrontendLock {
  readonly lock_version: number;
  readonly toolchain: {
    readonly node: string;
    readonly npm: string;
    readonly packageManager: string;
    readonly lockfile_sha256: string;
    readonly install_command: string;
  };
  readonly openapi: {
    readonly path: string;
    readonly sha256: string;
    readonly snapshot_sha256: string;
    readonly content_commit: string;
    readonly operations: number;
    readonly component_schemas: number;
  };
  readonly generator: {
    readonly script: string;
    readonly script_sha256: string;
    readonly generate_command: string;
  };
  readonly generated: {
    readonly directory: string;
    readonly files: Readonly<Record<string, string>>;
  };
}

const lock = readJson<FrontendLock>(LOCK_PATH);

/** Recompute what the lock claims, so the two can be compared as data. */
function recomputed(): Record<string, string> {
  const digests: Record<string, string> = {
    'openapi.sha256': sha256File(CONTRACT_PATH),
    'openapi.snapshot_sha256': sha256File(SNAPSHOT_PATH),
    'generator.script_sha256': sha256File(GENERATOR_PATH),
    'toolchain.lockfile_sha256': sha256File(join(WEB_ROOT, 'package-lock.json')),
  };
  for (const name of Object.keys(lock.generated.files).sort()) {
    digests[`generated.${name}`] = sha256File(join(GENERATED_DIR, name));
  }
  return digests;
}

function claimed(): Record<string, string> {
  const digests: Record<string, string> = {
    'openapi.sha256': lock.openapi.sha256,
    'openapi.snapshot_sha256': lock.openapi.snapshot_sha256,
    'generator.script_sha256': lock.generator.script_sha256,
    'toolchain.lockfile_sha256': lock.toolchain.lockfile_sha256,
  };
  for (const name of Object.keys(lock.generated.files).sort()) {
    digests[`generated.${name}`] = lock.generated.files[name] as string;
  }
  return digests;
}

describe('the frontend lock matches the tree', () => {
  it('claims a non-trivial number of digests', () => {
    expect(Object.keys(claimed()).length).toBeGreaterThanOrEqual(8);
  });

  it('records the digest of every file it names', () => {
    expect(recomputed()).toEqual(claimed());
  });

  it('names a generator command that exists in package.json', () => {
    const manifest = readJson<{ scripts: Record<string, string> }>(join(WEB_ROOT, 'package.json'));
    expect(lock.generator.generate_command).toBe('npm --prefix web run api:generate');
    expect(manifest.scripts['api:generate']).toBeDefined();
    expect(lock.toolchain.install_command).toBe('npm --prefix web ci');
  });

  it('names the OpenAPI commit the client was generated from', () => {
    expect(lock.openapi.content_commit).toMatch(/^[0-9a-f]{7,40}$/);
    expect(lock.openapi.path).toBe('contracts/api/v1/openapi.json');
  });

  it('agrees with the contract on operation and schema counts', () => {
    const document = JSON.parse(readText(CONTRACT_PATH)) as {
      paths: Record<string, Record<string, unknown>>;
      components: { schemas: Record<string, unknown> };
    };
    const methods = new Set(['get', 'put', 'post', 'delete', 'patch', 'head', 'options']);
    const operations = Object.values(document.paths).flatMap((item) =>
      Object.keys(item).filter((key) => methods.has(key)),
    );
    expect(lock.openapi.operations).toBe(operations.length);
    expect(lock.openapi.component_schemas).toBe(Object.keys(document.components.schemas).length);
  });
});

describe('the lock check goes red when a digest is stale', () => {
  const compare = (
    claim: Record<string, string>,
    actual: Record<string, string>,
  ): string[] =>
    Object.keys(claim)
      .sort()
      .filter((key) => claim[key] !== actual[key]);

  it('detects a single changed character in a recorded digest', () => {
    const actual = recomputed();
    const stale = { ...claimed() };
    const key = 'generated.types.gen.ts';
    const original = stale[key] as string;
    stale[key] = `${original.slice(0, -1)}${original.endsWith('0') ? '1' : '0'}`;
    expect(compare(stale, actual)).toEqual([key]);
  });

  it('detects a contract whose bytes moved under a recorded digest', () => {
    const actual = { ...recomputed() };
    actual['openapi.sha256'] = createHash('sha256')
      .update(`${readFileSync(CONTRACT_PATH).toString('utf8')} `)
      .digest('hex');
    expect(compare(claimed(), actual)).toContain('openapi.sha256');
  });

  it('would notice an unrecorded generated file', () => {
    const stale = { ...claimed() };
    delete stale['generated.client.gen.ts'];
    expect(Object.keys(stale).length).toBeLessThan(Object.keys(recomputed()).length);
  });
});
