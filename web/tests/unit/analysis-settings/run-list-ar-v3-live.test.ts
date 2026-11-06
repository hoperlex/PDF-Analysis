/**
 * `AR-V3-BETA-PACK-STATUS-WEB-FIX-01` and `-02`: the six-check start while the page around it changes,
 * as `3821261a` ("restore original-source text profile") left it.
 *
 * The run list used to mount the control, hold its idempotency key and its mutation observer, and keep it
 * drawn while a start was in flight although the pack status stopped being readable or the list itself
 * stopped showing. That owner decision removed the control from the run list: the ordinary start is the
 * only start there. The control, `useArV3GroupStartIntent` and the start's mutation remain, for a caller
 * that mounts them, so the file now pins two things:
 *
 *   - the run list mounts NO six-check control, whatever the pack status or the list does, and does not
 *     read the pack (`the run list ...`);
 *   - what a caller that DOES mount the control relies on, which the run list's tests used to prove through
 *     it: the key is the same on a retry and after the control was taken off the page, the observer opens
 *     the started group although no control is mounted, a pending start leaves its button disabled and a
 *     disabled button takes no press, and one version's pending start says nothing about another
 *     (`a caller that mounts the control`). The caller here is `Host`, which does what the run list did:
 *     it holds the intent, mounts the control and opens the accepted group's review.
 *
 * These tests mount the real control and the real mutation in a minimal DOM (`live-render.ts`), and read
 * what the request carried and where the page went. Only the transport is replaced: the generated
 * operations the tree calls, and the router.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { useRouter } from 'next/navigation';
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
  };
});

import { ApiError, getArV3BetaPackStatus, listRuns, queryKeys, startArV3BetaGroup, estimateArV3GroupCost } from '@/shared/api';
import type { ApiResponse, ArV3BetaGroup, ErrorCode, RunStatusPage } from '@/shared/api';
import { RUN_PAGE_LIMIT, arV3GroupReviewAddress } from '@/entities/audit-run';
import { StartArV3GroupControl, useArV3GroupStartIntent, useStartArV3Group } from '@/features/start-ar-v3-group';
import { RunList } from '@/widgets/run-list';

import { runStatus } from '../review/fixtures';

import { GROUP_ID } from './ar-v3-beta-review-fixtures';
import { NOT_INSTALLED_PACK, installedPackFixture } from './ar-v3-beta-pack-fixtures';
import { mountLive } from './live-render';
import { approveCost, costEstimate } from './cost-estimate-fixtures';
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
/** The six-check button as markup, disabled: what a pending start must leave on the page. */
const DISABLED_SIX_CHECKS = /<button[^>]*disabled=""[^>]*>Запустить шесть проверок АР v3<\/button>/;

const start = vi.mocked(startArV3BetaGroup);
const packStatus = vi.mocked(getArV3BetaPackStatus);

function envelopeError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  return new ApiError(
    status,
    {
      contract_version: '1.37.0',
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

/** The run list, as the page mounts it. */
const listTree = (client: QueryClient, versionUid: string = VERSION_UID) =>
  createElement(
    QueryClientProvider,
    { client },
    createElement(RunList, { projectUid: PROJECT_UID, versionUid } as never),
  );

/**
 * A caller of the six-check start: it holds the intent for as long as it lives, mounts the control while
 * `show` says so, and opens the review of the group the 202 names -- what the run list did. Keyed by the
 * version, as the run list was, because the observer holds one version's answer.
 */
function Host({ versionUid, show }: { readonly versionUid: string; readonly show: boolean }) {
  const router = useRouter();
  const intent = useArV3GroupStartIntent(versionUid as never);
  return show
    ? createElement(StartArV3GroupControl, {
        projectUid: PROJECT_UID as never,
        versionUid: versionUid as never,
        intent,
        onStarted: (group: ArV3BetaGroup) => router.push(arV3GroupReviewAddress(group.group_id)),
      })
    : null;
}

const tree = (client: QueryClient, versionUid: string = VERSION_UID, show = true) =>
  createElement(QueryClientProvider, { client }, createElement(Host, { key: versionUid, versionUid, show }));

let live: LiveRender | null = null;

beforeEach(() => {
  navigation.pushed.length = 0;
  vi.resetAllMocks();
  vi.mocked(estimateArV3GroupCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body, 'ar_v3_group') }) as never);
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

/** A first page with one run and a way on to a second: the state in which «Дальше» is drawn. */
const FIRST_PAGE: RunStatusPage = { items: [runStatus()], page: { next_cursor: 'cursor-2' } } as RunStatusPage;
const NEXT = 'Дальше';
const FIRST_PAGE_KEY = queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT);
const LIST_LOADING = 'Загрузка: прогоны этой версии';
const NEVER = (): Promise<never> => new Promise(() => undefined);

function pagedClient(): QueryClient {
  const client = newClient();
  client.setQueryData(FIRST_PAGE_KEY, FIRST_PAGE);
  return client;
}

describe('the run list mounts no six-check control, whatever the pack and the list do', () => {
  it('draws the ordinary start on an installed pack, no control, and does not observe the pack status', async () => {
    const client = newClient();
    live = await mountLive(listTree(client));
    expect(live.markup()).toContain('data-start-run-control');
    expect(live.markup()).not.toContain(CONTROL);
    expect(live.count(SIX_CHECKS)).toBe(0);
    expect(live.markup()).not.toContain('шесть проверок');
    const pack = client.getQueryCache().find({ queryKey: queryKeys.runs.arV3PackStatus() });
    expect(pack?.getObserversCount() ?? 0, 'the run list reads the pack status').toBe(0);
    expect(start).not.toHaveBeenCalled();
  });

  it('draws nothing in the control\u2019s place when the pack read fails, and nothing again when it recovers', async () => {
    const client = newClient();
    live = await mountLive(listTree(client));
    await failPackRead(client);
    expect(live.markup()).not.toContain(CONTROL);
    expect(live.markup()).not.toContain('шесть проверок');
    await recoverPackRead(client);
    expect(live.markup()).not.toContain(CONTROL);
    expect(live.markup()).not.toContain('шесть проверок');
    expect(live.markup()).toContain('data-start-run-control');
  });

  it('draws none while the list is loading, whatever the pack status is', async () => {
    for (const [name, pack] of [
      ['not installed', NOT_INSTALLED_PACK],
      ['a contract fault', { state: 'withdrawn' }],
      ['installed', installedPackFixture()],
    ] as const) {
      const client = newClient();
      client.removeQueries({ queryKey: FIRST_PAGE_KEY });
      client.setQueryData(queryKeys.runs.arV3PackStatus(), pack);
      vi.mocked(listRuns).mockImplementation(NEVER as never);
      live = await mountLive(listTree(client));
      expect(live.markup(), `${name}: the list was not loading`).toContain(LIST_LOADING);
      expect(live.markup(), name).not.toContain(CONTROL);
      expect(live.markup(), name).not.toContain('шесть проверок');
      await live.unmount();
      live = null;
    }
  });

  it('draws none while the list has failed, whatever the pack status is', async () => {
    for (const [name, pack] of [
      ['not installed', NOT_INSTALLED_PACK],
      ['installed', installedPackFixture()],
    ] as const) {
      const client = newClient();
      client.removeQueries({ queryKey: FIRST_PAGE_KEY });
      client.setQueryData(queryKeys.runs.arV3PackStatus(), pack);
      vi.mocked(listRuns).mockRejectedValue(envelopeError(503, 'dependency_unavailable', true));
      live = await mountLive(listTree(client));
      await live.settle(() => undefined);
      expect(live.markup(), `${name}: the list had not failed`).toContain('data-list-failure');
      expect(live.markup(), name).not.toContain(CONTROL);
      expect(live.markup(), name).not.toContain('шесть проверок');
      await live.unmount();
      live = null;
    }
  });

  it('draws none on the first page, while the next one loads, or after it failed to re-read', async () => {
    const client = pagedClient();
    live = await mountLive(listTree(client));
    expect(live.markup()).not.toContain(CONTROL);

    vi.mocked(listRuns).mockReturnValueOnce(deferred<{ data: RunStatusPage }>().promise as never);
    await live.press(NEXT);
    expect(live.markup(), 'the list did not go to its loading state').toContain(LIST_LOADING);
    expect(live.markup()).not.toContain(CONTROL);
    await live.unmount();

    const failing = pagedClient();
    live = await mountLive(listTree(failing));
    vi.mocked(listRuns).mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.settle(() => failing.refetchQueries({ queryKey: FIRST_PAGE_KEY }));
    expect(live.markup(), 'the list did not go to its error state').toContain('data-list-failure');
    expect(live.markup()).not.toContain(CONTROL);
    expect(start).not.toHaveBeenCalled();
  });
});

describe('a caller that mounts the control: the harness itself can see what these tests rely on', () => {
  it('draws the control and presses it', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    expect(live.markup()).toContain(CONTROL);
    expect(live.count(SIX_CHECKS)).toBe(1);
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(start).toHaveBeenCalledTimes(1);
    expect(live.markup()).toContain('запрос на шесть проверок');
  });

  it('draws nothing when the caller does not show it, and the control again when it does', async () => {
    const client = newClient();
    live = await mountLive(tree(client, VERSION_UID, false));
    expect(live.markup()).not.toContain(CONTROL);
    expect(live.markup()).not.toContain('шесть проверок');
    await live.update(tree(client, VERSION_UID, true));
    expect(live.markup()).toContain(CONTROL);
  });
});

describe('a start in flight when the control is taken off the page', () => {
  // The mutation's observer and the key are the caller's, so taking the control away does not lose them.
  it('still opens the started group', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);

    await live.update(tree(client, VERSION_UID, false));
    expect(live.markup(), 'the control stayed mounted').not.toContain(CONTROL);

    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed, 'the accepted group was not opened').toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('sends the SAME key when the control comes back after the request failed unseen', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    const first = keyOfCall(0);

    await live.update(tree(client, VERSION_UID, false));
    // The answer never reached the page (the connection dropped): the server may have made the group, the
    // page does not know.
    await live.settle(() => reply.reject(new TypeError('Failed to fetch')));
    expect(live.markup()).not.toContain(CONTROL);

    await live.update(tree(client, VERSION_UID, true));
    expect(live.markup()).toContain(CONTROL);

    start.mockResolvedValueOnce(ACCEPTED);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(start).toHaveBeenCalledTimes(2);
    expect(keyOfCall(1), 'a new key would make a second group of six runs').toBe(first);
  });

  it('shows the refusal, and retries under the same key, when the control comes back after a failed start', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    const first = keyOfCall(0);

    await live.update(tree(client, VERSION_UID, false));
    await live.settle(() => reply.reject(envelopeError(503, 'dependency_unavailable', true)));
    expect(live.count(RETRY), 'a refusal that came while no control was mounted drew a retry').toBe(0);

    await live.update(tree(client, VERSION_UID, true));
    expect(live.markup(), 'the control came back with no sign of the failed start').toContain('data-ar-v3-group-failure');
    expect(live.count(RETRY)).toBe(1);

    start.mockResolvedValueOnce(ACCEPTED);
    await live.press(RETRY);
    expect(keyOfCall(1), 'a retry under a new key would make a second group').toBe(first);
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('opens a group accepted while the control was away even when it is back by then', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);

    await live.update(tree(client, VERSION_UID, false));
    await live.update(tree(client, VERSION_UID, true));
    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });
});

describe('a caller mounted while a start is still on its way', () => {
  it('draws the control with its button disabled, so the pending start is not sent twice', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    await live.unmount();

    // The page is opened again; the earlier request is still pending.
    live = await mountLive(tree(client));
    expect(live.markup()).toContain(CONTROL);
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);
    expect(live.markup()).toContain('запрос на шесть проверок');

    // A browser does not dispatch a click to a disabled button; the harness must not either.
    expect(await live.press(SIX_CHECKS), 'a disabled button took a press').toBe(false);
    expect(start, 'a second request was sent while the first was pending').toHaveBeenCalledTimes(1);
  });
});

describe('a pending start leaves its button disabled, and a disabled button takes no press', () => {
  // `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`, finding 2: `press` used to call `onClick` whatever the
  // button's state, so a test could press a button the page had disabled and pass.
  it('refuses a second press while the first request is pending', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await approveCost(live);
    expect(await live.press(SIX_CHECKS)).toBe(true);
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);

    expect(await live.press(SIX_CHECKS)).toBe(false);
    expect(await live.press(SIX_CHECKS)).toBe(false);
    expect(start, 'a press on a disabled button reached the request').toHaveBeenCalledTimes(1);
  });

  it('stays disabled for as long as the start is unanswered, however the page around it moves', async () => {
    // The shape of an `inFlight` that never clears: the request is never answered. The button must
    // not come back, whatever re-renders and refetches happen around it.
    const client = pagedClient();
    live = await mountLive(tree(client));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    await recoverPackRead(client);
    await live.update(tree(client));
    await live.settle(() => client.refetchQueries({ queryKey: FIRST_PAGE_KEY }));
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);
    expect(await live.press(SIX_CHECKS)).toBe(false);
    expect(start).toHaveBeenCalledTimes(1);
  });

  it('is enabled again, and takes a press, once the request has been answered with a refusal', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(live.markup()).not.toMatch(DISABLED_SIX_CHECKS);
    start.mockResolvedValueOnce(ACCEPTED);
    await approveCost(live);
    expect(await live.press(SIX_CHECKS)).toBe(true);
    expect(start).toHaveBeenCalledTimes(2);
  });
});

describe('the key of one intent', () => {
  it('is the same on a retry after a failure, and on a second press', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(live.count(RETRY)).toBe(1);

    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.press(RETRY);
    start.mockResolvedValueOnce(ACCEPTED);
    await approveCost(live);
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
    await approveCost(live);
    await live.press(SIX_CHECKS);
    const forFirstVersion = keyOfCall(0);

    await live.update(tree(client, OTHER_VERSION_UID));
    // A new version requires its own estimate/approval, but has no pending start.
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);
    expect(live.markup()).not.toContain('запрос на шесть проверок');
    start.mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await approveCost(live);
    await live.press(SIX_CHECKS);
    const forSecondVersion = keyOfCall(1);
    expect(forSecondVersion).not.toBe(forFirstVersion);

    expect(start.mock.calls.map((call) => (call[0] as { body: { version_uid: string } }).body.version_uid)).toEqual([
      VERSION_UID,
      OTHER_VERSION_UID,
    ]);
  });
});

describe('a start pending for one version says nothing about another', () => {
  // `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`, finding 4. Next remounts the page on a `[version_uid]`
  // change, so production never changes the version of a mounted list; the live harness's
  // `update()` does, and `useIsMutating` kept answering for the first version until a
  // mutation-cache event happened.
  it('allows an independent estimate and approved start when the caller switches version', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await approveCost(live);
    await live.press(SIX_CHECKS);
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);

    await live.update(tree(client, OTHER_VERSION_UID));
    // The new version is disabled for missing cost approval, not for the old pending start.
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);
    expect(live.markup()).not.toContain('запрос на шесть проверок');
    start.mockResolvedValueOnce(ACCEPTED);
    await approveCost(live);
    expect(await live.press(SIX_CHECKS)).toBe(true);
    expect(start).toHaveBeenCalledTimes(2);
  });

  it('the intent hook recomputes inFlight for the version it is given, not only on a cache event', async () => {
    const client = newClient();
    const reading: string[] = [];
    function Probe({ versionUid }: { versionUid: string }) {
      const intent = useArV3GroupStartIntent(versionUid as never);
      const send = useStartArV3Group();
      reading.push(`${versionUid === VERSION_UID ? 'A' : 'B'}:${intent.inFlight}`);
      return createElement(
        'button',
        { onClick: () => send.mutate({ versionUid: VERSION_UID, idempotencyKey: 'ik-probe' }) },
        'go',
      );
    }
    const probe = (versionUid: string) =>
      createElement(QueryClientProvider, { client }, createElement(Probe, { versionUid }));
    live = await mountLive(probe(VERSION_UID));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await live.press('go');
    expect(reading[reading.length - 1]).toBe('A:true');

    await live.update(probe(OTHER_VERSION_UID));
    expect(reading[reading.length - 1], 'the hook still answers for the first version').toBe('B:false');
    await live.update(probe(VERSION_UID));
    expect(reading[reading.length - 1]).toBe('A:true');
  });
});
