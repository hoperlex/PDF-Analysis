/**
 * `AR-V3-BETA-PACK-STATUS-WEB-FIX-01`: the six-check start while the page around it changes.
 *
 * The static tests in `tests/unit/screens/run-list-ar-v3-start.test.ts` pin which status draws the
 * control. They cannot say what a status that CHANGES does to a start already sent: the control is
 * drawn only on an installed pack, so a failed re-read of the pack unmounts it, and with it the
 * mutation's observer (the per-call `onSuccess` that navigates) and the idempotency key held in a
 * `useRef`. These tests mount the real run list, the real control and the real mutation in a
 * minimal DOM (`live-render.ts`), move the pack status under a request in flight, and read what
 * the request carried and where the page went.
 *
 * Only the transport is replaced: the four generated operations the tree calls, and the router.
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
    startRun: vi.fn(),
  };
});

import { ApiError, getArV3BetaPackStatus, listRuns, queryKeys, startArV3BetaGroup } from '@/shared/api';
import type { ApiResponse, ArV3BetaGroup, ErrorCode } from '@/shared/api';
import { RUN_PAGE_LIMIT, arV3GroupReviewAddress } from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';

import { GROUP_ID } from './ar-v3-beta-review-fixtures';
import { installedPackFixture } from './ar-v3-beta-pack-fixtures';
import { mountLive } from './live-render';
import type { LiveRender } from './live-render';

const PROJECT_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const OTHER_VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const GROUP = { group_id: GROUP_ID, project_uid: PROJECT_UID, version_uid: VERSION_UID } as ArV3BetaGroup;

/** The server's 202: what `startArV3BetaGroup` resolves with. */
const ACCEPTED: ApiResponse<ArV3BetaGroup> = { data: GROUP, status: 202, correlationId: 'cid-live' };
type Accepted = ApiResponse<ArV3BetaGroup>;

const SIX_CHECKS = 'Запустить шесть проверок АР v3';
const RETRY = 'Повторить с тем же ключом';
const CONTROL = 'data-ar-v3-group-start';

const start = vi.mocked(startArV3BetaGroup);
const packStatus = vi.mocked(getArV3BetaPackStatus);

function envelopeError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  return new ApiError(
    status,
    {
      contract_version: '1.5.0',
      error_code: code,
      message: 'A caller-safe sentence.',
      correlation_id: 'cid-live',
      retryable,
      details: { dependency: 'metadata_store' },
    },
    'cid-live',
  );
}

/** The answer of a pack re-read that fails: what `getArV3BetaPackStatus` rejects with. */
const readFailure = () => envelopeError(503, 'dependency_unavailable', true);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function newClient(): QueryClient {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity, gcTime: Infinity }, mutations: { retry: false } },
  });
  for (const versionUid of [VERSION_UID, OTHER_VERSION_UID]) {
    client.setQueryData(queryKeys.runs.list(versionUid, undefined, RUN_PAGE_LIMIT), { items: [], page: { next_cursor: null } });
  }
  client.setQueryData(queryKeys.runs.arV3PackStatus(), installedPackFixture());
  return client;
}

const tree = (client: QueryClient, versionUid: string = VERSION_UID) =>
  createElement(
    QueryClientProvider,
    { client },
    createElement(RunList, { projectUid: PROJECT_UID, versionUid } as never),
  );

let live: LiveRender | null = null;

beforeEach(() => {
  navigation.pushed.length = 0;
  vi.resetAllMocks();
  // Whatever re-reads the tree triggers (an accepted start invalidates `runs`) find the pack
  // installed and no runs, unless a test says otherwise.
  packStatus.mockResolvedValue({ data: installedPackFixture() } as never);
  vi.mocked(listRuns).mockResolvedValue({ data: { items: [], page: { next_cursor: null } } } as never);
});

afterEach(async () => {
  await live?.unmount();
  live = null;
});

/** Fail the next pack re-read and run it, as a flaky network would while the page is open. */
async function failPackRead(client: QueryClient): Promise<void> {
  packStatus.mockRejectedValueOnce(readFailure());
  await live!.settle(() => client.refetchQueries({ queryKey: queryKeys.runs.arV3PackStatus() }));
}

async function recoverPackRead(client: QueryClient): Promise<void> {
  packStatus.mockResolvedValueOnce({ data: installedPackFixture() } as never);
  await live!.settle(() => client.refetchQueries({ queryKey: queryKeys.runs.arV3PackStatus() }));
}

const keyOfCall = (index: number): string => {
  const call = start.mock.calls[index];
  if (call === undefined) throw new Error(`startArV3BetaGroup was called ${start.mock.calls.length} times`);
  return (call[0] as { idempotencyKey: string }).idempotencyKey;
};

describe('the harness itself can see what these tests rely on', () => {
  it('draws the control on an installed pack and presses it', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    expect(live.markup()).toContain(CONTROL);
    expect(live.count(SIX_CHECKS)).toBe(1);
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await live.press(SIX_CHECKS);
    expect(start).toHaveBeenCalledTimes(1);
    expect(live.markup()).toContain('запрос на шесть проверок');
  });

  it('draws nothing in its place once the pack read has failed', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    await failPackRead(client);
    expect(live.markup()).not.toContain(CONTROL);
    expect(live.markup()).not.toContain('шесть проверок');
    await recoverPackRead(client);
    expect(live.markup()).toContain(CONTROL);
  });
});

describe('a start in flight when the pack status stops being readable', () => {
  it('keeps the control mounted and still opens the started group', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);

    await failPackRead(client);
    expect(live.markup(), 'the control was unmounted under a request in flight').toContain(CONTROL);
    expect(live.markup()).toContain('запрос на шесть проверок');

    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed, 'the accepted group was not opened').toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('draws nothing again once the request has settled and the pack is still unreadable', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);
    await failPackRead(client);

    // The invalidation an accepted start triggers re-reads the pack; it is still failing.
    packStatus.mockRejectedValue(readFailure());
    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
    expect(live.markup()).not.toContain(CONTROL);
    expect(live.markup()).not.toContain('шесть проверок');
  });

  it('sends the SAME key when the control comes back after the request failed unseen', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);
    const first = keyOfCall(0);

    await failPackRead(client);
    // The answer never reached the page (the connection dropped): the server may have made the
    // group, the page does not know. The pack is still unreadable, so the control goes.
    packStatus.mockRejectedValue(readFailure());
    await live.settle(() => reply.reject(new TypeError('Failed to fetch')));
    expect(live.markup()).not.toContain(CONTROL);

    packStatus.mockResolvedValue({ data: installedPackFixture() } as never);
    await live.settle(() => client.refetchQueries({ queryKey: queryKeys.runs.arV3PackStatus() }));
    expect(live.markup()).toContain(CONTROL);

    start.mockResolvedValueOnce(ACCEPTED);
    await live.press(SIX_CHECKS);
    expect(start).toHaveBeenCalledTimes(2);
    expect(keyOfCall(1), 'a new key would make a second group of six runs').toBe(first);
  });
});

describe('a list mounted while a start is still on its way', () => {
  it('draws the control with its button disabled, so the pending start is not sent twice', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await live.press(SIX_CHECKS);
    await live.unmount();

    // The page is opened again; the pack read fails, but the earlier request is still pending.
    packStatus.mockRejectedValueOnce(readFailure());
    await client.refetchQueries({ queryKey: queryKeys.runs.arV3PackStatus() });
    live = await mountLive(tree(client));
    expect(live.markup()).toContain(CONTROL);
    expect(live.markup()).toMatch(/<button[^>]*disabled=""[^>]*>Запустить шесть проверок АР v3<\/button>/);
    expect(live.markup()).toContain('запрос на шесть проверок');
  });
});

describe('the key of one intent', () => {
  it('is the same on a retry after a failure, and on a second press', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.press(SIX_CHECKS);
    expect(live.count(RETRY)).toBe(1);

    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.press(RETRY);
    start.mockResolvedValueOnce(ACCEPTED);
    await live.press(SIX_CHECKS);

    expect(start).toHaveBeenCalledTimes(3);
    expect(keyOfCall(0).length).toBeGreaterThan(8);
    expect(keyOfCall(1)).toBe(keyOfCall(0));
    expect(keyOfCall(2)).toBe(keyOfCall(0));
  });

  it('is a different one for a different version', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.press(SIX_CHECKS);
    const forFirstVersion = keyOfCall(0);

    await live.update(tree(client, OTHER_VERSION_UID));
    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.press(SIX_CHECKS);
    const forSecondVersion = keyOfCall(1);
    expect(forSecondVersion).not.toBe(forFirstVersion);

    expect(start.mock.calls.map((call) => (call[0] as { body: { version_uid: string } }).body.version_uid)).toEqual([
      VERSION_UID,
      OTHER_VERSION_UID,
    ]);
  });
});
