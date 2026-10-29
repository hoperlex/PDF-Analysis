/**
 * The cells of steps 4 «ИИ-проверка сомнительных пар», 6 «ИИ-описание изменений» and 7 «Сводка и отчёт» of «Проекты и этапы»
 * (`frontend/static/js/version-comparison-projects.js:65-115` `stageView`, `:460-530` `stageActs`, `:355-396` `SELECTABLE`,
 * `OPEN`, `canSelect`).
 *
 * The overview serves these three steps as `not_applicable` until a lane extends it (`CMP-VC-OVERVIEW-01` section 6.1), so the
 * state of a cell is derived here from what the AI layer reads — the latest pair-check job, the AI description's job and its
 * progress per transition, the newest report — and falls back to the overview's own word when none of them has been read. A cell
 * never prints a code: every state has a word, every figure a place.
 *
 * Offering only what the server accepts is the rule of {@link aiStepActions}: «Пауза» for a job that is queued or running
 * (`comparison_ai_job_state` otherwise), «Продолжить» for a paused one (a **new consent** after `overrun` or `route_changed`),
 * «Досчитать» for a cancelled or failed `sheet_changes` job with something left, «Из очереди» for a job that has not started.
 * A report has no pause in the contract (`cancelComparisonReport` keeps the finished parts and `continueComparisonReport` goes on),
 * so step 7 offers «Отменить» where the original has «Пауза».
 */

import type {
  ComparisonAiJob,
  ComparisonAiPairCounts,
  ComparisonAiPauseReason,
  ComparisonAiTransitionProgress,
  ComparisonLaunchEntry,
  ComparisonReport,
  ComparisonStepId,
  ComparisonStepState,
} from '@/shared/api';

import { pauseNeedsConsent } from './ai-words';
import type { AiStepId, SelectableStep, StepView } from './steps';
import { TONE_ICONS, stepView } from './steps';

export type AiStepActionId = 'start' | 'pause' | 'resume' | 'finish' | 'dequeue' | 'restart' | 'cancel' | 'continue' | 'pdf';

export interface AiStepAction {
  readonly id: AiStepActionId;
  readonly label: string;
  /** The command sends a new consent (a start, a restart, a resume after an overrun): it goes through the estimate dialog. */
  readonly asksConsent: boolean;
  readonly title?: string;
}

/** The totals of the AI description over the transitions of a series (`ComparisonAiTransitionProgress`). */
export interface SheetTotals {
  readonly sheets: number;
  readonly done: number;
  readonly errors: number;
  readonly review: number;
  readonly calls: number;
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly seconds: number;
}

export function sheetTotals(rows: readonly ComparisonAiTransitionProgress[]): SheetTotals {
  const sum = (pick: (row: ComparisonAiTransitionProgress) => number): number => rows.reduce((total, row) => total + pick(row), 0);
  return {
    sheets: sum((row) => row.sheets),
    done: sum((row) => row.done),
    errors: sum((row) => row.errors),
    review: sum((row) => row.to_review),
    calls: sum((row) => row.calls),
    inputTokens: sum((row) => row.input_tokens),
    outputTokens: sum((row) => row.output_tokens),
    seconds: sum((row) => row.seconds),
  };
}

export interface AiStepFacts {
  readonly step: AiStepId;
  /** The overview's own word for the step; `not_applicable` until the overview serves it. */
  readonly overviewState: ComparisonStepState;
  readonly versions: number;
  /** Step 4 needs the matrix built (`mReady`, `:462`); step 6 needs the series. */
  readonly matrixReady: boolean;
  readonly seriesKnown: boolean;
  /** Transitions of the series that changed (`counts.with_changes` of step 5): none means step 6 is not needed. */
  readonly seriesChanged?: number | undefined;
  readonly job?: ComparisonAiJob | undefined;
  readonly pairCounts?: ComparisonAiPairCounts | undefined;
  readonly sheets?: readonly ComparisonAiTransitionProgress[] | undefined;
  /** Step 7 needs the summary, which exists once step 6 is done or partial. */
  readonly summaryReady: boolean;
  /** The newest report that was started (a draft is not one). */
  readonly report?: ComparisonReport | undefined;
  /** Step 6 is running or waiting: step 7 is not offered (the summary is not complete yet, `aiBusy`, `:466`). */
  readonly aiChangesBusy: boolean;
}

function jobState(job: ComparisonAiJob, partial: boolean): ComparisonStepState {
  switch (job.state) {
    case 'queued': return 'queued';
    case 'running': return 'running';
    case 'paused': return 'paused';
    case 'completed': return partial || job.counts.failed > 0 ? 'partial' : 'done';
    case 'failed': return 'failed';
    case 'cancelled': return 'interrupted';
  }
}

function reportState(report: ComparisonReport): ComparisonStepState {
  switch (report.state) {
    case 'draft': return 'not_started';
    case 'queued': return 'queued';
    case 'running': return 'running';
    case 'paused': return 'paused';
    case 'completed': return 'done';
    case 'partial': return 'partial';
    case 'failed': return 'failed';
    case 'cancelled': return 'interrupted';
  }
}

/** The state of a cell: the AI layer's read first, then the overview's word, then «не запускалось» or «ждёт предыдущего шага». */
export function aiStepState(facts: AiStepFacts): ComparisonStepState {
  const fallback = (): ComparisonStepState => {
    if (facts.overviewState !== 'not_applicable') return facts.overviewState;
    return 'not_started';
  };
  if (facts.step === 'ai_pairs') {
    if (facts.job !== undefined) return jobState(facts.job, false);
    return facts.matrixReady ? fallback() : facts.overviewState === 'not_applicable' ? 'blocked' : facts.overviewState;
  }
  if (facts.step === 'ai_changes') {
    if (facts.job !== undefined) {
      const totals = sheetTotals(facts.sheets ?? []);
      return jobState(facts.job, totals.errors > 0 || totals.review > 0);
    }
    return facts.seriesKnown ? fallback() : facts.overviewState === 'not_applicable' ? 'blocked' : facts.overviewState;
  }
  if (facts.report !== undefined) return reportState(facts.report);
  return facts.summaryReady ? fallback() : facts.overviewState === 'not_applicable' ? 'blocked' : facts.overviewState;
}

export interface AiStepCell {
  readonly state: ComparisonStepState;
  readonly view: StepView;
  readonly actions: readonly AiStepAction[];
  /** The progress bar of a running or interrupted step (`:207-209`). */
  readonly progress: { readonly done: number; readonly total: number } | null;
  readonly pauseReason: ComparisonAiPauseReason | null;
  /** The job or report the buttons act on. */
  readonly jobId: string | null;
  readonly reportId: string | null;
}

function n(value: number): string {
  return value.toLocaleString('ru-RU');
}

/** «вопросов N · пар N · подсказок N · против N» (`:68-70`). */
export function pairNote(counts: ComparisonAiPairCounts | undefined): string {
  if (counts === undefined || counts.questions === 0) return '';
  return (
    `вопросов ${n(counts.questions)}` +
    (counts.pairs > 0 ? ` · пар ${n(counts.pairs)}` : '') +
    (counts.hints > 0 ? ` · подсказок ${n(counts.hints)}` : '') +
    (counts.against > 0 ? ` · против ${n(counts.against)}` : '')
  );
}

/** «листов готово N из M · ошибок K · проверить R» (`:96-98`). */
export function sheetsNote(totals: SheetTotals): string {
  if (totals.sheets === 0) return '';
  return (
    `листов готово ${n(totals.done)} из ${n(totals.sheets)}` +
    (totals.errors > 0 ? ` · ошибок ${n(totals.errors)}` : '') +
    (totals.review > 0 ? ` · проверить ${n(totals.review)}` : '')
  );
}

const PARTIAL_TITLE =
  'Описания готовы. «Проверить» — листы, где ИИ изменений не нашёл, но сравнение оставило пометки (например, пара листов сопоставлена неуверенно): откройте комплект, блок «ИИ-описание изменений», столбец «Проверить». «Ошибок» — листы, которые ИИ не смог описать.';

export const NOT_NEEDED_TITLE = 'Переходов с изменениями содержания нет.';

export function reportNote(report: ComparisonReport | undefined, summaryReady: boolean): string {
  if (report === undefined) return summaryReady ? 'PDF не формировался' : '';
  const finished = report.parts.filter((part) => (part.selection ?? part.analysis) === 'done').length;
  const total = report.parts.length;
  if (report.state === 'completed') return 'MD + PDF';
  return total > 0 ? `переходов ${n(finished)} из ${n(total)}` : '';
}

function lines(...parts: readonly (string | false | undefined)[]): string {
  return parts.filter((part): part is string => typeof part === 'string' && part !== '').join('\n');
}

export function aiStepActions(facts: AiStepFacts, state: ComparisonStepState): readonly AiStepAction[] {
  const A = (id: AiStepActionId, label: string, asksConsent: boolean, title?: string): AiStepAction => ({
    id, label, asksConsent, ...(title === undefined ? {} : { title }),
  });
  if (facts.versions < 2) return [];
  const reason = facts.job?.pause_reason;
  if (facts.step === 'ai_pairs') {
    if (!facts.matrixReady) return [];
    switch (state) {
      case 'not_started':
      case 'failed':
      case 'interrupted':
        return [A('start', 'Проверить', true, 'ИИ проверит только листы, которые алгоритм не связал уверенно. Другие шаги не запускаются. Ответы, которые уже есть, повторно не отправляются.')];
      case 'queued':
      case 'running':
        return [A('pause', 'Пауза', false, 'Начатое доводится и сохраняется, новое не начинается.')];
      case 'paused':
        return [A('resume', 'Продолжить', pauseNeedsConsent(reason), 'С того же места: готовое не пересчитывается.')];
      default:
        return [];
    }
  }
  if (facts.step === 'ai_changes') {
    if (!facts.seriesKnown || state === 'blocked') return [];
    const left = facts.job !== undefined && facts.job.counts.done < facts.job.counts.total;
    switch (state) {
      case 'not_started':
        return facts.seriesChanged === 0
          ? []
          : [A('start', 'Запустить', true, 'ИИ опишет изменения на листах и соберёт «Сводку изменений (MD)».')];
      case 'queued':
        return [A('dequeue', 'Из очереди', false, 'Убрать комплект из очереди ИИ-описаний; ничего не будет описано.')];
      case 'running':
        return [A('pause', 'Пауза', false, 'Начатое доводится и сохраняется, новое не начинается.')];
      case 'paused':
        return [A('resume', 'Продолжить', pauseNeedsConsent(reason), 'С того же места: готовое не пересчитывается.')];
      case 'interrupted':
      case 'failed':
        return [
          ...(left ? [A('finish', 'Продолжить', false, 'Описать оставшиеся листы; готовые не описываются заново.')] : []),
          A('restart', 'Заново', true, 'Описать заново: листы, которые не менялись, берутся из сохранённых ответов.'),
        ];
      case 'done':
      case 'partial':
        return [A('restart', 'Заново', true, 'Описать заново: листы, которые не менялись, берутся из сохранённых ответов.')];
      default:
        return [];
    }
  }
  // step 7
  if (state === 'blocked' || !facts.summaryReady) return [];
  switch (state) {
    case 'not_started':
      return [A('start', 'Сформировать PDF-отчёт', true, facts.aiChangesBusy ? 'Идёт ИИ-описание изменений — дождитесь окончания.' : 'ИИ подготовит короткий отчёт по «Сводке изменений (MD)».')];
    case 'queued':
    case 'running':
      return [A('cancel', 'Отменить', false, 'Остановить отчёт. Готовые части сохранятся, отчёт можно будет продолжить.')];
    case 'paused':
    case 'interrupted':
    case 'failed':
    case 'partial': {
      const needs = pauseNeedsConsent(facts.report?.job?.pause_reason);
      return [
        A('continue', 'Продолжить', needs, 'С того же места: готовые переходы не отправляются заново.'),
        A('restart', 'Заново', true, 'Сформировать отчёт с начала по текущей сводке.'),
      ];
    }
    case 'done':
      return [A('pdf', 'PDF', false, 'Скачать готовый PDF-отчёт.'), A('restart', 'Заново', true, 'Сформировать отчёт заново по текущей сводке.')];
    default:
      return [];
  }
}

export function aiStepCell(facts: AiStepFacts): AiStepCell {
  const state = aiStepState(facts);
  const base = stepView(facts.step, state);
  let { text, tone } = base;
  let note = '';
  let title = '';
  let progress: { done: number; total: number } | null = null;
  const totals = sheetTotals(facts.sheets ?? []);
  if (facts.step === 'ai_pairs') {
    note = pairNote(facts.pairCounts);
    if (state === 'blocked') text = 'ждёт сопоставления';
    const counts = facts.pairCounts;
    title = lines(
      counts !== undefined && counts.questions > 0 &&
        `Вопросов ИИ: ${counts.questions}; пар поставлено: ${counts.pairs}; подсказок у «⁇»: ${counts.hints}`,
      counts !== undefined && counts.against > 0 &&
        `ИИ против пары алгоритма: ${counts.against} — проверить в матрице («ИИ ?»)`,
    );
    if (facts.job !== undefined && facts.job.counts.total > 0 && (state === 'running' || state === 'paused')) {
      progress = { done: facts.job.counts.done, total: facts.job.counts.total };
    }
  } else if (facts.step === 'ai_changes') {
    note = sheetsNote(totals);
    if (state === 'queued') text = `в очереди №${facts.job?.queue_position ?? '?'}`;
    if (state === 'partial') title = PARTIAL_TITLE;
    if (totals.calls > 0) title = lines(title, `Обращений: ${n(totals.calls)}`);
    if (state === 'not_started' && facts.seriesChanged === 0) {
      text = 'не нужно';
      tone = 'ok';
      title = NOT_NEEDED_TITLE;
    }
    if ((state === 'running' || state === 'paused' || state === 'interrupted') && totals.sheets > 0) {
      progress = { done: totals.done, total: totals.sheets };
    }
  } else {
    note = reportNote(facts.report, facts.summaryReady);
    if (state === 'not_started') {
      text = facts.summaryReady ? 'есть MD' : '—';
      tone = facts.summaryReady ? 'todo' : 'off';
    }
    if (state === 'partial') text = 'неполный результат';
    if (state === 'blocked') text = '—';
  }
  if (state === 'paused' && facts.job?.pause_reason !== undefined && facts.step !== 'report') {
    title = lines(title, 'Пауза: причина указана в подсказке кнопки «Продолжить».');
  }
  const jobId = facts.step === 'report' ? (facts.report?.job?.job_id ?? null) : (facts.job?.job_id ?? null);
  return {
    state,
    view: { text, note, tone, icon: TONE_ICONS[tone], title },
    actions: aiStepActions(facts, state),
    progress,
    pauseReason: (facts.step === 'report' ? facts.report?.job?.pause_reason : facts.job?.pause_reason) ?? null,
    jobId,
    reportId: facts.report?.report_id ?? null,
  };
}

// ------------------------------------------------------------------------------ selection (`projects.js:355-396`)

/** Which states of each selectable step the queue can run or continue (`OPEN`, `:366-368`). */
const OPEN_STATES: Readonly<Record<SelectableStep, readonly ComparisonStepState[]>> = {
  ai_pairs: ['not_started', 'paused', 'interrupted', 'done', 'partial', 'attention', 'failed'],
  series: ['not_started', 'stale', 'paused', 'interrupted', 'failed'],
  ai_changes: ['not_started', 'blocked', 'paused', 'interrupted'],
  report: ['not_started', 'blocked', 'paused', 'interrupted', 'failed'],
};

export interface SelectContext {
  readonly mayAct: boolean;
  readonly versions: number;
  readonly state: ComparisonStepState;
  /** Step 6 with no changed transition has nothing to describe (`:376`). */
  readonly seriesChanged?: number | undefined;
  /** The set and step already stand in the queue. */
  readonly queued: boolean;
}

export function canSelect(step: SelectableStep, context: SelectContext): boolean {
  if (!context.mayAct || context.versions < 2 || context.queued) return false;
  if (!OPEN_STATES[step].includes(context.state)) return false;
  if (step === 'ai_changes' && context.state === 'not_started' && context.seriesChanged === 0) return false;
  return true;
}

export function selectionKey(documentUid: string, step: ComparisonStepId): string {
  return `${documentUid}|${step}`;
}

export type ColumnState = 'none' | 'off' | 'some' | 'all';

/** «выбрать все» of a column (`colState`, `:380-385`): nothing selectable, none, some or all of the selectable cells. */
export function columnState(selectable: readonly string[], selected: ReadonlySet<string>): ColumnState {
  if (selectable.length === 0) return 'none';
  const chosen = selectable.filter((key) => selected.has(key)).length;
  return chosen === 0 ? 'off' : chosen === selectable.length ? 'all' : 'some';
}

export const COLUMN_SELECT_TITLE = (label: string): string => `Выбрать все строки, где шаг «${label}» можно запустить или продолжить`;
export const ROW_SELECT_TITLE = (label: string): string => `Выбрать для запуска по очереди: ${label}`;

// ------------------------------------------------------------------------------ the queue badge of a cell (`queuedAt`, `:358-369`)

export interface QueueBadge {
  readonly short: string;
  readonly title: string;
}

/** The entry of the launch queue that holds this set and step, and what to say of it; `null` when none does. */
export function queueBadge(
  entries: readonly ComparisonLaunchEntry[],
  documentUid: string,
  step: ComparisonStepId,
): QueueBadge | null {
  const entry = entries.find(
    (item) => item.document_uid === documentUid && item.step === step && (item.state === 'waiting' || item.state === 'running' || item.state === 'needs_consent'),
  );
  if (entry === undefined) return null;
  if (entry.state === 'running') return { short: 'очередь: идёт', title: 'идёт' };
  if (entry.state === 'needs_consent') return { short: 'очередь: ждёт подтверждения', title: 'ждёт вашего подтверждения передачи' };
  const ahead = entries.filter((item) => item.state === 'waiting' && item.position <= entry.position).length;
  return { short: `в очереди №${ahead}`, title: `ждёт, №${ahead}` };
}
