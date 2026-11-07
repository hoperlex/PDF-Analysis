'use client';

/**
 * The window of the opened sheet pair (`frontend/static/js/version-comparison-viewer.js`, `.vcv-overlay`): in the original the pair opens over
 * the whole screen, so the reader neither scrolls down a tall matrix to find the viewer nor scrolls back to find the matrix after closing it.
 * It is a {@link ModalWindow} with its own «✕ Закрыть» in a bar, so that a pair still loading or refused can be left too.
 */

import type { ReactNode } from 'react';

import { ModalWindow } from './modal-window';
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
  return (
    <ModalWindow label={PAIR_WINDOW_TITLE} className={styles.viewerWindow} onClose={onClose} staticOpen={staticOpen} markers={{ 'data-pair-viewer': '' }}>
      <div className={styles.viewerBox}>
        <header className={styles.viewerBar}>
          <strong>{PAIR_WINDOW_TITLE}</strong>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onClose} title="Закрыть окно и вернуться к матрице.">
            ✕ Закрыть
          </button>
        </header>
        <div className={styles.viewerBody}>{children}</div>
      </div>
    </ModalWindow>
  );
}
