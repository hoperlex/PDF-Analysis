/**
 * `EXEC2-FOLLOWUP-01` item 2 (ADR-0026 decisions 12 to 16): the executor of a comparison AI job, on the screens that show a job.
 *
 * A job admitted by a rule or a group carries `binding_state`, `planned`, `binding`, `wait_reason` and `waiting_since`. Before its
 * first call to the model the screens say the planned group's model and that the connection is chosen at that call; after it, the
 * connection and the model the job is actually on; while it waits for an executor, why and since when — and for a wait for a runner,
 * what is wrong with the group (`executor-groups-wait.test.ts` holds the sentences). A job that existed before groups is drawn
 * exactly as it always was.
 *
 * The rule under test is the one `EXEC2-WEB-GROUPS-01` set for a Run: **no screen claims a model ran before the first call.** Before
 * it a job has a plan and no connection; the line says «плановая модель», names no connection and says nothing was called.
 *
 * Written under `R-149d` and not run in EXEC-2; none of it needs PostgreSQL.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ComparisonAiJob, ExecutorBinding, ExecutorGroupCapacity, ExecutorGroupPlan } from '@/shared/api';
import { ApiError, RUN_QUEUE_REASON_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { OFFLINE_WAIT_END_SENTENCE, PREVIOUS_REVISION_NOTE, executorGroupCapacityKey } from '@/entities/executor-group';
import type { AiStepFacts } from '@/entities/version-series';
import {
  GROUP_RATES_STALE_SENTENCE,
  GROUP_ROUTE_LINE,
  JOB_PLANNED_TAIL,
  JOB_UNBOUND_TAIL,
  EstimatePanel,
  JOB_WAIT_LABELS,
  JobExecutor,
  aiStepCell,
  comparisonFailure,
  estimateLines,
  jobExecutorHint,
  jobExecutorLine,
  jobExecutorSentence,
  jobWaitSentence,
} from '@/entities/version-series';
import { AiChangesBlockView } from '@/widgets/version-series';

import { newClient, renderWith } from '../screens/harness';
import { connectionId, revisionId } from '../workers/executor-fixtures';
import { groupId, groupRevisionId, ruleRevisionId } from '../executor-groups/executor-groups-fixtures';
import { estimate, job, sheetChanges } from './ai-fixtures';
import { series } from './fixtures';

const MODEL = 'модель-основная';
const SINCE = '2026-11-03T09:30:00.000Z';
const GROUP = groupId(1);
const PLAN: ExecutorGroupPlan = {
  executor_group_id: GROUP,
  executor_group_revision_id: groupRevisionId(1),
  routing_rule_revision_id: ruleRevisionId(1),
  pin_id: MODEL,
  gateway_model: 'шлюзовая-основная',
  billing: 'metered',
};
const BINDING: ExecutorBinding = {
  connection_id: connectionId(1),
  connection_revision_id: revisionId(1),
  display_name: 'Основной шлюз',
  pin_id: MODEL,
  gateway_model: 'шлюзовая-основная',
};
const PLANNED = `Плановая модель «${MODEL}», подключение будет выбрано при первом обращении к модели`;
const BOUND = `Фактическая модель «${MODEL}», подключение «Основной шлюз»`;
/** What a sentence must not do before the first call: say a model ran, answered or was used. */
const CLAIMS_A_MODEL_RAN = /фактическ|ответил|использова|выполнил|работал|отработал|вызван/i;
const noop = (): void => undefined;

/** A job admitted by a rule or a group and not yet bound: it waits for its first call. */
function pending(over: Partial<ComparisonAiJob> = {}): ComparisonAiJob {
  return job({
    state: 'running', binding_state: 'pending', planned: PLAN, wait_reason: 'executor_at_capacity', waiting_since: SINCE, ...over,
  });
}

/** The same job after its first call bound it. */
function bound(over: Partial<ComparisonAiJob> = {}): ComparisonAiJob {
  return job({ state: 'running', binding_state: 'bound', planned: PLAN, binding: BINDING, ...over });
}

describe('before the first call: the plan', () => {
  const line = jobExecutorLine(pending())!;

  it('is a plan with no connection, the reason it waits, since when, and the group', () => {
    expect(line).toEqual({
      phase: 'planned', name: '', model: MODEL, counting: true, groupId: GROUP, groupRevisionId: groupRevisionId(1),
      waitReason: 'executor_at_capacity', waitingSince: SINCE,
    });
  });

  it('says «плановая модель» and that the connection is chosen at the first call', () => {
    expect(jobExecutorSentence(line)).toBe(PLANNED);
    expect(JOB_PLANNED_TAIL).toBe('подключение будет выбрано при первом обращении к модели');
  });

  it('says why it waits and since when, in the words of a job, for every reason', () => {
    expect(jobWaitSentence(line)).toBe(`Ждёт исполнителя: все места заняты. Ждёт с ${formatInstant(SINCE)}.`);
    for (const reason of RUN_QUEUE_REASON_VALUES) {
      const one = jobExecutorLine(pending({ wait_reason: reason }))!;
      expect(one.waitReason).toBe(reason);
      expect(jobWaitSentence(one)).toBe(`${JOB_WAIT_LABELS[reason]}. Ждёт с ${formatInstant(SINCE)}.`);
    }
  });

  it('never claims a model ran, answered or was used, and names no connection', () => {
    for (const text of [jobExecutorSentence(line), jobWaitSentence(line) ?? '', jobExecutorHint(pending()) ?? '']) {
      expect(text).not.toMatch(CLAIMS_A_MODEL_RAN);
      expect(text).not.toContain('Основной шлюз');
    }
  });

  it('says nothing of a wait when the reading carries no reason, and invents none', () => {
    const quiet = jobExecutorLine(pending({ wait_reason: undefined as never, waiting_since: undefined as never }))!;
    expect(quiet.waitReason).toBeUndefined();
    expect(quiet.waitingSince).toBeUndefined();
    expect(jobWaitSentence(quiet)).toBeNull();
    expect(jobExecutorSentence(quiet)).toBe(PLANNED);
  });

  it('does not read a reason it has no word for', () => {
    expect(jobExecutorLine(pending({ wait_reason: 'future_reason' as never }))!.waitReason).toBeUndefined();
  });

  it('waits while queued, running or paused (a pause keeps its wait), and counts down to an end only while it is queued or running', () => {
    for (const state of ['queued', 'running', 'paused'] as const) {
      const one = jobExecutorLine(pending({ state }))!;
      expect(one.phase, state).toBe('planned');
      expect(one.waitReason, state).toBe('executor_at_capacity');
      expect(jobWaitSentence(one), state).not.toBeNull();
      expect(one.counting, state).toBe(state !== 'paused');
    }
  });

  it('says the plan is missing rather than naming a model it was not given', () => {
    const bare = jobExecutorLine(pending({ planned: undefined as never }))!;
    expect(bare.model).toBeNull();
    expect(bare.groupId).toBeUndefined();
    expect(jobExecutorSentence(bare)).toBe('Плановая модель не указана, подключение будет выбрано при первом обращении к модели');
  });

  it('does not take a binding the reading still carries for the plan’s connection', () => {
    const stale = jobExecutorLine(pending({ binding: BINDING }))!;
    expect(stale.phase).toBe('planned');
    expect(jobExecutorSentence(stale)).not.toContain('Основной шлюз');
  });
});

describe('a job that ended without ever being given a connection (L1)', () => {
  it.each(['completed', 'failed', 'cancelled'] as const)('is the plan in the past tense when it is %s, never the future of «будет выбрано»', (state) => {
    const line = jobExecutorLine(pending({ state }))!;
    expect(line).toEqual({ phase: 'unbound', name: '', model: MODEL });
    const sentence = jobExecutorSentence(line);
    expect(sentence).toBe(`Плановая модель «${MODEL}», подключение так и не было выбрано`);
    expect(JOB_UNBOUND_TAIL).toBe('подключение так и не было выбрано');
    expect(sentence).not.toContain('будет выбрано');
    expect(jobWaitSentence(line)).toBeNull();
    expect(jobExecutorHint(pending({ state }))).toBe(`${sentence}.`);
    expect(sentence).not.toMatch(CLAIMS_A_MODEL_RAN);
  });

  it('is drawn with its machine value, and without a wait or a promise', () => {
    const markup = renderToStaticMarkup(createElement(JobExecutor, { job: pending({ state: 'failed' }) }));
    expect(markup).toContain('data-job-binding="unbound"');
    expect(markup).not.toContain('data-job-wait-reason');
    expect(markup).not.toContain('Ждёт исполнителя');
    expect(markup).not.toContain('будет выбрано');
  });
});

describe('after the first call: the binding', () => {
  const line = jobExecutorLine(bound())!;

  it('is the connection and the model the job is on, with no wait', () => {
    expect(line).toEqual({ phase: 'bound', name: 'Основной шлюз', model: MODEL });
    expect(jobWaitSentence(line)).toBeNull();
  });

  it('says «фактическая модель» and the connection, and no longer speaks of a plan', () => {
    expect(jobExecutorSentence(line)).toBe(BOUND);
    expect(BOUND).not.toContain('лановая');
    expect(BOUND).not.toContain('при первом обращении');
  });

  it('is the same line for a job that has ended: the connection it was on', () => {
    for (const state of ['completed', 'failed', 'cancelled'] as const) {
      expect(jobExecutorSentence(jobExecutorLine(bound({ state }))!)).toBe(BOUND);
    }
  });

  it('is nothing without a binding: the reading is not trusted to name a connection', () => {
    expect(jobExecutorLine(bound({ binding: undefined as never }))).toBeNull();
  });
});

describe('a job that existed before groups', () => {
  it('has no line, with or without frozen_at_start, and even over a stale plan or binding', () => {
    for (const over of [{}, { binding_state: 'frozen_at_start' as const }, { planned: PLAN }, { binding: BINDING }]) {
      const one = job(over);
      expect(jobExecutorLine(one)).toBeNull();
      expect(jobExecutorHint(one)).toBeNull();
    }
  });

  it('is drawn with nothing new', () => {
    expect(renderToStaticMarkup(createElement(JobExecutor, { job: job() }))).toBe('');
  });
});

describe('the screens that show a job', () => {
  const block = (changesJob: ComparisonAiJob, client = newClient()): string =>
    renderWith(client, createElement(AiChangesBlockView, {
      changes: sheetChanges({ job: changesJob }), series: series(), names: new Map(), mayAct: true, busy: false, failure: null,
      folds: new Set<string>(), review: new Map(), onFold: noop, onAct: noop, onOpenTransition: noop, onOpenReviewSheet: noop, dialog: null,
    }));

  it('say the plan before the first call, with the machine values beside it, and why it waits', () => {
    const markup = block(pending());
    expect(markup).toContain('data-job-executor');
    expect(markup).toContain('data-job-binding="planned"');
    expect(markup).toContain('data-job-wait-reason="executor_at_capacity"');
    expect(markup).toContain(PLANNED);
    expect(markup).toContain(`Ждёт исполнителя: все места заняты. Ждёт с ${formatInstant(SINCE)}.`);
    expect(markup).not.toContain('Основной шлюз');
    // the words of the executor's own part of the block, not the block's other texts
    expect(/<div[^>]*data-job-executor[\s\S]*?<\/div>/.exec(markup)?.[0] ?? '').not.toMatch(CLAIMS_A_MODEL_RAN);
  });

  it('say the connection and the model after the first call', () => {
    const markup = block(bound());
    expect(markup).toContain('data-job-binding="bound"');
    expect(markup).toContain(BOUND);
    expect(markup).not.toContain('data-job-wait-reason');
    expect(markup).not.toContain('Плановая модель');
  });

  it('draw nothing new for a job that existed before groups', () => {
    expect(block(job())).not.toContain('data-job-executor');
  });

  const capacityOf = (issue: 'connection_archived' | 'runner_offline', revision = groupRevisionId(1)): ExecutorGroupCapacity => ({
    group_id: GROUP, group_revision_id: revision, capacity: 0, used: 0, waiting: 1,
    members: [{ connection_id: connectionId(1), snapshot_revision_id: revisionId(1), eligible: false, ineligible_reason: issue }],
  });

  it('say what is wrong with the group of a job that waits for a runner, and that the wait ends', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacityOf('connection_archived'));
    const markup = block(pending({ wait_reason: 'runner_offline' }), client);
    expect(markup).toContain('Ждёт исполнителя: раннер не в сети.');
    expect(markup).toContain('data-wait-causes="connection_archived"');
    expect(markup).toContain('Подключение группы не может принять работу: подключение в архиве.');
    expect(markup).toContain(OFFLINE_WAIT_END_SENTENCE);
  });

  it('say that the job was accepted on a previous revision when the group has a newer one (M4)', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacityOf('runner_offline', groupRevisionId(2)));
    const markup = block(pending({ wait_reason: 'runner_offline' }), client);
    expect(markup).toContain(`${PREVIOUS_REVISION_NOTE} Подключение группы не может принять работу: агент офлайн.`);
    expect(markup).not.toContain('не обслужит');
  });

  it('do not promise that the wait ends for a job that is paused (L2)', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacityOf('runner_offline'));
    const markup = block(pending({ wait_reason: 'runner_offline', state: 'paused', pause_reason: 'quota' }), client);
    expect(markup).toContain('Подключение группы не может принять работу: агент офлайн.');
    expect(markup).not.toContain('по истечении лимита ожидания');
  });

  it('read no capacity for any other wait', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacityOf('runner_offline'));
    expect(block(pending({ wait_reason: 'needs_reconsent', state: 'paused' }), client)).not.toContain('data-wait-detail');
  });
});

describe('the cell of a step', () => {
  const facts = (one: ComparisonAiJob): AiStepFacts => ({
    step: 'ai_pairs', overviewState: 'not_applicable', versions: 3, matrixReady: true, seriesKnown: true, job: one,
    summaryReady: false, aiChangesBusy: false,
  });

  it('carries the executor and the reason it waits in its hint', () => {
    const title = aiStepCell(facts(pending())).view.title;
    expect(title).toContain(`${PLANNED}.`);
    expect(title).toContain('Ждёт исполнителя: все места заняты.');
    expect(aiStepCell(facts(bound())).view.title).toContain(`${BOUND}.`);
  });

  it('adds nothing for a job that existed before groups', () => {
    expect(aiStepCell(facts(job())).view.title).not.toContain('модель');
  });

  it('says in the past tense that an ended job never got a connection', () => {
    const title = aiStepCell(facts(pending({ state: 'failed' }))).view.title;
    expect(title).toContain(`Плановая модель «${MODEL}», подключение так и не было выбрано.`);
    expect(title).not.toContain('будет выбрано');
  });
});

describe('a group whose rates are stale (M2)', () => {
  const stale = (reason = 'cost_estimate_binding_changed'): ApiError => new ApiError(
    422,
    {
      contract_version: '1.42.0', error_code: 'analysis_input_invalid', message: 'A caller-safe sentence in English.',
      correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: false,
      details: { stage_id: 'comparison_pair_check', reason },
    },
    '0f0e9d8c-7b6a-4948-b726-150413021100',
  );

  it('is refused where the estimate is made, and said in Russian: «тарифы группы устарели — пересоберите группу»', () => {
    const failure = comparisonFailure(stale());
    expect(failure.detail).toBe(GROUP_RATES_STALE_SENTENCE);
    expect(GROUP_RATES_STALE_SENTENCE).toContain('тарифы группы устарели — пересоберите группу');
    expect(failure.moduleUnavailable).toBe(false);
    expect(failure.estimateStale).toBe(false);
  });

  it('is told only by the registered reason: another reason of the same code keeps the code’s own sentence', () => {
    expect(comparisonFailure(stale('cost_text_count_unavailable')).detail).not.toBe(GROUP_RATES_STALE_SENTENCE);
  });

  it('is what the estimate panel shows in place of an estimate the reader could not consent to', () => {
    const markup = renderToStaticMarkup(createElement(EstimatePanel, {
      title: 'Запуск', consentKind: 'pair_check', confirmLabel: 'Проверить', estimate: undefined, loading: false,
      failure: comparisonFailure(stale()), agreedDigest: null, busy: false, onAgree: noop, onConfirm: noop, onCancel: noop,
    }));
    expect(markup).toContain('тарифы группы устарели — пересоберите группу');
  });
});

describe('the estimate', () => {
  it('says that the connection is chosen at the first call when the route names a group and no connection', () => {
    const grouped = estimate({
      route: { executor_group_id: GROUP, executor_group_revision_id: groupRevisionId(1), pinned_model: MODEL, billing: 'metered', provider_mode: 'live' },
    });
    const lines = estimateLines(grouped);
    expect(lines.map((line) => line.key)).toContain('executor');
    expect(lines.find((line) => line.key === 'executor')?.text).toBe(GROUP_ROUTE_LINE);
    expect(GROUP_ROUTE_LINE).toBe('Исполнитель: группа подключений; подключение будет выбрано при первом обращении к модели.');
    expect(lines.map((line) => line.key).indexOf('executor')).toBe(lines.map((line) => line.key).indexOf('model') + 1);
  });

  it('says nothing new for a route with a connection', () => {
    expect(estimateLines(estimate()).map((line) => line.key)).not.toContain('executor');
  });
});
