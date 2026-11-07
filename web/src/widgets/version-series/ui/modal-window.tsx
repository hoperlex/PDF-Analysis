'use client';

/**
 * A window over the screen for the three things the original opens as modals from the card of a set: the opened pair of sheets, «Порядок версий»
 * and the window «Сформировать PDF-отчёт…» (`frontend/static/js/version-comparison.js`, `.modal-overlay`). A native modal `<dialog>`: the browser
 * keeps the focus inside, Esc closes it (what the window's own «Закрыть» does) and the screen behind is inert, so the matrix is not pushed
 * down the page and is where it was when the window is closed.
 *
 * Where `showModal` is missing, or the harness asks for `staticOpen` (the static render, the contrast census), it is drawn open as it is.
 * A press on the backdrop closes nothing, as the original's does not for the viewer: a drag that pans the sheet may end outside it.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

export interface ModalWindowProps {
  readonly children: ReactNode;
  /** What the window is called for a reader of the screen. */
  readonly label: string;
  /** The module class that sizes it. */
  readonly className: string;
  /** Esc and the window's own way out; absent in the static harness. */
  readonly onClose?: (() => void) | undefined;
  /** The census and the static render: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
  /** `data-` markers of the window (the journey and the tests name it by them). */
  readonly markers?: Readonly<Record<`data-${string}`, string>> | undefined;
}

export function ModalWindow({ children, label, className, onClose, staticOpen = false, markers }: ModalWindowProps) {
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
    <dialog ref={dialog} className={className} open={staticOpen ? true : undefined} aria-label={label} {...markers}>
      {children}
    </dialog>
  );
}
