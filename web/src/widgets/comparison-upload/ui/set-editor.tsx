/**
 * One proposed set of a comparison upload, for the reader to confirm or change (`frontend/static/js/version-comparison.js:468-500`,
 * `version-comparison-batch.js:80-120`): its designation, where its versions go, its warnings, its files in the order they will
 * be compared with a label for each, and the commands the set allows — «Подтвердить состав и порядок», «Исключить», «Повторить».
 *
 * The reader proposes; nothing is admitted as a version until a set is confirmed, and nothing here guesses a stage, a section or
 * a document (`CMP-INGEST-01` section 2.3). A file moves up and down inside its set; it does not move to another set, because the
 * confirmation names exactly the set's own files. {@link SetEditor} is controlled: the draft lives with the dialog, so «Подтвердить
 * группировку и порядок» can confirm every set with what the reader changed.
 */

import type { ComparisonProposalSet } from '@/shared/api';
import {
  PROPOSAL_WARNING_LABELS,
  SET_STATUS_LABELS,
  canConfirmSet,
  canExcludeSet,
  canRetrySet,
  uploadFailureReasonSentence,
} from '@/entities/version-series';
import { sectionTitleOf, stageChoiceText, uploadConstraintSentence } from '@/entities/document-version';

import type { SetDraft } from '../model/confirm';
import { moveFile, relabel } from '../model/confirm';
import styles from './comparison-upload.module.css';

export interface SetEditorProps {
  readonly set: ComparisonProposalSet;
  readonly draft: SetDraft;
  /** The names the files were declared with, by file identity (a hint, never an identity). */
  readonly fileNames: ReadonlyMap<string, string>;
  /** In the batch dialog a set is confirmed on its own; in the single one the dialog confirms them all. */
  readonly perSet: boolean;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly onDraft: (draft: SetDraft) => void;
  readonly onConfirm: () => void;
  readonly onExclude: () => void;
  readonly onRetry: () => void;
}

export function SetEditor({ set, draft, fileNames, perSet, mayAct, busy, onDraft, onConfirm, onExclude, onRetry }: SetEditorProps) {
  const editable = canConfirmSet(set.state) && mayAct;
  const reason = uploadFailureReasonSentence(set.failure_reason, uploadConstraintSentence);
  return (
    <section className={styles.set} aria-label="Комплект загрузки" data-set-id={set.set_id} data-set-state={set.state}>
      <header className={styles.setHeader}>
        <strong>{draft.designation === '' ? 'Комплект без шифра' : draft.designation}</strong>
        <span className="am-badge am-badge--inert" data-set-status={set.state}>
          {SET_STATUS_LABELS[set.state]}
        </span>
        <span className={styles.note}>файлов: {set.files.length}</span>
      </header>
      {(set.warnings ?? []).map((warning) => (
        <p key={warning} className={styles.warning} role="note" data-proposal-warning={warning}>
          ⚠ {PROPOSAL_WARNING_LABELS[warning]}
        </p>
      ))}
      {reason === '' ? null : (
        <p className={styles.warning} role="alert" data-failure-reason={set.failure_reason}>
          {reason}
        </p>
      )}
      {set.project_stage !== undefined && set.section_code !== undefined ? (
        <p className={styles.note}>
          Предложено: стадия {stageChoiceText(set.project_stage)}, раздел «{sectionTitleOf(set.section_code)}».
          {editable ? (
            <label className={styles.inline}>
              <input
                type="checkbox"
                checked={draft.confirmClassification}
                onChange={(event) => onDraft({ ...draft, confirmClassification: event.target.checked })}
              />{' '}
              подтвердить их вместе с комплектом
            </label>
          ) : null}
        </p>
      ) : null}
      {editable ? (
        <div className={styles.fields}>
          <label className={styles.field}>
            Шифр комплекта
            <input type="text" value={draft.designation} onChange={(event) => onDraft({ ...draft, designation: event.target.value })} />
          </label>
          <label className={styles.field}>
            Куда загрузить
            <select
              value={draft.addToExisting ? 'existing' : 'new'}
              onChange={(event) => onDraft({ ...draft, addToExisting: event.target.value === 'existing' })}
            >
              <option value="new">Новый проект со всеми версиями</option>
              {set.existing_document_uid === undefined ? null : <option value="existing">Добавить версии в существующий комплект</option>}
            </select>
          </label>
        </div>
      ) : null}
      <div className={styles.scroller}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">№</th>
              <th scope="col">Файл</th>
              <th scope="col">Метка версии</th>
              {editable ? (
                <th scope="col">
                  <span className={styles.visuallyHidden}>Порядок</span>
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {draft.files.map((file, index) => (
              <tr key={file.fileId}>
                <td>{index + 1}</td>
                <td className={styles.fileName}>{fileNames.get(file.fileId) ?? '—'}</td>
                <td>
                  {editable ? (
                    <input
                      type="text"
                      value={file.label}
                      aria-label={`Метка версии ${index + 1}`}
                      onChange={(event) => onDraft(relabel(draft, index, event.target.value))}
                    />
                  ) : (
                    file.label || '—'
                  )}
                </td>
                {editable ? (
                  <td>
                    <button
                      type="button"
                      className="am-button am-button--small am-button--quiet"
                      disabled={index === 0}
                      aria-label={`Поднять файл ${index + 1} выше`}
                      onClick={() => onDraft(moveFile(draft, index, -1))}
                    >
                      ↑
                    </button>{' '}
                    <button
                      type="button"
                      className="am-button am-button--small am-button--quiet"
                      disabled={index === draft.files.length - 1}
                      aria-label={`Опустить файл ${index + 1} ниже`}
                      onClick={() => onDraft(moveFile(draft, index, 1))}
                    >
                      ↓
                    </button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {mayAct ? (
        <p className={styles.actions}>
          {perSet && canConfirmSet(set.state) ? (
            <button type="button" className="am-button am-button--small" disabled={busy} onClick={onConfirm}>
              Подтвердить состав и порядок
            </button>
          ) : null}
          {canExcludeSet(set.state) ? (
            <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} onClick={onExclude}>
              Исключить
            </button>
          ) : null}
          {canRetrySet(set.state) ? (
            <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} onClick={onRetry}>
              Повторить
            </button>
          ) : null}
        </p>
      ) : null}
    </section>
  );
}
