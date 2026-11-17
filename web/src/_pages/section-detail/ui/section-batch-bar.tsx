'use client';

/**
 * The start of the documents a reader chose together, and the notes of the listing's reading (`R-151c`, `UI-A-35`).
 *
 * **The choosing moved to the section's header** (`UIP-S02-01`, `SectionHeader`): the box «(N)», «Выделить необработанные», the plaque
 * «ждут решения N» and «Снять выделение» sit in its one line. This row keeps what is not a choice: the start of the chosen documents
 * and the existing batch panel (one consent per run stays on the server, `BatchStartPanel`), and the words about the reading —
 * while the listing's pages are being read to their end (`useListingWalk`) the row says so, and when one cannot be read it says that
 * and offers to try again; the header's controls choose nothing from a part of the section.
 */

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { BatchStartPanel } from '@/features/start-run';
import type { BatchSelection } from '@/widgets/project-sections';

import type { ListingWalk } from '../model/use-listing-walk';
import { sectionChoices } from '../model/section-choices';
import styles from './section-detail-page.module.css';

export interface SectionBatchBarProps {
  readonly projectUid: ProjectUid;
  readonly selection: BatchSelection;
  /** The cards in front of the reader: the whole listing when it fits one page. */
  readonly pageDocuments: readonly DocumentVersion[];
  /** The listing read to its end, or `idle` when the page is all of it. */
  readonly walk: ListingWalk;
}

export function SectionBatchBar({ projectUid, selection, pageDocuments, walk }: SectionBatchBarProps) {
  const choices = sectionChoices(pageDocuments, walk);
  // Nothing to say once the listing is known to hold no startable card; while it is still being read, the row waits.
  const visible = selection.selection !== undefined && (choices === null || choices.all.length > 0);
  return (
    <>
      {!visible ? null : (
        <p className={styles.batchBar} data-batch-controls="" data-batch-selection={selection.chosenCount} data-batch-scope={walk.status === 'idle' ? 'page' : 'section'}>
          {selection.chosenCount === 0 ? null : (
            <button type="button" className="am-button am-button--small" onClick={selection.openBatch}>
              Запустить аудит ({selection.chosenCount})
            </button>
          )}
          {walk.status === 'pending' ? (
            <span role="status" className={styles.batchNote} data-batch-walk="pending">
              Читаю все страницы раздела, чтобы выбрать документы целиком.
            </span>
          ) : null}
          {walk.status === 'failed' ? (
            <span role="status" className={styles.batchNote} data-batch-walk="failed">
              Не удалось прочитать все страницы раздела: выбрать документы целиком пока нельзя.{' '}
              <button type="button" className="am-button am-button--quiet am-button--small" onClick={walk.retry}>
                Повторить
              </button>
            </span>
          ) : null}
        </p>
      )}
      {selection.batch === null ? null : (
        <BatchStartPanel projectUid={projectUid} entries={selection.batch} onClose={selection.closeBatch} />
      )}
    </>
  );
}
