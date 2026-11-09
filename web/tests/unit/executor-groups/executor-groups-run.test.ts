/**
 * `EXEC2-WEB-GROUPS-01` — the run and the queue row of work admitted by a rule or a group: the waiting
 * reason, «плановая модель» before dispatch and «фактическая модель и подключение» after it
 * (ADR-0026 decisions 12 to 15). Written under `R-149d` and not run in EXEC-2; none of it needs
 * PostgreSQL.
 *
 * The rule under test is the one the task states: **no screen claims a model ran before dispatch.**
 * Before it a run on a group has a plan and no connection; the line says «плановая модель», names no
 * connection, and says the connection is chosen when the work is sent. After it the line is built from
 * the binding alone and says «фактическая модель» and the connection. A run that existed before groups
 * (`frozen_at_start`, or no `binding_state`) is worded exactly as it always was.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutorBinding, ExecutorGroupPlan, RunStatus } from '@/shared/api';
import { RUN_QUEUE_REASON_VALUES, queryKeys } from '@/shared/api';
import {
  QUEUE_REASON_LABELS, QueueItemWaiting, RunTable, queueItemWaiting, runExecutorLine, runExecutorSentence,
  runExecutorValue, runQueueReason, runWaitingSentence,
} from '@/entities/audit-run';
import { formatInstant } from '@/shared/lib';
import { RunProgress } from '@/widgets/run-progress';
import { runDialog } from '../run/run-dialog-fixture';

import { PROJECT_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';
import { READY, groupId, groupRevisionId, ruleRevisionId } from './executor-groups-fixtures';

const MODEL = 'модель-основная';
const PLAN: ExecutorGroupPlan = {
  executor_group_id: groupId(1),
  executor_group_revision_id: groupRevisionId(1),
  routing_rule_revision_id: ruleRevisionId(1),
  pin_id: MODEL,
  gateway_model: 'шлюзовая-основная',
  billing: 'metered',
};
const BINDING: ExecutorBinding = {
  connection_id: READY.connection.connection_id,
  connection_revision_id: READY.detail.revisions[0]!.revision_id,
  display_name: 'Основной шлюз',
  pin_id: MODEL,
  gateway_model: 'шлюзовая-основная',
};
const SINCE = '2026-11-03T09:30:00.000Z';
const PLANNED_TAIL = 'подключение будет выбрано при отправке в работу';

/** A run admitted by a rule or a group and not yet dispatched. */
function pending(over: Partial<RunStatus> = {}): RunStatus {
  return runStatus({
    state: 'queued', terminal_at: null, binding_state: 'pending', planned: PLAN,
    wait_reason: 'executor_at_capacity', waiting_since: SINCE, ...over,
  });
}

/** The same run after dispatch bound it. */
function bound(over: Partial<RunStatus> = {}): RunStatus {
  return runStatus({
    state: 'running', terminal_at: null, binding_state: 'bound', planned: PLAN, binding: BINDING,
    executor: { connection_id: BINDING.connection_id, display_name: BINDING.display_name, pin_id: MODEL },
    ...over,
  });
}

/** What a sentence must not do before dispatch: say a model ran, answered or was used. */
const CLAIMS_A_MODEL_RAN = /фактическ|ответил|использова|выполнил|работал|отработал|вызван/i;

describe('before dispatch: the plan', () => {
  const line = runExecutorLine(pending())!;

  it('is a plan with no connection, the reason it waits and since when', () => {
    expect(line).toEqual({
      name: '', model: MODEL, waiting: true, phase: 'planned', queueReason: 'executor_at_capacity', waitingSince: SINCE,
    });
  });

  it('says «плановая модель» and that the connection is chosen when the work is sent', () => {
    expect(runExecutorValue(line)).toBe(`Плановая модель «${MODEL}», ${PLANNED_TAIL}`);
    expect(runExecutorSentence(line)).toBe(`В очереди: исполнитель занят — плановая модель «${MODEL}», ${PLANNED_TAIL}`);
  });

  it('says why it waits, and since when', () => {
    expect(runWaitingSentence(line)).toBe(`В очереди: исполнитель занят. Ждёт с ${formatInstant(SINCE)}.`);
  });

  it('never claims a model ran, answered or was used, and names no connection', () => {
    for (const text of [runExecutorValue(line), runExecutorSentence(line), runWaitingSentence(line) ?? '']) {
      expect(text).not.toMatch(CLAIMS_A_MODEL_RAN);
      expect(text).not.toContain('Исполнитель «');
      expect(text).not.toContain('Основной шлюз');
    }
  });

  it('says every reason in the words of the queue, from the stored wait_reason', () => {
    for (const reason of RUN_QUEUE_REASON_VALUES) {
      const one = runExecutorLine(pending({ wait_reason: reason }))!;
      expect(one.queueReason).toBe(reason);
      expect(runExecutorSentence(one)).toContain(QUEUE_REASON_LABELS[reason]);
      expect(runWaitingSentence(one)).toContain(`${QUEUE_REASON_LABELS[reason]}.`);
    }
  });

  it('says that it waits to be sent when the reading carries no reason, and invents none', () => {
    const quiet = runExecutorLine(pending({ wait_reason: undefined as never, waiting_since: undefined as never }))!;
    expect(quiet.queueReason).toBeUndefined();
    expect(quiet.waitingSince).toBeUndefined();
    expect(runWaitingSentence(quiet)).toBe('Ждёт отправки в работу: подключение группы ещё не выбрано.');
    expect(runExecutorSentence(quiet)).toBe(`Ждёт отправки в работу — плановая модель «${MODEL}», ${PLANNED_TAIL}`);
  });

  it('is still a plan when the run is not in the queue (nothing is waiting), and still has no connection', () => {
    const created = runExecutorLine(pending({ state: 'created' }))!;
    expect(created.waiting).toBe(false);
    expect(created.queueReason).toBeUndefined();
    expect(runWaitingSentence(created)).toBeNull();
    expect(runExecutorSentence(created)).toBe(`Плановая модель «${MODEL}», ${PLANNED_TAIL}`);
  });

  it('says the plan is missing rather than naming a model it was not given', () => {
    const bare = runExecutorLine(pending({ planned: undefined as never }))!;
    expect(bare.model).toBeNull();
    expect(runExecutorValue(bare)).toBe(`Плановая модель не указана, ${PLANNED_TAIL}`);
  });

  it('does not take an executor the reading still carries for the plan’s connection', () => {
    const stale = runExecutorLine(pending({
      executor: { connection_id: BINDING.connection_id, display_name: 'Чужое подключение', pin_id: 'чужая-модель' },
    }))!;
    expect(stale.phase).toBe('planned');
    expect(runExecutorSentence(stale)).not.toContain('Чужое подключение');
    expect(runExecutorSentence(stale)).not.toContain('чужая-модель');
  });
});

describe('after dispatch: the binding', () => {
  const line = runExecutorLine(bound())!;

  it('is the connection and the model dispatch chose', () => {
    expect(line).toEqual({ name: 'Основной шлюз', model: MODEL, waiting: false, phase: 'bound' });
  });

  it('says «фактическая модель» and the connection, and no longer speaks of a plan', () => {
    const expected = `Фактическая модель «${MODEL}», подключение «Основной шлюз»`;
    expect(runExecutorValue(line)).toBe(expected);
    expect(runExecutorSentence(line)).toBe(expected);
    expect(runWaitingSentence(line)).toBeNull();
    expect(expected).not.toContain('лановая');
    expect(expected).not.toContain(PLANNED_TAIL);
  });

  it('reads the binding, not the executor member, which the contract says only names the same connection', () => {
    const odd = runExecutorLine(bound({
      executor: { connection_id: BINDING.connection_id, display_name: 'Другое имя', pin_id: 'другая-модель' },
    }))!;
    expect(odd.name).toBe('Основной шлюз');
    expect(odd.model).toBe(MODEL);
  });

  it('falls back to the executor member only when the binding is absent, and then claims no phase', () => {
    const lost = runExecutorLine(bound({ binding: undefined as never }))!;
    expect(lost.phase).toBeUndefined();
    expect(runExecutorSentence(lost)).toBe(`Исполнитель «Основной шлюз», модель «${MODEL}»`);
  });
});

describe('a run that existed before groups', () => {
  const executor = { connection_id: BINDING.connection_id, display_name: 'Основной шлюз', pin_id: MODEL };

  it('is worded exactly as it always was, with or without frozen_at_start', () => {
    for (const over of [{}, { binding_state: 'frozen_at_start' as const }]) {
      const line = runExecutorLine(runStatus({ executor, ...over }))!;
      expect(line).toEqual({ name: 'Основной шлюз', model: MODEL, waiting: false });
      expect(runExecutorSentence(line)).toBe(`Исполнитель «Основной шлюз», модель «${MODEL}»`);
      expect(runExecutorValue(line)).toBe(`«Основной шлюз», модель «${MODEL}»`);
    }
    const queued = runExecutorLine(runStatus({ state: 'queued', terminal_at: null, executor, binding_state: 'frozen_at_start' }))!;
    expect(runWaitingSentence(queued)).toBe('Ждёт исполнителя «Основной шлюз».');
  });

  it('has no line without an executor, even over a stale plan', () => {
    expect(runExecutorLine(runStatus({ planned: PLAN }))).toBeNull();
    expect(runExecutorLine(runStatus({ binding_state: 'frozen_at_start', binding: BINDING }))).toBeNull();
  });
});

describe('the stored wait_reason', () => {
  it('is read for a queued run, after the derived queue_reason', () => {
    expect(runQueueReason({ state: 'queued', wait_reason: 'needs_reconsent' })).toBe('needs_reconsent');
    expect(runQueueReason({ state: 'queued', queue_reason: 'runner_offline', wait_reason: 'needs_reconsent' })).toBe('runner_offline');
    expect(runQueueReason({ state: 'queued', queue_reason: null, wait_reason: 'executor_at_capacity' })).toBe('executor_at_capacity');
  });

  it('is not read for a run that is not queued, and not when it is a word this screen does not know', () => {
    expect(runQueueReason({ state: 'running', wait_reason: 'needs_reconsent' })).toBeNull();
    expect(runQueueReason({ state: 'queued', wait_reason: 'future_reason' as never })).toBeNull();
    expect(runQueueReason({ state: 'queued' })).toBeNull();
  });
});

describe('the run table row and the run page', () => {
  const row = (run: RunStatus): string =>
    render(createElement(RunTable, { runs: [run], runHref: () => '/run', reviewHref: () => '/review' }));

  function page(run: RunStatus): string {
    const client = newClient();
    client.setQueryData(queryKeys.runs.detail(run.run_id), run);
    return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: run.run_id }));
  }

  it('say the plan before dispatch, with the machine value beside it', () => {
    const markup = row(pending());
    expect(markup).toContain('data-run-binding="planned"');
    expect(markup).toContain('data-run-queue-reason="executor_at_capacity"');
    expect(markup).toContain(`плановая модель «${MODEL}», ${PLANNED_TAIL}`);
    expect(markup).not.toMatch(CLAIMS_A_MODEL_RAN);
    expect(markup).not.toContain('Основной шлюз');
  });

  it('say the binding after dispatch', () => {
    const markup = row(bound());
    expect(markup).toContain('data-run-binding="bound"');
    expect(markup).toContain(`Фактическая модель «${MODEL}», подключение «Основной шлюз»`);
    expect(markup).not.toContain('лановая');
  });

  it('draw nothing new for a run that existed before groups', () => {
    const markup = row(runStatus({ executor: { connection_id: BINDING.connection_id, display_name: 'Основной шлюз', pin_id: MODEL } }));
    expect(markup).not.toContain('data-run-binding');
    expect(markup).toContain(`Исполнитель «Основной шлюз», модель «${MODEL}»`);
  });

  it('put the plan among the facts of «Этапы анализа раздела», and the reason it waits in the live line', () => {
    const markup = page(pending());
    expect(markup).toContain('data-run-executor-waiting');
    expect(markup).toContain('В очереди: исполнитель занят.');
    expect(markup).toContain(`Ждёт с ${formatInstant(SINCE)}.`);
    expect(markup).not.toContain('Основной шлюз');
    const dialog = runDialog(pending());
    expect(dialog).toContain('<dt>Исполнитель</dt>');
    expect(dialog).toMatch(new RegExp(`<dd data-run-executor="true">Плановая модель «${MODEL}», ${PLANNED_TAIL}</dd>`));
    expect(dialog).not.toContain('Основной шлюз');
  });

  it('put the binding among the facts of «Этапы анализа раздела» once dispatch has bound it', () => {
    const run = bound({ state: 'published', terminal_at: '2026-09-10T08:04:00.000Z' });
    const dialog = runDialog(run);
    expect(dialog).toMatch(new RegExp(`<dd data-run-executor="true">Фактическая модель «${MODEL}», подключение «Основной шлюз»</dd>`));
    expect(dialog).not.toContain('Плановая модель');
    const markup = page(run);
    expect(markup).not.toContain('data-run-executor-waiting');
    expect(markup).not.toContain('Плановая модель');
  });
});

describe('a row of the execution queue', () => {
  const TAIL = 'Подключение ещё не выбрано: его выберут при отправке в работу.';

  it('says why a job on a group is not running, and that no connection is chosen yet', () => {
    for (const reason of RUN_QUEUE_REASON_VALUES) {
      const waiting = queueItemWaiting({ state: 'queued', binding_state: 'pending', wait_reason: reason })!;
      expect(waiting).toEqual({
        binding: 'pending', reason, sentence: `${QUEUE_REASON_LABELS[reason]}. ${TAIL}`,
      });
    }
  });

  it('says that it waits to be sent when the reading names no reason, or one this screen does not know', () => {
    for (const item of [
      { state: 'queued', binding_state: 'pending' as const },
      { state: 'queued', binding_state: 'pending' as const, wait_reason: 'future_reason' as never },
    ]) {
      expect(queueItemWaiting(item)).toEqual({ binding: 'pending', reason: null, sentence: `Ждёт отправки в работу. ${TAIL}` });
    }
  });

  it('says that a bound job has its connection, and sends the reader to the run for which one', () => {
    const waiting = queueItemWaiting({ state: 'running', binding_state: 'bound' })!;
    expect(waiting.binding).toBe('bound');
    expect(waiting.sentence).toBe('Подключение и модель выбраны при отправке в работу. Какие именно, показано на странице прогона.');
    expect(waiting.sentence).not.toMatch(/Основной шлюз|модель «/);
  });

  it('says nothing of a job that existed before groups, or of a pending one that is not queued', () => {
    expect(queueItemWaiting({ state: 'queued' })).toBeNull();
    expect(queueItemWaiting({ state: 'queued', binding_state: 'frozen_at_start' })).toBeNull();
    expect(queueItemWaiting({ state: 'cancelled', binding_state: 'pending', wait_reason: 'executor_at_capacity' })).toBeNull();
  });

  it('is drawn with its machine values, and not at all when there is nothing to say', () => {
    const drawn = render(createElement(QueueItemWaiting, {
      item: { state: 'queued', binding_state: 'pending', wait_reason: 'runner_offline' },
    }));
    expect(drawn).toContain('data-queue-binding="pending"');
    expect(drawn).toContain('data-queue-wait-reason="runner_offline"');
    expect(drawn).toContain('В очереди: раннер не в сети.');
    expect(render(createElement(QueueItemWaiting, { item: { state: 'queued' } }))).toBe('');
  });
});
