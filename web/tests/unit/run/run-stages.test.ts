/**
 * `RUN-STAGES-WEB-01` — the models and the facts of a chip, as `getRunStages` states them: the rail's one line, the read of the
 * answer, the poll that follows the status loop's delays, and the view a screen reads.
 *
 * Pure functions are calls; the view is one render over a seeded cache (the harness runs no effect, so what is read is the cache's
 * answer, which is exactly what a screen sees before its first re-read).
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunStage, RunStageCell, RunStages } from '@/shared/api';
import { pollDelayMs } from '@/shared/config';
import {
  chipModelLine, modelsCount, planModelIds, runStagesKey, runStagesPollInterval, stageOfChip, useRunStages,
} from '@/entities/audit-run';

import { RUN_ID } from '../review/fixtures';
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

describe('the poll', () => {
  it('follows the status loop\'s delays, counted from the readings, and never asks at once', () => {
    expect([1, 2, 3, 4, 5, 6, 7].map((readings) => runStagesPollInterval(true, readings))).toEqual([2000, 3000, 4500, 6750, 10125, 15000, 15000]);
    expect([1, 2, 3, 4, 5, 6].map((readings) => runStagesPollInterval(true, readings))).toEqual([1, 2, 3, 4, 5, 6].map(pollDelayMs));
    // A query that has not read yet waits the first delay, not zero.
    expect(runStagesPollInterval(true, 0)).toBe(2000);
  });

  it('stops when the run is not open', () => {
    expect(runStagesPollInterval(false, 1)).toBe(false);
    expect(runStagesPollInterval(false, 9)).toBe(false);
  });
});

describe('the view a screen reads', () => {
  function Probe({ active }: { readonly active: boolean }) {
    const view = useRunStages(RUN_ID, active);
    return createElement('p', { 'data-phase': view.phase, 'data-items': view.phase === 'read' ? view.stages.items.length : -1 });
  }
  const render = (seed: RunStages | null) => {
    const client = newClient();
    if (seed !== null) client.setQueryData(runStagesKey(RUN_ID), seed);
    return renderScreen(client, createElement(Probe, { active: true }));
  };

  it('is loading before the first answer, and is not an error', () => {
    expect(render(null)).toContain('data-phase="loading"');
  });

  it('is the answer once the cache holds one', () => {
    const markup = render(answer([stage('text', [cell('main', 'claude-sonnet-5-5')])]));
    expect(markup).toContain('data-phase="read"');
    expect(markup).toContain('data-items="1"');
  });
});
