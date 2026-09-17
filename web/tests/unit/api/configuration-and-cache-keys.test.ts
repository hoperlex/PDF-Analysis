/**
 * Configuration, idempotency keys and cache namespaces: four modules the `W12-WEB` sweep
 * found completely unguarded.
 *
 * Nothing in `web/tests` read `shared/config/env`, `shared/api/idempotency`,
 * `shared/api/query-keys` or `entities/expert-decision/model/cache` before this file, and
 * every rule in all four survived deletion:
 *
 *   - **no localhost default.** Removing the throw from `getApiBaseUrl` reddened nothing.
 *     A build with no `NEXT_PUBLIC_API_BASE_URL` would then have looked healthy while
 *     talking to nothing — the exact failure the module's first rule exists to prevent.
 *   - **the trailing slash is stripped**, so `https://api/v1/` and `https://api/v1` build
 *     the same URL instead of one with `//` in it.
 *   - **`hasApiBaseUrl` is about a usable value**, not about the key being present.
 *   - **one key per intent, and keys are distinct.** Replacing `newIdempotencyKey` with a
 *     constant reddened nothing; every write in a session would then have carried the same
 *     key, and the second one would have come back as `idempotency_key_reuse`.
 *   - **the four cache namespaces do not collide**, and appending a decision invalidates
 *     all three of the entries `PC01_UI_SEAM.md` §6 names. Dropping the run finding list
 *     from that set reddened nothing, and that is how a screen shows `accepted` in the
 *     detail panel and `pending` in the row behind it.
 *
 * `process.env` is read here, which `shared/config` alone may do in `src`. This is a test
 * file, outside that scope, and it restores what it changed.
 */

import { afterEach, describe, expect, it } from 'vitest';

import {
  MissingConfigurationError,
  getApiBaseUrl,
  getInstanceLabel,
  hasApiBaseUrl,
} from '@/shared/config';
import { QUERY_NAMESPACES, newIdempotencyKey, queryKeys } from '@/shared/api';
import { decisionCacheKeys } from '@/entities/expert-decision';

const VARIABLE = 'NEXT_PUBLIC_API_BASE_URL';
const LABEL_VARIABLE = 'NEXT_PUBLIC_INSTANCE_LABEL';
const ORIGINAL_URL = process.env[VARIABLE];
const ORIGINAL_LABEL = process.env[LABEL_VARIABLE];

function setEnv(name: string, value: string | undefined): void {
  if (value === undefined) delete process.env[name];
  else process.env[name] = value;
}

afterEach(() => {
  setEnv(VARIABLE, ORIGINAL_URL);
  setEnv(LABEL_VARIABLE, ORIGINAL_LABEL);
});

// ---------------------------------------------------------------------------------------
// There is no localhost default
// ---------------------------------------------------------------------------------------

describe('an unconfigured API base URL fails loudly', () => {
  it('throws rather than defaulting when the variable is absent', () => {
    setEnv(VARIABLE, undefined);
    expect(() => getApiBaseUrl()).toThrow(MissingConfigurationError);
  });

  it('throws rather than defaulting when the variable is blank', () => {
    setEnv(VARIABLE, '   ');
    expect(() => getApiBaseUrl()).toThrow(MissingConfigurationError);
  });

  it('names the variable the operator has to set', () => {
    setEnv(VARIABLE, undefined);
    try {
      getApiBaseUrl();
      throw new Error('getApiBaseUrl returned instead of throwing');
    } catch (error) {
      expect(error).toBeInstanceOf(MissingConfigurationError);
      expect((error as MissingConfigurationError).variable).toBe('NEXT_PUBLIC_API_BASE_URL');
      expect((error as Error).message).toContain('NEXT_PUBLIC_API_BASE_URL');
    }
  });

  it('never returns a localhost address of its own', () => {
    setEnv(VARIABLE, undefined);
    let returned: string | null = null;
    try {
      returned = getApiBaseUrl();
    } catch {
      returned = null;
    }
    expect(returned).toBeNull();
  });
});

describe('a configured API base URL is returned without its trailing slash', () => {
  it('strips one trailing slash', () => {
    setEnv(VARIABLE, 'https://api.example.test/v1/');
    expect(getApiBaseUrl()).toBe('https://api.example.test/v1');
  });

  it('strips several', () => {
    setEnv(VARIABLE, 'https://api.example.test/v1///');
    expect(getApiBaseUrl()).toBe('https://api.example.test/v1');
  });

  it('leaves a URL with no trailing slash alone, and trims surrounding whitespace', () => {
    setEnv(VARIABLE, '  https://api.example.test/v1  ');
    expect(getApiBaseUrl()).toBe('https://api.example.test/v1');
  });
});

describe('the configured-or-not question is about a usable value', () => {
  it('is false for absent and for blank', () => {
    setEnv(VARIABLE, undefined);
    expect(hasApiBaseUrl()).toBe(false);
    setEnv(VARIABLE, '');
    expect(hasApiBaseUrl()).toBe(false);
    setEnv(VARIABLE, '  \t ');
    expect(hasApiBaseUrl()).toBe(false);
  });

  it('is true for a value', () => {
    setEnv(VARIABLE, 'https://api.example.test/v1');
    expect(hasApiBaseUrl()).toBe(true);
  });
});

describe('the instance label is cosmetic and absent means absent', () => {
  it('is null for absent and for blank', () => {
    setEnv(LABEL_VARIABLE, undefined);
    expect(getInstanceLabel()).toBeNull();
    setEnv(LABEL_VARIABLE, '   ');
    expect(getInstanceLabel()).toBeNull();
  });

  it('is the trimmed value when there is one', () => {
    setEnv(LABEL_VARIABLE, '  gate-w12c  ');
    expect(getInstanceLabel()).toBe('gate-w12c');
  });
});

// ---------------------------------------------------------------------------------------
// One key per intent means one key, not one key for everything
// ---------------------------------------------------------------------------------------

describe('a minted idempotency key is a new key', () => {
  it('is different every time it is minted', () => {
    // A constant key would make the second write of a session `idempotency_key_reuse`.
    const keys = new Set([
      newIdempotencyKey(),
      newIdempotencyKey(),
      newIdempotencyKey(),
      newIdempotencyKey(),
    ]);
    expect(keys.size).toBe(4);
  });

  it('carries the `ik_` prefix so a key is recognisable in a log', () => {
    expect(newIdempotencyKey().startsWith('ik_')).toBe(true);
  });

  it('matches the contract pattern for an IdempotencyKey', () => {
    // `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`, written out rather than imported, so a change
    // to the generated constant and a change to the generator are two separate reds.
    expect(newIdempotencyKey()).toMatch(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/);
  });
});

// ---------------------------------------------------------------------------------------
// Cache namespaces
// ---------------------------------------------------------------------------------------

const PROJECT_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const FINDING_UID = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

describe('every cache key starts in its own namespace', () => {
  it('declares exactly the four roots', () => {
    expect([...QUERY_NAMESPACES]).toEqual(['projects', 'versions', 'runs', 'findings']);
  });

  it('puts each builder under the root it belongs to', () => {
    expect(queryKeys.projects.list()[0]).toBe('projects');
    expect(queryKeys.projects.detail(PROJECT_UID)[0]).toBe('projects');
    expect(queryKeys.versions.detail(VERSION_UID)[0]).toBe('versions');
    expect(queryKeys.versions.content(VERSION_UID)[0]).toBe('versions');
    expect(queryKeys.runs.detail(RUN_ID)[0]).toBe('runs');
    expect(queryKeys.runs.findings(RUN_ID)[0]).toBe('runs');
    expect(queryKeys.findings.detail(FINDING_UID)[0]).toBe('findings');
    expect(queryKeys.findings.decisions(FINDING_UID)[0]).toBe('findings');
  });

  it('keeps a finding detail and a run detail apart even for the same identity string', () => {
    // A collision here is how one slice invalidates another slice's entry, or reads it.
    expect(JSON.stringify(queryKeys.findings.detail(RUN_ID))).not.toBe(
      JSON.stringify(queryKeys.runs.detail(RUN_ID)),
    );
  });

  it('gives every builder a distinct key for the same identity', () => {
    const keys = [
      queryKeys.projects.detail(PROJECT_UID),
      queryKeys.versions.detail(VERSION_UID),
      queryKeys.versions.content(VERSION_UID),
      queryKeys.runs.detail(RUN_ID),
      queryKeys.runs.findings(RUN_ID),
      queryKeys.findings.detail(FINDING_UID),
      queryKeys.findings.decisions(FINDING_UID),
    ].map((key) => JSON.stringify(key));
    expect(new Set(keys).size).toBe(keys.length);
  });
});

describe('an appended decision invalidates all three entries the seam names', () => {
  it('invalidates the decision history, the finding detail and the run finding list', () => {
    const keys = decisionCacheKeys(FINDING_UID, RUN_ID).map((key) => JSON.stringify(key));

    expect(keys).toHaveLength(3);
    expect(keys).toContain(JSON.stringify(['findings', 'decisions', FINDING_UID]));
    expect(keys).toContain(JSON.stringify(['findings', 'detail', FINDING_UID]));
    // The third is the one that gets forgotten: the verdict projection is in the list row
    // as well as in the detail panel.
    expect(keys).toContain(JSON.stringify(['runs', 'findings', RUN_ID, {}]));
  });

  it('builds the run key with default filters, so it matches every filtered list', () => {
    const runKey = decisionCacheKeys(FINDING_UID, RUN_ID)[2];
    expect(runKey?.[3]).toEqual({});
  });
});
