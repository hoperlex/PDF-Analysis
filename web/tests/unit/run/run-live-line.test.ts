/**
 * `UI-A-65`: the open run's live line, and the time each stage took on the rail (the original's stage cards and
 * live banner, as far as the reading states them). A closed run has neither the line nor a clock.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { formatClockTime, runFinishEstimate, stageRows } from '@/entities/audit-run';
import { RunLiveLineView, RunProgress, liveStageOf } from '@/widgets/run-progress';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

function screen(overrides: Partial<RunStatus> = {}): string {
  const status = runStatus(overrides);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

describe('the live line of an open run', () => {
  it('names the first scheduled stage the run has not reported, and none when all are reported', () => {
    const open = stageRows({ stages: [{ stage_id: 'source_preparation', status: 'succeeded', error_code: null }] });
    expect(liveStageOf(open)?.stageId).toBe('page_geometry_extraction');
    const done = stageRows({
      stages: open.map((row) => ({ stage_id: row.stageId, status: 'succeeded' as const, error_code: null })),
    });
    expect(liveStageOf(done)).toBeNull();
  });

  it('says the stage and the elapsed time, and «—» before the clock is read', () => {
    const rows = stageRows({ stages: [] });
    const markup = renderToStaticMarkup(createElement(RunLiveLineView, { stage: liveStageOf(rows), elapsed: '—' }));
    expect(markup).toContain('data-run-live="source_preparation"');
    expect(markup).toContain('Сейчас:');
    expect(markup).toContain('идёт —');
  });

  it('is drawn for an open run and not for a closed one', () => {
    expect(screen({ state: 'running', terminal_at: null })).toContain('data-run-live=');
    expect(screen({ state: 'published' })).not.toContain('data-run-live=');
    expect(screen({ state: 'running', terminal_at: null, interrupted_reason: 'worker_lost' })).not.toContain('data-run-live=');
  });
});

describe('the time a stage took, on the rail', () => {
  it('states it under a stage that has both ends, and nothing under one that has not', () => {
    const markup = screen({
      stages: [
        { stage_id: 'source_preparation', status: 'succeeded', error_code: null, started_at: '2026-11-06T10:00:00.000Z', finished_at: '2026-11-06T10:00:00.030Z' },
        { stage_id: 'page_geometry_extraction', status: 'succeeded', error_code: null },
      ],
    });
    expect(markup).toMatch(/data-pipeline-stage="source_preparation"[^>]*>.*?data-pipeline-took="30 ms"/s);
    expect((markup.match(/data-pipeline-took=/g) ?? []).length).toBe(1);
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

  it('is worded on the line with the instant on the time element, and says «дольше обычного» once it has passed', () => {
    const stage = liveStageOf(stageRows({ stages: [] }));
    const line = (finish: Parameters<typeof RunLiveLineView>[0]['finish']) =>
      renderToStaticMarkup(createElement(RunLiveLineView, { stage, elapsed: '2 m 3 s', finish }));
    const ahead = line(runFinishEstimate({ estimated_finish_at: FINISH }, BEFORE, 'UTC'));
    expect(ahead).toContain('ожидаемое завершение');
    expect(ahead).toContain(`<time dateTime="${FINISH}" title="2026-11-08 09:05:30 UTC">~09:05</time>`);
    expect(ahead).toContain('идёт 2 m 3 s');
    expect(ahead).not.toContain('дольше обычного');
    expect(ahead).not.toContain('data-run-eta-late');
    const late = line(runFinishEstimate({ estimated_finish_at: FINISH }, AFTER, 'UTC'));
    expect(late).toContain('дольше обычного');
    expect(late).toContain('data-run-eta-late');
    const none = line(null);
    expect(none).not.toContain('ожидаемое');
    expect(none).not.toContain('data-run-eta');
    expect(line(undefined)).toBe(none);
  });

  it('is not part of a server render: the clock is read after mount, so the first client render says the same', () => {
    const open = screen({ state: 'running', terminal_at: null, estimated_finish_at: FINISH });
    expect(open).toContain('data-run-live=');
    expect(open).not.toContain('data-run-eta');
    expect(open).not.toContain('ожидаемое завершение');
  });
});
