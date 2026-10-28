'use client';

/**
 * The sheet matrix «Лист \ версия» (`frontend/static/js/version-comparison.js:347-430`): the versions as columns in
 * the comparison order, the sheets as rows, «только изменения», the choice of the sides A and B, the row heads with
 * the status of their pair, the cells, and the row «Несвязанные страницы».
 *
 * The matrix is the server's effective matrix (the algorithm, then accepted AI links, then manual edits; a manual
 * edit wins, ADR-0025 decision 3). A row is valid within one revision only, so nothing here keeps a row between
 * reads. While a batch is being applied the table is `inert`, as the original's is. Manual gestures turn into
 * draft edits (`matrix-edits`) and are applied in one batch from the header; they never change a cell on their own.
 */

import type {
  ComparisonMatrix,
  ComparisonMatrixCandidate,
  ComparisonMatrixCell,
  ComparisonMatrixRow,
  ComparisonPageRef,
  ComparisonSheetPair,
} from '@/shared/api';
import type { GestureResult, Sides } from '@/entities/version-series';
import {
  DRAG_TYPE,
  PAIR_STATE_LABELS,
  PERMIT_HEADING,
  PERMIT_STATE_LABELS,
  SHEET_STATUS_BADGES,
  UNDESCRIBED_FAILURE,
  changedRows,
  dropOnCell,
  linkCandidate,
  markAbsent,
  pageKey,
  pairReasonWords,
  partsLine,
  pairOfRow,
  parseDragged,
  rowHeading,
  unlinkSheet,
  dragPayload,
} from '@/entities/version-series';

import { MatrixCellView, Thumb } from './matrix-cell';
import styles from './version-series.module.css';

export const NO_PAIR_FOR_CHANGES =
  'Для выбранной пары «было → стало» нет посчитанного перехода: «только изменения» станет доступно, когда он будет готов.';

export interface SheetMatrixProps {
  readonly matrix: ComparisonMatrix;
  /** The names of the versions in the comparison order: «V1», «V2». */
  readonly names: ReadonlyMap<string, string>;
  /** What a column's head says on hover: the file the version came from. */
  readonly titles: ReadonlyMap<string, string>;
  readonly sides: Sides;
  readonly onSide: (side: 'a' | 'b', versionUid: string) => void;
  /** The pairs of the chosen transition A → B; `null` when it has none. */
  readonly pairs: readonly ComparisonSheetPair[] | null;
  readonly onlyChanged: boolean;
  readonly onOnlyChanged: (on: boolean) => void;
  readonly touched: ReadonlySet<string>;
  readonly mayEdit: boolean;
  /** A batch is being applied: the table takes no input. */
  readonly locked: boolean;
  readonly onGesture: (result: GestureResult) => void;
  readonly onSheet: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell) => void;
  readonly onOpenPair: (pair: ComparisonSheetPair) => void;
}

function UnassignedRow({
  matrix,
  mayEdit,
}: {
  readonly matrix: ComparisonMatrix;
  readonly mayEdit: boolean;
}) {
  const pages = matrix.unassigned_pages ?? [];
  if (pages.length === 0) return null;
  const columns = matrix.columns ?? [];
  return (
    <tr className={styles.unassigned}>
      <th scope="row" className={styles.rowHead}>
        Несвязанные страницы
      </th>
      {columns.map((column) => (
        <td key={column.version_uid} className={styles.cell}>
          {pages
            .filter((page) => page.version_uid === column.version_uid)
            .map((page: ComparisonPageRef) => (
              <div
                key={pageKey(page)}
                className={styles.thumbSmall}
                draggable={mayEdit}
                data-unassigned-page={page.page_number}
                onDragStart={(event) => {
                  event.dataTransfer.setData(DRAG_TYPE, dragPayload(page));
                  event.dataTransfer.effectAllowed = 'move';
                }}
              >
                <Thumb page={page} small />
                <div className={styles.thumbMeta}>стр.{page.page_number}</div>
              </div>
            ))}
        </td>
      ))}
    </tr>
  );
}

/**
 * What the series says of a pair beside its status (`CMP-SERIES-01`): the reasons for a review, the part of a split sheet, the
 * pair's dependence on an AI link, the declared changes of the permit and how each fared, and a failure.
 */
function PairDetails({ pair }: { readonly pair: ComparisonSheetPair }) {
  const reasons = pair.reasons ?? [];
  const parts = pair.parts;
  const permit = pair.permit;
  if (reasons.length === 0 && parts === undefined && permit === undefined && pair.ai_dependent !== true && pair.state !== 'failed') {
    return null;
  }
  return (
    <div className={styles.pairNote} data-pair-details="">
      {reasons.length === 0 ? null : (
        <div>
          причины:{' '}
          {reasons.map((code, index) => (
            <span key={code} data-pair-reason={code}>
              {index === 0 ? '' : '; '}
              {pairReasonWords(code)}
            </span>
          ))}
        </div>
      )}
      {pair.ai_dependent === true && !reasons.includes('AI_MATCH') ? <div>пара опирается на связь, предложенную ИИ</div> : null}
      {parts === undefined ? null : <div data-part-role={parts.role}>{partsLine(parts)}</div>}
      {permit === undefined ? null : (
        <div data-permit-state={permit.state}>
          {PERMIT_HEADING}: {PERMIT_STATE_LABELS[permit.state]}
          {(permit.items ?? []).length === 0 ? null : (
            <ul className={styles.pairList}>
              {(permit.items ?? []).map((item, index) => (
                <li key={`${index}-${item.text}`} data-permit-state={item.state}>
                  {item.text} — {PERMIT_STATE_LABELS[item.state]}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {pair.state === 'failed' ? (
        <div className={styles.errorText} {...(pair.failure_reason === undefined ? {} : { 'data-failure-reason': pair.failure_reason })}>
          ошибка расчёта{pair.failure_reason === undefined ? '' : `: ${UNDESCRIBED_FAILURE}`}
        </div>
      ) : null}
    </div>
  );
}

function RowStatus({
  pair,
  onOpenPair,
}: {
  readonly pair: ComparisonSheetPair | null;
  readonly onOpenPair: (pair: ComparisonSheetPair) => void;
}) {
  if (pair === null) return null;
  if (pair.status === undefined) {
    return (
      <>
        <span className={styles.note} data-pair-state={pair.state}>
          {PAIR_STATE_LABELS[pair.state]}
        </span>
        <PairDetails pair={pair} />
      </>
    );
  }
  const badge = SHEET_STATUS_BADGES[pair.status];
  return (
    <>
      <button
        type="button"
        className={`am-badge am-badge--${badge.tone} ${styles.statusBadge}`}
        data-sheet-status={pair.status}
        data-pair-state={pair.state}
        title="Открыть сравнение этого листа в выбранной паре: наложение, было, стало и рядом."
        onClick={() => onOpenPair(pair)}
      >
        {badge.icon} {badge.label}
      </button>
      <PairDetails pair={pair} />
    </>
  );
}

export function SheetMatrix({
  matrix,
  names,
  titles,
  sides,
  onSide,
  pairs,
  onlyChanged,
  onOnlyChanged,
  touched,
  mayEdit,
  locked,
  onGesture,
  onSheet,
  onOpenPair,
}: SheetMatrixProps) {
  const columns = matrix.columns ?? [];
  const allRows = matrix.rows ?? [];
  const hasPairs = pairs !== null && pairs.length > 0;
  const rows = onlyChanged && hasPairs ? changedRows(allRows, sides, pairs) : allRows;
  return (
    <div className={styles.matrixWrap}>
      <table
        className={styles.matrix}
        aria-busy={locked}
        {...(locked ? { inert: true } : {})}
        data-comparison-matrix=""
      >
        <thead>
          <tr>
            <th scope="col" className={styles.rowHead}>
              <span>Лист \ версия</span>
              <label className={styles.onlyChanged} title={hasPairs ? 'Скрыть листы без изменений в выбранной паре «было → стало».' : NO_PAIR_FOR_CHANGES}>
                <input type="checkbox" checked={onlyChanged && hasPairs} disabled={!hasPairs} onChange={(event) => onOnlyChanged(event.target.checked)} />
                {' '}только изменения
                {onlyChanged && hasPairs ? <span className={styles.note}> ({rows.length} из {allRows.length})</span> : null}
              </label>
            </th>
            {columns.map((column) => (
              <th
                key={column.version_uid}
                scope="col"
                className={column.version_uid === sides.a ? styles.headA : column.version_uid === sides.b ? styles.headB : styles.head}
              >
                <div className={styles.colLabel} title={titles.get(column.version_uid)}>
                  Версия {names.get(column.version_uid) ?? '№?'}
                  <span className={styles.note}> · стр. {column.page_count}</span>
                </div>
                <div className={styles.pick}>
                  <button
                    type="button"
                    className="am-button am-button--small am-button--quiet"
                    aria-pressed={column.version_uid === sides.a}
                    title="Сделать эту версию стороной «было» выбранной пары."
                    onClick={() => onSide('a', column.version_uid)}
                  >
                    Было
                  </button>
                  <button
                    type="button"
                    className="am-button am-button--small am-button--quiet"
                    aria-pressed={column.version_uid === sides.b}
                    title="Сделать эту версию стороной «стало» выбранной пары."
                    onClick={() => onSide('b', column.version_uid)}
                  >
                    Стало
                  </button>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const heading = rowHeading(row);
            const pair = pairs === null ? null : pairOfRow(row, sides, pairs);
            return (
              <tr key={row.row_id} data-row-id={row.row_id}>
                <th scope="row" className={styles.rowHead}>
                  <div className={styles.rowTitle}>{heading.title === '' ? 'Лист без названия' : heading.title}</div>
                  {heading.number === '' ? null : <div className={styles.note}>лист {heading.number}</div>}
                  <RowStatus pair={pair} onOpenPair={onOpenPair} />
                </th>
                {row.cells.map((cell) => (
                  <MatrixCellView
                    key={cell.version_uid}
                    row={row}
                    cell={cell}
                    versionName={names.get(cell.version_uid) ?? '№?'}
                    touched={touched}
                    mayEdit={mayEdit}
                    side={cell.version_uid === sides.a ? 'a' : cell.version_uid === sides.b ? 'b' : null}
                    onSheet={onSheet}
                    onUnlink={(r, c) => (c.page === undefined ? undefined : onGesture(unlinkSheet(r, c.page)))}
                    onLink={(r, c, candidate: ComparisonMatrixCandidate) => onGesture(linkCandidate(r, c.version_uid, candidate))}
                    onAbsent={(r, c) => onGesture(markAbsent(r, c.version_uid))}
                    onDropped={(r, c, text) => {
                      const dragged = parseDragged(text);
                      if (dragged !== null) onGesture(dropOnCell(r, c.version_uid, dragged));
                    }}
                  />
                ))}
              </tr>
            );
          })}
          <UnassignedRow matrix={matrix} mayEdit={mayEdit} />
        </tbody>
      </table>
    </div>
  );
}
