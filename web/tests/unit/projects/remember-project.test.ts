/**
 * `UIP-G-06` (owner ruling Г7-B): the account's last object, read from the one `getMe` query and kept by `setMyLastProject`.
 *
 * Three hooks, read here as the screens use them:
 *
 *   - `useLastProject`: what `getMe` says (`last_project_uid`), with `known` and `pending` told apart, and no request where it
 *     is told not to ask;
 *   - `useRememberProject`: the command of one choice. One idempotency key per choice, nothing repeats it on its own, the
 *     answer is written into the account's cache, and a refusal comes back as a sentence rather than as a throw;
 *   - `useCurrentProject`: the address first, the account's object where the address is silent, and `pending` while the account
 *     has not answered.
 *
 * Mounted live (`analysis-settings/live-render.ts`): a press, an effect and a settled request are events a one-pass render cannot
 * deliver. Only the transport is replaced.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, getMe: vi.fn(), setMyLastProject: vi.fn() };
});

import { ApiError, getMe, queryKeys, setMyLastProject } from '@/shared/api';
import type { Account, ErrorEnvelope } from '@/shared/api';
import { useLastProject, useRememberProject } from '@/entities/account';
import { useCurrentProject } from '@/entities/project';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

const me = vi.mocked(getMe);
const command = vi.mocked(setMyLastProject);

const account = (lastProject: string | null | undefined): Account =>
  ({ user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles: ['expert'], ...(lastProject === undefined ? {} : { last_project_uid: lastProject }) }) as unknown as Account;

function refusal(status: number, code: ErrorEnvelope['error_code']): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.55.0',
    error_code: code,
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-remember-404',
    retryable: false,
  };
  return new ApiError(status, envelope, 'cid-remember-404');
}

const freshClient = (): QueryClient =>
  new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

const under = (client: QueryClient, element: ReactElement): ReactElement => createElement(QueryClientProvider, { client }, element);

async function settled(view: LiveRender): Promise<void> {
  for (let round = 0; round < 5; round += 1) {
    await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
  }
}

let live: LiveRender | null = null;
beforeEach(() => {
  me.mockReset();
  me.mockImplementation((async () => ({ data: account(null), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
  command.mockReset();
  command.mockImplementation((async () => ({ data: undefined, status: 204, correlationId: 'cid-command' })) as unknown as typeof setMyLastProject);
});
afterEach(async () => {
  await live?.unmount();
  live = null;
});

// ------------------------------------------------------------------------------------ useLastProject

function LastProjectProbe({ enabled }: { readonly enabled?: boolean }) {
  const last = useLastProject(enabled === undefined ? {} : { enabled });
  return createElement('p', { 'data-last': '' }, JSON.stringify(last));
}
const lastOf = (view: LiveRender): { known: boolean; pending: boolean; projectUid: string | null } =>
  JSON.parse(/data-last="">([^<]*)</.exec(view.markup())?.[1]?.replace(/&quot;/g, '"') ?? 'null');

describe('useLastProject: what getMe says of the object the account chose last', () => {
  it('is pending while getMe is on its way, then known with the object', async () => {
    me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    live = await mountLive(under(freshClient(), createElement(LastProjectProbe)));
    expect(lastOf(live)).toEqual({ known: false, pending: true, projectUid: null });
    await settled(live);
    expect(lastOf(live)).toEqual({ known: true, pending: false, projectUid: A });
  });

  it('is known with null for an account that chose none, and for an answer that does not carry the field', async () => {
    live = await mountLive(under(freshClient(), createElement(LastProjectProbe)));
    await settled(live);
    expect(lastOf(live)).toEqual({ known: true, pending: false, projectUid: null });
    await live.unmount();

    me.mockImplementation((async () => ({ data: account(undefined), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    live = await mountLive(under(freshClient(), createElement(LastProjectProbe)));
    await settled(live);
    expect(lastOf(live)).toEqual({ known: true, pending: false, projectUid: null });
  });

  it('is neither known nor pending when the read failed: the screens then show «Все объекты»', async () => {
    me.mockRejectedValue(refusal(503, 'dependency_unavailable'));
    live = await mountLive(under(freshClient(), createElement(LastProjectProbe)));
    await settled(live);
    expect(lastOf(live)).toEqual({ known: false, pending: false, projectUid: null });
  });

  it('asks nothing where it is told not to, and reads the cache all the same', async () => {
    live = await mountLive(under(freshClient(), createElement(LastProjectProbe, { enabled: false })));
    await settled(live);
    expect(me).not.toHaveBeenCalled();
    expect(lastOf(live)).toEqual({ known: false, pending: false, projectUid: null });
    await live.unmount();

    const client = freshClient();
    client.setQueryData(queryKeys.account.me(), account(B));
    live = await mountLive(under(client, createElement(LastProjectProbe, { enabled: false })));
    expect(lastOf(live)).toEqual({ known: true, pending: false, projectUid: B });
    expect(me).not.toHaveBeenCalled();
  });

  it('is one getMe for any number of readers: the account\'s query is shared', async () => {
    live = await mountLive(under(freshClient(), createElement('div', null, createElement(LastProjectProbe), createElement(LastProjectProbe))));
    await settled(live);
    expect(me).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------------- useRememberProject

function RememberProbe() {
  const { remember, failure, reset } = useRememberProject();
  return createElement(
    'div',
    null,
    createElement('button', { type: 'button', onClick: () => remember(A) }, 'Запомнить A'),
    createElement('button', { type: 'button', onClick: () => remember(B) }, 'Запомнить B'),
    createElement('button', { type: 'button', onClick: reset }, 'Забыть отказ'),
    failure === null ? null : createElement('p', { 'data-failure': failure.correlationId ?? 'none' }, failure.detail),
  );
}

describe('useRememberProject: one choice is one command', () => {
  it('sends the object with an idempotency key, and nothing else', async () => {
    live = await mountLive(under(freshClient(), createElement(RememberProbe)));
    expect(await live.press('Запомнить A')).toBe(true);
    await settled(live);
    expect(command).toHaveBeenCalledTimes(1);
    expect(command.mock.calls[0]?.[0]).toEqual({ body: { project_uid: A }, idempotencyKey: expect.stringMatching(/^ik_/) });
  });

  it('mints a new key for every choice, even for the same object', async () => {
    live = await mountLive(under(freshClient(), createElement(RememberProbe)));
    await live.press('Запомнить A');
    await settled(live);
    await live.press('Запомнить A');
    await settled(live);
    await live.press('Запомнить B');
    await settled(live);
    const keys = command.mock.calls.map((call) => (call[0] as { idempotencyKey: string }).idempotencyKey);
    expect(keys).toHaveLength(3);
    expect(new Set(keys).size).toBe(3);
  });

  it('writes the stored choice into the account\'s answer at once, and refreshes it behind', async () => {
    const client = freshClient();
    client.setQueryData(queryKeys.account.me(), account(null));
    me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    // a reader of the account is mounted, so the invalidated answer is read again
    live = await mountLive(under(client, createElement('div', null, createElement(RememberProbe), createElement(LastProjectProbe))));
    await live.press('Запомнить A');
    expect(client.getQueryData<Account>(queryKeys.account.me())?.last_project_uid).toBe(A);
    await settled(live);
    expect(me).toHaveBeenCalledTimes(1);
    expect(lastOf(live)).toEqual({ known: true, pending: false, projectUid: A });
  });

  it('does not invent an account where none is cached', async () => {
    const client = freshClient();
    live = await mountLive(under(client, createElement(RememberProbe)));
    await live.press('Запомнить A');
    await settled(live);
    expect(client.getQueryData(queryKeys.account.me())).toBeUndefined();
  });

  it('does not throw at the caller on a refusal: it says it, once, and does not repeat the command on its own', async () => {
    command.mockRejectedValue(refusal(404, 'not_found'));
    const client = freshClient();
    client.setQueryData(queryKeys.account.me(), account(B));
    live = await mountLive(under(client, createElement(RememberProbe)));
    expect(await live.press('Запомнить A')).toBe(true);
    await settled(live);
    expect(command).toHaveBeenCalledTimes(1);
    expect(live.markup()).toContain('data-failure="cid-remember-404"');
    // the cache still holds the object the server has
    expect(client.getQueryData<Account>(queryKeys.account.me())?.last_project_uid).toBe(B);
  });

  it('a transport failure is a sentence too, never the thrown value\'s own message', async () => {
    command.mockRejectedValue(new Error('SECRET internal detail'));
    live = await mountLive(under(freshClient(), createElement(RememberProbe)));
    await live.press('Запомнить A');
    await settled(live);
    expect(live.markup()).toContain('data-failure="none"');
    expect(live.markup()).not.toContain('SECRET');
  });

  it('the refusal stays until the next choice or a reset, and the next choice that succeeds clears it', async () => {
    command.mockRejectedValueOnce(refusal(404, 'not_found'));
    live = await mountLive(under(freshClient(), createElement(RememberProbe)));
    await live.press('Запомнить A');
    await settled(live);
    expect(live.markup()).toContain('data-failure');
    await live.press('Запомнить B');
    await settled(live);
    expect(live.markup()).not.toContain('data-failure');

    command.mockRejectedValueOnce(refusal(404, 'not_found'));
    await live.press('Запомнить A');
    await settled(live);
    expect(live.markup()).toContain('data-failure');
    await live.press('Забыть отказ');
    await settled(live);
    expect(live.markup()).not.toContain('data-failure');
  });
});

// ---------------------------------------------------------------------------------- useCurrentProject

function CurrentProbe({ fallback = '/dashboard' }: { readonly fallback?: string }) {
  return createElement('p', { 'data-current': '' }, JSON.stringify(useCurrentProject(fallback)));
}
const currentOf = (view: LiveRender): { projectUid: string | null; source: string; pending: boolean } =>
  JSON.parse(/data-current="">([^<]*)</.exec(view.markup())?.[1]?.replace(/&quot;/g, '"') ?? 'null');

const atAddress = (pathname: string, query: string, element: ReactElement): ReactElement =>
  createElement(PathnameContext.Provider, { value: pathname }, createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, element));

describe('useCurrentProject: the address first, then the account\'s object', () => {
  it('is pending, for «Все объекты», while the account has not answered, then the account\'s object', async () => {
    me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    live = await mountLive(under(freshClient(), atAddress('/dashboard', '', createElement(CurrentProbe))));
    expect(currentOf(live)).toEqual({ projectUid: null, source: 'none', pending: true });
    await settled(live);
    expect(currentOf(live)).toEqual({ projectUid: A, source: 'remembered', pending: false });
  });

  it('takes the address where it names an object, and does not ask the account', async () => {
    me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    live = await mountLive(under(freshClient(), atAddress('/dashboard', `project=${B}`, createElement(CurrentProbe))));
    await settled(live);
    expect(currentOf(live)).toEqual({ projectUid: B, source: 'query', pending: false });
    await live.unmount();
    live = await mountLive(under(freshClient(), atAddress('/dashboard', 'project=all', createElement(CurrentProbe))));
    await settled(live);
    expect(currentOf(live)).toEqual({ projectUid: null, source: 'all', pending: false });
    live = await (async () => {
      await live!.unmount();
      return mountLive(under(freshClient(), atAddress(`/projects/${A}`, '', createElement(CurrentProbe))));
    })();
    await settled(live);
    expect(currentOf(live)).toEqual({ projectUid: A, source: 'path', pending: false });
    expect(me).not.toHaveBeenCalled();
  });

  it('does not ask the account on a screen that does not follow the object', async () => {
    live = await mountLive(under(freshClient(), atAddress('/queue', '', createElement(CurrentProbe, { fallback: '/queue' }))));
    await settled(live);
    expect(currentOf(live)).toEqual({ projectUid: null, source: 'none', pending: false });
    expect(me).not.toHaveBeenCalled();
  });

  it('stands for the screen\'s own address outside the app router, so its class is known', async () => {
    const client = freshClient();
    client.setQueryData(queryKeys.account.me(), account(B));
    live = await mountLive(under(client, createElement(CurrentProbe, { fallback: '/dashboard' })));
    expect(currentOf(live)).toEqual({ projectUid: B, source: 'remembered', pending: false });
    await live.unmount();
    live = await mountLive(under(client, createElement(CurrentProbe, { fallback: '/queue' })));
    expect(currentOf(live)).toEqual({ projectUid: null, source: 'none', pending: false });
  });

  it('ends pending when the account\'s read failed, with «Все объекты»', async () => {
    me.mockRejectedValue(refusal(503, 'dependency_unavailable'));
    live = await mountLive(under(freshClient(), atAddress('/dashboard', '', createElement(CurrentProbe))));
    await settled(live);
    expect(currentOf(live)).toEqual({ projectUid: null, source: 'none', pending: false });
  });
});
