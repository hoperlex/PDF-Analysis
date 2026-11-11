'use client';

/** @jsxRuntime automatic */

/**
 * «Рекомендовано снять · N»: the collapsed queue above the list (`PREC-WEB`, plan-v5 sections 2.3 and 6, the owner's «метка + свёрнутая очередь»).
 *
 * It holds the findings the server labelled `cancel_suggested` after the AI critic reviewed them and that still wait for a decision; opening
 * it lists them, each a link to its finding. It is a reference, not an action: nothing is cancelled from here, the expert decides on the
 * finding. With nothing to list it is not drawn at all (a queue that says «0» is a concept with nothing in it).
 */

import type { MouseEvent } from 'react';

import type { Finding, PrecedentFindingLabel } from '@/shared/api';

import styles from './finding-list.module.css';

export interface CancelQueueItem {
  readonly finding: Finding;
  readonly label: PrecedentFindingLabel;
}

export interface CancelQueueProps {
  readonly items: readonly CancelQueueItem[];
  readonly onOpen: (findingUid: string) => void;
}

export function CancelQueue({ items, onOpen }: CancelQueueProps) {
  if (items.length === 0) return null;
  return (
    <details className={`am-note ${styles.queue}`} data-cancel-queue={items.length}>
      <summary className={styles.queueSummary}>Рекомендовано снять · {items.length}</summary>
      <p className={styles.queueHint}>Эксперты почти всегда отклоняли такие находки, и критик их разобрал. Это справка, решаете вы.</p>
      <ul className={styles.queueList}>
        {items.map(({ finding, label }) => (
          <li key={finding.finding_uid} className={styles.queueItem} data-cancel-queue-item={finding.finding_uid}>
            <a
              className={styles.queueText}
              href={`?finding=${encodeURIComponent(finding.finding_uid)}`}
              onClick={(event: MouseEvent<HTMLAnchorElement>) => {
                // A plain press opens the finding in place; a press with a modifier keeps the browser's own link.
                if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                onOpen(finding.finding_uid);
              }}
            >
              {finding.observation.finding_text}
            </a>
            <span className={styles.queueCount}>{label.votes.rejected} из {label.votes.total}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

/**
 * The queue of what is shown: the findings with a `cancel_suggested` label of a critic's review, that still wait for a decision. The caller
 * passes the findings AS SHOWN, after the verdict and severity filters, so a filter that hides the waiting findings leaves the queue empty.
 */
export function cancelQueueOf(
  shown: readonly Finding[],
  precedentOf: ((findingUid: string) => PrecedentFindingLabel | undefined) | undefined,
  isWaiting: (finding: Finding) => boolean,
  isQueued: (label: PrecedentFindingLabel | undefined) => boolean,
): readonly CancelQueueItem[] {
  if (precedentOf === undefined) return [];
  const items: CancelQueueItem[] = [];
  for (const finding of shown) {
    const label = precedentOf(finding.finding_uid);
    if (label !== undefined && isWaiting(finding) && isQueued(label)) items.push({ finding, label });
  }
  return items;
}
