'use client';

/**
 * The window of the opened sheet pair (`frontend/static/js/version-comparison-viewer.js`, `.vcv-overlay`): in the original the pair
 * opens over the whole screen, so the reader neither scrolls down a tall matrix to find the viewer nor scrolls back to find the
 * matrix after closing it. Here it is the same: a native modal `<dialog>` over the page (the browser keeps the focus inside, Esc
 * closes it and the screen behind is inert), with «✕ Закрыть» in its bar so that a pair still loading or refused can be left too.
 *
 * Where `showModal` is missing, or the harness asks for `staticOpen` (the static render, the contrast census), it is drawn open as
 * it is. A press on the backdrop does not close it, as the original's does not: a drag that pans the sheet may end outside.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import styles from './version-series.module.css';

export const PAIR_WINDOW_TITLE = 'Просмотр пары листов';

export interface PairViewerWindowProps {
  readonly children: ReactNode;
  /** «✕ Закрыть» and Esc; the window has no way out of itself without it. */
  readonly onClose?: (() => void) | undefined;
  /** The census and the static render: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

export function PairViewerWindow({ children, onClose, staticOpen = false }: PairViewerWindowProps) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const element = dialog.current;
    if (element === null || staticOpen || typeof element.showModal !== 'function') return;
    if (!element.open) element.showModal();
    const closed = () => {
      closeRef.current?.();
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
      className={styles.viewerWindow}
      open={staticOpen ? true : undefined}
      aria-label={PAIR_WINDOW_TITLE}
      data-pair-viewer=""
    >
      <div className={styles.viewerBox}>
        <header className={styles.viewerBar}>
          <strong>{PAIR_WINDOW_TITLE}</strong>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onClose} title="Закрыть окно и вернуться к матрице (Esc).">
            ✕ Закрыть
          </button>
        </header>
        <div className={styles.viewerBody}>{children}</div>
      </div>
    </dialog>
  );
}
