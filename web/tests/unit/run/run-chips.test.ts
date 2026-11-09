/**
 * `RUN-SCREEN-01a`: what the rail says about a run -- which chips it has, how each stands, and what the live position is.
 *
 * Pure functions over a reading, so every row of the table is a case: a chip appears only when a stage row or a procedure mentions it,
 * a stage state is canonical for the chips it covers, a procedure speaks for the rest, and the two states that are the screen's own
 * reading (the run is on this chip, the run waits to start) exist only while the run is open.
 */

import { describe, expect, it } from 'vitest';

import type { RunStatus, StageId } from '@/shared/api';
import {
  AR_V3_BETA_PROFILE_ID, chipProgress, extendedLiveProgress, liveProgressText, procedureReadings, runChips, shortModelName,
} from '@/entities/audit-run';
import type { ProcedureReading, ProcedureStatus } from '@/entities/audit-run';

import { runStatus } from '../review/fixtures';

const PREP: readonly StageId[] = ['source_preparation', 'page_geometry_extraction', 'document_context_build'];
const stage = (stage_id: StageId, status: 'succeeded' | 'partial' | 'failed' | 'skipped', extra: Record<string, unknown> = {}) => ({
  stage_id, status, error_code: status === 'succeeded' ? null : 'analysis_failed', ...extra,
});
const proc = (id: string, status: ProcedureStatus, extra: Partial<ProcedureReading> = {}): ProcedureReading => ({
  id, title: id, status, reason: null, dependency: null, errorCode: null, ...extra,
});
const chips = (over: Partial<RunStatus>, procedures: readonly ProcedureReading[] = [], reused?: ReadonlySet<string>) =>
  runChips({ status: runStatus(over), procedures, reused });
const stateOf = (list: ReturnType<typeof chips>) => Object.fromEntries(list.map((chip) => [chip.definition.id, chip.state]));

describe('which chips a run has', () => {
  it('a plain PC-01 run has Подготовка and Текст, and no other chip is drawn', () => {
    expect(chips({ stages: [] }).map((chip) => chip.definition.id)).toEqual(['preparation', 'text']);
  });

  it('a procedure of the extended review adds its chip, in the rail\'s order, and report generation adds none', () => {
    const list = chips({ stages: [] }, [
      proc('finding_review', 'queued'), proc('block_analysis', 'queued'), proc('report_generation', 'queued'), proc('finding_merge', 'queued'),
    ]);
    expect(list.map((chip) => chip.definition.id)).toEqual(['preparation', 'text', 'blocks', 'merge', 'review']);
  });

  it('a stage the run reports outside the PC-01 schedule adds its chip as well', () => {
    expect(chips({ stages: [stage('block_analysis', 'succeeded')] }).map((chip) => chip.definition.id)).toContain('blocks');
  });

  it('the AR v3 profile has its own chip, once it reports its stage, and none of the eight', () => {
    expect(chips({ analysis_profile_id: AR_V3_BETA_PROFILE_ID, stages: [] })).toEqual([]);
    const v3 = chips({ analysis_profile_id: AR_V3_BETA_PROFILE_ID, stages: [{ stage_id: 'ar_v3_citation_review', status: 'succeeded', error_code: null }] });
    expect(v3.map((chip) => chip.definition.id)).toEqual(['ar_v3']);
    expect(v3[0]?.state).toBe('done');
  });
});

describe('how a chip stands, from the stage states', () => {
  const done = (...ids: StageId[]) => ids.map((id) => stage(id, 'succeeded'));

  it('is done when every stage of it succeeded, and not started when none was reported', () => {
    expect(stateOf(chips({ state: 'published', stages: done(...PREP, 'text_analysis') }))).toEqual({ preparation: 'done', text: 'done' });
    expect(stateOf(chips({ state: 'cancelled', stages: [] }))).toEqual({ preparation: 'pending', text: 'pending' });
  });

  it('is failed over partial over done, and skipped when all were skipped', () => {
    expect(stateOf(chips({ state: 'failed', stages: [stage('source_preparation', 'succeeded'), stage('page_geometry_extraction', 'failed')] })).preparation).toBe('failed');
    expect(stateOf(chips({ state: 'partial', stages: [stage('source_preparation', 'succeeded'), stage('page_geometry_extraction', 'partial'), stage('document_context_build', 'failed')] })).preparation).toBe('failed');
    expect(stateOf(chips({ state: 'partial', stages: [stage('source_preparation', 'partial')] })).preparation).toBe('partial');
    expect(stateOf(chips({ state: 'published', stages: [stage('text_analysis', 'skipped')] })).text).toBe('skipped');
  });

  it('carries the error code of the stage that failed, and the time of the stages this run computed', () => {
    const list = chips({ state: 'failed', stages: [
      stage('source_preparation', 'succeeded', { started_at: '2026-11-08T10:00:00.000Z', finished_at: '2026-11-08T10:00:01.000Z' }),
      stage('page_geometry_extraction', 'failed', { started_at: '2026-11-08T10:00:01.000Z', finished_at: '2026-11-08T10:00:04.000Z', error_code: 'storage_integrity_error' }),
      stage('document_context_build', 'skipped', { started_at: '2026-11-08T10:00:04.000Z', finished_at: '2026-11-08T10:00:05.000Z' }),
    ] });
    expect(list[0]?.errorCode).toBe('storage_integrity_error');
    expect(list[0]?.elapsedMs).toBe(5000);
    expect(list[1]?.errorCode).toBeNull();
    expect(list[1]?.elapsedMs).toBeNull();
  });

  it('has no duration while a stage of the chip lacks an end, and none from the stages taken from an earlier run', () => {
    const open = chips({ state: 'running', stages: [stage('source_preparation', 'succeeded', { started_at: '2026-11-08T10:00:00.000Z', finished_at: '2026-11-08T10:00:01.000Z' })] });
    expect(open[0]?.elapsedMs).toBeNull();
    const reused = new Set<string>(PREP);
    const taken = chips({ state: 'published', stages: [...done(...PREP, 'text_analysis')].map((s) => ({ ...s, started_at: '2026-11-08T10:00:00.000Z', finished_at: '2026-11-08T10:00:00.000Z' })) }, [], reused);
    expect(taken[0]?.reused).toBe(true);
    expect(taken[0]?.elapsedMs).toBeNull();
    expect(taken[1]?.reused).toBe(false);
  });
});

describe('how a chip stands, from the extended review', () => {
  const base = { state: 'published' as const, stages: [...PREP, 'text_analysis' as const].map((id) => stage(id, 'succeeded')) };

  it('reads a procedure\'s status for a chip the stages do not cover', () => {
    const list = chips(base, [proc('block_analysis', 'completed'), proc('comprehensive_analysis', 'partial'), proc('finding_merge', 'failed'), proc('norm_verification', 'unavailable'), proc('finding_review', 'skipped'), proc('finding_correction', 'queued')]);
    expect(stateOf(list)).toEqual({
      preparation: 'done', text: 'done', blocks: 'done', cross_check: 'partial', merge: 'failed', norms: 'unavailable', review: 'skipped', correction: 'pending',
    });
  });

  it('is running while a procedure runs or repairs an answer, and keeps the reason code', () => {
    expect(stateOf(chips(base, [proc('block_analysis', 'repairing')])).blocks).toBe('running');
    expect(chips(base, [proc('norm_verification', 'failed', { errorCode: 'codex_timeout' })]).find((c) => c.definition.id === 'norms')?.errorCode).toBe('codex_timeout');
  });

  it('lets the stage state win over a procedure of the same chip, and ignores a status it does not know', () => {
    const list = chips({ ...base, stages: [stage('text_analysis', 'failed')] }, [proc('text_analysis', 'completed')]);
    expect(stateOf(list).text).toBe('failed');
    expect(procedureReadings({ procedures: [{ id: 'block_analysis', title: 'x', status: 'future_status' }, { id: 'finding_merge', title: 'y', status: 'queued' }, { title: 'no id', status: 'queued' }] }).map((p) => p.id)).toEqual(['finding_merge']);
    expect(procedureReadings(null)).toEqual([]);
    expect(procedureReadings({ procedures: 'nope' })).toEqual([]);
  });
});

describe('the two states that are the screen\'s own reading', () => {
  it('puts the run on the first chip that has not started, while the run is open', () => {
    const list = chips({ state: 'running', terminal_at: null, stages: [stage('source_preparation', 'succeeded')] });
    expect(stateOf(list)).toEqual({ preparation: 'running', text: 'pending' });
    const next = chips({ state: 'running', terminal_at: null, stages: [...PREP, 'text_analysis' as const].map((id) => stage(id, 'succeeded')) }, [proc('block_analysis', 'queued'), proc('finding_merge', 'queued')]);
    expect(stateOf(next).blocks).toBe('running');
    expect(stateOf(next).merge).toBe('pending');
  });

  it('keeps a chip a procedure says is running, and promotes none beside it', () => {
    const list = chips({ state: 'running', terminal_at: null, stages: [...PREP, 'text_analysis' as const].map((id) => stage(id, 'succeeded')) }, [proc('block_analysis', 'completed'), proc('comprehensive_analysis', 'running'), proc('finding_merge', 'queued')]);
    expect(stateOf(list)).toMatchObject({ blocks: 'done', cross_check: 'running', merge: 'pending' });
  });

  it('says «ждёт» for the chip a queued run has not started, and for none other', () => {
    expect(stateOf(chips({ state: 'queued', terminal_at: null, stages: [] }))).toEqual({ preparation: 'waiting', text: 'pending' });
  });

  it('promotes nothing on a run that is over or was reconciled after a crash', () => {
    expect(stateOf(chips({ state: 'cancelled', stages: [stage('source_preparation', 'succeeded')] })).text).toBe('pending');
    expect(stateOf(chips({ state: 'failed', stages: [] }))).toEqual({ preparation: 'pending', text: 'pending' });
    expect(stateOf(chips({ state: 'running', terminal_at: null, interrupted_reason: 'worker_lost', stages: [] }))).toEqual({ preparation: 'pending', text: 'pending' });
  });

  it('counts the chips of this run, the ones that did their work, and where the live one is', () => {
    const list = chips({ state: 'running', terminal_at: null, stages: [...PREP].map((id) => stage(id, 'succeeded')) }, [proc('block_analysis', 'queued')]);
    expect(chipProgress(list)).toMatchObject({ total: 3, completed: 1, liveIndex: 2 });
    expect(chipProgress(list).live?.definition.id).toBe('text');
    const over = chips({ state: 'published', stages: [...PREP, 'text_analysis' as const].map((id) => stage(id, 'succeeded')) });
    expect(chipProgress(over)).toMatchObject({ total: 2, completed: 2, live: null, liveIndex: null });
    expect(chipProgress([])).toEqual({ total: 0, completed: 0, live: null, liveIndex: null });
  });
});

describe('the position inside the current phase', () => {
  it('names the running window with the number of windows the server planned', () => {
    const result = { windows: [{ window_id: 'w1', index: 0, status: 'completed' }, { window_id: 'w2', index: 1, status: 'running' }], window_progress: { total: 5 } };
    expect(extendedLiveProgress(result)).toEqual({ kind: 'window', index: 2, total: 5 });
    expect(liveProgressText({ kind: 'window', index: 2, total: 5 })).toBe('окно 2 из 5');
  });

  it('falls back to the windows listed when the server gives no total, and to the window named as current', () => {
    expect(extendedLiveProgress({ windows: [{ window_id: 'a', index: 0, status: 'completed' }, { window_id: 'b', index: 1, status: 'queued' }], window_progress: { current: 'b' } }))
      .toEqual({ kind: 'window', index: 2, total: 2 });
  });

  it('names the running batch of a result without windows, counted among the batches of its procedure', () => {
    const result = { batches: [
      { procedure: 'block_analysis', index: 0, status: 'completed' }, { procedure: 'block_analysis', index: 1, status: 'running' },
      { procedure: 'block_analysis', index: 2, status: 'queued' }, { procedure: 'comprehensive_analysis', index: 0, status: 'queued' },
    ] };
    expect(extendedLiveProgress(result)).toEqual({ kind: 'batch', index: 2, total: 3 });
    expect(liveProgressText({ kind: 'batch', index: 2, total: 3 })).toBe('пакет 2 из 3');
  });

  it('says nothing when nothing is running or the result exposes neither', () => {
    expect(extendedLiveProgress({ windows: [{ window_id: 'a', index: 0, status: 'completed' }] })).toBeNull();
    expect(extendedLiveProgress({ batches: [{ procedure: 'x', index: 0, status: 'queued' }] })).toBeNull();
    expect(extendedLiveProgress(null)).toBeNull();
    expect(extendedLiveProgress({})).toBeNull();
  });
});

describe('a model\'s short name', () => {
  it.each([
    ['claude-opus-5-5', 'Opus 5.5'],
    ['claude-sonnet-5', 'Sonnet 5'],
    ['claude-opus-5', 'Opus 5'],
    ['gpt-6-sol', 'GPT 6 sol'],
    ['gpt-6.1-sol', 'GPT 6.1 sol'],
    ['gpt-6-astra', 'GPT 6 astra'],
  ])('shortens %s to %s', (pin, short) => {
    expect(shortModelName(pin)).toBe(short);
  });

  it('returns a pin it does not recognise as it is, and nothing for an absent one', () => {
    expect(shortModelName('модель-основная')).toBe('модель-основная');
    expect(shortModelName('  ')).toBeNull();
    expect(shortModelName(null)).toBeNull();
    expect(shortModelName(undefined)).toBeNull();
  });
});
