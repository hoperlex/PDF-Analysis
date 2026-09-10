/**
 * Guard: the transport seam has exactly one implementation.
 *
 * `B7` and `B8` will each be tempted, once, to call the API "just here". The moment a
 * second `fetch` exists there is a second answer to how the idempotency key is attached,
 * how the correlation id travels and how the error envelope is decoded — and the second
 * answer is always the one missing a case.
 *
 * The same scanner runs over the real `web/src` tree and over fixtures that break every
 * rule, so the guard is shown to fire rather than assumed to.
 */

import { describe, expect, it } from 'vitest';

import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';
import { join } from 'node:path';
import { BOUNDARY_RULE_IDS, scanBoundaries } from './lib/source-scan';
import type { SourceFile } from './lib/source-scan';

const SRC = join(WEB_ROOT, 'src');

const sources: SourceFile[] = walkFiles(SRC, (p) => /\.(ts|tsx)$/.test(p)).map((path) => ({
  path: repoRelative(path),
  text: readText(path),
}));

describe('the application source respects the transport boundary', () => {
  it('scans a non-trivial number of files, so a broken walk cannot pass vacuously', () => {
    expect(sources.length).toBeGreaterThan(15);
    expect(sources.map((s) => s.path)).toContain('web/src/shared/api/transport.ts');
  });

  it('has no boundary violation anywhere under web/src', () => {
    const violations = scanBoundaries(sources);
    expect(
      violations,
      `boundary violations:\n${violations
        .map((v) => `  ${v.path}:${v.line} [${v.rule}] ${v.excerpt}`)
        .join('\n')}`,
    ).toEqual([]);
  });

  it('keeps every declared rule in force', () => {
    expect(BOUNDARY_RULE_IDS).toEqual([
      'raw-http',
      'http-library',
      'environment-read',
      'storage-address',
    ]);
  });
});

/**
 * The mutation half: fixtures that break each rule, scanned in memory. Nothing tracked is
 * edited, and the fixture paths are the paths a real offending slice would have.
 */
describe('the scanner goes red on a boundary violation', () => {
  const cases: ReadonlyArray<{ rule: string; file: SourceFile }> = [
    {
      rule: 'raw-http',
      file: {
        path: 'web/src/features/create-project/api.ts',
        text: 'export async function create() {\n  const r = await fetch("/api/v1/projects");\n  return r.json();\n}\n',
      },
    },
    {
      rule: 'raw-http',
      file: {
        path: 'web/src/widgets/run-progress/poll.ts',
        text: 'const xhr = new XMLHttpRequest();\nxhr.open("GET", "/runs/1");\n',
      },
    },
    {
      rule: 'http-library',
      file: {
        path: 'web/src/entities/finding/api.ts',
        text: 'import axios from "axios";\nexport const client = axios.create();\n',
      },
    },
    {
      rule: 'environment-read',
      file: {
        path: 'web/src/_pages/projects/ui.tsx',
        text: 'const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";\n',
      },
    },
    {
      rule: 'storage-address',
      file: {
        path: 'web/src/entities/document-version/model.ts',
        text: 'export interface Leak {\n  object_key: string;\n}\n',
      },
    },
  ];

  for (const { rule, file } of cases) {
    it(`catches ${rule} in ${file.path}`, () => {
      const violations = scanBoundaries([file]);
      expect(violations.map((v) => v.rule)).toContain(rule);
    });
  }

  it('does not fire on the same construct inside the one place it is allowed', () => {
    const allowed: SourceFile = {
      path: 'web/src/shared/api/transport.ts',
      text: 'const response = await fetch(url, init);\n',
    };
    expect(scanBoundaries([allowed])).toEqual([]);
  });

  it('does not fire on a comment that merely mentions the construct', () => {
    const commentary: SourceFile = {
      path: 'web/src/widgets/finding-list/ui.tsx',
      text: '// never call fetch( here; import the generated client instead\nexport const x = 1;\n',
    };
    expect(scanBoundaries([commentary])).toEqual([]);
  });
});
