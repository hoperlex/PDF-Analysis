/**
 * The state of the matrix as a sentence above it (`frontend/static/js/version-comparison.js:107-116`): not built, being
 * built (with how many pages are read), ready, stale and why, or failed. A stale build is still shown as built, with its
 * rows; this banner is what keeps a reader from taking it for the current one.
 */

import type { ComparisonMatrix } from '@/shared/api';
import { MATRIX_STALE_LABELS, MATRIX_STATE_LABELS, UNDESCRIBED_FAILURE } from '@/entities/version-series';

import styles from './version-series.module.css';

export interface MatrixStateProps {
  readonly matrix: ComparisonMatrix;
  readonly mayPrepare: boolean;
  readonly busy: boolean;
  readonly onPrepare: () => void;
}

export function MatrixState({ matrix, mayPrepare, busy, onPrepare }: MatrixStateProps) {
  if (matrix.state === 'ready') return null;
  const { progress } = matrix;
  const offer = matrix.state === 'absent' || matrix.state === 'stale' || matrix.state === 'failed';
  return (
    <section className={styles.block} role="status" aria-label="Состояние сопоставления">
      <p className={styles.blockHead}>
        <strong>{MATRIX_STATE_LABELS[matrix.state]}.</strong>
        {matrix.state === 'building' ? (
          <span className={styles.muted}>
            Разбор версий: готово {progress.ready} из {progress.total}
            {progress.failed > 0 ? ` · ошибок ${progress.failed}` : ''}
          </span>
        ) : null}
        {mayPrepare && offer ? (
          <button type="button" className="am-button am-button--small" disabled={busy} onClick={onPrepare}>
            Подготовить
          </button>
        ) : null}
      </p>
      {matrix.state === 'stale' && (matrix.stale_reasons ?? []).length > 0 ? (
        <ul className={styles.draftList}>
          {(matrix.stale_reasons ?? []).map((reason) => (
            <li key={reason} data-matrix-stale-reason={reason}>
              {MATRIX_STALE_LABELS[reason]}
            </li>
          ))}
        </ul>
      ) : null}
      {matrix.state === 'failed' && matrix.failure_reason !== undefined ? (
        <p className="am-note" data-failure-reason={matrix.failure_reason}>
          {UNDESCRIBED_FAILURE}
        </p>
      ) : null}
      {matrix.state === 'absent' ? (
        <p className="am-note">Сначала «Подготовить»: система прочитает страницы версий и свяжет листы между ними.</p>
      ) : null}
    </section>
  );
}
