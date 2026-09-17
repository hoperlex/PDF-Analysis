/**
 * Guard: `T-6`'s credential is not in the browser bundle, and cannot get there by accident.
 *
 * `web/src/shared/config/env.ts` states the hazard in its own comment — "`NEXT_PUBLIC_*`
 * values are compiled into the browser bundle, so anything placed here is public by
 * construction" — and `W15-AUTH` is the wave that had to put a real secret in the web tier
 * anyway. The secret is safe only because of a structural property, and a structural
 * property that nothing checks is a comment.
 *
 * This is the static half and it runs in milliseconds. The dynamic half — `npm run build`
 * followed by a grep of `.next/static` for the token bytes — is a measurement recorded
 * with its command in `docs/program/reviews/W15-AUTH.md`, because it needs a build.
 *
 * The mutation half below runs the same scanner over in-memory files that break each rule,
 * so the guard is shown to fire.
 */

import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { SERVER_ONLY_VARIABLES } from '@/shared/config/server-env';
import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';
import type { ScannedFile } from './lib/credential-scan';
import {
  CREDENTIAL_IMPORTER_PREFIX,
  CREDENTIAL_READER,
  CREDENTIAL_RULE_IDS,
  EXPECTED_SERVER_ONLY_NAMES,
  scanCredentialExposure,
} from './lib/credential-scan';

const SRC = join(WEB_ROOT, 'src');

const sources: ScannedFile[] = walkFiles(SRC, (p) => /\.(ts|tsx)$/.test(p)).map((path) => ({
  path: repoRelative(path),
  text: readText(path),
}));

describe('the credential is out of the browser bundle by construction', () => {
  it('scans a non-trivial tree, so a broken walk cannot pass vacuously', () => {
    expect(sources.length).toBeGreaterThan(100);
    expect(sources.map((s) => s.path)).toContain(CREDENTIAL_READER);
    expect(sources.map((s) => s.path)).toContain('web/src/app/bff/v1/[...path]/route.ts');
  });

  it('reads the credential through names Next never inlines', () => {
    // Pinned as literals, not derived from the module: a test that mapped over
    // SERVER_ONLY_VARIABLES and asserted the prefix is absent would pass over an empty
    // array. OPERATING_CONSTRAINTS.md section 12.
    expect([...SERVER_ONLY_VARIABLES]).toEqual([
      'AUDITMANAGER_API_UPSTREAM',
      'AUDITMANAGER_API_TOKEN',
    ]);
    expect([...EXPECTED_SERVER_ONLY_NAMES]).toEqual([
      'AUDITMANAGER_API_UPSTREAM',
      'AUDITMANAGER_API_TOKEN',
    ]);
  });

  it('has no credential exposure anywhere under web/src, nor in the example environment', () => {
    // `.env.example` is scanned too: it is exactly where a later session would write
    // `NEXT_PUBLIC_API_TOKEN=` and then wonder why the bundle carried it.
    const violations = scanCredentialExposure([
      ...sources,
      { path: 'web/.env.example', text: readText(join(WEB_ROOT, '.env.example')) },
    ]);
    expect(
      violations,
      `credential exposure:\n${violations.map((v) => `  ${v.path} [${v.rule}] ${v.detail}`).join('\n')}`,
    ).toEqual([]);
  });

  it('keeps the two NEXT_PUBLIC_ names the web tier is allowed to have', () => {
    const names = new Set<string>();
    for (const file of sources) {
      for (const match of file.text.match(/NEXT_PUBLIC_[A-Z0-9_]+/g) ?? []) names.add(match);
    }
    expect([...names].sort()).toEqual(['NEXT_PUBLIC_API_BASE_URL', 'NEXT_PUBLIC_INSTANCE_LABEL']);
  });

  it('is imported by exactly the BFF route handler and nothing else', () => {
    const importers = sources
      .filter(
        (file) =>
          file.path !== CREDENTIAL_READER && /['"]@\/shared\/config\/server-env['"]/.test(file.text),
      )
      .map((file) => file.path);
    expect(importers).toEqual(['web/src/app/bff/v1/[...path]/route.ts']);
    expect(importers[0]!.startsWith(CREDENTIAL_IMPORTER_PREFIX)).toBe(true);
  });

  it('is not re-exported from the config barrel a client component imports', () => {
    const barrel = readText(join(SRC, 'shared', 'config', 'index.ts'));
    expect(barrel).not.toContain('server-env');
    expect(barrel).toContain("from './env'");
  });

  it('keeps every declared rule in force', () => {
    expect([...CREDENTIAL_RULE_IDS]).toEqual([
      'public-secret-name',
      'credential-read-outside-reader',
      'credential-reader-reexported',
      'credential-reader-imported-outside-bff',
    ]);
  });
});

describe('the scanner goes red on each way the credential could leak', () => {
  const cases: ReadonlyArray<{ rule: string; file: ScannedFile }> = [
    {
      rule: 'public-secret-name',
      file: {
        path: 'web/src/shared/config/env.ts',
        text: 'const t = process.env.NEXT_PUBLIC_API_TOKEN;\n',
      },
    },
    {
      rule: 'public-secret-name',
      file: {
        path: 'web/src/shared/api/transport.ts',
        text: 'headers.set("Authorization", `Bearer ${process.env.NEXT_PUBLIC_BEARER_SECRET}`);\n',
      },
    },
    {
      rule: 'credential-read-outside-reader',
      file: {
        path: 'web/src/shared/api/transport.ts',
        text: 'const token = process.env.AUDITMANAGER_API_TOKEN ?? "";\n',
      },
    },
    {
      rule: 'credential-read-outside-reader',
      file: {
        path: 'web/src/features/start-run/ui/start-run-control.tsx',
        text: 'const up = process.env.AUDITMANAGER_API_UPSTREAM;\n',
      },
    },
    {
      rule: 'credential-reader-reexported',
      file: {
        path: 'web/src/shared/config/index.ts',
        text: "export { getApiToken } from './server-env';\n",
      },
    },
    {
      rule: 'credential-reader-imported-outside-bff',
      file: {
        path: 'web/src/widgets/project-list/ui/project-list.tsx',
        text: "import { getApiToken } from '@/shared/config/server-env';\n",
      },
    },
  ];

  for (const { rule, file } of cases) {
    it(`catches ${rule} in ${file.path}`, () => {
      const violations = scanCredentialExposure([file]);
      expect(violations.map((v) => v.rule)).toContain(rule);
    });
  }

  it('does not fire on the one module that is allowed to read the names', () => {
    const allowed: ScannedFile = {
      path: CREDENTIAL_READER,
      text:
        'const raw = process.env.AUDITMANAGER_API_TOKEN;\n' +
        'const up = process.env.AUDITMANAGER_API_UPSTREAM;\n',
    };
    expect(scanCredentialExposure([allowed])).toEqual([]);
  });

  it('does not fire on the route handler that imports it', () => {
    const allowed: ScannedFile = {
      path: 'web/src/app/bff/v1/[...path]/route.ts',
      text: "import { getApiToken } from '@/shared/config/server-env';\n",
    };
    expect(scanCredentialExposure([allowed])).toEqual([]);
  });

  it('does not fire on the two public names that carry nothing secret', () => {
    const allowed: ScannedFile = {
      path: 'web/src/shared/config/env.ts',
      text:
        'const base = process.env.NEXT_PUBLIC_API_BASE_URL;\n' +
        'const label = process.env.NEXT_PUBLIC_INSTANCE_LABEL;\n',
    };
    expect(scanCredentialExposure([allowed])).toEqual([]);
  });
});
