'use client';

/**
 * `SubmitLock` — the one client island the no-JavaScript forms carry (`C-22`).
 *
 * The sign-in, registration and password-change forms are plain HTML posts on purpose: no
 * password they carry is ever a JavaScript value. That leaves one thing only a script can do:
 * stop a second press from posting the same form twice while the first post is on its way (a
 * second sign-in, a second registration request, a password change racing itself).
 *
 * This island does that and **reads nothing**. It finds the form it sits in, listens for that
 * form's `submit` event, and once the first submission goes ahead it disables the form's submit
 * buttons and cancels any later `submit`. It never reads a field, a value, the form's data or
 * its elements; `web/tests/unit/session/submit-lock.test.ts` holds this file to that by its
 * source. Without JavaScript the form posts exactly as before.
 *
 * The buttons are disabled on the next task, not inside the `submit` event: the browser builds
 * the submission after the event, and a control disabled before that is left out of it. A page
 * restored from the back-forward cache gets its buttons back (`pageshow` with `persisted`).
 */

import { useEffect, useRef } from 'react';

/** The submit controls of a form: the only elements this island touches. */
export const SUBMIT_CONTROLS = 'button[type="submit"], input[type="submit"]';

/** A `submit` event, as far as the lock reads it. */
export interface SubmitLockEvent {
  readonly defaultPrevented: boolean;
  preventDefault(): void;
}

/** The form the lock sits in, narrowed to what it uses. */
export interface SubmitLockForm {
  onSubmit(listener: (event: SubmitLockEvent) => void): () => void;
  submitControls(): Iterable<{ disabled: boolean }>;
}

/** The window, narrowed to the back-forward-cache restore the lock undoes itself on. */
export interface SubmitLockView {
  onRestore(listener: () => void): () => void;
}

/**
 * Arm the lock on `form`. Returns the function that disarms it.
 *
 * The first `submit` nobody has cancelled goes ahead and locks the form; every later one is
 * cancelled until the page is restored from the back-forward cache.
 */
export function lockOnSubmit(
  form: SubmitLockForm,
  view: SubmitLockView | null,
  later: (task: () => void) => void = (task) => void setTimeout(task, 0),
): () => void {
  let locked = false;
  const setDisabled = (disabled: boolean) => {
    for (const control of form.submitControls()) control.disabled = disabled;
  };
  const offSubmit = form.onSubmit((event) => {
    if (event.defaultPrevented) return;
    if (locked) {
      event.preventDefault();
      return;
    }
    locked = true;
    later(() => setDisabled(true));
  });
  const offRestore =
    view?.onRestore(() => {
      locked = false;
      setDisabled(false);
    }) ?? (() => {});
  return () => {
    offSubmit();
    offRestore();
  };
}

/** Put inside a `<form>`; renders an empty hidden marker and locks the form on submit. */
export function SubmitLock() {
  const marker = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const element = marker.current?.closest('form');
    if (element === null || element === undefined) return undefined;
    const form: SubmitLockForm = {
      onSubmit(listener) {
        element.addEventListener('submit', listener);
        return () => element.removeEventListener('submit', listener);
      },
      submitControls: () => element.querySelectorAll<HTMLButtonElement | HTMLInputElement>(SUBMIT_CONTROLS),
    };
    const view: SubmitLockView = {
      onRestore(listener) {
        const onPageShow = (event: PageTransitionEvent) => {
          if (event.persisted) listener();
        };
        window.addEventListener('pageshow', onPageShow);
        return () => window.removeEventListener('pageshow', onPageShow);
      },
    };
    return lockOnSubmit(form, view);
  }, []);

  return <span ref={marker} hidden data-submit-lock="" />;
}
