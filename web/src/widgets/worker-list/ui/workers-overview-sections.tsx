/**
 * The three blocks under the tiles of «Обзор» (`UI-B-64`, the original's overview): «Вычислительные узлы» (one line per
 * server), «Очередь — ближайшие проверки» and «Требует внимания». They are drawn from the first page of the registry and the
 * first page of the queue that the screen already reads for its tiles, so the overview asks the API for nothing more; each
 * block says that it is a first page when the server has more.
 */

import Link from 'next/link';

import type { ExecutionQueueItem, ExecutionWorker } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { queueItemError, workerStateLabel } from '@/entities/execution';

import { attentionItems, nextJobs } from '../model/attention';
import styles from './workers-overview-sections.module.css';

export interface WorkersOverviewSectionsProps {
  readonly workers: readonly ExecutionWorker[];
  /** The registry has pages beyond the one read. */
  readonly workersPartial: boolean;
  /** The first page of the queue; absent while it is not read. */
  readonly jobs?: readonly ExecutionQueueItem[] | undefined;
  readonly jobsPartial?: boolean | undefined;
  readonly processesHref?: string | undefined;
  readonly onOpenProcesses?: (() => void) | undefined;
}

const NEXT_LIMIT = 5;

function toneOf(state: ExecutionWorker['state']): string {
  return state === 'online' ? 'ok' : state === 'stale' ? 'degraded' : 'failed';
}

function WorkRow({ item }: { readonly item: ExecutionQueueItem }) {
  return (
    <>
      <Link href={routes.project(item.project_uid)}>{item.project_name}</Link>
      {' · '}
      <Link href={routes.document(item.project_uid, item.document_uid)}>{item.document_name}</Link>
      {' · '}
      <Link href={routes.version(item.project_uid, item.version_uid)}>{`Версия ${item.version_ordinal}`}</Link>
    </>
  );
}

export function WorkersOverviewSections({
  workers, workersPartial, jobs, jobsPartial = false, processesHref, onOpenProcesses,
}: WorkersOverviewSectionsProps) {
  const attention = attentionItems(workers, jobs ?? []);
  const next = nextJobs(jobs ?? [], NEXT_LIMIT);
  const online = workers.filter((worker) => worker.state !== 'offline');
  return (
    <div className={styles.sections} data-workers-overview-sections="">
      <section className={styles.block} aria-label="Вычислительные узлы" data-overview-nodes="">
        <h3 className={styles.title}>
          Вычислительные узлы
          {processesHref === undefined ? null : (
            <a
              className={styles.more}
              href={processesHref}
              onClick={onOpenProcesses === undefined ? undefined : (event) => { event.preventDefault(); onOpenProcesses(); }}
            >
              Все исполнители →
            </a>
          )}
        </h3>
        {online.length === 0 ? (
          <p className={styles.empty}>Исполнителей на связи нет.</p>
        ) : (
          <ul className={styles.rows}>
            {online.map((worker) => (
              <li key={worker.worker_id} className={styles.row} data-overview-node={worker.state}>
                <span className={`am-badge am-badge--${toneOf(worker.state)}`}>
                  <span className="am-badge__label">{workerStateLabel(worker.state)}</span>
                </span>
                <code className={styles.id}>{worker.worker_id}</code>
                <span>Слотов: {worker.slots} (занято {worker.current_run_ids.length})</span>
                <span className={styles.quiet}>Сигнал: <time dateTime={worker.heartbeat_at}>{formatInstant(worker.heartbeat_at)}</time></span>
              </li>
            ))}
          </ul>
        )}
        {workersPartial ? <p className={styles.quiet}>По первой странице исполнителей.</p> : null}
      </section>
      {jobs === undefined ? null : (
        <section className={styles.block} aria-label="Ближайшие проверки" data-overview-next="">
          <h3 className={styles.title}>
            Очередь — ближайшие проверки
            <a className={styles.more} href={routes.queue()}>Открыть всю очередь →</a>
          </h3>
          {next.length === 0 ? (
            <p className={styles.empty}>Ожидающих задач нет.</p>
          ) : (
            <ol className={styles.rows}>
              {next.map((item) => (
                <li key={item.job_id} className={styles.row} data-overview-next-job={item.queue_position ?? ''}>
                  {item.queue_position === undefined ? null : <strong>№ {item.queue_position}</strong>}
                  <span className={styles.work}><WorkRow item={item} /></span>
                  <span className={styles.quiet}>Принята: <time dateTime={item.created_at}>{formatInstant(item.created_at)}</time></span>
                </li>
              ))}
            </ol>
          )}
          {jobsPartial ? <p className={styles.quiet}>По первой странице очереди.</p> : null}
        </section>
      )}
      <section className={styles.block} aria-label="Требует внимания" data-overview-attention="">
        <h3 className={styles.title}>Требует внимания</h3>
        {attention.length === 0 ? (
          <p className={styles.ok} data-overview-attention-none="">✓ Проблем не обнаружено</p>
        ) : (
          <ul className={styles.rows}>
            {attention.map((entry) => entry.kind === 'worker' ? (
              <li key={entry.worker.worker_id} className={styles.row} data-overview-attention-worker="">
                <span className="am-badge am-badge--degraded"><span className="am-badge__label">Не отвечает</span></span>
                <span>Исполнитель <code className={styles.id}>{entry.worker.worker_id}</code></span>
                <span className={styles.quiet}>
                  последний сигнал <time dateTime={entry.worker.heartbeat_at}>{formatInstant(entry.worker.heartbeat_at)}</time>
                </span>
              </li>
            ) : (
              <li key={entry.item.job_id} className={styles.row} data-overview-attention-job={entry.item.state}>
                <span className="am-badge am-badge--failed"><span className="am-badge__label">{entry.item.state === 'failed' ? 'Ошибка' : 'Остановлена после повторов'}</span></span>
                <span className={styles.work}><WorkRow item={entry.item} /></span>
                <AttentionReason item={entry.item} />
                <Link href={routes.run(entry.item.project_uid, entry.item.run_id)}>Открыть прогон</Link>
              </li>
            ))}
          </ul>
        )}
        {jobsPartial || workersPartial ? <p className={styles.quiet}>По первым страницам исполнителей и очереди.</p> : null}
      </section>
    </div>
  );
}

function AttentionReason({ item }: { readonly item: ExecutionQueueItem }) {
  const error = queueItemError(item);
  if (error === null) return null;
  return <span className={styles.quiet}>{error.sentence ?? <code>{error.code}</code>}</span>;
}
