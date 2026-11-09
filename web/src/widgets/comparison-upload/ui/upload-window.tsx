'use client';

/**
 * The upload dialogs as a window over the screen (`frontend/static/js/version-comparison.js`, `.vc-modal` in a `.modal-overlay`): in
 * the original «Загрузка проекта и версий» is a modal, so the table and the tabs stay where they were and the reader is back at them
 * as soon as it is closed. A native modal `<dialog>`: the browser keeps the focus inside, Esc closes it (what «Закрыть» does) and the
 * screen behind is inert.
 *
 * While the files are being read or sent Esc is refused: a press meant for something else must not drop a transfer of hundreds of
 * megabytes. «Закрыть» in the dialog's own header is still there, and an unfinished upload is listed for continuing.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import styles from './comparison-upload.module.css';

export interface UploadWindowProps {
  readonly children: ReactNode;
  readonly onClose: () => void;
  /** Esc does nothing: a transfer is running. */
  readonly escBlocked?: boolean;
}

export function UploadWindow({ children, onClose, escBlocked = false }: UploadWindowProps) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const blockedRef = useRef(escBlocked);
  blockedRef.current = escBlocked;

  useEffect(() => {
    const element = dialog.current;
    if (element === null || typeof element.showModal !== 'function') return;
    if (!element.open) element.showModal();
    const cancelled = (event: Event) => {
      if (blockedRef.current) event.preventDefault();
    };
    const closed = () => {
      closeRef.current();
    };
    element.addEventListener('cancel', cancelled);
    element.addEventListener('close', closed);
    return () => {
      element.removeEventListener('cancel', cancelled);
      element.removeEventListener('close', closed);
      if (element.open) element.close();
    };
  }, []);

  return (
    <dialog ref={dialog} className={styles.window} aria-label="Загрузка версий для сравнения" data-upload-window="">
      {children}
    </dialog>
  );
}
