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
import type { ApiResponse, ArV3BetaGroup, ErrorCode, RunStatusPage } from '@/shared/api';
import { RUN_PAGE_LIMIT, arV3GroupReviewAddress } from '@/entities/audit-run';
import { useArV3GroupStartIntent, useStartArV3Group } from '@/features/start-ar-v3-group';
import { RunList } from '@/widgets/run-list';

import { runStatus } from '../review/fixtures';

import { GROUP_ID } from './ar-v3-beta-review-fixtures';
import { NOT_INSTALLED_PACK, installedPackFixture } from './ar-v3-beta-pack-fixtures';
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
/** The six-check button as markup, disabled: what a pending start must leave on the page. */
const DISABLED_SIX_CHECKS = /<button[^>]*disabled=""[^>]*>Запустить шесть проверок АР v3<\/button>/;

const start = vi.mocked(startArV3BetaGroup);
const packStatus = vi.mocked(getArV3BetaPackStatus);

function envelopeError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  return new ApiError(
    status,
    {
      contract_version: '1.6.0',
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
    await live.press(SIX_CHECKS);
    expect(live.markup()).not.toMatch(DISABLED_SIX_CHECKS);
    start.mockResolvedValueOnce(ACCEPTED);
    expect(await live.press(SIX_CHECKS)).toBe(true);
    expect(start).toHaveBeenCalledTimes(2);
  });
});

/** A first page with one run and a way on to a second: the state in which «Дальше» is drawn. */
const FIRST_PAGE: RunStatusPage = { items: [runStatus()], page: { next_cursor: 'cursor-2' } } as RunStatusPage;
const NEXT = 'Дальше';
const FIRST_PAGE_KEY = queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT);
const LIST_LOADING = 'Загрузка: прогоны этой версии';

function pagedClient(): QueryClient {
  const client = newClient();
  client.setQueryData(FIRST_PAGE_KEY, FIRST_PAGE);
  return client;
}

describe('a start in flight when the run list itself stops showing the list', () => {
  // `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`, finding 1. The list's query key carries the cursor and
  // the query has no placeholder data, so «Дальше» turns the list into its loading state, and a
  // failed re-read turns it into its error state; both returned before the control was drawn.

  it('keeps the control and still opens the started group while the next page loads', async () => {
    const client = pagedClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);

    vi.mocked(listRuns).mockReturnValueOnce(deferred<{ data: RunStatusPage }>().promise as never);
    await live.press(NEXT);
    expect(live.markup(), 'the list did not go to its loading state').toContain(LIST_LOADING);
    expect(live.markup(), 'the control was unmounted under a request in flight').toContain(CONTROL);
    expect(live.markup()).toContain('запрос на шесть проверок');

    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed, 'the accepted group was not opened').toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('keeps the control and still opens the started group while the list failed to re-read', async () => {
    const client = pagedClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);

    vi.mocked(listRuns).mockRejectedValueOnce(envelopeError(503, 'dependency_unavailable', true));
    await live.settle(() => client.refetchQueries({ queryKey: FIRST_PAGE_KEY }));
    expect(live.markup(), 'the list did not go to its error state').toContain('data-list-failure');
    expect(live.markup(), 'the control was unmounted under a request in flight').toContain(CONTROL);

    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed, 'the accepted group was not opened').toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('shows the refusal, and retries under the same key, when the page comes back after a failed start', async () => {
    const client = pagedClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);
    const first = keyOfCall(0);

    const nextPage = deferred<{ data: RunStatusPage }>();
    vi.mocked(listRuns).mockReturnValueOnce(nextPage.promise as never);
    await live.press(NEXT);
    await live.settle(() => reply.reject(envelopeError(503, 'dependency_unavailable', true)));
    expect(live.count(RETRY), 'a refusal that came while the list was loading was swallowed').toBe(0);

    await live.settle(() => nextPage.resolve({ data: FIRST_PAGE }));
    expect(live.markup(), 'the control came back with no sign of the failed start').toContain('data-ar-v3-group-failure');
    expect(live.count(RETRY)).toBe(1);

    start.mockResolvedValueOnce(ACCEPTED);
    await live.press(RETRY);
    expect(keyOfCall(1), 'a retry under a new key would make a second group').toBe(first);
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });

  it('opens a group accepted while the list was loading even when it is back by then', async () => {
    const client = pagedClient();
    live = await mountLive(tree(client));
    const reply = deferred<Accepted>();
    start.mockReturnValueOnce(reply.promise);
    await live.press(SIX_CHECKS);

    const nextPage = deferred<{ data: RunStatusPage }>();
    vi.mocked(listRuns).mockReturnValueOnce(nextPage.promise as never);
    await live.press(NEXT);
    await live.settle(() => nextPage.resolve({ data: FIRST_PAGE }));
    await live.settle(() => reply.resolve(ACCEPTED));
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);
  });
});

describe('a fresh visit draws no six-check control while the list is not showing', () => {
  const NEVER = (): Promise<never> => new Promise(() => undefined);

  it('draws none while the list is loading, whatever the pack status is', async () => {
    for (const [name, pack] of [
      ['not installed', NOT_INSTALLED_PACK],
      ['a contract fault', { state: 'withdrawn' }],
      ['installed', installedPackFixture()],
    ] as const) {
      const client = newClient();
      client.removeQueries({ queryKey: queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT) });
      client.setQueryData(queryKeys.runs.arV3PackStatus(), pack);
      vi.mocked(listRuns).mockImplementation(NEVER as never);
      live = await mountLive(tree(client));
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
      client.removeQueries({ queryKey: queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT) });
      client.setQueryData(queryKeys.runs.arV3PackStatus(), pack);
      vi.mocked(listRuns).mockRejectedValue(envelopeError(503, 'dependency_unavailable', true));
      live = await mountLive(tree(client));
      await live.settle(() => undefined);
      expect(live.markup(), `${name}: the list had not failed`).toContain('data-list-failure');
      expect(live.markup(), name).not.toContain(CONTROL);
      expect(live.markup(), name).not.toContain('шесть проверок');
      await live.unmount();
      live = null;
    }
  });

  it('draws none once a start has settled and the list is loading again', async () => {
    const client = pagedClient();
    // The invalidation an accepted start triggers re-reads the first page; it still has a next.
    vi.mocked(listRuns).mockResolvedValue({ data: FIRST_PAGE } as never);
    live = await mountLive(tree(client));
    start.mockResolvedValueOnce(ACCEPTED);
    await live.press(SIX_CHECKS);
    expect(navigation.pushed).toEqual([arV3GroupReviewAddress(GROUP_ID)]);

    vi.mocked(listRuns).mockReturnValue(deferred<{ data: RunStatusPage }>().promise as never);
    await live.press(NEXT);
    expect(live.markup()).toContain(LIST_LOADING);
    expect(live.markup(), 'a settled start must not keep the control drawn').not.toContain(CONTROL);
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
    // No start is pending for the other version, so nothing about its control says one is.
    expect(live.markup()).not.toMatch(DISABLED_SIX_CHECKS);
    expect(live.markup()).not.toContain('запрос на шесть проверок');
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

describe('a start pending for one version says nothing about another', () => {
  // `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`, finding 4. Next remounts the page on a `[version_uid]`
  // change, so production never changes the version of a mounted list; the live harness's
  // `update()` does, and `useIsMutating` kept answering for the first version until a
  // mutation-cache event happened.
  it('keeps the other version\'s button enabled when the list switches version', async () => {
    const client = newClient();
    live = await mountLive(tree(client));
    start.mockReturnValueOnce(deferred<Accepted>().promise);
    await live.press(SIX_CHECKS);
    expect(live.markup()).toMatch(DISABLED_SIX_CHECKS);

    await live.update(tree(client, OTHER_VERSION_UID));
    expect(live.markup(), 'the other version shows a start it never sent').not.toMatch(DISABLED_SIX_CHECKS);
    expect(live.markup()).not.toContain('запрос на шесть проверок');
    start.mockResolvedValueOnce(ACCEPTED);
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
