/**
 * `AR-V3-OPT-IN` (design 4.3, 4.5 and 4.8), live: what the choice of an analysis does while the page around it changes.
 *
 * The real run list, the real start controls and the real mutations are mounted in a minimal DOM (`live-render.ts`); only
 * the transport is replaced. What is read is what the requests carried and where the page went.
 *
 *   - the standard analysis is selected whenever the form opens, a remount returns to it, and nothing is written to
 *     storage (no choice is remembered per person, project or browser);
 *   - choosing v3 replaces the standard form, with its executor, preset and group selectors, by the v3 form, and
 *     choosing standard replaces it back; what the form left behind (its estimate, its consent, its refusal) is
 *     cleared, and a consent given for one analysis is never what the other sends;
 *   - one start sends exactly one analysis's operation: v3 sends `startArV3BetaGroup` and never `startRun`, the standard
 *     form sends no v3 request, and a refusal of v3 never offers the single-run start as a substitute;
 *   - the allowance withdrawn while the form is open takes the choice away at the next read of the status, and a v3 start
 *     that is already on its way keeps its form, its key and its observer until it is answered.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const navigation = vi.hoisted(() => ({ pushed: [] as string[] }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useRouter: () => ({ push: (href: string) => navigation.pushed.push(href) }),
}));

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    getArV3BetaPackStatus: vi.fn(),
    listRuns: vi.fn(),
    startArV3BetaGroup: vi.fn(),
    estimateArV3GroupCost: vi.fn(),
    startRun: vi.fn(),
    estimateRunCost: vi.fn(),
  };
});

import {
  ApiError, estimateArV3GroupCost, estimateRunCost, getArV3BetaPackStatus, listRuns, queryKeys, startArV3BetaGroup, startRun,
} from '@/shared/api';
import type { ApiResponse, ArV3BetaGroup, ErrorCode } from '@/shared/api';
import { RUN_PAGE_LIMIT, arV3GroupReviewAddress } from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';

import { GROUP_ID } from './ar-v3-beta-review-fixtures';
import { installedPackFixture } from './ar-v3-beta-pack-fixtures';
import { approveCost, costEstimate } from './cost-estimate-fixtures';
import { mountLive } from './live-render';
import type { LiveRender } from './live-render';

const PROJECT_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const GROUP = { group_id: GROUP_ID, project_uid: PROJECT_UID, version_uid: VERSION_UID } as ArV3BetaGroup;
const ACCEPTED: ApiResponse<ArV3BetaGroup> = { data: GROUP, status: 202, correlationId: 'cid-choice' };

const STANDARD_OPTION = 'Стандартный (профиль АР из исходного приложения)';
const V3_OPTION = 'АР v3: шесть проверок по нормам (бета)';
const SIX_CHECKS = 'Запустить шесть проверок АР v3';
const STANDARD_FORM = 'data-start-run-control';
const V3_FORM = 'data-ar-v3-group-start';
const CHOICE = 'data-analysis-choice';
const DISABLED_SIX_CHECKS = /<button[^>]*disabled=""[^>]*>Запустить шесть проверок АР v3<\/button>/;

const allowed = () => installedPackFixture({ start_allowed: true });
const packStatus = vi.mocked(getArV3BetaPackStatus);
const startV3 = vi.mocked(startArV3BetaGroup);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function envelopeError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  return new ApiError(status, {
    contract_version: '1.41.0', error_code: code, message: 'A caller-safe sentence.', correlation_id: 'cid-choice',
    retryable, details: { dependency: 'metadata_store' },
  }, 'cid-choice');
}

function newClient(): QueryClient {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity, gcTime: Infinity }, mutations: { retry: false } },
  });
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), { items: [], page: { next_cursor: null } });
  client.setQueryData(queryKeys.runs.arV3PackStatus(), allowed());
  return client;
}

const tree = (client: QueryClient, props: Record<string, unknown> = { sectionCode: 'AR' }) =>
  createElement(QueryClientProvider, { client }, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, ...props } as never));

let live: LiveRender | null = null;
const storage = vi.hoisted(() => ({ writes: [] as string[] }));

beforeEach(() => {
  navigation.pushed.length = 0;
  storage.writes.length = 0;
  vi.resetAllMocks();
  // A browser's storage, recording every write: the choice must not be remembered anywhere.
  const recorder = {
    getItem: () => null,
    setItem: (key: string) => storage.writes.push(`set ${key}`),
    removeItem: (key: string) => storage.writes.push(`remove ${key}`),
    clear: () => storage.writes.push('clear'),
  };
  vi.stubGlobal('localStorage', recorder);
  vi.stubGlobal('sessionStorage', recorder);
  vi.mocked(estimateArV3GroupCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body, 'ar_v3_group') }) as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body, 'run') }) as never);
  packStatus.mockResolvedValue({ data: allowed() } as never);
  vi.mocked(listRuns).mockResolvedValue({ data: { items: [], page: { next_cursor: null } } } as never);
});

afterEach(async () => {
  await live?.unmount();
  live = null;
  vi.unstubAllGlobals();
});

describe('the standard analysis is the default every time', () => {
  it('opens on the standard analysis, with the ordinary form, and v3 is not sent by opening it', async () => {
    live = await mountLive(tree(newClient()));
    expect(live.markup()).toContain(`${CHOICE}="standard"`);
    expect(live.markup()).toContain(STANDARD_FORM);
    expect(live.markup()).not.toContain(V3_FORM);
    expect(startV3).not.toHaveBeenCalled();
    expect(vi.mocked(startRun)).not.toHaveBeenCalled();
  });

  it('returns to the standard analysis on a remount, after v3 was chosen, and writes nothing to storage', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    await live.change(V3_OPTION, 'ar_v3_beta');
    expect(live.markup()).toContain(`${CHOICE}="ar_v3_beta"`);
    await live.unmount();

    live = await mountLive(tree(client));
    expect(live.markup(), 'the form opened on the choice of the last visit').toContain(`${CHOICE}="standard"`);
    expect(live.markup()).not.toContain(V3_FORM);
    expect(storage.writes, 'a choice was remembered').toEqual([]);
  });
});

describe('choosing the other analysis replaces the form and clears what the first one held', () => {
  it('swaps the standard form for the v3 form, selectors included, and back', async () => {
    live = await mountLive(tree(newClient()));
    expect(live.markup()).toContain('data-start-mode'); // the standard form's three ways to start
    await live.change(V3_OPTION, 'ar_v3_beta');
    expect(live.markup()).toContain(V3_FORM);
    expect(live.markup()).not.toContain(STANDARD_FORM);
    expect(live.markup(), 'the executor selectors were kept beside a start that takes none').not.toContain('data-start-mode');
    expect(live.markup()).toContain('data-ar-v3-choice-note');
    expect(live.markup()).toContain('Это другой анализ, а не замена стандартного');
    await live.change(STANDARD_OPTION, 'standard');
    expect(live.markup()).toContain(STANDARD_FORM);
    expect(live.markup()).not.toContain(V3_FORM);
    expect(live.markup()).not.toContain('data-ar-v3-choice-note');
  });

  it('clears the v3 estimate, the consent and the refusal when the choice changes, so none is carried over', async () => {
    live = await mountLive(tree(newClient()));
    await live.change(V3_OPTION, 'ar_v3_beta');
    startV3.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(live.markup()).toContain('data-ar-v3-group-failure');
    expect(live.markup()).toContain('data-cost-approval');

    await live.change(STANDARD_OPTION, 'standard');
    await live.change(V3_OPTION, 'ar_v3_beta');
    expect(live.markup(), 'the refusal of the earlier visit to v3 is still on the form').not.toContain('data-ar-v3-group-failure');
    expect(live.markup(), 'the estimate was kept').not.toContain('data-cost-approval');
    expect(live.markup(), 'the start is enabled without a consent').toMatch(DISABLED_SIX_CHECKS);
    expect(startV3).toHaveBeenCalledTimes(1);
  });
});

describe('one start sends one analysis’s operation', () => {
  it('v3 sends startArV3BetaGroup with the version and the consent, opens the group review, and never sends startRun', async () => {
    live = await mountLive(tree(newClient()));
    await live.change(V3_OPTION, 'ar_v3_beta');
    startV3.mockResolvedValueOnce(ACCEPTED);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(startV3).toHaveBeenCalledTimes(1);
    const call = startV3.mock.calls[0]?.[0] as { body: { version_uid: string; cost_consent: { confirmed: boolean } } };
    expect(call.body.version_uid).toBe(VERSION_UID);
    expect(call.body.cost_consent.confirmed).toBe(true);
    expect(vi.mocked(startRun)).not.toHaveBeenCalled();
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('a refusal of v3 is said as itself and offers no single-run start in its place', async () => {
    live = await mountLive(tree(newClient()));
    await live.change(V3_OPTION, 'ar_v3_beta');
    startV3.mockRejectedValueOnce(envelopeError(409, 'conflict', false));
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(live.markup()).toContain('data-ar-v3-group-failure');
    expect(live.markup()).not.toContain(STANDARD_FORM);
    expect(live.count('Запустить прогон')).toBe(0);
    expect(vi.mocked(startRun)).not.toHaveBeenCalled();
  });

  it('a consent approved for the v3 estimate is not on the standard form after the choice goes back', async () => {
    live = await mountLive(tree(newClient()));
    await live.change(V3_OPTION, 'ar_v3_beta');
    await approveCost(live);
    expect(live.markup()).toContain('data-cost-approval');
    await live.change(STANDARD_OPTION, 'standard');
    expect(live.markup()).not.toContain('data-cost-approval');
    expect(live.markup()).toMatch(/<button[^>]*disabled=""[^>]*>Запустить прогон<\/button>/);
  });
});

describe('the allowance is withdrawn while the form is open', () => {
  async function refetch(client: QueryClient): Promise<void> {
    await live!.settle(() => client.refetchQueries({ queryKey: queryKeys.runs.arV3PackStatus() }));
  }

  it('takes the choice away at the next read of the status, and leaves the ordinary form', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    expect(live.markup()).toContain(CHOICE);
    packStatus.mockResolvedValueOnce({ data: installedPackFixture({ start_allowed: false }) } as never);
    await refetch(client);
    expect(live.markup()).not.toContain(CHOICE);
    expect(live.markup()).toContain(STANDARD_FORM);
  });

  it('takes it away when the status can no longer be read, and brings it back when it can', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    packStatus.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await refetch(client);
    expect(live.markup(), 'a failed re-read was taken for the earlier answer').not.toContain(CHOICE);
    packStatus.mockResolvedValueOnce({ data: allowed() } as never);
    await refetch(client);
    expect(live.markup()).toContain(`${CHOICE}="standard"`);
  });

  it('keeps the v3 form of a start that is on its way, and opens the group it is answered with', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    await live.change(V3_OPTION, 'ar_v3_beta');
    const reply = deferred<ApiResponse<ArV3BetaGroup>>();
    startV3.mockReturnValueOnce(reply.promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    packStatus.mockResolvedValueOnce({ data: installedPackFixture({ start_allowed: false }) } as never);
    await refetch(client);
    expect(live.markup(), 'the form of a start in flight was taken away').toContain(V3_FORM);
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);
    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });
});

describe('where there is no choice there is no request about it', () => {
  it('a version of another section and a comparison PDF never read the status', async () => {
    for (const props of [{ sectionCode: 'KJ' }, {}, { sectionCode: 'AR', uploadKind: 'comparison_pdf' }]) {
      const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity }, mutations: { retry: false } } });
      client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), { items: [], page: { next_cursor: null } });
      live = await mountLive(tree(client, props));
      expect(live.markup()).not.toContain(CHOICE);
      expect(packStatus, JSON.stringify(props)).not.toHaveBeenCalled();
      await live.unmount();
      live = null;
    }
  });
});
