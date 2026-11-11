/**
 * `PREC-WEB`: who asks for the precedents. The server denies the viewer, so the screen makes NO request for him, and none while the
 * account is not known. Two proofs: the screen hands the reads `enabled` from the session's right (a stand-in records what it was given), and a
 * read built with `enabled: false` asks the network nothing while one built with `true` asks exactly once.
 */

import { QueryObserver, environmentManager } from '@tanstack/react-query';
import type * as DecisionMemory from '@/entities/decision-memory';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

const seen = vi.hoisted(() => ({ run: [] as boolean[], finding: [] as boolean[] }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => null,
  useSearchParams: () => new URLSearchParams(''),
}));

vi.mock('@/entities/decision-memory', async (importOriginal) => {
  const actual = await importOriginal<typeof DecisionMemory>();
  return {
    ...actual,
    useRunPrecedents: (runId: string, enabled: boolean) => {
      seen.run.push(enabled);
      return actual.useRunPrecedents(runId, enabled);
    },
    useFindingPrecedents: (findingUid: string | null, enabled: boolean) => {
      seen.finding.push(enabled);
      return actual.useFindingPrecedents(findingUid, enabled);
    },
  };
});

import { newClient } from '../screens/harness';
import { runPrecedentsQueryOptions } from '@/entities/decision-memory';

import { navigation, reviewPage, textFinding } from './precedents-fixtures';
import { RUN_ID } from './fixtures';

const A = textFinding('E1', 'Не указан предел огнестойкости перекрытия.');

afterEach(() => {
  seen.run.length = 0;
  seen.finding.length = 0;
  navigation.search = '';
});

describe('the screen hands the reads the session’s right', () => {
  it('enables them for an expert and for an administrator', () => {
    for (const roles of [['expert'], ['admin'], ['admin', 'expert']]) {
      reviewPage({ findings: [A], roles });
      expect(seen.run.at(-1), roles.join()).toBe(true);
      expect(seen.finding.at(-1), roles.join()).toBe(true);
    }
  });

  it('disables them for a viewer and while the account is not known', () => {
    reviewPage({ findings: [A], roles: ['viewer'] });
    expect(seen.run.every((enabled) => !enabled)).toBe(true);
    expect(seen.finding.every((enabled) => !enabled)).toBe(true);
    seen.run.length = 0;
    reviewPage({ findings: [A] });
    expect(seen.run.length).toBeGreaterThan(0);
    expect(seen.run.every((enabled) => !enabled)).toBe(true);
  });
});

describe('a disabled read asks nothing', () => {
  const wasServer = environmentManager.isServer();
  let requests: string[] = [];
  beforeAll(() => environmentManager.setIsServer(() => false));
  afterAll(() => environmentManager.setIsServer(() => wasServer));
  beforeEach(() => {
    requests = [];
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
    vi.stubGlobal('fetch', async (input: unknown) => {
      requests.push(String(input instanceof Request ? input.url : input));
      return new Response(JSON.stringify({ run_id: RUN_ID, available: false, items: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  async function settle(enabled: boolean): Promise<void> {
    const observer = new QueryObserver(newClient(), runPrecedentsQueryOptions(RUN_ID, enabled));
    const stop = observer.subscribe(() => {});
    await new Promise((resolve) => setTimeout(resolve, 50));
    stop();
  }

  it('makes no request for the viewer’s disabled read', async () => {
    await settle(false);
    expect(requests).toEqual([]);
  });

  it('makes exactly one request for an enabled read, to the run’s precedents', async () => {
    await settle(true);
    expect(requests.length).toBe(1);
    expect(requests[0]).toContain(`/runs/${RUN_ID}/precedents`);
  });
});
