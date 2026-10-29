/**
 * The AI layer of «Сравнение версий» (`CMP-VC-UI-02`): the estimate and the consent, the cells of steps 4/6/7 and what they offer,
 * the selection and the queues, the hints in the cells, the rules of the report window, the label on every AI text and on a
 * recorded answer, and the module that is not wired.
 *
 * Each commitment the brief names has a test here that a mutation of the source turns red (the report quotes them): the
 * consent carries the digest it showed, a stale estimate asks again, no AI text is drawn without «не подтверждено инженером»,
 * a recorded answer says so, a `503` is a state and not a crash, and the census reaches the stylesheets.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api';
import type * as api from '@/shared/api';
import { ChangesPanelView, EvidenceBanner } from '@/widgets/comparison-viewer';
import { ReportWindowView } from '@/widgets/comparison-report';
import { AiChangesBlockView, ProjectsAndStagesView, SpecificationsBlockView } from '@/widgets/version-series';
import {
  COMPARISON_KEYS,
  AI_JOB_PARTIAL_LABEL,
  AI_PAUSE_ADVICE,
  AI_PAUSE_REASON_LABELS,
  pauseNeedsConsent,
  AiLabel,
  AiText,
  EstimatePanel,
  RECORDED_LABEL,
  UNCONFIRMED_LABEL,
  aiStepActions,
  aiStepCell,
  agreementStands,
  canCancelReport,
  canContinueReport,
  canDeleteReport,
  canPrepareClientReport,
  canRebuildReport,
  canSelect,
  columnState,
  comparisonFailure,
  consentOf,
  costLine,
  estimateLines,
  evidenceOf,
  formatUsd,
  hintMark,
  hintText,
  hintsFor,
  launchControls,
  launchCountsLine,
  positionsLine,
  queueBadge,
  reconsentRequired,
  selectionKey,
  sheetTotals,
} from '@/entities/version-series';
import type { AiStepFacts } from '@/entities/version-series';
import { refusalAction } from '@/entities/version-series/api/use-consent-flow';
import { sendAiStart } from '@/entities/version-series/api/use-ai-commands';

import { newClient, renderScreen, seedError } from '../screens/harness';

import {
  DIGEST,
  DIGEST_NEW,
  description,
  estimate,
  hints,
  job,
  launchQueue,
  report,
  reportsInEveryShape,
  sheetChanges,
  specChanges,
  specification,
} from './ai-fixtures';
import { DOCUMENT_UID, PROJECT_UID, SERIES_ID, V1, V2, V3, matrix, overview, series, uid } from './fixtures';
import { projectsProps } from './shapes';
import { refusal } from './seed';

const noop = (): void => undefined;
const LATIN = /[A-Za-z]/;

const calls = vi.hoisted(() => ({ start: vi.fn() }));
vi.mock('@/shared/api', async (importOriginal) => ({
  ...(await importOriginal<typeof api>()),
  startComparisonAiPairCheck: calls.start,
  startComparisonAiSheetChanges: calls.start,
}));

beforeEach(() => {
  calls.start.mockReset();
  calls.start.mockResolvedValue({ data: job() });
});

function panel(over: Partial<Parameters<typeof ChangesPanelView>[0]> = {}): string {
  return renderToStaticMarkup(
    createElement(ChangesPanelView, {
      sheetTitle: 'л. 3 · Схема', description: description(), loading: false, failure: null, mayAct: true, busy: false, copied: false,
      history: undefined, estimate: null, onDescribe: noop, onCancelJob: noop, onShow: noop, onCopy: noop, onMd: noop, ...over,
    }),
  );
}

const count = (markup: string, attribute: string): number => (markup.match(new RegExp(`\\s${attribute}=`, 'g')) ?? []).length;

// ------------------------------------------------------------------------------ the consent carries the digest it showed

describe('the consent of an AI start carries the digest of the estimate that was shown', () => {
  it('is that estimate\'s digest, confirmed', () => {
    expect(consentOf(estimate({ estimate_digest: DIGEST_NEW }))).toEqual({ estimate_digest: DIGEST_NEW, confirmed: true });
  });

  it('sends it in the body of every start, for a pair check and for a series', async () => {
    const shown = estimate({ estimate_digest: DIGEST_NEW });
    await sendAiStart({ scope: { kind: 'pair_check', projectUid: PROJECT_UID, documentUid: DOCUMENT_UID } as never, shown }, 'key-1');
    await sendAiStart({ scope: { kind: 'sheet_changes', seriesId: SERIES_ID } as never, shown, restart: true }, 'key-2');
    expect(calls.start).toHaveBeenCalledTimes(2);
    for (const [input] of calls.start.mock.calls as [{ body: { consent: unknown; restart?: boolean }; idempotencyKey: string }][]) {
      expect(input.body.consent).toEqual({ estimate_digest: DIGEST_NEW, confirmed: true });
    }
    expect((calls.start.mock.calls[1] as [{ body: { restart?: boolean } }])[0].body.restart).toBe(true);
    expect((calls.start.mock.calls[0] as [{ idempotencyKey: string }])[0].idempotencyKey).toBe('key-1');
  });

  it('offers the confirm button only to an agreement given to the estimate on screen', () => {
    const props = { title: 'Запуск', consentKind: 'sheet_changes', confirmLabel: 'Запустить', estimate: estimate(), loading: false, failure: null, busy: false, onAgree: noop, onConfirm: noop, onCancel: noop } as const;
    const confirm = (agreedDigest: string | null, over: object = {}): string => {
      const markup = renderToStaticMarkup(createElement(EstimatePanel, { ...props, agreedDigest, ...over }));
      return /<button[^>]*data-estimate-confirm=""[^>]*>/.exec(markup)?.[0] ?? '';
    };
    expect(confirm(DIGEST)).not.toContain('disabled');
    expect(confirm(null)).toContain('disabled');
    expect(confirm(DIGEST_NEW)).toContain('disabled');
    expect(confirm(DIGEST, { estimate: estimate({ blocked_by: 'job' }) })).toContain('disabled');
    expect(confirm(DIGEST, { estimate: estimate({ calls: 0, reused: 12 }) })).toContain('disabled');
    expect(confirm(DIGEST, { busy: true })).toContain('disabled');
  });
});

// ------------------------------------------------------------------------------ a stale estimate asks again

describe('a refusal for a stale estimate asks again', () => {
  const stale = comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_estimate_stale' }));

  it('is recognised and said in words', () => {
    expect(stale.estimateStale).toBe(true);
    expect(stale.kind).toBe('estimate_stale');
    expect(stale.detail).toContain('подтвердите ещё раз');
    expect(comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_ceiling_job' })).estimateStale).toBe(false);
  });

  it('voids the agreement and reads the estimate again, never sends by itself', () => {
    expect(refusalAction(stale)).toBe('ask-again');
    expect(refusalAction(comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_ceiling_day' })))).toBe('show');
    expect(refusalAction(comparisonFailure(refusal('internal_error')))).toBe('show');
  });

  it('keeps no agreement for an estimate other than the one it was given to', () => {
    expect(agreementStands(DIGEST, estimate())).toBe(true);
    expect(agreementStands(DIGEST, estimate({ estimate_digest: DIGEST_NEW }))).toBe(false);
    expect(reconsentRequired(DIGEST, estimate({ estimate_digest: DIGEST_NEW }))).toBe(true);
    expect(reconsentRequired(null, estimate())).toBe(false);
    const markup = renderToStaticMarkup(
      createElement(EstimatePanel, {
        title: 'Запуск', consentKind: 'sheet_changes', confirmLabel: 'Запустить', estimate: estimate({ estimate_digest: DIGEST_NEW }), loading: false,
        failure: stale, agreedDigest: DIGEST, busy: false, onAgree: noop, onConfirm: noop, onCancel: noop,
      }),
    );
    expect(markup).toContain('data-estimate-reasked=""');
    expect(markup).toContain('data-estimate-refusal="stale"');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*data-estimate-confirm=""/);
  });
});

// ------------------------------------------------------------------------------ the estimate in words

describe('the estimate says what would be sent and what it would cost', () => {
  it('prints USD with the hundredths rounded up and never reads a small spend as free', () => {
    expect(formatUsd(3_450_000)).toBe('3,45 долл.');
    expect(formatUsd(3_450_001)).toBe('3,46 долл.');
    expect(formatUsd(900)).toBe('меньше 0,01 долл.');
    expect(formatUsd(0)).toBe('0,00 долл.');
    expect(formatUsd(46_000_000)).toBe('46,00 долл.');
  });

  it('says «без учёта стоимости» for a connection that is not metered, and no ceilings', () => {
    const subscription = estimate({ estimate_micros: 0, route: { ...estimate().route, billing: 'not_metered' } });
    expect(costLine(subscription)).toBe('без учёта стоимости');
    const text = estimateLines(subscription).map((line) => line.text).join('\n');
    expect(text).toContain('без учёта стоимости');
    expect(text).toContain('Потолки по деньгам на это подключение не действуют');
    expect(text).not.toContain('10 долл.');
  });

  it('lists the calls, the images with their bytes, the size of the prompt, the model and the ceilings', () => {
    const text = estimateLines(estimate()).map((line) => line.text).join('\n');
    expect(text).toContain('Обращений к модели: 9');
    expect(text).toContain('изображений: 18 (5,2 МБ)');
    expect(text).toContain('текст: 48');
    expect(text).toContain('Модель: Модель-эксперт-1');
    expect(text).toContain('≈ 3,45 долл.');
    expect(text).toContain('10 долл. на одно задание и 50 долл. в день');
    expect(text).toContain('в 1,2 раза');
    for (const line of estimateLines(estimate())) expect(line.text.replace(/МБ/g, '')).not.toMatch(LATIN);
  });
});

// ------------------------------------------------------------------------------ the label on every AI text

describe('every AI text carries «не подтверждено инженером»', () => {
  it('is drawn with its label by AiText', () => {
    const markup = renderToStaticMarkup(createElement(AiText, null, 'Кабель заменён'));
    expect(markup).toContain('data-ai-text=""');
    expect(markup).toContain('data-ai-label=""');
    expect(markup).toContain(UNCONFIRMED_LABEL);
    expect(renderToStaticMarkup(createElement(AiLabel, {}))).toContain(UNCONFIRMED_LABEL);
  });

  it('labels every text the side panel draws from a description', () => {
    const markup = panel();
    // three changes (each one text), the open question, plus the note under the panel: every `data-ai-text` has its label.
    expect(count(markup, 'data-ai-text')).toBeGreaterThanOrEqual(4);
    expect(count(markup, 'data-ai-label')).toBe(count(markup, 'data-ai-text'));
    expect(markup).toContain(UNCONFIRMED_LABEL);
  });

  it('labels the model\'s sentence on a hint in a cell, a text of the evidence banner and a position change', () => {
    const cell = renderToStaticMarkup(createElement(EvidenceBanner, { evidence: { items: evidenceOf(description()), index: 0, all: false }, onAction: noop }));
    expect(count(cell, 'data-ai-label')).toBe(count(cell, 'data-ai-text'));
    expect(count(cell, 'data-ai-text')).toBe(1);
    const specs = renderToStaticMarkup(
      createElement(SpecificationsBlockView, {
        specs: [specification()], transitions: series().transitions ?? [], names: new Map([[V1, '№1'], [V2, '№2']]), mayAct: true, busy: false, failure: null,
        openChanges: series().transitions?.[0]?.transition_id ?? null, changes: null, onOpenChanges: noop, onStart: noop, onCancel: noop, onOpenTransition: noop, dialog: null,
      }),
    );
    expect(specs).toContain('Полные спецификации (СО)');
    expect(specChanges().filter((change) => change.text !== undefined)).toHaveLength(1);
  });
});

describe('the pauses of a job, as the job core stops them', () => {
  it('says a day-ceiling stop (reason quota) and a job-ceiling stop (reason overrun) in words, and asks a new consent only after the second', () => {
    expect(AI_PAUSE_REASON_LABELS.quota).toContain('дневной потолок');
    expect(AI_PAUSE_REASON_LABELS.overrun).toContain('потолок одного задания');
    expect(AI_PAUSE_ADVICE.overrun).toContain('новым подтверждением');
    expect(pauseNeedsConsent('overrun')).toBe(true);
    expect(pauseNeedsConsent('route_changed')).toBe(true);
    expect(pauseNeedsConsent('quota')).toBe(false);
    expect(pauseNeedsConsent(undefined)).toBe(false);
  });

  it('finishes a cancelled job under the consent it holds: «Досчитать» sends no estimate', () => {
    const finish = aiStepCell(facts({ step: 'ai_changes', job: job({ state: 'cancelled', counts: { total: 12, done: 5, failed: 0, unknown: 0 } }) })).actions.find((a) => a.id === 'finish');
    expect(finish).toMatchObject({ label: 'Продолжить', asksConsent: false });
  });
});

describe('a recorded (test) answer is labelled as one', () => {
  it('says so on the panel and puts the label on the texts', () => {
    const recorded = panel({ description: description({ recorded: true }) });
    expect(recorded).toContain('data-recorded-label=""');
    expect(recorded).toContain(RECORDED_LABEL);
    const ordinary = panel({ description: description({ recorded: false }) });
    expect(ordinary).not.toContain('data-recorded-label');
    expect(ordinary).not.toContain(RECORDED_LABEL);
    expect(recorded.match(/data-recorded-label=""/g)?.length ?? 0).toBeGreaterThan(count(recorded, 'data-ai-text') - 2);
  });

  it('marks a job or a report whose route records, by the provider mode of its route', () => {
    const block = (provider: 'live' | 'recorded'): string =>
      renderToStaticMarkup(createElement(AiChangesBlockView, {
        changes: sheetChanges({ job: job({ estimate: estimate({ route: { ...estimate().route, provider_mode: provider } }) }) }), series: series(),
        names: new Map(), mayAct: true, busy: false, failure: null, folds: new Set<string>(), review: new Map(), onFold: noop, onAct: noop,
        onOpenTransition: noop, onOpenReviewSheet: noop, dialog: null,
      }));
    expect(block('recorded')).toContain('data-recorded-label=""');
    expect(block('recorded')).toContain('тестовый ответ');
    expect(block('live')).not.toContain('data-recorded-label');
  });

  it('says so in the history of the descriptions, and warns when the connection itself records', () => {
    const history = panel({
      history: { items: [{ description_id: uid('csd', 2), state: 'done', changes_count: 1, unresolved_count: 0, recorded: true, created_at: '2026-10-27T10:15:30Z' }], page: { next_cursor: null } },
    });
    expect(history).toContain(RECORDED_LABEL);
    const warned = renderToStaticMarkup(
      createElement(EstimatePanel, {
        title: 'Запуск', consentKind: 'sheet_changes', confirmLabel: 'Запустить', estimate: estimate({ route: { ...estimate().route, provider_mode: 'recorded' } }),
        loading: false, failure: null, agreedDigest: null, busy: false, onAgree: noop, onConfirm: noop, onCancel: noop,
      }),
    );
    expect(warned).toContain('data-provider-recorded=""');
  });
});

// ------------------------------------------------------------------------------ a 503 is a state, not a crash

describe('a module that is not wired is a state on every screen', () => {
  const NOT_WIRED = refusal('dependency_unavailable', { dependency: 'comparison_ai_sheets' });

  it('is the module\'s state for the classifier, whichever class names it', () => {
    for (const dependency of ['comparison_ai_pairs', 'comparison_ai_sheets', 'comparison_specification', 'comparison_launch_queue', 'comparison_reports', 'comparison_modules']) {
      expect(comparisonFailure(refusal('dependency_unavailable', { dependency })).moduleUnavailable, dependency).toBe(true);
    }
  });

  it('is not the module\'s state when a work kind has no route: that is a refusal with advice', () => {
    const failure = comparisonFailure(refusal('dependency_unavailable', { dependency: 'executor_route_missing' }));
    expect(failure.moduleUnavailable).toBe(false);
    expect(failure.detail).toContain('Назначениях');
  });

  it('renders the panel, the blocks, the window and the cells without throwing', () => {
    const failure = comparisonFailure(NOT_WIRED);
    expect(panel({ description: undefined, failure })).toContain('data-comparison-module="unavailable"');
    const block = renderToStaticMarkup(createElement(AiChangesBlockView, {
      changes: sheetChanges(), series: series(), names: new Map(), mayAct: true, busy: false, failure, folds: new Set<string>(), review: new Map(),
      onFold: noop, onAct: noop, onOpenTransition: noop, onOpenReviewSheet: noop, dialog: null,
    }));
    expect(block).toContain('Модуль «Сравнение версий» ещё недоступен');
    const reportWindow = renderToStaticMarkup(createElement(ReportWindowView, {
      reports: [], transitions: [], names: new Map(), summaryReady: true, mayAct: true, busy: false, failure, source: 'series_summary', onSource: noop,
      kind: 'client', onKind: noop, reuse: true, onReuse: noop, fileName: null, onFile: noop, onPrepareEstimate: noop, onAct: noop, onClose: noop, dialog: null,
    }));
    expect(reportWindow).toContain('data-comparison-module="unavailable"');
  });

  it('draws the cells of a row whose reads are refused as «ещё недоступно», with the sentence on hover and no button', () => {
    const client = newClient();
    for (const set of overview().sets) {
      seedError(client, COMPARISON_KEYS.aiPair(PROJECT_UID, set.document_uid), refusal('dependency_unavailable', { dependency: 'comparison_ai_pairs' }));
    }
    const markup = renderScreen(client, createElement(ProjectsAndStagesView, projectsProps()));
    expect(markup).toContain('data-comparison-module="unavailable"');
    expect(markup).toContain('ещё недоступно');
    expect(markup).toContain('Модуль «Сравнение версий» ещё недоступен');
  });
});

// ------------------------------------------------------------------------------ the cells of steps 4, 6 and 7

function facts(over: Partial<AiStepFacts> & Pick<AiStepFacts, 'step'>): AiStepFacts {
  return { overviewState: 'not_applicable', versions: 4, matrixReady: true, seriesKnown: true, summaryReady: false, aiChangesBusy: false, ...over };
}

describe('the cells of steps 4, 6 and 7', () => {
  it('offers «Проверить» to a set with a ready matrix and no check, and nothing while the matrix is not ready', () => {
    expect(aiStepCell(facts({ step: 'ai_pairs' })).actions.map((a) => a.label)).toEqual(['Проверить']);
    const blocked = aiStepCell(facts({ step: 'ai_pairs', matrixReady: false }));
    expect(blocked.state).toBe('blocked');
    expect(blocked.actions).toEqual([]);
    expect(aiStepCell(facts({ step: 'ai_pairs', versions: 1 })).actions).toEqual([]);
  });

  it('pauses a running job and resumes a paused one; after an overrun the resume asks for a new consent', () => {
    expect(aiStepCell(facts({ step: 'ai_pairs', job: job({ method: 'pair_check', state: 'running' }) })).actions.map((a) => a.id)).toEqual(['pause']);
    const user = aiStepCell(facts({ step: 'ai_pairs', job: job({ method: 'pair_check', state: 'paused', pause_reason: 'user' }) }));
    expect(user.actions).toEqual([expect.objectContaining({ id: 'resume', label: 'Продолжить', asksConsent: false })]);
    for (const reason of ['overrun', 'route_changed'] as const) {
      const cell = aiStepCell(facts({ step: 'ai_pairs', job: job({ method: 'pair_check', state: 'paused', pause_reason: reason }) }));
      expect(cell.actions[0]).toMatchObject({ id: 'resume', asksConsent: true });
      expect(cell.pauseReason).toBe(reason);
    }
    for (const reason of ['user', 'quota', 'auth', 'module_off'] as const) {
      expect(aiStepCell(facts({ step: 'ai_pairs', job: job({ method: 'pair_check', state: 'paused', pause_reason: reason }) })).actions[0]?.asksConsent).toBe(false);
    }
  });

  it('says the original\'s words and notes for the pair check', () => {
    const done = aiStepCell(facts({
      step: 'ai_pairs', job: job({ method: 'pair_check', state: 'completed' }),
      pairCounts: { questions: 6, answered: 6, pairs: 2, hints: 3, against: 1, failed: 0, reused: 0 },
    }));
    expect(done.view.text).toBe('проверено');
    expect(done.view.note).toBe('вопросов 6 · пар 2 · подсказок 3 · против 1');
    expect(done.actions).toEqual([]);
    expect(aiStepCell(facts({ step: 'ai_pairs' })).view.text).toBe('не проверялось');
  });

  it('keeps the original\'s buttons for step 6: «Запустить», «Из очереди», «Пауза», «Продолжить», «Заново»', () => {
    const labels = (over: Partial<AiStepFacts>): string[] => aiStepCell(facts({ step: 'ai_changes', ...over })).actions.map((a) => a.label);
    expect(labels({})).toEqual(['Запустить']);
    expect(labels({ job: job({ state: 'queued', queue_position: 2 }) })).toEqual(['Из очереди']);
    expect(aiStepCell(facts({ step: 'ai_changes', job: job({ state: 'queued', queue_position: 2 }) })).view.text).toBe('в очереди №2');
    expect(labels({ job: job({ state: 'running' }) })).toEqual(['Пауза']);
    expect(labels({ job: job({ state: 'paused', pause_reason: 'quota' }) })).toEqual(['Продолжить']);
    expect(labels({ job: job({ state: 'completed' }), sheets: sheetChanges().transitions })).toEqual(['Заново']);
    expect(labels({ job: job({ state: 'cancelled', counts: { total: 12, done: 5, failed: 0, unknown: 0 } }) })).toEqual(['Продолжить', 'Заново']);
    expect(labels({ job: job({ state: 'cancelled', counts: { total: 12, done: 12, failed: 0, unknown: 0 } }) })).toEqual(['Заново']);
  });

  it('reads step 6 as «не нужно» when no transition changed, and as «готово» with notes when sheets need a look', () => {
    const none = aiStepCell(facts({ step: 'ai_changes', seriesChanged: 0 }));
    expect(none.view.text).toBe('не нужно');
    expect(none.actions).toEqual([]);
    const partial = aiStepCell(facts({ step: 'ai_changes', job: job({ state: 'completed' }), sheets: sheetChanges().transitions }));
    expect(partial.state).toBe('partial');
    expect(partial.view.text).toBe('готово');
    expect(partial.view.note).toBe('листов готово 10 из 12 · ошибок 1 · проверить 2');
    expect(sheetTotals(sheetChanges().transitions)).toMatchObject({ sheets: 12, done: 10, errors: 1, review: 2 });
  });

  it('keeps step 7 to what the contract can do: no pause, «Отменить» instead; «PDF» and «Заново» when it is done', () => {
    const labels = (over: Partial<AiStepFacts>): string[] => aiStepCell(facts({ step: 'report', summaryReady: true, ...over })).actions.map((a) => a.label);
    expect(labels({})).toEqual(['Сформировать PDF-отчёт']);
    expect(aiStepCell(facts({ step: 'report', summaryReady: true })).view.text).toBe('есть MD');
    expect(aiStepCell(facts({ step: 'report', summaryReady: false })).actions).toEqual([]);
    expect(labels({ report: report({ state: 'running' }) })).toEqual(['Отменить']);
    expect(labels({ report: report({ state: 'completed' }) })).toEqual(['PDF', 'Заново']);
    expect(labels({ report: report({ state: 'failed' }) })).toEqual(['Продолжить', 'Заново']);
    expect(aiStepCell(facts({ step: 'report', summaryReady: true, report: report({ state: 'completed' }) })).view.text).toBe('PDF готов');
    expect(aiStepCell(facts({ step: 'report', summaryReady: true, report: report({ state: 'running' }) })).view.text).toBe('PDF строится');
    for (const labelled of ['Пауза']) expect(labels({ report: report({ state: 'running' }) })).not.toContain(labelled);
  });

  it('draws a state of every kind without printing a code', () => {
    for (const state of ['queued', 'running', 'paused', 'completed', 'failed', 'cancelled'] as const) {
      for (const step of ['ai_pairs', 'ai_changes'] as const) {
        const cell = aiStepCell(facts({ step, job: job({ state, ...(state === 'paused' ? { pause_reason: 'auth' as const } : {}) }) }));
        expect(`${cell.view.text} ${cell.view.note} ${cell.view.title}`.replace(/№|MD/g, ''), `${step} ${state}`).not.toMatch(LATIN);
      }
    }
  });

  it('says a partial job in the original\'s words', () => {
    expect(AI_JOB_PARTIAL_LABEL).toBe('готово, есть ошибки');
    expect(aiStepActions(facts({ step: 'ai_changes' }), 'blocked')).toEqual([]);
  });
});

// ------------------------------------------------------------------------------ the selection and the queues

describe('the selection bar and the launch queue', () => {
  const open = { mayAct: true, versions: 4, queued: false } as const;

  it('ticks only what can be started or continued, as the original does', () => {
    expect(canSelect('ai_pairs', { ...open, state: 'not_started' })).toBe(true);
    expect(canSelect('ai_pairs', { ...open, state: 'done' })).toBe(true);
    expect(canSelect('ai_pairs', { ...open, state: 'running' })).toBe(false);
    expect(canSelect('series', { ...open, state: 'stale' })).toBe(true);
    expect(canSelect('series', { ...open, state: 'done' })).toBe(false);
    expect(canSelect('ai_changes', { ...open, state: 'not_started', seriesChanged: 0 })).toBe(false);
    expect(canSelect('ai_changes', { ...open, state: 'blocked' })).toBe(true);
    expect(canSelect('report', { ...open, state: 'done' })).toBe(false);
    expect(canSelect('report', { ...open, state: 'failed' })).toBe(true);
    expect(canSelect('report', { ...open, state: 'failed', mayAct: false })).toBe(false);
    expect(canSelect('report', { ...open, state: 'failed', versions: 1 })).toBe(false);
    expect(canSelect('report', { ...open, state: 'failed', queued: true })).toBe(false);
  });

  it('knows «выбрать все» of a column: none, off, some, all', () => {
    const keys = [selectionKey('a', 'ai_pairs'), selectionKey('b', 'ai_pairs'), selectionKey('c', 'ai_pairs')];
    expect(columnState([], new Set())).toBe('none');
    expect(columnState(keys, new Set())).toBe('off');
    expect(columnState(keys, new Set(keys.slice(0, 1)))).toBe('some');
    expect(columnState(keys, new Set(keys))).toBe('all');
  });

  it('says the strip of the queue in the original\'s words and offers the controls its state allows', () => {
    const queue = launchQueue('running');
    expect(launchCountsLine(queue)).toBe('готово 1 · идёт 1 · ждут 1 · ждут подтверждения 1 из 6 · пропущено 1 · ошибок 1');
    expect(launchControls(queue)).toEqual({ pause: true, resume: false, clear: true });
    expect(launchControls(launchQueue('paused'))).toEqual({ pause: false, resume: true, clear: true });
    expect(launchControls(launchQueue('failed')).resume).toBe(true);
    expect(launchControls({ ...launchQueue('idle'), counts: { total: 0, done: 0, running: 0, waiting: 0, needs_consent: 0, skipped: 0, failed: 0 } }).clear).toBe(false);
  });

  it('badges a cell that stands in the queue', () => {
    const queue = launchQueue('running');
    const waiting = queue.entries.find((entry) => entry.state === 'waiting');
    const running = queue.entries.find((entry) => entry.state === 'running');
    const consent = queue.entries.find((entry) => entry.state === 'needs_consent');
    expect(queueBadge(queue.entries, waiting?.document_uid ?? '', waiting?.step ?? 'series')?.short).toMatch(/^в очереди №\d$/);
    expect(queueBadge(queue.entries, running?.document_uid ?? '', running?.step ?? 'series')?.short).toBe('очередь: идёт');
    expect(queueBadge(queue.entries, consent?.document_uid ?? '', consent?.step ?? 'series')?.short).toBe('очередь: ждёт подтверждения');
    expect(queueBadge(queue.entries, 'nobody', 'series')).toBeNull();
  });

  it('draws the table with the selection bar and the strips, and the first-tab checkboxes only for an expert', () => {
    const first = overview().sets[0]?.document_uid ?? '';
    const ticked = new Set<string>([selectionKey(first, 'series')]);
    const render = (over: Record<string, unknown>): string =>
      renderScreen(newClient(), createElement(ProjectsAndStagesView, projectsProps(over)));
    const expert = render({ selected: ticked, selectableAi: new Set<string>([selectionKey(first, 'ai_pairs')]) });
    expect(expert).toContain('data-selection-bar="1"');
    expect(expert).toContain('Запустить выбранные по очереди');
    expect(expert).toContain('Снять выбор');
    expect(expert).toContain('data-select-column="series"');
    const reader = render({ selected: ticked, mayAct: false });
    expect(reader).not.toContain('data-selection-bar');
    expect(reader).not.toContain('data-select-column');
    expect(reader).not.toContain('data-select-step');
  });
});

// ------------------------------------------------------------------------------ the hints in the cells

describe('the AI flags and hints in the matrix cells', () => {
  const m = matrix();
  const all = hints();

  it('joins a hint to its cell by (version, page)', () => {
    const row = m.rows?.[5];
    const cell = row?.cells.find((c) => c.version_uid === V3);
    expect(row === undefined || cell === undefined).toBe(false);
    const mine = hintsFor(all, row as NonNullable<typeof row>, cell as NonNullable<typeof cell>);
    expect(mine.map((hint) => hint.decision)).toEqual(['link_accepted']);
    // a hint of another version's cell of the same row does not land here, nor does one for a sheet that is not in the row
    expect(hintsFor(all, (m.rows ?? [])[3] as never, (m.rows ?? [])[3]?.cells[0] as never)).toEqual([]);
  });

  it('says «🌙 ИИ: вероятно стр. N» for a hint with a page and «ИИ ?» where the AI is against the pair', () => {
    const moon = all.find((hint) => hint.decision === 'hint_confidence');
    const doubt = all.find((hint) => hint.decision === 'medium_other');
    expect(moon && hintMark(moon)).toBe('moon');
    expect(moon && hintText(moon)).toBe('🌙 ИИ: вероятно стр. 7');
    expect(doubt && hintMark(doubt)).toBe('doubt');
    expect(doubt && hintText(doubt)).toBe('ИИ ?');
  });

  it('has a mark and words for every one of the thirteen decisions', () => {
    expect(all).toHaveLength(13);
    for (const hint of all) {
      expect(hintText(hint)).not.toBe('');
      expect(hintText(hint).replace(/ИИ/g, '')).not.toMatch(LATIN);
    }
  });
});

// ------------------------------------------------------------------------------ the report and the specifications

describe('the report window offers what the server accepts', () => {
  const state = (s: Parameters<typeof canCancelReport>[0]['state']) => ({ state: s });

  it('cancels a live report, continues a stopped one, rebuilds a complete one, deletes one that is not live', () => {
    for (const s of ['queued', 'running', 'paused'] as const) {
      expect(canCancelReport(state(s)), s).toBe(true);
      expect(canDeleteReport(state(s)), s).toBe(false);
    }
    for (const s of ['paused', 'partial', 'failed', 'cancelled'] as const) expect(canContinueReport(state(s)), s).toBe(true);
    for (const s of ['draft', 'queued', 'running', 'completed'] as const) expect(canContinueReport(state(s)), s).toBe(false);
    expect(canRebuildReport({ state: 'completed' } as never)).toBe(true);
    expect(canRebuildReport({ state: 'failed', stage: 'pdf_writing' })).toBe(true);
    expect(canRebuildReport({ state: 'failed', stage: 'verification' })).toBe(false);
    expect(canRebuildReport({ state: 'running', stage: 'pdf_writing' })).toBe(false);
    expect(canPrepareClientReport({ state: 'completed', kind: 'analytic' })).toBe(true);
    expect(canPrepareClientReport({ state: 'completed', kind: 'client' })).toBe(false);
    expect(canPrepareClientReport({ state: 'running', kind: 'analytic' })).toBe(false);
  });

  it('draws the window with every control in some row, and the controls are for an expert', () => {
    const props = {
      reports: reportsInEveryShape(), transitions: series().transitions ?? [], names: new Map(), summaryReady: true, busy: false, failure: null,
      source: 'series_summary' as const, onSource: noop, kind: 'client' as const, onKind: noop, reuse: true, onReuse: noop, fileName: null, onFile: noop,
      onPrepareEstimate: noop, onAct: noop, onClose: noop, dialog: null,
    };
    const expert = renderToStaticMarkup(createElement(ReportWindowView, { ...props, mayAct: true }));
    for (const act of ['pdf', 'source', 'start', 'cancel', 'continue', 'rebuild', 'prepare', 'delete']) expect(expert, act).toContain(`data-report-act="${act}"`);
    expect(expert).toContain('Подготовить оценку');
    const reader = renderToStaticMarkup(createElement(ReportWindowView, { ...props, mayAct: false }));
    expect(reader).toContain('data-report-act="pdf"');
    for (const act of ['start', 'cancel', 'continue', 'rebuild', 'prepare', 'delete']) expect(reader, act).not.toContain(`data-report-act="${act}"`);
    expect(reader).not.toContain('data-report-start');
  });

  it('says the positions of a specification as «изменено / +добавлено / −удалено / ?неясно»', () => {
    expect(positionsLine({ changed: 3, added: 1, removed: 2, unclear: 1, renumbered: 0, moved: 0 })).toBe('3 / +1 / −2 / ?1');
    expect(positionsLine({ changed: 3, added: 1, removed: 2, unclear: 0, renumbered: 0, moved: 0 })).toBe('3 / +1 / −2');
    expect(positionsLine(undefined)).toBe('—');
  });
});

// ------------------------------------------------------------------------------ a failure the cell cannot read

describe('the reasons of wave C2 are said in Russian', () => {
  it('words every new conflict, constraint and dependency, and none prints a code', () => {
    const conflicts = ['comparison_estimate_stale', 'comparison_ceiling_job', 'comparison_ceiling_day', 'comparison_ai_job_active', 'comparison_ai_job_state', 'comparison_ai_nothing_to_do', 'comparison_description_missing', 'comparison_summary_unavailable', 'comparison_report_state', 'comparison_launch_entry_active', 'comparison_launch_entry_state', 'comparison_launch_queue_state'];
    for (const reason of conflicts) {
      const failure = comparisonFailure(refusal('conflict', { conflict_reason: reason }));
      expect(failure.detail, reason).toMatch(/[А-Яа-я]/);
      expect(failure.detail, reason).not.toContain('caller-safe');
    }
    for (const constraint of ['comparison_consent_required', 'comparison_step_not_queueable', 'comparison_report_source_invalid']) {
      const failure = comparisonFailure(new ApiError(422, { contract_version: '1.11.0', error_code: 'validation_failed', message: 'English', correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: false, details: { constraint } }, '0f0e9d8c-7b6a-4948-b726-150413021100'));
      expect(failure.detail, constraint).toMatch(/[А-Яа-я]/);
      expect(failure.detail, constraint).not.toContain('English');
    }
  });
});

