/**
 * The critic's queues of the extended review (`R-151q`, register row UI-B-78), as data.
 *
 * The original's «Critic v2» screen lays the notes out in tabs, each with «видимо / всего». The queues here are the
 * critic's own recommendations (`llm_decision`), because that is what the preliminary record carries: nothing is
 * hidden, moved or deleted by the critic, and a queue only filters the one list. The critic's word is a recommendation,
 * never the expert's decision.
 */

type RecordValue = Record<string, unknown>;

function object(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null;
}
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }

/** The value and the name of each queue, in the order the tabs stand. */
export const CRITIC_QUEUES: readonly (readonly [string, string])[] = [
  ['all', 'Все'],
  ['accept', 'Сохранить'],
  ['reject', 'Снять'],
  ['borderline', 'Пограничные'],
  ['needs_human', 'Нужен человек'],
  ['rewrite', 'Уточнить'],
  ['not_reviewed', 'Без критики'],
];

/** The queue an observation stands in: the critic's recommendation, or `not_reviewed`, or `''` when it carries none. */
export function criticQueueOf(item: RecordValue): string {
  return item.review_status === 'not_reviewed' ? 'not_reviewed' : text(object(item.review ?? item.critic)?.llm_decision);
}

/** How many of `observations` stand in each queue; `all` counts every one. Each observation is in at most one queue. */
export function criticQueueCounts(observations: readonly RecordValue[]): Readonly<Record<string, number>> {
  const counts: Record<string, number> = Object.fromEntries(CRITIC_QUEUES.map(([value]) => [value, 0]));
  for (const item of observations) {
    counts.all = (counts.all ?? 0) + 1;
    const key = criticQueueOf(item);
    if (key in counts) counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

/**
 * What a tab says about its queue, as the original's «Замечание не удалено. Оно только вынесено из основной очереди.»
 * does for a collapsed tab. `all` says nothing: it is the whole record.
 */
export const CRITIC_QUEUE_NOTES: Readonly<Record<string, string>> = {
  accept: 'Критик рекомендует сохранить эти наблюдения. Это совет модели, а не решение эксперта.',
  reject: 'Критик рекомендует снять эти наблюдения. Ничего не удалено: наблюдения только собраны в отдельную очередь, а решает эксперт.',
  borderline: 'Критик считает эти случаи пограничными. Решение остаётся за экспертом.',
  needs_human: 'Критик просит проверку человеком. Это не одобрение и не отклонение.',
  rewrite: 'Критик предлагает уточнить формулировку; предложенный вариант показан в карточке наблюдения.',
  not_reviewed: 'Критика для этих наблюдений не выполнялась. Это не одобрение.',
};

/**
 * The same notes for a record whose critic is the original's deterministic one (`V2-ORIGINAL-REVIEW-01`): a rule's word, not a model's.
 * A queue the rules never fill (`reject`, `borderline`) keeps its note.
 */
export const CRITIC_QUEUE_NOTES_DETERMINISTIC: Readonly<Record<string, string>> = {
  ...CRITIC_QUEUE_NOTES,
  accept: 'Правила критика оригинала не нашли структурных проблем. Смысловая проверка не выполнялась; это не решение эксперта.',
  needs_human: 'Правила критика оригинала просят проверку человеком: нет источника, блок не найден или цитата стоит на другой странице. Ничего не удалено; это не одобрение и не отклонение.',
  rewrite: 'Правила критика оригинала предлагают уточнить страницу; предложенный вариант показан в карточке наблюдения.',
};

/** Whether any observation carries a row of the original's deterministic critic. */
export function criticIsDeterministic(observations: readonly RecordValue[]): boolean {
  return observations.some((item) => object(item.review ?? item.critic)?.mode === 'deterministic');
}

/**
 * The queue a key press moves to, for the tabs pattern: `←` and `→` step round the row, `Home` and `End` go to its ends.
 * `null` for any other key, which the tabs leave to the browser.
 */
export function queueAfterKey(current: string, key: string): string | null {
  const values = CRITIC_QUEUES.map(([value]) => value);
  const at = Math.max(0, values.indexOf(current));
  if (key === 'ArrowRight') return values[(at + 1) % values.length] ?? null;
  if (key === 'ArrowLeft') return values[(at - 1 + values.length) % values.length] ?? null;
  if (key === 'Home') return values[0] ?? null;
  if (key === 'End') return values[values.length - 1] ?? null;
  return null;
}
