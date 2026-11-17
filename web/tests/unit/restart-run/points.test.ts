/**
 * `RUN-RESTART-01` / `R-155a`: what a restart is offered for, and what it takes and computes. The contract's `RestartPoint` and the
 * stage dictionary's eight chips are held to each other in both directions, so a ninth chip, or a point the dictionary does not know,
 * reddens here rather than on the screen.
 */

import { describe, expect, it } from 'vitest';

import { RESTART_POINT_VALUES } from '@/shared/api';
import { RUN_CHIPS, RUN_CHIP_IDS } from '@/entities/audit-run';
import {
  RESTART_POINTS, computedFrom, mayRestart, pointName, pointNames, restartPointOf, restartableRun, restartableState,
  stageIdsTakenBefore, takenBefore, takesNorms,
} from '@/features/restart-run';

describe('the restart points', () => {
  it('are the eight chips of the run screen, in the order the rail draws them', () => {
    expect([...RESTART_POINTS]).toEqual([...RUN_CHIP_IDS]);
    expect([...RESTART_POINT_VALUES]).toEqual([...RUN_CHIP_IDS]);
    expect(RUN_CHIP_IDS.map(restartPointOf)).toEqual([...RESTART_POINTS]);
  });

  it('are named by the chip\'s short name', () => {
    expect(RESTART_POINTS.map(pointName)).toEqual(RUN_CHIPS.map((chip) => chip.short));
    expect(pointNames(['preparation', 'text'])).toBe('«Подготовка», «Текст»');
  });

  it('take the chips before the point and compute the point and every later one', () => {
    expect(takenBefore('preparation')).toEqual([]);
    expect(computedFrom('preparation')).toEqual([...RESTART_POINTS]);
    expect(takenBefore('blocks')).toEqual(['preparation', 'text']);
    expect(computedFrom('blocks')).toEqual(['blocks', 'cross_check', 'merge', 'norms', 'review', 'correction']);
    for (const point of RESTART_POINTS) expect([...takenBefore(point), ...computedFrom(point)]).toEqual([...RESTART_POINTS]);
  });

  it('name, for the rail, the stage ids of the chips taken from the source', () => {
    expect([...stageIdsTakenBefore('preparation')]).toEqual([]);
    expect([...stageIdsTakenBefore('text')]).toEqual(['source_preparation', 'page_geometry_extraction', 'document_context_build']);
    expect([...stageIdsTakenBefore('cross_check')]).toEqual([
      'source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis', 'block_analysis',
    ]);
  });

  it('warn about the norms from the critic on, and not before', () => {
    expect(RESTART_POINTS.filter(takesNorms)).toEqual(['review', 'correction']);
  });
});

describe('who is offered a restart, and for which run', () => {
  it('only a run that ended without a clean result', () => {
    for (const state of ['partial', 'failed', 'cancelled'] as const) expect(restartableState(state)).toBe(true);
    for (const state of ['published', 'created', 'queued', 'running', 'validating'] as const) expect(restartableState(state)).toBe(false);
    expect(restartableState(undefined)).toBe(false);
  });

  it('not a run a restart has replaced', () => {
    expect(restartableRun({ state: 'failed' })).toBe(true);
    expect(restartableRun({ state: 'failed', replaced_by_run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8N' as never })).toBe(false);
  });

  it('an expert or an administrator, and an account not known yet is left to the server', () => {
    expect(mayRestart(['expert'])).toBe(true);
    expect(mayRestart(['admin'])).toBe(true);
    expect(mayRestart(['viewer'])).toBe(false);
    expect(mayRestart([])).toBe(false);
    expect(mayRestart(undefined)).toBe(true);
  });
});
