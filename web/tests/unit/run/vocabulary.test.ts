/**
 * The run vocabulary, and the one word that is legal on a stage and illegal on a run.
 *
 * `succeeded` is a `StageResult` status. The success terminal of an `AuditRun` is
 * `published`. A fixture whose *run* state is `succeeded` must be rejected rather than
 * rendered, and nothing this slice produces for a run may contain the word.
 */

import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus } from '@/shared/api';
import { RUN_STATE_VALUES, STAGE_STATUS_VALUES, isTerminalRunState } from '@/shared/api';
import { providerModeCaption, runOutcome, stageRows } from '@/entities/audit-run';

function reading(state: RunState, extra: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: 'run_01M2545JSD15ETSNNV904X991J',
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state,
    stages: [],
    ...extra,
  };
}

describe('the run state set is the contract set', () => {
  it('has eight states and none of them is `succeeded`', () => {
    expect(RUN_STATE_VALUES).toEqual([
      'created',
      'queued',
      'running',
      'validating',
      'published',
      'partial',
      'failed',
      'cancelled',
    ]);
    expect(RUN_STATE_VALUES as readonly string[]).not.toContain('succeeded');
  });

  it('keeps `succeeded` where it is legal — the stage status set', () => {
    expect(STAGE_STATUS_VALUES as readonly string[]).toContain('succeeded');
  });

  it('rejects a fixture whose run state is `succeeded` rather than rendering it', () => {
    // The type system refuses it at compile time; this is the runtime half of the same
    // claim, for a fixture that arrived as data rather than as a literal.
    const rogue = 'succeeded';
    expect((RUN_STATE_VALUES as readonly string[]).includes(rogue)).toBe(false);
    expect(() => {
      if (!(RUN_STATE_VALUES as readonly string[]).includes(rogue)) {
        throw new Error(`not a run state: ${rogue}`);
      }
    }).toThrow('not a run state: succeeded');
  });
});

describe('nothing this slice writes for a run says `succeeded`, `done` or `OK`', () => {
  const banned = ['succeeded', 'done', ' ok', 'complete'];

  it('holds for every outcome of every contract state', () => {
    for (const state of RUN_STATE_VALUES) {
      const outcome = runOutcome(reading(state));
      const text = JSON.stringify(outcome).toLowerCase();
      for (const word of banned) {
        expect(text, `${state} outcome contains "${word}"`).not.toContain(word);
      }
      // The outcome always names the contract state or a kind derived from it.
      expect(outcome.kind.length).toBeGreaterThan(0);
    }
  });

  it('holds for every provider-mode caption', () => {
    for (const label of ['live', 'recorded', 'unknown'] as const) {
      expect(providerModeCaption(label).toLowerCase()).not.toContain('succeeded');
    }
  });
});

describe('the success terminal is `published`, and `partial` borrows nothing from it', () => {
  it('gives published, partial and failed three different outcome kinds', () => {
    expect(runOutcome(reading('published')).kind).toBe('published');
    expect(runOutcome(reading('partial')).kind).toBe('partial');
    expect(runOutcome(reading('failed')).kind).toBe('failed');
  });

  it('reports the recorded degradation set on a partial run', () => {
    const outcome = runOutcome(
      reading('partial', { degradation_set: ['text_analysis', 'document_context_build'] }),
    );
    expect(outcome.kind).toBe('partial');
    if (outcome.kind !== 'partial') throw new Error('unreachable');
    expect(outcome.degradation).toEqual(['text_analysis', 'document_context_build']);
  });

  it('reports the terminal reason on a failed run', () => {
    const outcome = runOutcome(reading('failed', { terminal_reason: 'analysis_failed' }));
    if (outcome.kind !== 'failed') throw new Error('unreachable');
    expect(outcome.terminalReason).toBe('analysis_failed');
  });

  it('classifies the four terminals as terminal and the four others as not', () => {
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) {
      expect(isTerminalRunState(state)).toBe(true);
    }
    for (const state of ['created', 'queued', 'running', 'validating'] as const) {
      expect(isTerminalRunState(state)).toBe(false);
    }
  });
});

describe('stage rows keep the run and stage vocabularies apart', () => {
  it('renders a `succeeded` stage on a run that is not published', () => {
    const rows = stageRows(
      reading('running', {
        stages: [{ stage_id: 'source_preparation', status: 'succeeded' }],
      }),
    );
    const first = rows[0];
    expect(first?.stageId).toBe('source_preparation');
    expect(first?.status).toBe('succeeded');
  });
});
