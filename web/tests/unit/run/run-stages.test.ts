/**
 * `RUN-STAGES-WEB-01` — the models and the facts of a chip, as `getRunStages` states them: the rail's one line, the read of the
 * answer, the cadence (the stages have no clock; the run's one loop marks them stale at each reading), and the view a screen reads.
 *
 * Pure functions are calls; the cadence is driven on a client and an observer, so no timer is waited on; the view is one render over a
 * seeded cache (the harness runs no effect, so what is read is the cache's answer, which is exactly what a screen sees before its
 * first re-read).
 */

import { createElement } from 'react';
import { QueryObserver } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';

import type { RunStage, RunStageCell, RunStages, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import {
  chipModelLine, modelsCount, planModelIds, recordRunReading, runStagesKey, stageOfChip, useRunStages,
} from '@/entities/audit-run';

import { RUN_ID, runStatus } from '../review/fixtures';
import { newClient, renderScreen } from '../screens/harness';

const FACTS = {
  state: 'done', calls_succeeded: 0, calls_failed: 0, calls_retried: 0, input_tokens: 0, output_tokens: 0,
  subscription_input_tokens: 0, subscription_output_tokens: 0, cost_micros: 0,
} as const;

const cell = (role: RunStageCell['role'], model_id: string | undefined, extra: Partial<RunStageCell> = {}): RunStageCell => ({
  role, ...(model_id === undefined ? {} : { model_id }), ...extra,
});
const stage = (chip: RunStage['chip'], plan: RunStageCell[]): RunStage => ({ chip, stage_ids: ['x'], plan, facts: FACTS });
const answer = (items: RunStage[]): RunStages => ({ run_id: RUN_ID, state: 'running', plan_source: 'stage_plan', items });

describe('the line a chip carries on the rail', () => {
  it('is the short name when every cell is on one model, and the pin in the tooltip', () => {
    expect(chipModelLine(stage('text', [cell('main', 'claude-sonnet-5-5')]))).toEqual({ text: 'Sonnet 5.5', title: 'claude-sonnet-5-5' });
    // Legs and a judge on the one model are still one model.
    expect(chipModelLine(stage('blocks', [cell('leg1', 'gpt-6-sol'), cell('judge', 'gpt-6-sol')]))?.text).toBe('GPT 6 sol');
  });

  it('is the number of models for an ensemble, with the short names in the tooltip', () => {
    const claude = stage('blocks', [cell('leg1', 'claude-opus-5-5'), cell('judge', 'claude-sonnet-5-5')]);
    expect(chipModelLine(claude)).toEqual({ text: '2 модели', title: 'Opus 5.5 · Sonnet 5.5' });
    const codex = stage('blocks', [cell('leg1', 'gpt-6-astra'), cell('leg2', 'gpt-6-sol'), cell('judge', 'gpt-6.1-sol')]);
    expect(chipModelLine(codex)?.text).toBe('3 модели');
  });

  it('says «модели» after 2 to 4 and «моделей» after 5, and «моделей» at 11 to 14', () => {
    expect([2, 3, 4, 5, 11, 12, 14, 21, 22].map(modelsCount)).toEqual([
      '2 модели', '3 модели', '4 модели', '5 моделей', '11 моделей', '12 моделей', '14 моделей', '21 моделей', '22 модели',
    ]);
  });

  it('is nothing for a chip that has no cell, a cell with no model, or no entry at all', () => {
    expect(chipModelLine(stage('merge', []))).toBeNull();
    expect(chipModelLine(stage('text', [cell('main', undefined)]))).toBeNull();
    expect(chipModelLine(null)).toBeNull();
    // A cell that names no model is not counted among the ones that do.
    expect(chipModelLine(stage('blocks', [cell('leg1', 'claude-opus-5-5'), cell('judge', undefined)]))?.text).toBe('Opus 5.5');
  });

  it('keeps a pin it cannot shorten as it is, never invents a name', () => {
    expect(chipModelLine(stage('text', [cell('main', 'mystery-9')]))?.text).toBe('mystery-9');
  });

  it('finds the entry of a chip in the answer, and none for a chip the answer does not list', () => {
    const stages = answer([stage('text', [cell('main', 'claude-sonnet-5-5')]), stage('blocks', [cell('main', 'gpt-6-astra')])]);
    expect(stageOfChip(stages, 'blocks')?.chip).toBe('blocks');
    expect(stageOfChip(stages, 'norms')).toBeNull();
    expect(stageOfChip(undefined, 'text')).toBeNull();
    expect(planModelIds(stageOfChip(stages, 'text'))).toEqual(['claude-sonnet-5-5']);
  });
});

describe('the cadence: the stages are asked about when the run is, and by nobody else', () => {
  const status = (state: RunStatus['state']) => runStatus({ state, terminal_at: state === 'running' ? null : '2026-09-10T08:04:00.000Z' });
  const keysOf = (spy: ReturnType<typeof vi.spyOn>) => spy.mock.calls.map((call) => (call[0] as { queryKey: unknown }).queryKey);

  it('files a reading of the run and marks the stages and the journal stale, and the dashboard only at the terminal one', () => {
    const client = newClient();
    const spy = vi.spyOn(client, 'invalidateQueries');
    recordRunReading(client, RUN_ID, status('running'));
    expect(client.getQueryData(queryKeys.runs.detail(RUN_ID))?.state).toBe('running');
    expect(keysOf(spy)).toEqual([queryKeys.execution.journal(RUN_ID), runStagesKey(RUN_ID)]);
    spy.mockClear();
    recordRunReading(client, RUN_ID, status('published'));
    expect(keysOf(spy)).toEqual([queryKeys.execution.journal(RUN_ID), runStagesKey(RUN_ID), queryKeys.dashboard.summary()]);
  });

  it('makes a mounted reader read again at each reading, and a reader that is not mounted ask nothing', async () => {
    const client = newClient();
    let reads = 0;
    const observer = new QueryObserver(client, {
      queryKey: runStagesKey(RUN_ID),
      queryFn: async () => { reads += 1; return answer([]); },
    });
    const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
    const unsubscribe = observer.subscribe(() => undefined);
    await settle();
    expect(reads).toBe(1);
    recordRunReading(client, RUN_ID, status('running'));
    await settle();
    expect(reads).toBe(2);
    // The reading that ends the loop is the last one the reader makes: it is the one that makes the facts final.
    recordRunReading(client, RUN_ID, status('published'));
    await settle();
    expect(reads).toBe(3);
    unsubscribe();
    recordRunReading(client, RUN_ID, status('running'));
    await settle();
    expect(reads).toBe(3);
    // Another run's readings do not touch this run's stages.
    const other = 'run_01M2545JSD15ETSNNV904X99ZZ';
    const again = observer.subscribe(() => undefined);
    await settle();
    const before = reads;
    recordRunReading(client, other, runStatus({ run_id: other, state: 'running', terminal_at: null }));
    await settle();
    expect(reads).toBe(before);
    again();
  });
});

describe('the view a screen reads', () => {
  function Probe({ enabled }: { readonly enabled: boolean }) {
    const view = useRunStages(RUN_ID, enabled);
    return createElement('p', { 'data-phase': view.phase, 'data-items': view.phase === 'read' ? view.stages.items.length : -1 });
  }
  const render = (seed: RunStages | null, enabled = true) => {
    const client = newClient();
    if (seed !== null) client.setQueryData(runStagesKey(RUN_ID), seed);
    return renderScreen(client, createElement(Probe, { enabled }));
  };

  it('is loading before the first answer, and is not an error', () => {
    expect(render(null)).toContain('data-phase="loading"');
    // A run not read yet (or not found) has no stages to ask for: the view stays loading and nothing is requested.
    expect(render(null, false)).toContain('data-phase="loading"');
  });

  it('is the answer once the cache holds one', () => {
    const markup = render(answer([stage('text', [cell('main', 'claude-sonnet-5-5')])]));
    expect(markup).toContain('data-phase="read"');
    expect(markup).toContain('data-items="1"');
  });
});
