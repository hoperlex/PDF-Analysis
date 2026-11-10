/**
 * One «Пауза» button with two items, and the badge «Векторы на паузе» only during a pause (`PAUSE-WEB-01`, `ADR-0029` decision 8).
 *
 * The strip is MOUNTED, not just rendered (`mountLive`: real React state, effects and clicks, no browser), because the claims are
 * about a sequence: the button opens, an item is chosen, one command goes out. What must not happen is read off the mocked
 * command list; what must not be drawn is read off the markup. Each claim has a negative that can fail.
 *
 * The role rules sit on both layers: `PauseStatusLive` (an administrator gets the button; an expert gets the badges and no button; a
 * viewer gets nothing) and the frame's own gate (`offersPauseStatus`: the strip is not even mounted for a viewer).
 */

import { QueryClientProvider } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getExecutionDispatch: vi.fn(), getVectorControl: vi.fn(), setExecutionPaused: vi.fn(), setVectorPaused: vi.fn(),
}));

import { offersPauseStatus } from '@/_app/navigation';
import {
  ApiError, getExecutionDispatch, getVectorControl, queryKeys, setExecutionPaused, setVectorPaused,
} from '@/shared/api';
import type { VectorControl } from '@/shared/api';
import { canSeePause, vectorControlKey, vectorsPauseOf } from '@/entities/execution';
import {
  PAUSED_LABEL, PauseStatusLive, PauseStatusView, dispatchItemLabel, pauseMenuProps, vectorsItemLabel,
} from '@/widgets/pause-status';
import type { PauseStatusViewProps } from '@/widgets/pause-status';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';

const BADGE = 'Векторы на паузе';
const TRIGGER = 'Пауза▾';
const QUEUE_ITEM = 'Выдача анализа — приостановить';
const QUEUE_ITEM_RESUME = 'Выдача анализа — возобновить';
const VECTORS_ITEM = 'Векторы — приостановить';
const VECTORS_ITEM_RESUME = 'Векторы — возобновить';
const RUNNING = { paused: false, changed_at: '2026-11-05T10:00:00Z' };
const STOPPED = { paused: true, changed_at: '2026-11-05T10:00:00Z' };

const control = (over: Partial<VectorControl> = {}): VectorControl => ({
  paused: false, window: { start: '01:00', end: '05:00', tz: 'Europe/Moscow' },
  window_changed_at: '2026-11-10T22:00:00Z', window_state: 'closed', ...over,
});

let live: LiveRender | null = null;
/** What the server holds: the commands change it and the reads that follow them (the cache refresh) answer it, as the real one does. */
let server = { dispatch: RUNNING as { paused: boolean; changed_at: string }, vectors: control() };

function seeded(roles: string[], dispatch = RUNNING, vectors: VectorControl | null = control()): QueryClient {
  server = { dispatch, vectors: vectors ?? control() };
  const client = newClient();
  client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', login: 'a@example.test', roles } as never);
  client.setQueryData(queryKeys.execution.dispatch(), dispatch);
  if (vectors !== null) client.setQueryData(vectorControlKey(), vectors);
  return client;
}

async function strip(client: QueryClient): Promise<LiveRender> {
  live = await mountLive(createElement(QueryClientProvider, { client }, createElement(PauseStatusLive)));
  return live;
}

/** The buttons of the strip that are not menu items: the controls a person sees before anything is opened. */
const controls = (markup: string): number =>
  [...markup.matchAll(/<button\b[^>]*>/g)].filter((tag) => !tag[0].includes('role="menuitem"')).length;
const items = (markup: string): number => [...markup.matchAll(/role="menuitem"/g)].length;

beforeEach(() => {
  vi.resetAllMocks();
  server = { dispatch: RUNNING, vectors: control() };
  vi.mocked(getExecutionDispatch).mockImplementation(async () => ({ data: server.dispatch }) as never);
  vi.mocked(getVectorControl).mockImplementation(async () => ({ data: server.vectors }) as never);
  vi.mocked(setExecutionPaused).mockImplementation(async ({ body }) => {
    server.dispatch = { paused: body.paused, changed_at: '2026-11-11T09:00:00Z' };
    return { data: server.dispatch } as never;
  });
  vi.mocked(setVectorPaused).mockImplementation(async ({ body }) => {
    server.vectors = control({ paused: body.paused, ...(body.paused ? { paused_since: '2026-11-11T09:00:00Z' } : {}) });
    return { data: server.vectors } as never;
  });
});

afterEach(async () => {
  await live?.unmount();
  live = null;
});

describe('one button, not two', () => {
  it('an administrator sees exactly one control, «Пауза», and the menu behind it holds the two items', async () => {
    const markup = (await strip(seeded(['admin']))).markup();
    expect(controls(markup)).toBe(1);
    expect(markup.match(/aria-haspopup="menu"/g)).toHaveLength(1);
    expect(markup).toContain('aria-expanded="false"');
    expect(items(markup)).toBe(2);
    expect(markup).toContain(QUEUE_ITEM);
    expect(markup).toContain(VECTORS_ITEM);
  });

  it('with the queue and the vectors both paused it is still one control, with the way back in each item', async () => {
    const markup = (await strip(seeded(['admin'], STOPPED, control({ paused: true })))).markup();
    expect(controls(markup)).toBe(1);
    expect(markup).toContain(QUEUE_ITEM_RESUME);
    expect(markup).toContain(VECTORS_ITEM_RESUME);
    // The old pair of buttons, one per state, is gone.
    expect(markup).not.toContain('>Возобновить</button>');
    expect(markup).not.toContain('>Приостановить</button>');
  });

  it('opening the button shows the menu; choosing an item closes it again', async () => {
    const strip_ = await strip(seeded(['admin']));
    await strip_.press(TRIGGER);
    expect(strip_.markup()).toContain('aria-expanded="true"');
    await strip_.press(VECTORS_ITEM);
    expect(strip_.markup()).toContain('aria-expanded="false"');
  });
});

describe('the badge «Векторы на паузе» exists only during a pause', () => {
  it('shows no badge while the vectors run, to an administrator or an expert, nor while their state is unknown', async () => {
    for (const roles of [['admin'], ['expert']]) {
      const markup = (await strip(seeded(roles, RUNNING, control()))).markup();
      expect(markup).not.toContain(BADGE);
      expect(markup).not.toContain('data-pause-vectors');
      await live?.unmount();
      live = null;
    }
    const unread = (await strip(seeded(['admin'], RUNNING, null))).markup();
    expect(unread).not.toContain(BADGE);
  });

  it('shows it while they are paused, to an expert too, who has no button', async () => {
    const markup = (await strip(seeded(['expert'], RUNNING, control({ paused: true, paused_since: '2026-11-11T09:00:00Z' })))).markup();
    expect(markup).toContain(BADGE);
    expect(markup).toContain('data-pause-vectors="paused"');
    expect(controls(markup)).toBe(0);
  });

  it('says in its tooltip what the pause means for the reader, and since when only when the time is known', () => {
    const view = (since: string | undefined) => renderToStaticMarkup(createElement(PauseStatusView, {
      status: RUNNING, failed: false, mayToggle: false, asking: false, busy: false, error: null,
      onAsk: () => {}, onConfirm: () => {}, onCancel: () => {}, vectors: { kind: 'read', paused: true, since },
    } satisfies PauseStatusViewProps));
    expect(view('2026-11-11T09:00:00Z')).toMatch(/title="Векторы на паузе с \d{2}:\d{2}; прецеденты новых находок появятся после возобновления"/);
    expect(view(undefined)).toContain('title="Векторы на паузе; прецеденты новых находок появятся после возобновления"');
  });

  it('does not touch the queue badge: that one still links to «Очередь» and is its own', async () => {
    const markup = (await strip(seeded(['admin'], STOPPED, control()))).markup();
    expect(markup).toContain(PAUSED_LABEL);
    expect(markup).not.toContain(BADGE);
  });
});

describe('who sees the button', () => {
  it('an expert reads the state and has no button; a viewer has no button and no vectors badge, whatever the cache holds', async () => {
    const expert = (await strip(seeded(['expert'], STOPPED, control({ paused: true })))).markup();
    expect(controls(expert)).toBe(0);
    expect(expert).toContain(PAUSED_LABEL);
    expect(expert).toContain(BADGE);
    await live?.unmount();
    live = null;
    const viewer = (await strip(seeded(['viewer'], STOPPED, control({ paused: true })))).markup();
    expect(controls(viewer)).toBe(0);
    expect(viewer).not.toContain(BADGE);
  });

  it('a viewer does not read the vectors: the read waits for a role it is open to', async () => {
    await strip(seeded(['viewer']));
    expect(getVectorControl).not.toHaveBeenCalled();
    await live?.unmount();
    live = null;
    // Negative control: the same mount for an administrator is allowed to ask (the seed is fresh, so it may not need to).
    const admin = seeded(['admin'], RUNNING, null);
    await strip(admin);
    expect(getVectorControl).toHaveBeenCalled();
  });

  it('the frame does not mount the strip for a viewer or a guest', () => {
    const subject = (roles: string[]) => ({ roles, isDefaultCredential: false, profileComplete: true });
    expect(offersPauseStatus(subject(['viewer']))).toBe(false);
    expect(offersPauseStatus(null)).toBe(false);
    expect(offersPauseStatus(subject(['admin']))).toBe(true);
    expect(offersPauseStatus(subject(['expert']))).toBe(true);
  });
});

describe('each item calls its own operation', () => {
  it('«Выдача анализа» asks first, then the confirmation pauses the queue; the vectors are not touched', async () => {
    const strip_ = await strip(seeded(['admin']));
    await strip_.press(TRIGGER);
    await strip_.press(QUEUE_ITEM);
    expect(strip_.markup()).toContain('Приостановить выдачу задач?');
    expect(setExecutionPaused).not.toHaveBeenCalled();
    await strip_.press('Приостановить');
    expect(setExecutionPaused).toHaveBeenCalledTimes(1);
    expect(setExecutionPaused).toHaveBeenCalledWith({ body: { paused: true }, idempotencyKey: expect.stringMatching(/\S+/) });
    expect(setVectorPaused).not.toHaveBeenCalled();
  });

  it('«Выдача анализа» can be abandoned: «Отмена» sends nothing', async () => {
    const strip_ = await strip(seeded(['admin']));
    await strip_.press(QUEUE_ITEM);
    await strip_.press('Отмена');
    expect(setExecutionPaused).not.toHaveBeenCalled();
    expect(setVectorPaused).not.toHaveBeenCalled();
    expect(strip_.markup()).toContain('aria-haspopup="menu"');
    expect(strip_.markup()).not.toContain('выдачу задач?');
  });

  it('«Векторы» pauses them at once, with no question; the queue is not touched; the badge appears from the answer', async () => {
    const strip_ = await strip(seeded(['admin']));
    await strip_.press(TRIGGER);
    await strip_.press(VECTORS_ITEM);
    expect(setVectorPaused).toHaveBeenCalledTimes(1);
    expect(setVectorPaused).toHaveBeenCalledWith({ body: { paused: true }, idempotencyKey: expect.stringMatching(/\S+/) });
    expect(setExecutionPaused).not.toHaveBeenCalled();
    expect(strip_.markup()).not.toContain('выдачу задач?');
    expect(strip_.markup()).toContain(BADGE);
    expect(strip_.markup()).toContain(VECTORS_ITEM_RESUME);
  });

  it('«Векторы» on paused vectors resumes them, and the badge goes with the pause', async () => {
    const strip_ = await strip(seeded(['admin'], RUNNING, control({ paused: true, paused_since: '2026-11-11T09:00:00Z' })));
    expect(strip_.markup()).toContain(BADGE);
    await strip_.press(VECTORS_ITEM_RESUME);
    expect(setVectorPaused).toHaveBeenCalledWith({ body: { paused: false }, idempotencyKey: expect.stringMatching(/\S+/) });
    expect(strip_.markup()).not.toContain(BADGE);
    expect(strip_.markup()).toContain(VECTORS_ITEM);
  });

  it('a refused command shows the refusal and keeps its key for the retry; a new intent gets a new key', async () => {
    const refusal = new ApiError(403, {
      contract_version: '1.51.0', error_code: 'permission_denied', message: 'no', correlation_id: 'vector-refused', retryable: false,
    }, 'vector-refused');
    vi.mocked(setVectorPaused).mockRejectedValueOnce(refusal);
    const strip_ = await strip(seeded(['admin']));
    await strip_.press(VECTORS_ITEM);
    expect(strip_.markup()).toContain('role="alert"');
    expect(strip_.markup()).not.toContain(BADGE);
    await strip_.press(VECTORS_ITEM);
    const [first, second] = vi.mocked(setVectorPaused).mock.calls.map(([input]) => input.idempotencyKey);
    expect(first).toBeDefined();
    expect(second).toBe(first);
    // It went through the second time: the next intent is the opposite one, so it is a new command with a new key.
    await strip_.press(VECTORS_ITEM_RESUME);
    const third = vi.mocked(setVectorPaused).mock.calls[2]?.[0].idempotencyKey;
    expect(third).toBeDefined();
    expect(third).not.toBe(first);
  });

  it('an unread state of the vectors offers no switch: nothing is sent from a state nobody read', async () => {
    vi.mocked(getVectorControl).mockRejectedValue(new ApiError(503, {
      contract_version: '1.51.0', error_code: 'dependency_unavailable', message: 'down', correlation_id: 'vector-down', retryable: true,
    }, 'vector-down'));
    const client = seeded(['admin'], RUNNING, null);
    const strip_ = await strip(client);
    // The read is in flight; let it settle into its failure.
    await strip_.settle(async () => { await client.refetchQueries({ queryKey: vectorControlKey() }); });
    const markup = strip_.markup();
    expect(markup).toContain('Векторы — состояние не прочитано');
    expect(markup).not.toContain(BADGE);
    await strip_.press('Векторы — состояние не прочитано');
    expect(setVectorPaused).not.toHaveBeenCalled();
  });
});

describe('the menu\'s two items, without a browser', () => {
  const choose = (item: ReturnType<typeof pauseMenuProps>['items'][number] | undefined): void => {
    if (item?.kind === 'action') item.onChoose?.();
  };
  const wired = (vectors: Parameters<typeof pauseMenuProps>[1]) => {
    const calls: string[] = [];
    const props = pauseMenuProps(RUNNING, vectors, () => calls.push('queue'), () => calls.push('vectors'));
    return { props, calls };
  };

  it('«Выдача анализа» is wired to the queue\'s question and «Векторы» to the vectors\' switch, each to its own', () => {
    const { props, calls } = wired({ kind: 'read', paused: false, since: undefined });
    expect(props.items.map((item) => item.label)).toEqual([dispatchItemLabel(false), vectorsItemLabel({ kind: 'read', paused: false, since: undefined })]);
    choose(props.items[0]);
    expect(calls).toEqual(['queue']);
    choose(props.items[1]);
    expect(calls).toEqual(['queue', 'vectors']);
  });

  it('an unread state of the vectors is an item with no action, and a state not yet read is no item', () => {
    const unread = wired({ kind: 'unread' });
    expect(unread.props.items).toHaveLength(2);
    choose(unread.props.items[1]);
    expect(unread.calls).toEqual([]);
    expect(wired(undefined).props.items).toHaveLength(1);
  });

  it('the strip reduces a read to paused, running or unread; a failed read never says «running»', () => {
    expect(vectorsPauseOf(undefined, false)).toBeUndefined();
    expect(vectorsPauseOf(undefined, true)).toEqual({ kind: 'unread' });
    expect(vectorsPauseOf(control({ paused: true, paused_since: '2026-11-11T09:00:00Z' }), false))
      .toEqual({ kind: 'read', paused: true, since: '2026-11-11T09:00:00Z' });
    // A later failed read keeps the last answer instead of inventing a state.
    expect(vectorsPauseOf(control({ paused: true }), true)).toMatchObject({ kind: 'read', paused: true });
  });

  it('the roles that read the pause are the roles the queue is open to', () => {
    expect([['admin'], ['expert'], ['admin', 'expert'], ['viewer'], []].map((roles) => canSeePause(roles as never)))
      .toEqual([true, true, true, false, false]);
  });
});
