/**
 * The tile loader's rules (`CMP-VIEWER-01`): a bounded number of requests, one request per tile, the unwanted stopped,
 * the retryable retried a bounded number of times, the absent told from the failed, the cache bounded and revoked.
 */

import { describe, expect, it, vi } from 'vitest';

import { ApiError, TransportError } from '@/shared/api';
import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { classifyTileFailure } from '@/widgets/comparison-viewer/model/use-tile-images';
import { type FailureKind, type TileRequest, TileLoader, tileKey } from '@/widgets/comparison-viewer/model/tile-loader';

interface Pending {
  readonly request: TileRequest;
  readonly signal: AbortSignal;
  resolve(blob?: Blob): void;
  reject(error: unknown): void;
}

function harness(options: { classify?: (error: unknown) => FailureKind; maxInFlight?: number; maxCached?: number; retries?: number } = {}) {
  const pending: Pending[] = [];
  const started: TileRequest[] = [];
  const revoked: string[] = [];
  const timers: { callback: () => void; ms: number }[] = [];
  let urls = 0;
  let changes = 0;
  const loader = new TileLoader({
    fetchTile: (request, signal) =>
      new Promise<Blob>((resolve, reject) => {
        started.push(request);
        pending.push({ request, signal, resolve: (blob = new Blob(['png'])) => resolve(blob), reject });
        signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
      }),
    classify: options.classify ?? (() => 'failed'),
    createUrl: () => `blob:tile-${(urls += 1)}`,
    revokeUrl: (url) => revoked.push(url),
    onChange: () => { changes += 1; },
    setTimer: (callback, ms) => { timers.push({ callback, ms }); return timers.length - 1; },
    clearTimer: () => {},
    ...(options.maxInFlight === undefined ? {} : { maxInFlight: options.maxInFlight }),
    ...(options.maxCached === undefined ? {} : { maxCached: options.maxCached }),
    ...(options.retries === undefined ? {} : { retries: options.retries }),
  });
  return { loader, pending, started, revoked, timers, changes: () => changes };
}

const tile = (column: number, row = 0, extra: Partial<TileRequest> = {}): TileRequest => ({ mode: 'overlay', level: 0, column, row, layers: 'main', ...extra });
const settle = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

describe('the tile loader', () => {
  it('never has more requests open than it was told', async () => {
    const h = harness({ maxInFlight: 3 });
    h.loader.want([0, 1, 2, 3, 4, 5].map((c) => tile(c)));
    expect(h.started).toHaveLength(3);
    expect(h.loader.openRequests).toBe(3);
    h.pending[0]!.resolve();
    await settle();
    expect(h.started).toHaveLength(4);
    expect(h.loader.openRequests).toBe(3);
  });

  it('asks for a tile once however often the window wants it, and gives its address when it arrives', async () => {
    const h = harness();
    h.loader.want([tile(0), tile(1)]);
    h.loader.want([tile(0), tile(1)]);
    h.loader.want([tile(1), tile(0)]);
    expect(h.started).toHaveLength(2);
    expect(h.loader.urlOf(tile(0))).toBeNull();
    expect(h.loader.stateOf(tile(0))).toBe('loading');
    h.pending[0]!.resolve();
    await settle();
    expect(h.loader.urlOf(tile(0))).toBe('blob:tile-1');
    expect(h.loader.stateOf(tile(0))).toBe('ready');
    h.loader.want([tile(0)]);
    expect(h.started).toHaveLength(2);
  });

  it('keeps tiles of different layers, alignment and mode apart', () => {
    const keys = new Set([tile(0), tile(0, 0, { layers: 'main,noise' }), tile(0, 0, { align: true }), { ...tile(0), mode: 'a' as const }].map(tileKey));
    expect(keys.size).toBe(4);
  });

  it('stops a request the window no longer wants', async () => {
    const h = harness();
    h.loader.want([tile(0), tile(1)]);
    h.loader.want([tile(1)]);
    expect(h.pending[0]!.signal.aborted).toBe(true);
    expect(h.pending[1]!.signal.aborted).toBe(false);
    await settle();
    expect(h.loader.openRequests).toBe(1);
    expect(h.loader.stateOf(tile(0))).toBeNull();
  });

  it('tells a tile the server does not have from a failure, and counts the failures', async () => {
    const h = harness({ classify: (error) => (error === 'gone' ? 'absent' : 'failed') });
    h.loader.want([tile(0), tile(1)]);
    h.pending[0]!.reject('gone');
    h.pending[1]!.reject('broken');
    await settle();
    expect(h.loader.stateOf(tile(0))).toBe('absent');
    expect(h.loader.stateOf(tile(1))).toBe('failed');
    expect(h.loader.failedCount()).toBe(1);
    expect(h.loader.pendingCount()).toBe(0);
    h.loader.retryFailed();
    expect(h.loader.stateOf(tile(1))).toBe('loading');
    expect(h.started).toHaveLength(3);
  });

  it('retries what the server says to retry, with a growing wait, a bounded number of times', async () => {
    const h = harness({ classify: () => 'retry', retries: 2 });
    h.loader.want([tile(0)]);
    h.pending[0]!.reject('busy');
    await settle();
    expect(h.timers.map((t) => t.ms)).toEqual([600]);
    expect(h.started).toHaveLength(1);
    h.timers[0]!.callback();
    expect(h.started).toHaveLength(2);
    h.pending[1]!.reject('busy');
    await settle();
    expect(h.timers.map((t) => t.ms)).toEqual([600, 1200]);
    h.timers[1]!.callback();
    h.pending[2]!.reject('busy');
    await settle();
    expect(h.timers).toHaveLength(2);
    expect(h.loader.stateOf(tile(0))).toBe('failed');
    expect(h.started).toHaveLength(3);
  });

  it('keeps at most the tiles it was told to and revokes the address of each one it lets go', async () => {
    const h = harness({ maxCached: 2 });
    h.loader.want([tile(0)]);
    h.pending[0]!.resolve();
    await settle();
    h.loader.want([tile(1)]);
    h.pending[1]!.resolve();
    await settle();
    h.loader.want([tile(2)]);
    h.pending[2]!.resolve();
    await settle();
    expect(h.loader.cachedCount).toBeLessThanOrEqual(2);
    expect(h.revoked).toEqual(['blob:tile-1']); // the oldest, which the window no longer wants
    expect(h.loader.urlOf(tile(2))).toBe('blob:tile-3');
  });

  it('never lets go of a tile the window wants now', async () => {
    const h = harness({ maxCached: 1 });
    h.loader.want([tile(0), tile(1)]);
    h.pending[0]!.resolve();
    h.pending[1]!.resolve();
    await settle();
    h.loader.want([tile(0), tile(1)]);
    expect(h.loader.urlOf(tile(0))).not.toBeNull();
    expect(h.loader.urlOf(tile(1))).not.toBeNull();
  });

  it('stops everything and revokes everything when the viewer closes', async () => {
    const h = harness();
    h.loader.want([tile(0), tile(1)]);
    h.pending[0]!.resolve();
    await settle();
    h.loader.dispose();
    expect(h.pending[1]!.signal.aborted).toBe(true);
    expect(h.revoked).toEqual(['blob:tile-1']);
    h.loader.want([tile(5)]);
    expect(h.started).toHaveLength(2);
    h.pending[1]!.resolve();
    await settle();
    expect(h.revoked).toEqual(['blob:tile-1']);
  });

  it('answers the window each time a tile arrives', async () => {
    const h = harness();
    h.loader.want([tile(0)]);
    const before = h.changes();
    h.pending[0]!.resolve();
    await settle();
    expect(h.changes()).toBe(before + 1);
  });
});

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = { contract_version: '1.14.0', error_code: code, message: 'Одна фраза.', correlation_id: 'c-1', retryable };
  return new ApiError(status, envelope, 'c-1');
}

describe('how a failed tile is read', () => {
  it('is absent for 404, retried for what the catalogue marks retryable, a failure otherwise', () => {
    expect(classifyTileFailure(apiError(404, 'not_found', false))).toBe('absent');
    expect(classifyTileFailure(apiError(503, 'dependency_unavailable', true))).toBe('retry');
    expect(classifyTileFailure(apiError(422, 'storage_integrity_error', false))).toBe('failed');
    expect(classifyTileFailure(apiError(500, 'internal_error', false))).toBe('failed');
    expect(classifyTileFailure(new TransportError('network', { retryable: true }))).toBe('retry');
    expect(classifyTileFailure(new TransportError('bad body'))).toBe('failed');
    expect(classifyTileFailure(new Error('anything else'))).toBe('failed');
  });
});

// vi is imported for parity with the other suites' fake-timer cases; the loader takes its clock as an argument.
void vi;
