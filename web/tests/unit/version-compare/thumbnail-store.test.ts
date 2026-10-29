/**
 * The thumbnails of the matrix (`CMP-VC-UI-01`): how many requests are open at once, that a page is asked for once however many
 * cells show it, that a thumbnail a cell holds is never evicted and a released one is revoked, and what a `404` and a retryable
 * refusal become. The store is plain TypeScript; the transport, the object URLs and the clock are injected.
 */

import { describe, expect, it } from 'vitest';

import { ThumbnailStore } from '@/entities/version-series';

interface Pending {
  readonly id: string;
  readonly resolve: (blob: Blob) => void;
  readonly reject: (error: unknown) => void;
  readonly signal: AbortSignal;
}

function harness(options: { maxInFlight?: number; maxCached?: number; classify?: (error: unknown) => 'retry' | 'absent' | 'failed' } = {}) {
  const pending: Pending[] = [];
  const revoked: string[] = [];
  const timers: (() => void)[] = [];
  let urls = 0;
  const store = new ThumbnailStore({
    fetchThumbnail: (id, signal) => new Promise<Blob>((resolve, reject) => pending.push({ id, resolve, reject, signal })),
    classify: options.classify ?? (() => 'failed'),
    createUrl: () => `blob:t${(urls += 1)}`,
    revokeUrl: (url) => revoked.push(url),
    maxInFlight: options.maxInFlight ?? 2,
    maxCached: options.maxCached ?? 2,
    retries: 1,
    setTimer: (callback) => {
      timers.push(callback);
      return timers.length;
    },
    clearTimer: () => undefined,
  });
  const settle = async (index = 0): Promise<void> => {
    (pending[index] as Pending).resolve(new Blob(['x']));
    await Promise.resolve();
    await Promise.resolve();
  };
  return { store, pending, revoked, timers, settle };
}

describe('the thumbnail store', () => {
  it('never has more requests open than it was told to', () => {
    const { store, pending } = harness({ maxInFlight: 2 });
    for (const id of ['a', 'b', 'c', 'd']) store.acquire(id);
    expect(pending.length).toBe(2);
    expect(store.openRequests).toBe(2);
  });

  it('asks for a page once however many cells show it', () => {
    const { store, pending } = harness();
    store.acquire('a');
    store.acquire('a');
    store.acquire('a');
    expect(pending.length).toBe(1);
  });

  it('starts the next waiting request as soon as one ends', async () => {
    const { store, pending, settle } = harness({ maxInFlight: 1 });
    store.acquire('a');
    store.acquire('b');
    expect(pending.map((call) => call.id)).toEqual(['a']);
    await settle(0);
    expect(pending.map((call) => call.id)).toEqual(['a', 'b']);
    expect(store.snapshot('a')).toEqual({ state: 'ready', url: 'blob:t1' });
  });

  it('keeps what a cell holds, evicts and revokes what was released, least recent first', async () => {
    const { store, revoked, settle } = harness({ maxInFlight: 4, maxCached: 1 });
    store.acquire('a');
    store.acquire('b');
    store.acquire('c');
    await settle(0);
    await settle(1);
    await settle(2);
    expect(revoked).toEqual([]);
    store.release('a');
    store.release('b');
    expect(revoked).toEqual(['blob:t1', 'blob:t2']);
    expect(store.snapshot('c').state).toBe('ready');
    expect(store.snapshot('a')).toEqual({ state: 'loading', url: null });
    expect(store.cachedCount).toBe(1);
  });

  it('stops a request nobody wants any more', () => {
    const { store, pending } = harness();
    store.acquire('a');
    store.release('a');
    expect(pending[0]?.signal.aborted).toBe(true);
    expect(store.snapshot('a')).toEqual({ state: 'loading', url: null });
  });

  it('reads a 404 as absent, an ordinary failure as failed, and tries a retryable one again a bounded number of times', async () => {
    const outcomes: Record<string, 'retry' | 'absent' | 'failed'> = { gone: 'absent', broken: 'failed', flaky: 'retry' };
    const { store, pending, timers } = harness({ maxInFlight: 3, classify: (error) => outcomes[String(error)] ?? 'failed' });
    for (const id of ['gone', 'broken', 'flaky']) store.acquire(id);
    pending[0]?.reject('gone');
    pending[1]?.reject('broken');
    pending[2]?.reject('flaky');
    await Promise.resolve();
    await Promise.resolve();
    expect(store.snapshot('gone')).toEqual({ state: 'absent', url: null });
    expect(store.snapshot('broken')).toEqual({ state: 'failed', url: null });
    expect(store.snapshot('flaky').state).toBe('loading');
    expect(timers.length).toBe(1);
    timers[0]?.();
    expect(pending.filter((call) => call.id === 'flaky').length).toBe(2);
    pending[3]?.reject('flaky');
    await Promise.resolve();
    await Promise.resolve();
    expect(store.snapshot('flaky').state).toBe('failed');
  });

  it('revokes every address when it is disposed', async () => {
    const { store, revoked, settle } = harness();
    store.acquire('a');
    await settle(0);
    store.dispose();
    expect(revoked).toEqual(['blob:t1']);
  });
});
