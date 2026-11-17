'use client';

/**
 * «Отменить очередь (N)» and what follows it (`UIP-S13-04`): the button in the page's head, and under the head the one confirmation, the
 * line while the runs are being cancelled and the honest result. The sequence is `useCancelQueue`'s, the words and the sums are
 * `../model/cancel-queue.ts`'s. A run is named by its document and version, never by its number.
 */

import { ErrorState, LoadingState } from '@/shared/ui';

import { cancelSummary, workName } from '../model/cancel-queue';
import type { CancelQueue } from './use-cancel-queue';
import styles from './queue-page.module.css';

export interface CancelQueueButtonProps {
  /** The overview's count of jobs that are not finished; the button is not drawn for none. */
  readonly count: number;
  readonly busy: boolean;
  readonly onClick: () => void;
}

export function CancelQueueButton({ count, busy, onClick }: CancelQueueButtonProps) {
  if (count <= 0) return null;
  return (
    <button className="am-button am-button--quiet" type="button" disabled={busy} data-queue-cancel-all={count} onClick={onClick}>
      Отменить очередь ({count})
    </button>
  );
}

export function CancelQueuePanel({ queue }: { readonly queue: CancelQueue }) {
  const { phase } = queue;
  switch (phase.kind) {
    case 'idle':
      return null;
    case 'reading':
      return <LoadingState what="задачи, которые можно отменить" />;
    case 'read_failed':
      return (
        <div data-queue-cancel-failure="">
          <ErrorState title="Задачи очереди не прочитаны" detail={phase.failure.detail} correlationId={phase.failure.correlationId} onRetry={queue.begin} />
          <button type="button" className="am-button am-button--quiet" onClick={queue.dismiss}>Закрыть</button>
        </div>
      );
    case 'ask':
      return (
        <section className={styles.intent} role="group" aria-label="Подтверждение отмены очереди" data-queue-cancel-ask={phase.jobs.length}>
          <p>Отменить очередь? Будет отменено задач: {phase.jobs.length}. Каждая отменяется отдельной командой.</p>
          <button type="button" className="am-button" onClick={queue.confirm}>Подтвердить</button>{' '}
          <button type="button" className="am-button am-button--quiet" onClick={queue.dismiss}>Отмена</button>
        </section>
      );
    case 'sending':
      return (
        <section className={styles.intent} role="group" aria-label="Отмена очереди" data-queue-cancel-sending="">
          <p role="status">Отменяю: {phase.sent} из {phase.total}…</p>
          <button type="button" className="am-button am-button--quiet" onClick={queue.stop}>Остановить</button>
        </section>
      );
    case 'done': {
      if (phase.outcomes.length === 0) {
        return (
          <section className={styles.intent} role="group" aria-label="Отмена очереди" data-queue-cancel-result="0">
            <p role="status">Отменять нечего: в очереди нет задач, которые можно отменить.</p>
            <button type="button" className="am-button am-button--quiet" onClick={queue.dismiss}>Закрыть</button>
          </section>
        );
      }
      const summary = cancelSummary(phase.outcomes);
      const unknown = phase.outcomes.some((outcome) => outcome.kind === 'unknown');
      return (
        <section className={styles.intent} role="group" aria-label="Итог отмены очереди" data-queue-cancel-result={summary.cancelled} data-queue-cancel-total={summary.total}>
          <p role="status">{summary.sentence}</p>
          {summary.rest.length === 0 ? null : (
            <ul data-queue-cancel-rest="">
              {summary.rest.map(({ item, reason }) => <li key={item.job_id}>{workName(item)}: {reason}.</li>)}
            </ul>
          )}
          {unknown ? (
            <button type="button" className="am-button" disabled={queue.busy} onClick={queue.retryUnknown}>Повторить с тем же ключом</button>
          ) : null}{' '}
          <button type="button" className="am-button am-button--quiet" onClick={queue.dismiss}>Закрыть</button>
        </section>
      );
    }
  }
}
