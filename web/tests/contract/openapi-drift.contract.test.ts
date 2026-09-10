/**
 * Contract guard: the committed client is exactly what the frozen OpenAPI document
 * generates, and nothing else.
 *
 * Three ways the client can stop matching its input, all covered here:
 *   1. someone hand-edits a generated file;
 *   2. someone adds a file to the generated directory;
 *   3. the contract changes upstream and nobody regenerates.
 *
 * The last one is the reason the snapshot at `web/openapi/openapi.json` exists: it is the
 * bytes the committed client was generated from, so a divergence between it and
 * `contracts/api/v1/openapi.json` is upstream drift, reported here rather than discovered
 * at the Gate B convergence.
 *
 * The mutation half regenerates from a deliberately altered copy of the contract and
 * asserts the comparison fails. A drift guard that has never seen drift is not evidence.
 */

import { mkdtempSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  CONTRACT_PATH,
  GENERATED_DIR,
  SNAPSHOT_PATH,
  sha256File,
} from '../guards/lib/repo';
// The generator is a plain ES module with a pure `generate(bytes)` export, so the drift
// check runs in process: no subprocess, no temp working tree, nothing to clean up.
import { generate } from '../../scripts/generate-api-client.mjs';

const OWNED_FILES = ['client.gen.ts', 'index.ts', 'operations.gen.ts', 'types.gen.ts'];

const contractBytes = readFileSync(CONTRACT_PATH);
const generated = generate(contractBytes) as {
  meta: { digest: string; version: string };
  operations: ReadonlyArray<{ operationId: string }>;
  files: Record<string, string>;
};

describe('the snapshot is the contract', () => {
  it('is byte-identical to contracts/api/v1/openapi.json', () => {
    expect(
      sha256File(SNAPSHOT_PATH),
      'web/openapi/openapi.json has drifted from the contract. The snapshot records the ' +
        'bytes the committed client was generated from; regenerate rather than editing it.',
    ).toBe(sha256File(CONTRACT_PATH));
  });
});

describe('the committed client is what the contract generates', () => {
  it('generates exactly the four owned files', () => {
    expect(Object.keys(generated.files).sort()).toEqual(OWNED_FILES);
  });

  it('has no unexpected file in the generated directory', () => {
    expect(readdirSync(GENERATED_DIR).sort()).toEqual(OWNED_FILES);
  });

  for (const name of OWNED_FILES) {
    it(`matches the committed ${name} byte for byte`, () => {
      const committed = readFileSync(join(GENERATED_DIR, name), 'utf8');
      expect(
        committed === generated.files[name],
        `${name} differs from what the contract generates. Run ` +
          '`npm --prefix web run api:generate` and commit the result; never hand-edit it.',
      ).toBe(true);
    });
  }

  it('records the contract digest inside the generated types', () => {
    expect(generated.files['types.gen.ts']).toContain(generated.meta.digest);
    expect(sha256File(CONTRACT_PATH)).toBe(generated.meta.digest);
  });
});

describe('regeneration is deterministic', () => {
  it('produces byte-identical output on a second run', () => {
    const again = generate(contractBytes) as { files: Record<string, string> };
    for (const name of OWNED_FILES) {
      expect(again.files[name]).toBe(generated.files[name]);
    }
  });

  it('emits no timestamp, hostname or absolute path', () => {
    const all = OWNED_FILES.map((name) => generated.files[name]).join('\n');
    expect(all).not.toMatch(/\b20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}/);
    expect(all).not.toMatch(/\/(?:home|root|Users)\//);
    expect(all).not.toMatch(/\bGenerated on\b/i);
  });
});

/**
 * The mutation half. Each case alters a copy of the contract in a temp directory — never
 * the tracked file — regenerates, and asserts the committed client no longer matches.
 */
describe('the drift guard goes red on a changed contract', () => {
  const temp = mkdtempSync(join(tmpdir(), 'a5-drift-'));
  const contractText = contractBytes.toString('utf8');

  function regenerateFrom(mutate: (text: string) => string): Record<string, string> {
    const mutatedPath = join(temp, `mutated-${Math.random().toString(36).slice(2)}.json`);
    writeFileSync(mutatedPath, mutate(contractText), 'utf8');
    const result = generate(readFileSync(mutatedPath)) as { files: Record<string, string> };
    return result.files;
  }

  it('detects a renamed run state — the `published` to `succeeded` probe', () => {
    const files = regenerateFrom((text) => text.replace(/"published"/g, '"succeeded"'));
    expect(files['types.gen.ts']).not.toBe(generated.files['types.gen.ts']);
    expect(files['types.gen.ts']).toContain("'succeeded'");
    // And the reason it matters: the committed client would no longer carry the state.
    const committed = readFileSync(join(GENERATED_DIR, 'types.gen.ts'), 'utf8');
    expect(committed).toContain("'published'");
    expect(committed).not.toMatch(/RUN_STATE_VALUES = \[[^\]]*'succeeded'/);
  });

  it('detects a removed schema property', () => {
    const files = regenerateFrom((text) => text.replace('"current_verdict"', '"verdict_now"'));
    expect(files['types.gen.ts']).not.toBe(generated.files['types.gen.ts']);
  });

  it('detects a changed operation path', () => {
    const files = regenerateFrom((text) =>
      text.replace('"/runs/{run_id}/export.csv"', '"/runs/{run_id}/download.csv"'),
    );
    expect(files['operations.gen.ts']).not.toBe(generated.files['operations.gen.ts']);
    expect(files['operations.gen.ts']).toContain('/runs/{run_id}/download.csv');
  });

  it('detects a changed digest even when nothing else moves', () => {
    const files = regenerateFrom((text) => `${text}\n`);
    expect(files['types.gen.ts']).not.toBe(generated.files['types.gen.ts']);
  });

  it('refuses a document with a missing operationId rather than guessing a name', () => {
    expect(() =>
      generate(Buffer.from(contractText.replace('"operationId": "createProject",', ''), 'utf8')),
    ).toThrow(/missing operationId/);
  });

  it('refuses a document that is not OpenAPI 3.1', () => {
    expect(() =>
      generate(Buffer.from(contractText.replace('"openapi": "3.1.0"', '"openapi": "3.0.3"'), 'utf8')),
    ).toThrow(/expected OpenAPI 3.1/);
  });
});
