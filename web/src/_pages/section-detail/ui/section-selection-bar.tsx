'use client';

/**
 * The bottom bar of a section's selection (`UIP-S02-03`, the original's «Выбрано: N · Запустить все (N)»; `UIP-S02-04`, «В архив (N)»;
 * `UIP-S02-05`, «Скачать пакеты аудита»).
 *
 * While at least one card is chosen the bar sticks to the bottom of the area: «Выбрано: N», «Запустить все (N)», «Скачать пакеты аудита»,
 * «В архив (N)» and «Снять выделение». «Запустить все» opens the existing batch panel (`SectionBatchBar` holds it) — the estimate and the ONE consent for
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
 * **«Скачать пакеты аудита»** (`UIP-S02-05`, `Г12-B`) builds in the browser one ZIP with the audit package of each chosen document that has a
 * result (the package of «Скачать пакет аудита» on «Разбор»), shows the document it is on and can be cancelled; a document with no result is
 * skipped and listed, and the package keeps its rule: a file missing from any package, no archive. It is a button for the expert like the
 * others, drawn while at least one chosen document has a result (a package is of a result; with none, there is nothing to build and no
 * button). At most 20 documents with a result at a time: where the choice is more, the button is held and the words beside it say why.
 * The choice stays as it is.
 *
 * The choosing is the header's (`SectionHeader`); the notes of the listing being read are the row over the cards (`SectionBatchBar`).
 * {@link SectionSelectionBarView} is the bar over what it is told, so a render can draw each of its states; {@link SectionSelectionBar}
 * holds the state of the actions over the documents the page has read (`scope`).
 */

import { ErrorState } from '@/shared/ui';
import { archiveReportLine } from '@/features/manage-document';
import { AUDIT_PACKAGES_TITLE } from '@/widgets/export-panel';
import type { BatchSelection } from '@/widgets/project-sections';

import type { SectionArchiveView, SectionBulk, SectionBulkScope, SectionPackagesView } from '../model/use-section-bulk';
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

/** What the packages say once they have run: the phase while they build, what the archive holds with the skipped documents, or why not. */
function PackageNotes({ packages }: { readonly packages: SectionPackagesView }) {
  const { pending, status, summary, error } = packages;
  if (pending) {
    return status === null ? null : <p className={styles.note} role="status" data-audit-packages-progress="">{status}</p>;
  }
  if (error !== null) {
    return (
      <div className={styles.report} data-audit-packages-error="">
        <ErrorState {...error} />
        <p className={styles.reportLine}>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={packages.onDismiss} data-audit-packages-dismiss="">
            Закрыть
          </button>
        </p>
      </div>
    );
  }
  if (status === null) return null;
  const skipped = summary?.skipped ?? [];
  return (
    <div className={styles.report} role="status" data-audit-packages-status={summary === null ? 'stopped' : 'done'}>
      <p className={styles.reportLine}>
        {status}
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={packages.onDismiss} data-audit-packages-dismiss="">
          Закрыть
        </button>
      </p>
      {skipped.length === 0 ? null : (
        <ul className={styles.failures} data-audit-packages-skipped={skipped.length}>
          {skipped.map((document) => (
            <li key={document.documentUid} data-audit-packages-skipped-document={document.documentUid}>
              <span className={styles.failedTitle}>{document.title}</span>
              {' — '}
              <span className={styles.note}>нет результата аудита</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function SectionSelectionBarView({ selection, bulk }: SectionSelectionBarViewProps) {
  if (selection.selection === undefined) return null;
  const archive = bulk?.archive;
  const packages = bulk?.packages;
  const chosen = selection.chosenCount;
  const archiveMessage = archive !== undefined && (archive.pending || archive.report !== null);
  const packagesMessage = packages !== undefined && (packages.pending || packages.status !== null || packages.error !== null);
  // A package is of a result: with no chosen document that has one there is nothing to build, so the button is not drawn (a build already
  // running keeps its button, to be cancelled).
  const packagesButton = packages !== undefined && (packages.count > 0 || packages.pending);
  if (chosen === 0 && !archiveMessage && !packagesMessage) return null;
  return (
    <div className={styles.bar} role="region" aria-label="Выбранные документы" data-batch-bar="" data-batch-selection={chosen}>
      {chosen === 0 ? null : (
        <>
          <span className={styles.count} role="status">Выбрано: {chosen}</span>
          <span className={styles.actions}>
            <button type="button" className="am-button am-button--small" onClick={selection.openBatch} data-batch-start="">
              Запустить все ({chosen})
            </button>
            {packages === undefined || !packagesButton ? null : (
              <>
                <button
                  type="button"
                  className="am-button am-button--quiet am-button--small"
                  disabled={packages.pending || packages.refusal !== null}
                  onClick={packages.onDownload}
                  title={packages.refusal ?? AUDIT_PACKAGES_TITLE}
                  data-audit-packages=""
                >
                  {packages.pending ? 'Собираю пакеты…' : 'Скачать пакеты аудита'}
                </button>
                {!packages.pending ? null : (
                  <button type="button" className="am-button am-button--quiet am-button--small" onClick={packages.onCancel} data-audit-packages-cancel="">
                    Отменить
                  </button>
                )}
              </>
            )}
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
      {chosen === 0 || packages === undefined || !packagesButton || packages.refusal === null || packages.pending ? null : (
        <p className={`${styles.note} ${styles.wide}`} data-audit-packages-refusal="">{packages.refusal}</p>
      )}
      {!archiveMessage && !packagesMessage ? null : (
        <div className={styles.notes}>
          {archive === undefined ? null : <ArchiveNotes archive={archive} />}
          {packages === undefined ? null : <PackageNotes packages={packages} />}
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
