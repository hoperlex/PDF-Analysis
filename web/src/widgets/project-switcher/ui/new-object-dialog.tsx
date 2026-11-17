'use client';

/**
 * The window «Новый объект» that the object selector opens (`UIP-S03-01`, owner rulings Г3-B, Г6-C, Г7-B, Г12-B): the shared
 * window (`Dialog`, `UIP-G-04`) over the screen, with the one field «Название объекта» and the buttons «Отмена» and «Создать».
 *
 * ## What it is made of
 *
 * The window is `Dialog` from `@/shared/ui`, and its body is the **same form** as the page «Объекты» has
 * (`CreateProjectForm`, `@/features/create-project`) in its window mode. The form owns the field, the name check, the command and
 * the idempotency key; this file owns what is the window's: the title, the row of buttons and what happens when the object has
 * been made. Nothing here is a second copy of the form.
 *
 * The buttons are in the window's row, outside the form. «Создать» is a submit button of the form by its `form` attribute, so it
 * and Enter in the field are one submit. The form says when a send is on its way (`onBusyChange`) and the button is held until it
 * ends (and for an account known not to be an expert, whom the form tells so instead of drawing the field).
 *
 * ## What the window promises
 *
 * - **What was typed is not lost.** The window is closed only by «Отмена», by «Закрыть» and by Esc (`Dialog`'s own rules); a press
 *   on the dimmed page does nothing (no click rule is attached), and a refusal leaves the field as it was, with the refusal as one
 *   line under it. «Создать» again is the retry: the same name is the same command under the same key, never a second object.
 * - **Esc and «Отмена» close it at any moment**, a send on its way included: the window never holds the reader. A send that is
 *   already on its way is not recalled, so the object may still be made; the list refreshes either way, and nothing here claims it
 *   was not.
 * - **Focus goes in and comes back** (`Dialog`): it starts in the field, and on closing returns to the control that held it, which is
 *   the selector's button (the menu returns focus there before the window opens).
 * - **No code of the object** in the window: «prj_…» stays in the object's «Сведения» (`Г12-B`).
 *
 * ## The object becomes the open one
 *
 * On success the caller is given the project (`onCreated`); the selector then does what a click on the object's row does
 * (`afterObjectCreated`). The window does not navigate by itself, and does not close itself on success: the caller unmounts it.
 */

import { useId, useState } from 'react';

import type { Project } from '@/shared/api';
import { Dialog } from '@/shared/ui';
import { useMayActAsExpert } from '@/entities/account';
import { CreateProjectForm } from '@/features/create-project';

import { NEW_PROJECT_LABEL } from '../model/switcher';

export const NEW_OBJECT_CANCEL_LABEL = 'Отмена';
export const NEW_OBJECT_CREATE_LABEL = 'Создать';

export interface NewObjectDialogProps {
  /** Esc, «Закрыть» and «Отмена»: the owner unmounts the window. */
  readonly onClose: () => void;
  /** The object was made: the owner makes it the open one and unmounts the window. */
  readonly onCreated: (project: Project) => void;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

export function NewObjectDialog({ onClose, onCreated, staticOpen }: NewObjectDialogProps) {
  const formId = useId();
  const [busy, setBusy] = useState(false);
  // The selector does not offer the row to an account known not to be an expert; this is for one that became known as such after
  // the window opened. The form then says so in its own words (it draws no field), and a button with nothing to submit is held.
  const mayAct = useMayActAsExpert();
  return (
    <Dialog
      title={NEW_PROJECT_LABEL}
      size="sm"
      onClose={onClose}
      staticOpen={staticOpen}
      markers={{ 'data-new-object-dialog': '' }}
      actions={
        <>
          <button type="button" className="am-button am-button--quiet" onClick={onClose}>
            {NEW_OBJECT_CANCEL_LABEL}
          </button>
          <button type="submit" className="am-button" form={formId} disabled={busy || !mayAct}>
            {NEW_OBJECT_CREATE_LABEL}
          </button>
        </>
      }
    >
      <CreateProjectForm mode="window" formId={formId} onCreated={onCreated} onBusyChange={setBusy} />
    </Dialog>
  );
}
