/**
 * `UIP-S08-03`: the line above a run's «Лог» -- «Сейчас: <этап> · стр. N из M» for an open run, «Прогон завершён: <состояние>» for an
 * ended one -- said from the journal's own events, and under it «Скопировать», «Автообновление» and «Записей на странице: N».
 * Nothing of a model, a server or a heartbeat is in it: the closed projection holds none of them.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry } from '@/shared/api';
import { RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import { RunEvents } from '@/_pages/run/ui/run-events';
import { journalStatus } from '@/entities/execution';
import { STAGE_LABELS, STATE_LABELS } from '@/shared/ui';

import { newClient, renderWith } from '../screens/harness';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

type Payload = Record<string, string | number | boolean | null>;

let second = 0;
function entry(eventType: string, payload: Payload = {}, aggregateType = 'AuditRun'): ExecutionJournalEntry {
  second += 1;
  return {
    event_id: `evt_${String(second).padStart(4, '0')}`,
    run_id: RUN_ID,
    aggregate_id: aggregateType === 'AuditRun' ? RUN_ID : 'att_1',
    aggregate_type: aggregateType,
    event_type: eventType,
    occurred_at: `2026-11-16T10:${String(Math.floor(second / 60)).padStart(2, '0')}:${String(second % 60).padStart(2, '0')}Z`,
    payload,
  };
}

const transition = (to: string) => entry('audit_run.transition', { from_state: 'queued', to_state: to });
const started = (stage: string) => entry('stage.started', { stage_id: stage });
const finished = (stage: string, state = 'succeeded') => entry('stage.finished', { stage_id: stage, state });
const progress = (stage: string, completed: number, total: number) =>
  entry('stage.progress', { stage_id: stage, completed_pages: completed, total_pages: total });

/** The journal as it is read: newest first. */
const newestFirst = (...oldestFirst: ExecutionJournalEntry[]): ExecutionJournalEntry[] => [...oldestFirst].reverse();

const FORBIDDEN = /модел|сервер|heartbeat/i;

describe('an open run: «Сейчас: <этап> · стр. N из M»', () => {
  it('names the stage at work and its newest pages', () => {
    const status = journalStatus(newestFirst(
      entry('audit_run.created', { state: 'queued' }), transition('running'),
      started('source_preparation'), finished('source_preparation'),
      started('page_geometry_extraction'), progress('page_geometry_extraction', 1, 10), progress('page_geometry_extraction', 3, 10),
    ));
    expect(status.kind).toBe('running');
    expect(status.text).toBe(`Сейчас: ${STAGE_LABELS.page_geometry_extraction} · стр. 3 из 10`);
  });

  it('names the stage alone while it has reported no pages', () => {
    const status = journalStatus(newestFirst(transition('running'), started('text_analysis')));
    expect(status.text).toBe(`Сейчас: ${STAGE_LABELS.text_analysis}`);
  });

  it('takes no pages from a stage that has ended, nor from another stage', () => {
    // The preparation read 12 of 12 pages and ended; the next stage has not reported any.
    const status = journalStatus(newestFirst(
      transition('running'), started('source_preparation'), entry('stage.pdf_precheck', { stage_id: 'source_preparation', phase: 'completed', completed_pages: 12, total_pages: 12 }),
      finished('source_preparation'), started('page_geometry_extraction'),
    ));
    expect(status.text).toBe(`Сейчас: ${STAGE_LABELS.page_geometry_extraction}`);
  });

  it('counts the pages of the PDF check as the stage\'s own', () => {
    const status = journalStatus(newestFirst(
      transition('running'), started('source_preparation'),
      entry('stage.pdf_precheck', { stage_id: 'source_preparation', phase: 'checking', completed_pages: 4, total_pages: 12 }),
    ));
    expect(status.text).toBe(`Сейчас: ${STAGE_LABELS.source_preparation} · стр. 4 из 12`);
  });

  it('says «Другой этап» for a stage the contract\'s list does not hold', () => {
    expect(journalStatus(newestFirst(transition('running'), started('unlisted_stage'))).text).toBe('Сейчас: Другой этап');
  });

  it('says the run\'s own state between two stages, and while it waits', () => {
    const between = journalStatus(newestFirst(transition('running'), started('source_preparation'), finished('source_preparation')));
    expect(between.kind).toBe('running');
    expect(between.text).toBe('Сейчас: прогон выполняется');
    expect(journalStatus(newestFirst(entry('audit_run.created', { state: 'queued' }))).text).toBe('Сейчас: прогон в очереди');
    expect(journalStatus(newestFirst(entry('audit_run.created', { state: 'queued' }), transition('validating'))).text).toBe('Сейчас: прогон проверяется');
    // A stage's end with no state of the run on the page: the stage's end says the run is being executed.
    expect(journalStatus([finished('source_preparation')]).text).toBe('Сейчас: прогон выполняется');
  });

  it('does not trust the order it is given', () => {
    const events = newestFirst(transition('running'), started('text_analysis'), progress('text_analysis', 2, 5));
    expect(journalStatus([...events].reverse()).text).toBe(journalStatus(events).text);
    expect(journalStatus([events[1] as ExecutionJournalEntry, events[2] as ExecutionJournalEntry, events[0] as ExecutionJournalEntry]).text)
      .toBe(`Сейчас: ${STAGE_LABELS.text_analysis} · стр. 2 из 5`);
  });

  it('is the run\'s own: the events of a job and an attempt, and an end that failed a stage, are not the run\'s state', () => {
    const status = journalStatus(newestFirst(
      transition('running'), started('text_analysis'),
      entry('job.transition', { to_state: 'failed' }, 'Job'), entry('attempt.transition', { to_state: 'failed' }, 'Attempt'),
    ));
    expect(status.text).toBe(`Сейчас: ${STAGE_LABELS.text_analysis}`);
    // A stage that ended `failed` carries a stage status, not the run's: the run is still open.
    expect(journalStatus(newestFirst(transition('running'), started('text_analysis'), finished('text_analysis', 'failed'))).kind).toBe('running');
  });
});

describe('an ended run: «Прогон завершён: <состояние>»', () => {
  it('says the state the last transition reached, in the run\'s own word', () => {
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) {
      const status = journalStatus(newestFirst(
        transition('running'), started('text_analysis'), finished('text_analysis'), transition(state),
        // The executor's own record that follows the run's end does not reopen it.
        entry('job.transition', { to_state: 'succeeded' }, 'Job'),
      ));
      expect(status.kind, state).toBe('ended');
      expect(status.text, state).toBe(`Прогон завершён: ${STATE_LABELS[state]}`);
    }
    expect(journalStatus(newestFirst(transition('published'))).text).toBe('Прогон завершён: опубликован');
  });

  it('says it from the newest transition, though a stage is the newest of the stage events', () => {
    const status = journalStatus(newestFirst(transition('running'), started('text_analysis'), progress('text_analysis', 1, 2), transition('failed')));
    expect(status.text).toBe('Прогон завершён: отказ');
  });

  it('knows each state of the run: the open ones read «Сейчас», the ended ones «Прогон завершён»', () => {
    for (const state of RUN_STATE_VALUES) {
      const text = journalStatus([transition(state)]).text;
      const ended = ['published', 'partial', 'failed', 'cancelled'].includes(state);
      expect(text, state).toBe(ended ? `Прогон завершён: ${STATE_LABELS[state]}` : `Сейчас: прогон ${STATE_LABELS[state]}`);
    }
  });
});

describe('an empty journal', () => {
  it('has no line to say', () => {
    expect(journalStatus([])).toEqual({ kind: 'empty', text: null });
  });

  it('has none either when it holds nothing of the run\'s own state or stages: no guess', () => {
    const status = journalStatus([entry('job.created', {}, 'Job'), entry('attempt.transition', { to_state: 'running' }, 'Attempt')]);
    expect(status).toEqual({ kind: 'unknown', text: null });
    expect(journalStatus([entry('audit_run.executor_chosen', { connection_id: 'exc_1' })]).text).toBeNull();
  });
});

describe('no model, no server, no heartbeat', () => {
  it('is built from the closed projection: a field of the payload that says them is not read', () => {
    const noisy = {
      model: 'claude-opus-5-5', model_name: 'Opus 5.5', host: 'adm1.hlab.kz', server: 'kzoct', executor: 'exc_1', heartbeat_at: '2026-11-16T10:00:00Z',
      message: 'Модель ищет замечания', cost_usd: 0.3,
    };
    const lines = [
      journalStatus(newestFirst(transition('running'), entry('stage.progress', { stage_id: 'text_analysis', completed_pages: 3, total_pages: 10, ...noisy }))).text,
      journalStatus(newestFirst(entry('audit_run.transition', { to_state: 'published', ...noisy }))).text,
      journalStatus(newestFirst(entry('audit_run.transition', { to_state: 'running', ...noisy }))).text,
    ];
    for (const line of lines) {
      expect(line).not.toBeNull();
      expect(line).not.toMatch(FORBIDDEN);
      expect(line).not.toMatch(/Opus|adm1|kzoct|exc_1|0\.3/);
    }
  });
});

function seeded(items: ExecutionJournalEntry[], roles: string[] | undefined = ['expert']) {
  const client = newClient();
  if (roles !== undefined) client.setQueryData(queryKeys.account.me(), { roles });
  client.setQueryData(queryKeys.execution.journal(RUN_ID as never), { items, page: { next_cursor: null } });
  return client;
}

function drawn(items: ExecutionJournalEntry[]): string {
  return renderWith(seeded(items), createElement(RunEvents, { runId: RUN_ID }));
}

describe('the «Лог» of a run, drawn', () => {
  const open = newestFirst(
    entry('audit_run.created', { state: 'queued' }), transition('running'),
    started('source_preparation'), finished('source_preparation'),
    started('block_analysis'), progress('block_analysis', 2, 5),
    entry('job.transition', { to_state: 'running' }, 'Job'),
  );

  it('says «Сейчас: …» for an open run, above «Скопировать», «Автообновление» and «Записей на странице: N», above the groups', () => {
    const markup = drawn(open);
    expect(markup).toContain(`data-journal-status="running"`);
    expect(markup).toContain(`<p data-journal-status="running"><strong>Сейчас: ${STAGE_LABELS.block_analysis} · стр. 2 из 5</strong></p>`);
    const at = (needle: string) => markup.indexOf(needle);
    for (const needle of ['data-journal-status', 'data-journal-controls', 'data-journal-groups']) expect(at(needle), needle).toBeGreaterThan(-1);
    expect(at('data-journal-status')).toBeLessThan(at('data-journal-controls'));
    expect(at('data-journal-controls')).toBeLessThan(at('data-journal-groups'));
    expect(markup).toContain('Скопировать');
    expect(markup).toContain('Автообновление');
    expect(markup).toContain(`Записей на странице: ${open.length}`);
    // The page says the run once, in its heading, not on every line.
    expect(markup).not.toContain('>Прогон</th>');
  });

  it('says «Прогон завершён: …» for an ended run', () => {
    const markup = drawn(newestFirst(transition('running'), started('text_analysis'), finished('text_analysis'), transition('published')));
    expect(markup).toContain('<p data-journal-status="ended"><strong>Прогон завершён: опубликован</strong></p>');
    expect(markup).toContain('Записей на странице: 4');
    expect(markup).not.toContain('data-journal-status="running"');
  });

  it('says no line for an empty journal, and keeps the empty state and the controls', () => {
    const markup = drawn([]);
    expect(markup).not.toContain('data-journal-status');
    expect(markup).toContain('Записей пока нет');
    expect(markup).toContain('Записей на странице: 0');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*data-journal-copy/);
  });

  it('says no model, no server and no heartbeat anywhere in it', () => {
    for (const markup of [drawn(open), drawn(newestFirst(transition('published'))), drawn([])]) {
      expect(markup).not.toMatch(FORBIDDEN);
    }
  });

  it('keeps the way to the whole journal, and is not drawn for a read-only account', () => {
    expect(drawn(open)).toContain('Весь журнал прогона');
    const viewer = renderWith(seeded(open, ['viewer']), createElement(RunEvents, { runId: RUN_ID }));
    expect(viewer).toBe('');
  });
});
