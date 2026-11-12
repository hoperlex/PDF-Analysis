'use client';

/** @jsxRuntime automatic */

/**
 * «Во весь экран» on «Разбор»: the open finding's page over the whole screen.
 *
 * The original's block view (`tile-split-overlay`: 94vh, at most 1440px, the picture on the left and
 * a 380px panel on the right, ‹ › with «i / n», closed by × or a click outside) is the model. Here
 * the picture is the PDF page with the quotations framed, the panel carries the finding, its ✓/✕
 * and the quotations, and ‹ › walk the findings in the order the list shows them under its
 * filters, so an expert goes through a run without leaving the page.
 *
 * A native modal `<dialog>`: the browser keeps focus inside, Esc closes it and the screen behind
 * is inert. Where `showModal` is missing (a static render, the unit suite) it is drawn open as it
 * is, which is what the styling census needs; `staticOpen` says so.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import styles from './review-viewer-dialog.module.css';

export interface ReviewViewerDialogProps {
  /** Where the open finding is among those the list shows, from 1; null when the filters hide it. */
  readonly position: number | null;
  /** How many findings the list shows. */
  readonly total: number;
  /** Absent at the first finding. */
  readonly onPrevious?: (() => void) | undefined;
  /** Absent at the last finding. */
  readonly onNext?: (() => void) | undefined;
  readonly onClose: () => void;
  /** The open finding's text, one line in the bar. */
  readonly title: string;
  readonly children: ReactNode;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

export interface ReviewViewerAsideProps {
  readonly findingUid: string;
  /** «Критическое · Лист 3 · стр. 7»: the severity and where the finding is. */
  readonly meta: string;
  readonly text: string;
  readonly recommendation: string;
  /** `F8-WEB`: the critic's advice for a block finding, one line under the recommendation. */
  readonly advice?: ReactNode;
  /** ✓/✕ for a session that may decide. */
  readonly actions?: ReactNode;
  /** «Блоки страницы N» (`UI-A-74`): the strip of the cited page's portal blocks, under the finding. */
  readonly blocks?: ReactNode;
}

/** The finding at the head of the side column: where it is, what it says, what it recommends, and ✓/✕. */
export function ReviewViewerAside({ findingUid, meta, text, recommendation, advice, actions, blocks }: ReviewViewerAsideProps) {
  return (
    <div className={styles.aside} data-finding-uid={findingUid}>
      {meta === '' ? null : <p className={styles.meta}>{meta}</p>}
      <p className={styles.text}>{text}</p>
      {recommendation === '' ? null : <p className={styles.recommendation}>{recommendation}</p>}
      {advice}
      {actions}
      {blocks}
    </div>
  );
}

export function ReviewViewerDialog({
  position,
  total,
  onPrevious,
  onNext,
  onClose,
  title,
  children,
  staticOpen = false,
}: ReviewViewerDialogProps) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const element = dialog.current;
    if (element === null || staticOpen || typeof element.showModal !== 'function') return;
    if (!element.open) element.showModal();
    const closed = () => {
      closeRef.current();
    };
    element.addEventListener('close', closed);
    return () => {
      element.removeEventListener('close', closed);
      if (element.open) element.close();
    };
  }, [staticOpen]);

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      open={staticOpen ? true : undefined}
      aria-label="Находка на странице документа"
      data-review-viewer=""
      onClick={(event) => {
        // A press on the backdrop lands on the dialog itself; inside, it lands on the content.
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={styles.box}>
        <header className={styles.bar}>
          <div className={styles.steps} role="group" aria-label="Находки списка">
            <button
              type="button"
              className={styles.step}
              onClick={onPrevious}
              disabled={onPrevious === undefined}
              aria-label="Предыдущая находка"
              title="Предыдущая находка"
            >
              ‹
            </button>
            <span className={styles.position} data-viewer-position={position ?? ''}>
              {position === null ? `— / ${total}` : `${position} / ${total}`}
            </span>
            <button
              type="button"
              className={styles.step}
              onClick={onNext}
              disabled={onNext === undefined}
              aria-label="Следующая находка"
              title="Следующая находка"
            >
              ›
            </button>
          </div>
          <span className={styles.title} title={title}>
            {title}
          </span>
          <button
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label="Закрыть"
            title="Закрыть (Esc)"
          >
            ✕
          </button>
        </header>
        <div className={styles.body}>{children}</div>
      </div>
    </dialog>
  );
}
