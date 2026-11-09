/**
 * `UI-A-65`, `RUN-SCREEN-01a`: the open run's live line, the time each chip took on the rail and the estimated finish in the head (the
 * original's stage cards, live banner and «≈ до»), as far as the reading states them. A closed run has neither the line nor a clock.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { chipProgress, formatClockTime, runChips, runFinishEstimate } from '@/entities/audit-run';
import { RunEta, RunLiveLineView, RunProgress, RunWaitLine } from '@/widgets/run-progress';
import { liveElapsed } from '@/widgets/run-progress/ui/run-live-line';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

function screen(overrides: Partial<RunStatus> = {}): string {
  const status = runStatus(overrides);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

const live = (status: Pick<RunStatus, 'state' | 'stages' | 'analysis_profile_id' | 'interrupted_reason'>) =>
  chipProgress(runChips({ status, procedures: [] })).live;

describe('the live line of an open run', () => {
  it('names the first chip the run has not finished, and none when every chip has started', () => {
    const open = live({ state: 'running', stages: [{ stage_id: 'source_preparation', status: 'succeeded', error_code: null }] });
    expect(open?.definition.id).toBe('preparation');
    expect(open?.state).toBe('running');
    const done = live({
      state: 'running',
      stages: ['source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis'].map((stage_id) => ({
        stage_id: stage_id as 'source_preparation', status: 'succeeded' as const, error_code: null,
      })),
    });
    expect(done).toBeNull();
  });

  it('says the chip and the time, and «—» before the clock is read', () => {
    const chip = live({ state: 'running', stages: [] });
    const markup = renderToStaticMarkup(createElement(RunLiveLineView, { chip, elapsed: '—' }));
    expect(markup).toContain('data-run-live="preparation"');
    expect(markup).toContain('Сейчас: <strong>Подготовка документа</strong>');
    expect(markup).toContain('прогон идёт —');
  });

  it('adds the window, the model and the server when the reading has them, and only then', () => {
    const chip = live({ state: 'running', stages: [{ stage_id: 'text_analysis', status: 'succeeded', error_code: null }] });
    const bare = renderToStaticMarkup(createElement(RunLiveLineView, { chip, elapsed: '1 с' }));
    expect(bare).not.toContain('data-run-live-progress');
    expect(bare).not.toContain('data-run-live-model');
    expect(bare).not.toContain('data-run-live-server');
    const stages = ['source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis'].map((stage_id) => ({
      stage_id: stage_id as 'source_preparation', status: 'succeeded' as const, error_code: null,
    }));
    const procedures = [{ id: 'block_analysis', title: 'Анализ блоков', status: 'running' as const, reason: null, dependency: null, errorCode: null }];
    const blocks = chipProgress(runChips({ status: runStatus({ state: 'running', stages }), procedures })).live;
    expect(blocks?.definition.id).toBe('blocks');
    const markup = renderToStaticMarkup(createElement(RunLiveLineView, {
      chip: blocks,
      progress: { kind: 'window', index: 2, total: 5 },
      model: { short: 'Opus 5.5', pin: 'claude-opus-5-5' },
      server: 'adm1.hlab.kz',
      elapsed: '12 мин 0 с',
      elapsedOf: 'chip',
    }));
    expect(markup).toContain('Сейчас: <strong>Анализ блоков</strong> · <span data-run-live-progress="window">окно 2 из 5</span>');
    expect(markup).toContain('<span data-run-live-model="true" title="claude-opus-5-5">Opus 5.5</span>');
    expect(markup).toContain('<span data-run-live-server="true">adm1.hlab.kz</span>');
    expect(markup).toContain('в этапе 12 мин 0 с');
  });

  it('counts from the chip start when the chip has one, from the run\'s creation when it has not, and reads «—» before the clock', () => {
    const status = runStatus({ created_at: '2026-11-08T08:00:00.000Z' });
    const started = runChips({
      status: runStatus({ state: 'running', stages: [{ stage_id: 'source_preparation', status: 'succeeded', error_code: null, started_at: '2026-11-08T08:00:30.000Z' }] }),
      procedures: [],
    })[0] ?? null;
    const now = Date.parse('2026-11-08T08:02:00.000Z');
    expect(liveElapsed(status, started, now)).toEqual({ text: '1 мин 30 с', of: 'chip' });
    expect(liveElapsed(status, null, now)).toEqual({ text: '2 мин 0 с', of: 'run' });
    expect(liveElapsed(status, started, null)).toEqual({ text: '—', of: 'run' });
  });

  it('is drawn for an open run and not for a closed one', () => {
    expect(screen({ state: 'running', terminal_at: null })).toContain('data-run-live=');
    expect(screen({ state: 'published' })).not.toContain('data-run-live=');
    expect(screen({ state: 'running', terminal_at: null, interrupted_reason: 'worker_lost' })).not.toContain('data-run-live=');
  });

  it('says what a queued run waits for, in the place of a stage', () => {
    const line = renderToStaticMarkup(createElement(RunWaitLine, { sentence: 'В очереди: исполнитель занят.', model: { short: 'Opus 5.5', pin: 'claude-opus-5-5' } }));
    expect(line).toContain('data-run-live="waiting"');
    expect(line).toContain('<span data-run-executor-waiting="true">В очереди: исполнитель занят.</span>');
    expect(line).toContain('Opus 5.5');
    expect(line).not.toContain('Сейчас:');
  });
});

describe('the time a chip took, on the rail', () => {
  it('states it under a chip whose every stage has both ends, and nothing under one that has not', () => {
    const markup = screen({
      stages: [
        { stage_id: 'source_preparation', status: 'succeeded', error_code: null, started_at: '2026-11-06T10:00:00.000Z', finished_at: '2026-11-06T10:00:00.030Z' },
        { stage_id: 'page_geometry_extraction', status: 'succeeded', error_code: null, started_at: '2026-11-06T10:00:00.030Z', finished_at: '2026-11-06T10:00:01.000Z' },
        { stage_id: 'document_context_build', status: 'succeeded', error_code: null, started_at: '2026-11-06T10:00:01.000Z', finished_at: '2026-11-06T10:00:02.500Z' },
        { stage_id: 'text_analysis', status: 'succeeded', error_code: null },
      ],
    });
    expect(markup).toMatch(/data-run-chip="preparation"[^>]*>.*?data-chip-took="2,5 с"/s);
    expect((markup.match(/data-chip-took=/g) ?? []).length).toBe(1);
  });
});

describe('the estimated finish of an open run (`UI-B-45`)', () => {
  const FINISH = '2026-11-08T09:05:30.000Z';
  const BEFORE = Date.parse('2026-11-08T08:50:00.000Z');
  const AFTER = Date.parse('2026-11-08T09:20:00.000Z');

  it('words the instant as «ЧЧ:ММ» on a 24-hour clock, in the zone it is asked for', () => {
    expect(formatClockTime(FINISH, 'UTC')).toBe('09:05');
    expect(formatClockTime('2026-11-08T23:59:59.000Z', 'UTC')).toBe('23:59');
    expect(formatClockTime('2026-11-08T00:00:00.000Z', 'UTC')).toBe('00:00');
    expect(formatClockTime(FINISH, 'Asia/Yekaterinburg')).toBe('14:05');
    expect(formatClockTime('not an instant', 'UTC')).toBeNull();
  });

  it('shows nothing the reading does not carry, and nothing before the clock is read', () => {
    expect(runFinishEstimate({}, BEFORE, 'UTC')).toBeNull();
    expect(runFinishEstimate({ estimated_finish_at: FINISH }, null, 'UTC')).toBeNull();
    expect(runFinishEstimate({ estimated_finish_at: 'garbled' }, BEFORE, 'UTC')).toBeNull();
  });

  it('says whether the instant is behind the clock reading, and computes no duration of its own', () => {
    expect(runFinishEstimate({ estimated_finish_at: FINISH }, BEFORE, 'UTC')).toEqual({ iso: FINISH, clock: '09:05', late: false });
    expect(runFinishEstimate({ estimated_finish_at: FINISH }, AFTER, 'UTC')).toEqual({ iso: FINISH, clock: '09:05', late: true });
  });

  it('is worded «≈ до ЧЧ:ММ» with the instant on the time element, and says «дольше обычного» once it has passed', () => {
    const eta = (finish: ReturnType<typeof runFinishEstimate>) => renderToStaticMarkup(createElement(RunEta, { finish }));
    const ahead = eta(runFinishEstimate({ estimated_finish_at: FINISH }, BEFORE, 'UTC'));
    expect(ahead).toContain('≈ до');
    expect(ahead).toContain(`<time dateTime="${FINISH}" title="2026-11-08 09:05:30 UTC">09:05</time>`);
    expect(ahead).not.toContain('дольше обычного');
    expect(ahead).not.toContain('data-run-eta-late');
    const late = eta(runFinishEstimate({ estimated_finish_at: FINISH }, AFTER, 'UTC'));
    expect(late).toContain('дольше обычного');
    expect(late).toContain('data-run-eta-late');
    expect(eta(null)).toBe('');
  });

  it('is not part of a server render: the clock is read after mount, so the first client render says the same', () => {
    const open = screen({ state: 'running', terminal_at: null, estimated_finish_at: FINISH });
    expect(open).toContain('data-run-live=');
    expect(open).not.toContain('data-run-eta');
    expect(open).not.toContain('≈ до');
  });
});
