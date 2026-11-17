'use client';

/**
 * The bottom bar of a section's selection (`UIP-S02-03`, the original's «Выбрано: N · Запустить все (N)»; `UIP-S02-04`, «В архив (N)»).
 *
 * While at least one card is chosen the bar sticks to the bottom of the area: «Выбрано: N», «Запустить все (N)», «В архив (N)» and
 * «Снять выделение». «Запустить все» opens the existing batch panel (`SectionBatchBar` holds it) — the estimate and the ONE consent for
 * the batch, which stay on the server (`R-151c`, `BatchStartPanel`); no native window is involved. The bar is the last thing of the page,
 * so scrolled to its end it stands after the last row and covers no card, and the page keeps room under the cards while it is drawn; it is
 * plain buttons in the order of the page, so the keyboard reaches it, and its count is a live status. It is drawn for whoever may start an
 * audit and only while something is chosen: `BatchSelection.selection` is `undefined` for a session that cannot start one, and while the
 * batch panel holds the choice.
 *
 * **«В архив (N)»** (`UIP-S02-04`, `R-151a`) archives the chosen documents that are not archived yet, one command each under its own key, with
 * no window to confirm — the action is reversible (the document comes back with «Показать архивные» and «Вернуть из архива» on its page) and
 * deletes no version, run or decision. At its end the bar says one thing, «Убрано в архив: k из N», and lists the documents that were
 * refused with the reason of each; the choice stays with those, so the button retries them. The message stays, with a «Закрыть», when
 * nothing is chosen any more. The button is not drawn when every chosen document is archived already.
 *
 * The choosing is the header's (`SectionHeader`); the notes of the listing being read are the row over the cards (`SectionBatchBar`).
 * {@link SectionSelectionBarView} is the bar over what it is told, so a render can draw each of its states; {@link SectionSelectionBar}
 * holds the state of the actions over the documents the page has read (`scope`).
 */

import { archiveReportLine } from '@/features/manage-document';
import type { BatchSelection } from '@/widgets/project-sections';

import type { SectionArchiveView, SectionBulk, SectionBulkScope } from '../model/use-section-bulk';
import { useSectionBulk } from '../model/use-section-bulk';
import styles from './section-selection-bar.module.css';

export interface SectionSelectionBarViewProps {
  readonly selection: BatchSelection;
  /** The actions over the chosen documents; without them the bar starts and clears only. */
  readonly bulk?: SectionBulk | undefined;
}

function ArchiveNotes({ archive }: { readonly archive: SectionArchiveView }) {
  const { report, pending, progress } = archive;
  if (pending) {
    return (
      <p className={styles.note} role="status" data-archive-progress="">
        Убираю в архив{progress === null ? '' : `: ${progress.done} из ${progress.total}`}…
      </p>
    );
  }
  if (report === null) return null;
  const refused = report.failed.length;
  return (
    <div className={styles.report} role="status" data-archive-report={`${report.archived.length}/${report.total}`}>
      <p className={styles.reportLine}>
        {archiveReportLine(report)}
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={archive.onDismiss} data-archive-dismiss="">
          Закрыть
        </button>
      </p>
      {refused === 0 ? null : (
        <ul className={styles.failures}>
          {report.failed.map((failure) => (
            <li key={failure.target.documentUid} data-archive-failed={failure.target.documentUid}>
              <span className={styles.failedTitle}>{failure.target.title}</span>
              {' — '}
              <span className={styles.reason}>{failure.reason}</span>
            </li>
          ))}
        </ul>
      )}
      <p className={styles.note}>
        {refused === 0
          ? 'Версии, прогоны и решения остались; архивные документы видны по «Показать архивные».'
          : 'Выбраны только документы, которые не вышли: «В архив» повторит их. Версии, прогоны и решения не удалены.'}
      </p>
    </div>
  );
}

export function SectionSelectionBarView({ selection, bulk }: SectionSelectionBarViewProps) {
  if (selection.selection === undefined) return null;
  const archive = bulk?.archive;
  const chosen = selection.chosenCount;
  const message = archive !== undefined && (archive.pending || archive.report !== null);
  if (chosen === 0 && !message) return null;
  return (
    <div className={styles.bar} role="region" aria-label="Выбранные документы" data-batch-bar="" data-batch-selection={chosen}>
      {chosen === 0 ? null : (
        <>
          <span className={styles.count} role="status">Выбрано: {chosen}</span>
          <span className={styles.actions}>
            <button type="button" className="am-button am-button--small" onClick={selection.openBatch} data-batch-start="">
              Запустить все ({chosen})
            </button>
            {archive === undefined || archive.count === 0 ? null : (
              <button
                type="button"
                className="am-button am-button--quiet am-button--small"
                disabled={archive.pending}
                onClick={archive.onArchive}
                title="Убрать выбранные документы в архив: версии, прогоны и решения не удаляются"
                data-archive-chosen=""
              >
                В архив ({archive.count})
              </button>
            )}
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={selection.clear} data-clear-selection="">
              Снять выделение
            </button>
          </span>
        </>
      )}
      {archive === undefined || !message ? null : (
        <div className={styles.notes}>
          <ArchiveNotes archive={archive} />
        </div>
      )}
    </div>
  );
}

export interface SectionSelectionBarProps {
  readonly selection: BatchSelection;
  /** What the actions act on: the project and the documents the page has read. Without it the bar starts and clears only. */
  readonly scope?: SectionBulkScope | undefined;
}

function SectionSelectionBarWithActions({ selection, scope }: { readonly selection: BatchSelection; readonly scope: SectionBulkScope }) {
  const bulk = useSectionBulk(scope, selection);
  return <SectionSelectionBarView selection={selection} bulk={bulk} />;
}

export function SectionSelectionBar({ selection, scope }: SectionSelectionBarProps) {
  if (scope === undefined) return <SectionSelectionBarView selection={selection} />;
  return <SectionSelectionBarWithActions selection={selection} scope={scope} />;
}
