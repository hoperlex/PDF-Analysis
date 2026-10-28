/**
 * The draft of manual edits, the history of the saved ones, and the edits that no longer apply
 * (`frontend/static/js/version-comparison.js:425-429`, ADR-0025 decision 14).
 *
 * Nothing a reader does in the matrix changes it at once: a drag, «Связать», «⤫» and «Отметить, что этого листа в
 * версии нет» add a line here, and «Применить сопоставления (N)» sends all of them in one batch. A line can be taken
 * out. When the matrix moved under the draft the lines that no longer fit it are listed here, not dropped in silence.
 * The history below is the append-only record of saved edits, with the ones a reorder left without cells marked as
 * such: they are kept, never applied quietly and never hidden.
 */

import type { ComparisonMatrixEdit, ComparisonMatrixEditId, ComparisonPageRef } from '@/shared/api';
import type { ComparisonFailure, Draft, DraftEdit } from '@/entities/version-series';
import {
  EDIT_KIND_LABELS,
  EDIT_SOURCE_LABELS,
  EDIT_STATUS_LABELS,
  describeEdit,
} from '@/entities/version-series';

import { CommandRefusal } from './module-state';
import styles from './version-series.module.css';

export interface DraftPanelProps {
  readonly draft: Draft;
  readonly names: ReadonlyMap<string, string>;
  /** A gesture that was refused before it entered the draft, or the word on a rebase. */
  readonly notice: string | null;
  /** The edits the last rebase took out of the draft. */
  readonly dropped: readonly DraftEdit[];
  readonly failure: ComparisonFailure | null;
  readonly busy: boolean;
  readonly onRemove: (index: number) => void;
}

function nameOf(names: ReadonlyMap<string, string>) {
  return (versionUid: string): string => names.get(versionUid) ?? '№?';
}

export function DraftPanel({ draft, names, notice, dropped, failure, busy, onRemove }: DraftPanelProps) {
  const name = nameOf(names);
  if (draft.edits.length === 0 && notice === null && dropped.length === 0 && failure === null) return null;
  return (
    <section className={styles.draft} aria-label="Черновик правок" data-draft-edits={draft.edits.length}>
      {draft.edits.length === 0 ? null : (
        <>
          <p>
            <strong>Выбрано правок: {draft.edits.length}.</strong> Примените сопоставления или нажмите кнопку сравнения
            после всех правок.
          </p>
          <ol className={styles.draftList}>
            {draft.edits.map((edit, index) => (
              <li key={`${edit.kind}-${index}`} data-draft-kind={edit.kind}>
                {describeEdit(edit, name)}{' '}
                <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} onClick={() => onRemove(index)}>
                  Убрать
                </button>
              </li>
            ))}
          </ol>
        </>
      )}
      {dropped.length === 0 ? null : (
        <div role="status" data-draft-dropped={dropped.length}>
          <p>Эти правки не подходят к сопоставлению, которое изменилось, и убраны из черновика ({dropped.length}):</p>
          <ul className={styles.draftList}>
            {dropped.map((edit, index) => (
              <li key={`${edit.kind}-${index}`}>{describeEdit(edit, name)}</li>
            ))}
          </ul>
        </div>
      )}
      {notice === null ? null : (
        <p className="am-note" role="status" data-draft-notice="">
          {notice}
        </p>
      )}
      <CommandRefusal failure={failure} />
    </section>
  );
}

function pageText(page: ComparisonPageRef, name: (versionUid: string) => string): string {
  return `лист ${page.page_number} (версия ${name(page.version_uid)})`;
}

function editLine(edit: ComparisonMatrixEdit, name: (versionUid: string) => string): string {
  switch (edit.kind) {
    case 'link':
      return edit.page !== undefined && edit.other_page !== undefined
        ? `${pageText(edit.other_page, name)} ↔ ${pageText(edit.page, name)}`
        : '';
    case 'unlink':
      return edit.page === undefined ? '' : pageText(edit.page, name);
    case 'mark_absent':
      return edit.page !== undefined && edit.absent_version_uid !== undefined
        ? `${pageText(edit.page, name)}: в версии ${name(edit.absent_version_uid)} листа нет`
        : '';
    case 'undo':
      return edit.undoes_edit_id === undefined ? '' : 'снимает предыдущую правку';
  }
}

export interface EditHistoryProps {
  readonly edits: readonly ComparisonMatrixEdit[];
  readonly orphanedIds: readonly ComparisonMatrixEditId[];
  readonly names: ReadonlyMap<string, string>;
}

export const ORPHANED_NOTE =
  'Эти правки сохранены, но больше не применяются: листов, о которых они, нет в текущем порядке версий. Они не удалены и ничего не меняют.';

/** The edits that no longer apply, always in view, and the whole history behind a disclosure. */
export function EditHistory({ edits, orphanedIds, names }: EditHistoryProps) {
  const name = nameOf(names);
  const orphaned = new Set(orphanedIds);
  const lost = edits.filter((edit) => edit.status === 'orphaned' || orphaned.has(edit.edit_id));
  const unknown = orphanedIds.filter((id) => !edits.some((edit) => edit.edit_id === id));
  return (
    <>
      {lost.length === 0 && unknown.length === 0 ? null : (
        <section className={styles.draft} aria-label="Правки, которые больше не применяются" data-orphaned-edits={lost.length + unknown.length}>
          <p>
            <strong>Правки, которые больше не применяются ({lost.length + unknown.length}).</strong> {ORPHANED_NOTE}
          </p>
          <ul className={styles.draftList}>
            {lost.map((edit) => (
              <li key={edit.edit_id} data-edit-status={edit.status} data-edit-kind={edit.kind}>
                №{edit.edit_no} · {EDIT_KIND_LABELS[edit.kind]}: {editLine(edit, name)}
              </li>
            ))}
          </ul>
        </section>
      )}
      {edits.length === 0 ? null : (
        <details className={styles.history} data-edit-history={edits.length}>
          <summary>История правок ({edits.length})</summary>
          <ol className={styles.draftList}>
            {edits.map((edit) => (
              <li
                key={edit.edit_id}
                data-edit-kind={edit.kind}
                data-edit-status={edit.status}
                data-edit-source={edit.source}
              >
                №{edit.edit_no} · {EDIT_KIND_LABELS[edit.kind]}: {editLine(edit, name)} · {EDIT_STATUS_LABELS[edit.status]} ·{' '}
                {EDIT_SOURCE_LABELS[edit.source]}
              </li>
            ))}
          </ol>
        </details>
      )}
    </>
  );
}
