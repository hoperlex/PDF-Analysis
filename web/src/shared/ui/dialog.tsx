'use client';

/**
 * `Dialog` — the shared window over the screen (`UIP-G-04`, `UIC-G-15`): one native modal `<dialog>`
 * with a title bar, a body and a row of buttons, so that every window of the product opens, closes and
 * lays itself out in the same way. The window of the models per stage under «Запустить» (`Г10-B`, `S05`)
 * is built on it; what stands in its body is that screen's, not this file's.
 *
 * ## What the window promises
 *
 * - **It is opened by being mounted and closed by being unmounted.** `showModal()` runs when it mounts:
 *   the browser keeps focus inside, the page behind is inert and Esc is heard. Where `showModal` is
 *   missing, or the harness asks for `staticOpen` (the static render, the contrast census), nothing is
 *   wired and the window is drawn open as it is.
 * - **Focus goes in and comes back.** Opening moves focus to the author's `autofocus` control, else to
 *   the first field of the body, else to what the browser picks (the close button). Closing, by whichever
 *   way, returns focus to the control that held it before the window opened, unless that control has left
 *   the page.
 * - **Esc and «Закрыть» ask for a close** (`onClose`); the owner of the window unmounts it. Esc is held
 *   back from the browser's own close (`cancel` is prevented), so a window whose owner does not unmount it
 *   stays open and its fields stay as they were. One browser exception is known: Chrome closes a modal
 *   whose Esc was prevented once already on a second press; the `close` event then calls `onClose` too.
 * - **A press on the dimmed page does nothing.** It is not a way out and it does not touch what was typed:
 *   a drag that selects text may end outside the window. No click handler is attached to the window.
 * - **Title and buttons share one layout.** The title and the close button are one row at the top, the
 *   body scrolls between, and `actions` (the buttons) are a row at the bottom, right-aligned, outside the
 *   scroll so they are never pushed out of sight.
 *
 * The dimming is the browser's own `::backdrop`. Styling it needs a token in `globals.css` that does not
 * exist yet and a pseudo-element the contrast census does not model, so it is left to a later task.
 *
 * ## Two layers
 *
 * `attachModalDialog` is the whole of the behaviour, over a narrow view of the element (`DialogHost`) and of
 * the document (`DialogDocument`), so the node test environment, which has no DOM, drives each promise
 * with a fake (`web/tests/unit/shared-ui/dialog.test.ts`). `Dialog` is the markup and the island that
 * hands the real element to it.
 */

import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';

import styles from './dialog.module.css';

/** Something focus can be given to. */
export interface DialogFocusTarget {
  focus(): void;
  /** `false` once the element has left the page: focus is not given back to it. */
  readonly isConnected: boolean;
}

/** What `attachModalDialog` reads and calls on the `<dialog>` element. */
export interface DialogHost {
  readonly open: boolean;
  showModal(): void;
  close(): void;
  /** Listen for `cancel` (Esc) or `close`; the answer stops listening. */
  on(type: 'cancel' | 'close', listener: (event: { preventDefault(): void }) => void): () => void;
  /** The first element inside the window that matches `selector`. */
  query(selector: string): DialogFocusTarget | null;
}

/** What `attachModalDialog` reads from the document. */
export interface DialogDocument {
  readonly activeElement: DialogFocusTarget | null;
  /** The document's body: focus on it means focus on nothing, so there is nothing to return to. */
  readonly body: unknown;
}

/** The control the author asked focus to start on; the browser honours it by itself. */
export const DIALOG_AUTOFOCUS_SELECTOR = '[autofocus]';

/** The first field of the body, where focus starts when the author named none. */
export const DIALOG_FIELD_SELECTOR =
  '[data-dialog-body] input:not([type="hidden"]):not([disabled]), ' +
  '[data-dialog-body] select:not([disabled]), ' +
  '[data-dialog-body] textarea:not([disabled])';

export interface DialogHandlers {
  /** Esc was pressed, or the browser closed the window; the owner unmounts it. */
  readonly onClose: () => void;
}

/**
 * Open `host` as a modal and wire its keys; the answer closes it and gives focus back.
 *
 * Nothing is attached for a press on the page behind: such a press is delivered to the window
 * element itself, and the window has no click rule, so it neither closes nor clears.
 */
export function attachModalDialog(
  host: DialogHost,
  document: DialogDocument,
  handlers: DialogHandlers,
): () => void {
  const held = document.activeElement;
  const opener = held !== null && held !== document.body ? held : null;
  // The window is closed, by us or by the browser; focus is given back once.
  let finished = false;

  const giveFocusBack = (): void => {
    if (opener !== null && opener.isConnected) opener.focus();
  };

  const stopCancel = host.on('cancel', (event) => {
    // Held back from the browser's close: the owner decides, by unmounting, whether the window goes.
    event.preventDefault();
    handlers.onClose();
  });
  const stopClose = host.on('close', () => {
    if (finished) return;
    finished = true;
    giveFocusBack();
    handlers.onClose();
  });

  if (!host.open) host.showModal();
  if (host.query(DIALOG_AUTOFOCUS_SELECTOR) === null) host.query(DIALOG_FIELD_SELECTOR)?.focus();

  return () => {
    stopCancel();
    stopClose();
    if (finished) return;
    finished = true;
    if (host.open) host.close();
    giveFocusBack();
  };
}

export type DialogSize = 'sm' | 'md' | 'lg';

export interface DialogProps {
  /** The window's name: its heading and its accessible name. */
  readonly title: string;
  /** The body; it scrolls when it is taller than the window. */
  readonly children: ReactNode;
  /** The buttons, in a row at the bottom, right-aligned; the window is as it is without them. */
  readonly actions?: ReactNode | undefined;
  /** Esc and «Закрыть»: the owner unmounts the window. */
  readonly onClose: () => void;
  /** The width: `sm` for a question, `md` (the default) for a form, `lg` for a table. */
  readonly size?: DialogSize | undefined;
  /** The census and the static render: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
  /** `data-` markers of the window (the journey and the tests name it by them). */
  readonly markers?: Readonly<Record<`data-${string}`, string>> | undefined;
}

const SIZE_CLASS: Readonly<Record<DialogSize, string>> = {
  sm: styles.sm ?? '',
  md: styles.md ?? '',
  lg: styles.lg ?? '',
};

export function Dialog({ title, children, actions, onClose, size = 'md', staticOpen = false, markers }: DialogProps) {
  const element = useRef<HTMLDialogElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const titleId = useId();

  useEffect(() => {
    const dialog = element.current;
    if (dialog === null || staticOpen || typeof dialog.showModal !== 'function') return undefined;
    return attachModalDialog(
      {
        get open() {
          return dialog.open;
        },
        showModal: () => dialog.showModal(),
        close: () => dialog.close(),
        on: (type, listener) => {
          dialog.addEventListener(type, listener);
          return () => dialog.removeEventListener(type, listener);
        },
        query: (selector) => dialog.querySelector<HTMLElement>(selector),
      },
      {
        get activeElement() {
          const active = document.activeElement;
          return active instanceof HTMLElement || active instanceof SVGElement ? active : null;
        },
        body: document.body,
      },
      { onClose: () => closeRef.current() },
    );
  }, [staticOpen]);

  return (
    <dialog
      ref={element}
      className={`${styles.dialog} ${SIZE_CLASS[size]}`}
      open={staticOpen ? true : undefined}
      aria-labelledby={titleId}
      {...markers}
    >
      <div className={styles.header}>
        <h2 className={styles.title} id={titleId}>{title}</h2>
        <button type="button" className={styles.close} aria-label="Закрыть" onClick={() => onClose()}>
          <span aria-hidden="true">×</span>
        </button>
      </div>
      <div className={styles.body} data-dialog-body="">{children}</div>
      {actions === undefined ? null : <div className={styles.actions} data-dialog-actions="">{actions}</div>}
    </dialog>
  );
}
