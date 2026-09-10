/**
 * Stage rows.
 *
 * A stage the run has not reported is a visible row with no status, not an absent row.
 * The difference matters: an absent row says "there is nothing to say about this stage",
 * which is a different claim from "this stage has not run".
 */

import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus, StageState } from '@/shared/api';
import { STAGE_ID_VALUES } from '@/shared/api';
import { PC01_STAGE_IDS, stageRows } from '@/entities/audit-run';

function reading(state: RunState, stages: StageState[]): RunStatus {
  return {
    run_id: 'run_01M2545JSD15ETSNNV904X991J',
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state,
    stages,
  };
}

describe('the four stages PC-01 schedules', () => {
  it('are the first four of the contract registry, in order', () => {
    expect(PC01_STAGE_IDS).toEqual([
      'source_preparation',
      'page_geometry_extraction',
      'document_context_build',
      'text_analysis',
    ]);
    expect(STAGE_ID_VALUES.slice(0, 4)).toEqual(PC01_STAGE_IDS);
  });

  it('always produce four rows, even when the run has reported nothing', () => {
    const rows = stageRows(reading('queued', []));
    expect(rows).toHaveLength(4);
    expect(rows.map((r) => r.stageId)).toEqual(PC01_STAGE_IDS);
    for (const row of rows) {
      expect(row.status).toBeNull();
      expect(row.expected).toBe(true);
    }
  });
});

describe('a reported stage fills its row', () => {
  it('carries the status, the error code and the timestamps', () => {
    const rows = stageRows(
      reading('running', [
        {
          stage_id: 'source_preparation',
          status: 'succeeded',
          started_at: '2026-01-01T00:00:01Z',
          finished_at: '2026-01-01T00:00:09Z',
        },
        { stage_id: 'page_geometry_extraction', status: 'failed', error_code: 'analysis_failed' },
      ]),
    );

    expect(rows[0]?.status).toBe('succeeded');
    expect(rows[0]?.errorCode).toBeNull();
    expect(rows[0]?.startedAt).toBe('2026-01-01T00:00:01Z');
    expect(rows[1]?.status).toBe('failed');
    expect(rows[1]?.errorCode).toBe('analysis_failed');
    // The two the run has not reached are still rows.
    expect(rows[2]?.status).toBeNull();
    expect(rows[3]?.status).toBeNull();
  });

  it('carries a skipped stage as skipped rather than dropping it', () => {
    const rows = stageRows(reading('partial', [{ stage_id: 'text_analysis', status: 'skipped' }]));
    expect(rows.find((r) => r.stageId === 'text_analysis')?.status).toBe('skipped');
  });
});

describe('a stage PC-01 does not schedule is shown, and marked as such', () => {
  it('appends it after the four, flagged as unexpected', () => {
    const rows = stageRows(
      reading('running', [
        { stage_id: 'source_preparation', status: 'succeeded' },
        { stage_id: 'norm_verification', status: 'partial', error_code: 'required_norm_unavailable' },
      ]),
    );

    expect(rows).toHaveLength(5);
    const extra = rows[4];
    expect(extra?.stageId).toBe('norm_verification');
    expect(extra?.expected).toBe(false);
    expect(extra?.status).toBe('partial');
    expect(extra?.errorCode).toBe('required_norm_unavailable');
  });

  it('does not duplicate a stage that is both expected and reported', () => {
    const rows = stageRows(
      reading('running', [{ stage_id: 'document_context_build', status: 'succeeded' }]),
    );
    expect(rows.filter((r) => r.stageId === 'document_context_build')).toHaveLength(1);
  });
});
