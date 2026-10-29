/**
 * «Очередь запуска» of a project and «Очередь «ИИ-описание изменений»» of the installation (`version-comparison-projects.js:136-151`,
 * `:355-357`, `:421-457`; `version-comparison.js:949-960`).
 *
 * The original's single global stage queue is two surfaces here (seal §3 decision 5): the **launch queue** is a project's — one
 * step at a time across its sets — and the **AI queue** is the installation's read of the AI jobs that wait. Reading either starts
 * nothing. This file says them in Russian and decides which controls the strip offers; the strip is drawn by
 * `widgets/version-series`.
 */

import type {
  ComparisonAiMethod,
  ComparisonAiQueue,
  ComparisonAiQueueItem,
  ComparisonLaunchEntry,
  ComparisonLaunchQueue,
  ComparisonLaunchQueueState,
  ComparisonOverviewSet,
  ComparisonStepId,
} from '@/shared/api';

import { AI_METHOD_LABELS } from './ai-words';
import { codeOf } from './overview-view';
import { STEP_LABELS, type StepTone } from './steps';

export const LAUNCH_QUEUE_TITLE = 'Очередь запуска';
export const AI_QUEUE_TITLE = 'Очередь «ИИ-описание изменений»';

/** The tone and icon of the queue's state chip (`:138-140`): running, paused or the rest. */
export const LAUNCH_QUEUE_TONES: Readonly<Record<ComparisonLaunchQueueState, { readonly tone: StepTone; readonly icon: string }>> = {
  running: { tone: 'run', icon: '⟳' },
  paused: { tone: 'warn', icon: '!' },
  failed: { tone: 'bad', icon: '✕' },
  done: { tone: 'ok', icon: '✓' },
  idle: { tone: 'ok', icon: '✓' },
};

/** «готово N из M · пропущено K · ошибок E» with the running, waiting and unconfirmed ones in between (`:142`). */
export function launchCountsLine(queue: ComparisonLaunchQueue): string {
  const c = queue.counts;
  return (
    `готово ${c.done}` +
    (c.running > 0 ? ` · идёт ${c.running}` : '') +
    (c.waiting > 0 ? ` · ждут ${c.waiting}` : '') +
    (c.needs_consent > 0 ? ` · ждут подтверждения ${c.needs_consent}` : '') +
    ` из ${c.total}` +
    (c.skipped > 0 ? ` · пропущено ${c.skipped}` : '') +
    (c.failed > 0 ? ` · ошибок ${c.failed}` : '')
  );
}

/** The strip is shown when the queue holds any entry (`queue.items.length`, `:136`). */
export function launchQueueShown(queue: ComparisonLaunchQueue | undefined): queue is ComparisonLaunchQueue {
  return queue !== undefined && queue.entries.length > 0;
}

export interface LaunchControls {
  readonly pause: boolean;
  readonly resume: boolean;
  readonly clear: boolean;
}

/** «Пауза очереди» while it runs; «Продолжить очередь» when paused or stopped; «Очистить» when something can be cleared (`:143-146`). */
export function launchControls(queue: ComparisonLaunchQueue): LaunchControls {
  const c = queue.counts;
  return {
    pause: queue.state === 'running',
    resume: queue.state === 'paused' || queue.state === 'failed',
    clear: c.waiting + c.needs_consent + c.done + c.failed + c.skipped > 0,
  };
}

/** An entry that can still be taken off the queue («✕», `:150`). */
export function canRemoveEntry(entry: ComparisonLaunchEntry): boolean {
  return entry.state === 'waiting' || entry.state === 'needs_consent';
}

export function entryLabel(entry: ComparisonLaunchEntry, sets: readonly ComparisonOverviewSet[]): string {
  const set = sets.find((item) => item.document_uid === entry.document_uid);
  const code = set === undefined ? '' : codeOf(set);
  return `${code === '' ? 'Комплект без шифра' : code} · ${STEP_LABELS[entry.step]}`;
}

/** The title and the lines of the dialog «Запустить по очереди» (`runSelected`, `:398-419`): the first eight, then «… и ещё N». */
export const PREVIEW_LIMIT = 8;

export function previewLines(items: readonly { readonly label: string }[]): readonly string[] {
  const lines = items.slice(0, PREVIEW_LIMIT).map((item, index) => `${index + 1}. ${item.label}`);
  if (items.length > PREVIEW_LIMIT) lines.push(`… и ещё ${items.length - PREVIEW_LIMIT}`);
  return lines;
}

export const SELECTION_RUN_LABEL = 'Запустить выбранные по очереди';
export const SELECTION_CLEAR_LABEL = 'Снять выбор';
export const SELECTION_RUN_TITLE = 'Отмеченные шаги выполнятся по одному: комплект за комплектом, внутри комплекта — слева направо.';
export const QUEUE_ENQUEUE_LABEL = 'Поставить в очередь';

export function selectionTitle(total: number, sets: number): string {
  return `Запустить по очереди: ${total} шагов, комплектов ${sets}`;
}

// ------------------------------------------------------------------------------ the installation's AI queue

const AI_QUEUE_PHASES = {
  running: 'идёт',
  paused: 'на паузе',
  queued: 'ждёт',
  completed: 'готово',
  failed: 'ошибка',
  cancelled: 'отменено',
} as const;

/** «идёт «шифр» · далее: «шифр» → «шифр»» (`aiQueueText`, `:949-957`); a set of another project is named «другой проект». */
export function aiQueueName(item: ComparisonAiQueueItem, sets: readonly ComparisonOverviewSet[]): string {
  const set = sets.find((entry) => entry.document_uid === item.document_uid);
  return set === undefined ? '«комплект другого проекта»' : `«${codeOf(set) === '' ? 'комплект без шифра' : codeOf(set)}»`;
}

export function aiQueueText(queue: ComparisonAiQueue, sets: readonly ComparisonOverviewSet[]): string {
  const running = queue.items.find((item) => item.state === 'running' || item.state === 'paused');
  const waiting = queue.items.filter((item) => item.state === 'queued');
  const parts: string[] = [];
  if (running !== undefined) parts.push(`${AI_QUEUE_PHASES[running.state]} ${aiQueueName(running, sets)}`);
  if (waiting.length > 0) parts.push(`далее: ${waiting.map((item) => aiQueueName(item, sets)).join(' → ')}`);
  return parts.join(' · ');
}

/** The strip is shown while anything is running or waits (`:76`). */
export function aiQueueShown(queue: ComparisonAiQueue | undefined): queue is ComparisonAiQueue {
  return queue !== undefined && queue.items.length > 0;
}

export function aiQueueItemLine(item: ComparisonAiQueueItem): string {
  const where = item.queue_position === undefined ? '' : `№${item.queue_position} · `;
  const progress = item.counts.total > 0 ? ` · ${item.counts.done} из ${item.counts.total}` : '';
  return `${where}${AI_METHOD_LABELS[item.method as ComparisonAiMethod]} — ${AI_QUEUE_PHASES[item.state]}${progress}`;
}

export function queueStepLabel(step: ComparisonStepId): string {
  return STEP_LABELS[step];
}
