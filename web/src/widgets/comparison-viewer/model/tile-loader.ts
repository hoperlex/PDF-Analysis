/**
 * Fetches the tiles a window needs, a few at a time, and keeps a bounded number of them (`CMP-VIEWER-01`).
 *
 * A viewer asks for a dozen tiles when it opens and for a new set at every zoom or pan. The loader does what the
 * browser would not: it never has more than `maxInFlight` requests open (the server composes four at a time), it asks
 * for a tile once however many times the window wants it, it stops the requests the window no longer wants, it retries
 * the answers the server says to retry (`dependency_unavailable`, a network failure) a bounded number of times with a
 * growing wait, and it keeps at most `maxCached` tiles as object URLs, revoking the ones it lets go of. A tile the
 * server says does not exist (`404`) is *absent*, which is a fact about the sheet (the pyramid the viewer derived may be
 * larger than the server's at an edge) and not a failure; anything else that is not retried is *failed* and counted so
 * the viewer can say so.
 *
 * It is plain TypeScript with the transport, the clock and the object URLs injected, so every rule above has a test.
 */

import type { ComparisonLayer } from '@/shared/api';

export interface TileRequest {
  readonly mode: 'overlay' | 'a' | 'b';
  readonly level: number;
  readonly column: number;
  readonly row: number;
  /** The `layers` query value (comma-separated), for the overlay only. */
  readonly layers?: string;
  /** Whether page B carries its aligned blocks (`b` and the overlay). */
  readonly align?: boolean;
}

export type TileState = 'loading' | 'ready' | 'absent' | 'failed';
export type FailureKind = 'retry' | 'absent' | 'failed';

export interface TileLoaderOptions {
  readonly fetchTile: (request: TileRequest, signal: AbortSignal) => Promise<Blob>;
  readonly classify: (error: unknown) => FailureKind;
  readonly createUrl: (blob: Blob) => string;
  readonly revokeUrl: (url: string) => void;
  readonly onChange: () => void;
  readonly maxInFlight?: number;
  readonly maxCached?: number;
  readonly retries?: number;
  readonly retryDelayMs?: number;
  readonly setTimer?: (callback: () => void, ms: number) => unknown;
  readonly clearTimer?: (handle: unknown) => void;
}

interface Entry {
  state: TileState;
  url: string | null;
  attempts: number;
  controller: AbortController | null;
  timer: unknown;
  lastUsed: number;
  request: TileRequest;
}

export const DEFAULT_MAX_IN_FLIGHT = 6;
export const DEFAULT_MAX_CACHED = 160;
export const DEFAULT_RETRIES = 3;
export const DEFAULT_RETRY_DELAY_MS = 600;

export function tileKey(request: TileRequest): string {
  return [request.mode, request.level, request.column, request.row, request.layers ?? '', request.align ? 'aligned' : ''].join('/');
}

/** The layers of a request as the enum values, for a test or a label. */
export function layersOf(request: TileRequest): ComparisonLayer[] {
  return (request.layers ?? '').split(',').filter((name) => name !== '') as ComparisonLayer[];
}

export class TileLoader {
  private readonly entries = new Map<string, Entry>();
  private wanted: readonly string[] = [];
  private inFlight = 0;
  private clock = 0;
  private disposed = false;
  private readonly maxInFlight: number;
  private readonly maxCached: number;
  private readonly retries: number;
  private readonly retryDelayMs: number;
  private readonly setTimer: (callback: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(private readonly options: TileLoaderOptions) {
    this.maxInFlight = options.maxInFlight ?? DEFAULT_MAX_IN_FLIGHT;
    this.maxCached = options.maxCached ?? DEFAULT_MAX_CACHED;
    this.retries = options.retries ?? DEFAULT_RETRIES;
    this.retryDelayMs = options.retryDelayMs ?? DEFAULT_RETRY_DELAY_MS;
    this.setTimer = options.setTimer ?? ((callback, ms) => setTimeout(callback, ms));
    this.clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));
  }

  /** The window now wants exactly these tiles, most important first. */
  want(requests: readonly TileRequest[]): void {
    if (this.disposed) return;
    this.wanted = requests.map(tileKey);
    const wantedSet = new Set(this.wanted);
    for (const [key, entry] of this.entries) {
      if (!wantedSet.has(key) && entry.state === 'loading') this.drop(key, entry);
    }
    for (const request of requests) {
      const key = tileKey(request);
      const entry = this.entries.get(key);
      if (entry === undefined) {
        this.entries.set(key, {
          state: 'loading', url: null, attempts: 0, controller: null, timer: null, lastUsed: ++this.clock, request,
        });
      } else {
        entry.lastUsed = ++this.clock;
      }
    }
    this.evict();
    this.pump();
  }

  stateOf(request: TileRequest): TileState | null {
    return this.entries.get(tileKey(request))?.state ?? null;
  }

  urlOf(request: TileRequest): string | null {
    return this.entries.get(tileKey(request))?.url ?? null;
  }

  /** The tiles the window wants that ended failed. */
  failedCount(): number {
    let count = 0;
    for (const key of this.wanted) if (this.entries.get(key)?.state === 'failed') count += 1;
    return count;
  }

  /** The tiles the window wants that have not arrived yet. */
  pendingCount(): number {
    let count = 0;
    for (const key of this.wanted) if (this.entries.get(key)?.state === 'loading') count += 1;
    return count;
  }

  /** Ask again for the wanted tiles that ended failed (a reader's «Повторить»). */
  retryFailed(): void {
    for (const key of this.wanted) {
      const entry = this.entries.get(key);
      if (entry !== undefined && entry.state === 'failed') {
        entry.state = 'loading';
        entry.attempts = 0;
      }
    }
    this.options.onChange();
    this.pump();
  }

  get openRequests(): number {
    return this.inFlight;
  }

  get cachedCount(): number {
    let count = 0;
    for (const entry of this.entries.values()) if (entry.url !== null) count += 1;
    return count;
  }

  dispose(): void {
    this.disposed = true;
    for (const [key, entry] of [...this.entries]) {
      this.drop(key, entry);
      if (entry.url !== null) this.options.revokeUrl(entry.url);
    }
    this.entries.clear();
  }

  // -- the requests ---------------------------------------------------------------------------------------

  private pump(): void {
    for (const key of this.wanted) {
      if (this.inFlight >= this.maxInFlight) return;
      const entry = this.entries.get(key);
      if (entry === undefined || entry.state !== 'loading' || entry.controller !== null || entry.timer !== null) continue;
      this.start(key, entry);
    }
  }

  private start(key: string, entry: Entry): void {
    const controller = new AbortController();
    entry.controller = controller;
    entry.attempts += 1;
    this.inFlight += 1;
    this.options.fetchTile(entry.request, controller.signal).then(
      (blob) => {
        this.finish(entry);
        if (this.disposed || this.entries.get(key) !== entry || controller.signal.aborted) return;
        entry.url = this.options.createUrl(blob);
        entry.state = 'ready';
        this.evict();
        this.options.onChange();
        this.pump();
      },
      (error: unknown) => {
        this.finish(entry);
        if (this.disposed || this.entries.get(key) !== entry || controller.signal.aborted) return;
        const kind = this.options.classify(error);
        if (kind === 'retry' && entry.attempts <= this.retries) {
          entry.timer = this.setTimer(() => {
            entry.timer = null;
            this.pump();
          }, this.retryDelayMs * 2 ** (entry.attempts - 1));
        } else {
          entry.state = kind === 'absent' ? 'absent' : 'failed';
          this.options.onChange();
        }
        this.pump();
      },
    );
  }

  private finish(entry: Entry): void {
    entry.controller = null;
    this.inFlight -= 1;
  }

  /** Stop what the window no longer wants and forget it. */
  private drop(key: string, entry: Entry): void {
    entry.controller?.abort();
    if (entry.timer !== null) this.clearTimer(entry.timer);
    entry.timer = null;
    if (entry.url === null) this.entries.delete(key);
  }

  /** Keep at most `maxCached` tiles; the least recently wanted go first, and never one the window wants now. */
  private evict(): void {
    const wantedSet = new Set(this.wanted);
    const held = [...this.entries].filter(([, entry]) => entry.url !== null || entry.state !== 'loading');
    if (held.length <= this.maxCached) return;
    held.sort((a, b) => a[1].lastUsed - b[1].lastUsed);
    for (const [key, entry] of held) {
      if (this.entries.size <= this.maxCached) break;
      if (wantedSet.has(key)) continue;
      if (entry.url !== null) this.options.revokeUrl(entry.url);
      this.entries.delete(key);
    }
  }
}
