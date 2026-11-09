'use client';

/**
 * The row under the filters of a section's cards that chooses documents to start together and opens the batch panel
 * (`R-151c`), as the original's bottom bar «Выбрано: N · Запустить все (N)».
 *
 * **«Выбрать все» and «Выбрать не запускавшиеся» choose across the whole listing in view**, not the fifty cards of one page
 * (`UI-A-35`): the listing's pages are followed by their cursor to the end (`useListingWalk`) and the buttons say how many
 * documents they will choose, counted over all of them. Until every page is read the buttons wait and the row says so; if a
 * page cannot be read it says that and offers to try again, and chooses nothing — never a part of the section offered as
 * the whole. A section that fits one page needs no further read and the count is the page's.
 *
 * One consent per run stays on the server (`BatchStartPanel`); this draws the choice and the existing batch panel.
 */

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { BatchStartPanel } from '@/features/start-run';
import { startable } from '@/widgets/project-sections';
import type { BatchSelection } from '@/widgets/project-sections';

import type { ListingWalk } from '../model/use-listing-walk';
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
  const whole: readonly DocumentVersion[] | null =
    walk.status === 'idle' ? pageDocuments : walk.status === 'complete' ? walk.items : null;
  const choices = whole === null ? null : whole.filter(startable);
  const notRun = choices === null ? null : choices.filter((version) => version.audit?.state === 'not_run');
  // Nothing to choose from once the listing is known to hold no startable card; while it is still being read, the row waits.
  const visible = selection.selection !== undefined && (choices === null || choices.length > 0);
  return (
    <>
      {!visible ? null : (
        <p className={styles.batchBar} data-batch-controls="" data-batch-selection={selection.chosenCount} data-batch-scope={walk.status === 'idle' ? 'page' : 'section'}>
          <button
            type="button"
            className="am-button am-button--quiet am-button--small"
            disabled={choices === null}
            onClick={() => choices !== null && selection.choose(choices)}
          >
            {choices === null ? 'Выбрать все…' : `Выбрать все (${choices.length})`}
          </button>
          {notRun === null ? (
            <button type="button" className="am-button am-button--quiet am-button--small" disabled>
              Выбрать не запускавшиеся…
            </button>
          ) : notRun.length === 0 ? null : (
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => selection.choose(notRun)}>
              Выбрать не запускавшиеся ({notRun.length})
            </button>
          )}
          {selection.chosenCount === 0 ? null : (
            <>
              <button type="button" className="am-button am-button--small" onClick={selection.openBatch}>
                Запустить аудит ({selection.chosenCount})
              </button>
              <button type="button" className="am-button am-button--quiet am-button--small" onClick={selection.clear}>
                Снять выбор
              </button>
            </>
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
