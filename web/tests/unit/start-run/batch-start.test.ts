/**
 * Starting several documents with one agreement (`R-151c`).
 *
 * The owner ruled one dialog with every estimate and one consent for the batch, while the server still records a
 * consent per run. These cases pin both halves: the arithmetic of the agreement (each run's ceiling, the total, a
 * failed estimate left out), and, mounted live, that nothing starts before the agreement and that each run is
 * started with its own estimate's consent and its own idempotency key.
 */

import { createElement } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  estimateRunCost: vi.fn(),
  startRun: vi.fn(),
}));

import type { RunCostEstimate, StartRunRequest, VersionUid } from '@/shared/api';
import { ApiError, estimateRunCost, startRun } from '@/shared/api';
import { BatchStartPanel, batchConsent, batchIsFree, batchTotals, estimateFits, minimumCeiling } from '@/features/start-run';

import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import type { LiveRender } from '../analysis-settings/live-render';
import { mountLive } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { runStatus } from '../review/fixtures';

const A = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4QA1' as VersionUid;
const B = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4QA2' as VersionUid;
const C = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4QA3' as VersionUid;
const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function estimateFor(versionUid: VersionUid, over: Partial<RunCostEstimate> = {}): RunCostEstimate {
  return { ...costEstimate({ version_uid: versionUid }), estimate_digest: versionUid.slice(-2).padEnd(64, '0').replace(/[^0-9a-f]/g, 'a'), ...over };
}

describe('the arithmetic of one agreement', () => {
  it('caps each run at its recommended ceiling, never under what it is estimated to cost', () => {
    const estimate = estimateFor(A, { estimated_cost_micros: 1_200_000, recommended_ceiling_micros: 1_500_000 });
    expect(batchConsent(estimate)).toEqual({ estimate_digest: estimate.estimate_digest, ceiling_micros: 1_500_000, confirmed: true });
    expect(minimumCeiling(estimateFor(A, { billing: 'metered', estimated_cost_micros: 0, recommended_ceiling_micros: 0 }))).toBe(1);
  });

  it('totals the ready estimates and counts a failed one apart', () => {
    const totals = batchTotals([
      { kind: 'ready', estimate: estimateFor(A, { estimated_cost_micros: 1_000_000, recommended_ceiling_micros: 1_200_000 }) },
      { kind: 'ready', estimate: estimateFor(B, { estimated_cost_micros: 500_000, recommended_ceiling_micros: 700_000 }) },
      { kind: 'failed', text: 'нет' },
    ]);
    expect(totals).toEqual({ ready: 2, pending: 0, failed: 1, costMicros: 1_500_000, ceilingMicros: 1_900_000 });
  });

  it('is free only when something is ready and every ready estimate is unmetered', () => {
    const free = (id: VersionUid) => ({ kind: 'ready' as const, estimate: estimateFor(id, { billing: 'unmetered', estimated_cost_micros: 0, recommended_ceiling_micros: 0 }) });
    const billed = (id: VersionUid) => ({ kind: 'ready' as const, estimate: estimateFor(id) });
    expect(batchIsFree([free(A), free(B)])).toBe(true);
    expect(batchIsFree([free(A), { kind: 'failed', text: 'нет' }, { kind: 'pending' }])).toBe(true);
    expect(batchIsFree([free(A), billed(B)])).toBe(false);
    expect(batchIsFree([billed(A)])).toBe(false);
    expect(batchIsFree([])).toBe(false);
    expect(batchIsFree([{ kind: 'failed', text: 'нет' }])).toBe(false);
    expect(batchConsent(free(A).estimate)).toEqual({ estimate_digest: free(A).estimate.estimate_digest, ceiling_micros: 0, confirmed: true });
  });

  it('agrees only to an estimate of this version under the standard limits', () => {
    expect(estimateFits(estimateFor(A), A)).toBe(true);
    expect(estimateFits(estimateFor(A), B)).toBe(false);
    expect(estimateFits(estimateFor(A, { relaxed_limits: true }), A)).toBe(false);
  });
});

describe('the batch panel, mounted', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.mocked(estimateRunCost).mockReset();
    vi.mocked(startRun).mockReset();
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => {
      if (body.version_uid === C) {
        throw new ApiError(503, { contract_version: '1.51.0', error_code: 'dependency_unavailable', message: 'down', correlation_id: 'cid-1', retryable: true }, 'cid-1');
      }
      return { data: estimateFor(body.version_uid as VersionUid) } as never;
    });
    vi.mocked(startRun).mockImplementation(async ({ body }) => ({ data: runStatus({ version_uid: body.version_uid }) }) as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: newClient() },
      createElement(BatchStartPanel, {
        projectUid: PROJECT,
        entries: [{ versionUid: A, title: 'Документ А' }, { versionUid: B, title: 'Документ Б' }, { versionUid: C, title: 'Документ В' }],
        onClose: () => {},
      })));
    await live.settle(async () => {});
    return live;
  }

  it('estimates every document, lists the one without an estimate, and starts nothing before the agreement', async () => {
    const view = await mount();
    expect(vi.mocked(estimateRunCost).mock.calls.map(([input]) => input.body.version_uid)).toEqual([A, B, C]);
    expect(view.markup()).toContain('Без оценки не запускается: 1.');
    expect(await view.press('Запустить 2')).toBe(false);
    expect(vi.mocked(startRun)).not.toHaveBeenCalled();
  });

  it('after one agreement, starts each estimated run with its own consent and its own key', async () => {
    const view = await mount();
    expect(await view.check('Согласен на расходы не более $3 по 2 прогонам', true)).toBe(true);
    expect(await view.press('Запустить 2')).toBe(true);
    await view.settle(async () => {});
    const calls = vi.mocked(startRun).mock.calls.map(([input]) => input as { body: StartRunRequest; idempotencyKey: string });
    expect(calls.map((call) => call.body.version_uid)).toEqual([A, B]);
    expect(calls.map((call) => call.body.cost_consent?.estimate_digest)).toEqual([estimateFor(A).estimate_digest, estimateFor(B).estimate_digest]);
    expect(new Set(calls.map((call) => call.idempotencyKey)).size).toBe(2);
    expect(view.markup()).toContain('прогон запущен');
  });

  it('sends no executor, group or preset for any document, and draws no selector', async () => {
    const view = await mount();
    expect(view.markup()).not.toContain('<select');
    expect(view.markup()).not.toContain('<option');
    await view.check('Согласен на расходы не более $3 по 2 прогонам', true);
    await view.press('Запустить 2');
    await view.settle(async () => {});
    const bodies = [...vi.mocked(estimateRunCost).mock.calls.map(([input]) => input.body), ...vi.mocked(startRun).mock.calls.map(([input]) => (input as { body: StartRunRequest }).body)];
    expect(bodies.length).toBe(5);
    for (const body of bodies) for (const key of Object.keys(body)) expect(['version_uid', 'cost_consent']).toContain(key);
  });
});

describe('the batch panel when nothing in it can be charged', () => {
  let live: LiveRender | null = null;
  const free = (versionUid: VersionUid) =>
    estimateFor(versionUid, { billing: 'unmetered', estimated_cost_micros: 0, recommended_ceiling_micros: 0 });

  beforeEach(() => {
    vi.mocked(estimateRunCost).mockReset();
    vi.mocked(startRun).mockReset();
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({
      data: body.version_uid === B ? estimateFor(B) : free(body.version_uid as VersionUid),
    }) as never);
    vi.mocked(startRun).mockImplementation(async ({ body }) => ({ data: runStatus({ version_uid: body.version_uid }) }) as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(entries: readonly { versionUid: VersionUid; title: string }[]): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: newClient() },
      createElement(BatchStartPanel, { projectUid: PROJECT, entries, onClose: () => {} })));
    await live.settle(async () => {});
    return live;
  }

  it('lists every document with 0, has no tick-box, and one confirm starts them all', async () => {
    const view = await mount([{ versionUid: A, title: 'Документ А' }, { versionUid: C, title: 'Документ В' }]);
    const markup = view.markup();
    // One dialog, with each document's 0 and the total 0.
    expect(markup.match(/data-batch-start=/g)).toHaveLength(1);
    expect(markup.match(/\$0 · без тарификации/g)).toHaveLength(3);
    expect(markup).toContain('Итого по 2 из 2: $0 · без тарификации.');
    expect(markup).not.toContain('<input');
    expect(markup).not.toContain('Согласен на расходы');
    expect(vi.mocked(startRun)).not.toHaveBeenCalled();
    expect(await view.press('Запустить 2')).toBe(true);
    await view.settle(async () => {});
    const calls = vi.mocked(startRun).mock.calls.map(([input]) => input as { body: StartRunRequest; idempotencyKey: string });
    expect(calls.map((call) => call.body)).toEqual([A, C].map((id) => ({
      version_uid: id, cost_consent: { estimate_digest: free(id).estimate_digest, ceiling_micros: 0, confirmed: true },
    })));
    expect(new Set(calls.map((call) => call.idempotencyKey)).size).toBe(2);
    expect(view.markup()).toContain('прогон запущен');
  });

  it('keeps the agreement when even one document can be charged', async () => {
    const view = await mount([{ versionUid: A, title: 'Документ А' }, { versionUid: B, title: 'Документ Б' }]);
    expect(view.markup()).toContain('<input');
    expect(view.markup()).toContain('Согласен на расходы не более $1.5 по 2 прогонам');
    expect(await view.press('Запустить 2')).toBe(false);
    expect(vi.mocked(startRun)).not.toHaveBeenCalled();
  });
});
