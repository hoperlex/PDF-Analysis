/**
 * `EXEC2-WEB-CAP-01` — why a queued Run waits (B1 §6, test 13; ADR-0026 decisions 1 and 5).
 *
 * `RunStatus.queue_reason` is derived by the server for a `queued` Run that is waiting for its
 * executor connection: `executor_at_capacity` when every unit of the connection is in use,
 * `runner_offline` when it is a `pull` connection with no runner online. The run list's row and
 * the run page say it in words — «В очереди: исполнитель занят», «В очереди: раннер не в сети» —
 * and keep the sentence they already had when the reading carries no reason, when the Run is not
 * queued, or when the reason is a value this release does not know.
 *
 * Rendered over a seeded cache (`D-53`), so the words a reader sees are the words judged. None of
 * this needs PostgreSQL. Written under `R-149d` and not run in EXEC-2.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunQueueReason, RunState, RunStatus } from '@/shared/api';
import { RUN_QUEUE_REASON_VALUES, RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import {
  QUEUE_REASON_LABELS, RUN_PAGE_LIMIT, RunTable, runExecutorLine, runExecutorSentence, runQueueReason,
  runQueueReasonLabel, runWaitingSentence,
} from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, VERSION_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderScreen, renderWith } from '../screens/harness';
import { runDialog } from './run-dialog-fixture';

const CONNECTION = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const EXECUTOR = { connection_id: CONNECTION, display_name: 'Основной шлюз', pin_id: 'модель-основная' };

const BUSY = 'В очереди: исполнитель занят';
const OFFLINE = 'В очереди: раннер не в сети';

function queued(over: Partial<RunStatus> = {}): RunStatus {
  return runStatus({ state: 'queued', terminal_at: null, executor: EXECUTOR, ...over });
}

function row(run: RunStatus): string {
  return render(createElement(RunTable, { runs: [run], runHref: () => '/run', reviewHref: () => '/review' }));
}

function page(run: RunStatus): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(run.run_id), run);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: run.run_id }));
}

/** The text a reader sees: tags and their attributes removed. */
function visibleText(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
}

describe('the words', () => {
  it('says what the owner named, for each reason', () => {
    expect(QUEUE_REASON_LABELS.executor_at_capacity).toBe(BUSY);
    expect(QUEUE_REASON_LABELS.runner_offline).toBe(OFFLINE);
  });

  it('has a label for every reason the contract has, and none it lacks', () => {
    expect(Object.keys(QUEUE_REASON_LABELS).sort()).toEqual([...RUN_QUEUE_REASON_VALUES].sort());
    expect(new Set(Object.values(QUEUE_REASON_LABELS)).size).toBe(RUN_QUEUE_REASON_VALUES.length);
    for (const label of Object.values(QUEUE_REASON_LABELS)) {
      expect(label).not.toMatch(/[A-Za-z]/);
    }
  });

  it('gives a queued Run the label of its reason', () => {
    expect(runQueueReasonLabel(queued({ queue_reason: 'executor_at_capacity' }))).toBe(BUSY);
    expect(runQueueReasonLabel(queued({ queue_reason: 'runner_offline' }))).toBe(OFFLINE);
  });

  it('gives nothing when the reading has no reason: the label the state already has stays', () => {
    expect(runQueueReasonLabel(queued())).toBeNull();
    expect(runQueueReasonLabel(queued({ queue_reason: null }))).toBeNull();
  });

  it('gives nothing for a Run that is not queued, whatever reason a reading still holds', () => {
    for (const state of RUN_STATE_VALUES as readonly RunState[]) {
      if (state === 'queued') continue;
      for (const reason of RUN_QUEUE_REASON_VALUES as readonly RunQueueReason[]) {
        expect(runQueueReason(runStatus({ state, queue_reason: reason })), `${state} ${reason}`).toBeNull();
        expect(runQueueReasonLabel(runStatus({ state, queue_reason: reason })), `${state} ${reason}`).toBeNull();
      }
    }
  });

  it('gives nothing for a reason it does not know, rather than guessing a label', () => {
    expect(runQueueReasonLabel(queued({ queue_reason: 'something_new' as never }))).toBeNull();
  });
});

describe('the executor line of a run', () => {
  it('carries the reason on a waiting line, and the waiting sentences name it', () => {
    const busy = runExecutorLine(queued({ queue_reason: 'executor_at_capacity' }))!;
    expect(busy.waiting).toBe(true);
    expect(busy.queueReason).toBe('executor_at_capacity');
    expect(runExecutorSentence(busy)).toBe(`${BUSY} — «Основной шлюз», модель «модель-основная»`);
    expect(runWaitingSentence(busy)).toBe(`${BUSY}.`);

    const offline = runExecutorLine(queued({ queue_reason: 'runner_offline' }))!;
    expect(runExecutorSentence(offline)).toBe(`${OFFLINE} — «Основной шлюз», модель «модель-основная»`);
    expect(runWaitingSentence(offline)).toBe(`${OFFLINE}.`);
  });

  it('keeps the sentences it had when the reading carries no reason, word for word', () => {
    for (const run of [queued(), queued({ queue_reason: null })]) {
      const line = runExecutorLine(run)!;
      expect(line).toEqual({ name: 'Основной шлюз', model: 'модель-основная', waiting: true });
      expect('queueReason' in line).toBe(false);
      expect(runExecutorSentence(line)).toBe('Ждёт исполнителя «Основной шлюз», модель «модель-основная»');
      expect(runWaitingSentence(line)).toBe('Ждёт исполнителя «Основной шлюз».');
    }
  });

  it('keeps the executor sentence of a run that is not queued, with no reason on it', () => {
    const line = runExecutorLine(runStatus({ state: 'running', executor: EXECUTOR, queue_reason: 'executor_at_capacity' }))!;
    expect(line.waiting).toBe(false);
    expect('queueReason' in line).toBe(false);
    expect(runExecutorSentence(line)).toBe('Исполнитель «Основной шлюз», модель «модель-основная»');
    expect(runWaitingSentence(line)).toBeNull();
  });

  it('draws no line for a run without an executor, even if a reason came with it', () => {
    expect(runExecutorLine(runStatus({ state: 'queued', terminal_at: null, queue_reason: 'executor_at_capacity' }))).toBeNull();
  });
});

describe('the run table row', () => {
  it('says the executor is busy, and names it, in the place of «Ждёт исполнителя»', () => {
    const markup = row(queued({ queue_reason: 'executor_at_capacity' }));
    expect(markup).toContain(`${BUSY} — «Основной шлюз», модель «модель-основная»`);
    expect(markup).toContain('data-run-queue-reason="executor_at_capacity"');
    expect(markup).not.toContain('Ждёт исполнителя');
    expect(markup).not.toContain(OFFLINE);
  });

  it('says the runner is not online, and names the executor', () => {
    const markup = row(queued({ queue_reason: 'runner_offline' }));
    expect(markup).toContain(`${OFFLINE} — «Основной шлюз», модель «модель-основная»`);
    expect(markup).toContain('data-run-queue-reason="runner_offline"');
    expect(markup).not.toContain(BUSY);
    expect(markup).not.toContain('Ждёт исполнителя');
  });

  it('keeps «Ждёт исполнителя» when the reading carries no reason, and marks none', () => {
    for (const run of [queued(), queued({ queue_reason: null })]) {
      const markup = row(run);
      expect(markup).toContain('Ждёт исполнителя «Основной шлюз», модель «модель-основная»');
      expect(markup).not.toContain('data-run-queue-reason');
      expect(markup).not.toContain('В очереди:');
    }
  });

  it('keeps «Ждёт исполнителя» for a reason it does not know', () => {
    const markup = row(queued({ queue_reason: 'something_new' as never }));
    expect(markup).toContain('Ждёт исполнителя «Основной шлюз»');
    expect(markup).not.toContain('В очереди:');
  });

  it('says nothing of waiting for a run that has left the queue', () => {
    const markup = row(runStatus({ state: 'running', terminal_at: null, executor: EXECUTOR, queue_reason: 'executor_at_capacity' }));
    expect(markup).toContain('Исполнитель «Основной шлюз», модель «модель-основная»');
    expect(markup).not.toContain('В очереди:');
    expect(markup).not.toContain('data-run-queue-reason');
  });

  it('keeps the contract value in the data attribute and never prints it as a word', () => {
    for (const reason of RUN_QUEUE_REASON_VALUES as readonly RunQueueReason[]) {
      const text = visibleText(row(queued({ queue_reason: reason })));
      expect(text).not.toContain(reason);
      expect(text).toContain(QUEUE_REASON_LABELS[reason]);
    }
  });

  it('is what the version’s run list draws for each queued run', () => {
    const client = newClient();
    const otherId = (digit: string) => `${RUN_ID.slice(0, -1)}${digit}`;
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [
        queued({ queue_reason: 'executor_at_capacity' }),
        queued({ run_id: otherId('9'), queue_reason: 'runner_offline', executor: { ...EXECUTOR, display_name: 'Запасной шлюз' } }),
        queued({ run_id: otherId('8') }),
        runStatus({ run_id: otherId('7') }),
      ],
      page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
    expect(markup).toContain(`${BUSY} — «Основной шлюз», модель «модель-основная»`);
    expect(markup).toContain(`${OFFLINE} — «Запасной шлюз», модель «модель-основная»`);
    expect(markup).toContain('Ждёт исполнителя «Основной шлюз», модель «модель-основная»');
    expect(markup.match(/data-run-queue-reason=/g)).toHaveLength(2);
  });
});

describe('the run page', () => {
  it('says the executor is busy in the waiting line, and the dialog names the executor once, as the server of the plan', () => {
    const run = queued({ queue_reason: 'executor_at_capacity' });
    const markup = page(run);
    expect(markup).toMatch(new RegExp(`<span data-run-executor-waiting="true">${BUSY}\\.</span>`));
    expect(markup).not.toContain('Ждёт исполнителя');
    const dialog = runDialog(run, { selected: 'text' });
    expect(dialog).not.toContain('<dt>Исполнитель</dt>');
    expect(dialog).not.toContain('data-run-executor');
    expect(dialog).toContain('<strong title="модель-основная">модель-основная</strong>');
    expect(dialog).toMatch(/data-plan-row="server"[\s\S]*?Основной шлюз/);
  });

  it('says the runner is not online', () => {
    const markup = page(queued({ queue_reason: 'runner_offline' }));
    expect(markup).toMatch(new RegExp(`<span data-run-executor-waiting="true">${OFFLINE}\\.</span>`));
    expect(markup).not.toContain(BUSY);
  });

  it('keeps «Ждёт исполнителя» when the reading carries no reason', () => {
    const markup = page(queued());
    expect(markup).toMatch(/<span data-run-executor-waiting="true">Ждёт исполнителя «Основной шлюз»\.<\/span>/);
    expect(markup).not.toContain('В очереди:');
  });

  it('draws no waiting line once the run has left the queue', () => {
    const markup = page(runStatus({ state: 'running', terminal_at: null, executor: EXECUTOR, queue_reason: 'executor_at_capacity' }));
    expect(markup).not.toContain('data-run-executor-waiting');
    expect(markup).not.toContain('В очереди:');
  });
});
