/**
 * The thumbnails of a matrix, fetched a few at a time and kept as object URLs (`CMP-VC-UI-01`).
 *
 * A matrix of twelve versions by a hundred sheets holds more than a thousand cells, and every thumbnail goes
 * through the generated client (the BFF turns the session into the API credential, so an `<img>` pointed at the
 * API would carry none). The store therefore never has more than `maxInFlight` requests open, asks for a page
 * once however many cells show it, keeps at most `maxCached` thumbnails that nothing shows (the least recently
 * released go first, their object URLs revoked), and never lets go of one a mounted cell still holds.
 * A thumbnail the server does not have (`404`) is *absent*, a fact about the page; any other failure that is not
 * retried is *failed*. Nothing is written to `localStorage`, `sessionStorage` or IndexedDB: page bytes are
 * fetched per view and not persisted (the seam's `P3-WEB-02`).
 *
 * Plain TypeScript with the transport, the object URLs and the clock injected, so each rule has a test.
 */

export type ThumbnailState = 'loading' | 'ready' | 'absent' | 'failed';

export interface ThumbnailSnapshot {
  readonly state: ThumbnailState;
  readonly url: string | null;
}

export type ThumbnailFailureKind = 'retry' | 'absent' | 'failed';

export interface ThumbnailStoreOptions {
  readonly fetchThumbnail: (profileId: string, signal: AbortSignal) => Promise<Blob>;
  readonly classify: (error: unknown) => ThumbnailFailureKind;
  readonly createUrl: (blob: Blob) => string;
  readonly revokeUrl: (url: string) => void;
  readonly maxInFlight?: number;
  readonly maxCached?: number;
  readonly retries?: number;
  readonly retryDelayMs?: number;
  readonly setTimer?: (callback: () => void, ms: number) => unknown;
  readonly clearTimer?: (handle: unknown) => void;
}

interface Entry {
  snapshot: ThumbnailSnapshot;
  holders: number;
  attempts: number;
  controller: AbortController | null;
  timer: unknown;
  lastUsed: number;
}

export const THUMBNAIL_MAX_IN_FLIGHT = 6;
export const THUMBNAIL_MAX_CACHED = 300;
export const THUMBNAIL_RETRIES = 2;
export const THUMBNAIL_RETRY_DELAY_MS = 800;

const LOADING: ThumbnailSnapshot = { state: 'loading', url: null };

export class ThumbnailStore {
  private readonly entries = new Map<string, Entry>();
  private readonly listeners = new Set<() => void>();
  private readonly queue: string[] = [];
  private inFlight = 0;
  private clock = 0;
  private disposed = false;
  private readonly maxInFlight: number;
  private readonly maxCached: number;
  private readonly retries: number;
  private readonly retryDelayMs: number;
  private readonly setTimer: (callback: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(private readonly options: ThumbnailStoreOptions) {
    this.maxInFlight = options.maxInFlight ?? THUMBNAIL_MAX_IN_FLIGHT;
    this.maxCached = options.maxCached ?? THUMBNAIL_MAX_CACHED;
    this.retries = options.retries ?? THUMBNAIL_RETRIES;
    this.retryDelayMs = options.retryDelayMs ?? THUMBNAIL_RETRY_DELAY_MS;
    this.setTimer = options.setTimer ?? ((callback, ms) => setTimeout(callback, ms));
    this.clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  /** The state of a thumbnail; the same object until it changes, so a store subscriber can compare. */
  snapshot = (profileId: string): ThumbnailSnapshot => this.entries.get(profileId)?.snapshot ?? LOADING;

  /** A cell shows this page: ask for it once, and hold it while the cell is on screen. */
  acquire(profileId: string): void {
    if (this.disposed) return;
    let entry = this.entries.get(profileId);
    if (entry === undefined) {
      entry = { snapshot: LOADING, holders: 0, attempts: 0, controller: null, timer: null, lastUsed: 0 };
      this.entries.set(profileId, entry);
      this.queue.push(profileId);
    }
    entry.holders += 1;
    entry.lastUsed = ++this.clock;
    this.pump();
  }

  /** The cell no longer shows it: it may now be evicted, and a request nobody wants is stopped. */
  release(profileId: string): void {
    const entry = this.entries.get(profileId);
    if (entry === undefined) return;
    entry.holders = Math.max(0, entry.holders - 1);
    entry.lastUsed = ++this.clock;
    if (entry.holders === 0 && entry.snapshot.state === 'loading') this.forget(profileId, entry);
    this.evict();
  }

  get openRequests(): number {
    return this.inFlight;
  }

  get cachedCount(): number {
    let count = 0;
    for (const entry of this.entries.values()) if (entry.snapshot.url !== null) count += 1;
    return count;
  }

  dispose(): void {
    this.disposed = true;
    for (const [id, entry] of [...this.entries]) {
      entry.controller?.abort();
      if (entry.timer !== null) this.clearTimer(entry.timer);
      if (entry.snapshot.url !== null) this.options.revokeUrl(entry.snapshot.url);
      this.entries.delete(id);
    }
    this.queue.length = 0;
    this.listeners.clear();
  }

  // -- the requests ---------------------------------------------------------------------------------

  private changed(): void {
    for (const listener of [...this.listeners]) listener();
  }

  private pump(): void {
    while (this.inFlight < this.maxInFlight) {
      const id = this.queue.shift();
      if (id === undefined) return;
      const entry = this.entries.get(id);
      if (entry === undefined || entry.snapshot.state !== 'loading' || entry.controller !== null || entry.timer !== null) continue;
      this.start(id, entry);
    }
  }

  private start(id: string, entry: Entry): void {
    const controller = new AbortController();
    entry.controller = controller;
    entry.attempts += 1;
    this.inFlight += 1;
    this.options.fetchThumbnail(id, controller.signal).then(
      (blob) => {
        this.finish(entry);
        if (this.disposed || this.entries.get(id) !== entry || controller.signal.aborted) return;
        entry.snapshot = { state: 'ready', url: this.options.createUrl(blob) };
        this.evict();
        this.changed();
        this.pump();
      },
      (error: unknown) => {
        this.finish(entry);
        if (this.disposed || this.entries.get(id) !== entry || controller.signal.aborted) return;
        const kind = this.options.classify(error);
        if (kind === 'retry' && entry.attempts <= this.retries) {
          entry.timer = this.setTimer(() => {
            entry.timer = null;
            this.queue.push(id);
            this.pump();
          }, this.retryDelayMs * 2 ** (entry.attempts - 1));
        } else {
          entry.snapshot = { state: kind === 'absent' ? 'absent' : 'failed', url: null };
          this.changed();
        }
        this.pump();
      },
    );
  }

  private finish(entry: Entry): void {
    entry.controller = null;
    this.inFlight -= 1;
  }

  private forget(id: string, entry: Entry): void {
    entry.controller?.abort();
    if (entry.timer !== null) this.clearTimer(entry.timer);
    this.entries.delete(id);
    const position = this.queue.indexOf(id);
    if (position >= 0) this.queue.splice(position, 1);
  }

  /** Keep at most `maxCached` finished thumbnails; the least recently released go first, never one a cell holds. */
  private evict(): void {
    const finished = [...this.entries].filter(([, entry]) => entry.snapshot.state !== 'loading');
    if (finished.length <= this.maxCached) return;
    finished.sort((a, b) => a[1].lastUsed - b[1].lastUsed);
    for (const [id, entry] of finished) {
      if (this.entries.size - this.countLoading() <= this.maxCached) break;
      if (entry.holders > 0) continue;
      if (entry.snapshot.url !== null) this.options.revokeUrl(entry.snapshot.url);
      this.entries.delete(id);
    }
  }

  private countLoading(): number {
    let count = 0;
    for (const entry of this.entries.values()) if (entry.snapshot.state === 'loading') count += 1;
    return count;
  }
}
