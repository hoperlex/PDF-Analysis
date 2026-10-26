/**
 * `EXEC-PAR-WEB-01`: the executor of a run, on the run list and the run page.
 *
 * The run list's row and the run page name the executor a run froze, with its pinned model; a run
 * in the queue says which executor it is waiting for; a run with none draws nothing and invents
 * nothing. Rendered over a seeded cache (`D-53`), so the words a reader sees are the words judged.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import {
  RUN_PAGE_LIMIT, RunRow, runExecutorLine, runExecutorSentence, runExecutorValue, runWaitingSentence,
} from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, VERSION_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderScreen, renderWith } from '../screens/harness';

const CONNECTION = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const EXECUTOR = { connection_id: CONNECTION, display_name: 'Основной шлюз', pin_id: 'модель-основная' };

function row(over: Partial<RunStatus>): string {
  return render(createElement(RunRow, { run: runStatus(over), href: '/run' }));
}

function page(over: Partial<RunStatus>): string {
  const status = runStatus(over);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

describe('the words', () => {
  it('names the executor and its model', () => {
    const line = runExecutorLine(runStatus({ executor: EXECUTOR }))!;
    expect(line).toEqual({ name: 'Основной шлюз', model: 'модель-основная', waiting: false });
    expect(runExecutorSentence(line)).toBe('Исполнитель «Основной шлюз», модель «модель-основная»');
    expect(runExecutorValue(line)).toBe('«Основной шлюз», модель «модель-основная»');
    expect(runWaitingSentence(line)).toBeNull();
  });

  it('says a run in the queue waits for its executor, and no other state does', () => {
    const queued = runExecutorLine(runStatus({ state: 'queued', executor: EXECUTOR }))!;
    expect(queued.waiting).toBe(true);
    expect(runWaitingSentence(queued)).toBe('Ждёт исполнителя «Основной шлюз».');
    expect(runExecutorSentence(queued)).toBe('Ждёт исполнителя «Основной шлюз», модель «модель-основная»');
    for (const state of ['created', 'running', 'validating', 'published', 'partial', 'failed', 'cancelled'] as const) {
      const line = runExecutorLine(runStatus({ state, executor: EXECUTOR }))!;
      expect(line.waiting, state).toBe(false);
      expect(runWaitingSentence(line), state).toBeNull();
      expect(runExecutorSentence(line), state).not.toContain('Ждёт');
    }
  });

  it('invents nothing for a run without an executor', () => {
    expect(runExecutorLine(runStatus({}))).toBeNull();
    expect(runExecutorLine(runStatus({ executor: null }))).toBeNull();
    expect(runExecutorLine(runStatus({ state: 'queued' }))).toBeNull();
    expect(runExecutorLine(runStatus({ executor: { ...EXECUTOR, display_name: '' } }))).toBeNull();
    expect(runExecutorLine(runStatus({ executor: { ...EXECUTOR, display_name: '   ' } }))).toBeNull();
  });

  it('leaves out a model it was not given rather than printing a blank one', () => {
    const line = runExecutorLine(runStatus({ executor: { ...EXECUTOR, pin_id: '' } }))!;
    expect(line.model).toBeNull();
    expect(runExecutorSentence(line)).toBe('Исполнитель «Основной шлюз»');
  });
});

describe('the run list row', () => {
  it('names the executor and the pinned model', () => {
    const markup = row({ executor: EXECUTOR });
    expect(markup).toContain('data-run-executor');
    expect(markup).toContain('Исполнитель «Основной шлюз», модель «модель-основная»');
  });

  it('says a run in the queue is waiting for the executor', () => {
    const markup = row({ state: 'queued', terminal_at: null, executor: EXECUTOR });
    expect(markup).toContain('Ждёт исполнителя «Основной шлюз»');
    expect(markup).not.toContain('Исполнитель «Основной шлюз»');
  });

  it('draws nothing for a run with no executor: no line, no placeholder', () => {
    for (const markup of [row({}), row({ executor: null }), row({ state: 'queued', terminal_at: null })]) {
      expect(markup).not.toContain('data-run-executor');
      expect(markup).not.toContain('Исполнитель');
      expect(markup).not.toContain('Ждёт');
      expect(markup).not.toContain('не указан');
    }
  });

  it('does not show a connection id, an address or a key', () => {
    const markup = row({ executor: EXECUTOR });
    expect(markup).not.toContain(CONNECTION);
  });

  it('is what the version’s run list draws for each run', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [runStatus({ executor: EXECUTOR }), runStatus({ run_id: `${RUN_ID.slice(0, -1)}9`, state: 'queued', terminal_at: null, executor: { ...EXECUTOR, display_name: 'Запасной шлюз' } }), runStatus({ run_id: `${RUN_ID.slice(0, -1)}8` })],
      page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
    expect(markup).toContain('Исполнитель «Основной шлюз», модель «модель-основная»');
    expect(markup).toContain('Ждёт исполнителя «Запасной шлюз», модель «модель-основная»');
    expect(markup.match(/data-run-executor/g)).toHaveLength(2);
  });
});

describe('the run page', () => {
  it('names the executor among the run’s facts', () => {
    const markup = page({ executor: EXECUTOR });
    expect(markup).toContain('<dt>Исполнитель</dt>');
    expect(markup).toMatch(/<dd data-run-executor="true">«Основной шлюз», модель «модель-основная»<\/dd>/);
    expect(markup).not.toContain('data-run-executor-waiting');
  });

  it('says a run in the queue is waiting for it', () => {
    const markup = page({ state: 'queued', terminal_at: null, executor: EXECUTOR });
    expect(markup).toMatch(/<p data-run-executor-waiting="true">Ждёт исполнителя «Основной шлюз»\.<\/p>/);
    expect(markup).toContain('<dt>Исполнитель</dt>');
  });

  it('draws no row, no waiting line and no placeholder for a run without an executor', () => {
    for (const over of [{}, { executor: null }, { state: 'queued' as const, terminal_at: null }]) {
      const markup = page(over);
      expect(markup).not.toContain('<dt>Исполнитель</dt>');
      expect(markup).not.toContain('data-run-executor');
      expect(markup).not.toContain('Ждёт исполнителя');
    }
  });
});
