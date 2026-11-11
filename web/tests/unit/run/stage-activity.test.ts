/**
 * `RUN-STAGE-PROGRESS-01`: a code stage at work reads «идёт», with its pages, not «не начинался».
 *
 * The owner's run of 2026-11-11: «Подготовка источника» ran 15 min, then «Извлечение геометрии страниц и блоков» read the
 * whole document again while its row said «не начинался», and the preparation's page count was shown only on the run page.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry, RunStatus } from '@/shared/api';
import { StageTable, chipPagesText, stageActivity, stageActivityText, stageRows } from '@/entities/audit-run';

import { runDialog } from './run-dialog-fixture';
import { RUN_ID, runStatus } from '../review/fixtures';

let sequence = 0;
function event(
  eventType: string,
  second: number,
  payload: ExecutionJournalEntry['payload'],
  runId: string = RUN_ID,
): ExecutionJournalEntry {
  sequence += 1;
  return {
    event_id: `evt_${String(sequence).padStart(4, '0')}`,
    event_type: eventType,
    aggregate_type: 'AuditRun',
    aggregate_id: runId,
    run_id: runId,
    occurred_at: `2026-11-11T12:${String(Math.floor(second / 60)).padStart(2, '0')}:${String(second % 60).padStart(2, '0')}Z`,
    payload,
  };
}

const GEOMETRY = 'page_geometry_extraction';
const SOURCE = 'source_preparation';

describe('the stages the journal says are under way', () => {
  it('names a stage whose newest event is its progress, with its pages and, while on the page, its start', () => {
    const activity = stageActivity([
      event('stage.started', 10, { stage_id: SOURCE }),
      event('stage.pdf_precheck', 11, { stage_id: SOURCE, phase: 'completed', completed_pages: 10, total_pages: 10 }),
      event('stage.finished', 20, { stage_id: SOURCE }),
      event('stage.started', 21, { stage_id: GEOMETRY }),
      event('stage.progress', 22, { stage_id: GEOMETRY, completed_pages: 0, total_pages: 10 }),
      event('stage.progress', 30, { stage_id: GEOMETRY, completed_pages: 3, total_pages: 10 }),
    ], RUN_ID);
    expect([...activity.keys()]).toEqual([GEOMETRY]);
    expect(activity.get(GEOMETRY)).toEqual({ startedAt: '2026-11-11T12:00:21Z', completed: 3, total: 10 });
    expect(stageActivityText(activity.get(GEOMETRY)!)).toBe('идёт · 3 из 10 стр.');
  });

  it('reads the preparation from its PDF check, and a start already off the page as unknown', () => {
    const activity = stageActivity([
      event('stage.pdf_precheck', 50, { stage_id: SOURCE, phase: 'checking', completed_pages: 120, total_pages: 500 }),
    ], RUN_ID);
    expect(activity.get(SOURCE)).toEqual({ startedAt: null, completed: 120, total: 500 });
    expect(chipPagesText(activity, [SOURCE, GEOMETRY, 'document_context_build'])).toBe('120/500 стр.');
  });

  it('takes the current start, not an earlier Attempt end that is older', () => {
    const activity = stageActivity([
      event('stage.started', 1, { stage_id: GEOMETRY }),
      event('stage.finished', 2, { stage_id: GEOMETRY }),
      event('stage.started', 5, { stage_id: GEOMETRY }),
    ], RUN_ID);
    expect(activity.get(GEOMETRY)).toEqual({ startedAt: '2026-11-11T12:00:05Z', completed: null, total: null });
    expect(stageActivityText(activity.get(GEOMETRY)!)).toBe('идёт');
  });

  it.each([[-1, 10], [11, 10], [1.5, 10], [1, 0], ['3', 10]])('shows no pages for impossible counts %s/%s', (done, total) => {
    const activity = stageActivity([event('stage.progress', 3, { stage_id: GEOMETRY, completed_pages: done, total_pages: total })], RUN_ID);
    expect(activity.get(GEOMETRY)).toEqual({ startedAt: null, completed: null, total: null });
  });

  it('borrows nothing from another run', () => {
    expect(stageActivity([event('stage.started', 1, { stage_id: GEOMETRY }, 'run_other')], RUN_ID).size).toBe(0);
  });
});

describe('the stage table', () => {
  const running: RunStatus = runStatus({
    state: 'running',
    terminal_at: null,
    published_finding_count: 0,
    stages: [{ stage_id: SOURCE, status: 'succeeded', started_at: '2026-11-11T12:15:38Z', finished_at: '2026-11-11T12:30:59Z' }],
  } as Partial<RunStatus>);
  const activity = stageActivity([
    event('stage.finished', 59, { stage_id: SOURCE }),
    event('stage.started', 60, { stage_id: GEOMETRY }),
    event('stage.progress', 90, { stage_id: GEOMETRY, completed_pages: 3, total_pages: 10 }),
  ], RUN_ID);

  it('says «идёт» and the pages for the stage at work, and «не начинался» for the next', () => {
    const markup = renderToStaticMarkup(createElement(StageTable, { rows: stageRows(running), activity }));
    expect(markup).toContain('data-stage-status="running"');
    expect(markup).toContain('идёт · 3 из 10 стр.');
    expect(markup.match(/не начинался/g)?.length).toBe(2);  // document_context_build and text_analysis
  });

  it('keeps a stage that has its result as the result says', () => {
    const stale = stageActivity([event('stage.started', 1, { stage_id: SOURCE })], RUN_ID);
    const markup = renderToStaticMarkup(createElement(StageTable, { rows: stageRows(running), activity: stale }));
    expect(markup).not.toContain('data-stage-status="running"');
  });

  it('draws as before without the journal', () => {
    const markup = renderToStaticMarkup(createElement(StageTable, { rows: stageRows(running) }));
    expect(markup).not.toContain('идёт');
  });

  it('puts the pages on the chip of «Этапы анализа раздела» while it is at work', () => {
    const dialog = runDialog(running, { activity });
    expect(dialog).toContain('3/10 стр.');
    expect(dialog).toContain('идёт · 3 из 10 стр.');
  });
});
