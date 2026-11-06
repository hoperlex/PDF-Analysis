/**
 * The overview tiles over «Процессы» (`UI-PARITY` M-17, ruling `R-151t`), as the original's line of tiles over its
 * worker monitor: servers online, free slots of the online servers, and the queue's running and waiting jobs. The
 * original's «Ошибки» and «Завершено сегодня» are not drawn: our failed-job count is all-time, not the active errors
 * the original means, and «сегодня» needs the installation's time zone from the server.
 */

import type { ExecutionQueueStateCount } from '@/shared/api';
import type { WorkersOverview } from '@/entities/execution';

import styles from './workers-overview.module.css';

export interface WorkersOverviewViewProps {
  readonly workers: WorkersOverview;
  /** The queue's counts by state (`listExecutionQueue`'s overview); absent while not read. */
  readonly queue?: readonly ExecutionQueueStateCount[] | undefined;
}

function countOf(queue: readonly ExecutionQueueStateCount[], ...states: readonly string[]): number {
  return queue.filter((entry) => states.includes(entry.state)).reduce((sum, entry) => sum + entry.count, 0);
}

export function WorkersOverviewView({ workers, queue }: WorkersOverviewViewProps) {
  const notOnline = workers.total - workers.online;
  return (
    <ul className={styles.tiles} data-workers-overview="" data-partial={workers.partial ? 'true' : 'false'}>
      <li className={styles.tile}>
        <span className={styles.label}>Серверы онлайн</span>
        <span className={styles.value}>{workers.online} / {workers.total}</span>
        {notOnline > 0 ? <span className={styles.note}>{notOnline} не в сети</span> : null}
      </li>
      <li className={styles.tile}>
        <span className={styles.label}>Свободные слоты</span>
        <span className={styles.value}>{workers.freeSlots} / {workers.onlineSlots}</span>
        <span className={styles.note}>на серверах онлайн</span>
      </li>
      {queue === undefined ? null : (
        <>
          <li className={styles.tile}>
            <span className={styles.label}>Выполняется</span>
            <span className={styles.value}>{countOf(queue, 'leased', 'running')}</span>
          </li>
          <li className={styles.tile}>
            <span className={styles.label}>В очереди</span>
            <span className={styles.value}>{countOf(queue, 'queued', 'retry_wait')}</span>
          </li>
        </>
      )}
      {workers.partial ? <li className={styles.partial}>по первой странице исполнителей</li> : null}
    </ul>
  );
}
