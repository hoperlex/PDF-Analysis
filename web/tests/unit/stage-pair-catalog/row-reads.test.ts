/**
 * The pairs catalog reads and polls only the rows in view (`UI-B-85`, the N+1 of lane D6).
 *
 * Every row of the catalog said what its pair's latest run is through `useLatestPairRun`, and each row's read is a walk of the pair's
 * run list. The catalog lists up to a hundred pairs, so opening step 1 fired a hundred walks, and once a batch ran every row with an
 * active run polled at the 1.5 s review cadence. These cases mount the real catalog over a hundred pairs and count the reads the
 * rows make, with the browser's `IntersectionObserver` scripted: the catalog must make none before a row is in view, one per row in
 * view, and none again for a row that scrolls out and in unchanged by a poll at the review cadence.
 *
 * The counts are literals. The last block is the instrument's own proof: the shape the hook had before the fix (every row read, at
 * the review cadence) is run through the same counter and must show the defect, so a green result above cannot be a counter that
 * sees nothing.
 */

import { QueryClientProvider, QueryObserver, environmentManager } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

// React Query decides once, when it is loaded, whether it runs on a server (no `window`) and, if so, never schedules a refetch
// interval. The polling cases below need the intervals, so a `window` exists before the library is imported; it has no document,
// so nothing that looks for a DOM finds one, and `mountLive` puts back what it finds.
// The whole battery runs in one fork (`vitest.config.ts`: `singleFork`), so `globalThis` is shared between test files: what
// this file puts there it takes back after its last test (`afterAll` below), and what an earlier file left there (a `document`
// whose `visibilityState` would make React Query treat the tab as hidden) is set aside for the duration of this file.
const leftBefore = vi.hoisted(() => {
  const holder = globalThis as { window?: unknown; document?: unknown };
  const before = { window: holder.window, document: holder.document, hadWindow: 'window' in holder, hadDocument: 'document' in holder };
  holder.window = { addEventListener: () => undefined, removeEventListener: () => undefined };
  delete holder.document;
  return before;
});

// React Query's own server check is a constant of the module, decided when the process first loaded it, and the battery's
// fork loads it long before this file: the `window` above cannot change that answer. The library's switch for it
// (`environmentManager.setIsServer`) can: this file runs as a browser would and puts back the answer it found.
let serverBefore = false;
beforeAll(() => {
  serverBefore = environmentManager.isServer();
  environmentManager.setIsServer(() => false);
});

afterAll(() => {
  environmentManager.setIsServer(() => serverBefore);
  const holder = globalThis as { window?: unknown; document?: unknown };
  if (leftBefore.hadWindow) holder.window = leftBefore.window;
  else delete holder.window;
  if (leftBefore.hadDocument) holder.document = leftBefore.document;
  else delete holder.document;
});

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  listStageChainRuns: vi.fn(),
  listStageChangeCards: vi.fn(),
}));

import type { StageChainRun, StagePair } from '@/shared/api';
import { listStageChainRuns, listStageChangeCards } from '@/shared/api';
import { OPERATIONAL_LIST_POLLING, STAGE_REVIEW_POLL_MS } from '@/shared/config';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { StagePairCatalog } from '@/widgets/stage-pair-catalog';
import { pairRunsQueryOptions } from '@/widgets/stage-run-controls/api/use-pair-run';
import { readRuns } from '@/widgets/stage-run-controls/api/reads';
import { runActive, STAGE_RUN_KEYS } from '@/widgets/stage-run-controls/model/runs';
import { createViewportWatcher, withRowVisibility } from '@/widgets/stage-pair-catalog/model/rows-in-view';
import type { ViewportEntry } from '@/widgets/stage-pair-catalog/model/rows-in-view';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { run } from '../stage-changes/fixtures';
import { NOW, PROJECT_UID, uid } from '../version-compare/fixtures';

const PAIR_COUNT = 100;
const ANCHOR = 'data-pair-row-anchor';

const pairId = (index: number): string => uid('stp', index);

function pair(index: number): StagePair {
  return {
    pair_id: pairId(index), project_uid: PROJECT_UID, state: 'confirmed', completeness: 'full', created_at: NOW,
    left_document_uid: uid('doc', index), right_document_uid: uid('doc', 100 + index),
  };
}

/** The scripted `IntersectionObserver`: it keeps what is watched, and says which of it is in view when a test asks. */
class ScriptedObserver {
  static made: ScriptedObserver[] = [];
  readonly targets = new Set<Element>();
  constructor(private readonly callback: (entries: ViewportEntry[]) => void) {
    ScriptedObserver.made.push(this);
  }
  observe(target: Element): void { this.targets.add(target); }
  unobserve(target: Element): void { this.targets.delete(target); }
  disconnect(): void { this.targets.clear(); }
  takeRecords(): [] { return []; }
  /** Report every watched row: in view when its pair is in `visible`. */
  report(visible: ReadonlySet<string>): void {
    this.callback([...this.targets].map((target) => ({
      target, isIntersecting: visible.has(target.getAttribute(ANCHOR) ?? ''),
    })));
  }
}

const indexes = (from: number, to: number): string[] => Array.from({ length: to - from }, (_, offset) => pairId(from + offset));

/** The runs each pair answers: an even pair has a run in `state`, an odd pair has never run. */
function answerRuns(state: StageChainRun['state']): void {
  vi.mocked(listStageChainRuns).mockImplementation((async (options: { path: { stage_pair_id: string } }) => {
    const id = options.path.stage_pair_id;
    const number = Number(id.slice(-2));
    return { data: { items: number % 2 === 0 ? [run({ run_id: uid('crn', number), pair_id: id, state })] : [], page: { next_cursor: null } } };
  }) as never);
}

function readPairs(): string[] {
  return vi.mocked(listStageChainRuns).mock.calls.map(([options]) => (options as { path: { stage_pair_id: string } }).path.stage_pair_id);
}

async function mountCatalog(): Promise<LiveRender> {
  const client = newClient();
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID, undefined), {
    items: Array.from({ length: PAIR_COUNT }, (_, index) => pair(index)), page: { next_cursor: null },
  });
  client.setQueryData(STAGE_PAIR_KEYS.suggestions(PROJECT_UID, undefined), { items: [], page: { next_cursor: null } });
  client.setQueryData(STAGE_PAIR_KEYS.documents(PROJECT_UID), new Map());
  return mountLive(createElement(QueryClientProvider, { client }, createElement(StagePairCatalog, { projectUid: PROJECT_UID, mayAct: true })));
}

/** The one observer the catalog's watcher made (it makes it once, on the first row, and keeps it). */
function viewport(): ScriptedObserver {
  const [first] = ScriptedObserver.made;
  if (first === undefined) throw new Error('the catalog watched no row: the watcher made no observer');
  return first;
}

/**
 * The rows read, then the card counts of the finished runs are asked for: a few turns, each of which lets React and the cache hear
 * the last (the counts are enabled by the run list the first turn brings).
 */
async function settleReads(view: LiveRender): Promise<void> {
  for (let turn = 0; turn < 4; turn += 1) await view.settle(() => undefined);
}

/** The rows in view become `visible`, as the browser would report them while the reader scrolls. */
async function scrollTo(view: LiveRender, visible: ReadonlySet<string>): Promise<void> {
  await view.settle(() => viewport().report(visible));
  await settleReads(view);
}

let live: LiveRender | undefined;

beforeEach(() => {
  vi.mocked(listStageChainRuns).mockReset();
  vi.mocked(listStageChangeCards).mockReset();
  vi.mocked(listStageChangeCards).mockResolvedValue({ data: { counts: { total: 1, review: 0, project_changes: 1 } } } as never);
  vi.stubGlobal('IntersectionObserver', ScriptedObserver);
});

afterEach(async () => {
  vi.useRealTimers();
  await live?.unmount();
  live = undefined;
  vi.unstubAllGlobals();
});

describe('the catalog of a hundred pairs', () => {
  it('reads no pair\'s runs before a row is in view, and says nothing about a pair it has not read', async () => {
    answerRuns('completed');
    live = await mountCatalog();
    expect(readPairs()).toEqual([]);
    expect(vi.mocked(listStageChangeCards)).not.toHaveBeenCalled();
    // A row not read is loading, not «Не запускалось»: the catalog does not claim a pair never ran on no reading.
    expect(live.markup()).not.toContain('Не запускалось');
  });

  it('reads one run list per row in view, and the card counts of those rows only', async () => {
    answerRuns('completed');
    live = await mountCatalog();
    const first = new Set(indexes(0, 10));
    await scrollTo(live, first);
    expect(readPairs().sort()).toEqual(indexes(0, 10).sort());
    // Ten rows in view, five of them (the even pairs) with a finished run: five card-count reads, none for the rest of the hundred.
    expect(vi.mocked(listStageChangeCards)).toHaveBeenCalledTimes(5);
    // Of those ten rows, the five odd ones have never run and say so; the ninety unread rows say nothing.
    expect(live.markup().split('Не запускалось').length - 1).toBe(5);
    expect(live.markup().split('Завершено').length - 1).toBe(5);
  });

  it('reads the rows that scroll in, and not again the rows that scroll out', async () => {
    answerRuns('completed');
    live = await mountCatalog();
    await scrollTo(live, new Set(indexes(0, 10)));
    await scrollTo(live, new Set(indexes(10, 20)));
    // Twenty rows were in view over the scroll, each read once: the first ten were not read again on their way out.
    expect(readPairs().sort()).toEqual(indexes(0, 20).sort());
  });

  it('polls the rows in view while their run moves, every ten seconds, and polls no row out of view', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    answerRuns('running');
    live = await mountCatalog();
    const mounted = live;
    await scrollTo(mounted, new Set(indexes(0, 10)));
    // Ten rows read once; five of them (even pairs) have a running run and so poll.
    expect(readPairs()).toHaveLength(10);
    for (let elapsed = 0; elapsed < 30_000; elapsed += 500) {
      await mounted.settle(() => vi.advanceTimersByTime(500));
    }
    // 30 s at the operational 10 s cadence: three more reads for each of the five moving rows. At the 1.5 s review cadence it
    // would be twenty each (100), and a hundred rows polling would be two thousand.
    expect(OPERATIONAL_LIST_POLLING.intervalMs).toBe(10_000);
    expect(readPairs()).toHaveLength(10 + 5 * 3);
    expect(new Set(readPairs()).size).toBe(10);
    // The five rows scroll out: their polling stops, and nothing is read for the rest.
    await scrollTo(mounted, new Set());
    const before = readPairs().length;
    for (let elapsed = 0; elapsed < 30_000; elapsed += 500) {
      await mounted.settle(() => vi.advanceTimersByTime(500));
    }
    expect(readPairs()).toHaveLength(before);
  });
});

describe('the watcher of the rows in view', () => {
  function scripted() {
    const target = (name: string) => ({ name }) as unknown as Element;
    let send: (entries: readonly ViewportEntry[]) => void = () => undefined;
    const observed = new Set<Element>();
    const watch = createViewportWatcher((onEntries) => {
      send = onEntries;
      return { observe: (element) => { observed.add(element); }, unobserve: (element) => { observed.delete(element); } };
    });
    return { target, watch, observed, send: (entries: readonly ViewportEntry[]) => send(entries) };
  }

  it('reports each change of one row, stops reporting it when it is unwatched, and ignores a row it does not watch', () => {
    const world = scripted();
    const one = world.target('one');
    const stranger = world.target('stranger');
    const seen: boolean[] = [];
    const stop = world.watch(one, (visible) => seen.push(visible));
    world.send([{ target: one, isIntersecting: true }, { target: stranger, isIntersecting: true }]);
    world.send([{ target: one, isIntersecting: false }]);
    expect(seen).toEqual([true, false]);
    stop();
    expect(world.observed.has(one)).toBe(false);
    world.send([{ target: one, isIntersecting: true }]);
    expect(seen).toEqual([true, false]);
  });

  it('with no observer in the client reports every row in view at once, as the catalog read every row before', () => {
    const watch = createViewportWatcher(() => null);
    const seen: boolean[] = [];
    const stop = watch({} as Element, (visible) => seen.push(visible));
    expect(seen).toEqual([true]);
    expect(stop()).toBeUndefined();
  });

  it('keeps the same set when a report changes nothing, so a repeat renders nothing', () => {
    const none: ReadonlySet<string> = new Set();
    const one = withRowVisibility(none, 'a', true);
    expect([...one]).toEqual(['a']);
    expect(withRowVisibility(one, 'a', true)).toBe(one);
    expect(withRowVisibility(none, 'a', false)).toBe(none);
    expect([...withRowVisibility(one, 'a', false)]).toEqual([]);
  });
});

describe('the counter sees the defect it guards', () => {
  /** The hook as it was before the fix: every row read, and polled at the review cadence while a run moves. */
  const legacy = (id: string) => ({
    queryKey: STAGE_RUN_KEYS.list(id),
    queryFn: () => readRuns(id),
    retry: false as const,
    refetchInterval: (query: { state: { data: StageChainRun[] | undefined } }) =>
      (query.state.data?.some(runActive) ? STAGE_REVIEW_POLL_MS : false) as number | false,
  });

  /** Lets the settled reads reach the observers: a real turn of the event loop (only the intervals are faked). */
  const flush = (): Promise<void> => new Promise((done) => setTimeout(done, 0));

  async function poll(optionsFor: (id: string) => object, ids: readonly string[]): Promise<{ opening: number; thirtySeconds: number }> {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    answerRuns('running');
    const client = newClient();
    const stops = ids.map((id) => new QueryObserver(client, optionsFor(id) as never).subscribe(() => undefined));
    await flush();
    const opening = readPairs().length;
    for (let elapsed = 0; elapsed < 30_000; elapsed += 500) {
      vi.advanceTimersByTime(500);
      await flush();
    }
    const thirtySeconds = readPairs().length - opening;
    for (const stop of stops) stop();
    client.clear();
    return { opening, thirtySeconds };
  }

  it('shows the hundred reads on open and the 1.5 s polling of the old shape, and none of either for the new one out of view', async () => {
    const all = Array.from({ length: PAIR_COUNT }, (_, index) => pairId(index));
    const before = await poll(legacy, all);
    // All hundred pairs read on open; the fifty with a moving run each read twenty more times in 30 s: a thousand.
    expect(before).toEqual({ opening: 100, thirtySeconds: 50 * 20 });
    vi.mocked(listStageChainRuns).mockReset();
    const after = await poll((id) => pairRunsQueryOptions(id, false), all);
    expect(after).toEqual({ opening: 0, thirtySeconds: 0 });
    vi.mocked(listStageChainRuns).mockReset();
    // The same hundred pairs with ten in view, at the operational cadence: ten reads on open, then three each for the five moving ones.
    const inView = new Set(all.slice(0, 10));
    const scrolled = await poll((id) => pairRunsQueryOptions(id, inView.has(id)), all);
    expect(scrolled).toEqual({ opening: 10, thirtySeconds: 5 * 3 });
  });
});
