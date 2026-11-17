/**
 * «Сейчас: документ · этап · 21 мин» (`UIP-S15-03`, `Г12-B`): what a server is doing now, one line for each task, at most three and
 * then «и ещё N». The document is a link to its page. It is drawn for an expert and for an administrator alike and names nothing of
 * how the work is done — no model, no provider, no number of a run or a task. A server that does nothing has no such line at all.
 */

import Link from 'next/link';

import { NOW_LABEL, NOW_LIST_LABEL, workMoreSentence } from '@/entities/executor-host';
import type { HostRowReading } from '@/entities/executor-host';
import { routes } from '@/shared/lib';

import { stageWordOf, workAgeOf } from '../model/now';

import styles from './executor-hosts.module.css';

export interface HostNowProps {
  readonly reading: Pick<HostRowReading, 'work' | 'workMore'>;
  /** Epoch milliseconds of the read the card is drawn from; the durations are measured to it. `null`: none are drawn. */
  readonly asOf: number | null;
}

export function HostNow({ reading, asOf }: HostNowProps) {
  if (reading.work.length === 0) return null;
  return (
    <div className={styles.now} data-host-now>
      <span className={styles.nowLabel}>{NOW_LABEL}</span>
      <ul className={styles.nowList} aria-label={NOW_LIST_LABEL}>
        {reading.work.map((item) => {
          const parts = [stageWordOf(item.stageKey), workAgeOf(item.since, asOf)].filter((part): part is string => part !== null);
          return (
            <li key={item.key} className={styles.nowItem} data-host-work>
              <Link href={routes.document(item.projectUid, item.documentUid)}>{item.title}</Link>
              {parts.length === 0 ? null : ` · ${parts.join(' · ')}`}
            </li>
          );
        })}
        {reading.workMore === 0 ? null : <li className={styles.nowMore} data-host-work-more>{workMoreSentence(reading.workMore)}</li>}
      </ul>
    </div>
  );
}
