'use client';

/**
 * «Очередь «ИИ-описание изменений»» of the installation (`frontend/static/js/version-comparison.js:76-79`, `:949-960`;
 * `getComparisonAiQueue`): the AI jobs of the version comparison that are queued, running or paused anywhere on this stand, the
 * running one first and then in the order they will start. A read for any role; it starts nothing, and a job is controlled in its
 * own cell on «Сравнение версий». It sits under the block «Сравнение» of «Очередь».
 *
 * The queue names no set (a job carries identities only), so a line says the method, the place in the queue and how far the job
 * got. A queue the module does not serve yet is the module's state, not a failure of «Очередь».
 */

import type { ComparisonAiQueue } from '@/shared/api';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { AI_QUEUE_TITLE, aiQueueItemLine, comparisonFailure, useAiQueue } from '@/entities/version-series';

import styles from './execution-queue.module.css';

export const NO_AI_QUEUE = 'ИИ-задач сравнения в очереди нет.';

export function ComparisonAiQueueBlockView({ queue }: { readonly queue: ComparisonAiQueue }) {
  return (
    <section className={styles.aiQueue} aria-label={AI_QUEUE_TITLE} data-comparison-ai-queue="">
      <h3 className={styles.comparisonTitle}>{AI_QUEUE_TITLE}</h3>
      {queue.items.length === 0 ? (
        <p className={styles.comparisonNote}>{NO_AI_QUEUE}</p>
      ) : (
        <>
          <p className={styles.comparisonNote}>
            идёт: {queue.running} · на паузе: {queue.paused} · ждут: {queue.queued}
          </p>
          <ol className={styles.aiQueueList}>
            {queue.items.map((item) => (
              <li key={item.job_id} data-ai-job-state={item.state} data-ai-method={item.method}>
                {aiQueueItemLine(item)}
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

export function ComparisonAiQueueBlock() {
  const queue = useAiQueue();
  if (queue.isPending) return <LoadingState what="очередь ИИ-описаний" />;
  if (queue.isError) {
    const failure = comparisonFailure(queue.error);
    return failure.moduleUnavailable ? (
      <div data-comparison-module="unavailable">
        <UnsupportedState title="Очередь ИИ-описаний ещё недоступна" detail={failure.detail} />
      </div>
    ) : (
      <ErrorState
        title="Очередь ИИ-описаний не открылась"
        detail={failure.detail}
        correlationId={failure.correlationId}
        onRetry={failure.retryable ? () => void queue.refetch() : undefined}
      />
    );
  }
  return <ComparisonAiQueueBlockView queue={queue.data} />;
}
