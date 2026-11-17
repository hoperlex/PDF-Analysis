'use client';

/**
 * The one line about the listing being read to its end, and the batch panel that «Запустить все» opens (`R-151c`, `UI-A-35`,
 * `UIP-S02-06`, `UIP-DEBT-02`).
 *
 * **The choosing is the header's** (`UIP-S02-01`, `SectionHeader`) **and the start is the bottom bar's** (`UIP-S02-03`,
 * `SectionSelectionBar`). What stays here, over the cards: while the listing's pages are being read to their end (`useListingWalk`) the
 * row says so, and when one cannot be read it says that and offers to try again, once — the walk is one, and the two things that wait
 * for it, the groups of the cards (every reader's) and the choosing of whole-section documents (an expert's), share this line — and the
 * existing batch panel, which holds the estimate and the ONE consent for the batch (it stays on the server, `BatchStartPanel`; it is a
 * dialog of the shared layer, so where it stands in the page is no matter). Nothing once the listing is known whole.
 */

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { BatchStartPanel } from '@/features/start-run';
import type { BatchSelection } from '@/widgets/project-sections';

import type { ListingWalk } from '../model/use-listing-walk';
import styles from './section-detail-page.module.css';

export interface SectionBatchBarProps {
  readonly projectUid: ProjectUid;
  readonly selection: BatchSelection;
  /** Not read any more: the row says only whether the listing is read, and what is chosen from it is the header's to count. */
  readonly pageDocuments?: readonly DocumentVersion[];
  /** The listing read to its end, or `idle` when the page is all of it. */
  readonly walk: ListingWalk;
}

export function SectionBatchBar({ projectUid, selection, walk }: SectionBatchBarProps) {
  // The groups are every reader's; the choosing, only the one who may start an audit, so only that reader is told it waits.
  const mayChoose = selection.selection !== undefined;
  return (
    <>
      {walk.status === 'pending' ? (
        <p className={styles.batchBar} role="status" data-listing-walk="pending">
          <span className={styles.batchNote}>Читаю все страницы раздела…</span>
        </p>
      ) : null}
      {walk.status === 'failed' ? (
        <p className={styles.batchBar} role="status" data-listing-walk="failed">
          <span className={styles.batchNote}>
            Не удалось прочитать все страницы раздела: группы не показаны{mayChoose ? ', выбрать документы целиком пока нельзя' : ''}.
          </span>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={walk.retry}>
            Повторить
          </button>
        </p>
      ) : null}
      {selection.batch === null ? null : (
        <BatchStartPanel projectUid={projectUid} entries={selection.batch} onClose={selection.closeBatch} />
      )}
    </>
  );
}
