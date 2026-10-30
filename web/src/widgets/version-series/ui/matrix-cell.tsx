'use client';

/**
 * One cell of the sheet matrix (`frontend/static/js/version-comparison.js:372-409`): a matched sheet as a
 * thumbnail with its flags, an unmatched one with its candidates, or the mark that the version has no such sheet.
 *
 * The flags are the original's: «?» (a match of medium confidence), «▤ группа», «✎» (by hand), «ИИ» (a link an AI
 * proposed and the check accepted — never an expert's act), «⧉» (a duplicate), «скан», «◫» / «⇉» (a sheet split
 * across versions). The contract's codes ride `data-` attributes; the reader reads Russian. A thumbnail can be
 * dragged onto another cell of its own column — that is a `link` edit — and «⤫» takes a sheet out of its row.
 * Every gesture reports an edit or a refusal to the matrix; nothing is sent from here.
 */

import { useEffect, useRef, useState } from 'react';
import type { DragEvent } from 'react';

import type { ComparisonAiPairHint, ComparisonMatrixCandidate, ComparisonMatrixCell, ComparisonMatrixRow, ComparisonPageRef } from '@/shared/api';
import {
  CELL_STATE_LABELS,
  CONFIDENCE_MARKS,
  DRAG_TYPE,
  FLAG_MARKS,
  SPLIT_PART_MARK,
  SPLIT_WHOLE_MARK,
  cellReasonWords,
  dragPayload,
  hintMark,
  hintText,
  hintTitle,
  isSoleSheet,
  newestHint,
  pageKey,
  splitDirection,
  useThumbnail,
} from '@/entities/version-series';

import { AiText } from '@/entities/version-series';

import styles from './version-series.module.css';

/** The thumbnail of a page, fetched when its cell comes into view and the placeholder until then. */
export function Thumb({ page, small }: { readonly page: ComparisonPageRef; readonly small?: boolean }) {
  const holder = useRef<HTMLSpanElement | null>(null);
  const [near, setNear] = useState(false);
  useEffect(() => {
    const element = holder.current;
    if (element === null || typeof IntersectionObserver === 'undefined') {
      setNear(true);
      return undefined;
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) setNear(true);
    }, { rootMargin: '200px' });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const image = useThumbnail(page.page_profile_id, near);
  return (
    <span ref={holder} className={small ? styles.thumbSmallFrame : styles.thumbFrame} data-thumbnail={image.state}>
      {image.url === null ? (
        <span className={styles.thumbEmpty}>{image.state === 'absent' || image.state === 'failed' ? 'нет миниатюры' : `стр. ${page.page_number}`}</span>
      ) : (
        <img src={image.url} alt="" className={styles.thumbImage} loading="lazy" decoding="async" />
      )}
    </span>
  );
}

export interface MatrixCellViewProps {
  readonly row: ComparisonMatrixRow;
  readonly cell: ComparisonMatrixCell;
  readonly versionName: string;
  readonly touched: ReadonlySet<string>;
  readonly mayEdit: boolean;
  /** The column of side A or side B of the chosen pair. */
  readonly side: 'a' | 'b' | null;
  readonly onSheet: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell) => void;
  readonly onUnlink: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell) => void;
  readonly onLink: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell, candidate: ComparisonMatrixCandidate) => void;
  readonly onAbsent: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell) => void;
  readonly onDropped: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell, text: string) => void;
  /** The answers of the AI check of doubtful pairs that concern this cell (`hintsFor`); none by default. */
  readonly hints?: readonly ComparisonAiPairHint[];
}

/**
 * What the AI check of doubtful pairs said about this cell: «🌙 ИИ: вероятно стр. N» on an unmatched cell, «ИИ ?» where the AI is
 * against the algorithm's pair or unsure of it, and the decision in words on hover. It changes nothing in the matrix; the model's
 * own sentence is shown with the label «не подтверждено инженером».
 */
function HintLine({ hints }: { readonly hints: readonly ComparisonAiPairHint[] }) {
  const hint = newestHint(hints);
  if (hint === undefined) return null;
  const mark = hintMark(hint);
  return (
    <span
      className={hint.stale ? `${styles.flag} ${styles.hintStale}` : styles.flag}
      title={hintTitle(hint)}
      data-ai-hint={mark}
      data-ai-pair-decision={hint.decision}
      {...(hint.confidence === undefined ? {} : { 'data-ai-confidence': hint.confidence })}
      data-ai-pair-question={hint.kind}
      {...(hint.stale ? { 'data-hint-stale': '' } : {})}
    >
      {hintText(hint)}
      {hint.reason === undefined || hint.reason === '' ? null : <AiText as="span">{hint.reason}</AiText>}
    </span>
  );
}

function MatchedCell(props: MatrixCellViewProps & { readonly page: ComparisonPageRef }) {
  const { row, cell, page, touched, mayEdit, onSheet, onUnlink } = props;
  const confidence = cell.confidence;
  const confidenceMark = confidence === undefined ? null : CONFIDENCE_MARKS[confidence];
  const drafted = touched.has(pageKey(page));
  return (
    <div
      className={drafted ? `${styles.thumb} ${styles.drafted}` : styles.thumb}
      draggable={mayEdit}
      data-cell-state="matched"
      data-page-number={page.page_number}
      {...(confidence === undefined ? {} : { 'data-cell-confidence': confidence })}
      {...(drafted ? { 'data-draft': '' } : {})}
      onDragStart={(event: DragEvent<HTMLDivElement>) => {
        event.dataTransfer.setData(DRAG_TYPE, dragPayload(page));
        event.dataTransfer.effectAllowed = 'move';
      }}
    >
      <button type="button" className={styles.thumbButton} title="Открыть сравнение этого листа: наложение, было, стало и рядом." onClick={() => onSheet(row, cell)}>
        <Thumb page={page} />
      </button>
      <div className={styles.thumbMeta}>
        <span>стр.{page.page_number}</span>
        {confidenceMark === null || confidenceMark.mark === null ? null : (
          <span className={styles.flag} title={confidenceMark.title} data-cell-flag-mark="confidence">
            {confidenceMark.mark}
          </span>
        )}
        {(cell.flags ?? []).map((flag) => {
          const mark =
            flag === 'split'
              ? splitDirection(row, cell.version_uid) === 'whole' ? SPLIT_WHOLE_MARK : SPLIT_PART_MARK
              : FLAG_MARKS[flag];
          return (
            <span key={flag} className={styles.flag} title={mark.title} data-cell-flag={flag}>
              {mark.mark}
            </span>
          );
        })}
        <HintLine hints={props.hints ?? []} />
      </div>
      {mayEdit && !isSoleSheet(row) ? (
        <button
          type="button"
          className={styles.cellMenu}
          title="Отвязать в отдельную строку"
          aria-label="Отвязать лист в отдельную строку"
          onClick={() => onUnlink(row, cell)}
        >
          ⤫
        </button>
      ) : null}
    </div>
  );
}

function UnmatchedCell(props: MatrixCellViewProps) {
  const { row, cell, mayEdit, onLink, onAbsent } = props;
  const reason = cellReasonWords(cell.reason);
  const candidates = cell.candidates ?? [];
  return (
    <div className={styles.unmatched} data-cell-state="unmatched" {...(cell.reason === undefined ? {} : { 'data-cell-reason': cell.reason })}>
      <div>⁇ {CELL_STATE_LABELS.unmatched}</div>
      {reason === '' ? null : <div className={styles.reason}>{reason}</div>}
      <HintLine hints={props.hints ?? []} />
      {candidates.length === 0 ? null : (
        <div className={styles.candidates}>
          <span>кандидаты:</span>
          {candidates.map((candidate) => (
            <span key={pageKey(candidate.page)} className={styles.candidate}>
              <Thumb page={candidate.page} small />
              {mayEdit ? (
                <button
                  type="button"
                  className="am-button am-button--small am-button--quiet"
                  title={`Связать с этой страницей (сходство ${candidate.score.toFixed(2)}). Затем «Применить сопоставления».`}
                  onClick={() => onLink(row, cell, candidate)}
                >
                  Связать · стр. {candidate.page.page_number}
                </button>
              ) : (
                <span className={styles.note}>стр. {candidate.page.page_number}</span>
              )}
            </span>
          ))}
        </div>
      )}
      {mayEdit ? (
        <button
          type="button"
          className="am-button am-button--small am-button--quiet"
          title="Отметить, что этого листа в версии нет. Это правка в черновике: затем «Применить сопоставления»."
          onClick={() => onAbsent(row, cell)}
        >
          Отметить, что этого листа в версии нет
        </button>
      ) : null}
    </div>
  );
}

export function MatrixCellView(props: MatrixCellViewProps) {
  const { row, cell, mayEdit, onDropped } = props;
  return (
    <td
      className={props.side === 'a' ? styles.sideA : props.side === 'b' ? styles.sideB : styles.cell}
      data-version-column={props.versionName}
      onDragOver={(event) => {
        if (mayEdit) event.preventDefault();
      }}
      onDrop={(event) => {
        if (!mayEdit) return;
        event.preventDefault();
        onDropped(row, cell, event.dataTransfer.getData(DRAG_TYPE));
      }}
    >
      {cell.state === 'matched' && cell.page !== undefined ? (
        <MatchedCell {...props} page={cell.page} />
      ) : cell.state === 'unmatched' ? (
        <UnmatchedCell {...props} />
      ) : (
        <div
          className={styles.absent}
          data-cell-state="absent"
          title={cellReasonWords(cell.reason) === '' ? undefined : cellReasonWords(cell.reason)}
        >
          ∅ {CELL_STATE_LABELS.absent}
          {cell.edit_id === undefined ? null : <span title="Отмечено вручную"> ✎</span>}
        </div>
      )}
    </td>
  );
}
