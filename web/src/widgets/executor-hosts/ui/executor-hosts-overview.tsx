'use client';

/**
 * The tab «Обзор» of «Диспетчер» (`UIP-S15-04`, `Г12-B`, `Г4-B`, `Г1-C`): a strip of five numbers and, under it, the servers in a
 * short form.
 *
 * ```
 * На связи 2 из 3 · Выполняется 3 · В очереди 4 · Ошибки 2 · Свободно мест 3 из 7
 *
 * ● основной  на связи  ▮▮▯ 2/3          ● резерв  нет связи с 11:02
 * Сейчас: Планы этажей · Анализ блоков   …                          Все серверы →
 * ```
 *
 * The servers' numbers come from the list of servers, the queue's three from the queue's overview (`running` and `leased` are
 * «Выполняется», `queued` and `retry_wait` are «В очереди», `live_failure_count` is «Ошибки»: the number of the red badge of the menu's
 * «Очередь»); `overviewFigures` of the `executor-host` entity puts them in one line. A queue that cannot be read leaves three dashes
 * and says so, and the two numbers of the servers stay. A card has no models and no control: those are on «Серверы». Nothing
 * the stand has no data for is drawn: no load of a machine, no limit of a provider, no «следующая задача», «проекты для проверки»,
 * «требует внимания» or «завершено сегодня».
 *
 * Nothing is read until the roles are: the viewer reads neither list (`R-150w`). Only the open tab is mounted, so a closed tab reads
 * nothing.
 */

import type { ExecutionQueueStateCount, ExecutorHost, ExecutorHostList, Role } from '@/shared/api';
import { UpdateTime, executionFailure, queueStateCount, useExecutionQueue } from '@/entities/execution';
import {
  HOST_STATE_LABELS,
  OVERVIEW_QUEUE_NOT_READ,
  SERVERS_EMPTY,
  hostRowReading,
  liveHosts,
  mayReadHosts,
  noContactSentence,
  overviewFigures,
  useExecutorHosts,
} from '@/entities/executor-host';
import type { HostRowReading } from '@/entities/executor-host';
import { EmptyState, ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';

import { HostNow } from './host-now';

import styles from './executor-hosts.module.css';

const TONE_CLASS = { ok: styles.dotOk, busy: styles.dotBusy, offline: styles.dotOffline } as const;

/** The queue as the strip reads it: its overview and the count of the failures nothing has answered. */
export interface OverviewQueue {
  readonly overview: readonly ExecutionQueueStateCount[] | undefined;
  readonly liveFailures: number | undefined;
}

/** The sum of the counts of some states, or `null` when the queue says none (it was not read). */
function sumOf(overview: OverviewQueue['overview'], states: readonly ExecutionQueueStateCount['state'][]): number | null {
  let sum = 0;
  for (const state of states) {
    const one = queueStateCount(overview, state);
    if (one === null) return null;
    sum += one;
  }
  return sum;
}

export interface HostCompactProps {
  readonly host: ExecutorHost;
  readonly asOf: number | null;
}

/** A server in its short form: the dot, the name, the state, the load and what it is doing now. No models, no control. */
export function HostCompact({ host, asOf }: HostCompactProps) {
  const reading: HostRowReading = hostRowReading(host);
  return (
    <li
      className={`${styles.row} ${reading.noContact ? styles.rowOffline : ''}`}
      data-host-compact={reading.hostId}
      data-host-state={host.state}
      data-host-tone={reading.tone}
    >
      <div className={styles.head}>
        <span className={`${styles.dot} ${TONE_CLASS[reading.tone]}`} role="img" aria-label={HOST_STATE_LABELS[host.state]}>●</span>
        <span className={styles.name}>{reading.name}</span>
      </div>
      <div className={styles.meta}>
        {reading.noContact ? (
          <span className={styles.note} data-host-no-contact>{noContactSentence(host.last_seen_at)}</span>
        ) : (
          <>
            <span className={styles.stateWord} data-host-state-word>{HOST_STATE_LABELS[host.state]}</span>
            <span className={styles.load} data-host-load={reading.load}>
              <meter className={styles.meter} min={0} max={Math.max(reading.slotsTotal, 1)} value={reading.slotsInUse} aria-label="Занято мест" />
              {reading.load}
            </span>
          </>
        )}
      </div>
      <HostNow reading={reading} asOf={asOf} />
    </li>
  );
}

export interface HostsOverviewViewProps {
  readonly list: ExecutorHostList;
  /** The queue's numbers; `null` when the queue was not read. */
  readonly queue: OverviewQueue | null;
  readonly asOf: number | null;
  /** The press of «Все серверы →»: the page opens its tab «Серверы». */
  readonly onShowServers: () => void;
}

/** The strip and the cards of a read list and a read queue; the pure part of the tab. */
export function HostsOverviewView({ list, queue, asOf, onShowServers }: HostsOverviewViewProps) {
  const hosts = liveHosts(list);
  const figures = overviewFigures({
    online: list.online,
    total: list.total,
    slotsFree: list.slots_free,
    slotsTotal: list.slots_total,
    running: queue === null ? null : sumOf(queue.overview, ['running', 'leased']),
    queued: queue === null ? null : sumOf(queue.overview, ['queued', 'retry_wait']),
    failures: queue?.liveFailures ?? null,
  });
  return (
    <>
      <ul className={styles.figures} aria-label="Итоги" data-overview-figures>
        {figures.map((figure) => (
          <li key={figure.key} className={`${styles.figure} ${figure.warning ? styles.figureWarning : ''}`} data-overview-figure={figure.key}>
            <span className={styles.figureLabel}>{figure.label}</span>
            {' '}
            <span className={styles.figureValue}>{figure.value}</span>
          </li>
        ))}
      </ul>
      {queue === null ? <p className="am-note" data-overview-queue-failure>{OVERVIEW_QUEUE_NOT_READ}</p> : null}
      {hosts.length === 0 ? (
        <EmptyState title={SERVERS_EMPTY} />
      ) : (
        <ul className={styles.list} data-overview-hosts>
          {hosts.map((host) => <HostCompact key={host.host_id} host={host} asOf={asOf} />)}
        </ul>
      )}
      <p className={styles.allServers}>
        <button type="button" className="am-button am-button--quiet" data-overview-all-servers onClick={onShowServers}>Все серверы →</button>
      </p>
    </>
  );
}

export interface ExecutorHostsOverviewProps {
  readonly roles: readonly Role[];
  readonly onShowServers: () => void;
}

export function ExecutorHostsOverview({ roles, onShowServers }: ExecutorHostsOverviewProps) {
  if (!mayReadHosts(roles)) {
    return <UnsupportedState title="Обзор недоступен" detail="Обзор показывается экспертам и администраторам." />;
  }
  return <OverviewReads onShowServers={onShowServers} />;
}

/** The two reads of the tab; mounted only for a role that may read them, so the viewer sends neither. */
function OverviewReads({ onShowServers }: { readonly onShowServers: () => void }) {
  const hosts = useExecutorHosts(true);
  const queue = useExecutionQueue();
  const failure = hosts.error === null ? null : executionFailure(hosts.error, false);
  // A failed read keeps the answer before it beside its error; that number is not what the server says now, so it is not drawn.
  const queueRead: OverviewQueue | null = queue.isError
    ? null
    : { overview: queue.data?.overview, liveFailures: queue.data?.live_failure_count };

  return (
    <div className={styles.panel} data-hosts-overview>
      <UpdateTime dataUpdatedAt={hosts.dataUpdatedAt} failed={hosts.isError} />
      {hosts.isPending ? <LoadingState what="серверы" /> : null}
      {failure === null ? null : (
        <div data-hosts-read-failure={failure.kind}>
          <ErrorState
            title={hosts.data === undefined ? 'Серверы не прочитаны' : 'Серверы не обновились'}
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void hosts.refetch()}
          />
        </div>
      )}
      {hosts.data === undefined ? null : (
        <HostsOverviewView
          list={hosts.data}
          queue={queueRead}
          asOf={hosts.dataUpdatedAt > 0 ? hosts.dataUpdatedAt : null}
          onShowServers={onShowServers}
        />
      )}
    </div>
  );
}
