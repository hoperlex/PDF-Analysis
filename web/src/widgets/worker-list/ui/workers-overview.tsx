/**
 * The overview tiles of «Обзор» (`UI-PARITY` M-17, ruling `R-151t`; the tab is UI-B-63 and UI-B-64), as the original's
 * line of tiles over its worker monitor: servers online, free slots of the online servers, and the queue's running and
 * waiting jobs, then the queue's line of counts. The original's «Ошибки» and «Завершено сегодня» are not drawn as tiles:
 * our failed-job count is all-time, not the active errors the original means, and «сегодня» needs the installation's
 * time zone from the server. Only figures the API returns are shown; the line says what the queue counts by state.
 *
 * Each tile leads to what it summarises: the two about servers to «Процессы» (the screen's own tab, so the address is
 * given by the page, with a handler that opens the tab without leaving the screen), the two about the queue to «Очередь».
 */

import type { ExecutionQueueStateCount } from '@/shared/api';
import { routes } from '@/shared/lib';
import { queueOverviewLine } from '@/entities/execution';
import type { WorkersOverview } from '@/entities/execution';

import styles from './workers-overview.module.css';

export interface WorkersOverviewViewProps {
  readonly workers: WorkersOverview;
  /** The queue's counts by state (`listExecutionQueue`'s overview); absent while not read. */
  readonly queue?: readonly ExecutionQueueStateCount[] | undefined;
  /** The address of «Процессы»; the two tiles about servers link to it. No address, no link. */
  readonly processesHref?: string | undefined;
  /** Opens «Процессы» on this screen when the link is followed; the address is the fallback (a new tab, no script). */
  readonly onOpenProcesses?: (() => void) | undefined;
}

function countOf(queue: readonly ExecutionQueueStateCount[], ...states: readonly string[]): number {
  return queue.filter((entry) => states.includes(entry.state)).reduce((sum, entry) => sum + entry.count, 0);
}

export function WorkersOverviewView({ workers, queue, processesHref, onOpenProcesses }: WorkersOverviewViewProps) {
  const notOnline = workers.total - workers.online;
  const queueLine = queueOverviewLine(queue);
  const toProcesses = processesHref === undefined ? null : (
    <a
      className={styles.link}
      href={processesHref}
      data-workers-tile-link="processes"
      onClick={onOpenProcesses === undefined ? undefined : (event) => { event.preventDefault(); onOpenProcesses(); }}
    >
      Открыть процессы
    </a>
  );
  const toQueue = (
    <a className={styles.link} href={routes.queue()} data-workers-tile-link="queue">Открыть очередь</a>
  );
  return (
    <>
      <ul className={styles.tiles} data-workers-overview="" data-partial={workers.partial ? 'true' : 'false'}>
        <li className={styles.tile} data-workers-tile="servers">
          <span className={styles.label}>Серверы онлайн</span>
          <span className={styles.value}>{workers.online} / {workers.total}</span>
          {notOnline > 0 ? <span className={styles.note}>{notOnline} не в сети</span> : null}
          {toProcesses}
        </li>
        <li className={styles.tile} data-workers-tile="slots">
          <span className={styles.label}>Свободные слоты</span>
          <span className={styles.value}>{workers.freeSlots} / {workers.onlineSlots}</span>
          <span className={styles.note}>на серверах онлайн</span>
          {toProcesses}
        </li>
        {queue === undefined ? null : (
          <>
            <li className={styles.tile} data-workers-tile="running">
              <span className={styles.label}>Выполняется</span>
              <span className={styles.value}>{countOf(queue, 'leased', 'running')}</span>
              {toQueue}
            </li>
            <li className={styles.tile} data-workers-tile="queued">
              <span className={styles.label}>В очереди</span>
              <span className={styles.value}>{countOf(queue, 'queued', 'retry_wait')}</span>
              {toQueue}
            </li>
          </>
        )}
        {workers.partial ? <li className={styles.partial}>по первой странице исполнителей</li> : null}
      </ul>
      {queueLine === null ? null : <p className={styles.queueLine} data-workers-queue-overview="">{queueLine}</p>}
    </>
  );
}
