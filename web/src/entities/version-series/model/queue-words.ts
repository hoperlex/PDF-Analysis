/**
 * The block «Сравнение» of «Очередь»: the states of the comparison work and the kinds of it, in words.
 * `ComparisonQueueKind.kind` is the name of a work kind, a word of the server's; the table below names the
 * ones the comparison workers have (`comparison/work`, `profile_queue`, `matrix`, `ingest/comparison_batch`);
 * any other is «Другая работа сравнения» and its name stays in a `data-` attribute.
 */

import type { ComparisonModules, ComparisonQueueCounts } from '@/shared/api';

export const QUEUE_STATE_LABELS: Readonly<Record<keyof ComparisonQueueCounts, string>> = {
  queued: 'ждут',
  leased: 'взяты в работу',
  running: 'идут',
  retry_wait: 'ждут повтора',
  paused: 'на паузе',
  spend_unknown: 'расход неизвестен',
  succeeded: 'выполнены',
  failed: 'с ошибкой',
  cancelled: 'отменены',
};

/** The order the counts are listed in: what is waiting or running first, what ended last. */
export const QUEUE_STATE_ORDER: readonly (keyof ComparisonQueueCounts)[] = [
  'queued', 'leased', 'running', 'retry_wait', 'paused', 'spend_unknown', 'failed', 'cancelled', 'succeeded',
];

export const QUEUE_KIND_LABELS: Readonly<Record<string, string>> = {
  page_profile: 'Разбор страниц версии',
  matrix_build: 'Сборка сопоставления листов',
  comparison_batch_drive: 'Ведение загрузки пакета',
  upload_abort_sweep: 'Уборка отменённой загрузки',
  pair_result: 'Сравнение пары листов',
  series_drive: 'Ведение сравнения соседних версий',
};

export const OTHER_QUEUE_KIND = 'Другая работа сравнения';

export function queueKindLabel(kind: string): string {
  return QUEUE_KIND_LABELS[kind] ?? OTHER_QUEUE_KIND;
}

export const QUEUE_MODULE_LABELS = {
  versions: 'Сравнение версий',
  stages: 'Сравнение стадий',
} as const;

/** What the deployment serves, said as a sentence under the block's heading. */
export function modulesSentence(modules: ComparisonModules): string {
  switch (modules) {
    case 'none': return 'Модули сравнения выключены: работа не берётся.';
    case 'versions': return 'Включён модуль «Сравнение версий».';
    case 'versions,stages': return 'Включены модули «Сравнение версий» и «Сравнение стадий».';
  }
}
