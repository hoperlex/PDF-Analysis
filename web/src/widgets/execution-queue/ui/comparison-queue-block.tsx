'use client';

/**
 * The read-only block «Сравнение» of «Очередь» (`CMP-VC-UI-01`, `getComparisonQueueSummary`): what the comparison modules have on
 * the queue — which modules are on, whether execution is paused for the whole installation, the items by state and by kind, and how
 * long the oldest queued one has waited.
 *
 * Comparison work yields to section runs and honours the global pause (ADR-0025 decisions 4, 6 and 7), which is why it is shown next
 * to them and why a paused installation says so here too. Nothing in the block sends anything: a reader who wants to pause or resume a
 * comparison does it on «Сравнение версий». A queue that the module does not serve yet answers `503`, which is shown as the module's
 * state, not as a failure of «Очередь».
 *
 * The block has a query of its own and is mounted by the page of «Очередь» (`_pages/queue`), beside the list of runs, not inside it.
 */

import type { ComparisonQueueSummary } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import {
  QUEUE_MODULE_LABELS,
  QUEUE_STATE_LABELS,
  QUEUE_STATE_ORDER,
  comparisonFailure,
  modulesSentence,
  queueKindLabel,
  useComparisonQueueSummary,
} from '@/entities/version-series';

import { ComparisonAiQueueBlock } from './comparison-ai-queue-block';
import styles from './execution-queue.module.css';

export const COMPARISON_BLOCK_TITLE = 'Сравнение';
export const NO_COMPARISON_WORK = 'Работы сравнения в очереди нет.';
export const COMPARISON_PAUSED_NOTE = 'Выдача задач приостановлена для всей установки: работа сравнения ждёт вместе с прогонами.';

export function ComparisonQueueBlockView({ summary }: { readonly summary: ComparisonQueueSummary }) {
  const present = QUEUE_STATE_ORDER.filter((state) => summary.counts[state] > 0);
  return (
    <section className={styles.comparison} aria-label="Сравнение" data-comparison-queue="" data-comparison-modules={summary.modules}>
      <h2 className={styles.comparisonTitle}>{COMPARISON_BLOCK_TITLE}</h2>
      <p className={styles.comparisonNote}>{modulesSentence(summary.modules)}</p>
      {summary.paused ? (
        <p role="status" className="am-note" data-comparison-paused="">
          {COMPARISON_PAUSED_NOTE}
        </p>
      ) : null}
      {present.length === 0 ? (
        <p className={styles.comparisonNote}>{NO_COMPARISON_WORK}</p>
      ) : (
        <ul className={styles.comparisonCounts}>
          {present.map((state) => (
            <li key={state} data-queue-count={state}>
              {QUEUE_STATE_LABELS[state]}: {summary.counts[state]}
            </li>
          ))}
        </ul>
      )}
      {summary.oldest_queued_at === undefined ? null : (
        <p className={styles.comparisonNote}>
          Самая давняя из ждущих принята <time dateTime={summary.oldest_queued_at}>{formatInstant(summary.oldest_queued_at)}</time>.
        </p>
      )}
      {summary.kinds.length === 0 ? null : (
        <div className={styles.comparisonScroller}>
          <table className={styles.comparisonTable}>
            <thead>
              <tr>
                <th scope="col">Вид работы</th>
                <th scope="col">Модуль</th>
                <th scope="col">Ждут</th>
                <th scope="col">Идут</th>
                <th scope="col">С ошибкой</th>
              </tr>
            </thead>
            <tbody>
              {summary.kinds.map((kind) => (
                <tr key={`${kind.module}-${kind.kind}`} data-queue-kind={kind.kind}>
                  <td>{queueKindLabel(kind.kind)}</td>
                  <td data-queue-module={kind.module}>{QUEUE_MODULE_LABELS[kind.module]}</td>
                  <td>{kind.counts.queued}</td>
                  <td>{kind.counts.running + kind.counts.leased}</td>
                  <td>{kind.counts.failed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ComparisonQueueBlock() {
  const summary = useComparisonQueueSummary();
  if (summary.isPending) return <LoadingState what="сводку сравнения" />;
  if (summary.isError) {
    const failure = comparisonFailure(summary.error);
    return failure.moduleUnavailable ? (
      <div data-comparison-module="unavailable">
        <UnsupportedState title="Модуль сравнения ещё недоступен" detail={failure.detail} />
      </div>
    ) : (
      <ErrorState
        title="Сводка сравнения не открылась"
        detail={failure.detail}
        correlationId={failure.correlationId}
        onRetry={failure.retryable ? () => void summary.refetch() : undefined}
      />
    );
  }
  return (
    <>
      <ComparisonQueueBlockView summary={summary.data} />
      <ComparisonAiQueueBlock />
    </>
  );
}
