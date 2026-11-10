'use client';

/**
 * The life of a native modal `<dialog>` of this widget, shared by the run's window and the plan's (`READINESS-WEB-01`): it is
 * opened with `showModal` when it mounts (the browser keeps focus inside, Esc closes it, the page behind is inert), the `close`
 * event calls `onClose`, and unmounting closes it. Where `showModal` is missing, or the harness asks for `staticOpen` (the static
 * render, the contrast census), nothing is wired and the dialog is drawn open as it is.
 */

import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

export function useModalDialog(staticOpen: boolean, onClose: () => void): RefObject<HTMLDialogElement | null> {
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

  return dialog;
}
